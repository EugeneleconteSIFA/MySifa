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
import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from database import get_db
from services.prod_machine_filter import norm_machine_canonical
from app.routers.historique import compute_sanity_score_v2
from config import (
    APP_VERSION,
    BASE_DIR,
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

# Codes 'arret' du referentiel operations.json — utilises pour calculer le
# temps d'arret par dossier via LEAD SQL. Chargement au niveau module,
# fallback minimal si le fichier manque.
try:
    with open(os.path.join(BASE_DIR, "operations.json"), encoding="utf-8") as _fop:
        _OPS_JSON = json.load(_fop)
    ARRET_CODES: List[str] = sorted(
        code for code, info in _OPS_JSON.items()
        if isinstance(info, dict) and (info.get("category") or "").lower() == "arret"
    )
except Exception:
    ARRET_CODES = ["50"]  # fallback minimal si le fichier manque

# ─────────────────────────── constantes ───────────────────────────

# Rôles → sections affichées dans le rapport
ROLE_SECTIONS: Dict[str, List[str]] = {
    # Note : les sections top_dossiers / flop_dossiers ont été retirées de toutes les vues
    # (retour utilisateur : trop de deep dive dossier par dossier dans le rapport hebdo).
    # Les données restent collectées dans data["top_dossiers"] / data["flop_dossiers"]
    # au cas où on veuille les réactiver plus tard.
    ROLE_SUPERADMIN:     ["summary", "prod_by_machine",
                          "sanity_global", "sanity_by_operateur", "stock_freshness",
                          "stock_from_prod", "repiquage", "expes", "alerts"],
    ROLE_DIRECTION:      ["summary", "prod_by_machine",
                          "sanity_global", "sanity_by_operateur", "stock_freshness",
                          "stock_from_prod", "repiquage", "expes", "alerts"],
    ROLE_ADMINISTRATION: ["summary", "prod_by_machine",
                          "sanity_global", "sanity_by_operateur", "stock_freshness",
                          "stock_from_prod", "repiquage", "expes", "alerts"],
    ROLE_FABRICATION:    ["summary_light", "prod_by_machine", "dossiers_fab_detail",
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


def _prod_par_machine_dossier_by_dossier(
    conn, rows: List[Dict[str, Any]], wstart: str, wend: str,
) -> Dict[str, Dict[str, Any]]:
    """
    Agrégation prod par machine, dossier par dossier.

    Pour chaque no_dossier ayant une op 89 dans la semaine [wstart, wend] :
      - metrage_dossier = metrage_reel de la ligne op 89
      - duree_dossier_mn = temps de production réel via LEAD (op 03/88),
        même logique que rentabilite.py lignes 67-82
      - machine = norm_machine_canonical(machine) de la ligne op 89

    Résultat par machine (dossiers valides : metrage>0 ET duree>0) :
      metrage       = Σ metrage_dossier
      duree_h       = Σ duree_dossier_mn / 60
      vitesse_m_h   = metrage / duree_h  (0 si duree_h = 0)
      dossiers      = nb dossiers valides
      detail_dossiers = liste [{no_dossier, metrage, duree_h}, ...]
    """
    # IMPORTANT — encodage historique de `metrage_reel` sur op 89 :
    # En pratique, à chaque fin de session (op 89) l'opérateur relève le COMPTEUR
    # MACHINE brut (ex: 91 994 681 m sur Cohésio 2), pas un delta consommé.
    # Un dossier long avec plusieurs pauses génère donc plusieurs op 89 avec des
    # valeurs de compteur croissantes. Sommer ces valeurs (comme le fait
    # rentabilite.py legacy) donne des chiffres absurdes (100 M m/semaine).
    #
    # Vrai métrage produit sur le dossier = MAX(m_reel op 89) - MIN(m_reel op 89)
    # = delta compteur cumulé sur toutes les sessions. Manque uniquement la
    # production entre le vrai démarrage (op 01, où m_reel = NULL) et la 1re op 89
    # observée — négligeable en pratique (quelques minutes).
    by_dossier: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        if str(r.get("operation_code") or "") != CODE_FIN_DOS:
            continue
        no_d = r.get("no_dossier") or ""
        if not no_d:
            continue
        try:
            m_val = float(r.get("metrage_reel") or 0)
        except (TypeError, ValueError):
            m_val = 0.0
        m_machine = norm_machine_canonical(r.get("machine") or "") or (r.get("machine") or "—")
        entry = by_dossier.setdefault(no_d, {
            "m_values": [], "machine": m_machine, "date_fin": None,
        })
        if m_val > 0:
            entry["m_values"].append(m_val)
        d_op = str(r.get("date_operation") or "")
        if not entry.get("date_fin") or d_op > entry["date_fin"]:
            entry["date_fin"] = d_op
            entry["machine"] = m_machine

    # Seuil au-dessus duquel une valeur unique de m_reel est présumée être un
    # compteur brut (typiquement millions/dizaines de millions) plutôt qu'un
    # vrai delta produit sur un seul dossier.
    _COMPTEUR_THRESHOLD = 1_000_000.0

    result: Dict[str, Dict[str, Any]] = {}
    for no_d, entry in by_dossier.items():
        m_vals = entry.get("m_values") or []
        if len(m_vals) >= 2:
            # Delta compteur = vrai métrage produit sur toutes les sessions.
            metrage = max(m_vals) - min(m_vals)
        elif len(m_vals) == 1:
            val = m_vals[0]
            # 1 seule op 89 : pas de delta possible. On accepte la valeur telle
            # quelle si elle ressemble à un vrai métrage produit (< seuil),
            # sinon on l'exclut (compteur brut).
            metrage = val if val < _COMPTEUR_THRESHOLD else 0.0
        else:
            metrage = 0.0
        try:
            row = conn.execute(
                """SELECT COALESCE(SUM(
                        CASE WHEN operation_code IN ('03','88')
                        THEN (julianday(lead_date) - julianday(date_operation)) * 1440
                        ELSE 0 END
                    ), 0) AS tps_mn
                     FROM (
                        SELECT date_operation, operation_code,
                               LEAD(date_operation) OVER (PARTITION BY operateur ORDER BY date_operation) AS lead_date
                          FROM production_data
                         WHERE no_dossier = ?
                     ) WHERE operation_code IN ('03','88')""",
                (no_d,),
            ).fetchone()
            duree_mn = float(row["tps_mn"] or 0) if row else 0.0
        except Exception:
            duree_mn = 0.0

        if metrage <= 0 or duree_mn <= 0:
            continue

        machine = entry.get("machine") or "—"
        agg = result.setdefault(machine, {
            "metrage": 0.0, "duree_h": 0.0, "vitesse_m_h": 0.0,
            "dossiers": 0, "detail_dossiers": [],
        })
        agg["metrage"] += metrage
        agg["duree_h"] += duree_mn / 60.0
        agg["dossiers"] += 1
        agg["detail_dossiers"].append({
            "no_dossier": no_d,
            "metrage": metrage,
            "duree_h": duree_mn / 60.0,
        })

    for m, agg in result.items():
        agg["vitesse_m_h"] = (agg["metrage"] / agg["duree_h"]) if agg["duree_h"] > 0 else 0.0

    return result


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

def _dossiers_fab_detail(conn, wstart: str, wend: str) -> List[Dict[str, Any]]:
    """Detail par dossier pour la vue Fabrication.

    Pour chaque no_dossier ayant au moins une op 89 dans [wstart, wend], calcule :
      - metrage (delta compteur MAX-MIN sur op 89, ou valeur unique si < seuil)
      - vitesse_m_min = metrage / tps_prod_mn
      - tps_calage_mn (LEAD sur op 02)
      - tps_prod_mn (LEAD sur op 03/88)
      - tps_arret_mn (LEAD sur toutes les op categorie 'arret')
      - nb_palettes_z1 = SUM(mouvement_palettes.nombre) pour les entrees Z1 du dossier

    Exclut Repiquage (pas de vitesse/metrage pertinent).
    Trie par metrage decroissant. Retour vide si rien.
    """
    _COMPTEUR_THRESHOLD = 1_000_000.0

    # Etape 1 : dossiers avec op 89 dans la semaine + agregation m_reel + machine
    rows89 = conn.execute(
        """SELECT no_dossier, machine, client, metrage_reel, date_operation
             FROM production_data
            WHERE operation_code = ?
              AND date_operation >= ? AND date_operation <= ?""",
        (CODE_FIN_DOS, wstart, wend),
    ).fetchall()

    by_dossier: Dict[str, Dict[str, Any]] = {}
    for r in rows89:
        no_d = r["no_dossier"] or ""
        if not no_d:
            continue
        try:
            m_val = float(r["metrage_reel"] or 0)
        except (TypeError, ValueError):
            m_val = 0.0
        m_machine = norm_machine_canonical(r["machine"] or "") or (r["machine"] or "—")
        entry = by_dossier.setdefault(no_d, {
            "m_values": [],
            "machine": m_machine,
            "client": r["client"] or "",
            "date_fin": None,
        })
        if m_val > 0:
            entry["m_values"].append(m_val)
        d_op = str(r["date_operation"] or "")
        if not entry.get("date_fin") or d_op > entry["date_fin"]:
            entry["date_fin"] = d_op
            entry["machine"] = m_machine
            if r["client"]:
                entry["client"] = r["client"]

    if not by_dossier:
        return []

    # Placeholders pour la clause IN sur les codes d'arret
    arret_placeholders = ",".join("?" * len(ARRET_CODES)) if ARRET_CODES else "''"

    out: List[Dict[str, Any]] = []
    for no_d, entry in by_dossier.items():
        machine = entry.get("machine") or "—"
        # Exclusion Repiquage
        if machine == "Repiquage":
            continue

        m_vals = entry.get("m_values") or []
        if len(m_vals) >= 2:
            metrage = max(m_vals) - min(m_vals)
        elif len(m_vals) == 1:
            val = m_vals[0]
            metrage = val if val < _COMPTEUR_THRESHOLD else 0.0
        else:
            metrage = 0.0

        # Temps calage (LEAD sur op 02)
        try:
            tps_calage = float(conn.execute(
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
        except Exception:
            tps_calage = 0.0

        # Temps production (LEAD sur op 03/88)
        try:
            tps_prod = float(conn.execute(
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
        except Exception:
            tps_prod = 0.0

        # Temps arret (LEAD sur toutes les op categorie 'arret')
        tps_arret = 0.0
        if ARRET_CODES:
            try:
                sql_arret = (
                    f"""SELECT COALESCE(SUM(
                            CASE WHEN operation_code IN ({arret_placeholders})
                            THEN (julianday(lead_date) - julianday(date_operation)) * 1440
                            ELSE 0 END
                        ), 0) AS tps
                         FROM (
                            SELECT date_operation, operation_code,
                                   LEAD(date_operation) OVER (PARTITION BY operateur ORDER BY date_operation) AS lead_date
                              FROM production_data
                             WHERE no_dossier = ?
                         ) WHERE operation_code IN ({arret_placeholders})"""
                )
                tps_arret = float(conn.execute(
                    sql_arret,
                    (*ARRET_CODES, no_d, *ARRET_CODES),
                ).fetchone()["tps"] or 0)
            except Exception:
                tps_arret = 0.0

        # Nombre de palettes entrees en Z1 pour ce dossier (cumule, non filtre semaine)
        try:
            nb_pal = int(conn.execute(
                """SELECT COALESCE(SUM(mp.nombre), 0) AS nb
                     FROM mouvement_palettes mp
                     JOIN mouvements_stock ms ON mp.mouvement_id = ms.id
                    WHERE ms.no_dossier = ?
                      AND UPPER(COALESCE(ms.emplacement,'')) = 'Z1'
                      AND ms.type_mouvement = 'entree'""",
                (no_d,),
            ).fetchone()["nb"] or 0)
        except Exception:
            nb_pal = 0

        vitesse = (metrage / tps_prod) if (metrage > 0 and tps_prod > 0) else 0.0

        out.append({
            "no_dossier": no_d,
            "client": entry.get("client") or "",
            "machine": machine,
            "metrage": float(metrage),
            "vitesse_m_min": float(vitesse),
            "tps_calage_mn": float(tps_calage),
            "tps_prod_mn": float(tps_prod),
            "tps_arret_mn": float(tps_arret),
            "nb_palettes_z1": int(nb_pal),
        })

    out.sort(key=lambda x: -x["metrage"])
    return out


def _kpis_semaine(conn, year: int, week: int) -> Dict[str, Any]:
    """Retourne les KPI bruts d'une semaine ISO donnée.

    Cohérence : heures_prod et metrage_total proviennent de la même
    agrégation dossier-par-dossier utilisée pour la vue "par machine",
    afin que la somme des machines égale les KPI globaux.
    """
    wstart, wend = _week_str_bounds(year, week)
    rows = _saisies_semaine(conn, wstart, wend)

    # Agrégation dossier-par-dossier (base commune KPI + prod par machine)
    prod_par_m = _prod_par_machine_dossier_by_dossier(conn, rows, wstart, wend)
    heures_prod = sum(a["duree_h"] for a in prod_par_m.values())
    metrage_total = sum(a["metrage"] for a in prod_par_m.values())

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

        # ────── Prod par machine (agrégation dossier-par-dossier)
        prod_par_m = _prod_par_machine_dossier_by_dossier(conn, rows_no_repi, wstart, wend)
        sanity_par_m: Dict[str, Dict[str, Any]] = {}
        by_m: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows_no_repi:
            m = norm_machine_canonical(r.get("machine") or "") or (r.get("machine") or "—")
            by_m.setdefault(m, []).append(r)
        for m, sub in by_m.items():
            sanity_par_m[m] = compute_sanity_score_v2(sub)

        machines_present = sorted(set(list(prod_par_m.keys()) + list(sanity_par_m.keys())))
        prod_by_machine = []
        for m in machines_present:
            agg = prod_par_m.get(m, {})
            prod_by_machine.append({
                "machine": m,
                "heures": float(agg.get("duree_h", 0.0)),
                "metrage": float(agg.get("metrage", 0.0)),
                "vitesse_moy": float(agg.get("vitesse_m_h", 0.0)),
                "dossiers": int(agg.get("dossiers", 0)),
                "detail_dossiers": agg.get("detail_dossiers", []),
                "sanity_score": sanity_par_m.get(m, {}).get("score", 0),
                "sanity_mention": sanity_par_m.get(m, {}).get("mention", ""),
                "sanity_color": sanity_par_m.get(m, {}).get("color", "muted"),
            })

        # ────── Detail par dossier (vue Fabrication)
        dossiers_fab_detail = _dossiers_fab_detail(conn, wstart, wend)

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
            # activité en h = somme des durées des dossiers valides (op 89)
            # travaillés par cet opérateur, agrégation dossier-par-dossier.
            _h_agg = _prod_par_machine_dossier_by_dossier(conn, sub, wstart, wend)
            h = sum(a["duree_h"] for a in _h_agg.values())
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
        "dossiers_fab_detail": dossiers_fab_detail,
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
    """Grille de mini-cards, une par machine — pas de tableau."""
    if not rows_data:
        return ""
    text = _color("text", email)
    muted = _color("muted", email)
    border = _color("border", email)
    card_bg = _color("card", email)

    cards = []
    for r in rows_data:
        heures = float(r.get("heures", 0) or 0)
        metrage = float(r.get("metrage", 0) or 0)
        vitesse = float(r.get("vitesse_moy", 0) or 0)
        dossiers = int(r.get("dossiers", 0) or 0)

        heures_txt = f'{_fnum(heures, 1)} h' if heures > 0 else "—"
        metrage_txt = f'{_fnum(metrage, 0)} m' if metrage > 0 else "—"
        # `vitesse` est stocké en m/h (metrage / duree_h) — on convertit en m/min pour l'affichage.
        vitesse_min = vitesse / 60.0 if vitesse > 0 else 0.0
        vitesse_txt = f'{_fnum(vitesse_min, 0)} m/min' if vitesse_min > 0 else "—"

        pill = _sanity_pill(r.get("sanity_mention", "") or "—",
                            r.get("sanity_color", "muted"), email)

        cards.append(
            f'<div style="flex:1 1 220px;background:{card_bg};'
            f'border:1px solid {border};border-radius:10px;padding:14px;min-width:200px">'
            f'<div style="font-size:16px;font-weight:700;color:{text};margin-bottom:12px">'
            f'{_esc(r["machine"])}</div>'
            f'<div style="display:flex;justify-content:space-between;gap:8px;margin-bottom:10px">'
            f'<div style="text-align:left"><div style="font-size:10px;color:{muted};'
            f'text-transform:uppercase;letter-spacing:.3px;font-weight:600">Heures</div>'
            f'<div style="font-size:15px;color:{text};font-weight:700;margin-top:2px">{heures_txt}</div></div>'
            f'<div style="text-align:center"><div style="font-size:10px;color:{muted};'
            f'text-transform:uppercase;letter-spacing:.3px;font-weight:600">Métrage</div>'
            f'<div style="font-size:15px;color:{text};font-weight:700;margin-top:2px">{metrage_txt}</div></div>'
            f'<div style="text-align:right"><div style="font-size:10px;color:{muted};'
            f'text-transform:uppercase;letter-spacing:.3px;font-weight:600">Vitesse</div>'
            f'<div style="font-size:15px;color:{text};font-weight:700;margin-top:2px">{vitesse_txt}</div></div>'
            f'</div>'
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding-top:10px;border-top:1px solid {border}">'
            f'<div style="font-size:11px;color:{muted}">{dossiers} dossier{"s" if dossiers > 1 else ""}</div>'
            f'<div>{pill}</div>'
            f'</div>'
            f'</div>'
        )

    grid = f'<div style="display:flex;flex-wrap:wrap;gap:12px">{"".join(cards)}</div>'
    return _section_title("Production par machine", email) + grid


def _render_dossiers_fab_detail(rows_data: List[Dict[str, Any]], email: bool) -> str:
    """Detail par dossier — vue Fabrication uniquement.

    Une carte par dossier avec 5 metriques : vitesse, calage, production, arret,
    palettes Z1. Trie par metrage decroissant en amont.
    """
    if not rows_data:
        return ""
    text = _color("text", email)
    muted = _color("muted", email)
    warn = _color("warn", email)
    border = _color("border", email)
    card_bg = _color("card", email)

    def _fmt_prod(mn: float) -> str:
        if mn <= 0:
            return "—"
        if mn >= 60:
            h = int(mn // 60)
            m = int(round(mn - h * 60))
            return f"{h}h {m:02d}min"
        return f"{_fnum(mn, 0)} min"

    def _metric(label: str, value_html: str, color: str = None) -> str:
        col = color or text
        return (
            f'<div style="flex:1;min-width:100px">'
            f'<div style="font-size:10px;color:{muted};text-transform:uppercase;'
            f'letter-spacing:.3px;font-weight:600">{_esc(label)}</div>'
            f'<div style="font-size:14px;color:{col};font-weight:700;margin-top:2px">{value_html}</div>'
            f'</div>'
        )

    cards: List[str] = []
    for r in rows_data:
        no_d = r.get("no_dossier") or "—"
        client = r.get("client") or ""
        machine = r.get("machine") or "—"
        vitesse = float(r.get("vitesse_m_min", 0) or 0)
        tps_calage = float(r.get("tps_calage_mn", 0) or 0)
        tps_prod = float(r.get("tps_prod_mn", 0) or 0)
        tps_arret = float(r.get("tps_arret_mn", 0) or 0)
        nb_pal = int(r.get("nb_palettes_z1", 0) or 0)

        vitesse_txt = f"{_fnum(vitesse, 1)} m/min" if vitesse > 0 else "—"
        calage_txt = f"{_fnum(tps_calage, 0)} min" if tps_calage > 0 else "—"
        prod_txt = _fmt_prod(tps_prod)
        arret_txt = f"{_fnum(tps_arret, 0)} min" if tps_arret > 0 else "—"
        arret_color = warn if tps_arret > 0 else text
        pal_txt = _esc(str(nb_pal))

        client_html = (
            f'<span style="color:{muted};font-weight:400"> · {_esc(client)}</span>' if client else ""
        )

        cards.append(
            f'<div style="border:1px solid {border};border-radius:10px;padding:12px 14px;'
            f'margin-bottom:8px;background:{card_bg}">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">'
            f'<div style="font-size:14px;font-weight:700;color:{text}">'
            f'{_esc(no_d)}{client_html}</div>'
            f'<div style="font-size:11px;color:{muted}">{_esc(machine)}</div>'
            f'</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:16px">'
            f'{_metric("Vitesse", vitesse_txt)}'
            f'{_metric("Calage", calage_txt)}'
            f'{_metric("Production", prod_txt)}'
            f'{_metric("Arret", arret_txt, color=arret_color)}'
            f'{_metric("Palettes Z1", pal_txt)}'
            f'</div>'
            f'</div>'
        )

    body = "".join(cards)
    return _section_title("Detail par dossier", email) + _card_wrap(body, email)


def _render_dossiers_table(rows_data: List[Dict[str, Any]], title: str, email: bool) -> str:
    """Liste compacte, une ligne par dossier. Pas de tableau. Max 5 lignes."""
    if not rows_data:
        return ""
    text = _color("text", email)
    muted = _color("muted", email)
    border = _color("border", email)

    items = []
    for r in rows_data[:5]:
        pill = _sanity_pill(f"{r['score']}/3 — {r['label']}", r["color"], email)
        metrage_reel = _fnum(r.get("metrage_reel", 0), 0)
        metrage_prevu = _fnum(r.get("metrage_prevu", 0), 0)
        duree_reel = _fnum(r.get("duree_reel_h", 0), 1)
        duree_prevu = _fnum(r.get("duree_prevu_h", 0), 1)
        no_devis_txt = ""
        if r.get("has_devis") is False:
            no_devis_txt = f' <span style="color:{muted};font-size:10px">(sans devis)</span>'
        items.append(
            f'<div style="display:flex;align-items:center;gap:10px;padding:10px 0;'
            f'border-bottom:1px solid {border}">'
            f'<div style="flex:1;min-width:0">'
            f'<div style="font-size:13px;font-weight:700;color:{text}">'
            f'{_esc(r["no_dossier"])} · <span style="font-weight:400;color:{muted}">'
            f'{_esc(r.get("client", "") or "—")}</span></div>'
            f'<div style="font-size:11px;color:{muted};margin-top:2px">'
            f'{metrage_reel} m / {metrage_prevu} m · {duree_reel} h / {duree_prevu} h'
            f'</div>'
            f'</div>'
            f'<div style="white-space:nowrap">{pill}{no_devis_txt}</div>'
            f'</div>'
        )
    body = "".join(items)
    return _section_title(title, email) + _card_wrap(body, email)


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
    """Grille de chips opérateur — pas de tableau, score numérique masqué."""
    ops = data.get("sanity_by_operateur", [])
    if not ops:
        return ""
    text = _color("text", email)
    muted = _color("muted", email)
    border = _color("border", email)

    ops_sorted = sorted(ops, key=lambda o: -float(o.get("activite_h", 0) or 0))

    chips = []
    for o in ops_sorted:
        h = float(o.get("activite_h", 0) or 0)
        h_txt = f'{_fnum(h, 1)} h' if h > 0 else "—"
        pill = _sanity_pill(o.get("mention", "") or "—", o.get("color", "muted"), email)
        chips.append(
            f'<div style="padding:8px 12px;border:1px solid {border};border-radius:10px;'
            f'display:flex;align-items:center;gap:8px">'
            f'<div style="font-size:13px;font-weight:600;color:{text}">{_esc(o["operateur"])}</div>'
            f'<div style="font-size:11px;color:{muted}">{h_txt}</div>'
            f'<div>{pill}</div>'
            f'</div>'
        )
    grid = f'<div style="display:flex;flex-wrap:wrap;gap:8px">{"".join(chips)}</div>'
    return _section_title("Sanity par opérateur", email) + _card_wrap(grid, email)


def _render_stock_freshness(data: Dict[str, Any], email: bool) -> str:
    """4 mini-KPIs (entrées/sorties MP + PF) + liste compacte des refs stagnantes."""
    sf = data.get("stock_freshness", {})
    text = _color("text", email)
    muted = _color("muted", email)
    border = _color("border", email)
    card_bg = _color("card", email)
    warn = _color("warn", email)

    mp_entrees = 0
    mp_sorties = 0
    for c in sf.get("mp_by_categorie", []) or []:
        mp_entrees += int(c.get("entrees", 0) or 0)
        mp_sorties += int(c.get("sorties", 0) or 0)
    pf_entrees = int(sf.get("pf_entrees", 0) or 0)
    pf_sorties = int(sf.get("pf_sorties", 0) or 0)

    def _mini_kpi(label: str, value: int) -> str:
        return (
            f'<div style="flex:1 1 130px;padding:12px 14px;background:{card_bg};'
            f'border:1px solid {border};border-radius:10px;text-align:center">'
            f'<div style="font-size:22px;font-weight:700;color:{text}">{value}</div>'
            f'<div style="font-size:11px;color:{muted};text-transform:uppercase;'
            f'letter-spacing:.3px;font-weight:600;margin-top:2px">{_esc(label)}</div>'
            f'</div>'
        )

    kpis_html = (
        f'<div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:14px">'
        f'{_mini_kpi("Entrées MP", mp_entrees)}'
        f'{_mini_kpi("Sorties MP", mp_sorties)}'
        f'{_mini_kpi("Entrées PF", pf_entrees)}'
        f'{_mini_kpi("Sorties PF", pf_sorties)}'
        f'</div>'
    )

    refs = sf.get("refs_stagnantes", []) or []
    stag_html = ""
    if refs:
        items = []
        for r in refs[:8]:
            items.append(
                f'<div style="padding:6px 0;border-bottom:1px solid {border};'
                f'font-size:13px;color:{text}">'
                f'<b>{_esc(r["reference"])}</b> — '
                f'<span style="color:{muted}">{_esc(r.get("designation", "") or "")}</span> · '
                f'<span style="color:{warn};font-weight:600">{r.get("jours_sans_mouv", 0)} j</span>'
                f'</div>'
            )
        stag_html = (
            f'<div style="margin-top:6px">'
            f'<div style="font-size:11px;color:{muted};text-transform:uppercase;'
            f'font-weight:600;letter-spacing:.3px;margin-bottom:4px">'
            f'Références sans mouvement (&gt;30 j)</div>'
            f'{"".join(items)}'
            f'</div>'
        )

    return _section_title("Fraîcheur des stocks", email) + _card_wrap(kpis_html + stag_html, email)


def _render_stock_from_prod(data: Dict[str, Any], email: bool) -> str:
    """Cohérence prod → stock — section visible et actionnable.

    Ligne principale + alerte warn si des dossiers terminés n'ont pas d'entrée
    stock dans les 48 h après la fin. Message de succès sinon.
    """
    sp = data.get("stock_from_prod", {})
    text = _color("text", email)
    muted = _color("muted", email)
    warn = _color("warn", email)
    ok = _color("ok", email)

    total = int(sp.get("dossiers_op89_semaine", 0) or 0)
    sans_stock = sp.get("dossiers_op89_sans_stock", []) or []
    n_sans = len(sans_stock)

    header = (
        f'<div style="font-size:15px;color:{text}">'
        f'{total} dossier{"s" if total > 1 else ""} terminé{"s" if total > 1 else ""} cette semaine · '
        f'<b style="color:{warn}">{n_sans} sans entrée stock dans les 48 h</b>'
        f'</div>'
    )

    if n_sans > 0:
        lines = []
        for d in sans_stock:
            date_fin = str(d.get("date_fin") or "")[:10]
            lines.append(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'font-size:13px;color:{text};padding:4px 0">'
                f'<div><b>{_esc(d["no_dossier"])}</b> · '
                f'<span style="color:{muted}">{_esc(d.get("client", "") or "—")}</span></div>'
                f'<div style="font-size:11px;color:{muted}">terminé le {_esc(date_fin)}</div>'
                f'</div>'
            )
        body = (
            f'{header}'
            f'<div style="margin-top:14px;padding:12px;border:1px solid {warn};'
            f'border-radius:10px;background:rgba(251,191,36,0.06)">'
            f'<div style="font-size:11px;color:{muted};text-transform:uppercase;'
            f'font-weight:600;letter-spacing:.3px;margin-bottom:8px">'
            f'À vérifier — mise en stock manquante</div>'
            f'<div style="display:flex;flex-direction:column;gap:6px">{"".join(lines)}</div>'
            f'</div>'
        )
    else:
        body = (
            f'{header}'
            f'<div style="margin-top:10px;color:{ok};font-size:13px">'
            f'✓ Toutes les productions terminées ont été mises en stock.</div>'
        )

    return _section_title("Cohérence prod → stock", email) + _card_wrap(body, email)


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
    """3 KPI cards + chips transporteurs.

    Note : la section "Retards de livraison" a été retirée sur retour utilisateur.
    Les données restent collectées dans data["expes"]["retards"] au cas où on
    voudrait les réactiver plus tard.
    """
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

    chips_html = ""
    transps = ex.get("by_transporteur", []) or []
    if transps:
        chips = []
        for t in transps:
            chips.append(
                f'<div style="padding:6px 10px;border:1px solid {border};border-radius:8px;'
                f'font-size:12px;color:{text}">'
                f'<b>{_esc(t["transporteur"])}</b> · {t["count"]} départ{"s" if t["count"] > 1 else ""} · '
                f'{_fnum(t["palettes"], 0)} pal'
                f'</div>'
            )
        chips_html = (
            f'<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:10px">'
            f'{"".join(chips)}</div>'
        )

    return _section_title("Expéditions", email) + _card_wrap(kpis + chips_html, email)


def _render_alerts(data: Dict[str, Any], email: bool, scope: str = "all") -> str:
    """scope='all'|'fab'|'log' — chaque catégorie devient une liste compacte avec cadre coloré."""
    a = data.get("alerts", {})
    text = _color("text", email)
    muted = _color("muted", email)
    warn = _color("warn", email)
    danger = _color("danger", email)

    parts = []

    if scope in ("all", "fab"):
        trous = a.get("trous_saisie", []) or []
        if trous:
            lines = []
            for t in trous:
                lines.append(
                    f'<div style="font-size:13px;color:{text}">'
                    f'<b>{_esc(t["no_dossier"])}</b> · '
                    f'{_esc(t.get("client", "") or "—")} · '
                    f'{_esc(t.get("machine", "") or "—")} · '
                    f'<span style="color:{warn};font-weight:600">{t.get("jours_ecoules", 0)} j</span>'
                    f'</div>'
                )
            parts.append(
                f'<div style="padding:10px 12px;border-left:3px solid {warn};'
                f'background:rgba(251,191,36,0.05);margin-bottom:8px">'
                f'<div style="font-size:11px;color:{muted};text-transform:uppercase;'
                f'font-weight:600;letter-spacing:.3px;margin-bottom:6px">'
                f'Trous de saisie · op 01 sans op 89 &gt; 5 j</div>'
                f'<div style="display:flex;flex-direction:column;gap:4px">{"".join(lines)}</div>'
                f'</div>'
            )

    if scope in ("all", "fab"):
        dep = a.get("depassements", []) or []
        if dep:
            lines = []
            for d in dep:
                lines.append(
                    f'<div style="font-size:13px;color:{text}">'
                    f'<b>{_esc(d["no_dossier"])}</b> · '
                    f'{_fnum(d["duree_reel"], 1)} h réelles / {_fnum(d["duree_prevu"], 1)} h prévues · '
                    f'<span style="color:{danger};font-weight:600">{_pct(d["ecart_pct"])}</span>'
                    f'</div>'
                )
            parts.append(
                f'<div style="padding:10px 12px;border-left:3px solid {danger};'
                f'background:rgba(248,113,113,0.05);margin-bottom:8px">'
                f'<div style="font-size:11px;color:{muted};text-transform:uppercase;'
                f'font-weight:600;letter-spacing:.3px;margin-bottom:6px">'
                f'Dépassements de durée &gt; 30 %</div>'
                f'<div style="display:flex;flex-direction:column;gap:4px">{"".join(lines)}</div>'
                f'</div>'
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
        if sec == "dossiers_fab_detail":
            return _render_dossiers_fab_detail(data.get("dossiers_fab_detail", []), email)
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
