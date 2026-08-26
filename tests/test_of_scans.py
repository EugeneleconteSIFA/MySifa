"""
Ingestion des OF termines scannes : lecture du nom de fichier, rattachement,
deduplication par contenu, et parcours du dossier reseau.

Lancer : python3 tests/test_of_scans.py
"""

import contextlib
import io
import os
import shutil
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))
os.chdir(RACINE)

FAIL = []


def check(label, got, expected):
    ok = got == expected
    print(("ok   " if ok else "KO   ") + label.ljust(58) + f"{got}"
          + ("" if ok else f"   attendu {expected}"))
    if not ok:
        FAIL.append(label)


db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["DB_PATH"] = db
import config; config.DB_PATH = db
import app.core.database as dbmod; dbmod.DB_PATH = db
with contextlib.redirect_stdout(io.StringIO()):
    dbmod.init_db()

from app.services import produit_memoire as pm
import app.routers.produits_memoire as pmr

# Les scans de test n'ont rien a faire dans data/uploads/of_scans.
DEPOT = tempfile.mkdtemp(prefix="of_scans_depot_")
pmr.SCAN_UPLOAD_DIR = DEPOT

print("--- lecture du nom de fichier (cas reels du dossier atelier) ---")
CAS = [
    ("9932140 (marché 748) 420-0018.pdf", "9932140", "420/0018"),
    ("9932178 706-0003.pdf", "9932178", "706/0003"),
    ("9932215 - L1 245-0241.pdf", "9932215", "245/0241"),
    ("9932215 - L2 245-0246.pdf", "9932215", "245/0246"),
    ("9932255 - L2 122-0021.pdf", "9932255", "122/0021"),
    ("M759 + 9932338 - L3 1382-0005.pdf", "9932338", "1382/0005"),
    ("March 746 1068-0002.pdf", None, "1068/0002"),
    ("Reliquat 9932056 890-0079.pdf", "Reliquat 9932056", "890/0079"),
    ("Reliquat Marché 745 1068-0001.pdf", None, "1068/0001"),
    # Le piege : « 16-07-2026 » est une date, pas une reference produit.
    ("Stock 16-07-2026 961-0007.pdf", None, "961/0007"),
    ("scan sans rien.pdf", None, None),
]
for nom, of_attendu, ref_attendue in CAS:
    lu = pm.analyser_nom_scan(nom)
    check(("nom " + nom)[:56], (lu["of_numero"], lu["ref_produit_norm"]),
          (of_attendu, ref_attendue))

print("--- jeu d'essai : un OF connu, un dossier, une reference ---")
REF = "965/0001"
with dbmod.get_db() as conn:
    conn.execute("INSERT OR REPLACE INTO machines (id, nom, code) VALUES (992,'Cohesio 1','CO1')")
    conn.execute(
        "INSERT INTO of_imports (id, of_numero, reference, machine, date_creation, date_import) "
        "VALUES (1, '9931987', ?, 'Cohesio 1', '2026-01-28', '2026-08-01')", (REF,))
    conn.execute(
        "INSERT INTO planning_entries (machine_id, position, reference, client, description, "
        "duree_heures, statut, ref_produit, numero_of, of_import_id) "
        "VALUES (992, 1, 'D-9931987', 'ITM', 'Etiquette', 8, 'termine', ?, '9931987', 1)",
        (REF + " - COHESIO 1",))
    conn.commit()


def pdf_octets(texte):
    """Un vrai PDF, pour que pdfplumber ne se plaigne pas."""
    from io import BytesIO
    from reportlab.pdfgen import canvas
    buf = BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(80, 800, texte)
    c.save()
    return buf.getvalue()


print("--- rattachement par le numero d'OF lu dans le nom ---")
res = pmr._enregistrer_scan(pdf_octets("OF 9931987"), "9931987 965-0001.pdf", "test")
check("scan enregistre", res["success"], True)
check("OF reconnu", res["of_numero"], "9931987")
check("dossier retrouve", res["no_dossier"], "D-9931987")
check("reference rattachee", res["ref_produit_norm"], REF)
check("resolu par le dossier", res["origine_ref"], "dossier")
check("statut", res["statut"], "rattache")

print("--- deduplication par contenu ---")
memes_octets = pdf_octets("OF 9931987")
pmr._enregistrer_scan(memes_octets, "premier depot.pdf", "test")
bis = pmr._enregistrer_scan(memes_octets, "renomme autrement.pdf", "test")
check("second depot vu comme doublon", bis.get("doublon"), True)
with dbmod.get_db() as conn:
    n = conn.execute("SELECT COUNT(*) FROM produit_documents").fetchone()[0]
check("aucune ligne en double", n, 2)  # le scan OF + le premier depot

print("--- rattachement par la seule reference du nom (aucun OF) ---")
res2 = pmr._enregistrer_scan(pdf_octets("marche 746"), "March 746 1068-0002.pdf", "test")
check("pas de numero d'OF", res2["of_numero"], None)
check("rattache au produit quand meme", res2["ref_produit_norm"], "1068/0002")
check("resolu par le nom", res2["origine_ref"], "nom_fichier")
check("aucun dossier", res2["no_dossier"], None)

