"""
Points de production : reunions et comptes-rendus.

Une reunion tient sur une plage de dates : on ouvre, on regarde ce que
l'atelier a produit sur cette plage, on prend des notes, on decide des actions,
on clot. Le compte-rendu garde la plage, les notes, les actions et les
participants — PAS les chiffres.

Ce choix est deliberatif : les chiffres se recalculent a chaque lecture. Un
compte-rendu rouvert dans trois mois montrera donc l'atelier tel qu'on le voit
ce jour-la, pas tel qu'on le voyait pendant la reunion. C'est plus leger, et
c'est assume — ce qui doit survivre intact, ce sont les notes et les decisions,
et celles-la sont bien figees.

Trois tables plutot qu'une : une action et un participant sont des lignes, pas
du texte dans un champ. Les compter, les cocher ou les filtrer devient possible
sans reparser quoi que ce soit.
"""

NOM = "reunions_prod"


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS reunions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            titre       TEXT NOT NULL,
            date_debut  TEXT NOT NULL,
            date_fin    TEXT NOT NULL,
            machine     TEXT,
            notes       TEXT NOT NULL DEFAULT '',
            statut      TEXT NOT NULL DEFAULT 'ouverte',
            ouverte_le  TEXT NOT NULL,
            ouverte_par TEXT NOT NULL,
            close_le    TEXT,
            close_par   TEXT,
            updated_at  TEXT,
            updated_par TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_reunions_date
            ON reunions(date_debut DESC, id DESC);
        CREATE INDEX IF NOT EXISTS idx_reunions_statut
            ON reunions(statut);

        CREATE TABLE IF NOT EXISTS reunion_actions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            reunion_id  INTEGER NOT NULL,
            texte       TEXT NOT NULL,
            responsable TEXT,
            echeance    TEXT,
            fait        INTEGER NOT NULL DEFAULT 0,
            fait_le     TEXT,
            fait_par    TEXT,
            created_at  TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_reunion_actions_reunion
            ON reunion_actions(reunion_id, id);

        CREATE TABLE IF NOT EXISTS reunion_participants (
            reunion_id INTEGER NOT NULL,
            nom        TEXT NOT NULL,
            user_id    INTEGER,
            PRIMARY KEY (reunion_id, nom)
        );
        """
    )
    conn.commit()
    print("[MySifa] migration reunions_prod : reunions / actions / participants en place.")
