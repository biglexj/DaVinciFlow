"""Gestión segura de credenciales para la API de Gemini."""

import json
import os
from pathlib import Path

from davinci_flow.errors import GeminiCredentialsError

CONFIG_DIR = Path.home() / ".davinci_flow"
CONFIG_FILE = CONFIG_DIR / "config.json"


def mask_api_key(key: str | None) -> str:
    """Enmascara una clave API para visualización segura en interfaces o registros."""
    if not key or not key.strip():
        return ""
    stripped = key.strip()
    if len(stripped) <= 8:
        return "********"
    return f"{stripped[:4]}...{stripped[-4:]}"


def get_config_path() -> Path:
    """Retorna la ruta del archivo de configuración del usuario."""
    return CONFIG_FILE


def load_user_config() -> dict[str, str]:
    """Carga el diccionario de configuración del usuario si existe."""
    if not CONFIG_FILE.is_file():
        return {}
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except Exception:
        return {}
    return {}


def save_gemini_api_key(key: str) -> Path:
    """Guarda la clave API en el archivo de configuración local del usuario con permisos seguros."""
    clean_key = key.strip()
    if not clean_key:
        raise GeminiCredentialsError("La clave API no puede estar vacía.")

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config = load_user_config()
    config["gemini_api_key"] = clean_key

    CONFIG_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    # En sistemas tipo Unix, restringir permisos de lectura/escritura únicamente al usuario
    if os.name != "nt":
        try:
            CONFIG_FILE.chmod(0o600)
        except OSError:
            pass

    return CONFIG_FILE


def get_gemini_api_key(explicit_key: str | None = None) -> str:
    """Obtiene la clave de Gemini buscando en orden: argumento explícito, entorno, configuración local."""
    if explicit_key and explicit_key.strip():
        return explicit_key.strip()

    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key

    config = load_user_config()
    saved_key = config.get("gemini_api_key", "").strip()
    if saved_key:
        return saved_key

    raise GeminiCredentialsError(
        "No se encontró una clave API de Google Gemini. "
        "Configura la variable de entorno GEMINI_API_KEY o ingresa tu clave en la interfaz gráfica."
    )


def has_gemini_api_key() -> bool:
    """Comprueba de forma segura si existe una clave de Gemini disponible sin lanzar excepciones."""
    try:
        get_gemini_api_key()
        return True
    except GeminiCredentialsError:
        return False