print("--- ni OF ni reference : file de rattachement ---")
res3 = pmr._enregistrer_scan(pdf_octets("rien"), "scan illisible.pdf", "test")
check("mis en file", res3["statut"], "a_rattacher")
check("aucune reference devinee", res3["ref_produit_norm"], None)

print("--- datation : production, OF, fichier, import ---")
with dbmod.get_db() as conn:
    # 1. Une production rattachee : sa date de fin fait foi.
    conn.execute(
        "INSERT INTO produit_series (ref_produit_norm, no_dossier, date_debut, date_fin, cloture_le) "
        "VALUES (?, 'D-9931987', '2026-01-29T17:00:00', '2026-02-02T16:15:00', ?)",
        (REF, pm.now_iso()))
    conn.commit()
    check("date = fin de production",
          pm.date_document(conn, "D-9931987", 1, "2026-08-24T10:00:00", "2026-08-24T12:00:00"),
          "2026-02-02T16:15:00")
    # 2. Sans production : la date de creation de l'OF.
    check("date = creation de l'OF",
          pm.date_document(conn, None, 1, "2026-08-24T10:00:00", "2026-08-24T12:00:00"),
          "2026-01-28")
    # 3. Sans OF : la date du fichier sur le partage.
    check("date = date du fichier",
          pm.date_document(conn, None, None, "2026-07-15T09:00:00", "2026-08-24T12:00:00"),
          "2026-07-15T09:00:00")
    # 4. Rien de mieux : la date d'import, faute d'autre chose.
    check("date = import en dernier recours",
          pm.date_document(conn, None, None, None, "2026-08-24T12:00:00"),
          "2026-08-24T12:00:00")

res4 = pmr._enregistrer_scan(pdf_octets("date"), "9931987 965-0001 bis.pdf", "test",
                             date_fichier="2026-08-24T10:00:00")
check("scan date sur la production", res4["date_document"], "2026-02-02T16:15:00")

with dbmod.get_db() as conn:
    docs = pm.documents_produit(conn, REF)
check("documents ordonnes et enrichis", len(docs) >= 2, True)
check("machine remontee depuis l'OF", docs[0].get("machine"), "Cohesio 1")

print("--- recherche de dossiers pour le rattachement manuel ---")
# La file de rattachement propose des candidats au fil de la frappe : ce qui
# compte est qu'on retrouve le dossier par TOUT ce que le scan peut porter
# (numero de dossier, numero d'OF, reference produit, client) et que la
# reference annoncee soit celle que le rattachement ecrira vraiment.
pmr.get_current_user = lambda request: {"nom": "test"}


def cherche(q):
    return [d["no_dossier"] for d in pmr.rechercher_dossiers(request=None, q=q)["dossiers"]]


check("trouve par le numero de dossier", cherche("D-9931987"), ["D-9931987"])
check("trouve par le numero d'OF", cherche("9931987"), ["D-9931987"])
check("trouve par la reference produit", cherche("965/0001"), ["D-9931987"])
check("trouve par le client", cherche("ITM"), ["D-9931987"])
check("une seule lettre ne cherche pas", cherche("D"), [])
check("aucun resultat reste vide", cherche("zzzzz"), [])
check("reference annoncee = celle qui sera ecrite",
      pmr.rechercher_dossiers(request=None, q="9931987")["dossiers"][0]["ref_produit_norm"],
      REF)

print("--- parcours du dossier reseau (sous-dossiers par annee) ---")
import of_scans_commun as osc

racine = tempfile.mkdtemp(prefix="of_scans_src_")
os.makedirs(os.path.join(racine, "2024"))
os.makedirs(os.path.join(racine, "2022 retrouves derriere radiateur"))
os.makedirs(os.path.join(racine, "_envoyes"))
for rel in ("9932178 706-0003.pdf",
            "2024/9931987 965-0001.pdf",
            "2022 retrouves derriere radiateur/vieux 122-0021.pdf",
            "_envoyes/deja parti.pdf",
            "2024/note.txt"):
    chemin = os.path.join(racine, rel)
    with open(chemin, "wb") as fh:
        fh.write(b"%PDF-1.4 test")

vus = osc.parcourir(racine)
noms = sorted(osc.cle_index(racine, c) for c, _, _ in vus)
check("PDF des sous-dossiers pris", len(vus), 3)
check("le .txt est ignore", any(n.endswith(".txt") for n in noms), False)
check("_envoyes est ignore", any(n.startswith("_envoyes") for n in noms), False)

idx = os.path.join(tempfile.mkdtemp(), "index.json")
osc.ecrire_index(idx, {"a.pdf": {"taille": 1, "mtime": 2}})
check("index relu", osc.charger_index(idx)["a.pdf"]["taille"], 1)
check("index absent = vide", osc.charger_index(os.path.join(idx, "nexistepas")), {})

for d in (DEPOT, racine):
    shutil.rmtree(d, ignore_errors=True)

print()
if FAIL:
    print(f"{len(FAIL)} echec(s) : " + ", ".join(FAIL))
    sys.exit(1)
print("Tous les controles passent.")
