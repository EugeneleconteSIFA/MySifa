"""MySifa — MyCalendrier — agrégation d'événements (superadmin)."""

from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.routers.planning import (
    _auto_complete_en_cours,
    _compute_timeline_slots,
    _enforce_single_en_cours,
    _fmt_ts,
    _load_planning_calendar_maps_range,
    _parse_planned_dt as _parse_planned_dt_planning,
)
from database import get_db
from services.auth_service import require_superadmin

router = APIRouter(tags=["calendrier"])

# Codes machines (table machines) — les id numériques ne sont pas fixes en base.
PRODUCTION_MACHINE_CODES: dict[str, str] = {
    "production_1": "C1",
    "production_2": "C2",
    "production_3": "DSI",
    "production_4": "REP",
}

VALID_CALENDARS = frozenset(
    set(PRODUCTION_MACHINE_CODES.keys())
    | {"conges", "anniversaires", "feries", "paie", "expeditions"}
)

DEFAULT_CALENDARS = ",".join(
    [
        "production_1",
        "production_2",
        "production_3",
        "production_4",
        "conges",
        "anniversaires",
        "feries",
        "paie",
        "expeditions",
    ]
)

def _parse_ymd(s: str) -> date:
    try:
        return datetime.strptime(s.strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, detail="date_debut / date_fin : format YYYY-MM-DD attendu.")


def _parse_planned_dt(val: Any) -> Optional[datetime]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    s = s.replace("Z", "").split("+")[0].strip()
    if len(s) == 10:
        s = f"{s}T00:00:00"
    elif "T" not in s and len(s) >= 16:
        s = s.replace(" ", "T", 1)
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        try:
            return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


def _fmt_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M")


def _event(
    *,
    eid: str,
    cal: str,
    titre: str,
    debut: str,
    fin: str,
    all_day: bool,
    meta: Optional[dict] = None,
) -> dict:
    return {
        "id": eid,
        "calendrier": cal,
        "titre": titre,
        "debut": debut,
        "fin": fin,
        "all_day": all_day,
        "meta": meta or {},
    }


def _ranges_overlap(d0: date, d1: date, start: date, end: date) -> bool:
    return start <= d1 and end >= d0


def _resolve_production_machines(
    conn, cals: set[str]
) -> dict[str, int]:
    """cal_key → machine_id réel (via code C1, C2, DSI, REP)."""
    wanted = {
        cal_key: code
        for cal_key, code in PRODUCTION_MACHINE_CODES.items()
        if cal_key in cals
    }
    if not wanted:
        return {}
    codes = list(wanted.values())
    placeholders = ",".join("?" * len(codes))
    rows = conn.execute(
        f"SELECT id, code FROM machines WHERE code IN ({placeholders})",
        codes,
    ).fetchall()
    code_to_id = {str(r["code"]): int(r["id"]) for r in rows}
    out: dict[str, int] = {}
    for cal_key, code in wanted.items():
        mid = code_to_id.get(code)
        if mid is not None:
            out[cal_key] = mid
    return out


def _slot_in_range(start_iso: str, end_iso: str, d0: date, d1: date) -> bool:
    ps = _parse_planned_dt_planning(start_iso)
    pe = _parse_planned_dt_planning(end_iso) or ps
    if not ps:
        return False
    return ps.date() <= d1 and pe.date() >= d0


