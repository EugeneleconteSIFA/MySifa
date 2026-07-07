"""MySifa — Router MyLearning (e-learning + habilitations).

Prefix : /api/learning
Accès  :
  - Endpoints apprenant (formations, videos/progression, quiz, habilitations) :
    tout utilisateur authentifié.
  - Endpoints admin (préfixe /admin) : superadmin uniquement.

Schéma DB (voir migration v160 dans app/core/database.py) :
  - formations                  : catalogue de parcours
  - formation_modules           : chapitres d'un parcours
  - formation_videos            : N vidéos par module (YouTube ID + durée)
  - formation_quiz              : questions QCM 4 choix (>=1 par module)
  - formation_permissions       : permissions débloquées par formation
  - user_video_progression      : pct_vu par vidéo
  - user_module_validation      : quiz_score + valide_le par module
  - user_habilitations          : cache permissions obtenues
  - role_parcours_defaut        : parcours d'accueil obligatoires par rôle

Règles de validation d'un module :
  - Toutes les vidéos actives du module ont pct_vu >= 90
  - Le score au quiz est >= 80 %
  → module_valide_le est renseigné, et si tous les modules de la formation
    sont validés, on peuple user_habilitations avec les permissions liées.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.database import get_db
from app.core.permissions import (
    ALL_PERMISSIONS,
    PERMISSION_LABELS,
    TRANCHE_1,
    TRANCHE_2,
    TRANCHE_3,
    is_known_permission,
)
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/learning", tags=["learning"])


# ─── Constantes métier ────────────────────────────────────────────────────
SEUIL_VIDEO_VUE = 90   # % de visionnage requis pour considérer une vidéo vue
SEUIL_QUIZ_OK   = 80   # % de bonnes réponses requis pour valider le quiz
MIN_QUIZ_QUESTIONS = 1  # au moins 1 question requise par module


# ─── Helpers ──────────────────────────────────────────────────────────────
def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _require_superadmin(request: Request) -> dict:
    user = get_current_user(request)
    if user["role"] != "superadmin":
        raise HTTPException(status_code=403, detail="Réservé au super administrateur")
    return user


# Regex des formats YouTube supportés : watch?v=ID, youtu.be/ID, /embed/ID,
# /shorts/ID, ou juste l'ID (11 chars alphanumeric + `-_`).
_YT_ID_RE = re.compile(r"[A-Za-z0-9_-]{11}")
_YT_URL_PATTERNS = [
    re.compile(r"youtube\.com/watch\?v=([A-Za-z0-9_-]{11})"),
    re.compile(r"youtube\.com/embed/([A-Za-z0-9_-]{11})"),
    re.compile(r"youtube\.com/shorts/([A-Za-z0-9_-]{11})"),
    re.compile(r"youtu\.be/([A-Za-z0-9_-]{11})"),
]


def parse_youtube_id(raw: str) -> str:
    """Extrait l'ID YouTube 11-caractères depuis une URL ou ID brut.
    Lève HTTPException 400 si aucun ID détectable.
    """
    if not raw:
        raise HTTPException(status_code=400, detail="URL ou ID YouTube requis")
    s = raw.strip()
    # Tentative URL
    for pat in _YT_URL_PATTERNS:
        m = pat.search(s)
        if m:
            return m.group(1)
    # Tentative ID brut (11 chars exactly, aucun autre caractère parasite)
    if len(s) == 11 and _YT_ID_RE.fullmatch(s):
        return s
    raise HTTPException(
        status_code=400,
        detail=(
            "Format YouTube non reconnu. Attendu : URL complète "
            "(watch?v=…, youtu.be/…, /shorts/…) ou ID 11 caractères."
        ),
    )


def _formation_row(row) -> dict[str, Any]:
    d = dict(row)
    return {
        "id": d["id"],
        "code": d["code"],
        "titre": d["titre"],
        "description": d.get("description") or "",
        "role_cible": d.get("role_cible") or "",
        "ordre": d.get("ordre") or 100,
        "actif": bool(d.get("actif", 1)),
    }


def _load_formation_full(conn, formation_id: int) -> dict[str, Any]:
    """Charge une formation avec ses modules → vidéos → quiz + permissions."""
    row = conn.execute(
        "SELECT id, code, titre, description, role_cible, ordre, actif "
        "FROM formations WHERE id=? LIMIT 1",
        (formation_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Formation introuvable")

    modules_rows = conn.execute(
        "SELECT id, ordre, titre, description, actif "
        "FROM formation_modules WHERE formation_id=? ORDER BY ordre, id",
        (formation_id,),
    ).fetchall()

    modules: list[dict] = []
    for m in modules_rows:
        mid = m["id"]
        videos = conn.execute(
            "SELECT id, ordre, titre, youtube_id, duree_sec "
            "FROM formation_videos WHERE module_id=? ORDER BY ordre, id",
            (mid,),
        ).fetchall()
        quiz = conn.execute(
            "SELECT id, ordre, question, choix_json, bonne_reponse, explication "
            "FROM formation_quiz WHERE module_id=? ORDER BY ordre, id",
            (mid,),
        ).fetchall()
        modules.append({
            "id": mid,
            "ordre": m["ordre"],
            "titre": m["titre"],
            "description": m["description"] or "",
            "actif": bool(m["actif"]),
            "videos": [dict(v) for v in videos],
            "quiz": [
                {
                    "id": q["id"],
                    "ordre": q["ordre"],
                    "question": q["question"],
                    "choix": json.loads(q["choix_json"]),
                    "bonne_reponse": q["bonne_reponse"],
                    "explication": q["explication"] or "",
                }
                for q in quiz
            ],
        })

    perms = conn.execute(
        "SELECT permission_code FROM formation_permissions WHERE formation_id=?",
        (formation_id,),
    ).fetchall()

    return {
        "formation": _formation_row(row),
        "modules": modules,
        "permissions": [p["permission_code"] for p in perms],
    }


def _load_user_progression(conn, user_id: int, formation_id: int) -> dict[str, Any]:
    """Retourne la progression détaillée d'un utilisateur sur une formation."""
    video_rows = conn.execute(
        """SELECT fv.id as video_id, fv.module_id, uvp.pct_vu
             FROM formation_videos fv
             JOIN formation_modules fm ON fm.id = fv.module_id
             LEFT JOIN user_video_progression uvp
                    ON uvp.video_id = fv.id AND uvp.user_id = ?
            WHERE fm.formation_id = ? AND fm.actif = 1""",
        (user_id, formation_id),
    ).fetchall()
    module_rows = conn.execute(
        """SELECT umv.module_id, umv.quiz_score, umv.valide_le
             FROM user_module_validation umv
             JOIN formation_modules fm ON fm.id = umv.module_id
            WHERE umv.user_id = ? AND fm.formation_id = ?""",
        (user_id, formation_id),
    ).fetchall()
    videos = {r["video_id"]: r["pct_vu"] or 0 for r in video_rows}
    modules = {
        r["module_id"]: {
            "quiz_score": r["quiz_score"],
            "valide_le": r["valide_le"],
        }
        for r in module_rows
    }
    return {"videos": videos, "modules": modules}


