"""MyAO — fiche produit tirée d'une fiche technique MyProd.

Une fiche produit MyAO peut naître de trois façons : vierge (produit neuf
chiffré en appel d'offre), depuis une fiche technique existante (produit déjà
fabriqué par SIFA), ou vierge puis rattachée plus tard à sa fiche technique,
une fois l'appel d'offre passé et le produit créé dans Access / MySifa.

Ce module traduit une ligne de ``fiches_techniques`` en morceau de fiche
produit (même forme que ``default_fiche()`` de ``ao_produit_fiche``) et sait
compléter une fiche produit sans jamais écraser ce qu'un humain y a saisi.

Deux précautions, reprises de ``.claude/rules/of-fiches-techniques.md`` :

- un zéro venu d'Access n'est pas une valeur — c'est une case vide ;
- ``eti_laize`` est la largeur de l'ÉTIQUETTE ; ``laize`` / ``laize_optimale``
  sont celles de la bobine matière, jamais à reporter dans l'étiquette.
"""
from __future__ import annotations

import re
from typing import Any

# Familles matière : colonne d'id de la fiche technique → chemin dans la fiche
# produit. La glassine, le carton et la palette sont des matières MyStock au
# même titre que le frontal.
_MATIERES = (
    ("support_ref_id", ("matiere", "frontal_id"), "frontal"),
    ("adhesif_ref_id", ("matiere", "adhesif_id"), "adhesif"),
    ("glassine_ref_id", ("matiere", "glassine_id"), "glassine"),
    ("carton_ref_id", ("conditionnement", "carton", "matiere_id"), "carton"),
    ("palette_ref_id", ("conditionnement", "palette", "matiere_id"), "palette"),
)


