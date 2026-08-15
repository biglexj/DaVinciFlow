"""Interfaz gráfica nativa para DaVinci Resolve mediante UIManager."""

import sys
from typing import Any

from davinci_flow.application import (
    generate_from_active_timeline,
    plan_active_subtitles,
    scan_active_subtitles,
)
from davinci_flow.errors import DaVinciFlowError
from davinci_flow.generation.plan import GenerationPlan
from davinci_flow.generation.record import GenerationExecutionRecord


def create_uimanager_window(resolve_app: Any = None) -> Any:
    """Crea y despliega la ventana interna de DaVinci Flow en DaVinci Resolve."""
    # Intentar obtener el objeto fusion y ui
    fusion = None
    if resolve_app is not None and hasattr(resolve_app, "Fusion"):
        fusion = resolve_app.Fusion()
    elif "fu" in globals():
        fusion = globals()["fu"]
    elif "fusion" in globals():
        fusion = globals()["fusion"]
    else:
        try:
            import fusionscript  # type: ignore[import-not-found]
            fusion = fusionscript.scriptapp("Fusion")
        except Exception:
            pass

    if fusion is None or not hasattr(fusion, "UIManager"):
        print(
            "DaVinci Flow UI: UIManager no está disponible en este entorno.\n"
            "Ejecuta el script desde DaVinci Resolve (Espacio de trabajo -> Scripts -> DaVinci Flow) "
            "o utiliza la interfaz CLI con 'python -m davinci_flow --plan'.",
            file=sys.stderr,
        )
        return None

    ui = fusion.UIManager
    dispatcher = getattr(fusion, "UIDispatcher", None)
    if dispatcher is None:
        try:
            import bmd  # type: ignore[import-not-found]
            dispatcher = bmd.UIDispatcher(ui)
        except Exception:
            dispatcher = ui

    # Construcción de la interfaz
    win = dispatcher.AddWindow(
        {
            "WindowTitle": "DaVinci Flow — Subtítulos Dinámicos & SFX",
            "ID": "DaVinciFlowWin",
            "Geometry": [200, 200, 680, 560],
        },
        [
            ui.VGroup(
                [
                    # Encabezado
                    ui.Label(
                        {
                            "Text": "<b>DaVinci Flow</b> — Automatización de Subtítulos y SFX",
                            "Alignment": {"AlignHCenter": True},
                            "Font": ui.Font({"PixelSize": 16}),
                        }
                    ),
                    ui.Label(
                        {
                            "Text": "Autor: biglexj | Licencia: MIT",
                            "Alignment": {"AlignHCenter": True},
                        }
                    ),
                    # Selector de Pista y Configuración
                    ui.HGroup(
                        [
                            ui.Label({"Text": "Pista Subtítulos:", "Weight": 0.3}),
                            ui.SpinBox({"ID": "TrackSpin", "Value": 1, "Minimum": 1, "Maximum": 16, "Weight": 0.2}),
                            ui.Label({"Text": "Tema:", "Weight": 0.2}),
                            ui.ComboBox({"ID": "ThemeCombo", "Weight": 0.3}),
                            ui.Label({"Text": "Perfil:", "Weight": 0.2}),
                            ui.ComboBox({"ID": "ProfileCombo", "Weight": 0.3}),
                        ]
                    ),
                    # Checkbox SFX
                    ui.HGroup(
                        [
                            ui.CheckBox({"ID": "SFXCheck", "Text": "Generar efectos sonoros (SFX)", "Checked": True}),
                            ui.CheckBox({"ID": "DryRunCheck", "Text": "Modo Simulación (Dry-Run)", "Checked": False}),
                        ]
                    ),
                    # Botones de Análisis
                    ui.HGroup(
                        [
                            ui.Button({"ID": "AnalyzeBtn", "Text": "🔍 Analizar Capas"}),
                            ui.Button({"ID": "GenerateBtn", "Text": "⚡ Generar en Línea de Tiempo"}),
                        ]
                    ),
                    # Lista de Bloques
                    ui.Tree({"ID": "BlocksTree", "Weight": 1.0}),
                    # Barra de Estado
                    ui.Label({"ID": "StatusLabel", "Text": "Listo para analizar la línea de tiempo activa."}),
                    # Pie de página / Acerca de
                    ui.HGroup(
                        [
                            ui.Button({"ID": "AboutBtn", "Text": "ℹ️ Acerca de DaVinci Flow"}),
                            ui.Button({"ID": "CloseBtn", "Text": "Cerrar"}),
                        ]
                    ),
                ]
            )
        ],
    )

    items = win.GetItems()

    # Cargar opciones en ComboBoxes
    items["ThemeCombo"].AddItem("Ely")
    items["ThemeCombo"].AddItem("Aurora")

    items["ProfileCombo"].AddItem("Natural")
    items["ProfileCombo"].AddItem("Dinámico")
    items["ProfileCombo"].AddItem("Reflexivo")
    items["ProfileCombo"].AddItem("Educativo")
    items["ProfileCombo"].AddItem("Vídeo Corto")

    # Configurar columnas del árbol
    hdr = items["BlocksTree"].NewItem()
    hdr.Text[0] = "Tiempo (f)"
    hdr.Text[1] = "Capas"
    hdr.Text[2] = "Contexto"
    hdr.Text[3] = "Principal"
    hdr.Text[4] = "Acento"
    hdr.Text[5] = "SFX"
    items["BlocksTree"].SetHeaderItem(hdr)
    items["BlocksTree"].ColumnCount = 6

    # Variables de estado
    current_plan: list[GenerationPlan] = []
    last_record: list[GenerationExecutionRecord] = []

    # Callbacks
    def on_analyze(ev: Any) -> None:
        track = int(items["TrackSpin"].Value)
        theme_idx = int(items["ThemeCombo"].CurrentIndex)
        theme_name = "ely" if theme_idx == 0 else "aurora"

        prof_map = {0: "natural", 1: "dinamico", 2: "reflexivo", 3: "educativo", 4: "video_corto"}
        profile_name = prof_map.get(int(items["ProfileCombo"].CurrentIndex), "natural")
        enable_sfx = bool(items["SFXCheck"].Checked)

        items["StatusLabel"].Text = "Analizando subtítulos y clasificando capas..."
        try:
            plan = plan_active_subtitles(
                track_index=track,
                theme_name=theme_name,
                profile_name=profile_name,
                enable_sfx=enable_sfx,
            )
            current_plan.clear()
            current_plan.append(plan)

            items["BlocksTree"].Clear()
            for b in plan.blocks:
                tree_item = items["BlocksTree"].NewItem()
                tree_item.Text[0] = f"{b.start_frame:g}-{b.end_frame:g}"
                tree_item.Text[1] = f"{b.layer_count} capas"
                tree_item.Text[2] = b.context_text or "—"
                tree_item.Text[3] = b.main_text
                tree_item.Text[4] = b.accent_text or "—"
                tree_item.Text[5] = b.sfx_proposal or "—"
                items["BlocksTree"].AddTopLevelItem(tree_item)

            items["StatusLabel"].Text = (
                f"✅ Plan listo: {plan.block_count} bloques clasificados. "
                f"Capas: {plan.layer_distribution}."
            )
        except DaVinciFlowError as err:
            items["StatusLabel"].Text = f"❌ Error: {err}"

    def on_generate(ev: Any) -> None:
        track = int(items["TrackSpin"].Value)
        theme_idx = int(items["ThemeCombo"].CurrentIndex)
        theme_name = "ely" if theme_idx == 0 else "aurora"

        prof_map = {0: "natural", 1: "dinamico", 2: "reflexivo", 3: "educativo", 4: "video_corto"}
        profile_name = prof_map.get(int(items["ProfileCombo"].CurrentIndex), "natural")
        enable_sfx = bool(items["SFXCheck"].Checked)
        dry_run = bool(items["DryRunCheck"].Checked)

        items["StatusLabel"].Text = "Generando elementos en la línea de tiempo..."
        try:
            record = generate_from_active_timeline(
                track_index=track,
                theme_name=theme_name,
                profile_name=profile_name,
                enable_sfx=enable_sfx,
                dry_run=dry_run,
            )
            last_record.clear()
            last_record.append(record)

            label = "Simulación" if dry_run else "Generación"
            items["StatusLabel"].Text = (
                f"🎉 {label} completada exitosamente: {record.item_count} clips creados en pistas dedicadas."
            )
        except DaVinciFlowError as err:
            items["StatusLabel"].Text = f"❌ Error: {err}"

    def on_about(ev: Any) -> None:
        items["StatusLabel"].Text = "DaVinci Flow v0.1.0 por biglexj | Donaciones: https://www.biglexj.com/donaciones"

    def on_close(ev: Any) -> None:
        dispatcher.ExitLoop()

    win.On.AnalyzeBtn.Clicked = on_analyze
    win.On.GenerateBtn.Clicked = on_generate
    win.On.AboutBtn.Clicked = on_about
    win.On.CloseBtn.Clicked = on_close
    win.On.DaVinciFlowWin.Close = on_close

    win.Show()
    dispatcher.RunLoop()
    win.Hide()
    return win


def open_davinci_flow_ui() -> None:
    """Función de entrada directa para invocar la interfaz gráfica."""
    create_uimanager_window()
