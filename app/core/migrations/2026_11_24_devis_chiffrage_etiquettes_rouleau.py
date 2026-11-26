"""
Rentabilité — étiquettes par rouleau du devis (Prix!E12, « NB Etiquettes au
rouleau »), pour comparer le conditionnement chiffré à celui de l'OF.

Les devis déjà lus gardent la colonne vide : elle se remplit à la prochaine
relecture du classeur (comparaison ouverte, ou reprise
`scripts/devis_chiffrage_reprise.py --appliquer`). En attendant, le « B3500 »
du nom de fichier sert de repli.
"""

NOM = "devis_chiffrage_etiquettes_rouleau"
DEPEND = ["rentabilite_chiffrage_parametres"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(devis_chiffrage)").fetchall()}
    if cols and "etiquettes_rouleau" not in cols:
        conn.execute("ALTER TABLE devis_chiffrage ADD COLUMN etiquettes_rouleau REAL")
    conn.commit()
