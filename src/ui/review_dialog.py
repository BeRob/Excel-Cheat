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


_REMARK_PLACEHOLDERS = {"", "n/a", "n.a.", "na", "-", "—", "–"}
_REMARK_FIELD_ID = "bemerkungen"
_REMARK_DISPLAY_NAME = "Bemerkungen"


def _remark_is_valid(value: str | None) -> bool:
    """Bemerkungen gilt als 'echt ausgefüllt', wenn es kein Placeholder ist.

    GMP-Anforderung: nicht ausgefüllte Felder werden via 'n/a' entwertet —
    semantisch identisch zu leer. Im Out-of-Spec-Fall muss eine reale
    Begründung stehen, sonst greift der Senden-Block."""
    if value is None:
        return False
    return value.strip().lower() not in _REMARK_PLACEHOLDERS


def _remark_display_name(field_defs: list["FieldDef"] | None) -> str:
    """Anzeigename des Bemerkungen-Felds, ermittelt über die Feld-id.

    Fallback auf den Standard-Anzeigenamen, falls kein Feld mit der id
    'bemerkungen' definiert ist — so funktioniert der OoS-Gate auch bei
    Prozessen mit abweichendem Anzeigenamen (z.B. "Bemerkung")."""
    for fd in field_defs or []:
        if fd.id == _REMARK_FIELD_ID:
            return fd.display_name
    return _REMARK_DISPLAY_NAME


def oos_blocked_sections_single(
    raw_values: dict[str, str],
    validation: ValidationResult,
    field_defs: list["FieldDef"] | None = None,
) -> list[str]:
    """Single-Nutzen-Gate: ["Messwerte"] wenn OoS ohne valide Bemerkung, sonst []."""
    remark_name = _remark_display_name(field_defs)
    if validation.oos_fields and not _remark_is_valid(raw_values.get(remark_name)):
        return ["Messwerte"]
    return []


def oos_blocked_sections_multi(
    nutzen_values: list[dict[str, str]],
    nutzen_validations: list[ValidationResult],
    shared_validation: ValidationResult,
    nutzen_field_defs: list["FieldDef"] | None = None,
) -> list[str]:
    """Multi-Nutzen-Gate: Liste der Sektionen mit OoS ohne valide Bemerkung.

    "Gemeinsame Werte" wird nur dann gelistet, wenn ein OoS-Feld zu den
    gemeinsamen Werten gehört — diese Sektion hat keine eigene Bemerkung,
    also wird der Bemerkungen-Wert der Nutzen-Sektionen bewertet
    (Approximation: wenn min. eine Nutzen-Bemerkung valide ist, gilt der
    gemeinsame OoS als begründet)."""
    remark_name = _remark_display_name(nutzen_field_defs)
    bad: list[str] = []
    for i, (raw, val) in enumerate(zip(nutzen_values, nutzen_validations), 1):
        if not val.oos_fields:
            continue
        if not _remark_is_valid(raw.get(remark_name)):
            bad.append(f"Nutzen {i}")
    if shared_validation.oos_fields:
        any_valid = any(
            _remark_is_valid(nv.get(remark_name)) for nv in nutzen_values
        )
        if not any_valid:
            bad.append("Gemeinsame Werte")
    return bad


