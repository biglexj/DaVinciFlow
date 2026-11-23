"""Clasificador semántico determinista de capas para subtítulos en español."""

import re
from dataclasses import dataclass
from typing import Sequence

from davinci_flow.subtitles.block import CaptionBlock
from davinci_flow.subtitles.model import SubtitleCue
from davinci_flow.subtitles.normalizer import normalize_subtitle_text

# Conectores y frases introductorias comunes en español (ordenados de mayor a menor longitud)
_INTRO_CONNECTORS = (
    "en primer lugar,",
    "en segundo lugar,",
    "en tercer lugar,",
    "por otra parte,",
    "por otro lado,",
    "por consiguiente,",
    "por lo tanto,",
    "de igual manera,",
    "de hecho,",
    "en realidad,",
    "por ejemplo,",
    "sin embargo,",
    "en resumen,",
    "es decir,",
    "por cierto,",
    "en este caso,",
    "para empezar,",
    "como resultado,",
    "mientras tanto,",
    "en consecuencia,",
    "en cambio,",
    "o sea,",
    "por ende,",
    "de todos modos,",
    "de cualquier forma,",
    "en pocas palabras,",
    "en primer lugar",
    "en segundo lugar",
    "por otra parte",
    "por otro lado",
    "por consiguiente",
    "por lo tanto",
    "de hecho",
    "en realidad",
    "por ejemplo",
    "sin embargo",
    "en resumen",
    "es decir",
    "por cierto",
    "en este caso",
    "para empezar",
    "como resultado",
    "mientras tanto",
    "en consecuencia",
    "en cambio",
    "o sea",
    "por ende",
    "además,",
    "entonces,",
    "finalmente,",
    "obviamente,",
    "claramente,",
    "naturalmente,",
    "afortunadamente,",
    "lamentablemente,",
    "generalmente,",
    "actualmente,",
    "personalmente,",
    "básicamente,",
    "simplemente,",
    "pero,",
    "aunque,",
    "cuando,",
    "si bien,",
    "además",
    "entonces",
    "finalmente",
    "obviamente",
)

# Patrón para detectar preguntas
_QUESTION_PATTERN = re.compile(r"(¿|.*\?\s*$)")
# Patrón para detectar exclamaciones
_EXCLAMATION_PATTERN = re.compile(r"(¡|.*!\s*$)")
# Patrón para detectar negaciones enfáticas
_NEGATION_PATTERN = re.compile(r"\b(no|nunca|jamás|tampoco|ningún|ninguna|nada)\b", re.IGNORECASE)
# Patrón para detectar cifras, porcentajes o monedas
_NUMERIC_PATTERN = re.compile(r"(\b\d+([.,]\d+)*%?|\$\d+|\b\d+\s+(mil|millones|billones)\b)", re.IGNORECASE)
# Patrón para detectar entrecomillados
_QUOTED_PATTERN = re.compile(r'("[^"]+"|\«[^\»]+\»|\'[^\']+\')')


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    """Resultado del desglose determinista de un texto en roles visuales."""

    normalized_text: str
    main_text: str
    context_text: str | None = None
    accent_text: str | None = None
    intent: str = "statement"
    confidence: float = 1.0
    reason: str = "Asignación directa."


def _detect_intent(text: str) -> str:
    """Determina la intención comunicativa dominante."""
    if _QUESTION_PATTERN.search(text):
        return "question"
    if _EXCLAMATION_PATTERN.search(text):
        return "exclamation"
    if _NEGATION_PATTERN.search(text):
        return "negation"
    if _NUMERIC_PATTERN.search(text) or _QUOTED_PATTERN.search(text):
        return "emphasis"
    return "statement"


