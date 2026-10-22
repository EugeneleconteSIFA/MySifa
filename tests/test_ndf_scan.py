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
                     tva=[{"taux": 10, "montant": 3.5, "base_ht": 35, "ttc": None},
                          {"taux": 20, "montant": 1.47, "base_ht": None, "ttc": 8.8}],
                     categorie="repas"), CATS)
L = r["champs"]["tva_lignes"] or []
check("ticket à deux taux : une ligne par taux", r["ok"] and [l["taux"] for l in L] == [20, 10])
check("ticket à deux taux : TTC par taux (HT + TVA, ou imprimé)",
      [l["ttc"] for l in L] == [8.8, 38.5] and [l["tva"] for l in L] == [1.47, 3.5])
check("ticket à deux taux : TVA totale et aucun taux unique",
      r["champs"]["montant_tva"] == 4.97 and r["champs"]["taux_tva"] is None)
check("ticket à deux taux : signalé, sans écart", "une ligne par taux" in (r["remarque"] or "") and "cart" not in (r["remarque"] or ""))
check("catégorie reconnue rendue par son id", r["champs"]["categorie_id"] == 1)
check("commerce repris en description", r["champs"]["description"] == "Le Bouchon")

r = interpreter(brut(montant_ttc=50, tva=[{"taux": 10, "montant": 3.5, "base_ht": 35, "ttc": None},
                                          {"taux": 20, "montant": 1.47, "base_ht": None, "ttc": 8.8}]), CATS)
check("écart entre les lignes et le total : signalé", "cart de 2,70 €" in (r["remarque"] or ""))

r = interpreter(brut(montant_ttc=12.6, tva=[{"taux": 5.5, "montant": 0.66, "base_ht": None, "ttc": None}]), CATS)
check("un seul taux : le total du ticket fait la ligne",
      r["champs"]["tva_lignes"] == [{"taux": 5.5, "ttc": 12.6, "tva": 0.66}] and r["champs"]["taux_tva"] == 5.5)

r = interpreter(brut(date="2099-01-01", montant_ttc=12), CATS)
check("date dans le futur écartée", r["ok"] and r["champs"]["date_frais"] is None)
check("catégorie inconnue laissée vide", r["champs"]["categorie_id"] is None)

r = interpreter(brut(montant_ttc=10, tva=[{"taux": 7, "montant": 0.65, "base_ht": None, "ttc": None}]), CATS)
check("taux hors liste légale ignoré", r["champs"]["tva_lignes"] is None and r["champs"]["montant_tva"] is None)

r = interpreter(brut(montant_ttc=10, tva=[{"taux": 20, "montant": 12, "base_ht": None, "ttc": None}]), CATS)
check("TVA supérieure au TTC ignorée", r["champs"]["tva_lignes"] is None)

r = interpreter(brut(montant_ttc=-5), CATS)
check("rien de lisible : échec explicite", not r["ok"] and "à la main" in r["erreur"])

r = interpreter({"lisible": False, "remarque": "Photo floue."}, CATS)
check("document illisible : remarque du modèle rendue", not r["ok"] and r["erreur"] == "Photo floue.")

print()
if echecs:
    print(f"ECHECS : {echecs}")
    sys.exit(1)
print("TOUT EST VERT")
