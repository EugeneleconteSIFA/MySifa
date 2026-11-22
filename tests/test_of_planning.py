"""Étape « Planning » de la fenêtre OF : relier ou créer le dossier.

Ce que ces tests protègent :

1. Le bon dossier est trouvé, le plus sûr d'abord : déjà relié, puis même
   numéro, puis mêmes lignes de commande. Un dossier terminé sur la même
   commande n'est PAS proposé : c'est une production passée.
2. L'OF ne reporte que ce qui diffère, et jamais sur un dossier en cours ou
   terminé, ni sur un délai imposé. Une valeur absente de l'OF n'efface rien.
3. Relier passe par `_promote_of_link` (colonne et table de liens d'accord)
   et n'écrit que les champs cochés.

Lancement : `python3 tests/test_of_planning.py`
"""

import _base_temporaire  # noqa: E402,F401  — base jetable, avant config/database/app.*
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database  # noqa: E402,F401  — migre la base jetable
from database import get_db  # noqa: E402
from app.routers import of_planning as op  # noqa: E402


def _preparer(conn):
    conn.execute("DELETE FROM planning_of_links")
    conn.execute("DELETE FROM planning_entries")
    conn.execute("DELETE FROM of_imports")
    conn.execute("DELETE FROM rvgi_rattachements")
    m = conn.execute("SELECT id FROM machines ORDER BY id LIMIT 1").fetchone()["id"]
    conn.execute(
        "INSERT INTO of_imports (id, of_numero, reference, delai_client, laize, format, statut) "
        "VALUES (10, '9932501/L1', '890/0017 - COHESIO2 - L440', '02/10/2026', 450, '102 x 125 mm', 'en_attente')")
    # 1 : même numéro, en attente, délai et laize différents
    conn.execute(
        "INSERT INTO planning_entries (id, machine_id, position, reference, numero_of, statut, "
        "date_livraison, laize, format_l, format_h, ref_produit, a_placer) "
        "VALUES (1, ?, 5, '9932501/L1', '9932501/L1', 'attente', '2026-10-05', 440, 102, 125, '890/0017', 0)", (m,))
    # 2 : même commande, terminé -> jamais proposé
    conn.execute(
        "INSERT INTO planning_entries (id, machine_id, position, reference, numero_of, statut) "
        "VALUES (2, ?, 1, '9932501', '9932501', 'termine')", (m,))
    # 3 : même commande, en attente, délai imposé
    conn.execute(
        "INSERT INTO planning_entries (id, machine_id, position, reference, numero_of, statut, "
        "date_livraison, date_livraison_imposee) "
        "VALUES (3, ?, 6, 'Reliquat 9932501', 'Reliquat 9932501', 'attente', '2026-09-30', 1)", (m,))
    for oid in (2, 3):
        conn.execute(
            "INSERT INTO rvgi_rattachements (objet, objet_id, piece, numero, ligne, etat, cree_le) "
            "VALUES ('dossier', ?, 'commande', '9932501', 1, 'confirme', '2026-11-22')", (oid,))
    conn.commit()
    return m


