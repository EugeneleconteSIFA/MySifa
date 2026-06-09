"""
MyProd by SIFA — v0.5.0
"""
import os
from contextlib import asynccontextmanager

import re

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from config import APP_TITLE, APP_VERSION, HOST, PORT, BASE_DIR, ENV_NAME, IS_STAGING
from app.web.html import render_frontend_html

from routers.auth       import router as auth_router
from routers.imports    import router as router_imports
from routers.filters    import router as router_filters
from routers.historique import router as router_historique
from routers.production import router as router_production
from routers.stats      import router as router_stats
from routers.dossiers   import router as router_dossiers
from routers.saisies    import router as router_saisies
from routers.rentabilite import router as router_rentabilite
from app.routers.matiere_prix import router as router_matiere_prix
from routers.planning import router as planning_router
from routers.stock import router as router_stock
from app.routers.reconciliation import router as reconciliation_router
from routers.support import router as support_router
from app.routers.messages import router as messages_router
from app.routers.compta import router as compta_router
from app.web.planning_page import router as planning_page_router
from app.web.prod_page import router as prod_page_router
from app.web.stock_page import router as stock_page_router
from app.web.compta_page import router as compta_page_router
from app.web.expe_page import router as expe_page_router
from app.web.devis_page import router as devis_page_router
from app.routers.expe_departs import router as expe_departs_router
from app.routers.settings import router as settings_api_router
from app.routers.clients import router as clients_api_router
from app.web.settings_page import router as settings_page_router
from app.routers.fabrication import router as fabrication_api_router
from app.routers.of_import import router as of_import_router
from app.web.fabrication_page import router as fabrication_page_router
from app.routers.planning_rh import router as planning_rh_api_router
from app.web.planning_rh_page import router as planning_rh_page_router
from app.routers.paie import router as paie_api_router
from app.web.paie_page import router as paie_page_router
from app.routers.widget_router import router as widget_router
from app.routers.db_viewer import router as db_viewer_api_router
from app.web.db_viewer_page import router as db_viewer_page_router
from app.web.profil_page import router as profil_page_router
from app.web.messages_page import router as messages_page_router
from app.routers.calendrier import router as calendrier_api_router
from app.web.calendrier_page import router as calendrier_page_router
from app.routers.ai import router as ai_router
from app.routers.chat import router as chat_router
from app.routers.alerts import router as alerts_router
from app.routers.postit import router as postit_router
from app.routers.ao import router as ao_router
from app.routers.ao_portail import router_api as ao_portail_api_router
from app.routers.ao_portail import router_html as ao_portail_html_router
from app.routers.expe_portail import router_api as expe_portail_api_router
from app.routers.expe_portail import router_html as expe_portail_html_router
from app.web.ao_page import router as ao_page_router
from app.routers.pricing import router as pricing_router
from app.web.pricing_page import router as pricing_page_router
from app.routers.dashboards import router as dashboards_router
from app.routers.api_bridge import router as bridge_router
from app.routers.bat import router as bat_api_router
from app.web.bat_page import router as bat_page_router
from app.routers.qualite import router as qualite_api_router
from app.web.qualite_page import router as qualite_page_router
from app.routers.pwa import router as pwa_router
from app.routers.push import router as push_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown — remplace @app.on_event('startup') (déprécié)."""
    print(f"[MySifa] Boot — ENV_NAME={ENV_NAME} version={APP_VERSION} port={PORT}")
    # v1 (staging) partage la DB avec la prod : aucune écriture au boot.
    # Les seeds (emplacements_plan, chat channels) sont la responsabilité exclusive de v2.
    if IS_STAGING:
        print("[MySifa] Staging v1 : seeds de boot ignorés (DB partagée avec prod).")
        yield
        return
    try:
        from app.core.database import get_db, sync_emplacements_plan_from_csv

        with get_db() as _conn:
            _count = _conn.execute("SELECT COUNT(*) FROM emplacements_plan").fetchone()[0]
        if _count == 0:
            n = sync_emplacements_plan_from_csv()
            print(f"[MySifa] emplacements_plan : {n} code(s) depuis CSV (seed initial)")
        else:
            print(f"[MySifa] emplacements_plan : {_count} code(s) en base — import CSV ignoré")
    except Exception as e:
        print(f"[MySifa] emplacements_plan : import CSV ignoré ({e})")
    try:
        from app.routers.chat import seed_default_channels_on_startup

        seed_default_channels_on_startup()
    except Exception as e:
        print(f"[MySifa] chat seed ignoré ({e})")
    yield


app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)

# Static assets (chat widget, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

_uploads_root = os.path.join(BASE_DIR, "uploads")
os.makedirs(os.path.join(_uploads_root, "traca"), exist_ok=True)
os.makedirs(os.path.join(_uploads_root, "avatars"), exist_ok=True)
os.makedirs(os.path.join(_uploads_root, "chat"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_uploads_root), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def no_cache_planning(request: Request, call_next):
    """Évite cache navigateur / proxy sur le planning (données toujours lues en base)."""
    response = await call_next(request)
    p = request.url.path
    if p.startswith("/api/planning") or p == "/planning" or p.startswith("/portail/ao/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


# ── Bandeau staging v1 ───────────────────────────────────────────────────────
# Injecté dans toutes les réponses HTML lorsque ENV_NAME=v1, pour qu'il apparaisse
# sur les pages standalone (profil, calendrier, db_viewer, settings, planning,
# fabrication, etc.) en plus du shell principal (app/web/html.py).
# Pas d'effet en prod (v2) : la fonction sort tôt si IS_STAGING est faux.
_STAGING_BANDEAU_CSS = (
    "<style>"
    ".staging-bandeau{position:fixed;top:0;left:0;right:0;height:24px;background:#dc2626;"
    "color:#fff;font-size:11px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;"
    "display:flex;align-items:center;justify-content:center;gap:10px;z-index:99999;"
    "font-family:'Segoe UI',system-ui,sans-serif;box-shadow:0 1px 6px rgba(220,38,38,.4);"
    "pointer-events:none}"
    ".staging-bandeau::before{content:\"●\";color:#fef2f2;font-size:9px;line-height:1}"
    "body{padding-top:24px!important}"
    "body .sidebar{top:24px!important}"
    "body .mobile-topbar{top:24px!important}"
    "</style>"
)
_STAGING_BANDEAU_HTML = (
    '<div class="staging-bandeau">'
    'v1 — Environnement de test — DB partagée avec la prod'
    '</div>'
)
_BODY_OPEN_RE = re.compile(rb"(<body[^>]*>)", re.IGNORECASE)


@app.middleware("http")
async def inject_staging_bandeau(request: Request, call_next):
    """Injecte le bandeau staging dans toutes les réponses HTML quand ENV_NAME=v1."""
    response = await call_next(request)
    if not IS_STAGING:
        return response
    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type.lower():
        return response
    if not hasattr(response, "body_iterator"):
        return response
    body_bytes = b""
    async for chunk in response.body_iterator:
        body_bytes += chunk if isinstance(chunk, (bytes, bytearray)) else chunk.encode("utf-8")
    # Ne rien faire si déjà présent (page rendue via render_frontend_html)
    if b"staging-bandeau" in body_bytes:
        new_headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
        return Response(
            content=body_bytes,
            status_code=response.status_code,
            headers=new_headers,
            media_type=response.media_type,
        )
    # Injection CSS avant </head>
    css_bytes = _STAGING_BANDEAU_CSS.encode("utf-8")
    if b"</head>" in body_bytes:
        body_bytes = body_bytes.replace(b"</head>", css_bytes + b"</head>", 1)
    # Injection HTML juste après <body…>
    bandeau_bytes = _STAGING_BANDEAU_HTML.encode("utf-8")
    new_body, count = _BODY_OPEN_RE.subn(rb"\1" + bandeau_bytes, body_bytes, count=1)
    if count == 0:
        # Pas de balise <body> : on n'a pas affaire à un document HTML complet, on laisse tel quel
        new_body = body_bytes
    new_headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
    return Response(
        content=new_body,
        status_code=response.status_code,
        headers=new_headers,
        media_type=response.media_type,
    )


app.include_router(auth_router)
app.include_router(router_imports)
app.include_router(router_filters)
app.include_router(router_historique)
app.include_router(router_production)
app.include_router(router_stats)
app.include_router(router_dossiers)
app.include_router(router_saisies)
app.include_router(router_rentabilite)
app.include_router(router_matiere_prix, prefix="/api/matiere")
app.include_router(planning_router)
app.include_router(router_stock)
app.include_router(reconciliation_router)
app.include_router(support_router)
app.include_router(messages_router)
app.include_router(compta_router)
app.include_router(planning_page_router)
app.include_router(prod_page_router)
app.include_router(stock_page_router)
app.include_router(compta_page_router)
app.include_router(expe_page_router)
app.include_router(devis_page_router)
app.include_router(expe_departs_router, prefix="/api/expe")
app.include_router(settings_api_router)
app.include_router(clients_api_router)
app.include_router(settings_page_router)
app.include_router(fabrication_api_router)
app.include_router(of_import_router, prefix="")
app.include_router(fabrication_page_router)
app.include_router(planning_rh_api_router)
app.include_router(planning_rh_page_router)
app.include_router(paie_api_router)
app.include_router(paie_page_router)
app.include_router(widget_router)
app.include_router(db_viewer_api_router)
app.include_router(db_viewer_page_router)
app.include_router(profil_page_router)
app.include_router(messages_page_router)
app.include_router(calendrier_api_router)
app.include_router(calendrier_page_router)
app.include_router(ai_router)
app.include_router(chat_router)
app.include_router(alerts_router)
app.include_router(postit_router)
app.include_router(ao_router)
app.include_router(ao_portail_html_router)
app.include_router(ao_portail_api_router)
app.include_router(expe_portail_html_router)
app.include_router(expe_portail_api_router)
app.include_router(ao_page_router)
app.include_router(pricing_router)
app.include_router(pricing_page_router)
app.include_router(dashboards_router)
app.include_router(bridge_router)
app.include_router(bat_api_router)
app.include_router(bat_page_router)
app.include_router(qualite_api_router)
app.include_router(qualite_page_router)
app.include_router(pwa_router)
app.include_router(push_router)


@app.get("/healthz", include_in_schema=False)
def healthz():
    """Sonde de santé — utilisée par le script de promotion v1→v2 pour valider
    qu'une mise à jour n'a pas cassé l'instance. Pong DB minimal sans toucher
    aux tables métier ; échec → réponse non-200 → rollback automatique."""
    from fastapi.responses import JSONResponse
    try:
        from app.core.database import get_db
        with get_db() as _conn:
            _conn.execute("SELECT 1").fetchone()
        return JSONResponse({
            "status": "ok",
            "env": ENV_NAME,
            "version": APP_VERSION,
        })
    except Exception as e:
        return JSONResponse(
            {"status": "ko", "env": ENV_NAME, "version": APP_VERSION, "error": str(e)[:200]},
            status_code=503,
        )


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(os.path.join(BASE_DIR, "static", "favicon.ico"))


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    return render_frontend_html("portal")

@app.get("/users")
def users_redirect():
    return RedirectResponse(url="/settings", status_code=302)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
