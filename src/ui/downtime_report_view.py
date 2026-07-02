"""Admin-Tab: Störungen / Auswertung.

Liest den Störungs-Store, filtert nach Zeitraum/Produkt/Prozess/Station/
Kategorie/Status und zeigt Detailtabelle, KPI-Kacheln (Anzahl, Σ Störzeit,
MTTR, MTBF, Verfügbarkeit) sowie eine wählbare Gruppierung. Export als .xlsx.

Die fachliche Rechnung liegt Tk-frei in ``src/downtime/downtime_query.py`` —
diese View ist reine Darstellung.
"""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import ttk, filedialog, messagebox

from src.downtime.downtime_query import (
    aggregate_by_kategorie, aggregate_by_prozess, aggregate_by_station,
    anzahl_ausfaelle, filter_stoerungen, gesamt_stoerzeit, mtbf, mttr,
    pair_stoerungen, verfuegbarkeit,
)
from src.ui.downtime_window import format_dauer
from src.ui.theme import COLORS


_ALLE = "(alle)"


class DowntimeReportView(ttk.Frame):
    """Auswertung der erfassten Störungen/Stillstandszeiten."""

    def __init__(self, parent, app_state):
        super().__init__(parent)
        self.app_state = app_state
        self._stoerungen = []      # alle gepaarten Störungen (ungefiltert)
        self._filtered = []        # aktuell gefilterte
        self._build_ui()

    # ---- Aufbau ----------------------------------------------------------

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        ttk.Label(self, text="Störungen / Auswertung", style="Subtitle.TLabel").grid(
            row=0, column=0, sticky="w", padx=15, pady=(10, 5)
        )

        # --- Filterleiste ---
        f = ttk.LabelFrame(self, text="Filter", padding=8)
        f.grid(row=1, column=0, sticky="ew", padx=15, pady=4)
        for c in (1, 3, 5, 7):
            f.columnconfigure(c, weight=1)

        self.von_var = tk.StringVar()
        self.bis_var = tk.StringVar()
        self.produkt_var = tk.StringVar(value=_ALLE)
        self.prozess_var = tk.StringVar(value=_ALLE)
        self.station_var = tk.StringVar()
        self.kategorie_var = tk.StringVar(value=_ALLE)
        self.status_var = tk.StringVar(value=_ALLE)
        self.planzeit_var = tk.StringVar()

        ttk.Label(f, text="Von (JJJJ-MM-TT):").grid(row=0, column=0, sticky="w", padx=4, pady=3)
        ttk.Entry(f, textvariable=self.von_var, width=14).grid(row=0, column=1, sticky="w", pady=3)
        ttk.Label(f, text="Bis:").grid(row=0, column=2, sticky="w", padx=4, pady=3)
        ttk.Entry(f, textvariable=self.bis_var, width=14).grid(row=0, column=3, sticky="w", pady=3)

        ttk.Label(f, text="Station:").grid(row=0, column=4, sticky="w", padx=4, pady=3)
        ttk.Entry(f, textvariable=self.station_var, width=14).grid(row=0, column=5, sticky="w", pady=3)
        ttk.Label(f, text="Status:").grid(row=0, column=6, sticky="w", padx=4, pady=3)
        self.status_combo = ttk.Combobox(
            f, textvariable=self.status_var, values=[_ALLE, "offen", "behoben"],
            state="readonly", width=12,
        )
        self.status_combo.grid(row=0, column=7, sticky="w", pady=3)

        ttk.Label(f, text="Produkt:").grid(row=1, column=0, sticky="w", padx=4, pady=3)
        self.produkt_combo = ttk.Combobox(f, textvariable=self.produkt_var, state="readonly", width=14)
        self.produkt_combo.grid(row=1, column=1, sticky="w", pady=3)
        ttk.Label(f, text="Prozess:").grid(row=1, column=2, sticky="w", padx=4, pady=3)
        self.prozess_combo = ttk.Combobox(f, textvariable=self.prozess_var, state="readonly", width=14)
        self.prozess_combo.grid(row=1, column=3, sticky="w", pady=3)
        ttk.Label(f, text="Kategorie:").grid(row=1, column=4, sticky="w", padx=4, pady=3)
        self.kategorie_combo = ttk.Combobox(f, textvariable=self.kategorie_var, state="readonly", width=14)
        self.kategorie_combo.grid(row=1, column=5, sticky="w", pady=3)
        ttk.Label(f, text="Planzeit (Std):").grid(row=1, column=6, sticky="w", padx=4, pady=3)
        ttk.Entry(f, textvariable=self.planzeit_var, width=12).grid(row=1, column=7, sticky="w", pady=3)

        # Schnellwahl + Aktionen
        bar = ttk.Frame(f)
        bar.grid(row=2, column=0, columnspan=8, sticky="w", pady=(6, 0))
        ttk.Button(bar, text="Letzte 2 Wochen", command=lambda: self._quick_range(14)).pack(side="left", padx=2)
        ttk.Button(bar, text="Dieser Monat", command=self._quick_month).pack(side="left", padx=2)
        ttk.Button(bar, text="Alles", command=self._quick_all).pack(side="left", padx=2)
        ttk.Button(bar, text="Aktualisieren", command=self._refresh, style="Accent.TButton").pack(side="left", padx=(12, 2))
        ttk.Button(bar, text="Export .xlsx", command=self._export).pack(side="left", padx=2)

        # --- KPI-Kacheln ---
        self.kpi_var = tk.StringVar(value="Noch nicht geladen.")
        ttk.Label(self, textvariable=self.kpi_var, style="Title.TLabel", wraplength=1100).grid(
            row=2, column=0, sticky="w", padx=15, pady=(6, 2)
        )

        # --- Detailtabelle ---
        table = ttk.Frame(self)
        table.grid(row=3, column=0, sticky="nsew", padx=15, pady=6)
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)

        cols = ("beginn", "ende", "dauer", "produkt", "prozess", "station",
                "kategorie", "ursache", "status", "erfasser", "techniker")
        self.tree = ttk.Treeview(table, show="headings", columns=cols)
        headings = {
            "beginn": "Beginn", "ende": "Ende", "dauer": "Dauer",
            "produkt": "Produkt", "prozess": "Prozess", "station": "Station",
            "kategorie": "Kategorie", "ursache": "Ursache", "status": "Status",
            "erfasser": "Erfasser", "techniker": "Techniker",
        }
        widths = {
            "beginn": 120, "ende": 120, "dauer": 70, "produkt": 90, "prozess": 110,
            "station": 80, "kategorie": 110, "ursache": 110, "status": 70,
            "erfasser": 80, "techniker": 90,
        }
        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = ttk.Scrollbar(table, orient="horizontal", command=self.tree.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # --- Gruppierung ---
        g = ttk.LabelFrame(self, text="Gruppierung", padding=8)
        g.grid(row=4, column=0, sticky="ew", padx=15, pady=(0, 10))
        g.columnconfigure(0, weight=1)
        top = ttk.Frame(g)
        top.grid(row=0, column=0, sticky="w")
        ttk.Label(top, text="Gruppieren nach:").pack(side="left", padx=(0, 6))
        self.group_var = tk.StringVar(value="Station")
        gc = ttk.Combobox(
            top, textvariable=self.group_var, state="readonly", width=14,
            values=["Station", "Kategorie", "Prozess"],
        )
        gc.pack(side="left")
        gc.bind("<<ComboboxSelected>>", lambda _e: self._render_groups())

        self.group_tree = ttk.Treeview(
            g, show="headings", height=5,
            columns=("key", "anzahl", "offen", "dauer_sum", "dauer_avg"),
        )
        for c, txt, w in (
            ("key", "Gruppe", 200), ("anzahl", "Anzahl", 80), ("offen", "offen", 70),
            ("dauer_sum", "Σ Störzeit", 110), ("dauer_avg", "Ø Dauer", 110),
        ):
            self.group_tree.heading(c, text=txt)
            self.group_tree.column(c, width=w, anchor="w")
        self.group_tree.grid(row=1, column=0, sticky="ew", pady=(6, 0))

        self.status_msg = tk.StringVar()
        ttk.Label(self, textvariable=self.status_msg, foreground=COLORS["text_secondary"]).grid(
            row=5, column=0, sticky="w", padx=15, pady=(0, 6)
        )

        self._quick_range(14)  # Default: letzte 2 Wochen

    # ---- Schnellwahl -----------------------------------------------------

    def _quick_range(self, days: int) -> None:
        heute = date.today()
        self.von_var.set((heute - timedelta(days=days)).isoformat())
        self.bis_var.set(heute.isoformat())
        self._refresh()

    def _quick_month(self) -> None:
        heute = date.today()
        self.von_var.set(heute.replace(day=1).isoformat())
        self.bis_var.set(heute.isoformat())
        self._refresh()

    def _quick_all(self) -> None:
        self.von_var.set("")
        self.bis_var.set("")
        self._refresh()

    # ---- Laden & Filtern -------------------------------------------------

    def _parse_date(self, value: str) -> date | None:
        value = value.strip()
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    def _load(self) -> None:
        store = self.app_state.downtime_store
        self._stoerungen = pair_stoerungen(store.read_all()) if store else []
        # Filter-Optionen aus den Daten ableiten.
        produkte = sorted({s.produkt_id for s in self._stoerungen if s.produkt_id})
        prozesse = sorted({s.prozess_name or s.prozess_template_id for s in self._stoerungen})
        kategorien = sorted({s.kategorie for s in self._stoerungen if s.kategorie})
        self.produkt_combo["values"] = [_ALLE, *produkte]
        self.prozess_combo["values"] = [_ALLE, *prozesse]
        self.kategorie_combo["values"] = [_ALLE, *kategorien]

    def _refresh(self) -> None:
        self._load()

        prozess_sel = self.prozess_var.get()
        prozess_tid = None
        if prozess_sel and prozess_sel != _ALLE:
            # Auswahl ist der Anzeige-/Template-Name → auf template_id zurückmappen.
            for s in self._stoerungen:
                if (s.prozess_name or s.prozess_template_id) == prozess_sel:
                    prozess_tid = s.prozess_template_id
                    break

        self._filtered = filter_stoerungen(
            self._stoerungen,
            von=self._parse_date(self.von_var.get()),
            bis=self._parse_date(self.bis_var.get()),
            produkt_id=None if self.produkt_var.get() in ("", _ALLE) else self.produkt_var.get(),
            prozess_template_id=prozess_tid,
            station=self.station_var.get().strip() or None,
            kategorie=None if self.kategorie_var.get() in ("", _ALLE) else self.kategorie_var.get(),
            status=None if self.status_var.get() in ("", _ALLE) else self.status_var.get(),
        )
        self._render_table()
        self._render_kpis()
        self._render_groups()
        self.status_msg.set(f"{len(self._filtered)} Störung(en) im Filter.")

    def _render_table(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for s in reversed(self._filtered):
            start = s.start_dt
            ende = s.ende_dt
            self.tree.insert("", "end", values=(
                start.strftime("%Y-%m-%d %H:%M") if start else s.ts_start,
                ende.strftime("%Y-%m-%d %H:%M") if ende else "—",
                format_dauer(s.computed_dauer_sekunden()),
                s.produkt_id, s.prozess_name or s.prozess_template_id,
                s.station or "—", s.kategorie, s.ursache, s.status,
                s.erfasser_user, s.techniker_name or "—",
            ))

    # ---- KPIs ------------------------------------------------------------

    def _suggested_planzeit_h(self) -> float:
        """Vorschlag: aktive Tage × Summe der Schichtstunden/Tag (aus app_config)."""
        tage = {s.start_dt.date() for s in self._filtered if s.start_dt}
        cfg = self.app_state.app_config
        shift_h = 0.0
        for sh in (cfg.shifts if cfg else []):
            dur = (sh.end_hour - sh.start_hour) % 24
            shift_h += dur or 24
        if shift_h == 0:
            shift_h = 24.0
        return len(tage) * shift_h

    def _planzeit_sekunden(self) -> float:
        raw = self.planzeit_var.get().strip().replace(",", ".")
        try:
            return float(raw) * 3600 if raw else 0.0
        except ValueError:
            return 0.0

    def _render_kpis(self) -> None:
        # Planzeit-Vorschlag eintragen, falls der Admin nichts gesetzt hat.
        if not self.planzeit_var.get().strip():
            sug = self._suggested_planzeit_h()
            if sug > 0:
                self.planzeit_var.set(f"{sug:g}")

        planzeit_s = self._planzeit_sekunden()
        anzahl = len(self._filtered)
        ausfaelle = anzahl_ausfaelle(self._filtered)
        stoerzeit = gesamt_stoerzeit(self._filtered)
        _mttr = mttr(self._filtered)
        _mtbf = mtbf(self._filtered, planzeit_s) if planzeit_s else None
        _verf = verfuegbarkeit(self._filtered, planzeit_s) if planzeit_s else None

        parts = [
            f"Störungen: {anzahl} ({ausfaelle} behoben)",
            f"Σ Störzeit: {format_dauer(stoerzeit)}",
            f"MTTR: {format_dauer(_mttr)}",
            f"MTBF: {format_dauer(_mtbf)}",
            f"Verfügbarkeit: {f'{_verf * 100:.1f} %' if _verf is not None else '—'}",
        ]
        self.kpi_var.set("    |    ".join(parts))

    # ---- Gruppierung -----------------------------------------------------

    def _render_groups(self) -> None:
        if not hasattr(self, "group_tree"):
            return
        mode = self.group_var.get()
        if mode == "Kategorie":
            agg = aggregate_by_kategorie(self._filtered)
        elif mode == "Prozess":
            agg = aggregate_by_prozess(self._filtered)
        else:
            agg = aggregate_by_station(self._filtered)

        self.group_tree.delete(*self.group_tree.get_children())
        for key, b in sorted(agg.items(), key=lambda kv: kv[1]["anzahl"], reverse=True):
            self.group_tree.insert("", "end", values=(
                key, b["anzahl"], b["offen"],
                format_dauer(b["dauer_sum"]), format_dauer(b["dauer_avg"]),
            ))

    # ---- Export ----------------------------------------------------------

    def _export(self) -> None:
        if not self._filtered:
            messagebox.showinfo("Export", "Keine Störungen im aktuellen Filter.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            title="Störungs-Auswertung exportieren",
            defaultextension=".xlsx",
            filetypes=[("Excel-Dateien", "*.xlsx")],
            initialfile=f"Stoerungen_{date.today().isoformat()}.xlsx",
        )
        if not path:
            return
        try:
            from openpyxl import Workbook
            from src.excel.safe_save import save_workbook_atomic

            wb = Workbook()
            ws = wb.active
            ws.title = "Störungen"
            headers = [
                "Beginn", "Ende", "Dauer (min)", "Produkt", "Prozess", "Station",
                "Kategorie", "Ursache", "Status", "Erfasser", "Techniker",
                "Beschreibung", "Behebung",
            ]
            ws.append(headers)
            for s in self._filtered:
                start = s.start_dt
                ende = s.ende_dt
                dauer = s.computed_dauer_sekunden()
                ws.append([
                    start.strftime("%Y-%m-%d %H:%M") if start else s.ts_start,
                    ende.strftime("%Y-%m-%d %H:%M") if ende else "",
                    round(dauer / 60, 1) if dauer is not None else "",
                    s.produkt_id, s.prozess_name or s.prozess_template_id,
                    s.station, s.kategorie, s.ursache, s.status,
                    s.erfasser_user, s.techniker_name, s.beschreibung, s.behebung,
                ])
            # Aggregat-Blatt
            ws2 = wb.create_sheet("Aggregat")
            ws2.append(["Gruppierung", self.group_var.get()])
            ws2.append(["Gruppe", "Anzahl", "offen", "Σ Störzeit (min)", "Ø Dauer (min)"])
            mode = self.group_var.get()
            agg = (aggregate_by_kategorie if mode == "Kategorie" else
                   aggregate_by_prozess if mode == "Prozess" else
                   aggregate_by_station)(self._filtered)
            for key, b in sorted(agg.items(), key=lambda kv: kv[1]["anzahl"], reverse=True):
                ws2.append([
                    key, b["anzahl"], b["offen"],
                    round(b["dauer_sum"] / 60, 1), round(b["dauer_avg"] / 60, 1),
                ])
            save_workbook_atomic(wb, path)
            messagebox.showinfo("Export", f"Exportiert nach:\n{path}", parent=self)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Export", f"Export fehlgeschlagen: {e}", parent=self)
