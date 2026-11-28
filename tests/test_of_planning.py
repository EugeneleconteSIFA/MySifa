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

    def test_supprimer_un_of_detache_proprement_le_dossier(self):
        with get_db() as conn:
            conn.execute("INSERT INTO of_imports (id, of_numero, reference) VALUES (11, 'RELAIS', '890/0017')")
            of10 = dict(conn.execute("SELECT * FROM of_imports WHERE id=10").fetchone())
            op._relier(conn, None, {"nom": "Essai"}, "Essai", "2026-11-22T10:00:00", of10, 1, [])
            conn.execute("INSERT INTO planning_of_links (planning_entry_id, of_import_id, position) VALUES (1, 11, 1)")
            conn.commit()
            avant = op.dossiers_des_of(conn, [10])
            self.assertEqual(avant[10][0]["relais"], "RELAIS")
            # 1. L'OF actif part : le suivant prend le relais.
            op.detacher_of(conn, [10])
            conn.execute("DELETE FROM of_imports WHERE id=10")
            conn.commit()
            self.assertEqual(conn.execute("SELECT of_import_id FROM planning_entries WHERE id=1").fetchone()[0], 11)
            # 2. Le dernier part : le dossier repasse sans OF, sans lien orphelin.
            op.detacher_of(conn, [11])
            conn.execute("DELETE FROM of_imports WHERE id=11")
            conn.commit()
            self.assertIsNone(conn.execute("SELECT of_import_id FROM planning_entries WHERE id=1").fetchone()[0])
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM planning_of_links WHERE planning_entry_id=1").fetchone()[0], 0)

    def test_etat_des_of_et_reutilisation(self):
        from datetime import datetime, timedelta
        from fastapi import HTTPException
        vieux = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%S")
        hier = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
        il_y_a_200j = (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d")
        with get_db() as conn:
            m = self.machine
            for oid, num, cree in ((20, 'LIBRE', None), (21, 'ANCIEN', il_y_a_200j), (22, 'PRODUIT', None),
                                   (23, 'PASSE', None), (24, 'ENCOURS', None), (25, 'RECENT', None)):
                conn.execute("INSERT INTO of_imports (id, of_numero, date_creation, date_import) VALUES (?,?,?,?)",
                             (oid, num, cree, datetime.now().strftime("%Y-%m-%dT%H:%M:%S")))
            # Dossiers déjà passés : un autre produit terminé il y a 60 jours, la
            # même référence que la cible, un en attente, un terminé hier.
            for eid, ref, statut, fin, of_id in ((30, 'AUTRE', 'termine', vieux, 22), (31, '9932501/L1', 'termine', vieux, 23),
                                                 (32, 'AILLEURS', 'attente', None, 24), (33, 'HIER', 'termine', hier, 25)):
                conn.execute("INSERT INTO planning_entries (id, machine_id, position, reference, statut, planned_end, duree_heures, created_at, updated_at) "
                             "VALUES (?,?,?,?,?,?,8,'2026-01-01','2026-01-01')", (eid, m, eid, ref, statut, fin))
                conn.execute("INSERT INTO planning_of_links (planning_entry_id, of_import_id, position) VALUES (?,?,0)", (eid, of_id))
            conn.commit()
            cible = {"id": 1, "reference": "9932501/L1"}
            e = op.etat_des_of(conn, [20, 21, 22, 23, 24, 25], cible)
            self.assertEqual({k: v["etat"] for k, v in e.items()},
                             {20: "libre", 21: "ancien", 22: "produit", 23: "passe", 24: "en_cours", 25: "recent"})
            self.assertFalse(e[22]["selectionnable"])
            self.assertIn("créez un nouvel OF", e[22]["note"])
            self.assertTrue(all(e[i]["selectionnable"] for i in (20, 21, 23, 24, 25)))
            with self.assertRaises(HTTPException) as ctx:
                op.verifier_reutilisable(conn, [22], 1)
            self.assertEqual(ctx.exception.status_code, 409)
            op.verifier_reutilisable(conn, [20, 23, 24, 25], 1)   # aucun refus

    def test_rapprochement_par_produit_jamais_automatique(self):
        """Un dossier « Stock 1153/0005 » ne se relie plus tout seul à l'OF du
        même produit : candidats à valider seulement, sans OF ancien."""
        from app.routers.of_import import _lookup_of_candidates
        from datetime import datetime, timedelta
        recent = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        with get_db() as conn:
            conn.execute("INSERT INTO of_imports (id, of_numero, reference, date_creation, date_import) "
                         "VALUES (40, '1153/0005 - 01/04/26', '1153/0005', '2026-04-01', '2026-06-02T09:00:00')")
            conn.commit()
            certain, cands = _lookup_of_candidates("Stock 1153/0005", "1153/0005", conn=conn)
            self.assertIsNone(certain)
            self.assertEqual(cands, [])            # OF ancien jamais planifié : écarté
            conn.execute("INSERT INTO of_imports (id, of_numero, reference, date_creation, date_import) "
                         "VALUES (41, 'Stock 1153/0005 bis', '1153/0005', ?, ?)",
                         (recent, datetime.now().strftime("%Y-%m-%dT%H:%M:%S")))
            conn.commit()
            certain, cands = _lookup_of_candidates("Stock 1153/0005", "1153/0005", conn=conn)
            self.assertIsNone(certain)             # jamais certain par le produit seul
            self.assertEqual([c["id"] for c in cands], [41])

    def test_commande_retrouvee_par_le_numero_du_dossier(self):
        lignes = [{"numero": "9932911", "ligne": 1, "qte": 100000, "article": "1068/0006", "client": "Maitre Coq"},
                  {"numero": "9932911", "ligne": 2, "qte": 50000, "article": "1068/0007", "client": "Maitre Coq"}]
        avant = op.ratt.chercher_commandes
        op.ratt.chercher_commandes = lambda q, *a, **k: [{"numero": "9932911", "lignes": lignes}]
        try:
            l, num = op.commande_du_dossier({"numero_of": "9932911", "reference": "9932911", "ref_produit": "1068/0006"})
            self.assertEqual((num, [x["ligne"] for x in l]), ("9932911", [1]))     # l'article du dossier
            l, _ = op.commande_du_dossier({"numero_of": "9932911 ligne 2", "reference": "9932911 ligne 2"})
            self.assertEqual([x["ligne"] for x in l], [2])                          # la ligne citée
            l, num = op.commande_du_dossier({"numero_of": "9932911", "reference": "9932911", "ref_produit": "999/0001"})
            self.assertEqual((l, num), ([], None))                                  # jamais au hasard
            l, num = op.commande_du_dossier({"numero_of": "Stock 1153/0024", "reference": "Stock 1153/0024"})
            self.assertEqual((l, num), ([], None))                                  # un stock n'a pas de commande
        finally:
            op.ratt.chercher_commandes = avant


class TestReservation(unittest.TestCase):
    """Dossier réservé au planning sans numéro (« ???? », 26/11/2026)."""

    def setUp(self):
        with get_db() as conn:
            self.machine = _preparer(conn)
            conn.execute(
                "INSERT INTO planning_entries (id, machine_id, position, reference, numero_of, statut, client) "
                "VALUES (20, ?, 9, '????', '????', 'attente', 'KIABI')", (self.machine,))
            conn.execute(
                "INSERT INTO of_imports (id, of_numero, reference, statut) "
                "VALUES (30, '9932950', '1027/0011 - DSI', 'en_attente')")
            conn.commit()

    def test_motif(self):
        for ref in ("????", "?????", "XXXXXXX", "? ? ?", ""):
            self.assertTrue(op.reference_a_venir(ref), ref)
        for ref in ("9932911", "Stock 1153/0005", "Marché 779", "X12"):
            self.assertFalse(op.reference_a_venir(ref), ref)

    def test_trouvee_par_le_dossier_de_depart(self):
        with get_db() as conn:
            self.assertEqual(op.candidats(conn, None, "9932950", []), [])
            ds = op.candidats(conn, None, "9932950", [], depart=20)
        self.assertEqual([d["id"] for d in ds], [20])
        self.assertEqual(ds[0]["_raison"], "Dossier de départ")

    def test_reference_proposee_et_remplacee(self):
        with get_db() as conn:
            of = dict(conn.execute("SELECT * FROM of_imports WHERE id=30").fetchone())
            d = dict(conn.execute("SELECT * FROM planning_entries WHERE id=20").fetchone())
            e = {x["champ"]: x for x in op.ecarts(d, op.valeurs_de_l_of(of), conn)}
            self.assertEqual((e["reference"]["avant"], e["reference"]["apres"]), ("????", "9932950"))
            self.assertTrue(e["reference"]["modifiable"])
            r = op._relier(conn, None, {"nom": "Essai"}, "Essai", "2026-11-26T10:00:00", of, 20,
                           ["reference", "numero_of"])
            apres = dict(conn.execute("SELECT reference, numero_of FROM planning_entries WHERE id=20").fetchone())
        self.assertEqual(apres, {"reference": "9932950", "numero_of": "9932950"})
        self.assertIn("9932950", r["message"])

    def test_vrai_numero_jamais_renomme(self):
        with get_db() as conn:
            of = dict(conn.execute("SELECT * FROM of_imports WHERE id=30").fetchone())
            d = dict(conn.execute("SELECT * FROM planning_entries WHERE id=1").fetchone())
            champs = [x["champ"] for x in op.ecarts(d, op.valeurs_de_l_of(of), conn)]
        self.assertNotIn("reference", champs)

    def test_reference_deja_prise_refusee(self):
        with get_db() as conn:
            conn.execute("UPDATE of_imports SET of_numero='9932501/L1' WHERE id=30")
            of = dict(conn.execute("SELECT * FROM of_imports WHERE id=30").fetchone())
            d = dict(conn.execute("SELECT * FROM planning_entries WHERE id=20").fetchone())
            e = {x["champ"]: x for x in op.ecarts(d, op.valeurs_de_l_of(of), conn)}
        self.assertFalse(e["reference"]["modifiable"])
        self.assertIn("9932501/L1", e["reference"]["motif"])


class TestCreerDossierDepuisOF(unittest.TestCase):
    """Bouton « Créer directement un dossier de prod » (26/11/2026)."""

    def setUp(self):
        from app.routers import of_import as oi
        self.oi = oi
        self._garde = oi._require_of_access
        oi._require_of_access = lambda request: {"nom": "Essai"}
        with get_db() as conn:
            self.machine = _preparer(conn)
            nom = conn.execute("SELECT nom FROM machines WHERE id=?", (self.machine,)).fetchone()["nom"]
            # OF libre, machine écrite à la façon d'Access (majuscules, sans accent).
            import unicodedata
            brut = "".join(c for c in unicodedata.normalize("NFKD", nom) if not unicodedata.combining(c)).upper()
            conn.execute("INSERT INTO of_imports (id, of_numero, reference, machine, statut) "
                         "VALUES (40, '9932501/L1', '890/0017 - X', ?, 'en_attente')", (brut,))
            conn.commit()

    def tearDown(self):
        self.oi._require_of_access = self._garde

    def test_of_qui_a_deja_son_dossier(self):
        with get_db() as conn:
            conn.execute("UPDATE planning_entries SET of_import_id=10 WHERE id=1")
            conn.commit()
        p = self.oi.of_dossier_prefill(10, None)
        self.assertEqual((p["dossier_existant"] or {}).get("id"), 1)
        self.assertEqual(p["correspondants"], [])

    def test_dossier_correspondant_propose(self):
        # Dossier 1 libre de tout OF (le jeu le relie à l'OF 10 par son numéro).
        with get_db() as conn:
            conn.execute("DELETE FROM planning_of_links WHERE planning_entry_id=1")
            conn.execute("UPDATE planning_entries SET of_import_id=NULL WHERE id=1")
            conn.commit()
        p = self.oi.of_dossier_prefill(40, None)
        self.assertIsNone(p["dossier_existant"])
        self.assertIn(1, [d["id"] for d in p["correspondants"]])

    def test_dossier_relie_a_un_autre_of_ecarte(self):
        p = self.oi.of_dossier_prefill(40, None)
        self.assertNotIn(1, [d["id"] for d in p["correspondants"]])

    def test_machine_reconnue_sans_accent(self):
        p = self.oi.of_dossier_prefill(40, None)
        self.assertEqual(p["machine_id"], self.machine)


class TestConcordance(unittest.TestCase):
    """OF et dossier à produire qui se contredisent, contrôlé en continu."""

    def setUp(self):
        with get_db() as conn:
            self.machine = _preparer(conn)
            conn.execute("DELETE FROM planning_of_links")
            conn.execute("UPDATE planning_entries SET of_import_id=NULL")
            # Dossier 1 (890/0017, délai 05/10, laize 440) relié à l'OF 10
            # (délai 02/10, laize 450) : deux écarts.
            conn.execute("UPDATE planning_entries SET of_import_id=10 WHERE id=1")
            # OF de la commande entière, autre produit, sur un dossier de ligne.
            conn.execute("INSERT INTO of_imports (id, of_numero, reference, statut) "
                         "VALUES (11, '9932765', '1411/0002', 'en_attente')")
            conn.execute("INSERT INTO planning_entries (id, machine_id, position, reference, numero_of, statut, ref_produit, of_import_id) "
                         "VALUES (30, ?, 7, '9932765 - L1', '9932765 - L1', 'attente', '1411/0001', 11)", (self.machine,))
            # « Stock … » rangé par Access dans la référence : pas un produit.
            conn.execute("INSERT INTO of_imports (id, of_numero, reference, statut) "
                         "VALUES (12, 'Stock 1153/0005', 'Stock 1153/0005', 'en_attente')")
            conn.execute("INSERT INTO planning_entries (id, machine_id, position, reference, numero_of, statut, ref_produit, of_import_id) "
                         "VALUES (31, ?, 8, 'Stock 1153/0005', 'Stock 1153/0005', 'attente', '1153/0005', 12)", (self.machine,))
            # Dossier terminé : plus contrôlé.
            conn.execute("UPDATE planning_entries SET of_import_id=11 WHERE id=2")
            conn.commit()

    def test_ecarts_releves(self):
        with get_db() as conn:
            res = op.concordance_dossiers(conn)
        self.assertEqual(sorted(e["champ"] for e in res[1]["ecarts"]), ["date_livraison", "laize"])
        self.assertEqual([e["champ"] for e in res[30]["ecarts"]], ["ref_produit"])
        self.assertEqual(res[30]["of_numero"], "9932765")

    def test_stock_et_termine_ignores(self):
        with get_db() as conn:
            res = op.concordance_dossiers(conn)
        self.assertNotIn(31, res)
        self.assertNotIn(2, res)

    def test_report_supprime_l_ecart(self):
        with get_db() as conn:
            of = dict(conn.execute("SELECT * FROM of_imports WHERE id=10").fetchone())
            op._relier(conn, None, {"nom": "Essai"}, "Essai", "2026-11-26T20:00:00", of, 1, ["date_livraison", "laize"])
            res = op.concordance_dossiers(conn, [1])
        self.assertNotIn(1, res)


class TestMemeCommandeDansLeNumero(unittest.TestCase):
    """OF « 9932957 - L1 » : les dossiers « 9932957 » sont proposés,
    pas celui d'une autre ligne (28/11/2026)."""

    def setUp(self):
        with get_db() as conn:
            m = _preparer(conn)
            for i, ref in ((40, "9932957"), (41, "9932957"), (42, "9932957 - L2"), (43, "9932957 - L1")):
                conn.execute("INSERT INTO planning_entries (id, machine_id, position, reference, numero_of, statut) "
                             "VALUES (?, ?, ?, ?, ?, 'attente')", (i, m, 20 + i, ref, ref))
            conn.commit()

    def test_dossiers_de_la_commande(self):
        with get_db() as conn:
            ids = [d["id"] for d in op.candidats(conn, None, "9932957 - L1", [])]
        self.assertEqual(ids[0], 43)              # même numéro d'abord
        self.assertIn(40, ids)
        self.assertIn(41, ids)
        self.assertNotIn(42, ids)                 # autre ligne


if __name__ == "__main__":
    unittest.main(verbosity=2)
