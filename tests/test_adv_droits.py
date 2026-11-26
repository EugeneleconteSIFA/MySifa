"""
ADV : qui ouvre l'appli, qui consulte le carnet, qui modifie (décision du
26/11/2026).

Ce que ce test protège :

1. **Les commerciaux et l'expédition consultent le carnet** (onglet
   Commandes) ; la logistique n'a que la Prépa.
2. **Un commercial ne modifie rien.** Toute route d'écriture de
   `app/routers/adv.py` exige `ROLES_ADV` (pilotage) ou `ROLES_ADV_PREPA`
   (passer « prête »), jamais un cercle de consultation — sauf l'ordre des
   colonnes, préférence d'affichage de la personne.
3. **La page, la tuile du portail et la palette** ouvrent l'appli aux mêmes
   rôles que l'API.

Le router est lu comme du texte : l'importer tirerait fastapi et la base.
"""
import re
import sys

sys.path.insert(0, ".")
import config  # noqa: E402

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


C, E, L = config.ROLE_COMMERCIAL, config.ROLE_EXPEDITION, config.ROLE_LOGISTIQUE

print("Cercles de rôles")
check("commercial : ouvre l'appli et voit le carnet",
      (C in config.ROLES_ADV_LECTURE, C in config.ROLES_ADV_CARNET), (True, True))
check("commercial : ne pilote pas et ne passe pas « prête »",
      (C in config.ROLES_ADV, C in config.ROLES_ADV_PREPA), (False, False))
check("expédition : voit le carnet et passe « prête », sans piloter",
      (E in config.ROLES_ADV_CARNET, E in config.ROLES_ADV_PREPA, E in config.ROLES_ADV), (True, True, False))
check("logistique : Prépa seule",
      (L in config.ROLES_ADV_LECTURE, L in config.ROLES_ADV_CARNET), (True, False))
check("l'administration et la direction pilotent",
      config.ROLES_ADMIN <= config.ROLES_ADV, True)
check("tout cercle est inclus dans l'ouverture de l'appli",
      (config.ROLES_ADV | config.ROLES_ADV_PREPA | config.ROLES_ADV_CARNET) <= config.ROLES_ADV_LECTURE, True)

print("\nRoutes d'écriture")
src = open("app/routers/adv.py", encoding="utf-8").read()
routes = []
for bloc in re.split(r"\n(?=@router\.)", src)[1:]:
    m = re.match(r'@router\.(get|put|post|delete|patch)\("([^"]+)"', bloc)
    g = re.search(r"_exiger\(request, (\w+)\)", bloc)
    routes.append((m.group(1), m.group(2), g.group(1) if g else None))
check("toutes les routes du router ont une garde de rôle", [r for r in routes if not r[2]], [])
PREFERENCES = {"/api/adv/preferences/colonnes"}
for verbe, chemin, cercle in routes:
    if verbe == "get":
        continue
    attendu = {"ROLES_ADV_CARNET"} if chemin in PREFERENCES else {"ROLES_ADV", "ROLES_ADV_PREPA"}
    check(f"{verbe.upper()} {chemin} : {cercle}", cercle in attendu, True)

print("\nPage, portail, palette")
page = open("app/web/adv_page.py", encoding="utf-8").read()
check("la page s'ouvre sur ROLES_ADV_LECTURE", "if role not in ROLES_ADV_LECTURE:" in page, True)
portail = open("app/web/portal_assets.py", encoding="utf-8").read()
m = re.search(r"\[([^\]]*)\]\.includes\(urole\)\)\{\s*const id='adv'", portail)
roles_portail = set(re.findall(r"'(\w+)'", m.group(1))) if m else set()
attendus = {r for r in config.ROLES_ADV_LECTURE if r != config.ROLE_SUPERADMIN}
check("la tuile du portail suit ROLES_ADV_LECTURE", roles_portail, attendus)
cmdk = open("static/mysifa_cmdk.js", encoding="utf-8").read()
m = re.search(r"title: 'ADV',[^\n]*roles: '([^']*)'", cmdk)
roles_cmdk = set(m.group(1).split(",")) if m else set()
check("la palette suit ROLES_ADV_LECTURE", roles_cmdk, attendus)

print()
if ko:
    print(f"test_adv_droits : {ko} échec(s)")
    sys.exit(1)
print("test_adv_droits : OK")
