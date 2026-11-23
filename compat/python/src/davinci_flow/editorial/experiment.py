"""Experimento comparativo: motor de decisiones frente al motor editorial actual.

Compara dos propuestas sobre la misma captura y mide acuerdo, cumplimiento
del contrato, latencia y consumo. No escribe en Resolve ni en la línea de
tiempo: solo produce un informe y propuestas sin revisar.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from davinci_flow.ai.decision_client import DecisionClient, DecisionUsage
from davinci_flow.editorial.decision_planner import DecisionTrace, propose_with_decisions
from davinci_flow.editorial.model import (
    Decision,
    EditorialError,
    EditorialOptions,
    Proposal,
    Snapshot,
    Template,
    is_grounded_excerpt,
)
from davinci_flow.editorial.planner import propose


@dataclass(frozen=True)
class DecisionAudit:
    """Incidencias del contrato editorial detectadas en una decisión."""

    index: int
    issues: tuple[str, ...] = ()

    @property
    def accepted(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class ComparisonMetrics:
    """Acuerdo entre dos propuestas sobre la misma captura."""

    blocks: int = 0
    enabled_agreement: float = 0.0
    layer_agreement: float = 0.0
    template_agreement: float = 0.0
    resource_agreement: float = 0.0
    exact_agreement: float = 0.0
    baseline_accepted: float = 0.0
    candidate_accepted: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "bloques": self.blocks,
            "acuerdo_rotulo": round(self.enabled_agreement, 4),
            "acuerdo_capas": round(self.layer_agreement, 4),
            "acuerdo_plantillas": round(self.template_agreement, 4),
            "acuerdo_recursos": round(self.resource_agreement, 4),
            "acuerdo_exacto": round(self.exact_agreement, 4),
            "aceptadas_actual": round(self.baseline_accepted, 4),
            "aceptadas_decision": round(self.candidate_accepted, 4),
        }


@dataclass(frozen=True)
class EngineRun:
    """Resultado de ejecutar un motor editorial sobre la misma captura."""

    name: str
    model: str
    proposal: Proposal
    seconds: float
    usage: DecisionUsage | None = None
    traces: tuple[DecisionTrace, ...] = ()
    prompt_chars: int = 0

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "motor": self.name,
            "modelo": self.model,
            "segundos": round(self.seconds, 3),
            "bloques": len(self.proposal.decisions),
            "con_rotulo": sum(1 for d in self.proposal.decisions if d.enabled),
            "con_sfx": sum(1 for d in self.proposal.decisions if d.resource_id),
        }
        if self.usage is not None:
            data["tokens_entrada"] = self.usage.total_input_tokens
            data["tokens_salida"] = self.usage.total_output_tokens
        if self.prompt_chars:
            data["caracteres_prompt"] = self.prompt_chars
        return data


@dataclass(frozen=True)
class ExperimentReport:
    """Informe completo del experimento."""

    decision_run: EngineRun
    baseline_run: EngineRun | None
    metrics: ComparisonMetrics | None
    decision_audits: tuple[DecisionAudit, ...] = ()
    baseline_audits: tuple[DecisionAudit, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "motor_decisiones": self.decision_run.to_dict(),
            "auditoria_decisiones": [
                {"bloque": audit.index, "incidencias": list(audit.issues)} for audit in self.decision_audits
            ],
            "notas": list(self.notes),
        }
        if self.baseline_run is not None:
            data["motor_actual"] = self.baseline_run.to_dict()
            data["auditoria_actual"] = [
                {"bloque": audit.index, "incidencias": list(audit.issues)} for audit in self.baseline_audits
            ]
        if self.metrics is not None:
            data["comparativa"] = self.metrics.to_dict()
        return data


def audit_proposal(proposal: Proposal) -> tuple[DecisionAudit, ...]:
    """Revisa cada decisión contra el contrato editorial, sin modificar la propuesta."""
    selective = proposal.options is not None and proposal.options.mode == "highlights"
    catalog = {template.id for template in proposal.templates}
    audits: list[DecisionAudit] = []
    for decision, cue in zip(proposal.decisions, proposal.snapshot.cues):
        issues: list[str] = []
        texts = (decision.context, decision.main, decision.accent)
        if not decision.main.strip() and (decision.enabled or not selective):
            issues.append("Sin texto principal.")
        reconstructed = " ".join(" ".join(texts).split())
        covered = (is_grounded_excerpt(cue.text, reconstructed) if selective
                   else reconstructed == " ".join(cue.text.split()))
        if selective and not decision.enabled and not reconstructed:
            covered = True
        if not covered:
            issues.append("El texto no está anclado al subtítulo original.")
        active = {layer for layer in ("context", "main", "accent") if getattr(decision, layer).strip()}
        if set(decision.templates) != active:
            issues.append("Las capas activas no coinciden con las plantillas asignadas.")
        if any(template_id not in catalog for template_id in decision.templates.values()):
            issues.append("Plantilla fuera del catálogo.")
        if not decision.reason.strip():
            issues.append("Sin motivo editorial.")
        audits.append(DecisionAudit(decision.cue_index, tuple(issues)))
    return tuple(audits)


def _layers(decision: Decision) -> frozenset[str]:
    return frozenset(layer for layer in ("context", "main", "accent") if getattr(decision, layer).strip())


def compare_proposals(baseline: Proposal, candidate: Proposal) -> ComparisonMetrics:
    """Mide el acuerdo entre el motor actual y el motor de decisiones."""
    if len(baseline.decisions) != len(candidate.decisions):
        raise EditorialError("Las propuestas comparadas cubren una cantidad distinta de bloques.")
    total = len(baseline.decisions) or 1
    enabled = layers = templates = resources = exact = 0
    for current, other in zip(baseline.decisions, candidate.decisions):
        same_enabled = current.enabled == other.enabled
        same_layers = _layers(current) == _layers(other)
        same_templates = current.templates == other.templates
        same_resources = current.resource_id == other.resource_id
        enabled += int(same_enabled)
        layers += int(same_layers)
        templates += int(same_templates)
        resources += int(same_resources)
        exact += int(same_enabled and same_layers and same_templates and same_resources)
    baseline_audits = audit_proposal(baseline)
    candidate_audits = audit_proposal(candidate)
    return ComparisonMetrics(
        blocks=len(baseline.decisions),
        enabled_agreement=enabled / total,
        layer_agreement=layers / total,
        template_agreement=templates / total,
        resource_agreement=resources / total,
        exact_agreement=exact / total,
        baseline_accepted=sum(1 for audit in baseline_audits if audit.accepted) / total,
        candidate_accepted=sum(1 for audit in candidate_audits if audit.accepted) / total,
    )


def run_decision_experiment(
    snapshot: Snapshot,
    templates: tuple[Template, ...],
    options: EditorialOptions | None = None,
    decision_client: DecisionClient | None = None,
    baseline_client: Any | None = None,
    threshold: float = 0.5,
    batch_size: int = 20,
) -> ExperimentReport:
    """Ejecuta el motor de decisiones y, si se pide, también el motor actual."""
    client = decision_client or DecisionClient()
    started = time.perf_counter()
    proposal, traces = propose_with_decisions(snapshot, templates, client, options, threshold, batch_size)
    seconds = time.perf_counter() - started
    usage = getattr(client, "usage", None)
    decision_run = EngineRun(
        name="decision-1",
        model=getattr(client, "model_name", "gemini-decision-1"),
        proposal=proposal,
        seconds=seconds,
        usage=usage,
        traces=traces,
    )

    baseline_run = None
    metrics = None
    baseline_audits: tuple[DecisionAudit, ...] = ()
    if baseline_client is not None:
        started = time.perf_counter()
        baseline_proposal = propose(snapshot, templates, baseline_client, options=options)
        baseline_seconds = time.perf_counter() - started
        baseline_run = EngineRun(
            name="gemini-actual",
            model=getattr(baseline_client, "model_name", "desconocido"),
            proposal=baseline_proposal,
            seconds=baseline_seconds,
        )
        baseline_audits = audit_proposal(baseline_proposal)
        metrics = compare_proposals(baseline_proposal, proposal)

    return ExperimentReport(
        decision_run=decision_run,
        baseline_run=baseline_run,
        metrics=metrics,
        decision_audits=audit_proposal(proposal),
        baseline_audits=baseline_audits,
        notes=(
            "El motor de decisiones no escribe texto: extrae decisiones y sus probabilidades.",
            "Las propuestas no están revisadas: no se aplican a ninguna línea de tiempo.",
        ),
    )
