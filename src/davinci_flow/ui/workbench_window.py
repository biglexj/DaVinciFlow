"""Ventana única para propuesta, plantillas, recursos y configuración."""

from dataclasses import asdict
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from davinci_flow.ai.credentials import has_gemini_api_key, save_gemini_api_key
from davinci_flow.editorial.model import EditorialError, EditorialOptions, Template
from davinci_flow.editorial.preferences import Preferences, PREFERENCES_PATH
from davinci_flow.ui.editorial_window import EditorialWindow
from davinci_flow.ui.library_panel import LibraryPanel
from davinci_flow.ui.template_panel import TemplatePanel
from davinci_flow.ui.widgets import RoundedButton, apply_theme, MUTED

MODES = {"Énfasis selectivo": "highlights", "Subtítulos completos": "captions"}
FORMATS = {"Según la secuencia": "auto", "Horizontal": "horizontal", "Vertical": "vertical"}
DENSITIES = {"Pocos rótulos": "sparse", "Equilibrado": "balanced", "Más rótulos": "dense"}


def label_for(values, value):
    return next(k for k, v in values.items() if v == value)


class Workbench:
    def __init__(self, root, preferences_path=PREFERENCES_PATH):
        self.root, self.preferences_path = root, preferences_path
        self.preferences = Preferences.load(preferences_path)
        self.jobs = queue.Queue()
        self.job_busy = False
        self.model = tk.StringVar(root, self.preferences.model)
        self.mode = tk.StringVar(root, label_for(MODES, self.preferences.mode))
        self.format = tk.StringVar(root, label_for(FORMATS, self.preferences.format))
        self.density = tk.StringVar(root, label_for(DENSITIES, self.preferences.density))
        self.direction = tk.StringVar(root, self.preferences.direction)
        self.status = tk.StringVar(root, "Listo. Abre los subtítulos para comenzar.")
        root.title("DaVinci Flow — Editor y recursos")
        root.geometry("1180x870")
        root.minsize(1080, 780)
        apply_theme(root)
        header = ttk.Frame(root, padding=(24, 16, 24, 0))
        header.pack(fill="x")
        ttk.Label(header, text="DaVinci Flow", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="Ideas que acompañan tu montaje", style="Muted.TLabel").pack(side="left", padx=24)
        self.tabs = ttk.Notebook(root)
        self.tabs.pack(fill="both", expand=True, padx=18, pady=8)
        self.pages = {}
        for label in ("Editor", "Plantillas", "Biblioteca", "Ajustes"):
            frame = ttk.Frame(self.tabs, padding=10)
            self.tabs.add(frame, text=label)
            self.pages[label] = frame
        self.build_direction(self.pages["Editor"])
        host = ttk.Frame(self.pages["Editor"])
        host.pack(fill="both", expand=True)
        self.editor = EditorialWindow(host, embedded=True, model=self.model,
                                      options_provider=self.options, catalog_action=lambda: self.show("Plantillas"))
        if self.preferences.templates:
            self.editor.templates = tuple(Template(**t) for t in self.preferences.templates)
            self.editor.refresh_catalog()
        self.library = LibraryPanel(self.pages["Biblioteca"], self)
        self.catalog = TemplatePanel(self.pages["Plantillas"], self)
        self.build_settings(self.pages["Ajustes"])
        ttk.Label(root, textvariable=self.status, style="Muted.TLabel", wraplength=1080).pack(fill="x", padx=24, pady=(0, 12))
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(100, self.poll)
        self.model.trace_add("write", lambda *_: self.status.set(f"Modelo compartido: {self.model.get()} · Guarda los ajustes para conservarlo."))

    def show(self, name):
        self.tabs.select(self.pages[name])

    def build_direction(self, parent):
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=12, pady=(4, 6))
        for title, variable, choices, width in (("Modo", self.mode, MODES, 23), ("Formato", self.format, FORMATS, 22),
                                               ("Densidad", self.density, DENSITIES, 18)):
            ttk.Label(row, text=title).pack(side="left", padx=(0, 8))
            ttk.Combobox(row, textvariable=variable, values=tuple(choices), state="readonly", width=width).pack(side="left", padx=(0, 16))
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=12, pady=4)
        ttk.Label(row, text="Dirección creativa").pack(side="left", padx=(0, 10))
        ttk.Entry(row, textvariable=self.direction).pack(side="left", fill="x", expand=True)
        ttk.Label(parent, text="Ejemplo: pocas palabras grandes sobre B-rolls; alternar con planos limpios. Las animaciones y fuentes vienen de tus plantillas.",
                  style="Muted.TLabel").pack(anchor="w", padx=12, pady=(2, 4))

    def options(self):
        if self.job_busy:
            raise EditorialError("Espera a que termine la lectura de la biblioteca.")
        self.save_preferences()
        return EditorialOptions(MODES[self.mode.get()], FORMATS[self.format.get()], DENSITIES[self.density.get()],
                                self.direction.get().strip(), self.library.context())

    def save_preferences(self):
        preferences = Preferences(model=self.model.get().strip(), mode=MODES[self.mode.get()],
            format=FORMATS[self.format.get()], density=DENSITIES[self.density.get()], direction=self.direction.get().strip(),
            paths={key: var.get().strip() for key, var in self.library.paths.items()},
            templates=[asdict(t) for t in self.editor.templates], resource_ids=sorted(self.library.selected_ids))
        preferences.save(self.preferences_path)
        self.preferences = preferences

    def build_settings(self, parent):
        ttk.Label(parent, text="Un modelo para todo el editor", style="Title.TLabel").pack(anchor="w", pady=(10, 8))
        ttk.Label(parent, text="Se usa exactamente el identificador elegido. Los errores del proveedor se muestran sin cambiar de modelo.",
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 20))
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=8)
        ttk.Label(row, text="Modelo", width=22).pack(side="left")
        ttk.Entry(row, textvariable=self.model, width=40).pack(side="left", padx=8)
        RoundedButton(row, "Guardar ajustes", lambda: self.guard(self.save_settings), primary=True).pack(side="left", padx=8)
        self.key = tk.StringVar(parent)
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=8)
        ttk.Label(row, text="Clave API de Gemini", width=22).pack(side="left")
        ttk.Entry(row, textvariable=self.key, show="•", width=40).pack(side="left", padx=8)
        self.key_status = ttk.Label(parent, text="Clave configurada. Déjala vacía para conservarla." if has_gemini_api_key()
                                     else "Añade tu clave para generar propuestas.", style="Muted.TLabel")
        self.key_status.pack(anchor="w", pady=8)
        ttk.Label(parent, text="Las propuestas guardan el modelo, la dirección creativa y el inventario compartido que se usaron al generarlas. "
                  "Cambiar estos ajustes afecta a la próxima propuesta; aplicar una revisión no vuelve a llamar a la LLM.",
                  style="Muted.TLabel", wraplength=900).pack(anchor="w", pady=24)

    def save_settings(self):
        self.save_preferences()
        if self.key.get().strip():
            save_gemini_api_key(self.key.get())
            self.key.set("")
            self.key_status.configure(text="Clave configurada. Déjala vacía para conservarla.")
        self.status.set(f"Ajustes guardados · {self.model.get()}")

    def guard(self, command):
        try:
            return command()
        except Exception as error:
            self.status.set(str(error))
            messagebox.showerror("DaVinci Flow", str(error), parent=self.root)

    def run_job(self, work, finish, status):
        if self.job_busy or self.editor.busy:
            raise EditorialError("Espera a que termine la operación actual.")
        self.job_busy = True
        self.status.set(status)
        def worker():
            try:
                self.jobs.put((finish, work(), None))
            except Exception as error:
                self.jobs.put((finish, None, str(error)))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            finish, result, error = self.jobs.get_nowait()
        except queue.Empty:
            pass
        else:
            self.job_busy = False
            if error:
                self.status.set(error)
            else:
                self.guard(lambda: finish(result))
                self.status.set("Lectura terminada. Revisa la selección en la pestaña correspondiente.")
        self.root.after(100, self.poll)

    def close(self):
        if self.editor.busy or self.job_busy:
            self.status.set("Espera a que termine la operación antes de cerrar.")
            return
        if self.editor.proposal is not None and self.editor.dirty:
            if not messagebox.askyesno("Propuesta sin guardar", "¿Cerrar sin guardar la propuesta actual?", parent=self.root):
                return
        try:
            self.save_preferences()
        except Exception as error:
            self.status.set(str(error))
            return
        self.root.destroy()


def open_workbench(parent=None):
    if parent is not None:
        top = parent.winfo_toplevel()
        existing = getattr(top, "_davinci_workbench", None)
        if existing is not None:
            existing.show("Editor")
            return existing.editor
        # Compatibilidad con un anfitrión antiguo: incorporar una pestaña, nunca otro Toplevel.
        tabs = ttk.Notebook(top)
        tabs.pack(fill="both", expand=True)
        frame = ttk.Frame(tabs)
        tabs.add(frame, text="Editor LLM")
        editor = EditorialWindow(frame, embedded=True)
        return editor
    root = tk.Tk()
    app = Workbench(root)
    root._davinci_workbench = app
    root.mainloop()
    return app.editor
