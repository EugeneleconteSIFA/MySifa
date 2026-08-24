<#
    export_rvgi_csv.ps1 - MySifa
    ============================

    Export LECTURE SEULE de la base HFSQL de l'ERP RVGI (sifa_cs) vers des CSV,
    pour alimenter le miroir `erp_mirror.db` de MySifa.

    Aucune ecriture sur l'ERP : uniquement SELECT.

    Ce que le script garantit
    -------------------------
      - `corbeille = 0` : seules les lignes vivantes sortent, sur toutes les
        tables qui portent le marqueur. RVGI ne supprime pas, il marque.
      - Colonnes sensibles JAMAIS lues : mots de passe salaries et acces FTP
        clients / fournisseurs sont retires de la liste de colonnes AVANT la
        requete (cf. $COLS_INTERDITES). La valeur n'entre jamais en memoire.
      - Tables de mots de passe jamais ouvertes ($TABLES_INTERDITES).
      - Vue PHYSIQUE des colonnes : les tableaux WinDev sortent depiles
        (`pafou1`, `pafou1_2`, ... `pafou1_10`), c'est ce que le miroir stocke.

    Sorties
    -------
      <Dossier>\<table>.csv        un fichier par table, UTF-8 BOM, separateur ;
      <Dossier>\_manifeste.json    tables, colonnes, lignes, filtre applique

    Le dossier par defaut est `data\rvgi_export\`, ignore par git : ces fichiers
    contiennent des noms de clients, des adresses et des prix reels.

    Identifiants - jamais en clair dans le fichier
    ----------------------------------------------
        $env:HFSQL_CONN = 'provider=PCSoft.HFSQL;initial catalog=sifa_cs;data source=192.168.100.199:4949;extended properties="Language=ISO-8859-1"'
        $env:HFSQL_UID  = 'readonly'
        $env:HFSQL_PWD  = '...'

    Usage
    -----
        .\scripts\export_rvgi_csv.ps1                     # tout le perimetre
        .\scripts\export_rvgi_csv.ps1 -Domaine cde,fic    # deux domaines
        .\scripts\export_rvgi_csv.ps1 -Tables cde_entete,cde_ligne
        .\scripts\export_rvgi_csv.ps1 -Max 2000           # echantillon rapide
#>
[CmdletBinding()]
param(
    [string[]] $Tables,
    [string[]] $Domaine,
    [int]      $Max = 0,
    [int]      $Bloc = 2000,
    [string]   $Dossier
)

$ErrorActionPreference = 'Stop'

# -- Configuration ----------------------------------------------------
$CONN_DEFAUT = 'provider=PCSoft.HFSQL;initial catalog=sifa_cs;data source=192.168.100.199:4949;extended properties="Language=ISO-8859-1"'
$ConnStr    = if ($env:HFSQL_CONN) { $env:HFSQL_CONN } else { $CONN_DEFAUT }
$Uid        = $env:HFSQL_UID
$MotDePasse = $env:HFSQL_PWD
$Timeout    = 120

# Jamais lues. Mots de passe salaries en clair, acces FTP clients/fournisseurs.
$COLS_INTERDITES = @('mdp','mdpbloq','pasmail','inftpmdp','ftpmdp','inftp','ftp')

# Jamais ouvertes. Tables de mots de passe applicatifs.
$TABLES_INTERDITES = @('gen_mdp','gen_mdpsal')

# Perimetre : les tables qui portent des ecrans. Un domaine = un prefixe.
$PERIMETRE = [ordered]@{
    'fic' = @('fic_art','fic_artv','fic_arta','fic_artc','fic_clt','fic_clta',
              'fic_fou','fic_foui','fic_depot','fic_pays','fic_ua','fic_uc',
              'fic_uv','fic_tva','fic_reg','fic_para','fic_rep','fic_tar')
    'mat' = @('mat_mat','mat_fmat','mat_nomen')
    'mac' = @('mac_pro','mac_tra','mac_ptps')
    'out' = @('out_dec','out_deca','out_cyl')
    'gen' = @('gen_sala','gen_soc')
    'dev' = @('dev_entete','dev_ligne')
    'cde' = @('cde_entete','cde_ligne','cde_exped')
    'cdm' = @('cdm_entete','cdm_ligne','cdm_appel')
    'liv' = @('liv_entete','liv_ligne')
    'vte' = @('vte_entete','vte_ligne')
    'ecc' = @('ecc_ech','ecc_reg')
    'col' = @('col_ligne')
    'cdf' = @('cdf_entete','cdf_ligne')
    'lif' = @('lif_ligne')
    'vtf' = @('vtf_entete','vtf_ligne')
    'stk' = @('stk_hist')
    'stm' = @('stm_hist')
    'gpr' = @('gpr_ff','gpr_ff1','gpr_gpr','gpr_mat')
    'cdi' = @('cdi_entete','cdi_ligne','cdi_res')
    'aof' = @('aof_entete','aof_ligne')
    'cpr' = @('cpr_pv')
}

if (-not $Dossier) {
    $racine  = Split-Path -Parent $PSScriptRoot
    $Dossier = Join-Path $racine 'data\rvgi_export'
}
if (-not (Test-Path $Dossier)) { New-Item -ItemType Directory -Path $Dossier -Force | Out-Null }

# -- Selection --------------------------------------------------------
$voulues = New-Object System.Collections.ArrayList
if ($Tables) {
    foreach ($t in $Tables) { [void]$voulues.Add($t.ToLower()) }
} elseif ($Domaine) {
    foreach ($d in $Domaine) {
        $k = $d.ToLower()
        if ($PERIMETRE.Contains($k)) { foreach ($t in $PERIMETRE[$k]) { [void]$voulues.Add($t) } }
        else { Write-Host ("Domaine inconnu : {0}" -f $d) -ForegroundColor Yellow }
    }
} else {
    foreach ($k in $PERIMETRE.Keys) { foreach ($t in $PERIMETRE[$k]) { [void]$voulues.Add($t) } }
}
$voulues = @($voulues | Where-Object { $TABLES_INTERDITES -notcontains $_ } | Select-Object -Unique)

if ($voulues.Count -eq 0) { Write-Host 'Aucune table selectionnee.' -ForegroundColor Yellow; exit 1 }

# -- Outils -----------------------------------------------------------
$CULTURE = [System.Globalization.CultureInfo]::InvariantCulture

function Get-NomCite {
    param([string]$Nom)
    if ($Nom -match '^[A-Za-z_][A-Za-z0-9_]*$') { return $Nom }
    return '"' + $Nom + '"'
}

function Format-Valeur {
    param($V)
    if ($null -eq $V)               { return '' }
    if ($V -is [System.DBNull])     { return '' }
    if ($V -is [datetime])          { return $V.ToString('yyyy-MM-dd HH:mm:ss', $CULTURE) }
    if ($V -is [bool])              { return $(if ($V) { '1' } else { '0' }) }
    if ($V -is [double] -or $V -is [single] -or $V -is [decimal]) {
        return $V.ToString($CULTURE)
    }
    return [string]$V
}

function Protege-Csv {
    param([string]$S)
    if ($S -match '[;"\r\n]') { return '"' + ($S -replace '"','""') + '"' }
    return $S
}

# -- Connexion --------------------------------------------------------
Write-Host ("Process PowerShell : {0} bits" -f $(if ([Environment]::Is64BitProcess) { 64 } else { 32 })) -ForegroundColor DarkGray

$chaine = $ConnStr
if ($Uid -and ($ConnStr -notmatch '(?i)user\s*id')) {
    $chaine = "$ConnStr;User ID=$Uid;Password=$MotDePasse"
}

$conn = New-Object -ComObject ADODB.Connection
$conn.ConnectionTimeout = $Timeout
$conn.CommandTimeout    = $Timeout
try {
    $conn.Open($chaine)
} catch {
    Write-Host ''
    Write-Host "Connexion impossible : $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'Pistes : provider 32 bits (relancer depuis SysWOW64), chaine HFSQL_CONN incomplete,' -ForegroundColor Yellow
    Write-Host 'identifiants absents, ou poste hors reseau SIFA.' -ForegroundColor Yellow
    exit 1
}
Write-Host 'Connecte.' -ForegroundColor Green
Write-Host ("{0} table(s) a exporter vers {1}" -f $voulues.Count, $Dossier)
Write-Host ''

# -- Export -----------------------------------------------------------
$manifeste = New-Object System.Collections.ArrayList
$totalLignes = 0

foreach ($table in $voulues) {

    Write-Host ("{0,-16}" -f $table) -NoNewline

    # 1. Colonnes physiques : metadonnees seules, aucune valeur lue.
    $cols = New-Object System.Collections.ArrayList
    try {
        $rsm = New-Object -ComObject ADODB.Recordset
        $rsm.MaxRecords = 1
        $rsm.Open(("SELECT * FROM {0}" -f (Get-NomCite $table)), $conn, 0, 1, 1)
        for ($i = 0; $i -lt $rsm.Fields.Count; $i++) {
            [void]$cols.Add([string]$rsm.Fields.Item($i).Name)
        }
        $rsm.Close()
    } catch {
        Write-Host (" ECHEC lecture du schema : {0}" -f $_.Exception.Message) -ForegroundColor Red
        [void]$manifeste.Add([pscustomobject]@{ table = $table; erreur = $_.Exception.Message })
        continue
    }

    if ($cols.Count -eq 0) {
        Write-Host ' vide (aucune colonne physique).' -ForegroundColor DarkGray
        [void]$manifeste.Add([pscustomobject]@{ table = $table; lignes = 0; colonnes = @(); note = 'aucune colonne physique' })
        continue
    }

    $aCorbeille = $false
    $gardees = New-Object System.Collections.ArrayList
    $retirees = New-Object System.Collections.ArrayList
    foreach ($c in $cols) {
        if ($c -eq 'corbeille') { $aCorbeille = $true }
        if ($COLS_INTERDITES -contains $c.ToLower()) { [void]$retirees.Add($c); continue }
        [void]$gardees.Add($c)
    }

    # 2. Requete sur colonnes explicites - les interdites ne sont jamais demandees.
    $listeCols = ($gardees | ForEach-Object { Get-NomCite $_ }) -join ', '
    $filtre = if ($aCorbeille) { ' WHERE corbeille = 0' } else { '' }
    $sql = "SELECT $listeCols FROM $(Get-NomCite $table)$filtre"

    $chemin = Join-Path $Dossier ("{0}.csv" -f $table)
    $nb = 0
    try {
        $rs = New-Object -ComObject ADODB.Recordset
        if ($Max -gt 0) { $rs.MaxRecords = $Max }
        $rs.Open($sql, $conn, 0, 1, 1)   # adOpenForwardOnly, adLockReadOnly, adCmdText

        $enc = New-Object System.Text.UTF8Encoding($true)
        $sw  = New-Object System.IO.StreamWriter($chemin, $false, $enc)
        try {
            $sw.WriteLine((($gardees | ForEach-Object { Protege-Csv $_ }) -join ';'))

            while (-not $rs.EOF) {
                $paquet = $rs.GetRows($Bloc)
                $nbCol = $paquet.GetLength(0)
                $nbLig = $paquet.GetLength(1)
                for ($r = 0; $r -lt $nbLig; $r++) {
                    $cells = New-Object string[] $nbCol
                    for ($c = 0; $c -lt $nbCol; $c++) {
                        $cells[$c] = Protege-Csv (Format-Valeur $paquet[$c, $r])
                    }
                    $sw.WriteLine(($cells -join ';'))
                    $nb++
                }
                if ($Max -gt 0 -and $nb -ge $Max) { break }
            }
        } finally {
            $sw.Flush(); $sw.Close(); $sw.Dispose()
        }
        $rs.Close()
    } catch {
        Write-Host (" ECHEC : {0}" -f $_.Exception.Message) -ForegroundColor Red
        [void]$manifeste.Add([pscustomobject]@{ table = $table; erreur = $_.Exception.Message })
        continue
    }

    $totalLignes += $nb
    $taille = 0
    try { $taille = (Get-Item $chemin).Length } catch { $taille = 0 }
    $suffixe = ''
    if ($retirees.Count -gt 0) { $suffixe = (" - {0} colonne(s) sensible(s) exclue(s)" -f $retirees.Count) }
    if (-not $aCorbeille)      { $suffixe += ' - pas de colonne corbeille' }
    Write-Host (" {0,9:N0} lignes  {1,7:N0} Ko{2}" -f $nb, ($taille / 1KB), $suffixe) -ForegroundColor Green

    [void]$manifeste.Add([pscustomobject]@{
        table            = $table
        fichier          = ("{0}.csv" -f $table)
        lignes           = $nb
        octets           = $taille
        filtre_corbeille = $aCorbeille
        colonnes         = @($gardees)
        colonnes_exclues = @($retirees)
        tronque          = ($Max -gt 0 -and $nb -ge $Max)
    })
}

$conn.Close()

# -- Manifeste --------------------------------------------------------
$meta = [pscustomobject]@{
    genere_le  = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss')
    base       = 'sifa_cs'
    erp        = 'RVGI'
    source     = ($ConnStr -split ';extended')[0]
    separateur = ';'
    encodage   = 'UTF-8 (BOM)'
    date_format= 'yyyy-MM-dd HH:mm:ss'
    max_lignes = $Max
    tables     = @($manifeste)
}
$cheminManifeste = Join-Path $Dossier '_manifeste.json'
$meta | ConvertTo-Json -Depth 6 | Set-Content -Path $cheminManifeste -Encoding UTF8

Write-Host ''
Write-Host ("Termine : {0:N0} lignes dans {1}" -f $totalLignes, $Dossier) -ForegroundColor Green
Write-Host ("Manifeste : {0}" -f $cheminManifeste) -ForegroundColor DarkGray
Write-Host ''
Write-Host 'Ces CSV contiennent des donnees reelles (clients, adresses, prix).' -ForegroundColor Yellow
Write-Host 'Le dossier data\rvgi_export\ est ignore par git - le laisser la.' -ForegroundColor Yellow
