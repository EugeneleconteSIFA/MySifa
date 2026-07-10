"""
Kernse — App FastAPI de la console plateforme.

Cette app est une des trois apps distinctes du repo (voir kernse/CLAUDE.md
« architecture non-monolithique »). Elle tourne :

    * kernse-admin-v2 : port 8102 → admin.kernse.fr (prod)
    * kernse-admin-v1 : port 8104 → admin-v1.kernse.fr (test)

Elle n'expose AUCUNE route publique. Auth : session cookie + 2FA TOTP
(voir kernse/shared/auth/).

Endpoints :
    GET  /healthz                                     → healthcheck
    GET  /login                                        → page de connexion
    POST /auth/login                                   → auth
    POST /auth/logout                                  → déconnexion
    GET  /2fa/setup                                    → activer la 2FA
    POST /auth/2fa/enable                              → enregistre le secret TOTP
    GET  /2fa/verify                                   → saisie code TOTP
    POST /auth/2fa/verify                              → valide le code TOTP
    POST /auth/2fa/disable                             → désactive la 2FA
    GET  /admin                                        → console HTML
    GET  /api/v1/clients                               → liste clients
    GET  /api/v1/clients/{id}                          → fiche client
    POST /api/v1/clients                               → créer client
    POST /api/v1/provision/client/{id}                 → provisionner l'instance
    POST /api/v1/promotion/client/{id}                 → promouvoir un client
    POST /api/v1/promotion/client/{id}/unpin           → détacher épingle
    POST /api/v1/promotion/all                         → promouvoir la flotte
    GET  /api/v1/audit                                 → journal d'audit
"""
from __future__ import annotations

import sqlite3

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse

from kernse.admin.config import APP_TITLE, APP_VERSION, ENV_NAME, PLATFORM_DB_PATH
from kernse.admin.routers import audit as audit_router
from kernse.admin.routers import auth as auth_router
from kernse.admin.routers import clients as clients_router
from kernse.admin.routers import promotion as promotion_router
from kernse.admin.routers import provision as provision_router
from kernse.admin.routers.auth import bootstrap_superadmin_if_needed
from kernse.admin.web import console_page, login_page, twofa_page
from kernse.shared.auth.dependency import HTTPRedirect
from kernse.shared.db.schema import init_platform_db, seed_platform_defaults


app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    # Doc OpenAPI privée : sur admin uniquement, jamais public.
    docs_url="/docs",
    redoc_url=None,
)


# Handler dédié aux redirections HTML levées depuis une dépendance
# (voir kernse.shared.auth.dependency.HTTPRedirect). Sans ce handler,
# `raise HTTPRedirect(...)` déclenche un 500 (FastAPI ne sait pas
# comment sérialiser l'exception).
@app.exception_handler(HTTPRedirect)
async def _handle_redirect(request: Request, exc: HTTPRedirect) -> RedirectResponse:
    return RedirectResponse(exc.url, status_code=exc.status_code)


# Racine → redirige vers /admin (dashboard). Si l'utilisateur n'est pas
# connecté, la dépendance `require_superadmin` le renverra vers /login.
@app.get("/", include_in_schema=False)
def _root_redirect() -> RedirectResponse:
    return RedirectResponse("/admin", status_code=302)


@app.on_event("startup")
def _boot() -> None:
    """Initialise la DB plateforme, pose les valeurs par défaut, et
    bootstrappe un superadmin depuis l'env si aucun compte n'existe."""
    init_platform_db(str(PLATFORM_DB_PATH))
    seed_platform_defaults(str(PLATFORM_DB_PATH), actor_email="system:boot")
    bootstrap_superadmin_if_needed()


@app.get("/healthz")
def healthz() -> JSONResponse:
    """Healthcheck utilisé par le monitoring plateforme."""
    try:
        conn = sqlite3.connect(str(PLATFORM_DB_PATH))
        conn.execute("SELECT 1").fetchone()
        conn.close()
        return JSONResponse({"status": "ok", "env": ENV_NAME, "version": APP_VERSION})
    except Exception as exc:
        return JSONResponse(
            {"status": "ko", "env": ENV_NAME, "error": str(exc)[:200]},
            status_code=503,
        )


# Routers API
app.include_router(clients_router.router)
app.include_router(provision_router.router)
app.include_router(promotion_router.router)
app.include_router(audit_router.router)
app.include_router(auth_router.router)

# Pages HTML (console + login + 2FA)
app.include_router(login_page.router)
app.include_router(twofa_page.router)
app.include_router(console_page.router)


if __name__ == "__main__":
    import uvicorn

    from kernse.admin.config import HOST, PORT

    uvicorn.run("kernse.admin.main:app", host=HOST, port=PORT, log_level="info")
