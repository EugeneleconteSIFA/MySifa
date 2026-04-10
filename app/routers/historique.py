"""SIFA — Historique v0.9
Sanity Score basé sur la cohérence “journée opérateur” + saisies clés.
"""
from datetime import datetime
from typing import Optional, List, Any, Dict
from fastapi import APIRouter, Request, Query
from database import get_db, parse_datetime
from services.analyse import analyse_saisie_errors
from services.auth_service import get_current_user, is_admin
from config import CODE_ARRIVEE, CODE_DEPART, CODE_DEBUT_DOS, CODE_FIN_DOS, CODE_CALAGE, CODE_PRODUCTION, CODE_REPRISE

router = APIRouter()

BLOCKED = {
    "blocked": True,
    "message": "Votre compte n'est pas encore lié à un opérateur. Contactez un administrateur.",
    "total_operations": 0, "severity_counts": {}, "category_counts": [],
    "issues": [], "operator_issues": [], "machine_issues": [],
    "saisie_errors": [], "saisie_errors_count": 0,
    "sanity": {"score": 0, "mention": "Non lié", "color": "danger", "penalites": []},
}


def _day_key(dt: Optional[datetime], raw: Any) -> str:
    if dt:
        return dt.date().isoformat()
    s = str(raw or "")
    return s[:10] if len(s) >= 10 else s


