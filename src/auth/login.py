"""Anmeldung per Passwort oder QR-Code."""

from __future__ import annotations

from pathlib import Path

from src.auth.users_kv import parse_users_kv
from src.domain.state import UserInfo


class AuthService:
    def __init__(self, users_kv_path: str | Path, qr_prefix: str = "") -> None:
        self.users = parse_users_kv(users_kv_path)
        self.qr_prefix = qr_prefix

    def login_password(self, username: str, password: str) -> UserInfo | None:
        user_data = self.users.get(username)
        if user_data is None:
            return None
        if user_data.get("password", "") != password:
            return None
        return self._make_user_info(username, user_data)

    def login_qr(self, scanned_text: str) -> UserInfo | None:
        """Matcht einen gescannten Code gegen die Benutzerdatenbank.

        Entfernt ggf. den konfigurierten Prefix (z.B. "WF2 "), den manche
        Handscanner voranstellen.
        """
        scanned_text = scanned_text.strip()
        if self.qr_prefix and scanned_text.startswith(self.qr_prefix):
            scanned_text = scanned_text[len(self.qr_prefix):]

        for user_id, user_data in self.users.items():
            if user_data.get("qr", "") == scanned_text:
                return self._make_user_info(user_id, user_data)
        return None

    def _make_user_info(self, user_id: str, user_data: dict[str, str]) -> UserInfo:
        display_name = user_data.get("name", user_id)
        is_admin = user_data.get("admin", "false").lower() == "true"
        return UserInfo(user_id=user_id, display_name=display_name, is_admin=is_admin)
