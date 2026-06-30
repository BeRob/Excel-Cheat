"""Störungsfenster: Erfassen und Freigeben in einem Dialog.

Aus der Messwertmaske per Button geöffnet. Liegt für den aktuellen Kontext
(Produkt + Prozess [+ Maschine]) eine **offene** Störung vor, zeigt das Fenster
oben den Freigabe-Abschnitt; sonst den Erfassungs-Abschnitt. Darunter eine
kompakte Liste der jüngsten Störungen desselben Kontexts.

Das Fenster ist der einzige Ort der Bedien-Interaktion; geschrieben wird über
``app_state.downtime_store`` (eigener System-of-Record), zusätzlich ein
schlankes Audit-Breadcrumb. Die fachliche Auswertung liegt Tk-frei in
``src/downtime/downtime_query.py``.
"""

from __future__ import annotations

import tkinter as tk
import uuid
from datetime import datetime, timezone
from tkinter import ttk, messagebox
from typing import Callable

from src.audit.events import Event
from src.downtime.downtime_models import Stoerung
from src.downtime.downtime_query import find_open, pair_stoerungen
from src.ui.theme import COLORS, FONTS


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def format_dauer(seconds: float | None) -> str:
    """Sekunden → kompakte deutsche Dauer-Anzeige ('1 h 23 min', '12 min', '45 s')."""
    if seconds is None:
        return "—"
    total = int(round(seconds))
    if total < 60:
        return f"{total} s"
    minutes, _sec = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours} h {minutes:02d} min"
    return f"{minutes} min"


