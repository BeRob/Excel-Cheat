"""Parser für die Benutzerliste im key=value Format."""

from __future__ import annotations

from pathlib import Path


def parse_users_kv(filepath: str | Path) -> dict[str, dict[str, str]]:
    """Parst eine KV-Datei mit Zeilen wie user.<id>.<property>=<value>.

    Returns:
        Dict mit user_id als Schlüssel und Property-Dict als Wert.
        Beispiel: {"robert": {"password": "1234", "qr": "11111", "name": "Robert Benner"}}
    """
    users: dict[str, dict[str, str]] = {}
    path = Path(filepath)

    with open(path, encoding="utf-8") as f:
        for line_num, raw_line in enumerate(f, 1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            parts = key.split(".")
            if len(parts) != 3 or parts[0] != "user":
                continue

            _, user_id, prop = parts
            if user_id not in users:
                users[user_id] = {}
            users[user_id][prop] = value

    return users
