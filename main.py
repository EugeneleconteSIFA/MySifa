"""
MyProd by SIFA — v0.5.0
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from config import APP_TITLE, APP_VERSION, HOST, PORT
from frontend.html import render_frontend_html

from routers.auth       import router as auth_router
from routers.imports    import router as router_imports
from routers.filters    import router as router_filters
from routers.historique import router as router_historique
from routers.production import router as router_production
from routers.stats      import router as router_stats
from routers.dossiers   import router as router_dossiers
from routers.saisies    import router as router_saisies
from routers.rentabilite import router as router_rentabilite
from routers.planning import router as planning_router
from routers.stock import router as router_stock
from routers.chat import router as chat_router
from routers.support import router as support_router
from app.routers.compta import router as compta_router
from frontend.planning_page import router as planning_page_router
from frontend.prod_page import router as prod_page_router
from frontend.stock_page import router as stock_page_router
from frontend.compta_page import router as compta_page_router
from app.web.expe_page import router as expe_page_router
from app.routers.settings import router as settings_api_router
from frontend.settings_page import router as settings_page_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown — remplace @app.on_event('startup') (déprécié)."""
    try:
        from database import sync_emplacements_plan_from_csv

        n = sync_emplacements_plan_from_csv()
        print(f"[MySifa] emplacements_plan : {n} code(s) depuis CSV")
    except Exception as e:
        print(f"[MySifa] emplacements_plan : import CSV ignoré ({e})")
    yield


app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)

# Static assets (chat widget, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

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
    if p.startswith("/api/planning") or p == "/planning":
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


app.include_router(auth_router)
app.include_router(router_imports)
app.include_router(router_filters)
app.include_router(router_historique)
app.include_router(router_production)
app.include_router(router_stats)
app.include_router(router_dossiers)
app.include_router(router_saisies)
app.include_router(router_rentabilite)
app.include_router(planning_router)
app.include_router(router_stock)
app.include_router(chat_router)
app.include_router(support_router)
app.include_router(compta_router)
app.include_router(planning_page_router)
app.include_router(prod_page_router)
app.include_router(stock_page_router)
app.include_router(compta_page_router)
app.include_router(expe_page_router)
app.include_router(settings_api_router)
app.include_router(settings_page_router)


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    return render_frontend_html("portal")

@app.get("/users")
def users_redirect():
    return RedirectResponse(url="/settings", status_code=302)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
