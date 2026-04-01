"""Zentraler Anwendungszustand."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.audit.audit_logger import AuditLogger
    from src.config.process_config import AppConfig, ProductConfig, ProcessConfig


@dataclass
class UserInfo:
    user_id: str
    display_name: str
    is_admin: bool = False


class AppState:
    """Zentraler Zustand der Anwendung, wird an alle Views ubergeben."""

    def __init__(self) -> None:
        self.current_user: UserInfo | None = None
        self.app_config: AppConfig | None = None

        # Auswahl
        self.selected_product: ProductConfig | None = None
        self.selected_process: ProcessConfig | None = None
        self.current_shift: str | None = None

        # Datei
        self.current_file: Path | None = None

        # Felder (aus Config abgeleitet)
        self.current_headers: list[str] = []
        self.persistent_headers: list[str] = []
        self.measurement_headers: list[str] = []
        self.persistent_values: dict[str, str] = {}

        # Zaehler
        self.row_group_counter: int = 0
        self.auto_sequence: int = 0

        # Sonstiges
        self.audit: AuditLogger | None = None
        self.layout_mode: str = "vertical"

    def reset_user(self) -> None:
        """Setzt Benutzer und alle abhaengigen Daten zurueck."""
        self.current_user = None
        self.reset_product()

    def reset_product(self) -> None:
        """Setzt Produktauswahl und alles Abhaengige zurueck."""
        self.selected_product = None
        self.reset_process()

    def reset_process(self) -> None:
        """Setzt Prozessauswahl, Datei und Zaehler zurueck."""
        self.selected_process = None
        self.current_shift = None
        self.current_file = None
        self.current_headers = []
        self.persistent_headers = []
        self.measurement_headers = []
        self.row_group_counter = 0
        self.auto_sequence = 0
        self.reset_context()

    def reset_context(self) -> None:
        """Setzt nur den Kontext zurueck."""
        self.persistent_values = {}
