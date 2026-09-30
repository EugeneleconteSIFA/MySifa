"""
Formations et documents exigés par poste, dans l'Outil RH (MyCompta).

Une ligne = « cet élément du catalogue est exigé pour ce poste ». Un employé
qui reçoit le poste reçoit l'élément ; exiger l'élément pour un poste
l'attribue aux employés qui l'ont déjà. Rien n'est jamais retiré
automatiquement. Les attributions sont faites par l'API.
"""

NOM = "rh_outil_exigences_postes"
DEPEND = ["rh_outil_postes", "rh_outil_formations", "rh_outil_documents"]


def appliquer(conn):
    for table, fk, catalogue in (
        ("rh_outil_formation_postes", "formation_id", "rh_outil_formations"),
        ("rh_outil_document_postes", "document_id", "rh_outil_documents"),
    ):
        conn.execute(
            f"""CREATE TABLE IF NOT EXISTS {table} (
                    {fk}      INTEGER NOT NULL REFERENCES {catalogue}(id) ON DELETE CASCADE,
                    poste_id  INTEGER NOT NULL REFERENCES rh_outil_postes(id) ON DELETE CASCADE,
                    PRIMARY KEY ({fk}, poste_id)
                )"""
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{table}_poste ON {table}(poste_id)"
        )
    conn.commit()
