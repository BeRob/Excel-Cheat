"""Leichtgewichtige Hover-Tooltips (abhängigkeitsfrei, themed).

Ersetzt feste Erklärungstexte im UI durch ⓘ-Symbole mit Hover-Hinweis —
spart Platz und folgt automatisch dem Theme (Farben werden bei jeder
Anzeige neu aus ``COLORS`` gelesen, daher dark-mode-fähig)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.ui.theme import COLORS, FONTS

_SHOW_DELAY_MS = 500


class Tooltip:
    """Zeigt nach kurzer Verzögerung einen Tooltip beim Mausover über ``widget``."""

    def __init__(
        self,
        widget: tk.Widget,
        text: str,
        wraplength: int = 320,
        hide_on_press: bool = True,
    ) -> None:
        self.widget = widget
        self.text = text
        self.wraplength = wraplength
        self._tip: tk.Toplevel | None = None
        self._after_id: str | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        # hide_on_press=False, wenn ein Klick den Tooltip togglen soll (ⓘ) —
        # sonst würde ButtonPress ihn verstecken, bevor das command greift.
        if hide_on_press:
            widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None) -> None:
        self._cancel()
        self._after_id = self.widget.after(_SHOW_DELAY_MS, self._show)

    def _cancel(self) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _show(self) -> None:
        if self._tip is not None or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        except tk.TclError:
            return
        self._tip = tk.Toplevel(self.widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        # Farben bei jeder Anzeige frisch lesen → folgt Dark-Mode-Umschaltung
        frame = tk.Frame(
            self._tip,
            background=COLORS["border"],
            borderwidth=0,
        )
        frame.pack()
        label = tk.Label(
            frame,
            text=self.text,
            justify="left",
            background=COLORS["surface"],
            foreground=COLORS["text_primary"],
            font=FONTS["small"],
            wraplength=self.wraplength,
            padx=8,
            pady=5,
        )
        label.pack(padx=1, pady=1)

    def _hide(self, _event=None) -> None:
        self._cancel()
        if self._tip is not None:
            try:
                self._tip.destroy()
            except tk.TclError:
                pass
            self._tip = None

    def toggle(self, _event=None) -> None:
        """Zeigt/versteckt den Tooltip sofort — für Klick/Touch statt Hover."""
        if self._tip is not None:
            self._hide()
        else:
            self._cancel()
            self._show()

    def update_text(self, text: str) -> None:
        self.text = text


def attach_tooltip(widget: tk.Widget, text: str, wraplength: int = 320) -> Tooltip:
    """Hängt einen Tooltip an ein bestehendes Widget."""
    return Tooltip(widget, text, wraplength=wraplength)


def attach_info_icon(parent: tk.Widget, text: str, wraplength: int = 320) -> ttk.Button:
    """Erzeugt einen kleinen ⓘ-Button mit Hover-Tooltip; ein Klick togglet den
    Tooltip zusätzlich (Touch-Bedienung ohne Hover).

    Der Button selbst ist nur Auslöser (take_focus aus); der Aufrufer platziert
    ihn per ``grid``/``pack``."""
    btn = ttk.Button(parent, text="ⓘ", style="Info.TButton", takefocus=False)
    btn.state(["!focus"])
    tip = Tooltip(btn, text, wraplength=wraplength, hide_on_press=False)
    btn.configure(command=tip.toggle)
    return btn
