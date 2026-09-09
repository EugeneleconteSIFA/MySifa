"""
Memoire des formats de packing list, un par fournisseur.

« Chaque fournisseur aura sa maniere de gerer cela » (Eugene, 09/09/2026). La
consequence pratique n'est pas qu'il faut ecrire un lecteur par fournisseur :
c'est qu'il faut demander UNE FOIS a un humain quelle colonne est quoi, et ne
plus jamais le redemander.

C'est tout ce que porte cette table : pour un fournisseur, le nom de la colonne
du code-barres, celle de la laize, celle du metrage, celle du lot, et l'unite
de chacune. Rien de calcule, rien de devine — ce qu'un humain a valide.

La cle est `fournisseur_id`, pas le nom. Renommer un fournisseur dans
l'annuaire ne doit pas lui faire perdre son profil ; c'est la meme lecon que
`stock_receptions.fournisseur_id` en aout 2026, ou renommer detachait les
receptions passees de leur licence FSC. Le nom reste en repli, pour les
receptions saisies avant que l'annuaire ne soit branche.

`exemple_fichier` garde le nom du dernier fichier lu avec ce profil. Ce n'est
pas de la decoration : quand un fournisseur change son format, on veut savoir
sur quel fichier le profil actuel a ete valide avant de le corriger.
"""

from __future__ import annotations

import sqlite3

NOM = "stock_packing_profils"
DEPEND = ["stock_bobines"]


def appliquer(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS stock_packing_profils (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            fournisseur_id   INTEGER,
            fournisseur_nom  TEXT,
            colonne_code     TEXT,
            colonne_laize    TEXT,
            colonne_metrage  TEXT,
            colonne_lot      TEXT,
            unite_laize      TEXT,
            unite_metrage    TEXT,
            exemple_fichier  TEXT,
            created_at       TEXT,
            updated_at       TEXT,
            updated_by_name  TEXT
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_packing_fournisseur
            ON stock_packing_profils(fournisseur_id)
            WHERE fournisseur_id IS NOT NULL;

        CREATE UNIQUE INDEX IF NOT EXISTS idx_packing_nom
            ON stock_packing_profils(UPPER(fournisseur_nom))
            WHERE fournisseur_id IS NULL AND fournisseur_nom IS NOT NULL;
        """
    )
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM stock_packing_profils").fetchone()[0]
    print("[MySifa] migration stock_packing_profils : %d format(s) de packing "
          "list memorise(s)." % n)
