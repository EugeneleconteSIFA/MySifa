"""SIFA — Production v0.9 — métrage produit = fin_machine - debut_machine"""
from typing import Optional, List
from fastapi import APIRouter, Request, Query
from datetime import datetime as _dt_cls
from database import get_db
from services.timings import compute_dossier_times
from services.auth_service import get_current_user, is_admin, can_view_all_prod, require_admin
from config import OPERATION_SEVERITY

router = APIRouter()

# ── Codes spéciaux ───────────────────────────────────────────────────────────
_CODES_CALAGE     = {'02','10','11','59','60','74','75','01'}
_CODES_PRODUCTION = {'03','88'}
_CODES_ARRET      = {c for c,v in OPERATION_SEVERITY.items()
                     if (v.get('category') or '').lower() == 'arret'}
_CODES_NETTOYAGE  = {c for c,v in OPERATION_SEVERITY.items()
                     if (v.get('category') or '').lower() == 'nettoyage'}
_CODE_ARRIVEE     = '86'
_CODE_DEPART      = '87'
_CODE_FIN_DOS     = '89'

def _norm_machine(m: str) -> Optional[str]:
    """Normalise le champ machine vers C1 ou C2 (None si non reconnu)."""
    if not m:
        return None
    n = m.lower().replace('é','e').replace('è','e').replace('ê','e').strip()
    if 'cohesio 1' in n or 'cohesion 1' in n or 'cohesio !' in n:
        return 'C1'
    if 'cohesio 2' in n or 'cohesion 2' in n:
        return 'C2'
    return None

def _clean_client(raw: str) -> str:
    """Supprime le préfixe code opérateur : '601 - ROQUETTE' → 'ROQUETTE'."""
    if not raw:
        return ''
    parts = raw.split(' - ', 1)
    if len(parts) == 2 and parts[0].strip().isdigit():
        return parts[1].strip()
    return raw.strip()

def _parse_date_op(s: str) -> Optional[_dt_cls]:
    """Parse date_operation (YYYY-MM-DDTHH:MM:SS ou DD/MM/YYYY HH:MM:SS)."""
    if not s:
        return None
    s = s.strip()
    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S',
                '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M'):
        try:
            return _dt_cls.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None

def _derive_status(rows_today: list) -> tuple:
    """
    Retourne (statut_key, statut_label, last_row_with_dossier).
    rows_today trié ASC par date_operation.
    """
    if not rows_today:
        return 'eteinte', 'Éteinte', None

    has_arrivee = any(r['operation_code'] == _CODE_ARRIVEE for r in rows_today)
    if not has_arrivee:
        return 'eteinte', 'Éteinte', None

    last = rows_today[-1]
    code = last['operation_code'] or ''
    cat  = (last['operation_category'] or '').lower()

    # Cherche le dernier dossier connu (non vide, non '0')
    last_dos_row = None
    for r in reversed(rows_today):
        nd = r.get('no_dossier') or ''
        if nd and nd != '0':
            last_dos_row = r
            break

    if code == _CODE_DEPART:
        return 'eteinte', 'Éteinte', None
    if code in (_CODE_ARRIVEE, _CODE_FIN_DOS):
        return 'changement', 'Changement de dossier', last_dos_row
    if code in _CODES_CALAGE or cat == 'calage':
        return 'calage', 'Calage', last_dos_row
    if code in _CODES_NETTOYAGE or cat == 'nettoyage':
        return 'nettoyage', 'Nettoyage', last_dos_row
    if code in _CODES_PRODUCTION or cat == 'production':
        return 'production', 'Production', last_dos_row
    if cat == 'arret':
        op_label = OPERATION_SEVERITY.get(code, {}).get('label', 'Arrêt')
        return 'arret', f'Arrêt — {op_label}', last_dos_row

    # Catch-all : affiche le label de l'opération
    op_label = OPERATION_SEVERITY.get(code, {}).get('label', f'Op {code}')
    return 'autre', op_label, last_dos_row

