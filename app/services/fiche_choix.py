"""
Choisir LA fiche technique d'un dossier ou d'un OF — une seule règle.

Le problème que ça règle (17/09/2026)
-------------------------------------
Un même produit a souvent une fiche par machine : « 1220/0001 - COHESIO1 -
Laize 470 » et « 1220/0001 - COHESIO2 - Laize 570 ». Six écrans départageaient
ces fiches en comparant `LOWER(TRIM(machine))` des deux côtés. Or le planning
écrit « Cohésio 2 » et Access « COHESIO 2 » (ou « COHESIO2 ») : l'accent et
l'espace faisaient échouer l'égalité, aucune fiche n'était reconnue comme
celle de la machine, et le repli prenait la plus petite id — la fiche de
l'AUTRE machine. Dossier 9931675+996, Cohésio 2, laize 570 : l'écran montrait
la fiche Cohésio 1 laize 470, outil 2419 à 4 de front au lieu de l'outil 2776
à 5 de front. Le nombre de fronts étant au dénominateur du métrage, le besoin
matière et le déstockage calculaient sur la mauvaise fiche.

La règle
--------
Parmi les fiches du même produit (`ref_produit_norm`), dans cet ordre :

  0. la référence complète est identique à celle de l'OF — Access pointe la
     fiche exacte par `t_of.format`, rien ne vaut ce lien ;
  1. la machine correspond ET la laize correspond ;
  2. la machine correspond ;
  3. la laize correspond (machine inconnue, fiche sans machine ou machine
     générique) ;
  4. fiche sans machine, ou machine générique (« COHESIO » sans numéro) ;
  5. le reste.
À rang égal, la plus petite id — l'ordre historique.

La comparaison des machines passe par `cle_machine()` : sans accent, sans
espace, en minuscules. « Cohésio 2 », « COHESIO 2 » et « COHESIO2 » donnent
tous « cohesio2 ». Les requêtes qui départagent directement en SQL utilisent
`sql_cle_machine(colonne)`, son équivalent en SQL pur — pas une fonction
Python enregistrée, qui manquerait à toute connexion ouverte hors `get_db()`.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable, Optional


def cle_machine(nom: Any) -> str:
    """« Cohésio 2 » → « cohesio2 ». Chaîne vide si rien d'exploitable."""
    if nom is None:
        return ""
    txt = unicodedata.normalize("NFKD", str(nom))
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return re.sub(r"[^0-9a-z]+", "", txt.lower())


def sql_cle_machine(colonne: str) -> str:
    """Expression SQL équivalente à `cle_machine()` pour les noms de machine.

    `LOWER()` de SQLite ne connaît que l'ASCII : « É » doit être remplacé
    avant. Les seuls accents des noms de machine sont é/è/É.
    """
    expr = f"COALESCE({colonne}, '')"
    for a, b in (("É", "e"), ("é", "e"), ("è", "e"), ("È", "e"),
                 (" ", ""), ("-", ""), ("_", ""), (".", "")):
        expr = f"REPLACE({expr}, '{a}', '{b}')"
    return f"LOWER({expr})"


def _generique(cle_fiche: str, cle_dossier: str) -> bool:
    """« cohesio » face à « cohesio2 » : une fiche qui ne tranche pas.

    Access porte 30 fiches « COHESIO » sans numéro. Elles valent pour les deux
    Cohésio, donc ni pour l'une en particulier ni contre elle.
    """
    return bool(cle_fiche) and not cle_fiche[-1].isdigit() and (
        not cle_dossier or cle_dossier.startswith(cle_fiche)
    )


def _laize(v: Any) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None


def _meme_laize(ft: dict, laize: Optional[float]) -> bool:
    if laize is None:
        return False
    for col in ("laize_optimale", "laize"):
        v = _laize(ft.get(col))
        if v is not None and abs(v - laize) < 0.5:
            return True
    return False


def rang_fiche(ft: dict, machine: Any = None, laize: Any = None,
               reference: Any = None) -> tuple:
    """Clé de tri d'une fiche candidate — plus petit = meilleur."""
    ref = str(reference or "").strip().lower()
    if ref and str(ft.get("reference") or "").strip().lower() == ref:
        return (0, ft.get("id") or 0)
    cm = cle_machine(machine)
    cf = cle_machine(ft.get("machine"))
    lz = _laize(laize)
    meme_machine = bool(cm) and cf == cm
    meme_laize = _meme_laize(ft, lz)
    if meme_machine and meme_laize:
        r = 1
    elif meme_machine:
        r = 2
    elif meme_laize and (not cm or not cf or _generique(cf, cm)):
        r = 3
    elif not cf or _generique(cf, cm):
        r = 4
    else:
        r = 5
    return (r, ft.get("id") or 0)


def meilleure_fiche(candidates: Iterable[dict], machine: Any = None,
                    laize: Any = None, reference: Any = None) -> Optional[dict]:
    cands = list(candidates or [])
    if not cands:
        return None
    return min(cands, key=lambda ft: rang_fiche(ft, machine, laize, reference))


def choisir_fiche(conn, ref_produit: Any, machine: Any = None, laize: Any = None,
                  reference: Any = None, colonnes: str = "*") -> Optional[dict]:
    """La fiche technique d'un produit, départagée par machine et laize.

    `ref_produit` peut être une clé « XXX/NNNN » ou n'importe quel libellé qui
    la contient. `reference` est la référence complète portée par l'OF
    (« 1220/0001 - COHESIO2 - Laize 570 ») quand on la connaît.
    """
    try:
        from app.services.fiche_ref_parser import normalize_ref_produit
    except Exception:  # pragma: no cover - module toujours présent
        normalize_ref_produit = None  # type: ignore

    norm = None
    for source in (ref_produit, reference):
        if source and normalize_ref_produit:
            norm = normalize_ref_produit(str(source))
            if norm:
                break

    cols = colonnes
    if cols.strip() != "*":
        requis = {"id", "reference", "machine", "laize", "laize_optimale"}
        presentes = {c.strip() for c in cols.split(",")}
        cols = ", ".join(list(presentes | requis))

    rows = []
    if norm:
        rows = conn.execute(
            f"SELECT {cols} FROM fiches_techniques WHERE ref_produit_norm = ?",
            (norm,),
        ).fetchall()
    if not rows:
        texte = str(reference or ref_produit or "").strip()
        if texte:
            rows = conn.execute(
                f"SELECT {cols} FROM fiches_techniques "
                "WHERE LOWER(TRIM(reference)) = LOWER(TRIM(?))",
                (texte,),
            ).fetchall()
    return meilleure_fiche([dict(r) for r in rows], machine, laize, reference)
