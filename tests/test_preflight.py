"""Tests für den Startup-Preflight (src/config/preflight.py).

Setzt die Pfad-Attribute im settings-Modul direkt auf ein Temp-Verzeichnis
(check_paths liest sie beim Aufruf) und prüft die Schweregrade pro Fall.
Tk-frei — kein Tkinter nötig."""

import tempfile
import unittest
from pathlib import Path

from src.config import settings
from src.config.preflight import CRITICAL, WARNING, check_paths


_SETTINGS_ATTRS = (
    "USERS_KV_PATH", "PRODUCTS_DIR", "PROCESS_TEMPLATES_DIR",
    "AUDIT_DIR", "LOG_DIR", "APP_CONFIG_PATH",
)


class TestPreflight(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {a: getattr(settings, a) for a in _SETTINGS_ATTRS}
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        for a, v in self._saved.items():
            setattr(settings, a, v)
        self._tmp.cleanup()

    def _make_healthy(self) -> None:
        """Legt eine vollständige, gesunde Verzeichnisstruktur an und biegt
        die settings-Pfade darauf um."""
        users = self.root / "user"
        config = self.root / "config"
        products = self.root / "products"
        templates = self.root / "templates"
        audit = self.root / "audit"
        log = self.root / "log"
        for d in (users, config, products, templates, audit, log):
            d.mkdir(parents=True, exist_ok=True)

        (users / "users.kv").write_text("user.1.password=x\n", encoding="utf-8")
        (products / "REF1.json").write_text("{}", encoding="utf-8")
        (products / "freigaben.json").write_text("{}", encoding="utf-8")
        (templates / "Walzen.json").write_text("{}", encoding="utf-8")
        (config / "app_config.json").write_text("{}", encoding="utf-8")

        settings.USERS_KV_PATH = users / "users.kv"
        settings.PRODUCTS_DIR = products
        settings.PROCESS_TEMPLATES_DIR = templates
        settings.AUDIT_DIR = audit
        settings.LOG_DIR = log
        settings.APP_CONFIG_PATH = config / "app_config.json"

    def test_all_present_is_ok_without_issues(self) -> None:
        self._make_healthy()
        result = check_paths()
        self.assertTrue(result.ok)
        self.assertEqual(result.issues, [])

    def test_missing_users_kv_is_critical(self) -> None:
        self._make_healthy()
        settings.USERS_KV_PATH.unlink()
        result = check_paths()
        self.assertFalse(result.ok)
        labels = [i.label for i in result.critical]
        self.assertTrue(any("users.kv" in lbl for lbl in labels))

    def test_empty_products_dir_is_critical(self) -> None:
        self._make_healthy()
        (settings.PRODUCTS_DIR / "REF1.json").unlink()
        (settings.PRODUCTS_DIR / "freigaben.json").unlink()
        result = check_paths()
        self.assertFalse(result.ok)
        self.assertTrue(any("Produkt" in i.label for i in result.critical))

    def test_missing_templates_dir_is_critical(self) -> None:
        self._make_healthy()
        (settings.PROCESS_TEMPLATES_DIR / "Walzen.json").unlink()
        result = check_paths()
        self.assertFalse(result.ok)
        self.assertTrue(any("Template" in i.label for i in result.critical))

    def test_unwritable_audit_dir_is_critical(self) -> None:
        self._make_healthy()
        # Auf einen Pfad zeigen, dessen Elternteil eine Datei ist → mkdir scheitert.
        blocker = self.root / "blocker_file"
        blocker.write_text("x", encoding="utf-8")
        settings.AUDIT_DIR = blocker / "audit"
        result = check_paths()
        self.assertFalse(result.ok)
        self.assertTrue(any("Audit" in i.label for i in result.critical))

    def test_missing_app_config_is_only_warning(self) -> None:
        self._make_healthy()
        settings.APP_CONFIG_PATH.unlink()
        result = check_paths()
        self.assertTrue(result.ok)  # Warnings blockieren nicht
        self.assertTrue(any("app_config" in i.label for i in result.warnings))
        self.assertEqual(
            [i for i in result.warnings if i.severity != WARNING], []
        )

    def test_missing_freigaben_is_only_warning(self) -> None:
        self._make_healthy()
        (settings.PRODUCTS_DIR / "freigaben.json").unlink()
        result = check_paths()
        self.assertTrue(result.ok)
        warn_labels = [i.label for i in result.warnings]
        self.assertTrue(any("freigaben" in lbl for lbl in warn_labels))

    def test_critical_severity_marked_correctly(self) -> None:
        self._make_healthy()
        settings.USERS_KV_PATH.unlink()
        result = check_paths()
        self.assertTrue(all(i.severity == CRITICAL for i in result.critical))


if __name__ == "__main__":
    unittest.main()
