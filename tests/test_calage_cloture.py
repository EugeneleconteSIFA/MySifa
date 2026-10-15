"""
Calage et gâche : compteur en fin de calage, heures déclarées à la clôture.

Ce que chaque bloc protège, posé le 15/10/2026 :

1. **Les heures se pré-remplissent depuis les saisies** : début = première
   saisie de la catégorie calage du dossier, fin = première saisie de
   production qui suit.
2. **La clôture corrige les saisies en place** : le calage commencé avant le
   clic « Début de production » emmène le 01 avec lui, le 03 prend l'heure
   de fin déclarée, la saisie de clôture l'heure de fin de prod. Les heures
   d'origine restent dans `dossier_calages_declares`.
3. **Une heure qui enjamberait une autre saisie n'est pas appliquée** : la
   déclaration est gardée avec son motif, les saisies ne bougent pas.
4. **Un « Production » jamais cliqué est inséré** à l'heure de fin de calage
   déclarée, tant qu'elle tombe dans le calage resté ouvert.
5. **Une déclaration incohérente refuse la clôture** sans rien écrire.
6. **Le compteur n'est proposé qu'au 03 qui ferme un calage**, et ne peut
   pas descendre sous le dernier relevé.

Lancer : python3 tests/test_calage_cloture.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

_tmp = tempfile.mkdtemp(prefix="mysifa_calage_test_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database  # noqa: E402,F401  — toujours avant app.*

MACHINE_ID = 90201
MACHINE_NOM = "Test Calage 1"
DOSSIER = "CAL-001"
USER = {"id": 1, "nom": "Testeur", "email": "test@local", "role": "direction"}
FMT = "%Y-%m-%dT%H:%M:%S"


def _client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers.fabrication import router as fab_router

    app = FastAPI()
    app.include_router(fab_router)
    return TestClient(app, raise_server_exceptions=True)


def _iso(d):
    return d.strftime(FMT)


class TestCalageCloture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from database import get_db

        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO machines (id, nom, code, actif, dernier_metrage) "
                "VALUES (?,?,?,1,NULL)",
                (MACHINE_ID, MACHINE_NOM, "TC1"),
            )
            conn.commit()
        cls.client = _client()

    def setUp(self):
        from database import get_db

        self.patchs = [
            patch("app.routers.fabrication.get_current_user", return_value=dict(USER)),
            patch("app.routers.fabrication.is_admin", return_value=True),
        ]
        for p in self.patchs:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patchs])
        with get_db() as conn:
            conn.execute("DELETE FROM production_data WHERE machine = ?", (MACHINE_NOM,))
            conn.execute("DELETE FROM dossier_calages_declares WHERE machine = ?", (MACHINE_NOM,))
            conn.execute("UPDATE machines SET dernier_metrage=NULL WHERE id=?", (MACHINE_ID,))
            conn.commit()
        # Minute ronde : les heures déclarées le sont à la minute.
        self.t0 = (datetime.now() - timedelta(hours=6)).replace(second=0, microsecond=0)

    # ── helpers ──────────────────────────────────────────────────────────
    def _saisie(self, code, minutes, dossier=DOSSIER):
        from config import classify_operation
        from database import get_db

        cl = classify_operation(code)
        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO production_data
                   (operateur, date_operation, operation, operation_code,
                    operation_severity, operation_category, machine, no_dossier,
                    quantite_a_traiter, quantite_traitee, service, data, est_manuel)
                   VALUES (?,?,?,?,?,?,?,?,0,0,'fabrication','{}',0)""",
                (USER["nom"], _iso(self.t0 + timedelta(minutes=minutes)),
                 f"{code} - {cl['label']}", code, cl["severity"], cl["category"],
                 MACHINE_NOM, dossier),
            )
            conn.commit()
            return cur.lastrowid

    @staticmethod
    def _ligne(saisie_id):
        from database import get_db

        with get_db() as conn:
            return dict(conn.execute(
                "SELECT * FROM production_data WHERE id=?", (saisie_id,)).fetchone())

    @staticmethod
    def _declarations():
        from database import get_db

        with get_db() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM dossier_calages_declares WHERE machine=? ORDER BY id",
                (MACHINE_NOM,)).fetchall()]

    def _cloturer(self, debut, fin, prod):
        return self.client.post("/api/fabrication/saisie", json={
            "operation": "89 - Fin de production", "machine_id": MACHINE_ID,
            "no_dossier": DOSSIER, "fin_dossier": True, "metrage_fin": 1000,
            "calage": {"debut_calage": _iso(debut), "fin_calage": _iso(fin),
                       "fin_prod": _iso(prod)},
        })

    # ── 1 + 2. Pré-remplissage puis correction en place ──────────────────
    def test_1_proposition_puis_correction(self):
        s01 = self._saisie("01", 0)
        s02 = self._saisie("02", 1)
        self._saisie("60", 30)
        s03 = self._saisie("03", 100)

        r = self.client.get("/api/fabrication/calage-cloture",
                            params={"no_dossier": DOSSIER, "machine_id": MACHINE_ID})
        self.assertEqual(r.status_code, 200, r.text)
        p = r.json()
        self.assertEqual(p["debut_calage"], _iso(self.t0 + timedelta(minutes=1)))
        self.assertEqual(p["fin_calage"], _iso(self.t0 + timedelta(minutes=100)))
        self.assertAlmostEqual(p["calage_mesure_min"], 99.0, places=1)

        debut = self.t0 - timedelta(minutes=10)
        fin = self.t0 + timedelta(minutes=90)
        prod = datetime.now().replace(second=0, microsecond=0) - timedelta(minutes=5)
        r = self._cloturer(debut, fin, prod)
        self.assertEqual(r.status_code, 200, r.text)
        rep = r.json()
        self.assertEqual(rep["calage"]["motifs"], [])

        self.assertEqual(self._ligne(s01)["date_operation"], _iso(debut))
        self.assertEqual(self._ligne(s02)["date_operation"], _iso(debut))
        self.assertEqual(self._ligne(s03)["date_operation"], _iso(fin))
        self.assertTrue(self._ligne(s03)["modifie_note"])
        self.assertEqual(self._ligne(rep["id"])["date_operation"], _iso(prod))

        d = self._declarations()[-1]
        self.assertEqual((d["debut_applique"], d["fin_calage_applique"], d["fin_prod_applique"]),
                         (1, 1, 1))
        self.assertEqual(d["debut_calage_mesure"], _iso(self.t0 + timedelta(minutes=1)))
        self.assertEqual(d["fin_calage_mesure"], _iso(self.t0 + timedelta(minutes=100)))
        self.assertEqual(d["saisie_cloture_id"], rep["id"])

    # ── 3. Une heure qui enjambe une saisie n'est pas appliquée ─────────
    def test_2_enjambement_non_applique(self):
        self._saisie("01", 0)
        self._saisie("02", 1)
        self._saisie("60", 30)
        s03 = self._saisie("03", 100)

        prod = datetime.now().replace(second=0, microsecond=0) - timedelta(minutes=5)
        r = self._cloturer(self.t0 + timedelta(minutes=1), self.t0 + timedelta(minutes=20), prod)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(len(r.json()["calage"]["motifs"]), 1)
        self.assertEqual(self._ligne(s03)["date_operation"],
                         _iso(self.t0 + timedelta(minutes=100)))
        d = self._declarations()[-1]
        self.assertEqual(d["fin_calage_applique"], 0)
        self.assertIn("enjamberait", d["motifs_non_appliques"])

    # ── 4. « Production » jamais cliqué : inséré ─────────────────────────
    def test_3_production_inseree(self):
        from database import get_db

        self._saisie("01", 0)
        self._saisie("02", 1)
        fin = self.t0 + timedelta(minutes=60)
        prod = datetime.now().replace(second=0, microsecond=0) - timedelta(minutes=5)
        r = self._cloturer(self.t0 + timedelta(minutes=1), fin, prod)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["calage"]["motifs"], [])
        with get_db() as conn:
            ins = conn.execute(
                "SELECT * FROM production_data WHERE machine=? AND operation_code='03'",
                (MACHINE_NOM,)).fetchall()
        self.assertEqual(len(ins), 1)
        self.assertEqual(ins[0]["date_operation"], _iso(fin))
        self.assertEqual(ins[0]["est_manuel"], 1)

    # ── 4 bis. Production cliqué en retard, juste avant la clôture ───────
    def test_3b_production_tardive_derniere_saisie(self):
        self._saisie("01", 0)
        self._saisie("02", 1)
        s03 = self._saisie("03", 340)  # cliqué 20 min avant maintenant
        fin = self.t0 + timedelta(minutes=60)
        prod = self.t0 + timedelta(minutes=330)  # avant le clic du 03, après la fin déclarée
        r = self._cloturer(self.t0 + timedelta(minutes=1), fin, prod)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["calage"]["motifs"], [])
        self.assertEqual(self._ligne(s03)["date_operation"], _iso(fin))
        self.assertEqual(self._ligne(r.json()["id"])["date_operation"], _iso(prod))
        # Le calage mesuré est celui des saisies AVANT correction : la clôture
        # insérée avant le 03 tardif ne le raccourcit pas.
        self.assertAlmostEqual(self._declarations()[-1]["calage_mesure_min"], 339.0, places=1)

    # ── 5. Déclaration incohérente : rien n'est écrit ────────────────────
    def test_4_declaration_incoherente(self):
        from database import get_db

        self._saisie("01", 0)
        self._saisie("02", 1)
        prod = datetime.now().replace(second=0, microsecond=0) - timedelta(minutes=5)
        r = self._cloturer(self.t0 + timedelta(minutes=60), self.t0 + timedelta(minutes=30), prod)
        self.assertEqual(r.status_code, 400, r.text)
        with get_db() as conn:
            n = conn.execute(
                "SELECT COUNT(*) FROM production_data WHERE machine=? AND operation_code='89'",
                (MACHINE_NOM,)).fetchone()[0]
        self.assertEqual(n, 0)
        self.assertEqual(self._declarations(), [])

    # ── 6. Compteur en fin de calage ─────────────────────────────────────
    def test_5_compteur_fin_calage(self):
        from database import get_db

        self._saisie("01", 0)
        self._saisie("02", 1)
        with get_db() as conn:
            conn.execute("UPDATE machines SET dernier_metrage=500 WHERE id=?", (MACHINE_ID,))
            conn.commit()
        r = self.client.post("/api/fabrication/saisie",
                             json={"operation": "03 - Production", "machine_id": MACHINE_ID,
                                   "no_dossier": DOSSIER})
        self.assertEqual(r.status_code, 200, r.text)
        ctx = r.json().get("compteur_fin_calage")
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx["dernier_metrage"], 500.0)

        # Un 03 qui suit autre chose qu'un calage ne propose rien.
        r2 = self.client.post("/api/fabrication/saisie",
                              json={"operation": "03 - Production", "machine_id": MACHINE_ID,
                                    "no_dossier": DOSSIER})
        self.assertNotIn("compteur_fin_calage", r2.json())

        with get_db() as conn:
            conn.execute("UPDATE production_data SET metrage_total_debut=500 "
                         "WHERE machine=? AND operation_code='01'", (MACHINE_NOM,))
            conn.commit()
        url = f"/api/fabrication/saisie/{ctx['saisie_id']}/compteur-fin-calage"
        self.assertEqual(self.client.put(url, json={"metrage_compteur": 400}).status_code, 400)
        r3 = self.client.put(url, json={"metrage_compteur": 820})
        self.assertEqual(r3.status_code, 200, r3.text)
        self.assertEqual(self._ligne(ctx["saisie_id"])["metrage_compteur"], 820.0)
        with get_db() as conn:
            self.assertEqual(conn.execute("SELECT dernier_metrage FROM machines WHERE id=?",
                                          (MACHINE_ID,)).fetchone()[0], 820.0)

    # ── 7. Gâche mesurée, comparée au devis, dans le compte-rendu ────────
    def test_6_gache_devis_compte_rendu(self):
        from database import get_db
        from app.services import rapport_dossier as rd

        s01 = self._saisie("01", 0)
        self._saisie("02", 1)
        s60 = self._saisie("60", 10)
        s03 = self._saisie("03", 60)
        self._saisie("02", 200, dossier="CAL-AUTRE")  # autre dossier : ne compte pas
        with get_db() as conn:
            conn.execute("UPDATE production_data SET metrage_total_debut=10000 WHERE id=?", (s01,))
            # Un changement d'outil relevé PENDANT le calage ne sert pas de départ.
            conn.execute("UPDATE production_data SET metrage_compteur=10100 WHERE id=?", (s60,))
            conn.execute("UPDATE production_data SET metrage_compteur=10850 WHERE id=?", (s03,))
            conn.execute("DELETE FROM rent_prod_links WHERE planning_entry_id=990201")
            conn.execute("DELETE FROM rent_links WHERE planning_entry_id=990201")
            cur = conn.execute(
                """INSERT INTO devis (filename, temps_calage_mn, temps_calage_impression_mn,
                                      metrage_calage_ml, metrage_calage_impression_ml,
                                      imported_at)
                   VALUES ('t.xlsx', 30, 30, 400, 200, '2026-10-15')""")
            conn.execute("INSERT INTO rent_links (planning_entry_id, devis_id, updated_at) "
                         "VALUES (990201, ?, '2026-10-15')", (cur.lastrowid,))
            conn.execute("INSERT INTO rent_prod_links (planning_entry_id, no_dossier) "
                         "VALUES (990201, ?)", (DOSSIER,))
            conn.commit()
            cr = rd.compte_rendu(conn, DOSSIER)

        c = cr["calage"]
        self.assertEqual(c["gache"]["metres"], 850.0)
        self.assertEqual(c["gache"]["plages"][0]["compteur_debut"], 10000.0)
        self.assertEqual(c["devis"]["minutes"], 60.0)
        self.assertEqual(c["devis"]["metres"], 600.0)
        self.assertAlmostEqual(c["ecart_devis_metres_pct"], 41.7, places=1)
        self.assertAlmostEqual(c["minutes"], 59.0, places=1)

        # Rentabilité : la gâche réelle face au métrage de calage devisé.
        from app.routers.rentabilite import _comparaison_from_no_dossiers
        with get_db() as conn:
            devis = conn.execute("SELECT * FROM devis WHERE filename='t.xlsx' "
                                 "ORDER BY id DESC LIMIT 1").fetchone()
            comp = _comparaison_from_no_dossiers(conn, devis, [DOSSIER])
        self.assertEqual(comp["reel"]["metrage_calage_ml"], 850.0)
        self.assertEqual(comp["ecarts"]["metrage_calage_ml"], "+41.7%")

        # Compteur non relevé : pas de gâche, et on sait pourquoi.
        with get_db() as conn:
            conn.execute("UPDATE production_data SET metrage_compteur=NULL WHERE id=?", (s03,))
            conn.commit()
            g = __import__("app.services.calage_cloture", fromlist=["x"]).gache_calage(conn, DOSSIER)
        self.assertIsNone(g["metres"])
        self.assertEqual(g["plages_sans_releve"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
