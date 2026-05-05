"""SIFA — Planning v1.1 (standalone)

Planning autonome : les dossiers sont saisis manuellement.
Pas de lien vers la table dossiers.

Ajouter dans main.py :
    from routers.planning import router as planning_router
    app.include_router(planning_router)
"""

import unicodedata
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from database import get_db
from config import ROLE_FABRICATION, ROLE_DIRECTION, ROLE_SUPERADMIN
from services.auth_service import require_admin, get_current_user, user_has_app_access

_TZ_PARIS = ZoneInfo("Europe/Paris")

router = APIRouter(prefix="/api/planning", tags=["planning"])


def require_planning_view(request: Request) -> dict:
    """Accès lecture planning : selon rôle ou surcharge utilisateur."""
    user = get_current_user(request)
    if not user_has_app_access(user, "planning"):
        raise HTTPException(status_code=403, detail="Accès réservé au planning")
    return user


def _norm_key(val: Any) -> str:
    return str(val or "").strip().lower()


def _norm_search(val: Any) -> str:
    """Minuscule + suppression accents + trim (pour recherche multi-machines)."""
    s = str(val or "").strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return " ".join(s.split())


def _match_tokens(blob: str, tokens: list[str]) -> bool:
    if not tokens:
        return False
    b = _norm_search(blob)
    return all(t in b for t in tokens)


def fabrication_planning_machine_ids(conn, user: dict) -> set[int]:
    """Machines autorisées pour le rôle fabrication : saisies production + machine du profil."""
    ids: set[int] = set()
    mid_user = user.get("machine_id")
    if mid_user is not None:
        try:
            mid_i = int(mid_user)
        except (TypeError, ValueError):
            mid_i = None
        if mid_i is not None:
            row = conn.execute(
                "SELECT id FROM machines WHERE id=? AND actif=1",
                (mid_i,),
            ).fetchone()
            if row:
                ids.add(mid_i)

    op_key = _norm_key(user.get("operateur_lie"))
    if op_key:
        rows = conn.execute(
            """
            SELECT DISTINCT m.id
            FROM production_data pd
            JOIN machines m ON m.actif = 1
              AND pd.machine IS NOT NULL AND trim(pd.machine) != ''
              AND (
                lower(trim(pd.machine)) = lower(trim(m.nom))
                OR (
                  m.code IS NOT NULL AND trim(m.code) != ''
                  AND lower(trim(pd.machine)) = lower(trim(m.code))
                )
              )
            WHERE lower(trim(pd.operateur)) = ?
            """,
            (op_key,),
        ).fetchall()
        for r in rows:
            ids.add(int(r["id"]))
    return ids


def require_planning_machine(request: Request, conn, machine_id: int) -> dict:
    """Vérifie l’accès planning puis, pour la fabrication, que la machine est autorisée."""
    user = require_planning_view(request)
    if user.get("role") == ROLE_FABRICATION:
        allowed = fabrication_planning_machine_ids(conn, user)
        if machine_id not in allowed:
            raise HTTPException(status_code=403, detail="Accès non autorisé à cette machine")
    return user


def require_planning_edit(request: Request, conn, machine_id: int) -> dict:
    """Planning + machine : actions sensibles (reset saisie réelle) réservées direction / superadmin."""
    user = require_planning_machine(request, conn, machine_id)
    if user.get("role") not in (ROLE_SUPERADMIN, ROLE_DIRECTION):
        raise HTTPException(status_code=403, detail="Action réservée aux administrateurs.")
    return user


def compute_statut(entry: dict) -> str:
    """
    Calcule le statut automatique basé sur l'heure actuelle.
    Si statut_force=1 (posé par la saisie opérateur ou manuellement),
    le statut stocké en DB fait autorité — pas de recalcul par dates.
    Un dossier déjà « terminé » en colonne statut reste terminé même si le créneau
    planning a été invalidé (planned_* nuls) : sinon il disparaît des filtres UI / export.
    Sinon, si planned_start/planned_end existent, le statut est dérivé de ces dates.
    """
    if int(entry.get("statut_force") or 0) == 1:
        return entry.get("statut") or "attente"

    if (entry.get("statut") or "") == "termine":
        return "termine"

    start = entry.get("planned_start")
    end = entry.get("planned_end")
    st = _parse_planned_dt(start)
    en = _parse_planned_dt(end)
    if not st or not en:
        return "attente"

    now = datetime.now()
    if now > en:
        return "termine"
    if now >= st:
        return "en_cours"
    return "attente"


def _assert_not_locked(conn, machine_id: int, entry_id: int) -> None:
    """Empêche réordonnancement / déplacement d'un dossier en_cours ou terminé."""
    row = conn.execute(
        "SELECT statut, statut_force, planned_start, planned_end FROM planning_entries WHERE id=? AND machine_id=?",
        (entry_id, machine_id),
    ).fetchone()
    if not row:
        return
    statut_actuel = compute_statut(dict(row))
    if statut_actuel in ("en_cours", "termine"):
        raise HTTPException(400, "Ce dossier est verrouillé — statut en cours ou terminé")

_HORAIRES_COL = {
    "lundi": "horaires_lundi",
    "mardi": "horaires_mardi",
    "mercredi": "horaires_mercredi",
    "jeudi": "horaires_jeudi",
    "vendredi": "horaires_vendredi",
    "samedi": "horaires_samedi",
}


def _parse_horaires_val(val: Optional[str], default: str = "5,21") -> tuple[float, float]:
    """'5,21' ou '05:30,21:15' → (début, fin) en heures décimales depuis minuit."""
    raw = (val or "").strip() or default
    parts = raw.split(",", 1)
    if len(parts) != 2:
        parts = default.split(",", 1)

    def to_hours(x: str) -> float:
        x = str(x).strip()
        if ":" in x:
            hp = x.split(":", 1)
            h = int(hp[0])
            m = int(hp[1]) if len(hp) > 1 and hp[1].strip() != "" else 0
            return h + m / 60.0
        return float(int(x))

    try:
        a, b = to_hours(parts[0]), to_hours(parts[1])
        if b <= a:
            return to_hours(default.split(",", 1)[0]), to_hours(default.split(",", 1)[1])
        return a, b
    except (ValueError, IndexError):
        return _parse_horaires_val(None, default)


def _normalize_horaires_pair(start: str, end: str) -> str:
    def norm(t: str) -> str:
        t = t.strip()
        if ":" in t:
            h, m = t.split(":", 1)
            hi, mi = int(h), int(m)
        else:
            hi, mi = int(t), 0
        if not (0 <= hi <= 23 and 0 <= mi <= 59):
            raise ValueError("heure")
        return f"{hi:02d}:{mi:02d}"

    return f"{norm(start)},{norm(end)}"


