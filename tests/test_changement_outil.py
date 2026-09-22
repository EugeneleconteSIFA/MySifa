"""
Changement d'outil : le compteur machine, l'outil démonté, l'outil monté.

Ce que chaque bloc protège, posé le 22/09/2026 :

1. **La migration installe le référentiel et rattache les quatre codes.**
   59 → contre-partie, 60 → plaque, 74 → magnétique, 75 → cliché. Le
   rattachement est ce qui déclenche la saisie : sans lui, rien ne se passe.
2. **Le référentiel ne crée jamais deux fois le même numéro**, réactive celui
   qu'on avait retiré plutôt que d'échouer, et refuse de renommer un outil
   sur un numéro déjà pris.
3. **La saisie exige les trois informations** — sans compteur, sans les deux
   numéros, ou avec deux fois le même, elle est refusée. C'est tout l'objet du
   chantier : une saisie « 60 » qui ne dit que l'heure ne sert à rien.
4. **Le compteur du changement est un compteur machine.** Il ne peut pas
   descendre, et il met à jour `machines.dernier_metrage` — sinon le début du
   dossier suivant repartirait d'une valeur périmée.
5. **Un code sans nature d'outil n'écrit ni compteur ni outil**, même si le
   corps de requête en porte : une valeur qui traîne ne doit pas s'enregistrer.
6. **L'outil en place se lit sur la MACHINE, pas sur le dossier** : un outil
   reste monté d'un dossier au suivant.
7. **Le changement s'écrit aussi dans le commentaire de la saisie** — c'est la
   colonne que tout le monde lit — sans écraser ce que le conducteur a écrit.

Lancer : python3 tests/test_changement_outil.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# DB isolée avant tout import projet (init_db au chargement de database.py)
_tmp = tempfile.mkdtemp(prefix="mysifa_outil_test_")
_db = os.path.join(_tmp, "test.db")
os.environ["DB_PATH"] = _db

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MACHINE_ID = 90101
MACHINE_NOM = "Test Outil 1"
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


class TestChangementOutil(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from database import get_db

        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO machines (id, nom, code, actif, dernier_metrage) "
                "VALUES (?,?,?,1,NULL)",
                (MACHINE_ID, MACHINE_NOM, "TO1"),
            )
            conn.execute("DELETE FROM production_data WHERE machine = ?", (MACHINE_NOM,))
            conn.execute("DELETE FROM outils WHERE numero LIKE 'T-%'")
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

    # ── helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _outil(numero, type_cle="plaque"):
        from database import get_db
        from app.services import outils as ref

        with get_db() as conn:
            return ref.creer_outil(conn, type_cle=type_cle, numero=numero, cree_par="test")

    def _saisie(self, **body):
        corps = {"operation": "60 - Changement Plaque", "machine_id": MACHINE_ID}
        corps.update(body)
        return self.client.post("/api/fabrication/saisie", json=corps)

    @staticmethod
    def _reset_compteur(valeur=None):
        from database import get_db

        with get_db() as conn:
            conn.execute(
                "UPDATE machines SET dernier_metrage=? WHERE id=?", (valeur, MACHINE_ID)
            )
            conn.execute("DELETE FROM production_data WHERE machine = ?", (MACHINE_NOM,))
            conn.commit()

    # ── 1. Migration ─────────────────────────────────────────────────────
    def test_1_migration_installe_le_referentiel(self):
        from database import get_db

        with get_db() as conn:
            types = {r["cle"] for r in conn.execute("SELECT cle FROM outil_types")}
            self.assertLessEqual(
                {"plaque", "contre_partie", "magnetique", "cliche"}, types
            )
            rattach = dict(
                conn.execute(
                    "SELECT code, outil_type FROM operation_codes "
                    "WHERE code IN ('59','60','74','75')"
                ).fetchall()
            )
            self.assertEqual(
                rattach,
                {"59": "contre_partie", "60": "plaque", "74": "magnetique", "75": "cliche"},
            )
            cols = {r[1] for r in conn.execute("PRAGMA table_info(production_data)")}
            self.assertLessEqual(
                {"metrage_compteur", "outil_avant_id", "outil_apres_id"}, cols
            )

    # ── 2. Référentiel ───────────────────────────────────────────────────
    def test_2_referentiel_unicite_et_reactivation(self):
        from database import get_db
        from app.services import outils as ref

        a = self._outil("T-100")
        b = self._outil("T-100")
        self.assertEqual(a["id"], b["id"])

        with get_db() as conn:
            ref.maj_outil(conn, a["id"], actif=False)
            remis = ref.creer_outil(conn, type_cle="plaque", numero="T-100")
            self.assertTrue(remis["actif"])
            self.assertEqual(remis["id"], a["id"])

            autre = ref.creer_outil(conn, type_cle="plaque", numero="T-101")
            with self.assertRaises(ValueError):
                ref.maj_outil(conn, autre["id"], numero="T-100")

            # Même numéro, autre nature : ce sont deux outils distincts.
            cliche = ref.creer_outil(conn, type_cle="cliche", numero="T-100")
            self.assertNotEqual(cliche["id"], a["id"])

    def test_2b_ajout_depuis_le_poste_sort_a_valider(self):
        r = self.client.post(
            "/api/fabrication/outils", json={"type": "plaque", "numero": "T-200"}
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()["a_valider"])

    # ── 3. La saisie exige les trois informations ────────────────────────
    def test_3_saisie_incomplete_refusee(self):
        self._reset_compteur(None)
        a = self._outil("T-300")
        b = self._outil("T-301")

        r = self._saisie(outil_avant_id=a["id"], outil_apres_id=b["id"])
        self.assertEqual(r.status_code, 400, "compteur absent")

        r = self._saisie(metrage_compteur=1000)
        self.assertEqual(r.status_code, 400, "outils absents")

        r = self._saisie(metrage_compteur=1000, outil_avant_id=a["id"], outil_apres_id=a["id"])
        self.assertEqual(r.status_code, 400, "même outil des deux côtés")

        r = self._saisie(metrage_compteur=1000, outil_avant_id=a["id"], outil_apres_id=999999)
        self.assertEqual(r.status_code, 422, "outil hors référentiel")

        # Un cliché ne peut pas être monté par un code qui attend une plaque.
        cliche = self._outil("T-302", type_cle="cliche")
        r = self._saisie(metrage_compteur=1000, outil_avant_id=a["id"], outil_apres_id=cliche["id"])
        self.assertEqual(r.status_code, 422, "nature d'outil incohérente")

    # ── 4. Le compteur est un compteur machine ───────────────────────────
    def test_4_compteur_machine(self):
        from database import get_db

        self._reset_compteur(None)
        a = self._outil("T-400")
        b = self._outil("T-401")

        r = self._saisie(metrage_compteur=5000, outil_avant_id=a["id"], outil_apres_id=b["id"])
        self.assertEqual(r.status_code, 200, r.text)

        with get_db() as conn:
            row = conn.execute(
                "SELECT metrage_compteur, outil_avant_id, outil_apres_id, "
                "       metrage_prevu, metrage_reel "
                "FROM production_data WHERE machine=? ORDER BY id DESC LIMIT 1",
                (MACHINE_NOM,),
            ).fetchone()
            self.assertEqual(row["metrage_compteur"], 5000)
            self.assertEqual(row["outil_avant_id"], a["id"])
            self.assertEqual(row["outil_apres_id"], b["id"])
            # Les colonnes historiques restent vierges : la rentabilité les lit
            # sans filtrer sur le code, y écrire fausserait les vitesses.
            self.assertIsNone(row["metrage_prevu"])
            self.assertIsNone(row["metrage_reel"])
            self.assertEqual(
                conn.execute(
                    "SELECT dernier_metrage FROM machines WHERE id=?", (MACHINE_ID,)
                ).fetchone()[0],
                5000,
            )

        # Le compteur ne descend pas.
        r = self._saisie(metrage_compteur=4000, outil_avant_id=b["id"], outil_apres_id=a["id"])
        self.assertEqual(r.status_code, 400, r.text)

    def test_4b_le_changement_part_dans_le_commentaire(self):
        """Ce que le conducteur, le retour de prod et le point de production
        lisent, c'est la colonne commentaire. Les identifiants en base sont le
        dossier de référence ; sans cette phrase, l'information n'existerait
        que pour qui sait ouvrir la bonne colonne."""
        from database import get_db

        self._reset_compteur(None)
        a = self._outil("T-450")
        b = self._outil("T-451")
        r = self._saisie(
            metrage_compteur=14200, outil_avant_id=a["id"], outil_apres_id=b["id"]
        )
        self.assertEqual(r.status_code, 200, r.text)
        with get_db() as conn:
            commentaire = conn.execute(
                "SELECT commentaire FROM production_data WHERE machine=? "
                "ORDER BY id DESC LIMIT 1",
                (MACHINE_NOM,),
            ).fetchone()[0]
        self.assertEqual(commentaire, "Plaque T-450 → T-451 · compteur 14 200 m")

        # Un commentaire déjà saisi n'est pas écrasé : il suit la trace.
        self._saisie(
            metrage_compteur=14300, outil_avant_id=b["id"], outil_apres_id=a["id"],
            commentaire="casse en sortie",
        )
        with get_db() as conn:
            commentaire = conn.execute(
                "SELECT commentaire FROM production_data WHERE machine=? "
                "ORDER BY id DESC LIMIT 1",
                (MACHINE_NOM,),
            ).fetchone()[0]
        self.assertEqual(
            commentaire, "Plaque T-451 → T-450 · compteur 14 300 m — casse en sortie"
        )

    # ── 5. Un code sans nature d'outil n'écrit rien ──────────────────────
    def test_5_code_ordinaire_ignore_les_champs_outil(self):
        from database import get_db

        self._reset_compteur(None)
        a = self._outil("T-500")
        b = self._outil("T-501")
        r = self.client.post(
            "/api/fabrication/saisie",
            json={
                "operation": "63 - Pause",
                "machine_id": MACHINE_ID,
                "metrage_compteur": 7777,
                "outil_avant_id": a["id"],
                "outil_apres_id": b["id"],
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        with get_db() as conn:
            row = conn.execute(
                "SELECT metrage_compteur, outil_avant_id, outil_apres_id "
                "FROM production_data WHERE machine=? ORDER BY id DESC LIMIT 1",
                (MACHINE_NOM,),
            ).fetchone()
            self.assertIsNone(row["metrage_compteur"])
            self.assertIsNone(row["outil_avant_id"])
            self.assertIsNone(row["outil_apres_id"])
            self.assertIsNone(
                conn.execute(
                    "SELECT dernier_metrage FROM machines WHERE id=?", (MACHINE_ID,)
                ).fetchone()[0]
            )

    # ── 6. L'outil en place se lit sur la machine ────────────────────────
    def test_6_contexte_donne_le_dernier_outil_monte(self):
        self._reset_compteur(None)
        a = self._outil("T-600")
        b = self._outil("T-601")
        c = self._outil("T-602")

        self._saisie(metrage_compteur=100, outil_avant_id=a["id"], outil_apres_id=b["id"])
        # Dossier différent : l'outil en place ne change pas pour autant.
        self._saisie(
            metrage_compteur=200, outil_avant_id=b["id"], outil_apres_id=c["id"],
            no_dossier="D-AUTRE",
        )

        r = self.client.get(
            f"/api/fabrication/outils-contexte?code=60&machine_id={MACHINE_ID}"
        )
        self.assertEqual(r.status_code, 200, r.text)
        d = r.json()
        self.assertEqual(d["outil_type"], "plaque")
        self.assertEqual(d["type_label"], "Plaque")
        self.assertEqual(d["outil_actuel"]["id"], c["id"])
        self.assertEqual(d["dernier_metrage"], 200)

        # Un code sans nature d'outil ne renvoie aucun contexte.
        r = self.client.get(
            f"/api/fabrication/outils-contexte?code=63&machine_id={MACHINE_ID}"
        )
        self.assertIsNone(r.json()["outil_type"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
