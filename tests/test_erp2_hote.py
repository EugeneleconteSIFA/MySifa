"""
Nouvel ERP : servi par son sous-domaine, et seulement par lui.

1. Sur un Host ERP, une page est servie sous ERP2_PREFIXE : sans session,
   c'est l'écran de connexion de l'ERP, pas celui de MySifa.
2. Le super administrateur reçoit la coque ; tout autre rôle est refusé.
3. Sur un Host ERP, l'API et les fichiers statiques restent ceux de MySifa.
4. Sur tout autre Host, ERP2_PREFIXE n'existe pas.
5. Aucun outil flottant de MySifa n'est injecté dans l'ERP.

Lancer : python3 tests/test_erp2_hote.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_tmp = tempfile.mkdtemp(prefix="mysifa_erp2_test_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database  # noqa: E402,F401 — le shim d'abord (CLAUDE.md)
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from config import ERP2_PREFIXE  # noqa: E402

ERP = {"host": "erp.localhost"}
WWW = {"host": "www.mysifa.com"}
SUPERADMIN = {"id": 1, "nom": "Admin", "email": "a@local", "role": "superadmin"}
DIRECTION = {"id": 2, "nom": "Dir", "email": "d@local", "role": "direction"}


class HoteErp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = TestClient(main.app)

    def test_connexion_sans_session(self):
        r = self.c.get("/", headers=ERP)
        self.assertEqual(r.status_code, 200)
        self.assertIn("erp-cx", r.text)
        self.assertIn("/api/auth/login", r.text)

    def test_coque_superadmin(self):
        with patch("app.web.erp2.page.get_current_user", return_value=SUPERADMIN):
            r = self.c.get("/ventes/commandes", headers=ERP)
        self.assertEqual(r.status_code, 200)
        self.assertIn('id="erp-app"', r.text)
        self.assertIn("/static/erp/erp.js", r.text)
        # Seul l'assistant IA est inclus (par la coque elle-même) : l'injection
        # des autres boutons flottants ne passe pas sur le sous-domaine.
        self.assertIn("mysifa_ai_chat.js", r.text)
        self.assertEqual(r.text.count("mysifa_boutons.js"), 1)
        self.assertNotIn("mysifa_postit.js", r.text)
        self.assertNotIn("chat_widget.js", r.text)
        self.assertNotIn("mysifa_blocs.js", r.text)

    def test_autre_role_refuse(self):
        with patch("app.web.erp2.page.get_current_user", return_value=DIRECTION):
            r = self.c.get("/", headers=ERP)
        self.assertEqual(r.status_code, 403)

    def test_api_et_statiques_communs(self):
        r = self.c.get("/api/auth/me", headers=ERP)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text.strip(), "null")
        r = self.c.get("/static/erp/erp.css", headers=ERP)
        self.assertEqual(r.status_code, 200)

    def test_prefixe_invisible_hors_erp(self):
        self.assertEqual(self.c.get(ERP2_PREFIXE, headers=WWW).status_code, 404)
        self.assertEqual(self.c.get(ERP2_PREFIXE + "/ventes", headers=WWW).status_code, 404)


if __name__ == "__main__":
    unittest.main()
