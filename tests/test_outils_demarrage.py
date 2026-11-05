"""
Plaque confirmée au démarrage du dossier.

Ce que chaque bloc protège, posé le 22/10/2026 :

1. **La migration marque la plaque « au démarrage »** et crée la table qui
   relie la saisie 01 à l'outil monté.
2. **La plaque proposée est celle de la fiche du dossier**, retrouvée par le
   créneau du planning ; une fiche qui prévoit deux plaques en propose deux, et
   un outil « Sheeter » n'est pas une plaque.
3. **Confirmer enregistre la plaque**, conforme à la fiche, et l'écrit dans le
   commentaire de la saisie. **Changer enregistre l'écart** : la plaque montée
   et celle de la fiche, et la phrase lisible le dit.
4. **Un numéro inconnu du référentiel est créé au passage** — « à valider »
   s'il a été tapé au poste, pas s'il vient de la fiche.
5. **La plaque confirmée devient la plaque en place sur la machine** : le
   dossier suivant la propose quand sa fiche ne dit rien, et le formulaire de
   changement d'outil la pré-remplit comme plaque démontée.
6. **Jamais bloquant** : un choix invalide ou une nature inconnue n'empêche pas
   le dossier de démarrer, et rien n'est écrit pour une autre saisie que la 01.

Lancer : python3 tests/test_outils_demarrage.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_tmp = tempfile.mkdtemp(prefix="mysifa_outil_demarrage_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MACHINE_ID = 90201
MACHINE_NOM = "Test Demarrage 1"
USER = {"id": 1, "nom": "Testeur", "email": "test@local", "role": "direction"}


def _client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.routers.fabrication import router as fab_router
    from app.routers.outils import router as outils_router

    app = FastAPI()
    app.include_router(fab_router)
    app.include_router(outils_router)
    return TestClient(app, raise_server_exceptions=True)


def _fiche(conn, reference, ref_norm, outils):
    cols = ["reference", "ref_produit_norm", "valide"]
    vals = [reference, ref_norm, 0]
    for i, (forme, numero) in enumerate(outils, start=1):
        cols += [f"outil{i}_forme", f"outil{i}_numero_sifa"]
        vals += [forme, numero]
    conn.execute(
        f"INSERT INTO fiches_techniques ({', '.join(cols)}) VALUES ({', '.join('?' * len(vals))})",
        vals,
    )


def _creneau(conn, reference, ref_produit):
    conn.execute(
        """INSERT INTO planning_entries
           (machine_id, position, reference, duree_heures, statut, created_at, updated_at,
            ref_produit, ref_produit_norm)
           VALUES (?, 1, ?, 1, 'attente', '2026-10-22T00:00:00', '2026-10-22T00:00:00', ?, ?)""",
        (MACHINE_ID, reference, ref_produit, ref_produit),
    )


class TestOutilsDemarrage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import database  # noqa: F401 — le shim d'abord (CLAUDE.md)
        from database import get_db

        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO machines (id, nom, code, actif, dernier_metrage) "
                "VALUES (?,?,?,1,NULL)",
                (MACHINE_ID, MACHINE_NOM, "TD1"),
            )
            _fiche(conn, "901/0001", "901/0001", [("Plaque", "D-1001")])
            _fiche(conn, "901/0002", "901/0002",
                   [("Plaque", "D-2001"), ("Spéciale", "D-2002"), ("Sheeter", "D-2003")])
            _fiche(conn, "901/0003", "901/0003", [("Sheeter", "D-3001")])
            _creneau(conn, "DOS-A", "901/0001")
            _creneau(conn, "DOS-B", "901/0002")
            _creneau(conn, "DOS-C", "901/0003")
            conn.commit()
        cls.client = _client()

    def setUp(self):
        self.patchs = [
            patch("app.routers.fabrication.get_current_user", return_value=dict(USER)),
            patch("app.routers.fabrication.is_admin", return_value=True),
            patch("app.routers.outils.get_current_user", return_value=dict(USER)),
            patch("app.routers.outils.is_admin", return_value=True),
        ]
        for p in self.patchs:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patchs])
        from database import get_db

        with get_db() as conn:
            conn.execute("UPDATE machines SET dernier_metrage=NULL WHERE id=?", (MACHINE_ID,))
            conn.execute("DELETE FROM production_data WHERE machine=?", (MACHINE_NOM,))
            conn.execute("DELETE FROM outils_demarrage")
            conn.commit()

    # ── helpers ──────────────────────────────────────────────────────────
    def _contexte(self, dossier):
        r = self.client.get(
            f"/api/fabrication/outils/demarrage?no_dossier={dossier}&machine_id={MACHINE_ID}"
        )
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def _demarrer(self, dossier, outils=None, compteur=1000):
        corps = {"operation": "01 - Début de production", "machine_id": MACHINE_ID,
                 "no_dossier": dossier, "metrage_debut": compteur}
        if outils is not None:
            corps["outils_demarrage"] = outils
        r = self.client.post("/api/fabrication/saisie", json=corps)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    @staticmethod
    def _lignes(saisie_id):
        from database import get_db

        with get_db() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM outils_demarrage WHERE saisie_id=? ORDER BY rang", (saisie_id,)
            )]

    @staticmethod
    def _commentaire(saisie_id):
        from database import get_db

        with get_db() as conn:
            return conn.execute(
                "SELECT commentaire FROM production_data WHERE id=?", (saisie_id,)
            ).fetchone()[0]

    # ── 1. Migration ─────────────────────────────────────────────────────
    def test_1_migration(self):
        from database import get_db

        with get_db() as conn:
            marques = [r[0] for r in conn.execute(
                "SELECT cle FROM outil_types WHERE au_demarrage = 1"
            )]
            self.assertEqual(marques, ["plaque"])
            cols = {r[1] for r in conn.execute("PRAGMA table_info(outils_demarrage)")}
            self.assertLessEqual(
                {"saisie_id", "type_cle", "rang", "outil_id", "numero_prevu", "conforme"}, cols
            )

    # ── 2. Proposition ───────────────────────────────────────────────────
    def test_2_proposition_depuis_la_fiche(self):
        d = self._contexte("DOS-A")
        self.assertEqual(d["fiche"]["reference"], "901/0001")
        (nature,) = d["natures"]
        self.assertEqual(nature["type_cle"], "plaque")
        (ligne,) = nature["lignes"]
        self.assertEqual(ligne["prevu"]["numero"], "D-1001")
        self.assertEqual(ligne["prevu"]["origine"], "fiche")

        d = self._contexte("DOS-B")
        numeros = [l["prevu"]["numero"] for l in d["natures"][0]["lignes"]]
        self.assertEqual(numeros, ["D-2001", "D-2002"])  # le Sheeter n'est pas une plaque

        d = self._contexte("DOS-C")
        self.assertEqual(d["natures"][0]["lignes"], [{"rang": 1, "prevu": None}])

    # ── 3. Confirmer / changer ───────────────────────────────────────────
    def test_3_confirmer_puis_changer(self):
        r = self._demarrer("DOS-A", [{"type": "plaque", "rang": 1,
                                      "numero": "D-1001", "origine": "fiche"}])
        self.assertEqual(r["outils_demarrage"][0]["conforme"], 1)
        (l,) = self._lignes(r["id"])
        self.assertEqual((l["numero_prevu"], l["conforme"]), ("D-1001", 1))
        self.assertEqual(self._commentaire(r["id"]), "Plaque D-1001")

        r = self._demarrer("DOS-A", [{"type": "plaque", "rang": 1,
                                      "numero": "D-9999", "origine": "poste"}], compteur=2000)
        (l,) = self._lignes(r["id"])
        self.assertEqual((l["numero_prevu"], l["conforme"]), ("D-1001", 0))
        self.assertEqual(self._commentaire(r["id"]), "Plaque D-9999 (fiche : D-1001)")

    # ── 4. Création au passage ───────────────────────────────────────────
    def test_4_numero_inconnu_cree(self):
        from database import get_db
        from app.services import outils as ref

        self._demarrer("DOS-A", [{"type": "plaque", "rang": 1, "numero": "D-1001", "origine": "fiche"}])
        self._demarrer("DOS-A", [{"type": "plaque", "rang": 1, "numero": "D-POSTE", "origine": "poste"}],
                       compteur=2000)
        with get_db() as conn:
            self.assertFalse(ref.trouver_par_numero(conn, "plaque", "D-1001")["a_valider"])
            self.assertTrue(ref.trouver_par_numero(conn, "plaque", "D-POSTE")["a_valider"])

    # ── 5. Plaque en place ───────────────────────────────────────────────
    def test_5_devient_la_plaque_en_place(self):
        self._demarrer("DOS-A", [{"type": "plaque", "rang": 1, "numero": "D-1001", "origine": "fiche"}])
        d = self._contexte("DOS-C")
        self.assertEqual(d["natures"][0]["en_place"]["numero"], "D-1001")

        clic = self.client.post("/api/fabrication/saisie", json={
            "operation": "60 - Changement Plaque", "machine_id": MACHINE_ID})
        self.assertEqual(clic.json()["outil_requis"]["outil_actuel"]["numero"], "D-1001")

    # ── 6. Jamais bloquant ───────────────────────────────────────────────
    def test_6_jamais_bloquant(self):
        r = self._demarrer("DOS-A", [{"type": "inconnu", "numero": "X"},
                                     {"type": "plaque", "outil_id": 999999},
                                     "pas un objet"])
        self.assertTrue(r["success"])
        self.assertNotIn("outils_demarrage", r)
        self.assertEqual(self._lignes(r["id"]), [])

        clic = self.client.post("/api/fabrication/saisie", json={
            "operation": "03 - Production", "machine_id": MACHINE_ID, "no_dossier": "DOS-A",
            "outils_demarrage": [{"type": "plaque", "numero": "D-1001", "origine": "fiche"}]})
        self.assertEqual(clic.status_code, 200, clic.text)
        self.assertEqual(self._lignes(clic.json()["id"]), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
