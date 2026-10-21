"""Requête HTTP en cours, lisible depuis n'importe quel service.

Le suivi de l'usage IA (`app/services/ia_usage.py`) veut savoir d'où vient un
appel : l'API appelée et la page de l'utilisateur au moment du clic. Passer la
requête à travers les douze fonctions qui appellent Claude, puis à chaque
nouvelle, serait l'oubli assuré. Ce middleware pose ces deux informations dans
une variable de contexte ; un service les lit s'il en a besoin.

Middleware ASGI pur (comme `audit_middleware.py`) : la variable est posée dans
la tâche qui exécute la route, et recopiée dans le fil d'exécution des routes
synchrones. Hors requête (boucles de fond, scripts), `courante()` rend None.

La page vient de l'en-tête `Referer`, gardée seulement si elle est sur le même
hôte : chemin + paramètres, jamais l'hôte ni le fragment (#).
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Optional
from urllib.parse import urlsplit

_REQUETE: ContextVar[Optional[dict]] = ContextVar("mysifa_requete_courante", default=None)


def courante() -> Optional[dict]:
    """{"api": "/api/…", "methode": "POST", "page": "/tools?outil=…"} ou None."""
    return _REQUETE.get()


def _entete(scope, nom: bytes) -> str:
    for cle, valeur in scope.get("headers") or []:
        if cle == nom:
            try:
                return valeur.decode("latin-1")
            except Exception:
                return ""
    return ""


def _page(scope) -> str:
    ref = _entete(scope, b"referer")
    if not ref:
        return ""
    try:
        u = urlsplit(ref)
    except Exception:
        return ""
    hote = _entete(scope, b"host")
    if u.netloc and hote and u.netloc != hote:
        return ""
    page = (u.path or "/") + (("?" + u.query) if u.query else "")
    return page[:500]


class RequeteCouranteMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or not (scope.get("path") or "").startswith("/api/"):
            await self.app(scope, receive, send)
            return
        jeton = _REQUETE.set({
            "api": (scope.get("path") or "")[:300],
            "methode": (scope.get("method") or "").upper(),
            "page": _page(scope),
        })
        try:
            await self.app(scope, receive, send)
        finally:
            _REQUETE.reset(jeton)
