"""MyProd Widget — routes /widget, /install/widget, /download/widget-mac et /download/widget-win"""

import io
import os
import zipfile
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from services.auth_service import get_current_user, require_admin
from app.web.widget_page import WIDGET_HTML
from app.web.widget_install_page import WIDGET_INSTALL_HTML

router = APIRouter()

# Dossier Electron à zipper
_WIDGET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "myprod-widget")
_SERVER_URL  = "https://www.mysifa.com"


@router.get("/widget", response_class=HTMLResponse)
def widget_page(request: Request):
    """Page widget autonome — chargée par l'app Electron MyProd."""
    # Auth légère : si non connecté, la page JS affiche le message "non connecté"
    # et propose le lien de login. On sert le HTML dans tous les cas.
    return HTMLResponse(content=WIDGET_HTML, status_code=200)


@router.get("/install/widget", response_class=HTMLResponse)
def install_widget_page(request: Request):
    """Page de choix Mac/Windows pour l'installation du widget."""
    require_admin(request)
    return HTMLResponse(content=WIDGET_INSTALL_HTML, status_code=200)


def _read_installer_file(filename: str) -> str:
    """Lit un fichier d'installateur depuis le dossier myprod-widget."""
    fpath = os.path.join(_WIDGET_DIR, filename)
    if not os.path.isfile(fpath):
        return ""
    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

def _read_installer_bytes(filename: str) -> bytes:
    """Lit un fichier binaire depuis le dossier myprod-widget."""
    fpath = os.path.join(_WIDGET_DIR, filename)
    if not os.path.isfile(fpath):
        return b""
    with open(fpath, "rb") as f:
        return f.read()


def _create_widget_zip(platform: str) -> io.BytesIO:
    """Crée le ZIP du widget avec les installateurs appropriés."""
    buf = io.BytesIO()
    
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Fichiers du dossier myprod-widget (sources)
        skip = {"node_modules", "dist", ".git", "__pycache__", 
                "installer-mac.applescript", "installer-windows.ps1", "installer-windows.bat",
                "Installer-MyProd-Widget.command", "Lancer-Widget.sh",
                "Install-MyProd-Widget-Mac.command", "Install-MyProd-Widget-Windows.bat"}
        
        if os.path.isdir(_WIDGET_DIR):
            for fname in os.listdir(_WIDGET_DIR):
                if fname in skip or fname.startswith("."):
                    continue
                fpath = os.path.join(_WIDGET_DIR, fname)
                if not os.path.isfile(fpath):
                    continue
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                # Injecter l'URL du serveur
                content = content.replace("http://localhost:8000", _SERVER_URL)
                content = content.replace("https://www.mysifa.com", _SERVER_URL)
                zf.writestr(f"myprod-widget/{fname}", content.encode("utf-8"))
        
        if platform == "mac":
            # Ajouter le nouvel installateur Mac (.command exécutable)
            installer_mac = _read_installer_bytes("Install-MyProd-Widget-Mac.command")
            if installer_mac:
                # Écrire avec permissions exécutables (mode 755)
                info = zipfile.ZipInfo("Installer-MyProd-Widget.command")
                info.external_attr = (0o755 << 16)  # Permissions Unix exécutables
                zf.writestr(info, installer_mac)
            
            readme_mac = (
                "=== MyProd Widget - Installation macOS ===\n\n"
                "SI GATEKEEPER BLOQUE (\"Apple cannot verify...\")\n"
                "--------------------------------------------------\n\n"
                "Methode 1 - Clic droit (recommandee):\n"
                "1. Clic droit sur Installer-MyProd-Widget.command\n"
                "2. Selectionnez 'Ouvrir' (pas double-clic)\n"
                "3. Cliquez sur 'Ouvrir' dans la fenetre d'alerte\n\n"
                "Methode 2 - Terminal:\n"
                "1. Ouvrez Terminal\n"
                "2. Tapez: xattr -c ~/Downloads/Installer-MyProd-Widget.command\n"
                "3. Double-cliquez ensuite sur le fichier\n\n"
                "ETAPE D'INSTALLATION\n"
                "--------------------\n"
                "1. Decompressez le ZIP\n"
                "2. Ouvrez Installer-MyProd-Widget.command (voir ci-dessus si bloque)\n"
                "3. Cliquez sur 'Installer'\n"
                "4. Patientez pendant le telechargement de Node.js\n"
                "5. Le widget se lance automatiquement\n\n"
                "PREREQUIS\n"
                "---------\n"
                "• macOS 10.15+\n"
                "• Connexion internet (80 Mo)\n"
                "• Droits administrateur\n\n"
                "MANUEL (si automatique echoue)\n"
                "-------------------------------\n"
                "1. https://nodejs.org - telechargez Node.js LTS\n"
                "2. Installez Node.js\n"
                "3. Dans myprod-widget, tapez: npm install && npm start\n"
            )
            zf.writestr("LISEZ-MOI.txt", readme_mac.encode("utf-8"))
            
        elif platform == "win":
            # Ajouter le nouvel installateur Windows (.bat)
            installer_win = _read_installer_bytes("Install-MyProd-Widget-Windows.bat")
            if installer_win:
                zf.writestr("Installer-MyProd-Widget.bat", installer_win)
            
            readme_win = (
                "=== MyProd Widget - Installation Windows ===\n\n"
                "ETAPE D'INSTALLATION\n"
                "--------------------\n"
                "1. Decompressez le ZIP\n"
                "2. Double-cliquez sur Installer-MyProd-Widget.bat\n"
                "3. Si SmartScreen bloque: Plus d'infos -> Executer quand meme\n"
                "4. Patientez pendant le telechargement de Node.js\n"
                "5. Le widget se lance automatiquement\n\n"
                "PREREQUIS\n"
                "---------\n"
                "• Windows 10+\n"
                "• PowerShell 5.1+\n"
                "• Connexion internet (80 Mo)\n"
                "• Droits administrateur\n\n"
                "MANUEL (si automatique echoue)\n"
                "-------------------------------\n"
                "1. https://nodejs.org - telechargez Node.js LTS\n"
                "2. Installez Node.js\n"
                "3. Dans myprod-widget, double-cliquez sur start.bat\n"
            )
            zf.writestr("LISEZ-MOI.txt", readme_win.encode("utf-8"))
    
    buf.seek(0)
    return buf


@router.get("/download/widget-mac")
def download_widget_mac(request: Request):
    """
    Télécharge le ZIP d'installation pour macOS.
    Contient l'installateur automatique + les sources du widget.
    """
    require_admin(request)
    buf = _create_widget_zip("mac")
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="myprod-widget-macos.zip"'},
    )


@router.get("/download/widget-win")
def download_widget_win(request: Request):
    """
    Télécharge le ZIP d'installation pour Windows.
    Contient l'installateur automatique + les sources du widget.
    """
    require_admin(request)
    buf = _create_widget_zip("win")
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="myprod-widget-windows.zip"'},
    )


@router.get("/download/widget")
def download_widget_legacy(request: Request):
    """
    Téléchargement legacy - redirige vers la page de choix.
    """
    require_admin(request)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/install/widget", status_code=302)