# ═════════════════════════════════════════════════════════════════════════
# ─── ENDPOINTS APPRENANT ──────────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════

@router.get("/formations")
def list_formations(request: Request) -> dict:
    """Liste des parcours actifs + résumé progression pour l'utilisateur."""
    user = get_current_user(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, code, titre, description, role_cible, ordre, actif "
            "FROM formations WHERE actif=1 ORDER BY ordre, titre"
        ).fetchall()
        formations = []
        for r in rows:
            fid = r["id"]
            # Nombre total de modules + modules validés
            total_modules = conn.execute(
                "SELECT COUNT(*) FROM formation_modules WHERE formation_id=? AND actif=1",
                (fid,),
            ).fetchone()[0]
            valides = conn.execute(
                """SELECT COUNT(*) FROM user_module_validation umv
                     JOIN formation_modules fm ON fm.id=umv.module_id
                    WHERE umv.user_id=? AND fm.formation_id=? AND umv.valide_le IS NOT NULL""",
                (user["id"], fid),
            ).fetchone()[0]
            f = _formation_row(r)
            f["modules_total"]   = total_modules
            f["modules_valides"] = valides
            f["complete"]        = total_modules > 0 and valides == total_modules
            formations.append(f)
    return {"formations": formations, "user_id": user["id"], "role": user["role"]}


