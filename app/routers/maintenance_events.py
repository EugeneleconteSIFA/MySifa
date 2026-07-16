"""MySifa — API Maintenance Events
Endpoints pour la gestion des créneaux de maintenance (multi-op + multi-opérateur).

Modèle : voir migration v158 dans app/core/database.py, complétée v162
(machines_csv par op → un créneau peut couvrir plusieurs machines).

- `maintenance_events` (le créneau : machine résumé CSV, date, heures, source)
- `maintenance_event_ops` (les opérations : statut + saisie partagée par le groupe,
  `machines_csv` = machine(s) attribuée(s) à l'opération)
- `maintenance_event_operators` (les opérateurs assignés)

Contrôle d'accès :
- Admin (superadmin, direction, administration) : CRUD complet.
- Opérateur (fabrication) : accès uniquement si le flag global
  `MAINTENANCE_OPEN_BETA` est actif dans .env. Peut :
  - Lire les events où il est dans le groupe (endpoint `/my-tasks`).
  - Mettre à jour statut/saisie d'une op **si** il est dans le groupe.
  - Créer un event `source=non_planifie` avec lui-même comme seul opérateur.
"""
from datetime import datetime
from typing import Any, Optional, List
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.database import get_db
from app.services.auth_service import get_current_user, effective_role
from config import (
    ROLE_SUPERADMIN,
    ROLE_DIRECTION,
    ROLE_ADMINISTRATION,
    ROLE_FABRICATION,
    MAINTENANCE_OPEN_BETA,
)


router = APIRouter(tags=["maintenance-events"])


# ─── Constantes / helpers ─────────────────────────────────────────

_ADMIN_ROLES = {ROLE_SUPERADMIN, ROLE_DIRECTION, ROLE_ADMINISTRATION}
_PARIS = ZoneInfo("Europe/Paris")

_VALID_STATUTS = {"a_faire", "en_cours", "termine", "reporte"}
_VALID_SOURCES = {"planifie", "non_planifie"}

# Séparateur utilisé pour stocker plusieurs machines dans machines_csv.
# " · " reste visuellement propre et évite le comma qui pourrait apparaître
# dans un futur libellé de machine.
_MACHINES_SEP = " · "


def _machines_csv_to_list(s):
    if not s:
        return []
    parts = [p.strip() for p in str(s).split(_MACHINES_SEP)]
    return [p for p in parts if p]


def _machines_list_to_csv(machines):
    if not machines:
        return None
    seen = []
    for m in machines:
        m = (m or "").strip()
        if m and m not in seen:
            seen.append(m)
    return _MACHINES_SEP.join(seen) if seen else None


def _normalize_op_spec(item):
    """Accepte un code brut (str) ou un dict {code, machines?}.
    Retourne (code, machines_csv_or_None)."""
    if isinstance(item, str):
        return item, None
    if isinstance(item, dict):
        code = str(item.get("code") or "").strip()
        if not code:
            raise HTTPException(status_code=400, detail="Op sans code")
        machines = item.get("machines") or []
        if not isinstance(machines, list):
            raise HTTPException(status_code=400, detail="machines doit être une liste")
        return code, _machines_list_to_csv(machines)
    raise HTTPException(status_code=400, detail=f"Format d'op invalide: {item!r}")


def _now_paris_iso() -> str:
    return datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")


def _get_maintenance_role(user: dict) -> Optional[str]:
    if not user:
        return None
    role = effective_role(user)
    if role in _ADMIN_ROLES:
        return "admin"
    if role == ROLE_FABRICATION and MAINTENANCE_OPEN_BETA:
        return "operator"
    return None


def _require_access(request: Request):
    user = get_current_user(request)
    maint_role = _get_maintenance_role(user)
    if maint_role is None:
        raise HTTPException(status_code=403, detail="Accès maintenance non autorisé")
    return user, maint_role


def _require_admin(request: Request) -> dict:
    user, maint_role = _require_access(request)
    if maint_role != "admin":
        raise HTTPException(status_code=403, detail="Réservé aux admins maintenance")
    return user


def _can_operator_manage_event(event: dict, user_id: int) -> bool:
    """Un opérateur peut modifier/supprimer un event qu'il a créé (peu importe
    la source). Depuis le "Nouvelle tâche" côté opérateur, il peut créer des
    events planifie avec N ops → il doit pouvoir les gérer ensuite.
    Sert de garde pour les endpoints PATCH/DELETE/ops côté opérateur."""
    if not event:
        return False
    return event.get("created_by") == user_id


def _user_in_group(conn, event_id: int, user_id: int) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM maintenance_event_operators WHERE event_id=? AND operator_id=? LIMIT 1",
        (event_id, user_id),
    ).fetchone())


def _validate_date(s: str) -> None:
    try:
        datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"date attendue au format YYYY-MM-DD: {s!r}")


