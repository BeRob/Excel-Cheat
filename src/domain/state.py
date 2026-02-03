"""Zentraler Anwendungszustand."""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.audit.audit_logger import AuditLogger


@dataclass
class UserInfo:
    user_id: str
    display_name: str


@dataclass
class ContextInfo:
    charge: str
    fa: str
    rolle: str


class AppState:
    """Zentraler Zustand der Anwendung, wird an alle Views übergeben."""

    def __init__(self) -> None:
        self.current_user: UserInfo | None = None
        self.current_file: Path | None = None
        self.current_sheet: str | None = None
        self.current_context: ContextInfo | None = None
        self.current_headers: list[str] = []
        self.measurement_headers: list[str] = []
        self.header_column_map: dict[str, int] = {}
        self.audit: AuditLogger | None = None

    def reset_user(self) -> None:
        """Setzt Benutzer und alle abhängigen Daten zurück."""
        self.current_user = None
        self.reset_file()

    def reset_file(self) -> None:
        """Setzt Datei, Kontext und Header zurück."""
        self.current_file = None
        self.current_sheet = None
        self.current_headers = []
        self.measurement_headers = []
        self.header_column_map = {}
        self.reset_context()

    def reset_context(self) -> None:
        """Setzt nur den Kontext zurück."""
        self.current_context = None
