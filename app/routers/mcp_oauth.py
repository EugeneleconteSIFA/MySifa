"""Serveur d'autorisation OAuth 2.1 du serveur MCP MySifa.

Pourquoi ce module existe — et pourquoi le `403` de `mcp_server.py` redevient
un `401`.

Un connecteur Claude ne sait pas transporter d'en-tete `X-Api-Key`. Quand il
recoit un `401` sur `/mcp`, il part chercher les metadonnees du serveur
d'autorisation, s'enregistre comme client, ouvre une fenetre de consentement,
et repasse avec un jeton. Ce module fournit les quatre pieces que cette
sequence exige, et qui manquaient :

    /.well-known/oauth-protected-resource   qui protege /mcp, et qui autorise
    /.well-known/oauth-authorization-server les endpoints et les algos acceptes
    POST /oauth/register                    enregistrement dynamique (RFC 7591)
    GET  /oauth/authorize + POST /oauth/token   code PKCE, puis jeton

Tant que ces routes n'existaient pas, le `401` envoyait le client dans le vide
et l'ecran affichait « impossible de s'inscrire aupres du service de connexion ».
Le commentaire historique de `mcp_server.py` en tirait la conclusion inverse —
supprimer le `401` — ce qui fermait la seule porte que le client sait ouvrir.

Ce qu'on gagne au passage sur les cles API : un jeton porte un utilisateur.
Le journal des actions nomme la personne derriere chaque lecture, la ou une
cle ne nommait qu'une etiquette. La revocation est individuelle, et une
session MySifa expiree ne suffit pas a reautoriser — il faut repasser par
l'ecran de consentement.

Rien n'est stocke en clair : codes, jetons d'acces et de rafraichissement ne
laissent qu'une empreinte SHA-256, comme `api_keys`.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Optional
from urllib.parse import urlencode, urlsplit

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from config import COOKIE_NAME, MCP_OAUTH_ROLES
from app.core.database import get_db
from app.services.audit_service import log_action
from app.services.auth_service import effective_role, get_optional_user
from app.web.mcp_oauth_page import page_consentement, page_erreur
from app.routers.mcp_server import SCOPE_MCP

router = APIRouter(tags=["mcp"])
logger = logging.getLogger("mysifa.mcp.oauth")

# Duree de vie. Le jeton d'acces est court parce qu'il circule a chaque appel ;
# le rafraichissement est long parce qu'il ne sort que pour le renouveler.
ACCES_HEURES = 8
RAFRAICHISSEMENT_JOURS = 30
CODE_SECONDES = 300

# Borne haute sur les clients enregistres. L'enregistrement dynamique est par
# construction ouvert — c'est le protocole qui le veut — donc il faut un
# plafond, sinon n'importe qui remplit la table. Au-dela, les clients jamais
# utilises et vieux de plus d'un jour sont recycles.
CLIENTS_MAX = 200

_HORODATAGE = "%Y-%m-%dT%H:%M:%S"


# ── Utilitaires ──────────────────────────────────────────────────────────────

def _maintenant() -> str:
    return datetime.now().strftime(_HORODATAGE)


def _dans(**delta) -> str:
    return (datetime.now() + timedelta(**delta)).strftime(_HORODATAGE)


def _empreinte(valeur: str) -> str:
    return hashlib.sha256(valeur.encode()).hexdigest()


def base_publique(request: Request) -> str:
    """URL absolue de CETTE instance, vue du client.

    Surtout pas `public_base_url()` : v1 et la prod partagent le code et pas le
    domaine. Un emetteur fige sur www casserait le consentement depuis v1, et
    le client rejette un `issuer` qui ne correspond pas a l'URL interrogee.
    """
    entetes = request.headers
    schema = (entetes.get("x-forwarded-proto") or request.url.scheme or "https").split(",")[0].strip()
    hote = (entetes.get("x-forwarded-host") or entetes.get("host") or request.url.netloc).split(",")[0].strip()
    return f"{schema}://{hote}".rstrip("/")


def _json(contenu: Any, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        contenu,
        status_code=status_code,
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


def _erreur_oauth(code: str, description: str, status_code: int = 400) -> JSONResponse:
    return _json({"error": code, "error_description": description}, status_code)


def _redirection_erreur(redirect_uri: str, code: str, description: str,
                        state: Optional[str]) -> RedirectResponse:
    params = {"error": code, "error_description": description}
    if state:
        params["state"] = state
    separateur = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(f"{redirect_uri}{separateur}{urlencode(params)}", status_code=302)


def _uri_redirection_acceptable(uri: str) -> bool:
    """HTTPS exige, sauf boucle locale — un client de bureau ecoute en local."""
    try:
        parts = urlsplit(uri)
    except Exception:
        return False
    if parts.fragment or not parts.scheme or not parts.netloc:
        return False
    if parts.scheme == "https":
        return True
    if parts.scheme == "http" and parts.hostname in ("localhost", "127.0.0.1", "::1"):
        return True
    return False


def _portees(demandee: Optional[str]) -> str:
    """Une seule portee existe. Tout le reste est ignore, jamais accorde."""
    if not demandee:
        return SCOPE_MCP
    demandees = [p.strip() for p in demandee.replace(",", " ").split() if p.strip()]
    return SCOPE_MCP if (not demandees or SCOPE_MCP in demandees) else ""


def _client(conn, client_id: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM mcp_oauth_clients WHERE client_id=? LIMIT 1", (client_id,)
    ).fetchone()
    return dict(row) if row else None


def _uris_client(client: dict) -> list[str]:
    try:
        uris = json.loads(client.get("redirect_uris") or "[]")
    except Exception:
        return []
    return [u for u in uris if isinstance(u, str)]


def _menage(conn) -> None:
    """Codes perimes et jetons morts depuis plus de 30 jours."""
    limite = (datetime.now() - timedelta(days=30)).strftime(_HORODATAGE)
    conn.execute("DELETE FROM mcp_oauth_codes WHERE expires_at < ?", (limite,))
    conn.execute(
        "DELETE FROM mcp_oauth_tokens WHERE (refresh_expires_at IS NULL OR refresh_expires_at < ?) "
        "AND (revoked_at IS NOT NULL OR expires_at < ?)",
        (limite, limite),
    )


# ── Metadonnees ──────────────────────────────────────────────────────────────
# Deux formes de chemin pour chacune : la RFC 9728 place l'identifiant de la
# ressource apres le chemin bien connu, certains clients interrogent la forme
# nue. Les deux repondent la meme chose plutot que de parier sur l'une.

def _metadonnees_ressource(request: Request) -> dict:
    base = base_publique(request)
    return {
        "resource": f"{base}/mcp",
        "authorization_servers": [base],
        "scopes_supported": [SCOPE_MCP],
        "bearer_methods_supported": ["header"],
        "resource_name": "MySifa — serveur MCP",
        "resource_documentation": f"{base}/mcp",
    }


def _metadonnees_serveur(request: Request) -> dict:
    base = base_publique(request)
    return {
        "issuer": base,
        "authorization_endpoint": f"{base}/oauth/authorize",
        "token_endpoint": f"{base}/oauth/token",
        "registration_endpoint": f"{base}/oauth/register",
        "revocation_endpoint": f"{base}/oauth/revoke",
        "scopes_supported": [SCOPE_MCP],
        "response_types_supported": ["code"],
        "response_modes_supported": ["query"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["none", "client_secret_post", "client_secret_basic"],
        "code_challenge_methods_supported": ["S256"],
        "service_documentation": f"{base}/mcp",
    }


@router.get("/.well-known/oauth-protected-resource")
@router.get("/.well-known/oauth-protected-resource/mcp")
def metadonnees_ressource(request: Request):
    return _json(_metadonnees_ressource(request))


@router.get("/.well-known/oauth-authorization-server")
@router.get("/.well-known/oauth-authorization-server/mcp")
def metadonnees_serveur(request: Request):
    return _json(_metadonnees_serveur(request))


# ── Enregistrement dynamique (RFC 7591) ──────────────────────────────────────

@router.post("/oauth/register")
async def enregistrer_client(request: Request):
    try:
        corps = await request.json()
    except Exception:
        return _erreur_oauth("invalid_client_metadata", "Corps JSON attendu.")
    if not isinstance(corps, dict):
        return _erreur_oauth("invalid_client_metadata", "Corps JSON attendu.")

    uris = corps.get("redirect_uris")
    if not isinstance(uris, list) or not uris:
        return _erreur_oauth("invalid_redirect_uri", "Au moins une URI de redirection est requise.")
    if len(uris) > 5:
        return _erreur_oauth("invalid_redirect_uri", "Cinq URIs de redirection au maximum.")
    for uri in uris:
        if not isinstance(uri, str) or not _uri_redirection_acceptable(uri):
            return _erreur_oauth(
                "invalid_redirect_uri",
                "URI de redirection invalide : HTTPS exige, hors boucle locale, sans fragment.",
            )

    methode = (corps.get("token_endpoint_auth_method") or "none").strip()
    if methode not in ("none", "client_secret_post", "client_secret_basic"):
        return _erreur_oauth("invalid_client_metadata", f"Methode d'authentification « {methode} » non supportee.")

    nom = str(corps.get("client_name") or "Client MCP").strip()[:120]
    client_id = "mcpc_" + secrets.token_urlsafe(24)
    secret_brut = None
    secret_empreinte = None
    if methode != "none":
        secret_brut = secrets.token_urlsafe(48)
        secret_empreinte = _empreinte(secret_brut)

    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM mcp_oauth_clients").fetchone()["n"]
        if total >= CLIENTS_MAX:
            veille = (datetime.now() - timedelta(days=1)).strftime(_HORODATAGE)
            conn.execute(
                "DELETE FROM mcp_oauth_clients WHERE last_used_at IS NULL AND created_at < ?",
                (veille,),
            )
            total = conn.execute("SELECT COUNT(*) AS n FROM mcp_oauth_clients").fetchone()["n"]
            if total >= CLIENTS_MAX:
                return _erreur_oauth(
                    "invalid_client_metadata",
                    "Trop de clients enregistres sur cette instance. Contactez l'administrateur.",
                    status_code=429,
                )
        conn.execute(
            """INSERT INTO mcp_oauth_clients
               (client_id, client_secret_hash, client_name, redirect_uris, scope, auth_method, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (client_id, secret_empreinte, nom, json.dumps(uris), SCOPE_MCP, methode, _maintenant()),
        )
        conn.commit()

    logger.info("MCP OAuth : client enregistre « %s » (%s)", nom, methode)
    reponse = {
        "client_id": client_id,
        "client_id_issued_at": int(datetime.now().timestamp()),
        "client_name": nom,
        "redirect_uris": uris,
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": methode,
        "scope": SCOPE_MCP,
    }
    # Le secret n'est renvoye qu'ici, une fois, et n'existe nulle part en clair
    # ensuite — meme regle que pour les cles API.
    if secret_brut:
        reponse["client_secret"] = secret_brut
        reponse["client_secret_expires_at"] = 0
    return _json(reponse, 201)


