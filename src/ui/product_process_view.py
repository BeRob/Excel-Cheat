"""Produkt- und Prozessauswahl."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog
from datetime import datetime
from pathlib import Path

from src.config.process_config import (
    determine_shift,
    get_all_headers,
    get_context_fields,
    get_measurement_fields,
    get_auto_fields,
    get_persistent_context_fields,
)
from src.config.settings import APP_ROOT
from src.ui.base_view import BaseView
from src.ui.analysis_view import AnalysisView
from src.ui.config_editor_view import ConfigEditorView
from src.ui.theme import COLORS, FONTS


class ProductProcessView(BaseView):
    def __init__(self, parent, app_state, on_navigate):
        super().__init__(parent, app_state, on_navigate)
        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        top_bar = ttk.Frame(self)
        top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        top_bar.columnconfigure(0, weight=1)

        self.user_label = ttk.Label(top_bar, text="")
        self.user_label.grid(row=0, column=0, sticky="w")

        ttk.Button(top_bar, text="Abmelden", command=self._logout).grid(
            row=0, column=1
        )

        # Je nach Admin-Flag wird in on_show ein Notebook oder nur die Auswahl angezeigt
        self.main_container = ttk.Frame(self)
        self.main_container.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.rowconfigure(0, weight=1)

    def _build_selection_ui(self, parent: tk.Widget) -> None:
        frame = ttk.Frame(parent, padding=20)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(
            frame, text="Produkt und Prozess wählen", style="Subtitle.TLabel"
        ).grid(row=0, column=0, columnspan=2, pady=(0, 20))

        ttk.Label(frame, text="Produkt:", font=FONTS["body"]).grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=5
        )
        self.product_var = tk.StringVar()
        self.product_combo = ttk.Combobox(
            frame, textvariable=self.product_var, state="readonly", width=60
        )
        self.product_combo.grid(row=1, column=1, sticky="ew", pady=5)
        self.product_combo.bind("<<ComboboxSelected>>", self._on_product_selected)

        ttk.Label(frame, text="Prozess:", font=FONTS["body"]).grid(
            row=2, column=0, sticky="w", padx=(0, 10), pady=5
        )
        self.process_var = tk.StringVar()
        self.process_combo = ttk.Combobox(
            frame, textvariable=self.process_var, state="readonly", width=60
        )
        self.process_combo.grid(row=2, column=1, sticky="ew", pady=5)
        self.process_combo.bind("<<ComboboxSelected>>", self._on_process_selected)

        ttk.Label(frame, text="Schicht:", font=FONTS["body"]).grid(
            row=3, column=0, sticky="w", padx=(0, 10), pady=5
        )
        self.shift_label = ttk.Label(frame, text="", font=FONTS["body"])
        self.shift_label.grid(row=3, column=1, sticky="w", pady=5)

        info_frame = ttk.LabelFrame(frame, text="Prozess-Details", padding=10)
        info_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(15, 5))
        info_frame.columnconfigure(0, weight=1)

        self.info_text = tk.Text(
            info_frame, height=8, wrap="word", state="disabled",
            font=FONTS["small"], bg=COLORS["background"],
            relief="flat", borderwidth=0,
        )
        self.info_text.pack(fill="both", expand=True)

        self.status_var = tk.StringVar()
        ttk.Label(
            frame, textvariable=self.status_var, foreground=COLORS["text_secondary"]
        ).grid(row=5, column=0, columnspan=2, pady=5)

        self.next_btn = ttk.Button(
            frame, text="Weiter", command=self._go_next,
            state="disabled", style="Accent.TButton",
        )
        self.next_btn.grid(row=6, column=0, columnspan=2, pady=15)

    def on_show(self) -> None:
        user = self.app_state.current_user
        if not user:
            return

        for child in self.main_container.winfo_children():
            child.destroy()

        if user.is_admin:
            notebook = ttk.Notebook(self.main_container)
            notebook.pack(fill="both", expand=True)

            selection_tab = ttk.Frame(notebook)
            notebook.add(selection_tab, text="Produkt/Prozess")

            analysis_tab = AnalysisView(notebook, self.app_state)
            notebook.add(analysis_tab, text="Datenauswertung")

            config_editor_tab = ConfigEditorView(notebook, self.app_state)
            notebook.add(config_editor_tab, text="Produktkonfiguration")

            self._build_selection_ui(selection_tab)
        else:
            self._build_selection_ui(self.main_container)

        self.user_label.config(text=f"Angemeldet als: {user.display_name}")

        config = self.app_state.app_config
        if config and config.products:
            product_names = [p.display_name for p in config.products]
            self.product_combo["values"] = product_names

            if self.app_state.selected_product:
                prev = self.app_state.selected_product.display_name
                if prev in product_names:
                    self.product_var.set(prev)
                    self._on_product_selected()
        else:
            self.status_var.set("Keine Produkte konfiguriert.")

        self._update_shift()

    def _update_shift(self) -> None:
        config = self.app_state.app_config
        if config and config.shifts:
            now = datetime.now()
            shift = determine_shift(now.hour, config.shifts)
            self.shift_label.config(text=f"Schicht {shift}")
        else:
            self.shift_label.config(text="Nicht konfiguriert")

    def _on_product_selected(self, event=None) -> None:
        config = self.app_state.app_config
        if not config:
            return

        product_name = self.product_var.get()
        product = next(
            (p for p in config.products if p.display_name == product_name), None
        )
        if not product:
            return

        process_names = [p.display_name for p in product.processes]
        self.process_combo["values"] = process_names

        if self.app_state.selected_process:
            prev = self.app_state.selected_process.display_name
            if prev in process_names:
                self.process_var.set(prev)
                self._on_process_selected()
                return

        self.process_var.set("")
        self._update_info(None)
        self.next_btn.config(state="disabled")

    def _on_process_selected(self, event=None) -> None:
        config = self.app_state.app_config
        if not config:
            return

        product_name = self.product_var.get()
        product = next(
            (p for p in config.products if p.display_name == product_name), None
        )
        if not product:
            return

        process_name = self.process_var.get()
        process = next(
            (p for p in product.processes if p.display_name == process_name), None
        )

        self._update_info(process)
        self.next_btn.config(state="normal" if process else "disabled")

    def _update_info(self, process) -> None:
        self.info_text.config(state="normal")
        self.info_text.delete("1.0", "end")

        if not process:
            self.info_text.insert("1.0", "Bitte Prozess wählen.")
            self.info_text.config(state="disabled")
            return

        lines = []

        ctx = get_context_fields(process)
        if ctx:
            persistent = [f for f in ctx if f.persistent]
            per_meas = [f for f in ctx if not f.persistent]
            if persistent:
                lines.append("Persistent (einmalig):")
                for f in persistent:
                    lines.append(f"  - {f.display_name}")
            if per_meas:
                lines.append("Pro Messung (Kontext):")
                for f in per_meas:
                    lines.append(f"  - {f.display_name}")

        meas = get_measurement_fields(process)
        if meas:
            lines.append("Messwerte:")
            for f in meas:
                spec = ""
                if f.spec_min is not None and f.spec_max is not None:
                    spec = f"  [{f.spec_min} - {f.spec_max}]"
                opt = " (optional)" if f.optional else ""
                lines.append(f"  - {f.display_name}{spec}{opt}")

        auto = get_auto_fields(process)
        if auto:
            lines.append("Automatisch:")
            for f in auto:
                lines.append(f"  - {f.display_name}")

        if process.row_group_size:
            lines.append(f"\nZeilengruppe: {process.row_group_size} Zeilen pro Messung")

        self.info_text.insert("1.0", "\n".join(lines))
        self.info_text.config(state="disabled")

    def _go_next(self) -> None:
        config = self.app_state.app_config
        if not config:
            return

        product_name = self.product_var.get()
        product = next(
            (p for p in config.products if p.display_name == product_name), None
        )
        if not product:
            return

        process_name = self.process_var.get()
        process = next(
            (p for p in product.processes if p.display_name == process_name), None
        )
        if not process:
            return

        now = datetime.now()
        shift = determine_shift(now.hour, config.shifts) if config.shifts else "1"

        # Output-Dir: Produkt-Config hat Vorrang; sonst Ordner-Dialog
        if product.output_dir:
            output_dir = Path(product.output_dir)
            if not output_dir.is_absolute():
                output_dir = APP_ROOT / output_dir
        else:
            chosen = filedialog.askdirectory(
                title="Speicherort für Messdaten wählen",
                mustexist=False,
            )
            if not chosen:
                self.status_var.set("Kein Speicherort gewählt.")
                return
            output_dir = Path(chosen)

        self.app_state.selected_product = product
        self.app_state.selected_process = process
        self.app_state.current_shift = shift
        self.app_state.output_dir = output_dir

        self.app_state.current_headers = get_all_headers(process)
        self.app_state.persistent_headers = [
            f.display_name for f in get_persistent_context_fields(process)
        ]
        self.app_state.measurement_headers = [
            f.display_name for f in get_measurement_fields(process)
        ]

        self.on_navigate("context")

    def _logout(self) -> None:
        self.app_state.reset_user()
        self.on_navigate("login")
