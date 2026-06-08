"""Tableaux de bord personnalisés sur le portail d'accueil MySifa."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Optional

from config import PORTAL_DASHBOARD_IDS, PORTAL_DASHBOARD_WIDGETS
from services.auth_service import can_view_all_prod, merged_app_access


def portal_dashboards_list_from_db(val) -> List[str]:
    if not val:
        return []
    try:
        arr = json.loads(val) if isinstance(val, str) else val
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(arr, list):
        return []
    out: List[str] = []
    seen: set = set()
    for x in arr:
        if isinstance(x, str):
            wid = x.strip()
            if wid in PORTAL_DASHBOARD_IDS and wid not in seen:
                out.append(wid)
                seen.add(wid)
    return out


def normalize_portal_dashboards_for_db(raw) -> Optional[str]:
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None
    if not isinstance(raw, list):
        return None
    out: List[str] = []
    seen: set = set()
    for x in raw:
        if not isinstance(x, str):
            continue
        wid = x.strip()
        if wid in PORTAL_DASHBOARD_IDS and wid not in seen:
            out.append(wid)
            seen.add(wid)
    if not out:
        return None
    return json.dumps(out, separators=(",", ":"))


def _widget_meta_by_id() -> dict:
    return {w["id"]: w for w in PORTAL_DASHBOARD_WIDGETS}


def catalog_for_user(user: dict) -> List[dict]:
    """Widgets disponibles pour l'utilisateur (selon app_access)."""
    app_access = user.get("app_access") or merged_app_access(
        user.get("role"), user.get("access_overrides")
    )
    out = []
    for w in PORTAL_DASHBOARD_WIDGETS:
        app_key = w.get("app")
        if app_key and not app_access.get(app_key):
            continue
        out.append(
            {
                "id": w["id"],
                "label": w["label"],
                "description": w.get("description") or "",
            }
        )
    return out


def filter_enabled_for_user(user: dict, enabled_ids: List[str]) -> List[str]:
    allowed = {w["id"] for w in catalog_for_user(user)}
    return [wid for wid in enabled_ids if wid in allowed]


def _today_paris_prefix() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _widget_stock_alertes(conn) -> dict:
    rows = conn.execute(
        """
        SELECT mp.reference, mp.designation, mp.categorie,
               COALESCE(s.quantite, 0) AS quantite, mp.seuil_alerte
        FROM matieres_premieres mp
        LEFT JOIN mp_stock s ON s.matiere_id = mp.id
        WHERE mp.actif = 1 AND mp.seuil_alerte > 0
          AND COALESCE(s.quantite, 0) <= mp.seuil_alerte
        ORDER BY mp.categorie, mp.reference
        LIMIT 8
        """
    ).fetchall()
    items = [
        {
            "reference": r["reference"],
            "designation": r["designation"],
            "quantite": float(r["quantite"] or 0),
            "seuil": float(r["seuil_alerte"] or 0),
        }
        for r in rows
    ]
    total = conn.execute(
        """
        SELECT COUNT(*) AS c FROM matieres_premieres mp
        LEFT JOIN mp_stock s ON s.matiere_id = mp.id
        WHERE mp.actif = 1 AND mp.seuil_alerte > 0
          AND COALESCE(s.quantite, 0) <= mp.seuil_alerte
        """
    ).fetchone()
    count = int(total["c"] or 0) if total else len(items)
    return {
        "kpi": str(count),
        "kpi_label": "alerte(s) MP",
        "lines": [
            f"{it['reference']} — {it['quantite']:.0f} / min. {it['seuil']:.0f}"
            for it in items[:4]
        ],
        "empty": count == 0,
        "empty_text": "Toutes les matières sont au-dessus des seuils.",
        "href": "/stock",
    }


def _widget_expe_departs(conn) -> dict:
    pending = conn.execute(
        "SELECT COUNT(*) AS c FROM expe_departs WHERE statut = 'en_attente'"
    ).fetchone()
    count = int(pending["c"] or 0) if pending else 0
    rows = conn.execute(
        """
        SELECT client, date_enlevement, transporteur
        FROM expe_departs
        WHERE statut = 'en_attente'
        ORDER BY date_enlevement ASC, id ASC
        LIMIT 4
        """
    ).fetchall()
    lines = []
    for r in rows:
        dt = (r["date_enlevement"] or "")[:10]
        client = (r["client"] or "—").strip()
        tr = (r["transporteur"] or "").strip()
        line = f"{dt} — {client}"
        if tr:
            line += f" · {tr}"
        lines.append(line)
    return {
        "kpi": str(count),
        "kpi_label": "en attente",
        "lines": lines,
        "empty": count == 0,
        "empty_text": "Aucun départ en attente.",
        "href": "/expe",
    }


