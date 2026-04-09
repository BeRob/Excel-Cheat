"""Zentrale Anwendungskonfiguration."""

from pathlib import Path
import sys


def _get_app_root() -> Path:
    """Ermittelt das Projektverzeichnis."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).resolve().parent.parent.parent

APP_ROOT = _get_app_root()

APP_TITLE = "QAInput"
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 650

USERS_KV_PATH = APP_ROOT / "data" / "users.kv"
AUDIT_LOG_PATH = APP_ROOT / "data" / "audit_log.jsonl"

INFO_HEADER_ROWS = 5   # Rows 1-5: product/process/FA info block
HEADER_ROW = 6          # Row 6: column headers (after info block)
AUTO_COLUMNS = ["Datum", "Bearbeiter"]

APP_CONFIG_PATH = APP_ROOT / "data" / "app_config.json"
PRODUCTS_DIR = APP_ROOT / "data" / "products"
OUTPUT_DIR = APP_ROOT / "output"
