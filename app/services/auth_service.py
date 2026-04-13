"""
SIFA — Service authentification v0.6
Gestion des 3 rôles : direction, administration, fabrication
"""
import bcrypt
import json
import secrets
from datetime import datetime, timedelta
from typing import Any, Optional
from fastapi import Request, HTTPException

from database import get_db
from config import (
    SESSION_HOURS,
    COOKIE_NAME,
    ROLES_ADMIN,
    ACCESS_OVERRIDABLE_APPS,
    ROLE_SUPERADMIN,
    default_app_access_for_role,
)


# ─── Passwords ────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ─── Sessions ─────────────────────────────────────────────────────
def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now()
    expires = now + timedelta(hours=SESSION_HOURS)
    with get_db() as conn:
        conn.execute("DELETE FROM sessions WHERE user_id=? AND expires_at<?",
                     (user_id, now.isoformat()))
        conn.execute("INSERT INTO sessions (user_id,token,created_at,expires_at) VALUES (?,?,?,?)",
                     (user_id, token, now.isoformat(), expires.isoformat()))
        conn.execute("UPDATE users SET last_login=? WHERE id=?",
                     (now.isoformat(), user_id))
        conn.commit()
    return token

def delete_session(token: str):
    with get_db() as conn:
        conn.execute("DELETE FROM sessions WHERE token=?", (token,))
        conn.commit()

def get_user_by_token(token: str) -> Optional[dict]:
    now = datetime.now().isoformat()
    with get_db() as conn:
        row = conn.execute(
            """SELECT u.id, u.email, u.nom, u.role, u.operateur_lie, u.machine_id, u.actif, u.access_overrides
               FROM sessions s JOIN users u ON s.user_id=u.id
               WHERE s.token=? AND s.expires_at>? AND u.actif=1""",
            (token, now)
        ).fetchone()
    return dict(row) if row else None


def parse_access_overrides_raw(raw: Any) -> dict:
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return {k: bool(v) for k, v in raw.items() if k in ACCESS_OVERRIDABLE_APPS and isinstance(v, bool)}
    try:
        o = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(o, dict):
        return {}
    return {k: bool(v) for k, v in o.items() if k in ACCESS_OVERRIDABLE_APPS and isinstance(v, bool)}


def merged_app_access(role: str, overrides_raw: Any) -> dict:
    if role == ROLE_SUPERADMIN:
        return default_app_access_for_role(ROLE_SUPERADMIN)
    base = default_app_access_for_role(role)
    ov = parse_access_overrides_raw(overrides_raw)
    out = dict(base)
    for k, v in ov.items():
        if k in out:
            out[k] = v
    return out


def user_has_app_access(user: dict, app: str) -> bool:
    """Accès effectif à une application (inclut surcharges par utilisateur sauf Paramètres)."""
    if app == "settings":
        return user.get("role") == ROLE_SUPERADMIN
    acc = merged_app_access(user.get("role"), user.get("access_overrides"))
    return bool(acc.get(app))


# ─── Résolution utilisateur ───────────────────────────────────────
def get_optional_user(request: Request) -> Optional[dict]:
    """Session valide ou None — sans lever d'exception (pour /api/auth/me)."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return get_user_by_token(token)


def get_current_user(request: Request) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Non authentifié")
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expirée ou invalide")
    return user

def require_admin(request: Request) -> dict:
    """Exige direction, administration ou super admin."""
    user = get_current_user(request)
    if user["role"] not in ROLES_ADMIN:
        raise HTTPException(status_code=403, detail="Accès réservé à l'administration")
    return user


def is_superadmin(user: dict) -> bool:
    """Super admin : tout compte avec le rôle superadmin."""
    return bool(user and user.get("role") == ROLE_SUPERADMIN)


def require_superadmin(request: Request) -> dict:
    user = get_current_user(request)
    if not is_superadmin(user):
        raise HTTPException(status_code=403, detail="Accès réservé au super administrateur")
    return user


def is_admin(user: dict) -> bool:
    return user.get("role") in ROLES_ADMIN

def is_fabrication(user: dict) -> bool:
    return user["role"] == "fabrication"


# ─── Login ────────────────────────────────────────────────────────
def login_user(email: str, password: str) -> dict:
    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND actif=1",
            (email.strip().lower(),)
        ).fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    if not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    token = create_session(user["id"])
    return {"user": dict(user), "token": token}
