"""
Post-its : prise de notes libre.

Un post-it n'est plus une liste de tâches mais une suite de blocs, comme une
page Notion : texte, titres, cases à cocher, listes, citation, encadré, code,
séparateur. Le contenu tient dans une colonne JSON `postits.contenu`
(`[{"type": "todo", "texte": "...", "coche": false, "retrait": 0}, …]`),
réécrite d'un bloc à chaque enregistrement.

Reprise : les lignes de `postit_tasks` deviennent des cases à cocher, dans leur
ordre. La table `postit_tasks` n'est plus lue ni écrite ; elle reste en place
le temps de vérifier la reprise en production, puis sera supprimée dans un lot
suivant.
"""

import json

NOM = "postits_notes_libres"


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(postits)").fetchall()}
    if not cols:
        return
    if "contenu" not in cols:
        conn.execute("ALTER TABLE postits ADD COLUMN contenu TEXT")
    a_taches = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='postit_tasks'"
    ).fetchone()
    vides = conn.execute("SELECT id FROM postits WHERE contenu IS NULL").fetchall()
    for (pid,) in vides:
        blocs = []
        if a_taches:
            for texte, done in conn.execute(
                "SELECT text, done FROM postit_tasks WHERE postit_id=? ORDER BY order_index, id",
                (pid,),
            ).fetchall():
                blocs.append({"type": "todo", "texte": texte or "", "coche": bool(done)})
        conn.execute(
            "UPDATE postits SET contenu=? WHERE id=?",
            (json.dumps(blocs, ensure_ascii=False), pid),
        )
    conn.commit()
    if vides:
        print(f"[MySifa] migration postits_notes_libres : {len(vides)} post-it(s) repris en blocs.")
