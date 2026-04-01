"""Dynamische Messwertmaske mit scrollbarem Eingabeformular."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from collections import deque
from datetime import datetime

from src.config.process_config import (
    get_measurement_fields,
    get_per_measurement_context_fields,
    get_auto_fields,
    FieldDef,
)
from src.domain.validation import validate_measurements, parse_numeric
from src.excel.writer import write_measurement_row
from src.ui.base_view import BaseView
from src.ui.review_dialog import ReviewDialog
from src.ui.theme import COLORS


class FormView(BaseView):
    """Bildschirm zur Erfassung von Messwerten."""

    def __init__(self, parent, app_state, on_navigate):
        super().__init__(parent, app_state, on_navigate)
        self.field_vars: dict[str, tk.StringVar] = {}
        self._field_defs: list[FieldDef] = []
        self._last_fields_key: str = ""
        self._history: deque = deque(maxlen=10)
        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(5, weight=0)

        # --- Obere Leiste ---
        top_bar = ttk.Frame(self)
        top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        top_bar.columnconfigure(0, weight=1)

        self.info_label = ttk.Label(top_bar, text="", wraplength=500)
        self.info_label.grid(row=0, column=0, sticky="w")

        btn_frame = ttk.Frame(top_bar)
        btn_frame.grid(row=0, column=1)

        self.layout_btn = ttk.Button(btn_frame, text="Layout: Vertikal",
                                     command=self._toggle_layout)
        self.layout_btn.pack(side="left", padx=(5, 0))

        ttk.Button(btn_frame, text="Kontext aendern",
                   command=self._change_context).pack(side="left", padx=(5, 0))
        ttk.Button(btn_frame, text="Prozess wechseln",
                   command=self._change_process).pack(side="left", padx=(5, 0))
        ttk.Button(btn_frame, text="Abmelden",
                   command=self._logout).pack(side="left", padx=(5, 0))

        # --- Titel + Row-Group Anzeige ---
        title_frame = ttk.Frame(self)
        title_frame.grid(row=1, column=0, pady=(5, 5))
        ttk.Label(title_frame, text="Messwerte erfassen",
                  style="Subtitle.TLabel").pack(side="left")
        self.group_label = ttk.Label(title_frame, text="", foreground=COLORS["accent"])
        self.group_label.pack(side="left", padx=(15, 0))

        # --- Scrollbarer Bereich ---
        scroll_container = ttk.Frame(self)
        scroll_container.grid(row=2, column=0, sticky="nsew", padx=40, pady=5)
        scroll_container.columnconfigure(0, weight=1)
        scroll_container.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            scroll_container, highlightthickness=0, bg=COLORS["background"]
        )
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
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width),
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

        # --- Status-Zeile ---
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(self, textvariable=self.status_var,
                                      style="Success.TLabel")
        self.status_label.grid(row=3, column=0, pady=5)

        # --- Untere Leiste ---
        bottom_bar = ttk.Frame(self)
        bottom_bar.grid(row=4, column=0, pady=(5, 10))

        ttk.Button(bottom_bar, text="Felder leeren",
                   command=self._clear_fields).pack(side="left", padx=10)
        ttk.Button(bottom_bar, text="Speichern", command=self._save,
                   style="Accent.TButton").pack(side="left", padx=10)

        # --- History-Bereich ---
        history_frame = ttk.LabelFrame(self, text="Letzte 10 Messungen", padding=10)
        history_frame.grid(row=5, column=0, sticky="ew", padx=40, pady=(5, 15))
        history_frame.columnconfigure(0, weight=1)

        tree_container = ttk.Frame(history_frame)
        tree_container.pack(fill="both", expand=True)
        tree_container.columnconfigure(0, weight=1)
        tree_container.rowconfigure(0, weight=1)

        self.history_tree = ttk.Treeview(
            tree_container,
            columns=("zeit", "kontext", "werte"),
            show="headings",
            height=6,
        )
        self.history_tree.heading("zeit", text="Zeit")
        self.history_tree.heading("kontext", text="Kontext")
        self.history_tree.heading("werte", text="Messwerte")
        self.history_tree.column("zeit", width=150, minwidth=100)
        self.history_tree.column("kontext", width=200, minwidth=150)
        self.history_tree.column("werte", width=300, minwidth=200)

        history_scrollbar = ttk.Scrollbar(
            tree_container, orient="vertical", command=self.history_tree.yview
        )
        self.history_tree.configure(yscrollcommand=history_scrollbar.set)
        self.history_tree.grid(row=0, column=0, sticky="nsew")
        history_scrollbar.grid(row=0, column=1, sticky="ns")

    def _bind_mousewheel(self, event) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event) -> None:
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_show(self) -> None:
        process = self.app_state.selected_process
        product = self.app_state.selected_product
        user = self.app_state.current_user
        shift = self.app_state.current_shift

        user_name = user.display_name if user else "?"
        product_name = product.display_name if product else "?"
        process_name = process.display_name if process else "?"
        file_name = Path(self.app_state.current_file).name if self.app_state.current_file else "?"

        pv = self.app_state.persistent_values
        ctx_text = " | ".join(f"{k}: {v}" for k, v in pv.items()) if pv else ""

        info_parts = [user_name, process_name, f"Schicht {shift}", file_name]
        if ctx_text:
            info_parts.append(ctx_text)
        self.info_label.config(text="  |  ".join(info_parts))

        mode_text = "Vertikal" if self.app_state.layout_mode == "vertical" else "Horizontal"
        self.layout_btn.config(text=f"Layout: {mode_text}")

        # Row-Group Anzeige
        self._update_group_label()

        # Felder generieren
        fields_key = f"{process_name}_{self.app_state.layout_mode}"
        if fields_key != self._last_fields_key:
            self._generate_fields()
            self._last_fields_key = fields_key

        self.status_var.set("")

    def _update_group_label(self) -> None:
        process = self.app_state.selected_process
        if process and process.row_group_size:
            current = (self.app_state.row_group_counter % process.row_group_size) + 1
            self.group_label.config(
                text=f"Nutzen: {current} von {process.row_group_size}"
            )
        else:
            self.group_label.config(text="")

    def _toggle_layout(self) -> None:
        if self.app_state.layout_mode == "vertical":
            self.app_state.layout_mode = "horizontal"
        else:
            self.app_state.layout_mode = "vertical"

        mode_text = "Vertikal" if self.app_state.layout_mode == "vertical" else "Horizontal"
        self.layout_btn.config(text=f"Layout: {mode_text}")
        self._generate_fields()
        self._last_fields_key = f"{self.app_state.selected_process.display_name}_{self.app_state.layout_mode}"

    def _generate_fields(self) -> None:
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.field_vars.clear()
        self._field_defs.clear()

        process = self.app_state.selected_process
        if not process:
            return

        # Per-measurement Kontext-Felder + Messwert-Felder sammeln
        per_meas_ctx = get_per_measurement_context_fields(process)
        measurement = get_measurement_fields(process)
        all_fields = per_meas_ctx + measurement
        self._field_defs = all_fields

        if self.app_state.layout_mode == "vertical":
            self._generate_vertical_fields(all_fields)
        else:
            self._generate_horizontal_fields(all_fields)

    def _generate_vertical_fields(self, fields: list[FieldDef]) -> None:
        self.scrollable_frame.columnconfigure(0, weight=0)
        self.scrollable_frame.columnconfigure(1, weight=1)
        self.scrollable_frame.columnconfigure(2, weight=0)

        first_widget = None
        for i, fd in enumerate(fields):
            # Label
            label_text = f"{fd.display_name}:"
            ttk.Label(self.scrollable_frame, text=label_text).grid(
                row=i, column=0, sticky="w", pady=5, padx=(10, 15)
            )

            var = tk.StringVar()
            # Vorausfuellen fuer per-measurement Kontext
            if fd.role == "context" and fd.display_name in self.app_state.persistent_values:
                var.set(self.app_state.persistent_values[fd.display_name])

            widget = self._create_field_widget(
                self.scrollable_frame, fd, var
            )
            widget.grid(row=i, column=1, sticky="w", pady=5, padx=(0, 10))

            # Spec-Hinweis
            if fd.spec_min is not None and fd.spec_max is not None:
                spec_text = f"[{fd.spec_min} - {fd.spec_max}]"
                ttk.Label(
                    self.scrollable_frame, text=spec_text,
                    foreground=COLORS["text_secondary"],
                    font=("Segoe UI", 8),
                ).grid(row=i, column=2, sticky="w", pady=5, padx=(5, 0))

            self.field_vars[fd.display_name] = var
            if i == 0:
                first_widget = widget

        if first_widget:
            first_widget.focus_set()

    def _generate_horizontal_fields(self, fields: list[FieldDef]) -> None:
        MAX_COLS = 4
        for i in range(MAX_COLS):
            self.scrollable_frame.columnconfigure(i, weight=1)

        first_widget = None
        for i, fd in enumerate(fields):
            row = i // MAX_COLS
            col = i % MAX_COLS

            cell = ttk.Frame(self.scrollable_frame, padding=5)
            cell.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
            cell.columnconfigure(0, weight=1)

            label_text = fd.display_name
            if fd.spec_min is not None and fd.spec_max is not None:
                label_text += f" [{fd.spec_min}-{fd.spec_max}]"
            ttk.Label(cell, text=f"{label_text}:",
                      font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")

            var = tk.StringVar()
            if fd.role == "context" and fd.display_name in self.app_state.persistent_values:
                var.set(self.app_state.persistent_values[fd.display_name])

            widget = self._create_field_widget(cell, fd, var)
            widget.grid(row=1, column=0, sticky="ew", pady=(2, 0))

            self.field_vars[fd.display_name] = var
            if i == 0:
                first_widget = widget

        if first_widget:
            first_widget.focus_set()

    def _create_field_widget(
        self, parent: tk.Widget, fd: FieldDef, var: tk.StringVar
    ) -> tk.Widget:
        """Erstellt das passende Widget basierend auf dem Feldtyp."""
        if fd.type == "choice" and fd.options:
            widget = ttk.Combobox(
                parent, textvariable=var, values=fd.options,
                state="readonly", width=23,
            )
        else:
            widget = ttk.Entry(parent, textvariable=var, width=25)
            # Spec-Feedback bei Zahlenfeldern
            if fd.type == "number" and fd.spec_min is not None:
                widget.bind("<FocusOut>", lambda e, w=widget, f=fd, v=var:
                            self._on_spec_check(w, f, v))

        return widget

    def _on_spec_check(self, widget: ttk.Entry, fd: FieldDef, var: tk.StringVar) -> None:
        """Prueft Spec-Limits und faerbt das Feld entsprechend."""
        value = var.get().strip()
        if not value:
            widget.configure(style="TEntry")
            return

        try:
            parsed = parse_numeric(value)
            if fd.spec_min is not None and fd.spec_max is not None:
                if fd.spec_min <= parsed <= fd.spec_max:
                    widget.configure(foreground=COLORS["success"])
                else:
                    widget.configure(foreground=COLORS["error"])
            else:
                widget.configure(foreground="")
        except (ValueError, OverflowError):
            widget.configure(foreground=COLORS["error"])

    def _clear_fields(self) -> None:
        process = self.app_state.selected_process
        for name, var in self.field_vars.items():
            # Per-measurement Kontext nicht leeren
            fd = next((f for f in self._field_defs if f.display_name == name), None)
            if fd and fd.role == "context":
                continue
            var.set("")
        self.status_var.set("")
        children = self.scrollable_frame.winfo_children()
        for child in children:
            if isinstance(child, (ttk.Entry, ttk.Combobox)):
                child.focus_set()
                break

    def _save(self) -> None:
        """Oeffnet den Review-Dialog vor dem Schreiben."""
        raw_values = {header: var.get() for header, var in self.field_vars.items()}

        ReviewDialog(
            parent=self,
            app_state=self.app_state,
            raw_values=raw_values,
            field_defs=self._field_defs,
            on_confirm=self._do_write,
        )

    def _do_write(self, normalized_values: dict[str, float | str | None]) -> None:
        """Schreibt die Messwerte in die Excel-Datei."""
        process = self.app_state.selected_process
        if not process:
            return

        if self.app_state.audit:
            self.app_state.audit.log(
                "write_attempt",
                user=self.app_state.current_user.user_id if self.app_state.current_user else None,
                file=str(self.app_state.current_file),
                context=dict(self.app_state.persistent_values),
                details={"measurement_count": len(normalized_values)},
            )

        # Werte aufteilen nach Rolle
        context_values: dict[str, str] = {}
        measurement_values: dict[str, float | str | None] = {}

        for fd in self._field_defs:
            val = normalized_values.get(fd.display_name)
            if fd.role == "context":
                context_values[fd.display_name] = str(val) if val is not None else ""
            else:
                measurement_values[fd.display_name] = val

        # Persistente Kontext-Werte hinzufuegen
        context_values.update(self.app_state.persistent_values)

        # Auto-Werte berechnen
        auto_values: dict[str, str | float | None] = {}
        now = datetime.now()
        for fd in get_auto_fields(process):
            if fd.id == "datum":
                auto_values[fd.display_name] = now.strftime("%Y-%m-%d %H:%M:%S")
            elif fd.id == "bearbeiter":
                user = self.app_state.current_user
                auto_values[fd.display_name] = user.display_name if user else ""
            elif fd.id == "nutzen" and process.row_group_size:
                nutzen = (self.app_state.row_group_counter % process.row_group_size) + 1
                auto_values[fd.display_name] = nutzen
            elif fd.id == "pruefmuster":
                self.app_state.auto_sequence += 1
                auto_values[fd.display_name] = self.app_state.auto_sequence

        result = write_measurement_row(
            filepath=self.app_state.current_file,
            process=process,
            context_values=context_values,
            measurements=measurement_values,
            auto_values=auto_values,
        )

        if result.success:
            # Zaehler aktualisieren
            self.app_state.row_group_counter += 1
            self._update_group_label()

            self._add_to_history(normalized_values)

            self.status_var.set(f"Zeile {result.row_number} erfolgreich geschrieben.")
            self.status_label.config(style="Success.TLabel")
            self._clear_fields()

            if self.app_state.audit:
                self.app_state.audit.log(
                    "write_success",
                    user=self.app_state.current_user.user_id if self.app_state.current_user else None,
                    file=str(self.app_state.current_file),
                    context=dict(self.app_state.persistent_values),
                    details={"row": result.row_number},
                )
        else:
            messagebox.showerror("Fehler beim Schreiben", result.error)
            self.status_var.set(f"Fehler: {result.error}")
            self.status_label.config(style="Error.TLabel")

            # Auto-Sequence zuruecksetzen wenn fehlgeschlagen
            if "pruefmuster" in [f.id for f in get_auto_fields(process)]:
                self.app_state.auto_sequence -= 1

            if self.app_state.audit:
                self.app_state.audit.log(
                    "write_fail",
                    user=self.app_state.current_user.user_id if self.app_state.current_user else None,
                    file=str(self.app_state.current_file),
                    context=dict(self.app_state.persistent_values),
                    details={"error": result.error},
                )

    def _add_to_history(self, measurements: dict[str, float | str | None]) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")

        pv = self.app_state.persistent_values
        kontext = " | ".join(f"{k}: {v}" for k, v in pv.items()) if pv else "-"

        werte_list = []
        for header, value in measurements.items():
            if value is not None:
                werte_list.append(f"{header}: {value}")
        werte = ", ".join(werte_list) if werte_list else "-"

        self._history.append((timestamp, kontext, werte))
        self._update_history_display()

    def _update_history_display(self) -> None:
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for zeit, kontext, werte in reversed(self._history):
            self.history_tree.insert("", "end", values=(zeit, kontext, werte))

    def _change_context(self) -> None:
        self.on_navigate("context")

    def _change_process(self) -> None:
        self.app_state.reset_process()
        self._history.clear()
        self._update_history_display()
        self.on_navigate("product_process")

    def _logout(self) -> None:
        self.app_state.reset_user()
        self._history.clear()
        self._update_history_display()
        self.on_navigate("login")
