"""MyProd Widget — routes /widget, /install/widget, /download/widget-mac et /download/widget-win

Stratégie de distribution (deux modes, automatique) :
  - Mode natif  : si myprod-widget/dist/ contient un DMG ou EXE compilé par electron-builder,
                  le serveur le sert directement (installation en un double-clic, ~130 Mo).
  - Mode legacy : si aucun binaire n'est présent, le serveur génère un ZIP des sources +
                  script d'installation automatique (télécharge Node.js, lance npm install).
  Pour passer en mode natif : voir myprod-widget/BUILD.md.
"""

import os
import glob as _glob
from fastapi import APIRouter, Request, Query
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


def _native_mac_arm64() -> str | None:
    return _find_latest("*arm64*.dmg")


def _native_mac_x64() -> str | None:
    return _find_latest("*x64*.dmg") or _find_latest("*x86_64*.dmg")


def _native_mac_any() -> str | None:
    return _native_mac_arm64() or _native_mac_x64() or _find_latest("*.dmg")


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
    dmg_any = _native_mac_any()
    dmg_arm = _native_mac_arm64()
    dmg_x64 = _native_mac_x64()
    exe = _native_win()

    if dmg_any or exe:
        mode = (
            "<div class=\"mode-banner\">"
            "<strong>Mode natif</strong> — installateurs autonomes disponibles."
            "</div>"
        )
    else:
        mode = (
            "<div class=\"mode-banner\">"
            "<strong>Mode legacy</strong> — installateurs natifs indisponibles."
            "<br>Le téléchargement fournit un <strong>ZIP</strong> contenant les sources + un script d'installation."
            "<br><em>Node.js requis</em>."
            "<br>Compilation : <code>cd myprod-widget && npm install && npm run build:mac</code> (voir <strong>BUILD.md</strong>)."
            "</div>"
        )

    if dmg_any:
        if dmg_arm and dmg_x64:
            mac_desc = "Installateur DMG — choisir la version de votre Mac"
            mac_cta = (
                "<a class=\"option-cta\" href=\"/download/widget-mac?arch=arm64\">Télécharger (Apple Silicon)</a>"
                "<a class=\"option-cta alt\" href=\"/download/widget-mac?arch=x64\">Télécharger (Intel)</a>"
            )
        elif dmg_arm:
            mac_desc = "Installateur DMG (Apple Silicon) — glisser vers Applications"
            mac_cta = "<a class=\"option-cta\" href=\"/download/widget-mac?arch=arm64\">Télécharger</a>"
        elif dmg_x64:
            mac_desc = "Installateur DMG (Intel) — glisser vers Applications"
            mac_cta = "<a class=\"option-cta\" href=\"/download/widget-mac?arch=x64\">Télécharger</a>"
        else:
            mac_desc = "Installateur DMG — glisser vers Applications"
            mac_cta = "<a class=\"option-cta\" href=\"/download/widget-mac\">Télécharger</a>"
    else:
        mac_desc = "Installateur indisponible — compilation DMG requise"
        mac_cta = "<span class=\"option-cta alt\" style=\"cursor:default;opacity:.7\">Indisponible</span>"

    win_desc = (
        "Installateur EXE (assistant)"
        if exe
        else "ZIP + script d'installation<br><em>Node.js requis</em>"
    )
    if exe:
        win_cta = "<a class=\"option-cta\" href=\"/download/widget-win\">Télécharger</a>"
    else:
        win_cta = "<a class=\"option-cta\" href=\"/download/widget-win\">Télécharger (legacy)</a>"

    html = (
        WIDGET_INSTALL_HTML.replace("__MODE_BANNER__", mode)
        .replace("__MAC_DESC__", mac_desc)
        .replace("__WIN_DESC__", win_desc)
        .replace("__MAC_CTA__", mac_cta)
        .replace("__WIN_CTA__", win_cta)
    )
    return HTMLResponse(content=html, status_code=200)


@router.get("/download/widget-mac")
def download_widget_mac(request: Request, arch: str | None = Query(None)):
    """
    Télécharge l'installateur macOS.
    • Mode natif  : DMG electron-builder (si présent dans dist/)
    """
    require_admin(request)

    dmg: str | None = None
    if arch:
        a = arch.strip().lower()
        if a in ("arm64", "apple", "silicon"):
            dmg = _native_mac_arm64()
        elif a in ("x64", "intel", "x86_64"):
            dmg = _native_mac_x64()
    if not dmg:
        dmg = _native_mac_any()
    if dmg:
        filename = os.path.basename(dmg)
        return FileResponse(
            path=dmg,
            media_type="application/octet-stream",
            filename=filename,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # Pas de fallback ZIP sur macOS : Gatekeeper bloque les scripts .command chez les utilisateurs.
    return HTMLResponse(
        content=(
            "<!doctype html><meta charset='utf-8'>"
            "<title>MyProd Widget — installateur indisponible</title>"
            "<div style='font-family:system-ui,-apple-system,Segoe UI,sans-serif;padding:24px;max-width:760px'>"
            "<h2 style='margin:0 0 10px'>Installateur macOS indisponible</h2>"
            "<p>Le serveur ne trouve aucun fichier <strong>.dmg</strong> dans <code>myprod-widget/dist/</code>.</p>"
            "<p>Action admin (sur un Mac) :</p>"
            "<pre style='background:#111827;color:#e2e8f0;padding:12px;border-radius:10px;overflow:auto'>"
            "cd myprod-widget\\nnpm install\\nnpm run build:mac\\n</pre>"
            "<p>Puis copier le DMG généré dans <code>myprod-widget/dist/</code> sur le serveur.</p>"
            "</div>"
        ),
        status_code=503,
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

import io
import zipfile


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

        # Windows only for now (macOS: no ZIP fallback)
        installer = _build_win_installer()
        zf.writestr("Installer-MyProd-Widget.bat", installer.encode("utf-8"))
        zf.writestr("LISEZ-MOI.txt", _readme_win().encode("utf-8"))

    buf.seek(0)
    return buf


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
