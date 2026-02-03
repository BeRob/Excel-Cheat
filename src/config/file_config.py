"""Per-file Spaltenkonfiguration als JSON-Sidecar."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.config.settings import CONFIG_DIR


def config_path_for(excel_path: str | Path) -> Path:
    """Gibt den Pfad zur Konfigurationsdatei fuer eine Excel-Datei zurueck.

    Format: data/configs/<name>_<hash>.json
    """
    p = Path(excel_path).resolve()
    name = p.stem
    path_hash = hashlib.md5(str(p).encode()).hexdigest()[:8]
    return CONFIG_DIR / f"{name}_{path_hash}.json"


def save_column_config(
    excel_path: str | Path,
    sheet_name: str,
    persistent_headers: list[str],
    measurement_headers: list[str],
) -> None:
    """Speichert die Spaltenzuordnung als JSON."""
    cfg_path = config_path_for(excel_path)
    p = Path(excel_path)

    # Bestehende Config laden falls vorhanden
    data: dict = {}
    if cfg_path.exists():
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}

    data["file"] = p.name
    sheets = data.get("sheets", {})
    sheets[sheet_name] = {
        "persistent": list(persistent_headers),
        "measurement": list(measurement_headers),
    }
    data["sheets"] = sheets

    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_column_config(
    excel_path: str | Path,
    sheet_name: str,
) -> dict | None:
    """Laedt die Spaltenzuordnung fuer ein bestimmtes Sheet.

    Returns:
        Dict mit 'persistent' und 'measurement' Listen, oder None.
    """
    cfg_path = config_path_for(excel_path)
    if not cfg_path.exists():
        return None

    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    sheets = data.get("sheets", {})
    return sheets.get(sheet_name)
