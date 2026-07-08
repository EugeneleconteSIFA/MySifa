"""Backfill retroactive de `quantite_apres` (et `quantite_avant` quand possible)
pour les mouvements historiques ou l'information a ete perdue.

Cibles :
- `mouvements_stock` (produits finis) : cle = (produit_id, emplacement).
  Le solde reconstitue = stock a l'emplacement APRES le mouvement.
  Source verite du present : `stock_emplacements.quantite`.
- `mp_mouvements` (matieres premieres) : cle = (matiere_id, COALESCE(laize_id, 0)).
  Pour les laizees, on suit `mp_stock_laize` (par laize).
  Pour les non-laizees, on suit `mp_stock`.
  Les transferts sont neutres au niveau matiere-wide.

Algorithme :
  Pour chaque cle :
    running = stock actuel
    pour chaque mvt de la cle en ordre DESCENDANT (created_at, id) :
      si quantite_apres IS NULL: set quantite_apres = running
      sinon: running = quantite_apres (resynchronisation)
      calcul reculte pour trouver `quantite_avant`:
        - entree  : prev = running - quantite
        - sortie  : prev = running + quantite
        - ajustement/inventaire : prev = quantite_avant (deja stocke) sinon arrete
        - transfert (MP) : prev = running (neutre)
      si quantite_avant IS NULL: set quantite_avant = prev
      running = prev

Usage :
    python3 scripts/backfill_quantite_apres.py             # dry-run par defaut
    python3 scripts/backfill_quantite_apres.py --apply     # ecrit
    python3 scripts/backfill_quantite_apres.py --apply --scope pf  # PF seulement
    python3 scripts/backfill_quantite_apres.py --apply --scope mp  # MP seulement

Aucune migration schema : la colonne existe deja. Toujours faire un backup DB
avant --apply. Recommande : lancer d'abord sur v1 (DB isolee) puis promouvoir.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections import defaultdict
from typing import Iterable

# Import config.py racine (source de verite pour DB_PATH)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config import DB_PATH  # noqa: E402

EPS = 1e-6


def _fmt(v):
    if v is None:
        return "NULL"
    return f"{v:.4f}".rstrip("0").rstrip(".")


def _iter_pf_keys(conn: sqlite3.Connection) -> Iterable[tuple[int, str]]:
    """Liste toutes les cles (produit_id, emplacement) touchees par au moins un mouvement."""
    rows = conn.execute(
        """SELECT DISTINCT produit_id, emplacement
           FROM mouvements_stock
           WHERE produit_id IS NOT NULL AND emplacement IS NOT NULL"""
    ).fetchall()
    return [(r["produit_id"], r["emplacement"]) for r in rows]


def _iter_mp_keys(conn: sqlite3.Connection) -> Iterable[tuple[int, int | None]]:
    """Liste toutes les cles (matiere_id, laize_id) touchees par au moins un mouvement."""
    rows = conn.execute(
        """SELECT DISTINCT matiere_id, laize_id
           FROM mp_mouvements
           WHERE matiere_id IS NOT NULL"""
    ).fetchall()
    return [(r["matiere_id"], r["laize_id"]) for r in rows]


def _pf_current_stock(conn, produit_id: int, emplacement: str) -> float:
    r = conn.execute(
        "SELECT quantite FROM stock_emplacements WHERE produit_id=? AND emplacement=?",
        (produit_id, emplacement),
    ).fetchone()
    return float(r["quantite"]) if r and r["quantite"] is not None else 0.0


def _mp_current_stock(conn, matiere_id: int, laize_id: int | None) -> float:
    if laize_id is not None:
        r = conn.execute(
            "SELECT quantite FROM mp_stock_laize WHERE matiere_id=? AND laize_id=?",
            (matiere_id, laize_id),
        ).fetchone()
        return float(r["quantite"]) if r and r["quantite"] is not None else 0.0
    r = conn.execute(
        "SELECT quantite FROM mp_stock WHERE matiere_id=?",
        (matiere_id,),
    ).fetchone()
    return float(r["quantite"]) if r and r["quantite"] is not None else 0.0


def _backfill_key_pf(conn, produit_id: int, emplacement: str, apply: bool) -> dict:
    """Backfill pour une cle PF. Retourne stats {rows_seen, backfilled_apres, backfilled_avant, stopped}."""
    mvts = conn.execute(
        """SELECT id, type_mouvement, quantite, quantite_avant, quantite_apres, created_at
           FROM mouvements_stock
           WHERE produit_id=? AND emplacement=?
           ORDER BY created_at DESC, id DESC""",
        (produit_id, emplacement),
    ).fetchall()

    running = _pf_current_stock(conn, produit_id, emplacement)
    seen = filled_apres = filled_avant = 0
    stopped = False

    for m in mvts:
        seen += 1
        mid = m["id"]
        t = (m["type_mouvement"] or "").strip().lower()
        qte = float(m["quantite"] or 0)
        q_avant = m["quantite_avant"]
        q_apres = m["quantite_apres"]

        # Etat APRES = running (si NULL, on ecrit)
        if q_apres is None:
            if apply:
                conn.execute(
                    "UPDATE mouvements_stock SET quantite_apres=? WHERE id=?",
                    (running, mid),
                )
            filled_apres += 1
            q_apres = running
        else:
            # Resynchronise sur la valeur historique connue
            running = float(q_apres)

        # Reconstituer l'etat AVANT
        if t == "entree":
            prev = running - qte
        elif t == "sortie":
            prev = running + qte
        elif t in ("ajustement", "inventaire"):
            if q_avant is not None:
                prev = float(q_avant)
            else:
                # Impossible de remonter avant un ajustement sans donnee.
                stopped = True
                break
        elif t == "transfert":
            # Cote PF, un transfert est represente comme sortie source + entree dest.
            # Chaque ligne bouge le stock a son emplacement. On traite comme entree/sortie.
            # Ici on ne l'attend pas (rare cote PF), on prend prev = running par prudence.
            prev = running
        else:
            # Type inconnu : on stoppe pour ne pas corrompre.
            stopped = True
            break

        if m["quantite_avant"] is None:
            if apply:
                conn.execute(
                    "UPDATE mouvements_stock SET quantite_avant=? WHERE id=?",
                    (prev, mid),
                )
            filled_avant += 1

        running = prev

    return {
        "seen": seen,
        "filled_apres": filled_apres,
        "filled_avant": filled_avant,
        "stopped": stopped,
        "final_running": running,
    }


def _backfill_key_mp(conn, matiere_id: int, laize_id: int | None, apply: bool) -> dict:
    """Backfill pour une cle MP."""
    # Filtre pertinent : mouvements de cette matiere; si laize_id defini, meme laize.
    if laize_id is None:
        mvts = conn.execute(
            """SELECT id, type_mouvement, quantite, quantite_avant, quantite_apres,
                      emplacement_source, emplacement_dest, created_at
               FROM mp_mouvements
               WHERE matiere_id=? AND laize_id IS NULL
               ORDER BY created_at DESC, id DESC""",
            (matiere_id,),
        ).fetchall()
    else:
        mvts = conn.execute(
            """SELECT id, type_mouvement, quantite, quantite_avant, quantite_apres,
                      emplacement_source, emplacement_dest, created_at
               FROM mp_mouvements
               WHERE matiere_id=? AND laize_id=?
               ORDER BY created_at DESC, id DESC""",
            (matiere_id, laize_id),
        ).fetchall()

    running = _mp_current_stock(conn, matiere_id, laize_id)
    seen = filled_apres = filled_avant = 0
    stopped = False

    for m in mvts:
        seen += 1
        mid = m["id"]
        t = (m["type_mouvement"] or "").strip().lower()
        qte = float(m["quantite"] or 0)
        q_avant = m["quantite_avant"]
        q_apres = m["quantite_apres"]

        if q_apres is None:
            if apply:
                conn.execute(
                    "UPDATE mp_mouvements SET quantite_apres=? WHERE id=?",
                    (running, mid),
                )
            filled_apres += 1
            q_apres = running
        else:
            running = float(q_apres)

        if t == "entree":
            prev = running - qte
        elif t == "sortie":
            prev = running + qte
        elif t == "ajustement":
            if q_avant is not None:
                prev = float(q_avant)
            else:
                stopped = True
                break
        elif t == "transfert":
            # Neutre au niveau matiere-wide (source out + dest in equilibre)
            prev = running
        else:
            stopped = True
            break

        if m["quantite_avant"] is None:
            if apply:
                conn.execute(
                    "UPDATE mp_mouvements SET quantite_avant=? WHERE id=?",
                    (prev, mid),
                )
            filled_avant += 1

        running = prev

    return {
        "seen": seen,
        "filled_apres": filled_apres,
        "filled_avant": filled_avant,
        "stopped": stopped,
        "final_running": running,
    }


def run(scope: str, apply: bool) -> None:
    print(f"[backfill] DB = {DB_PATH}")
    print(f"[backfill] mode = {'APPLY (writes to DB)' if apply else 'DRY-RUN (no writes)'}")
    print(f"[backfill] scope = {scope}")
    print()

    if not os.path.exists(DB_PATH):
        print(f"ERREUR : DB introuvable ({DB_PATH})")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    totals = defaultdict(int)
    stopped_keys = []

    try:
        if scope in ("tout", "pf"):
            pf_keys = list(_iter_pf_keys(conn))
            print(f"[PF] {len(pf_keys)} cles (produit, emplacement)")
            for produit_id, emplacement in pf_keys:
                stats = _backfill_key_pf(conn, produit_id, emplacement, apply)
                totals["pf_seen"] += stats["seen"]
                totals["pf_filled_apres"] += stats["filled_apres"]
                totals["pf_filled_avant"] += stats["filled_avant"]
                if stats["stopped"]:
                    stopped_keys.append(("PF", produit_id, emplacement))
                if abs(stats["final_running"]) > EPS and stats["seen"] > 0 and not stats["stopped"]:
                    # Incoherence : apres avoir tout remonte, on ne devrait pas avoir de stock avant le tout premier mvt.
                    # C'est ok si l'historique commence a un stock initial non-zero.
                    totals["pf_nonzero_initial"] += 1

        if scope in ("tout", "mp"):
            mp_keys = list(_iter_mp_keys(conn))
            print(f"[MP] {len(mp_keys)} cles (matiere, laize)")
            for matiere_id, laize_id in mp_keys:
                stats = _backfill_key_mp(conn, matiere_id, laize_id, apply)
                totals["mp_seen"] += stats["seen"]
                totals["mp_filled_apres"] += stats["filled_apres"]
                totals["mp_filled_avant"] += stats["filled_avant"]
                if stats["stopped"]:
                    stopped_keys.append(("MP", matiere_id, laize_id))
                if abs(stats["final_running"]) > EPS and stats["seen"] > 0 and not stats["stopped"]:
                    totals["mp_nonzero_initial"] += 1

        if apply:
            conn.commit()
            print("[backfill] COMMIT ok")
        else:
            conn.rollback()
    finally:
        conn.close()

    print()
    print("=== Bilan ===")
    if scope in ("tout", "pf"):
        print(f"PF : {totals['pf_seen']} mvts vus | "
              f"{totals['pf_filled_apres']} quantite_apres backfilles | "
              f"{totals['pf_filled_avant']} quantite_avant backfilles")
        if totals["pf_nonzero_initial"]:
            print(f"     -> {totals['pf_nonzero_initial']} cles avec stock initial non-zero (normal si import migre)")
    if scope in ("tout", "mp"):
        print(f"MP : {totals['mp_seen']} mvts vus | "
              f"{totals['mp_filled_apres']} quantite_apres backfilles | "
              f"{totals['mp_filled_avant']} quantite_avant backfilles")
        if totals["mp_nonzero_initial"]:
            print(f"     -> {totals['mp_nonzero_initial']} cles avec stock initial non-zero (normal si import migre)")

    if stopped_keys:
        print()
        print(f"! {len(stopped_keys)} cles ont ete stoppees (ajustement sans quantite_avant, ou type inconnu) :")
        for kind, a, b in stopped_keys[:20]:
            print(f"  - {kind} : {a} / {b}")
        if len(stopped_keys) > 20:
            print(f"  ... et {len(stopped_keys) - 20} autres")

    if not apply:
        print()
        print("(dry-run : aucune ecriture. Relancer avec --apply pour committer.)")


def main():
    parser = argparse.ArgumentParser(description="Backfill quantite_apres/quantite_avant.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Ecrit reellement en base. Par defaut : dry-run seulement.",
    )
    parser.add_argument(
        "--scope",
        choices=("tout", "pf", "mp"),
        default="tout",
        help="Perimetre : tout / pf (produits finis) / mp (matieres premieres).",
    )
    args = parser.parse_args()
    run(args.scope, args.apply)


if __name__ == "__main__":
    main()
