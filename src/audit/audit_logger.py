"""GMP-Audit-Log als JSONL mit Tagesrotation und Netzlaufwerk-Robustheit.

Mehrere Workstations schreiben gleichzeitig in dieselbe Datei auf einem
SMB-Share. Eine separate Lock-Datei (Inter-Prozess) serialisiert die
Append-Operationen. Bei Netzlauswerk-Aussetzern werden Events lokal
zwischengespeichert und beim nächsten erfolgreichen Lock nachgereicht —
es geht kein Event verloren.

Tagesrotation: vor jedem Schreiben wird geprüft, ob die aktive Datei
älter als heute ist. Wenn ja, wird sie in audit_log.jsonl.YYYY-MM-DD
umbenannt. Race-Free, weil der Rename innerhalb des Locks geschieht
und die Zieldatei vorher auf Existenz geprüft wird (andere Workstation
war schneller).
"""

from __future__ import annotations

import getpass
import json
import logging
import os
import socket
import sys
import uuid
from datetime import datetime, date, timezone
from pathlib import Path

from src.audit.file_lock import acquire_lock, release_lock
from src.version import APP_VERSION


_LOCK_TIMEOUT_SECONDS = 5.0
_logger = logging.getLogger("audit")


def _local_fallback_path() -> Path:
    """Lokaler Pfad für Events, die wegen Netzaussetzer nicht ins Audit konnten."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("TEMP") or "."
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return Path(base) / "QAInput" / "audit_local_fallback.jsonl"


class AuditLogger:
    """Schreibt strukturierte Events als JSON-Zeilen.

    Pro App-Instanz: eine session_id (UUID), die jedem Event beigelegt wird.
    Damit lassen sich Sessions auch über View-Wechsel und Workstation-
    Grenzen hinweg zuordnen.
    """

    def __init__(
        self, log_path: str | Path, *,
        lock_timeout: float = _LOCK_TIMEOUT_SECONDS,
    ) -> None:
        self.log_path = Path(log_path)
        self._lock_timeout = lock_timeout
        self._lock_path = self.log_path.with_name(self.log_path.name + ".lock")
        self._session_id = uuid.uuid4().hex
        self._host = socket.gethostname()
        # Windows-/OS-Benutzer (unabhängig vom App-User). getpass.getuser
        # liest zuerst die Env-Vars USER/LOGNAME/USERNAME — funktioniert
        # auch in nicht-interaktiven Sessions, anders als os.getlogin().
        try:
            self._os_user = getpass.getuser()
        except Exception:
            self._os_user = "?"
        self._current_view: str | None = None
        # None = Audit-Trail gesund. Sonst Grund des letzten Ausweichens:
        # "lock_timeout" / "write_error" (Event liegt im lokalen Fallback),
        # "fallback_failed" (Event ist VERLOREN — muss dem Operator angezeigt
        # werden, sonst entstehen stille Lücken in der GMP-Dokumentation).
        self.degraded_reason: str | None = None

    @property
    def host(self) -> str:
        return self._host

    @property
    def os_user(self) -> str:
        return self._os_user

    @property
    def session_id(self) -> str:
        return self._session_id

    def set_view(self, view_name: str | None) -> None:
        """Vom App-Navigator gesetzt — wird in jedes folgende Event geschrieben."""
        self._current_view = view_name

    def log_event(
        self,
        event: str,
        level: str = "info",
        user: str | None = None,
        file: str | None = None,
        context: dict | None = None,
        details: dict | None = None,
    ) -> None:
        entry: dict = {
            "ts": datetime.now(timezone.utc).astimezone().isoformat(),
            "event": event,
            "level": level,
            "app_version": APP_VERSION,
            "session": self._session_id,
            "host": self._host,
            "win_user": self._os_user,
        }
        if self._current_view is not None:
            entry["view"] = self._current_view
        if user is not None:
            entry["user"] = user
        if file is not None:
            entry["file"] = file
        if context is not None:
            entry["context"] = context
        if details is not None:
            entry["details"] = details

        line = json.dumps(entry, ensure_ascii=False)
        self._safe_write(line, event=event, level=level)

    # Rückwärts-kompatibel — alte Callsites benutzen log(...)
    def log(
        self,
        event: str,
        user: str | None = None,
        file: str | None = None,
        context: dict | None = None,
        details: dict | None = None,
    ) -> None:
        self.log_event(
            event, level="info", user=user, file=file,
            context=context, details=details,
        )

    def _maybe_rotate(self) -> None:
        """Wenn die aktive Datei vom Vortag ist, in audit_log.jsonl.YYYY-MM-DD umbenennen.

        Race-Behandlung: existiert die Zieldatei bereits (andere Workstation
        war schneller), wird der Rename übersprungen — wir schreiben dann
        einfach in die schon vorhandene neue Datei.

        Annahme: alle Workstations eines Werks laufen in derselben Zeitzone
        (mtime-Datum und date.today() sind beide lokal). Bei Standorten in
        verschiedenen Zeitzonen würde die Rotationsgrenze auseinanderlaufen."""
        try:
            if not self.log_path.exists():
                return
            mtime = datetime.fromtimestamp(self.log_path.stat().st_mtime).date()
            today = date.today()
            if mtime >= today:
                return
            archived = self.log_path.with_name(
                self.log_path.name + "." + mtime.strftime("%Y-%m-%d")
            )
            if archived.exists():
                # Andere Workstation hat schon rotiert — die heutige Datei
                # ist eventuell schon neu angelegt; nichts zu tun.
                return
            self.log_path.rename(archived)
        except Exception as e:
            _logger.warning("Audit-Rotation fehlgeschlagen: %s", e, exc_info=True)

    def _try_replay_fallback(self) -> None:
        """Hängt eventuell vorher offline-zwischengespeicherte Events an.

        Crash-sicher über eine Replay-Datei: der aktive Fallback wird zuerst
        per Rename beiseitegelegt. Schlägt das Anhängen fehl, bleibt die
        Replay-Datei vollständig liegen und wird beim nächsten Versuch zuerst
        nachgeholt — schlimmstenfalls entstehen Duplikate (erkennbar an
        session+ts), nie Lücken. Das frühere Leeren per write_text("") konnte
        bei einem Fehlschlag nach dem Anhängen Duplikate erzeugen und bei
        teilweisem Verhalten Events verlieren."""
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
                _logger.info("Audit-Fallback nachgeholt (%d Bytes)", len(pending))
        except Exception as e:
            _logger.error("Audit-Fallback-Replay fehlgeschlagen: %s", e, exc_info=True)

    def _write_to_fallback(self, line: str) -> None:
        fb = _local_fallback_path()
        try:
            fb.parent.mkdir(parents=True, exist_ok=True)
            with open(fb, "a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
        except Exception as e:
            # Event ist verloren — Status setzen, damit die UI warnen kann.
            self.degraded_reason = "fallback_failed"
            _logger.critical("Audit-Fallback nicht schreibbar: %s", e, exc_info=True)

    def _safe_write(self, line: str, event: str, level: str) -> None:
        # Zusätzlich zum strukturierten Audit-Log auch in debug.log/error.log
        # mitschreiben — pro Event-Level passender Logger.
        py_level = {
            "error": logging.ERROR,
            "warn": logging.WARNING,
            "warning": logging.WARNING,
            "info": logging.INFO,
            "debug": logging.DEBUG,
        }.get(level.lower(), logging.INFO)
        _logger.log(py_level, "%s %s", event, line)

        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            _logger.error("Audit-Verzeichnis nicht erstellbar: %s", e, exc_info=True)
            self.degraded_reason = "write_error"
            self._write_to_fallback(line)
            return

        lock_fd: int | None = None
        try:
            lock_fd = os.open(
                str(self._lock_path),
                os.O_RDWR | os.O_CREAT,
                0o644,
            )
            if not acquire_lock(lock_fd, self._lock_timeout):
                _logger.warning(
                    "Audit-Lock-Timeout — schreibe lokal in Fallback-Datei"
                )
                self.degraded_reason = "lock_timeout"
                self._write_to_fallback(line)
                return

            self._maybe_rotate()
            self._try_replay_fallback()

            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            self.degraded_reason = None
        except Exception as e:
            _logger.error("Audit-Schreibfehler: %s", e, exc_info=True)
            self.degraded_reason = "write_error"
            self._write_to_fallback(line)
        finally:
            if lock_fd is not None:
                release_lock(lock_fd)
                try:
                    os.close(lock_fd)
                except OSError:
                    pass
