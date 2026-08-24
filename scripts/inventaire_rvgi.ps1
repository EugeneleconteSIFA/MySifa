<#
    inventaire_rvgi.ps1 - MySifa
    ============================

    Inventaire LECTURE SEULE et complet de la base HFSQL de l'ERP RVGI (sifa_cs).
    Aucune ecriture sur l'ERP : uniquement OpenSchema, SELECT, COUNT et MAX.

    Ce que le script ramene, pour chaque table hors copies `_backup_...`
    -------------------------------------------------------------------
      - le nombre de lignes ;
      - la date de derniere modification (MAX sur la colonne date de la table),
        qui dit tout de suite si la table est vivante ou morte ;
      - deux vues des colonnes :
          * LOGIQUE  - ce que declare l'analyse HFSQL. Un tableau WinDev
            (`coul[20]`) y compte pour UNE colonne. C'est le modele tel que
            l'a pense l'editeur.
          * PHYSIQUE - ce que renvoie reellement `SELECT *`. Le meme tableau y
            occupe 20 colonnes `coul`, `coul_2` ... `coul_20`. C'est ce qu'un
            script de synchro devra lire.
        Les deux sont utiles et ne se deduisent pas l'une de l'autre.
      - les index declares ;
      - les N DERNIERES lignes.

    Deux sorties
    ------------
      docs\rvgi\rapport_rvgi.md     lisible par un humain
      docs\rvgi\schema_rvgi.json    exploitable par un script

    Le tri des dernieres lignes
    ---------------------------
    La v1 tentait `ORDER BY id DESC` et retombait en silence sur les premieres
    lignes quand le provider refusait la requete - on relisait donc les lignes
    de 2015. Le script teste maintenant plusieurs syntaxes sur une table temoin,
    annonce celle qui passe, et journalise l'erreur des autres dans le JSON
    (`strategies_testees`). Si aucune ne passe, il le dit au lieu de faire
    croire que les lignes sont recentes.

    Prerequis
    ---------
    Aucun. Le provider OLE DB PCSoft.HFSQL est deja sur le poste (celui d'Excel).

    Identifiants - jamais en clair dans le fichier
    ----------------------------------------------
        $env:HFSQL_CONN = 'provider=PCSoft.HFSQL;initial catalog=sifa_cs;data source=192.168.100.199:4949;extended properties="Language=ISO-8859-1"'
        $env:HFSQL_UID  = 'readonly'
        $env:HFSQL_PWD  = '...'

    Usage
    -----
        .\scripts\inventaire_rvgi.ps1
        .\scripts\inventaire_rvgi.ps1 -Echantillon 5
        .\scripts\inventaire_rvgi.ps1 -Motif "gpr_|cdi_"
        .\scripts\inventaire_rvgi.ps1 -SansExtrait      # aucune donnee reelle

    Prudence : par defaut le rapport contient 3 vraies lignes par table,
    tronquees a 60 caracteres. -SansExtrait s'il doit circuler hors SIFA.
#>
[CmdletBinding()]
param(
    [int]      $Echantillon = 3,
    [string]   $Motif,
    [string[]] $Tables,
    [switch]   $AvecBackups,
    [switch]   $AvecCorbeille,
    [switch]   $SansExtrait,
    [switch]   $SansComptage,
    [string]   $DossierSortie
)

$ErrorActionPreference = 'Stop'

# -- Configuration ----------------------------------------------------
$CONN_DEFAUT = 'provider=PCSoft.HFSQL;initial catalog=sifa_cs;data source=192.168.100.199:4949;extended properties="Language=ISO-8859-1"'
$ConnStr    = if ($env:HFSQL_CONN) { $env:HFSQL_CONN } else { $CONN_DEFAUT }
$Uid        = $env:HFSQL_UID
$MotDePasse = $env:HFSQL_PWD
$Timeout    = 60
$MaxColExtraitMd = 30   # colonnes montrees dans l'extrait Markdown (le JSON garde tout)

# Colonnes de date candidates, par ordre de preference.
$COLS_DATE = @('dtem', 'amj', 'amjf', 'amjc', 'amjp', 'amjl', 'date')

# RVGI ne supprime pas : il marque. `corbeille = 0` est la seule ligne vivante ;
# toute autre valeur (1, 9, 2.1, 18.2...) est une ligne mise a la corbeille, et
# ses valeurs n'ont plus aucune garantie de coherence. On les exclut PARTOUT -
# comptages, dates de derniere activite et extraits - sinon on lit et on
# documente des donnees mortes. -AvecCorbeille pour voir le volume total.
$COL_CORBEILLE = 'corbeille'

if (-not $DossierSortie) {
    $racine = Split-Path -Parent $PSScriptRoot
    $DossierSortie = Join-Path $racine 'docs\rvgi'
}
if (-not (Test-Path $DossierSortie)) { New-Item -ItemType Directory -Path $DossierSortie -Force | Out-Null }
$SortieMd   = Join-Path $DossierSortie 'rapport_rvgi.md'
$SortieJson = Join-Path $DossierSortie 'schema_rvgi.json'

$ADO_TABLES       = 20
$ADO_COLUMNS      = 4
$ADO_INDEXES      = 12
$ADO_FOREIGN_KEYS = 27

$AdoTypes = @{
    0='vide'; 2='entier2'; 3='entier4'; 4='reel4'; 5='reel8'; 6='monetaire'
    7='date'; 11='booleen'; 14='decimal'; 16='entier1'; 17='octet'
    18='entier2ns'; 19='entier4ns'; 20='entier8'; 21='entier8ns'; 72='guid'
    128='binaire'; 129='texte'; 130='texte_unicode'; 131='numerique'
    133='date'; 134='heure'; 135='horodatage'; 200='varchar'; 201='texte_long'
    202='varwchar'; 203='texte_long_unicode'; 204='varbinaire'; 205='binaire_long'
}

function Get-TypeLisible {
    param([int]$Code, [int]$Taille)
    $nom = if ($AdoTypes.ContainsKey($Code)) { $AdoTypes[$Code] } else { "type_$Code" }
    if ($Taille -gt 0 -and $Taille -lt 1000000 -and @(129,130,200,202) -contains $Code) {
        return "$nom($Taille)"
    }
    return $nom
}

function Get-NomCite {
    param([string]$Nom)
    if ($Nom -match '^[A-Za-z_][A-Za-z0-9_]*$') { return $Nom }
    return '"' + $Nom + '"'
}

function Format-Cellule {
    param($Valeur)
    if ($null -eq $Valeur) { return '' }
    if ($Valeur -is [System.DBNull]) { return '' }
    $s = [string]$Valeur
    $s = $s -replace "`r`n", ' ' -replace "`n", ' ' -replace "`r", ' ' -replace '\|', '/'
    if ($s.Length -gt 60) { $s = $s.Substring(0, 57) + '...' }
    return $s
}

function Get-MessageCourt {
    param($Erreur)
    $m = ([string]$Erreur) -replace "`r`n", ' ' -replace "`n", ' '
    if ($m.Length -gt 180) { $m = $m.Substring(0, 180) }
    return $m.Trim()
}

function Read-Schema {
    param($Connexion, [int]$Type, [string[]]$Champs)
    $lignes = New-Object System.Collections.ArrayList
    try {
        $rs = $Connexion.OpenSchema($Type)
    } catch {
        return $null
    }
    try {
        $dispo = @()
        for ($i = 0; $i -lt $rs.Fields.Count; $i++) { $dispo += $rs.Fields.Item($i).Name }
        while (-not $rs.EOF) {
            $o = @{}
            foreach ($c in $Champs) {
                if ($dispo -contains $c) { $o[$c] = $rs.Fields.Item($c).Value } else { $o[$c] = $null }
            }
            [void]$lignes.Add($o)
            $rs.MoveNext()
        }
        $rs.Close()
    } catch {
        return $lignes
    }
    return $lignes
}

# Ouvre un recordset et renvoie @{ champs = [...]; lignes = [[...]] }.
function Invoke-Extrait {
    param($Connexion, [string]$Sql, [int]$Max)
    $rsd = New-Object -ComObject ADODB.Recordset
    $rsd.MaxRecords = [Math]::Max($Max, 1)
    $rsd.Open($Sql, $Connexion, 0, 1, 1)   # adOpenForwardOnly, adLockReadOnly, adCmdText

    $champs = New-Object System.Collections.ArrayList
    for ($i = 0; $i -lt $rsd.Fields.Count; $i++) {
        $f = $rsd.Fields.Item($i)
        [void]$champs.Add([pscustomobject]@{
            n    = $i + 1
            nom  = [string]$f.Name
            type = Get-TypeLisible -Code ([int]$f.Type) -Taille ([int]$f.DefinedSize)
        })
    }

    $lignes = New-Object System.Collections.ArrayList
    while ((-not $rsd.EOF) -and ($lignes.Count -lt $Max)) {
        $vals = New-Object System.Collections.ArrayList
        for ($i = 0; $i -lt $rsd.Fields.Count; $i++) {
            $v = $null
            try { $v = $rsd.Fields.Item($i).Value } catch { $v = '<illisible>' }
            [void]$vals.Add((Format-Cellule $v))
        }
        [void]$lignes.Add(@($vals))
        $rsd.MoveNext()
    }
    $rsd.Close()
    return @{ champs = @($champs); lignes = @($lignes) }
}

# -- Connexion --------------------------------------------------------
Write-Host ("Process PowerShell : {0} bits" -f $(if ([Environment]::Is64BitProcess) { 64 } else { 32 })) -ForegroundColor DarkGray
Write-Host ("Connexion : {0}" -f ($ConnStr -split 'extended')[0]) -ForegroundColor DarkGray

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

# -- 1. Tables --------------------------------------------------------
$rs = $conn.OpenSchema($ADO_TABLES)
$toutes = New-Object System.Collections.ArrayList
while (-not $rs.EOF) {
    $nom = [string]$rs.Fields.Item('TABLE_NAME').Value
    $typ = [string]$rs.Fields.Item('TABLE_TYPE').Value
    if ($nom) { [void]$toutes.Add([pscustomobject]@{ Nom = $nom; Type = $typ }) }
    $rs.MoveNext()
}
$rs.Close()
$toutes = @($toutes | Sort-Object { $_.Nom.ToLower() })
$nbBackups = @($toutes | Where-Object { $_.Nom -like '_backup*' }).Count
Write-Host ("{0} objets au schema, dont {1} copies _backup_." -f $toutes.Count, $nbBackups)

$sel = $toutes
if (-not $AvecBackups) { $sel = $sel | Where-Object { $_.Nom -notlike '_backup*' } }
if ($Motif)  { $sel = $sel | Where-Object { $_.Nom -match $Motif } }
if ($Tables) {
    $voulues = $Tables | ForEach-Object { $_.ToLower() }
    $sel = $sel | Where-Object { $voulues -contains $_.Nom.ToLower() }
}
$sel = @($sel)
Write-Host ("{0} table(s) a inspecter." -f $sel.Count)

# -- 2. Colonnes logiques ---------------------------------------------
Write-Host 'Lecture des colonnes (vue logique)...' -NoNewline
$colParTable = @{}
$schemaCols = Read-Schema -Connexion $conn -Type $ADO_COLUMNS -Champs @(
    'TABLE_NAME','COLUMN_NAME','ORDINAL_POSITION','DATA_TYPE','CHARACTER_MAXIMUM_LENGTH'
)
if ($schemaCols) {
    foreach ($c in $schemaCols) {
        $t = [string]$c['TABLE_NAME']
        if (-not $t) { continue }
        if (-not $colParTable.ContainsKey($t)) { $colParTable[$t] = New-Object System.Collections.ArrayList }
        $taille = 0
        if ($null -ne $c['CHARACTER_MAXIMUM_LENGTH']) {
            try { $taille = [int]$c['CHARACTER_MAXIMUM_LENGTH'] } catch { $taille = 0 }
        }
        $code = 0
        try { $code = [int]$c['DATA_TYPE'] } catch { $code = 0 }
        [void]$colParTable[$t].Add([pscustomobject]@{
            n    = [int]$c['ORDINAL_POSITION']
            nom  = [string]$c['COLUMN_NAME']
            type = Get-TypeLisible -Code $code -Taille $taille
        })
    }
    Write-Host (" {0} tables couvertes." -f $colParTable.Count) -ForegroundColor Green
} else {
    Write-Host ' non expose par le provider.' -ForegroundColor Yellow
}

# -- 3. Index ---------------------------------------------------------
Write-Host 'Lecture des index...' -NoNewline
$idxParTable = @{}
$schemaIdx = Read-Schema -Connexion $conn -Type $ADO_INDEXES -Champs @(
    'TABLE_NAME','INDEX_NAME','PRIMARY_KEY','UNIQUE','COLUMN_NAME','ORDINAL_POSITION'
)
if ($schemaIdx) {
    foreach ($i in $schemaIdx) {
        $t = [string]$i['TABLE_NAME']
        if (-not $t) { continue }
        if (-not $idxParTable.ContainsKey($t)) { $idxParTable[$t] = New-Object System.Collections.ArrayList }
        [void]$idxParTable[$t].Add([pscustomobject]@{
            index   = [string]$i['INDEX_NAME']
            colonne = [string]$i['COLUMN_NAME']
            ordre   = [int]$i['ORDINAL_POSITION']
            pk      = [bool]$i['PRIMARY_KEY']
            unique  = [bool]$i['UNIQUE']
        })
    }
    Write-Host (" {0} tables indexees." -f $idxParTable.Count) -ForegroundColor Green
} else {
    Write-Host ' non expose.' -ForegroundColor Yellow
}

# -- 4. Liaisons declarees --------------------------------------------
Write-Host 'Lecture des liaisons...' -NoNewline
$liens = New-Object System.Collections.ArrayList
$schemaFk = Read-Schema -Connexion $conn -Type $ADO_FOREIGN_KEYS -Champs @(
    'PK_TABLE_NAME','PK_COLUMN_NAME','FK_TABLE_NAME','FK_COLUMN_NAME','FK_NAME'
)
if ($schemaFk) {
    foreach ($f in $schemaFk) {
        [void]$liens.Add([pscustomobject]@{
            table_pk = [string]$f['PK_TABLE_NAME']; col_pk = [string]$f['PK_COLUMN_NAME']
            table_fk = [string]$f['FK_TABLE_NAME']; col_fk = [string]$f['FK_COLUMN_NAME']
            nom      = [string]$f['FK_NAME']
        })
    }
    Write-Host (" {0} liaison(s)." -f $liens.Count) -ForegroundColor Green
} else {
    Write-Host ' non expose (liaisons a deduire des noms de colonnes).' -ForegroundColor Yellow
}

# -- 5. Quelle syntaxe pour "les N dernieres lignes" ? -----------------
# On teste sur une table temoin : la plus grosse table non vide qui porte un
# champ `id`. Une syntaxe qui tient sur 70 000 lignes tiendra partout.
# {0} = table, {1} = nombre de lignes, {2} = clause WHERE (vide ou " WHERE corbeille = 0")
$strategies = @(
    @{ nom = 'TOP n + ORDER BY id DESC'; modele = 'SELECT TOP {1} * FROM {0}{2} ORDER BY id DESC' },
    @{ nom = 'ORDER BY id DESC';         modele = 'SELECT * FROM {0}{2} ORDER BY id DESC' },
    @{ nom = 'TOP n + ORDER BY 1 DESC';  modele = 'SELECT TOP {1} * FROM {0}{2} ORDER BY 1 DESC' },
    @{ nom = 'LIMIT n + ORDER BY id DESC'; modele = 'SELECT * FROM {0}{2} ORDER BY id DESC LIMIT {1}' }
)
$strategieRetenue = $null
$strategiesTestees = New-Object System.Collections.ArrayList

if (-not $SansExtrait) {
    $temoin = $null
    foreach ($t in $sel) {
        if ($t.Nom -in @('vte_ligne','cde_ligne','liv_ligne','fic_art')) { $temoin = $t.Nom; break }
    }
    if (-not $temoin -and $sel.Count -gt 0) { $temoin = $sel[0].Nom }

    $filtreTemoin = ''
    if (-not $AvecCorbeille -and $colParTable.ContainsKey($temoin)) {
        if (@($colParTable[$temoin] | ForEach-Object { $_.nom }) -contains $COL_CORBEILLE) {
            $filtreTemoin = " WHERE $COL_CORBEILLE = 0"
        }
    }

    Write-Host "Choix de la syntaxe de tri (table temoin : $temoin$filtreTemoin)" -ForegroundColor DarkGray
    foreach ($s in $strategies) {
        $sql = [string]::Format($s.modele, (Get-NomCite $temoin), 2, $filtreTemoin)
        try {
            $r = Invoke-Extrait -Connexion $conn -Sql $sql -Max 2
            if ($r.lignes.Count -gt 0) {
                [void]$strategiesTestees.Add([pscustomobject]@{ nom = $s.nom; ok = $true; erreur = $null })
                if (-not $strategieRetenue) { $strategieRetenue = $s }
                Write-Host ("  OK    {0}" -f $s.nom) -ForegroundColor Green
            } else {
                [void]$strategiesTestees.Add([pscustomobject]@{ nom = $s.nom; ok = $false; erreur = 'aucune ligne' })
                Write-Host ("  vide  {0}" -f $s.nom) -ForegroundColor Yellow
            }
        } catch {
            $msg = Get-MessageCourt $_.Exception.Message
            [void]$strategiesTestees.Add([pscustomobject]@{ nom = $s.nom; ok = $false; erreur = $msg })
            Write-Host ("  KO    {0} : {1}" -f $s.nom, $msg) -ForegroundColor DarkYellow
        }
    }
    if ($strategieRetenue) {
        Write-Host ("Syntaxe retenue : {0}" -f $strategieRetenue.nom) -ForegroundColor Green
    } else {
        Write-Host 'Aucune syntaxe de tri acceptee - les extraits seront les PREMIERES lignes.' -ForegroundColor Red
    }
}

# -- 6. Volume, derniere activite, extrait ----------------------------
$resultats = New-Object System.Collections.ArrayList
$idx = 0
foreach ($t in $sel) {
    $idx++
    $nom  = $t.Nom
    $cite = Get-NomCite $nom
    Write-Host ("[{0}/{1}] {2}" -f $idx, $sel.Count, $nom)

    $colonnes = @()
    if ($colParTable.ContainsKey($nom)) { $colonnes = @($colParTable[$nom] | Sort-Object n) }
    $nomsCols = @($colonnes | ForEach-Object { $_.nom })

    # Filtre corbeille : applique des que la table porte la colonne.
    $aCorbeille = ($nomsCols -contains $COL_CORBEILLE)
    $filtre = ''
    if ($aCorbeille -and -not $AvecCorbeille) { $filtre = " WHERE $COL_CORBEILLE = 0" }

    $nbTotal   = $null
    $nbLignes  = $null
    if (-not $SansComptage) {
        try {
            $rsc = $conn.Execute("SELECT COUNT(*) FROM $cite")
            $nbTotal = [int64]$rsc.Fields.Item(0).Value
            $rsc.Close()
        } catch { $nbTotal = -1 }

        if ($filtre) {
            try {
                $rsc = $conn.Execute("SELECT COUNT(*) FROM $cite$filtre")
                $nbLignes = [int64]$rsc.Fields.Item(0).Value
                $rsc.Close()
            } catch { $nbLignes = -1 }
        } else {
            $nbLignes = $nbTotal
        }
    }

    # Derniere activite : MAX sur la premiere colonne de date disponible,
    # calcule sur les lignes vivantes uniquement.
    $colDate = $null
    $derniereDate = $null
    foreach ($c in $COLS_DATE) {
        if ($nomsCols -contains $c) { $colDate = $c; break }
    }
    if ($colDate -and $nbLignes -ne 0) {
        try {
            $rsm = $conn.Execute("SELECT MAX($colDate) FROM $cite$filtre")
            $derniereDate = Format-Cellule $rsm.Fields.Item(0).Value
            $rsm.Close()
        } catch { $derniereDate = $null }
    }

    $extrait   = @()
    $physiques = @()
    $triUtilise = $null
    $erreur    = $null

    if (-not $SansExtrait -and $nbLignes -ne 0) {
        $essais = New-Object System.Collections.ArrayList
        if ($strategieRetenue) {
            [void]$essais.Add(@{ sql = [string]::Format($strategieRetenue.modele, $cite, $Echantillon, $filtre); tri = $strategieRetenue.nom })
        }
        [void]$essais.Add(@{ sql = "SELECT * FROM $cite$filtre"; tri = 'aucun (premieres lignes)' })

        foreach ($e in $essais) {
            try {
                $r = Invoke-Extrait -Connexion $conn -Sql $e.sql -Max $Echantillon
                $physiques  = $r.champs
                $extrait    = $r.lignes
                $triUtilise = $e.tri
                $erreur     = $null
                break
            } catch {
                $erreur = Get-MessageCourt $_.Exception.Message
            }
        }
    }

    $indexTable = @()
    if ($idxParTable.ContainsKey($nom)) { $indexTable = @($idxParTable[$nom]) }

    [void]$resultats.Add([pscustomobject]@{
        nom                = $nom
        type               = $t.Type
        lignes             = $nbLignes
        lignes_total       = $nbTotal
        filtre             = $filtre
        a_corbeille        = $aCorbeille
        colonne_date       = $colDate
        derniere_date      = $derniereDate
        tri                = $triUtilise
        erreur             = $erreur
        colonnes_logiques  = @($colonnes)
        colonnes_physiques = @($physiques)
        index              = $indexTable
        extrait            = @($extrait)
    })
}

$conn.Close()

# -- 7. JSON ----------------------------------------------------------
Write-Host ''
Write-Host 'Ecriture du JSON...' -NoNewline
$paquet = [pscustomobject]@{
    genere_le          = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss')
    source             = ($ConnStr -split 'extended')[0].Trim()
    base               = 'sifa_cs'
    erp                = 'RVGI'
    objets_total       = $toutes.Count
    backups            = $nbBackups
    inspectees         = $sel.Count
    echantillon        = $(if ($SansExtrait) { 0 } else { $Echantillon })
    filtre_corbeille   = $(if ($AvecCorbeille) { $null } else { "$COL_CORBEILLE = 0" })
    strategie_tri      = $(if ($strategieRetenue) { $strategieRetenue.nom } else { $null })
    strategies_testees = @($strategiesTestees)
    liens              = @($liens)
    tables             = @($resultats)
}
$json = $paquet | ConvertTo-Json -Depth 8 -Compress
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($SortieJson, $json, $utf8)
Write-Host (" {0:N0} Ko" -f ((Get-Item $SortieJson).Length / 1KB)) -ForegroundColor Green

# -- 8. Markdown ------------------------------------------------------
Write-Host 'Ecriture du Markdown...' -NoNewline
$md = New-Object System.Collections.ArrayList
[void]$md.Add('# Inventaire de la base RVGI (`sifa_cs`)')
[void]$md.Add('')
[void]$md.Add("Genere le $(Get-Date -Format 'dd/MM/yyyy HH:mm') - lecture seule.")
[void]$md.Add('')
[void]$md.Add("Source : ``$(($ConnStr -split 'extended')[0].Trim())``")
[void]$md.Add('')
[void]$md.Add("Objets au schema : $($toutes.Count) - copies ``_backup_`` : $nbBackups - inspectees : $($sel.Count)")
[void]$md.Add('')
if ($strategieRetenue) {
    [void]$md.Add("Extraits : les $Echantillon dernieres lignes (``$($strategieRetenue.nom)``), valeurs tronquees a 60 caracteres.")
} else {
    [void]$md.Add("Extraits : les $Echantillon PREMIERES lignes - aucune syntaxe de tri n'a ete acceptee par le provider.")
}
[void]$md.Add('')
[void]$md.Add('Deux vues des colonnes : **logique** (un tableau WinDev compte pour une colonne, c''est le modele de l''editeur) et **physique** (ce que renvoie `SELECT *`, tableaux depiles en `x`, `x_2`...). Un script de synchro lit la vue physique.')
[void]$md.Add('')
if ($AvecCorbeille) {
    [void]$md.Add('**Corbeille incluse** : les comptages et extraits melangent lignes vivantes et lignes supprimees.')
} else {
    [void]$md.Add('**Corbeille exclue** : comptages, dates et extraits ne portent que sur `corbeille = 0`. La colonne *Total* montre le volume brut, corbeille comprise, quand la table porte ce marqueur.')
}
[void]$md.Add('')
[void]$md.Add('## Sommaire')
[void]$md.Add('')
[void]$md.Add('| Table | Lignes vivantes | Total | Derniere activite | Col. logiques | Col. physiques |')
[void]$md.Add('|---|---:|---:|---|---:|---:|')
foreach ($r in $resultats) {
    $nb = if ($null -eq $r.lignes) { '-' } elseif ($r.lignes -lt 0) { 'erreur' } else { '{0:N0}' -f $r.lignes }
    $tot = if ($null -eq $r.lignes_total) { '-' } elseif ($r.lignes_total -lt 0) { 'erreur' } elseif (-not $r.a_corbeille) { '=' } else { '{0:N0}' -f $r.lignes_total }
    $dd = if ($r.derniere_date) { $r.derniere_date } else { '-' }
    $ancre = ($r.nom.ToLower() -replace '[^a-z0-9]+', '-')
    [void]$md.Add("| [``$($r.nom)``](#$ancre) | $nb | $tot | $dd | $($r.colonnes_logiques.Count) | $($r.colonnes_physiques.Count) |")
}

if ($liens.Count -gt 0) {
    [void]$md.Add('')
    [void]$md.Add('## Liaisons declarees')
    [void]$md.Add('')
    [void]$md.Add('| Table source | Colonne | Table cible | Colonne |')
    [void]$md.Add('|---|---|---|---|')
    foreach ($l in $liens) {
        [void]$md.Add("| ``$($l.table_fk)`` | ``$($l.col_fk)`` | ``$($l.table_pk)`` | ``$($l.col_pk)`` |")
    }
}

[void]$md.Add('')
[void]$md.Add('## Detail des tables')
[void]$md.Add('')
foreach ($r in $resultats) {
    [void]$md.Add("### ``$($r.nom)``")
    [void]$md.Add('')
    $nb = if ($null -eq $r.lignes) { 'non compte' } elseif ($r.lignes -lt 0) { 'erreur de comptage' } else { '{0:N0}' -f $r.lignes }
    $ligneMeta = "Lignes : $nb - colonnes logiques : $($r.colonnes_logiques.Count) - physiques : $($r.colonnes_physiques.Count)"
    if ($r.a_corbeille -and $null -ne $r.lignes_total -and $r.lignes_total -ge 0) {
        $ligneMeta += " - total corbeille comprise : $('{0:N0}' -f $r.lignes_total)"
    }
    if ($r.derniere_date) { $ligneMeta += " - derniere activite ($($r.colonne_date)) : $($r.derniere_date)" }
    if ($r.tri) { $ligneMeta += " - extrait : $($r.tri)" }
    [void]$md.Add($ligneMeta)
    if ($r.erreur) {
        [void]$md.Add('')
        [void]$md.Add("Extrait impossible : $($r.erreur)")
    }
    [void]$md.Add('')

    if ($r.index.Count -gt 0) {
        $parIndex = $r.index | Group-Object index
        [void]$md.Add('Cles : ' + (($parIndex | ForEach-Object {
            $cols = ($_.Group | Sort-Object ordre | ForEach-Object { $_.colonne }) -join ', '
            $marque = if ($_.Group[0].pk) { ' (primaire)' } elseif ($_.Group[0].unique) { ' (unique)' } else { '' }
            "``$($_.Name)`` sur $cols$marque"
        }) -join ' - '))
        [void]$md.Add('')
    }

    [void]$md.Add('| # | Colonne (logique) | Type |')
    [void]$md.Add('|---:|---|---|')
    foreach ($c in $r.colonnes_logiques) {
        [void]$md.Add("| $($c.n) | ``$($c.nom)`` | $($c.type) |")
    }

    if ($r.extrait.Count -gt 0 -and $r.colonnes_physiques.Count -gt 0) {
        $nbCol = [Math]::Min($r.colonnes_physiques.Count, $MaxColExtraitMd)
        $entetes = @($r.colonnes_physiques | Select-Object -First $nbCol | ForEach-Object { $_.nom })
        [void]$md.Add('')
        $note = if ($r.colonnes_physiques.Count -gt $nbCol) { " (les $nbCol premieres colonnes sur $($r.colonnes_physiques.Count) - tout est dans le JSON)" } else { '' }
        [void]$md.Add("Dernieres lignes$note :")
        [void]$md.Add('')
        [void]$md.Add('| ' + ($entetes -join ' | ') + ' |')
        [void]$md.Add('|' + ('---|' * $nbCol))
        foreach ($l in $r.extrait) {
            $vals = @($l | Select-Object -First $nbCol)
            while ($vals.Count -lt $nbCol) { $vals += '' }
            [void]$md.Add('| ' + ($vals -join ' | ') + ' |')
        }
    }
    [void]$md.Add('')
}

[System.IO.File]::WriteAllText($SortieMd, ($md -join [Environment]::NewLine), $utf8)
Write-Host (" {0:N0} Ko" -f ((Get-Item $SortieMd).Length / 1KB)) -ForegroundColor Green

Write-Host ''
Write-Host "JSON     : $SortieJson" -ForegroundColor Green
Write-Host "Markdown : $SortieMd" -ForegroundColor Green
Write-Host 'Les deux contiennent des extraits de donnees reelles - a ne pas diffuser hors SIFA.' -ForegroundColor DarkGray
