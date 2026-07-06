"""Admin-Editor für Produktkonfigurationen (template-basiert).

Der Editor arbeitet um das dünne Template-Modell herum: pro Prozess wird ein
Operation-Template gewählt, die Felder kommen als Checkliste aus dem Template
(kein Freitext für IDs), Spec-Werte werden inline gesetzt, seltenere Overrides
über einen Dialog. Eigene (produktunike) Felder sind als extra_fields möglich.
Legacy-Voll-Configs werden hart geblockt.

Die nicht-triviale Logik liegt Tk-frei in src/config/config_editing.py; dieser
View ist nur die Hülle und reicht beim Speichern immer die volle fields-Liste an
config_writer, der gegen das Template zurückrechnet.
"""

from __future__ import annotations

import json
import logging
import tkinter as tk
from dataclasses import replace
from datetime import date
from tkinter import ttk, filedialog, messagebox, simpledialog

from src.audit.events import Event
from src.config.config_editing import (
    apply_template_change,
    is_legacy_product,
    removed_template_ids,
    seed_process_from_template,
    validate_editor_product,
)
from src.config.config_writer import save_product_config, validate_product_config
from src.config.process_config import (
    FieldDef,
    ProcessConfig,
    ProcessTemplate,
    ProductConfig,
    load_app_config,
    load_process_templates,
    load_product_config,
)
from src.config.settings import APP_CONFIG_PATH, PRODUCTS_DIR, PROCESS_TEMPLATES_DIR
from src.ui.dialog_util import make_scrollable, place_dialog
from src.ui.theme import COLORS, FONTS
from src.ui.tooltip import attach_info_icon

logger = logging.getLogger(__name__)

# Spaltenraster der Feldliste in PIXELN — identisch in Kopfzeile und jeder
# Datenzeile gesetzt (getrennte grid-Container!), damit die Spalten unabhängig
# von den Fonts der Zellinhalte bündig stehen (Zeichen-width misst in der
# jeweiligen Widget-Font und fluchtet daher nicht containerübergreifend).
# Spalte 5 (Anzeigename) stretcht; Nummern = grid-Spalten in _render_rows.
_COL_PX: dict[int, int] = {
    0: 24,    # Drag-Griff ⠿
    1: 28,    # Aktiv-Checkbox
    2: 230,   # Feld-ID (mono-Chip; Puffer für lange IDs bei Font-Zoom +3)
    3: 80,    # Typ
    4: 120,   # Rolle ("measurement" auch bei Font-Zoom +3)
    6: 64,    # Spec Min
    7: 64,    # Spec Soll
    8: 64,    # Spec Max
    9: 150,   # Aktionen (Bearbeiten + ✕ bei Extra-Feldern)
}


def _configure_list_columns(container: tk.Widget) -> None:
    """Setzt das gemeinsame Pixel-Spaltenraster der Feldliste (Kopf + Zeilen)."""
    for col, px in _COL_PX.items():
        container.columnconfigure(col, minsize=px)
    container.columnconfigure(5, weight=1)


# --------------------------------------------------------------------------- #
# Modul-Helfer
# --------------------------------------------------------------------------- #
def _copy_field(f: FieldDef) -> FieldDef:
    return replace(f, options=list(f.options) if f.options is not None else None)


def _checkbox_with_info(master, r: int, label: str, var, info: str) -> int:
    """Checkbox mit kurzem Label + ⓘ-Tooltip in einer Dialog-Zeile. Gibt r+1 zurück."""
    cell = ttk.Frame(master)
    cell.grid(row=r, column=0, columnspan=2, sticky="w", pady=2)
    ttk.Checkbutton(cell, text=label, variable=var).pack(side="left")
    attach_info_icon(cell, info).pack(side="left", padx=(4, 0))
    return r + 1


