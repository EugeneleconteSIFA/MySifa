"""
Stock en magasin et stock en production — deux colonnes, pas deux stocks.

Arbitrage d'Eugene du 09/09/2026 : les deux zones se COMPTENT a l'inventaire,
elles ne se suivent pas. Aucun mouvement automatique ne fait passer une bobine
du magasin a la production ; personne ne scannera un deplacement interne, et un
suivi que personne n'alimente est pire qu'une absence de suivi — il donne un
chiffre faux avec l'air d'etre juste.

Consequence sur le schema, et c'est ce qui rend cette migration sans danger :
`quantite` ne change pas de sens. Elle reste LA quantite qui fait foi, celle que
lit tout le reste de l'application. Les deux colonnes ajoutees ne sont qu'un
detail de ce total, renseigne au dernier comptage. Rien ailleurs ne casse, et
une reference jamais comptee par zone les garde a NULL — ce qui se lit
« on ne sait pas », et non « zero en production ».

C'est aussi pour ca que la separation vaut pour TOUTES les matieres et pas
seulement pour les bobines : l'adhesif et les palettes ne se scannent pas, mais
ils sont bien quelque part, et l'inventaire est le seul moment ou quelqu'un
regarde ou.
"""

from __future__ import annotations

import sqlite3

NOM = "stock_zones_magasin_production"


def _colonnes(conn: sqlite3.Connection, table: str) -> set:
    try:
        return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}
    except sqlite3.Error:
        return set()


def appliquer(conn: sqlite3.Connection) -> None:
    ajouts = 0
    for table in ("inventaires_matieres", "mp_stock", "mp_stock_laize"):
        presentes = _colonnes(conn, table)
        if not presentes:
            continue
        for colonne in ("quantite_magasin", "quantite_production"):
            if colonne not in presentes:
                conn.execute("ALTER TABLE %s ADD COLUMN %s REAL" % (table, colonne))
                ajouts += 1
    conn.commit()
    print("[MySifa] migration stock_zones_magasin_production : %d colonne(s) "
          "ajoutee(s). Les zones restent NULL tant qu'aucun inventaire ne les "
          "a comptees — NULL se lit « on ne sait pas », pas « zero »." % ajouts)
