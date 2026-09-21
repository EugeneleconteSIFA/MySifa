"""
Client deduit du rangement quand le classeur ne le donne pas.

Le modele maison arrive prerempli « Mon client » et beaucoup de commerciaux ne
le remplacent pas : le vrai nom est alors celui du dossier. Encore faut-il
sauter les segments qui n'ont jamais nomme un client — le millesime, le format
de l'etiquette, le dossier fourre-tout. Sans ce tri, un devis range dans
« PHT/Boulanger/Solvarea/80x40 mm/ » entrait en base au nom du client
« 80x40 mm » (vu sur v1 le 21/09/2026).

Lancer : python3 tests/test_devis_client_repli.py
"""

import os
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))
os.chdir(RACINE)

import database  # noqa: F401,E402  — le shim d'abord, toujours
from app.services.devis_extraction import _client_de_repli  # noqa: E402

FAIL = []


def check(chemin, attendu, provenance_attendue="nom du dossier"):
    got, prov = _client_de_repli(chemin.split("/")[-1], chemin)
    ok = got == attendu and prov == provenance_attendue
    print(("ok   " if ok else "KO   ") + chemin[:66].ljust(68) + f"{got!r}"
          + ("" if ok else f"   attendu {attendu!r}"))
    if not ok:
        FAIL.append(chemin)


print("\n1. Segments qui ne nomment pas un client")

check("PHT/Boulanger/Solvarea/80x40 mm/80 x 40 mm Thermique enlevable 27.000.xlsx", "Solvarea")
check("Ozalyd/35 mm Rondes et 45 x 25 mm couche permanent/LAIZE 440m.xlsx", "Ozalyd")
check("Carso/35x12 mm Foliset/35x12 mm PP 100 LH 243 permanent.xlsx", "Carso")
check("Logisteo Groupe AD/60x49 mm repiquage/60x49 mm velin permanent.xls", "Logisteo Groupe AD")
check("CARREFOUR/2026/devis.xlsx", "CARREFOUR")
check("CARREFOUR/Devis 2025/devis.xlsx", "CARREFOUR")
check("E&P Consult/Carrefour belgique AO 2023/Nouveau dossier/122-0022.xlsx",
      "Carrefour belgique AO 2023")

print("\n2. Ce qui doit rester intact")

check("Kiabi/35x20 mm couche permanent 6 series 10-09-2026.xlsx", "Kiabi")
check("3M France/devis.xlsx", "3M France")
check("LDC - Volena - SNV/65 x 65 mm thermique Pro permanent.xlsx", "LDC - Volena - SNV")
check("devis pose a la racine.xlsx", "devis pose a la racine", "nom du fichier")

print("")
if FAIL:
    print("ECHECS : " + ", ".join(FAIL))
    sys.exit(1)
print("TOUT EST VERT")
