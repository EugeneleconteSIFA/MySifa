"""
Mes notes : réparation des notes doublées lors de la promotion du 12/11/2026.

Pendant le redémarrage, une page a chargé le nouvel éditeur alors que l'ancien
processus répondait encore : elle a reçu des blocs sans identifiant et les a
renvoyés au nouveau serveur comme des blocs neufs. Le contenu de ces notes a
été inséré une seconde fois en tête (55 blocs pour une note, 2 pour une autre).

Correction : pour chaque note, les blocs insérés par une opération `ins` de
la fenêtre de l'incident sont retirés **seulement s'ils sont la copie exacte**
d'un bloc d'origine encore présent (même type, texte, mise en forme, case,
retrait). Une copie modifiée depuis est gardée. Les éditeurs ouverts sur ces
notes rechargent (opération `reset`).

La cause est corrigée dans l'éditeur (aucun envoi depuis des blocs sans
identifiant serveur) et dans le serveur (un bloc inconnu n'est plus ajouté).
"""

import json
from collections import Counter
from datetime import datetime

NOM = "notes_doublons_promotion"
DEPEND = ["notes_collaboration"]

FENETRE_DEBUT = "2026-11-12T11:14:00"
FENETRE_FIN = "2026-11-12T11:20:00"


def _cle(b):
    return (b.get("type") or "p", b.get("texte") or "", b.get("html") or "", bool(b.get("coche")),
            int(b.get("retrait") or 0), int(b.get("ref") or 0))


def appliquer(conn):
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "note_ops" not in tables or "postits" not in tables:
        return
    inseres = {}
    for note_id, op in conn.execute(
        "SELECT note_id, op FROM note_ops WHERE cree_le BETWEEN ? AND ?", (FENETRE_DEBUT, FENETRE_FIN)
    ).fetchall():
        try:
            o = json.loads(op)
        except (TypeError, ValueError):
            continue
        if o.get("t") == "ins" and isinstance(o.get("bloc"), dict) and o["bloc"].get("uid"):
            inseres.setdefault(note_id, set()).add(o["bloc"]["uid"])
    total = 0
    notes = 0
    for note_id, uids in inseres.items():
        row = conn.execute("SELECT contenu, revision, user_id FROM postits WHERE id=?", (note_id,)).fetchone()
        if not row:
            continue
        try:
            blocs = json.loads(row[0]) if row[0] else []
        except (TypeError, ValueError):
            continue
        dispo = Counter(_cle(b) for b in blocs if isinstance(b, dict) and b.get("uid") not in uids)
        garde, retires = [], 0
        for b in blocs:
            if isinstance(b, dict) and b.get("uid") in uids and dispo[_cle(b)] > 0:
                dispo[_cle(b)] -= 1
                retires += 1
                continue
            garde.append(b)
        if not retires:
            continue
        rev = int(row[1] or 0) + 1
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        conn.execute("UPDATE postits SET contenu=?, revision=? WHERE id=?",
                     (json.dumps(garde, ensure_ascii=False), rev, note_id))
        conn.execute(
            "INSERT INTO note_ops (note_id, revision, user_id, client, op, cree_le) VALUES (?,?,?,?,?,?)",
            (note_id, rev, row[2], "reparation", json.dumps({"t": "reset"}), now),
        )
        total += retires
        notes += 1
    conn.commit()
    if total:
        print(f"[MySifa] migration notes_doublons_promotion : {total} bloc(s) en double retiré(s) dans {notes} note(s).")
