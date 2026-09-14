"""
OAuth du serveur MCP : la sequence complete, de l'enregistrement au jeton.

Ce que ce test protege, dans l'ordre d'importance :

1. **Le `401` porteur de `WWW-Authenticate`.** C'est le seul signal qui envoie
   un connecteur Claude vers les metadonnees, puis vers l'enregistrement. Il a
   deja ete remplace par un `403` une fois, en juin 2026, avec pour symptome
   « impossible de s'inscrire aupres du service de connexion ». Si ce cas
   repasse au vert avec un `403`, le connecteur est casse et rien d'autre ne le
   dit.
2. **PKCE reellement verifie.** Un code d'autorisation qui se convertit en
   jeton sans le bon verificateur, c'est une interception qui reussit.
3. **Le code ne sert qu'une fois**, et un rejeu revoque ce qui a ete emis.
4. **Les redirections ne sont jamais suivies a l'aveugle** : une URI non
   declaree ne recoit ni code, ni redirection d'erreur.
5. **L'habilitation** : un compte hors des roles autorises ne peut pas ouvrir
   la base de production a un agent.

Le test monte sa propre base temporaire via DB_PATH — il ne touche a aucune
base du depot. Il est saute si FastAPI n'est pas installe.

Lancer : python3 tests/test_mcp_oauth.py
"""

import base64
import hashlib
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

# Avant tout import applicatif : la base de ce test est un fichier neuf.
_tmp = tempfile.mkdtemp(prefix="mcp_oauth_test_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")

FAIL: list[str] = []


def verifier(libelle, obtenu, attendu):
    if obtenu == attendu:
        print(f"  ok   {libelle}")
    else:
        print(f"  KO   {libelle} : obtenu {obtenu!r}, attendu {attendu!r}")
        FAIL.append(libelle)


try:
    import fastapi  # noqa: F401
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
except Exception as e:  # pragma: no cover
    print(f"  --   saute : FastAPI indisponible ({type(e).__name__}: {e})")
    sys.exit(0)

# Le shim `database` en premier : il charge app.core.database, qui joue les
# migrations. L'ordre inverse casse l'import (cf. CLAUDE.md).
import database  # noqa: E402
from database import get_db  # noqa: E402
from config import COOKIE_NAME  # noqa: E402
from app.routers import mcp_oauth as oauth  # noqa: E402
from app.routers import mcp_server as srv  # noqa: E402


# ─── Utilitaires PKCE ───────────────────────────────────────────────

VERIFICATEUR = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"


def defi(verificateur: str) -> str:
    return base64.urlsafe_b64encode(
        hashlib.sha256(verificateur.encode()).digest()
    ).decode().rstrip("=")


DEFI = defi(VERIFICATEUR)

print("\n0. PKCE")
verifier("le calcul du defi suit l'exemple de la RFC 7636",
         DEFI, "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM")
verifier("un verificateur correct passe", oauth._verifier_pkce(VERIFICATEUR, DEFI), True)
verifier("un verificateur faux est refuse", oauth._verifier_pkce("autre-chose", DEFI), False)


# ─── Application de test ────────────────────────────────────────────

app = FastAPI()
app.include_router(oauth.router)
app.include_router(srv.router)
client = TestClient(app, base_url="https://test.mysifa.com")

REDIRECT = "https://claude.ai/api/mcp/auth_callback"


def _creer_utilisateur(email: str, role: str) -> str:
    """Cree un compte et une session valide, renvoie le jeton de session."""
    jeton = "sess_" + base64.urlsafe_b64encode(os.urandom(18)).decode().rstrip("=")
    maintenant = datetime.now()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (email, identifiant, password_hash, nom, role, actif, created_at) "
            "VALUES (?,?,?,?,?,1,?)",
            (email, email.split("@")[0], "x", email.split("@")[0], role,
             maintenant.isoformat()),
        )
        uid = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"]
        conn.execute(
            "INSERT INTO sessions (user_id, token, created_at, expires_at) VALUES (?,?,?,?)",
            (uid, jeton, maintenant.isoformat(), (maintenant + timedelta(hours=6)).isoformat()),
        )
        conn.commit()
    return jeton


# ─── 1. Le refus qui ouvre la negociation ───────────────────────────

print("\n1. Refus de /mcp sans jeton")
r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
verifier("sans credential, c'est un 401 et pas un 403", r.status_code, 401)
entete = r.headers.get("WWW-Authenticate", "")
verifier("le 401 designe les metadonnees de la ressource",
         "resource_metadata=" in entete and "/.well-known/oauth-protected-resource" in entete, True)

