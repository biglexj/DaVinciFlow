"""Contrato editorial versionado y validación antes de escribir en Resolve."""

from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from davinci_flow.errors import DaVinciFlowError
from davinci_flow.generation.plan import GenerationPlan, build_generation_plan
from davinci_flow.subtitles.model import SubtitleCue


class EditorialError(DaVinciFlowError):
    """La propuesta no puede aplicarse con garantías."""


def digest(data: Any) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Template:
    id: str
    name: str
    source: str  # installed_file o media_pool
    locator: str
    text_tool: str = ""
    fingerprint: str = ""
    text_input: str = "StyledText"

    def __post_init__(self) -> None:
        if self.source not in ("installed_file", "installed_archive", "media_pool") or not all(
            isinstance(v, str) and v.strip() for v in (self.id, self.name, self.locator)
        ):
            raise EditorialError("Descriptor de plantilla inválido.")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", self.id):
            raise EditorialError("ID de plantilla inválido.")


@dataclass(frozen=True)
class Snapshot:
    project: str
    timeline: str
    timeline_id: str | None
    fps: float
    width: int
    height: int
    origin: int
    track: int
    cues: tuple[SubtitleCue, ...]
    cuts: tuple[tuple, ...] = ()
    source: str = "resolve"
    first: int = 1
    last: int = 120
    project_id: str = ""

    def __post_init__(self) -> None:
        if self.source not in ("resolve", "srt") or not self.cues:
            raise EditorialError("La fuente debe contener subtítulos.")
        if not math.isfinite(self.fps) or self.fps <= 0 or min(self.width, self.height, self.track) < 1:
            raise EditorialError("FPS, resolución o pista inválidos.")
        previous_end = -1.0
        for cue in self.cues:
            if not all(math.isfinite(v) for v in (cue.start_frame, cue.end_frame)):
                raise EditorialError("Los tiempos deben ser finitos.")
            if cue.start_frame < previous_end or cue.end_frame <= cue.start_frame:
                raise EditorialError("Revisa los subtítulos solapados, desordenados o sin duración.")
            previous_end = cue.end_frame

    @property
    def fingerprint(self) -> str:
        return digest(asdict(self))


@dataclass(frozen=True)
class Decision:
    cue_index: int
    context: str
    main: str
    accent: str
    templates: dict[str, str]
    reason: str
    enabled: bool = True
    reviewed: bool = False
    edit_note: str = ""
    visual_note: str = ""
    resource_id: str = ""


@dataclass(frozen=True)
class EditorialOptions:
    mode: str = "highlights"
    format: str = "auto"
    density: str = "balanced"
    direction: str = ""
    resources: tuple[dict, ...] = ()

    def validate(self) -> None:
        if self.mode not in ("highlights", "captions") or self.format not in ("auto", "horizontal", "vertical"):
            raise EditorialError("Modo o formato editorial inválido.")
        if self.density not in ("sparse", "balanced", "dense") or not isinstance(self.direction, str) or len(self.direction) > 4000:
            raise EditorialError("Densidad o dirección creativa inválida.")
        if len(self.resources) > 80 or any(not isinstance(r, dict) or set(r) != {"id", "name", "category"}
                or not all(isinstance(v, str) and 0 < len(v) <= 250 for v in r.values()) for r in self.resources):
            raise EditorialError("Contexto de biblioteca inválido.")
        if len({r["id"] for r in self.resources}) != len(self.resources):
            raise EditorialError("Recursos duplicados en la propuesta.")


def is_grounded_excerpt(original: str, selected: str) -> bool:
    """Permite selección y mayúsculas; impide inventar palabras o perder negaciones."""
    tokenize = lambda text: re.findall(r"\w+", text.casefold())
    source, output = tokenize(original), tokenize(selected)
    remaining = iter(source)
    if not output or not all(any(word == candidate for candidate in remaining) for word in output):
        return False
    return all(output.count(word) >= source.count(word) for word in ("no", "nunca", "jamás", "sin", "tampoco", "ni"))


