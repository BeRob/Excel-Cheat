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
    get_persistent_context_fields,
    get_group_shared_fields,
    get_per_nutzen_fields,
    get_auto_fields,
    FieldDef,
)
from src.config.settings import HEADER_ROW
from src.domain.validation import parse_numeric
from src.excel.reader import read_all_data
from src.excel.writer import write_measurement_row, write_measurement_rows
from src.ui.base_view import BaseView
from src.ui.review_dialog import ReviewDialog
from src.ui.theme import COLORS


class FormView(BaseView):
    def __init__(self, parent, app_state, on_navigate):
        super().__init__(parent, app_state, on_navigate)
        self.field_vars: dict[str, tk.StringVar] = {}
        self.persistent_vars: dict[str, tk.StringVar] = {}
        self._field_defs: list[FieldDef] = []
        self._nutzen_field_defs: list[FieldDef] = []
        self._persistent_field_defs: list[FieldDef] = []
        self._last_fields_key: str = ""
        self._history: deque = deque(maxlen=10)
        self._first_focus_widget: tk.Widget | None = None
        self._nutzen_count_var: tk.IntVar | None = None
        self._nutzen_sections_parent: tk.Widget | None = None
        self._is_multi_nutzen: bool = False
        self._validation_borders: dict[str, tk.Frame] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(5, weight=0)

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

        ttk.Button(btn_frame, text="Kontext ändern",
                   command=self._change_context).pack(side="left", padx=(5, 0))
        ttk.Button(btn_frame, text="Prozess wechseln",
                   command=self._change_process).pack(side="left", padx=(5, 0))
        ttk.Button(btn_frame, text="Abmelden",
                   command=self._logout).pack(side="left", padx=(5, 0))

        title_frame = ttk.Frame(self)
        title_frame.grid(row=1, column=0, pady=(5, 5))
        ttk.Label(title_frame, text="Messwerte erfassen",
                  style="Subtitle.TLabel").pack(side="left")
        self.group_label = ttk.Label(title_frame, text="", foreground=COLORS["accent"])
        self.group_label.pack(side="left", padx=(15, 0))

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
            "<Configure>", lambda e: self._update_scroll_region(),
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

        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(self, textvariable=self.status_var,
                                      style="Success.TLabel")
        self.status_label.grid(row=3, column=0, pady=5)

        bottom_bar = ttk.Frame(self)
        bottom_bar.grid(row=4, column=0, pady=(5, 10))

        ttk.Button(bottom_bar, text="Felder leeren",
                   command=self._clear_fields).pack(side="left", padx=10)
        ttk.Button(bottom_bar, text="Speichern", command=self._save,
                   style="Accent.TButton").pack(side="left", padx=10)

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

    def _update_scroll_region(self) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        if self.scrollable_frame.winfo_reqheight() <= self.canvas.winfo_height():
            self.scrollbar.grid_remove()
        else:
            self.scrollbar.grid()

    def _bind_mousewheel(self, event) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event) -> None:
        if self.scrollable_frame.winfo_reqheight() <= self.canvas.winfo_height():
            return
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

        self._update_group_label()

        fields_key = f"{process_name}_{self.app_state.layout_mode}"
        if fields_key != self._last_fields_key:
            self._history.clear()
            self._generate_fields()
            self._last_fields_key = fields_key
            if self.app_state.is_resume:
                self._preload_history()
        else:
            self._set_initial_focus()

        self.status_var.set("")

    def _set_initial_focus(self) -> None:
        if self._first_focus_widget is not None:
            try:
                self._first_focus_widget.focus_set()
            except tk.TclError:
                pass

    def _update_group_label(self) -> None:
        process = self.app_state.selected_process
        if process and process.row_group_size and not self._is_multi_nutzen:
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
        self.persistent_vars.clear()
        self._field_defs.clear()
        self._nutzen_field_defs.clear()
        self._persistent_field_defs.clear()
        self._nutzen_sections_parent = None
        self._first_focus_widget = None
        self._validation_borders.clear()

        process = self.app_state.selected_process
        if not process:
            self._is_multi_nutzen = False
            return

        self._is_multi_nutzen = bool(
            process.row_group_size and get_group_shared_fields(process)
        )

        persistent_fields = get_persistent_context_fields(process)
        self._persistent_field_defs = persistent_fields

        if persistent_fields:
            ctx_frame = ttk.LabelFrame(
                self.scrollable_frame, text="Feste Werte", padding=10,
            )
            ctx_frame.pack(fill="x", padx=5, pady=(5, 10))
            ctx_frame.columnconfigure(1, weight=1)

            for i, fd in enumerate(persistent_fields):
                ttk.Label(ctx_frame, text=f"{fd.display_name}:").grid(
                    row=i, column=0, sticky="w", pady=3, padx=(5, 10),
                )
                var = tk.StringVar()
                if fd.display_name in self.app_state.persistent_values:
                    var.set(self.app_state.persistent_values[fd.display_name])

                if fd.type == "choice" and fd.options:
                    widget = ttk.Combobox(
                        ctx_frame, textvariable=var, values=fd.options,
                        state="readonly", width=23,
                    )
                else:
                    widget = ttk.Entry(ctx_frame, textvariable=var, width=25)

                widget.grid(row=i, column=1, sticky="w", pady=3)
                self.persistent_vars[fd.display_name] = var

        if self._is_multi_nutzen:
            self._generate_multi_nutzen_fields(process)
        else:
            per_meas_ctx = get_per_measurement_context_fields(process)
            measurement = get_measurement_fields(process)
            all_fields_original = per_meas_ctx + measurement
            choice_fields = [f for f in all_fields_original if f.type == "choice"]
            other_fields = [f for f in all_fields_original if f.type != "choice"]
            display_fields = choice_fields + other_fields
            self._field_defs = display_fields

            meas_frame = ttk.LabelFrame(
                self.scrollable_frame, text="Messwerte", padding=10,
            )
            meas_frame.pack(fill="x", padx=5, pady=(0, 5))

            if self.app_state.layout_mode == "vertical":
                first_meas, first_choice = self._generate_vertical_fields(
                    display_fields, meas_frame,
                )
            else:
                first_meas, first_choice = self._generate_horizontal_fields(
                    display_fields, meas_frame,
                )

            self._first_focus_widget = first_choice or first_meas

        self._set_initial_focus()
        self.canvas.yview_moveto(0)

    def _generate_multi_nutzen_fields(self, process) -> None:
        """Baut das Multi-Nutzen-Formular: Anzahl-Wähler, Gemeinsame Werte, Nutzen-Sektionen."""
        max_nutzen = process.row_group_size

        # Anzahl-Nutzen-Wähler
        count_frame = ttk.LabelFrame(
            self.scrollable_frame, text="Anzahl Nutzen", padding=10,
        )
        count_frame.pack(fill="x", padx=5, pady=(0, 5))
        self._nutzen_count_var = tk.IntVar(value=self.app_state.nutzen_count)
        for n in range(1, max_nutzen + 1):
            ttk.Radiobutton(
                count_frame, text=str(n), variable=self._nutzen_count_var, value=n,
                command=self._rebuild_nutzen_sections,
            ).pack(side="left", padx=10)

        # Gemeinsame Werte: per-measurement context + group_shared Messfelder
        per_meas_ctx = get_per_measurement_context_fields(process)
        shared_meas = get_group_shared_fields(process)
        shared_fields = per_meas_ctx + shared_meas
        self._field_defs = shared_fields

        shared_frame = ttk.LabelFrame(
            self.scrollable_frame, text="Gemeinsame Werte", padding=10,
        )
        shared_frame.pack(fill="x", padx=5, pady=(0, 5))
        first_shared, _ = self._generate_vertical_fields(shared_fields, shared_frame)
        if self._first_focus_widget is None:
            self._first_focus_widget = first_shared

        # Per-Nutzen-Felder speichern
        self._nutzen_field_defs = get_per_nutzen_fields(process)

        # Container für Nutzen-Sektionen
        self._nutzen_sections_parent = ttk.Frame(self.scrollable_frame)
        self._nutzen_sections_parent.pack(fill="x", padx=5, pady=(0, 5))

        self._rebuild_nutzen_sections()

    def _rebuild_nutzen_sections(self) -> None:
        """Baut die Nutzen-Sektionen neu auf wenn die Anzahl geändert wird."""
        if self._nutzen_sections_parent is None or self._nutzen_count_var is None:
            return

        count = self._nutzen_count_var.get()
        self.app_state.nutzen_count = count

        # Alte per-nutzen Einträge aus field_vars entfernen
        for key in [k for k in self.field_vars if "_n" in k]:
            del self.field_vars[key]

        for widget in self._nutzen_sections_parent.winfo_children():
            widget.destroy()

        for i in range(1, count + 1):
            section = ttk.LabelFrame(
                self._nutzen_sections_parent,
                text=f"Nutzen {i}",
                padding=10,
            )
            section.pack(fill="x", padx=0, pady=(0, 5))
            section.columnconfigure(0, weight=0)
            section.columnconfigure(1, weight=1)
            section.columnconfigure(2, weight=0)

            for row_idx, fd in enumerate(self._nutzen_field_defs):
                key = f"{fd.display_name}_n{i}"
                ttk.Label(section, text=f"{fd.display_name}:").grid(
                    row=row_idx, column=0, sticky="w", pady=5, padx=(5, 15),
                )
                var = tk.StringVar()
                if fd.default_value is not None:
                    var.set(fd.default_value)

                widget, container = self._create_field_widget(section, fd, var)
                container.grid(row=row_idx, column=1, sticky="w", pady=5, padx=(0, 10))

                if fd.spec_min is not None and fd.spec_max is not None:
                    ttk.Label(
                        section,
                        text=f"{fd.spec_min} – {fd.spec_max}",
                        foreground=COLORS["text_secondary"],
                        font=("Segoe UI", 8),
                    ).grid(row=row_idx, column=2, sticky="w", pady=5)

                self.field_vars[key] = var

        self.canvas.yview_moveto(0)

    def _preload_history(self) -> None:
        """Lädt die letzten 10 Messungen aus der Excel-Datei beim Resume."""
        if not self.app_state.current_file:
            return
        process = self.app_state.selected_process
        if not process:
            return

        rows = read_all_data(self.app_state.current_file, header_row=HEADER_ROW)
        if not rows:
            return

        meas_display_names = {fd.display_name for fd in get_measurement_fields(process)}
        pv = self.app_state.persistent_values

        self._history.clear()
        for row in rows[-10:]:
            datum = str(row.get("Datum", "") or "")
            zeit = datum[-8:] if len(datum) >= 8 else datum
            kontext = " | ".join(f"{k}: {v}" for k, v in pv.items()) if pv else "-"
            werte_parts = [
                f"{k}: {v}" for k, v in row.items()
                if k in meas_display_names and v is not None
            ]
            werte = ", ".join(werte_parts) or "-"
            self._history.append((zeit, kontext, werte))

        self._update_history_display()

    def _generate_vertical_fields(
        self, fields: list[FieldDef], parent: tk.Widget,
    ) -> tuple[tk.Widget | None, tk.Widget | None]:
        parent.columnconfigure(0, weight=0)
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(2, weight=0)

        first_widget = None
        first_choice = None
        for i, fd in enumerate(fields):
            ttk.Label(parent, text=f"{fd.display_name}:").grid(
                row=i, column=0, sticky="w", pady=5, padx=(5, 15),
            )

            var = tk.StringVar()
            if fd.role == "context" and fd.display_name in self.app_state.persistent_values:
                var.set(self.app_state.persistent_values[fd.display_name])
            elif fd.default_value is not None:
                var.set(fd.default_value)

            widget, container = self._create_field_widget(parent, fd, var)
            container.grid(row=i, column=1, sticky="w", pady=5, padx=(0, 10))

            if fd.spec_min is not None or fd.spec_max is not None:
                spec_parts = []
                if fd.spec_min is not None:
                    spec_parts.append(f"≥{fd.spec_min}")
                if fd.spec_max is not None:
                    spec_parts.append(f"≤{fd.spec_max}")
                if fd.spec_min is not None and fd.spec_max is not None:
                    spec_parts = [f"{fd.spec_min} – {fd.spec_max}"]
                ttk.Label(
                    parent, text="  ".join(spec_parts),
                    foreground=COLORS["text_secondary"],
                    font=("Segoe UI", 8),
                ).grid(row=i, column=2, sticky="w", pady=5, padx=(5, 0))

            self.field_vars[fd.display_name] = var
            if i == 0:
                first_widget = widget
            if first_choice is None and fd.type == "choice":
                first_choice = widget

        return first_widget, first_choice

    def _generate_horizontal_fields(
        self, fields: list[FieldDef], parent: tk.Widget,
    ) -> tuple[tk.Widget | None, tk.Widget | None]:
        max_cols = 4
        for i in range(max_cols):
            parent.columnconfigure(i, weight=1)

        first_widget = None
        first_choice = None
        for i, fd in enumerate(fields):
            row = i // max_cols
            col = i % max_cols

            cell = ttk.Frame(parent, padding=5)
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
            elif fd.default_value is not None:
                var.set(fd.default_value)

            widget, container = self._create_field_widget(cell, fd, var)
            container.grid(row=1, column=0, sticky="ew", pady=(2, 0))

            self.field_vars[fd.display_name] = var
            if i == 0:
                first_widget = widget
            if first_choice is None and fd.type == "choice":
                first_choice = widget

        return first_widget, first_choice

    def _create_field_widget(
        self, parent: tk.Widget, fd: FieldDef, var: tk.StringVar
    ) -> tuple[tk.Widget, tk.Widget]:
        """Gibt (input_widget, container) zurück. Container ist bei Spec-Feldern ein
        farbiger Border-Frame, sonst identisch mit dem input_widget."""
        has_spec = fd.type == "number" and (fd.spec_min is not None or fd.spec_max is not None)

        if fd.type == "choice" and fd.options:
            widget = ttk.Combobox(
                parent, textvariable=var, values=fd.options,
                state="readonly", width=23,
            )
            widget.bind("<Return>", self._focus_next)
            return widget, widget

        if has_spec:
            border = tk.Frame(parent, bg=COLORS["border"], padx=3, pady=3)
            entry = ttk.Entry(border, textvariable=var, width=23)
            entry.pack(fill="both", expand=True)
            entry.bind("<Return>", self._focus_next)
            entry.bind("<Down>", self._focus_next)
            entry.bind("<Up>", self._focus_prev)
            entry.bind("<FocusOut>", lambda e, f=fd, v=var: self._on_spec_check(f, v))
            self._validation_borders[fd.display_name] = border
            return entry, border

        widget = ttk.Entry(parent, textvariable=var, width=25)
        widget.bind("<Return>", self._focus_next)
        widget.bind("<Down>", self._focus_next)
        widget.bind("<Up>", self._focus_prev)
        return widget, widget

    def _focus_next(self, event) -> str:
        event.widget.tk_focusNext().focus_set()
        return "break"

    def _focus_prev(self, event) -> str:
        event.widget.tk_focusPrev().focus_set()
        return "break"

    def _on_spec_check(self, fd: FieldDef, var: tk.StringVar) -> None:
        border = self._validation_borders.get(fd.display_name)
        if border is None:
            return
        value = var.get().strip()
        if not value:
            border.configure(bg=COLORS["border"])
            return
        try:
            parsed = parse_numeric(value)
            in_spec = True
            if fd.spec_min is not None and parsed < fd.spec_min:
                in_spec = False
            if fd.spec_max is not None and parsed > fd.spec_max:
                in_spec = False
            border.configure(bg=COLORS["success"] if in_spec else COLORS["error"])
        except (ValueError, OverflowError):
            border.configure(bg=COLORS["error"])

    def _clear_fields(self) -> None:
        all_defs = self._field_defs + self._nutzen_field_defs
        for name, var in self.field_vars.items():
            # Per-Nutzen-Keys haben Suffix "_n{i}" – Basis-Name für FieldDef-Suche ermitteln
            base_name = name
            for fd in self._nutzen_field_defs:
                if name.startswith(fd.display_name + "_n"):
                    base_name = fd.display_name
                    break
            fd = next((f for f in all_defs if f.display_name == base_name), None)
            # Kontext-, Choice- und group_shared-Felder behalten ihren Wert.
            if fd and (fd.role == "context" or fd.type == "choice" or fd.group_shared):
                continue
            var.set(fd.default_value if fd and fd.default_value is not None else "")
        for border in self._validation_borders.values():
            border.configure(bg=COLORS["border"])
        self.status_var.set("")
        self._set_initial_focus()

    def _save(self) -> None:
        for header, var in self.persistent_vars.items():
            self.app_state.persistent_values[header] = var.get().strip()

        if self._is_multi_nutzen:
            self._do_multi_nutzen_save()
            return

        raw_values = {header: var.get() for header, var in self.field_vars.items()}

        ReviewDialog(
            parent=self,
            app_state=self.app_state,
            raw_values=raw_values,
            field_defs=self._field_defs,
            on_confirm=self._do_write,
        )

    def _do_write(self, normalized_values: dict[str, float | str | None]) -> None:
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

        context_values: dict[str, str] = {}
        measurement_values: dict[str, float | str | None] = {}

        for fd in self._field_defs:
            val = normalized_values.get(fd.display_name)
            if fd.role == "context":
                context_values[fd.display_name] = str(val) if val is not None else ""
            else:
                measurement_values[fd.display_name] = val

        context_values.update(self.app_state.persistent_values)

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

            # Sequenz zuruecknehmen, wenn das Schreiben fehlschlug
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

    def _do_multi_nutzen_save(self) -> None:
        """Validierung und Bestätigung für Multi-Nutzen, dann Schreiben."""
        process = self.app_state.selected_process
        if not process:
            return

        nutzen_count = self.app_state.nutzen_count

        # Pflichtfeld-Prüfung: Gemeinsame Werte
        for fd in self._field_defs:
            if not fd.optional and fd.role != "context":
                val = self.field_vars.get(fd.display_name, tk.StringVar()).get().strip()
                if not val:
                    messagebox.showwarning(
                        "Fehlende Eingabe",
                        f"Bitte '{fd.display_name}' ausfüllen.",
                    )
                    return

        # Pflichtfeld-Prüfung: Per-Nutzen-Felder
        for i in range(1, nutzen_count + 1):
            for fd in self._nutzen_field_defs:
                if not fd.optional:
                    key = f"{fd.display_name}_n{i}"
                    val = self.field_vars.get(key, tk.StringVar()).get().strip()
                    if not val:
                        messagebox.showwarning(
                            "Fehlende Eingabe",
                            f"Bitte '{fd.display_name}' für Nutzen {i} ausfüllen.",
                        )
                        return

        summary_lines = []
        for fd in self._field_defs:
            val = self.field_vars.get(fd.display_name, tk.StringVar()).get().strip()
            if val:
                summary_lines.append(f"  {fd.display_name}: {val}")
        for i in range(1, nutzen_count + 1):
            summary_lines.append(f"  --- Nutzen {i} ---")
            for fd in self._nutzen_field_defs:
                key = f"{fd.display_name}_n{i}"
                val = self.field_vars.get(key, tk.StringVar()).get().strip()
                if val:
                    summary_lines.append(f"  {fd.display_name}: {val}")

        confirmed = messagebox.askyesno(
            "Messung speichern",
            f"{nutzen_count} Nutzen speichern?\n\n" + "\n".join(summary_lines),
        )
        if confirmed:
            self._do_multi_nutzen_write()

    def _do_multi_nutzen_write(self) -> None:
        process = self.app_state.selected_process
        if not process:
            return

        nutzen_count = self.app_state.nutzen_count
        now = datetime.now()

        context_values: dict[str, str] = {}
        context_values.update(self.app_state.persistent_values)
        for fd in self._field_defs:
            if fd.role == "context":
                val = self.field_vars.get(fd.display_name, tk.StringVar()).get().strip()
                context_values[fd.display_name] = val

        shared_meas: dict[str, float | str | None] = {}
        for fd in self._field_defs:
            if fd.role == "measurement":
                raw = self.field_vars.get(fd.display_name, tk.StringVar()).get().strip()
                if fd.type == "number" and raw:
                    try:
                        from src.domain.validation import parse_numeric
                        shared_meas[fd.display_name] = parse_numeric(raw)
                    except (ValueError, OverflowError):
                        shared_meas[fd.display_name] = raw
                else:
                    shared_meas[fd.display_name] = raw or None

        rows = []
        for i in range(1, nutzen_count + 1):
            per_nutzen: dict[str, float | str | None] = {}
            for fd in self._nutzen_field_defs:
                key = f"{fd.display_name}_n{i}"
                raw = self.field_vars.get(key, tk.StringVar()).get().strip()
                if fd.type == "number" and raw:
                    try:
                        from src.domain.validation import parse_numeric
                        per_nutzen[fd.display_name] = parse_numeric(raw)
                    except (ValueError, OverflowError):
                        per_nutzen[fd.display_name] = raw
                else:
                    per_nutzen[fd.display_name] = raw or None

            auto: dict[str, str | float | None] = {}
            for fd in get_auto_fields(process):
                if fd.id == "datum":
                    auto[fd.display_name] = now.strftime("%Y-%m-%d %H:%M:%S")
                elif fd.id == "bearbeiter":
                    user = self.app_state.current_user
                    auto[fd.display_name] = user.display_name if user else ""
                elif fd.id == "nutzen":
                    auto[fd.display_name] = i

            row: dict[str, str | float | None] = {}
            row.update(context_values)
            row.update(shared_meas)
            row.update(per_nutzen)
            row.update(auto)
            rows.append(row)

        if self.app_state.audit:
            self.app_state.audit.log(
                "write_attempt",
                user=self.app_state.current_user.user_id if self.app_state.current_user else None,
                file=str(self.app_state.current_file),
                context=dict(self.app_state.persistent_values),
                details={"nutzen_count": nutzen_count},
            )

        result = write_measurement_rows(
            filepath=self.app_state.current_file,
            rows=rows,
        )

        if result.success:
            self.app_state.row_group_counter += nutzen_count

            for i, row in enumerate(rows, 1):
                meas_vals = {**shared_meas}
                for fd in self._nutzen_field_defs:
                    meas_vals[fd.display_name] = row.get(fd.display_name)
                self._add_to_history(meas_vals, label=f"Nutzen {i}")

            self.status_var.set(
                f"{nutzen_count} Nutzen gespeichert (bis Zeile {result.row_number})."
            )
            self.status_label.config(style="Success.TLabel")
            self._clear_fields()

            if self.app_state.audit:
                self.app_state.audit.log(
                    "write_success",
                    user=self.app_state.current_user.user_id if self.app_state.current_user else None,
                    file=str(self.app_state.current_file),
                    context=dict(self.app_state.persistent_values),
                    details={"last_row": result.row_number, "nutzen_count": nutzen_count},
                )
        else:
            messagebox.showerror("Fehler beim Schreiben", result.error)
            self.status_var.set(f"Fehler: {result.error}")
            self.status_label.config(style="Error.TLabel")
            if self.app_state.audit:
                self.app_state.audit.log(
                    "write_fail",
                    user=self.app_state.current_user.user_id if self.app_state.current_user else None,
                    file=str(self.app_state.current_file),
                    context=dict(self.app_state.persistent_values),
                    details={"error": result.error},
                )

    def _add_to_history(self, measurements: dict[str, float | str | None], label: str = "") -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        if label:
            timestamp = f"{timestamp} ({label})"

        pv = self.app_state.persistent_values
        kontext = " | ".join(f"{k}: {v}" for k, v in pv.items()) if pv else "-"

        werte_list = [
            f"{header}: {value}"
            for header, value in measurements.items()
            if value is not None
        ]
        werte = ", ".join(werte_list) if werte_list else "-"

        self._history.append((timestamp, kontext, werte))
        self._update_history_display()

    def _update_history_display(self) -> None:
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for zeit, kontext, werte in reversed(self._history):
            self.history_tree.insert("", "end", values=(zeit, kontext, werte))
        for col in ("zeit", "kontext", "werte"):
            header_len = len(self.history_tree.heading(col)["text"])
            max_len = max(
                [header_len] +
                [len(str(self.history_tree.set(item, col))) for item in self.history_tree.get_children()]
            )
            self.history_tree.column(col, width=max(max_len * 8, 80))

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
