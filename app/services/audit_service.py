"""MySifa — Service d'audit log.
Enregistre les actions sensibles en DB de façon non bloquante.

Deux chemins alimentent le journal, et ils se complètent :

1. Les appels EXPLICITES à `log_action` depuis un router. Ce sont les plus
   riches : ils nomment l'objet métier (« Dossier REF-4521 · Cohésio 1 ») et
   décrivent l'avant/après. À privilégier partout où l'on sait quoi écrire.
2. Le middleware d'audit (`app/core/audit_middleware.py`), qui journalise
   automatiquement toute écriture aboutie n'ayant PAS déjà été tracée par un
   appel explicite. C'est le filet : aucune écriture ne peut plus passer à
   travers, y compris dans les modules où personne n'a pensé à appeler ce
   service.

Le dédoublonnage passe par `_ACTION_CTX`, un compteur posé par le middleware
avant d'appeler le handler et incrémenté ici. Le middleware voit donc, en
sortie, si quelqu'un a déjà écrit pour cette requête.
"""
from __future__ import annotations

import json
from contextvars import ContextVar
from typing import Any, Optional

from database import get_db

# Compteur d'appels explicites pour la requête HTTP en cours. Le middleware y
# place un dict mutable AVANT d'appeler le handler : la mutation faite ici est
# donc visible depuis le middleware, quel que soit le contexte async.
_ACTION_CTX: ContextVar[Optional[dict]] = ContextVar("mysifa_audit_ctx", default=None)


def ouvrir_contexte() -> dict:
    """Ouvre le compteur de la requête en cours (réservé au middleware)."""
    ctx: dict = {"n": 0}
    _ACTION_CTX.set(ctx)
    return ctx


def _marquer_appel() -> None:
    ctx = _ACTION_CTX.get()
    if ctx is not None:
        ctx["n"] = ctx.get("n", 0) + 1


def _ip_de(request) -> Optional[str]:
    if request is None:
        return None
    try:
        entete = request.headers.get("x-forwarded-for")
        if entete:
            return entete.split(",")[0].strip()
        client = getattr(request, "client", None)
        return getattr(client, "host", None)
    except Exception:
        return None


def log_action(
    *,
    user: Optional[dict] = None,
    action: str,
    module: str,
    objet: str,
    detail: Optional[Any] = None,
    ip: Optional[str] = None,
    request: Any = None,
) -> None:
    """
    Enregistre une action dans audit_logs.
    Ne lève jamais d'exception — l'audit ne doit pas bloquer l'action métier.

    Args:
        user    : dict retourné par get_current_user()
        action  : verbe court en majuscules. Le vocabulaire complet et ses
                  libellés français vivent dans `app/core/audit_taxonomy.py`
                  (CREATE, UPDATE, DELETE, CLOSE, VALIDATE, SAISIE, SEND…).
        module  : clé de module. Idem, la liste est dans la taxonomie.
        objet   : description courte (ex: "Dossier REF-4521 · Cohésio 1")
        detail  : dict ou str avec contexte supplémentaire (avant/après, champs modifiés)
        ip      : adresse IP ; déduite de `request` si elle n'est pas fournie
        request : la Request FastAPI. Facultative, mais la passer donne l'IP
                  sans effort et évite que le middleware ne réécrive une ligne
                  générique en doublon de celle-ci.
    """
    _marquer_appel()
    try:
        detail_str = (
            json.dumps(detail, ensure_ascii=False)
            if isinstance(detail, (dict, list))
            else (str(detail) if detail else None)
        )
        user = user or {}
        with get_db() as conn:
            conn.execute(
                """INSERT INTO audit_logs (user_id, user_nom, user_role, action, module, objet, detail, ip)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user.get("id"),
                    user.get("nom") or user.get("email", ""),
                    user.get("role", ""),
                    action.upper(),
                    module.lower(),
                    objet,
                    detail_str,
                    ip if ip is not None else _ip_de(request),
                ),
            )
            conn.commit()
    except Exception:
        pass  # L'audit ne doit jamais faire planter une action métier
