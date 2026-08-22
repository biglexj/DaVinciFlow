"""Interfaz gráfica de DaVinci Flow no bloqueante con soporte para Guion, SRT, Corrección IA y Marcadores."""

import json
import re
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from davinci_flow.ai.aligner import CorrectionResult, TimelineMarker
from davinci_flow.ai.credentials import (
    get_gemini_api_key,
    has_gemini_api_key,
    mask_api_key,
    save_gemini_api_key,
)
from davinci_flow.application import (
    align_and_correct_subtitles,
    generate_from_active_timeline,
    insert_ai_timeline_markers,
    inspect_active_timeline,
    plan_active_subtitles,
    scan_active_subtitles,
)
from davinci_flow.errors import DaVinciFlowError
from davinci_flow.generation.plan import GenerationPlan
from davinci_flow.subtitles.srt_parser import load_srt_file


def parse_glossary_str(text: str) -> dict[str, str]:
    """Parsea una cadena de pares clave:valor o JSON a un diccionario de glosario."""
    if not text or not text.strip():
        return {}
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            data = json.loads(stripped)
            if isinstance(data, dict):
                return {str(k).strip(): str(v).strip() for k, v in data.items() if str(k).strip()}
        except Exception:
            pass

    glossary: dict[str, str] = {}
    items = re.split(r"[\n,]+", stripped)
    for item in items:
        if ":" in item:
            parts = item.split(":", 1)
            k, v = parts[0].strip(), parts[1].strip()
            if k:
                glossary[k] = v
        elif "->" in item:
            parts = item.split("->", 1)
            k, v = parts[0].strip(), parts[1].strip()
            if k:
                glossary[k] = v
    return glossary


