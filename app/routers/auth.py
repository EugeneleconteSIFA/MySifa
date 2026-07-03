"""SIFA — Auth v0.8 — profil utilisateur + fiche admin"""
import json
import re
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse, Response as PlainResponse

from config import BASE_DIR, UPLOADS_ROOT
from database import get_db
from services.audit_service import log_action
from services.auth_service import (
    login_user,
    delete_session,
    get_current_user,
    get_optional_user,
    hash_password,
    verify_password,
    merged_app_access,
    parse_access_overrides_raw,
    require_superadmin,
    is_real_superadmin,
    IMPERSONATE_COOKIE,
)
from config import (
    ACCESS_OVERRIDABLE_APPS,
    ASSIGNABLE_ROLES,
    COOKIE_NAME,
    ROLE_SUPERADMIN,
    SESSION_HOURS,
    SUPERADMIN_EMAIL,
    ENV_NAME,
)

router = APIRouter()

# Identifiants des tuiles portail (ordre personnalisable, sauvegardé par utilisateur).
_PORTAL_TILE_IDS = frozenset(
    {
        "fabrication",
        "prod",
        "stock",
        "print",
        "compta",
        "expe",
        "planning_rh",
        "pricing",
        "com_expe",
        "com_devis",
    }
)


def _portal_order_list_from_db(val) -> List[str]:
    if not val:
        return []
    try:
        arr = json.loads(val) if isinstance(val, str) else val
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(arr, list):
        return []
    out: List[str] = []
    seen: set = set()
    for x in arr:
        if isinstance(x, str):
            tid = x.strip()
            if tid == "devis":
                tid = "pricing"
            if tid in _PORTAL_TILE_IDS and tid not in seen:
                out.append(tid)
                seen.add(tid)
    return out


def _normalize_portal_order_for_db(raw) -> Optional[str]:
    """Valide et compacte la liste d'ids ; None si vide ou invalide."""
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None
    if not isinstance(raw, list):
        return None
    out: List[str] = []
    seen: set = set()
    for x in raw:
        if not isinstance(x, str):
            continue
        tid = x.strip()
        if tid in _PORTAL_TILE_IDS and tid not in seen:
            out.append(tid)
            seen.add(tid)
    if not out:
        return None
    return json.dumps(out, separators=(",", ":"))


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
        key = "pricing" if k == "devis" else k
        if key not in ACCESS_OVERRIDABLE_APPS:
            continue
        if not isinstance(v, bool):
            raise HTTPException(status_code=400, detail=f"Valeur booléenne attendue pour {k}")
        clean[key] = v
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
            "adresse": u_pub.get("adresse", ""),
            "date_naissance": u_pub.get("date_naissance", ""),
            "avatar_url": u_pub.get("avatar_url") or "",
            "app_access": u_pub.get("app_access", {}),
        },
    })
    response.set_cookie(
        key=COOKIE_NAME, value=token, httponly=True,
        samesite="lax", secure=False, max_age=SESSION_HOURS * 3600,
    )
    client_ip = request.client.host if request.client else None
    log_action(
        user=u_pub,
        action="LOGIN",
        module="auth",
        objet=f"Connexion · {u_pub.get('email', '')}",
        ip=client_ip,
    )
    return response


# ─── Logout ───────────────────────────────────────────────────────
@router.post("/api/auth/logout")
def logout(request: Request, response: Response):
    user = get_optional_user(request)
    token = request.cookies.get(COOKIE_NAME)
    if token:
        delete_session(token)
    response.delete_cookie(COOKIE_NAME)
    if user:
        client_ip = request.client.host if request.client else None
        log_action(
            user=user,
            action="LOGOUT",
            module="auth",
            objet=f"Déconnexion · {user.get('email', '')}",
            ip=client_ip,
        )
    return {"success": True}


