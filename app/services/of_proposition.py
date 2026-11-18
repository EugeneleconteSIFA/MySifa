"""
Proposer un OF à partir d'une fiche technique (12/11/2026).

C'est le geste de l'ADV dans Access (formulaire « Nouvel OF ») : un numéro
d'OF, une fiche technique choisie dans la liste « Format », puis le délai
client et le nombre d'étiquettes. Tout le reste de l'OF découle de la fiche.

Deux familles de cases
----------------------
1. Ce qui décrit le PRODUIT est recopié de la fiche : machine, laize,
   matière, glassine, adhésif, outils, mandrin, conditionnement, cartons,
   palette, particularités (`of_depuis_fiche.CORRESPONDANCES`, plus les
   références MyStock et le format).
2. Ce qui dépend de la QUANTITÉ se calcule. Les formules sont celles des OF
   Access, vérifiées le 12/11/2026 sur les 142 OF Access dont la référence
   retrouve une fiche :

       métrage    = nb étiquettes × qté au mille ÷ 1000      139 / 142
       bobines    = ⌈ nb étiquettes ÷ nb étiq. par bobine ⌉   60 / 65
       mandrins   = bobines                                   141 / 141
       levées     = ⌈ bobines ÷ nb fronts de l'outil ⌉        relevé sur les OF qui
                    ont une fiche (8 000 ÷ 10 = 800, 1 120 ÷ 9 = 124,4 → 125)
       cartons    = ⌈ bobines ÷ nb bobines par carton ⌉       140 / 141
       tubes      = ⌈ mandrins ÷ ⌊ long. du tube ÷ long. du mandrin ⌋ ⌉
                                                              134 / 138
       adhésif kg = grammage × métrage × laize ÷ 1 000 000   (vue Access
                    [adhesif_necessaire_sans_date_prev], cf. access_sync_of.py)

   Le métrage est arrondi au mètre le plus proche, comme l'OF Access imprimé
   (7 124,04 → 7 124 ; 1 796,6 → 1 797).

   La quantité proposée depuis une commande est arrondie à la LEVÉE COMPLÈTE
   (`arrondir_a_la_levee`) : c'est ce que fait l'ADV dans Access.

La longueur du tube se LIT dans le libellé du mandrin (« Tube 1500x40 ») :
une bague (« Bague 63,7x25 ») ne se coupe pas dans un tube, et il n'y a
alors pas de tubes à compter. Aucune longueur n'est supposée.

Le grammage de l'adhésif est dans la table `Adhesif` d'Access, que MySifa ne
reçoit pas. Il est repris du dernier OF qui porte le MÊME libellé d'adhésif :
sur les OF Access, un libellé n'a jamais eu qu'un grammage (« Permanent
2028Y - 19 » → 19 g, 247 OF). Un libellé sans référence (« Permanent ») n'a
pas de grammage dans Access non plus : la case reste vide, comme sur le
papier.

Lecture seule : rien n'est écrit en base. La création passe par
`POST /api/of`, qui marque les champs saisis et part en `valide = 0`.
"""

from __future__ import annotations

import json
import math
import re
from typing import Any, Dict, List, Optional

from app.services.of_depuis_fiche import CORRESPONDANCES

# Références MyStock : (colonne de la fiche, colonne de l'OF). La colonne
# texte de l'OF découle de l'id côté serveur (_appliquer_references).
REFERENCES = (
    ("support_ref_id",  "matiere_ref_id"),
    ("glassine_ref_id", "glassine_ref_id"),
    ("adhesif_ref_id",  "adhesif_ref_id"),
    ("carton_ref_id",   "carton_ref_id"),
    ("mandrin_ref_id",  "mandrin_ref_id"),
    ("palette_ref_id",  "palette_ref_id"),
)

# Texte imprimé sur l'OF : (id fiche, texte fiche, id OF, texte OF). Access
# imprime le libellé de la fiche (« THERMIQUE PRO », « Permanent 2028Y - 19 »),
# pas la désignation MyStock (comparaison du 18/11/2026).
LIBELLES_FICHE = (
    ("support_ref_id",  "support",      "matiere_ref_id",  "matiere"),
    ("glassine_ref_id", "glassine",     "glassine_ref_id", "glassine"),
    ("adhesif_ref_id",  "adhesif",      "adhesif_ref_id",  "adhesif_label"),
    ("carton_ref_id",   "cartons",      "carton_ref_id",   "cartons_type"),
    ("mandrin_ref_id",  "mandrin_dia",  "mandrin_ref_id",  "mandrins_dia"),
    ("palette_ref_id",  "palette_type", "palette_ref_id",  "palette_type"),
)

# Cases que le calcul remplit. L'écran ne les écrase plus dès qu'un humain
# les a touchées.
CHAMPS_CALCULES = (
    "metrage", "qte_bobines", "nb_mandrins", "nb_levees", "nb_tubes", "nb_cartons",
    "qte_adhesif_g", "qte_adhesif_kg",
)

# Cases dont la valeur de l'OF prend le pas sur la fiche une fois corrigées.
CHAMPS_SOURCES = (
    "nb_fronts", "laize", "qte_au_mille", "conditionnement",
    "mandrins_dia", "mandrin_longueur",
)
CHAMPS_CORRIGEABLES = frozenset(CHAMPS_CALCULES) | frozenset(CHAMPS_SOURCES)

