#!/usr/bin/env python3
"""
One-shot maintenance script.

Recalcule planned_start / planned_end des dossiers statut='attente' pour chaque machine active,
à partir de la fin du dossier 'en_cours' (si planifiée) sinon "maintenant" arrondi à l'heure,
en utilisant le moteur d'heures ouvrées de la timeline (mêmes fonctions que GET /timeline).

Ne modifie jamais les dossiers 'termine' ni 'en_cours'.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, List, Optional, Tuple

from app.core.database import get_db

# Réutiliser strictement le même moteur que la timeline / pack-attente.
from app.routers.planning import (  # noqa: PLC0415
    _TZ_PARIS,
    _fmt_ts,
    _load_planning_calendar_maps,
    _make_work_duration_consumer,
    _parse_planned_dt,
)


@dataclass(frozen=True)
class DiffRow:
    entry_id: int
    old_start: str
    old_end: str
    new_start: str
    new_end: str


def _round_now_to_hour_paris() -> datetime:
    return datetime.now(_TZ_PARIS).replace(tzinfo=None, minute=0, second=0, microsecond=0)


def _to_float(v: Any) -> float:
    try:
        return float(v or 0.0)
    except Exception:
        return 0.0


def _load_anchor_dt(conn, machine_id: int, consume_from) -> datetime:
    """Point d'ancrage : fin 'en_cours' si présente, sinon maintenant arrondi à l'heure (Paris).

    Aligne la logique de /pack-attente avec un fallback robuste si planned_end manque.
    """
    anchor = conn.execute(
        """SELECT planned_end, planned_start, duree_heures
           FROM planning_entries
           WHERE machine_id=? AND statut='en_cours'
           ORDER BY position ASC LIMIT 1""",
        (machine_id,),
    ).fetchone()

    dt0: Optional[datetime] = None
    if anchor and (anchor["planned_end"] or "").strip():
        dt0 = _parse_planned_dt(anchor["planned_end"])

    # Fallback : si on a planned_start + duree_heures, reconstruire planned_end.
    if not dt0 and anchor and (anchor["planned_start"] or "").strip():
        dt_ps = _parse_planned_dt(anchor["planned_start"])
        if dt_ps:
            dur = _to_float(anchor["duree_heures"])
            if dur > 1e-6:
                _, dt0, _ = consume_from(dt_ps.replace(microsecond=0), dur)

    if not dt0:
        dt0 = _round_now_to_hour_paris()

    return dt0.replace(second=0, microsecond=0)


def _partition_waits(waits: Iterable[dict]) -> List[dict]:
    main_entries: List[dict] = []
    aplacer_entries: List[dict] = []
    for e in waits:
        try:
            ap = int(e.get("a_placer") or 0)
        except Exception:
            ap = 0
        (aplacer_entries if ap == 1 else main_entries).append(e)
    return main_entries + aplacer_entries


def _compute_waits_diffs_for_machine(conn, machine_id: int, *, apply: bool) -> Tuple[int, List[DiffRow]]:
    mrow = conn.execute("SELECT * FROM machines WHERE id=? AND actif=1", (machine_id,)).fetchone()
    if not mrow:
        return 0, []
    m = dict(mrow)

    cfgs, off, dw, dh = _load_planning_calendar_maps(conn, machine_id)
    advance_to_work, consume_from = _make_work_duration_consumer(m, cfgs, off, dw, dh)

    dt0 = _load_anchor_dt(conn, machine_id, consume_from)
    cursor = advance_to_work(dt0)

    waits = conn.execute(
        """SELECT id, position, duree_heures, a_placer, planned_start, planned_end
           FROM planning_entries
           WHERE machine_id=? AND statut='attente'
           ORDER BY position ASC""",
        (machine_id,),
    ).fetchall()
    waits_list = [dict(r) for r in waits]
    ordered = _partition_waits(waits_list)

    diffs: List[DiffRow] = []
    now_u = datetime.now().isoformat()
    updated = 0

    for e in ordered:
        dur = _to_float(e.get("duree_heures"))
        if dur <= 1e-6:
            continue

        slot_start, slot_end, cursor = consume_from(cursor, dur)
        new_ps, new_pe = _fmt_ts(slot_start), _fmt_ts(slot_end)

        old_ps = str(e.get("planned_start") or "")
        old_pe = str(e.get("planned_end") or "")
        if old_ps != new_ps or old_pe != new_pe:
            diffs.append(
                DiffRow(
                    entry_id=int(e["id"]),
                    old_start=old_ps,
                    old_end=old_pe,
                    new_start=new_ps,
                    new_end=new_pe,
                )
            )
            updated += 1

        if apply:
            conn.execute(
                """UPDATE planning_entries
                   SET planned_start=?, planned_end=?, planned_end_manual=0, updated_at=?
                   WHERE id=? AND machine_id=?""",
                (new_ps, new_pe, now_u, int(e["id"]), machine_id),
            )

    return updated, diffs


def _print_machine_report(machine_name: str, machine_id: int, updated: int, diffs: List[DiffRow]) -> None:
    print(f"- Machine {machine_name} (id={machine_id}): {updated} attente(s) recalée(s)")
    if not diffs:
        return
    print("  Exemples (5 premières modifications):")
    for d in diffs[:5]:
        old = f"{d.old_start} → {d.old_end}" if (d.old_start or d.old_end) else "(vide)"
        new = f"{d.new_start} → {d.new_end}"
        print(f"  - id={d.entry_id}: {old}  =>  {new}")


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Répare planned_start/planned_end des dossiers 'attente' sur toutes les machines actives."
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true", help="Affiche les diffs sans écrire en base.")
    g.add_argument("--apply", action="store_true", help="Applique les modifications (UPDATE + commit).")
    args = p.parse_args(argv)

    apply = bool(args.apply)
    mode = "APPLY" if apply else "DRY-RUN"
    print(f"MySifa repair planning planned dates — mode {mode}")
    print("Rappel: faire un backup explicite avant --apply.")

    with get_db() as conn:
        mrows = conn.execute(
            "SELECT id, nom FROM machines WHERE actif=1 ORDER BY nom"
        ).fetchall()
        machines = [dict(r) for r in mrows]

        total_updated = 0
        for m in machines:
            mid = int(m["id"])
            mname = (m.get("nom") or "").strip() or f"machine_{mid}"
            updated, diffs = _compute_waits_diffs_for_machine(conn, mid, apply=apply)
            total_updated += int(updated)
            _print_machine_report(mname, mid, updated, diffs)

        if apply:
            conn.commit()

    print(f"Terminé. Total attente(s) recalée(s): {total_updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

