<#
    inspect_hfsql_sifa_cs.ps1 — MySifa
    ==================================

    Inventaire LECTURE SEULE de la base HFSQL `sifa_cs` (ERP). Liste les tables,
    leurs colonnes, le nombre de lignes et quelques valeurs d'exemple, puis écrit
    un rapport Markdown. Aucune écriture sur l'ERP.

    Pourquoi PowerShell et pas Python
    ---------------------------------
    Le provider OLE DB `PCSoft.HFSQL` est déjà installé sur le poste (c'est celui
    qu'Excel utilise) et PowerShell l'atteint via COM/ADODB sans rien installer.
    La variante Python (`inspect_hfsql_sifa_cs.py`) fait exactement la même chose
    sur un poste qui a Python — elle sert de base au futur script de synchro.

    Le driver ODBC HFSQL est une troisième voie, mais il suppose un DSN système et
    fait planter pyodbc : inutile ici.

    Prérequis
    ---------
    Aucun. Juste être sur le réseau SIFA (la base écoute en 192.168.100.199:4949).

    L'architecture du process doit correspondre à celle du provider. PowerShell est
    64 bits par défaut. Si le provider est 32 bits (Excel 32 bits), relancer le
    script depuis :
        C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe

    Identifiants — jamais en clair dans le fichier
    ----------------------------------------------
        $env:HFSQL_CONN = 'provider=PCSoft.HFSQL;initial catalog=sifa_cs;data source=192.168.100.199:4949;extended properties="Language=ISO-8859-1"'
        $env:HFSQL_UID  = 'readonly'
        $env:HFSQL_PWD  = '...'

    La chaîne complète se relit dans Excel : Données → Requêtes et connexions →
    Propriétés → Définition → Chaîne de connexion.

    Usage
    -----
        .\scripts\inspect_hfsql_sifa_cs.ps1
        .\scripts\inspect_hfsql_sifa_cs.ps1 -Motif "cdi_|vte_|mat_"
        .\scripts\inspect_hfsql_sifa_cs.ps1 -Tables vte_com,cdi_entete
        .\scripts\inspect_hfsql_sifa_cs.ps1 -SansComptage       # rapide
        .\scripts\inspect_hfsql_sifa_cs.ps1 -Echantillon 0      # aucune donnée réelle

    Prudence : par défaut le rapport contient 3 vraies lignes par table, tronquées
    à 60 caractères. Mettre -Echantillon 0 s'il doit circuler.
#>
[CmdletBinding()]
param(
    [string]   $Motif,
    [string[]] $Tables,
    [int]      $Echantillon = 3,
    [switch]   $SansComptage,
    [switch]   $AvecBackups,
    [string]   $Sortie
)

$ErrorActionPreference = 'Stop'

# ── Configuration ────────────────────────────────────────────────────
$CONN_DEFAUT = 'provider=PCSoft.HFSQL;initial catalog=sifa_cs;data source=192.168.100.199:4949;extended properties="Language=ISO-8859-1"'
$ConnStr = if ($env:HFSQL_CONN) { $env:HFSQL_CONN } else { $CONN_DEFAUT }
$Uid       = $env:HFSQL_UID
$MotDePasse = $env:HFSQL_PWD
$Timeout = 30

if (-not $Sortie) {
    $Sortie = Join-Path $PSScriptRoot 'rapport_sifa_cs.md'
}

# adSchemaTables
$ADO_SCHEMA_TABLES = 20

$AdoTypes = @{
    0='vide'; 2='entier2'; 3='entier4'; 4='réel4'; 5='réel8'; 6='monétaire'
    7='date'; 11='booléen'; 14='décimal'; 16='entier1'; 17='octet'
    18='entier2ns'; 19='entier4ns'; 20='entier8'; 21='entier8ns'; 72='guid'
    128='binaire'; 129='texte'; 130='texte_unicode'; 131='numérique'
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
    $s = [string]$Valeur
    $s = $s -replace "`r`n", ' ' -replace "`n", ' ' -replace "`r", ' ' -replace '\|', '/'
    if ($s.Length -gt 60) { $s = $s.Substring(0, 60) }
    return $s
}

# ── Connexion ────────────────────────────────────────────────────────
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
    Write-Host ''
    Write-Host 'Pistes :' -ForegroundColor Yellow
    Write-Host '  - "Fournisseur introuvable" alors qu Excel fonctionne : le provider est 32 bits.'
    Write-Host '    Relancer depuis C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe'
    Write-Host '  - Chaine HFSQL_CONN incomplete : la recopier depuis Excel (Donnees > Requetes'
    Write-Host '    et connexions > Proprietes > Definition).'
    Write-Host '  - Identifiants HFSQL_UID / HFSQL_PWD absents, ou poste hors reseau SIFA.'
    exit 1
}
Write-Host 'Connecté.' -ForegroundColor Green

