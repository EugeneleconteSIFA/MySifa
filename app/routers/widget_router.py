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


def _create_widget_zip(platform: str) -> io.BytesIO:
    """Crée le ZIP du widget avec les installateurs appropriés."""
    buf = io.BytesIO()
    
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Fichiers du dossier myprod-widget (sources)
        skip = {"node_modules", "dist", ".git", "__pycache__", 
                "installer-mac.applescript", "installer-windows.ps1", "installer-windows.bat",
                "Installer-MyProd-Widget.command", "Lancer-Widget.sh"}
        
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
            # Ajouter l'installateur Mac
            installer_mac = _read_installer_file("installer-mac.applescript")
            if installer_mac:
                zf.writestr("Installer-MyProd-Widget.applescript", installer_mac.encode("utf-8"))
            
            readme_mac = (
                "=== MyProd Widget - Installation macOS ===\n\n"
                "ÉTAPES D'INSTALLATION AUTOMATIQUE\n"
                "-----------------------------------\n\n"
                "1. Double-cliquez sur \"Installer-MyProd-Widget.applescript\"\n"
                "2. Cliquez sur \"Installer\" dans la fenêtre de dialogue\n"
                "3. Patientez pendant le téléchargement et l'installation de Node.js\n"
                "4. Le widget se lance automatiquement à la fin\n\n"
                "PRÉREQUIS\n"
                "---------\n"
                "• macOS 10.15 ou plus récent\n"
                "• Connexion internet (80 Mo)\n"
                "• Droits administrateur\n\n"
                "MANUEL (si l'automatique échoue)\n"
                "---------------------------------\n"
                "1. Allez sur https://nodejs.org et téléchargez la version LTS\n"
                "2. Installez Node.js\n"
                "3. Dans le dossier myprod-widget, ouvrez un terminal\n"
                "4. Tapez: npm install && npm start\n\n"
                "LANCEMENT ULTÉRIEUR\n"
                "-------------------\n"
                "Un raccourci est créé sur le bureau et dans le Dock.\n"
            )
            zf.writestr("LISEZ-MOI-macOS.txt", readme_mac.encode("utf-8"))
            
        elif platform == "win":
            # Ajouter l'installateur Windows
            installer_ps1 = _read_installer_file("installer-windows.ps1")
            installer_bat = _read_installer_file("installer-windows.bat")
            if installer_ps1:
                zf.writestr("Installer-MyProd-Widget.ps1", installer_ps1.encode("utf-8"))
            if installer_bat:
                zf.writestr("Installer-MyProd-Widget.bat", installer_bat.encode("utf-8"))
            
            readme_win = (
                "=== MyProd Widget - Installation Windows ===\n\n"
                "ÉTAPES D'INSTALLATION AUTOMATIQUE\n"
                "-----------------------------------\n\n"
                "1. Faites un clic droit sur \"Installer-MyProd-Widget.bat\"\n"
                "2. Sélectionnez \"Exécuter avec PowerShell\" ou \"Exécuter en tant qu'administrateur\"\n"
                "3. Cliquez sur \"Oui\" pour autoriser l'installation\n"
                "4. Patientez pendant le téléchargement et l'installation de Node.js\n"
                "5. Le widget se lance automatiquement à la fin\n\n"
                "PRÉREQUIS\n"
                "---------\n"
                "• Windows 10 ou plus récent\n"
                "• PowerShell 5.1 ou plus récent\n"
                "• Connexion internet (80 Mo)\n"
                "• Droits administrateur\n\n"
                "MANUEL (si l'automatique échoue)\n"
                "---------------------------------\n"
                "1. Allez sur https://nodejs.org et téléchargez la version LTS\n"
                "2. Installez Node.js\n"
                "3. Dans le dossier myprod-widget, double-cliquez sur start.bat\n\n"
                "LANCEMENT ULTÉRIEUR\n"
                "-------------------\n"
                "Un raccourci est créé sur le bureau et dans le Menu Démarrer.\n"
            )
            zf.writestr("LISEZ-MOI-Windows.txt", readme_win.encode("utf-8"))
    
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
