"""
Dateiauswahl-Bildschirm: Excel-Datei und Arbeitsblatt waehlen."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog

from src.config.settings import AUTO_COLUMNS, HEADER_ROW
from src.excel.reader import read_excel_headers
from src.ui.analysis_view import AnalysisView
from src.ui.base_view import BaseView
from src.ui.theme import COLORS, FONTS


class FileSelectView(BaseView):
    """Bildschirm zur Auswahl einer Excel-Datei und des Arbeitsblatts."""

    def __init__(self, parent, app_state, on_navigate):
        super().__init__(parent, app_state, on_navigate)
        self._selected_path: str | None = None
        self._sheet_names: list[str] = []
        self._headers: list[str] = []
        self._notebook: ttk.Notebook | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # We create a container that will either hold the notebook or the selection content directly
        self.main_container = ttk.Frame(self)
        self.main_container.grid(row=0, column=0, sticky="nsew")
        self.main_container.columnconfigure(0, weight=1)

    def _build_selection_ui(self, parent: tk.Widget) -> None:
        parent.columnconfigure(0, weight=1)

        # --- Obere Leiste ---
        top_bar = ttk.Frame(parent)
        top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        top_bar.columnconfigure(0, weight=1)

        self.user_label = ttk.Label(top_bar, text="")
        self.user_label.grid(row=0, column=0, sticky="w")

        logout_btn = ttk.Button(
            top_bar, text="Abmelden", command=self._logout
        )
        logout_btn.grid(row=0, column=1, padx=(10, 0))

        # --- Titel ---
        ttk.Label(parent, text="Datei auswählen", style="Subtitle.TLabel").grid(
            row=1, column=0, pady=(10, 5)
        )

        # --- Datei-Auswahl ---
        file_frame = ttk.Frame(parent)
        file_frame.grid(row=2, column=0, padx=40, pady=5, sticky="ew")
        file_frame.columnconfigure(1, weight=1)

        ttk.Button(
            file_frame, text="Datei wählen...", command=self._choose_file
        ).grid(row=0, column=0, padx=(0, 10))

        self.file_path_var = tk.StringVar(value="Keine Datei ausgewählt")
        ttk.Label(file_frame, textvariable=self.file_path_var, foreground=COLORS["text_secondary"]).grid(
            row=0, column=1, sticky="w"
        )

        # --- Sheet-Auswahl ---
        self.sheet_frame = ttk.Frame(parent)
        self.sheet_frame.grid(row=3, column=0, padx=40, pady=5, sticky="ew")

        ttk.Label(self.sheet_frame, text="Arbeitsblatt:").grid(
            row=0, column=0, padx=(0, 10)
        )
        self.sheet_var = tk.StringVar()
        self.sheet_combo = ttk.Combobox(
            self.sheet_frame, textvariable=self.sheet_var, state="readonly", width=30
        )
        self.sheet_combo.grid(row=0, column=1)
        self.sheet_combo.bind("<<ComboboxSelected>>", lambda e: self._load_headers())

        ttk.Button(
            self.sheet_frame, text="Laden", command=self._load_headers
        ).grid(row=0, column=2, padx=(10, 0))

        self.sheet_frame.grid_remove()  # Verstecken bis Datei geladen

        # --- Header-Vorschau ---
        self.header_frame = ttk.LabelFrame(parent, text="Erkannte Spalten", padding=10)
        self.header_frame.grid(row=4, column=0, padx=40, pady=10, sticky="ew")
        self.header_frame.grid_remove()

        self.header_listbox = tk.Listbox(
            self.header_frame,
            height=8,
            font=FONTS["body"],
            bg=COLORS["background"],
            fg=COLORS["text_primary"],
            selectbackground=COLORS["accent"],
        )
        self.header_listbox.pack(fill="both", expand=True)

        # --- Fehlermeldung ---
        self.error_var = tk.StringVar()
        self.error_label = ttk.Label(parent, textvariable=self.error_var, style="Error.TLabel")
        self.error_label.grid(row=5, column=0, padx=40, pady=5)

        # --- Weiter-Button ---
        self.next_btn = ttk.Button(
            parent, text="Weiter", command=self._go_next, state="disabled",
            style="Accent.TButton",
        )
        self.next_btn.grid(row=6, column=0, pady=15)

    def on_show(self) -> None:
        user = self.app_state.current_user
        if not user:
            return

        # Clear container
        for child in self.main_container.winfo_children():
            child.destroy()

        if user.is_admin:
            # Create Notebook for Admin
            self._notebook = ttk.Notebook(self.main_container)
            self._notebook.pack(fill="both", expand=True)

            selection_tab = ttk.Frame(self._notebook)
            analysis_tab = AnalysisView(self._notebook, self.app_state)

            self._notebook.add(selection_tab, text="Datei auswählen")
            self._notebook.add(analysis_tab, text="Datenauswertung")

            self._build_selection_ui(selection_tab)
        else:
            # Simple View for normal users
            self._build_selection_ui(self.main_container)

        name = user.display_name
        self.user_label.config(text=f"Angemeldet als: {name}")

    def _choose_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Excel-Datei auswählen",
            filetypes=[("Excel-Dateien", "*.xlsx")],
        )
        if not path:
            return

        self._selected_path = path
        self.file_path_var.set(path)
        self.error_var.set("")
        self.next_btn.config(state="disabled")

        # Header laden fuer erstes Sheet
        result = read_excel_headers(path, header_row=HEADER_ROW)

        if result.errors:
            self.error_var.set("\n".join(result.errors))
            self.header_frame.grid_remove()
            self.sheet_frame.grid_remove()
            return

        self._sheet_names = result.sheet_names
        self._update_sheet_combo()
        self._show_headers(result.headers)

    def _update_sheet_combo(self) -> None:
        self.sheet_combo["values"] = self._sheet_names
        if self._sheet_names:
            self.sheet_var.set(self._sheet_names[0])
        if len(self._sheet_names) > 1:
            self.sheet_frame.grid()
        else:
            self.sheet_frame.grid_remove()

    def _load_headers(self) -> None:
        if not self._selected_path:
            return

        sheet = self.sheet_var.get()
        result = read_excel_headers(
            self._selected_path, sheet_name=sheet, header_row=HEADER_ROW
        )

        if result.errors:
            self.error_var.set("\n".join(result.errors))
            self.next_btn.config(state="disabled")
            self.header_frame.grid_remove()
            return

        self.error_var.set("")
        self._show_headers(result.headers)

    def _show_headers(self, headers: list[str]) -> None:
        self._headers = headers
        self.header_listbox.delete(0, "end")

        auto_set = set(AUTO_COLUMNS)
        for h in headers:
            marker = "  [Auto]" if h in auto_set else ""
            self.header_listbox.insert("end", f"{h}{marker}")

        self.header_frame.grid()
        self.next_btn.config(state="normal")

    def _go_next(self) -> None:
        if not self._selected_path:
            return

        sheet = self.sheet_var.get() or (self._sheet_names[0] if self._sheet_names else None)
        if not sheet:
             return

        # Erneut Headers lesen fuer aktuelle Map
        result = read_excel_headers(
            self._selected_path, sheet_name=sheet, header_row=HEADER_ROW
        )
        if result.errors:
            self.error_var.set("\n".join(result.errors))
            return

        # AppState aktualisieren
        self.app_state.current_file = self._selected_path
        self.app_state.current_sheet = sheet
        self.app_state.current_headers = result.headers
        self.app_state.header_column_map = result.header_column_map

        if self.app_state.audit:
            self.app_state.audit.log(
                "file_selected",
                user=self.app_state.current_user.user_id if self.app_state.current_user else None,
                file=str(self._selected_path),
                details={"sheet": sheet},
            )

        self.on_navigate("column_classify")

    def _logout(self) -> None:
        self.app_state.reset_user()
        self._selected_path = None
        self.file_path_var.set("Keine Datei ausgewählt")
        self.header_frame.grid_remove()
        self.sheet_frame.grid_remove()
        self.next_btn.config(state="disabled")
        self.on_navigate("login")