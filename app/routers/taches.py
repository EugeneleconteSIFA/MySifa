"""MySifa — Gestionnaire de tâches (API).

Suivi interne des demandes faites à l'équipe de développement : tâches,
statuts, priorités, assignation, échéances, sous-tâches, checklist, fichiers
de contexte, commentaires et journal d'activité.

Accès : super administrateur uniquement (rôle effectif — un superadmin qui
simule un autre rôle perd l'accès, cohérent avec la tuile du portail).

Les référentiels (statuts, priorités, types, modules) vivent dans `config.py`
et sont exposés par `GET /api/taches/meta` — aucune valeur en dur côté front.
"""

from __future__ import annotations

import mimetypes
import os
import re
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import (
    BASE_DIR,
    GED_BLOCKED_EXTENSIONS,
    TACHES_MAX_FILE_MB,
    TACHES_PRIORITES_CODES,
    TACHES_STATUTS_CODES,
    TACHES_STATUTS_FINAUX,
    TACHES_TYPES_CODES,
    taches_modules,
    taches_priorites,
    taches_statuts,
    taches_types,
)
from database import get_db
from services.auth_service import get_current_user, is_superadmin

router = APIRouter(tags=["taches"])

TACHES_ROOT = Path(BASE_DIR) / "data" / "uploads" / "taches"
TACHES_ROOT.mkdir(parents=True, exist_ok=True)

MAX_FILE_BYTES = TACHES_MAX_FILE_MB * 1024 * 1024

# Ordre d'insertion en tête de colonne : on décrémente sous le minimum courant.
_ORDRE_STEP = 100.0

# Statuts clôturants, figés au chargement du module pour interpoler des `IN (?)`
# sans risque de liste vide (SQLite refuse `IN ()`).
_FINAUX = tuple(sorted(TACHES_STATUTS_FINAUX)) or ("__aucun__",)
_FINAUX_PH = ",".join("?" * len(_FINAUX))


# ─── Accès ────────────────────────────────────────────────────────────────

def _require_taches(request: Request) -> dict:
    """Super administrateur (rôle effectif) uniquement."""
    user = get_current_user(request)
    if not is_superadmin(user):
        raise HTTPException(status_code=403, detail="Accès réservé au super administrateur")
    return user


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _nom(user: dict) -> str:
    return str(user.get("nom") or user.get("email") or "")[:120]


def _sanitize_filename(name: str) -> str:
    base = os.path.basename(name or "")
    base = re.sub(r"[^A-Za-z0-9._\- ]", "_", base).strip()
    return base[:160] or "fichier"


def _check_extension(filename: str) -> None:
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if ext in GED_BLOCKED_EXTENSIONS:
        raise HTTPException(400, f"Extension .{ext} refusée (exécutable ou script)")


