"""SIFA — Historique v0.9
Sanity Score basé sur la cohérence “journée opérateur” + saisies clés.
"""
from datetime import datetime
from typing import Optional, List, Any, Dict
from fastapi import APIRouter, Request, Query
from database import get_db, parse_datetime
from services.analyse import analyse_saisie_errors, assign_shift_keys
from services.auth_service import get_current_user, is_admin, can_view_all_prod
from services.prod_machine_filter import append_machine_filter, norm_machine_canonical
from config import CODE_ARRIVEE, CODE_DEPART, CODE_DEBUT_DOS, CODE_FIN_DOS, CODE_CALAGE, CODES_CALAGE, CODE_PRODUCTION, CODE_REPRISE

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


def compute_sanity_score_v2(
    rows: List[Dict[str, Any]],
    ctx: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Sanity v2 (règles métier).

    Règles (pénalités cumulées, score sur 100):
    - -5  si arrivée (86) n'est pas la 1ère étape OU départ (87) n'est pas la dernière étape
    - -5  si début dossier (01) n'est pas la 2e étape OU fin dossier (89) n'est pas l'avant-dernière étape
    - -5  si aucun code de {production|calage|technique} dans la journée
    - -5  si durée entre arrivée et départ < 5h (si les deux existent)
    - -2  si arrêt machine (code 50) présent
    - -7  si fin dossier (89) sans métrage réel
    - -7  si fin dossier (89) sans quantité traitée (nb étiquettes)
    - -7  si début dossier (01) directement suivi d'une fin dossier (89)
           sans saisie intermédiaire (calage / production / nettoyage / technique)

    Règles ajoutées via ``ctx`` (backward-compatible : sans ctx, comportement
    identique à v2 historique) :
    - -7  si fin dossier (89) sans aucune entrée Z1 pour ce no_dossier
    - -3  par entrée Z1 sans palettes déclarées (mouvement_palettes vide)
    - -3  si fin dossier avec quantite_traitee>0 mais aucun scan MP
    - +1  par alerte maintenance/qualité validée pendant la journée opérateur

    ctx (tous optionnels) :
        z1_by_dossier      : {no_dossier: {"count": int, "mouvement_ids": [int]}}
        palettes_by_mvt_id : {mouvement_id: nb_palettes_declarees}
        mp_scans_by_dossier: {no_dossier: nb_scans}
        acks_by_op_day     : {(operateur, "YYYY-MM-DD"): nb_acks}
    """
    if not rows:
        return {"score": 0, "mention": "Aucune saisie", "color": "warn", "penalites": [], "events": {}}

    ctx = ctx or {}
    z1_by_dossier       = ctx.get("z1_by_dossier") or {}
    palettes_by_mvt_id  = ctx.get("palettes_by_mvt_id") or {}
    mp_scans_by_dossier = ctx.get("mp_scans_by_dossier") or {}
    acks_by_op_day      = ctx.get("acks_by_op_day") or {}

    # Group by opérateur + shift ("journée opérateur" : 86 → 87, peut
    # traverser minuit). assign_shift_keys mute les lignes en y ajoutant
    # ``_shift_key`` et renvoie le cache de datetimes parsés.
    dt_cache: Dict[int, Optional[datetime]] = assign_shift_keys(rows)
    by_op_day: Dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        op = str(r.get("operateur") or "?")
        sk = r.get("_shift_key") or _day_key(dt_cache.get(id(r)), r.get("date_operation"))
        by_op_day.setdefault((op, sk), []).append(r)

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
    c_empty_dossier = 0
    # Nouvelles règles Z1 / MP / alertes (dépendent de ctx)
    c_89_no_z1 = 0
    c_z1_no_palettes = 0
    c_89_no_mp_scan = 0
    c_alertes_ok = 0

    prod_codes = {CODE_PRODUCTION, CODE_REPRISE}
    calage_codes = CODES_CALAGE
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

        # -7 : manque métrage sur fin dossier (89)
        # Règle appliquée par journée: si au moins une fin dossier est incomplète.
        # Boucle mutualisée avec les nouvelles règles Z1/MP pour éviter deux
        # itérations sur les mêmes lignes.
        miss_m = False
        seen_dossiers_89: set[str] = set()
        for x in lignes_sorted:
            if str(x.get("operation_code") or "") != CODE_FIN_DOS:
                continue
            mr = x.get("metrage_reel", None)
            dos_raw = x.get("no_dossier") or ""
            dos = str(dos_raw).strip()
            if mr is None or (isinstance(mr, (int, float)) and float(mr) == 0.0) or str(mr).strip() == "":
                miss_m = True
                add_event("jour_missing_metrage", op, jour, dos)

            # ── Nouvelles règles Z1 / MP (ctx-dépendantes) ────────────
            # On dédoublonne par no_dossier au sein de la même journée op :
            # une même fin de dossier saisie deux fois ne pénalise qu'une fois.
            if not dos or dos in seen_dossiers_89:
                continue
            seen_dossiers_89.add(dos)

            # Uniquement si un ctx a été fourni côté appelant. Sinon on
            # skippe silencieusement (weekly_report et anciens appels
            # gardent leur comportement).
            if not ctx:
                continue

            z1_info = z1_by_dossier.get(dos) or {}
            z1_count = int(z1_info.get("count") or 0)
            if z1_count == 0:
                c_89_no_z1 += 1
                add_event("dossier_fin_sans_z1", op, jour, dos)
            else:
                mvt_ids = z1_info.get("mouvement_ids") or []
                for mid in mvt_ids:
                    try:
                        nb_pal = int(palettes_by_mvt_id.get(mid, 0) or 0)
                    except (TypeError, ValueError):
                        nb_pal = 0
                    if nb_pal == 0:
                        c_z1_no_palettes += 1
                        add_event("z1_sans_palettes", op, jour, dos)

            # Scan MP : fin dossier avec quantité traitée > 0 et 0 scan.
            q_tr = x.get("quantite_traitee", None)
            try:
                q_tr_f = float(q_tr) if q_tr is not None else 0.0
            except (TypeError, ValueError):
                q_tr_f = 0.0
            nb_scans = int(mp_scans_by_dossier.get(dos, 0) or 0)
            if q_tr_f > 0 and nb_scans == 0:
                c_89_no_mp_scan += 1
                add_event("dossier_fin_sans_mp_scan", op, jour, dos)
        if miss_m:
            c_missing_metrage += 1

        # ── Bonus alertes maintenance/qualité validées sur la journée ─
        # +1 point par ack pris sur cette (op, jour). On ne dédoublonne
        # pas : chaque validation d'alerte compte, y compris plusieurs
        # occurrences d'une même alerte périodique dans la journée.
        # Clé opérateur normalisée (lower/strip) : les noms peuvent différer
        # entre production_data.operateur et maintenance_alert_acks.user_nom.
        if ctx:
            op_key_ack = str(op or "").strip().lower()
            try:
                nb_acks = int(acks_by_op_day.get((op_key_ack, jour), 0) or 0)
            except (TypeError, ValueError):
                nb_acks = 0
            if nb_acks > 0:
                c_alertes_ok += nb_acks

        # -7 : début dossier (01) directement suivi de fin dossier (89)
        # sans saisie intermédiaire (calage/production/nettoyage/technique).
        # On considère comme "non productifs" les codes qui ne représentent
        # pas du travail réel sur le dossier: 01, 89, 86 (arrivée), 87 (départ).
        non_work_codes = {CODE_DEBUT_DOS, CODE_FIN_DOS, CODE_ARRIVEE, CODE_DEPART}
        idx_walk = 0
        while idx_walk < len(codes):
            if codes[idx_walk] == CODE_DEBUT_DOS:
                # Chercher la prochaine fin dossier (89) après ce 01
                end_idx = idx_walk + 1
                has_work = False
                while end_idx < len(codes) and codes[end_idx] != CODE_FIN_DOS:
                    if codes[end_idx] not in non_work_codes:
                        has_work = True
                    end_idx += 1
                if (
                    end_idx < len(codes)
                    and codes[end_idx] == CODE_FIN_DOS
                    and not has_work
                ):
                    c_empty_dossier += 1
                    dossier_no = lignes_sorted[end_idx].get("no_dossier") or \
                                 lignes_sorted[idx_walk].get("no_dossier") or ""
                    add_event("jour_empty_dossier", op, jour, str(dossier_no))
                idx_walk = end_idx + 1
            else:
                idx_walk += 1

    add_pen("jour_first_last", "Journée: arrivée 1ère étape / départ dernière étape", -5, c_first_last)
    add_pen("jour_second_penult", "Journée: début dossier 2e étape / fin dossier avant-dernière", -5, c_second_penult)
    add_pen("jour_need_prod_cal_tech", "Journée: au moins une production/calage/technique", -5, c_need_prod_cal_tech)
    add_pen("jour_short_shift", "Journée: arrivée→départ < 5h", -5, c_short_shift)
    add_pen("jour_arret_50", "Arrêt machine (code 50)", -2, c_arret_50)
    add_pen("jour_missing_metrage", "Fin dossier: métrage manquant", -7, c_missing_metrage)
    add_pen(
        "jour_empty_dossier",
        "Dossier vide: début → fin sans saisie intermédiaire (calage/prod/nettoyage)",
        -7,
        c_empty_dossier,
    )
    # Nouvelles règles (dépendent de ctx — 0 si non fourni)
    add_pen("dossier_fin_sans_z1", "Fin de dossier sans entrée Z1", -7, c_89_no_z1)
    add_pen("z1_sans_palettes", "Entrée Z1 sans palettes déclarées", -3, c_z1_no_palettes)
    add_pen(
        "dossier_fin_sans_mp_scan",
        "Fin de dossier avec quantité traitée mais aucun scan matière",
        -3,
        c_89_no_mp_scan,
    )
    # Bonus (pts unitaire positif)
    add_pen("bonus_alertes_validees", "Alertes maintenance/qualité validées", 1, c_alertes_ok)

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


def _sanity_mention_color(score: int) -> tuple[str, str]:
    if score >= 90:
        return "Excellent", "success"
    if score >= 70:
        return "Bon", "warn"
    if score >= 50:
        return "À améliorer", "warn"
    return "Critique", "danger"


def _activity_minutes_by_operateur(
    dur_rows: List[dict], duree_by_id: Dict[int, float]
) -> Dict[str, float]:
    """Temps d'activité = somme des durées entre saisies consécutives (minutes)."""
    agg: Dict[str, float] = {}
    for r in dur_rows:
        rid = r.get("id")
        if rid is None:
            continue
        mins = float(duree_by_id.get(int(rid), 0.0) or 0.0)
        if mins <= 0:
            continue
        op = str(r.get("operateur") or "?")
        agg[op] = round(agg.get(op, 0.0) + mins, 1)
    return agg


def compute_weighted_sanity(
    sanity_by_operateur: Dict[str, Dict[str, Any]],
    activity_min_by_operateur: Dict[str, float],
    selected_ops: List[str],
) -> Dict[str, Any]:
    """Moyenne pondérée : Σ(note_i × temps_i) / Σ(temps_i) (temps en minutes)."""
    num = 0.0
    den = 0.0
    weights_used: Dict[str, float] = {}
    for op in selected_ops:
        san = sanity_by_operateur.get(op)
        if not san:
            continue
        w = float(activity_min_by_operateur.get(op, 0.0) or 0.0)
        if w <= 0:
            continue
        weights_used[op] = w
        num += float(san.get("score", 0) or 0) * w
        den += w

    if den <= 0:
        scores = [
            float(sanity_by_operateur[op].get("score", 0) or 0)
            for op in selected_ops
            if op in sanity_by_operateur
        ]
        if not scores:
            return {**compute_sanity_score_v2([]), "weighted": True}
        score = int(round(sum(scores) / len(scores)))
    else:
        score = int(round(num / den))

    score = max(0, min(100, score))
    mention, color = _sanity_mention_color(score)
    return {
        "score": score,
        "mention": mention,
        "color": color,
        "penalites": [],
        "events": {},
        "weighted": True,
        "activity_min_by_operateur": weights_used,
    }


@router.get("/api/dashboard/historique")
def dashboard_historique(
    request: Request,
    operateur: Optional[List[str]] = Query(default=None),
    no_dossier: Optional[List[str]] = Query(default=None),
    machine: Optional[List[str]] = Query(default=None),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    user = get_current_user(request)
    # Pour fabrication: utiliser nom si operateur_lie n'est pas défini
    user_operateur = user.get("operateur_lie") or user.get("nom") or ""
    if not can_view_all_prod(user) and not user_operateur:
        return {**BLOCKED}

    operateurs = [o for o in (operateur or []) if o]
    dossiers   = [d for d in (no_dossier or []) if d]
    machines   = [m for m in (machine or []) if m]

    # ── Filtre principal (avec dossiers) ──────────────────────────
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

    # ── Filtre Sanity (sans filtre dossier) ───────────────────────
    ws, ps = ["1=1"], []
    if can_view_all_prod(user):
        if operateurs:
            ws.append(f"operateur IN ({','.join('?'*len(operateurs))})")
            ps.extend(operateurs)
    else:
        # Pour fabrication: filtrer par operateur_lie ou nom utilisateur
        ws.append("operateur = ?"); ps.append(user_operateur)
    if date_from: ws.append("date_operation >= ?"); ps.append(date_from)
    if date_to:   ws.append("date_operation <= ?"); ps.append(date_to+'T23:59:59')

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
            items_sorted = sorted(
                items,
                key=lambda x: (x[0] if x[0] else datetime.min, int(x[1].get("id") or 0)),
            )
            for i, (dt, r) in enumerate(items_sorted[:-1]):
                nxt = items_sorted[i + 1][0]
                delta = (nxt - dt).total_seconds() / 60.0
                if delta < 0 or delta > 480:
                    continue
                rid = int(r["id"])
                out[rid] = round(delta, 1)
        return out

    with get_db() as conn:
        if machines:
            append_machine_filter(where, params, conn, machines)
            append_machine_filter(ws, ps, conn, machines)
        wc = " AND ".join(where)
        wc_san = " AND ".join(ws)
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
        # Exclure les saisies machine Repiquage du calcul "Qualite de saisie".
        # Le score n'a pas de sens pour l'atelier Repiquage qui utilise un comptage carton.
        san_machine_excl = (
            "AND NOT (lower(trim(COALESCE(machine,''))) LIKE 'repiquage%' "
            " OR lower(trim(COALESCE(machine,''))) = 'rep' "
            " OR lower(trim(COALESCE(machine,''))) LIKE 'rep %')"
        )
        san_rows  = conn.execute(f"""
            SELECT operateur,date_operation,operation_code,operation_category,machine,no_dossier,
                   quantite_a_traiter,quantite_traitee,metrage_prevu,metrage_reel
            FROM production_data WHERE {wc_san} {san_machine_excl}
            ORDER BY operateur,date_operation""", ps).fetchall()

        # ── Contexte enrichi pour compute_sanity_score_v2 ─────────────
        # Objectif : intégrer au score les actions opérateur qui ne sont pas
        # dans production_data (entrées Z1, palettes déclarées, scans MP,
        # alertes maintenance/qualité ackées). Toutes ces requêtes sont
        # scopées aux dossiers/opérateurs/dates déjà filtrés par l'UI, donc
        # bornées et indexées.
        sanity_ctx: Dict[str, Any] = {
            "z1_by_dossier": {},
            "palettes_by_mvt_id": {},
            "mp_scans_by_dossier": {},
            "acks_by_op_day": {},
        }
        san_dossiers = sorted({
            str(r["no_dossier"]).strip()
            for r in san_rows
            if r["no_dossier"] and str(r["no_dossier"]).strip()
        })
        if san_dossiers:
            ph_d = ",".join(["?"] * len(san_dossiers))
            # Entrées Z1 (produit fini → stock zone Z1) rattachées à ces dossiers
            z1_rows = conn.execute(
                f"""SELECT id, no_dossier
                    FROM mouvements_stock
                    WHERE type_mouvement='entree'
                      AND UPPER(COALESCE(emplacement,'')) = 'Z1'
                      AND TRIM(COALESCE(no_dossier,'')) IN ({ph_d})""",
                san_dossiers,
            ).fetchall()
            z1_by_dossier_ctx: Dict[str, Dict[str, Any]] = {}
            all_z1_mvt_ids: list[int] = []
            for r in z1_rows:
                d = str(r["no_dossier"]).strip()
                info = z1_by_dossier_ctx.setdefault(d, {"count": 0, "mouvement_ids": []})
                info["count"] += 1
                info["mouvement_ids"].append(int(r["id"]))
                all_z1_mvt_ids.append(int(r["id"]))
            sanity_ctx["z1_by_dossier"] = z1_by_dossier_ctx

            # Palettes déclarées par mouvement (mouvement_palettes)
            if all_z1_mvt_ids:
                ph_m = ",".join(["?"] * len(all_z1_mvt_ids))
                pal_rows = conn.execute(
                    f"""SELECT mouvement_id, COUNT(*) AS n
                        FROM mouvement_palettes
                        WHERE mouvement_id IN ({ph_m})
                        GROUP BY mouvement_id""",
                    all_z1_mvt_ids,
                ).fetchall()
                sanity_ctx["palettes_by_mvt_id"] = {
                    int(r["mouvement_id"]): int(r["n"]) for r in pal_rows
                }

            # Scans matière première par dossier
            mp_rows_s = conn.execute(
                f"""SELECT TRIM(no_dossier) AS no_dossier, COUNT(*) AS n
                    FROM fab_matieres_utilisees
                    WHERE TRIM(COALESCE(no_dossier,'')) IN ({ph_d})
                    GROUP BY TRIM(no_dossier)""",
                san_dossiers,
            ).fetchall()
            sanity_ctx["mp_scans_by_dossier"] = {
                str(r["no_dossier"]).strip(): int(r["n"]) for r in mp_rows_s
            }

        # Alertes maintenance/qualité ackées, groupées par (opérateur, jour)
        # Clé opérateur en lower/strip pour matcher production_data.operateur
        # (l'UI ack utilise user.nom, qui peut différer légèrement).
        san_ops_norm = sorted({
            str(r["operateur"] or "").strip().lower()
            for r in san_rows
            if r["operateur"] and str(r["operateur"]).strip()
        })
        if san_ops_norm:
            ph_op = ",".join(["?"] * len(san_ops_norm))
            ack_q = (
                "SELECT LOWER(TRIM(COALESCE(user_nom,''))) AS op, "
                "       DATE(ack_at) AS d, COUNT(*) AS n "
                "FROM maintenance_alert_acks "
                f"WHERE LOWER(TRIM(COALESCE(user_nom,''))) IN ({ph_op})"
            )
            ack_params: list = list(san_ops_norm)
            if date_from:
                ack_q += " AND ack_at >= ?"
                ack_params.append(date_from + "T00:00:00")
            if date_to:
                ack_q += " AND ack_at <= ?"
                ack_params.append(date_to + "T23:59:59")
            ack_q += " GROUP BY op, d"
            ack_rows = conn.execute(ack_q, ack_params).fetchall()
            sanity_ctx["acks_by_op_day"] = {
                (str(r["op"] or ""), str(r["d"] or "")): int(r["n"])
                for r in ack_rows
            }

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
    sanity        = compute_sanity_score_v2(san_list, sanity_ctx)

    # Si le filtre machine ne contient QUE Repiquage, neutraliser le sanity score
    # (sinon il vaudrait 100 par defaut sur 0 evenement, ce qui est trompeur).
    repiquage_only = bool(machines) and all(
        (norm_machine_canonical(m) == "Repiquage") for m in machines
    )
    if repiquage_only:
        sanity = None
        saisie_errors = []

    sanity_by_operateur = None
    if can_view_all_prod(user) and not repiquage_only:
        # Si multi-sélection opérateurs => score par opérateur + moyenne pondérée globale
        sel_ops = operateurs
        if sel_ops and len(sel_ops) > 1:
            sanity_by_operateur = {}
            for op in sel_ops:
                sub = [r for r in san_list if str(r.get("operateur") or "") == str(op)]
                # ctx est partagé : les clés (op, jour) et no_dossier
                # sont scopées, le sous-set d'op filtre naturellement.
                sanity_by_operateur[op] = compute_sanity_score_v2(sub, sanity_ctx)
            activity_min = _activity_minutes_by_operateur(
                [dict(r) for r in dur_rows], duree_by_id
            )
            sanity = compute_weighted_sanity(
                sanity_by_operateur, activity_min, sel_ops
            )

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
