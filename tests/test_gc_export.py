"""
Nouvel ERP — export comptable FEC (app/services/gc/export_compta.py).

1. Sur le jeu de démonstration, toutes les écritures sont équilibrées et
   tous les comptes renseignés.
2. Une facture : client au débit TTC, ventes et TVA au crédit ; un avoir :
   l'inverse.
3. La remise de pied est répartie sans perdre un centime.
4. Le fichier FEC a ses 18 colonnes, des dates AAAAMMJJ et des montants à
   virgule.

Lancer : python3 tests/test_gc_export.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mysifa_gc_export_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database  # noqa: E402,F401 — le shim d'abord (CLAUDE.md)
from database import get_db  # noqa: E402
from app.services.gc import demo, export_compta, pieces  # noqa: E402


class Export(unittest.TestCase):
    def setUp(self):
        self.ctx = get_db()
        self.c = self.ctx.__enter__()
        demo.reinitialiser(self.c)

    def tearDown(self):
        self.c.rollback()
        self.ctx.__exit__(None, None, None)

    def test_demo_equilibree(self):
        l = export_compta.ecritures(self.c, "2000-01-01", "2999-12-31")
        self.assertTrue(l)
        self.assertEqual(export_compta.controles(l), [])
        self.assertEqual(sum(x["debit_cents"] for x in l), sum(x["credit_cents"] for x in l))
        journaux = {x["JournalCode"] for x in l}
        self.assertEqual(journaux, {"VT", "BQ"})

    def test_facture_avoir_remise(self):
        c = self.c
        t = c.execute("SELECT id FROM gc_tiers WHERE code='C0002'").fetchone()["id"]   # remise 2 %
        a = {r["code"]: r["id"] for r in c.execute("SELECT id, code FROM gc_articles").fetchall()}
        a["PF0002"] = c.execute("SELECT id FROM gc_articles WHERE client_id=? AND nature='pf'", (t,)).fetchone()["id"]
        co = pieces.creer(c, "commande", t)
        pieces.enregistrer(c, co, {"date_piece": "2026-05-01"}, [
            {"article_id": a["PF0002"], "quantite_milli": 3_333_000, "prix_cents": 2800, "base_prix": 1000},
            {"article_id": a["PR0001"], "quantite_milli": 1000, "prix_cents": 8501}])
        pieces.valider(c, co)
        bl = pieces.transformer(c, [co], "bl")
        pieces.enregistrer(c, bl, {"date_piece": "2026-05-02"}, None)
        pieces.valider(c, bl)
        fa = pieces.transformer(c, [bl], "facture")
        pieces.enregistrer(c, fa, {"date_piece": "2026-05-03"}, None)
        pieces.valider(c, fa)
        av = pieces.transformer(c, [fa], "avoir")
        pieces.enregistrer(c, av, {"date_piece": "2026-05-04"}, None)
        pieces.valider(c, av)
        l = export_compta.ecritures(c, "2026-05-01", "2026-05-31")
        self.assertEqual(export_compta.controles(l), [])
        f = [x for x in l if x["PieceRef"] == pieces.charger(c, fa)["numero"]]
        clients = [x for x in f if x["CompteNum"] == "411000"]
        self.assertEqual(clients[0]["debit_cents"], pieces.charger(c, fa)["total_ttc_cents"])
        self.assertEqual({x["CompteNum"] for x in f}, {"411000", "701000", "706000", "445713"})
        v = [x for x in l if x["PieceRef"] == pieces.charger(c, av)["numero"]]
        self.assertEqual([x for x in v if x["CompteNum"] == "411000"][0]["credit_cents"],
                         pieces.charger(c, av)["total_ttc_cents"])

    def test_banque_du_reglement(self):
        from app.services.gc import compta
        c = self.c
        c.execute("INSERT INTO gc_banques (code, libelle, compte, journal) VALUES ('CIC', 'CIC', '512100', 'BQ1')")
        e = c.execute("""SELECT e.id, p.tiers_id FROM gc_echeances e JOIN gc_pieces p ON p.id=e.piece_id
                         WHERE e.montant_cents > e.regle_cents LIMIT 1""").fetchone()
        compta.enregistrer_reglement(c, {"tiers_id": e["tiers_id"], "date_reglement": "2026-10-10", "montant_cents": 100,
                                         "banque": "CIC", "affectations": [{"echeance_id": e["id"], "montant_cents": 100}]})
        l = [x for x in export_compta.ecritures(c, "2026-10-10", "2026-10-10") if x["JournalCode"] == "BQ1"]
        self.assertEqual({x["CompteNum"] for x in l}, {"512100", "411000"})

    def test_format_fec(self):
        l = export_compta.ecritures(self.c, "2000-01-01", "2999-12-31")
        txt = export_compta.fec(l).split("\r\n")
        self.assertEqual(txt[0].split("\t"), export_compta.COLONNES)
        champs = txt[1].split("\t")
        self.assertEqual(len(champs), 18)
        self.assertRegex(champs[3], r"^\d{8}$")
        self.assertRegex(champs[11], r"^\d+,\d{2}$")


if __name__ == "__main__":
    unittest.main()
