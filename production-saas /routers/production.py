"""SIFA — Production v0.7 — multi-select opérateurs/dossiers"""
from typing import Optional, List
from fastapi import APIRouter, Request, Query
from database import get_db
from services.timings import compute_dossier_times
from services.auth_service import get_current_user, is_admin

router = APIRouter()

@router.get("/api/dashboard/production")
def dashboard_production(
    request: Request,
    operateur: Optional[List[str]] = Query(default=None),
    no_dossier: Optional[List[str]] = Query(default=None),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    user = get_current_user(request)
    if not is_admin(user) and not user.get("operateur_lie"):
        return {"blocked": True, "message": "Compte non lié à un opérateur.",
                "completed_dossiers":[],"total_prevue":0,"total_realisee":0,
                "dossier_count":0,"by_machine":[],"by_operator":[],"temps_totaux":{},"dossier_times":[]}

    operateurs = [o for o in (operateur or []) if o]
    dossiers   = [d for d in (no_dossier or []) if d]

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

    with get_db() as conn:
        completed   = conn.execute(f"SELECT no_dossier,operateur,machine,client,designation,quantite_a_traiter,quantite_traitee,date_operation FROM production_data WHERE {wc} AND operation_code='89' ORDER BY date_operation DESC", params).fetchall()
        totals      = conn.execute(f"SELECT COALESCE(SUM(quantite_a_traiter),0) as total_prevue,COALESCE(SUM(quantite_traitee),0) as total_realisee FROM production_data WHERE {wc} AND operation_code='89'", params).fetchone()
        dc          = conn.execute(f"SELECT COUNT(DISTINCT no_dossier) as c FROM production_data WHERE {wc} AND no_dossier IS NOT NULL AND no_dossier!='0'", params).fetchone()["c"]
        by_machine  = conn.execute(f"SELECT machine,COUNT(DISTINCT no_dossier) as dossiers,SUM(CASE WHEN operation_code='89' THEN quantite_traitee ELSE 0 END) as total_prod FROM production_data WHERE {wc} AND machine IS NOT NULL AND machine!='' GROUP BY machine ORDER BY total_prod DESC", params).fetchall()
        by_operator = conn.execute(f"SELECT operateur,COUNT(DISTINCT no_dossier) as dossiers,SUM(CASE WHEN operation_code='89' THEN quantite_traitee ELSE 0 END) as total_prod FROM production_data WHERE {wc} AND operateur IS NOT NULL GROUP BY operateur ORDER BY total_prod DESC", params).fetchall()
        all_rows    = conn.execute(f"SELECT operateur,date_operation,operation_code,machine,no_dossier,client,designation,quantite_a_traiter,quantite_traitee FROM production_data WHERE {wc} ORDER BY operateur,date_operation", params).fetchall()

    dossier_times = compute_dossier_times([dict(r) for r in all_rows])
    total_calage  = sum(d["temps_calage_min"]       for d in dossier_times)
    total_prod    = sum(d["temps_prod_min"]         for d in dossier_times)
    total_hors    = sum(d["temps_total_min"]        for d in dossier_times if d["temps_total_min"])
    total_avec    = sum(d["temps_total_calage_min"] for d in dossier_times if d["temps_total_calage_min"])

    return {
        "blocked": False,
        "completed_dossiers": [dict(r) for r in completed],
        "total_prevue":   totals["total_prevue"],
        "total_realisee": totals["total_realisee"],
        "dossier_count":  dc,
        "by_machine":     [dict(r) for r in by_machine],
        "by_operator":    [dict(r) for r in by_operator],
        "temps_totaux": {
            "calage_min":      round(total_calage, 1),
            "production_min":  round(total_prod,   1),
            "hors_calage_min": round(total_hors,   1),
            "avec_calage_min": round(total_avec,   1),
        },
        "dossier_times": sorted([d for d in dossier_times if d["temps_total_calage_min"]],
                                 key=lambda x: x["temps_total_calage_min"], reverse=True),
    }
