"""MySifa — Rapport hebdomadaire (endpoints API + envoi email + archive)."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request

from config import (
    BASE_DIR,
    APP_VERSION,
    public_base_url,
    ROLE_ADMINISTRATION,
    ROLE_COMMERCIAL,
    ROLE_COMPTABILITE,
    ROLE_DIRECTION,
    ROLE_EXPEDITION,
    ROLE_FABRICATION,
    ROLE_LOGISTIQUE,
    ROLE_SUPERADMIN,
)
from database import get_db
from services.auth_service import (
    effective_role,
    get_current_user,
    is_superadmin,
)
from app.services.email_service import send_email
from app.services.weekly_report import (
    ROLE_SECTIONS,
    collect_week_data,
    previous_iso_week,
    render_report_html,
)

router = APIRouter()

# V1 : accès restreint au super administrateur uniquement (phase de test).
_SEND_ROLES = {ROLE_SUPERADMIN}
_VIEW_ANY_ROLES = {ROLE_SUPERADMIN}

ARCHIVE_DIR = Path(BASE_DIR) / "data" / "weekly_reports"


def _ensure_archive_dir() -> None:
    try:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


def _default_week() -> Dict[str, int]:
    y, w = previous_iso_week()
    return {"year": y, "week": w}


@router.get("/api/reports/weekly/preview")
def preview_weekly_report(request: Request, year: int | None = None,
                          week: int | None = None, role: str | None = None):
    """Preview du rapport pour un rôle donné (fragment HTML + data)."""
    user = get_current_user(request)
    if not is_superadmin(user):
        raise HTTPException(status_code=403, detail="Accès réservé au super administrateur (phase de test).")
    eff = effective_role(user)
    if year is None or week is None:
        d = _default_week()
        year = year or d["year"]
        week = week or d["week"]
    target_role = (role or eff or ROLE_DIRECTION).strip()
    if target_role != eff and eff not in _VIEW_ANY_ROLES:
        raise HTTPException(status_code=403, detail="Accès réservé à la direction pour changer de rôle")
    if target_role not in ROLE_SECTIONS:
        raise HTTPException(status_code=400, detail=f"Rôle inconnu : {target_role}")

    data = collect_week_data(int(year), int(week))
    html = render_report_html(data, target_role, include_email_wrapper=False)
    return {"html": html, "data": data, "role": target_role}


def _target_recipients() -> List[Dict[str, Any]]:
    """Liste des users actifs avec email + rôle."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, email, nom, role FROM users
                WHERE actif=1 AND email IS NOT NULL AND TRIM(email) != ''"""
        ).fetchall()
    out = []
    for r in rows:
        role = (r["role"] or "").strip()
        if role not in ROLE_SECTIONS:
            continue
        out.append({
            "id": r["id"], "email": r["email"], "nom": r["nom"], "role": role,
        })
    return out


def _archive_report(year: int, week: int, role: str, html: str) -> None:
    _ensure_archive_dir()
    fname = ARCHIVE_DIR / f"{year}-{week:02d}-{role}.html"
    try:
        fname.write_text(html, encoding="utf-8")
    except OSError:
        pass


def _publish_announcement(year: int, week: int, data: Dict[str, Any]) -> int | None:
    """Publie une annonce in-app scope=weekly-report. Retourne l'ID ou None."""
    s = data.get("summary", {})
    heures = int(s.get("heures_prod", {}).get("cur", 0))
    doss = int(s.get("dossiers_termines", {}).get("cur", 0))
    expes = int(s.get("expes", {}).get("cur", 0))
    label = data.get("week", {}).get("label", "")
    link = f"/reports/weekly?year={year}&week={week}"
    message = (
        f'<div style="font-size:13px;line-height:1.7;color:var(--text2)">'
        f'<div style="font-size:15px;font-weight:700;color:var(--text);margin-bottom:12px">'
        f'Rapport hebdomadaire — {label}</div>'
        f'<ul style="margin:0 0 14px 0;padding-left:18px">'
        f'<li style="margin-bottom:5px"><b>{heures} h</b> de production</li>'
        f'<li style="margin-bottom:5px"><b>{doss}</b> dossiers terminés</li>'
        f'<li style="margin-bottom:5px"><b>{expes}</b> expéditions envoyées</li>'
        f'</ul>'
        f'<div style="margin-top:14px"><a href="{link}" '
        f'style="color:var(--accent);text-decoration:none;font-weight:600">Ouvrir le rapport complet →</a></div>'
        f'</div>'
    )
    titre = f"Rapport hebdo — {label}"
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO update_announcements (scope,titre,message,created_at,created_by,active)
               VALUES (?,?,?,?,?,?)""",
            ("weekly-report", titre, message, datetime.now().isoformat(), "système", 1),
        )
        conn.commit()
        return cur.lastrowid


@router.post("/api/reports/weekly/send")
async def send_weekly_report(request: Request):
    """Envoie le rapport hebdomadaire par email à tous les users actifs."""
    user = get_current_user(request)
    if effective_role(user) not in _SEND_ROLES:
        raise HTTPException(status_code=403, detail="Accès réservé à la direction / super admin")
    body = await request.json()
    year = int(body.get("year") or _default_week()["year"])
    week = int(body.get("week") or _default_week()["week"])
    dry_run = bool(body.get("dry_run", False))

    recipients = _target_recipients()

    if dry_run:
        return {"dry_run": True, "recipients": recipients, "count": len(recipients)}

    data = collect_week_data(year, week)
    label = data.get("week", {}).get("label", "")
    subject = f"MySifa — Rapport hebdomadaire — {label}"

    # Cache HTML par rôle (pour ne pas re-render N fois)
    html_cache: Dict[str, str] = {}
    for role in ROLE_SECTIONS.keys():
        html_cache[role] = render_report_html(data, role, include_email_wrapper=True)
        _archive_report(year, week, role, html_cache[role])

    sent = []
    for r in recipients:
        role = r["role"]
        html = html_cache.get(role, "")
        try:
            ok = send_email(r["email"], subject, html)
        except Exception:
            ok = False
        sent.append({"email": r["email"], "role": role, "ok": bool(ok)})

    ann_id = _publish_announcement(year, week, data)

    return {
        "sent": sent,
        "count_sent": sum(1 for s in sent if s["ok"]),
        "count_failed": sum(1 for s in sent if not s["ok"]),
        "announcement_id": ann_id,
        "year": year, "week": week,
    }


@router.get("/api/reports/weekly/list")
def list_weekly_reports(request: Request):
    """Liste des rapports archivés (fichiers HTML dans data/weekly_reports/)."""
    get_current_user(request)
    _ensure_archive_dir()
    out = []
    seen: set = set()
    try:
        files = sorted(ARCHIVE_DIR.glob("*.html"))
    except OSError:
        files = []
    for f in files:
        name = f.stem  # "YYYY-WW-role"
        parts = name.split("-", 2)
        if len(parts) < 3:
            continue
        try:
            y = int(parts[0])
            w = int(parts[1])
        except ValueError:
            continue
        key = (y, w)
        if key in seen:
            continue
        seen.add(key)
        try:
            stat = f.stat()
            gen = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
        except OSError:
            gen = ""
        out.append({"year": y, "week": w, "generated_at": gen})
    out.sort(key=lambda x: (x["year"], x["week"]), reverse=True)
    return out
