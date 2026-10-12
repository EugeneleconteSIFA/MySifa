"""
Lecture d'une boîte Outlook par Microsoft Graph (application, sans utilisateur).

Même application Azure que l'envoi (`MS_TENANT_ID`, `MS_CLIENT_ID`,
`MS_CLIENT_SECRET`), avec une permission en plus : `Mail.Read` en mode
application, idéalement limitée à la boîte voulue par une Application Access
Policy côté Exchange. Ce module ne fait que des GET : il ne déplace, ne marque
et ne supprime aucun message.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from config import MS_CLIENT_ID, MS_CLIENT_SECRET, MS_TENANT_ID

_JETON: Dict[str, Any] = {"valeur": None, "expire": 0.0}

GRAPH = "https://graph.microsoft.com/v1.0"


class GraphErreur(Exception):
    """Erreur lisible par un humain, avec le code HTTP quand il y en a un."""

    def __init__(self, message: str, code: Optional[int] = None):
        super().__init__(message)
        self.code = code


def configure() -> bool:
    return bool(MS_TENANT_ID and MS_CLIENT_ID and MS_CLIENT_SECRET)


def _jeton() -> str:
    now = time.time()
    if _JETON["valeur"] and _JETON["expire"] - now > 60:
        return _JETON["valeur"]
    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": MS_CLIENT_ID,
        "client_secret": MS_CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
    }).encode("utf-8")
    req = urllib.request.Request(
        f"https://login.microsoftonline.com/{MS_TENANT_ID}/oauth2/v2.0/token",
        data=data, method="POST",
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            j = json.loads(r.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        raise GraphErreur("Authentification Graph refusée — vérifier l'application Azure.", e.code)
    except Exception as e:
        raise GraphErreur(f"Authentification Graph impossible ({e}).")
    tok = j.get("access_token")
    if not tok:
        raise GraphErreur("Authentification Graph : jeton absent de la réponse.")
    _JETON["valeur"] = tok
    _JETON["expire"] = now + float(j.get("expires_in") or 3600)
    return tok


def _get(url: str, entetes: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    if not configure():
        raise GraphErreur("Microsoft Graph n'est pas configuré sur ce serveur.")
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {_jeton()}")
    for k, v in (entetes or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise GraphErreur(
                "Accès à la boîte refusé — l'application Graph doit recevoir la "
                "permission Mail.Read sur cette boîte (administrateur Microsoft 365).",
                e.code,
            )
        if e.code == 404:
            raise GraphErreur("Boîte introuvable — vérifier l'adresse.", e.code)
        raise GraphErreur(f"Graph a répondu {e.code}.", e.code)
    except GraphErreur:
        raise
    except Exception as e:
        raise GraphErreur(f"Graph injoignable ({e}).")


def tester_acces(boite: str) -> Dict[str, Any]:
    """Lit le compteur de la boîte de réception : prouve le droit de lecture."""
    b = urllib.parse.quote(boite)
    j = _get(f"{GRAPH}/users/{b}/mailFolders/inbox?$select=totalItemCount,unreadItemCount")
    return {"messages": j.get("totalItemCount"), "non_lus": j.get("unreadItemCount")}


_CHAMPS = ("id,conversationId,receivedDateTime,from,subject,bodyPreview,body,"
           "hasAttachments,webLink")


def messages_depuis(boite: str, depuis_iso_utc: str, maximum: int = 200) -> List[Dict[str, Any]]:
    """Messages de la boîte de réception reçus après `depuis_iso_utc`
    (format `2026-10-12T04:00:00Z`), du plus ancien au plus récent.
    Le corps est demandé en texte brut : rien d'HTML n'entre en base."""
    b = urllib.parse.quote(boite)
    q = urllib.parse.urlencode({
        "$filter": f"receivedDateTime gt {depuis_iso_utc}",
        "$orderby": "receivedDateTime asc",
        "$select": _CHAMPS,
        "$top": "50",
    }, safe="$,:")
    url: Optional[str] = f"{GRAPH}/users/{b}/mailFolders/inbox/messages?{q}"
    out: List[Dict[str, Any]] = []
    while url and len(out) < maximum:
        j = _get(url, {"Prefer": 'outlook.body-content-type="text"'})
        out.extend(j.get("value") or [])
        url = j.get("@odata.nextLink")
    return out[:maximum]
