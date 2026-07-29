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
- Opérateur (fabrication) : peut :
  - Lire les events où il est dans le groupe (endpoint `/my-tasks`).
  - Mettre à jour statut/saisie d'une op **si** il est dans le groupe.
  - Créer un event `source=non_planifie` avec lui-même comme seul opérateur.
"""
import hashlib
from datetime import datetime, date, timedelta
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
    ROLE_ADMINISTRATION_VENTES,
    ROLE_ADMINISTRATION_TECHNIQUE,
    ROLE_FABRICATION,
)


router = APIRouter(tags=["maintenance-events"])


# ─── Constantes / helpers ─────────────────────────────────────────

_ADMIN_ROLES = {ROLE_SUPERADMIN, ROLE_DIRECTION, ROLE_ADMINISTRATION,
                ROLE_ADMINISTRATION_VENTES, ROLE_ADMINISTRATION_TECHNIQUE}
_PARIS = ZoneInfo("Europe/Paris")

_VALID_STATUTS = {"a_faire", "en_cours", "termine", "reporte", "invalidee"}
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


def _bump_libre_usage(conn, code: str) -> None:
    """v2.2.37 : incrémente maintenance_codes.usage_count si le code est un libre (LIB-*).
    Safe : ignore silencieusement les codes standards et les erreurs.
    """
    if not code or not code.startswith("LIB-"):
        return
    try:
        conn.execute(
            "UPDATE maintenance_codes SET usage_count = COALESCE(usage_count, 0) + 1 "
            "WHERE code = ? AND libre = 1",
            (code,),
        )
    except Exception:
        pass


def _get_maintenance_role(user: dict) -> Optional[str]:
    if not user:
        return None
    role = effective_role(user)
    if role in _ADMIN_ROLES:
        return "admin"
    if role == ROLE_FABRICATION:
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
    """Un opérateur peut modifier/supprimer un event qu'il a créé, mais
    uniquement de source non_planifie (interventions déclarées via les
    boutons "Enregistrer une opération" ou "Intervention libre").
    Les créneaux planifie sont réservés à l'admin.
    Sert de garde pour les endpoints PATCH/DELETE/ops côté opérateur."""
    if not event:
        return False
    if event.get("source") != "non_planifie":
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
                  o.updated_by, o.updated_at, o.machines_csv, o.consignes,
                  o.invalidated_by, o.invalidated_at,
                  c.label     AS code_label,
                  c.categorie AS code_categorie,
                  ub.nom      AS done_by_nom,
                  ui.nom      AS invalidated_by_nom
           FROM maintenance_event_ops o
           LEFT JOIN maintenance_codes c ON c.code = o.code
           LEFT JOIN users ub ON ub.id = o.done_by
           LEFT JOIN users ui ON ui.id = o.invalidated_by
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
    # v185 : consignes admin optionnelles à la création d'une op
    consignes: Optional[str] = None


class OpUpdateBody(BaseModel):
    statut: Optional[str] = None
    duree_reelle_min: Optional[int] = None
    pieces_changees: Optional[str] = None
    observations: Optional[str] = None
    photos_json: Optional[str] = None
    machines: Optional[List[str]] = None
    # v185 : consignes admin (empty string autorisée pour effacer)
    consignes: Optional[str] = None
    # v2.2.5 : override du done_at (l'admin peut ajuster la date de saisie
    # historique d'une op déjà terminée). Format ISO Paris (YYYY-MM-DDTHH:MM:SS
    # ou avec .SSSZ). Si fourni, écrase la valeur actuelle.
    done_at: Optional[str] = None


class OperatorAddBody(BaseModel):
    operator_id: int


# ─── Endpoints — codes & opérateurs (utilitaires pickers) ────────

@router.get("/api/maintenance/operators")
def list_operators(request: Request):
    """Liste des utilisateurs assignables : opérateurs fabrication + Manuel Lesaffre.
    v2.2.45 : ciblé sur Manuel Lesaffre uniquement (au lieu de tous les admins)
    puisqu'il est le seul admin à réaliser aussi la maintenance."""
    _require_access(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, nom, email, identifiant "
            "FROM users "
            "WHERE (role = ? OR LOWER(COALESCE(nom, '')) LIKE '%lesaffre%') "
            "  AND actif = 1 "
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
        # v2.4.28 : lazy trigger — genere les occurrences des templates recurrents
        # actifs jusqu'a today+90j. Idempotent, cout negligeable si a jour.
        _ensure_recurring_events_generated(conn, horizon_days=90)
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
        # L'opérateur ne peut créer QUE des interventions non_planifie (single
        # op, self forcé) via les boutons "Enregistrer une opération" ou
        # "Intervention libre". La création de créneaux planifiés est réservée
        # à l'admin. On force source=non_planifie côté serveur pour blinder
        # contre les requêtes forgées.
        src = "non_planifie"
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
        # v2.2.49 : opérateurs obligatoires pour un créneau planifié admin.
        # L'ancienne logique d'auto-assign 'tous fabrication' est retirée
        # (un créneau doit expliciter qui doit intervenir).
        if maint_role == "admin" and src == "planifie" and not operator_ids:
            raise HTTPException(
                status_code=400,
                detail="Sélectionne au moins un opérateur pour ce créneau."
            )
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
                    _bump_libre_usage(conn, code)  # v2.2.37
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
        # v2.5.14 : garde-fou 'past event' -- interdit toute modif de la date ou
        # des heures d'un créneau déjà passé (aujourd'hui inclus reste modifiable).
        # Les autres champs (ops, notes, ...) restent éditables librement.
        _today = datetime.now(_PARIS).strftime("%Y-%m-%d")
        _ev_date = ev.get("date_prevue") or ""
        _time_fields = {"date_prevue", "heure_debut", "heure_fin"}
        if _ev_date < _today and any(k in updates for k in _time_fields):
            raise HTTPException(
                status_code=403,
                detail="Ce créneau est passé. La date et les horaires ne sont plus modifiables (seules les ops peuvent être corrigées).",
            )
        updates["updated_at"] = _now_paris_iso()
        set_clause = ", ".join(f"{k}=?" for k in updates)
        conn.execute(f"UPDATE maintenance_events SET {set_clause} WHERE id=?",
                     list(updates.values()) + [event_id])
        conn.commit()
        ev = _load_event_full(conn, event_id)
    return {"event": ev}


@router.delete("/api/maintenance/events/{event_id}")
def delete_event(event_id: int, request: Request, confirm_token: Optional[str] = None):
    """Admin : suppression libre. Opérateur : uniquement ses propres non_planifie.

    v2.4.19 : garde-fou anti-destruction de traçabilité. Si le créneau contient
    des ops déjà 'termine', premier appel → HTTP 409 avec la liste des ops
    effectuées et un token déterministe `sha256(sorted(op_ids))[:16]`. Second
    appel avec `?confirm_token=<hash>` → suppression autorisée. Le token étant
    dérivé de l'état, il s'invalide automatiquement si une op change de statut
    entre les 2 appels (protection anti-race, aucun stockage serveur).

    Comportement inchangé si le créneau n'a aucune op 'termine' (suppression
    directe, comme avant v2.4.19).
    """
    user, maint_role = _require_access(request)
    with get_db() as conn:
        ev = _load_event_full(conn, event_id)
        if not ev:
            raise HTTPException(status_code=404, detail="Créneau introuvable")
        if maint_role == "operator":
            if not _can_operator_manage_event(ev, user["id"]):
                raise HTTPException(status_code=403, detail="Vous ne pouvez supprimer que vos propres interventions non planifiées")

        # v2.4.19 : lister les ops termine + métadonnées pour l'écran de
        # confirmation renforcée. Jointure sur maintenance_codes pour le
        # libellé lisible, et sur users pour le nom de l'opérateur qui a saisi.
        done_rows = conn.execute("""
            SELECT eo.id, eo.code, eo.done_at, eo.done_by, eo.machines_csv,
                   mc.label AS code_label,
                   u.nom AS done_by_name
            FROM maintenance_event_ops eo
            LEFT JOIN maintenance_codes mc ON mc.code = eo.code
            LEFT JOIN users u ON u.id = eo.done_by
            WHERE eo.event_id = ? AND eo.statut = 'termine'
            ORDER BY eo.done_at ASC, eo.id ASC
        """, (event_id,)).fetchall()

        if done_rows:
            op_ids_sorted = sorted(int(r["id"]) for r in done_rows)
            token_source = ",".join(str(i) for i in op_ids_sorted)
            expected_token = hashlib.sha256(token_source.encode("utf-8")).hexdigest()[:16]
            if confirm_token != expected_token:
                done_ops_payload = [{
                    "id": r["id"],
                    "code": r["code"],
                    "label": r["code_label"] or r["code"],
                    "done_at": r["done_at"],
                    "done_by_name": r["done_by_name"] or "opérateur inconnu",
                    "machines": _machines_csv_to_list(r["machines_csv"]),
                } for r in done_rows]
                raise HTTPException(status_code=409, detail={
                    "requires_confirmation": True,
                    "done_ops": done_ops_payload,
                    "confirm_token": expected_token,
                    "n_done": len(done_ops_payload),
                })

        # v2.2.11 : cleanup manuel — get_db() n'active pas PRAGMA foreign_keys,
        # donc le CASCADE des FK est INACTIF. Sans ces DELETE explicites, les
        # rows dans maintenance_event_ops et maintenance_event_operators
        # restent orphelines dans la DB (invisibles dans l'UI via JOIN mais
        # présentes physiquement).
        conn.execute("DELETE FROM maintenance_event_ops WHERE event_id=?", (event_id,))
        conn.execute("DELETE FROM maintenance_event_operators WHERE event_id=?", (event_id,))
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
            # v185 : consignes si fournies à la création
            conn.execute(
                "INSERT INTO maintenance_event_ops (event_id, code, machines_csv, consignes, updated_at) VALUES (?, ?, ?, ?, ?)",
                (event_id, body.code, single_csv, (body.consignes or None) if body.consignes else None, now),
            )
            _bump_libre_usage(conn, body.code)  # v2.2.37
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
            # v185 : consignes accepte empty string (pour effacer les consignes)
            if v is None and k != "consignes": continue
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
        # v2.2.9 : si le client a fourni un done_at explicite (admin qui saisit
        # rétroactivement une op faite plus tôt), on le respecte au lieu de
        # l'écraser avec now. done_by reste toujours l'user qui valide.
        if updates.get("statut") == "termine" and not row["done_at"]:
            if "done_at" not in updates:
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

@router.post("/api/maintenance/events/{event_id}/ops/{op_id}/invalidate")
def invalidate_op(event_id: int, op_id: int, request: Request):
    """Admin : marque une saisie d'op comme invalidee.
    - Statut termine -> invalidee. Conserve done_at/done_by (traceabilite
      historique : la saisie a bien eu lieu, on la met de cote sans effacer
      qui l'a faite).
    - Ecrit invalidated_by + invalidated_at (traceabilite de l'invalidation).
    - La ligne dans get_history disparait automatiquement (filtre statut=termine).
    - Le creneau conserve la ligne, affichee en grise avec badge Invalidee.
    - Perms : admin uniquement (contrairement a reset_op)."""
    user = _require_admin(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT event_id, statut FROM maintenance_event_ops WHERE id=?",
            (op_id,),
        ).fetchone()
        if not row or row["event_id"] != event_id:
            raise HTTPException(status_code=404, detail="Op introuvable dans ce creneau")
        if row["statut"] != "termine":
            raise HTTPException(status_code=400, detail="Seule une saisie terminee peut etre invalidee")
        now = _now_paris_iso()
        conn.execute(
            """UPDATE maintenance_event_ops
               SET statut='invalidee',
                   invalidated_by=?,
                   invalidated_at=?
               WHERE id=?""",
            (user["id"], now, op_id),
        )
        conn.commit()
        ev = _load_event_full(conn, event_id)
    return {"event": ev}


@router.post("/api/maintenance/events/{event_id}/ops/{op_id}/revalidate")
def revalidate_op(event_id: int, op_id: int, request: Request):
    """Admin : reactive une saisie invalidee (invalidee -> termine).
    Sortie de sortie de secours si on invalide par erreur. Efface
    invalidated_by/at. Perms : admin uniquement."""
    user = _require_admin(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT event_id, statut FROM maintenance_event_ops WHERE id=?",
            (op_id,),
        ).fetchone()
        if not row or row["event_id"] != event_id:
            raise HTTPException(status_code=404, detail="Op introuvable dans ce creneau")
        if row["statut"] != "invalidee":
            raise HTTPException(status_code=400, detail="Seule une saisie invalidee peut etre revalidee")
        now = _now_paris_iso()
        conn.execute(
            """UPDATE maintenance_event_ops
               SET statut='termine',
                   invalidated_by=NULL,
                   invalidated_at=NULL,
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
    # v2.4.28 : recurrence
    recurrence_type: Optional[str] = None       # 'weekly' | 'monthly' | 'quarterly' | 'yearly' | None
    recurrence_dow: Optional[int] = None        # 0-6 (0=lundi)
    recurrence_dom: Optional[int] = None        # 1-31
    recurrence_month: Optional[int] = None      # 1-12 (yearly)
    recurrence_time_start: Optional[str] = None # 'HH:MM'
    recurrence_time_end: Optional[str] = None
    recurrence_active: Optional[bool] = False


class TemplateUpdateBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    ops: Optional[List[TemplateOpSpec]] = None
    recurrence_type: Optional[str] = None
    recurrence_dow: Optional[int] = None
    recurrence_dom: Optional[int] = None
    recurrence_month: Optional[int] = None
    recurrence_time_start: Optional[str] = None
    recurrence_time_end: Optional[str] = None
    recurrence_active: Optional[bool] = None


class SaveAsTemplateBody(BaseModel):
    name: str
    description: Optional[str] = None



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
                       e.heure_debut    AS event_heure_debut,
                       e.heure_fin      AS event_heure_fin,
                       o.consignes      AS consignes,
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
                       o.updated_at     AS updated_at,
                       o.updated_by     AS updated_by,
                       uu.nom           AS updated_by_nom,
                       e.date_prevue    AS date_prevue,
                       e.created_by     AS created_by,
                       uc.nom           AS created_by_nom,
                       e.created_at     AS event_created_at,
                       e.source         AS source
                FROM maintenance_event_ops o
                JOIN maintenance_events e ON e.id = o.event_id
                LEFT JOIN maintenance_codes c ON c.code = o.code
                LEFT JOIN users ub ON ub.id = o.done_by
                LEFT JOIN users uc ON uc.id = e.created_by
                LEFT JOIN users uu ON uu.id = o.updated_by
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
        # Flag libre : détection LIB-xxx (compat avec _libre côté client)
        d["libre"] = bool(d.get("code") and str(d["code"]).startswith("LIB-"))
        out.append(d)
    return {"history": out}


def _load_template_full(conn, template_id: int) -> Optional[dict]:
    # v2.4.28 : SELECT * pour recuperer aussi les colonnes recurrence
    row = conn.execute(
        "SELECT * FROM maintenance_templates WHERE id = ?",
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
    d = dict(row)
    d["ops"] = ops_out
    # Assure la presence des champs recurrence meme si l'ancien schema n'a pas encore les colonnes
    for f in ("recurrence_type","recurrence_dow","recurrence_dom","recurrence_month",
              "recurrence_time_start","recurrence_time_end"):
        d.setdefault(f, None)
    d["recurrence_active"] = bool(d.get("recurrence_active"))
    return d


# ── v2.4.28 — Helpers de recurrence ─────────────────────────────────
# Convention interne : recurrence_dow 0=lundi..6=dimanche (ISO/Python weekday).
# Les cas edge (day-of-month inexistant type 31 fevrier) sont skip silencieusement.

def _add_months(year: int, month: int, delta: int):
    total = (year * 12 + month - 1) + delta
    return total // 12, (total % 12) + 1


def _compute_next_occurrence(tmpl: dict, from_date=None):
    """Retourne la date de la prochaine occurrence >= from_date (ou date.today())
    pour un template donne. None si pas recurrent ou parametres invalides."""
    if not tmpl.get("recurrence_type") or not tmpl.get("recurrence_active"):
        return None
    rtype = tmpl["recurrence_type"]
    today = from_date or date.today()

    if rtype == "weekly":
        dow = tmpl.get("recurrence_dow")
        if dow is None or not (0 <= dow <= 6):
            return None
        # Python weekday(): 0=lundi..6=dimanche → match notre convention
        days_ahead = (dow - today.weekday()) % 7
        return today + timedelta(days=days_ahead)

    dom = tmpl.get("recurrence_dom")
    if dom is None or not (1 <= dom <= 31):
        return None

    if rtype == "monthly":
        valid_months = tuple(range(1, 13))
    elif rtype == "quarterly":
        # Cycle Jan / Avr / Jul / Oct (mois 1, 4, 7, 10)
        valid_months = (1, 4, 7, 10)
    elif rtype == "yearly":
        month = tmpl.get("recurrence_month")
        if month is None or not (1 <= month <= 12):
            return None
        valid_months = (month,)
    else:
        return None

    # Cherche la prochaine date dom @ mois valide, dans les 24 prochains mois max
    for offset in range(24):
        y, m = _add_months(today.year, today.month, offset)
        if m not in valid_months:
            continue
        try:
            candidate = date(y, m, dom)
        except ValueError:
            continue  # jour inexistant dans ce mois (ex. 31 fevrier)
        if candidate >= today:
            return candidate
    return None


def _generate_events_for_template(conn, template_id: int, until_date) -> int:
    """Genere toutes les occurrences futures (aujourd'hui..until_date incluse)
    pour un template recurrent. Idempotent : skip si event existe deja pour
    (template_id, date_prevue). Retourne le nombre d'events crees."""
    tmpl = _load_template_full(conn, template_id)
    if not tmpl or not tmpl.get("recurrence_active") or not tmpl.get("recurrence_type"):
        return 0

    now_iso = datetime.now().isoformat(timespec="seconds")
    heure_debut = tmpl.get("recurrence_time_start") or ""
    heure_fin = tmpl.get("recurrence_time_end") or ""

    # CSV machines = union de toutes les machines des ops du template
    all_machines = []
    for op in tmpl["ops"]:
        for m in op.get("machines") or []:
            if m not in all_machines:
                all_machines.append(m)
    machine_csv = " · ".join(all_machines) if all_machines else ""

    count = 0
    cursor = date.today()
    # Safety : 500 iterations max (largement suffisant pour 3 mois meme en hebdo)
    for _ in range(500):
        nxt = _compute_next_occurrence(tmpl, cursor)
        if nxt is None or nxt > until_date:
            break
        # v2.5.15 : dedup sur template_origin_date (immuable) au lieu de
        # date_prevue (mutable via drag&drop). Evite la re-generation d'une
        # occurrence quand le creneau original a ete deplace ailleurs.
        exists = conn.execute(
            "SELECT 1 FROM maintenance_events WHERE template_id=? AND template_origin_date=? LIMIT 1",
            (template_id, nxt.isoformat())
        ).fetchone()
        if not exists:
            cur = conn.execute(
                "INSERT INTO maintenance_events "
                "(machine, date_prevue, heure_debut, heure_fin, source, created_at, template_id, template_origin_date) "
                "VALUES (?, ?, ?, ?, 'planifie', ?, ?, ?)",
                (machine_csv, nxt.isoformat(), heure_debut, heure_fin, now_iso, template_id, nxt.isoformat())
            )
            event_id = cur.lastrowid
            for op in tmpl["ops"]:
                op_machines_csv = (" · ".join(op["machines"]) if op.get("machines")
                                   else machine_csv)
                conn.execute(
                    "INSERT OR IGNORE INTO maintenance_event_ops "
                    "(event_id, code, machines_csv, updated_at) VALUES (?, ?, ?, ?)",
                    (event_id, op["code"], op_machines_csv, now_iso)
                )
            count += 1
        cursor = nxt + timedelta(days=1)
    if count:
        conn.commit()
    return count


def _ensure_recurring_events_generated(conn, horizon_days: int = 90) -> int:
    """Pour chaque template recurrent actif, genere les occurrences futures
    dans une fenetre glissante de horizon_days (defaut 90 = 3 mois).
    Idempotent. Appele en lazy trigger au load des events."""
    until = date.today() + timedelta(days=horizon_days)
    total = 0
    tmpl_ids = [r["id"] for r in conn.execute(
        "SELECT id FROM maintenance_templates WHERE recurrence_active=1 AND recurrence_type IS NOT NULL"
    ).fetchall()]
    for tid in tmpl_ids:
        try:
            total += _generate_events_for_template(conn, tid, until)
        except Exception:
            pass  # ne pas bloquer le chargement de la page si un template foire
    return total


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
            _bump_libre_usage(conn, op["code"])  # v2.2.37
        _recompute_event_machine(conn, eid)
    return len(events)


@router.get("/api/maintenance/templates")
def list_templates(request: Request):
    """Liste tous les templates avec metadonnees enrichies (v2.4.28) :
    nb d'ops, recurrence, prochaine occurrence prevue, stats d'utilisation
    (nb d'events crees, derniere date d'utilisation).
    Admin only."""
    _require_admin(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT t.id, t.name, t.description, t.created_at, t.updated_at,
                      t.recurrence_type, t.recurrence_dow, t.recurrence_dom,
                      t.recurrence_month, t.recurrence_time_start, t.recurrence_time_end,
                      t.recurrence_active,
                      (SELECT COUNT(*) FROM maintenance_template_ops o WHERE o.template_id=t.id) AS ops_count,
                      (SELECT COUNT(*) FROM maintenance_events e WHERE e.template_id=t.id) AS events_count,
                      (SELECT MAX(date_prevue) FROM maintenance_events e WHERE e.template_id=t.id) AS last_event_date
               FROM maintenance_templates t
               ORDER BY t.name""",
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["recurrence_active"] = bool(d.get("recurrence_active"))
            nxt = _compute_next_occurrence(d)
            d["next_occurrence"] = nxt.isoformat() if nxt else None
            out.append(d)
    return {"templates": out}


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
            """INSERT INTO maintenance_templates
                (name, description, created_by, created_at,
                 recurrence_type, recurrence_dow, recurrence_dom, recurrence_month,
                 recurrence_time_start, recurrence_time_end, recurrence_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, body.description, user["id"], now,
             (body.recurrence_type or None),
             body.recurrence_dow,
             body.recurrence_dom,
             body.recurrence_month,
             (body.recurrence_time_start or None),
             (body.recurrence_time_end or None),
             1 if body.recurrence_active else 0),
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
        # v2.4.28 : champs recurrence
        if body.recurrence_type is not None:
            meta_updates["recurrence_type"] = body.recurrence_type or None
        if body.recurrence_dow is not None:
            meta_updates["recurrence_dow"] = body.recurrence_dow
        if body.recurrence_dom is not None:
            meta_updates["recurrence_dom"] = body.recurrence_dom
        if body.recurrence_month is not None:
            meta_updates["recurrence_month"] = body.recurrence_month
        if body.recurrence_time_start is not None:
            meta_updates["recurrence_time_start"] = body.recurrence_time_start or None
        if body.recurrence_time_end is not None:
            meta_updates["recurrence_time_end"] = body.recurrence_time_end or None
        # v2.5.13 : si la recurrence est desactivee, purge les creneaux FUTURS
        # generes depuis ce template (les passes restent, comme dans delete_template).
        deleted_future = 0
        if body.recurrence_active is not None:
            meta_updates["recurrence_active"] = 1 if body.recurrence_active else 0
            if not body.recurrence_active:
                today = datetime.now(_PARIS).strftime("%Y-%m-%d")
                future_ids = [r["id"] for r in conn.execute(
                    "SELECT id FROM maintenance_events WHERE template_id = ? AND date_prevue >= ?",
                    (template_id, today),
                ).fetchall()]
                for eid in future_ids:
                    conn.execute("DELETE FROM maintenance_event_ops WHERE event_id = ?", (eid,))
                    conn.execute("DELETE FROM maintenance_event_operators WHERE event_id = ?", (eid,))
                    conn.execute("DELETE FROM maintenance_events WHERE id = ?", (eid,))
                deleted_future = len(future_ids)
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
    return {"template": tmpl, "resynced_events": resynced, "deleted_future_events": deleted_future}


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


# ── v2.4.28 — Nouveaux endpoints : generate-now + save-as-template ──

@router.post("/api/maintenance/templates/{template_id}/generate-now")
def template_generate_now(template_id: int, request: Request):
    """Force la generation immediate des occurrences futures d'un template
    recurrent, dans la fenetre glissante par defaut (90 jours).
    Admin only. Retourne le nombre d'events crees."""
    _require_admin(request)
    with get_db() as conn:
        tmpl = _load_template_full(conn, template_id)
        if not tmpl:
            raise HTTPException(status_code=404, detail="Modèle introuvable")
        if not tmpl.get("recurrence_active") or not tmpl.get("recurrence_type"):
            raise HTTPException(status_code=400,
                                detail="Ce modèle n'a pas de récurrence active.")
        until = date.today() + timedelta(days=90)
        n = _generate_events_for_template(conn, template_id, until)
    return {"created": n}


@router.post("/api/maintenance/events/{event_id}/save-as-template")
def save_event_as_template(event_id: int, body: SaveAsTemplateBody, request: Request):
    """Sauvegarde les operations d'un creneau existant sous forme de nouveau
    template (sans recurrence — a activer dans la modale template si besoin).
    Admin only."""
    user = _require_admin(request)
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nom du modèle requis")
    now = _now_paris_iso()
    with get_db() as conn:
        event = _load_event_full(conn, event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Créneau introuvable")
        if not event.get("ops"):
            raise HTTPException(status_code=400, detail="Ce créneau n'a aucune opération à sauvegarder.")
        if conn.execute("SELECT 1 FROM maintenance_templates WHERE name = ?", (name,)).fetchone():
            raise HTTPException(status_code=409, detail=f"Un modèle nommé « {name} » existe déjà.")
        user_id = user.get("id") if isinstance(user, dict) else None
        cur = conn.execute(
            "INSERT INTO maintenance_templates (name, description, created_by, created_at, recurrence_active) "
            "VALUES (?, ?, ?, ?, 0)",
            (name, (body.description or None), user_id, now),
        )
        template_id = cur.lastrowid
        # Copie des ops (dedup par code, union des machines)
        seen = {}
        for op in event["ops"]:
            code = op.get("code")
            if not code:
                continue
            machines = op.get("machines") or []
            if code in seen:
                for m in machines:
                    if m not in seen[code]:
                        seen[code].append(m)
            else:
                seen[code] = list(machines)
        for code, machines in seen.items():
            conn.execute(
                "INSERT INTO maintenance_template_ops (template_id, code, machines_csv) VALUES (?, ?, ?)",
                (template_id, code, " · ".join(machines) if machines else None),
            )
        conn.commit()
    return {"template_id": template_id, "name": name}