# ── Liste des tables ─────────────────────────────────────────────────
$rs = $conn.OpenSchema($ADO_SCHEMA_TABLES)
$toutes = New-Object System.Collections.ArrayList
while (-not $rs.EOF) {
    $nom = [string]$rs.Fields.Item('TABLE_NAME').Value
    $typ = [string]$rs.Fields.Item('TABLE_TYPE').Value
    if ($nom) { [void]$toutes.Add([pscustomobject]@{ Nom = $nom; Type = $typ }) }
    $rs.MoveNext()
}
$rs.Close()
$toutes = $toutes | Sort-Object { $_.Nom.ToLower() }
Write-Host ("{0} objets remontés par le schéma." -f $toutes.Count)

$sel = $toutes
$nbBackups = ($toutes | Where-Object { $_.Nom -like '_backup*' }).Count
if (-not $AvecBackups) { $sel = $sel | Where-Object { $_.Nom -notlike '_backup*' } }
if ($Motif)  { $sel = $sel | Where-Object { $_.Nom -match $Motif } }
if ($Tables) {
    $voulues = $Tables | ForEach-Object { $_.ToLower() }
    $sel = $sel | Where-Object { $voulues -contains $_.Nom.ToLower() }
}
$sel = @($sel)
Write-Host ("{0} table(s) à inspecter." -f $sel.Count)
Write-Host ''

# ── Inspection ───────────────────────────────────────────────────────
$sommaire = New-Object System.Collections.ArrayList
$detail   = New-Object System.Collections.ArrayList
$idx = 0

