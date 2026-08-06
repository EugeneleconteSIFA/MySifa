# Inspection des bases Access SIFA - diagnostic metrage / adhesif
# ----------------------------------------------------------------
# Aucune installation requise : utilise ADODB, present nativement sur Windows.
# Le script ne fait que des SELECT, il ne modifie rien.
#
# 1) La table des OF (defaut) :
#     powershell -ExecutionPolicy Bypass -File .\inspect_of_access.ps1
#
# 2) La fiche technique du meme OF :
#     powershell -ExecutionPolicy Bypass -File .\inspect_of_access.ps1 -Table fiches_techniques `
#         -DbPath "\\IDEFIX\sifa_pub\Fiches techniques Access\sifa_fiches_techniques.mdb" `
#         -KeyColumn reference -KeyValue "24/0023" -Valeurs "470,10.8,19,2028,660000"
#
# 3) La table des adhesifs :
#     powershell -ExecutionPolicy Bypass -File .\inspect_of_access.ps1 -Table Adhesif -KeyColumn "" -Apercu 10
#
# NB : -Valeurs est une CHAINE separee par des virgules (les decimales
#      s'ecrivent avec un point). Avec -File, PowerShell passe tout en texte.

param(
    [string] $DbPath    = "\\IDEFIX\sifa_pub\Fiches techniques Access\of.mdb",
    [string] $Table     = "t_of",
    [string] $KeyColumn = "numero_of",
    [string] $KeyValue  = "9931861",
    # Valeurs lues sur l'impression papier de l'OF 9931861 :
    # qte etiq, bobines, metrage, qte/mille, laize, nb levees,
    # cartons, mandrins, grammage adhesif, kg adhesif, pignon
    [string] $Valeurs   = "660000,165,7124,10.8,470,33,55,165,19,63.6,68",
    [int]    $Apercu    = 0     # >0 : affiche N lignes de la table au lieu d'une cle
)

$ErrorActionPreference = "Stop"
$script:Sortie = New-Object System.Collections.ArrayList

function Log($txt = "") {
    Write-Host $txt
    [void]$script:Sortie.Add([string]$txt)
}
function Sep($titre) {
    Log ""
    Log ("=" * 78)
    Log $titre
    Log ("=" * 78)
}
function ToNum($v) {
    # Retourne [double] ou $null. Gere "10,8", "1 234", "10.8".
    if ($v -eq $null) { return $null }
    $t = ("$v" -replace '\s', '') -replace ',', '.'
    $d = 0.0
    if ([double]::TryParse($t, [Globalization.NumberStyles]::Float,
                           [Globalization.CultureInfo]::InvariantCulture, [ref]$d)) { return $d }
    return $null
}

$Attendus = @()
foreach ($x in ($Valeurs -split ',')) {
    $n = ToNum $x
    if ($n -ne $null) { $Attendus += $n }
}

Log "Base   : $DbPath"
Log "Table  : $Table"
if ($KeyColumn) { Log "Cle    : $KeyColumn = $KeyValue" }
Log "PowerShell : $($PSVersionTable.PSVersion)  |  Process 64 bits : $([Environment]::Is64BitProcess)"

# --- Connexion ------------------------------------------------------
$conn = New-Object -ComObject ADODB.Connection
$ouvert = $false
foreach ($p in @("Microsoft.ACE.OLEDB.16.0", "Microsoft.ACE.OLEDB.12.0", "Microsoft.Jet.OLEDB.4.0")) {
    try { $conn.Open("Provider=$p;Data Source=$DbPath;"); Log "Provider   : $p"; $ouvert = $true; break }
    catch { }
}
if (-not $ouvert) {
    Log "Aucun provider Access disponible (conflit 32/64 bits ?)."
    Log 'Repli : C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe -ExecutionPolicy Bypass -File .\inspect_of_access.ps1'
    exit 1
}

