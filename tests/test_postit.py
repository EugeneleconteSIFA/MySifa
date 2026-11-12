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


def sans_uid(x):
    """Les blocs portent un identifiant aléatoire : on le retire pour comparer."""
    if isinstance(x, list):
        return [sans_uid(b) for b in x]
    return {k: v for k, v in x.items() if k != "uid"}


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
        self.assertEqual(sans_uid(p["blocs"][0]), {"type": "h1", "texte": "Réunion"})
        self.assertEqual(sans_uid(p["blocs"][1]), {"type": "todo", "texte": "Appeler", "retrait": 1, "coche": True})
        self.assertEqual(p["blocs"][2]["texte"], "")
        self.assertEqual(p["blocs"][3]["texte"], "Libre\nsur deux lignes")

    def test_patch_blocs(self):
        client = self._client()
        with patch("app.routers.postit.get_current_user", return_value={"id": 1}):
            r = client.patch(f"/api/postits/{self.pid}", json={"blocs": [{"type": "citation", "texte": "x"}]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(sans_uid(r.json()["blocs"]), [{"type": "citation", "texte": "x"}])

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
        self.assertEqual(sans_uid(p["blocs"][-1]), {"type": "todo", "texte": "Relancer", "coche": False})

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


class TestMesNotes(unittest.TestCase):
    """Espace Mes notes : écran, arbre, corbeille, dossier virtuel de l'explorateur."""

    def _client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.routers.postit import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def setUp(self):
        from database import get_db

        with get_db() as conn:
            for uid, mail in ((1, "test@local"), (2, "autre@local")):
                conn.execute(
                    "INSERT OR IGNORE INTO users (id, email, nom, password_hash, role, actif, created_at) "
                    "VALUES (?, ?, 'Test', 'x', 'direction', 1, '2026-01-01')",
                    (uid, mail),
                )
            conn.commit()
        self.c = self._client()

    def _creer(self, uid=1, **corps):
        corps.setdefault("type", "someday")
        corps.setdefault("title", "N")
        with patch("app.routers.postit.get_current_user", return_value={"id": uid}):
            r = self.c.post("/api/postits", json=corps)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def _get(self, url, uid=1):
        with patch("app.routers.postit.get_current_user", return_value={"id": uid}):
            return self.c.get(url)

    def test_note_hors_ecran_absente_des_postits(self):
        hors = self._creer(title="Hors écran", sur_ecran=0)
        sur = self._creer(title="Sur écran")
        ids = {p["id"] for p in self._get("/api/postits?ecran=1").json()}
        self.assertIn(sur["id"], ids)
        self.assertNotIn(hors["id"], ids)
        arbre = {n["id"] for n in self._get("/api/postits/notes").json()["notes"]}
        self.assertTrue({hors["id"], sur["id"]} <= arbre)

    def test_retirer_de_l_ecran_garde_la_note(self):
        n = self._creer(title="Garder")
        with patch("app.routers.postit.get_current_user", return_value={"id": 1}):
            r = self.c.patch(f"/api/postits/{n['id']}", json={"sur_ecran": False})
        self.assertEqual(r.json()["sur_ecran"], 0)
        self.assertEqual(self._get(f"/api/postits/{n['id']}").status_code, 200)

    def test_corbeille_restaure_avec_sous_pages(self):
        p = self._creer(title="Parent", sur_ecran=0)
        e = self._creer(title="Enfant", sur_ecran=0, parent_id=p["id"])
        with patch("app.routers.postit.get_current_user", return_value={"id": 1}):
            self.assertEqual(self.c.delete(f"/api/postits/{p['id']}").json()["nb"], 2)
            vivants = {n["id"] for n in self.c.get("/api/postits/notes").json()["notes"]}
            jetes = {n["id"] for n in self.c.get("/api/postits/notes?corbeille=1").json()["notes"]}
            self.assertFalse({p["id"], e["id"]} & vivants)
            self.assertTrue({p["id"], e["id"]} <= jetes)
            self.assertEqual(self.c.post(f"/api/postits/{p['id']}/restaurer").status_code, 200)
            vivants = {n["id"] for n in self.c.get("/api/postits/notes").json()["notes"]}
        self.assertTrue({p["id"], e["id"]} <= vivants)

    def test_suppression_definitive_exige_la_corbeille(self):
        n = self._creer(title="Définitif", sur_ecran=0)
        with patch("app.routers.postit.get_current_user", return_value={"id": 1}):
            self.assertEqual(self.c.delete(f"/api/postits/{n['id']}/definitif").status_code, 400)
            self.c.delete(f"/api/postits/{n['id']}")
            self.assertEqual(self.c.delete(f"/api/postits/{n['id']}/definitif").status_code, 200)
            self.assertEqual(self.c.get(f"/api/postits/{n['id']}").status_code, 404)

    def test_pas_de_cycle(self):
        a = self._creer(title="A", sur_ecran=0)
        b = self._creer(title="B", sur_ecran=0, parent_id=a["id"])
        with patch("app.routers.postit.get_current_user", return_value={"id": 1}):
            r = self.c.patch(f"/api/postits/{a['id']}", json={"parent_id": b["id"]})
        self.assertEqual(r.status_code, 400)

    def test_notes_personnelles(self):
        n = self._creer(title="Privée", sur_ecran=0)
        self.assertEqual(self._get(f"/api/postits/{n['id']}", uid=2).status_code, 404)
        autres = {x["id"] for x in self._get("/api/postits/notes", uid=2).json()["notes"]}
        self.assertNotIn(n["id"], autres)
        with patch("app.routers.postit.get_current_user", return_value={"id": 2}):
            r = self.c.post("/api/postits", json={"type": "someday", "title": "x", "parent_id": n["id"]})
        # 404 et non 403 : on ne révèle pas qu'une note non partagée existe.
        self.assertEqual(r.status_code, 404)

    def test_bloc_page(self):
        n = self._creer(title="Avec lien", sur_ecran=0)
        with patch("app.routers.postit.get_current_user", return_value={"id": 1}):
            r = self.c.patch(f"/api/postits/{n['id']}", json={"blocs": [{"type": "page", "texte": "Sous", "ref": "12"}]})
        self.assertEqual(sans_uid(r.json()["blocs"]), [{"type": "page", "texte": "Sous", "ref": 12}])

    def test_dossier_virtuel_de_l_explorateur(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.routers.qualite_ged import router as ged

        n = self._creer(title="Dans la GED", sur_ecran=0)
        app = FastAPI()
        app.include_router(ged)
        c = TestClient(app)
        user = {"id": 1, "role": "direction"}
        with patch("app.routers.qualite_ged.get_current_user", return_value=user):
            racine = c.get("/api/qualite/ged/folders/0").json()
            dossier = c.get("/api/qualite/ged/folders/-1").json()
        self.assertEqual(racine["folders"][0]["virtuel"], "notes")
        self.assertEqual(dossier["breadcrumb"], [{"id": -1, "nom": "Mes notes"}])
        lignes = {f["id"]: f for f in dossier["files"]}
        self.assertIn(n["id"], lignes)
        self.assertEqual(lignes[n["id"]]["lien"], f"/note?note={n['id']}")
        with patch("app.routers.qualite_ged.get_current_user", return_value={"id": 2, "role": "direction"}):
            autre = c.get("/api/qualite/ged/folders/-1").json()
        self.assertNotIn(n["id"], {f["id"] for f in autre["files"]})


class TestCollaboration(TestMesNotes):
    """Partage, opérations par bloc, flux temps réel, texte riche, images."""

    def _as(self, uid, methode, url, **kw):
        with patch("app.routers.postit.get_current_user", return_value={"id": uid}):
            return getattr(self.c, methode)(url, **kw)

    def _note_partagee(self, droit="ecrire"):
        n = self._creer(title="Commune", sur_ecran=0,
                        blocs=[{"uid": "a1", "type": "p", "texte": "un"}, {"uid": "b2", "type": "p", "texte": "deux"}])
        r = self._as(1, "put", f"/api/postits/{n['id']}/partages", json={"user_id": 2, "droit": droit})
        self.assertEqual(r.status_code, 200, r.text)
        return n

    def test_partage_donne_acces_a_l_invite(self):
        n = self._note_partagee()
        r = self._as(2, "get", f"/api/postits/{n['id']}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["droit"], "ecrire")
        partagees = self._as(2, "get", "/api/postits/notes").json()["partagees"]
        self.assertIn(n["id"], {x["id"] for x in partagees})

    def test_partage_couvre_les_sous_pages(self):
        n = self._note_partagee()
        sous = self._creer(uid=2, title="Sous de l'invité", sur_ecran=0, parent_id=n["id"])
        self.assertEqual(sous["user_id"], 1)  # rangée chez l'auteur de la note
        self.assertEqual(self._as(2, "get", f"/api/postits/{sous['id']}").status_code, 200)

    def test_lecture_seule_refuse_l_ecriture(self):
        n = self._note_partagee("lire")
        r = self._as(2, "post", f"/api/postits/{n['id']}/frappe",
                     json={"client": "x", "ops": [{"t": "set", "bloc": {"uid": "a1", "type": "p", "texte": "pirate"}}]})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self._as(2, "put", f"/api/postits/{n['id']}/partages", json={"user_id": 1}).status_code, 403)

    def test_ops_et_flux(self):
        n = self._note_partagee()
        rev0 = self._as(1, "get", f"/api/postits/{n['id']}").json()["revision"]
        ops = [
            {"t": "set", "bloc": {"uid": "a1", "type": "h2", "texte": "Titre"}},
            {"t": "ins", "apres": "a1", "bloc": {"uid": "c3", "type": "todo", "texte": "Nouveau"}},
            {"t": "mov", "uid": "b2", "apres": None},
            {"t": "del", "uid": "inexistant"},
            {"t": "titre", "titre": "Commune v2"},
        ]
        r = self._as(2, "post", f"/api/postits/{n['id']}/frappe", json={"client": "c-invite", "ops": ops})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["appliquees"], 4)
        note = self._as(1, "get", f"/api/postits/{n['id']}").json()
        self.assertEqual([b["uid"] for b in note["blocs"]], ["b2", "a1", "c3"])
        self.assertEqual(note["title"], "Commune v2")
        f = self._as(1, "get", f"/api/postits/{n['id']}/flux?depuis={rev0}&client=c-auteur").json()
        self.assertEqual(len(f["ops"]), 4)
        self.assertEqual(f["ops"][0]["client"], "c-invite")
        self.assertFalse(f["reset"])
        # Présence : l'invité, vu par l'auteur.
        self._as(2, "get", f"/api/postits/{n['id']}/flux?depuis={f['revision']}&client=c-invite&bloc=a1&sig=x")
        f2 = self._as(1, "get", f"/api/postits/{n['id']}/flux?depuis={f['revision']}&client=c-auteur&sig=x").json()
        self.assertIn({"client": "c-invite", "bloc": "a1"}, [{"client": p["client"], "bloc": p["bloc"]} for p in f2["presences"]])

    def test_patch_complet_force_le_rechargement(self):
        n = self._note_partagee()
        rev = self._as(1, "get", f"/api/postits/{n['id']}").json()["revision"]
        self._as(1, "patch", f"/api/postits/{n['id']}", json={"blocs": [{"type": "p", "texte": "neuf"}]})
        f = self._as(2, "get", f"/api/postits/{n['id']}/flux?depuis={rev}&client=z").json()
        self.assertTrue(f["reset"])

    def test_html_assaini(self):
        from app.services.notes import assainir_html, normaliser_blocs

        self.assertEqual(assainir_html('<b>gras</b> <script>alert(1)</script><i onclick="x">it</i>'),
                         "<b>gras</b> alert(1)<i>it</i>")
        self.assertEqual(assainir_html('<a href="javascript:alert(1)">x</a>'), "x")
        self.assertEqual(assainir_html('<a href="https://sifa.fr" target="_blank">site</a>'),
                         '<a href="https://sifa.fr">site</a>')
        self.assertEqual(assainir_html("<strong>a<em>b</strong>"), "<b>a<i>b</i></b>")
        b = normaliser_blocs([{"type": "p", "html": "<u>sous</u>ligné &amp; <img src=x onerror=1>"}])[0]
        self.assertEqual(b["html"], "<u>sous</u>ligné &amp; ")
        self.assertEqual(b["texte"], "sousligné & ")
        brut = normaliser_blocs([{"type": "p", "html": "sans mise en forme"}])[0]
        self.assertNotIn("html", brut)

    def test_image_controlee_et_protegee(self):
        import tempfile as _tf

        n = self._creer(title="Image", sur_ecran=0)
        png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
        with patch("app.routers.postit.UPLOAD_DIR", _tf.mkdtemp()):
            r = self._as(1, "post", f"/api/postits/{n['id']}/images", files={"fichier": ("a.png", png, "image/png")})
            self.assertEqual(r.status_code, 200, r.text)
            url = r.json()["url"]
            self.assertEqual(self._as(1, "get", url).status_code, 200)
            self.assertEqual(self._as(2, "get", url).status_code, 404)
            svg = b"<svg onload=alert(1)></svg>"
            r = self._as(1, "post", f"/api/postits/{n['id']}/images", files={"fichier": ("a.svg", svg, "image/svg+xml")})
            self.assertEqual(r.status_code, 400)


class TestIncidentPromotion(unittest.TestCase):
    """12/11/2026 : contenu renvoyé en entier par une page désynchronisée."""

    def test_set_sur_bloc_inconnu_ignore(self):
        import json as _json

        from database import get_db
        from app.services.notes import appliquer_ops

        with get_db() as conn:
            conn.execute("INSERT OR IGNORE INTO users (id, email, nom, password_hash, role, actif, created_at) "
                         "VALUES (1, 'test@local', 'Test', 'x', 'direction', 1, '2026-01-01')")
            pid = conn.execute("INSERT INTO postits (user_id, type, title, contenu) VALUES (1,'someday','I',?)",
                               (_json.dumps([{"uid": "a", "type": "p", "texte": "A"}]),)).lastrowid
            conn.commit()
            appliquer_ops(conn, pid, 1, "x", [{"t": "set", "bloc": {"uid": "zz", "type": "p", "texte": "A"}}])
            blocs = _json.loads(conn.execute("SELECT contenu FROM postits WHERE id=?", (pid,)).fetchone()[0])
        self.assertEqual([b["uid"] for b in blocs], ["a"])

    def test_reparation_retire_les_copies_exactes(self):
        import importlib
        import json as _json

        from database import get_db

        mig = importlib.import_module("app.core.migrations.2026_11_12_notes_doublons_promotion")
        d = [{"uid": "x1", "type": "h2", "texte": "Titre"}, {"uid": "x2", "type": "p", "texte": "Texte"},
             {"uid": "x3", "type": "p", "texte": "Modifié depuis"}]
        o = [{"uid": "a1", "type": "h2", "texte": "Titre"}, {"uid": "a2", "type": "p", "texte": "Texte"},
             {"uid": "a3", "type": "p", "texte": "Original"}]
        with get_db() as conn:
            conn.execute("INSERT OR IGNORE INTO users (id, email, nom, password_hash, role, actif, created_at) "
                         "VALUES (1, 'test@local', 'Test', 'x', 'direction', 1, '2026-01-01')")
            pid = conn.execute("INSERT INTO postits (user_id, type, title, contenu, revision) VALUES (1,'someday','D',?,3)",
                               (_json.dumps(d + o, ensure_ascii=False),)).lastrowid
            for i, b in enumerate(d, 1):
                conn.execute("INSERT INTO note_ops (note_id, revision, user_id, client, op, cree_le) VALUES (?,?,?,?,?,?)",
                             (pid, i, 1, "c", _json.dumps({"t": "ins", "apres": None, "bloc": b}), "2026-11-12T11:15:17"))
            conn.commit()
            mig.appliquer(conn)
            mig.appliquer(conn)
            blocs = _json.loads(conn.execute("SELECT contenu FROM postits WHERE id=?", (pid,)).fetchone()[0])
            dernier = conn.execute("SELECT op FROM note_ops WHERE note_id=? ORDER BY revision DESC LIMIT 1", (pid,)).fetchone()[0]
        self.assertEqual([b["uid"] for b in blocs], ["x3", "a1", "a2", "a3"])
        self.assertEqual(_json.loads(dernier), {"t": "reset"})


class TestOutilsNotes(TestMesNotes):
    """Historique, modèles, favoris et récentes, commentaires, liens @, export."""

    def setUp(self):
        super().setUp()
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.routers.notes_outils import router as outils
        from app.routers.postit import router as postit

        app = FastAPI()
        app.include_router(outils)
        app.include_router(postit)
        self.c = TestClient(app)

    def _as(self, uid, methode, url, **kw):
        with patch("app.routers.postit.get_current_user", return_value={"id": uid, "nom": f"U{uid}"}), \
             patch("app.routers.notes_outils.get_current_user", return_value={"id": uid, "nom": f"U{uid}", "role": "direction"}):
            return getattr(self.c, methode)(url, **kw)

    def test_historique_et_restauration(self):
        from database import get_db

        n = self._creer(title="Hist", sur_ecran=0, blocs=[{"uid": "a", "type": "p", "texte": "v1"}])
        with get_db() as conn:  # une photo existe déjà depuis plus de 10 minutes
            conn.execute("DELETE FROM note_versions WHERE note_id=?", (n["id"],))
            conn.commit()
        self._as(1, "post", f"/api/postits/{n['id']}/frappe",
                 json={"client": "x", "ops": [{"t": "set", "bloc": {"uid": "a", "type": "p", "texte": "v2"}}]})
        versions = self._as(1, "get", f"/api/postits/{n['id']}/versions").json()["versions"]
        self.assertEqual(len(versions), 1)
        v = self._as(1, "get", f"/api/postits/{n['id']}/versions/{versions[0]['id']}").json()
        self.assertEqual(v["blocs"][0]["texte"], "v1")
        self.assertEqual(self._as(1, "post", f"/api/postits/{n['id']}/versions/{versions[0]['id']}/restaurer").status_code, 200)
        note = self._as(1, "get", f"/api/postits/{n['id']}").json()
        self.assertEqual(note["blocs"][0]["texte"], "v1")
        self.assertEqual(len(self._as(1, "get", f"/api/postits/{n['id']}/versions").json()["versions"]), 2)
        self.assertEqual(self._as(2, "get", f"/api/postits/{n['id']}/versions").status_code, 404)

    def test_modeles(self):
        communs = self._as(1, "get", "/api/postits/modeles").json()
        self.assertTrue(any(m["commun"] and m["nom"] == "Réunion" for m in communs))
        n = self._creer(title="Trame", sur_ecran=0, blocs=[{"type": "h2", "texte": "Ma trame"}])
        r = self._as(1, "post", "/api/postits/modeles", json={"note_id": n["id"], "nom": "Ma trame"})
        self.assertEqual(r.status_code, 200)
        mid = r.json()["id"]
        self.assertNotIn(mid, [m["id"] for m in self._as(2, "get", "/api/postits/modeles").json()])
        self.assertEqual(self._as(2, "delete", f"/api/postits/modeles/{mid}").status_code, 404)
        self.assertEqual(self._as(1, "delete", f"/api/postits/modeles/{mid}").status_code, 200)

    def test_favoris_recentes(self):
        n = self._creer(title="Fav", sur_ecran=0)
        self._as(1, "put", f"/api/postits/{n['id']}/favori", json={"favori": True})
        self._as(1, "post", f"/api/postits/{n['id']}/consultee")
        d = self._as(1, "get", "/api/postits/raccourcis").json()
        self.assertIn(n["id"], [f["id"] for f in d["favoris"]])
        self.assertIn(n["id"], [r["id"] for r in d["recentes"]])
        self.assertEqual(self._as(2, "put", f"/api/postits/{n['id']}/favori", json={"favori": True}).status_code, 404)

    def test_commentaires_et_mentions(self):
        n = self._creer(title="Com", sur_ecran=0, blocs=[{"uid": "b1", "type": "p", "texte": "texte"}])
        with patch("app.routers.push.send_push_safe") as push:
            r = self._as(1, "post", f"/api/postits/{n['id']}/commentaires",
                         json={"texte": "@U2 regarde", "bloc_uid": "b1", "citation": "texte", "mentions": [2]})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(len(r.json()["sans_acces"]), 1)  # U2 n'a pas accès : pas de notification
        push.assert_not_called()
        self._as(1, "put", f"/api/postits/{n['id']}/partages", json={"user_id": 2, "droit": "lire"})
        with patch("app.routers.push.send_push_safe") as push:
            r = self._as(1, "post", f"/api/postits/{n['id']}/commentaires", json={"texte": "@U2 et maintenant ?", "mentions": [2]})
        push.assert_called_once()
        self.assertEqual(len(self._as(2, "get", "/api/postits/raccourcis").json()["mentions"]), 1)
        coms = self._as(2, "get", f"/api/postits/{n['id']}/commentaires").json()["commentaires"]
        self.assertEqual(len(coms), 2)
        self.assertEqual(self._as(2, "get", "/api/postits/raccourcis").json()["mentions"], [])  # lues
        # Lecture seule : on commente, mais on ne résout pas le fil d'un autre.
        cid = coms[0]["id"]
        self.assertEqual(self._as(2, "patch", f"/api/postits/{n['id']}/commentaires/{cid}", json={"resolu": True}).status_code, 403)
        rep = self._as(2, "post", f"/api/postits/{n['id']}/commentaires", json={"texte": "Vu", "parent_id": cid})
        self.assertEqual(rep.json()["bloc_uid"], "b1")
        self.assertEqual(self._as(1, "patch", f"/api/postits/{n['id']}/commentaires/{cid}", json={"resolu": True}).status_code, 200)
        self.assertEqual(self._as(1, "delete", f"/api/postits/{n['id']}/commentaires/{cid}").status_code, 200)
        restants = self._as(1, "get", f"/api/postits/{n['id']}/commentaires").json()["commentaires"]
        self.assertEqual(len(restants), 1)

    def test_references(self):
        n = self._creer(title="Référence unique zz", sur_ecran=0)
        with patch("app.routers.notes_outils.user_has_app_access", return_value=False):
            d = self._as(1, "get", "/api/postits/references?q=unique zz").json()["resultats"]
        self.assertEqual(d[0]["url"], f"/note?note={n['id']}")
        with patch("app.routers.notes_outils.user_has_app_access", return_value=False):
            self.assertEqual(self._as(2, "get", "/api/postits/references?q=unique zz").json()["resultats"], [])

    def test_references_dossier_client(self):
        from database import get_db

        with get_db() as conn:
            mid = conn.execute("SELECT id FROM machines ORDER BY id LIMIT 1").fetchone()
            mid = mid[0] if mid else 1
            pid = conn.execute("INSERT INTO planning_entries (machine_id, position, reference, client, description) VALUES (?,?,?,?,?)",
                               (mid, 9999, "ZZ-4521", "Client Test", "Étiquettes")).lastrowid
            cid = conn.execute("INSERT INTO clients (raison_sociale, code, ville, created_at, updated_at) VALUES (?,?,?,?,?)",
                               ("Zzclient SA", "ZZC", "Lyon", "2026-11-13", "2026-11-13")).lastrowid
            conn.commit()
        with patch("app.routers.notes_outils.user_has_app_access", side_effect=lambda u, a: a == "prod"):
            d = self._as(1, "get", "/api/postits/references?q=ZZ-45").json()["resultats"]
        self.assertIn({"type": "dossier", "libelle": "ZZ-4521", "url": "/prod?page=traceabilite&dossier=ZZ-4521"},
                      [{k: x[k] for k in ("type", "libelle", "url")} for x in d])
        with patch("app.routers.notes_outils.user_has_app_access", side_effect=lambda u, a: a == "planning"):
            d = self._as(1, "get", "/api/postits/references?q=ZZ-45").json()["resultats"]
        self.assertEqual([x["url"] for x in d if x["type"] == "dossier"], [f"/planning?machine={mid}&dossier={pid}"])
        with patch("app.routers.notes_outils.user_has_app_access", return_value=False), \
             patch("app.routers.notes_outils.can_access_settings", return_value=True), \
             patch("app.routers.notes_outils.can_access_settings_contacts", return_value=True):
            d = self._as(1, "get", "/api/postits/references?q=Zzclient").json()["resultats"]
        self.assertEqual([x["url"] for x in d if x["type"] == "client"], [f"/settings?onglet=clients&client={cid}"])
        with patch("app.routers.notes_outils.user_has_app_access", return_value=False), \
             patch("app.routers.notes_outils.can_access_settings", return_value=False):
            d = self._as(1, "get", "/api/postits/references?q=Zzclient").json()["resultats"]
        self.assertEqual([x for x in d if x["type"] in ("client", "dossier")], [])

    def test_exports(self):
        n = self._creer(title="Export", sur_ecran=0, blocs=[
            {"type": "h2", "texte": "Titre → suite"}, {"type": "todo", "texte": "a", "coche": True},
            {"type": "tableau", "entete": True, "lignes": [["A", "B"], ["<b>1</b>", "2"]]}])
        pdf = self._as(1, "get", f"/api/postits/{n['id']}/export.pdf")
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertIn("attachment", pdf.headers["content-disposition"])
        n2 = self._creer(title="Cœur → suite", sur_ecran=0)
        r2 = self._as(1, "get", f"/api/postits/{n2['id']}/export.pdf")
        self.assertEqual(r2.status_code, 200)
        self.assertIn("filename*=UTF-8''", r2.headers["content-disposition"])
        doc = self._as(1, "get", f"/api/postits/{n['id']}/export.docx")
        self.assertTrue(doc.content.startswith(b"PK"))
        self.assertEqual(self._as(2, "get", f"/api/postits/{n['id']}/export.pdf").status_code, 404)

    def test_impression_reseau_note(self):
        from app.routers.print import _fetch_pdf_bytes

        n = self._creer(title="Imprimer", sur_ecran=0, blocs=[{"type": "p", "texte": "x"}])
        pdf, nom = _fetch_pdf_bytes("note", n["id"], {"id": 1})
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(nom, "Imprimer.pdf")
        from fastapi import HTTPException
        with self.assertRaises(HTTPException):
            _fetch_pdf_bytes("note", n["id"], {"id": 2})


if __name__ == "__main__":
    unittest.main()
