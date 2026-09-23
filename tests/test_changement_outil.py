"""
Changement d'outil : le compteur machine, l'outil démonté, l'outil monté.

Ce que chaque bloc protège, posé les 22/09/2026 :

1. **La migration installe le référentiel, les quatre codes et leur source.**
   59 → contre-partie, 60 → plaque, 74 → magnétique, 75 → cliché ; et chaque
   nature sait dans quelle table du miroir RVGI aller chercher sa liste.
2. **Le référentiel ne crée jamais deux fois le même numéro**, réactive celui
   qu'on avait retiré plutôt que d'échouer, et refuse de renommer un outil
   sur un numéro déjà pris.
3. **La saisie part au CLIC, pas à la validation.** Un changement dure
   plusieurs minutes ; si l'heure n'était écrite qu'à la fin, elle serait
   fausse de toute la durée de la recherche. La réponse porte de quoi ouvrir
   le formulaire, et le compteur machine n'a pas encore bougé.
4. **La complétion écrit les trois informations et la phrase lisible**, fait
   avancer le compteur machine, et ne duplique pas sa trace quand on corrige.
5. **Elle refuse ce qui ne veut rien dire** : pas de compteur, un seul outil,
   deux fois le même, un outil d'une autre nature, un compteur qui descend.
6. **« Annuler » supprime la saisie qui vient de partir** — et seulement
   celle-là : un changement déjà enregistré ne se supprime pas par ce chemin.
7. **La recherche interroge les trois sources d'un coup** — référentiel local,
   miroir RVGI, fiches techniques — et propose de créer le numéro tapé quand
   il n'existe nulle part. Un numéro venu de RVGI n'est pas « à valider » :
   il existe déjà ailleurs, il n'a pas été inventé au poste.
8. **Un code sans nature d'outil n'écrit ni compteur ni outil**, même si le
   corps de requête en porte.
9. **L'outil en place se lit sur la MACHINE, pas sur le dossier** : un outil
   reste monté d'un dossier au suivant.

Lancer : python3 tests/test_changement_outil.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Bases isolées avant tout import projet (init_db au chargement de database.py,
# et config lit ERP_MIRROR_DB à l'import).
_tmp = tempfile.mkdtemp(prefix="mysifa_outil_test_")
_db = os.path.join(_tmp, "test.db")
_miroir = os.path.join(_tmp, "erp_mirror.db")
os.environ["DB_PATH"] = _db
os.environ["ERP_MIRROR_DB"] = _miroir

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MACHINE_ID = 90101
MACHINE_NOM = "Test Outil 1"
USER = {"id": 1, "nom": "Testeur", "email": "test@local", "role": "direction"}


def _construire_miroir():
    """Un miroir RVGI minuscule, avec les trois tables que les natures visent.
    Les colonnes sont celles que le service lit — pas le schéma complet."""
    c = sqlite3.connect(_miroir)
    c.executescript(
        """
        CREATE TABLE out_dec (id INTEGER PRIMARY KEY, corbeille INTEGER, type INTEGER,
            numero INTEGER, code TEXT, nbl INTEGER, nba INTEGER);
        INSERT INTO out_dec (corbeille,type,numero,code,nbl,nba) VALUES
            (0,2,9920,NULL,4,3), (0,2,9918,'1002',4,7), (0,2,2867,NULL,6,4),
            (1,2,7777,NULL,1,1);
        CREATE TABLE out_cyl (id INTEGER PRIMARY KEY, corbeille INTEGER, type INTEGER,
            code TEXT, nbd INTEGER, qte INTEGER);
        INSERT INTO out_cyl (corbeille,type,code,nbd,qte) VALUES
            (0,2,NULL,134,4), (0,3,'160',160,1), (0,4,'CP-25',192,1),
            (0,5,'800',8,2);
        CREATE TABLE mat_mat (id INTEGER PRIMARY KEY, corbeille INTEGER, type INTEGER,
            code1 TEXT, code2 TEXT, libc1 TEXT, ref TEXT);
        INSERT INTO mat_mat (corbeille,type,code1,code2,libc1,ref) VALUES
            (0,9,'897','0287','Ronds 40 mm, 1 coul., rouge','1041/0004'),
            (0,9,'897','0286','Cliché 59 x 50 mm, 2 couleurs','748/0016'),
            (0,1,'100','0001','Une matière, pas un cliché',NULL);
        """
    )
    c.commit()
    c.close()


_construire_miroir()


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

    def _clic(self, operation="60 - Changement Plaque", **body):
        corps = {"operation": operation, "machine_id": MACHINE_ID}
        corps.update(body)
        return self.client.post("/api/fabrication/saisie", json=corps)

    def _completer(self, saisie_id, **body):
        return self.client.put(
            f"/api/fabrication/saisie/{saisie_id}/changement-outil", json=body
        )

    @staticmethod
    def _reset(compteur=None):
        from database import get_db

        with get_db() as conn:
            conn.execute(
                "UPDATE machines SET dernier_metrage=? WHERE id=?", (compteur, MACHINE_ID)
            )
            conn.execute("DELETE FROM production_data WHERE machine = ?", (MACHINE_NOM,))
            conn.commit()

    @staticmethod
    def _derniere():
        from database import get_db

        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM production_data WHERE machine=? ORDER BY id DESC LIMIT 1",
                (MACHINE_NOM,),
            ).fetchone()
            compteur = conn.execute(
                "SELECT dernier_metrage FROM machines WHERE id=?", (MACHINE_ID,)
            ).fetchone()[0]
        return (dict(row) if row else None), compteur

    # ── 1. Migration ─────────────────────────────────────────────────────
    def test_1_migration_installe_referentiel_et_sources(self):
        from database import get_db

        with get_db() as conn:
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
            sources = {
                r["cle"]: (r["source_table"], r["source_types"])
                for r in conn.execute(
                    "SELECT cle, source_table, source_types FROM outil_types"
                )
            }
            self.assertEqual(sources["plaque"], ("out_dec", ""))
            self.assertEqual(sources["magnetique"], ("out_cyl", "2,3"))
            self.assertEqual(sources["contre_partie"], ("out_cyl", "4"))
            self.assertEqual(sources["cliche"], ("mat_mat", "9"))
            cols = {r[1] for r in conn.execute("PRAGMA table_info(production_data)")}
            self.assertLessEqual(
                {"metrage_compteur", "outil_avant_id", "outil_apres_id"}, cols
            )

    # ── 2. Référentiel ───────────────────────────────────────────────────
    def test_2_referentiel_unicite_et_reactivation(self):
        from database import get_db
        from app.services import outils as ref

        a = self._outil("T-100")
        self.assertEqual(self._outil("T-100")["id"], a["id"])
        with get_db() as conn:
            ref.maj_outil(conn, a["id"], actif=False)
            remis = ref.creer_outil(conn, type_cle="plaque", numero="T-100")
            self.assertTrue(remis["actif"])
            self.assertEqual(remis["id"], a["id"])
            autre = ref.creer_outil(conn, type_cle="plaque", numero="T-101")
            with self.assertRaises(ValueError):
                ref.maj_outil(conn, autre["id"], numero="T-100")
            # Même numéro, autre nature : deux outils distincts.
            self.assertNotEqual(
                ref.creer_outil(conn, type_cle="cliche", numero="T-100")["id"], a["id"]
            )

    # ── 3. La saisie part au clic ────────────────────────────────────────
    def test_3_la_saisie_part_au_clic(self):
        self._reset(None)
        r = self._clic()
        self.assertEqual(r.status_code, 200, r.text)
        d = r.json()
        self.assertIn("outil_requis", d)
        ctx = d["outil_requis"]
        self.assertEqual(ctx["saisie_id"], d["id"])
        self.assertEqual(ctx["outil_type"], "plaque")
        self.assertEqual(ctx["type_label"], "Plaque")

        row, compteur = self._derniere()
        self.assertEqual(row["operation_code"], "60")
        self.assertIsNone(row["outil_apres_id"])
        # Rien n'est acquis tant que le conducteur n'a pas validé.
        self.assertIsNone(row["metrage_compteur"])
        self.assertIsNone(compteur)

    # ── 4. Complétion ────────────────────────────────────────────────────
    def test_4_completion_ecrit_tout_et_ne_duplique_pas(self):
        self._reset(None)
        a = self._outil("T-400")
        b = self._outil("T-401")
        sid = self._clic().json()["id"]

        r = self._completer(
            sid, metrage_compteur=14200, outil_avant_id=a["id"], outil_apres_id=b["id"]
        )
        self.assertEqual(r.status_code, 200, r.text)
        row, compteur = self._derniere()
        self.assertEqual(row["metrage_compteur"], 14200)
        self.assertEqual(row["outil_avant_id"], a["id"])
        self.assertEqual(row["outil_apres_id"], b["id"])
        self.assertEqual(row["commentaire"], "Plaque T-400 → T-401 · compteur 14 200 m")
        self.assertEqual(compteur, 14200)
        # Les colonnes historiques restent vierges : la rentabilité les lit sans
        # filtrer sur le code, y écrire fausserait les vitesses.
        self.assertIsNone(row["metrage_prevu"])
        self.assertIsNone(row["metrage_reel"])

        # Correction : la trace est reconstruite, pas empilée.
        r = self._completer(
            sid, metrage_compteur=14300, outil_avant_id=a["id"], outil_apres_id=b["id"]
        )
        self.assertEqual(r.status_code, 200, r.text)
        row, _ = self._derniere()
        self.assertEqual(row["commentaire"], "Plaque T-400 → T-401 · compteur 14 300 m")

    def test_4b_le_commentaire_du_conducteur_est_conserve(self):
        self._reset(None)
        a = self._outil("T-450")
        b = self._outil("T-451")
        sid = self._clic(commentaire="casse en sortie").json()["id"]
        self._completer(
            sid, metrage_compteur=500, outil_avant_id=a["id"], outil_apres_id=b["id"]
        )
        row, _ = self._derniere()
        self.assertEqual(
            row["commentaire"], "Plaque T-450 → T-451 · compteur 500 m — casse en sortie"
        )

    # ── 5. Ce qui est refusé ─────────────────────────────────────────────
    def test_5_completion_incomplete_refusee(self):
        self._reset(None)
        a = self._outil("T-500")
        b = self._outil("T-501")
        cliche = self._outil("T-502", type_cle="cliche")
        sid = self._clic().json()["id"]

        self.assertEqual(
            self._completer(sid, outil_avant_id=a["id"], outil_apres_id=b["id"]).status_code,
            400, "compteur absent",
        )
        self.assertEqual(
            self._completer(sid, metrage_compteur=1000).status_code,
            400, "outils absents",
        )
        self.assertEqual(
            self._completer(sid, metrage_compteur=1000,
                            outil_avant_id=a["id"], outil_apres_id=a["id"]).status_code,
            400, "même outil des deux côtés",
        )
        self.assertEqual(
            self._completer(sid, metrage_compteur=1000,
                            outil_avant_id=a["id"], outil_apres_id=999999).status_code,
            422, "outil hors référentiel",
        )
        self.assertEqual(
            self._completer(sid, metrage_compteur=1000,
                            outil_avant_id=a["id"], outil_apres_id=cliche["id"]).status_code,
            422, "nature d'outil incohérente",
        )
        # Le compteur ne descend pas sous le dernier relevé antérieur.
        self._completer(sid, metrage_compteur=5000,
                        outil_avant_id=a["id"], outil_apres_id=b["id"])
        sid2 = self._clic().json()["id"]
        self.assertEqual(
            self._completer(sid2, metrage_compteur=4000,
                            outil_avant_id=b["id"], outil_apres_id=a["id"]).status_code,
            400, "compteur en baisse",
        )

    # ── 6. Annulation ────────────────────────────────────────────────────
    def test_6_annuler_supprime_la_saisie_du_clic(self):
        from database import get_db

        self._reset(None)
        sid = self._clic().json()["id"]
        r = self.client.delete(f"/api/fabrication/saisie/{sid}/changement-outil")
        self.assertEqual(r.status_code, 200, r.text)
        with get_db() as conn:
            self.assertIsNone(
                conn.execute(
                    "SELECT id FROM production_data WHERE id=?", (sid,)
                ).fetchone()
            )

        # Un changement déjà enregistré ne se supprime pas par ce chemin.
        a = self._outil("T-600")
        b = self._outil("T-601")
        sid2 = self._clic().json()["id"]
        self._completer(sid2, metrage_compteur=100,
                        outil_avant_id=a["id"], outil_apres_id=b["id"])
        self.assertEqual(
            self.client.delete(f"/api/fabrication/saisie/{sid2}/changement-outil").status_code,
            409,
        )

    # ── 7. Recherche multi-sources ───────────────────────────────────────
    def test_7_recherche_les_trois_sources(self):
        self._outil("T-700")

        r = self.client.get("/api/fabrication/outils/recherche?type=plaque&q=T-700")
        self.assertEqual(r.status_code, 200, r.text)
        d = r.json()
        self.assertEqual([o["numero"] for o in d["resultats"]], ["T-700"])
        self.assertEqual(d["resultats"][0]["origine"], "referentiel")
        self.assertIsNone(d["creation"], "le numéro existe déjà")

        # RVGI : les outils de découpe pour la plaque, corbeille exclue.
        d = self.client.get("/api/fabrication/outils/recherche?type=plaque&q=99").json()
        numeros = [o["numero"] for o in d["resultats"]]
        self.assertIn("9920", numeros)
        self.assertIn("9918", numeros)
        self.assertNotIn("7777", numeros, "ligne en corbeille")
        self.assertEqual(
            next(o for o in d["resultats"] if o["numero"] == "9920")["origine"], "rvgi"
        )

        # Le magnétique se nomme par son nombre de dents, et ne voit que les
        # types que sa nature déclare (2 et 3, pas l'anilox en 5).
        d = self.client.get("/api/fabrication/outils/recherche?type=magnetique").json()
        numeros = [o["numero"] for o in d["resultats"]]
        self.assertIn("134", numeros)
        self.assertIn("160", numeros)
        self.assertNotIn("800", numeros, "anilox : pas cette nature")
        self.assertNotIn("CP-25", numeros, "contre-partie : pas cette nature")

        d = self.client.get("/api/fabrication/outils/recherche?type=contre_partie").json()
        self.assertEqual([o["numero"] for o in d["resultats"]], ["CP-25"])

        # Le cliché se référence par code1/code2, avec son libellé.
        d = self.client.get("/api/fabrication/outils/recherche?type=cliche&q=0286").json()
        self.assertEqual([o["numero"] for o in d["resultats"]], ["897/0286"])
        self.assertEqual(
            d["resultats"][0]["label"], "Cliché 59 x 50 mm, 2 couleurs"
        )

        # Un terme qui n'existe nulle part se propose à la création.
        d = self.client.get("/api/fabrication/outils/recherche?type=plaque&q=ZZ-9").json()
        self.assertEqual(d["creation"], "ZZ-9")
        self.assertEqual(d["resultats"], [])

    def test_7b_origine_decide_du_a_valider(self):
        depuis_rvgi = self.client.post(
            "/api/fabrication/outils",
            json={"type": "plaque", "numero": "9920", "origine": "rvgi"},
        ).json()
        self.assertFalse(depuis_rvgi["a_valider"], "9920 existe dans RVGI")

        invente = self.client.post(
            "/api/fabrication/outils",
            json={"type": "plaque", "numero": "T-750", "origine": "poste"},
        ).json()
        self.assertTrue(invente["a_valider"])

        # Rejouer la même résolution ne recrée rien.
        self.assertEqual(
            self.client.post(
                "/api/fabrication/outils",
                json={"type": "plaque", "numero": "9920", "origine": "rvgi"},
            ).json()["id"],
            depuis_rvgi["id"],
        )

    # ── 8. Un code sans nature d'outil ───────────────────────────────────
    def test_8_code_ordinaire_ignore_les_champs_outil(self):
        self._reset(None)
        a = self._outil("T-800")
        b = self._outil("T-801")
        r = self._clic(
            operation="63 - Pause", metrage_compteur=7777,
            outil_avant_id=a["id"], outil_apres_id=b["id"],
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertNotIn("outil_requis", r.json())
        row, compteur = self._derniere()
        self.assertIsNone(row["metrage_compteur"])
        self.assertIsNone(row["outil_avant_id"])
        self.assertIsNone(row["outil_apres_id"])
        self.assertIsNone(compteur)

    # ── 9. L'outil en place se lit sur la machine ────────────────────────
    def test_9_outil_en_place_suit_la_machine(self):
        self._reset(None)
        a = self._outil("T-900")
        b = self._outil("T-901")
        c = self._outil("T-902")

        sid = self._clic().json()["id"]
        self._completer(sid, metrage_compteur=100,
                        outil_avant_id=a["id"], outil_apres_id=b["id"])
        # Dossier différent : l'outil en place ne change pas pour autant.
        sid2 = self._clic(no_dossier="D-AUTRE").json()["id"]
        self._completer(sid2, metrage_compteur=200,
                        outil_avant_id=b["id"], outil_apres_id=c["id"])

        sid3 = self._clic().json()["id"]
        ctx = self.client.get(
            f"/api/fabrication/saisie/{sid3}/changement-outil"
        ).json()
        self.assertEqual(ctx["outil_actuel"]["id"], c["id"])
        self.assertEqual(ctx["dernier_metrage"], 200)
        self.assertFalse(ctx["deja_complete"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
