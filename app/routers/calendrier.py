"""MySifa — MyCalendrier — agrégation d'événements."""

from __future__ import annotations

import calendar
import json
from datetime import date, datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.routers.planning import (
    _auto_complete_en_cours,
    _compute_timeline_slots,
    _enforce_single_en_cours,
    _fmt_ts,
    _hours_for_date_factory,
    _load_planning_calendar_maps_range,
    _parse_planned_dt as _parse_planned_dt_planning,
)
from config import ROLE_ADMINISTRATION, ROLE_DIRECTION, ROLE_SUPERADMIN
from database import get_db
from services.auth_service import require_calendrier

router = APIRouter(tags=["calendrier"])

CALENDRIER_ADMIN_CALENDARS = frozenset(
    {"conges", "anniversaires", "feries", "paie", "expeditions"}
)
CALENDRIER_BASIC_CALENDARS = frozenset({"conges", "feries"})
CALENDRIER_PERSO_CAL = "perso"

# Codes machines (table machines) — les id numériques ne sont pas fixes en base.
PRODUCTION_MACHINE_CODES: dict[str, str] = {
    "production_1": "C1",
    "production_2": "C2",
    "production_3": "DSI",
    "production_4": "REP",
}

VALID_CALENDARS = frozenset(
    set(PRODUCTION_MACHINE_CODES.keys())
    | {"conges", "anniversaires", "feries", "paie", "expeditions", "perso"}
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
        "perso",
    ]
)


def _allowed_calendars_for_role(role: str) -> frozenset[str]:
    if role in {ROLE_SUPERADMIN, ROLE_DIRECTION}:
        base: frozenset[str] = VALID_CALENDARS
    elif role == ROLE_ADMINISTRATION:
        base = CALENDRIER_ADMIN_CALENDARS
    else:
        base = CALENDRIER_BASIC_CALENDARS
    return base | frozenset({CALENDRIER_PERSO_CAL})


def _filter_calendars_for_role(role: str, requested: set[str]) -> set[str]:
    allowed = _allowed_calendars_for_role(role)
    return {c for c in requested if c in allowed}


class PersoEventCreate(BaseModel):
    titre: str = Field(..., min_length=1, max_length=500)
    date_debut: str
    date_fin: str
    all_day: bool = False
    note: Optional[str] = Field(None, max_length=4000)


def _parse_event_dt(s: str, field: str) -> datetime:
    raw = str(s or "").strip().replace(" ", "T")
    if len(raw) == 10:
        raw = f"{raw}T00:00"
    try:
        return datetime.fromisoformat(raw[:16])
    except ValueError:
        raise HTTPException(
            400,
            detail=f"{field} : format YYYY-MM-DDTHH:MM attendu.",
        )


