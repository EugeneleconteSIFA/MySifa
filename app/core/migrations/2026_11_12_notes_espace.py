"""
Mes notes : les post-its deviennent un espace de notes.

Une note reste une ligne de `postits`. Elle peut désormais vivre sans être
posée sur l'écran, se ranger sous une autre et passer par la corbeille :

- `sur_ecran` : 1 = affichée en post-it flottant, 0 = seulement dans Mes notes
  (/note). Les post-its existants restent à l'écran.
- `parent_id` : note parente (sous-page), NULL à la racine.
- `ordre` : rang parmi les notes sœurs.
- `modifie_le` : dernière modification du titre ou du contenu.
- `supprime_le` : mise à la corbeille (restaurable), NULL sinon.
"""

NOM = "notes_espace"
DEPEND = ["postits_notes_libres"]

_COLONNES = (
    ("sur_ecran", "INTEGER NOT NULL DEFAULT 1"),
    ("parent_id", "INTEGER"),
    ("ordre", "INTEGER NOT NULL DEFAULT 0"),
    ("modifie_le", "TEXT"),
    ("supprime_le", "TEXT"),
)


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(postits)").fetchall()}
    if not cols:
        return
    for nom, decl in _COLONNES:
        if nom not in cols:
            conn.execute(f"ALTER TABLE postits ADD COLUMN {nom} {decl}")
    conn.execute("UPDATE postits SET modifie_le = created_at WHERE modifie_le IS NULL")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_postits_user_parent ON postits(user_id, parent_id)")
    conn.commit()
