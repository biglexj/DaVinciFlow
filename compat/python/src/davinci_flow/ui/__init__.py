"""Módulo de interfaz de usuario integrada para DaVinci Resolve."""

def open_davinci_flow_ui(resolve_app=None, fusion_app=None, bmd_module=None):
    from davinci_flow.ui.desktop_launcher import launch_desktop
    return launch_desktop()

__all__ = [
    "open_davinci_flow_ui",
]
