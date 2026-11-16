import importlib
import io
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


class ApiSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.upload_dir = root / "uploads"
        cls.upload_dir.mkdir()
        cls.env = patch.dict(
            os.environ,
            {
                "DB_PATH": str(root / "allinone.db"),
                "UPLOAD_DIR": str(cls.upload_dir),
            },
        )
        cls.env.start()

        import database
        database._engine = None
        database._session_factory = None

        cls.main = importlib.import_module("main")
        cls.client_context = TestClient(cls.main.app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)
        cls.env.stop()
        cls.tmp.cleanup()

    def test_uploads_require_login_and_work_with_session_cookie(self):
        item_dir = self.upload_dir / "items"
        item_dir.mkdir(exist_ok=True)
        (item_dir / "private.txt").write_text("private", encoding="utf-8")

        self.client.cookies.clear()
        anonymous = self.client.get("/uploads/items/private.txt")
        self.assertEqual(anonymous.status_code, 401)

        login = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn("aio_session", login.cookies)

        authenticated = self.client.get("/uploads/items/private.txt")
        self.assertEqual(authenticated.status_code, 200)
        self.assertEqual(authenticated.text, "private")

    def test_login_upgrades_legacy_password_hash(self):
        from database import get_session_factory
        from models.auth import User

        response = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        self.assertEqual(response.status_code, 200)

        db = get_session_factory()()
        try:
            user = db.query(User).filter(User.username == "admin").first()
            self.assertTrue(user.password_hash.startswith("scrypt$"))
        finally:
            db.close()

    def test_reset_password_does_not_reveal_user_state(self):
        missing = self.client.post(
            "/api/auth/reset-password",
            json={
                "username": "missing-user",
                "security_code": "0000",
                "new_password": "new-password",
            },
        )
        no_code = self.client.post(
            "/api/auth/reset-password",
            json={
                "username": "admin",
                "security_code": "0000",
                "new_password": "new-password",
            },
        )
        self.assertEqual(missing.status_code, 401)
        self.assertEqual(no_code.status_code, 401)
        self.assertEqual(missing.json()["detail"], no_code.json()["detail"])

    def test_backup_export_excludes_user_credentials(self):
        self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        response = self.client.get("/api/backup/export")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("users", response.json()["modules"]["system"])

    def test_full_backup_uses_portable_upload_paths(self):
        item_dir = self.upload_dir / "items"
        item_dir.mkdir(exist_ok=True)
        photo = item_dir / "backup-photo.txt"
        photo.write_text("photo", encoding="utf-8")

        self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        response = self.client.get("/api/backup/export/full")
        self.assertEqual(response.status_code, 200)

        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            names = archive.namelist()
        self.assertIn("uploads/items/backup-photo.txt", names)
        self.assertFalse(any(name.startswith("../") for name in names))

        photo.write_text("changed", encoding="utf-8")
        restored = self.client.post(
            "/api/backup/import/full",
            files={"file": ("backup.zip", response.content, "application/zip")},
        )
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(photo.read_text(encoding="utf-8"), "photo")


if __name__ == "__main__":
    unittest.main()
