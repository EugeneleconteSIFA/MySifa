"""
Usage IA — origine et détail de chaque appel (Paramètres › Usage IA).

Lancer : python3 tests/test_ia_usage_detail.py

Ce que le test verrouille :
1. L'application et l'écran se déduisent de la page d'origine (MyTools ›
   Étiquettes › Étiquettes spécifiques…), à défaut de l'API appelée.
2. Un suivi ouvert pendant une requête enregistre page, API, application,
   écran, modèle demandé, fichiers joints, raison de fin ; hors requête,
   l'application vaut « Automatique ».
3. Une exception enregistre l'échec et son message (detail d'HTTPException).
4. Les filtres de la synthèse (utilisateur, application — y compris « non
   renseignée » —, fonction, modèle, statut) et la fiche d'un appel.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

_tmp = tempfile.mkdtemp(prefix="mysifa_ia_usage_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import database  # noqa: E402,F401  — d'abord, toujours (CLAUDE.md)
from database import get_db  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from app.core import requete_courante as rc  # noqa: E402
from app.services import ia_usage  # noqa: E402


def reponse(modele="claude-sonnet-5-5-20260101", e=1000, s=200, fin="end_turn"):
    return SimpleNamespace(model=modele, stop_reason=fin,
                           usage=SimpleNamespace(input_tokens=e, output_tokens=s,
                                                 cache_read_input_tokens=0, cache_creation_input_tokens=0))


class Origine(unittest.TestCase):
    def test_page_mytools(self):
        self.assertEqual(ia_usage.origine("/tools?outil=etiquettes&poste=specifiques", "/api/print/x"),
                         ("MyTools", "Étiquettes › Étiquettes spécifiques"))

    def test_page_stock(self):
        app, ecran = ia_usage.origine("/stock?tab=reception", "")
        self.assertEqual(app, "MyStock")
        self.assertEqual(ecran, "Reception")

    def test_api_seule(self):
        self.assertEqual(ia_usage.origine("", "/api/qualite/formulaires/ia/proposer"), ("MyQualité", ""))


class Enregistrement(unittest.TestCase):
    def setUp(self):
        with get_db() as c:
            c.execute("DELETE FROM ia_usage")
            c.commit()

    def _dans_requete(self, page, api, fn):
        jeton = rc._REQUETE.set({"api": api, "methode": "POST", "page": page})
        try:
            fn()
        finally:
            rc._REQUETE.reset(jeton)

    def test_detail_enregistre(self):
        def appel():
            with ia_usage.suivi({"id": 7, "nom": "Test", "role": "superadmin"}, "etiquettes", "photo"):
                ia_usage.noter(reponse(), "etiquettes")
                ia_usage.preciser(modele_demande="claude-sonnet-5-5", fichiers=2)
        self._dans_requete("/tools?outil=etiquettes&poste=specifiques", "/api/print/specifiques/ia/depuis-photo", appel)
        with get_db() as c:
            r = dict(c.execute("SELECT * FROM ia_usage").fetchone())
        self.assertEqual(r["application"], "MyTools")
        self.assertEqual(r["ecran"], "Étiquettes › Étiquettes spécifiques")
        self.assertEqual(r["api"], "/api/print/specifiques/ia/depuis-photo")
        self.assertEqual(r["page"], "/tools?outil=etiquettes&poste=specifiques")
        self.assertEqual(r["modele_demande"], "claude-sonnet-5-5")
        self.assertEqual(r["nb_fichiers"], 2)
        self.assertEqual(r["fin_raison"], "end_turn")
        self.assertEqual(r["statut"], "ok")

    def test_hors_requete_automatique(self):
        ia_usage.noter(reponse(), "memo_expe")
        with get_db() as c:
            r = dict(c.execute("SELECT * FROM ia_usage").fetchone())
        self.assertEqual(r["application"], "Automatique")
        self.assertIsNone(r["page"])

    def test_echec_message(self):
        def appel():
            try:
                with ia_usage.suivi({"id": 7, "nom": "Test"}, "formulaires"):
                    ia_usage.noter(reponse(fin="max_tokens"), "formulaires")
                    raise HTTPException(status_code=400, detail="Réponse tronquée.")
            except HTTPException:
                pass
        self._dans_requete("/tools?outil=formulaires", "/api/qualite/formulaires/ia/proposer", appel)
        with get_db() as c:
            r = dict(c.execute("SELECT * FROM ia_usage").fetchone())
        self.assertEqual(r["statut"], "err")
        self.assertEqual(r["erreur"], "Réponse tronquée.")
        self.assertEqual(r["fin_raison"], "max_tokens")


class Synthese(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with get_db() as c:
            c.execute("DELETE FROM ia_usage")
            c.commit()
        lignes = [
            (1, "Alice", "agent", "MyTools", "Éditeur PDF", "claude-sonnet-5-5", "ok"),
            (1, "Alice", "etiquettes", "MyTools", "Étiquettes", "claude-haiku-5-5", "ok"),
            (2, "Bob", "devis", "MyProd", "Rentabilité", "claude-sonnet-5-5", "err"),
            (None, "Automatique", "memo_expe", None, None, "claude-haiku-5-5", "ok"),
        ]
        with get_db() as c:
            for uid, nom, f, app, ecran, mod, st in lignes:
                c.execute(
                    """INSERT INTO ia_usage (cree_le, user_id, utilisateur, role, fonction, modele, nb_appels,
                           input_tokens, output_tokens, cout_usd, duree_ms, statut, application, ecran, modele_demande)
                       VALUES (datetime('now','localtime'), ?, ?, 'superadmin', ?, ?, 1, 1000, 100, 0.01, 1500, ?, ?, ?, ?)""",
                    (uid, nom, f, mod, st, app, ecran, "claude-opus-5-5" if f == "agent" else mod))
            c.commit()

    def syn(self, **f):
        with get_db() as c:
            return ia_usage.synthese(c, 30, f)

    def test_sans_filtre(self):
        d = self.syn()
        self.assertEqual(d["total"]["actions"], 4)
        self.assertEqual(d["total"]["echecs"], 1)
        apps = {r["application"]: r["actions"] for r in d["par_application"]}
        self.assertEqual(apps, {"MyTools": 2, "MyProd": 1, "": 1})
        self.assertTrue(0 < d["taux_usd_eur"] < 10)

    def test_filtres(self):
        self.assertEqual(self.syn(utilisateur="1")["total"]["actions"], 2)
        self.assertEqual(self.syn(utilisateur="auto")["total"]["actions"], 1)
        self.assertEqual(self.syn(application="MyTools")["total"]["actions"], 2)
        self.assertEqual(self.syn(application="")["total"]["actions"], 1)
        self.assertEqual(self.syn(fonction="devis")["total"]["actions"], 1)
        self.assertEqual(self.syn(modele="claude-haiku-5-5")["total"]["actions"], 2)
        self.assertEqual(self.syn(statut="err")["total"]["actions"], 1)
        # Les options des filtres ignorent les filtres posés.
        self.assertEqual(len(self.syn(utilisateur="1")["options"]["utilisateurs"]), 3)

    def test_fiche_et_repli(self):
        with get_db() as c:
            i = c.execute("SELECT id FROM ia_usage WHERE fonction='agent'").fetchone()[0]
            d = ia_usage.detail(c, i)
            self.assertIsNone(ia_usage.detail(c, 999999))
        self.assertTrue(d["repli"])
        self.assertIn("entree", d["cout_detail"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
