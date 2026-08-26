"""
État machine de Saisieprod : seul un code de production dit « En production ».

Avant août 2026, `_compute_etat` renvoyait « en_cours_production » sur le code
01. L'opérateur qui ouvrait un dossier voyait aussitôt le badge vert « En
production » alors qu'il partait en calage — il n'avait donc aucune raison de
pointer son passage réel en production (code 03). Le temps était imputé au
code 01, catégorie `personnel`, que la rentabilité et le rapport hebdo ne
comptent pas : du temps machine disparaissait des indicateurs.

Le second défaut était la plage numérique 50–85, qui découpait les codes de
calage en deux états : 02/10/11/12 tombaient en « en_cours_production »,
58/59/60/74/75 en « en_arret ». Deux états pour un même geste d'atelier.

L'état se lit désormais dans la catégorie du référentiel des opérations.
Invariant testé ici : aucun chemin autre qu'un code de catégorie `production`
ne peut produire l'état « en_cours_production ».
"""
import ast
import json
import sys
from typing import Optional

sys.path.insert(0, ".")

# `_compute_etat` est une fonction pure : on l'extrait du routeur plutôt que
# d'importer app.routers.fabrication, qui ouvrirait la base et jouerait les
# migrations pour trois assertions.
_SRC = open("app/routers/fabrication.py", encoding="utf-8").read()
_NS = {"Optional": Optional}
for _node in ast.parse(_SRC).body:
    _nom = getattr(_node, "name", None)
    if _nom is None and isinstance(_node, ast.Assign) and isinstance(_node.targets[0], ast.Name):
        _nom = _node.targets[0].id
    if _nom in ("_ETAT_PAR_CATEGORIE", "_compute_etat"):
        exec(ast.get_source_segment(_SRC, _node), _NS)  # noqa: S102

compute_etat = _NS["_compute_etat"]
OPS = json.load(open("operations.json", encoding="utf-8"))

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


def saisies(*codes):
    return [{"operation_code": c} for c in codes]


print("\nÉtat piloté par la catégorie du référentiel")
CAS = [
    ([], "sans_session", "aucune saisie du jour"),
    (saisies("86"), "arrive", "arrivée personnel"),
    (saisies("86", "01"), "en_calage", "01 ouvre le dossier -> calage, pas production"),
    (saisies("86", "01", "02"), "en_calage", "02 calage"),
    (saisies("86", "01", "12"), "en_calage", "12 changement de couleur (était : production)"),
    (saisies("86", "01", "58"), "en_calage", "58 changement bobines (était : arrêt)"),
    (saisies("86", "01", "74"), "en_calage", "74 changement magnétique (était : arrêt)"),
    (saisies("86", "01", "03"), "en_cours_production", "03 production"),
    (saisies("86", "01", "03", "53"), "en_arret", "53 casse bande"),
    (saisies("86", "01", "03", "53", "88"), "en_cours_production", "88 reprise"),
    (saisies("86", "01", "03", "61"), "en_arret", "61 nettoyage"),
    (saisies("86", "01", "03", "63"), "en_arret", "63 pause"),
    (saisies("86", "01", "03", "64"), "en_arret", "64 intervention technique"),
    (saisies("86", "01", "03", "66"), "en_arret", "66 attente matière"),
    (saisies("86", "01", "03", "89"), "fin_dossier", "89 fin de production"),
    (saisies("86", "01", "03", "87"), "sans_session", "87 départ personnel"),
    (saisies("86", "01", "03", "90"), "en_cours_production", "90 annulation : on lit la saisie d'avant"),
    (saisies("86", "01", "90"), "en_calage", "90 sur un 01 : retour au calage"),
    (saisies("86", "01", "99"), "en_calage", "code hors référentiel : jamais « En production »"),
]
for rows, attendu, libelle in CAS:
    check(libelle, compute_etat(rows, OPS), attendu)

print("\nInvariant : seule la catégorie `production` déclare la production")
for code, entree in OPS.items():
    if code in ("01", "86", "87", "89", "90"):
        continue  # codes de pointage, traités à part dans la fonction
    etat = compute_etat(saisies("86", "01", code), OPS)
    if entree["category"] == "production":
        check(f"{code} ({entree['label']})", etat, "en_cours_production")
    else:
        if etat == "en_cours_production":
            ko += 1
            print(f"  KO  {code} ({entree['label']}) déclare la production sans en être")

print("\nRepli quand le référentiel n'est pas chargé")
check("01 sans référentiel", compute_etat(saisies("86", "01"), None), "en_calage")
check("03 sans référentiel", compute_etat(saisies("86", "01", "03"), None), "en_cours_production")
check("88 sans référentiel", compute_etat(saisies("86", "01", "88"), None), "en_cours_production")
check("53 sans référentiel", compute_etat(saisies("86", "01", "53"), None), "en_arret")
check("99 sans référentiel", compute_etat(saisies("86", "01", "99"), None), "en_calage")

print(f"\n{'Tous les cas passent.' if not ko else str(ko) + ' cas en échec.'}")
sys.exit(1 if ko else 0)