def _widget_planning_actif(conn) -> dict:
    attente = conn.execute(
        "SELECT COUNT(*) AS c FROM planning_entries WHERE statut = 'attente'"
    ).fetchone()
    en_cours = conn.execute(
        "SELECT COUNT(*) AS c FROM planning_entries WHERE statut = 'en_cours'"
    ).fetchone()
    n_att = int(attente["c"] or 0) if attente else 0
    n_cours = int(en_cours["c"] or 0) if en_cours else 0
    rows = conn.execute(
        """
        SELECT reference, client, statut, machine_nom
        FROM planning_entries
        WHERE statut IN ('en_cours', 'attente')
        ORDER BY CASE statut WHEN 'en_cours' THEN 0 ELSE 1 END, reference
        LIMIT 4
        """
    ).fetchall()
    statut_lbl = {"attente": "En attente", "en_cours": "En cours"}
    lines = []
    for r in rows:
        ref = r["reference"] or "—"
        st = statut_lbl.get(r["statut"], r["statut"] or "")
        mac = (r["machine_nom"] or "").strip()
        lines.append(f"{ref} — {st}" + (f" · {mac}" if mac else ""))
    return {
        "kpi": str(n_cours),
        "kpi_label": "en cours",
        "kpi_secondary": str(n_att),
        "kpi_secondary_label": "en attente",
        "lines": lines,
        "empty": n_att == 0 and n_cours == 0,
        "empty_text": "Aucun dossier actif au planning.",
        "href": "/planning",
    }


def _widget_prod_jour(conn, user: dict) -> dict:
    today = _today_paris_prefix()

    where = ["date_operation >= ?", "date_operation <= ?"]
    params: list = [today, today + "T23:59:59"]
    if not can_view_all_prod(user):
        op = (user.get("operateur_lie") or user.get("nom") or "").strip()
        if not op:
            return {
                "kpi": "—",
                "kpi_label": "non lié",
                "lines": [],
                "empty": True,
                "empty_text": "Compte non lié à un opérateur.",
                "href": "/prod",
            }
        where.append("operateur = ?")
        params.append(op)

    wc = " AND ".join(where)
    finis = conn.execute(
        f"""
        SELECT COUNT(DISTINCT no_dossier) AS c FROM production_data
        WHERE {wc} AND operation_code = '89' AND COALESCE(no_dossier, '') != ''
        """,
        params,
    ).fetchone()
    n_finis = int(finis["c"] or 0) if finis else 0

    rows = conn.execute(
        f"""
        SELECT no_dossier, client, designation, date_operation
        FROM production_data
        WHERE {wc} AND operation_code = '89'
        ORDER BY date_operation DESC
        LIMIT 4
        """,
        params,
    ).fetchall()
    lines = []
    for r in rows:
        dos = r["no_dossier"] or "—"
        client = (r["client"] or "").strip()
        lines.append(f"{dos}" + (f" — {client}" if client else ""))

    return {
        "kpi": str(n_finis),
        "kpi_label": "dossier(s) terminé(s)",
        "lines": lines,
        "empty": n_finis == 0,
        "empty_text": "Aucune fin de dossier aujourd'hui.",
        "href": "/prod",
    }


def _widget_fabrication_machine(conn, user: dict) -> dict:
    machine_id = user.get("machine_id")
    if not machine_id:
        return {
            "kpi": "—",
            "kpi_label": "sans machine",
            "lines": [],
            "empty": True,
            "empty_text": "Aucune machine liée à votre compte.",
            "href": "/fabrication",
        }
    mac = conn.execute(
        "SELECT nom FROM machines WHERE id = ? LIMIT 1", (machine_id,)
    ).fetchone()
    mac_nom = (mac["nom"] if mac else "") or f"Machine {machine_id}"

    row = conn.execute(
        """
        SELECT reference, client, statut
        FROM planning_entries
        WHERE machine_id = ? AND statut = 'en_cours'
        ORDER BY id DESC
        LIMIT 1
        """,
        (machine_id,),
    ).fetchone()
    if row:
        ref = row["reference"] or "—"
        client = (row["client"] or "").strip()
        return {
            "kpi": ref,
            "kpi_label": "en cours",
            "lines": [mac_nom] + ([client] if client else []),
            "empty": False,
            "href": "/fabrication",
        }
    return {
        "kpi": "—",
        "kpi_label": "libre",
        "lines": [mac_nom],
        "empty": True,
        "empty_text": "Aucun dossier en cours sur votre machine.",
        "href": "/fabrication",
    }


_FETCHERS = {
    "stock_alertes": lambda conn, user: _widget_stock_alertes(conn),
    "expe_departs": lambda conn, user: _widget_expe_departs(conn),
    "planning_actif": lambda conn, user: _widget_planning_actif(conn),
    "prod_jour": lambda conn, user: _widget_prod_jour(conn, user),
    "fabrication_machine": lambda conn, user: _widget_fabrication_machine(conn, user),
}


def widget_data(conn, user: dict, widget_id: str) -> Optional[dict]:
    meta = _widget_meta_by_id().get(widget_id)
    if not meta:
        return None
    catalog_ids = {w["id"] for w in catalog_for_user(user)}
    if widget_id not in catalog_ids:
        return None
    fetcher = _FETCHERS.get(widget_id)
    if not fetcher:
        return None
    try:
        payload = fetcher(conn, user)
    except Exception:
        payload = {
            "kpi": "—",
            "kpi_label": "",
            "lines": [],
            "empty": True,
            "empty_text": "Données indisponibles.",
            "href": "/",
        }
    return {
        "id": widget_id,
        "label": meta["label"],
        "description": meta.get("description") or "",
        **payload,
    }


def widgets_payload(conn, user: dict, enabled_ids: List[str]) -> List[dict]:
    allowed = filter_enabled_for_user(user, enabled_ids)
    out = []
    for wid in allowed:
        data = widget_data(conn, user, wid)
        if data:
            out.append(data)
    return out
