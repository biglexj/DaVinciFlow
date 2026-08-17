"""Interfaz gráfica de DaVinci Flow no bloqueante con soporte para Guion, Corrección IA y Marcadores."""

import json
import re
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
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
)
from davinci_flow.errors import DaVinciFlowError
from davinci_flow.generation.plan import GenerationPlan


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
    """Crea la ventana nativa mediante UIManager de Resolve."""
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

    win = dispatcher.AddWindow(
        {
            "WindowTitle": "DaVinci Flow — Subtítulos Dinámicos, Guion & IA",
            "ID": "DaVinciFlowWin",
            "Geometry": [250, 100, 800, 660],
            "Margin": 10,
            "Spacing": 6,
        },
        [
            ui.VGroup(
                {"Spacing": 6, "Margin": 0},
                [
                    ui.VGroup(
                        {"Spacing": 1, "Weight": 0},
                        [
                            ui.Label(
                                {
                                    "Text": "<b>DaVinci Flow</b> — Subtítulos Dinámicos, Guion & Asistente IA",
                                    "Alignment": {"AlignHCenter": True},
                                    "Font": ui.Font({"PixelSize": 13, "Bold": True}),
                                    "Weight": 0,
                                }
                            ),
                            ui.Label(
                                {
                                    "ID": "HeaderInfoLabel",
                                    "Text": "<font color='#888888'>Autor: biglexj | Licencia: MIT</font>",
                                    "Alignment": {"AlignHCenter": True},
                                    "Font": ui.Font({"PixelSize": 10}),
                                    "Weight": 0,
                                }
                            ),
                        ],
                    ),
                    ui.VGap(2),
                    ui.HGroup(
                        {"Spacing": 8, "Weight": 0},
                        [
                            ui.Label({"Text": "Pista Subtítulos:", "Weight": 0}),
                            ui.SpinBox(
                                {
                                    "ID": "TrackSpin",
                                    "Value": 1,
                                    "Minimum": 1,
                                    "Maximum": 16,
                                    "FixedSize": [54, 24],
                                    "Weight": 0,
                                }
                            ),
                            ui.HGap(8),
                            ui.Label({"Text": "Tema:", "Weight": 0}),
                            ui.ComboBox(
                                {
                                    "ID": "ThemeCombo",
                                    "FixedSize": [95, 24],
                                    "Weight": 0,
                                }
                            ),
                            ui.HGap(8),
                            ui.Label({"Text": "Perfil:", "Weight": 0}),
                            ui.ComboBox(
                                {
                                    "ID": "ProfileCombo",
                                    "FixedSize": [115, 24],
                                    "Weight": 0,
                                }
                            ),
                            ui.HGap(1),
                        ]
                    ),
                    # Sección Asistente Gemini y Guion
                    ui.VGroup(
                        {"Spacing": 4, "Margin": 0, "Weight": 0},
                        [
                            ui.HGroup(
                                {"Spacing": 6, "Weight": 0},
                                [
                                    ui.Label({"Text": "API Key Gemini:", "Weight": 0}),
                                    ui.LineEdit(
                                        {
                                            "ID": "ApiKeyInput",
                                            "PlaceholderText": "Clave API Gemini (o variable GEMINI_API_KEY)",
                                            "EchoMode": "Password",
                                            "Weight": 1.0,
                                        }
                                    ),
                                    ui.Button(
                                        {
                                            "ID": "SaveKeyBtn",
                                            "Text": "💾 Guardar",
                                            "FixedSize": [75, 24],
                                            "Weight": 0,
                                        }
                                    ),
                                ]
                            ),
                            ui.HGroup(
                                {"Spacing": 6, "Weight": 0},
                                [
                                    ui.Label({"Text": "Glosario/Marcas:", "Weight": 0}),
                                    ui.LineEdit(
                                        {
                                            "ID": "GlossaryInput",
                                            "PlaceholderText": "Reemplazos fijos (ej. biglex: Biglex J, resolve: DaVinci)",
                                            "Weight": 1.0,
                                        }
                                    ),
                                ]
                            ),
                            ui.TextEdit(
                                {
                                    "ID": "ScriptTextEdit",
                                    "PlaceholderText": "Pega aquí el guion original completo para comparar y corregir los subtítulos...",
                                    "FixedSize": [770, 70],
                                    "Weight": 0,
                                }
                            ),
                        ]
                    ),
                    ui.HGroup(
                        {"Spacing": 16, "Weight": 0},
                        [
                            ui.CheckBox({"ID": "SFXCheck", "Text": "Efectos SFX", "Checked": True, "Weight": 0}),
                            ui.CheckBox({"ID": "DryRunCheck", "Text": "Modo Simulación (Dry-Run)", "Checked": False, "Weight": 0}),
                            ui.CheckBox({"ID": "CorrectAiCheck", "Text": "✨ Corregir con Guion (Gemini)", "Checked": False, "Weight": 0}),
                            ui.CheckBox({"ID": "MarkersAiCheck", "Text": "🎯 Marcadores en Línea de Tiempo", "Checked": False, "Weight": 0}),
                            ui.HGap(1),
                        ]
                    ),
                    ui.HGroup(
                        {"Spacing": 8, "Weight": 0},
                        [
                            ui.Button(
                                {
                                    "ID": "AnalyzeBtn",
                                    "Text": "🔍 Analizar Capas",
                                    "FixedSize": [130, 26],
                                    "Weight": 0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "AiCorrectBtn",
                                    "Text": "✨ Corregir con IA",
                                    "FixedSize": [140, 26],
                                    "Weight": 0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "GenerateBtn",
                                    "Text": "⚡ Generar en Línea de Tiempo",
                                    "FixedSize": [180, 26],
                                    "Weight": 0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "RevertBtn",
                                    "Text": "🔄 Deshacer",
                                    "FixedSize": [95, 26],
                                    "Weight": 0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "StopBtn",
                                    "Text": "⏹️ Detener",
                                    "FixedSize": [85, 26],
                                    "Weight": 0,
                                    "Enabled": False,
                                }
                            ),
                            ui.HGap(1),
                        ]
                    ),
                    ui.VGap(2),
                    ui.Tree({"ID": "BlocksTree", "Weight": 1.0}),
                    ui.Label(
                        {
                            "ID": "StatusLabel",
                            "Text": "Inspeccionando línea de tiempo...",
                            "Weight": 0,
                            "Font": ui.Font({"PixelSize": 10}),
                        }
                    ),
                    ui.HGroup(
                        {"Spacing": 8, "Weight": 0},
                        [
                            ui.Button(
                                {
                                    "ID": "AboutBtn",
                                    "Text": "ℹ️ Acerca de",
                                    "FixedSize": [95, 22],
                                    "Weight": 0,
                                }
                            ),
                            ui.HGap(1),
                            ui.Button(
                                {
                                    "ID": "CloseBtn",
                                    "Text": "Cerrar",
                                    "FixedSize": [75, 22],
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
        tree.SetHeaderLabels(["Tiempo (f)", "Capas", "Contexto", "Principal (Corregido)", "Acento", "SFX"])
        tree.ColumnWidth[0] = 85
        tree.ColumnWidth[1] = 65
        tree.ColumnWidth[2] = 120
        tree.ColumnWidth[3] = 230
        tree.ColumnWidth[4] = 120
        tree.ColumnWidth[5] = 85
    except Exception:
        pass

    current_plan: list[GenerationPlan] = []
    last_correction_result: list[CorrectionResult] = []
    cancel_flag = [False]
    is_running = [False]

    try:
        summary = inspect_active_timeline()
        sub_cues = summary.subtitle_cues_counts.get(1, 0)
        items["HeaderInfoLabel"].Text = (
            f"<font color='#94A3B8'>Proyecto: {summary.project_name} | Línea de tiempo: {summary.timeline_name}</font>"
        )
        if summary.subtitle_track_count == 0 or sub_cues == 0:
            items["StatusLabel"].Text = "⚠️ No se detectaron subtítulos en la pista 1."
        else:
            items["StatusLabel"].Text = f"✅ Detectados {sub_cues} subtítulos en Pista 1. Listo para analizar."
    except Exception as err:
        items["StatusLabel"].Text = f"Aviso: {err}"

    def on_save_key(ev: Any) -> None:
        key_text = str(items["ApiKeyInput"].Text or "").strip()
        if not key_text:
            items["StatusLabel"].Text = "⚠️ La clave API no puede estar vacía."
            return
        try:
            save_gemini_api_key(key_text)
            items["StatusLabel"].Text = f"✅ Clave API guardada con éxito ({mask_api_key(key_text)})."
        except Exception as err:
            items["StatusLabel"].Text = f"❌ Error al guardar clave: {err}"

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

        def worker() -> None:
            try:
                items["StatusLabel"].Text = "Analizando subtítulos y clasificando capas..."
                plan, corr = plan_active_subtitles(
                    track_index=track,
                    theme_name=theme_name,
                    profile_name=profile_name,
                    enable_sfx=enable_sfx,
                    original_script=script_text,
                    glossary=glossary,
                    api_key=api_key,
                    use_ai_correction=use_ai,
                )
                if plan.block_count == 0:
                    items["StatusLabel"].Text = f"⚠️ La pista {track} está vacía. No contiene subtítulos."
                    items["BlocksTree"].Clear()
                    current_plan.clear()
                    return

                current_plan.clear()
                current_plan.append(plan)
                last_correction_result.clear()
                if corr:
                    last_correction_result.append(corr)

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

                corr_msg = f" (IA: {corr.total_corrections} correcciones)" if corr and corr.total_corrections > 0 else ""
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
                    progress_callback=progress_cb,
                    is_cancelled=lambda: cancel_flag[0],
                )
                if record.status == "cancelled":
                    items["StatusLabel"].Text = f"⏹️ Generación detenida ({record.item_count} clips creados)."
                else:
                    lbl = "Simulación" if dry_run else "Generación"
                    items["StatusLabel"].Text = f"🎉 {lbl} completada: {record.item_count} clips creados."
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
        items["StatusLabel"].Text = "Eliminando clips generados en pistas de DaVinci Flow..."
        try:
            from davinci_flow.application import revert_active_generation
            count = revert_active_generation()
            items["StatusLabel"].Text = f"🔄 Deshacer completado: {count} clips eliminados de las pistas."
        except Exception as err:
            items["StatusLabel"].Text = f"❌ Error al deshacer: {err}"

    def on_about(ev: Any) -> None:
        items["StatusLabel"].Text = "DaVinci Flow v0.1.0 • biglexj | Donaciones: https://www.biglexj.com/donaciones"

    def on_close(ev: Any) -> None:
        cancel_flag[0] = True
        dispatcher.ExitLoop()

    win.On.SaveKeyBtn.Clicked = on_save_key
    win.On.AnalyzeBtn.Clicked = on_analyze
    win.On.AiCorrectBtn.Clicked = on_ai_correct
    win.On.GenerateBtn.Clicked = on_generate
    win.On.RevertBtn.Clicked = on_revert
    win.On.StopBtn.Clicked = on_stop
    win.On.AboutBtn.Clicked = on_about
    win.On.CloseBtn.Clicked = on_close
    win.On.DaVinciFlowWin.Close = on_close

    win.Show()
    dispatcher.RunLoop()
    win.Hide()
    return True


def _create_tkinter_window() -> None:
    """Crea una ventana gráfica dark-mode usando Tkinter con pestañas para Generación y Guion IA."""
    root = tk.Tk()
    root.title("DaVinci Flow — Subtítulos Dinámicos, Guion & Asistente IA")
    root.geometry("880x700")
    root.configure(bg="#0F172A")

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background="#0F172A", foreground="#F8FAFC", font=("Segoe UI", 10))
    style.configure("TLabel", background="#0F172A", foreground="#F8FAFC")
    style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#06B6D4")
    style.configure("SubHeader.TLabel", font=("Segoe UI", 9), foreground="#94A3B8")
    style.configure("TButton", font=("Segoe UI", 10, "bold"), background="#1E293B", foreground="#38BDF8", borderwidth=1)
    style.map("TButton", background=[("active", "#334155")])
    style.configure("Accent.TButton", background="#06B6D4", foreground="#0F172A")
    style.map("Accent.TButton", background=[("active", "#22D3EE")])
    style.configure("Ai.TButton", background="#8B5CF6", foreground="#FFFFFF")
    style.map("Ai.TButton", background=[("active", "#7C3AED")])
    style.configure("Stop.TButton", background="#EF4444", foreground="#FFFFFF")
    style.map("Stop.TButton", background=[("active", "#DC2626")])
    style.configure("TNotebook", background="#0F172A", tabmargins=[2, 5, 2, 0])
    style.configure("TNotebook.Tab", background="#1E293B", foreground="#94A3B8", padding=[12, 6], font=("Segoe UI", 10, "bold"))
    style.map("TNotebook.Tab", background=[("selected", "#06B6D4")], foreground=[("selected", "#0F172A")])
    style.configure("Treeview", background="#1E293B", foreground="#F8FAFC", fieldbackground="#1E293B", rowheight=26)
    style.configure("Treeview.Heading", background="#334155", foreground="#38BDF8", font=("Segoe UI", 10, "bold"))

    header_frame = tk.Frame(root, bg="#0F172A")
    header_frame.pack(fill="x", padx=16, pady=(10, 4))
    ttk.Label(header_frame, text="DaVinci Flow", style="Header.TLabel").pack()
    header_info = ttk.Label(header_frame, text="Subtítulos Dinámicos, Guion & Asistente IA • biglexj (2026)", style="SubHeader.TLabel")
    header_info.pack()

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=16, pady=6)

    # Pestaña 1: Generación & Subtítulos
    tab_gen = tk.Frame(notebook, bg="#0F172A")
    notebook.add(tab_gen, text="🎬 Subtítulos & Generación")

    ctrl_frame = tk.Frame(tab_gen, bg="#1E293B", padx=10, pady=8)
    ctrl_frame.pack(fill="x", padx=4, pady=6)

    ttk.Label(ctrl_frame, text="Pista:").grid(row=0, column=0, padx=4, pady=4, sticky="w")
    track_var = tk.IntVar(value=1)
    track_spin = ttk.Spinbox(ctrl_frame, from_=1, to=16, textvariable=track_var, width=4)
    track_spin.grid(row=0, column=1, padx=4, pady=4)

    ttk.Label(ctrl_frame, text="Tema:").grid(row=0, column=2, padx=4, pady=4, sticky="w")
    theme_var = tk.StringVar(value="ely")
    theme_combo = ttk.Combobox(ctrl_frame, textvariable=theme_var, values=["ely", "aurora"], width=8, state="readonly")
    theme_combo.grid(row=0, column=3, padx=4, pady=4)

    ttk.Label(ctrl_frame, text="Perfil:").grid(row=0, column=4, padx=4, pady=4, sticky="w")
    profile_var = tk.StringVar(value="natural")
    profile_combo = ttk.Combobox(ctrl_frame, textvariable=profile_var, values=["natural", "dinamico", "reflexivo", "educativo", "video_corto"], width=11, state="readonly")
    profile_combo.grid(row=0, column=5, padx=4, pady=4)

    sfx_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(ctrl_frame, text="SFX", variable=sfx_var).grid(row=0, column=6, padx=6, pady=4)

    dry_run_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(ctrl_frame, text="Dry-Run", variable=dry_run_var).grid(row=0, column=7, padx=6, pady=4)

    correct_ai_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(ctrl_frame, text="✨ Usar Guion/IA", variable=correct_ai_var).grid(row=0, column=8, padx=6, pady=4)

    markers_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(ctrl_frame, text="🎯 Marcadores", variable=markers_var).grid(row=0, column=9, padx=6, pady=4)

    btn_frame = tk.Frame(tab_gen, bg="#0F172A")
    btn_frame.pack(fill="x", padx=4, pady=4)

    tree_frame = tk.Frame(tab_gen, bg="#0F172A")
    tree_frame.pack(fill="both", expand=True, padx=4, pady=4)

    columns = ("time", "layers", "context", "main", "accent", "sfx")
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
    tree.heading("time", text="Tiempo (f)")
    tree.heading("layers", text="Capas")
    tree.heading("context", text="Contexto")
    tree.heading("main", text="Principal (Corregido)")
    tree.heading("accent", text="Acento")
    tree.heading("sfx", text="SFX")

    tree.column("time", width=90, anchor="center")
    tree.column("layers", width=65, anchor="center")
    tree.column("context", width=130)
    tree.column("main", width=250)
    tree.column("accent", width=130)
    tree.column("sfx", width=90, anchor="center")

    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Pestaña 2: Guion Original & Asistente Gemini
    tab_ai = tk.Frame(notebook, bg="#0F172A", padx=8, pady=8)
    notebook.add(tab_ai, text="✨ Guion & Asistente Gemini")

    ai_creds_frame = tk.Frame(tab_ai, bg="#1E293B", padx=10, pady=8)
    ai_creds_frame.pack(fill="x", pady=(0, 8))

    ttk.Label(ai_creds_frame, text="API Key Gemini:").grid(row=0, column=0, padx=4, pady=4, sticky="w")
    api_key_var = tk.StringVar()
    if has_gemini_api_key():
        try:
            api_key_var.set(get_gemini_api_key())
        except Exception:
            pass
    api_key_entry = ttk.Entry(ai_creds_frame, textvariable=api_key_var, show="*", width=38)
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
    glossary_entry = ttk.Entry(ai_creds_frame, textvariable=glossary_var, width=54)
    glossary_entry.grid(row=1, column=1, columnspan=2, padx=4, pady=4, sticky="w")

    script_label_frame = tk.Frame(tab_ai, bg="#0F172A")
    script_label_frame.pack(fill="x", pady=(4, 2))
    ttk.Label(script_label_frame, text="Guion original de referencia (pega el texto completo aquí):").pack(side="left")

    script_text_area = tk.Text(tab_ai, bg="#1E293B", fg="#F8FAFC", insertbackground="#38BDF8", font=("Consolas", 10), height=14)
    script_text_area.pack(fill="both", expand=True, pady=4)

    status_label = ttk.Label(root, text="Inspeccionando línea de tiempo...", style="SubHeader.TLabel")
    status_label.pack(fill="x", padx=16, pady=4)

    cancel_flag_tk = [False]
    current_plan_tk: list[GenerationPlan] = []

    try:
        summary = inspect_active_timeline()
        header_info.config(text=f"Proyecto: {summary.project_name} | Línea de tiempo: {summary.timeline_name}")
        c_count = summary.subtitle_cues_counts.get(1, 0)
        if c_count > 0:
            status_label.config(text=f"✅ Detectados {c_count} subtítulos en Pista 1. Pulsa 'Analizar Capas'.")
        else:
            status_label.config(text="⚠️ No se encontraron subtítulos en la pista 1.")
    except Exception as err:
        status_label.config(text=f"Listo para conectar ({err})")

    def do_analyze() -> None:
        status_label.config(text="Analizando subtítulos y clasificando capas...")
        root.update_idletasks()
        try:
            script_val = script_text_area.get("1.0", "end-1c").strip()
            gloss_val = parse_glossary_str(glossary_var.get())
            key_val = api_key_var.get().strip() or None
            use_ai_val = correct_ai_var.get() or bool(script_val or gloss_val)

            plan, corr = plan_active_subtitles(
                track_index=track_var.get(),
                theme_name=theme_var.get(),
                profile_name=profile_var.get(),
                enable_sfx=sfx_var.get(),
                original_script=script_val,
                glossary=gloss_val,
                api_key=key_val,
                use_ai_correction=use_ai_val,
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
            corr_txt = f" ({corr.total_corrections} correcciones IA)" if corr and corr.total_corrections > 0 else ""
            status_label.config(text=f"✅ Plan listo: {plan.block_count} bloques clasificados{corr_txt}.")
        except DaVinciFlowError as err:
            status_label.config(text=f"❌ Error: {err}")

    def do_ai_correct_action() -> None:
        correct_ai_var.set(True)
        notebook.select(tab_gen)
        do_analyze()

    ttk.Button(ai_creds_frame, text="✨ Analizar & Corregir con IA", command=do_ai_correct_action, style="Ai.TButton").grid(row=0, column=3, rowspan=2, padx=8, pady=4)

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
                    progress_callback=progress_cb,
                    is_cancelled=lambda: cancel_flag_tk[0],
                )
                if record.status == "cancelled":
                    status_label.config(text=f"⏹️ Generación cancelada por el usuario ({record.item_count} clips creados).")
                else:
                    mode = "Simulación" if is_dry else "Generación"
                    status_label.config(text=f"🎉 {mode} completada: {record.item_count} clips creados.")
            except DaVinciFlowError as err:
                status_label.config(text=f"❌ Error: {err}")

        threading.Thread(target=worker_gen, daemon=True).start()

    def do_revert() -> None:
        status_label.config(text="Eliminando clips generados en pistas de DaVinci Flow...")
        root.update_idletasks()
        try:
            from davinci_flow.application import revert_active_generation
            removed = revert_active_generation()
            status_label.config(text=f"🔄 Deshacer global completado: {removed} clips eliminados.")
        except Exception as err:
            status_label.config(text=f"❌ Error al deshacer: {err}")

    ttk.Button(btn_frame, text="🔍 Analizar Capas", command=do_analyze, style="TButton").pack(side="left", padx=(0, 6))
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
