"""Admin-Editor für Produktkonfigurationen."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from src.config.config_writer import (
    save_product_config,
    validate_product_config,
)
from src.config.process_config import (
    FieldDef,
    ProcessConfig,
    ProductConfig,
    load_app_config,
    load_product_config,
)
from src.config.settings import APP_CONFIG_PATH, PRODUCTS_DIR
from src.ui.theme import COLORS, FONTS


class ConfigEditorView(ttk.Frame):
    """Erstellt und bearbeitet die Produkt-JSONs unter data/products/."""

    def __init__(self, parent, app_state):
        super().__init__(parent)
        self.app_state = app_state

        self._product: ProductConfig | None = None
        self._selected_process_idx: int | None = None
        self._dirty: bool = False

        self._build_ui()
        self._load_product_list()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        product_frame = ttk.LabelFrame(self, text="Produkt", padding=10)
        product_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        product_frame.columnconfigure(1, weight=1)

        load_frame = ttk.Frame(product_frame)
        load_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        load_frame.columnconfigure(0, weight=1)

        self._product_combo = ttk.Combobox(load_frame, state="readonly", width=30)
        self._product_combo.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        ttk.Button(load_frame, text="Laden", command=self._on_load).grid(
            row=0, column=1, padx=2
        )
        ttk.Button(load_frame, text="Neu", command=self._on_new).grid(
            row=0, column=2, padx=2
        )
        ttk.Button(load_frame, text="Kopieren", command=self._on_copy).grid(
            row=0, column=3, padx=2
        )

        ttk.Label(product_frame, text="Produkt-ID:").grid(
            row=1, column=0, sticky="w", pady=2
        )
        self._product_id_var = tk.StringVar()
        self._product_id_var.trace_add("write", lambda *_: self._mark_dirty())
        ttk.Entry(product_frame, textvariable=self._product_id_var, width=30).grid(
            row=1, column=1, sticky="w", pady=2
        )

        ttk.Label(product_frame, text="Anzeigename:").grid(
            row=2, column=0, sticky="w", pady=2
        )
        self._product_name_var = tk.StringVar()
        self._product_name_var.trace_add("write", lambda *_: self._mark_dirty())
        ttk.Entry(product_frame, textvariable=self._product_name_var, width=50).grid(
            row=2, column=1, columnspan=2, sticky="ew", pady=2
        )

        ttk.Label(product_frame, text="Ausgabeverz.:").grid(
            row=3, column=0, sticky="w", pady=2
        )
        dir_frame = ttk.Frame(product_frame)
        dir_frame.grid(row=3, column=1, columnspan=2, sticky="ew", pady=2)
        dir_frame.columnconfigure(0, weight=1)

        self._output_dir_var = tk.StringVar()
        self._output_dir_var.trace_add("write", lambda *_: self._mark_dirty())
        ttk.Entry(dir_frame, textvariable=self._output_dir_var).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ttk.Button(dir_frame, text="Wählen...", command=self._choose_output_dir).grid(
            row=0, column=1
        )

        proc_frame = ttk.LabelFrame(self, text="Prozesse", padding=10)
        proc_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        proc_frame.columnconfigure(1, weight=1)
        proc_frame.rowconfigure(0, weight=1)

        left = ttk.Frame(proc_frame)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        self._proc_listbox = tk.Listbox(
            left,
            font=FONTS["body"],
            bg=COLORS["background"],
            fg=COLORS["text_primary"],
            selectbackground=COLORS["accent"],
            selectforeground=COLORS["text_on_primary"],
            relief="solid",
            borderwidth=1,
            width=25,
            exportselection=False,
        )
        self._proc_listbox.grid(row=0, column=0, sticky="nsew")
        self._proc_listbox.bind("<<ListboxSelect>>", self._on_process_selected)

        proc_btn_frame = ttk.Frame(left)
        proc_btn_frame.grid(row=1, column=0, pady=(5, 0))
        ttk.Button(proc_btn_frame, text="+", width=3, command=self._add_process).pack(
            side="left", padx=2
        )
        ttk.Button(
            proc_btn_frame, text="-", width=3, command=self._remove_process
        ).pack(side="left", padx=2)
        ttk.Button(
            proc_btn_frame, text="\u2191", width=3, command=self._move_process_up
        ).pack(side="left", padx=2)
        ttk.Button(
            proc_btn_frame, text="\u2193", width=3, command=self._move_process_down
        ).pack(side="left", padx=2)

        self._right_panel = ttk.Frame(proc_frame)
        self._right_panel.grid(row=0, column=1, sticky="nsew")
        self._right_panel.columnconfigure(0, weight=1)
        self._right_panel.rowconfigure(1, weight=1)

        detail_frame = ttk.Frame(self._right_panel)
        detail_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        detail_frame.columnconfigure(1, weight=1)

        ttk.Label(detail_frame, text="Template-ID:").grid(
            row=0, column=0, sticky="w", pady=2
        )
        self._template_id_var = tk.StringVar()
        self._template_id_entry = ttk.Entry(
            detail_frame, textvariable=self._template_id_var, width=30
        )
        self._template_id_entry.grid(row=0, column=1, sticky="w", pady=2)
        self._template_id_entry.bind("<FocusOut>", lambda e: self._sync_process_details())

        ttk.Label(detail_frame, text="Anzeigename:").grid(
            row=1, column=0, sticky="w", pady=2
        )
        self._proc_name_var = tk.StringVar()
        self._proc_name_entry = ttk.Entry(
            detail_frame, textvariable=self._proc_name_var, width=40
        )
        self._proc_name_entry.grid(row=1, column=1, sticky="ew", pady=2)
        self._proc_name_entry.bind("<FocusOut>", lambda e: self._sync_process_details())

        ttk.Label(detail_frame, text="Zeilengruppe:").grid(
            row=2, column=0, sticky="w", pady=2
        )
        self._row_group_var = tk.StringVar()
        self._row_group_entry = ttk.Entry(
            detail_frame, textvariable=self._row_group_var, width=10
        )
        self._row_group_entry.grid(row=2, column=1, sticky="w", pady=2)
        self._row_group_entry.bind("<FocusOut>", lambda e: self._sync_process_details())

        fields_frame = ttk.LabelFrame(self._right_panel, text="Felder", padding=5)
        fields_frame.grid(row=1, column=0, sticky="nsew")
        fields_frame.columnconfigure(0, weight=1)
        fields_frame.rowconfigure(0, weight=1)

        tree_container = ttk.Frame(fields_frame)
        tree_container.grid(row=0, column=0, sticky="nsew")
        tree_container.columnconfigure(0, weight=1)
        tree_container.rowconfigure(0, weight=1)

        columns = ("id", "name", "typ", "rolle", "persistent", "optional")
        self._fields_tree = ttk.Treeview(
            tree_container, columns=columns, show="headings", height=8
        )
        self._fields_tree.heading("id", text="ID")
        self._fields_tree.heading("name", text="Anzeigename")
        self._fields_tree.heading("typ", text="Typ")
        self._fields_tree.heading("rolle", text="Rolle")
        self._fields_tree.heading("persistent", text="Persistent")
        self._fields_tree.heading("optional", text="Optional")

        self._fields_tree.column("id", width=100, minwidth=60)
        self._fields_tree.column("name", width=150, minwidth=80)
        self._fields_tree.column("typ", width=80, minwidth=50)
        self._fields_tree.column("rolle", width=100, minwidth=60)
        self._fields_tree.column("persistent", width=70, minwidth=50)
        self._fields_tree.column("optional", width=70, minwidth=50)

        self._fields_tree.grid(row=0, column=0, sticky="nsew")
        self._fields_tree.bind("<Double-1>", lambda e: self._edit_field())

        vsb = ttk.Scrollbar(
            tree_container, orient="vertical", command=self._fields_tree.yview
        )
        vsb.grid(row=0, column=1, sticky="ns")
        self._fields_tree.configure(yscrollcommand=vsb.set)

        field_btn_frame = ttk.Frame(fields_frame)
        field_btn_frame.grid(row=1, column=0, pady=(5, 0))

        ttk.Button(
            field_btn_frame, text="Hinzufügen", command=self._add_field
        ).pack(side="left", padx=2)
        ttk.Button(
            field_btn_frame, text="Bearbeiten", command=self._edit_field
        ).pack(side="left", padx=2)
        ttk.Button(
            field_btn_frame, text="Entfernen", command=self._remove_field
        ).pack(side="left", padx=2)
        ttk.Button(
            field_btn_frame, text="\u2191", width=3, command=self._move_field_up
        ).pack(side="left", padx=2)
        ttk.Button(
            field_btn_frame, text="\u2193", width=3, command=self._move_field_down
        ).pack(side="left", padx=2)

        self._no_proc_label = ttk.Label(
            self._right_panel,
            text="Prozess in der Liste links auswählen oder neuen Prozess hinzufügen.",
            foreground=COLORS["text_secondary"],
        )

        bottom_frame = ttk.Frame(self)
        bottom_frame.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")
        bottom_frame.columnconfigure(0, weight=1)

        self._status_var = tk.StringVar(value="Bereit.")
        ttk.Label(bottom_frame, textvariable=self._status_var).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(
            bottom_frame,
            text="Speichern",
            style="Accent.TButton",
            command=self._on_save,
        ).grid(row=0, column=1, padx=(10, 0))

        self._show_right_panel(False)

    def _load_product_list(self) -> None:
        if not PRODUCTS_DIR.exists():
            self._product_combo["values"] = []
            return
        names = sorted(p.stem for p in PRODUCTS_DIR.glob("*.json"))
        self._product_combo["values"] = names

    def _on_load(self) -> None:
        name = self._product_combo.get()
        if not name:
            return
        if self._dirty and not self._confirm_discard():
            return

        path = PRODUCTS_DIR / f"{name}.json"
        if not path.exists():
            self._status_var.set(f"Datei nicht gefunden: {path}")
            return

        product = load_product_config(path)
        self._populate_ui_from_product(product)
        self._dirty = False
        self._status_var.set(f"Geladen: {name}")

    def _on_new(self) -> None:
        if self._dirty and not self._confirm_discard():
            return
        product = ProductConfig(
            product_id="",
            display_name="",
            processes=[],
        )
        self._populate_ui_from_product(product)
        self._dirty = False
        self._status_var.set("Neues Produkt erstellt.")

    def _on_copy(self) -> None:
        name = self._product_combo.get()
        if not name:
            return
        if self._dirty and not self._confirm_discard():
            return

        path = PRODUCTS_DIR / f"{name}.json"
        if not path.exists():
            return

        product = load_product_config(path)
        product.product_id = ""
        self._populate_ui_from_product(product)
        self._dirty = True
        self._status_var.set(f"Kopie von {name} erstellt. Neue Produkt-ID vergeben.")

    def _populate_ui_from_product(self, product: ProductConfig) -> None:
        self._product = product
        self._selected_process_idx = None

        self._product_id_var.set(product.product_id)
        self._product_name_var.set(product.display_name)
        self._output_dir_var.set(product.output_dir or "")

        self._proc_listbox.delete(0, tk.END)
        for proc in product.processes:
            self._proc_listbox.insert(tk.END, proc.display_name or proc.template_id)

        self._show_right_panel(False)

    def _build_product_from_ui(self) -> ProductConfig:
        self._sync_process_details()

        output_dir = self._output_dir_var.get().strip() or None
        return ProductConfig(
            product_id=self._product_id_var.get().strip(),
            display_name=self._product_name_var.get().strip(),
            processes=list(self._product.processes) if self._product else [],
            output_dir=output_dir,
        )

    def _on_process_selected(self, event=None) -> None:
        sel = self._proc_listbox.curselection()
        if not sel:
            return
        self._sync_process_details()

        idx = sel[0]
        self._selected_process_idx = idx
        proc = self._product.processes[idx]

        self._template_id_var.set(proc.template_id)
        self._proc_name_var.set(proc.display_name)
        self._row_group_var.set(str(proc.row_group_size) if proc.row_group_size else "")

        self._show_right_panel(True)
        self._refresh_fields_tree()

    def _sync_process_details(self) -> None:
        if self._selected_process_idx is None or not self._product:
            return
        if self._selected_process_idx >= len(self._product.processes):
            return

        proc = self._product.processes[self._selected_process_idx]
        old_template = proc.template_id
        old_name = proc.display_name
        old_rg = proc.row_group_size

        proc.template_id = self._template_id_var.get().strip()
        proc.display_name = self._proc_name_var.get().strip()

        rg_str = self._row_group_var.get().strip()
        if rg_str:
            try:
                proc.row_group_size = int(rg_str)
            except ValueError:
                proc.row_group_size = None
        else:
            proc.row_group_size = None

        display = proc.display_name or proc.template_id
        self._proc_listbox.delete(self._selected_process_idx)
        self._proc_listbox.insert(self._selected_process_idx, display)
        self._proc_listbox.selection_set(self._selected_process_idx)

        if (
            proc.template_id != old_template
            or proc.display_name != old_name
            or proc.row_group_size != old_rg
        ):
            self._mark_dirty()

    def _add_process(self) -> None:
        if not self._product:
            return
        self._sync_process_details()

        proc = ProcessConfig(
            template_id="",
            display_name="Neuer Prozess",
            fields=[],
        )
        self._product.processes.append(proc)
        self._proc_listbox.insert(tk.END, proc.display_name)

        idx = len(self._product.processes) - 1
        self._proc_listbox.selection_clear(0, tk.END)
        self._proc_listbox.selection_set(idx)
        self._on_process_selected()
        self._mark_dirty()

    def _remove_process(self) -> None:
        if not self._product or self._selected_process_idx is None:
            return
        if not messagebox.askyesno(
            "Prozess entfernen",
            "Soll der ausgewählte Prozess wirklich entfernt werden?",
        ):
            return

        del self._product.processes[self._selected_process_idx]
        self._proc_listbox.delete(self._selected_process_idx)
        self._selected_process_idx = None
        self._show_right_panel(False)
        self._mark_dirty()

    def _move_process_up(self) -> None:
        self._move_process(-1)

    def _move_process_down(self) -> None:
        self._move_process(1)

    def _move_process(self, direction: int) -> None:
        if not self._product or self._selected_process_idx is None:
            return
        self._sync_process_details()

        idx = self._selected_process_idx
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self._product.processes):
            return

        procs = self._product.processes
        procs[idx], procs[new_idx] = procs[new_idx], procs[idx]

        self._proc_listbox.delete(0, tk.END)
        for p in procs:
            self._proc_listbox.insert(tk.END, p.display_name or p.template_id)

        self._selected_process_idx = new_idx
        self._proc_listbox.selection_set(new_idx)
        self._mark_dirty()

    def _refresh_fields_tree(self) -> None:
        self._fields_tree.delete(*self._fields_tree.get_children())
        if self._selected_process_idx is None or not self._product:
            return

        proc = self._product.processes[self._selected_process_idx]
        for field in proc.fields:
            self._fields_tree.insert(
                "",
                "end",
                values=(
                    field.id,
                    field.display_name,
                    field.type,
                    field.role,
                    "Ja" if field.persistent else "Nein",
                    "Ja" if field.optional else "Nein",
                ),
            )

    def _get_selected_field_index(self) -> int | None:
        sel = self._fields_tree.selection()
        if not sel:
            return None
        return self._fields_tree.index(sel[0])

    def _add_field(self) -> None:
        if self._selected_process_idx is None or not self._product:
            return

        def on_save(field: FieldDef) -> None:
            self._product.processes[self._selected_process_idx].fields.append(field)
            self._refresh_fields_tree()
            self._mark_dirty()

        FieldEditorDialog(self.winfo_toplevel(), None, on_save)

    def _edit_field(self) -> None:
        if self._selected_process_idx is None or not self._product:
            return
        fi = self._get_selected_field_index()
        if fi is None:
            return

        proc = self._product.processes[self._selected_process_idx]
        field = proc.fields[fi]

        def on_save(updated: FieldDef) -> None:
            proc.fields[fi] = updated
            self._refresh_fields_tree()
            self._mark_dirty()

        FieldEditorDialog(self.winfo_toplevel(), field, on_save)

    def _remove_field(self) -> None:
        if self._selected_process_idx is None or not self._product:
            return
        fi = self._get_selected_field_index()
        if fi is None:
            return
        if not messagebox.askyesno(
            "Feld entfernen",
            "Soll das ausgewählte Feld wirklich entfernt werden?",
        ):
            return

        del self._product.processes[self._selected_process_idx].fields[fi]
        self._refresh_fields_tree()
        self._mark_dirty()

    def _move_field_up(self) -> None:
        self._move_field(-1)

    def _move_field_down(self) -> None:
        self._move_field(1)

    def _move_field(self, direction: int) -> None:
        if self._selected_process_idx is None or not self._product:
            return
        fi = self._get_selected_field_index()
        if fi is None:
            return

        fields = self._product.processes[self._selected_process_idx].fields
        new_fi = fi + direction
        if new_fi < 0 or new_fi >= len(fields):
            return

        fields[fi], fields[new_fi] = fields[new_fi], fields[fi]
        self._refresh_fields_tree()
        self._mark_dirty()

        children = self._fields_tree.get_children()
        if 0 <= new_fi < len(children):
            self._fields_tree.selection_set(children[new_fi])

    def _on_save(self) -> None:
        if not self._product:
            return
        self._sync_process_details()

        product = self._build_product_from_ui()

        errors = validate_product_config(product)
        if errors:
            messagebox.showerror(
                "Validierungsfehler",
                "\n".join(errors),
            )
            return

        target = PRODUCTS_DIR / f"{product.product_id}.json"
        if target.exists():
            is_same = (
                self._product
                and self._product.product_id == product.product_id
            )
            if not is_same and not messagebox.askyesno(
                "Datei überschreiben",
                f"Die Datei {target.name} existiert bereits.\nÜberschreiben?",
            ):
                return

        path = save_product_config(product, PRODUCTS_DIR)
        self._product = product
        self._dirty = False

        self.app_state.app_config = load_app_config(APP_CONFIG_PATH, PRODUCTS_DIR)

        self._load_product_list()
        self._status_var.set(f"Gespeichert: {path}")

    def _show_right_panel(self, show: bool) -> None:
        if show:
            self._no_proc_label.grid_remove()
            for child in self._right_panel.winfo_children():
                if child != self._no_proc_label:
                    child.grid()
        else:
            for child in self._right_panel.winfo_children():
                if child != self._no_proc_label:
                    child.grid_remove()
            self._no_proc_label.grid(row=0, column=0, padx=20, pady=40)
            self._fields_tree.delete(*self._fields_tree.get_children())
            self._template_id_var.set("")
            self._proc_name_var.set("")
            self._row_group_var.set("")

    def _choose_output_dir(self) -> None:
        path = filedialog.askdirectory(title="Ausgabeverzeichnis wählen")
        if path:
            self._output_dir_var.set(path)

    def _mark_dirty(self) -> None:
        self._dirty = True

    def _confirm_discard(self) -> bool:
        return messagebox.askyesno(
            "Ungespeicherte Änderungen",
            "Es gibt ungespeicherte Änderungen. Verwerfen?",
        )


class FieldEditorDialog(tk.Toplevel):
    """Modaler Dialog zum Bearbeiten eines einzelnen Feldes."""

    def __init__(
        self,
        parent,
        field: FieldDef | None,
        on_save: callable,
    ):
        super().__init__(parent)
        self._on_save = on_save
        self._editing = field is not None

        self.title("Feld bearbeiten" if self._editing else "Neues Feld")
        self.geometry("450x520")
        self.resizable(False, True)
        self.transient(parent)
        self.grab_set()

        self._build_ui(field)
        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _build_ui(self, field: FieldDef | None) -> None:
        main = ttk.Frame(self, padding=15)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)

        row = 0

        ttk.Label(main, text="ID:").grid(row=row, column=0, sticky="w", pady=3)
        self._id_var = tk.StringVar(value=field.id if field else "")
        ttk.Entry(main, textvariable=self._id_var, width=30).grid(
            row=row, column=1, sticky="ew", pady=3
        )
        row += 1

        ttk.Label(main, text="Anzeigename:").grid(
            row=row, column=0, sticky="w", pady=3
        )
        self._name_var = tk.StringVar(value=field.display_name if field else "")
        ttk.Entry(main, textvariable=self._name_var, width=30).grid(
            row=row, column=1, sticky="ew", pady=3
        )
        row += 1

        ttk.Label(main, text="Typ:").grid(row=row, column=0, sticky="w", pady=3)
        self._type_var = tk.StringVar(value=field.type if field else "text")
        type_combo = ttk.Combobox(
            main,
            textvariable=self._type_var,
            values=["text", "number", "choice"],
            state="readonly",
            width=15,
        )
        type_combo.grid(row=row, column=1, sticky="w", pady=3)
        type_combo.bind("<<ComboboxSelected>>", lambda e: self._on_type_changed())
        row += 1

        ttk.Label(main, text="Rolle:").grid(row=row, column=0, sticky="w", pady=3)
        self._role_var = tk.StringVar(value=field.role if field else "measurement")
        ttk.Combobox(
            main,
            textvariable=self._role_var,
            values=["context", "measurement", "auto"],
            state="readonly",
            width=15,
        ).grid(row=row, column=1, sticky="w", pady=3)
        row += 1

        self._persistent_var = tk.BooleanVar(
            value=field.persistent if field else False
        )
        ttk.Checkbutton(
            main, text="Persistent", variable=self._persistent_var
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=3)
        row += 1

        self._optional_var = tk.BooleanVar(value=field.optional if field else False)
        ttk.Checkbutton(main, text="Optional", variable=self._optional_var).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=3
        )
        row += 1

        self._spec_frame = ttk.LabelFrame(main, text="Spezifikation", padding=8)
        self._spec_frame.grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(8, 3)
        )
        self._spec_frame.columnconfigure(1, weight=1)
        self._spec_row = row
        row += 1

        ttk.Label(self._spec_frame, text="Zielwert:").grid(
            row=0, column=0, sticky="w", pady=2
        )
        self._target_var = tk.StringVar(
            value=str(field.spec_target) if field and field.spec_target is not None else ""
        )
        ttk.Entry(self._spec_frame, textvariable=self._target_var, width=15).grid(
            row=0, column=1, sticky="w", pady=2
        )

        ttk.Label(self._spec_frame, text="Minimum:").grid(
            row=1, column=0, sticky="w", pady=2
        )
        self._min_var = tk.StringVar(
            value=str(field.spec_min) if field and field.spec_min is not None else ""
        )
        ttk.Entry(self._spec_frame, textvariable=self._min_var, width=15).grid(
            row=1, column=1, sticky="w", pady=2
        )

        ttk.Label(self._spec_frame, text="Maximum:").grid(
            row=2, column=0, sticky="w", pady=2
        )
        self._max_var = tk.StringVar(
            value=str(field.spec_max) if field and field.spec_max is not None else ""
        )
        ttk.Entry(self._spec_frame, textvariable=self._max_var, width=15).grid(
            row=2, column=1, sticky="w", pady=2
        )

        self._options_frame = ttk.LabelFrame(main, text="Optionen", padding=8)
        self._options_frame.grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(8, 3)
        )
        self._options_frame.columnconfigure(0, weight=1)
        self._options_row = row
        row += 1

        self._options_listbox = tk.Listbox(
            self._options_frame,
            height=4,
            font=FONTS["body"],
            bg=COLORS["background"],
            fg=COLORS["text_primary"],
            relief="solid",
            borderwidth=1,
        )
        self._options_listbox.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        if field and field.options:
            for opt in field.options:
                self._options_listbox.insert(tk.END, opt)

        opt_input_frame = ttk.Frame(self._options_frame)
        opt_input_frame.grid(row=1, column=0, sticky="ew")
        opt_input_frame.columnconfigure(0, weight=1)

        self._new_option_var = tk.StringVar()
        opt_entry = ttk.Entry(
            opt_input_frame, textvariable=self._new_option_var, width=20
        )
        opt_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        opt_entry.bind("<Return>", lambda e: self._add_option())

        ttk.Button(
            opt_input_frame, text="Hinzufügen", command=self._add_option
        ).grid(row=0, column=1, padx=2)
        ttk.Button(
            opt_input_frame, text="Entfernen", command=self._remove_option
        ).grid(row=0, column=2, padx=2)

        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=(15, 0), sticky="e")

        ttk.Button(btn_frame, text="Abbrechen", command=self._cancel).pack(
            side="left", padx=(0, 10)
        )
        ttk.Button(
            btn_frame, text="Speichern", style="Accent.TButton", command=self._save
        ).pack(side="left")

        self._on_type_changed()

    def _on_type_changed(self) -> None:
        typ = self._type_var.get()
        if typ == "number":
            self._spec_frame.grid()
        else:
            self._spec_frame.grid_remove()

        if typ == "choice":
            self._options_frame.grid()
        else:
            self._options_frame.grid_remove()

    def _add_option(self) -> None:
        val = self._new_option_var.get().strip()
        if val:
            self._options_listbox.insert(tk.END, val)
            self._new_option_var.set("")

    def _remove_option(self) -> None:
        sel = self._options_listbox.curselection()
        if sel:
            self._options_listbox.delete(sel[0])

    def _save(self) -> None:
        fid = self._id_var.get().strip()
        fname = self._name_var.get().strip()

        if not fid:
            messagebox.showwarning("Fehler", "ID darf nicht leer sein.", parent=self)
            return
        if not fname:
            messagebox.showwarning(
                "Fehler", "Anzeigename darf nicht leer sein.", parent=self
            )
            return

        ftype = self._type_var.get()
        frole = self._role_var.get()
        persistent = self._persistent_var.get()
        optional = self._optional_var.get()

        spec_target = self._parse_float(self._target_var.get())
        spec_min = self._parse_float(self._min_var.get())
        spec_max = self._parse_float(self._max_var.get())

        options = None
        if ftype == "choice":
            options = list(self._options_listbox.get(0, tk.END))
            if not options:
                messagebox.showwarning(
                    "Fehler",
                    "Choice-Feld braucht mindestens eine Option.",
                    parent=self,
                )
                return

        field = FieldDef(
            id=fid,
            display_name=fname,
            type=ftype,
            role=frole,
            persistent=persistent,
            spec_target=spec_target if ftype == "number" else None,
            spec_min=spec_min if ftype == "number" else None,
            spec_max=spec_max if ftype == "number" else None,
            options=options,
            optional=optional,
        )

        self._on_save(field)
        self.destroy()

    def _cancel(self) -> None:
        self.destroy()

    @staticmethod
    def _parse_float(s: str) -> float | None:
        s = s.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
