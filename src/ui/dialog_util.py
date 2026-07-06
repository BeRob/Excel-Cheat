"""Gemeinsame Helfer für Toplevel-Dialoge: Zentrieren/Größe und Scrollbereich.

Vorher kochte jeder Dialog seine eigene Geometrie-Logik (`_center`,
`_fit_to_content`, `_maximize`, Info-Dialog-Arithmetik). Das führte u.a. dazu,
dass das Störungsfenster unten abgeschnitten war (Höhe hart auf Bildschirm
begrenzt, aber ohne Scrolling). Diese beiden Helfer vereinheitlichen das:

* ``place_dialog`` — misst den Inhalt, begrenzt auf die Bildschirmgröße,
  zentriert (auf das Elternfenster, sonst auf den Bildschirm) und setzt eine
  Mindestgröße, damit Buttons nie aus dem Fenster fallen.
* ``make_scrollable`` — legt einen vertikal scrollbaren Bereich an (Canvas +
  Scrollbar + Mausrad) nach dem bewährten Muster aus ``review_dialog.py`` und
  gibt den Inhaltsframe zurück.

Theme-konform (nutzt ``COLORS``), keine zusätzliche Abhängigkeit.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.ui.theme import COLORS


def place_dialog(
    win: tk.Toplevel,
    parent: tk.Widget | None = None,
    *,
    min_size: tuple[int, int] = (480, 320),
    max_margin: tuple[int, int] = (80, 100),
    resizable: tuple[bool, bool] = (True, True),
) -> None:
    """Größe an den Inhalt anpassen, auf den Bildschirm begrenzen, zentrieren.

    ``min_size`` garantiert, dass Kopf und Fußzeile (Buttons) sichtbar bleiben.
    ``max_margin`` = (horizontal, vertikal) Freiraum zum Bildschirmrand. Zentriert
    auf ``parent`` (falls sichtbar), sonst auf den Bildschirm.
    """
    win.update_idletasks()
    min_w, min_h = min_size
    mx, my = max_margin

    screen_w = win.winfo_screenwidth()
    screen_h = win.winfo_screenheight()

    req_w = max(min_w, win.winfo_reqwidth())
    req_h = max(min_h, win.winfo_reqheight())
    w = min(req_w, screen_w - mx)
    h = min(req_h, screen_h - my)

    # Zentrieren: bevorzugt über dem Elternfenster, sonst mittig auf dem Schirm.
    px = py = pw = ph = 0
    if parent is not None:
        try:
            top = parent.winfo_toplevel()
            if top.winfo_viewable():
                px, py = top.winfo_rootx(), top.winfo_rooty()
                pw, ph = top.winfo_width(), top.winfo_height()
        except tk.TclError:
            pass

    if pw > 1 and ph > 1:
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
    else:
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2 - 20

    # In den sichtbaren Bereich klemmen (nie negativ / nie rechts-unten raus).
    x = max(0, min(x, screen_w - w))
    y = max(0, min(y, screen_h - h))

    win.geometry(f"{w}x{h}+{x}+{y}")
    win.minsize(min(min_w, w), min(min_h, h))
    win.resizable(*resizable)


def make_scrollable(container: tk.Widget) -> ttk.Frame:
    """Vertikal scrollbarer Bereich in ``container``. Gibt den Inhaltsframe zurück.

    Der Aufrufer packt/gridet ``container`` selbst (mit ``expand``), legt den
    Inhalt in den zurückgegebenen Frame und braucht sich um Canvas/Scrollbar
    nicht zu kümmern. Das Mausrad scrollt, solange der Zeiger über dem Bereich
    steht.
    """
    canvas = tk.Canvas(
        container, highlightthickness=0, bg=COLORS["background"],
    )
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    inner = ttk.Frame(canvas)

    window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_inner_configure(_event: tk.Event) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _on_canvas_configure(event: tk.Event) -> None:
        # Inhaltsbreite an die Canvas-Breite koppeln → keine Horizontal-Lücke.
        canvas.itemconfigure(window_id, width=event.width)

    inner.bind("<Configure>", _on_inner_configure)
    canvas.bind("<Configure>", _on_canvas_configure)
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Mausrad nur binden, während der Zeiger über dem Bereich ist.
    def _on_wheel(event: tk.Event) -> None:
        delta = event.delta
        if delta:
            canvas.yview_scroll(int(-delta / 120) or (-1 if delta > 0 else 1), "units")

    def _bind_wheel(_event: tk.Event) -> None:
        canvas.bind_all("<MouseWheel>", _on_wheel)

    def _unbind_wheel(_event: tk.Event) -> None:
        canvas.unbind_all("<MouseWheel>")

    canvas.bind("<Enter>", _bind_wheel)
    canvas.bind("<Leave>", _unbind_wheel)

    return inner
