"""Zentrales JSONL-Auditlog."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


class AuditLogger:
    """Schreibt strukturierte Audit-Events als JSON-Zeilen in eine Logdatei."""

    def __init__(self, log_path: str | Path) -> None:
        self.log_path = Path(log_path)

    def log(
        self,
        event: str,
        user: str | None = None,
        file: str | None = None,
        context: dict | None = None,
        details: dict | None = None,
    ) -> None:
        """Schreibt ein Audit-Event als JSONL-Zeile."""
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

        line = json.dumps(entry, ensure_ascii=False)
        self._safe_write(line)

    def _safe_write(self, line: str) -> None:
        """Hängt eine Zeile an die Logdatei an. Fehler werden abgefangen."""
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            print(f"[AUDIT FEHLER] Konnte nicht schreiben: {e}", file=sys.stderr)
