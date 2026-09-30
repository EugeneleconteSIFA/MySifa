"""
Formations et documents exigés par service, dans l'Outil RH (MyCompta).

Le service d'un employé est celui de son compte (users.role) ; l'Outil RH ne
le modifie jamais. Une ligne = « cet élément du catalogue est exigé pour ce
service ». Un employé ajouté reçoit ce qui est exigé pour son service ;
exiger un élément pour un service l'attribue aux employés de ce service.
Rien n'est jamais retiré automatiquement. Les attributions sont faites par
l'API.

Nettoyage : une première version rangeait les exigences par « poste »
(tables rh_outil_postes…), abandonnée avant la production. Elle n'a existé
que sur v1 ; on retire ses tables si elles sont là.
"""

NOM = "rh_outil_exigences_services"
DEPEND = ["rh_outil_formations", "rh_outil_documents"]


def appliquer(conn):
    for table in ("rh_outil_formation_postes", "rh_outil_document_postes",
                  "rh_outil_membre_postes", "rh_outil_postes"):
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    for table, fk, catalogue in (
        ("rh_outil_formation_services", "formation_id", "rh_outil_formations"),
        ("rh_outil_document_services", "document_id", "rh_outil_documents"),
    ):
        conn.execute(
            f"""CREATE TABLE IF NOT EXISTS {table} (
                    {fk}     INTEGER NOT NULL REFERENCES {catalogue}(id) ON DELETE CASCADE,
                    service  TEXT NOT NULL,
                    PRIMARY KEY ({fk}, service)
                )"""
        )
        conn.execute(f"CREATE INDEX IF NOT EXISTS ix_{table}_service ON {table}(service)")
    conn.commit()