# ─── Portail — recherche Google ─────────────────────────────────────
@router.post("/api/portal/google-search")
async def portal_google_search(request: Request):
    """Journalise une recherche Google depuis le portail d'accueil (audit_logs)."""
    user = get_current_user(request)
    body = await request.json()
    q = str(body.get("q") or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Requête vide")
    if len(q) > 200:
        q = q[:200]
    client_ip = request.client.host if request.client else None
    log_action(
        user=user,
        action="SEARCH",
        module="portal",
        objet=f"Recherche Google · {q}",
        detail={"q": q},
        ip=client_ip,
    )
    return {"success": True}


def _avatar_file_from_url(url: str) -> Optional[Path]:
    if not url or not isinstance(url, str):
        return None
    rel = url.strip().lstrip("/")
    if rel.startswith("..") or rel.startswith("/"):
        return None
    if not rel.startswith("uploads/avatars/"):
        return None
    # rel = "uploads/avatars/<file>" ; UPLOADS_ROOT pointe déjà sur le dossier "uploads".
    p = (Path(UPLOADS_ROOT) / rel[len("uploads/"):]).resolve()
    try:
        p.relative_to((Path(UPLOADS_ROOT) / "avatars").resolve())
    except ValueError:
        return None
    return p


def _delete_avatar_file(url: Optional[str]) -> None:
    if not url:
        return
    old_p = _avatar_file_from_url(str(url))
    if old_p and old_p.is_file():
        try:
            old_p.unlink()
        except OSError:
            pass


# ─── Profil courant ───────────────────────────────────────────────
@router.get("/api/auth/me")
def me(request: Request):
    """200 + JSON utilisateur, ou 200 + `null` si pas de session (pas de 401 : évite le bruit console / DevTools)."""
    user = get_optional_user(request)
    if not user:
        return PlainResponse(content=b"null", media_type="application/json")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id,email,identifiant,nom,role,operateur_lie,machine_id,telephone,adresse,date_naissance,avatar_url,access_overrides,portal_apps_order,theme_prefs,humeur_active,humeur_valeur,humeur_date FROM users WHERE id=?",
            (user["id"],)
        ).fetchone()
    if not row:
        return PlainResponse(content=b"null", media_type="application/json")
    d = dict(row)
    ov_raw = d.get("access_overrides")
    d["access_overrides"] = parse_access_overrides_raw(ov_raw)
    # get_current_user a déjà posé effective_role / effective_machine_id / is_impersonating.
    real_role = d.get("role")
    real_machine_id = d.get("machine_id")
    eff_role = user.get("effective_role") or real_role
    eff_machine_id = user.get("effective_machine_id")
    is_imp = bool(user.get("is_impersonating"))
    # En impersonation on remplace role et machine_id : toutes les logiques front qui lisent
    # S.user.role héritent naturellement du rôle simulé (rendu contextualisé).
    if is_imp:
        d["role"] = eff_role
        d["machine_id"] = eff_machine_id
    d["real_role"] = real_role
    d["real_machine_id"] = real_machine_id
    d["effective_role"] = eff_role
    d["effective_machine_id"] = eff_machine_id
    d["is_impersonating"] = is_imp
    # app_access suit le rôle effectif : simulation fidèle (le portail et la sidebar affichent
    # exactement ce qu'un vrai opérateur du rôle simulé verrait). Le bouton "Revenir superadmin"
    # reste toujours visible dans le bandeau : chemin de sortie garanti.
    d["app_access"] = merged_app_access(eff_role, ov_raw)
    # real_app_access exposé au cas où le front en a besoin (bandeau, debug, etc.).
    d["real_app_access"] = merged_app_access(real_role, ov_raw)
    d["portal_apps_order"] = _portal_order_list_from_db(d.get("portal_apps_order"))
    return d


