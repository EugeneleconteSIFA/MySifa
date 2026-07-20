<#
.SYNOPSIS
  Installe l'agent MySifa Print sur un PC Windows h�te (celui qui a l'imprimante branch�e en USB / LPT / r�seau).

.DESCRIPTION
  1. V�rifie / installe Python 3.8 (compatible Windows 7+)
  2. Installe pywin32 (indispensable pour piloter les queues Windows locales)
  3. D�pose print_agent.py + agent_config.yaml (avec le token) dans C:\mysifa-print-agent\
  4. T�l�charge NSSM et installe le service Windows MysifaPrintAgent
  5. D�marre le service et v�rifie qu'il tourne

.PARAMETER Token
  Le token de l'agent, r�cup�r� dans MySifa (/settings > Imprimantes > Agents locaux > Nouvel agent).
  Chaque PC h�te doit avoir SON PROPRE agent + SON PROPRE token.

.PARAMETER ServerUrl
  URL du VPS MySifa. D�faut : https://www.mysifa.com

.PARAMETER InstallDir
  Dossier d'install. D�faut : C:\mysifa-print-agent

.EXAMPLE
  # Lancement typique, en admin :
  powershell -ExecutionPolicy Bypass -File .\install_agent_windows.ps1 -Token "abcd1234..."

.NOTES
  � lancer en tant qu'Administrateur (clic droit > Ex�cuter en tant qu'admin).
  Testé sur Windows 7 SP1 (32/64), Windows 10, Windows 11.
#>

param(
  [Parameter(Mandatory=$true)]
  [string]$Token,

  [string]$ServerUrl = "https://www.mysifa.com",
  [string]$InstallDir = "C:\mysifa-print-agent",
  [string]$PythonVersion = "3.8.10"
)

$ErrorActionPreference = "Stop"

function Write-Section($msg) {
  Write-Host ""
  Write-Host "============================================================" -ForegroundColor Cyan
  Write-Host " $msg" -ForegroundColor Cyan
  Write-Host "============================================================" -ForegroundColor Cyan
}

function Test-Admin {
  $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin)) {
  Write-Host "[ERREUR] Ce script doit être lancé en Administrateur." -ForegroundColor Red
  Write-Host "         Clic droit sur PowerShell > Exécuter en tant qu'administrateur." -ForegroundColor Red
  exit 1
}

# ─── 1. Vérifier / installer Python ─────────────────────────────────
Write-Section "1. Python 3.8"
$pythonExe = $null
try {
  $out = (& python --version 2>&1)
  if ($out -match "Python 3\.[89]|Python 3\.1[0-9]") {
    $pythonExe = (Get-Command python).Source
    Write-Host "  Python déjà installé : $out ($pythonExe)" -ForegroundColor Green
  }
} catch { }

if (-not $pythonExe) {
  $arch = if ([Environment]::Is64BitOperatingSystem) { "amd64" } else { "" }
  $suffix = if ($arch) { "-$arch" } else { "" }
  $url = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion$suffix.exe"
  $installer = Join-Path $env:TEMP "python-$PythonVersion.exe"
  Write-Host "  Téléchargement Python $PythonVersion depuis $url ..."
  Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
  Write-Host "  Installation silencieuse (Add to PATH activé) ..."
  Start-Process -FilePath $installer -ArgumentList "/quiet","InstallAllUsers=1","PrependPath=1","Include_test=0" -Wait
  # Actualise le PATH pour cette session
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
  $pythonExe = (Get-Command python).Source
  Write-Host "  Python installé : $pythonExe" -ForegroundColor Green
}

# ─── 2. pywin32 ─────────────────────────────────────────────────────
Write-Section "2. pywin32 (accès aux imprimantes Windows)"
& $pythonExe -m pip install --upgrade pip --quiet
& $pythonExe -m pip install pywin32 --quiet
Write-Host "  pywin32 installé." -ForegroundColor Green

# ─── 3. Dossier d'install + fichiers ────────────────────────────────
Write-Section "3. Fichiers de l'agent"
if (-not (Test-Path $InstallDir)) { New-Item -ItemType Directory -Path $InstallDir | Out-Null }
if (-not (Test-Path (Join-Path $InstallDir "logs"))) {
  New-Item -ItemType Directory -Path (Join-Path $InstallDir "logs") | Out-Null
}

# print_agent.py — copié depuis le même dossier que ce script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$srcAgent = Join-Path $scriptDir "print_agent.py"
if (-not (Test-Path $srcAgent)) {
  Write-Host "[ERREUR] print_agent.py introuvable à côté de ce script ($srcAgent)." -ForegroundColor Red
  Write-Host "         Copie print_agent.py dans le même dossier que install_agent_windows.ps1 et relance." -ForegroundColor Red
  exit 1
}
Copy-Item $srcAgent (Join-Path $InstallDir "print_agent.py") -Force
Write-Host "  print_agent.py copié."

# agent_config.yaml — généré à partir du token en argument
$configPath = Join-Path $InstallDir "agent_config.yaml"
$configContent = @"
# MySifa — configuration agent d'impression local (généré par install_agent_windows.ps1)

