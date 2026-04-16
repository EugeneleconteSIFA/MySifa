"""SIFA — Auth v0.8 — profil utilisateur + fiche admin"""
import json
from datetime import datetime
from typing import Optional
import re
import unicodedata
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import JSONResponse, Response as PlainResponse

from database import get_db
from services.auth_service import (
    login_user,
    delete_session,
    get_current_user,
    get_optional_user,
    hash_password,
    merged_app_access,
    parse_access_overrides_raw,
    require_superadmin,
)
from config import (
    ACCESS_OVERRIDABLE_APPS,
    ASSIGNABLE_ROLES,
    COOKIE_NAME,
    ROLE_SUPERADMIN,
    SESSION_HOURS,
    SUPERADMIN_EMAIL,
)

router = APIRouter()

def _norm_email(s: str) -> str:
    return (s or "").strip().lower()


def _is_designated_superadmin_row(row_email: str, row_role: str) -> bool:
    return _norm_email(row_email) == _norm_email(SUPERADMIN_EMAIL) and row_role == ROLE_SUPERADMIN


def _validate_user_role_write(*, target_email: str, target_role: str, existing_email: str, existing_role: str) -> str:
    """Retourne le rôle effectif à enregistrer. Lève HTTPException si interdit."""
    t_em = _norm_email(target_email)
    sup_em = _norm_email(SUPERADMIN_EMAIL)

    if _is_designated_superadmin_row(existing_email, existing_role):
        if t_em != sup_em:
            raise HTTPException(status_code=400, detail="L'email du compte super administrateur ne peut pas être modifié.")
        if target_role != ROLE_SUPERADMIN:
            raise HTTPException(
                status_code=400,
                detail="Le compte super administrateur désigné ne peut pas être rétrogradé.",
            )
        return ROLE_SUPERADMIN

    if target_role == ROLE_SUPERADMIN:
        return ROLE_SUPERADMIN

    if t_em == sup_em:
        raise HTTPException(
            status_code=400,
            detail="Cet email est réservé au compte super administrateur.",
        )

    if target_role not in ASSIGNABLE_ROLES:
        raise HTTPException(status_code=400, detail="Rôle invalide")

    return target_role


def _normalize_access_overrides_payload(raw: object) -> Optional[str]:
    """Retourne JSON à stocker ou None si aucune surcharge."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise HTTPException(status_code=400, detail="access_overrides doit être un objet")
    clean = {}
    for k, v in raw.items():
        if k not in ACCESS_OVERRIDABLE_APPS:
            continue
        if not isinstance(v, bool):
            raise HTTPException(status_code=400, detail=f"Valeur booléenne attendue pour {k}")
        clean[k] = v
    if not clean:
        return None
    return json.dumps(clean)


def _slug_ident(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _default_identifiant_from_nom(nom: str) -> str:
    parts = _slug_ident(nom).split(" ")
    parts = [p for p in parts if p]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]}.{parts[1]}"


def _ensure_unique_identifiant(conn, ident: str, exclude_user_id: Optional[int] = None) -> str:
    base = _slug_ident(ident).replace(" ", ".")
    base = base.replace("..", ".").strip(".")
    if not base:
        return ""
    cand = base
    i = 2
    while True:
        if exclude_user_id is None:
            row = conn.execute("SELECT id FROM users WHERE identifiant=?", (cand,)).fetchone()
        else:
            row = conn.execute("SELECT id FROM users WHERE identifiant=? AND id!=?", (cand, exclude_user_id)).fetchone()
        if not row:
            return cand
        cand = f"{base}{i}"
        i += 1


def _user_public_dict(row: dict) -> dict:
    d = dict(row)
    if "password_hash" in d:
        del d["password_hash"]
    ov = d.get("access_overrides")
    d["access_overrides"] = parse_access_overrides_raw(ov)
    d["app_access"] = merged_app_access(d.get("role"), ov)
    return d


# ─── Login ────────────────────────────────────────────────────────
@router.post("/api/auth/login")
async def login(request: Request):
    body = await request.json()
    email    = body.get("email", "")
    password = body.get("password", "")
    if not email or not password:
        raise HTTPException(status_code=400, detail="Identifiant/email et mot de passe requis")
    result = login_user(email, password)
    user   = result["user"]
    token  = result["token"]
    u_pub = _user_public_dict(user)
    response = JSONResponse({
        "success": True,
        "user": {
            "id": u_pub["id"],
            "nom": u_pub["nom"],
            "email": u_pub["email"],
            "role": u_pub["role"],
            "operateur_lie": u_pub.get("operateur_lie"),
            "telephone": u_pub.get("telephone", ""),
            "app_access": u_pub.get("app_access", {}),
        },
    })
    response.set_cookie(
        key=COOKIE_NAME, value=token, httponly=True,
        samesite="lax", secure=False, max_age=SESSION_HOURS * 3600,
    )
    return response


# ─── Logout ───────────────────────────────────────────────────────
@router.post("/api/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        delete_session(token)
    response.delete_cookie(COOKIE_NAME)
    return {"success": True}


# ─── Profil courant ───────────────────────────────────────────────
@router.get("/api/auth/me")
def me(request: Request):
    """200 + JSON utilisateur, ou 200 + `null` si pas de session (pas de 401 : évite le bruit console / DevTools)."""
    user = get_optional_user(request)
    if not user:
        return PlainResponse(content=b"null", media_type="application/json")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id,email,identifiant,nom,role,operateur_lie,machine_id,telephone,access_overrides FROM users WHERE id=?",
            (user["id"],)
        ).fetchone()
    if not row:
        return PlainResponse(content=b"null", media_type="application/json")
    d = dict(row)
    ov_raw = d.get("access_overrides")
    d["access_overrides"] = parse_access_overrides_raw(ov_raw)
    d["app_access"] = merged_app_access(d.get("role"), ov_raw)
    return d


@router.put("/api/auth/me")
async def update_me(request: Request):
    """L'utilisateur met à jour son propre profil."""
    user = get_current_user(request)
    body = await request.json()

    with get_db() as conn:
        ex = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

        nom       = (body.get("nom")       or ex["nom"]).strip()
        email     = (body.get("email")     or ex["email"]).strip().lower()
        telephone = (body.get("telephone") or ex.get("telephone") or "").strip()
        pwd_hash  = ex["password_hash"]

        if "password" in body and body["password"]:
            if len(body["password"]) < 8:
                raise HTTPException(status_code=400, detail="Mot de passe minimum 8 caractères")
            # Vérifier confirmation
            if body.get("password_confirm") and body["password"] != body["password_confirm"]:
                raise HTTPException(status_code=400, detail="Les mots de passe ne correspondent pas")
            pwd_hash = hash_password(body["password"])

        # Vérifier unicité email si changé
        if email != ex["email"]:
            existing = conn.execute(
                "SELECT id FROM users WHERE email=? AND id!=?", (email, user["id"])
            ).fetchone()
            if existing:
                raise HTTPException(status_code=409, detail="Email déjà utilisé")

        conn.execute(
            "UPDATE users SET nom=?,email=?,telephone=?,password_hash=? WHERE id=?",
            (nom, email, telephone, pwd_hash, user["id"])
        )
        conn.commit()

    return {"success": True}


