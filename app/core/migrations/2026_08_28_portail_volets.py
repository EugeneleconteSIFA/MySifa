"""
Portail : favoris de tuiles et reprise de navigation.

Deux besoins, une seule migration parce qu'ils naissent du même chantier.

`users.portal_apps_favoris` complète `portal_apps_order` : l'ordre dit où sont
les tuiles, les favoris disent lesquelles remontent en première rangée. Une
colonne JSON plutôt qu'une table, comme l'ordre — c'est une préférence
d'affichage, elle n'a ni historique ni relation.

`portail_recents` est la reprise de navigation (« Reprendre où j'en étais »).
Côté serveur et pas dans le navigateur : dans l'atelier on change de poste, et
un historique qui reste sur la machine ne suit pas l'opérateur. Une ligne par
écran et par utilisateur — l'index unique fait qu'une deuxième visite déplace
la date au lieu d'empiler un doublon, ce qui garde la table petite et la
lecture triviale.
"""

NOM = "portail_volets_favoris_recents"


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "portal_apps_favoris" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN portal_apps_favoris TEXT")

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS portail_recents (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            -- Clé de l'entrée dans le catalogue des volets : c'est elle qui
            -- identifie l'écran, pas l'URL (une ancre peut changer).
            cle     TEXT    NOT NULL,
            libelle TEXT    NOT NULL,
            module  TEXT,
            url     TEXT    NOT NULL,
            vu_le   TEXT    NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ix_portail_recents_user_cle
            ON portail_recents(user_id, cle);
        CREATE INDEX IF NOT EXISTS ix_portail_recents_user_date
            ON portail_recents(user_id, vu_le DESC);
        """
    )
    conn.commit()
