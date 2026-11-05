"""
Clôture d'inventaire — une purge de Z1 se propose au rattachement (cas réel
690/0034, clôture du 30/09/2026 : 4 050 000 étiquettes livrées fin juillet
dans RVGI, restées en Z1 dans MySifa jusqu'au 07/10).

1. Les sorties FIFO et les expéditions depuis Z1 saisies après la clôture sont
   proposées, marquées `purge_z1`, et jamais cochées d'office.
2. Un déplacement depuis Z1 (rangement) et une sortie FIFO d'un autre
   emplacement restent hors de la liste.
3. Rattachée, la purge retire le stock de la valorisation au soir de la
   clôture ; les autres emplacements ne bougent pas.

Lancer : python3 tests/test_valo_cloture_purge_z1.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mysifa_valo_z1_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database  # noqa: E402,F401 — le shim d'abord (CLAUDE.md)
from database import get_db  # noqa: E402
from app.routers import stock  # noqa: E402
from app.services import valo_cloture  # noqa: E402

REF = "TST/0034"
CLOTURE = "2026-09-30"


def mvt(c, pid, empl, typ, avant, apres, quand, note):
    cur = c.execute(
        """INSERT INTO mouvements_stock (produit_id, emplacement, type_mouvement, quantite,
               quantite_avant, quantite_apres, note, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (pid, empl, typ, abs(apres - avant), avant, apres, note, quand),
    )
    return cur.lastrowid


class PurgeZ1(unittest.TestCase):
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
            "VALUES (?, 'Test', 'étiquette', 'fabrique', '2026-07-01T00:00:00', '2026-07-01T00:00:00')",
            (REF,),
        )
        self.pid = pid = cur.lastrowid
        # Juillet : production déclarée en Z1, une palette rangée en D293.
        mvt(c, pid, "Z1", "entree", 0, 4_080_000, "2026-07-29T10:00:00", "Production dossier OF")
        mvt(c, pid, "Z1", "sortie", 4_080_000, 4_050_000, "2026-07-29T11:00:00", "Déplacement vers D293")
        mvt(c, pid, "D293", "entree", 0, 30_000, "2026-07-29T11:00:00", "Déplacement depuis Z1")
        # Octobre : purge de Z1 (FIFO + une expédition), un rangement, une
        # sortie FIFO hors Z1.
        self.fifo = mvt(c, pid, "Z1", "sortie", 4_050_000, 202_500, "2026-10-07T08:57:00", "Sortie lot FIFO")
        self.expe = mvt(c, pid, "Z1", "sortie", 202_500, 0, "2026-10-07T08:58:00",
                        "Expédition transporteur — 07/10/2026")
        mvt(c, pid, "Z1", "entree", 0, 10_000, "2026-10-08T08:00:00", "Production dossier OF2")
        self.depl = mvt(c, pid, "Z1", "sortie", 10_000, 0, "2026-10-08T09:00:00", "Déplacement vers C141")
        mvt(c, pid, "C141", "entree", 0, 10_000, "2026-10-08T09:00:00", "Déplacement depuis Z1")
        self.hors_z1 = mvt(c, pid, "D293", "sortie", 30_000, 0, "2026-10-26T07:39:00", "Sortie lot FIFO")
        for empl, q in (("Z1", 0), ("D293", 0), ("C141", 10_000)):
            c.execute(
                "INSERT INTO stock_emplacements (produit_id, emplacement, quantite, updated_at) "
                "VALUES (?, ?, ?, '2026-10-26T07:39:00')",
                (pid, empl, q),
            )
        c.commit()
        stock._PF_STOCK_SNAPSHOT_CACHE.clear()

    def tearDown(self):
        self._cm.__exit__(None, None, None)

    def _candidats_pf(self):
        return {m["id"]: m for m in valo_cloture.candidats(self.c, CLOTURE) if m["source"] == "pf"}

    def test_purge_proposee_et_marquee(self):
        lignes = self._candidats_pf()
        for mid in (self.fifo, self.expe):
            self.assertIn(mid, lignes)
            self.assertTrue(lignes[mid]["purge_z1"])
            self.assertFalse(lignes[mid]["rattache"])

    def test_rangement_et_fifo_hors_z1_exclus(self):
        lignes = self._candidats_pf()
        self.assertNotIn(self.depl, lignes)
        self.assertNotIn(self.hors_z1, lignes)

    def test_purge_rattachee_solde_le_stock_du_soir(self):
        self.assertEqual(stock._pf_stock_snapshot_at_date(self.c, CLOTURE).get(self.pid), 4_080_000)
        valo_cloture.enregistrer(self.c, CLOTURE, None, [], [self.fifo, self.expe],
                                 now="2026-11-05T10:00:00", par="test")
        self.assertEqual(valo_cloture.ecarts_pf(self.c, CLOTURE), {self.pid: -4_050_000.0})
        items = stock._pf_valo_query_at_date(self.c, CLOTURE)
        it = next(i for i in items if int(i["id"]) == self.pid)
        self.assertEqual(it["quantite"], 30_000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
