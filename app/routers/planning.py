"""SIFA — Planning v1.1 (standalone)

Planning autonome : les dossiers sont saisis manuellement.
Pas de lien vers la table dossiers.

Ajouter dans main.py :
    from routers.planning import router as planning_router
    app.include_router(planning_router)
"""

import json
import logging
import math
import re
import sqlite3
import unicodedata
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from database import get_db
from config import ROLE_FABRICATION, ROLE_DIRECTION, ROLE_SUPERADMIN
from app.services.audit_service import log_action
from services.auth_service import require_admin, get_current_user, user_has_app_access
from services.dossier_stats import build_dossier_production_stats

_TZ_PARIS = ZoneInfo("Europe/Paris")
_log = logging.getLogger(__name__)

# Colonnes ajoutées après déploiements partiels — ALTER si absentes (évite 500 si migration pas encore passée).
_PLANNING_ENTRY_COL_DDLS = [
    ("exigences_production", "ALTER TABLE planning_entries ADD COLUMN exigences_production TEXT"),
    ("a_placer", "ALTER TABLE planning_entries ADD COLUMN a_placer INTEGER DEFAULT 0"),
    ("created_by", "ALTER TABLE planning_entries ADD COLUMN created_by TEXT"),
    ("updated_by", "ALTER TABLE planning_entries ADD COLUMN updated_by TEXT"),
    ("fsc_requis", "ALTER TABLE planning_entries ADD COLUMN fsc_requis INTEGER DEFAULT 0"),
    ("fsc_type_requis", "ALTER TABLE planning_entries ADD COLUMN fsc_type_requis TEXT DEFAULT ''"),
    ("departement_livraison", "ALTER TABLE planning_entries ADD COLUMN departement_livraison TEXT DEFAULT ''"),
    ("prise_rdv", "ALTER TABLE planning_entries ADD COLUMN prise_rdv INTEGER DEFAULT 0"),
    ("date_livraison_imposee", "ALTER TABLE planning_entries ADD COLUMN date_livraison_imposee INTEGER DEFAULT 0"),
    ("valide", "ALTER TABLE planning_entries ADD COLUMN valide INTEGER DEFAULT 0"),
]

_FSC_TYPES = frozenset({"fsc_100", "fsc_mix", "fsc_recycled"})

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
    # Important: date_operation peut être stocké sous plusieurs formats (ISO et fr-FR).
    # Un ORDER BY SQL sur le texte donne parfois un ordre chronologique faux.
    rows = conn.execute(
        """SELECT id, no_dossier, date_operation
           FROM production_data
           WHERE (trim(machine) = trim(?) OR (trim(?) != '' AND trim(machine) = trim(?)))""",
        (mnom, mcode, mcode),
    ).fetchall()
    if not rows:
        return None
    rows = [dict(r) for r in rows]
    rows.sort(key=lambda r: (_parse_prod_dt(str(r.get("date_operation") or "")) or datetime.min, int(r.get("id") or 0)))

    def row_ref(r: Any) -> str:
        # Neutraliser les "trous" : certaines lignes peuvent ne pas porter de no_dossier (vide / "0").
        # Elles ne doivent pas casser un run contigu si aucun autre dossier n'apparaît entre deux saisies.
        v = _norm_prod_dossier(r["no_dossier"])
        if not v or v == "0":
            return ""
        return v

    n = len(rows)
    last = n - 1
    while last >= 0 and row_ref(rows[last]) != ref:
        last -= 1
    if last < 0:
        return None

    # Remonter tant qu'on ne rencontre pas un autre dossier non vide.
    # Les lignes sans no_dossier (vide/"0") sont ignorées et ne cassent pas la juxtaposition.
    i = last
    while i > 0:
        pr = row_ref(rows[i - 1])
        if pr == ref or pr == "":
            i -= 1
            continue
        break

    # Trouver la première ligne du run qui porte réellement ce dossier.
    first = i
    while first <= last and row_ref(rows[first]) != ref:
        first += 1
    if first > last:
        return None

    raw = rows[first].get("date_operation")
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


def _body_flag_true(val) -> bool:
    if val is True or val == 1:
        return True
    if isinstance(val, str) and val.strip().lower() in ("1", "true", "yes", "on"):
        return True
    return False


def _invalidate_attente_plans(conn, machine_id: int) -> None:
    """Recalcule les créneaux « en attente » au prochain GET (réordre, ajout, durée, etc.).

    Réinitialise aussi planned_end_manual : une fin « manuelle » n'a pas de sens pour un
    dossier en attente (créneau recalculé dynamiquement). Sans ce reset, le flag fuyait
    jusqu'au passage en_cours et figeait un planned_end obsolète (durée visuelle fausse).
    """
    conn.execute(
        """UPDATE planning_entries SET planned_start=NULL, planned_end=NULL, planned_end_manual=0
           WHERE machine_id=? AND statut='attente'""",
        (machine_id,),
    )


def _planning_entry_columns(conn) -> set:
    return {row[1] for row in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}


def _ensure_planning_entry_columns(conn) -> set:
    cols = _planning_entry_columns(conn)
    for name, ddl in _PLANNING_ENTRY_COL_DDLS:
        if name not in cols:
            try:
                conn.execute(ddl)
                cols.add(name)
            except sqlite3.OperationalError:
                cols = _planning_entry_columns(conn)
    return cols


def _parse_duree_heures(raw: Any, default: float = 8.0) -> float:
    if raw is None:
        return float(default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Durée invalide")


def _parse_a_placer(raw: Any, default: int = 1) -> int:
    if raw is None:
        return 1 if default else 0
    if isinstance(raw, bool):
        return 1 if raw else 0
    if isinstance(raw, (int, float)):
        return 1 if int(raw) else 0
    if isinstance(raw, str) and raw.strip().lower() in ("1", "true", "yes", "on"):
        return 1
    return 0


def _parse_fsc_requis(raw: Any, default: int = 0) -> int:
    return _parse_a_placer(raw, default=default)


def _parse_fsc_type_requis(raw: Any, fsc_requis: int) -> str:
    if not fsc_requis:
        return ""
    t = (raw or "").strip()
    if t not in _FSC_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Type FSC invalide — valeurs : fsc_100, fsc_mix, fsc_recycled.",
        )
    return t


