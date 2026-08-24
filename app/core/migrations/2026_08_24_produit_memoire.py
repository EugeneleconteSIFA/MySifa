"""
Memoire produit — tables de capitalisation par reference produit.

Le probleme : tout ce que l'atelier produit comme information est indexe par
`no_dossier`. Le dossier se clot, et huit mois plus tard la meme reference
repasse en fabrication sans que rien de ce qu'on a appris ne soit disponible.

La cle produit existe deja (`ref_produit_norm`, "XXX/NNNN", maintenue par
triggers sur `planning_entries` et `fiches_techniques`). Cette migration
n'invente aucune notion metier : elle cree les trois tables qui accrochent
l'information a cette cle.

- `produit_series`      : un snapshot FIGE par production passee. Fige, parce
                          qu'un changement de regle de calcul ne doit pas
                          reecrire l'histoire. `UNIQUE(no_dossier)` rend la
                          materialisation rejouable sans doublon.
- `produit_documents`   : les OF terminees scannees (notes manuscrites de
                          l'atelier). `statut` porte le rattachement : un scan
                          dont on n'a pas su lire le numero d'OF reste
                          consultable dans la file « a rattacher ».
- `produit_savoirs`     : les notes ecrites, publiees sans validation. On ne
                          supprime pas un savoir perime, on le marque
                          `obsolete` — « ce reglage ne vaut plus depuis le
                          changement d'outil » se lit, une note effacee non.
- `produit_savoirs_utile` : un vote « ca m'a servi » par utilisateur, qui sert
                          au tri. Sans validation hierarchique, c'est l'usage
                          qui fait remonter ce qui compte.
"""

NOM = "produit_memoire_tables"


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS produit_series (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            ref_produit_norm     TEXT NOT NULL,
            no_dossier           TEXT NOT NULL,
            planning_entry_id    INTEGER,
            of_import_id         INTEGER,
            fiche_id             INTEGER,

            machine              TEXT,
            laize_mm             INTEGER,
            conditionnement_norm TEXT,
            format               TEXT,
            matiere              TEXT,
            ref_adhesif          TEXT,

            client               TEXT,
            designation          TEXT,
            operateurs           TEXT,
            date_debut           TEXT,
            date_fin             TEXT,

            nb_saisies           INTEGER DEFAULT 0,
            temps_calage_min     REAL,
            temps_prod_min       REAL,
            temps_arret_min      REAL,
            duree_totale_min     REAL,
            metrage_m            REAL,
            etiquettes           REAL,
            vitesse_m_min        REAL,

            arrets_par_code      TEXT,
            outillage            TEXT,
            matieres_consommees  TEXT,
            commentaires         TEXT,
            nb_nc                INTEGER DEFAULT 0,

            cloture_le           TEXT NOT NULL,
            cloture_par          TEXT,
            UNIQUE(no_dossier)
        );
        CREATE INDEX IF NOT EXISTS idx_produit_series_ref
            ON produit_series(ref_produit_norm, date_fin DESC);
        CREATE INDEX IF NOT EXISTS idx_produit_series_machine
            ON produit_series(ref_produit_norm, machine);

        CREATE TABLE IF NOT EXISTS produit_documents (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            ref_produit_norm TEXT,
            no_dossier       TEXT,
            of_numero        TEXT,
            of_import_id     INTEGER,
            type             TEXT NOT NULL DEFAULT 'of_termine',
            fichier          TEXT NOT NULL,
            fichier_origine  TEXT,
            nb_pages         INTEGER,
            taille_octets    INTEGER,
            texte_extrait    INTEGER NOT NULL DEFAULT 0,
            statut           TEXT NOT NULL DEFAULT 'a_rattacher',
            note             TEXT,
            rattache_par     TEXT,
            rattache_le      TEXT,
            importe_le       TEXT NOT NULL,
            importe_par      TEXT,
            UNIQUE(fichier)
        );
        CREATE INDEX IF NOT EXISTS idx_produit_documents_ref
            ON produit_documents(ref_produit_norm, importe_le DESC);
        CREATE INDEX IF NOT EXISTS idx_produit_documents_statut
            ON produit_documents(statut, importe_le DESC);
        CREATE INDEX IF NOT EXISTS idx_produit_documents_dossier
            ON produit_documents(no_dossier);

        CREATE TABLE IF NOT EXISTS produit_savoirs (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            ref_produit_norm  TEXT NOT NULL,
            type              TEXT NOT NULL DEFAULT 'autre',
            texte             TEXT NOT NULL,
            machine           TEXT,
            laize_mm          INTEGER,
            no_dossier_source TEXT,
            saisie_source_id  INTEGER,
            epingle           INTEGER NOT NULL DEFAULT 0,
            obsolete          INTEGER NOT NULL DEFAULT 0,
            obsolete_motif    TEXT,
            utile_count       INTEGER NOT NULL DEFAULT 0,
            auteur            TEXT NOT NULL,
            created_at        TEXT NOT NULL,
            updated_at        TEXT,
            updated_par       TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_produit_savoirs_ref
            ON produit_savoirs(ref_produit_norm, obsolete, epingle DESC, created_at DESC);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_produit_savoirs_saisie
            ON produit_savoirs(saisie_source_id) WHERE saisie_source_id IS NOT NULL;

        CREATE TABLE IF NOT EXISTS produit_savoirs_utile (
            savoir_id  INTEGER NOT NULL,
            user_login TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (savoir_id, user_login)
        );
        """
    )
    conn.commit()
    print("[MySifa] migration produit_memoire_tables : "
          "produit_series / produit_documents / produit_savoirs en place.")
