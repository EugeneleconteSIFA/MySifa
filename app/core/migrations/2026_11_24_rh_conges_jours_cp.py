"""
Planning RH : jours décomptés des CP sur une absence justifiée.

Une absence justifiée (événement familial, formation…) ne s'impute pas sur le
solde CP, sauf la part qui dépasse ce qu'elle couvre : 6 jours d'absence dont
4 d'événement familial = 2 jours retirés des CP. `jours_cp` porte cette part.

Lecture : pour un motif qui se décompte des CP (`decompte = 'cp'`), c'est
`nb_jours` qui s'impute, `jours_cp` est ignoré ; pour les autres motifs,
`jours_cp` (0 par défaut) s'ajoute aux CP posés.
"""

NOM = "rh_conges_jours_cp"
DEPEND = ["rh_demandes_motifs"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(rh_conges)").fetchall()}
    if "jours_cp" not in cols:
        conn.execute("ALTER TABLE rh_conges ADD COLUMN jours_cp REAL")
    conn.commit()