function Query($sql) {
    $rs = New-Object -ComObject ADODB.Recordset
    $rs.Open($sql, $conn, 3, 1)   # adOpenStatic, adLockReadOnly
    return $rs
}

# --- 1. Colonnes de la table ----------------------------------------
Sep "1. COLONNES DE [$Table]"
$rs = Query "SELECT TOP 1 * FROM [$Table]"
$noms = @()
for ($i = 0; $i -lt $rs.Fields.Count; $i++) { $noms += $rs.Fields.Item($i).Name }
$types = @{
    2="Entier";3="Entier long";4="Simple";5="Double";6="Monetaire";7="Date";
    11="Booleen";72="GUID";128="Binaire";130="Texte";131="Decimal";
    133="Date";135="Date/Heure";200="Texte";202="Texte";203="Memo";205="Objet OLE"
}
Log "$($rs.Fields.Count) colonne(s)"
Log ""
for ($i = 0; $i -lt $rs.Fields.Count; $i++) {
    $f = $rs.Fields.Item($i)
    $t = if ($types.ContainsKey([int]$f.Type)) { $types[[int]$f.Type] } else { "type $($f.Type)" }
    Log ("  {0,-4}{1,-36}{2,-16}{3}" -f ($i + 1), $f.Name, $t, $f.DefinedSize)
}
$rs.Close()

# --- 2. Contenu ------------------------------------------------------
$ligne = [ordered]@{}

if ($Apercu -gt 0) {
    Sep "2. APERCU DES $Apercu PREMIERES LIGNES DE [$Table]"
    $r = Query "SELECT TOP $Apercu * FROM [$Table]"
    $k = 0
    while (-not $r.EOF) {
        $k++
        Log ""
        Log "  --- ligne $k ---"
        for ($i = 0; $i -lt $r.Fields.Count; $i++) {
            $f = $r.Fields.Item($i)
            if ($f.Value -ne $null -and "$($f.Value)".Trim() -ne "") {
                $v = "$($f.Value)"
                if ($v.Length -gt 120) { $v = $v.Substring(0, 120) + "..." }
                Log ("    {0,-34} = {1}" -f $f.Name, $v)
            }
        }
        $r.MoveNext()
    }
    $r.Close()
}
elseif ($KeyColumn) {
    Sep "2. CONTENU COMPLET DE $KeyColumn = $KeyValue"
    $rs = $null
    $echap = $KeyValue -replace "'", "''"
    foreach ($clause in @("[$KeyColumn] = '$echap'", "[$KeyColumn] = $KeyValue")) {
        try { $rs = Query "SELECT * FROM [$Table] WHERE $clause"; break } catch { }
    }

    if ($rs -eq $null -or $rs.EOF) {
        Log "  Aucun enregistrement trouve."
        try {
            $r = Query "SELECT TOP 5 [$KeyColumn] FROM [$Table]"
            $ex = @(); while (-not $r.EOF) { $ex += $r.Fields.Item(0).Value; $r.MoveNext() }; $r.Close()
            Log ("  Exemples de [$KeyColumn] : " + ($ex -join " | "))
        } catch {}
    } else {
        for ($i = 0; $i -lt $rs.Fields.Count; $i++) {
            $f = $rs.Fields.Item($i)
            $ligne[$f.Name] = $f.Value
            $v = if ($f.Value -eq $null -or "$($f.Value)".Trim() -eq "") { "<vide>" } else { "$($f.Value)" }
            if ($v.Length -gt 200) { $v = $v.Substring(0, 200) + "..." }
            Log ("  {0,-36} = {1}" -f $f.Name, $v)
        }
        $rs.Close()

        # --- 3. Rapprochement avec l'impression papier --------------
        # Tolerance 1 % : l'etat Access ARRONDIT a l'affichage.
        # Ex. "Quantite au mille 10,8" vaut ~10,7939 en base.
        Sep "3. RAPPROCHEMENT AVEC L'IMPRESSION PAPIER (tolerance 1 %)"
        foreach ($attendu in $Attendus) {
            $hits = @()
            foreach ($n in $ligne.Keys) {
                $d = ToNum $ligne[$n]
                if ($d -eq $null) { continue }
                $tol = [Math]::Max(0.51, [Math]::Abs($attendu) * 0.01)
                if ([Math]::Abs($d - $attendu) -lt $tol) { $hits += "$n=$($ligne[$n])" }
            }
            if ($hits.Count -gt 0) { Log ("  {0,-12} -> {1}" -f $attendu, ($hits -join " | ")) }
            else { Log ("  {0,-12} -> AUCUNE COLONNE" -f $attendu) }
        }

        Sep "3bis. COLONNES TEXTE NON VIDES"
        foreach ($n in $ligne.Keys) {
            $v = $ligne[$n]
            if ($v -ne $null -and $v -is [string] -and $v.Trim() -ne "") {
                $t = $v.Trim(); if ($t.Length -gt 150) { $t = $t.Substring(0, 150) + "..." }
                Log ("  {0,-36} = {1}" -f $n, $t)
            }
        }
    }
}

