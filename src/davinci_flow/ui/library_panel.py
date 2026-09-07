"""Rutas e inventario de recursos; la selección define el contexto enviado a la LLM."""

from tkinter import filedialog, ttk
import tkinter as tk

from davinci_flow.assets.library import CATEGORIES, scan_library
from davinci_flow.editorial.model import EditorialError
from davinci_flow.ui.widgets import RoundedButton


class LibraryPanel:
    def __init__(self, parent, workbench):
        self.app = workbench
        self.resources = ()
        self.selected_ids = set(workbench.preferences.resource_ids)
        self.paths = {key: tk.StringVar(parent, workbench.preferences.paths.get(key, "")) for key in CATEGORIES}
        ttk.Label(parent, text="Tu biblioteca de recursos", style="Title.TLabel").pack(anchor="w", pady=(10, 6))
        ttk.Label(parent, text="Define una carpeta por tipo. Solo se comparten los nombres y categorías de los recursos que selecciones.",
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 10))
        for category, label in CATEGORIES.items():
            row = ttk.Frame(parent)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=label, width=23).pack(side="left")
            ttk.Entry(row, textvariable=self.paths[category]).pack(side="left", fill="x", expand=True, padx=8)
            RoundedButton(row, "Elegir carpeta", lambda key=category: self.browse(key)).pack(side="left")
        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=12)
        RoundedButton(actions, "Guardar e indexar", self.scan, primary=True).pack(side="left")
        RoundedButton(actions, "Compartir seleccionados", self.share).pack(side="left", padx=8)
        RoundedButton(actions, "Quitar seleccionados", self.unshare).pack(side="left")
        ttk.Label(actions, text="Buscar", style="Muted.TLabel").pack(side="left", padx=(16, 6))
        self.query = tk.StringVar(parent)
        ttk.Entry(actions, textvariable=self.query, width=22).pack(side="left", fill="x", expand=True)
        self.query.trace_add("write", lambda *_: self.populate())
        table = ttk.Frame(parent)
        table.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table, columns=("shared", "category", "name"), show="headings", selectmode="extended")
        for key, title, width in (("shared", "Para la LLM", 100), ("category", "Tipo", 170), ("name", "Archivo", 630)):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=80)
        scroll = ttk.Scrollbar(table, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.summary = tk.StringVar(parent, "La biblioteca se lee al pulsar Guardar e indexar.")
        ttk.Label(parent, textvariable=self.summary, style="Muted.TLabel", wraplength=1050).pack(fill="x", pady=10)
        ttk.Label(parent, text="Los documentos se catalogan por nombre. Pega su contenido relevante en Dirección creativa. "
                  "Las sugerencias de imagen o sonido todavía no insertan recursos en la secuencia.",
                  style="Muted.TLabel", wraplength=1050).pack(fill="x", pady=(0, 10))

    def browse(self, key):
        path = filedialog.askdirectory(parent=self.app.root, title=CATEGORIES[key])
        if path:
            self.paths[key].set(path)

    def scan(self):
        def start():
            self.app.save_preferences()
            paths = {k: v.get().strip() for k, v in self.paths.items()}
            self.app.run_job(lambda: scan_library(paths), self.scanned, "Indexando nombres de recursos…")
        self.app.guard(start)

    def scanned(self, result):
        self.resources, diagnostics = result
        self.selected_ids &= {r.id for r in self.resources}
        self.populate()
        self.summary.set(f"{len(self.resources)} recursos · {len(self.selected_ids)} compartidos con la LLM. " + " ".join(diagnostics))
        self.app.save_preferences()

    def populate(self):
        self.tree.delete(*self.tree.get_children())
        query = self.query.get().casefold()
        for resource in self.resources:
            if query and query not in (resource.name + CATEGORIES[resource.category]).casefold():
                continue
            self.tree.insert("", "end", iid=resource.id, values=("Sí" if resource.id in self.selected_ids else "—",
                             CATEGORIES[resource.category], resource.name))

    def share(self):
        def accept():
            selection = self.selected_ids | set(self.tree.selection())
            if len(selection) > 80:
                raise EditorialError("Comparte hasta 80 recursos relevantes por propuesta.")
            self.selected_ids = selection
            self.app.save_preferences()
            self.populate()
            self.summary.set(f"{len(self.selected_ids)} recursos compartidos por nombre y categoría.")
        self.app.guard(accept)

    def unshare(self):
        self.selected_ids -= set(self.tree.selection())
        self.app.guard(self.app.save_preferences)
        self.populate()
        self.summary.set(f"{len(self.selected_ids)} recursos compartidos por nombre y categoría.")

    def context(self):
        if self.selected_ids and not self.resources:
            raise EditorialError("Vuelve a indexar la biblioteca para comprobar los recursos seleccionados.")
        return tuple(r.context() for r in self.resources if r.id in self.selected_ids)
