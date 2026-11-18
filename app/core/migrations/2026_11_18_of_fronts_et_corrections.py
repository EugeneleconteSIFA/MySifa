"""
Ce que l'ADV corrige sur un OF doit survivre à sa réouverture.

`nb_fronts` : le nombre de fronts réellement retenu pour cet OF. Il part de la
fiche, mais 5 OF Access sur 26 relevés le 18/11/2026 s'en écartent, et levées
comme quantités en dépendent.

`champs_corriges` : liste JSON des cases corrigées à la main. `champs_manuels`
ne peut pas servir : à la création, il marque TOUS les champs saisis pour
qu'Access ne les réécrive pas, y compris ceux que le calcul a remplis.
"""

NOM = "of_nb_fronts_champs_corriges"


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(of_imports)").fetchall()}
    if "nb_fronts" not in cols:
        conn.execute("ALTER TABLE of_imports ADD COLUMN nb_fronts INTEGER")
    if "champs_corriges" not in cols:
        conn.execute("ALTER TABLE of_imports ADD COLUMN champs_corriges TEXT")
    conn.commit()
