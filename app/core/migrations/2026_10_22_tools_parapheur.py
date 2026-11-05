"""
MyTools › Parapheur — envoi d'un PDF à signer à une ou plusieurs personnes.

Une demande = un PDF d'origine (fichier hors base, empreinte SHA-256), des
signataires ordonnés (utilisateurs MySifa ou contacts externes, ces derniers
passant par leur Espace SIFA), des zones posées sur les pages, une échéance et
un rythme de relance. Une fois tous les signataires passés, le document final
est scellé : signatures apposées et page de certificat ajoutée.

parapheur_demandes     : la demande, son document d'origine et son document final.
parapheur_signataires  : une ligne par signataire ; `ordre` sert au mode
                         séquentiel ; la signature (PNG) y est gardée.
parapheur_zones        : zones de signature, paraphe, date ou nom, en fractions
                         de la page affichée (rotation appliquée, origine en
                         haut à gauche), pour ne dépendre d'aucun zoom.
parapheur_jetons       : liens de signature des externes. Seule l'empreinte du
                         jeton est gardée ; durée et nombre de consultations
                         limités, révoqués dès que le signataire a répondu.
parapheur_evenements   : historique (création, envoi, relance, ouverture,
                         signature, refus, annulation, expiration, scellement,
                         téléchargement), repris dans le certificat.
"""

NOM = "tools_parapheur"
DEPEND = ["portail_espace_formulaires_envois"]


def appliquer(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS parapheur_demandes (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            titre            TEXT NOT NULL DEFAULT '',
            message          TEXT NOT NULL DEFAULT '',
            mode             TEXT NOT NULL DEFAULT 'sequentiel',
            statut           TEXT NOT NULL DEFAULT 'en_cours',
            echeance         TEXT,
            relance_jours    INTEGER NOT NULL DEFAULT 3,
            nom_fichier      TEXT NOT NULL DEFAULT '',
            fichier_original TEXT NOT NULL,
            sha256_original  TEXT NOT NULL,
            taille_original  INTEGER NOT NULL DEFAULT 0,
            nb_pages         INTEGER NOT NULL DEFAULT 0,
            fichier_final    TEXT,
            sha256_signe     TEXT,
            sha256_final     TEXT,
            niveau           TEXT NOT NULL DEFAULT 'simple',
            cree_par_id      INTEGER,
            cree_par_nom     TEXT,
            cree_par_email   TEXT,
            cree_le          TEXT NOT NULL,
            termine_le       TEXT,
            motif_fin        TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_parapheur_demandes_statut ON parapheur_demandes(statut)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_parapheur_demandes_auteur ON parapheur_demandes(cree_par_id)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS parapheur_signataires (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            demande_id      INTEGER NOT NULL,
            ordre           INTEGER NOT NULL DEFAULT 1,
            type            TEXT NOT NULL DEFAULT 'interne',
            user_id         INTEGER,
            nom             TEXT NOT NULL DEFAULT '',
            email           TEXT NOT NULL DEFAULT '',
            organisation    TEXT NOT NULL DEFAULT '',
            statut          TEXT NOT NULL DEFAULT 'attente',
            notifie_le      TEXT,
            ouvert_le       TEXT,
            signe_le        TEXT,
            refuse_le       TEXT,
            motif_refus     TEXT,
            ip              TEXT,
            user_agent      TEXT,
            mode_signature  TEXT,
            nom_saisi       TEXT,
            signature_png   BLOB,
            paraphe_png     BLOB,
            nb_relances     INTEGER NOT NULL DEFAULT 0,
            relance_le      TEXT,
            liens_jour      TEXT,
            liens_nb        INTEGER NOT NULL DEFAULT 0,
            tache_id        INTEGER,
            FOREIGN KEY (demande_id) REFERENCES parapheur_demandes(id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_parapheur_sig_demande ON parapheur_signataires(demande_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_parapheur_sig_user ON parapheur_signataires(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_parapheur_sig_email ON parapheur_signataires(email)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS parapheur_zones (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            demande_id     INTEGER NOT NULL,
            signataire_id  INTEGER NOT NULL,
            page           INTEGER NOT NULL,
            type           TEXT NOT NULL DEFAULT 'signature',
            x              REAL NOT NULL,
            y              REAL NOT NULL,
            w              REAL NOT NULL,
            h              REAL NOT NULL,
            FOREIGN KEY (demande_id) REFERENCES parapheur_demandes(id),
            FOREIGN KEY (signataire_id) REFERENCES parapheur_signataires(id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_parapheur_zones_demande ON parapheur_zones(demande_id)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS parapheur_jetons (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            signataire_id  INTEGER NOT NULL,
            jeton_hash     TEXT NOT NULL UNIQUE,
            cree_le        TEXT NOT NULL,
            expire_le      TEXT NOT NULL,
            usages         INTEGER NOT NULL DEFAULT 0,
            usages_max     INTEGER NOT NULL DEFAULT 30,
            revoque_le     TEXT,
            FOREIGN KEY (signataire_id) REFERENCES parapheur_signataires(id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_parapheur_jetons_sig ON parapheur_jetons(signataire_id)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS parapheur_evenements (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            demande_id     INTEGER NOT NULL,
            signataire_id  INTEGER,
            le             TEXT NOT NULL,
            type           TEXT NOT NULL,
            acteur         TEXT NOT NULL DEFAULT '',
            ip             TEXT,
            detail         TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (demande_id) REFERENCES parapheur_demandes(id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_parapheur_ev_demande ON parapheur_evenements(demande_id)")
    conn.commit()
