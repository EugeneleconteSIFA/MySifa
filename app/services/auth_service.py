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
    ROLES_ADMINISTRATION_ALL,
    ROLES_PRICING,
    ROLES_SETTINGS,
    ACCESS_OVERRIDABLE_APPS,
    ROLE_SUPERADMIN,
    ROLE_DIRECTION,
    ROLE_ADMINISTRATION,
    ROLE_EXPEDITION,
    ROLES_EXPE_WRITE,
    ASSIGNABLE_ROLES,
    default_app_access_for_role,
    LEVEL_ORDER,
    APPS_CATALOG,
)

# MyCalendrier — accès page (pas de rôle rh en base). Inclut le rôle legacy
# `administration` + les deux nouveaux rôles issus du split (v163).
CALENDRIER_PAGE_ROLES = frozenset({ROLE_SUPERADMIN, ROLE_DIRECTION} | ROLES_ADMINISTRATION_ALL)

# ─── Impersonation (superadmin uniquement) ────────────────────────
# Cookie posé par POST /api/impersonate, retiré par DELETE /api/impersonate.
# Contenu JSON : {"role": "<role>", "machine_id": <int|null>}
# Ne modifie JAMAIS user["role"] : les permissions passent par effective_role(user)
# ce qui laisse un chemin de sortie (is_superadmin lit toujours le rôle réel).
IMPERSONATE_COOKIE = "sifa_impersonate"


def _parse_impersonate_cookie(request: Request) -> Optional[dict]:
    """Retourne {'role': str, 'machine_id': int|None} ou None si absent/invalide."""
    raw = request.cookies.get(IMPERSONATE_COOKIE)
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    role = str(data.get("role") or "").strip()
    if role not in ASSIGNABLE_ROLES:
        return None
    mid = data.get("machine_id")
    try:
        mid_int = int(mid) if mid not in (None, "", 0) else None
    except (ValueError, TypeError):
        mid_int = None
    return {"role": role, "machine_id": mid_int}


def _apply_impersonation(request: Request, user: dict) -> dict:
    """Injecte les champs effectifs sur user. N'écrase pas user['role'].

    Champs ajoutés :
      - real_role, real_machine_id : rôle et machine réels (copie de sécurité).
      - effective_role, effective_machine_id : à utiliser pour les checks de permission.
      - is_impersonating : True si le superadmin joue actuellement un autre rôle.
    """
    user["real_role"] = user.get("role")
    user["real_machine_id"] = user.get("machine_id")
    user["effective_role"] = user.get("role")
    user["effective_machine_id"] = user.get("machine_id")
    user["is_impersonating"] = False
    if user.get("role") != ROLE_SUPERADMIN:
        return user
    imp = _parse_impersonate_cookie(request)
    if not imp:
        return user
    user["effective_role"] = imp["role"]
    user["effective_machine_id"] = imp["machine_id"]
    user["is_impersonating"] = True
    return user


def effective_role(user: dict) -> str:
    """Rôle à utiliser pour les checks de permission (impersonation-aware)."""
    if not user:
        return ""
    return user.get("effective_role") or user.get("role") or ""


def effective_machine_id(user: dict) -> Optional[int]:
    """Machine à utiliser pour les filtres (impersonation-aware)."""
    if not user:
        return None
    val = user.get("effective_machine_id")
    if val in (None, "", 0):
        val = user.get("machine_id")
    try:
        return int(val) if val not in (None, "", 0) else None
    except (ValueError, TypeError):
        return None


def is_real_superadmin(user: dict) -> bool:
    """Vrai superadmin (rôle en base), utile pour /api/impersonate."""
    return bool(user and (user.get("real_role") or user.get("role")) == ROLE_SUPERADMIN)


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
            """SELECT u.id, u.email, u.identifiant, u.nom, u.role, u.operateur_lie, u.machine_id, u.actif, u.access_overrides, u.nc_service_override
               FROM sessions s JOIN users u ON s.user_id=u.id
               WHERE s.token=? AND s.expires_at>? AND u.actif=1""",
            (token, now)
        ).fetchone()
    return dict(row) if row else None


