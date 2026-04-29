"""MyProd Widget — routes /widget, /install/widget, /download/widget-mac et /download/widget-win

Stratégie de distribution (deux modes, automatique) :
  - Mode natif  : si myprod-widget/dist/ contient un DMG ou EXE compilé par electron-builder,
                  le serveur le sert directement (installation en un double-clic, ~130 Mo).
  - Mode legacy : si aucun binaire n'est présent, le serveur génère un ZIP des sources +
                  script d'installation automatique (télécharge Node.js, lance npm install).
  Pour passer en mode natif : voir myprod-widget/BUILD.md.
"""

import io
import os
import glob as _glob
import zipfile
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from services.auth_service import get_current_user, require_admin
from app.web.widget_page import WIDGET_HTML
from app.web.widget_install_page import WIDGET_INSTALL_HTML

router = APIRouter()

_WIDGET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "myprod-widget")
_DIST_DIR   = os.path.join(_WIDGET_DIR, "dist")
_SERVER_URL  = "https://www.mysifa.com"


# ── Détection des binaires compilés ────────────────────────────────────────────

def _find_latest(pattern: str) -> str | None:
    matches = _glob.glob(os.path.join(_DIST_DIR, pattern))
    if not matches:
        return None
    return max(matches, key=os.path.getmtime)


def _native_mac() -> str | None:
    return _find_latest("*arm64*.dmg") or _find_latest("*.dmg")


def _native_win() -> str | None:
    return _find_latest("*Setup*.exe") or _find_latest("*.exe")


# ── Routes principales ──────────────────────────────────────────────────────────

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
    Télécharge l'installateur macOS.
    • Mode natif  : DMG electron-builder (si présent dans dist/)
    • Mode legacy : ZIP sources + script .command (fallback automatique)
    """
    require_admin(request)

    dmg = _native_mac()
    if dmg:
        filename = os.path.basename(dmg)
        return FileResponse(
            path=dmg,
            media_type="application/octet-stream",
            filename=filename,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # Fallback : ZIP legacy
    buf = _create_widget_zip("mac")
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="myprod-widget-macos.zip"'},
    )


@router.get("/download/widget-win")
def download_widget_win(request: Request):
    """
    Télécharge l'installateur Windows.
    • Mode natif  : NSIS EXE electron-builder (si présent dans dist/)
    • Mode legacy : ZIP sources + script .bat (fallback automatique)
    """
    require_admin(request)

    exe = _native_win()
    if exe:
        filename = os.path.basename(exe)
        return FileResponse(
            path=exe,
            media_type="application/octet-stream",
            filename=filename,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # Fallback : ZIP legacy
    buf = _create_widget_zip("win")
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="myprod-widget-windows.zip"'},
    )


@router.get("/download/widget")
def download_widget_legacy(request: Request):
    require_admin(request)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/install/widget", status_code=302)


# ── Génération ZIP legacy ───────────────────────────────────────────────────────

def _read_installer_bytes(filename: str) -> bytes:
    fpath = os.path.join(_WIDGET_DIR, filename)
    if not os.path.isfile(fpath):
        return b""
    with open(fpath, "rb") as f:
        return f.read()


def _create_widget_zip(platform: str) -> io.BytesIO:
    """Génère un ZIP des sources + script d'installation (mode legacy)."""
    buf = io.BytesIO()
    skip = {
        "node_modules", "dist", ".git", "__pycache__",
        "Install-MyProd-Widget-Mac.command", "Install-MyProd-Widget-Windows.bat",
        "Installer-MyProd-Widget.command", "Lancer-Widget.sh",
        "installer-mac.applescript", "installer-windows.bat", "installer-windows.ps1",
        "BUILD.md",
    }

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if os.path.isdir(_WIDGET_DIR):
            for fname in os.listdir(_WIDGET_DIR):
                if fname in skip or fname.startswith("."):
                    continue
                fpath = os.path.join(_WIDGET_DIR, fname)
                if not os.path.isfile(fpath):
                    continue
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    content = content.replace("http://localhost:8000", _SERVER_URL)
                    zf.writestr(f"myprod-widget/{fname}", content.encode("utf-8"))
                except Exception:
                    pass

        if platform == "mac":
            installer = _build_mac_installer()
            info = zipfile.ZipInfo("Installer-MyProd-Widget.command")
            info.external_attr = (0o755 << 16)
            zf.writestr(info, installer.encode("utf-8"))
            zf.writestr("LISEZ-MOI.txt", _readme_mac().encode("utf-8"))
        else:
            installer = _build_win_installer()
            zf.writestr("Installer-MyProd-Widget.bat", installer.encode("utf-8"))
            zf.writestr("LISEZ-MOI.txt", _readme_win().encode("utf-8"))

    buf.seek(0)
    return buf