server_url: $ServerUrl
token: "$Token"

poll_interval: 2
heartbeat_interval: 30
printer_timeout: 8
log_level: INFO
"@
Set-Content -Path $configPath -Value $configContent -Encoding UTF8
Write-Host "  agent_config.yaml généré avec le token."

# ─── 4. NSSM ────────────────────────────────────────────────────────
Write-Section "4. NSSM (Non-Sucking Service Manager)"
$nssmDir = Join-Path $InstallDir "nssm"
$nssmExe = if ([Environment]::Is64BitOperatingSystem) {
  Join-Path $nssmDir "win64\nssm.exe"
} else {
  Join-Path $nssmDir "win32\nssm.exe"
}

if (-not (Test-Path $nssmExe)) {
  $nssmZip = Join-Path $env:TEMP "nssm.zip"
  Write-Host "  Téléchargement NSSM 2.24 ..."
  Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile $nssmZip -UseBasicParsing
  Write-Host "  Décompression ..."
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  if (Test-Path $nssmDir) { Remove-Item $nssmDir -Recurse -Force }
  [System.IO.Compression.ZipFile]::ExtractToDirectory($nssmZip, $InstallDir)
  # nssm-2.24 est décompressé sous $InstallDir\nssm-2.24 — on renomme en $InstallDir\nssm
  Rename-Item (Join-Path $InstallDir "nssm-2.24") $nssmDir
  Remove-Item $nssmZip -Force
}
Write-Host "  NSSM prêt : $nssmExe" -ForegroundColor Green

# ─── 5. Service Windows ─────────────────────────────────────────────
Write-Section "5. Service MysifaPrintAgent"
$svcName = "MysifaPrintAgent"

# S'il existe déjà, on le stoppe et le supprime avant de recréer proprement
$existing = Get-Service -Name $svcName -ErrorAction SilentlyContinue
if ($existing) {
  Write-Host "  Service existant détecté, remise à zéro ..."
  & $nssmExe stop $svcName 2>&1 | Out-Null
  Start-Sleep -Seconds 2
  & $nssmExe remove $svcName confirm 2>&1 | Out-Null
  Start-Sleep -Seconds 1
}

$agentPy = Join-Path $InstallDir "print_agent.py"
$logFile = Join-Path $InstallDir "logs\agent.log"

& $nssmExe install $svcName $pythonExe $agentPy | Out-Null
& $nssmExe set $svcName AppDirectory $InstallDir | Out-Null
& $nssmExe set $svcName DisplayName "MySifa Print Agent" | Out-Null
& $nssmExe set $svcName Description "Agent d'impression MySifa - poll cloud + push imprimantes locales et LAN" | Out-Null
& $nssmExe set $svcName Start SERVICE_AUTO_START | Out-Null
& $nssmExe set $svcName AppStdout $logFile | Out-Null
& $nssmExe set $svcName AppStderr $logFile | Out-Null
& $nssmExe set $svcName AppRotateFiles 1 | Out-Null
& $nssmExe set $svcName AppRotateOnline 1 | Out-Null
& $nssmExe set $svcName AppRotateBytes 5242880 | Out-Null
& $nssmExe set $svcName AppRestartDelay 3000 | Out-Null

Write-Host "  Service installé. Démarrage ..."
& $nssmExe start $svcName | Out-Null
Start-Sleep -Seconds 3

$status = (& $nssmExe status $svcName).Trim()
if ($status -match "RUNNING") {
  Write-Host "  Service en cours d'exécution ($status)." -ForegroundColor Green
} else {
  Write-Host "  [ATTENTION] Statut : $status" -ForegroundColor Yellow
  Write-Host "  Regarde le log : $logFile" -ForegroundColor Yellow
}

# ─── Bilan ──────────────────────────────────────────────────────────
Write-Section "Installation terminée"
Write-Host "  Service       : $svcName" -ForegroundColor Green
Write-Host "  Dossier       : $InstallDir" -ForegroundColor Green
Write-Host "  Log           : $logFile" -ForegroundColor Green
Write-Host "  Vérifier      : dans MySifa /settings > Imprimantes > Agents locaux" -ForegroundColor Green
Write-Host ""
Write-Host "  Prochaines étapes :" -ForegroundColor Cyan
Write-Host "  1. Dans MySifa, l'agent doit passer 'En ligne' sous 30s." -ForegroundColor Cyan
Write-Host "  2. Créer les imprimantes sur ce PC :" -ForegroundColor Cyan
Write-Host "     - Type de connexion : 'Locale (USB/LPT via PC hôte)'" -ForegroundColor Cyan
Write-Host "     - Agent local       : celui qu'on vient d'installer" -ForegroundColor Cyan
Write-Host "     - Nom queue Windows : exact nom vu dans 'Périphériques et imprimantes'" -ForegroundColor Cyan
Write-Host "  3. Bouton 'Test d'impression' à côté de l'imprimante." -ForegroundColor Cyan
Write-Host ""
Write-Host "  Logs en direct : Get-Content -Wait $logFile" -ForegroundColor Cyan
