"""Inicio y revisión de la ventana compartida, sin conexión ni GPU de Resolve."""

import tkinter as tk
import unittest
from unittest.mock import patch

from davinci_flow.ui.editorial_window import EditorialWindow
from test_editorial import sample


class EditorialUiTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f"Tk no disponible: {error}")
        self.root.withdraw()
        self.connection = patch("davinci_flow.resolve.connect_to_resolve", side_effect=AssertionError("No conectar"))
        self.connect = self.connection.start()
        self.window = EditorialWindow(self.root)

    def tearDown(self):
        if hasattr(self, "connection"):
            self.connection.stop()
            self.root.destroy()

    def test_window_initialization_does_not_connect(self):
        self.root.update_idletasks()
        self.connect.assert_not_called()
        self.assertEqual(len(self.window.buttons), 11)

    def test_block_review_persists_selected_template(self):
        window = self.window
        window.proposal = sample()
        window.snapshot, window.templates = window.proposal.snapshot, window.proposal.templates
        window.refresh_catalog()
        window.populate()
        window.tree.selection_set("0")
        window.select()
        window.review()
        self.assertTrue(window.proposal.decisions[0].reviewed)
        self.assertEqual(window.proposal.decisions[0].templates, {"main": "pool_p1"})
        self.connect.assert_not_called()

    def test_unsaved_form_changes_cannot_be_applied(self):
        from davinci_flow.editorial.model import EditorialError
        window = self.window
        window.proposal = sample().edit(0, reviewed=True)
        window.snapshot, window.templates = window.proposal.snapshot, window.proposal.templates
        window.refresh_catalog()
        window.populate()
        window.tree.selection_set("0")
        window.select()
        window.texts["main"].set("Edición todavía sin guardar")
        with self.assertRaises(EditorialError):
            window.apply()
        self.connect.assert_not_called()
