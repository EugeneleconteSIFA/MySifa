"""Page /website : maquette du site vitrine, derrière la connexion."""
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


def test_sans_session_redirige_vers_login(monkeypatch):
    def refuse(_request):
        raise HTTPException(status_code=401)
    monkeypatch.setattr(website_page, "get_current_user", refuse)
    r = _client().get("/website", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/?next=/website"


def test_avec_session_sert_la_page_non_indexee(monkeypatch):
    monkeypatch.setattr(website_page, "get_current_user", lambda _r: {"id": 1})
    r = _client().get("/website")
    assert r.status_code == 200
    assert r.headers["x-robots-tag"] == "noindex, nofollow"
    assert 'name="robots"' in r.text
    assert 'src="assets/' not in r.text