@router.get("/formations/{formation_id}")
def get_formation(formation_id: int, request: Request) -> dict:
    """Détail complet d'un parcours + progression utilisateur."""
    user = get_current_user(request)
    with get_db() as conn:
        data = _load_formation_full(conn, formation_id)
        data["progression"] = _load_user_progression(conn, user["id"], formation_id)
    return data


class VideoProgPayload(BaseModel):
    pct_vu: int


@router.post("/videos/{video_id}/progression")
def upsert_video_progression(video_id: int, request: Request, payload: VideoProgPayload) -> dict:
    """Met à jour le pct_vu d'une vidéo pour l'utilisateur courant."""
    user = get_current_user(request)
    pct = max(0, min(100, int(payload.pct_vu or 0)))
    now = _now()
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, module_id FROM formation_videos WHERE id=? LIMIT 1",
            (video_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Vidéo introuvable")
        existing = conn.execute(
            "SELECT id, pct_vu FROM user_video_progression WHERE user_id=? AND video_id=? LIMIT 1",
            (user["id"], video_id),
        ).fetchone()
        # Ne jamais diminuer pct_vu : si l'utilisateur re-regarde la vidéo,
        # on garde la meilleure valeur atteinte.
        if existing:
            new_pct = max(pct, existing["pct_vu"] or 0)
            conn.execute(
                "UPDATE user_video_progression SET pct_vu=?, updated_at=? WHERE id=?",
                (new_pct, now, existing["id"]),
            )
        else:
            new_pct = pct
            conn.execute(
                "INSERT INTO user_video_progression (user_id,video_id,pct_vu,updated_at) "
                "VALUES (?,?,?,?)",
                (user["id"], video_id, pct, now),
            )
        conn.commit()
        # Après update pct_vu, vérifier si le module peut être validé
        # (uniquement possible si quiz_score déjà présent et >= seuil).
        _try_validate_module(conn, user["id"], row["module_id"])
    return {"ok": True, "pct_vu": new_pct}


class QuizAnswersPayload(BaseModel):
    reponses: dict[str, int]  # {"question_id": choix_index}


@router.post("/modules/{module_id}/quiz")
def submit_quiz(module_id: int, request: Request, payload: QuizAnswersPayload) -> dict:
    """Soumet les réponses au quiz d'un module. Calcule le score et
    déclenche la validation si les 2 conditions sont remplies."""
    user = get_current_user(request)
    with get_db() as conn:
        module_row = conn.execute(
            "SELECT id FROM formation_modules WHERE id=? AND actif=1 LIMIT 1",
            (module_id,),
        ).fetchone()
        if module_row is None:
            raise HTTPException(status_code=404, detail="Module introuvable")
        quiz_rows = conn.execute(
            "SELECT id, choix_json, bonne_reponse FROM formation_quiz WHERE module_id=? ORDER BY ordre, id",
            (module_id,),
        ).fetchall()
        if not quiz_rows:
            raise HTTPException(status_code=400, detail="Ce module n'a pas de quiz")
        total = len(quiz_rows)
        bonnes = 0
        for q in quiz_rows:
            key = str(q["id"])
            reponse = payload.reponses.get(key)
            if reponse is None:
                continue
            try:
                if int(reponse) == int(q["bonne_reponse"]):
                    bonnes += 1
            except (TypeError, ValueError):
                pass
        score = round(100 * bonnes / total)
        now = _now()

        existing = conn.execute(
            "SELECT id, valide_le FROM user_module_validation "
            "WHERE user_id=? AND module_id=? LIMIT 1",
            (user["id"], module_id),
        ).fetchone()
        if existing:
            # On garde le meilleur score jamais atteint.
            # valide_le sera recalculé par _try_validate_module.
            best_score = max(
                score,
                conn.execute(
                    "SELECT COALESCE(quiz_score, 0) FROM user_module_validation WHERE id=?",
                    (existing["id"],),
                ).fetchone()[0],
            )
            conn.execute(
                "UPDATE user_module_validation SET quiz_score=?, updated_at=? WHERE id=?",
                (best_score, now, existing["id"]),
            )
            saved_score = best_score
        else:
            conn.execute(
                "INSERT INTO user_module_validation (user_id,module_id,quiz_score,updated_at) "
                "VALUES (?,?,?,?)",
                (user["id"], module_id, score, now),
            )
            saved_score = score
        conn.commit()
        valide_le = _try_validate_module(conn, user["id"], module_id)
    return {
        "ok": True,
        "score": score,
        "meilleur_score": saved_score,
        "valide_le": valide_le,
        "seuil": SEUIL_QUIZ_OK,
    }


def _try_validate_module(conn, user_id: int, module_id: int) -> Optional[str]:
    """Vérifie que toutes les vidéos du module sont ≥90% ET que le quiz
    a ≥80%. Si oui, renseigne user_module_validation.valide_le et
    éventuellement peuple user_habilitations."""
    # État actuel
    videos = conn.execute(
        "SELECT id FROM formation_videos WHERE module_id=?",
        (module_id,),
    ).fetchall()
    if not videos:
        return None  # Module sans vidéo = pas de validation possible
    video_ids = [v["id"] for v in videos]
    # % moyen sur toutes les vidéos ; toutes doivent être >= seuil.
    q = conn.execute(
        f"""SELECT COUNT(*) FROM user_video_progression
             WHERE user_id=? AND video_id IN ({",".join("?"*len(video_ids))})
               AND pct_vu >= ?""",
        [user_id, *video_ids, SEUIL_VIDEO_VUE],
    ).fetchone()[0]
    videos_ok = (q == len(video_ids))

    validation = conn.execute(
        "SELECT id, quiz_score, valide_le FROM user_module_validation "
        "WHERE user_id=? AND module_id=? LIMIT 1",
        (user_id, module_id),
    ).fetchone()
    if validation is None:
        return None
    quiz_ok = (validation["quiz_score"] or 0) >= SEUIL_QUIZ_OK

    if not (videos_ok and quiz_ok):
        return None
    if validation["valide_le"]:
        return validation["valide_le"]  # déjà validé

    now = _now()
    conn.execute(
        "UPDATE user_module_validation SET valide_le=?, updated_at=? WHERE id=?",
        (now, now, validation["id"]),
    )
    conn.commit()
    # Recalcule les habilitations pour la formation associée.
    formation = conn.execute(
        "SELECT formation_id FROM formation_modules WHERE id=? LIMIT 1",
        (module_id,),
    ).fetchone()
    if formation:
        _recompute_habilitations_for_formation(conn, user_id, formation["formation_id"])
    return now


def _recompute_habilitations_for_formation(conn, user_id: int, formation_id: int) -> None:
    """Si tous les modules actifs d'une formation sont validés, on insère
    les permissions correspondantes dans user_habilitations."""
    total = conn.execute(
        "SELECT COUNT(*) FROM formation_modules WHERE formation_id=? AND actif=1",
        (formation_id,),
    ).fetchone()[0]
    if total == 0:
        return
    valides = conn.execute(
        """SELECT COUNT(*) FROM user_module_validation umv
             JOIN formation_modules fm ON fm.id=umv.module_id
            WHERE umv.user_id=? AND fm.formation_id=? AND umv.valide_le IS NOT NULL
              AND fm.actif=1""",
        (user_id, formation_id),
    ).fetchone()[0]
    if valides < total:
        return
    now = _now()
    perms = conn.execute(
        "SELECT permission_code FROM formation_permissions WHERE formation_id=?",
        (formation_id,),
    ).fetchall()
    for row in perms:
        code = row["permission_code"]
        if not is_known_permission(code):
            continue
        conn.execute(
            "INSERT OR IGNORE INTO user_habilitations "
            "(user_id, permission_code, formation_id, obtenu_le) "
            "VALUES (?,?,?,?)",
            (user_id, code, formation_id, now),
        )
    conn.commit()


@router.get("/habilitations")
def get_habilitations(request: Request) -> dict:
    """Liste des permissions détenues par l'utilisateur courant.
    Le super admin renvoie l'ensemble du catalogue."""
    user = get_current_user(request)
    if user["role"] == "superadmin":
        codes = list(ALL_PERMISSIONS)
    else:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT permission_code FROM user_habilitations WHERE user_id=?",
                (user["id"],),
            ).fetchall()
        codes = [r["permission_code"] for r in rows]
    return {"user_id": user["id"], "role": user["role"], "permissions": codes}


