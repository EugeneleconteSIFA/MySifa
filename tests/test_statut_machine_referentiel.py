"""
État d'une machine (app/routers/production.py › _derive_status) et référentiel
des opérations.

Ce que ce test protège : le référentiel des codes opération vit en base et
s'édite dans Paramètres. L'état machine doit lire la version courante de
`config.OPERATION_SEVERITY`, pas une copie figée au démarrage. Relevé en prod
le 12/11/2026 : Cohésio 2 affichait « Op 83 » alors que le code 83
(« Changement couteaux rive », catégorie calage) existait en base — le module
avait gardé le repli operations.json, où il manque.

Lancer : python3 tests/test_statut_machine_referentiel.py
"""
import sys

sys.path.insert(0, ".")
try:
    import database  # noqa: F401  — toujours avant app.* (cf. CLAUDE.md)
    import config
    from app.routers import production as prod
except ImportError as e:   # poste sans FastAPI : la CI rejoue le test
    print(f"test_statut_machine_referentiel : sauté ({e})")
    sys.exit(0)

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


def ligne(code, cat="", dossier="9932839", heure="08:00:00"):
    return {"operation_code": code, "operation_category": cat, "no_dossier": dossier,
            "date_operation": "2026-11-12T" + heure}


avant = config.OPERATION_SEVERITY
try:
    # Le référentiel change après le chargement du module (édition dans
    # Paramètres, ou rechargement depuis la base au démarrage).
    ref = dict(avant or {})
    ref["83"] = {"label": "Changement couteaux rive", "category": "calage", "severity": "info"}
    ref["97"] = {"label": "Code de test inconnu du fichier", "category": "autre", "severity": "info"}
    config.OPERATION_SEVERITY = ref

    print("\nCode présent en base, saisie sans catégorie")
    k, lib, _ = prod._derive_status([ligne("86", heure="06:00:00"), ligne("83")])
    check("83 → calage", (k, lib), ("calage", "Calage"))

    print("\nCatégorie portée par la saisie")
    k, lib, _ = prod._derive_status([ligne("86", heure="06:00:00"), ligne("83", cat="calage")])
    check("83 (calage) → calage", (k, lib), ("calage", "Calage"))

    print("\nLibellé relu dans le référentiel courant")
    k, lib, _ = prod._derive_status([ligne("86", heure="06:00:00"), ligne("97")])
    check("97 → son libellé, pas « Op 97 »", lib, "Code de test inconnu du fichier")

    print("\nCode absent partout : le code brut reste affiché")
    k, lib, _ = prod._derive_status([ligne("86", heure="06:00:00"), ligne("98")])
    check("98 → Op 98", lib, "Op 98")
finally:
    config.OPERATION_SEVERITY = avant

print()
if ko:
    print(f"test_statut_machine_referentiel : {ko} échec(s)")
    sys.exit(1)
print("test_statut_machine_referentiel : OK")
