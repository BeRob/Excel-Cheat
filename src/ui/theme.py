"""Farben, Schriften und ttk-Styles (Questalpha-Branding)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont


_LIGHT_COLORS: dict[str, str] = {
    "primary": "#1B2023",
    "background": "#FFFFFF",
    "surface": "#E8ECF0",
    "accent": "#0070BB",
    "accent_hover": "#005A96",
    "accent_light": "#E3F2FD",
    "text_primary": "#1B2023",
    "text_secondary": "#555555",
    "text_on_primary": "#FFFFFF",
    "success": "#2E7D32",
    "warning": "#ED6C02",
    "error": "#D32F2F",
    "border": "#C0C0C0",
    "disabled": "#BDBDBD",
}

_DARK_COLORS: dict[str, str] = {
    "primary": "#E8ECF0",
    "background": "#1E1E1E",
    "surface": "#2D2D2D",
    "accent": "#4FC3F7",
    "accent_hover": "#81D4FA",
    "accent_light": "#1A2A3A",
    "text_primary": "#E8ECF0",
    "text_secondary": "#AAAAAA",
    "text_on_primary": "#1E1E1E",
    "success": "#66BB6A",
    "warning": "#FFA726",
    "error": "#EF5350",
    "border": "#555555",
    "disabled": "#666666",
}

COLORS: dict[str, str] = dict(_LIGHT_COLORS)

# Tupel-Fallback bis apply_theme() aufgerufen wurde
FONTS: dict[str, object] = {
    "logo_bold": ("Segoe UI", 18, "bold"),
    "heading": ("Segoe UI", 16, "bold"),
    "subheading": ("Segoe UI", 14, "bold"),
    "body": ("Segoe UI", 11),
    "body_bold": ("Segoe UI", 11, "bold"),
    "small": ("Segoe UI", 10),
}

_BASE_SIZES: dict[str, int] = {
    "logo_bold": 18,
    "heading": 16,
    "subheading": 14,
    "body": 11,
    "body_bold": 11,
    "small": 10,
}

_FONT_WEIGHTS: dict[str, str] = {
    "logo_bold": "bold",
    "heading": "bold",
    "subheading": "bold",
    "body": "normal",
    "body_bold": "bold",
    "small": "normal",
}

_font_objects: dict[str, tkfont.Font] = {}
_dark_mode: bool = False
_MIN_SCALE = -2
_MAX_SCALE = 5


def _init_fonts(scale: int = 0) -> None:
    """Erstellt oder aktualisiert tkfont.Font-Objekte."""
    for name, base in _BASE_SIZES.items():
        size = base + scale
        weight = _FONT_WEIGHTS[name]
        if name in _font_objects:
            _font_objects[name].configure(size=size)
        else:
            _font_objects[name] = tkfont.Font(family="Segoe UI", size=size, weight=weight)
        FONTS[name] = _font_objects[name]


def scale_fonts(delta: int, current_scale: int) -> int:
    """Ändert alle Schriftgrößen relativ zum Basiswert. Gibt neue Scale zurück."""
    new_scale = max(_MIN_SCALE, min(_MAX_SCALE, current_scale + delta))
    for name, base in _BASE_SIZES.items():
        if name in _font_objects:
            _font_objects[name].configure(size=base + new_scale)
    return new_scale


def is_dark_mode() -> bool:
    return _dark_mode


def toggle_dark_mode(root: tk.Tk) -> bool:
    """Schaltet zwischen Hell und Dunkel um. Gibt True zurück wenn jetzt dunkel."""
    global _dark_mode
    _dark_mode = not _dark_mode
    COLORS.update(_DARK_COLORS if _dark_mode else _LIGHT_COLORS)
    apply_theme(root)
    return _dark_mode


def update_tk_backgrounds(widget: tk.Widget, old_bg: str, new_bg: str) -> None:
    """Aktualisiert rekursiv alle tk-Widgets mit explizitem bg=old_bg."""
    try:
        if widget.cget("bg") == old_bg:
            widget.configure(bg=new_bg)
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        update_tk_backgrounds(child, old_bg, new_bg)


def apply_theme(root: tk.Tk, scale: int = 0) -> None:
    _init_fonts(scale)

    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=COLORS["background"], font=FONTS["body"])
    style.configure("TFrame", background=COLORS["background"])
    style.configure(
        "TLabel",
        background=COLORS["background"],
        foreground=COLORS["text_primary"],
        font=FONTS["body"],
    )
    style.configure(
        "TEntry",
        fieldbackground=COLORS["surface"],
        foreground=COLORS["text_primary"],
        font=FONTS["body"],
        borderwidth=1,
        relief="solid",
        bordercolor=COLORS["border"],
    )
    style.map(
        "TEntry",
        fieldbackground=[
            ("disabled", COLORS["disabled"]),
            ("readonly", COLORS["surface"]),
            ("!disabled", COLORS["surface"]),
        ],
    )
    style.configure(
        "TButton",
        font=FONTS["body_bold"],
        padding=(12, 6),
        background=COLORS["surface"],
        foreground=COLORS["text_primary"],
        borderwidth=1,
        relief="solid",
        bordercolor=COLORS["border"],
    )
    style.map(
        "TButton",
        background=[("active", COLORS["border"]), ("disabled", COLORS["disabled"])],
        foreground=[("disabled", COLORS["text_secondary"])],
    )

    style.configure(
        "Accent.TButton",
        background=COLORS["accent"],
        foreground=COLORS["text_on_primary"],
        font=FONTS["body_bold"],
        padding=(16, 10),
        borderwidth=1,
        relief="solid",
        bordercolor=COLORS["accent_hover"],
    )
    style.map(
        "Accent.TButton",
        background=[
            ("active", COLORS["accent_hover"]),
            ("disabled", COLORS["disabled"]),
        ],
        foreground=[("disabled", COLORS["background"])],
    )

    style.configure(
        "Manual.TButton",
        background=COLORS["surface"],
        foreground=COLORS["accent"],
        font=FONTS["body_bold"],
        padding=(5, 5),
        borderwidth=1,
        bordercolor=COLORS["accent"],
    )
    style.map(
        "Manual.TButton",
        background=[("active", COLORS["accent_light"])],
    )

    style.configure(
        "TNotebook",
        background=COLORS["background"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["background"],
        darkcolor=COLORS["background"],
        tabmargins=[2, 5, 2, 0],
    )
    style.configure(
        "TNotebook.Tab",
        font=FONTS["body"],
        padding=(12, 6),
        background=COLORS["surface"],
        foreground=COLORS["text_secondary"],
        borderwidth=1,
        bordercolor=COLORS["border"],
        lightcolor=COLORS["background"],
        darkcolor=COLORS["background"],
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", COLORS["background"])],
        foreground=[("selected", COLORS["accent"])],
        expand=[("selected", [1, 1, 1, 0])],
        lightcolor=[("selected", COLORS["background"])],
        darkcolor=[("selected", COLORS["background"])],
    )

    style.configure(
        "TLabelframe",
        background=COLORS["background"],
        foreground=COLORS["text_primary"],
        font=FONTS["body_bold"],
        borderwidth=1,
        relief="solid",
        bordercolor=COLORS["border"],
    )
    style.configure(
        "TLabelframe.Label",
        background=COLORS["background"],
        foreground=COLORS["text_primary"],
        font=FONTS["body_bold"],
    )
    style.configure(
        "TCombobox",
        font=FONTS["body"],
        fieldbackground=COLORS["surface"],
        background=COLORS["surface"],
    )
    style.map(
        "TCombobox",
        fieldbackground=[
            ("disabled", COLORS["disabled"]),
            ("readonly", COLORS["surface"]),
            ("!disabled", COLORS["surface"]),
        ],
    )

    style.configure(
        "Title.TLabel",
        font=FONTS["heading"],
        foreground=COLORS["text_primary"],
        background=COLORS["background"],
    )
    style.configure(
        "Subtitle.TLabel",
        font=FONTS["subheading"],
        foreground=COLORS["text_primary"],
        background=COLORS["background"],
    )

    style.configure(
        "Success.TLabel",
        foreground=COLORS["success"],
        background=COLORS["background"],
        font=FONTS["body"],
    )
    style.configure(
        "Error.TLabel",
        foreground=COLORS["error"],
        background=COLORS["background"],
        font=FONTS["body"],
    )
    style.configure(
        "Warning.TLabel",
        foreground=COLORS["warning"],
        background=COLORS["background"],
        font=FONTS["body"],
    )

    style.configure("Header.TFrame", background=COLORS["background"])
    style.configure(
        "LogoBold.TLabel",
        background=COLORS["background"],
        foreground=COLORS["text_primary"],
        font=FONTS["logo_bold"],
    )
    style.configure(
        "HeaderInfo.TLabel",
        background=COLORS["background"],
        foreground=COLORS["text_secondary"],
        font=FONTS["body"],
    )

    style.configure(
        "Treeview",
        background=COLORS["surface"],
        foreground=COLORS["text_primary"],
        fieldbackground=COLORS["surface"],
        font=FONTS["body"],
        rowheight=28,
    )
    style.configure(
        "Treeview.Heading",
        background=COLORS["background"],
        foreground=COLORS["text_primary"],
        font=FONTS["body_bold"],
    )
    style.map(
        "Treeview",
        background=[("selected", COLORS["accent"])],
        foreground=[("selected", COLORS["text_on_primary"])],
    )

    style.configure(
        "TScrollbar",
        background=COLORS["surface"],
        troughcolor=COLORS["background"],
        bordercolor=COLORS["border"],
        arrowcolor=COLORS["text_secondary"],
    )

    root.configure(background=COLORS["background"])