foreach ($t in $sel) {
    $idx++
    $nom = $t.Nom
    Write-Host ("[{0}/{1}] {2}" -f $idx, $sel.Count, $nom)
    $cite = Get-NomCite $nom

    # Nombre de lignes
    $nbLignes = '-'
    if (-not $SansComptage) {
        try {
            $rsc = $conn.Execute("SELECT COUNT(*) FROM $cite")
            $nbLignes = [string]$rsc.Fields.Item(0).Value
            $rsc.Close()
        } catch {
            $nbLignes = 'erreur'
        }
    }

    # Colonnes + échantillon, en une seule requête
    $colNoms  = New-Object System.Collections.ArrayList
    $colTypes = New-Object System.Collections.ArrayList
    $lignes   = New-Object System.Collections.ArrayList
    $erreur   = $null

    try {
        $rsd = New-Object -ComObject ADODB.Recordset
        $rsd.MaxRecords = [Math]::Max($Echantillon, 1)
        # adOpenForwardOnly = 0, adLockReadOnly = 1, adCmdText = 1
        $rsd.Open("SELECT * FROM $cite", $conn, 0, 1, 1)

        for ($i = 0; $i -lt $rsd.Fields.Count; $i++) {
            $f = $rsd.Fields.Item($i)
            [void]$colNoms.Add([string]$f.Name)
            [void]$colTypes.Add((Get-TypeLisible -Code ([int]$f.Type) -Taille ([int]$f.DefinedSize)))
        }

        while ((-not $rsd.EOF) -and ($lignes.Count -lt $Echantillon)) {
            $vals = New-Object System.Collections.ArrayList
            for ($i = 0; $i -lt $rsd.Fields.Count; $i++) {
                $v = $null
                try { $v = $rsd.Fields.Item($i).Value } catch { $v = '<illisible>' }
                [void]$vals.Add((Format-Cellule $v))
            }
            [void]$lignes.Add($vals)
            $rsd.MoveNext()
        }
        $rsd.Close()
    } catch {
        $erreur = $_.Exception.Message -replace "`r`n", ' '
        if ($erreur.Length -gt 200) { $erreur = $erreur.Substring(0, 200) }
    }

    $ancre = ($nom.ToLower() -replace '[^a-z0-9]+', '-')

    if ($erreur) {
        [void]$sommaire.Add("| ``$nom`` | $($t.Type) | $nbLignes | erreur |")
        [void]$detail.Add("### ``$nom``$([Environment]::NewLine)$([Environment]::NewLine)Lecture impossible : $erreur$([Environment]::NewLine)")
        continue
    }

    [void]$sommaire.Add("| [``$nom``](#$ancre) | $($t.Type) | $nbLignes | $($colNoms.Count) |")

    $bloc = New-Object System.Collections.ArrayList
    [void]$bloc.Add("### ``$nom``")
    [void]$bloc.Add('')
    [void]$bloc.Add("Type : $($t.Type) — lignes : $nbLignes — colonnes : $($colNoms.Count)")
    [void]$bloc.Add('')
    [void]$bloc.Add('| # | Colonne | Type |')
    [void]$bloc.Add('|---:|---|---|')
    for ($i = 0; $i -lt $colNoms.Count; $i++) {
        [void]$bloc.Add("| $($i+1) | ``$($colNoms[$i])`` | $($colTypes[$i]) |")
    }
    if ($lignes.Count -gt 0) {
        [void]$bloc.Add('')
        [void]$bloc.Add('Extrait :')
        [void]$bloc.Add('')
        [void]$bloc.Add('| ' + ($colNoms -join ' | ') + ' |')
        [void]$bloc.Add('|' + ('---|' * $colNoms.Count))
        foreach ($l in $lignes) {
            [void]$bloc.Add('| ' + ($l -join ' | ') + ' |')
        }
    }
    [void]$bloc.Add('')
    [void]$detail.Add(($bloc -join [Environment]::NewLine))
}

$conn.Close()

# ── Rapport ──────────────────────────────────────────────────────────
$entete = New-Object System.Collections.ArrayList
[void]$entete.Add('# Inventaire de la base HFSQL `sifa_cs`')
[void]$entete.Add('')
[void]$entete.Add("Généré le $(Get-Date -Format 'dd/MM/yyyy HH:mm') — lecture seule.")
[void]$entete.Add('')
[void]$entete.Add("Source : ``$(($ConnStr -split 'extended')[0].Trim())``")
[void]$entete.Add('')
[void]$entete.Add("Objets vus par le schéma : $($toutes.Count) — inspectés ici : $($sel.Count)" + $(if (-not $AvecBackups) { " (tables ``_backup_`` exclues : $nbBackups)" } else { '' }))
[void]$entete.Add('')
[void]$entete.Add('## Sommaire')
[void]$entete.Add('')
[void]$entete.Add('| Table | Type | Lignes | Colonnes |')
[void]$entete.Add('|---|---|---:|---:|')

$contenu = ($entete -join [Environment]::NewLine) + [Environment]::NewLine +
           ($sommaire -join [Environment]::NewLine) + [Environment]::NewLine +
           [Environment]::NewLine + '## Détail des tables' + [Environment]::NewLine +
           [Environment]::NewLine + ($detail -join [Environment]::NewLine)

$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($Sortie, $contenu, $utf8)

Write-Host ''
Write-Host "Rapport écrit : $Sortie" -ForegroundColor Green
Write-Host 'Relis-le avant de le partager : il contient des extraits de données réelles.' -ForegroundColor DarkGray
