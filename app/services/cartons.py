"""MyTools › Calculs bobine › Carton — références carton et leurs dimensions.

Les cartons sont des matières MyStock (`matieres_premieres`, catégorie
`CARTONS_CATEGORIE` de config.py). Leurs dimensions ne vivent que dans la
désignation ou la référence (« Carton 385 x 385 x 208 mm », « Carton RAJA
CAS14 31x21.5x5.5 cm », « Conteneur grand box 1180 x 780 x 1070 mm »).
`dimensions()` les lit ; une référence sans dimensions lisibles, ou portant un
mot de `CARTONS_EXCLUS` (couvercle seul, intercalaire), est écartée et comptée.

Le calcul de rangement (bobines debout ou couchées, disposition, remplissage)
se fait dans le navigateur (static/mysifa_tools_calculs.js) : il suit la
saisie à la frappe.
"""
from __future__ import annotations

import re
from typing import Optional

from config import CARTONS_CATEGORIE, CARTONS_EXCLUS

_NB = r"(\d+(?:[.,]\d+)?)"
_MOTIF = re.compile(_NB + r"\s*[x×X*]\s*" + _NB + r"\s*[x×X*]\s*" + _NB + r"\s*(mm|cm|m)?\b", re.I)
_FACTEUR = {"mm": 1.0, "cm": 10.0, "m": 1000.0, None: 1.0, "": 1.0}


def dimensions(texte: str) -> Optional[tuple[float, float, float]]:
    """(longueur, largeur, hauteur) en mm lues dans un libellé, ou None.

    La dernière dimension écrite est la hauteur (usage des cartonniers :
    L x l x h). Sans unité, le millimètre est supposé — sauf si toutes les
    valeurs sont petites (< 60) et décimales ou que « cm » apparaît ailleurs.
    """
    if not texte:
        return None
    m = _MOTIF.search(texte)
    if not m:
        return None
    vals = [float(v.replace(",", ".")) for v in m.group(1, 2, 3)]
    unite = (m.group(4) or "").lower()
    if not unite and re.search(r"\bcm\b", texte, re.I):
        unite = "cm"
    f = _FACTEUR.get(unite, 1.0)
    l, w, h = (round(v * f, 1) for v in vals)
    if min(l, w, h) <= 0:
        return None
    return l, w, h


def liste(conn) -> dict:
    rows = conn.execute(
        """SELECT id, reference, designation, sous_categorie FROM matieres_premieres
           WHERE lower(categorie) = ? AND COALESCE(actif, 1) = 1 AND COALESCE(brouillon, 0) = 0
           ORDER BY designation""",
        (CARTONS_CATEGORIE.lower(),),
    ).fetchall()
    cartons, ecartes = [], []
    for r in rows:
        libelle = r["designation"] or r["reference"] or ""
        bas = (libelle + " " + (r["reference"] or "")).lower()
        if any(m in bas for m in CARTONS_EXCLUS):
            ecartes.append({"id": r["id"], "libelle": libelle, "raison": "sans volume utile"})
            continue
        d = dimensions(r["designation"] or "") or dimensions(r["reference"] or "")
        if not d:
            ecartes.append({"id": r["id"], "libelle": libelle, "raison": "dimensions illisibles"})
            continue
        cartons.append({"id": r["id"], "libelle": libelle, "reference": r["reference"],
                        "famille": r["sous_categorie"] or "", "l": d[0], "w": d[1], "h": d[2]})
    return {"cartons": cartons, "ecartes": ecartes}
