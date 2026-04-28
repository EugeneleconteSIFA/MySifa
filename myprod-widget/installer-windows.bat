@echo off
:: MyProd Widget Launcher pour Windows
:: Double-cliquez pour lancer l'installation

title MyProd Widget Installer
echo ========================================
echo   MyProd Widget - Installation
echo ========================================
echo.

:: Vérifier PowerShell
where powershell >nul 2>&1
if errorlevel 1 (
    echo ERREUR: PowerShell n'est pas disponible.
    echo Veuillez installer Windows PowerShell ou utiliser une version plus recente de Windows.
    pause
    exit /b 1
)

:: Lancer le script PowerShell
echo Lancement de l'installation...
echo.
powershell -ExecutionPolicy Bypass -File "%~dp0installer-windows.ps1"

if errorlevel 1 (
    echo.
    echo Une erreur s'est produite. Essayez de:
    echo 1. Cliquer droit sur ce fichier -^> "Executer en tant qu'administrateur"
    echo 2. Ou installer Node.js manuellement depuis nodejs.org
    pause
)
