"""Review-Dialog: prüfen und bestätigen vor dem Schreiben."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import Callable, TYPE_CHECKING
from pathlib import Path

from src.domain.state import AppState
from src.domain.validation import validate_measurements
from src.ui.theme import COLORS

if TYPE_CHECKING:
    from src.config.process_config import FieldDef


class ReviewDialog(tk.Toplevel):
    """Modaler Dialog zur Kontrolle der Messwerte vor dem Speichern."""

    def __init__(
        self,
        parent: tk.Widget,
        app_state: AppState,
        raw_values: dict[str, str],
        on_confirm: Callable[[dict[str, float | str | None]], None],
        field_defs: list[FieldDef] | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.raw_values = raw_values
        self.on_confirm = on_confirm
        self.field_defs = field_defs

        self.title("Prüfen und Senden")
        height = min(900, 420 + len(raw_values) * 32)
        self.geometry(f"1000x{height}")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self.validation = validate_measurements(raw_values, field_defs=field_defs)
        self._build_ui()

        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _build_ui(self) -> None:
        self.configure(bg=COLORS["background"])
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1, minsize=200)

        info_frame = ttk.LabelFrame(self, text="Prozess", padding=10)
        info_frame.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")

        product = self.app_state.selected_product
        process = self.app_state.selected_process
        shift = self.app_state.current_shift
        file = self.app_state.current_file

        product_name = product.display_name if product else "?"
        process_name = process.display_name if process else "?"
        file_name = Path(file).name if file else "?"

        ttk.Label(info_frame, text=f"Produkt: {product_name}").pack(anchor="w")
        ttk.Label(info_frame, text=f"Prozess: {process_name}  |  Schicht {shift}").pack(anchor="w")
        ttk.Label(info_frame, text=f"Datei: {file_name}").pack(anchor="w")

        ctx_frame = ttk.LabelFrame(self, text="Feste Werte", padding=10)
        ctx_frame.grid(row=1, column=0, padx=15, pady=5, sticky="ew")

        pv = self.app_state.persistent_values
        if pv:
            for header, value in pv.items():
                ttk.Label(ctx_frame, text=f"{header}: {value}").pack(anchor="w")
        else:
            ttk.Label(ctx_frame, text="Keine festen Werte.",
                      foreground=COLORS["text_secondary"]).pack(anchor="w")

        auto_frame = ttk.LabelFrame(self, text="Automatische Felder", padding=10)
        auto_frame.grid(row=2, column=0, padx=15, pady=5, sticky="ew")

        user = self.app_state.current_user
        ttk.Label(auto_frame,
                  text=f"Datum: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}").pack(anchor="w")
        ttk.Label(auto_frame,
                  text=f"Bearbeiter: {user.display_name if user else '?'}").pack(anchor="w")

        if process and process.row_group_size:
            nutzen = (self.app_state.row_group_counter % process.row_group_size) + 1
            ttk.Label(auto_frame,
                      text=f"Nutzen: {nutzen} von {process.row_group_size}").pack(anchor="w")

        values_frame = ttk.LabelFrame(self, text="Messwerte", padding=10)
        values_frame.grid(row=3, column=0, padx=15, pady=5, sticky="nsew")
        values_frame.columnconfigure(0, weight=1)
        values_frame.rowconfigure(0, weight=1)

        canvas = tk.Canvas(values_frame, highlightthickness=0, bg=COLORS["background"])
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

        fd_map: dict[str, FieldDef] = {}
        if self.field_defs:
            for fd in self.field_defs:
                fd_map[fd.display_name] = fd

        scroll_frame.columnconfigure(0, weight=0)
        scroll_frame.columnconfigure(1, weight=0)
        scroll_frame.columnconfigure(2, weight=0)
        scroll_frame.columnconfigure(3, weight=1)

        error_set = {e.split(":")[0] for e in self.validation.errors}
        warning_set = set()
        for w in self.validation.warnings:
            # Unterstützt sowohl "Feld ist leer" als auch "Feld: Wert liegt unter ..."
            if ":" in w:
                warning_set.add(w.split(":")[0])
            else:
                warning_set.add(w.split(" ")[0])

        for i, (header, raw_val) in enumerate(self.raw_values.items()):
            norm_val = self.validation.normalized_values.get(header)
            fd = fd_map.get(header)

            if header in error_set:
                fg = COLORS["error"]
                status = "Fehler"
            elif header in warning_set:
                fg = COLORS["warning"]
                status = "Warnung"
            else:
                fg = COLORS["success"]
                status = str(norm_val) if norm_val is not None else ""

            ttk.Label(scroll_frame, text=f"{header}:", foreground=fg).grid(
                row=i, column=0, sticky="w", padx=(5, 10), pady=2
            )
            ttk.Label(scroll_frame, text=raw_val or "(leer)", foreground=fg).grid(
                row=i, column=1, sticky="w", padx=(0, 10), pady=2
            )

            spec_text = ""
            if fd and fd.spec_min is not None and fd.spec_max is not None:
                spec_text = f"[{fd.spec_min}-{fd.spec_max}]"
            ttk.Label(scroll_frame, text=spec_text,
                      foreground=COLORS["text_secondary"]).grid(
                row=i, column=2, sticky="w", padx=(0, 10), pady=2
            )

            ttk.Label(scroll_frame, text=status, foreground=fg).grid(
                row=i, column=3, sticky="w", pady=2
            )

        summary_text = (
            f"{len(self.validation.warnings)} Warnung(en), "
            f"{len(self.validation.errors)} Fehler"
        )
        if self.validation.has_errors:
            summary_style = "Error.TLabel"
        elif self.validation.warnings:
            summary_style = "Warning.TLabel"
        else:
            summary_style = "Success.TLabel"
        ttk.Label(self, text=summary_text, style=summary_style).grid(
            row=4, column=0, pady=5
        )

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
            style="Accent.TButton",
        )
        self.send_btn.pack(side="left", padx=10)

    def _confirm(self) -> None:
        self.on_confirm(self.validation.normalized_values)
        self.destroy()

    def _cancel(self) -> None:
        self.destroy()
