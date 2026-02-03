"""Kontext-Bildschirm: Chargen-Nr, FA-Nr, Rolle setzen."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from pathlib import Path

from src.domain.state import ContextInfo
from src.ui.base_view import BaseView


class ContextView(BaseView):
    """Bildschirm zum Setzen der Kontext-Informationen."""

    def __init__(self, parent, app_state, on_navigate):
        super().__init__(parent, app_state, on_navigate)
        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)

        # --- Obere Leiste ---
        top_bar = ttk.Frame(self)
        top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        top_bar.columnconfigure(0, weight=1)

        self.info_label = ttk.Label(top_bar, text="")
        self.info_label.grid(row=0, column=0, sticky="w")

        btn_frame = ttk.Frame(top_bar)
        btn_frame.grid(row=0, column=1)
        ttk.Button(btn_frame, text="Datei wechseln", command=self._change_file).pack(
            side="left", padx=(5, 0)
        )
        ttk.Button(btn_frame, text="Abmelden", command=self._logout).pack(
            side="left", padx=(5, 0)
        )

        # --- Titel ---
        ttk.Label(self, text="Kontext setzen", font=("", 14, "bold")).grid(
            row=1, column=0, pady=(10, 5)
        )

        # --- Kontext-Felder ---
        form = ttk.Frame(self)
        form.grid(row=2, column=0, padx=40, pady=10)

        self.charge_var = tk.StringVar()
        self.fa_var = tk.StringVar()
        self.rolle_var = tk.StringVar()

        fields = [
            ("Chargen-Nr:", self.charge_var),
            ("FA-Nr:", self.fa_var),
            ("Rolle:", self.rolle_var),
        ]

        for i, (label_text, var) in enumerate(fields):
            ttk.Label(form, text=label_text).grid(
                row=i, column=0, sticky="w", pady=5, padx=(0, 10)
            )
            entry = ttk.Entry(form, textvariable=var, width=30)
            entry.grid(row=i, column=1, pady=5)
            if i == 0:
                self._first_entry = entry

        # Validierung: Button aktivieren wenn alle Felder gefüllt
        for var in (self.charge_var, self.fa_var, self.rolle_var):
            var.trace_add("write", self._check_fields)

        # --- Weiter-Button ---
        self.next_btn = ttk.Button(
            self, text="Weiter zur Messung", command=self._go_next, state="disabled"
        )
        self.next_btn.grid(row=3, column=0, pady=15)

    def on_show(self) -> None:
        # Info-Leiste aktualisieren
        user = self.app_state.current_user
        file = self.app_state.current_file
        user_name = user.display_name if user else "?"
        file_name = Path(file).name if file else "?"
        self.info_label.config(
            text=f"Angemeldet als: {user_name}  |  Datei: {file_name}"
        )

        # Felder vorausfüllen wenn Kontext bereits gesetzt
        ctx = self.app_state.current_context
        if ctx:
            self.charge_var.set(ctx.charge)
            self.fa_var.set(ctx.fa)
            self.rolle_var.set(ctx.rolle)
        else:
            self.charge_var.set("")
            self.fa_var.set("")
            self.rolle_var.set("")

        self._first_entry.focus_set()

    def _check_fields(self, *_args) -> None:
        filled = all(
            var.get().strip()
            for var in (self.charge_var, self.fa_var, self.rolle_var)
        )
        self.next_btn.config(state="normal" if filled else "disabled")

    def _go_next(self) -> None:
        ctx = ContextInfo(
            charge=self.charge_var.get().strip(),
            fa=self.fa_var.get().strip(),
            rolle=self.rolle_var.get().strip(),
        )
        self.app_state.current_context = ctx

        if self.app_state.audit:
            self.app_state.audit.log(
                "context_set",
                user=self.app_state.current_user.user_id if self.app_state.current_user else None,
                file=str(self.app_state.current_file) if self.app_state.current_file else None,
                context={"charge": ctx.charge, "fa": ctx.fa, "rolle": ctx.rolle},
            )

        self.on_navigate("form")

    def _change_file(self) -> None:
        self.app_state.reset_file()
        self.on_navigate("file_select")

    def _logout(self) -> None:
        self.app_state.reset_user()
        self.on_navigate("login")
