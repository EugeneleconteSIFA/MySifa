"""
MyQualité — questionnaire EUDR envoyé aux fournisseurs.

Le circuit : l'onglet EUDR envoie à chaque fournisseur choisi un email (anglais)
avec un lien personnel ; le fournisseur répond sans compte ; la réponse arrive
en base et la personne qui a envoyé la demande est prévenue.

Ce que ce test verrouille :

- l'envoi crée une demande avec un jeton, et une relance réutilise ce jeton ;
- la page publique s'ouvre avec le jeton, un jeton inconnu donne 404 ;
- l'ouverture par le fournisseur fait passer la demande en « ouverte » ;
- une réponse sans rôle ou sans email est refusée, un choix inconnu aussi ;
- une réponse valide passe le fournisseur en « répondu », garde l'historique,
  et prévient l'auteur de la demande ;
- l'API publique pré-remplit la réponse précédente sans exposer l'IP.

Lancer : python3 tests/test_qualite_eudr.py
"""

import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

_TMP = tempfile.mkdtemp(prefix="mysifa_eudr_")
os.environ["DB_PATH"] = os.path.join(_TMP, "test.db")

import database  # noqa: E402,F401  — toujours avant tout app.* (cf. CLAUDE.md)
from database import get_db  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.routers.qualite_eudr as r_eudr  # noqa: E402

ECHECS = []


def check(label, obtenu, attendu=True):
    ok = obtenu == attendu
    print(("ok   " if ok else "KO   ") + label.ljust(64)
          + ("" if ok else f"{obtenu!r}   attendu {attendu!r}"))
    if not ok:
        ECHECS.append(label)


USER = {"id": 1, "email": "qualite@exemple.test", "nom": "Jeanne Qualité", "role": "direction"}
ENVOIS = []


def faux_send_email(to, subject, html_body, reply_to=None, cc=None, attachments=None, from_upn=None):
    ENVOIS.append({"to": to, "subject": subject, "html": html_body, "from": from_upn})
    return True


r_eudr._require_qualite_access = lambda request: USER
r_eudr._require_qualite_view = lambda request: USER
r_eudr._visiteur_interne = lambda request: False
r_eudr.send_email = faux_send_email
r_eudr.log_action = lambda **kw: None

app = FastAPI()
app.include_router(r_eudr.router)
app.include_router(r_eudr.router_html)
app.include_router(r_eudr.router_api)
client = TestClient(app)

with get_db() as conn:
    cur = conn.execute("INSERT INTO fournisseurs_fsc (nom, pays) VALUES ('Papeterie Test', 'DE')")
    FID = cur.lastrowid
    conn.commit()


def ligne():
    r = client.get("/api/qualite/eudr/fournisseurs")
    return next(f for f in r.json()["fournisseurs"] if f["id"] == FID)


check("fournisseur listé, jamais sollicité", ligne()["statut"], "jamais")

r = client.post("/api/qualite/eudr/demander",
                json={"envois": [{"fournisseur_id": FID, "emails": ["achat@papeterie.test"]}]})
check("envoi accepté", r.status_code, 200)
check("un email parti", len(ENVOIS), 1)
check("expéditeur = la personne qui clique", ENVOIS[0]["from"], USER["email"])
check("email en anglais", "EUDR — information requested" in ENVOIS[0]["subject"], True)
check("statut envoyé", ligne()["statut"], "envoyee")

with get_db() as conn:
    TOKEN = conn.execute("SELECT token FROM eudr_demandes WHERE fournisseur_id=?", (FID,)).fetchone()[0]
check("lien du questionnaire dans l'email", f"/portail/eudr/{TOKEN}" in ENVOIS[0]["html"], True)

client.post("/api/qualite/eudr/demander",
            json={"envois": [{"fournisseur_id": FID, "emails": ["ACHAT@papeterie.test"]}]})
with get_db() as conn:
    n = conn.execute("SELECT COUNT(*), MAX(nb_envois) FROM eudr_demandes WHERE fournisseur_id=?", (FID,)).fetchone()
check("relance : même demande, même jeton", (n[0], n[1]), (1, 2))
check("relance signalée dans le sujet", ENVOIS[1]["subject"].startswith("Reminder"), True)

check("jeton inconnu : 404", client.get("/portail/eudr/inconnu").status_code, 404)
r = client.get(f"/portail/eudr/{TOKEN}")
check("page publique servie", r.status_code, 200)
check("statut ouvert après visite", ligne()["statut"], "ouverte")

r = client.get(f"/api/portail/eudr/{TOKEN}")
check("API publique : nom du fournisseur", r.json()["fournisseur"], "Papeterie Test")
check("API publique : choix en anglais", r.json()["choix"]["role"]["non_concerne"], "Not concerned")

base = {"repondant_nom": "Hans", "repondant_email": "hans@papeterie.test", "role": "operateur",
        "perimetre": "oui", "transmission": "bl", "codes_nc": "4810 92", "etablissement": "eu"}
check("réponse sans rôle refusée",
      client.post(f"/api/portail/eudr/{TOKEN}", json={**base, "role": ""}).status_code, 400)
check("réponse sans email refusée",
      client.post(f"/api/portail/eudr/{TOKEN}", json={**base, "repondant_email": "x"}).status_code, 400)
check("choix inconnu refusé",
      client.post(f"/api/portail/eudr/{TOKEN}", json={**base, "perimetre": "peut-etre"}).status_code, 400)

avant = len(ENVOIS)
r = client.post(f"/api/portail/eudr/{TOKEN}", json=base)
check("réponse valide acceptée", r.status_code, 200)
check("auteur de la demande prévenu", ENVOIS[avant]["to"] if len(ENVOIS) > avant else None, USER["email"])
l = ligne()
check("statut répondu", l["statut"], "repondue")
check("libellé français du rôle", l["reponse"]["libelles"]["role"], "Opérateur — dépose les DDS")
check("IP non exposée dans la liste", "ip" in l["reponse"], False)

client.post(f"/api/portail/eudr/{TOKEN}", json={**base, "role": "aval"})
r = client.get(f"/api/qualite/eudr/fournisseurs/{FID}/reponses")
check("historique conservé, plus récente d'abord",
      [x["role"] for x in r.json()["reponses"]], ["aval", "operateur"])
r = client.get(f"/api/portail/eudr/{TOKEN}")
check("pré-remplissage avec la dernière réponse", r.json()["precedente"]["role"], "aval")
check("pré-remplissage sans IP", "ip" in r.json()["precedente"], False)

print()
if ECHECS:
    print(f"{len(ECHECS)} échec(s)")
    sys.exit(1)
print("Tous les contrôles passent.")
