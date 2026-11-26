# -*- coding: utf-8 -*-
"""Journal de promotion : lecture par GET /api/promote/journal.

promote_v2.sh tourne dans une unité systemd détachée et termine toujours son
journal par « [promotion terminee - code N] ». Si v1 redémarre pendant la
promotion, la page reprend le suivi en lisant ce journal : il faut donc savoir
dire « en cours », « terminé avec tel code » ou « interrompu » (muet sans
marqueur de fin), sans jamais bloquer le bouton indéfiniment.
"""
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, ".")
import database  # noqa: F401,E402  (shim d'abord, cf. CLAUDE.md)

from app.routers.settings import _lire_journal_promotion  # noqa: E402

ko = 0


def check(libelle, ok, detail=""):
    global ko
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}" + (f" — {detail}" if detail and not ok else ""))


def ecrire(dossier, nom, texte, age_s=0):
    p = os.path.join(dossier, nom)
    with open(p, "w", encoding="utf-8") as f:
        f.write(texte)
    t = time.time() - age_s
    os.utime(p, (t, t))
    return p


print("\nJournal de promotion")
with tempfile.TemporaryDirectory() as d:
    r = _lire_journal_promotion(d)
    check("dossier vide : rien en cours", r["fichier"] is None and not r["en_cours"])
    check("dossier absent : pas d'exception", _lire_journal_promotion(os.path.join(d, "absent"))["fichier"] is None)

    ecrire(d, "promote_20261126_090000.log", "[09:00:00] 1/7 Backup DB\n[promotion terminee - code 0]\n", age_s=9000)
    ecrire(d, "promote_20261126_113843.log", "[11:38:43] 1/7 Backup DB\n[11:39:09] 4/7 chown -R sifa:sifa\n")
    r = _lire_journal_promotion(d)
    check("prend le journal le plus récent", r["fichier"] == "promote_20261126_113843.log", r["fichier"])
    check("sans marqueur et récent : en cours", r["en_cours"] and not r["termine"] and not r["interrompu"])
    check("le contenu est renvoyé", "4/7 chown" in r["contenu"])

    ecrire(d, "promote_20261126_113843.log",
           "[11:38:43] 1/7 Backup DB\n[11:39:30] ==> Promotion réussie\n[promotion terminee - code 0]\n")
    r = _lire_journal_promotion(d)
    check("marqueur code 0 : terminé, code 0", r["termine"] and r["code"] == 0 and not r["en_cours"])

    ecrire(d, "promote_20261126_113843.log", "[11:38:43] ERREUR: rollback\n[promotion terminee - code 1]\n")
    check("marqueur code 1 : code 1", _lire_journal_promotion(d)["code"] == 1)

    ecrire(d, "promote_20261126_113843.log", "[11:38:43] 4/7 chown\n", age_s=1200)
    r = _lire_journal_promotion(d)
    check("muet depuis 20 min sans marqueur : interrompu, plus en cours",
          r["interrompu"] and not r["en_cours"] and not r["termine"])

    gros = "x" * 100_000 + "\n[promotion terminee - code 0]\n"
    ecrire(d, "promote_20261126_120000.log", gros)
    r = _lire_journal_promotion(d)
    check("gros journal : tronqué par le début, marqueur de fin lu",
          r["termine"] and len(r["contenu"]) <= 64_000)

print("\nScript")
rc = subprocess.run(["bash", "-n", "scripts/promote_v2.sh"], capture_output=True, text=True)
check("promote_v2.sh : syntaxe bash", rc.returncode == 0, rc.stderr)
src = open("scripts/promote_v2.sh", encoding="utf-8").read()
check("le script se relance via systemd-run", "systemd-run" in src and "PROMOTE_DETACHE" in src)
check("le marqueur de fin du script est celui que lit l'API",
      'printf "[promotion terminee - code %s]\\n"' in src)

print()
if ko:
    print(f"test_promote_journal : {ko} échec(s)")
    sys.exit(1)
print("test_promote_journal : OK")
