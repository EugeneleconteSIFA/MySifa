"""
Statistiques des réponses aux alertes de maintenance (onglet Analyse).

Calculées ici, sur toute la période demandée, et non dans la page : la liste
de l'historique ne charge que les 1 000 dernières validations.

Ce qui entre dans les statistiques :
- les validations remplies par un opérateur. Fermetures automatiques et
  esquives ne comptent que dans le taux de remplissage ;
- les réponses rangées sous les questions ACTUELLES de l'alerte
  (`alertes_questionnaire.lire_saisie`). Une validation d'un ancien
  formulaire (aucune réponse ne se range plus) est écartée entièrement, et une
  réponse à une question retirée depuis n'est pas comptée.

Les filtres sont ceux de l'historique : alerte, période, machine, opérateur,
conformité, filtres par question. La non-conformité suit exactement la règle
de la page (`_ackHasNonConformite` de maintenance_page.py) ;
tests/test_alertes_statistiques.py rejoue les deux.
"""

import json
import math
import re
from datetime import date, datetime, timedelta

from app.services.alertes_questionnaire import items_de_params, lire_saisie

_FERMEE_AUTO = re.compile(r"^\s*Ferm[eé]e\s+auto\b", re.I)
PERIODES = ("today", "yesterday", "last7", "last30", "thisMonth", "prevMonth")


# ── Lecture des réponses ────────────────────────────────────────────────

def _nombre(x):
    """parseFloat de JavaScript, en plus strict : None si ce n'est pas un nombre."""
    if x is None or x == "" or isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x) if math.isfinite(x) else None
    m = re.match(r"^\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?", str(x))
    return float(m.group(0)) if m else None


def _valeurs(r) -> list:
    return r if isinstance(r, list) else ([] if r is None or r == "" else [r])


def nc_question(it: dict, r) -> bool:
    """La réponse `r` à la question `it` est-elle non conforme ?"""
    if not it:
        return False
    if it.get("type") == "value":
        if not it.get("out_of_range_is_nc"):
            return False
        mn, mx = _nombre(it.get("min")), _nombre(it.get("max"))
        for x in _valeurs(r):
            n = _nombre(x)
            if n is None:
                continue
            if (mn is not None and n < mn) or (mx is not None and n > mx):
                return True
        return False
    if not isinstance(r, list):
        return False
    nc = [str(x) for x in (it.get("nc_responses") or [])]
    for sel in r:
        s = str(sel if sel is not None else "").strip()
        if s in nc or (it.get("other_is_nc") and s == "Autre"):
            return True
    return False


def est_non_conforme(items: list, responses: dict) -> bool:
    return any(nc_question(it, (responses or {}).get(str(i))) for i, it in enumerate(items))


def passe_filtres_points(items: list, responses: dict, filtres: dict) -> bool:
    """Filtres par question du bandeau « Réponses » (_matchPointFilters)."""
    for k, filt in (filtres or {}).items():
        try:
            idx = int(k)
        except (TypeError, ValueError):
            continue
        if idx < 0 or idx >= len(items) or not isinstance(filt, dict):
            continue
        it, r = items[idx], (responses or {}).get(str(idx))
        if it.get("type") == "value":
            # Comme parseFloat côté page : une liste se lit par sa 1re mesure.
            num = _nombre(r[0] if isinstance(r, list) and r else r)
            mn, mx = _nombre(filt.get("min")), _nombre(filt.get("max"))
            if mn is not None and (num is None or num < mn):
                return False
            if mx is not None and (num is None or num > mx):
                return False
        else:
            v = filt.get("value")
            if v not in (None, "") and v not in _valeurs(r):
                return False
    return True


# ── Période ─────────────────────────────────────────────────────────────

def bornes_periode(cle: str, aujourd_hui: date = None):
    """Mêmes raccourcis que maintDatePresets() de la page."""
    j = aujourd_hui or date.today()
    if cle == "today":
        return j, j
    if cle == "yesterday":
        return j - timedelta(days=1), j - timedelta(days=1)
    if cle == "last7":
        return j - timedelta(days=6), j
    if cle == "last30":
        return j - timedelta(days=29), j
    if cle == "thisMonth":
        return j.replace(day=1), j
    if cle == "prevMonth":
        fin = j.replace(day=1) - timedelta(days=1)
        return fin.replace(day=1), fin
    return None, None


