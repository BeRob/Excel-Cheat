"""Zentraler Anwendungszustand, geteilt von allen Views."""

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
    """Zustand wird an alle Views durchgereicht."""

    def __init__(self) -> None:
        self.current_user: UserInfo | None = None
        self.app_config: AppConfig | None = None

        self.selected_product: ProductConfig | None = None
        self.selected_process: ProcessConfig | None = None
        self.current_shift: str | None = None

        self.current_file: Path | None = None

        self.current_headers: list[str] = []
        self.persistent_headers: list[str] = []
        self.measurement_headers: list[str] = []
        self.persistent_values: dict[str, str] = {}

        self.row_group_counter: int = 0
        self.auto_sequence: int = 0

        self.audit: AuditLogger | None = None
        self.layout_mode: str = "vertical"

    def reset_user(self) -> None:
        self.current_user = None
        self.reset_product()

    def reset_product(self) -> None:
        self.selected_product = None
        self.reset_process()

    def reset_process(self) -> None:
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
        self.persistent_values = {}
