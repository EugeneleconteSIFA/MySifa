"""
MyTools › Parapheur — circuit de signature d'un PDF.

Ce que ce test verrouille, sur une base neuve et sans aucun email réel :

- création : refus sans zone de signature, sans signataire, sur un fichier
  qui n'est pas un PDF ; empreinte SHA-256 de l'original gardée ;
- séquentiel : seul le premier est prévenu ; le suivant l'est à la signature
  du précédent ; un tiers non concerné ne voit pas la demande (403) ;
- externe : lien de l'email vers son Espace SIFA, jeton dans le FRAGMENT,
  seule son empreinte en base, jamais dans une réponse ; jeton exigé en
  en-tête, lié à l'adresse de l'Espace, révoqué après signature, expiré,
  épuisé ; nouveau lien borné par jour ; carte dans le contenu de l'Espace ;
- scellement : PDF final = pages d'origine + certificat, empreintes en base,
  certificat qui cite l'empreinte de l'original, téléchargement en pièce
  jointe ;
- parallèle : tous prévenus d'emblée ; un refus arrête la demande ;
- boucle : relance d'un signataire qui tarde, expiration à l'échéance ;
- géométrie : passage page affichée → espace PDF pour les quatre rotations.

Lancer : python3 tests/test_parapheur.py
"""

import base64
import io
import os
import re
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

_TMP = tempfile.mkdtemp(prefix="mysifa_parapheur_")
os.environ["DB_PATH"] = os.path.join(_TMP, "test.db")
os.environ["PARAPHEUR_DIR"] = os.path.join(_TMP, "parapheur")
os.environ["PARAPHEUR_LIENS_PAR_JOUR"] = "2"

import database  # noqa: E402,F401  — toujours avant tout app.* (cf. CLAUDE.md)
from database import get_db  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pypdf import PdfReader  # noqa: E402
from reportlab.pdfgen import canvas as rl_canvas  # noqa: E402

import app.routers.portail_espace as r_espace  # noqa: E402
import app.routers.tools_parapheur as r_ppx  # noqa: E402
from app.services import email_service  # noqa: E402
from app.services import parapheur as svc  # noqa: E402
from app.services import parapheur_pdf as ppdf  # noqa: E402

ECHECS = []


def check(label, obtenu, attendu=True):
    ok = obtenu == attendu
    print(("ok   " if ok else "KO   ") + label.ljust(70) + ("" if ok else f"{obtenu!r}   attendu {attendu!r}"))
    if not ok:
        ECHECS.append(label)


# ── Environnement : emails simulés, session simulée ─────────────────────
ENVOIS = []


def faux_send_email(to, subject, html_body, reply_to=None, cc=None, attachments=None, from_upn=None):
    ENVOIS.append({"to": to, "subject": subject, "html": html_body})
    return True


email_service.send_email = faux_send_email
JOURNAL = []
r_ppx.log_action = lambda **kw: JOURNAL.append(kw)
r_espace.log_action = lambda **kw: None
r_ppx._visiteur_interne = lambda request: False
r_espace._visiteur_interne = lambda request: False

with get_db() as conn:
    def _user(nom, email, role):
        cur = conn.execute(
            "INSERT INTO users (nom, email, role, actif, password_hash, created_at) VALUES (?, ?, ?, 1, 'x', '2026-10-22T08:00:00')", (nom, email, role))
        return {"id": cur.lastrowid, "nom": nom, "email": email, "role": role}
    try:
        AUTEUR = _user("Jeanne Émettrice", "jeanne@exemple.test", "direction")
        INTERNE = _user("Paul Interne", "paul@exemple.test", "fabrication")
        TIERS = _user("Zoé Tiers", "zoe@exemple.test", "fabrication")
    except Exception:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        raise SystemExit(f"Table users inattendue : {cols}")
    conn.commit()

COURANT = {"user": AUTEUR}
r_ppx.get_current_user = lambda request: COURANT["user"]

app = FastAPI()
app.include_router(r_ppx.router)
app.include_router(r_ppx.router_espace)
app.include_router(r_espace.router_api)
client = TestClient(app)


def pdf_test(pages=2) -> bytes:
    b = io.BytesIO()
    c = rl_canvas.Canvas(b, pagesize=(595, 842))
    for i in range(pages):
        c.drawString(72, 760, f"Contrat de test — page {i + 1}")
        c.showPage()
    c.save()
    return b.getvalue()


