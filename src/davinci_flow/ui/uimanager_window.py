"""Interfaz gráfica de DaVinci Flow no bloqueante con soporte para Guion, SRT, Corrección IA y Marcadores."""

import json
import re
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from davinci_flow.ai.aligner import parse_glossary_str
from davinci_flow.ai.client import list_available_gemini_models
from davinci_flow.ai.credentials import (
    get_gemini_api_key,
    has_gemini_api_key,
    mask_api_key,
    save_gemini_api_key,
)
from davinci_flow.application import (
    generate_from_active_timeline,
    get_available_mediapool_presets,
    inspect_active_timeline,
    plan_active_subtitles,
    propose_brolls_for_plan,
)
from davinci_flow.errors import DaVinciFlowError
from davinci_flow.generation.plan import GenerationPlan
from davinci_flow.subtitles.srt_parser import export_srt_file

def _try_create_uimanager_window(
    resolve_app: Any = None,
    fusion_app: Any = None,
    bmd_module: Any = None,
) -> bool:
    """Crea la ventana nativa con estilo gris neutro DaVinci y disposición espaciada en filas limpias."""
    if fusion_app is None:
        if resolve_app is not None and hasattr(resolve_app, "Fusion"):
            try:
                fusion_app = resolve_app.Fusion()
            except Exception:
                fusion_app = None

    if fusion_app is None:
        main_mod = sys.modules.get("__main__")
        if main_mod:
            fusion_app = getattr(main_mod, "fusion", None) or getattr(main_mod, "fu", None)
        if fusion_app is None:
            fusion_app = getattr(__builtins__, "fusion", None) or getattr(__builtins__, "fu", None)

    if fusion_app is None:
        try:
            import fusionscript  # type: ignore[import-not-found]
            fusion_app = fusionscript.scriptapp("Fusion")
        except Exception:
            pass

    if fusion_app is None:
        return False

    ui = getattr(fusion_app, "UIManager", None)
    dispatcher = getattr(bmd_module, "UIDispatcher", None) if bmd_module else None
    if dispatcher is None and hasattr(fusion_app, "UIDispatcher"):
        dispatcher = fusion_app.UIDispatcher

    if ui is None or dispatcher is None:
        return False

    # Icono oficial transparente de assets
    icon_path = Path(__file__).resolve().parent.parent.parent.parent / "assets" / "branding" / "icons" / "icon-transparent.png"
    win_props: dict[str, Any] = {
        "WindowTitle": "DaVinci Flow — Subtítulos Dinámicos, Guion & Asistente IA",
        "ID": "DaVinciFlowWindow_v6",
        "Geometry": [300, 35, 980, 780],
        "MinimumSize": [880, 660],
        "Margin": 12,
        "Spacing": 6,
    }
    if icon_path.is_file():
        win_props["WindowIcon"] = str(icon_path)

    win = dispatcher.AddWindow(
        win_props,
        [
            ui.VGroup(
                {"Spacing": 5, "Margin": 0},
                [
                    # 1. Encabezado Centrado
                    ui.VGroup(
                        {"Spacing": 1, "Weight": 0},
                        [
                            ui.Label(
                                {
                                    "Text": "<b>DaVinci Flow</b> — Subtítulos Dinámicos Multicapa, B-Rolls & Asistente IA",
                                    "Alignment": {"AlignHCenter": True},
                                    "Font": ui.Font({"PixelSize": 12, "Bold": True}),
                                    "Weight": 0,
                                }
                            ),
                            ui.Label(
                                {
                                    "ID": "HeaderInfoLabel",
                                    "Text": "Inspeccionando sesión activa...",
                                    "Alignment": {"AlignHCenter": True},
                                    "Font": ui.Font({"PixelSize": 10}),
                                    "Weight": 0,
                                }
                            ),
                        ]
                    ),
                    ui.VGap(1),

                    # 2. Fila 1: Origen de Transcripción y Pistas
                    ui.HGroup(
                        {"Spacing": 8, "Weight": 0},
                        [
                            ui.Label({"Text": "Origen:", "Weight": 0}),
                            ui.ComboBox(
                                {
                                    "ID": "SourceCombo",
                                    "FixedSize": [105, 24],
                                    "Weight": 0,
                                }
                            ),
                            ui.Label({"Text": "Pista:", "Weight": 0}),
                            ui.SpinBox(
                                {
                                    "ID": "TrackSpin",
                                    "Value": 1,
                                    "Minimum": 1,
                                    "Maximum": 16,
                                    "FixedSize": [48, 24],
                                    "Weight": 0,
                                }
                            ),
                            ui.HGap(1),
                            ui.Button(
                                {
                                    "ID": "ReadTimelineBtn",
                                    "Text": "🎬 Leer Pista Resolve",
                                    "FixedSize": [130, 24],
                                    "Weight": 0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "LoadSrtBtn",
                                    "Text": "📂 Cargar SRT",
                                    "FixedSize": [110, 24],
                                    "Weight": 0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "ExportSrtBtn",
                                    "Text": "💾 Exportar SRT",
                                    "FixedSize": [115, 24],
                                    "Weight": 0,
                                }
                            ),
                        ]
                    ),

                    # 3. Fila 2: Estilos, Capas y Animación
                    ui.HGroup(
                        {"Spacing": 8, "Weight": 0},
                        [
                            ui.Label({"Text": "Tema / Preset:", "Weight": 0}),
                            ui.ComboBox(
                                {
                                    "ID": "ThemeCombo",
                                    "FixedSize": [180, 24],
                                    "Weight": 0,
                                }
                            ),
                            ui.Label({"Text": "Perfil:", "Weight": 0}),
                            ui.ComboBox(
                                {
                                    "ID": "ProfileCombo",
                                    "FixedSize": [110, 24],
                                    "Weight": 0,
                                }
                            ),
                            ui.Label({"Text": "Animación:", "Weight": 0}),
                            ui.ComboBox(
                                {
                                    "ID": "AnimCombo",
                                    "FixedSize": [140, 24],
                                    "Weight": 0,
                                }
                            ),
                        ]
                    ),

                    # 4. Fila 3: API Key Gemini + Modelo Dinámico + Botón Guardar
                    ui.HGroup(
                        {"Spacing": 8, "Weight": 0},
                        [
                            ui.Label({"Text": "API Key Gemini:", "Weight": 0}),
                            ui.LineEdit(
                                {
                                    "ID": "ApiKeyInput",
                                    "PlaceholderText": "Clave API Gemini o usa GEMINI_API_KEY...",
                                    "EchoMode": "Password",
                                    "Weight": 1.0,
                                }
                            ),
                            ui.Label({"Text": "Modelo:", "Weight": 0}),
                            ui.ComboBox(
                                {
                                    "ID": "AiModelCombo",
                                    "FixedSize": [165, 24],
                                    "Weight": 0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "SaveKeyBtn",
                                    "Text": "💾 Guardar",
                                    "FixedSize": [80, 24],
                                    "Weight": 0,
                                }
                            ),
                        ]
                    ),

                    # 5. Fila 4: Glosario de Marcas / Jergas
                    ui.HGroup(
                        {"Spacing": 8, "Weight": 0},
                        [
                            ui.Label({"Text": "Glosario/Jergas:", "Weight": 0}),
                            ui.LineEdit(
                                {
                                    "ID": "GlossaryInput",
                                    "PlaceholderText": "Reemplazos fijos (ej: biglex: Biglex J, resolve: DaVinci, python: Python 3)",
                                    "Weight": 1.0,
                                }
                            ),
                        ]
                    ),

                    # 6. Fila 5A: Guion Original y Botón de Carga
                    ui.HGroup(
                        {"Spacing": 8, "Weight": 0},
                        [
                            ui.Label(
                                {
                                    "Text": "Guion Original (Referencia para sincronización y marcadores):",
                                    "Weight": 0,
                                }
                            ),
                            ui.HGap(1),
                            ui.Button(
                                {
                                    "ID": "LoadScriptBtn",
                                    "Text": "📄 Cargar Guion .txt",
                                    "FixedSize": [140, 22],
                                    "Weight": 0,
                                }
                            ),
                        ]
                    ),
                    # Área de Texto de Guion
                    ui.TextEdit(
                        {
                            "ID": "ScriptTextEdit",
                            "PlaceholderText": "Pega aquí o carga el guion original completo para comparar y corregir los subtítulos...",
                            "MinimumSize": [100, 55],
                            "MaximumSize": [4000, 65],
                            "Weight": 0,
                        }
                    ),

                    # Fila 5B: Carpeta de Assets / B-Rolls
                    ui.HGroup(
                        {"Spacing": 8, "Weight": 0},
                        [
                            ui.Label({"Text": "Carpeta Assets/B-Rolls:", "Weight": 0}),
                            ui.LineEdit(
                                {
                                    "ID": "AssetsDirInput",
                                    "PlaceholderText": "Carpeta local con vídeos de apoyo o efectos sonoros...",
                                    "Weight": 1.0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "BrowseAssetsBtn",
                                    "Text": "📁 Seleccionar...",
                                    "FixedSize": [115, 22],
                                    "Weight": 0,
                                }
                            ),
                        ]
                    ),

                    # 7. Fila 6: Opciones y Switches de Generación
                    ui.HGroup(
                        {"Spacing": 10, "Weight": 0},
                        [
                            ui.CheckBox({"ID": "SFXCheck", "Text": "SFX Automáticos", "Checked": True, "Weight": 0}),
                            ui.CheckBox({"ID": "BRollCheck", "Text": "🎬 B-Rolls Contextuales", "Checked": False, "Weight": 0}),
                            ui.CheckBox({"ID": "DryRunCheck", "Text": "Dry-Run (Simulación)", "Checked": False, "Weight": 0}),
                            ui.CheckBox({"ID": "CorrectAiCheck", "Text": "✨ Corregir con Guion/IA", "Checked": True, "Weight": 0}),
                            ui.CheckBox({"ID": "MarkersAiCheck", "Text": "🎯 Marcadores Cromáticos", "Checked": True, "Weight": 0}),
                        ]
                    ),

                    # 8. Fila 7A: Botones de Acción Principales
                    ui.HGroup(
                        {"Spacing": 6, "Weight": 0},
                        [
                            ui.Button(
                                {
                                    "ID": "AnalyzeBtn",
                                    "Text": "🔍 Análisis local",
                                    "Weight": 1.0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "AiCorrectBtn",
                                    "Text": "✨ Corregir con IA",
                                    "Weight": 1.0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "GenerateBtn",
                                    "Text": "Editor LLM · Fase 1",
                                    "Weight": 1.0,
                                }
                            ),
                        ]
                    ),

                    # Fila 6B: Botones de Control y Reversión
                    ui.HGroup(
                        {"Spacing": 6, "Weight": 0},
                        [
                            ui.Button(
                                {
                                    "ID": "RevertBtn",
                                    "Text": "🔄 Deshacer Última Generación",
                                    "Weight": 1.0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "StopBtn",
                                    "Text": "⏹️ Detener Proceso",
                                    "Weight": 1.0,
                                    "Enabled": False,
                                }
                            ),
                        ]
                    ),

                    # 8. Fila 7: Árbol de Subtítulos y Capas
                    ui.Tree(
                        {
                            "ID": "BlocksTree",
                            "ColumnCount": 7,
                            "Weight": 1.0,
                        }
                    ),

                    # 9. Fila 8: Barra de Estado y Cierre
                    ui.HGroup(
                        {"Spacing": 8, "Weight": 0},
                        [
                            ui.Label(
                                {
                                    "ID": "StatusLabel",
                                    "Text": "Listo.",
                                    "Weight": 1.0,
                                    "Font": ui.Font({"PixelSize": 10}),
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "AboutBtn",
                                    "Text": "ℹ️ Info",
                                    "FixedSize": [70, 24],
                                    "Weight": 0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "CloseBtn",
                                    "Text": "Cerrar",
                                    "FixedSize": [80, 24],
                                    "Weight": 0,
                                }
                            ),
                        ]
                    ),
                ]
            )
        ],
    )

    items = win.GetItems()

    # Aplicar paleta moderna DaVinci + Ely Turquesa (#00C7B1)
    davinci_modern_qss = """
        QWidget {
            background-color: #181d26;
            color: #e1e7ed;
            font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            font-size: 11px;
        }
        QLineEdit, QTextEdit, QSpinBox, QComboBox {
            background-color: #14181f;
            color: #ffffff;
            border: 1px solid #2b3647;
            border-radius: 4px;
            padding: 3px 6px;
            selection-background-color: #00C7B1;
            selection-color: #ffffff;
        }
        QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {
            border: 1px solid #00C7B1;
        }
        QPushButton {
            background-color: #202836;
            color: #e1e7ed;
            border: 1px solid #2b3647;
            border-radius: 4px;
            padding: 4px 10px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2a3547;
            border: 1px solid #00C7B1;
            color: #ffffff;
        }
        QPushButton:pressed {
            background-color: #14181f;
            border: 1px solid #00C7B1;
        }
        QPushButton#GenerateBtn, QPushButton#AiCorrectBtn {
            background-color: #00C7B1;
            color: #091a18;
            border: none;
            font-weight: bold;
        }
        QPushButton#GenerateBtn:hover, QPushButton#AiCorrectBtn:hover {
            background-color: #01D6B9;
            color: #091a18;
        }
        QPushButton#StopBtn {
            background-color: #361c20;
            color: #ff7782;
            border: 1px solid #5c2a30;
        }
        QPushButton#StopBtn:hover {
            background-color: #48242a;
        }
        QTreeWidget, QTreeView {
            background-color: #14181f;
            color: #e1e7ed;
            border: 1px solid #2b3647;
            alternate-background-color: #181d26;
        }
        QHeaderView::section {
            background-color: #1c232e;
            color: #8b98a5;
            border: none;
            padding: 4px;
            font-weight: bold;
        }
        QCheckBox {
            color: #e1e7ed;
            spacing: 6px;
        }
        QCheckBox::indicator {
            width: 14px;
            height: 14px;
            background-color: #14181f;
            border: 1px solid #2b3647;
            border-radius: 3px;
        }
        QCheckBox::indicator:checked {
            background-color: #00C7B1;
            border: 1px solid #01D6B9;
        }
    """
    try:
        win.SetAttribute("StyleSheet", davinci_modern_qss)
    except Exception:
        try:
            win.StyleSheet = davinci_modern_qss
        except Exception:
            pass

    items["SourceCombo"].AddItem("Subtítulos")
    items["SourceCombo"].AddItem("Vídeo (Text+)")
    items["SourceCombo"].AddItem("Auto")

    items["ThemeCombo"].AddItem("Ely")
    items["ThemeCombo"].AddItem("Aurora")

    items["ProfileCombo"].AddItem("Natural")
    items["ProfileCombo"].AddItem("Dinámico")
    items["ProfileCombo"].AddItem("Reflexivo")
    items["ProfileCombo"].AddItem("Educativo")
    items["ProfileCombo"].AddItem("Vídeo Corto")

    items["AnimCombo"].AddItem("Auto (Perfil)")
    items["AnimCombo"].AddItem("Pop Bounce")
    items["AnimCombo"].AddItem("Slide Up")
    items["AnimCombo"].AddItem("Smooth Fade")
    items["AnimCombo"].AddItem("Kinetic Pulse")
    items["AnimCombo"].AddItem("Typewriter")
    items["AnimCombo"].AddItem("Estático (None)")

    items["AiModelCombo"].AddItem("gemini-3.5-flash")
    items["AiModelCombo"].AddItem("gemini-3.5-flash-lite")
    items["AiModelCombo"].AddItem("gemini-3.7-flash")
    items["AiModelCombo"].AddItem("gemini-3.1-pro")
    items["AiModelCombo"].AddItem("gemini-3.0-flash")

    # Autocargar clave si existe
    if has_gemini_api_key():
        try:
            saved_k = get_gemini_api_key()
            items["ApiKeyInput"].Text = saved_k
        except Exception:
            pass

    try:
        tree = items["BlocksTree"]
        tree.ColumnCount = 8
        tree.SetHeaderLabels(["Tiempo (f)", "Capas", "Contexto", "Principal (Corregido)", "Acento", "SFX", "Animación", "B-Roll / SFX"])
        tree.ColumnWidth[0] = 80
        tree.ColumnWidth[1] = 50
        tree.ColumnWidth[2] = 100
        tree.ColumnWidth[3] = 175
        tree.ColumnWidth[4] = 85
        tree.ColumnWidth[5] = 60
        tree.ColumnWidth[6] = 75
        tree.ColumnWidth[7] = 95
    except Exception:
        pass

    current_plan: list[GenerationPlan] = []
    loaded_srt_path: list[str] = []
    cancel_flag = [False]
    is_running = [False]

    def refresh_models_list() -> None:
        try:
            key_text = str(items["ApiKeyInput"].Text or "").strip() or None
            models = list_available_gemini_models(api_key=key_text)
            current_model = str(items["AiModelCombo"].CurrentText or "").strip()
            items["AiModelCombo"].Clear()
            for m in models:
                items["AiModelCombo"].AddItem(m)
            if current_model:
                for idx in range(getattr(items["AiModelCombo"], "Count", 0) or 0):
                    if str(items["AiModelCombo"].ItemText[idx]) == current_model:
                        items["AiModelCombo"].CurrentIndex = idx
                        break
        except Exception:
            pass

    def refresh_presets_list() -> None:
        try:
            presets = get_available_mediapool_presets()
            current_txt = str(items["ThemeCombo"].CurrentText or "")
            items["ThemeCombo"].Clear()
            items["ThemeCombo"].AddItem("Ely")
            items["ThemeCombo"].AddItem("Aurora")
            for p in presets:
                items["ThemeCombo"].AddItem(p.display_label)
            if current_txt:
                for idx in range(getattr(items["ThemeCombo"], "Count", 0) or 0):
                    if str(items["ThemeCombo"].ItemText[idx]) == current_txt:
                        items["ThemeCombo"].CurrentIndex = idx
                        break
        except Exception:
            pass

    def refresh_timeline_info() -> None:
        try:
            refresh_presets_list()
            refresh_models_list()
            summary = inspect_active_timeline()
            sub_cues = summary.subtitle_cues_counts.get(1, 0)
            items["HeaderInfoLabel"].Text = (
                f"Proyecto: {summary.project_name} | Línea de tiempo: {summary.timeline_name} | Pistas Subtítulos: {summary.subtitle_track_count}"
            )
            if sub_cues > 0:
                on_analyze(None)
            else:
                items["StatusLabel"].Text = "⚠️ Pista 1 sin subtítulos detectados. Puedes cargar un archivo .SRT o usar pista de vídeo."
        except Exception as err:
            items["StatusLabel"].Text = f"Aviso de conexión: {err}"

    def on_save_key(ev: Any) -> None:
        key_text = str(items["ApiKeyInput"].Text or "").strip()
        if not key_text:
            items["StatusLabel"].Text = "⚠️ La clave API no puede estar vacía."
            return
        try:
            save_gemini_api_key(key_text)
            refresh_models_list()
            items["StatusLabel"].Text = f"✅ Clave API guardada ({mask_api_key(key_text)}). Modelos actualizados."
        except Exception as err:
            items["StatusLabel"].Text = f"❌ Error al guardar clave: {err}"

    def on_load_srt(ev: Any) -> None:
        try:
            root_tk = tk.Tk()
            root_tk.withdraw()
            root_tk.attributes("-topmost", True)
            filepath = filedialog.askopenfilename(
                title="Seleccionar archivo de subtítulos SRT",
                filetypes=[("Archivos SubRip SRT", "*.srt"), ("Todos los archivos", "*.*")],
            )
            root_tk.destroy()
            if filepath:
                loaded_srt_path.clear()
                loaded_srt_path.append(filepath)
                items["StatusLabel"].Text = f"📂 Subtítulos SRT: {Path(filepath).name}. Analizando..."
                on_analyze(None)
        except Exception as err:
            items["StatusLabel"].Text = f"Error al abrir diálogo SRT: {err}"

    def on_export_srt(ev: Any) -> None:
        if not current_plan or current_plan[0].block_count == 0:
            items["StatusLabel"].Text = "⚠️ No hay subtítulos analizados para exportar. Pulsa 'Analizar Transcripción' primero."
            return
        try:
            root_tk = tk.Tk()
            root_tk.withdraw()
            root_tk.attributes("-topmost", True)
            filepath = filedialog.asksaveasfilename(
                title="Exportar subtítulos corregidos a SRT",
                defaultextension=".srt",
                filetypes=[("Archivos SubRip SRT", "*.srt"), ("Todos los archivos", "*.*")],
            )
            root_tk.destroy()
            if filepath:
                plan = current_plan[0]
                cues = [b.to_subtitle_cue() for b in plan.blocks]
                export_srt_file(filepath, cues, fps=plan.fps)
                items["StatusLabel"].Text = f"💾 Subtítulos exportados a {Path(filepath).name}."
        except Exception as err:
            items["StatusLabel"].Text = f"Error al exportar SRT: {err}"

    def on_load_script(ev: Any) -> None:
        try:
            root_tk = tk.Tk()
            root_tk.withdraw()
            root_tk.attributes("-topmost", True)
            filepath = filedialog.askopenfilename(
                title="Seleccionar archivo de Guion",
                filetypes=[("Archivos de texto", "*.txt;*.md"), ("Todos los archivos", "*.*")],
            )
            root_tk.destroy()
            if filepath:
                content = Path(filepath).read_text(encoding="utf-8", errors="ignore")
                items["ScriptTextEdit"].PlainText = content
                items["StatusLabel"].Text = f"📄 Guion cargado: {Path(filepath).name} ({len(content.splitlines())} líneas)."
        except Exception as err:
            items["StatusLabel"].Text = f"Error al cargar guion: {err}"

    def on_browse_assets(ev: Any) -> None:
        try:
            root_tk = tk.Tk()
            root_tk.withdraw()
            root_tk.attributes("-topmost", True)
            dirpath = filedialog.askdirectory(
                title="Seleccionar carpeta de Assets / B-Rolls y Sonidos"
            )
            root_tk.destroy()
            if dirpath:
                items["AssetsDirInput"].Text = dirpath
                items["StatusLabel"].Text = f"📁 Carpeta de assets: {Path(dirpath).name}."
                if current_plan:
                    on_analyze(None)
        except Exception as err:
            items["StatusLabel"].Text = f"Error al seleccionar assets: {err}"

    def on_stop(ev: Any) -> None:
        cancel_flag[0] = True
        items["StatusLabel"].Text = "⏹️ Cancelación solicitada... Deteniendo tras el bloque actual."

    def _selected_track_type() -> str:
        idx = int(items["SourceCombo"].CurrentIndex) if "SourceCombo" in items else 0
        types = ["subtitle", "video", "auto"]
        return types[idx] if 0 <= idx < len(types) else "subtitle"

    def _selected_theme_and_preset() -> tuple[str, str | None]:
        txt = str(items["ThemeCombo"].CurrentText or "Ely").strip()
        if txt.startswith("📁"):
            return "ely", txt
        return txt.lower(), None

    def _selected_anim_preset() -> str | None:
        idx = int(items["AnimCombo"].CurrentIndex) if "AnimCombo" in items else 0
        anim_map = {0: None, 1: "pop_bounce", 2: "slide_up", 3: "fade_smooth", 4: "kinetic_pulse", 5: "typewriter", 6: "none"}
        return anim_map.get(idx)

    def _selected_ai_model() -> str:
        if "AiModelCombo" in items:
            txt = str(items["AiModelCombo"].CurrentText or "").strip()
            if txt:
                return txt
        return "gemini-2.5-flash"

    def on_analyze(ev: Any = None) -> None:
        if is_running[0]:
            return
        cancel_flag[0] = False
        is_running[0] = True
        items["AnalyzeBtn"].Enabled = False
        items["AiCorrectBtn"].Enabled = False
        items["GenerateBtn"].Enabled = False
        items["StopBtn"].Enabled = True

        track = int(items["TrackSpin"].Value)
        track_type = _selected_track_type()
        theme_name, _ = _selected_theme_and_preset()
        prof_map = {0: "natural", 1: "dinamico", 2: "reflexivo", 3: "educativo", 4: "video_corto"}
        profile_name = prof_map.get(int(items["ProfileCombo"].CurrentIndex), "natural")
        enable_sfx = bool(items["SFXCheck"].Checked)
        enable_brolls = bool(items["BRollCheck"].Checked) if "BRollCheck" in items else False
        assets_dir = str(items["AssetsDirInput"].Text or "").strip() or None if "AssetsDirInput" in items else None
        srt_file = loaded_srt_path[0] if loaded_srt_path else None
        glossary_text = str(items["GlossaryInput"].Text or "").strip()
        glossary = parse_glossary_str(glossary_text)
        anim_preset = _selected_anim_preset()

        t0 = time.time()
        try:
            items["StatusLabel"].Text = f"🔍 Leyendo pista {track} ({track_type}) y clasificando subtítulos..."
            plan, _ = plan_active_subtitles(
                track_index=track,
                track_type=track_type,
                theme_name=theme_name,
                profile_name=profile_name,
                enable_sfx=enable_sfx,
                glossary=glossary,
                use_ai_correction=False,
                animation_preset=anim_preset,
                srt_path=srt_file,
            )
            if plan.block_count == 0:
                items["StatusLabel"].Text = f"⚠️ La pista {track} ({track_type}) está vacía. No contiene subtítulos."
                items["BlocksTree"].Clear()
                current_plan.clear()
                return

            current_plan.clear()
            current_plan.append(plan)

            broll_map: dict[int, str] = {}
            if enable_brolls and assets_dir:
                try:
                    proposals = propose_brolls_for_plan(plan, assets_directory=assets_dir, use_ai=False)
                    broll_map = {p.block_index: p.asset.name for p in proposals}
                except Exception:
                    pass

            items["BlocksTree"].Clear()
            for b_idx, b in enumerate(plan.blocks, start=1):
                if cancel_flag[0]:
                    break
                it = items["BlocksTree"].NewItem()
                it.Text[0] = f"{b.start_frame:g}-{b.end_frame:g}"
                it.Text[1] = f"{b.layer_count} capas"
                it.Text[2] = b.context_text or "—"
                it.Text[3] = b.main_text
                it.Text[4] = b.accent_text or "—"
                it.Text[5] = b.sfx_proposal or "—"
                it.Text[6] = b.style_preset or "auto"
                it.Text[7] = broll_map.get(b_idx, "—")
                items["BlocksTree"].AddTopLevelItem(it)

            elapsed = round(time.time() - t0, 2)
            items["StatusLabel"].Text = f"✅ Transcripción cargada ({plan.block_count} bloques) en {elapsed}s. Listo para generar o corregir."
        except Exception as err:
            items["StatusLabel"].Text = f"❌ Error al analizar: {err}"
        finally:
            is_running[0] = False
            items["AnalyzeBtn"].Enabled = True
            items["AiCorrectBtn"].Enabled = True
            items["GenerateBtn"].Enabled = True
            items["StopBtn"].Enabled = False

    def on_ai_correct(ev: Any = None) -> None:
        if is_running[0]:
            return
        cancel_flag[0] = False
        is_running[0] = True
        items["AnalyzeBtn"].Enabled = False
        items["AiCorrectBtn"].Enabled = False
        items["GenerateBtn"].Enabled = False
        items["StopBtn"].Enabled = True

        track = int(items["TrackSpin"].Value)
        track_type = _selected_track_type()
        theme_name, _ = _selected_theme_and_preset()
        prof_map = {0: "natural", 1: "dinamico", 2: "reflexivo", 3: "educativo", 4: "video_corto"}
        profile_name = prof_map.get(int(items["ProfileCombo"].CurrentIndex), "natural")
        enable_sfx = bool(items["SFXCheck"].Checked)
        enable_brolls = bool(items["BRollCheck"].Checked) if "BRollCheck" in items else False
        assets_dir = str(items["AssetsDirInput"].Text or "").strip() or None if "AssetsDirInput" in items else None
        script_text = str(items["ScriptTextEdit"].PlainText or "").strip()
        glossary_text = str(items["GlossaryInput"].Text or "").strip()
        glossary = parse_glossary_str(glossary_text)
        api_key = str(items["ApiKeyInput"].Text or "").strip() or None
        srt_file = loaded_srt_path[0] if loaded_srt_path else None
        anim_preset = _selected_anim_preset()
        ai_model = _selected_ai_model()

        def progress_cb(curr: int, total: int, msg: str) -> None:
            items["StatusLabel"].Text = f"🤖 {msg}"

        t0 = time.time()
        try:
            items["StatusLabel"].Text = f"🤖 Conectando con Gemini ({ai_model}) para alineación..."
            plan, corr = plan_active_subtitles(
                track_index=track,
                track_type=track_type,
                theme_name=theme_name,
                profile_name=profile_name,
                enable_sfx=enable_sfx,
                original_script=script_text,
                glossary=glossary,
                api_key=api_key,
                model_name=ai_model,
                use_ai_correction=True,
                animation_preset=anim_preset,
                srt_path=srt_file,
                progress_callback=progress_cb,
            )
            if plan.block_count == 0:
                items["StatusLabel"].Text = f"⚠️ La pista {track} está vacía."
                items["BlocksTree"].Clear()
                current_plan.clear()
                return

            current_plan.clear()
            current_plan.append(plan)

            broll_map: dict[int, str] = {}
            if enable_brolls and assets_dir:
                try:
                    proposals = propose_brolls_for_plan(
                        plan,
                        assets_directory=assets_dir,
                        api_key=api_key,
                        model_name=ai_model,
                        use_ai=True,
                    )
                    broll_map = {p.block_index: p.asset.name for p in proposals}
                except Exception:
                    pass

            items["BlocksTree"].Clear()
            for b_idx, b in enumerate(plan.blocks, start=1):
                if cancel_flag[0]:
                    break
                it = items["BlocksTree"].NewItem()
                it.Text[0] = f"{b.start_frame:g}-{b.end_frame:g}"
                it.Text[1] = f"{b.layer_count} capas"
                it.Text[2] = b.context_text or "—"
                it.Text[3] = b.main_text
                it.Text[4] = b.accent_text or "—"
                it.Text[5] = b.sfx_proposal or "—"
                it.Text[6] = b.style_preset or "auto"
                it.Text[7] = broll_map.get(b_idx, "—")
                items["BlocksTree"].AddTopLevelItem(it)

            elapsed = round(time.time() - t0, 1)
            corr_count = corr.total_corrections if corr else 0
            mark_count = corr.total_markers if corr else 0
            broll_count = len(broll_map)
            items["StatusLabel"].Text = f"✨ Corrección IA completada ({ai_model}) en {elapsed}s: {corr_count} correcciones, {mark_count} marcadores y {broll_count} B-Rolls propuestos."
        except Exception as err:
            items["StatusLabel"].Text = f"❌ Error en corrección IA: {err}"
        finally:
            is_running[0] = False
            items["AnalyzeBtn"].Enabled = True
            items["AiCorrectBtn"].Enabled = True
            items["GenerateBtn"].Enabled = True
            items["StopBtn"].Enabled = False

    def on_generate(ev: Any = None) -> None:
        if is_running[0]:
            return
        cancel_flag[0] = False
        is_running[0] = True

        track = int(items["TrackSpin"].Value)
        track_type = _selected_track_type()
        theme_name, preset_name = _selected_theme_and_preset()
        prof_map = {0: "natural", 1: "dinamico", 2: "reflexivo", 3: "educativo", 4: "video_corto"}
        profile_name = prof_map.get(int(items["ProfileCombo"].CurrentIndex), "natural")
        enable_sfx = bool(items["SFXCheck"].Checked)
        enable_brolls = bool(items["BRollCheck"].Checked) if "BRollCheck" in items else False
        assets_dir = str(items["AssetsDirInput"].Text or "").strip() or None if "AssetsDirInput" in items else None
        dry_run = bool(items["DryRunCheck"].Checked)
        use_ai = bool(items["CorrectAiCheck"].Checked)
        add_markers = bool(items["MarkersAiCheck"].Checked)
        script_text = str(items["ScriptTextEdit"].PlainText or "").strip()
        glossary_text = str(items["GlossaryInput"].Text or "").strip()
        glossary = parse_glossary_str(glossary_text)
        api_key = str(items["ApiKeyInput"].Text or "").strip() or None
        srt_file = loaded_srt_path[0] if loaded_srt_path else None
        anim_preset = _selected_anim_preset()
        ai_model = _selected_ai_model()

        items["AnalyzeBtn"].Enabled = False
        items["AiCorrectBtn"].Enabled = False
        items["GenerateBtn"].Enabled = False
        items["StopBtn"].Enabled = True

        t0 = time.time()
        try:
            def progress_cb(curr: int, total: int, msg: str) -> None:
                items["StatusLabel"].Text = f"⚡ {msg}"

            items["StatusLabel"].Text = "⚡ Iniciando generación de subtítulos multicapa en DaVinci Resolve..."
            record = generate_from_active_timeline(
                track_index=track,
                track_type=track_type,
                theme_name=theme_name,
                profile_name=profile_name,
                enable_sfx=enable_sfx,
                dry_run=dry_run,
                original_script=script_text,
                glossary=glossary,
                api_key=api_key,
                model_name=ai_model,
                use_ai_correction=use_ai,
                animation_preset=anim_preset,
                insert_markers=add_markers,
                srt_path=srt_file,
                template_preset_name=preset_name,
                assets_directory=assets_dir,
                enable_brolls=enable_brolls,
                progress_callback=progress_cb,
                is_cancelled=lambda: cancel_flag[0],
            )
            elapsed = round(time.time() - t0, 1)
            if record.status == "cancelled":
                items["StatusLabel"].Text = f"⏹️ Generación detenida por el usuario ({record.item_count} clips creados en {elapsed}s)."
            else:
                if dry_run:
                    items["StatusLabel"].Text = f"🔎 Dry-Run completado en {elapsed}s: {record.item_count} elementos planificados (sin cambios en Resolve)."
                else:
                    items["StatusLabel"].Text = f"🎉 Generación completada en {elapsed}s: {record.item_count} clips creados y verificados en Resolve."
        except Exception as err:
            items["StatusLabel"].Text = f"❌ Error: {err}"
        finally:
            is_running[0] = False
            items["AnalyzeBtn"].Enabled = True
            items["AiCorrectBtn"].Enabled = True
            items["GenerateBtn"].Enabled = True
            items["StopBtn"].Enabled = False

    def on_revert(ev: Any) -> None:
        if is_running[0]:
            return
        items["StatusLabel"].Text = "Deshaciendo únicamente la última generación registrada..."
        try:
            from davinci_flow.application import revert_active_generation
            count = revert_active_generation()
            items["StatusLabel"].Text = f"🔄 Deshacer completado: {count} clips de la última generación eliminados."
        except Exception as err:
            items["StatusLabel"].Text = f"❌ Error al deshacer: {err}"

    def on_about(ev: Any) -> None:
        items["StatusLabel"].Text = "DaVinci Flow v0.2.0 • biglexj | Donaciones: https://www.biglexj.com/donaciones"

    def on_close(ev: Any) -> None:
        cancel_flag[0] = True
        dispatcher.ExitLoop()

    win.On.ReadTimelineBtn.Clicked = lambda ev: (loaded_srt_path.clear(), refresh_timeline_info())
    win.On.SourceCombo.CurrentIndexChanged = lambda ev: (loaded_srt_path.clear(), on_analyze(ev))
    win.On.TrackSpin.ValueChanged = lambda ev: (loaded_srt_path.clear(), on_analyze(ev))
    win.On.ThemeCombo.CurrentIndexChanged = lambda ev: on_analyze(ev)
    win.On.ProfileCombo.CurrentIndexChanged = lambda ev: on_analyze(ev)
    win.On.AnimCombo.CurrentIndexChanged = lambda ev: on_analyze(ev)
    win.On.SFXCheck.Clicked = lambda ev: on_analyze(ev)
    if "BRollCheck" in items:
        win.On.BRollCheck.Clicked = lambda ev: on_analyze(ev)
    if "BrowseAssetsBtn" in items:
        win.On.BrowseAssetsBtn.Clicked = on_browse_assets
    win.On.LoadSrtBtn.Clicked = on_load_srt
    win.On.ExportSrtBtn.Clicked = on_export_srt
    win.On.LoadScriptBtn.Clicked = on_load_script
    win.On.SaveKeyBtn.Clicked = on_save_key
    win.On.AnalyzeBtn.Clicked = on_analyze
    win.On.AiCorrectBtn.Clicked = on_ai_correct
    from davinci_flow.ui.editorial_window import launch_editorial_window
    win.On.GenerateBtn.Clicked = lambda ev: launch_editorial_window()
    win.On.RevertBtn.Clicked = on_revert
    win.On.StopBtn.Clicked = on_stop
    win.On.AboutBtn.Clicked = on_about
    win.On.CloseBtn.Clicked = on_close
    win.On.DaVinciFlowWindow_v6.Close = on_close

    refresh_timeline_info()

    win.Show()
    dispatcher.RunLoop()
    win.Hide()
    return True

def open_davinci_flow_ui(
    resolve_app: Any = None,
    fusion_app: Any = None,
    bmd_module: Any = None,
) -> None:
    """Los accesos de consola y Resolve abren el mismo espacio de trabajo con pestañas."""
    from davinci_flow.ui.tkinter_window import create_tkinter_window
    create_tkinter_window()

