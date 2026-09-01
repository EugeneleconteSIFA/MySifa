"""
Pieces jointes des notes produit — une note d'atelier peut montrer, pas
seulement raconter.

Le probleme : « contre-partie a regler 2/10e plus bas, sinon casse
echenillage » se comprend a la lecture ; « le defaut est la, en rive gauche,
tous les 40 cm » ne se comprend qu'en photo. L'operateur a un appareil dans la
main et rien pour s'en servir : la note repartait en texte, et le defaut se
redecouvrait au passage suivant.

Une piece = une ligne. Plusieurs pieces par note, dans l'ordre de depot.
Le fichier vit dans `data/uploads/savoirs/`, jamais en base : une photo
d'atelier pese 2 a 4 Mo, et une base SQLite qui les porte se sauvegarde mal.

`est_image` est fige au depot plutot que deduit du mime a l'affichage : c'est
lui qui decide de la vignette, et un mime absent (certains navigateurs mobiles
n'en envoient pas sur une photo prise sur le moment) ne doit pas transformer
une photo en icone de document.

Suppression : une piece deposee par erreur s'efface (auteur ou admin). C'est la
difference avec la note elle-meme, qui se perime et ne se supprime pas — une
note perimee s'apprend encore, une photo floue n'apprend rien.
"""

NOM = "savoir_pieces_jointes"
DEPEND = ["produit_memoire_tables"]


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS produit_savoirs_pieces (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            savoir_id       INTEGER NOT NULL,
            fichier         TEXT NOT NULL,
            fichier_origine TEXT,
            mime            TEXT,
            taille_octets   INTEGER,
            est_image       INTEGER NOT NULL DEFAULT 0,
            auteur          TEXT,
            created_at      TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_savoirs_pieces_savoir
            ON produit_savoirs_pieces(savoir_id, id);
        """
    )
    conn.commit()
    print("[MySifa] migration savoir_pieces_jointes : table produit_savoirs_pieces en place.")
