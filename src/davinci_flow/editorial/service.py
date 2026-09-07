"""Aplicación de la revisión exacta con detección de cambios de secuencia."""

from pathlib import Path
from typing import Any

from davinci_flow.editorial.model import EditorialError, Proposal, digest
from davinci_flow.editorial.sources import capture, media_pool_catalog
from davinci_flow.editorial.writer import EditorialWriter
from davinci_flow.generation.record import GenerationExecutionRecord


def record_path_for(project_id: str, timeline_id: str) -> Path:
    """Cada secuencia conserva su propia ejecución reversible."""
    return Path.home() / ".davinci_flow/records/editorial" / digest([project_id, timeline_id])[:32] / "last.json"


def apply_reviewed(proposal: Proposal, session: Any, record_path: Path) -> GenerationExecutionRecord:
    proposal.validate(require_review=True)
    if proposal.snapshot.source != "resolve":
        raise EditorialError("La propuesta SRT es offline. Captura los subtítulos de Resolve para generar.")
    current = capture(session, proposal.snapshot.track, proposal.snapshot.first, proposal.snapshot.last)
    if current.fingerprint != proposal.snapshot.fingerprint:
        raise EditorialError("La secuencia o sus subtítulos cambiaron. Vuelve a capturar y analizar.")
    _, handles = media_pool_catalog(session.project.GetMediaPool())
    writer = EditorialWriter(session.timeline, session.project.GetMediaPool(), proposal, handles)
    writer.preflight()
    if record_path.is_file():
        previous = GenerationExecutionRecord.load_from_file(record_path)
        if previous.status == "completed" and previous.plan_id != proposal.generation_plan().plan_id:
            raise EditorialError("Deshaz la muestra anterior antes de aplicar una revisión diferente.")
    # Comprobar almacenamiento antes de tocar la secuencia.
    record_path.parent.mkdir(parents=True, exist_ok=True)
    proposal.save(record_path.with_suffix(".proposal.json"))
    record = writer.apply_plan(proposal.generation_plan())
    try:
        record.save_to_file(record_path)
    except OSError:
        writer.revert_execution(record)
        raise
    return record


def undo_reviewed(session: Any, record_path: Path) -> GenerationExecutionRecord:
    proposal = Proposal.load(record_path.with_suffix(".proposal.json"))
    if (str(session.timeline.GetUniqueId()) != proposal.snapshot.timeline_id
            or str(session.project.GetUniqueId()) != proposal.snapshot.project_id):
        raise EditorialError("La ejecución pertenece a otra secuencia o proyecto.")
    record = GenerationExecutionRecord.load_from_file(record_path)
    writer = EditorialWriter(session.timeline, session.project.GetMediaPool(), proposal, {})
    result = writer.revert_execution(record)
    result.save_to_file(record_path)
    return result