# --- 4. SQL des vues metrage / adhesif -------------------------------
Sep "4. SQL DES REQUETES ACCESS (metrage, adhesif, matiere)"
Log "  C'est ici que se trouve la formule officielle, deja ecrite cote SIFA."
try {
    $rsV = $conn.OpenSchema(23)   # adSchemaViews
    while (-not $rsV.EOF) {
        $nom = "$($rsV.Fields.Item('TABLE_NAME').Value)"
        if ($nom -match '(?i)metrage|m.trage|adhesif|adh.sif|matiere|mati.re') {
            $def = "$($rsV.Fields.Item('VIEW_DEFINITION').Value)"
            Log ""
            Log ("  --- " + $nom + " " + ("-" * [Math]::Max(3, 66 - $nom.Length)))
            foreach ($l in ($def -split "`r?`n")) { Log "    $l" }
        }
        $rsV.MoveNext()
    }
    $rsV.Close()
} catch {
    Log "  (lecture des vues impossible : $_)"
}

# --- 5. Taux de remplissage -----------------------------------------
Sep "5. TAUX DE REMPLISSAGE (500 dernieres lignes)"
Log "  Une colonne vide a 100 % n'est jamais saisie -> inutile de la lire."
Log ""
$total = 0
try { $r = Query "SELECT COUNT(*) AS n FROM (SELECT TOP 500 * FROM [$Table])"
      $total = [int]$r.Fields.Item(0).Value; $r.Close() } catch {}

foreach ($n in $noms) {
    $rempli = $null
    foreach ($cond in @("<> 0", "<> ''", "IS NOT NULL")) {
        try {
            $where = if ($cond -eq "IS NOT NULL") { "[$n] IS NOT NULL" }
                     else { "[$n] IS NOT NULL AND [$n] $cond" }
            $r = Query "SELECT COUNT(*) AS n FROM (SELECT TOP 500 [$n] FROM [$Table]) WHERE $where"
            $rempli = [int]$r.Fields.Item(0).Value; $r.Close(); break
        } catch {}
    }
    if ($rempli -ne $null -and $total -gt 0) {
        $pct = [Math]::Round(100 * $rempli / $total)
        Log ("  {0,-36} {1,3} %  {2}" -f $n, $pct, ("#" * [Math]::Floor($pct / 5)))
    } else {
        Log ("  {0,-36}   ?" -f $n)
    }
}

$conn.Close()

$suffixe = ($Table -replace '[^A-Za-z0-9]', '')
$chemin  = Join-Path $PSScriptRoot "rapport_access_$suffixe.txt"
$script:Sortie -join "`r`n" | Out-File -FilePath $chemin -Encoding UTF8
Log ""
Log "Rapport ecrit dans : $chemin"