def _try_create_uimanager_window(
    resolve_app: Any = None,
    fusion_app: Any = None,
    bmd_module: Any = None,
) -> bool:
    """Crea la ventana nativa con estilo gris neutro DaVinci y botón Cargar Guion junto a la etiqueta."""
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

    if fusion_app is None or not hasattr(fusion_app, "UIManager"):
        return False

    ui = fusion_app.UIManager

    if bmd_module is None:
        main_mod = sys.modules.get("__main__")
        if main_mod:
            bmd_module = getattr(main_mod, "bmd", None)
        if bmd_module is None:
            bmd_module = getattr(__builtins__, "bmd", None)
        if bmd_module is None:
            try:
                import bmd  # type: ignore[import-not-found]
                bmd_module = bmd
            except Exception:
                pass

    if bmd_module is None or not hasattr(bmd_module, "UIDispatcher"):
        return False

    dispatcher = bmd_module.UIDispatcher(ui)

    # Ventana amplia para que las filas de opciones y acciones no se compriman.
    win = dispatcher.AddWindow(
        {
            "WindowTitle": "DaVinci Flow — Subtítulos Dinámicos, Guion & Asistente IA",
            "ID": "DaVinciFlowWinV5",
            "Geometry": [480, 50, 900, 715],
            "MinimumSize": [820, 600],
            "Margin": 10,
            "Spacing": 4,
        },
        [
            ui.VGroup(
                {"Spacing": 4, "Margin": 0},
                [
                    # 1. Encabezado Centrado
                    ui.VGroup(
                        {"Spacing": 1, "Weight": 0},
                        [
                            ui.Label(
                                {
                                    "Text": "<b>DaVinci Flow</b> — Subtítulos Dinámicos Multicapa & Asistente IA",
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
                        ],
                    ),
                    ui.VGap(1),

                    # 2. Fila 1: Pista, Tema, Perfil, Leer Resolve, Cargar SRT
                    ui.HGroup(
                        {"Spacing": 6, "Weight": 0},
                        [
                            ui.Label({"Text": "Pista:", "Weight": 0}),
                            ui.SpinBox(
                                {
                                    "ID": "TrackSpin",
                                    "Value": 1,
                                    "Minimum": 1,
                                    "Maximum": 16,
                                    "FixedSize": [42, 24],
                                    "Weight": 0,
                                }
                            ),
                            ui.Label({"Text": "Tema:", "Weight": 0}),
                            ui.ComboBox(
                                {
                                    "ID": "ThemeCombo",
                                    "FixedSize": [80, 24],
                                    "Weight": 0,
                                }
                            ),
                            ui.Label({"Text": "Perfil:", "Weight": 0}),
                            ui.ComboBox(
                                {
                                    "ID": "ProfileCombo",
                                    "FixedSize": [100, 24],
                                    "Weight": 0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "ReadTimelineBtn",
                                    "Text": "🎬 Leer Pista",
                                    "FixedSize": [110, 24],
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
                        ]
                    ),

                    # 3. Fila 2: API Key + Botón Guardar en la misma línea
                    ui.HGroup(
                        {"Spacing": 6, "Weight": 0},
                        [
                            ui.Label({"Text": "API Key Gemini:", "FixedSize": [100, 24], "Weight": 0}),
                            ui.LineEdit(
                                {
                                    "ID": "ApiKeyInput",
                                    "PlaceholderText": "Clave API Gemini o usa GEMINI_API_KEY...",
                                    "EchoMode": "Password",
                                    "FixedSize": [640, 24],
                                    "Weight": 0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "SaveKeyBtn",
                                    "Text": "💾 Guardar",
                                    "FixedSize": [90, 24],
                                    "Weight": 0,
                                }
                            ),
                        ]
                    ),

                    # 4. Fila 3: Glosario de Marcas / Jergas
                    ui.HGroup(
                        {"Spacing": 6, "Weight": 0},
                        [
                            ui.Label({"Text": "Glosario/Marcas:", "FixedSize": [100, 24], "Weight": 0}),
                            ui.LineEdit(
                                {
                                    "ID": "GlossaryInput",
                                    "PlaceholderText": "Reemplazos fijos (ej: biglex: Biglex J, resolve: DaVinci)",
                                    "FixedSize": [736, 24],
                                    "Weight": 0,
                                }
                            ),
                        ]
                    ),

                    # 5. Fila 4: Guion Original inmediatamente seguido por el botón Cargar Guion
                    ui.HGroup(
                        {"Spacing": 8, "Weight": 0},
                        [
                            ui.Label(
                                {
                                    "Text": "Guion Original:",
                                    "Weight": 0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "LoadScriptBtn",
                                    "Text": "📄 Cargar Guion .txt",
                                    "FixedSize": [140, 22],
                                    "Weight": 0,
                                }
                            ),
                            ui.Label(
                                {
                                    "Text": "(Referencia para corrección y marcadores)",
                                    "Weight": 0,
                                }
                            ),
                            ui.HGap(1),
                        ]
                    ),
                    # Área de Texto de Guion
                    ui.TextEdit(
                        {
                            "ID": "ScriptTextEdit",
                            "PlaceholderText": "Pega aquí o carga el guion original completo para comparar y corregir los subtítulos...",
                            "FixedSize": [842, 75],
                            "Weight": 0,
                        }
                    ),

                    # 6. Fila 5: Checkboxes de Opciones
                    ui.HGroup(
                        {"Spacing": 10, "Weight": 0},
                        [
                            ui.CheckBox({"ID": "SFXCheck", "Text": "SFX", "Checked": True, "Weight": 0}),
                            ui.CheckBox({"ID": "DryRunCheck", "Text": "Dry-Run", "Checked": False, "Weight": 0}),
                            ui.CheckBox({"ID": "CorrectAiCheck", "Text": "✨ Corregir con Guion", "Checked": True, "Weight": 0}),
                            ui.CheckBox({"ID": "MarkersAiCheck", "Text": "🎯 Marcadores Timeline", "Checked": True, "Weight": 0}),
                        ]
                    ),

                    # 7. Fila 6: Botones de Acción
                    ui.HGroup(
                        {"Spacing": 6, "Weight": 0},
                        [
                            ui.Button(
                                {
                                    "ID": "AnalyzeBtn",
                                    "Text": "🔍 Analizar Transcripción",
                                    "FixedSize": [170, 26],
                                    "Weight": 0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "AiCorrectBtn",
                                    "Text": "✨ Corregir con IA",
                                    "FixedSize": [145, 26],
                                    "Weight": 0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "GenerateBtn",
                                    "Text": "⚡ Generar en Timeline",
                                    "FixedSize": [180, 26],
                                    "Weight": 0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "RevertBtn",
                                    "Text": "🔄 Deshacer",
                                    "FixedSize": [105, 26],
                                    "Weight": 0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "StopBtn",
                                    "Text": "⏹️ Detener",
                                    "FixedSize": [90, 26],
                                    "Weight": 0,
                                    "Enabled": False,
                                }
                            ),
                        ]
                    ),

                    # 8. Fila 7: Árbol de Subtítulos y Capas
                    ui.Tree(
                        {
                            "ID": "BlocksTree",
                            "ColumnCount": 6,
                            "Weight": 1.0,
                        }
                    ),

                    # 9. Fila 8: Barra de Estado y Cierre
                    ui.HGroup(
                        {"Spacing": 6, "Weight": 0},
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
                                    "FixedSize": [60, 22],
                                    "Weight": 0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "CloseBtn",
                                    "Text": "Cerrar",
                                    "FixedSize": [65, 22],
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

    # Aplicar paleta gris neutra DaVinci a la ventana
    davinci_neutral_qss = """
        QWidget {
            background-color: #202020;
            color: #CCCCCC;
            font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            font-size: 11px;
        }
        QLineEdit, QTextEdit, QSpinBox, QComboBox {
            background-color: #181818;
            color: #E0E0E0;
            border: 1px solid #383838;
            border-radius: 3px;
            padding: 2px 4px;
            selection-background-color: #404040;
            selection-color: #FFFFFF;
        }
        QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {
            border: 1px solid #4F4F4F;
        }
        QPushButton {
            background-color: #2B2B2B;
            color: #D6D6D6;
            border: 1px solid #3C3C3C;
            border-radius: 3px;
            padding: 3px 8px;
        }
        QPushButton:hover {
            background-color: #383838;
            border: 1px solid #4C4C4C;
        }
        QPushButton:pressed {
            background-color: #1C1C1C;
            border: 1px solid #303030;
        }
        QTreeWidget, QTreeView {
            background-color: #181818;
            color: #CCCCCC;
            border: 1px solid #383838;
            alternate-background-color: #1E1E1E;
        }
        QHeaderView::section {
            background-color: #262626;
            color: #999999;
            border: 1px solid #333333;
            padding: 3px;
            font-weight: bold;
        }
        QCheckBox {
            color: #CCCCCC;
            spacing: 5px;
        }
        QCheckBox::indicator {
            width: 13px;
            height: 13px;
            background-color: #181818;
            border: 1px solid #383838;
            border-radius: 2px;
        }
        QCheckBox::indicator:checked {
            background-color: #3A3A3A;
            border: 1px solid #505050;
        }
    """
    try:
        win.SetAttribute("StyleSheet", davinci_neutral_qss)
    except Exception:
        try:
            win.StyleSheet = davinci_neutral_qss
        except Exception:
            pass

    items["ThemeCombo"].AddItem("Ely")
    items["ThemeCombo"].AddItem("Aurora")

    items["ProfileCombo"].AddItem("Natural")
    items["ProfileCombo"].AddItem("Dinámico")
    items["ProfileCombo"].AddItem("Reflexivo")
    items["ProfileCombo"].AddItem("Educativo")
    items["ProfileCombo"].AddItem("Vídeo Corto")

    # Autocargar clave si existe
    if has_gemini_api_key():
        try:
            saved_k = get_gemini_api_key()
            items["ApiKeyInput"].Text = saved_k
        except Exception:
            pass

    try:
        tree = items["BlocksTree"]
        tree.ColumnCount = 6
        tree.SetHeaderLabels(["Tiempo (f)", "Capas", "Contexto", "Principal (Corregido)", "Acento", "SFX"])
        tree.ColumnWidth[0] = 85
        tree.ColumnWidth[1] = 55
        tree.ColumnWidth[2] = 110
        tree.ColumnWidth[3] = 200
        tree.ColumnWidth[4] = 100
        tree.ColumnWidth[5] = 60
    except Exception:
        pass

    current_plan: list[GenerationPlan] = []
    loaded_srt_path: list[str] = []
    cancel_flag = [False]
    is_running = [False]

    def refresh_timeline_info() -> None:
        try:
            summary = inspect_active_timeline()
            sub_cues = summary.subtitle_cues_counts.get(1, 0)
            items["HeaderInfoLabel"].Text = (
                f"Proyecto: {summary.project_name} | Línea de tiempo: {summary.timeline_name} | Pistas Subtítulos: {summary.subtitle_track_count}"
            )
            if sub_cues > 0:
                items["StatusLabel"].Text = f"✅ Detectados {sub_cues} subtítulos en Pista 1. Pulsa 'Analizar Transcripción' o 'Corregir con IA'."
            else:
                items["StatusLabel"].Text = "⚠️ Pista 1 sin subtítulos detectados. Puedes cargar un archivo .SRT o comprobar la pista."
        except Exception as err:
            items["StatusLabel"].Text = f"Aviso de conexión: {err}"

    refresh_timeline_info()

    def on_save_key(ev: Any) -> None:
        key_text = str(items["ApiKeyInput"].Text or "").strip()
        if not key_text:
            items["StatusLabel"].Text = "⚠️ La clave API no puede estar vacía."
            return
        try:
            save_gemini_api_key(key_text)
            items["StatusLabel"].Text = f"✅ Clave API guardada ({mask_api_key(key_text)})."
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

    def on_stop(ev: Any) -> None:
        cancel_flag[0] = True
        items["StatusLabel"].Text = "⏹️ Cancelación solicitada... Deteniendo tras el bloque actual."

    def on_analyze(ev: Any) -> None:
        if is_running[0]:
            return
        cancel_flag[0] = False
        is_running[0] = True
        items["AnalyzeBtn"].Enabled = False
        items["AiCorrectBtn"].Enabled = False
        items["GenerateBtn"].Enabled = False
        items["StopBtn"].Enabled = True

        track = int(items["TrackSpin"].Value)
        theme_name = "ely" if int(items["ThemeCombo"].CurrentIndex) == 0 else "aurora"
        prof_map = {0: "natural", 1: "dinamico", 2: "reflexivo", 3: "educativo", 4: "video_corto"}
        profile_name = prof_map.get(int(items["ProfileCombo"].CurrentIndex), "natural")
        enable_sfx = bool(items["SFXCheck"].Checked)
        use_ai = bool(items["CorrectAiCheck"].Checked)
        script_text = str(items["ScriptTextEdit"].PlainText or "").strip()
        glossary_text = str(items["GlossaryInput"].Text or "").strip()
        glossary = parse_glossary_str(glossary_text)
        api_key = str(items["ApiKeyInput"].Text or "").strip() or None
        srt_file = loaded_srt_path[0] if loaded_srt_path else None

        def worker() -> None:
            try:
                items["StatusLabel"].Text = "Analizando la transcripción y preparando sus capas..."
                plan, corr = plan_active_subtitles(
                    track_index=track,
                    theme_name=theme_name,
                    profile_name=profile_name,
                    enable_sfx=enable_sfx,
                    original_script=script_text,
                    glossary=glossary,
                    api_key=api_key,
                    use_ai_correction=use_ai,
                    srt_path=srt_file,
                )
                if plan.block_count == 0:
                    items["StatusLabel"].Text = f"⚠️ La pista {track} está vacía. No contiene subtítulos."
                    items["BlocksTree"].Clear()
                    current_plan.clear()
                    return

                current_plan.clear()
                current_plan.append(plan)

                items["BlocksTree"].Clear()
                for b in plan.blocks:
                    if cancel_flag[0]:
                        break
                    it = items["BlocksTree"].NewItem()
                    it.Text[0] = f"{b.start_frame:g}-{b.end_frame:g}"
                    it.Text[1] = f"{b.layer_count} capas"
                    it.Text[2] = b.context_text or "—"
                    it.Text[3] = b.main_text
                    it.Text[4] = b.accent_text or "—"
                    it.Text[5] = b.sfx_proposal or "—"
                    items["BlocksTree"].AddTopLevelItem(it)

                corr_msg = f" (IA: {corr.total_corrections} corregidos, {corr.total_markers} marcadores)" if corr and (corr.total_corrections > 0 or corr.total_markers > 0) else ""
                items["StatusLabel"].Text = f"✅ Plan listo: {plan.block_count} bloques clasificados{corr_msg}."
            except Exception as err:
                items["StatusLabel"].Text = f"❌ Error: {err}"
            finally:
                is_running[0] = False
                items["AnalyzeBtn"].Enabled = True
                items["AiCorrectBtn"].Enabled = True
                items["GenerateBtn"].Enabled = True
                items["StopBtn"].Enabled = False

        threading.Thread(target=worker, daemon=True).start()

    def on_ai_correct(ev: Any) -> None:
        items["CorrectAiCheck"].Checked = True
        on_analyze(ev)

    def on_generate(ev: Any) -> None:
        if is_running[0]:
            return
        cancel_flag[0] = False
        is_running[0] = True

        track = int(items["TrackSpin"].Value)
        theme_name = "ely" if int(items["ThemeCombo"].CurrentIndex) == 0 else "aurora"
        prof_map = {0: "natural", 1: "dinamico", 2: "reflexivo", 3: "educativo", 4: "video_corto"}
        profile_name = prof_map.get(int(items["ProfileCombo"].CurrentIndex), "natural")
        enable_sfx = bool(items["SFXCheck"].Checked)
        dry_run = bool(items["DryRunCheck"].Checked)
        use_ai = bool(items["CorrectAiCheck"].Checked)
        add_markers = bool(items["MarkersAiCheck"].Checked)
        script_text = str(items["ScriptTextEdit"].PlainText or "").strip()
        glossary_text = str(items["GlossaryInput"].Text or "").strip()
        glossary = parse_glossary_str(glossary_text)
        api_key = str(items["ApiKeyInput"].Text or "").strip() or None
        srt_file = loaded_srt_path[0] if loaded_srt_path else None

        items["AnalyzeBtn"].Enabled = False
        items["AiCorrectBtn"].Enabled = False
        items["GenerateBtn"].Enabled = False
        items["StopBtn"].Enabled = True

        def worker() -> None:
            try:
                def progress_cb(curr: int, total: int, msg: str) -> None:
                    items["StatusLabel"].Text = msg

                items["StatusLabel"].Text = "Iniciando generación en línea de tiempo..."
                record = generate_from_active_timeline(
                    track_index=track,
                    theme_name=theme_name,
                    profile_name=profile_name,
                    enable_sfx=enable_sfx,
                    dry_run=dry_run,
                    original_script=script_text,
                    glossary=glossary,
                    api_key=api_key,
                    use_ai_correction=use_ai,
                    insert_markers=add_markers,
                    srt_path=srt_file,
                    progress_callback=progress_cb,
                    is_cancelled=lambda: cancel_flag[0],
                )
                if record.status == "cancelled":
                    items["StatusLabel"].Text = f"⏹️ Generación detenida ({record.item_count} clips creados)."
                else:
                    if dry_run:
                        items["StatusLabel"].Text = f"🔎 Análisis completado: {record.item_count} elementos planificados; Resolve no fue modificado."
                    else:
                        items["StatusLabel"].Text = f"🎉 Generación completada: {record.item_count} clips creados y verificados en Resolve."
            except Exception as err:
                items["StatusLabel"].Text = f"❌ Error: {err}"
            finally:
                is_running[0] = False
                items["AnalyzeBtn"].Enabled = True
                items["AiCorrectBtn"].Enabled = True
                items["GenerateBtn"].Enabled = True
                items["StopBtn"].Enabled = False

        threading.Thread(target=worker, daemon=True).start()

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
        items["StatusLabel"].Text = "DaVinci Flow v0.1.0 • biglexj | Donaciones: https://www.biglexj.com/donaciones"

    def on_close(ev: Any) -> None:
        cancel_flag[0] = True
        dispatcher.ExitLoop()

    win.On.ReadTimelineBtn.Clicked = lambda ev: (loaded_srt_path.clear(), refresh_timeline_info(), on_analyze(ev))
    win.On.LoadSrtBtn.Clicked = on_load_srt
    win.On.LoadScriptBtn.Clicked = on_load_script
    win.On.SaveKeyBtn.Clicked = on_save_key
    win.On.AnalyzeBtn.Clicked = on_analyze
    win.On.AiCorrectBtn.Clicked = on_ai_correct
    win.On.GenerateBtn.Clicked = on_generate
    win.On.RevertBtn.Clicked = on_revert
    win.On.StopBtn.Clicked = on_stop
    win.On.AboutBtn.Clicked = on_about
    win.On.CloseBtn.Clicked = on_close
    win.On.DaVinciFlowWinV5.Close = on_close

    win.Show()
    dispatcher.RunLoop()
    win.Hide()
    return True


def _create_tkinter_window() -> None:
    """Crea una ventana gráfica dark-mode usando Tkinter con la paleta neutra de DaVinci."""
    root = tk.Tk()
    root.title("DaVinci Flow — Subtítulos Dinámicos, Guion & Asistente IA")
    root.geometry("920x715+480+50")
    root.minsize(840, 580)
    root.configure(bg="#202020")

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background="#202020", foreground="#CCCCCC", font=("Segoe UI", 10))
    style.configure("TLabel", background="#202020", foreground="#CCCCCC")
    style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), foreground="#E0E0E0")
    style.configure("SubHeader.TLabel", font=("Segoe UI", 9), foreground="#888888")
    style.configure("TButton", font=("Segoe UI", 9, "bold"), background="#2B2B2B", foreground="#D6D6D6", borderwidth=1)
    style.map("TButton", background=[("active", "#383838")])
    style.configure("Accent.TButton", background="#353535", foreground="#FFFFFF")
    style.map("Accent.TButton", background=[("active", "#454545")])
    style.configure("Ai.TButton", background="#303030", foreground="#FFFFFF")
    style.map("Ai.TButton", background=[("active", "#404040")])
    style.configure("Stop.TButton", background="#3A2828", foreground="#FF9999")
    style.map("Stop.TButton", background=[("active", "#4D3030")])
    style.configure("TNotebook", background="#202020", tabmargins=[2, 5, 2, 0])
    style.configure("TNotebook.Tab", background="#282828", foreground="#888888", padding=[12, 5], font=("Segoe UI", 9, "bold"))
    style.map("TNotebook.Tab", background=[("selected", "#383838")], foreground=[("selected", "#FFFFFF")])
    style.configure("Treeview", background="#181818", foreground="#CCCCCC", fieldbackground="#181818", rowheight=24)
    style.configure("Treeview.Heading", background="#262626", foreground="#999999", font=("Segoe UI", 9, "bold"))

    header_frame = tk.Frame(root, bg="#202020")
    header_frame.pack(fill="x", padx=14, pady=(8, 2))
    ttk.Label(header_frame, text="DaVinci Flow", style="Header.TLabel").pack()
    header_info = ttk.Label(header_frame, text="Subtítulos Dinámicos, Guion & Asistente IA • biglexj (2026)", style="SubHeader.TLabel")
    header_info.pack()

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=14, pady=4)

    # Pestaña 1: Generación & Subtítulos
    tab_gen = tk.Frame(notebook, bg="#202020")
    notebook.add(tab_gen, text="🎬 Subtítulos & Generación")

    ctrl_frame = tk.Frame(tab_gen, bg="#262626", padx=10, pady=8)
    ctrl_frame.pack(fill="x", padx=2, pady=4)

    ttk.Label(ctrl_frame, text="Pista:").grid(row=0, column=0, padx=3, pady=3, sticky="w")
    track_var = tk.IntVar(value=1)
    track_spin = ttk.Spinbox(ctrl_frame, from_=1, to=16, textvariable=track_var, width=4)
    track_spin.grid(row=0, column=1, padx=3, pady=3)

    ttk.Label(ctrl_frame, text="Tema:").grid(row=0, column=2, padx=3, pady=3, sticky="w")
    theme_var = tk.StringVar(value="ely")
    theme_combo = ttk.Combobox(ctrl_frame, textvariable=theme_var, values=["ely", "aurora"], width=7, state="readonly")
    theme_combo.grid(row=0, column=3, padx=3, pady=3)

    ttk.Label(ctrl_frame, text="Perfil:").grid(row=0, column=4, padx=3, pady=3, sticky="w")
    profile_var = tk.StringVar(value="natural")
    profile_combo = ttk.Combobox(ctrl_frame, textvariable=profile_var, values=["natural", "dinamico", "reflexivo", "educativo", "video_corto"], width=10, state="readonly")
    profile_combo.grid(row=0, column=5, padx=3, pady=3)

    sfx_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(ctrl_frame, text="SFX", variable=sfx_var).grid(row=0, column=6, padx=4, pady=3)

    dry_run_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(ctrl_frame, text="Dry-Run", variable=dry_run_var).grid(row=0, column=7, padx=4, pady=3)

    correct_ai_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(ctrl_frame, text="✨ Guion/IA", variable=correct_ai_var).grid(row=0, column=8, padx=4, pady=3)

    markers_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(ctrl_frame, text="🎯 Marcadores", variable=markers_var).grid(row=0, column=9, padx=4, pady=3)

    # Sub-fila de botones de importación
    import_row = tk.Frame(ctrl_frame, bg="#262626")
    import_row.grid(row=1, column=0, columnspan=10, pady=(6, 2), sticky="w")

    loaded_srt_tk: list[str] = []

    def choose_srt() -> None:
        f = filedialog.askopenfilename(
            title="Seleccionar subtítulo SRT",
            filetypes=[("Archivos SRT", "*.srt"), ("Todos los archivos", "*.*")],
        )
        if f:
            loaded_srt_tk.clear()
            loaded_srt_tk.append(f)
            status_label.config(text=f"📂 Transcripción SRT: {Path(f).name}. Pulsa 'Analizar Transcripción'.")
            do_analyze()

    ttk.Button(import_row, text="📂 Cargar archivo .SRT...", command=choose_srt, style="TButton").pack(side="left", padx=(0, 6))

    def reset_timeline() -> None:
        loaded_srt_tk.clear()
        try:
            summary = inspect_active_timeline()
            c_count = summary.subtitle_cues_counts.get(1, 0)
            status_label.config(text=f"🎬 Pista Resolve re-leída: {c_count} subtítulos detectados.")
        except Exception as e:
            status_label.config(text=f"Aviso: {e}")
        do_analyze()

    ttk.Button(import_row, text="🎬 Leer Pista Resolve", command=reset_timeline, style="TButton").pack(side="left", padx=6)

    btn_frame = tk.Frame(tab_gen, bg="#202020")
    btn_frame.pack(fill="x", padx=4, pady=4)

    tree_frame = tk.Frame(tab_gen, bg="#202020")
    tree_frame.pack(fill="both", expand=True, padx=4, pady=4)

    columns = ("time", "layers", "context", "main", "accent", "sfx")
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
    tree.heading("time", text="Tiempo (f)")
    tree.heading("layers", text="Capas")
    tree.heading("context", text="Contexto")
    tree.heading("main", text="Principal (Corregido)")
    tree.heading("accent", text="Acento")
    tree.heading("sfx", text="SFX")

    tree.column("time", width=85, anchor="center")
    tree.column("layers", width=55, anchor="center")
    tree.column("context", width=110)
    tree.column("main", width=200)
    tree.column("accent", width=100)
    tree.column("sfx", width=60, anchor="center")

    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Pestaña 2: Guion Original & Asistente Gemini
    tab_ai = tk.Frame(notebook, bg="#202020", padx=10, pady=10)
    notebook.add(tab_ai, text="✨ Guion & Asistente Gemini")

    ai_creds_frame = tk.Frame(tab_ai, bg="#262626", padx=12, pady=8)
    ai_creds_frame.pack(fill="x", pady=(0, 8))

    ttk.Label(ai_creds_frame, text="API Key Gemini:").grid(row=0, column=0, padx=4, pady=4, sticky="w")
    api_key_var = tk.StringVar()
    if has_gemini_api_key():
        try:
            api_key_var.set(get_gemini_api_key())
        except Exception:
            pass
    api_key_entry = ttk.Entry(ai_creds_frame, textvariable=api_key_var, show="*", width=32)
    api_key_entry.grid(row=0, column=1, padx=4, pady=4, sticky="w")

    def save_key_action() -> None:
        k = api_key_var.get().strip()
        if not k:
            messagebox.showwarning("Aviso", "Ingresa una clave API válida.")
            return
        try:
            save_gemini_api_key(k)
            messagebox.showinfo("Éxito", f"Clave API guardada ({mask_api_key(k)}).")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")

    ttk.Button(ai_creds_frame, text="💾 Guardar Clave", command=save_key_action, style="TButton").grid(row=0, column=2, padx=6, pady=4)

    ttk.Label(ai_creds_frame, text="Glosario / Jergas:").grid(row=1, column=0, padx=4, pady=4, sticky="w")
    glossary_var = tk.StringVar()
    glossary_entry = ttk.Entry(ai_creds_frame, textvariable=glossary_var, width=50)
    glossary_entry.grid(row=1, column=1, columnspan=2, padx=4, pady=4, sticky="w")

    script_label_frame = tk.Frame(tab_ai, bg="#202020")
    script_label_frame.pack(fill="x", pady=(6, 2))
    ttk.Label(script_label_frame, text="Guion Original:").pack(side="left")

    def choose_script() -> None:
        f = filedialog.askopenfilename(
            title="Seleccionar archivo de guion",
            filetypes=[("Archivos de texto", "*.txt;*.md"), ("Todos los archivos", "*.*")],
        )
        if f:
            content = Path(f).read_text(encoding="utf-8", errors="ignore")
            script_text_area.delete("1.0", "end")
            script_text_area.insert("1.0", content)
            status_label.config(text=f"📄 Guion cargado: {Path(f).name} ({len(content.splitlines())} líneas).")

    ttk.Button(script_label_frame, text="📄 Cargar Guion .txt", command=choose_script, style="TButton").pack(side="left", padx=8)

    script_text_area = tk.Text(tab_ai, bg="#181818", fg="#E0E0E0", insertbackground="#CCCCCC", font=("Consolas", 10), height=12)
    script_text_area.pack(fill="both", expand=True, pady=4)

    status_label = ttk.Label(root, text="Inspeccionando línea de tiempo...", style="SubHeader.TLabel")
    status_label.pack(fill="x", padx=14, pady=4)

    cancel_flag_tk = [False]
    current_plan_tk: list[GenerationPlan] = []

    try:
        summary = inspect_active_timeline()
        header_info.config(text=f"Proyecto: {summary.project_name} | Línea de tiempo: {summary.timeline_name}")
        c_count = summary.subtitle_cues_counts.get(1, 0)
        if c_count > 0:
            status_label.config(text=f"✅ Detectados {c_count} subtítulos en Pista 1. Pulsa 'Analizar Transcripción'.")
        else:
            status_label.config(text="⚠️ No se encontraron subtítulos en la pista 1. Puedes cargar un archivo .SRT.")
    except Exception as err:
        status_label.config(text=f"Listo para conectar ({err})")

    def do_analyze() -> None:
        status_label.config(text="Analizando la transcripción y preparando sus capas...")
        root.update_idletasks()
        try:
            script_val = script_text_area.get("1.0", "end-1c").strip()
            gloss_val = parse_glossary_str(glossary_var.get())
            key_val = api_key_var.get().strip() or None
            use_ai_val = correct_ai_var.get() or bool(script_val or gloss_val)
            srt_f = loaded_srt_tk[0] if loaded_srt_tk else None

            plan, corr = plan_active_subtitles(
                track_index=track_var.get(),
                theme_name=theme_var.get(),
                profile_name=profile_var.get(),
                enable_sfx=sfx_var.get(),
                original_script=script_val,
                glossary=gloss_val,
                api_key=key_val,
                use_ai_correction=use_ai_val,
                srt_path=srt_f,
            )
            if plan.block_count == 0:
                status_label.config(text=f"⚠️ La pista {track_var.get()} no contiene subtítulos.")
                tree.delete(*tree.get_children())
                current_plan_tk.clear()
                return

            current_plan_tk.clear()
            current_plan_tk.append(plan)
            tree.delete(*tree.get_children())
            for b in plan.blocks:
                tree.insert("", "end", values=(
                    f"{b.start_frame:g}-{b.end_frame:g}",
                    f"{b.layer_count} capas",
                    b.context_text or "—",
                    b.main_text,
                    b.accent_text or "—",
                    b.sfx_proposal or "—",
                ))
            corr_txt = f" ({corr.total_corrections} correcciones IA, {corr.total_markers} marcadores)" if corr and (corr.total_corrections > 0 or corr.total_markers > 0) else ""
            status_label.config(text=f"✅ Plan listo: {plan.block_count} bloques clasificados{corr_txt}.")
        except DaVinciFlowError as err:
            status_label.config(text=f"❌ Error: {err}")

    def do_ai_correct_action() -> None:
        correct_ai_var.set(True)
        notebook.select(tab_gen)
        do_analyze()

    ttk.Button(ai_creds_frame, text="✨ Analizar & Corregir con IA", command=do_ai_correct_action, style="Ai.TButton").grid(row=0, column=3, rowspan=2, padx=6, pady=4)

    def do_stop() -> None:
        cancel_flag_tk[0] = True
        status_label.config(text="⏹️ Cancelación solicitada...")

    def do_generate() -> None:
        cancel_flag_tk[0] = False
        track = track_var.get()
        is_dry = dry_run_var.get()
        script_val = script_text_area.get("1.0", "end-1c").strip()
        gloss_val = parse_glossary_str(glossary_var.get())
        key_val = api_key_var.get().strip() or None
        use_ai_val = correct_ai_var.get()
        add_markers_val = markers_var.get()
        srt_f = loaded_srt_tk[0] if loaded_srt_tk else None

        status_label.config(text="Generando elementos en DaVinci Resolve...")
        root.update_idletasks()

        def progress_cb(c: int, tot: int, msg: str) -> None:
            status_label.config(text=msg)
            root.update_idletasks()

        def worker_gen() -> None:
            try:
                record = generate_from_active_timeline(
                    track_index=track,
                    theme_name=theme_var.get(),
                    profile_name=profile_var.get(),
                    enable_sfx=sfx_var.get(),
                    dry_run=is_dry,
                    original_script=script_val,
                    glossary=gloss_val,
                    api_key=key_val,
                    use_ai_correction=use_ai_val,
                    insert_markers=add_markers_val,
                    srt_path=srt_f,
                    progress_callback=progress_cb,
                    is_cancelled=lambda: cancel_flag_tk[0],
                )
                if record.status == "cancelled":
                    status_label.config(text=f"⏹️ Generación cancelada por el usuario ({record.item_count} clips creados).")
                else:
                    if is_dry:
                        status_label.config(text=f"🔎 Análisis completado: {record.item_count} elementos planificados; Resolve no fue modificado.")
                    else:
                        status_label.config(text=f"🎉 Generación completada: {record.item_count} clips creados y verificados.")
            except DaVinciFlowError as err:
                status_label.config(text=f"❌ Error: {err}")

        threading.Thread(target=worker_gen, daemon=True).start()

    def do_revert() -> None:
        status_label.config(text="Eliminando clips generados en pistas de DaVinci Flow...")
        root.update_idletasks()
        try:
            from davinci_flow.application import revert_active_generation
            removed = revert_active_generation()
            status_label.config(text=f"🔄 Deshacer completado: {removed} clips de la última generación eliminados.")
        except Exception as err:
            status_label.config(text=f"❌ Error al deshacer: {err}")

    ttk.Button(btn_frame, text="🔍 Analizar Transcripción", command=do_analyze, style="TButton").pack(side="left", padx=(0, 6))
    ttk.Button(btn_frame, text="⚡ Generar en Línea de Tiempo", command=do_generate, style="Accent.TButton").pack(side="left", padx=6)
    ttk.Button(btn_frame, text="🔄 Deshacer", command=do_revert, style="TButton").pack(side="left", padx=6)
    ttk.Button(btn_frame, text="⏹️ Detener", command=do_stop, style="Stop.TButton").pack(side="left", padx=6)

    root.mainloop()


def open_davinci_flow_ui(
    resolve_app: Any = None,
    fusion_app: Any = None,
    bmd_module: Any = None,
) -> None:
    """Punto de entrada universal: intenta UIManager de Resolve y si no está disponible abre la GUI de respaldo."""
    success = False
    try:
        success = _try_create_uimanager_window(
            resolve_app=resolve_app,
            fusion_app=fusion_app,
            bmd_module=bmd_module,
        )
    except Exception as err:
        print(f"Aviso: No se pudo iniciar UIManager ({err}). Abriendo GUI nativa...", file=sys.stderr)
        success = False

    if not success:
        _create_tkinter_window()
