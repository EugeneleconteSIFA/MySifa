#!/usr/bin/env python3
"""
backfill_en_cours_run_start.py — Recalcule planned_start / planned_end des entrées en_cours
selon la règle « run » sur la machine (suffixe production_data homogène, puis fin en heures ouvrées).

Règle (identique à app.routers.planning._prod_run_start_for_machine + consume_duration_from) :
  • Lignes production_data pour la machine (nom ou code), tri date_operation, id.
  • Suffixe final où no_dossier = réf dossier (trim, insensible à la casse).
  • planned_start = date_operation de la 1re ligne de ce suffixe.
  • planned_end = début + duree_heures en heures ouvrées machine (calendrier planning).

Usage :
  cd /chemin/vers/MySifa
  python scripts/backfill_en_cours_run_start.py              # dry-run
  python scripts/backfill_en_cours_run_start.py --apply      # écrit en base
  python scripts/backfill_en_cours_run_start.py --apply --machine-id 3
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Appliquer les UPDATE en base")
    parser.add_argument("--machine-id", type=int, default=None, help="Limiter à une machine (id)")
    args = parser.parse_args()

    from database import get_db
    from app.routers.planning import (
        _fmt_ts,
        _load_planning_calendar_maps,
        _make_work_duration_consumer,
        _prod_run_start_for_machine,
    )

    with get_db() as conn:
        q = """SELECT pe.id, pe.machine_id, pe.numero_of, pe.reference, pe.duree_heures,
                      pe.planned_start, pe.planned_end, pe.statut_force
               FROM planning_entries pe
               WHERE pe.statut = 'en_cours'"""
        params: tuple = ()
        if args.machine_id is not None:
            q += " AND pe.machine_id = ?"
            params = (args.machine_id,)
        rows = conn.execute(q, params).fetchall()

        if not rows:
            print("Aucune entrée statut=en_cours.")
            return

        now_u = datetime.now().isoformat()
        updates = 0
        skipped = 0
        unchanged = 0
        would_change = 0

        for r in rows:
            eid = int(r["id"])
            mid = int(r["machine_id"])
            ref = (r["numero_of"] or r["reference"] or "").strip()
            mrow = conn.execute("SELECT * FROM machines WHERE id=?", (mid,)).fetchone()
            if not mrow:
                print(f"[skip] entry {eid}: machine {mid} introuvable")
                skipped += 1
                continue
            m = dict(mrow)

            run_start = _prod_run_start_for_machine(conn, mid, m, ref) if ref else None
            if run_start is None:
                print(
                    f"[skip] entry {eid} machine={mid} ref={ref!r}: "
                    f"aucun run prod détecté sur cette machine"
                )
                skipped += 1
                continue

            duree_h = float(r["duree_heures"] or 0)
            cfgs, off, dw = _load_planning_calendar_maps(conn, mid)
            _, consume_from = _make_work_duration_consumer(m, cfgs, off, dw)
            p0 = run_start.replace(microsecond=0)
            try:
                _, pe_dt, _ = consume_from(p0, duree_h)
            except Exception as ex:
                print(f"[skip] entry {eid}: consume_duration_from erreur: {ex}")
                skipped += 1
                continue

            ps = _fmt_ts(p0)
            pe = _fmt_ts(pe_dt)
            old_ps, old_pe = r["planned_start"], r["planned_end"]

            if str(old_ps) == ps and str(old_pe) == pe:
                unchanged += 1
                print(f"[ok]   entry {eid} machine={mid} ref={ref!r} — déjà aligné")
                continue

            would_change += 1
            print(
                f"{'[maj]' if args.apply else '[dry]'} entry {eid} machine={mid} ({m.get('nom')}) ref={ref!r}\n"
                f"       planned_start: {old_ps!s} → {ps}\n"
                f"       planned_end:   {old_pe!s} → {pe}"
            )

            if args.apply:
                conn.execute(
                    """UPDATE planning_entries
                       SET planned_start=?, planned_end=?, updated_at=?
                       WHERE id=?""",
                    (ps, pe, now_u, eid),
                )
                updates += 1

        if args.apply:
            conn.commit()
            print(
                f"\nTerminé : {updates} ligne(s) mise(s) à jour, "
                f"{unchanged} déjà alignée(s), {skipped} ignorée(s)."
            )
        else:
            print(
                f"\nDry-run : {len(rows)} entrée(s) en_cours, "
                f"{would_change} seraient modifiée(s), {unchanged} déjà alignée(s), "
                f"{skipped} ignorée(s). Lancez avec --apply pour écrire."
            )


if __name__ == "__main__":
    main()