def _coerce_access_override_dict(o: dict) -> dict:
    """Normalise les clés d'accès (devis → pricing, ancien MyDevis)."""
    out: dict = {}
    for k, v in o.items():
        if not isinstance(v, bool):
            continue
        key = "pricing" if k == "devis" else k
        if key in ACCESS_OVERRIDABLE_APPS:
            out[key] = v
    return out


def parse_access_overrides_raw(raw: Any) -> dict:
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return _coerce_access_override_dict(raw)
    try:
        o = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(o, dict):
        return {}
    return _coerce_access_override_dict(o)


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
    """Accès effectif à une application (inclut surcharges par utilisateur sauf Paramètres).

    Utilise effective_role : quand un superadmin joue un rôle simulé, l'accès reflète
    le rôle simulé. Paramètres reste réservé au superadmin réel (chemin de sortie).

    Depuis la migration 184, délégué à user_can(user, app, '_app', 'read') qui lit
    les tables role_access_defaults / user_access_overrides. Fallback sur l'ancien
    système (colonne users.access_overrides + default_app_access_for_role) si la
    nouvelle table est vide (transition douce).
    """
    if app == "settings":
        # /settings doit rester accessible au vrai superadmin même en impersonation
        # (sinon impossible de sortir depuis /settings).
        return (user.get("real_role") or user.get("role")) == ROLE_SUPERADMIN
    if app == "devis":
        app = "pricing"
    return user_can(user, app, "_app", "read")


# ─── Contrôle d'accès database-driven (migration 184) ─────────────
# Nouveau système : lecture des tables role_access_defaults + user_access_overrides.
# Priorité : user (app, module) → user (app, _app) → role (app, module) → role
# (app, _app) → fallback legacy default_app_access_for_role → 'none'.
# Cache par process d'une map par-utilisateur : rechargée à chaque request via
# _prime_access_map (attaché à user).

def _load_access_map(user_id: int, role: str) -> dict:
    """Charge la carte d'accès effective d'un utilisateur en un seul aller-retour DB.

    Retourne un dict indexé par tuple (app_id, module_id) → level, où les
    surcharges utilisateur priment sur les défauts de rôle.
    """
    out: dict = {}
    try:
        with get_db() as conn:
            for row in conn.execute(
                "SELECT app_id, module_id, level FROM role_access_defaults WHERE role=?",
                (role,),
            ).fetchall():
                out[(row["app_id"], row["module_id"])] = row["level"]
            for row in conn.execute(
                "SELECT app_id, module_id, level FROM user_access_overrides WHERE user_id=?",
                (user_id,),
            ).fetchall():
                out[(row["app_id"], row["module_id"])] = row["level"]
    except Exception:
        # Tables absentes (dev sans migration jouée) : on retombe sur legacy.
        return out
    return out


def _prime_access_map(user: dict) -> dict:
    """Attache/renvoie user['_access_map'] en le calculant à la demande."""
    if not user:
        return {}
    m = user.get("_access_map")
    if m is not None:
        return m
    role = effective_role(user)
    m = _load_access_map(user["id"], role)
    user["_access_map"] = m
    return m


def user_access_level(user: dict, app: str, module: str = "_app") -> str:
    """Niveau effectif (none/read/write/admin) pour (app, module).

    - Superadmin : 'admin' partout sauf en impersonation (rôle simulé alors).
    - Paramètres : 'admin' pour le superadmin réel, 'none' sinon.
    - Fallback legacy : si la nouvelle table est vide, retombe sur
      default_app_access_for_role (bool → 'write' / 'none').
    """
    if not user:
        return "none"
    if app == "settings":
        return "admin" if (user.get("real_role") or user.get("role")) == ROLE_SUPERADMIN else "none"
    if app == "devis":
        app = "pricing"
    role = effective_role(user)
    if role == ROLE_SUPERADMIN:
        return "admin"
    m = _prime_access_map(user)
    # Ordre de résolution : (app, module) → (app, _app)
    if (app, module) in m:
        return m[(app, module)]
    if module != "_app" and (app, "_app") in m:
        return m[(app, "_app")]
    # Fallback legacy : ancienne colonne users.access_overrides + role defaults.
    try:
        legacy = merged_app_access(role, user.get("access_overrides"))
        return "write" if legacy.get(app) else "none"
    except Exception:
        return "none"


