"""
MyExpe — taxe carburant saisie par le transporteur sur son portail.

Le circuit : l'onglet Taxe carburant envoie a chaque transporteur un email
(meme habillage que la demande de tarif) qui ouvre son espace ; il y saisit
son taux, qui s'ecrit sur sa fiche ; la personne qui a envoye la demande
recoit un email de confirmation, la boite du service en copie.

Ce que ce test verrouille :

- l'email part dans la langue de la fiche, vers chaque adresse de contact,
  avec un lien portail qui ouvre le bloc taxe carburant (#carburant) ;
- apres l'envoi, le transporteur est « en attente » ; apres sa saisie, « a
  jour » — et la valeur est celle qu'applique le comparateur ;
- la saisie accepte la virgule, refuse hors [0, 100] ;
- un lien portail sans fiche transporteur ne peut rien ecrire ;
- la fiche fait foi, pas le rattachement du compte portail : un compte
  rattache a Coquelle par un ancien devis, dont l'adresse figure sur une
  autre fiche, ne voit ni ne modifie la taxe de Coquelle (bug du 30/09/2026) ;
- une adresse presente sur deux fiches voit deux blocs et doit designer
  celui qu'elle modifie ;
- la confirmation va a l'auteur de la demande, le service en copie ;
- la fiche transporteur n'historise la taxe QUE si elle change : corriger un
  telephone ne doit pas dater la taxe du jour.

Lancer : python3 tests/test_expe_taxe_carburant_portail.py
"""

import json
import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

_TMP = tempfile.mkdtemp(prefix="mysifa_carb_")
os.environ["DB_PATH"] = os.path.join(_TMP, "test.db")

import database  # noqa: E402,F401  — toujours avant tout app.* (cf. CLAUDE.md)
from database import get_db  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.routers.expe_carburant as r_carb  # noqa: E402
import app.routers.expe_departs as r_dep  # noqa: E402
import app.routers.expe_portail as r_portail  # noqa: E402

ECHECS = []


def check(label, obtenu, attendu=True):
    ok = obtenu == attendu
    print(("ok   " if ok else "KO   ") + label.ljust(64)
          + ("" if ok else f"{obtenu!r}   attendu {attendu!r}"))
    if not ok:
        ECHECS.append(label)


USER = {"id": 1, "email": "demandeur@exemple.test", "nom": "Jeanne Demandeur", "role": "direction"}
ENVOIS = []


def faux_send_email(to, subject, html_body, reply_to=None, cc=None, attachments=None, from_upn=None):
    ENVOIS.append({"to": to, "subject": subject, "html": html_body, "cc": cc, "from": from_upn})
    return True


r_carb._require_expe = lambda request: USER
r_carb._require_expe_write = lambda request: USER
r_carb.send_email = faux_send_email
r_carb.log_action = lambda **kw: None
r_dep._require_expe_write = lambda request: USER
r_dep.log_action = lambda **kw: None
r_portail.send_email = faux_send_email
r_portail.EXPE_DEVIS_FROM = "service@exemple.test"
import app.services.expe_carburant as carb  # noqa: E402

carb.EXPE_DEVIS_FROM = "service@exemple.test"

app = FastAPI()
app.include_router(r_carb.router, prefix="/api/expe")
app.include_router(r_dep.router, prefix="/api/expe")
app.include_router(r_portail.router_api)
client = TestClient(app)

