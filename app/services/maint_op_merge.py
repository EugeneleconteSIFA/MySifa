"""Fusion de deux saisies de maintenance portant le meme code dans un creneau.

`maintenance_event_ops` porte une contrainte UNIQUE(event_id, code) : un
creneau ne peut pas contenir deux saisies du meme code. Deux fonctionnalites
admin se heurtent a cette contrainte et doivent fusionner plutot qu'echouer :

  - le rattachement d'une intervention libre a un code recurrent
    (app/routers/settings.py, v2.5.11) ;
  - le reclassement d'une saisie depuis l'historique des operations
    (app/routers/maintenance_events.py, v2.5.13).

Regles de fusion, communes aux deux : rien n'est perdu.
  - observations et pieces changees concatenees (sans doublon) ;
  - durees additionnees : les deux interventions ont bien eu lieu ;
  - machines en union ;
  - photos en union ;
  - date, auteur et statut repris de la saisie la plus recente.

La saisie source est supprimee, la cible conserve son id.
"""

import json


def concat_text(a, b):
    """Concatene deux champs texte en evitant les doublons et les vides."""
    a = (a or "").strip()
    b = (b or "").strip()
    if not a:
        return b or None
    if not b or b == a or b in a:
        return a
    return a + "\n" + b


def merge_machines(a, b):
    """Union des machines_csv de deux saisies, ordre stable."""
    out = []
    for raw in ((a or ""), (b or "")):
        for m in str(raw).split(","):
            m = m.strip()
            if m and m not in out:
                out.append(m)
    return ",".join(out) if out else None


def merge_photos(a, b):
    """Union de deux listes JSON de photos. Retourne None si vide."""
    def _load(v):
        if not v:
            return []
        try:
            parsed = json.loads(v)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    base = _load(a)
    merged = base + [x for x in _load(b) if x not in base]
    return json.dumps(merged) if merged else None


def merge_op_rows(conn, src, tgt, now):
    """Fusionne la saisie `src` dans `tgt` puis supprime `src`.

    `src` et `tgt` sont des lignes completes de maintenance_event_ops
    (SELECT *). Retourne l'id de la ligne conservee.
    """
    cols = {c["name"] for c in conn.execute(
        "PRAGMA table_info(maintenance_event_ops)").fetchall()}
    src_newer = str(src["done_at"] or "") > str(tgt["done_at"] or "")
    recent = src if src_newer else tgt
    duree = (tgt["duree_reelle_min"] or 0) + (src["duree_reelle_min"] or 0)
    sets = ["observations = ?", "pieces_changees = ?", "duree_reelle_min = ?",
            "photos_json = ?", "done_at = ?", "done_by = ?", "statut = ?",
            "updated_at = ?"]
    params = [
        concat_text(tgt["observations"], src["observations"]),
        concat_text(tgt["pieces_changees"], src["pieces_changees"]),
        duree or None,
        merge_photos(tgt["photos_json"], src["photos_json"]),
        recent["done_at"],
        recent["done_by"],
        recent["statut"],
        now,
    ]
    if "machines_csv" in cols:
        sets.append("machines_csv = ?")
        params.append(merge_machines(tgt["machines_csv"], src["machines_csv"]))
    params.append(tgt["id"])
    conn.execute(
        "UPDATE maintenance_event_ops SET " + ", ".join(sets) + " WHERE id = ?",
        params,
    )
    conn.execute("DELETE FROM maintenance_event_ops WHERE id = ?", (src["id"],))
    return tgt["id"]
