"""Append-only JSONL-Store für Störungs-/Stillstandsereignisse.

System-of-Record der Störungserfassung — getrennt vom Audit-Log, aber nach dem
gleichen gehärteten Muster (``src/audit/audit_logger.py``): Inter-Prozess-Lock
für gleichzeitige Workstations auf demselben SMB-Share, lokaler Fallback bei
Netzaussetzern mit Replay beim nächsten erfolgreichen Schreiben — es geht kein
Ereignis verloren.

Anders als das Audit-Log wird hier **nicht** täglich rotiert: das Störungs-
volumen ist gering und Auswertungen (z.B. „letzte 2 Wochen", „dieser Monat")
brauchen die gesamte Historie in einer Datei. So liest ``read_all`` genau eine
Datei statt über rotierte Archive zu mischen.

Zwei Zeilen-Typen, gepaart über ``id``:
- ``{"kind": "stoerung_start", "id", "ts_start", ...}``  bei der Erfassung
- ``{"kind": "stoerung_ende",  "id", "ts_ende", ...}``   bei der Freigabe
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from src.audit.file_lock import acquire_lock, release_lock

_LOCK_TIMEOUT_SECONDS = 5.0
_logger = logging.getLogger("downtime")


def _local_fallback_path() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("TEMP") or "."
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return Path(base) / "QAInput" / "stoerungen_local_fallback.jsonl"


class DowntimeStore:
    """Schreibt/liest Störungs-Ereignisse als JSON-Zeilen."""

    def __init__(
        self, log_path: str | Path, *,
        lock_timeout: float = _LOCK_TIMEOUT_SECONDS,
    ) -> None:
        self.log_path = Path(log_path)
        self._lock_timeout = lock_timeout
        self._lock_path = self.log_path.with_name(self.log_path.name + ".lock")
        # None = gesund. Sonst Grund des letzten Ausweichens (für UI-Warnung):
        # "lock_timeout" / "write_error" (im lokalen Fallback) / "fallback_failed"
        # (Ereignis VERLOREN — muss dem Operator angezeigt werden).
        self.degraded_reason: str | None = None

    # ---- Schreiben -------------------------------------------------------

    def append_start(self, record: dict) -> None:
        self._append({**record, "kind": "stoerung_start"})

    def append_ende(self, record: dict) -> None:
        self._append({**record, "kind": "stoerung_ende"})

    def _append(self, record: dict) -> None:
        line = json.dumps(record, ensure_ascii=False)
        self._safe_write(line)

    # ---- Lesen -----------------------------------------------------------

    def read_all(self) -> list[dict]:
        """Alle Roh-Ereignisse (start/ende) in Schreibreihenfolge. Fehler → []."""
        records: list[dict] = []
        try:
            if not self.log_path.exists():
                return []
            text = self.log_path.read_text(encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            _logger.error("Störungs-Store nicht lesbar: %s", e, exc_info=True)
            return []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                _logger.warning("Störungs-Store: ungültige Zeile übersprungen")
        return records

    # ---- Robustheit (Lock + Fallback + Replay) ---------------------------

    def _write_to_fallback(self, line: str) -> None:
        fb = _local_fallback_path()
        try:
            fb.parent.mkdir(parents=True, exist_ok=True)
            with open(fb, "a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
        except Exception as e:  # noqa: BLE001
            self.degraded_reason = "fallback_failed"
            _logger.critical("Störungs-Fallback nicht schreibbar: %s", e, exc_info=True)

    def _try_replay_fallback(self) -> None:
        """Hängt offline zwischengespeicherte Ereignisse an (crash-sicher via Rename)."""
        fb = _local_fallback_path()
        replay = fb.with_name(fb.name + ".replaying")
        try:
            if not replay.exists():
                if not fb.exists() or fb.stat().st_size == 0:
                    return
                fb.rename(replay)
            pending = replay.read_text(encoding="utf-8")
            if pending.strip():
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(pending)
                    if not pending.endswith("\n"):
                        f.write("\n")
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except OSError:
                        pass
            replay.unlink()
            if pending.strip():
                _logger.info("Störungs-Fallback nachgeholt (%d Bytes)", len(pending))
        except Exception as e:  # noqa: BLE001
            _logger.error("Störungs-Fallback-Replay fehlgeschlagen: %s", e, exc_info=True)

    def _safe_write(self, line: str) -> None:
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:  # noqa: BLE001
            _logger.error("Störungs-Verzeichnis nicht erstellbar: %s", e, exc_info=True)
            self.degraded_reason = "write_error"
            self._write_to_fallback(line)
            return

        lock_fd: int | None = None
        try:
            lock_fd = os.open(str(self._lock_path), os.O_RDWR | os.O_CREAT, 0o644)
            if not acquire_lock(lock_fd, self._lock_timeout):
                _logger.warning("Störungs-Lock-Timeout — schreibe lokal in Fallback")
                self.degraded_reason = "lock_timeout"
                self._write_to_fallback(line)
                return

            self._try_replay_fallback()

            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            self.degraded_reason = None
        except Exception as e:  # noqa: BLE001
            _logger.error("Störungs-Schreibfehler: %s", e, exc_info=True)
            self.degraded_reason = "write_error"
            self._write_to_fallback(line)
        finally:
            if lock_fd is not None:
                release_lock(lock_fd)
                try:
                    os.close(lock_fd)
                except OSError:
                    pass
