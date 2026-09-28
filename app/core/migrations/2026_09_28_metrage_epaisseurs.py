"""
Épaisseurs de matière pour le calcul du métrage d'une bobine (MyStock).

Le widget « Métrage bobine » estime la longueur enroulée à partir de
l'épaisseur de la matière et des deux diamètres (mandrin, bobine). Les
épaisseurs types sont un référentiel SIFA : elles viennent du classeur
« Calcul métrage bobine » de l'atelier et se modifient ensuite depuis le
widget, par les administrateurs matières.
"""

NOM = "metrage_epaisseurs"

_SEED = [
    ("Matière enduite (frontal + colle + glassine)", 145, 10),
    ("Vélin", 66, 20),
    ("Couché", 75, 30),
    ("Thermique Eco", 78, 40),
    ("Thermique Pro", 72, 50),
    ("Glassine", 52, 60),
]


def appliquer(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mp_metrage_epaisseurs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            libelle    TEXT    NOT NULL UNIQUE,
            microns    REAL    NOT NULL,
            ordre      INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT
        )
        """
    )
    n = 0
    for libelle, microns, ordre in _SEED:
        cur = conn.execute(
            "INSERT OR IGNORE INTO mp_metrage_epaisseurs (libelle, microns, ordre) VALUES (?,?,?)",
            (libelle, microns, ordre),
        )
        n += cur.rowcount or 0
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n} épaisseur(s) seedée(s).")
