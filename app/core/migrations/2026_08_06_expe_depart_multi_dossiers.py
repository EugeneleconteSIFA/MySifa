"""
FSC — un départ peut couvrir plusieurs dossiers de fabrication.

Pourquoi c'est nécessaire
-------------------------
`expe_departs.planning_entry_id` ne porte qu'UN dossier. Or la mesure sur la
base de production l'a montré noir sur blanc : 47 départs ont un ARC qui
correspond à plusieurs OF. Le cas n'est pas théorique, il est courant — une
expédition consolide plusieurs commandes, ou un OF est scindé en lignes
(« 9932339 ligne 2 », « 9932232 - L1 »).

Avec un seul rattachement possible, l'expéditionnaire devait choisir un dossier
et taire les autres. Pour un audit FSC c'est le pire des cas : la chaîne
remonte, elle a l'air complète, et elle est partielle sans le dire.

Ce que dit la norme
-------------------
FSC-STD-40-004 n'impose nulle part « un document de vente = un ordre de
fabrication ». Ce qu'elle exige, c'est que le claim soit identifiable POUR
CHAQUE LIGNE du document de vente, et que chaque ligne soit traçable jusqu'à
ses entrées. Un BL groupant plusieurs OF est donc parfaitement recevable — et
le devient d'autant plus qu'on peut nommer tous les OF concernés.

Le seul cas à surveiller est la vente MIXTE : un départ dont une partie des
dossiers est certifiée et l'autre non. Le claim ne peut alors pas être porté
globalement sur le document, il doit l'être ligne par ligne. C'est ce que
`GET /api/fsc/departs/{id}/mention` détecte désormais au lieu de produire une
mention globale fausse.

Ce que fait cette migration
---------------------------
Une table de liaison, et le backfill du lien existant. `expe_departs`
conserve `planning_entry_id` et `no_dossier` : ils désignent le PREMIER
dossier rattaché et restent tenus à jour automatiquement. C'est de la
dénormalisation assumée — une dizaine de requêtes, du traceur au registre,
interrogent une référence de dossier unique, et les casser toutes pour un
champ d'affichage n'aurait rien apporté.
"""

from __future__ import annotations

import sqlite3

NOM = "expe_depart_multi_dossiers"
DEPEND = ["expe_depart_sans_dossier"]


def appliquer(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS expe_depart_dossiers (
               id                INTEGER PRIMARY KEY AUTOINCREMENT,
               depart_id         INTEGER NOT NULL
                                 REFERENCES expe_departs(id) ON DELETE CASCADE,
               planning_entry_id INTEGER NOT NULL
                                 REFERENCES planning_entries(id),
               -- Copie textuelle de la référence au moment du rattachement.
               -- Un dossier renommé ne doit pas réécrire ce qui a été expédié.
               no_dossier        TEXT,
               created_at        TEXT NOT NULL,
               created_by        TEXT,
               UNIQUE(depart_id, planning_entry_id)
           )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_expe_dd_depart ON expe_depart_dossiers(depart_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_expe_dd_planning "
        "ON expe_depart_dossiers(planning_entry_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_expe_dd_no_dossier "
        "ON expe_depart_dossiers(no_dossier)"
    )

    repris = conn.execute(
        """INSERT OR IGNORE INTO expe_depart_dossiers
             (depart_id, planning_entry_id, no_dossier, created_at, created_by)
           SELECT d.id, d.planning_entry_id,
                  COALESCE(NULLIF(TRIM(COALESCE(pe.reference,'')), ''),
                           TRIM(COALESCE(pe.numero_of,''))),
                  COALESCE(d.created_at, datetime('now')),
                  'migration:expe_depart_multi_dossiers'
             FROM expe_departs d
             JOIN planning_entries pe ON pe.id = d.planning_entry_id
            WHERE d.planning_entry_id IS NOT NULL"""
    ).rowcount

    print(
        f"[MySifa] migration expe_depart_multi_dossiers : table de liaison créée, "
        f"{repris} rattachement(s) existant(s) repris. Un départ peut désormais "
        f"couvrir plusieurs dossiers."
    )
