"""« noindex » sur tout ce qui n'est pas l'accueil public de la prod.

Seule « / » de l'instance de prod, appelée par son domaine public
(`public_base_url()`), est ouverte aux moteurs, avec robots.txt, sitemap.xml et
/static/ (l'image de partage). Tout le reste reçoit `X-Robots-Tag: noindex,
nofollow` : v1 (sinon copie de la prod dans Google), l'ERP, le domaine nu, une
IP, les pages de modules, les liens du portail Espace envoyés aux destinataires
externes et l'API.

Middleware ASGI pur (comme `requete_courante.py`) : l'en-tête est ajouté au
message `http.response.start`, le corps passe sans être lu. Streaming et
téléchargements restent intacts, et le coût par requête est de quelques
microsecondes, là où un `@app.middleware("http")` en ajoutait environ 180.
"""
from __future__ import annotations

from urllib.parse import urlparse

from config import SEO_INDEXABLE, public_base_url

CHEMINS_PUBLICS = ("/", "/robots.txt", "/sitemap.xml")
_ENTETE = (b"x-robots-tag", b"noindex, nofollow")


def hote_indexable(hote: str) -> bool:
    """Vrai sur l'instance de prod appelée par son domaine public. Faux sur v1, l'ERP, le domaine nu, une IP."""
    hote = (hote or "").split(":")[0].strip().lower()
    return SEO_INDEXABLE and hote == (urlparse(public_base_url()).hostname or "").lower()


def _hote(scope) -> str:
    for cle, valeur in scope.get("headers") or []:
        if cle == b"host":
            return valeur.decode("latin-1")
    return ""


class NoindexMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        p = scope.get("path") or "/"
        if (p in CHEMINS_PUBLICS or p.startswith("/static/")) and hote_indexable(_hote(scope)):
            await self.app(scope, receive, send)
            return

        async def envoyer(message):
            if message["type"] == "http.response.start":
                message["headers"] = [*message.get("headers", ()), _ENTETE]
            await send(message)

        await self.app(scope, receive, envoyer)