def _backfill_group_id(conn, entry_id: int, pe_cols: set) -> None:
    if "group_id" not in pe_cols:
        return
    conn.execute(
        """UPDATE planning_entries SET group_id=CAST(id AS TEXT)
           WHERE id=? AND (group_id IS NULL OR TRIM(COALESCE(group_id,''))='')""",
        (entry_id,),
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


def _parity_slot_to_tuple(slot: Any) -> Optional[tuple[float, float]]:
    if slot is None:
        return None
    if isinstance(slot, (list, tuple)) and len(slot) >= 2:
        return (float(slot[0]), float(slot[1]))
    if isinstance(slot, dict):
        s, e = slot.get("s"), slot.get("e")
        if s is None or e is None:
            return None
        return (float(s), float(e))
    return None


def _parity_defs_from_raw(raw: Any) -> Optional[Dict[str, Any]]:
    if raw is None:
        return None
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    out: Dict[str, Any] = {}
    for par in ("pair", "impair"):
        block = data.get(par)
        if not isinstance(block, dict):
            return None
        week = _parity_slot_to_tuple(block.get("week"))
        fri = _parity_slot_to_tuple(block.get("fri"))
        if week is None or fri is None:
            return None
        out[par] = {"week": week, "fri": fri}
    return out


def _parity_defs_for_machine(m: dict) -> Optional[Dict[str, Any]]:
    """Horaires paire/impaire : DB (horaires_parity) puis repli codé en dur pour Cohésio 2."""
    db_defs = _parity_defs_from_raw(m.get("horaires_parity"))
    if db_defs:
        return db_defs
    mk = _machine_key_from_record(m)
    if mk == "C2":
        return _parity_defs_from_raw(_PARITY_DEFAULTS.get("C2"))
    return None


def _normalize_parity_body(body: dict) -> Dict[str, Any]:
    """Valide et normalise le JSON horaires paire/impaire depuis l'API."""
    out: Dict[str, Any] = {}
    for par in ("pair", "impair"):
        block = body.get(par)
        if not isinstance(block, dict):
            raise HTTPException(400, f"Bloc '{par}' manquant ou invalide")
        norm_block: Dict[str, Any] = {}
        for slot in ("week", "fri"):
            raw = block.get(slot)
            if not isinstance(raw, dict):
                raise HTTPException(400, f"{par}.{slot} invalide")
            try:
                s = float(raw.get("s"))
                e = float(raw.get("e"))
            except (TypeError, ValueError):
                raise HTTPException(400, f"{par}.{slot} : s et e numériques requis")
            if not (0 <= s < e <= 24):
                raise HTTPException(400, f"{par}.{slot} : plage invalide (0 ≤ début < fin ≤ 24)")
            norm_block[slot] = {"s": s, "e": e}
        out[par] = norm_block
    return out


def _load_day_horaires_map(conn, machine_id: int) -> Dict[str, Tuple[float, float]]:
    """Overrides journaliers (planning_day_horaires) — priorité sur horaires machine / paire-impair.

    Quand journee_entiere=1, on force (0.0, 24.0) pour que la logique aval
    n'ait pas besoin de connaître le flag.
    """
    rows = conn.execute(
        """SELECT date, heure_debut, heure_fin,
                  COALESCE(journee_entiere, 0) AS journee_entiere
             FROM planning_day_horaires WHERE machine_id=?""",
        (machine_id,),
    ).fetchall()
    out: Dict[str, Tuple[float, float]] = {}
    for r in rows:
        try:
            s = float(r["heure_debut"])
            e = float(r["heure_fin"])
        except (TypeError, ValueError):
            continue
        if int(r["journee_entiere"] or 0) == 1:
            out[str(r["date"])] = (0.0, 24.0)
        elif e > s:
            out[str(r["date"])] = (s, e)
    return out


def _load_planning_calendar_maps(
    conn, machine_id: int
) -> tuple[dict, dict, Dict[str, int], Dict[str, Tuple[float, float]]]:
    """Config semaines (samedi + journée entière), fériés, jours travaillés, horaires journaliers — aligné GET /timeline.

    configs[sw] est un dict {"samedi_travaille": 0/1, "journee_entiere": 0/1}.
    """
    configs: dict = {}
    today = datetime.now()
    for w in range(8):
        d = today + timedelta(weeks=w)
        sw = f"{d.year}-W{d.isocalendar()[1]:02d}"
        cfg = conn.execute(
            """SELECT samedi_travaille, COALESCE(journee_entiere, 0) AS journee_entiere
                 FROM planning_config WHERE machine_id=? AND semaine=?""",
            (machine_id, sw),
        ).fetchone()
        configs[sw] = {
            "samedi_travaille": int(cfg["samedi_travaille"] or 0) if cfg else 0,
            "journee_entiere":  int(cfg["journee_entiere"] or 0) if cfg else 0,
        }
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
    day_horaires_map = _load_day_horaires_map(conn, machine_id)
    return configs, off_days, day_worked_map, day_horaires_map


def _load_planning_calendar_maps_range(
    conn, machine_id: int, weeks_back: int = 52, weeks_forward: int = 8
) -> tuple[dict, dict, Dict[str, int], Dict[str, Tuple[float, float]]]:
    """Variante de _load_planning_calendar_maps avec plage étendue (utile pour opérations de recalage)."""
    configs: dict = {}
    today = datetime.now()
    for w in range(-int(weeks_back), int(weeks_forward) + 1):
        d = today + timedelta(weeks=w)
        sw = f"{d.year}-W{d.isocalendar()[1]:02d}"
        if sw in configs:
            continue
        cfg = conn.execute(
            """SELECT samedi_travaille, COALESCE(journee_entiere, 0) AS journee_entiere
                 FROM planning_config WHERE machine_id=? AND semaine=?""",
            (machine_id, sw),
        ).fetchone()
        configs[sw] = {
            "samedi_travaille": int(cfg["samedi_travaille"] or 0) if cfg else 0,
            "journee_entiere":  int(cfg["journee_entiere"] or 0) if cfg else 0,
        }
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
    day_horaires_map = _load_day_horaires_map(conn, machine_id)
    return configs, off_days, day_worked_map, day_horaires_map


def _hours_for_date_factory(
    m: dict,
    configs: dict,
    off_days: dict,
    day_worked_map: Dict[str, int],
    day_horaires_map: Optional[Dict[str, Tuple[float, float]]] = None,
):
    """get_hours_for_date(dt) — jours non travaillés exclus avant tout override horaire."""
    dh_map = day_horaires_map or {}
    base_hours = {}
    for day_idx, field in [(0, "horaires_lundi"), (1, "horaires_mardi"),
                           (2, "horaires_mercredi"), (3, "horaires_jeudi"),
                           (4, "horaires_vendredi")]:
        base_hours[day_idx] = _parse_horaires_val(m.get(field), "5,21")

    sat_hours_t = _parse_horaires_val(m.get("horaires_samedi"), "6,18")

    _parity_defs = _parity_defs_for_machine(m)

    def _is_pair_week(dt: datetime) -> bool:
        return dt.isocalendar()[1] % 2 == 0

    def week_key(dt: datetime) -> str:
        return f"{dt.year}-W{dt.isocalendar()[1]:02d}"

    def get_hours_for_date(dt: datetime):
        dkey = dt.strftime("%Y-%m-%d")
        wd = dt.weekday()
        if wd <= 4 and int(off_days.get(dkey, 0) or 0):
            return None
        dw = day_worked_map.get(dkey)
        if wd in base_hours:
            if dw is not None and int(dw) == 0:
                return None
        elif wd == 5:
            if dw is None:
                if int((configs.get(week_key(dt), {}) or {}).get("samedi_travaille", 0) or 0) == 0:
                    return None
            elif int(dw) == 0:
                return None
        # Journée entière : hiérarchie override day > override semaine > default machine.
        # (le jour doit rester travaillé — les checks day-off ci-dessus s'appliquent d'abord)
        dh = dh_map.get(dkey)
        if dh is not None:
            return dh
        wk_cfg = configs.get(week_key(dt), {}) or {}
        if isinstance(wk_cfg, dict) and int(wk_cfg.get("journee_entiere", 0) or 0) == 1:
            return (0.0, 24.0)
        if int(m.get("journee_entiere") or 0) == 1:
            return (0.0, 24.0)
        if wd in base_hours:
            if _parity_defs is not None:
                par = "pair" if _is_pair_week(dt) else "impair"
                slot = "fri" if wd == 4 else "week"
                h = _parity_defs[par][slot]
                if isinstance(h, dict):
                    return (float(h["s"]), float(h["e"]))
                return (float(h[0]), float(h[1]))
            return base_hours[wd]
        if wd == 5:
            return sat_hours_t
        return None

    return get_hours_for_date


def _make_work_duration_consumer(
    m: dict,
    configs: dict,
    off_days: dict,
    day_worked_map: Dict[str, int],
    day_horaires_map: Optional[Dict[str, Tuple[float, float]]] = None,
) -> tuple[Any, Any]:
    """(advance_to_work, consume_duration_from) — duree_heures = heures ouvrées machine (même logique que la timeline)."""
    get_hours_for_date = _hours_for_date_factory(
        m, configs, off_days, day_worked_map, day_horaires_map
    )

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


def _work_hours_between(get_hours_for_date, start_dt: datetime, end_dt: datetime) -> float:
    """Heures ouvrées machine entre deux instants : somme des intersections avec les
    fenêtres journalières (jours off / dimanches exclus via get_hours_for_date)."""
    if not start_dt or not end_dt or end_dt <= start_dt:
        return 0.0
    total = 0.0
    day = datetime(start_dt.year, start_dt.month, start_dt.day)
    end_day = datetime(end_dt.year, end_dt.month, end_dt.day)
    guard = 0
    while day <= end_day and guard < 400:
        guard += 1
        win = get_hours_for_date(day)
        if win:
            s, e = win
            ws = day + timedelta(hours=float(s))
            we = day + timedelta(hours=float(e))
            seg_s = start_dt if start_dt > ws else ws
            seg_e = end_dt if end_dt < we else we
            if seg_e > seg_s:
                total += (seg_e - seg_s).total_seconds() / 3600.0
        day += timedelta(days=1)
    return total


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
        cfgs, off, dw, dh = _load_planning_calendar_maps(conn, machine_id)
        _, consume_from = _make_work_duration_consumer(dict(m), cfgs, off, dw, dh)
        _, slot_end, _ = consume_from(dt0.replace(microsecond=0), float(duree_h))
        return _fmt_ts(slot_end)
    except Exception:
        return None


def _normalize_palette_type(value) -> Optional[str]:
    """Normalise la valeur palette_type pour l'affichage utilisateur.
    Antibactérienne, perdue, jetable → 'Perdue'.
    Europe (toutes variantes) → 'Europe'.
    Sinon : valeur d'origine en Capitalize (pas de perte d'info)."""
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    s = raw.lower()
    if "antibac" in s or "anti-bac" in s or "anti bac" in s:
        return "Perdue"
    if "perdu" in s or "jetab" in s:
        return "Perdue"
    if "europe" in s or s == "eur" or s.startswith("eur "):
        return "Europe"
    # Cas non reconnu : garde la valeur mais en mise en forme propre
    return raw[:1].upper() + raw[1:].lower() if len(raw) > 1 else raw.upper()


def _is_palette_sized_box(label) -> bool:
    """Détecte si le format de carton/conteneur a une taille proche d'une
    palette standard (1200x800 mm). Dans ce cas, 1 carton = 1 palette.
    Détection :
      - mots-clés explicites : 'conteneur', 'container', 'box', 'palette box'
      - dimensions parsées (XXXX x YYY) proches de 1200x800 avec tolérance ±150 mm
    """
    if not label:
        return False
    s = str(label).lower()
    for kw in ("conteneur", "container", " box", "box ", "palette box"):
        if kw in s:
            return True
    if s.strip().startswith("box"):
        return True
    m = re.search(r"(\d{3,4})\s*[x\u00d7]\s*(\d{3,4})", s)
    if m:
        try:
            a, b = int(m.group(1)), int(m.group(2))
            lo, hi = min(a, b), max(a, b)
            # Format palette standard EUR : 1200x800 (tolérance ±150)
            if 1050 <= hi <= 1350 and 650 <= lo <= 950:
                return True
        except Exception:
            pass
    return False


def _build_conditionnement_phrase(e: dict) -> Optional[str]:
    """Phrase descriptive du conditionnement pour la vue expé.
    Cas classique : 'Palettes de 30 cartons de 6 bobines de 1000 étiquettes'
    Cas conteneur/box : 'Conteneurs de 6 bobines de 1000 étiquettes' (1 carton = 1 palette)
    Retourne None si données insuffisantes."""
    try:
        nb_bob_carton = e.get("_ft_nb_bobines_carton")
        nb_etiq_bobin = e.get("_ft_nb_etiq_bobin")
        sol  = e.get("_ft_palette_nb_cartons_sol")
        haut = e.get("_ft_palette_nb_cartons_hauteur")
    except Exception:
        return None

    is_box = (_is_palette_sized_box(e.get("_ft_cartons"))
              or _is_palette_sized_box(e.get("_ft_palette_type")))

    parts: list = []

    if is_box:
        parts.append("Conteneurs")
    else:
        try:
            n_cartons = int(sol) * int(haut)
            if n_cartons <= 0:
                return None
            label = "cartons" if n_cartons > 1 else "carton"
            parts.append(f"Palettes de {n_cartons} {label}")
        except (TypeError, ValueError):
            return None

    if nb_bob_carton is not None:
        try:
            n = int(nb_bob_carton)
            if n > 0:
                label = "bobines" if n > 1 else "bobine"
                parts.append(f"de {n} {label}")
        except (TypeError, ValueError):
            pass

    if nb_etiq_bobin is not None:
        try:
            n = int(nb_etiq_bobin)
            if n > 0:
                # Espace insécable comme séparateur de milliers (lecture humaine)
                s = f"{n:,}".replace(",", "\u202F")
                label = "étiquettes" if n > 1 else "étiquette"
                parts.append(f"de {s} {label}")
        except (TypeError, ValueError):
            pass

    if not parts:
        return None
    return " ".join(parts)


def _compute_nb_palettes(e: dict) -> Optional[int]:
    """Calcule le nombre de palettes nécessaires.
    Formule classique :
      nb_cartons  = ceil(qte_bobines / nb_bobines_carton)
      nb_palettes = ceil(nb_cartons / (palette_nb_cartons_sol * palette_nb_cartons_hauteur))
    Cas particulier : si le carton est en réalité un conteneur/box de taille palette
    (détecté via le libellé du carton ou du type de palette), alors 1 carton = 1 palette.
    Retourne None si données insuffisantes.
    """
    try:
        qte_bobines       = e.get("_of_qte_bobines")
        nb_bobines_carton = e.get("_ft_nb_bobines_carton")
        if qte_bobines is None or nb_bobines_carton is None:
            return None
        qb  = float(qte_bobines)
        nbc = float(nb_bobines_carton)
        if nbc <= 0 or qb <= 0:
            return None
        nb_cartons = math.ceil(qb / nbc)
        # Cas conteneur/box de taille palette → 1 carton = 1 palette
        if (_is_palette_sized_box(e.get("_ft_cartons"))
            or _is_palette_sized_box(e.get("_ft_palette_type"))):
            return int(nb_cartons)
        # Formule classique : nécessite cartons_sol et cartons_haut
        cartons_sol  = e.get("_ft_palette_nb_cartons_sol")
        cartons_haut = e.get("_ft_palette_nb_cartons_hauteur")
        if cartons_sol is None or cartons_haut is None:
            return None
        cso = float(cartons_sol)
        cha = float(cartons_haut)
        if cso <= 0 or cha <= 0:
            return None
        nb_palettes = math.ceil(nb_cartons / (cso * cha))
        return int(nb_palettes)
    except Exception:
        return None


def _of_timeline_fields(e: dict) -> Tuple[bool, Optional[float]]:
    """OF PDF lié (of_import_id) et qté étiquettes affichable (non nulle, pas 0)."""
    of_id = e.get("of_import_id")
    has_of = of_id is not None and int(of_id or 0) > 0
    if not has_of:
        return False, None
    raw = e.get("_of_qte_etiquettes")
    if raw is None:
        return True, None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return True, None
    if v == 0:
        return True, None
    return True, v


def _slot_payload(e: dict, start_iso: str, end_iso: str) -> dict:
    has_of, qte_etiquettes = _of_timeline_fields(e)
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
        "exigences_production": e.get("exigences_production"),
        "fsc_requis": int(e.get("fsc_requis") or 0),
        "fsc_type_requis": (e.get("fsc_type_requis") or "").strip(),
        "a_placer": e.get("a_placer", 0),
        "valide": int(e.get("valide") or 0),
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
        "has_of": has_of,
        "qte_etiquettes": qte_etiquettes,
        "nb_palettes": _compute_nb_palettes(e),
        "prise_rdv": int(e.get("prise_rdv") or 0),
        "date_livraison_imposee": int(e.get("date_livraison_imposee") or 0),
        "departement_livraison": (e.get("departement_livraison") or "").strip(),
        "ft_support": (e.get("_ft_support") or "").strip() or None,
        "ft_adhesif": (e.get("_ft_adhesif") or "").strip() or None,
        "ft_palette_type": _normalize_palette_type(e.get("_ft_palette_type")),
        "ft_conditionnement_phrase": _build_conditionnement_phrase(e),
        "ft_mandrin_dia": (e.get("_ft_mandrin_dia") or "").strip() or None,
    }