def _production_events_for_machine(
    conn,
    machine_id: int,
    cal_key: str,
    d0: date,
    d1: date,
) -> list[dict]:
    """Créneaux alignés sur GET /machines/{id}/timeline (horaires ouvrés, recalcul attente)."""
    machine = conn.execute("SELECT * FROM machines WHERE id=?", (machine_id,)).fetchone()
    if not machine:
        return []
    m = dict(machine)

    today = date.today()
    weeks_back = max(12, (today - d0).days // 7 + 2)
    weeks_forward = max(12, (d1 - today).days // 7 + 2)
    configs, off_days, day_worked_map, day_horaires_map = _load_planning_calendar_maps_range(
        conn, machine_id, weeks_back=weeks_back, weeks_forward=weeks_forward
    )

    _auto_complete_en_cours(conn, machine_id)
    _enforce_single_en_cours(conn, machine_id)

    rows = conn.execute(
        """
        SELECT * FROM planning_entries
        WHERE machine_id = ?
        ORDER BY position ASC
        """,
        (machine_id,),
    ).fetchall()
    entries_list = [dict(r) for r in rows]
    main_entries: list[dict] = []
    aplacer_entries: list[dict] = []
    for e in entries_list:
        st = (e.get("statut") or "attente").strip()
        ap = int(e.get("a_placer") or 0)
        if st == "attente" and ap == 1:
            aplacer_entries.append(e)
        else:
            main_entries.append(e)
    entries_list = main_entries + aplacer_entries

    slots = _compute_timeline_slots(
        conn,
        machine_id,
        m,
        configs,
        off_days,
        day_worked_map,
        day_horaires_map,
        entries_list,
    )

    out: list[dict] = []
    for slot in slots:
        ps_iso = slot.get("start") or ""
        pe_iso = slot.get("end") or ""
        if not _slot_in_range(ps_iso, pe_iso, d0, d1):
            continue
        ref = (slot.get("reference") or slot.get("numero_of") or "").strip()
        cli = (slot.get("client") or "").strip()
        titre = f"{ref} · {cli}" if cli else ref or f"Dossier #{slot.get('id')}"
        out.append(
            _event(
                eid=f"prod-{slot.get('id')}",
                cal=cal_key,
                titre=titre,
                debut=_fmt_ts(_parse_planned_dt_planning(ps_iso) or datetime.now()),
                fin=_fmt_ts(
                    _parse_planned_dt_planning(pe_iso)
                    or _parse_planned_dt_planning(ps_iso)
                    or datetime.now()
                ),
                all_day=False,
                meta={
                    "statut": slot.get("statut"),
                    "machine_id": machine_id,
                    "machine_code": m.get("code"),
                    "reference": ref,
                },
            )
        )
    return out


@router.get("/api/calendrier/events")
def list_events(
    request: Request,
    date_debut: str = Query(..., description="YYYY-MM-DD"),
    date_fin: str = Query(..., description="YYYY-MM-DD"),
    calendriers: str = Query(
        DEFAULT_CALENDARS,
        description="Liste séparée par des virgules",
    ),
):
    require_superadmin(request)
    d0 = _parse_ymd(date_debut)
    d1 = _parse_ymd(date_fin)
    if d1 < d0:
        raise HTTPException(400, detail="date_fin doit être >= date_debut.")

    cals = {c.strip() for c in calendriers.split(",") if c.strip()}
    unknown = cals - VALID_CALENDARS
    if unknown:
        raise HTTPException(400, detail=f"Calendriers inconnus : {', '.join(sorted(unknown))}")
    if not cals:
        return []

    out: list[dict] = []

    with get_db() as conn:
        prod_machines = _resolve_production_machines(conn, cals)
        for cal_key, machine_id in prod_machines.items():
            out.extend(
                _production_events_for_machine(conn, machine_id, cal_key, d0, d1)
            )
        conn.commit()

        if "conges" in cals:
            rows = conn.execute(
                """
                SELECT c.id, c.date_debut, c.date_fin, c.type_conge, c.statut, u.nom
                FROM rh_conges c
                JOIN users u ON u.id = c.user_id
                WHERE c.statut IN ('pose', 'valide')
                  AND date(c.date_debut) <= ?
                  AND date(c.date_fin) >= ?
                """,
                (d1.isoformat(), d0.isoformat()),
            ).fetchall()
            for r in rows:
                nom = (r["nom"] or "").strip() or "Utilisateur"
                tc = (r["type_conge"] or "CP").strip()
                try:
                    db = datetime.strptime(str(r["date_debut"])[:10], "%Y-%m-%d").date()
                    de = datetime.strptime(str(r["date_fin"])[:10], "%Y-%m-%d").date()
                except ValueError:
                    continue
                out.append(
                    _event(
                        eid=f"conge-{r['id']}",
                        cal="conges",
                        titre=f"{nom} · {tc}",
                        debut=f"{db.isoformat()}T00:00",
                        fin=f"{de.isoformat()}T23:59",
                        all_day=True,
                        meta={"statut": r["statut"], "type_conge": tc},
                    )
                )

        if "anniversaires" in cals:
            rows = conn.execute(
                """
                SELECT id, nom, date_naissance
                FROM users
                WHERE actif = 1 AND date_naissance IS NOT NULL AND trim(date_naissance) != ''
                """
            ).fetchall()
            for r in rows:
                raw = str(r["date_naissance"] or "").strip()[:10]
                try:
                    born = datetime.strptime(raw, "%Y-%m-%d").date()
                except ValueError:
                    continue
                nom = (r["nom"] or "").strip() or "Utilisateur"
                for year in range(d0.year, d1.year + 1):
                    try:
                        bday = date(year, born.month, born.day)
                    except ValueError:
                        if born.month == 2 and born.day == 29:
                            bday = date(year, 2, 28)
                        else:
                            continue
                    if d0 <= bday <= d1:
                        out.append(
                            _event(
                                eid=f"anniv-{r['id']}-{year}",
                                cal="anniversaires",
                                titre=nom,
                                debut=f"{bday.isoformat()}T00:00",
                                fin=f"{bday.isoformat()}T23:59",
                                all_day=True,
                                meta={"user_id": r["id"], "annee": year},
                            )
                        )

        if "feries" in cals:
            rows = conn.execute(
                """
                SELECT date, label
                FROM planning_holidays
                WHERE date >= ? AND date <= ?
                GROUP BY date, label
                ORDER BY date, label
                """,
                (d0.isoformat(), d1.isoformat()),
            ).fetchall()
            for r in rows:
                ds = str(r["date"] or "")[:10]
                try:
                    hd = datetime.strptime(ds, "%Y-%m-%d").date()
                except ValueError:
                    continue
                label = (r["label"] or "").strip() or "Jour férié"
                out.append(
                    _event(
                        eid=f"ferie-{ds}-{label}",
                        cal="feries",
                        titre=label,
                        debut=f"{hd.isoformat()}T00:00",
                        fin=f"{hd.isoformat()}T23:59",
                        all_day=True,
                        meta={},
                    )
                )

        if "expeditions" in cals:
            rows = conn.execute(
                """
                SELECT id, date_enlevement, date_livraison, client, transporteur,
                       ref_sifa, code_postal_destination, statut, nb_palette, poids_total_kg
                FROM expe_departs
                WHERE statut IN ('en_attente', 'valide')
                  AND date(date_enlevement) <= ?
                  AND date(COALESCE(NULLIF(trim(date_livraison), ''), date_enlevement)) >= ?
                ORDER BY date_enlevement ASC, id ASC
                """,
                (d1.isoformat(), d0.isoformat()),
            ).fetchall()
            for r in rows:
                try:
                    d_enl = datetime.strptime(
                        str(r["date_enlevement"] or "")[:10], "%Y-%m-%d"
                    ).date()
                except ValueError:
                    continue
                d_liv = d_enl
                raw_liv = str(r["date_livraison"] or "").strip()[:10]
                if raw_liv:
                    try:
                        d_liv = datetime.strptime(raw_liv, "%Y-%m-%d").date()
                    except ValueError:
                        d_liv = d_enl
                if d_liv < d_enl:
                    d_liv = d_enl
                if not _ranges_overlap(d0, d1, d_enl, d_liv):
                    continue
                client = (r["client"] or "").strip()
                transp = (r["transporteur"] or "").strip()
                ref = (r["ref_sifa"] or "").strip()
                cp = (r["code_postal_destination"] or "").strip()
                parts = [p for p in (client, transp) if p]
                if not parts and ref:
                    parts = [ref]
                titre = " · ".join(parts) if parts else f"Départ #{r['id']}"
                if cp and cp not in titre:
                    titre = f"{titre} ({cp})"
                out.append(
                    _event(
                        eid=f"expe-{r['id']}",
                        cal="expeditions",
                        titre=titre,
                        debut=f"{d_enl.isoformat()}T00:00",
                        fin=f"{d_liv.isoformat()}T23:59",
                        all_day=True,
                        meta={
                            "statut": r["statut"],
                            "ref_sifa": ref,
                            "date_enlevement": d_enl.isoformat(),
                            "date_livraison": d_liv.isoformat(),
                        },
                    )
                )

        if "paie" in cals:
            rows = conn.execute(
                """
                SELECT DISTINCT annee, mois
                FROM paie_variables
                ORDER BY annee, mois
                """
            ).fetchall()
            seen: set[tuple[int, int]] = set()
            for r in rows:
                annee = int(r["annee"])
                mois = int(r["mois"])
                if mois < 1 or mois > 12:
                    continue
                key = (annee, mois)
                if key in seen:
                    continue
                last_day = calendar.monthrange(annee, mois)[1]
                start = date(annee, mois, 1)
                end = date(annee, mois, last_day)
                if not _ranges_overlap(d0, d1, start, end):
                    continue
                seen.add(key)
                out.append(
                    _event(
                        eid=f"paie-{annee}-{mois}",
                        cal="paie",
                        titre=f"Paie · {mois}/{annee}",
                        debut=f"{end.isoformat()}T00:00",
                        fin=f"{end.isoformat()}T23:59",
                        all_day=True,
                        meta={"annee": annee, "mois": mois},
                    )
                )

    out.sort(key=lambda e: (e["debut"], e["calendrier"], e["id"]))
    return out