with get_db() as conn:
    conn.execute("DELETE FROM expe_transporteurs")
    cur = conn.execute(
        """INSERT INTO expe_transporteurs (nom, taxe_carburant_pct, contact_emails, langue, actif, created_at)
           VALUES ('Transports Test', 12.8, ?, 'en', 1, '2026-09-01T08:00:00')""",
        (json.dumps(["Resa@Trp.test", "compta@trp.test"]),),
    )
    TID = int(cur.lastrowid)
    conn.execute(
        """INSERT INTO expe_transporteurs (nom, taxe_carburant_pct, contact_emails, langue, actif, created_at)
           VALUES ('Sans Email', 0, '[]', 'fr', 1, '2026-09-01T08:00:00')"""
    )
    conn.execute(
        """INSERT INTO expe_portal_transporteurs (email, token, transporteur_id, created_at, actif)
           VALUES ('prospect@x.test', 'tok-prospect', NULL, '2026-09-01T08:00:00', 1)"""
    )
    # Cas du 30/09/2026 : « Coquelle » (25,6 %) et une fiche « Eugene » dont
    # le seul contact est une adresse dont le compte portail est rattache a
    # Coquelle depuis un ancien devis.
    COQ = int(conn.execute(
        """INSERT INTO expe_transporteurs (nom, taxe_carburant_pct, contact_emails, langue, actif, created_at)
           VALUES ('Coquelle', 25.6, ?, 'fr', 1, '2026-09-01T08:00:00')""",
        (json.dumps(["orlane@coquelle.test"]),),
    ).lastrowid)
    EUG = int(conn.execute(
        """INSERT INTO expe_transporteurs (nom, taxe_carburant_pct, contact_emails, langue, actif, created_at)
           VALUES ('Eugene', 0, ?, 'fr', 1, '2026-09-01T08:00:00')""",
        (json.dumps(["eugene@perso.test"]),),
    ).lastrowid)
    conn.execute(
        """INSERT INTO expe_portal_transporteurs (email, token, transporteur_id, created_at, actif)
           VALUES ('eugene@perso.test', 'tok-eugene', ?, '2026-05-28T16:05:03', 1)""",
        (COQ,),
    )
    conn.commit()

# ── Liste initiale ──
lst = client.get("/api/expe/carburant").json()["transporteurs"]
t = next(x for x in lst if x["id"] == TID)
check("liste : taux de la fiche", t["pct"], 12.8)
check("liste : jamais renseignee avant toute saisie", t["statut"], "jamais")
check("liste : emails normalises", t["emails"], ["resa@trp.test", "compta@trp.test"])

# ── Envoi de la demande ──
sans = next(x for x in lst if x["nom"] == "Sans Email")
r = client.post("/api/expe/carburant/demander", json={"transporteur_ids": [TID, sans["id"]]}).json()
check("demande : envoyee au transporteur", r["envoyes"], ["Transports Test"])
check("demande : sans email signale", r["sans_email"], ["Sans Email"])
check("demande : un email par adresse", len(ENVOIS), 2)
check("demande : expediteur = boite du service", ENVOIS[0]["from"], r_carb.EXPE_DEVIS_FROM)
check("demande : email en anglais (langue de la fiche)", "Fuel surcharge" in ENVOIS[0]["subject"])
check("demande : pas de copie au demandeur", ENVOIS[0]["cc"], None)
with get_db() as conn:
    tok = conn.execute(
        "SELECT token, transporteur_id FROM expe_portal_transporteurs WHERE email='resa@trp.test'"
    ).fetchone()
check("demande : compte portail cree", tok is not None)
check("demande : lien vers le bloc de CE transporteur",
      f"/portail/expe/{tok['token']}?lang=en#carburant-{TID}" in ENVOIS[0]["html"])
t = next(x for x in r["transporteurs"] if x["id"] == TID)
check("demande : statut en attente", t["statut"], "en_attente")
check("demande : auteur memorise", t["demande_par"], USER["email"])
TOKEN = tok["token"]

# ── Portail : lecture ──
d = client.get(f"/api/portail/expe/{TOKEN}").json()
check("portail : un bloc, le bon transporteur", [c["transporteur"] for c in d["carburants"]], ["Transports Test"])
check("portail : bloc en attente", d["carburants"][0]["en_attente"], True)
d2 = client.get("/api/portail/expe/tok-prospect").json()
check("portail : pas de bloc sans fiche transporteur", d2["carburants"], [])

# ── Portail : saisie ──
ENVOIS.clear()
check("saisie : hors bornes refusee", client.post(f"/api/portail/expe/{TOKEN}/carburant", json={"pct": 150}).status_code, 400)
check("saisie : texte refuse", client.post(f"/api/portail/expe/{TOKEN}/carburant", json={"pct": "abc"}).status_code, 400)
check("saisie : lien sans fiche refuse", client.post("/api/portail/expe/tok-prospect/carburant", json={"pct": 10}).status_code, 403)
check("saisie : aucune notification sur un refus", len(ENVOIS), 0)
rs = client.post(f"/api/portail/expe/{TOKEN}/carburant", json={"pct": "13,5"})
check("saisie : acceptee avec virgule", rs.status_code, 200)
check("saisie : bloc a jour", rs.json()["carburants"][0]["en_attente"], False)
with get_db() as conn:
    row = conn.execute(
        "SELECT taxe_carburant_pct, taxe_carburant_maj_source, taxe_carburant_maj_par FROM expe_transporteurs WHERE id=?",
        (TID,),
    ).fetchone()
