"""SIFA — Production v0.9 — métrage produit = fin_machine - debut_machine"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request, Query
from datetime import datetime as _dt_cls
from zoneinfo import ZoneInfo as _ZoneInfo
_TZ_PARIS = _ZoneInfo('Europe/Paris')
from database import get_db
from services.timings import compute_dossier_times
from services.auth_service import get_current_user, is_admin, can_view_all_prod, require_admin
from services.prod_machine_filter import append_machine_filter
from config import OPERATION_SEVERITY
import logging
_log = logging.getLogger(__name__)

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
    Calcule la durée (en minutes) du statut courant.
    Production : depuis le début de la séquence prod/arrêt en cours
    (les arrêts sont transparents). Autres statuts : depuis la dernière saisie.
    """
    if not rows_today:
        return None

    if status_key == 'production':
        earliest_prod = None
        for r in reversed(rows_today):
            c   = r.get('operation_code') or ''
            cat = (r.get('operation_category') or '').lower()
            if c in _CODES_PRODUCTION:
                earliest_prod = r
            elif c in _CODES_ARRET or cat == 'arret':
                pass
            else:
                break
        if earliest_prod is None:
            earliest_prod = rows_today[-1]
        ts = _parse_date_op(earliest_prod.get('date_operation') or '')
        if ts is None:
            return None
        return max(0, int((now - ts).total_seconds() // 60))

    last_ts = _parse_date_op(rows_today[-1].get('date_operation') or '')
    if last_ts is None:
        return None
    return max(0, int((now - last_ts).total_seconds() // 60))


def _rep_team_for_operator(conn, operateur_nom: str, jour_iso: str):
    """Renvoie le creneau ('matin'|'aprem'|None) de l'operateur pour un jour donne
    sur la machine Repiquage, via rh_planning_postes.
    """
    if not operateur_nom or not jour_iso:
        return None
    try:
        d = _dt_cls.fromisoformat(jour_iso[:10]).date()
        iso_year, iso_week, iso_weekday = d.isocalendar()
    except Exception:
        return None
    semaine = '{0}-W{1:02d}'.format(iso_year, iso_week)
    day_bit = 1 << (iso_weekday - 1)
    mach = conn.execute(
        "SELECT id FROM machines WHERE actif=1 AND ("
        "lower(trim(COALESCE(nom,''))) LIKE 'repiquage%' "
        "OR lower(trim(COALESCE(nom,''))) = 'rep')"
    ).fetchone()
    if not mach:
        return None
    repiquage_machine_id = int(mach[0])
    row = conn.execute(
        "SELECT p.creneau, p.jours "
        "FROM rh_planning_postes p JOIN users u ON u.id = p.user_id "
        "WHERE p.semaine = ? AND p.machine_id = ? "
        "AND trim(lower(u.nom)) = trim(lower(?))",
        (semaine, repiquage_machine_id, operateur_nom),
    ).fetchone()
    if not row:
        return None
    creneau = (row[0] or '').strip()
    jours = int(row[1] or 0)
    if not (jours & day_bit):
        return None
    if creneau in ('matin', 'aprem'):
        return creneau
    return None


def _format_team_label(team_members):
    """Format 'Repiquage (Prenom1 & Prenom2)' a partir d'une iterable de noms."""
    prenoms = []
    for nom in sorted({(n or '').strip() for n in (team_members or []) if n}):
        first = nom.split()[0] if nom else ''
        if first:
            prenoms.append(first)
    if not prenoms:
        return 'Repiquage'
    return 'Repiquage (' + ' & '.join(prenoms) + ')'


def _rep_get_full_team_for_date(conn, operateur_nom: str, jour_iso: str):
    """Renvoie (creneau, [tous_les_membres_de_l_equipe]) pour cet operateur ce jour.
    Tous les membres planning_rh sur ce creneau (matin ou aprem), pas seulement
    ceux qui ont saisi. Renvoie (None, []) si non trouve.
    """
    if not operateur_nom or not jour_iso:
        return (None, [])
    try:
        d = _dt_cls.fromisoformat(jour_iso[:10]).date()
        iso_year, iso_week, iso_weekday = d.isocalendar()
    except Exception:
        return (None, [])
    semaine = '{0}-W{1:02d}'.format(iso_year, iso_week)
    day_bit = 1 << (iso_weekday - 1)
    mach = conn.execute(
        "SELECT id FROM machines WHERE actif=1 AND ("
        "lower(trim(COALESCE(nom,''))) LIKE 'repiquage%' "
        "OR lower(trim(COALESCE(nom,''))) = 'rep')"
    ).fetchone()
    if not mach:
        return (None, [])
    repiquage_machine_id = int(mach[0])
    row = conn.execute(
        "SELECT p.creneau, p.jours "
        "FROM rh_planning_postes p JOIN users u ON u.id = p.user_id "
        "WHERE p.semaine = ? AND p.machine_id = ? "
        "AND trim(lower(u.nom)) = trim(lower(?))",
        (semaine, repiquage_machine_id, operateur_nom),
    ).fetchone()
    if not row:
        return (None, [])
    creneau = (row[0] or '').strip()
    jours = int(row[1] or 0)
    if not (jours & day_bit):
        return (None, [])
    if creneau not in ('matin', 'aprem'):
        return (None, [])
    members = conn.execute(
        "SELECT DISTINCT u.nom "
        "FROM rh_planning_postes p JOIN users u ON u.id = p.user_id "
        "WHERE p.semaine = ? AND p.machine_id = ? AND p.creneau = ? "
        "AND (p.jours & ?) != 0",
        (semaine, repiquage_machine_id, creneau, day_bit),
    ).fetchall()
    noms = sorted({(m[0] or '').strip() for m in members if m and m[0]})
    return (creneau, noms)


def _build_repiquage_team_rows(all_list, dossier_times, no_dossier_filter=None):
    """Pour chaque saisie Repiquage (code 03), identifier l'equipe complete
    de la date concernee via planning_rh, et agreger.
    Le label utilise TOUS les membres planifies sur le creneau (pas que ceux
    qui ont saisi), au format 'Repiquage (Prenom1 & Prenom2)'.
    """
    nd_filter = set(d for d in (no_dossier_filter or []) if d)
    rep_lines = []
    for r in all_list:
        code = str(r.get('operation_code') or '')
        if code != '03':
            continue
        if not _is_machine_repiquage_name(r.get('machine')):
            continue
        if nd_filter and str(r.get('no_dossier') or '').strip() not in nd_filter:
            continue
        rep_lines.append(r)
    if not rep_lines:
        return []
    # Pour chaque saisie : identifier l'equipe (creneau + membres complets)
    # et accumuler les totaux par equipe (regroupes par cle membres-tuple)
    by_team = {}  # tuple(sorted(noms_complets)) -> agg
    with get_db() as conn:
        for r in rep_lines:
            op_nom = str(r.get('operateur') or '').strip()
            jour_iso = str(r.get('date_operation') or '')[:10]
            if not op_nom or not jour_iso:
                continue
            _creneau, full_team = _rep_get_full_team_for_date(conn, op_nom, jour_iso)
            if not full_team:
                continue
            key = tuple(full_team)
            acc = by_team.setdefault(key, {
                'membres': list(full_team),
                'dossiers': set(),
                'etiquettes': 0.0,
                'cartons': 0,
            })
            dos = str(r.get('no_dossier') or '').strip()
            if dos:
                acc['dossiers'].add(dos)
            acc['etiquettes'] += float(r.get('quantite_traitee') or 0)
            acc['cartons'] += int(r.get('nb_cartons') or 0) if r.get('nb_cartons') is not None else 0
    out = []
    for _team_key, t in by_team.items():
        label = _format_team_label(t['membres'])
        out.append({
            'key': label,
            'dossiers': len(t['dossiers']),
            'etiquettes': round(t['etiquettes'], 1),
            'metrage_m': 0.0,
            'calage_min': 0.0,
            'prod_min': 0.0,
            'arret_min': 0.0,
            'vitesse_m_min': 0.0,
            'cartons': t['cartons'],
            'is_repiquage_team': True,
            'team_members': list(t['membres']),
        })
    return sorted(out, key=lambda x: x['etiquettes'], reverse=True)


def _build_repiquage_dossier_rows(all_list):
    """Construit des sessions virtuelles 'Repiquage' agregees par
    (operateur, no_dossier, jour) depuis les saisies code 03 sur machine Repiquage.

    Chaque ligne est enrichie d'un champ team_label resolu via planning_rh
    (cache (op, jour) -> label pour limiter les requetes).

    Format identique a by_dossier (issu de compute_dossier_times) pour pouvoir
    etre concatene proprement dans by_dossier_with_rep. Les champs temps sont
    a 0 (le repiquage ne tracke pas calage/prod/arret par session).
    """
    # 1) Filtrer les saisies repiquage utiles
    rep_lines = []
    for r in all_list:
        if str(r.get('operation_code') or '') != '03':
            continue
        if not _is_machine_repiquage_name(r.get('machine')):
            continue
        op = str(r.get('operateur') or '').strip()
        dos = str(r.get('no_dossier') or '').strip()
        jour = str(r.get('date_operation') or '')[:10]
        if not op or not dos or not jour:
            continue
        rep_lines.append((r, op, dos, jour))
    if not rep_lines:
        return []
    # 2) Resoudre team_label par (op_lc, jour) en cache pour limiter le DB hit
    team_cache = {}  # (op_lc, jour) -> team_label
    try:
        with get_db() as conn:
            for _r, op, _dos, jour in rep_lines:
                ck = (op.lower(), jour)
                if ck in team_cache:
                    continue
                try:
                    _creneau, full_team = _rep_get_full_team_for_date(conn, op, jour)
                except Exception:
                    full_team = []
                team_cache[ck] = _format_team_label(full_team) if full_team else 'Repiquage'
    except Exception as _exc:
        _log.exception('team_cache build failed: %s', _exc)
    # 3) Agreger par (operateur, no_dossier, jour)
    agg = {}
    for r, op, dos, jour in rep_lines:
        team_label = team_cache.get((op.lower(), jour)) or 'Repiquage'
        key = (op, dos, jour)
        x = agg.setdefault(key, {
            'operateur': op,
            'no_dossier': dos,
            'jour': jour,
            'machine': 'Repiquage',
            'team_label': team_label,
            'client': str(r.get('client') or '').strip(),
            'designation': str(r.get('designation') or '').strip().strip(',').strip(),
            'etiquettes': 0.0,
            'metrage_m': 0.0,
            'temps_calage_min': 0.0,
            'temps_prod_min': 0.0,
            'temps_arret_min': 0.0,
            'cartons': 0,
        })
        x['etiquettes'] += float(r.get('quantite_traitee') or 0)
        try:
            x['cartons'] += int(r.get('nb_cartons') or 0)
        except Exception:
            pass
        if not x.get('client') and r.get('client'):
            x['client'] = str(r.get('client') or '').strip()
        if not x.get('designation') and r.get('designation'):
            x['designation'] = str(r.get('designation') or '').strip().strip(',').strip()
    out = []
    for v in agg.values():
        v['etiquettes'] = round(v['etiquettes'], 1)
        out.append(v)
    return sorted(out, key=lambda x: (x.get('jour') or '', x.get('operateur') or ''), reverse=True)


def _build_repiquage_machine_row(all_list):
    """Une seule ligne 'Repiquage' agregeant cartons + etiq de toutes les saisies 03."""
    total_cartons = 0
    total_etiq = 0.0
    dossiers = set()
    for r in all_list:
        if str(r.get('operation_code') or '') != '03':
            continue
        if not _is_machine_repiquage_name(r.get('machine')):
            continue
        total_cartons += int(r.get('nb_cartons') or 0) if r.get('nb_cartons') is not None else 0
        total_etiq += float(r.get('quantite_traitee') or 0)
        dos = str(r.get('no_dossier') or '').strip()
        if dos:
            dossiers.add(dos)
    if total_cartons == 0 and total_etiq == 0:
        return None
    return {
        'key': 'Repiquage',
        'dossiers': len(dossiers),
        'etiquettes': round(total_etiq, 1),
        'metrage_m': 0.0,
        'calage_min': 0.0,
        'prod_min': 0.0,
        'arret_min': 0.0,
        'vitesse_m_min': 0.0,
        'cartons': total_cartons,
    }


def _augment_by_day_with_repiquage(by_day, all_list):
    """Ajoute aux lignes by_day les etiq/cartons Repiquage du jour correspondant."""
    rep_by_day = {}
    for r in all_list:
        if str(r.get('operation_code') or '') != '03':
            continue
        if not _is_machine_repiquage_name(r.get('machine')):
            continue
        jour = str(r.get('date_operation') or '')[:10]
        if not jour:
            continue
        acc = rep_by_day.setdefault(jour, {'etiquettes': 0.0, 'cartons': 0, 'dossiers': set()})
        acc['etiquettes'] += float(r.get('quantite_traitee') or 0)
        acc['cartons'] += int(r.get('nb_cartons') or 0) if r.get('nb_cartons') is not None else 0
        dos = str(r.get('no_dossier') or '').strip()
        if dos:
            acc['dossiers'].add(dos)
    # Mettre a jour les lignes existantes
    existing_keys = {row.get('key'): row for row in by_day}
    for jour, acc in rep_by_day.items():
        if jour in existing_keys:
            row = existing_keys[jour]
            row['etiquettes'] = round(float(row.get('etiquettes') or 0) + acc['etiquettes'], 1)
            row['cartons'] = int(row.get('cartons') or 0) + acc['cartons']
            row['dossiers'] = int(row.get('dossiers') or 0) + len(acc['dossiers'])
        else:
            by_day.append({
                'key': jour,
                'dossiers': len(acc['dossiers']),
                'etiquettes': round(acc['etiquettes'], 1),
                'metrage_m': 0.0,
                'calage_min': 0.0,
                'prod_min': 0.0,
                'arret_min': 0.0,
                'vitesse_m_min': 0.0,
                'cartons': acc['cartons'],
            })
    by_day.sort(key=lambda x: (x.get('key') or ''), reverse=True)


def _is_machine_repiquage_name(name):
    n = str(name or '').lower().strip()
    n = (n.replace('e' + chr(0x301), 'e')  # combining acute on e
          .replace(chr(0xe9), 'e')
          .replace(chr(0xe8), 'e')
          .replace(chr(0xea), 'e'))
    return n == 'repiquage' or n == 'rep' or n.startswith('rep ') or n.startswith('repiquage')


@router.get("/api/production/machine-status")
def machine_status(request: Request):
    """
    Statut en temps réel des machines C1 et C2 basé sur les saisies de prod du jour.
    Accessible aux rôles avec vue globale MyProd (direction, commercial, expédition…).
    """
    user = get_current_user(request)
    if not can_view_all_prod(user):
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    now  = _dt_cls.now(_TZ_PARIS).replace(tzinfo=None)
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

        result[mkey] = {
            'nom':          machine_names[mkey],
            'statut_key':   status_key,
            'statut_label': status_label,
            'operateur':    operateur,
            'dossier':      dossier,
            'duree_min':    _compute_duree_min(status_key, rows_m, now),
        }

    # Carte DSI (placeholder)
    result['DSI'] = {
        'nom':          'DSI',
        'statut_key':   'en_dev',
        'statut_label': 'En cours de developpement',
        'operateur':    '',
        'dossier':      None,
        'duree_min':    None,
        'placeholder':  True,
    }

    # Carte Repiquage : dossiers du jour avec cartons cumules
    iso_today_rep = now.strftime('%Y-%m-%d')
    old_today_rep = now.strftime('%d/%m/%Y')
    rep_sql = (
        "SELECT pd.no_dossier, pd.client, pd.designation, "
        "COALESCE(SUM(pd.nb_cartons), 0) AS cartons "
        "FROM production_data pd "
        "WHERE pd.operation_code = '03' "
        "AND (lower(trim(COALESCE(pd.machine,''))) LIKE 'repiquage%' "
        "     OR lower(trim(COALESCE(pd.machine,''))) = 'rep' "
        "     OR lower(trim(COALESCE(pd.machine,''))) LIKE 'rep %') "
        "AND (pd.date_operation LIKE ? OR pd.date_operation LIKE ?) "
        "AND TRIM(COALESCE(pd.no_dossier,'')) != '' "
        "GROUP BY pd.no_dossier, pd.client, pd.designation "
        "HAVING cartons != 0 "
        "ORDER BY cartons DESC"
    )
    with get_db() as conn:
        rep_rows = conn.execute(rep_sql, (iso_today_rep + '%', old_today_rep + '%')).fetchall()
    rep_dossiers = []
    for r in rep_rows:
        rd = dict(r)
        client_raw = str(rd.get('client') or '').strip()
        rep_dossiers.append({
            'no_dossier': str(rd.get('no_dossier') or '').strip(),
            'client':     _clean_client(client_raw) if client_raw else '',
            'designation':(str(rd.get('designation') or '').strip().strip(',').strip()),
            'cartons':    int(rd.get('cartons') or 0),
        })
    total_cartons_rep = sum(int(d.get('cartons') or 0) for d in rep_dossiers)
    result['REP'] = {
        'nom':          'Repiquage',
        'statut_key':   'production' if rep_dossiers else 'eteinte',
        'statut_label': 'Atelier actif' if rep_dossiers else 'Aucune saisie aujourd' + chr(0x2019) + 'hui',
        'operateur':    '',
        'dossier':      None,
        'duree_min':    None,
        'dossiers_du_jour': rep_dossiers,
        'total_cartons':    total_cartons_rep,
    }

    return result

@router.get("/api/dashboard/production")
def dashboard_production(
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
    machines   = [m for m in (machine or []) if m]

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

    with get_db() as conn:
        if machines:
            append_machine_filter(where, params, conn, machines)
        wc = " AND ".join(where)
        completed = conn.execute(
            f"""SELECT no_dossier,operateur,machine,client,designation,
                       quantite_traitee,metrage_reel,metrage_prevu,date_operation
                FROM production_data
                WHERE {wc} AND operation_code='89'
                ORDER BY date_operation DESC""",
            params,
        ).fetchall()

        # Toutes les lignes pour calculs temps + métrages (+ nb_cartons pour Repiquage)
        # Tolerance : si la colonne nb_cartons n'existe pas encore (migration 114
        # non jouee sur le serveur), on utilise 0 par defaut.
        pd_cols = {r[1] for r in conn.execute('PRAGMA table_info(production_data)').fetchall()}
        nb_cartons_col = 'COALESCE(nb_cartons, 0) AS nb_cartons' if 'nb_cartons' in pd_cols else '0 AS nb_cartons'
        all_rows = conn.execute(
            f"""SELECT operateur,date_operation,operation_code,operation_category,
                       machine,no_dossier,client,designation,quantite_traitee,
                       {nb_cartons_col},
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
    #
    # Fallback (cas poste de nuit) : si aucun code-01 n'est trouvé dans la
    # fenêtre date filtrée, on requête le code-01 du même (operateur, dossier)
    # en dehors de la fenêtre, sans quoi le métrage produit serait calculé
    # comme `metrage_reel - 0`, ce qui prend tout le compteur cumulé machine.
    debut_entries = {}   # (op, dos) -> [(norm_dt_iso, compteur_debut_float), ...]
    fin_data      = {}   # (op, jour_iso, dos) -> {"metrage_m": float, "etiquettes": float}
    fallback_debut_ctr_cache: dict = {}  # (op, dos) -> float

    def _fallback_debut_ctr(op_key: str, dos_key: str, fin_dt_iso: str) -> float:
        """Cherche le compteur début du dossier dans production_data, sans
        filtre de date (sauf <= fin_dt). Utilisé seulement quand la fenêtre
        date filtrée ne contient pas le code-01 (production de nuit, etc.)."""
        cache_key = (op_key, dos_key)
        if cache_key in fallback_debut_ctr_cache:
            return fallback_debut_ctr_cache[cache_key]
        try:
            with get_db() as _conn:
                row = _conn.execute(
                    """SELECT COALESCE(metrage_total_debut, metrage_prevu) AS ctr
                       FROM production_data
                       WHERE operateur=? AND trim(no_dossier)=trim(?)
                         AND operation_code='01'
                         AND date_operation <= ?
                         AND COALESCE(metrage_total_debut, metrage_prevu) IS NOT NULL
                       ORDER BY date_operation DESC, id DESC LIMIT 1""",
                    (op_key, dos_key, fin_dt_iso),
                ).fetchone()
            ctr_val = float(row["ctr"]) if (row and row["ctr"] is not None) else 0.0
        except Exception:
            ctr_val = 0.0
        fallback_debut_ctr_cache[cache_key] = ctr_val
        return ctr_val

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
            if before:
                debut_ctr = sorted(before, reverse=True)[0][1]
            else:
                # Aucun 01 dans la fenêtre date : on va le chercher en DB
                # sans filtre — typique du poste de nuit (01 la veille, 89 le matin).
                debut_ctr = _fallback_debut_ctr(op, dos, fin_dt)

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

    # ── Totaux (excl. Repiquage qui ne contribue pas au metrage/temps) ─────
    _by_dos_for_totals = [d for d in by_dossier if not _is_machine_repiquage_name(d.get('machine') or '')]
    total_calage  = sum(float(d.get("temps_calage_min") or 0) for d in _by_dos_for_totals)
    total_prod    = sum(float(d.get("temps_prod_min")   or 0) for d in _by_dos_for_totals)
    total_arret   = sum(float(d.get("temps_arret_min")  or 0) for d in _by_dos_for_totals)

    metrage_total     = round(sum(float(d.get("metrage_m") or 0) for d in _by_dos_for_totals), 1)
    etiquettes_total  = round(sum(float(d.get("etiquettes") or 0) for d in _by_dos_for_totals), 1)
    nb_dossiers_total = len([d for d in _by_dos_for_totals if d.get("no_dossier")])

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

    # Variante by_dossier sans les saisies machine Repiquage
    # (utilisee pour by_operator non-Repiquage et les totaux haut de page)
    by_dossier_no_rep = [d for d in by_dossier if not _is_machine_repiquage_name(d.get('machine') or '')]

    # Sessions virtuelles Repiquage construites depuis les saisies code 03.
    # Robuste : on log et continue avec des listes vides si quelque chose plante
    # (ex. table rh_planning_postes pas encore migree, etc.)
    try:
        rep_dossier_sessions = _build_repiquage_dossier_rows(all_list)
    except Exception as _exc:
        _log.exception('_build_repiquage_dossier_rows failed: %s', _exc)
        rep_dossier_sessions = []
    by_dossier_with_rep = by_dossier_no_rep + rep_dossier_sessions

    by_operator = agg_key(by_dossier_no_rep, "operateur")
    try:
        rep_team_rows = _build_repiquage_team_rows(
            all_list, dossier_times, no_dossier_filter=dossiers
        )
    except Exception as _exc:
        _log.exception('_build_repiquage_team_rows failed: %s', _exc)
        rep_team_rows = []
    by_operator.extend(rep_team_rows)

    by_machine  = agg_key(by_dossier, "machine")
    try:
        rep_machine_row = _build_repiquage_machine_row(all_list)
    except Exception as _exc:
        _log.exception('_build_repiquage_machine_row failed: %s', _exc)
        rep_machine_row = None
    if rep_machine_row:
        by_machine = [m for m in by_machine if not _is_machine_repiquage_name(m.get('key'))]
        by_machine.append(rep_machine_row)
        by_machine = sorted(by_machine, key=lambda x: x.get('metrage_m', 0) + x.get('etiquettes', 0), reverse=True)

    by_day      = agg_key(by_dossier, "jour")
    try:
        _augment_by_day_with_repiquage(by_day, all_list)
    except Exception as _exc:
        _log.exception('_augment_by_day_with_repiquage failed: %s', _exc)

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
        "by_dossier":  sorted([d for d in by_dossier_with_rep if d.get("no_dossier")],
                               key=lambda x: x.get("temps_total_calage_min") or 0, reverse=True),
        "by_day": by_day,
    }
