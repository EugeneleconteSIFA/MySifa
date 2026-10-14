"""
Nouvel ERP — PDF et envoi des pièces par e-mail (app/services/gc/pdf.py, envoi.py).

1. Chaque pièce de la démonstration produit un PDF (aperçu et pièce jointe
   lisent les mêmes données).
2. Destinataires proposés : les interlocuteurs cochés pour ce document, à
   défaut l'e-mail de facturation ou du tiers.
3. Envoi : PDF joint, envoi tracé, pièce marquée envoyée ; un échec est tracé
   et ne marque rien ; un brouillon ou une adresse invalide sont refusés.

Lancer : python3 tests/test_gc_envoi.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mysifa_gc_envoi_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database  # noqa: E402,F401 — le shim d'abord (CLAUDE.md)
from database import get_db  # noqa: E402
from app.services.gc import demo, envoi, pdf, pieces  # noqa: E402
from app.services.gc.pieces import ErreurPiece  # noqa: E402
from app.web.erp2.impression import donnees  # noqa: E402


class Envoi(unittest.TestCase):
    def setUp(self):
        self.ctx = get_db()
        self.c = self.ctx.__enter__()
        demo.reinitialiser(self.c)
        self.fa = self.c.execute("SELECT id, tiers_id FROM gc_pieces WHERE type='facture'").fetchone()

    def tearDown(self):
        self.c.rollback()
        self.ctx.__exit__(None, None, None)

    def test_pdf_toutes_pieces(self):
        for p in self.c.execute("SELECT id FROM gc_pieces").fetchall():
            self.assertEqual(pdf.generer(donnees(self.c, p["id"]))[:4], b"%PDF")

    def test_destinataires_proposes(self):
        c = self.c
        prep = envoi.preparation(c, self.fa["id"])
        self.assertTrue(prep["destinataires"])                      # repli : e-mail du tiers
        c.execute("UPDATE gc_tiers_contacts SET email='compta@client.example', envoi_facture=1 WHERE tiers_id=?",
                  (self.fa["tiers_id"],))
        self.assertEqual(envoi.preparation(c, self.fa["id"])["destinataires"], ["compta@client.example"])
        self.assertTrue(prep["fichier"].endswith(".pdf"))

    def test_envoi(self):
        c = self.c
        recu = {}

        def faux(to, subject, html_body, cc=None, attachments=None):
            recu.update(to=to, subject=subject, att=attachments)
            return True
        ok = envoi.envoyer(c, self.fa["id"], ["a@b.example"], [], "Objet", "Bonjour", envoyeur=faux)
        self.assertTrue(ok)
        self.assertEqual(recu["to"], ["a@b.example"])
        self.assertEqual(recu["att"][0]["content"][:4], b"%PDF")
        p = c.execute("SELECT envoye_le FROM gc_pieces WHERE id=?", (self.fa["id"],)).fetchone()
        self.assertIsNotNone(p["envoye_le"])
        # Échec : tracé, sans marquer la pièce
        bl = c.execute("SELECT id FROM gc_pieces WHERE type='bl' AND numero IS NOT NULL").fetchone()["id"]
        self.assertFalse(envoi.envoyer(c, bl, ["a@b.example"], [], "", "", envoyeur=lambda *a, **k: False))
        self.assertIsNone(c.execute("SELECT envoye_le FROM gc_pieces WHERE id=?", (bl,)).fetchone()["envoye_le"])
        self.assertEqual(c.execute("SELECT reussi FROM gc_envois WHERE piece_id=?", (bl,)).fetchone()["reussi"], 0)
        with self.assertRaises(ErreurPiece):
            envoi.envoyer(c, self.fa["id"], ["pas-une-adresse"], [], "", "", envoyeur=faux)
        brouillon = c.execute("SELECT id FROM gc_pieces WHERE numero IS NULL").fetchone()["id"]
        with self.assertRaises(ErreurPiece):
            envoi.envoyer(c, brouillon, ["a@b.example"], [], "", "", envoyeur=faux)


if __name__ == "__main__":
    unittest.main()