def _jour(s):
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


# ── Calculs ─────────────────────────────────────────────────────────────

def _pct(n, total):
    return round(100.0 * n / total, 1) if total else None


def _resume(vals: list) -> dict:
    vals = sorted(vals)
    n = len(vals)
    if not n:
        return {"n": 0}
    moy = sum(vals) / n
    med = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
    et = math.sqrt(sum((v - moy) ** 2 for v in vals) / (n - 1)) if n > 1 else 0.0
    return {"n": n, "moyenne": round(moy, 4), "mediane": round(med, 4),
            "ecart_type": round(et, 4), "min": vals[0], "max": vals[-1]}


def _histogramme(vals: list, it: dict, nb: int = 12) -> list:
    if not vals:
        return []
    bas, haut = min(vals), max(vals)
    for b in (_nombre(it.get("min")), _nombre(it.get("max"))):
        if b is not None:
            bas, haut = min(bas, b), max(haut, b)
    if haut == bas:
        return [{"de": bas, "a": haut, "n": len(vals)}]
    pas = (haut - bas) / nb
    classes = [{"de": round(bas + i * pas, 6), "a": round(bas + (i + 1) * pas, 6), "n": 0} for i in range(nb)]
    for v in vals:
        classes[min(nb - 1, int((v - bas) / pas))]["n"] += 1
    return classes


def _semaine(j: date) -> str:
    return (j - timedelta(days=j.weekday())).isoformat()


def _stats_choix(it, lignes, idx):
    rep, autres, semaines = {}, {}, {}
    repondants = 0
    for l in lignes:
        r = l["responses"].get(str(idx))
        vals = [str(v) for v in _valeurs(r)]
        if not vals:
            continue
        repondants += 1
        for v in vals:
            rep[v] = rep.get(v, 0) + 1
        precision = str(l["responses"].get(str(idx) + "_other") or "").strip()
        if precision:
            cle = re.sub(r"\s+", " ", precision.lower())
            e = autres.setdefault(cle, {"texte": precision, "n": 0})
            e["n"] += 1
        s = semaines.setdefault(_semaine(l["jour"]), {"semaine": _semaine(l["jour"]), "n": 0, "nc": 0})
        s["n"] += 1
        if nc_question(it, r):
            s["nc"] += 1
    nc_set = set(str(x) for x in (it.get("nc_responses") or []))
    ordre = [str(x) for x in (it.get("responses") or [])]
    cles = ordre + sorted(k for k in rep if k not in ordre)
    return {
        "repondants": repondants,
        "repartition": [{"reponse": k, "n": rep.get(k, 0), "pct": _pct(rep.get(k, 0), repondants),
                         "nc": k in nc_set or (k == "Autre" and bool(it.get("other_is_nc")))}
                        for k in cles if rep.get(k) or k in ordre],
        "autres": sorted(autres.values(), key=lambda e: -e["n"])[:10],
        "evolution": [dict(s, taux_nc=_pct(s["nc"], s["n"])) for _, s in sorted(semaines.items())],
    }


def _stats_valeur(it, lignes, idx):
    mesures, serie, ecarts, par_position = [], [], [], {}
    mn, mx = _nombre(it.get("min")), _nombre(it.get("max"))
    hors = 0
    for l in lignes:
        r = l["responses"].get(str(idx))
        vals = [v for v in (_nombre(x) for x in _valeurs(r)) if v is not None]
        if not vals:
            continue
        mesures.extend(vals)
        hors += sum(1 for v in vals if (mn is not None and v < mn) or (mx is not None and v > mx))
        serie.append({"t": l["ack_at"], "v": round(sum(vals) / len(vals), 4), "vals": vals,
                      "machine": l["machine"], "nc": nc_question(it, r)})
        if len(vals) > 1:
            ecarts.append(max(vals) - min(vals))
            for i, v in enumerate(vals):
                par_position.setdefault(i, []).append(v)
    out = {
        "resume": _resume(mesures),
        "controles": len(serie),
        "hors_tolerance": hors,
        "pct_hors_tolerance": _pct(hors, len(mesures)) if (mn is not None or mx is not None) else None,
        "min": mn, "max": mx, "cible": _nombre(it.get("target_value")),
        "serie": serie,
        "histogramme": _histogramme(mesures, it),
    }
    if ecarts:
        out["multiples"] = {
            "libelle": it.get("libelle_point") or "Mesure",
            "ecart": _resume(ecarts),
            "par_position": [{"position": i + 1, **_resume(v)} for i, v in sorted(par_position.items())],
        }
    return out