# ─── Impersonation (superadmin uniquement) ─────────────────────────
@router.post("/api/impersonate")
async def start_impersonation(request: Request, response: Response):
    """Le superadmin passe en mode 'simulation d'un service'.

    Body : {"role": "fabrication|logistique|...", "machine_id": <int|null>}
    Superadmin réel uniquement (l'endpoint reste accessible même déjà en simulation).
    """
    user = get_current_user(request)
    if not is_real_superadmin(user):
        raise HTTPException(status_code=403, detail="Réservé au super administrateur")
    body = await request.json()
    role = str(body.get("role") or "").strip()
    if role not in ASSIGNABLE_ROLES:
        raise HTTPException(status_code=400, detail="Rôle invalide")
    raw_mid = body.get("machine_id")
    machine_id: Optional[int] = None
    if raw_mid not in (None, "", 0):
        try:
            machine_id = int(raw_mid)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="machine_id invalide")
    # Vérifie que la machine existe (si fournie)
    if machine_id is not None:
        with get_db() as conn:
            m = conn.execute("SELECT id FROM machines WHERE id=? AND actif=1", (machine_id,)).fetchone()
            if not m:
                raise HTTPException(status_code=400, detail="Machine introuvable")
    payload = json.dumps({"role": role, "machine_id": machine_id})
    response.set_cookie(
        key=IMPERSONATE_COOKIE,
        value=payload,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=SESSION_HOURS * 3600,
    )
    return {
        "success": True,
        "effective_role": role,
        "effective_machine_id": machine_id,
        "is_impersonating": True,
        "env": ENV_NAME,
    }


@router.delete("/api/impersonate")
def stop_impersonation(request: Request, response: Response):
    """Retour au rôle réel. Accessible au vrai superadmin uniquement."""
    user = get_current_user(request)
    if not is_real_superadmin(user):
        raise HTTPException(status_code=403, detail="Réservé au super administrateur")
    response.delete_cookie(IMPERSONATE_COOKIE)
    return {"success": True, "is_impersonating": False, "env": ENV_NAME}


@router.put("/api/auth/me")
async def update_me(request: Request):
    """L'utilisateur met à jour son propre profil."""
    user = get_current_user(request)
    body = await request.json()

    with get_db() as conn:
        ex = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        exd = dict(ex)

        nom = str(body.get("nom") or exd.get("nom") or "").strip()
        email = str(body.get("email") or exd.get("email") or "").strip().lower()
        telephone = str(body.get("telephone") or exd.get("telephone") or "").strip()
        adresse = str(body.get("adresse") if ("adresse" in body) else (exd.get("adresse") or "")).strip()
        date_naissance = str(body.get("date_naissance") if ("date_naissance" in body) else (exd.get("date_naissance") or "")).strip()
        pwd_hash = exd["password_hash"]

        if "password" in body and body["password"]:
            current_pwd = str(body.get("current_password") or "").strip()
            if not current_pwd:
                raise HTTPException(status_code=400, detail="Mot de passe actuel requis")
            if not verify_password(current_pwd, exd.get("password_hash") or ""):
                raise HTTPException(status_code=403, detail="Mot de passe actuel invalide")
            if len(body["password"]) < 8:
                raise HTTPException(status_code=400, detail="Mot de passe minimum 8 caractères")
            # Vérifier confirmation
            if body.get("password_confirm") and body["password"] != body["password_confirm"]:
                raise HTTPException(status_code=400, detail="Les mots de passe ne correspondent pas")
            pwd_hash = hash_password(body["password"])

        # Vérifier unicité email si changé
        if email != str(exd.get("email") or "").strip().lower():
            existing = conn.execute(
                "SELECT id FROM users WHERE email=? AND id!=?", (email, user["id"])
            ).fetchone()
            if existing:
                raise HTTPException(status_code=409, detail="Email déjà utilisé")

        portal_val = exd.get("portal_apps_order")
        if "portal_apps_order" in body:
            portal_val = _normalize_portal_order_for_db(body.get("portal_apps_order"))

        theme_prefs_val = exd.get("theme_prefs")
        if "theme_prefs" in body:
            import json as _json
            tp = body.get("theme_prefs")
            if tp is None:
                theme_prefs_val = None
            elif isinstance(tp, dict):
                theme_prefs_val = _json.dumps(tp, ensure_ascii=False)
            else:
                theme_prefs_val = str(tp)

        conn.execute(
            "UPDATE users SET nom=?,email=?,telephone=?,adresse=?,date_naissance=?,password_hash=?,portal_apps_order=?,theme_prefs=? WHERE id=?",
            (nom, email, telephone, adresse or None, date_naissance or None, pwd_hash, portal_val, theme_prefs_val, user["id"]),
        )
        conn.commit()

    return {"success": True}


