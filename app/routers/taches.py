"""MySifa — Gestionnaire de tâches (API).

Suivi interne des demandes faites à l'équipe de développement : tâches,
statuts, priorités, assignation, échéances, sous-tâches, checklist, fichiers
de contexte, commentaires et journal d'activité.

Accès : piloté par la matrice database-driven (Paramètres → Accès), app
`taches`. Trois niveaux, trois périmètres :

- `read`  : mes tâches — celles où je suis assigné ou que j'ai créées ;
- `write` : celles-là plus toutes les tâches de mon service, en écriture ;
- `admin` : tous les services (direction, super administrateur).

Le périmètre est calculé à un seul endroit (`_scope_sql`) et appliqué par
`_fetch_tache` : tout endpoint qui charge une tâche par son identifiant est
couvert sans contrôle supplémentaire. Hors périmètre, la réponse est 404 et
non 403 — l'existence d'une tâche d'un autre service ne se déduit pas.

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
    ROLE_SUPERADMIN,
    TACHES_SERVICES_CODES,
    role_label,
    taches_modules,
    taches_priorites,
    taches_services,
    taches_statuts,
    taches_types,
)
from database import get_db
from services.auth_service import (
    effective_role,
    get_current_user,
    user_access_level,
    user_can,
)

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

APP = "taches"


def _niveau(user: dict) -> str:
    """none / read / write / admin sur l'app taches."""
    return user_access_level(user, APP)


def _service(user: dict) -> str:
    """Service de l'utilisateur — c'est son rôle effectif (cf. config.taches_services)."""
    return effective_role(user) or ""


def _require_taches(request: Request, min_level: str = "read") -> dict:
    user = get_current_user(request)
    if not user_can(user, APP, "_app", min_level):
        raise HTTPException(
            status_code=403,
            detail="Accès refusé — gestionnaire de tâches",
        )
    return user


def _scope_sql(user: dict, alias: str = "t") -> tuple[str, list]:
    """Clause SQL du périmètre visible, et ses paramètres.

    Point unique de vérité du cloisonnement : `list`, `stats` et `_fetch_tache`
    l'appellent, personne ne réécrit la règle dans son coin.
    """
    niveau = _niveau(user)
    if niveau == "admin":
        return "1=1", []
    uid = user.get("id")
    miennes = (
        f"(EXISTS (SELECT 1 FROM taches_assignes sc WHERE sc.tache_id={alias}.id"
        f"                                            AND sc.user_id=?)"
        f" OR {alias}.createur_user_id=?)"
    )
    if niveau == "write":
        return f"({alias}.service=? OR {miennes})", [_service(user), uid, uid]
    return miennes, [uid, uid]


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


def _valid_service(user: dict, valeur: Optional[str]) -> str:
    """Service rattaché à une tâche, contrôlé contre le périmètre de l'auteur.

    Sans valeur : le service de l'auteur. Un non-admin qui en vise un autre est
    refusé — sinon il déposerait une tâche dans un périmètre qu'il ne voit pas,
    et la perdrait de vue aussitôt créée.
    """
    service = (valeur or "").strip() or _service(user)
    if service not in TACHES_SERVICES_CODES:
        raise HTTPException(400, "Service inconnu.")
    if _niveau(user) != "admin" and service != _service(user):
        raise HTTPException(403, "Une tâche ne peut être rattachée qu'à votre service.")
    return service


def _next_ordre(conn, statut: str) -> float:
    row = conn.execute(
        "SELECT MIN(ordre) AS m FROM taches WHERE statut=? AND deleted_at IS NULL",
        (statut,),
    ).fetchone()
    mini = row["m"] if row and row["m"] is not None else 0.0
    return float(mini) - _ORDRE_STEP


def _module_codes() -> set:
    return {m["code"] for m in taches_modules()}


# ─── Assignation (plusieurs personnes par tâche) ──────────────────────────

def _valid_assignes(conn, ids) -> list[int]:
    """Normalise une liste d'identifiants : dédoublonnée, ordre stable, actifs."""
    if ids is None:
        return []
    if not isinstance(ids, (list, tuple, set)):
        raise HTTPException(400, "Liste d'assignés invalide.")
    vus: list[int] = []
    for raw in ids:
        try:
            uid = int(raw)
        except (TypeError, ValueError):
            raise HTTPException(400, "Identifiant d'assigné invalide.")
        if uid in vus:
            continue
        if not conn.execute("SELECT 1 FROM users WHERE id=? AND actif=1", (uid,)).fetchone():
            raise HTTPException(400, "Utilisateur assigné introuvable.")
        vus.append(uid)
    return vus


