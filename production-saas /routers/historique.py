"""SIFA — Historique v0.7
Sanity Score découplé du filtre dossier.
Multi-select opérateurs et dossiers.
"""
from typing import Optional, List
from fastapi import APIRouter, Request, Query
from database import get_db
from services.analyse import analyse_saisie_errors
from services.auth_service import get_current_user, is_admin

router = APIRouter()

BLOCKED = {
    "blocked": True,
    "message": "Votre compte n'est pas encore lié à un opérateur. Contactez un administrateur.",
    "total_operations": 0, "severity_counts": {}, "category_counts": [],
    "issues": [], "operator_issues": [], "machine_issues": [],
    "saisie_errors": [], "saisie_errors_count": 0,
    "sanity": {"score": 0, "mention": "Non lié", "color": "danger", "penalites": []},
}

def compute_sanity_score(errors, total):
    if total == 0:
        return {"score": 100, "mention": "Excellent", "color": "success", "penalites": []}
    pen_map = {
        "absence_arrivee":        ("Arrivée manquante",   20),
        "absence_depart":         ("Départ manquant",     20),
        "dossier_sans_debut":     ("Début manquant",      10),
        "dossier_sans_fin":       ("Fin manquante",       10),
        "dossier_sans_debut_fin": ("Début+Fin manquants", 15),
    }
    counts = {}
    for e in errors:
        counts[e["type"]] = counts.get(e["type"], 0) + 1
    penalites = []
    total_pen = 0
    for t, n in counts.items():
        if t in pen_map:
            label, pts = pen_map[t]
            total_pen += pts * n
            penalites.append({"type": t, "label": label, "count": n,
                               "pts_unitaire": pts, "total": pts * n})
    score = max(0, min(100, 100 - total_pen))
    if score >= 90:   mention, color = "Excellent",   "success"
    elif score >= 70: mention, color = "Bon",         "warn"
    elif score >= 50: mention, color = "À améliorer", "warn"
    else:             mention, color = "Critique",    "danger"
    return {"score": score, "mention": mention, "color": color, "penalites": penalites}


@router.get("/api/dashboard/historique")
def dashboard_historique(
    request: Request,
    operateur: Optional[List[str]] = Query(default=None),
    no_dossier: Optional[List[str]] = Query(default=None),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    user = get_current_user(request)
    if not is_admin(user) and not user.get("operateur_lie"):
        return {**BLOCKED}

    operateurs = [o for o in (operateur or []) if o]
    dossiers   = [d for d in (no_dossier or []) if d]

    # ── Filtre principal (avec dossiers) ──────────────────────────
    where, params = ["1=1"], []
    if is_admin(user):
        if operateurs:
            where.append(f"operateur IN ({','.join('?'*len(operateurs))})")
            params.extend(operateurs)
        if dossiers:
            where.append(f"no_dossier IN ({','.join('?'*len(dossiers))})")
            params.extend(dossiers)
    else:
        where.append("operateur = ?"); params.append(user["operateur_lie"])
    if date_from: where.append("date_operation >= ?"); params.append(date_from)
    if date_to:   where.append("date_operation <= ?"); params.append(date_to+'T23:59:59')
    wc = " AND ".join(where)

    # ── Filtre Sanity (sans filtre dossier) ───────────────────────
    ws, ps = ["1=1"], []
    if is_admin(user):
        if operateurs:
            ws.append(f"operateur IN ({','.join('?'*len(operateurs))})")
            ps.extend(operateurs)
    else:
        ws.append("operateur = ?"); ps.append(user["operateur_lie"])
    if date_from: ws.append("date_operation >= ?"); ps.append(date_from)
    if date_to:   ws.append("date_operation <= ?"); ps.append(date_to+'T23:59:59')
    wc_san = " AND ".join(ws)

    with get_db() as conn:
        total     = conn.execute(f"SELECT COUNT(*) as c FROM production_data WHERE {wc}", params).fetchone()["c"]
        sev       = conn.execute(f"SELECT operation_severity, COUNT(*) as c FROM production_data WHERE {wc} GROUP BY operation_severity", params).fetchall()
        cat       = conn.execute(f"SELECT operation_category, operation_severity, COUNT(*) as c FROM production_data WHERE {wc} GROUP BY operation_category, operation_severity ORDER BY c DESC", params).fetchall()
        issues    = conn.execute(f"""
            SELECT operateur,date_operation,operation,operation_code,operation_severity,
                   operation_category,machine,no_dossier,client,designation
            FROM production_data WHERE {wc} AND operation_severity IN ('critique','attention')
            ORDER BY date_operation DESC LIMIT 200""", params).fetchall()
        op_issues = conn.execute(f"""
            SELECT operateur,operation_severity,COUNT(*) as c
            FROM production_data WHERE {wc} AND operation_severity IN ('critique','attention')
            GROUP BY operateur,operation_severity ORDER BY c DESC""", params).fetchall()
        m_issues  = conn.execute(f"""
            SELECT machine,operation_severity,COUNT(*) as c
            FROM production_data WHERE {wc} AND operation_severity IN ('critique','attention')
              AND machine IS NOT NULL AND machine != ''
            GROUP BY machine,operation_severity ORDER BY c DESC""", params).fetchall()
        san_rows  = conn.execute(f"""
            SELECT operateur,date_operation,operation_code,machine,no_dossier,
                   quantite_a_traiter,quantite_traitee
            FROM production_data WHERE {wc_san}
            ORDER BY operateur,date_operation""", ps).fetchall()

    saisie_errors = analyse_saisie_errors([dict(r) for r in san_rows])
    sanity        = compute_sanity_score(saisie_errors, len(san_rows))

    return {
        "blocked": False,
        "total_operations":    total,
        "severity_counts":     {r["operation_severity"]: r["c"] for r in sev},
        "category_counts":     [dict(r) for r in cat],
        "issues":              [dict(r) for r in issues],
        "operator_issues":     [dict(r) for r in op_issues],
        "machine_issues":      [dict(r) for r in m_issues],
        "saisie_errors":       saisie_errors,
        "saisie_errors_count": len(saisie_errors),
        "sanity":              sanity,
    }
