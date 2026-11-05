"""
Écarts de saisie de production : file, pastille, validation, correction.

Ce que chaque bloc protège, posé le 16/10/2026 :

1. **Les trois écarts de saisie naissent tout de suite** : un dossier fictif,
   un chiffrage signalé et des heures non reportées entrent dans la file
   Cohérence (famille prod) dès la saisie, sans attendre le passage des
   30 minutes — la pastille MyProd les compte.
2. **Valider** sort l'écart de la file, et une déclaration validée ne revient
   pas au passage suivant.
3. **Corriger un fictif** rattache toutes ses saisies au vrai dossier choisi.
4. **Corriger des heures non reportées** les reporte en forçant, après un
   aperçu qui ne touche à rien.
5. **Corriger un chiffrage signalé** reporte les heures corrigées.
6. **Amener au bon endroit** : un fictif se retrouve par la réf produit
   notée par l'opérateur, un dossier « en cours » sans saisie montre les
   saisies de sa machine et un lien planning (machine, semaine, fiche), et
   l'info prod absente s'écrit depuis l'écart.
7. **Valider en groupe** sort tous les écarts cochés d'un coup ; un écart
   déjà traité est ignoré, pas une erreur.

Lancer : python3 tests/test_prod_ecarts.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

_tmp = tempfile.mkdtemp(prefix="mysifa_ecarts_test_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database  # noqa: E402,F401  — toujours avant app.*

MACHINE_ID = 90301
MACHINE_NOM = "Test Ecarts 1"
USER = {"id": 1, "nom": "Testeur", "email": "test@local", "role": "direction"}
FMT = "%Y-%m-%dT%H:%M:%S"


def _iso(d):
    return d.strftime(FMT)


def _client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers.fabrication import router as fab_router
    from app.routers.prod_ecarts import router as ecarts_router

    app = FastAPI()
    app.include_router(fab_router)
    app.include_router(ecarts_router)
    return TestClient(app, raise_server_exceptions=True)


class TestProdEcarts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from database import get_db

        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO machines (id, nom, code, actif, dernier_metrage) "
                "VALUES (?,?,?,1,NULL)", (MACHINE_ID, MACHINE_NOM, "TE1"))
            conn.commit()
        cls.client = _client()

    def setUp(self):
        from database import get_db

        self.patchs = [
            patch("app.routers.fabrication.get_current_user", return_value=dict(USER)),
            patch("app.routers.fabrication.is_admin", return_value=True),
            patch("app.routers.prod_ecarts.get_current_user", return_value=dict(USER)),
            patch("app.routers.prod_ecarts.is_admin", return_value=True),
        ]
        for p in self.patchs:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patchs])
        with get_db() as conn:
            conn.execute("DELETE FROM production_data WHERE machine = ?", (MACHINE_NOM,))
            conn.execute("DELETE FROM dossier_calages_declares WHERE machine = ?", (MACHINE_NOM,))
            conn.execute("DELETE FROM coherence_ecarts")
            conn.commit()
        self.t0 = (datetime.now() - timedelta(hours=6)).replace(second=0, microsecond=0)

    def _saisie(self, code, minutes, dossier):
        from config import classify_operation
        from database import get_db

        cl = classify_operation(code)
        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO production_data
                   (operateur, date_operation, operation, operation_code, operation_severity,
                    operation_category, machine, no_dossier, quantite_a_traiter, quantite_traitee,
                    service, data, est_manuel)
                   VALUES (?,?,?,?,?,?,?,?,0,0,'fabrication','{}',0)""",
                (USER["nom"], _iso(self.t0 + timedelta(minutes=minutes)), f"{code} - {cl['label']}",
                 code, cl["severity"], cl["category"], MACHINE_NOM, dossier))
            conn.commit()
            return cur.lastrowid

    def _cloturer(self, dossier, debut, fin, signalement=None):
        prod = datetime.now().replace(second=0, microsecond=0) - timedelta(minutes=5)
        calage = {"debut_calage": _iso(debut), "fin_calage": _iso(fin), "fin_prod": _iso(prod)}
        if signalement:
            calage["signalement"] = signalement
        r = self.client.post("/api/fabrication/saisie", json={
            "operation": "89 - Fin de production", "machine_id": MACHINE_ID, "no_dossier": dossier,
            "fin_dossier": True, "metrage_fin": 1000, "calage": calage})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def _ecarts(self):
        r = self.client.get("/api/prod/ecarts")
        self.assertEqual(r.status_code, 200, r.text)
        return {e["regle"]: e for e in r.json()["ecarts"]}

    def test_1_trois_ecarts_et_pastille(self):
        # Dossier fictif saisi depuis l'écran opérateur.
        r = self.client.post("/api/fabrication/saisie", json={
            "operation": "02 - Calage", "machine_id": MACHINE_ID,
            "dossier_fictif": True, "numero_of_fictif": "9900111"})
        self.assertEqual(r.status_code, 200, r.text)
        # Clôture : heure de fin de calage qui enjambe un changement de plaque,
        # et chiffrage signalé.
        self._saisie("01", 0, "ECA-1")
        self._saisie("02", 1, "ECA-1")
        self._saisie("60", 30, "ECA-1")
        self._saisie("03", 100, "ECA-1")
        self._cloturer("ECA-1", self.t0 + timedelta(minutes=1), self.t0 + timedelta(minutes=20),
                       signalement="Calage noté 20 min")
        e = self._ecarts()
        self.assertEqual(set(e), {"prod.dossier_fictif", "prod.calage_signale", "prod.calage_non_reporte"})
        self.assertEqual(e["prod.dossier_fictif"]["action"], "rattacher")
        self.assertEqual(e["prod.calage_non_reporte"]["action"], "reappliquer")
        self.assertEqual(e["prod.calage_signale"]["action"], "heures")
        self.assertEqual(self.client.get("/api/prod/ecarts/count").json()["n"], 3)
        from database import get_db
        from app.services.notifications import DETECTEURS
        with get_db() as conn:
            self.assertEqual(DETECTEURS["prod.ecarts"].compter(conn)[0], 3)

        # Valider le signalement : il sort, et ne revient pas au passage suivant.
        r = self.client.post(f"/api/prod/ecarts/{e['prod.calage_signale']['id']}/valider",
                             json={"commentaire": "Vu avec le conducteur"})
        self.assertEqual(r.status_code, 200, r.text)
        from app.services import coherence
        with get_db() as conn:
            coherence.rafraichir_saisies(conn)
        self.assertNotIn("prod.calage_signale", self._ecarts())

    def test_2_corriger_fictif(self):
        from database import get_db

        self.client.post("/api/fabrication/saisie", json={
            "operation": "02 - Calage", "machine_id": MACHINE_ID,
            "dossier_fictif": True, "numero_of_fictif": "9900222"})
        self._saisie("01", 0, "9900222")  # le vrai dossier existe déjà en saisies
        e = self._ecarts()["prod.dossier_fictif"]
        ap = self.client.get(f"/api/prod/ecarts/{e['id']}/correction").json()
        self.assertIn("9900222", [c["no_dossier"] for c in ap["candidats"]])
        r = self.client.post(f"/api/prod/ecarts/{e['id']}/corriger", json={"to_no_dossier": "9900222"})
        self.assertEqual(r.status_code, 200, r.text)
        with get_db() as conn:
            n = conn.execute("SELECT COUNT(*) FROM production_data WHERE no_dossier LIKE 'FICTIF:%' "
                             "AND machine=?", (MACHINE_NOM,)).fetchone()[0]
        self.assertEqual(n, 0)
        self.assertNotIn("prod.dossier_fictif", self._ecarts())

    def test_3_reappliquer_heures(self):
        from database import get_db

        self._saisie("01", 0, "ECA-3")
        self._saisie("02", 1, "ECA-3")
        self._saisie("60", 30, "ECA-3")
        s03 = self._saisie("03", 100, "ECA-3")
        self._cloturer("ECA-3", self.t0 + timedelta(minutes=1), self.t0 + timedelta(minutes=20))
        e = self._ecarts()["prod.calage_non_reporte"]
        ap = self.client.get(f"/api/prod/ecarts/{e['id']}/correction").json()
        self.assertTrue(any(c["saisie_id"] == s03 for c in ap["apercu"]["changements"]))
        with get_db() as conn:  # l'aperçu ne touche à rien
            avant = conn.execute("SELECT date_operation FROM production_data WHERE id=?", (s03,)).fetchone()[0]
        self.assertEqual(avant, _iso(self.t0 + timedelta(minutes=100)))
        r = self.client.post(f"/api/prod/ecarts/{e['id']}/corriger", json={})
        self.assertEqual(r.status_code, 200, r.text)
        with get_db() as conn:
            apres = conn.execute("SELECT date_operation FROM production_data WHERE id=?", (s03,)).fetchone()[0]
        self.assertEqual(apres, _iso(self.t0 + timedelta(minutes=20)))
        self.assertNotIn("prod.calage_non_reporte", self._ecarts())

    def test_4_corriger_signalement(self):
        from database import get_db

        self._saisie("01", 0, "ECA-4")
        self._saisie("02", 1, "ECA-4")
        s03 = self._saisie("03", 100, "ECA-4")
        self._cloturer("ECA-4", self.t0 + timedelta(minutes=1), self.t0 + timedelta(minutes=100),
                       signalement="Fin de calage à 9h")
        e = self._ecarts()["prod.calage_signale"]
        prod = datetime.now().replace(second=0, microsecond=0) - timedelta(minutes=5)
        r = self.client.post(f"/api/prod/ecarts/{e['id']}/corriger", json={
            "debut_calage": _iso(self.t0 + timedelta(minutes=1)),
            "fin_calage": _iso(self.t0 + timedelta(minutes=60)), "fin_prod": _iso(prod)})
        self.assertEqual(r.status_code, 200, r.text)
        with get_db() as conn:
            apres = conn.execute("SELECT date_operation FROM production_data WHERE id=?", (s03,)).fetchone()[0]
        self.assertEqual(apres, _iso(self.t0 + timedelta(minutes=60)))
        self.assertNotIn("prod.calage_signale", self._ecarts())

    def _ecart_brut(self, regle, objet_ref, donnees):
        import json
        from database import get_db
        maintenant = _iso(datetime.now())
        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO coherence_ecarts (cle, regle, famille, objet_type, objet_ref, titre,
                       detail, donnees_json, premiere_vue, derniere_vue)
                   VALUES (?,?,'prod','dossier',?,?,'',?,?,?)""",
                (f"{regle}:{objet_ref}", regle, objet_ref, objet_ref, json.dumps(donnees),
                 maintenant, maintenant))
            conn.commit()
            return cur.lastrowid

    def test_5_amener_au_bon_endroit(self):
        from database import get_db
        from app.routers import prod_ecarts as pe_mod

        with get_db() as conn:
            conn.execute("DELETE FROM planning_entries WHERE machine_id=?", (MACHINE_ID,))
            debut = datetime(2026, 10, 14, 8, 0)  # un mercredi
            pe_id = conn.execute(
                """INSERT INTO planning_entries (machine_id, position, reference, client, ref_produit,
                       statut, planned_start, planned_end)
                   VALUES (?,1,'ECA-5','Client Test','RP-77881','en_cours',?,?)""",
                (MACHINE_ID, _iso(debut), _iso(debut + timedelta(hours=4)))).lastrowid
            conn.commit()
            # Réf produit notée à la place du numéro de dossier.
            cands = pe_mod._candidats(conn, "", {"of": "RP-77881", "machine": MACHINE_NOM})
            self.assertEqual(cands[0]["no_dossier"], "ECA-5")
            self.assertEqual(pe_mod._candidats(conn, "client test", None)[0]["no_dossier"], "ECA-5")
            self.assertEqual(pe_mod._lien_planning(conn, pe_id),
                             f"/planning?machine={MACHINE_ID}&dossier={pe_id}&semaine=2026-10-12")
        # Recherche à la demande depuis la fenêtre de rattachement.
        e_id = self._ecart_brut("prod.dossier_fictif", "FICTIF:X", {"of": "zzz", "machine": MACHINE_NOM})
        r = self.client.get(f"/api/prod/ecarts/{e_id}/candidats", params={"q": "77881"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("ECA-5", [c["no_dossier"] for c in r.json()["candidats"]])

        # Dossier en cours sans saisie : les saisies de la machine depuis la veille.
        self.t0 = datetime(2026, 10, 14, 9, 0)
        sid = self._saisie("01", 0, "AUTRE-5")
        e_id = self._ecart_brut("prod.en_cours_sans_saisie", "ECA-5", {"planning_entry_id": pe_id})
        ap = self.client.get(f"/api/prod/ecarts/{e_id}/correction").json()
        self.assertEqual(ap["action"], "machine_saisies")
        self.assertEqual(ap["dossier"]["reference"], "ECA-5")
        self.assertIn(sid, [x["id"] for x in ap["saisies"]])
        self.assertIn("dossier=", ap["lien"])

        # Info prod absente : écrite depuis l'écart, qui se résout.
        e_id = self._ecart_brut("prod.info_prod_absente", "ECA-5", {})
        self.assertEqual(self.client.get(f"/api/prod/ecarts/{e_id}/correction").json()["action"], "info_prod")
        self.assertEqual(self.client.post(f"/api/prod/ecarts/{e_id}/corriger", json={"texte": ""}).status_code, 400)
        r = self.client.post(f"/api/prod/ecarts/{e_id}/corriger", json={"texte": "R.A.S."})
        self.assertEqual(r.status_code, 200, r.text)
        with get_db() as conn:
            st = conn.execute("SELECT statut FROM coherence_ecarts WHERE id=?", (e_id,)).fetchone()[0]
        self.assertEqual(st, "resolu")

    def test_6_valider_en_groupe(self):
        from database import get_db

        a = self._ecart_brut("prod.info_prod_absente", "GRP-1", {})
        b = self._ecart_brut("prod.info_prod_absente", "GRP-2", {})
        c = self._ecart_brut("prod.info_prod_absente", "GRP-3", {})
        self.assertEqual(self.client.post("/api/prod/ecarts/valider-groupe", json={"ids": []}).status_code, 400)
        r = self.client.post("/api/prod/ecarts/valider-groupe",
                             json={"ids": [a, b], "commentaire": "Dossiers de test"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["valides"], 2)
        # Rejouer la même sélection : déjà traités, ignorés.
        r = self.client.post("/api/prod/ecarts/valider-groupe", json={"ids": [a, b, 999999]})
        self.assertEqual((r.json()["valides"], r.json()["ignores"]), (0, 3))
        with get_db() as conn:
            st = dict(conn.execute("SELECT id, statut FROM coherence_ecarts WHERE id IN (?,?,?)",
                                   (a, b, c)).fetchall())
        self.assertEqual(st[a], "explique")
        self.assertEqual(st[b], "explique")
        self.assertEqual(st[c], "ouvert")


if __name__ == "__main__":
    unittest.main(verbosity=2)
