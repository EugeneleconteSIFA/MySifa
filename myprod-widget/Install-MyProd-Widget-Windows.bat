@echo off
chcp 65001 >nul
:: ============================================
:: MyProd Widget Installer pour Windows
:: Double-cliquez ce fichier pour installer
:: ============================================

title MyProd Widget - Installation
echo.
echo ============================================
echo   MyProd Widget - Installation
echo ============================================
echo.

:: Vérifier PowerShell
where powershell >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] PowerShell n'est pas disponible.
    echo Veuillez installer Windows PowerShell.
    pause
    exit /b 1
)

:: Créer le script PowerShell temporaire
set "PS_SCRIPT=%TEMP%\myprod-widget-install.ps1"

echo # MyProd Widget Installer - PowerShell > "%PS_SCRIPT%"
echo $nodeVersion = "20.11.0" >> "%PS_SCRIPT%"
echo $nodeInstaller = "node-v$nodeVersion-x64.msi" >> "%PS_SCRIPT%"
echo $nodeUrl = "https://nodejs.org/dist/v$nodeVersion/$nodeInstaller" >> "%PS_SCRIPT%"
echo $downloadPath = "$env:TEMP\$nodeInstaller" >> "%PS_SCRIPT%"
echo $widgetDir = "$env:USERPROFILE\Desktop\MyProd-Widget" >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo # Fonction pour messages >> "%PS_SCRIPT%"
echo function Msg($m) { Write-Host "[$([datetime]::now.ToString('HH:mm:ss'))] $m" -ForegroundColor Cyan } >> "%PS_SCRIPT%"
echo function Err($m) { Write-Host "[ERREUR] $m" -ForegroundColor Red } >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo Msg "Verification de Node.js..." >> "%PS_SCRIPT%"
echo try { >> "%PS_SCRIPT%"
echo     $nodeV = node --version 2^>$null >> "%PS_SCRIPT%"
echo     if ($nodeV) { >> "%PS_SCRIPT%"
echo         Msg "Node.js deja installe : $nodeV" >> "%PS_SCRIPT%"
echo         $installNode = $false >> "%PS_SCRIPT%"
echo     } else { $installNode = $true } >> "%PS_SCRIPT%"
echo } catch { $installNode = $true } >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo if ($installNode) { >> "%PS_SCRIPT%"
echo     Msg "Telechargement de Node.js... (~80 Mo)" >> "%PS_SCRIPT%"
echo     try { >> "%PS_SCRIPT%"
echo         Invoke-WebRequest -Uri $nodeUrl -OutFile $downloadPath -UseBasicParsing -TimeoutSec 300 >> "%PS_SCRIPT%"
echo         Msg "Telechargement termine" >> "%PS_SCRIPT%"
echo     } catch { >> "%PS_SCRIPT%"
echo         Err "Impossible de telecharger Node.js : $_" >> "%PS_SCRIPT%"
echo         pause >> "%PS_SCRIPT%"
echo         exit 1 >> "%PS_SCRIPT%"
echo     } >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo     Msg "Installation de Node.js... (cliquez Oui si Windows demande)" >> "%PS_SCRIPT%"
echo     Start-Process msiexec.exe -ArgumentList "/i `"$downloadPath`" /qn /norestart" -Wait -Verb RunAs >> "%PS_SCRIPT%"
echo     if ($LASTEXITCODE -ne 0) { >> "%PS_SCRIPT%"
echo         Err "L'installation de Node.js a echoue. Code: $LASTEXITCODE" >> "%PS_SCRIPT%"
echo         pause >> "%PS_SCRIPT%"
echo         exit 1 >> "%PS_SCRIPT%"
echo     } >> "%PS_SCRIPT%"
echo     Remove-Item $downloadPath -Force -ErrorAction SilentlyContinue >> "%PS_SCRIPT%"
echo     Msg "Node.js installe avec succes !" >> "%PS_SCRIPT%"
echo } >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo # Verifier que node est disponible >> "%PS_SCRIPT%"
echo if (!(Get-Command node -ErrorAction SilentlyContinue)) { >> "%PS_SCRIPT%"
echo     Err "Node.js n'est pas trouve apres l'installation" >> "%PS_SCRIPT%"
echo     pause >> "%PS_SCRIPT%"
echo     exit 1 >> "%PS_SCRIPT%"
echo } >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo Msg "Installation de MyProd Widget..." >> "%PS_SCRIPT%"
echo New-Item -ItemType Directory -Force -Path $widgetDir ^| Out-Null >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo # Creer le script de lancement >> "%PS_SCRIPT%"
echo $launchBat = @' >> "%PS_SCRIPT%"
echo @echo off >> "%PS_SCRIPT%"
echo cd /d "%%USERPROFILE%%\Desktop\MyProd-Widget\myprod-widget" >> "%PS_SCRIPT%"
echo if not exist "node_modules\" ( >> "%PS_SCRIPT%"
echo     echo Installation des dependances... >> "%PS_SCRIPT%"
echo     npm install --silent >> "%PS_SCRIPT%"
echo ) >> "%PS_SCRIPT%"
echo npm start >> "%PS_SCRIPT%"
echo '@ >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo $launchPath = "$widgetDir\Lancer-Widget.bat" >> "%PS_SCRIPT%"
echo $launchBat ^| Out-File -FilePath $launchPath -Encoding ASCII >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo # Creer le raccourci bureau >> "%PS_SCRIPT%"
echo $WshShell = New-Object -comObject WScript.Shell >> "%PS_SCRIPT%"
echo $DesktopShortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\MyProd-Widget.lnk") >> "%PS_SCRIPT%"
echo $DesktopShortcut.TargetPath = $launchPath >> "%PS_SCRIPT%"
echo $DesktopShortcut.WorkingDirectory = "$widgetDir\myprod-widget" >> "%PS_SCRIPT%"
echo $DesktopShortcut.IconLocation = "shell32.dll,21" >> "%PS_SCRIPT%"
echo $DesktopShortcut.Save() >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo Msg "Installation terminee !" >> "%PS_SCRIPT%"
echo Write-Host "" >> "%PS_SCRIPT%"
echo Write-Host "MyProd Widget est installe sur votre bureau." -ForegroundColor Green >> "%PS_SCRIPT%"
echo Write-Host "Double-cliquez sur 'MyProd-Widget' pour lancer." -ForegroundColor Yellow >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo $response = Read-Host "Voulez-vous lancer le widget maintenant ? (O/N)" >> "%PS_SCRIPT%"
echo if ($response -eq "O" -or $response -eq "o") { >> "%PS_SCRIPT%"
echo     Start-Process $launchPath >> "%PS_SCRIPT%"
echo } >> "%PS_SCRIPT%"

:: Exécuter le script PowerShell avec bypass de la politique d'exécution
echo.
echo Lancement de l'installation...
echo.
powershell -ExecutionPolicy Bypass -File "%PS_SCRIPT%"

:: Nettoyer
if exist "%PS_SCRIPT%" del "%PS_SCRIPT%"

echo.
echo ============================================
echo Installation terminee.
echo ============================================
echo.
pause
