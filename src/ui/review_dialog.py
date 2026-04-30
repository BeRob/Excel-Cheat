"""Review-Dialog: prüfen und bestätigen vor dem Schreiben."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import Callable, TYPE_CHECKING
from pathlib import Path

from src.domain.state import AppState
from src.domain.validation import validate_measurements, ValidationResult
from src.ui.theme import COLORS

if TYPE_CHECKING:
    from src.config.process_config import FieldDef


class ReviewDialog(tk.Toplevel):
    """Modaler Dialog zur Kontrolle der Messwerte vor dem Speichern.

    Zwei Modi:
    - Single-Nutzen: `raw_values` + `field_defs`. `on_confirm(normalized)` wird
      mit dem normalisierten Werte-Dict aufgerufen.
    - Multi-Nutzen: `shared_values` + `shared_field_defs` und `nutzen_values` +
      `nutzen_field_defs`. `on_confirm(shared_normalized, [nutzen_norm_1, …])`."""

    def __init__(
        self,
        parent: tk.Widget,
        app_state: AppState,
        on_confirm: Callable,
        # Single-Nutzen-Modus
        raw_values: dict[str, str] | None = None,
        field_defs: list["FieldDef"] | None = None,
        # Multi-Nutzen-Modus
        shared_values: dict[str, str] | None = None,
        shared_field_defs: list["FieldDef"] | None = None,
        nutzen_values: list[dict[str, str]] | None = None,
        nutzen_field_defs: list["FieldDef"] | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.on_confirm = on_confirm

        self._is_multi = nutzen_values is not None

        if self._is_multi:
            self.shared_values = shared_values or {}
            self.shared_field_defs = shared_field_defs or []
            self.nutzen_values = nutzen_values or []
            self.nutzen_field_defs = nutzen_field_defs or []
            self.shared_validation = validate_measurements(
                self.shared_values, field_defs=self.shared_field_defs,
            )
            self.nutzen_validations: list[ValidationResult] = [
                validate_measurements(nv, field_defs=self.nutzen_field_defs)
                for nv in self.nutzen_values
            ]
        else:
            self.raw_values = raw_values or {}
            self.field_defs = field_defs
            self.validation = validate_measurements(
                self.raw_values, field_defs=self.field_defs,
            )

        self.title("Prüfen und Senden")

        if self._is_multi:
            row_count = len(self.shared_values) + sum(
                len(nv) for nv in self.nutzen_values
            )
            height = min(1100, 480 + row_count * 26)
        else:
            height = min(1100, 480 + len(self.raw_values) * 30)
        self.geometry(f"720x{height}")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _has_errors(self) -> bool:
        if self._is_multi:
            if self.shared_validation.has_errors:
                return True
            return any(v.has_errors for v in self.nutzen_validations)
        return self.validation.has_errors

    def _total_warnings(self) -> int:
        if self._is_multi:
            return len(self.shared_validation.warnings) + sum(
                len(v.warnings) for v in self.nutzen_validations
            )
        return len(self.validation.warnings)

    def _total_errors(self) -> int:
        if self._is_multi:
            return len(self.shared_validation.errors) + sum(
                len(v.errors) for v in self.nutzen_validations
            )
        return len(self.validation.errors)

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

        if self._is_multi:
            self._render_multi_blocks(scroll_frame)
        else:
            self._render_value_block(
                scroll_frame, self.raw_values, self.field_defs or [],
                self.validation,
            )

        summary_text = (
            f"{self._total_warnings()} Warnung(en), "
            f"{self._total_errors()} Fehler"
        )
        if self._has_errors():
            summary_style = "Error.TLabel"
        elif self._total_warnings():
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
            state="normal" if not self._has_errors() else "disabled",
            style="Accent.TButton",
        )
        self.send_btn.pack(side="left", padx=10)

    def _render_multi_blocks(self, parent: tk.Widget) -> None:
        """Rendert im Multi-Nutzen-Modus: Gemeinsame Werte + pro Nutzen einen Block."""
        parent.columnconfigure(0, weight=1)
        row = 0

        if self.shared_values:
            block = ttk.LabelFrame(parent, text="Gemeinsame Werte", padding=8)
            block.grid(row=row, column=0, sticky="ew", padx=5, pady=(0, 6))
            block.columnconfigure(0, weight=1)
            inner = ttk.Frame(block)
            inner.pack(fill="x")
            self._render_value_block(
                inner, self.shared_values, self.shared_field_defs,
                self.shared_validation,
            )
            row += 1

        for i, (nv, val) in enumerate(zip(self.nutzen_values, self.nutzen_validations), 1):
            label_style = "Error.TLabel" if val.has_errors else (
                "Warning.TLabel" if val.warnings else "TLabel"
            )
            block = ttk.LabelFrame(parent, text=f"Nutzen {i}", padding=8)
            block.grid(row=row, column=0, sticky="ew", padx=5, pady=(0, 6))
            block.columnconfigure(0, weight=1)
            ttk.Label(
                block,
                text=f"{len(val.warnings)} Warnung(en), {len(val.errors)} Fehler",
                style=label_style,
            ).pack(anchor="w", pady=(0, 4))
            inner = ttk.Frame(block)
            inner.pack(fill="x")
            self._render_value_block(inner, nv, self.nutzen_field_defs, val)
            row += 1

    def _render_value_block(
        self,
        parent: tk.Widget,
        raw_values: dict[str, str],
        field_defs: list["FieldDef"],
        validation: ValidationResult,
    ) -> None:
        fd_map: dict[str, "FieldDef"] = {fd.display_name: fd for fd in field_defs}

        parent.columnconfigure(0, weight=0)
        parent.columnconfigure(1, weight=0)
        parent.columnconfigure(2, weight=0)
        parent.columnconfigure(3, weight=1)

        error_set = {e.split(":")[0] for e in validation.errors}
        warning_set = set()
        for w in validation.warnings:
            if ":" in w:
                warning_set.add(w.split(":")[0])
            else:
                warning_set.add(w.split(" ")[0])

        for i, (header, raw_val) in enumerate(raw_values.items()):
            norm_val = validation.normalized_values.get(header)
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

            ttk.Label(parent, text=f"{header}:", foreground=fg).grid(
                row=i, column=0, sticky="w", padx=(5, 10), pady=2
            )
            ttk.Label(parent, text=raw_val or "(leer)", foreground=fg).grid(
                row=i, column=1, sticky="w", padx=(0, 10), pady=2
            )

            spec_text = ""
            if fd and fd.spec_min is not None and fd.spec_max is not None:
                spec_text = f"[{fd.spec_min}-{fd.spec_max}]"
            elif fd and fd.spec_min is not None:
                spec_text = f"[≥{fd.spec_min}]"
            elif fd and fd.spec_max is not None:
                spec_text = f"[≤{fd.spec_max}]"
            ttk.Label(parent, text=spec_text,
                      foreground=COLORS["text_secondary"]).grid(
                row=i, column=2, sticky="w", padx=(0, 10), pady=2
            )

            ttk.Label(parent, text=status, foreground=fg).grid(
                row=i, column=3, sticky="w", pady=2
            )

    def _confirm(self) -> None:
        if self._is_multi:
            self.on_confirm(
                self.shared_validation.normalized_values,
                [v.normalized_values for v in self.nutzen_validations],
            )
        else:
            self.on_confirm(self.validation.normalized_values)
        self.destroy()

    def _cancel(self) -> None:
        self.destroy()
