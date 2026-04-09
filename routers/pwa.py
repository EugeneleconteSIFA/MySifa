"""MySifa — PWA (manifest + service worker).

Permet l'installation « Ajouter à l'écran d'accueil » (mobile) / « Installer » (desktop).
"""

from fastapi import APIRouter
from fastapi.responses import Response


router = APIRouter()


@router.get("/manifest.webmanifest")
def manifest():
    # Icônes carrées, l'OS applique son propre masque (iOS/Android/desktop).
    body = {
        "name": "MySifa",
        "short_name": "MySifa",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#0a0e17",
        "theme_color": "#0a0e17",
        "icons": [
            {"src": "/static/mys_icon_192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/mys_icon_512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }
    import json

    return Response(
        content=json.dumps(body, ensure_ascii=False),
        media_type="application/manifest+json",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/service-worker.js")
def service_worker():
    # SW minimal (installabilité). On évite un cache agressif pour ne pas bloquer les mises à jour.
    js = r"""/* MySifa service worker (minimal) */
self.addEventListener('install', (event) => { self.skipWaiting(); });
self.addEventListener('activate', (event) => { event.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', (event) => { /* passthrough */ });
"""
    return Response(
        content=js,
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-cache",
            # important: certains navigateurs exigent le bon type
            "Service-Worker-Allowed": "/",
        },
    )

