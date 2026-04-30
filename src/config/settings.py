"""Zentrale Pfade und Grundeinstellungen.

Pfade lassen sich ausserhalb des Codes konfigurieren. Quelle in
dieser Prioritätsreihenfolge:

1. Umgebungsvariable (z.B. QAINPUT_DATA_DIR als Fallback).
2. Bootstrap-Datei <APP_ROOT>/config.json mit optionalen Keys
   users_dir, config_dir, products_dir, audit_dir
   (absolute Pfade, ~ erlaubt). Malformed JSON wird ignoriert.
3. Default: Unterordner von <APP_ROOT>/data (Entwicklungsstand).

Die Bootstrap-Datei ist nicht das gleiche wie app_config.json.
app_config.json (Schichten, globale Einstellungen) liegt im
aufgelösten config_dir -- eine Konfiguration der Pfade innerhalb
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

# Fallback-Basis wenn keine spezifischen Dirs konfiguriert sind (Entwicklung)
DATA_DIR = _resolve_dir(
    "QAINPUT_DATA_DIR", _BOOTSTRAP.get("data_dir"), APP_ROOT / "data",
)

USERS_DIR = _resolve_dir(
    "QAINPUT_USERS_DIR", _BOOTSTRAP.get("users_dir"), DATA_DIR,
)
CONFIG_DIR = _resolve_dir(
    "QAINPUT_CONFIG_DIR", _BOOTSTRAP.get("config_dir"), DATA_DIR,
)
PRODUCTS_DIR = _resolve_dir(
    "QAINPUT_PRODUCTS_DIR", _BOOTSTRAP.get("products_dir"), DATA_DIR / "products",
)
AUDIT_DIR = _resolve_dir(
    "QAINPUT_AUDIT_DIR", _BOOTSTRAP.get("audit_dir"), DATA_DIR,
)

APP_TITLE = "QAInput - Messwerterfassung"
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 650

USERS_KV_PATH = USERS_DIR / "users.kv"
AUDIT_LOG_PATH = AUDIT_DIR / "audit_log.jsonl"

# Zeile 1: nur Produktname (groß, fett)
# Zeilen 2-5 (Spalten A-B): Prozess, Schicht, Datum
# Zeilen 2-8 (Spalten C-D): dynamische Info-Felder (FA-Nr., LOT, ...)
# Zeile 9: Spaltenüberschriften, ab Zeile 10 Daten
HEADER_ROW = 9

APP_CONFIG_PATH = CONFIG_DIR / "app_config.json"
