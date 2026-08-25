"""
MyCalendrier — événements récurrents.

Une réunion hebdomadaire est enregistrée comme autant de créneaux réels reliés
par un `serie_id`, plutôt que comme une règle dépliée à l'affichage : chaque
occurrence garde ainsi ses propres invités, ses propres réponses et peut être
déplacée ou annulée seule, sans cas particulier dans le reste du calendrier.

`recurrence` conserve la règle d'origine, pour l'afficher (« toutes les
semaines ») et pour prolonger une série plus tard.
"""

NOM = "calendrier_evenements_recurrents"
DEPEND = ["calendrier_participants_reunion"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(cal_events_perso)").fetchall()}
    if "serie_id" not in cols:
        conn.execute("ALTER TABLE cal_events_perso ADD COLUMN serie_id TEXT")
    if "recurrence" not in cols:
        conn.execute("ALTER TABLE cal_events_perso ADD COLUMN recurrence TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_cal_events_perso_serie "
        "ON cal_events_perso(serie_id)"
    )
    conn.commit()
