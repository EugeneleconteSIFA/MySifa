"""Repère « déstocké dans RVGI » du planning, séparé du déstockage MyStock.

Décision d'Eugène du 10/09/2026 : la collègue qui déstocke les dossiers dans
l'ERP continue de poser son point gris sur le planning de prod. Ce repère ne
doit plus rien avoir à faire avec le stock MySifa, qui sort désormais par
MyStock › Déstockage. Les deux vivaient dans la même colonne `destockage` :

- `destockage_rvgi`     : 'todo' / 'done' — le point gris du planning ;
- `destockage_rvgi_at`  : quand le repère a été posé ;
- `destockage_rvgi_par` : par qui.

Reprise, UNE fois (quand la colonne est créée) : un dossier marqué
« déstocké » sans aucun mouvement de stock rattaché a été marqué à la main
par cette collègue — c'était le seul usage du bouton jusqu'au 09/09/2026
(232 dossiers, zéro mouvement). Son repère passe dans `destockage_rvgi`, et
son état MyStock revient à « à destocker » : il n'est rien sorti du stock
MySifa. Un dossier qui porte des mouvements garde son état MyStock et ne
reçoit pas de repère RVGI.

`updated_at` n'est pas touché : le balayage du déstockage automatique s'en
sert pour ne traiter que les clôtures postérieures à sa mise en service.
"""

import sqlite3

NOM = "destockage_rvgi_planning"

_COLONNES = (
    ("destockage_rvgi", "TEXT DEFAULT 'todo'"),
    ("destockage_rvgi_at", "TEXT"),
    ("destockage_rvgi_par", "TEXT"),
)


def _colonnes(conn, table):
    return {r[1] for r in conn.execute("PRAGMA table_info(%s)" % table)}


def appliquer(conn: sqlite3.Connection) -> None:
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if "planning_entries" not in tables:
        print("[MySifa] migration destockage_rvgi : table absente, rien a faire.")
        return
    existantes = _colonnes(conn, "planning_entries")
    reprise = "destockage_rvgi" not in existantes
    for nom, type_sql in _COLONNES:
        if nom not in existantes:
            conn.execute("ALTER TABLE planning_entries ADD COLUMN %s %s" % (nom, type_sql))

    if reprise and "destockage" in existantes:
        sans_mvt = ("NOT EXISTS (SELECT 1 FROM mp_mouvements m "
                    "             WHERE m.planning_entry_id = planning_entries.id)"
                    if "mp_mouvements" in tables else "1=1")
        n = conn.execute(
            "UPDATE planning_entries SET destockage_rvgi='done', "
            "       destockage_rvgi_at=COALESCE(destockage_at, updated_at) "
            " WHERE destockage IN ('done', 'reserve') AND " + sans_mvt).rowcount
        cols_raz = ["destockage='todo'"]
        for c in ("destockage_at", "destockage_reserve", "destockage_par",
                  "destockage_relu_par", "destockage_relu_at"):
            if c in existantes:
                cols_raz.append("%s=NULL" % c)
        conn.execute(
            "UPDATE planning_entries SET " + ", ".join(cols_raz) +
            " WHERE destockage_rvgi='done' AND destockage IN ('done', 'reserve')")
        print("[MySifa] migration destockage_rvgi : %d repère(s) repris." % n)
    conn.commit()