# ── Autorisation ─────────────────────────────────────────────────────────────

def _jeton_formulaire(request: Request, client_id: str, redirect_uri: str, defi: str) -> str:
    """Anti-CSRF de l'ecran de consentement.

    La cle est le cookie de session lui-meme : il est `httponly`, donc un site
    tiers ne peut ni le lire ni fabriquer la signature. Pas de secret a
    provisionner, pas d'etat a stocker, et la signature meurt avec la session.
    """
    cle = (request.cookies.get(COOKIE_NAME) or "").encode()
    message = f"{client_id}|{redirect_uri}|{defi}".encode()
    return hmac.new(cle, message, hashlib.sha256).hexdigest()


@router.get("/oauth/authorize")
def autoriser(request: Request):
    p = request.query_params
    client_id = (p.get("client_id") or "").strip()
    redirect_uri = (p.get("redirect_uri") or "").strip()
    state = p.get("state")
    defi = (p.get("code_challenge") or "").strip()
    methode_defi = (p.get("code_challenge_method") or "").strip()
    type_reponse = (p.get("response_type") or "").strip()

    with get_db() as conn:
        client = _client(conn, client_id) if client_id else None

    # Tant que le client ou l'URI n'est pas verifie, on n'a nulle part ou
    # rediriger : afficher l'erreur est la seule option sure. Rediriger vers
    # une URI non validee, c'est offrir un relais ouvert.
    if not client:
        return page_erreur("Client inconnu",
                           "Ce client n'est pas enregistre sur cette instance. "
                           "Supprimez le connecteur et ajoutez-le a nouveau.")
    if redirect_uri not in _uris_client(client):
        return page_erreur("Redirection refusee",
                           "L'adresse de retour ne correspond pas a celles declarees "
                           "lors de l'enregistrement du client.")

    if type_reponse != "code":
        return _redirection_erreur(redirect_uri, "unsupported_response_type",
                                   "Seul le type « code » est supporte.", state)
    if not defi or methode_defi != "S256":
        return _redirection_erreur(redirect_uri, "invalid_request",
                                   "PKCE avec code_challenge_method=S256 obligatoire.", state)
    if not _portees(p.get("scope")):
        return _redirection_erreur(redirect_uri, "invalid_scope",
                                   f"Seule la portee « {SCOPE_MCP} » est accordee.", state)

    utilisateur = get_optional_user(request)
    if not utilisateur:
        # Pas de session : la page porte un formulaire de connexion qui poste
        # sur /api/auth/login puis recharge cette meme URL. Pas de detour par
        # le portail, qui perdrait les parametres OAuth en route.
        return page_consentement(request, client=client, utilisateur=None, jeton_formulaire="")

    if effective_role(utilisateur) not in MCP_OAUTH_ROLES:
        return page_erreur(
            "Compte non habilite",
            "Votre compte n'a pas le droit d'ouvrir un acces MCP aux donnees de production. "
            "Cet acces est reserve a la direction et aux super administrateurs.",
        )

    return page_consentement(
        request,
        client=client,
        utilisateur=utilisateur,
        jeton_formulaire=_jeton_formulaire(request, client_id, redirect_uri, defi),
    )


