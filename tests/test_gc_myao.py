"""
Nouvel ERP — demande de prix MyAO → commande fournisseur (app/services/gc/myao.py).

1. Une demande clôturée propose le fournisseur ERP (par nom) et les prix du
   fournisseur retenu : au mille en euros tel quel, en USD converti au taux,
   à la bobine laissé à saisir.
2. La commande créée est un brouillon de commande fournisseur, quantités et
   prix repris, référence de la demande gardée ; une seconde transformation est
   refusée.
3. Les correspondances sont retenues : article de la ligne, fournisseur MyAO.
4. Une demande non clôturée ne se transforme pas.

Lancer : python3 tests/test_gc_myao.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mysifa_gc_myao_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database  # noqa: E402,F401 — le shim d'abord (CLAUDE.md)
from database import get_db  # noqa: E402
from app.services.gc import myao, pieces  # noqa: E402
from app.services.gc.pieces import ErreurPiece  # noqa: E402

NOW = "2026-10-16T10:00:00"


class MyAO(unittest.TestCase):
    def setUp(self):
        self._cm = get_db()
        self.c = self._cm.__enter__()
        c = self.c
        for t in ("ao_reponses", "ao_fournisseurs", "ao_lignes", "ao_demandes", "gc_correspondances_myao",
                  "gc_pieces_lignes", "gc_pieces", "gc_articles", "gc_tiers"):
            c.execute(f"DELETE FROM {t}")
        c.execute("INSERT INTO gc_tiers (id, code, est_fournisseur, raison_sociale, cree_le, modifie_le) VALUES (7,'F7',1,'QRT Graphique',?,?)", (NOW, NOW))
        c.execute("""INSERT INTO gc_articles (id, code, libelle, nature, unite, base_prix, tva_code, gere_stock, actif, cree_le, modifie_le)
                     VALUES (70,'ETQ-NEGOCE','Étiquette achetée','mp','ETQ',1000,'N',1,1,?,?)""", (NOW, NOW))
        c.execute("""INSERT INTO ao_demandes (id, reference, titre, date_creation, statut, fournisseur_retenu_id)
                     VALUES (1,'AO-2026-001','Étiquettes négoce',?, 'cloturee', 11)""", (NOW,))
        c.execute("INSERT INTO ao_fournisseurs (id, ao_id, nom_fournisseur, email_contact, token, statut) VALUES (11,1,'QRT Graphique','a@b.c','t1','repondu')")
        c.execute("INSERT INTO ao_lignes (id, ao_id, ref_produit, designation, quantite, unite, position) VALUES (101,1,'ETQ-NEGOCE','Etiquette 50x50',20000,'etiquettes',1)")
        c.execute("INSERT INTO ao_lignes (id, ao_id, ref_produit, designation, quantite, unite, position) VALUES (102,1,'REF-USD','Etiquette USD',10000,'etiquettes',2)")
        c.execute("INSERT INTO ao_lignes (id, ao_id, ref_produit, designation, quantite, unite, position) VALUES (103,1,'REF-BOB','Etiquette bobine',5000,'etiquettes',3)")
        c.execute("INSERT INTO ao_reponses (ao_fournisseur_id, ligne_id, quotation, devise, unite_quotation) VALUES (11,101,36.5,'EUR','mille')")
        c.execute("INSERT INTO ao_reponses (ao_fournisseur_id, ligne_id, quotation, devise, unite_quotation) VALUES (11,102,11.0,'USD','mille')")
        c.execute("INSERT INTO ao_reponses (ao_fournisseur_id, ligne_id, quotation, devise, unite_quotation) VALUES (11,103,4.0,'EUR','bobine')")
        c.commit()

    def tearDown(self):
        self.c.rollback()
        self._cm.__exit__(None, None, None)

    def test_detail(self):
        D = myao.detail(self.c, 1)
        self.assertEqual(D["tiers_id"], 7)
        L = {l["ligne_id"]: l for l in D["lignes"]}
        self.assertEqual(L[101]["article_id"], 70)
        self.assertEqual((L[101]["options"][0]["prix_cents"], L[101]["options"][0]["quantite_milli"]), (3650, 20_000_000))
        usd = L[102]["options"][0]
        self.assertEqual(usd["prix_cents"], round(11.0 / D["taux_usd"] * 100))
        self.assertIn("USD", usd["note"])
        self.assertTrue(L[103]["options"][0]["a_saisir"])

    def test_vers_commande(self):
        c = self.c
        with self.assertRaises(ErreurPiece):     # prix à la bobine non saisi
            myao.vers_commande(c, 1, {"lignes": [{"ligne_id": 103, "article_id": 70}]})
        pid = myao.vers_commande(c, 1, {"lignes": [{"ligne_id": 101, "article_id": 70},
                                                   {"ligne_id": 102}, {"ligne_id": 103}]})
        p = pieces.charger(c, pid)
        self.assertEqual((p["type"], p["statut"], p["tiers_id"], p["origine_ref"]), ("cde_fournisseur", "brouillon", 7, "AO-2026-001"))
        self.assertEqual([(l["quantite_milli"], l["prix_cents"], l["base_prix"]) for l in p["lignes"]], [(20_000_000, 3650, 1000)])
        self.assertEqual(c.execute("SELECT article_id FROM gc_correspondances_myao WHERE cle='produit:None'").fetchone(), None)
        self.assertEqual(c.execute("SELECT article_id FROM gc_correspondances_myao WHERE cle='ref:ETQ-NEGOCE'").fetchone()[0], 70)
        self.assertEqual(myao.demandes(c)[0]["commande_id"], pid)
        with self.assertRaises(ErreurPiece):
            myao.vers_commande(c, 1, {"lignes": [{"ligne_id": 101, "article_id": 70}]})

    def test_non_cloturee(self):
        self.c.execute("UPDATE ao_demandes SET statut='envoyee' WHERE id=1")
        with self.assertRaises(ErreurPiece):
            myao.vers_commande(self.c, 1, {"tiers_id": 7, "lignes": [{"ligne_id": 101, "article_id": 70}]})


if __name__ == "__main__":
    unittest.main()
