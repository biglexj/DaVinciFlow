"""Procesamiento editorial reanudable con checkpoints locales por tanda."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from davinci_flow.ai.model_catalog import ModelCapability, capability_for
from davinci_flow.ai.providers.factory import build_text_provider
from davinci_flow.editorial.model import (
    Decision,
    EditorialError,
    EditorialOptions,
    Proposal,
    Snapshot,
    Template,
    digest,
)
from davinci_flow.editorial.planner import propose_batch
from davinci_flow.editorial.resolve_bridge import read_resolve
from davinci_flow.subtitles.model import SubtitleCue

SESSION_DIR = Path.home() / ".davinci_flow" / "editorial_runs"
FULL_CAPTURE_LAST = 1_000_000
SESSION_VERSION = 1
BATCH_CHOICES = ("20", "50", "100", "500", "all")


def capture_full_sequence(track: int = 1) -> tuple[Snapshot, tuple[Template, ...]]:
    """Captura toda la pista activa sin cambiar el estado del controlador Flet."""
    snapshot, templates = read_resolve(track=track, first=1, last=FULL_CAPTURE_LAST)
    return replace(snapshot, first=1, last=len(snapshot.cues)), templates


def _stable_cuts(snapshot: Snapshot, start: int = 0, end: int | None = None) -> tuple | None:
    if not snapshot.cuts:
        return ()
    if len(snapshot.cut_source_refs) != len(snapshot.cuts):
        return None
    end = len(snapshot.cues) if end is None else min(end, len(snapshot.cues))
    if start < 0 or start >= end:
        return ()
    span_start = min(cue.start_frame for cue in snapshot.cues[start:end])
    span_end = max(cue.end_frame for cue in snapshot.cues[start:end])
    signatures: Counter = Counter()
    for cut, source_ref in zip(snapshot.cuts, snapshot.cut_source_refs):
        if len(cut) < 5:
            return None
        if cut[4] <= span_start or cut[3] >= span_end:
            continue
        if not source_ref:
            return None
        # TimelineItem IDs can change on duplicate; media references and cut geometry remain stable.
        signature = ((cut[0],) + cut[3:] if cut[0] == "audio" else cut[:2] + cut[3:])
        signatures[signature + (source_ref,)] += 1
    return tuple(sorted(signatures.items(), key=lambda item: repr(item[0])))


def snapshot_span_offset(source: Snapshot, target: Snapshot) -> int | None:
    """Devuelve el desplazamiento de un snapshot dentro de otro si fuente y tramo coinciden."""
    if source.source != target.source:
        return None
    if (source.fps, source.width, source.height, source.origin, source.track) != (
        target.fps, target.width, target.height, target.origin, target.track
    ):
        return None
    if source.source == "resolve":
        if not source.project_id or source.project_id != target.project_id:
            return None
    elif source.timeline != target.timeline:
        return None
    offset = source.first - target.first
    finish = offset + len(source.cues)
    if offset < 0 or finish > len(target.cues) or source.cues != target.cues[offset:finish]:
        return None
    source_cuts = _stable_cuts(source)
    target_cuts = _stable_cuts(target, offset, finish)
    if source_cuts is None or target_cuts is None:
        if source.timeline_id != target.timeline_id or source.cuts != target.cuts:
            return None
    elif source_cuts != target_cuts:
        return None
    return offset


def _options_signature(options: EditorialOptions) -> str:
    return digest(asdict(options))


def _template_signature(templates: tuple[Template, ...]) -> str:
    return digest([asdict(template) for template in templates])


def _run_key(snapshot: Snapshot, options: EditorialOptions, templates: tuple[Template, ...]) -> str:
    stable_cuts = _stable_cuts(snapshot)
    stable_source = {
        "source": snapshot.source,
        "project_id": snapshot.project_id,
        "timeline": snapshot.timeline if snapshot.source == "srt" else "",
        # If media references are unavailable, keep identity conservative to avoid merging unrelated duplicates.
        "timeline_id": snapshot.timeline_id if snapshot.source == "resolve" and (
            stable_cuts is None or not snapshot.project_id
        ) else "",
        "fps": snapshot.fps,
        "width": snapshot.width,
        "height": snapshot.height,
        "origin": snapshot.origin,
        "track": snapshot.track,
        "first": snapshot.first,
        "cues": [asdict(cue) for cue in snapshot.cues],
        "cuts": stable_cuts if stable_cuts is not None else snapshot.cuts,
        "cut_source_refs": snapshot.cut_source_refs if stable_cuts is None else (),
    }
    return digest({"source": stable_source, "options": asdict(options),
                   "templates": [asdict(template) for template in templates]})[:40]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class EditorialBatchRun:
    snapshot: Snapshot
    templates: tuple[Template, ...]
    options: EditorialOptions
    decisions: list[Decision | None]
    history: list[dict[str, Any]]
    created_at: str
    updated_at: str

    @classmethod
    def empty(cls, snapshot: Snapshot, templates: tuple[Template, ...],
              options: EditorialOptions) -> "EditorialBatchRun":
        if not templates:
            raise EditorialError("Elige al menos una plantilla antes de generar tandas.")
        return cls(snapshot, templates, options, [None] * len(snapshot.cues), [], _now(), _now())

    @property
    def total(self) -> int:
        return len(self.decisions)

    @property
    def processed(self) -> int:
        return sum(decision is not None for decision in self.decisions)

    @property
    def complete(self) -> bool:
        return self.total > 0 and self.processed == self.total

    @property
    def next_index(self) -> int | None:
        return next((index for index, decision in enumerate(self.decisions) if decision is None), None)

    @property
    def next_subtitle_number(self) -> int | None:
        index = self.next_index
        return None if index is None else self.snapshot.first + index

    def next_range(self, batch_size: int | None) -> tuple[int, int] | None:
        start = self.next_index
        if start is None:
            return None
        limit = self.total if batch_size is None else max(1, batch_size)
        end = start
        while end < self.total and self.decisions[end] is None and end - start < limit:
            end += 1
        return start, end

    def add_batch(self, start: int, end: int, decisions: tuple[Decision, ...],
                  provider: str, model: str) -> None:
        if not (0 <= start < end <= self.total) or len(decisions) != end - start:
            raise EditorialError("La tanda recibida no coincide con el avance guardado.")
        for offset, decision in enumerate(decisions):
            self.decisions[start + offset] = replace(decision, cue_index=start + offset)
        self.history.append({"first": self.snapshot.first + start,
                             "last": self.snapshot.first + end - 1,
                             "provider": provider,
                             "model": model,
                             "completed_at": _now()})
        self.updated_at = _now()

    def merge_proposal(self, proposal: Proposal) -> int:
        offset = snapshot_span_offset(proposal.snapshot, self.snapshot)
        if offset is None:
            raise EditorialError(
                "La propuesta guardada no coincide con ese tramo de subtítulos y cortes. No reutilicé sus resultados."
            )
        if proposal.options is None and self.options.mode != "captions":
            raise EditorialError(
                "La propuesta guardada no incluye sus opciones editoriales. No puedo confirmar que use el mismo criterio."
            )
        if proposal.options is not None and _options_signature(proposal.options) != _options_signature(self.options):
            raise EditorialError(
                "La propuesta guardada usa otra dirección editorial. Iguala sus opciones para continuar sin mezclar criterios."
            )
        if _template_signature(proposal.templates) != _template_signature(self.templates):
            raise EditorialError("La propuesta guardada usa otro catálogo de plantillas y no se puede mezclar.")
        for index, decision in enumerate(proposal.decisions):
            target = offset + index
            self.decisions[target] = replace(decision, cue_index=target)
        if proposal.decisions:
            self.history.append({"first": self.snapshot.first + offset,
                                 "last": self.snapshot.first + offset + len(proposal.decisions) - 1,
                                 "provider": "saved-proposal",
                                 "model": proposal.model,
                                 "completed_at": _now()})
        self.updated_at = _now()
        return len(proposal.decisions)

    def merge_visible_proposal(self, proposal: Proposal) -> None:
        """Persiste revisiones manuales de la tanda que el usuario tiene abierta."""
        offset = snapshot_span_offset(proposal.snapshot, self.snapshot)
        if (offset is None or len(proposal.decisions) != len(proposal.snapshot.cues)
                or len(proposal.decisions) > self.total - offset
                or _template_signature(proposal.templates) != _template_signature(self.templates)):
            raise EditorialError("La propuesta abierta ya no coincide con la tanda guardada.")
        if proposal.options is not None and _options_signature(proposal.options) != _options_signature(self.options):
            raise EditorialError("La propuesta abierta usa otras opciones editoriales.")
        for index, decision in enumerate(proposal.decisions):
            self.decisions[offset + index] = replace(decision, cue_index=offset + index)
        self.updated_at = _now()

    def batch_snapshot(self, start: int, end: int) -> Snapshot:
        first = self.snapshot.first + start
        return replace(self.snapshot, cues=self.snapshot.cues[start:end], first=first, last=first + (end - start) - 1)

    def batch_proposal(self, start: int, end: int, model: str) -> Proposal:
        batch_snapshot = self.batch_snapshot(start, end)
        decisions = tuple(replace(self.decisions[index], cue_index=index - start)
                          for index in range(start, end) if self.decisions[index] is not None)
        proposal = Proposal(batch_snapshot, self.templates, decisions, model,
                            "1.1.0" if self.options is not None else "1.0.0", self.options)
        proposal.validate()
        return proposal

    def proposal(self) -> Proposal:
        if not self.complete:
            raise EditorialError("La secuencia todavía tiene subtítulos pendientes.")
        decisions = tuple(replace(decision, cue_index=index)
                          for index, decision in enumerate(self.decisions) if decision is not None)
        distinct_models = list(dict.fromkeys(
            f"{entry['provider']}/{entry['model']}" for entry in self.history if entry.get("model")
        ))
        model = distinct_models[0] if len(distinct_models) == 1 else " + ".join(distinct_models)
        proposal = Proposal(self.snapshot, self.templates, decisions, model or "manual-direct", "1.1.0", self.options)
        proposal.validate()
        return proposal

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SESSION_VERSION,
            "snapshot": asdict(self.snapshot),
            "templates": [asdict(template) for template in self.templates],
            "options": asdict(self.options),
            "decisions": [asdict(decision) if decision is not None else None for decision in self.decisions],
            "history": self.history,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EditorialBatchRun":
        if data.get("schema_version") != SESSION_VERSION:
            raise EditorialError("La versión del avance guardado no es compatible.")
        raw = data["snapshot"]
        raw["cues"] = tuple(SubtitleCue(**cue) for cue in raw["cues"])
        raw["cuts"] = tuple(tuple(cut) for cut in raw.get("cuts", ()))
        raw["cut_source_refs"] = tuple(raw.get("cut_source_refs", ()))
        snapshot = Snapshot(**raw)
        options_data = dict(data["options"])
        options_data["resources"] = tuple(options_data.get("resources", ()))
        options = EditorialOptions(**options_data)
        decisions = [Decision(**decision) if decision is not None else None
                     for decision in data["decisions"]]
        if len(decisions) != len(snapshot.cues):
            raise EditorialError("El avance guardado no cubre el tamaño de su secuencia.")
        return cls(snapshot, tuple(Template(**template) for template in data["templates"]), options,
                   decisions, list(data.get("history", [])), str(data.get("created_at") or _now()),
                   str(data.get("updated_at") or _now()))


class EditorialBatchStore:
    """Guarda avances por contenido de secuencia, permitiendo reutilizarlos en duplicados idénticos."""

    def __init__(self, root: Path = SESSION_DIR):
        self.root = root

    def _path(self, snapshot: Snapshot, options: EditorialOptions, templates: tuple[Template, ...]) -> Path:
        return self.root / f"{_run_key(snapshot, options, templates)}.json"

    def save(self, run: EditorialBatchRun) -> Path:
        path = self._path(run.snapshot, run.options, run.templates)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(run.to_dict(), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        temporary.replace(path)
        return path

    @staticmethod
    def load(path: Path) -> EditorialBatchRun:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("invalid session")
            return EditorialBatchRun.from_dict(data)
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise EditorialError("No se pudo leer el avance guardado. Conserva el archivo para revisarlo.") from error

    def create_or_resume(self, snapshot: Snapshot, templates: tuple[Template, ...],
                         options: EditorialOptions, seed_proposal: Proposal | None = None) -> tuple[EditorialBatchRun, str]:
        path = self._path(snapshot, options, templates)
        run = None
        message = ""
        if path.is_file():
            candidate = self.load(path)
            if snapshot_span_offset(candidate.snapshot, snapshot) == 0 and len(candidate.snapshot.cues) == len(snapshot.cues):
                candidate.snapshot = snapshot
                run = candidate
                message = "Se encontró un avance guardado para esta secuencia."

        if run is None:
            run = EditorialBatchRun.empty(snapshot, templates, options)
            candidates = []
            if self.root.is_dir():
                for saved_path in self.root.glob("*.json"):
                    if saved_path == path:
                        continue
                    try:
                        candidate = self.load(saved_path)
                    except EditorialError:
                        continue
                    if (_options_signature(candidate.options) == _options_signature(options)
                            and _template_signature(candidate.templates) == _template_signature(templates)
                            and candidate.snapshot.first == snapshot.first
                            and len(candidate.snapshot.cues) <= len(snapshot.cues)
                            and snapshot_span_offset(candidate.snapshot, snapshot) == 0):
                        candidates.append(candidate)
            if candidates:
                candidate = max(candidates, key=lambda item: (item.processed, item.updated_at))
                for index, decision in enumerate(candidate.decisions):
                    if decision is not None:
                        run.decisions[index] = replace(decision, cue_index=index)
                run.history.extend(candidate.history)
                run.created_at = candidate.created_at
                message = f"Se reutilizó el avance guardado ({run.processed}/{run.total})."

        if seed_proposal is not None:
            if not message:
                message = ""
            reused = run.merge_proposal(seed_proposal)
            if reused:
                message = f"Se reutilizó la propuesta abierta ({run.processed}/{run.total})."
        self.save(run)
        return run, message


def generate_next_batch(
    run: EditorialBatchRun,
    batch_choice: str,
    provider: str,
    model: str,
    long_context_enabled: bool,
    capability: ModelCapability | None = None,
    store: EditorialBatchStore | None = None,
) -> tuple[int, int, Proposal | None]:
    """Genera, registra y guarda una tanda. Devuelve sus índices locales y, si terminó, la propuesta final."""
    if batch_choice not in BATCH_CHOICES:
        raise EditorialError("Elige una tanda de 20, 50, 100, 500 o todos los subtítulos.")
    batch_size = None if batch_choice == "all" else int(batch_choice)
    selected = run.next_range(batch_size)
    if selected is None:
        return 0, 0, run.proposal()
    start, end = selected
    provider_client = build_text_provider(provider, model)
    model_capability = capability or capability_for(provider, model)
    prompt_limit = model_capability.prompt_char_limit(long_context_enabled)
    previous = tuple(decision for decision in run.decisions[:start] if decision is not None)[-2:]
    decisions = propose_batch(run.snapshot, run.templates, provider_client, start, end,
                              run.options, previous, prompt_limit)
    run.add_batch(start, end, decisions, provider, model)
    (store or EditorialBatchStore()).save(run)
    final_proposal = run.proposal() if run.complete else None
    return start, end, final_proposal
