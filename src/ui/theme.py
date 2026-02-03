"""Zentrales Theming: Farben, Schriften und ttk-Styles."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


COLORS = {
    "primary": "#1A1A1A",
    "background": "#FFFFFF",
    "surface": "#FFFFFF",  # Gleiche Farbe wie background für einheitliches Aussehen
    "accent": "#0077B6",
    "accent_hover": "#005F8A",
    "accent_light": "#E0F0FA",
    "text_primary": "#1A1A1A",
    "text_secondary": "#555555",
    "text_on_primary": "#FFFFFF",
    "success": "#2E7D32",
    "warning": "#CC8800",
    "error": "#C62828",
    "border": "#CCCCCC",
    "disabled": "#AAAAAA",
}

FONTS = {
    "heading": ("Segoe UI", 16, "bold"),
    "subheading": ("Segoe UI", 14, "bold"),
    "body": ("Segoe UI", 10),
    "body_bold": ("Segoe UI", 10, "bold"),
    "small": ("Segoe UI", 9),
}


def apply_theme(root: tk.Tk) -> None:
    """Konfiguriert ttk.Style mit dem Anwendungsthema."""
    style = ttk.Style(root)
    style.theme_use("clam")

    # --- Standard-Hintergrund ---
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
        fieldbackground=COLORS["background"],
        foreground=COLORS["text_primary"],
        font=FONTS["body"],
    )
    style.configure(
        "TButton",
        font=FONTS["body"],
        padding=(10, 4),
    )
    style.configure(
        "TNotebook",
        background=COLORS["background"],
    )
    style.configure(
        "TNotebook.Tab",
        font=FONTS["body"],
        padding=(12, 4),
        background=COLORS["background"],
    )
    style.configure(
        "TLabelframe",
        background=COLORS["background"],
        foreground=COLORS["text_primary"],
        font=FONTS["body_bold"],
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
    )

    # --- Title ---
    style.configure(
        "Title.TLabel",
        font=FONTS["heading"],
        foreground=COLORS["text_primary"],
        background=COLORS["background"],
    )

    # --- Subtitle ---
    style.configure(
        "Subtitle.TLabel",
        font=FONTS["subheading"],
        foreground=COLORS["text_primary"],
        background=COLORS["background"],
    )

    # --- Accent Button ---
    style.configure(
        "Accent.TButton",
        background=COLORS["accent"],
        foreground=COLORS["text_on_primary"],
        font=FONTS["body_bold"],
        padding=(14, 6),
    )
    style.map(
        "Accent.TButton",
        background=[
            ("active", COLORS["accent_hover"]),
            ("disabled", COLORS["disabled"]),
        ],
        foreground=[
            ("disabled", COLORS["background"]),
        ],
    )

    # --- Success / Error / Warning labels ---
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

    # --- Header bar ---
    style.configure(
        "Header.TFrame",
        background=COLORS["primary"],
    )
    style.configure(
        "Header.TLabel",
        background=COLORS["primary"],
        foreground=COLORS["text_on_primary"],
        font=FONTS["body_bold"],
    )

    root.configure(background=COLORS["background"])
