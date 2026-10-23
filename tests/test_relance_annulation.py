"""
Relance d'un dossier au planning après une annulation.

Ce que le test protège, posé le 23/10/2026 :

1. Le second créneau créé par la conversion d'une fin de production en
   annulation pointe le passage annulé (`annulation_source_id`, d'où sa
   couleur), revient « à placer » et porte le signal `annulation_a_revoir`.
2. Décocher « À placer au planning » éteint le signal, quel que soit le
   chemin d'écriture (déclencheur `trg_pe_annulation_revue`).
3. Recocher « À placer » ne rallume pas le signal.

Lancer : python3 tests/test_relance_annulation.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mysifa_relance_test_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database  # noqa: E402,F401  — toujours avant app.*

MACHINE_ID = 90301


class TestRelanceAnnulation(unittest.TestCase):
    def setUp(self):
        from database import get_db

        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO machines (id, nom, code, actif) VALUES (?,?,?,1)",
                (MACHINE_ID, "Test Relance", "TR1"),
            )
            conn.execute("DELETE FROM planning_entries WHERE machine_id=?", (MACHINE_ID,))
            self.source = conn.execute(
                """INSERT INTO planning_entries
                   (machine_id, position, reference, client, duree_heures, statut,
                    created_at, updated_at, a_placer)
                   VALUES (?, 1, 'REL-001', 'Client', 2.5, 'termine', '2026-10-21T08:00:00',
                           '2026-10-21T08:00:00', 0)""",
                (MACHINE_ID,),
            ).lastrowid
            conn.commit()

    @staticmethod
    def _ligne(entry_id):
        from database import get_db

        with get_db() as conn:
            return dict(conn.execute("SELECT * FROM planning_entries WHERE id=?", (entry_id,)).fetchone())

    def test_relance_puis_placement(self):
        from database import get_db
        from app.services.annulation_fin_production import _creer_second_creneau

        with get_db() as conn:
            rid = _creer_second_creneau(conn, self.source, "Testeur", "2026-10-21T15:00:00")
            conn.commit()
        r = self._ligne(rid)
        self.assertEqual(r["annulation_source_id"], self.source)
        self.assertEqual(r["annulation_a_revoir"], 1)
        self.assertEqual(r["a_placer"], 1)
        self.assertEqual(r["statut"], "attente")

        with get_db() as conn:
            conn.execute("UPDATE planning_entries SET a_placer=0 WHERE id=?", (rid,))
            conn.commit()
        r = self._ligne(rid)
        self.assertEqual(r["annulation_a_revoir"], 0)
        # La couleur reste celle du passage annulé.
        self.assertEqual(r["annulation_source_id"], self.source)

        with get_db() as conn:
            conn.execute("UPDATE planning_entries SET a_placer=1 WHERE id=?", (rid,))
            conn.commit()
        self.assertEqual(self._ligne(rid)["annulation_a_revoir"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
