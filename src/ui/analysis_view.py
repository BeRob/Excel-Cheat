"""Analyse-Bildschirm: Auswertung der Excel-Daten."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path

from src.config.settings import HEADER_ROW
from src.excel.reader import read_all_data
from src.ui.base_view import BaseView
from src.ui.theme import COLORS, FONTS


class AnalysisView(ttk.Frame):
    """View zur Anzeige und Auswertung von Excel-Daten."""

    def __init__(self, parent, app_state):
        super().__init__(parent)
        self.app_state = app_state
        self._selected_path: str | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # --- Titel ---
        ttk.Label(self, text="Datenauswertung", style="Subtitle.TLabel").grid(
            row=0, column=0, pady=(10, 5)
        )

        # --- Datei-Auswahl ---
        file_frame = ttk.Frame(self)
        file_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        file_frame.columnconfigure(1, weight=1)

        ttk.Button(
            file_frame, text="Datei wählen...", command=self._choose_file
        ).grid(row=0, column=0, padx=(0, 10))

        self.file_path_var = tk.StringVar(value="Keine Datei ausgewählt")
        ttk.Label(file_frame, textvariable=self.file_path_var, foreground=COLORS["text_secondary"]).grid(
            row=0, column=1, sticky="w"
        )
        
        ttk.Button(file_frame, text="Aktualisieren", command=self._load_data).grid(row=0, column=2, padx=5)

        # --- Tabelle (Treeview) ---
        table_frame = ttk.Frame(self)
        table_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(table_frame, show="headings")
        self.tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # --- Status ---
        self.status_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var, style="Error.TLabel").grid(row=3, column=0, pady=5)

    def _choose_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Excel-Datei zur Auswertung auswählen",
            filetypes=[("Excel-Dateien", "*.xlsx")],
        )
        if not path:
            return

        self._selected_path = path
        self.file_path_var.set(path)
        self._load_data()

    def _load_data(self) -> None:
        if not self._selected_path:
            return

        self.status_var.set("Lade Daten...")
        self.update_idletasks()
        
        data = read_all_data(self._selected_path, header_row=HEADER_ROW)
        
        # Clear tree
        self.tree.delete(*self.tree.get_children())
        
        if not data:
            self.status_var.set("Keine Daten gefunden oder Datei gesperrt.")
            return
            
        self.status_var.set(f"{len(data)} Zeilen geladen.")
        
        # Set columns
        headers = list(data[0].keys())
        self.tree["columns"] = headers
        
        for h in headers:
            self.tree.heading(h, text=h)
            self.tree.column(h, width=100, anchor="w")
            
        # Add data
        for row in data:
            values = [row.get(h, "") for h in headers]
            self.tree.insert("", "end", values=values)
