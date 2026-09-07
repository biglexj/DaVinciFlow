"""Ventana de interfaz gráfica moderna para DaVinci Flow con centrado automático, scrollbars oscuros y ajustes optimizados."""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from davinci_flow.ai.aligner import parse_glossary_str
from davinci_flow.ai.client import DEFAULT_MODEL, list_available_gemini_models
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


def create_tkinter_window() -> None:
    from davinci_flow.ui.workbench_window import open_workbench
    open_workbench()


def create_legacy_tkinter_window() -> None:
    """Crea la interfaz de DaVinci Flow perfectamente centrada, con scrollbar dark y ajustes Gemini 3+."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("biglexj.davinciflow.subtitles")
        except Exception:
            pass

    root = tk.Tk()
    root.title("DaVinci Flow — Herramientas locales y corrección de guion")
    from davinci_flow.ui.editorial_window import open_editorial_window
    ttk.Button(root, text="Abrir editor LLM — tres capas con tus plantillas (fase 1)",
               command=lambda: open_editorial_window(root)).pack(side="top", fill="x", padx=12, pady=6)

    # Centrado automático en la pantalla
    win_w, win_h = 1120, 800
    scr_w = root.winfo_screenwidth()
    scr_h = root.winfo_screenheight()
    pos_x = max(0, (scr_w - win_w) // 2)
    pos_y = max(0, (scr_h - win_h) // 2 - 20)
    root.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
    root.minsize(980, 680)

    # 🎨 Paleta cromática oficial: DaVinci Dark Neutral + Acento Turquesa Ely (#00C7B1)
    BG_DARK = "#0f141c"          # Fondo de inputs, listboxes y tablas
    BG_WINDOW = "#141a24"        # Fondo general de la ventana
    BG_SIDEBAR = "#0c1017"       # Fondo de la barra lateral izquierda
    BG_HEADER = "#0c1017"        # Fondo de la cabecera superior
    BG_CARD = "#19222f"          # Fondo de tarjetas y contenedores
    BORDER_TURQUOISE = "#00C7B1" # Borde turquesa principal
    BORDER_MUTED = "#1e2c3d"     # Borde suave para contenedores
    BORDER_DARK_TEAL = "#103833" # Borde oscuro turquesa

    # Acentos Turquesa Ely (#00C7B1)
    ACCENT_TURQUOISE = "#00C7B1"
    ACCENT_HOVER = "#01D6B9"
    FG_ON_TURQUOISE = "#061816"  # Texto oscuro profundo para legibilidad máxima sobre turquesa

    # Botones Neutrales y Peligro
    BG_BTN_DARK = "#1a2433"
    BG_BTN_HOVER = "#243247"
    BG_DANGER = "#36161b"
    BORDER_DANGER = "#6b2229"
    FG_DANGER = "#ff7b87"
    BG_DANGER_HOVER = "#4a1c22"

    # Textos
    FG_TITLE = "#ffffff"
    FG_TEXT = "#e2e8f0"
    FG_MUTED = "#8fa0b5"
    FG_DISABLED = "#475569"
    FG_STATUS = "#00C7B1"

    root.configure(bg=BG_WINDOW)

    # Icono oficial transparente de assets
    try:
        icon_path = Path(__file__).resolve().parent.parent.parent.parent / "assets" / "branding" / "icons" / "icon-transparent.png"
        if icon_path.is_file():
            icon_img = tk.PhotoImage(file=str(icon_path))
            root.iconphoto(True, icon_img)
    except Exception:
        pass

    # Configuración de popups y listados de Combobox sin fondos blancos
    root.option_add("*TCombobox*Listbox.background", BG_DARK)
    root.option_add("*TCombobox*Listbox.foreground", FG_TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT_TURQUOISE)
    root.option_add("*TCombobox*Listbox.selectForeground", FG_ON_TURQUOISE)
    root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 9))
    root.option_add("*TCombobox*Listbox.relief", "flat")
    root.option_add("*TCombobox*Listbox.borderwidth", "1")
    root.option_add("*TCombobox*Listbox.highlightThickness", "0")

    style = ttk.Style(root)
    style.theme_use("clam")

    # Estilos globales ttk
    style.configure(".", background=BG_WINDOW, foreground=FG_TEXT, font=("Segoe UI", 9))
    style.configure("TFrame", background=BG_WINDOW)
    style.configure("Sidebar.TFrame", background=BG_SIDEBAR)
    style.configure("Header.TFrame", background=BG_HEADER)
    style.configure("Card.TFrame", background=BG_CARD)
    style.configure("TLabel", background=BG_WINDOW, foreground=FG_TEXT, font=("Segoe UI", 9))

    # Entradas de Texto y Spinbox con bordes turquesa / dark
    style.configure(
        "TEntry",
        fieldbackground=BG_DARK,
        foreground=FG_TEXT,
        insertcolor=ACCENT_TURQUOISE,
        borderwidth=1,
        relief="solid",
        darkcolor=BORDER_TURQUOISE,
        lightcolor=BORDER_TURQUOISE,
    )
    style.map(
        "TEntry",
        fieldbackground=[("active", BG_DARK), ("!disabled", BG_DARK)],
        foreground=[("active", FG_TEXT), ("!disabled", FG_TEXT)],
    )

    style.configure(
        "TSpinbox",
        fieldbackground=BG_DARK,
        background=BG_BTN_DARK,
        foreground=FG_TEXT,
        arrowcolor=ACCENT_TURQUOISE,
        borderwidth=1,
        relief="solid",
        darkcolor=BORDER_MUTED,
        lightcolor=BORDER_MUTED,
    )

    # Combobox con borde turquesa y lista oscura
    style.configure(
        "TCombobox",
        fieldbackground=BG_DARK,
        background=BG_BTN_DARK,
        foreground=FG_TEXT,
        darkcolor=BORDER_TURQUOISE,
        lightcolor=BORDER_TURQUOISE,
        arrowcolor=ACCENT_TURQUOISE,
        relief="solid",
        borderwidth=1,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", BG_DARK), ("!readonly", BG_DARK)],
        foreground=[("readonly", FG_TEXT), ("!readonly", FG_TEXT)],
        selectbackground=[("readonly", ACCENT_TURQUOISE), ("!readonly", ACCENT_TURQUOISE)],
        selectforeground=[("readonly", FG_ON_TURQUOISE), ("!readonly", FG_ON_TURQUOISE)],
    )

    # Scrollbar Oscuro Estilizado
    style.configure(
        "Vertical.TScrollbar",
        background=BG_BTN_DARK,
        troughcolor=BG_DARK,
        bordercolor=BG_DARK,
        arrowcolor=ACCENT_TURQUOISE,
        relief="flat",
        borderwidth=0,
    )
    style.map(
        "Vertical.TScrollbar",
        background=[("active", ACCENT_TURQUOISE), ("!disabled", BG_BTN_DARK)],
        arrowcolor=[("active", FG_ON_TURQUOISE), ("!disabled", ACCENT_TURQUOISE)],
    )

    # Checkbuttons
    style.configure("TCheckbutton", background=BG_WINDOW, foreground=FG_TEXT, focuscolor="none")
    style.map("TCheckbutton", background=[("active", BG_WINDOW)], foreground=[("active", "#ffffff")])

    # Tabla Treeview
    style.configure(
        "Treeview",
        background=BG_DARK,
        fieldbackground=BG_DARK,
        foreground=FG_TEXT,
        borderwidth=0,
        relief="flat",
        font=("Segoe UI", 9),
        rowheight=26,
    )
    style.configure(
        "Treeview.Heading",
        background=BG_CARD,
        foreground="#8fa0b5",
        borderwidth=0,
        relief="flat",
        font=("Segoe UI", 9, "bold"),
    )
    style.map("Treeview", background=[("selected", "#103833")], foreground=[("selected", "#00e5cc")])

    # =========================================================================
    # 1. BARRA SUPERIOR (HEADER)
    # =========================================================================
    header_bar = tk.Frame(root, bg=BG_HEADER, height=52, padx=18, pady=9)
    header_bar.pack(fill="x", side="top")

    # Brand Title
    brand_frame = tk.Frame(header_bar, bg=BG_HEADER)
    brand_frame.pack(side="left")
    tk.Label(brand_frame, text="DaVinci Flow", bg=BG_HEADER, fg=FG_TITLE, font=("Segoe UI", 12, "bold")).pack(side="left", padx=(0, 14))
    tk.Label(brand_frame, text="Subtítulos Dinámicos Multicapa & Asistente IA", bg=BG_HEADER, fg=FG_MUTED, font=("Segoe UI", 9)).pack(side="left")

    # Top Right Hero Action Button
    header_right = tk.Frame(header_bar, bg=BG_HEADER)
    header_right.pack(side="right")

    top_gen_btn = tk.Button(
        header_right,
        text="⚡ Generate Timeline",
        bg=ACCENT_TURQUOISE,
        fg=FG_ON_TURQUOISE,
        activebackground=ACCENT_HOVER,
        activeforeground=FG_ON_TURQUOISE,
        font=("Segoe UI", 9, "bold"),
        relief="flat",
        padx=16,
        pady=5,
        cursor="hand2",
    )
    top_gen_btn.pack(side="right")

    # =========================================================================
    # 2. CONTENEDOR CENTRAL: SIDEBAR + MAIN CONTENT
    # =========================================================================
    body_frame = tk.Frame(root, bg=BG_WINDOW)
    body_frame.pack(fill="both", expand=True)

    # BARRA LATERAL IZQUIERDA (SIDEBAR)
    sidebar = tk.Frame(body_frame, bg=BG_SIDEBAR, width=195, padx=12, pady=14)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    project_label_title = tk.Label(sidebar, text="Project Alpha", bg=BG_SIDEBAR, fg=FG_TITLE, font=("Segoe UI", 10, "bold"), anchor="w")
    project_label_title.pack(fill="x")
    project_label_sub = tk.Label(sidebar, text="V1.0 - Subtitles", bg=BG_SIDEBAR, fg=FG_MUTED, font=("Segoe UI", 8), anchor="w")
    project_label_sub.pack(fill="x", pady=(0, 12))

    new_asset_btn = tk.Button(
        sidebar,
        text="+ New Asset",
        bg=BG_CARD,
        fg=FG_TEXT,
        activebackground=BG_BTN_HOVER,
        activeforeground="#ffffff",
        font=("Segoe UI", 9, "bold"),
        relief="solid",
        borderwidth=1,
        highlightbackground=BORDER_MUTED,
        pady=5,
        cursor="hand2",
    )
    new_asset_btn.pack(fill="x", pady=(0, 16))

    # Botones de Navegación Lateral
    sidebar_items_frame = tk.Frame(sidebar, bg=BG_SIDEBAR)
    sidebar_items_frame.pack(fill="x")

    nav_btns: dict[str, tk.Label] = {}

    def make_nav_item(parent: Any, key: str, text: str, cmd: Any) -> None:
        lbl = tk.Label(
            parent,
            text=text,
            bg=BG_SIDEBAR,
            fg=FG_MUTED,
            font=("Segoe UI", 10),
            anchor="w",
            padx=8,
            pady=7,
            cursor="hand2",
        )
        lbl.pack(fill="x", pady=2)
        lbl.bind("<Button-1>", lambda _: cmd())
        nav_btns[key] = lbl

    # =========================================================================
    # ÁREA PRINCIPAL
    # =========================================================================
    main_area = tk.Frame(body_frame, bg=BG_WINDOW, padx=16, pady=12)
    main_area.pack(side="right", fill="both", expand=True)

    view_editor = tk.Frame(main_area, bg=BG_WINDOW)
    view_library = tk.Frame(main_area, bg=BG_WINDOW)
    view_assistant = tk.Frame(main_area, bg=BG_WINDOW)
    view_settings = tk.Frame(main_area, bg=BG_WINDOW)

    def switch_view(view_name: str) -> None:
        view_editor.pack_forget()
        view_library.pack_forget()
        view_assistant.pack_forget()
        view_settings.pack_forget()

        for k, btn in nav_btns.items():
            btn.config(bg=BG_SIDEBAR, fg=FG_MUTED, font=("Segoe UI", 10))

        if view_name == "editor":
            view_editor.pack(fill="both", expand=True)
            if "editor" in nav_btns:
                nav_btns["editor"].config(bg="#12242b", fg=ACCENT_TURQUOISE, font=("Segoe UI", 10, "bold"))
        elif view_name == "library":
            view_library.pack(fill="both", expand=True)
            if "library" in nav_btns:
                nav_btns["library"].config(bg="#12242b", fg=ACCENT_TURQUOISE, font=("Segoe UI", 10, "bold"))
        elif view_name == "assistant":
            view_assistant.pack(fill="both", expand=True)
            if "assistant" in nav_btns:
                nav_btns["assistant"].config(bg="#12242b", fg=ACCENT_TURQUOISE, font=("Segoe UI", 10, "bold"))
        elif view_name == "settings":
            view_settings.pack(fill="both", expand=True)
            if "settings" in nav_btns:
                nav_btns["settings"].config(bg="#12242b", fg=ACCENT_TURQUOISE, font=("Segoe UI", 10, "bold"))

    make_nav_item(sidebar_items_frame, "editor", "✏️  Editor (Subtítulos)", lambda: switch_view("editor"))
    make_nav_item(sidebar_items_frame, "library", "📁  Library (B-Rolls)", lambda: switch_view("library"))
    make_nav_item(sidebar_items_frame, "assistant", "🤖  Assistant (Guion)", lambda: switch_view("assistant"))
    make_nav_item(sidebar_items_frame, "settings", "⚙️  Settings (Ajustes)", lambda: switch_view("settings"))

    # Bottom Sidebar items
    sidebar_bottom = tk.Frame(sidebar, bg=BG_SIDEBAR)
    sidebar_bottom.pack(side="bottom", fill="x", pady=(10, 0))
    make_nav_item(sidebar_bottom, "history", "🕒  History", lambda: switch_view("editor"))

    # Consola desactivada
    lbl_console = tk.Label(
        sidebar_bottom,
        text="📟  Console (Inactivo)",
        bg=BG_SIDEBAR,
        fg=FG_DISABLED,
        font=("Segoe UI", 9),
        anchor="w",
        padx=8,
        pady=6,
    )
    lbl_console.pack(fill="x", pady=1)

    def make_action_btn(parent: Any, text: str, cmd: Any) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=cmd,
            bg=BG_CARD,
            fg=FG_TEXT,
            activebackground=BG_BTN_HOVER,
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
            relief="solid",
            borderwidth=1,
            highlightbackground=BORDER_TURQUOISE,
            highlightcolor=BORDER_TURQUOISE,
            highlightthickness=1,
            padx=10,
            pady=3,
            cursor="hand2",
        )

    # =========================================================================
    # VISTA 1: ✏️ EDITOR (SUBTÍTULOS & CAPAS)
    # =========================================================================
    card_params = tk.Frame(view_editor, bg=BG_CARD, padx=12, pady=8, relief="solid", borderwidth=1, highlightbackground=BORDER_DARK_TEAL, highlightthickness=1)
    card_params.pack(fill="x", pady=(0, 6))

    f_params = tk.Frame(card_params, bg=BG_CARD)
    f_params.pack(fill="x", pady=2)

    tk.Label(f_params, text="Origen:", bg=BG_CARD, fg=FG_MUTED).pack(side="left", padx=(0, 4))
    track_type_var = tk.StringVar(value="subtitle")
    track_type_combo = ttk.Combobox(f_params, textvariable=track_type_var, values=["subtitle", "video", "auto"], width=8, state="readonly")
    track_type_combo.pack(side="left", padx=(0, 8))

    tk.Label(f_params, text="Pista:", bg=BG_CARD, fg=FG_MUTED).pack(side="left", padx=(0, 4))
    track_var = tk.IntVar(value=1)
    ttk.Spinbox(f_params, from_=1, to=16, textvariable=track_var, width=3).pack(side="left", padx=(0, 8))

    tk.Label(f_params, text="Tema/Preset:", bg=BG_CARD, fg=FG_MUTED).pack(side="left", padx=(0, 4))
    theme_var = tk.StringVar(value="ely")
    theme_combo = ttk.Combobox(f_params, textvariable=theme_var, values=["ely", "aurora"], width=16, state="readonly")
    theme_combo.pack(side="left", padx=(0, 8))

    tk.Label(f_params, text="Perfil:", bg=BG_CARD, fg=FG_MUTED).pack(side="left", padx=(0, 4))
    profile_var = tk.StringVar(value="natural")
    profile_combo = ttk.Combobox(f_params, textvariable=profile_var, values=["natural", "dinamico", "reflexivo", "educativo", "video_corto"], width=9, state="readonly")
    profile_combo.pack(side="left", padx=(0, 8))

    loaded_srt_tk: list[str] = []

    def reset_timeline() -> None:
        loaded_srt_tk.clear()
        try:
            summary = inspect_active_timeline()
            project_label_title.config(text=summary.project_name or "Proyecto Activo")
            project_label_sub.config(text=f"TL: {summary.timeline_name} ({summary.subtitle_track_count} pistas)")
            presets = get_available_mediapool_presets()
            theme_vals = ["ely", "aurora"] + [p.display_label for p in presets]
            theme_combo.config(values=theme_vals)
        except Exception as e:
            status_label.config(text=f"Aviso de conexión: {e}")
        do_analyze()

    btn_read_tl = make_action_btn(f_params, "🎬 Leer Pista", reset_timeline)
    btn_read_tl.pack(side="left", padx=3)

    def choose_srt() -> None:
        f = filedialog.askopenfilename(
            title="Seleccionar subtítulo SRT",
            filetypes=[("Archivos SRT", "*.srt"), ("Todos los archivos", "*.*")],
        )
        if f:
            loaded_srt_tk.clear()
            loaded_srt_tk.append(f)
            status_label.config(text=f"📂 Transcripción SRT: {Path(f).name}.")
            do_analyze()

    btn_load_srt = make_action_btn(f_params, "📂 Cargar SRT", choose_srt)
    btn_load_srt.pack(side="left", padx=3)

    def do_export_srt() -> None:
        if not current_plan_tk or current_plan_tk[0].block_count == 0:
            status_label.config(text="⚠️ No hay subtítulos analizados para exportar.")
            return
        f = filedialog.asksaveasfilename(
            title="Exportar subtítulos corregidos a SRT",
            defaultextension=".srt",
            filetypes=[("Archivos SubRip SRT", "*.srt"), ("Todos los archivos", "*.*")],
        )
        if f:
            plan = current_plan_tk[0]
            cues = [b.to_subtitle_cue() for b in plan.blocks]
            export_srt_file(f, cues, fps=plan.fps)
            status_label.config(text=f"💾 Exportado a {Path(f).name}.")

    btn_exp_srt = make_action_btn(f_params, "💾 Exportar SRT", do_export_srt)
    btn_exp_srt.pack(side="left", padx=3)

    # Fila 2: Switches y Animación
    f_opts = tk.Frame(card_params, bg=BG_CARD)
    f_opts.pack(fill="x", pady=(4, 2))

    sfx_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(f_opts, text="SFX", variable=sfx_var).pack(side="left", padx=(0, 10))

    broll_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(f_opts, text="B-Rolls", variable=broll_var).pack(side="left", padx=(0, 10))

    dry_run_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(f_opts, text="Dry-Run", variable=dry_run_var).pack(side="left", padx=(0, 10))

    correct_ai_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(f_opts, text="Guion/IA", variable=correct_ai_var).pack(side="left", padx=(0, 10))

    markers_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(f_opts, text="Marcadores", variable=markers_var).pack(side="left", padx=(0, 14))

    tk.Label(f_opts, text="Animación:", bg=BG_CARD, fg=FG_MUTED).pack(side="left", padx=(0, 4))
    anim_var = tk.StringVar(value="Auto (Perfil)")
    anim_combo = ttk.Combobox(
        f_opts,
        textvariable=anim_var,
        values=["Auto (Perfil)", "Pop Bounce", "Slide Up", "Smooth Fade", "Kinetic Pulse", "Typewriter", "Estático (None)"],
        width=13,
        state="readonly",
    )
    anim_combo.pack(side="left")

    # Fila 3: Las 4 Tarjetas de Acción Principales
    f_hero_actions = tk.Frame(view_editor, bg=BG_WINDOW)
    f_hero_actions.pack(fill="x", pady=(4, 8))

    cancel_flag_tk = [False]
    current_plan_tk: list[GenerationPlan] = []

    def _selected_anim_str() -> str | None:
        val = anim_var.get()
        mapping = {
            "Pop Bounce": "pop_bounce",
            "Slide Up": "slide_up",
            "Smooth Fade": "fade_smooth",
            "Kinetic Pulse": "kinetic_pulse",
            "Typewriter": "typewriter",
            "Estático (None)": "none",
        }
        return mapping.get(val)

    def do_analyze() -> None:
        status_label.config(text="🔍 Analizando transcripción y clasificando capas...")
        root.update_idletasks()
        try:
            gloss_val = parse_glossary_str(glossary_text.get("1.0", "end-1c").strip())
            srt_f = loaded_srt_tk[0] if loaded_srt_tk else None
            selected_th = theme_var.get()
            th_name = "ely" if selected_th.startswith("📁") else selected_th
            assets_dir = assets_dir_var.get().strip() or None
            enable_brolls = broll_var.get()

            plan, _ = plan_active_subtitles(
                track_index=track_var.get(),
                track_type=track_type_var.get(),
                theme_name=th_name,
                profile_name=profile_var.get(),
                enable_sfx=sfx_var.get(),
                glossary=gloss_val,
                use_ai_correction=False,
                animation_preset=_selected_anim_str(),
                srt_path=srt_f,
            )
            if plan.block_count == 0:
                status_label.config(text=f"⚠️ La pista {track_var.get()} ({track_type_var.get()}) no contiene subtítulos.")
                tree.delete(*tree.get_children())
                current_plan_tk.clear()
                return

            current_plan_tk.clear()
            current_plan_tk.append(plan)

            broll_map: dict[int, str] = {}
            if enable_brolls and assets_dir:
                try:
                    proposals = propose_brolls_for_plan(plan, assets_directory=assets_dir, use_ai=False)
                    broll_map = {p.block_index: p.asset.name for p in proposals}
                except Exception:
                    pass

            tree.delete(*tree.get_children())
            for idx, b in enumerate(plan.blocks, start=1):
                layer_tag = "layer3" if b.layer_count == 3 else "layer2" if b.layer_count == 2 else "layer1"
                tree.insert(
                    "",
                    "end",
                    values=(
                        f"{b.start_frame:g}-{b.end_frame:g}",
                        f"{b.layer_count} capas",
                        b.context_text or "—",
                        b.main_text,
                        b.accent_text or "—",
                        b.sfx_proposal or "—",
                        b.style_preset or "auto",
                        broll_map.get(idx, "—"),
                    ),
                    tags=(layer_tag,),
                )
            status_label.config(text=f"✓ Transcripción cargada ({plan.block_count} bloques). Listo para generar o corregir.")
        except Exception as err:
            status_label.config(text=f"❌ Error al analizar: {err}")

    def do_generate() -> None:
        editor = open_editorial_window(root)
        editor.track.set(str(track_var.get()))
        editor.model.set(model_var.get().strip() or DEFAULT_MODEL)
        editor.guard(editor.capture)
        status_label.config(text="Revisa la propuesta y sus plantillas en el editor LLM antes de aplicar.")

    def do_generate_legacy() -> None:
        cancel_flag_tk[0] = False
        track = track_var.get()
        is_dry = dry_run_var.get()
        script_val = script_text_area.get("1.0", "end-1c").strip()
        gloss_val = parse_glossary_str(glossary_text.get("1.0", "end-1c").strip())
        key_val = api_key_var.get().strip() or None
        ai_model_val = model_var.get().strip() or DEFAULT_MODEL
        use_ai_val = correct_ai_var.get()
        add_markers_val = markers_var.get()
        srt_f = loaded_srt_tk[0] if loaded_srt_tk else None
        selected_preset = theme_var.get()
        th_name = "ely" if selected_preset.startswith("📁") else selected_preset
        preset_name = selected_preset if selected_preset.startswith("📁") else None
        assets_dir = assets_dir_var.get().strip() or None
        enable_brolls = broll_var.get()

        status_label.config(text="⚡ Generando elementos nativos Fusion en DaVinci Resolve...")
        root.update_idletasks()

        def progress_cb(c: int, tot: int, msg: str) -> None:
            status_label.config(text=f"⚡ {msg}")
            root.update_idletasks()

        try:
            record = generate_from_active_timeline(
                track_index=track,
                track_type=track_type_var.get(),
                theme_name=th_name,
                profile_name=profile_var.get(),
                enable_sfx=sfx_var.get(),
                dry_run=is_dry,
                original_script=script_val,
                glossary=gloss_val,
                api_key=key_val,
                model_name=ai_model_val,
                use_ai_correction=use_ai_val,
                animation_preset=_selected_anim_str(),
                insert_markers=add_markers_val,
                srt_path=srt_f,
                template_preset_name=preset_name,
                assets_directory=assets_dir,
                enable_brolls=enable_brolls,
                progress_callback=progress_cb,
                is_cancelled=lambda: cancel_flag_tk[0],
            )
            if record.status == "cancelled":
                status_label.config(text=f"⏹️ Generación detenida por el usuario ({record.item_count} clips creados).")
            else:
                if is_dry:
                    status_label.config(text=f"🔎 Dry-Run completado: {record.item_count} elementos planificados.")
                else:
                    status_label.config(text=f"🎉 Generación completada: {record.item_count} clips creados y verificados en Resolve.")
        except Exception as err:
            status_label.config(text=f"❌ Error: {err}")

    def do_revert() -> None:
        status_label.config(text="Deshaciendo la muestra editorial de esta secuencia...")
        root.update_idletasks()
        try:
            from davinci_flow.editorial.service import record_path_for, undo_reviewed
            from davinci_flow.resolve import connect_to_resolve
            session = connect_to_resolve()
            path = record_path_for(str(session.project.GetUniqueId()), str(session.timeline.GetUniqueId()))
            result = undo_reviewed(session, path)
            status_label.config(text=f"🔄 Reversión editorial: {result.status}.")
        except Exception as err:
            status_label.config(text=f"❌ Error al deshacer: {err}")

    def do_stop() -> None:
        cancel_flag_tk[0] = True
        status_label.config(text="⏹️ Cancelación solicitada... Deteniendo tras el bloque actual.")

    # Tarjeta 1: Analizar Transcripción
    btn_hero_analyze = tk.Button(
        f_hero_actions,
        text="🔍  Análisis local",
        command=do_analyze,
        bg=BG_CARD,
        fg=FG_TEXT,
        activebackground=BG_BTN_HOVER,
        activeforeground="#ffffff",
        font=("Segoe UI", 9, "bold"),
        relief="solid",
        borderwidth=1,
        highlightbackground=BORDER_TURQUOISE,
        highlightcolor=BORDER_TURQUOISE,
        highlightthickness=1,
        padx=14,
        pady=8,
        cursor="hand2",
    )
    btn_hero_analyze.pack(side="left", fill="both", expand=True, padx=(0, 4))

    # Tarjeta 2: Generar en Timeline (HERO TURQUESA)
    btn_hero_gen = tk.Button(
        f_hero_actions,
        text="⚡  Revisar y generar con LLM",
        command=do_generate,
        bg=ACCENT_TURQUOISE,
        fg=FG_ON_TURQUOISE,
        activebackground=ACCENT_HOVER,
        activeforeground=FG_ON_TURQUOISE,
        font=("Segoe UI", 10, "bold"),
        relief="flat",
        padx=18,
        pady=8,
        cursor="hand2",
    )
    btn_hero_gen.pack(side="left", fill="both", expand=True, padx=4)
    top_gen_btn.config(command=do_generate, text="Editor LLM")

    # Tarjeta 3: Deshacer
    btn_hero_undo = tk.Button(
        f_hero_actions,
        text="🔄  Deshacer",
        command=do_revert,
        bg=BG_CARD,
        fg=FG_TEXT,
        activebackground=BG_BTN_HOVER,
        activeforeground="#ffffff",
        font=("Segoe UI", 9, "bold"),
        relief="solid",
        borderwidth=1,
        highlightbackground=BORDER_MUTED,
        highlightthickness=1,
        padx=14,
        pady=8,
        cursor="hand2",
    )
    btn_hero_undo.pack(side="left", fill="both", expand=True, padx=4)

    # Tarjeta 4: Detener
    btn_hero_stop = tk.Button(
        f_hero_actions,
        text="⏹  Detener",
        command=do_stop,
        bg=BG_DANGER,
        fg=FG_DANGER,
        activebackground=BG_DANGER_HOVER,
        activeforeground="#ffffff",
        font=("Segoe UI", 9, "bold"),
        relief="solid",
        borderwidth=1,
        highlightbackground=BORDER_DANGER,
        highlightthickness=1,
        padx=14,
        pady=8,
        cursor="hand2",
    )
    btn_hero_stop.pack(side="left", fill="both", expand=True, padx=(4, 0))

    # Fila 4: Tabla de Datos Moderna
    tree_card = tk.Frame(view_editor, bg=BG_DARK, relief="solid", borderwidth=1, highlightbackground=BORDER_DARK_TEAL, highlightthickness=1)
    tree_card.pack(fill="both", expand=True, pady=(2, 0))

    columns = ("time", "layers", "context", "main", "accent", "sfx", "anim", "broll")
    tree = ttk.Treeview(tree_card, columns=columns, show="headings")
    tree.heading("time", text="Tiempo (f)")
    tree.heading("layers", text="Capas")
    tree.heading("context", text="Contexto")
    tree.heading("main", text="Principal (Corregido)")
    tree.heading("accent", text="Acento")
    tree.heading("sfx", text="SFX")
    tree.heading("anim", text="Animación")
    tree.heading("broll", text="B-Roll / SFX")

    tree.column("time", width=85, anchor="center")
    tree.column("layers", width=55, anchor="center")
    tree.column("context", width=110)
    tree.column("main", width=200)
    tree.column("accent", width=95)
    tree.column("sfx", width=60, anchor="center")
    tree.column("anim", width=75, anchor="center")
    tree.column("broll", width=100)

    # Tags para badges de colores
    tree.tag_configure("layer3", foreground="#00e5cc")
    tree.tag_configure("layer2", foreground=FG_TEXT)
    tree.tag_configure("layer1", foreground=FG_MUTED)

    scrollbar = ttk.Scrollbar(tree_card, orient="vertical", command=tree.yview, style="Vertical.TScrollbar")
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # =========================================================================
    # VISTA 2: 🤖 ASSISTANT (GUION & ASISTENTE GEMINI)
    # =========================================================================
    card_glossary = tk.Frame(view_assistant, bg=BG_CARD, padx=14, pady=10, relief="solid", borderwidth=1, highlightbackground=BORDER_DARK_TEAL, highlightthickness=1)
    card_glossary.pack(fill="x", pady=(0, 8))

    f_gloss_header = tk.Frame(card_glossary, bg=BG_CARD)
    f_gloss_header.pack(fill="x", pady=(0, 4))
    tk.Label(f_gloss_header, text="Glosario / Jergas y Marcas Fijas (Reemplazos automáticos):", bg=BG_CARD, fg=FG_TITLE, font=("Segoe UI", 9, "bold")).pack(side="left")

    glossary_text = tk.Text(
        card_glossary,
        bg=BG_DARK,
        fg=FG_TEXT,
        insertbackground=ACCENT_TURQUOISE,
        font=("Segoe UI", 9),
        height=2,
        relief="solid",
        borderwidth=1,
        highlightbackground=BORDER_TURQUOISE,
        highlightcolor=BORDER_TURQUOISE,
        highlightthickness=1,
        padx=6,
        pady=4,
    )
    glossary_text.insert("1.0", "biglex: Biglex J, resolve: DaVinci Resolve, ely: Ely Vtuber")
    glossary_text.pack(fill="x")

    # Guion Original
    f_script_header = tk.Frame(view_assistant, bg=BG_WINDOW)
    f_script_header.pack(fill="x", pady=(4, 2))
    tk.Label(f_script_header, text="Guion Original (Referencia para sincronización, corrección y marcadores):", bg=BG_WINDOW, fg=FG_TITLE, font=("Segoe UI", 9, "bold")).pack(side="left")

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

    make_action_btn(f_script_header, "📄 Cargar Guion .txt", choose_script).pack(side="right")

    script_text_area = tk.Text(
        view_assistant,
        bg=BG_DARK,
        fg=FG_TEXT,
        insertbackground=ACCENT_TURQUOISE,
        font=("Consolas", 9),
        height=12,
        relief="solid",
        borderwidth=1,
        highlightbackground=BORDER_MUTED,
        highlightthickness=1,
        padx=6,
        pady=4,
    )
    script_text_area.pack(fill="both", expand=True, pady=(2, 6))

    def do_ai_correct() -> None:
        status_label.config(text=f"🤖 Conectando con Gemini ({model_var.get()}) para corrección y marcadores...")
        root.update_idletasks()
        try:
            script_val = script_text_area.get("1.0", "end-1c").strip()
            gloss_val = parse_glossary_str(glossary_text.get("1.0", "end-1c").strip())
            key_val = api_key_var.get().strip() or None
            srt_f = loaded_srt_tk[0] if loaded_srt_tk else None
            ai_model_val = model_var.get().strip() or DEFAULT_MODEL
            selected_th = theme_var.get()
            th_name = "ely" if selected_th.startswith("📁") else selected_th
            assets_dir = assets_dir_var.get().strip() or None
            enable_brolls = broll_var.get()

            def progress_cb(curr: int, tot: int, msg: str) -> None:
                status_label.config(text=f"🤖 {msg}")
                root.update_idletasks()

            plan, corr = plan_active_subtitles(
                track_index=track_var.get(),
                track_type=track_type_var.get(),
                theme_name=th_name,
                profile_name=profile_var.get(),
                enable_sfx=sfx_var.get(),
                original_script=script_val,
                glossary=gloss_val,
                api_key=key_val,
                model_name=ai_model_val,
                use_ai_correction=True,
                animation_preset=_selected_anim_str(),
                srt_path=srt_f,
                progress_callback=progress_cb,
            )
            if plan.block_count == 0:
                status_label.config(text=f"⚠️ La pista {track_var.get()} no contiene subtítulos.")
                tree.delete(*tree.get_children())
                current_plan_tk.clear()
                return

            current_plan_tk.clear()
            current_plan_tk.append(plan)

            broll_map: dict[int, str] = {}
            if enable_brolls and assets_dir:
                try:
                    proposals = propose_brolls_for_plan(
                        plan,
                        assets_directory=assets_dir,
                        api_key=key_val,
                        model_name=ai_model_val,
                        use_ai=True,
                    )
                    broll_map = {p.block_index: p.asset.name for p in proposals}
                except Exception:
                    pass

            tree.delete(*tree.get_children())
            for idx, b in enumerate(plan.blocks, start=1):
                layer_tag = "layer3" if b.layer_count == 3 else "layer2" if b.layer_count == 2 else "layer1"
                tree.insert(
                    "",
                    "end",
                    values=(
                        f"{b.start_frame:g}-{b.end_frame:g}",
                        f"{b.layer_count} capas",
                        b.context_text or "—",
                        b.main_text,
                        b.accent_text or "—",
                        b.sfx_proposal or "—",
                        b.style_preset or "auto",
                        broll_map.get(idx, "—"),
                    ),
                    tags=(layer_tag,),
                )
            corr_count = corr.total_corrections if corr else 0
            mark_count = corr.total_markers if corr else 0
            b_count = len(broll_map)
            switch_view("editor")
            status_label.config(text=f"✨ Corrección IA completada: {corr_count} correcciones, {mark_count} marcadores y {b_count} B-Rolls.")
        except Exception as err:
            status_label.config(text=f"❌ Error en corrección IA: {err}")

    btn_ai_action = tk.Button(
        view_assistant,
        text="✨  Analizar & Corregir con IA",
        command=do_ai_correct,
        bg=ACCENT_TURQUOISE,
        fg=FG_ON_TURQUOISE,
        activebackground=ACCENT_HOVER,
        activeforeground=FG_ON_TURQUOISE,
        font=("Segoe UI", 10, "bold"),
        relief="flat",
        pady=8,
        cursor="hand2",
    )
    btn_ai_action.pack(fill="x", pady=4)

    # =========================================================================
    # VISTA 3: 📁 LIBRARY (B-ROLLS & ASSETS)
    # =========================================================================
    card_assets = tk.Frame(view_library, bg=BG_CARD, padx=14, pady=12, relief="solid", borderwidth=1, highlightbackground=BORDER_DARK_TEAL, highlightthickness=1)
    card_assets.pack(fill="x", pady=(0, 10))

    f_ass_row = tk.Frame(card_assets, bg=BG_CARD)
    f_ass_row.pack(fill="x", pady=4)

    tk.Label(f_ass_row, text="Carpeta de Assets / B-Rolls:", bg=BG_CARD, fg=FG_MUTED).pack(side="left", padx=(0, 6))
    assets_dir_var = tk.StringVar()
    assets_dir_entry = ttk.Entry(f_ass_row, textvariable=assets_dir_var, width=42)
    assets_dir_entry.pack(side="left", padx=(0, 8))

    def choose_assets_dir() -> None:
        d = filedialog.askdirectory(title="Seleccionar carpeta de Assets / B-Rolls y Sonidos")
        if d:
            assets_dir_var.set(d)
            status_label.config(text=f"📁 Carpeta de assets: {Path(d).name}")
            do_analyze()

    make_action_btn(f_ass_row, "📁 Seleccionar Carpeta...", choose_assets_dir).pack(side="left", padx=3)

    assets_info = tk.Label(
        view_library,
        text="Biblioteca de Recursos Multimedia:\n\n• Almacena tus clips B-Rolls (.mp4, .mov, .mkv) y efectos de sonido (.wav, .mp3) en tu carpeta.\n• DaVinci Flow indexa las etiquetas semánticas a partir de los nombres de carpeta y archivos.\n• El motor IA colocará automáticamente los planos de apoyo sobre la pista DF_BROLL según el ritmo del guion.",
        bg=BG_WINDOW,
        fg=FG_MUTED,
        justify="left",
        font=("Segoe UI", 9),
        pady=10,
    )
    assets_info.pack(anchor="w")

    # =========================================================================
    # VISTA 4: ⚙️ SETTINGS (AJUSTES DE API & MODELOS GEMINI 3+)
    # =========================================================================
    card_settings = tk.Frame(view_settings, bg=BG_CARD, padx=18, pady=18, relief="solid", borderwidth=1, highlightbackground=BORDER_DARK_TEAL, highlightthickness=1)
    card_settings.pack(fill="x", pady=(0, 10))

    tk.Label(card_settings, text="Configuración de Inteligencia Artificial (Google Gemini 3+)", bg=BG_CARD, fg=FG_TITLE, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 14))

    # Fila API Key (Expandible y amplia)
    f_set_key = tk.Frame(card_settings, bg=BG_CARD)
    f_set_key.pack(fill="x", pady=6)

    tk.Label(f_set_key, text="API Key Gemini:", bg=BG_CARD, fg=FG_MUTED, width=14, anchor="w").pack(side="left")
    api_key_var = tk.StringVar()
    if has_gemini_api_key():
        try:
            api_key_var.set(get_gemini_api_key())
        except Exception:
            pass
    api_key_entry = ttk.Entry(f_set_key, textvariable=api_key_var, show="*")
    api_key_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

    # Fila Modelo Activo
    f_set_model = tk.Frame(card_settings, bg=BG_CARD)
    f_set_model.pack(fill="x", pady=6)

    tk.Label(f_set_model, text="Modelo Activo:", bg=BG_CARD, fg=FG_MUTED, width=14, anchor="w").pack(side="left")
    model_var = tk.StringVar(value=DEFAULT_MODEL)
    initial_models = list_available_gemini_models(api_key=api_key_var.get().strip() or None)
    model_combo = ttk.Combobox(f_set_model, textvariable=model_var, values=list(initial_models), state="readonly")
    model_combo.pack(side="left", fill="x", expand=True, padx=(0, 10))

    def save_settings_action() -> None:
        k = api_key_var.get().strip()
        if not k:
            messagebox.showwarning("Aviso", "Ingresa una clave API válida.")
            return
        try:
            save_gemini_api_key(k)
            fresh = list_available_gemini_models(api_key=k)
            model_combo.config(values=list(fresh))
            messagebox.showinfo("Éxito", f"Clave API guardada ({mask_api_key(k)}).\nModelos Gemini 3+ actualizados.")
            status_label.config(text=f"✅ Ajustes guardados ({mask_api_key(k)}).")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")

    f_set_actions = tk.Frame(card_settings, bg=BG_CARD)
    f_set_actions.pack(fill="x", pady=(14, 4))

    btn_save_settings = tk.Button(
        f_set_actions,
        text="💾  Guardar Ajustes de API",
        command=save_settings_action,
        bg=ACCENT_TURQUOISE,
        fg=FG_ON_TURQUOISE,
        activebackground=ACCENT_HOVER,
        activeforeground=FG_ON_TURQUOISE,
        font=("Segoe UI", 9, "bold"),
        relief="flat",
        padx=16,
        pady=6,
        cursor="hand2",
    )
    btn_save_settings.pack(side="left")

    # =========================================================================
    # 3. BARRA DE ESTADO INFERIOR
    # =========================================================================
    status_bar = tk.Frame(root, bg=BG_HEADER, padx=14, pady=6, relief="flat")
    status_bar.pack(fill="x", side="bottom")

    status_label = tk.Label(status_bar, text="Listo.", bg=BG_HEADER, fg=FG_STATUS, font=("Segoe UI", 9), anchor="w")
    status_label.pack(side="left", fill="x", expand=True)

    def on_info() -> None:
        status_label.config(text="DaVinci Flow v0.2.0 • biglexj | Donaciones: https://www.biglexj.com/donaciones")

    tk.Button(status_bar, text="ℹ Info", command=on_info, bg=BG_HEADER, fg=FG_MUTED, relief="flat", font=("Segoe UI", 8), cursor="hand2").pack(side="right", padx=6)
    tk.Button(status_bar, text="Cerrar", command=root.destroy, bg=BG_HEADER, fg=FG_MUTED, relief="flat", font=("Segoe UI", 8), cursor="hand2").pack(side="right")

    # Iniciar en la vista Editor
    switch_view("editor")
    reset_timeline()

    root.mainloop()
