"""
MyCalendrier — ce qui manquait à une vraie réunion.

Quatre ajouts, tous nés du même constat : une réunion ne se résume pas à un
titre et à deux dates.

  - lieu, lien de visio et délai de rappel propres à l'événement (les dix
    minutes étaient figées dans le code) ;
  - invités externes : un client ou un fournisseur n'a pas de compte MySifa,
    il répond depuis un lien signé reçu par e-mail ;
  - contre-propositions d'horaire, pour qu'un invité puisse dire « pas à cette
    heure-là, plutôt à celle-ci » sans ouvrir un fil de mails ;
  - délégations, pour qu'un assistant pose un créneau au nom de quelqu'un.
"""

NOM = "calendrier_reunions_avancees"
DEPEND = ["calendrier_participants_reunion"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(cal_events_perso)").fetchall()}
    if "lieu" not in cols:
        conn.execute("ALTER TABLE cal_events_perso ADD COLUMN lieu TEXT")
    if "visio" not in cols:
        conn.execute("ALTER TABLE cal_events_perso ADD COLUMN visio TEXT")
    if "rappel_minutes" not in cols:
        # NULL = valeur par defaut du calendrier (10 min) ; 0 = aucun rappel.
        conn.execute("ALTER TABLE cal_events_perso ADD COLUMN rappel_minutes INTEGER")
    if "cree_par" not in cols:
        # Delegation : qui a reellement pose le creneau, quand ce n'est pas le
        # proprietaire du calendrier.
        conn.execute("ALTER TABLE cal_events_perso ADD COLUMN cree_par INTEGER")

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS cal_event_invites_ext (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id   INTEGER NOT NULL,
            email      TEXT NOT NULL,
            nom        TEXT,
            statut     TEXT NOT NULL DEFAULT 'en_attente',
            jeton      TEXT NOT NULL UNIQUE,
            repondu_le TEXT,
            invite_le  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
            UNIQUE(event_id, email),
            FOREIGN KEY(event_id) REFERENCES cal_events_perso(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_cal_invites_ext_event
            ON cal_event_invites_ext(event_id);
        CREATE INDEX IF NOT EXISTS idx_cal_invites_ext_jeton
            ON cal_event_invites_ext(jeton);

        CREATE TABLE IF NOT EXISTS cal_event_propositions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id   INTEGER NOT NULL,
            user_id    INTEGER NOT NULL,
            date_debut TEXT NOT NULL,
            date_fin   TEXT NOT NULL,
            message    TEXT,
            statut     TEXT NOT NULL DEFAULT 'proposee',
            cree_le    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
            FOREIGN KEY(event_id) REFERENCES cal_events_perso(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_cal_propositions_event
            ON cal_event_propositions(event_id, statut);

        CREATE TABLE IF NOT EXISTS cal_delegations (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            proprietaire_id INTEGER NOT NULL,
            delegue_id     INTEGER NOT NULL,
            cree_le        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
            UNIQUE(proprietaire_id, delegue_id),
            FOREIGN KEY(proprietaire_id) REFERENCES users(id),
            FOREIGN KEY(delegue_id) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_cal_delegations_delegue
            ON cal_delegations(delegue_id);
        """
    )
    conn.commit()
