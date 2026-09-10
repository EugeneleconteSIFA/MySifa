"""Bobines héritées d'un dossier à l'autre — d'où vient un scan que personne n'a fait.

Lot 4 du chantier « scan matière en production » (10/09/2026). Au début de
production, les bobines restées montées sur la machine sont reprises sur le
nouveau dossier sans qu'on les rescanne (case « Réutiliser les dernières
matières », cochée par défaut). Chaque reprise écrit une ligne dans
`fab_matieres_utilisees`, parce que c'est là que la traçabilité, le contrôle
FSC et l'alerte de fin de production lisent ce qu'un dossier a consommé.

`herite_de_id` distingue ces lignes d'un scan réel et pointe le scan d'origine.
Sans elle, un audit ne pourrait pas dire si la bobine a été vue sur ce dossier
ou seulement supposée encore en place.
"""

from __future__ import annotations

import sqlite3

NOM = "bobines_heritees"
DEPEND = ["bobines_montees"]


def appliquer(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(fab_matieres_utilisees)")}
    if cols and "herite_de_id" not in cols:
        conn.execute("ALTER TABLE fab_matieres_utilisees ADD COLUMN herite_de_id INTEGER")
    conn.commit()
