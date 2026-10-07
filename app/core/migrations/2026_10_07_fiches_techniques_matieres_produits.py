"""
Fiches techniques des matières et des produits (Coûts matières).

Une fiche technique décrit ce que le client reçoit : épaisseur, grammage,
type d'adhésif, tenue en température, applications. Rien de ce qui la compose
n'existait en base — le prix, oui, la description technique, non.

Une seule table pour les deux objets : la fiche d'un produit hérite de celles
de ses composants (frontal, adhésif, dorsal) et n'ajoute que ce qui lui est
propre. Les champs vivent dans un JSON : la liste évolue avec les demandes
clients sans migration à chaque ligne de caractéristique.
"""

NOM = "fiches_techniques_matieres_produits"


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS mp_fiche_technique (
               id              INTEGER PRIMARY KEY AUTOINCREMENT,
               objet           TEXT    NOT NULL,
               objet_id        INTEGER NOT NULL,
               data            TEXT    NOT NULL DEFAULT '{}',
               updated_at      TEXT,
               updated_by_name TEXT,
               UNIQUE (objet, objet_id)
           )"""
    )
    conn.commit()
