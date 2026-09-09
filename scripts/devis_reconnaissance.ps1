<#
    Reconnaissance du dossier des devis — lecture seule, sans reseau, sans cle API.

    Jumeau PowerShell de scripts/devis_reconnaissance.py, sur le meme modele que
    inspect_of_access.ps1 / .py. Il existe parce que Python n'est pas installe
    sur tous les postes qui voient le partage des commerciaux, et qu'un
    diagnostic qui exige d'abord d'installer un interpreteur n'est plus un
    diagnostic.

    Il repond aux deux questions que seul le vrai dossier peut trancher :

      1. l'agent quotidien ne ramasse que l'annee en cours, en se fiant au NOM
         des sous-dossiers. Si l'arborescence n'est pas rangee par annee, ce
         filtre ecarte tout, ou n'ecarte rien — silencieusement dans les deux cas ;
      2. quand un devis ne porte pas de nom de client lisible, faut-il le deduire
         du dossier qui le contient ? Cela depend de ce que sont ces dossiers.

    N'envoie rien, n'ecrit rien dans le partage, ne demande aucune cle, et n'a
    pas besoin que le serveur soit a jour. A lancer AVANT tout deploiement.

        .\devis_reconnaissance.ps1
        .\devis_reconnaissance.ps1 -Dossier "\\serveur\PSEGARD\Devis etiquettes"
        .\devis_reconnaissance.ps1 -Rapport reco.txt

    Ecrit pour Windows PowerShell 5.1 : pas d'operateur ternaire, pas de && ni
    de ??, ASCII uniquement dans les textes du script (la console 5.1 rend mal
    l'Unicode). Les noms de dossiers, eux, sont affiches tels quels — le
    rapport ecrit en UTF-8 les restitue correctement meme si la console les
    abime.
#>

[CmdletBinding()]
param(
    # Le vrai dossier porte un accent. Il est ecrit ici en point de code
    # plutot qu'en clair : un .ps1 sans BOM est decode en ANSI par PowerShell
    # 5.1, et le chemin par defaut serait « Devis Ã©tiquettes » — introuvable.
    # Le fichier EST enregistre avec un BOM, ceci est la ceinture en plus des
    # bretelles, et cela survit a un copier-coller a travers un editeur.
    [string]$Dossier = ("U:\PSEGARD\Devis " + [char]0xE9 + "tiquettes"),
    [string]$Rapport = "",
    [int]$Echantillon = 15
)

$ErrorActionPreference = 'Continue'

# NOM EN UN SEUL MORCEAU, ET DIFFERENT DU COMPTEUR. PowerShell ne distingue
# pas la casse des variables : $EXTENSIONS (la liste) et $extensions (le
# compteur par extension) etaient LA MEME variable. Le compteur, initialise a
# @{}, ecrasait la liste avant la premiere comparaison — resultat, aucune
# extension n'etait reconnue et le script annoncait « 0 devis exploitables »
# sur un dossier qui en contenait des milliers, en les rangeant tous dans
# « extension non lue ». Un faux negatif silencieux, exactement ce qu'un
# outil de diagnostic ne doit jamais produire.
$EXT_LUES = @('.xlsx', '.xlsm', '.xls', '.pdf', '.png', '.jpg', '.jpeg')
$MOIS = @('janvier','fevrier','mars','avril','mai','juin','juillet','aout',
          'septembre','octobre','novembre','decembre',
          'jan','fev','avr','juil','sept','oct','nov','dec')

$script:Lignes = New-Object System.Collections.Generic.List[string]

function Write-L {
    param([string]$Texte = "")
    $script:Lignes.Add($Texte)
    Write-Host $Texte
}

function Remove-Accents {
    param([string]$Texte)
    if ([string]::IsNullOrEmpty($Texte)) { return "" }
    $n = $Texte.Normalize([Text.NormalizationForm]::FormD)
    $sb = New-Object Text.StringBuilder
    foreach ($c in $n.ToCharArray()) {
        if ([Globalization.CharUnicodeInfo]::GetUnicodeCategory($c) -ne
            [Globalization.UnicodeCategory]::NonSpacingMark) {
            [void]$sb.Append($c)
        }
    }
    return $sb.ToString()
}

function Get-AnneeDossier {
    # Meme lecture que l'agent : une annee plausible n'importe ou dans le nom.
    # « Devis 2026 » compte autant que « 2026 ».
    param([string]$Nom)
    foreach ($m in [regex]::Matches([string]$Nom, '(\d{4})')) {
        $a = [int]$m.Groups[1].Value
        if ($a -ge 1990 -and $a -le 2099) { return $a }
    }
    return $null
}

function Test-EstDate {
    # « 2026 », « Devis 2025 », « 03 - Mars », « T1 » : une date, pas un client.
    param([string]$Nom)
    if ($Nom -eq '(racine)') { return $false }
    $brut = (Remove-Accents $Nom).ToLower().Trim()
    if ($null -ne (Get-AnneeDossier $brut)) { return $true }
    foreach ($m in $MOIS) { if ($brut.Contains($m)) { return $true } }
    $noyau = [regex]::Replace($brut, '[^a-z0-9]', '')
    if ($noyau -match '^\d{1,2}$') { return $true }
    if ($noyau -match '^(t[1-4]|s[0-5]?\d)$') { return $true }
    return $false
}

# ─── Verification du chemin ───────────────────────────────────────────────────
if (-not (Test-Path -LiteralPath $Dossier -PathType Container)) {
    Write-Host "Dossier introuvable : $Dossier"
    Write-Host "Si c'est un lecteur mappe (U:), essayer le chemin UNC complet."
    exit 2
}
# Le separateur vient du systeme plutot que d'un '\' en dur : le script doit
# pouvoir etre eprouve ailleurs que sur Windows avant d'y etre lance.
$SEP = [IO.Path]::DirectorySeparatorChar
$Racine = (Resolve-Path -LiteralPath $Dossier).ProviderPath.TrimEnd($SEP)

# ─── Parcours ─────────────────────────────────────────────────────────────────
Write-Host "Lecture de $Racine ..."
$erreurs = @()
$tout = Get-ChildItem -LiteralPath $Racine -Recurse -File -Force `
        -ErrorAction SilentlyContinue -ErrorVariable +erreurs

$fichiers = New-Object System.Collections.Generic.List[object]
$nbParExt = @{}
$autresExt  = @{}
$verrous = 0
$vides   = 0
$profondeurs = @{}
$parents = @{}
$niveau1 = @{}

foreach ($f in $tout) {
    # Fichiers de travail d'Excel : « ~$devis.xlsx » est un verrou, pas un devis.
    if ($f.Name.StartsWith('~$') -or $f.Name.StartsWith('.~')) { $verrous++; continue }
    $ext = $f.Extension.ToLower()
    if ($EXT_LUES -notcontains $ext) {
        $cle = $ext
        if ([string]::IsNullOrEmpty($cle)) { $cle = '(sans extension)' }
        if ($autresExt.ContainsKey($cle)) { $autresExt[$cle]++ } else { $autresExt[$cle] = 1 }
        continue
    }
    if ($f.Length -le 0) { $vides++; continue }

    $rel = $f.FullName.Substring($Racine.Length).TrimStart($SEP)
    $segments = @($rel.Split($SEP))
    $prof = $segments.Count - 1          # nombre de dossiers au-dessus du fichier

    $fichiers.Add([pscustomobject]@{
        Rel = $rel.Replace($SEP,'/'); Taille = $f.Length; Date = $f.LastWriteTime })

    if ($nbParExt.ContainsKey($ext)) { $nbParExt[$ext]++ } else { $nbParExt[$ext] = 1 }
    if ($profondeurs.ContainsKey($prof)) { $profondeurs[$prof]++ } else { $profondeurs[$prof] = 1 }

    $p1 = '(racine)'
    if ($prof -ge 1) { $p1 = $segments[0] }
    if ($niveau1.ContainsKey($p1)) { $niveau1[$p1]++ } else { $niveau1[$p1] = 1 }

    $par = '(racine)'
    if ($prof -ge 1) { $par = $segments[$segments.Count - 2] }
    if ($parents.ContainsKey($par)) { $parents[$par]++ } else { $parents[$par] = 1 }
}

$total = $fichiers.Count
$anneeCourante = (Get-Date).Year

# ─── Rapport ──────────────────────────────────────────────────────────────────
$barre = ('=' * 72)
Write-L $barre
Write-L "RECONNAISSANCE - $Racine"
Write-L ("{0} - lecture seule, rien n'a ete modifie" -f (Get-Date -Format 'dd/MM/yyyy HH:mm'))
Write-L $barre

Write-L ""
Write-L "1. CE QUE CONTIENT LE DOSSIER"
Write-L ("   {0} devis exploitables." -f $total)
if ($total -eq 0) {
    Write-L "   AUCUN fichier lisible. Verifier le chemin, ou les droits du compte"
    Write-L "   qui lance ce script (une tache planifiee ne voit pas les lecteurs"
    Write-L "   mappes d'une session ouverte : preferer le chemin UNC complet)."
}
foreach ($e in ($nbParExt.GetEnumerator() | Sort-Object Value -Descending)) {
    Write-L ("     {0,-8} {1,6}" -f $e.Key, $e.Value)
}
if ($autresExt.Count -gt 0) {
    Write-L "   Ignores (extension non lue par le serveur) :"
    foreach ($e in ($autresExt.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 8)) {
        Write-L ("     {0,-16} {1,6}" -f $e.Key, $e.Value)
    }
}
if ($verrous -gt 0) {
    Write-L ("   {0} verrou(s) Excel '~`$' ignore(s) - normal, des classeurs sont ouverts." -f $verrous)
}
if ($vides -gt 0) { Write-L ("   {0} fichier(s) de 0 octet ignore(s)." -f $vides) }

