"""Zentrale Pfade und Grundeinstellungen.

Pfade lassen sich ausserhalb des Codes konfigurieren. Quelle in
dieser Prioritätsreihenfolge:

1. Umgebungsvariable (z.B. QAINPUT_DATA_DIR als Fallback).
2. Bootstrap-Datei <APP_ROOT>/config.json mit optionalen Keys
   users_dir, config_dir, products_dir, process_templates_dir,
   audit_dir, downtime_dir, log_dir, vorlagen_dir,
   freigabedokumente_dir, ui_prefs_dir (absolute Pfade, ~ erlaubt).
   Malformed JSON wird ignoriert.
3. Default: Unterordner von <APP_ROOT>/data (Entwicklungsstand).

Die Bootstrap-Datei ist nicht das gleiche wie app_config.json.
app_config.json (Schichten, globale Einstellungen) liegt im
aufgelösten config_dir -- eine Konfiguration der Pfade innerhalb
dieser Datei wäre zirkulär.

audit_dir   → audit_log.jsonl (GMP-Trail, Tagesrotation)
log_dir     → debug.log + error.log (technische Logs, Größen-Rotation)
Audit und Logs sind absichtlich getrennt — GMP-Trail darf zentral
liegen, Debug/Error können in einen separaten Ordner.
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


def _local_base() -> Path:
    """Stations-lokaler Basisordner für Dateien, die NICHT ins Netz gehören
    (z.B. UI-Präferenzen). Analog zum Audit-Fallback: %LOCALAPPDATA% unter
    Windows, sonst ~/.cache."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("TEMP") or "."
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return Path(base) / "QAInput"


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
# Prozess-Templates (kanonische Feldstruktur je Operation). Default: <DATA_DIR>/process_templates
PROCESS_TEMPLATES_DIR = _resolve_dir(
    "QAINPUT_PROCESS_TEMPLATES_DIR",
    _BOOTSTRAP.get("process_templates_dir"),
    DATA_DIR / "process_templates",
)
AUDIT_DIR = _resolve_dir(
    "QAINPUT_AUDIT_DIR", _BOOTSTRAP.get("audit_dir"), DATA_DIR,
)
# Störungs-/Stillstands-Store (GMP-Record, daher Default neben dem Audit-Trail).
DOWNTIME_DIR = _resolve_dir(
    "QAINPUT_DOWNTIME_DIR", _BOOTSTRAP.get("downtime_dir"), AUDIT_DIR,
)
# Logs (debug.log, error.log) liegen getrennt vom GMP-Audit-Trail.
# Default: <DATA_DIR>/logs/ — also Sibling zum Audit, nicht im selben Ordner.
LOG_DIR = _resolve_dir(
    "QAINPUT_LOG_DIR", _BOOTSTRAP.get("log_dir"), DATA_DIR / "logs",
)
# Word-Vorlagen (freigabedokument.docx) — read-only, gehören zur Konfiguration.
VORLAGEN_DIR = _resolve_dir(
    "QAINPUT_VORLAGEN_DIR", _BOOTSTRAP.get("vorlagen_dir"), DATA_DIR / "vorlagen",
)
# Generierte Freigabedokumente (schreibbar) — eigener Ordner, damit sie nicht
# beim read-only-Config-Ordner bzw. neben der Exe landen.
FREIGABEDOKUMENTE_DIR = _resolve_dir(
    "QAINPUT_FREIGABEDOKUMENTE_DIR", _BOOTSTRAP.get("freigabedokumente_dir"),
    DATA_DIR / "freigabedokumente",
)
# UI-Präferenzen sind pro Station lokal (werden zur Laufzeit geschrieben und
# gehören nicht in den zentralen read-only-Config-Ordner). Override möglich.
UI_PREFS_DIR = _resolve_dir(
    "QAINPUT_UI_PREFS_DIR", _BOOTSTRAP.get("ui_prefs_dir"), _local_base(),
)

from src.version import APP_VERSION  # noqa: F401  re-export

APP_TITLE = "QAInput - Messwerterfassung"
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 650

USERS_KV_PATH = USERS_DIR / "users.kv"
AUDIT_LOG_PATH = AUDIT_DIR / "audit_log.jsonl"
DEBUG_LOG_PATH = LOG_DIR / "debug.log"
ERROR_LOG_PATH = LOG_DIR / "error.log"

UI_PREFS_PATH = UI_PREFS_DIR / "ui_prefs.json"

# Störungs-Store (append-only JSONL) + zweistufige Fehler-Code-Liste.
DOWNTIME_LOG_PATH = DOWNTIME_DIR / "stoerungen.jsonl"
STOERUNGS_CODES_PATH = CONFIG_DIR / "stoerungs_codes.json"

# Word-Vorlage für Freigabedokumente (vom QM gepflegt, mit {{...}}-Platzhaltern).
# Fehlt sie, fällt die Erzeugung auf ein festes HTML-Layout zurück.
FREIGABE_VORLAGE_PATH = VORLAGEN_DIR / "freigabedokument.docx"


def load_ui_prefs() -> dict:
    """Lädt UI-Einstellungen (Spaltenauswahl Historie, etc.). Fehler → leeres Dict."""
    import logging

    try:
        if UI_PREFS_PATH.exists():
            data = json.loads(UI_PREFS_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception as e:
        logging.getLogger("config").warning(
            "ui_prefs.json nicht lesbar (%s) — verwende Defaults", e
        )
    return {}


def save_ui_prefs(prefs: dict) -> None:
    """Speichert UI-Einstellungen. Fehler kosten nur die Präferenzen (best-effort),
    landen aber im debug.log statt unterzugehen."""
    import logging

    try:
        UI_PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
        UI_PREFS_PATH.write_text(
            json.dumps(prefs, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logging.getLogger("config").warning("ui_prefs.json nicht speicherbar: %s", e)

# Zeile 1: nur Produktname (groß, fett)
# Zeilen 2-5 (Spalten A-B): Prozess, Schicht, Datum
# Zeilen 2-8 (Spalten C-D): dynamische Info-Felder (FA-Nr., LOT, ...)
# Zeile 9: Spaltenüberschriften, ab Zeile 10 Daten
HEADER_ROW = 9

APP_CONFIG_PATH = CONFIG_DIR / "app_config.json"


def load_app_config_raw() -> dict:
    """Liest app_config.json als rohes Dict.

    Für Werte, die schon beim Start gebraucht werden — bevor der
    AppConfig-Dataclass existiert (Logging-Rotation, Audit-Lock-Timeout).
    Fehlende/fehlerhafte Datei → leeres Dict, Aufrufer nutzen ihre Defaults.
    """
    try:
        if APP_CONFIG_PATH.exists():
            data = json.loads(APP_CONFIG_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}