def collect_oos_details(
    validation: ValidationResult,
    field_defs: list["FieldDef"] | None,
) -> list[dict]:
    """OoS-Felder mit Wert und Spec-Grenzen — für den Audit-Trail.

    Ein OOS_BLOCKED-Event ohne die betroffenen Werte wäre für einen Auditor
    nicht nachvollziehbar (welcher Wert verletzte welche Grenze?)."""
    fd_map = {fd.display_name: fd for fd in field_defs or []}
    details: list[dict] = []
    for name in sorted(validation.oos_fields):
        fd = fd_map.get(name)
        details.append({
            "field": name,
            "value": validation.normalized_values.get(name),
            "spec_min": fd.spec_min if fd else None,
            "spec_max": fd.spec_max if fd else None,
        })
    return details


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
        on_cancel: Callable | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self._oos_blocked_sections: list[str] = []

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
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._fit_to_content()

        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _fit_to_content(self) -> None:
        """Fenster an den Inhalt anpassen, auf die Bildschirmgröße begrenzen und
        zentrieren. Der Messwerte-Bereich scrollt — so bleiben Zusammenfassung
        und der Senden-Button immer sichtbar (nicht mehr unten abgeschnitten)."""
        self.update_idletasks()
        req_w = max(720, self.winfo_reqwidth())
        req_h = self.winfo_reqheight()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        w = min(req_w, screen_w - 80)
        h = min(req_h, screen_h - 100)
        x = max(0, (screen_w - w) // 2)
        y = max(0, (screen_h - h) // 2 - 20)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(560, 360)

    def _has_errors(self) -> bool:
        if self._is_multi:
            if self.shared_validation.has_errors:
                return True
            return any(v.has_errors for v in self.nutzen_validations)
        return self.validation.has_errors

    def _oos_without_remark(self) -> list[str]:
        """Liste betroffener Sektions-Labels, die OoS-Werte haben aber
        keine valide Bemerkung tragen (Logik in den Modul-Funktionen
        oos_blocked_sections_single/_multi — dort ohne Tk testbar)."""
        if self._is_multi:
            return oos_blocked_sections_multi(
                self.nutzen_values, self.nutzen_validations,
                self.shared_validation, self.nutzen_field_defs,
            )
        return oos_blocked_sections_single(
            self.raw_values, self.validation, self.field_defs,
        )

    def _collect_oos_details(self) -> dict[str, list[dict]]:
        """OoS-Felder je Sektion (Werte + Grenzen) für den Audit-Trail."""
        details: dict[str, list[dict]] = {}
        if self._is_multi:
            for i, val in enumerate(self.nutzen_validations, 1):
                if val.oos_fields:
                    details[f"Nutzen {i}"] = collect_oos_details(
                        val, self.nutzen_field_defs,
                    )
            if self.shared_validation.oos_fields:
                details["Gemeinsame Werte"] = collect_oos_details(
                    self.shared_validation, self.shared_field_defs,
                )
        else:
            if self.validation.oos_fields:
                details["Messwerte"] = collect_oos_details(
                    self.validation, self.field_defs,
                )
        return details

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
        self.rowconfigure(3, weight=1, minsize=140)

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
                      style="Hint.TLabel").pack(anchor="w")

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

        # Messwerte-Bereich an den Inhalt anpassen (bis zu einem Maximum),
        # darüber hinaus scrollen — damit Zusammenfassung und Senden-Button
        # immer ins Fenster passen.
        scroll_frame.update_idletasks()
        canvas.configure(height=min(scroll_frame.winfo_reqheight(), 380))

        oos_blocked = self._oos_without_remark()
        if oos_blocked:
            banner = (
                "Außerhalb der Spezifikation — Bemerkung nötig "
                "(‚n/a' genügt nicht). Betrifft: "
                + ", ".join(oos_blocked) + "."
            )
            ttk.Label(self, text=banner, style="Error.TLabel",
                      wraplength=680).grid(row=4, column=0, pady=(5, 0), padx=15)

        summary_text = (
            f"{self._total_warnings()} Warnung(en), "
            f"{self._total_errors()} Fehler"
        )
        if self._has_errors() or oos_blocked:
            summary_style = "Error.TLabel"
        elif self._total_warnings():
            summary_style = "Warning.TLabel"
        else:
            summary_style = "Success.TLabel"
        ttk.Label(self, text=summary_text, style=summary_style).grid(
            row=5, column=0, pady=5
        )

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=6, column=0, pady=(5, 15))

        ttk.Button(btn_frame, text="Bearbeiten", command=self._cancel).pack(
            side="left", padx=10
        )

        send_enabled = not self._has_errors() and not oos_blocked
        self.send_btn = ttk.Button(
            btn_frame,
            text="Senden",
            command=self._confirm,
            state="normal" if send_enabled else "disabled",
            style="Accent.TButton",
        )
        self.send_btn.pack(side="left", padx=10)

        # Hinweis fürs Audit-Log, dass der Senden-Button gesperrt wurde
        self._oos_blocked_sections = oos_blocked

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
            ttk.Label(parent, text=spec_text, style="Hint.TLabel").grid(
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
        if self.on_cancel is not None:
            try:
                self.on_cancel(
                    list(self._oos_blocked_sections),
                    self._collect_oos_details(),
                )
            except Exception:
                pass
        self.destroy()
