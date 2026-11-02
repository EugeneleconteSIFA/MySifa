"""
Référentiel des épaisseurs matière : ajout du grammage et de la famille.

Le widget « Poids de colle » de la saisie prod retrouve le grammage d'adhésif
à partir de la pesée d'étiquettes : poids pesé − frontal (− glassine si on
pèse avec) − encre, rapporté à la surface. Il lui faut donc le grammage de
chaque matière (g/m²), que MyStock ne porte pas (`weight_gsm` vide partout),
et le dépôt d'encre par anilox.

Ces valeurs vivent dans le même référentiel que les épaisseurs du widget
« Métrage bobine » : une matière y a une épaisseur, un grammage, ou les deux.
`microns` devient donc facultatif — SQLite ne sait pas retirer un NOT NULL,
la table est reconstruite (mêmes id, mêmes lignes).

Valeurs seedées : classeur « application excel calcul de poids adhésif » de
l'atelier. Elles sont indicatives et se modifient ensuite depuis le widget.
"""

NOM = "epaisseurs_grammages_matiere"
DEPEND = ["metrage_epaisseurs"]

# Familles des lignes déjà en base (seed de metrage_epaisseurs).
_FAMILLES = {
    "Matière enduite (frontal + colle + glassine)": "complexe",
    "Vélin": "frontal",
    "Couché": "frontal",
    "Thermique Eco": "frontal",
    "Thermique Pro": "frontal",
    "Glassine": "glassine",
}
_GRAMMAGES = {"Vélin": 70, "Couché": 70}

# (libellé, famille, grammage g/m², ordre)
_SEED = [
    ("Thermique Eco Kanzan", "frontal", 73, 41),
    ("Thermique Eco Jujo", "frontal", 72, 42),
    ("Thermique bicolore", "frontal", 73.2, 43),
    ("Thermique protégé Kanzan", "frontal", 72, 51),
    ("Thermique protégé Jujo", "frontal", 74.5, 52),
    ("PP blanc Jindal 60ZH647", "frontal", 43.6, 70),
    ("PP blanc Jindal 65LT500", "frontal", 48.8, 71),
    ("Polyart", "frontal", 80, 80),
    ("Foliset 80", "frontal", 74, 81),
    ("Foliset 100", "frontal", 85, 82),
    ("Foliset 120", "frontal", 99.4, 83),
    # Anilox : dépôt d'encre (g/m²) pour un aplat à 100 %.
    ("400L", "anilox", 2, 100),
    ("500L", "anilox", 1.4, 101),
    ("800L", "anilox", 1, 102),
]

_CREATE = """
    CREATE TABLE {nom} (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        libelle      TEXT    NOT NULL UNIQUE,
        famille      TEXT,
        microns      REAL,
        grammage_gsm REAL,
        ordre        INTEGER NOT NULL DEFAULT 0,
        updated_at   TEXT
    )
"""


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(mp_metrage_epaisseurs)").fetchall()}
    if not cols:
        conn.execute(_CREATE.format(nom="mp_metrage_epaisseurs"))
    elif "grammage_gsm" not in cols:
        conn.execute("DROP TABLE IF EXISTS mp_metrage_epaisseurs_nv")
        conn.execute(_CREATE.format(nom="mp_metrage_epaisseurs_nv"))
        conn.execute(
            """INSERT INTO mp_metrage_epaisseurs_nv (id, libelle, microns, ordre, updated_at)
               SELECT id, libelle, microns, ordre, updated_at FROM mp_metrage_epaisseurs"""
        )
        conn.execute("DROP TABLE mp_metrage_epaisseurs")
        conn.execute("ALTER TABLE mp_metrage_epaisseurs_nv RENAME TO mp_metrage_epaisseurs")

    for libelle, famille in _FAMILLES.items():
        conn.execute(
            "UPDATE mp_metrage_epaisseurs SET famille = ? WHERE libelle = ? AND famille IS NULL",
            (famille, libelle),
        )
    for libelle, g in _GRAMMAGES.items():
        conn.execute(
            "UPDATE mp_metrage_epaisseurs SET grammage_gsm = ? WHERE libelle = ? AND grammage_gsm IS NULL",
            (g, libelle),
        )
    n = 0
    for libelle, famille, g, ordre in _SEED:
        cur = conn.execute(
            "INSERT OR IGNORE INTO mp_metrage_epaisseurs (libelle, famille, grammage_gsm, ordre) "
            "VALUES (?,?,?,?)",
            (libelle, famille, g, ordre),
        )
        n += cur.rowcount or 0
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n} grammage(s) seedé(s).")