check("saisie : taux ecrit sur la fiche", row["taxe_carburant_pct"], 13.5)
check("saisie : source portail", row["taxe_carburant_maj_source"], "portail")
check("saisie : auteur = email du compte portail", row["taxe_carburant_maj_par"], "resa@trp.test")
check("confirmation : une seule", len(ENVOIS), 1)
check("confirmation : au demandeur", ENVOIS[0]["to"], USER["email"])
check("confirmation : service en copie", ENVOIS[0]["cc"], ["service@exemple.test"])
check("confirmation : taux dans le sujet", "13,5 %" in ENVOIS[0]["subject"])
t = next(x for x in client.get("/api/expe/carburant").json()["transporteurs"] if x["id"] == TID)
check("liste : a jour apres saisie", t["statut"], "a_jour")

# ── La fiche fait foi, pas le rattachement du compte portail ──
de = client.get("/api/portail/expe/tok-eugene").json()
check("rattachement perime : seul le bloc de la fiche", [c["transporteur"] for c in de["carburants"]], ["Eugene"])
check("rattachement perime : Coquelle refuse",
      client.post("/api/portail/expe/tok-eugene/carburant", json={"transporteur_id": COQ, "pct": 19}).status_code, 403)
check("rattachement perime : saisie sans id -> sa seule fiche",
      client.post("/api/portail/expe/tok-eugene/carburant", json={"pct": 19}).status_code, 200)
with get_db() as conn:
    pcts = {r["id"]: r["taxe_carburant_pct"] for r in conn.execute(
        "SELECT id, taxe_carburant_pct FROM expe_transporteurs WHERE id IN (?,?)", (COQ, EUG))}
check("rattachement perime : Coquelle intacte", pcts[COQ], 25.6)
check("rattachement perime : Eugene mise a jour", pcts[EUG], 19.0)

# ── Une adresse sur deux fiches ──
with get_db() as conn:
    conn.execute("UPDATE expe_transporteurs SET contact_emails=? WHERE id=?",
                 (json.dumps(["orlane@coquelle.test", "eugene@perso.test"]), COQ))
    conn.commit()
dd = client.get("/api/portail/expe/tok-eugene").json()
check("deux fiches : deux blocs", sorted(c["transporteur"] for c in dd["carburants"]), ["Coquelle", "Eugene"])
check("deux fiches : saisie sans id refusee",
      client.post("/api/portail/expe/tok-eugene/carburant", json={"pct": 20}).status_code, 403)
rr = client.post("/api/portail/expe/tok-eugene/carburant", json={"transporteur_id": EUG, "pct": 20})
check("deux fiches : saisie designee acceptee", rr.status_code, 200)
with get_db() as conn:
    check("deux fiches : l'autre fiche intacte",
          conn.execute("SELECT taxe_carburant_pct FROM expe_transporteurs WHERE id=?", (COQ,)).fetchone()[0], 25.6)

# ── Fiche transporteur : seul un changement s'historise ──
def nb_saisies():
    with get_db() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM expe_taxe_carburant_historique WHERE transporteur_id=? AND evenement='saisie'",
            (TID,),
        ).fetchone()[0]

avant = nb_saisies()
client.put(f"/api/expe/transporteurs/{TID}", json={"taxe_carburant_pct": 13.5, "contact_nom": "Paul"})
check("fiche : meme taux, pas d'historique", nb_saisies(), avant)
client.put(f"/api/expe/transporteurs/{TID}", json={"taxe_carburant_pct": 14})
check("fiche : taux change, une ligne", nb_saisies(), avant + 1)
h = client.get(f"/api/expe/carburant/{TID}/historique").json()["historique"]
check("historique : plus recent en tete, manuel", (h[0]["source"], h[0]["pct_avant"], h[0]["pct"]), ("manuel", 13.5, 14.0))
check("historique : la demande y figure", any(e["evenement"] == "demande" for e in h))

print()
if ECHECS:
    print(f"{len(ECHECS)} echec(s)")
    sys.exit(1)
print("Tous les cas passent.")
