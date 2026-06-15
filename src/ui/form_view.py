"""Dynamische Messwertmaske mit scrollbarem Eingabeformular."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from collections import deque
from datetime import datetime

from src.audit.events import Event
from src.config.process_config import (
    get_measurement_fields,
    get_per_measurement_context_fields,
    get_form_persistent_fields,
    get_info_header_fields,
    get_group_shared_fields,
    get_per_nutzen_fields,
    get_auto_fields,
    is_multi_nutzen,
    FieldDef,
)
from src.config.settings import HEADER_ROW, save_ui_prefs
from src.domain.validation import parse_numeric
from src.excel.reader import read_all_data
from src.excel.writer import write_measurement_row, write_measurement_rows
from src.ui.base_view import BaseView
from src.ui.review_dialog import ReviewDialog
from src.ui.theme import COLORS, FONTS


def _format_spec_text(fd: FieldDef) -> str:
    """Einheitliche Toleranz-/Optional-Anzeige für alle Render-Pfade."""
    parts: list[str] = []
    if fd.spec_min is not None and fd.spec_max is not None:
        parts.append(f"{fd.spec_min} – {fd.spec_max}")
    elif fd.spec_min is not None:
        parts.append(f"≥{fd.spec_min}")
    elif fd.spec_max is not None:
        parts.append(f"≤{fd.spec_max}")
    if fd.optional and not parts:
        parts.append("optional")
    return "  ".join(parts)


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
        # Einmal-pro-Episode-Warnung bei Audit-Totalausfall (Event verloren)
        self._audit_fail_warned: bool = False
        # Machine-scoped (Variante 2): pro Maschine eine "aktive" Rolle merken,
        # automatisch in das machine_scoped Feld übernehmen sobald Maschine gewählt wird.
        self._machine_scoped_fields: list[FieldDef] = []
        self._machine_field: FieldDef | None = None
        self._machine_scoped_entry_vars: dict[tuple[str, str], tk.StringVar] = {}
        self._machine_scoped_trace_lock: bool = False
        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        # row 2 (Messfelder-Scrollbereich) bekommt den ganzen Platz
        self.rowconfigure(2, weight=1)

        # row 0: 1-zeilige Meta-Info (klein, sekundäre Farbe)
        top_bar = ttk.Frame(self)
        top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(6, 2))
        top_bar.columnconfigure(0, weight=1)

        self.meta_label = ttk.Label(
            top_bar, text="",
            foreground=COLORS["text_secondary"],
            font=FONTS["small"],
        )
        self.meta_label.grid(row=0, column=0, sticky="w")

        # row 1: Info-Header-Chips (FA-Nr., LOT, Verwendbarkeit, Messmittel) ✎
        self.header_bar = ttk.Frame(self)
        self.header_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 4))

        # row 2: Scrollbarer Messfelder-Bereich
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

        # row 3: Statuszeile (Erfolg/Fehler nach Speichern)
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(self, textvariable=self.status_var,
                                      style="Success.TLabel")
        self.status_label.grid(row=3, column=0, pady=2)

        # row 4: History-Bar (Toggle + Letzte-Messung-Inline + ⚙)
        self._build_history_bar()

        # row 5: Action-Bar (Navigation links + Felder leeren/Speichern rechts)
        action_bar = ttk.Frame(self)
        action_bar.grid(row=5, column=0, sticky="ew", padx=10, pady=(4, 8))
        action_bar.columnconfigure(1, weight=1)

        nav_left = ttk.Frame(action_bar)
        nav_left.grid(row=0, column=0, sticky="w")
        self.layout_btn = ttk.Button(
            nav_left, text="Layout: Horizontal", command=self._toggle_layout,
        )
        self.layout_btn.pack(side="left", padx=(0, 5))
        ttk.Button(
            nav_left, text="Prozess wechseln", command=self._change_process,
        ).pack(side="left", padx=5)
        ttk.Button(
            nav_left, text="Abmelden", command=self._logout,
        ).pack(side="left", padx=5)

        action_right = ttk.Frame(action_bar)
        action_right.grid(row=0, column=2, sticky="e")
        ttk.Button(
            action_right, text="Felder leeren", command=self._clear_fields,
        ).pack(side="left", padx=(5, 10))
        ttk.Button(
            action_right, text="Speichern", command=self._save,
            style="Accent.TButton",
        ).pack(side="left", padx=(0, 5))

    def _build_history_bar(self) -> None:
        """Schmale Leiste oberhalb der Action-Bar:
        Toggle ▼/▲ + 1-Zeilen-Last-Message + Spaltenwahl-Zahnrad.
        Beim Aufklappen wird darunter ein kompaktes Treeview gegridded."""
        self.history_container = ttk.Frame(self)
        self.history_container.grid(row=4, column=0, sticky="ew", padx=40, pady=(2, 0))
        self.history_container.columnconfigure(0, weight=1)

        bar = ttk.Frame(self.history_container)
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)

        self.history_toggle_btn = ttk.Button(
            bar, text="▼ Verlauf (0)", width=16,
            command=self._toggle_history,
        )
        self.history_toggle_btn.grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.history_last_var = tk.StringVar(value="Noch keine Messung.")
        ttk.Label(
            bar, textvariable=self.history_last_var,
            foreground=COLORS["text_secondary"],
        ).grid(row=0, column=1, sticky="w")

        ttk.Button(
            bar, text="⚙", width=3, command=self._open_history_column_picker,
            style="Manual.TButton",
        ).grid(row=0, column=2, sticky="e", padx=(8, 0))

        # Frame für das Treeview – per default versteckt (collapsed).
        self.history_tree_frame = ttk.Frame(self.history_container)
        # nicht direkt gridden — _apply_history_collapsed entscheidet
        self.history_tree: ttk.Treeview | None = None
        self._history_columns: list[str] = []
        self._history_collapsed: bool = True

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
        file_name = (
            Path(self.app_state.current_file).name
            if self.app_state.current_file else "?"
        )

        self.meta_label.config(
            text=f"{user_name}  ·  {product_name}  ·  {process_name}"
                 f"  ·  Schicht {shift}  ·  {file_name}"
        )

        mode_text = (
            "Vertikal" if self.app_state.layout_mode == "vertical" else "Horizontal"
        )
        self.layout_btn.config(text=f"Layout: {mode_text}")

        self._render_header_bar()

        fields_key = f"{process_name}_{self.app_state.layout_mode}"
        if fields_key != self._last_fields_key:
            self._history.clear()
            self._generate_fields()
            self._last_fields_key = fields_key
            self._load_history_columns_for_process()
            self._apply_history_collapsed(initial=True)
            self._rebuild_history_tree()
            if self.app_state.is_resume:
                self._preload_history()
            self._refresh_history_view()
        else:
            self._set_initial_focus()

        self.status_var.set("")

    def _render_header_bar(self) -> None:
        """Zeigt die Info-Header-Felder read-only mit kleinem ✎-Button."""
        for child in self.header_bar.winfo_children():
            child.destroy()

        process = self.app_state.selected_process
        if not process:
            return

        pv = self.app_state.persistent_values
        for fd in get_info_header_fields(process):
            cell = ttk.Frame(self.header_bar)
            cell.pack(side="left", padx=(0, 14))
            ttk.Label(
                cell, text=f"{fd.display_name}:",
                font=("Segoe UI", 9, "bold"),
            ).pack(side="left")
            ttk.Label(
                cell, text=pv.get(fd.display_name, "") or "—",
                foreground=COLORS["accent"],
            ).pack(side="left", padx=(4, 2))
            ttk.Button(
                cell, text="✎", width=2,
                style="Manual.TButton",
                command=self._change_context,
            ).pack(side="left")

    def _change_context(self) -> None:
        """✎-Button: zurück zur ContextView, um Info-Header zu ändern."""
        if self.app_state.audit:
            user = self.app_state.current_user
            self.app_state.audit.log_event(
                Event.CONTEXT_EDIT_REQUESTED,
                user=user.user_id if user else None,
            )
        self.on_navigate("context")

    def _set_initial_focus(self) -> None:
        if self._first_focus_widget is not None:
            try:
                self._first_focus_widget.focus_set()
            except tk.TclError:
                pass

    def _toggle_layout(self) -> None:
        if self.app_state.layout_mode == "vertical":
            self.app_state.layout_mode = "horizontal"
        else:
            self.app_state.layout_mode = "vertical"

        mode_text = (
            "Vertikal" if self.app_state.layout_mode == "vertical" else "Horizontal"
        )
        self.layout_btn.config(text=f"Layout: {mode_text}")
        self._generate_fields()
        self._last_fields_key = (
            f"{self.app_state.selected_process.display_name}"
            f"_{self.app_state.layout_mode}"
        )
        if self.app_state.audit:
            self.app_state.audit.log_event(
                Event.LAYOUT_TOGGLED,
                details={"mode": self.app_state.layout_mode},
            )

    def _render_machine_scoped_panel(self) -> None:
        """Rendert oben einen Block mit je einer Eingabe pro
        (machine_scoped-Feld × Maschine-Option).

        Beispiel IPC5: zwei Eingaben "Aktive Rolle M1" und "Aktive Rolle M2".
        Der Mitarbeiter trägt hier die gerade laufende Rolle pro Maschine ein
        und ändert nur dann etwas, wenn die Rolle physisch gewechselt wurde.
        Bei jeder Messung wählt er nur die Maschine — die Rolle wird automatisch
        in das Datenfeld übernommen."""
        if not self._machine_scoped_fields or not self._machine_field:
            return

        panel = ttk.LabelFrame(
            self.scrollable_frame,
            text="Aktive Rolle pro Maschine",
            padding=10,
        )
        panel.pack(fill="x", padx=5, pady=(5, 10))

        col = 0
        for fd in self._machine_scoped_fields:
            for opt in self._machine_field.options or []:
                cell = ttk.Frame(panel)
                cell.grid(row=0, column=col, padx=10, sticky="w")
                ttk.Label(
                    cell,
                    text=f"{fd.display_name} M{opt}:",
                    font=("Segoe UI", 9, "bold"),
                ).pack(side="left")
                var = tk.StringVar()
                stored = self.app_state.machine_scoped_values.get(fd.id, {}).get(opt, "")
                var.set(stored)
                entry = ttk.Entry(cell, textvariable=var, width=14)
                entry.pack(side="left", padx=(4, 0))

                self._machine_scoped_entry_vars[(fd.id, opt)] = var

                var.trace_add(
                    "write",
                    lambda *_args, fid=fd.id, machine_opt=opt, v=var:
                    self._on_machine_scoped_entry_change(fid, machine_opt, v),
                )
                col += 1

    def _on_machine_scoped_entry_change(
        self, field_id: str, machine_value: str, var: tk.StringVar,
    ) -> None:
        """Aktive-Rolle-Eingabe geändert: Wert merken und ggf. Datenfeld aktualisieren."""
        if self._machine_scoped_trace_lock:
            return
        val = var.get().strip()
        self.app_state.machine_scoped_values.setdefault(field_id, {})[machine_value] = val
        # Wenn aktuell genau diese Maschine gewählt ist, das Datenfeld synchron halten.
        if not self._machine_field:
            return
        machine_var = self.field_vars.get(self._machine_field.display_name)
        if machine_var and machine_var.get() == machine_value:
            for fd in self._machine_scoped_fields:
                if fd.id == field_id and fd.display_name in self.field_vars:
                    self._machine_scoped_trace_lock = True
                    try:
                        self.field_vars[fd.display_name].set(val)
                    finally:
                        self._machine_scoped_trace_lock = False
                    break

    def _install_machine_change_trace(self) -> None:
        """Bindet die Maschine-Auswahl an die machine_scoped Datenfelder."""
        if not self._machine_field:
            return
        machine_var = self.field_vars.get(self._machine_field.display_name)
        if machine_var is None:
            return

        def on_machine_change(*_args):
            if self._machine_scoped_trace_lock:
                return
            value = machine_var.get()
            for fd in self._machine_scoped_fields:
                stored = self.app_state.machine_scoped_values.get(fd.id, {}).get(value, "")
                target = self.field_vars.get(fd.display_name)
                if target is not None:
                    self._machine_scoped_trace_lock = True
                    try:
                        target.set(stored)
                    finally:
                        self._machine_scoped_trace_lock = False

        machine_var.trace_add("write", on_machine_change)
        # Initial einmal triggern, falls Maschine bereits einen Wert hat
        on_machine_change()

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
        self._machine_scoped_fields = []
        self._machine_field = None
        self._machine_scoped_entry_vars.clear()

        process = self.app_state.selected_process
        if not process:
            self._is_multi_nutzen = False
            return

        self._is_multi_nutzen = is_multi_nutzen(process)

        # Machine-scoped Setup (Variante 2): wenn Felder mit machine_scoped=true
        # existieren UND ein Maschine-Choice-Feld vorhanden ist, oben einen Slot
        # pro (Feld × Maschine) anzeigen und dem Datenfeld den passenden Wert zuweisen.
        self._machine_scoped_fields = [f for f in process.fields if f.machine_scoped]
        if self._machine_scoped_fields:
            self._machine_field = next(
                (f for f in process.fields
                 if f.id == "maschine" and f.type == "choice" and f.options),
                None,
            )
            if self._machine_field is None:
                # Keine Maschine-Auswahl gefunden – Feature deaktivieren
                self._machine_scoped_fields = []

        if self._machine_scoped_fields and self._machine_field:
            self._render_machine_scoped_panel()

        persistent_fields = get_form_persistent_fields(process)
        self._persistent_field_defs = persistent_fields

        if persistent_fields:
            ctx_frame = ttk.LabelFrame(
                self.scrollable_frame, text="Feste Werte", padding=10,
            )
            ctx_frame.pack(fill="x", padx=5, pady=(5, 10))
            ctx_frame.columnconfigure(1, weight=1)
            ctx_frame.columnconfigure(2, weight=0)

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

                spec_text = _format_spec_text(fd)
                if spec_text:
                    ttk.Label(
                        ctx_frame, text=spec_text,
                        foreground=COLORS["text_secondary"],
                        font=("Segoe UI", 8),
                    ).grid(row=i, column=2, sticky="w", pady=3, padx=(5, 0))

                self.persistent_vars[fd.display_name] = var

        if self._is_multi_nutzen:
            self._generate_multi_nutzen_fields(process)
        else:
            per_meas_ctx_all = get_per_measurement_context_fields(process)
            measurement = get_measurement_fields(process)

            scoped_ids = {f.id for f in self._machine_scoped_fields}
            per_meas_ctx_render = [
                f for f in per_meas_ctx_all if f.id not in scoped_ids
            ]
            # Hidden StringVars für machine_scoped Felder, damit sie im Save-Pfad
            # auftauchen obwohl sie kein eigenes Eingabe-Widget haben.
            for fd in self._machine_scoped_fields:
                self.field_vars[fd.display_name] = tk.StringVar()

            shared_frame_first: tk.Widget | None = None
            if per_meas_ctx_render:
                shared_frame = ttk.LabelFrame(
                    self.scrollable_frame, text="Gemeinsame Werte", padding=10,
                )
                shared_frame.pack(fill="x", padx=5, pady=(0, 5))
                if self.app_state.layout_mode == "vertical":
                    shared_frame_first, _ = self._generate_vertical_fields(
                        per_meas_ctx_render, shared_frame,
                    )
                else:
                    shared_frame_first, _ = self._generate_horizontal_fields(
                        per_meas_ctx_render, shared_frame,
                    )

            choice_fields = [f for f in measurement if f.type == "choice"]
            other_fields = [f for f in measurement if f.type != "choice"]
            display_fields = choice_fields + other_fields
            # _field_defs enthält ALLE per_meas_ctx Felder (auch machine_scoped),
            # damit ReviewDialog und Writer die Werte sehen.
            self._field_defs = per_meas_ctx_all + display_fields

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

            self._first_focus_widget = (
                first_choice or shared_frame_first or first_meas
            )

        # Maschine→Rolle-Bindung installieren, sobald die Maschine-Var existiert.
        if self._machine_scoped_fields and self._machine_field:
            self._install_machine_change_trace()

        self._set_initial_focus()
        self.canvas.yview_moveto(0)

    def _generate_multi_nutzen_fields(self, process) -> None:
        """Baut das Multi-Nutzen-Formular: Anzahl-Wähler, Gemeinsame Werte, Nutzen-Sektionen."""
        max_nutzen = process.row_group_size

        # Anzahl-Nutzen-Wähler – default: alle Nutzen (row_group_size) sichtbar
        if self.app_state.nutzen_count <= 1 or self.app_state.nutzen_count > max_nutzen:
            self.app_state.nutzen_count = max_nutzen

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
        if self.app_state.layout_mode == "vertical":
            first_shared, _ = self._generate_vertical_fields(shared_fields, shared_frame)
        else:
            first_shared, _ = self._generate_horizontal_fields(shared_fields, shared_frame)
        if self._first_focus_widget is None:
            self._first_focus_widget = first_shared

        # Per-Nutzen-Felder speichern
        self._nutzen_field_defs = get_per_nutzen_fields(process)

        # Container für Nutzen-Sektionen
        self._nutzen_sections_parent = ttk.Frame(self.scrollable_frame)
        self._nutzen_sections_parent.pack(fill="x", padx=5, pady=(0, 5))

        self._rebuild_nutzen_sections()

    def _rebuild_nutzen_sections(self) -> None:
        """Baut die Nutzen-Sektionen neu auf wenn die Anzahl geändert wird.

        Im vertikalen Layout-Modus stehen die Sektionen untereinander,
        im horizontalen Modus nebeneinander."""
        if self._nutzen_sections_parent is None or self._nutzen_count_var is None:
            return

        count = self._nutzen_count_var.get()
        if count != self.app_state.nutzen_count and self.app_state.audit:
            self.app_state.audit.log_event(
                Event.NUTZEN_COUNT_CHANGED,
                details={"from": self.app_state.nutzen_count, "to": count},
            )
        self.app_state.nutzen_count = count

        # Alte per-nutzen Einträge aus field_vars und Border-Map entfernen
        for key in [k for k in self.field_vars if "_n" in k]:
            del self.field_vars[key]
        for key in [k for k in self._validation_borders if "_n" in k]:
            del self._validation_borders[key]

        for widget in self._nutzen_sections_parent.winfo_children():
            widget.destroy()

        horizontal = self.app_state.layout_mode == "horizontal"
        if horizontal:
            for c in range(count):
                self._nutzen_sections_parent.columnconfigure(c, weight=1, uniform="nutzen")

        for i in range(1, count + 1):
            section = ttk.LabelFrame(
                self._nutzen_sections_parent,
                text=f"Nutzen {i}",
                padding=10,
            )
            if horizontal:
                section.grid(row=0, column=i - 1, sticky="nsew", padx=(0, 5))
            else:
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

                widget, container = self._create_field_widget(
                    section, fd, var, border_key=key,
                )
                container.grid(row=row_idx, column=1, sticky="w", pady=5, padx=(0, 10))

                spec_text = _format_spec_text(fd)
                if spec_text:
                    ttk.Label(
                        section,
                        text=spec_text,
                        foreground=COLORS["text_secondary"],
                        font=("Segoe UI", 8),
                    ).grid(row=row_idx, column=2, sticky="w", pady=5, padx=(5, 0))

                self.field_vars[key] = var

        self.canvas.yview_moveto(0)

    def _preload_history(self) -> None:
        """Lädt die letzten Messungen aus der Excel-Datei beim Resume.

        Jeder Eintrag ist ein Dict mit allen Spaltenwerten plus 'Zeit'.
        Welche Spalten angezeigt werden, entscheidet `_history_columns`."""
        if not self.app_state.current_file:
            return
        process = self.app_state.selected_process
        if not process:
            return

        rows = read_all_data(self.app_state.current_file, header_row=HEADER_ROW)
        if not rows:
            return

        self._history.clear()
        for row in rows[-10:]:
            datum = str(row.get("Datum", "") or "")
            zeit = datum[-8:] if len(datum) >= 8 else datum
            entry: dict[str, str] = {"Zeit": zeit}
            for k, v in row.items():
                if v is None:
                    continue
                entry[str(k)] = str(v)
            self._history.append(entry)

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

            spec_text = _format_spec_text(fd)
            if spec_text:
                ttk.Label(
                    parent, text=spec_text,
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

            ttk.Label(cell, text=f"{fd.display_name}:",
                      font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")

            var = tk.StringVar()
            if fd.role == "context" and fd.display_name in self.app_state.persistent_values:
                var.set(self.app_state.persistent_values[fd.display_name])
            elif fd.default_value is not None:
                var.set(fd.default_value)

            widget, container = self._create_field_widget(cell, fd, var)
            container.grid(row=1, column=0, sticky="ew", pady=(2, 0))

            spec_text = _format_spec_text(fd)
            if spec_text:
                ttk.Label(
                    cell, text=spec_text,
                    foreground=COLORS["text_secondary"],
                    font=("Segoe UI", 8),
                ).grid(row=2, column=0, sticky="w", pady=(2, 0))

            self.field_vars[fd.display_name] = var
            if i == 0:
                first_widget = widget
            if first_choice is None and fd.type == "choice":
                first_choice = widget

        return first_widget, first_choice

    def _create_field_widget(
        self, parent: tk.Widget, fd: FieldDef, var: tk.StringVar,
        border_key: str | None = None,
    ) -> tuple[tk.Widget, tk.Widget]:
        """Gibt (input_widget, container) zurück.

        Alle Felder werden in einen 3px-Container gewickelt, damit die
        Außenmaße identisch sind (Spec-Felder haben einen farbigen Border,
        andere einen transparenten Spacer in der Hintergrundfarbe).

        `border_key` wird zum Speichern des Borders verwendet (default =
        display_name); bei per-Nutzen-Feldern wird ein eindeutiger Schlüssel
        mit Suffix `_n{i}` benötigt, damit Borders unabhängig validiert
        werden können."""
        has_spec = fd.type == "number" and (fd.spec_min is not None or fd.spec_max is not None)
        key = border_key if border_key is not None else fd.display_name

        if fd.type == "choice" and fd.options:
            container = tk.Frame(
                parent, bg=COLORS["background"], padx=3, pady=3,
            )
            widget = ttk.Combobox(
                container, textvariable=var, values=fd.options,
                state="readonly", width=23,
            )
            widget.pack(fill="both", expand=True)
            widget.bind("<Return>", self._focus_next)
            return widget, container

        if has_spec:
            border = tk.Frame(parent, bg=COLORS["border"], padx=3, pady=3)
            entry = ttk.Entry(border, textvariable=var, width=23)
            entry.pack(fill="both", expand=True)
            entry.bind("<Return>", self._focus_next)
            entry.bind("<Down>", self._focus_next)
            entry.bind("<Up>", self._focus_prev)
            entry.bind(
                "<FocusOut>",
                lambda e, f=fd, v=var, bk=key: self._on_spec_check(f, v, bk),
            )
            self._validation_borders[key] = border
            return entry, border

        container = tk.Frame(parent, bg=COLORS["background"], padx=3, pady=3)
        widget = ttk.Entry(container, textvariable=var, width=23)
        widget.pack(fill="both", expand=True)
        widget.bind("<Return>", self._focus_next)
        widget.bind("<Down>", self._focus_next)
        widget.bind("<Up>", self._focus_prev)
        return widget, container

    def _focus_next(self, event) -> str:
        event.widget.tk_focusNext().focus_set()
        return "break"

    def _focus_prev(self, event) -> str:
        event.widget.tk_focusPrev().focus_set()
        return "break"

    def _on_spec_check(
        self, fd: FieldDef, var: tk.StringVar, border_key: str | None = None,
    ) -> None:
        key = border_key if border_key is not None else fd.display_name
        border = self._validation_borders.get(key)
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
        if self.app_state.audit:
            self.app_state.audit.log_event(
                Event.FIELDS_CLEARED,
                user=(self.app_state.current_user.user_id
                      if self.app_state.current_user else None),
                details={"field_count": len(self.field_vars)},
            )
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

        if self.app_state.audit:
            self.app_state.audit.log_event(
                Event.REVIEW_OPENED,
                user=(self.app_state.current_user.user_id
                      if self.app_state.current_user else None),
                details={"multi_nutzen": self._is_multi_nutzen},
            )

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
            on_cancel=self._on_review_cancelled,
        )

    def _on_review_cancelled(
        self,
        blocked_sections: list[str],
        oos_details: dict[str, list[dict]] | None = None,
    ) -> None:
        if not self.app_state.audit:
            return
        user_id = (
            self.app_state.current_user.user_id
            if self.app_state.current_user else None
        )
        process = self.app_state.selected_process
        tpl_details = self._template_details(process) if process else {}
        if blocked_sections:
            # GMP: Werte + Grenzen mitloggen — ein OOS_BLOCKED ohne die
            # betroffenen Messwerte wäre für einen Auditor nicht nachvollziehbar.
            self.app_state.audit.log_event(
                Event.OOS_BLOCKED, level="warn", user=user_id,
                file=str(self.app_state.current_file),
                details={
                    "sections": blocked_sections,
                    "oos_fields": oos_details or {},
                    **tpl_details,
                },
            )
        self.app_state.audit.log_event(
            Event.REVIEW_CANCELLED, user=user_id,
            details={"blocked_sections": blocked_sections, **tpl_details},
        )

    def _template_details(self, process) -> dict:
        """Template-Herkunft für den Audit-Trail (GMP: welche Template-Version
        hat die Excel-Datei erzeugt). Leeres Dict für Legacy-Prozesse ohne Template."""
        details: dict = {}
        if getattr(process, "template", None):
            details["template"] = process.template
            details["template_revision"] = process.template_revision
        return details

    def _audit_health_suffix(self) -> str:
        """Warntext für die Statuszeile, falls der Audit-Trail gerade ausweicht.

        Ein stiller Audit-Ausfall würde Lücken in der GMP-Dokumentation
        erzeugen, ohne dass es jemand merkt. Bei Totalausfall (auch der
        lokale Puffer schlug fehl = Event verloren) zusätzlich einmalig
        eine Warnbox."""
        audit = self.app_state.audit
        if not audit or not audit.degraded_reason:
            self._audit_fail_warned = False
            return ""
        if audit.degraded_reason == "fallback_failed":
            if not self._audit_fail_warned:
                self._audit_fail_warned = True
                messagebox.showwarning(
                    "Audit-Log ausgefallen",
                    "Das Audit-Ereignis konnte weder ins Audit-Log noch in "
                    "den lokalen Puffer geschrieben werden — die "
                    "GMP-Dokumentation ist unvollständig.\n\nBitte IT "
                    "informieren.",
                )
            return "  ⚠ Audit-Log AUSGEFALLEN — IT informieren!"
        return "  ⚠ Audit-Log nicht erreichbar — Ereignisse werden lokal gepuffert."

    def _do_write(self, normalized_values: dict[str, float | str | None]) -> None:
        process = self.app_state.selected_process
        if not process:
            return

        if self.app_state.audit:
            self.app_state.audit.log_event(
                Event.WRITE_ATTEMPT,
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
        seq_increments = 0
        for fd in get_auto_fields(process):
            if fd.id == "datum":
                auto_values[fd.display_name] = now.strftime("%Y-%m-%d %H:%M:%S")
            elif fd.id == "bearbeiter":
                user = self.app_state.current_user
                auto_values[fd.display_name] = user.display_name if user else ""
            elif fd.id == "nutzen" and process.row_group_size:
                nutzen = (self.app_state.row_group_counter % process.row_group_size) + 1
                auto_values[fd.display_name] = nutzen
            elif fd.id in ("pruefmuster", "beutel_nr"):
                self.app_state.auto_sequence += 1
                seq_increments += 1
                auto_values[fd.display_name] = self.app_state.auto_sequence
            elif fd.id == "karton":
                # 20 Beutel pro Karton — abgeleitet aus dem aktuellen auto_sequence
                # (Bag-Nr.). pruefmuster muss in process.fields VOR karton stehen.
                bag_no = self.app_state.auto_sequence
                auto_values[fd.display_name] = ((bag_no - 1) // 20) + 1 if bag_no >= 1 else 1

        result = write_measurement_row(
            filepath=self.app_state.current_file,
            process=process,
            context_values=context_values,
            measurements=measurement_values,
            auto_values=auto_values,
        )

        if result.success:
            self.app_state.row_group_counter += 1

            self._add_to_history(normalized_values)

            if self.app_state.audit:
                self.app_state.audit.log_event(
                    Event.WRITE_SUCCESS,
                    user=self.app_state.current_user.user_id if self.app_state.current_user else None,
                    file=str(self.app_state.current_file),
                    context=dict(self.app_state.persistent_values),
                    details={"row": result.row_number, **self._template_details(process)},
                )

            suffix = self._audit_health_suffix()
            self.status_var.set(
                f"Zeile {result.row_number} erfolgreich geschrieben.{suffix}"
            )
            self.status_label.config(
                style="Warning.TLabel" if suffix else "Success.TLabel"
            )
            self._clear_fields()
        else:
            messagebox.showerror("Fehler beim Schreiben", result.error)
            self.status_var.set(f"Fehler: {result.error}")
            self.status_label.config(style="Error.TLabel")

            # Sequenz exakt um die Zahl der Inkremente zurücknehmen — pauschal
            # -1 wäre falsch, falls ein Prozess mehrere Sequenz-Felder hätte.
            if seq_increments:
                self.app_state.auto_sequence -= seq_increments

            if self.app_state.audit:
                self.app_state.audit.log_event(
                    Event.WRITE_FAIL, level="error",
                    user=self.app_state.current_user.user_id if self.app_state.current_user else None,
                    file=str(self.app_state.current_file),
                    context=dict(self.app_state.persistent_values),
                    details={"error": result.error},
                )

    def _do_multi_nutzen_save(self) -> None:
        """Öffnet den Multi-Nutzen-ReviewDialog mit getrennten Blöcken pro Nutzen."""
        process = self.app_state.selected_process
        if not process:
            return

        nutzen_count = self.app_state.nutzen_count

        shared_raw = {
            fd.display_name: self.field_vars.get(fd.display_name, tk.StringVar()).get()
            for fd in self._field_defs
        }

        nutzen_raw_list: list[dict[str, str]] = []
        for i in range(1, nutzen_count + 1):
            nutzen_raw: dict[str, str] = {}
            for fd in self._nutzen_field_defs:
                key = f"{fd.display_name}_n{i}"
                nutzen_raw[fd.display_name] = self.field_vars.get(
                    key, tk.StringVar(),
                ).get()
            nutzen_raw_list.append(nutzen_raw)

        ReviewDialog(
            parent=self,
            app_state=self.app_state,
            on_confirm=self._on_multi_nutzen_confirmed,
            on_cancel=self._on_review_cancelled,
            shared_values=shared_raw,
            shared_field_defs=self._field_defs,
            nutzen_values=nutzen_raw_list,
            nutzen_field_defs=self._nutzen_field_defs,
        )

    def _on_multi_nutzen_confirmed(
        self,
        shared_normalized: dict[str, float | str | None],
        nutzen_normalized: list[dict[str, float | str | None]],
    ) -> None:
        """Empfängt die normalisierten Werte aus dem ReviewDialog und schreibt."""
        self._do_multi_nutzen_write(shared_normalized, nutzen_normalized)

    def _do_multi_nutzen_write(
        self,
        shared_normalized: dict[str, float | str | None],
        nutzen_normalized: list[dict[str, float | str | None]],
    ) -> None:
        process = self.app_state.selected_process
        if not process:
            return

        nutzen_count = len(nutzen_normalized)
        now = datetime.now()

        context_values: dict[str, str] = {}
        context_values.update(self.app_state.persistent_values)
        shared_meas: dict[str, float | str | None] = {}
        for fd in self._field_defs:
            value = shared_normalized.get(fd.display_name)
            if fd.role == "context":
                context_values[fd.display_name] = (
                    str(value) if value is not None else ""
                )
            else:
                shared_meas[fd.display_name] = value

        rows = []
        for i, per_nutzen in enumerate(nutzen_normalized, 1):
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
            self.app_state.audit.log_event(
                Event.WRITE_ATTEMPT,
                user=self.app_state.current_user.user_id if self.app_state.current_user else None,
                file=str(self.app_state.current_file),
                context=dict(self.app_state.persistent_values),
                details={"nutzen_count": nutzen_count},
            )

        result = write_measurement_rows(
            filepath=self.app_state.current_file,
            rows=rows,
            process=process,
        )

        if result.success:
            self.app_state.row_group_counter += nutzen_count

            for i, row in enumerate(rows, 1):
                meas_vals = {**shared_meas}
                for fd in self._nutzen_field_defs:
                    meas_vals[fd.display_name] = row.get(fd.display_name)
                self._add_to_history(meas_vals, label=f"Nutzen {i}")

            if self.app_state.audit:
                self.app_state.audit.log_event(
                    Event.WRITE_SUCCESS,
                    user=self.app_state.current_user.user_id if self.app_state.current_user else None,
                    file=str(self.app_state.current_file),
                    context=dict(self.app_state.persistent_values),
                    details={"last_row": result.row_number, "nutzen_count": nutzen_count,
                             **self._template_details(process)},
                )

            suffix = self._audit_health_suffix()
            self.status_var.set(
                f"{nutzen_count} Nutzen gespeichert (bis Zeile {result.row_number})."
                f"{suffix}"
            )
            self.status_label.config(
                style="Warning.TLabel" if suffix else "Success.TLabel"
            )
            self._clear_fields()
        else:
            messagebox.showerror("Fehler beim Schreiben", result.error)
            self.status_var.set(f"Fehler: {result.error}")
            self.status_label.config(style="Error.TLabel")
            if self.app_state.audit:
                self.app_state.audit.log_event(
                    Event.WRITE_FAIL, level="error",
                    user=self.app_state.current_user.user_id if self.app_state.current_user else None,
                    file=str(self.app_state.current_file),
                    context=dict(self.app_state.persistent_values),
                    details={"error": result.error},
                )

    def _add_to_history(
        self, measurements: dict[str, float | str | None], label: str = "",
        extra_context: dict[str, str] | None = None,
    ) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        if label:
            timestamp = f"{timestamp} ({label})"

        entry: dict[str, str] = {"Zeit": timestamp}
        # Persistente Kontext-Werte mit aufnehmen, damit die Spaltenwahl
        # diese ebenfalls anzeigen kann.
        for k, v in self.app_state.persistent_values.items():
            if v:
                entry[k] = str(v)
        if extra_context:
            for k, v in extra_context.items():
                if v:
                    entry[k] = str(v)
        for k, v in measurements.items():
            if v is not None:
                entry[str(k)] = str(v)

        self._history.append(entry)
        self._refresh_history_view()

    def _refresh_history_view(self) -> None:
        """Aktualisiert Toggle-Button-Text, Last-Message und ggf. Tree."""
        count = len(self._history)
        arrow = "▼" if self._history_collapsed else "▲"
        self.history_toggle_btn.config(text=f"{arrow} Verlauf ({count})")

        if self._history:
            last = self._history[-1]
            cols = [c for c in self._history_columns if c != "Zeit"]
            if not cols:
                cols = [k for k in last.keys() if k != "Zeit"]
            parts = [f"{c}: {last[c]}" for c in cols if c in last]
            zeit = last.get("Zeit", "")
            msg = f"Zuletzt {zeit} — " + (", ".join(parts) if parts else "—")
            self.history_last_var.set(msg)
        else:
            self.history_last_var.set("Noch keine Messung.")

        if self.history_tree is not None:
            self._update_history_display()

    def _update_history_display(self) -> None:
        if self.history_tree is None:
            return
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for entry in reversed(self._history):
            values = tuple(entry.get(col, "") for col in self._history_columns)
            self.history_tree.insert("", "end", values=values)

    def _change_process(self) -> None:
        self.app_state.reset_process()
        self._history.clear()
        self._refresh_history_view()
        self.on_navigate("product_process")

    def _logout(self) -> None:
        if self.app_state.audit:
            user = self.app_state.current_user
            self.app_state.audit.log_event(
                Event.LOGOUT, user=user.user_id if user else None,
            )
        self.app_state.reset_user()
        self._history.clear()
        self._refresh_history_view()
        self.on_navigate("login")

    # ---------------------------------------------------------------
    # History-Spaltenwahl und Einklapp-Logik
    # ---------------------------------------------------------------

    def _process_key(self) -> str:
        """Schlüssel für ui_prefs.history_columns pro Prozess."""
        process = self.app_state.selected_process
        return process.display_name if process else "_"

    def _default_history_columns(self) -> list[str]:
        """Default: Zeit + alle measurement-Felder + ausgewählte Kontextfelder."""
        process = self.app_state.selected_process
        if not process:
            return ["Zeit"]
        cols: list[str] = ["Zeit"]
        wanted_context_ids = {"rollencharge", "rollen_nr", "bahn", "nutzen", "maschine"}
        for fd in process.fields:
            if fd.role == "measurement":
                cols.append(fd.display_name)
            elif fd.id in wanted_context_ids and fd.role == "context":
                cols.append(fd.display_name)
            elif fd.id == "nutzen" and fd.role == "auto":
                cols.append(fd.display_name)
        return cols

    def _load_history_columns_for_process(self) -> None:
        prefs = self.app_state.ui_prefs or {}
        hc = prefs.get("history_columns", {}) if isinstance(prefs, dict) else {}
        saved = hc.get(self._process_key()) if isinstance(hc, dict) else None
        if isinstance(saved, list) and saved:
            self._history_columns = [str(c) for c in saved]
        else:
            self._history_columns = self._default_history_columns()
        self._history_collapsed = bool(prefs.get("history_collapsed", True))

    def _save_history_columns(self) -> None:
        prefs = self.app_state.ui_prefs or {}
        if not isinstance(prefs, dict):
            prefs = {}
        hc = prefs.get("history_columns")
        if not isinstance(hc, dict):
            hc = {}
        hc[self._process_key()] = list(self._history_columns)
        prefs["history_columns"] = hc
        prefs["history_collapsed"] = self._history_collapsed
        self.app_state.ui_prefs = prefs
        save_ui_prefs(prefs)

    def _rebuild_history_tree(self) -> None:
        """Baut das Treeview mit den aktuell gewählten Spalten neu auf."""
        for child in self.history_tree_frame.winfo_children():
            child.destroy()
        self.history_tree = None

        if not self._history_columns:
            return

        self.history_tree_frame.columnconfigure(0, weight=1)
        self.history_tree_frame.rowconfigure(0, weight=1)

        self.history_tree = ttk.Treeview(
            self.history_tree_frame,
            columns=tuple(self._history_columns),
            show="headings",
            height=5,
        )
        for col in self._history_columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=110, minwidth=70, anchor="w")

        scrollbar = ttk.Scrollbar(
            self.history_tree_frame, orient="vertical",
            command=self.history_tree.yview,
        )
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        self.history_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

    def _apply_history_collapsed(self, initial: bool = False) -> None:
        """Zeigt/versteckt das Tree-Frame entsprechend `_history_collapsed`."""
        if self._history_collapsed:
            self.history_tree_frame.grid_forget()
        else:
            self.history_tree_frame.grid(
                row=1, column=0, sticky="ew", pady=(4, 0),
            )
        # Toggle-Button-Text aktualisieren ist Aufgabe von _refresh_history_view

    def _toggle_history(self) -> None:
        self._history_collapsed = not self._history_collapsed
        self._apply_history_collapsed()
        self._refresh_history_view()
        self._save_history_columns()
        if self.app_state.audit:
            self.app_state.audit.log_event(
                Event.HISTORY_TOGGLED,
                details={"collapsed": self._history_collapsed},
            )

    def _open_history_column_picker(self) -> None:
        process = self.app_state.selected_process
        if not process:
            return
        available: list[str] = ["Zeit"]
        for fd in process.fields:
            if fd.role in ("context", "measurement", "auto"):
                if fd.display_name not in available:
                    available.append(fd.display_name)

        dialog = tk.Toplevel(self)
        dialog.title("Verlauf: Spalten auswählen")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.configure(bg=COLORS["background"])

        ttk.Label(
            dialog, text="Welche Spalten sollen im Verlauf angezeigt werden?",
            style="Subtitle.TLabel",
        ).pack(padx=15, pady=(15, 8), anchor="w")

        check_frame = ttk.Frame(dialog)
        check_frame.pack(fill="both", expand=True, padx=15)
        vars_map: dict[str, tk.BooleanVar] = {}
        for name in available:
            v = tk.BooleanVar(value=name in self._history_columns)
            vars_map[name] = v
            ttk.Checkbutton(check_frame, text=name, variable=v).pack(anchor="w")

        btn_row = ttk.Frame(dialog)
        btn_row.pack(fill="x", padx=15, pady=15)

        def on_ok():
            new_cols = [name for name in available if vars_map[name].get()]
            if not new_cols:
                new_cols = ["Zeit"]
            self._history_columns = new_cols
            self._save_history_columns()
            self._rebuild_history_tree()
            self._refresh_history_view()
            if self.app_state.audit:
                self.app_state.audit.log_event(
                    Event.HISTORY_COLUMNS_CHANGED,
                    details={
                        "process": self._process_key(),
                        "columns": new_cols,
                    },
                )
            dialog.destroy()

        ttk.Button(btn_row, text="Abbrechen", command=dialog.destroy).pack(
            side="right", padx=5,
        )
        ttk.Button(
            btn_row, text="OK", command=on_ok, style="Accent.TButton",
        ).pack(side="right", padx=5)