def _build_mac_installer() -> str:
    return f"""#!/bin/bash
# MyProd Widget — Installateur macOS (legacy)
set -e
WIDGET_DIR="$HOME/.myprod-widget"
mkdir -p "$WIDGET_DIR"
SRC="$(cd "$(dirname "$0")/myprod-widget" 2>/dev/null && pwd || echo "")"
if [ -n "$SRC" ]; then
  cp -r "$SRC/." "$WIDGET_DIR/"
fi
cd "$WIDGET_DIR"
if ! command -v node &>/dev/null; then
  echo "Node.js introuvable — téléchargement..."
  curl -fsSL https://nodejs.org/dist/v20.11.0/node-v20.11.0-darwin-arm64.tar.gz | tar -xz -C "$HOME/.local" --strip-components=1 2>/dev/null || \\
  curl -fsSL https://nodejs.org/dist/v20.11.0/node-v20.11.0-darwin-x64.tar.gz   | tar -xz -C "$HOME/.local" --strip-components=1
  export PATH="$HOME/.local/bin:$PATH"
fi
npm install --prefer-offline
node_modules/.bin/electron . &
echo "Widget lancé !"
"""


def _build_win_installer() -> str:
    return f"""@echo off
setlocal
set WIDGET_DIR=%USERPROFILE%\\.myprod-widget
if not exist "%WIDGET_DIR%" mkdir "%WIDGET_DIR%"
xcopy /E /Y "%~dp0myprod-widget\\*" "%WIDGET_DIR%\\" >nul 2>&1
cd /d "%WIDGET_DIR%"
where node >nul 2>&1
if %errorlevel% neq 0 (
  echo Node.js introuvable. Installez-le depuis https://nodejs.org puis relancez ce script.
  pause & exit /b 1
)
npm install --prefer-offline
start "" node_modules\\.bin\\electron .
echo Widget lance !
"""


def _readme_mac() -> str:
    return (
        "=== MyProd Widget - Installation macOS (version legacy) ===\n\n"
        "NOTE : Cette version nécessite Node.js. Pour une installation en un clic\n"
        "       (sans Node.js), demandez à l'administrateur de compiler les installateurs natifs.\n\n"
        "INSTALLATION\n"
        "------------\n"
        "1. Décompressez ce ZIP\n"
        "2. Clic droit sur Installer-MyProd-Widget.command → Ouvrir\n"
        "3. Confirmez l'ouverture si macOS demande\n"
        "4. Le widget se lance automatiquement\n\n"
        "PRÉREQUIS\n"
        "---------\n"
        "• macOS 10.15+  •  Connexion internet (~50 Mo)  •  Node.js (téléchargé auto si absent)\n"
    )


def _readme_win() -> str:
    return (
        "=== MyProd Widget - Installation Windows (version legacy) ===\n\n"
        "NOTE : Cette version nécessite Node.js. Pour une installation en un clic\n"
        "       (sans Node.js), demandez à l'administrateur de compiler les installateurs natifs.\n\n"
        "INSTALLATION\n"
        "------------\n"
        "1. Décompressez ce ZIP\n"
        "2. Installez Node.js depuis https://nodejs.org si ce n'est pas déjà fait\n"
        "3. Double-cliquez sur Installer-MyProd-Widget.bat\n"
        "4. Si SmartScreen bloque : Plus d'infos → Exécuter quand même\n\n"
        "PRÉREQUIS\n"
        "---------\n"
        "• Windows 10+  •  Node.js installé  •  Connexion internet (~20 Mo)\n"
    )
