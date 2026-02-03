"""Zentrales Theming: Farben, Schriften und ttk-Styles."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


COLORS = {
    "primary": "#1C1C1C",       # Very dark grey, almost black
    "background": "#FFFFFF",    # Pure white
    "surface": "#F8F9FA",       # Very light grey for slight contrast
    "accent": "#0066CC",        # Medical/Professional Blue
    "accent_hover": "#0052A3",
    "accent_light": "#E3F2FD",
    "text_primary": "#1C1C1C",
    "text_secondary": "#555555",
    "text_on_primary": "#FFFFFF",
    "success": "#2E7D32",
    "warning": "#ED6C02",
    "error": "#D32F2F",
    "border": "#E0E0E0",
    "disabled": "#BDBDBD",
}

FONTS = {
    "logo_bold": ("Segoe UI", 18, "bold"),
    "logo_light": ("Segoe UI", 18, "normal"),
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
        fieldbackground=COLORS["surface"],
        foreground=COLORS["text_primary"],
        font=FONTS["body"],
        borderwidth=1,
        relief="solid",
        bordercolor=COLORS["border"],
    )
    style.configure(
        "TButton",
        font=FONTS["body"],
        padding=(10, 4),
        background=COLORS["surface"],
        foreground=COLORS["text_primary"],
        borderwidth=1,
        bordercolor=COLORS["border"],
    )
    style.map(
        "TButton",
        background=[("active", COLORS["border"])],
    )

    style.configure(
        "TNotebook",
        background=COLORS["background"],
        tabmargins=[2, 5, 2, 0],
    )
    style.configure(
        "TNotebook.Tab",
        font=FONTS["body"],
        padding=(12, 6),
        background=COLORS["surface"],
        foreground=COLORS["text_secondary"],
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", COLORS["background"])],
        foreground=[("selected", COLORS["accent"])],
        expand=[("selected", [1, 1, 1, 0])],
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
        padding=(14, 8),
        borderwidth=0,
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

    # --- Header bar (Clean White) ---
    style.configure(
        "Header.TFrame",
        background=COLORS["background"],
    )
    # Styles for the split logo
    style.configure(
        "LogoBold.TLabel",
        background=COLORS["background"],
        foreground=COLORS["text_primary"],
        font=FONTS["logo_bold"],
    )
    style.configure(
        "LogoLight.TLabel",
        background=COLORS["background"],
        foreground=COLORS["text_primary"],
        font=FONTS["logo_light"],
    )
    style.configure(
        "HeaderInfo.TLabel",
        background=COLORS["background"],
        foreground=COLORS["text_secondary"],
        font=FONTS["body"],
    )

    root.configure(background=COLORS["background"])
