"""Basis für alle Bildschirm-Views."""

from __future__ import annotations

import tkinter as tk
from typing import Callable

from src.domain.state import AppState


class BaseView(tk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        app_state: AppState,
        on_navigate: Callable[[str], None],
    ) -> None:
        super().__init__(parent, bg="#FFFFFF")
        self.app_state = app_state
        self.on_navigate = on_navigate

    def on_show(self) -> None:
        """Wird aufgerufen, wenn die View sichtbar wird."""

    def on_hide(self) -> None:
        """Wird aufgerufen, wenn die View ausgeblendet wird."""