r = client.post("/mcp", headers={"X-Api-Key": "msk_inexistante"},
                json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
verifier("une cle inconnue reste un 401 invalid_token", r.status_code, 401)


# ─── 2. Metadonnees ─────────────────────────────────────────────────

print("\n2. Metadonnees")
m = client.get("/.well-known/oauth-protected-resource").json()
verifier("la ressource protegee est bien /mcp", m["resource"], "https://test.mysifa.com/mcp")
verifier("l'emetteur suit l'hote interroge, pas une constante",
         m["authorization_servers"], ["https://test.mysifa.com"])
verifier("la forme suffixee repond aussi",
         client.get("/.well-known/oauth-protected-resource/mcp").status_code, 200)

s = client.get("/.well-known/oauth-authorization-server").json()
verifier("S256 est la seule methode PKCE annoncee", s["code_challenge_methods_supported"], ["S256"])
verifier("l'enregistrement dynamique est annonce",
         s["registration_endpoint"], "https://test.mysifa.com/oauth/register")


# ─── 3. Enregistrement dynamique ────────────────────────────────────

print("\n3. Enregistrement")
verifier("une redirection en clair hors boucle locale est refusee",
         client.post("/oauth/register",
                     json={"redirect_uris": ["http://exemple.test/retour"]}).status_code, 400)
verifier("une redirection avec fragment est refusee",
         client.post("/oauth/register",
                     json={"redirect_uris": ["https://exemple.test/retour#x"]}).status_code, 400)
verifier("sans redirect_uris, c'est un refus",
         client.post("/oauth/register", json={"client_name": "X"}).status_code, 400)

r = client.post("/oauth/register", json={"client_name": "Claude", "redirect_uris": [REDIRECT]})
verifier("un client public s'enregistre", r.status_code, 201)
enr = r.json()
CLIENT_ID = enr["client_id"]
verifier("un client public ne recoit pas de secret", "client_secret" in enr, False)
verifier("la boucle locale reste acceptee",
         client.post("/oauth/register",
                     json={"redirect_uris": ["http://127.0.0.1:8976/cb"]}).status_code, 201)


# ─── 4. Autorisation ────────────────────────────────────────────────

print("\n4. Autorisation")


def url_autorisation(client_id=None, redirect=None, challenge=None):
    return ("/oauth/authorize?response_type=code"
            f"&client_id={client_id or CLIENT_ID}"
            f"&redirect_uri={redirect or REDIRECT}"
            f"&code_challenge={challenge or DEFI}"
            "&code_challenge_method=S256&state=etat-42")


r = client.get(url_autorisation(client_id="mcpc_inconnu"))
verifier("un client inconnu ne redirige nulle part", r.status_code, 400)
r = client.get(url_autorisation(redirect="https://ailleurs.test/cb"))
verifier("une URI non declaree ne recoit meme pas d'erreur redirigee", r.status_code, 400)

r = client.get(url_autorisation(), follow_redirects=False)
verifier("sans session, la page demande la connexion",
         r.status_code == 200 and "Connexion requise" in r.text, True)

def poser_session(jeton: str) -> None:
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, jeton)


jeton_ope = _creer_utilisateur("operateur@sifa.test", "fabrication")
poser_session(jeton_ope)
r = client.get(url_autorisation())
verifier("un compte non habilite est arrete net",
         r.status_code == 400 and "non habilite" in r.text, True)

jeton_dir = _creer_utilisateur("direction@sifa.test", "direction")
poser_session(jeton_dir)
r = client.get(url_autorisation())
verifier("la direction voit l'ecran de consentement",
         r.status_code == 200 and "Autoriser l'acces" in r.text, True)

import re  # noqa: E402
trouve = re.search(r'name="jeton_formulaire" value="([^"]+)"', r.text)
verifier("le formulaire porte un jeton anti-CSRF", bool(trouve), True)
JETON_FORM = trouve.group(1) if trouve else ""


def poster_decision(decision="autoriser", jeton_form=None):
    return client.post("/oauth/authorize/decision", data={
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT,
        "code_challenge": DEFI,
        "state": "etat-42",
        "resource": "",
        "jeton_formulaire": JETON_FORM if jeton_form is None else jeton_form,
        "decision": decision,
    }, follow_redirects=False)


verifier("un jeton de formulaire falsifie est rejete",
         poster_decision(jeton_form="faux").status_code, 400)

r = poster_decision(decision="refuser")
verifier("un refus revient au client avec access_denied",
         r.status_code == 302 and "error=access_denied" in r.headers["location"], True)

r = poster_decision()
verifier("l'autorisation redirige avec un code", r.status_code, 302)
lieu = r.headers["location"]
verifier("l'etat du client est rendu tel quel", "state=etat-42" in lieu, True)
CODE = re.search(r"[?&]code=([^&]+)", lieu).group(1)


# ─── 5. Echange du code ─────────────────────────────────────────────

