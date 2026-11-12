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

   Le métrage est arrondi au mètre SUPÉRIEUR : c'est ce que font les OF
   Access récents (1 796,6 → 1 797), et une bobine trop courte ne se rattrape
   pas en fin de tirage.

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

# Cases que le calcul remplit. L'écran ne les écrase plus dès qu'un humain
# les a touchées.
CHAMPS_CALCULES = (
    "metrage", "qte_bobines", "nb_mandrins", "nb_levees", "nb_tubes", "nb_cartons",
    "qte_adhesif_g", "qte_adhesif_kg",
)

_TUBE_RE = re.compile(r"\btube\s*(\d+(?:[.,]\d+)?)\s*[x×]", re.IGNORECASE)
# Désignation MyStock : « Tube carton Ø 40 mm, Lg. 1500 mm, ép. 4 mm ».
_TUBE_LG_RE = re.compile(r"\b(?:lg|long(?:ueur)?)\.?\s*:?\s*(\d[\d\s\u202f]*(?:[.,]\d+)?)\s*mm",
                         re.IGNORECASE)
# Conditionnement de la fiche : « Bobine de 1 000 étiquettes ».
_BOBINE_DE_RE = re.compile(r"^\s*bobines?\s+de\s+(\d[\d\s\u202f.]*)\s*[ée]tiquettes?\b",
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
    que l'OF imprime mot pour mot. Rien d'autre n'est deviné : « Paravent de
    1000 plis de 4 étiquettes » ne dit pas un nombre par bobine."""
    lu = _nombre(fiche.get("nb_etiq_bobin"))
    if lu:
        return lu, "fiche"
    m = _BOBINE_DE_RE.search(str(fiche.get("conditionnement") or ""))
    if m:
        n = _nombre(re.sub(r"[\s\u202f.]", "", m.group(1)))
        if n:
            return n, "conditionnement"
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

    qam = qte_au_mille(fiche)
    metrage = None
    if qam:
        metrage = math.ceil(round(q * qam / 1000.0, 6))
        out["metrage"] = metrage
    else:
        manques.append("Qté au mille absente de la fiche — métrage non calculé.")

    eb, origine_eb = etiquettes_par_bobine(fiche)
    bobines = None
    if eb:
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

        tube = longueur_tube(fiche.get("mandrin_dia"))
        ml = _nombre(fiche.get("mandrin_longueur"))
        if tube and ml:
            par_tube = math.floor(round(tube / ml, 6))
            if par_tube >= 1:
                out["nb_tubes"] = math.ceil(round(bobines / par_tube, 6))

    g = _nombre(grammage)
    lz = _nombre(laize)
    if g:
        out["qte_adhesif_g"] = g
        if metrage and lz:
            out["qte_adhesif_kg"] = round(g * metrage * lz / 1_000_000, 3)

    out["_manques"] = manques
    return out


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


def proposer(conn, fiche_id: int, qte_etiquettes: Any = None) -> Optional[Dict[str, Any]]:
    """L'OF tel qu'il découle de la fiche `fiche_id`. None si elle n'existe pas."""
    row = conn.execute(
        "SELECT * FROM fiches_techniques WHERE id = ?", (fiche_id,)
    ).fetchone()
    if not row:
        return None
    fiche = dict(row)

    champs: Dict[str, Any] = {}
    provenance: Dict[str, str] = {}

    def poser(col: str, val: Any, origine: str) -> None:
        if _vide(val):
            return
        champs[col] = val
        provenance[col] = origine

    poser("reference", _cle_produit(fiche.get("reference")), "fiche")
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

    grammage = grammage_adhesif(conn, champs.get("adhesif_label"))
    calc = calculer_quantites(fiche, qte_etiquettes,
                              laize=champs.get("laize"), grammage=grammage)
    manques = calc.pop("_manques", [])
    if calc.get("_info"):
        manques.insert(0, calc.pop("_info"))
    for col, val in calc.items():
        poser(col, val, "adhésif d'un OF précédent" if col == "qte_adhesif_g" else "calcul")

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
        "manques": manques,
    }
