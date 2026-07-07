"""
MySifa — Rapport hebdomadaire (service pur, sans routes).

Fournit :
- `iso_week_bounds(year, week)` : bornes lundi/dimanche pour une semaine ISO
- `previous_iso_week(today)`    : (year, week) de la semaine précédente
- `collect_week_data(year, week)` : dict structuré (KPI, tableaux, alertes) avec
  comparaisons S-1 vs S-2 vs moyenne(S-2..S-5)
- `render_report_html(data, role, include_email_wrapper=False)` : HTML par rôle,
  utilisable en preview (fragment CSS-vars) ou en email (styles inline).
- `ROLE_SECTIONS` : mapping rôle → sections visibles.

Toute la logique de score sanity utilise `compute_sanity_score_v2` (historique).
Toute la logique score 3-points dossier suit rentabilite.py.
"""
from __future__ import annotations

import html as html_module
import json
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from database import get_db
from services.prod_machine_filter import norm_machine_canonical
from app.routers.historique import compute_sanity_score_v2
from config import (
    APP_VERSION,
    CODE_DEBUT_DOS,
    CODE_FIN_DOS,
    ROLE_ADMINISTRATION,
    ROLE_COMMERCIAL,
    ROLE_COMPTABILITE,
    ROLE_DIRECTION,
    ROLE_EXPEDITION,
    ROLE_FABRICATION,
    ROLE_LOGISTIQUE,
    ROLE_SUPERADMIN,
)

# ─────────────────────────── constantes ───────────────────────────

# Rôles → sections affichées dans le rapport
ROLE_SECTIONS: Dict[str, List[str]] = {
    ROLE_SUPERADMIN:     ["summary", "prod_by_machine", "top_dossiers", "flop_dossiers",
                          "sanity_global", "sanity_by_operateur", "stock_freshness",
                          "stock_from_prod", "repiquage", "expes", "alerts"],
    ROLE_DIRECTION:      ["summary", "prod_by_machine", "top_dossiers", "flop_dossiers",
                          "sanity_global", "sanity_by_operateur", "stock_freshness",
                          "stock_from_prod", "repiquage", "expes", "alerts"],
    ROLE_ADMINISTRATION: ["summary", "prod_by_machine", "top_dossiers", "flop_dossiers",
                          "sanity_global", "sanity_by_operateur", "stock_freshness",
                          "stock_from_prod", "repiquage", "expes", "alerts"],
    ROLE_FABRICATION:    ["summary_light", "prod_by_machine", "top_dossiers", "flop_dossiers",
                          "sanity_global", "sanity_by_operateur", "repiquage", "alerts_fab"],
    ROLE_LOGISTIQUE:     ["summary_light", "stock_freshness", "stock_from_prod", "expes", "alerts_log"],
    ROLE_COMPTABILITE:   ["summary_light", "stock_freshness", "expes"],
    ROLE_EXPEDITION:     ["summary_light", "expes"],
    ROLE_COMMERCIAL:     ["summary_light", "expes"],
}

# Couleurs email (styles inline — pas de CSS vars)
EMAIL_COLORS: Dict[str, str] = {
    "bg":     "#0a0e17",
    "card":   "#111827",
    "border": "#1e293b",
    "text":   "#f1f5f9",
    "text2":  "#cbd5e1",
    "muted":  "#94a3b8",
    "accent": "#22d3ee",
    "accent_bg": "rgba(34,211,238,0.12)",
    "ok":     "#34d399",
    "warn":   "#fbbf24",
    "danger": "#f87171",
}


def _esc(v: Any) -> str:
    return html_module.escape("" if v is None else str(v))


def _color(name: str, email: bool) -> str:
    """Retourne soit `var(--x)` (preview), soit la valeur hex (email)."""
    if email:
        return EMAIL_COLORS.get(name, "#f1f5f9")
    # noms MySifa vers noms CSS
    alias = {"ok": "success", "text2": "text2"}
    css = alias.get(name, name)
    return f"var(--{css})"


# ─────────────────────────── dates ISO ───────────────────────────

def iso_week_bounds(year: int, week: int) -> Tuple[date, date]:
    """Retourne (lundi 00:00, dimanche 23:59:59) pour la semaine ISO donnée."""
    monday = date.fromisocalendar(year, week, 1)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def previous_iso_week(today: Optional[date] = None) -> Tuple[int, int]:
    """Retourne (year, week) de la semaine ISO précédente (celle qu'on rapporte)."""
    if today is None:
        today = date.today()
    prev = today - timedelta(days=7)
    y, w, _ = prev.isocalendar()
    return int(y), int(w)


def _week_str_bounds(year: int, week: int) -> Tuple[str, str]:
    """Retourne (wstart, wend) formatés `%Y-%m-%dT%H:%M:%S` pour comparaison lexico."""
    monday, sunday = iso_week_bounds(year, week)
    return (
        monday.strftime("%Y-%m-%dT00:00:00"),
        sunday.strftime("%Y-%m-%dT23:59:59"),
    )


def _iso_offset(year: int, week: int, offset_weeks: int) -> Tuple[int, int]:
    """Retourne (year, week) décalés de ±N semaines."""
    monday = date.fromisocalendar(year, week, 1) + timedelta(weeks=offset_weeks)
    y, w, _ = monday.isocalendar()
    return int(y), int(w)


# ─────────────────────────── helpers stats ───────────────────────────

def _delta_pct(cur: float, prev: float) -> Optional[float]:
    """Retourne l'écart en % (cur vs prev), None si prev=0."""
    if prev is None or prev == 0:
        return None
    try:
        return (float(cur) - float(prev)) / float(prev) * 100.0
    except (TypeError, ValueError):
        return None


def _fnum(v: Any, digits: int = 0) -> str:
    """Formatte un nombre : 12345.67 → '12 345,67'."""
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if digits == 0:
        s = f"{f:,.0f}"
    else:
        s = f"{f:,.{digits}f}"
    return s.replace(",", " ").replace(".", ",")


def _pct(v: Optional[float]) -> str:
    if v is None:
        return "—"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}%".replace(".", ",")


# ─────────────────────────── collecte prod / machine ───────────────────────────

def _saisies_semaine(conn, wstart: str, wend: str) -> List[Dict[str, Any]]:
    """Toutes les saisies d'une semaine."""
    rows = conn.execute(
        """SELECT id, operateur, date_operation, operation_code, operation_severity,
                  operation_category, machine, no_dossier, client, designation,
                  quantite_a_traiter, quantite_traitee, data,
                  metrage_prevu, metrage_reel, metrage_total_debut, metrage_total_fin
             FROM production_data
            WHERE date_operation >= ? AND date_operation <= ?
            ORDER BY date_operation ASC""",
        (wstart, wend),
    ).fetchall()
    return [dict(r) for r in rows]


