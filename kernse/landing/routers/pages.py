"""
Kernse-landing — pages publiques (server-side rendering avec Jinja2).
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from kernse.landing.config import (
    CONTACT_EMAIL,
    DEMO_URL,
    IS_STAGING,
    TEMPLATES_DIR,
)


router = APIRouter(tags=["landing"])
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _ctx(request: Request, **extra) -> dict:
    return {
        "request": request,
        "is_staging": IS_STAGING,
        "demo_url": DEMO_URL,
        "contact_email": CONTACT_EMAIL,
        **extra,
    }


@router.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    # Starlette >= 0.35 : `request` doit être passé en premier argument
    # positionnel à `TemplateResponse` (l'ancienne signature name-first
    # est dépréciée et lève « unhashable type: 'dict' » en runtime).
    return templates.TemplateResponse(request, "home.html.j2", _ctx(request))


@router.get("/contact", response_class=HTMLResponse)
def contact(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "contact.html.j2", _ctx(request))


@router.get("/demo")
def demo_redirect() -> RedirectResponse:
    """Redirige vers l'instance démo provisionnée manuellement."""
    return RedirectResponse(DEMO_URL, status_code=307)


@router.get("/mentions-legales", response_class=HTMLResponse)
def mentions(request: Request) -> HTMLResponse:
    # Placeholder — à rédiger avec un juriste avant ouverture publique.
    return HTMLResponse(
        "<h1>Mentions légales</h1><p>À compléter avant la mise en ligne publique.</p>",
        status_code=200,
    )


@router.get("/cgv", response_class=HTMLResponse)
def cgv(request: Request) -> HTMLResponse:
    # Placeholder — à rédiger avec un juriste avant premier client payé.
    return HTMLResponse(
        "<h1>Conditions générales de vente</h1><p>À compléter avant la mise en ligne publique.</p>",
        status_code=200,
    )
