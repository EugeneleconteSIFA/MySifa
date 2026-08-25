<#
    sync_rvgi.ps1 - MySifa
    ======================

    Synchronisation RVGI -> MySifa. A lancer par le Planificateur de taches
    Windows, sur une machine du RESEAU SIFA (le VPS ne voit pas 192.168.100.x).

    Ce qu'elle fait, dans l'ordre
    -----------------------------
      1. exporte l'ERP en CSV (scripts\export_rvgi_csv.ps1, lecture seule) ;
      2. zippe le dossier d'export ;
      3. pousse l'archive vers chaque instance MySifa declaree, en HTTPS,
         authentifiee par une cle API (header X-Api-Key, portee erp:write) ;
      4. supprime l'archive et les CSV locaux ;
      5. journalise tout dans data\logs\sync_rvgi.log.

    C'est le SERVEUR qui reconstruit le miroir a partir des CSV. Cette machine
    n'a donc besoin ni de Python ni de SQLite : PowerShell suffit.

    Configuration - dans le .env a la racine du projet
    --------------------------------------------------
        HFSQL_CONN=provider=PCSoft.HFSQL;initial catalog=sifa_cs;data source=192.168.100.199:4949;extended properties="Language=ISO-8859-1"
        HFSQL_UID=compte_lecture
        HFSQL_PWD=...

        # Une URL par instance, separees par des virgules.
        MYSIFA_SYNC_URLS=https://v1.mysifa.com,https://www.mysifa.com
        MYSIFA_API_KEY=...        # creee dans Parametres > Cles API, portee "Synchro ERP RVGI"

    ATTENTION : v1 et la prod ont chacune LEUR base, donc chacune ses cles API.
    Une cle creee sur v1 est effacee par le resync nocturne (02:00 UTC, la DB de
    v1 est reecrite depuis celle de prod). La cle a garder est donc celle creee
    en PROD : elle arrivera sur v1 au resync suivant. En attendant, on peut
    donner une cle par instance :

        MYSIFA_SYNC_URLS=https://v1.mysifa.com|cle_v1,https://www.mysifa.com|cle_prod

    Sans `|`, c'est MYSIFA_API_KEY qui sert.

    Installation de la tache planifiee (PowerShell en administrateur)
    -----------------------------------------------------------------
        $ps = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
        $script = "C:\chemin\vers\MySifa\scripts\sync_rvgi.ps1"
        schtasks /Create /TN "MySifa - Synchro RVGI 5h"    /SC DAILY /ST 05:00 /RU SYSTEM `
                 /TR "$ps -NoProfile -ExecutionPolicy Bypass -File `"$script`""
        schtasks /Create /TN "MySifa - Synchro RVGI 12h30" /SC DAILY /ST 12:30 /RU SYSTEM `
                 /TR "$ps -NoProfile -ExecutionPolicy Bypass -File `"$script`""

    Verification a la main
    ----------------------
        .\scripts\sync_rvgi.ps1 -Verbeux