@router.post("/oauth/authorize/decision")
async def decision(request: Request):
    formulaire = await request.form()
    client_id = (formulaire.get("client_id") or "").strip()
    redirect_uri = (formulaire.get("redirect_uri") or "").strip()
    defi = (formulaire.get("code_challenge") or "").strip()
    state = formulaire.get("state") or None
    ressource = formulaire.get("resource") or None
    accorde = (formulaire.get("decision") or "") == "autoriser"

    with get_db() as conn:
        client = _client(conn, client_id) if client_id else None
    if not client or redirect_uri not in _uris_client(client):
        return page_erreur("Demande invalide", "Client ou adresse de retour non reconnus.")

    utilisateur = get_optional_user(request)
    if not utilisateur:
        return page_erreur("Session expiree", "Reconnectez-vous, puis relancez la connexion du connecteur.")
    if effective_role(utilisateur) not in MCP_OAUTH_ROLES:
        return page_erreur("Compte non habilite",
                           "Cet acces est reserve a la direction et aux super administrateurs.")

    attendu = _jeton_formulaire(request, client_id, redirect_uri, defi)
    if not hmac.compare_digest(attendu, (formulaire.get("jeton_formulaire") or "")):
        return page_erreur("Formulaire perime",
                           "La page de consentement n'est plus valide. Relancez la connexion du connecteur.")

    if not accorde:
        return _redirection_erreur(redirect_uri, "access_denied", "Acces refuse par l'utilisateur.", state)

    code = "mcpa_" + secrets.token_urlsafe(32)
    with get_db() as conn:
        _menage(conn)
        conn.execute(
            """INSERT INTO mcp_oauth_codes
               (code_hash, client_id, user_id, user_email, redirect_uri, code_challenge,
                code_challenge_method, scope, resource, created_at, expires_at)
               VALUES (?,?,?,?,?,?,'S256',?,?,?,?)""",
            (_empreinte(code), client_id, utilisateur["id"], utilisateur.get("email", ""),
             redirect_uri, defi, SCOPE_MCP, ressource, _maintenant(),
             _dans(seconds=CODE_SECONDES)),
        )
        conn.execute("UPDATE mcp_oauth_clients SET last_used_at=? WHERE client_id=?",
                     (_maintenant(), client_id))
        conn.commit()

    # Un humain vient d'ouvrir sa base de production a un agent : c'est
    # exactement le genre d'evenement pour lequel le journal existe.
    log_action(
        user=utilisateur,
        action="GRANT",
        module="mcp",
        objet=f"Acces MCP accorde · {client.get('client_name') or client_id}",
        detail=f"Portee {SCOPE_MCP} · retour {urlsplit(redirect_uri).netloc}",
        ip=request.client.host if request.client else None,
    )

    params = {"code": code}
    if state:
        params["state"] = state
    separateur = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(f"{redirect_uri}{separateur}{urlencode(params)}", status_code=302)


