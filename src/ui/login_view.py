"""Login-Bildschirm mit Passwort- und QR-Anmeldung."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.auth.login import AuthService
from src.config.settings import USERS_KV_PATH
from src.ui.base_view import BaseView


class LoginView(BaseView):
    """Anmeldebildschirm mit Tabs für Passwort und QR-Code."""

    def __init__(self, parent, app_state, on_navigate):
        super().__init__(parent, app_state, on_navigate)
        self.auth = AuthService(USERS_KV_PATH)
        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Titel
        title = ttk.Label(self, text="Anmeldung", font=("", 16, "bold"))
        title.grid(row=0, column=0, pady=(20, 10))

        # Notebook mit Tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=1, column=0, padx=40, pady=10, sticky="n")

        # --- Tab 1: Passwort ---
        pw_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(pw_frame, text="Passwort")

        ttk.Label(pw_frame, text="Benutzername:").grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )
        self.username_var = tk.StringVar()
        self.username_entry = ttk.Entry(pw_frame, textvariable=self.username_var, width=30)
        self.username_entry.grid(row=1, column=0, pady=(0, 10))

        ttk.Label(pw_frame, text="Passwort:").grid(
            row=2, column=0, sticky="w", pady=(0, 5)
        )
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(
            pw_frame, textvariable=self.password_var, show="*", width=30
        )
        self.password_entry.grid(row=3, column=0, pady=(0, 15))

        self.pw_login_btn = ttk.Button(
            pw_frame, text="Anmelden", command=self._login_password
        )
        self.pw_login_btn.grid(row=4, column=0)

        # Enter-Taste für Passwort-Login
        self.password_entry.bind("<Return>", lambda e: self._login_password())

        # --- Tab 2: QR-Code ---
        qr_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(qr_frame, text="QR-Code")

        ttk.Label(qr_frame, text="QR-Code scannen:").grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )
        self.qr_var = tk.StringVar()
        self.qr_entry = ttk.Entry(qr_frame, textvariable=self.qr_var, width=30)
        self.qr_entry.grid(row=1, column=0, pady=(0, 10))

        ttk.Label(
            qr_frame,
            text="Bitte QR-Code mit Handscanner scannen.",
            foreground="gray",
        ).grid(row=2, column=0, pady=(0, 15))

        # Enter-Taste für QR-Login (Scanner sendet Enter)
        self.qr_entry.bind("<Return>", lambda e: self._login_qr())

        # --- Status-Meldung ---
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(
            self, textvariable=self.status_var, foreground="red"
        )
        self.status_label.grid(row=2, column=0, pady=10)

    def on_show(self) -> None:
        self.username_var.set("")
        self.password_var.set("")
        self.qr_var.set("")
        self.status_var.set("")
        self.username_entry.focus_set()

    def _login_password(self) -> None:
        username = self.username_var.get().strip()
        password = self.password_var.get()

        if not username or not password:
            self.status_var.set("Bitte Benutzername und Passwort eingeben.")
            return

        user = self.auth.login_password(username, password)
        if user:
            self._on_login_success(user, "password")
        else:
            self._on_login_fail(username, "password")

    def _login_qr(self) -> None:
        scanned = self.qr_var.get().strip()
        if not scanned:
            return

        user = self.auth.login_qr(scanned)
        if user:
            self._on_login_success(user, "qr")
        else:
            self._on_login_fail("qr_scan", "qr")

    def _on_login_success(self, user, method: str) -> None:
        self.app_state.current_user = user
        if self.app_state.audit:
            self.app_state.audit.log(
                "login_success",
                user=user.user_id,
                details={"method": method},
            )
        self.on_navigate("file_select")

    def _on_login_fail(self, attempted: str, method: str) -> None:
        self.status_var.set("Anmeldung fehlgeschlagen.")
        if self.app_state.audit:
            self.app_state.audit.log(
                "login_fail",
                user=attempted,
                details={"method": method},
            )
        self.password_var.set("")
        self.qr_var.set("")