def _compute_timeline_slots(
    conn,
    machine_id: int,
    m: dict,
    configs: dict,
    off_days: dict,
    day_worked_map: Dict[str, int],
    day_horaires_map: Dict[str, Tuple[float, float]],
    entries: List[dict],
    *,
    persist: bool = True,
) -> List[dict]:
    """Calcule les créneaux : terminé / en cours figés ; en attente (et en_cours sans plan) dynamiques + persistés.

    day_worked_map : pour chaque date YYYY-MM-DD, is_worked 0/1. Samedi : sans ligne ou 0 = non travaillé ;
    lun–ven : sans ligne = ouvré selon horaires machine ; ligne 0 = forcé non travaillé.
    """
    advance_to_work, consume_duration_from = _make_work_duration_consumer(
        m, configs, off_days, day_worked_map, day_horaires_map
    )

    slots: List[dict] = []
    cursor = advance_to_work(datetime.now().replace(minute=0, second=0, microsecond=0))
    now_u = _fmt_ts(datetime.now())

    # Un dossier "en cours" est produit MAINTENANT : aucun dossier "en attente" ne peut
    # démarrer avant sa fin, même s'il le précède dans la liste (cas d'un démarrage
    # opérateur hors séquence — saisie sur un dossier placé après un dossier en attente).
    # Sans ce garde-fou, le dossier en attente positionné avant l'en-cours était planifié
    # à "maintenant" et se superposait visuellement au dossier réellement en production.
    for e in entries:
        if (e.get("statut") or "") == "en_cours" and _is_frozen_entry(e):
            # Recalcul de la vraie fin de l'en_cours pour le curseur : on part
            # du run_start réel (1re saisie) + duree_heures, plutôt que du
            # planned_end stocké qui peut être stale (ex : horaires modifiés
            # depuis le dernier calcul). Sans ça, les dossiers en attente
            # positionnés AVANT l'en_cours dans la file sont placés sur du
            # stale et se retrouvent visuellement écrasés par l'en_cours
            # une fois qu'il est recalculé dans la boucle principale.
            manual_end = int(e.get("planned_end_manual") or 0) == 1
            ref = (e.get("numero_of") or e.get("reference") or "").strip()
            run_start = _prod_run_start_for_machine(conn, machine_id, m, ref) if ref else None
            fresh_pend = None
            if run_start is not None and not manual_end:
                try:
                    duree_h = float(e.get("duree_heures") or 0)
                    if duree_h > 0:
                        _, fresh_pend, _ = consume_duration_from(
                            run_start.replace(microsecond=0), duree_h
                        )
                except (TypeError, ValueError):
                    fresh_pend = None
            pend = fresh_pend or _parse_planned_dt(e.get("planned_end"))
            if pend:
                cand = advance_to_work(pend)
                if cand and cand > cursor:
                    cursor = cand
            break

    for e in entries:
        st = e.get("statut") or "attente"

        # ── Terminé figé : conserve ses dates, avance le curseur ──────────
        if st == "termine" and _is_frozen_entry(e):
            ps, pe = e["planned_start"], e["planned_end"]
            pend = _parse_planned_dt(pe)
            if pend:
                cand = advance_to_work(pend)
                if cand and cand > cursor:
                    cursor = cand
            slots.append(_slot_payload(e, ps, pe))
            continue
        if st == "termine":
            continue

        # ── En cours figé : début prod = 1re saisie du run actuel ; fin auto sauf override manuel ─
        if st == "en_cours" and _is_frozen_entry(e):
            manual_end = int(e.get("planned_end_manual") or 0) == 1
            ref = (e.get("numero_of") or e.get("reference") or "").strip()
            run_start = _prod_run_start_for_machine(conn, machine_id, m, ref) if ref else None
            if run_start is not None and not manual_end:
                duree_h = float(e.get("duree_heures") or 0)
                p0 = run_start.replace(microsecond=0)
                ps = _fmt_ts(p0)
                _, pe_dt, _ = consume_duration_from(p0, duree_h)
                pe = _fmt_ts(pe_dt)
                if persist and (
                    str(e.get("planned_start") or "") != ps
                    or str(e.get("planned_end") or "") != pe
                ):
                    conn.execute(
                        """UPDATE planning_entries SET planned_start=?, planned_end=?, updated_at=?
                           WHERE id=? AND machine_id=?""",
                        (ps, pe, now_u, e["id"], machine_id),
                    )
                e["planned_start"], e["planned_end"] = ps, pe
            elif run_start is not None and manual_end:
                p0 = run_start.replace(microsecond=0)
                ps = _fmt_ts(p0)
                pe = e.get("planned_end")
                if persist and str(e.get("planned_start") or "") != ps:
                    conn.execute(
                        """UPDATE planning_entries SET planned_start=?, updated_at=?
                           WHERE id=? AND machine_id=?""",
                        (ps, now_u, e["id"], machine_id),
                    )
                e["planned_start"] = ps
            else:
                ps, pe = e["planned_start"], e["planned_end"]
            pend = _parse_planned_dt(pe)
            if pend:
                cand = advance_to_work(pend)
                if cand and cand > cursor:
                    cursor = cand
            slots.append(_slot_payload(e, ps, pe))
            continue

        # ── Attente et en_cours sans dates : calcul dynamique depuis cursor
        slot_start, slot_end, cursor = consume_duration_from(cursor, e["duree_heures"])
        ps, pe = _fmt_ts(slot_start), _fmt_ts(slot_end)
        if persist:
            conn.execute(
                """UPDATE planning_entries SET planned_start=?, planned_end=?, updated_at=?
                   WHERE id=? AND machine_id=?""",
                (ps, pe, now_u, e["id"], machine_id),
            )
        ee = {**e, "planned_start": ps, "planned_end": pe}
        slots.append(_slot_payload(ee, ps, pe))

    return slots


# ═══════════════════════════════════════════════════════════════
# PLACEMENT AUTOMATIQUE PAR DÉLAI CLIENT (à l'ajout d'un dossier)
# ═══════════════════════════════════════════════════════════════

def _parse_liv_date(raw: Any) -> Optional[datetime]:
    """Date de livraison 'YYYY-MM-DD' → datetime fin de journée (échéance). None si invalide/vide."""
    s = str(raw or "").strip()
    if not s:
        return None
    try:
        d = datetime.strptime(s[:10], "%Y-%m-%d")
        return d.replace(hour=23, minute=59, second=59, microsecond=0)
    except (ValueError, TypeError):
        return None


def _entry_tardiness_h(entry: dict, end_dt: Optional[datetime]) -> float:
    """Retard d'un dossier en heures : max(0, fin_prod − échéance). 0 si pas d'échéance ou fin inconnue."""
    if not end_dt:
        return 0.0
    dl = _parse_liv_date(entry.get("date_livraison"))
    if dl is None:
        return 0.0
    return max(0.0, (end_dt - dl).total_seconds() / 3600.0)


def _simulate_planned_ends(
    m: dict, configs: dict, off_days: dict, day_worked_map: Dict[str, int],
    day_horaires_map: Dict[str, Tuple[float, float]], ordered_entries: List[dict],
) -> List[Optional[datetime]]:
    """Simule (sans persister) les dates de fin de prod d'une séquence ordonnée.

    Miroir de _compute_timeline_slots : terminé/en_cours figés conservent leurs dates et avancent
    le curseur ; les dossiers en attente consomment leur durée depuis le curseur.
    """
    advance_to_work, consume_duration_from = _make_work_duration_consumer(
        m, configs, off_days, day_worked_map, day_horaires_map
    )
    cursor = advance_to_work(datetime.now().replace(minute=0, second=0, microsecond=0))
    # Cf. _compute_timeline_slots : ne jamais placer un "en attente" avant la fin du dossier en cours.
    for e in ordered_entries:
        if (e.get("statut") or "") == "en_cours" and bool(e.get("planned_start")) and bool(e.get("planned_end")):
            pend = _parse_planned_dt(e.get("planned_end"))
            if pend:
                cand = advance_to_work(pend)
                if cand and cand > cursor:
                    cursor = cand
            break
    ends: List[Optional[datetime]] = []
    for e in ordered_entries:
        st = e.get("statut") or "attente"
        frozen = st in ("termine", "en_cours") and bool(e.get("planned_start")) and bool(e.get("planned_end"))
        if frozen:
            pe_dt = _parse_planned_dt(e.get("planned_end"))
            ends.append(pe_dt)
            if pe_dt:
                cand = advance_to_work(pe_dt)
                if cand and cand > cursor:
                    cursor = cand
            continue
        if st == "termine":
            # Terminé sans dates : neutre, on ne consomme pas.
            ends.append(None)
            continue
        slot_start, slot_end, cursor = consume_duration_from(cursor, float(e.get("duree_heures") or 8.0))
        ends.append(slot_end)
    return ends