# ── Jetons ───────────────────────────────────────────────────────────────────

def _verifier_pkce(verificateur: str, defi: str) -> bool:
    calcule = base64.urlsafe_b64encode(
        hashlib.sha256(verificateur.encode("ascii")).digest()
    ).decode("ascii").rstrip("=")
    return hmac.compare_digest(calcule, defi)


def _client_authentifie(request: Request, formulaire, conn) -> tuple[Optional[dict], Optional[JSONResponse]]:
    client_id = (formulaire.get("client_id") or "").strip()
    secret = formulaire.get("client_secret") or ""

    entete = request.headers.get("authorization") or ""
    if entete.lower().startswith("basic "):
        try:
            decode = base64.b64decode(entete[6:].strip()).decode("utf-8")
            identifiant, _, motdepasse = decode.partition(":")
            client_id = client_id or identifiant.strip()
            secret = secret or motdepasse
        except Exception:
            return None, _erreur_oauth("invalid_client", "En-tete Basic illisible.", 401)

    if not client_id:
        return None, _erreur_oauth("invalid_client", "client_id manquant.", 401)
    client = _client(conn, client_id)
    if not client:
        return None, _erreur_oauth("invalid_client", "Client inconnu.", 401)

    attendu = client.get("client_secret_hash")
    if attendu:
        if not secret or not hmac.compare_digest(_empreinte(secret), attendu):
            return None, _erreur_oauth("invalid_client", "Secret client invalide.", 401)
    return client, None


