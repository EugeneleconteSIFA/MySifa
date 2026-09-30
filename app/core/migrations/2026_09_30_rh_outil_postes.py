"""
Postes de l'Outil RH (MyCompta) : la précision du poste à l'intérieur d'un
service existant.

Le service d'un employé reste celui de son compte (users.role, réglé dans
Paramètres › Comptes) ; l'Outil RH ne le modifie jamais. Un poste appartient à
un service, désigné par son code de rôle. Un employé peut avoir plusieurs
postes, tous dans son service (contrôlé par l'API).

Préremplissage : les postes utilisés par le Planning RH, rangés dans leur
service. Modifiables ensuite depuis l'Outil RH.
"""

from datetime import datetime

NOM = "rh_outil_postes"
DEPEND = ["rh_outil_membres"]

_SEED = [
    ("Conducteur", "fabrication"),
    ("Aide", "fabrication"),
    ("Emballage", "fabrication"),
    ("Resp. d'atelier", "fabrication"),
    ("Logistique", "logistique"),
]


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_outil_postes (
               id        INTEGER PRIMARY KEY AUTOINCREMENT,
               libelle   TEXT NOT NULL,
               service   TEXT NOT NULL,
               cree_le   TEXT NOT NULL,
               cree_par  TEXT
           )"""
    )
    conn.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS ux_rh_outil_postes_service_libelle
               ON rh_outil_postes(service, libelle COLLATE NOCASE)"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_outil_membre_postes (
               id         INTEGER PRIMARY KEY AUTOINCREMENT,
               membre_id  INTEGER NOT NULL REFERENCES rh_outil_membres(id) ON DELETE CASCADE,
               poste_id   INTEGER NOT NULL REFERENCES rh_outil_postes(id) ON DELETE CASCADE,
               ajoute_le  TEXT NOT NULL,
               UNIQUE(membre_id, poste_id)
           )"""
    )
    conn.execute(
        """CREATE INDEX IF NOT EXISTS ix_rh_outil_membre_postes_poste
               ON rh_outil_membre_postes(poste_id)"""
    )
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    n = 0
    for libelle, service in _SEED:
        n += conn.execute(
            """INSERT OR IGNORE INTO rh_outil_postes (libelle, service, cree_le, cree_par)
               VALUES (?,?,?,NULL)""",
            (libelle, service, now),
        ).rowcount
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n} poste(s) préremplis.")
