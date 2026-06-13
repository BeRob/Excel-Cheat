"""Tests für AuthService (Passwort- und QR-Login, Admin-Flag)."""

import shutil
import tempfile
import unittest
from pathlib import Path

from src.auth.login import AuthService


_USERS_KV = """\
# Testbenutzer
user.anna.password=geheim
user.anna.qr=QR123
user.anna.name=Anna Muster
user.anna.admin=true
user.bob.password=1234
user.bob.qr=QR999
user.bob.name=Bob Beispiel
"""


class AuthServiceTestBase(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.kv_path = self.tmp_dir / "users.kv"
        self.kv_path.write_text(_USERS_KV, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)


class TestPasswordLogin(AuthServiceTestBase):

    def test_valid_login(self):
        auth = AuthService(self.kv_path)
        user = auth.login_password("anna", "geheim")
        self.assertIsNotNone(user)
        self.assertEqual(user.user_id, "anna")
        self.assertEqual(user.display_name, "Anna Muster")

    def test_wrong_password_rejected(self):
        auth = AuthService(self.kv_path)
        self.assertIsNone(auth.login_password("anna", "falsch"))

    def test_unknown_user_rejected(self):
        auth = AuthService(self.kv_path)
        self.assertIsNone(auth.login_password("eve", "geheim"))

    def test_empty_password_rejected(self):
        auth = AuthService(self.kv_path)
        self.assertIsNone(auth.login_password("anna", ""))

    def test_admin_flag_propagated(self):
        auth = AuthService(self.kv_path)
        self.assertTrue(auth.login_password("anna", "geheim").is_admin)
        self.assertFalse(auth.login_password("bob", "1234").is_admin)


class TestQrLogin(AuthServiceTestBase):

    def test_qr_match(self):
        auth = AuthService(self.kv_path)
        user = auth.login_qr("QR123")
        self.assertIsNotNone(user)
        self.assertEqual(user.user_id, "anna")

    def test_qr_with_scanner_prefix_stripped(self):
        auth = AuthService(self.kv_path, qr_prefix="WF2 ")
        user = auth.login_qr("WF2 QR999")
        self.assertIsNotNone(user)
        self.assertEqual(user.user_id, "bob")

    def test_qr_without_configured_prefix_still_matches(self):
        auth = AuthService(self.kv_path, qr_prefix="WF2 ")
        self.assertIsNotNone(auth.login_qr("QR123"))

    def test_unknown_qr_rejected(self):
        auth = AuthService(self.kv_path)
        self.assertIsNone(auth.login_qr("QR000"))

    def test_qr_whitespace_stripped(self):
        auth = AuthService(self.kv_path)
        self.assertIsNotNone(auth.login_qr("  QR123  "))


if __name__ == "__main__":
    unittest.main()