def _set_assignes(conn, tache_id: int, ids: list[int], user: dict) -> tuple[list[int], list[int]]:
    """Applique la liste d'assignés et retourne (ajoutés, retirés).

    Différentiel plutôt que purge + réinsertion : `assigne_at` d'une personne
    déjà assignée n'est pas réécrit à chaque enregistrement de la tâche.
    """
    actuels = [
        r["user_id"]
        for r in conn.execute(
            "SELECT user_id FROM taches_assignes WHERE tache_id=?", (tache_id,)
        ).fetchall()
    ]
    ajoutes = [u for u in ids if u not in actuels]
    retires = [u for u in actuels if u not in ids]
    now = _now()
    for uid in ajoutes:
        conn.execute(
            """INSERT OR IGNORE INTO taches_assignes (tache_id,user_id,assigne_at,assigne_par)
               VALUES (?,?,?,?)""",
            (tache_id, uid, now, _nom(user)),
        )
    for uid in retires:
        conn.execute(
            "DELETE FROM taches_assignes WHERE tache_id=? AND user_id=?", (tache_id, uid)
        )
    return ajoutes, retires


def _noms_users(conn, ids: list[int]) -> str:
    if not ids:
        return "personne"
    rows = conn.execute(
        f"SELECT nom FROM users WHERE id IN ({','.join('?' * len(ids))})", ids
    ).fetchall()
    return ", ".join(str(r["nom"] or "") for r in rows) or "personne"


# Assignés agrégés en une seule chaîne "id:nom:avatar|id:nom:avatar" par tâche.
# Choix délibéré face à une 2e requête ou un JOIN qui dupliquerait les lignes :
# la liste reste courte (quelques personnes) et le front la découpe une fois.
_SQL_ASSIGNES = """(SELECT GROUP_CONCAT(u2.id || ':' || REPLACE(COALESCE(u2.nom,''),'|',' ')
                            || ':' || REPLACE(COALESCE(u2.avatar_url,''),'|',' '), '|')
                       FROM taches_assignes a2
                       JOIN users u2 ON u2.id = a2.user_id
                      WHERE a2.tache_id = t.id)"""


def _parse_assignes(brut: Optional[str]) -> list[dict]:
    out: list[dict] = []
    for morceau in str(brut or "").split("|"):
        if not morceau:
            continue
        parts = morceau.split(":", 2)
        if len(parts) < 2:
            continue
        try:
            uid = int(parts[0])
        except ValueError:
            continue
        out.append({
            "id": uid,
            "nom": parts[1],
            "avatar_url": parts[2] if len(parts) > 2 and parts[2] else None,
        })
    out.sort(key=lambda u: (u["nom"] or "").casefold())
    return out


# ─── Personnes assignables ────────────────────────────────────────────────

def _users_assignables(conn, user: dict) -> list:
    """Comptes actifs qu'on peut assigner : ceux qui peuvent ouvrir l'app.

    Assigner quelqu'un qui recevra un 403 en cliquant n'a pas de sens. La liste
    se déduit donc de la matrice d'accès, pas d'un rôle en dur.

    Tous services confondus, volontairement : une tâche se confie à la personne
    qui sait la traiter, pas à un organigramme. L'assigné la voit à titre
    personnel (clause « mes tâches » du périmètre) sans que la tâche entre pour
    autant dans le périmètre de son service — la confier à quelqu'un ne la
    publie pas à toute son équipe.

    Le contrôle serveur de `_valid_assignes` reste, lui, ouvert à tout compte
    actif : des tâches plus anciennes portent des assignés qui ne sont plus
    proposés ici, et il faut pouvoir les rouvrir et les désassigner.
    """
    filtres = ["u.actif=1"]
    params: list = []

    a_matrice = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='role_access_defaults'"
    ).fetchone()
    if a_matrice:
        filtres.append(
            "(u.role=?"
            " OR EXISTS (SELECT 1 FROM role_access_defaults r"
            "             WHERE r.role=u.role AND r.app_id=? AND r.module_id='_app'"
            "               AND r.level<>'none')"
            " OR EXISTS (SELECT 1 FROM user_access_overrides o"
            "             WHERE o.user_id=u.id AND o.app_id=? AND o.module_id='_app'"
            "               AND o.level<>'none'))"
        )
        params.extend([ROLE_SUPERADMIN, APP, APP])

    return conn.execute(
        f"""SELECT id, nom, role, avatar_url FROM users u
             WHERE {' AND '.join(filtres)}
             ORDER BY nom COLLATE NOCASE""",
        params,
    ).fetchall()


