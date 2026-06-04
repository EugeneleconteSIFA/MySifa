"""MySifa — Notifications Web Push (VAPID).

Active les notifications lorsque l'app est installée en PWA (mobile ou desktop).

Variables d'environnement requises (à ajouter au .env du VPS) :
    VAPID_PUBLIC_KEY        — clé publique (base64url, sans préfixe)
    VAPID_PRIVATE_KEY       — clé privée (PEM ou base64url)
    VAPID_CLAIM_EMAIL       — mailto: pour les claims (ex. mailto:eleconte@sifa.pro)

Génération des clés (une seule fois) :
    python -m py_vapid

Endpoints :
    GET  /api/push/public-key      — clé publique pour PushManager.subscribe
    POST /api/push/subscribe       — enregistre l'abonnement de l'appareil courant
    POST /api/push/unsubscribe     — supprime un abonnement (par endpoint)
    GET  /api/push/status          — l'utilisateur a-t-il des abonnements actifs ?

Fonction utilitaire :
    send_push_to_user(user_id, title, body, url=None, tag=None)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request

from database import get_db
from services.auth_service import get_current_user


log = logging.getLogger("mysifa.push")

router = APIRouter(prefix="/api/push", tags=["push"])


def _vapid_public_key() -> str:
    return (os.getenv("VAPID_PUBLIC_KEY") or "").strip()


def _vapid_private_key() -> str:
    return (os.getenv("VAPID_PRIVATE_KEY") or "").strip()


def _vapid_claim_email() -> str:
    raw = (os.getenv("VAPID_CLAIM_EMAIL") or "").strip()
    if not raw:
        return "mailto:noreply@mysifa.fr"
    return raw if raw.startswith("mailto:") else f"mailto:{raw}"


def _push_configured() -> bool:
    return bool(_vapid_public_key() and _vapid_private_key())


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/public-key")
def public_key(request: Request):
    """Renvoie la clé VAPID publique pour PushManager.subscribe.

    Pas de 401 dur ici : la page profil peut détecter l'absence de configuration
    et afficher un message clair, sans casser le rendu.
    """
    get_current_user(request)
    key = _vapid_public_key()
    if not key:
        return {"key": "", "configured": False}
    return {"key": key, "configured": True}


@router.get("/status")
def push_status(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM push_subscriptions WHERE user_id=?",
            (int(user["id"]),),
        ).fetchone()
    return {
        "configured": _push_configured(),
        "subscriptions": int(row["n"] if row else 0),
    }


@router.post("/subscribe")
async def subscribe(request: Request):
    """Enregistre un abonnement Web Push.

    Body attendu (= retour de PushManager.subscribe().toJSON()) :
        {
          "endpoint": "https://...",
          "keys": {"p256dh": "...", "auth": "..."}
        }
    """
    user = get_current_user(request)
    body = await request.json()
    endpoint = (body.get("endpoint") or "").strip()
    keys = body.get("keys") or {}
    p256dh = (keys.get("p256dh") or "").strip()
    auth = (keys.get("auth") or "").strip()
    if not endpoint or not p256dh or not auth:
        raise HTTPException(400, "Abonnement invalide")

    ua = (request.headers.get("user-agent") or "")[:255]
    now = datetime.now().isoformat()

    with get_db() as conn:
        # Si l'endpoint existait pour un autre user, on le réassigne.
        conn.execute(
            """INSERT INTO push_subscriptions
                 (user_id, endpoint, p256dh, auth, user_agent, created_at, last_used_at)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(endpoint) DO UPDATE SET
                 user_id=excluded.user_id,
                 p256dh=excluded.p256dh,
                 auth=excluded.auth,
                 user_agent=excluded.user_agent,
                 last_used_at=excluded.last_used_at""",
            (int(user["id"]), endpoint, p256dh, auth, ua, now, now),
        )
        conn.commit()
    return {"success": True}


@router.post("/unsubscribe")
async def unsubscribe(request: Request):
    user = get_current_user(request)
    body = await request.json()
    endpoint = (body.get("endpoint") or "").strip()
    with get_db() as conn:
        if endpoint:
            conn.execute(
                "DELETE FROM push_subscriptions WHERE user_id=? AND endpoint=?",
                (int(user["id"]), endpoint),
            )
        else:
            # Désactive toutes les souscriptions du user (bouton « tout désactiver »).
            conn.execute(
                "DELETE FROM push_subscriptions WHERE user_id=?",
                (int(user["id"]),),
            )
        conn.commit()
    return {"success": True}


@router.post("/test")
def push_test(request: Request):
    """Envoi d'une notification de test à l'utilisateur courant."""
    user = get_current_user(request)
    sent = send_push_to_user(
        int(user["id"]),
        title="MySifa — test",
        body="Si tu vois ce message, les notifications fonctionnent.",
        url="/messagerie",
        tag="mysifa-test",
    )
    return {"sent": sent}


# ── Envoi ────────────────────────────────────────────────────────────


def send_push_to_user(
    user_id: int,
    title: str,
    body: str,
    url: Optional[str] = None,
    tag: Optional[str] = None,
) -> int:
    """Envoie une notification à tous les appareils enregistrés d'un utilisateur.

    Retourne le nombre d'envois réussis. Ne lève jamais d'exception : les
    appelants (chat, etc.) ne doivent pas être bloqués par un problème push.
    Les endpoints qui répondent 404/410 sont supprimés automatiquement.
    """
    if not _push_configured():
        return 0
    try:
        from pywebpush import WebPushException, webpush  # type: ignore
    except Exception as exc:  # pragma: no cover
        log.warning("pywebpush indisponible (%s)", exc)
        return 0

    payload = json.dumps(
        {"title": title, "body": body, "url": url or "/", "tag": tag or ""},
        ensure_ascii=False,
    )

    vapid_claims = {"sub": _vapid_claim_email()}
    private_key = _vapid_private_key()

    sent = 0
    to_drop: list[int] = []
    try:
        with get_db() as conn:
            subs = conn.execute(
                "SELECT id, endpoint, p256dh, auth FROM push_subscriptions WHERE user_id=?",
                (int(user_id),),
            ).fetchall()
    except Exception as exc:
        log.warning("send_push: lecture DB impossible (%s)", exc)
        return 0

    for sub in subs:
        subscription_info = {
            "endpoint": sub["endpoint"],
            "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=private_key,
                vapid_claims=dict(vapid_claims),  # webpush mute le dict reçu
                ttl=60,
            )
            sent += 1
        except WebPushException as exc:  # type: ignore[misc]
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (404, 410):
                to_drop.append(int(sub["id"]))
            else:
                log.warning(
                    "send_push échec uid=%s endpoint=%s status=%s err=%s",
                    user_id, sub["endpoint"][:60], status, exc,
                )
        except Exception as exc:
            log.warning("send_push erreur inattendue uid=%s err=%s", user_id, exc)

    if to_drop:
        try:
            with get_db() as conn:
                conn.executemany(
                    "DELETE FROM push_subscriptions WHERE id=?",
                    [(i,) for i in to_drop],
                )
                conn.commit()
        except Exception:
            pass

    if sent:
        try:
            with get_db() as conn:
                conn.execute(
                    "UPDATE push_subscriptions SET last_used_at=? WHERE user_id=?",
                    (datetime.now().isoformat(), int(user_id)),
                )
                conn.commit()
        except Exception:
            pass

    return sent


def send_push_safe(user_id: Any, **kwargs: Any) -> int:
    """Variante 100 % silencieuse, utilisable dans les routers métier."""
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return 0
    if uid <= 0:
        return 0
    try:
        return send_push_to_user(uid, **kwargs)
    except Exception as exc:  # pragma: no cover — défense en profondeur
        log.warning("send_push_safe: %s", exc)
        return 0
