"""Kontext-Bildschirm: Dynamische feste Werte setzen."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from pathlib import Path

from src.ui.base_view import BaseView
from src.ui.theme import COLORS


class ContextView(BaseView):
    """Bildschirm zum Setzen der festen Werte (persistent headers)."""

    def __init__(self, parent, app_state, on_navigate):
        super().__init__(parent, app_state, on_navigate)
        self.field_vars: dict[str, tk.StringVar] = {}
        self._field_entries: list[ttk.Entry] = []
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
        ttk.Button(btn_frame, text="Zuordnung ändern", command=self._change_classify).pack(
            side="left", padx=(5, 0)
        )
        ttk.Button(btn_frame, text="Datei wechseln", command=self._change_file).pack(
            side="left", padx=(5, 0)
        )
        ttk.Button(btn_frame, text="Abmelden", command=self._logout).pack(
            side="left", padx=(5, 0)
        )

        # --- Titel ---
        ttk.Label(self, text="Feste Werte setzen", style="Subtitle.TLabel").grid(
            row=1, column=0, pady=(10, 5)
        )

        # --- Dynamischer Formular-Container ---
        self.form_frame = ttk.Frame(self)
        self.form_frame.grid(row=2, column=0, padx=40, pady=10)

        # --- Hinweis bei 0 festen Werten ---
        self.no_fields_label = ttk.Label(
            self,
            text="Keine festen Werte definiert. Sie können direkt weiter zur Messung.",
            foreground=COLORS["text_secondary"],
        )
        self.no_fields_label.grid(row=3, column=0, padx=40, pady=5)
        self.no_fields_label.grid_remove()

        # --- Weiter-Button ---
        self.next_btn = ttk.Button(
            self, text="Weiter zur Messung", command=self._go_next,
            style="Accent.TButton",
        )
        self.next_btn.grid(row=4, column=0, pady=15)

    def on_show(self) -> None:
        # Info-Leiste aktualisieren
        user = self.app_state.current_user
        file = self.app_state.current_file
        user_name = user.display_name if user else "?"
        file_name = Path(file).name if file else "?"
        self.info_label.config(
            text=f"Angemeldet als: {user_name}  |  Datei: {file_name}"
        )

        # Dynamische Felder generieren
        self._generate_fields()

    def _generate_fields(self) -> None:
        # Alte Felder entfernen
        for widget in self.form_frame.winfo_children():
            widget.destroy()
        self.field_vars.clear()
        self._field_entries.clear()

        headers = self.app_state.persistent_headers

        if not headers:
            self.no_fields_label.grid()
            self.next_btn.config(state="normal")
            return

        self.no_fields_label.grid_remove()

        for i, header in enumerate(headers):
            ttk.Label(self.form_frame, text=f"{header}:").grid(
                row=i, column=0, sticky="w", pady=5, padx=(0, 10)
            )
            var = tk.StringVar()
            # Vorausfuellen wenn bereits Werte vorhanden
            if header in self.app_state.persistent_values:
                var.set(self.app_state.persistent_values[header])
            var.trace_add("write", self._check_fields)
            entry = ttk.Entry(self.form_frame, textvariable=var, width=30)
            entry.grid(row=i, column=1, pady=5)
            self.field_vars[header] = var
            self._field_entries.append(entry)

        if self._field_entries:
            self._field_entries[0].focus_set()

        self._check_fields()

    def _check_fields(self, *_args) -> None:
        if not self.field_vars:
            self.next_btn.config(state="normal")
            return
        filled = all(var.get().strip() for var in self.field_vars.values())
        self.next_btn.config(state="normal" if filled else "disabled")

    def _go_next(self) -> None:
        self.app_state.persistent_values = {
            h: var.get().strip() for h, var in self.field_vars.items()
        }

        if self.app_state.audit:
            self.app_state.audit.log(
                "context_set",
                user=self.app_state.current_user.user_id if self.app_state.current_user else None,
                file=str(self.app_state.current_file) if self.app_state.current_file else None,
                context=dict(self.app_state.persistent_values),
            )

        self.on_navigate("form")

    def _change_classify(self) -> None:
        self.on_navigate("column_classify")

    def _change_file(self) -> None:
        self.app_state.reset_file()
        self.on_navigate("file_select")

    def _logout(self) -> None:
        self.app_state.reset_user()
        self.on_navigate("login")