_TUBE_RE = re.compile(r"\btube\s*(\d+(?:[.,]\d+)?)\s*[x×]", re.IGNORECASE)
# Désignation MyStock : « Tube carton Ø 40 mm, Lg. 1500 mm, ép. 4 mm ».
_TUBE_LG_RE = re.compile(r"\b(?:lg|long(?:ueur)?)\.?\s*:?\s*(\d[\d\s\u202f]*(?:[.,]\d+)?)\s*mm",
                         re.IGNORECASE)
# Conditionnement de la fiche : « Bobine de 1 000 étiquettes ».
_BOBINE_DE_RE = re.compile(r"^\s*bobines?\s+de\s+(\d[\d\s\u202f.]*)\s*[ée]tiquettes?\b",
                           re.IGNORECASE)
# « Paravent de 1 000 plis de 4 étiquettes », « Paquet de 1 000 plis de 1
# étiquette » : un paravent (ou paquet) compte plis × étiquettes, et Access le
# traite comme une bobine — OF 9931861 : 660 000 ÷ 4 000 = 165 « bobines »,
# 165 mandrins, 33 levées, 55 cartons (comparaison du 17/11/2026).
_PLIS_RE = re.compile(r"^\s*(?:paravents?|paquets?)\s+de\s+(\d[\d\s\u202f.]*)\s*plis\s+de\s+(\d[\d\s\u202f.]*)\s*[ée]tiquettes?\b",
                      re.IGNORECASE)