# ─── Gestion utilisateurs (super admin uniquement) ──────────────
@router.get("/api/users")
def list_users(request: Request):
    require_superadmin(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT u.id,u.email,u.identifiant,u.nom,u.role,u.operateur_lie,u.actif,u.telephone,u.machine_id,
                      u.created_at,u.last_login,u.access_overrides,
                      m.nom AS machine_nom
               FROM users u
               LEFT JOIN machines m ON m.id = u.machine_id
               ORDER BY u.role DESC, u.nom ASC"""
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        raw = d.get("access_overrides")
        d["access_overrides"] = parse_access_overrides_raw(raw)
        d["app_access"] = merged_app_access(d.get("role"), raw)
        out.append(d)
    return out


@router.get("/api/users/{user_id}")
def get_user(user_id: int, request: Request):
    """Fiche détaillée d'un utilisateur — super admin uniquement."""
    require_superadmin(request)
    with get_db() as conn:
        row = conn.execute(
            """SELECT u.id,u.email,u.identifiant,u.nom,u.role,u.operateur_lie,u.actif,u.telephone,u.machine_id,
                      u.created_at,u.last_login,u.access_overrides,
                      m.nom AS machine_nom
               FROM users u
               LEFT JOIN machines m ON m.id = u.machine_id
               WHERE u.id=?""",
            (user_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    d = dict(row)
    raw = d.get("access_overrides")
    d["access_overrides"] = parse_access_overrides_raw(raw)
    d["app_access"] = merged_app_access(d.get("role"), raw)
    return d


@router.post("/api/users")
async def create_user(request: Request):
    require_superadmin(request)
    body = await request.json()

    email = (body.get("email") or "").strip().lower()
    ident = (body.get("identifiant") or "").strip().lower()
    nom   = (body.get("nom")   or "").strip()
    pwd   = (body.get("password") or "").strip()
    role  = body.get("role", "fabrication")
    op    = (body.get("operateur_lie") or "").strip() or None
    tel   = (body.get("telephone") or "").strip() or None
    machine_id = body.get("machine_id") or None

    if not email or not nom or not pwd:
        raise HTTPException(status_code=400, detail="Email, nom et mot de passe requis")
    if role not in ASSIGNABLE_ROLES and role != ROLE_SUPERADMIN:
        raise HTTPException(status_code=400, detail="Rôle invalide")
    if _norm_email(email) == _norm_email(SUPERADMIN_EMAIL) and role != ROLE_SUPERADMIN:
        raise HTTPException(
            status_code=400,
            detail="Cet email est réservé au compte super administrateur.",
        )
    if len(pwd) < 8:
        raise HTTPException(status_code=400, detail="Mot de passe minimum 8 caractères")

    with get_db() as conn:
        try:
            if not ident:
                ident = _default_identifiant_from_nom(nom)
            ident = _ensure_unique_identifiant(conn, ident) if ident else ""
            conn.execute(
                """INSERT INTO users (email,identifiant,nom,password_hash,role,operateur_lie,telephone,machine_id,actif,created_at)
                   VALUES (?,?,?,?,?,?,?,?,1,?)""",
                (email, ident or None, nom, hash_password(pwd), role, op, tel, machine_id, datetime.now().isoformat())
            )
            conn.commit()
        except Exception:
            raise HTTPException(status_code=409, detail="Email déjà utilisé")

    return {"success": True}


@router.put("/api/users/{user_id}")
async def update_user(user_id: int, request: Request):
    require_superadmin(request)
    body = await request.json()

    with get_db() as conn:
        ex = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

        nom      = body.get("nom")           or ex["nom"]
        role_req = body.get("role")          or ex["role"]
        op       = body.get("operateur_lie", ex["operateur_lie"])
        actif    = body.get("actif",         ex["actif"])
        tel      = body.get("telephone")     or (ex["telephone"] if "telephone" in ex.keys() else "") or ""
        email    = (body.get("email") or ex["email"]).strip().lower()
        ident_in = (body.get("identifiant") if "identifiant" in body else ex.get("identifiant")) or ""
        ident_in = str(ident_in).strip().lower()
        pwd_hash = ex["password_hash"]
        # machine_id : None si la clé est présente et vide, sinon valeur existante
        if "machine_id" in body:
            raw_mid = body["machine_id"]
            machine_id = int(raw_mid) if raw_mid not in (None, "", 0, "0") else None
        else:
            machine_id = ex["machine_id"] if "machine_id" in ex.keys() else None

        role_eff = _validate_user_role_write(
            target_email=email,
            target_role=role_req,
            existing_email=ex["email"],
            existing_role=ex["role"],
        )

        if "password" in body and body["password"]:
            if len(body["password"]) < 8:
                raise HTTPException(status_code=400, detail="Mot de passe minimum 8 caractères")
            pwd_hash = hash_password(body["password"])

        ao_sql: Optional[str]
        if "access_overrides" in body:
            ao_sql = _normalize_access_overrides_payload(body.get("access_overrides"))
        else:
            ao_sql = None

        # identifiant: générer si vide (ou si absent en base) à partir du nom, puis assurer unicité.
        if not ident_in:
            ident_in = _default_identifiant_from_nom(str(nom or ""))
        ident_sql = _ensure_unique_identifiant(conn, ident_in, exclude_user_id=user_id) if ident_in else ""

        if "access_overrides" in body:
            conn.execute(
                """UPDATE users SET nom=?,email=?,identifiant=?,role=?,operateur_lie=?,actif=?,telephone=?,
                   password_hash=?,access_overrides=?,machine_id=? WHERE id=?""",
                (nom, email, ident_sql or None, role_eff, op, actif, tel, pwd_hash, ao_sql, machine_id, user_id),
            )
        else:
            conn.execute(
                """UPDATE users SET nom=?,email=?,identifiant=?,role=?,operateur_lie=?,actif=?,telephone=?,
                   password_hash=?,machine_id=? WHERE id=?""",
                (nom, email, ident_sql or None, role_eff, op, actif, tel, pwd_hash, machine_id, user_id),
            )
        conn.commit()

    return {"success": True}


@router.post("/api/users/{user_id}/reset-password")
def reset_password(user_id: int, request: Request):
    """Super admin génère un mot de passe temporaire pour un utilisateur."""
    require_superadmin(request)
    import secrets, string

    # Génère un mdp lisible : 10 caractères alphanumériques
    chars = string.ascii_letters + string.digits
    temp_pwd = ''.join(secrets.choice(chars) for _ in range(10))

    with get_db() as conn:
        ex = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

        conn.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (hash_password(temp_pwd), user_id),
        )
        conn.commit()

    return {"success": True, "temp_password": temp_pwd}


@router.delete("/api/users/{user_id}")
def deactivate_user(user_id: int, request: Request):
    actor = require_superadmin(request)
    if actor["id"] == user_id:
        raise HTTPException(status_code=400, detail="Impossible de désactiver votre propre compte")
    with get_db() as conn:
        ex = conn.execute("SELECT email, role FROM users WHERE id=?", (user_id,)).fetchone()
        if ex and _is_designated_superadmin_row(ex["email"], ex["role"]):
            raise HTTPException(status_code=400, detail="Impossible de désactiver le compte super administrateur")
        conn.execute("UPDATE users SET actif=0 WHERE id=?", (user_id,))
        conn.commit()
    return {"success": True}