Write-L ""
Write-L "2. LA FORME DE L'ARBRE  (repond au filtre 'annee en cours')"
if ($profondeurs.Count -eq 0) {
    Write-L "   Rien a mesurer."
} else {
    foreach ($k in ($profondeurs.Keys | Sort-Object)) {
        $lib = "$k niveau(x) sous la racine"
        if ($k -eq 0) { $lib = "a la racine" }
        Write-L ("     {0,-28} {1,6} devis" -f $lib, $profondeurs[$k])
    }
}

Write-L ""
Write-L "   Premier niveau, dossier par dossier :"
$avecAnnee = 0; $sansAnnee = 0; $gardes = 0
$listeN1 = @($niveau1.GetEnumerator() | Sort-Object Value -Descending)
foreach ($e in ($listeN1 | Select-Object -First 40)) {
    $nom = $e.Key
    $n = $e.Value
    if ($nom -eq '(racine)') {
        $verdict = "toujours pris (fichiers a la racine)"
    } else {
        $an = Get-AnneeDossier $nom
        if ($null -eq $an) {
            $verdict = "PAS D'ANNEE LUE -> toujours pris"
            $sansAnnee++; $gardes += $n
        } elseif ($an -lt $anneeCourante) {
            $verdict = "annee $an -> ECARTE par la passe quotidienne"
            $avecAnnee++
        } else {
            $verdict = "annee $an -> pris"
            $avecAnnee++; $gardes += $n
        }
    }
    $court = $nom
    if ($court.Length -gt 34) { $court = $court.Substring(0, 34) }
    Write-L ("     {0,-34} {1,5} devis  |  {2}" -f $court, $n, $verdict)
}
if ($listeN1.Count -gt 40) {
    Write-L ("     ... et {0} autre(s) dossier(s)." -f ($listeN1.Count - 40))
}