def classify_text_layers(text: str) -> ClassificationResult:
    """Clasifica deterministamente el texto en capas (Contexto, Principal, Acento).

    Aplica reglas lingüísticas para el español que preservan la integridad de la frase
    y generan una jerarquía visual coherente.
    """
    normalized = normalize_subtitle_text(text)
    intent = _detect_intent(normalized)
    words = normalized.split()
    word_count = len(words)

    # 1. Frases breves o atómicas (1 a 3 palabras) -> 1 sola capa (Principal)
    if word_count <= 3:
        return ClassificationResult(
            normalized_text=normalized,
            main_text=normalized,
            context_text=None,
            accent_text=None,
            intent=intent,
            confidence=1.0,
            reason=f"Frase corta o atómica ({word_count} palabra(s)); asignada íntegramente a capa principal.",
        )

    # 2. Detección de conectores introductorios
    lower_text = normalized.lower()
    matched_connector: str | None = None
    for connector in _INTRO_CONNECTORS:
        if lower_text.startswith(connector):
            matched_connector = normalized[: len(connector)]
            break

    if matched_connector:
        remainder = normalized[len(matched_connector) :].strip()
        # Limpiar posible coma o espacio inicial en el resto
        if remainder.startswith(","):
            remainder = remainder[1:].strip()

        remainder_words = remainder.split()
        if remainder_words:
            # Si el resto es corto (1 a 5 palabras), se convierte en 2 capas (Contexto + Principal)
            if len(remainder_words) <= 5 and "," not in remainder:
                return ClassificationResult(
                    normalized_text=normalized,
                    context_text=matched_connector.strip(),
                    main_text=remainder,
                    accent_text=None,
                    intent=intent,
                    confidence=0.95,
                    reason="Conector introductorio separado en contexto; núcleo asignado a capa principal.",
                )

            # Si el resto es más largo y tiene una coma o división natural -> 3 capas
            comma_idx = remainder.find(",")
            if comma_idx != -1 and 2 <= len(remainder[:comma_idx].split()) <= 6:
                part_main = remainder[:comma_idx].strip()
                part_accent = remainder[comma_idx + 1 :].strip()
                if part_main and part_accent:
                    return ClassificationResult(
                        normalized_text=normalized,
                        context_text=matched_connector.strip(),
                        main_text=part_main,
                        accent_text=part_accent,
                        intent=intent,
                        confidence=0.90,
                        reason="Estructura de 3 capas: conector como contexto, cláusula central principal y remate en acento.",
                    )

            # División semántica del resto largo (Main + Accent)
            mid = len(remainder_words) // 2
            part_main = " ".join(remainder_words[:mid])
            part_accent = " ".join(remainder_words[mid:])
            return ClassificationResult(
                normalized_text=normalized,
                context_text=matched_connector.strip(),
                main_text=part_main,
                accent_text=part_accent,
                intent=intent,
                confidence=0.88,
                reason="Conector en contexto con división balanceada del predicado en principal y acento.",
            )

    # 3. Detección de divisiones por puntuación interna (coma, dos puntos, guion)
    for sep in (":", " - ", " – ", " — ", ","):
        if sep in normalized:
            parts = normalized.split(sep, 1)
            left = parts[0].strip()
            right = parts[1].strip()
            left_len = len(left.split())
            right_len = len(right.split())

            if left and right and left_len >= 2 and right_len >= 2:
                # Si left es corto (2-4 palabras), actúa como contexto
                if left_len <= 4:
                    # Evaluar si right puede tener acento
                    if right_len >= 5 and "," in right:
                        sub_parts = right.split(",", 1)
                        sub_main = sub_parts[0].strip()
                        sub_acc = sub_parts[1].strip()
                        if sub_main and sub_acc:
                            return ClassificationResult(
                                normalized_text=normalized,
                                context_text=left + (":" if sep == ":" else ""),
                                main_text=sub_main,
                                accent_text=sub_acc,
                                intent=intent,
                                confidence=0.87,
                                reason="Segmentación por puntuación: contexto introductorio, núcleo y acento secundario.",
                            )

                    return ClassificationResult(
                        normalized_text=normalized,
                        context_text=left + (":" if sep == ":" else ""),
                        main_text=right,
                        accent_text=None,
                        intent=intent,
                        confidence=0.90,
                        reason=f"División en 2 capas mediante signo '{sep.strip()}': contexto y proposición principal.",
                    )
                else:
                    # Left es más largo -> Main + Accent
                    return ClassificationResult(
                        normalized_text=normalized,
                        context_text=None,
                        main_text=left,
                        accent_text=right,
                        intent=intent,
                        confidence=0.88,
                        reason=f"División en 2 capas mediante signo '{sep.strip()}': proposición principal y remate en acento.",
                    )

    # 4. Frases medianas sin puntuación (4 a 6 palabras) -> 2 capas balanceadas
    if 4 <= word_count <= 6:
        split_point = word_count // 2
        part1 = " ".join(words[:split_point])
        part2 = " ".join(words[split_point:])
        return ClassificationResult(
            normalized_text=normalized,
            context_text=None,
            main_text=part1,
            accent_text=part2,
            intent=intent,
            confidence=0.80,
            reason="Frase mediana dividida sintácticamente en capa principal y complemento.",
        )

    # 5. Frases largas sin puntuación (> 6 palabras) -> 3 capas balanceadas
    p1_end = max(2, word_count // 3)
    p2_end = max(p1_end + 2, (word_count * 2) // 3)

    context_part = " ".join(words[:p1_end])
    main_part = " ".join(words[p1_end:p2_end])
    accent_part = " ".join(words[p2_end:])

    return ClassificationResult(
        normalized_text=normalized,
        context_text=context_part,
        main_text=main_part,
        accent_text=accent_part if accent_part else None,
        intent=intent,
        confidence=0.75,
        reason="Frase extendida distribuida en 3 capas mediante partición proporcional.",
    )


def create_caption_block_from_cue(cue: SubtitleCue, block_id: str) -> CaptionBlock:
    """Construye un CaptionBlock a partir de un SubtitleCue individual aplicando clasificación."""
    classification = classify_text_layers(cue.text)
    return CaptionBlock(
        id=block_id,
        source_cues=(cue,),
        start_frame=cue.start_frame,
        end_frame=cue.end_frame,
        original_text=cue.text,
        normalized_text=classification.normalized_text,
        context_text=classification.context_text,
        main_text=classification.main_text,
        accent_text=classification.accent_text,
        intent=classification.intent,
        confidence=classification.confidence,
        reason=classification.reason,
    )


def create_caption_blocks_from_cues(cues: Sequence[SubtitleCue]) -> tuple[CaptionBlock, ...]:
    """Genera la lista ordenada de CaptionBlocks a partir de una secuencia de subtítulos."""
    blocks: list[CaptionBlock] = []
    for idx, cue in enumerate(cues, start=1):
        block_id = f"block_{cue.track_index}_{idx}_{int(cue.start_frame)}_{int(cue.end_frame)}"
        blocks.append(create_caption_block_from_cue(cue, block_id))
    return tuple(blocks)