@router.post("/api/auth/me/avatar")
async def upload_my_avatar(request: Request, photo: UploadFile = File(...)):
    """Upload de la photo de profil de l'utilisateur connecté."""
    user = get_current_user(request)
    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if (photo.content_type or "") not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Format image non accepté (jpg, png, webp, gif).",
        )
    ext_map = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}
    ext = ext_map.get(photo.content_type or "", "jpg")
    dest_dir = Path(UPLOADS_ROOT) / "avatars"
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"user_{user['id']}_{uuid.uuid4().hex[:8]}.{ext}"
    dest = dest_dir / filename
    content = await photo.read()
    if len(content) > 4 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 4 Mo).")
    with open(dest, "wb") as f:
        f.write(content)
    url = f"/uploads/avatars/{filename}"
    with get_db() as conn:
        ex = conn.execute("SELECT avatar_url FROM users WHERE id=?", (user["id"],)).fetchone()
        if not ex:
            try:
                dest.unlink(missing_ok=True)
            except OSError:
                pass
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        _delete_avatar_file(ex["avatar_url"])
        conn.execute("UPDATE users SET avatar_url=? WHERE id=?", (url, user["id"]))
        conn.commit()
    client_ip = request.client.host if request.client else None
    log_action(
        user=user,
        action="UPDATE",
        module="auth",
        objet="Photo de profil",
        detail={"avatar": True},
        ip=client_ip,
    )
    return {"url": url}


