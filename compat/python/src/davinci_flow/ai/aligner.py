"""Motor de alineación con guion original, corrección de subtítulos y detección de marcadores."""

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from davinci_flow.ai.credentials import has_gemini_api_key
from davinci_flow.ai.client import GeminiClient
from davinci_flow.errors import ScriptAlignmentError
from davinci_flow.subtitles.model import SubtitleCue

@dataclass(frozen=True, slots=True)
class TimelineMarker:
    """Marcador para colocar en la línea de tiempo de DaVinci Resolve."""

    frame: float
    color: str = "Cyan"
    name: str = "Punto Clave"
    note: str = ""
    duration: int = 1

    def __post_init__(self) -> None:
        if self.frame < 0:
            raise ValueError("El fotograma del marcador no puede ser negativo.")


@dataclass(frozen=True, slots=True)
class CorrectionItem:
    """Detalle de una corrección individual aplicada sobre un bloque de subtítulo."""

    index: int
    start_frame: float
    end_frame: float
    original_text: str
    corrected_text: str
    reason: str = "Alineación contextual"
    is_modified: bool = True


@dataclass(frozen=True, slots=True)
class CorrectionResult:
    """Resultado integral del proceso de alineación y corrección con IA."""

    corrected_cues: tuple[SubtitleCue, ...]
    corrections: tuple[CorrectionItem, ...]
    markers: tuple[TimelineMarker, ...]
    summary: str = ""

    @property
    def total_corrections(self) -> int:
        """Cantidad de subtítulos modificados."""
        return sum(1 for c in self.corrections if c.is_modified)

    @property
    def total_markers(self) -> int:
        """Cantidad de marcadores sugeridos."""
        return len(self.markers)


def apply_glossary_to_text(text: str, glossary: dict[str, str]) -> tuple[str, list[str]]:
    """Aplica sustituciones directas e insensibles a mayúsculas desde un glosario de términos evitando duplicaciones."""
    modified_text = text
    applied_changes: list[str] = []
    for term, replacement in glossary.items():
        t_clean = term.strip()
        r_clean = replacement.strip()
        if not t_clean or not r_clean:
            continue

        pattern = re.compile(rf"\b{re.escape(t_clean)}\b", re.IGNORECASE)

        def _replace_match(m: re.Match[str]) -> str:
            start, end = m.span()
            matched_str = m.group(0)
            if matched_str == r_clean:
                return matched_str
            if r_clean.lower().startswith(matched_str.lower()):
                suffix_needed = r_clean[len(matched_str):]
                remaining_text = modified_text[end:]
                if remaining_text.startswith(suffix_needed):
                    return r_clean[:len(matched_str)]
            return r_clean

        new_text = pattern.sub(_replace_match, modified_text)
        if new_text != modified_text:
            applied_changes.append(f"Glosario: '{t_clean}' -> '{r_clean}'")
            modified_text = new_text

    return modified_text, applied_changes


def parse_glossary_str(text: str) -> dict[str, str]:
    """Parsea una cadena de pares clave:valor o JSON a un diccionario de glosario."""
    if not text or not text.strip():
        return {}
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            data = json.loads(stripped)
            if isinstance(data, dict):
                return {str(k).strip(): str(v).strip() for k, v in data.items() if str(k).strip()}
        except Exception:
            pass

    glossary: dict[str, str] = {}
    items = re.split(r"[\n,]+", stripped)
    for item in items:
        if ":" in item:
            parts = item.split(":", 1)
            k, v = parts[0].strip(), parts[1].strip()
            if k:
                glossary[k] = v
        elif "->" in item:
            parts = item.split("->", 1)
            k, v = parts[0].strip(), parts[1].strip()
            if k:
                glossary[k] = v
    return glossary


_CLIENT_DEFAULT = object()


