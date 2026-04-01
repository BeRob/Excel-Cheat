"""Messwerterfassung -- Einstiegspunkt der Anwendung."""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path

# Sicherstellen, dass das Projektverzeichnis im Suchpfad ist
_app_root = Path(__file__).resolve().parent
if str(_app_root) not in sys.path:
    sys.path.insert(0, str(_app_root))

from src.audit.audit_logger import AuditLogger
from src.config.settings import (
    APP_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT, AUDIT_LOG_PATH,
    APP_CONFIG_PATH, PRODUCTS_DIR, OUTPUT_DIR,
)
from src.config.process_config import load_app_config
from src.domain.state import AppState
from src.ui.theme import apply_theme, COLORS, FONTS
from src.ui.login_view import LoginView
from src.ui.product_process_view import ProductProcessView
from src.ui.context_view import ContextView
from src.ui.form_view import FormView
from src.ui.base_view import BaseView


class MeasurementApp:
    """Hauptanwendung: Fenster, Navigation und Verwaltung der Views."""

    SCREENS: list[tuple[type[BaseView], str]] = [
        (LoginView, "login"),
        (ProductProcessView, "product_process"),
        (ContextView, "context"),
        (FormView, "form"),
    ]

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(800, 600)

        # Vollbild / Maximiert starten
        try:
            self.root.state('zoomed')
        except tk.TclError:
            self.root.attributes('-fullscreen', True)

        apply_theme(self.root)

        self.state = AppState()
        self.state.audit = AuditLogger(AUDIT_LOG_PATH)

        # Konfiguration laden
        self.state.app_config = load_app_config(APP_CONFIG_PATH, PRODUCTS_DIR)

        # Output-Verzeichnis erstellen
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Hauptcontainer
        main_frame = tk.Frame(self.root, bg=COLORS["background"])
        main_frame.pack(fill="both", expand=True)

        # --- Branded Header Bar ---
        header_bar = ttk.Frame(main_frame, style="Header.TFrame")
        header_bar.pack(fill="x", side="top", pady=(0, 1))

        logo_frame = ttk.Frame(header_bar, style="Header.TFrame")
        logo_frame.pack(side="left", padx=15, pady=8)

        ttk.Label(logo_frame, text="QUEST", style="LogoBold.TLabel").pack(side="left")
        ttk.Label(logo_frame, text="ALPHA", style="LogoLight.TLabel").pack(side="left")
        ttk.Label(
            logo_frame, text="  |  Messwerterfassung", style="HeaderInfo.TLabel",
        ).pack(side="left", padx=(5, 0))

        help_btn = ttk.Button(
            header_bar, text="?", width=3,
            style="Manual.TButton", command=self._open_manual,
        )
        help_btn.pack(side="right", padx=15, pady=8)

        # Container fuer gestapelte Views
        self.container = tk.Frame(main_frame, bg=COLORS["background"])
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.views: dict[str, BaseView] = {}
        self.current_view_name: str | None = None

        self._create_views()
        self.navigate("login")

    def _open_manual(self) -> None:
        """Oeffnet die Bedienungsanleitung."""
        manual_path = _app_root / "Bedienungsanleitung.html"
        if manual_path.exists():
            os.startfile(str(manual_path))

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
