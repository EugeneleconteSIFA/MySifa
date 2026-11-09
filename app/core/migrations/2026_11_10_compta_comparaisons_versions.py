"""
MyCompta — Comparaison factures : revérification et écarts justifiés.

Une comparaison corrigée se revérifie en ne redéposant que le fichier refait :
l'autre côté est relu dans `donnees` (factures lues dans chaque PDF, jamais le
PDF lui-même). Chaque revérification est une nouvelle version du même dossier
(`dossier_id` = id de la v1, `version` = 1, 2, 3…). `ecarts` garde la liste
compacte des écarts de la version (clé numéro|date et montants), pour compter
sans relire tout le résultat.

`compta_comparaisons_justifs` : un écart reconnu normal (escompte voulu…) est
justifié pour tout le dossier, tant que ses montants ne changent pas
(`signature` = « HT|TTC »).
"""

NOM = "compta_comparaisons_versions"
DEPEND = ["compta_comparaisons"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(compta_comparaisons)").fetchall()}
    for nom, ddl in (
        ("dossier_id", "INTEGER"),
        ("version", "INTEGER NOT NULL DEFAULT 1"),
        ("donnees", "TEXT"),
        ("ecarts", "TEXT"),
    ):
        if nom not in cols:
            conn.execute(f"ALTER TABLE compta_comparaisons ADD COLUMN {nom} {ddl}")
    n = conn.execute(
        "UPDATE compta_comparaisons SET dossier_id = id WHERE dossier_id IS NULL"
    ).rowcount
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_compta_comparaisons_dossier "
        "ON compta_comparaisons(dossier_id)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS compta_comparaisons_justifs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            dossier_id  INTEGER NOT NULL,
            cle         TEXT NOT NULL,
            signature   TEXT NOT NULL,
            commentaire TEXT NOT NULL,
            cree_par    INTEGER,
            cree_le     TEXT NOT NULL,
            UNIQUE(dossier_id, cle)
        )
        """
    )
    conn.commit()
    if n:
        print(f"[MySifa] migration compta_comparaisons_versions : {n} comparaison(s) rattachée(s) à leur dossier.")