def compute_sanity_score_v2(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Sanity v2 (règles métier).

    Règles (pénalités cumulées, score sur 100):
    - -5  si arrivée (86) n'est pas la 1ère étape OU départ (87) n'est pas la dernière étape
    - -5  si début dossier (01) n'est pas la 2e étape OU fin dossier (89) n'est pas l'avant-dernière étape
    - -5  si aucun code de {production|calage|technique} dans la journée
    - -5  si durée entre arrivée et départ < 5h (si les deux existent)
    - -2  si arrêt machine (code 50) présent
    - -7  si fin dossier (89) sans métrage réel
    - -7  si fin dossier (89) sans quantité traitée (nb étiquettes)
    """
    if not rows:
        return {"score": 0, "mention": "Aucune saisie", "color": "warn", "penalites": [], "events": {}}

    # Group by opérateur + jour
    by_op_day: Dict[tuple[str, str], list[dict]] = {}
    dt_cache: Dict[int, Optional[datetime]] = {}
    for r in rows:
        op = str(r.get("operateur") or "?")
        dt = parse_datetime(r.get("date_operation"))
        dt_cache[id(r)] = dt
        dk = _day_key(dt, r.get("date_operation"))
        by_op_day.setdefault((op, dk), []).append(r)

    penalites: list[dict] = []
    total_pen = 0
    events: Dict[str, List[Dict[str, Any]]] = {}

    def add_pen(p_type: str, label: str, pts: int, count: int):
        nonlocal total_pen
        if count <= 0:
            return
        total = pts * count
        total_pen += total
        penalites.append({"type": p_type, "label": label, "count": count, "pts_unitaire": pts, "total": total})

    def add_event(t: str, operateur: str, jour: str, no_dossier: Optional[str] = None):
        events.setdefault(t, []).append(
            {"operateur": operateur, "jour": jour, "no_dossier": (no_dossier or "")}
        )

    c_first_last = 0
    c_second_penult = 0
    c_need_prod_cal_tech = 0
    c_short_shift = 0
    c_arret_50 = 0
    c_missing_metrage = 0
    c_missing_etiquettes = 0

    prod_codes = {CODE_PRODUCTION, CODE_REPRISE}
    calage_codes = {CODE_CALAGE, "10", "11", "59", "60", "74", "75"}
    tech_codes = {"64", "73", "76"}

    for (op, jour), lignes in by_op_day.items():
        lignes_sorted = sorted(lignes, key=lambda x: dt_cache.get(id(x)) or datetime.min)
        codes = [str(x.get("operation_code") or "") for x in lignes_sorted]
        codes = [c for c in codes if c]
        if not codes:
            continue

        # -5 : 86 première et 87 dernière
        if codes[0] != CODE_ARRIVEE or codes[-1] != CODE_DEPART:
            c_first_last += 1
            add_event("jour_first_last", op, jour)

        # -5 : 01 deuxième et 89 avant-dernière (si assez de lignes)
        if len(codes) < 3 or codes[1] != CODE_DEBUT_DOS or codes[-2] != CODE_FIN_DOS:
            c_second_penult += 1
            add_event("jour_second_penult", op, jour)

        # -5 : au moins un prod/calage/tech
        has_any = any(c in prod_codes or c in calage_codes or c in tech_codes for c in codes)
        if not has_any:
            c_need_prod_cal_tech += 1
            add_event("jour_need_prod_cal_tech", op, jour)

        # -5 : durée arrivée->départ < 5h (si présents)
        try:
            idx_arr = codes.index(CODE_ARRIVEE)
            idx_dep = len(codes) - 1 - list(reversed(codes)).index(CODE_DEPART)
            dt_arr = dt_cache.get(id(lignes_sorted[idx_arr]))
            dt_dep = dt_cache.get(id(lignes_sorted[idx_dep]))
            if dt_arr and dt_dep:
                dur_h = (dt_dep - dt_arr).total_seconds() / 3600.0
                if dur_h < 5.0:
                    c_short_shift += 1
                    add_event("jour_short_shift", op, jour)
        except ValueError:
            # si manque arrivée/départ, déjà pénalisé dans la règle first/last
            pass

        # -2 : arrêt machine 50 présent
        if "50" in codes:
            c_arret_50 += 1
            add_event("jour_arret_50", op, jour)

        # -7 : manque métrage / nb étiquettes sur fin dossier (89)
        # Règle appliquée par journée: si au moins une fin dossier est incomplète.
        miss_m = False
        miss_q = False
        for x in lignes_sorted:
            if str(x.get("operation_code") or "") != CODE_FIN_DOS:
                continue
            mr = x.get("metrage_reel", None)
            qt = x.get("quantite_traitee", None)
            dos = x.get("no_dossier") or ""
            if mr is None or (isinstance(mr, (int, float)) and float(mr) == 0.0) or str(mr).strip() == "":
                miss_m = True
                add_event("jour_missing_metrage", op, jour, str(dos))
            if qt is None or (isinstance(qt, (int, float)) and float(qt) == 0.0) or str(qt).strip() == "":
                miss_q = True
                add_event("jour_missing_etiquettes", op, jour, str(dos))
        if miss_m:
            c_missing_metrage += 1
        if miss_q:
            c_missing_etiquettes += 1

    add_pen("jour_first_last", "Journée: arrivée 1ère étape / départ dernière étape", -5, c_first_last)
    add_pen("jour_second_penult", "Journée: début dossier 2e étape / fin dossier avant-dernière", -5, c_second_penult)
    add_pen("jour_need_prod_cal_tech", "Journée: au moins une production/calage/technique", -5, c_need_prod_cal_tech)
    add_pen("jour_short_shift", "Journée: arrivée→départ < 5h", -5, c_short_shift)
    add_pen("jour_arret_50", "Arrêt machine (code 50)", -2, c_arret_50)
    add_pen("jour_missing_metrage", "Fin dossier: métrage manquant", -7, c_missing_metrage)
    add_pen("jour_missing_etiquettes", "Fin dossier: nombre d’étiquettes manquant", -7, c_missing_etiquettes)

    # pts négatifs => total_pen négatif : on soustrait via addition
    score = 100 + total_pen
    score = max(0, min(100, int(round(score))))
    if score >= 90:
        mention, color = "Excellent", "success"
    elif score >= 70:
        mention, color = "Bon", "warn"
    elif score >= 50:
        mention, color = "À améliorer", "warn"
    else:
        mention, color = "Critique", "danger"
    # Dédupliquer les events (mêmes jour/op/dossier)
    for t, lst in list(events.items()):
        seen = set()
        out = []
        for e in lst:
            key = (e.get("operateur") or "", e.get("jour") or "", e.get("no_dossier") or "")
            if key in seen:
                continue
            seen.add(key)
            out.append(e)
        events[t] = out

    return {"score": score, "mention": mention, "color": color, "penalites": penalites, "events": events}


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

    def compute_duree_minutes_by_id(rows: List[dict]) -> Dict[int, float]:
        """Durée (minutes) = écart jusqu'à la saisie suivante, par opérateur+jour.

        Ignore:
        - date non parsable
        - écarts > 8h ou négatifs (comme ailleurs)
        """
        # grouper par opérateur/jour, puis calculer next_dt
        by_key: Dict[tuple[str, str], list[tuple[datetime, dict]]] = {}
        for r in rows:
            rid = r.get("id")
            dt = parse_datetime(r.get("date_operation"))
            if rid is None or dt is None:
                continue
            key = (str(r.get("operateur") or "?"), dt.date().isoformat())
            by_key.setdefault(key, []).append((dt, r))

        out: Dict[int, float] = {}
        for _k, items in by_key.items():
            items_sorted = sorted(items, key=lambda x: x[0])
            for i, (dt, r) in enumerate(items_sorted[:-1]):
                nxt = items_sorted[i + 1][0]
                delta = (nxt - dt).total_seconds() / 60.0
                if delta < 0 or delta > 480:
                    continue
                rid = int(r["id"])
                out[rid] = round(delta, 1)
        return out

    with get_db() as conn:
        total     = conn.execute(f"SELECT COUNT(*) as c FROM production_data WHERE {wc}", params).fetchone()["c"]
        sev       = conn.execute(f"SELECT operation_severity, COUNT(*) as c FROM production_data WHERE {wc} GROUP BY operation_severity", params).fetchall()
        cat       = conn.execute(f"SELECT operation_category, operation_severity, COUNT(*) as c FROM production_data WHERE {wc} GROUP BY operation_category, operation_severity ORDER BY c DESC", params).fetchall()
        # Toutes les lignes (pour durées)
        dur_rows  = conn.execute(
            f"""SELECT id, operateur, date_operation
                FROM production_data
                WHERE {wc}
                ORDER BY operateur, date_operation""",
            params,
        ).fetchall()
        issues    = conn.execute(f"""
            SELECT id, operateur,date_operation,operation,operation_code,operation_severity,
                   operation_category,machine,no_dossier,client,designation
            FROM production_data WHERE {wc} AND operation_severity IN ('critique','attention')
            ORDER BY date_operation DESC LIMIT 200""", params).fetchall()
        op_issues = conn.execute(f"""
            SELECT operateur,operation_severity,COUNT(*) as c
            FROM production_data WHERE {wc} AND operation_severity IN ('critique','attention')
            GROUP BY operateur,operation_severity ORDER BY c DESC""", params).fetchall()

        # Arrêts machine (lignes)
        arret_rows = conn.execute(
            f"""SELECT id, operateur, date_operation, operation_code, operation
                FROM production_data
                WHERE {wc} AND operation_category='arret'
                ORDER BY operateur, date_operation""",
            params,
        ).fetchall()
        m_issues  = conn.execute(f"""
            SELECT machine,operation_severity,COUNT(*) as c
            FROM production_data WHERE {wc} AND operation_severity IN ('critique','attention')
              AND machine IS NOT NULL AND machine != ''
            GROUP BY machine,operation_severity ORDER BY c DESC""", params).fetchall()
        san_rows  = conn.execute(f"""
            SELECT operateur,date_operation,operation_code,operation_category,machine,no_dossier,
                   quantite_a_traiter,quantite_traitee,metrage_prevu,metrage_reel
            FROM production_data WHERE {wc_san}
            ORDER BY operateur,date_operation""", ps).fetchall()

    duree_by_id = compute_duree_minutes_by_id([dict(r) for r in dur_rows])
    issues_list = [dict(r) for r in issues]
    for it in issues_list:
        rid = it.get("id")
        it["duree_min"] = duree_by_id.get(int(rid), None) if rid is not None else None

    # Agréger arrêts par opérateur + type, avec durée cumulée
    operator_arrets: list[dict] = []
    tmp: Dict[tuple[str, str, str], dict] = {}
    for r in [dict(x) for x in arret_rows]:
        op = str(r.get("operateur") or "?")
        code = str(r.get("operation_code") or "")
        op_lbl = str(r.get("operation") or "")
        key = (op, code, op_lbl)
        acc = tmp.get(key)
        if not acc:
            acc = {"operateur": op, "operation_code": code, "operation": op_lbl, "c": 0, "duree_min": 0.0}
            tmp[key] = acc
        acc["c"] += 1
        rid = r.get("id")
        if rid is not None:
            acc["duree_min"] += float(duree_by_id.get(int(rid), 0.0) or 0.0)
    operator_arrets = sorted(
        [{**v, "duree_min": round(float(v.get("duree_min") or 0.0), 1)} for v in tmp.values()],
        key=lambda x: (x["operateur"], -(x.get("c") or 0)),
    )

    san_list = [dict(r) for r in san_rows]
    saisie_errors = analyse_saisie_errors(san_list)
    sanity        = compute_sanity_score_v2(san_list)

    sanity_by_operateur = None
    if is_admin(user):
        # Si multi-sélection opérateurs => un sanity score par opérateur
        sel_ops = operateurs
        if sel_ops and len(sel_ops) > 1:
            sanity_by_operateur = {}
            for op in sel_ops:
                sub = [r for r in san_list if str(r.get("operateur") or "") == str(op)]
                sanity_by_operateur[op] = compute_sanity_score_v2(sub)

    return {
        "blocked": False,
        "total_operations":    total,
        "severity_counts":     {r["operation_severity"]: r["c"] for r in sev},
        "category_counts":     [dict(r) for r in cat],
        "issues":              issues_list,
        "operator_issues":     [dict(r) for r in op_issues],
        "operator_arrets":     operator_arrets,
        "machine_issues":      [dict(r) for r in m_issues],
        "saisie_errors":       saisie_errors,
        "saisie_errors_count": len(saisie_errors),
        "sanity":              sanity,
        "sanity_by_operateur": sanity_by_operateur,
    }
