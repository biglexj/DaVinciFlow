"""Inventario y preparación de plantillas instaladas, sin cargar Fusion ni renderizar."""

import hashlib
from pathlib import Path, PurePosixPath
import re
from zipfile import ZipFile, BadZipFile

from davinci_flow.editorial.model import EditorialError, Template, digest


ROOT_TOOL = re.compile(r'Tools\s*=\s*ordered\(\)\s*\{\s*([\w]+)\s*=\s*(MacroOperator|GroupOperator|TextPlus)\s*\{')
EXPOSED_TEXT = re.compile(r'(\w+)\s*=\s*InstanceInput\s*\{[^{}]*Source\s*=\s*"StyledText"[^{}]*\}', re.S)


def descriptor(name: str, source: str, locator: str, content: bytes) -> Template:
    text = content.decode("utf-8-sig")
    root = ROOT_TOOL.search(text)
    controls = EXPOSED_TEXT.findall(text)
    node, input_id = "", "StyledText"
    if root and root[2] in ("MacroOperator", "GroupOperator") and len(controls) == 1:
        node, input_id = root[1], controls[0]
    return Template("tpl_" + digest(locator)[:20], name, source, locator, node,
                    hashlib.sha256(content).hexdigest(), input_id)


def scan_archive(path: Path) -> tuple[Template, ...]:
    result = []
    try:
        with ZipFile(path) as archive:
            for info in archive.infolist():
                entry = info.filename.replace("\\", "/")
                if "/titles/" not in "/" + entry.lower() or not entry.lower().endswith((".setting", ".comp")):
                    continue
                if info.file_size > 4 * 1024 * 1024:
                    continue
                result.append(descriptor(PurePosixPath(entry).stem, "installed_archive",
                                         str(path.resolve()) + "::" + info.filename, archive.read(info)))
    except (BadZipFile, UnicodeError) as error:
        raise EditorialError(f"No se pudo leer el paquete de títulos {path.name}.") from error
    return tuple(result)


def template_bytes(template: Template) -> bytes:
    try:
        if template.source == "installed_archive":
            path, member = template.locator.split("::", 1)
            with ZipFile(path) as archive:
                return archive.read(member)
        return Path(template.locator).read_bytes()
    except (OSError, BadZipFile, KeyError, ValueError) as error:
        raise EditorialError(f"La plantilla {template.name} no está disponible.") from error


def prepare_comp(template: Template, directory: Path) -> Path:
    """Añade salida de imagen a macros de títulos; nunca cambia su árbol interno."""
    content = template_bytes(template)
    if hashlib.sha256(content).hexdigest() != template.fingerprint:
        raise EditorialError("La plantilla cambió después del análisis.")
    directory.mkdir(parents=True, exist_ok=True)
    if template.source == "installed_archive":
        archive_path, member = template.locator.split("::", 1)
        resources = (directory / template.id).resolve()
        with ZipFile(archive_path) as archive:
            # Preservar la jerarquía para referencias Setting: del paquete.
            if sum(i.file_size for i in archive.infolist()) > 512 * 1024 * 1024:
                raise EditorialError("Paquete demasiado grande; prepara el título en el Media Pool.")
            for info in archive.infolist():
                relative = PurePosixPath(info.filename.replace("\\", "/"))
                if relative.is_absolute() or any(part == ".." or ":" in part for part in relative.parts):
                    raise EditorialError("El paquete contiene una ruta no permitida.")
                destination = resources.joinpath(*relative.parts).resolve()
                if not destination.is_relative_to(resources):
                    raise EditorialError("El paquete contiene una ruta fuera de su carpeta.")
                if info.is_dir():
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(info))
        source_directory = resources.joinpath(*PurePosixPath(member.replace("\\", "/")).parts).parent
    else:
        source_directory = Path(template.locator).parent
    text = content.decode("utf-8-sig")
    # Un mapa relativo del paquete deja de apuntar al directorio temporal de la composición.
    text = text.replace("Setting:", source_directory.as_posix().rstrip("/") + "/")
    if not re.search(r'=\s*MediaOut\s*\{', text):
        root = ROOT_TOOL.search(text)
        if not root:
            raise EditorialError("No se puede identificar la salida del título; usa una composición exportada con MediaOut.")
        output = "Output"
        if root[2] in ("MacroOperator", "GroupOperator"):
            match = re.search(r'Outputs\s*=\s*(?:ordered\(\)\s*)?\{\s*(\w+)\s*=\s*InstanceOutput', text)
            if not match:
                raise EditorialError("La macro no expone una salida de imagen.")
            output = match[1]
        insertion = (f'\n DF_EditorialOutput = MediaOut {{ Inputs = {{ Input = Input {{ '
                     f'SourceOp = "{root[1]}", Source = "{output}" }} }} }},\n')
        location = text.index("{", root.start()) + 1
        text = text[:location] + insertion + text[location:]
    target = directory / (template.id + ".comp")
    target.write_text(text, encoding="utf-8")
    return target