def png_test() -> str:
    from PIL import Image
    im = Image.new("RGBA", (120, 40), (0, 0, 0, 0))
    for x in range(10, 110):
        im.putpixel((x, 20 + (x % 7)), (20, 20, 30, 255))
    b = io.BytesIO()
    im.save(b, "PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


PDF = pdf_test()
SIG = png_test()


def creer(donnees, octets=PDF, nom="contrat.pdf"):
    import json
    return client.post("/api/tools/parapheur", files={"fichier": (nom, octets, "application/pdf")},
                       data={"donnees": json.dumps(donnees)})


def zone(i, page=1, type_="signature", y=0.7):
    return {"signataire": i, "page": page, "type": type_, "x": 0.1, "y": y, "w": 0.3, "h": 0.08}


SIGNATAIRES = [{"type": "interne", "user_id": INTERNE["id"]},
               {"type": "externe", "nom": "Marc Client", "email": "Marc@Client.test", "organisation": "Client SA"}]

# ── Création : refus ────────────────────────────────────────────────────
r = creer({"titre": "Contrat", "signataires": SIGNATAIRES, "zones": [zone(0)]})
check("refus sans zone de signature pour chaque signataire", r.status_code, 400)
r = creer({"titre": "Contrat", "signataires": [], "zones": []})
check("refus sans signataire", r.status_code, 400)
r = creer({"titre": "Contrat", "signataires": SIGNATAIRES, "zones": [zone(0), zone(1)]}, octets=b"pas un pdf")
check("refus d'un fichier qui n'est pas un PDF", r.status_code, 400)
r = creer({"titre": "Contrat", "signataires": SIGNATAIRES, "zones": [zone(0, page=9), zone(1)]})
check("refus d'une zone sur une page absente", r.status_code, 400)
COURANT["user"] = dict(TIERS, role="inconnu")
r = creer({"titre": "Contrat", "signataires": SIGNATAIRES, "zones": [zone(0), zone(1)]})
check("refus de création pour un rôle hors ROLES_PARAPHEUR_CREATION", r.status_code, 403)
COURANT["user"] = AUTEUR

# ── Création séquentielle ───────────────────────────────────────────────
ENVOIS.clear()
r = creer({"titre": "Contrat cadre", "message": "Merci de signer.", "mode": "sequentiel", "relance_jours": 2,
           "signataires": SIGNATAIRES,
           "zones": [zone(0), zone(0, type_="date", y=0.8), zone(1, page=2), zone(1, page=1, type_="paraphe", y=0.9)]})
check("création séquentielle acceptée", r.status_code, 200)
DID = r.json()["id"]
check("un seul prévenu au départ (le premier)", [e["to"] for e in ENVOIS], ["paul@exemple.test"])
check("email interne : lien MyTools avec signer=1", "outil=parapheur&amp;demande=%d&amp;signer=1" % DID in ENVOIS[0]["html"]
      or f"outil=parapheur&demande={DID}&signer=1" in ENVOIS[0]["html"], True)
with get_db() as conn:
    d = svc.demande(conn, DID)
    sigs = svc.signataires(conn, DID)
check("empreinte SHA-256 de l'original gardée", d["sha256_original"], svc.sha256(PDF))
check("fichier d'origine hors de la base, sur disque", os.path.isfile(os.path.join(os.environ["PARAPHEUR_DIR"], d["fichier_original"])))
check("statuts initiaux", [s["statut"] for s in sigs], ["a_signer", "attente"])
check("email externe normalisé en minuscules", sigs[1]["email"], "marc@client.test")
check("tâche créée pour le signataire interne", bool(sigs[0]["tache_id"]))
check("création journalisée (log_action CREATE)", JOURNAL[-1]["action"], "CREATE")

r = client.get("/api/tools/parapheur?statut=en_cours")
check("liste de l'émetteur : 1 en cours", r.json()["compteurs"]["en_cours"], 1)
COURANT["user"] = INTERNE
r = client.get("/api/tools/parapheur?statut=a_signer")
check("liste du signataire : 1 à signer", (r.json()["compteurs"]["a_signer"], len(r.json()["demandes"])), (1, 1))
r = client.get(f"/api/tools/parapheur/{DID}")
check("détail : le signataire peut signer", r.json()["moi"]["peut_signer"], True)
check("détail du signataire : pas d'historique ni d'IP", (r.json()["evenements"], "ip" in r.json()["signataires"][0]), ([], False))
COURANT["user"] = TIERS
check("un tiers ne voit pas la demande", client.get(f"/api/tools/parapheur/{DID}").status_code, 403)
check("un tiers ne télécharge pas l'original", client.get(f"/api/tools/parapheur/{DID}/document").status_code, 403)
check("un tiers ne signe pas", client.post(f"/api/tools/parapheur/{DID}/signer", json={"signature": SIG}).status_code, 403)
COURANT["user"] = AUTEUR
r = client.get(f"/api/tools/parapheur/{DID}/document")
check("original en pièce jointe", (r.status_code, r.headers["content-disposition"].startswith("attachment")), (200, True))

with get_db() as conn:
    check("externe pas encore prévenu : rien dans son Espace", svc.elements_espace(conn, "marc@client.test"), [])

# ── Signature interne → l'externe est prévenu ──────────────────────────
ENVOIS.clear()
COURANT["user"] = INTERNE
r = client.post(f"/api/tools/parapheur/{DID}/signer", json={"signature": "data:image/png;base64,AAAA"})
check("signature non PNG refusée", r.status_code, 400)
r = client.post(f"/api/tools/parapheur/{DID}/signer", json={"signature": SIG, "mode": "dessin"})
check("signature interne enregistrée", (r.status_code, r.json().get("termine")), (200, False))
check("signer deux fois : refusé", client.post(f"/api/tools/parapheur/{DID}/signer", json={"signature": SIG}).status_code, 409)
COURANT["user"] = AUTEUR
check("le second est prévenu", [e["to"] for e in ENVOIS], ["marc@client.test"])
lien = re.search(r'href="([^"]+#signer=[^"]+)"', ENVOIS[0]["html"])
check("lien de l'email : Espace SIFA + jeton dans le fragment", bool(lien and "/portail/" in lien.group(1)))
URL = lien.group(1)
TOKEN_ESPACE = re.search(r"/portail/([^?#]+)", URL).group(1)
JETON = URL.split("#signer=", 1)[1]
check("aucun jeton dans la query de l'adresse", "?" not in URL.split("#")[0])
with get_db() as conn:
    j = conn.execute("SELECT * FROM parapheur_jetons").fetchall()
    taches = conn.execute("SELECT statut FROM taches WHERE id = ?", (sigs[0]["tache_id"],)).fetchone()
check("jeton : seule l'empreinte est en base", (len(j), j[0]["jeton_hash"] != JETON, JETON not in str([dict(x) for x in j])), (1, True, True))
check("tâche du signataire interne terminée", taches["statut"], "termine")

API_ESP = f"/api/portail/espace/{TOKEN_ESPACE}"
r = client.get(API_ESP)
cartes = [e for e in r.json()["a_traiter"] if e["module"] == "signature"]
check("carte « à signer » dans l'Espace", len(cartes), 1)
SID_EXT = cartes[0]["id"]
check("signature sans jeton : refusée", client.get(API_ESP + "/signature").status_code, 404)
check("jeton faux : refusé", client.get(API_ESP + "/signature", headers={"X-Parapheur-Jeton": "x" * 43}).status_code, 404)
with get_db() as conn:
    from app.services import portail_espace as esp_svc
    autre = esp_svc.espace_pour(conn, "autre@exemple.test", "Autre")
    conn.commit()
check("bon jeton dans l'Espace d'un autre : refusé",
      client.get(f"/api/portail/espace/{autre['token']}/signature", headers={"X-Parapheur-Jeton": JETON}).status_code, 404)
H = {"X-Parapheur-Jeton": JETON}
r = client.get(API_ESP + "/signature", headers=H)
check("ouverture avec le jeton", r.status_code, 200)
check("l'externe ne reçoit que ses zones", sorted(z["type"] for z in r.json()["zones"]), ["paraphe", "signature"])
check("aucune réponse ne contient le jeton", JETON in r.text, False)
check("document servi au signataire externe", client.get(API_ESP + "/signature/document", headers=H).content[:4], b"%PDF")
with get_db() as conn:
    s_ext = svc.signataire(conn, SID_EXT)
    us = conn.execute("SELECT usages FROM parapheur_jetons").fetchone()["usages"]
check("ouverture notée (statut « ouvert »)", (s_ext["statut"], bool(s_ext["ouvert_le"])), ("ouvert", True))
check("consultation décomptée sur le jeton", us, 1)

r = client.post(API_ESP + "/signature/signer", headers=H, json={"signature": SIG, "nom": "Marc Client"})
check("signature externe sans consentement : refusée", r.status_code, 400)
ENVOIS.clear()
r = client.post(API_ESP + "/signature/signer", headers=H,
                json={"signature": SIG, "paraphe": SIG, "mode": "texte", "nom": "Marc Client", "consentement": True})
check("signature externe : demande terminée", (r.status_code, r.json().get("termine")), (200, True))
check("jeton révoqué après signature (410)", client.get(API_ESP + "/signature", headers=H).status_code, 410)

# ── Scellement ──────────────────────────────────────────────────────────
with get_db() as conn:
    d = svc.demande(conn, DID)
    ev = [e["type"] for e in svc.evenements(conn, DID)]
check("demande signée", d["statut"], "signee")
final = open(os.path.join(os.environ["PARAPHEUR_DIR"], d["fichier_final"]), "rb").read()
check("empreinte du fichier final en base", d["sha256_final"], svc.sha256(final))
lect = PdfReader(io.BytesIO(final))
check("PDF final = 2 pages d'origine + certificat", len(lect.pages) >= 3)
texte_cert = " ".join(p.extract_text() or "" for p in lect.pages[2:]).replace("\n", "")
check("certificat : empreinte de l'original", d["sha256_original"][:32] in texte_cert.replace(" ", ""))
check("certificat : empreinte du document signé", d["sha256_signe"][:32] in texte_cert.replace(" ", ""))
check("certificat : nom du signataire externe", "Marc Client" in texte_cert)
check("historique : scellement noté", "scelle" in ev)
check("fin : émetteur et signataires prévenus",
      sorted(set(e["to"] for e in ENVOIS)), ["jeanne@exemple.test", "marc@client.test", "paul@exemple.test"])
r = client.get(f"/api/tools/parapheur/{DID}/final")
check("document signé en pièce jointe (MyTools)", (r.status_code, r.headers["content-disposition"].startswith("attachment")), (200, True))
r = client.get(f"{API_ESP}/signatures/{SID_EXT}/final")
check("document signé téléchargeable depuis l'Espace", (r.status_code, r.content[:4]), (200, b"%PDF"))
check("Espace d'un autre : pas de téléchargement", client.get(f"/api/portail/espace/{autre['token']}/signatures/{SID_EXT}/final").status_code, 404)
r = client.get(f"/api/tools/parapheur/{DID}")
check("détail : pas de fichier interne exposé", ("fichier_original" in r.json()["demande"], "signature_png" in r.text), (False, False))

# ── Parallèle + refus ───────────────────────────────────────────────────
ENVOIS.clear()
r = creer({"titre": "Avenant", "mode": "parallele",
           "signataires": [{"type": "externe", "nom": "Ana Externe", "email": "ana@ext.test"},
                           {"type": "interne", "user_id": INTERNE["id"]}],
           "zones": [zone(0), zone(1, y=0.5)]})
DID2 = r.json()["id"]
check("parallèle : tous prévenus d'emblée", sorted(e["to"] for e in ENVOIS), ["ana@ext.test", "paul@exemple.test"])
COURANT["user"] = INTERNE
check("refus sans motif : refusé", client.post(f"/api/tools/parapheur/{DID2}/refuser", json={"motif": ""}).status_code, 400)
check("refus motivé", client.post(f"/api/tools/parapheur/{DID2}/refuser", json={"motif": "Montant erroné"}).status_code, 200)
COURANT["user"] = AUTEUR
with get_db() as conn:
    d2 = svc.demande(conn, DID2)
    s2 = svc.signataires(conn, DID2)
    actifs = conn.execute(
        """SELECT COUNT(*) FROM parapheur_jetons j JOIN parapheur_signataires s ON s.id = j.signataire_id
            WHERE s.demande_id = ? AND j.revoque_le IS NULL""", (DID2,)).fetchone()[0]
check("demande refusée, motif gardé", (d2["statut"], "Montant erroné" in (d2["motif_fin"] or "")), ("refusee", True))
check("l'autre signataire passe « annulé »", sorted(s["statut"] for s in s2), ["annule", "refuse"])
check("jetons de la demande révoqués", actifs, 0)

# ── Liens : expiration, renvoi borné ────────────────────────────────────
ENVOIS.clear()
r = creer({"titre": "Bon de commande", "signataires": [{"type": "externe", "nom": "Léa", "email": "lea@ext.test"}],
           "zones": [zone(0)]})
DID3 = r.json()["id"]
url3 = re.search(r'href="([^"]+#signer=[^"]+)"', ENVOIS[0]["html"]).group(1)
tok3, jet3 = re.search(r"/portail/([^?#]+)", url3).group(1), url3.split("#signer=", 1)[1]
with get_db() as conn:
    conn.execute("UPDATE parapheur_jetons SET expire_le = '2000-01-01T00:00:00' WHERE revoque_le IS NULL")
    sid3 = svc.signataires(conn, DID3)[0]["id"]
    conn.commit()
r = client.get(f"/api/portail/espace/{tok3}/signature", headers={"X-Parapheur-Jeton": jet3})
check("jeton expiré : 410 avec raison", (r.status_code, r.json()["detail"]["raison"]), (410, "expire"))
ENVOIS.clear()
check("nouveau lien depuis l'Espace", client.post(f"/api/portail/espace/{tok3}/signatures/{sid3}/lien").status_code, 200)
check("nouveau lien : email parti", len(ENVOIS), 1)
check("second lien du jour", client.post(f"/api/portail/espace/{tok3}/signatures/{sid3}/lien").status_code, 200)
check("au-delà de la limite du jour : 429", client.post(f"/api/portail/espace/{tok3}/signatures/{sid3}/lien").status_code, 429)
jet4 = re.search(r"#signer=([^\"]+)\"", ENVOIS[-1]["html"]).group(1)
with get_db() as conn:
    conn.execute("UPDATE parapheur_jetons SET usages = usages_max WHERE jeton_hash = ?", (svc._empreinte_jeton(jet4),))
    conn.commit()
r = client.get(f"/api/portail/espace/{tok3}/signature", headers={"X-Parapheur-Jeton": jet4})
check("jeton épuisé : 410", (r.status_code, r.json()["detail"]["raison"]), (410, "epuise"))

# ── Relances et échéance (boucle) ───────────────────────────────────────
with get_db() as conn:
    conn.execute("UPDATE parapheur_signataires SET relance_le = '2020-01-01T09:00:00', notifie_le = '2020-01-01T09:00:00' WHERE demande_id = ?", (DID3,))
    conn.commit()
ENVOIS.clear()
res = svc.tour(get_db, force=True)
check("relance automatique d'un signataire qui tarde", res["relances"], 1)
check("relance : objet « Rappel »", ENVOIS and ENVOIS[0]["subject"].startswith("Rappel"), True)
res = svc.tour(get_db, force=True)
check("pas de seconde relance dans la foulée", res["relances"], 0)
COURANT["user"] = AUTEUR
check("relance manuelle par l'émetteur", client.post(f"/api/tools/parapheur/{DID3}/signataires/{sid3}/relancer").status_code, 200)
COURANT["user"] = INTERNE
check("relance manuelle refusée à un non-émetteur", client.post(f"/api/tools/parapheur/{DID3}/signataires/{sid3}/relancer").status_code, 403)
COURANT["user"] = AUTEUR
with get_db() as conn:
    conn.execute("UPDATE parapheur_demandes SET echeance = '2020-01-01' WHERE id = ?", (DID3,))
    conn.commit()
res = svc.tour(get_db, force=True)
with get_db() as conn:
    d3 = svc.demande(conn, DID3)
check("échéance dépassée : demande expirée", (res["expirees"], d3["statut"]), (1, "expiree"))

# ── Annulation ──────────────────────────────────────────────────────────
r = creer({"titre": "À annuler", "signataires": [{"type": "interne", "user_id": INTERNE["id"]}], "zones": [zone(0)]})
DID4 = r.json()["id"]
COURANT["user"] = INTERNE
check("annulation refusée au signataire", client.post(f"/api/tools/parapheur/{DID4}/annuler", json={}).status_code, 403)
COURANT["user"] = AUTEUR
check("annulation par l'émetteur", client.post(f"/api/tools/parapheur/{DID4}/annuler", json={"motif": "Erreur"}).status_code, 200)
COURANT["user"] = INTERNE
check("signer une demande annulée : refusé", client.post(f"/api/tools/parapheur/{DID4}/signer", json={"signature": SIG}).status_code, 409)
COURANT["user"] = AUTEUR

# ── Géométrie ───────────────────────────────────────────────────────────
box = [0, 0, 600, 800]
check("rotation 0 : haut-gauche affiché → (x0, y1)", ppdf.vers_pdf(box, 0, 0, 0), (0, 800))
check("rotation 90", ppdf.vers_pdf(box, 90, 10, 20), (20, 10))
check("rotation 180", ppdf.vers_pdf(box, 180, 10, 20), (590, 20))
check("rotation 270", ppdf.vers_pdf(box, 270, 10, 20), (580, 790))
try:
    ppdf.niveau("qualifiee")
    check("niveau « qualifiee » non implémenté", False)
except ValueError:
    check("niveau « qualifiee » non implémenté", True)



def test_parapheur_circuit():
    """Point d'entrée pytest : les contrôles ont tourné à l'import."""
    assert not ECHECS, ECHECS


if __name__ == "__main__":
    print()
    if ECHECS:
        print(f"{len(ECHECS)} échec(s).")
        sys.exit(1)
    print("Parapheur : tout est vert.")
