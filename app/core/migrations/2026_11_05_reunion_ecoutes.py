"""
Réunions : le mode écoute.

Une écoute est un enregistrement de réunion. Le navigateur l'envoie en
morceaux de 30 s (fichiers dans ECOUTE_DIR/<id>/, jamais en base), le serveur
la transcrit sur place, puis Claude propose un brief que quelqu'un valide.

Cycle (`statut`) :
  enregistrement → a_transcrire → transcription → a_structurer → proposition → validee
  et, à tout moment : erreur, abandonnee.

`a_structurer` est sauté quand le type de réunion a `structuration_ia = 0` :
l'écoute passe directement en `proposition` avec la transcription seule.

L'audio est supprimé dès la transcription faite. `transcription` est purgée à
`purge_le` (rétention ECOUTE_RETENTION_JOURS après validation) : seul le brief
validé reste, dans `reunions` et `reunion_actions`.
"""

NOM = "reunion_ecoutes"
DEPEND = ["reunions_types_visibilite"]


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS reunion_ecoutes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            statut          TEXT NOT NULL DEFAULT 'enregistrement',
            reunion_id      INTEGER,
            type_id         INTEGER,
            titre           TEXT NOT NULL DEFAULT '',
            demarre_le      TEXT NOT NULL,
            demarre_par     TEXT NOT NULL DEFAULT '',
            demarre_par_id  INTEGER,
            dernier_morceau_le TEXT,
            arrete_le       TEXT,
            duree_s         REAL,
            nb_morceaux     INTEGER NOT NULL DEFAULT 0,
            nb_annonces     INTEGER,
            morceaux_manquants TEXT NOT NULL DEFAULT '',
            mime            TEXT NOT NULL DEFAULT '',
            taille_octets   INTEGER NOT NULL DEFAULT 0,
            transcription   TEXT,
            modele          TEXT,
            transcription_debut TEXT,
            transcrit_le    TEXT,
            duree_traitement_s REAL,
            proposition     TEXT,
            structure_le    TEXT,
            valide_le       TEXT,
            valide_par      TEXT,
            purge_le        TEXT,
            erreur          TEXT,
            tentatives      INTEGER NOT NULL DEFAULT 0,
            maj_le          TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_reunion_ecoutes_statut
            ON reunion_ecoutes(statut, id);
        CREATE INDEX IF NOT EXISTS idx_reunion_ecoutes_auteur
            ON reunion_ecoutes(demarre_par_id, id DESC);
        CREATE INDEX IF NOT EXISTS idx_reunion_ecoutes_reunion
            ON reunion_ecoutes(reunion_id);
        """
    )
    conn.commit()
    print("[MySifa] migration reunion_ecoutes : table en place.")
