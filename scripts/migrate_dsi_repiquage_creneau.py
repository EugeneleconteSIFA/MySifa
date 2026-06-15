"""MySifa — Script one-shot : creneau 'journee' -> 'matin' pour DSI + Repiquage.

Contexte : le planning RH pour DSI et Repiquage est passe de 'journee' a un
split matin/apres-midi (comme Cohesio 1 et 2). Les affectations existantes en
base sont sur creneau='journee' et n'apparaissent plus dans la nouvelle vue.

Cette migration deplace toutes ces affectations vers creneau='matin' (defaut).
L'utilisateur ajustera ensuite vers 'aprem' au cas par cas via l'icone oeil.

Idempotent : enregistre la migration version=113 dans schema_migrations. Une
seconde execution ne fera rien.

Utilisation sur le VPS (v1 ou prod) :
    cd /home/sifa/production-saas-v1   # ou /home/sifa/production-saas pour prod
    python3 scripts/migrate_dsi_repiquage_creneau.py

Note : v1 et v2 partagent la meme base de donnees, donc une seule execution
suffit. Une fois jouee, la migration officielle dans _migrate() (version 113)
detectera la trace et ne refera rien lors de la promotion v2.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Resolution du chemin DB via config.py (source de verite)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config import DB_PATH  # noqa: E402


def normalise(nom: str) -> str:
    n = (nom or "").lower().strip()
    return (
        n.replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("â", "a")
        .replace("î", "i")
        .replace("ô", "o")
    )


def is_target(nom: str) -> bool:
    n = normalise(nom)
    if n == "dsi" or n.startswith("dsi ") or n.endswith(" dsi"):
        return True
    if "repiquage" in n or n == "rep" or n.startswith("rep "):
        return True
    return False


def main() -> int:
    print(f"DB : {DB_PATH}")
    if not Path(DB_PATH).exists():
        print("ERREUR : fichier DB introuvable", file=sys.stderr)
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        # Garantir l'existence de la table schema_migrations
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "  version INTEGER PRIMARY KEY,"
            "  name TEXT NOT NULL,"
            "  applied_at TEXT NOT NULL)"
        )

        deja = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version=113 LIMIT 1"
        ).fetchone()
        if deja:
            print("Migration 113 deja appliquee, rien a faire.")
            return 0

        machines = conn.execute(
            "SELECT id, nom FROM machines WHERE actif = 1"
        ).fetchall()
        targets = [m["id"] for m in machines if is_target(m["nom"])]
        if not targets:
            print("Aucune machine DSI/Repiquage active trouvee. "
                  "Enregistrement de la migration sans rien modifier.")
        else:
            noms = ", ".join(
                f"{m['nom']} (id={m['id']})"
                for m in machines if is_target(m["nom"])
            )
            print(f"Machines ciblees : {noms}")

            before = conn.execute(
                "SELECT COUNT(*) AS c FROM rh_planning_postes "
                "WHERE machine_id IN ("
                + ",".join(["?"] * len(targets))
                + ") AND creneau = 'journee'",
                targets,
            ).fetchone()["c"]
            print(f"Affectations 'journee' a deplacer : {before}")

            placeholders = ",".join(["?"] * len(targets))
            sql = (
                "UPDATE rh_planning_postes "
                "SET creneau = 'matin' "
                "WHERE machine_id IN (" + placeholders + ") "
                "AND creneau = 'journee'"
            )
            cur = conn.execute(sql, targets)
            print(f"Lignes modifiees : {cur.rowcount}")

        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations "
            "(version, name, applied_at) VALUES (?, ?, ?)",
            (113, "dsi_repiquage_creneau_matin", datetime.now().isoformat()),
        )
        conn.commit()
        print("Migration 113 enregistree. OK.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
