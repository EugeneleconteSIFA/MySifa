"""Bobines montées — le lien « remplacée par », et la mémoire des natures rejouée.

Pourquoi une seconde migration plutôt qu'une retouche de `bobines_montees`
------------------------------------------------------------------------
`bobines_montees` est partie sur staging dans le commit `flux_mp_auto`
(10/09/2026, 14:53) avant la fin du chantier : sans la colonne
`remplacee_par_id`, et sans le service `poste_bobine` dont elle se sert pour
rejouer la mémoire des natures. Une migration déjà enregistrée ne se rejoue
jamais — la corriger en place laisserait v1 sans la colonne. Ce fichier
complète donc, sur toutes les bases, ce que la première n'a pas pu faire.

`remplacee_par_id` : quand une bobine est démontée parce qu'une autre a pris
sa place sur un poste plein, le montage qui l'a poussée. C'est ce qui permet,
si le scan de la nouvelle bobine est annulé, de rendre sa place à l'ancienne
au lieu de laisser le poste à moitié vide.

Rejouable : test de présence de colonne, et la reconstruction de la mémoire
remet les compteurs à zéro avant de les refaire.
"""

from __future__ import annotations

import sqlite3

NOM = "bobines_montees_remplacement"
DEPEND = ["bobines_montees"]


def _colonnes(conn: sqlite3.Connection, table: str) -> set:
    try:
        return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}
    except sqlite3.Error:
        return set()


def appliquer(conn: sqlite3.Connection) -> None:
    cols = _colonnes(conn, "bobines_montees")
    if cols and "remplacee_par_id" not in cols:
        conn.execute("ALTER TABLE bobines_montees ADD COLUMN remplacee_par_id INTEGER")
    conn.commit()

    try:
        from app.services.poste_bobine import reconstruire_categories
        bilan = reconstruire_categories(conn)
        conn.commit()
        print(f"[MySifa] migration {NOM} : {bilan['apprises']} identification(s) "
              f"de nature rejouée(s) sur {bilan['scans']} scan(s).")
    except Exception as e:  # la mémoire est un bénéfice, pas une condition
        conn.rollback()
        print(f"[MySifa] migration {NOM} : mémoire des natures non reconstruite ({e}).")