def _fmt_num(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _parse_float(s: str):
    """(<ok>, <wert oder None>). Leer = (True, None); ungültig = (False, None)."""
    s = (s or "").strip().replace(",", ".")
    if not s:
        return True, None
    try:
        return True, float(s)
    except ValueError:
        return False, None


def choose_template(parent, templates: dict[str, ProcessTemplate]) -> str | None:
    """Modaler Mini-Dialog: Operation-Template auswählen. Liefert Name oder None."""
    dlg = tk.Toplevel(parent)
    dlg.title("Operation wählen")
    dlg.transient(parent)
    dlg.grab_set()
    result: dict[str, str | None] = {"name": None}

    frame = ttk.Frame(dlg, padding=15)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Operation-Template:").grid(row=0, column=0, sticky="w", pady=(0, 6))
    var = tk.StringVar()
    combo = ttk.Combobox(
        frame, textvariable=var, state="readonly",
        values=sorted(templates), width=28,
    )
    combo.grid(row=1, column=0, sticky="ew")
    if templates:
        combo.current(0)

    def ok():
        result["name"] = var.get() or None
        dlg.destroy()

    bf = ttk.Frame(frame)
    bf.grid(row=2, column=0, pady=(12, 0))
    ttk.Button(bf, text="Abbrechen", command=dlg.destroy).pack(side="left", padx=6)
    ttk.Button(bf, text="OK", style="Accent.TButton", command=ok).pack(side="left", padx=6)

    place_dialog(dlg, parent, min_size=(320, 160), resizable=(False, False))
    dlg.wait_window()
    return result["name"]


# --------------------------------------------------------------------------- #
# Feld-Checkliste (eine Zeile)
# --------------------------------------------------------------------------- #
class _FieldRow:
    """Wahrheit einer Checklisten-Zeile; die Widgets werden je Render neu gebaut
    und über _harvest() zurückgelesen."""

    __slots__ = ("field", "is_extra", "active")

    def __init__(self, field: FieldDef, is_extra: bool, active: bool):
        self.field = field
        self.is_extra = is_extra
        self.active = active


class ProcessEditorPanel(ttk.Frame):
    """Bearbeitet genau einen Prozess template-basiert. Wird vom Haupt-Editor
    UND vom Wizard genutzt, damit Checklisten-/Override-Logik nur einmal
    existiert."""

    def __init__(self, parent, templates, dirty_callback=None, stage_hint=1):
        super().__init__(parent)
        self._templates: dict[str, ProcessTemplate] = templates
        self._dirty_cb = dirty_callback or (lambda: None)
        self._stage_hint = stage_hint
        self._process: ProcessConfig | None = None
        self._rows: list[_FieldRow] = []
        self._render_refs: list[dict] = []
        self._row_frames: list[tk.Widget] = []
        self._drag_from: int | None = None
        self._template_id_manual = False
        self._inline_errors: list[str] = []
        self._build_ui()

    # -- öffentliche API --------------------------------------------------- #
    def set_templates(self, templates) -> None:
        self._templates = templates
        self._template_combo["values"] = sorted(templates)

    def has_process(self) -> bool:
        return self._process is not None

    def load(self, process: ProcessConfig, stage_hint: int | None = None) -> None:
        self._process = process
        if stage_hint is not None:
            self._stage_hint = stage_hint
        self._template_id_manual = bool(process.template_id)
        self._template_var.set(process.template or "")
        self._template_id_var.set(process.template_id)
        self._name_var.set(process.display_name)
        self._rg_var.set(str(process.row_group_size) if process.row_group_size else "")
        self._rebuild_rows()

    def flush(self) -> None:
        if self._process is None:
            return
        self._harvest()
        p = self._process
        p.template = self._template_var.get() or None
        p.template_id = self._template_id_var.get().strip()
        p.display_name = self._name_var.get().strip()
        rg = self._rg_var.get().strip()
        if rg:
            try:
                p.row_group_size = int(rg)
            except ValueError:
                p.row_group_size = None
        else:
            p.row_group_size = None
        tpl = self._current_template()
        if tpl is not None:
            p.template_revision = tpl.template_revision
        p.fields = [r.field for r in self._rows if r.active]

    def inline_errors(self) -> list[str]:
        """Nicht-numerische Inline-Spec-Eingaben (für die Save-Sperre)."""
        self._harvest()
        return list(self._inline_errors)

    # -- UI-Aufbau --------------------------------------------------------- #
    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        head = ttk.Frame(self)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        head.columnconfigure(1, weight=1)

        ttk.Label(head, text="Operation (Template):").grid(row=0, column=0, sticky="w", pady=2)
        self._template_var = tk.StringVar()
        self._template_combo = ttk.Combobox(
            head, textvariable=self._template_var, state="readonly",
            values=sorted(self._templates), width=28,
        )
        self._template_combo.grid(row=0, column=1, sticky="w", pady=2)
        self._template_combo.bind("<<ComboboxSelected>>", lambda e: self._on_template_changed())

        ttk.Label(head, text="Template-ID:").grid(row=1, column=0, sticky="w", pady=2)
        tid_cell = ttk.Frame(head)
        tid_cell.grid(row=1, column=1, sticky="w", pady=2)
        self._template_id_var = tk.StringVar()
        tid_entry = ttk.Entry(tid_cell, textvariable=self._template_id_var, width=30)
        tid_entry.pack(side="left")
        tid_entry.bind("<KeyRelease>", lambda e: self._on_template_id_typed())
        attach_info_icon(
            tid_cell,
            "Excel-Dateiname + Resume-Schlüssel — nach den ersten Excel-Dateien "
            "NICHT mehr ändern.",
        ).pack(side="left", padx=(4, 0))

        ttk.Label(head, text="Anzeigename:").grid(row=2, column=0, sticky="w", pady=2)
        self._name_var = tk.StringVar()
        name_entry = ttk.Entry(head, textvariable=self._name_var, width=40)
        name_entry.grid(row=2, column=1, sticky="ew", pady=2)
        name_entry.bind("<KeyRelease>", lambda e: self._dirty_cb())

        ttk.Label(head, text="Standard-/Max-Anzahl Nutzen:").grid(row=3, column=0, sticky="w", pady=2)
        rg_cell = ttk.Frame(head)
        rg_cell.grid(row=3, column=1, sticky="w", pady=2)
        self._rg_var = tk.StringVar()
        rg_entry = ttk.Entry(rg_cell, textvariable=self._rg_var, width=8)
        rg_entry.pack(side="left")
        rg_entry.bind("<KeyRelease>", lambda e: self._dirty_cb())
        attach_info_icon(
            rg_cell,
            "Bediener wählt beim Prozessstart 1..Max. Nötig für clone-Felder "
            "(je Nutzen/Bahn eine Spalte).",
        ).pack(side="left", padx=(4, 0))

        toolbar = ttk.Frame(self)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(4, 2))
        ttk.Button(
            toolbar, text="+ Eigenes Feld", style="Small.TButton",
            command=self._add_extra_field,
        ).pack(side="right")
        attach_info_icon(
            toolbar,
            "Anhaken = Feld aktiv. Reihenfolge (per Maus am Griff ⠿ ziehen) = "
            "Reihenfolge der Excel-Spalten.",
        ).pack(side="left", padx=(0, 4))

        list_wrap = ttk.Frame(self)
        list_wrap.grid(row=2, column=0, sticky="nsew")
        list_wrap.columnconfigure(0, weight=1)
        list_wrap.rowconfigure(1, weight=1)

        # Einmalige Spaltenüberschrift (scrollt nicht mit) — spiegelt das
        # grid-Layout von _render_rows mit denselben Breitenkonstanten.
        hdr = ttk.Frame(list_wrap)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        _configure_list_columns(hdr)
        ttk.Label(hdr, text="").grid(row=0, column=0, padx=(0, 4))
        ttk.Label(hdr, text="✓", style="ColHeader.TLabel").grid(row=0, column=1)
        ttk.Label(hdr, text="ID", style="ColHeader.TLabel").grid(
            row=0, column=2, sticky="w", padx=(0, 6)
        )
        ttk.Label(hdr, text="Typ", style="ColHeader.TLabel").grid(
            row=0, column=3, sticky="w"
        )
        ttk.Label(hdr, text="Rolle", style="ColHeader.TLabel").grid(
            row=0, column=4, sticky="w"
        )
        ttk.Label(hdr, text="Anzeigename", style="ColHeader.TLabel").grid(
            row=0, column=5, sticky="w"
        )
        for col, txt in ((6, "Min"), (7, "Soll"), (8, "Max")):
            ttk.Label(hdr, text=txt, style="ColHeader.TLabel").grid(
                row=0, column=col, sticky="w", padx=1
            )
        # Leerer Platzhalter belegt die Aktions-Spalte, damit ihre minsize greift.
        ttk.Label(hdr, text="").grid(row=0, column=9, sticky="ew", padx=(6, 1))

        self._canvas = tk.Canvas(list_wrap, bg=COLORS["background"], highlightthickness=0)
        self._canvas.grid(row=1, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(list_wrap, orient="vertical", command=self._canvas.yview)
        vsb.grid(row=1, column=1, sticky="ns")
        self._canvas.configure(yscrollcommand=vsb.set)
        self._rows_frame = ttk.Frame(self._canvas)
        self._rows_frame.columnconfigure(0, weight=1)
        self._rows_window = self._canvas.create_window(
            (0, 0), window=self._rows_frame, anchor="nw"
        )
        self._rows_frame.bind(
            "<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")),
        )
        self._canvas.bind(
            "<Configure>",
            lambda e: self._canvas.itemconfigure(self._rows_window, width=e.width),
        )
        self._canvas.bind("<MouseWheel>", self._on_wheel)
        self._rows_frame.bind("<MouseWheel>", self._on_wheel)

    def _on_wheel(self, event) -> None:
        self._canvas.yview_scroll(int(-event.delta / 120), "units")

    # -- Zeilen ------------------------------------------------------------ #
    def _current_template(self) -> ProcessTemplate | None:
        if self._process and self._process.template:
            return self._templates.get(self._process.template)
        return None

    def _template_ids(self) -> set[str]:
        tpl = self._current_template()
        return set(tpl.field_map()) if tpl else set()

    def _rebuild_rows(self) -> None:
        self._rows = []
        proc = self._process
        if proc is not None:
            tpl = self._current_template()
            tpl_ids = set(tpl.field_map()) if tpl else set()
            active_ids = []
            for f in proc.fields:
                self._rows.append(
                    _FieldRow(field=f, is_extra=(f.id not in tpl_ids), active=True)
                )
                active_ids.append(f.id)
            if tpl is not None:
                for f in tpl.fields:
                    if f.id not in active_ids:
                        self._rows.append(
                            _FieldRow(field=_copy_field(f), is_extra=False, active=False)
                        )
        self._render_rows()

    def _render_rows(self) -> None:
        for w in self._rows_frame.winfo_children():
            w.destroy()
        self._render_refs = []
        self._row_frames = []

        for i, row in enumerate(self._rows):
            f = row.field
            rf = ttk.Frame(self._rows_frame)
            rf.grid(row=2 * i, column=0, sticky="ew", pady=2)
            _configure_list_columns(rf)
            rf.bind("<MouseWheel>", self._on_wheel)
            self._row_frames.append(rf)

            # Drag-Griff: per Maus ziehen, um die Feldreihenfolge zu ändern.
            grip = ttk.Label(rf, text="⠿", foreground=COLORS["text_secondary"], cursor="fleur")
            grip.grid(row=0, column=0, sticky="w", padx=(0, 4))
            grip.bind("<ButtonPress-1>", lambda e, idx=i: self._drag_start(idx))
            grip.bind("<B1-Motion>", self._drag_motion)
            grip.bind("<ButtonRelease-1>", self._drag_drop)

            active_var = tk.BooleanVar(value=row.active)
            ttk.Checkbutton(
                rf, variable=active_var,
                command=lambda r=row, v=active_var: self._on_toggle(r, v),
            ).grid(row=0, column=1, sticky="w")

            # Feld-ID als Monospace-Chip — füllt die Spalte (einheitliche Breite).
            id_style = "FieldId.TLabel" if row.active else "FieldIdMuted.TLabel"
            ttk.Label(rf, text=f.id, anchor="w", style=id_style).grid(
                row=0, column=2, sticky="ew", padx=(0, 6)
            )
            ttk.Label(
                rf, text=f.type, foreground=COLORS["text_secondary"]
            ).grid(row=0, column=3, sticky="w")
            ttk.Label(
                rf, text=f.role, foreground=COLORS["text_secondary"]
            ).grid(row=0, column=4, sticky="w")
            tags = []
            if row.is_extra:
                tags.append("eigenes")
            if f.clone:
                tags.append("clone")
            name_txt = f.display_name + (f"  [{', '.join(tags)}]" if tags else "")
            ttk.Label(rf, text=name_txt).grid(row=0, column=5, sticky="w")

            refs = {
                "row": row, "active_var": active_var,
                "min_var": None, "target_var": None, "max_var": None,
            }
            if f.type == "number":
                min_var = tk.StringVar(value=_fmt_num(f.spec_min))
                target_var = tk.StringVar(value=_fmt_num(f.spec_target))
                max_var = tk.StringVar(value=_fmt_num(f.spec_max))
                for col, var in enumerate((min_var, target_var, max_var), start=6):
                    e = ttk.Entry(rf, textvariable=var, width=4)
                    e.grid(row=0, column=col, sticky="ew", padx=1)
                    e.bind("<FocusOut>", lambda ev: self._dirty_cb())
                refs.update(min_var=min_var, target_var=target_var, max_var=max_var)
            else:
                # Platzhalter belegt die Spec-Spalten, damit ihre minsize greift.
                ttk.Label(rf, text="").grid(row=0, column=6, columnspan=3)

            # Beide Aktionen in EINER Zelle, damit das ✕ der Extra-Felder den
            # Spalten-Stretch der übrigen Zeilen nicht verschiebt.
            action = ttk.Frame(rf)
            action.grid(row=0, column=9, sticky="w", padx=(6, 1))
            ttk.Button(
                action, text="Bearbeiten", style="Small.TButton",
                command=lambda r=row: self._edit_row(r),
            ).pack(side="left")
            if row.is_extra:
                ttk.Button(
                    action, text="✕", style="Small.TButton",
                    command=lambda r=row: self._remove_extra(r),
                ).pack(side="left", padx=(4, 0))

            # Dezente Trennlinie zwischen den Feldzeilen (vom Drag-Highlight
            # unberührt, da nur die rf-Frames umkonfiguriert werden).
            if i < len(self._rows) - 1:
                ttk.Separator(self._rows_frame, orient="horizontal").grid(
                    row=2 * i + 1, column=0, sticky="ew"
                )

            self._render_refs.append(refs)

        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    # -- Drag & Drop der Feldreihenfolge ----------------------------------- #
    def _drag_start(self, idx: int) -> None:
        self._drag_from = idx

    def _drag_motion(self, event) -> None:
        # Zielzeile optisch hervorheben, solange gezogen wird.
        if self._drag_from is None:
            return
        target = self._row_index_at_pointer()
        for j, rf in enumerate(self._row_frames):
            rf.configure(relief="solid" if j == target else "flat", borderwidth=1 if j == target else 0)

    def _drag_drop(self, event) -> None:
        if self._drag_from is None:
            return
        target = self._row_index_at_pointer()
        src = self._drag_from
        self._drag_from = None
        if target is None or target == src:
            self._render_rows()  # Hervorhebung zurücksetzen
            return
        self._harvest()
        row = self._rows.pop(src)
        self._rows.insert(target, row)
        self._render_rows()
        self._dirty_cb()

    def _row_index_at_pointer(self) -> int | None:
        """Index der Zeile unter dem Mauszeiger (oder None)."""
        x = self._rows_frame.winfo_pointerx()
        y = self._rows_frame.winfo_pointery()
        w = self._rows_frame.winfo_containing(x, y)
        while w is not None:
            if w in self._row_frames:
                return self._row_frames.index(w)
            w = getattr(w, "master", None)
        return None

    def _harvest(self) -> None:
        """Liest die aktuellen Widget-Werte in die Zeilen-Wahrheit zurück."""
        self._inline_errors = []
        for refs in self._render_refs:
            row = refs["row"]
            row.active = bool(refs["active_var"].get())
            if refs["min_var"] is not None:
                ok_min, vmin = _parse_float(refs["min_var"].get())
                ok_t, vt = _parse_float(refs["target_var"].get())
                ok_max, vmax = _parse_float(refs["max_var"].get())
                for ok, raw in (
                    (ok_min, refs["min_var"].get()),
                    (ok_t, refs["target_var"].get()),
                    (ok_max, refs["max_var"].get()),
                ):
                    if not ok:
                        self._inline_errors.append(
                            f"Feld '{row.field.id}': '{raw.strip()}' ist keine Zahl."
                        )
                row.field = replace(
                    row.field, spec_min=vmin, spec_target=vt, spec_max=vmax
                )

    # -- Events ------------------------------------------------------------ #
    def _on_toggle(self, row: _FieldRow, var: tk.BooleanVar) -> None:
        self._harvest()
        row.active = bool(var.get())
        self._dirty_cb()
        self.after_idle(self._render_rows)

    def _on_template_id_typed(self) -> None:
        self._template_id_manual = True
        self._dirty_cb()

    def _on_template_changed(self) -> None:
        new_name = self._template_var.get()
        if not self._process or not new_name or new_name == self._process.template:
            return
        new_tpl = self._templates.get(new_name)
        if new_tpl is None:
            return
        old_tpl = self._current_template()
        self._harvest()
        self.flush()  # template_id/Name/Felder aktuell halten

        new_ids = set(new_tpl.field_map())
        old_ids = set(old_tpl.field_map()) if old_tpl else set()
        would_drop = [
            f.id for f in self._process.fields
            if f.id not in new_ids and f.id in old_ids
        ]
        if would_drop and not messagebox.askyesno(
            "Template wechseln",
            f"Beim Wechsel zu '{new_name}' werden diese Felder entfernt:\n"
            f"{', '.join(would_drop)}\n\nFortfahren?",
            parent=self.winfo_toplevel(),
        ):
            self._template_var.set(self._process.template or "")
            return

        apply_template_change(self._process, old_tpl, new_tpl)
        if not self._template_id_manual:
            self._template_id_var.set(f"IPC{self._stage_hint}_{new_name}")
            self._process.template_id = self._template_id_var.get()
        self.load(self._process, self._stage_hint)
        self._dirty_cb()

    def _edit_row(self, row: _FieldRow) -> None:
        self._harvest()

        def on_save(updated: FieldDef) -> None:
            row.field = updated
            self._render_rows()
            self._dirty_cb()

        if row.is_extra:
            FieldEditorDialog(
                self.winfo_toplevel(), row.field, on_save,
                forbidden_ids=self._template_ids(),
            )
        else:
            FieldOverrideDialog(self.winfo_toplevel(), row.field, on_save)

    def _add_extra_field(self) -> None:
        if self._process is None:
            return
        self._harvest()

        def on_save(new_field: FieldDef) -> None:
            insert_at = 0
            for j, r in enumerate(self._rows):
                if r.active:
                    insert_at = j + 1
            self._rows.insert(
                insert_at, _FieldRow(field=new_field, is_extra=True, active=True)
            )
            self._render_rows()
            self._dirty_cb()

        existing = {r.field.id for r in self._rows}
        FieldEditorDialog(
            self.winfo_toplevel(), None, on_save,
            forbidden_ids=self._template_ids() | existing,
        )

    def _remove_extra(self, row: _FieldRow) -> None:
        if not messagebox.askyesno(
            "Feld entfernen",
            f"Eigenes Feld '{row.field.id}' wirklich entfernen?",
            parent=self.winfo_toplevel(),
        ):
            return
        self._harvest()
        self._rows = [r for r in self._rows if r is not row]
        self._render_rows()
        self._dirty_cb()