def _compute_smart_position(
    conn, machine_id: int, new_duree: float, new_date_liv: Any, new_ref: str
) -> Optional[Tuple[int, Optional[dict]]]:
    """Position d'insertion par délai client.

    Règle : on retient la position la plus tardive où personne ne rate son délai (ni le nouveau
    dossier, ni les dossiers décalés en aval). Si aucune position n'est tenable (planning saturé),
    on minimise le retard total et on renvoie un avertissement.

    Retourne (position, warning|None), ou None si le calcul n'est pas applicable
    (machine introuvable, délai illisible) → le caller retombe sur le fond de planning.
    """
    new_deadline = _parse_liv_date(new_date_liv)
    if new_deadline is None:
        return None
    mac = conn.execute("SELECT * FROM machines WHERE id=?", (machine_id,)).fetchone()
    if not mac:
        return None
    m = dict(mac)

    rows = conn.execute(
        """SELECT id, position, statut, planned_start, planned_end, duree_heures,
                  date_livraison, numero_of, reference
           FROM planning_entries WHERE machine_id=? ORDER BY position ASC""",
        (machine_id,),
    ).fetchall()
    ordered = [dict(r) for r in rows]
    max_pos = max((int(e["position"]) for e in ordered), default=0)

    # Index du premier créneau déplaçable : juste après le dernier dossier figé (terminé/en_cours).
    first_movable = 0
    for i, e in enumerate(ordered):
        if (e.get("statut") or "") in ("termine", "en_cours"):
            first_movable = i + 1

    try:
        cfgs, off, dw, dh = _load_planning_calendar_maps(conn, machine_id)
    except Exception:
        return None

    new_entry = {"statut": "attente", "duree_heures": float(new_duree), "date_livraison": None}

    def pos_for_idx(idx: int) -> int:
        return int(ordered[idx]["position"]) if idx < len(ordered) else max_pos + 1

    def ref_of(e: dict) -> str:
        return str(e.get("numero_of") or e.get("reference") or "?").strip()

    def liv_str(e: dict) -> str:
        return str(e.get("date_livraison") or "").strip()

    # Retards de référence (sans le nouveau dossier).
    base_ends = _simulate_planned_ends(m, cfgs, off, dw, dh, ordered)
    base_tard = [_entry_tardiness_h(ordered[i], base_ends[i]) for i in range(len(ordered))]

    feasible_pos: Optional[int] = None
    sat_best: Optional[tuple] = None  # (cost, idx, position, c_at_risk, c_deadline_str, risks)

    for idx in range(first_movable, len(ordered) + 1):
        trial = ordered[:idx] + [new_entry] + ordered[idx:]
        ends = _simulate_planned_ends(m, cfgs, off, dw, dh, trial)
        c_end = ends[idx]
        c_tard = (
            max(0.0, (c_end - new_deadline).total_seconds() / 3600.0) if c_end else 1e9
        )
        # Retard ajouté aux dossiers en aval (décalés par l'insertion).
        added = 0.0
        risks: List[dict] = []
        for j in range(idx, len(ordered)):
            tt = _entry_tardiness_h(ordered[j], ends[j + 1])
            delta = tt - base_tard[j]
            if delta > 1e-6:
                added += delta
                risks.append({"ref": ref_of(ordered[j]), "date": liv_str(ordered[j])})
        c_on_time = c_tard <= 1e-6
        if c_on_time and added <= 1e-6:
            feasible_pos = pos_for_idx(idx)  # garde la dernière (= la plus tardive) tenable
        else:
            cost = added + c_tard
            cand = (cost, idx, pos_for_idx(idx), c_tard > 1e-6, str(new_date_liv or "").strip()[:10], risks)
            if (
                sat_best is None
                or cost < sat_best[0] - 1e-9
                or (abs(cost - sat_best[0]) <= 1e-9 and idx > sat_best[1])
            ):
                sat_best = cand

    if feasible_pos is not None:
        return (feasible_pos, None)

    if sat_best is None:
        return None

    _, _, position, c_at_risk, c_deadline_str, risks = sat_best
    # Déduplique les dossiers aval à risque.
    seen = set()
    risk_list = []
    for r in risks:
        key = r["ref"]
        if key not in seen:
            seen.add(key)
            risk_list.append(r)

    bits: List[str] = []
    if c_at_risk:
        bits.append(f"le dossier {new_ref or '?'} risque de dépasser son délai client ({c_deadline_str})")
    for r in risk_list:
        d = f" (délai {r['date']})" if r["date"] else ""
        bits.append(f"le dossier {r['ref']}{d} passe en risque de retard")
    message = "Planning tendu — " + " ; ".join(bits) + ". Merci de prévenir le responsable industriel."
    return (position, {"message": message})


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
    if user.get("role") in {"direction", "administration", "administration_ventes", "administration_technique"}:
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
    user = require_admin(request)
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
    machine_nom = ""
    with get_db() as conn:
        ex = conn.execute("SELECT id, nom FROM machines WHERE id=?", (machine_id,)).fetchone()
        if not ex:
            raise HTTPException(404, "Machine non trouvée")
        machine_nom = ex["nom"] or ""
        conn.execute(f"UPDATE machines SET {col} = ? WHERE id = ?", (val, machine_id))
        _invalidate_attente_plans(conn, machine_id)
        conn.commit()
    log_action(
        user=user,
        action="UPDATE",
        module="planning",
        objet=f"Horaires machine {machine_nom}",
        detail={"day": day, "start": start, "end": end},
        ip=request.client.host if request.client else None,
    )
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


@router.put("/machines/{machine_id}/horaires-parity")
async def set_machine_horaires_parity(machine_id: int, request: Request):
    """Enregistre les horaires paire/impaire (semaine + vendredi) pour la timeline.

    Body: {
      "pair": {"week": {"s": 5, "e": 20}, "fri": {"s": 6, "e": 20}},
      "impair": {"week": {"s": 13, "e": 20}, "fri": {"s": 14, "e": 20}}
    }
    """
    require_admin(request)
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Body invalide")
    normalized = _normalize_parity_body(body)
    with get_db() as conn:
        ex = conn.execute("SELECT id FROM machines WHERE id=?", (machine_id,)).fetchone()
        if not ex:
            raise HTTPException(404, "Machine non trouvée")
        conn.execute(
            "UPDATE machines SET horaires_parity=? WHERE id=?",
            (json.dumps(normalized), machine_id),
        )
        _invalidate_attente_plans(conn, machine_id)
        conn.commit()
    return {"success": True, "horaires_parity": normalized}


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
        # Nom de la machine pour désambiguïser la fiche technique (multi-variantes par ref_produit_norm)
        m_row = conn.execute("SELECT nom FROM machines WHERE id=?", (machine_id,)).fetchone()
        machine_nom = (m_row["nom"] if m_row else "") or ""
        rows = conn.execute("""
            SELECT pe.*,
                   (SELECT ft.support FROM fiches_techniques ft
                    WHERE ft.ref_produit_norm IS NOT NULL
                      AND ft.ref_produit_norm = pe.ref_produit_norm
                    ORDER BY
                      CASE
                        WHEN LOWER(TRIM(COALESCE(ft.machine,''))) = LOWER(TRIM(COALESCE(?,''))) AND TRIM(COALESCE(ft.machine,'')) != '' THEN 0
                        WHEN TRIM(COALESCE(ft.machine,'')) = '' THEN 1
                        ELSE 2
                      END,
                      ft.id
                    LIMIT 1) AS ft_support,
                   (SELECT ft.adhesif FROM fiches_techniques ft
                    WHERE ft.ref_produit_norm IS NOT NULL
                      AND ft.ref_produit_norm = pe.ref_produit_norm
                    ORDER BY
                      CASE
                        WHEN LOWER(TRIM(COALESCE(ft.machine,''))) = LOWER(TRIM(COALESCE(?,''))) AND TRIM(COALESCE(ft.machine,'')) != '' THEN 0
                        WHEN TRIM(COALESCE(ft.machine,'')) = '' THEN 1
                        ELSE 2
                      END,
                      ft.id
                    LIMIT 1) AS ft_adhesif
            FROM planning_entries pe
            WHERE pe.machine_id = ?
            ORDER BY pe.position ASC
        """, (machine_nom, machine_nom, machine_id)).fetchall()
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
    ref_audit = ""

    with get_db() as conn:
        require_planning_machine(request, conn, machine_id)
        row = conn.execute(
            """SELECT id, reference, statut, statut_reel, planned_start, planned_end
               FROM planning_entries WHERE id = ? AND machine_id = ?""",
            (entry_id, machine_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entrée introuvable.")
        ref_audit = (row["reference"] or "").strip()

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

    log_action(
        user=user,
        action="CLOSE" if statut == "termine" else "UPDATE",
        module="planning",
        objet=f"Statut dossier {ref_audit} → {statut}",
        detail={"statut": statut, "override": override},
        ip=request.client.host if request.client else None,
    )
    return {"ok": True, "saisie_found": saisie_found}


def _parse_etiq_par_carton(raw):
    """Parse etiquettes_par_carton: entier positif ou None."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    try:
        v = int(float(str(raw).replace(",", ".").strip()))
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


@router.post("/machines/{machine_id}/entries")
async def add_entry(machine_id: int, request: Request):
    """Ajouter un dossier manuellement au planning."""
    require_admin(request)
    body = await request.json()
    reference = (body.get("reference") or body.get("numero_of") or "").strip()
    if not reference:
        raise HTTPException(400, "Référence requise")

    duree = _parse_duree_heures(body.get("duree_heures", 8))
    if duree < 0.75 or duree > 720:
        raise HTTPException(400, "Durée entre 0,75 et 720 heures")

    user = get_current_user(request)
    user_name = user.get("nom") or user.get("email") or "Admin"
    now = datetime.now().isoformat()
    date_liv = body.get("date_livraison")
    if date_liv is not None and not str(date_liv).strip():
        date_liv = None

    fsc_requis_val = _parse_fsc_requis(body.get("fsc_requis"), default=0)
    row_data = {
        "reference": reference,
        "client": body.get("client", "") or "",
        "description": body.get("description", "") or "",
        "format_l": body.get("format_l"),
        "format_h": body.get("format_h"),
        "duree_heures": duree,
        "statut": body.get("statut", "attente") or "attente",
        "notes": body.get("notes", "") or "",
        "created_at": now,
        "updated_at": now,
        "dos_rvgi": (body.get("dos_rvgi") or "").strip() or None,
        "numero_of": body.get("numero_of") or reference,
        "ref_produit": body.get("ref_produit"),
        "laize": body.get("laize"),
        "date_livraison": date_liv,
        "commentaire": body.get("commentaire", "") or "",
        "exigences_production": (body.get("exigences_production") or "").strip() or None,
        "a_placer": _parse_a_placer(body.get("a_placer"), default=1),
        "valide": _parse_a_placer(body.get("valide"), default=0),
        "fsc_requis": fsc_requis_val,
        "fsc_type_requis": _parse_fsc_type_requis(
            body.get("fsc_type_requis"), fsc_requis_val
        ),
        "departement_livraison": (body.get("departement_livraison") or "").strip() or "",
        "prise_rdv": _parse_a_placer(body.get("prise_rdv"), default=0),
        "date_livraison_imposee": _parse_a_placer(body.get("date_livraison_imposee"), default=0),
        "etiquettes_par_carton": _parse_etiq_par_carton(body.get("etiquettes_par_carton")),
        "created_by": user_name,
        "updated_by": user_name,
    }

    position: int
    machine_nom = ""
    placement_warning = None
    try:
        with get_db() as conn:
            pe_cols = _ensure_planning_entry_columns(conn)
            mac = conn.execute("SELECT id, nom FROM machines WHERE id=?", (machine_id,)).fetchone()
            if not mac:
                raise HTTPException(404, "Machine non trouvée")
            machine_nom = mac["nom"] or ""

            position = body.get("position")
            if position is None:
                # Placement automatique par délai client (uniquement pour un dossier à venir
                # avec une date de livraison renseignée). Sinon : fond de planning.
                if (row_data["statut"] or "attente") == "attente" and date_liv:
                    smart = _compute_smart_position(
                        conn, machine_id, duree, date_liv, reference
                    )
                    if smart is not None:
                        position, placement_warning = smart
            if position is None:
                max_pos = conn.execute(
                    "SELECT COALESCE(MAX(position),0) FROM planning_entries WHERE machine_id=?",
                    (machine_id,),
                ).fetchone()[0]
                position = int(max_pos) + 1
            else:
                position = int(position)
                conn.execute(
                    "UPDATE planning_entries SET position = position + 1 WHERE machine_id=? AND position >= ?",
                    (machine_id, position),
                )

            insert_cols = ["machine_id", "position"] + [c for c in row_data if c in pe_cols]
            values = [machine_id, position] + [row_data[c] for c in insert_cols[2:]]
            conn.execute(
                f"INSERT INTO planning_entries ({', '.join(insert_cols)}) VALUES ({', '.join('?' * len(insert_cols))})",
                values,
            )
            new_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
            _backfill_group_id(conn, new_id, pe_cols)
            _invalidate_attente_plans(conn, machine_id)
            conn.commit()
    except HTTPException:
        raise
    except sqlite3.OperationalError as exc:
        _log.exception("add_entry DB error machine_id=%s", machine_id)
        raise HTTPException(status_code=500, detail=f"Erreur base de données : {exc}") from exc

    log_action(
        user=user,
        action="CREATE",
        module="planning",
        objet=f"Dossier {reference} · {machine_nom}",
        detail={"reference": reference, "duree_heures": duree},
        ip=request.client.host if request.client else None,
    )
    return {"success": True, "position": position, "warning": placement_warning}


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
    ref_audit = ""
    audit_detail: dict = {}

    with get_db() as conn:
        ex = conn.execute(
            "SELECT * FROM planning_entries WHERE id=? AND machine_id=?",
            (entry_id, machine_id)
        ).fetchone()
        if not ex:
            raise HTTPException(404, "Entrée non trouvée")

        exd = dict(ex)
        ref_audit = (exd.get("reference") or "").strip()
        if body.get("reference") is not None and str(body.get("reference")) != str(exd.get("reference") or ""):
            audit_detail["reference"] = body.get("reference")
        if body.get("duree_heures") is not None and float(body.get("duree_heures")) != float(exd.get("duree_heures") or 0):
            audit_detail["duree_heures"] = body.get("duree_heures")
        if body.get("statut") is not None and body.get("statut") != exd.get("statut"):
            audit_detail["statut"] = body.get("statut")
        if body.get("client") is not None and body.get("client") != exd.get("client"):
            audit_detail["client"] = body.get("client")
        fsc_requis_new = (
            _parse_fsc_requis(body["fsc_requis"])
            if "fsc_requis" in body
            else int(exd.get("fsc_requis") or 0)
        )
        fsc_type_new = _parse_fsc_type_requis(
            body.get("fsc_type_requis", exd.get("fsc_type_requis")),
            fsc_requis_new,
        )
        if "fsc_requis" in body and fsc_requis_new != int(exd.get("fsc_requis") or 0):
            audit_detail["fsc_requis"] = fsc_requis_new
        if (
            "fsc_requis" in body
            or "fsc_type_requis" in body
        ) and fsc_type_new != (exd.get("fsc_type_requis") or "").strip():
            audit_detail["fsc_type_requis"] = fsc_type_new
        statut_auto = compute_statut(exd)
        set_manual_end = _body_flag_true(body.get("planned_end_manual"))
        clear_manual_end = body.get("planned_end_manual") is not None and not set_manual_end
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
        manual_end_explicit = (
            not clear_plan
            and not invalidate_dur
            and not termine_reposition
            and set_manual_end
            and body.get("planned_end") is not None
        )

        if clear_plan or invalidate_dur:
            ps = None
            pe = None
        elif manual_end_explicit:
            ps_dt = _parse_planned_dt(exd.get("planned_start"))
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

        # Recalcul fin de créneau si durée change (ancrage inchangé) — conserve l'override manuel
        if (
            not termine_reposition
            and not manual_end_explicit
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
                if set_manual_end:
                    pass  # planned_end_manual mis à 1 plus bas

        old_ps = exd.get("planned_start")
        old_pe = exd.get("planned_end")
        statut_reel_actuel = exd.get("statut_reel") or "reellement_en_attente"
        if statut_reel_actuel != "reellement_en_attente" and not termine_reposition and not manual_end_explicit:
            if old_ps and ps and str(ps) != str(old_ps):
                raise HTTPException(
                    status_code=409,
                    detail="Impossible de déplacer ce dossier : une saisie de production est en cours ou terminée.",
                )

        if clear_plan or clear_manual_end:
            planned_end_manual_val = 0
        elif set_manual_end:
            planned_end_manual_val = 1
        else:
            planned_end_manual_val = int(exd.get("planned_end_manual") or 0)

        conn.execute("""
            UPDATE planning_entries
            SET reference=?, client=?, description=?, format_l=?, format_h=?,
                duree_heures=?, statut=?, notes=?, updated_at=?, updated_by=?,
                dos_rvgi=?, numero_of=?, ref_produit=?, laize=?, date_livraison=?, commentaire=?,
                exigences_production=?, planned_start=?, planned_end=?, planned_end_manual=?, a_placer=?,
                fsc_requis=?, fsc_type_requis=?, departement_livraison=?, prise_rdv=?, date_livraison_imposee=?,
                valide=?, etiquettes_par_carton=?
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
            body.get(
                "exigences_production",
                ex["exigences_production"] if "exigences_production" in ex.keys() else None,
            ),
            ps,
            pe,
            planned_end_manual_val,
            body.get("a_placer", ex["a_placer"] if "a_placer" in ex.keys() else 0),
            fsc_requis_new,
            fsc_type_new,
            (body.get("departement_livraison") or "").strip()
            if "departement_livraison" in body
            else (ex["departement_livraison"] if "departement_livraison" in ex.keys() else ""),
            _parse_a_placer(body.get("prise_rdv"), default=int(exd.get("prise_rdv") or 0))
            if "prise_rdv" in body
            else int(exd.get("prise_rdv") or 0),
            _parse_a_placer(body.get("date_livraison_imposee"), default=int(exd.get("date_livraison_imposee") or 0))
            if "date_livraison_imposee" in body
            else int(exd.get("date_livraison_imposee") or 0),
            _parse_a_placer(body.get("valide"), default=int(exd.get("valide") or 0))
            if "valide" in body
            else int(exd.get("valide") or 0),
            _parse_etiq_par_carton(body.get("etiquettes_par_carton"))
            if "etiquettes_par_carton" in body
            else (exd.get("etiquettes_par_carton") if "etiquettes_par_carton" in ex.keys() else None),
            entry_id
        ))

        # Si un créneau planifié voit sa durée changer (donc planned_end bouge),
        # il faut pousser les dossiers suivants (non verrouillés) en invalidant
        # leurs dates; elles seront recalculées au prochain GET timeline.
        try:
            pe_changed = (
                duree is not None
                and old_ps
                and ps
                and str(ps) == str(old_ps)  # ancrage inchangé (resize)
                and (str(old_pe or "") != str(pe or ""))
            )
            if pe_changed:
                pos = conn.execute(
                    "SELECT position FROM planning_entries WHERE id=? AND machine_id=?",
                    (entry_id, machine_id),
                ).fetchone()
                if pos and pos["position"] is not None:
                    conn.execute(
                        """UPDATE planning_entries
                           SET planned_start=NULL, planned_end=NULL, updated_at=?
                           WHERE machine_id=?
                             AND position > ?
                             AND statut='attente'""",
                        (now, machine_id, int(pos["position"])),
                    )
        except Exception:
            pass
        conn.commit()
    log_action(
        user=user,
        action="UPDATE",
        module="planning",
        objet=f"Dossier {ref_audit}",
        detail=audit_detail or None,
        ip=request.client.host if request.client else None,
    )
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