def _heures_prod_par_machine(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Approximation V1 : pour chaque paire (op 01 → op 89) d'un même
    (opérateur, machine, no_dossier), somme le delta temps si les deux existent
    et sont < 48h d'écart. Sinon 0.

    Note: la vraie logique se trouve dans production.py:788 (delta entre saisies
    successives). Ici on approxime pour ne pas dupliquer 100 lignes de logique.
    Voir TODO dans collect_week_data.
    """
    by_key: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
    for r in rows:
        code = str(r.get("operation_code") or "")
        if code not in (CODE_DEBUT_DOS, CODE_FIN_DOS):
            continue
        m = norm_machine_canonical(r.get("machine") or "") or (r.get("machine") or "—")
        op = r.get("operateur") or "?"
        dossier = r.get("no_dossier") or ""
        by_key.setdefault((m, op, dossier), []).append(r)
    heures: Dict[str, float] = {}
    for (m, _op, _d), lignes in by_key.items():
        lignes.sort(key=lambda x: str(x.get("date_operation") or ""))
        debut = next((x for x in lignes if str(x.get("operation_code")) == CODE_DEBUT_DOS), None)
        fin = next((x for x in lignes[::-1] if str(x.get("operation_code")) == CODE_FIN_DOS), None)
        if not debut or not fin:
            continue
        try:
            d1 = datetime.strptime(str(debut["date_operation"])[:19], "%Y-%m-%dT%H:%M:%S")
            d2 = datetime.strptime(str(fin["date_operation"])[:19], "%Y-%m-%dT%H:%M:%S")
            dh = (d2 - d1).total_seconds() / 3600.0
            if 0 < dh < 48:
                heures[m] = heures.get(m, 0.0) + dh
        except (ValueError, TypeError, KeyError):
            continue
    return heures


def _metrage_par_machine(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    """Somme metrage_reel par machine (canonique)."""
    out: Dict[str, float] = {}
    for r in rows:
        code = str(r.get("operation_code") or "")
        if code != CODE_FIN_DOS:
            continue
        m = norm_machine_canonical(r.get("machine") or "") or (r.get("machine") or "—")
        try:
            v = float(r.get("metrage_reel") or 0)
            if v > 0:
                out[m] = out.get(m, 0.0) + v
        except (ValueError, TypeError):
            continue
    return out


def _dossiers_termines(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Dossiers avec op 89 dans la semaine."""
    out = []
    for r in rows:
        if str(r.get("operation_code") or "") == CODE_FIN_DOS:
            out.append(r)
    return out


def _devis_for_dossier(conn, no_dossier: str) -> Optional[Dict[str, Any]]:
    """Retourne le premier devis lié à ce no_dossier via devis_dossiers, ou None.

    Un dossier peut être lié à 0 ou 1 devis pratiquement. Un devis peut couvrir
    plusieurs dossiers ; pour scorer un dossier isolé on prend le premier match.
    """
    if not no_dossier:
        return None
    try:
        row = conn.execute(
            """SELECT d.* FROM devis d
                 JOIN devis_dossiers dd ON d.id = dd.devis_id
                WHERE dd.no_dossier = ?
                LIMIT 1""",
            (str(no_dossier).strip(),),
        ).fetchone()
    except Exception:
        return None
    if not row:
        return None
    try:
        return dict(row)
    except Exception:
        # Fallback si le driver ne supporte pas dict(row)
        return {k: row[k] for k in row.keys()} if hasattr(row, "keys") else None


def _score_devis_based(conn, no_dossier: str, devis_row: Dict[str, Any]) -> Dict[str, Any]:
    """Score 3-points aligné sur rentabilite._comparaison_from_no_dossiers.

    Calcule métrage réel + qté réelle (op 89) et temps calage/prod réels (LEAD
    sur op 02 / op 03,88) pour ce dossier précis, puis applique la logique
    3-points identique à rentabilite.py.
    """
    d = devis_row
    no_d = str(no_dossier).strip()

    # Métrage réel + quantité réelle (op 89)
    row_mq = conn.execute(
        """SELECT COALESCE(SUM(metrage_reel),0) AS met,
                  COALESCE(SUM(quantite_traitee),0) AS qte
             FROM production_data
            WHERE no_dossier = ? AND operation_code='89'""",
        (no_d,),
    ).fetchone()
    metrage_reel = float(row_mq["met"] or 0)
    qte_reel = float(row_mq["qte"] or 0)

    # Temps calage réel (op 02, LEAD)
    tps_calage_reel = float(conn.execute(
        """SELECT COALESCE(SUM(
                CASE WHEN operation_code='02'
                THEN (julianday(lead_date) - julianday(date_operation)) * 1440
                ELSE 0 END
            ), 0) AS tps
             FROM (
                SELECT date_operation, operation_code,
                       LEAD(date_operation) OVER (PARTITION BY operateur ORDER BY date_operation) AS lead_date
                  FROM production_data
                 WHERE no_dossier = ?
             ) WHERE operation_code='02'""",
        (no_d,),
    ).fetchone()["tps"] or 0)

    # Temps production réel (op 03/88, LEAD)
    tps_prod_reel = float(conn.execute(
        """SELECT COALESCE(SUM(
                CASE WHEN operation_code IN ('03','88')
                THEN (julianday(lead_date) - julianday(date_operation)) * 1440
                ELSE 0 END
            ), 0) AS tps
             FROM (
                SELECT date_operation, operation_code,
                       LEAD(date_operation) OVER (PARTITION BY operateur ORDER BY date_operation) AS lead_date
                  FROM production_data
                 WHERE no_dossier = ?
             ) WHERE operation_code IN ('03','88')""",
        (no_d,),
    ).fetchone()["tps"] or 0)

    vitesse_reel = (metrage_reel / tps_prod_reel) if tps_prod_reel > 0 else 0.0

    theo_calage = float(d.get("temps_calage_mn") or 0)
    theo_prod   = float(d.get("temps_production_mn") or 0)
    theo_metrage = float(d.get("metrage_production_ml") or 0)
    theo_qte    = float(d.get("qte_etiquettes") or 0)
    theo_vit    = float(d.get("vitesse_theorique") or 0)

    # Logique 3-points — copie exacte rentabilite.py lignes 128-143
    score = 0
    if vitesse_reel > (theo_vit or 0):
        score += 1
    if tps_calage_reel < (theo_calage or 999):
        score += 1
    if qte_reel >= (theo_qte or 0):
        score += 1

    label = {3: "Excellent", 2: "Bon", 1: "Mitigé", 0: "À améliorer"}[score]
    color = {3: "success", 2: "success", 1: "warn", 0: "danger"}[score]

    return {
        "score": score,
        "label": label,
        "color": color,
        "vitesse_reel": vitesse_reel,
        "vitesse_theo": theo_vit,
        "metrage_reel": metrage_reel,
        "metrage_prevu": theo_metrage,
        "tps_calage_reel_mn": tps_calage_reel,
        "tps_calage_theo_mn": theo_calage,
        "tps_prod_reel_mn": tps_prod_reel,
        "tps_prod_theo_mn": theo_prod,
        "qte_reel": qte_reel,
        "qte_prevu": theo_qte,
        "duree_reel_h": tps_prod_reel / 60.0,
        "duree_prevu_h": theo_prod / 60.0,
        "has_devis": True,
    }


def _score_3pts_dossier(r_debut: Dict[str, Any], r_fin: Dict[str, Any],
                        duree_h: float) -> Tuple[int, Dict[str, Any]]:
    """
    Fallback planning-based (quand aucun devis n'est lié au dossier).

    Score 3 points, aligné labels sur rentabilite.py :
     - +1 si vitesse réelle > vitesse théorique
     - +1 si quantité traitée ≥ théorique
     - 3e point (calage) non calculé sans devis → skippé
    Labels : Excellent / Bon / Mitigé / À améliorer (comme rentabilite.py).
    """
    metrage_reel = float(r_fin.get("metrage_reel") or 0)
    metrage_prevu = float(r_fin.get("metrage_prevu") or r_debut.get("metrage_prevu") or 0)
    qte_prevu = float(r_debut.get("quantite_a_traiter") or r_fin.get("quantite_a_traiter") or 0)
    qte_reel = float(r_fin.get("quantite_traitee") or 0)
    duree_prevu_h = float(r_debut.get("data") and json.loads(r_debut.get("data") or "{}").get("duree_prevu_h") or 0) if isinstance(r_debut.get("data"), str) else 0

    # Approximation vitesse (m/min)
    reel_v = (metrage_reel / (duree_h * 60.0)) if (metrage_reel and duree_h and duree_h > 0) else 0
    theo_v = (metrage_prevu / (duree_prevu_h * 60.0)) if (metrage_prevu and duree_prevu_h and duree_prevu_h > 0) else 0

    score = 0
    if reel_v and theo_v and reel_v > theo_v:
        score += 1
    if qte_reel and qte_prevu and qte_reel >= qte_prevu:
        score += 1
    # 3e point (calage) non calculé sans devis

    label = {3: "Excellent", 2: "Bon", 1: "Mitigé", 0: "À améliorer"}[score]
    color = {3: "success", 2: "success", 1: "warn", 0: "danger"}[score]
    return score, {
        "vitesse_reel": reel_v,
        "vitesse_theo": theo_v,
        "metrage_reel": metrage_reel,
        "metrage_prevu": metrage_prevu,
        "duree_reel_h": duree_h,
        "duree_prevu_h": duree_prevu_h,
        "qte_reel": qte_reel,
        "qte_prevu": qte_prevu,
        "tps_calage_reel_mn": 0.0,
        "tps_calage_theo_mn": 0.0,
        "tps_prod_reel_mn": duree_h * 60.0,
        "tps_prod_theo_mn": duree_prevu_h * 60.0,
        "label": label,
        "color": color,
        "has_devis": False,
    }


def _dossiers_scores(conn, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Pour chaque dossier ayant op 01 + op 89 dans la semaine, calcule le score.
    Priorité : si un devis est lié (devis_dossiers), on utilise le score
    devis-based (parité exacte avec rentabilite.py). Sinon fallback planning.
    Retourne liste triée par score DESC (top) — l'appelant reverse pour flop.
    """
    by_dossier: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for r in rows:
        dossier = r.get("no_dossier") or ""
        if not dossier:
            continue
        code = str(r.get("operation_code") or "")
        d = by_dossier.setdefault(dossier, {"debut": [], "fin": [], "all": []})
        d["all"].append(r)
        if code == CODE_DEBUT_DOS:
            d["debut"].append(r)
        elif code == CODE_FIN_DOS:
            d["fin"].append(r)

    scored = []
    for dossier, d in by_dossier.items():
        if not d["debut"] or not d["fin"]:
            continue
        r_debut = sorted(d["debut"], key=lambda x: str(x.get("date_operation") or ""))[0]
        r_fin = sorted(d["fin"], key=lambda x: str(x.get("date_operation") or ""))[-1]
        try:
            d1 = datetime.strptime(str(r_debut["date_operation"])[:19], "%Y-%m-%dT%H:%M:%S")
            d2 = datetime.strptime(str(r_fin["date_operation"])[:19], "%Y-%m-%dT%H:%M:%S")
            duree_h = max((d2 - d1).total_seconds() / 3600.0, 0.0)
        except (ValueError, TypeError, KeyError):
            duree_h = 0.0

        devis = _devis_for_dossier(conn, dossier)
        if devis:
            det = _score_devis_based(conn, dossier, devis)
            score = det["score"]
        else:
            score, det = _score_3pts_dossier(r_debut, r_fin, duree_h)

        scored.append({
            "no_dossier": dossier,
            "client": r_fin.get("client") or r_debut.get("client") or "",
            "machine": norm_machine_canonical(r_fin.get("machine") or "") or (r_fin.get("machine") or ""),
            "score": score,
            **det,
        })
    scored.sort(key=lambda x: (x["score"], x["metrage_reel"]), reverse=True)
    return scored


# ─────────────────────────── agrégation par semaine ───────────────────────────

def _kpis_semaine(conn, year: int, week: int) -> Dict[str, Any]:
    """Retourne les KPI bruts d'une semaine ISO donnée."""
    wstart, wend = _week_str_bounds(year, week)
    rows = _saisies_semaine(conn, wstart, wend)

    # Heures prod (approximation via paires 01/89)
    heures_par_m = _heures_prod_par_machine(rows)
    heures_prod = sum(heures_par_m.values())

    # Métrage total (somme metrage_reel sur op 89)
    m_par_m = _metrage_par_machine(rows)
    metrage_total = sum(m_par_m.values())

    # Dossiers terminés (nb op 89 distinct dossier)
    doss_termines = set()
    for r in rows:
        if str(r.get("operation_code") or "") == CODE_FIN_DOS:
            d = r.get("no_dossier")
            if d:
                doss_termines.add(d)

    # Expés
    expes_count = conn.execute(
        """SELECT COUNT(*) FROM expe_departs
            WHERE date_enlevement >= ? AND date_enlevement <= ?""",
        (wstart[:10], wend[:10]),
    ).fetchone()[0]

    # Mouvements stock
    mouv_mp = conn.execute(
        """SELECT COUNT(*) FROM mp_mouvements
            WHERE created_at >= ? AND created_at <= ?""",
        (wstart, wend),
    ).fetchone()[0]
    mouv_pf = conn.execute(
        """SELECT COUNT(*) FROM pf_mouvements
            WHERE date_mouvement >= ? AND date_mouvement <= ?""",
        (wstart, wend),
    ).fetchone()[0]

    return {
        "heures_prod": heures_prod,
        "metrage_total": metrage_total,
        "dossiers_termines": len(doss_termines),
        "expes": int(expes_count or 0),
        "mouv_mp": int(mouv_mp or 0),
        "mouv_pf": int(mouv_pf or 0),
    }


def _avg4(vals: List[float]) -> float:
    valid = [v for v in vals if v is not None]
    if not valid:
        return 0.0
    return sum(valid) / len(valid)


# ─────────────────────────── collecte principale ───────────────────────────

def collect_week_data(year: int, week: int) -> Dict[str, Any]:
    """Collecte toute la data + comparaisons S-2 et moyenne 4 semaines."""
    wstart, wend = _week_str_bounds(year, week)
    monday, sunday = iso_week_bounds(year, week)

    with get_db() as conn:
        # ────── KPI courants
        cur_kpis = _kpis_semaine(conn, year, week)

        # ────── KPI S-2 (la semaine précédant celle rapportée)
        y2, w2 = _iso_offset(year, week, -1)
        prev_kpis = _kpis_semaine(conn, y2, w2)

        # ────── Moyenne des 4 semaines avant S-1 (S-2, S-3, S-4, S-5)
        avg4_data: Dict[str, List[float]] = {k: [] for k in cur_kpis.keys()}
        for offset in range(-1, -5, -1):
            yo, wo = _iso_offset(year, week, offset)
            k = _kpis_semaine(conn, yo, wo)
            for kk, vv in k.items():
                avg4_data[kk].append(float(vv or 0))
        avg4_kpis = {k: _avg4(v) for k, v in avg4_data.items()}

        # ────── Saisies détaillées de la semaine courante
        rows = _saisies_semaine(conn, wstart, wend)
        rows_no_repi = [r for r in rows
                        if norm_machine_canonical(r.get("machine") or "") != "Repiquage"]

        # ────── Prod par machine
        heures_par_m = _heures_prod_par_machine(rows_no_repi)
        m_par_m = _metrage_par_machine(rows_no_repi)
        # dossiers distincts par machine (op 89)
        doss_par_m: Dict[str, set] = {}
        for r in rows_no_repi:
            if str(r.get("operation_code") or "") == CODE_FIN_DOS:
                m = norm_machine_canonical(r.get("machine") or "") or (r.get("machine") or "—")
                doss_par_m.setdefault(m, set()).add(r.get("no_dossier") or "")
        # sanity par machine
        sanity_par_m: Dict[str, Dict[str, Any]] = {}
        by_m: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows_no_repi:
            m = norm_machine_canonical(r.get("machine") or "") or (r.get("machine") or "—")
            by_m.setdefault(m, []).append(r)
        for m, sub in by_m.items():
            sanity_par_m[m] = compute_sanity_score_v2(sub)

        machines_present = sorted(set(list(heures_par_m.keys())
                                      + list(m_par_m.keys())
                                      + list(doss_par_m.keys())
                                      + list(sanity_par_m.keys())))
        prod_by_machine = []
        for m in machines_present:
            h = heures_par_m.get(m, 0.0)
            met = m_par_m.get(m, 0.0)
            vit = (met / h) if h > 0 else 0.0
            prod_by_machine.append({
                "machine": m,
                "heures": h,
                "metrage": met,
                "vitesse_moy": vit,
                "dossiers": len(doss_par_m.get(m, set())),
                "sanity_score": sanity_par_m.get(m, {}).get("score", 0),
                "sanity_mention": sanity_par_m.get(m, {}).get("mention", ""),
                "sanity_color": sanity_par_m.get(m, {}).get("color", "muted"),
            })

        # ────── Top / flop dossiers (score 3-pts)
        scored = _dossiers_scores(conn, rows_no_repi)
        top_dossiers = scored[:5]
        flop_dossiers = sorted(scored, key=lambda x: (x["score"], -x["metrage_reel"]))[:5]

        # ────── Sanity global (hors Repiquage)
        sanity_global = compute_sanity_score_v2(rows_no_repi)

        # ────── Sanity par opérateur (hors Repiquage)
        by_op: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows_no_repi:
            op = r.get("operateur") or "?"
            by_op.setdefault(op, []).append(r)
        sanity_by_operateur = []
        for op, sub in by_op.items():
            s = compute_sanity_score_v2(sub)
            # activité en h = approximé par paires 01/89 dessus
            h = sum(_heures_prod_par_machine(sub).values())
            sanity_by_operateur.append({
                "operateur": op,
                "score": s.get("score", 0),
                "mention": s.get("mention", ""),
                "color": s.get("color", "muted"),
                "activite_h": h,
            })
        sanity_by_operateur.sort(key=lambda x: x["score"], reverse=True)

        # ────── Stock — mouvements par catégorie
        mp_by_cat_rows = conn.execute(
            """SELECT mp.categorie AS categorie, m.type_mouvement AS t, COUNT(*) AS n
                 FROM mp_mouvements m
                 JOIN matieres_premieres mp ON mp.id = m.matiere_id
                WHERE m.created_at >= ? AND m.created_at <= ?
                GROUP BY mp.categorie, m.type_mouvement""",
            (wstart, wend),
        ).fetchall()
        mp_agg: Dict[str, Dict[str, int]] = {}
        for r in mp_by_cat_rows:
            c = r["categorie"] or "?"
            t = r["t"] or ""
            mp_agg.setdefault(c, {"entrees": 0, "sorties": 0})
            if t == "entree":
                mp_agg[c]["entrees"] += int(r["n"] or 0)
            elif t == "sortie":
                mp_agg[c]["sorties"] += int(r["n"] or 0)
        mp_by_categorie = [{"categorie": k, **v} for k, v in mp_agg.items()]

        pf_entrees = conn.execute(
            """SELECT COUNT(*) FROM pf_mouvements
                WHERE type='entree' AND date_mouvement >= ? AND date_mouvement <= ?""",
            (wstart, wend),
        ).fetchone()[0]
        pf_sorties = conn.execute(
            """SELECT COUNT(*) FROM pf_mouvements
                WHERE type='sortie' AND date_mouvement >= ? AND date_mouvement <= ?""",
            (wstart, wend),
        ).fetchone()[0]

        # ────── Refs stagnantes (>30 jours sans mouvement)
        refs_stagnantes_rows = conn.execute(
            """SELECT reference, designation, MAX(date_mouvement) AS last
                 FROM pf_mouvements
                GROUP BY reference
               HAVING (julianday('now') - julianday(last)) > 30
                ORDER BY last ASC
                LIMIT 10"""
        ).fetchall()
        refs_stagnantes = []
        now = datetime.now()
        for r in refs_stagnantes_rows:
            last = r["last"]
            try:
                dt = datetime.strptime(str(last)[:19], "%Y-%m-%dT%H:%M:%S")
                jours = (now - dt).days
            except (ValueError, TypeError):
                jours = 0
            refs_stagnantes.append({
                "reference": r["reference"],
                "designation": r["designation"],
                "dernier_mouv": last,
                "jours_sans_mouv": jours,
            })

        # ────── Dossiers op 89 sans stock (entrée pf dans 48h)
        op89_dossiers = []
        for r in rows:
            if str(r.get("operation_code") or "") == CODE_FIN_DOS:
                d = r.get("no_dossier")
                if d:
                    op89_dossiers.append({
                        "no_dossier": d,
                        "date_fin": r.get("date_operation"),
                        "client": r.get("client") or "",
                    })
        op89_sans_stock = []
        for d in op89_dossiers:
            try:
                fin_dt = datetime.strptime(str(d["date_fin"])[:19], "%Y-%m-%dT%H:%M:%S")
                fin_p48 = (fin_dt + timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%S")
            except (ValueError, TypeError):
                continue
            row = conn.execute(
                """SELECT COUNT(*) FROM pf_mouvements
                    WHERE type='entree' AND no_of = ?
                      AND date_mouvement >= ? AND date_mouvement <= ?""",
                (d["no_dossier"], d["date_fin"], fin_p48),
            ).fetchone()
            if int(row[0] or 0) == 0:
                op89_sans_stock.append(d)

        stock_from_prod = {
            "dossiers_op89_semaine": len(op89_dossiers),
            "dossiers_op89_sans_stock": op89_sans_stock[:20],
        }

        # ────── Repiquage
        rows_repi = [r for r in rows
                     if norm_machine_canonical(r.get("machine") or "") == "Repiquage"]
        cartons_total = 0
        doss_repi = set()
        ops_repi = set()
        for r in rows_repi:
            # cartons dans data JSON si présent
            data_raw = r.get("data")
            data_obj = {}
            if isinstance(data_raw, str) and data_raw:
                try:
                    data_obj = json.loads(data_raw)
                except (ValueError, TypeError):
                    data_obj = {}
            elif isinstance(data_raw, dict):
                data_obj = data_raw
            try:
                cartons_total += int(float(data_obj.get("nb_cartons") or 0))
            except (TypeError, ValueError):
                pass
            if r.get("no_dossier"):
                doss_repi.add(r["no_dossier"])
            if r.get("operateur"):
                ops_repi.add(r["operateur"])
        repiquage = {
            "cartons_total": cartons_total,
            "dossiers_traites": len(doss_repi),
            "saisies_count": len(rows_repi),
            "operateurs_actifs": sorted(ops_repi),
        }

        # ────── Expes
        expes_rows = conn.execute(
            """SELECT id, date_enlevement, transporteur, client, ref_sifa,
                      nb_palette, poids_total_kg, date_livraison, statut
                 FROM expe_departs
                WHERE date_enlevement >= ? AND date_enlevement <= ?""",
            (wstart[:10], wend[:10]),
        ).fetchall()
        expes_list = [dict(r) for r in expes_rows]
        by_transp: Dict[str, Dict[str, float]] = {}
        palettes_total = 0.0
        poids_total = 0.0
        for e in expes_list:
            t = e.get("transporteur") or "—"
            by_transp.setdefault(t, {"count": 0, "palettes": 0.0, "poids": 0.0})
            by_transp[t]["count"] += 1
            try:
                p = float(e.get("nb_palette") or 0)
                by_transp[t]["palettes"] += p
                palettes_total += p
            except (TypeError, ValueError):
                pass
            try:
                pk = float(e.get("poids_total_kg") or 0)
                by_transp[t]["poids"] += pk
                poids_total += pk
            except (TypeError, ValueError):
                pass
        by_transporteur = [
            {"transporteur": t, "count": int(v["count"]), "palettes": v["palettes"], "poids": v["poids"]}
            for t, v in sorted(by_transp.items(), key=lambda x: -x[1]["count"])
        ]

        # Retards : date_livraison passée, statut pas livré
        today_iso = date.today().isoformat()
        retards = []
        for e in expes_list:
            dl = e.get("date_livraison")
            statut = (e.get("statut") or "").lower()
            if dl and dl < today_iso and statut not in ("livre", "livré", "termine", "terminé", "clos"):
                retards.append({
                    "ref_sifa": e.get("ref_sifa") or "",
                    "transporteur": e.get("transporteur") or "",
                    "date_enlevement": e.get("date_enlevement"),
                    "date_livraison_prevue": dl,
                    "statut": e.get("statut"),
                })

        expes = {
            "count": len(expes_list),
            "palettes_total": palettes_total,
            "poids_total_kg": poids_total,
            "by_transporteur": by_transporteur,
            "retards": retards[:20],
        }

        # ────── Alertes
        # Trous de saisie : op 01 sans op 89 depuis > 5 jours
        cutoff = (date.today() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S")
        rows_all_recent = conn.execute(
            """SELECT no_dossier, operateur, machine, date_operation, operation_code, client
                 FROM production_data
                WHERE date_operation >= ?
                ORDER BY date_operation ASC""",
            ((date.today() - timedelta(days=45)).strftime("%Y-%m-%dT%H:%M:%S"),),
        ).fetchall()
        by_dossier_all: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows_all_recent:
            d = r["no_dossier"]
            if not d:
                continue
            by_dossier_all.setdefault(d, []).append(dict(r))
        trous_saisie = []
        for dossier, lst in by_dossier_all.items():
            has_01 = any(str(x.get("operation_code") or "") == CODE_DEBUT_DOS for x in lst)
            has_89 = any(str(x.get("operation_code") or "") == CODE_FIN_DOS for x in lst)
            if has_01 and not has_89:
                r01 = sorted(
                    [x for x in lst if str(x.get("operation_code") or "") == CODE_DEBUT_DOS],
                    key=lambda x: str(x.get("date_operation") or "")
                )[0]
                if str(r01.get("date_operation") or "") <= cutoff:
                    try:
                        d1 = datetime.strptime(str(r01["date_operation"])[:19], "%Y-%m-%dT%H:%M:%S")
                        jours = (datetime.now() - d1).days
                    except (ValueError, TypeError):
                        jours = 0
                    trous_saisie.append({
                        "no_dossier": dossier,
                        "client": r01.get("client") or "",
                        "machine": norm_machine_canonical(r01.get("machine") or "") or (r01.get("machine") or ""),
                        "date_op01": r01.get("date_operation"),
                        "jours_ecoules": jours,
                    })
        trous_saisie.sort(key=lambda x: -x["jours_ecoules"])
        trous_saisie = trous_saisie[:20]

        # Dépassements : dossiers terminés cette semaine avec écart > 30%
        depassements = []
        for d in scored:
            dp = d.get("duree_prevu_h") or 0
            dr = d.get("duree_reel_h") or 0
            if dp > 0 and dr > 0:
                ecart = (dr - dp) / dp * 100.0
                if ecart > 30:
                    depassements.append({
                        "no_dossier": d["no_dossier"],
                        "duree_reel": dr,
                        "duree_prevu": dp,
                        "ecart_pct": ecart,
                    })
        depassements.sort(key=lambda x: -x["ecart_pct"])
        depassements = depassements[:20]

        alerts = {
            "trous_saisie": trous_saisie,
            "depassements": depassements,
        }

    # ────── Summary agrégé avec deltas
    def _kpi_block(key: str) -> Dict[str, Any]:
        return {
            "cur": float(cur_kpis.get(key) or 0),
            "prev": float(prev_kpis.get(key) or 0),
            "avg4": float(avg4_kpis.get(key) or 0),
        }

    summary = {
        "heures_prod":       _kpi_block("heures_prod"),
        "metrage_total":     _kpi_block("metrage_total"),
        "dossiers_termines": _kpi_block("dossiers_termines"),
        "expes":             _kpi_block("expes"),
        "mouv_mp":           _kpi_block("mouv_mp"),
        "mouv_pf":           _kpi_block("mouv_pf"),
    }

    return {
        "week": {
            "year": year, "num": week,
            "start": monday.isoformat(), "end": sunday.isoformat(),
            "label": f"Semaine {week} ({year})",
        },
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": summary,
        "prod_by_machine": prod_by_machine,
        "top_dossiers": top_dossiers,
        "flop_dossiers": flop_dossiers,
        "sanity_global": {
            "score": sanity_global.get("score", 0),
            "mention": sanity_global.get("mention", ""),
            "color": sanity_global.get("color", "muted"),
        },
        "sanity_by_operateur": sanity_by_operateur,
        "stock_freshness": {
            "mouv_mp_count": int(cur_kpis["mouv_mp"]),
            "mouv_pf_count": int(cur_kpis["mouv_pf"]),
            "mp_by_categorie": mp_by_categorie,
            "pf_entrees": int(pf_entrees or 0),
            "pf_sorties": int(pf_sorties or 0),
            "refs_stagnantes": refs_stagnantes,
        },
        "stock_from_prod": stock_from_prod,
        "repiquage": repiquage,
        "expes": expes,
        "alerts": alerts,
    }


# ─────────────────────────── rendu HTML ───────────────────────────

def _render_delta(cur: float, prev: float, avg4: float, email: bool,
                  is_int: bool = True, unit: str = "") -> str:
    """Rend deux petits deltas côte à côte : vs S-2 et vs moy 4s."""
    def _one(cur_v: float, ref: float, label: str) -> str:
        d = _delta_pct(cur_v, ref)
        if d is None:
            arrow = "·"
            color = _color("muted", email)
            txt = f"{label} : —"
        elif d > 0.5:
            arrow = "↑"
            color = _color("ok", email)
            txt = f"{label} : {arrow} {_pct(d)}"
        elif d < -0.5:
            arrow = "↓"
            color = _color("danger", email)
            txt = f"{label} : {arrow} {_pct(d)}"
        else:
            arrow = "·"
            color = _color("muted", email)
            txt = f"{label} : {arrow} stable"
        return f'<span style="color:{color};font-size:11px;font-weight:600;margin-right:12px">{_esc(txt)}</span>'
    return _one(cur, prev, "vs S-2") + _one(cur, avg4, "vs moy 4s")


def _kpi_card(title: str, block: Dict[str, float], email: bool,
              digits: int = 0, unit: str = "") -> str:
    cur = block.get("cur", 0)
    val_txt = f"{_fnum(cur, digits)}{(' ' + unit) if unit else ''}"
    card_bg = _color("card", email)
    border = _color("border", email)
    text = _color("text", email)
    muted = _color("muted", email)
    return (
        f'<div style="background:{card_bg};border:1px solid {border};'
        f'border-radius:12px;padding:16px 20px;flex:1;min-width:180px;margin:6px">'
        f'<div style="text-transform:uppercase;letter-spacing:.5px;font-size:11px;'
        f'color:{muted};font-weight:600">{_esc(title)}</div>'
        f'<div style="font-size:28px;font-weight:700;color:{text};margin:6px 0 8px">{_esc(val_txt)}</div>'
        f'<div>{_render_delta(cur, block.get("prev", 0), block.get("avg4", 0), email)}</div>'
        f'</div>'
    )


def _section_title(txt: str, email: bool) -> str:
    muted = _color("muted", email)
    return (
        f'<div style="text-transform:uppercase;letter-spacing:.5px;font-size:12px;'
        f'color:{muted};font-weight:700;margin:22px 0 10px">{_esc(txt)}</div>'
    )


def _card_wrap(inner: str, email: bool) -> str:
    card = _color("card", email)
    border = _color("border", email)
    return (
        f'<div style="background:{card};border:1px solid {border};'
        f'border-radius:12px;padding:16px 20px;margin-bottom:16px">{inner}</div>'
    )


def _sanity_pill(mention: str, color: str, email: bool) -> str:
    palette = {
        "success": _color("ok", email),
        "ok":      _color("ok", email),
        "warn":    _color("warn", email),
        "danger":  _color("danger", email),
    }
    bg = palette.get(color, _color("muted", email))
    return (
        f'<span style="background:{bg};color:#0a0e17;font-size:11px;font-weight:700;'
        f'padding:3px 10px;border-radius:999px;letter-spacing:.3px">{_esc(mention)}</span>'
    )


def _render_summary(data: Dict[str, Any], email: bool, light: bool = False) -> str:
    s = data.get("summary", {})
    parts = []
    parts.append(_kpi_card("Heures prod", s.get("heures_prod", {}), email, digits=1, unit="h"))
    parts.append(_kpi_card("Métrage total", s.get("metrage_total", {}), email, digits=0, unit="m"))
    parts.append(_kpi_card("Dossiers terminés", s.get("dossiers_termines", {}), email))
    if not light:
        parts.append(_kpi_card("Expéditions", s.get("expes", {}), email))
        parts.append(_kpi_card("Mouvements MP", s.get("mouv_mp", {}), email))
        parts.append(_kpi_card("Mouvements PF", s.get("mouv_pf", {}), email))
    row = f'<div style="display:flex;flex-wrap:wrap;margin:-6px">{"".join(parts)}</div>'
    return _section_title("Résumé de la semaine", email) + row


def _render_prod_by_machine(data: Dict[str, Any], email: bool) -> str:
    rows_data = data.get("prod_by_machine", [])
    if not rows_data:
        return ""
    text = _color("text", email)
    muted = _color("muted", email)
    border = _color("border", email)
    thead = (
        f'<tr style="text-align:left">'
        f'<th style="padding:8px 10px;font-size:11px;text-transform:uppercase;color:{muted};border-bottom:1px solid {border}">Machine</th>'
        f'<th style="padding:8px 10px;font-size:11px;text-transform:uppercase;color:{muted};border-bottom:1px solid {border}">Heures</th>'
        f'<th style="padding:8px 10px;font-size:11px;text-transform:uppercase;color:{muted};border-bottom:1px solid {border}">Métrage</th>'
        f'<th style="padding:8px 10px;font-size:11px;text-transform:uppercase;color:{muted};border-bottom:1px solid {border}">Vitesse moy</th>'
        f'<th style="padding:8px 10px;font-size:11px;text-transform:uppercase;color:{muted};border-bottom:1px solid {border}">Dossiers</th>'
        f'<th style="padding:8px 10px;font-size:11px;text-transform:uppercase;color:{muted};border-bottom:1px solid {border}">Sanity</th>'
        f'</tr>'
    )
    body = ""
    for r in rows_data:
        pill = _sanity_pill(f"{r.get('sanity_score', 0)} — {r.get('sanity_mention', '')}",
                            r.get("sanity_color", "muted"), email)
        body += (
            f'<tr>'
            f'<td style="padding:8px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_esc(r["machine"])}</td>'
            f'<td style="padding:8px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_fnum(r["heures"], 1)} h</td>'
            f'<td style="padding:8px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_fnum(r["metrage"], 0)} m</td>'
            f'<td style="padding:8px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_fnum(r["vitesse_moy"], 1)} m/h</td>'
            f'<td style="padding:8px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{r["dossiers"]}</td>'
            f'<td style="padding:8px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{pill}</td>'
            f'</tr>'
        )
    table = f'<table style="width:100%;border-collapse:collapse">{thead}{body}</table>'
    return _section_title("Production par machine", email) + _card_wrap(table, email)


def _render_dossiers_table(rows_data: List[Dict[str, Any]], title: str, email: bool) -> str:
    if not rows_data:
        return ""
    text = _color("text", email)
    muted = _color("muted", email)
    border = _color("border", email)
    thead = (
        f'<tr style="text-align:left">'
        f'<th style="padding:8px 10px;font-size:11px;text-transform:uppercase;color:{muted};border-bottom:1px solid {border}">Dossier</th>'
        f'<th style="padding:8px 10px;font-size:11px;text-transform:uppercase;color:{muted};border-bottom:1px solid {border}">Client</th>'
        f'<th style="padding:8px 10px;font-size:11px;text-transform:uppercase;color:{muted};border-bottom:1px solid {border}">Métrage</th>'
        f'<th style="padding:8px 10px;font-size:11px;text-transform:uppercase;color:{muted};border-bottom:1px solid {border}">Durée</th>'
        f'<th style="padding:8px 10px;font-size:11px;text-transform:uppercase;color:{muted};border-bottom:1px solid {border}">Score</th>'
        f'</tr>'
    )
    body = ""
    for r in rows_data:
        pill = _sanity_pill(f"{r['score']}/3 — {r['label']}", r["color"], email)
        # Petit indicateur textuel quand le score est calculé sans devis (fallback planning)
        if r.get("has_devis") is False:
            pill += f' <span style="color:{muted};font-size:10px">(sans devis)</span>'
        body += (
            f'<tr>'
            f'<td style="padding:8px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}"><b>{_esc(r["no_dossier"])}</b></td>'
            f'<td style="padding:8px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_esc(r["client"])}</td>'
            f'<td style="padding:8px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_fnum(r["metrage_reel"], 0)} m / {_fnum(r["metrage_prevu"], 0)} m</td>'
            f'<td style="padding:8px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_fnum(r["duree_reel_h"], 1)} h / {_fnum(r["duree_prevu_h"], 1)} h</td>'
            f'<td style="padding:8px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{pill}</td>'
            f'</tr>'
        )
    table = f'<table style="width:100%;border-collapse:collapse">{thead}{body}</table>'
    return _section_title(title, email) + _card_wrap(table, email)


def _render_sanity_global(data: Dict[str, Any], email: bool) -> str:
    sg = data.get("sanity_global", {})
    text = _color("text", email)
    inner = (
        f'<div style="display:flex;align-items:center;gap:20px">'
        f'<div style="font-size:36px;font-weight:800;color:{text}">{sg.get("score", 0)}<span style="font-size:16px;color:{_color("muted", email)}">/100</span></div>'
        f'<div>{_sanity_pill(sg.get("mention", ""), sg.get("color", "muted"), email)}</div>'
        f'</div>'
    )
    return _section_title("Sanity score global", email) + _card_wrap(inner, email)


def _render_sanity_operateurs(data: Dict[str, Any], email: bool) -> str:
    ops = data.get("sanity_by_operateur", [])
    if not ops:
        return ""
    text = _color("text", email)
    muted = _color("muted", email)
    border = _color("border", email)
    thead = (
        f'<tr style="text-align:left">'
        f'<th style="padding:8px 10px;font-size:11px;text-transform:uppercase;color:{muted};border-bottom:1px solid {border}">Opérateur</th>'
        f'<th style="padding:8px 10px;font-size:11px;text-transform:uppercase;color:{muted};border-bottom:1px solid {border}">Score</th>'
        f'<th style="padding:8px 10px;font-size:11px;text-transform:uppercase;color:{muted};border-bottom:1px solid {border}">Mention</th>'
        f'<th style="padding:8px 10px;font-size:11px;text-transform:uppercase;color:{muted};border-bottom:1px solid {border}">Activité</th>'
        f'</tr>'
    )
    body = ""
    for o in ops:
        body += (
            f'<tr>'
            f'<td style="padding:8px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_esc(o["operateur"])}</td>'
            f'<td style="padding:8px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}"><b>{o["score"]}</b>/100</td>'
            f'<td style="padding:8px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_sanity_pill(o["mention"], o["color"], email)}</td>'
            f'<td style="padding:8px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_fnum(o["activite_h"], 1)} h</td>'
            f'</tr>'
        )
    return _section_title("Sanity score par opérateur", email) + _card_wrap(
        f'<table style="width:100%;border-collapse:collapse">{thead}{body}</table>', email
    )


def _render_stock_freshness(data: Dict[str, Any], email: bool) -> str:
    sf = data.get("stock_freshness", {})
    text = _color("text", email)
    muted = _color("muted", email)
    border = _color("border", email)
    # Mouvements MP par catégorie
    mp_html = ""
    for m in sf.get("mp_by_categorie", []):
        mp_html += (
            f'<tr>'
            f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_esc(m["categorie"])}</td>'
            f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{m["entrees"]}</td>'
            f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{m["sorties"]}</td>'
            f'</tr>'
        )
    mp_table = ""
    if mp_html:
        mp_table = (
            f'<div style="font-size:12px;color:{muted};text-transform:uppercase;font-weight:600;margin-bottom:6px">Mouvements MP par catégorie</div>'
            f'<table style="width:100%;border-collapse:collapse">'
            f'<tr><th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Catégorie</th>'
            f'<th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Entrées</th>'
            f'<th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Sorties</th></tr>'
            f'{mp_html}</table>'
        )
    pf_line = (
        f'<div style="font-size:13px;color:{text};margin:12px 0">'
        f'PF : <b>{sf.get("pf_entrees", 0)}</b> entrées · <b>{sf.get("pf_sorties", 0)}</b> sorties'
        f'</div>'
    )
    # Refs stagnantes
    stag_html = ""
    for r in sf.get("refs_stagnantes", []):
        stag_html += (
            f'<tr>'
            f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}"><b>{_esc(r["reference"])}</b></td>'
            f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_esc(r.get("designation", "") or "")}</td>'
            f'<td style="padding:6px 10px;font-size:13px;color:{_color("warn", email)};border-bottom:1px solid {border}"><b>{r["jours_sans_mouv"]} j</b></td>'
            f'</tr>'
        )
    stag_table = ""
    if stag_html:
        stag_table = (
            f'<div style="font-size:12px;color:{muted};text-transform:uppercase;font-weight:600;margin:12px 0 6px">Refs sans mouvement (>30 j)</div>'
            f'<table style="width:100%;border-collapse:collapse">'
            f'<tr><th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Référence</th>'
            f'<th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Désignation</th>'
            f'<th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Ancienneté</th></tr>'
            f'{stag_html}</table>'
        )
    return _section_title("Fraîcheur des stocks", email) + _card_wrap(mp_table + pf_line + stag_table, email)


def _render_stock_from_prod(data: Dict[str, Any], email: bool) -> str:
    sp = data.get("stock_from_prod", {})
    text = _color("text", email)
    muted = _color("muted", email)
    border = _color("border", email)
    intro = (
        f'<div style="font-size:13px;color:{text};margin-bottom:10px">'
        f'{sp.get("dossiers_op89_semaine", 0)} dossiers terminés · '
        f'<b style="color:{_color("warn", email)}">{len(sp.get("dossiers_op89_sans_stock", []))}</b> sans entrée stock dans les 48 h'
        f'</div>'
    )
    lst = ""
    for d in sp.get("dossiers_op89_sans_stock", []):
        lst += (
            f'<tr>'
            f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}"><b>{_esc(d["no_dossier"])}</b></td>'
            f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_esc(d.get("client", ""))}</td>'
            f'<td style="padding:6px 10px;font-size:13px;color:{muted};border-bottom:1px solid {border}">{_esc(d.get("date_fin", ""))}</td>'
            f'</tr>'
        )
    tab = ""
    if lst:
        tab = (
            f'<table style="width:100%;border-collapse:collapse">'
            f'<tr><th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Dossier</th>'
            f'<th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Client</th>'
            f'<th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Fin de production</th></tr>'
            f'{lst}</table>'
        )
    return _section_title("Cohérence prod → stock", email) + _card_wrap(intro + tab, email)


