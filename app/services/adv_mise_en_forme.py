"""ADV — règles de mise en forme conditionnelle du carnet.

Une règle : une colonne, un opérateur, une cible (une valeur, une autre colonne
du même type, ou « aujourd'hui ± N jours » pour une date) et un ton du thème.
Les règles sont communes au service et s'évaluent dans l'ordre : la première
qui s'applique à une cellule l'emporte. L'évaluation se fait dans le
navigateur (static/mysifa_adv.js, `tonCellule`) — le serveur ne fait que
garder et valider.

Rien du client n'est cru sur parole : colonne, opérateur, cible et ton sont
contrôlés contre les référentiels de config.py, la valeur est bornée en
longueur et, selon le type, doit être un nombre ou une date.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List

from config import (ADV_MEF_CIBLES, ADV_MEF_COLONNES, ADV_MEF_MAX_REGLES,
                    ADV_MEF_OPERATEURS, ADV_MEF_TONS)

TYPES = {k: t for k, _, t in ADV_MEF_COLONNES}
LIBELLES = {k: l for k, l, _ in ADV_MEF_COLONNES}
TONS = {k for k, _ in ADV_MEF_TONS}
CIBLES = {k for k, _ in ADV_MEF_CIBLES}
ETATS_ETAPE = ("oui", "en_cours", "non", "sans_objet")
SANS_CIBLE = ("vide", "non_vide")


def referentiel() -> Dict[str, Any]:
    """Ce que la fenêtre d'édition propose, tel que le serveur l'acceptera."""
    return {
        "colonnes": [{"cle": k, "label": l, "type": t} for k, l, t in ADV_MEF_COLONNES],
        "operateurs": {t: [{"cle": k, "label": l} for k, l in ops]
                       for t, ops in ADV_MEF_OPERATEURS.items()},
        "cibles": [{"cle": k, "label": l} for k, l in ADV_MEF_CIBLES],
        "tons": [{"cle": k, "label": l} for k, l in ADV_MEF_TONS],
        "max": ADV_MEF_MAX_REGLES,
    }


def lister(conn) -> List[Dict[str, Any]]:
    try:
        rows = conn.execute("""
            SELECT id, ordre, colonne, operateur, cible, valeur, ton, maj_le, maj_par
              FROM adv_mises_en_forme ORDER BY ordre, id""").fetchall()
    except Exception:
        return []
    return [dict(r) for r in rows]


class RegleInvalide(ValueError):
    pass


def _nombre(v: str) -> bool:
    try:
        float(str(v).replace(",", ".").replace(" ", "").replace(" ", ""))
        return True
    except ValueError:
        return False


def valider(regles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalise et contrôle une liste de règles ; lève RegleInvalide."""
    if not isinstance(regles, list):
        raise RegleInvalide("Liste de règles attendue.")
    if len(regles) > ADV_MEF_MAX_REGLES:
        raise RegleInvalide("Au plus %d règles." % ADV_MEF_MAX_REGLES)
    propres = []
    for i, r in enumerate(regles, start=1):
        if not isinstance(r, dict):
            raise RegleInvalide("Règle %d illisible." % i)
        col = str(r.get("colonne") or "")
        typ = TYPES.get(col)
        if not typ:
            raise RegleInvalide("Règle %d : colonne inconnue." % i)
        op = str(r.get("operateur") or "")
        if op not in {k for k, _ in ADV_MEF_OPERATEURS[typ]}:
            raise RegleInvalide("Règle %d : condition inconnue pour « %s »." % (i, LIBELLES[col]))
        ton = str(r.get("ton") or "")
        if ton not in TONS:
            raise RegleInvalide("Règle %d : couleur inconnue." % i)
        cible = str(r.get("cible") or "valeur")
        valeur = str(r.get("valeur") if r.get("valeur") is not None else "").strip()[:100]
        if cible not in CIBLES:
            raise RegleInvalide("Règle %d : cible inconnue." % i)
        if op in SANS_CIBLE:
            cible, valeur = "valeur", ""
        elif cible == "colonne":
            if TYPES.get(valeur) != typ or valeur == col:
                raise RegleInvalide("Règle %d : comparer « %s » à une autre colonne du même type."
                                    % (i, LIBELLES[col]))
        elif cible == "aujourdhui":
            if typ != "date":
                raise RegleInvalide("Règle %d : « aujourd'hui » ne vaut que pour une date." % i)
            valeur = valeur or "0"
            if not re.fullmatch(r"[+-]?\d{1,3}", valeur):
                raise RegleInvalide("Règle %d : décalage en jours entre -999 et 999." % i)
        else:
            if typ == "nombre" and not _nombre(valeur):
                raise RegleInvalide("Règle %d : « %s » attend un nombre." % (i, LIBELLES[col]))
            if typ == "date":
                try:
                    date.fromisoformat(valeur)
                except ValueError:
                    raise RegleInvalide("Règle %d : date attendue (AAAA-MM-JJ)." % i)
            if typ == "etat" and valeur not in ETATS_ETAPE:
                raise RegleInvalide("Règle %d : état inconnu." % i)
            if typ == "texte" and not valeur:
                raise RegleInvalide("Règle %d : texte à chercher manquant." % i)
        propres.append({"colonne": col, "operateur": op, "cible": cible,
                        "valeur": valeur, "ton": ton})
    return propres


def enregistrer(conn, regles: List[Dict[str, Any]], quand: str, par: str) -> List[Dict[str, Any]]:
    """Remplace le jeu de règles en une transaction. Les règles arrivent déjà validées."""
    conn.execute("DELETE FROM adv_mises_en_forme")
    for ordre, r in enumerate(regles):
        conn.execute("""
            INSERT INTO adv_mises_en_forme (ordre, colonne, operateur, cible, valeur, ton, maj_le, maj_par)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (ordre, r["colonne"], r["operateur"], r["cible"], r["valeur"], r["ton"], quand, par))
    conn.commit()
    return lister(conn)
