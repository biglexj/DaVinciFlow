"""Editor compartido de fase 1; abrirlo no consulta ni inicia Resolve."""

from dataclasses import replace
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from davinci_flow.ai.client import DEFAULT_MODEL, GeminiClient
from davinci_flow.editorial.model import EditorialError, EditorialOptions, Proposal
from davinci_flow.editorial.planner import propose
from davinci_flow.editorial.sources import basic_titles, capture, from_srt, media_pool_catalog, scan_installed
from davinci_flow.editorial.service import apply_reviewed, record_path_for, undo_reviewed


class EditorialWindow:
    def __init__(self, root: tk.Misc, *, embedded=False, model=None, options_provider=None,
                 catalog_action=None) -> None:
        self.root = root
        self.snapshot = None
        self.templates = basic_titles()
        self.proposal = None
        self.selected = None
        self.dirty = False
        self.busy = False
        self.events = queue.Queue()
        self.record_path = Path.home() / ".davinci_flow/records/editorial_last.json"
        self.status = tk.StringVar(root, "Carga un SRT offline o captura Resolve cuando esté disponible.")
        self.model = model if model is not None else tk.StringVar(root, DEFAULT_MODEL)
        self.options_provider = options_provider
        self.catalog_action = catalog_action
        self.fps = tk.StringVar(root, "24")
        self.track = tk.StringVar(root, "1")
        self.first = tk.StringVar(root, "1")
        self.last = tk.StringVar(root, "120")
        self.enabled = tk.BooleanVar(root, True)
        self.note = tk.StringVar(root)
        if not embedded:
            root.title("DaVinci Flow — Propuesta editorial LLM")
            root.geometry("1100x760")
            root.minsize(880, 660)
        panel = ttk.Frame(root, padding=12)
        panel.pack(fill="both", expand=True)
        source = ttk.Frame(panel)
        source.pack(fill="x")
        for label, variable, width in (("FPS SRT", self.fps, 6), ("Pista", self.track, 4),
                                       ("Primer subtítulo", self.first, 5), ("Último", self.last, 5)):
            ttk.Label(source, text=label).pack(side="left", padx=(0, 4))
            ttk.Entry(source, textvariable=variable, width=width).pack(side="left", padx=(0, 10))
        self.buttons = []
        self.button(source, "Abrir SRT offline", self.load_srt)
        self.button(source, "Capturar Resolve", self.capture)
        catalog = ttk.Frame(panel)
        catalog.pack(fill="x", pady=8)
        if catalog_action is None:
            self.button(catalog, "Títulos instalados", lambda: self.scan(None))
            self.button(catalog, "Carpeta de títulos…", self.browse_titles)
        self.button(catalog, "Elegir plantillas", self.configure_catalog)
        self.catalog_label = ttk.Label(catalog, text="Sin plantillas seleccionadas")
        self.catalog_label.pack(side="left", padx=8)
        actions = ttk.Frame(panel)
        actions.pack(fill="x", pady=4)
        ttk.Label(actions, text="Modelo exacto").pack(side="left")
        ttk.Entry(actions, textvariable=self.model, width=25, state="readonly" if embedded else "normal").pack(side="left", padx=6)
        self.button(actions, "Proponer con LLM", self.analyze)
        self.button(actions, "Abrir propuesta", self.load)
        self.button(actions, "Guardar propuesta", self.save)
        table = ttk.Frame(panel)
        table.pack(fill="both", expand=True, pady=8)
        self.tree = ttk.Treeview(table, columns=("time", "main", "layers", "state"), show="headings", height=12)
        for key, title, width in (("time", "Fotogramas", 130), ("main", "Texto principal", 480),
                                  ("layers", "Capas", 65), ("state", "Revisión", 110)):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width)
        scrollbar = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.select)
        self.original = ttk.Label(panel, text="Selecciona un bloque para revisarlo.", wraplength=1000)
        self.original.pack(fill="x")
        self.texts, self.choices = {}, {}
        for role, label in (("context", "Contexto"), ("main", "Principal"), ("accent", "Énfasis")):
            row = ttk.Frame(panel)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label, width=10).pack(side="left")
            var = tk.StringVar(root)
            ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True, padx=6)
            combo = ttk.Combobox(row, state="readonly", width=42)
            combo.pack(side="left")
            self.texts[role], self.choices[role] = var, combo
        row = ttk.Frame(panel)
        row.pack(fill="x", pady=4)
        ttk.Checkbutton(row, text="Incluir bloque", variable=self.enabled).pack(side="left")
        ttk.Label(row, text="Nota si reescribes").pack(side="left", padx=6)
        ttk.Entry(row, textvariable=self.note).pack(side="left", fill="x", expand=True)
        self.button(row, "Guardar revisión del bloque", self.review)
        bottom = ttk.Frame(panel)
        bottom.pack(fill="x", pady=8)
        self.button(bottom, "Aplicar revisión en Resolve", self.apply)
        self.button(bottom, "Deshacer muestra", self.undo)
        ttk.Label(panel, textvariable=self.status, wraplength=1000).pack(fill="x")
        self.refresh_catalog()
        root.after(100, self.poll)

    def button(self, parent, text, command):
        from davinci_flow.ui.widgets import RoundedButton
        button = RoundedButton(parent, text=text, command=lambda: self.guard(command),
                               primary=text in ("Proponer con LLM", "Aplicar revisión en Resolve"))
        button.pack(side="left", padx=3)
        self.buttons.append(button)

    def guard(self, command):
        if self.busy:
            return
        try:
            command()
        except Exception as error:
            self.status.set(str(error))
            messagebox.showerror("DaVinci Flow", str(error), parent=self.root)

    def reset(self):
        self.proposal = None
        self.selected = None
        self.tree.delete(*self.tree.get_children())

    def load_srt(self):
        path = filedialog.askopenfilename(parent=self.root, filetypes=[("Subtítulos", "*.srt")])
        if path:
            self.snapshot = from_srt(path, float(self.fps.get()))
            self.reset()
            self.status.set(f"{len(self.snapshot.cues)} subtítulos offline. No se ha conectado con Resolve.")

    def capture(self):
        from davinci_flow.resolve import connect_to_resolve
        session = connect_to_resolve()
        snapshot = capture(session, int(self.track.get()), int(self.first.get()), int(self.last.get()))
        templates, _ = media_pool_catalog(session.project.GetMediaPool())
        self.snapshot = snapshot
        if self.catalog_action is None:
            self.templates = tuple(t for t in self.templates if t.source != "media_pool") + templates
        self.reset()
        self.refresh_catalog()
        self.status.set(f"{snapshot.timeline} · {len(snapshot.cues)} subtítulos · {snapshot.width} × {snapshot.height}. "
                        f"{len(templates)} títulos del proyecto disponibles en Plantillas.")

    def scan(self, roots):
        catalog = {t.id: t for t in self.templates}
        diagnostics = []
        catalog.update({t.id: t for t in scan_installed(roots, diagnostics)})
        self.templates = tuple(catalog.values())
        self.reset()
        self.refresh_catalog()
        self.status.set("Inventario de archivos listo. La reproducción de cada plantilla requiere prueba en Resolve.")
        if diagnostics:
            messagebox.showwarning("Archivos omitidos", "\n".join(diagnostics), parent=self.root)

    def browse_titles(self):
        path = filedialog.askdirectory(parent=self.root, title="Carpeta de títulos .setting o .comp")
        if path:
            self.scan((Path(path),))

    def labels(self):
        from davinci_flow.ui.widgets import source_label
        return [f"{t.name} · {source_label(t)} · {t.id[-6:]}" for t in self.templates]

    def refresh_catalog(self):
        self.catalog_label.configure(text=f"{len(self.templates)} plantillas")
        for combo in self.choices.values():
            combo.configure(values=self.labels())

    def configure_catalog(self):
        if self.catalog_action is not None:
            self.catalog_action()
            return
        dialog = tk.Toplevel(self.root)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.title("Plantillas disponibles para la LLM")
        ttk.Label(dialog, text="Selecciona solo las plantillas que quieras utilizar. Nodo vacío: detectar un único Text+.").pack(padx=10, pady=10)
        tree = ttk.Treeview(dialog, columns=("source", "node"), show="tree headings", selectmode="extended")
        tree.heading("#0", text="Plantilla")
        tree.heading("source", text="Fuente")
        tree.heading("node", text="Nodo de texto")
        for i, t in enumerate(self.templates):
            tree.insert("", "end", iid=str(i), text=t.name, values=(t.source, t.text_tool + "::" + t.text_input))
        tree.pack(fill="both", expand=True, padx=10)
        tree.selection_set(tree.get_children())
        node = tk.StringVar(dialog)
        ttk.Label(dialog, text="Nodo::Control (ejemplo: MiTitulo::Input1; vacío = detectar Text+)").pack()
        ttk.Entry(dialog, textvariable=node).pack(fill="x", padx=10)
        def set_node():
            for item in tree.selection():
                values = tree.item(item, "values")
                tree.item(item, values=(values[0], node.get().strip()))
        ttk.Button(dialog, text="Asignar nodo a selección", command=set_node).pack(pady=5)
        def accept():
            selected = []
            for i in tree.selection():
                value = tree.item(i, "values")[1]
                tool, _, control = value.partition("::")
                selected.append(replace(self.templates[int(i)], text_tool=tool, text_input=control or "StyledText"))
            self.templates = tuple(selected)
            self.reset()
            self.refresh_catalog()
            dialog.destroy()
        ttk.Button(dialog, text="Usar solo las seleccionadas", command=accept).pack(pady=10)

    def analyze(self):
        if self.snapshot is None:
            raise EditorialError("Carga primero los subtítulos.")
        model = self.model.get().strip()
        if not model:
            raise EditorialError("Selecciona el identificador del modelo.")
        client = GeminiClient(model_name=model, strict_model=True)
        snapshot, templates = self.snapshot, self.templates
        options = self.options_provider() if self.options_provider is not None else None
        self.reset()
        self.busy = True
        for button in self.buttons:
            button.configure(state="disabled")
        self.status.set("Analizando con LLM; sin acceder a Resolve…")
        def worker():
            try:
                self.events.put((propose(snapshot, templates, client, options=options), None))
            except Exception as error:
                self.events.put((None, str(error)))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            result, error = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            for button in self.buttons:
                button.configure(state="normal")
            if error:
                self.status.set(error)
            else:
                self.proposal = result
                self.populate()
                self.status.set("Propuesta lista. Revisa y guarda cada bloque antes de aplicar.")
        self.root.after(100, self.poll)

    def populate(self):
        self.selected = None
        self.tree.delete(*self.tree.get_children())
        for i, (cue, decision) in enumerate(zip(self.proposal.snapshot.cues, self.proposal.decisions)):
            self.tree.insert("", "end", iid=str(i), values=(f"{cue.start_frame:g}–{cue.end_frame:g}",
                decision.main if decision.enabled else "— Dejar respirar la imagen —", len(decision.templates),
                ("Revisado" if decision.enabled else "Excluido") if decision.reviewed else "Pendiente"))
        self.dirty = True

    def select(self, event=None):
        selection = self.tree.selection()
        if not selection or self.proposal is None:
            return
        if self.selected is not None and int(selection[0]) != self.selected and self.form_changed():
            self.tree.selection_set(str(self.selected))
            self.status.set("Guarda la revisión del bloque antes de cambiar de fila.")
            return
        self.selected = int(selection[0])
        decision = self.proposal.decisions[self.selected]
        self.original.configure(text="Original: " + self.proposal.snapshot.cues[self.selected].text + "\nMotivo: " + decision.reason
                                + ("\nImagen (propuesta): " + decision.visual_note if decision.visual_note else ""))
        labels = dict(zip((t.id for t in self.templates), self.labels()))
        for role in self.texts:
            self.texts[role].set(getattr(decision, role))
            self.choices[role].set(labels.get(decision.templates.get(role), ""))
        self.enabled.set(decision.enabled)
        self.note.set(decision.edit_note)

    def form_changed(self):
        if self.selected is None or self.proposal is None:
            return False
        decision = self.proposal.decisions[self.selected]
        labels = dict(zip(self.labels(), (t.id for t in self.templates)))
        return (any(var.get().strip() != getattr(decision, role).strip() for role, var in self.texts.items())
                or any(labels.get(self.choices[r].get(), "") != tid for r, tid in decision.templates.items())
                or self.enabled.get() != decision.enabled or self.note.get().strip() != decision.edit_note)

    def review(self):
        if self.selected is None or self.proposal is None:
            raise EditorialError("Selecciona un bloque.")
        labels = dict(zip(self.labels(), (t.id for t in self.templates)))
        texts = {role: var.get().strip() for role, var in self.texts.items()}
        templates = {role: labels.get(self.choices[role].get(), "") for role, text in texts.items() if text}
        selected = self.selected
        self.proposal = self.proposal.edit(selected, **texts, templates=templates,
                                           enabled=self.enabled.get(), reviewed=True, edit_note=self.note.get().strip())
        self.populate()
        self.tree.selection_set(str(selected))

    def load(self):
        path = filedialog.askopenfilename(parent=self.root, filetypes=[("Propuesta", "*.json")])
        if path:
            proposal = Proposal.load(path)
            self.proposal, self.snapshot, self.templates = proposal, proposal.snapshot, proposal.templates
            self.refresh_catalog()
            self.populate()
            self.model.set(proposal.model)
            workbench = getattr(self.root.winfo_toplevel(), "_davinci_workbench", None)
            if workbench is not None and proposal.options is not None:
                from davinci_flow.ui.workbench_window import MODES, FORMATS, DENSITIES, label_for
                workbench.mode.set(label_for(MODES, proposal.options.mode))
                workbench.format.set(label_for(FORMATS, proposal.options.format))
                workbench.density.set(label_for(DENSITIES, proposal.options.density))
                workbench.direction.set(proposal.options.direction)
            self.fps.set(str(proposal.snapshot.fps))
            self.track.set(str(proposal.snapshot.track))
            self.first.set(str(proposal.snapshot.first))
            self.last.set(str(proposal.snapshot.last))
            self.status.set(f"Propuesta cargada: {proposal.snapshot.timeline}, {len(proposal.decisions)} bloques.")

    def save(self):
        if self.proposal is None:
            raise EditorialError("No hay propuesta para guardar.")
        if self.form_changed():
            raise EditorialError("Guarda primero la revisión del bloque que estás editando.")
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".json")
        if path:
            self.proposal.save(path)
            self.dirty = False
            self.status.set("Propuesta guardada. Las ediciones cuentan al pulsar Guardar revisión del bloque.")

    def apply(self):
        if self.proposal is None:
            raise EditorialError("No hay propuesta revisada.")
        if self.form_changed():
            raise EditorialError("Guarda primero la revisión del bloque que estás editando.")
        self.proposal.validate(require_review=True)
        if self.proposal.snapshot.source != "resolve":
            raise EditorialError("Esta propuesta es offline. Captura una secuencia de Resolve para aplicar.")
        from davinci_flow.resolve import connect_to_resolve
        self.record_path = record_path_for(self.proposal.snapshot.project_id, self.proposal.snapshot.timeline_id)
        result = apply_reviewed(self.proposal, connect_to_resolve(), self.record_path)
        self.status.set(f"Aplicados {result.item_count} elementos de la revisión guardada.")

    def undo(self):
        from davinci_flow.resolve import connect_to_resolve
        session = connect_to_resolve()
        self.record_path = record_path_for(str(session.project.GetUniqueId()), str(session.timeline.GetUniqueId()))
        result = undo_reviewed(session, self.record_path)
        self.status.set(f"Reversión: {result.status}.")


def open_editorial_window(parent=None):
    from davinci_flow.ui.workbench_window import open_workbench
    return open_workbench(parent)


def launch_editorial_window():
    """UIManager delega la ventana compartida a un proceso ligero de Python."""
    import os
    import subprocess
    import sys
    environment = os.environ.copy()
    package_root = str(Path(__file__).resolve().parents[2])
    environment["PYTHONPATH"] = os.pathsep.join(filter(None, (package_root, environment.get("PYTHONPATH"))))
    executable = Path(__file__).resolve().parents[3] / ".venv/Scripts/python.exe"
    if not executable.is_file():
        executable = Path(sys.executable)
    if not executable.name.lower().startswith("python"):
        raise EditorialError("Abre el editor con Python 3.13: python -m davinci_flow --editorial-ui.")
    subprocess.Popen([str(executable), "-m", "davinci_flow", "--editorial-ui"], env=environment,
                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
