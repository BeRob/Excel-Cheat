"""Einstiegspunkt der Messwerterfassung."""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path

_app_root = Path(__file__).resolve().parent
if str(_app_root) not in sys.path:
    sys.path.insert(0, str(_app_root))

from src.audit.audit_logger import AuditLogger
from src.config.settings import (
    APP_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT, AUDIT_LOG_PATH,
    APP_CONFIG_PATH, PRODUCTS_DIR,
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

        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.attributes("-fullscreen", True)

        apply_theme(self.root)

        self.state = AppState()
        self.state.audit = AuditLogger(AUDIT_LOG_PATH)
        self.state.app_config = load_app_config(APP_CONFIG_PATH, PRODUCTS_DIR)

        main_frame = tk.Frame(self.root, bg=COLORS["background"])
        main_frame.pack(fill="both", expand=True)

        header_bar = ttk.Frame(main_frame, style="Header.TFrame")
        header_bar.pack(fill="x", side="top", pady=(0, 1))

        logo_frame = ttk.Frame(header_bar, style="Header.TFrame")
        logo_frame.pack(side="left", padx=15, pady=8)

        # Logo via Pillow laden (saubere Skalierung), bei Fehler Textlabel
        logo_path = _app_root / "QUESTALPHA_StaticLogo_pos_rgb.png"
        try:
            from PIL import Image, ImageTk
            pil_img = Image.open(str(logo_path))
            target_h = 40
            target_w = int(pil_img.width * target_h / pil_img.height)
            pil_img = pil_img.resize((target_w, target_h), Image.LANCZOS)
            self._logo_image = ImageTk.PhotoImage(pil_img)
            ttk.Label(
                logo_frame, image=self._logo_image,
                background=COLORS["background"],
            ).pack(side="left")
        except Exception:
            ttk.Label(logo_frame, text="QUESTALPHA", style="LogoBold.TLabel").pack(side="left")

        ttk.Label(
            logo_frame, text="  |  QAInput - Messwerterfassung", style="HeaderInfo.TLabel",
        ).pack(side="left", padx=(5, 0))

        help_btn = ttk.Button(
            header_bar, text="?", width=3,
            style="Manual.TButton", command=self._open_manual,
        )
        help_btn.pack(side="right", padx=15, pady=8)

        self.container = tk.Frame(main_frame, bg=COLORS["background"])
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.views: dict[str, BaseView] = {}
        self.current_view_name: str | None = None

        self._create_views()
        self.navigate("login")

    def _open_manual(self) -> None:
        manual_path = _app_root / "Bedienungsanleitung.html"
        if manual_path.exists():
            os.startfile(str(manual_path))

    def _create_views(self) -> None:
        for view_class, name in self.SCREENS:
            view = view_class(self.container, self.state, self.navigate)
            view.grid(row=0, column=0, sticky="nsew")
            self.views[name] = view

    def navigate(self, target: str) -> None:
        if self.current_view_name and self.current_view_name in self.views:
            self.views[self.current_view_name].on_hide()

        self.current_view_name = target
        view = self.views[target]
        view.on_show()
        view.tkraise()

    def run(self) -> None:
        self.state.audit.log("app_start")
        self.root.mainloop()


def main() -> None:
    app = MeasurementApp()
    app.run()


if __name__ == "__main__":
    main()
