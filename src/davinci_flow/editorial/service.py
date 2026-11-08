"""Aplicación de la revisión exacta con detección de cambios de secuencia."""

from collections import Counter
from dataclasses import replace
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from davinci_flow.editorial.model import EditorialError, Proposal, Snapshot, digest
from davinci_flow.editorial.sources import capture, media_pool_catalog
from davinci_flow.editorial.writer import EditorialWriter
from davinci_flow.generation.record import GenerationExecutionRecord


def record_path_for(project_id: str, timeline_id: str) -> Path:
    """Cada secuencia conserva su propia ejecución reversible."""
    return Path.home() / ".davinci_flow/records/editorial" / digest([project_id, timeline_id])[:32] / "last.json"


def _same_revision_on_timeline(captured: Snapshot, current: Snapshot) -> bool:
    """Compatibilidad con revisiones guardadas antes de registrar los medios fuente."""
    if (captured.project_id != current.project_id or captured.timeline_id != current.timeline_id
            or not captured.timeline_id):
        return False
    if (captured.project, captured.fps, captured.width, captured.height, captured.origin,
            captured.track, captured.first, captured.last, captured.cues) != (
            current.project, current.fps, current.width, current.height, current.origin,
            current.track, current.first, current.last, current.cues):
        return False
    if len(captured.cuts) != len(current.cuts):
        return False
    return all(len(saved) <= len(now) and saved == now[:len(saved)]
               for saved, now in zip(captured.cuts, current.cuts))


def _same_project_timeline_content(captured: Snapshot, current: Snapshot) -> bool:
    """Acepta una copia si coincide el montaje que cubre los subtítulos revisados."""
    if (captured.source != "resolve" or current.source != "resolve"
            or not captured.project_id or captured.project_id != current.project_id):
        return False
    if (captured.fps, captured.width, captured.height, captured.origin, captured.track,
            captured.first, captured.last, captured.cues) != (
            current.fps, current.width, current.height, current.origin, current.track,
            current.first, current.last, current.cues):
        return False

    # Los IDs de TimelineItem cambian al duplicar. Se comparan solo los cortes que
    # cubren la revisión; en audio el índice de pista puede variar al duplicar.
    def stable_cuts(snapshot: Snapshot) -> Counter | None:
        if len(snapshot.cut_source_refs) != len(snapshot.cuts):
            return None
        result = Counter()
        span_start = min(cue.start_frame for cue in snapshot.cues)
        span_end = max(cue.end_frame for cue in snapshot.cues)
        for cut, source_ref in zip(snapshot.cuts, snapshot.cut_source_refs):
            if cut[4] <= span_start or cut[3] >= span_end:
                continue
            if not source_ref:
                return None
            signature = ((cut[0],) + cut[3:] if cut[0] == "audio"
                         else cut[:2] + cut[3:])
            result[signature + (source_ref,)] += 1
        return result

    captured_cuts = stable_cuts(captured)
    current_cuts = stable_cuts(current)
    if captured_cuts is None or current_cuts is None:
        return False
    return captured_cuts == current_cuts


def _matches_duplicate_via_source_timeline(captured: Snapshot, current: Snapshot,
                                           project: Any) -> bool:
    """Verifica propuestas antiguas contra su timeline original aún presente."""
    if not captured.timeline_id or not captured.project_id or captured.project_id != current.project_id:
        return False
    try:
        for index in range(1, int(project.GetTimelineCount()) + 1):
            timeline = project.GetTimelineByIndex(index)
            if timeline is None or str(timeline.GetUniqueId() or "") != captured.timeline_id:
                continue
            source = capture(SimpleNamespace(timeline=timeline, project=project),
                             captured.track, captured.first, captured.last)
            return (_same_revision_on_timeline(captured, source)
                    and _same_project_timeline_content(source, current))
    except Exception:
        return False
    return False


def _same_srt_cues_on_active_timeline(source: Snapshot, current: Snapshot) -> bool:
    """Vincula un SRT importado solo si reproduce exactamente la pista activa."""
    if source.source != "srt" or current.source != "resolve":
        return False
    if (not source.project_id or source.project_id != current.project_id
            or source.track != current.track
            or source.first != current.first or source.last != current.last
            or source.origin != current.origin
            or (source.width, source.height) != (current.width, current.height)
            or not math.isclose(source.fps, current.fps, rel_tol=0.0, abs_tol=1e-9)
            or len(source.cues) != len(current.cues)):
        return False
    return all(
        saved.text == active.text
        and saved.track_index == active.track_index
        and math.isclose(saved.start_frame, active.start_frame, rel_tol=0.0, abs_tol=1e-6)
        and math.isclose(saved.end_frame, active.end_frame, rel_tol=0.0, abs_tol=1e-6)
        for saved, active in zip(source.cues, current.cues)
    )


def apply_reviewed(proposal: Proposal, session: Any, record_path: Path) -> GenerationExecutionRecord:
    proposal.validate(require_review=True)
    current = capture(session, proposal.snapshot.track, proposal.snapshot.first, proposal.snapshot.last)
    if proposal.snapshot.source == "srt":
        if not _same_srt_cues_on_active_timeline(proposal.snapshot, current):
            raise EditorialError(
                "La propuesta SRT no coincide exactamente con los subtítulos de la pista activa. "
                "Comprueba el proyecto, la pista y los tiempos antes de aplicarla."
            )
        # Una secuencia duplicada puede cambiar de ID; la coincidencia completa
        # de proyecto, pista y cues enlaza la propuesta al destino activo.
        proposal = replace(proposal, snapshot=current)
    elif current.fingerprint != proposal.snapshot.fingerprint:
        if not (_same_revision_on_timeline(proposal.snapshot, current)
                or _same_project_timeline_content(proposal.snapshot, current)
                or _matches_duplicate_via_source_timeline(proposal.snapshot, current, session.project)):
            raise EditorialError("El montaje o sus subtítulos cambiaron. Vuelve a capturar y analizar.")
        # La copia verificada pasa a ser el destino del plan y de su registro reversible.
        proposal = replace(proposal, snapshot=current)
    _, handles = media_pool_catalog(session.project.GetMediaPool())
    writer = EditorialWriter(session.timeline, session.project.GetMediaPool(), proposal, handles)
    writer.preflight()
    if record_path.is_file():
        previous = GenerationExecutionRecord.load_from_file(record_path)
        if previous.status == "completed" and previous.plan_id != proposal.generation_plan().plan_id:
            try:
                writer.revert_execution(previous)
            except Exception:
                pass

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
