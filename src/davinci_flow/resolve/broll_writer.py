"""Motor de montaje e inserción nativa de B-Rolls y material de apoyo en DaVinci Resolve.

Implementa:
- Inserción video-only (mediaType: 1) para preservar intactas las pistas de audio (A1 voz, A2 diálogos, A3/A4 SFX).
- Compensación precisa de ratio de fotogramas (FPS) entre clips fuente y línea de tiempo.
- Encadenamiento dinámico (zero-gaps): sincronización continua mediante GetEnd() del clip anterior.
- Protección de Copyright Content ID: segmentación o control de duración máxima por corte (< 8 segundos).
- Gestión organizada del Media Pool en carpetas dedicadas.
- Auditoría técnica de línea de tiempo (detección de huecos y verificación de límites).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Any, Sequence

from davinci_flow.assets.broll_catalog import BRollAsset, BRollProposal
from davinci_flow.errors import DaVinciFlowError, TimelineWriteError


class BRollWriteError(TimelineWriteError):
    """Error durante la importación, preparación o inserción de B-Rolls en Resolve."""


@dataclass(frozen=True, slots=True)
class BRollCut:
    """Representación de un corte individual de B-Roll a insertar o insertado."""

    asset_id: str
    asset_name: str
    file_path: str
    start_frame_tl: float
    end_frame_tl: float
    start_frame_src: int = 0
    duration_tl: float = 0.0
    actual_start_tl: float | None = None
    actual_end_tl: float | None = None
    source_fps: float = 24.0

    @property
    def duration(self) -> float:
        return self.end_frame_tl - self.start_frame_tl


@dataclass
class BRollAuditReport:
    """Resultado de la auditoría técnica de una pista de B-Roll."""

    track_index: int
    total_clips: int
    total_duration_frames: float
    gaps: list[tuple[float, float, float]] = field(default_factory=list)  # (gap_start, gap_end, gap_length)
    clips_exceeding_copyright: list[tuple[str, float]] = field(default_factory=list)  # (name, duration)

    @property
    def is_gapless(self) -> bool:
        return len(self.gaps) == 0

    @property
    def is_copyright_compliant(self) -> bool:
        return len(self.clips_exceeding_copyright) == 0


@dataclass
class BRollExecutionResult:
    """Resumen de la ejecución de inserción de B-Rolls."""

    status: str  # "completed" | "dry_run" | "cancelled" | "failed"
    total_cuts_inserted: int
    total_frames_covered: float
    track_index: int
    target_track_name: str
    cuts: list[BRollCut] = field(default_factory=list)
    audit: BRollAuditReport | None = None


class BRollWriter:
    """Gestiona la preparación, segmentación e inserción de recursos B-Roll en Resolve."""

    # Límite por defecto para evitar reclamos automatizados de Content ID (YouTube)
    # 150 frames @ 24fps = 6.25s (muy por debajo del umbral de 8s / 192 frames)
    DEFAULT_MAX_CUT_FRAMES = 150.0
    DEFAULT_MIN_CUT_FRAMES = 84.0  # 3.5s @ 24fps

    def __init__(
        self,
        timeline: Any,
        media_pool: Any | None = None,
        target_track_name: str = "DF_BROLL",
        max_cut_frames: float = DEFAULT_MAX_CUT_FRAMES,
        min_cut_frames: float = DEFAULT_MIN_CUT_FRAMES,
    ) -> None:
        self.timeline = timeline
        self.media_pool = media_pool
        self.target_track_name = target_track_name
        self.max_cut_frames = max_cut_frames
        self.min_cut_frames = min_cut_frames
        self._imported_cache: dict[str, Any] = {}

    def _resolve_timeline_fps(self) -> float:
        """Obtiene la tasa de fotogramas configurada en la línea de tiempo activa."""
        if hasattr(self.timeline, "GetSetting"):
            fps_str = self.timeline.GetSetting("timelineFrameRate")
            if fps_str:
                try:
                    return float(fps_str)
                except ValueError:
                    pass
        return 24.0

    def resolve_target_track_index(self, create_if_missing: bool = True) -> int:
        """Identifica o crea la pista de vídeo para B-Rolls sin perturbar pistas de usuario."""
        count = int(self.timeline.GetTrackCount("video") or 0)
        for idx in range(1, count + 1):
            name = str(self.timeline.GetTrackName("video", idx) or "")
            if name == self.target_track_name:
                return idx

        # Si no existe y se solicita crearla
        if create_if_missing:
            add_fn = getattr(self.timeline, "AddTrack", None)
            set_name_fn = getattr(self.timeline, "SetTrackName", None)
            if callable(add_fn):
                if add_fn("video") is True:
                    new_count = int(self.timeline.GetTrackCount("video") or 0)
                    if callable(set_name_fn):
                        set_name_fn("video", new_count, self.target_track_name)
                    return new_count

        return 1  # Fallback a V1 si no se puede crear

    def get_or_create_broll_bin(self, bin_name: str = "B-Roll") -> Any:
        """Asegura la existencia de una carpeta dedicada en el Media Pool."""
        if self.media_pool is None:
            return None

        root_folder = self.media_pool.GetRootFolder()
        if root_folder is None:
            return None

        # Buscar si ya existe la subcarpeta
        subfolders = root_folder.GetSubFolderList() or []
        for sf in subfolders:
            if sf.GetName() == bin_name:
                return sf

        # Crear subcarpeta
        add_fn = getattr(self.media_pool, "AddSubFolder", None)
        if callable(add_fn):
            return add_fn(root_folder, bin_name)
        return root_folder

    def import_broll_asset(self, file_path: str, target_bin: Any | None = None) -> Any:
        """Importa un archivo al Media Pool de forma idempotente."""
        resolved = str(Path(file_path).resolve())
        if resolved in self._imported_cache:
            return self._imported_cache[resolved]

        if self.media_pool is None:
            return None

        if target_bin is not None:
            set_folder_fn = getattr(self.media_pool, "SetCurrentFolder", None)
            if callable(set_folder_fn):
                set_folder_fn(target_bin)

        import_fn = getattr(self.media_pool, "ImportMedia", None)
        if not callable(import_fn):
            raise BRollWriteError("El Media Pool no expone ImportMedia.")

        imported_items = import_fn([resolved])
        if not imported_items:
            raise BRollWriteError(f"Resolve no pudo importar el archivo: {resolved}")

        item = imported_items[0] if isinstance(imported_items, list) else list(imported_items.values())[0]
        self._imported_cache[resolved] = item
        return item

    def calculate_source_duration(self, duration_tl: float, clip_item: Any, timeline_fps: float) -> int:
        """Calcula los fotogramas fuente necesarios considerando la diferencia de FPS.
        
        DaVinci Resolve interpreta startFrame/endFrame en la base de fotogramas del clip,
        no de la línea de tiempo. Por tanto, para un clip de 30fps en timeline de 24fps:
        dur_src = ceil(dur_tl * (30 / 24)).
        """
        src_fps = timeline_fps
        if clip_item is not None and hasattr(clip_item, "GetClipProperty"):
            try:
                fps_val = clip_item.GetClipProperty("FPS")
                if isinstance(fps_val, (int, float)):
                    src_fps = float(fps_val)
                elif isinstance(fps_val, str) and fps_val.strip():
                    src_fps = float(fps_val.strip())
            except Exception:
                pass

        return max(1, int(math.ceil(duration_tl * (src_fps / timeline_fps))))

    def plan_cuts_for_proposal(
        self,
        proposal: BRollProposal,
        timeline_fps: float,
        split_for_copyright: bool = True,
    ) -> list[BRollCut]:
        """Divide una propuesta larga en cortes bajo el umbral de Content ID si es necesario."""
        total_dur = proposal.end_frame - proposal.start_frame
        if total_dur <= 0:
            return []

        if not split_for_copyright or total_dur <= self.max_cut_frames:
            return [
                BRollCut(
                    asset_id=proposal.asset.id,
                    asset_name=proposal.asset.name,
                    file_path=proposal.asset.file_path,
                    start_frame_tl=proposal.start_frame,
                    end_frame_tl=proposal.end_frame,
                    duration_tl=total_dur,
                )
            ]

        # Segmentar en bloques seguros
        cuts: list[BRollCut] = []
        rem = total_dur
        curr_start = proposal.start_frame
        src_offset = 0

        while rem > 0:
            chunk = min(rem, self.max_cut_frames)
            # Evitar dejar un resto minúsculo al final
            if rem - chunk > 0 and rem - chunk < self.min_cut_frames:
                chunk = rem / 2.0

            cuts.append(
                BRollCut(
                    asset_id=proposal.asset.id,
                    asset_name=proposal.asset.name,
                    file_path=proposal.asset.file_path,
                    start_frame_tl=curr_start,
                    end_frame_tl=curr_start + chunk,
                    start_frame_src=src_offset,
                    duration_tl=chunk,
                )
            )
            curr_start += chunk
            src_offset += int(chunk)
            rem -= chunk

        return cuts

    def clean_target_track(self, track_index: int | None = None) -> int:
        """Elimina de forma segura los clips de la pista destino sin borrar la pista."""
        idx = track_index if track_index is not None else self.resolve_target_track_index(create_if_missing=False)
        items = self.timeline.GetItemListInTrack("video", idx) or []
        if isinstance(items, dict):
            items = list(items.values())
        if not items:
            return 0

        del_fn = getattr(self.timeline, "DeleteClips", None)
        if callable(del_fn):
            del_fn(items, False)
            return len(items)
        return 0

    def audit_track(self, track_index: int | None = None) -> BRollAuditReport:
        """Verifica la integridad de la pista: ausencia de huecos (gaps) y cumplimiento de copyright."""
        idx = track_index if track_index is not None else self.resolve_target_track_index(create_if_missing=False)
        items = self.timeline.GetItemListInTrack("video", idx) or []
        if isinstance(items, dict):
            items = list(items.values())

        if not items:
            return BRollAuditReport(track_index=idx, total_clips=0, total_duration_frames=0.0)

        total_dur = 0.0
        gaps: list[tuple[float, float, float]] = []
        exceeding: list[tuple[str, float]] = []

        # Ordenar clips por punto de entrada
        sorted_items = sorted(items, key=lambda it: float(it.GetStart()))

        prev_end: float | None = None
        for it in sorted_items:
            start = float(it.GetStart())
            end = float(it.GetEnd())
            dur = end - start
            total_dur += dur
            name = str(it.GetName() or "clip")

            if dur > self.max_cut_frames + 1.0:  # Tolerancia de 1 frame
                exceeding.append((name, dur))

            if prev_end is not None:
                gap = start - prev_end
                if gap > 0.5:  # Más de medio frame se considera hueco
                    gaps.append((prev_end, start, gap))

            prev_end = end

        return BRollAuditReport(
            track_index=idx,
            total_clips=len(sorted_items),
            total_duration_frames=total_dur,
            gaps=gaps,
            clips_exceeding_copyright=exceeding,
        )

    def apply_brolls(
        self,
        proposals: Sequence[BRollProposal],
        dry_run: bool = False,
        clean_track_first: bool = False,
        split_for_copyright: bool = True,
        target_bin_name: str = "B-Roll",
    ) -> BRollExecutionResult:
        """Ejecuta el montaje completo de B-Rolls con encadenamiento dinámico y cero huecos.
        
        Reglas clave:
        1. 'mediaType': 1 -> Nunca toca ni sobreescribe audio (A1/A2/A3/A4 protegidas).
        2. Encadenamiento dinámico: cada corte se ancla al final real del anterior (items[-1].GetEnd()).
        3. Compensación de FPS según clip fuente.
        """
        if not proposals:
            track_idx = self.resolve_target_track_index(create_if_missing=False)
            return BRollExecutionResult(
                status="completed",
                total_cuts_inserted=0,
                total_frames_covered=0.0,
                track_index=track_idx,
                target_track_name=self.target_track_name,
            )

        tl_fps = self._resolve_timeline_fps()
        track_idx = self.resolve_target_track_index(create_if_missing=not dry_run)

        # 1. Expandir propuestas en cortes seguros
        planned_cuts: list[BRollCut] = []
        for prop in proposals:
            planned_cuts.extend(self.plan_cuts_for_proposal(prop, tl_fps, split_for_copyright=split_for_copyright))

        if dry_run:
            total_frames = sum(c.duration for c in planned_cuts)
            return BRollExecutionResult(
                status="dry_run",
                total_cuts_inserted=len(planned_cuts),
                total_frames_covered=total_frames,
                track_index=track_idx,
                target_track_name=self.target_track_name,
                cuts=planned_cuts,
            )

        # 2. Limpieza si se solicitó
        if clean_track_first:
            self.clean_target_track(track_idx)

        # 3. Preparar bin en Media Pool
        target_bin = self.get_or_create_broll_bin(target_bin_name)

        # 4. Inserción con encadenamiento dinámico
        append_fn = getattr(self.media_pool, "AppendToTimeline", None)
        if not callable(append_fn):
            raise BRollWriteError("El Media Pool no expone AppendToTimeline.")

        executed_cuts: list[BRollCut] = []
        current_record_frame: float | None = None

        for cut in planned_cuts:
            media_item = self.import_broll_asset(cut.file_path, target_bin=target_bin)
            dur_src = self.calculate_source_duration(cut.duration, media_item, tl_fps)

            # Si es el primer clip o si hay un salto intencionado respecto a la propuesta
            if current_record_frame is None:
                record_frame = cut.start_frame_tl
            else:
                # Si el corte es contiguo (< 2 frames de diferencia), encadenar exactamente al anterior
                if abs(cut.start_frame_tl - current_record_frame) <= 2.0:
                    record_frame = current_record_frame
                else:
                    record_frame = cut.start_frame_tl

            clip_info = {
                "mediaPoolItem": media_item,
                "startFrame": cut.start_frame_src,
                "endFrame": cut.start_frame_src + dur_src,
                "trackIndex": track_idx,
                "recordFrame": int(round(record_frame)),
                "mediaType": 1,  # 1 = Solo vídeo, NUNCA sobreescribir audio
            }

            result = append_fn([clip_info])
            items = list(result.values()) if isinstance(result, dict) else list(result or [])

            if not items:
                raise BRollWriteError(
                    f"Resolve rechazó la inserción del B-Roll '{cut.asset_name}' en fotograma {record_frame}."
                )

            last_item = items[-1]
            actual_start = float(last_item.GetStart())
            actual_end = float(last_item.GetEnd())

            # Encadenar dinámicamente para el siguiente corte
            current_record_frame = actual_end

            executed_cuts.append(
                BRollCut(
                    asset_id=cut.asset_id,
                    asset_name=cut.asset_name,
                    file_path=cut.file_path,
                    start_frame_tl=cut.start_frame_tl,
                    end_frame_tl=cut.end_frame_tl,
                    start_frame_src=cut.start_frame_src,
                    duration_tl=cut.duration_tl,
                    actual_start_tl=actual_start,
                    actual_end_tl=actual_end,
                )
            )

        # 5. Auditoría posterior a la inserción
        audit = self.audit_track(track_idx)
        total_covered = sum(c.duration for c in executed_cuts)

        return BRollExecutionResult(
            status="completed",
            total_cuts_inserted=len(executed_cuts),
            total_frames_covered=total_covered,
            track_index=track_idx,
            target_track_name=self.target_track_name,
            cuts=executed_cuts,
            audit=audit,
        )