#>
[CmdletBinding()]
param(
    [switch] $Verbeux,
    [switch] $SansEnvoi,      # exporte et zippe, n'envoie rien (test)
    [string[]] $Urls,         # surcharge MYSIFA_SYNC_URLS
    [int] $TimeoutSec = 900
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$racine   = Split-Path -Parent $PSScriptRoot
$dossierLog = Join-Path $racine 'data\logs'
if (-not (Test-Path $dossierLog)) { New-Item -ItemType Directory -Path $dossierLog -Force | Out-Null }
$journal  = Join-Path $dossierLog 'sync_rvgi.log'
$verrou   = Join-Path $dossierLog 'sync_rvgi.lock'

function Ecrire {
    param([string]$Message, [string]$Niveau = 'INFO')
    $ligne = "{0} [{1}] {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Niveau, $Message
    Add-Content -Path $journal -Value $ligne -Encoding UTF8
    if ($Verbeux -or $Niveau -ne 'INFO') {
        $couleur = switch ($Niveau) { 'ERREUR' { 'Red' } 'ALERTE' { 'Yellow' } default { 'Gray' } }
        Write-Host $ligne -ForegroundColor $couleur
    }
}

# -- Verrou : deux executions qui se chevauchent liraient l'ERP en double ----
if (Test-Path $verrou) {
    $age = (Get-Date) - (Get-Item $verrou).LastWriteTime
    if ($age.TotalMinutes -lt 90) {
        Ecrire ("Une synchro tourne deja (verrou de {0:N0} min). Abandon." -f $age.TotalMinutes) 'ALERTE'
        exit 0
    }
    Ecrire ("Verrou perime de {0:N0} min : on passe outre." -f $age.TotalMinutes) 'ALERTE'
    Remove-Item $verrou -Force -ErrorAction SilentlyContinue
}
New-Item -ItemType File -Path $verrou -Force | Out-Null

# -- Lecture du .env ---------------------------------------------------------
# Duplique volontairement le parseur de export_rvgi_csv.ps1 : la tache
# planifiee doit tenir dans un seul fichier, sans dependance a un module tiers.
function Read-DotEnv {
    param([string]$Chemin)
    $valeurs = @{}
    if (-not (Test-Path $Chemin)) { return $valeurs }
    foreach ($ligne in (Get-Content -LiteralPath $Chemin -Encoding UTF8)) {
        $l = $ligne.Trim()
        if (-not $l -or $l.StartsWith('#')) { continue }
        $i = $l.IndexOf('=')
        if ($i -lt 1) { continue }
        $cle = $l.Substring(0, $i).Trim()
        $val = $l.Substring($i + 1).Trim()
        if ($val.Length -ge 2) {
            if (($val.StartsWith('"') -and $val.EndsWith('"')) -or
                ($val.StartsWith("'") -and $val.EndsWith("'"))) {
                $val = $val.Substring(1, $val.Length - 2)
            }
        }
        $valeurs[$cle] = $val
    }
    return $valeurs
}

$dotenv = Read-DotEnv (Join-Path $racine '.env')
function Get-Param {
    param([string]$Nom, [string]$Defaut = $null)
    $p = [Environment]::GetEnvironmentVariable($Nom)
    if ($p) { return $p }
    if ($dotenv.ContainsKey($Nom) -and $dotenv[$Nom]) { return $dotenv[$Nom] }
    return $Defaut
}

$cle = Get-Param 'MYSIFA_API_KEY'

# Chaque entree vaut "url" ou "url|cle". Sans cle explicite, MYSIFA_API_KEY.
$cibles = @()
$brut = if ($Urls) { $Urls -join ',' } else { Get-Param 'MYSIFA_SYNC_URLS' }
if ($brut) {
    foreach ($morceau in ($brut -split ',')) {
        $m = $morceau.Trim()
        if (-not $m) { continue }
        $bouts = $m -split '\|', 2
        $cibles += [pscustomobject]@{
            Url = $bouts[0].Trim().TrimEnd('/')
            Cle = if ($bouts.Count -gt 1 -and $bouts[1].Trim()) { $bouts[1].Trim() } else { $cle }
        }
    }
}

$dossierExport = Join-Path $racine 'data\rvgi_export'
$archive = Join-Path $racine 'data\rvgi_export.zip'
$codeSortie = 0
$garderArchive = $false

try {
    if (-not $SansEnvoi) {
        if (-not $cibles) { throw 'MYSIFA_SYNC_URLS absente du .env.' }
        $sansCle = @($cibles | Where-Object { -not $_.Cle })
        if ($sansCle) {
            throw ("Aucune cle API pour : {0}" -f (($sansCle | ForEach-Object { $_.Url }) -join ', '))
        }
    }

    Ecrire '--- Synchro RVGI : debut ---'

    # -- 1. Export ----------------------------------------------------------
    $chrono = [Diagnostics.Stopwatch]::StartNew()
    $scriptExport = Join-Path $PSScriptRoot 'export_rvgi_csv.ps1'
    $global:LASTEXITCODE = 0
    $avant = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $scriptExport
    $codeExport = $LASTEXITCODE
    $ErrorActionPreference = $avant
    Ecrire ("Export termine, code {0}" -f $codeExport)
    if ($codeExport -ne 0) { throw ("Export en echec, code {0}" -f $codeExport) }

    $lignes = @(Get-ChildItem -Path $dossierExport -Filter *.csv -ErrorAction SilentlyContinue)
    if (-not $lignes) { throw 'Aucun CSV produit par l export.' }
    # Un export interrompu laisse des CSV, mais pas les 61 attendus.
    if ($lignes.Count -lt 20) {
        throw ("Export incomplet : {0} fichiers seulement." -f $lignes.Count)
    }
    $poids = ($lignes | Measure-Object -Property Length -Sum).Sum
    Ecrire ("Export : {0} fichiers, {1:N1} Mo, en {2:N0} s" -f $lignes.Count, ($poids / 1MB), $chrono.Elapsed.TotalSeconds)

    # -- 2. Archive ---------------------------------------------------------
    if (Test-Path $archive) { Remove-Item $archive -Force }
    Compress-Archive -Path (Join-Path $dossierExport '*') -DestinationPath $archive -CompressionLevel Optimal
    $poidsZip = (Get-Item $archive).Length
    Ecrire ("Archive : {0:N1} Mo" -f ($poidsZip / 1MB))

    # -- 3. Envoi -----------------------------------------------------------
    if ($SansEnvoi) {
        Ecrire 'Mode -SansEnvoi : archive conservee, rien n a ete envoye.' 'ALERTE'
        Ecrire ("Archive : {0}" -f $archive)
        $garderArchive = $true
        $cibles = @()
    }

    foreach ($c in $cibles) {
        $adresse = "$($c.Url)/api/bridge/erp/miroir"
        try {
            $t = [Diagnostics.Stopwatch]::StartNew()
            $reponse = Invoke-RestMethod -Uri $adresse -Method Post -InFile $archive `
                        -ContentType 'application/zip' `
                        -Headers @{ 'X-Api-Key' = $c.Cle } -TimeoutSec $TimeoutSec
            Ecrire ("{0} : {1} fichiers recus, {2:N1} Mo, en {3:N0} s" -f `
                    $c.Url, $reponse.fichiers, ($reponse.recu_octets / 1MB), $t.Elapsed.TotalSeconds)
        } catch {
            $codeSortie = 1
            $detail = $_.Exception.Message
            if ($_.ErrorDetails -and $_.ErrorDetails.Message) { $detail = $_.ErrorDetails.Message }
            Ecrire ("{0} : ECHEC - {1}" -f $c.Url, $detail) 'ERREUR'
        }
    }
}
catch {
    $codeSortie = 1
    Ecrire ("Interruption : {0}" -f $_.Exception.Message) 'ERREUR'
}
finally {
    # -- 4. Menage : les CSV portent des donnees clients, ils ne restent pas --
    if (-not $garderArchive) { Remove-Item $archive -Force -ErrorAction SilentlyContinue }
    if (Test-Path $dossierExport) {
        Remove-Item (Join-Path $dossierExport '*') -Force -Recurse -ErrorAction SilentlyContinue
    }
    Remove-Item $verrou -Force -ErrorAction SilentlyContinue
    Ecrire ("--- Synchro RVGI : fin (code {0}) ---" -f $codeSortie)

    # -- Rotation simple du journal : au-dela de 5 Mo, on repart a zero ------
    if ((Test-Path $journal) -and ((Get-Item $journal).Length -gt 5MB)) {
        $vieux = "$journal.1"
        if (Test-Path $vieux) { Remove-Item $vieux -Force -ErrorAction SilentlyContinue }
        Move-Item $journal $vieux -Force -ErrorAction SilentlyContinue
    }
}

exit $codeSortie
