"""
Validation humaine des OF et des fiches techniques.

Le déstockage de production retire de la matière du stock à partir de ce que
disent l'OF et la fiche technique. Si l'un des deux est faux, le stock devient
faux — et personne ne s'en aperçoit avant l'inventaire. On exige donc que les
deux documents aient été relus et validés par quelqu'un avant tout défalquage.

`of_imports.statut` existait déjà, positionné à « valide » par le seul fait
d'importer un PDF. Ce n'était pas une validation : c'était un état d'import.
On ne le réutilise pas, et l'ancien badge disparaît de MyProd → OF pour ne pas
laisser croire qu'un OF est relu alors qu'il n'a été que déposé.

La validation part donc de zéro, des deux côtés, avec la même forme : qui a
validé, et quand. Sans le « qui », une case cochée ne veut rien dire.
"""

NOM = "validation_of_et_fiches"

_COLONNES = (
    ("valide", "INTEGER NOT NULL DEFAULT 0"),
    ("valide_par", "TEXT"),
    ("valide_at", "TEXT"),
)

_TABLES = ("of_imports", "fiches_techniques")


def appliquer(conn):
    for table in _TABLES:
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if not cols:
            continue  # table absente sur cette base : rien à faire
        for nom, ddl in _COLONNES:
            if nom not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {nom} {ddl}")
    conn.commit()
    print("[MySifa] migration validation_of_et_fiches : OF et fiches techniques "
          "portent désormais une validation humaine (0 par défaut).")
