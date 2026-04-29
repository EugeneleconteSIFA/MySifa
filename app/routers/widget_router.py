"""MyProd Widget — routes /widget, /install/widget, /download/widget-mac et /download/widget-win

Nouveau fonctionnement (v2) :
  - Les installateurs sont des binaires natifs compilés avec electron-builder
    (DMG pour macOS, NSIS EXE pour Windows) — Node.js est embarqué.
  - Le serveur sert simplement les fichiers pré-compilés depuis myprod-widget/dist/.
  - Pour compiler les installateurs, voir myprod-widget/BUILD.md.
"""

import glob
import os
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from services.auth_service import get_current_user, require_admin
from app.web.widget_page import WIDGET_HTML
from app.web.widget_install_page import WIDGET_INSTALL_HTML

router = APIRouter()

# Dossier de sortie electron-builder
_WIDGET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "myprod-widget")
_DIST_DIR   = os.path.join(_WIDGET_DIR, "dist")


def _find_latest(pattern: str) -> str | None:
    """Retourne le fichier le plus récent correspondant au glob, ou None."""
    matches = glob.glob(os.path.join(_DIST_DIR, pattern))
    if not matches:
        return None
    return max(matches, key=os.path.getmtime)


@router.get("/widget", response_class=HTMLResponse)
def widget_page(request: Request):
    """Page widget autonome — chargée par l'app Electron MyProd."""
    return HTMLResponse(content=WIDGET_HTML, status_code=200)


@router.get("/install/widget", response_class=HTMLResponse)
def install_widget_page(request: Request):
    """Page de téléchargement Mac/Windows pour le widget."""
    require_admin(request)
    return HTMLResponse(content=WIDGET_INSTALL_HTML, status_code=200)


@router.get("/download/widget-mac")
def download_widget_mac(request: Request):
    """
    Télécharge le DMG macOS compilé par electron-builder.
    Fichier servi depuis myprod-widget/dist/*.dmg.
    Si absent : 404 avec instructions pour builder.
    """
    require_admin(request)

    # Préférer arm64 (Apple Silicon) — fallback x64
    dmg = _find_latest("*arm64*.dmg") or _find_latest("*.dmg")
    if not dmg:
        raise HTTPException(
            status_code=404,
            detail=(
                "Installateur macOS introuvable. "
                "Compilez-le avec : cd myprod-widget && npm install && npm run build:mac "
                "(voir BUILD.md)"
            ),
        )

    filename = os.path.basename(dmg)
    return FileResponse(
        path=dmg,
        media_type="application/octet-stream",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/download/widget-win")
def download_widget_win(request: Request):
    """
    Télécharge l'installateur NSIS Windows compilé par electron-builder.
    Fichier servi depuis myprod-widget/dist/*Setup*.exe.
    Si absent : 404 avec instructions pour builder.
    """
    require_admin(request)

    exe = _find_latest("*Setup*.exe") or _find_latest("*.exe")
    if not exe:
        raise HTTPException(
            status_code=404,
            detail=(
                "Installateur Windows introuvable. "
                "Compilez-le avec : cd myprod-widget && npm install && npm run build:win "
                "(voir BUILD.md)"
            ),
        )

    filename = os.path.basename(exe)
    return FileResponse(
        path=exe,
        media_type="application/octet-stream",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/download/widget")
def download_widget_legacy(request: Request):
    """Redirige vers la page de téléchargement."""
    require_admin(request)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/install/widget", status_code=302)