def _nombre(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        n = float(str(v).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _vide(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return not v.strip()
    return False


def longueur_tube(mandrin: Any) -> Optional[float]:
    """« Tube 1500x40 » → 1500. Une bague ou un libellé libre → None."""
    txt = str(mandrin or "")
    m = _TUBE_RE.search(txt)
    if m:
        return _nombre(m.group(1))
    if re.search(r"\btube\b", txt, re.IGNORECASE):
        m = _TUBE_LG_RE.search(txt)
        if m:
            return _nombre(re.sub(r"[\s\u202f]", "", m.group(1)))
    return None


def etiquettes_par_bobine(fiche: Dict[str, Any]):
    """(nombre, origine). La fiche le porte (`nbetiquette` d'Access) ; à
    défaut on le lit dans son conditionnement, « Bobine de 1 000 étiquettes »,
    que l'OF imprime mot pour mot. Un paravent ou un paquet compte plis ×
    étiquettes (« Paravent de 1 000 plis de 4 étiquettes » = 4 000), comme
    Access. Rien d'autre n'est deviné."""
    lu = _nombre(fiche.get("nb_etiq_bobin"))
    if lu:
        return lu, "fiche"
    cond = str(fiche.get("conditionnement") or "")
    m = _BOBINE_DE_RE.search(cond)
    if m:
        n = _nombre(re.sub(r"[\s\u202f.]", "", m.group(1)))
        if n:
            return n, "conditionnement"
    m = _PLIS_RE.search(cond)
    if m:
        plis = _nombre(re.sub(r"[\s\u202f.]", "", m.group(1)))
        par = _nombre(re.sub(r"[\s\u202f.]", "", m.group(2)))
        if plis and par:
            return plis * par, "conditionnement"
    return None, None


def qte_au_mille(fiche: Dict[str, Any]) -> Optional[float]:
    """Mètres de matière pour mille étiquettes.

    La fiche la porte (`matquantite` d'Access). À défaut, c'est le calcul
    d'Access : longueur du module ÷ nombre de fronts de l'OUTIL — jamais
    `mod_nb_front`, qui vaut 1 sur presque toutes les fiches.
    """
    lue = _nombre(fiche.get("qte_au_mille"))
    if lue:
        return lue
    longueur = _nombre(fiche.get("mod_longueur"))
    fronts = _nombre(fiche.get("outil1_nb_front"))
    if longueur and fronts:
        return longueur / fronts
    return None


# ─── Produits vendus au mètre ────────────────────────────────────────────────
#
# Un rouleau sans découpe à compter (« Bobine de 45 ml », format « 58 x 45
# ml ») n'a pas de nombre d'étiquettes par bobine. Dans Access, l'ADV tape
# alors le NOMBRE DE ROULEAUX dans « Nb étiquettes », et l'OF en découle —
# relevé sur l'OF 9932835 (122/0022) : 630 rouleaux → 630 bobines, 126 levées
# (5 fronts), métrage 5 418 = 630 × 8,6 (qté au mille de la fiche, lue ici
# par rouleau). Décision du 17/11/2026 : MySifa fait comme Access.

_AU_METRE_RE = re.compile(r"^\s*(?:bobines?|rouleaux?)\s+de\s+[\d\s.,]+\s*ml\b", re.IGNORECASE)


def vendu_au_metre(fiche: Optional[Dict[str, Any]]) -> bool:
    """Le produit se compte en rouleaux d'une longueur, pas en étiquettes."""
    if not fiche or _nombre(fiche.get("nb_etiq_bobin")):
        return False
    return bool(_AU_METRE_RE.search(str(fiche.get("conditionnement") or "")))


def _nb_tubes(fiche: Dict[str, Any], mandrins: Any) -> Optional[int]:
    """⌈ mandrins ÷ ⌊ long. du tube ÷ long. du mandrin ⌋ ⌉, None sans tube."""
    n = _nombre(mandrins)
    tube = longueur_tube(fiche.get("mandrin_dia"))
    ml = _nombre(fiche.get("mandrin_longueur"))
    if not (n and tube and ml):
        return None
    par_tube = math.floor(round(tube / ml, 6))
    return math.ceil(round(n / par_tube, 6)) if par_tube >= 1 else None


def calculer_quantites(fiche: Dict[str, Any], qte_etiquettes: Any,
                       laize: Any = None,
                       grammage: Any = None) -> Dict[str, Any]:
    """Les quantités de l'OF pour `qte_etiquettes` étiquettes.

    Rend {colonne: valeur} pour ce qui a pu être calculé, et
    `_manques` : ce qui manque à la fiche pour calculer le reste.
    """
    out: Dict[str, Any] = {}
    manques: List[str] = []
    q = _nombre(qte_etiquettes)
    if not q:
        return {"_manques": []}

    au_metre = vendu_au_metre(fiche)
    qam = qte_au_mille(fiche)
    metrage = None
    if qam:
        # Au mètre, la quantité compte des rouleaux et la « qté au mille » de
        # la fiche se lit par rouleau (Access : 630 × 8,6 = 5 418 m).
        # Arrondi au mètre LE PLUS PROCHE, comme l'OF Access imprimé :
        # 9931861 = 7 124,04 → 7 124 ; 9931953 = 10 226,04 → 10 226 ;
        # 9932770 L2 = 1 796,6 → 1 797. (Jusqu'au 17/11/2026 on arrondissait
        # au-dessus, ce qui donnait 7 125.) Le millimètre d'abord : la fiche
        # stocke la qté au mille en simple précision (8,600000381…).
        brut = round(q * qam / (1.0 if au_metre else 1000.0), 3)
        metrage = int(math.floor(brut + 0.5))
        out["metrage"] = metrage
    else:
        manques.append("Qté au mille absente de la fiche — métrage non calculé.")

    eb, origine_eb = etiquettes_par_bobine(fiche)
    bobines = None
    if au_metre:
        bobines = math.ceil(round(q, 6))
        out["qte_bobines"] = bobines
        out["nb_mandrins"] = bobines
    elif eb:
        if origine_eb == "conditionnement":
            out["_info"] = ("Nb étiquettes par bobine absent de la fiche — "
                            "%d lu dans le conditionnement." % eb)
        bobines = math.ceil(round(q / eb, 6))
        out["qte_bobines"] = bobines
        out["nb_mandrins"] = bobines
    else:
        manques.append("Nb étiquettes par bobine absent de la fiche — bobines non calculées.")

    if bobines:
        # Une levée sort une bobine par front de l'outil : arrondi au-dessus,
        # la dernière levée est entamée même incomplète. Jamais mod_nb_front.
        fronts = _nombre(fiche.get("outil1_nb_front"))
        if fronts:
            out["nb_levees"] = math.ceil(round(bobines / fronts, 6))
        else:
            manques.append("Nb de fronts de l'outil absent de la fiche — levées non calculées.")

        bc = _nombre(fiche.get("nb_bobines_carton"))
        if bc:
            out["nb_cartons"] = math.ceil(round(bobines / bc, 6))
        else:
            manques.append("Nb bobines par carton absent de la fiche — cartons non calculés.")

        tubes = _nb_tubes(fiche, bobines)
        if tubes is not None:
            out["nb_tubes"] = tubes

    g = _nombre(grammage)
    lz = _nombre(laize)
    if g:
        out["qte_adhesif_g"] = g
        if metrage and lz:
            out["qte_adhesif_kg"] = round(g * metrage * lz / 1_000_000, 3)

    out["_manques"] = manques
    return out


def lire_corriges(brut: Any) -> List[str]:
    """Les cases corrigées, depuis une liste ou son JSON. Inconnues écartées.

    Étiquettes, bobines et levées forment une seule chaîne : une seule mène.
    Si bobines et levées arrivent ensemble, les levées mènent.
    """
    if isinstance(brut, str):
        try:
            brut = json.loads(brut)
        except ValueError:
            return []
    if not isinstance(brut, (list, tuple)):
        return []
    corriges = {str(c) for c in brut if str(c) in CHAMPS_CORRIGEABLES}
    if "nb_levees" in corriges:
        corriges.discard("qte_bobines")
    return sorted(corriges)


def fiche_selon_of(fiche: Dict[str, Any], valeurs: Optional[Dict[str, Any]],
                   corriges: Any = None) -> Dict[str, Any]:
    """La fiche, vue à travers ce que l'OF porte : la base de tout recalcul.

    Corriger la quantité au mille d'un OF doit changer son métrage, pas
    seulement la case. Une valeur vide de l'OF laisse celle de la fiche.
    """
    f = dict(fiche)
    v = valeurs or {}
    corr = set(lire_corriges(corriges))
    fronts = _nombre(v.get("nb_fronts"))
    if fronts:
        f["outil1_nb_front"] = fronts
    # Un OF Access porte la qté au mille arrondie à une décimale (10,9 pour
    # 10,885) : sans correction, seul un vrai écart l'emporte sur la fiche.
    qam = _nombre(v.get("qte_au_mille"))
    lue = qte_au_mille(fiche)
    if qam and ("qte_au_mille" in corr or not lue or abs(qam - lue) > 0.06):
        f["qte_au_mille"] = qam
    cond = str(v.get("conditionnement") or "").strip()
    if cond and cond.lower() != str(fiche.get("conditionnement") or "").strip().lower():
        essai = {"conditionnement": cond}
        par_bobine = etiquettes_par_bobine(essai)[0]
        if par_bobine or vendu_au_metre(essai):
            f["conditionnement"] = cond
            f["nb_etiq_bobin"] = par_bobine
    if str(v.get("mandrins_dia") or "").strip():
        f["mandrin_dia"] = v.get("mandrins_dia")
    if _nombre(v.get("mandrin_longueur")):
        f["mandrin_longueur"] = _nombre(v.get("mandrin_longueur"))
    return f


def quantite_menee(fiche: Dict[str, Any], valeurs: Dict[str, Any], corriges: Any, qte: Any) -> Any:
    """Le nombre d'étiquettes quand l'ADV a corrigé les levées ou les bobines.

    `fiche` est déjà vue à travers l'OF (`fiche_selon_of`). Sans correction, ou
    sans de quoi convertir, la quantité reste celle de l'OF.
    """
    corr = lire_corriges(corriges)
    par_bobine = 1.0 if vendu_au_metre(fiche) else etiquettes_par_bobine(fiche)[0]
    if not par_bobine:
        return qte
    bobines = None
    if "nb_levees" in corr:
        levees, fronts = _nombre(valeurs.get("nb_levees")), _nombre(fiche.get("outil1_nb_front"))
        bobines = levees * fronts if levees and fronts else None
    elif "qte_bobines" in corr:
        bobines = _nombre(valeurs.get("qte_bobines"))
    return int(round(bobines * par_bobine)) if bobines else qte


def appliquer_corrections(calc: Dict[str, Any], fiche: Dict[str, Any], valeurs: Dict[str, Any],
                          corriges: Any, laize: Any, grammage: Any) -> None:
    """Une case corrigée garde sa valeur, et ce qui en dépend la suit."""
    corr = lire_corriges(corriges)
    for col in CHAMPS_CALCULES:
        if col in corr and valeurs.get(col) not in (None, ""):
            calc[col] = valeurs[col]
    if "nb_mandrins" in corr and "nb_tubes" not in corr:
        tubes = _nb_tubes(fiche, calc.get("nb_mandrins"))
        if tubes is not None:
            calc["nb_tubes"] = tubes
    g, lz, metrage = _nombre(calc.get("qte_adhesif_g") or grammage), _nombre(laize), _nombre(calc.get("metrage"))
    if "qte_adhesif_kg" not in corr and g and lz and metrage:
        calc["qte_adhesif_kg"] = round(g * metrage * lz / 1_000_000, 3)


def arrondir_a_la_levee(fiche: Dict[str, Any], qte: Any) -> Optional[Dict[str, Any]]:
    """La quantité commandée, portée à la levée complète supérieure.

    Une levée sort une bobine par front : l'ADV lance donc un nombre entier de
    levées. Relevé le 18/11/2026 sur 26 OF Access : 13 arrondis ainsi, 7 déjà
    ronds, 3 doublés par choix de l'ADV, 3 en cartons non vérifiables.
    OF 9931861 : 650 000 ÷ (4 000 × 5) = 32,5 → 33 levées → 660 000.

    None quand la fiche ne dit pas le nombre de fronts ou d'étiquettes par
    bobine : la quantité commandée reste alors telle quelle.
    """
    q = _nombre(qte)
    fronts = _nombre(fiche.get("outil1_nb_front"))
    par_bobine = 1.0 if vendu_au_metre(fiche) else etiquettes_par_bobine(fiche)[0]
    if not (q and fronts and par_bobine):
        return None
    par_levee = par_bobine * fronts
    levees = math.ceil(round(q / par_levee, 6))
    return {"commandee": int(round(q)), "proposee": int(round(levees * par_levee)),
            "levees": levees, "par_levee": int(round(par_levee))}


def libelles_de_la_fiche(conn, valeurs: Dict[str, Any], fiche_id: Any) -> None:
    """Remet sur l'OF le libellé de sa fiche, à la place de la désignation
    MyStock, pour chaque matière dont l'OF porte la référence de la fiche.

    Le serveur écrit ce texte, jamais le client. La référence reste posée : les
    besoins matières et le déstockage continuent de lire l'id. Une référence
    changée à la main garde la désignation de la matière choisie.
    """
    try:
        fid = int(fiche_id or 0)
    except (TypeError, ValueError):
        return
    if not fid:
        return
    row = conn.execute("SELECT * FROM fiches_techniques WHERE id = ?", (fid,)).fetchone()
    if not row:
        return
    fiche = dict(row)
    for id_ft, txt_ft, id_of, txt_of in LIBELLES_FICHE:
        ref = valeurs.get(id_of)
        if ref and ref == fiche.get(id_ft) and not _vide(fiche.get(txt_ft)):
            valeurs[txt_of] = fiche[txt_ft]


def ref_adhesif_precedente(conn, libelle: Any) -> Optional[str]:
    """La réf. adhésif (« 2028Y ») du dernier OF qui porte ce libellé —
    Access la tire de sa table Adhesif, que MySifa ne reçoit pas."""
    lib = str(libelle or "").strip()
    if not lib:
        return None
    try:
        r = conn.execute(
            """SELECT ref_adhesif FROM of_imports
                WHERE LOWER(TRIM(adhesif_label)) = LOWER(?)
                  AND TRIM(COALESCE(ref_adhesif, '')) <> ''
                ORDER BY id DESC LIMIT 1""",
            (lib,),
        ).fetchone()
    except Exception:
        return None
    return str(r[0]).strip() if r else None


def grammage_adhesif(conn, libelle: Any) -> Optional[float]:
    """Grammage repris du dernier OF qui porte ce libellé d'adhésif."""
    lib = str(libelle or "").strip()
    if not lib:
        return None
    try:
        r = conn.execute(
            """SELECT qte_adhesif_g FROM of_imports
                WHERE LOWER(TRIM(adhesif_label)) = LOWER(?)
                  AND qte_adhesif_g > 0
                ORDER BY id DESC LIMIT 1""",
            (lib,),
        ).fetchone()
    except Exception:
        return None
    return _nombre(r[0]) if r else None


def _cle_produit(reference: Any) -> Optional[str]:
    """« 1183/0028 - DSI » → « 1183/0028 ». Une référence sans clé reste telle
    quelle : c'est la seule chose qu'on sache du produit."""
    brut = str(reference or "").strip()
    if not brut:
        return None
    try:
        from app.services.fiche_ref_parser import normalize_ref_produit
        cle = normalize_ref_produit(brut)
    except Exception:  # pragma: no cover
        cle = None
    return cle or brut


def proposer(conn, fiche_id: int, qte_etiquettes: Any = None,
             arrondir: bool = False, valeurs: Optional[Dict[str, Any]] = None,
             corriges: Any = None) -> Optional[Dict[str, Any]]:
    """L'OF tel qu'il découle de la fiche `fiche_id`. None si elle n'existe pas.

    `arrondir` : `qte_etiquettes` est la quantité commandée, le calcul part de
    la levée complète (`qte_proposee`, détail dans `arrondi`).
    `valeurs` et `corriges` : l'OF en cours de saisie, dont les calculs partent
    au lieu de repartir de la fiche seule."""
    row = conn.execute(
        "SELECT * FROM fiches_techniques WHERE id = ?", (fiche_id,)
    ).fetchone()
    if not row:
        return None
    fiche = dict(row)

    valeurs = valeurs or {}
    base_calcul = fiche_selon_of(fiche, valeurs, corriges)
    arrondi = arrondir_a_la_levee(base_calcul, qte_etiquettes) if arrondir else None
    if arrondi:
        qte_etiquettes = arrondi["proposee"]
    qte_etiquettes = quantite_menee(base_calcul, valeurs, corriges, qte_etiquettes)

    champs: Dict[str, Any] = {}
    provenance: Dict[str, str] = {}

    def poser(col: str, val: Any, origine: str) -> None:
        if _vide(val):
            return
        champs[col] = val
        provenance[col] = origine

    poser("reference", _cle_produit(fiche.get("reference")), "fiche")
    fronts_fiche = _nombre(fiche.get("outil1_nb_front"))
    if fronts_fiche:
        poser("nb_fronts", int(round(fronts_fiche)), "fiche")
    poser("format", fiche.get("format"), "fiche")
    for col_of, col_ft in CORRESPONDANCES:
        poser(col_of, fiche.get(col_ft), "fiche")
    for col_ft, col_of in REFERENCES:
        poser(col_of, fiche.get(col_ft), "fiche")

    # La fiche stocke la qté au mille en simple précision (2,7639999389…) :
    # on l'arrondit au dix-millième, la précision d'Access.
    qam = qte_au_mille(fiche)
    if qam:
        poser("qte_au_mille", round(qam, 4),
              "fiche" if _nombre(fiche.get("qte_au_mille")) else "calcul")

    adhesif = valeurs.get("adhesif_label") or champs.get("adhesif_label")
    grammage = grammage_adhesif(conn, adhesif)
    laize = _nombre(valeurs.get("laize")) or champs.get("laize")
    calc = calculer_quantites(base_calcul, qte_etiquettes, laize=laize, grammage=grammage)
    appliquer_corrections(calc, base_calcul, valeurs, corriges, laize, grammage)
    manques = calc.pop("_manques", [])
    if calc.get("_info"):
        manques.insert(0, calc.pop("_info"))
    for col, val in calc.items():
        poser(col, val, "adhésif d'un OF précédent" if col == "qte_adhesif_g" else "calcul")
    poser("ref_adhesif", ref_adhesif_precedente(conn, adhesif),
          "adhésif d'un OF précédent")

    return {
        "fiche": {
            "id": fiche.get("id"),
            "reference": fiche.get("reference"),
            "machine": fiche.get("machine"),
            "format": fiche.get("format"),
            "valide": bool(fiche.get("valide")),
        },
        "champs": champs,
        "provenance": provenance,
        "calcules": [c for c in CHAMPS_CALCULES if c in champs],
        "qte_proposee": int(round(_nombre(qte_etiquettes) or 0)) or None,
        # Absent quand la commande tombe déjà sur une levée complète.
        "arrondi": arrondi if arrondi and arrondi["proposee"] != arrondi["commandee"] else None,
        # La quantité se compte alors en rouleaux : l'écran renomme la case.
        "au_metre": vendu_au_metre(base_calcul),
        "manques": manques,
    }


# ─── Depuis les commandes cochées ────────────────────────────────────────────
#
# La commande dit QUEL produit, COMBIEN et POUR QUAND. Le code article d'une
# ligne de commande (« 1164/0066 ») est la clé produit de la fiche technique :
# vérifié sur tous les OF Access récents (9932770 L1/L2, 9932839-842,
# 9932856 L1-L8). Il suffit donc de cocher la commande pour retrouver la
# fiche — sauf quand le produit en a plusieurs (une par machine ou par laize,
# 152 produits sur 785) : c'est alors à l'ADV de choisir.
#
# Quantité : celle des lignes cochées, ou la quantité partielle saisie dans
# le sélecteur. Elle dépend ensuite de la fiche choisie : `proposer(arrondir=
# True)` la porte à la levée complète, et l'ADV peut revenir à la commande.
#
# Délai : la date de livraison de la ligne (`amjl`) — celle des OF 9932770 et
# 9932856. La plus proche quand plusieurs lignes sont cochées.

def _article_produit(code1: Any, code2: Any) -> Optional[str]:
    """« 1164/0066 », ou None pour une ligne qui n'est pas un produit
    (« FR/FRAIS_DE_CLICHE ») : code1 et code2 sont numériques sur un article."""
    a = str(code1 or "").strip()
    b = str(code2 or "").strip()
    if not (a.isdigit() and b.isdigit()):
        return None
    return "%s/%s" % (a, b)


def lire_commandes(lignes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Articles, quantité et délai des lignes de commande cochées.

    `lignes` : [{numero, ligne (None = commande entière), qte (partielle)}].
    Lecture seule du miroir RVGI ; miroir absent = résultat vide, jamais
    d'erreur.
    """
    choix: Dict[str, Dict[Any, Any]] = {}
    for l in lignes or []:
        num = str((l or {}).get("numero") or "").strip()
        if not num:
            continue
        ligne = l.get("ligne")
        try:
            ligne = int(ligne) if ligne not in (None, "") else None
        except (TypeError, ValueError):
            ligne = None
        choix.setdefault(num, {})[ligne] = _nombre(l.get("qte"))
    vide = {"articles": [], "qte_etiquettes": None, "delai_client": None, "lignes": []}
    if not choix:
        return vide
    try:
        from app.services import erp_mirror as miroir
        with miroir.get_erp_db() as c:
            tables = miroir.tables_presentes(c)
            if "cde_ligne" not in tables or "cde_entete" not in tables:
                return vide
            nums = sorted(choix)
            # INNER JOIN obligatoire : une commande à la corbeille laisse ses
            # lignes orphelines dans le miroir (règle RVGI du 28/08).
            rows = c.execute(
                "SELECT l.id AS id_ligne, CAST(l.numero AS TEXT) AS numero, l.ligne, l.code1, l.code2, "
                "       l.qte, l.cuv, l.des1, l.des2, l.des3, "
                "       substr(l.amjl, 1, 10) AS livraison, substr(l.amje, 1, 10) AS expedition "
                "  FROM cde_ligne l "
                "  JOIN cde_entete e ON e.numero = l.numero AND e.corbeille = 0 "
                " WHERE l.corbeille = 0 AND CAST(l.numero AS TEXT) IN (%s) "
                " ORDER BY l.numero, l.ligne" % ",".join("?" * len(nums)),
                nums,
            ).fetchall()
            unites = {}
            if "fic_ua" in tables:
                for u in c.execute("SELECT code, lib1, nombre FROM fic_ua WHERE corbeille = 0"):
                    unites[str(u["code"] or "").strip()] = (
                        str(u["lib1"] or "").strip(), _nombre(u["nombre"]) or 0.0)
    except Exception:
        return vide

    retenues = []
    for r in rows:
        num = r["numero"]
        sel = choix.get(num, {})
        try:
            ligne = int(r["ligne"]) if r["ligne"] is not None else None
        except (TypeError, ValueError):
            ligne = None
        if None in sel and len(sel) == 1:
            partielle = None              # commande entière
        elif ligne in sel:
            partielle = sel[ligne]
        else:
            continue
        article = _article_produit(r["code1"], r["code2"])
        if not article:
            continue
        qte = partielle if partielle else _nombre(r["qte"])
        unite, par_unite = unite_de_vente(r["cuv"], unites, r["des1"], r["des2"], r["des3"])
        m_rl = _ROULEAUX_TETE.search(str(r["des1"] or ""))
        retenues.append({"id": r["id_ligne"], "numero": num, "ligne": ligne, "article": article,
                         "qte": qte, "unite": unite, "par_unite": par_unite,
                         "rouleaux_par_unite": _entier_texte(m_rl.group(1)) if m_rl else None,
                         "livraison": (r["livraison"] or None),
                         "expedition": (r["expedition"] or None)})

    articles = sorted({x["article"] for x in retenues})
    dates = sorted(x["livraison"] for x in retenues if x["livraison"])
    expeditions = sorted(x["expedition"] for x in retenues if x.get("expedition"))
    return {
        "articles": articles,
        "qte_etiquettes": None,          # posée par quantite_etiquettes()
        "delai_client": dates[0] if dates else None,
        # Le délai des OF Access est la date de livraison 3 fois sur 4, la
        # date d'expédition parfois (43 commandes, 15/11/2026) : l'écran
        # propose la livraison et montre les deux, au choix d'un clic.
        "date_livraison": dates[0] if dates else None,
        "date_expedition": expeditions[0] if expeditions else None,
        "lignes": retenues,
    }


# ─── Unité de vente des lignes de commande ──────────────────────────────────
#
# RVGI compte une ligne dans son UNITÉ DE VENTE (`cuv` → `fic_ua`), pas en
# étiquettes. Constat du 15/11/2026 sur 9932858 : « B440/Etiquette 102 x
# 150 mm », 200 en unité 5 = Bobine — 200 BOBINES de 440, soit 88 000
# étiquettes. Lues comme 200 étiquettes, elles donnaient un OF de 11 m.
#
# Répartition des lignes de produit depuis 9932000 : Mille (11) 661, Carton
# (1, C) 464, Bobine (5) 87, et quelques paravents et planches.
#
#   - une unité « de prix » (Mille, Cent : `nombre` ≥ 100) : la quantité EST
#     un nombre d'étiquettes, le prix est au mille ;
#   - une unité contenant (Bobine, Carton, Paravent, Planche…) : la quantité
#     compte des contenants. Le nombre d'étiquettes par contenant se lit en
#     tête de désignation (« B440/ », « C12000/ », « C/60 000 », « P500/ »),
#     sinon dans ses phrases (« Bobine de 440 étiquettes »), sinon dans la
#     fiche technique (étiquettes par bobine, × bobines par carton).
#
# Rien n'est deviné au-delà : une quantité qu'on ne sait pas convertir est
# signalée, pas transformée.

# Le nombre doit compter des ÉTIQUETTES : « C50/rouleaux » (50 rouleaux par
# carton) ne dit pas combien d'étiquettes, et le prendre ferait un OF faux.
_PAR_UNITE_TETE = (
    re.compile(r"^\s*[A-Za-z]{1,2}\s*(\d[\d\s.\u202f]*)\s*/\s*[EeÉé]"),     # B440/Etiq  C12000/Etiq  P500/ Etiq
    re.compile(r"^\s*[A-Za-z]{1,2}\s*/\s*(\d[\d\s.\u202f]*\d)\s*[EeÉé]"),   # C/60 000 Eti  B/1000Etique
)
# « C32/Rouleaux » : 32 rouleaux par carton (produits vendus au mètre).
_ROULEAUX_TETE = re.compile(r"^\s*[A-Za-z]{1,2}\s*(\d[\d\s.\u202f]*)\s*/\s*rouleaux?", re.IGNORECASE)
_PAR_UNITE_PHRASE = re.compile(
    r"\b(?:bobines?|cartons?|paravents?|rouleaux?|planches?)\s+de\s+(\d[\d\s.\u202f]*)\s*(?:[ée]tiq|plis)",
    re.IGNORECASE)


def _entier_texte(brut: str) -> Optional[float]:
    return _nombre(re.sub(r"[\s.\u202f]", "", brut or ""))


def unite_de_vente(cuv: Any, unites: Dict[str, Any], *designations: Any):
    """(libellé de l'unité, étiquettes par unité ou None).

    1.0 pour une unité de prix (la quantité compte déjà des étiquettes)."""
    lib, nombre = unites.get(str(cuv or "").strip(), ("", 0.0))
    if nombre and nombre >= 100:
        return lib or "Mille", 1.0
    tete = str(designations[0] or "") if designations else ""
    for motif in _PAR_UNITE_TETE:
        m = motif.search(tete)
        if m:
            n = _entier_texte(m.group(1))
            if n:
                return lib or "unité", n
    for d in designations:
        m = _PAR_UNITE_PHRASE.search(str(d or ""))
        if m:
            n = _entier_texte(m.group(1))
            if n:
                return lib or "unité", n
    return lib or "unité", None


def quantite_etiquettes(lu: Dict[str, Any], fiche: Optional[Dict[str, Any]] = None):
    """(nombre d'étiquettes, messages) des lignes lues, unités converties.

    Une bobine ou un carton sans nombre dans la désignation prend celui de
    la fiche. Une ligne qu'on ne sait pas convertir est laissée de côté et
    nommée : la quantité proposée serait sinon fausse sans le dire."""
    total = 0.0
    messages: List[str] = []
    eb = etiquettes_par_bobine(fiche)[0] if fiche else None
    bc = _nombre((fiche or {}).get("nb_bobines_carton"))
    au_metre = vendu_au_metre(fiche)
    for x in lu.get("lignes") or []:
        q = x.get("qte")
        if not q:
            continue
        unite = (x.get("unite") or "").lower()
        if au_metre:
            # Au mètre, on compte des ROULEAUX : un rouleau par bobine, les
            # rouleaux par carton lus en tête de désignation (« C32/Rouleaux »)
            # ou dans la fiche.
            par = None
            if "carton" in unite:
                par = x.get("rouleaux_par_unite") or bc
            elif "mille" not in unite:
                par = 1.0
            if not par:
                messages.append("%s L%s : %s en « %s », nombre de rouleaux par %s inconnu — "
                                "quantité à saisir." % (x["numero"], x["ligne"], _texte_qte(q),
                                                       x.get("unite") or "unité", x.get("unite") or "unité"))
                continue
            total += q * par
            if par != 1.0:
                messages.append("%s L%s : %s %s de %s rouleaux." % (
                    x["numero"], x["ligne"], _texte_qte(q), (x.get("unite") or "unité").lower(),
                    _texte_qte(par)))
            continue
        par = x.get("par_unite")
        if not par and eb and "bobine" in unite:
            par = eb
        if not par and eb and bc and "carton" in unite:
            par = eb * bc
        if not par:
            messages.append("%s L%s : %s en « %s », nombre d'étiquettes par %s inconnu — "
                            "quantité à saisir." % (x["numero"], x["ligne"], _texte_qte(q),
                                                   x.get("unite") or "unité", x.get("unite") or "unité"))
            continue
        total += q * par
        if par != 1.0:
            messages.append("%s L%s : %s %s de %s étiquettes." % (
                x["numero"], x["ligne"], _texte_qte(q), (x.get("unite") or "unité").lower(),
                _texte_qte(par)))
    return (int(round(total)) if total else None), messages


def _texte_qte(v: Any) -> str:
    n = _nombre(v) or 0
    return ("{:,.0f}".format(n)).replace(",", " ") if n == int(n) else str(n)


def fiches_du_produit(conn, article: Any) -> List[Dict[str, Any]]:
    """Les fiches techniques d'un produit : « 1183/0028 », « 1183/0028 - DSI »…"""
    cle = _cle_produit(article)
    if not cle:
        return []
    rows = conn.execute(
        """SELECT id, reference, machine, format FROM fiches_techniques
            WHERE ref_produit_norm = ? OR TRIM(reference) = ?
               OR reference LIKE ? || ' %'
            ORDER BY reference""",
        (cle, cle, cle),
    ).fetchall()
    return [dict(r) for r in rows]


def depuis_commandes(conn, lignes: List[Dict[str, Any]],
                     sauf_of_id: Optional[int] = None) -> Dict[str, Any]:
    """Ce que les commandes cochées proposent pour l'OF : fiche(s), quantité,
    délai. Une fiche n'est proposée que si les lignes portent UN SEUL
    article — deux articles, c'est un OF par ligne (« 9932770 - L1 »)."""
    lu = lire_commandes(lignes)
    articles = lu["articles"]
    fiches = fiches_du_produit(conn, articles[0]) if len(articles) == 1 else []
    # Le nombre d'étiquettes par bobine d'un produit ne dépend pas de la
    # machine : la première fiche suffit à convertir une commande en bobines.
    fiche = None
    if fiches:
        r = conn.execute("SELECT * FROM fiches_techniques WHERE id = ?",
                         (fiches[0]["id"],)).fetchone()
        fiche = dict(r) if r else None
    qte, conversions = quantite_etiquettes(lu, fiche)
    # Le numéro tel que la création le donnera, suffixe compris : « 9932128/L1
    # (2) » quand un autre OF porte déjà le numéro (numero_of_libre, règle du
    # 16/11/2026). L'ADV le voit avant de créer, au lieu d'un refus.
    numero = None
    try:
        from app.services import rvgi_rattachement as ratt
        nommees, totaux = ratt.lignes_a_numeroter(lignes)
        base = ratt.proposer_reference(nommees, totaux)
        # En modification, l'OF lui-même ne compte pas comme « déjà pris » :
        # sans ça il se verrait proposer son propre numéro suffixé « (2) ».
        numero = ratt.numero_of_libre(conn, base, sauf_of_id=sauf_of_id) if base else None
    except Exception:
        numero = None
    return {
        "numero": numero,
        "au_metre": vendu_au_metre(fiche),
        "articles": articles,
        "article": articles[0] if len(articles) == 1 else None,
        "fiches": fiches,
        "qte_etiquettes": qte,
        "conversions": conversions,
        "date_livraison": lu.get("date_livraison"),
        "date_expedition": lu.get("date_expedition"),
        # Pour « Voir la commande » : l'id de la ligne ouvre sa fiche dans
        # l'écran Commandes de l'ERP (/erp#/commandes?fiche=commandes:<id>).
        "lignes": [{"id": x["id"], "numero": x["numero"], "ligne": x["ligne"],
                    "article": x["article"]} for x in lu.get("lignes") or []],
        "delai_client": lu["delai_client"],
    }


# ─── Concordance fiche / commandes ───────────────────────────────────────────
#
# Un OF rattaché à des commandes doit être fait avec la fiche d'un de leurs
# articles. Vérifié le 15/11/2026 sur les 55 OF Access récents qui portent à
# la fois un numéro de commande et une référence produit : 55 sur 55. Un écart
# n'est donc presque jamais voulu — et il ne se verrait pas : planning,
# besoins matières et déstockage suivraient la mauvaise fiche.
#
# Un OF = un produit (décision du 15/11/2026) : TOUTES les lignes cochées
# doivent porter l'article de la fiche. Plusieurs modèles imprimés ensemble
# sur la fiche de l'un d'eux (9932652 : fiche 1315/0003 pour 1315/0003, 0004
# et 0013) reste possible, mais c'est une exception qui se justifie : elle
# passe par le motif, comme tout écart.
#
# Rien à contrôler sans commande (stock, marché, reliquat), ni quand le miroir
# ne répond pas : on ne bloque jamais une création sur une panne de lecture.
# Le cas légitime (nouveau code article, fiche pas encore dupliquée) passe
# avec un motif, que la route d'écriture exige et journalise.

def controler_concordance(conn, commandes: List[Dict[str, Any]],
                          fiche_id: Any = None,
                          reference: Any = None) -> Dict[str, Any]:
    """{ok, verifiable, articles, message}. `ok` est vrai quand rien n'est
    vérifiable : l'absence de contrôle n'est pas un écart."""
    articles = lire_commandes(commandes)["articles"] if commandes else []
    res: Dict[str, Any] = {"ok": True, "verifiable": bool(articles),
                           "articles": articles, "message": None}
    if not articles:
        return res

    a_verifier = []   # (libellé, clé produit)
    if fiche_id:
        try:
            row = conn.execute(
                "SELECT reference FROM fiches_techniques WHERE id = ?", (int(fiche_id),)
            ).fetchone()
        except (TypeError, ValueError):
            row = None
        if row:
            a_verifier.append(("La fiche %s" % row["reference"], _cle_produit(row["reference"])))
    cle_ref = _cle_produit(reference)
    if cle_ref and cle_ref not in [c for _, c in a_verifier]:
        a_verifier.append(("La référence %s" % cle_ref, cle_ref))

    hors = [lib for lib, cle in a_verifier if cle not in articles]
    if hors:
        res["ok"] = False
        res["message"] = "%s ne correspond%s à aucun article des commandes cochées (%s)." % (
            " et ".join(hors), "ent" if len(hors) > 1 else "", ", ".join(articles))
        return res
    # Un seul produit : les lignes d'un autre article n'ont rien à faire là.
    cle_of = a_verifier[0][1] if a_verifier else None
    autres = [a for a in articles if cle_of and a != cle_of]
    if autres:
        res["ok"] = False
        res["message"] = ("Les lignes cochées portent %d articles (%s) : un OF ne couvre qu'un "
                          "produit. Faites un OF par article, ou indiquez le motif "
                          "(modèles imprimés ensemble…)." % (len(articles), ", ".join(articles)))
    return res