class TestPlanningDepuisOF(unittest.TestCase):
    def setUp(self):
        with get_db() as conn:
            self.machine = _preparer(conn)

    def test_candidats_ordre_et_termine_exclu(self):
        with get_db() as conn:
            ds = op.candidats(conn, None, "9932501/L1", [{"numero": "9932501", "ligne": 1}])
        ids = [d["id"] for d in ds]
        self.assertEqual(ids, [1, 3])
        self.assertEqual(ds[0]["_raison"], "Même numéro d'OF")
        self.assertTrue(ds[1]["_raison"].startswith("Même commande 9932501/L1"))

    def test_ecarts_seulement_ce_qui_differe(self):
        with get_db() as conn:
            of = dict(conn.execute("SELECT * FROM of_imports WHERE id=10").fetchone())
            d1 = dict(conn.execute("SELECT * FROM planning_entries WHERE id=1").fetchone())
            d3 = dict(conn.execute("SELECT * FROM planning_entries WHERE id=3").fetchone())
        vals = op.valeurs_de_l_of(of)
        e1 = {e["champ"]: e for e in op.ecarts(d1, vals)}
        self.assertEqual(sorted(e1), ["date_livraison", "laize"])
        self.assertEqual((e1["date_livraison"]["avant"], e1["date_livraison"]["apres"]), ("05/10/2026", "02/10/2026"))
        self.assertTrue(all(e["modifiable"] for e in e1.values()))
        e3 = {e["champ"]: e for e in op.ecarts(d3, vals)}
        self.assertFalse(e3["date_livraison"]["modifiable"])
        self.assertEqual(e3["date_livraison"]["motif"], "Délai imposé au planning.")

    def test_dossier_en_cours_jamais_modifie(self):
        d = {"statut": "en_cours", "laize": 440}
        e = op.ecarts(d, {"laize": 450.0})
        self.assertFalse(e[0]["modifiable"])

    def test_valeur_absente_n_efface_rien(self):
        d = {"statut": "attente", "laize": 440, "date_livraison": "2026-10-05"}
        self.assertEqual(op.ecarts(d, {"laize": None, "date_livraison": None}), [])

    def test_relier_ecrit_seulement_les_champs_coches(self):
        with get_db() as conn:
            of = dict(conn.execute("SELECT * FROM of_imports WHERE id=10").fetchone())
            r = op._relier(conn, None, {"nom": "Essai"}, "Essai", "2026-11-22T10:00:00", of, 1, ["laize"])
            d = dict(conn.execute("SELECT * FROM planning_entries WHERE id=1").fetchone())
            lien = conn.execute("SELECT position FROM planning_of_links WHERE planning_entry_id=1 AND of_import_id=10").fetchone()
        self.assertTrue(r["ok"])
        self.assertEqual(float(d["laize"]), 450.0)
        self.assertEqual(d["date_livraison"], "2026-10-05")
        self.assertEqual(d["of_import_id"], 10)
        self.assertIsNotNone(lien)
        self.assertEqual(lien["position"], 0)

    def test_candidat_deja_relie_en_tete(self):
        with get_db() as conn:
            of = dict(conn.execute("SELECT * FROM of_imports WHERE id=10").fetchone())
            op._relier(conn, None, {"nom": "Essai"}, "Essai", "2026-11-22T10:00:00", of, 3, [])
            ds = op.candidats(conn, 10, "9932501/L1", [])
        self.assertEqual(ds[0]["id"], 3)
        self.assertEqual(ds[0]["_raison"], "Relié à cet OF")

    def test_suggestions_depuis_le_dossier(self):
        with get_db() as conn:
            conn.execute("INSERT INTO of_imports (id, of_numero, reference, date_import) "
                         "VALUES (11, 'AUTRE', '890/0017 - COHESIO1', '2026-11-01T10:00:00')")
            conn.execute("INSERT INTO of_imports (id, of_numero, reference, date_import) "
                         "VALUES (12, 'SANS RAPPORT', '1315/0004', '2026-11-20T10:00:00')")
            conn.commit()
            d = dict(conn.execute("SELECT * FROM planning_entries WHERE id=1").fetchone())
            s = op._ofs_suggeres(conn, d)
        ids = [o["id"] for o in s]
        self.assertEqual(ids[0], 10)           # même numéro d'abord
        self.assertEqual(s[0]["raison"], "Même numéro")
        self.assertIn(11, ids)                 # même produit ensuite
        self.assertNotIn(12, ids)              # un autre produit jamais

    def test_historique_de_la_machine_montre_le_geste(self):
        from app.services import planning_historique as ph
        with get_db() as conn:
            of = dict(conn.execute("SELECT * FROM of_imports WHERE id=10").fetchone())
            conn.execute("DELETE FROM audit_logs WHERE module='planning'")
            conn.commit()
            r = op._relier(conn, None, {"nom": "Essai"}, "Essai", "2026-11-22T10:00:00", of, 1, ["date_livraison"])
            res = ph.lister(conn, machine_id=self.machine, jours=None)
        self.assertEqual([e["libelle"] for e in r["ecrits"]], ["Délai"])
        self.assertEqual([g["libelle"] for g in r["gardes"]], ["Laize"])
        self.assertTrue(r["dossier"]["machine"])
        lignes = res.get("lignes") or res.get("items") or res.get("rows") or []
        self.assertTrue(lignes, "la ligne doit apparaître dans l'historique de la machine")
        l0 = lignes[0]
        self.assertEqual(l0.get("geste"), "Relié à l'OF 9932501/L1")
        self.assertIn({"champ": "Délai", "avant": "05/10/2026", "apres": "02/10/2026"}, l0.get("lignes"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
