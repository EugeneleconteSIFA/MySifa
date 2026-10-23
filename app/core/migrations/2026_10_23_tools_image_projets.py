"""
MyTools › Image et BAT — projets enregistrés.

Un projet = l'image d'origine (fichier hors base, sous TOOLS_IMAGE_DIR), tous
les réglages (mode, amélioration, vectorisation) en JSON et une vignette.
Rouvrir un projet rejoue les réglages sur l'image d'origine : on garde de quoi
refaire le résultat, pas le résultat.

tools_image_projets : une ligne par projet ; un projet n'est visible que de
                      son auteur (`user_id`). `fichier` et `vignette` sont des
                      noms de fichier générés, jamais un chemin.
"""

NOM = "tools_image_projets"


def appliquer(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tools_image_projets (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            nom           TEXT NOT NULL DEFAULT '',
            mode          TEXT NOT NULL DEFAULT 'ameliorer',
            reglages      TEXT NOT NULL DEFAULT '{}',
            nom_source    TEXT NOT NULL DEFAULT '',
            fichier       TEXT NOT NULL,
            mime          TEXT NOT NULL DEFAULT '',
            taille        INTEGER NOT NULL DEFAULT 0,
            vignette      TEXT,
            cree_le       TEXT NOT NULL,
            maj_le        TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tools_image_projets_user ON tools_image_projets(user_id, maj_le)")
    conn.commit()