print("\n5. Jetons")


def poster_jeton(**champs):
    base = {"grant_type": "authorization_code", "client_id": CLIENT_ID,
            "code": CODE, "code_verifier": VERIFICATEUR, "redirect_uri": REDIRECT}
    base.update(champs)
    return client.post("/oauth/token", data=base)


verifier("un verificateur PKCE faux ne donne pas de jeton",
         poster_jeton(code_verifier="mauvais").json()["error"], "invalid_grant")
verifier("une autre adresse de retour est refusee",
         poster_jeton(redirect_uri="https://claude.ai/autre").json()["error"], "invalid_grant")

r = poster_jeton()
verifier("le code correct donne un jeton", r.status_code, 200)
jetons = r.json()
verifier("le type est Bearer", jetons["token_type"], "Bearer")
verifier("la portee accordee est la seule qui existe", jetons["scope"], srv.SCOPE_MCP)
ACCES, RAFRAICHIR = jetons["access_token"], jetons["refresh_token"]

verifier("le meme code ne marche pas deux fois",
         poster_jeton().json()["error"], "invalid_grant")
with get_db() as conn:
    restants = conn.execute(
        "SELECT COUNT(*) AS n FROM mcp_oauth_tokens WHERE revoked_at IS NULL"
    ).fetchone()["n"]
verifier("un code rejoue revoque les jetons deja emis", restants, 0)


# ─── 6. Le jeton ouvre reellement /mcp ──────────────────────────────

print("\n6. Acces au protocole")
# Les jetons du tour precedent ont ete revoques par le rejeu : on repart d'une
# autorisation propre, ce qui verifie aussi qu'un second passage fonctionne.
r = client.get(url_autorisation())
JETON_FORM = re.search(r'name="jeton_formulaire" value="([^"]+)"', r.text).group(1)
CODE = re.search(r"[?&]code=([^&]+)", poster_decision().headers["location"]).group(1)
jetons = poster_jeton().json()
ACCES, RAFRAICHIR = jetons["access_token"], jetons["refresh_token"]

r = client.post("/mcp", headers={"Authorization": f"Bearer {ACCES}"},
                json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
                      "params": {"protocolVersion": "2025-06-18"}})
verifier("le jeton OAuth ouvre le protocole", r.status_code, 200)
verifier("le serveur repond bien un resultat MCP",
         r.json()["result"]["protocolVersion"], "2025-06-18")

verifier("un jeton inconnu reste un 401",
         client.post("/mcp", headers={"Authorization": "Bearer mcpt_faux"},
                     json={"jsonrpc": "2.0", "id": 1, "method": "initialize"}).status_code, 401)

with get_db() as conn:
    vu = conn.execute(
        "SELECT user_email FROM mcp_oauth_tokens WHERE revoked_at IS NULL ORDER BY id DESC LIMIT 1"
    ).fetchone()["user_email"]
verifier("le jeton nomme l'utilisateur, pas une etiquette", vu, "direction@sifa.test")


# ─── 7. Rafraichissement ────────────────────────────────────────────

print("\n7. Rafraichissement")
r = client.post("/oauth/token", data={"grant_type": "refresh_token",
                                      "client_id": CLIENT_ID, "refresh_token": RAFRAICHIR})
verifier("le rafraichissement donne un nouveau jeton", r.status_code, 200)
NOUVEAU = r.json()
verifier("le jeton d'acces a change", NOUVEAU["access_token"] != ACCES, True)
verifier("l'ancien jeton de rafraichissement est mort",
         client.post("/oauth/token", data={"grant_type": "refresh_token",
                                           "client_id": CLIENT_ID,
                                           "refresh_token": RAFRAICHIR}).json()["error"],
         "invalid_grant")
verifier("l'ancien jeton d'acces ne passe plus",
         client.post("/mcp", headers={"Authorization": f"Bearer {ACCES}"},
                     json={"jsonrpc": "2.0", "id": 1, "method": "initialize"}).status_code, 401)

client.post("/oauth/revoke", data={"token": NOUVEAU["access_token"]})
verifier("un jeton revoque ne passe plus",
         client.post("/mcp", headers={"Authorization": f"Bearer {NOUVEAU['access_token']}"},
                     json={"jsonrpc": "2.0", "id": 1, "method": "initialize"}).status_code, 401)
verifier("revoquer un jeton inconnu repond quand meme 200",
         client.post("/oauth/revoke", data={"token": "mcpt_jamais_vu"}).status_code, 200)


# ─── Verdict ────────────────────────────────────────────────────────

print("\n" + "=" * 62)
if FAIL:
    print(f"{len(FAIL)} echec(s) :")
    for f in FAIL:
        print(f"  - {f}")
    sys.exit(1)
print("Tous les cas passent.")