@router.delete("/api/auth/me/avatar")
def delete_my_avatar(request: Request):
    """Supprime la photo de profil de l'utilisateur connecté."""
    user = get_current_user(request)
    with get_db() as conn:
        ex = conn.execute("SELECT avatar_url FROM users WHERE id=?", (user["id"],)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        _delete_avatar_file(ex["avatar_url"])
        conn.execute("UPDATE users SET avatar_url=NULL WHERE id=?", (user["id"],))
        conn.commit()
    client_ip = request.client.host if request.client else None
    log_action(
        user=user,
        action="UPDATE",
        module="auth",
        objet="Photo de profil",
        detail={"avatar": False},
        ip=client_ip,
    )
    return {"ok": True}


# ─── Humeur utilisateur ───────────────────────────────────────────
HUMEURS_VALIDES = {"😊", "😩", "😢", "🤒", "😐", "😠", "🥵", "🥶", "🤮", "🥱"}

@router.put("/api/auth/me/humeur")
async def update_humeur(request: Request):
    """Met à jour l'humeur du jour et/ou le toggle actif/inactif."""
    user = get_current_user(request)
    body = await request.json()
    today = datetime.now().strftime("%Y-%m-%d")

    with get_db() as conn:
        ex = conn.execute("SELECT humeur_active,humeur_valeur,humeur_date FROM users WHERE id=?", (user["id"],)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

        humeur_active = ex["humeur_active"] if ex["humeur_active"] is not None else 0
        humeur_valeur = ex["humeur_valeur"]
        humeur_date = ex["humeur_date"]

        if "humeur_active" in body:
            humeur_active = 1 if body["humeur_active"] else 0

        if "humeur_valeur" in body:
            val = body["humeur_valeur"]
            if val is None or val == "":
                humeur_valeur = None
                humeur_date = None
            elif val in HUMEURS_VALIDES:
                humeur_valeur = val
                humeur_date = today
            else:
                raise HTTPException(status_code=400, detail="Humeur invalide")

        conn.execute(
            "UPDATE users SET humeur_active=?,humeur_valeur=?,humeur_date=? WHERE id=?",
            (humeur_active, humeur_valeur, humeur_date, user["id"]),
        )
        conn.commit()

    return {"ok": True, "humeur_active": humeur_active, "humeur_valeur": humeur_valeur, "humeur_date": humeur_date}


# ─── Gestion utilisateurs (super admin uniquement) ──────────────
@router.get("/api/users")
def list_users(request: Request):
    require_superadmin(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT u.id,u.email,u.identifiant,u.nom,u.role,u.operateur_lie,u.actif,u.telephone,u.adresse,u.date_naissance,u.machine_id,
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
            """SELECT u.id,u.email,u.identifiant,u.nom,u.role,u.operateur_lie,u.actif,u.telephone,u.adresse,u.date_naissance,u.machine_id,
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
    actor = require_superadmin(request)
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

    log_action(
        user=actor,
        action="CREATE",
        module="settings",
        objet=f"Utilisateur {nom} [{role}]",
        detail={"email": email},
        ip=request.client.host if request.client else None,
    )
    return {"success": True}


@router.put("/api/users/{user_id}")
async def update_user(user_id: int, request: Request):
    actor = require_superadmin(request)
    body = await request.json()

    with get_db() as conn:
        ex = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        exd = dict(ex)

        nom      = body.get("nom")           or exd["nom"]
        role_req = body.get("role")          or exd["role"]
        op       = body.get("operateur_lie", exd["operateur_lie"])
        actif    = body.get("actif",         exd["actif"])
        tel      = body.get("telephone")     or (exd.get("telephone") or "")
        adresse  = str(body.get("adresse") if ("adresse" in body) else (exd.get("adresse") or "")).strip()
        date_naissance = str(body.get("date_naissance") if ("date_naissance" in body) else (exd.get("date_naissance") or "")).strip()
        email    = (body.get("email") or exd["email"]).strip().lower()
        ident_in = (body.get("identifiant") if "identifiant" in body else exd.get("identifiant")) or ""
        ident_in = str(ident_in).strip().lower()
        pwd_hash = exd["password_hash"]
        # machine_id : None si la clé est présente et vide, sinon valeur existante
        if "machine_id" in body:
            raw_mid = body["machine_id"]
            machine_id = int(raw_mid) if raw_mid not in (None, "", 0, "0") else None
        else:
            machine_id = exd.get("machine_id")

        role_eff = _validate_user_role_write(
            target_email=email,
            target_role=role_req,
            existing_email=exd["email"],
            existing_role=exd["role"],
        )

        if "password" in body and body["password"]:
            if len(body["password"]) < 8:
                raise HTTPException(status_code=400, detail="Mot de passe minimum 8 caractères")
            pwd_hash = hash_password(body["password"])

        ao_sql: Optional[str]
        if "access_overrides" in body:
            ao_sql = _normalize_access_overrides_payload(body.get("access_overrides"))
        else:
            ao_sql = exd.get("access_overrides")

        # identifiant: générer si vide (ou si absent en base) à partir du nom, puis assurer unicité.
        if not ident_in:
            ident_in = _default_identifiant_from_nom(str(nom or ""))
        ident_sql = _ensure_unique_identifiant(conn, ident_in, exclude_user_id=user_id) if ident_in else ""

        conn.execute(
            """UPDATE users SET nom=?,email=?,identifiant=?,role=?,operateur_lie=?,actif=?,telephone=?,
               adresse=?,date_naissance=?,password_hash=?,access_overrides=?,machine_id=? WHERE id=?""",
            (nom, email, ident_sql or None, role_eff, op, actif, tel,
             (adresse or None), (date_naissance or None),
             pwd_hash, ao_sql, machine_id, user_id),
        )
        conn.commit()

    log_action(
        user=actor,
        action="UPDATE",
        module="settings",
        objet=f"Utilisateur {nom} [{role_eff}]",
        detail={"user_id": user_id},
        ip=request.client.host if request.client else None,
    )
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
    nom_audit = ""
    role_audit = ""
    with get_db() as conn:
        ex = conn.execute("SELECT email, nom, role FROM users WHERE id=?", (user_id,)).fetchone()
        if ex and _is_designated_superadmin_row(ex["email"], ex["role"]):
            raise HTTPException(status_code=400, detail="Impossible de désactiver le compte super administrateur")
        if ex:
            nom_audit = ex["nom"] or ""
            role_audit = ex["role"] or ""
        conn.execute("UPDATE users SET actif=0 WHERE id=?", (user_id,))
        conn.commit()
    log_action(
        user=actor,
        action="DELETE",
        module="settings",
        objet=f"Utilisateur {nom_audit} [{role_audit}]",
        detail={"user_id": user_id},
        ip=request.client.host if request.client else None,
    )
    return {"success": True}
