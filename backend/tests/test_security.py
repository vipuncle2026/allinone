import hashlib
import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from routers.auth import (
    _hash_password,
    _hash_security_code,
    _verify_password,
    _verify_security_code,
)
from services.backup_service import restore_full_backup
from services.upload_utils import resolve_upload_path, safe_extract_path


class UploadPathTests(unittest.TestCase):
    def test_upload_reference_stays_inside_upload_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"UPLOAD_DIR": tmp}):
                target = resolve_upload_path("uploads/items/photo.jpg")
                self.assertEqual(target, Path(tmp).resolve() / "items/photo.jpg")

    def test_upload_reference_rejects_parent_and_absolute_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"UPLOAD_DIR": tmp}):
                for value in ("../allinone.db", "uploads/../allinone.db", "/etc/passwd"):
                    with self.subTest(value=value):
                        with self.assertRaises(HTTPException):
                            resolve_upload_path(value)

    def test_backup_entry_is_scoped_to_upload_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = safe_extract_path(tmp, "uploads/cycling/ride.gpx")
            self.assertEqual(Path(target), Path(tmp).resolve() / "cycling/ride.gpx")

            for value in (
                "uploads/../allinone.db",
                "uploads/../../routers/auth.py",
                "uploads\\..\\allinone.db",
            ):
                with self.subTest(value=value):
                    with self.assertRaises(HTTPException):
                        safe_extract_path(tmp, value)

    def test_full_restore_rejects_traversal_before_writing(self):
        payload = {
            "version": "1.0",
            "modules": {"finance": {"accounts": []}},
        }
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("backup_data.json", json.dumps(payload))
            archive.writestr("uploads/../allinone.db", b"not-a-database")

        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"UPLOAD_DIR": tmp}):
                with self.assertRaises(HTTPException):
                    restore_full_backup(buf.getvalue(), "malicious.zip")
                self.assertFalse((Path(tmp).parent / "allinone.db").exists())


class CredentialHashTests(unittest.TestCase):
    def test_scrypt_password_hash_is_salted_and_verifiable(self):
        first = _hash_password("correct horse battery staple")
        second = _hash_password("correct horse battery staple")
        self.assertNotEqual(first, second)
        self.assertTrue(_verify_password(first, "correct horse battery staple"))
        self.assertFalse(_verify_password(first, "wrong"))

    def test_legacy_password_hash_remains_compatible(self):
        legacy = hashlib.sha256(b"aio_salt_admin").hexdigest()
        self.assertTrue(_verify_password(legacy, "admin"))
        self.assertFalse(_verify_password(legacy, "admin123"))

    def test_security_code_hash_is_verifiable(self):
        hashed = _hash_security_code("123456")
        self.assertTrue(_verify_security_code(hashed, "123456"))
        self.assertFalse(_verify_security_code(hashed, "654321"))


if __name__ == "__main__":
    unittest.main()
