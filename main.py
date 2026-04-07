"""
MyProd by SIFA — v0.5.0
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from config import APP_TITLE, APP_VERSION, HOST, PORT
from frontend.html import FRONTEND_HTML

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
from frontend.planning_page import router as planning_page_router

app = FastAPI(title=APP_TITLE, version=APP_VERSION)

# Static assets (chat widget, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(planning_router)
app.include_router(router_stock)
app.include_router(chat_router)
app.include_router(planning_page_router)

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    return FRONTEND_HTML

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
