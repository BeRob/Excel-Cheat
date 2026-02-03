"""Dynamische Messwertmaske mit scrollbarem Eingabeformular."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

from src.config.settings import CONTEXT_COLUMNS, AUTO_COLUMNS
from src.domain.state import AppState
from src.domain.validation import validate_measurements
from src.excel.writer import write_measurement_row
from src.ui.base_view import BaseView
from src.ui.review_dialog import ReviewDialog


class FormView(BaseView):
    """Bildschirm zur Erfassung von Messwerten."""

    def __init__(self, parent, app_state, on_navigate):
        super().__init__(parent, app_state, on_navigate)
        self.field_vars: dict[str, tk.StringVar] = {}
        self._last_headers: list[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # --- Obere Leiste ---
        top_bar = ttk.Frame(self)
        top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        top_bar.columnconfigure(0, weight=1)

        self.info_label = ttk.Label(top_bar, text="", wraplength=500)
        self.info_label.grid(row=0, column=0, sticky="w")

        btn_frame = ttk.Frame(top_bar)
        btn_frame.grid(row=0, column=1)
        ttk.Button(btn_frame, text="Kontext ändern", command=self._change_context).pack(
            side="left", padx=(5, 0)
        )
        ttk.Button(btn_frame, text="Datei wechseln", command=self._change_file).pack(
            side="left", padx=(5, 0)
        )
        ttk.Button(btn_frame, text="Abmelden", command=self._logout).pack(
            side="left", padx=(5, 0)
        )

        # --- Titel ---
        ttk.Label(self, text="Messwerte erfassen", font=("", 14, "bold")).grid(
            row=1, column=0, pady=(5, 5)
        )

        # --- Scrollbarer Bereich ---
        scroll_container = ttk.Frame(self)
        scroll_container.grid(row=2, column=0, sticky="nsew", padx=40, pady=5)
        scroll_container.columnconfigure(0, weight=1)
        scroll_container.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(scroll_container, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            scroll_container, orient="vertical", command=self.canvas.yview
        )
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw"
        )

        # Canvas-Breite an Container anpassen
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width),
        )

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # Mausrad-Scrolling
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

        # --- Status-Zeile ---
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(self, textvariable=self.status_var, foreground="green")
        self.status_label.grid(row=3, column=0, pady=5)

        # --- Untere Leiste ---
        bottom_bar = ttk.Frame(self)
        bottom_bar.grid(row=4, column=0, pady=(5, 15))

        ttk.Button(bottom_bar, text="Felder leeren", command=self._clear_fields).pack(
            side="left", padx=10
        )
        ttk.Button(bottom_bar, text="Speichern", command=self._save).pack(
            side="left", padx=10
        )

    def _bind_mousewheel(self, event) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event) -> None:
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_show(self) -> None:
        # Info-Leiste aktualisieren
        user = self.app_state.current_user
        ctx = self.app_state.current_context
        file = self.app_state.current_file

        user_name = user.display_name if user else "?"
        file_name = Path(file).name if file else "?"
        sheet = self.app_state.current_sheet or "?"
        ctx_text = (
            f"{ctx.charge} | {ctx.fa} | {ctx.rolle}" if ctx else "?"
        )

        self.info_label.config(
            text=f"Benutzer: {user_name}  |  Datei: {file_name} / {sheet}  |  Kontext: {ctx_text}"
        )

        # Felder neu generieren wenn sich Header geändert haben
        current_headers = self.app_state.measurement_headers
        if current_headers != self._last_headers:
            self._generate_fields(current_headers)
            self._last_headers = list(current_headers)

        self.status_var.set("")

    def _generate_fields(self, headers: list[str]) -> None:
        """Erzeugt Eingabefelder dynamisch aus den Header-Namen."""
        # Alte Felder entfernen
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.field_vars.clear()

        self.scrollable_frame.columnconfigure(1, weight=1)

        first_entry = None
        for i, header in enumerate(headers):
            ttk.Label(self.scrollable_frame, text=f"{header}:").grid(
                row=i, column=0, sticky="w", pady=5, padx=(10, 15)
            )
            var = tk.StringVar()
            entry = ttk.Entry(self.scrollable_frame, textvariable=var, width=25)
            entry.grid(row=i, column=1, sticky="w", pady=5, padx=(0, 10))
            self.field_vars[header] = var
            if i == 0:
                first_entry = entry

        if first_entry:
            first_entry.focus_set()

    def _clear_fields(self) -> None:
        for var in self.field_vars.values():
            var.set("")
        self.status_var.set("")
        # Fokus auf erstes Feld
        children = self.scrollable_frame.winfo_children()
        for child in children:
            if isinstance(child, ttk.Entry):
                child.focus_set()
                break

    def _save(self) -> None:
        """Öffnet den Review-Dialog vor dem Schreiben."""
        raw_values = {header: var.get() for header, var in self.field_vars.items()}

        ReviewDialog(
            parent=self,
            app_state=self.app_state,
            raw_values=raw_values,
            on_confirm=self._do_write,
        )

    def _do_write(self, normalized_values: dict[str, float | None]) -> None:
        """Schreibt die Messwerte in die Excel-Datei."""
        if self.app_state.audit:
            self.app_state.audit.log(
                "write_attempt",
                user=self.app_state.current_user.user_id if self.app_state.current_user else None,
                file=str(self.app_state.current_file),
                context={
                    "charge": self.app_state.current_context.charge,
                    "fa": self.app_state.current_context.fa,
                    "rolle": self.app_state.current_context.rolle,
                } if self.app_state.current_context else None,
                details={"measurement_count": len(normalized_values)},
            )

        result = write_measurement_row(
            filepath=self.app_state.current_file,
            sheet_name=self.app_state.current_sheet,
            header_column_map=dict(self.app_state.header_column_map),
            context=self.app_state.current_context,
            user=self.app_state.current_user,
            measurements=normalized_values,
        )

        if result.success:
            # header_column_map aktualisieren falls neue Spalten erstellt
            if result.columns_created:
                # Re-read headers to get updated map
                from src.excel.reader import read_excel_headers
                from src.config.settings import HEADER_ROW
                updated = read_excel_headers(
                    self.app_state.current_file,
                    sheet_name=self.app_state.current_sheet,
                    header_row=HEADER_ROW,
                )
                if not updated.errors:
                    self.app_state.header_column_map = updated.header_column_map
                    self.app_state.current_headers = updated.headers

            self.status_var.set(f"Zeile {result.row_number} erfolgreich geschrieben.")
            self.status_label.config(foreground="green")
            self._clear_fields()

            if self.app_state.audit:
                self.app_state.audit.log(
                    "write_success",
                    user=self.app_state.current_user.user_id if self.app_state.current_user else None,
                    file=str(self.app_state.current_file),
                    context={
                        "charge": self.app_state.current_context.charge,
                        "fa": self.app_state.current_context.fa,
                        "rolle": self.app_state.current_context.rolle,
                    } if self.app_state.current_context else None,
                    details={
                        "row": result.row_number,
                        "columns_created": result.columns_created,
                    },
                )
        else:
            messagebox.showerror("Fehler beim Schreiben", result.error)
            self.status_var.set(f"Fehler: {result.error}")
            self.status_label.config(foreground="red")

            if self.app_state.audit:
                self.app_state.audit.log(
                    "write_fail",
                    user=self.app_state.current_user.user_id if self.app_state.current_user else None,
                    file=str(self.app_state.current_file),
                    context={
                        "charge": self.app_state.current_context.charge,
                        "fa": self.app_state.current_context.fa,
                        "rolle": self.app_state.current_context.rolle,
                    } if self.app_state.current_context else None,
                    details={"error": result.error},
                )

    def _change_context(self) -> None:
        self.on_navigate("context")

    def _change_file(self) -> None:
        self.app_state.reset_file()
        self.on_navigate("file_select")

    def _logout(self) -> None:
        self.app_state.reset_user()
        self.on_navigate("login")
