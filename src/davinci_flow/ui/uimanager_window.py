"""Interfaz gráfica de DaVinci Flow no bloqueante (Multihilo con soporte de parada inmediata)."""

import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Any

from davinci_flow.application import (
    generate_from_active_timeline,
    inspect_active_timeline,
    plan_active_subtitles,
)
from davinci_flow.errors import DaVinciFlowError
from davinci_flow.generation.plan import GenerationPlan


def _try_create_uimanager_window(
    resolve_app: Any = None,
    fusion_app: Any = None,
    bmd_module: Any = None,
) -> bool:
    """Crea la ventana nativa mediante UIManager de Resolve con ejecución en hilo secundario."""
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
            "WindowTitle": "DaVinci Flow — Subtítulos Dinámicos & SFX",
            "ID": "DaVinciFlowWin",
            "Geometry": [300, 160, 740, 540],
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
                                    "Text": "<b>DaVinci Flow</b> — Subtítulos Dinámicos Multicapa & SFX",
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
                    ui.HGroup(
                        {"Spacing": 16, "Weight": 0},
                        [
                            ui.CheckBox({"ID": "SFXCheck", "Text": "Generar efectos sonoros (SFX)", "Checked": True, "Weight": 0}),
                            ui.CheckBox({"ID": "DryRunCheck", "Text": "Modo Simulación (Dry-Run)", "Checked": False, "Weight": 0}),
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
                                    "FixedSize": [140, 26],
                                    "Weight": 0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "GenerateBtn",
                                    "Text": "⚡ Generar en Línea de Tiempo",
                                    "FixedSize": [190, 26],
                                    "Weight": 0,
                                }
                            ),
                            ui.Button(
                                {
                                    "ID": "RevertBtn",
                                    "Text": "🔄 Deshacer",
                                    "FixedSize": [115, 26],
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

    try:
        tree = items["BlocksTree"]
        tree.SetHeaderLabels(["Tiempo (f)", "Capas", "Contexto", "Principal", "Acento", "SFX"])
        tree.ColumnWidth[0] = 85
        tree.ColumnWidth[1] = 65
        tree.ColumnWidth[2] = 120
        tree.ColumnWidth[3] = 210
        tree.ColumnWidth[4] = 120
        tree.ColumnWidth[5] = 90
    except Exception:
        pass

    current_plan: list[GenerationPlan] = []
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
            items["StatusLabel"].Text = f"✅ Detectados {sub_cues} subtítulos en Pista 1. Pulsa 'Analizar Capas'."
    except Exception as err:
        items["StatusLabel"].Text = f"Aviso: {err}"

    def on_stop(ev: Any) -> None:
        cancel_flag[0] = True
        items["StatusLabel"].Text = "⏹️ Cancelación solicitada... Deteniendo tras el bloque actual."

    def on_analyze(ev: Any) -> None:
        if is_running[0]:
            return
        cancel_flag[0] = False
        is_running[0] = True
        items["AnalyzeBtn"].Enabled = False
        items["GenerateBtn"].Enabled = False
        items["StopBtn"].Enabled = True

        track = int(items["TrackSpin"].Value)
        theme_name = "ely" if int(items["ThemeCombo"].CurrentIndex) == 0 else "aurora"
        prof_map = {0: "natural", 1: "dinamico", 2: "reflexivo", 3: "educativo", 4: "video_corto"}
        profile_name = prof_map.get(int(items["ProfileCombo"].CurrentIndex), "natural")
        enable_sfx = bool(items["SFXCheck"].Checked)

        def worker() -> None:
            try:
                items["StatusLabel"].Text = "Analizando subtítulos..."
                plan = plan_active_subtitles(track, theme_name, profile_name, enable_sfx)
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

                items["StatusLabel"].Text = f"✅ Plan listo: {plan.block_count} bloques clasificados."
            except Exception as err:
                items["StatusLabel"].Text = f"❌ Error: {err}"
            finally:
                is_running[0] = False
                items["AnalyzeBtn"].Enabled = True
                items["GenerateBtn"].Enabled = True
                items["StopBtn"].Enabled = False

        threading.Thread(target=worker, daemon=True).start()

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

        items["AnalyzeBtn"].Enabled = False
        items["GenerateBtn"].Enabled = False
        items["StopBtn"].Enabled = True

        def worker() -> None:
            try:
                if not current_plan or current_plan[0].block_count == 0:
                    plan = plan_active_subtitles(track, theme_name, profile_name, enable_sfx)
                    if plan.block_count == 0:
                        items["StatusLabel"].Text = f"⚠️ La pista {track} está vacía. No hay subtítulos para generar."
                        return
                    current_plan.clear()
                    current_plan.append(plan)

                def progress_cb(curr: int, total: int, msg: str) -> None:
                    items["StatusLabel"].Text = msg

                items["StatusLabel"].Text = f"Generando {current_plan[0].block_count} bloques..."
                record = generate_from_active_timeline(
                    track_index=track,
                    theme_name=theme_name,
                    profile_name=profile_name,
                    enable_sfx=enable_sfx,
                    dry_run=dry_run,
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

    win.On.AnalyzeBtn.Clicked = on_analyze
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
    """Crea una ventana gráfica dark-mode usando Tkinter como respaldo garantizado."""
    root = tk.Tk()
    root.title("DaVinci Flow — Subtítulos Dinámicos & SFX")
    root.geometry("820x620")
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
    style.configure("Stop.TButton", background="#EF4444", foreground="#FFFFFF")
    style.map("Stop.TButton", background=[("active", "#DC2626")])
    style.configure("Treeview", background="#1E293B", foreground="#F8FAFC", fieldbackground="#1E293B", rowheight=26)
    style.configure("Treeview.Heading", background="#334155", foreground="#38BDF8", font=("Segoe UI", 10, "bold"))

    header_frame = tk.Frame(root, bg="#0F172A")
    header_frame.pack(fill="x", padx=16, pady=(12, 6))
    ttk.Label(header_frame, text="DaVinci Flow", style="Header.TLabel").pack()
    header_info = ttk.Label(header_frame, text="Subtítulos Dinámicos Multicapa & SFX • biglexj (2026)", style="SubHeader.TLabel")
    header_info.pack()

    ctrl_frame = tk.Frame(root, bg="#1E293B", padx=12, pady=10)
    ctrl_frame.pack(fill="x", padx=16, pady=8)

    ttk.Label(ctrl_frame, text="Pista:").grid(row=0, column=0, padx=6, pady=4, sticky="w")
    track_var = tk.IntVar(value=1)
    track_spin = ttk.Spinbox(ctrl_frame, from_=1, to=16, textvariable=track_var, width=5)
    track_spin.grid(row=0, column=1, padx=6, pady=4)

    ttk.Label(ctrl_frame, text="Tema:").grid(row=0, column=2, padx=6, pady=4, sticky="w")
    theme_var = tk.StringVar(value="ely")
    theme_combo = ttk.Combobox(ctrl_frame, textvariable=theme_var, values=["ely", "aurora"], width=10, state="readonly")
    theme_combo.grid(row=0, column=3, padx=6, pady=4)

    ttk.Label(ctrl_frame, text="Perfil:").grid(row=0, column=4, padx=6, pady=4, sticky="w")
    profile_var = tk.StringVar(value="natural")
    profile_combo = ttk.Combobox(ctrl_frame, textvariable=profile_var, values=["natural", "dinamico", "reflexivo", "educativo", "video_corto"], width=12, state="readonly")
    profile_combo.grid(row=0, column=5, padx=6, pady=4)

    sfx_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(ctrl_frame, text="Efectos SFX", variable=sfx_var).grid(row=0, column=6, padx=10, pady=4)

    dry_run_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(ctrl_frame, text="Simulación (Dry-Run)", variable=dry_run_var).grid(row=0, column=7, padx=10, pady=4)

    btn_frame = tk.Frame(root, bg="#0F172A")
    btn_frame.pack(fill="x", padx=16, pady=4)

    tree_frame = tk.Frame(root, bg="#0F172A")
    tree_frame.pack(fill="both", expand=True, padx=16, pady=6)

    columns = ("time", "layers", "context", "main", "accent", "sfx")
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
    tree.heading("time", text="Tiempo (f)")
    tree.heading("layers", text="Capas")
    tree.heading("context", text="Contexto")
    tree.heading("main", text="Principal")
    tree.heading("accent", text="Acento")
    tree.heading("sfx", text="SFX")

    tree.column("time", width=90, anchor="center")
    tree.column("layers", width=70, anchor="center")
    tree.column("context", width=140)
    tree.column("main", width=220)
    tree.column("accent", width=140)
    tree.column("sfx", width=110, anchor="center")

    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

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
        status_label.config(text="Analizando subtítulos de la línea de tiempo activa...")
        root.update_idletasks()
        try:
            plan = plan_active_subtitles(
                track_index=track_var.get(),
                theme_name=theme_var.get(),
                profile_name=profile_var.get(),
                enable_sfx=sfx_var.get(),
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
            status_label.config(text=f"✅ Plan listo: {plan.block_count} bloques clasificados.")
        except DaVinciFlowError as err:
            status_label.config(text=f"❌ Error: {err}")

    def do_stop() -> None:
        cancel_flag_tk[0] = True
        status_label.config(text="⏹️ Cancelación solicitada...")

    def do_generate() -> None:
        cancel_flag_tk[0] = False
        track = track_var.get()
        if not current_plan_tk or current_plan_tk[0].block_count == 0:
            try:
                plan = plan_active_subtitles(track, theme_var.get(), profile_var.get(), sfx_var.get())
                if plan.block_count == 0:
                    status_label.config(text=f"⚠️ La pista {track} está vacía. No hay subtítulos para generar.")
                    return
                current_plan_tk.clear()
                current_plan_tk.append(plan)
            except Exception as err:
                status_label.config(text=f"⚠️ Error: {err}")
                return

        is_dry = dry_run_var.get()
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

    ttk.Button(btn_frame, text="🔍 Analizar Capas", command=do_analyze, style="TButton").pack(side="left", padx=(0, 8))
    ttk.Button(btn_frame, text="⚡ Generar en Línea de Tiempo", command=do_generate, style="Accent.TButton").pack(side="left", padx=8)
    ttk.Button(btn_frame, text="🔄 Deshacer", command=do_revert, style="TButton").pack(side="left", padx=8)
    ttk.Button(btn_frame, text="⏹️ Detener", command=do_stop, style="Stop.TButton").pack(side="left", padx=8)

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
