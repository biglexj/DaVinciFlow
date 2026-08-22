"""Casos de uso principales y orquestación de DaVinci Flow."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import os
from math import gcd
from pathlib import Path
from typing import Any

from davinci_flow.ai.aligner import (
    CorrectionResult,
    ScriptAligner,
    TimelineMarker,
)
from davinci_flow.ai.credentials import save_gemini_api_key
from davinci_flow.generation.plan import GenerationPlan, build_generation_plan
from davinci_flow.generation.reconciler import PlanDiff, reconcile_subtitles
from davinci_flow.generation.record import GenerationExecutionRecord
from davinci_flow.errors import TimelineWriteError
from davinci_flow.resolve import (
    ResolveMarkerWriter,
    ResolveSubtitleReader,
    ResolveTimelineWriter,
    connect_to_resolve,
)
from davinci_flow.sfx.engine import SFXProposalEngine
from davinci_flow.subtitles import SubtitleCue
from davinci_flow.subtitles.srt_parser import load_srt_file, parse_srt_content


def _last_execution_record_path() -> Path:
    """Ruta local del último registro físico, fuera del repositorio y sin datos secretos."""
    app_data = os.environ.get("APPDATA")
    base = Path(app_data) if app_data else Path.home() / ".davinci-flow"
    return base / "DaVinciFlow" / "records" / "last_execution.json"


def _timeline_metrics(timeline: Any) -> tuple[str | None, float, int, int, str]:
    """Lee FPS, resolución e identificador reales con valores seguros de respaldo."""
    timeline_id: str | None = None
    get_unique_id = getattr(timeline, "GetUniqueId", None)
    if callable(get_unique_id):
        try:
            raw_id = get_unique_id()
            if raw_id:
                timeline_id = str(raw_id)
        except Exception:
            pass

    def setting(keys: tuple[str, ...], default: str) -> str:
        get_setting = getattr(timeline, "GetSetting", None)
        if not callable(get_setting):
            return default
        for key in keys:
            try:
                value = get_setting(key)
                if value not in (None, ""):
                    return str(value)
            except Exception:
                continue
        return default

    try:
        fps = float(setting(("timelineFrameRate", "timelinePlaybackFrameRate"), "24"))
    except ValueError:
        fps = 24.0
    try:
        width = int(float(setting(("timelineResolutionWidth",), "1920")))
        height = int(float(setting(("timelineResolutionHeight",), "1080")))
    except ValueError:
        width, height = 1920, 1080

    if fps <= 0:
        fps = 24.0
    if width <= 0 or height <= 0:
        width, height = 1920, 1080
    divisor = gcd(width, height)
    return timeline_id, fps, width, height, f"{width // divisor}:{height // divisor}"


@dataclass(frozen=True, slots=True)
class SubtitleScan:
    """Resultado de leer subtítulos de la línea de tiempo activa o de un archivo SRT."""

    project_name: str
    timeline_name: str
    track_index: int
    cues: tuple[SubtitleCue, ...]


@dataclass(frozen=True, slots=True)
class TimelineSummary:
    """Información general de la línea de tiempo activa y sus pistas de subtítulos."""

    project_name: str
    timeline_name: str
    video_track_count: int
    audio_track_count: int
    subtitle_track_count: int
    subtitle_cues_counts: dict[int, int]


def inspect_active_timeline() -> TimelineSummary:
    """Inspecciona la línea de tiempo activa para autodetectar pistas de subtítulos y contenido."""
    session = connect_to_resolve()
    tl = session.timeline

    def _safe_count(t_type: str) -> int:
        getter = getattr(tl, "GetTrackCount", None)
        if callable(getter):
            try:
                return int(getter(t_type) or 0)
            except Exception:
                return 0
        return 0

    v_count = _safe_count("video")
    a_count = _safe_count("audio")
    sub_count = _safe_count("subtitle")

    reader = ResolveSubtitleReader(tl)
    cues_counts: dict[int, int] = {}
    for idx in range(1, max(2, sub_count + 1)):
        try:
            cues = reader.read_track(idx)
            cues_counts[idx] = len(cues)
        except Exception:
            cues_counts[idx] = 0

    return TimelineSummary(
        project_name=str(session.project.GetName()),
        timeline_name=str(session.timeline.GetName()),
        video_track_count=v_count,
        audio_track_count=a_count,
        subtitle_track_count=sub_count,
        subtitle_cues_counts=cues_counts,
    )


def scan_active_subtitles(
    track_index: int = 1,
    srt_path: str | Path | None = None,
) -> SubtitleScan:
    """Conecta con Resolve u obtiene subtítulos directamente desde un archivo SRT."""
    if srt_path:
        try:
            session = connect_to_resolve()
            proj_name = str(session.project.GetName())
            tl_name = str(session.timeline.GetName())
            _timeline_id, fps, _width, _height, _aspect = _timeline_metrics(session.timeline)
        except Exception:
            proj_name = "Archivo SRT"
            tl_name = Path(srt_path).name
            fps = 24.0
        cues = load_srt_file(srt_path, track_index=track_index, fps=fps)

        return SubtitleScan(
            project_name=proj_name,
            timeline_name=tl_name,
            track_index=track_index,
            cues=cues,
        )

    session = connect_to_resolve()
    cues = ResolveSubtitleReader(session.timeline).read_track(track_index)
    return SubtitleScan(
        project_name=str(session.project.GetName()),
        timeline_name=str(session.timeline.GetName()),
        track_index=track_index,
        cues=cues,
    )


def align_and_correct_subtitles(
    track_index: int = 1,
    original_script: str = "",
    glossary: dict[str, str] | None = None,
    detect_markers: bool = True,
    api_key: str | None = None,
    srt_path: str | Path | None = None,
) -> CorrectionResult:
    """Lee subtítulos de Resolve o archivo SRT, los compara contra el guion original y los corrige con Gemini."""
    scan = scan_active_subtitles(track_index=track_index, srt_path=srt_path)
    aligner = ScriptAligner(api_key=api_key)
    return aligner.align_and_correct(
        cues=scan.cues,
        original_script=original_script,
        glossary=glossary,
        detect_markers=detect_markers,
    )


def insert_ai_timeline_markers(
    markers: Sequence[TimelineMarker],
    clear_existing_color: bool = False,
) -> int:
    """Inserta en la línea de tiempo activa de DaVinci Resolve los marcadores generados."""
    session = connect_to_resolve()
    writer = ResolveMarkerWriter(session.timeline)
    return writer.apply_markers(markers, clear_existing_color=clear_existing_color)


def plan_active_subtitles(
    track_index: int = 1,
    theme_name: str = "ely",
    profile_name: str = "natural",
    enable_sfx: bool = True,
    original_script: str = "",
    glossary: dict[str, str] | None = None,
    api_key: str | None = None,
    use_ai_correction: bool = False,
    srt_path: str | Path | None = None,
    resolve_session: Any | None = None,
) -> tuple[GenerationPlan, CorrectionResult | None]:
    """Lee la pista activa o archivo SRT y produce un GenerationPlan clasificado con soporte de corrección por IA."""
    if srt_path:
        try:
            session = resolve_session or connect_to_resolve()
            proj_name = str(session.project.GetName())
            tl_name = str(session.timeline.GetName())
            timeline_id, fps, width, height, aspect_ratio = _timeline_metrics(session.timeline)
        except Exception:
            proj_name = "Proyecto DaVinci"
            tl_name = Path(srt_path).stem
            timeline_id, fps, width, height, aspect_ratio = None, 24.0, 1920, 1080, "16:9"
        cues = load_srt_file(srt_path, track_index=track_index, fps=fps)
    else:
        session = resolve_session or connect_to_resolve()
        proj_name = str(session.project.GetName())
        tl_name = str(session.timeline.GetName())
        timeline_id, fps, width, height, aspect_ratio = _timeline_metrics(session.timeline)
        cues = ResolveSubtitleReader(session.timeline).read_track(track_index)

    correction_res: CorrectionResult | None = None

    if use_ai_correction or original_script or glossary or api_key:
        aligner = ScriptAligner(api_key=api_key)
        correction_res = aligner.align_and_correct(
            cues=cues,
            original_script=original_script,
            glossary=glossary,
            detect_markers=True,
        )
        cues = correction_res.corrected_cues

    base_plan = build_generation_plan(
        project_name=proj_name,
        timeline_name=tl_name,
        cues=cues,
        track_index=track_index,
        timeline_id=timeline_id,
        fps=fps,
        width=width,
        height=height,
        aspect_ratio=aspect_ratio,
        theme_name=theme_name,
        profile_name=profile_name,
    )

    if enable_sfx:
        sfx_engine = SFXProposalEngine()
        processed_blocks = sfx_engine.process_blocks(base_plan.blocks, profile_name=profile_name)
        final_plan = GenerationPlan(
            plan_id=base_plan.plan_id,
            project_name=base_plan.project_name,
            timeline_name=base_plan.timeline_name,
            timeline_id=base_plan.timeline_id,
            track_index=base_plan.track_index,
            start_frame=base_plan.start_frame,
            end_frame=base_plan.end_frame,
            fps=base_plan.fps,
            width=base_plan.width,
            height=base_plan.height,
            aspect_ratio=base_plan.aspect_ratio,
            theme_name=base_plan.theme_name,
            profile_name=base_plan.profile_name,
            source_hash=base_plan.source_hash,
            track_mapping=base_plan.track_mapping,
            blocks=processed_blocks,
        )
        return final_plan, correction_res

    return base_plan, correction_res


def generate_from_active_timeline(
    track_index: int = 1,
    theme_name: str = "ely",
    profile_name: str = "natural",
    enable_sfx: bool = True,
    dry_run: bool = False,
    original_script: str = "",
    glossary: dict[str, str] | None = None,
    api_key: str | None = None,
    use_ai_correction: bool = False,
    insert_markers: bool = False,
    srt_path: str | Path | None = None,
    progress_callback: Callable[[int, int, str], None] | None = None,
    is_cancelled: Callable[[], bool] | None = None,
) -> GenerationExecutionRecord:
    """Ejecuta el flujo completo de análisis, corrección IA, planificación y generación en Resolve."""
    session = connect_to_resolve()
    plan, correction_res = plan_active_subtitles(
        track_index=track_index,
        theme_name=theme_name,
        profile_name=profile_name,
        enable_sfx=enable_sfx,
        original_script=original_script,
        glossary=glossary,
        api_key=api_key,
        use_ai_correction=use_ai_correction,
        srt_path=srt_path,
        resolve_session=session,
    )

    if insert_markers and correction_res and correction_res.markers and not dry_run:
        marker_writer = ResolveMarkerWriter(session.timeline)
        marker_writer.apply_markers(correction_res.markers)

    media_pool = session.project.GetMediaPool()
    writer = ResolveTimelineWriter(session.timeline, media_pool=media_pool)
    record = writer.apply_plan(
        plan,
        dry_run=dry_run,
        progress_callback=progress_callback,
        is_cancelled=is_cancelled,
    )
    if not dry_run:
        record.save_to_file(_last_execution_record_path())
    return record


def reconcile_active_timeline(
    previous_plan_path: str | Path,
    track_index: int = 1,
) -> PlanDiff:
    """Calcula diferencias entre un plan previo y el estado actual de subtítulos."""
    session = connect_to_resolve()
    previous_plan = GenerationPlan.load_from_file(previous_plan_path)
    current_cues = ResolveSubtitleReader(session.timeline).read_track(track_index)
    return reconcile_subtitles(previous_plan, current_cues)


def revert_active_generation() -> int:
    """Deshace únicamente la última ejecución registrada en el proyecto y timeline activos."""
    session = connect_to_resolve()
    record_path = _last_execution_record_path()
    if not record_path.is_file():
        raise TimelineWriteError("No existe una generación registrada que se pueda deshacer.")

    record = GenerationExecutionRecord.load_from_file(record_path)
    project_name = str(session.project.GetName())
    timeline_name = str(session.timeline.GetName())
    if record.project_name != project_name or record.timeline_name != timeline_name:
        raise TimelineWriteError(
            "La última generación pertenece a otro proyecto o línea de tiempo; no se eliminó nada."
        )

    writer = ResolveTimelineWriter(
        session.timeline,
        media_pool=session.project.GetMediaPool(),
    )
    reverted = writer.revert_execution(record)
    reverted.save_to_file(record_path)
    return sum(1 for item in reverted.items if item.status == "reverted")


def save_user_gemini_key(api_key: str) -> Path:
    """Guarda la clave API de Gemini en la configuración local del usuario."""
    return save_gemini_api_key(api_key)
