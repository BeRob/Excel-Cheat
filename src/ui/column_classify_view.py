"""Spalten-Zuordnung: Feste Werte vs. Messwerte per Dual-Listbox."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from pathlib import Path

from src.config.settings import AUTO_COLUMNS, DEFAULT_PERSISTENT_COLUMNS
from src.config.file_config import load_column_config, save_column_config
from src.ui.base_view import BaseView
from src.ui.theme import COLORS, FONTS


class ColumnClassifyView(BaseView):
    """Bildschirm zur Zuordnung von Spalten als feste Werte oder Messwerte."""

    def __init__(self, parent, app_state, on_navigate):
        super().__init__(parent, app_state, on_navigate)
        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

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
        ttk.Label(self, text="Spalten zuordnen", style="Subtitle.TLabel").grid(
            row=1, column=0, pady=(10, 5)
        )

        # --- Auto-Spalten Info ---
        auto_text = ", ".join(AUTO_COLUMNS)
        ttk.Label(
            self,
            text=f"Automatische Spalten (nicht verschiebbar): {auto_text}",
            foreground=COLORS["text_secondary"],
            font=FONTS["small"],
        ).grid(row=2, column=0, pady=(0, 5))

        # --- Dual-Listbox ---
        list_container = ttk.Frame(self)
        list_container.grid(row=3, column=0, sticky="nsew", padx=30, pady=5)
        list_container.columnconfigure(0, weight=1)
        list_container.columnconfigure(2, weight=1)
        list_container.rowconfigure(1, weight=1)

        # Linke Liste: Feste Werte
        ttk.Label(list_container, text="Feste Werte", style="Subtitle.TLabel").grid(
            row=0, column=0, pady=(0, 5)
        )
        self.persistent_listbox = tk.Listbox(
            list_container,
            selectmode="extended",
            font=FONTS["body"],
            bg=COLORS["background"],
            fg=COLORS["text_primary"],
            selectbackground=COLORS["accent"],
            selectforeground=COLORS["text_on_primary"],
            relief="solid",
            borderwidth=1,
        )
        self.persistent_listbox.grid(row=1, column=0, sticky="nsew", padx=(0, 5))

        # Transfer-Buttons
        btn_col = ttk.Frame(list_container)
        btn_col.grid(row=1, column=1, padx=10)

        ttk.Button(btn_col, text="\u2192", width=4, command=self._move_right).pack(pady=5)
        ttk.Button(btn_col, text="\u2190", width=4, command=self._move_left).pack(pady=5)

        # Rechte Liste: Messwerte
        ttk.Label(list_container, text="Messwerte", style="Subtitle.TLabel").grid(
            row=0, column=2, pady=(0, 5)
        )
        self.measurement_listbox = tk.Listbox(
            list_container,
            selectmode="extended",
            font=FONTS["body"],
            bg=COLORS["background"],
            fg=COLORS["text_primary"],
            selectbackground=COLORS["accent"],
            selectforeground=COLORS["text_on_primary"],
            relief="solid",
            borderwidth=1,
        )
        self.measurement_listbox.grid(row=1, column=2, sticky="nsew", padx=(5, 0))

        # --- Info/Error ---
        self.error_var = tk.StringVar()
        self.error_label = ttk.Label(self, textvariable=self.error_var, style="Warning.TLabel")
        self.error_label.grid(row=4, column=0, pady=5)

        # --- Weiter-Button ---
        self.next_btn = ttk.Button(
            self, text="Weiter", command=self._go_next, style="Accent.TButton"
        )
        self.next_btn.grid(row=5, column=0, pady=(5, 15))

    def on_show(self) -> None:
        user = self.app_state.current_user
        file = self.app_state.current_file
        user_name = user.display_name if user else "?"
        file_name = Path(file).name if file else "?"
        sheet = self.app_state.current_sheet or "?"
        self.info_label.config(
            text=f"Angemeldet als: {user_name}  |  Datei: {file_name} / {sheet}"
        )

        # Alle Headers ohne Auto-Spalten
        auto_set = set(AUTO_COLUMNS)
        available = [h for h in self.app_state.current_headers if h not in auto_set]

        # Gespeicherte Config laden
        persistent = []
        measurement = []
        saved = None
        if self.app_state.current_file and self.app_state.current_sheet:
            saved = load_column_config(
                self.app_state.current_file, self.app_state.current_sheet
            )

        if saved:
            saved_persistent = saved.get("persistent", [])
            saved_measurement = saved.get("measurement", [])
            # Pruefen ob gespeicherte Headers noch aktuell sind
            saved_all = set(saved_persistent + saved_measurement)
            available_set = set(available)
            if saved_all == available_set:
                persistent = saved_persistent
                measurement = saved_measurement
            else:
                # Headers haben sich geaendert, Fallback auf Defaults
                self.error_var.set(
                    "Spalten haben sich geändert. Zuordnung wurde zurückgesetzt."
                )
                persistent, measurement = self._apply_defaults(available)
        else:
            persistent, measurement = self._apply_defaults(available)

        # Listen fuellen
        self.persistent_listbox.delete(0, "end")
        for h in persistent:
            self.persistent_listbox.insert("end", h)

        self.measurement_listbox.delete(0, "end")
        for h in measurement:
            self.measurement_listbox.insert("end", h)

        self._update_next_state()

    def _apply_defaults(self, available: list[str]) -> tuple[list[str], list[str]]:
        """Wendet Default-Zuordnung an."""
        default_set = set(DEFAULT_PERSISTENT_COLUMNS)
        persistent = [h for h in available if h in default_set]
        measurement = [h for h in available if h not in default_set]
        return persistent, measurement

    def _move_right(self) -> None:
        """Verschiebt selektierte Elemente von Feste Werte nach Messwerte."""
        selected = list(self.persistent_listbox.curselection())
        if not selected:
            return
        items = [self.persistent_listbox.get(i) for i in selected]
        for i in reversed(selected):
            self.persistent_listbox.delete(i)
        for item in items:
            self.measurement_listbox.insert("end", item)
        self.error_var.set("")
        self._update_next_state()

    def _move_left(self) -> None:
        """Verschiebt selektierte Elemente von Messwerte nach Feste Werte."""
        selected = list(self.measurement_listbox.curselection())
        if not selected:
            return
        items = [self.measurement_listbox.get(i) for i in selected]
        for i in reversed(selected):
            self.measurement_listbox.delete(i)
        for item in items:
            self.persistent_listbox.insert("end", item)
        self.error_var.set("")
        self._update_next_state()

    def _update_next_state(self) -> None:
        """Aktiviert/deaktiviert Weiter-Button."""
        count = self.measurement_listbox.size()
        if count == 0:
            self.next_btn.config(state="disabled")
            self.error_var.set("Mindestens eine Messwert-Spalte erforderlich.")
        else:
            self.next_btn.config(state="normal")
            if not self.error_var.get().startswith("Spalten haben sich"):
                self.error_var.set("")

    def _go_next(self) -> None:
        persistent = list(self.persistent_listbox.get(0, "end"))
        measurement = list(self.measurement_listbox.get(0, "end"))

        # In AppState speichern
        self.app_state.persistent_headers = persistent
        self.app_state.measurement_headers = measurement

        # Config persistent speichern
        if self.app_state.current_file and self.app_state.current_sheet:
            save_column_config(
                self.app_state.current_file,
                self.app_state.current_sheet,
                persistent,
                measurement,
            )

        if self.app_state.audit:
            self.app_state.audit.log(
                "columns_classified",
                user=self.app_state.current_user.user_id if self.app_state.current_user else None,
                file=str(self.app_state.current_file),
                details={
                    "persistent": persistent,
                    "measurement": measurement,
                },
            )

        self.on_navigate("context")

    def _change_file(self) -> None:
        self.app_state.reset_file()
        self.on_navigate("file_select")

    def _logout(self) -> None:
        self.app_state.reset_user()
        self.on_navigate("login")