class StoerungFenster(tk.Toplevel):
    """Modaler Dialog für Störungserfassung und -freigabe."""

    def __init__(
        self,
        parent: tk.Widget,
        app_state,
        *,
        maschine: str = "",
        on_change: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.maschine = maschine or ""
        self.on_change = on_change

        self.title("Störung / Stillstand")
        self.transient(parent)
        self.grab_set()
        self.configure(bg=COLORS["background"])
        self.protocol("WM_DELETE_WINDOW", self._close)

        self._build()
        self._center()
        self.focus_set()

    # ---- Kontext-Helfer --------------------------------------------------

    def _stoerungen(self) -> list[Stoerung]:
        store = self.app_state.downtime_store
        if store is None:
            return []
        return pair_stoerungen(store.read_all())

    def _open_fault(self) -> Stoerung | None:
        product = self.app_state.selected_product
        process = self.app_state.selected_process
        if not product or not process:
            return None
        return find_open(
            self._stoerungen(),
            produkt_id=product.product_id,
            prozess_template_id=process.template_id,
            maschine=self.maschine or None,
        )

    # ---- Aufbau ----------------------------------------------------------

    def _build(self) -> None:
        for child in self.winfo_children():
            child.destroy()

        self.columnconfigure(0, weight=1)
        product = self.app_state.selected_product
        process = self.app_state.selected_process

        ttk.Label(
            self, text="Störung / Stillstand", style="Subtitle.TLabel",
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 2))

        if not product or not process:
            ttk.Label(
                self,
                text="Kein Produkt/Prozess aktiv — Störung kann nicht erfasst werden.",
                style="Error.TLabel", wraplength=460,
            ).grid(row=1, column=0, padx=15, pady=10)
            ttk.Button(self, text="Schließen", command=self._close).grid(
                row=2, column=0, pady=(0, 15)
            )
            return

        ctx = (
            f"{product.display_name}  ·  {process.display_name}"
            f"  ·  Schicht {self.app_state.current_shift or '?'}"
        )
        if self.maschine:
            ctx += f"  ·  Maschine {self.maschine}"
        ttk.Label(self, text=ctx, style="HeaderInfo.TLabel").grid(
            row=1, column=0, sticky="w", padx=15, pady=(0, 8)
        )

        self._open = self._open_fault()
        # active_downtime im State spiegeln, damit FormView/Reconcile konsistent ist.
        self.app_state.active_downtime = (
            {
                "id": self._open.id, "ts_start": self._open.ts_start,
                "kategorie": self._open.kategorie, "ursache": self._open.ursache,
                "station": self._open.station, "maschine": self._open.maschine,
            }
            if self._open else None
        )

        if self._open:
            self._build_freigabe(self._open)
        else:
            self._build_erfassen()

        self._build_letzte_liste()

        ttk.Button(self, text="Schließen", command=self._close).grid(
            row=9, column=0, pady=(6, 15)
        )

    # ---- Erfassen --------------------------------------------------------

    def _build_erfassen(self) -> None:
        frame = ttk.LabelFrame(self, text="Störung erfassen", padding=12)
        frame.grid(row=2, column=0, sticky="ew", padx=15, pady=5)
        frame.columnconfigure(1, weight=1)

        codes = self.app_state.stoerungs_codes
        kat_namen = codes.kategorie_namen() if codes else []

        self.kat_var = tk.StringVar()
        self.urs_var = tk.StringVar()

        ttk.Label(frame, text="Kategorie:").grid(row=0, column=0, sticky="w", pady=4, padx=(0, 8))
        self.kat_combo = ttk.Combobox(
            frame, textvariable=self.kat_var, values=kat_namen,
            state="readonly", width=32,
        )
        self.kat_combo.grid(row=0, column=1, sticky="w", pady=4)
        self.kat_combo.bind("<<ComboboxSelected>>", self._on_kategorie)

        ttk.Label(frame, text="Ursache:").grid(row=1, column=0, sticky="w", pady=4, padx=(0, 8))
        self.urs_combo = ttk.Combobox(
            frame, textvariable=self.urs_var, values=[],
            state="readonly", width=32,
        )
        self.urs_combo.grid(row=1, column=1, sticky="w", pady=4)
        self.urs_combo.bind("<<ComboboxSelected>>", lambda _e: self._update_erfassen_btn())

        ttk.Label(frame, text="Station (Ort):").grid(row=2, column=0, sticky="w", pady=4, padx=(0, 8))
        self.station_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.station_var, width=34).grid(
            row=2, column=1, sticky="w", pady=4
        )

        ttk.Label(frame, text="Beschreibung:").grid(row=3, column=0, sticky="nw", pady=4, padx=(0, 8))
        self.beschreibung_txt = tk.Text(
            frame, height=3, width=34, font=FONTS["body"],
            bg=COLORS["surface"], fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"], relief="solid", borderwidth=1,
        )
        self.beschreibung_txt.grid(row=3, column=1, sticky="ew", pady=4)

        ttk.Label(
            frame, text="Startzeit: jetzt (wird beim Erfassen gesetzt)",
            style="HeaderInfo.TLabel",
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 2))

        self.erfassen_btn = ttk.Button(
            frame, text="Störung erfassen", style="Accent.TButton",
            command=self._do_erfassen, state="disabled",
        )
        self.erfassen_btn.grid(row=5, column=0, columnspan=2, pady=(8, 0))

        self._hint = ttk.Label(self, text="", style="Error.TLabel", wraplength=460)
        self._hint.grid(row=3, column=0, padx=15)

    def _on_kategorie(self, _event=None) -> None:
        codes = self.app_state.stoerungs_codes
        ursachen = codes.ursachen(self.kat_var.get()) if codes else []
        self.urs_combo["values"] = ursachen
        self.urs_var.set("")
        self._update_erfassen_btn()

    def _update_erfassen_btn(self) -> None:
        ok = bool(self.kat_var.get()) and bool(self.urs_var.get())
        ok = ok and self.app_state.downtime_store is not None
        self.erfassen_btn.config(state="normal" if ok else "disabled")

    def _do_erfassen(self) -> None:
        product = self.app_state.selected_product
        process = self.app_state.selected_process
        user = self.app_state.current_user
        audit = self.app_state.audit
        store = self.app_state.downtime_store
        if not product or not process or store is None:
            return

        record = {
            "id": uuid.uuid4().hex,
            "ts_start": _now_iso(),
            "produkt_id": product.product_id,
            "prozess_template_id": process.template_id,
            "prozess_name": process.display_name,
            "schicht": self.app_state.current_shift or "",
            "maschine": self.maschine,
            "station": self.station_var.get().strip(),
            "kategorie": self.kat_var.get(),
            "ursache": self.urs_var.get(),
            "beschreibung": self.beschreibung_txt.get("1.0", "end").strip(),
            "erfasser_user": user.user_id if user else "",
            "host": audit.host if audit else "",
            "win_user": audit.os_user if audit else "",
        }
        store.append_start(record)
        if store.degraded_reason == "fallback_failed":
            if audit:
                audit.log_event(
                    Event.STOERUNG_FAIL, level="error",
                    user=user.user_id if user else None,
                    details={"phase": "start", "id": record["id"], "reason": "fallback_failed"},
                )
            messagebox.showerror(
                "Störung", "Die Störung konnte nicht gespeichert werden "
                "(Speicher nicht erreichbar). Bitte Technik/IT informieren.",
                parent=self,
            )
            return

        if audit:
            audit.log_event(
                Event.STOERUNG_START,
                user=user.user_id if user else None,
                details={
                    "id": record["id"], "produkt": product.product_id,
                    "prozess": process.template_id, "maschine": self.maschine,
                    "station": record["station"], "kategorie": record["kategorie"],
                    "ursache": record["ursache"],
                },
            )

        self.app_state.active_downtime = record
        if self.on_change:
            self.on_change()
        messagebox.showinfo(
            "Störung erfasst",
            "Störung erfasst — die Stillstandszeit läuft.\n"
            "Nach der Behebung über diesen Dialog die Maschine freigeben.",
            parent=self,
        )
        self._build()  # neu aufbauen → zeigt jetzt den Freigabe-Abschnitt

    # ---- Freigeben -------------------------------------------------------

    def _build_freigabe(self, fault: Stoerung) -> None:
        frame = ttk.LabelFrame(self, text="Offene Störung — Maschine freigeben", padding=12)
        frame.grid(row=2, column=0, sticky="ew", padx=15, pady=5)
        frame.columnconfigure(1, weight=1)

        start = fault.start_dt
        start_txt = start.strftime("%Y-%m-%d %H:%M") if start else fault.ts_start
        laufende = format_dauer(fault.computed_dauer_sekunden()
                                if not fault.offen else
                                ((datetime.now(timezone.utc).astimezone() - start).total_seconds()
                                 if start else None))

        info = [
            ("Beginn", start_txt),
            ("Bisherige Dauer", laufende),
            ("Klassifizierung", f"{fault.kategorie} / {fault.ursache}"),
        ]
        if fault.station:
            info.append(("Station", fault.station))
        if fault.beschreibung:
            info.append(("Beschreibung", fault.beschreibung))
        for r, (lbl, val) in enumerate(info):
            ttk.Label(frame, text=f"{lbl}:", font=("Segoe UI", 9, "bold")).grid(
                row=r, column=0, sticky="nw", pady=2, padx=(0, 8)
            )
            ttk.Label(frame, text=val, wraplength=320).grid(
                row=r, column=1, sticky="w", pady=2
            )

        base = len(info)
        ttk.Separator(frame, orient="horizontal").grid(
            row=base, column=0, columnspan=2, sticky="ew", pady=8
        )

        ttk.Label(frame, text="Techniker (Name):").grid(
            row=base + 1, column=0, sticky="w", pady=4, padx=(0, 8)
        )
        self.techniker_var = tk.StringVar()
        self.techniker_var.trace_add("write", lambda *_: self._update_freigabe_btn())
        ttk.Entry(frame, textvariable=self.techniker_var, width=34).grid(
            row=base + 1, column=1, sticky="w", pady=4
        )

        ttk.Label(frame, text="Behebung:").grid(
            row=base + 2, column=0, sticky="nw", pady=4, padx=(0, 8)
        )
        self.behebung_txt = tk.Text(
            frame, height=4, width=34, font=FONTS["body"],
            bg=COLORS["surface"], fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"], relief="solid", borderwidth=1,
        )
        self.behebung_txt.grid(row=base + 2, column=1, sticky="ew", pady=4)
        self.behebung_txt.bind("<KeyRelease>", lambda _e: self._update_freigabe_btn())

        ttk.Label(
            frame, text="Endzeit: jetzt (wird bei Freigabe gesetzt)",
            style="HeaderInfo.TLabel",
        ).grid(row=base + 3, column=0, columnspan=2, sticky="w", pady=(6, 2))

        self.freigabe_btn = ttk.Button(
            frame, text="Maschine freigeben", style="Accent.TButton",
            command=lambda: self._do_freigabe(fault), state="disabled",
        )
        self.freigabe_btn.grid(row=base + 4, column=0, columnspan=2, pady=(8, 0))

    def _update_freigabe_btn(self) -> None:
        techniker = self.techniker_var.get().strip()
        behebung = self.behebung_txt.get("1.0", "end").strip()
        ok = bool(techniker) and bool(behebung) and self.app_state.downtime_store is not None
        self.freigabe_btn.config(state="normal" if ok else "disabled")

    def _do_freigabe(self, fault: Stoerung) -> None:
        user = self.app_state.current_user
        audit = self.app_state.audit
        store = self.app_state.downtime_store
        if store is None:
            return

        ende_iso = _now_iso()
        start = fault.start_dt
        ende = datetime.fromisoformat(ende_iso)
        dauer = max(0.0, (ende - start).total_seconds()) if start else None

        record = {
            "id": fault.id,
            "ts_ende": ende_iso,
            "dauer_sekunden": dauer,
            "techniker_name": self.techniker_var.get().strip(),
            "behebung": self.behebung_txt.get("1.0", "end").strip(),
            "freigabe_user": user.user_id if user else "",
        }
        store.append_ende(record)
        if store.degraded_reason == "fallback_failed":
            if audit:
                audit.log_event(
                    Event.STOERUNG_FAIL, level="error",
                    user=user.user_id if user else None,
                    details={"phase": "ende", "id": fault.id, "reason": "fallback_failed"},
                )
            messagebox.showerror(
                "Freigabe", "Die Freigabe konnte nicht gespeichert werden "
                "(Speicher nicht erreichbar). Bitte Technik/IT informieren.",
                parent=self,
            )
            return

        if audit:
            audit.log_event(
                Event.STOERUNG_ENDE,
                user=user.user_id if user else None,
                details={
                    "id": fault.id, "dauer_sekunden": dauer,
                    "techniker": record["techniker_name"],
                },
            )

        self.app_state.active_downtime = None
        if self.on_change:
            self.on_change()
        messagebox.showinfo(
            "Maschine freigegeben",
            f"Maschine freigegeben. Stillstandsdauer: {format_dauer(dauer)}.",
            parent=self,
        )
        self._close()

    # ---- Letzte Störungen ------------------------------------------------

    def _build_letzte_liste(self) -> None:
        product = self.app_state.selected_product
        process = self.app_state.selected_process
        if not product or not process:
            return
        items = [
            s for s in self._stoerungen()
            if s.produkt_id == product.product_id
            and s.prozess_template_id == process.template_id
        ]
        items = list(reversed(items))[:5]
        if not items:
            return

        frame = ttk.LabelFrame(self, text="Letzte Störungen (dieser Prozess)", padding=8)
        frame.grid(row=8, column=0, sticky="ew", padx=15, pady=(8, 2))
        frame.columnconfigure(0, weight=1)

        tree = ttk.Treeview(
            frame, show="headings", height=min(len(items), 5),
            columns=("beginn", "dauer", "klass", "station", "status"),
        )
        for col, txt, w in (
            ("beginn", "Beginn", 110), ("dauer", "Dauer", 70),
            ("klass", "Kategorie/Ursache", 150), ("station", "Station", 90),
            ("status", "Status", 70),
        ):
            tree.heading(col, text=txt)
            tree.column(col, width=w, anchor="w")
        for s in items:
            start = s.start_dt
            tree.insert("", "end", values=(
                start.strftime("%Y-%m-%d %H:%M") if start else s.ts_start,
                format_dauer(s.computed_dauer_sekunden()),
                f"{s.kategorie} / {s.ursache}",
                s.station or "—",
                s.status,
            ))
        tree.grid(row=0, column=0, sticky="ew")

    # ---- Sonstiges -------------------------------------------------------

    def _center(self) -> None:
        self.update_idletasks()
        w = max(540, self.winfo_reqwidth())
        h = self.winfo_reqheight()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = min(w, sw - 80)
        h = min(h, sh - 100)
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2 - 20)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _close(self) -> None:
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
