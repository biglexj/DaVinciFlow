"""Autocorrector de subtítulos.

El corrector trabaja por etapas y **reporta cada una por separado**, para no dejar
confundido un cambio hecho por reglas locales con uno propuesto por el modelo:

1. ``normalizacion``: limpieza determinista (espacios, tildes, signos de puntuación).
2. ``glosario``: sustituciones literales de los términos del guion.
3. ``ia``: corrección de errores de transcripción propuesta por el proveedor de IA.

Las etapas 1 y 2 nunca reescriben el sentido del texto. La etapa 3 es la única que
puede alterar las palabras y, si el modelo no devuelve una respuesta utilizable, la
operación se cancela completa: nunca se aplica una corrección a medias sin avisar.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Sequence

from davinci_flow.ai.aligner import apply_glossary_to_text, parse_glossary_str
from davinci_flow.ai.providers.base import TextProvider
from davinci_flow.errors import AutocorrectError
from davinci_flow.subtitles.model import SubtitleCue
from davinci_flow.subtitles.normalizer import normalize_subtitle_text

NORMALIZATION_STAGE = "normalizacion"
GLOSSARY_STAGE = "glosario"
AI_STAGE = "ia"

DEFAULT_BATCH_SIZE = 20
MAX_BATCH_SIZE = 30

SYSTEM_INSTRUCTION = (
    "Eres un corrector de subtítulos en español. Corrijas únicamente errores de "
    "transcripción: palabras mal escritas, homófonos, falta de tildes, mayúsculas "
    "iniciales, puntuación mal puesta y palabras cortadas. No reescas, no resumas, "
    "no cambies el sentido, no traduzcas, no cambies nombres propios ni cifras, y no "
    "añadas ni elimines información. Si una línea ya está correcta, devuélvela igual."
)


@dataclass(frozen=True, slots=True)
class AutocorrectChange:
    """Cambio aplicado sobre un subtítulo, con las etapas que lo produjeron."""

    index: int
    original: str
    corrected: str
    stages: tuple[str, ...]

    @property
    def is_modified(self) -> bool:
        return self.original != self.corrected


@dataclass(frozen=True, slots=True)
class AutocorrectResult:
    """Resultado del autocorrector sobre un lote de subtítulos."""

    cues: tuple[SubtitleCue, ...]
    changes: tuple[AutocorrectChange, ...]
    stages_applied: tuple[str, ...]
    ai_status: str = "skipped"
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def modified_count(self) -> int:
        return sum(1 for change in self.changes if change.is_modified)

    @property
    def unchanged_count(self) -> int:
        return len(self.changes) - self.modified_count

    def summary(self) -> dict[str, Any]:
        """Resumen serializable del resultado."""
        return {
            "cues": len(self.cues),
            "modificados": self.modified_count,
            "sin_cambios": self.unchanged_count,
            "etapas": list(self.stages_applied),
            "estado_ia": self.ai_status,
            "notas": list(self.notes),
        }


class SubtitleAutocorrector:
    """Corrige subtítulos combinando reglas deterministas y un proveedor de IA."""

    def __init__(
        self,
        provider: TextProvider | None = None,
        glossary: dict[str, str] | str | None = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self.provider = provider
        self.glossary = parse_glossary_str(glossary) if isinstance(glossary, str) else dict(glossary or {})
        if not 1 <= batch_size <= MAX_BATCH_SIZE:
            raise AutocorrectError(f"El lote debe tener entre 1 y {MAX_BATCH_SIZE} subtítulos.")
        self.batch_size = batch_size

    def correct(
        self,
        cues: Sequence[SubtitleCue],
        use_ai: bool = True,
        apply_normalization: bool = True,
    ) -> AutocorrectResult:
        """Corrige una secuencia de subtítulos y devuelve el resultado con su diff."""
        if not cues:
            raise AutocorrectError("No hay subtítulos que corregir.")

        stages: list[str] = []
        notes: list[str] = []
        texts = [cue.text for cue in cues]
        snapshots: list[tuple[str, tuple[str, ...]]] = [(text, ()) for text in texts]

        if apply_normalization:
            normalized = [self._normalize(text) for text in texts]
            texts = normalized
            snapshots = self._record_stage(snapshots, texts, NORMALIZATION_STAGE)
            stages.append(NORMALIZATION_STAGE)

        if self.glossary:
            replaced: list[str] = []
            for text in texts:
                corrected, applied = apply_glossary_to_text(text, self.glossary)
                if applied:
                    notes.append(f"Glosario: {len(applied)} término(s) sustituido(s).")
                replaced.append(corrected)
            texts = replaced
            snapshots = self._record_stage(snapshots, texts, GLOSSARY_STAGE)
            stages.append(GLOSSARY_STAGE)

        ai_status = "skipped"
        if use_ai:
            if self.provider is None:
                raise AutocorrectError(
                    "Se pidió corrección con IA pero no hay un proveedor configurado."
                )
            texts = self._correct_with_ai(texts)
            snapshots = self._record_stage(snapshots, texts, AI_STAGE)
            stages.append(AI_STAGE)
            ai_status = "ok"

        corrected_cues = tuple(
            SubtitleCue(
                text=text,
                start_frame=cue.start_frame,
                end_frame=cue.end_frame,
                track_index=cue.track_index,
            )
            for cue, text in zip(cues, texts)
        )

        changes = tuple(
            AutocorrectChange(
                index=index,
                original=cue.text,
                corrected=corrected.text,
                stages=snapshots[index][1],
            )
            for index, (cue, corrected) in enumerate(zip(cues, corrected_cues))
        )

        return AutocorrectResult(
            cues=corrected_cues,
            changes=changes,
            stages_applied=tuple(stages),
            ai_status=ai_status,
            notes=tuple(notes),
        )

    @staticmethod
    def _record_stage(
        snapshots: list[tuple[str, tuple[str, ...]]],
        texts: list[str],
        stage: str,
    ) -> list[tuple[str, tuple[str, ...]]]:
        """Anota en qué etapas cambió el texto de cada subtítulo."""
        updated: list[tuple[str, tuple[str, ...]]] = []
        for (previous, applied), text in zip(snapshots, texts):
            stages = applied + ((stage,) if text != previous else ())
            updated.append((text, stages))
        return updated

    def _normalize(self, text: str) -> str:
        """Normaliza un texto; si la limpieza lo deja vacío, conserva el original."""
        try:
            return normalize_subtitle_text(text)
        except Exception:
            return text

    def _correct_with_ai(self, texts: list[str]) -> list[str]:
        """Pide al modelo una corrección por lotes y valida cada respuesta."""
        assert self.provider is not None
        corrected = list(texts)

        for start in range(0, len(corrected), self.batch_size):
            end = min(start + self.batch_size, len(corrected))
            batch = corrected[start:end]
            payload = self._request_batch(batch, start)
            corrected[start:end] = payload

        return corrected

    def _request_batch(self, batch: list[str], offset: int) -> list[str]:
        """Solicita un lote al modelo y valida que devuelva exactamente los índices pedidos."""
        assert self.provider is not None
        lines = "\n".join(
            f"{offset + position}: {text}" for position, text in enumerate(batch)
        )
        prompt = (
            "Corrige estas líneas de subtítulo y devuelve un JSON con la forma "
            '{"correcciones": [{"indice": <numero>, "texto": "<texto corregido>"}]}. '
            "Devuelve exactamente una entrada por línea, con el mismo índice y el mismo "
            f"orden. Si una línea no tiene errores, devuelve su texto sin cambios.\n\n{lines}"
        )

        last_error: Exception | None = None
        for attempt in range(2):
            try:
                raw = self.provider.generate_json(
                    prompt, system_instruction=SYSTEM_INSTRUCTION, temperature=0.0
                )
                return self._read_corrections(raw, batch, offset)
            except (AutocorrectError, ValueError, TypeError, AttributeError) as err:
                last_error = err
                if attempt == 1:
                    break
                prompt += (
                    "\n\nTu respuesta anterior no era válida. Devuelve solo el JSON "
                    '{"correcciones": [{"indice": ..., "texto": "..."}]} sin explicaciones.'
                )

        raise AutocorrectError(
            "El proveedor de IA no devolvió una corrección utilizable; "
            f"no se aplicó ningún cambio. Detalle: {last_error}"
        ) from last_error

    def _read_corrections(self, raw: Any, batch: list[str], offset: int) -> list[str]:
        """Valida la respuesta del modelo y devuelve los textos corregidos del lote."""
        if isinstance(raw, str):
            raise AutocorrectError("El proveedor devolvió texto donde se esperaba JSON.")
        if isinstance(raw, dict):
            entries = raw.get("correcciones")
            if entries is None:
                entries = raw.get("corrections")
        elif isinstance(raw, list):
            entries = raw
        else:
            entries = None

        if not isinstance(entries, list):
            raise AutocorrectError("El proveedor no devolvió la lista de correcciones esperada.")

        by_index: dict[int, str] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                raise AutocorrectError("Una corrección del proveedor tiene un formato inválido.")
            try:
                index = int(entry.get("indice", entry.get("index")))
            except (TypeError, ValueError) as err:
                raise AutocorrectError("Una corrección del proveedor tiene un índice inválido.") from err
            text = entry.get("texto", entry.get("text"))
            if not isinstance(text, str) or not text.strip():
                raise AutocorrectError("Una corrección del proveedor llegó sin texto.")
            by_index[index] = text.strip()

        expected = list(range(offset, offset + len(batch)))
        if sorted(by_index) != expected:
            raise AutocorrectError(
                "El proveedor no devolvió exactamente los índices solicitados "
                f"({sorted(by_index)} en lugar de {expected})."
            )

        return [by_index[index] for index in expected]


def apply_result(result: AutocorrectResult) -> tuple[SubtitleCue, ...]:
    """Devuelve los subtítulos corregidos (alias explícito para el llamador)."""
    return result.cues


def corrections_to_json(result: AutocorrectResult) -> str:
    """Serializa el diff del autocorrector en JSON legible."""
    payload = {
        "resumen": result.summary(),
        "cambios": [
            {
                "indice": change.index,
                "original": change.original,
                "corregido": change.corrected,
                "etapas": list(change.stages),
            }
            for change in result.changes
            if change.is_modified
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
