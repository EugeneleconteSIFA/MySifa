"""Qui a déstocké un dossier, et qui l'a relu.

MyStock gagne le 10/09/2026 un espace Déstockage : « à traiter », « déstockés »
et le suivi de ce qui a été validé. Or `planning_entries` ne savait dire que
QUAND un dossier avait été déstocké (`destockage_at`), pas par qui — et rien
ne distinguait une sortie automatique jamais regardée d'une sortie relue et
corrigée par la personne qui a vu la production. C'est pourtant toute la
différence entre un stock présumé et un stock vérifié.

- `destockage_par`     : qui a écrit la sortie (« Déstockage automatique »
                         quand c'est le balayage).
- `destockage_relu_par`: qui a enregistré la relecture (ajustement, lever la
                         réserve) — c'est le « validé » de l'écran.
- `destockage_relu_at` : quand.

Aucune reprise : les dossiers déjà déstockés restent « non relus », ce qui est
exact.
"""

import sqlite3

NOM = "destockage_suivi_relecture"

_COLONNES = (
    ("destockage_par", "TEXT"),
    ("destockage_relu_par", "TEXT"),
    ("destockage_relu_at", "TEXT"),
)


def _colonnes(conn, table):
    return {r[1] for r in conn.execute("PRAGMA table_info(%s)" % table)}


def appliquer(conn: sqlite3.Connection) -> None:
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if "planning_entries" not in tables:
        print("[MySifa] migration destockage_suivi : table absente, rien a faire.")
        return
    existantes = _colonnes(conn, "planning_entries")
    for nom, type_sql in _COLONNES:
        if nom not in existantes:
            conn.execute("ALTER TABLE planning_entries ADD COLUMN %s %s" % (nom, type_sql))
    conn.commit()
