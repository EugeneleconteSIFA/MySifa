"""
Planning : un dossier de production destiné au repiquage, et le lien du
dossier de repiquage vers sa production d'origine.

- `pour_repiquage` (case « Prod pour repiquage ») : les étiquettes de ce
  dossier ne partent pas telles quelles, elles attendent un repiquage pour la
  même commande (ex. OF 9932304 : DSI puis Repiquage).
- `repiquage_source_id` : sur un dossier d'une machine de type `repiquage`,
  l'id du dossier de production qu'il repique, choisi sur le planning.
  Jusqu'ici seule la référence partagée reliait les deux passes.
"""

NOM = "planning_repiquage"
DEPEND = ["machines_type"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
    if not cols:
        return
    if "pour_repiquage" not in cols:
        conn.execute("ALTER TABLE planning_entries ADD COLUMN pour_repiquage INTEGER NOT NULL DEFAULT 0")
    if "repiquage_source_id" not in cols:
        conn.execute("ALTER TABLE planning_entries ADD COLUMN repiquage_source_id INTEGER")
    conn.commit()
