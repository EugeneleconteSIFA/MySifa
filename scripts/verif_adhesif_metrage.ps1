# Verification metrage + adhesif : jointure complete t_of -> fiches -> Adhesif
# ---------------------------------------------------------------------------
# Reproduit la formule de la vue Access [adhesif_necessaire_sans_date_prev]
# sur des OF dont on connait l'impression papier, pour la valider avant de la
# porter dans MySifa.
#
#     powershell -ExecutionPolicy Bypass -File .\verif_adhesif_metrage.ps1
#
# Lecture seule.

param(
    [string] $DbPath = "\\IDEFIX\sifa_pub\Fiches techniques Access\of.mdb",
    [string] $Ofs    = "9931861,9931953"
)

$ErrorActionPreference = "Stop"
$script:Sortie = New-Object System.Collections.ArrayList
function Log($t = "") { Write-Host $t; [void]$script:Sortie.Add([string]$t) }
function Sep($t) { Log ""; Log ("=" * 78); Log $t; Log ("=" * 78) }

# Valeurs relevees sur les impressions papier, pour comparaison automatique.
$Papier = @{
    "9931861" = @{ metrage = 7124;  laize = 470; grammage = 19; kg = 63.6; mille = 10.8 }
    "9931953" = @{ metrage = 10226; laize = 333; grammage = $null; kg = $null; mille = 50.8 }
}

$conn = New-Object -ComObject ADODB.Connection
$ouvert = $false
foreach ($p in @("Microsoft.ACE.OLEDB.16.0", "Microsoft.ACE.OLEDB.12.0", "Microsoft.Jet.OLEDB.4.0")) {
    try { $conn.Open("Provider=$p;Data Source=$DbPath;"); $ouvert = $true; break } catch {}
}
if (-not $ouvert) { Log "Aucun provider Access disponible."; exit 1 }

