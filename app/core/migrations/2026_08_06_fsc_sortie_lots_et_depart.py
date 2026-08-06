"""
FSC — une sortie de stock dit enfin QUELS lots sont partis, et sur quel départ.

Le problème
-----------
`apply_fifo_sortie()` consomme potentiellement plusieurs lots — c'est le
principe même du FIFO — mais n'écrit qu'UNE ligne dans `mouvements_stock`,
agrégée, sans `lot_id`. La migration 221 avait rattaché les ENTRÉES à leur lot
et s'était arrêtée là, en le disant : « une sortie FIFO touche potentiellement
plusieurs lots, on ne devine pas lequel rétroactivement ».

Résultat, côté audit : on sait d'où vient une palette, jamais où elle est
allée. Et rien ne relie une sortie à l'expédition qui l'a provoquée. Un
auditeur FSC qui demande « prouvez-moi que la palette partie sur ce BL vient
bien du dossier certifié » n'obtient qu'une déduction par le dossier — ce qui
suffit tant qu'un dossier ne produit qu'un lot, et cesse de suffire dès qu'il
en produit plusieurs.

Ce que fait cette migration
---------------------------
1. `mouvements_stock_lots` — le détail de consommation, une ligne par lot
   réellement entamé par un mouvement. C'est la table qui manquait : elle
   transforme un total en une liste de lots identifiés.

   `fsc` et `no_dossier` y sont recopiés au moment de la consommation, pas lus
   par jointure. Un enregistrement de chaîne de contrôle doit rester vrai même
   si le lot est corrigé après coup — c'est le même principe que le verdict de
   certificat figé à la date du BL dans le module négoce.

2. `mouvements_stock.expe_depart_id` — le départ qui a provoqué la sortie.
   Sans lui, la chaîne s'arrête au stock et reprend, sans continuité, au bon
   de livraison.

Ce qu'elle ne fait PAS
----------------------
Aucun backfill. Les sorties passées ont consommé des lots qu'aucune donnée ne
permet de retrouver : les quantités restantes ont déjà été décrémentées, et
reconstituer l'ordre FIFO a posteriori produirait une chaîne plausible mais
fausse. Une chaîne fausse coûte plus cher à un audit qu'une chaîne absente : on
laisse le passé vide et le traceur le dira.
"""

from __future__ import annotations

import sqlite3

NOM = "fsc_sortie_lots_et_depart"
DEPEND = ["fsc_expe_dossier_vivant"]


def _colonnes(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def appliquer(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS mouvements_stock_lots (
               id            INTEGER PRIMARY KEY AUTOINCREMENT,
               mouvement_id  INTEGER NOT NULL REFERENCES mouvements_stock(id) ON DELETE CASCADE,
               lot_id        INTEGER NOT NULL REFERENCES lots_stock(id),
               quantite      REAL NOT NULL,
               fsc           INTEGER NOT NULL DEFAULT 0,
               no_dossier    TEXT,
               created_at    TEXT NOT NULL
           )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mvt_lots_mouvement "
        "ON mouvements_stock_lots(mouvement_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mvt_lots_lot ON mouvements_stock_lots(lot_id)"
    )

    cols = _colonnes(conn, "mouvements_stock")
    if "expe_depart_id" not in cols:
        conn.execute(
            "ALTER TABLE mouvements_stock ADD COLUMN expe_depart_id "
            "INTEGER REFERENCES expe_departs(id)"
        )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mvt_expe_depart "
        "ON mouvements_stock(expe_depart_id)"
    )

    sorties_muettes = conn.execute(
        "SELECT COUNT(*) FROM mouvements_stock WHERE type_mouvement='sortie'"
    ).fetchone()[0]

    print(
        f"[MySifa] migration fsc_sortie_lots_et_depart : table de consommation créée. "
        f"{sorties_muettes} sortie(s) antérieure(s) restent sans détail de lots — "
        f"non reconstituables, elles ressortiront comme telles dans le traceur."
    )