@router.get("/machines/{machine_id}/entries/{entry_id}/production-stats")
def entry_production_stats(machine_id: int, entry_id: int, request: Request):
    """Statistiques de production du dossier (alignées MyProd > Production)."""
    with get_db() as conn:
        require_planning_machine(request, conn, machine_id)
        row = conn.execute(
            """SELECT id, reference, numero_of
               FROM planning_entries WHERE id=? AND machine_id=?""",
            (entry_id, machine_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entrée introuvable.")
        m = conn.execute(
            "SELECT nom, code FROM machines WHERE id=? AND actif=1",
            (machine_id,),
        ).fetchone()
        if not m:
            raise HTTPException(status_code=404, detail="Machine introuvable.")
        no_dossier = (row["numero_of"] or row["reference"] or "").strip()
        if not no_dossier:
            return build_dossier_production_stats([], "")
        mnom = (m["nom"] or "").strip()
        mcode = (m["code"] or "").strip()
        prod_rows = conn.execute(
            """SELECT id, operateur, date_operation, operation, operation_code,
                      operation_category, machine, no_dossier, client, designation,
                      quantite_a_traiter, quantite_traitee,
                      COALESCE(metrage_total_debut, metrage_prevu) AS metrage_prevu,
                      COALESCE(metrage_total_fin, metrage_reel) AS metrage_reel
               FROM production_data
               WHERE trim(no_dossier) = trim(?)
                 AND (
                   trim(machine) = trim(?)
                   OR (trim(?) != '' AND trim(machine) = trim(?))
                 )
               ORDER BY operateur, date_operation""",
            (no_dossier, mnom, mcode, mcode),
        ).fetchall()
    return build_dossier_production_stats([dict(r) for r in prod_rows], no_dossier)


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
                   planned_end_manual = 0,
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
    user = require_admin(request)
    now = datetime.now().isoformat()
    ref_audit = ""
    with get_db() as conn:
        ex = conn.execute(
            "SELECT * FROM planning_entries WHERE id=? AND machine_id=?",
            (entry_id, machine_id),
        ).fetchone()
        if not ex:
            raise HTTPException(404, "Entrée non trouvée")
        exd = dict(ex)
        ref_audit = (exd.get("reference") or "").strip()
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
            "exigences_production", "notes",
        ]
        payload = {c: exd.get(c) for c in cols}
        conn.execute(
            """INSERT INTO planning_entries
               (machine_id, position, reference, client, description, format_l, format_h,
                dos_rvgi, duree_heures, statut, notes, created_at, updated_at,
                numero_of, ref_produit, laize, date_livraison, commentaire, exigences_production)
               VALUES (?,?,?,?,?,?,?,?,?,'attente',?,?,?,?,?,?,?,?,?)""",
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
                payload.get("exigences_production"),
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
    log_action(
        user=user,
        action="CREATE",
        module="planning",
        objet=f"Scission dossier {ref_audit}",
        detail={"duree_1": d1, "duree_2": d2},
        ip=request.client.host if request.client else None,
    )
    return {"success": True, "split": [d1, d2]}


@router.delete("/machines/{machine_id}/entries/{entry_id}")
def delete_entry(machine_id: int, entry_id: int, request: Request):
    """Supprimer une entrée et recompacter les positions.
    Si l'entrée supprimée était en_cours, le premier dossier attente suivant est promu en_cours.
    """
    user = require_admin(request)
    ref_audit = ""
    machine_nom = ""
    with get_db() as conn:
        mac = conn.execute("SELECT nom FROM machines WHERE id=?", (machine_id,)).fetchone()
        machine_nom = (mac["nom"] or "") if mac else ""
        ex = conn.execute(
            """SELECT id, position, statut, statut_force, planned_start, planned_end, reference
               FROM planning_entries WHERE id=? AND machine_id=?""",
            (entry_id, machine_id)
        ).fetchone()
        if not ex:
            raise HTTPException(404, "Entrée non trouvée")
        ref_audit = (ex["reference"] or "").strip()

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
    log_action(
        user=user,
        action="DELETE",
        module="planning",
        objet=f"Dossier {ref_audit} · {machine_nom}",
        ip=request.client.host if request.client else None,
    )
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
                 numero_of, a_placer, valide)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, 0, 1)
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
    user = require_admin(request)
    body = await request.json()
    entry_ids = body.get("entry_ids", [])
    if not entry_ids:
        raise HTTPException(400, "entry_ids requis (liste ordonnée)")

    now = datetime.now().isoformat()
    machine_nom = ""
    with get_db() as conn:
        mac = conn.execute("SELECT nom FROM machines WHERE id=?", (machine_id,)).fetchone()
        machine_nom = (mac["nom"] or "") if mac else ""
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
    log_action(
        user=user,
        action="REORDER",
        module="planning",
        objet=f"Réorganisation planning {machine_nom}",
        detail={"entry_ids": entry_ids},
        ip=request.client.host if request.client else None,
    )
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

    duree = _parse_duree_heures(body.get("duree_heures", 8))
    if duree < 0.75 or duree > 720:
        raise HTTPException(400, "Durée entre 0,75 et 720 heures")

    now = datetime.now().isoformat()
    date_liv = body.get("date_livraison")
    if date_liv is not None and not str(date_liv).strip():
        date_liv = None
    fsc_requis_val = _parse_fsc_requis(body.get("fsc_requis"), default=0)
    row_data = {
        "reference": reference,
        "client": body.get("client", "") or "",
        "description": body.get("description", "") or "",
        "format_l": body.get("format_l"),
        "format_h": body.get("format_h"),
        "duree_heures": duree,
        "statut": "attente",
        "notes": body.get("notes", "") or "",
        "created_at": now,
        "updated_at": now,
        "dos_rvgi": (body.get("dos_rvgi") or "").strip() or None,
        "numero_of": body.get("numero_of") or reference,
        "ref_produit": body.get("ref_produit"),
        "laize": body.get("laize"),
        "date_livraison": date_liv,
        "commentaire": body.get("commentaire", "") or "",
        "exigences_production": (body.get("exigences_production") or "").strip() or None,
        "a_placer": _parse_a_placer(body.get("a_placer"), default=1),
        "valide": _parse_a_placer(body.get("valide"), default=0),
        "fsc_requis": fsc_requis_val,
        "fsc_type_requis": _parse_fsc_type_requis(
            body.get("fsc_type_requis"), fsc_requis_val
        ),
        "departement_livraison": (body.get("departement_livraison") or "").strip() or "",
        "prise_rdv": _parse_a_placer(body.get("prise_rdv"), default=0),
        "date_livraison_imposee": _parse_a_placer(body.get("date_livraison_imposee"), default=0),
    }
    with get_db() as conn:
        pe_cols = _ensure_planning_entry_columns(conn)
        conn.execute(
            "UPDATE planning_entries SET position = position + 1 WHERE machine_id=? AND position >= ?",
            (machine_id, new_position)
        )
        insert_cols = ["machine_id", "position"] + [c for c in row_data if c in pe_cols]
        values = [machine_id, new_position] + [row_data[c] for c in insert_cols[2:]]
        conn.execute(
            f"INSERT INTO planning_entries ({', '.join(insert_cols)}) VALUES ({', '.join('?' * len(insert_cols))})",
            values,
        )
        new_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        _backfill_group_id(conn, new_id, pe_cols)
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
            """SELECT date, heure_debut, heure_fin,
                      COALESCE(journee_entiere, 0) AS journee_entiere
                 FROM planning_day_horaires
                WHERE machine_id=? AND date>=? AND date<=?
                ORDER BY date""",
            (machine_id, start, end),
        ).fetchall()
    return [
        {
            "date": r["date"],
            "heure_debut": r["heure_debut"],
            "heure_fin": r["heure_fin"],
            "journee_entiere": int(r["journee_entiere"] or 0),
        }
        for r in rows
    ]


