"""
Plan du site : lecture et écriture de `plan_site_elements`.

Un élément se rattache aux emplacements par son `prefixe` : le code Z0
appartient à l'élément de préfixe « Z0 », les codes A111, A432… à celui de
préfixe « A ». Un préfixe ne capte que les codes où il est suivi d'un
chiffre, pour que « A » ne prenne pas un futur « AB12 ».
"""

import json
import re

TYPES = (
    "contour", "limite", "entree", "batiment", "titre", "rack", "sol",
    "zone", "allee", "machine", "divers", "locaux",
)
# Types décrits par une suite de points plutôt que par un rectangle.
# `batiment` : zone polygonale qu'on clique pour voir le détail du bâtiment.
TYPES_POINTS = ("contour", "limite", "entree", "batiment")

_COLS = "id, cle, type, libelle, sous_titre, x, y, w, h, vertical, prefixe, points, ordre"


def lister(conn) -> list[dict]:
    try:
        rows = conn.execute(
            f"SELECT {_COLS} FROM plan_site_elements ORDER BY ordre, id"
        ).fetchall()
    except Exception:
        return []
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["points"] = json.loads(d["points"]) if d["points"] else None
        except (TypeError, ValueError):
            d["points"] = None
        d["vertical"] = bool(d["vertical"])
        out.append(d)
    return out


def code_appartient(code: str, prefixe: str) -> bool:
    code = (code or "").upper()
    prefixe = (prefixe or "").upper()
    if not prefixe:
        return False
    if code == prefixe:
        return True
    return code.startswith(prefixe) and code[len(prefixe):len(prefixe) + 1].isdigit()


def nettoyer(payload: dict) -> dict:
    """Valide un élément reçu de l'écran. Lève ValueError avec un message affichable."""
    typ = str(payload.get("type") or "").strip()
    if typ not in TYPES:
        raise ValueError("Type d'élément inconnu.")
    d = {
        "type": typ,
        "libelle": str(payload.get("libelle") or "").strip()[:80],
        "sous_titre": str(payload.get("sous_titre") or "").strip()[:80],
        "vertical": 1 if payload.get("vertical") else 0,
        "prefixe": str(payload.get("prefixe") or "").strip().upper()[:10],
    }
    if d["prefixe"] and not re.fullmatch(r"[A-Z0-9]+", d["prefixe"]):
        raise ValueError("Préfixe invalide — lettres et chiffres uniquement.")
    for k in ("x", "y", "w", "h"):
        try:
            d[k] = round(float(payload.get(k) or 0), 1)
        except (TypeError, ValueError):
            raise ValueError("Position invalide.")
    if typ in TYPES_POINTS:
        pts = payload.get("points") or []
        try:
            pts = [[round(float(p[0]), 1), round(float(p[1]), 1)] for p in pts]
        except (TypeError, ValueError, IndexError):
            raise ValueError("Points invalides.")
        mini = 3 if typ in ("contour", "batiment") else 2
        if len(pts) < mini:
            raise ValueError(f"{mini} points minimum pour ce type.")
        d["points"] = json.dumps(pts)
    else:
        if d["w"] < 2 or d["h"] < 2:
            raise ValueError("Élément trop petit.")
        d["points"] = None
    return d
