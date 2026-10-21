"""Mesure en nombre libre — réglages communs aux alertes et aux formulaires.

Une question « valeur » peut demander :
  - une seule valeur ;
  - plusieurs valeurs à libellés fixes (`points` : « Début de prod »,
    « Milieu de prod »…) ;
  - un nombre libre de valeurs (`points_libres`) : l'opérateur ajoute autant
    de lignes qu'il en faut (« Front 1 », « Front 2 »…), entre `min_points`
    et `max_points`. Demande d'Eugène du 21/10/2026 : le nombre de fronts
    dépend de la laize, il ne peut pas être fixé dans l'alerte.

Dans les trois cas la réponse est un nombre, ou une liste de nombres. Une
question en nombre libre ignore `points`.
"""
from __future__ import annotations

MAX_POINTS_LIBRES = 50


def _entier(v, defaut: int, bas: int, haut: int) -> int:
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        n = defaut
    return max(bas, min(haut, n))


def normaliser(it: dict) -> dict:
    """Champs propres d'une mesure en nombre libre, ou {} si elle n'en est pas une."""
    if not isinstance(it, dict) or not bool(it.get("points_libres")):
        return {}
    lib = it.get("libelle_point")
    lib = lib.strip()[:30] if isinstance(lib, str) and lib.strip() else "Mesure"
    mini = _entier(it.get("min_points"), 1, 1, MAX_POINTS_LIBRES)
    maxi = _entier(it.get("max_points"), MAX_POINTS_LIBRES, mini, MAX_POINTS_LIBRES)
    return {"points_libres": True, "libelle_point": lib, "min_points": mini, "max_points": maxi}


def libelle(it: dict, k: int) -> str:
    """Libellé de la k-ième mesure (0 = première)."""
    if it.get("points_libres"):
        return f"{it.get('libelle_point') or 'Mesure'} {k + 1}"
    pts = it.get("points") or []
    return pts[k] if k < len(pts) else f"Mesure {k + 1}"