@router.put("/machines/{machine_id}/day-horaires")
async def set_day_horaires(machine_id: int, request: Request):
    """Enregistre ou met à jour l'horaire pour une date précise.

    Body: {date:'YYYY-MM-DD', heure_debut: 5.0, heure_fin: 13.0, journee_entiere?: 0|1}
    Passer heure_debut==null supprime l'override.
    Quand journee_entiere==1, on force heure_debut=0 et heure_fin=24 (3×8).
    """
    require_admin(request)
    body = await request.json()
    date = (body.get("date") or "").strip()
    if not date:
        raise HTTPException(400, "date requise (YYYY-MM-DD)")

    je_raw = body.get("journee_entiere", 0)
    try:
        je = 1 if int(je_raw or 0) == 1 else 0
    except (TypeError, ValueError):
        je = 0

    # Suppression de l'override (heure_debut null ET pas de journee_entiere).
    if body.get("heure_debut") is None and je == 0:
        with get_db() as conn:
            conn.execute(
                "DELETE FROM planning_day_horaires WHERE machine_id=? AND date=?",
                (machine_id, date),
            )
            conn.commit()
        return {"success": True, "deleted": True}

    if je == 1:
        hd, hf = 0.0, 24.0
    else:
        try:
            hd = float(body["heure_debut"])
            hf = float(body["heure_fin"])
        except (TypeError, ValueError, KeyError):
            raise HTTPException(400, "heure_debut et heure_fin doivent être des nombres")
        if not (0 <= hd < hf <= 24):
            raise HTTPException(400, "Plage invalide : 0 ≤ début < fin ≤ 24")

    with get_db() as conn:
        conn.execute(
            """INSERT INTO planning_day_horaires (machine_id, date, heure_debut, heure_fin, journee_entiere)
               VALUES (?,?,?,?,?)
               ON CONFLICT(machine_id, date)
               DO UPDATE SET heure_debut=excluded.heure_debut,
                             heure_fin=excluded.heure_fin,
                             journee_entiere=excluded.journee_entiere""",
            (machine_id, date, hd, hf, je),
        )
        _invalidate_attente_plans(conn, machine_id)
        conn.commit()
    return {"success": True, "journee_entiere": je}


# ═══════════════════════════════════════════════════════════════
# JOURNÉE ENTIÈRE — default machine
# ═══════════════════════════════════════════════════════════════

@router.put("/machines/{machine_id}/journee-entiere")
async def set_machine_journee_entiere(machine_id: int, request: Request):
    """Active/désactive la journée entière par défaut sur une machine.

    Body: {"journee_entiere": 0|1}
    Quand actif, tous les jours travaillés de cette machine s'étendent de
    00:00 à 23:59, sauf override plus prioritaire (day override, week override).
    """
    user = require_admin(request)
    body = await request.json()
    try:
        je = 1 if int(body.get("journee_entiere", 0) or 0) == 1 else 0
    except (TypeError, ValueError):
        je = 0
    with get_db() as conn:
        ex = conn.execute("SELECT id, nom FROM machines WHERE id=?", (machine_id,)).fetchone()
        if not ex:
            raise HTTPException(404, "Machine non trouvée")
        conn.execute(
            "UPDATE machines SET journee_entiere=? WHERE id=?",
            (je, machine_id),
        )
        _invalidate_attente_plans(conn, machine_id)
        conn.commit()
    try:
        log_action(
            user=user,
            action="UPDATE",
            module="planning",
            objet=f"Journée entière machine {ex['nom']}",
            detail={"journee_entiere": je},
            ip=request.client.host if request.client else None,
        )
    except Exception:
        pass
    return {"success": True, "journee_entiere": je}


# ═══════════════════════════════════════════════════════════════
# COMMENTAIRES TIMELINE (semaine / jour)
# ═══════════════════════════════════════════════════════════════


def _iso_week_keys_between(start: str, end: str) -> List[str]:
    """Clés ISO semaine (YYYY-Www) couvrant la plage [start, end] inclusive."""
    try:
        d0 = datetime.strptime(start, "%Y-%m-%d").date()
        d1 = datetime.strptime(end, "%Y-%m-%d").date()
    except ValueError:
        return []
    if d1 < d0:
        d0, d1 = d1, d0
    keys: set = set()
    cur = d0
    while cur <= d1:
        ic = cur.isocalendar()
        keys.add(f"{ic[0]}-W{ic[1]:02d}")
        cur += timedelta(days=1)
    return sorted(keys)


@router.get("/machines/{machine_id}/calendar-comments")
def list_calendar_comments(machine_id: int, request: Request, start: str, end: str):
    """Commentaires semaine (planning_config.notes) et jour sur une plage YYYY-MM-DD."""
    require_planning_view(request)
    week_keys = _iso_week_keys_between(start, end)
    with get_db() as conn:
        require_planning_machine(request, conn, machine_id)
        week_comments: dict = {}
        if week_keys:
            ph = ",".join("?" * len(week_keys))
            rows = conn.execute(
                f"""SELECT semaine, notes FROM planning_config
                    WHERE machine_id=? AND semaine IN ({ph})
                      AND TRIM(COALESCE(notes, '')) != ''""",
                (machine_id, *week_keys),
            ).fetchall()
            week_comments = {str(r["semaine"]): str(r["notes"] or "") for r in rows}
        day_rows = conn.execute(
            """SELECT date, comment FROM planning_day_comments
               WHERE machine_id=? AND date>=? AND date<=?
                 AND TRIM(COALESCE(comment, '')) != ''
               ORDER BY date""",
            (machine_id, start, end),
        ).fetchall()
    day_comments = {str(r["date"]): str(r["comment"] or "") for r in day_rows}
    return {"week_comments": week_comments, "day_comments": day_comments}


@router.put("/machines/{machine_id}/week-comment")
async def set_week_comment(machine_id: int, request: Request):
    """Body: {semaine: '2026-W20', comment: '...'} — ne modifie pas samedi_travaille."""
    require_admin(request)
    body = await request.json()
    semaine = (body.get("semaine") or "").strip()
    if not semaine:
        raise HTTPException(400, "semaine requise")
    comment = (body.get("comment") or "").strip()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO planning_config (machine_id, semaine, samedi_travaille, notes)
               VALUES (?, ?, 0, ?)
               ON CONFLICT(machine_id, semaine) DO UPDATE SET notes=excluded.notes""",
            (machine_id, semaine, comment),
        )
        conn.commit()
    return {"success": True, "semaine": semaine, "comment": comment}


@router.put("/machines/{machine_id}/day-comment")
async def set_day_comment(machine_id: int, request: Request):
    """Body: {date: 'YYYY-MM-DD', comment: '...'}"""
    require_admin(request)
    body = await request.json()
    date = (body.get("date") or "").strip()
    if not date:
        raise HTTPException(400, "date requise")
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "date invalide (YYYY-MM-DD)")
    comment = (body.get("comment") or "").strip()
    with get_db() as conn:
        if comment:
            conn.execute(
                """INSERT INTO planning_day_comments (machine_id, date, comment, updated_at)
                   VALUES (?, ?, ?, datetime('now'))
                   ON CONFLICT(machine_id, date)
                   DO UPDATE SET comment=excluded.comment, updated_at=datetime('now')""",
                (machine_id, date, comment),
            )
        else:
            conn.execute(
                "DELETE FROM planning_day_comments WHERE machine_id=? AND date=?",
                (machine_id, date),
            )
        conn.commit()
    return {"success": True, "date": date, "comment": comment}


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
        d = dict(row)
        d["journee_entiere"] = int(d.get("journee_entiere") or 0)
        return d
    return {"machine_id": machine_id, "semaine": semaine, "samedi_travaille": 0, "notes": "", "journee_entiere": 0}


@router.put("/machines/{machine_id}/config")
async def set_week_config(machine_id: int, request: Request):
    """Définir la config d'une semaine. Body: {"semaine": "2026-W14", "samedi_travaille": 1}"""
    require_admin(request)
    body = await request.json()
    semaine = body.get("semaine")
    if not semaine:
        today = datetime.now()
        semaine = f"{today.year}-W{today.isocalendar()[1]:02d}"

    try:
        je = 1 if int(body.get("journee_entiere", 0) or 0) == 1 else 0
    except (TypeError, ValueError):
        je = 0

    with get_db() as conn:
        conn.execute("""
            INSERT INTO planning_config (machine_id, semaine, samedi_travaille, notes, journee_entiere)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(machine_id, semaine)
            DO UPDATE SET samedi_travaille=excluded.samedi_travaille,
                          notes=excluded.notes,
                          journee_entiere=excluded.journee_entiere
        """, (
            machine_id, semaine,
            body.get("samedi_travaille", 0),
            body.get("notes", ""),
            je,
        ))
        _invalidate_attente_plans(conn, machine_id)
        conn.commit()
    return {"success": True, "journee_entiere": je}


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

        configs, off_days, day_worked_map, day_horaires_map = _load_planning_calendar_maps(
            conn, machine_id
        )

        _auto_complete_en_cours(conn, machine_id)
        _enforce_single_en_cours(conn, machine_id)

        # Nom de la machine courante : utilisé pour sélectionner, parmi
        # plusieurs fiches techniques partageant la même référence produit,
        # celle dont la machine correspond au planning courant.
        machine_nom_row = conn.execute(
            "SELECT nom FROM machines WHERE id=?", (machine_id,)
        ).fetchone()
        machine_nom = machine_nom_row["nom"] if machine_nom_row else ""

        rows = conn.execute(
            """
            SELECT pe.*,
                   oi.qte_etiquettes  AS _of_qte_etiquettes,
                   oi.qte_bobines     AS _of_qte_bobines,
                   ft.nb_bobines_carton          AS _ft_nb_bobines_carton,
                   ft.palette_nb_cartons_sol     AS _ft_palette_nb_cartons_sol,
                   ft.palette_nb_cartons_hauteur AS _ft_palette_nb_cartons_hauteur,
                   ft.support                    AS _ft_support,
                   ft.adhesif                    AS _ft_adhesif,
                   ft.palette_type               AS _ft_palette_type,
                   ft.cartons                    AS _ft_cartons,
                   ft.mandrin_dia                AS _ft_mandrin_dia,
                   ft.nb_etiq_bobin              AS _ft_nb_etiq_bobin
            FROM planning_entries pe
            LEFT JOIN of_imports oi
                ON oi.id = pe.of_import_id
            -- Liaison fiche ↔ dossier : on matche en priorité sur la clé
            -- produit normalisée (XXX/NNNN), insensible aux variantes
            -- machine/laize présentes dans le libellé. Quand plusieurs
            -- fiches partagent la même clé (une variante par machine),
            -- on retient celle dont `machine` correspond à la machine
            -- courante du planning. Fallback sur la référence textuelle
            -- complète pour les fiches non encore re-parsées.
            LEFT JOIN fiches_techniques ft ON ft.id = (
                SELECT ft2.id FROM fiches_techniques ft2
                WHERE COALESCE(NULLIF(TRIM(ft2.ref_produit_norm), ''),
                               LOWER(TRIM(ft2.reference)))
                    = COALESCE(NULLIF(TRIM(pe.ref_produit_norm), ''),
                               LOWER(TRIM(pe.ref_produit)))
                ORDER BY
                  CASE
                    WHEN LOWER(TRIM(COALESCE(ft2.machine,''))) = LOWER(TRIM(?))
                         AND TRIM(COALESCE(ft2.machine,'')) != '' THEN 0
                    WHEN TRIM(COALESCE(ft2.machine,'')) = '' THEN 1
                    ELSE 2
                  END,
                  ft2.id
                LIMIT 1
            )
            WHERE pe.machine_id = ?
            ORDER BY pe.position ASC
            """,
            (machine_nom or "", machine_id),
        ).fetchall()
        entries_list = [dict(r) for r in rows]

        # Les dossiers "à placer" doivent apparaître à la suite de la timeline,
        # pas intercalés (sinon superpositions visuelles avec les dossiers planifiés).
        # On garde l'ordre relatif (position) dans chaque groupe.
        main_entries: List[dict] = []
        aplacer_entries: List[dict] = []
        for e in entries_list:
            try:
                st = (e.get("statut") or "attente").strip()
                ap = int(e.get("a_placer") or 0)
            except Exception:
                st = (e.get("statut") or "attente").strip()
                ap = 0
            if st == "attente" and ap == 1:
                aplacer_entries.append(e)
            else:
                main_entries.append(e)
        entries_list = main_entries + aplacer_entries

        slots = _compute_timeline_slots(
            conn,
            machine_id,
            dict(machine),
            configs,
            off_days,
            day_worked_map,
            day_horaires_map,
            entries_list,
        )
        conn.commit()

    return {
        "machine": dict(machine),
        "slots": slots,
        "configs": configs,
    }


