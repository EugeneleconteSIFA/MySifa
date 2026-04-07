"""Tests légers sans dépendance lourde (stdlib)."""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestPathSafety(unittest.TestCase):
    def test_upload_stays_under_root(self):
        from services.path_safety import path_is_under_directory, safe_upload_dest

        from config import UPLOAD_DIR

        p = safe_upload_dest(UPLOAD_DIR, "fichier.csv", "20260101_120000")
        self.assertTrue(path_is_under_directory(p, UPLOAD_DIR))

    def test_parent_jump_rejected(self):
        from tempfile import TemporaryDirectory

        from services.path_safety import path_is_under_directory

        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "uploads"
            root.mkdir()
            evil = os.path.normpath(os.path.join(str(root), "..", "secret.txt"))
            self.assertFalse(path_is_under_directory(evil, str(root)))


class TestOperationsJsonValidation(unittest.TestCase):
    def test_valid_sample(self):
        from config import validate_operations_config

        validate_operations_config(
            {
                "01": {"severity": "info", "label": "x", "category": "y"},
                "99": {"severity": "critique", "label": "z", "category": "w"},
            }
        )

    def test_invalid_severity(self):
        from config import validate_operations_config

        with self.assertRaises(ValueError):
            validate_operations_config(
                {"01": {"severity": "oops", "label": "x", "category": "y"}}
            )


class TestOperationsJsonFile(unittest.TestCase):
    def test_repo_file_loads(self):
        from config import load_operations

        path = ROOT / "operations.json"
        if not path.is_file():
            self.skipTest("operations.json absent")
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        from config import validate_operations_config

        validate_operations_config(raw)
        data = load_operations()
        self.assertIsInstance(data, dict)
        self.assertGreater(len(data), 3)


if __name__ == "__main__":
    unittest.main()
