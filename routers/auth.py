"""SIFA — Auth v0.8 — profil utilisateur + fiche admin"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import JSONResponse, Response as PlainResponse

from database import get_db
from services.auth_service import (
    login_user, delete_session, get_current_user, get_optional_user,
    require_admin, hash_password
)
from config import COOKIE_NAME, SESSION_HOURS

router = APIRouter()

VALID_ROLES = {"fabrication", "administration", "direction", "logistique"}


# ─── Login ────────────────────────────────────────────────────────
@router.post("/api/auth/login")
async def login(request: Request):
    body = await request.json()
    email    = body.get("email", "")
    password = body.get("password", "")
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email et mot de passe requis")
    result = login_user(email, password)
    user   = result["user"]
    token  = result["token"]
    response = JSONResponse({"success": True, "user": {
        "id": user["id"], "nom": user["nom"], "email": user["email"],
        "role": user["role"], "operateur_lie": user["operateur_lie"],
        "telephone": user.get("telephone", ""),
    }})
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
            "SELECT id,email,nom,role,operateur_lie,telephone FROM users WHERE id=?",
            (user["id"],)
        ).fetchone()
    if not row:
        return PlainResponse(content=b"null", media_type="application/json")
    return dict(row)


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


# ─── Gestion utilisateurs (admin only) ───────────────────────────
@router.get("/api/users")
def list_users(request: Request):
    require_admin(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id,email,nom,role,operateur_lie,actif,telephone,created_at,last_login
               FROM users ORDER BY role DESC, nom ASC"""
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/api/users/{user_id}")
def get_user(user_id: int, request: Request):
    """Fiche détaillée d'un utilisateur — admin uniquement."""
    require_admin(request)
    with get_db() as conn:
        row = conn.execute(
            """SELECT id,email,nom,role,operateur_lie,actif,telephone,created_at,last_login
               FROM users WHERE id=?""", (user_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return dict(row)


@router.post("/api/users")
async def create_user(request: Request):
    require_admin(request)
    body = await request.json()

    email = (body.get("email") or "").strip().lower()
    nom   = (body.get("nom")   or "").strip()
    pwd   = (body.get("password") or "").strip()
    role  = body.get("role", "fabrication")
    op    = (body.get("operateur_lie") or "").strip() or None
    tel   = (body.get("telephone") or "").strip() or None

    if not email or not nom or not pwd:
        raise HTTPException(status_code=400, detail="Email, nom et mot de passe requis")
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Rôle invalide")
    if len(pwd) < 8:
        raise HTTPException(status_code=400, detail="Mot de passe minimum 8 caractères")

    with get_db() as conn:
        try:
            conn.execute(
                """INSERT INTO users (email,nom,password_hash,role,operateur_lie,telephone,actif,created_at)
                   VALUES (?,?,?,?,?,?,1,?)""",
                (email, nom, hash_password(pwd), role, op, tel, datetime.now().isoformat())
            )
            conn.commit()
        except Exception:
            raise HTTPException(status_code=409, detail="Email déjà utilisé")

    return {"success": True}


@router.put("/api/users/{user_id}")
async def update_user(user_id: int, request: Request):
    require_admin(request)
    body = await request.json()

    with get_db() as conn:
        ex = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

        nom      = body.get("nom")           or ex["nom"]
        role     = body.get("role")          or ex["role"]
        op       = body.get("operateur_lie", ex["operateur_lie"])
        actif    = body.get("actif",         ex["actif"])
        tel      = body.get("telephone")     or (ex["telephone"] if "telephone" in ex.keys() else "") or ""
        email    = (body.get("email") or ex["email"]).strip().lower()
        pwd_hash = ex["password_hash"]

        if role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail="Rôle invalide")

        if "password" in body and body["password"]:
            if len(body["password"]) < 8:
                raise HTTPException(status_code=400, detail="Mot de passe minimum 8 caractères")
            pwd_hash = hash_password(body["password"])

        conn.execute(
            """UPDATE users SET nom=?,email=?,role=?,operateur_lie=?,actif=?,telephone=?,
               password_hash=? WHERE id=?""",
            (nom, email, role, op, actif, tel, pwd_hash, user_id)
        )
        conn.commit()

    return {"success": True}


@router.post("/api/users/{user_id}/reset-password")
def reset_password(user_id: int, request: Request):
    """Admin génère un mot de passe temporaire pour un utilisateur."""
    require_admin(request)
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
    admin = require_admin(request)
    if admin["id"] == user_id:
        raise HTTPException(status_code=400, detail="Impossible de désactiver votre propre compte")
    with get_db() as conn:
        conn.execute("UPDATE users SET actif=0 WHERE id=?", (user_id,))
        conn.commit()
    return {"success": True}
