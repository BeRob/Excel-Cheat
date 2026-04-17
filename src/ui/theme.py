"""Farben, Schriften und ttk-Styles (Questalpha-Branding)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


COLORS = {
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
    "border": "#E0E0E0",
    "disabled": "#BDBDBD",
}

FONTS = {
    "logo_bold": ("Segoe UI", 18, "bold"),
    "heading": ("Segoe UI", 16, "bold"),
    "subheading": ("Segoe UI", 14, "bold"),
    "body": ("Segoe UI", 11),
    "body_bold": ("Segoe UI", 11, "bold"),
    "small": ("Segoe UI", 10),
}


def apply_theme(root: tk.Tk) -> None:
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

    root.configure(background=COLORS["background"])
