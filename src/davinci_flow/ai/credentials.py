"""Gestión segura de credenciales para las APIs de IA (Gemini y Minimax)."""

import json
import os
from dataclasses import dataclass
from pathlib import Path

from davinci_flow.errors import DaVinciFlowError, GeminiCredentialsError, MinimaxCredentialsError

CONFIG_DIR = Path.home() / ".davinci_flow"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass(frozen=True)
class CredentialProfile:
    """Describe dónde vive la clave de un proveedor y con qué error falla cuando falta."""

    provider: str
    config_key: str
    env_var: str
    label: str
    error: type[DaVinciFlowError]
    missing_message: str


CREDENTIAL_PROFILES: dict[str, CredentialProfile] = {
    "gemini": CredentialProfile(
        provider="gemini",
        config_key="gemini_api_key",
        env_var="GEMINI_API_KEY",
        label="Clave API de Gemini",
        error=GeminiCredentialsError,
        missing_message=(
            "No se encontró una clave API de Google Gemini. "
            "Configura la variable de entorno GEMINI_API_KEY o ingresa tu clave en la interfaz gráfica."
        ),
    ),
    "minimax": CredentialProfile(
        provider="minimax",
        config_key="minimax_api_key",
        env_var="MINIMAX_API_KEY",
        label="Clave API de Minimax",
        error=MinimaxCredentialsError,
        missing_message=(
            "No se encontró una clave API de Minimax. "
            "Configura la variable de entorno MINIMAX_API_KEY o ingresa tu clave en la interfaz gráfica."
        ),
    ),
}


def credential_profile(provider: str) -> CredentialProfile:
    """Devuelve el perfil de credenciales de un proveedor."""
    try:
        return CREDENTIAL_PROFILES[provider]
    except KeyError as err:
        raise KeyError(
            f"Proveedor sin perfil de credenciales: '{provider}'. "
            f"Disponibles: {', '.join(sorted(CREDENTIAL_PROFILES))}."
        ) from err


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


def save_provider_api_key(provider: str, key: str) -> Path:
    """Guarda la clave de un proveedor en el archivo de configuración local con permisos seguros."""
    profile = credential_profile(provider)
    clean_key = key.strip()
    if not clean_key:
        raise profile.error("La clave API no puede estar vacía.")

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config = load_user_config()
    config[profile.config_key] = clean_key

    CONFIG_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    # En sistemas tipo Unix, restringir permisos de lectura/escritura únicamente al usuario
    if os.name != "nt":
        try:
            CONFIG_FILE.chmod(0o600)
        except OSError:
            pass

    return CONFIG_FILE


def get_provider_api_key(provider: str, explicit_key: str | None = None) -> str:
    """Obtiene la clave de un proveedor buscando en orden: argumento, entorno, configuración local."""
    profile = credential_profile(provider)

    if explicit_key and explicit_key.strip():
        return explicit_key.strip()

    env_key = os.environ.get(profile.env_var, "").strip()
    if env_key:
        return env_key

    config = load_user_config()
    saved_key = config.get(profile.config_key, "").strip()
    if saved_key:
        return saved_key

    raise profile.error(profile.missing_message)


def has_provider_api_key(provider: str) -> bool:
    """Comprueba de forma segura si existe una clave disponible sin lanzar excepciones."""
    try:
        get_provider_api_key(provider)
        return True
    except DaVinciFlowError:
        return False


def save_gemini_api_key(key: str) -> Path:
    """Guarda la clave API de Gemini en el archivo de configuración local del usuario."""
    return save_provider_api_key("gemini", key)


def get_gemini_api_key(explicit_key: str | None = None) -> str:
    """Obtiene la clave de Gemini buscando en orden: argumento explícito, entorno, configuración local."""
    return get_provider_api_key("gemini", explicit_key)


def has_gemini_api_key() -> bool:
    """Comprueba de forma segura si existe una clave de Gemini disponible sin lanzar excepciones."""
    return has_provider_api_key("gemini")


def save_minimax_api_key(key: str) -> Path:
    """Guarda la clave API de Minimax en el archivo de configuración local del usuario."""
    return save_provider_api_key("minimax", key)


def get_minimax_api_key(explicit_key: str | None = None) -> str:
    """Obtiene la clave de Minimax buscando en orden: argumento explícito, entorno, configuración local."""
    return get_provider_api_key("minimax", explicit_key)


def has_minimax_api_key() -> bool:
    """Comprueba de forma segura si existe una clave de Minimax disponible sin lanzar excepciones."""
    return has_provider_api_key("minimax")