def _compute_duree_min(status_key: str, rows_today: list, now: _dt_cls) -> Optional[int]:
    """
    Calcule la durée (en minutes entières) du statut courant.

    • production : durée depuis la dernière saisie qui n'est ni production
      ni arrêt (= début de session productive). Les arrêts intermédiaires
      n'interrompent pas le compteur.
    • autres statuts : durée depuis la dernière saisie (= last row).
    • eteinte sans saisies : None.
    """
    if not rows_today:
        return None

    if status_key == 'production':
        # Remonter depuis la fin en cherchant le PLUS ANCIEN code production
        # de la séquence ininterrompue prod/arrêt.
        # Les arrêts sont transparents (on les traverse).
        # On s'arrête au premier événement qui n'est ni prod ni arrêt
        # (calage, arrivée, fin de dossier…) : ce qui précède ce point
        # marque le début de la session productive.
        earliest_prod = None
        for r in reversed(rows_today):
            c   = r.get('operation_code') or ''
            cat = (r.get('operation_category') or '').lower()
            if c in _CODES_PRODUCTION:
                earliest_prod = r          # mise à jour : on remonte
            elif c in _CODES_ARRET or cat == 'arret':
                pass                       # arrêt transparent
            else:
                break                      # fin du bloc courant
        if earliest_prod is None:
            earliest_prod = rows_today[-1]
        ts = _parse_date_op(earliest_prod.get('date_operation') or '')
        if ts is None:
            return None
        return max(0, int((now - ts).total_seconds() // 60))

    # Pour tous les autres statuts : durée depuis la dernière saisie
    last_ts = _parse_date_op(rows_today[-1].get('date_operation') or '')
    if last_ts is None:
        return None
    return max(0, int((now - last_ts).total_seconds() // 60))


@router.get("/api/production/machine-status")
def machine_status(request: Request):
    """
    Statut en temps réel des machines C1 et C2 basé sur les saisies de prod du jour.
    Accessible uniquement à la Direction, Administration et Super Admin.
    """
    require_admin(request)   # direction, administration ou superadmin uniquement

    now  = _dt_cls.now()
    iso_today = now.strftime('%Y-%m-%d')           # 'YYYY-MM-DD'
    old_today = now.strftime('%d/%m/%Y')            # 'DD/MM/YYYY'

    with get_db() as conn:
        rows = conn.execute(
            """SELECT operation_code, operation_category, machine,
                      no_dossier, client, designation, operateur, date_operation
               FROM production_data
               WHERE date_operation LIKE ? OR date_operation LIKE ?
               ORDER BY date_operation ASC""",
            (iso_today + '%', old_today + '%'),
        ).fetchall()

    # Bucket par machine (C1/C2) — tri par timestamp réel après fetch,
    # car les formats DD/MM/YYYY et YYYY-MM-DDTHH:MM:SS ne se trient pas
    # correctement par ORDER BY lexicographique.
    by_mkey: dict = {'C1': [], 'C2': []}
    for r in [dict(x) for x in rows]:
        k = _norm_machine(r.get('machine') or '')
        if k:
            by_mkey[k].append(r)
    for k in by_mkey:
        by_mkey[k].sort(key=lambda r: _parse_date_op(r.get('date_operation') or '') or _dt_cls.min)

    result = {}
    machine_names = {'C1': 'Cohésio 1', 'C2': 'Cohésio 2'}
    for mkey in ('C1', 'C2'):
        rows_m = by_mkey[mkey]
        status_key, status_label, dos_row = _derive_status(rows_m)

        dossier = None
        if dos_row:
            nd = dos_row.get('no_dossier') or ''
            if nd and nd != '0':
                dossier = {
                    'no_dossier':  nd,
                    'client':      _clean_client(dos_row.get('client') or ''),
                    'designation': (dos_row.get('designation') or '').strip(', ').strip(),
                }

        # Dernier opérateur arrivé (code 86)
        operateur = ''
        for r in reversed(rows_m):
            if r.get('operation_code') == _CODE_ARRIVEE:
                operateur = r.get('operateur') or ''
                break
        # Nettoie "907 - DENIS Alan" → "DENIS Alan"
        if ' - ' in operateur:
            operateur = operateur.split(' - ', 1)[1].strip()

        duree_min = _compute_duree_min(status_key, rows_m, now)

        result[mkey] = {
            'nom':          machine_names[mkey],
            'statut_key':   status_key,
            'statut_label': status_label,
            'operateur':    operateur,
            'dossier':      dossier,
            'duree_min':    duree_min,
        }

    return result

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
