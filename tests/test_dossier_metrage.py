"""
Metrage produit d'un dossier : ecart de compteur machine, pas somme de champs.

Cas releve le 26/08/2026 sur le dossier « 9932255 - L2 » (Cohesio 1, ref
122/0021) : la liste des saisies MyProd affichait « 17 531 m » quand la fiche
produit affichait 0 m et 0 m/mn. Les deux ecrans lisaient des colonnes
differentes.

Lancer : python3 tests/test_dossier_metrage.py
"""

import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))
os.chdir(RACINE)

# Base jetable : le calcul ne lit rien en base, mais le shim `database`
# initialise le schema au chargement — hors de question de le faire sur
# data/production.db.
os.environ["DB_PATH"] = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
import database  # noqa: F401,E402  — le shim doit etre charge avant tout app.*
from app.services.dossier_stats import build_dossier_production_stats  # noqa: E402

FAIL = []


def check(label, got, expected):
    ok = got == expected
    print(("ok   " if ok else "KO   ") + label.ljust(60) + f"{got}"
          + ("" if ok else f"   attendu {expected}"))
    if not ok:
        FAIL.append(label)


DOS = "9932255 - L2"
TONY = "Tony Cathelineau"
ALAN = "DENIS Alan"


def saisie(sid, heure, code, operation, operateur, **extra):
    r = {
        "id": sid, "no_dossier": DOS, "operateur": operateur,
        "date_operation": "2026-07-28T" + heure, "operation_code": code,
        "operation": operation, "machine": "Cohésio 1",
        "operation_category": extra.pop("categorie", "production"),
        "quantite_traitee": extra.pop("etiquettes", 0),
    }
    r.update(extra)
    return r


print("--- compteurs dans les colonnes actuelles (metrage_total_*) ---")
# Les saisies fabrication remplissent metrage_total_debut / metrage_total_fin.
# Avant correction, seules metrage_prevu / metrage_reel etaient lues : la
# journee entiere ressortait a 0 m.
JOURNEE = [
    saisie(1, "12:56:42", "01", "01 Début de production", TONY,
           metrage_total_debut=4307113.0),
    saisie(2, "12:56:54", "02", "02 - Calage", TONY, categorie="calage"),
    saisie(3, "15:08:48", "03", "03 - Production", TONY),
    saisie(4, "17:41:25", "64", "64 - Intervention technique", TONY,
           categorie="technique"),
    saisie(5, "19:49:36", "88", "88 - Reprise production", TONY),
    saisie(6, "21:56:47", "89", "89 Fin de production", TONY,
           metrage_total_fin=4324644.0, etiquettes=891000),
]
stats = build_dossier_production_stats(JOURNEE, DOS)
check("metrage = compteur fin - compteur debut", stats["quantites"]["metrage_m"], 17531.0)
check("etiquettes remontees", stats["quantites"]["etiquettes"], 891000.0)
check("temps de production (03 + 88)", stats["temps_totaux"]["production_min"], 279.8)
check("vitesse non nulle", round(stats["vitesse_m_min"], 2), 62.66)

print("--- repli sur les anciennes colonnes (lignes historiques) ---")
ANCIEN = [
    saisie(1, "12:56:42", "01", "01 Début de production", TONY, metrage_prevu=4307113.0),
    saisie(2, "15:08:48", "03", "03 - Production", TONY),
    saisie(3, "21:56:47", "89", "89 Fin de production", TONY,
           metrage_reel=4324644.0, etiquettes=891000),
]
check("ancien couple prevu/reel toujours lu",
      build_dossier_production_stats(ANCIEN, DOS)["quantites"]["metrage_m"], 17531.0)

print("--- relais d'equipe : le 01 n'est pas pose par celui qui cloture ---")
# Le compteur de debut appartient au dossier, pas a l'operateur. Une equipe
# qui prend la suite en cours de cycle ne repose pas de 01 : chercher le
# compteur sous le seul nom de celui qui cloture ne le trouvait pas, et le
# calcul repartait de 0 — il sortait alors le compteur machine entier.
RELAIS = [
    saisie(1, "06:10:00", "01", "01 Début de production", ALAN,
           metrage_total_debut=4307113.0),
    saisie(2, "06:11:00", "03", "03 - Production", ALAN),
    saisie(3, "12:55:00", "87", "87 - Départ personnel", ALAN, categorie="autre"),
    saisie(4, "12:56:22", "86", "86 - Arrivée personnel", TONY, categorie="autre"),
    saisie(5, "12:57:00", "03", "03 - Production", TONY),
    saisie(6, "21:56:47", "89", "89 Fin de production", TONY,
           metrage_total_fin=4324644.0, etiquettes=891000),
]
relais = build_dossier_production_stats(RELAIS, DOS)
check("compteur de debut retrouve malgre le changement d'equipe",
      relais["quantites"]["metrage_m"], 17531.0)
check("le compteur machine nu ne sort jamais",
      relais["quantites"]["metrage_m"] == 4324644.0, False)

print("--- aucun compteur de debut : pas de metrage, jamais le compteur nu ---")
# Prendre 0 pour origine sortait le compteur machine entier — l'erreur
# d'ordre de grandeur qui a deja fausse les besoins matieres.
SANS_DEBUT = [
    saisie(1, "12:56:42", "01", "01 Début de production", TONY),
    saisie(2, "15:08:48", "03", "03 - Production", TONY),
    saisie(3, "21:56:47", "89", "89 Fin de production", TONY,
           metrage_total_fin=4324644.0, etiquettes=891000),
]
sans = build_dossier_production_stats(SANS_DEBUT, DOS)
check("metrage non mesurable = 0, pas 4 324 644", sans["quantites"]["metrage_m"], 0.0)
check("etiquettes restent lisibles", sans["quantites"]["etiquettes"], 891000.0)

print("--- annulation (90) : le cycle porte ses deux compteurs ---")
ANNULE = [
    saisie(1, "12:56:42", "01", "01 Début de production", TONY,
           metrage_total_debut=4307113.0),
    saisie(2, "15:08:48", "03", "03 - Production", TONY),
    saisie(3, "16:30:00", "90", "90 - Annulation dossier", TONY,
           metrage_total_debut=4307113.0, metrage_total_fin=4309000.0),
]
check("metrage consomme avant annulation",
      build_dossier_production_stats(ANNULE, DOS)["quantites"]["metrage_m"], 1887.0)

print()
if FAIL:
    print(f"{len(FAIL)} echec(s) : " + ", ".join(FAIL))
    sys.exit(1)
print("Tous les controles passent.")
