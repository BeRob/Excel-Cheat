"""Tests für den KV-Datei Parser."""

import tempfile
import unittest
from pathlib import Path

from src.auth.users_kv import parse_users_kv


class TestKVParser(unittest.TestCase):

    def _write_temp(self, content: str) -> Path:
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".kv", delete=False, encoding="utf-8")
        f.write(content)
        f.close()
        return Path(f.name)

    def test_parse_single_user(self):
        path = self._write_temp(
            "user.max.password=1234\nuser.max.qr=QR-MAX\nuser.max.name=Max Mustermann\n"
        )
        users = parse_users_kv(path)
        self.assertIn("max", users)
        self.assertEqual(users["max"]["password"], "1234")
        self.assertEqual(users["max"]["qr"], "QR-MAX")
        self.assertEqual(users["max"]["name"], "Max Mustermann")

    def test_parse_multiple_users(self):
        path = self._write_temp(
            "user.max.password=1234\nuser.max.name=Max\n"
            "user.anna.password=pass\nuser.anna.name=Anna\n"
        )
        users = parse_users_kv(path)
        self.assertEqual(len(users), 2)
        self.assertIn("max", users)
        self.assertIn("anna", users)

    def test_skip_empty_lines_and_comments(self):
        path = self._write_temp(
            "# Kommentar\n\nuser.max.password=1234\n\n# Noch ein Kommentar\n"
        )
        users = parse_users_kv(path)
        self.assertEqual(len(users), 1)
        self.assertEqual(users["max"]["password"], "1234")

    def test_value_with_equals(self):
        path = self._write_temp("user.max.password=a=b=c\n")
        users = parse_users_kv(path)
        self.assertEqual(users["max"]["password"], "a=b=c")

    def test_malformed_lines_skipped(self):
        path = self._write_temp(
            "user.max.password=1234\ngarbage_line\nno_dots=value\nuser.anna.password=pass\n"
        )
        users = parse_users_kv(path)
        self.assertEqual(len(users), 2)

    def test_missing_property(self):
        path = self._write_temp("user.max.password=1234\n")
        users = parse_users_kv(path)
        self.assertNotIn("name", users["max"])

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            parse_users_kv("/nonexistent/path.kv")


if __name__ == "__main__":
    unittest.main()
