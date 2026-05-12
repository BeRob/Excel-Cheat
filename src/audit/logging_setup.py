"""Zentrale Logging-Konfiguration (debug.log, error.log + Exception-Hooks).

debug.log ist das vollständige Vorgangsprotokoll, error.log enthält nur
ERROR/CRITICAL inkl. Traceback. Beide rotieren nach Größe — die GMP-
Audit-Trail-Datei (audit_log.jsonl) rotiert separat in AuditLogger
nach Datum.

Im Netz-Deployment liegen alle drei Logs im selben konfigurierten
audit_dir; das ist in src/config/settings.py via Env-Var oder
config.json einstellbar.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
import tkinter as tk
import traceback
from pathlib import Path
from typing import Callable


_FMT = logging.Formatter(
    fmt="%(asctime)s.%(msecs)03d %(levelname)-5s [%(name)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

# Auf Netzlaufwerk halten wir das Debug-Log kompakt – 5 MB × 5 Files
# reichen für rund einen Tag aktive Bedienung pro Workstation.
_DEBUG_MAX_BYTES = 5 * 1024 * 1024
_DEBUG_BACKUP_COUNT = 5
_ERROR_MAX_BYTES = 2 * 1024 * 1024
_ERROR_BACKUP_COUNT = 5


def _make_rotating_handler(
    path: Path, level: int, max_bytes: int, backups: int,
    buffered: bool = False,
) -> logging.Handler:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        filename=str(path),
        maxBytes=max_bytes,
        backupCount=backups,
        encoding="utf-8",
        delay=True,
    )
    handler.setLevel(level)
    handler.setFormatter(_FMT)
    if buffered:
        # MemoryHandler puffert bis Buffer voll oder Level >= WARNING auftritt.
        # Reduziert Schreiblast auf SMB bei häufigen DEBUG/INFO-Events.
        buffered_handler = logging.handlers.MemoryHandler(
            capacity=20,
            flushLevel=logging.WARNING,
            target=handler,
            flushOnClose=True,
        )
        buffered_handler.setLevel(level)
        return buffered_handler
    return handler


def init_logging(
    debug_log_path: Path,
    error_log_path: Path,
    on_exception: Callable[[BaseException], None] | None = None,
) -> None:
    """Initialisiert Root-Logger + Exception-Hooks. Idempotent."""
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Bei Re-Init alte Handler entfernen (z.B. in Tests)
    for h in list(root.handlers):
        if getattr(h, "_qainput_managed", False):
            root.removeHandler(h)

    debug_handler = _make_rotating_handler(
        debug_log_path, logging.DEBUG, _DEBUG_MAX_BYTES, _DEBUG_BACKUP_COUNT,
        buffered=True,
    )
    debug_handler._qainput_managed = True  # type: ignore[attr-defined]
    root.addHandler(debug_handler)

    error_handler = _make_rotating_handler(
        error_log_path, logging.ERROR, _ERROR_MAX_BYTES, _ERROR_BACKUP_COUNT,
        buffered=False,
    )
    error_handler._qainput_managed = True  # type: ignore[attr-defined]
    root.addHandler(error_handler)

    if sys.stderr is not None:
        console = logging.StreamHandler(sys.stderr)
        console.setLevel(logging.WARNING)
        console.setFormatter(_FMT)
        console._qainput_managed = True  # type: ignore[attr-defined]
        root.addHandler(console)

    def _uncaught(exc_type, exc_value, exc_tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logging.getLogger("uncaught").critical(
            "Unbehandelte Exception",
            exc_info=(exc_type, exc_value, exc_tb),
        )
        if on_exception is not None:
            try:
                on_exception(exc_value)
            except Exception:
                pass

    sys.excepthook = _uncaught

    # Tk-Callback-Exceptions landen sonst still in stderr.
    def _tk_report(self, exc, val, tb) -> None:
        logging.getLogger("tk").error(
            "Tk-Callback-Exception",
            exc_info=(exc, val, tb),
        )
        if on_exception is not None:
            try:
                on_exception(val)
            except Exception:
                pass

    tk.Tk.report_callback_exception = _tk_report


def shutdown_logging() -> None:
    """Flusht alle Handler. Aufrufen vor App-Exit."""
    logging.shutdown()