@router.get("/permissions/catalog")
def permissions_catalog(request: Request) -> dict:
    _ = get_current_user(request)

    def _pack(codes):
        return [{"code": c, "label": PERMISSION_LABELS.get(c, c)} for c in codes]

    return {
        "tranche_1": _pack(TRANCHE_1),
        "tranche_2": _pack(TRANCHE_2),
        "tranche_3": _pack(TRANCHE_3),
    }


# ═════════════════════════════════════════════════════════════════════════
# ─── ENDPOINTS ADMIN (superadmin uniquement) ──────────────────────────────
# ═════════════════════════════════════════════════════════════════════════

class FormationCreate(BaseModel):
    code: str
    titre: str
    description: Optional[str] = ""
    role_cible: Optional[str] = ""
    ordre: Optional[int] = 100
    actif: Optional[bool] = True


class FormationUpdate(BaseModel):
    titre: Optional[str] = None
    description: Optional[str] = None
    role_cible: Optional[str] = None
    ordre: Optional[int] = None
    actif: Optional[bool] = None


class ModuleCreate(BaseModel):
    titre: str
    description: Optional[str] = ""
    ordre: Optional[int] = 100


class ModuleUpdate(BaseModel):
    titre: Optional[str] = None
    description: Optional[str] = None
    ordre: Optional[int] = None
    actif: Optional[bool] = None


