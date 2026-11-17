"""Lecture des fichiers déposés avec repli sur le dossier de prod (17/11/2026).

v1 reçoit la base de prod chaque nuit, pas ses fichiers : les scans d'OF y
étaient listés sans pouvoir s'ouvrir. `UPLOAD_SECOURS_DIR` laisse v1 LIRE
dans le data/uploads de prod ce qu'il n'a pas.

Lancer : python3 tests/test_fichiers_secours.py
"""
import os
import sys
import tempfile

sys.path.insert(0, ".")

import config  # noqa: E402
from app.services import fichiers_secours as fs  # noqa: E402

ko = 0


def verifier(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    ko += 0 if ok else 1
    print(("  OK  " if ok else "  KO  ") + libelle + ("" if ok else f" — obtenu {obtenu!r}, attendu {attendu!r}"))


local = tempfile.mkdtemp()
secours = tempfile.mkdtemp()
fs.UPLOAD_DIR = local
dossier = os.path.join(local, "of_scans")
os.makedirs(dossier)
os.makedirs(os.path.join(secours, "of_scans"))
open(os.path.join(dossier, "ici.pdf"), "wb").write(b"%PDF local")
open(os.path.join(secours, "of_scans", "prod.pdf"), "wb").write(b"%PDF prod")
open(os.path.join(secours, "secret.txt"), "wb").write(b"x")

fs.UPLOAD_SECOURS_DIR = ""
verifier("sans secours : fichier local trouvé", fs.chemin_lecture(dossier, "ici.pdf"), os.path.join(dossier, "ici.pdf"))
verifier("sans secours : fichier absent = None (comportement d'avant)", fs.chemin_lecture(dossier, "prod.pdf"), None)

fs.UPLOAD_SECOURS_DIR = secours
verifier("le local reste prioritaire", fs.chemin_lecture(dossier, "ici.pdf"), os.path.join(dossier, "ici.pdf"))
verifier("absent en local : lu dans le dossier de prod",
         fs.chemin_lecture(dossier, "prod.pdf"), os.path.join(secours, "of_scans", "prod.pdf"))
verifier("absent partout : None", fs.chemin_lecture(dossier, "rien.pdf"), None)
verifier("un nom en « ../ » ne sort pas du dossier visé", fs.chemin_lecture(dossier, "../secret.txt"), None)
verifier("un dossier hors uploads n'a pas de secours", fs.chemin_lecture(tempfile.gettempdir(), "prod.pdf"), None)
verifier("nom vide", fs.chemin_lecture(dossier, ""), None)
verifier("désactivé par défaut dans config", os.getenv("UPLOAD_SECOURS_DIR", "") == "" and config.UPLOAD_SECOURS_DIR == "", True)

print()
print("ÉCHECS : %d" % ko if ko else "Tout est vert.")
sys.exit(1 if ko else 0)
