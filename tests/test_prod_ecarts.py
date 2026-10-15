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


if __name__ == "__main__":
    unittest.main(verbosity=2)
