"""SIFA — Historique v0.10
Sanity Score : une note par journée opérateur, puis moyenne pondérée par la durée.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Any, Dict
from fastapi import APIRouter, Request, Query
from database import get_db, parse_datetime
from services.analyse import analyse_saisie_errors, assign_shift_keys
from services.auth_service import get_current_user, is_admin, can_view_all_prod
from services.prod_machine_filter import append_machine_filter, norm_machine_canonical
from config import CODE_ARRIVEE, CODE_DEPART, CODE_DEBUT_DOS, CODE_FIN_DOS, CODE_CALAGE, CODES_CALAGE, CODE_PRODUCTION, CODE_REPRISE
from config import SANITY_JOURNEE_MIN_H, SANITY_DELAI_Z1_H, SANITY_POIDS_MIN_MIN

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


def _clamp_score(v: float) -> int:
    return max(0, min(100, int(round(v))))


def sanity_regles() -> List[Dict[str, Any]]:
    """Règles du score, pour la modale « Comment c'est calculé » de MyProd.

    Une seule définition : le calcul et l'explication lisent les mêmes
    seuils, l'écran ne peut pas décrire une règle que le code n'applique plus.
    """
    h_min = f"{SANITY_JOURNEE_MIN_H:g} h"
    d_z1 = f"{SANITY_DELAI_Z1_H:g} h"
    return [
        {"groupe": "journee", "pts": -5, "label": "L'arrivée (86) n'est pas la première saisie, ou le départ (87) n'est pas la dernière"},
        {"groupe": "journee", "pts": -5, "label": "Le début de production (01) n'est pas la 2e saisie, ou la fin de production (89) n'est pas l'avant-dernière"},
        {"groupe": "journee", "pts": -5, "label": "Aucune saisie de production, calage ou intervention technique"},
        {"groupe": "journee", "pts": -5, "label": f"Journée de moins de {h_min} sans motif. Le motif est demandé au départ ; une fois donné, pas de pénalité"},
        {"groupe": "journee", "pts": -2, "label": "Arrêt machine (code 50) sans explication. Une fois expliqué, pas de pénalité"},
        {"groupe": "journee", "pts": -7, "label": "Fin de production sans métrage réel"},
        {"groupe": "dossier", "pts": -7, "label": "Début de production suivi directement d'une fin, sans saisie entre les deux (par dossier)"},
        {"groupe": "dossier", "pts": -7, "label": f"Fin de production sans entrée Z1, {d_z1} après la clôture. Avant ce délai, le dossier est « en attente », sans pénalité"},
        {"groupe": "dossier", "pts": -3, "label": "Entrée Z1 sans palette déclarée (par entrée)"},
        {"groupe": "dossier", "pts": -3, "label": "Fin de production avec quantité traitée mais aucun scan matière"},
        {"groupe": "bonus", "pts": 1, "label": "Alerte maintenance ou qualité validée dans la journée (par alerte)"},
    ]


def sanity_calcul_texte() -> List[str]:
    return [
        "Chaque journée opérateur (de l'arrivée au départ) part de 100 points. Les pénalités et bonus de la journée s'appliquent, puis la note est bornée entre 0 et 100.",
        "Le score affiché est la moyenne des journées, pondérée par leur durée : une journée de 8 h compte deux fois plus qu'une journée de 4 h.",
        "Sur plusieurs opérateurs, la même moyenne s'applique à toutes leurs journées : chacun pèse selon son temps de présence, les erreurs ne s'additionnent pas.",
        "Mentions : 90 et plus Excellent, 70 à 89 Bon, 50 à 69 À améliorer, moins de 50 Critique.",
    ]


def compute_sanity_score_v2(
    rows: List[Dict[str, Any]],
    ctx: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Sanity v3 : une note par journée opérateur, puis moyenne pondérée.

    Chaque journée (86 → 87, peut traverser minuit) part de 100, reçoit ses
    pénalités et ses bonus, et est bornée à [0, 100]. Le score renvoyé est la
    moyenne de ces notes pondérée par la durée de la journée. Sur plusieurs
    jours ou plusieurs opérateurs, les erreurs ne s'additionnent donc plus :
    un mois propre avec une mauvaise journée reste un bon mois.

    Règles : voir ``sanity_regles()`` (même source que la modale MyProd).

    Justifications qui lèvent une pénalité :
    - journée < SANITY_JOURNEE_MIN_H : commentaire sur le départ (87) ;
    - arrêt 50 : commentaire sur la saisie, ou explication rattachée au
      franchissement de seuil (ctx ``arrets_justifies``).

    ctx (tous optionnels, sans ctx les règles Z1 / MP / bonus sont ignorées) :
        z1_by_dossier      : {no_dossier: {"count": int, "mouvement_ids": [int]}}
        palettes_by_mvt_id : {mouvement_id: nb_palettes_declarees}
        mp_scans_by_dossier: {no_dossier: nb_scans}
        acks_by_op_day     : {(operateur, "YYYY-MM-DD"): nb_acks}
        arrets_justifies   : {saisie_id, ...}
        now                : datetime de référence pour le délai Z1
    """
    if not rows:
        return {"score": 0, "mention": "Aucune saisie", "color": "warn",
                "penalites": [], "events": {}, "weighted": True, "journees": 0}

    ctx = ctx or {}
    z1_by_dossier       = ctx.get("z1_by_dossier") or {}
    palettes_by_mvt_id  = ctx.get("palettes_by_mvt_id") or {}
    mp_scans_by_dossier = ctx.get("mp_scans_by_dossier") or {}
    acks_by_op_day      = ctx.get("acks_by_op_day") or {}
    arrets_justifies    = set(ctx.get("arrets_justifies") or ())
    now_ref: datetime   = ctx.get("now") or datetime.now()
    delai_z1 = timedelta(hours=SANITY_DELAI_Z1_H)

    dt_cache: Dict[int, Optional[datetime]] = assign_shift_keys(rows)
    by_op_day: Dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        op = str(r.get("operateur") or "?")
        sk = r.get("_shift_key") or _day_key(dt_cache.get(id(r)), r.get("date_operation"))
        by_op_day.setdefault((op, sk), []).append(r)

    events: Dict[str, List[Dict[str, Any]]] = {}

    def add_event(t: str, operateur: str, jour: str, no_dossier: Optional[str] = None):
        events.setdefault(t, []).append(
            {"operateur": operateur, "jour": jour, "no_dossier": (no_dossier or "")}
        )

    # Compteurs sur la période : informatifs (détail des pénalités), la note
    # elle-même se calcule journée par journée.
    PTS = {
        "jour_first_last": -5, "jour_second_penult": -5,
        "jour_need_prod_cal_tech": -5, "jour_short_shift": -5,
        "jour_arret_50": -2, "jour_missing_metrage": -7,
        "jour_empty_dossier": -7, "dossier_fin_sans_z1": -7,
        "z1_sans_palettes": -3, "dossier_fin_sans_mp_scan": -3,
        "bonus_alertes_validees": 1,
    }
    counts: Dict[str, int] = {k: 0 for k in PTS}

    prod_codes = {CODE_PRODUCTION, CODE_REPRISE}
    calage_codes = CODES_CALAGE
    tech_codes = {"64", "73", "76"}
    non_work_codes = {CODE_DEBUT_DOS, CODE_FIN_DOS, CODE_ARRIVEE, CODE_DEPART}

    num = 0.0
    den = 0.0
    nb_journees = 0

    def _txt(v: Any) -> str:
        return str(v or "").strip()

    for (op, jour), lignes in by_op_day.items():
        lignes_sorted = sorted(lignes, key=lambda x: dt_cache.get(id(x)) or datetime.min)
        lignes_sorted = [x for x in lignes_sorted if _txt(x.get("operation_code"))]
        codes = [_txt(x.get("operation_code")) for x in lignes_sorted]
        if not codes:
            continue

        jc: Dict[str, int] = {k: 0 for k in PTS}

        # 86 première et 87 dernière
        if codes[0] != CODE_ARRIVEE or codes[-1] != CODE_DEPART:
            jc["jour_first_last"] += 1
            add_event("jour_first_last", op, jour)

        # 01 deuxième et 89 avant-dernière
        if len(codes) < 3 or codes[1] != CODE_DEBUT_DOS or codes[-2] != CODE_FIN_DOS:
            jc["jour_second_penult"] += 1
            add_event("jour_second_penult", op, jour)

        # au moins un prod/calage/tech
        if not any(c in prod_codes or c in calage_codes or c in tech_codes for c in codes):
            jc["jour_need_prod_cal_tech"] += 1
            add_event("jour_need_prod_cal_tech", op, jour)

        # journée courte : levée si le départ porte un motif
        if CODE_ARRIVEE in codes and CODE_DEPART in codes:
            idx_arr = codes.index(CODE_ARRIVEE)
            idx_dep = len(codes) - 1 - codes[::-1].index(CODE_DEPART)
            dt_arr = dt_cache.get(id(lignes_sorted[idx_arr]))
            dt_dep = dt_cache.get(id(lignes_sorted[idx_dep]))
            if dt_arr and dt_dep:
                dur_h = (dt_dep - dt_arr).total_seconds() / 3600.0
                if dur_h < SANITY_JOURNEE_MIN_H:
                    if _txt(lignes_sorted[idx_dep].get("commentaire")):
                        add_event("jour_short_shift_justifie", op, jour)
                    else:
                        jc["jour_short_shift"] += 1
                        add_event("jour_short_shift", op, jour)

        # arrêt 50 : pénalisé seulement s'il reste un arrêt sans explication
        arrets_50 = [x for x in lignes_sorted if _txt(x.get("operation_code")) == "50"]
        if arrets_50:
            non_justifies = [
                x for x in arrets_50
                if not _txt(x.get("commentaire")) and x.get("id") not in arrets_justifies
            ]
            if non_justifies:
                jc["jour_arret_50"] += 1
                add_event("jour_arret_50", op, jour)

        # fins de production : métrage, Z1, scan MP
        miss_m = False
        seen_dossiers_89: set[str] = set()
        for x in lignes_sorted:
            if _txt(x.get("operation_code")) != CODE_FIN_DOS:
                continue
            mr = x.get("metrage_reel", None)
            dos = _txt(x.get("no_dossier"))
            if mr is None or (isinstance(mr, (int, float)) and float(mr) == 0.0) or str(mr).strip() == "":
                miss_m = True
                add_event("jour_missing_metrage", op, jour, dos)

            if not dos or dos in seen_dossiers_89:
                continue
            seen_dossiers_89.add(dos)
            if not ctx:
                continue

            z1_info = z1_by_dossier.get(dos) or {}
            if int(z1_info.get("count") or 0) == 0:
                dt_fin = dt_cache.get(id(x))
                if dt_fin and (now_ref - dt_fin) < delai_z1:
                    add_event("dossier_fin_z1_en_attente", op, jour, dos)
                else:
                    jc["dossier_fin_sans_z1"] += 1
                    add_event("dossier_fin_sans_z1", op, jour, dos)
            else:
                for mid in z1_info.get("mouvement_ids") or []:
                    try:
                        nb_pal = int(palettes_by_mvt_id.get(mid, 0) or 0)
                    except (TypeError, ValueError):
                        nb_pal = 0
                    if nb_pal == 0:
                        jc["z1_sans_palettes"] += 1
                        add_event("z1_sans_palettes", op, jour, dos)

            try:
                q_tr_f = float(x.get("quantite_traitee") or 0)
            except (TypeError, ValueError):
                q_tr_f = 0.0
            if q_tr_f > 0 and int(mp_scans_by_dossier.get(dos, 0) or 0) == 0:
                jc["dossier_fin_sans_mp_scan"] += 1
                add_event("dossier_fin_sans_mp_scan", op, jour, dos)
        if miss_m:
            jc["jour_missing_metrage"] += 1

        # bonus alertes validées
        if ctx:
            try:
                nb_acks = int(acks_by_op_day.get((op.strip().lower(), jour), 0) or 0)
            except (TypeError, ValueError):
                nb_acks = 0
            if nb_acks > 0:
                jc["bonus_alertes_validees"] += nb_acks

        # dossier vide : 01 → 89 sans travail entre les deux
        i = 0
        while i < len(codes):
            if codes[i] == CODE_DEBUT_DOS:
                j = i + 1
                has_work = False
                while j < len(codes) and codes[j] != CODE_FIN_DOS:
                    if codes[j] not in non_work_codes:
                        has_work = True
                    j += 1
                if j < len(codes) and not has_work:
                    jc["jour_empty_dossier"] += 1
                    dossier_no = lignes_sorted[j].get("no_dossier") or \
                                 lignes_sorted[i].get("no_dossier") or ""
                    add_event("jour_empty_dossier", op, jour, str(dossier_no))
                i = j + 1
            else:
                i += 1

        note = _clamp_score(100 + sum(PTS[k] * n for k, n in jc.items()))
        for k, n in jc.items():
            counts[k] += n

        # poids = durée de la journée (première → dernière saisie)
        dts = [dt_cache.get(id(x)) for x in lignes_sorted]
        dts = [d for d in dts if d]
        duree_min = (max(dts) - min(dts)).total_seconds() / 60.0 if len(dts) >= 2 else 0.0
        poids = min(max(duree_min, SANITY_POIDS_MIN_MIN), 16 * 60.0)
        num += note * poids
        den += poids
        nb_journees += 1

    if den <= 0:
        return {"score": 0, "mention": "Aucune saisie", "color": "warn",
                "penalites": [], "events": {}, "weighted": True, "journees": 0}

    LABELS = {
        "jour_first_last": "Journée : arrivée 1re étape / départ dernière étape",
        "jour_second_penult": "Journée : début de production 2e étape / fin de production avant-dernière",
        "jour_need_prod_cal_tech": "Journée : aucune production, calage ou intervention technique",
        "jour_short_shift": f"Journée de moins de {SANITY_JOURNEE_MIN_H:g} h sans motif",
        "jour_arret_50": "Arrêt machine (code 50) sans explication",
        "jour_missing_metrage": "Fin de production : métrage manquant",
        "jour_empty_dossier": "Dossier vide : début → fin sans saisie intermédiaire",
        "dossier_fin_sans_z1": "Fin de production sans entrée Z1",
        "z1_sans_palettes": "Entrée Z1 sans palettes déclarées",
        "dossier_fin_sans_mp_scan": "Fin de production avec quantité traitée mais aucun scan matière",
        "bonus_alertes_validees": "Alertes maintenance/qualité validées",
    }
    penalites = [
        {"type": k, "label": LABELS[k], "count": n, "pts_unitaire": PTS[k], "total": PTS[k] * n}
        for k, n in counts.items() if n > 0
    ]

    score = _clamp_score(num / den)
    mention, color = _sanity_mention_color(score)

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

    return {
        "score": score, "mention": mention, "color": color,
        "penalites": penalites, "events": events,
        "weighted": True, "journees": nb_journees,
    }