def _vide(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() == "" or v.strip() == "0"
    if isinstance(v, (int, float)):
        return v == 0
    return False


def _num(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        n = float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    return int(n) if n == int(n) else round(n, 4)


def diametre_mandrin(texte: Any) -> float | None:
    """« Tube 1500x40 » → 40, « 12 mm » → 12, « Bague 69,9x40 » → 40.

    Access décrit le mandrin en texte libre : longueur x diamètre pour un tube,
    diamètre seul sinon. Rien d'exploitable (« Planches A4 ») → None.
    """
    if texte is None:
        return None
    if isinstance(texte, (int, float)):
        return _num(texte)
    s = str(texte).strip().lower().replace(",", ".")
    if not s:
        return None
    m = re.search(r"x\s*(\d+(?:\.\d+)?)", s)
    if m:
        return _num(m.group(1))
    # Un nombre collé à une lettre (« A4 ») est un format, pas un diamètre.
    m = re.search(r"(?<![a-z])(\d+(?:\.\d+)?)", s)
    return _num(m.group(1)) if m else None


def enroulement(texte: Any) -> str | None:
    """« Exterieur pied en avant » → exterieur, « Intérieur… » → interieur."""
    s = str(texte or "").strip().lower()
    if not s:
        return None
    if s.startswith("int"):
        return "interieur"
    if s.startswith("ext"):
        return "exterieur"
    return None


def _poser(dst: dict, chemin: tuple[str, ...], valeur: Any) -> None:
    cur = dst
    for k in chemin[:-1]:
        cur = cur.setdefault(k, {})
    cur[chemin[-1]] = valeur


def fiche_vers_produit(ft: dict, matieres_actives: dict[int, str] | None = None) -> dict:
    """Traduit une fiche technique en fiche produit partielle.

    ``matieres_actives`` : {id: catégorie} des matières que le formulaire MyAO
    sait afficher. Une référence absente ou d'une autre catégorie n'est pas
    reprise : le select la montrerait vide, puis l'enregistrement l'effacerait.

    Seuls les champs renseignés sont présents dans le résultat.
    """
    out: dict[str, Any] = {}
    ref = str(ft.get("reference") or "").strip()
    if ref:
        out["ref_sifa"] = ref

    def put(chemin: tuple[str, ...], valeur: Any) -> None:
        if not _vide(valeur):
            _poser(out, chemin, valeur)

    # Étiquette
    put(("etiquette", "laize"), _num(ft.get("eti_laize")))
    put(("etiquette", "longueur"), _num(ft.get("eti_longueur")))
    put(("etiquette", "rayon"), _num(ft.get("eti_rayons")))
    put(("etiquette", "perforation"), str(ft.get("eti_perforations") or "").strip())

    # Échenillage : bord latéral des deux côtés, horizontal = en avance.
    lat = _num(ft.get("lateral_ext"))
    put(("echenillage", "droite"), lat)
    put(("echenillage", "gauche"), lat)
    put(("echenillage", "avance"), _num(ft.get("horizontal")))

    # Matières (références MyStock)
    for col, chemin, cat in _MATIERES:
        mid = ft.get(col)
        try:
            mid = int(mid) if mid not in (None, "") else None
        except (TypeError, ValueError):
            mid = None
        if not mid:
            continue
        if matieres_actives is not None and matieres_actives.get(mid) != cat:
            continue
        put(chemin, str(mid))

    # Bobines
    put(("bobines", "diametre_mandrin"), diametre_mandrin(ft.get("mandrin_dia")))
    put(("bobines", "diametre_bobine"), _num(ft.get("dia_ext")))
    nb = _num(ft.get("nb_etiq_bobin"))
    put(("bobines", "nb_etiquettes"), int(nb) if nb else None)
    enr = enroulement(ft.get("enroulement"))
    if enr:
        _poser(out, ("bobines", "enroulement"), enr)
        _poser(out, ("bobines", "sens_sortie"), 5 if enr == "interieur" else 1)

    # Impressions : le nombre de passages. Couleur et zone de chaque passage
    # restent à saisir (le formulaire les exige) — la fiche technique ne porte
    # que des pantones par tête, pas la zone imprimée.
    recto = _num(ft.get("recto"))
    verso = _num(ft.get("verso"))
    if recto:
        _poser(out, ("impressions_detail", "recto"), int(recto))
    if verso:
        _poser(out, ("impressions_detail", "verso"), int(verso))
    if recto or verso:
        out["impressions"] = True

    # Conditionnement
    put(("conditionnement", "carton", "bobines_carton"), _num(ft.get("nb_bobines_carton")))
    put(("conditionnement", "carton", "bobines_sol"), _num(ft.get("nb_au_sol")))
    put(("conditionnement", "carton", "nb_etages"), _num(ft.get("nb_etage")))
    put(("conditionnement", "palette", "cartons_sol"), _num(ft.get("palette_nb_cartons_sol")))
    put(("conditionnement", "palette", "nb_etages"), _num(ft.get("palette_nb_cartons_hauteur")))

    put(("particularites",), str(ft.get("particularite") or "").strip())
    return out


def completer_vides(fiche: dict, apport: dict) -> int:
    """Copie ``apport`` dans ``fiche`` là où ``fiche`` est vide. Rend le nombre
    de champs remplis. Ce qu'un humain a saisi n'est jamais écrasé — sauf
    ``ref_sifa``, qui est précisément ce qu'on vient choisir."""
    n = 0
    for k, v in apport.items():
        if isinstance(v, dict):
            sous = fiche.get(k)
            if not isinstance(sous, dict):
                sous = {}
                fiche[k] = sous
            n += completer_vides(sous, v)
        elif k == "ref_sifa":
            fiche[k] = v
        elif k in ("impressions", "enroulement", "sens_sortie"):
            # Booléen / défauts du formulaire : « vide » n'a pas de sens, on
            # ne les pose que si la clé est absente.
            if k not in fiche:
                fiche[k] = v
        elif _vide(fiche.get(k)):
            # Un composant saisi en libre (``frontal_libre``…) est une valeur :
            # la référence MyStock de la fiche technique ne l'écrase pas.
            if k.endswith("_id") and str(fiche.get(k[:-3] + "_libre") or "").strip():
                continue
            fiche[k] = v
            n += 1
    return n


def nb_champs(apport: dict) -> int:
    """Nombre de valeurs utiles d'un apport (hors ref_sifa et défauts)."""
    n = 0
    for k, v in apport.items():
        if isinstance(v, dict):
            n += nb_champs(v)
        elif k not in ("ref_sifa", "impressions", "enroulement", "sens_sortie"):
            n += 1
    return n
