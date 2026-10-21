"""
Lecture des justificatifs de note de frais : ce que l'application fait de la
réponse du modèle (app/services/ndf_scan.py, interpreter()). Aucun appel
réseau : la réponse du modèle est simulée.

Lancer : python3 tests/test_ndf_scan.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import database  # noqa: F401  (le shim d'abord, cf. CLAUDE.md)
from app.services.ndf_scan import interpreter

CATS = [{"id": 1, "code": "repas", "libelle": "Repas"},
        {"id": 2, "code": "deplacement", "libelle": "Déplacement"}]
echecs = 0


def check(nom, ok):
    global echecs
    print(("ok   " if ok else "KO   ") + nom)
    if not ok:
        echecs += 1


def brut(**k):
    base = {"lisible": True, "date": None, "commerce": None, "ville": None,
            "montant_ttc": None, "tva": [], "categorie": "inconnue", "remarque": None}
    base.update(k)
    return base


r = interpreter(brut(date="2026-10-20", commerce="Le Bouchon", ville="Lyon", montant_ttc=47.3,
                     tva=[{"taux": 10, "montant": 3.1}, {"taux": 20, "montant": 1.2}],
                     categorie="repas"), CATS)
check("ticket à deux taux : TVA additionnée", r["ok"] and r["champs"]["montant_tva"] == 4.3)
check("ticket à deux taux : taux qui porte le plus de TVA", r["champs"]["taux_tva"] == 10)
check("ticket à deux taux : signalé au salarié", "plusieurs taux" in (r["remarque"] or ""))
check("catégorie reconnue rendue par son id", r["champs"]["categorie_id"] == 1)
check("commerce repris en description", r["champs"]["description"] == "Le Bouchon")

r = interpreter(brut(date="2099-01-01", montant_ttc=12), CATS)
check("date dans le futur écartée", r["ok"] and r["champs"]["date_frais"] is None)
check("catégorie inconnue laissée vide", r["champs"]["categorie_id"] is None)

r = interpreter(brut(montant_ttc=10, tva=[{"taux": 7, "montant": 0.65}]), CATS)
check("taux hors liste légale ignoré", r["champs"]["taux_tva"] is None and r["champs"]["montant_tva"] is None)

r = interpreter(brut(montant_ttc=10, tva=[{"taux": 20, "montant": 12}]), CATS)
check("TVA supérieure au TTC ignorée", r["champs"]["montant_tva"] is None)

r = interpreter(brut(montant_ttc=-5), CATS)
check("rien de lisible : échec explicite", not r["ok"] and "à la main" in r["erreur"])

r = interpreter({"lisible": False, "remarque": "Photo floue."}, CATS)
check("document illisible : remarque du modèle rendue", not r["ok"] and r["erreur"] == "Photo floue.")

print()
if echecs:
    print(f"ECHECS : {echecs}")
    sys.exit(1)
print("TOUT EST VERT")
