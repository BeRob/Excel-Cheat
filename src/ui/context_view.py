"""Kontext-Bildschirm: Persistente Werte (z.B. FA-Nr., LOT) setzen."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from datetime import datetime

from src.config.process_config import (
    get_persistent_context_fields,
    get_info_header_fields,
    get_all_headers,
    get_measurement_fields,
)
from src.excel.creator import (
    find_existing_file,
    create_measurement_file,
    count_data_rows,
    write_info_header,
    get_shift_date,
)
from src.ui.base_view import BaseView
from src.ui.date_picker import DatePickerDialog
from src.ui.theme import COLORS


class ContextView(BaseView):
    def __init__(self, parent, app_state, on_navigate):
        super().__init__(parent, app_state, on_navigate)
        self.field_vars: dict[str, tk.StringVar] = {}
        self._field_entries: list[tk.Widget] = []
        self._pending_file = None
        self._is_resume: bool = False
        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        top_bar = ttk.Frame(self)
        top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        top_bar.columnconfigure(0, weight=1)

        self.info_label = ttk.Label(top_bar, text="")
        self.info_label.grid(row=0, column=0, sticky="w")

        ttk.Label(self, text="Feste Werte setzen", style="Subtitle.TLabel").grid(
            row=1, column=0, pady=(10, 5)
        )

        self.form_frame = ttk.Frame(self)
        self.form_frame.grid(row=2, column=0, padx=40, pady=10)

        self.no_fields_label = ttk.Label(
            self,
            text="Keine festen Werte definiert. Sie können direkt weiter zur Messung.",
            foreground=COLORS["text_secondary"],
        )
        self.no_fields_label.grid(row=3, column=0, padx=40, pady=5)
        self.no_fields_label.grid_remove()

        self.file_status_label = ttk.Label(self, text="")
        self.file_status_label.grid(row=4, column=0, pady=(0, 5))

        self.next_btn = ttk.Button(
            self, text="Weiter zur Messung", command=self._go_next,
            style="Accent.TButton",
        )
        self.next_btn.grid(row=5, column=0, pady=15)

        # Navigations-Leiste am unteren Fensterrand
        nav_bar = ttk.Frame(self)
        nav_bar.grid(row=6, column=0, sticky="ew", padx=10, pady=(0, 10))
        nav_bar.columnconfigure(0, weight=1)

        nav_right = ttk.Frame(nav_bar)
        nav_right.grid(row=0, column=1, sticky="e")
        ttk.Button(
            nav_right, text="Prozess wechseln", command=self._change_process,
        ).pack(side="left", padx=(5, 0))
        ttk.Button(
            nav_right, text="Abmelden", command=self._logout,
        ).pack(side="left", padx=(5, 0))

    def on_show(self) -> None:
        user = self.app_state.current_user
        process = self.app_state.selected_process
        product = self.app_state.selected_product
        shift = self.app_state.current_shift

        user_name = user.display_name if user else "?"
        process_name = process.display_name if process else "?"
        product_name = product.display_name if product else "?"

        self.info_label.config(
            text=f"{user_name}  |  {product_name}  |  {process_name}  |  Schicht {shift}"
        )

        self._pending_file = None
        self._is_resume = False
        self.file_status_label.config(text="")

        self._generate_fields()

    def _generate_fields(self) -> None:
        for widget in self.form_frame.winfo_children():
            widget.destroy()
        self.field_vars.clear()
        self._field_entries.clear()

        process = self.app_state.selected_process
        if not process:
            self.no_fields_label.grid()
            self.next_btn.config(state="normal")
            return

        fields = get_persistent_context_fields(process)
        if not fields:
            self.no_fields_label.grid()
            self.next_btn.config(state="normal")
            self._check_file_status()
            return

        self.no_fields_label.grid_remove()

        for i, field_def in enumerate(fields):
            ttk.Label(self.form_frame, text=f"{field_def.display_name}:").grid(
                row=i, column=0, sticky="w", pady=5, padx=(0, 10)
            )
            var = tk.StringVar()

            # Vorbelegung: erst persistent_values, dann carried_values
            if field_def.display_name in self.app_state.persistent_values:
                var.set(self.app_state.persistent_values[field_def.display_name])
            elif field_def.display_name in self.app_state.carried_values:
                var.set(self.app_state.carried_values[field_def.display_name])

            var.trace_add("write", self._on_field_changed)

            if field_def.type == "choice" and field_def.options:
                widget = ttk.Combobox(
                    self.form_frame, textvariable=var,
                    values=field_def.options, state="readonly", width=28,
                )
                widget.bind("<Return>", lambda e: e.widget.tk_focusNext().focus_set() or "break")
                widget.grid(row=i, column=1, pady=5)
                self._field_entries.append(widget)
            elif field_def.type == "date":
                container = ttk.Frame(self.form_frame)
                container.grid(row=i, column=1, pady=5, sticky="w")
                widget = ttk.Entry(container, textvariable=var, width=22)
                widget.bind("<Return>", lambda e: e.widget.tk_focusNext().focus_set() or "break")
                widget.pack(side="left")
                ttk.Button(
                    container, text="📅", width=3,
                    command=lambda v=var: self._open_date_picker(v),
                ).pack(side="left", padx=(4, 0))
                self._field_entries.append(widget)
            else:
                widget = ttk.Entry(self.form_frame, textvariable=var, width=30)
                widget.bind("<Return>", lambda e: e.widget.tk_focusNext().focus_set() or "break")
                widget.grid(row=i, column=1, pady=5)
                self._field_entries.append(widget)

            self.field_vars[field_def.display_name] = var

        if self._field_entries:
            self._field_entries[0].focus_set()

        self._on_field_changed()

    def _on_field_changed(self, *_) -> None:
        self._check_fields()
        self._check_file_status()

    def _check_fields(self, *_) -> None:
        if not self.field_vars:
            self.next_btn.config(state="normal")
            return
        filled = all(var.get().strip() for var in self.field_vars.values())
        self.next_btn.config(state="normal" if filled else "disabled")

    def _check_file_status(self, *_) -> None:
        product = self.app_state.selected_product
        process = self.app_state.selected_process
        output_dir = self.app_state.output_dir
        if not product or not process or not output_dir:
            return

        lot = self.field_vars.get("LOT Nr.", tk.StringVar()).get().strip()
        fa_nr = self.field_vars.get("FA-Nr.", tk.StringVar()).get().strip()

        if not lot or not fa_nr:
            self.file_status_label.config(text="", style="TLabel")
            self._pending_file = None
            self._is_resume = False
            return

        existing = find_existing_file(
            lot, fa_nr, product.product_id, process.template_id, output_dir
        )
        if existing:
            count = count_data_rows(existing)
            self.file_status_label.config(
                text=f"↺  Fortsetzen  –  {count} Messungen vorhanden",
                style="Warning.TLabel",
            )
            self._pending_file = existing
            self._is_resume = True
        else:
            self.file_status_label.config(
                text="＋  Neue Datei wird erstellt",
                style="Success.TLabel",
            )
            self._pending_file = None
            self._is_resume = False

    def _go_next(self) -> None:
        self.app_state.persistent_values = {
            h: var.get().strip() for h, var in self.field_vars.items()
        }

        product = self.app_state.selected_product
        process = self.app_state.selected_process
        output_dir = self.app_state.output_dir
        shift = self.app_state.current_shift or "1"
        now = datetime.now()
        shift_date = get_shift_date(now, shift)

        lot = self.app_state.persistent_values.get("LOT Nr.", "")
        fa_nr = self.app_state.persistent_values.get("FA-Nr.", "")

        if self._pending_file and self._pending_file.exists():
            filepath = self._pending_file
        else:
            filepath = create_measurement_file(
                process, product.product_id, output_dir,
                lot, fa_nr, shift, shift_date,
            )

        self.app_state.current_file = filepath
        self.app_state.is_resume = self._is_resume

        row_count = count_data_rows(filepath)
        self.app_state.auto_sequence = row_count
        if process.row_group_size:
            self.app_state.row_group_counter = row_count % process.row_group_size
        else:
            self.app_state.row_group_counter = 0

        extra_info: list[tuple[str, str]] = []
        for fd in get_info_header_fields(process):
            value = self.app_state.persistent_values.get(fd.display_name, "")
            extra_info.append((f"{fd.display_name}:", value))

        write_info_header(
            filepath=filepath,
            product_name=product.display_name if product else "",
            process_name=process.display_name if process else "",
            shift=shift,
            dt=shift_date,
            extra_info=extra_info,
        )

        if self.app_state.audit:
            self.app_state.audit.log(
                "context_set",
                user=self.app_state.current_user.user_id if self.app_state.current_user else None,
                file=str(filepath),
                context=dict(self.app_state.persistent_values),
                details={"resumed": self._is_resume},
            )

        self.on_navigate("form")

    def _open_date_picker(self, var: tk.StringVar) -> None:
        DatePickerDialog(self, initial=var.get(), on_pick=var.set)

    def _change_process(self) -> None:
        self.app_state.reset_process()
        self.on_navigate("product_process")

    def _logout(self) -> None:
        self.app_state.reset_user()
        self.on_navigate("login")
