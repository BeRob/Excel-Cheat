"""Tests für den GMP-Audit-Logger: Schreiben, Rotation, Lock-Timeout, Fallback-Replay."""

import json
import os
import shutil
import tempfile
import time
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from src.audit.audit_logger import AuditLogger
from src.audit.file_lock import acquire_lock, release_lock


class AuditLoggerTestBase(unittest.TestCase):
    """Gemeinsames Setup: Temp-Verzeichnis + umgeleiteter lokaler Fallback."""

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.log_path = self.tmp_dir / "audit_log.jsonl"
        self.fallback = self.tmp_dir / "local" / "audit_local_fallback.jsonl"
        patcher = mock.patch(
            "src.audit.audit_logger._local_fallback_path",
            return_value=self.fallback,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _read_events(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]


class TestLogEvent(AuditLoggerTestBase):

    def test_writes_jsonl_with_required_keys(self):
        logger = AuditLogger(self.log_path)
        logger.log_event("test_event", user="anna", details={"x": 1})

        events = self._read_events(self.log_path)
        self.assertEqual(len(events), 1)
        e = events[0]
        for key in ("ts", "event", "level", "app_version", "session",
                    "host", "win_user"):
            self.assertIn(key, e)
        self.assertEqual(e["event"], "test_event")
        self.assertEqual(e["user"], "anna")
        self.assertEqual(e["details"], {"x": 1})
        self.assertIsNone(logger.degraded_reason)

    def test_view_included_when_set(self):
        logger = AuditLogger(self.log_path)
        logger.set_view("form")
        logger.log_event("test_event")
        self.assertEqual(self._read_events(self.log_path)[0]["view"], "form")


class TestRotation(AuditLoggerTestBase):

    def test_rotates_yesterdays_file(self):
        logger = AuditLogger(self.log_path)
        logger.log_event("event_gestern")

        yesterday = date.today() - timedelta(days=1)
        old = time.mktime(
            time.strptime(yesterday.strftime("%Y-%m-%d") + " 12:00", "%Y-%m-%d %H:%M")
        )
        os.utime(self.log_path, (old, old))

        logger.log_event("event_heute")

        archived = self.log_path.with_name(
            self.log_path.name + "." + yesterday.strftime("%Y-%m-%d")
        )
        self.assertTrue(archived.exists())
        self.assertEqual(self._read_events(archived)[0]["event"], "event_gestern")
        self.assertEqual(self._read_events(self.log_path)[0]["event"], "event_heute")


class TestLockTimeoutFallback(AuditLoggerTestBase):

    def test_lock_timeout_writes_to_fallback(self):
        # Lock von außen halten — der Logger muss in den Fallback ausweichen
        # und seinen Degraded-Status setzen (UI-Warnung hängt daran).
        lock_path = self.log_path.with_name(self.log_path.name + ".lock")
        fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
        self.assertTrue(acquire_lock(fd, 1.0))
        try:
            logger = AuditLogger(self.log_path, lock_timeout=0.1)
            logger.log_event("blocked_event")

            self.assertEqual(logger.degraded_reason, "lock_timeout")
            events = self._read_events(self.fallback)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["event"], "blocked_event")
            self.assertFalse(self.log_path.exists())
        finally:
            release_lock(fd)
            os.close(fd)

    def test_recovers_after_lock_released(self):
        lock_path = self.log_path.with_name(self.log_path.name + ".lock")
        fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
        self.assertTrue(acquire_lock(fd, 1.0))
        logger = AuditLogger(self.log_path, lock_timeout=0.1)
        logger.log_event("offline_event")
        release_lock(fd)
        os.close(fd)

        logger.log_event("online_event")

        # Beide Events im Hauptlog (Fallback wurde nachgeholt), Status gesund.
        names = [e["event"] for e in self._read_events(self.log_path)]
        self.assertEqual(names, ["offline_event", "online_event"])
        self.assertIsNone(logger.degraded_reason)
        self.assertTrue(
            not self.fallback.exists() or self.fallback.stat().st_size == 0
        )


class TestFallbackReplay(AuditLoggerTestBase):

    def test_replay_appends_and_clears(self):
        self.fallback.parent.mkdir(parents=True, exist_ok=True)
        self.fallback.write_text(
            '{"event": "offline_1"}\n{"event": "offline_2"}\n', encoding="utf-8"
        )

        logger = AuditLogger(self.log_path)
        logger.log_event("online_event")

        names = [e["event"] for e in self._read_events(self.log_path)]
        self.assertEqual(names, ["offline_1", "offline_2", "online_event"])
        self.assertTrue(
            not self.fallback.exists() or self.fallback.stat().st_size == 0
        )

    def test_replay_leftover_from_crash_is_processed_first(self):
        # Eine .replaying-Datei von einem Absturz mitten im Replay darf nicht
        # liegen bleiben — sie wird beim nächsten Schreiben zuerst nachgeholt.
        replaying = self.fallback.with_name(self.fallback.name + ".replaying")
        replaying.parent.mkdir(parents=True, exist_ok=True)
        replaying.write_text('{"event": "crash_leftover"}\n', encoding="utf-8")

        logger = AuditLogger(self.log_path)
        logger.log_event("online_event")

        names = [e["event"] for e in self._read_events(self.log_path)]
        self.assertEqual(names, ["crash_leftover", "online_event"])
        self.assertFalse(replaying.exists())


class TestDegradedOnWriteError(AuditLoggerTestBase):

    def test_unwritable_log_dir_falls_back(self):
        # Elternpfad ist eine DATEI → mkdir schlägt fehl → Event landet im
        # Fallback, Status "write_error" (kein Event geht verloren).
        blocker = self.tmp_dir / "blocker"
        blocker.write_text("", encoding="utf-8")
        logger = AuditLogger(blocker / "sub" / "audit_log.jsonl")
        logger.log_event("rescued_event")

        self.assertEqual(logger.degraded_reason, "write_error")
        events = self._read_events(self.fallback)
        self.assertEqual(events[0]["event"], "rescued_event")


if __name__ == "__main__":
    unittest.main()
