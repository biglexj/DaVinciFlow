"""Catálogo en una pestaña: descubrimiento y selección son acciones diferentes."""

from dataclasses import asdict
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk

from davinci_flow.editorial.model import EditorialError, Template
from davinci_flow.editorial.sources import basic_titles, media_pool_catalog, scan_installed
from davinci_flow.ui.widgets import RoundedButton, source_label


class TemplatePanel:
    def __init__(self, parent, workbench):
        self.app = workbench
        self.catalog = {t.id: t for t in basic_titles()}
        self.catalog.update({t.id: t for t in (Template(**raw) for raw in self.app.preferences.templates)})
        self.selected_ids = {t.id for t in self.app.editor.templates}
        self.query = tk.StringVar(parent)
        self.source = tk.StringVar(parent, "Todas las fuentes")
        ttk.Label(parent, text="Elige tus títulos", style="Title.TLabel").pack(anchor="w", pady=(10, 6))
        ttk.Label(parent, text="Combina títulos instalados y composiciones del proyecto. Las plantillas de karaoke se eligen de forma explícita.",
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 12))
        actions = ttk.Frame(parent)
        actions.pack(fill="x")
        for text, command in (("Leer títulos instalados", self.installed), ("Leer proyecto DaVinciFlow", self.project),
                              ("Añadir carpeta", self.folder)):
            RoundedButton(actions, text, command).pack(side="left", padx=(0, 8))
        filters = ttk.Frame(parent)
        filters.pack(fill="x", pady=12)
        ttk.Label(filters, text="Buscar").pack(side="left", padx=(0, 8))
        ttk.Entry(filters, textvariable=self.query).pack(side="left", fill="x", expand=True, padx=(0, 12))
        ttk.Combobox(filters, textvariable=self.source, state="readonly", width=32,
                     values=("Todas las fuentes", "Títulos instalados / archivos", "Proyecto · Fusion", "Text+ básico")).pack(side="left")
        self.query.trace_add("write", lambda *_: self.populate())
        self.source.trace_add("write", lambda *_: self.populate())
        table = ttk.Frame(parent)
        table.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table, columns=("selected", "name", "source"), show="headings", selectmode="extended")
        for key, title, width in (("selected", "En uso", 80), ("name", "Plantilla", 520), ("source", "Fuente", 330)):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=70)
        scroll = ttk.Scrollbar(table, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.describe)
        self.detail = tk.StringVar(parent, "Selecciona títulos y pulsa Usar selección. Cada capa conserva la animación de su plantilla.")
        ttk.Label(parent, textvariable=self.detail, style="Muted.TLabel", wraplength=1050).pack(fill="x", pady=10)
        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=(0, 10))
        RoundedButton(actions, "Usar selección", lambda: self.app.guard(self.use), primary=True).pack(side="left")
        RoundedButton(actions, "Añadir a las actuales", lambda: self.app.guard(lambda: self.use(add=True))).pack(side="left", padx=8)
        self.populate()

    def populate(self):
        self.tree.delete(*self.tree.get_children())
        query, source = self.query.get().casefold(), self.source.get()
        for t in sorted(self.catalog.values(), key=lambda t: t.name.casefold()):
            label = source_label(t)
            if (query and query not in (t.name + ' ' + t.locator).casefold()) or (source != "Todas las fuentes" and label != source):
                continue
            self.tree.insert("", "end", iid=t.id, values=("Sí" if t.id in self.selected_ids else "—", t.name, label))

    def describe(self, event=None):
        selection = self.tree.selection()
        if len(selection) == 1:
            t = self.catalog[selection[0]]
            self.detail.set(f"{t.name} · {source_label(t)}\n{t.locator}")
        elif selection:
            self.detail.set(f"{len(selection)} plantillas seleccionadas.")

    def scanned(self, result):
        templates, diagnostics = result
        self.catalog.update({t.id: t for t in templates})
        self.populate()
        self.detail.set(f"{len(templates)} títulos encontrados. Inventariar no comprueba la reproducción. " + " ".join(diagnostics))

    def scan(self, roots):
        def work():
            diagnostics = []
            return scan_installed(roots, diagnostics), diagnostics
        self.app.guard(lambda: self.app.run_job(work, self.scanned, "Leyendo títulos…"))

    def installed(self):
        self.scan(None)

    def folder(self):
        configured = self.app.library.paths["titles"].get().strip()
        path = filedialog.askdirectory(parent=self.app.root, title="Carpeta de títulos", initialdir=configured or None)
        if path:
            self.app.library.paths["titles"].set(path)
            self.scan((Path(path),))

    def project(self):
        def read():
            from davinci_flow.resolve import connect_to_resolve
            session = connect_to_resolve()
            templates, _ = media_pool_catalog(session.project.GetMediaPool())
            self.catalog = {k: t for k, t in self.catalog.items() if t.source != "media_pool"}
            self.scanned((templates, []))
        self.app.guard(read)

    def use(self, add=False):
        if self.app.editor.busy:
            raise EditorialError("Espera a que termine la propuesta.")
        if self.app.editor.proposal is not None:
            raise EditorialError("Guarda tu propuesta y vuelve a capturar la fuente antes de cambiar el catálogo.")
        selected = set(self.tree.selection())
        if add:
            selected |= self.selected_ids
        if not selected or len(selected) > 60:
            raise EditorialError("Selecciona entre 1 y 60 plantillas para esta propuesta.")
        self.selected_ids = selected
        self.app.editor.templates = tuple(t for t in self.catalog.values() if t.id in selected)
        self.app.editor.refresh_catalog()
        self.app.save_preferences()
        self.populate()
        self.detail.set(f"{len(selected)} plantillas disponibles para la LLM y para elegir por capa en el editor.")
