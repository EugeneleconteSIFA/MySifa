"""
MyTools › Convertir — conversions serveur (app/services/conversion.py) et API.

Lancer : python3 tests/test_tools_convertir.py

Ce que le test verrouille (sans LibreOffice ni ffmpeg installés : les outils
système sont simulés) :
1. Type de fichier inconnu, mélange de types, cible non prise en charge : refus 400.
2. Outil absent du serveur : refus 503 avec le paquet à installer.
3. Plusieurs fichiers produits → un ZIP ; un seul → le fichier ; le dossier
   temporaire est toujours effacé.
4. Quota par heure et conversions simultanées.
5. L'API répond en pièce jointe et refuse sans session.
"""

import io
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

_tmp = tempfile.mkdtemp(prefix="mysifa_conv_test_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import database  # noqa: E402,F401  — d'abord, toujours (CLAUDE.md)
from app.services import conversion as cv  # noqa: E402

TOUS = {o: True for o in cv.OUTILS}


class Refus(unittest.TestCase):
    def test_type_inconnu(self):
        with self.assertRaises(cv.ConversionRefusee) as e:
            cv.convertir([("virus.exe", b"x")], "pdf", {})
        self.assertEqual(e.exception.code, 400)

    def test_melange(self):
        with patch.object(cv, "outils_disponibles", return_value={"outils": TOUS, "paquets": cv.OUTILS}):
            with self.assertRaises(cv.ConversionRefusee):
                cv.convertir([("a.docx", b"x"), ("b.mp3", b"y")], "pdf", {})

    def test_cible_non_prise_en_charge(self):
        with self.assertRaises(cv.ConversionRefusee):
            cv.convertir([("a.mp3", b"x")], "docx", {})

    def test_outil_absent(self):
        absent = dict(TOUS, soffice=False)
        with patch.object(cv, "outils_disponibles", return_value={"outils": absent, "paquets": cv.OUTILS}):
            with self.assertRaises(cv.ConversionRefusee) as e:
                cv.convertir([("a.docx", b"x")], "pdf", {})
        self.assertEqual(e.exception.code, 503)
        self.assertIn("libreoffice", str(e.exception))

    def test_nom_propre(self):
        self.assertEqual(cv.nom_propre("../../etc/passwd.docx"), "etc_passwd")
        self.assertEqual(cv.nom_propre("Devis client été 2026.xlsx"), "Devis client été 2026")


class Production(unittest.TestCase):
    def _faux(self, n_sorties):
        vus = {}

        def faux(f, cible, o, dossier, i):
            vus["dossier"] = dossier
            for k in range(n_sorties):
                with open(os.path.join(dossier, "out", f"{f['base']}-{k + 1}.{cible}"), "wb") as fh:
                    fh.write(b"contenu %d" % k)
        return faux, vus

    def test_un_fichier(self):
        faux, vus = self._faux(1)
        with patch.object(cv, "outils_disponibles", return_value={"outils": TOUS, "paquets": cv.OUTILS}), \
             patch.object(cv, "_convertir_un", faux):
            nom, octets, mime = cv.convertir([("Rapport.docx", b"x")], "pdf", {})
        self.assertEqual(nom, "Rapport-1.pdf")
        self.assertEqual(octets, b"contenu 0")
        self.assertFalse(os.path.exists(vus["dossier"]), "dossier temporaire non effacé")

    def test_zip(self):
        faux, vus = self._faux(3)
        with patch.object(cv, "outils_disponibles", return_value={"outils": TOUS, "paquets": cv.OUTILS}), \
             patch.object(cv, "_convertir_un", faux):
            nom, octets, mime = cv.convertir([("Diapos.pptx", b"x")], "png", {})
        self.assertEqual(mime, "application/zip")
        self.assertEqual(nom, "Diapos-png.zip")
        self.assertEqual(len(zipfile.ZipFile(io.BytesIO(octets)).namelist()), 3)
        self.assertFalse(os.path.exists(vus["dossier"]))

    def test_echec_efface_aussi(self):
        vus = {}

        def casse(f, cible, o, dossier, i):
            vus["dossier"] = dossier
            raise RuntimeError("ffmpeg a échoué")
        with patch.object(cv, "outils_disponibles", return_value={"outils": TOUS, "paquets": cv.OUTILS}), \
             patch.object(cv, "_convertir_un", casse):
            with self.assertRaises(RuntimeError):
                cv.convertir([("son.wav", b"x")], "mp3", {})
        self.assertFalse(os.path.exists(vus["dossier"]))


class Limites(unittest.TestCase):
    def setUp(self):
        cv._historique.clear()
        cv._en_cours = 0

    def test_paralleles(self):
        for _ in range(cv.CONVERTIR_PARALLELE):
            cv.reserver(f"u{_}")
        with self.assertRaises(cv.ConversionRefusee) as e:
            cv.reserver("autre")
        self.assertEqual(e.exception.code, 429)
        for _ in range(cv.CONVERTIR_PARALLELE):
            cv.liberer()
        cv.reserver("autre")
        cv.liberer()

    def test_quota(self):
        for _ in range(cv.CONVERTIR_PAR_HEURE):
            cv.reserver("u1")
            cv.liberer()
        with self.assertRaises(cv.ConversionRefusee):
            cv.reserver("u1")


class Api(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.routers import tools_convertir
        app = FastAPI()
        app.include_router(tools_convertir.router)
        cls.client = TestClient(app)
        cls.mod = tools_convertir

    def setUp(self):
        cv._historique.clear()
        cv._en_cours = 0

    def test_sans_session(self):
        r = self.client.get("/api/tools/convertir/outils")
        self.assertEqual(r.status_code, 401)

    def test_conversion_piece_jointe(self):
        with patch.object(self.mod, "get_current_user", return_value={"id": 1}), \
             patch.object(cv, "convertir", return_value=("été.pdf", b"%PDF", "application/octet-stream")):
            r = self.client.post("/api/tools/convertir", data={"cible": "pdf", "options": "{}"},
                                 files={"fichiers": ("été.docx", b"x")})
        self.assertEqual(r.status_code, 200)
        self.assertIn("attachment", r.headers["content-disposition"])
        self.assertIn("%C3%A9t%C3%A9.pdf", r.headers["content-disposition"])
        self.assertEqual(cv._en_cours, 0, "créneau de conversion non libéré")

    def test_echec_message_generique(self):
        with patch.object(self.mod, "get_current_user", return_value={"id": 1}), \
             patch.object(cv, "convertir", side_effect=RuntimeError("soffice: /tmp/secret")):
            r = self.client.post("/api/tools/convertir", data={"cible": "pdf"},
                                 files={"fichiers": ("a.docx", b"x")})
        self.assertEqual(r.status_code, 500)
        self.assertNotIn("/tmp", r.text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
