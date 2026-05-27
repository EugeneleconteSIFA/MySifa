# Déploiement MySifa sous Windows (PowerShell)
#
# SOURCE DE VÉRITÉ : Google Drive (ce dossier)
# Miroir git       : Documents\GitHub\MySifa (push GitHub / VPS uniquement)
#
# Usage :
#   .\deploy.ps1              # sync rapide (fichiers modifiés seulement)
#   .\deploy.ps1 -Full        # miroir complet (plus lent, gère les suppressions)
#   .\deploy.ps1 -SkipSync    # push + VPS sans recopier (miroir déjà à jour)
#   .\deploy.ps1 -GitHubOnly  # push GitHub uniquement (pas de VPS)
#   .\git-push.ps1            # raccourci : sync + push GitHub (pas de VPS)
#   .\deploy.ps1 --widget

param(
    [switch]$Full,
    [switch]$SkipSync,
    [switch]$GitHubOnly,
    [Alias("m")]
    [string]$CommitMessage
)

$ErrorActionPreference = "Stop"

# Args transmis à deploy.sh (--widget, --uploads, etc.)
$deployShArgs = @()
foreach ($a in $args) {
    if ($a -notin @("-Full", "-SkipSync", "-GitHubOnly")) { $deployShArgs += $a }
}

function Find-GitBash {
    @(
        "${env:ProgramFiles}\Git\bin\bash.exe",
        "${env:ProgramFiles(x86)}\Git\bin\bash.exe"
    ) | ForEach-Object {
        if (Test-Path $_) { return $_ }
    }
    return $null
}

