"""
MyPrint — création d'une étiquette depuis une photo (POST /ia/depuis-photo).

Lancer : python3 tests/test_etiq_depuis_photo.py

Ce que le test verrouille :
1. Refus sans fichier, refus d'un format que l'assistant ne lit pas.
2. Un modèle IA hors liste est refusé avant toute lecture.
3. Création : l'étiquette est enregistrée dans le dossier avec la mise en
   page rendue par l'assistant (simulé), sans demande rattachée, et la photo
   source est conservée et téléchargeable.
4. Sans format fourni, l'assistant est appelé en format libre ; avec un
   format, celui-ci est imposé.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_tmp = tempfile.mkdtemp(prefix="mysifa_etiq_photo_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import database  # noqa: E402,F401  — d'abord, toujours (CLAUDE.md)
from database import get_db  # noqa: E402

USER = {"id": 1, "email": "op@test.local", "nom": "Op", "role": "fabrication"}
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 200


def _client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers import print_specifiques as ps
    app = FastAPI()
    app.include_router(ps.router)
    return TestClient(app), ps


def _faux_proposer(appels):
    def proposer(consigne, l, h, dpi, layout, pieces=None, contexte="", modele=None, format_libre=False):
        appels.append({"consigne": consigne, "l": l, "h": h, "pieces": pieces, "contexte": contexte,
                       "modele": modele, "format_libre": format_libre})
        return {
            "largeur_mm": 100.0, "hauteur_mm": 50.0,
            "layout": {"elements": [{"id": "e1", "type": "texte", "x": 3, "y": 3, "valeur": "Lot {{lot}}"}],
                       "variables": [{"nom": "lot", "libelle": "Lot", "type": "saisie"}]},
            "resume": "Étiquette carton reproduite.", "remarques": ["Préfixe GS1 absent."],
            "modele": "claude-sonnet-5-5", "modele_libelle": "Claude Sonnet 5.5",
            "modele_reel": "claude-sonnet-5-5",
        }
    return proposer


class TestDepuisPhoto(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client, cls.ps = _client()
        cls.sources = os.path.join(_tmp, "sources")
        cls._p_sources = patch.object(cls.ps, "_SOURCES_DIR", cls.sources)
        cls._p_user = patch.object(cls.ps, "get_current_user", return_value=USER)
        cls._p_sources.start()
        cls._p_user.start()
        with get_db() as conn:
            cur = conn.execute("INSERT INTO etiq_dossiers (nom,created_at,created_by) VALUES ('Client X','2026-10-21T08:00:00','t')")
            cls.dossier = cur.lastrowid
            conn.commit()

    @classmethod
    def tearDownClass(cls):
        cls._p_sources.stop()
        cls._p_user.stop()

    def _post(self, fichiers=None, **champs):
        data = {"consigne": "La référence et le lot changent à chaque impression.", "nom": "Carton X",
                "dossier_id": str(self.dossier)}
        data.update({k: v for k, v in champs.items() if v is not None})
        return self.client.post("/api/print/specifiques/ia/depuis-photo", data=data, files=fichiers or [])

    def test_sans_fichier(self):
        r = self._post()
        self.assertEqual(r.status_code, 400)
        self.assertIn("Joindre au moins une photo", r.json()["detail"])

    def test_mauvais_type(self):
        r = self._post([("fichiers", ("cdc.docx", b"PK..", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))])
        self.assertEqual(r.status_code, 400)
        self.assertIn("format non accepté", r.json()["detail"])

    def test_modele_inconnu(self):
        appels = []
        with patch("app.services.etiq_specifiques_ia.proposer", _faux_proposer(appels)):
            r = self._post([("fichiers", ("a.jpg", JPEG, "image/jpeg"))], modele="gpt-quelconque")
        self.assertEqual(r.status_code, 400)
        self.assertIn("non proposé", r.json()["detail"])
        self.assertEqual(appels, [])

    def test_consigne_obligatoire(self):
        r = self._post([("fichiers", ("a.jpg", JPEG, "image/jpeg"))], consigne="  ")
        self.assertEqual(r.status_code, 400)

    def test_creation_format_libre(self):
        appels = []
        with patch("app.services.etiq_specifiques_ia.proposer", _faux_proposer(appels)):
            r = self._post([("fichiers", ("photo.jpg", JPEG, "image/jpeg"))])
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["remarques"], ["Préfixe GS1 absent."])
        self.assertEqual(len(appels), 1)
        self.assertTrue(appels[0]["format_libre"])
        self.assertIn("à déduire", appels[0]["contexte"])
        self.assertEqual(appels[0]["pieces"][0]["mime"], "image/jpeg")
        with get_db() as conn:
            row = conn.execute("SELECT * FROM etiq_modeles WHERE id=?", (body["modele_id"],)).fetchone()
        self.assertEqual(row["dossier_id"], self.dossier)
        self.assertIsNone(row["demande_id"])
        self.assertEqual((row["largeur_mm"], row["hauteur_mm"]), (100.0, 50.0))
        self.assertIn("À vérifier : Préfixe GS1 absent.", row["description"])
        self.assertIn("{{lot}}", row["layout_json"])
        # Photo source conservée, listée et téléchargeable
        m = self.client.get(f"/api/print/specifiques/modeles/{body['modele_id']}").json()
        self.assertEqual(len(m["sources"]), 1)
        f = self.client.get(m["sources"][0]["url"])
        self.assertEqual(f.status_code, 200)
        self.assertEqual(f.content, JPEG)
        # Un nom hors motif ou d'une autre étiquette est refusé
        self.assertEqual(self.client.get(
            f"/api/print/specifiques/modeles/{body['modele_id']}/sources/..%2Ftest.db").status_code, 404)
        autre = m["sources"][0]["fichier"].replace(f"source_{body['modele_id']}_", "source_999999_")
        self.assertEqual(self.client.get(
            f"/api/print/specifiques/modeles/{body['modele_id']}/sources/{autre}").status_code, 404)

    def test_creation_format_impose(self):
        appels = []
        with patch("app.services.etiq_specifiques_ia.proposer", _faux_proposer(appels)):
            r = self._post([("fichiers", ("bl.pdf", b"%PDF-1.4", "application/pdf"))],
                           largeur_mm="148", hauteur_mm="105")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertFalse(appels[0]["format_libre"])
        self.assertIn("148 × 105 mm", appels[0]["contexte"])
        with get_db() as conn:
            row = conn.execute("SELECT largeur_mm,hauteur_mm FROM etiq_modeles WHERE id=?",
                               (r.json()["modele_id"],)).fetchone()
        self.assertEqual((row["largeur_mm"], row["hauteur_mm"]), (148.0, 105.0))

    def test_format_incomplet(self):
        r = self._post([("fichiers", ("a.jpg", JPEG, "image/jpeg"))], largeur_mm="100")
        self.assertEqual(r.status_code, 400)

    def test_dossier_inconnu(self):
        r = self._post([("fichiers", ("a.jpg", JPEG, "image/jpeg"))], dossier_id="987654")
        self.assertEqual(r.status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
