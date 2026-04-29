#!/usr/bin/env python3
"""
repair_termine_nullend.py — Répare les dossiers terminés dont planned_end est NULL.

Cause : un bug temporaire (fix durée) a mis planned_end=NULL sur certains terminés.
        compute_slots les ignore (ils disparaissent du planning).

Correctif : planned_end = planned_start + duree_heures (heures calendaires).

Usage :
  python3 scripts/repair_termine_nullend.py            # dry-run
  python3 scripts/repair_termine_nullend.py --apply
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.getenv("DB_PATH", os.path.join(BASE_DIR, "data", "production.db"))


def connect():
    if not os.path.exists(DB_PATH):
        print(f"[ERREUR] Base introuvable : {DB_PATH}")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def find_broken(conn):
    return conn.execute(
        """SELECT pe.id, pe.machine_id, m.nom as machine_nom,
                  pe.reference, pe.client, pe.statut,
                  pe.planned_start, pe.duree_heures
           FROM planning_entries pe
           JOIN machines m ON m.id = pe.machine_id
           WHERE pe.statut = 'termine'
             AND pe.planned_end IS NULL
             AND pe.planned_start IS NOT NULL
           ORDER BY pe.machine_id, pe.position"""
    ).fetchall()


def parse_dt(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    conn = connect()
    rows = find_broken(conn)

    print(f"\n{'='*60}")
    print(f"  repair_termine_nullend — {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"  Base : {DB_PATH}")
    print(f"{'='*60}\n")

    if not rows:
        print("  ✓ Aucun dossier terminé avec planned_end manquant. Rien à réparer.\n")
        return

    print(f"  {len(rows)} dossier(s) à réparer :\n")
    now = datetime.now().isoformat()
    repairs = []

    for r in rows:
        st = parse_dt(r["planned_start"])
        if not st:
            print(f"  ⚠  id={r['id']} ({r['reference']}) — planned_start invalide, ignoré")
            continue
        new_end = _fmt_ts(st + timedelta(hours=float(r["duree_heures"])))
        print(f"  • [{r['machine_nom']}] id={r['id']}  {(r['reference'] or '')[:25]:25}"
              f"  start={str(r['planned_start'])[:16]}  +{r['duree_heures']}h  → end={new_end[:16]}")
        repairs.append((new_end, now, r["id"]))

    if args.apply and repairs:
        for pe, ts, eid in repairs:
            conn.execute(
                "UPDATE planning_entries SET planned_end=?, updated_at=? WHERE id=?",
                (pe, ts, eid),
            )
        conn.commit()
        print(f"\n  ✓ {len(repairs)} dossier(s) réparé(s).")
        print("  → Rechargez le planning dans l'app pour voir les dossiers réapparaître.")
    elif not args.apply:
        print(f"\n  [DRY-RUN] Ajoutez --apply pour appliquer.")

    print()
    conn.close()


def _fmt_ts(dt):
    if dt is None:
        return None
    return dt.replace(microsecond=0).isoformat()


if __name__ == "__main__":
    main()