class ScriptAligner:
    """Orquesta la comparación del texto transcrito contra el guion original y glosarios con Gemini."""

    def __init__(
        self,
        client: Any = _CLIENT_DEFAULT,
        api_key: str | None = None,
        model_name: str | None = None,
    ) -> None:
        if client is not _CLIENT_DEFAULT:
            self._client = client
        elif api_key:
            self._client = GeminiClient(api_key=api_key, model_name=model_name or "gemini-3.6-flash")
        elif has_gemini_api_key():
            self._client = GeminiClient(model_name=model_name or "gemini-3.6-flash")
        else:
            self._client = None

    def align_and_correct(
        self,
        cues: Sequence[SubtitleCue],
        original_script: str = "",
        glossary: dict[str, str] | None = None,
        detect_markers: bool = True,
        progress_callback: Any | None = None,
        chunk_size: int = 50,
    ) -> CorrectionResult:
        """Compara los subtítulos con el guion, corrige errores/jergas y genera marcadores en lotes con progreso."""
        if not cues:
            return CorrectionResult(
                corrected_cues=(),
                corrections=(),
                markers=(),
                summary="No hay subtítulos para procesar.",
            )

        active_glossary = glossary or {}
        script_text = (original_script or "").strip()

        # Si no hay cliente Gemini configurado o no hay guion/IA, aplicar glosario básico local
        if self._client is None and not script_text and not active_glossary:
            return CorrectionResult(
                corrected_cues=tuple(cues),
                corrections=(),
                markers=(),
                summary="Sin cambios: no se proporcionó guion ni API Key de Gemini.",
            )

        # Si no hay cliente pero hay glosario, aplicar reemplazos locales deterministas
        if self._client is None:
            updated_cues: list[SubtitleCue] = []
            correction_items: list[CorrectionItem] = []
            for idx, cue in enumerate(cues, start=1):
                new_text, changes = apply_glossary_to_text(cue.text, active_glossary)
                is_changed = new_text != cue.text
                updated_cues.append(
                    SubtitleCue(
                        text=new_text,
                        start_frame=cue.start_frame,
                        end_frame=cue.end_frame,
                        track_index=cue.track_index,
                    )
                )
                if is_changed:
                    correction_items.append(
                        CorrectionItem(
                            index=idx,
                            start_frame=cue.start_frame,
                            end_frame=cue.end_frame,
                            original_text=cue.text,
                            corrected_text=new_text,
                            reason=", ".join(changes),
                            is_modified=True,
                        )
                    )
            return CorrectionResult(
                corrected_cues=tuple(updated_cues),
                corrections=tuple(correction_items),
                markers=(),
                summary=f"Glosario aplicado localmente: {len(correction_items)} corrección(es).",
            )

        # Procesamiento con Gemini: Si la cantidad de subtítulos es pequeña, procesar de una vez
        total_cues = len(cues)
        if total_cues <= chunk_size:
            if progress_callback:
                progress_callback(0, total_cues, f"Alineando {total_cues} subtítulos con IA...")
            res = self._align_with_gemini(
                cues=cues,
                script_text=script_text,
                glossary=active_glossary,
                detect_markers=detect_markers,
                start_index=1,
            )
            if progress_callback:
                progress_callback(total_cues, total_cues, "Alineación con IA completada.")
            return res

        # Procesamiento por lotes (chunks) para transcripciones largas
        import math
        total_chunks = math.ceil(total_cues / chunk_size)
        all_corrected_cues: list[SubtitleCue] = []
        all_corrections: list[CorrectionItem] = []
        all_markers: list[TimelineMarker] = []

        for chunk_idx in range(total_chunks):
            start_i = chunk_idx * chunk_size
            end_i = min(start_i + chunk_size, total_cues)
            chunk_cues = cues[start_i:end_i]

            if progress_callback:
                progress_callback(
                    start_i,
                    total_cues,
                    f"Alineando con IA: lote {chunk_idx + 1}/{total_chunks} (subtítulos {start_i + 1} a {end_i} de {total_cues})...",
                )

            chunk_res = self._align_with_gemini(
                cues=chunk_cues,
                script_text=script_text,
                glossary=active_glossary,
                detect_markers=detect_markers,
                start_index=start_i + 1,
            )
            all_corrected_cues.extend(chunk_res.corrected_cues)
            all_corrections.extend(chunk_res.corrections)
            all_markers.extend(chunk_res.markers)

        if progress_callback:
            progress_callback(total_cues, total_cues, f"Alineación con IA completada ({len(all_corrections)} correcciones).")

        return CorrectionResult(
            corrected_cues=tuple(all_corrected_cues),
            corrections=tuple(all_corrections),
            markers=tuple(all_markers),
            summary=f"Alineación por lotes ({total_chunks} lotes): {len(all_corrections)} corrección(es) y {len(all_markers)} marcador(es).",
        )

    def _align_with_gemini(
        self,
        cues: Sequence[SubtitleCue],
        script_text: str,
        glossary: dict[str, str],
        detect_markers: bool,
        start_index: int = 1,
    ) -> CorrectionResult:
        """Construye el prompt estructurado y procesa la respuesta JSON de Gemini."""
        if self._client is None:
            raise ScriptAlignmentError("Cliente de Gemini no inicializado.")

        cues_payload = [
            {
                "index": start_index + idx,
                "start_frame": cue.start_frame,
                "end_frame": cue.end_frame,
                "text": cue.text,
            }
            for idx, cue in enumerate(cues)
        ]

        system_instruction = (
            "Eres un asistente editorial experto en postproducción de vídeo y subtitulado en DaVinci Resolve. "
            "Tu tarea es analizar los subtítulos transcritos automáticamente por DaVinci Resolve, compararlos "
            "con el guion original del creador y con un glosario de marcas/jergas, y producir subtítulos 100% "
            "fieles, limpios y gramaticalmente correctos.\n"
            "Reglas críticas:\n"
            "1. Mantén intacto el índice (index), start_frame y end_frame de cada subtítulo.\n"
            "2. Corrige palabras mal transcritas, errores de homofonía, ortografía, jerga mal interpretada o palabras soeces mal captadas.\n"
            "3. Aplica estrictamente las marcas y términos del glosario con la ortografía y mayúsculas exactas.\n"
            "4. Si detect_markers es verdadero, detecta puntos clave importantes en la narrativa y propón marcadores para la línea de tiempo con colores de Resolve ('Blue' para capítulos/secciones, 'Yellow' para puntos clave/conclusiones, 'Green' para eventos de sonido/SFX, 'Cyan' para preguntas, 'Magenta' para correcciones/glosario, 'Pink' para llamadas a la acción).\n"
            "5. Tu respuesta DEBE ser estrictamente un JSON válido con la estructura solicitada."
        )

        prompt_dict = {
            "task": "align_and_correct_subtitles",
            "detect_markers": detect_markers,
            "original_script": script_text if script_text else "(No proporcionado, usar contexto y glosario)",
            "glossary": glossary,
            "subtitles": cues_payload,
            "expected_json_structure": {
                "aligned_cues": [
                    {
                        "index": 1,
                        "corrected_text": "texto corregido",
                        "changed": True,
                        "reason": "motivo de la corrección o 'Sin cambios'",
                    }
                ],
                "markers": [
                    {
                        "frame": 120.0,
                        "color": "Cyan",
                        "name": "Título de punto clave",
                        "note": "Nota explicativa",
                    }
                ],
                "summary": "Resumen conciso de las mejoras aplicadas",
            },
        }

        import json

        prompt = (
            "Analiza y corrige los siguientes subtítulos según las instrucciones:\n"
            f"```json\n{json.dumps(prompt_dict, ensure_ascii=False, indent=2)}\n```"
        )

        try:
            response_json = self._client.generate_json(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.15,
            )
        except Exception as err:
            raise ScriptAlignmentError(f"Fallo al alinear subtítulos con Gemini: {err}") from err

        if not isinstance(response_json, dict):
            raise ScriptAlignmentError("Respuesta inesperada de Gemini: se esperaba un objeto JSON.")

        raw_aligned = response_json.get("aligned_cues", [])
        aligned_map: dict[int, dict[str, Any]] = {}
        if isinstance(raw_aligned, list):
            for item in raw_aligned:
                if isinstance(item, dict) and "index" in item:
                    try:
                        aligned_map[int(item["index"])] = item
                    except (ValueError, TypeError):
                        pass

        # Reconstruir lista de SubtitleCue y correcciones
        corrected_cues_list: list[SubtitleCue] = []
        correction_items_list: list[CorrectionItem] = []

        for idx, cue in enumerate(cues):
            current_index = start_index + idx
            ai_item = aligned_map.get(current_index)
            corrected_text = cue.text
            reason = "Sin cambios"
            is_changed = False

            if ai_item:
                c_text = str(ai_item.get("corrected_text", "")).strip()
                if c_text:
                    corrected_text = c_text
                reason = str(ai_item.get("reason", "Alineación con guion"))
                is_changed = bool(ai_item.get("changed", corrected_text != cue.text))

            # Aplicar glosario como garantía de seguridad adicional
            if glossary:
                glossary_text, g_changes = apply_glossary_to_text(corrected_text, glossary)
                if glossary_text != corrected_text:
                    corrected_text = glossary_text
                    is_changed = True
                    reason = f"{reason} | {', '.join(g_changes)}" if reason != "Sin cambios" else ", ".join(g_changes)

            corrected_cues_list.append(
                SubtitleCue(
                    text=corrected_text,
                    start_frame=cue.start_frame,
                    end_frame=cue.end_frame,
                    track_index=cue.track_index,
                )
            )

            if is_changed or corrected_text != cue.text:
                correction_items_list.append(
                    CorrectionItem(
                        index=current_index,
                        start_frame=cue.start_frame,
                        end_frame=cue.end_frame,
                        original_text=cue.text,
                        corrected_text=corrected_text,
                        reason=reason,
                        is_modified=True,
                    )
                )

        # Parsear marcadores si fueron solicitados
        markers_list: list[TimelineMarker] = []
        if detect_markers:
            raw_markers = response_json.get("markers", [])
            if isinstance(raw_markers, list):
                for rm in raw_markers:
                    if isinstance(rm, dict) and "frame" in rm:
                        try:
                            f_val = float(rm["frame"])
                            color_val = str(rm.get("color", "Cyan")).capitalize()
                            valid_colors = {
                                "Blue", "Cyan", "Green", "Yellow", "Red", "Pink",
                                "Purple", "Fuchsia", "Rose", "Lavender", "Sky", "Mint",
                            }
                            if color_val not in valid_colors:
                                color_val = "Cyan"
                            markers_list.append(
                                TimelineMarker(
                                    frame=f_val,
                                    color=color_val,
                                    name=str(rm.get("name", "Punto Clave")),
                                    note=str(rm.get("note", "")),
                                    duration=int(rm.get("duration", 1)),
                                )
                            )
                        except (ValueError, TypeError):
                            continue

        summary_text = str(
            response_json.get(
                "summary",
                f"Alineación completada: {len(correction_items_list)} corrección(es) y {len(markers_list)} marcador(es).",
            )
        )

        return CorrectionResult(
            corrected_cues=tuple(corrected_cues_list),
            corrections=tuple(correction_items_list),
            markers=tuple(markers_list),
            summary=summary_text,
        )
