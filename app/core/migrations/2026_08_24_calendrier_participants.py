"""
MyCalendrier — participants d'une réunion.

Un créneau personnel peut désormais porter des invités : chacun répond
« accepté », « refusé » ou « peut-être », et la réunion s'affiche dans tous
les cas sur son propre calendrier.

Deux ajouts :
  - `cal_event_participants` : une ligne par invité, avec son statut ;
  - `cal_events_perso.annule` : l'organisateur qui annule une réunion ayant
    des invités ne supprime pas la ligne — les participants doivent voir
    l'annulation, pas voir l'événement disparaître sans explication.
"""

NOM = "calendrier_participants_reunion"


def _colonnes(conn, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS cal_event_participants (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id    INTEGER NOT NULL,
            user_id     INTEGER NOT NULL,
            statut      TEXT NOT NULL DEFAULT 'en_attente',
            repondu_le  TEXT,
            invite_le   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
            UNIQUE(event_id, user_id),
            FOREIGN KEY(event_id) REFERENCES cal_events_perso(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_cal_event_part_event
            ON cal_event_participants(event_id);
        CREATE INDEX IF NOT EXISTS idx_cal_event_part_user
            ON cal_event_participants(user_id, statut);
        """
    )

    cols = _colonnes(conn, "cal_events_perso")
    if "annule" not in cols:
        conn.execute(
            "ALTER TABLE cal_events_perso ADD COLUMN annule INTEGER NOT NULL DEFAULT 0"
        )
    conn.commit()
