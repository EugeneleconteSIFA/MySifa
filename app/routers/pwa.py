"""MySifa — PWA (manifest + service worker).

Permet l'installation « Ajouter à l'écran d'accueil » (mobile) / « Installer » (desktop).
"""

import json

from fastapi import APIRouter
from fastapi.responses import Response

from config import APP_VERSION


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
    # SW minimal + handlers Web Push (notifications).
    # Pas de cache agressif côté fetch pour ne pas bloquer les mises à jour.
    # IMPORTANT : on injecte APP_VERSION dans le source du SW (commentaire en haut)
    # pour que chaque release modifie le byte-content servi par /service-worker.js.
    # Sans ça, le navigateur ne détecte aucun changement et garde l'ancien SW —
    # qui à son tour peut servir des assets cachés (anciens JS/CSS) à l'app.
    js = (
        f"/* MySifa service worker v{APP_VERSION} — bust:{APP_VERSION} */\n"
        r"""self.addEventListener('install', (event) => { self.skipWaiting(); });
self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    // Nettoie d'éventuels anciens caches d'une version précédente du SW
    try {
      const names = await caches.keys();
      await Promise.all(names.map(n => caches.delete(n)));
    } catch (e) {}
    await self.clients.claim();
  })());
});
self.addEventListener('fetch', (event) => { /* passthrough */ });"""
    )
    js_tail = r"""

// ─── Notifications push ───────────────────────────────────────────
self.addEventListener('push', (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; }
  catch (e) {
    try { data = { body: event.data ? event.data.text() : '' }; } catch (e2) {}
  }
  const title = data.title || 'MySifa';
  const body = data.body || '';
  const url = data.url || '/';
  const tag = data.tag || ('mysifa-' + Date.now());
  const options = {
    body: body,
    icon: '/static/mys_icon_192.png',
    badge: '/static/mys_icon_192.png',
    tag: tag,
    renotify: true,
    data: { url: url },
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil((async () => {
    const allClients = await clients.matchAll({ type: 'window', includeUncontrolled: true });
    // Focus l'onglet existant si déjà ouvert sur la même origine
    for (const c of allClients) {
      try {
        const u = new URL(c.url);
        if (u.origin === self.location.origin) {
          await c.focus();
          if ('navigate' in c) { try { c.navigate(target); } catch (e) {} }
          return;
        }
      } catch (e) {}
    }
    if (clients.openWindow) await clients.openWindow(target);
  })());
});
"""
    js = js + js_tail
    return Response(
        content=js,
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-cache",
            # important: certains navigateurs exigent le bon type
            "Service-Worker-Allowed": "/",
        },
    )

