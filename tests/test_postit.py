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
_test_db = os.path.join(_test_tmp, "test.db")
os.environ["DB_PATH"] = _test_db

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_src_db = ROOT / "data" / "production.db"
if _src_db.is_file():
    import shutil

    shutil.copy2(_src_db, _test_db)


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
            # AUTOINCREMENT : sans remise à zéro, les ids 1 et 2 visés plus bas
            # n'existent pas dès que la base copiée contient déjà des post-its.
            conn.execute("DELETE FROM sqlite_sequence WHERE name='postits'")
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


class TestPostitBlocs(unittest.TestCase):
    """Prise de notes libre : contenu en blocs."""

    def setUp(self):
        from database import get_db

        with get_db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (id, email, nom, password_hash, role, actif, created_at) "
                "VALUES (1, 'test@local', 'Test', 'x', 'direction', 1, '2026-01-01')"
            )
            self.pid = conn.execute(
                "INSERT INTO postits (user_id, type, title) VALUES (1, 'someday', 'Blocs')"
            ).lastrowid
            conn.commit()

    def _client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.routers.postit import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_contenu_column_present(self):
        from database import get_db

        with get_db() as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(postits)").fetchall()]
        self.assertIn("contenu", cols)

    def test_creation_et_lecture_blocs(self):
        client = self._client()
        blocs = [
            {"type": "h1", "texte": "Réunion"},
            {"type": "todo", "texte": "Appeler", "coche": True, "retrait": 1},
            {"type": "sep", "texte": "ignoré"},
            {"type": "p", "texte": "Libre\nsur deux lignes"},
        ]
        with patch("app.routers.postit.get_current_user", return_value={"id": 1}):
            r = client.post("/api/postits", json={"type": "someday", "title": "Note", "blocs": blocs})
            self.assertEqual(r.status_code, 200)
            pid = r.json()["id"]
            liste = client.get("/api/postits").json()
        p = next(x for x in liste if x["id"] == pid)
        self.assertNotIn("contenu", p)
        self.assertEqual(p["blocs"][0], {"type": "h1", "texte": "Réunion"})
        self.assertEqual(p["blocs"][1], {"type": "todo", "texte": "Appeler", "retrait": 1, "coche": True})
        self.assertEqual(p["blocs"][2]["texte"], "")
        self.assertEqual(p["blocs"][3]["texte"], "Libre\nsur deux lignes")

    def test_patch_blocs(self):
        client = self._client()
        with patch("app.routers.postit.get_current_user", return_value={"id": 1}):
            r = client.patch(f"/api/postits/{self.pid}", json={"blocs": [{"type": "citation", "texte": "x"}]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["blocs"], [{"type": "citation", "texte": "x"}])

    def test_type_inconnu_refuse(self):
        client = self._client()
        with patch("app.routers.postit.get_current_user", return_value={"id": 1}):
            r = client.patch(f"/api/postits/{self.pid}", json={"blocs": [{"type": "script", "texte": "x"}]})
        self.assertEqual(r.status_code, 400)

    def test_blocs_non_liste_refuses(self):
        client = self._client()
        with patch("app.routers.postit.get_current_user", return_value={"id": 1}):
            r = client.patch(f"/api/postits/{self.pid}", json={"blocs": "texte"})
        self.assertEqual(r.status_code, 400)

    def test_ajout_case_par_assistant(self):
        client = self._client()
        with patch("app.routers.postit.get_current_user", return_value={"id": 1}):
            client.patch(f"/api/postits/{self.pid}", json={"blocs": [{"type": "p", "texte": "a"}]})
            r = client.post(f"/api/postits/{self.pid}/tasks", json={"text": "Relancer"})
            self.assertEqual(r.status_code, 200)
            p = next(x for x in client.get("/api/postits").json() if x["id"] == self.pid)
        self.assertEqual(p["blocs"][-1], {"type": "todo", "texte": "Relancer", "coche": False})

    def test_migration_reprend_les_taches(self):
        import importlib

        from database import get_db

        mig = importlib.import_module("app.core.migrations.2026_11_09_postits_notes_libres")
        with get_db() as conn:
            cur = conn.execute("INSERT INTO postits (user_id, type, title) VALUES (1, 'today', 'Ancien')")
            pid = cur.lastrowid
            conn.execute("UPDATE postits SET contenu=NULL WHERE id=?", (pid,))
            conn.execute("INSERT INTO postit_tasks (postit_id, text, done, order_index) VALUES (?, 'B', 1, 1)", (pid,))
            conn.execute("INSERT INTO postit_tasks (postit_id, text, done, order_index) VALUES (?, 'A', 0, 0)", (pid,))
            conn.commit()
            mig.appliquer(conn)
            mig.appliquer(conn)
            brut = conn.execute("SELECT contenu FROM postits WHERE id=?", (pid,)).fetchone()[0]
        import json

        self.assertEqual(
            json.loads(brut),
            [{"type": "todo", "texte": "A", "coche": False}, {"type": "todo", "texte": "B", "coche": True}],
        )


if __name__ == "__main__":
    unittest.main()
