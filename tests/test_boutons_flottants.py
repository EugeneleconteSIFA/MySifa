"""
Boutons flottants par application (app/services/boutons_flottants.py).

Ce que ce test protège :

1. **L'adresse donne la bonne appli.** « /planning-rh » n'est pas « /planning »,
   « /rh/coffre » n'est pas « /coffre », et une page publique (invitation
   calendrier, portail, API) n'en a aucune : rien n'y est injecté.
2. **Le défaut est « tout activé »**, sauf la bulle de messagerie sur la page
   Messagerie — sans aucune ligne en base.
3. **Un bouton coupé est masqué par son sélecteur**, et un réglage en base
   l'emporte sur le défaut.
4. **Un bouton propre à une appli ne se règle que chez elle.**
5. **Chaque bouton est réglable** : une clé, un sélecteur (sauf les raccourcis
   sans icône), et aucune appli en double.

Module pur : aucun import de base ni de FastAPI.
"""
import importlib.util
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("boutons_flottants", RACINE / "app/services/boutons_flottants.py")
bf = importlib.util.module_from_spec(_spec)
sys.modules["boutons_flottants"] = bf
_spec.loader.exec_module(bf)

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


print("\nAdresse → application")
for chemin, attendu in [
    ("/", "portail"), ("/stock", "stock"), ("/stock?tab=dashboard", "stock"),
    ("/planning-rh", "planning_rh"), ("/planning", "planning"), ("/planningx", None),
    ("/rh/coffre", "rh_coffre"), ("/coffre", "coffre"), ("/pricing/mystock/12", "pricing"),
    ("/erp", "erp"), ("/calendrier", "calendrier"), ("/calendrier/invitation/abc", None),
    ("/portail/expe/xyz", None), ("/api/auth/me", None), ("/static/x.js", None),
    ("/website", None),
]:
    check(f"{chemin} → {attendu}", bf.appli_de_chemin(chemin), attendu)

print("\nDéfauts")
check("messagerie coupée sur Messagerie", bf.coupes({}, "messages"), ["messagerie"])
check("rien de coupé ailleurs", bf.coupes({}, "stock"), [])
check("métrage bobine propre à MyStock", "metrage" in [b.cle for b in bf.BOUTONS if bf.applicable(b, "stock")], True)
check("métrage bobine absent de MyProd", "metrage" in [b.cle for b in bf.BOUTONS if bf.applicable(b, "prod")], False)

print("\nRéglage en base et masquage")
reg = {("stock", "ia"): False, ("messages", "messagerie"): True}
check("l'IA coupée dans MyStock", bf.coupes(reg, "stock"), ["ia"])
check("la messagerie réactivée sur Messagerie", bf.coupes(reg, "messages"), [])
tete = bf.tete_de_page(reg, "stock")
check("réglage lisible par les scripts", '"off": ["ia"]' in tete, True)
check("CSS de masquage", "#ai-chat-root{display:none!important}" in tete, True)
check("aucun CSS quand rien n'est coupé", "mysifa-boutons-off" in bf.tete_de_page({}, "prod"), False)
conf = json.loads(tete.split("window.__MYSIFA_BOUTONS__=", 1)[1].split(";", 1)[0])
check("appli transmise", conf["appli"], "stock")

print("\nGrille de Paramètres")
g = bf.grille(reg)
ia = next(b for b in g["boutons"] if b["cle"] == "ia")
check("case coupée", ia["etats"]["stock"], False)
check("case active", ia["etats"]["prod"], True)
mtr = next(b for b in g["boutons"] if b["cle"] == "metrage")
check("bouton propre : case des autres applis vide", mtr["etats"]["prod"], None)
check("bouton propre : nommé", mtr["propre_libelle"], "MyStock")

print("\nValidation")
for appli, cle, attendu in [("stock", "ia", None), ("stock", "metrage", None),
                            ("prod", "metrage", "Ce bouton est propre à une autre application."),
                            ("inconnue", "ia", "Application inconnue."), ("stock", "x", "Bouton inconnu.")]:
    try:
        bf.valider(appli, cle)
        r = None
    except ValueError as e:
        r = str(e)
    check(f"{appli} / {cle}", r, attendu)

print("\nCohérence du référentiel")
codes = [a.code for a in bf.APPLIS]
check("aucune appli en double", len(codes), len(set(codes)))
check("chaque bouton propre vise une appli existante",
      all(b.appli in set(codes) for b in bf.BOUTONS if b.appli), True)
check("seul le raccourci Option+T n'a pas de sélecteur",
      [b.cle for b in bf.BOUTONS if not b.selecteur], ["tache"])

print()
if ko:
    print(f"test_boutons_flottants : {ko} échec(s)")
    sys.exit(1)
print("test_boutons_flottants : OK")