function Resolve-GitMirror {
    if ($env:MYSIFA_GIT_MIRROR -and (Test-Path (Join-Path $env:MYSIFA_GIT_MIRROR ".git"))) {
        return (Resolve-Path $env:MYSIFA_GIT_MIRROR).Path
    }
    $default = Join-Path $env:USERPROFILE "Documents\GitHub\MySifa"
    if (Test-Path (Join-Path $default ".git")) {
        return (Resolve-Path $default).Path
    }
    throw @"
Miroir git introuvable.
  Clone attendu : $default
  ou : `$env:MYSIFA_GIT_MIRROR = 'C:\chemin\vers\MySifa'
"@
}

function Sync-TruthToMirror {
    param(
        [string]$TruthDir,
        [string]$MirrorDir,
        [bool]$FullMirror
    )
    if ($TruthDir -eq $MirrorDir) { return }

    if (-not (Test-Path $TruthDir)) {
        throw "Source de verite introuvable : $TruthDir"
    }
    if (-not (Test-Path $MirrorDir)) {
        New-Item -ItemType Directory -Path $MirrorDir -Force | Out-Null
    }

    Write-Host ""
    if ($FullMirror) {
        Write-Host "Sync COMPLETE (miroir) - peut prendre 5-15 min sur Google Drive..."
    } else {
        Write-Host "Sync RAPIDE (fichiers modifies) - patientez 30 s a 3 min..."
    }
    Write-Host "  source de verite : $TruthDir"
    Write-Host "  miroir git       : $MirrorDir"
    Write-Host ""

    $xd = @(
        ".git", "venv", ".venv", "__pycache__", "node_modules",
        "myprod-widget\node_modules",
        "myprod-widget\dist",
        "myprod-widget\dist\win-unpacked",
        "myprod-widget\dist\mac",
        "myprod-widget\dist\mac-arm64",
        "data", ".cursor", "agent-transcripts", "terminals",
        "uploads", "_tmp_planning_v2", "app\_tmp_planning_v2", "__in"
    )
    $xf = @(
        ".DS_Store", "mysifa.db", "production.db", "Thumbs.db", "desktop.ini",
        "*.gdoc", "*.gsheet", "*.gslides",
        "*.dmg", "*.exe", "*.blockmap",
        "nohup.out", "root@*"
    )

    $roboBase = @(
        $TruthDir, $MirrorDir,
        "/MT:4", "/R:0", "/W:1",
        "/BYTES", "/TEE", "/ETA", "/NS", "/NC",
        "/XD"
    ) + $xd + @("/XF") + $xf

    if ($FullMirror) {
        $roboArgs = @($TruthDir, $MirrorDir, "/MIR") + $roboBase[2..($roboBase.Length - 1)]
    } else {
        $roboArgs = @($TruthDir, $MirrorDir, "/E", "/XO") + $roboBase[2..($roboBase.Length - 1)]
    }

    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & robocopy @roboArgs
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEap

    Write-Host ""
    if (($code -band 16) -ne 0 -or $code -ge 16) {
        throw "Robocopy erreur grave (code $code)."
    }
    if (($code -band 8) -ne 0) {
        Write-Host "Sync terminee avec avertissements (code $code : fichiers ignores, ex. .gdoc Google Drive)." -ForegroundColor Yellow
        Write-Host "Le code applicatif (app/, main.py, etc.) est copie - suite du deploy."
    } else {
        Write-Host "Sync terminee (robocopy code $code)."
    }
    if (-not $FullMirror) {
        Write-Host "Astuce : apres une suppression de fichier, lancez .\deploy.ps1 -Full une fois."
    }
}

function To-BashPath([string]$winPath) {
    $p = (Resolve-Path $winPath).Path -replace '\\', '/'
    if ($p -match '^([A-Za-z]):(.*)$') {
        return "/" + $Matches[1].ToLower() + $Matches[2]
    }
    return $p
}

function Invoke-GitInMirror {
    param(
        [string]$MirrorDir,
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$GitArgs
    )
    $prev = Get-Location
    try {
        Set-Location $MirrorDir
        & git @GitArgs
        if ($LASTEXITCODE -ne 0) {
            throw "git $($GitArgs -join ' ') a echoue (code $LASTEXITCODE)."
        }
    } finally {
        Set-Location $prev
    }
}

function Push-MySifaGitHub {
    <#
    .SYNOPSIS
        Sync Google Drive -> miroir git puis push origin main (Git natif Windows).
    .PARAMETER SkipSync
        Ne pas recopier les fichiers (miroir deja a jour).
    .PARAMETER CommitMessage
        Message de commit (defaut : deploy YYYY-MM-DD HH:mm).
    #>
    param(
        [switch]$SkipSync,
        [string]$CommitMessage
    )

    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    if (-not $scriptDir) { $scriptDir = (Get-Location).Path }

    $truthDir = if ($env:MYSIFA_TRUTH) {
        (Resolve-Path $env:MYSIFA_TRUTH).Path
    } else {
        $scriptDir
    }

    $mirrorDir = if (Test-Path (Join-Path $truthDir ".git")) {
        $truthDir
    } else {
        Resolve-GitMirror
    }

    Write-Host "Push GitHub MySifa"
    Write-Host "  source de verite : $truthDir"
    if ($mirrorDir -ne $truthDir) {
        Write-Host "  miroir git       : $mirrorDir"
    }

    if (-not $SkipSync -and $mirrorDir -ne $truthDir) {
        Sync-TruthToMirror -TruthDir $truthDir -MirrorDir $mirrorDir -FullMirror:$false
    } elseif ($SkipSync) {
        Write-Host "  (sync ignoree)"
    }

    $deploySh = Join-Path $scriptDir "deploy.sh"
    if (Test-Path $deploySh) {
        Copy-Item -Path $deploySh -Destination (Join-Path $mirrorDir "deploy.sh") -Force
    }

    $msg = if ($CommitMessage) {
        $CommitMessage
    } else {
        "deploy $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    }

    Write-Host ""
    Write-Host "Commit + push origin main..."
    Invoke-GitInMirror $mirrorDir add .
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & git -C $mirrorDir commit -m $msg 2>&1 | Out-Host
    $commitCode = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    if ($commitCode -ne 0) {
        $pending = & git -C $mirrorDir status --porcelain
        if ($pending) {
            throw "git commit a echoue alors que des changements sont presents."
        }
        Write-Host "Rien a committer - push des commits deja presents."
    }

    # Evite les blocages silencieux (prompt credentials) dans un terminal non-interactif.
    # - GIT_TERMINAL_PROMPT=0 : pas de demande d'auth en ligne de commande (fail fast)
    # - timeout : rend toujours la main si push suspendu (réseau/credentials)
    $prevPrompt = $env:GIT_TERMINAL_PROMPT
    $env:GIT_TERMINAL_PROMPT = "0"
    try {
        $pushTimeoutSec = 120
        $p = Start-Process -FilePath "git" -ArgumentList @("-C", $mirrorDir, "push", "origin", "main") -NoNewWindow -PassThru
        $done = $p.WaitForExit($pushTimeoutSec * 1000)
        if (-not $done) {
            try { Stop-Process -Id $p.Id -Force } catch {}
            throw "git push bloque (timeout ${pushTimeoutSec}s). Verifiez l'acces au remote (auth/SSH, réseau, VPN)."
        }
        if ($p.ExitCode -ne 0) {
            throw "git push a echoue (code $($p.ExitCode))."
        }
    } finally {
        $env:GIT_TERMINAL_PROMPT = $prevPrompt
    }
    Write-Host ""
    Write-Host "Push GitHub termine."
}

function Invoke-DeploySh {
    param(
        [string]$BashExe,
        [string]$GitPushDir,
        [string]$TruthDir,
        [bool]$SkipSync,
        [bool]$GitHubOnly,
        [string[]]$ExtraArgs
    )

    $bashPush = To-BashPath $GitPushDir
    $bashTruth = To-BashPath $TruthDir
    $skipVal = if ($SkipSync) { "1" } else { "" }
    $argsStr = ($ExtraArgs + $(if ($SkipSync) { "--skip-sync" }) + $(if ($GitHubOnly) { "--push-only" })) -join " "

    $inner = @"
set -euo pipefail
cd '$bashPush'
export MYSIFA_SOURCE='$bashPush'
export MYSIFA_WORKDIR='$bashTruth'
export MYSIFA_SKIP_SYNC='$skipVal'
./deploy.sh $argsStr
"@

    Write-Host ""
    Write-Host "Lancement deploy.sh (git push + VPS)..."
    & $BashExe -lc $inner
    if ($LASTEXITCODE -ne 0) {
        throw "deploy.sh a echoue (code $LASTEXITCODE)."
    }
}

# --- Point d'entree ---
$bash = Find-GitBash
if (-not $bash) {
    throw "Git Bash introuvable - installez Git for Windows."
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$truthDir = if ($env:MYSIFA_TRUTH) {
    (Resolve-Path $env:MYSIFA_TRUTH).Path
} else {
    $scriptDir
}

$deploySh = Join-Path $scriptDir "deploy.sh"
if (-not (Test-Path $deploySh)) {
    throw "deploy.sh introuvable : $deploySh"
}

$gitPushDir = $truthDir
if (-not (Test-Path (Join-Path $truthDir ".git"))) {
    $gitPushDir = Resolve-GitMirror
}

if ($GitHubOnly) {
    Push-MySifaGitHub -SkipSync:$SkipSync -CommitMessage $CommitMessage
    exit 0
}

Write-Host "Deploiement MySifa (Windows)"
Write-Host "  SOURCE DE VERITE : $truthDir"
if ($gitPushDir -ne $truthDir) {
    Write-Host "  miroir git       : $gitPushDir"
}

$skipDeployShSync = $SkipSync.IsPresent
if (-not $SkipSync -and $gitPushDir -ne $truthDir) {
    Sync-TruthToMirror -TruthDir $truthDir -MirrorDir $gitPushDir -FullMirror:$Full.IsPresent
    # Robocopy a deja synchronise : eviter le rsync deploy.sh (code 3 frequent sous Windows)
    $skipDeployShSync = $true
} elseif ($SkipSync) {
    Write-Host "  (sync ignoree -SkipSync)"
}

Copy-Item -Path $deploySh -Destination (Join-Path $gitPushDir "deploy.sh") -Force

Invoke-DeploySh -BashExe $bash -GitPushDir $gitPushDir -TruthDir $truthDir `
    -SkipSync:$skipDeployShSync -GitHubOnly:$false -ExtraArgs $deployShArgs
