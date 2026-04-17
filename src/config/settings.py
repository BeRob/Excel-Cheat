"""Zentrale Pfade und Grundeinstellungen.

Pfade lassen sich ausserhalb des Codes konfigurieren (z.B. für
gemeinsame Netzlaufwerke bei Multi-Instance-Betrieb). Quelle in
dieser Prioritätsreihenfolge:

1. Umgebungsvariable ``QAINPUT_DATA_DIR`` / ``QAINPUT_OUTPUT_DIR``.
2. Bootstrap-Datei ``<APP_ROOT>/config.json`` mit optionalen Keys
   ``data_dir`` und ``output_dir`` (absolute Pfade, ``~`` erlaubt).
3. Default: ``<APP_ROOT>/data`` bzw. ``<APP_ROOT>/output``.

Die Bootstrap-Datei ist nicht das gleiche wie ``app_config.json``.
``app_config.json`` (Schichten, globale Einstellungen) liegt im
aufgelösten ``data_dir`` -- eine Konfiguration der Pfade innerhalb
dieser Datei wäre zirkulär.
"""

import json
import os
from pathlib import Path
import sys


def _get_app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


APP_ROOT = _get_app_root()


def _load_bootstrap_config() -> dict:
    path = APP_ROOT / "config.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _resolve_dir(env_var: str, config_value: object, default: Path) -> Path:
    env = os.environ.get(env_var, "").strip()
    if env:
        return Path(env).expanduser()
    if isinstance(config_value, str) and config_value.strip():
        return Path(config_value.strip()).expanduser()
    return default


_BOOTSTRAP = _load_bootstrap_config()

DATA_DIR = _resolve_dir(
    "QAINPUT_DATA_DIR", _BOOTSTRAP.get("data_dir"), APP_ROOT / "data",
)
OUTPUT_DIR = _resolve_dir(
    "QAINPUT_OUTPUT_DIR", _BOOTSTRAP.get("output_dir"), APP_ROOT / "output",
)

APP_TITLE = "QAInput - Messwerterfassung"
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 650

USERS_KV_PATH = DATA_DIR / "users.kv"
AUDIT_LOG_PATH = DATA_DIR / "audit_log.jsonl"

# Zeile 1-5: Info-Block (Produkt, Prozess, FA-Nr., Schicht, Datum)
# Zeile 6: Spaltenüberschriften, ab Zeile 7 Daten
HEADER_ROW = 6

APP_CONFIG_PATH = DATA_DIR / "app_config.json"
PRODUCTS_DIR = DATA_DIR / "products"