def _render_repiquage(data: Dict[str, Any], email: bool) -> str:
    r = data.get("repiquage", {})
    text = _color("text", email)
    muted = _color("muted", email)
    inner = (
        f'<div style="display:flex;flex-wrap:wrap;gap:20px">'
        f'<div><div style="font-size:11px;color:{muted};text-transform:uppercase">Cartons</div>'
        f'<div style="font-size:22px;color:{text};font-weight:700">{r.get("cartons_total", 0)}</div></div>'
        f'<div><div style="font-size:11px;color:{muted};text-transform:uppercase">Dossiers</div>'
        f'<div style="font-size:22px;color:{text};font-weight:700">{r.get("dossiers_traites", 0)}</div></div>'
        f'<div><div style="font-size:11px;color:{muted};text-transform:uppercase">Saisies</div>'
        f'<div style="font-size:22px;color:{text};font-weight:700">{r.get("saisies_count", 0)}</div></div>'
        f'<div><div style="font-size:11px;color:{muted};text-transform:uppercase">Opérateurs actifs</div>'
        f'<div style="font-size:13px;color:{text};margin-top:4px">{_esc(", ".join(r.get("operateurs_actifs", [])) or "—")}</div></div>'
        f'</div>'
    )
    return _section_title("Repiquage", email) + _card_wrap(inner, email)


