"""
Les cadres du papier atelier qu'aucun champ de l'OF ne porte (nombre de tours,
vitesse, autres outils disponibles, plieuse, Serame…) se remplissent à l'écran.

`cases_libres` : JSON {clé du cadre: texte}. La clé vient du modèle
(`of_pdf_generator.cases_du_modele()["libres"]`) ; le texte s'imprime dans ce
cadre. Une colonne par cadre aurait fait soixante-quinze colonnes pour des
valeurs que personne ne calcule ni ne filtre.
"""

NOM = "of_cases_libres"


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(of_imports)").fetchall()}
    if "cases_libres" not in cols:
        conn.execute("ALTER TABLE of_imports ADD COLUMN cases_libres TEXT")
    conn.commit()
