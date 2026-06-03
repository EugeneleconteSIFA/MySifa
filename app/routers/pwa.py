"""MySifa — PWA (manifest + service worker).

Permet l'installation « Ajouter à l'écran d'accueil » (mobile) / « Installer » (desktop).
"""

import json

from fastapi import APIRouter
from fastapi.responses import Response


router = APIRouter()

_MANIFEST_HEADERS = {"Cache-Control": "no-cache"}
_MANIFEST_MEDIA_TYPE = "application/manifest+json"


def _manifest_response(body: dict) -> Response:
    return Response(
        content=json.dumps(body, ensure_ascii=False),
        media_type=_MANIFEST_MEDIA_TYPE,
        headers=_MANIFEST_HEADERS,
    )


@router.get("/manifest.webmanifest")
def manifest():
    # Icônes carrées, l'OS applique son propre masque (iOS/Android/desktop).
    return _manifest_response({
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
    })


@router.get("/manifest-stock.webmanifest")
def manifest_stock():
    return _manifest_response({
        "name": "MyStock",
        "short_name": "MyStock",
        "start_url": "/stock",
        "scope": "/",
        "display": "standalone",
        "background_color": "#0a0e17",
        "theme_color": "#0a0e17",
        "icons": [
            {"src": "/static/stock_favicon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/stock_favicon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    })


@router.get("/manifest-expe.webmanifest")
def manifest_expe():
    return _manifest_response({
        "name": "MyExpé",
        "short_name": "MyExpé",
        "start_url": "/expe",
        "scope": "/",
        "display": "standalone",
        "background_color": "#0a0e17",
        "theme_color": "#0a0e17",
        "icons": [
            {"src": "/static/expe_favicon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/expe_favicon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    })


@router.get("/manifest-planning-rh.webmanifest")
def manifest_planning_rh():
    return _manifest_response({
        "name": "Planning RH",
        "short_name": "Planning RH",
        "start_url": "/planning-rh",
        "scope": "/",
        "display": "standalone",
        "background_color": "#0a0e17",
        "theme_color": "#0a0e17",
        "icons": [
            {"src": "/static/planning_rh_favicon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/planning_rh_favicon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    })


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

