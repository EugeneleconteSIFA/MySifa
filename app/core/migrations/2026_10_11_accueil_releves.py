"""
Relevés quotidiens des indicateurs d'accueil.

Une trentaine de blocs capturables affichent un état à l'instant (matières
sous seuil, NC non clôturées, OF à traiter…) que rien ne conserve : leur
courbe ne peut pas se reconstituer après coup, elle ne peut que s'accumuler.
`app/services/accueil_releves.py` photographie donc ces valeurs, côté serveur,
toutes les 30 minutes ; la ligne du jour est réécrite à chaque passage, si bien
qu'elle porte l'état du soir une fois la journée finie.

Une ligne par (bloc, objet suivi, filtres, jour). `objet` et `filtres` valent
'' quand le bloc n'en a pas : une clé primaire n'accepte pas NULL comme valeur
comparable. `valeurs` est un objet JSON {clé: nombre}, avec les clés du
registre (app/services/blocs_registre.py).
"""

NOM = "accueil_releves_table"


def appliquer(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS accueil_releves ("
        " bloc TEXT NOT NULL,"
        " objet TEXT NOT NULL DEFAULT '',"
        " filtres TEXT NOT NULL DEFAULT '',"
        " jour TEXT NOT NULL,"
        " valeurs TEXT NOT NULL DEFAULT '{}',"
        " maj_le TEXT,"
        " PRIMARY KEY (bloc, objet, filtres, jour))"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_accueil_releves_jour"
        " ON accueil_releves(bloc, jour)"
    )
    conn.commit()
