"""
Agent IA — actions du nouvel ERP (app/services/agent_actions_erp.py).

1. Les actions et lectures ERP sont dans le catalogue de l'agent, réservées
   aux rôles de l'ERP.
2. Une commande proposée en unités et en euros devient un corps en millièmes
   et en centimes ; la carte nomme le client et les articles.
3. Un identifiant inexistant est refusé avant d'atteindre l'utilisateur.
4. Un tiers proposé devient fiche + adresse + interlocuteur.

Lancer : python3 tests/test_agent_erp.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mysifa_agent_erp_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database  # noqa: E402,F401 — le shim d'abord (CLAUDE.md)
from database import get_db  # noqa: E402
from app.services import agent_actions as aa  # noqa: E402

SUPER = {"id": 0, "role": "superadmin", "email": "a@b.c"}
NOW = "2026-10-14T10:00:00"


class AgentErp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with get_db() as c:
            c.execute("INSERT INTO gc_tiers (id, code, est_client, raison_sociale, cree_le, modifie_le) VALUES (901,'C901',1,'Brasserie Test',?,?)", (NOW, NOW))
            c.execute("""INSERT INTO gc_articles (id, code, libelle, nature, unite, base_prix, tva_code, gere_stock, cree_le, modifie_le)
                         VALUES (901,'C901/0001','Étiquette bière','pf','ETQ',1000,'N',1,?,?)""", (NOW, NOW))
            c.commit()

    def test_catalogue(self):
        cles = {a["cle"] for a in aa.catalogue_pour(SUPER)}
        self.assertIn("erp_piece_creer", cles)
        self.assertNotIn("erp_piece_creer", {a["cle"] for a in aa.catalogue_pour({"id": 0, "role": "fabrication"})})
        self.assertIn("erp_carnet", {l["cle"] for l in aa.LECTURES})

    def test_commande(self):
        with get_db() as c:
            r = aa.preparer(SUPER, "erp_piece_creer", {
                "type": "commande", "tiers_id": 901, "ref_tiers": "BC-1",
                "lignes": [{"article_id": 901, "quantite": "20000", "prix": "36,5", "date_livraison": "2026-11-15"}]}, c)
        self.assertEqual(r["chemin"], "/api/erp2/pieces")
        self.assertEqual(r["corps"]["lignes"][0]["quantite_milli"], 20_000_000)
        self.assertEqual(r["corps"]["lignes"][0]["prix_cents"], 3650)
        self.assertEqual(r["corps"]["entete"], {"ref_tiers": "BC-1"})
        texte = " ".join(v for _, v in r["details"])
        self.assertIn("Brasserie Test", texte)
        self.assertIn("C901/0001", texte)

    def test_refus_id_inconnu(self):
        with get_db() as c:
            with self.assertRaises(aa.ActionInvalide):
                aa.preparer(SUPER, "erp_piece_creer", {"type": "commande", "tiers_id": 901,
                                                       "lignes": [{"article_id": 99999, "quantite": 1}]}, c)
            with self.assertRaises(aa.ActionInvalide):
                aa.preparer(SUPER, "erp_piece_valider", {"piece_id": 99999}, c)

    def test_tiers(self):
        with get_db() as c:
            r = aa.preparer(SUPER, "erp_tiers_creer", {"role": "fournisseur", "raison_sociale": "Papeterie X",
                                                       "ville": "Lille", "code_postal": "59000", "contact_nom": "M. Martin"}, c)
        self.assertEqual(r["corps"]["tiers"]["est_fournisseur"], 1)
        self.assertEqual(r["corps"]["adresses"][0]["ville"], "Lille")
        self.assertEqual(r["corps"]["contacts"][0]["nom"], "M. Martin")


if __name__ == "__main__":
    unittest.main()
