"""
Kernse — dépendance FastAPI `require_superadmin`.

Extrait le session_id du cookie, vérifie la session (existence + non
expirée + optionnellement 2FA validée), injecte l'email superadmin dans
la requête. Redirige vers /login si absent, vers /2fa/verify si 2FA
requise mais pas encore validée.
"""
from __future__ import annotations

from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse

from kernse.shared.auth.session import get_session
from kernse.shared.db.database import platform_db


ADMIN_COOKIE_NAME = "kernse_admin_sid"


class SuperadminContext:
    __slots__ = ("email", "session_id", "twofa_ok")

    def __init__(self, email: str, session_id: str, twofa_ok: bool):
        self.email = email
        self.session_id = session_id
        self.twofa_ok = twofa_ok


def _reject_html(target: str) -> RedirectResponse:
    return RedirectResponse(target, status_code=status.HTTP_302_FOUND)


def _reject_json(detail: str, code: int = 401) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


def _wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept and not request.url.path.startswith("/api/")


def require_superadmin_base(request: Request, *, need_2fa: bool) -> SuperadminContext:
    session_id = request.cookies.get(ADMIN_COOKIE_NAME, "")
    if not session_id:
        if _wants_html(request):
            raise _reject_html("/login")
        raise _reject_json("Non authentifié.", 401)

    with platform_db() as conn:
        session = get_session(conn, session_id)
        if session is None:
            if _wants_html(request):
                raise _reject_html("/login?expired=1")
            raise _reject_json("Session invalide ou expirée.", 401)

        email = session["email"]
        twofa_ok = bool(session["twofa_ok"])

        # Le superadmin a-t-il un secret TOTP configuré ?
        row = conn.execute(
            "SELECT totp_secret FROM superadmins WHERE email = ? LIMIT 1",
            (email,),
        ).fetchone()
        has_totp = bool(row and row["totp_secret"])

    if need_2fa and has_totp and not twofa_ok:
        if _wants_html(request):
            raise _reject_html("/2fa/verify")
        raise _reject_json("2FA requise.", 401)

    return SuperadminContext(email=email, session_id=session_id, twofa_ok=twofa_ok)


def require_superadmin(request: Request) -> SuperadminContext:
    """Dépendance standard : session valide + 2FA validée si configurée."""
    return require_superadmin_base(request, need_2fa=True)


def require_superadmin_no_2fa(request: Request) -> SuperadminContext:
    """Variante utilisée par la page de saisie du code 2FA : on veut la
    session mais pas encore le flag `twofa_ok`."""
    return require_superadmin_base(request, need_2fa=False)