def _log(conn, tache_id: int, user: dict, action: str,
         champ: Optional[str] = None, avant: Any = None, apres: Any = None) -> None:
    """Journal d'activité. Jamais bloquant : une trace ratée ne casse pas l'action."""
    try:
        conn.execute(
            """INSERT INTO taches_activite
               (tache_id,user_id,auteur_nom,action,champ,avant,apres,created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                tache_id, user.get("id"), _nom(user), action, champ,
                None if avant is None else str(avant)[:400],
                None if apres is None else str(apres)[:400],
                _now(),
            ),
        )
    except Exception:
        pass


def _valid_date(value: Optional[str], champ: str) -> Optional[str]:
    if value is None:
        return None
    v = str(value).strip()[:10]
    if not v:
        return None
    try:
        date.fromisoformat(v)
    except ValueError:
        raise HTTPException(400, f"{champ} invalide — format attendu AAAA-MM-JJ.")
    return v


def _valid_heures(value: Any, champ: str) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        h = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        raise HTTPException(400, f"{champ} invalide — nombre d'heures attendu.")
    if h < 0 or h > 9999:
        raise HTTPException(400, f"{champ} invalide — valeur entre 0 et 9999 h.")
    return round(h, 2)


def _next_ordre(conn, statut: str) -> float:
    row = conn.execute(
        "SELECT MIN(ordre) AS m FROM taches WHERE statut=? AND deleted_at IS NULL",
        (statut,),
    ).fetchone()
    mini = row["m"] if row and row["m"] is not None else 0.0
    return float(mini) - _ORDRE_STEP


def _module_codes() -> set:
    return {m["code"] for m in taches_modules()}


# ─── Schémas ──────────────────────────────────────────────────────────────

class TacheIn(BaseModel):
    titre: str
    description: Optional[str] = None
    statut: Optional[str] = None
    priorite: Optional[str] = None
    type: Optional[str] = None
    module: Optional[str] = None
    assigne_user_id: Optional[int] = None
    parent_id: Optional[int] = None
    echeance: Optional[str] = None
    estimation_h: Optional[float] = None


class TachePatch(BaseModel):
    titre: Optional[str] = None
    description: Optional[str] = None
    statut: Optional[str] = None
    priorite: Optional[str] = None
    type: Optional[str] = None
    module: Optional[str] = None
    assigne_user_id: Optional[int] = None
    echeance: Optional[str] = None
    estimation_h: Optional[float] = None
    temps_passe_h: Optional[float] = None


class MoveIn(BaseModel):
    statut: str
    avant_id: Optional[int] = None   # tâche devant laquelle se placer
    apres_id: Optional[int] = None   # tâche derrière laquelle se placer


class CommentaireIn(BaseModel):
    message: str


class ChecklistIn(BaseModel):
    libelle: str


class ChecklistPatch(BaseModel):
    libelle: Optional[str] = None
    fait: Optional[bool] = None


class TempsIn(BaseModel):
    heures: float
    note: Optional[str] = None


# ─── Référentiels ─────────────────────────────────────────────────────────

@router.get("/api/taches/meta")
def taches_meta(request: Request):
    """Référentiels + liste des personnes assignables. Aucune valeur en dur au front."""
    _require_taches(request)
    with get_db() as conn:
        users = conn.execute(
            """SELECT id, nom, role, avatar_url
               FROM users WHERE actif=1 ORDER BY nom COLLATE NOCASE"""
        ).fetchall()
    return {
        "statuts": taches_statuts(),
        "priorites": taches_priorites(),
        "types": taches_types(),
        "modules": taches_modules(),
        "users": [dict(u) for u in users],
        "max_file_mb": TACHES_MAX_FILE_MB,
    }


# ─── Liste ────────────────────────────────────────────────────────────────

@router.get("/api/taches")
def list_taches(
    request: Request,
    statut: Optional[str] = None,
    assigne: Optional[int] = None,
    priorite: Optional[str] = None,
    type: Optional[str] = None,
    module: Optional[str] = None,
    q: Optional[str] = None,
    archivees: int = 0,
    racines: int = 0,
):
    """Liste des tâches, avec compteurs agrégés pour l'affichage carte/ligne."""
    _require_taches(request)
    where = ["t.deleted_at IS NULL"]
    params: list = []
    if not archivees:
        where.append("t.archived_at IS NULL")
    if statut and statut in TACHES_STATUTS_CODES:
        where.append("t.statut=?")
        params.append(statut)
    if assigne:
        where.append("t.assigne_user_id=?")
        params.append(int(assigne))
    if priorite and priorite in TACHES_PRIORITES_CODES:
        where.append("t.priorite=?")
        params.append(priorite)
    if type and type in TACHES_TYPES_CODES:
        where.append("t.type=?")
        params.append(type)
    if module:
        where.append("t.module=?")
        params.append(module)
    if racines:
        where.append("t.parent_id IS NULL")
    if q:
        terme = f"%{q.strip()}%"
        where.append("(t.titre LIKE ? OR t.description LIKE ?)")
        params.extend([terme, terme])

    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT t.*,
                       u.nom AS assigne_nom, u.avatar_url AS assigne_avatar,
                       p.titre AS parent_titre,
                       (SELECT COUNT(*) FROM taches_commentaires c
                          WHERE c.tache_id=t.id AND c.deleted_at IS NULL) AS nb_commentaires,
                       (SELECT COUNT(*) FROM taches_fichiers f
                          WHERE f.tache_id=t.id AND f.deleted_at IS NULL) AS nb_fichiers,
                       (SELECT COUNT(*) FROM taches_checklist k WHERE k.tache_id=t.id) AS nb_checklist,
                       (SELECT COUNT(*) FROM taches_checklist k
                          WHERE k.tache_id=t.id AND k.fait=1) AS nb_checklist_faits,
                       (SELECT COUNT(*) FROM taches s
                          WHERE s.parent_id=t.id AND s.deleted_at IS NULL) AS nb_sous_taches,
                       (SELECT COUNT(*) FROM taches s
                          WHERE s.parent_id=t.id AND s.deleted_at IS NULL
                            AND s.statut IN ({_FINAUX_PH})
                       ) AS nb_sous_taches_faites
                  FROM taches t
                  LEFT JOIN users u ON u.id = t.assigne_user_id
                  LEFT JOIN taches p ON p.id = t.parent_id
                 WHERE {' AND '.join(where)}
                 ORDER BY t.ordre ASC, t.id DESC""",
            list(_FINAUX) + params,
        ).fetchall()
    return {"taches": [dict(r) for r in rows]}


@router.get("/api/taches/stats")
def taches_stats(request: Request):
    """Compteurs d'en-tête : par statut, en retard, non assignées."""
    _require_taches(request)
    today = date.today().isoformat()
    with get_db() as conn:
        par_statut = conn.execute(
            """SELECT statut, COUNT(*) AS n FROM taches
               WHERE deleted_at IS NULL AND archived_at IS NULL
               GROUP BY statut"""
        ).fetchall()
        retard = conn.execute(
            f"""SELECT COUNT(*) AS n FROM taches
                WHERE deleted_at IS NULL AND archived_at IS NULL
                  AND echeance IS NOT NULL AND echeance < ?
                  AND statut NOT IN ({_FINAUX_PH})""",
            [today] + list(_FINAUX),
        ).fetchone()
        non_assignees = conn.execute(
            """SELECT COUNT(*) AS n FROM taches
               WHERE deleted_at IS NULL AND archived_at IS NULL AND assigne_user_id IS NULL"""
        ).fetchone()
    return {
        "par_statut": {r["statut"]: r["n"] for r in par_statut},
        "en_retard": retard["n"] if retard else 0,
        "non_assignees": non_assignees["n"] if non_assignees else 0,
    }


# ─── Détail ───────────────────────────────────────────────────────────────

def _fetch_tache(conn, tache_id: int) -> dict:
    row = conn.execute(
        """SELECT t.*, u.nom AS assigne_nom, u.avatar_url AS assigne_avatar,
                  p.titre AS parent_titre
             FROM taches t
             LEFT JOIN users u ON u.id = t.assigne_user_id
             LEFT JOIN taches p ON p.id = t.parent_id
            WHERE t.id=? AND t.deleted_at IS NULL""",
        (tache_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Tâche introuvable")
    return dict(row)


@router.get("/api/taches/{tache_id}")
def get_tache(tache_id: int, request: Request):
    _require_taches(request)
    with get_db() as conn:
        tache = _fetch_tache(conn, tache_id)
        commentaires = conn.execute(
            """SELECT c.*, u.avatar_url AS auteur_avatar
                 FROM taches_commentaires c
                 LEFT JOIN users u ON u.id = c.user_id
                WHERE c.tache_id=? AND c.deleted_at IS NULL
                ORDER BY c.created_at ASC, c.id ASC""",
            (tache_id,),
        ).fetchall()
        fichiers = conn.execute(
            """SELECT id,nom,taille_bytes,mime,uploaded_nom,created_at
                 FROM taches_fichiers
                WHERE tache_id=? AND deleted_at IS NULL
                ORDER BY created_at DESC, id DESC""",
            (tache_id,),
        ).fetchall()
        checklist = conn.execute(
            """SELECT id,libelle,fait,ordre,fait_at,fait_par_nom
                 FROM taches_checklist WHERE tache_id=?
                ORDER BY ordre ASC, id ASC""",
            (tache_id,),
        ).fetchall()
        activite = conn.execute(
            """SELECT id,auteur_nom,action,champ,avant,apres,created_at
                 FROM taches_activite WHERE tache_id=?
                ORDER BY created_at DESC, id DESC LIMIT 120""",
            (tache_id,),
        ).fetchall()
        sous_taches = conn.execute(
            """SELECT t.id,t.titre,t.statut,t.priorite,t.echeance,
                      u.nom AS assigne_nom
                 FROM taches t LEFT JOIN users u ON u.id=t.assigne_user_id
                WHERE t.parent_id=? AND t.deleted_at IS NULL
                ORDER BY t.ordre ASC, t.id ASC""",
            (tache_id,),
        ).fetchall()
    return {
        "tache": tache,
        "commentaires": [dict(r) for r in commentaires],
        "fichiers": [dict(r) for r in fichiers],
        "checklist": [dict(r) for r in checklist],
        "activite": [dict(r) for r in activite],
        "sous_taches": [dict(r) for r in sous_taches],
    }


# ─── Création / modification ──────────────────────────────────────────────

@router.post("/api/taches")
def create_tache(payload: TacheIn, request: Request):
    user = _require_taches(request)
    titre = (payload.titre or "").strip()
    if not titre:
        raise HTTPException(400, "Titre obligatoire.")
    statut = payload.statut or "backlog"
    if statut not in TACHES_STATUTS_CODES:
        raise HTTPException(400, "Statut inconnu.")
    priorite = payload.priorite or "normale"
    if priorite not in TACHES_PRIORITES_CODES:
        raise HTTPException(400, "Priorité inconnue.")
    ttype = payload.type or "evolution"
    if ttype not in TACHES_TYPES_CODES:
        raise HTTPException(400, "Type inconnu.")
    module = (payload.module or "").strip() or None
    if module and module not in _module_codes():
        raise HTTPException(400, "Module inconnu.")
    echeance = _valid_date(payload.echeance, "Échéance")
    estimation = _valid_heures(payload.estimation_h, "Estimation")
    now = _now()

    with get_db() as conn:
        if payload.parent_id:
            parent = conn.execute(
                "SELECT id,parent_id FROM taches WHERE id=? AND deleted_at IS NULL",
                (int(payload.parent_id),),
            ).fetchone()
            if not parent:
                raise HTTPException(400, "Tâche parente introuvable.")
            if parent["parent_id"]:
                raise HTTPException(400, "Une sous-tâche ne peut pas avoir de sous-tâches.")
        if payload.assigne_user_id:
            if not conn.execute(
                "SELECT 1 FROM users WHERE id=? AND actif=1", (int(payload.assigne_user_id),)
            ).fetchone():
                raise HTTPException(400, "Utilisateur assigné introuvable.")
        cur = conn.execute(
            """INSERT INTO taches
               (titre,description,statut,priorite,type,module,assigne_user_id,
                createur_user_id,createur_nom,parent_id,echeance,estimation_h,
                temps_passe_h,ordre,created_at,updated_at,started_at,done_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0,?,?,?,?,?)""",
            (
                titre[:300], (payload.description or "").strip() or None,
                statut, priorite, ttype, module,
                payload.assigne_user_id, user.get("id"), _nom(user),
                payload.parent_id, echeance, estimation,
                _next_ordre(conn, statut), now, now,
                now if statut == "en_cours" else None,
                now if statut in TACHES_STATUTS_FINAUX else None,
            ),
        )
        tache_id = cur.lastrowid
        _log(conn, tache_id, user, "creation")
        conn.commit()
    return {"success": True, "id": tache_id}


_PATCH_LABELS = {
    "titre": "Titre", "description": "Description", "statut": "Statut",
    "priorite": "Priorité", "type": "Type", "module": "Module",
    "assigne_user_id": "Assigné", "echeance": "Échéance",
    "estimation_h": "Estimation", "temps_passe_h": "Temps passé",
}


@router.put("/api/taches/{tache_id}")
def update_tache(tache_id: int, payload: TachePatch, request: Request):
    """Mise à jour partielle : seuls les champs fournis sont écrits."""
    user = _require_taches(request)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return {"success": True, "modifie": 0}

    if "statut" in data and data["statut"] not in TACHES_STATUTS_CODES:
        raise HTTPException(400, "Statut inconnu.")
    if "priorite" in data and data["priorite"] not in TACHES_PRIORITES_CODES:
        raise HTTPException(400, "Priorité inconnue.")
    if "type" in data and data["type"] not in TACHES_TYPES_CODES:
        raise HTTPException(400, "Type inconnu.")
    if "module" in data:
        data["module"] = (data["module"] or "").strip() or None
        if data["module"] and data["module"] not in _module_codes():
            raise HTTPException(400, "Module inconnu.")
    if "echeance" in data:
        data["echeance"] = _valid_date(data["echeance"], "Échéance")
    if "estimation_h" in data:
        data["estimation_h"] = _valid_heures(data["estimation_h"], "Estimation")
    if "temps_passe_h" in data:
        data["temps_passe_h"] = _valid_heures(data["temps_passe_h"], "Temps passé") or 0
    if "titre" in data:
        data["titre"] = (data["titre"] or "").strip()[:300]
        if not data["titre"]:
            raise HTTPException(400, "Titre obligatoire.")
    if "description" in data:
        data["description"] = (data["description"] or "").strip() or None

    now = _now()
    with get_db() as conn:
        avant = _fetch_tache(conn, tache_id)
        if data.get("assigne_user_id"):
            if not conn.execute(
                "SELECT 1 FROM users WHERE id=? AND actif=1", (int(data["assigne_user_id"]),)
            ).fetchone():
                raise HTTPException(400, "Utilisateur assigné introuvable.")

        sets, params = [], []
        for champ, valeur in data.items():
            sets.append(f"{champ}=?")
            params.append(valeur)

        # Horodatages dérivés du statut — jamais écrasés une fois posés.
        if "statut" in data:
            nouveau = data["statut"]
            if nouveau == "en_cours" and not avant.get("started_at"):
                sets.append("started_at=?")
                params.append(now)
            if nouveau in TACHES_STATUTS_FINAUX:
                sets.append("done_at=?")
                params.append(now)
            elif avant.get("done_at"):
                sets.append("done_at=NULL")

        sets.append("updated_at=?")
        params.append(now)
        params.append(tache_id)
        conn.execute(f"UPDATE taches SET {', '.join(sets)} WHERE id=?", params)

        for champ, valeur in data.items():
            if str(avant.get(champ) or "") == str(valeur or ""):
                continue
            _log(conn, tache_id, user, "modification", _PATCH_LABELS.get(champ, champ),
                 avant.get(champ), valeur)
        conn.commit()
    return {"success": True}


@router.post("/api/taches/{tache_id}/move")
def move_tache(tache_id: int, payload: MoveIn, request: Request):
    """Déplacement kanban : change le statut et/ou la position dans la colonne."""
    user = _require_taches(request)
    if payload.statut not in TACHES_STATUTS_CODES:
        raise HTTPException(400, "Statut inconnu.")
    now = _now()
    with get_db() as conn:
        avant = _fetch_tache(conn, tache_id)

        # Position : entre `apres_id` et `avant_id` s'ils sont fournis, sinon en tête.
        bornes = []
        for ref_id in (payload.apres_id, payload.avant_id):
            if not ref_id:
                bornes.append(None)
                continue
            r = conn.execute(
                "SELECT ordre FROM taches WHERE id=? AND deleted_at IS NULL", (int(ref_id),)
            ).fetchone()
            bornes.append(float(r["ordre"]) if r else None)
        haut, bas = bornes
        if haut is not None and bas is not None:
            ordre = (haut + bas) / 2
        elif haut is not None:
            ordre = haut + _ORDRE_STEP
        elif bas is not None:
            ordre = bas - _ORDRE_STEP
        else:
            ordre = _next_ordre(conn, payload.statut)

        sets = ["statut=?", "ordre=?", "updated_at=?"]
        params: list = [payload.statut, ordre, now]
        if payload.statut == "en_cours" and not avant.get("started_at"):
            sets.append("started_at=?")
            params.append(now)
        if payload.statut in TACHES_STATUTS_FINAUX:
            sets.append("done_at=?")
            params.append(now)
        elif avant.get("done_at"):
            sets.append("done_at=NULL")
        params.append(tache_id)
        conn.execute(f"UPDATE taches SET {', '.join(sets)} WHERE id=?", params)

        if avant.get("statut") != payload.statut:
            _log(conn, tache_id, user, "statut", "Statut", avant.get("statut"), payload.statut)
        conn.commit()
    return {"success": True, "ordre": ordre}


@router.post("/api/taches/{tache_id}/archive")
def archive_tache(tache_id: int, request: Request):
    user = _require_taches(request)
    with get_db() as conn:
        tache = _fetch_tache(conn, tache_id)
        nouvel_etat = None if tache.get("archived_at") else _now()
        conn.execute(
            "UPDATE taches SET archived_at=?, updated_at=? WHERE id=?",
            (nouvel_etat, _now(), tache_id),
        )
        _log(conn, tache_id, user, "archivage" if nouvel_etat else "desarchivage")
        conn.commit()
    return {"success": True, "archivee": bool(nouvel_etat)}


@router.delete("/api/taches/{tache_id}")
def delete_tache(tache_id: int, request: Request):
    """Suppression logique — les sous-tâches suivent."""
    user = _require_taches(request)
    now = _now()
    with get_db() as conn:
        _fetch_tache(conn, tache_id)
        conn.execute("UPDATE taches SET deleted_at=? WHERE id=?", (now, tache_id))
        conn.execute(
            "UPDATE taches SET deleted_at=? WHERE parent_id=? AND deleted_at IS NULL",
            (now, tache_id),
        )
        _log(conn, tache_id, user, "suppression")
        conn.commit()
    return {"success": True}


@router.post("/api/taches/{tache_id}/temps")
def add_temps(tache_id: int, payload: TempsIn, request: Request):
    """Ajoute des heures au temps passé (incrément, jamais un remplacement)."""
    user = _require_taches(request)
    heures = _valid_heures(payload.heures, "Temps")
    if not heures:
        raise HTTPException(400, "Temps invalide — valeur supérieure à 0 attendue.")
    with get_db() as conn:
        tache = _fetch_tache(conn, tache_id)
        total = round(float(tache.get("temps_passe_h") or 0) + heures, 2)
        conn.execute(
            "UPDATE taches SET temps_passe_h=?, updated_at=? WHERE id=?",
            (total, _now(), tache_id),
        )
        _log(conn, tache_id, user, "temps", "Temps passé",
             tache.get("temps_passe_h"), f"{total} (+{heures})")
        if (payload.note or "").strip():
            conn.execute(
                """INSERT INTO taches_commentaires
                   (tache_id,user_id,auteur_nom,message,created_at)
                   VALUES (?,?,?,?,?)""",
                (tache_id, user.get("id"), _nom(user),
                 f"[{heures} h] {payload.note.strip()}"[:4000], _now()),
            )
        conn.commit()
    return {"success": True, "temps_passe_h": total}


# ─── Commentaires ─────────────────────────────────────────────────────────

@router.post("/api/taches/{tache_id}/commentaires")
def add_commentaire(tache_id: int, payload: CommentaireIn, request: Request):
    user = _require_taches(request)
    message = (payload.message or "").strip()
    if not message:
        raise HTTPException(400, "Commentaire vide.")
    with get_db() as conn:
        _fetch_tache(conn, tache_id)
        cur = conn.execute(
            """INSERT INTO taches_commentaires
               (tache_id,user_id,auteur_nom,message,created_at)
               VALUES (?,?,?,?,?)""",
            (tache_id, user.get("id"), _nom(user), message[:4000], _now()),
        )
        _log(conn, tache_id, user, "commentaire")
        conn.commit()
    return {"success": True, "id": cur.lastrowid}


@router.delete("/api/taches/commentaires/{commentaire_id}")
def delete_commentaire(commentaire_id: int, request: Request):
    user = _require_taches(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT id,tache_id FROM taches_commentaires WHERE id=? AND deleted_at IS NULL",
            (commentaire_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Commentaire introuvable")
        conn.execute(
            "UPDATE taches_commentaires SET deleted_at=? WHERE id=?", (_now(), commentaire_id)
        )
        _log(conn, row["tache_id"], user, "commentaire_supprime")
        conn.commit()
    return {"success": True}


# ─── Fichiers de contexte ─────────────────────────────────────────────────

@router.post("/api/taches/{tache_id}/fichiers")
async def upload_fichier(tache_id: int, request: Request, fichier: UploadFile = File(...)):
    user = _require_taches(request)
    if not fichier.filename:
        raise HTTPException(400, "Aucun fichier reçu.")
    _check_extension(fichier.filename)
    contenu = await fichier.read()
    if len(contenu) > MAX_FILE_BYTES:
        raise HTTPException(400, f"Fichier > {TACHES_MAX_FILE_MB} Mo")
    if not contenu:
        raise HTTPException(400, "Fichier vide.")

    with get_db() as conn:
        _fetch_tache(conn, tache_id)
        dossier = TACHES_ROOT / str(tache_id)
        dossier.mkdir(parents=True, exist_ok=True)
        nom_sur = _sanitize_filename(fichier.filename)
        dest = dossier / f"{uuid.uuid4().hex[:12]}_{nom_sur}"
        with open(dest, "wb") as f:
            f.write(contenu)
        cur = conn.execute(
            """INSERT INTO taches_fichiers
               (tache_id,nom,fichier_path,taille_bytes,mime,uploaded_by,uploaded_nom,created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                tache_id, fichier.filename[:200], str(dest), len(contenu),
                (fichier.content_type or "")[:120], user.get("id"), _nom(user), _now(),
            ),
        )
        _log(conn, tache_id, user, "fichier", "Fichier", None, fichier.filename[:200])
        conn.commit()
    return {"success": True, "id": cur.lastrowid}


@router.get("/api/taches/fichiers/{fichier_id}/download")
def download_fichier(fichier_id: int, request: Request, inline: bool = False):
    """Télécharge ou prévisualise (?inline=1) une pièce jointe."""
    _require_taches(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT nom,fichier_path FROM taches_fichiers WHERE id=? AND deleted_at IS NULL",
            (fichier_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Fichier introuvable")
    chemin = Path(row["fichier_path"])
    if not chemin.is_file():
        raise HTTPException(410, "Fichier absent du serveur")
    nom = row["nom"] or chemin.name
    mime, _ = mimetypes.guess_type(nom)
    if not mime:
        mime = "application/octet-stream"
    if inline:
        return FileResponse(
            str(chemin), media_type=mime,
            headers={"Content-Disposition": f'inline; filename="{nom}"'},
        )
    return FileResponse(str(chemin), filename=nom, media_type=mime)


@router.delete("/api/taches/fichiers/{fichier_id}")
def delete_fichier(fichier_id: int, request: Request):
    user = _require_taches(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT id,tache_id,nom FROM taches_fichiers WHERE id=? AND deleted_at IS NULL",
            (fichier_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Fichier introuvable")
        conn.execute("UPDATE taches_fichiers SET deleted_at=? WHERE id=?", (_now(), fichier_id))
        _log(conn, row["tache_id"], user, "fichier_supprime", "Fichier", row["nom"], None)
        conn.commit()
    return {"success": True}


# ─── Checklist ────────────────────────────────────────────────────────────

@router.post("/api/taches/{tache_id}/checklist")
def add_checklist(tache_id: int, payload: ChecklistIn, request: Request):
    user = _require_taches(request)
    libelle = (payload.libelle or "").strip()
    if not libelle:
        raise HTTPException(400, "Libellé vide.")
    with get_db() as conn:
        _fetch_tache(conn, tache_id)
        row = conn.execute(
            "SELECT MAX(ordre) AS m FROM taches_checklist WHERE tache_id=?", (tache_id,)
        ).fetchone()
        ordre = (float(row["m"]) if row and row["m"] is not None else 0.0) + _ORDRE_STEP
        cur = conn.execute(
            """INSERT INTO taches_checklist (tache_id,libelle,fait,ordre,created_at)
               VALUES (?,?,0,?,?)""",
            (tache_id, libelle[:300], ordre, _now()),
        )
        _log(conn, tache_id, user, "checklist_ajout", "Checklist", None, libelle[:300])
        conn.commit()
    return {"success": True, "id": cur.lastrowid}


@router.put("/api/taches/checklist/{item_id}")
def update_checklist(item_id: int, payload: ChecklistPatch, request: Request):
    user = _require_taches(request)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return {"success": True}
    with get_db() as conn:
        row = conn.execute(
            "SELECT id,tache_id,libelle,fait FROM taches_checklist WHERE id=?", (item_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Élément introuvable")
        sets, params = [], []
        if "libelle" in data:
            libelle = (data["libelle"] or "").strip()
            if not libelle:
                raise HTTPException(400, "Libellé vide.")
            sets.append("libelle=?")
            params.append(libelle[:300])
        if "fait" in data:
            fait = 1 if data["fait"] else 0
            sets.extend(["fait=?", "fait_at=?", "fait_par_nom=?"])
            params.extend([fait, _now() if fait else None, _nom(user) if fait else None])
        params.append(item_id)
        conn.execute(f"UPDATE taches_checklist SET {', '.join(sets)} WHERE id=?", params)
        if "fait" in data:
            _log(conn, row["tache_id"], user,
                 "checklist_coche" if data["fait"] else "checklist_decoche",
                 "Checklist", None, row["libelle"])
        conn.commit()
    return {"success": True}


@router.delete("/api/taches/checklist/{item_id}")
def delete_checklist(item_id: int, request: Request):
    user = _require_taches(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT id,tache_id,libelle FROM taches_checklist WHERE id=?", (item_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Élément introuvable")
        conn.execute("DELETE FROM taches_checklist WHERE id=?", (item_id,))
        _log(conn, row["tache_id"], user, "checklist_supprime", "Checklist", row["libelle"], None)
        conn.commit()
    return {"success": True}
