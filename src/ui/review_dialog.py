"""Review-Dialog: Prüfen und Bestätigen vor dem Schreiben."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import Callable
from pathlib import Path

from src.domain.state import AppState
from src.domain.validation import validate_measurements, ValidationResult


class ReviewDialog(tk.Toplevel):
    """Modaler Dialog zur Prüfung der Messwerte vor dem Schreiben."""

    def __init__(
        self,
        parent: tk.Widget,
        app_state: AppState,
        raw_values: dict[str, str],
        on_confirm: Callable[[dict[str, float | None]], None],
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.raw_values = raw_values
        self.on_confirm = on_confirm

        self.title("Prüfen und Senden")
        self.geometry("550x500")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self.validation = validate_measurements(raw_values)
        self._build_ui()

        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        # --- Datei-Info ---
        info_frame = ttk.LabelFrame(self, text="Datei", padding=10)
        info_frame.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")

        file = self.app_state.current_file
        file_name = Path(file).name if file else "?"
        sheet = self.app_state.current_sheet or "?"
        ttk.Label(info_frame, text=f"Datei: {file_name}").pack(anchor="w")
        ttk.Label(info_frame, text=f"Arbeitsblatt: {sheet}").pack(anchor="w")

        # --- Kontext ---
        ctx_frame = ttk.LabelFrame(self, text="Kontext", padding=10)
        ctx_frame.grid(row=1, column=0, padx=15, pady=5, sticky="ew")

        ctx = self.app_state.current_context
        if ctx:
            ttk.Label(ctx_frame, text=f"Chargen-Nr: {ctx.charge}").pack(anchor="w")
            ttk.Label(ctx_frame, text=f"FA-Nr: {ctx.fa}").pack(anchor="w")
            ttk.Label(ctx_frame, text=f"Rolle: {ctx.rolle}").pack(anchor="w")

        # --- Auto-Felder ---
        auto_frame = ttk.LabelFrame(self, text="Automatische Felder", padding=10)
        auto_frame.grid(row=2, column=0, padx=15, pady=5, sticky="ew")

        user = self.app_state.current_user
        ttk.Label(auto_frame, text=f"Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}").pack(
            anchor="w"
        )
        ttk.Label(
            auto_frame,
            text=f"Mitarbeiter: {user.display_name if user else '?'}",
        ).pack(anchor="w")

        # --- Messwerte (scrollbar) ---
        values_frame = ttk.LabelFrame(self, text="Messwerte", padding=10)
        values_frame.grid(row=3, column=0, padx=15, pady=5, sticky="nsew")
        values_frame.columnconfigure(0, weight=1)
        values_frame.rowconfigure(0, weight=1)

        canvas = tk.Canvas(values_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(values_frame, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Messwerte anzeigen
        scroll_frame.columnconfigure(0, weight=0)
        scroll_frame.columnconfigure(1, weight=0)
        scroll_frame.columnconfigure(2, weight=1)

        error_set = {e.split(":")[0] for e in self.validation.errors}
        warning_set = {w.split(" ")[0] for w in self.validation.warnings}

        for i, (header, raw_val) in enumerate(self.raw_values.items()):
            norm_val = self.validation.normalized_values.get(header)

            # Farbe bestimmen
            if header in error_set:
                fg = "red"
                status = "Fehler"
            elif header in warning_set:
                fg = "#CC8800"
                status = "Leer"
            else:
                fg = "green"
                status = str(norm_val) if norm_val is not None else ""

            ttk.Label(scroll_frame, text=f"{header}:", foreground=fg).grid(
                row=i, column=0, sticky="w", padx=(5, 10), pady=2
            )
            ttk.Label(scroll_frame, text=raw_val or "(leer)", foreground=fg).grid(
                row=i, column=1, sticky="w", padx=(0, 10), pady=2
            )
            ttk.Label(scroll_frame, text=status, foreground=fg).grid(
                row=i, column=2, sticky="w", pady=2
            )

        # --- Zusammenfassung ---
        summary_text = f"{len(self.validation.warnings)} Warnung(en), {len(self.validation.errors)} Fehler"
        summary_fg = "red" if self.validation.has_errors else ("#CC8800" if self.validation.warnings else "green")
        ttk.Label(self, text=summary_text, foreground=summary_fg).grid(
            row=4, column=0, pady=5
        )

        # --- Buttons ---
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=5, column=0, pady=(5, 15))

        ttk.Button(btn_frame, text="Bearbeiten", command=self._cancel).pack(
            side="left", padx=10
        )

        self.send_btn = ttk.Button(
            btn_frame,
            text="Senden",
            command=self._confirm,
            state="normal" if not self.validation.has_errors else "disabled",
        )
        self.send_btn.pack(side="left", padx=10)

    def _confirm(self) -> None:
        self.on_confirm(self.validation.normalized_values)
        self.destroy()

    def _cancel(self) -> None:
        self.destroy()
