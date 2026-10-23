"""
MyTools › Image et BAT — projets enregistrés (app/routers/tools_image.py).

Ce que ce test verrouille, sur une base neuve :

- CRUD : création (image + vignette + réglages), liste, détail avec réglages
  restitués à l'identique, « Enregistrer » qui écrase (et remplace l'image
  d'origine si un fichier est joint, l'ancien fichier effacé), renommage,
  duplication (fichiers recopiés), suppression (fichiers effacés) ;
- droits : un autre utilisateur ne voit ni la liste, ni le détail, ni les
  fichiers d'un projet, et ne peut ni l'écraser, ni le renommer, ni le
  dupliquer, ni le supprimer (404, comme un projet inexistant) ;
- taille : image au-delà de TOOLS_IMAGE_TAILLE_MAX_MO et vignette au-delà de
  TOOLS_IMAGE_VIGNETTE_MAX_KO refusées (413) ; nombre de projets plafonné ;
- types : type lu dans les octets (un PDF ou un HTML déguisé en PNG est
  refusé, 415), jamais dans l'en-tête du navigateur ;
- téléchargement en pièce jointe, nosniff ; fichiers rangés sous
  TOOLS_IMAGE_DIR, hors de UPLOADS_ROOT ;
- journal : chaque écriture appelle log_action, module « tools ».

Lancer : python3 tests/test_tools_image_projets.py
"""

import io
import json
import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

_TMP = tempfile.mkdtemp(prefix="mysifa_tools_image_")
os.environ["DB_PATH"] = os.path.join(_TMP, "test.db")
os.environ["TOOLS_IMAGE_DIR"] = os.path.join(_TMP, "tools_image")
os.environ["TOOLS_IMAGE_TAILLE_MAX_MO"] = "1"
os.environ["TOOLS_IMAGE_VIGNETTE_MAX_KO"] = "20"
os.environ["TOOLS_IMAGE_PROJETS_MAX"] = "4"

import database  # noqa: E402,F401  — toujours avant tout app.* (cf. CLAUDE.md)
from database import get_db  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.routers.tools_image as r_img  # noqa: E402
import config  # noqa: E402

ECHECS = []


def check(label, obtenu, attendu=True):
    ok = obtenu == attendu
    print(("ok   " if ok else "KO   ") + label.ljust(70) + ("" if ok else f"{obtenu!r}   attendu {attendu!r}"))
    if not ok:
        ECHECS.append(label)


JOURNAL = []
r_img.log_action = lambda **kw: JOURNAL.append(kw)

with get_db() as conn:
    def _user(nom, email, role):
        cur = conn.execute(
            "INSERT INTO users (nom, email, role, actif, password_hash, created_at) VALUES (?, ?, ?, 1, 'x', '2026-10-23T08:00:00')",
            (nom, email, role))
        return {"id": cur.lastrowid, "nom": nom, "email": email, "role": role}
    AUTEUR = _user("Jeanne Graphiste", "jeanne@exemple.test", "commercial")
    AUTRE = _user("Paul Voisin", "paul@exemple.test", "fabrication")
    conn.commit()

COURANT = {"user": AUTEUR}
r_img.get_current_user = lambda request: COURANT["user"]

app = FastAPI()
app.include_router(r_img.router)
client = TestClient(app)


def png(w=40, h=20, couleur=(200, 30, 30, 255)) -> bytes:
    from PIL import Image
    im = Image.new("RGBA", (w, h), couleur)
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def jpg(w=40, h=20) -> bytes:
    from PIL import Image
    im = Image.new("RGB", (w, h), (10, 120, 200))
    b = io.BytesIO()
    im.save(b, "JPEG")
    return b.getvalue()


REGLAGES = {"mode": "vectoriser", "r": {"echelle": 2, "bruit": 1, "nettete": 35, "transparent": True, "dpi": 600},
            "v": {"couleurs": 6, "lissage": 1.4, "details": 12, "fond": False}, "comparaison": 30}


def creer(nom="Logo client", fichier=None, vignette=None, reglages=REGLAGES, mime_annonce="image/png"):
    files = {"fichier": ("logo.png", fichier if fichier is not None else png(), mime_annonce)}
    if vignette is not False:
        files["vignette"] = ("v.png", vignette if vignette is not None else png(8, 4), "image/png")
    return client.post("/api/tools/image/projets", files=files,
                       data={"donnees": json.dumps({"nom": nom, "nom_source": "logo", "reglages": reglages})})


def fichiers_disque():
    d = os.environ["TOOLS_IMAGE_DIR"]
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


# ── Emplacement des fichiers ────────────────────────────────────────────
check("TOOLS_IMAGE_DIR lu depuis l'environnement", config.TOOLS_IMAGE_DIR, os.environ["TOOLS_IMAGE_DIR"])
uploads = os.path.realpath(config.UPLOADS_ROOT)
defaut = os.path.realpath(os.path.join(config.DATA_DIR, "tools_image"))
check("dossier par défaut hors de UPLOADS_ROOT", not (defaut + os.sep).startswith(uploads + os.sep) and defaut != uploads)
gi = (RACINE / ".gitignore").read_text(encoding="utf-8")
check("data/tools_image/ ignoré par git", "data/tools_image/" in gi)