def _render_expes(data: Dict[str, Any], email: bool) -> str:
    ex = data.get("expes", {})
    text = _color("text", email)
    muted = _color("muted", email)
    border = _color("border", email)
    kpis = (
        f'<div style="display:flex;flex-wrap:wrap;gap:20px;margin-bottom:12px">'
        f'<div><div style="font-size:11px;color:{muted};text-transform:uppercase">Départs</div>'
        f'<div style="font-size:22px;color:{text};font-weight:700">{ex.get("count", 0)}</div></div>'
        f'<div><div style="font-size:11px;color:{muted};text-transform:uppercase">Palettes</div>'
        f'<div style="font-size:22px;color:{text};font-weight:700">{_fnum(ex.get("palettes_total", 0), 0)}</div></div>'
        f'<div><div style="font-size:11px;color:{muted};text-transform:uppercase">Poids</div>'
        f'<div style="font-size:22px;color:{text};font-weight:700">{_fnum(ex.get("poids_total_kg", 0), 0)} kg</div></div>'
        f'</div>'
    )
    transp_html = ""
    for t in ex.get("by_transporteur", []):
        transp_html += (
            f'<tr>'
            f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_esc(t["transporteur"])}</td>'
            f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{t["count"]}</td>'
            f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_fnum(t["palettes"], 0)}</td>'
            f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_fnum(t["poids"], 0)} kg</td>'
            f'</tr>'
        )
    transp_tab = ""
    if transp_html:
        transp_tab = (
            f'<div style="font-size:12px;color:{muted};text-transform:uppercase;font-weight:600;margin-bottom:6px">Par transporteur</div>'
            f'<table style="width:100%;border-collapse:collapse">'
            f'<tr><th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Transporteur</th>'
            f'<th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Départs</th>'
            f'<th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Palettes</th>'
            f'<th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Poids</th></tr>'
            f'{transp_html}</table>'
        )
    # Retards
    retards_html = ""
    for r in ex.get("retards", []):
        retards_html += (
            f'<tr>'
            f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}"><b>{_esc(r["ref_sifa"])}</b></td>'
            f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_esc(r["transporteur"])}</td>'
            f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_esc(r["date_enlevement"] or "")}</td>'
            f'<td style="padding:6px 10px;font-size:13px;color:{_color("warn", email)};border-bottom:1px solid {border}">{_esc(r["date_livraison_prevue"] or "")}</td>'
            f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_esc(r["statut"] or "")}</td>'
            f'</tr>'
        )
    retards_tab = ""
    if retards_html:
        retards_tab = (
            f'<div style="font-size:12px;color:{muted};text-transform:uppercase;font-weight:600;margin:12px 0 6px">Retards de livraison</div>'
            f'<table style="width:100%;border-collapse:collapse">'
            f'<tr><th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Réf SIFA</th>'
            f'<th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Transporteur</th>'
            f'<th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Enlèvement</th>'
            f'<th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Livraison prévue</th>'
            f'<th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Statut</th></tr>'
            f'{retards_html}</table>'
        )
    return _section_title("Expéditions", email) + _card_wrap(kpis + transp_tab + retards_tab, email)


