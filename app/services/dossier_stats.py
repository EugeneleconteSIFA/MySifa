"""Statistiques de production agrégées pour un dossier (no_dossier)."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import CODE_PRODUCTION, CODE_REPRISE, OPERATION_SEVERITY
from database import parse_datetime
from services.timings import compute_dossier_times

_FMTS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y",
)


def _norm_date(dt_raw: str) -> str:
    s = str(dt_raw or "").strip()
    for fmt in _FMTS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return s[:10]


def _norm_dt(dt_raw: str) -> str:
    s = str(dt_raw or "").strip()
    for fmt in _FMTS:
        try:
            return datetime.strptime(s, fmt).isoformat()
        except ValueError:
            continue
    return s


def _compute_duree_minutes_by_id(rows: List[dict]) -> Dict[int, float]:
    by_key: Dict[tuple, list] = defaultdict(list)
    for r in rows:
        rid = r.get("id")
        dt = parse_datetime(r.get("date_operation"))
        if rid is None or dt is None:
            continue
        key = (str(r.get("operateur") or "?"), dt.date().isoformat())
        by_key[key].append((dt, r))

    out: Dict[int, float] = {}
    for items in by_key.values():
        items_sorted = sorted(
            items,
            key=lambda x: (x[0] if x[0] else datetime.min, int(x[1].get("id") or 0)),
        )
        for i, (dt, r) in enumerate(items_sorted[:-1]):
            nxt = items_sorted[i + 1][0]
            delta = (nxt - dt).total_seconds() / 60.0
            if delta < 0 or delta > 480:
                continue
            out[int(r["id"])] = round(delta, 1)
    return out


def _enrich_metrage(all_list: List[dict], dossier_times: List[dict]) -> List[dict]:
    debut_entries: Dict[tuple, list] = {}
    fin_data: Dict[tuple, dict] = {}

    for r in all_list:
        code = str(r.get("operation_code") or "")
        dos = str(r.get("no_dossier") or "").strip()
        if not dos or dos == "0":
            continue
        op = str(r.get("operateur") or "?")
        dt_op = str(r.get("date_operation") or "")

        if code == "01":
            ctr = float(r["metrage_prevu"]) if r.get("metrage_prevu") is not None else 0.0
            debut_entries.setdefault((op, dos), []).append((_norm_dt(dt_op), ctr))
        elif code == "89" and r.get("metrage_reel") is not None:
            fin_dt = _norm_dt(dt_op)
            jour_iso = _norm_date(dt_op)
            key = (op, jour_iso, dos)
            entry = fin_data.setdefault(key, {"metrage_m": 0.0, "etiquettes": 0.0})
            debuts = debut_entries.get((op, dos), [])
            before = [(dt, m) for dt, m in debuts if dt <= fin_dt]
            debut_ctr = sorted(before, reverse=True)[0][1] if before else 0.0
            produit = max(0.0, float(r["metrage_reel"]) - debut_ctr)
            entry["metrage_m"] += produit
            if r.get("quantite_traitee") is not None:
                entry["etiquettes"] = float(r["quantite_traitee"])

    enriched = []
    for d in dossier_times:
        op = str(d.get("operateur") or "?")
        dos = str(d.get("no_dossier") or "")
        dt = str(d.get("jour") or "")
        entry = fin_data.get((op, dt, dos), {})
        row = dict(d)
        row["etiquettes"] = entry.get("etiquettes") or d.get("quantite_traitee") or 0
        row["metrage_m"] = round(float(entry.get("metrage_m", 0.0)), 1)
        enriched.append(row)
    return enriched


def _by_operation(rows: List[dict]) -> List[dict]:
    duree_by_id = _compute_duree_minutes_by_id(rows)
    agg: Dict[str, dict] = {}
    for r in rows:
        rid = r.get("id")
        if rid is None:
            continue
        minutes = float(duree_by_id.get(int(rid), 0.0) or 0.0)
        code = str(r.get("operation_code") or "").strip() or "?"
        cat = str(r.get("operation_category") or "").strip().lower()
        if not cat:
            info = OPERATION_SEVERITY.get(code, {})
            cat = str(info.get("category") or "autre").lower()
        label = str(r.get("operation") or "").strip()
        if not label:
            label = OPERATION_SEVERITY.get(code, {}).get("label", f"Op {code}")
        acc = agg.setdefault(
            code,
            {
                "code": code,
                "label": label,
                "category": cat,
                "minutes": 0.0,
                "count": 0,
            },
        )
        acc["count"] += 1
        acc["minutes"] += minutes
        if not acc["label"] and label:
            acc["label"] = label

    out = []
    for v in agg.values():
        v["minutes"] = round(v["minutes"], 1)
        out.append(v)
    return sorted(out, key=lambda x: (-x["minutes"], x["code"]))


def _clean_operateur(name: str) -> str:
    s = str(name or "").strip()
    if " - " in s:
        return s.split(" - ", 1)[1].strip() or s
    return s or "?"


def build_dossier_production_stats(rows: List[dict], no_dossier: str) -> dict:
    """Construit les stats MyProd pour un seul no_dossier."""
    ref = str(no_dossier or "").strip()
    all_list = [dict(r) for r in rows if str(r.get("no_dossier") or "").strip() == ref]
    if not all_list:
        return {
            "no_dossier": ref,
            "nb_saisies": 0,
            "temps_totaux": {
                "duree_totale_min": 0.0,
                "calage_min": 0.0,
                "production_min": 0.0,
                "arret_min": 0.0,
            },
            "quantites": {"etiquettes": 0.0, "metrage_m": 0.0},
            "vitesse_m_min": 0.0,
            "by_category": [],
            "by_operation": [],
            "operateurs": [],
        }

    dossier_times = _enrich_metrage(all_list, compute_dossier_times(all_list))

    calage = sum(float(d.get("temps_calage_min") or 0) for d in dossier_times)
    prod = sum(float(d.get("temps_prod_min") or 0) for d in dossier_times)
    arret = sum(float(d.get("temps_arret_min") or 0) for d in dossier_times)
    session = sum(
        float(d.get("temps_total_calage_min") or 0)
        for d in dossier_times
        if d.get("temps_total_calage_min") is not None
    )
    duree_totale = round(session if session > 0 else calage + prod + arret, 1)

    etiquettes = round(sum(float(d.get("etiquettes") or 0) for d in dossier_times), 1)
    metrage = round(sum(float(d.get("metrage_m") or 0) for d in dossier_times), 1)
    denom = prod + arret
    vitesse = round(metrage / denom, 3) if denom > 0 else 0.0

    by_category = [
        {"category": "calage", "label": "Calage", "minutes": round(calage, 1)},
        {
            "category": "production",
            "label": "Production",
            "minutes": round(prod, 1),
        },
        {"category": "arret", "label": "Arrêts", "minutes": round(arret, 1)},
    ]

    op_agg: Dict[str, dict] = {}
    for d in dossier_times:
        op_raw = str(d.get("operateur") or "?")
        acc = op_agg.setdefault(
            op_raw,
            {
                "operateur": _clean_operateur(op_raw),
                "operateur_raw": op_raw,
                "nb_saisies": 0,
                "calage_min": 0.0,
                "prod_min": 0.0,
                "arret_min": 0.0,
                "minutes": 0.0,
            },
        )
        acc["calage_min"] += float(d.get("temps_calage_min") or 0)
        acc["prod_min"] += float(d.get("temps_prod_min") or 0)
        acc["arret_min"] += float(d.get("temps_arret_min") or 0)

    op_saisies: Dict[str, int] = defaultdict(int)
    for r in all_list:
        op_saisies[str(r.get("operateur") or "?")] += 1

    operateurs = []
    for op_raw, acc in op_agg.items():
        acc["nb_saisies"] = op_saisies.get(op_raw, 0)
        acc["calage_min"] = round(acc["calage_min"], 1)
        acc["prod_min"] = round(acc["prod_min"], 1)
        acc["arret_min"] = round(acc["arret_min"], 1)
        acc["minutes"] = round(
            acc["calage_min"] + acc["prod_min"] + acc["arret_min"], 1
        )
        operateurs.append(acc)
    operateurs.sort(key=lambda x: (-x["minutes"], x["operateur"]))

    return {
        "no_dossier": ref,
        "nb_saisies": len(all_list),
        "temps_totaux": {
            "duree_totale_min": duree_totale,
            "calage_min": round(calage, 1),
            "production_min": round(prod, 1),
            "arret_min": round(arret, 1),
        },
        "quantites": {"etiquettes": etiquettes, "metrage_m": metrage},
        "vitesse_m_min": vitesse,
        "by_category": by_category,
        "by_operation": _by_operation(all_list),
        "operateurs": operateurs,
    }
