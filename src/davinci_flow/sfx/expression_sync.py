"""Sincronizador automático de efectos de sonido (SFX) con expresiones visuales.

Diseñado para Shorts y contenido vertical: detecta cortes de expresión en la pista
de personaje (ej. V4 con Ely VTuber) e inserta automáticamente efectos de sonido
en la pista de audio dedicada (ej. A4) con alineación y anticipación exacta de fotogramas.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

from davinci_flow.errors import DaVinciFlowError, TimelineWriteError
from davinci_flow.sfx.assets import ensure_builtin_sfx_assets
from davinci_flow.sfx.catalog import DEFAULT_SFX_ASSETS, AssetDescriptor, SFXCatalog


class SFXSyncError(DaVinciFlowError):
    """Error durante la detección o sincronización de SFX para expresiones."""


@dataclass(frozen=True, slots=True)
class ExpressionCutEvent:
    """Evento visual de cambio de expresión o corte en la pista de personaje."""

    frame: int
    clip_name: str
    previous_clip_name: str | None
    event_type: str  # 'pop', 'swoosh', 'bubble'
    sfx_asset_name: str
    target_frame: int
    lead_frames: int = 0
    duration_frames: int = 24


# Rutas por defecto a los recursos SFX del creador en Windows
DEFAULT_POP_DIR = Path(r"D:\Vídeos\Assets\02_Audio\Efectos\Sonidos de Transición - Movimiento\Pop")
DEFAULT_WHOOSH_DIR = Path(r"D:\Vídeos\Assets\02_Audio\Efectos\Sonidos de Transición - Movimiento\Whoosh")


class SFXExpressionSynchronizer:
    """Inspecciona pistas de expresiones de personaje y genera sincronización de SFX en audio."""

    def __init__(
        self,
        timeline: Any,
        media_pool: Any | None = None,
        sfx_catalog: SFXCatalog | None = None,
        custom_sfx_dirs: Sequence[Path] | None = None,
        min_cooldown_frames: int = 14,
        swoosh_lead_frames: int = 3,
    ) -> None:
        self.timeline = timeline
        self.media_pool = media_pool
        self.catalog = sfx_catalog or SFXCatalog()
        self.min_cooldown_frames = max(1, min_cooldown_frames)
        self.swoosh_lead_frames = max(0, swoosh_lead_frames)

        self._sfx_search_dirs: list[Path] = []
        if custom_sfx_dirs:
            self._sfx_search_dirs.extend(d for d in custom_sfx_dirs if d.is_dir())
        for default_dir in (DEFAULT_POP_DIR, DEFAULT_WHOOSH_DIR):
            if default_dir.is_dir() and default_dir not in self._sfx_search_dirs:
                self._sfx_search_dirs.append(default_dir)

        self._imported_sfx_cache: dict[str, Any] = {}

    def scan_expression_cuts(
        self,
        expression_track_index: int = 4,
    ) -> tuple[ExpressionCutEvent, ...]:
        """Analiza la pista de video dada y detecta los puntos de transición de expresiones."""
        get_items = getattr(self.timeline, "GetItemListInTrack", None)
        if not callable(get_items):
            return ()

        try:
            items = get_items("video", expression_track_index) or []
        except Exception:
            return ()

        clip_list = list(items.values() if isinstance(items, dict) else items)
        if not clip_list:
            return ()

        # Ordenar clips cronológicamente por su punto de inicio
        sorted_clips = sorted(
            clip_list,
            key=lambda c: getattr(c, "GetStart", lambda: 0)() or 0,
        )

        events: list[ExpressionCutEvent] = []
        last_sfx_frame = -float("inf")
        pop_toggle = False

        for i, clip in enumerate(sorted_clips):
            start = getattr(clip, "GetStart", lambda: 0)() or 0
            start_frame = round(start)
            name = getattr(clip, "GetName", lambda: f"Clip_{i}")() or f"Clip_{i}"
            prev_name = (
                getattr(sorted_clips[i - 1], "GetName", lambda: None)()
                if i > 0
                else None
            )

            # Clasificar si el evento amerita swoosh o pop
            name_lower = name.lower()
            is_swoosh = any(k in name_lower for k in ("swoosh", "whoosh", "transicion", "movimiento", "giro"))
            is_first_clip = (i == 0)

            # Si es el primer clip o cambio marcado de postura, o nombre contiene swoosh
            if is_swoosh or (is_first_clip and "intro" in name_lower):
                lead = self.swoosh_lead_frames
                target = max(0, start_frame - lead)
                event_type = "swoosh"
                sfx_name = "swoosh_02"
                dur = 24
            else:
                lead = 0
                target = start_frame
                event_type = "pop"
                # Alternar entre pop_02 y suction_pop_07 para mayor dinamismo auditivo
                sfx_name = "suction_pop_07" if pop_toggle else "pop_02"
                dur = 12

            # Verificar cooldown para evitar saturar el audio si hay microcortes
            if target - last_sfx_frame < self.min_cooldown_frames:
                continue

            if event_type == "pop":
                pop_toggle = not pop_toggle

            last_sfx_frame = target
            events.append(
                ExpressionCutEvent(
                    frame=start_frame,
                    clip_name=name,
                    previous_clip_name=prev_name,
                    event_type=event_type,
                    sfx_asset_name=sfx_name,
                    target_frame=target,
                    lead_frames=lead,
                    duration_frames=dur,
                )
            )

        return tuple(events)

    def apply_sfx_sync(
        self,
        expression_track_index: int = 4,
        sfx_audio_track_index: int = 4,
        dry_run: bool = False,
    ) -> tuple[ExpressionCutEvent, ...]:
        """Detecta los eventos de corte en expresiones e inserta los SFX en la pista de audio."""
        events = self.scan_expression_cuts(expression_track_index)
        if not events or dry_run:
            return events

        # Asegurar pista de audio suficiente
        self._ensure_audio_tracks(sfx_audio_track_index)

        inserted_events: list[ExpressionCutEvent] = []
        for ev in events:
            media_item = self._resolve_sfx_media_item(ev.sfx_asset_name)
            if media_item is None:
                continue

            success = self._insert_sfx_clip(
                media_item=media_item,
                audio_track_index=sfx_audio_track_index,
                record_frame=ev.target_frame,
                duration_frames=ev.duration_frames,
                clip_label=f"SFX_{ev.event_type}_{ev.target_frame}",
            )
            if success:
                inserted_events.append(ev)

        return tuple(inserted_events)

    def _ensure_audio_tracks(self, target_index: int) -> None:
        get_count = getattr(self.timeline, "GetTrackCount", None)
        add_track = getattr(self.timeline, "AddTrack", None)
        if not callable(get_count) or not callable(add_track):
            return

        current_count = get_count("audio") or 0
        while current_count < target_index:
            success = add_track("audio")
            if not success:
                break
            new_count = get_count("audio")
            if new_count is not None and new_count > current_count:
                current_count = new_count
            else:
                current_count += 1

    def _resolve_sfx_media_item(self, asset_name: str) -> Any | None:
        """Localiza en disco e importa al Media Pool el archivo de efecto sonoro requerido."""
        cached = self._imported_sfx_cache.get(asset_name)
        if cached is not None:
            return cached

        if self.media_pool is None:
            return None

        # 1. Buscar archivo en disco en los directorios de SFX
        file_path = self._find_sfx_file_on_disk(asset_name)

        # 2. Si no se encuentra en directorios de usuario, buscar en recursos predeterminados
        if file_path is None:
            builtin_paths = ensure_builtin_sfx_assets()
            cand = builtin_paths.get(asset_name)
            if cand and Path(cand).is_file():
                file_path = Path(cand)

        if file_path is None or not file_path.is_file():
            return None

        # 3. Comprobar si ya está en el Media Pool
        root_folder = getattr(self.media_pool, "GetRootFolder", lambda: None)()
        if root_folder is not None:
            existing = self._find_clip_in_folder(root_folder, file_path.name)
            if existing is not None:
                self._imported_sfx_cache[asset_name] = existing
                return existing

        # 4. Importar mediante ImportMedia
        import_fn = getattr(self.media_pool, "ImportMedia", None)
        if callable(import_fn):
            try:
                imported = import_fn([str(file_path)])
                if imported:
                    items = list(imported.values() if isinstance(imported, dict) else imported)
                    if items:
                        self._imported_sfx_cache[asset_name] = items[0]
                        return items[0]
            except Exception:
                pass

        return None

    def _find_sfx_file_on_disk(self, asset_name: str) -> Path | None:
        name_clean = asset_name.lower().replace("sfx_", "")
        for sfx_dir in self._sfx_search_dirs:
            if not sfx_dir.is_dir():
                continue
            for entry in sfx_dir.iterdir():
                if not entry.is_file():
                    continue
                if entry.suffix.lower() in (".mp3", ".wav", ".aac", ".ogg", ".flac"):
                    stem_clean = entry.stem.lower()
                    if name_clean in stem_clean or stem_clean in name_clean:
                        return entry
        return None

    def _find_clip_in_folder(self, folder: Any, filename: str) -> Any | None:
        get_clips = getattr(folder, "GetClipList", None)
        if callable(get_clips):
            clips = get_clips() or []
            clip_iter = clips.values() if isinstance(clips, dict) else clips
            for c in clip_iter:
                if getattr(c, "GetName", lambda: "")() == filename:
                    return c

        get_subfolders = getattr(folder, "GetSubFolderList", None)
        if callable(get_subfolders):
            subfolders = get_subfolders() or []
            sf_iter = subfolders.values() if isinstance(subfolders, dict) else subfolders
            for sf in sf_iter:
                found = self._find_clip_in_folder(sf, filename)
                if found is not None:
                    return found
        return None

    def _insert_sfx_clip(
        self,
        media_item: Any,
        audio_track_index: int,
        record_frame: int,
        duration_frames: int,
        clip_label: str,
    ) -> bool:
        """Añade el clip de audio al track especificado con AppendToTimeline."""
        append_fn = getattr(self.media_pool, "AppendToTimeline", None)
        if not callable(append_fn):
            return False

        clip_info = {
            "mediaPoolItem": media_item,
            "startFrame": 0,
            "endFrame": float(duration_frames),
            "mediaType": 2,  # Audio only
            "trackIndex": audio_track_index,
            "recordFrame": record_frame,
        }

        try:
            result = append_fn([clip_info])
            if result:
                items = list(result.values() if isinstance(result, dict) else result)
                if items and clip_label:
                    set_name = getattr(items[0], "SetName", None)
                    if callable(set_name):
                        try:
                            set_name(clip_label)
                        except Exception:
                            pass
                return True
        except Exception:
            return False

        return False
