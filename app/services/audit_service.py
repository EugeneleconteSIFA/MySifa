"""MySifa — Service d'audit log.
Enregistre les actions sensibles en DB de façon non bloquante.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from database import get_db


def log_action(
    *,
    user: dict,
    action: str,
    module: str,
    objet: str,
    detail: Optional[Any] = None,
    ip: Optional[str] = None,
) -> None:
    """
    Enregistre une action dans audit_logs.
    Ne lève jamais d'exception — l'audit ne doit pas bloquer l'action métier.

    Args:
        user    : dict retourné par get_current_user()
        action  : CREATE | UPDATE | DELETE | CLOSE | REORDER | VALIDATE | LOGIN | LOGOUT
        module  : planning | fabrication | stock | expe | rh | settings | auth
        objet   : description courte (ex: "Dossier REF-4521 · Cohésio 1")
        detail  : dict ou str avec contexte supplémentaire (avant/après, champs modifiés)
        ip      : adresse IP (Request.client.host)
    """
    try:
        detail_str = (
            json.dumps(detail, ensure_ascii=False)
            if isinstance(detail, dict)
            else (str(detail) if detail else None)
        )
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
                    ip,
                ),
            )
            conn.commit()
    except Exception:
        pass  # L'audit ne doit jamais faire planter une action métier
