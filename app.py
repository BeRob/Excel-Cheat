"""Messwerterfassung -- Einstiegspunkt der Anwendung."""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path

# Sicherstellen, dass das Projektverzeichnis im Suchpfad ist
_app_root = Path(__file__).resolve().parent
if str(_app_root) not in sys.path:
    sys.path.insert(0, str(_app_root))

from src.audit.audit_logger import AuditLogger
from src.config.settings import APP_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT, AUDIT_LOG_PATH
from src.domain.state import AppState
from src.ui.theme import apply_theme, COLORS, FONTS
from src.ui.login_view import LoginView
from src.ui.file_select_view import FileSelectView
from src.ui.column_classify_view import ColumnClassifyView
from src.ui.context_view import ContextView
from src.ui.form_view import FormView
from src.ui.base_view import BaseView


class MeasurementApp:
    """Hauptanwendung: Fenster, Navigation und Verwaltung der Views."""

    SCREENS: list[tuple[type[BaseView], str]] = [
        (LoginView, "login"),
        (FileSelectView, "file_select"),
        (ColumnClassifyView, "column_classify"),
        (ContextView, "context"),
        (FormView, "form"),
    ]

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(600, 400)

        apply_theme(self.root)

        self.state = AppState()
        self.state.audit = AuditLogger(AUDIT_LOG_PATH)

        # Hauptcontainer
        main_frame = tk.Frame(self.root, bg=COLORS["background"])
        main_frame.pack(fill="both", expand=True)

        # --- Branded Header Bar ---
        header_bar = ttk.Frame(main_frame, style="Header.TFrame")
        header_bar.pack(fill="x", side="top", pady=(0, 1)) # Small padding for border effect if needed

        # Logo Container to hold the parts
        logo_frame = ttk.Frame(header_bar, style="Header.TFrame")
        logo_frame.pack(side="left", padx=15, pady=8)

        # "QUEST" part (Bold)
        ttk.Label(
            logo_frame,
            text="QUEST",
            style="LogoBold.TLabel",
        ).pack(side="left")

        # "ALPHA" part (Light/Normal)
        ttk.Label(
            logo_frame,
            text="ALPHA",
            style="LogoLight.TLabel",
        ).pack(side="left")

        # Separator and Title
        ttk.Label(
            logo_frame,
            text="  |  Messwerterfassung",
            style="HeaderInfo.TLabel",
        ).pack(side="left", padx=(5, 0))

        # Container fuer gestapelte Views
        self.container = tk.Frame(main_frame, bg=COLORS["background"])
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.views: dict[str, BaseView] = {}
        self.current_view_name: str | None = None

        self._create_views()
        self.navigate("login")

    def _create_views(self) -> None:
        for ViewClass, name in self.SCREENS:
            view = ViewClass(self.container, self.state, self.navigate)
            view.grid(row=0, column=0, sticky="nsew")
            self.views[name] = view

    def navigate(self, target: str) -> None:
        """Wechselt zum angegebenen Bildschirm."""
        if self.current_view_name and self.current_view_name in self.views:
            self.views[self.current_view_name].on_hide()

        self.current_view_name = target
        view = self.views[target]
        view.on_show()
        view.tkraise()

    def run(self) -> None:
        """Startet die Anwendung."""
        self.state.audit.log("app_start")
        self.root.mainloop()


def main() -> None:
    app = MeasurementApp()
    app.run()


if __name__ == "__main__":
    main()