class VideoCreate(BaseModel):
    titre: str
    youtube_url: str            # accepte URL complète ou ID brut
    duree_sec: Optional[int] = 0
    ordre: Optional[int] = 100


class VideoUpdate(BaseModel):
    titre: Optional[str] = None
    youtube_url: Optional[str] = None
    duree_sec: Optional[int] = None
    ordre: Optional[int] = None


class QuestionCreate(BaseModel):
    question: str
    choix: list[str]            # 2 à 6 éléments
    bonne_reponse: int          # index 0-based
    explication: Optional[str] = ""
    ordre: Optional[int] = 100


class QuestionUpdate(BaseModel):
    question: Optional[str] = None
    choix: Optional[list[str]] = None
    bonne_reponse: Optional[int] = None
    explication: Optional[str] = None
    ordre: Optional[int] = None


class PermissionsPayload(BaseModel):
    permissions: list[str]


@router.get("/admin/formations")
def admin_list_formations(request: Request) -> dict:
    """Vue admin : toutes les formations, actives ET inactives."""
    _require_superadmin(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, code, titre, description, role_cible, ordre, actif "
            "FROM formations ORDER BY ordre, titre"
        ).fetchall()
        formations = []
        for r in rows:
            f = _formation_row(r)
            f["nb_modules"] = conn.execute(
                "SELECT COUNT(*) FROM formation_modules WHERE formation_id=?", (r["id"],)
            ).fetchone()[0]
            f["nb_permissions"] = conn.execute(
                "SELECT COUNT(*) FROM formation_permissions WHERE formation_id=?", (r["id"],)
            ).fetchone()[0]
            formations.append(f)
    return {"formations": formations}


@router.get("/admin/formations/{formation_id}")
def admin_get_formation(formation_id: int, request: Request) -> dict:
    _require_superadmin(request)
    with get_db() as conn:
        return _load_formation_full(conn, formation_id)


