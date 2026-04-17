"""JSONL-Auditlog mit Inter-Prozess-Sperre."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


if sys.platform == "win32":
    import msvcrt

    def _acquire_lock(fd: int) -> None:
        os.lseek(fd, 0, os.SEEK_SET)
        # msvcrt.LK_LOCK blockiert bis zu 10s; bei Timeout erneut versuchen.
        while True:
            try:
                msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
                return
            except OSError:
                continue

    def _release_lock(fd: int) -> None:
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass

else:
    import fcntl

    def _acquire_lock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_EX)

    def _release_lock(fd: int) -> None:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass


class AuditLogger:
    """Schreibt strukturierte Events als JSON-Zeilen in eine Logdatei.

    Mehrere Prozesse können gleichzeitig schreiben: eine separate Lock-Datei
    serialisiert die Append-Operationen, damit Zeilen nicht ineinanderlaufen.
    """

    def __init__(self, log_path: str | Path) -> None:
        self.log_path = Path(log_path)
        self._lock_path = self.log_path.with_name(self.log_path.name + ".lock")

    def log(
        self,
        event: str,
        user: str | None = None,
        file: str | None = None,
        context: dict | None = None,
        details: dict | None = None,
    ) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).astimezone().isoformat(),
            "event": event,
        }
        if user is not None:
            entry["user"] = user
        if file is not None:
            entry["file"] = file
        if context is not None:
            entry["context"] = context
        if details is not None:
            entry["details"] = details

        self._safe_write(json.dumps(entry, ensure_ascii=False))

    def _safe_write(self, line: str) -> None:
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"[AUDIT FEHLER] Verzeichnis nicht erstellbar: {e}", file=sys.stderr)
            return

        lock_fd: int | None = None
        try:
            lock_fd = os.open(
                str(self._lock_path),
                os.O_RDWR | os.O_CREAT,
                0o644,
            )
            _acquire_lock(lock_fd)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
        except Exception as e:
            print(f"[AUDIT FEHLER] Konnte nicht schreiben: {e}", file=sys.stderr)
        finally:
            if lock_fd is not None:
                _release_lock(lock_fd)
                try:
                    os.close(lock_fd)
                except OSError:
                    pass
