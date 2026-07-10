"""
Kernse — App FastAPI de la landing publique.

Une des trois apps distinctes du repo. Tourne sur :

    * kernse-landing-v2 : port 8101 → www.kernse.fr (prod)
    * kernse-landing-v1 : port 8103 → v1.kernse.fr (test)

Aucune DB requise pour fonctionner. Aucune auth. Contenu 100% public.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from kernse.landing.config import (
    APP_TITLE,
    APP_VERSION,
    ENV_NAME,
    STATIC_DIR,
)
from kernse.landing.routers import pages


app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    # Pas de docs OpenAPI en public.
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(pages.router)


@app.get("/healthz")
def healthz() -> JSONResponse:
    return JSONResponse({"status": "ok", "env": ENV_NAME, "version": APP_VERSION})


if __name__ == "__main__":
    import uvicorn

    from kernse.landing.config import HOST, PORT

    uvicorn.run("kernse.landing.main:app", host=HOST, port=PORT, log_level="info")
