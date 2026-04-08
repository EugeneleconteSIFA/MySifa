"""Support — contact email (MySifa)."""

from email.message import EmailMessage
import smtplib
import traceback
import time
import json
import urllib.parse
import urllib.request
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from config import (
    SUPPORT_TO_EMAIL,
    SUPPORT_EMAIL_DEBUG,
    SUPPORT_EMAIL_PROVIDER,
    MS_TENANT_ID,
    MS_CLIENT_ID,
    MS_CLIENT_SECRET,
    MS_SENDER_UPN,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASS,
    SMTP_PORT,
    SMTP_TLS,
    SMTP_USER,
)
from services.auth_service import get_current_user


router = APIRouter()

_GRAPH_TOKEN = {"access_token": None, "expires_at": 0.0}


def _graph_get_token() -> str:
    if not MS_TENANT_ID or not MS_CLIENT_ID or not MS_CLIENT_SECRET:
        raise RuntimeError("Microsoft Graph non configuré (MS_TENANT_ID/MS_CLIENT_ID/MS_CLIENT_SECRET)")
    now = time.time()
    if _GRAPH_TOKEN["access_token"] and float(_GRAPH_TOKEN["expires_at"] or 0) - now > 60:
        return str(_GRAPH_TOKEN["access_token"])

    url = f"https://login.microsoftonline.com/{MS_TENANT_ID}/oauth2/v2.0/token"
    data = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": MS_CLIENT_ID,
            "client_secret": MS_CLIENT_SECRET,
            "scope": "https://graph.microsoft.com/.default",
        }
    ).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode("utf-8", errors="replace")
    except Exception:
        raise RuntimeError("Token Graph impossible (réseau/identifiants)")

    try:
        j = json.loads(raw)
    except Exception:
        raise RuntimeError("Token Graph invalide")
    tok = j.get("access_token")
    exp = j.get("expires_in", 3600)
    if not tok:
        raise RuntimeError("Token Graph manquant")
    _GRAPH_TOKEN["access_token"] = tok
    try:
        _GRAPH_TOKEN["expires_at"] = now + float(exp)
    except Exception:
        _GRAPH_TOKEN["expires_at"] = now + 3600.0
    return str(tok)


def _send_support_graph(*, subject: str, text: str, reply_to: Optional[str]) -> None:
    if not SUPPORT_TO_EMAIL:
        raise RuntimeError("SUPPORT_TO_EMAIL manquant")
    if not MS_SENDER_UPN:
        raise RuntimeError("Microsoft Graph non configuré (MS_SENDER_UPN)")
    token = _graph_get_token()

    url = f"https://graph.microsoft.com/v1.0/users/{urllib.parse.quote(MS_SENDER_UPN)}/sendMail"
    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": text},
            "toRecipients": [{"emailAddress": {"address": SUPPORT_TO_EMAIL}}],
        },
        "saveToSentItems": "true",
    }
    if reply_to:
        payload["message"]["replyTo"] = [{"emailAddress": {"address": reply_to}}]

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            # Graph sendMail returns 202 Accepted with empty body
            if getattr(r, "status", 202) not in (200, 201, 202):
                raise RuntimeError("Graph sendMail refusé")
    except Exception as e:
        # Ne pas divulguer de secrets dans l'erreur
        raise RuntimeError(f"Graph sendMail impossible ({type(e).__name__})")


def _send_support_email(*, subject: str, text: str, reply_to: Optional[str]) -> None:
    if not SUPPORT_TO_EMAIL:
        raise RuntimeError("SUPPORT_TO_EMAIL manquant")
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        raise RuntimeError("SMTP non configuré (SMTP_HOST/SMTP_USER/SMTP_PASS)")

    msg = EmailMessage()
    msg["To"] = SUPPORT_TO_EMAIL
    msg["From"] = SMTP_FROM or SMTP_USER
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(text)

    if SMTP_TLS:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
            s.ehlo()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)


@router.post("/api/support/contact")
async def contact_support(request: Request):
    """Envoie un email au support (auth requis)."""
    user = get_current_user(request)
    body = await request.json()

    name = (body.get("name") or user.get("nom") or "").strip()
    email = (body.get("email") or user.get("email") or "").strip().lower()
    subject = (body.get("subject") or "").strip() or "Demande support"
    message = (body.get("message") or "").strip()
    page = (body.get("page") or "").strip()

    if not message or len(message) < 5:
        raise HTTPException(status_code=400, detail="Message trop court")
    if len(message) > 4000:
        raise HTTPException(status_code=400, detail="Message trop long")
    if len(subject) > 140:
        raise HTTPException(status_code=400, detail="Objet trop long")

    who = f"{name} <{email}>" if name and email else (email or name or f"user_id={user.get('id')}")
    full_subject = f"[MySifa Support] {subject} — {who}"

    text = (
        f"Demande support MySifa\n"
        f"Utilisateur: {who}\n"
        f"Rôle: {user.get('role','')}\n"
        f"Page: {page}\n"
        f"\n"
        f"{message}\n"
    )

    try:
        provider = (SUPPORT_EMAIL_PROVIDER or "graph").strip().lower()
        if provider == "smtp":
            _send_support_email(subject=full_subject, text=text, reply_to=email or None)
        else:
            _send_support_graph(subject=full_subject, text=text, reply_to=email or None)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # Diagnostic côté serveur (sans exposer de secrets)
        print("[support] email send failed:", type(e).__name__)
        print(traceback.format_exc())
        if SUPPORT_EMAIL_DEBUG:
            msg = str(e) or ""
            if SMTP_PASS and SMTP_PASS in msg:
                msg = msg.replace(SMTP_PASS, "***")
            detail = f"Envoi email impossible: {type(e).__name__}"
            if msg:
                detail += f" — {msg[:240]}"
            raise HTTPException(status_code=500, detail=detail)
        raise HTTPException(status_code=500, detail="Envoi email impossible")

    return {"success": True}

