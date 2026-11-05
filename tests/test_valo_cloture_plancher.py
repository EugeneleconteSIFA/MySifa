"""
Clôture d'inventaire — une correction rattachée ne fait pas passer un produit
fini sous zéro (cas réel 890/0017, clôture du 30/09/2026).

1. Valorisation au 30/09 : stock du soir 6 000 000, correction rattachée de
   -11 640 000 (inventaire du 14/10 qui solde aussi la production d'octobre)
   -> quantité 0, valorisation 0, jamais négative.
2. L'écran de clôture reçoit la clé de stock et le stock du soir de chaque
   correction, pour signaler celles qui le dépassent.

Lancer : python3 tests/test_valo_cloture_plancher.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mysifa_valo_clo_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database  # noqa: E402,F401 — le shim d'abord (CLAUDE.md)
from database import get_db  # noqa: E402
from app.routers import stock  # noqa: E402
from app.services import valo_cloture  # noqa: E402

REF = "TST/0017"
CLOTURE = "2026-09-30"


def mvt(c, pid, typ, avant, apres, quand, note):
    cur = c.execute(
        """INSERT INTO mouvements_stock (produit_id, emplacement, type_mouvement, quantite,
               quantite_avant, quantite_apres, note, created_at)
           VALUES (?, 'Z1', ?, ?, ?, ?, ?, ?)""",
        (pid, typ, abs(apres - avant), avant, apres, note, quand),
    )
    return cur.lastrowid


class Plancher(unittest.TestCase):
    def setUp(self):
        self._cm = get_db()
        self.c = c = self._cm.__enter__()
        c.execute("DELETE FROM valo_cloture_mouvements")
        c.execute("DELETE FROM valo_clotures")
        c.execute("DELETE FROM mouvements_stock")
        c.execute("DELETE FROM stock_emplacements")
        c.execute("DELETE FROM produits WHERE reference=?", (REF,))
        cur = c.execute(
            "INSERT INTO produits (reference, designation, unite, type, created_at, updated_at) "
            "VALUES (?, 'Test', 'étiquette', 'fabrique', '2026-09-01T00:00:00', '2026-09-01T00:00:00')",
            (REF,),
        )
        self.pid = pid = cur.lastrowid
        mvt(c, pid, "entree", 0, 6_000_000, "2026-09-29T10:00:00", "Production")
        # Production d'octobre, puis inventaire du 14/10 qui solde tout.
        mvt(c, pid, "entree", 6_000_000, 11_640_000, "2026-10-02T10:00:00", "Production")
        self.inv = mvt(c, pid, "inventaire", 11_640_000, 0, "2026-10-14T16:44:48", "Inventaire emplacement")
        c.execute(
            "INSERT INTO stock_emplacements (produit_id, emplacement, quantite, updated_at) "
            "VALUES (?, 'Z1', 0, '2026-10-14T16:44:48')",
            (pid,),
        )
        c.commit()
        valo_cloture.enregistrer(c, CLOTURE, None, [], [self.inv], now="2026-10-16T10:00:00", par="test")
        stock._PF_STOCK_SNAPSHOT_CACHE.clear()

    def tearDown(self):
        self._cm.__exit__(None, None, None)

    def test_valorisation_jamais_negative(self):
        # Sans plancher : 6 000 000 - 11 640 000 = -5 640 000.
        self.assertEqual(valo_cloture.ecarts_pf(self.c, CLOTURE), {self.pid: -11_640_000.0})
        items = stock._pf_valo_query_at_date(self.c, CLOTURE)
        it = next(i for i in items if int(i["id"]) == self.pid)
        self.assertEqual(it["quantite"], 0)
        self.assertEqual(it["valorisation"], 0)

    def test_candidat_porte_sa_cle_de_stock(self):
        lignes = valo_cloture.candidats(self.c, CLOTURE)
        inv = next(m for m in lignes if m["source"] == "pf" and m["id"] == self.inv)
        self.assertEqual(inv["cle_stock"], f"pf:{self.pid}")
        self.assertTrue(inv["rattache"])
        self.assertEqual(stock._pf_stock_snapshot_at_date(self.c, CLOTURE).get(self.pid), 6_000_000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
