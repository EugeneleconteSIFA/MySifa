"""
Valorisation PF — un prix posé avant une conversion d'unité n'est plus appliqué
tel quel (cas réel 938/0038, bobine → carton ×1/12 le 20/10/2026).

Le prix importé (1,33 €/bobine) restait en place après la conversion et
s'appliquait à des cartons que RVGI facture 15,36 € : la ligne valait douze
fois moins. Le prix RVGI, exprimé dans la nouvelle unité, le remplace :

1. dans la valorisation courante ;
2. dans la valorisation à une date antérieure à la conversion, où la quantité
   reconstituée est déjà ramenée à la nouvelle unité ;
3. un prix saisi APRÈS la conversion reste celui qui compte.

Lancer : python3 tests/test_pf_conversion_prix.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mysifa_pf_conv_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database  # noqa: E402,F401 — le shim d'abord (CLAUDE.md)
from database import get_db  # noqa: E402
from app.routers import stock  # noqa: E402

REF = "TST/0038"
NOTE = stock._NOTE_CONVERSION_UNITE + " : bobine → cartons (facteur ×0.0833333)"


def _faux_rvgi(reference, par_mille, taux, unite, stock_qte):
    if reference != REF:
        return None
    return {"prix": 15.36, "source": "Commande RVGI n°1 · 06/08/2026", "origine": "commande_rvgi",
            "fournisseur": None, "detail": None}


class PrixApresConversion(unittest.TestCase):
    def setUp(self):
        self._orig = stock._pf_prix_achat.prix_rvgi
        stock._pf_prix_achat.prix_rvgi = _faux_rvgi
        self._cm = get_db()
        self.c = c = self._cm.__enter__()
        for t in ("valo_cloture_mouvements", "valo_clotures", "mouvements_stock", "stock_emplacements",
                  "pf_valorisation", "pf_valorisation_historique"):
            c.execute(f"DELETE FROM {t}")
        c.execute("DELETE FROM produits WHERE reference=?", (REF,))
        self.pid = pid = c.execute(
            "INSERT INTO produits (reference, designation, unite, type, created_at, updated_at) "
            "VALUES (?, 'Test', 'carton', 'fabrique', '2026-06-01T00:00:00', '2026-10-20T10:30:09')",
            (REF,),
        ).lastrowid
        c.execute(
            "INSERT INTO pf_valorisation (produit_id, prix_unitaire_ht, source_prix, updated_at) "
            "VALUES (?, 1.33, 'ERP (2024+)', '2026-06-19T10:08:38')",
            (pid,),
        )
        c.execute(
            "INSERT INTO pf_valorisation_historique (produit_id, prix_avant, prix_apres, source, created_at) "
            "VALUES (?, NULL, 1.33, 'import', '2026-06-19T10:08:38')",
            (pid,),
        )
        mv = """INSERT INTO mouvements_stock (produit_id, emplacement, type_mouvement, quantite,
                    quantite_avant, quantite_apres, note, created_at) VALUES (?, 'Z1', ?, ?, ?, ?, ?, ?)"""
        c.execute(mv, (pid, "entree", 1200, 0, 1200, "", "2026-09-10T10:00:00"))
        c.execute(mv, (pid, "inventaire", -1100, 1200, 100, NOTE, "2026-10-20T10:30:09"))
        c.execute(
            "INSERT INTO stock_emplacements (produit_id, emplacement, quantite, updated_at) "
            "VALUES (?, 'Z1', 100, '2026-10-20T10:30:09')",
            (pid,),
        )
        c.commit()
        stock._PF_STOCK_SNAPSHOT_CACHE.clear()
        stock._PF_PRICE_SNAPSHOT_CACHE.clear()

    def tearDown(self):
        stock._pf_prix_achat.prix_rvgi = self._orig
        self._cm.__exit__(None, None, None)

    def _ligne(self, date=None):
        items = stock._pf_valo_query_at_date(self.c, date)
        return next(i for i in items if int(i["id"]) == self.pid)

    def test_valorisation_courante(self):
        it = self._ligne()
        self.assertEqual(it["prix_unitaire_ht"], 15.36)
        self.assertEqual(it["valorisation"], 1536.0)
        self.assertEqual(it["prix_origine"], "commande_rvgi")

    def test_valorisation_a_date_avant_conversion(self):
        it = self._ligne("2026-09-30")
        self.assertEqual(it["quantite"], 100)  # 1 200 bobines ramenées en cartons
        self.assertEqual(it["prix_unitaire_ht"], 15.36)
        self.assertEqual(it["valorisation"], 1536.0)

    def test_prix_saisi_apres_conversion(self):
        self.c.execute(
            "UPDATE pf_valorisation SET prix_unitaire_ht=16, source_prix='Saisi à la main', "
            "updated_at='2026-11-05T09:00:00' WHERE produit_id=?",
            (self.pid,),
        )
        self.c.execute(
            "INSERT INTO pf_valorisation_historique (produit_id, prix_avant, prix_apres, source, created_at) "
            "VALUES (?, 1.33, 16, 'manuel', '2026-11-05T09:00:00')",
            (self.pid,),
        )
        self.c.commit()
        stock._PF_PRICE_SNAPSHOT_CACHE.clear()
        self.assertEqual(self._ligne()["prix_unitaire_ht"], 16)
        self.assertEqual(self._ligne("2026-09-30")["valorisation"], 1600.0)

    def test_sans_conversion_rien_ne_change(self):
        self.c.execute("DELETE FROM mouvements_stock WHERE note LIKE ?", (stock._NOTE_CONVERSION_UNITE + "%",))
        self.c.commit()
        stock._PF_STOCK_SNAPSHOT_CACHE.clear()
        self.assertEqual(self._ligne()["prix_unitaire_ht"], 1.33)


if __name__ == "__main__":
    unittest.main(verbosity=2)
