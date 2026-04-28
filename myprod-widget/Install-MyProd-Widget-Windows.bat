@echo off
:: ============================================
:: MyProd Widget Installer for Windows
:: Double-click this file to install
:: ============================================

title MyProd Widget - Installation
echo.
echo ============================================
echo   MyProd Widget - Installation
echo ============================================
echo.

:: Check PowerShell
where powershell >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PowerShell is not available.
    echo Please install Windows PowerShell.
    pause
    exit /b 1
)

:: Create temp PowerShell script
set "PS_SCRIPT=%TEMP%\myprod-widget-install.ps1"

:: Write PowerShell script (using ASCII characters only)
echo # MyProd Widget Installer > "%PS_SCRIPT%"
echo $nodeVersion = "20.11.0" >> "%PS_SCRIPT%"
echo $nodeInstaller = "node-v$nodeVersion-x64.msi" >> "%PS_SCRIPT%"
echo $nodeUrl = "https://nodejs.org/dist/v$nodeVersion/$nodeInstaller" >> "%PS_SCRIPT%"
echo $downloadPath = "$env:TEMP\$nodeInstaller" >> "%PS_SCRIPT%"
echo $widgetDir = "$env:USERPROFILE\Desktop\MyProd-Widget" >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo function Msg($m) { Write-Host "[$([datetime]::now.ToString('HH:mm:ss'))] $m" -ForegroundColor Cyan } >> "%PS_SCRIPT%"
echo function Err($m) { Write-Host "[ERROR] $m" -ForegroundColor Red } >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo Msg "Checking Node.js..." >> "%PS_SCRIPT%"
echo try { >> "%PS_SCRIPT%"
echo     $nodeV = node --version 2^>$null >> "%PS_SCRIPT%"
echo     if ($nodeV) { >> "%PS_SCRIPT%"
echo         Msg "Node.js already installed: $nodeV" >> "%PS_SCRIPT%"
echo         $installNode = $false >> "%PS_SCRIPT%"
echo     } else { $installNode = $true } >> "%PS_SCRIPT%"
echo } catch { $installNode = $true } >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo if ($installNode) { >> "%PS_SCRIPT%"
echo     Msg "Downloading Node.js... (~80 MB)" >> "%PS_SCRIPT%"
echo     try { >> "%PS_SCRIPT%"
echo         Invoke-WebRequest -Uri $nodeUrl -OutFile $downloadPath -UseBasicParsing -TimeoutSec 300 >> "%PS_SCRIPT%"
echo         Msg "Download complete" >> "%PS_SCRIPT%"
echo     } catch { >> "%PS_SCRIPT%"
echo         Err "Failed to download Node.js: $_" >> "%PS_SCRIPT%"
echo         pause >> "%PS_SCRIPT%"
echo         exit 1 >> "%PS_SCRIPT%"
echo     } >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo     Msg "Installing Node.js... (click Yes if Windows asks)" >> "%PS_SCRIPT%"
echo     Start-Process msiexec.exe -ArgumentList "/i `"$downloadPath`" /qn /norestart" -Wait -Verb RunAs >> "%PS_SCRIPT%"
echo     if ($LASTEXITCODE -ne 0) { >> "%PS_SCRIPT%"
echo         Err "Node.js installation failed. Code: $LASTEXITCODE" >> "%PS_SCRIPT%"
echo         pause >> "%PS_SCRIPT%"
echo         exit 1 >> "%PS_SCRIPT%"
echo     } >> "%PS_SCRIPT%"
echo     Remove-Item $downloadPath -Force -ErrorAction SilentlyContinue >> "%PS_SCRIPT%"
echo     Msg "Node.js installed successfully!" >> "%PS_SCRIPT%"
echo } >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo if (!(Get-Command node -ErrorAction SilentlyContinue)) { >> "%PS_SCRIPT%"
echo     Err "Node.js not found after installation" >> "%PS_SCRIPT%"
echo     pause >> "%PS_SCRIPT%"
echo     exit 1 >> "%PS_SCRIPT%"
echo } >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo Msg "Installing MyProd Widget..." >> "%PS_SCRIPT%"
echo New-Item -ItemType Directory -Force -Path $widgetDir ^| Out-Null >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo # Copy widget source files from installer location >> "%PS_SCRIPT%"
echo $sourceDir = Split-Path -Parent $PSCommandPath >> "%PS_SCRIPT%"
echo $sourceWidgetDir = Join-Path $sourceDir "myprod-widget" >> "%PS_SCRIPT%"
echo if (Test-Path $sourceWidgetDir) { >> "%PS_SCRIPT%"
echo     Msg "Copying widget files..." >> "%PS_SCRIPT%"
echo     Copy-Item -Path $sourceWidgetDir -Destination $widgetDir -Recurse -Force ^| Out-Null >> "%PS_SCRIPT%"
echo } else { >> "%PS_SCRIPT%"
echo     Err "Source folder not found: $sourceWidgetDir" >> "%PS_SCRIPT%"
echo     Err "Please make sure the myprod-widget folder is in the same directory as this installer" >> "%PS_SCRIPT%"
echo     pause >> "%PS_SCRIPT%"
echo     exit 1 >> "%PS_SCRIPT%"
echo } >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo $launchBat = @' >> "%PS_SCRIPT%"
echo @echo off >> "%PS_SCRIPT%"
echo set "SCRIPTDIR=%%~dp0" >> "%PS_SCRIPT%"
echo cd /d "%%SCRIPTDIR%%myprod-widget" >> "%PS_SCRIPT%"
echo if not exist "node_modules\" ( >> "%PS_SCRIPT%"
echo     echo Installing dependencies... >> "%PS_SCRIPT%"
echo     npm install --silent >> "%PS_SCRIPT%"
echo     if errorlevel 1 ( >> "%PS_SCRIPT%"
echo         echo ERROR: npm install failed >> "%PS_SCRIPT%"
echo         pause >> "%PS_SCRIPT%"
echo         exit /b 1 >> "%PS_SCRIPT%"
echo     ) >> "%PS_SCRIPT%"
echo ) >> "%PS_SCRIPT%"
echo npm start >> "%PS_SCRIPT%"
echo if errorlevel 1 pause >> "%PS_SCRIPT%"
echo '@ >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo $launchPath = "$widgetDir\Lancer-Widget.bat" >> "%PS_SCRIPT%"
echo $launchBat ^| Out-File -FilePath $launchPath -Encoding ASCII >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo $WshShell = New-Object -comObject WScript.Shell >> "%PS_SCRIPT%"
echo $DesktopShortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\MyProd-Widget.lnk") >> "%PS_SCRIPT%"
echo $DesktopShortcut.TargetPath = $launchPath >> "%PS_SCRIPT%"
echo $DesktopShortcut.WorkingDirectory = $widgetDir >> "%PS_SCRIPT%"
echo $DesktopShortcut.IconLocation = "shell32.dll,21" >> "%PS_SCRIPT%"
echo $DesktopShortcut.Save() >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo Msg "Installation complete!" >> "%PS_SCRIPT%"
echo Write-Host "" >> "%PS_SCRIPT%"
echo Write-Host "MyProd Widget is installed on your desktop." -ForegroundColor Green >> "%PS_SCRIPT%"
echo Write-Host "Double-click 'MyProd-Widget' to launch." -ForegroundColor Yellow >> "%PS_SCRIPT%"
echo. >> "%PS_SCRIPT%"
echo $response = Read-Host "Launch widget now? (Y/N)" >> "%PS_SCRIPT%"
echo if ($response -eq "Y" -or $response -eq "y") { >> "%PS_SCRIPT%"
echo     Start-Process $launchPath >> "%PS_SCRIPT%"
echo } >> "%PS_SCRIPT%"

:: Run PowerShell script
echo.
echo Starting installation...
echo.
powershell -ExecutionPolicy Bypass -File "%PS_SCRIPT%"

:: Cleanup
if exist "%PS_SCRIPT%" del "%PS_SCRIPT%"

echo.
echo ============================================
echo Installation finished.
echo ============================================
echo.
pause
