"""
Outil RH (MyRH) : pièce jointe facultative ou exigée.

Réglage du catalogue, sur chaque document administratif et sur chaque
justificatif de formation. Exigée : chez l'employé, l'élément ne compte comme
fait (colonne Dossier) qu'une fois coché ET avec au moins un fichier joint ; le
trombone le signale « à joindre ». Par défaut : facultative, comme avant.
"""

NOM = "rh_outil_piece_exigee"
DEPEND = ["rh_outil_documents_administratifs"]


def appliquer(conn):
    for table in ("rh_outil_documents", "rh_outil_formation_justificatifs"):
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if "piece_exigee" not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN piece_exigee INTEGER NOT NULL DEFAULT 0")
    conn.commit()
