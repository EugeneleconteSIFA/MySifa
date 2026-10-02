"""
Marge de vente par catégorie de matière.

Un frontal ne se marge pas comme un adhésif : la marge par défaut unique
(`mc_setting.default_margin_pct`) ne suffit plus. Une ligne par catégorie
MyStock (en minuscules : frontal, adhesif, glassine, complexe, autre…).
Une catégorie sans ligne garde la marge par défaut — la table démarre donc
vide, et rien ne change dans les chiffres tant qu'on n'y a rien saisi.
"""

NOM = "mc_marge_categorie"


def appliquer(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mc_marge_categorie (
            categorie   TEXT PRIMARY KEY,
            marge_pct   REAL NOT NULL,
            updated_at  TEXT,
            updated_by  INTEGER
        )
        """
    )
    conn.commit()
