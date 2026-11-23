"""Motor de subtítulos cinéticos nativos para DaVinci Resolve.

Permite insertar títulos Fusion animados (Statement, Word Highlight, Rotate, etc.)
directamente en pistas dedicadas (ej. V3) con StyledText editable en el Inspector,
sin generar archivos intermediarios pre-renderizados (.mov ni carriers .avi).
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence
import zipfile

from davinci_flow.errors import DaVinciFlowError, TimelineWriteError


class KineticTitleError(DaVinciFlowError):
    """Error al localizar, importar o configurar un título cinético en Resolve."""


@dataclass(frozen=True, slots=True)
class KineticTitleDescriptor:
    """Descriptor de una plantilla de título cinético nativo."""

    id: str
    name: str
    resolve_template_name: str
    category: str = "Animated"
    description: str = ""
    drfx_rel_path: str = ""
    drb_filename: str = ""
    default_font: str = "Open Sans"
    default_style: str = "Extrabold Italic"


# Catálogo estándar de subtítulos cinéticos y títulos nativos disponibles en Resolve
BUILTIN_KINETIC_TITLES: Sequence[KineticTitleDescriptor] = (
    # Subtítulos cinéticos de alto impacto
    KineticTitleDescriptor(
        id="statement",
        name="Statement",
        resolve_template_name="Statement",
        category="Animated",
        description="Subtítulo audaz inclinado con realce de fondo rojo y animación pop.",
        drfx_rel_path="Edit/Titles/Subtitles/Animated/Statement.setting",
        drb_filename="SC-87-Impact Statement.drb",
        default_font="Open Sans",
        default_style="Extrabold Italic",
    ),
    KineticTitleDescriptor(
        id="word_highlight",
        name="Word Highlight",
        resolve_template_name="Word Highlight",
        category="Animated",
        description="Subtítulo con resaltado dinámico palabra por palabra.",
        drfx_rel_path="Edit/Titles/Subtitles/Animated/Word Highlight.setting",
        drb_filename="",
        default_font="Open Sans",
        default_style="Bold",
    ),
    KineticTitleDescriptor(
        id="rotate",
        name="Rotate",
        resolve_template_name="Rotate",
        category="Animated",
        description="Subtítulo con animación de rotación al entrar.",
        drfx_rel_path="Edit/Titles/Subtitles/Animated/Rotate.setting",
        drb_filename="",
        default_font="Open Sans",
        default_style="Bold",
    ),
    KineticTitleDescriptor(
        id="lollipop",
        name="Lollipop",
        resolve_template_name="Lollipop",
        category="Animated",
        description="Subtítulo con rebote suave y colores vibrantes.",
        drfx_rel_path="Edit/Titles/Subtitles/Animated/Lollipop.setting",
        drb_filename="",
        default_font="Open Sans",
        default_style="Bold",
    ),
    KineticTitleDescriptor(
        id="slide_in",
        name="Slide In",
        resolve_template_name="Slide In",
        category="Animated",
        description="Subtítulo cinético con deslizamiento lateral.",
        drfx_rel_path="Edit/Titles/Subtitles/Animated/Slide In.setting",
        drb_filename="",
        default_font="Open Sans",
        default_style="Bold",
    ),
    # Títulos Fusion nativos integrados de DaVinci Resolve
    KineticTitleDescriptor(
        id="text_plus",
        name="Text+",
        resolve_template_name="Text+",
        category="Native",
        description="Generador base Text+ nativo y editable de DaVinci Resolve.",
        drfx_rel_path="",
        default_font="Montserrat",
        default_style="Bold",
    ),
    KineticTitleDescriptor(
        id="ribbon_text",
        name="Ribbon Text",
        resolve_template_name="Ribbon Text",
        category="Native",
        description="Texto con cinta horizontal de fondo y animación de recorte.",
        drfx_rel_path="Edit/Titles/Ribbon Text.setting",
        default_font="Montserrat",
        default_style="Bold",
    ),
    KineticTitleDescriptor(
        id="text_box",
        name="Text Box",
        resolve_template_name="Text Box",
        category="Native",
        description="Texto enmarcado en caja rectangular con bordes limpios.",
        drfx_rel_path="Edit/Titles/Text Box.setting",
        default_font="Montserrat",
        default_style="Bold",
    ),
    KineticTitleDescriptor(
        id="fade_on",
        name="Fade On",
        resolve_template_name="Fade On",
        category="Native",
        description="Entrada suave con fundido gradual de opacidad.",
        drfx_rel_path="Edit/Titles/Fade On.setting",
        default_font="Montserrat",
        default_style="SemiBold",
    ),
    KineticTitleDescriptor(
        id="rise_fade",
        name="Rise Fade",
        resolve_template_name="Rise Fade",
        category="Native",
        description="Elevación vertical combinada con desvanecimiento suave.",
        drfx_rel_path="Edit/Titles/Rise Fade.setting",
        default_font="Montserrat",
        default_style="Bold",
    ),
    KineticTitleDescriptor(
        id="drop_in",
        name="Drop In",
        resolve_template_name="Drop In",
        category="Native",
        description="Caída vertical dinámica con amortiguación elástica.",
        drfx_rel_path="Edit/Titles/Drop In.setting",
        default_font="Montserrat",
        default_style="Bold",
    ),
    KineticTitleDescriptor(
        id="digital_glitch",
        name="Digital Glitch",
        resolve_template_name="Digital Glitch",
        category="Native",
        description="Efecto de interferencia y glitch digital cibernético.",
        drfx_rel_path="Edit/Titles/Digital Glitch.setting",
        default_font="Montserrat",
        default_style="Black",
    ),
    KineticTitleDescriptor(
        id="headline",
        name="Headline",
        resolve_template_name="Headline",
        category="Native",
        description="Titular destacado de alto impacto para noticias y editoriales.",
        drfx_rel_path="Edit/Titles/Headline.setting",
        default_font="Montserrat",
        default_style="ExtraBold",
    ),
    KineticTitleDescriptor(
        id="clean_and_simple",
        name="Clean and Simple",
        resolve_template_name="Clean and Simple",
        category="Native",
        description="Tipografía limpia y minimalista sin distracciones.",
        drfx_rel_path="Edit/Titles/Clean and Simple.setting",
        default_font="Montserrat",
        default_style="Medium",
    ),
    KineticTitleDescriptor(
        id="simple_box_lower_third",
        name="Simple Box 1 Line Lower Third",
        resolve_template_name="Simple Box 1 Line Lower Third",
        category="Native",
        description="Tercio inferior con caja sólida para identificadores y créditos.",
        drfx_rel_path="Edit/Titles/Simple Box 1 Line Lower Third.setting",
        default_font="Montserrat",
        default_style="SemiBold",
    ),
)


def get_default_drfx_path() -> Path | None:
    """Localiza el archivo Templates.drfx oficial en el sistema del usuario."""
    if sys.platform == "win32":
        app_data = Path(os.environ.get("APPDATA", "C:/Users/Default/AppData/Roaming"))
        candidate = (
            app_data
            / "Blackmagic Design"
            / "DaVinci Resolve"
            / "Support"
            / "Fusion"
            / "Templates"
            / "Templates.drfx"
        )
        if candidate.is_file():
            return candidate
    elif sys.platform == "darwin":
        candidate = Path(
            "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/Templates.drfx"
        )
        if candidate.is_file():
            return candidate
    return None


def get_snap_captions_drb_folder() -> Path | None:
    """Localiza la carpeta de plantillas DRB de Snap Captions si está instalada."""
    if sys.platform == "win32":
        program_data = Path(os.environ.get("PROGRAMDATA", "C:/ProgramData"))
        candidate = (
            program_data
            / "Blackmagic Design"
            / "DaVinci Resolve"
            / "Support"
            / "Workflow Integration Plugins"
            / "Snap Captions"
            / "Templates"
            / "For Resolve 20"
        )
        if candidate.is_dir():
            return candidate
    return None


class KineticTitleCatalog:
    """Gestiona y resuelve las plantillas de títulos cinéticos disponibles."""

    def __init__(
        self,
        custom_descriptors: Sequence[KineticTitleDescriptor] | None = None,
        drfx_path: Path | None = None,
        drb_folder: Path | None = None,
        auto_discover: bool = True,
    ) -> None:
        descriptors = list(custom_descriptors or BUILTIN_KINETIC_TITLES)
        self._descriptors_by_id: dict[str, KineticTitleDescriptor] = {
            d.id.lower(): d for d in descriptors
        }
        self._descriptors_by_template_name: dict[str, KineticTitleDescriptor] = {
            d.resolve_template_name.lower(): d for d in descriptors
        }
        self.drfx_path = drfx_path or get_default_drfx_path()
        self.drb_folder = drb_folder or get_snap_captions_drb_folder()
        if auto_discover:
            self.discover_resolve_titles()

    def discover_resolve_titles(self) -> int:
        """Descubre e indexa dinámicamente títulos .setting dentro de Templates.drfx y del sistema."""
        candidates: list[Path] = []
        if self.drfx_path and self.drfx_path.is_file():
            candidates.append(self.drfx_path)
        default_path = get_default_drfx_path()
        if default_path and default_path.is_file() and default_path not in candidates:
            candidates.append(default_path)

        added = 0
        for drfx in candidates:
            try:
                with zipfile.ZipFile(drfx, "r") as z:
                    for name in z.namelist():
                        if not name.endswith(".setting") or "/titles/" not in name.lower():
                            continue
                        stem = Path(name).stem
                        key = stem.lower()
                        if key in self._descriptors_by_template_name:
                            continue
                        slug = re.sub(r"[^a-z0-9]+", "_", key).strip("_")
                        if not slug:
                            slug = f"native_title_{len(self._descriptors_by_id)}"
                        desc = KineticTitleDescriptor(
                            id=slug,
                            name=stem,
                            resolve_template_name=stem,
                            category="Native",
                            description=f"Título Fusion nativo de DaVinci Resolve ({stem}).",
                            drfx_rel_path=name,
                            default_font="Montserrat",
                            default_style="Bold",
                        )
                        self._descriptors_by_id[desc.id] = desc
                        self._descriptors_by_template_name[key] = desc
                        added += 1
            except Exception:
                continue
        return added

    def list_all(self) -> tuple[KineticTitleDescriptor, ...]:
        return tuple(self._descriptors_by_id.values())

    def list_by_category(self, category: str) -> tuple[KineticTitleDescriptor, ...]:
        cat_lower = category.strip().lower()
        return tuple(d for d in self._descriptors_by_id.values() if d.category.lower() == cat_lower)

    def get(self, identifier: str) -> KineticTitleDescriptor:
        key = identifier.strip().lower()
        if key in self._descriptors_by_id:
            return self._descriptors_by_id[key]
        if key in self._descriptors_by_template_name:
            return self._descriptors_by_template_name[key]
        raise KineticTitleError(f"No se encontró la plantilla cinética '{identifier}'.")

    def find_drb_path(self, descriptor: KineticTitleDescriptor) -> Path | None:
        if not descriptor.drb_filename or not self.drb_folder:
            return None
        candidate = self.drb_folder / descriptor.drb_filename
        return candidate if candidate.is_file() else None

    def read_setting_from_drfx(self, descriptor: KineticTitleDescriptor) -> str | None:
        """Extrae el contenido .setting crudo desde el archivo Templates.drfx."""
        if not self.drfx_path or not self.drfx_path.is_file() or not descriptor.drfx_rel_path:
            return None
        try:
            with zipfile.ZipFile(self.drfx_path, "r") as z:
                if descriptor.drfx_rel_path in z.namelist():
                    raw = z.read(descriptor.drfx_rel_path)
                    return raw.decode("utf-8", errors="replace")
        except Exception:
            return None
        return None


def frames_to_timecode_string(frame: int | float, fps: float = 24.0) -> str:
    """Convierte un número de fotogramas absoluto en formato 'HH:MM:SS:FF'."""
    fps_int = max(1, round(fps))
    total_frames = max(0, round(frame))
    ff = total_frames % fps_int
    total_seconds = total_frames // fps_int
    ss = total_seconds % 60
    total_minutes = total_seconds // 60
    mm = total_minutes % 60
    hh = total_minutes // 60
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


class KineticTitleWriter:
    """Inserta y personaliza títulos cinéticos nativos en la línea de tiempo de DaVinci Resolve."""

    def __init__(
        self,
        timeline: Any,
        media_pool: Any | None = None,
        catalog: KineticTitleCatalog | None = None,
    ) -> None:
        self.timeline = timeline
        self.media_pool = media_pool
        self.catalog = catalog or KineticTitleCatalog()
        self._cached_template_pool_items: dict[str, Any] = {}

    def insert_kinetic_subtitle(
        self,
        track_index: int,
        record_frame: int | float,
        duration_frames: int | float,
        text: str,
        preset_id: str = "statement",
        fps: float = 24.0,
        custom_name: str | None = None,
        font_name: str | None = None,
        font_style: str | None = None,
        style_overrides: Mapping[str, Any] | None = None,
    ) -> Any:
        """Inserta un título cinético editable en el fotograma y pista indicados."""
        descriptor = self.catalog.get(preset_id)
        target_duration = max(1, round(duration_frames))
        target_record = round(record_frame)

        # Garantizar que existan pistas suficientes hasta track_index
        self._ensure_video_tracks(track_index)

        item: Any = None

        # Estrategia 1: Inserción nativa mediante InsertFusionTitleIntoTimeline con MarkInOut
        item = self._insert_via_playhead_and_marks(
            descriptor=descriptor,
            track_index=track_index,
            record_frame=target_record,
            duration_frames=target_duration,
            fps=fps,
        )

        # Estrategia 2: Inserción mediante MediaPoolItem (DRB importado) y AppendToTimeline
        if item is None and self.media_pool is not None:
            item = self._insert_via_media_pool_append(
                descriptor=descriptor,
                track_index=track_index,
                record_frame=target_record,
                duration_frames=target_duration,
            )

        if item is None:
            raise TimelineWriteError(
                f"No se pudo insertar el título cinético '{descriptor.name}' en la pista V{track_index} "
                f"(fotograma {target_record})."
            )

        # Asignar texto y atributos de estilo en la composición Fusion
        self.update_fusion_text_and_style(
            item=item,
            text=text,
            font_name=font_name or descriptor.default_font,
            font_style=font_style or descriptor.default_style,
            style_overrides=style_overrides,
        )

        if custom_name:
            set_name = getattr(item, "SetName", None)
            if callable(set_name):
                try:
                    set_name(custom_name)
                except Exception:
                    pass

        return item

    def update_fusion_text_and_style(
        self,
        item: Any,
        text: str,
        font_name: str | None = None,
        font_style: str | None = None,
        style_overrides: Mapping[str, Any] | None = None,
    ) -> bool:
        """Actualiza el StyledText y propiedades del nodo TextPlus dentro de Fusion."""
        get_comp = getattr(item, "GetFusionCompByIndex", None)
        if not callable(get_comp):
            return False

        try:
            comp = get_comp(1)
            if comp is None:
                return False

            # Localizar el nodo de texto (Template, Text1 o cualquier TextPlus)
            tool = self._find_textplus_tool(comp)
            if tool is None:
                return False

            set_inp = getattr(tool, "SetInput", None)
            if callable(set_inp):
                # Asignar texto a StyledText; si retorna False (ej. Group/MacroOperator con InstanceInput), probar Input1
                res = set_inp("StyledText", text)
                if res is False:
                    try:
                        set_inp("Input1", text)
                    except Exception:
                        pass
                if font_name:
                    try:
                        set_inp("Font", font_name)
                    except Exception:
                        pass
                if font_style:
                    try:
                        set_inp("Style", font_style)
                    except Exception:
                        pass

                if style_overrides:
                    for input_name, input_val in style_overrides.items():
                        try:
                            set_inp(input_name, input_val)
                        except Exception:
                            pass
            else:
                tool.StyledText = text
                if font_name:
                    tool.Font = font_name
                if font_style:
                    tool.Style = font_style

            return True
        except Exception:
            return False

    def _find_textplus_tool(self, comp: Any) -> Any | None:
        """Localiza de forma robusta el operador TextPlus principal en la composición Fusion."""
        find_tool = getattr(comp, "FindTool", None)
        if callable(find_tool):
            for candidate_name in (
                "Template",
                "Text1",
                "Text2_1",
                "Text2",
                "Text",
                "Title",
                "MacroTool1",
                "TextBox",
                "RibbonText",
            ):
                t = find_tool(candidate_name)
                if t is not None:
                    return t

        get_tool_list = getattr(comp, "GetToolList", None)
        if callable(get_tool_list):
            tools = None
            try:
                # Búsqueda recursiva (True) para explorar dentro de GroupOperators
                tools = get_tool_list(True)
            except TypeError:
                tools = get_tool_list()
            if not tools:
                tools = get_tool_list() or {}
            tool_values = tools.values() if isinstance(tools, dict) else tools
            for t in tool_values:
                get_attrs = getattr(t, "GetAttrs", None)
                if callable(get_attrs):
                    reg_id = get_attrs("TOOLS_RegID") or ""
                    if any(target in reg_id for target in ("TextPlus", "Fuse.TextPlus", "Text3D")):
                        return t
            # Si no encontró por RegID, comprobar si responde al input StyledText
            for t in tool_values:
                get_inp = getattr(t, "GetInput", None)
                if callable(get_inp):
                    try:
                        if get_inp("StyledText") is not None:
                            return t
                    except Exception:
                        pass
            if tool_values:
                return next(iter(tool_values), None)

        return None

    def _ensure_video_tracks(self, target_index: int) -> None:
        get_count = getattr(self.timeline, "GetTrackCount", None)
        add_track = getattr(self.timeline, "AddTrack", None)
        if not callable(get_count) or not callable(add_track):
            return

        current_count = get_count("video") or 0
        while current_count < target_index:
            success = add_track("video")
            if not success:
                break
            new_count = get_count("video")
            if new_count is not None and new_count > current_count:
                current_count = new_count
            else:
                current_count += 1

    def _insert_via_playhead_and_marks(
        self,
        descriptor: KineticTitleDescriptor,
        track_index: int,
        record_frame: int,
        duration_frames: int,
        fps: float,
    ) -> Any | None:
        """Inserta usando la API nativa de Resolve dirigiendo la pista con bloqueo selectivo."""
        insert_fn = getattr(self.timeline, "InsertFusionTitleIntoTimeline", None)
        if not callable(insert_fn):
            return None

        set_tc = getattr(self.timeline, "SetCurrentTimecode", None)
        set_marks = getattr(self.timeline, "SetMarkInOut", None)
        clear_marks = getattr(self.timeline, "ClearMarkInOut", None)
        set_lock = getattr(self.timeline, "SetTrackLock", None)
        get_lock = getattr(self.timeline, "GetIsTrackLocked", None)

        locked_states: dict[int, bool] = {}

        try:
            # 1. Bloquear temporalmente las pistas inferiores (1 .. track_index - 1)
            # para forzar a Resolve a insertar el título en track_index
            if callable(set_lock) and callable(get_lock) and track_index > 1:
                for idx in range(1, track_index):
                    locked_states[idx] = bool(get_lock("video", idx))
                    if not locked_states[idx]:
                        set_lock("video", idx, True)

            # 2. Posicionar cabezal de reproducción
            tc_str = frames_to_timecode_string(record_frame, fps)
            if callable(set_tc):
                set_tc(tc_str)

            # 3. Establecer Mark In y Mark Out para controlar la duración exacta
            if callable(set_marks):
                set_marks(record_frame, record_frame + duration_frames)

            # 4. Inserción mediante API nativa de Resolve
            item = insert_fn(descriptor.resolve_template_name)
            if item is None and descriptor.resolve_template_name == "Text+" and callable(getattr(self.timeline, "InsertTitleIntoTimeline", None)):
                # Fallback para generador Text+ clásico de Resolve
                item = self.timeline.InsertTitleIntoTimeline(descriptor.resolve_template_name)
            return item

        except Exception:
            return None

        finally:
            # Restaurar el estado de bloqueo de pistas y limpiar marcas
            if callable(set_lock):
                for idx, was_locked in locked_states.items():
                    set_lock("video", idx, was_locked)
            if callable(clear_marks):
                clear_marks()

    def _insert_via_media_pool_append(
        self,
        descriptor: KineticTitleDescriptor,
        track_index: int,
        record_frame: int,
        duration_frames: int,
    ) -> Any | None:
        """Inserta mediante AppendToTimeline usando un MediaPoolItem del título Fusion."""
        pool_item = self._get_or_import_template_pool_item(descriptor)
        if pool_item is None:
            return None

        append_fn = getattr(self.media_pool, "AppendToTimeline", None)
        if not callable(append_fn):
            return None

        clip_info = {
            "mediaPoolItem": pool_item,
            "startFrame": 0,
            "endFrame": float(duration_frames),
            "mediaType": 1,
            "trackIndex": track_index,
            "recordFrame": record_frame,
        }

        try:
            result = append_fn([clip_info])
            if result:
                items = list(result.values() if isinstance(result, dict) else result)
                return items[0] if items else None
        except Exception:
            pass

        return None

    def _get_or_import_template_pool_item(self, descriptor: KineticTitleDescriptor) -> Any | None:
        if descriptor.id in self._cached_template_pool_items:
            return self._cached_template_pool_items[descriptor.id]

        if self.media_pool is None:
            return None

        root_folder = getattr(self.media_pool, "GetRootFolder", lambda: None)()
        if root_folder is None:
            return None

        # 1. Buscar si ya existe en el Media Pool
        item = self._find_item_in_folder_tree(root_folder, descriptor.name)
        if item is not None:
            self._cached_template_pool_items[descriptor.id] = item
            return item

        # 2. Si existe un DRB en el sistema, importarlo al Media Pool
        drb_path = self.catalog.find_drb_path(descriptor)
        if drb_path and drb_path.is_file():
            import_folder = getattr(self.media_pool, "ImportFolderFromFile", None)
            if callable(import_folder):
                try:
                    success = import_folder(str(drb_path))
                    if success:
                        item = self._find_item_in_folder_tree(root_folder, descriptor.name)
                        if item is not None:
                            self._cached_template_pool_items[descriptor.id] = item
                            return item
                except Exception:
                    pass

        return None

    def _find_item_in_folder_tree(self, folder: Any, name_pattern: str) -> Any | None:
        get_clips = getattr(folder, "GetClipList", None)
        if callable(get_clips):
            clips = get_clips() or []
            clip_iter = clips.values() if isinstance(clips, dict) else clips
            for clip in clip_iter:
                c_name = getattr(clip, "GetName", lambda: "")()
                if name_pattern.casefold() in c_name.casefold():
                    return clip

        get_subfolders = getattr(folder, "GetSubFolderList", None)
        if callable(get_subfolders):
            subfolders = get_subfolders() or []
            sf_iter = subfolders.values() if isinstance(subfolders, dict) else subfolders
            for sf in sf_iter:
                found = self._find_item_in_folder_tree(sf, name_pattern)
                if found is not None:
                    return found

        return None
