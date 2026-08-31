"""
Fin de production sans aucun code matiere scanne : on demande pourquoi.

Un dossier cloture sans bobine scannee ne dit rien de la matiere qui l'a
produit. Ce n'est pas toujours une erreur — un poste de repiquage ne consomme
pas de frontal, une bobine entamee la veille a pu etre scannee sur le dossier
precedent — mais le silence et l'oubli ont exactement la meme allure dans la
base, et c'est precisement ce qu'un audit FSC de chaine de controle vient
regarder.

La colonne porte donc la reponse de l'operateur, attachee a la saisie 89 qui
l'a declenchee. Elle reste vide quand au moins un code a ete scanne : la
question ne se pose pas, et une valeur par defaut ferait croire a une reponse.
"""

NOM = "matiere_absente_motif"


def appliquer(conn):
    cols = {r["name"] for r in conn.execute(
        "PRAGMA table_info(production_data)").fetchall()}
    if "matiere_absente_motif" not in cols:
        conn.execute(
            "ALTER TABLE production_data ADD COLUMN matiere_absente_motif TEXT")
        conn.commit()
        print("[MySifa] migration matiere_absente_motif : colonne ajoutee.")
    else:
        print("[MySifa] migration matiere_absente_motif : deja en place.")
