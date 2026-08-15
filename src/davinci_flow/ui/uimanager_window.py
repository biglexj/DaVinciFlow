"""Interfaz gráfica de DaVinci Flow (UIManager nativo de Resolve con respaldo Tkinter)."""

import sys
import tkinter as tk
from tkinter import ttk
from typing import Any

from davinci_flow.application import (
    generate_from_active_timeline,
    plan_active_subtitles,
)
from davinci_flow.errors import DaVinciFlowError
from davinci_flow.generation.plan import GenerationPlan
from davinci_flow.generation.record import GenerationExecutionRecord


def _try_create_uimanager_window(
    resolve_app: Any = None,
    fusion_app: Any = None,
    bmd_module: Any = None,
) -> bool:
    """Intenta crear y ejecutar la ventana nativa mediante el UIManager de Resolve."""
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
            "Geometry": [200, 200, 720, 580],
        },
        [
            ui.VGroup(
                [
                    ui.Label(
                        {
                            "Text": "<b>DaVinci Flow</b> — Subtítulos Dinámicos Multicapa & SFX",
                            "Alignment": {"AlignHCenter": True},
                            "Font": ui.Font({"PixelSize": 15}),
                        }
                    ),
                    ui.Label(
                        {
                            "Text": "Autor: biglexj | Licencia: MIT",
                            "Alignment": {"AlignHCenter": True},
                        }
                    ),
                    ui.HGroup(
                        [
                            ui.Label({"Text": "Pista Subtítulos:", "Weight": 0.25}),
                            ui.SpinBox({"ID": "TrackSpin", "Value": 1, "Minimum": 1, "Maximum": 16, "Weight": 0.2}),
                            ui.Label({"Text": "Tema:", "Weight": 0.15}),
                            ui.ComboBox({"ID": "ThemeCombo", "Weight": 0.2}),
                            ui.Label({"Text": "Perfil:", "Weight": 0.15}),
                            ui.ComboBox({"ID": "ProfileCombo", "Weight": 0.25}),
                        ]
                    ),
                    ui.HGroup(
                        [
                            ui.CheckBox({"ID": "SFXCheck", "Text": "Generar efectos sonoros (SFX)", "Checked": True}),
                            ui.CheckBox({"ID": "DryRunCheck", "Text": "Modo Simulación (Dry-Run)", "Checked": False}),
                        ]
                    ),
                    ui.HGroup(
                        [
                            ui.Button({"ID": "AnalyzeBtn", "Text": "🔍 Analizar Capas"}),
                            ui.Button({"ID": "GenerateBtn", "Text": "⚡ Generar en Línea de Tiempo"}),
                        ]
                    ),
                    ui.Tree({"ID": "BlocksTree", "Weight": 1.0}),
                    ui.Label({"ID": "StatusLabel", "Text": "Listo para analizar la línea de tiempo activa."}),
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
    items["ThemeCombo"].AddItem("Ely")
    items["ThemeCombo"].AddItem("Aurora")

    items["ProfileCombo"].AddItem("Natural")
    items["ProfileCombo"].AddItem("Dinámico")
    items["ProfileCombo"].AddItem("Reflexivo")
    items["ProfileCombo"].AddItem("Educativo")
    items["ProfileCombo"].AddItem("Vídeo Corto")

    # Configurar encabezados del árbol
    try:
        items["BlocksTree"].SetHeaderLabels(["Tiempo (f)", "Capas", "Contexto", "Principal", "Acento", "SFX"])
    except Exception:
        pass

    def on_analyze(ev: Any) -> None:
        track = int(items["TrackSpin"].Value)
        theme_name = "ely" if int(items["ThemeCombo"].CurrentIndex) == 0 else "aurora"
        prof_map = {0: "natural", 1: "dinamico", 2: "reflexivo", 3: "educativo", 4: "video_corto"}
        profile_name = prof_map.get(int(items["ProfileCombo"].CurrentIndex), "natural")
        enable_sfx = bool(items["SFXCheck"].Checked)

        items["StatusLabel"].Text = "Analizando subtítulos..."
        try:
            plan = plan_active_subtitles(track, theme_name, profile_name, enable_sfx)
            items["BlocksTree"].Clear()
            for b in plan.blocks:
                it = items["BlocksTree"].NewItem()
                it.Text[0] = f"{b.start_frame:g}-{b.end_frame:g}"
                it.Text[1] = f"{b.layer_count} capas"
                it.Text[2] = b.context_text or "—"
                it.Text[3] = b.main_text
                it.Text[4] = b.accent_text or "—"
                it.Text[5] = b.sfx_proposal or "—"
                items["BlocksTree"].AddTopLevelItem(it)
            items["StatusLabel"].Text = f"✅ Plan listo: {plan.block_count} bloques clasificados."
        except DaVinciFlowError as err:
            items["StatusLabel"].Text = f"❌ Error: {err}"

    def on_generate(ev: Any) -> None:
        track = int(items["TrackSpin"].Value)
        theme_name = "ely" if int(items["ThemeCombo"].CurrentIndex) == 0 else "aurora"
        prof_map = {0: "natural", 1: "dinamico", 2: "reflexivo", 3: "educativo", 4: "video_corto"}
        profile_name = prof_map.get(int(items["ProfileCombo"].CurrentIndex), "natural")
        enable_sfx = bool(items["SFXCheck"].Checked)
        dry_run = bool(items["DryRunCheck"].Checked)

        items["StatusLabel"].Text = "Generando en Resolve..."
        try:
            record = generate_from_active_timeline(track, theme_name, profile_name, enable_sfx, dry_run)
            lbl = "Simulación" if dry_run else "Generación"
            items["StatusLabel"].Text = f"🎉 {lbl} completada: {record.item_count} clips creados."
        except DaVinciFlowError as err:
            items["StatusLabel"].Text = f"❌ Error: {err}"

    def on_close(ev: Any) -> None:
        dispatcher.ExitLoop()

    win.On.AnalyzeBtn.Clicked = on_analyze
    win.On.GenerateBtn.Clicked = on_generate
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

    # Estilos TTK Oscuros
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
    style.configure("Treeview", background="#1E293B", foreground="#F8FAFC", fieldbackground="#1E293B", rowheight=26)
    style.configure("Treeview.Heading", background="#334155", foreground="#38BDF8", font=("Segoe UI", 10, "bold"))

    # Encabezado
    header_frame = tk.Frame(root, bg="#0F172A")
    header_frame.pack(fill="x", padx=16, pady=(12, 6))
    ttk.Label(header_frame, text="DaVinci Flow", style="Header.TLabel").pack()
    ttk.Label(header_frame, text="Subtítulos Dinámicos Multicapa & SFX • biglexj (2026)", style="SubHeader.TLabel").pack()

    # Controles Superiores
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

    # Botones de Acción
    btn_frame = tk.Frame(root, bg="#0F172A")
    btn_frame.pack(fill="x", padx=16, pady=4)

    # Tabla / Treeview
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

    # Barra de Estado
    status_label = ttk.Label(root, text="Listo para conectar con DaVinci Resolve.", style="SubHeader.TLabel")
    status_label.pack(fill="x", padx=16, pady=4)

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
            status_label.config(text=f"✅ Plan listo: {plan.block_count} bloques clasificados. Capas: {plan.layer_distribution}")
        except DaVinciFlowError as err:
            status_label.config(text=f"❌ Error: {err}")

    def do_generate() -> None:
        is_dry = dry_run_var.get()
        status_label.config(text="Generando elementos en DaVinci Resolve...")
        root.update_idletasks()
        try:
            record = generate_from_active_timeline(
                track_index=track_var.get(),
                theme_name=theme_var.get(),
                profile_name=profile_var.get(),
                enable_sfx=sfx_var.get(),
                dry_run=is_dry,
            )
            mode = "Simulación" if is_dry else "Generación"
            status_label.config(text=f"🎉 {mode} completada: {record.item_count} clips creados en pistas dedicadas.")
        except DaVinciFlowError as err:
            status_label.config(text=f"❌ Error: {err}")

    ttk.Button(btn_frame, text="🔍 Analizar Capas", command=do_analyze, style="TButton").pack(side="left", padx=(0, 8))
    ttk.Button(btn_frame, text="⚡ Generar en Línea de Tiempo", command=do_generate, style="Accent.TButton").pack(side="left", padx=8)

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
