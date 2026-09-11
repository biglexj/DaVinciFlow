"""Estado y operaciones del editor, sin dependencias de un framework gráfico."""

from dataclasses import asdict, replace
from pathlib import Path

from davinci_flow.ai.client import GeminiClient
from davinci_flow.assets.library import scan_library
from davinci_flow.editorial.model import Decision, EditorialError, EditorialOptions, Proposal, Template
from davinci_flow.editorial.planner import propose
from davinci_flow.editorial.preferences import Preferences, PREFERENCES_PATH
from davinci_flow.editorial.sources import basic_titles, from_srt, scan_installed
from davinci_flow.editorial import resolve_bridge
from davinci_flow.sfx.catalog import DEFAULT_SFX_ASSETS


class EditorialController:
    def __init__(self, preferences_path: Path = PREFERENCES_PATH):
        self.preferences_path = preferences_path
        self.preferences = Preferences.load(preferences_path)
        self.snapshot = None
        self.proposal = None
        self.dirty = False
        fresh_basic = {t.id: t for t in basic_titles()}
        loaded_templates = [fresh_basic.get(t.id, t) for t in (Template(**d) for d in self.preferences.templates)]
        self.templates = tuple(loaded_templates) or basic_titles()
        self.catalog = dict(fresh_basic)
        self.catalog.update({t.id: t for t in self.templates})
        if self.preferences.templates != [asdict(t) for t in self.templates]:
            self.save_preferences()
        self.resources = ()
        self.library_loaded = False
        self.diagnostics = ()

    def read_resolve(self, track=1, first=1, last=120):
        snapshot, templates = resolve_bridge.read_resolve(track, first, last)
        self.snapshot = snapshot
        self.proposal, self.dirty = None, False
        self.catalog = {k: t for k, t in self.catalog.items() if t.source != 'media_pool'}
        self.catalog.update({t.id: t for t in templates})
        return snapshot

    def read_srt(self, path, fps=24):
        snapshot = from_srt(path, fps)
        self.snapshot = snapshot
        self.proposal, self.dirty = None, False
        return snapshot

    def scan_titles(self, roots=None):
        diagnostics = []
        templates = scan_installed(roots, diagnostics)
        self.catalog.update({t.id: t for t in templates})
        return len(templates), diagnostics

    def read_project_titles(self):
        templates = resolve_bridge.read_titles()
        self.catalog = {k: t for k, t in self.catalog.items() if t.source != 'media_pool'}
        self.catalog.update({t.id: t for t in templates})
        return len(templates)

    def choose_templates(self, identifiers):
        if not identifiers or len(identifiers) > 60 or any(i not in self.catalog for i in identifiers):
            raise EditorialError('Elige entre 1 y 60 plantillas disponibles.')
        # El catálogo de una propuesta ya generada es inmutable: esta selección es para la siguiente.
        self.templates = tuple(t for t in self.catalog.values() if t.id in identifiers)
        self.save_preferences()

    def scan_resources(self):
        self.resources, self.diagnostics = scan_library(self.preferences.paths)
        self.library_loaded = True
        return len(self.resources), self.diagnostics

    def resource_context(self):
        chosen = set(self.preferences.resource_ids)
        if chosen and not self.library_loaded:
            raise EditorialError('Indexa la biblioteca para comprobar los recursos seleccionados.')
        missing = chosen - {r.id for r in self.resources}
        if missing:
            raise EditorialError(f'{len(missing)} recursos seleccionados no están disponibles. Revisa la biblioteca.')
        user_resources = tuple(r.context() for r in self.resources if r.id in chosen)
        builtin_sfx = tuple(
            {"id": a.id, "category": "sfx", "name": f"{a.name} ({a.category})"}
            for a in DEFAULT_SFX_ASSETS
        )
        combined = list(user_resources)
        user_ids = {r["id"] for r in user_resources}
        for sfx in builtin_sfx:
            if sfx["id"] not in user_ids and len(combined) < 80:
                combined.append(sfx)
        return tuple(combined)

    def options(self):
        p = self.preferences
        return EditorialOptions(p.mode, p.format, p.density, p.direction, self.resource_context())

    def generate(self, client=None):
        if self.snapshot is None:
            raise EditorialError('Captura la secuencia o abre un SRT primero.')
        self.save_preferences()
        result = propose(self.snapshot, self.templates,
                         client or GeminiClient(model_name=self.preferences.model, strict_model=True),
                         options=self.options())
        # Un fallo conserva la propuesta anterior y todas sus revisiones.
        self.proposal = result
        self.dirty = True
        return result

    def load_proposal(self, path):
        result = Proposal.load(path)
        self.proposal, self.snapshot = result, result.snapshot
        self.templates = result.templates
        self.catalog.update({t.id: t for t in result.templates})
        self.preferences.model = result.model
        if result.options:
            for name in ('mode', 'format', 'density', 'direction'):
                setattr(self.preferences, name, getattr(result.options, name))
        else:
            self.preferences.mode = 'captions'
        self.dirty = False
        return result

    def save_proposal(self, path):
        if self.proposal is None:
            raise EditorialError('Todavía no hay una propuesta para guardar.')
        self.proposal.save(path)
        self.dirty = False

    def review(self, index, **changes):
        if self.proposal is None:
            raise EditorialError('Genera o abre una propuesta antes de revisar.')
        self.proposal = self.proposal.edit(index, **changes, reviewed=True)
        self.dirty = True

    def approve_all(self):
        if self.proposal is None:
            raise EditorialError('Genera o abre una propuesta antes de aprobar.')
        self.proposal = self.proposal.approve_all()
        self.dirty = True

    def apply(self):
        if self.proposal is None:
            raise EditorialError('No hay una propuesta revisada.')
        fresh_basic = {t.id: t for t in basic_titles()}
        synced_templates = tuple(fresh_basic.get(t.id, t) for t in self.proposal.templates)
        if synced_templates != self.proposal.templates:
            self.proposal = replace(self.proposal, templates=synced_templates)
        self.proposal.validate(require_review=True)
        return resolve_bridge.apply(self.proposal)

    def undo(self):
        return resolve_bridge.undo()

    def create_default_proposal(self):
        """Crea una propuesta base 1:1 desde los subtítulos existentes sin requerir llamada a IA."""
        if self.snapshot is None:
            raise EditorialError('Captura la secuencia o abre un SRT primero.')
        fresh_basic = {t.id: t for t in basic_titles()}
        templates = tuple(fresh_basic.get(t.id, t) for t in (self.templates or basic_titles()))
        if not templates:
            raise EditorialError('No hay plantillas disponibles para la propuesta.')
        main_template = next((t.id for t in templates if 'principal' in t.name.lower()), templates[0].id)
        decisions = []
        for i, cue in enumerate(self.snapshot.cues):
            decisions.append(
                Decision(
                    cue_index=i,
                    context='',
                    main=cue.text,
                    accent='',
                    templates={'main': main_template},
                    reason='Subtítulo original listo para revisión directa.',
                    enabled=True,
                    reviewed=False,
                    edit_note='',
                    visual_note='',
                    resource_id='',
                )
            )
        options = self.options()
        proposal = Proposal(
            snapshot=self.snapshot,
            templates=templates,
            decisions=tuple(decisions),
            model='manual-direct',
            version='1.1.0',
            options=options,
        )
        proposal.validate()
        self.proposal = proposal
        self.dirty = True
        return proposal

    def update_cues(self, new_cues):
        """Sincroniza subtítulos corregidos actualizando el snapshot y las decisiones existentes."""
        if self.snapshot is None:
            raise EditorialError('No hay una secuencia activa para actualizar subtítulos.')
        if len(new_cues) != len(self.snapshot.cues):
            raise EditorialError('La cantidad de subtítulos corregidos no coincide con la secuencia.')
        old_cues = self.snapshot.cues
        self.snapshot = replace(self.snapshot, cues=tuple(new_cues))
        if self.proposal is not None:
            new_decisions = []
            for i, (decision, old_cue, new_cue) in enumerate(zip(self.proposal.decisions, old_cues, new_cues)):
                if old_cue.text != new_cue.text:
                    note = decision.edit_note
                    if not note:
                        note = f"Texto corregido: '{old_cue.text}' -> '{new_cue.text}'"
                    if decision.main == old_cue.text and not decision.context and not decision.accent:
                        new_d = replace(decision, main=new_cue.text, edit_note=note)
                    else:
                        new_main = new_cue.text if decision.main == old_cue.text else decision.main
                        new_d = replace(decision, main=new_main, edit_note=note)
                    new_decisions.append(new_d)
                else:
                    new_decisions.append(decision)
            updated_proposal = replace(self.proposal, snapshot=self.snapshot, decisions=tuple(new_decisions))
            updated_proposal.validate()
            self.proposal = updated_proposal
            self.dirty = True
        return self.snapshot

    def save_preferences(self):
        self.preferences.templates = [asdict(t) for t in self.templates]
        self.preferences.save(self.preferences_path)
