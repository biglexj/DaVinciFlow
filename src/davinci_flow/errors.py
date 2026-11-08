"""Errores controlados de DaVinci Flow."""


class DaVinciFlowError(RuntimeError):
    """Error esperado que puede mostrarse al usuario sin un rastro técnico."""


class ResolveConnectionError(DaVinciFlowError):
    """No fue posible obtener una sesión activa de DaVinci Resolve."""


class SubtitleTrackError(DaVinciFlowError):
    """La pista de subtítulos solicitada no existe o no puede leerse."""


class NormalizationError(DaVinciFlowError):
    """El texto del subtítulo no pudo normalizarse adecuadamente."""


class ClassificationError(DaVinciFlowError):
    """Ocurrió un error al clasificar los roles de un bloque de subtítulo."""


class PlanSerializationError(DaVinciFlowError):
    """Error al serializar o deserializar el plan de generación."""


class PlanVersionMismatchError(PlanSerializationError):
    """La versión del plan no es compatible con la versión del software."""


class GeminiError(DaVinciFlowError):
    """Error general en la integración con la API de Google Gemini."""


class GeminiCredentialsError(GeminiError):
    """La clave API de Gemini no está configurada o es inválida."""


class ScriptAlignmentError(GeminiError):
    """Error al procesar o alinear los subtítulos con el guion original."""


class ProviderError(DaVinciFlowError):
    """Error general de un proveedor de IA externo."""


class MinimaxError(ProviderError):
    """Error general en la integración con la API de Minimax."""


class MinimaxCredentialsError(MinimaxError):
    """La clave API de Minimax no está configurada o fue rechazada."""


class VoiceSynthesisError(DaVinciFlowError):
    """La locución no pudo sintetizarse o materializarse en disco."""


class AutocorrectError(DaVinciFlowError):
    """El autocorrector no pudo completar el lote de subtítulos."""


class FusionEffectError(DaVinciFlowError):
    """No se pudo generar, importar o insertar el efecto Fusion."""


class MCPServerError(DaVinciFlowError):
    """El servidor MCP de DaVinci Flow no pudo atender la solicitud."""


class MarkerError(DaVinciFlowError):
    """Error al insertar o gestionar marcadores en la línea de tiempo."""


class TimelineWriteError(DaVinciFlowError):
    """Resolve no confirmó una escritura solicitada sobre la línea de tiempo."""

