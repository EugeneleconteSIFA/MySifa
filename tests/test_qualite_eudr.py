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
check("sans catégorie : pas fournisseur de bobines", ligne()["bobines"], False)
with get_db() as conn:
    conn.execute("UPDATE fournisseurs_fsc SET categories='[\"complexe\"]' WHERE id=?", (FID,))
    conn.commit()
check("catégorie complexe : fournisseur de bobines", ligne()["bobines"], True)

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
check("API publique : choix en anglais", r.json()["choix"]["en"]["role"]["non_concerne"], "Not concerned")
check("API publique : choix en espagnol", r.json()["choix"]["es"]["role"]["non_concerne"], "No afectado")
check("langue par défaut de la demande : anglais", r.json()["langue"], "en")

# Langues : un second fournisseur sollicité en espagnol.
with get_db() as conn:
    FID2 = conn.execute("INSERT INTO fournisseurs_fsc (nom, pays) VALUES ('Papelera Test', 'ES')").lastrowid
    conn.execute("INSERT INTO fournisseur_contacts (fournisseur_id, nom, emails, langue, is_principal, actif, created_at)"
                 " VALUES (?, 'Ana', '[\"ana@papelera.test\"]', 'es', 1, 1, '2026-10-13T08:00:00')", (FID2,))
    conn.commit()
l2 = next(f for f in client.get("/api/qualite/eudr/fournisseurs").json()["fournisseurs"] if f["id"] == FID2)
check("langue proposée = langue du contact", l2["langue"], "es")
n_av = len(ENVOIS)
client.post("/api/qualite/eudr/demander",
            json={"envois": [{"fournisseur_id": FID2, "emails": ["ana@papelera.test"], "langue": "es"}]})
check("email en espagnol", ENVOIS[n_av]["subject"].startswith("EUDR — información solicitada"), True)
check("lien ouvert en espagnol", "?lang=es" in ENVOIS[n_av]["html"], True)
with get_db() as conn:
    TOK2 = conn.execute("SELECT token FROM eudr_demandes WHERE fournisseur_id=?", (FID2,)).fetchone()[0]
check("langue de la demande : espagnol", client.get(f"/api/portail/eudr/{TOK2}").json()["langue"], "es")
client.post(f"/api/portail/eudr/{TOK2}/langue", json={"langue": "fr"})
check("le fournisseur passe en français", client.get(f"/api/portail/eudr/{TOK2}").json()["langue"], "fr")
client.post(f"/api/portail/eudr/{TOK2}/langue", json={"langue": "xx"})
check("langue inconnue : anglais", client.get(f"/api/portail/eudr/{TOK2}").json()["langue"], "en")
client.post(f"/api/portail/eudr/{TOK2}/langue", json={"langue": "fr"})
l2 = next(f for f in client.get("/api/qualite/eudr/fournisseurs").json()["fournisseurs"] if f["id"] == FID2)
check("relance proposée dans la langue choisie", l2["langue"], "fr")
n_av = len(ENVOIS)
client.post("/api/qualite/eudr/demander",
            json={"envois": [{"fournisseur_id": FID2, "emails": ["ana@papelera.test"], "langue": l2["langue"]}]})
check("relance en français", ENVOIS[n_av]["subject"], "Relance — EUDR — informations demandées par SIFA")

base = {"repondant_societe": "Papeterie Test GmbH", "repondant_nom": "Hans", "repondant_email": "hans@papeterie.test", "role": "operateur",
        "perimetre": "oui", "transmission": "bl", "codes_nc": "4810 92", "etablissement": "eu"}
check("réponse sans rôle refusée",
      client.post(f"/api/portail/eudr/{TOKEN}", json={**base, "role": ""}).status_code, 400)
check("réponse sans société refusée",
      client.post(f"/api/portail/eudr/{TOKEN}", json={**base, "repondant_societe": ""}).status_code, 400)
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

# Aperçu du questionnaire depuis MyQualité : données factices, aucune écriture.
with get_db() as conn:
    avant_dem = conn.execute("SELECT COUNT(*) FROM eudr_demandes").fetchone()[0]
