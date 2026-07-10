"""
Kernse-admin — routes d'authentification superadmin plateforme.

Endpoints :
    POST /auth/login              email + password → cookie session
    POST /auth/logout              détruit la session courante
    GET  /auth/2fa/setup           génère un secret TOTP + QR (si 2FA off)
    POST /auth/2fa/enable          active la 2FA (secret + code)
    POST /auth/2fa/verify          valide le code TOTP pour la session
    POST /auth/2fa/disable         désactive la 2FA (mot de passe requis)

Bootstrap : si aucun superadmin n'existe en DB au boot, on en crée un
avec KERNSE_BOOTSTRAP_EMAIL + KERNSE_BOOTSTRAP_PASSWORD. Après quoi
l'admin change son mot de passe et active la 2FA.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from kernse.admin.config import COOKIE_NAME, IS_STAGING, SESSION_HOURS
from kernse.shared.auth.dependency import (
    ADMIN_COOKIE_NAME,
    SuperadminContext,
    require_superadmin,
    require_superadmin_no_2fa,
)
from kernse.shared.auth.password import hash_password, verify_password
from kernse.shared.auth.session import (
    create_session,
    destroy_session,
    mark_2fa_ok,
)
from kernse.shared.auth.totp import generate_secret, otpauth_uri, verify_code
from kernse.shared.db.database import log_audit, platform_db
from kernse.shared.db.schema import utcnow_iso


router = APIRouter(tags=["auth"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _set_cookie(response, session_id: str) -> None:
    # Cookie Secure en prod (HTTPS), Lax pour la navigation classique.
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=session_id,
        max_age=SESSION_HOURS * 3600,
        httponly=True,
        secure=not IS_STAGING is False,  # Toujours secure — accédé via HTTPS
        samesite="lax",
        path="/",
    )


# ─── Login ───────────────────────────────────────────────────────────────
@router.post("/auth/login", response_model=None)
def login(
    request: Request,
    email: str = Form(min_length=3, max_length=200),
    password: str = Form(min_length=1, max_length=200),
) -> RedirectResponse:
    email_lc = email.strip().lower()

    with platform_db() as conn:
        row = conn.execute(
            "SELECT email, password_hash, totp_secret FROM superadmins WHERE email = ? LIMIT 1",
            (email_lc,),
        ).fetchone()

        # Message générique : ne révèle pas si l'email existe ou non (règle
        # de sécurité racine).
        if row is None or not verify_password(password, row["password_hash"]):
            log_audit(
                conn,
                actor_email=email_lc or "unknown",
                actor_ip=_client_ip(request),
                action="login_failed",
                entity_type="superadmin",
                entity_id=email_lc,
            )
            raise HTTPException(status_code=401, detail="Identifiants invalides.")

        has_totp = bool(row["totp_secret"])
        session_id = create_session(
            conn,
            email=email_lc,
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            hours=SESSION_HOURS,
            twofa_ok=not has_totp,  # si pas de 2FA, session pleine directement
        )
        conn.execute(
            "UPDATE superadmins SET last_login_at = ? WHERE email = ?",
            (utcnow_iso(), email_lc),
        )
        log_audit(
            conn,
            actor_email=email_lc,
            actor_ip=_client_ip(request),
            action="login_success",
            entity_type="superadmin",
            entity_id=email_lc,
            after={"twofa_required": has_totp},
        )

    # Redirection : /admin si 2FA OK, sinon /2fa/verify
    target = "/admin" if not has_totp else "/2fa/verify"
    response = RedirectResponse(target, status_code=303)
    _set_cookie(response, session_id)
    return response


# ─── Logout ──────────────────────────────────────────────────────────────
@router.post("/auth/logout")
def logout(
    request: Request,
    ctx: SuperadminContext = Depends(require_superadmin_no_2fa),
) -> RedirectResponse:
    with platform_db() as conn:
        destroy_session(conn, ctx.session_id)
        log_audit(
            conn,
            actor_email=ctx.email,
            actor_ip=_client_ip(request),
            action="logout",
            entity_type="superadmin",
            entity_id=ctx.email,
        )
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(ADMIN_COOKIE_NAME, path="/")
    return response


# ─── 2FA — setup (génère un secret + URI QR) ─────────────────────────────
@router.get("/auth/2fa/setup")
def totp_setup(
    request: Request,
    ctx: SuperadminContext = Depends(require_superadmin_no_2fa),
) -> JSONResponse:
    """Génère un secret TOTP pour l'utilisateur, à confirmer avec un code.

    Le secret n'est PAS persisté ici — il n'est activé qu'après un code
    valide via `/auth/2fa/enable`.
    """
    secret = generate_secret()
    uri = otpauth_uri(secret_b32=secret, email=ctx.email)
    return JSONResponse({"secret": secret, "otpauth_uri": uri, "email": ctx.email})


@router.post("/auth/2fa/enable")
def totp_enable(
    request: Request,
    secret: str = Form(min_length=16, max_length=200),
    code: str = Form(min_length=6, max_length=6),
    ctx: SuperadminContext = Depends(require_superadmin_no_2fa),
) -> JSONResponse:
    if not verify_code(secret, code):
        raise HTTPException(status_code=400, detail="Code TOTP invalide.")
    with platform_db() as conn:
        conn.execute(
            "UPDATE superadmins SET totp_secret = ? WHERE email = ?",
            (secret, ctx.email),
        )
        mark_2fa_ok(conn, ctx.session_id)
        log_audit(
            conn,
            actor_email=ctx.email,
            actor_ip=_client_ip(request),
            action="2fa_enabled",
            entity_type="superadmin",
            entity_id=ctx.email,
        )
    return JSONResponse({"ok": True})


@router.post("/auth/2fa/verify")
def totp_verify(
    request: Request,
    code: str = Form(min_length=6, max_length=6),
    ctx: SuperadminContext = Depends(require_superadmin_no_2fa),
) -> RedirectResponse:
    with platform_db() as conn:
        row = conn.execute(
            "SELECT totp_secret FROM superadmins WHERE email = ? LIMIT 1",
            (ctx.email,),
        ).fetchone()
        if not row or not row["totp_secret"]:
            raise HTTPException(status_code=400, detail="2FA non configurée pour cet utilisateur.")
        if not verify_code(row["totp_secret"], code):
            log_audit(
                conn,
                actor_email=ctx.email,
                actor_ip=_client_ip(request),
                action="2fa_verify_failed",
                entity_type="superadmin",
                entity_id=ctx.email,
            )
            raise HTTPException(status_code=401, detail="Code TOTP invalide.")
        mark_2fa_ok(conn, ctx.session_id)
        log_audit(
            conn,
            actor_email=ctx.email,
            actor_ip=_client_ip(request),
            action="2fa_verify_ok",
            entity_type="superadmin",
            entity_id=ctx.email,
        )
    return RedirectResponse("/admin", status_code=303)


@router.post("/auth/2fa/disable")
def totp_disable(
    request: Request,
    password: str = Form(min_length=1, max_length=200),
    ctx: SuperadminContext = Depends(require_superadmin),
) -> JSONResponse:
    """Désactivation 2FA — nécessite le mot de passe pour prévenir un
    session-hijack qui l'aurait activée."""
    with platform_db() as conn:
        row = conn.execute(
            "SELECT password_hash FROM superadmins WHERE email = ? LIMIT 1",
            (ctx.email,),
        ).fetchone()
        if not row or not verify_password(password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Mot de passe invalide.")
        conn.execute(
            "UPDATE superadmins SET totp_secret = NULL WHERE email = ?",
            (ctx.email,),
        )
        log_audit(
            conn,
            actor_email=ctx.email,
            actor_ip=_client_ip(request),
            action="2fa_disabled",
            entity_type="superadmin",
            entity_id=ctx.email,
        )
    return JSONResponse({"ok": True})


# ─── Bootstrap (appelé au boot de l'app) ─────────────────────────────────
def bootstrap_superadmin_if_needed() -> None:
    """Crée le premier superadmin depuis les variables d'env si aucun
    n'existe. À appeler dans le startup de kernse-admin.

    Variables lues :
        KERNSE_BOOTSTRAP_EMAIL     (obligatoire pour bootstrap)
        KERNSE_BOOTSTRAP_PASSWORD  (obligatoire pour bootstrap)

    Si les variables ne sont pas définies ET qu'aucun superadmin
    n'existe : on émet un avertissement clair mais on ne casse pas le
    boot (la console renverra 401 tant qu'aucun compte n'est créé).
    """
    with platform_db() as conn:
        existing = conn.execute("SELECT COUNT(*) AS c FROM superadmins").fetchone()["c"]
        if existing > 0:
            return

        email = (os.getenv("KERNSE_BOOTSTRAP_EMAIL") or "").strip().lower()
        password = os.getenv("KERNSE_BOOTSTRAP_PASSWORD") or ""

        if not email or not password:
            print(
                "[kernse-admin] AUCUN SUPERADMIN EN DB et pas de bootstrap "
                "(KERNSE_BOOTSTRAP_EMAIL + KERNSE_BOOTSTRAP_PASSWORD). "
                "La console renverra 401 tant qu'un compte n'est pas créé.",
                flush=True,
            )
            return

        try:
            pwd_hash = hash_password(password)
        except ValueError as exc:
            print(
                f"[kernse-admin] Bootstrap ignoré : {exc}. Utilisez un mot de "
                "passe >= 12 caractères.",
                flush=True,
            )
            return

        conn.execute(
            "INSERT INTO superadmins(email, password_hash, created_at) VALUES(?, ?, ?)",
            (email, pwd_hash, utcnow_iso()),
        )
        log_audit(
            conn,
            actor_email="system:bootstrap",
            action="superadmin_bootstrap",
            entity_type="superadmin",
            entity_id=email,
            after={"email": email},
        )
        print(f"[kernse-admin] Superadmin bootstrap créé : {email}", flush=True)
