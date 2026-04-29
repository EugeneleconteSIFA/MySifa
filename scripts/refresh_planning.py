#!/usr/bin/env python3
"""
refresh_planning.py — Remet les dossiers du planning bout-à-bout.

Actions :
  1. Compacte les positions (1, 2, 3 … sans trous) pour chaque machine.
  2. Remet planned_start=NULL / planned_end=NULL sur les dossiers « attente »
     → au prochain GET /api/planning/…/entries, compute_slots recalcule
       tous les créneaux en tenant compte des horaires machine et des jours ouvrés.

Données conservées intactes :
  • Dossiers terminés et leurs dates réelles
  • Dossiers en cours
  • Toutes les infos (référence, client, durée, notes, etc.)

Usage :
  cd /chemin/vers/MySifa
  python scripts/refresh_planning.py            # dry-run (affiche sans modifier)
  python scripts/refresh_planning.py --apply    # applique les changements
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime

# ── Chemin DB (identique à config.py) ──────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.getenv("DB_PATH", os.path.join(BASE_DIR, "data", "production.db"))


def connect():
    if not os.path.exists(DB_PATH):
        print(f"[ERREUR] Base introuvable : {DB_PATH}")
        print("         Vérifiez DB_PATH ou lancez le script depuis le dossier racine du projet.")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_machines(conn):
    return conn.execute(
        "SELECT id, nom, code FROM machines WHERE actif=1 ORDER BY id"
    ).fetchall()


def get_entries(conn, machine_id):
    return conn.execute(
        """SELECT id, position, reference, client, statut, statut_force,
                  planned_start, planned_end, duree_heures
           FROM planning_entries
           WHERE machine_id=?
           ORDER BY position ASC""",
        (machine_id,),
    ).fetchall()


def statut_label(e):
    s = e["statut"] or "attente"
    sf = e["statut_force"] or 0
    tag = " [forcé]" if sf else ""
    return f"{s}{tag}"


def fmt_dt(v):
    if not v:
        return "—"
    return str(v)[:16].replace("T", " ")


# ── Analyse ─────────────────────────────────────────────────────────────────────

def analyse(conn):
    machines = get_machines(conn)
    if not machines:
        print("[!] Aucune machine active trouvée.")
        return

    for m in machines:
        entries = get_entries(conn, m["id"])
        if not entries:
            print(f"\n  ▸ {m['nom']} ({m['code']}) — aucun dossier")
            continue

        n_att  = sum(1 for e in entries if e["statut"] == "attente")
        n_enc  = sum(1 for e in entries if e["statut"] == "en_cours")
        n_ter  = sum(1 for e in entries if e["statut"] == "termine")
        n_null = sum(1 for e in entries if e["statut"] == "attente" and e["planned_start"] is None)

        positions = [e["position"] for e in entries]
        has_gaps  = positions != list(range(1, len(positions) + 1))

        print(f"\n  ▸ {m['nom']} ({m['code']}) — {len(entries)} dossiers"
              f"  (att:{n_att}  enc:{n_enc}  ter:{n_ter})")
        print(f"    Positions    : {positions}")
        print(f"    Gaps posit°  : {'OUI ← sera corrigé' if has_gaps else 'non'}")
        print(f"    Attente null : {n_null}/{n_att}"
              f"  {'← déjà OK' if n_null == n_att else '← sera réinitialisé'}")

        print(f"    {'Pos':>4}  {'Réf':20}  {'Statut':18}  {'Début':16}  {'Fin':16}  {'Durée':>6}")
        print(f"    {'---':>4}  {'---':20}  {'------':18}  {'-----':16}  {'---':16}  {'-----':>6}")
        for e in entries:
            ref   = (e["reference"] or "")[:20]
            stlbl = statut_label(e)[:18]
            d     = fmt_dt(e["planned_start"])
            f     = fmt_dt(e["planned_end"])
            dur   = f"{e['duree_heures']}h"
            print(f"    {e['position']:>4}  {ref:20}  {stlbl:18}  {d:16}  {f:16}  {dur:>6}")


# ── Application ─────────────────────────────────────────────────────────────────

def apply_refresh(conn):
    machines = get_machines(conn)
    now      = datetime.now().isoformat()
    total_pos = 0
    total_inv = 0

    for m in machines:
        entries = get_entries(conn, m["id"])
        if not entries:
            continue

        # 1. Compacter les positions
        positions = [e["position"] for e in entries]
        expected  = list(range(1, len(entries) + 1))
        if positions != expected:
            for new_pos, e in enumerate(entries, start=1):
                if e["position"] != new_pos:
                    conn.execute(
                        "UPDATE planning_entries SET position=?, updated_at=? WHERE id=?",
                        (new_pos, now, e["id"]),
                    )
                    total_pos += 1
            print(f"  ✓ {m['nom']} — positions recompactées : {positions} → {expected}")

        # 2. Invalider les créneaux attente
        result = conn.execute(
            """UPDATE planning_entries
               SET planned_start=NULL, planned_end=NULL, updated_at=?
               WHERE machine_id=? AND statut='attente'
                 AND (planned_start IS NOT NULL OR planned_end IS NOT NULL)""",
            (now, m["id"]),
        )
        n = result.rowcount
        if n:
            total_inv += n
            print(f"  ✓ {m['nom']} — {n} dossier(s) attente réinitialisés (recalcul au prochain GET)")

    conn.commit()
    print(f"\n  → {total_pos} position(s) corrigée(s), {total_inv} créneau(x) invalidé(s).")
    print("  → Ouvrez le planning dans l'app : les dossiers seront recalculés bout-à-bout.")


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true",
                        help="Applique les modifications (sans cet argument : dry-run)")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  refresh_planning.py — {'APPLY' if args.apply else 'DRY-RUN (--apply pour modifier)'}")
    print(f"  Base : {DB_PATH}")
    print(f"  Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    conn = connect()

    print("\n── État actuel ──────────────────────────────────────────────")
    analyse(conn)

    if args.apply:
        print("\n── Application ──────────────────────────────────────────────")
        apply_refresh(conn)
        print("\n── État après correction ────────────────────────────────────")
        analyse(conn)
    else:
        print("\n  [DRY-RUN] Aucune modification. Relancez avec --apply pour corriger.")

    conn.close()
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
