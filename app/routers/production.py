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
    # Pour fabrication: utiliser nom si operateur_lie n'est pas défini
    user_operateur = user.get("operateur_lie") or user.get("nom") or ""
    if not can_view_all_prod(user) and not user_operateur:
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
        # Pour fabrication: filtrer par operateur_lie ou nom utilisateur
        where.append("operateur = ?"); params.append(user_operateur)
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
                       machine,no_dossier,client,designation,quantite_traitee,
                       COALESCE(metrage_total_debut, metrage_prevu) AS metrage_prevu,
                       COALESCE(metrage_total_fin,   metrage_reel)  AS metrage_reel
                FROM production_data
                WHERE {wc}
                ORDER BY operateur,date_operation""",
            params,
        ).fetchall()

    all_list = [dict(r) for r in all_rows]
    dossier_times = compute_dossier_times(all_list)

    # ── Helpers : normalisation des dates ───────────────────────────────────
    # metrage_prevu (code-01) = compteur machine au DÉBUT de session
    # metrage_reel  (code-89) = compteur machine à la FIN de session
    # → métrage produit par session = fin_counter − debut_counter
    _FMTS = (
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
        "%Y-%m-%d", "%d/%m/%Y",
    )
    def _norm_date(dt_raw: str) -> str:
        """Retourne 'YYYY-MM-DD' depuis n'importe quel format."""
        s = str(dt_raw or "").strip()
        for fmt in _FMTS:
            try:
                return _dt_cls.strptime(s, fmt).date().isoformat()
            except ValueError:
                continue
        return s[:10]

    def _norm_dt(dt_raw: str) -> str:
        """Retourne 'YYYY-MM-DDTHH:MM:SS' depuis n'importe quel format."""
        s = str(dt_raw or "").strip()
        for fmt in _FMTS:
            try:
                return _dt_cls.strptime(s, fmt).isoformat()
            except ValueError:
                continue
        return s

    # ── Construire debut_entries et fin_data ─────────────────────────────────
    # all_list est trié par (operateur, date_operation), donc quand on traite
    # un code-89, tous les code-01 antérieurs pour cet opérateur sont déjà indexés.
    debut_entries = {}   # (op, dos) -> [(norm_dt_iso, compteur_debut_float), ...]
    fin_data      = {}   # (op, jour_iso, dos) -> {"metrage_m": float, "etiquettes": float}

    for r in all_list:
        code  = str(r.get("operation_code") or "")
        dos   = str(r.get("no_dossier") or "").strip()
        if not dos or dos == "0":
            continue
        op    = str(r.get("operateur") or "?")
        dt_op = str(r.get("date_operation") or "")

        if code == "01":
            # Compteur début = metrage_prevu, ou 0 si absent (1re session du dossier)
            ctr = float(r["metrage_prevu"]) if r.get("metrage_prevu") is not None else 0.0
            debut_entries.setdefault((op, dos), []).append((_norm_dt(dt_op), ctr))

        elif code == "89" and r.get("metrage_reel") is not None:
            fin_dt   = _norm_dt(dt_op)
            jour_iso = _norm_date(dt_op)
            key      = (op, jour_iso, dos)
            entry    = fin_data.setdefault(key, {"metrage_m": 0.0, "etiquettes": 0.0})

            # Compteur début = dernier code-01 dont l'heure ≤ heure de cette fin
            debuts   = debut_entries.get((op, dos), [])
            before   = [(dt, m) for dt, m in debuts if dt <= fin_dt]
            debut_ctr = sorted(before, reverse=True)[0][1] if before else 0.0

            produit = max(0.0, float(r["metrage_reel"]) - debut_ctr)
            entry["metrage_m"] += produit
            if r.get("quantite_traitee") is not None:
                entry["etiquettes"] = float(r["quantite_traitee"])

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
    # Pour chaque fin (code-89) dans completed, calculer fin − début via fin_data
    completed_list = []
    for r in completed:
        row      = dict(r)
        op       = str(row.get("operateur") or "?")
        dos      = str(row.get("no_dossier") or "").strip()
        jour_iso = _norm_date(str(row.get("date_operation") or ""))
        # Récupérer le métrage produit déjà calculé dans fin_data
        entry    = fin_data.get((op, jour_iso, dos), {})
        row["metrage_produit"] = round(entry.get("metrage_m", 0.0), 1)
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
