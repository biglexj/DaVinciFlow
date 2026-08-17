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


class MarkerError(DaVinciFlowError):
    """Error al insertar o gestionar marcadores en la línea de tiempo."""