@router.post("/machines/{machine_id}/pack-termines")
async def pack_termines(machine_id: int, request: Request):
    """Recale les dossiers terminés les uns derrière les autres pour terminer à "maintenant" (arrondi à l'heure).

    - Ne modifie que les entrées statut='termine'
    - Affecte planned_start/planned_end en conséquence (persisté)
    """
    require_admin(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    end_iso = (body.get("end_iso") or "").strip()

    with get_db() as conn:
        require_planning_machine(request, conn, machine_id)
        mrow = conn.execute("SELECT * FROM machines WHERE id=?", (machine_id,)).fetchone()
        if not mrow:
            raise HTTPException(404, "Machine non trouvée")
        m = dict(mrow)

        # Cible : maintenant, arrondi à l'heure (heure Paris)
        if end_iso:
            dt_end = _parse_planned_dt(end_iso)
            if not dt_end:
                raise HTTPException(status_code=400, detail="end_iso invalide.")
            dt_end = dt_end.replace(minute=0, second=0, microsecond=0)
        else:
            dt_end = datetime.now(_TZ_PARIS).replace(tzinfo=None, minute=0, second=0, microsecond=0)

        # Charger calendrier étendu (peut remonter loin pour les terminés)
        configs, off_days, day_worked_map, day_horaires_map = _load_planning_calendar_maps_range(
            conn, machine_id
        )
        get_hours_for_date = _hours_for_date_factory(
            m, configs, off_days, day_worked_map, day_horaires_map
        )

        def prev_work_instant(dt: datetime) -> datetime:
            """Dernier instant <= dt qui est dans une fenêtre ouvrée (ou fin de fenêtre si dt après)."""
            cur = dt.replace(microsecond=0)
            for _ in range(366 * 3):
                win = get_hours_for_date(cur)
                if win:
                    s, e = win
                    sod = datetime(cur.year, cur.month, cur.day, 0, 0, 0, 0)
                    start_dt = sod + timedelta(hours=s)
                    end_dt = sod + timedelta(hours=e)
                    if cur > end_dt:
                        return end_dt.replace(second=0, microsecond=0)
                    if cur >= start_dt:
                        return cur.replace(second=0, microsecond=0)
                # reculer au jour précédent
                prev_day = datetime(cur.year, cur.month, cur.day, 0, 0, 0, 0) - timedelta(seconds=1)
                cur = prev_day.replace(microsecond=0)
            return cur.replace(second=0, microsecond=0)

        def rewind_work_hours(end_dt: datetime, hours: float) -> datetime:
            """Remonte 'hours' heures ouvrées avant end_dt (end_dt peut être hors fenêtre ouvrée)."""
            remaining = float(hours or 0.0)
            cur = prev_work_instant(end_dt)
            for _ in range(20000):
                if remaining <= 1e-9:
                    break
                win = get_hours_for_date(cur)
                if not win:
                    cur = prev_work_instant(cur - timedelta(days=1))
                    continue
                s, _e = win
                sod = datetime(cur.year, cur.month, cur.day, 0, 0, 0, 0)
                start_dt = sod + timedelta(hours=s)
                if cur <= start_dt:
                    cur = prev_work_instant(start_dt - timedelta(seconds=1))
                    continue
                avail = (cur - start_dt).total_seconds() / 3600.0
                used = min(remaining, max(0.0, avail))
                remaining -= used
                cur = (cur - timedelta(hours=used)).replace(second=0, microsecond=0)
                if remaining > 1e-9 and cur <= start_dt:
                    cur = prev_work_instant(start_dt - timedelta(seconds=1))
            return cur.replace(second=0, microsecond=0)

        terms = conn.execute(
            """SELECT id, position, duree_heures
               FROM planning_entries
               WHERE machine_id=? AND statut='termine'
               ORDER BY position ASC""",
            (machine_id,),
        ).fetchall()
        terms_list = [dict(r) for r in terms]

        now_u = datetime.now().isoformat()
        updated = 0
        end_cur = dt_end
        for e in reversed(terms_list):
            try:
                dur = float(e.get("duree_heures") or 0.0)
            except Exception:
                dur = 0.0
            if dur <= 1e-6:
                continue
            start_cur = rewind_work_hours(end_cur, dur)
            conn.execute(
                """UPDATE planning_entries
                   SET planned_start=?, planned_end=?, updated_at=?
                   WHERE id=? AND machine_id=?""",
                (_fmt_ts(start_cur), _fmt_ts(end_cur), now_u, int(e["id"]), machine_id),
            )
            updated += 1
            end_cur = start_cur

        conn.commit()

    return {"success": True, "updated": updated, "end": _fmt_ts(dt_end)}


@router.post("/machines/{machine_id}/pack-attente")
async def pack_attente(machine_id: int, request: Request):
    """Recale les dossiers en attente les uns derrière les autres (durées en heures ouvrées machine).

    - Ne modifie que les entrées statut='attente'
    - Point d'ancrage : fin du dossier "en cours" si planifiée, sinon maintenant (arrondi à l'heure)
    - Affecte planned_start/planned_end (persisté) et remet planned_end_manual à 0
    """
    require_admin(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    start_iso = (body.get("start_iso") or "").strip()

    with get_db() as conn:
        require_planning_machine(request, conn, machine_id)
        mrow = conn.execute("SELECT * FROM machines WHERE id=?", (machine_id,)).fetchone()
        if not mrow:
            raise HTTPException(404, "Machine non trouvée")
        m = dict(mrow)

        cfgs, off, dw, dh = _load_planning_calendar_maps(conn, machine_id)
        advance_to_work, consume_from = _make_work_duration_consumer(m, cfgs, off, dw, dh)

        # Ancrage : fin en_cours, sinon start_iso, sinon maintenant (arrondi à l'heure, heure Paris)
        anchor = conn.execute(
            """SELECT planned_end, planned_start, duree_heures
               FROM planning_entries
               WHERE machine_id=? AND statut='en_cours'
               ORDER BY position ASC LIMIT 1""",
            (machine_id,),
        ).fetchone()

        dt0: Optional[datetime] = None
        if anchor and (anchor["planned_end"] or "").strip():
            dt0 = _parse_planned_dt(anchor["planned_end"])
        if not dt0 and start_iso:
            dt0 = _parse_planned_dt(start_iso)
            if not dt0:
                raise HTTPException(status_code=400, detail="start_iso invalide.")
        if not dt0 and anchor and (anchor["planned_start"] or "").strip():
            dt_ps = _parse_planned_dt(anchor["planned_start"])
            if dt_ps:
                try:
                    dur = float(anchor["duree_heures"] or 0.0)
                except Exception:
                    dur = 0.0
                if dur > 1e-6:
                    _, dt0, _ = consume_from(dt_ps.replace(microsecond=0), dur)
        if not dt0:
            dt0 = datetime.now(_TZ_PARIS).replace(
                tzinfo=None, minute=0, second=0, microsecond=0
            )

        cursor = advance_to_work(dt0.replace(second=0, microsecond=0))

        waits = conn.execute(
            """SELECT id, position, duree_heures, a_placer
               FROM planning_entries
               WHERE machine_id=? AND statut='attente'
               ORDER BY position ASC""",
            (machine_id,),
        ).fetchall()
        waits_list = [dict(r) for r in waits]

        # Garder la logique "à placer" à la fin, comme la timeline.
        main_entries: List[dict] = []
        aplacer_entries: List[dict] = []
        for e in waits_list:
            try:
                ap = int(e.get("a_placer") or 0)
            except Exception:
                ap = 0
            (aplacer_entries if ap == 1 else main_entries).append(e)
        ordered = main_entries + aplacer_entries

        now_u = datetime.now().isoformat()
        updated = 0
        for e in ordered:
            try:
                dur = float(e.get("duree_heures") or 0.0)
            except Exception:
                dur = 0.0
            if dur <= 1e-6:
                continue
            slot_start, slot_end, cursor = consume_from(cursor, dur)
            conn.execute(
                """UPDATE planning_entries
                   SET planned_start=?, planned_end=?, planned_end_manual=0, updated_at=?
                   WHERE id=? AND machine_id=?""",
                (_fmt_ts(slot_start), _fmt_ts(slot_end), now_u, int(e["id"]), machine_id),
            )
            updated += 1

        conn.commit()

    return {"success": True, "updated": updated, "start": _fmt_ts(dt0)}


def _pack_termines_before_anchor(
    conn,
    machine_id: int,
    anchor_end_dt: datetime,
    only_before_position: Optional[int],
) -> int:
    """Recale les terminés (position < only_before_position) pour finir à anchor_end_dt.

    Ne modifie que les entrées statut='termine'.
    Retourne le nombre d'entrées mises à jour.
    """
    mrow = conn.execute("SELECT * FROM machines WHERE id=?", (machine_id,)).fetchone()
    if not mrow:
        return 0
    m = dict(mrow)

    configs, off_days, day_worked_map, day_horaires_map = _load_planning_calendar_maps_range(
        conn, machine_id
    )
    get_hours_for_date = _hours_for_date_factory(
        m, configs, off_days, day_worked_map, day_horaires_map
    )

    def prev_work_instant(dt: datetime) -> datetime:
        cur = dt.replace(microsecond=0)
        for _ in range(366 * 3):
            win = get_hours_for_date(cur)
            if win:
                s, e = win
                sod = datetime(cur.year, cur.month, cur.day, 0, 0, 0, 0)
                start_dt = sod + timedelta(hours=s)
                end_dt = sod + timedelta(hours=e)
                if cur > end_dt:
                    return end_dt.replace(second=0, microsecond=0)
                if cur >= start_dt:
                    return cur.replace(second=0, microsecond=0)
            prev_day = datetime(cur.year, cur.month, cur.day, 0, 0, 0, 0) - timedelta(seconds=1)
            cur = prev_day.replace(microsecond=0)
        return cur.replace(second=0, microsecond=0)

    def rewind_work_hours(end_dt: datetime, hours: float) -> datetime:
        remaining = float(hours or 0.0)
        cur = prev_work_instant(end_dt)
        for _ in range(20000):
            if remaining <= 1e-9:
                break
            win = get_hours_for_date(cur)
            if not win:
                cur = prev_work_instant(cur - timedelta(days=1))
                continue
            s, _e = win
            sod = datetime(cur.year, cur.month, cur.day, 0, 0, 0, 0)
            start_dt = sod + timedelta(hours=s)
            if cur <= start_dt:
                cur = prev_work_instant(start_dt - timedelta(seconds=1))
                continue
            avail = (cur - start_dt).total_seconds() / 3600.0
            used = min(remaining, max(0.0, avail))
            remaining -= used
            cur = (cur - timedelta(hours=used)).replace(second=0, microsecond=0)
            if remaining > 1e-9 and cur <= start_dt:
                cur = prev_work_instant(start_dt - timedelta(seconds=1))
        return cur.replace(second=0, microsecond=0)

    if only_before_position is None:
        rows = conn.execute(
            """SELECT id, position, duree_heures
               FROM planning_entries
               WHERE machine_id=? AND statut='termine'
               ORDER BY position ASC""",
            (machine_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT id, position, duree_heures
               FROM planning_entries
               WHERE machine_id=? AND statut='termine' AND position < ?
               ORDER BY position ASC""",
            (machine_id, int(only_before_position)),
        ).fetchall()

    terms_list = [dict(r) for r in rows]
    now_u = datetime.now().isoformat()

    updated = 0
    end_cur = anchor_end_dt
    for e in reversed(terms_list):
        try:
            dur = float(e.get("duree_heures") or 0.0)
        except Exception:
            dur = 0.0
        if dur <= 1e-6:
            continue
        start_cur = rewind_work_hours(end_cur, dur)
        conn.execute(
            """UPDATE planning_entries
               SET planned_start=?, planned_end=?, updated_at=?
               WHERE id=? AND machine_id=?""",
            (_fmt_ts(start_cur), _fmt_ts(end_cur), now_u, int(e["id"]), machine_id),
        )
        updated += 1
        end_cur = start_cur

    return updated


@router.post("/machines/{machine_id}/pack-termines-before-en-cours")
async def pack_termines_before_en_cours(machine_id: int, request: Request):
    """Recale les terminés *avant* le dossier en cours pour finir au début du en_cours.

    Les terminés restent ensuite figés sauf déplacement manuel.
    """
    require_admin(request)
    with get_db() as conn:
        require_planning_machine(request, conn, machine_id)

        # Anchor = planned_start du en_cours si possible, sinon "maintenant" arrondi à l'heure.
        row = conn.execute(
            """SELECT position, planned_start
               FROM planning_entries
               WHERE machine_id=? AND statut='en_cours'
               ORDER BY position ASC LIMIT 1""",
            (machine_id,),
        ).fetchone()
        if row and row["planned_start"]:
            dt_anchor = _parse_planned_dt(row["planned_start"])
        else:
            dt_anchor = datetime.now(_TZ_PARIS).replace(tzinfo=None)
        if not dt_anchor:
            dt_anchor = datetime.now(_TZ_PARIS).replace(tzinfo=None)
        dt_anchor = dt_anchor.replace(minute=0, second=0, microsecond=0)

        before_pos = int(row["position"]) if row and row["position"] is not None else None
        updated = _pack_termines_before_anchor(conn, machine_id, dt_anchor, before_pos)
        conn.commit()

    return {"success": True, "updated": updated, "anchor": _fmt_ts(dt_anchor)}


@router.post("/pack-termines-before-en-cours")
async def pack_termines_before_en_cours_all(request: Request):
    """Recale, sur toutes les machines actives, les terminés avant le en_cours."""
    require_admin(request)
    with get_db() as conn:
        mids = [
            int(r["id"])
            for r in conn.execute("SELECT id FROM machines WHERE actif=1").fetchall()
        ]
        out = []
        for mid in mids:
            try:
                row = conn.execute(
                    """SELECT position, planned_start
                       FROM planning_entries
                       WHERE machine_id=? AND statut='en_cours'
                       ORDER BY position ASC LIMIT 1""",
                    (mid,),
                ).fetchone()
                if row and row["planned_start"]:
                    dt_anchor = _parse_planned_dt(row["planned_start"])
                else:
                    dt_anchor = datetime.now(_TZ_PARIS).replace(tzinfo=None)
                if not dt_anchor:
                    dt_anchor = datetime.now(_TZ_PARIS).replace(tzinfo=None)
                dt_anchor = dt_anchor.replace(minute=0, second=0, microsecond=0)
                before_pos = int(row["position"]) if row and row["position"] is not None else None
                upd = _pack_termines_before_anchor(conn, mid, dt_anchor, before_pos)
                out.append({"machine_id": mid, "updated": upd})
            except Exception:
                out.append({"machine_id": mid, "updated": 0, "error": True})
        conn.commit()
    return {"success": True, "machines": out}


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
        # Temps écoulé en heures OUVRÉES machine (même calendrier que la timeline) :
        # les nuits, dimanches et jours non travaillés ne gonflent plus la durée.
        try:
            cfgs, off, dw, dh = _load_planning_calendar_maps(conn, machine_id)
        except Exception:
            return {"updated": False}
        get_hours_for_date = _hours_for_date_factory(dict(mac), cfgs, off, dw, dh)
        elapsed = _work_hours_between(get_hours_for_date, dt_start, now)
        # Quart d'heure supérieur : granularité UI, et évite un UPDATE par minute.
        elapsed = math.ceil(elapsed * 4 - 1e-9) / 4

        if elapsed <= current_dur or elapsed <= 0:
            return {"updated": False}

        planned_start = _fmt_ts(dt_start)
        # Fin de créneau cohérente : consommation de la durée en heures ouvrées.
        _, consume_from = _make_work_duration_consumer(dict(mac), cfgs, off, dw, dh)
        _, pe_dt, _ = consume_from(dt_start.replace(microsecond=0), float(elapsed))
        planned_end = _fmt_ts(pe_dt)
        conn.execute(
            """UPDATE planning_entries
               SET duree_heures=?, planned_start=?, planned_end=?, updated_at=?, updated_by=?
               WHERE id=?""",
            (elapsed, planned_start, planned_end, datetime.now().isoformat(), "Auto", entry_id),
        )
        conn.commit()
        return {"updated": True, "entry_id": entry_id, "duree_heures": elapsed}


@router.patch("/machines/{machine_id}/entries/{entry_id}/etiquettes-par-carton")
async def update_etiquettes_par_carton(machine_id: int, entry_id: int, request: Request):
    """Modifie le parametrage etiquettes_par_carton d'un dossier.

    Endpoint specifique pour permettre aux operateurs Repiquage de modifier la
    valeur (le PUT global est reserve aux admins). Si l'auteur n'est pas admin,
    un message est cree dans la messagerie a destination du superadmin pour
    qu'il puisse valider/auditer la modification.
    """
    from config import SUPERADMIN_EMAIL
    from services.auth_service import is_admin, is_fabrication

    user = get_current_user(request)
    if not (is_admin(user) or is_fabrication(user)):
        raise HTTPException(403, "Acces non autorise")

    body = await request.json()
    new_val = _parse_etiq_par_carton(body.get("etiquettes_par_carton"))
    # new_val peut etre None : signifie "effacer le parametrage"

    user_name = user.get("nom") or user.get("email") or "Operateur"
    now = datetime.now().isoformat()

    with get_db() as conn:
        ex = conn.execute(
            "SELECT * FROM planning_entries WHERE id=? AND machine_id=?",
            (entry_id, machine_id),
        ).fetchone()
        if not ex:
            raise HTTPException(404, "Entree non trouvee")

        exd = dict(ex)
        old_val = exd.get("etiquettes_par_carton")
        try:
            old_val = int(old_val) if old_val is not None else None
        except (TypeError, ValueError):
            old_val = None
        if old_val == new_val:
            return {"success": True, "unchanged": True, "etiquettes_par_carton": new_val}

        conn.execute(
            "UPDATE planning_entries SET etiquettes_par_carton=?, updated_at=?, updated_by=? WHERE id=?",
            (new_val, now, user_name, entry_id),
        )
        conn.commit()

        ref = (exd.get("reference") or "").strip() or f"#{entry_id}"
        client = (exd.get("client") or "").strip()
        machine_row = conn.execute(
            "SELECT nom FROM machines WHERE id=?", (machine_id,)
        ).fetchone()
        machine_nom = (machine_row["nom"] if machine_row else "?") or "?"

        # Notification superadmin uniquement si modificateur != admin
        if not is_admin(user):
            old_label = str(old_val) if old_val is not None else "(non defini)"
            new_label = str(new_val) if new_val is not None else "(efface)"
            from_email = (user.get("email") or "").strip().lower()
            from_user_id = int(user.get("id")) if user.get("id") is not None else None
            from_name = f"[Repiquage] {user_name}"
            subject = f"[Repiquage] Parametrage carton modifie - OF {ref}"
            body_msg = (
                f"L'operateur {user_name} a modifie le parametrage "
                f"'etiquettes par carton' du dossier {ref}"
                + (f" ({client})" if client else "")
                + f" sur la machine {machine_nom}.\n\n"
                f"Ancienne valeur : {old_label}\n"
                f"Nouvelle valeur : {new_label}\n\n"
                f"A valider/auditer dans le planning machine."
            )
            try:
                conn.execute(
                    """INSERT INTO messages
                       (from_user_id, from_email, from_name, to_email, subject, body, created_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (
                        from_user_id,
                        from_email,
                        from_name,
                        (SUPERADMIN_EMAIL or "").strip().lower(),
                        subject,
                        body_msg,
                        now,
                    ),
                )
                conn.commit()
            except Exception:
                # Ne jamais bloquer la modification metier pour un echec de notif
                pass

    log_action(
        user=user,
        action="UPDATE",
        module="planning",
        objet=f"Parametrage carton dossier {ref}",
        detail={"old": old_val, "new": new_val, "notif_admin": not is_admin(user)},
        ip=request.client.host if request.client else None,
    )
    return {"success": True, "etiquettes_par_carton": new_val}