# ── Création, liste, détail ─────────────────────────────────────────────
r = creer()
check("création → 200", r.status_code, 200)
P = r.json()
check("création : nom", P["nom"], "Logo client")
check("création : mode", P["mode"], "vectoriser")
check("création : vignette", P["vignette"], True)
check("création : journalisée", JOURNAL[-1]["action"] == "CREATE" and JOURNAL[-1]["module"] == "tools", True)
check("création : deux fichiers sur disque", len(fichiers_disque()), 2)

r = client.get("/api/tools/image/projets")
check("liste → 1 projet", len(r.json()["projets"]), 1)
check("liste sans les réglages", "reglages" in r.json()["projets"][0], False)

r = client.get(f"/api/tools/image/projets/{P['id']}")
check("détail → réglages restitués à l'identique", r.json()["reglages"], REGLAGES)

r = client.get(f"/api/tools/image/projets/{P['id']}/fichier")
check("fichier → 200", r.status_code, 200)
check("fichier : octets d'origine", r.content, png())
check("fichier : type lu dans les octets", r.headers["content-type"], "image/png")
check("fichier : pièce jointe", r.headers["content-disposition"].startswith("attachment"), True)
check("fichier : nosniff", r.headers.get("x-content-type-options"), "nosniff")
r = client.get(f"/api/tools/image/projets/{P['id']}/vignette")
check("vignette → 200 en pièce jointe", (r.status_code, r.headers["content-disposition"].startswith("attachment")), (200, True))

# JPEG annoncé comme PNG : le type retenu est celui des octets.
r = creer(nom="Photo", fichier=jpg(), vignette=False)
check("JPEG annoncé PNG → accepté", r.status_code, 200)
J = r.json()
check("JPEG : type lu dans les octets", J["mime"], "image/jpeg")
check("sans vignette : accepté", J["vignette"], False)
check("sans vignette : vignette → 404", client.get(f"/api/tools/image/projets/{J['id']}/vignette").status_code, 404)

# ── Types refusés ───────────────────────────────────────────────────────
r = creer(fichier=b"%PDF-1.7\n1 0 obj<<>>endobj\n", mime_annonce="image/png")
check("PDF déguisé en PNG → 415", r.status_code, 415)
r = creer(fichier=b"<html><script>alert(1)</script></html>", mime_annonce="image/png")
check("HTML déguisé en PNG → 415", r.status_code, 415)
r = creer(vignette=b"<svg xmlns='http://www.w3.org/2000/svg'/>")
check("vignette SVG → 415", r.status_code, 415)
r = creer(fichier=b"")
check("fichier vide → 400", r.status_code, 400)
r = client.post("/api/tools/image/projets", files={"fichier": ("a.png", png(), "image/png")}, data={"donnees": "pas du json"})
check("données illisibles → 400", r.status_code, 400)
r = creer(reglages={"mode": "ameliorer", "r": "pas un objet"})
check("réglages mal formés → 400", r.status_code, 400)
r = creer(reglages={"mode": "x" * 10, "r": {"k": "y" * 30000}})
check("réglages trop volumineux → 413", r.status_code, 413)
r = creer(reglages={"mode": "pirate", "r": {}})
check("mode inconnu → ramené à « ameliorer »", r.json().get("mode"), "ameliorer")
client.delete(f"/api/tools/image/projets/{r.json()['id']}")

# ── Tailles ─────────────────────────────────────────────────────────────
gros = png() + b"\x00" * (1024 * 1024 + 10)
r = creer(fichier=gros)
check("image > TOOLS_IMAGE_TAILLE_MAX_MO → 413", r.status_code, 413)
r = creer(vignette=png(8, 4) + b"\x00" * (21 * 1024))
check("vignette > TOOLS_IMAGE_VIGNETTE_MAX_KO → 413", r.status_code, 413)
avant = len(fichiers_disque())
check("refus : aucun fichier laissé sur disque", avant, 3)

# ── Enregistrer (écrase) ────────────────────────────────────────────────
NOUV = dict(REGLAGES, mode="ameliorer", r={"echelle": 1, "lum": 20})
ancien_fichier = set(fichiers_disque())
r = client.put(f"/api/tools/image/projets/{P['id']}",
               data={"donnees": json.dumps({"nom": "Logo client v2", "reglages": NOUV})},
               files={"vignette": ("v.png", png(6, 6), "image/png")})
check("enregistrer → 200", r.status_code, 200)
check("enregistrer : nom", r.json()["nom"], "Logo client v2")
check("enregistrer : mode", r.json()["mode"], "ameliorer")
check("enregistrer : réglages écrasés", client.get(f"/api/tools/image/projets/{P['id']}").json()["reglages"], NOUV)
check("enregistrer sans fichier : image d'origine conservée",
      client.get(f"/api/tools/image/projets/{P['id']}/fichier").content, png())
