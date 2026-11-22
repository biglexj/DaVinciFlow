"""Módulo de interfaz de usuario integrada para DaVinci Resolve."""

def open_davinci_flow_ui(resolve_app=None, fusion_app=None, bmd_module=None, prefer_flet: bool = False):
    from davinci_flow.ui.desktop_launcher import launch_desktop
    return launch_desktop(prefer_flet=True) if prefer_flet else launch_desktop()

__all__ = [
    "open_davinci_flow_ui",
]