# --------------------------------------------------------------------------- #
# Override-Dialog (Template-Feld) — id/typ/rolle fix
# --------------------------------------------------------------------------- #
class FieldOverrideDialog(tk.Toplevel):
    """Editiert die selteneren Override-Attribute eines Template-Feldes
    (Anzeigename, Default, Optional, group_shared, machine_scoped, info_header,
    Optionen). Spec-Werte werden inline in der Checkliste gesetzt; Typ/Rolle
    sind durch das Template fix."""

    def __init__(self, parent, field: FieldDef, on_save):
        super().__init__(parent)
        self._field = field
        self._on_save = on_save
        self.title(f"Feld bearbeiten: {field.id}")
        self.transient(parent)
        self.grab_set()
        self._build()
        place_dialog(self, parent, min_size=(420, 320), resizable=(False, True))
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.focus_set()

    def _build(self) -> None:
        # Buttons in fester Fußzeile, Formular scrollbar → bei vielen
        # Choice-Optionen fällt „Übernehmen“ nie aus dem Fenster.
        footer = ttk.Frame(self)
        footer.pack(side="bottom", fill="x")
        bf = ttk.Frame(footer)
        bf.pack(pady=(8, 12))
        ttk.Button(bf, text="Abbrechen", command=self.destroy).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(
            bf, text="Übernehmen", style="Accent.TButton", command=self._save
        ).pack(side="left")

        body = ttk.Frame(self)
        body.pack(side="top", fill="both", expand=True)
        m = ttk.Frame(make_scrollable(body), padding=15)
        m.pack(fill="both", expand=True)
        m.columnconfigure(1, weight=1)
        f = self._field

        ttk.Label(
            m, text=f"ID: {f.id}    Typ: {f.type}",
            style="Subtitle.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        r = 1
        ttk.Label(m, text="Rolle:").grid(row=r, column=0, sticky="w", pady=3)
        self._role_var = tk.StringVar(value=f.role)
        ttk.Combobox(
            m, textvariable=self._role_var,
            values=["context", "identifier", "measurement", "auto"],
            state="readonly", width=15,
        ).grid(row=r, column=1, sticky="w", pady=3)
        r += 1

        ttk.Label(m, text="Anzeigename:").grid(row=r, column=0, sticky="w", pady=3)
        self._name_var = tk.StringVar(value=f.display_name)
        ttk.Entry(m, textvariable=self._name_var, width=30).grid(
            row=r, column=1, sticky="ew", pady=3
        )
        r += 1

        ttk.Label(m, text="Default-Wert:").grid(row=r, column=0, sticky="w", pady=3)
        self._default_var = tk.StringVar(value=f.default_value or "")
        ttk.Entry(m, textvariable=self._default_var, width=30).grid(
            row=r, column=1, sticky="ew", pady=3
        )
        r += 1

        self._optional_var = tk.BooleanVar(value=f.optional)
        ttk.Checkbutton(
            m, text="Optional (darf leer bleiben)", variable=self._optional_var
        ).grid(row=r, column=0, columnspan=2, sticky="w", pady=2)
        r += 1

        self._clone_var = tk.BooleanVar(value=f.clone)
        r = _checkbox_with_info(
            m, r, "clone", self._clone_var,
            "Je Nutzen/Bahn eine eigene Excel-Spalte („Breite Bahn 1“, „Breite Bahn 2“ …).",
        )

        self._machine_var = tk.BooleanVar(value=f.machine_scoped)
        r = _checkbox_with_info(
            m, r, "machine_scoped", self._machine_var,
            "Wert an die Maschinen-Auswahl gebunden (pro Maschine eigene aktive Rolle).",
        )

        self._info_var = tk.BooleanVar(value=f.info_header)
        r = _checkbox_with_info(
            m, r, "info_header", self._info_var,
            "Wird in den Excel-Kopfblock geschrieben statt als Datenspalte.",
        )

        self._opts_text = None
        if f.type == "choice":
            ttk.Label(m, text="Optionen (je Zeile):").grid(
                row=r, column=0, sticky="nw", pady=3
            )
            self._opts_text = tk.Text(
                m, width=30, height=4, font=FONTS["body"],
                bg=COLORS["surface"], fg=COLORS["text_primary"],
                relief="solid", borderwidth=1,
            )
            self._opts_text.grid(row=r, column=1, sticky="ew", pady=3)
            if f.options:
                self._opts_text.insert("1.0", "\n".join(f.options))
            r += 1

    def _save(self) -> None:
        opts = self._field.options
        if self._opts_text is not None:
            opts = [
                ln.strip()
                for ln in self._opts_text.get("1.0", "end").splitlines()
                if ln.strip()
            ]
            if not opts:
                messagebox.showwarning(
                    "Fehler", "Choice-Feld braucht mindestens eine Option.",
                    parent=self,
                )
                return
        updated = replace(
            self._field,
            role=self._role_var.get(),
            display_name=self._name_var.get().strip() or self._field.display_name,
            default_value=self._default_var.get().strip() or None,
            optional=self._optional_var.get(),
            clone=self._clone_var.get(),
            machine_scoped=self._machine_var.get(),
            info_header=self._info_var.get(),
            options=opts,
        )
        self._on_save(updated)
        self.destroy()


# --------------------------------------------------------------------------- #
# Voll-Editor (nur für extra_fields) — freie ID + alle Attribute
# --------------------------------------------------------------------------- #
class FieldEditorDialog(tk.Toplevel):
    """Voll-Editor für produktunike Felder (extra_fields). Freie ID (muss
    eindeutig sein und darf kein Template-Feld überdecken), alle Attribute."""

    def __init__(self, parent, field: FieldDef | None, on_save, forbidden_ids=None):
        super().__init__(parent)
        self._on_save = on_save
        self._editing = field is not None
        self._forbidden = set(forbidden_ids or ())
        if field is not None:
            self._forbidden.discard(field.id)  # eigene ID erlauben

        self.title("Eigenes Feld bearbeiten" if self._editing else "Neues eigenes Feld")
        self.transient(parent)
        self.grab_set()
        self._build_ui(field)
        place_dialog(self, parent, min_size=(470, 420), resizable=(False, True))
        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_ui(self, field: FieldDef | None) -> None:
        # Buttons in fester Fußzeile, Formular scrollbar.
        footer = ttk.Frame(self)
        footer.pack(side="bottom", fill="x")
        bf = ttk.Frame(footer)
        bf.pack(pady=(10, 12))
        ttk.Button(bf, text="Abbrechen", command=self.destroy).pack(
            side="left", padx=(0, 10)
        )
        ttk.Button(
            bf, text="Speichern", style="Accent.TButton", command=self._save
        ).pack(side="left")

        body = ttk.Frame(self)
        body.pack(side="top", fill="both", expand=True)
        m = ttk.Frame(make_scrollable(body), padding=15)
        m.pack(fill="both", expand=True)
        m.columnconfigure(1, weight=1)
        r = 0

        ttk.Label(m, text="ID:").grid(row=r, column=0, sticky="w", pady=3)
        self._id_var = tk.StringVar(value=field.id if field else "")
        ttk.Entry(m, textvariable=self._id_var, width=30).grid(
            row=r, column=1, sticky="ew", pady=3
        )
        r += 1

        ttk.Label(m, text="Anzeigename:").grid(row=r, column=0, sticky="w", pady=3)
        self._name_var = tk.StringVar(value=field.display_name if field else "")
        ttk.Entry(m, textvariable=self._name_var, width=30).grid(
            row=r, column=1, sticky="ew", pady=3
        )
        r += 1

        ttk.Label(m, text="Typ:").grid(row=r, column=0, sticky="w", pady=3)
        self._type_var = tk.StringVar(value=field.type if field else "number")
        type_combo = ttk.Combobox(
            m, textvariable=self._type_var,
            values=["text", "number", "choice", "date"],
            state="readonly", width=15,
        )
        type_combo.grid(row=r, column=1, sticky="w", pady=3)
        type_combo.bind("<<ComboboxSelected>>", lambda e: self._on_type_changed())
        r += 1

        ttk.Label(m, text="Rolle:").grid(row=r, column=0, sticky="w", pady=3)
        self._role_var = tk.StringVar(value=field.role if field else "measurement")
        ttk.Combobox(
            m, textvariable=self._role_var,
            values=["context", "identifier", "measurement", "auto"],
            state="readonly", width=15,
        ).grid(row=r, column=1, sticky="w", pady=3)
        r += 1

        self._persistent_var = tk.BooleanVar(value=field.persistent if field else False)
        ttk.Checkbutton(m, text="Persistent", variable=self._persistent_var).grid(
            row=r, column=0, columnspan=2, sticky="w", pady=2
        )
        r += 1

        self._optional_var = tk.BooleanVar(value=field.optional if field else False)
        ttk.Checkbutton(m, text="Optional", variable=self._optional_var).grid(
            row=r, column=0, columnspan=2, sticky="w", pady=2
        )
        r += 1

        self._clone_var = tk.BooleanVar(value=field.clone if field else False)
        r = _checkbox_with_info(
            m, r, "clone", self._clone_var,
            "Je Nutzen/Bahn eine eigene Excel-Spalte („Breite Bahn 1“ …).",
        )

        self._info_var = tk.BooleanVar(value=field.info_header if field else False)
        r = _checkbox_with_info(
            m, r, "info_header", self._info_var,
            "Wird in den Excel-Kopfblock geschrieben statt als Datenspalte.",
        )

        self._machine_var = tk.BooleanVar(value=field.machine_scoped if field else False)
        r = _checkbox_with_info(
            m, r, "machine_scoped", self._machine_var,
            "Wert an die Maschinen-Auswahl gebunden.",
        )

        ttk.Label(m, text="Default-Wert:").grid(row=r, column=0, sticky="w", pady=3)
        self._default_var = tk.StringVar(value=(field.default_value or "") if field else "")
        ttk.Entry(m, textvariable=self._default_var, width=30).grid(
            row=r, column=1, sticky="ew", pady=3
        )
        r += 1

        self._spec_frame = ttk.LabelFrame(m, text="Spezifikation", padding=8)
        self._spec_frame.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(8, 3))
        self._spec_frame.columnconfigure(1, weight=1)
        r += 1
        self._target_var = tk.StringVar(
            value=_fmt_num(field.spec_target) if field else ""
        )
        self._min_var = tk.StringVar(value=_fmt_num(field.spec_min) if field else "")
        self._max_var = tk.StringVar(value=_fmt_num(field.spec_max) if field else "")
        for i, (lbl, var) in enumerate(
            [("Zielwert:", self._target_var), ("Minimum:", self._min_var),
             ("Maximum:", self._max_var)]
        ):
            ttk.Label(self._spec_frame, text=lbl).grid(row=i, column=0, sticky="w", pady=2)
            ttk.Entry(self._spec_frame, textvariable=var, width=15).grid(
                row=i, column=1, sticky="w", pady=2
            )

        self._options_frame = ttk.LabelFrame(m, text="Optionen (je Zeile)", padding=8)
        self._options_frame.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(8, 3))
        self._options_frame.columnconfigure(0, weight=1)
        r += 1
        self._opts_text = tk.Text(
            self._options_frame, width=30, height=4, font=FONTS["body"],
            bg=COLORS["surface"], fg=COLORS["text_primary"],
            relief="solid", borderwidth=1,
        )
        self._opts_text.grid(row=0, column=0, sticky="ew")
        if field and field.options:
            self._opts_text.insert("1.0", "\n".join(field.options))

        self._on_type_changed()

    def _on_type_changed(self) -> None:
        typ = self._type_var.get()
        self._spec_frame.grid() if typ == "number" else self._spec_frame.grid_remove()
        self._options_frame.grid() if typ == "choice" else self._options_frame.grid_remove()

    def _save(self) -> None:
        fid = self._id_var.get().strip()
        fname = self._name_var.get().strip()
        if not fid:
            messagebox.showwarning("Fehler", "ID darf nicht leer sein.", parent=self)
            return
        if fid in self._forbidden:
            messagebox.showwarning(
                "Fehler",
                f"ID '{fid}' ist bereits vergeben oder ein Template-Feld. "
                "Bitte eine eindeutige ID wählen.",
                parent=self,
            )
            return
        if not fname:
            messagebox.showwarning(
                "Fehler", "Anzeigename darf nicht leer sein.", parent=self
            )
            return

        ftype = self._type_var.get()
        options = None
        if ftype == "choice":
            options = [
                ln.strip()
                for ln in self._opts_text.get("1.0", "end").splitlines()
                if ln.strip()
            ]
            if not options:
                messagebox.showwarning(
                    "Fehler", "Choice-Feld braucht mindestens eine Option.",
                    parent=self,
                )
                return

        def pf(s):
            ok, v = _parse_float(s)
            return v if ok else None

        field = FieldDef(
            id=fid,
            display_name=fname,
            type=ftype,
            role=self._role_var.get(),
            persistent=self._persistent_var.get(),
            spec_target=pf(self._target_var.get()) if ftype == "number" else None,
            spec_min=pf(self._min_var.get()) if ftype == "number" else None,
            spec_max=pf(self._max_var.get()) if ftype == "number" else None,
            options=options,
            optional=self._optional_var.get(),
            default_value=self._default_var.get().strip() or None,
            clone=self._clone_var.get(),
            info_header=self._info_var.get(),
            machine_scoped=self._machine_var.get(),
        )
        self._on_save(field)
        self.destroy()


