"""Einfacher Datumsauswahl-Dialog (ttk-only, ohne externe Dependencies)."""

from __future__ import annotations

import calendar
import tkinter as tk
from datetime import date, datetime
from tkinter import ttk
from typing import Callable

from src.ui.theme import COLORS


_WEEKDAYS_DE = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
_MONTHS_DE = (
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
)


def parse_date_string(value: str) -> date | None:
    """Versucht, einen String im Format DD.MM.YYYY zu parsen."""
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d.%m.%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def format_date(d: date) -> str:
    return d.strftime("%d.%m.%Y")


class DatePickerDialog(tk.Toplevel):
    """Modaler Kalender-Popup. Auswahl wird über `on_pick` als 'DD.MM.YYYY' geliefert."""

    def __init__(
        self,
        parent: tk.Widget,
        initial: str,
        on_pick: Callable[[str], None],
    ) -> None:
        super().__init__(parent)
        self.on_pick = on_pick

        today = date.today()
        start = parse_date_string(initial) or today
        self._year = start.year
        self._month = start.month
        self._selected = start

        self.title("Datum auswählen")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.configure(bg=COLORS["background"])
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self._build_ui()
        self._render_calendar()

        self.update_idletasks()
        self._center_on_parent(parent)
        self.focus_set()

    def _center_on_parent(self, parent: tk.Widget) -> None:
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            w = self.winfo_width()
            h = self.winfo_height()
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
            self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        except tk.TclError:
            pass

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=10)
        outer.pack(fill="both", expand=True)

        nav = ttk.Frame(outer)
        nav.pack(fill="x", pady=(0, 8))

        ttk.Button(nav, text="◀", width=3, command=self._prev_month).pack(side="left")

        self._month_var = tk.StringVar(value=_MONTHS_DE[self._month - 1])
        self._month_combo = ttk.Combobox(
            nav, textvariable=self._month_var, values=list(_MONTHS_DE),
            state="readonly", width=12,
        )
        self._month_combo.pack(side="left", padx=(4, 4))
        self._month_combo.bind("<<ComboboxSelected>>", self._on_month_change)

        current_year = date.today().year
        self._year_var = tk.IntVar(value=self._year)
        self._year_spin = ttk.Spinbox(
            nav,
            from_=current_year - 20,
            to=current_year + 5,
            textvariable=self._year_var,
            width=6,
            command=self._on_year_change,
        )
        self._year_spin.pack(side="left", padx=(0, 4))
        self._year_spin.bind("<Return>", self._on_year_change)
        self._year_spin.bind("<FocusOut>", self._on_year_change)

        ttk.Button(nav, text="▶", width=3, command=self._next_month).pack(side="left")

        self._grid = ttk.Frame(outer)
        self._grid.pack()

        for col, name in enumerate(_WEEKDAYS_DE):
            ttk.Label(
                self._grid, text=name, style="Subtitle.TLabel",
                foreground=COLORS["text_secondary"], anchor="center", width=4,
            ).grid(row=0, column=col, padx=1, pady=(0, 4))

        bottom = ttk.Frame(outer)
        bottom.pack(fill="x", pady=(8, 0))
        ttk.Button(bottom, text="Heute", command=self._pick_today).pack(side="left")
        ttk.Button(bottom, text="Abbrechen", command=self._cancel).pack(side="right")

    def _render_calendar(self) -> None:
        for child in list(self._grid.children.values()):
            info = child.grid_info()
            if int(info.get("row", 0)) >= 1:
                child.destroy()

        # Nav-Widgets mit aktuellem Monat/Jahr synchron halten
        try:
            self._month_var.set(_MONTHS_DE[self._month - 1])
            self._year_var.set(self._year)
        except (AttributeError, tk.TclError):
            pass

        weeks = calendar.monthcalendar(self._year, self._month)
        today = date.today()

        for r, week in enumerate(weeks, start=1):
            for c, day in enumerate(week):
                if day == 0:
                    continue
                d = date(self._year, self._month, day)
                style = "TButton"
                if d == today:
                    style = "Accent.TButton"
                btn = ttk.Button(
                    self._grid, text=str(day), width=4, style=style,
                    command=lambda dd=d: self._pick(dd),
                )
                btn.grid(row=r, column=c, padx=1, pady=1)

    def _on_month_change(self, event=None) -> None:
        try:
            idx = _MONTHS_DE.index(self._month_var.get())
        except ValueError:
            return
        self._month = idx + 1
        self._render_calendar()

    def _on_year_change(self, event=None) -> None:
        try:
            year = int(self._year_var.get())
        except (tk.TclError, ValueError):
            self._year_var.set(self._year)
            return
        if year != self._year:
            self._year = year
            self._render_calendar()

    def _prev_month(self) -> None:
        if self._month == 1:
            self._month = 12
            self._year -= 1
        else:
            self._month -= 1
        self._render_calendar()

    def _next_month(self) -> None:
        if self._month == 12:
            self._month = 1
            self._year += 1
        else:
            self._month += 1
        self._render_calendar()

    def _pick_today(self) -> None:
        self._pick(date.today())

    def _pick(self, d: date) -> None:
        self.on_pick(format_date(d))
        self.destroy()

    def _cancel(self) -> None:
        self.destroy()