# ─── Schémas ──────────────────────────────────────────────────────────────

class TacheIn(BaseModel):
    titre: str
    description: Optional[str] = None
    statut: Optional[str] = None
    priorite: Optional[str] = None
    type: Optional[str] = None
    module: Optional[str] = None
    service: Optional[str] = None
    assignes: Optional[list[int]] = None
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
    service: Optional[str] = None
    assignes: Optional[list[int]] = None
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
    user = _require_taches(request)
    niveau = _niveau(user)
    mon_service = _service(user)
    with get_db() as conn:
        users = [dict(u) for u in _users_assignables(conn, user)]
    for u in users:
        u["service_label"] = role_label(u.get("role") or "")
    # Un non-admin ne rattache une tâche qu'à son propre service : lui proposer
    # les autres reviendrait à afficher un choix que l'API refusera.
    services = taches_services() if niveau == "admin" else [
        {"code": mon_service, "label": role_label(mon_service)}
    ]
    return {
        "statuts": taches_statuts(),
        "priorites": taches_priorites(),
        "types": taches_types(),
        "modules": taches_modules(),
        "services": services,
        "users": users,
        "niveau": niveau,
        "moi": {
            "id": user.get("id"),
            "nom": user.get("nom") or "",
            "service": mon_service,
            "service_label": role_label(mon_service),
        },
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
    service: Optional[str] = None,
    q: Optional[str] = None,
    archivees: int = 0,
    racines: int = 0,
    non_assignees: int = 0,
):
    """Liste des tâches, avec compteurs agrégés pour l'affichage carte/ligne."""
    user = _require_taches(request)
    where = ["t.deleted_at IS NULL"]
    params: list = []
    # archivees=1 : l'onglet Archives ne montre QUE les tâches archivées.
    # Les inclure en plus des tâches actives ferait doublon avec la vue Liste.
    where.append("t.archived_at IS NOT NULL" if archivees else "t.archived_at IS NULL")
    if statut and statut in TACHES_STATUTS_CODES:
        where.append("t.statut=?")
        params.append(statut)
    if assigne:
        where.append("EXISTS (SELECT 1 FROM taches_assignes a WHERE a.tache_id=t.id AND a.user_id=?)")
        params.append(int(assigne))
    if non_assignees:
        where.append("NOT EXISTS (SELECT 1 FROM taches_assignes a WHERE a.tache_id=t.id)")
    if priorite and priorite in TACHES_PRIORITES_CODES:
        where.append("t.priorite=?")
        params.append(priorite)
    if type and type in TACHES_TYPES_CODES:
        where.append("t.type=?")
        params.append(type)
    if module:
        where.append("t.module=?")
        params.append(module)
    # Filtre d'affichage seulement : il restreint À L'INTÉRIEUR du périmètre,
    # il ne l'élargit jamais — la clause de périmètre est ajoutée après.
    if service:
        where.append("t.service=?")
        params.append(service)
    if racines:
        where.append("t.parent_id IS NULL")
    if q:
        terme = f"%{q.strip()}%"
        where.append("(t.titre LIKE ? OR t.description LIKE ?)")
        params.extend([terme, terme])

    scope, scope_params = _scope_sql(user)
    where.append(scope)
    params.extend(scope_params)

    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT t.*,
                       {_SQL_ASSIGNES} AS assignes_brut,
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
                  LEFT JOIN taches p ON p.id = t.parent_id
                 WHERE {' AND '.join(where)}
                 ORDER BY t.ordre ASC, t.id DESC""",
            list(_FINAUX) + params,
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["assignes"] = _parse_assignes(d.pop("assignes_brut", None))
        d.pop("assigne_user_id", None)
        out.append(d)
    return {"taches": out}


@router.get("/api/taches/badge")
def taches_badge(request: Request):
    """Compteur pour la pastille du portail : mes tâches ouvertes.

    Volontairement séparé de /api/taches/stats : le portail l'interroge en
    boucle pour tous les utilisateurs, il doit rester une requête indexée qui ne
    lit aucune donnée de tâche. Renvoie 0 (jamais une erreur) pour un rôle non
    autorisé — le portail ne doit pas afficher d'échec pour une pastille.

    Pas de clause de périmètre ici : le compteur ne porte que sur les tâches
    assignées à l'utilisateur, qui sont dans son périmètre par construction.
    """
    try:
        user = get_current_user(request)
    except HTTPException:
        return {"count": 0}
    if not user_can(user, APP, "_app", "read"):
        return {"count": 0}
    today = date.today().isoformat()
    with get_db() as conn:
        row = conn.execute(
            f"""SELECT COUNT(*) AS n,
                       SUM(CASE WHEN t.echeance IS NOT NULL AND t.echeance < ? THEN 1 ELSE 0 END) AS retard
                  FROM taches t
                  JOIN taches_assignes a ON a.tache_id = t.id
                 WHERE a.user_id = ?
                   AND t.deleted_at IS NULL AND t.archived_at IS NULL
                   AND t.statut NOT IN ({_FINAUX_PH})""",
            [today, user.get("id")] + list(_FINAUX),
        ).fetchone()
    return {"count": row["n"] or 0, "en_retard": row["retard"] or 0}


@router.get("/api/taches/stats")
def taches_stats(request: Request):
    """Compteurs d'en-tête : par statut, en retard, non assignées.

    Comptés dans le périmètre de l'utilisateur : un chiffre d'en-tête qui
    inclurait des tâches invisibles dans la liste en dessous serait un bug de
    lecture, pas une information.
    """
    user = _require_taches(request)
    today = date.today().isoformat()
    scope, sp = _scope_sql(user)
    with get_db() as conn:
        par_statut = conn.execute(
            f"""SELECT t.statut AS statut, COUNT(*) AS n FROM taches t
                WHERE t.deleted_at IS NULL AND t.archived_at IS NULL AND {scope}
                GROUP BY t.statut""",
            sp,
        ).fetchall()
        retard = conn.execute(
            f"""SELECT COUNT(*) AS n FROM taches t
                WHERE t.deleted_at IS NULL AND t.archived_at IS NULL
                  AND t.echeance IS NOT NULL AND t.echeance < ?
                  AND t.statut NOT IN ({_FINAUX_PH}) AND {scope}""",
            [today] + list(_FINAUX) + sp,
        ).fetchone()
        non_assignees = conn.execute(
            f"""SELECT COUNT(*) AS n FROM taches t
                WHERE t.deleted_at IS NULL AND t.archived_at IS NULL
                  AND NOT EXISTS (SELECT 1 FROM taches_assignes a WHERE a.tache_id=t.id)
                  AND {scope}""",
            sp,
        ).fetchone()
    return {
        "par_statut": {r["statut"]: r["n"] for r in par_statut},
        "en_retard": retard["n"] if retard else 0,
        "non_assignees": non_assignees["n"] if non_assignees else 0,
    }


# ─── Détail ───────────────────────────────────────────────────────────────

def _fetch_tache(conn, tache_id: int, user: dict) -> dict:
    """Charge une tâche DANS le périmètre de l'utilisateur, 404 sinon.

    Tous les endpoints qui manipulent une tâche passent par ici : le contrôle
    de périmètre ne peut pas être oublié sur l'un d'eux.
    """
    scope, scope_params = _scope_sql(user)
    row = conn.execute(
        f"""SELECT t.*, {_SQL_ASSIGNES} AS assignes_brut,
                  p.titre AS parent_titre
             FROM taches t
             LEFT JOIN taches p ON p.id = t.parent_id
            WHERE t.id=? AND t.deleted_at IS NULL AND {scope}""",
        [tache_id] + scope_params,
    ).fetchone()
    if not row:
        raise HTTPException(404, "Tâche introuvable")
    d = dict(row)
    d["assignes"] = _parse_assignes(d.pop("assignes_brut", None))
    d.pop("assigne_user_id", None)
    return d


@router.get("/api/taches/{tache_id}")
def get_tache(tache_id: int, request: Request):
    user = _require_taches(request)
    with get_db() as conn:
        tache = _fetch_tache(conn, tache_id, user)
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
            f"""SELECT t.id,t.titre,t.statut,t.priorite,t.echeance,
                       {_SQL_ASSIGNES} AS assignes_brut
                 FROM taches t
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
        "sous_taches": [
            {**dict(r), "assignes": _parse_assignes(dict(r).pop("assignes_brut", None))}
            for r in sous_taches
        ],
    }