function Query($sql) {
    $rs = New-Object -ComObject ADODB.Recordset
    $rs.Open($sql, $conn, 3, 1)
    return $rs
}
function Num($v) {
    if ($v -eq $null) { return $null }
    $t = ("$v" -replace '[^0-9,\.\-]', '') -replace ',', '.'
    $d = 0.0
    if ([double]::TryParse($t, [Globalization.NumberStyles]::Float,
        [Globalization.CultureInfo]::InvariantCulture, [ref]$d)) { return $d }
    return $null
}
function Cmp($libelle, $calcule, $attendu) {
    if ($attendu -eq $null) { Log ("    {0,-22} calcule {1,-14} (rien sur le papier)" -f $libelle, $calcule); return }
    if ($calcule -eq $null) { Log ("    {0,-22} NON CALCULABLE   papier {1}" -f $libelle, $attendu); return }
    $ecart = [Math]::Abs($calcule - $attendu)
    $tol   = [Math]::Max(0.06, [Math]::Abs($attendu) * 0.005)
    $verdict = if ($ecart -lt $tol) { "OK" } else { "ECART" }
    Log ("    {0,-22} calcule {1,-14} papier {2,-10} -> {3}" -f `
         $libelle, [Math]::Round($calcule, 3), $attendu, $verdict)
}

# --- 1. La table Adhesif --------------------------------------------
Sep "1. TABLE [Adhesif] - 12 premieres lignes"
$r = Query "SELECT TOP 12 * FROM [Adhesif]"
$colsAdh = @()
for ($i = 0; $i -lt $r.Fields.Count; $i++) { $colsAdh += $r.Fields.Item($i).Name }
Log ("  Colonnes : " + ($colsAdh -join ", "))
Log ""
while (-not $r.EOF) {
    $vals = @()
    for ($i = 0; $i -lt $r.Fields.Count; $i++) {
        $vals += "$($colsAdh[$i])=$($r.Fields.Item($i).Value)"
    }
    Log ("  " + ($vals -join "  |  "))
    $r.MoveNext()
}
$r.Close()

# --- 2. Jointure complete par OF ------------------------------------
Sep "2. JOINTURE t_of -> t_fiches_techniques -> Adhesif"

$liste = ($Ofs -split ',' | ForEach-Object { "'" + $_.Trim() + "'" }) -join ","
$sql = @"
SELECT t_of.numero_of,
       t_of.format,
       t_of.choix_laize_matiere,
       t_of.theorique_quantite,
       t_of.theorique_metrage_necessaire,
       f.matsupport,
       f.matglassine,
       f.matlaize,
       f.matlaizestandard,
       f.matadhesif,
       f.matquantite,
       f.matquantite_type,
       f.matquantite_unite,
       f.nbfront,
       a.reference,
       a.grammage
FROM   (t_of LEFT JOIN t_fiches_techniques AS f ON t_of.format = f.reference)
       LEFT JOIN Adhesif AS a ON f.matadhesif = a.type
WHERE  t_of.numero_of IN ($liste)
"@

$rs = Query $sql
if ($rs.EOF) { Log "  Aucune ligne. La jointure t_of.format = f.reference ne matche pas." }

while (-not $rs.EOF) {
    $g = @{}
    for ($i = 0; $i -lt $rs.Fields.Count; $i++) { $g[$rs.Fields.Item($i).Name] = $rs.Fields.Item($i).Value }

    Log ""
    Log ("  OF " + $g["numero_of"] + "  (" + $g["format"] + ")")
    Log ("  " + ("-" * 74))
    foreach ($k in @("choix_laize_matiere","theorique_quantite","theorique_metrage_necessaire",
                     "matsupport","matglassine","matlaize","matlaizestandard","nbfront",
                     "matadhesif","matquantite","matquantite_type","matquantite_unite",
                     "reference","grammage")) {
        $v = if ($g[$k] -eq $null -or "$($g[$k])".Trim() -eq "") { "<vide>" } else { $g[$k] }
        Log ("    {0,-32} = {1}" -f $k, $v)
    }

    $pap      = $Papier["$($g['numero_of'])"]
    $metrage  = Num $g["theorique_metrage_necessaire"]
    $lStd     = Num $g["matlaizestandard"]
    $lOpt     = Num $g["matlaize"]
    $gram     = Num $g["grammage"]
    $mille    = Num $g["matquantite"]

    Log ""
    Log "    -- Controles --"
    Cmp "metrage stocke"      $metrage $pap.metrage
    Cmp "qte au mille"        $mille   $pap.mille
    Cmp "grammage adhesif"    $gram    $pap.grammage

    # Quelle laize correspond a celle imprimee ?
    Log ("    laize standard         = {0,-14} laize optionnelle = {1,-10} papier {2}" -f `
         $lStd, $lOpt, $pap.laize)
    $bonne = if ($lOpt -ne $null -and $pap.laize -ne $null -and [Math]::Abs($lOpt - $pap.laize) -lt 1) { "matlaize (OPTIONNELLE)" }
             elseif ($lStd -ne $null -and $pap.laize -ne $null -and [Math]::Abs($lStd - $pap.laize) -lt 1) { "matlaizestandard" }
             else { "AUCUNE des deux" }
    Log ("    -> la laize imprimee vient de : {0}" -f $bonne)

    # Formule Access, avec chacune des deux laizes
    if ($metrage -ne $null -and $gram -ne $null) {
        if ($lStd -ne $null) { Cmp "kg via laize standard"  (($gram * $metrage * $lStd) / 1000000) $pap.kg }
        if ($lOpt -ne $null) { Cmp "kg via laize optionn."  (($gram * $metrage * $lOpt) / 1000000) $pap.kg }
    }

    # Coherence metrage <-> quantite au mille
    if ($mille -ne $null -and $g["theorique_quantite"] -ne $null) {
        $recalc = (Num $g["theorique_quantite"]) / 1000 * $mille
        Cmp "metrage recalcule"  $recalc $pap.metrage
    }

    $rs.MoveNext()
}
$rs.Close()

# --- 3. Combien d'OF perdent leur fiche technique ? ------------------
Sep "3. FIABILITE DE LA JOINTURE (500 derniers OF)"
try {
    $r = Query @"
SELECT COUNT(*) AS n
FROM   (SELECT TOP 500 t_of.format FROM t_of ORDER BY t_of.id_of DESC) AS o
       LEFT JOIN t_fiches_techniques AS f ON o.format = f.reference
WHERE  f.reference IS NULL
"@
    Log ("  OF sans fiche technique correspondante : " + $r.Fields.Item(0).Value + " / 500")
    $r.Close()
} catch { Log "  (test impossible : $_)" }

try {
    $r = Query @"
SELECT COUNT(*) AS n
FROM   ((SELECT TOP 500 t_of.format FROM t_of ORDER BY t_of.id_of DESC) AS o
       LEFT JOIN t_fiches_techniques AS f ON o.format = f.reference)
       LEFT JOIN Adhesif AS a ON f.matadhesif = a.type
WHERE  a.grammage IS NULL
"@
    Log ("  OF sans grammage adhesif resolu       : " + $r.Fields.Item(0).Value + " / 500")
    $r.Close()
} catch { Log "  (test impossible : $_)" }

$conn.Close()
$chemin = Join-Path $PSScriptRoot "rapport_verif_adhesif.txt"
$script:Sortie -join "`r`n" | Out-File -FilePath $chemin -Encoding UTF8
Log ""
Log "Rapport ecrit dans : $chemin"
