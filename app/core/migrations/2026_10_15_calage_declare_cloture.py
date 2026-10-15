"""Calage déclaré à la clôture d'un dossier.

Le constat (15/10/2026)
-----------------------
Le temps de calage se déduit des clics : du « 02 Calage » jusqu'à la saisie
suivante. Sur six mois, 180 calages fermés par un « 03 Production » durent en
moyenne 98 min, avec un maximum de 7 h, et six ne se ferment qu'au « 86
Arrivée personnel » du lendemain. Ce sont des clics oubliés, pas des calages.

Le dossier de prod papier, lui, porte trois heures notées à la main : début de
calage, fin de calage, fin de prod. À la clôture, l'opérateur les recopie.

Ce que la migration installe
----------------------------
`dossier_calages_declares` — une ligne par clôture. Les trois heures
déclarées, les trois heures que les saisies donnaient avant correction, et
pour chacune si la correction a pu être appliquée aux saisies. Une heure qui
enjamberait une autre saisie n'est pas appliquée : elle reste ici, avec son
motif, pour Retour de prod.

Les saisies, elles, sont corrigées en place (heure déplacée, ou « 03
Production » inséré quand il manquait), avec `modifie_par` / `modifie_note` :
c'est ce qui garde tous les écrans d'accord sans toucher à leurs calculs. Les
heures d'origine ne se perdent pas, elles sont dans cette table.
"""

NOM = "calage_declare_cloture"


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS dossier_calages_declares (
               id                    INTEGER PRIMARY KEY AUTOINCREMENT,
               no_dossier            TEXT NOT NULL,
               machine               TEXT NOT NULL,
               saisie_cloture_id     INTEGER,
               debut_calage_declare  TEXT,
               fin_calage_declare    TEXT,
               fin_prod_declare      TEXT,
               debut_calage_mesure   TEXT,
               fin_calage_mesure     TEXT,
               fin_prod_mesure       TEXT,
               calage_mesure_min     REAL,
               debut_applique        INTEGER NOT NULL DEFAULT 0,
               fin_calage_applique   INTEGER NOT NULL DEFAULT 0,
               fin_prod_applique     INTEGER NOT NULL DEFAULT 0,
               motifs_non_appliques  TEXT,
               declare_par           TEXT,
               declare_le            TEXT NOT NULL
           )"""
    )
    conn.execute(
        """CREATE INDEX IF NOT EXISTS idx_calages_declares_dossier
           ON dossier_calages_declares(no_dossier, machine)"""
    )
    conn.commit()