def _emettre(conn, client_id: str, user_id: int, user_email: str) -> dict:
    acces = "mcpt_" + secrets.token_urlsafe(40)
    rafraichissement = "mcpr_" + secrets.token_urlsafe(40)
    conn.execute(
        """INSERT INTO mcp_oauth_tokens
           (access_hash, refresh_hash, client_id, user_id, user_email, scope,
            created_at, expires_at, refresh_expires_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (_empreinte(acces), _empreinte(rafraichissement), client_id, user_id, user_email,
         SCOPE_MCP, _maintenant(), _dans(hours=ACCES_HEURES),
         _dans(days=RAFRAICHISSEMENT_JOURS)),
    )
    return {
        "access_token": acces,
        "token_type": "Bearer",
        "expires_in": ACCES_HEURES * 3600,
        "refresh_token": rafraichissement,
        "scope": SCOPE_MCP,
    }


@router.post("/oauth/token")
async def jeton(request: Request):
    try:
        formulaire = await request.form()
    except Exception:
        return _erreur_oauth("invalid_request", "Formulaire attendu (application/x-www-form-urlencoded).")

    type_octroi = (formulaire.get("grant_type") or "").strip()

    with get_db() as conn:
        client, refus = _client_authentifie(request, formulaire, conn)
        if refus is not None:
            return refus
        _menage(conn)

        if type_octroi == "authorization_code":
            code = (formulaire.get("code") or "").strip()
            verificateur = (formulaire.get("code_verifier") or "").strip()
            redirect_uri = (formulaire.get("redirect_uri") or "").strip()
            if not code or not verificateur:
                return _erreur_oauth("invalid_request", "code et code_verifier requis.")

            ligne = conn.execute(
                "SELECT * FROM mcp_oauth_codes WHERE code_hash=? LIMIT 1", (_empreinte(code),)
            ).fetchone()
            if not ligne:
                return _erreur_oauth("invalid_grant", "Code inconnu.")
            ligne = dict(ligne)

            if ligne["used_at"]:
                # Rejeu : le code est deja consomme. Tout ce qui a ete emis a
                # partir de lui devient suspect, donc on revoque.
                conn.execute(
                    "UPDATE mcp_oauth_tokens SET revoked_at=? WHERE client_id=? AND user_id=? AND revoked_at IS NULL",
                    (_maintenant(), ligne["client_id"], ligne["user_id"]),
                )
                conn.commit()
                logger.warning("MCP OAuth : code rejoue pour le client %s — jetons revoques",
                               ligne["client_id"])
                return _erreur_oauth("invalid_grant", "Code deja utilise.")
            if ligne["expires_at"] < _maintenant():
                return _erreur_oauth("invalid_grant", "Code expire.")
            if ligne["client_id"] != client["client_id"]:
                return _erreur_oauth("invalid_grant", "Code emis pour un autre client.")
            if redirect_uri and redirect_uri != ligne["redirect_uri"]:
                return _erreur_oauth("invalid_grant", "Adresse de retour differente de celle du code.")
            if not _verifier_pkce(verificateur, ligne["code_challenge"]):
                return _erreur_oauth("invalid_grant", "Verificateur PKCE invalide.")

            conn.execute("UPDATE mcp_oauth_codes SET used_at=? WHERE id=?",
                         (_maintenant(), ligne["id"]))
            sortie = _emettre(conn, client["client_id"], ligne["user_id"], ligne["user_email"])
            conn.execute("UPDATE mcp_oauth_clients SET last_used_at=? WHERE client_id=?",
                         (_maintenant(), client["client_id"]))
            conn.commit()
            return _json(sortie)

        if type_octroi == "refresh_token":
            brut = (formulaire.get("refresh_token") or "").strip()
            if not brut:
                return _erreur_oauth("invalid_request", "refresh_token requis.")
            ligne = conn.execute(
                "SELECT * FROM mcp_oauth_tokens WHERE refresh_hash=? LIMIT 1", (_empreinte(brut),)
            ).fetchone()
            if not ligne:
                return _erreur_oauth("invalid_grant", "Jeton de rafraichissement inconnu.")
            ligne = dict(ligne)
            if ligne["revoked_at"]:
                return _erreur_oauth("invalid_grant", "Jeton revoque.")
            if (ligne["refresh_expires_at"] or "") < _maintenant():
                return _erreur_oauth("invalid_grant", "Jeton de rafraichissement expire.")
            if ligne["client_id"] != client["client_id"]:
                return _erreur_oauth("invalid_grant", "Jeton emis pour un autre client.")

            # Rotation : l'ancien meurt en meme temps que le nouveau nait.
            conn.execute("UPDATE mcp_oauth_tokens SET revoked_at=? WHERE id=?",
                         (_maintenant(), ligne["id"]))
            sortie = _emettre(conn, client["client_id"], ligne["user_id"], ligne["user_email"])
            conn.commit()
            return _json(sortie)

    return _erreur_oauth("unsupported_grant_type",
                         "Seuls authorization_code et refresh_token sont supportes.")


@router.post("/oauth/revoke")
async def revoquer(request: Request):
    """RFC 7009. Repond 200 meme si le jeton est inconnu : le contraire dirait
    a un attaquant lesquels de ses essais existent."""
    try:
        formulaire = await request.form()
    except Exception:
        return Response(status_code=200)
    brut = (formulaire.get("token") or "").strip()
    if brut:
        empreinte = _empreinte(brut)
        with get_db() as conn:
            conn.execute(
                "UPDATE mcp_oauth_tokens SET revoked_at=? WHERE (access_hash=? OR refresh_hash=?) AND revoked_at IS NULL",
                (_maintenant(), empreinte, empreinte),
            )
            conn.commit()
    return Response(status_code=200)


# ── Lecture par le serveur MCP ───────────────────────────────────────────────

def utilisateur_du_jeton(brut: str) -> Optional[dict]:
    """Resout un jeton d'acces. Renvoie None si absent, expire ou revoque.

    Appele par `mcp_server.py` a chaque requete : c'est le point ou un jeton
    OAuth vaut une cle API, avec un utilisateur nomme en plus.
    """
    if not brut:
        return None
    empreinte = _empreinte(brut)
    with get_db() as conn:
        ligne = conn.execute(
            "SELECT * FROM mcp_oauth_tokens WHERE access_hash=? LIMIT 1", (empreinte,)
        ).fetchone()
        if not ligne:
            return None
        ligne = dict(ligne)
        if ligne["revoked_at"] or ligne["expires_at"] < _maintenant():
            return None
        try:
            conn.execute("UPDATE mcp_oauth_tokens SET last_used_at=? WHERE id=?",
                         (_maintenant(), ligne["id"]))
            conn.commit()
        except Exception:
            pass
    return {
        "user_id": ligne["user_id"],
        "user_email": ligne["user_email"],
        "scope": ligne["scope"],
        "client_id": ligne["client_id"],
    }
