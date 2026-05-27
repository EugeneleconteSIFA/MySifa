"""Tests API post-its (multi-page)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# DB isolée avant tout import projet (init_db au chargement de database.py)
_test_tmp = tempfile.mkdtemp(prefix="mysifa_postit_test_")
os.environ["DB_PATH"] = os.path.join(_test_tmp, "test.db")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestPostitMultiPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from database import get_db

        with get_db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (id, email, nom, password_hash, role, actif, created_at) "
                "VALUES (1, 'test@local', 'Test', 'x', 'direction', 1, '2026-01-01')"
            )
            conn.execute("DELETE FROM postit_tasks")
            conn.execute("DELETE FROM postits")
            conn.execute(
                "INSERT INTO postits (user_id, type, title, multi_page) VALUES (1, 'today', 'P1', 0)"
            )
            conn.execute(
                "INSERT INTO postits (user_id, type, title, multi_page) VALUES (1, 'someday', 'P2', 1)"
            )
            conn.commit()

    def test_multi_page_column_present(self):
        from database import get_db

        with get_db() as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(postits)").fetchall()]
        self.assertIn("multi_page", cols)

    def test_list_includes_multi_page(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.routers.postit import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        with patch("app.routers.postit.get_current_user", return_value={"id": 1}):
            r = client.get("/api/postits")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(len(data), 2)
        by_title = {p["title"]: p for p in data}
        self.assertEqual(by_title["P1"]["multi_page"], 0)
        self.assertEqual(by_title["P2"]["multi_page"], 1)

    def test_patch_toggle_multi_page(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.routers.postit import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        with patch("app.routers.postit.get_current_user", return_value={"id": 1}):
            r = client.patch("/api/postits/1", json={"multi_page": True})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("ok"))
        self.assertEqual(body.get("multi_page"), 1)
        from database import get_db

        with get_db() as conn:
            row = conn.execute("SELECT multi_page FROM postits WHERE id=1").fetchone()
        self.assertEqual(row["multi_page"], 1)

    def test_patch_title_only(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.routers.postit import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        with patch("app.routers.postit.get_current_user", return_value={"id": 1}):
            r = client.patch("/api/postits/1", json={"title": "Renommé"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("title"), "Renommé")

    def test_hidden_column_present(self):
        from database import get_db

        with get_db() as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(postits)").fetchall()]
        self.assertIn("hidden", cols)

    def test_patch_toggle_hidden(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.routers.postit import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        with patch("app.routers.postit.get_current_user", return_value={"id": 1}):
            r = client.patch("/api/postits/1", json={"hidden": True})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("ok"))
        self.assertEqual(body.get("hidden"), 1)
        from database import get_db

        with get_db() as conn:
            row = conn.execute("SELECT hidden FROM postits WHERE id=1").fetchone()
        self.assertEqual(row["hidden"], 1)

    def test_color_column_present(self):
        from database import get_db

        with get_db() as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(postits)").fetchall()]
        self.assertIn("color", cols)

    def test_patch_color(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.routers.postit import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        with patch("app.routers.postit.get_current_user", return_value={"id": 1}):
            r = client.patch("/api/postits/1", json={"color": "#34d399"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("color"), "#34d399")
        from database import get_db

        with get_db() as conn:
            row = conn.execute("SELECT color FROM postits WHERE id=1").fetchone()
        self.assertEqual(row["color"], "#34d399")

    def test_patch_invalid_color_rejected(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.routers.postit import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        with patch("app.routers.postit.get_current_user", return_value={"id": 1}):
            r = client.patch("/api/postits/1", json={"color": "rouge"})
        self.assertEqual(r.status_code, 400)

    def test_patch_empty_body_rejected(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.routers.postit import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        with patch("app.routers.postit.get_current_user", return_value={"id": 1}):
            r = client.patch("/api/postits/1", json={})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