# --------------------------------------------------------------------------- #
# Assistent für neue Produkte
# --------------------------------------------------------------------------- #
class NewProductWizard(tk.Toplevel):
    """Geführte Neuanlage: Produkt-Kopf + beliebig viele Prozesse (je
    ProcessEditorPanel, geseedet aus einem Template). Speichert nicht selbst —
    übergibt das fertige Produkt an on_finish (= normaler Speicherpfad)."""

    def __init__(self, parent, templates, on_finish):
        super().__init__(parent)
        self._templates = templates
        self._on_finish = on_finish
        self._processes: list[ProcessConfig] = []
        self._selected: int | None = None

        self.title("Neues Produkt — Assistent")
        self.geometry("1100x740")  # Fallback, falls Maximieren nicht greift
        self.transient(parent)
        self.grab_set()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.focus_set()
        # Groß (fast Vollbild) starten — der Assistent zeigt Prozessliste +
        # Feld-Panel nebeneinander und braucht Platz. Bewusst KEIN
        # state("zoomed"): das überdeckte hier die Taskleiste und verdeckte die
        # Fußzeilen-Buttons. Stattdessen explizite Geometrie mit Rändern.
        self.after_idle(self._maximize)

    def _maximize(self) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        # Bewusst groß (zwei Spalten), aber mit symmetrischem Rand zentriert,
        # damit Taskleiste + Fensterrahmen frei bleiben und die Fußzeilen-Buttons
        # sichtbar sind. (Kein place_dialog: das würde auf Inhaltshöhe schrumpfen.)
        w = min(1600, sw - 80)
        h = min(1000, sh - 120)
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(900, 560)

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        head = ttk.LabelFrame(self, text="1) Produkt", padding=10)
        head.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        head.columnconfigure(1, weight=1)
        head.columnconfigure(3, weight=1)
        ttk.Label(head, text="Produkt-ID (REF):").grid(row=0, column=0, sticky="w", pady=2)
        self._pid_var = tk.StringVar()
        ttk.Entry(head, textvariable=self._pid_var, width=20).grid(
            row=0, column=1, sticky="w", pady=2
        )
        ttk.Label(head, text="Anzeigename:").grid(row=0, column=2, sticky="w", pady=2, padx=(10, 0))
        self._pname_var = tk.StringVar()
        ttk.Entry(head, textvariable=self._pname_var, width=30).grid(
            row=0, column=3, sticky="ew", pady=2
        )
        ttk.Label(head, text="Ausgabeverz.:").grid(row=1, column=0, sticky="w", pady=2)
        self._pout_var = tk.StringVar()
        ttk.Entry(head, textvariable=self._pout_var).grid(
            row=1, column=1, columnspan=2, sticky="ew", pady=2
        )
        ttk.Button(head, text="Wählen…", command=self._choose_dir).grid(
            row=1, column=3, sticky="w", pady=2, padx=(6, 0)
        )

        body = ttk.LabelFrame(self, text="2) Prozesse", padding=10)
        body.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.rowconfigure(0, weight=1)
        self._listbox = tk.Listbox(
            left, font=FONTS["body"], bg=COLORS["background"],
            fg=COLORS["text_primary"], selectbackground=COLORS["accent"],
            selectforeground=COLORS["text_on_primary"], relief="solid",
            borderwidth=1, width=24, exportselection=False,
        )
        self._listbox.grid(row=0, column=0, sticky="nsew")
        self._listbox.bind("<<ListboxSelect>>", lambda e: self._on_select())
        btns = ttk.Frame(left)
        btns.grid(row=1, column=0, pady=(5, 0))
        ttk.Button(btns, text="+ Prozess", command=self._add_process).pack(side="left", padx=2)
        ttk.Button(btns, text="−", style="Icon.TButton", command=self._remove_process).pack(side="left", padx=2)

        self._panel = ProcessEditorPanel(body, self._templates, dirty_callback=lambda: None)
        self._panel.grid(row=0, column=1, sticky="nsew")
        self._placeholder = ttk.Label(
            body, text="„+ Prozess“ klicken, um einen Prozessschritt anzulegen.",
            style="Hint.TLabel",
        )

        foot = ttk.Frame(self)
        foot.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))
        foot.columnconfigure(0, weight=1)
        ttk.Button(foot, text="Abbrechen", command=self.destroy).grid(
            row=0, column=1, padx=(0, 8)
        )
        ttk.Button(
            foot, text="Übernehmen & schließen", style="Accent.TButton",
            command=self._finish,
        ).grid(row=0, column=2)

        self._show_panel(False)

    def _choose_dir(self) -> None:
        path = filedialog.askdirectory(title="Ausgabeverzeichnis wählen", parent=self)
        if path:
            self._pout_var.set(path)

    def _show_panel(self, show: bool) -> None:
        if show:
            self._placeholder.grid_remove()
            self._panel.grid()
        else:
            self._panel.grid_remove()
            self._placeholder.grid(row=0, column=1, sticky="nsew")

    def _flush(self) -> None:
        if self._selected is not None and self._panel.has_process():
            self._panel.flush()
            proc = self._processes[self._selected]
            self._listbox.delete(self._selected)
            self._listbox.insert(self._selected, proc.display_name or proc.template_id)
            self._listbox.selection_set(self._selected)

    def _add_process(self) -> None:
        self._flush()
        name = choose_template(self, self._templates)
        if not name:
            return
        idx = len(self._processes)
        proc = seed_process_from_template(
            self._templates[name], f"IPC{idx + 1}_{name}", f"IPC{idx + 1} {name}"
        )
        self._processes.append(proc)
        self._listbox.insert(tk.END, proc.display_name)
        self._listbox.selection_clear(0, tk.END)
        self._listbox.selection_set(idx)
        self._on_select()

    def _remove_process(self) -> None:
        if self._selected is None:
            return
        del self._processes[self._selected]
        self._listbox.delete(self._selected)
        self._selected = None
        self._show_panel(False)

    def _on_select(self) -> None:
        sel = self._listbox.curselection()
        if not sel:
            return
        self._flush()
        idx = sel[0]
        self._selected = idx
        self._panel.load(self._processes[idx], stage_hint=idx + 1)
        self._show_panel(True)

    def _finish(self) -> None:
        self._flush()
        pid = self._pid_var.get().strip()
        if not pid:
            messagebox.showwarning("Produkt", "Produkt-ID darf nicht leer sein.", parent=self)
            return
        if not self._processes:
            messagebox.showwarning("Produkt", "Mindestens einen Prozess anlegen.", parent=self)
            return
        product = ProductConfig(
            product_id=pid,
            display_name=self._pname_var.get().strip() or pid,
            processes=self._processes,
            output_dir=self._pout_var.get().strip() or None,
        )
        self._on_finish(product)
        self.destroy()


