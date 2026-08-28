"""
Info prod — le commentaire libre attache a UN dossier de production.

Le probleme : ce qu'on apprend pendant une production ne survit pas au
dossier. Les notes produit (`produit_savoirs`) portent sur la reference et
valent pour toutes ses series ; il manquait l'echelon en dessous, celui du
dossier : « sur celui-la, le client a valide un decalage de 2 mm », « bobine
n°3 defectueuse, reprise a 14 h ».

Une seule ligne par dossier, reecrite en place :

- la fin de dossier (code 89, `fin_dossier`) l'exige — « R.A.S. » est une
  reponse valable, l'absence de reponse n'en est pas une ;
- l'onglet Tracabilite l'affiche en colonne et la laisse modifier par
  quiconque y a acces ;
- la memoire produit la restitue sur la carte de chaque serie passee, et en
  tete du panneau pour le dossier en cours.

`ref_produit_norm` est denormalisee ici pour retrouver d'un seul index toutes
les infos prod d'une reference sans passer par le planning — un dossier finit
par en sortir, l'info doit lui survivre.
"""

NOM = "dossier_info_prod"


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS dossier_info_prod (
            no_dossier       TEXT PRIMARY KEY NOT NULL,
            ref_produit_norm TEXT,
            texte            TEXT NOT NULL,
            auteur           TEXT NOT NULL,
            created_at       TEXT NOT NULL,
            updated_at       TEXT,
            updated_par      TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_dossier_info_prod_ref
            ON dossier_info_prod(ref_produit_norm);
        """
    )
    conn.commit()
    print("[MySifa] migration dossier_info_prod : table dossier_info_prod en place.")
