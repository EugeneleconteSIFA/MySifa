"""
Portail : ce qu'une preference de tuiles doit survivre a un rechargement.

Le bug d'origine : on epinglait MyBAT en favori, l'etoile s'allumait, et le
premier rechargement complet la faisait disparaitre. Cote serveur, la liste
d'ids etait filtree contre une liste fermee ecrite a la main, figee a la
creation du portail. Toutes les applications ajoutees ensuite (MyAO, MyBAT,
MyQualite, Coffre, Coffre RH, Maintenance) etaient jetees en silence — a
l'ecriture comme a la lecture, ordre des tuiles compris.

Ce test verrouille deux choses :

1. Toute tuile REELLEMENT rendue par le portail traverse l'aller-retour. La
   liste des ids est relevee dans le source du portail, pas recopiee ici : une
   tuile ajoutee demain est couverte sans qu'on touche a ce fichier, et un
   retour au filtrage par liste fermee le fait tomber immediatement.
2. Le filtrage de forme reste strict : rien qui ne ressemble pas a un id de
   tuile n'entre en base, les doublons sont ecrases, l'alias historique
   `devis` -> `pricing` tient, et « aucun favori » s'ecrit NULL.

Le module valide ne depend que de la stdlib : ce test ne charge ni base ni
FastAPI.

Lancer : python3 tests/test_portail_favoris.py
"""

import json
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from app.services import portail_prefs as pp  # noqa: E402

ECHECS = []


def check(label, obtenu, attendu=True):
    ok = obtenu == attendu
    print(("ok   " if ok else "KO   ") + label.ljust(62)
          + ("" if ok else f"{obtenu!r}   attendu {attendu!r}"))
    if not ok:
        ECHECS.append(label)


def aller_retour(ids):
    """Ce que le serveur relit apres avoir enregistre ce que le front envoie."""
    return pp.depuis_db(pp.pour_db(ids))


# ── 1. Toutes les tuiles du portail traversent l'aller-retour ───────────────
# Ids releves a la source : le portail les declare en `const id='xxx'` juste
# avant de poser `data-portal-id` sur la tuile.
source = (RACINE / "app/web/portal_assets.py").read_text(encoding="utf-8")
TUILES = sorted(set(re.findall(r"const id='([a-z0-9_]+)';", source)))
check(f"les ids de tuiles sont bien releves ({len(TUILES)})", len(TUILES) >= 10)
check("'bat' fait partie des tuiles rendues", "bat" in TUILES)

perdues = [t for t in TUILES if aller_retour([t]) != [t]]
check("aucune tuile n'est perdue a l'aller-retour", perdues, [])

# Le cas exact du rapport : MyBAT epingle, puis rechargement complet.
check("MyBAT reste en favori apres rechargement", aller_retour(["bat"]), ["bat"])
check("l'ordre complet du portail survit", aller_retour(TUILES), TUILES)
check("l'ordre est conserve tel quel", aller_retour(["expe", "bat", "prod"]),
      ["expe", "bat", "prod"])

# ── 2. Le filtrage de forme reste strict ───────────────────────────────────
check("un id vide est ignore", aller_retour(["", "  "]), [])
check("une valeur non-str est ignoree", aller_retour([None, 3, {}, "prod"]), ["prod"])
check("un id hors forme est ignore",
      aller_retour(["../../etc", "<script>", "PROD", "a" * 40, "prod"]), ["prod"])
check("les doublons sont ecrases", aller_retour(["prod", "prod", "expe"]),
      ["prod", "expe"])
check("l'alias devis -> pricing tient", aller_retour(["devis"]), ["pricing"])
check("devis et pricing ensemble ne font qu'une tuile",
      aller_retour(["devis", "pricing"]), ["pricing"])
check("la liste est bornee",
      len(aller_retour([f"app{i}" for i in range(200)])) <= pp.MAX_TILES)

# ── 3. Ce qui part en base : du JSON compact, ou NULL ──────────────────────
check("aucun favori s'ecrit NULL", pp.pour_db([]), None)
check("une liste invalide s'ecrit NULL", pp.pour_db(["!!"]), None)
check("None s'ecrit NULL", pp.pour_db(None), None)
brut = pp.pour_db(["bat", "expe"])
check("le format stocke est du JSON compact", brut, '["bat","expe"]')
check("il se relit tel quel", json.loads(brut), ["bat", "expe"])
check("une colonne vide se lit comme aucune preference", pp.depuis_db(None), [])
check("une colonne corrompue ne fait pas tomber la page",
      pp.depuis_db("{pas du json"), [])

print()
if ECHECS:
    print(f"ECHEC : {len(ECHECS)} verification(s)")
    sys.exit(1)
print("Toutes les verifications passent.")