# --------------------------------------------------------------------------- #
# Haupt-View
# --------------------------------------------------------------------------- #
class ConfigEditorView(ttk.Frame):
    """Erstellt und bearbeitet die Produkt-JSONs unter data/products/."""

    def __init__(self, parent, app_state):
        super().__init__(parent)
        self.app_state = app_state
        self._product: ProductConfig | None = None
        self._selected_idx: int | None = None
        self._loaded_id: str | None = None
        # template_ids des gespeicherten Dateistands — Vergleichsbasis für den
        # Wächter in _on_save (leer = neue Datei, Wächter feuert nie).
        self._saved_template_ids: set[str] = set()
        self._dirty = False
        self._build_ui()
        self._load_product_list()

    def _templates(self):
        return load_process_templates(PROCESS_TEMPLATES_DIR)

    # -- UI ---------------------------------------------------------------- #
    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        pf = ttk.LabelFrame(self, text="Produkt", padding=10)
        pf.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        pf.columnconfigure(1, weight=1)

        load_frame = ttk.Frame(pf)
        load_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        load_frame.columnconfigure(0, weight=1)
        self._product_combo = ttk.Combobox(load_frame, state="readonly", width=30)
        self._product_combo.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(load_frame, text="Laden", command=self._on_load).grid(row=0, column=1, padx=2)
        ttk.Button(load_frame, text="Neu (Assistent)", command=self._on_new).grid(row=0, column=2, padx=2)
        ttk.Button(load_frame, text="Kopieren", command=self._on_copy).grid(row=0, column=3, padx=2)

        ttk.Label(pf, text="Produkt-ID:").grid(row=1, column=0, sticky="w", pady=2)
        self._product_id_var = tk.StringVar()
        self._product_id_var.trace_add("write", lambda *_: self._mark_dirty())
        ttk.Entry(pf, textvariable=self._product_id_var, width=30).grid(
            row=1, column=1, sticky="w", pady=2
        )

        ttk.Label(pf, text="Anzeigename:").grid(row=2, column=0, sticky="w", pady=2)
        self._product_name_var = tk.StringVar()
        self._product_name_var.trace_add("write", lambda *_: self._mark_dirty())
        ttk.Entry(pf, textvariable=self._product_name_var, width=50).grid(
            row=2, column=1, columnspan=2, sticky="ew", pady=2
        )

        ttk.Label(pf, text="Ausgabeverz.:").grid(row=3, column=0, sticky="w", pady=2)
        dir_frame = ttk.Frame(pf)
        dir_frame.grid(row=3, column=1, columnspan=2, sticky="ew", pady=2)
        dir_frame.columnconfigure(0, weight=1)
        self._output_dir_var = tk.StringVar()
        self._output_dir_var.trace_add("write", lambda *_: self._mark_dirty())
        ttk.Entry(dir_frame, textvariable=self._output_dir_var).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ttk.Button(dir_frame, text="Wählen...", command=self._choose_output_dir).grid(row=0, column=1)

        badge_frame = ttk.Frame(pf)
        badge_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        # Statusbadge als dezenter Chip (fester Hintergrund + Rahmen) für ein
        # ruhigeres, professionelleres Bild als nur farbiger Text.
        self._badge = ttk.Label(
            badge_frame, text="—", font=FONTS["body_bold"],
            background=COLORS["surface"], padding=(8, 3),
            relief="solid", borderwidth=1,
        )
        self._badge.pack(side="left")
        self._hint_var = tk.StringVar(value="")
        ttk.Label(
            badge_frame, textvariable=self._hint_var, style="Hint.TLabel"
        ).pack(side="left", padx=(12, 0))

        proc_frame = ttk.LabelFrame(self, text="Prozesse", padding=10)
        proc_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        proc_frame.columnconfigure(1, weight=1)
        proc_frame.rowconfigure(0, weight=1)

        left = ttk.Frame(proc_frame)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        self._proc_listbox = tk.Listbox(
            left, font=FONTS["body"], bg=COLORS["background"],
            fg=COLORS["text_primary"], selectbackground=COLORS["accent"],
            selectforeground=COLORS["text_on_primary"], relief="solid",
            borderwidth=1, width=24, exportselection=False,
        )
        self._proc_listbox.grid(row=0, column=0, sticky="nsew")
        self._proc_listbox.bind("<<ListboxSelect>>", lambda e: self._on_process_selected())
        pbtn = ttk.Frame(left)
        pbtn.grid(row=1, column=0, pady=(5, 0))
        ttk.Button(pbtn, text="+", style="Icon.TButton", command=self._add_process).pack(side="left", padx=2)
        ttk.Button(pbtn, text="−", style="Icon.TButton", command=self._remove_process).pack(side="left", padx=2)
        ttk.Button(pbtn, text="↑", style="Icon.TButton", command=lambda: self._move_process(-1)).pack(side="left", padx=2)
        ttk.Button(pbtn, text="↓", style="Icon.TButton", command=lambda: self._move_process(1)).pack(side="left", padx=2)

        right = ttk.Frame(proc_frame)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        self._panel = ProcessEditorPanel(
            right, {}, dirty_callback=self._mark_dirty
        )
        self._panel.grid(row=0, column=0, sticky="nsew")
        self._no_proc_label = ttk.Label(
            right,
            text="Prozess links auswählen oder mit „+“ hinzufügen.",
            style="Hint.TLabel",
        )

        bottom = ttk.Frame(self)
        bottom.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")
        bottom.columnconfigure(0, weight=1)
        self._status_var = tk.StringVar(value="Bereit.")
        ttk.Label(bottom, textvariable=self._status_var).grid(row=0, column=0, sticky="w")
        self._btn_doc = ttk.Button(
            bottom, text="Freigabedokument erzeugen…",
            command=self._on_create_freigabedokument,
        )
        self._btn_doc.grid(row=0, column=1, padx=(10, 0))
        self._btn_release = ttk.Button(
            bottom, text="Freigabe erfassen…", command=self._on_record_freigabe
        )
        self._btn_release.grid(row=0, column=2, padx=(10, 0))
        ttk.Button(
            bottom, text="Speichern", style="Accent.TButton", command=self._on_save
        ).grid(row=0, column=3, padx=(10, 0))

        self._show_panel(False)
        self._refresh_badge()

    # -- Produktliste / Laden --------------------------------------------- #
    def _load_product_list(self) -> None:
        if not PRODUCTS_DIR.exists():
            self._product_combo["values"] = []
            return
        names = sorted(
            p.stem for p in PRODUCTS_DIR.glob("*.json") if p.stem != "freigaben"
        )
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
        try:
            if is_legacy_product(path):
                messagebox.showerror(
                    "Legacy-Config",
                    "Diese Konfiguration ist im alten Vollformat (kein Template).\n"
                    "Bitte template-basiert neu anlegen (Assistent „Neu“).\n"
                    "Bearbeiten ist gesperrt.",
                )
                return
        except Exception as e:
            messagebox.showerror("Laden", f"Datei nicht lesbar:\n{e}")
            return

        tpls = self._templates()
        try:
            product = load_product_config(path, tpls)
        except ValueError as e:
            messagebox.showerror(
                "Template fehlt",
                f"Konfiguration nicht auflösbar (Template fehlt?):\n{e}\n\n"
                "Templates-Verzeichnis prüfen.",
            )
            return

        self._panel.set_templates(tpls)
        self._loaded_id = product.product_id
        self._saved_template_ids = {p.template_id.strip() for p in product.processes}
        self._populate(product)
        self._dirty = False
        self._status_var.set(f"Geladen: {name}")
        self._check_template_revision_drift(path, tpls)
        self._refresh_badge(path=path)

    def _on_new(self) -> None:
        if self._dirty and not self._confirm_discard():
            return
        tpls = self._templates()
        NewProductWizard(self.winfo_toplevel(), tpls, on_finish=self._adopt_wizard_product)

    def _adopt_wizard_product(self, product: ProductConfig) -> None:
        self._panel.set_templates(self._templates())
        self._loaded_id = None  # neues Produkt -> eigene Datei
        self._saved_template_ids = set()
        self._populate(product)
        self._dirty = True
        self._status_var.set("Neues Produkt aus Assistent — bitte speichern.")
        self._refresh_badge()

    def _on_copy(self) -> None:
        name = self._product_combo.get()
        if not name:
            return
        if self._dirty and not self._confirm_discard():
            return
        path = PRODUCTS_DIR / f"{name}.json"
        if not path.exists():
            return
        try:
            if is_legacy_product(path):
                messagebox.showerror(
                    "Legacy-Config",
                    "Legacy-Configs können nicht kopiert werden. "
                    "Bitte template-basiert neu anlegen (Assistent „Neu“).",
                )
                return
            tpls = self._templates()
            product = load_product_config(path, tpls)
        except ValueError as e:
            messagebox.showerror("Kopieren", f"Konfiguration nicht lesbar:\n{e}")
            return
        product.product_id = ""
        product.revision = 1
        product.revision_history = []
        self._panel.set_templates(tpls)
        self._loaded_id = None
        self._saved_template_ids = set()
        self._populate(product)
        self._dirty = True
        self._status_var.set(f"Kopie von {name} — neue Produkt-ID vergeben und speichern.")
        self._refresh_badge()

    def _populate(self, product: ProductConfig) -> None:
        self._product = product
        self._selected_idx = None
        self._product_id_var.set(product.product_id)
        self._product_name_var.set(product.display_name)
        self._output_dir_var.set(product.output_dir or "")
        self._proc_listbox.delete(0, tk.END)
        for proc in product.processes:
            self._proc_listbox.insert(tk.END, proc.display_name or proc.template_id)
        self._show_panel(False)

    def _check_template_revision_drift(self, path, tpls) -> None:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            # Best-effort-Hinweis nach erfolgreichem Laden — nicht GMP-kritisch,
            # aber nicht still verschlucken.
            logger.debug("Template-Revisions-Drift-Check übersprungen: %s nicht erneut lesbar", path)
            return
        drift = []
        for p in raw.get("processes", []):
            tname = p.get("template")
            if not tname or tname not in tpls:
                continue
            old = p.get("template_revision")
            cur = tpls[tname].template_revision
            if old is not None and old != cur:
                drift.append(f"{tname}: Rev {old} → {cur}")
        if drift:
            messagebox.showinfo(
                "Template aktualisiert",
                "Seit dem letzten Speichern wurden Templates aktualisiert. Beim "
                "nächsten Speichern wird gegen die neue Revision aufgelöst:\n\n"
                + "\n".join(drift),
            )

    # -- Prozesse ---------------------------------------------------------- #
    def _flush_panel(self) -> None:
        if (
            self._selected_idx is not None
            and self._product
            and self._panel.has_process()
        ):
            self._panel.flush()
            proc = self._product.processes[self._selected_idx]
            label = proc.display_name or proc.template_id
            self._proc_listbox.delete(self._selected_idx)
            self._proc_listbox.insert(self._selected_idx, label)
            self._proc_listbox.selection_set(self._selected_idx)

    def _on_process_selected(self) -> None:
        sel = self._proc_listbox.curselection()
        if not sel or not self._product:
            return
        self._flush_panel()
        idx = sel[0]
        self._selected_idx = idx
        self._panel.load(self._product.processes[idx], stage_hint=idx + 1)
        self._show_panel(True)

    def _add_process(self) -> None:
        if not self._product:
            return
        self._flush_panel()
        tpls = self._templates()
        name = choose_template(self.winfo_toplevel(), tpls)
        if not name:
            return
        idx = len(self._product.processes)
        proc = seed_process_from_template(
            tpls[name], f"IPC{idx + 1}_{name}", f"IPC{idx + 1} {name}"
        )
        self._product.processes.append(proc)
        self._proc_listbox.insert(tk.END, proc.display_name)
        self._proc_listbox.selection_clear(0, tk.END)
        self._proc_listbox.selection_set(idx)
        self._panel.set_templates(tpls)
        self._on_process_selected()
        self._mark_dirty()

    def _remove_process(self) -> None:
        if not self._product or self._selected_idx is None:
            return
        if not messagebox.askyesno(
            "Prozess entfernen", "Ausgewählten Prozess wirklich entfernen?"
        ):
            return
        del self._product.processes[self._selected_idx]
        self._proc_listbox.delete(self._selected_idx)
        self._selected_idx = None
        self._show_panel(False)
        self._mark_dirty()

    def _move_process(self, direction: int) -> None:
        if not self._product or self._selected_idx is None:
            return
        self._flush_panel()
        idx = self._selected_idx
        new = idx + direction
        if new < 0 or new >= len(self._product.processes):
            return
        procs = self._product.processes
        procs[idx], procs[new] = procs[new], procs[idx]
        self._proc_listbox.delete(0, tk.END)
        for p in procs:
            self._proc_listbox.insert(tk.END, p.display_name or p.template_id)
        self._selected_idx = new
        self._proc_listbox.selection_set(new)
        self._panel.load(procs[new], stage_hint=new + 1)
        self._mark_dirty()

    def _show_panel(self, show: bool) -> None:
        if show:
            self._no_proc_label.grid_remove()
            self._panel.grid()
        else:
            self._panel.grid_remove()
            self._no_proc_label.grid(row=0, column=0, padx=20, pady=40)

    # -- Speichern --------------------------------------------------------- #
    def _on_save(self) -> None:
        if not self._product:
            return
        self._flush_panel()
        self._product.product_id = self._product_id_var.get().strip()
        self._product.display_name = self._product_name_var.get().strip()
        self._product.output_dir = self._output_dir_var.get().strip() or None
        product = self._product
        tpls = self._templates()

        inline = self._panel.inline_errors() if self._panel.has_process() else []
        errors = (
            inline
            + validate_product_config(product)
            + validate_editor_product(product, tpls)
        )
        if errors:
            messagebox.showerror("Validierungsfehler", "\n".join(errors[:25]))
            return

        # template_id-Wächter: geänderte/entfernte IDs an einer bereits
        # gespeicherten Datei brechen Resume + Excel-Dateinamen — nur mit
        # ausdrücklicher Bestätigung speichern.
        if product.product_id == self._loaded_id:
            removed = removed_template_ids(self._saved_template_ids, product)
            if removed and not messagebox.askyesno(
                "Template-ID geändert",
                "Folgende Template-IDs sind gegenüber dem gespeicherten Stand "
                "geändert oder entfernt:\n\n  "
                + "\n  ".join(removed)
                + "\n\nDie Template-ID ist Excel-Dateiname und "
                "Fortsetzungs-Schlüssel: bestehende Excel-Dateien werden NICHT "
                "fortgesetzt, es entstehen neue Dateien.\n\nTrotzdem speichern?",
                icon="warning",
                default="no",
            ):
                self._status_var.set("Speichern abgebrochen (Template-ID-Änderung).")
                return

        target = PRODUCTS_DIR / f"{product.product_id}.json"
        if (
            target.exists()
            and product.product_id != self._loaded_id
            and not messagebox.askyesno(
                "Datei überschreiben",
                f"Die Datei {target.name} existiert bereits.\nÜberschreiben?",
            )
        ):
            return

        change_text: str | None = None
        if self._dirty or not target.exists():
            change_text = simpledialog.askstring(
                "Änderungsbeschreibung",
                "Beschreibung der Änderung für die Revisionshistorie:",
                parent=self,
            )
            if change_text is None:
                self._status_var.set("Speichern abgebrochen.")
                return
            if target.exists():
                product.revision += 1
            user = self.app_state.current_user
            product.revision_history.append({
                "revision": product.revision,
                "date": date.today().isoformat(),
                "user": user.user_id if user else None,
                "change": change_text.strip() or "Bearbeitet im Config-Editor",
            })

        try:
            path = save_product_config(product, PRODUCTS_DIR, tpls)
        except Exception as e:
            messagebox.showerror("Speichern", f"Konnte nicht speichern:\n{e}")
            return

        self._loaded_id = product.product_id
        self._saved_template_ids = {p.template_id.strip() for p in product.processes}
        self._dirty = False

        if self.app_state.audit:
            user = self.app_state.current_user
            self.app_state.audit.log_event(
                Event.CONFIG_EDITED,
                user=user.user_id if user else None,
                file=str(path),
                details={
                    "product": product.product_id,
                    "revision": product.revision,
                    "change": change_text,
                },
            )

        self.app_state.app_config = load_app_config(
            APP_CONFIG_PATH, PRODUCTS_DIR, PROCESS_TEMPLATES_DIR
        )
        self._load_product_list()
        self._refresh_badge(path=path)
        self._status_var.set(f"Gespeichert: {path} (Revision {product.revision})")

    # -- Freigabe ---------------------------------------------------------- #
    def _refresh_badge(self, path=None) -> None:
        from src.config.freigabe import (
            FREIGEGEBEN, GEAENDERT, compute_config_hash, determine_status,
            load_freigaben,
        )
        if not self._product or not self._product.product_id.strip():
            self._set_badge("—", COLORS["text_secondary"])
            self._update_freigabe_buttons(file_ok=False)
            return
        if self._dirty:
            self._set_badge("● Ungespeicherte Änderungen", COLORS["text_secondary"])
            self._update_freigabe_buttons(file_ok=False)
            return
        p = path or (PRODUCTS_DIR / f"{self._product.product_id}.json")
        if not p.exists():
            self._set_badge("○ Ungespeichert", COLORS["text_secondary"])
            self._update_freigabe_buttons(file_ok=False)
            return
        entry = load_freigaben(PRODUCTS_DIR).get(self._product.product_id)
        status = determine_status(entry, compute_config_hash(p), self._product.revision)
        if status == FREIGEGEBEN:
            doc = entry.get("dokument", "") if entry else ""
            self._set_badge(
                f"● Freigegeben (Rev {self._product.revision}, Dok {doc})",
                COLORS["success"],
            )
            self._hint_var.set("")
        elif status == GEAENDERT:
            self._set_badge(
                "● Geändert seit Freigabe — neue Freigabe nötig", COLORS["warning"]
            )
            self._hint_var.set(
                "Nächster Schritt: Freigabedokument erzeugen → unterschreiben → Freigabe erfassen."
            )
        else:
            self._set_badge("○ Nicht freigegeben", COLORS["text_secondary"])
            self._hint_var.set(
                "Nächster Schritt: Freigabedokument erzeugen → unterschreiben → Freigabe erfassen."
            )
        self._update_freigabe_buttons(file_ok=True)

    def _set_badge(self, text: str, color: str) -> None:
        self._badge.configure(text=text, foreground=color)

    def _update_freigabe_buttons(self, file_ok: bool) -> None:
        state = ["!disabled"] if file_ok else ["disabled"]
        self._btn_doc.state(state)
        self._btn_release.state(state)
        if not file_ok and self._product and self._dirty:
            self._hint_var.set("Erst speichern — Freigabe bindet sich an den Dateistand.")

    def _on_create_freigabedokument(self) -> None:
        if not self._product or not self._product.product_id.strip():
            messagebox.showinfo("Freigabedokument", "Bitte zuerst ein Produkt laden.")
            return
        if self._dirty:
            messagebox.showwarning(
                "Freigabedokument",
                "Es gibt ungespeicherte Änderungen. Bitte zuerst speichern — das "
                "Dokument bindet sich an den gespeicherten Dateistand.",
            )
            return
        path = PRODUCTS_DIR / f"{self._product.product_id}.json"
        if not path.exists():
            messagebox.showwarning(
                "Freigabedokument",
                f"Die Datei {path.name} existiert noch nicht. Bitte zuerst speichern.",
            )
            return

        from src.config.freigabedokument import erzeuge_freigabedokument
        from src.config.settings import FREIGABE_VORLAGE_PATH, FREIGABEDOKUMENTE_DIR

        try:
            product = load_product_config(path, self._templates())
            vorlage = FREIGABE_VORLAGE_PATH if FREIGABE_VORLAGE_PATH.exists() else None
            out, unresolved = erzeuge_freigabedokument(
                product, path, FREIGABEDOKUMENTE_DIR, vorlage=vorlage
            )
        except Exception as e:
            messagebox.showerror("Freigabedokument", f"Dokument konnte nicht erzeugt werden:\n{e}")
            return

        if unresolved:
            messagebox.showwarning(
                "Unbekannte Platzhalter in der Vorlage",
                "Folgende Platzhalter wurden nicht ersetzt und stehen noch im "
                "Dokument:\n\n" + ", ".join(sorted(unresolved))
                + "\n\nBitte Vorlage prüfen (Schreibweise siehe CONFIG_REFERENZ.md).",
            )
        hinweis = "" if vorlage else " (HTML-Fallback — keine Word-Vorlage gefunden)"
        self._status_var.set(f"Freigabedokument erzeugt: {out}{hinweis}")
        messagebox.showinfo(
            "Freigabedokument erzeugt",
            f"{out}\n\nAusdrucken, von zwei Personen prüfen/freigeben lassen "
            "(Vier-Augen-Prinzip) und danach hier „Freigabe erfassen…“ ausführen.",
        )

    def _on_record_freigabe(self) -> None:
        if not self._product or not self._product.product_id.strip():
            messagebox.showinfo("Freigabe erfassen", "Bitte zuerst ein Produkt laden.")
            return
        if self._dirty:
            messagebox.showwarning(
                "Freigabe erfassen",
                "Es gibt ungespeicherte Änderungen. Bitte zuerst speichern — die "
                "Freigabe bindet sich an den gespeicherten Dateistand.",
            )
            return
        path = PRODUCTS_DIR / f"{self._product.product_id}.json"
        if not path.exists():
            messagebox.showwarning(
                "Freigabe erfassen",
                f"Die Datei {path.name} existiert noch nicht. Bitte zuerst speichern.",
            )
            return

        from src.config.freigabe import compute_config_hash, record_freigabe

        sha = compute_config_hash(path)

        dialog = tk.Toplevel(self)
        dialog.title("Freigabe erfassen")
        dialog.transient(self)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        ttk.Label(
            frame,
            text=(
                f"Produkt: {self._product.product_id}   "
                f"Revision: {self._product.revision}\n"
                f"SHA-256: {sha}\n\n"
                "Angaben vom unterschriebenen Freigabedokument übernehmen.\n"
                "Der Hash auf dem Dokument muss mit dem obigen übereinstimmen."
            ),
            justify="left",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        vars_: dict[str, tk.StringVar] = {}
        for i, (key, label) in enumerate([
            ("dokument", "Freigabedokument-Nr.:"),
            ("geprueft_von", "Geprüft von:"),
            ("freigegeben_von", "Freigegeben von:"),
        ], start=1):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", pady=3)
            vars_[key] = tk.StringVar()
            ttk.Entry(frame, textvariable=vars_[key], width=36).grid(
                row=i, column=1, sticky="ew", pady=3, padx=(10, 0)
            )

        def on_ok() -> None:
            dokument = vars_["dokument"].get().strip()
            geprueft = vars_["geprueft_von"].get().strip()
            freigegeben = vars_["freigegeben_von"].get().strip()
            if not dokument or not geprueft or not freigegeben:
                messagebox.showwarning(
                    "Freigabe erfassen", "Alle Felder sind Pflicht.", parent=dialog
                )
                return
            if geprueft.lower() == freigegeben.lower():
                messagebox.showwarning(
                    "Vier-Augen-Prinzip",
                    "Geprüft und Freigegeben müssen verschiedene Personen sein.",
                    parent=dialog,
                )
                return
            user = self.app_state.current_user
            entry = record_freigabe(
                PRODUCTS_DIR, self._product.product_id, path, self._product.revision,
                dokument=dokument, geprueft_von=geprueft, freigegeben_von=freigegeben,
                erfasst_von=user.user_id if user else None,
            )
            if self.app_state.audit:
                self.app_state.audit.log_event(
                    Event.CONFIG_RELEASED,
                    user=user.user_id if user else None,
                    file=str(path),
                    details={"product": self._product.product_id, **entry},
                )
            self.app_state.app_config = load_app_config(
                APP_CONFIG_PATH, PRODUCTS_DIR, PROCESS_TEMPLATES_DIR
            )
            self._status_var.set(
                f"Freigabe erfasst: {self._product.product_id} "
                f"Revision {self._product.revision} ({dokument})"
            )
            dialog.destroy()
            self._refresh_badge()

        bf = ttk.Frame(frame)
        bf.grid(row=4, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(bf, text="Abbrechen", command=dialog.destroy).pack(side="left", padx=8)
        ttk.Button(
            bf, text="Freigabe erfassen", style="Accent.TButton", command=on_ok
        ).pack(side="left", padx=8)

        place_dialog(dialog, self, min_size=(420, 240), resizable=(False, False))

    # -- Diverses ---------------------------------------------------------- #
    def _choose_output_dir(self) -> None:
        path = filedialog.askdirectory(title="Ausgabeverzeichnis wählen")
        if path:
            self._output_dir_var.set(path)

    def _mark_dirty(self) -> None:
        self._dirty = True
        self._refresh_badge()

    def _confirm_discard(self) -> bool:
        return messagebox.askyesno(
            "Ungespeicherte Änderungen", "Es gibt ungespeicherte Änderungen. Verwerfen?"
        )
