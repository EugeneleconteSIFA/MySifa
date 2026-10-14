"""
Nouvel ERP — allégation FSC (app/services/gc/fsc.py).

1. La matrice de l'affiche atelier, case par case.
2. Une bobine non FSC, ou du Controlled Wood → tout le dossier est non FSC.
3. Film, colle, encre ne comptent pas.
4. De la consommation de l'OF jusqu'au BL et à la facture : l'allégation suit
   la ligne, et un article vendu certifié FSC produit sans matière FSC lève
   une alerte.

Lancer : python3 tests/test_gc_fsc.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mysifa_gc_fsc_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database  # noqa: E402,F401 — le shim d'abord (CLAUDE.md)
from database import get_db  # noqa: E402
from app.services.gc import fsc, pieces  # noqa: E402

CR, NON, CW = ("fsc_mix_credit", None), ("non_fsc", None), ("controlled_wood", None)
M70, M50, REC85, REC80, F100 = ("fsc_mix", 70), ("fsc_mix", 50), ("fsc_recycled", 85), ("fsc_recycled", 80), ("fsc_100", None)
NOW = "2026-10-14T10:00:00"


class Matrice(unittest.TestCase):
    def test_affiche(self):
        c = fsc.combiner
        self.assertEqual(c([CR, CR]), CR)
        self.assertEqual(c([CR, M70]), M70)
        self.assertEqual(c([M70, CR]), M70)
        self.assertEqual(c([CR, REC85]), ("fsc_mix", None))
        self.assertEqual(c([M70, M50]), M50)                 # le X % le plus bas
        self.assertEqual(c([M70, REC85]), M70)               # Mix, le plus bas
        self.assertEqual(c([REC85, REC80]), REC80)           # Recycled, le plus bas
        for a in (CR, M70, REC85, F100):
            self.assertEqual(c([a, NON]), NON)               # 1. une bobine non FSC suffit
            self.assertEqual(c([a, CW]), NON)                # 2. Controlled Wood → non FSC
        self.assertEqual(c([F100, CR]), CR)
        self.assertEqual(c([F100, F100]), F100)
        self.assertIsNone(c([]))
        self.assertEqual(fsc.libelle(M70), "FSC Mix 70%")


class Chaine(unittest.TestCase):
    def test_of_bl_facture(self):
        with get_db() as conn:
            c = conn
            c.execute("""INSERT INTO gc_tiers (id, code, est_client, raison_sociale, cree_le, modifie_le)
                         VALUES (1, 'C1', 1, 'Client', ?, ?)""", (NOW, NOW))
            arts = [
                (1, "PF", "Étiquette certifiée", "pf", "ETQ", 1000, 1, "", None, 1),
                (2, "PAP", "Papier Mix Credit", "mp", "ML", 1, 0, "fsc_mix_credit", None, 1),
                (3, "FILM", "Film PP", "mp", "ML", 1, 0, "", None, 0),         # ne compte pas
                (4, "PAPN", "Papier non FSC", "mp", "ML", 1, 0, "non_fsc", None, 1),
            ]
            for i, code, lib, nat, un, base, req, alleg, pct, bois in arts:
                c.execute("""INSERT INTO gc_articles (id, code, libelle, nature, unite, base_prix, prix_vente_cents, tva_code,
                               gere_stock, fsc_requis, fsc_allegation, fsc_pct, fsc_bois, cree_le, modifie_le)
                             VALUES (?,?,?,?,?,?,1000,'N',1,?,?,?,?,?,?)""",
                          (i, code, lib, nat, un, base, req, alleg, pct, bois, NOW, NOW))
            co = pieces.creer(c, "commande", 1)
            pieces.enregistrer(c, co, None, [{"article_id": 1, "quantite_milli": 10_000_000, "prix_cents": 1000, "base_prix": 1000}])
            pieces.valider(c, co)
            of = pieces.transformer(c, [co], "of")
            pieces.valider(c, of)
            pieces.declarer_consommation(c, of, 2, 1_000_000)
            pieces.declarer_consommation(c, of, 3, 1_000_000)       # film : ignoré
            pieces.declarer_production(c, of, 10_000_000)
            self.assertEqual(fsc.allegation_of(c, of), CR)
            bl = pieces.transformer(c, [co], "bl")
            pieces.valider(c, bl)
            lbl = pieces.charger(c, bl)["lignes"][0]["id"]
            self.assertEqual(fsc.allegation_ligne(c, lbl), CR)
            self.assertEqual(fsc.alertes(c, bl), [])
            fa = pieces.transformer(c, [bl], "facture")
            pieces.valider(c, fa)
            self.assertEqual(fsc.allegation_ligne(c, pieces.charger(c, fa)["lignes"][0]["id"]), CR)
            # Une bobine non FSC sur le même OF : tout bascule, et l'alerte tombe
            pieces.declarer_consommation(c, of, 4, 500_000)
            self.assertEqual(fsc.allegation_of(c, of), NON)
            self.assertEqual(len(fsc.alertes(c, bl)), 1)
            c.rollback()


if __name__ == "__main__":
    unittest.main()
