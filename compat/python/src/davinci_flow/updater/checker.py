"""Cliente de comprobación y sanitización de actualizaciones desde GitHub Releases."""

from dataclasses import dataclass
import json
import re
import urllib.error
import urllib.request
from typing import Optional

from davinci_flow import __version__

GITHUB_API_LATEST = "https://api.github.com/repos/{owner}/{repo}/releases/latest"
DEFAULT_OWNER = "biglexj"
DEFAULT_REPO = "DaVinciFlow"


@dataclass
class UpdateRelease:
    """Modelo inmutable de datos para una versión publicada en GitHub Releases."""
    version: str
    download_url: str
    release_page_url: str
    body: str
    published_at: str
    is_newer: bool
    sanitized_notes: str


def is_newer_version(current: str, remote: str) -> bool:
    """Compara semánticamente dos versiones con números naturales."""
    def parse_components(ver_str: str) -> list[int]:
        clean = ver_str.strip().lstrip("vV")
        parts: list[int] = []
        for segment in clean.split("."):
            digits = "".join(ch for ch in segment if ch.isdigit())
            if digits:
                parts.append(int(digits))
        return parts

    current_parts = parse_components(current)
    remote_parts = parse_components(remote)
    max_len = max(len(current_parts), len(remote_parts))

    for i in range(max_len):
        c = current_parts[i] if i < len(current_parts) else 0
        r = remote_parts[i] if i < len(remote_parts) else 0
        if r > c:
            return True
        if c > r:
            return False
    return False


def sanitize_release_notes(raw_body: str) -> str:
    """Sanitiza limpiamente notas de versión en Markdown eliminando marcadores crudos."""
    if not raw_body or not raw_body.strip():
        return "Actualización con mejoras de rendimiento y estabilidad general."

    lines: list[str] = []
    for line in raw_body.strip().splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue

        # Encabezados Markdown (# Título)
        if cleaned.startswith("#"):
            header_text = cleaned.lstrip("#").strip()
            lines.append(f"\n{header_text}:" if not header_text.endswith(":") else f"\n{header_text}")
            continue

        # Viñetas de lista (- o *)
        if cleaned.startswith(("- ", "* ")):
            cleaned = "• " + cleaned[2:].strip()

        # Eliminar formato negrita y cursiva
        cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
        cleaned = re.sub(r"\*(.*?)\*", r"\1", cleaned)
        cleaned = re.sub(r"__(.*?)__", r"\1", cleaned)
        cleaned = re.sub(r"`(.*?)`", r"\1", cleaned)

        # Simplificar enlaces Markdown [Texto](url) -> Texto
        cleaned = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", cleaned)

        # Eliminar etiquetas HTML crudas
        cleaned = re.sub(r"<[^>]+>", "", cleaned).strip()

        # Ocultar posibles rutas de desarrollo locales
        cleaned = re.sub(r"[A-Za-z]:\\[^ \n\r\t]+", "[ruta]", cleaned)

        if cleaned:
            lines.append(cleaned)

    result = "\n".join(lines).strip()
    return result if result else "Actualización con mejoras de rendimiento y estabilidad general."


def parse_update_release(
    data: dict | str,
    current_version: str = __version__
) -> Optional[UpdateRelease]:
    """Parsea una respuesta JSON de GitHub Releases y extrae la versión y assets relevantes."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return None

    if not isinstance(data, dict):
        return None

    tag_name = str(data.get("tag_name", "")).strip()
    html_url = str(data.get("html_url", "")).strip()
    body = str(data.get("body", "")).strip()
    published_at = str(data.get("published_at", "")).strip()

    if not tag_name:
        return None

    clean_version = tag_name.lstrip("vV").strip()
    assets = data.get("assets", [])

    # Priorizar instalador ejecutable o paquete si existe en los assets
    download_url = html_url
    if isinstance(assets, list) and assets:
        for asset in assets:
            if isinstance(asset, dict):
                name = str(asset.get("name", "")).lower()
                browser_url = str(asset.get("browser_download_url", ""))
                if (
                    name.endswith((".exe", ".zip", ".whl", ".tar.gz"))
                    and not name.endswith("sha256sums.txt")
                    and browser_url
                ):
                    download_url = browser_url
                    break
        if download_url == html_url and assets:
            first_asset = assets[0]
            if isinstance(first_asset, dict) and first_asset.get("browser_download_url"):
                download_url = str(first_asset["browser_download_url"])

    is_newer = is_newer_version(current_version, clean_version)
    sanitized = sanitize_release_notes(body)

    return UpdateRelease(
        version=clean_version,
        download_url=download_url,
        release_page_url=html_url,
        body=body,
        published_at=published_at,
        is_newer=is_newer,
        sanitized_notes=sanitized,
    )


def check_github_release(
    owner: str = DEFAULT_OWNER,
    repo: str = DEFAULT_REPO,
    timeout: float = 6.0,
    current_version: str = __version__
) -> Optional[UpdateRelease]:
    """Consulta la API pública de GitHub para obtener la última release publicada."""
    endpoint = GITHUB_API_LATEST.format(owner=owner, repo=repo)
    request = urllib.request.Request(
        endpoint,
        headers={
            "User-Agent": f"DaVinciFlow/{current_version}",
            "Accept": "application/vnd.github.v3+json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status == 200:
                raw_data = json.loads(response.read().decode("utf-8"))
                return parse_update_release(raw_data, current_version=current_version)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        # Fallo silencioso y controlado ante ausencia de red o releases no publicadas (404)
        return None

    return None