@router.post("/admin/formations")
def admin_create_formation(request: Request, payload: FormationCreate) -> dict:
    _require_superadmin(request)
    code = payload.code.strip().lower()
    if not re.match(r"^[a-z0-9_]+$", code):
        raise HTTPException(400, "Code invalide (alphanumérique et _ uniquement)")
    with get_db() as conn:
        exists = conn.execute("SELECT 1 FROM formations WHERE code=? LIMIT 1", (code,)).fetchone()
        if exists:
            raise HTTPException(409, f"Formation avec code '{code}' déjà existante")
        conn.execute(
            "INSERT INTO formations (code,titre,description,role_cible,ordre,actif,cree_le) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                code, payload.titre.strip(),
                (payload.description or "").strip(),
                (payload.role_cible or "").strip(),
                int(payload.ordre or 100),
                1 if payload.actif else 0,
                _now(),
            ),
        )
        fid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
    return {"ok": True, "id": fid}


@router.put("/admin/formations/{formation_id}")
def admin_update_formation(formation_id: int, request: Request, payload: FormationUpdate) -> dict:
    _require_superadmin(request)
    fields, values = [], []
    if payload.titre is not None:
        fields.append("titre=?"); values.append(payload.titre.strip())
    if payload.description is not None:
        fields.append("description=?"); values.append(payload.description.strip())
    if payload.role_cible is not None:
        fields.append("role_cible=?"); values.append(payload.role_cible.strip())
    if payload.ordre is not None:
        fields.append("ordre=?"); values.append(int(payload.ordre))
    if payload.actif is not None:
        fields.append("actif=?"); values.append(1 if payload.actif else 0)
    fields.append("maj_le=?"); values.append(_now())
    if len(fields) == 1:
        raise HTTPException(400, "Aucun champ à modifier")
    values.append(formation_id)
    with get_db() as conn:
        conn.execute(f"UPDATE formations SET {','.join(fields)} WHERE id=?", values)
        conn.commit()
    return {"ok": True}


@router.delete("/admin/formations/{formation_id}")
def admin_delete_formation(formation_id: int, request: Request) -> dict:
    """Supprime formation + tout ce qui en dépend. CASCADE manuel (car
    PRAGMA foreign_keys=OFF)."""
    _require_superadmin(request)
    with get_db() as conn:
        modules = [
            m["id"] for m in conn.execute(
                "SELECT id FROM formation_modules WHERE formation_id=?", (formation_id,)
            ).fetchall()
        ]
        if modules:
            ph = ",".join("?" * len(modules))
            conn.execute(f"DELETE FROM formation_videos WHERE module_id IN ({ph})", modules)
            conn.execute(f"DELETE FROM formation_quiz   WHERE module_id IN ({ph})", modules)
            conn.execute(f"DELETE FROM user_module_validation WHERE module_id IN ({ph})", modules)
        conn.execute("DELETE FROM formation_modules       WHERE formation_id=?", (formation_id,))
        conn.execute("DELETE FROM formation_permissions   WHERE formation_id=?", (formation_id,))
        conn.execute("DELETE FROM user_habilitations      WHERE formation_id=?", (formation_id,))
        conn.execute("DELETE FROM role_parcours_defaut    WHERE formation_id=?", (formation_id,))
        conn.execute("DELETE FROM formations              WHERE id=?", (formation_id,))
        conn.commit()
    return {"ok": True}


# ─── Modules ──────────────────────────────────────────────────────────────
@router.post("/admin/formations/{formation_id}/modules")
def admin_add_module(formation_id: int, request: Request, payload: ModuleCreate) -> dict:
    _require_superadmin(request)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM formations WHERE id=? LIMIT 1", (formation_id,)).fetchone():
            raise HTTPException(404, "Formation introuvable")
        conn.execute(
            "INSERT INTO formation_modules (formation_id,ordre,titre,description,actif,cree_le) "
            "VALUES (?,?,?,?,1,?)",
            (formation_id, int(payload.ordre or 100), payload.titre.strip(),
             (payload.description or "").strip(), _now()),
        )
        mid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
    return {"ok": True, "id": mid}


