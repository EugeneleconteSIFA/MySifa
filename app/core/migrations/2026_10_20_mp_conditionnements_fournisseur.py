"""
Conditionnements d'un fournisseur sur une laize : plusieurs longueurs de bobine.

Un même fournisseur livre parfois la même laize en deux longueurs (2 000 m et
6 000 m sur la 530). `matiere_laize_fournisseurs.ml_bobine` n'en portait
qu'une : cette table en porte autant qu'il faut, une ligne par longueur.
`matiere_laize_fournisseurs` reste le lien « ce fournisseur livre cette laize ».

Reprise : chaque `ml_bobine` déjà saisi devient un conditionnement. La colonne
n'est plus lue ni écrite ; elle partira dans un lot suivant.

Information d'achat seulement : le stock MySifa reste compté au métrage
standard de la matière.
"""

NOM = "mp_conditionnements_fournisseur"
DEPEND = ["mlf_ml_bobine"]


def appliquer(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mp_conditionnements_fournisseur (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            matiere_id      INTEGER NOT NULL,
            laize_id        INTEGER NOT NULL,
            fournisseur_id  INTEGER NOT NULL,
            ml_bobine       REAL    NOT NULL,
            created_at      TEXT,
            created_by_name TEXT,
            UNIQUE(matiere_id, laize_id, fournisseur_id, ml_bobine)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mp_cond_fou_matiere ON mp_conditionnements_fournisseur(matiere_id)"
    )
    n = 0
    cols = {r[1] for r in conn.execute("PRAGMA table_info(matiere_laize_fournisseurs)").fetchall()}
    if "ml_bobine" in cols:
        n = conn.execute(
            """INSERT OR IGNORE INTO mp_conditionnements_fournisseur
                   (matiere_id, laize_id, fournisseur_id, ml_bobine, created_at, created_by_name)
               SELECT matiere_id, laize_id, fournisseur_id, ml_bobine, datetime('now'), 'reprise'
                 FROM matiere_laize_fournisseurs WHERE ml_bobine > 0"""
        ).rowcount
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n} conditionnement(s) repris.")
