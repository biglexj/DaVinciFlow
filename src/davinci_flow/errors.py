"""Errores controlados de DaVinci Flow."""


class DaVinciFlowError(RuntimeError):
    """Error esperado que puede mostrarse al usuario sin un rastro técnico."""


class ResolveConnectionError(DaVinciFlowError):
    """No fue posible obtener una sesión activa de DaVinci Resolve."""


class SubtitleTrackError(DaVinciFlowError):
    """La pista de subtítulos solicitada no existe o no puede leerse."""