@router.put("/admin/modules/{module_id}")
def admin_update_module(module_id: int, request: Request, payload: ModuleUpdate) -> dict:
    _require_superadmin(request)
    fields, values = [], []
    if payload.titre is not None:       fields.append("titre=?"); values.append(payload.titre.strip())
    if payload.description is not None: fields.append("description=?"); values.append(payload.description.strip())
    if payload.ordre is not None:       fields.append("ordre=?"); values.append(int(payload.ordre))
    if payload.actif is not None:       fields.append("actif=?"); values.append(1 if payload.actif else 0)
    if not fields:
        raise HTTPException(400, "Aucun champ à modifier")
    values.append(module_id)
    with get_db() as conn:
        conn.execute(f"UPDATE formation_modules SET {','.join(fields)} WHERE id=?", values)
        conn.commit()
    return {"ok": True}


@router.delete("/admin/modules/{module_id}")
def admin_delete_module(module_id: int, request: Request) -> dict:
    _require_superadmin(request)
    with get_db() as conn:
        conn.execute("DELETE FROM formation_videos      WHERE module_id=?", (module_id,))
        conn.execute("DELETE FROM formation_quiz        WHERE module_id=?", (module_id,))
        conn.execute("DELETE FROM user_video_progression WHERE video_id IN (SELECT id FROM formation_videos WHERE module_id=?)", (module_id,))
        conn.execute("DELETE FROM user_module_validation WHERE module_id=?", (module_id,))
        conn.execute("DELETE FROM formation_modules     WHERE id=?", (module_id,))
        conn.commit()
    return {"ok": True}


# ─── Vidéos ───────────────────────────────────────────────────────────────
@router.post("/admin/modules/{module_id}/videos")
def admin_add_video(module_id: int, request: Request, payload: VideoCreate) -> dict:
    _require_superadmin(request)
    yid = parse_youtube_id(payload.youtube_url)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM formation_modules WHERE id=? LIMIT 1", (module_id,)).fetchone():
            raise HTTPException(404, "Module introuvable")
        conn.execute(
            "INSERT INTO formation_videos (module_id,ordre,titre,youtube_id,duree_sec,cree_le) "
            "VALUES (?,?,?,?,?,?)",
            (module_id, int(payload.ordre or 100), payload.titre.strip(),
             yid, int(payload.duree_sec or 0), _now()),
        )
        vid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
    return {"ok": True, "id": vid, "youtube_id": yid}


@router.put("/admin/videos/{video_id}")
def admin_update_video(video_id: int, request: Request, payload: VideoUpdate) -> dict:
    _require_superadmin(request)
    fields, values = [], []
    if payload.titre is not None:      fields.append("titre=?"); values.append(payload.titre.strip())
    if payload.youtube_url is not None:
        yid = parse_youtube_id(payload.youtube_url)
        fields.append("youtube_id=?"); values.append(yid)
    if payload.duree_sec is not None:  fields.append("duree_sec=?"); values.append(int(payload.duree_sec))
    if payload.ordre is not None:      fields.append("ordre=?"); values.append(int(payload.ordre))
    if not fields:
        raise HTTPException(400, "Aucun champ à modifier")
    values.append(video_id)
    with get_db() as conn:
        conn.execute(f"UPDATE formation_videos SET {','.join(fields)} WHERE id=?", values)
        conn.commit()
    return {"ok": True}


@router.delete("/admin/videos/{video_id}")
def admin_delete_video(video_id: int, request: Request) -> dict:
    _require_superadmin(request)
    with get_db() as conn:
        conn.execute("DELETE FROM user_video_progression WHERE video_id=?", (video_id,))
        conn.execute("DELETE FROM formation_videos       WHERE id=?", (video_id,))
        conn.commit()
    return {"ok": True}


# ─── Quiz ─────────────────────────────────────────────────────────────────
def _validate_quiz_payload(choix: list[str], bonne_reponse: int) -> None:
    if not isinstance(choix, list) or not (2 <= len(choix) <= 6):
        raise HTTPException(400, "Le nombre de choix doit être entre 2 et 6")
    if any((not isinstance(c, str)) or not c.strip() for c in choix):
        raise HTTPException(400, "Les choix ne peuvent pas être vides")
    if not (0 <= int(bonne_reponse) < len(choix)):
        raise HTTPException(400, f"bonne_reponse doit être entre 0 et {len(choix)-1}")