def _sanity_mention_color(score: int) -> tuple[str, str]:
    if score >= 90:
        return "Excellent", "success"
    if score >= 70:
        return "Bon", "warn"
    if score >= 50:
        return "À améliorer", "warn"
    return "Critique", "danger"


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
            SELECT id,operateur,date_operation,operation_code,operation_category,machine,no_dossier,
                   quantite_a_traiter,quantite_traitee,metrage_prevu,metrage_reel,commentaire
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
            "arrets_justifies": set(),
        }

        # Arrêts 50 expliqués après coup (feuille atelier / point de prod) :
        # l'explication vit sur le franchissement de seuil, pas sur la saisie.
        ids_50 = [int(r["id"]) for r in san_rows if str(r["operation_code"] or "") == "50"]
        if ids_50:
            try:
                ph_50 = ",".join(["?"] * len(ids_50))
                sanity_ctx["arrets_justifies"] = {
                    int(r["saisie_id"]) for r in conn.execute(
                        f"""SELECT DISTINCT saisie_id FROM arret_seuils_franchis
                            WHERE saisie_id IN ({ph_50})
                              AND COALESCE(TRIM(explication_texte),'') <> ''""",
                        ids_50,
                    ).fetchall()
                }
            except Exception:
                pass  # base sans la table des seuils : seul le commentaire compte
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

    # Plusieurs opérateurs : une carte par opérateur. Le score global reste
    # celui calculé sur l'ensemble des lignes, qui est déjà la moyenne des
    # journées de tous les opérateurs pondérée par leur durée.
    sanity_by_operateur = None
    if can_view_all_prod(user) and not repiquage_only:
        sel_ops = operateurs
        if sel_ops and len(sel_ops) > 1:
            sanity_by_operateur = {}
            for op in sel_ops:
                sub = [r for r in san_list if str(r.get("operateur") or "") == str(op)]
                sanity_by_operateur[op] = compute_sanity_score_v2(sub, sanity_ctx)

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
        "sanity_regles":       {"regles": sanity_regles(), "calcul": sanity_calcul_texte()},
    }
