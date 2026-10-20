"""
Espace SIFA (portail unique des destinataires) et envoi des formulaires.

Décision du 20/10/2026 : tout ce qu'un tiers reçoit de SIFA (formulaires,
appels d'offres MyAO, demandes de devis transport, questionnaire EUDR) se
retrouve au même endroit, son Espace SIFA, ouvert par un lien personnel. Un
Espace par adresse email : c'est la seule clé commune aux modules existants.
Lien personnel seul, sans code (arbitrage d'Eugène, même niveau que le portail
transporteurs).

portail_espaces : un Espace par adresse email (en minuscules), son jeton.
qualite_formulaires_envois : un envoi = une version publiée d'un formulaire
  adressée à une liste de destinataires, avec message et échéance. Titre et
  description y sont figés au moment de l'envoi, comme les questions.
qualite_formulaires_destinataires : une ligne par (envoi, adresse) ; suit
  envoi, ouverture, réponse et relances. `tache_id` : tâche créée dans MySifa
  pour un destinataire du personnel.
qualite_formulaires_reponses : une ligne par réponse envoyée, jamais écrasée.
  La dernière fait foi ; les précédentes gardent la trace des modifications.
"""

NOM = "portail_espace_formulaires_envois"
DEPEND = ["qualite_formulaires"]


def appliquer(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS portail_espaces (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            email             TEXT NOT NULL UNIQUE,
            token             TEXT NOT NULL UNIQUE,
            nom               TEXT NOT NULL DEFAULT '',
            actif             INTEGER NOT NULL DEFAULT 1,
            cree_le           TEXT NOT NULL,
            dernier_acces_le  TEXT,
            dernier_acces_ip  TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS qualite_formulaires_envois (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            formulaire_id  INTEGER NOT NULL,
            version        INTEGER NOT NULL,
            titre          TEXT NOT NULL DEFAULT '',
            description    TEXT NOT NULL DEFAULT '',
            message        TEXT NOT NULL DEFAULT '',
            echeance       TEXT,
            cree_par       TEXT,
            cree_par_email TEXT,
            cree_le        TEXT NOT NULL,
            FOREIGN KEY (formulaire_id) REFERENCES qualite_formulaires(id)
        )
        """
    )
    conn.execute(
        """CREATE INDEX IF NOT EXISTS idx_qf_envois_formulaire
           ON qualite_formulaires_envois(formulaire_id)"""
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS qualite_formulaires_destinataires (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            envoi_id     INTEGER NOT NULL,
            type         TEXT NOT NULL,
            ref_id       INTEGER,
            nom          TEXT NOT NULL DEFAULT '',
            organisation TEXT NOT NULL DEFAULT '',
            email        TEXT NOT NULL,
            user_id      INTEGER,
            tache_id     INTEGER,
            statut       TEXT NOT NULL DEFAULT 'envoye',
            nb_envois    INTEGER NOT NULL DEFAULT 0,
            envoye_le    TEXT,
            ouvert_le    TEXT,
            repondu_le   TEXT,
            actif        INTEGER NOT NULL DEFAULT 1,
            UNIQUE (envoi_id, email),
            FOREIGN KEY (envoi_id) REFERENCES qualite_formulaires_envois(id)
        )
        """
    )
    conn.execute(
        """CREATE INDEX IF NOT EXISTS idx_qf_dest_email
           ON qualite_formulaires_destinataires(email)"""
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS qualite_formulaires_reponses (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            destinataire_id INTEGER NOT NULL,
            reponses_json   TEXT NOT NULL DEFAULT '{}',
            repondant_nom   TEXT NOT NULL DEFAULT '',
            soumis_le       TEXT NOT NULL,
            ip              TEXT,
            FOREIGN KEY (destinataire_id) REFERENCES qualite_formulaires_destinataires(id)
        )
        """
    )
    conn.execute(
        """CREATE INDEX IF NOT EXISTS idx_qf_reponses_dest
           ON qualite_formulaires_reponses(destinataire_id)"""
    )
    conn.commit()