check("enregistrer : ancienne vignette effacée", len(fichiers_disque()), 3)
check("enregistrer : journalisé UPDATE", JOURNAL[-1]["action"], "UPDATE")
autre_img = png(30, 30, (0, 200, 0, 255))
r = client.put(f"/api/tools/image/projets/{P['id']}",
               data={"donnees": json.dumps({"reglages": NOUV})},
               files={"fichier": ("n.png", autre_img, "image/png")})
check("enregistrer avec fichier : image remplacée",
      client.get(f"/api/tools/image/projets/{P['id']}/fichier").content, autre_img)
check("enregistrer avec fichier : ancien fichier effacé", len(fichiers_disque()), 3)
check("enregistrer sans nom : nom gardé", r.json()["nom"], "Logo client v2")
r = client.put(f"/api/tools/image/projets/{P['id']}", data={"donnees": json.dumps({"reglages": NOUV})},
               files={"fichier": ("n.png", b"GIF8", "image/png")})
check("enregistrer avec un fichier invalide → 415", r.status_code, 415)

# ── Renommer, dupliquer ─────────────────────────────────────────────────
r = client.patch(f"/api/tools/image/projets/{P['id']}", json={"nom": "  Logo   final  "})
check("renommer → espaces normalisés", r.json()["nom"], "Logo final")
check("renommer vide → 400", client.patch(f"/api/tools/image/projets/{P['id']}", json={"nom": "  "}).status_code, 400)
r = client.post(f"/api/tools/image/projets/{P['id']}/dupliquer")
check("dupliquer → 200", r.status_code, 200)
D = r.json()
check("dupliquer : nom « (copie) »", D["nom"], "Logo final (copie)")
check("dupliquer : réglages identiques", client.get(f"/api/tools/image/projets/{D['id']}").json()["reglages"], NOUV)
check("dupliquer : fichiers recopiés", len(fichiers_disque()), 5)
check("dupliquer : journalisé DUPLICATE", JOURNAL[-1]["action"], "DUPLICATE")

# ── Droits : un autre utilisateur ───────────────────────────────────────
COURANT["user"] = AUTRE
check("autre : liste vide", client.get("/api/tools/image/projets").json()["projets"], [])
pid = P["id"]
check("autre : détail → 404", client.get(f"/api/tools/image/projets/{pid}").status_code, 404)
check("autre : fichier → 404", client.get(f"/api/tools/image/projets/{pid}/fichier").status_code, 404)
check("autre : vignette → 404", client.get(f"/api/tools/image/projets/{pid}/vignette").status_code, 404)
check("autre : enregistrer → 404", client.put(f"/api/tools/image/projets/{pid}",
      data={"donnees": json.dumps({"reglages": REGLAGES})}).status_code, 404)
check("autre : renommer → 404", client.patch(f"/api/tools/image/projets/{pid}", json={"nom": "x"}).status_code, 404)
check("autre : dupliquer → 404", client.post(f"/api/tools/image/projets/{pid}/dupliquer").status_code, 404)
check("autre : supprimer → 404", client.delete(f"/api/tools/image/projets/{pid}").status_code, 404)
check("inexistant → 404 identique", client.get("/api/tools/image/projets/999999").status_code, 404)
COURANT["user"] = AUTEUR
check("auteur : projet intact après les tentatives", client.get(f"/api/tools/image/projets/{pid}").json()["nom"], "Logo final")

# ── Plafond ─────────────────────────────────────────────────────────────
check("3 projets avant le plafond", len(client.get("/api/tools/image/projets").json()["projets"]), 3)
check("4e projet → accepté", creer(nom="Quatre", vignette=False).status_code, 200)
check("5e projet → 409 (plafond)", creer(nom="Cinq", vignette=False).status_code, 409)
check("dupliquer au plafond → 409", client.post(f"/api/tools/image/projets/{pid}/dupliquer").status_code, 409)

# ── Suppression ─────────────────────────────────────────────────────────
n = len(fichiers_disque())
r = client.delete(f"/api/tools/image/projets/{D['id']}")
check("supprimer → 200", r.status_code, 200)
check("supprimer : fichier et vignette effacés", len(fichiers_disque()), n - 2)
check("supprimer : détail → 404", client.get(f"/api/tools/image/projets/{D['id']}").status_code, 404)
check("supprimer : journalisé DELETE", JOURNAL[-1]["action"], "DELETE")

# ── Chemin : un nom de fichier forgé ne sort pas du dossier ─────────────
with get_db() as conn:
    conn.execute("UPDATE tools_image_projets SET fichier = '../../etc/passwd' WHERE id = ?", (J["id"],))
    conn.commit()
check("nom de fichier forgé → 404", client.get(f"/api/tools/image/projets/{J['id']}/fichier").status_code, 404)

print()
if ECHECS:
    print(f"{len(ECHECS)} échec(s) :", ", ".join(ECHECS))
    sys.exit(1)
print("Tous les contrôles passent.")
