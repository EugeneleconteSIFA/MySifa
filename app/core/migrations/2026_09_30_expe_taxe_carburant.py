"""
MyExpé — taxe carburant : date de mise à jour, demande aux transporteurs,
historique.

Le pourcentage lui-même existait déjà (`expe_transporteurs.taxe_carburant_pct`,
appliqué par le comparateur). Ce qui manquait, c'est de savoir QUAND il a été
mis à jour et PAR QUI : la taxe se renégocie chaque mois, arrivait par email
et se recopiait à la main, et rien ne disait si la valeur en base datait de la
semaine ou de l'an dernier.

Colonnes sur la fiche transporteur (cache de lecture, réécrit à chaque saisie) :
  taxe_carburant_maj_le       date de la dernière saisie
  taxe_carburant_maj_source   'portail' (le transporteur) ou 'manuel' (nous)
  taxe_carburant_maj_par      email de l'auteur de la saisie
  taxe_carburant_demande_le   dernière demande de mise à jour envoyée
  taxe_carburant_demande_par  email de l'utilisateur qui l'a envoyée — c'est
                              lui qui reçoit la confirmation

Historique : une ligne par événement. `evenement` vaut 'saisie' ou 'demande' ;
pct / pct_avant sont NULL pour une demande.
"""

NOM = "expe_taxe_carburant_suivi"


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(expe_transporteurs)").fetchall()}
    for col in (
        "taxe_carburant_maj_le",
        "taxe_carburant_maj_source",
        "taxe_carburant_maj_par",
        "taxe_carburant_demande_le",
        "taxe_carburant_demande_par",
    ):
        if col not in cols:
            conn.execute(f"ALTER TABLE expe_transporteurs ADD COLUMN {col} TEXT")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expe_taxe_carburant_historique (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            transporteur_id INTEGER NOT NULL,
            evenement       TEXT NOT NULL,
            source          TEXT,
            pct_avant       REAL,
            pct             REAL,
            auteur          TEXT,
            created_at      TEXT NOT NULL,
            FOREIGN KEY (transporteur_id) REFERENCES expe_transporteurs(id)
        )
        """
    )
    conn.execute(
        """CREATE INDEX IF NOT EXISTS idx_expe_taxe_carb_hist_trp
           ON expe_taxe_carburant_historique(transporteur_id, created_at)"""
    )
    conn.commit()