def _render_alerts(data: Dict[str, Any], email: bool, scope: str = "all") -> str:
    """scope='all'|'fab'|'log' → filtre le contenu."""
    a = data.get("alerts", {})
    text = _color("text", email)
    muted = _color("muted", email)
    border = _color("border", email)
    parts = []
    if scope in ("all", "fab"):
        trous = a.get("trous_saisie", [])
        if trous:
            body = ""
            for t in trous:
                body += (
                    f'<tr>'
                    f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}"><b>{_esc(t["no_dossier"])}</b></td>'
                    f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_esc(t.get("client", ""))}</td>'
                    f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_esc(t.get("machine", ""))}</td>'
                    f'<td style="padding:6px 10px;font-size:13px;color:{_color("warn", email)};border-bottom:1px solid {border}"><b>{t.get("jours_ecoules", 0)} j</b></td>'
                    f'</tr>'
                )
            parts.append(
                f'<div style="font-size:12px;color:{muted};text-transform:uppercase;font-weight:600;margin-bottom:6px">'
                f'Trous de saisie (op 01 sans op 89, > 5 j)</div>'
                f'<table style="width:100%;border-collapse:collapse">'
                f'<tr><th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Dossier</th>'
                f'<th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Client</th>'
                f'<th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Machine</th>'
                f'<th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Ancienneté</th></tr>'
                f'{body}</table>'
            )
    if scope in ("all", "fab"):
        dep = a.get("depassements", [])
        if dep:
            body = ""
            for d in dep:
                body += (
                    f'<tr>'
                    f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}"><b>{_esc(d["no_dossier"])}</b></td>'
                    f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_fnum(d["duree_reel"], 1)} h</td>'
                    f'<td style="padding:6px 10px;font-size:13px;color:{text};border-bottom:1px solid {border}">{_fnum(d["duree_prevu"], 1)} h</td>'
                    f'<td style="padding:6px 10px;font-size:13px;color:{_color("danger", email)};border-bottom:1px solid {border}"><b>{_pct(d["ecart_pct"])}</b></td>'
                    f'</tr>'
                )
            parts.append(
                f'<div style="font-size:12px;color:{muted};text-transform:uppercase;font-weight:600;margin:12px 0 6px">'
                f'Dépassements de durée (> 30 %)</div>'
                f'<table style="width:100%;border-collapse:collapse">'
                f'<tr><th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Dossier</th>'
                f'<th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Durée réelle</th>'
                f'<th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Durée prévue</th>'
                f'<th style="padding:6px 10px;text-align:left;font-size:11px;color:{muted};border-bottom:1px solid {border}">Écart</th></tr>'
                f'{body}</table>'
            )
    if not parts:
        return ""
    return _section_title("Alertes", email) + _card_wrap("".join(parts), email)