# ─── Création / modification ──────────────────────────────────────────────

@router.post("/api/taches")
def create_tache(payload: TacheIn, request: Request):
    user = _require_taches(request, "write")
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
    service = _valid_service(user, payload.service)
    now = _now()

    with get_db() as conn:
        if payload.parent_id:
            # Le parent doit être dans le périmètre : on ne greffe pas une
            # sous-tâche sur une tâche qu'on n'a pas le droit de voir.
            parent = _fetch_tache(conn, int(payload.parent_id), user)
            if parent.get("parent_id"):
                raise HTTPException(400, "Une sous-tâche ne peut pas avoir de sous-tâches.")
            # Une sous-tâche appartient au service de sa mère : sans ça, la
            # mère et sa fille pourraient se retrouver dans deux périmètres
            # différents et l'arborescence apparaîtrait tronquée.
            service = parent.get("service") or service
        assignes = _valid_assignes(conn, payload.assignes)
        cur = conn.execute(
            """INSERT INTO taches
               (titre,description,statut,priorite,type,module,service,
                createur_user_id,createur_nom,parent_id,echeance,estimation_h,
                temps_passe_h,ordre,created_at,updated_at,started_at,done_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0,?,?,?,?,?)""",
            (
                titre[:300], (payload.description or "").strip() or None,
                statut, priorite, ttype, module, service,
                user.get("id"), _nom(user),
                payload.parent_id, echeance, estimation,
                _next_ordre(conn, statut), now, now,
                now if statut == "en_cours" else None,
                now if statut in TACHES_STATUTS_FINAUX else None,
            ),
        )
        tache_id = cur.lastrowid
        if assignes:
            _set_assignes(conn, tache_id, assignes, user)
        _log(conn, tache_id, user, "creation")
        conn.commit()
    return {"success": True, "id": tache_id}


