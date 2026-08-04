"""
Impression : support des imprimantes Windows locales (USB / LPT).

Cette migration existait dans app/core/database.py sous le numéro 195 — déjà pris
par « backfill_libres_usage_count ». Son garde-fou testant ce numéro, elle n'a
JAMAIS pu s'exécuter sur une base où l'autre était passée avant elle : la colonne
`type_connexion` y manque encore. Sortie en fichier et identifiée par son nom,
elle rattrape son retard au prochain démarrage, et ne rejoue pas là où elle avait
eu la chance de passer.
"""

NOM = "imprimantes_type_connexion_windows_local"


def appliquer(conn):
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(imprimantes)").fetchall()}
    if not cols:
        return  # table absente : rien à faire
    if "type_connexion" not in cols:
        conn.execute(
            "ALTER TABLE imprimantes ADD COLUMN type_connexion TEXT NOT NULL DEFAULT 'tcp_ip'"
        )
    if "nom_queue_windows" not in cols:
        conn.execute("ALTER TABLE imprimantes ADD COLUMN nom_queue_windows TEXT")
    conn.commit()