r = client.get("/qualite/eudr/apercu?lang=es")
check("aperçu servi", r.status_code, 200)
check("aperçu : mode aperçu actif", '"fournisseur": "Exemple fournisseur"' in r.text, True)
check("aperçu : langue demandée", '"langue": "es"' in r.text, True)
with get_db() as conn:
    check("aperçu : aucune demande créée",
          conn.execute("SELECT COUNT(*) FROM eudr_demandes").fetchone()[0], avant_dem)
check("page fournisseur : pas en mode aperçu", "const APERCU = null;" in client.get(f"/portail/eudr/{TOKEN}").text, True)

# Destinataire retiré : son lien ne fonctionne plus.
with get_db() as conn:
    DID = conn.execute("SELECT id FROM eudr_demandes WHERE token=?", (TOKEN,)).fetchone()[0]
check("retrait accepté", client.post(f"/api/qualite/eudr/demandes/{DID}/annuler").status_code, 200)
check("lien retiré : formulaire invalide", client.get(f"/portail/eudr/{TOKEN}").status_code, 404)
check("retrait en double : 404", client.post(f"/api/qualite/eudr/demandes/{DID}/annuler").status_code, 404)
check("réponses conservées après retrait", ligne()["statut"], "repondue")

# Saisie manuelle (réponse reçue par courrier), avec pièce jointe.
import app.routers.qualite_eudr as _re  # noqa: E402
_re.EUDR_PIECES_DIR = os.path.join(_TMP, "pieces")
with get_db() as conn:
    FID3 = conn.execute("INSERT INTO fournisseurs_fsc (nom, pays) VALUES ('Distributeur Test', 'FR')").lastrowid
    conn.commit()
check("saisie sans commentaire refusée",
      client.post(f"/api/qualite/eudr/fournisseurs/{FID3}/saisie", data={"role": "aval"}).status_code, 400)
check("pièce exécutable refusée",
      client.post(f"/api/qualite/eudr/fournisseurs/{FID3}/saisie", data={"commentaire": "x"},
                  files={"piece": ("a.html", b"<script>", "text/html")}).status_code, 400)
r = client.post(f"/api/qualite/eudr/fournisseurs/{FID3}/saisie",
                data={"role": "aval", "commentaire": "Courrier du 13/10 : troisième acteur."},
                files={"piece": ("courrier avery.pdf", b"%PDF-1.4 test", "application/pdf")})
check("saisie manuelle acceptée", r.status_code, 200)
l3 = next(f for f in r.json()["fournisseurs"] if f["id"] == FID3)
check("saisie manuelle : statut répondu", l3["statut"], "repondue")
check("saisie manuelle : source", l3["reponse"]["source"], "manuel")
check("saisie manuelle : auteur", l3["reponse"]["saisi_par"], USER["email"])
check("saisie manuelle : aucun destinataire affiché", l3["demandes"], [])
r = client.get(f"/api/qualite/eudr/reponses/{l3['reponse']['id']}/piece")
check("pièce jointe servie", (r.status_code, r.content), (200, b"%PDF-1.4 test"))
check("pièce PDF ouverte dans le navigateur", r.headers["content-disposition"].startswith("inline"), True)
# Le formulaire fournisseur ne reprend jamais une saisie manuelle (commentaire interne).
with get_db() as conn:
    conn.execute("INSERT INTO eudr_demandes (fournisseur_id, email, token, statut, created_at)"
                 " VALUES (?, 'x@distrib.test', 'tok-manuel', 'envoyee', '2026-10-14T09:00:00')", (FID3,))
    conn.commit()
check("formulaire : pas de préremplissage par la saisie manuelle",
      client.get("/api/portail/eudr/tok-manuel").json()["precedente"], None)

# Questionnaire PDF.
r = client.get(f"/api/qualite/eudr/questionnaire.pdf?lang=es&fournisseur_id={FID}")
check("PDF servi", (r.status_code, r.content[:5]), (200, b"%PDF-"))
check("PDF : nom de fichier en espagnol", "EUDR_questionnaire_ES" in r.headers["content-disposition"], True)
check("PDF vierge", client.get("/api/qualite/eudr/questionnaire.pdf").status_code, 200)

print()
if ECHECS:
    print(f"{len(ECHECS)} échec(s)")
    sys.exit(1)
print("Tous les contrôles passent.")
