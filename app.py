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
from src.audit.events import Event
from src.audit.logging_setup import init_logging, shutdown_logging
from src.config.settings import (
    APP_TITLE, APP_VERSION, WINDOW_WIDTH, WINDOW_HEIGHT, AUDIT_LOG_PATH,
    APP_CONFIG_PATH, PRODUCTS_DIR,
    DEBUG_LOG_PATH, ERROR_LOG_PATH, load_ui_prefs,
)
from src.config.process_config import load_app_config
from src.domain.state import AppState
from src.ui.theme import (
    apply_theme, COLORS, FONTS,
    scale_fonts, toggle_dark_mode, refresh_tk_widget_colors,
)
from src.ui.login_view import LoginView
from src.ui.product_process_view import ProductProcessView
from src.ui.context_view import ContextView
from src.ui.form_view import FormView
from src.ui.base_view import BaseView


import logging
import tkinter.messagebox as messagebox

_logger = logging.getLogger("app")


class MeasurementApp:
    """Hauptanwendung: Fenster, Navigation und Verwaltung der Views."""

    SCREENS: list[tuple[type[BaseView], str]] = [
        (LoginView, "login"),
        (ProductProcessView, "product_process"),
        (ContextView, "context"),
        (FormView, "form"),
    ]

    def __init__(self) -> None:
        # Logging muss vor allem anderen stehen, damit Fehler in der
        # Initialisierung selbst noch im error.log landen.
        init_logging(
            DEBUG_LOG_PATH, ERROR_LOG_PATH,
            on_exception=self._on_uncaught_exception,
        )
        _logger.info("app starting")

        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(800, 600)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.attributes("-fullscreen", True)

        apply_theme(self.root)

        self.state = AppState()
        self.state.audit = AuditLogger(AUDIT_LOG_PATH)
        try:
            self.state.app_config = load_app_config(APP_CONFIG_PATH, PRODUCTS_DIR)
        except Exception:
            _logger.exception("load_app_config fehlgeschlagen")
            self.state.audit.log_event(
                Event.EXCEPTION, level="error",
                details={"phase": "load_app_config"},
            )
            raise
        self.state.ui_prefs = load_ui_prefs()

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
        help_btn.pack(side="right", padx=(5, 15), pady=8)

        ttk.Button(
            header_bar, text="ⓘ", width=3,
            style="Manual.TButton", command=self._open_info_dialog,
        ).pack(side="right", padx=2, pady=8)

        ttk.Button(
            header_bar, text="+", width=3,
            style="Manual.TButton", command=self._increase_font,
        ).pack(side="right", padx=2, pady=8)

        ttk.Button(
            header_bar, text="–", width=3,
            style="Manual.TButton", command=self._decrease_font,
        ).pack(side="right", padx=2, pady=8)

        self._dark_btn = ttk.Button(
            header_bar, text="◑ Dark",
            style="Manual.TButton", command=self._toggle_dark,
        )
        self._dark_btn.pack(side="right", padx=(5, 2), pady=8)

        self._font_scale: int = 0

        self.container = tk.Frame(main_frame, bg=COLORS["background"])
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.views: dict[str, BaseView] = {}
        self.current_view_name: str | None = None

        self._create_views()
        self.navigate("login")

    def _increase_font(self) -> None:
        self._font_scale = scale_fonts(+1, self._font_scale)
        if self.state.audit:
            self.state.audit.log_event(
                Event.FONT_SCALED, details={"scale": self._font_scale},
            )

    def _decrease_font(self) -> None:
        self._font_scale = scale_fonts(-1, self._font_scale)
        if self.state.audit:
            self.state.audit.log_event(
                Event.FONT_SCALED, details={"scale": self._font_scale},
            )

    def _toggle_dark(self) -> None:
        is_dark = toggle_dark_mode(self.root, self._font_scale)
        self._dark_btn.config(text="◑ Hell" if is_dark else "◑ Dark")
        refresh_tk_widget_colors(self.root)
        if self.state.audit:
            self.state.audit.log_event(
                Event.DARK_MODE_TOGGLED, details={"dark": is_dark},
            )

    def _open_manual(self) -> None:
        manual_path = _app_root / "Kurzanleitung.html"
        if manual_path.exists():
            os.startfile(str(manual_path))

    def _open_info_dialog(self) -> None:
        """Kleines Info-Fenster mit App-Version, Host, Windows-User,
        Pfaden und Produkt-Revisionen."""
        import platform
        from src.config.settings import (
            AUDIT_LOG_PATH as _audit, DEBUG_LOG_PATH as _dbg,
            ERROR_LOG_PATH as _err, PRODUCTS_DIR as _prod, DATA_DIR as _data,
        )
        from src.version import APP_VERSION_DATE, collect_product_revisions

        dlg = tk.Toplevel(self.root)
        dlg.title("Info")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.configure(bg=COLORS["background"])
        dlg.resizable(False, True)

        header = ttk.Frame(dlg)
        header.pack(fill="x", padx=20, pady=(20, 5))
        ttk.Label(
            header, text="QAInput", style="Title.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            header, text="QA-Messwerterfassung · Questalpha",
            foreground=COLORS["text_secondary"],
        ).pack(anchor="w")

        audit = self.state.audit
        host = audit.host if audit else "?"
        win_user = audit.os_user if audit else "?"
        session = audit.session_id if audit else "?"
        app_user = (
            self.state.current_user.user_id
            if self.state.current_user else "(nicht angemeldet)"
        )

        rows: list[tuple[str, str]] = [
            ("Version", f"{APP_VERSION}  ({APP_VERSION_DATE})"),
            ("Python", platform.python_version()),
            ("System", f"{platform.system()} {platform.release()}"),
            ("Host", host),
            ("Windows-Benutzer", win_user),
            ("App-Benutzer", app_user),
            ("Session-ID", session[:12] + "…"),
            ("", ""),
            ("Datenverzeichnis", str(_data)),
            ("Produkte", str(_prod)),
            ("Audit-Log", str(_audit)),
            ("Debug-Log", str(_dbg)),
            ("Error-Log", str(_err)),
        ]

        grid = ttk.Frame(dlg)
        grid.pack(fill="x", padx=20, pady=10)
        for i, (label, value) in enumerate(rows):
            if not label and not value:
                ttk.Separator(grid, orient="horizontal").grid(
                    row=i, column=0, columnspan=2, sticky="ew", pady=4,
                )
                continue
            ttk.Label(
                grid, text=f"{label}:", font=FONTS["body_bold"],
            ).grid(row=i, column=0, sticky="w", padx=(0, 12), pady=2)
            ttk.Label(grid, text=value).grid(
                row=i, column=1, sticky="w", pady=2,
            )

        # Produkt-Revisionen
        revs = collect_product_revisions(_prod)
        if revs:
            ttk.Separator(dlg, orient="horizontal").pack(
                fill="x", padx=20, pady=(8, 4),
            )
            ttk.Label(
                dlg, text="Produkt-Revisionen", font=FONTS["body_bold"],
            ).pack(anchor="w", padx=20)

            list_frame = ttk.Frame(dlg)
            list_frame.pack(fill="both", expand=True, padx=20, pady=(4, 10))

            tree = ttk.Treeview(
                list_frame, columns=("rev",), show="tree headings",
                height=min(10, max(4, len(revs))),
            )
            tree.heading("#0", text="Produkt")
            tree.heading("rev", text="Revision")
            tree.column("#0", width=180, anchor="w")
            tree.column("rev", width=80, anchor="center")

            scroll = ttk.Scrollbar(
                list_frame, orient="vertical", command=tree.yview,
            )
            tree.configure(yscrollcommand=scroll.set)
            tree.pack(side="left", fill="both", expand=True)
            scroll.pack(side="right", fill="y")

            for pid in sorted(revs.keys()):
                tree.insert("", "end", text=pid, values=(revs[pid],))

        ttk.Button(
            dlg, text="Schließen", command=dlg.destroy,
            style="Accent.TButton",
        ).pack(pady=(5, 20))

        dlg.update_idletasks()
        rw = self.root.winfo_rootx()
        rh = self.root.winfo_rooty()
        rw_w = self.root.winfo_width()
        rw_h = self.root.winfo_height()
        dw = dlg.winfo_reqwidth()
        dh = dlg.winfo_reqheight()
        dlg.geometry(f"+{rw + (rw_w - dw)//2}+{rh + (rw_h - dh)//2}")

    def _on_uncaught_exception(self, exc: BaseException) -> None:
        """Vom logging_setup als Callback bei sys.excepthook / Tk-Hook gerufen."""
        try:
            if self.state.audit:
                self.state.audit.log_event(
                    Event.EXCEPTION, level="error",
                    user=(self.state.current_user.user_id
                          if self.state.current_user else None),
                    details={"type": type(exc).__name__, "msg": str(exc)},
                )
        except Exception:
            pass
        try:
            messagebox.showerror(
                "Unerwarteter Fehler",
                f"{type(exc).__name__}: {exc}\n\n"
                "Details stehen in der error.log-Datei.",
            )
        except Exception:
            pass

    def _on_close(self) -> None:
        try:
            if self.state.audit:
                user_id = (
                    self.state.current_user.user_id
                    if self.state.current_user else None
                )
                self.state.audit.log_event(
                    Event.APP_EXIT, user=user_id,
                )
        finally:
            shutdown_logging()
            try:
                self.root.destroy()
            except tk.TclError:
                pass

    def _create_views(self) -> None:
        for view_class, name in self.SCREENS:
            view = view_class(self.container, self.state, self.navigate)
            view.grid(row=0, column=0, sticky="nsew")
            self.views[name] = view

    def navigate(self, target: str) -> None:
        previous = self.current_view_name
        if previous and previous in self.views:
            self.views[previous].on_hide()

        self.current_view_name = target
        self.state.current_view = target
        if self.state.audit:
            self.state.audit.set_view(target)
            self.state.audit.log_event(
                Event.NAVIGATE,
                user=(self.state.current_user.user_id
                      if self.state.current_user else None),
                details={"from": previous, "to": target},
            )
        view = self.views[target]
        view.on_show()
        view.tkraise()

    def run(self) -> None:
        self.state.audit.log_event(Event.APP_START)
        try:
            self.root.mainloop()
        finally:
            shutdown_logging()


def main() -> None:
    app = MeasurementApp()
    app.run()


if __name__ == "__main__":
    main()
