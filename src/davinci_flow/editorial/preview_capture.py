"""Miniaturas reales, desde el medio original o una captura aislada en Resolve."""

from dataclasses import asdict
from pathlib import Path
import shutil
import subprocess
import time
import uuid

from davinci_flow.editorial.model import EditorialError, Template
from davinci_flow.editorial.title_preview import captured_preview_path, read_title_preview

PRODUCTION_PROJECT = 'DF_Validacion_TextPlus_20261109'


def ensure_title_thumbnail(template: Template) -> Path:
    preview = read_title_preview(template)
    if preview.image:
        return preview.image
    target = captured_preview_path(template)
    target.parent.mkdir(parents=True, exist_ok=True)
    if preview.video:
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            raise EditorialError('FFmpeg no está disponible para obtener la miniatura del vídeo.')
        temporary = target.with_name(target.stem + '-' + uuid.uuid4().hex + '.png')
        try:
            for position in ('1', '0'):
                completed = subprocess.run([ffmpeg, '-nostdin', '-loglevel', 'error', '-ss', position,
                                           '-i', str(preview.video), '-frames:v', '1', '-vf', 'scale=640:-2',
                                           '-y', str(temporary)], capture_output=True, timeout=20,
                                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                if completed.returncode == 0 and temporary.is_file() and temporary.stat().st_size:
                    temporary.replace(target)
                    return target
            raise EditorialError('El vídeo no devolvió un fotograma para la miniatura.')
        finally:
            temporary.unlink(missing_ok=True)
    if template.source in {'media_pool', 'installed_bin', 'installed_archive'}:
        raise EditorialError('Esta base necesita una muestra preparada en el proyecto de producción.')
    from davinci_flow.editorial.resolve_bridge import request
    request('capture_title_preview', template=asdict(template), target=str(target))
    if not target.is_file():
        raise EditorialError('Resolve no confirmó la captura de la plantilla.')
    return target


def capture_in_resolve(session, template: Template, target: Path) -> dict:
    """Solo crea y retira una secuencia temporal propia en el proyecto de producción."""
    from davinci_flow.editorial.template_files import prepare_comp
    p, resolve = session.project, session.resolve
    pm = resolve.GetProjectManager()
    if (p.GetName() != PRODUCTION_PROJECT or pm.GetCurrentDatabase().get('DbName') != 'Contenidos'
            or pm.GetCurrentFolder() != 'Titulos'):
        raise EditorialError('Abre el proyecto de producción de DaVinci Flow en Contenidos / Biglex J Producciones / Titulos para capturar este título.')
    if target.resolve() != captured_preview_path(template).resolve():
        raise EditorialError('La captura debe guardarse en la caché de su plantilla.')
    pool = p.GetMediaPool()
    if template.source in {'media_pool', 'installed_bin', 'installed_archive'}:
        raise EditorialError('Esta base necesita una secuencia de muestra preparada; no se insertará automáticamente por API para capturarla.')
    previous = p.GetCurrentTimeline()
    previous_tc = previous.GetCurrentTimecode() if previous else None
    previous_folder = pool.GetCurrentFolder()
    timeline = None
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        timeline = pool.CreateEmptyTimeline('DF_Captura_' + uuid.uuid4().hex[:12])
        if timeline is None or p.SetCurrentTimeline(timeline) is not True:
            raise EditorialError('Resolve no pudo preparar la secuencia de captura.')
        timeline.SetStartTimecode('00:00:00:00')
        timeline.SetSetting('useCustomSettings', '1')
        timeline.SetSetting('timelineResolutionWidth', '1920')
        timeline.SetSetting('timelineResolutionHeight', '1080')
        timeline.SetCurrentTimecode('00:00:00:00')
        timeline.SetMarkInOut(0, 95)
        item = timeline.InsertFusionTitleIntoTimeline(template.name if template.source == 'native' else 'Text+')
        if item and template.source != 'native':
            comp = item.ImportFusionComp(str(prepare_comp(template, target.parent / 'comps')))
            if not comp:
                raise EditorialError('Resolve no pudo cargar el diseño para la captura.')
            name = comp.GetAttrs().get('COMPS_Name')
            if name:
                item.LoadFusionCompByName(name)
        if not item:
            raise EditorialError('Resolve no devolvió el título para la captura.')
        timeline.SetCurrentTimecode('00:00:01:00')
        time.sleep(.15)
        if p.ExportCurrentFrameAsStill(str(target)) is not True:
            raise EditorialError('Resolve no pudo exportar la captura.')
        return {'path': str(target)}
    finally:
        if previous:
            p.SetCurrentTimeline(previous)
            if previous_tc:
                previous.SetCurrentTimecode(previous_tc)
        if timeline is not None:
            pool.DeleteTimelines([timeline])
        if previous_folder:
            pool.SetCurrentFolder(previous_folder)