def _user_id_from_session(user: dict) -> int:
    uid = user.get("id")
    if uid is None:
        raise HTTPException(401, detail="Session invalide.")
    try:
        return int(uid)
    except (TypeError, ValueError):
        raise HTTPException(401, detail="Session invalide.")


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
        entry_id = slot.get("entry_id")
        titre = f"{ref} · {cli}" if cli else ref or f"Dossier #{entry_id}"
        out.append(
            _event(
                eid=f"prod-{cal_key}-{entry_id}",
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


def _compute_day_windows(
    conn,
    prod_machine_ids: list[int],
    d0: date,
    d1: date,
) -> dict[str, dict[str, float]]:
    """Plage horaire d'affichage par jour (union des machines production), alignée planning."""
    if not prod_machine_ids:
        return {}

    unique_ids = list(dict.fromkeys(prod_machine_ids))
    today = date.today()
    weeks_back = max(12, (today - d0).days // 7 + 2)
    weeks_forward = max(12, (d1 - today).days // 7 + 2)

    getters: list[Any] = []
    for mid in unique_ids:
        row = conn.execute("SELECT * FROM machines WHERE id=?", (mid,)).fetchone()
        if not row:
            continue
        m = dict(row)
        configs, off_days, day_worked_map, day_horaires_map = _load_planning_calendar_maps_range(
            conn, mid, weeks_back=weeks_back, weeks_forward=weeks_forward
        )
        getters.append(
            _hours_for_date_factory(m, configs, off_days, day_worked_map, day_horaires_map)
        )

    if not getters:
        return {}

    default_start, default_end = 5.0, 21.0
    windows: dict[str, dict[str, float]] = {}
    cur = d0
    while cur <= d1:
        dkey = cur.isoformat()
        dt = datetime(cur.year, cur.month, cur.day)
        starts: list[float] = []
        ends: list[float] = []
        for get_h in getters:
            win = get_h(dt)
            if win:
                starts.append(float(win[0]))
                ends.append(float(win[1]))
        if starts:
            windows[dkey] = {"h_start": min(starts), "h_end": max(ends)}
        else:
            windows[dkey] = {
                "h_start": default_start,
                "h_end": default_end,
                "off": 1.0,
            }
        cur += timedelta(days=1)
    return windows


def _calendar_request_context(
    request: Request,
    date_debut: str,
    date_fin: str,
    calendriers: str,
) -> tuple[dict, date, date, set[str]]:
    user = require_calendrier(request)
    d0 = _parse_ymd(date_debut)
    d1 = _parse_ymd(date_fin)
    if d1 < d0:
        raise HTTPException(400, detail="date_fin doit être >= date_debut.")
    role = str(user.get("role") or "")
    requested = {c.strip() for c in calendriers.split(",") if c.strip()}
    cals = _filter_calendars_for_role(role, requested)
    unknown = cals - VALID_CALENDARS
    if unknown:
        raise HTTPException(400, detail=f"Calendriers inconnus : {', '.join(sorted(unknown))}")
    return user, d0, d1, cals


def _fetch_calendar_events(
    user: dict,
    d0: date,
    d1: date,
    cals: set[str],
) -> tuple[list[dict], dict[str, dict[str, float]]]:
    out: list[dict] = []
    prod_machine_ids: list[int] = []
    day_windows: dict[str, dict[str, float]] = {}

    with get_db() as conn:
        prod_machines = _resolve_production_machines(conn, cals)
        prod_machine_ids = list(prod_machines.values())
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

        if prod_machine_ids:
            day_windows = _compute_day_windows(conn, prod_machine_ids, d0, d1)

        if CALENDRIER_PERSO_CAL in cals:
            uid = _user_id_from_session(user)
            rows = conn.execute(
                """
                SELECT id, titre, date_debut, date_fin, all_day, note
                FROM cal_events_perso
                WHERE user_id = ?
                  AND date(substr(date_debut, 1, 10)) <= ?
                  AND date(substr(date_fin, 1, 10)) >= ?
                ORDER BY date_debut ASC, id ASC
                """,
                (uid, d1.isoformat(), d0.isoformat()),
            ).fetchall()
            for r in rows:
                debut = str(r["date_debut"] or "").strip()
                fin = str(r["date_fin"] or "").strip() or debut
                all_day = bool(int(r["all_day"] or 0))
                note = (r["note"] or "").strip() or None
                out.append(
                    _event(
                        eid=f"perso-{r['id']}",
                        cal=CALENDRIER_PERSO_CAL,
                        titre=(r["titre"] or "").strip() or "Sans titre",
                        debut=debut,
                        fin=fin,
                        all_day=all_day,
                        meta={"note": note} if note else {},
                    )
                )

    out.sort(key=lambda e: (e["debut"], e["calendrier"], e["id"]))
    return out, day_windows


def _ics_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def _fold_ics_line(line: str, limit: int = 75) -> str:
    if len(line) <= limit:
        return line
    parts = [line[:limit]]
    rest = line[limit:]
    while rest:
        parts.append(" " + rest[: limit - 1])
        rest = rest[limit - 1 :]
    return "\r\n".join(parts)


def _parse_ev_dt_for_ics(raw: str) -> Optional[datetime]:
    s = str(raw or "").strip().replace(" ", "T").split("+")[0]
    if not s:
        return None
    if len(s) == 10:
        s = f"{s}T00:00:00"
    elif "T" in s and len(s) == 16:
        s = f"{s}:00"
    try:
        return datetime.fromisoformat(s[:19])
    except ValueError:
        return None


def _ics_description(ev: dict) -> str:
    meta = ev.get("meta") or {}
    payload = {"calendrier": ev.get("calendrier"), **meta}
    try:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return str(payload)


def _event_to_vevent_lines(ev: dict) -> list[str]:
    eid = str(ev.get("id") or "event")
    titre = _ics_escape(str(ev.get("titre") or "Sans titre"))
    uid = _ics_escape(f"{eid}@mysifa")
    desc = _ics_escape(_ics_description(ev))
    lines = ["BEGIN:VEVENT", f"UID:{uid}", f"SUMMARY:{titre}"]
    if desc:
        lines.append(f"DESCRIPTION:{desc}")
    debut = _parse_ev_dt_for_ics(ev.get("debut") or "")
    fin = _parse_ev_dt_for_ics(ev.get("fin") or "") or debut
    if not debut:
        lines.append("END:VEVENT")
        return lines
    if ev.get("all_day"):
        start_d = debut.date()
        end_d = (fin or debut).date()
        if end_d < start_d:
            end_d = start_d
        end_exclusive = end_d + timedelta(days=1)
        lines.append(f"DTSTART;VALUE=DATE:{start_d.strftime('%Y%m%d')}")
        lines.append(f"DTEND;VALUE=DATE:{end_exclusive.strftime('%Y%m%d')}")
    else:
        if not fin or fin < debut:
            fin = debut
        lines.append(f"DTSTART:{debut.strftime('%Y%m%dT%H%M%S')}")
        lines.append(f"DTEND:{fin.strftime('%Y%m%dT%H%M%S')}")
    lines.append("END:VEVENT")
    return lines


def build_ics_calendar(events: list[dict]) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//MySifa//MyCalendrier//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for ev in events:
        for line in _event_to_vevent_lines(ev):
            lines.append(_fold_ics_line(line))
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


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
    user, d0, d1, cals = _calendar_request_context(
        request, date_debut, date_fin, calendriers
    )
    if not cals:
        return {"events": [], "day_windows": {}}
    events, day_windows = _fetch_calendar_events(user, d0, d1, cals)
    return {"events": events, "day_windows": day_windows}


@router.get("/api/calendrier/export.ics")
def export_ics(
    request: Request,
    date_debut: str = Query(..., description="YYYY-MM-DD"),
    date_fin: str = Query(..., description="YYYY-MM-DD"),
    calendriers: str = Query(
        DEFAULT_CALENDARS,
        description="Liste séparée par des virgules",
    ),
):
    user, d0, d1, cals = _calendar_request_context(
        request, date_debut, date_fin, calendriers
    )
    events: list[dict] = []
    if cals:
        events, _ = _fetch_calendar_events(user, d0, d1, cals)
    body = build_ics_calendar(events)
    return Response(
        content=body.encode("utf-8"),
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="mysifa-calendrier.ics"',
        },
    )


@router.post("/api/calendrier/events/perso")
def create_perso_event(request: Request, body: PersoEventCreate):
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    titre = body.titre.strip()
    if not titre:
        raise HTTPException(400, detail="titre est requis.")
    dt_debut = _parse_event_dt(body.date_debut, "date_debut")
    dt_fin = _parse_event_dt(body.date_fin, "date_fin")
    if dt_fin < dt_debut:
        raise HTTPException(400, detail="date_fin doit être >= date_debut.")
    note = (body.note or "").strip() or None
    all_day = 1 if body.all_day else 0
    debut_s = _fmt_dt(dt_debut)
    fin_s = _fmt_dt(dt_fin)
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO cal_events_perso (user_id, titre, date_debut, date_fin, all_day, note)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (uid, titre, debut_s, fin_s, all_day, note),
        )
        conn.commit()
        new_id = int(cur.lastrowid)
    return {
        "id": f"perso-{new_id}",
        "calendrier": CALENDRIER_PERSO_CAL,
        "titre": titre,
        "debut": debut_s,
        "fin": fin_s,
        "all_day": bool(all_day),
        "meta": {"note": note} if note else {},
    }


@router.delete("/api/calendrier/events/perso/{event_id}")
def delete_perso_event(request: Request, event_id: int):
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM cal_events_perso WHERE id = ? AND user_id = ?",
            (event_id, uid),
        ).fetchone()
        if not row:
            raise HTTPException(404, detail="Événement introuvable.")
        conn.execute("DELETE FROM cal_events_perso WHERE id = ?", (event_id,))
        conn.commit()
    return {"ok": True}
