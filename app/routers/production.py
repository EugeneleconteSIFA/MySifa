"""SIFA — Production v0.9 — métrage produit = fin_machine - debut_machine"""
from typing import Optional, List
from fastapi import APIRouter, Request, Query
from datetime import datetime as _dt_cls
from database import get_db
from services.timings import compute_dossier_times
from services.auth_service import get_current_user, is_admin, can_view_all_prod

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
    if not can_view_all_prod(user) and not user.get("operateur_lie"):
        return {"blocked": True, "message": "Compte non lié à un opérateur.",
                "completed_dossiers": [],
                "produit": {"dossiers": 0, "etiquettes": 0, "metrage_m": 0},
                "temps_totaux": {},
                "vitesse_m_min": 0,
                "by_machine": [],
                "by_operator": [],
                "by_dossier": [],
                "by_day": []}

    operateurs = [o for o in (operateur or []) if o]
    dossiers   = [d for d in (no_dossier or []) if d]

    where, params = ["1=1"], []
    if can_view_all_prod(user):
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
        completed = conn.execute(
            f"""SELECT no_dossier,operateur,machine,client,designation,
                       quantite_traitee,metrage_reel,metrage_prevu,date_operation
                FROM production_data
                WHERE {wc} AND operation_code='89'
                ORDER BY date_operation DESC""",
            params,
        ).fetchall()

        # Toutes les lignes pour calculs temps + métrages
        all_rows = conn.execute(
            f"""SELECT operateur,date_operation,operation_code,operation_category,
                       machine,no_dossier,client,designation,
                       quantite_traitee,metrage_reel,metrage_prevu
                FROM production_data
                WHERE {wc}
                ORDER BY operateur,date_operation""",
            params,
        ).fetchall()

    all_list = [dict(r) for r in all_rows]
    dossier_times = compute_dossier_times(all_list)

    # ── Helper : normalise n'importe quel format de date → 'YYYY-MM-DD' ────────
    _FMTS = (
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
        "%Y-%m-%d", "%d/%m/%Y",
    )
    def _norm_date(dt_raw: str) -> str:
        s = str(dt_raw or "").strip()
        for fmt in _FMTS:
            try:
                return _dt_cls.strptime(s, fmt).date().isoformat()
            except ValueError:
                continue
        return s[:10]   # dernier recours

    # ── Map des fins : somme de tous les metrage_reel (code-89) par jour ────────
    # Chaque entrée fin contient directement les mètres produits lors de la session.
    # On additionne toutes les fins du même (opérateur, jour, dossier).
    fin_data = {}   # (op, jour_iso, dos) -> {"metrage_m": float, "etiquettes": float}

    for r in all_list:
        code = str(r.get("operation_code") or "")
        dos  = str(r.get("no_dossier") or "").strip()
        if not dos or dos == "0":
            continue
        op    = str(r.get("operateur") or "?")
        dt_op = str(r.get("date_operation") or "")

        if code == "89":
            jour_iso = _norm_date(dt_op)
            key      = (op, jour_iso, dos)
            entry    = fin_data.setdefault(key, {"metrage_m": 0.0, "etiquettes": 0.0})
            if r.get("metrage_reel") is not None:
                entry["metrage_m"] += float(r["metrage_reel"])
            if r.get("quantite_traitee") is not None:
                entry["etiquettes"] = float(r["quantite_traitee"])  # dernière valeur du jour

    # ── Enrichir by_dossier avec le métrage produit calculé ─────────────────
    by_dossier = []
    for d in dossier_times:
        op  = str(d.get("operateur") or "?")
        dos = str(d.get("no_dossier") or "")
        dt  = str(d.get("jour") or "")

        entry = fin_data.get((op, dt, dos), {})

        d["etiquettes"] = entry.get("etiquettes") or d.get("quantite_traitee") or 0
        d["metrage_m"]  = round(entry.get("metrage_m", 0.0), 1)
        by_dossier.append(d)

    # ── Enrichir completed_dossiers avec le métrage produit ─────────────────
    completed_list = []
    for r in completed:
        row = dict(r)
        row["metrage_produit"] = float(row.get("metrage_reel") or 0)
        completed_list.append(row)

    # ── Totaux (recalculés depuis by_dossier pour cohérence) ─────────────────
    total_calage  = sum(float(d.get("temps_calage_min") or 0) for d in by_dossier)
    total_prod    = sum(float(d.get("temps_prod_min")   or 0) for d in by_dossier)
    total_arret   = sum(float(d.get("temps_arret_min")  or 0) for d in by_dossier)

    metrage_total     = round(sum(float(d.get("metrage_m") or 0) for d in by_dossier), 1)
    etiquettes_total  = round(sum(float(d.get("etiquettes") or 0) for d in by_dossier), 1)
    nb_dossiers_total = len([d for d in by_dossier if d.get("no_dossier")])

    denom = float(total_prod + total_arret)
    vitesse_m_min = round(metrage_total / denom, 3) if denom > 0 else 0.0

    # ── Agrégations ──────────────────────────────────────────────────────────
    def agg_key(rows, key_name):
        out = {}
        for r in rows:
            k = str(r.get(key_name) or "").strip() or "?"
            x = out.setdefault(k, {"key": k, "dossiers": 0, "etiquettes": 0.0, "metrage_m": 0.0,
                                   "calage_min": 0.0, "prod_min": 0.0, "arret_min": 0.0})
            x["dossiers"]   += 1
            x["etiquettes"] += float(r.get("etiquettes") or 0)
            x["metrage_m"]  += float(r.get("metrage_m")  or 0)
            x["calage_min"] += float(r.get("temps_calage_min") or 0)
            x["prod_min"]   += float(r.get("temps_prod_min")   or 0)
            x["arret_min"]  += float(r.get("temps_arret_min")  or 0)
        res = []
        for k, v in out.items():
            den = v["prod_min"] + v["arret_min"]
            v["vitesse_m_min"] = round((v["metrage_m"] / den), 3) if den > 0 else 0.0
            v["etiquettes"] = round(v["etiquettes"], 1)
            v["metrage_m"]  = round(v["metrage_m"],  1)
            v["calage_min"] = round(v["calage_min"],  1)
            v["prod_min"]   = round(v["prod_min"],    1)
            v["arret_min"]  = round(v["arret_min"],   1)
            res.append(v)
        return sorted(res, key=lambda x: x["metrage_m"], reverse=True)

    by_operator = agg_key(by_dossier, "operateur")
    by_machine  = agg_key(by_dossier, "machine")
    by_day      = agg_key(by_dossier, "jour")

    return {
        "blocked": False,
        "completed_dossiers": completed_list,
        "produit": {
            "dossiers":   nb_dossiers_total,
            "etiquettes": etiquettes_total,
            "metrage_m":  metrage_total,
        },
        "temps_totaux": {
            "calage_min":      round(total_calage, 1),
            "production_min":  round(total_prod,   1),
            "arret_min":       round(total_arret,  1),
        },
        "vitesse_m_min": vitesse_m_min,
        "by_machine":  by_machine,
        "by_operator": by_operator,
        "by_dossier":  sorted([d for d in by_dossier if d.get("no_dossier")],
                               key=lambda x: x.get("temps_total_calage_min") or 0, reverse=True),
        "by_day": by_day,
    }