_PATCH_LABELS = {
    "titre": "Titre", "description": "Description", "statut": "Statut",
    "priorite": "Priorité", "type": "Type", "module": "Module",
    "service": "Service", "echeance": "Échéance",
    "estimation_h": "Estimation", "temps_passe_h": "Temps passé",
}


@router.put("/api/taches/{tache_id}")
def update_tache(tache_id: int, payload: TachePatch, request: Request):
    """Mise à jour partielle : seuls les champs fournis sont écrits."""
    user = _require_taches(request, "write")
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
    if "service" in data:
        # Transférer une tâche à un autre service, c'est la faire sortir de son
        # propre périmètre : réservé au niveau admin.
        data["service"] = _valid_service(user, data["service"])
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
        avant = _fetch_tache(conn, tache_id, user)

        # L'assignation vit dans une table de liaison : elle sort du UPDATE.
        if "assignes" in data:
            cibles = _valid_assignes(conn, data.pop("assignes"))
            ajoutes, retires = _set_assignes(conn, tache_id, cibles, user)
            if ajoutes:
                _log(conn, tache_id, user, "assignation", "Assignés",
                     None, _noms_users(conn, ajoutes))
            if retires:
                _log(conn, tache_id, user, "desassignation", "Assignés",
                     _noms_users(conn, retires), None)
        if not data:
            conn.execute("UPDATE taches SET updated_at=? WHERE id=?", (now, tache_id))
            conn.commit()
            return {"success": True}

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
    user = _require_taches(request, "write")
    if payload.statut not in TACHES_STATUTS_CODES:
        raise HTTPException(400, "Statut inconnu.")
    now = _now()
    with get_db() as conn:
        avant = _fetch_tache(conn, tache_id, user)

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
    user = _require_taches(request, "write")
    with get_db() as conn:
        tache = _fetch_tache(conn, tache_id, user)
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
    user = _require_taches(request, "write")
    now = _now()
    with get_db() as conn:
        _fetch_tache(conn, tache_id, user)
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
    user = _require_taches(request, "write")
    heures = _valid_heures(payload.heures, "Temps")
    if not heures:
        raise HTTPException(400, "Temps invalide — valeur supérieure à 0 attendue.")
    with get_db() as conn:
        tache = _fetch_tache(conn, tache_id, user)
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
    # `read` suffit : quelqu'un d'assigné doit pouvoir répondre sans avoir le
    # droit de modifier la tâche.
    user = _require_taches(request)
    message = (payload.message or "").strip()
    if not message:
        raise HTTPException(400, "Commentaire vide.")
    with get_db() as conn:
        _fetch_tache(conn, tache_id, user)
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
            "SELECT id,tache_id,user_id FROM taches_commentaires "
            "WHERE id=? AND deleted_at IS NULL",
            (commentaire_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Commentaire introuvable")
        # Périmètre de la tâche porteuse, puis propriété du message : on ne
        # supprime pas la parole de quelqu'un d'autre sans être admin.
        _fetch_tache(conn, row["tache_id"], user)
        if row["user_id"] != user.get("id") and _niveau(user) != "admin":
            raise HTTPException(403, "Seul l'auteur peut supprimer son commentaire.")
        conn.execute(
            "UPDATE taches_commentaires SET deleted_at=? WHERE id=?", (_now(), commentaire_id)
        )
        _log(conn, row["tache_id"], user, "commentaire_supprime")
        conn.commit()
    return {"success": True}


# ─── Fichiers de contexte ─────────────────────────────────────────────────

@router.post("/api/taches/{tache_id}/fichiers")
async def upload_fichier(tache_id: int, request: Request, fichier: UploadFile = File(...)):
    user = _require_taches(request, "write")
    if not fichier.filename:
        raise HTTPException(400, "Aucun fichier reçu.")
    _check_extension(fichier.filename)
    contenu = await fichier.read()
    if len(contenu) > MAX_FILE_BYTES:
        raise HTTPException(400, f"Fichier > {TACHES_MAX_FILE_MB} Mo")
    if not contenu:
        raise HTTPException(400, "Fichier vide.")

    with get_db() as conn:
        _fetch_tache(conn, tache_id, user)
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
    user = _require_taches(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT nom,fichier_path,tache_id FROM taches_fichiers "
            "WHERE id=? AND deleted_at IS NULL",
            (fichier_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Fichier introuvable")
        # Une pièce jointe suit le périmètre de sa tâche : sans ce contrôle,
        # une URL devinée servirait le fichier d'un autre service.
        _fetch_tache(conn, row["tache_id"], user)
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
    user = _require_taches(request, "write")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id,tache_id,nom FROM taches_fichiers WHERE id=? AND deleted_at IS NULL",
            (fichier_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Fichier introuvable")
        _fetch_tache(conn, row["tache_id"], user)
        conn.execute("UPDATE taches_fichiers SET deleted_at=? WHERE id=?", (_now(), fichier_id))
        _log(conn, row["tache_id"], user, "fichier_supprime", "Fichier", row["nom"], None)
        conn.commit()
    return {"success": True}


# ─── Checklist ────────────────────────────────────────────────────────────

@router.post("/api/taches/{tache_id}/checklist")
def add_checklist(tache_id: int, payload: ChecklistIn, request: Request):
    user = _require_taches(request, "write")
    libelle = (payload.libelle or "").strip()
    if not libelle:
        raise HTTPException(400, "Libellé vide.")
    with get_db() as conn:
        _fetch_tache(conn, tache_id, user)
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
    user = _require_taches(request, "write")
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return {"success": True}
    with get_db() as conn:
        row = conn.execute(
            "SELECT id,tache_id,libelle,fait FROM taches_checklist WHERE id=?", (item_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Élément introuvable")
        _fetch_tache(conn, row["tache_id"], user)
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
    user = _require_taches(request, "write")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id,tache_id,libelle FROM taches_checklist WHERE id=?", (item_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Élément introuvable")
        _fetch_tache(conn, row["tache_id"], user)
        conn.execute("DELETE FROM taches_checklist WHERE id=?", (item_id,))
        _log(conn, row["tache_id"], user, "checklist_supprime", "Checklist", row["libelle"], None)
        conn.commit()
    return {"success": True}