Write-L ""
Write-L ("   VERDICT : {0} dossier(s) de premier niveau portent une annee lisible," -f $avecAnnee)
Write-L ("             {0} n'en portent pas." -f $sansAnnee)
if ($avecAnnee -eq 0 -and $total -gt 0) {
    Write-L "             >>> L'arborescence n'est PAS rangee par annee. Le filtre"
    Write-L "                 'annee en cours' ne filtrera rien : la passe du soir"
    Write-L "                 relira tout le partage chaque nuit. A remplacer par le"
    Write-L "                 filtre sur la date de modification (--jours), deja en"
    Write-L "                 place, et a lancer avec --annee-min -1."
} elseif ($avecAnnee -gt 0 -and $sansAnnee -gt 0) {
    Write-L "             >>> Arborescence MIXTE. Les dossiers sans annee seront"
    Write-L "                 toujours relus. Verifier la liste ci-dessus avant de"
    Write-L "                 planifier la tache."
} elseif ($avecAnnee -gt 0) {
    Write-L ("             >>> Rangement par annee confirme : la passe quotidienne ne")
    Write-L ("                 lira que {0} devis au lieu de {1}." -f $gardes, $total)
}

Write-L ""
Write-L "3. D'OU POURRAIT VENIR LE NOM DU CLIENT"
Write-L "   Pour chaque devis, le dossier qui le contient. Si cette colonne"
Write-L "   ressemble a des noms de clients, on prend le dossier ; si elle"
Write-L "   ressemble a des annees ou des mois, on laisse le champ vide"
Write-L "   plutot que d'y mettre une description de produit."
Write-L ""
Write-L "   Les 15 dossiers parents les plus frequents :"
foreach ($e in ($parents.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 15)) {
    $court = $e.Key
    if ($court.Length -gt 40) { $court = $court.Substring(0, 40) }
    Write-L ("     {0,-40} {1,5} devis" -f $court, $e.Value)
}
$distincts = $parents.Count
$sousDate = 0
foreach ($e in $parents.GetEnumerator()) {
    if (Test-EstDate $e.Key) { $sousDate += $e.Value }
}
Write-L ""
Write-L ("   {0} dossier(s) parent(s) distinct(s) pour {1} devis." -f $distincts, $total)
if ($total -gt 0 -and $sousDate -ge ($total * 0.6)) {
    Write-L ("   >>> {0} devis sur {1} sont ranges sous un dossier qui est une DATE" -f $sousDate, $total)
    Write-L "       (annee ou mois), pas un client. Le repli par nom de dossier"
    Write-L "       ecrirait '2026' dans la colonne Client : laisser vide."
} elseif ($total -gt 0 -and $distincts -le 3) {
    Write-L "   >>> Trop peu de dossiers parents pour porter des noms de clients :"
    Write-L "       le repli par nom de dossier n'apporterait rien. Laisser vide."
} elseif ($total -gt 0 -and $distincts -ge [Math]::Max(8, $total * 0.05)) {
    Write-L "   >>> Beaucoup de dossiers parents distincts, et peu ressemblent a"
    Write-L "       des dates : ils portent probablement un client ou une affaire."
    Write-L "       Le repli a du sens."
} elseif ($total -gt 0) {
    Write-L "   >>> Cas intermediaire : lire la liste ci-dessus et trancher a l'oeil."
}

