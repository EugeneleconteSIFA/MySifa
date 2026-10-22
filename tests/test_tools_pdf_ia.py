"""
MyTools › Éditeur PDF — fonctions IA (app/services/pdf_ia.py).

Lancer : python3 tests/test_tools_pdf_ia.py

Sans appel réseau : le client Anthropic est remplacé par un faux qui rend une
réponse préparée. Verrouille l'envoi du PDF en bloc document, la remise en
forme des tableaux extraits, le bornage des champs détectés, les messages
d'erreur (clé absente, refus, réponse tronquée) et l'enregistrement dans
ia_usage sous la fonction « pdf ».
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

_tmp = tempfile.mkdtemp(prefix="mysifa_pdf_ia_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import database  # noqa: E402,F401  — d'abord, toujours (CLAUDE.md)
from app.services import ia_usage, pdf_ia  # noqa: E402

PDF = b"%PDF-1.7\n%test\n"


class FauxClient:
    def __init__(self, texte="", raison="end_turn"):
        self.texte, self.raison, self.appels = texte, raison, []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.appels.append(kw)
        return SimpleNamespace(
            content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=self.texte)],
            stop_reason=self.raison, model=kw["model"],
            usage=SimpleNamespace(input_tokens=1200, output_tokens=80, cache_read_input_tokens=0, cache_creation_input_tokens=0))


class Base(unittest.TestCase):
    def brancher(self, texte="", raison="end_turn"):
        self.client = FauxClient(texte, raison)
        self._orig = pdf_ia._client
        pdf_ia._client = lambda: self.client

    def tearDown(self):
        if hasattr(self, "_orig"):
            pdf_ia._client = self._orig


class Appels(Base):
    def test_resume_envoie_le_pdf_en_document(self):
        self.brancher("Résumé.")
        r = pdf_ia.resumer(PDF)
        self.assertEqual(r, {"texte": "Résumé."})
        kw = self.client.appels[0]
        bloc = kw["messages"][0]["content"][0]
        self.assertEqual(bloc["type"], "document")
        self.assertEqual(bloc["source"]["media_type"], "application/pdf")
        self.assertEqual(kw["extra_body"]["fallbacks"], "default")
        self.assertEqual(kw["extra_body"]["output_config"]["effort"], "medium")

    def test_extraction_tableau_normalise(self):
        self.brancher(json.dumps({"colonnes": ["Réf", "Qté"], "lignes": [["A1"], ["B2", "3", "en trop"]], "remarques": ""}))
        r = pdf_ia.extraire(PDF, "facture")
        self.assertEqual(r["lignes"], [["A1", ""], ["B2", "3"]])
        self.assertIn("format", self.client.appels[0]["extra_body"]["output_config"])

    def test_champs_bornes_et_noms(self):
        self.brancher(json.dumps({"champs": [
            {"page": 1, "nom": "Nom.client", "type": "texte", "x": -5, "y": 100, "l": 300, "h": 30, "options": []},
            {"page": 2, "nom": "Minuscule", "type": "case", "x": 10, "y": 10, "l": 1, "h": 1, "options": []},
            {"page": 1, "nom": "Choix", "type": "inconnu", "x": 900, "y": 990, "l": 500, "h": 20, "options": ["A"]},
        ]}))
        r = pdf_ia.champs(PDF)["champs"]
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0]["nom"], "Nom client")
        self.assertEqual(r[0]["x"], 0.0)
        self.assertEqual(r[1]["type"], "texte")

    def test_type_de_document_inconnu(self):
        self.brancher("{}")
        with self.assertRaises(pdf_ia.PdfIaErreur):
            pdf_ia.extraire(PDF, "devis")

    def test_question_vide(self):
        self.brancher("x")
        with self.assertRaises(pdf_ia.PdfIaErreur):
            pdf_ia.question(PDF, "   ")


class Erreurs(Base):
    def test_cle_absente(self):
        self._orig = pdf_ia._client
        pdf_ia._client = lambda: None
        with self.assertRaisesRegex(pdf_ia.PdfIaErreur, "ANTHROPIC_API_KEY"):
            pdf_ia.resumer(PDF)

    def test_refus(self):
        self.brancher("", raison="refusal")
        with self.assertRaisesRegex(pdf_ia.PdfIaErreur, "refusé"):
            pdf_ia.resumer(PDF)

    def test_tronque(self):
        self.brancher("début", raison="max_tokens")
        with self.assertRaisesRegex(pdf_ia.PdfIaErreur, "tronquée"):
            pdf_ia.resumer(PDF)


class Suivi(Base):
    def test_appel_compte_dans_le_suivi(self):
        self.brancher("ok")
        with ia_usage.suivi({"id": 7, "nom": "Test"}, "pdf", "MyTools") as s:
            pdf_ia.resumer(PDF)
        self.assertEqual(s.nb_appels, 1)
        self.assertEqual(s.entree, 1200)
        self.assertEqual(s.nb_fichiers, 1)
        self.assertIn("pdf", ia_usage.FONCTIONS)


class Lot4(Base):
    def test_selection_texte_seul(self):
        self.brancher("Explication.")
        r = pdf_ia.selection("Article 3 : le preneur s'oblige…", "expliquer")
        self.assertEqual(r["texte"], "Explication.")
        contenu = self.client.appels[0]["messages"][0]["content"]
        self.assertFalse(any(b.get("type") == "document" for b in contenu))

    def test_contrats_deux_documents(self):
        self.brancher("CLAUSES MODIFIÉES")
        pdf_ia.contrats(PDF, PDF)
        contenu = self.client.appels[0]["messages"][0]["content"]
        self.assertEqual(sum(1 for b in contenu if b.get("type") == "document"), 2)

    def test_bat_rapport(self):
        self.brancher(json.dumps({"points": [{"sujet": "Format", "attendu": "50×30", "constate": "50×30", "statut": "conforme", "page": 1}],
                                  "synthese": "Conforme."}))
        r = pdf_ia.bat(PDF, {"reference": "ETQ-1", "format": "50x30", "champs_manuels": "[]", "support_ref_id": 4})
        self.assertEqual(r["points"][0]["statut"], "conforme")
        texte = self.client.appels[0]["messages"][0]["content"][1]["text"]
        self.assertIn("ETQ-1", texte)
        self.assertNotIn("support_ref_id", texte)

    def test_remplir_ne_garde_que_les_champs_du_modele(self):
        self.brancher(json.dumps({"valeurs": [{"nom": "client", "valeur": "ACME"}, {"nom": "intrus", "valeur": "x"}]}))
        r = pdf_ia.remplir(PDF, [{"nom": "client", "type": "texte"}], "Client : ACME")
        self.assertEqual(r["valeurs"], {"client": "ACME"})


class Actions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from unittest.mock import patch
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.routers import tools_pdf
        app = FastAPI()
        app.include_router(tools_pdf.router)
        cls.client = TestClient(app)
        cls.patch = patch.object(tools_pdf, "get_current_user", return_value={"id": 42, "nom": "Test"})
        cls.patch.start()

    @classmethod
    def tearDownClass(cls):
        cls.patch.stop()

    def test_cycle_action(self):
        r = self.client.put("/api/tools/pdf/actions", json={"nom": "Envoi client", "etapes": [{"type": "filigrane", "p": {"texte": "COPIE"}}, {"type": "inconnu"}]})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(len(r.json()["etapes"]), 1)
        aid = r.json()["id"]
        r2 = self.client.put("/api/tools/pdf/actions", json={"nom": "Envoi client", "etapes": [{"type": "ocr"}]})
        self.assertEqual(r2.json()["id"], aid, "même nom : remplacée, pas dupliquée")
        l = self.client.get("/api/tools/pdf/actions").json()["actions"]
        self.assertEqual([a["nom"] for a in l], ["Envoi client"])
        self.assertEqual(self.client.delete(f"/api/tools/pdf/actions/{aid}").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/tools/pdf/actions/{aid}").status_code, 404)

    def test_action_vide_refusee(self):
        r = self.client.put("/api/tools/pdf/actions", json={"nom": "Vide", "etapes": []})
        self.assertEqual(r.status_code, 400)

    def test_reglages(self):
        r = self.client.get("/api/tools/pdf/reglages").json()["preflight"]
        self.assertEqual(r["dpi_min"], 300)


if __name__ == "__main__":
    unittest.main(verbosity=1)
