"""
Garde-fou de saisie des références produit MyStock.

La forme canonique d'une référence produit SIFA est « FFF/NNNN » ou
« FFFF/NNNN » : famille sur 3 ou 4 chiffres, numéro sur 4 chiffres. Une
référence tapée sans le slash (« 10770035 »), avec un espace, un tiret ou un
point (« 1077 0035 », « 1077-0035 », « 1077.0035 ») créait jusqu'ici un second
produit à côté du vrai, avec son propre stock.

`canoniser_reference_produit` ramène toutes ces variantes à la forme
canonique. Une référence qui n'est pas purement numérique (rubans « FR055X300… »,
articles de négoce) ressort telle quelle, en majuscules.
"""

from __future__ import annotations

import re

# Avec séparateur explicite : famille 3-4 chiffres, numéro 1-4 chiffres (complété à 4).
_AVEC_SEP = re.compile(r"^(\d{3,4})\s*[/\-.\s_]\s*(\d{1,4})$")
# Sans séparateur : 7 chiffres (3+4) ou 8 chiffres (4+4).
_COLLEE = re.compile(r"^(\d{3,4})(\d{4})$")


def canoniser_reference_produit(value: str | None) -> str:
    s = re.sub(r"\s+", " ", str(value or "")).strip().upper()
    if not s:
        return ""
    m = _COLLEE.match(s) or _AVEC_SEP.match(s)
    if not m:
        return s
    return f"{m.group(1)}/{m.group(2).zfill(4)}"
