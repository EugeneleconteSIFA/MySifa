"""
Nouvel ERP — valorisation du stock à une date (app/services/gc/valorisation.py).

1. Quantité à la date : les mouvements postérieurs ne comptent pas.
2. Prix à la date : le prix de stock de l'historique valable ce jour-là ; un
   changement de prix sur la fiche est daté.
3. Matière sans prix de stock : prix de la dernière réception jusqu'à la date.
4. Matière en laize suivie en ML avec un prix au m² : ML × laize × prix.
5. Paramètres de MyStock : charges de production sur les produits finis,
   frais de stockage sur le total.

Lancer : python3 tests/test_gc_valorisation.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mysifa_gc_valo_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database  # noqa: E402,F401 — le shim d'abord (CLAUDE.md)
from database import get_db  # noqa: E402
from app.services.gc import fichiers, valorisation  # noqa: E402

NOW = "2026-10-16T10:00:00"


def mvt(c, art, q, jour, typ="inventaire", laize=None, valeur=None):
    c.execute("""INSERT INTO gc_mouvements (date_mvt, article_id, depot, quantite_milli, type, laize_dmm, valeur_cents, cree_le)
                 VALUES (?,?, 'PRINC', ?, ?, ?, ?, ?)""", (jour, art, q, typ, laize, valeur, NOW))


class Valorisation(unittest.TestCase):
    def setUp(self):
        self._cm = get_db()
        self.c = c = self._cm.__enter__()
        for t in ("gc_prix_stock_historique", "gc_mouvements", "gc_articles", "gc_tiers"):
            c.execute(f"DELETE FROM {t}")
        c.execute("INSERT INTO gc_tiers (id, code, est_client, raison_sociale, cree_le, modifie_le) VALUES (1,'C1',1,'Client',?,?)", (NOW, NOW))
        for k, v in (("charge_production_pct", 20.0), ("storage_fees_pct", 2.0)):
            c.execute("INSERT OR REPLACE INTO mc_setting (key, value_decimal) VALUES (?,?)", (k, v))
        # Produit fini : 10 000 étiquettes, prix au mille
        self.pf = fichiers.enregistrer_article(c, None, {"libelle": "Étiquette", "nature": "pf", "unite": "ETQ", "client_id": 1,
                                                         "base_prix": 1000, "prix_vente_cents": 5000})
        mvt(c, self.pf, 10_000_000, "2026-09-01")
        mvt(c, self.pf, -4_000_000, "2026-10-10", "livraison")
        # Matière en ML, laize 330 mm, prix au m²
        self.mp = fichiers.enregistrer_article(c, None, {"libelle": "Vélin", "nature": "mp", "unite": "ML", "base_prix": 1})
        mvt(c, self.mp, 2_000_000, "2026-09-01", laize=3300)
        # Matière sans prix de stock, valorisée à la dernière réception
        self.mp2 = fichiers.enregistrer_article(c, None, {"libelle": "Encre", "nature": "mp", "unite": "KG", "base_prix": 1})
        mvt(c, self.mp2, 50_000, "2026-09-05", "reception", valeur=60_000)     # 50 kg pour 600 €

    def tearDown(self):
        self.c.rollback()
        self._cm.__exit__(None, None, None)

    def ligne(self, V, art):
        return [i for i in V["items"] if i["id"] == art][0]

    def test_quantite_et_prix_a_la_date(self):
        c = self.c
        fichiers.enregistrer_article(c, self.pf, {"prix_stock_cents": 3000})          # historisé aujourd'hui
        c.execute("UPDATE gc_prix_stock_historique SET depuis='2026-09-01' WHERE article_id=?", (self.pf,))
        valorisation.historiser(c, self.pf, {"prix_stock_cents": 3000}, {"prix_stock_cents": 3500}, jour="2026-10-05")
        sept = self.ligne(valorisation.valoriser(c, "2026-09-30"), self.pf)
        self.assertEqual((sept["quantite_milli"], sept["prix_cents"], sept["valeur_cents"]), (10_000_000, 3000, 30_000))
        oct_ = self.ligne(valorisation.valoriser(c, "2026-10-16"), self.pf)
        self.assertEqual((oct_["quantite_milli"], oct_["prix_cents"], oct_["valeur_cents"]), (6_000_000, 3500, 21_000))
        self.assertEqual(oct_["source_prix"], "historique")

    def test_sans_prix_de_stock(self):
        V = valorisation.valoriser(self.c, "2026-10-16")
        pf = self.ligne(V, self.pf)
        self.assertEqual((pf["source_prix"], pf["valeur_cents"]), ("fiche_vente", 30_000))     # 6 000 × 50 € / 1000
        enc = self.ligne(V, self.mp2)
        self.assertEqual((enc["source_prix"], enc["prix_cents"], enc["valeur_cents"]), ("reception", 1200, 60_000))
        self.assertEqual(self.ligne(V, self.mp)["source_prix"], "aucun")
        self.assertEqual(V["sans_prix"], 1)
        self.assertEqual(self.ligne(valorisation.valoriser(self.c, "2026-09-01"), self.mp2)["quantite_milli"] if any(
            i["id"] == self.mp2 for i in valorisation.valoriser(self.c, "2026-09-01")["items"]) else 0, 0)

    def test_prix_au_m2_et_parametres(self):
        c = self.c
        fichiers.enregistrer_article(c, self.mp, {"prix_stock_m2_cents": 50})      # 0,50 €/m²
        V = valorisation.valoriser(c, "2026-10-16")
        self.assertEqual(self.ligne(V, self.mp)["valeur_cents"], 33_000)           # 2 000 ML × 0,33 m × 0,50 €
        T = V["totaux"]
        self.assertEqual(T["pf_brut_cents"], 30_000)
        self.assertEqual(T["charge_production_cents"], 6_000)                     # 20 %
        self.assertEqual(T["mp_cents"], 33_000 + 60_000)
        sous = 93_000 + 24_000
        self.assertEqual(T["frais_stockage_cents"], round(sous * 0.02))
        self.assertEqual(T["total_cents"], sous + round(sous * 0.02))


if __name__ == "__main__":
    unittest.main()
