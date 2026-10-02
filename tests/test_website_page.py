"""Pages /website/ : aperçu du site vitrine, derrière la connexion."""
import sys

sys.path.insert(0, ".")
import database  # noqa: F401  (toujours avant app.*)

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import app.web.website_page as website_page


def _client():
    app = FastAPI()
    app.include_router(website_page.router)
    return TestClient(app)


def _connecte(monkeypatch):
    monkeypatch.setattr(website_page, "get_current_user", lambda _r: {"id": 1})


def test_sans_session_redirige_vers_login(monkeypatch):
    def refuse(_request):
        raise HTTPException(status_code=401)
    monkeypatch.setattr(website_page, "get_current_user", refuse)
    c = _client()
    r = c.get("/website", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/?next=/website"
    r = c.get("/website/produits/etiquettes-bobines/", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/?next=/website/produits/etiquettes-bobines/"


def test_racine_sans_barre_redirige_vers_racine_avec_barre(monkeypatch):
    _connecte(monkeypatch)
    r = _client().get("/website", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "/website/"


def test_accueil_servi_non_indexe(monkeypatch):
    _connecte(monkeypatch)
    r = _client().get("/website/")
    assert r.status_code == 200
    assert r.headers["x-robots-tag"] == "noindex, nofollow"
    assert 'name="robots" content="noindex' in r.text
    assert '<link rel="canonical" href="https://www.sifapro.fr/">' in r.text
    assert 'src="assets/' not in r.text


def test_sous_page_servie(monkeypatch):
    _connecte(monkeypatch)
    r = _client().get("/website/produits/etiquettes-linerless/")
    assert r.status_code == 200
    assert "Étiquettes linerless</h1>" in r.text
    assert r.headers["x-robots-tag"] == "noindex, nofollow"
    assert '"BreadcrumbList"' in r.text


def test_dossier_sans_barre_redirige(monkeypatch):
    _connecte(monkeypatch)
    r = _client().get("/website/contact", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "/website/contact/"


def test_traversee_refusee(monkeypatch):
    _connecte(monkeypatch)
    c = _client()
    for chemin in ("/website/..%2fwebsite_page.py", "/website/%2e%2e/%2e%2e/main.py",
                   "/website/produits/..%2f..%2f..%2fconfig.py", "/website/_partials/",
                   "/website/_partials/site.json", "/website/.git/"):
        r = c.get(chemin, follow_redirects=False)
        assert r.status_code == 404, (chemin, r.status_code)
        assert "import " not in r.text, chemin


def test_page_inconnue_404(monkeypatch):
    _connecte(monkeypatch)
    r = _client().get("/website/produits/etiquettes-rfid/")
    assert r.status_code == 404
    assert r.headers["x-robots-tag"] == "noindex, nofollow"
