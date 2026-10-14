"""
Étiquettes spécifiques : valeurs de chaque étiquette d'une impression.

Le ZPL suffisait à réimprimer sur une Zebra. Depuis que les imprimantes de
bureau reçoivent un PDF, une réimpression peut changer de langage : il faut
pouvoir redessiner exactement les mêmes étiquettes (mêmes SSCC, mêmes
numéros) à partir de la mise en page et des valeurs, pas du ZPL.
"""

NOM = "etiq_impressions_valeurs_serie"
DEPEND = ["etiquettes_specifiques"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(etiq_impressions)").fetchall()}
    if "valeurs_serie_json" not in cols:
        conn.execute("ALTER TABLE etiq_impressions ADD COLUMN valeurs_serie_json TEXT")
    if "format_sortie" not in cols:
        conn.execute("ALTER TABLE etiq_impressions ADD COLUMN format_sortie TEXT NOT NULL DEFAULT 'zpl'")
    conn.commit()
