"""Parser für die Benutzerliste im key=value Format."""

from __future__ import annotations

from pathlib import Path


def parse_users_kv(filepath: str | Path) -> dict[str, dict[str, str]]:
    """Liest Zeilen der Form `user.<id>.<property>=<value>`.

    Ergebnis: {"robert": {"password": "1234", "qr": "11111", "name": "Robert Benner"}}
    Leere Zeilen und Kommentare (#) werden ignoriert.
    """
    users: dict[str, dict[str, str]] = {}
    path = Path(filepath)

    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            parts = key.strip().split(".")
            if len(parts) != 3 or parts[0] != "user":
                continue

            _, user_id, prop = parts
            users.setdefault(user_id, {})[prop] = value.strip()

    return users
