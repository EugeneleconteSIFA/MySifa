"""
Référencement : seule la page d'accueil de la prod, sur son domaine public, est indexable.

1. Prod sur le domaine public : « / » est indexable, avec titre long, canonical, Open
   Graph et sitemap ; robots.txt n'ouvre que « / » et /static/.
2. Le même code appelé par un autre Host (v1, ERP, domaine nu, IP) : X-Robots-Tag
   « noindex », robots.txt « Disallow: / », pas de sitemap.
3. Toute autre page (modules, API, portail Espace) répond « noindex », même en prod.
4. Un utilisateur connecté garde le titre court et ne reçoit pas les balises.
5. ENV_NAME=v1 : SEO_INDEXABLE est faux, « noindex » partout.
6. Le middleware laisse passer intacts une réponse en streaming et un téléchargement.

Lancer : python3 tests/test_seo_accueil.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from html import escape
from pathlib import Path
from unittest.mock import patch

_tmp = tempfile.mkdtemp(prefix="mysifa_seo_test_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")
# Instance de prod, quel que soit le .env du poste.
os.environ["ENV_NAME"] = "v2"
os.environ["PUBLIC_BASE_URL"] = "https://www.mysifa.com"
os.environ.pop("SEO_INDEXABLE", None)

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database  # noqa: E402,F401 — le shim d'abord (CLAUDE.md)
from fastapi.responses import FileResponse, StreamingResponse  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from app.web.html import render_frontend_html  # noqa: E402
from config import APP_NAME, APP_PAGE_TITLE, COOKIE_NAME  # noqa: E402

NOINDEX = "noindex, nofollow"
AUTRES_HOTES = ["v1.mysifa.com", "erp.mysifa.com", "mysifa.com", "127.0.0.1", "127.0.0.1:8000"]


def _ajouter_routes_de_test():
    """Une réponse en streaming et un téléchargement, pour vérifier que le middleware les laisse passer."""
    fichier = Path(_tmp) / "export.csv"
    fichier.write_bytes(b"a;b\n1;2\n")

    @main.app.get("/api/_test_seo/flux")
    def flux():
        return StreamingResponse((f"morceau {i}\n" for i in range(3)), media_type="text/plain")

    @main.app.get("/api/_test_seo/fichier")
    def telechargement():
        return FileResponse(str(fichier), filename="export.csv")


_ajouter_routes_de_test()


class _Cas(unittest.TestCase):
    def assertIn(self, morceau, texte, msg=None):  # noqa: N802 — sans recopier 500 Ko de HTML en cas d'échec
        if morceau not in texte:
            self.fail(msg or f"absent de la réponse : {morceau!r}")

    def assertNotIn(self, morceau, texte, msg=None):  # noqa: N802
        if morceau in texte:
            self.fail(msg or f"présent dans la réponse : {morceau!r}")


class ProdDomainePublic(_Cas):
    @classmethod
    def setUpClass(cls):
        cls.c = TestClient(main.app, base_url="https://www.mysifa.com")

    def test_accueil_indexable(self):
        r = self.c.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("X-Robots-Tag", r.headers)
        self.assertNotIn('name="robots"', r.text)
        self.assertIn(f"{escape(APP_PAGE_TITLE, quote=False)}</title>", r.text)
        self.assertIn('<link rel="canonical" href="https://www.mysifa.com/">', r.text)
        self.assertIn('property="og:image" content="https://www.mysifa.com/static/og-mysifa.png"', r.text)
        self.assertIn('"@type": "WebApplication"', r.text)

    def test_robots_ouvre_l_accueil_seul(self):
        r = self.c.get("/robots.txt")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Allow: /$", r.text)
        self.assertIn("Disallow: /\n", r.text)
        self.assertIn("Sitemap: https://www.mysifa.com/sitemap.xml", r.text)

    def test_sitemap(self):
        r = self.c.get("/sitemap.xml")
        self.assertEqual(r.status_code, 200)
        self.assertIn("application/xml", r.headers["content-type"])
        self.assertIn("<loc>https://www.mysifa.com/</loc>", r.text)

    def test_image_de_partage_servie(self):
        r = self.c.get("/static/og-mysifa.png")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["content-type"], "image/png")
        self.assertNotIn("X-Robots-Tag", r.headers)

    def test_autres_pages_noindex(self):
        for chemin in ["/prod", "/stock", "/planning", "/expe", "/settings", "/api/health",
                       "/manifest.webmanifest", "/service-worker.js", "/espace/inconnu"]:
            with self.subTest(chemin=chemin):
                r = self.c.get(chemin, follow_redirects=False)
                self.assertEqual(r.headers.get("X-Robots-Tag"), NOINDEX)

    def test_pages_de_modules_portent_la_meta_noindex(self):
        for app in ["prod", "expe", "compta", "myrh"]:
            with self.subTest(app=app):
                html = render_frontend_html(app)
                self.assertIn('<meta name="robots" content="noindex, nofollow">', html)
                self.assertNotIn('rel="canonical"', html)

    def test_utilisateur_connecte_garde_le_titre_court(self):
        c = TestClient(main.app, base_url="https://www.mysifa.com", cookies={COOKIE_NAME: "session-quelconque"})
        r = c.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(f"<title>{APP_NAME}</title>", r.text)
        self.assertNotIn('rel="canonical"', r.text)

    def test_connexion_remet_le_titre_court(self):
        r = self.c.get("/")
        self.assertIn(f'<title data-titre-connecte="{APP_NAME}">', r.text)
        self.assertIn("document.title=tc.dataset.titreConnecte", r.text)

    def test_streaming_et_telechargement_intacts(self):
        r = self.c.get("/api/_test_seo/flux")
        self.assertEqual(r.text, "morceau 0\nmorceau 1\nmorceau 2\n")
        self.assertEqual(r.headers.get("X-Robots-Tag"), NOINDEX)
        r = self.c.get("/api/_test_seo/fichier")
        self.assertEqual(r.content, b"a;b\n1;2\n")
        self.assertIn('filename="export.csv"', r.headers["content-disposition"])
        self.assertEqual(r.headers.get("X-Robots-Tag"), NOINDEX)


class AutresHotes(_Cas):
    @classmethod
    def setUpClass(cls):
        cls.c = TestClient(main.app)

    def test_noindex_et_disallow(self):
        for hote in AUTRES_HOTES:
            with self.subTest(hote=hote):
                h = {"host": hote}
                r = self.c.get("/", headers=h)
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.headers.get("X-Robots-Tag"), NOINDEX)
                r = self.c.get("/robots.txt", headers=h)
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.text, "User-agent: *\nDisallow: /\n")
                self.assertEqual(r.headers.get("X-Robots-Tag"), NOINDEX)
                self.assertEqual(self.c.get("/sitemap.xml", headers=h).status_code, 404)


class InstanceV1(_Cas):
    def test_env_v1_ferme_l_indexation(self):
        code = "import config; print(config.SEO_INDEXABLE, config.IS_STAGING)"
        env = {**os.environ, "ENV_NAME": "v1"}
        env.pop("SEO_INDEXABLE", None)
        out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env,
                             capture_output=True, text=True, check=True).stdout.split()
        self.assertEqual(out, ["False", "True"])

    def test_v1_noindex_partout(self):
        c = TestClient(main.app, base_url="https://www.mysifa.com")
        with patch("app.core.noindex.SEO_INDEXABLE", False), \
                patch("app.web.components.seo_accueil.SEO_INDEXABLE", False):
            render_frontend_html.cache_clear()
            try:
                r = c.get("/")
                self.assertEqual(r.headers.get("X-Robots-Tag"), NOINDEX)
                self.assertIn('<meta name="robots" content="noindex, nofollow">', r.text)
                self.assertNotIn('rel="canonical"', r.text)
                self.assertEqual(c.get("/robots.txt").text, "User-agent: *\nDisallow: /\n")
                self.assertEqual(c.get("/sitemap.xml").status_code, 404)
            finally:
                render_frontend_html.cache_clear()


class Parite(_Cas):
    """Le middleware n'ajoute qu'un en-tête : même statut, même corps, mêmes autres en-têtes."""

    REQUETES = [
        ("GET", "/"), ("GET", "/prod"), ("GET", "/manifest.webmanifest"), ("GET", "/service-worker.js"),
        ("GET", "/api/auth/me"), ("GET", "/portail/jeton-inconnu"),
        ("GET", "/mcp"), ("POST", "/mcp"), ("GET", "/.well-known/oauth-authorization-server"),
        ("GET", "/api/print/agent/jobs"), ("POST", "/api/print/agent/heartbeat"),
        ("GET", "/api/_test_seo/flux"), ("GET", "/api/_test_seo/fichier"),
    ]
    VARIABLES = {"date", "x-robots-tag", "set-cookie"}

    def _tout(self):
        c = TestClient(main.app, base_url="https://v1.mysifa.com")
        out = []
        for methode, chemin in self.REQUETES:
            r = c.request(methode, chemin, json={} if methode == "POST" else None, follow_redirects=False)
            entetes = {k: v for k, v in r.headers.items() if k.lower() not in self.VARIABLES}
            out.append((methode, chemin, r.status_code, r.content, entetes, r.headers.get("x-robots-tag")))
        return out

    def test_seul_x_robots_tag_change(self):
        from app.core.noindex import NoindexMiddleware
        avec = self._tout()
        origine = list(main.app.user_middleware)
        main.app.user_middleware = [m for m in origine if m.cls is not NoindexMiddleware]
        self.assertEqual(len(main.app.user_middleware), len(origine) - 1)
        main.app.middleware_stack = None
        try:
            sans = self._tout()
        finally:
            main.app.user_middleware = origine
            main.app.middleware_stack = None
        for a, s in zip(avec, sans):
            with self.subTest(requete=f"{a[0]} {a[1]}"):
                self.assertEqual(a[2:5], s[2:5])
                self.assertEqual(a[5], NOINDEX)
                self.assertIsNone(s[5])


if __name__ == "__main__":
    unittest.main(verbosity=2)
