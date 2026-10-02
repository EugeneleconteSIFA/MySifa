"""MySifa — Aperçu du futur site vitrine (/website/)

Accès : /website/ et ses sous-pages /website/<chemin>/
Tout utilisateur authentifié. Les pages servent à montrer la refonte du site
public avant sa mise en ligne : elles restent derrière la connexion et ne
sont pas indexées (meta robots + en-tête X-Robots-Tag).

Les pages vivent dans app/web/website/<chemin>/index.html, hors de /static,
pour ne pas être lisibles sans session. Images, feuille de style et script
partagés sont dans static/website/. Les liens entre pages sont relatifs :
/website sans barre finale redirige vers /website/ pour qu'ils se résolvent.

Les mêmes fichiers sont exportés vers www.sifapro.fr par
tools/website_export.py (qui retire le noindex).
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from services.auth_service import get_current_user

router = APIRouter()

_ROOT = Path(__file__).with_name("website").resolve()
_HEADERS = {"X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-cache"}

_PAGE_404 = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="robots" content="noindex, nofollow"><title>Page introuvable · SIFA</title></head>
<body style="font-family:system-ui,sans-serif;padding:48px">
<h1>Page introuvable</h1><p><a href="/website/">Retour à l'accueil du site vitrine</a></p>
</body></html>"""


def _refus_connexion(request: Request):
    """None si la session est valide, sinon la redirection vers la connexion."""
    try:
        get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url=f"/?next={request.url.path}", status_code=302)
        raise
    return None


def _fichier(chemin: str):
    """index.html de la page demandée, ou None.

    Refuse les segments « . », « .. », cachés (« .git ») ou internes
    (« _partials »), puis vérifie après résolution que le fichier reste dans
    le dossier des pages : aucune sortie possible par « .. » ni par un lien.
    """
    morceaux = [m for m in chemin.split("/") if m]
    for m in morceaux:
        if m.startswith((".", "_")) or "\\" in m or "\x00" in m:
            return None
    if morceaux and morceaux[-1] == "index.html":
        morceaux = morceaux[:-1]
    try:
        cible = _ROOT.joinpath(*morceaux, "index.html").resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if not cible.is_relative_to(_ROOT) or not cible.is_file():
        return None
    return cible


@router.get("/website", response_class=HTMLResponse)
def website_racine(request: Request):
    refus = _refus_connexion(request)
    if refus:
        return refus
    return RedirectResponse(url="/website/", status_code=301)


@router.get("/website/{chemin:path}", response_class=HTMLResponse)
def website_page(request: Request, chemin: str = ""):
    refus = _refus_connexion(request)
    if refus:
        return refus
    fichier = _fichier(chemin)
    if fichier is None:
        return HTMLResponse(content=_PAGE_404, status_code=404, headers=_HEADERS)
    # Dossier demandé sans barre finale : on la rajoute, sinon les liens
    # relatifs de la page partiraient du dossier parent.
    if chemin and not chemin.endswith("/") and not chemin.endswith("index.html"):
        return RedirectResponse(url=f"/website/{chemin}/", status_code=301)
    return HTMLResponse(content=fichier.read_text(encoding="utf-8"), headers=_HEADERS)
