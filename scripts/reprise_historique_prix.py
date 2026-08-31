# -*- coding: utf-8 -*-
"""
Reprise de l'historique des prix : les prix EN VIGUEUR deviennent sa première ligne.

`mp_prix_historique` ne trace que les mouvements survenus depuis sa mise en
service. Résultat : une matière dont le prix n'a pas bougé depuis affiche un
historique vide et « jamais revu » dans la colonne Dernier prix — alors que son
prix a bien été saisi un jour, et que `mp_matiere_prix.updated_at` le sait.

Ce script fait remonter cette date dans l'historique, une ligne par prix en
vigueur, en tête de son historique :

    prix_avant   = NULL          (on ne sait pas ce qu'il y avait avant)
    prix_apres   = le prix en vigueur
    origine      = 'reprise'
    created_at   = mp_matiere_prix.updated_at

Il est IDEMPOTENT : une ligne de reprise déjà posée pour une déclinaison n'est
jamais reposée, et une déclinaison qui a déjà un vrai mouvement daté d'avant sa
dernière écriture est laissée tranquille — son historique se suffit.

──────────────────────────────────────────────────────────────────────────────
Deux étapes
──────────────────────────────────────────────────────────────────────────────

  1.  python3 scripts/reprise_historique_prix.py --simulation

      Montre ce qui serait écrit, ligne par ligne. N'écrit rien.

  2.  python3 scripts/reprise_historique_prix.py --appliquer

      Écrit. Relançable sans doublon.

Options : --db /chemin/production.db pour viser une autre base.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

ORIGINE = "reprise"


def _ouvrir(chemin: str) -> sqlite3.Connection:
    conn = sqlite3.connect(chemin)
    conn.row_factory = sqlite3.Row
    return conn


def _chemin_defaut() -> str:
    try:
        from config import DB_PATH  # type: ignore

        return DB_PATH
    except Exception:
        return os.path.join(RACINE, "data", "production.db")


def collecter(conn: sqlite3.Connection) -> list[dict]:
    """
    Les prix en vigueur qui méritent une ligne de reprise.

    On ne prend que le prix PRINCIPAL de chaque déclinaison : c'est celui qui
    fait foi, et poser une ligne pour chaque offre concurrente remplirait
    l'historique de chiffres que personne n'a jamais appliqués.
    """
    lignes = conn.execute(
        """SELECT p.declinaison_id, d.matiere_id, p.fournisseur_id, p.prix,
                  p.updated_at, p.updated_by_name
             FROM mp_matiere_prix p
             JOIN mp_matiere_declinaison d ON d.id = p.declinaison_id
            WHERE p.declinaison_id IS NOT NULL
              AND p.principal = 1
              AND COALESCE(p.prix, 0) > 0
            ORDER BY d.matiere_id, p.declinaison_id"""
    ).fetchall()

    # Ce que l'historique couvre déjà : une reprise posée, ou un mouvement.
    deja_reprises = {
        int(r["declinaison_id"])
        for r in conn.execute(
            "SELECT DISTINCT declinaison_id FROM mp_prix_historique WHERE origine = ?",
            (ORIGINE,),
        ).fetchall()
        if r["declinaison_id"] is not None
    }
    a_un_mouvement = {
        int(r["declinaison_id"])
        for r in conn.execute(
            """SELECT DISTINCT declinaison_id FROM mp_prix_historique
                WHERE declinaison_id IS NOT NULL AND origine <> ?""",
            (ORIGINE,),
        ).fetchall()
    }

    out: list[dict] = []
    for r in lignes:
        did = int(r["declinaison_id"])
        if did in deja_reprises:
            continue
        if did in a_un_mouvement:
            # Déjà des mouvements tracés : l'historique raconte l'essentiel, et
            # une reprise datée d'aujourd'hui viendrait s'y intercaler en tête
            # comme si le prix avait été revu. On s'abstient.
            continue
        if not r["updated_at"]:
            # Sans date, une reprise n'apprendrait rien : on ne fabrique pas
            # une date d'aujourd'hui pour un prix saisi on ne sait quand.
            continue
        out.append(
            {
                "declinaison_id": did,
                "matiere_id": int(r["matiere_id"]) if r["matiere_id"] is not None else None,
                "fournisseur_id": int(r["fournisseur_id"]) if r["fournisseur_id"] is not None else None,
                "prix": float(r["prix"]),
                "created_at": str(r["updated_at"]),
                "auteur": r["updated_by_name"],
            }
        )
    return out


def appliquer(conn: sqlite3.Connection, lignes: list[dict]) -> int:
    conn.executemany(
        """INSERT INTO mp_prix_historique
           (declinaison_id, matiere_id, fournisseur_id, prix_avant, prix_apres,
            sous_total_avant, sous_total_apres, origine, note,
            created_at, created_by, created_by_name)
           VALUES (?,?,?,NULL,?,NULL,NULL,?,?,?,NULL,?)""",
        [
            (
                l["declinaison_id"],
                l["matiere_id"],
                l["fournisseur_id"],
                l["prix"],
                ORIGINE,
                "Prix en vigueur repris comme première ligne d'historique.",
                l["created_at"],
                l["auteur"],
            )
            for l in lignes
        ],
    )
    conn.commit()
    return len(lignes)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=None, help="chemin de la base (défaut : config.DB_PATH)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--simulation", action="store_true", help="montre sans écrire")
    g.add_argument("--appliquer", action="store_true", help="écrit dans la base")
    a = ap.parse_args()

    chemin = a.db or _chemin_defaut()
    if not os.path.exists(chemin):
        print(f"Base introuvable : {chemin}")
        return 2

    conn = _ouvrir(chemin)
    try:
        lignes = collecter(conn)
        print(f"Base : {chemin}")
        print(f"{len(lignes)} prix en vigueur à reprendre dans l'historique.\n")
        for l in lignes[:40]:
            print(
                f"  décl. {l['declinaison_id']:>5}  "
                f"{l['prix']:>10.4f}  {l['created_at'][:10]}  {l['auteur'] or '—'}"
            )
        if len(lignes) > 40:
            print(f"  … et {len(lignes) - 40} autres.")

        if a.simulation:
            print("\nSimulation : rien n'a été écrit.")
            return 0

        n = appliquer(conn, lignes)
        print(f"\n{n} ligne(s) de reprise écrite(s). Relançable sans doublon.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
