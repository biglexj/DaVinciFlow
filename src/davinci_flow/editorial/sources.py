"""Lectura explícita de fuentes: ninguna conexión al importar o abrir el editor."""

import os
from pathlib import Path
from typing import Any

from davinci_flow.editorial.model import EditorialError, Snapshot, Template
from davinci_flow.editorial.template_files import descriptor, scan_archive
from davinci_flow.resolve.subtitle_reader import ResolveSubtitleReader
from davinci_flow.resolve.template_scanner import scan_davinciflow_presets
from davinci_flow.subtitles.srt_parser import load_srt_file


def default_title_roots() -> tuple[Path, ...]:
    return (
        Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) /
        "Blackmagic Design/DaVinci Resolve/Fusion/Templates",
        Path(os.environ.get("APPDATA", str(Path.home() / "AppData/Roaming"))) /
        "Blackmagic Design/DaVinci Resolve/Support/Fusion/Templates",
    )


def basic_titles() -> tuple[Template, ...]:
    """Text+ nativo, con posiciones iniciales independientes y sin animación añadida."""
    root = Path(__file__).with_name("basic_titles")
    return tuple(descriptor(path.stem, "installed_file", str(path.resolve()), path.read_bytes())
                 for path in sorted(root.glob("*.setting")))


def scan_installed(roots: tuple[Path, ...] | None = None, diagnostics: list[str] | None = None) -> tuple[Template, ...]:
    """Inventario de archivos, no declaración de compatibilidad de reproducción."""
    result = list(basic_titles()) if roots is None else []
    seen = set()
    for root in roots if roots is not None else default_title_roots():
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.name.startswith("."):
                continue
            if path.suffix.lower() == ".drfx" and path.is_file():
                try:
                    result.extend(scan_archive(path))
                except (EditorialError, OSError) as error:
                    if diagnostics is not None:
                        diagnostics.append(str(error))
                continue
            if path.suffix.lower() not in (".setting", ".comp") or not path.is_file():
                continue
            locator = str(path.resolve())
            if locator in seen:
                continue
            seen.add(locator)
            if roots is None and "/titles/" not in path.as_posix().lower():
                continue
            result.append(descriptor(path.stem, "installed_file", locator, path.read_bytes()))
    return tuple(result)


def media_pool_catalog(media_pool: Any) -> tuple[tuple[Template, ...], dict[str, Any]]:
    templates, handles = [], {}
    for preset in scan_davinciflow_presets(media_pool):
        identifier = str(preset.media_item.GetUniqueId() or "")
        if not identifier:
            raise EditorialError(f"La plantilla {preset.name} no tiene ID estable.")
        template = Template("pool_" + identifier, preset.name, "media_pool", identifier)
        templates.append(template)
        handles[template.id] = preset.media_item
    if len(handles) != len(templates):
        raise EditorialError("Hay referencias duplicadas a una misma plantilla del Media Pool.")
    return tuple(templates), handles


def capture(session: Any, track: int = 1, first: int = 1, last: int = 120) -> Snapshot:
    """Captura inmutable; recibe una sesión, nunca la inicia por cuenta propia."""
    timeline = session.timeline
    if first < 1 or last < first:
        raise EditorialError("Rango de subtítulos inválido.")
    cues = ResolveSubtitleReader(timeline).read_track(track)[first - 1:last]
    identifier = timeline.GetUniqueId()
    if not identifier:
        raise EditorialError("Resolve no confirmó la identidad de la secuencia.")
    cuts = []
    for track_type in ("video", "audio"):
        for index in range(1, int(timeline.GetTrackCount(track_type)) + 1):
            name = str(timeline.GetTrackName(track_type, index) or "")
            if name in {"DF_CONTEXT", "DF_MAIN", "DF_ACCENT", "DF_BROLL", "DF_VISUAL_FX",
                        "DF_SFX", "DF_SFX_TRANSITIONS", "DF_SFX_ACCENTS"}:
                continue
            items = timeline.GetItemListInTrack(track_type, index) or []
            if isinstance(items, dict):
                items = items.values()
            for item in items:
                # Huella del montaje, incluyendo sustituciones y desplazamiento de origen.
                cuts.append((track_type, index, str(item.GetUniqueId()),
                             float(item.GetStart()), float(item.GetEnd()),
                             float(item.GetLeftOffset()), float(item.GetRightOffset())))
    return Snapshot(str(session.project.GetName()), str(timeline.GetName()), str(identifier),
                    float(timeline.GetSetting("timelineFrameRate")),
                    int(timeline.GetSetting("timelineResolutionWidth")),
                    int(timeline.GetSetting("timelineResolutionHeight")),
                    int(timeline.GetStartFrame()), track, tuple(cues), tuple(sorted(cuts)),
                    first=first, last=last, project_id=str(session.project.GetUniqueId()))


def from_srt(path: str | Path, fps: float, width: int = 1920, height: int = 1080) -> Snapshot:
    return Snapshot("SRT offline", Path(path).name, None, fps, width, height, 0, 1,
                    load_srt_file(path, fps=fps), source="srt")