# ─────────────────────────── rendu global ───────────────────────────

def render_report_html(data: Dict[str, Any], role: str,
                       include_email_wrapper: bool = False) -> str:
    """
    Rend le HTML complet du rapport pour un rôle donné.
    - include_email_wrapper=True : doc HTML autonome avec couleurs hard-codées
    - False : fragment CSS-vars destiné à /reports/weekly
    """
    email = include_email_wrapper
    sections = ROLE_SECTIONS.get(role, ROLE_SECTIONS[ROLE_DIRECTION])

    # dispatch
    def _render_section(sec: str) -> str:
        if sec == "summary":
            return _render_summary(data, email, light=False)
        if sec == "summary_light":
            return _render_summary(data, email, light=True)
        if sec == "prod_by_machine":
            return _render_prod_by_machine(data, email)
        if sec == "top_dossiers":
            return _render_dossiers_table(data.get("top_dossiers", []), "Top dossiers de la semaine", email)
        if sec == "flop_dossiers":
            return _render_dossiers_table(data.get("flop_dossiers", []), "Dossiers à améliorer", email)
        if sec == "sanity_global":
            return _render_sanity_global(data, email)
        if sec == "sanity_by_operateur":
            return _render_sanity_operateurs(data, email)
        if sec == "stock_freshness":
            return _render_stock_freshness(data, email)
        if sec == "stock_from_prod":
            return _render_stock_from_prod(data, email)
        if sec == "repiquage":
            return _render_repiquage(data, email)
        if sec == "expes":
            return _render_expes(data, email)
        if sec == "alerts":
            return _render_alerts(data, email, scope="all")
        if sec == "alerts_fab":
            return _render_alerts(data, email, scope="fab")
        if sec == "alerts_log":
            return _render_alerts(data, email, scope="log")
        return ""

    body_parts = [_render_section(s) for s in sections]
    body_html = "".join(p for p in body_parts if p)

    label = data.get("week", {}).get("label", "")
    generated = data.get("generated_at", "")

    if not email:
        # Fragment CSS-vars
        return (
            f'<div style="font-family:\'Segoe UI\',system-ui,sans-serif;color:var(--text)">'
            f'<div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">'
            f'Rapport hebdomadaire — rôle {_esc(role)}</div>'
            f'<div style="font-size:22px;font-weight:700;color:var(--text);margin-bottom:2px">{_esc(label)}</div>'
            f'<div style="font-size:12px;color:var(--muted);margin-bottom:20px">Généré le {_esc(generated)}</div>'
            f'{body_html}'
            f'</div>'
        )

    # Email HTML complet
    bg = EMAIL_COLORS["bg"]
    text = EMAIL_COLORS["text"]
    muted = EMAIL_COLORS["muted"]
    accent = EMAIL_COLORS["accent"]
    return (
        f'<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>Rapport hebdomadaire — {_esc(label)}</title></head>'
        f'<body style="margin:0;padding:0;background:{bg};font-family:\'Segoe UI\',system-ui,sans-serif;color:{text}">'
        f'<div style="max-width:840px;margin:0 auto;padding:24px 20px">'
        f'<div style="border-bottom:1px solid {EMAIL_COLORS["border"]};padding-bottom:16px;margin-bottom:20px">'
        f'<div style="font-size:11px;color:{muted};text-transform:uppercase;letter-spacing:.5px">Rapport hebdomadaire — rôle {_esc(role)}</div>'
        f'<h1 style="font-size:24px;color:{text};margin:6px 0 4px">{_esc(label)}</h1>'
        f'<div style="font-size:12px;color:{muted}">Généré le {_esc(generated)}</div>'
        f'</div>'
        f'{body_html}'
        f'<div style="border-top:1px solid {EMAIL_COLORS["border"]};margin-top:26px;padding-top:14px;font-size:11px;color:{muted};text-align:center">'
        f'MySifa · Rapport automatique du mercredi matin · v{_esc(APP_VERSION)}'
        f'</div>'
        f'</div></body></html>'
    )
