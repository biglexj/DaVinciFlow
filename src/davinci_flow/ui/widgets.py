"""Componentes ligeros compartidos: color, tipografía y botones redondeados."""

import tkinter as tk
from tkinter import ttk
from tkinter.font import Font

BG = "#10151F"
SURFACE = "#192231"
HOVER = "#29374B"
TEXT = "#ECF2FA"
MUTED = "#A5B4C8"
ACCENT = "#00C7B1"


def source_label(template):
    if template.source == "media_pool":
        return "Proyecto · Fusion"
    if "basic_titles" in template.locator:
        return "Text+ básico"
    return "Títulos instalados / archivos"


def apply_theme(root):
    root.configure(background=BG)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", font=("Segoe UI", 10), background=BG, foreground=TEXT,
                    borderwidth=0, focuscolor=BG)
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Muted.TLabel", foreground=MUTED)
    style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"))
    style.configure("TEntry", fieldbackground=SURFACE, foreground=TEXT, padding=7, insertcolor=TEXT)
    style.configure("TCombobox", fieldbackground=SURFACE, foreground=TEXT, padding=6, arrowcolor=MUTED)
    style.map("TCombobox", fieldbackground=[("readonly", SURFACE)], foreground=[("readonly", TEXT)])
    style.configure("TNotebook", background=BG, tabmargins=(0, 8, 0, 10))
    style.configure("TNotebook.Tab", padding=(23, 12), background=SURFACE, foreground=MUTED)
    style.map("TNotebook.Tab", background=[("selected", "#19413F")], foreground=[("selected", ACCENT)])
    style.configure("Treeview", background=SURFACE, fieldbackground=SURFACE, foreground=TEXT,
                    rowheight=32, borderwidth=0)
    style.configure("Treeview.Heading", background=HOVER, foreground=MUTED, padding=8,
                    font=("Segoe UI", 10, "bold"))
    style.map("Treeview", background=[("selected", "#225650")], foreground=[("selected", TEXT)])
    style.configure("TCheckbutton", background=BG, foreground=MUTED, padding=5)
    style.map("TCheckbutton", background=[("active", BG)])
    style.configure("Vertical.TScrollbar", background=HOVER, troughcolor=BG, arrowcolor=MUTED)
    root.option_add("*TCombobox*Listbox.background", SURFACE)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", HOVER)


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, primary=False):
        self.text, self.command, self.primary = text, command, primary
        self.disabled, self.hovered = False, False
        self.font = Font(parent, family="Segoe UI", size=10, weight="bold")
        super().__init__(parent, width=self.font.measure(text) + 28, height=38,
                         background=BG, highlightthickness=0, takefocus=True, cursor="hand2")
        self.bind("<Configure>", self.draw)
        self.bind("<Enter>", lambda e: self.hover(True))
        self.bind("<Leave>", lambda e: self.hover(False))
        self.bind("<FocusIn>", self.draw)
        self.bind("<FocusOut>", self.draw)
        self.bind("<ButtonRelease-1>", lambda e: self.invoke())
        self.bind("<Return>", lambda e: self.invoke())
        self.bind("<space>", lambda e: self.invoke())

    def hover(self, value):
        self.hovered = value
        self.draw()

    def invoke(self):
        if not self.disabled:
            self.command()

    def configure(self, cnf=None, **kwargs):
        if "state" in kwargs:
            self.disabled = kwargs.pop("state") == "disabled"
        super().configure(cnf, **kwargs)
        self.draw()

    config = configure

    def draw(self, event=None):
        self.delete("all")
        w, h, r = self.winfo_width() - 2, self.winfo_height() - 2, 10
        fill = HOVER if self.hovered else SURFACE
        if self.primary and not self.disabled:
            fill = "#4DDBCB" if self.hovered else ACCENT
        points = (r, 1, w-r, 1, w, 1, w, r, w, h-r, w, h, w-r, h, r, h, 1, h, 1, h-r, 1, r, 1, 1)
        self.create_polygon(points, smooth=True, splinesteps=24, fill=fill,
                            outline=ACCENT if self.focus_get() == self else fill)
        self.create_text(w/2, h/2, text=self.text, font=self.font,
                         fill=MUTED if self.disabled else (BG if self.primary else TEXT))