def _comparaison(lignes, items, cle):
    groupes = {}
    for l in lignes:
        k = l.get(cle) or ""
        g = groupes.setdefault(k, {"cle": k, "n": 0, "nc": 0, "_v": {}})
        g["n"] += 1
        if l["nc"]:
            g["nc"] += 1
        for i, it in enumerate(items):
            if it.get("type") != "value":
                continue
            vals = [v for v in (_nombre(x) for x in _valeurs(l["responses"].get(str(i)))) if v is not None]
            if vals:
                g["_v"].setdefault(i, []).extend(vals)
    out = []
    for g in groupes.values():
        moy = {str(i): round(sum(v) / len(v), 4) for i, v in g.pop("_v").items()}
        out.append(dict(g, taux_nc=_pct(g["nc"], g["n"]), moyennes=moy))
    return sorted(out, key=lambda g: (-g["n"], g["cle"]))


def _produits(conn, dossiers: set) -> dict:
    """{no_dossier: {ref_produit, adhesif}} depuis le planning et la fiche technique."""
    dossiers = sorted(d for d in dossiers if d)
    if not dossiers:
        return {}
    out = {}
    try:
        ph = ",".join("?" * len(dossiers))
        rows = conn.execute(
            f"""SELECT TRIM(pe.reference) AS reference, TRIM(COALESCE(pe.numero_of,'')) AS numero_of,
                       COALESCE(NULLIF(TRIM(pe.ref_produit),''), pe.ref_produit_norm) AS ref_produit,
                       (SELECT ft.adhesif FROM fiches_techniques ft
                         WHERE TRIM(COALESCE(ft.ref_produit_norm,'')) != ''
                           AND TRIM(ft.ref_produit_norm) = TRIM(COALESCE(pe.ref_produit_norm,''))
                         ORDER BY ft.id LIMIT 1) AS adhesif
                  FROM planning_entries pe
                 WHERE TRIM(pe.reference) IN ({ph}) OR TRIM(COALESCE(pe.numero_of,'')) IN ({ph})""",
            tuple(dossiers) * 2,
        ).fetchall()
    except Exception:
        return {}  # planning ou fiches absents : comparaison produit vide
    for r in rows:
        for k in (r["reference"], r["numero_of"]):
            if k in dossiers and (k not in out or not out[k]["ref_produit"]):
                out[k] = {"ref_produit": r["ref_produit"] or "", "adhesif": r["adhesif"] or ""}
    return out


def _lignes(conn, alerte_id, du, au, machine, operateur):
    where, params = ["a.alert_id = ?"], [alerte_id]
    if du:
        where.append("a.ack_at >= ?")
        params.append(du.isoformat() + "T00:00:00")
    if au:
        where.append("a.ack_at <= ?")
        params.append(au.isoformat() + "T23:59:59")
    if machine:
        where.append("a.machine = ?")
        params.append(machine)
    if operateur:
        where.append("a.user_nom = ?")
        params.append(operateur)
    return conn.execute(
        f"""SELECT a.id, a.ack_at, a.machine, a.user_nom, a.no_dossier, a.responses,
                   a.comment, COALESCE(a.dismissed, 0) AS dismissed, a.questionnaire
              FROM maintenance_alert_acks a
             WHERE {' AND '.join(where)}
             ORDER BY a.ack_at, a.id""",
        tuple(params),
    ).fetchall()


