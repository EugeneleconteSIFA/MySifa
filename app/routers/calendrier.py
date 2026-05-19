"""MySifa — MyCalendrier — agrégation d'événements (superadmin)."""

from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from database import get_db
from services.auth_service import require_superadmin

router = APIRouter(tags=["calendrier"])

VALID_CALENDARS = frozenset(
    {"production", "conges", "anniversaires", "feries", "paie"}
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


@router.get("/api/calendrier/events")
def list_events(
    request: Request,
    date_debut: str = Query(..., description="YYYY-MM-DD"),
    date_fin: str = Query(..., description="YYYY-MM-DD"),
    calendriers: str = Query(
        "production,conges,anniversaires,feries,paie",
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
        if "production" in cals:
            rows = conn.execute(
                """
                SELECT id, reference, client, machine_id, statut,
                       planned_start, planned_end
                FROM planning_entries
                WHERE planned_start IS NOT NULL
                  AND date(planned_start) <= ?
                  AND date(COALESCE(planned_end, planned_start)) >= ?
                """,
                (d1.isoformat(), d0.isoformat()),
            ).fetchall()
            for r in rows:
                ps = _parse_planned_dt(r["planned_start"])
                pe = _parse_planned_dt(r["planned_end"]) or ps
                if not ps:
                    continue
                if not pe:
                    pe = ps
                ref = (r["reference"] or "").strip()
                cli = (r["client"] or "").strip()
                titre = f"{ref} · {cli}" if cli else ref or f"Dossier #{r['id']}"
                out.append(
                    _event(
                        eid=f"prod-{r['id']}",
                        cal="production",
                        titre=titre,
                        debut=_fmt_dt(ps),
                        fin=_fmt_dt(pe),
                        all_day=False,
                        meta={
                            "statut": r["statut"],
                            "machine_id": r["machine_id"],
                            "reference": ref,
                        },
                    )
                )

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