def user_can(user: dict, app: str, module: str = "_app", min_level: str = "read") -> bool:
    """True si user a au moins `min_level` sur (app, module). Base des contrôles d'accès."""
    if not user:
        return False
    lvl = user_access_level(user, app, module)
    return LEVEL_ORDER.get(lvl, 0) >= LEVEL_ORDER.get(min_level, 1)


def build_user_access_map(user: dict) -> dict:
    """Sérialisation pour /api/auth/me : {app_id: {module_id: level}}.

    Utilisé par le front pour cacher/griser les onglets et boutons.
    """
    out: dict = {}
    for app in APPS_CATALOG:
        app_id = app["id"]
        out[app_id] = {"_app": user_access_level(user, app_id, "_app")}
        for m in app.get("modules", []):
            out[app_id][m["id"]] = user_access_level(user, app_id, m["id"])
    return out


def user_can_write_expe(user: dict) -> bool:
    """MyExpé — écriture (départs, transporteurs). Logistique et commercial : lecture seule."""
    return effective_role(user) in ROLES_EXPE_WRITE


# ─── Résolution utilisateur ───────────────────────────────────────
def get_optional_user(request: Request) -> Optional[dict]:
    """Session valide ou None — sans lever d'exception (pour /api/auth/me)."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    user = get_user_by_token(token)
    if not user:
        return None
    return _apply_impersonation(request, user)


def get_current_user(request: Request) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Non authentifié")
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expirée ou invalide")
    return _apply_impersonation(request, user)

def require_admin(request: Request) -> dict:
    """Exige direction, administration ou super admin (rôle effectif)."""
    user = get_current_user(request)
    if effective_role(user) not in ROLES_ADMIN:
        raise HTTPException(status_code=403, detail="Accès réservé à l'administration")
    return user


def is_superadmin(user: dict) -> bool:
    """Super admin (rôle effectif — un superadmin qui joue un rôle simulé retourne False)."""
    return bool(user and effective_role(user) == ROLE_SUPERADMIN)


def require_superadmin(request: Request) -> dict:
    """Superadmin réel — insensible à l'impersonation (pour /api/impersonate)."""
    user = get_current_user(request)
    if not is_real_superadmin(user):
        raise HTTPException(status_code=403, detail="Accès réservé au super administrateur")
    return user


def can_access_settings(user: dict) -> bool:
    """Accès à l'application Paramètres — piloté par ROLES_SETTINGS (config.py)."""
    return bool(user and effective_role(user) in ROLES_SETTINGS)


def require_settings(request: Request) -> dict:
    """Exige un rôle autorisé pour l'application Paramètres (ROLES_SETTINGS)."""
    user = get_current_user(request)
    if not can_access_settings(user):
        raise HTTPException(status_code=403, detail="Accès réservé à l'administration des paramètres")
    return user


def can_access_calendrier(user: dict) -> bool:
    """MyCalendrier : superadmin, direction, administration."""
    return bool(user and effective_role(user) in CALENDRIER_PAGE_ROLES)


def require_calendrier(request: Request) -> dict:
    user = get_current_user(request)
    if not can_access_calendrier(user):
        raise HTTPException(status_code=403, detail="Accès non autorisé à MyCalendrier")
    return user


def is_admin(user: dict) -> bool:
    return effective_role(user) in ROLES_ADMIN

def is_commercial(user: dict) -> bool:
    return effective_role(user) == "commercial"

def can_view_all_prod(user: dict) -> bool:
    """Vue globale MyProd : toutes machines et opérateurs (lecture seule hors admin)."""
    return (
        is_admin(user)
        or is_commercial(user)
        or effective_role(user) == ROLE_EXPEDITION
    )

def is_fabrication(user: dict) -> bool:
    return effective_role(user) == "fabrication"


# ─── Login ────────────────────────────────────────────────────────
def login_user(login: str, password: str) -> dict:
    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE (email=? OR identifiant=?) AND actif=1",
            (str(login or "").strip().lower(), str(login or "").strip().lower()),
        ).fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="Identifiant/email ou mot de passe incorrect")
    if not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Identifiant/email ou mot de passe incorrect")
    token = create_session(user["id"])
    return {"user": dict(user), "token": token}
