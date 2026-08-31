"""MySifa — Journalisation automatique des écritures.

Le problème que ce middleware règle
-----------------------------------
MySifa compte ~606 endpoints d'écriture répartis sur 65 routers. Seuls 7
d'entre eux appelaient `log_action`. Le journal des actions donnait donc une
image très partielle : il connaissait les paramètres, les expéditions et le
stock, et ignorait complètement les tâches, les réunions, MyQualité, la GED,
le calendrier, la paie, le coffre, les saisies d'atelier, les imports, MyPrint,
le chiffrage, l'ERP…

Compléter à la main les 599 endpoints manquants aurait été un travail sans fin
— et surtout un travail à refaire à chaque nouvel endpoint. Le filet est donc
posé au seul endroit par lequel TOUT passe : la couche HTTP.

Comment il se comporte
----------------------
- Il ne regarde que les écritures (POST / PUT / PATCH / DELETE). Les
  consultations ne sont pas journalisées.
- Il ne journalise que ce qui a abouti (statut < 400), plus les refus de
  permission (403), qui sont précisément ce qu'un journal d'audit doit
  montrer. Une session expirée (401) n'est pas un événement d'audit.
- Il s'efface devant les appels explicites : si le handler a déjà appelé
  `log_action`, aucune ligne générique n'est écrite. L'entrée métier, plus
  parlante, reste seule.
- Il n'écrit jamais le corps d'une requête portant des données personnelles
  (discussions, messagerie, coffre, coffre RH, paie), et filtre partout les
  mots de passe, jetons et clés.
- Il ne peut pas casser une action métier : toute erreur de journalisation est
  avalée.

C'est un middleware ASGI pur, pas un `BaseHTTPMiddleware`. La différence
compte : `BaseHTTPMiddleware` exécute le handler dans une autre tâche, et le
compteur de contexte qui sert au dédoublonnage n'y remonterait pas.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from app.core.audit_taxonomy import (
    BODY_BLIND_MODULES,
    humaniser_endpoint,
    is_skipped,
    redact,
    resolve_action,
    resolve_module,
)
from app.services.audit_service import log_action, ouvrir_contexte

METHODES_ECRITURE = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Au-delà, on ne lit plus le corps : un import Excel ou un upload de PDF n'a
# rien à faire en mémoire pour les besoins du journal.
CORPS_MAX = 4096
DETAIL_MAX = 1500


def _entete(scope, nom: bytes) -> str:
    for cle, valeur in scope.get("headers") or []:
        if cle == nom:
            try:
                return valeur.decode("latin-1")
            except Exception:
                return ""
    return ""


def _ip(scope) -> Optional[str]:
    fwd = _entete(scope, b"x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    client = scope.get("client")
    return client[0] if client else None


def _utilisateur(scope) -> Optional[dict]:
    """Résout l'utilisateur depuis le cookie de session, sans lever."""
    try:
        from app.services.auth_service import COOKIE_NAME, get_user_by_token
    except Exception:
        return None
    brut = _entete(scope, b"cookie")
    if not brut:
        return None
    token = None
    for morceau in brut.split(";"):
        nom, _, valeur = morceau.strip().partition("=")
        if nom == COOKIE_NAME:
            token = valeur
            break
    if not token:
        return None
    try:
        user = get_user_by_token(token)
        return dict(user) if user else None
    except Exception:
        return None


def _objet(scope, path: str) -> str:
    """Libellé lisible : le nom du handler, complété des identifiants d'URL.

    `POST /api/taches/12/commentaires` donne « Ajouter commentaire ·
    tache_id=12 ». À défaut de handler identifiable (404, redirection), on
    retombe sur le chemin, qui reste toujours parlant.
    """
    endpoint = scope.get("endpoint")
    nom = humaniser_endpoint(getattr(endpoint, "__name__", None))
    params = scope.get("path_params") or {}
    suffixe = " · ".join(f"{k}={v}" for k, v in list(params.items())[:4])
    if nom and suffixe:
        return f"{nom} · {suffixe}"
    if nom:
        return nom
    return path


class AuditMiddleware:
    """Filet de journalisation des écritures. À ajouter via `add_middleware`."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        methode = (scope.get("method") or "").upper()
        chemin = scope.get("path") or ""
        if methode not in METHODES_ECRITURE or is_skipped(chemin):
            await self.app(scope, receive, send)
            return

        ctx = ouvrir_contexte()
        statut = {"code": 500}
        corps: list[bytes] = []
        taille = {"n": 0}
        json_attendu = "application/json" in _entete(scope, b"content-type").lower()

        async def receive_espion():
            message = await receive()
            if json_attendu and message.get("type") == "http.request":
                bout = message.get("body") or b""
                if taille["n"] < CORPS_MAX:
                    corps.append(bout[: CORPS_MAX - taille["n"]])
                    taille["n"] += len(bout)
            return message

        async def send_espion(message):
            if message.get("type") == "http.response.start":
                statut["code"] = message.get("status", 500)
            await send(message)

        await self.app(scope, receive_espion, send_espion)

        try:
            self._journaliser(scope, methode, chemin, statut["code"], ctx, corps)
        except Exception:
            pass  # Le journal ne doit jamais dégrader une réponse déjà partie.

    def _journaliser(self, scope, methode, chemin, code, ctx, corps) -> None:
        # Le handler a déjà écrit sa propre ligne, plus précise : on se tait.
        if (ctx or {}).get("n"):
            return
        if code >= 400 and code != 403:
            return

        module = resolve_module(chemin)
        action = "DENIED" if code == 403 else resolve_action(methode, chemin)
        user = _utilisateur(scope)

        if user is None:
            # Écriture sans session : seuls les portails publics (fournisseur,
            # expédition) en font légitimement. Le reste est du bruit.
            if module != "portal":
                return
            user = {"nom": "Portail public", "role": "portail"}

        detail: dict[str, Any] = {"methode": methode, "chemin": chemin}
        if code == 403:
            detail["refus"] = "403"
        if corps and module not in BODY_BLIND_MODULES:
            try:
                charge = json.loads(b"".join(corps).decode("utf-8", "replace"))
                detail["donnees"] = redact(charge)
            except Exception:
                pass

        detail_str = json.dumps(detail, ensure_ascii=False)
        if len(detail_str) > DETAIL_MAX:
            detail_str = detail_str[:DETAIL_MAX] + "…"

        log_action(
            user=user,
            action=action,
            module=module,
            objet=_objet(scope, chemin),
            detail=detail_str,
            ip=_ip(scope),
        )