Write-L ""
Write-L ("4. ECHANTILLON  (les {0} devis modifies le plus recemment)" -f $Echantillon)
foreach ($f in ($fichiers | Sort-Object Date -Descending | Select-Object -First $Echantillon)) {
    $chemin = $f.Rel
    if ($chemin.Length -gt 88) { $chemin = $chemin.Substring(0, 88) }
    Write-L ("     {0}  -  {1} Ko  -  {2}" -f $chemin,
             [int]($f.Taille / 1024), $f.Date.ToString('dd/MM/yyyy'))
}

Write-L ""
Write-L "5. VOLUME"
if ($total -gt 0) {
    $somme = ($fichiers | Measure-Object -Property Taille -Sum).Sum
    $maxi  = ($fichiers | Measure-Object -Property Taille -Maximum).Maximum
    Write-L ("     {0:N1} Mo au total, {1} Ko en moyenne, {2} Ko pour le plus gros." -f
             ($somme / 1MB), [int]($somme / $total / 1024), [int]($maxi / 1024))
    $limite = (Get-Date).AddDays(-30)
    $recents = @($fichiers | Where-Object { $_.Date -ge $limite }).Count
    Write-L ("     {0} devis modifie(s) dans les 30 derniers jours - c'est l'ordre" -f $recents)
    Write-L "     de grandeur de ce que la passe du soir aura a traiter."
}

if ($erreurs.Count -gt 0) {
    Write-L ""
    Write-L ("6. CE QUI N'A PAS PU ETRE LU  ({0})" -f $erreurs.Count)
    foreach ($e in ($erreurs | Select-Object -First 10)) {
        Write-L ("     {0}" -f $e.Exception.Message)
    }
    if ($erreurs.Count -gt 10) {
        Write-L ("     ... et {0} autre(s)." -f ($erreurs.Count - 10))
    }
}

Write-L ""
Write-L $barre

if ($Rapport -ne "") {
    # UTF-8 : les noms de dossiers accentues doivent rester lisibles dans le
    # fichier meme quand la console les abime a l'affichage.
    $script:Lignes | Out-File -FilePath $Rapport -Encoding UTF8
    Write-Host ("Rapport ecrit dans {0}" -f (Resolve-Path -LiteralPath $Rapport).ProviderPath)
}
