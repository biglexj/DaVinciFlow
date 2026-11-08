"""Efectos Fusion editables para DaVinci Flow.

Dos caminos, ambos **editables** en Resolve (nada se hornea ni se rasteriza):

- ``insert_composition``: genera una composición Fusion (``Text+`` con animación) como
  archivo ``.comp``, la importa al Media Pool y la anexa a la línea de tiempo. El
  resultado es una composición que se sigue pudiendo editar en la página Fusion.
- ``insert_native_title``: inserta un título nativo de Resolve (``Text+``, ``Fade On``,
  ``Headline``…) con la API oficial, sin rehacer el trabajo de catálogo que vive en
  ``davinci_flow.resolve.kinetic_titles``.

Reglas heredadas del puente de Resolve: una escritura no se reintenta sola y, si
Resolve no confirma el resultado, se informa con precisión en lugar de insistir.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from davinci_flow.errors import FusionEffectError
from davinci_flow.generation.fusion_template import (
    SUPPORTED_ANIMATION_PRESETS,
    generate_textplus_fusion_setting,
    hex_to_rgb_float,
)
from davinci_flow.themes.tokens import ThemeTokens, get_theme

ROLE_MAIN = "main"
ROLE_CONTEXT = "context"
ROLE_ACCENT = "accent"
VALID_ROLES = (ROLE_MAIN, ROLE_CONTEXT, ROLE_ACCENT)

TOOLS_MARKER = "\tTools = ordered() {\n"
MEDIAOUT_SOURCE = re.compile(r'SourceOp = "(DF_Transform_[A-Za-z_]+)"')


@dataclass(frozen=True, slots=True)
class FusionEffectSpec:
    """Descripción de un efecto Fusion generado por DaVinci Flow."""

    text: str
    role: str = ROLE_MAIN
    animation_preset: str = "fade_smooth"
    position_x: float = 0.5
    position_y: float = 0.15
    glow: float = 0.0
    theme: str = "ely"

    def validate(self) -> None:
        if not self.text.strip():
            raise FusionEffectError("El texto del efecto no puede estar vacío.")
        if self.role not in VALID_ROLES:
            raise FusionEffectError(
                f"Rol desconocido: '{self.role}'. Roles válidos: {', '.join(VALID_ROLES)}."
            )
        if self.animation_preset not in SUPPORTED_ANIMATION_PRESETS:
            raise FusionEffectError(
                f"Animación desconocida: '{self.animation_preset}'. "
                f"Disponibles: {', '.join(SUPPORTED_ANIMATION_PRESETS)}."
            )
        if not 0.0 <= self.position_x <= 1.0 or not 0.0 <= self.position_y <= 1.0:
            raise FusionEffectError("La posición del efecto debe estar entre 0 y 1.")
        if not 0.0 <= self.glow <= 1.0:
            raise FusionEffectError("El brillo del efecto debe estar entre 0 y 1.")


@dataclass(frozen=True, slots=True)
class FusionEffectResult:
    """Confirmación de un efecto insertado en la línea de tiempo."""

    kind: str
    name: str
    track_index: int
    start_frame: float
    end_frame: float
    comp_path: str = ""
    item_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tipo": self.kind,
            "nombre": self.name,
            "pista": self.track_index,
            "inicio": self.start_frame,
            "fin": self.end_frame,
            "archivo": self.comp_path,
            "elemento": self.item_name,
        }


def build_effect_setting(spec: FusionEffectSpec, tokens: ThemeTokens | None = None) -> str:
    """Genera el contenido de la composición Fusion a partir de la especificación."""
    spec.validate()
    theme = tokens or get_theme(spec.theme)

    setting = generate_textplus_fusion_setting(
        text=spec.text,
        tokens=theme,
        role=spec.role,
        pos_x=spec.position_x,
        pos_y=spec.position_y,
        animation_preset=spec.animation_preset,
    )

    if spec.glow > 0:
        setting = _inject_glow(setting, spec.glow)

    return setting


def _inject_glow(setting: str, strength: float) -> str:
    """Añade un nodo Glow entre la transformación y la salida de la composición."""
    if TOOLS_MARKER not in setting:
        raise FusionEffectError("La composición generada no tiene la estructura esperada.")

    match = MEDIAOUT_SOURCE.search(setting)
    if not match:
        raise FusionEffectError("No se encontró la salida de medios en la composición.")
    upstream = match.group(1)

    glow_tool = (
        "\t\tDF_Glow = Glow {\n"
        "\t\t\tInputs = {\n"
        "\t\t\t\tThreshold = Input { Value = 0.4, },\n"
        f"\t\t\t\tGain = Input {{ Value = {max(0.1, float(strength)):.4f}, }},\n"
        "\t\t\t\tInput = Input {\n"
        f"\t\t\t\t\tSourceOp = \"{upstream}\",\n"
        "\t\t\t\t\tSource = \"Output\",\n"
        "\t\t\t\t},\n"
        "\t\t\t},\n"
        "\t\t\tViewInfo = OperatorInfo { Pos = { 540, 82.5 } },\n"
        "\t\t},\n"
    )

    setting = setting.replace(TOOLS_MARKER, TOOLS_MARKER + glow_tool, 1)
    return setting.replace(f'SourceOp = "{upstream}"', 'SourceOp = "DF_Glow"', 1)


class FusionEffectWriter:
    """Inserta efectos Fusion editables en la línea de tiempo activa."""

    def __init__(self, session: Any, temp_root: Path | None = None) -> None:
        self.session = session
        self.timeline = session.timeline
        self.media_pool = session.project.GetMediaPool()
        if self.media_pool is None:
            raise FusionEffectError("El proyecto activo no expone el Media Pool.")
        self.temp_root = temp_root or Path.home() / ".davinci_flow" / "fusion_effects"

    def insert_composition(
        self,
        spec: FusionEffectSpec,
        start_frame: float,
        duration_frames: float,
        track_index: int | None = None,
        tokens: ThemeTokens | None = None,
    ) -> FusionEffectResult:
        """Genera, importa y anexa una composición Fusion editable."""
        if start_frame < 0:
            raise FusionEffectError("El fotograma de inicio no puede ser negativo.")
        if duration_frames <= 0:
            raise FusionEffectError("La duración del efecto debe ser positiva.")

        setting = build_effect_setting(spec, tokens)
        self.temp_root.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^A-Za-z0-9_]+", "_", spec.text.strip())[:40] or "efecto"
        comp_path = self.temp_root / f"{safe_name}.comp"
        comp_path.write_text(setting, encoding="utf-8")

        item = self._import_media(str(comp_path))
        target_track = track_index or self._resolve_video_track()
        end_frame = start_frame + duration_frames

        appended = self._append_to_timeline(item, target_track, start_frame)
        if appended is None:
            raise FusionEffectError(
                "Resolve no confirmó la inserción de la composición en la línea de tiempo."
            )

        return FusionEffectResult(
            kind="composicion_fusion",
            name=spec.text,
            track_index=target_track,
            start_frame=start_frame,
            end_frame=end_frame,
            comp_path=str(comp_path),
            item_name=str(getattr(appended, "GetName", lambda: "")() or ""),
        )

    def insert_native_title(
        self,
        template_name: str,
        start_frame: float,
        duration_frames: float,
        track_index: int | None = None,
    ) -> FusionEffectResult:
        """Inserta un título nativo de Resolve (Text+, Fade On, Headline…) editable."""
        if not template_name.strip():
            raise FusionEffectError("El nombre del título nativo está vacío.")
        if start_frame < 0:
            raise FusionEffectError("El fotograma de inicio no puede ser negativo.")
        if duration_frames <= 0:
            raise FusionEffectError("La duración del título debe ser positiva.")

        insert = getattr(self.timeline, "InsertFusionTitleIntoTimeline", None)
        if not callable(insert):
            raise FusionEffectError("Esta versión de Resolve no expone InsertFusionTitleIntoTimeline.")

        # La pista se resuelve antes de insertar: si no hay destino válido, no se
        # deja ningún título suelto en la línea de tiempo.
        target_track = track_index or self._resolve_video_track()

        title_item = insert(template_name)
        if title_item is None:
            raise FusionEffectError(
                f"Resolve no encontró el título nativo '{template_name}'."
            )

        try:
            self._move_to_track(title_item, target_track)
            self._set_start(title_item, start_frame)
            self._set_duration(title_item, duration_frames)
        except Exception:
            self._delete_item(title_item)
            raise

        return FusionEffectResult(
            kind="titulo_nativo",
            name=template_name,
            track_index=target_track,
            start_frame=start_frame,
            end_frame=start_frame + duration_frames,
            item_name=str(getattr(title_item, "GetName", lambda: "")() or template_name),
        )

    def _import_media(self, path: str) -> Any:
        """Importa un archivo al Media Pool y devuelve el elemento creado."""
        import_fn = getattr(self.media_pool, "ImportMedia", None)
        if not callable(import_fn):
            raise FusionEffectError("El Media Pool no expone ImportMedia.")
        imported = import_fn([{"FilePath": path}])
        if not imported:
            raise FusionEffectError(f"Resolve no pudo importar el archivo: {path}")
        if isinstance(imported, dict):
            imported = list(imported.values())
        return imported[0]

    def _append_to_timeline(self, item: Any, track_index: int, record_frame: float) -> Any:
        """Anexa un elemento del Media Pool a una pista de vídeo."""
        append_fn = getattr(self.media_pool, "AppendToTimeline", None)
        if not callable(append_fn):
            raise FusionEffectError("El Media Pool no expone AppendToTimeline.")
        result = append_fn(
            [
                {
                    "mediaPoolItem": item,
                    "mediaType": 1,
                    "trackIndex": track_index,
                    "recordFrame": record_frame,
                }
            ]
        )
        if isinstance(result, dict):
            result = list(result.values())
        if not result:
            return None
        return result[0]

    def _resolve_video_track(self) -> int:
        """Devuelve el índice de la última pista de vídeo de la línea de tiempo."""
        count = int(self.timeline.GetTrackCount("video") or 0)
        if count < 1:
            raise FusionEffectError("La línea de tiempo no tiene pistas de vídeo.")
        return count

    def _move_to_track(self, item: Any, track_index: int) -> None:
        """Mueve un elemento a la pista indicada."""
        for track_type in ("video", "audio"):
            count = int(self.timeline.GetTrackCount(track_type) or 0)
            for index in range(1, count + 1):
                items = self._items_in_track(track_type, index)
                if item in items:
                    if track_type == "video" and index == track_index:
                        return
                    self.timeline.MoveClip(item, track_type, index, 0)
                    return
        raise FusionEffectError("No se encontró el elemento insertado en la línea de tiempo.")

    def _set_duration(self, item: Any, duration_frames: float) -> None:
        """Fija la duración del elemento."""
        self._set_end(item, duration_frames)

    def _set_end(self, item: Any, duration_frames: float) -> None:
        """Fija el fotograma final del elemento."""
        start = float(item.GetStart() or 0)
        item.SetEnd(start + duration_frames)

    def _set_start(self, item: Any, start_frame: float) -> None:
        """Fija el fotograma inicial del elemento."""
        item.SetStart(start_frame)

    def _delete_item(self, item: Any) -> None:
        """Elimina un elemento; los fallos no ocultan el error original."""
        try:
            self.timeline.DeleteClips([item], False)
        except Exception:
            pass

    def _items_in_track(self, track_type: str, index: int) -> list[Any]:
        """Devuelve los elementos de una pista como lista."""
        items = self.timeline.GetItemListInTrack(track_type, index) or []
        if isinstance(items, dict):
            items = list(items.values())
        return list(items)