def _trier(rows, items, conformite, points):
    """(validations retenues, compteurs). Une validation retenue porte ses
    réponses alignées sur les questions actuelles."""
    compte = {"fermetures_auto": 0, "esquives": 0, "anciens_exclus": 0, "remplies": 0}
    retenues = []
    for r in rows:
        if r["dismissed"]:
            compte["esquives"] += 1
            continue
        if _FERMEE_AUTO.match(r["comment"] or ""):
            compte["fermetures_auto"] += 1
            continue
        try:
            resp = json.loads(r["responses"] or "{}")
        except (TypeError, ValueError):
            resp = {}
        lu = lire_saisie(resp, r["questionnaire"], items)
        if lu["ancien"]:
            compte["anciens_exclus"] += 1
            continue
        compte["remplies"] += 1
        nc = est_non_conforme(items, lu["responses"])
        if conformite == "nc" and not nc:
            continue
        if conformite == "ok" and nc:
            continue
        if not passe_filtres_points(items, lu["responses"], points):
            continue
        retenues.append({"id": r["id"], "ack_at": r["ack_at"], "jour": _jour(r["ack_at"]),
                         "machine": r["machine"] or "", "operateur": r["user_nom"] or "",
                         "no_dossier": (r["no_dossier"] or "").strip(), "responses": lu["responses"],
                         "comment": r["comment"] or "", "nc": nc})
    return retenues, compte


def statistiques(conn, alerte_ids, du=None, au=None, machine=None, operateur=None,
                 conformite=None, points=None) -> dict:
    """Statistiques par alerte. `du` / `au` : dates (date) ou None."""
    alertes = []
    for aid in alerte_ids:
        al = conn.execute("SELECT id, nom, params FROM maintenance_alerts WHERE id = ?", (aid,)).fetchone()
        if not al:
            continue
        items = items_de_params(al["params"])
        rows = _lignes(conn, aid, du, au, machine, operateur)
        lignes, compte = _trier(rows, items, conformite, points)
        total = compte["remplies"] + compte["fermetures_auto"] + compte["esquives"]
        nc = sum(1 for l in lignes if l["nc"])
        synthese = dict(compte, validations=len(lignes), nc=nc, taux_nc=_pct(nc, len(lignes)),
                        remplissage=_pct(compte["remplies"], total), occurrences=total)
        if du and au:
            # Même durée, juste avant : sert à la tendance du bandeau.
            duree = (au - du).days + 1
            p_au, p_du = du - timedelta(days=1), du - timedelta(days=duree)
            p_lignes, _ = _trier(_lignes(conn, aid, p_du, p_au, machine, operateur), items, conformite, points)
            p_nc = sum(1 for l in p_lignes if l["nc"])
            synthese["precedent"] = {"du": p_du.isoformat(), "au": p_au.isoformat(),
                                     "validations": len(p_lignes), "taux_nc": _pct(p_nc, len(p_lignes))}
        produits = _produits(conn, {l["no_dossier"] for l in lignes})
        for l in lignes:
            p = produits.get(l["no_dossier"]) or {}
            l["produit"] = p.get("ref_produit") or ""
            l["adhesif"] = p.get("adhesif") or ""
        questions = []
        for i, it in enumerate(items):
            q = {"index": i, "id": it.get("id") or "", "label": it.get("label") or f"Question {i + 1}",
                 "type": "value" if it.get("type") == "value" else "choice", "unit": it.get("unit") or ""}
            q.update(_stats_valeur(it, lignes, i) if q["type"] == "value" else _stats_choix(it, lignes, i))
            questions.append(q)
        alertes.append({
            "id": al["id"], "nom": al["nom"] or "", "synthese": synthese, "questions": questions,
            "comparaisons": {
                "machine": _comparaison(lignes, items, "machine"),
                "operateur": _comparaison(lignes, items, "operateur"),
                "produit": _comparaison([l for l in lignes if l["produit"]], items, "produit"),
                "adhesif": _comparaison([l for l in lignes if l["adhesif"]], items, "adhesif"),
            },
            "_lignes": lignes, "_items": items,
        })
    return {"du": du.isoformat() if du else None, "au": au.isoformat() if au else None, "alertes": alertes}


def texte_reponse(it: dict, responses: dict, idx: int) -> str:
    """Réponse lisible d'une question, pour l'export."""
    r = responses.get(str(idx))
    s = (" / " if it.get("type") == "value" else ", ").join(str(v) for v in _valeurs(r))
    autre = responses.get(str(idx) + "_other")
    if autre not in (None, ""):
        s = f"{s} — {autre}" if s else str(autre)
    com = str(responses.get(str(idx) + "_comment") or "").strip()
    if com:
        s = f"{s} « {com} »" if s else f"« {com} »"
    return s
