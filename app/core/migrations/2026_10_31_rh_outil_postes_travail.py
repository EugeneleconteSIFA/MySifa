"""
Intitulés de poste dans MyRH : un poste appartient à un service, un employé
suivi peut en occuper plusieurs, et une formation peut être exigée pour un
poste précis (en plus des services).

Le catalogue des postes est saisi à la main dans MyRH › Catalogues › Postes :
aucun poste n'est seedé. Rien n'est jamais retiré automatiquement aux
employés : exiger une formation pour un poste l'attribue à ceux qui l'occupent.

Noms distincts de la première version abandonnée (rh_outil_postes,
rh_outil_membre_postes, rh_outil_formation_postes), que
rh_outil_exigences_services supprime : ces noms-là ne doivent pas resservir.
"""

NOM = "rh_outil_postes_travail"
DEPEND = ["rh_outil_exigences_services", "rh_outil_membres", "rh_outil_formations"]


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_outil_poste_catalogue (
               id        INTEGER PRIMARY KEY AUTOINCREMENT,
               libelle   TEXT NOT NULL,
               service   TEXT NOT NULL,
               cree_le   TEXT NOT NULL,
               cree_par  TEXT,
               UNIQUE (service, libelle COLLATE NOCASE)
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_outil_membre_poste (
               membre_id  INTEGER NOT NULL REFERENCES rh_outil_membres(id) ON DELETE CASCADE,
               poste_id   INTEGER NOT NULL REFERENCES rh_outil_poste_catalogue(id) ON DELETE CASCADE,
               ajoute_le  TEXT NOT NULL,
               PRIMARY KEY (membre_id, poste_id)
           )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS ix_rh_outil_membre_poste_poste ON rh_outil_membre_poste(poste_id)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_outil_formation_poste (
               formation_id  INTEGER NOT NULL REFERENCES rh_outil_formations(id) ON DELETE CASCADE,
               poste_id      INTEGER NOT NULL REFERENCES rh_outil_poste_catalogue(id) ON DELETE CASCADE,
               PRIMARY KEY (formation_id, poste_id)
           )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS ix_rh_outil_formation_poste_poste ON rh_outil_formation_poste(poste_id)")
    conn.commit()