@dataclass(frozen=True)
class Proposal:
    snapshot: Snapshot
    templates: tuple[Template, ...]
    decisions: tuple[Decision, ...]
    model: str
    version: str = "1.0.0"
    options: EditorialOptions | None = None

    def validate(self, require_review: bool = False) -> None:
        if self.version not in ("1.0.0", "1.1.0"):
            raise EditorialError(f"Versión editorial no soportada: {self.version}.")
        if self.version == "1.1.0":
            if not isinstance(self.options, EditorialOptions):
                raise EditorialError("Faltan las opciones editoriales.")
            self.options.validate()
        elif self.options is not None:
            raise EditorialError("Las opciones requieren el contrato 1.1.0.")
        selective = self.options is not None and self.options.mode == "highlights"
        if not isinstance(self.model, str) or not self.model.strip():
            raise EditorialError("Falta el modelo que produjo la propuesta.")
        catalog = {t.id: t for t in self.templates}
        if len(catalog) != len(self.templates) or not catalog:
            raise EditorialError("Catálogo vacío o IDs de plantilla duplicados.")
        if len(self.decisions) != len(self.snapshot.cues):
            raise EditorialError("La propuesta debe cubrir todos los subtítulos exactamente una vez.")
        for index, (decision, cue) in enumerate(zip(self.decisions, self.snapshot.cues)):
            if type(decision.cue_index) is not int or decision.cue_index != index:
                raise EditorialError("Índice de subtítulo duplicado, ausente o fuera de orden.")
            if any(type(getattr(decision, k)) is not bool for k in ("enabled", "reviewed")):
                raise EditorialError("Los estados de revisión deben ser booleanos.")
            texts = (decision.context, decision.main, decision.accent)
            if not all(isinstance(t, str) for t in texts) or (not decision.main.strip() and (decision.enabled or not selective)):
                raise EditorialError("Cada bloque debe tener un texto principal.")
            reconstructed = " ".join(" ".join(texts).split())
            if not isinstance(decision.edit_note, str) or not isinstance(decision.reason, str):
                raise EditorialError("Motivo editorial o nota de edición inválidos.")
            covered = (is_grounded_excerpt(cue.text, reconstructed) if selective else reconstructed == " ".join(cue.text.split()))
            if selective and not decision.enabled and not reconstructed:
                covered = True
            if not covered and not decision.edit_note.strip():
                raise EditorialError(f"Bloque {index + 1}: se alteró el texto; corrige la cobertura o registra el motivo de edición manual.")
            if self.options is not None:
                if not decision.reason.strip() or not isinstance(decision.visual_note, str) or not isinstance(decision.resource_id, str):
                    raise EditorialError("Falta el motivo editorial o la intención visual es inválida.")
                if decision.resource_id and decision.resource_id not in {r["id"] for r in self.options.resources}:
                    raise EditorialError("La LLM recomendó un recurso que no está en la biblioteca compartida.")
            if not isinstance(decision.templates, dict):
                raise EditorialError("Las plantillas deben asignarse por capa.")
            active = {r for r in ("context", "main", "accent") if getattr(decision, r).strip()}
            if set(decision.templates) != active or any(not isinstance(t, str) or t not in catalog for t in decision.templates.values()):
                raise EditorialError(f"Bloque {index + 1}: falta una plantilla válida para cada capa activa.")
            if require_review and not decision.reviewed:
                raise EditorialError(f"Revisa el bloque {index + 1} antes de aplicar.")

    @property
    def revision(self) -> str:
        return digest(self.to_dict())

    def to_dict(self) -> dict:
        data = asdict(self)
        if self.version == "1.0.0":
            data.pop("options")
            for decision in data["decisions"]:
                decision.pop("visual_note")
                decision.pop("resource_id")
        return data

    def edit(self, index: int, **changes: Any) -> "Proposal":
        if not 0 <= index < len(self.decisions):
            raise EditorialError("Bloque inexistente.")
        decisions = list(self.decisions)
        changes.setdefault("reviewed", False)
        decisions[index] = replace(decisions[index], **changes)
        result = replace(self, decisions=tuple(decisions))
        result.validate()
        return result

    def save(self, path: str | Path) -> None:
        self.validate()
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2,
                                        allow_nan=False), encoding="utf-8")
        temporary.replace(target)

    @classmethod
    def load(cls, path: str | Path) -> "Proposal":
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            fields = {"snapshot", "templates", "decisions", "model", "version"}
            if isinstance(data, dict) and data.get("version") == "1.1.0":
                fields.add("options")
            if not isinstance(data, dict) or set(data) != fields:
                raise EditorialError("El archivo no corresponde al contrato editorial.")
            options = None
            if "options" in data:
                data["options"]["resources"] = tuple(data["options"].get("resources", ()))
                options = EditorialOptions(**data["options"])
            raw = data["snapshot"]
            raw["cues"] = tuple(SubtitleCue(**c) for c in raw["cues"])
            raw["cuts"] = tuple(tuple(c) for c in raw.get("cuts", []))
            result = cls(Snapshot(**raw), tuple(Template(**t) for t in data["templates"]),
                         tuple(Decision(**d) for d in data["decisions"]), data["model"], data["version"], options)
            result.validate()
            return result
        except (ValueError, KeyError, TypeError) as error:
            raise EditorialError("Archivo editorial inválido o incompatible.") from error

    def generation_plan(self) -> GenerationPlan:
        """Adapta al contrato anterior sin alterar su esquema ni volver a llamar a la IA."""
        self.validate(require_review=True)
        s = self.snapshot
        base = build_generation_plan(s.project, s.timeline, s.cues, track_index=s.track,
                                     timeline_id=s.timeline_id, fps=s.fps, width=s.width, height=s.height)
        blocks = []
        for original, decision in zip(base.blocks, self.decisions):
            blocks.append(replace(original, context_text=decision.context or None,
                                  # El contrato antiguo exige texto aun en bloques desactivados.
                                  main_text=decision.main or original.main_text, accent_text=decision.accent or None,
                                  reason=decision.reason, is_enabled=decision.enabled,
                                  sfx_proposal=None))
        return replace(base, plan_id="editorial_" + self.revision[:24], blocks=tuple(blocks))
