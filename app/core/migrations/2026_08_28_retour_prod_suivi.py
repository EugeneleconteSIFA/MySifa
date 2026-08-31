"""
Retour de prod : suivi des remontees d'atelier.

Ce que les conducteurs ecrivent remonte desormais dans la feuille atelier. Il
manquait de quoi en faire quelque chose : dire qu'une remontee a ete traitee,
et y repondre. Deux tables, aucune colonne ajoutee ailleurs.

`retour_prod_ecrits` porte l'etat d'une remontee, designee par une CLE stable
plutot que par une cle etrangere : une remontee peut etre un commentaire de
saisie, une info prod, une explication d'arret ou une note ajoutee ici. Trois
tables differentes, un seul suivi — la cle les reconcilie.

    saisie:<id>      commentaire de saisie      production_data.commentaire
    infoprod:<no>    info prod de cloture       dossier_info_prod.texte
    seuil:<id>       explication d'arret        arret_seuils_franchis
    note:<id>        note ajoutee ici           retour_prod_notes

`retour_prod_notes` porte les notes ajoutees depuis la feuille. `cle_ecrit`
rattache la note a la remontee a laquelle elle repond, ou reste vide pour une
note libre sur le dossier.
"""

NOM = "retour_prod_suivi"


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS retour_prod_ecrits (
            cle        TEXT PRIMARY KEY NOT NULL,
            no_dossier TEXT,
            valide     INTEGER NOT NULL DEFAULT 0,
            valide_par TEXT,
            valide_le  TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_retour_prod_ecrits_dossier
            ON retour_prod_ecrits(no_dossier);

        CREATE TABLE IF NOT EXISTS retour_prod_notes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            no_dossier  TEXT NOT NULL,
            cle_ecrit   TEXT,
            texte       TEXT NOT NULL,
            auteur      TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            updated_at  TEXT,
            updated_par TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_retour_prod_notes_dossier
            ON retour_prod_notes(no_dossier, created_at);
        CREATE INDEX IF NOT EXISTS idx_retour_prod_notes_ecrit
            ON retour_prod_notes(cle_ecrit);
        """
    )
    conn.commit()
    print("[MySifa] migration retour_prod_suivi : retour_prod_ecrits / retour_prod_notes en place.")
