"""HTTP verificado para Aurora, sin redirecciones ni exposición de credenciales."""

import json
import urllib.error
import urllib.request

from davinci_flow.editorial.model import EditorialError

MESSAGES = {
    'authentication-required': 'Inicia sesión en Aurora.',
    'session-expired': 'Tu sesión ha caducado. Inicia sesión de nuevo.',
    'account-disabled': 'Tu cuenta no tiene acceso activo.',
    'subscription-required': 'Tu suscripción no tiene acceso vigente a la generación de voz.',
    'insufficient-credits': 'No tienes créditos suficientes para este guion.',
    'voice-unavailable': 'La voz elegida ya no está disponible. Actualiza el catálogo.',
    'generation-failed': 'La generación terminó con error y no se repetirá automáticamente.',
    'synthesis-failed': 'Aurora no pudo generar la voz. No se consumieron créditos.',
    'not-found': 'No se encontró esta generación en Aurora.',
    'invalid-audio': 'El servicio no devolvió el audio del proveedor y la voz elegidos.',
    'provider-unavailable': 'El motor elegido no está disponible. Actualiza el catálogo de voces.',
    'rate-unavailable': 'La tarifa de voz no está disponible.',
    'rate-changed': 'La tarifa cambió. Actualiza el acceso antes de generar; no se consumieron créditos.',
}


class AuroraError(EditorialError):
    def __init__(self, status, code, message=None):
        self.status, self.code = status, code
        super().__init__(message or MESSAGES.get(code, 'Aurora no pudo completar la operación.'))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(method, url, payload=None, headers=None, timeout=30):
    body = json.dumps(payload).encode() if payload is not None else None
    request_headers = {'Accept': 'application/json, audio/wav', **(headers or {})}
    if body is not None:
        request_headers['Content-Type'] = 'application/json'
    message = urllib.request.Request(url, data=body, method=method, headers=request_headers)
    try:
        with urllib.request.build_opener(NoRedirect()).open(message, timeout=timeout) as response:
            content = response.read(64 * 1024 * 1024 + 1)
            if len(content) > 64 * 1024 * 1024:
                raise AuroraError(502, 'invalid-audio')
            return response.status, {k.lower(): v for k, v in response.headers.items()}, content
    except urllib.error.HTTPError as error:
        try:
            value = json.loads(error.read(65536))
            code = value.get('error', '') if isinstance(value, dict) else ''
        except (ValueError, OSError):
            code = ''
        if error.code in (401, 403) and code not in MESSAGES:
            code = 'session-expired' if error.code == 401 else 'subscription-required'
        if error.code == 404 and 'action=config' in url:
            raise AuroraError(404, 'integration-unavailable', 'El inicio de sesión de DaVinci Flow aún no está disponible en este servidor de Aurora.') from None
        raise AuroraError(error.code, code) from None
    except (urllib.error.URLError, OSError, TimeoutError):
        raise AuroraError(0, 'network-unavailable', 'No se recibió una respuesta de Aurora. Si estabas generando, recupera la solicitud antes de volver a generar.') from None


def json_request(*args, **kwargs):
    _, _, content = request(*args, **kwargs)
    try:
        value = json.loads(content)
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (ValueError, TypeError):
        raise AuroraError(502, 'invalid-response') from None
