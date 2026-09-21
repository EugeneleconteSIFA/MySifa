"""
Filtres de l'agent d'import des devis : dossiers ecartes et millesime.

Le partage des commerciaux est range par client, pas par annee, et les noms de
fichiers sont pleins de references matiere qui ressemblent a des annees
(« 1408-22 », « 2021-40 », « 2288-50g »). Ces deux pieges sont la raison d'etre
du test : un filtre trop gourmand ecarterait des devis de l'annee en cours.

Lancer : python3 tests/test_devis_agent_filtres.py
"""

import os
import sys
import tempfile
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "scripts"))

from devis_import_commun import (  # noqa: E402
    DOSSIERS_IGNORES, annee_du_nom, dossiers_exclus, parcourir,
)

FAIL = []


def check(label, got, expected):
    ok = got == expected
    print(("ok   " if ok else "KO   ") + label.ljust(64) + f"{got}"
          + ("" if ok else f"   attendu {expected}"))
    if not ok:
        FAIL.append(label)


print("\n1. Annee lue dans le nom du fichier")

# Noms reels du partage : la reference matiere precede la date du devis.
check("2021-40 ... 27-10-2025 -> 2025",
      annee_du_nom("150x200mm PP RIFO 2021-40 ref 0169 2 couleurs 100.000 ex 27-10-2025.xlsx"),
      2025)
check("2028-19 ... 21-09-2026 -> 2026",
      annee_du_nom("149 x 55 mm thermique protege 2028-19 qte 5.860.800 21-09-2026.xlsx"),
      2026)
check("1408-22 ... 22-01-2026 -> 2026",
      annee_du_nom("105x230 mm thermique eco enlevable 1408 - 22g B800 qte 600.000 22-01-2026.xlsx"),
      2026)
check("annee sur deux chiffres (11-05-26) -> 2026",
      annee_du_nom("40x20 mm velin permanent 21 series 1 couleur 13.300.000 11-05-26.xlsx"),
      2026)
check("aucune date -> None",
      annee_du_nom("100x149 mm velin permanent COHESIO dont 160.000 vierges.xls"), None)
check("reference matiere seule n'est pas une date",
      annee_du_nom("98x98 mm velin congelation 2028 B5400 M40.xlsx"), None)
check("date collee (160126) non lue -> None",
      annee_du_nom("180x130 mm glassine SILICONE qte 12.000 160126.xls"), None)
check("jour et mois invalides ignores",
      annee_du_nom("50x60 40-99-2026.xlsx"), None)
check("la derniere date l'emporte",
      annee_du_nom("devis 03-02-2025 revu 16-06-2026.xlsx"), 2026)

print("\n2. Liste de dossiers ecartes")

check("valeur par defaut non vide", len(DOSSIERS_IGNORES) >= 3, True)
check("decoupage de la ligne de commande",
      dossiers_exclus(" _modele , 1111 - base marge brute ,, "),
      ("_modele", "1111 - base marge brute"))
check("chaine vide : plus aucun dossier ecarte", dossiers_exclus(""), ())
check("« aucun » vide la liste (PowerShell refuse la chaine vide)",
      dossiers_exclus("Aucun"), ())

print("\n3. Parcours du partage")

base = tempfile.mkdtemp(prefix="devis_agent_")
ANCIEN = time.time() - 900 * 86400   # ~2 ans et demi


def poser(relatif, mtime=None):
    chemin = os.path.join(base, relatif)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "wb") as fh:
        fh.write(b"x" * 64)
    if mtime:
        os.utime(chemin, (mtime, mtime))
    return chemin


poser("Kiabi/35x20 mm couche permanent 6 series 10-09-2026.xlsx")
poser("Roquette/150x200 PP RIFO 2021-40 100.000 ex 27-10-2025.xlsx")
poser("_modèle/modèle calcul de prix COHESIO 110122.xlsx")
poser("2 Paramètres devis/Prix matière première support adhésif.xls")
poser("1111 - base marge brute/PHT/Arkena/105x148 mm thermique eco 500.000.xlsx")
poser("PHT/Nestle/158x80 mm Velin permanent 28-11-2025.xlsx")
poser("E&P Consult/100x149 mm velin permanent COHESIO sans date.xls", ANCIEN)
poser("Hermes/45x130 mm Hermes 105841X00 sans date mais recent.xlsx")
poser("Cosium/~$classeur ouvert 10-09-2026.xlsx")     # verrou Excel
poser("Cosium/notes 10-09-2026.txt")                  # extension non lue


def noms(fichiers):
    return sorted(os.path.relpath(c, base).replace("\\", "/") for c, _, _ in fichiers)


tout = noms(parcourir(base, exclure=()))
check("sans filtre : verrou Excel et .txt deja ecartes", len(tout), 8)

garde = noms(parcourir(base))
check("_modèle ecarte (le vrai nom, accentue)",
      any(n.startswith("_modèle/") for n in garde), False)
check("2 Parametres devis ecarte (accents et casse indifferents)",
      any(n.startswith("2 Paramètres devis/") for n in garde), False)
check("1111 - base marge brute ecarte avec toute sa descendance",
      any(n.startswith("1111 - base marge brute/") for n in garde), False)
check("les devis clients restent", len(garde), 5)

m2026 = noms(parcourir(base, annee_devis_min=2026))
check("le devis 2026 est garde",
      "Kiabi/35x20 mm couche permanent 6 series 10-09-2026.xlsx" in m2026, True)
check("le devis 2025 est ecarte",
      any("27-10-2025" in n for n in m2026), False)
check("sans date mais fichier recent : garde",
      any("Hermes/" in n for n in m2026), True)
check("sans date et fichier ancien : ecarte",
      any("E&P Consult/" in n for n in m2026), False)

print("")
if FAIL:
    print("ECHECS : " + ", ".join(FAIL))
    sys.exit(1)
print("TOUT EST VERT")
