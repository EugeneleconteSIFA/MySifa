"""Comparer le stock de MySifa à celui de RVGI, et en garder la trace.

Pourquoi une table plutôt qu'un calcul à la volée
-------------------------------------------------
Un écart de stock ne se juge pas sur une photo. « 12 000 étiquettes de
différence » ne veut rien dire ; « 12 000 depuis le 3 août, et ça n'a pas
bougé » veut dire quelque chose, et « 12 000 hier, 40 000 aujourd'hui » veut
dire tout autre chose. On enregistre donc chaque comparaison, et l'écart
devient une courbe.

C'est aussi ce qui distingue un écart corrigé d'un écart masqué : sans
historique, une ligne qui disparaît de la liste ne dit pas laquelle des deux
choses s'est produite.

Deux périmètres
---------------
`pf` — produits finis : `stk_hist` côté RVGI, `produits` + `lots_stock` côté
MySifa. La clé est la référence article `890/0079`, que les deux parlent déjà.

`matiere` — matières : `stm_hist` côté RVGI, `matieres_premieres` + `mp_stock`
côté MySifa. Ici la clé n'est PAS acquise : MySifa nomme ses matières par
catégorie et référence fournisseur, RVGI par `code1/code2`. Le taux de
correspondance est donc mesuré et rendu à chaque comparaison — c'est lui qui
dira s'il faut une table de correspondance avant d'aller plus loin.
"""

from __future__ import annotations

import sqlite3

NOM = "stock_compare"


def appliquer(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS stock_compare_instantanes (
               id            INTEGER PRIMARY KEY AUTOINCREMENT,
               perimetre     TEXT NOT NULL CHECK (perimetre IN ('pf','matiere')),
               cree_le       TEXT NOT NULL,
               cree_par      TEXT,
               -- 'manuel' quand quelqu'un a cliqué, 'synchro' quand c'est le
               -- miroir qui vient d'être reconstruit. Les deux ont leur usage,
               -- et il faut pouvoir distinguer les deux séries.
               origine       TEXT NOT NULL DEFAULT 'manuel',
               miroir_releve_le TEXT,

               nb_rvgi       INTEGER NOT NULL DEFAULT 0,
               nb_mysifa     INTEGER NOT NULL DEFAULT 0,
               nb_communs    INTEGER NOT NULL DEFAULT 0,
               nb_ecarts     INTEGER NOT NULL DEFAULT 0,
               nb_rvgi_seul  INTEGER NOT NULL DEFAULT 0,
               nb_mysifa_seul INTEGER NOT NULL DEFAULT 0,
               nb_negatifs   INTEGER NOT NULL DEFAULT 0,
               ecart_absolu  REAL NOT NULL DEFAULT 0
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS stock_compare_lignes (
               id            INTEGER PRIMARY KEY AUTOINCREMENT,
               instantane_id INTEGER NOT NULL
                             REFERENCES stock_compare_instantanes(id) ON DELETE CASCADE,
               reference     TEXT NOT NULL,
               designation   TEXT,
               stock_rvgi    REAL,
               stock_mysifa  REAL,
               ecart         REAL,
               -- ok | ecart | rvgi_seul | mysifa_seul
               statut        TEXT NOT NULL,
               rvgi_mvt_libelle TEXT,
               rvgi_mvt_date TEXT,
               rvgi_mvt_qte  REAL,
               mysifa_maj_le TEXT
           )"""
    )
    for idx, cols in (
        ("idx_sci_perimetre", "stock_compare_instantanes(perimetre, cree_le)"),
        ("idx_scl_instantane", "stock_compare_lignes(instantane_id, statut)"),
        ("idx_scl_reference", "stock_compare_lignes(reference)"),
    ):
        conn.execute("CREATE INDEX IF NOT EXISTS %s ON %s" % (idx, cols))

    print(
        "[MySifa] migration stock_compare : comparaison RVGI ↔ MySifa prête "
        "(produits finis et matières, avec historique des écarts)."
    )