def _validate_time(s: Optional[str]) -> None:
    if s is None:
        return
    try:
        datetime.strptime(s, "%H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"heure attendue au format HH:MM: {s!r}")


def _load_event_full(conn, event_id: int) -> Optional[dict]:
    """Retourne un dict enrichi {event, ops:[...], operators:[...]} ou None."""
    ev = conn.execute(
        """SELECT id, machine, nom, date_prevue, heure_debut, heure_fin, source,
                  template_id, created_by, created_at, updated_at
           FROM maintenance_events WHERE id = ?""",
        (event_id,),
    ).fetchone()
    if not ev:
        return None
    ops = conn.execute(
        """SELECT o.id, o.code, o.statut, o.duree_reelle_min, o.pieces_changees,
                  o.observations, o.photos_json, o.done_at, o.done_by,
                  o.updated_by, o.updated_at, o.machines_csv,
                  c.label     AS code_label,
                  c.categorie AS code_categorie
           FROM maintenance_event_ops o
           LEFT JOIN maintenance_codes c ON c.code = o.code
           WHERE o.event_id = ?
           ORDER BY o.id""",
        (event_id,),
    ).fetchall()
    ops_rows = conn.execute(
        """SELECT u.id, u.nom
           FROM maintenance_event_operators eo
           JOIN users u ON u.id = eo.operator_id
           WHERE eo.event_id = ?
           ORDER BY u.nom""",
        (event_id,),
    ).fetchall()
    ops_out = []
    for r in ops:
        d = dict(r)
        # Expose la liste parsée. Fallback à la machine du créneau pour la
        # rétrocompat des events créés avant la migration v162.
        machines = _machines_csv_to_list(d.get("machines_csv"))
        if not machines and ev["machine"]:
            machines = _machines_csv_to_list(ev["machine"])
        d["machines"] = machines
        ops_out.append(d)
    return {
        "id": ev["id"],
        "machine": ev["machine"],
        "nom": ev["nom"],
        "date_prevue": ev["date_prevue"],
        "heure_debut": ev["heure_debut"],
        "heure_fin": ev["heure_fin"],
        "source": ev["source"],
        "template_id": ev["template_id"],
        "created_by": ev["created_by"],
        "created_at": ev["created_at"],
        "updated_at": ev["updated_at"],
        "ops": ops_out,
        "operators": [dict(r) for r in ops_rows],
    }


def _recompute_event_machine(conn, event_id: int) -> None:
    """Recalcule maintenance_events.machine à partir de l'union des machines
    des ops enfants (résumé CSV). Appelé après tout add/update/delete op."""
    rows = conn.execute(
        "SELECT machines_csv FROM maintenance_event_ops WHERE event_id=?",
        (event_id,),
    ).fetchall()
    union = []
    for r in rows:
        for m in _machines_csv_to_list(r["machines_csv"]):
            if m not in union:
                union.append(m)
    if not union:
        return
    csv = _machines_list_to_csv(union) or ""
    conn.execute(
        "UPDATE maintenance_events SET machine=?, updated_at=? WHERE id=?",
        (csv, _now_paris_iso(), event_id),
    )


# ─── Body models ──────────────────────────────────────────────────

class EventCreateBody(BaseModel):
    # machine devient optionnelle : côté admin/planifié on peut désormais
    # avoir plusieurs machines dans le même créneau (attribuées par op).
    # Elle reste obligatoire côté opérateur (non_planifie, 1 seul code).
    machine: Optional[str] = None
    # nom libre du créneau ("Nettoyage matinal", "Grande révision", …), optionnel.
    nom: Optional[str] = None
    date_prevue: str                         # YYYY-MM-DD
    heure_debut: Optional[str] = None        # HH:MM (nullable si non planifié)
    heure_fin: Optional[str] = None          # HH:MM
    source: str = "planifie"
    # Chaque entrée : soit un code (str, legacy / non_planifie),
    # soit un objet {code: str, machines: List[str]} (nouveau format planifié).
    ops: List[Any] = []
    operators: List[int] = []                # liste d'ids user (peut être vide)
    # v163 : si le créneau est créé depuis un template, on trace le lien.
    # (Si fourni, ops/machines sont ignorés et pris depuis le template — voir
    # create_event.)
    template_id: Optional[int] = None


class EventUpdateBody(BaseModel):
    machine: Optional[str] = None
    nom: Optional[str] = None
    date_prevue: Optional[str] = None
    heure_debut: Optional[str] = None
    heure_fin: Optional[str] = None


class OpAddBody(BaseModel):
    code: str
    machines: Optional[List[str]] = None


class OpUpdateBody(BaseModel):
    statut: Optional[str] = None
    duree_reelle_min: Optional[int] = None
    pieces_changees: Optional[str] = None
    observations: Optional[str] = None
    photos_json: Optional[str] = None
    machines: Optional[List[str]] = None


class OperatorAddBody(BaseModel):
    operator_id: int


# ─── Endpoints — codes & opérateurs (utilitaires pickers) ────────

@router.get("/api/maintenance/operators")
def list_operators(request: Request):
    """Liste des utilisateurs assignables (rôle fabrication + actifs).
    Ouvert à admin et opérateur (l'opérateur peut désormais créer des tâches
    riches "à la admin" — cf. bouton Nouvelle tâche v163+)."""
    _require_access(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, nom, email, identifiant "
            "FROM users WHERE role = ? AND actif = 1 "
            "ORDER BY nom",
            (ROLE_FABRICATION,),
        ).fetchall()
    return {"operators": [dict(r) for r in rows]}


# ─── Endpoints — events ──────────────────────────────────────────

@router.get("/api/maintenance/events")
def list_events(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    machine: Optional[str] = None,
):
    """Liste des créneaux, filtres par plage de date et machine.

    - Admin voit tout.
    - Opérateur : voit tout aussi (le "Planning général" a besoin de la
      vue globale de la journée pour son onglet dédié).
    """
    _require_access(request)
    where, params = [], []
    if date_from:
        where.append("date_prevue >= ?"); params.append(date_from)
    if date_to:
        where.append("date_prevue <= ?"); params.append(date_to)
    if machine:
        # Comme `machine` peut désormais contenir un résumé CSV (ex.
        # "Cohésio 1 · DSI"), on filtre par match partiel — un event dont
        # une des machines match est retenu.
        where.append("machine LIKE ?"); params.append(f"%{machine}%")
    sql = ("SELECT id FROM maintenance_events "
           + ("WHERE " + " AND ".join(where) if where else "")
           + " ORDER BY date_prevue ASC, heure_debut ASC, id ASC")
    with get_db() as conn:
        ids = [r["id"] for r in conn.execute(sql, params).fetchall()]
        events = [_load_event_full(conn, eid) for eid in ids]
    return {"events": events}


@router.get("/api/maintenance/events/{event_id}")
def get_event(event_id: int, request: Request):
    _require_access(request)
    with get_db() as conn:
        ev = _load_event_full(conn, event_id)
    if ev is None:
        raise HTTPException(status_code=404, detail="Créneau introuvable")
    return {"event": ev}


@router.post("/api/maintenance/events")
def create_event(body: EventCreateBody, request: Request):
    """Crée un créneau avec ses N ops et M opérateurs.

    - Admin : `source=planifie` (défaut), avec heures et opérateurs libres.
      Depuis v162, chaque op porte sa liste de machines (multi-machines par créneau).
    - Opérateur : `source=non_planifie` forcé, sans heures, opérateur = self.
      1 seul code accepté (déclaration ponctuelle d'intervention), 1 machine.
    """
    user, maint_role = _require_access(request)
    _validate_date(body.date_prevue)
    _validate_time(body.heure_debut)
    _validate_time(body.heure_fin)

    src = body.source
    # v163 : si template_id fourni, on prend les ops+machines depuis le template
    # (ce qui garantit qu'un créneau instancié = copie fidèle du template).
    template_id = body.template_id
    if template_id and maint_role == "admin":
        with get_db() as tmpl_conn:
            tmpl = _load_template_full(tmpl_conn, template_id)
        if not tmpl:
            raise HTTPException(status_code=400, detail=f"Modèle inconnu: {template_id}")
        # On remplace body.ops par les ops du template (ignoré si fourni côté client)
        ops_from_tmpl = [{"code": o["code"], "machines": o.get("machines") or []} for o in tmpl["ops"]]
        body_ops_effective = ops_from_tmpl
    else:
        template_id = None  # opérateur n'utilise pas de template
        body_ops_effective = body.ops

    # Normalise chaque entrée en tuple (code, machines_csv_or_None), avec dedup
    # sur le code tout en conservant les machines de la première occurrence.
    seen_codes = {}
    for item in body_ops_effective:
        code, mcsv = _normalize_op_spec(item)
        if code not in seen_codes:
            seen_codes[code] = mcsv
    ops_specs = list(seen_codes.items())  # [(code, machines_csv_or_None), ...]
    operator_ids = list(dict.fromkeys(body.operators))

    if maint_role == "operator":
        # v163+ : l'opérateur peut créer soit une saisie rapide (non_planifie,
        # 1 code, self forcé — flow "Enregistrer une opération"), soit un
        # créneau planifie complet (N ops, N machines, N operators — flow
        # "Nouvelle tâche"). On détecte le mode via body.source.
        if src not in _VALID_SOURCES:
            raise HTTPException(status_code=400, detail=f"source invalide: {src}")
        if src == "non_planifie":
            heure_debut = None
            heure_fin = None
            operator_ids = [user["id"]]
            if len(ops_specs) != 1:
                raise HTTPException(status_code=400, detail="Une intervention non planifiée doit contenir exactement 1 code")
            if not body.machine:
                raise HTTPException(status_code=400, detail="machine requise pour une intervention non planifiée")
            ops_specs = [(ops_specs[0][0], _machines_list_to_csv([body.machine]))]
            event_machine = body.machine
        else:
            # source=planifie côté opérateur : mêmes règles qu'admin, sauf que
            # self doit être dans les opérateurs assignés (garde-fou anti-abus).
            heure_debut = body.heure_debut
            heure_fin = body.heure_fin
            if not ops_specs:
                raise HTTPException(status_code=400, detail="Au moins un code d'opération est requis")
            if user["id"] not in operator_ids:
                operator_ids = list(dict.fromkeys([user["id"]] + operator_ids))
            normalized = []
            machines_union = []
            for code, mcsv in ops_specs:
                if not mcsv:
                    if body.machine:
                        mcsv = _machines_list_to_csv([body.machine])
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"L'opération {code} doit être attribuée à au moins une machine",
                        )
                normalized.append((code, mcsv))
                for m in _machines_csv_to_list(mcsv):
                    if m not in machines_union:
                        machines_union.append(m)
            ops_specs = normalized
            event_machine = _machines_list_to_csv(machines_union) or (body.machine or "")
    else:
        if src not in _VALID_SOURCES:
            raise HTTPException(status_code=400, detail=f"source invalide: {src}")
        heure_debut = body.heure_debut
        heure_fin = body.heure_fin
        if not ops_specs:
            raise HTTPException(status_code=400, detail="Au moins un code d'opération est requis")
        # Toute op planifiée doit être rattachée à ≥1 machine (par op).
        # Sinon on retombe sur body.machine (rétrocompat).
        normalized = []
        machines_union = []
        for code, mcsv in ops_specs:
            if not mcsv:
                if body.machine:
                    mcsv = _machines_list_to_csv([body.machine])
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"L'opération {code} doit être attribuée à au moins une machine",
                    )
            normalized.append((code, mcsv))
            for m in _machines_csv_to_list(mcsv):
                if m not in machines_union:
                    machines_union.append(m)
        ops_specs = normalized
        # `maintenance_events.machine` : résumé CSV (rétrocompat filtres et
        # affichage sommaire). Si le body en fournissait une, on la respecte
        # tant qu'elle est cohérente ; sinon on la calcule.
        event_machine = _machines_list_to_csv(machines_union) or (body.machine or "")

    with get_db() as conn:
        # Vérif codes
        for code, _mcsv in ops_specs:
            if not conn.execute("SELECT 1 FROM maintenance_codes WHERE code=?", (code,)).fetchone():
                raise HTTPException(status_code=400, detail=f"code inconnu: {code}")
        # Vérif opérateurs
        for oid in operator_ids:
            if not conn.execute("SELECT 1 FROM users WHERE id=?", (oid,)).fetchone():
                raise HTTPException(status_code=400, detail=f"opérateur inconnu: {oid}")

        now = _now_paris_iso()
        # Nom libre (optionnel), stripé et normalisé à None si vide.
        nom_clean = (body.nom or "").strip() or None
        cur = conn.execute(
            """INSERT INTO maintenance_events
               (machine, nom, date_prevue, heure_debut, heure_fin, source,
                template_id, created_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (event_machine, nom_clean, body.date_prevue, heure_debut, heure_fin, src,
             template_id, user["id"], now),
        )
        event_id = cur.lastrowid
        # v179 : une op multi-machines = N lignes (une par machine). Chaque ligne
        # a son propre statut → validation indépendante par (op, machine).
        for code, mcsv in ops_specs:
            machines_for_op = _machines_csv_to_list(mcsv) or [None]
            for m in machines_for_op:
                single_csv = _machines_list_to_csv([m]) if m else None
                try:
                    conn.execute(
                        """INSERT INTO maintenance_event_ops (event_id, code, machines_csv, updated_at)
                           VALUES (?, ?, ?, ?)""",
                        (event_id, code, single_csv, now),
                    )
                except Exception as e:
                    # UNIQUE(event_id, code, machines_csv) : doublon silencieux (rare, mais safe).
                    pass
        for oid in operator_ids:
            conn.execute(
                "INSERT OR IGNORE INTO maintenance_event_operators (event_id, operator_id) VALUES (?, ?)",
                (event_id, oid),
            )
        conn.commit()
        ev = _load_event_full(conn, event_id)
    return {"event": ev}


@router.patch("/api/maintenance/events/{event_id}")
def update_event(event_id: int, body: EventUpdateBody, request: Request):
    """Admin : édition libre. Opérateur : uniquement ses propres non_planifie."""
    user, maint_role = _require_access(request)
    if body.date_prevue is not None: _validate_date(body.date_prevue)
    if body.heure_debut is not None: _validate_time(body.heure_debut)
    if body.heure_fin is not None:   _validate_time(body.heure_fin)

    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")

    with get_db() as conn:
        ev = _load_event_full(conn, event_id)
        if not ev:
            raise HTTPException(status_code=404, detail="Créneau introuvable")
        if maint_role == "operator":
            if not _can_operator_manage_event(ev, user["id"]):
                raise HTTPException(status_code=403, detail="Vous ne pouvez modifier que vos propres interventions non planifiées")
        updates["updated_at"] = _now_paris_iso()
        set_clause = ", ".join(f"{k}=?" for k in updates)
        conn.execute(f"UPDATE maintenance_events SET {set_clause} WHERE id=?",
                     list(updates.values()) + [event_id])
        conn.commit()
        ev = _load_event_full(conn, event_id)
    return {"event": ev}


@router.delete("/api/maintenance/events/{event_id}")
def delete_event(event_id: int, request: Request):
    """Admin : suppression libre. Opérateur : uniquement ses propres non_planifie."""
    user, maint_role = _require_access(request)
    with get_db() as conn:
        ev = _load_event_full(conn, event_id)
        if not ev:
            raise HTTPException(status_code=404, detail="Créneau introuvable")
        if maint_role == "operator":
            if not _can_operator_manage_event(ev, user["id"]):
                raise HTTPException(status_code=403, detail="Vous ne pouvez supprimer que vos propres interventions non planifiées")
        # CASCADE supprime ops et rattachements
        conn.execute("DELETE FROM maintenance_events WHERE id=?", (event_id,))
        conn.commit()
    return {"deleted": event_id}


# ─── Endpoints — event ops (les opérations du créneau) ───────────

@router.post("/api/maintenance/events/{event_id}/ops")
def add_op(event_id: int, body: OpAddBody, request: Request):
    """Admin : ajout libre. Opérateur : uniquement sur son propre non_planifie."""
    user, maint_role = _require_access(request)
    with get_db() as conn:
        ev_check = _load_event_full(conn, event_id)
        if not ev_check:
            raise HTTPException(status_code=404, detail="Créneau introuvable")
        if maint_role == "operator":
            if not _can_operator_manage_event(ev_check, user["id"]):
                raise HTTPException(status_code=403, detail="Vous ne pouvez modifier que vos propres interventions non planifiées")
        if not conn.execute("SELECT 1 FROM maintenance_codes WHERE code=?", (body.code,)).fetchone():
            raise HTTPException(status_code=400, detail=f"code inconnu: {body.code}")
        # v179 : une op multi-machines = N lignes. On boucle sur chaque machine
        # et on skip celles déjà présentes (idempotent). Erreur si TOUTES déjà là.
        wanted_machines = list(body.machines) if body.machines else [None]
        inserted = 0
        now = _now_paris_iso()
        for m in wanted_machines:
            single_csv = _machines_list_to_csv([m]) if m else None
            # Check existant pour ce couple (code, machine)
            if single_csv is None:
                exists = conn.execute(
                    "SELECT 1 FROM maintenance_event_ops WHERE event_id=? AND code=? AND machines_csv IS NULL",
                    (event_id, body.code),
                ).fetchone()
            else:
                exists = conn.execute(
                    "SELECT 1 FROM maintenance_event_ops WHERE event_id=? AND code=? AND machines_csv=?",
                    (event_id, body.code, single_csv),
                ).fetchone()
            if exists:
                continue
            conn.execute(
                "INSERT INTO maintenance_event_ops (event_id, code, machines_csv, updated_at) VALUES (?, ?, ?, ?)",
                (event_id, body.code, single_csv, now),
            )
            inserted += 1
        if inserted == 0:
            raise HTTPException(status_code=400, detail="Op déjà présente sur toutes les machines demandées")
        _recompute_event_machine(conn, event_id)
        conn.commit()
        ev = _load_event_full(conn, event_id)
    return {"event": ev}


@router.patch("/api/maintenance/events/{event_id}/ops/{op_id}")
def update_op(event_id: int, op_id: int, body: OpUpdateBody, request: Request):
    """Met à jour statut / saisie d'une op. Admin OU opérateur du groupe.
    Trace updated_by (dernier modifieur). Pose done_at + done_by au premier
    passage à termine."""
    user, maint_role = _require_access(request)

    with get_db() as conn:
        row = conn.execute(
            "SELECT event_id, statut, done_at FROM maintenance_event_ops WHERE id=?",
            (op_id,),
        ).fetchone()
        if not row or row["event_id"] != event_id:
            raise HTTPException(status_code=404, detail="Op introuvable dans ce créneau")

        if maint_role == "operator" and not _user_in_group(conn, event_id, user["id"]):
            raise HTTPException(status_code=403, detail="Vous n'êtes pas assigné à ce créneau")

        updates = {}
        machines_touched = False
        for k, v in body.model_dump(exclude_unset=True).items():
            if v is None: continue
            if k == "statut" and v not in _VALID_STATUTS:
                raise HTTPException(status_code=400, detail=f"statut invalide: {v}")
            if k == "machines":
                if maint_role != "admin":
                    raise HTTPException(status_code=403, detail="Réassignation machine réservée aux admins")
                updates["machines_csv"] = _machines_list_to_csv(v)
                machines_touched = True
                continue
            updates[k] = v
        if not updates:
            raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")

        now = _now_paris_iso()
        updates["updated_by"] = user["id"]
        updates["updated_at"] = now
        # Pose done_at + done_by au moment où l'op passe à termine.
        if updates.get("statut") == "termine" and not row["done_at"]:
            updates["done_at"] = now
            updates["done_by"] = user["id"]

        set_clause = ", ".join(f"{k}=?" for k in updates)
        conn.execute(f"UPDATE maintenance_event_ops SET {set_clause} WHERE id=?",
                     list(updates.values()) + [op_id])
        if machines_touched:
            _recompute_event_machine(conn, event_id)
        conn.commit()
        ev = _load_event_full(conn, event_id)
    return {"event": ev}


@router.delete("/api/maintenance/events/{event_id}/ops/{op_id}")
def delete_op(event_id: int, op_id: int, request: Request):
    """Admin : suppression libre. Opérateur : uniquement sur son propre non_planifie."""
    user, maint_role = _require_access(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT event_id FROM maintenance_event_ops WHERE id=?", (op_id,),
        ).fetchone()
        if not row or row["event_id"] != event_id:
            raise HTTPException(status_code=404, detail="Op introuvable dans ce créneau")
        if maint_role == "operator":
            ev_check = _load_event_full(conn, event_id)
            if not _can_operator_manage_event(ev_check, user["id"]):
                raise HTTPException(status_code=403, detail="Vous ne pouvez modifier que vos propres interventions non planifiées")
        conn.execute("DELETE FROM maintenance_event_ops WHERE id=?", (op_id,))
        _recompute_event_machine(conn, event_id)
        conn.commit()
        ev = _load_event_full(conn, event_id)
    return {"event": ev}


@router.post("/api/maintenance/events/{event_id}/ops/{op_id}/reset")
def reset_op(event_id: int, op_id: int, request: Request):
    """Annule la saisie d'une op (statut termine -> a_faire).
    - Efface done_at, done_by, duree_reelle_min, pieces_changees, observations.
    - Trace updated_by / updated_at (traçabilité minimale de l'annulation).
    - Perms : admin partout. Opérateur si dans le groupe assigné du créneau
      (identique à update_op) OU s'il a créé l'event.
    - La ligne dans l'historique (get_history) disparaît automatiquement puisque
      elle est filtrée par statut='termine'."""
    user, maint_role = _require_access(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT event_id, statut FROM maintenance_event_ops WHERE id=?",
            (op_id,),
        ).fetchone()
        if not row or row["event_id"] != event_id:
            raise HTTPException(status_code=404, detail="Op introuvable dans ce créneau")
        # Perms opérateur : dans le groupe OU créateur (cf. update_op / _can_operator_manage_event)
        if maint_role == "operator":
            ev_check = _load_event_full(conn, event_id)
            in_group = _user_in_group(conn, event_id, user["id"])
            is_owner = _can_operator_manage_event(ev_check, user["id"])
            if not (in_group or is_owner):
                raise HTTPException(status_code=403, detail="Vous n'êtes pas autorisé à annuler cette saisie")
        now = _now_paris_iso()
        conn.execute(
            """UPDATE maintenance_event_ops
               SET statut='a_faire',
                   duree_reelle_min=NULL,
                   pieces_changees=NULL,
                   observations=NULL,
                   done_at=NULL,
                   done_by=NULL,
                   updated_by=?,
                   updated_at=?
               WHERE id=?""",
            (user["id"], now, op_id),
        )
        conn.commit()
        ev = _load_event_full(conn, event_id)
    return {"event": ev}


# ─── Endpoints — event operators (le groupe) ─────────────────────

@router.post("/api/maintenance/events/{event_id}/operators")
def add_operator(event_id: int, body: OperatorAddBody, request: Request):
    """Admin : ajout libre. Opérateur : uniquement sur son propre event."""
    user, maint_role = _require_access(request)
    with get_db() as conn:
        ev_check = _load_event_full(conn, event_id)
        if not ev_check:
            raise HTTPException(status_code=404, detail="Créneau introuvable")
        if maint_role == "operator":
            if not _can_operator_manage_event(ev_check, user["id"]):
                raise HTTPException(status_code=403, detail="Vous ne pouvez modifier que vos propres événements")
        if not conn.execute("SELECT 1 FROM users WHERE id=?", (body.operator_id,)).fetchone():
            raise HTTPException(status_code=400, detail=f"opérateur inconnu: {body.operator_id}")
        conn.execute(
            "INSERT OR IGNORE INTO maintenance_event_operators (event_id, operator_id) VALUES (?, ?)",
            (event_id, body.operator_id),
        )
        conn.commit()
        ev = _load_event_full(conn, event_id)
    return {"event": ev}


@router.delete("/api/maintenance/events/{event_id}/operators/{operator_id}")
def remove_operator(event_id: int, operator_id: int, request: Request):
    """Admin : suppression libre. Opérateur : uniquement sur son propre event
    (et il ne peut pas se retirer lui-même sinon il perd les droits d'édition)."""
    user, maint_role = _require_access(request)
    with get_db() as conn:
        ev_check = _load_event_full(conn, event_id)
        if not ev_check:
            raise HTTPException(status_code=404, detail="Créneau introuvable")
        if maint_role == "operator":
            if not _can_operator_manage_event(ev_check, user["id"]):
                raise HTTPException(status_code=403, detail="Vous ne pouvez modifier que vos propres événements")
            if operator_id == user["id"]:
                raise HTTPException(status_code=400, detail="Impossible de se retirer soi-même du groupe (perte d'accès en cas d'erreur)")
        conn.execute(
            "DELETE FROM maintenance_event_operators WHERE event_id=? AND operator_id=?",
            (event_id, operator_id),
        )
        conn.commit()
        ev = _load_event_full(conn, event_id)
    return {"event": ev}


# ─── Endpoint spécifique opérateur ────────────────────────────────

@router.get("/api/maintenance/my-tasks")
def my_tasks(
    request: Request,
    date: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """Liste des events où l'user courant est dans le groupe (fabrication).

    Renvoie les events enrichis (ops + operators) comme /events. Le rôle admin
    peut aussi l'appeler pour voir ses propres assignations éventuelles."""
    user, _maint_role = _require_access(request)
    where = ["eo.operator_id = ?"]
    params = [user["id"]]
    if date:
        where.append("e.date_prevue = ?"); params.append(date)
    

# ─── Templates de session (v163) ─────────────────────────────────
#
# Un template = un ensemble prédéfini d'opérations (avec leurs machines) que
# l'admin peut instancier en tant que créneau. Modifier un template resynchronise
# automatiquement les créneaux futurs qui en dépendent (écrasement des ops).
# Supprimer un template supprime en cascade les créneaux futurs liés.


class TemplateOpSpec(BaseModel):
    code: str
    machines: List[str] = []


class TemplateCreateBody(BaseModel):
    name: str
    description: Optional[str] = None
    ops: List[TemplateOpSpec] = []


class TemplateUpdateBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    ops: Optional[List[TemplateOpSpec]] = None



@router.get("/api/maintenance/history")
def get_history(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    machine: Optional[str] = None,
    operator_id: Optional[int] = None,
    code: Optional[str] = None,
):
    """Historique des opérations terminées (source de vérité DB, partagée
    admin+opérateur). Retourne les ops statut=termine avec joins event+code+
    users, formatées pour la table "Historique des opérations".

    Filtres optionnels par plage de date (sur done_at OU date_prevue),
    machine, opérateur créateur/exécutant, code."""
    _require_access(request)
    where = ["o.statut = 'termine'"]
    params: List[Any] = []
    if date_from:
        _validate_date(date_from)
        where.append("(o.done_at >= ? OR e.date_prevue >= ?)")
        params.extend([date_from, date_from])
    if date_to:
        _validate_date(date_to)
        where.append("(o.done_at <= ? OR e.date_prevue <= ?)")
        # Ajoute un buffer à date_to pour couvrir toute la journée côté done_at
        params.extend([date_to + "T23:59:59", date_to])
    if code:
        where.append("o.code = ?")
        params.append(code)
    if machine:
        # Match dans l'union event.machine CSV OU op.machines_csv
        where.append("(e.machine LIKE ? OR o.machines_csv LIKE ?)")
        params.extend([f"%{machine}%", f"%{machine}%"])
    if operator_id:
        where.append("(o.done_by = ? OR e.created_by = ?)")
        params.extend([operator_id, operator_id])
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT o.id             AS op_id,
                       e.id             AS event_id,
                       e.machine        AS machine,
                       e.nom            AS event_nom,
                       o.machines_csv   AS op_machines_csv,
                       o.code           AS code,
                       c.label          AS code_label,
                       c.categorie      AS categorie,
                       o.duree_reelle_min AS duree_reelle_min,
                       o.observations   AS commentaire,
                       o.pieces_changees AS pieces_changees,
                       o.done_at        AS done_at,
                       o.done_by        AS done_by,
                       ub.nom           AS done_by_nom,
                       e.date_prevue    AS date_prevue,
                       e.created_by     AS created_by,
                       uc.nom           AS created_by_nom,
                       e.source         AS source
                FROM maintenance_event_ops o
                JOIN maintenance_events e ON e.id = o.event_id
                LEFT JOIN maintenance_codes c ON c.code = o.code
                LEFT JOIN users ub ON ub.id = o.done_by
                LEFT JOIN users uc ON uc.id = e.created_by
                WHERE {" AND ".join(where)}
                ORDER BY COALESCE(o.done_at, e.date_prevue) DESC, o.id DESC
                LIMIT 2000""",
            params,
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        # Machines : préfère op.machines_csv, fallback event.machine
        machines_list = _machines_csv_to_list(d.pop("op_machines_csv"))
        if not machines_list and d.get("machine"):
            machines_list = _machines_csv_to_list(d["machine"])
        d["machines"] = machines_list
        d["machine"] = " · ".join(machines_list) if machines_list else (d.get("machine") or "")
        # Date_saisie : done_at si présent (moment d'exécution enregistré),
        # sinon date_prevue (jour d'intervention déclaré).
        d["date_saisie"] = d.get("done_at") or d.get("date_prevue")
        # Opérateur : done_by en priorité (qui a marqué termine), fallback creator.
        d["operateur"] = d.get("done_by_nom") or d.get("created_by_nom") or ""
        d["type"] = d.get("code_label") or d.get("code") or ""
        out.append(d)
    return {"history": out}


def _load_template_full(conn, template_id: int) -> Optional[dict]:
    row = conn.execute(
        """SELECT id, name, description, created_by, created_at, updated_at
           FROM maintenance_templates WHERE id = ?""",
        (template_id,),
    ).fetchone()
    if not row:
        return None
    ops = conn.execute(
        """SELECT o.id, o.code, o.machines_csv,
                  c.label AS code_label, c.categorie AS code_categorie
           FROM maintenance_template_ops o
           LEFT JOIN maintenance_codes c ON c.code = o.code
           WHERE o.template_id = ?
           ORDER BY o.id""",
        (template_id,),
    ).fetchall()
    ops_out = []
    for o in ops:
        d = dict(o)
        d["machines"] = _machines_csv_to_list(d.get("machines_csv"))
        ops_out.append(d)
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "ops": ops_out,
    }


def _resync_future_events_from_template(conn, template_id: int) -> int:
    """Écrase les ops des créneaux futurs (date_prevue >= aujourd'hui) liés au
    template. Retourne le nombre d'events resynchronisés.
    Préserve : date, horaires, opérateurs, source. Écrase : liste des ops."""
    tmpl = _load_template_full(conn, template_id)
    if not tmpl:
        return 0
    today = datetime.now(_PARIS).strftime("%Y-%m-%d")
    events = conn.execute(
        "SELECT id FROM maintenance_events WHERE template_id = ? AND date_prevue >= ?",
        (template_id, today),
    ).fetchall()
    now = _now_paris_iso()
    for ev in events:
        eid = ev["id"]
        # Supprime toutes les ops existantes de l'event
        conn.execute("DELETE FROM maintenance_event_ops WHERE event_id = ?", (eid,))
        # Insère les ops du template (copie profonde des machines)
        for op in tmpl["ops"]:
            conn.execute(
                """INSERT INTO maintenance_event_ops (event_id, code, machines_csv, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (eid, op["code"], op.get("machines_csv"), now),
            )
        _recompute_event_machine(conn, eid)
    return len(events)


@router.get("/api/maintenance/templates")
def list_templates(request: Request):
    """Liste tous les templates (nom, description, nb d'ops). Admin only."""
    _require_admin(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT t.id, t.name, t.description, t.created_at, t.updated_at,
                      COUNT(o.id) AS ops_count
               FROM maintenance_templates t
               LEFT JOIN maintenance_template_ops o ON o.template_id = t.id
               GROUP BY t.id
               ORDER BY t.name""",
        ).fetchall()
    return {"templates": [dict(r) for r in rows]}


@router.get("/api/maintenance/templates/{template_id}")
def get_template(template_id: int, request: Request):
    """Détail d'un template (avec ses ops). Admin only."""
    _require_admin(request)
    with get_db() as conn:
        tmpl = _load_template_full(conn, template_id)
    if tmpl is None:
        raise HTTPException(status_code=404, detail="Modèle introuvable")
    return {"template": tmpl}


@router.post("/api/maintenance/templates")
def create_template(body: TemplateCreateBody, request: Request):
    """Crée un template. Admin only."""
    user = _require_admin(request)
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nom du modèle requis")
    if not body.ops:
        raise HTTPException(status_code=400, detail="Au moins une opération est requise")
    # Dedup sur code, garde les machines de la première occurrence
    seen = {}
    for spec in body.ops:
        code = (spec.code or "").strip()
        if not code:
            raise HTTPException(status_code=400, detail="Op sans code")
        if code not in seen:
            seen[code] = _machines_list_to_csv(spec.machines)
    with get_db() as conn:
        if conn.execute("SELECT 1 FROM maintenance_templates WHERE name = ?", (name,)).fetchone():
            raise HTTPException(status_code=400, detail=f"Un modèle nommé '{name}' existe déjà")
        for code, mcsv in seen.items():
            if not conn.execute("SELECT 1 FROM maintenance_codes WHERE code=?", (code,)).fetchone():
                raise HTTPException(status_code=400, detail=f"code inconnu: {code}")
            if not mcsv:
                raise HTTPException(status_code=400, detail=f"L'opération {code} doit être attribuée à au moins une machine")
        now = _now_paris_iso()
        cur = conn.execute(
            """INSERT INTO maintenance_templates (name, description, created_by, created_at)
               VALUES (?, ?, ?, ?)""",
            (name, body.description, user["id"], now),
        )
        template_id = cur.lastrowid
        for code, mcsv in seen.items():
            conn.execute(
                "INSERT INTO maintenance_template_ops (template_id, code, machines_csv) VALUES (?, ?, ?)",
                (template_id, code, mcsv),
            )
        conn.commit()
        tmpl = _load_template_full(conn, template_id)
    return {"template": tmpl}


@router.patch("/api/maintenance/templates/{template_id}")
def update_template(template_id: int, body: TemplateUpdateBody, request: Request):
    """Met à jour un template. Si les ops changent, resync les créneaux futurs."""
    _require_admin(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name FROM maintenance_templates WHERE id = ?",
            (template_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Modèle introuvable")
        now = _now_paris_iso()
        # Métadonnées (name, description)
        meta_updates = {}
        if body.name is not None:
            new_name = body.name.strip()
            if not new_name:
                raise HTTPException(status_code=400, detail="Nom vide non autorisé")
            if new_name != row["name"]:
                dup = conn.execute(
                    "SELECT 1 FROM maintenance_templates WHERE name = ? AND id != ?",
                    (new_name, template_id),
                ).fetchone()
                if dup:
                    raise HTTPException(status_code=400, detail=f"Un modèle nommé '{new_name}' existe déjà")
                meta_updates["name"] = new_name
        if body.description is not None:
            meta_updates["description"] = body.description
        if meta_updates:
            meta_updates["updated_at"] = now
            set_clause = ", ".join(f"{k}=?" for k in meta_updates)
            conn.execute(
                f"UPDATE maintenance_templates SET {set_clause} WHERE id = ?",
                list(meta_updates.values()) + [template_id],
            )
        # Ops (si fournies, on remplace intégralement)
        resynced = 0
        if body.ops is not None:
            if not body.ops:
                raise HTTPException(status_code=400, detail="Au moins une opération est requise")
            seen = {}
            for spec in body.ops:
                code = (spec.code or "").strip()
                if not code:
                    raise HTTPException(status_code=400, detail="Op sans code")
                if code not in seen:
                    seen[code] = _machines_list_to_csv(spec.machines)
            for code, mcsv in seen.items():
                if not conn.execute("SELECT 1 FROM maintenance_codes WHERE code=?", (code,)).fetchone():
                    raise HTTPException(status_code=400, detail=f"code inconnu: {code}")
                if not mcsv:
                    raise HTTPException(status_code=400, detail=f"L'opération {code} doit être attribuée à au moins une machine")
            conn.execute("DELETE FROM maintenance_template_ops WHERE template_id = ?", (template_id,))
            for code, mcsv in seen.items():
                conn.execute(
                    "INSERT INTO maintenance_template_ops (template_id, code, machines_csv) VALUES (?, ?, ?)",
                    (template_id, code, mcsv),
                )
            conn.execute(
                "UPDATE maintenance_templates SET updated_at=? WHERE id=?",
                (now, template_id),
            )
            # Resync des créneaux futurs liés
            resynced = _resync_future_events_from_template(conn, template_id)
        conn.commit()
        tmpl = _load_template_full(conn, template_id)
    return {"template": tmpl, "resynced_events": resynced}


@router.delete("/api/maintenance/templates/{template_id}")
def delete_template(template_id: int, request: Request):
    """Supprime un template et, en cascade, les créneaux futurs qui en dépendent.
    (Les créneaux passés restent, avec template_id → NULL.)"""
    _require_admin(request)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM maintenance_templates WHERE id = ?", (template_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Modèle introuvable")
        today = datetime.now(_PARIS).strftime("%Y-%m-%d")
        # Cascade sur les créneaux futurs (>= aujourd'hui)
        future_ids = [r["id"] for r in conn.execute(
            "SELECT id FROM maintenance_events WHERE template_id = ? AND date_prevue >= ?",
            (template_id, today),
        ).fetchall()]
        for eid in future_ids:
            conn.execute("DELETE FROM maintenance_event_ops WHERE event_id = ?", (eid,))
            conn.execute("DELETE FROM maintenance_event_operators WHERE event_id = ?", (eid,))
            conn.execute("DELETE FROM maintenance_events WHERE id = ?", (eid,))
        # Détache les créneaux passés (template_id -> NULL, ils survivent)
        conn.execute(
            "UPDATE maintenance_events SET template_id = NULL WHERE template_id = ?",
            (template_id,),
        )
        # Supprime le template (ON DELETE CASCADE FK inactif, nettoyage manuel)
        conn.execute("DELETE FROM maintenance_template_ops WHERE template_id = ?", (template_id,))
        conn.execute("DELETE FROM maintenance_templates WHERE id = ?", (template_id,))
        conn.commit()
    return {"deleted": template_id, "deleted_future_events": len(future_ids)}
