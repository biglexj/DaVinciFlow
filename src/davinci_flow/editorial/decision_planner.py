"""Motor editorial experimental: decisiones calibradas en vez de texto generado.

`gemini-decision-1` no escribe una propuesta: evalúa preguntas tipadas sobre
los subtítulos y devuelve probabilidades. Este módulo traduce esas decisiones
a una :class:`~davinci_flow.editorial.model.Proposal` que respeta el contrato
editorial vigente (mismas validaciones, mismas capas, revisión manual
obligatoria) para poder compararla con el motor actual.

Ninguna decisión se aplica a Resolve: el resultado es una propuesta sin
revisar, como la de cualquier otra generación.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from davinci_flow.editorial.model import (
    BUILTIN_SFX_IDS,
    Decision,
    EditorialError,
    EditorialOptions,
    Proposal,
    Snapshot,
    Template,
    is_grounded_excerpt,
)
from davinci_flow.sfx.catalog import DEFAULT_SFX_ASSETS

LAYER_CONTEXT = "DF_CONTEXT"
LAYER_MAIN = "DF_MAIN"
LAYER_ACCENT = "DF_ACCENT"
LAYER_NONE = "SIN_ROTULO"

_INTENSITY_LEVELS = ("Nula", "Leve", "Media", "Alta", "Maxima")


class DecisionEngine(Protocol):
    """Contrato mínimo del motor de decisiones."""

    model_name: str

    def decide(self, input_text: str, questions: dict[str, dict[str, Any]]) -> Any: ...


@dataclass(frozen=True)
class DecisionTrace:
    """Traza auditable de las decisiones del modelo para un bloque."""

    cue_index: int
    enabled: bool
    layer: str
    layer_probability: float
    worth_probability: float
    breathe_probability: float
    intensity: float
    template_ids: dict[str, str] = field(default_factory=dict)
    resource_id: str = ""
    idea_probability: float = 0.0

    def summary(self) -> str:
        """Resumen legible de las probabilidades que sostienen la decisión."""
        parts = [
            f"destacar={self.worth_probability:.2f}",
            f"capa={self.layer}({self.layer_probability:.2f})",
            f"intensidad={self.intensity:.2f}",
            f"respirar={self.breathe_probability:.2f}",
        ]
        if self.idea_probability:
            parts.append(f"idea={self.idea_probability:.2f}")
        return " · ".join(parts)


def _words(text: str) -> list[str]:
    return text.split()


def _span_text(words: list[str], start: int, end: int) -> str:
    return " ".join(words[start:end])


def _split_ratio(words: list[str], ratio: float) -> int:
    """Punto de corte que conserva al menos una palabra por lado."""
    if len(words) < 2:
        return 0
    return max(1, min(len(words) - 1, round(len(words) * ratio)))


def _idea_candidates(words: list[str]) -> list[tuple[str, str, int]]:
    """Fragmentos candidatos a «idea principal» del bloque.

    Solo se consideran sufijos del subtítulo: el contrato editorial exige que
    la reconstrucción de las capas conserve el orden original de las palabras.
    """
    if len(words) < 4:
        return []
    cut_long = _split_ratio(words, 0.45)
    cut_short = _split_ratio(words, 0.7)
    candidates = []
    if cut_long < len(words):
        candidates.append(("idea_larga", _span_text(words, cut_long, len(words)), cut_long))
    if cut_short > cut_long:
        candidates.append(("idea_corta", _span_text(words, cut_short, len(words)), cut_short))
    return candidates


def _template_options(templates: tuple[Template, ...]) -> tuple[dict[str, str], dict[str, str]]:
    """Opciones de plantilla para las preguntas `choice` y su equivalencia."""
    options: dict[str, str] = {}
    mapping: dict[str, str] = {}
    for index, template in enumerate(templates):
        key = f"t{index}"
        options[key] = f"{template.name} (id: {template.id})"
        mapping[key] = template.id
    return options, mapping


def _sfx_options() -> tuple[dict[str, str], dict[str, str]]:
    options: dict[str, str] = {}
    mapping: dict[str, str] = {}
    for index, asset in enumerate(DEFAULT_SFX_ASSETS):
        key = f"s{index}"
        options[key] = f"{asset.name} — {asset.category}"
        mapping[key] = asset.id
    return options, mapping


def _build_input(snapshot: Snapshot, templates: tuple[Template, ...], start: int, end: int,
                 options: EditorialOptions | None) -> str:
    """Entrada compartida: transcripción con contexto vecino, tiempos y catálogo."""
    lines = [
        "Transcripción de un montaje con subtítulos numerados.",
        "Cada línea empieza por su número de bloque y sus tiempos en segundos.",
        "El contexto narrativo de los bloques vecinos ayuda a valorar la intención.",
    ]
    if options is not None and options.direction.strip():
        lines.append(f"Dirección creativa del autor: {options.direction.strip()}")
    if options is not None:
        lines.append(f"Densidad solicitada: {options.density}. Modo: {options.mode}.")
    lines.append("Plantillas disponibles:")
    for template in templates:
        lines.append(f"- {template.id}: {template.name}")
    lines.append("Transcripción:")
    for index in range(max(0, start - 2), min(len(snapshot.cues), end + 2)):
        cue = snapshot.cues[index]
        seconds = cue.start_frame / (snapshot.fps or 24.0)
        marker = "  " if start <= index < end else "· "
        lines.append(f"{marker}[{index}] ({seconds:.1f}s) {cue.text}")
    return "\n".join(lines)


def _build_questions(snapshot: Snapshot, templates: tuple[Template, ...], start: int, end: int,
                     options: EditorialOptions | None) -> dict[str, dict[str, Any]]:
    """Preguntas tipadas por bloque: selección, capa, intensidad, plantilla, sonido."""
    template_options, _mapping = _template_options(templates)
    sfx_options, _sfx_mapping = _sfx_options()
    questions: dict[str, dict[str, Any]] = {}
    for index in range(start, end):
        cue = snapshot.cues[index]
        text = cue.text
        reference = f'Para el bloque {index} ("{text}")'
        questions[f"c{index}_destaca"] = {
            "type": "noul",
            "instructions": f"{reference}: ¿este fragmento merece un rótulo en pantalla?",
            "criteria": {
                "true_description": "Aporta una idea, una cifra, un giro o un remate que conviene destacar.",
                "false_description": "Es una transición, una muletilla o una frase de relleno.",
            },
        }
        questions[f"c{index}_jerarquia"] = {
            "type": "choice",
            "instructions": f"{reference}: ¿qué capa editorial describe mejor este fragmento?",
            "criteria": {
                LAYER_MAIN: "La idea principal del fragmento va en la capa principal.",
                LAYER_CONTEXT: "El fragmento tiene una entrada de apoyo y un núcleo: la entrada va en contexto.",
                LAYER_ACCENT: "El fragmento pide una capa de acento destacada sobre el remate final.",
                LAYER_NONE: "El fragmento no necesita rótulo.",
            },
        }
        questions[f"c{index}_intensidad"] = {
            "type": "score",
            "instructions": f"{reference}: ¿qué intensidad editorial tiene este fragmento?",
            "criteria": list(_INTENSITY_LEVELS),
        }
        questions[f"c{index}_plantilla_ctx"] = {
            "type": "choice",
            "instructions": f"{reference}: ¿qué plantilla del catálogo encaja con una capa de contexto?",
            "criteria": template_options,
        }
        questions[f"c{index}_plantilla_main"] = {
            "type": "choice",
            "instructions": f"{reference}: ¿qué plantilla del catálogo encaja con la capa principal?",
            "criteria": template_options,
        }
        questions[f"c{index}_plantilla_accent"] = {
            "type": "choice",
            "instructions": f"{reference}: ¿qué plantilla del catálogo encaja con una capa de acento?",
            "criteria": template_options,
        }
        questions[f"c{index}_efecto"] = {
            "type": "noul",
            "instructions": f"{reference}: ¿este fragmento necesita un efecto sonoro de apoyo?",
            "criteria": {
                "true_description": "Un golpe o barrido mejora el remate o el cambio de idea.",
                "false_description": "El fragmento debe respirar sin sonido.",
            },
        }
        questions[f"c{index}_tipo_efecto"] = {
            "type": "choice",
            "instructions": f"{reference}: si necesita efecto, ¿cuál encaja mejor?",
            "criteria": sfx_options,
        }
        questions[f"c{index}_respirar"] = {
            "type": "noul",
            "instructions": f"{reference}: ¿conviene dejar este fragmento sin efectos y sin rótulo?",
            "criteria": {
                "true_description": "Deja respirar el ritmo: nada de rótulo ni de sonido.",
                "false_description": "El fragmento puede llevar rótulo o efecto.",
            },
        }
        questions[f"c{index}_acento_final"] = {
            "type": "noul",
            "instructions": f"{reference}: ¿el remate final de este fragmento merece ser la capa de acento?",
            "criteria": {
                "true_description": "Las últimas palabras concentran la fuerza del fragmento.",
                "false_description": "El fragmento no tiene un remate destacado al final.",
            },
        }
        for name, candidate, _cut in _idea_candidates(_words(text)):
            questions[f"c{index}_{name}"] = {
                "type": "noul",
                "instructions": f'{reference}: ¿el fragmento "{candidate}" resume su idea principal?',
                "criteria": {
                    "true_description": "Ese fragmento contiene la idea que hay que destacar.",
                    "false_description": "La idea principal no está en ese fragmento.",
                },
            }
    return questions


def _answer(answers: dict[str, Any], key: str):
    return answers.get(key)


def _probability(answers: dict[str, Any], key: str) -> float:
    answer = _answer(answers, key)
    if answer is None:
        return 0.0
    return float(getattr(answer, "probability", 0.0) or 0.0)


def _choice(answers: dict[str, Any], key: str) -> str:
    answer = _answer(answers, key)
    return str(getattr(answer, "choice", "") or "") if answer is not None else ""


def _template_for(answers: dict[str, Any], key: str, templates: tuple[Template, ...]) -> str:
    """Plantilla elegida para una capa, con reserva en la primera del catálogo."""
    _options, mapping = _template_options(templates)
    chosen = mapping.get(_choice(answers, key), "")
    return chosen or (templates[0].id if templates else "")


def _build_decision(index: int, cue_text: str, answers: dict[str, Any], templates: tuple[Template, ...],
                    options: EditorialOptions | None, threshold: float) -> tuple[Decision, DecisionTrace]:
    """Traduce las respuestas del modelo a una decisión editorial válida."""
    words = _words(cue_text)
    layer = _choice(answers, f"c{index}_jerarquia")
    worth = _probability(answers, f"c{index}_destaca")
    breathe = _probability(answers, f"c{index}_respirar")
    effect = _probability(answers, f"c{index}_efecto")
    accent_final = _probability(answers, f"c{index}_acento_final")
    intensity_answer = _answer(answers, f"c{index}_intensidad")
    intensity = float(getattr(intensity_answer, "score", 0.0) or 0.0) if intensity_answer else 0.0

    candidates = _idea_candidates(words)
    idea_probability = 0.0
    idea_text = ""
    idea_cut = 0
    for name, candidate, cut in candidates:
        probability = _probability(answers, f"c{index}_{name}")
        if probability <= idea_probability:
            continue
        # El contrato editorial no admite perder negaciones: un fragmento que
        # las deja fuera se descarta y se conserva el subtítulo completo.
        if not is_grounded_excerpt(cue_text, candidate):
            continue
        idea_probability, idea_text, idea_cut = probability, candidate, cut

    selective = options is not None and options.mode == "highlights"
    enabled = True
    if selective:
        enabled = worth >= threshold and layer != LAYER_NONE and breathe < 0.6
        if enabled and candidates and idea_probability >= threshold:
            enabled = True

    context = main = accent = ""
    if enabled:
        if selective and idea_text and idea_probability >= threshold:
            main = idea_text
            if layer == LAYER_CONTEXT and idea_cut > 0:
                context = _span_text(words, 0, idea_cut)
        elif layer == LAYER_CONTEXT and len(words) >= 4:
            cut = _split_ratio(words, 0.4)
            context = _span_text(words, 0, cut)
            main = _span_text(words, cut, len(words))
        elif layer == LAYER_ACCENT and accent_final >= threshold and len(words) >= 4:
            cut = _split_ratio(words, 0.75)
            main = _span_text(words, 0, cut)
            accent = _span_text(words, cut, len(words))
        else:
            main = cue_text

    template_map: dict[str, str] = {}
    if context:
        template_map["context"] = _template_for(answers, f"c{index}_plantilla_ctx", templates)
    if main:
        template_map["main"] = _template_for(answers, f"c{index}_plantilla_main", templates)
    if accent:
        template_map["accent"] = _template_for(answers, f"c{index}_plantilla_accent", templates)

    resource_id = ""
    if enabled and effect >= threshold and breathe < 0.5:
        _sfx_options_map, sfx_mapping = _sfx_options()
        candidate = sfx_mapping.get(_choice(answers, f"c{index}_tipo_efecto"), "")
        if candidate in BUILTIN_SFX_IDS:
            resource_id = candidate

    trace = DecisionTrace(
        cue_index=index,
        enabled=enabled,
        layer=layer or LAYER_MAIN,
        layer_probability=_probability(answers, f"c{index}_jerarquia"),
        worth_probability=worth,
        breathe_probability=breathe,
        intensity=intensity,
        template_ids=dict(template_map),
        resource_id=resource_id,
        idea_probability=idea_probability,
    )

    reason = f"Decisión 1: {trace.summary()}"
    visual_note = ""
    if enabled:
        visual_note = "Capa " + ", ".join(sorted(template_map))
        if accent:
            visual_note += f" con acento sobre «{accent}»"

    decision = Decision(
        cue_index=index,
        context=context,
        main=main,
        accent=accent,
        templates=template_map,
        reason=reason,
        enabled=enabled,
        reviewed=False,
        edit_note="",
        visual_note=visual_note,
        resource_id=resource_id,
    )
    return decision, trace


def propose_with_decisions(
    snapshot: Snapshot,
    templates: tuple[Template, ...],
    client: DecisionEngine,
    options: EditorialOptions | None = None,
    threshold: float = 0.5,
    batch_size: int = 20,
) -> tuple[Proposal, tuple[DecisionTrace, ...]]:
    """Propone una propuesta editorial a partir de decisiones calibradas.

    Devuelve la propuesta (sin revisar) y la traza de decisiones para poder
    comparar con el motor actual.
    """
    if not templates:
        raise EditorialError("Selecciona plantillas para el experimento.")
    if options is not None:
        options.validate()
    if not 0.0 < threshold < 1.0:
        raise EditorialError("El umbral de decisión debe estar entre 0 y 1.")
    if batch_size < 1:
        raise EditorialError("El tamaño de tanda debe ser al menos 1.")

    decisions: list[Decision] = []
    traces: list[DecisionTrace] = []
    for start in range(0, len(snapshot.cues), batch_size):
        end = min(start + batch_size, len(snapshot.cues))
        questions = _build_questions(snapshot, templates, start, end, options)
        answers, _usage = client.decide(_build_input(snapshot, templates, start, end, options), questions)
        for index in range(start, end):
            decision, trace = _build_decision(index, snapshot.cues[index].text, answers, templates, options, threshold)
            decisions.append(decision)
            traces.append(trace)

    proposal = Proposal(
        snapshot=snapshot,
        templates=templates,
        decisions=tuple(decisions),
        model=getattr(client, "model_name", "gemini-decision-1"),
        version="1.1.0" if options is not None else "1.0.0",
        options=options,
    )
    proposal.validate()
    return proposal, tuple(traces)
