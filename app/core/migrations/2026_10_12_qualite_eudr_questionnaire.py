"""
MyQualité — Certifications SIFA › EUDR : questionnaire fournisseurs.

Le règlement (UE) 2023/1115 (EUDR) impose de remonter, fournisseur par
fournisseur, son rôle (opérateur ou aval), ses codes NC et la façon dont il
transmettra les numéros de référence de ses déclarations de diligence
raisonnée. Comme pour la taxe carburant, on ne recopie plus des emails : le
fournisseur reçoit un lien personnel et répond dans un formulaire MySifa.

eudr_demandes : une ligne par (fournisseur, adresse) sollicitée. Le jeton est
  le lien du formulaire ; une relance réutilise la ligne et son jeton.
eudr_reponses : une ligne par réponse envoyée, jamais écrasée. La dernière
  fait foi ; les précédentes restent la trace de ce que le fournisseur a dit.
"""

NOM = "qualite_eudr_questionnaire"


def appliquer(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS eudr_demandes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            fournisseur_id  INTEGER NOT NULL,
            email           TEXT NOT NULL,
            token           TEXT NOT NULL UNIQUE,
            statut          TEXT NOT NULL DEFAULT 'envoyee',
            nb_envois       INTEGER NOT NULL DEFAULT 0,
            envoye_le       TEXT,
            envoye_par      TEXT,
            ouvert_le       TEXT,
            repondu_le      TEXT,
            actif           INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT NOT NULL,
            FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs_fsc(id)
        )
        """
    )
    conn.execute(
        """CREATE INDEX IF NOT EXISTS idx_eudr_demandes_four
           ON eudr_demandes(fournisseur_id)"""
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS eudr_reponses (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            demande_id           INTEGER NOT NULL,
            fournisseur_id       INTEGER NOT NULL,
            repondant_nom        TEXT,
            repondant_fonction   TEXT,
            repondant_email      TEXT,
            etablissement        TEXT,
            perimetre            TEXT,
            codes_nc             TEXT,
            role                 TEXT,
            date_debut_dds       TEXT,
            transmission         TEXT,
            transmission_detail  TEXT,
            ref_par_livraison    TEXT,
            amont                TEXT,
            geolocalisation      TEXT,
            essences             TEXT,
            pays_recolte         TEXT,
            contact_nom          TEXT,
            contact_email        TEXT,
            commentaire          TEXT,
            ip                   TEXT,
            created_at           TEXT NOT NULL,
            FOREIGN KEY (demande_id) REFERENCES eudr_demandes(id),
            FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs_fsc(id)
        )
        """
    )
    conn.execute(
        """CREATE INDEX IF NOT EXISTS idx_eudr_reponses_four
           ON eudr_reponses(fournisseur_id, created_at)"""
    )
    conn.commit()
