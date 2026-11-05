"""
Étiquettes spécifiques — bibliothèque : versions et verrous.

Versions : chaque enregistrement qui change la mise en page ou le format
range l'état précédent dans `etiq_modeles_versions` et incrémente
`etiq_modeles.version`. Revenir à une version, c'est enregistrer son contenu
comme une nouvelle version : l'historique ne se réécrit jamais.

Verrous : un objet `verrou`, ou posé sur un calque verrouillé, ne peut être
modifié, déplacé ni retiré que par un rôle de ETIQ_ROLES_CONCEPTION. Les
autres rôles MyPrint gardent l'édition de tout le reste.
"""

from __future__ import annotations

import json
from datetime import datetime


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _verrouille(e: dict, calques: dict) -> bool:
    return bool(e.get("verrou")) or bool(calques.get(e.get("calque"), {}).get("verrou"))


def _sans_etat(e: dict) -> str:
    """Empreinte comparable : 50 et 50.0 sont la même valeur."""
    def n(v):
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v
    return json.dumps({k: n(v) for k, v in e.items() if not str(k).startswith("_")}, sort_keys=True, ensure_ascii=False)


def violations_verrous(ancien: dict, nouveau: dict) -> list[str]:
    """Ce qu'un rôle hors conception n'a pas le droit de changer (vide = ok).
    Les deux mises en page sont déjà normalisées."""
    out = []
    ca = {c["id"]: c for c in ancien.get("calques", [])}
    cn = {c["id"]: c for c in nouveau.get("calques", [])}
    for cid, c in ca.items():
        if bool(c.get("verrou")) != bool(cn.get(cid, {}).get("verrou")):
            out.append(f"Calque « {c['nom']} » : seul un concepteur le verrouille ou le déverrouille.")
    for cid, c in cn.items():
        if cid not in ca and c.get("verrou"):
            out.append(f"Calque « {c['nom']} » : seul un concepteur crée un calque verrouillé.")
    an = {e["id"]: e for e in ancien.get("elements", [])}
    nn = {e["id"]: e for e in nouveau.get("elements", [])}
    for eid, e in an.items():
        if not _verrouille(e, ca):
            continue
        nom = e.get("nom") or eid
        if eid not in nn:
            out.append(f"« {nom} » est figé : il ne peut pas être retiré.")
        elif _sans_etat(nn[eid]) != _sans_etat(e):
            out.append(f"« {nom} » est figé : il ne peut pas être modifié.")
    for eid, e in nn.items():
        if eid not in an and _verrouille(e, cn):
            out.append(f"« {e.get('nom') or eid} » : seul un concepteur ajoute un objet figé.")
    return out


def enregistrer_version(conn, row, email: str, motif: str = "") -> int:
    """Range l'état actuel du modèle (row = ligne etiq_modeles) comme version
    `row.version` et rend le numéro de la suivante."""
    v = int(row["version"] or 1) if "version" in row.keys() else 1
    conn.execute(
        "INSERT OR IGNORE INTO etiq_modeles_versions (modele_id,version,nom,largeur_mm,hauteur_mm,dpi,layout_json,"
        "motif,created_at,created_by) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (row["id"], v, row["nom"], row["largeur_mm"], row["hauteur_mm"], row["dpi"], row["layout_json"],
         (motif or "")[:200], row["updated_at"] or row["created_at"] or _now(), row["updated_by"] or row["created_by"]))
    return v + 1


def lister_versions(conn, modele_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT id,version,nom,largeur_mm,hauteur_mm,dpi,layout_json,motif,created_at,created_by"
        " FROM etiq_modeles_versions WHERE modele_id=? ORDER BY version DESC LIMIT 200", (modele_id,)).fetchall()
    out = []
    for r in rows:
        try:
            lay = json.loads(r["layout_json"] or "{}")
        except Exception:
            lay = {}
        d = dict(r)
        d.pop("layout_json", None)
        d["nb_elements"] = len(lay.get("elements") or [])
        d["nb_variables"] = len(lay.get("variables") or [])
        out.append(d)
    return out
