"""MyExpé — référentiel des régions françaises.

Le classement des transporteurs raisonne par région et non par département :
un transporteur qui dessert bien Lille dessert le Pas-de-Calais et la Somme, et
découper l'historique en 101 morceaux produisait des zones à un seul départ où
le premier transporteur croisé devenait « le meilleur ». La région regroupe
assez de départs pour qu'un classement veuille dire quelque chose, tout en
restant plus fin que la France entière.

Le référentiel est figé ici — 13 régions métropolitaines plus les cinq DOM,
chacun sa propre région. Il n'a pas bougé depuis 2016 et n'a rien à faire en
base : une table de plus se désynchroniserait du SVG de la carte, qui est lui
aussi dessiné une fois pour toutes.
"""

from __future__ import annotations

from typing import Optional

# code région -> (nom, départements). L'ordre est l'ordre d'affichage.
REGIONS: dict[str, tuple[str, tuple[str, ...]]] = {
    "ARA": ("Auvergne-Rhône-Alpes",
            ("01", "03", "07", "15", "26", "38", "42", "43", "63", "69", "73", "74")),
    "BFC": ("Bourgogne-Franche-Comté",
            ("21", "25", "39", "58", "70", "71", "89", "90")),
    "BRE": ("Bretagne", ("22", "29", "35", "56")),
    "CVL": ("Centre-Val de Loire", ("18", "28", "36", "37", "41", "45")),
    "COR": ("Corse", ("2A", "2B")),
    "GES": ("Grand Est",
            ("08", "10", "51", "52", "54", "55", "57", "67", "68", "88")),
    "HDF": ("Hauts-de-France", ("02", "59", "60", "62", "80")),
    "IDF": ("Île-de-France",
            ("75", "77", "78", "91", "92", "93", "94", "95")),
    "NOR": ("Normandie", ("14", "27", "50", "61", "76")),
    "NAQ": ("Nouvelle-Aquitaine",
            ("16", "17", "19", "23", "24", "33", "40", "47", "64", "79", "86", "87")),
    "OCC": ("Occitanie",
            ("09", "11", "12", "30", "31", "32", "34", "46", "48", "65", "66", "81", "82")),
    "PDL": ("Pays de la Loire", ("44", "49", "53", "72", "85")),
    "PAC": ("Provence-Alpes-Côte d'Azur", ("04", "05", "06", "13", "83", "84")),
    "GLP": ("Guadeloupe", ("971",)),
    "MTQ": ("Martinique", ("972",)),
    "GUF": ("Guyane", ("973",)),
    "REU": ("La Réunion", ("974",)),
    "MYT": ("Mayotte", ("976",)),
}

# Index inverse, construit une fois : un département est cherché à chaque
# départ balayé, et une boucle sur 18 régions à chaque ligne coûterait cher.
_PAR_DEPARTEMENT: dict[str, str] = {
    dept: code for code, (_, depts) in REGIONS.items() for dept in depts
}


def region_du_departement(dept: str) -> str:
    """Code région d'un département, ou chaîne vide s'il est inconnu."""
    return _PAR_DEPARTEMENT.get((dept or "").strip().upper(), "")


def nom_region(code: str) -> str:
    entree = REGIONS.get((code or "").strip().upper())
    return entree[0] if entree else ""


def departements_de(code: str) -> tuple[str, ...]:
    entree = REGIONS.get((code or "").strip().upper())
    return entree[1] if entree else ()


def existe(code: str) -> bool:
    return (code or "").strip().upper() in REGIONS


def normaliser(code: str) -> Optional[str]:
    """Code région en majuscules s'il existe, None sinon."""
    txt = (code or "").strip().upper()
    return txt if txt in REGIONS else None
