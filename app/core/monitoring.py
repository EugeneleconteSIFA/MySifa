# -*- coding: utf-8 -*-
"""
Remontee des erreurs de production.

Le constat qui motive ce module : au 27 aout 2026, MySifa comptait 388
`except Exception:` et zero remontee d'erreur. Une erreur chez un operateur a
6 h du matin ne laissait aucune trace ailleurs que dans `journalctl`, ou
personne ne va la chercher. Le bug n'existait que dans la tete de celui qui
l'avait subi.

Deux niveaux, dans cet ordre :

1. **Le journal structure — toujours actif, aucune dependance.**
   Un gestionnaire d'exception attrape ce qui remonte jusqu'a FastAPI et
   l'ecrit dans le logger `mysifa.erreurs` avec la trace complete, la route,
   la methode et l'utilisateur. Visible en `journalctl -u mysifa -t mysifa`.
   Ca ne remplace pas un outil de suivi, mais ca existe des maintenant et ca
   ne coute rien.

2. **Sentry — optionnel, active par la seule presence de SENTRY_DSN.**
   Sans DSN, ce module ne tente meme pas l'import : aucune dependance requise,
   aucun appel reseau, aucun changement de comportement. Avec un DSN, les
   erreurs partent avec la version, l'instance (v1/v2) et la route.

Ce qui ne part JAMAIS, DSN ou pas : cookies, en-tetes d'autorisation, corps de
requete, mots de passe, cles API. Voir `_nettoyer()`.
"""

import logging
import sys

logger = logging.getLogger("mysifa.erreurs")

_CLES_SENSIBLES = (
    "password", "mot_de_passe", "passwd", "secret", "token", "authorization",
    "cookie", "api_key", "apikey", "cle_api", "dsn", "sifa_token",
)

_actif = False


def _nettoyer(evenement, indice=None):
    """Retire de l'evenement tout ce qui ne doit pas quitter le serveur.

    On enleve plutot que d'anonymiser : une valeur "masquee" reste une valeur
    transmise, et la liste des choses qu'on croit avoir masquees est toujours
    plus courte que la realite.
    """
    try:
        requete = evenement.get("request") or {}
        requete.pop("cookies", None)
        requete.pop("data", None)
        entetes = requete.get("headers") or {}
        for cle in list(entetes):
            if any(m in cle.lower() for m in _CLES_SENSIBLES):
                entetes.pop(cle, None)

        for contexte in (evenement.get("extra") or {}, evenement.get("contexts") or {}):
            for cle in list(contexte):
                if any(m in str(cle).lower() for m in _CLES_SENSIBLES):
                    contexte.pop(cle, None)
    except Exception:
        # Un nettoyage qui echoue ne doit pas empecher l'erreur d'origine de
        # remonter — mais on prefere ne rien envoyer que d'envoyer trop.
        return None
    return evenement


def init_monitoring(app, dsn: str = "", environnement: str = "", version: str = "") -> bool:
    """Branche Sentry si un DSN est fourni. Retourne True si actif.

    Appele depuis main.py au demarrage. Sans DSN : ne fait rien, ne casse rien,
    n'ecrit qu'une ligne de journal.
    """
    global _actif
    if not dsn:
        logger.info("Monitoring externe desactive (SENTRY_DSN absent) — "
                    "les erreurs restent dans le journal systemd.")
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        logger.warning("SENTRY_DSN est renseigne mais sentry-sdk n'est pas installe. "
                       "Installer avec : pip install 'sentry-sdk[fastapi]'")
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=environnement or "inconnu",
        release=version or None,
        # Aucune donnee personnelle par defaut : pas d'IP, pas d'utilisateur.
        send_default_pii=False,
        # Echantillonnage des traces de performance : 0 pour commencer. Les
        # erreurs remontent toutes ; la performance se mesure ailleurs (le
        # logger `mysifa.slow` existe deja).
        traces_sample_rate=0.0,
        before_send=_nettoyer,
        integrations=[StarletteIntegration(), FastApiIntegration()],
    )
    _actif = True
    logger.info("Monitoring Sentry actif (environnement=%s, version=%s).",
                environnement, version)
    return True


def monitoring_actif() -> bool:
    return _actif


def journaliser_exception(request, exc) -> None:
    """Ecrit une exception non rattrapee dans le journal, avec son contexte.

    Toujours appele, que Sentry soit branche ou non : le journal systemd est le
    seul endroit garanti present sur les deux instances.
    """
    try:
        utilisateur = getattr(getattr(request, "state", None), "user", None)
        qui = ""
        if isinstance(utilisateur, dict):
            qui = utilisateur.get("email") or utilisateur.get("username") or ""
        logger.error(
            "%s %s%s -> %s: %s",
            getattr(request, "method", "?"),
            getattr(getattr(request, "url", None), "path", "?"),
            (" [%s]" % qui) if qui else "",
            type(exc).__name__,
            exc,
            exc_info=sys.exc_info(),
        )
    except Exception:
        logger.error("Exception non rattrapee (contexte illisible) : %r", exc, exc_info=True)
