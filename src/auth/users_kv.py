"""Parser für die Benutzerliste im key=value Format."""

from __future__ import annotations

import logging
from pathlib import Path


_logger = logging.getLogger("auth")


def parse_users_kv(filepath: str | Path) -> dict[str, dict[str, str]]:
    """Liest Zeilen der Form `user.<id>.<property>=<value>`.

    Ergebnis: {"robert": {"password": "1234", "qr": "11111", "name": "Robert Benner"}}
    Leere Zeilen und Kommentare (#) werden ignoriert; nicht parsbare Zeilen
    werden übersprungen und im Tech-Log vermerkt (ein Tippfehler darf keinen
    Benutzer stillschweigend verschwinden lassen).
    """
    users: dict[str, dict[str, str]] = {}
    path = Path(filepath)

    with open(path, encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, 1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                _logger.warning(
                    "users.kv Zeile %d übersprungen (kein '='): %r", line_no, line
                )
                continue

            key, value = line.split("=", 1)
            parts = key.strip().split(".")
            if len(parts) != 3 or parts[0] != "user":
                _logger.warning(
                    "users.kv Zeile %d übersprungen (erwartet "
                    "user.<id>.<property>): %r", line_no, line
                )
                continue

            _, user_id, prop = parts
            users.setdefault(user_id, {})[prop] = value.strip()

    return users
