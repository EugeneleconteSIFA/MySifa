"""
Estimation du nombre de palettes d'un dossier, à partir de la fiche technique.

Ce module ne contient que le calcul, sans SQL ni FastAPI : il est appelé par le
planning (`app/routers/planning.py`, pour le camion et la marge transport) et
par le pilotage des expéditions (`app/services/expe_pilotage.py`, pour savoir
combien de palettes réserver avant que la production soit finie).

Il vit ici parce que ces deux écrans doivent donner le MÊME chiffre. Une
seconde implémentation, même fidèle au départ, finit par diverger d'un
arrondi — et deux écrans qui annoncent 4 et 5 palettes pour le même dossier
font perdre la confiance dans les deux.

La formule :

    nb_cartons  = ceil(qte_bobines / nb_bobines_carton)
    nb_palettes = ceil(nb_cartons / (palette_nb_cartons_sol × palette_nb_cartons_hauteur))

Cas particulier : quand le « carton » est en réalité un conteneur de taille
palette (détecté sur le libellé ou sur des dimensions proches de 1200×800),
1 carton = 1 palette et le plan de palettisation ne s'applique pas.

Renvoie `None` dès qu'une entrée manque — on ne devine pas un nombre de
palettes, on affiche « à estimer ».
"""

import math
import re
from typing import Optional

# Clés attendues dans le dictionnaire de dossier enrichi (mêmes noms que
# `_SQL_ENTRIES_ENRICHIES` du planning, pour qu'un dossier se passe tel quel).
CLES_ENRICHIES = (
    "_of_qte_bobines",
    "_ft_nb_bobines_carton",
    "_ft_palette_nb_cartons_sol",
    "_ft_palette_nb_cartons_hauteur",
    "_ft_palette_type",
    "_ft_cartons",
)


def est_conteneur_taille_palette(label) -> bool:
    """Le format de carton/conteneur a-t-il la taille d'une palette ?

    Détection sur deux registres :
      - mots-clés explicites : 'conteneur', 'container', 'box', 'palette box' ;
      - dimensions lues dans le libellé (XXXX x YYY), proches de 1200×800 mm
        avec une tolérance de ±150 mm.
    """
    if not label:
        return False
    s = str(label).lower()
    for kw in ("conteneur", "container", " box", "box ", "palette box"):
        if kw in s:
            return True
    if s.strip().startswith("box"):
        return True
    m = re.search(r"(\d{3,4})\s*[x×]\s*(\d{3,4})", s)
    if m:
        try:
            a, b = int(m.group(1)), int(m.group(2))
            lo, hi = min(a, b), max(a, b)
            # Format palette standard EUR : 1200x800 (tolérance ±150)
            if 1050 <= hi <= 1350 and 650 <= lo <= 950:
                return True
        except Exception:
            pass
    return False


def nb_palettes(e: dict) -> Optional[int]:
    """Nombre de palettes d'un dossier enrichi, ou None si on ne peut pas."""
    try:
        qte_bobines = e.get("_of_qte_bobines")
        nb_bobines_carton = e.get("_ft_nb_bobines_carton")
        if qte_bobines is None or nb_bobines_carton is None:
            return None
        qb = float(qte_bobines)
        nbc = float(nb_bobines_carton)
        if nbc <= 0 or qb <= 0:
            return None
        nb_cartons = math.ceil(qb / nbc)
        # Cas conteneur/box de taille palette → 1 carton = 1 palette
        if (est_conteneur_taille_palette(e.get("_ft_cartons"))
                or est_conteneur_taille_palette(e.get("_ft_palette_type"))):
            return int(nb_cartons)
        cartons_sol = e.get("_ft_palette_nb_cartons_sol")
        cartons_haut = e.get("_ft_palette_nb_cartons_hauteur")
        if cartons_sol is None or cartons_haut is None:
            return None
        cso = float(cartons_sol)
        cha = float(cartons_haut)
        if cso <= 0 or cha <= 0:
            return None
        return int(math.ceil(nb_cartons / (cso * cha)))
    except Exception:
        return None


def manques(e: dict) -> list:
    """Ce qui empêche le calcul, en clair, pour l'afficher à l'utilisateur.

    Liste vide quand le calcul aboutit. Sert à orienter vers la fiche à
    compléter plutôt qu'à laisser une case vide sans explication.
    """
    if nb_palettes(e) is not None:
        return []
    out = []
    if e.get("_of_qte_bobines") in (None, "", 0):
        out.append("Quantité de bobines (OF)")
    if e.get("_ft_nb_bobines_carton") in (None, "", 0):
        out.append("Bobines par carton (fiche technique)")
    conteneur = (est_conteneur_taille_palette(e.get("_ft_cartons"))
                 or est_conteneur_taille_palette(e.get("_ft_palette_type")))
    if not conteneur:
        if e.get("_ft_palette_nb_cartons_sol") in (None, "", 0):
            out.append("Cartons au sol (fiche technique)")
        if e.get("_ft_palette_nb_cartons_hauteur") in (None, "", 0):
            out.append("Cartons en hauteur (fiche technique)")
    return out