@router.post("/admin/modules/{module_id}/quiz")
def admin_add_question(module_id: int, request: Request, payload: QuestionCreate) -> dict:
    _require_superadmin(request)
    _validate_quiz_payload(payload.choix, payload.bonne_reponse)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM formation_modules WHERE id=? LIMIT 1", (module_id,)).fetchone():
            raise HTTPException(404, "Module introuvable")
        conn.execute(
            "INSERT INTO formation_quiz (module_id,ordre,question,choix_json,bonne_reponse,explication) "
            "VALUES (?,?,?,?,?,?)",
            (
                module_id, int(payload.ordre or 100),
                payload.question.strip(),
                json.dumps([c.strip() for c in payload.choix], ensure_ascii=False),
                int(payload.bonne_reponse),
                (payload.explication or "").strip(),
            ),
        )
        qid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
    return {"ok": True, "id": qid}


@router.put("/admin/quiz/{question_id}")
def admin_update_question(question_id: int, request: Request, payload: QuestionUpdate) -> dict:
    _require_superadmin(request)
    fields, values = [], []
    if payload.question is not None:
        fields.append("question=?"); values.append(payload.question.strip())
    if payload.choix is not None or payload.bonne_reponse is not None:
        # Si l'un des deux change, on relit l'autre depuis la DB pour valider.
        with get_db() as conn:
            row = conn.execute(
                "SELECT choix_json, bonne_reponse FROM formation_quiz WHERE id=? LIMIT 1",
                (question_id,),
            ).fetchone()
            if row is None:
                raise HTTPException(404, "Question introuvable")
            choix = payload.choix if payload.choix is not None else json.loads(row["choix_json"])
            br = payload.bonne_reponse if payload.bonne_reponse is not None else row["bonne_reponse"]
            _validate_quiz_payload(choix, br)
            fields.append("choix_json=?"); values.append(json.dumps([c.strip() for c in choix], ensure_ascii=False))
            fields.append("bonne_reponse=?"); values.append(int(br))
    if payload.explication is not None:
        fields.append("explication=?"); values.append(payload.explication.strip())
    if payload.ordre is not None:
        fields.append("ordre=?"); values.append(int(payload.ordre))
    if not fields:
        raise HTTPException(400, "Aucun champ à modifier")
    values.append(question_id)
    with get_db() as conn:
        conn.execute(f"UPDATE formation_quiz SET {','.join(fields)} WHERE id=?", values)
        conn.commit()
    return {"ok": True}


@router.delete("/admin/quiz/{question_id}")
def admin_delete_question(question_id: int, request: Request) -> dict:
    _require_superadmin(request)
    with get_db() as conn:
        conn.execute("DELETE FROM formation_quiz WHERE id=?", (question_id,))
        conn.commit()
    return {"ok": True}


# ─── Permissions débloquées par la formation ──────────────────────────────
@router.put("/admin/formations/{formation_id}/permissions")
def admin_set_permissions(formation_id: int, request: Request, payload: PermissionsPayload) -> dict:
    """Remplace la liste complète des permissions liées à une formation."""
    _require_superadmin(request)
    codes = [c.strip() for c in (payload.permissions or []) if c and c.strip()]
    for c in codes:
        if not is_known_permission(c):
            raise HTTPException(400, f"Permission inconnue : {c}")
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM formations WHERE id=? LIMIT 1", (formation_id,)).fetchone():
            raise HTTPException(404, "Formation introuvable")
        conn.execute("DELETE FROM formation_permissions WHERE formation_id=?", (formation_id,))
        for c in codes:
            conn.execute(
                "INSERT INTO formation_permissions (formation_id, permission_code) VALUES (?,?)",
                (formation_id, c),
            )
        conn.commit()
    return {"ok": True, "permissions": codes}