def _fmt_ts(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _parse_planned_dt(val: Any) -> Optional[datetime]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    s = s.replace("Z", "").split("+")[0].strip()
    if len(s) == 10:
        s = f"{s}T00:00:00"
    elif "T" not in s and len(s) >= 16:
        s = s.replace(" ", "T", 1)
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        try:
            return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


def _auto_complete_en_cours(conn, machine_id: int) -> None:
    """Passe en 'termine' les dossiers en_cours dont planned_end est dépassé.
    Les dossiers avec statut_force=1 (posé par la saisie opérateur) sont ignorés :
    seul le code 89 (fin de production) peut les terminer."""
    now = datetime.now()
    now_s = _fmt_ts(now)
    rows = conn.execute(
        """SELECT id, planned_end FROM planning_entries
           WHERE machine_id=? AND statut='en_cours'
             AND planned_end IS NOT NULL
             AND COALESCE(statut_force, 0) = 0""",
        (machine_id,),
    ).fetchall()
    for r in rows:
        end = _parse_planned_dt(r["planned_end"])
        if end and end <= now:
            conn.execute(
                "UPDATE planning_entries SET statut='termine', updated_at=? WHERE id=?",
                (now_s, r["id"]),
            )


def _norm_prod_dossier(val: Any) -> str:
    return (str(val or "").strip().lower())


def _prod_run_start_for_machine(conn, machine_id: int, m: dict, no_dossier: str) -> Optional[datetime]:
    """Date de début du « run » actuel du dossier sur cette machine.

    Chronologie des saisies prod filtrées sur la machine : on prend le suffixe final où
    chaque ligne est le même no_dossier ; la date de début affichée est celle de la
    **première** saisie de ce suffixe (après le dernier autre dossier sur la machine).
    """
    ref = _norm_prod_dossier(no_dossier)
    if not ref:
        return None
    mnom = (m.get("nom") or "").strip()
    mcode = (m.get("code") or "").strip()
    if not mnom and not mcode:
        return None
    rows = conn.execute(
        """SELECT no_dossier, date_operation
           FROM production_data
           WHERE (trim(machine) = trim(?) OR (trim(?) != '' AND trim(machine) = trim(?)))
           ORDER BY date_operation ASC, id ASC""",
        (mnom, mcode, mcode),
    ).fetchall()
    if not rows:
        return None

    def row_ref(r: Any) -> str:
        return _norm_prod_dossier(r["no_dossier"])

    n = len(rows)
    last = n - 1
    while last >= 0 and row_ref(rows[last]) != ref:
        last -= 1
    if last < 0:
        return None
    first = last
    while first > 0 and row_ref(rows[first - 1]) == ref:
        first -= 1
    raw = rows[first]["date_operation"]
    if not raw:
        return None
    s = str(raw).strip()
    return _parse_prod_dt(s) or _parse_planned_dt(s)


def _enforce_single_en_cours(conn, machine_id: int) -> None:
    """Au plus une entrée avec statut DB 'en_cours' par machine (la plus haute dans la pile)."""
    rows = conn.execute(
        """SELECT id FROM planning_entries
           WHERE machine_id=? AND statut='en_cours' ORDER BY position ASC""",
        (machine_id,),
    ).fetchall()
    if len(rows) <= 1:
        return
    now_s = datetime.now().isoformat()
    for r in rows[1:]:
        conn.execute(
            """UPDATE planning_entries SET statut='attente', statut_force=0,
                   planned_start=NULL, planned_end=NULL, updated_at=?
               WHERE id=? AND machine_id=?""",
            (now_s, int(r["id"]), machine_id),
        )


def _is_frozen_entry(e: dict) -> bool:
    st = e.get("statut") or ""
    if st not in ("termine", "en_cours"):
        return False
    return bool(e.get("planned_start") and e.get("planned_end"))


def _invalidate_attente_plans(conn, machine_id: int) -> None:
    """Recalcule les créneaux « en attente » au prochain GET (réordre, ajout, durée, etc.)."""
    conn.execute(
        """UPDATE planning_entries SET planned_start=NULL, planned_end=NULL
           WHERE machine_id=? AND statut='attente'""",
        (machine_id,),
    )


def _normalize_str(s: str) -> str:
    nfkd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def _machine_key_from_record(m: dict) -> str:
    """Identifie la clé machine (C1/C2/DSI/REP) depuis le dict machine — miroir du JS machineKey()."""
    raw = str(m.get("code") or m.get("nom") or "").strip()
    norm = _normalize_str(raw)
    if "cohesio 2" in norm or norm == "c2":
        return "C2"
    if "cohesio 1" in norm or norm == "c1":
        return "C1"
    if "repiquage" in norm or norm == "rep":
        return "REP"
    if "dsi" in norm:
        return "DSI"
    return norm or raw


# Horaires paire/impaire — miroir exact du JS DEFAULTS_BY_KEY.
# Clés : (heure_début, heure_fin) en heures décimales depuis minuit.
_PARITY_DEFAULTS: Dict[str, Any] = {
    "C1":  {"pair": {"week": (5, 20), "fri": (7, 19)}, "impair": {"week": (5, 20), "fri": (7, 19)}},
    "C2":  {"pair": {"week": (5, 13), "fri": (6, 13)}, "impair": {"week": (13, 20), "fri": (14, 20)}},
    "DSI": {"pair": {"week": (8, 14), "fri": (8, 14)}, "impair": {"week": (8, 14), "fri": (8, 14)}},
    "REP": {"pair": {"week": (6, 20), "fri": (7, 19)}, "impair": {"week": (6, 20), "fri": (7, 19)}},
}


def _load_planning_calendar_maps(conn, machine_id: int) -> tuple[dict, dict, Dict[str, int]]:
    """Config semaines (samedi), fériés, jours travaillés — aligné sur GET /timeline."""
    configs: dict = {}
    today = datetime.now()
    for w in range(8):
        d = today + timedelta(weeks=w)
        sw = f"{d.year}-W{d.isocalendar()[1]:02d}"
        cfg = conn.execute(
            "SELECT samedi_travaille FROM planning_config WHERE machine_id=? AND semaine=?",
            (machine_id, sw),
        ).fetchone()
        configs[sw] = cfg["samedi_travaille"] if cfg else 0
    hol_rows = conn.execute(
        "SELECT date, is_off FROM planning_holidays WHERE machine_id=?",
        (machine_id,),
    ).fetchall()
    off_days = {str(r["date"]): int(r["is_off"] or 0) for r in hol_rows}
    dw_rows = conn.execute(
        "SELECT date, is_worked FROM planning_day_worked WHERE machine_id=?",
        (machine_id,),
    ).fetchall()
    day_worked_map = {str(r["date"]): int(r["is_worked"] or 0) for r in dw_rows}
    return configs, off_days, day_worked_map


def _make_work_duration_consumer(
    m: dict, configs: dict, off_days: dict, day_worked_map: Dict[str, int]
) -> tuple[Any, Any]:
    """(advance_to_work, consume_duration_from) — duree_heures = heures ouvrées machine (même logique que la timeline)."""
    base_hours = {}
    for day_idx, field in [(0, "horaires_lundi"), (1, "horaires_mardi"),
                           (2, "horaires_mercredi"), (3, "horaires_jeudi"),
                           (4, "horaires_vendredi")]:
        base_hours[day_idx] = _parse_horaires_val(m.get(field), "5,21")

    sat_hours_t = _parse_horaires_val(m.get("horaires_samedi"), "6,18")

    mk = _machine_key_from_record(m)
    _parity_defs = _PARITY_DEFAULTS.get(mk)

    def _is_pair_week(dt: datetime) -> bool:
        return dt.isocalendar()[1] % 2 == 0

    def week_key(dt: datetime) -> str:
        return f"{dt.year}-W{dt.isocalendar()[1]:02d}"

    def get_hours_for_date(dt):
        dkey = dt.strftime("%Y-%m-%d")
        wd = dt.weekday()
        if wd <= 4 and int(off_days.get(dkey, 0) or 0):
            return None
        dw = day_worked_map.get(dkey)
        if wd in base_hours:
            if dw is not None and int(dw) == 0:
                return None
            if _parity_defs is not None:
                par = "pair" if _is_pair_week(dt) else "impair"
                slot = "fri" if wd == 4 else "week"
                h = _parity_defs[par][slot]
                return (h[0], h[1])
            return base_hours[wd]
        if wd == 5:
            if dw is None:
                if int(configs.get(week_key(dt), 0) or 0) == 0:
                    return None
                return sat_hours_t
            if int(dw) == 0:
                return None
            return sat_hours_t
        return None

    def advance_to_work(dt):
        for _ in range(366):
            win = get_hours_for_date(dt)
            if win:
                s, e = win
                sod = datetime(dt.year, dt.month, dt.day, 0, 0, 0, 0)
                start_dt = sod + timedelta(hours=s)
                end_dt = sod + timedelta(hours=e)
                if dt < start_dt:
                    return start_dt
                if dt < end_dt:
                    return dt.replace(microsecond=0)
            nd = datetime(dt.year, dt.month, dt.day) + timedelta(days=1)
            dt = nd.replace(hour=0, minute=0, second=0, microsecond=0)
        return dt

    def consume_duration_from(cursor: datetime, duree_heures: float):
        remaining = float(duree_heures)
        slot_start: Optional[datetime] = None
        while remaining > 1e-9:
            win = get_hours_for_date(cursor)
            if not win:
                cursor = datetime(cursor.year, cursor.month, cursor.day) + timedelta(days=1)
                cursor = cursor.replace(hour=0, minute=0, second=0, microsecond=0)
                cursor = advance_to_work(cursor)
                continue
            s, e = win
            sod = datetime(cursor.year, cursor.month, cursor.day, 0, 0, 0, 0)
            curf = (cursor - sod).total_seconds() / 3600.0
            if curf < s - 1e-9:
                cursor = sod + timedelta(hours=s)
                curf = s
            if slot_start is None:
                slot_start = cursor.replace(second=0, microsecond=0)
            avail = max(0.0, e - curf)
            if avail <= 1e-9:
                cursor = datetime(cursor.year, cursor.month, cursor.day) + timedelta(days=1)
                cursor = cursor.replace(hour=0, minute=0, second=0, microsecond=0)
                cursor = advance_to_work(cursor)
                continue
            used = min(remaining, avail)
            remaining -= used
            cursor = cursor + timedelta(hours=used)
            if remaining > 1e-9:
                cursor = datetime(cursor.year, cursor.month, cursor.day) + timedelta(days=1)
                cursor = cursor.replace(hour=0, minute=0, second=0, microsecond=0)
                cursor = advance_to_work(cursor)
            else:
                cursor = advance_to_work(cursor)
        if slot_start is None:
            slot_start = cursor.replace(second=0, microsecond=0)
        slot_end = cursor.replace(second=0, microsecond=0)
        return slot_start, slot_end, cursor

    return advance_to_work, consume_duration_from


def _planned_end_iso_for_machine(
    conn, machine_id: int, planned_start_iso: str, duree_h: float
) -> Optional[str]:
    """planned_end ISO : début + duree_h heures **ouvrées** selon calendrier machine."""
    m = conn.execute("SELECT * FROM machines WHERE id=?", (machine_id,)).fetchone()
    if not m:
        return None
    dt0 = _parse_planned_dt(planned_start_iso)
    if not dt0:
        return None
    try:
        cfgs, off, dw = _load_planning_calendar_maps(conn, machine_id)
        _, consume_from = _make_work_duration_consumer(dict(m), cfgs, off, dw)
        _, slot_end, _ = consume_from(dt0.replace(microsecond=0), float(duree_h))
        return _fmt_ts(slot_end)
    except Exception:
        return None


def _slot_payload(e: dict, start_iso: str, end_iso: str) -> dict:
    return {
        "entry_id": e["id"],
        "reference": e["reference"],
        "client": e["client"],
        "description": e["description"],
        "format_l": e["format_l"],
        "format_h": e["format_h"],
        "laize": e.get("laize"),
        "date_livraison": e.get("date_livraison"),
        "numero_of": e.get("numero_of"),
        "ref_produit": e.get("ref_produit"),
        "commentaire": e.get("commentaire"),
        "a_placer": e.get("a_placer", 0),
        "destockage": e.get("destockage") or "todo",
        "statut_reel": e.get("statut_reel") or "reellement_en_attente",
        "duree_heures": e["duree_heures"],
        # Un dossier terminé en DB reste terminé même si planned_end est dans le futur
        # (cas : durée modifiée → planned_end recalculé en heures ouvrées machine)
        "statut": (
            "termine"
            if (e.get("statut") == "termine")
            else compute_statut({**e, "planned_start": start_iso, "planned_end": end_iso})
        ),
        "notes": e["notes"],
        "start": start_iso,
        "end": end_iso,
    }


def _compute_timeline_slots(
    conn,
    machine_id: int,
    m: dict,
    configs: dict,
    off_days: dict,
    day_worked_map: Dict[str, int],
    entries: List[dict],
) -> List[dict]:
    """Calcule les créneaux : terminé / en cours figés ; en attente (et en_cours sans plan) dynamiques + persistés.

    day_worked_map : pour chaque date YYYY-MM-DD, is_worked 0/1. Samedi : sans ligne ou 0 = non travaillé ;
    lun–ven : sans ligne = ouvré selon horaires machine ; ligne 0 = forcé non travaillé.
    """
    advance_to_work, consume_duration_from = _make_work_duration_consumer(
        m, configs, off_days, day_worked_map
    )

    slots: List[dict] = []
    cursor = advance_to_work(datetime.now().replace(minute=0, second=0, microsecond=0))
    now_u = _fmt_ts(datetime.now())

    for e in entries:
        st = e.get("statut") or "attente"

        # ── Terminé figé : conserve ses dates, avance le curseur ──────────
        if st == "termine" and _is_frozen_entry(e):
            ps, pe = e["planned_start"], e["planned_end"]
            pend = _parse_planned_dt(pe)
            if pend:
                cursor = advance_to_work(pend)
            slots.append(_slot_payload(e, ps, pe))
            continue
        if st == "termine":
            continue

        # ── En cours figé : début prod = 1re saisie du run actuel du dossier sur la machine ─
        if st == "en_cours" and _is_frozen_entry(e):
            ref = (e.get("numero_of") or e.get("reference") or "").strip()
            run_start = _prod_run_start_for_machine(conn, machine_id, m, ref) if ref else None
            if run_start is not None:
                duree_h = float(e.get("duree_heures") or 0)
                p0 = run_start.replace(microsecond=0)
                ps = _fmt_ts(p0)
                _, pe_dt, _ = consume_duration_from(p0, duree_h)
                pe = _fmt_ts(pe_dt)
                if str(e.get("planned_start") or "") != ps or str(e.get("planned_end") or "") != pe:
                    conn.execute(
                        """UPDATE planning_entries SET planned_start=?, planned_end=?, updated_at=?
                           WHERE id=? AND machine_id=?""",
                        (ps, pe, now_u, e["id"], machine_id),
                    )
                    e["planned_start"], e["planned_end"] = ps, pe
            else:
                ps, pe = e["planned_start"], e["planned_end"]
            pend = _parse_planned_dt(pe)
            if pend:
                cursor = advance_to_work(pend)
            slots.append(_slot_payload(e, ps, pe))
            continue

        # ── Attente et en_cours sans dates : calcul dynamique depuis cursor
        slot_start, slot_end, cursor = consume_duration_from(cursor, e["duree_heures"])
        ps, pe = _fmt_ts(slot_start), _fmt_ts(slot_end)
        conn.execute(
            """UPDATE planning_entries SET planned_start=?, planned_end=?, updated_at=?
               WHERE id=? AND machine_id=?""",
            (ps, pe, now_u, e["id"], machine_id),
        )
        ee = {**e, "planned_start": ps, "planned_end": pe}
        slots.append(_slot_payload(ee, ps, pe))

    return slots


# ═══════════════════════════════════════════════════════════════
# MACHINES
# ═══════════════════════════════════════════════════════════════

@router.get("/machines")
def list_machines(request: Request):
    """Liste des machines actives (filtrée pour le rôle fabrication)."""
    user = require_planning_view(request)
    with get_db() as conn:
        if user.get("role") == ROLE_FABRICATION:
            allowed = fabrication_planning_machine_ids(conn, user)
            if not allowed:
                return []
            ph = ",".join("?" * len(allowed))
            rows = conn.execute(
                f"SELECT * FROM machines WHERE actif=1 AND id IN ({ph}) ORDER BY nom",
                tuple(allowed),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM machines WHERE actif=1 ORDER BY nom"
            ).fetchall()
    return [dict(r) for r in rows]


@router.get("/search")
def search_across_machines(
    request: Request,
    q: str = "",
    limit_per_machine: int = 3,
):
    """Recherche planning sur toutes les machines actives.

    Retour: [{machine_id, nom, count, sample_entry_ids:[...]}, ...]
    - Insensible à la casse et aux accents, et multi-mots (tous les tokens doivent matcher).
    - Filtré pour le rôle fabrication (machines autorisées).
    """
    user = require_planning_view(request)
    qt = _norm_search(q)
    tokens = [t for t in qt.split(" ") if t]
    if not tokens:
        return []

    with get_db() as conn:
        if user.get("role") == ROLE_FABRICATION:
            allowed = fabrication_planning_machine_ids(conn, user)
            if not allowed:
                return []
            ph = ",".join("?" * len(allowed))
            mrows = conn.execute(
                f"SELECT id, nom FROM machines WHERE actif=1 AND id IN ({ph}) ORDER BY nom",
                tuple(allowed),
            ).fetchall()
            erows = conn.execute(
                f"""
                SELECT id, machine_id, client, reference, numero_of, ref_produit, description
                FROM planning_entries
                WHERE machine_id IN ({ph})
                ORDER BY machine_id, id DESC
                """,
                tuple(allowed),
            ).fetchall()
        else:
            mrows = conn.execute(
                "SELECT id, nom FROM machines WHERE actif=1 ORDER BY nom"
            ).fetchall()
            erows = conn.execute(
                """
                SELECT id, machine_id, client, reference, numero_of, ref_produit, description
                FROM planning_entries
                ORDER BY machine_id, id DESC
                """
            ).fetchall()

    mnames = {int(r["id"]): (r["nom"] or "") for r in mrows}
    out: dict[int, dict] = {}
    for r in erows:
        mid = int(r["machine_id"])
        blob = " ".join(
            str(x or "")
            for x in (
                r["client"],
                r["reference"],
                r["numero_of"],
                r["ref_produit"],
                r["description"],
            )
        )
        if not _match_tokens(blob, tokens):
            continue
        if mid not in out:
            out[mid] = {
                "machine_id": mid,
                "nom": mnames.get(mid, ""),
                "count": 0,
                "sample_entry_ids": [],
            }
        out[mid]["count"] += 1
        if len(out[mid]["sample_entry_ids"]) < int(limit_per_machine):
            out[mid]["sample_entry_ids"].append(int(r["id"]))

    # Ne renvoyer que les machines où il y a un résultat, tri par nom.
    items = list(out.values())
    items.sort(key=lambda d: (d.get("nom") or ""))
    return items


@router.get("/summary")
def planning_summary(request: Request):
    """Diagnostic : total dossiers planning + répartition par machine (vérif local vs VPS)."""
    user = require_planning_view(request)
    from config import DB_PATH

    with get_db() as conn:
        if user.get("role") == ROLE_FABRICATION:
            allowed = fabrication_planning_machine_ids(conn, user)
            if not allowed:
                return {"planning_entries_total": 0, "per_machine": []}
            ph = ",".join("?" * len(allowed))
            total = conn.execute(
                f"SELECT COUNT(*) FROM planning_entries WHERE machine_id IN ({ph})",
                tuple(allowed),
            ).fetchone()[0]
            rows = conn.execute(
                f"""
                SELECT m.id AS machine_id, m.nom, COUNT(e.id) AS entries_count
                FROM machines m
                LEFT JOIN planning_entries e ON e.machine_id = m.id
                WHERE m.actif = 1 AND m.id IN ({ph})
                GROUP BY m.id, m.nom
                ORDER BY m.nom
                """,
                tuple(allowed),
            ).fetchall()
        else:
            total = conn.execute("SELECT COUNT(*) FROM planning_entries").fetchone()[0]
            rows = conn.execute(
                """
                SELECT m.id AS machine_id, m.nom, COUNT(e.id) AS entries_count
                FROM machines m
                LEFT JOIN planning_entries e ON e.machine_id = m.id
                WHERE m.actif = 1
                GROUP BY m.id, m.nom
                ORDER BY m.nom
                """
            ).fetchall()
    out: Dict[str, Any] = {
        "planning_entries_total": int(total),
        "per_machine": [dict(r) for r in rows],
    }
    if user.get("role") in {"direction", "administration"}:
        out["db_path"] = DB_PATH
    return out


@router.get("/machines/{machine_id}")
def get_machine(machine_id: int, request: Request):
    with get_db() as conn:
        require_planning_machine(request, conn, machine_id)
        row = conn.execute("SELECT * FROM machines WHERE id=?", (machine_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Machine non trouvée")
    return dict(row)


@router.put("/machines/{machine_id}/horaires")
async def set_machine_horaires(machine_id: int, request: Request):
    """Modifier les heures d'ouverture d'un jour : body { day: lundi|…|samedi, start, end } en HH:MM."""
    require_admin(request)
    body = await request.json()
    day = (body.get("day") or "").lower().strip()
    if day not in _HORAIRES_COL:
        raise HTTPException(400, "day invalide (lundi … samedi)")
    start = (body.get("start") or "").strip()
    end = (body.get("end") or "").strip()
    if not start or not end:
        raise HTTPException(400, "start et end requis (HH:MM)")
    try:
        val = _normalize_horaires_pair(start, end)
        hs, he = _parse_horaires_val(val, "0,1")
    except ValueError:
        raise HTTPException(400, "Format heure invalide")
    if he <= hs:
        raise HTTPException(400, "La fin doit être après le début")
    col = _HORAIRES_COL[day]
    with get_db() as conn:
        ex = conn.execute("SELECT id FROM machines WHERE id=?", (machine_id,)).fetchone()
        if not ex:
            raise HTTPException(404, "Machine non trouvée")
        conn.execute(f"UPDATE machines SET {col} = ? WHERE id = ?", (val, machine_id))
        _invalidate_attente_plans(conn, machine_id)
        conn.commit()
    return {"success": True, "field": col, "value": val}


@router.put("/machines/{machine_id}/horaires-bulk")
async def set_machine_horaires_bulk(machine_id: int, request: Request):
    """Modifier plusieurs horaires_* en une fois.

    Body: { horaires_lundi: "HH:MM,HH:MM", ..., horaires_samedi: "HH:MM,HH:MM" }
    """
    require_admin(request)
    body = await request.json()
    if not isinstance(body, dict) or not body:
        raise HTTPException(400, "Body invalide")

    allowed = set(_HORAIRES_COL.values())
    updates: Dict[str, str] = {}
    for k, v in body.items():
        if k not in allowed:
            continue
        raw = (v or "").strip()
        if not raw:
            continue
        # Valider/normaliser: "HH:MM,HH:MM"
        try:
            start, end = raw.split(",", 1)
            val = _normalize_horaires_pair(start, end)
            hs, he = _parse_horaires_val(val, "0,1")
        except Exception:
            raise HTTPException(400, f"Horaire invalide: {k}")
        if he <= hs:
            raise HTTPException(400, f"Horaire invalide (fin<=début): {k}")
        updates[k] = val

    if not updates:
        raise HTTPException(400, "Aucun champ horaires_* à mettre à jour")

    with get_db() as conn:
        ex = conn.execute("SELECT id FROM machines WHERE id=?", (machine_id,)).fetchone()
        if not ex:
            raise HTTPException(404, "Machine non trouvée")
        sets = ", ".join([f"{col}=?" for col in updates.keys()])
        conn.execute(f"UPDATE machines SET {sets} WHERE id=?", (*updates.values(), machine_id))
        _invalidate_attente_plans(conn, machine_id)
        conn.commit()
    return {"success": True, "updated": updates}


# ═══════════════════════════════════════════════════════════════
# PLANNING ENTRIES — CRUD
# ═══════════════════════════════════════════════════════════════

@router.get("/machines/{machine_id}/entries")
def list_entries(machine_id: int, request: Request):
    with get_db() as conn:
        user = require_planning_machine(request, conn, machine_id)
        if user.get("role") == ROLE_FABRICATION:
            raise HTTPException(
                status_code=403,
                detail="Liste des dossiers réservée à l'administration",
            )
        _auto_complete_en_cours(conn, machine_id)
        _enforce_single_en_cours(conn, machine_id)
        conn.commit()
        rows = conn.execute("""
            SELECT * FROM planning_entries
            WHERE machine_id = ?
            ORDER BY position ASC
        """, (machine_id,)).fetchall()
    entries = []
    for r in rows:
        e = dict(r)
        e["statut"] = compute_statut(e)
        entries.append(e)
    return entries


@router.put("/machines/{machine_id}/entries/{entry_id}/statut")
async def force_statut(machine_id: int, entry_id: int, request: Request):
    """Forcer un statut depuis la liste. Direction / superadmin : transitions flexibles."""
    require_admin(request)
    user = get_current_user(request)
    body = await request.json()
    statut = body.get("statut", "attente")
    override = bool(body.get("override", False))

    if statut not in ("attente", "en_cours", "termine"):
        raise HTTPException(status_code=400, detail="Statut invalide.")

    is_flex = user.get("role") in (ROLE_SUPERADMIN, ROLE_DIRECTION)

    with get_db() as conn:
        require_planning_machine(request, conn, machine_id)
        row = conn.execute(
            """SELECT id, reference, statut, statut_reel, planned_start, planned_end
               FROM planning_entries WHERE id = ? AND machine_id = ?""",
            (entry_id, machine_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entrée introuvable.")

        current_reel = row["statut_reel"] or "reellement_en_attente"

        if not is_flex and current_reel != "reellement_en_attente":
            raise HTTPException(
                status_code=409,
                detail="Statut verrouillé par la saisie de production.",
            )

        if current_reel == "reellement_termine" and statut != "termine":
            raise HTTPException(
                status_code=409,
                detail="Ce dossier est clôturé en production. Utiliser « Réinitialiser la saisie » pour le rouvrir.",
            )

        saisie_found = False
        if statut == "termine" and row["statut"] != "termine":
            reference = (row["reference"] or "").strip()
            if reference:
                saisie_row = conn.execute(
                    """SELECT id FROM production_data
                       WHERE no_dossier = ?
                       ORDER BY date_operation DESC LIMIT 1""",
                    (reference,),
                ).fetchone()
                saisie_found = saisie_row is not None

            if not saisie_found and not override:
                return JSONResponse(
                    status_code=200,
                    content={
                        "warning": True,
                        "code": "NO_SAISIE",
                        "message": "Aucune saisie de production trouvée pour ce dossier. Continuer quand même ?",
                    },
                )

        new_reel = current_reel
        if statut == "attente":
            new_reel = "reellement_en_attente"
        elif statut == "en_cours":
            if current_reel == "reellement_en_attente":
                new_reel = "reellement_en_saisie"
        elif statut == "termine":
            if current_reel in ("reellement_en_attente", "reellement_en_saisie"):
                new_reel = "reellement_termine" if (saisie_found or override) else current_reel

        now_iso = datetime.now().isoformat()
        conn.execute(
            """UPDATE planning_entries
               SET statut       = ?,
                   statut_force = 1,
                   statut_reel  = ?,
                   updated_at   = ?
               WHERE id = ? AND machine_id = ?""",
            (statut, new_reel, now_iso, entry_id, machine_id),
        )
        if statut == "attente":
            _invalidate_attente_plans(conn, machine_id)
        conn.commit()

    return {"ok": True, "saisie_found": saisie_found}


@router.post("/machines/{machine_id}/entries")
async def add_entry(machine_id: int, request: Request):
    """Ajouter un dossier manuellement au planning."""
    require_admin(request)
    body = await request.json()
    reference = body.get("reference", "").strip()
    if not reference:
        raise HTTPException(400, "Référence requise")

    duree = body.get("duree_heures", 8)
    if duree < 0.75 or duree > 720:
        raise HTTPException(400, "Durée entre 0,75 et 720 heures")

    # Récupérer l'utilisateur courant pour la traçabilité
    user = get_current_user(request)
    user_name = user.get("nom") or user.get("email") or "Admin"

    now = datetime.now().isoformat()
    with get_db() as conn:
        # Vérifier que la machine existe
        mac = conn.execute("SELECT id FROM machines WHERE id=?", (machine_id,)).fetchone()
        if not mac:
            raise HTTPException(404, "Machine non trouvée")

        # Position : soit spécifiée, soit en fin de file
        position = body.get("position")
        if position is None:
            max_pos = conn.execute(
                "SELECT COALESCE(MAX(position),0) FROM planning_entries WHERE machine_id=?",
                (machine_id,)
            ).fetchone()[0]
            position = max_pos + 1
        else:
            # Décaler les entrées existantes pour faire de la place
            conn.execute(
                "UPDATE planning_entries SET position = position + 1 WHERE machine_id=? AND position >= ?",
                (machine_id, position)
            )

        conn.execute("""
            INSERT INTO planning_entries
                (machine_id, position, reference, client, description, format_l, format_h,
                 duree_heures, statut, notes, created_at, updated_at,
                 dos_rvgi, numero_of, ref_produit, laize, date_livraison, commentaire, a_placer,
                 created_by, updated_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            machine_id, position,
            reference,
            body.get("client", ""),
            body.get("description", ""),
            body.get("format_l"),
            body.get("format_h"),
            duree,
            body.get("statut", "attente"),
            body.get("notes", ""),
            now, now,
            (body.get("dos_rvgi") or "").strip() or None,
            body.get("numero_of"),
            body.get("ref_produit"),
            body.get("laize"),
            body.get("date_livraison"),
            body.get("commentaire"),
            body.get("a_placer", 1),
            user_name,
            user_name,
        ))
        _invalidate_attente_plans(conn, machine_id)
        conn.commit()

    return {"success": True, "position": position}


@router.put("/machines/{machine_id}/entries/{entry_id}")
async def update_entry(machine_id: int, entry_id: int, request: Request):
    """Modifier une entrée du planning (durée, format, statut, notes)."""
    require_admin(request)
    body = await request.json()
    now = datetime.now().isoformat()

    duree_raw = body.get("duree_heures")
    duree: Optional[float] = None
    if duree_raw is not None:
        try:
            duree = float(duree_raw)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Durée invalide")
        if duree < 0.75 or duree > 720:
            raise HTTPException(status_code=400, detail="Durée entre 0,75 et 720 heures")

    # Récupérer l'utilisateur courant pour la traçabilité
    user = get_current_user(request)
    user_name = user.get("nom") or user.get("email") or "Admin"

    with get_db() as conn:
        ex = conn.execute(
            "SELECT * FROM planning_entries WHERE id=? AND machine_id=?",
            (entry_id, machine_id)
        ).fetchone()
        if not ex:
            raise HTTPException(404, "Entrée non trouvée")

        exd = dict(ex)
        statut_auto = compute_statut(exd)
        if (
            exd.get("statut") == "attente"
            and duree is not None
            and float(duree) != float(ex["duree_heures"])
        ):
            _invalidate_attente_plans(conn, machine_id)
        new_statut = body.get("statut", exd["statut"])
        clear_plan = new_statut == "attente" and exd.get("statut") in ("en_cours", "termine")
        if clear_plan:
            _invalidate_attente_plans(conn, machine_id)
        invalidate_dur = (
            exd.get("statut") == "attente"
            and duree is not None
            and float(duree) != float(ex["duree_heures"])
        )
        termine_reposition = (
            not clear_plan
            and not invalidate_dur
            and exd.get("statut") == "termine"
            and body.get("planned_start") is not None
            and body.get("planned_end") is not None
        )

        if clear_plan or invalidate_dur:
            ps = None
            pe = None
        elif termine_reposition:
            ps_dt = _parse_planned_dt(body.get("planned_start"))
            pe_dt = _parse_planned_dt(body.get("planned_end"))
            if not ps_dt or not pe_dt:
                raise HTTPException(
                    status_code=400,
                    detail="planned_start / planned_end invalides.",
                )
            if pe_dt <= ps_dt:
                raise HTTPException(
                    status_code=400,
                    detail="Intervalle planifié invalide (fin avant ou égale au début).",
                )
            ps = _fmt_ts(ps_dt)
            pe = _fmt_ts(pe_dt)
        else:
            ps = exd.get("planned_start")
            pe = exd.get("planned_end")

        # Recalcul simple de fin de créneau si seule la durée change (ancrage inchangé)
        if (
            not termine_reposition
            and duree is not None
            and float(duree) != float(ex["duree_heures"])
            and exd.get("planned_start")
            and not clear_plan
            and not invalidate_dur
        ):
            dt_start = _parse_planned_dt(exd["planned_start"])
            if dt_start:
                ps = exd.get("planned_start")
                pe_w = _planned_end_iso_for_machine(conn, machine_id, str(ps), float(duree))
                pe = pe_w or (dt_start + timedelta(hours=float(duree))).strftime("%Y-%m-%dT%H:%M:%S")

        old_ps = exd.get("planned_start")
        statut_reel_actuel = exd.get("statut_reel") or "reellement_en_attente"
        if statut_reel_actuel != "reellement_en_attente" and not termine_reposition:
            if old_ps and ps and str(ps) != str(old_ps):
                raise HTTPException(
                    status_code=409,
                    detail="Impossible de déplacer ce dossier : une saisie de production est en cours ou terminée.",
                )

        conn.execute("""
            UPDATE planning_entries
            SET reference=?, client=?, description=?, format_l=?, format_h=?,
                duree_heures=?, statut=?, notes=?, updated_at=?, updated_by=?,
                dos_rvgi=?, numero_of=?, ref_produit=?, laize=?, date_livraison=?, commentaire=?,
                planned_start=?, planned_end=?, a_placer=?
            WHERE id=?
        """, (
            body.get("reference", ex["reference"]),
            body.get("client", ex["client"]),
            body.get("description", ex["description"]),
            body.get("format_l", ex["format_l"]),
            body.get("format_h", ex["format_h"]),
            float(body.get("duree_heures", ex["duree_heures"]))
            if body.get("duree_heures") is not None
            else ex["duree_heures"],
            new_statut,
            body.get("notes", ex["notes"]),
            now,
            user_name,
            (body.get("dos_rvgi") or "").strip() or None,
            body.get("numero_of", ex["numero_of"] if "numero_of" in ex.keys() else None),
            body.get("ref_produit", ex["ref_produit"] if "ref_produit" in ex.keys() else None),
            body.get("laize", ex["laize"] if "laize" in ex.keys() else None),
            body.get("date_livraison", ex["date_livraison"] if "date_livraison" in ex.keys() else None),
            body.get("commentaire", ex["commentaire"] if "commentaire" in ex.keys() else None),
            ps,
            pe,
            body.get("a_placer", ex["a_placer"] if "a_placer" in ex.keys() else 0),
            entry_id
        ))
        conn.commit()
    return {"success": True}


@router.put("/machines/{machine_id}/entries/{entry_id}/destockage")
async def toggle_destockage(machine_id: int, entry_id: int, request: Request):
    """Bascule le flag destockage (todo ↔ done) d'un dossier."""
    require_admin(request)
    now = datetime.now().isoformat()
    with get_db() as conn:
        ex = conn.execute(
            "SELECT destockage FROM planning_entries WHERE id=? AND machine_id=?",
            (entry_id, machine_id)
        ).fetchone()
        if not ex:
            raise HTTPException(404, "Entrée non trouvée")
        cur = ex["destockage"] or "todo"
        new_val = "todo" if cur == "done" else "done"
        conn.execute(
            "UPDATE planning_entries SET destockage=?, updated_at=? WHERE id=? AND machine_id=?",
            (new_val, now, entry_id, machine_id)
        )
        conn.commit()
    return {"success": True, "destockage": new_val}


@router.post("/machines/{machine_id}/entries/{entry_id}/reset-saisie")
async def reset_statut_reel(machine_id: int, entry_id: int, request: Request):
    """
    Remet statut_reel à reellement_en_attente.
    Réservé aux rôles superadmin et direction.
    Bloqué si dossier définitivement clôturé (statut + saisie réelle terminés).
    """
    with get_db() as conn:
        require_planning_edit(request, conn, machine_id)
        row = conn.execute(
            "SELECT id, statut, statut_reel FROM planning_entries WHERE id=? AND machine_id=?",
            (entry_id, machine_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entrée introuvable.")
        if (row["statut_reel"] or "") == "reellement_termine":
            raise HTTPException(
                status_code=409,
                detail="Dossier définitivement clôturé — reset impossible.",
            )
        now = datetime.now().isoformat()
        conn.execute(
            """UPDATE planning_entries
               SET statut_reel   = 'reellement_en_attente',
                   statut        = 'attente',
                   statut_force  = 0,
                   planned_start = NULL,
                   planned_end   = NULL,
                   updated_at    = ?
               WHERE id = ? AND machine_id = ?""",
            (now, entry_id, machine_id),
        )
        _invalidate_attente_plans(conn, machine_id)
        conn.commit()
    return {"ok": True}


@router.post("/machines/{machine_id}/entries/{entry_id}/split")
def split_entry(machine_id: int, entry_id: int, request: Request):
    """Duplique un dossier en 2 dossiers consécutifs (mêmes infos), durée /2.

    Si la durée n'est pas divisible par 2 :
    - 1er dossier = arrondi supérieur
    - 2e dossier  = arrondi inférieur
    """
    require_admin(request)
    now = datetime.now().isoformat()
    with get_db() as conn:
        ex = conn.execute(
            "SELECT * FROM planning_entries WHERE id=? AND machine_id=?",
            (entry_id, machine_id),
        ).fetchone()
        if not ex:
            raise HTTPException(404, "Entrée non trouvée")
        exd = dict(ex)
        statut_auto = compute_statut(exd)
        if statut_auto in ("en_cours", "termine"):
            raise HTTPException(400, "Ce dossier est verrouillé — statut en cours ou terminé")

        # Durées (heures) : on split sur un entier (UI) → mais on garde robuste
        try:
            d = float(exd.get("duree_heures") or 0.0)
        except Exception:
            d = 0.0
        if d < 2 or d > 720:
            raise HTTPException(400, "Durée invalide (2..720h)")

        # Règle de split : ceil / floor, somme = d si d entier
        import math

        d1 = float(math.ceil(d / 2.0))
        d2 = float(math.floor(d / 2.0))
        if d1 < 2:
            d1 = 2.0
        if d2 < 2:
            # Si d=3 → d2=1 => on force 2 et on réduit d1 pour garder total
            d2 = 2.0
            d1 = max(2.0, d - d2)

        # Insérer un duplicat juste après (position+1)
        pos = int(exd.get("position") or 1)
        new_position = pos + 1
        conn.execute(
            "UPDATE planning_entries SET position = position + 1 WHERE machine_id=? AND position >= ?",
            (machine_id, new_position),
        )

        # Mettre à jour la durée du premier (entry_id)
        group_id = str(exd.get("group_id") or "").strip() or str(entry_id)
        # S'assurer que l'entrée source a bien un group_id stable (utilisé par Rentabilité pour regrouper un split)
        conn.execute(
            """UPDATE planning_entries
               SET duree_heures=?, updated_at=?, planned_start=NULL, planned_end=NULL, group_id=?
               WHERE id=? AND machine_id=?""",
            (d1, now, group_id, entry_id, machine_id),
        )

        # Dupliquer la ligne
        cols = [
            "reference", "client", "description", "format_l", "format_h",
            "dos_rvgi", "numero_of", "ref_produit", "laize", "date_livraison", "commentaire",
            "notes",
        ]
        payload = {c: exd.get(c) for c in cols}
        conn.execute(
            """INSERT INTO planning_entries
               (machine_id, position, reference, client, description, format_l, format_h,
                dos_rvgi, duree_heures, statut, notes, created_at, updated_at,
                numero_of, ref_produit, laize, date_livraison, commentaire)
               VALUES (?,?,?,?,?,?,?,?,?,'attente',?,?,?,?,?,?,?,?)""",
            (
                machine_id,
                new_position,
                payload.get("reference") or "",
                payload.get("client") or "",
                payload.get("description") or "",
                payload.get("format_l"),
                payload.get("format_h"),
                payload.get("dos_rvgi"),
                d2,
                payload.get("notes") or "",
                now,
                now,
                payload.get("numero_of"),
                payload.get("ref_produit"),
                payload.get("laize"),
                payload.get("date_livraison"),
                payload.get("commentaire"),
            ),
        )
        # Assigner group_id identique + split_parent_id sur la nouvelle entrée
        new_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        try:
            conn.execute(
                "UPDATE planning_entries SET group_id=?, split_parent_id=? WHERE id=? AND machine_id=?",
                (group_id, entry_id, int(new_id), machine_id),
            )
        except Exception:
            pass

        _invalidate_attente_plans(conn, machine_id)
        conn.commit()
    return {"success": True, "split": [d1, d2]}


@router.delete("/machines/{machine_id}/entries/{entry_id}")
def delete_entry(machine_id: int, entry_id: int, request: Request):
    """Supprimer une entrée et recompacter les positions.
    Si l'entrée supprimée était en_cours, le premier dossier attente suivant est promu en_cours.
    """
    require_admin(request)
    with get_db() as conn:
        ex = conn.execute(
            """SELECT id, position, statut, statut_force, planned_start, planned_end
               FROM planning_entries WHERE id=? AND machine_id=?""",
            (entry_id, machine_id)
        ).fetchone()
        if not ex:
            raise HTTPException(404, "Entrée non trouvée")

        was_en_cours = (compute_statut(dict(ex)) == "en_cours")

        conn.execute("DELETE FROM planning_entries WHERE id=?", (entry_id,))
        conn.execute(
            "UPDATE planning_entries SET position = position - 1 WHERE machine_id=? AND position > ?",
            (machine_id, ex["position"])
        )
        _invalidate_attente_plans(conn, machine_id)

        # Si le dossier supprimé était en cours, promouvoir le premier dossier en attente.
        if was_en_cours:
            next_e = conn.execute(
                """SELECT id FROM planning_entries
                   WHERE machine_id=? AND statut='attente'
                   ORDER BY position ASC LIMIT 1""",
                (machine_id,),
            ).fetchone()
            if next_e:
                conn.execute(
                    """UPDATE planning_entries
                       SET statut='en_cours', statut_force=1,
                           planned_start=NULL, planned_end=NULL, updated_at=?
                       WHERE id=?""",
                    (_fmt_ts(datetime.now()), next_e["id"]),
                )

        conn.commit()
    return {"success": True}


# ═══════════════════════════════════════════════════════════════
# DOSSIERS ORPHELINS (saisis en prod mais absents du planning)
# ═══════════════════════════════════════════════════════════════

@router.get("/machines/{machine_id}/orphan-dossiers")
def list_orphan_dossiers(machine_id: int, request: Request):
    """Liste les dossiers saisis en production (code 01) sur cette machine
    qui ne sont pas encore reliés à une entrée du planning."""
    require_admin(request)
    with get_db() as conn:
        mac = conn.execute("SELECT id, nom, code FROM machines WHERE id=?", (machine_id,)).fetchone()
        if not mac:
            raise HTTPException(404, "Machine non trouvée")
        mnom = mac["nom"] or ""
        mcode = mac["code"] or ""

        rows = conn.execute(
            """SELECT pd.no_dossier,
                      pd.client,
                      pd.designation,
                      MIN(CASE WHEN pd.operation_code='01' THEN pd.date_operation END) AS first_start,
                      MAX(CASE WHEN pd.operation_code='89' THEN pd.date_operation END) AS last_end,
                      pd.operateur
               FROM production_data pd
               WHERE pd.no_dossier IS NOT NULL
                 AND pd.no_dossier != ''
                 AND (pd.machine = ? OR pd.machine = ?)
                 AND pd.no_dossier NOT IN (
                     SELECT pe.reference FROM planning_entries pe WHERE pe.machine_id = ?
                 )
               GROUP BY pd.no_dossier
               HAVING MIN(CASE WHEN pd.operation_code='01' THEN pd.date_operation END) IS NOT NULL
               ORDER BY first_start DESC""",
            (mnom, mcode, machine_id),
        ).fetchall()

    result = []
    for r in rows:
        d = dict(r)
        elapsed = None
        if d["first_start"] and d["last_end"]:
            try:
                dt_s = datetime.fromisoformat(d["first_start"])
                dt_e = datetime.fromisoformat(d["last_end"])
                elapsed = round((dt_e - dt_s).total_seconds() / 3600, 2)
            except Exception:
                pass
        d["duree_reelle"] = elapsed
        d["has_end"] = d["last_end"] is not None
        result.append(d)

    return {"dossiers": result}


@router.post("/machines/{machine_id}/import-orphan")
async def import_orphan_dossier(machine_id: int, request: Request):
    """Importe un dossier orphelin (saisi en prod) dans le planning avec ses dates réelles."""
    require_admin(request)
    body = await request.json()
    no_dossier = (body.get("no_dossier") or "").strip()
    if not no_dossier:
        raise HTTPException(400, "Référence dossier requise")

    user = get_current_user(request)
    user_name = user.get("nom") or user.get("email") or "Admin"
    now = datetime.now().isoformat()

    with get_db() as conn:
        mac = conn.execute("SELECT id, nom, code FROM machines WHERE id=?", (machine_id,)).fetchone()
        if not mac:
            raise HTTPException(404, "Machine non trouvée")

        existing = conn.execute(
            "SELECT id FROM planning_entries WHERE reference=? AND machine_id=?",
            (no_dossier, machine_id),
        ).fetchone()
        if existing:
            raise HTTPException(400, "Ce dossier est déjà au planning")

        mnom = mac["nom"] or ""
        mcode = mac["code"] or ""

        prod_rows = conn.execute(
            """SELECT operation_code, date_operation, client, designation,
                      metrage_total_debut, metrage_total_fin
               FROM production_data
               WHERE no_dossier = ? AND (machine = ? OR machine = ?)
               ORDER BY date_operation ASC""",
            (no_dossier, mnom, mcode),
        ).fetchall()
        if not prod_rows:
            raise HTTPException(404, "Aucune saisie trouvée pour ce dossier sur cette machine")

        client = ""
        first_start = None
        last_end = None
        for pr in prod_rows:
            p = dict(pr)
            if not client and p.get("client"):
                client = p["client"]
            if p["operation_code"] == "01" and p["date_operation"]:
                if first_start is None:
                    first_start = p["date_operation"]
            if p["operation_code"] == "89" and p["date_operation"]:
                last_end = p["date_operation"]

        duree = 8.0
        statut = "en_cours"
        statut_reel = "reellement_en_saisie"
        planned_end = None

        if first_start and last_end:
            try:
                dt_s = datetime.fromisoformat(first_start)
                dt_e = datetime.fromisoformat(last_end)
                duree = max(1.0, round((dt_e - dt_s).total_seconds() / 3600, 2))
            except Exception:
                pass
            statut = "termine"
            statut_reel = "reellement_termine"
            planned_end = last_end
        elif first_start:
            planned_end = _planned_end_iso_for_machine(conn, machine_id, first_start, float(duree))
            if not planned_end:
                planned_end = (
                    datetime.fromisoformat(first_start) + timedelta(hours=duree)
                ).strftime("%Y-%m-%dT%H:%M:%S")

        # Position : insérer parmi les terminés existants (avant le premier non-terminé)
        rows_pos = conn.execute(
            """SELECT id, position, statut, statut_force, planned_start, planned_end
               FROM planning_entries WHERE machine_id=? ORDER BY position ASC""",
            (machine_id,),
        ).fetchall()

        insert_pos = 0
        for rp in rows_pos:
            rpd = dict(rp)
            st = compute_statut(rpd)
            if st == "termine":
                insert_pos = rpd["position"] + 1
            else:
                break

        if not rows_pos:
            insert_pos = 1
        elif insert_pos == 0:
            insert_pos = 1

        conn.execute(
            "UPDATE planning_entries SET position = position + 1 WHERE machine_id=? AND position >= ?",
            (machine_id, insert_pos),
        )

        conn.execute("""
            INSERT INTO planning_entries
                (machine_id, position, reference, client, description,
                 duree_heures, statut, statut_reel, statut_force,
                 planned_start, planned_end,
                 created_at, updated_at, created_by, updated_by,
                 numero_of, a_placer)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            machine_id, insert_pos,
            no_dossier, client, "",
            duree, statut, statut_reel,
            first_start, planned_end,
            now, now, user_name, user_name,
            no_dossier,
        ))
        _invalidate_attente_plans(conn, machine_id)
        conn.commit()

    return {"success": True, "statut": statut, "duree": duree}


# ═══════════════════════════════════════════════════════════════
# RÉORDONNER (drag & drop)
# ═══════════════════════════════════════════════════════════════

@router.post("/machines/{machine_id}/reorder")
async def reorder_entries(machine_id: int, request: Request):
    """Réordonner les entrées. Body: {"entry_ids": [5, 3, 8, 1, ...]}"""
    require_admin(request)
    body = await request.json()
    entry_ids = body.get("entry_ids", [])
    if not entry_ids:
        raise HTTPException(400, "entry_ids requis (liste ordonnée)")

    now = datetime.now().isoformat()
    with get_db() as conn:
        # Autoriser le reorder même si des entrées sont verrouillées,
        # à condition que les entrées verrouillées (en_cours/termine) restent
        # exactement à la même position (index) dans la liste.
        rows = conn.execute(
            """SELECT id, statut, statut_force, planned_start, planned_end
               FROM planning_entries
               WHERE machine_id=?
               ORDER BY position ASC""",
            (machine_id,),
        ).fetchall()
        cur_ids = [int(r["id"]) for r in rows]
        wanted_ids = [int(x) for x in entry_ids]

        if set(wanted_ids) != set(cur_ids) or len(wanted_ids) != len(cur_ids):
            raise HTTPException(400, "entry_ids doit contenir toutes les entrées de la machine")

        locked_pos = {}
        for idx, r in enumerate(rows):
            st = compute_statut(dict(r))
            if st in ("en_cours", "termine"):
                locked_pos[int(r["id"])] = idx

        wanted_index = {eid: i for i, eid in enumerate(wanted_ids)}
        for eid, old_idx in locked_pos.items():
            if wanted_index.get(eid) != old_idx:
                raise HTTPException(400, "Impossible de déplacer un dossier en cours/terminé")

        for pos, eid in enumerate(entry_ids, start=1):
            conn.execute(
                "UPDATE planning_entries SET position=?, updated_at=? WHERE id=? AND machine_id=?",
                (pos, now, eid, machine_id)
            )
        _invalidate_attente_plans(conn, machine_id)
        conn.commit()
    return {"success": True, "count": len(entry_ids)}


# ═══════════════════════════════════════════════════════════════
# INSÉRER UN DOSSIER APRÈS UNE POSITION
# ═══════════════════════════════════════════════════════════════

@router.post("/machines/{machine_id}/insert-after/{after_entry_id}")
async def insert_after(machine_id: int, after_entry_id: int, request: Request):
    """Insérer un dossier juste après une entrée existante."""
    require_admin(request)
    body = await request.json()

    with get_db() as conn:
        _assert_not_locked(conn, machine_id, after_entry_id)
        ref_entry = conn.execute(
            "SELECT position FROM planning_entries WHERE id=? AND machine_id=?",
            (after_entry_id, machine_id)
        ).fetchone()
        if not ref_entry:
            raise HTTPException(404, "Entrée de référence non trouvée")

        new_position = ref_entry["position"] + 1

    reference = body.get("reference", "").strip()
    if not reference:
        raise HTTPException(400, "Référence requise")

    duree = body.get("duree_heures", 8)
    if duree < 2 or duree > 720:
        raise HTTPException(400, "Durée entre 2 et 720 heures")

    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE planning_entries SET position = position + 1 WHERE machine_id=? AND position >= ?",
            (machine_id, new_position)
        )
        conn.execute("""
            INSERT INTO planning_entries
                (machine_id, position, reference, client, description, format_l, format_h,
                 duree_heures, statut, notes, created_at, updated_at,
                 dos_rvgi, numero_of, ref_produit, laize, date_livraison, commentaire)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'attente', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            machine_id, new_position,
            reference,
            body.get("client", ""),
            body.get("description", ""),
            body.get("format_l"),
            body.get("format_h"),
            duree,
            body.get("notes", ""),
            now, now,
            (body.get("dos_rvgi") or "").strip() or None,
            body.get("numero_of"),
            body.get("ref_produit"),
            body.get("laize"),
            body.get("date_livraison"),
            body.get("commentaire"),
        ))
        _invalidate_attente_plans(conn, machine_id)
        conn.commit()

    return {"success": True, "position": new_position}


# ═══════════════════════════════════════════════════════════════
# JOURS OFF / FÉRIÉS
# ═══════════════════════════════════════════════════════════════

@router.get("/machines/{machine_id}/holidays")
def list_holidays(machine_id: int, request: Request, start: str, end: str):
    """Liste des jours off entre start/end (YYYY-MM-DD)."""
    with get_db() as conn:
        require_planning_machine(request, conn, machine_id)
        rows = conn.execute(
            """SELECT date,is_off,label FROM planning_holidays
               WHERE machine_id=? AND date>=? AND date<=?""",
            (machine_id, start, end),
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/machines/{machine_id}/day-work")
def list_day_work(machine_id: int, request: Request, start: str, end: str):
    """Dates travaillées (is_worked) entre start et end.

    - Lun–ven : seules les exceptions sont stockées (0 = forcé non travaillé). Sans ligne => travaillé selon horaires machine + fériés.
    - Samedi  : valeur effective = exception planning_day_worked si présente, sinon planning_config.samedi_travaille de la semaine.
    """
    try:
        dt_start = datetime.strptime(start, "%Y-%m-%d")
        dt_end = datetime.strptime(end, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "start/end invalides (YYYY-MM-DD)")
    if dt_end < dt_start:
        raise HTTPException(400, "end < start")

    with get_db() as conn:
        require_planning_machine(request, conn, machine_id)
        rows = conn.execute(
            """SELECT date, is_worked FROM planning_day_worked
               WHERE machine_id=? AND date>=? AND date<=? ORDER BY date""",
            (machine_id, start, end),
        ).fetchall()
        explicit = {str(r["date"]): int(r["is_worked"] or 0) for r in rows}

        # Compléter les samedis sans override avec planning_config.samedi_travaille.
        # (La UI planning se base sur ce endpoint pour cocher/décocher le samedi.)
        saturdays: list[str] = []
        cur = dt_start
        while cur <= dt_end:
            if cur.weekday() == 5:
                dkey = cur.strftime("%Y-%m-%d")
                if dkey not in explicit:
                    saturdays.append(dkey)
            cur += timedelta(days=1)

        if saturdays:
            week_keys = sorted({f"{datetime.strptime(d, '%Y-%m-%d').year}-W{datetime.strptime(d, '%Y-%m-%d').isocalendar()[1]:02d}" for d in saturdays})
            cfg_rows = conn.execute(
                f"""SELECT semaine, samedi_travaille
                    FROM planning_config
                    WHERE machine_id=? AND semaine IN ({",".join("?" * len(week_keys))})""",
                (machine_id, *week_keys),
            ).fetchall()
            cfg = {str(r["semaine"]): int(r["samedi_travaille"] or 0) for r in cfg_rows}
            for d in saturdays:
                dt = datetime.strptime(d, "%Y-%m-%d")
                wk = f"{dt.year}-W{dt.isocalendar()[1]:02d}"
                explicit[d] = 1 if int(cfg.get(wk, 0) or 0) == 1 else 0

    return [{"date": d, "is_worked": w} for d, w in sorted(explicit.items())]


@router.post("/machines/{machine_id}/reset-default-days")
def reset_default_days(machine_id: int, request: Request):
    """Réinitialise les jours off / overrides pour repartir d'une base fonctionnelle.

    Spécialement destiné à Cohésio 2 : supprime planning_holidays et planning_day_worked,
    afin que le planning reparte sur:
    - horaires_* de la machine pour lun–ven
    - planning_config.samedi_travaille pour les samedis
    """
    require_admin(request)
    with get_db() as conn:
        m = conn.execute("SELECT id, nom, code FROM machines WHERE id=?", (machine_id,)).fetchone()
        if not m:
            raise HTTPException(404, "Machine non trouvée")
        nom = str(m["nom"] or "")
        code = str(m["code"] or "")
        if code != "C2" and nom != "Cohésio 2":
            raise HTTPException(400, "Cette réinitialisation est réservée à Cohésio 2")

        # Repartir d'une base saine:
        # - supprimer les overrides jours off / samedis
        # - remettre les horaires_* sur les valeurs "génériques" de schéma
        #   (la UI Planning appliquera ensuite les défauts Cohésio 2 paire/impair en fallback)
        conn.execute("DELETE FROM planning_holidays WHERE machine_id=?", (machine_id,))
        conn.execute("DELETE FROM planning_day_worked WHERE machine_id=?", (machine_id,))
        conn.execute(
            """UPDATE machines
               SET horaires_lundi=?,
                   horaires_mardi=?,
                   horaires_mercredi=?,
                   horaires_jeudi=?,
                   horaires_vendredi=?
               WHERE id=?""",
            ("5,21", "5,21", "5,21", "5,21", "6,20", machine_id),
        )
        _invalidate_attente_plans(conn, machine_id)
        conn.commit()
    return {"success": True}


@router.put("/machines/{machine_id}/day-work")
async def set_day_work(machine_id: int, request: Request):
    """Body: {date:'YYYY-MM-DD', is_worked:1|0}. Samedi non travaillé par défaut ; 1 = travaillé."""
    require_admin(request)
    body = await request.json()
    date = (body.get("date") or "").strip()
    if not date:
        raise HTTPException(400, "date requise")
    is_worked = 1 if body.get("is_worked") else 0
    try:
        dt_day = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "date invalide (YYYY-MM-DD)")
    with get_db() as conn:
        conn.execute(
            """INSERT INTO planning_day_worked (machine_id, date, is_worked)
               VALUES (?,?,?)
               ON CONFLICT(machine_id, date) DO UPDATE SET is_worked=excluded.is_worked""",
            (machine_id, date, is_worked),
        )
        # Samedi travaillé : retirer un éventuel férié (même date) qui bloquait l’UI / la cohérence
        if dt_day.weekday() == 5 and is_worked == 1:
            conn.execute(
                "DELETE FROM planning_holidays WHERE machine_id=? AND date=?",
                (machine_id, date),
            )
        _invalidate_attente_plans(conn, machine_id)
        conn.commit()
    return {"success": True}


@router.put("/machines/{machine_id}/holidays")
async def set_holiday(machine_id: int, request: Request):
    """Body: {date:'YYYY-MM-DD', is_off:1/0, label:''}"""
    require_admin(request)
    body = await request.json()
    date = (body.get("date") or "").strip()
    if not date:
        raise HTTPException(400, "date requise")
    is_off = 1 if body.get("is_off", 1) else 0
    label = body.get("label", "") or ""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO planning_holidays (machine_id,date,is_off,label)
               VALUES (?,?,?,?)
               ON CONFLICT(machine_id,date)
               DO UPDATE SET is_off=excluded.is_off, label=excluded.label""",
            (machine_id, date, is_off, label),
        )
        _invalidate_attente_plans(conn, machine_id)
        conn.commit()
    return {"success": True}


# ═══════════════════════════════════════════════════════════════
# HORAIRES PAR DATE (override ponctuel)
# ═══════════════════════════════════════════════════════════════

@router.get("/machines/{machine_id}/day-horaires")
def list_day_horaires(machine_id: int, request: Request, start: str, end: str):
    """Retourne les overrides d'horaires sur une plage YYYY-MM-DD."""
    require_planning_view(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT date, heure_debut, heure_fin FROM planning_day_horaires
               WHERE machine_id=? AND date>=? AND date<=?
               ORDER BY date""",
            (machine_id, start, end),
        ).fetchall()
    return [{"date": r["date"], "heure_debut": r["heure_debut"], "heure_fin": r["heure_fin"]} for r in rows]


@router.put("/machines/{machine_id}/day-horaires")
async def set_day_horaires(machine_id: int, request: Request):
    """Enregistre ou met à jour l'horaire pour une date précise.
    Body: {date:'YYYY-MM-DD', heure_debut: 5.0, heure_fin: 13.0}
    Passer heure_debut==null supprime l'override.
    """
    require_admin(request)
    body = await request.json()
    date = (body.get("date") or "").strip()
    if not date:
        raise HTTPException(400, "date requise (YYYY-MM-DD)")

    # Suppression de l'override
    if body.get("heure_debut") is None:
        with get_db() as conn:
            conn.execute(
                "DELETE FROM planning_day_horaires WHERE machine_id=? AND date=?",
                (machine_id, date),
            )
            conn.commit()
        return {"success": True, "deleted": True}

    try:
        hd = float(body["heure_debut"])
        hf = float(body["heure_fin"])
    except (TypeError, ValueError, KeyError):
        raise HTTPException(400, "heure_debut et heure_fin doivent être des nombres")
    if not (0 <= hd < hf <= 24):
        raise HTTPException(400, "Plage invalide : 0 ≤ début < fin ≤ 24")

    with get_db() as conn:
        conn.execute(
            """INSERT INTO planning_day_horaires (machine_id, date, heure_debut, heure_fin)
               VALUES (?,?,?,?)
               ON CONFLICT(machine_id, date)
               DO UPDATE SET heure_debut=excluded.heure_debut, heure_fin=excluded.heure_fin""",
            (machine_id, date, hd, hf),
        )
        conn.commit()
    return {"success": True}


# ═══════════════════════════════════════════════════════════════
# CONFIG SEMAINE (samedi travaillé)
# ═══════════════════════════════════════════════════════════════

@router.get("/machines/{machine_id}/config")
def get_week_config(machine_id: int, request: Request, semaine: Optional[str] = None):
    """Récupérer la config d'une semaine (ou semaine courante)."""
    if not semaine:
        today = datetime.now()
        semaine = f"{today.year}-W{today.isocalendar()[1]:02d}"

    with get_db() as conn:
        require_planning_machine(request, conn, machine_id)
        row = conn.execute(
            "SELECT * FROM planning_config WHERE machine_id=? AND semaine=?",
            (machine_id, semaine)
        ).fetchone()
    if row:
        return dict(row)
    return {"machine_id": machine_id, "semaine": semaine, "samedi_travaille": 0, "notes": ""}


@router.put("/machines/{machine_id}/config")
async def set_week_config(machine_id: int, request: Request):
    """Définir la config d'une semaine. Body: {"semaine": "2026-W14", "samedi_travaille": 1}"""
    require_admin(request)
    body = await request.json()
    semaine = body.get("semaine")
    if not semaine:
        today = datetime.now()
        semaine = f"{today.year}-W{today.isocalendar()[1]:02d}"

    with get_db() as conn:
        conn.execute("""
            INSERT INTO planning_config (machine_id, semaine, samedi_travaille, notes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(machine_id, semaine)
            DO UPDATE SET samedi_travaille=excluded.samedi_travaille, notes=excluded.notes
        """, (
            machine_id, semaine,
            body.get("samedi_travaille", 0),
            body.get("notes", "")
        ))
        _invalidate_attente_plans(conn, machine_id)
        conn.commit()
    return {"success": True}


# ═══════════════════════════════════════════════════════════════
# DOSSIERS DISPONIBLES (non encore planifiés sur cette machine)
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# TIMELINE — Calcul du planning (lecture seule)
# ═══════════════════════════════════════════════════════════════

@router.get("/machines/{machine_id}/timeline")
def get_timeline(machine_id: int, request: Request, semaine: Optional[str] = None):
    """Calcule la timeline : créneaux figés (terminé / en cours avec dates) ou recalculés (en attente)."""
    with get_db() as conn:
        require_planning_machine(request, conn, machine_id)
        machine = conn.execute("SELECT * FROM machines WHERE id=?", (machine_id,)).fetchone()
        if not machine:
            raise HTTPException(404, "Machine non trouvée")

        configs: dict = {}
        today = datetime.now()
        for w in range(8):
            d = today + timedelta(weeks=w)
            sw = f"{d.year}-W{d.isocalendar()[1]:02d}"
            cfg = conn.execute(
                "SELECT samedi_travaille FROM planning_config WHERE machine_id=? AND semaine=?",
                (machine_id, sw)
            ).fetchone()
            configs[sw] = cfg["samedi_travaille"] if cfg else 0

        hol_rows = conn.execute(
            "SELECT date, is_off FROM planning_holidays WHERE machine_id=?",
            (machine_id,),
        ).fetchall()
        off_days = {str(r["date"]): int(r["is_off"] or 0) for r in hol_rows}

        dw_rows = conn.execute(
            "SELECT date, is_worked FROM planning_day_worked WHERE machine_id=?",
            (machine_id,),
        ).fetchall()
        day_worked_map = {str(r["date"]): int(r["is_worked"] or 0) for r in dw_rows}

        _auto_complete_en_cours(conn, machine_id)
        _enforce_single_en_cours(conn, machine_id)

        rows = conn.execute(
            """
            SELECT * FROM planning_entries
            WHERE machine_id = ?
            ORDER BY position ASC
            """,
            (machine_id,),
        ).fetchall()
        entries_list = [dict(r) for r in rows]

        slots = _compute_timeline_slots(
            conn,
            machine_id,
            dict(machine),
            configs,
            off_days,
            day_worked_map,
            entries_list,
        )
        conn.commit()

    return {
        "machine": dict(machine),
        "slots": slots,
        "configs": configs,
    }


# ── Codes opération production ──────────────────────────────────────────────
_PROD_CODE_ARRIVEE = "86"
_PROD_CODE_DEPART  = "87"


def _norm_machine_key_prod(m: str) -> Optional[str]:
    """Normalise le champ machine de production_data vers C1/C2."""
    if not m:
        return None
    n = m.lower().replace("é", "e").replace("è", "e").replace("ê", "e").strip()
    if "cohesio 1" in n or "cohesion 1" in n or "cohesio !" in n:
        return "C1"
    if "cohesio 2" in n or "cohesion 2" in n:
        return "C2"
    return None


def _parse_prod_dt(s: str) -> Optional[datetime]:
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


@router.get("/machines/{machine_id}/active-dossier")
def get_active_dossier(machine_id: int, request: Request):
    """Retourne le dossier actuellement en cours de saisie sur cette machine.

    Interroge production_data pour les saisies d'aujourd'hui afin de déterminer
    le dernier no_dossier actif sur la machine correspondante.
    Retourne {"dossier": {"no_dossier": ..., "client": ..., "designation": ...}}
    ou {"dossier": null} si aucun dossier actif.
    """
    with get_db() as conn:
        require_planning_machine(request, conn, machine_id)
        machine = conn.execute(
            "SELECT * FROM machines WHERE id=?", (machine_id,)
        ).fetchone()
        if not machine:
            raise HTTPException(404, "Machine non trouvée")

        mk = _machine_key_from_record(dict(machine))
        # Seulement C1/C2 ont la saisie de production (Cohésio 1 & 2)
        if mk not in ("C1", "C2"):
            return {"dossier": None}

        now = datetime.now(_TZ_PARIS).replace(tzinfo=None)
        iso_today = now.strftime("%Y-%m-%d")
        old_today = now.strftime("%d/%m/%Y")

        rows = conn.execute(
            """SELECT operation_code, no_dossier, client, designation, machine, date_operation
               FROM production_data
               WHERE date_operation LIKE ? OR date_operation LIKE ?
               ORDER BY date_operation ASC""",
            (iso_today + "%", old_today + "%"),
        ).fetchall()

    # Filtrer par machine et trier chronologiquement
    machine_rows: List[dict] = []
    for r in [dict(x) for x in rows]:
        if _norm_machine_key_prod(r.get("machine") or "") == mk:
            machine_rows.append(r)
    machine_rows.sort(
        key=lambda r: _parse_prod_dt(r.get("date_operation") or "") or datetime.min
    )

    if not machine_rows:
        return {"dossier": None}

    # Pas d'arrivée → machine éteinte
    if not any(r["operation_code"] == _PROD_CODE_ARRIVEE for r in machine_rows):
        return {"dossier": None}

    # Dernière opération = départ → machine éteinte
    if machine_rows[-1]["operation_code"] == _PROD_CODE_DEPART:
        return {"dossier": None}

    # Cherche le dernier no_dossier non vide
    for r in reversed(machine_rows):
        nd = (r.get("no_dossier") or "").strip()
        if nd and nd != "0":
            # Nettoie le préfixe opérateur "907 - CLIENT" → "CLIENT"
            client = r.get("client") or ""
            parts = client.split(" - ", 1)
            if len(parts) == 2 and parts[0].strip().isdigit():
                client = parts[1].strip()
            return {
                "dossier": {
                    "no_dossier": nd,
                    "client": client,
                    "designation": (r.get("designation") or "").strip(", ").strip(),
                }
            }

    return {"dossier": None}


@router.post("/machines/{machine_id}/live-refresh")
def live_refresh_en_cours(machine_id: int, request: Request):
    """Recalcule la durée du dossier en_cours à partir des timestamps de production.

    L’horodatage de référence est le début du run actuel du dossier sur la machine
    (première saisie du bloc final contigu pour ce no_dossier, cf. _prod_run_start_for_machine).
    Si le temps écoulé depuis ce point dépasse la durée planifiée, met à jour duree_heures
    en DB et retourne {"updated": true}. Sinon retourne {"updated": false}.
    """
    with get_db() as conn:
        require_planning_machine(request, conn, machine_id)

        # Trouve l'entrée en_cours pour cette machine
        en_cours = conn.execute(
            """SELECT id, COALESCE(numero_of, reference) AS dossier_ref, duree_heures, updated_at, updated_by
               FROM planning_entries
               WHERE machine_id=? AND statut='en_cours'
               ORDER BY position ASC LIMIT 1""",
            (machine_id,),
        ).fetchone()
        if not en_cours:
            return {"updated": False}

        entry_id = en_cours["id"]
        no_dossier = (en_cours["dossier_ref"] or "").strip()
        current_dur = float(en_cours["duree_heures"] or 0)
        updated_at_raw = (en_cours["updated_at"] or "").strip()
        updated_by_raw = (en_cours["updated_by"] or "").strip()

        if not no_dossier:
            return {"updated": False}

        # Ne pas écraser une modification manuelle récente.
        # Sinon, un utilisateur qui ajuste la durée voit son changement annulé au refresh automatique.
        try:
            if updated_at_raw and updated_by_raw:
                dt_updated = datetime.fromisoformat(updated_at_raw.split("+")[0].replace("Z", ""))
                if (datetime.now() - dt_updated) < timedelta(minutes=10):
                    return {"updated": False}
        except ValueError:
            pass

        mac = conn.execute("SELECT * FROM machines WHERE id=?", (machine_id,)).fetchone()
        if not mac:
            return {"updated": False}

        dt_start = _prod_run_start_for_machine(conn, machine_id, dict(mac), no_dossier)
        if not dt_start:
            return {"updated": False}

        now = datetime.now(_TZ_PARIS).replace(tzinfo=None)
        elapsed = (now - dt_start).total_seconds() / 3600
        elapsed = round(elapsed, 2)

        if elapsed <= current_dur or elapsed <= 0:
            return {"updated": False}

        planned_start = _fmt_ts(dt_start)
        planned_end = _fmt_ts(dt_start + timedelta(hours=elapsed))
        conn.execute(
            """UPDATE planning_entries
               SET duree_heures=?, planned_start=?, planned_end=?, updated_at=?, updated_by=?
               WHERE id=?""",
            (elapsed, planned_start, planned_end, datetime.now().isoformat(), "Auto", entry_id),
        )
        conn.commit()
        return {"updated": True, "entry_id": entry_id, "duree_heures": elapsed}
