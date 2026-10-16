"""
Nouvel ERP — documents fournisseurs lus par l'IA (app/services/gc/documents.py).

Le modèle est remplacé par un lecteur factice : on teste ce que l'ERP fait de
la lecture, pas la lecture.

1. Dépôt : format refusé, fichier rangé sous les uploads.
2. Lecture : fournisseur reconnu (SIRET), commande retrouvée par son numéro,
   lignes appariées par la référence fournisseur du tarif.
3. Écarts : quantité au-delà du reste, prix différent, unité différente.
4. BL → réception en brouillon aux quantités du BL, n° du BL en référence.
5. Facture → facture fournisseur en brouillon au prix facturé ; le
   rapprochement relève l'écart de prix.

Lancer : python3 tests/test_gc_documents.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mysifa_gc_docs_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")
os.environ["UPLOADS_ROOT"] = os.path.join(_tmp, "uploads")
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database  # noqa: E402,F401 — le shim d'abord (CLAUDE.md)
from database import get_db  # noqa: E402
from app.services.gc import documents, pieces, rapprochement  # noqa: E402
from app.services.gc.pieces import ErreurPiece  # noqa: E402

NOW = "2026-10-16T10:00:00"


def lecteur(extraction):
    return lambda contenu, mime: (extraction, "factice")


class Documents(unittest.TestCase):
    def setUp(self):
        self._cm = get_db()
        self.c = self._cm.__enter__()
        c = self.c
        for t in ("gc_documents", "gc_mouvements", "gc_echeances", "gc_pieces_lignes", "gc_pieces", "gc_tarifs", "gc_articles", "gc_tiers"):
            c.execute(f"DELETE FROM {t}")
        c.execute("UPDATE gc_sequences SET prochain=1, annee=0, mois=0")
        c.execute("""INSERT INTO gc_tiers (id, code, est_fournisseur, raison_sociale, siret, cree_le, modifie_le)
                     VALUES (5,'F5',1,'Papeterie Adhésive SA','123 456 789 00012',?,?)""", (NOW, NOW))
        c.execute("""INSERT INTO gc_articles (id, code, libelle, nature, unite, base_prix, tva_code, gere_stock, actif, cree_le, modifie_le)
                     VALUES (50,'MP-VEL','Vélin adhésif permanent','mp','M2',1,'N',1,1,?,?)""", (NOW, NOW))
        c.execute("""INSERT INTO gc_articles (id, code, libelle, nature, unite, base_prix, tva_code, gere_stock, actif, cree_le, modifie_le)
                     VALUES (51,'MP-PP','Polypropylène blanc','mp','M2',1,'N',1,1,?,?)""", (NOW, NOW))
        c.execute("INSERT INTO gc_tarifs (article_id, tiers_id, sens, qte_min_milli, prix_cents, ref_fournisseur) VALUES (50,5,'achat',0,55,'VEL-80')")
        c.execute("INSERT INTO gc_tarifs (article_id, tiers_id, sens, qte_min_milli, prix_cents, ref_fournisseur) VALUES (51,5,'achat',0,90,'PP-60')")
        self.cde = pieces.creer(c, "cde_fournisseur", 5)
        pieces.enregistrer(c, self.cde, None, [{"article_id": 50, "quantite_milli": 10_000_000, "prix_cents": 55},
                                               {"article_id": 51, "quantite_milli": 4_000_000, "prix_cents": 90}])
        pieces.valider(c, self.cde)
        self.no_cde = pieces.charger(c, self.cde)["numero"]

    def tearDown(self):
        self.c.rollback()
        self._cm.__exit__(None, None, None)

    def test_depot_refus(self):
        with self.assertRaises(ErreurPiece):
            documents.deposer(self.c, b"x", "bl.exe")

    def test_bl_puis_facture(self):
        c = self.c
        did = documents.deposer(c, b"%PDF-1.4 faux", "BL-778.pdf")
        D = documents.analyser(c, did, lecteur({
            "nature": "bl", "numero": "BL-778", "date": "2026-10-15", "ref_commande": f"V/Cde {self.no_cde}",
            "fournisseur": {"nom": "PAPETERIE ADHESIVE", "siret": "12345678900012"},
            "lignes": [{"reference": "VEL-80", "designation": "Velin 80g", "quantite": 6000, "unite": "m²"},
                       {"reference": "PP-60", "designation": "PP blanc", "quantite": 5000, "unite": "ML"}]}))
        self.assertEqual(D["tiers_id"], 5)
        R = D["rapprochement"]
        self.assertEqual(R["commande"]["id"], self.cde)
        self.assertEqual([l["article_id"] for l in R["lignes"]], [50, 51])
        self.assertEqual(R["lignes"][0]["ecarts"], [])
        self.assertIn("quantité au-delà du reste à recevoir", R["lignes"][1]["ecarts"])
        self.assertTrue(any("unité" in e for e in R["lignes"][1]["ecarts"]))

        rec = documents.preparer(c, did, "reception")
        P = pieces.charger(c, rec)
        self.assertEqual((P["type"], P["statut"], P["ref_tiers"], P["date_piece"][:10]), ("reception", "brouillon", "BL-778", "2026-10-15"))
        self.assertEqual([l["quantite_milli"] for l in P["lignes"]], [6_000_000, 5_000_000])
        self.assertEqual(c.execute("SELECT statut, piece_id FROM gc_documents WHERE id=?", (did,)).fetchone()[:], ("traite", rec))
        pieces.enregistrer(c, rec, None, [P["lignes"][0]])      # seule la première ligne est reçue pour de bon
        pieces.valider(c, rec)

        fid = documents.deposer(c, b"%PDF-1.4 faux", "FA-55.pdf")
        documents.analyser(c, fid, lecteur({
            "nature": "facture", "numero": "FA-55", "date": "2026-10-16", "ref_commande": self.no_cde,
            "fournisseur": {"nom": "Papeterie Adhésive SA"},
            "lignes": [{"reference": "VEL-80", "designation": "Velin 80g", "quantite": 6000, "unite": "m2", "prix_unitaire": 0.58}]}))
        ff = documents.preparer(c, fid, "facture_fournisseur")
        F = pieces.charger(c, ff)
        self.assertEqual([(l["quantite_milli"], l["prix_cents"]) for l in F["lignes"]], [(6_000_000, 58)])
        r = rapprochement.rapprochement(c, ff)
        self.assertEqual((r["nb_ecarts"], r["lignes"][0]["ecart_prix_cents"]), (1, 3))

    def test_sans_commande(self):
        c = self.c
        did = documents.deposer(c, b"%PDF", "inconnu.pdf")
        D = documents.analyser(c, did, lecteur({"nature": "bl", "fournisseur": {"nom": "Inconnu SARL"},
                                                "lignes": [{"designation": "Carton", "quantite": 3}]}))
        self.assertIsNone(D["tiers_id"])
        self.assertIsNone(D["rapprochement"]["commande"])
        with self.assertRaises(ErreurPiece):
            documents.preparer(c, did, "reception")


if __name__ == "__main__":
    unittest.main()
