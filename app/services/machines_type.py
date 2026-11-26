"""Le type d'une machine (`machines.type`) : impression ou repiquage.

Un seul endroit sait reconnaître une machine de repiquage. Le reste du code
demande ici, au lieu de comparer un nom (« Repiquage », « rep »…) : la règle
du projet veut que la logique métier lise un attribut en base, réglable dans
Paramètres › Machines, jamais un identifiant de machine.

Les saisies (`production_data.machine`) portent le NOM de la machine en texte,
pas son id : le filtre SQL compare donc ce texte aux noms ET codes des
machines typées `repiquage`, en littéraux échappés (aucune valeur venue d'une
requête n'y entre — ce sont des noms de machines lus en base).

Base sans la colonne `type` (avant la migration `machines_type`, ou base de
test minimale) : on retombe sur l'ancienne règle de nom, à l'identique, pour
ne rien changer à ce qui tournait.
"""

from __future__ import annotations

import unicodedata
from typing import Iterable, List, Optional

TYPE_IMPRESSION = "impression"
TYPE_REPIQUAGE = "repiquage"

# Ancienne règle, gardée pour les bases sans la colonne `type`.
_SQL_HERITE = ("(lower(trim(COALESCE({col},''))) LIKE 'repiquage%' "
               "OR lower(trim(COALESCE({col},''))) = 'rep' "
               "OR lower(trim(COALESCE({col},''))) LIKE 'rep %')")


def _norm(v) -> str:
    s = unicodedata.normalize("NFD", str(v or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def _colonnes(conn) -> set:
    try:
        return {r[1] for r in conn.execute("PRAGMA table_info(machines)").fetchall()}
    except Exception:
        return set()


def a_le_type(conn) -> bool:
    return "type" in _colonnes(conn)


def nom_herite_repiquage(nom) -> bool:
    n = _norm(nom)
    return n.startswith("repiquage") or n == "rep" or n.startswith("rep ")


def noms_repiquage(conn) -> Optional[List[str]]:
    """Noms et codes (minuscules, sans accent) des machines de repiquage.

    None quand la base n'a pas encore la colonne `type` : l'appelant applique
    alors l'ancienne règle.
    """
    cols = _colonnes(conn)
    if "type" not in cols:
        return None
    champs = "nom, code" if "code" in cols else "nom, NULL"
    out = set()
    for r in conn.execute("SELECT %s FROM machines WHERE type=?" % champs, (TYPE_REPIQUAGE,)).fetchall():
        for v in (r[0], r[1]):
            if v and str(v).strip():
                out.add(_norm(v))
    return sorted(out)


def est_repiquage_nom(conn, nom) -> bool:
    """Le nom (ou code) de machine d'une saisie désigne-t-il un poste de repiquage ?"""
    noms = noms_repiquage(conn)
    if noms is None:
        return nom_herite_repiquage(nom)
    return _norm(nom) in noms


def est_repiquage(machine) -> bool:
    """Sur une ligne de `machines` (dict ou Row) : le type, sinon le nom."""
    try:
        t = machine["type"]
    except (KeyError, IndexError, TypeError):
        t = None
    if t:
        return str(t).strip() == TYPE_REPIQUAGE
    try:
        nom = machine["nom"]
    except (KeyError, IndexError, TypeError):
        nom = None
    return nom_herite_repiquage(nom)


def _litteraux(valeurs: Iterable[str]) -> str:
    return ",".join("'" + v.replace("'", "''") + "'" for v in valeurs)


def sql_nom_repiquage(conn, col: str) -> str:
    """Fragment SQL : la colonne TEXTE `col` (nom de machine) est un repiquage."""
    noms = noms_repiquage(conn)
    if noms is None:
        return _SQL_HERITE.format(col=col)
    if not noms:
        return "0"
    return "lower(trim(COALESCE(%s,''))) IN (%s)" % (col, _litteraux(noms))


def sql_machine_repiquage(conn, alias: str) -> str:
    """Fragment SQL : la ligne `alias` de la table `machines` est un repiquage."""
    if a_le_type(conn):
        return "%s.type = '%s'" % (alias, TYPE_REPIQUAGE)
    return _SQL_HERITE.format(col="%s.nom" % alias)


# ── Sans connexion sous la main (boucles, filtres préparés avant la requête) ──
# Un cache court sur la base de l'application. Il se vide dès que le type
# d'une machine change dans Paramètres (`invalider_cache`), sinon au bout de
# `_TTL` secondes. Là où une connexion est disponible, les fonctions
# ci-dessus la lisent directement : un test sur sa propre base reste juste.
import time as _time

_TTL = 60
_cache = {"t": 0.0, "noms": None}


def invalider_cache() -> None:
    _cache["t"] = 0.0


def _noms_globaux() -> Optional[List[str]]:
    if _time.time() - _cache["t"] > _TTL:
        try:
            from database import get_db
            with get_db() as conn:
                _cache["noms"] = noms_repiquage(conn)
        except Exception:
            _cache["noms"] = None
        _cache["t"] = _time.time()
    return _cache["noms"]


def est_repiquage_nom_global(nom) -> bool:
    noms = _noms_globaux()
    if noms is None:
        return nom_herite_repiquage(nom)
    return _norm(nom) in noms


def sql_nom_repiquage_global(col: str) -> str:
    noms = _noms_globaux()
    if noms is None:
        return _SQL_HERITE.format(col=col)
    if not noms:
        return "0"
    return "lower(trim(COALESCE(%s,''))) IN (%s)" % (col, _litteraux(noms))
