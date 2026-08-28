"""
Le catalogue des volets du portail : filtrage par rôle, URL et icônes réelles.

Lancer : python3 tests/test_portail_volets.py

Ce test attrape trois erreurs qui, sans lui, ne se voient qu'à l'usage :

1. Une entrée réservée qui fuit vers un rôle qui n'y a pas droit — le front ne
   filtre rien, il affiche ce qu'on lui envoie.
2. Une URL qui ne correspond à aucune route : l'utilisateur clique, atterrit sur
   un 404 ou sur l'onglet par défaut de la page, et croit avoir raté son clic.
3. Un nom d'icône absent du jeu SVG : `icon()` retombe alors sur
   'alert-circle' et met un point d'exclamation dans tout le menu.
"""

import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

from app.services import portail_volets as pv   # noqa: E402

ECHECS = []


def check(label, obtenu, attendu=True):
    ok = obtenu == attendu
    print(("ok   " if ok else "KO   ") + label.ljust(62)
          + ("" if ok else f"{obtenu!r}   attendu {attendu!r}"))
    if not ok:
        ECHECS.append(label)


def entrees(volets):
    for v in list(volets["rail"].values()) + list(volets["tuiles"].values()):
        for g in v.get("groupes", []):
            for e in g["entrees"]:
                yield v, e


# ── 1. Filtrage par rôle ─────────────────────────────────────────────────────
sup = pv.volets_pour("superadmin")
fab = pv.volets_pour("fabrication")
adv = pv.volets_pour("administration_ventes")

check("superadmin voit les paramètres", "settings" in sup["rail"])
check("superadmin voit la base", "db" in sup["rail"])
check("fabrication ne voit pas les paramètres", "settings" not in fab["rail"], True)
check("fabrication ne voit pas la base", "db" not in fab["rail"], True)
check("fabrication garde profil et tâches",
      "profil" in fab["rail"] and "taches" in fab["rail"])

cles_adv = [e["cle"] for g in adv["rail"]["settings"]["groupes"] for e in g["entrees"]]
check("ADV voit les comptes", "set_users" in cles_adv)
check("ADV ne voit pas la promotion", "set_promote" not in cles_adv, True)

fuite = [e["cle"] for _v, e in entrees(sup) if "roles" in e]
check("aucune liste de rôles n'est envoyée au front", fuite, [])

check("le volet ERP survit au filtrage bien qu'il soit vide",
      sup["rail"].get("erp", {}).get("source"), "erp")

# ── 2. Les URL existent ──────────────────────────────────────────────────────
# Routes déclarées dans le code, relevées à la source plutôt que par un import
# de `main` : le test reste rapide et ne démarre aucune base.
ROUTES = set()
for f in list((RACINE / "app").rglob("*.py")):
    txt = f.read_text(encoding="utf-8", errors="ignore")
    ROUTES.update(re.findall(r'@(?:router|app)\.get\(\s*"([^"{}]+)"', txt))

# `/perf-postes` et consorts sont déclarés sur un router sans préfixe ; ceux qui
# en ont un sont montés dans main.py, hors du champ de cette regex. Le catalogue
# ne pointe que vers des pages, jamais vers des routes préfixées d'API.
manquantes = []
for v, e in entrees(sup):
    chemin = e["url"].split("#")[0].split("?")[0]
    if chemin not in ROUTES:
        manquantes.append((e["cle"], e["url"]))
for cle, volet in list(sup["rail"].items()) + list(sup["tuiles"].items()):
    pied = volet.get("pied") or {}
    if pied:
        chemin = pied["url"].split("#")[0].split("?")[0]
        if chemin not in ROUTES:
            manquantes.append((cle + ".pied", pied["url"]))
check("toutes les URL du catalogue existent", manquantes, [])

# ── 3. Les ancres correspondent aux onglets réels des pages ─────────────────
# Chaque page expose la liste de ses onglets valides ; une ancre inconnue ouvre
# silencieusement l'onglet par défaut.
ANCRES = {
    "/profil": (RACINE / "app/web/profil_page.py", r"PROFIL_VALID_TABS\s*=\s*\[([^\]]*)\]"),
    "/expe": (RACINE / "app/web/expe_assets.py", r"EXPE_VALID_TABS\s*=\s*\[([^\]]*)\]"),
    "/fabrication": (RACINE / "app/web/fabrication_page.py", r"FAB_VALID_TABS\s*=\s*\[([^\]]*)\]"),
    "/taches": (RACINE / "app/web/taches_page.py", r"VALID_VIEWS\s*=\s*\[([^\]]*)\]"),
    "/coffre": (RACINE / "app/web/coffre_page.py", r"COFFRE_VALID_TABS\s*=\s*\[([^\]]*)\]"),
    "/rh/coffre": (RACINE / "app/web/rh_coffre_page.py", r"RH_COFFRE_VALID_TABS\s*=\s*\[([^\]]*)\]"),
    "/planning-rh": (RACINE / "app/web/planning_rh_page.py", r"PRH_VALID_TABS\s*=\s*\[([^\]]*)\]"),
    "/qualite": (RACINE / "app/web/qualite_page.py", r"QUALITE_PERSIST_VIEWS\s*=\s*\[([^\]]*)\]"),
}
# Deux pages ne déclarent pas de liste : leurs onglets sont les valeurs de
# `data-tab` du menu (Paramètres) et les clés de VIEW_META (Maintenance).
ANCRES_DIRECTES = {
    "/settings": (RACINE / "app/web/settings_page.py", r'data-tab="([a-z_-]+)"'),
    "/maintenance": (RACINE / "app/web/maintenance_page.py",
                     r"^\s*'?([a-z-]+)'?\s*:\s*\{\s*title:"),
}
for _p, (_f, _m) in ANCRES_DIRECTES.items():
    _n = len(set(re.findall(_m, _f.read_text(encoding="utf-8", errors="ignore"), re.M)))
    check(f"les onglets de {_p} sont bien relevés ({_n})", _n >= 3)

mauvaises = []
for v, e in entrees(sup):
    if "#" not in e["url"]:
        continue
    chemin, ancre = e["url"].split("#", 1)
    valides = set()
    if chemin in ANCRES:
        fichier, motif = ANCRES[chemin]
        m = re.search(motif, fichier.read_text(encoding="utf-8", errors="ignore"))
        valides = set(re.findall(r"'([^']+)'", m.group(1))) if m else set()
    elif chemin in ANCRES_DIRECTES:
        fichier, motif = ANCRES_DIRECTES[chemin]
        valides = set(re.findall(motif, fichier.read_text(encoding="utf-8", errors="ignore"),
                                 re.M))
    if valides and ancre not in valides:
        mauvaises.append((e["cle"], e["url"], sorted(valides)))
check("toutes les ancres correspondent à un onglet existant", mauvaises, [])

# ── 3 bis. Les paramètres d'URL correspondent aux listes blanches des pages ──
# Une valeur hors liste est ignorée en silence par la page, qui ouvre son onglet
# par défaut : le raccourci a l'air de marcher et n'emmène pas au bon endroit.
PARAMS = {
    ("/stock", "tab"): (RACINE / "app/web/stock_page.py",
                        r"urlTab\s*&&\s*\[([^\]]*)\]\.includes\(urlTab\)"),
    ("/prod", "page"): (RACINE / "static/mysifa_prod_core.js",
                        r"const allowed\s*=\s*new Set\(\[([^\]]*)\]\)"),
    ("/planning", "vue"): (RACINE / "app/web/planning_page.py",
                           r"PLANNING_VUES\s*=\s*\[(.*?)\];"),
}
mauvais_params = []
for (chemin, nom), (fichier, motif) in PARAMS.items():
    m = re.search(motif, fichier.read_text(encoding="utf-8", errors="ignore"), re.S)
    valides = set(re.findall(r"[\"']([a-z_-]+)[\"']", m.group(1))) if m else set()
    check(f"liste blanche {chemin}?{nom}= relevée ({len(valides)})", len(valides) >= 3)
    for v, e in entrees(sup):
        base = e["url"].split("#")[0]
        if "?" not in base:
            continue
        c, q = base.split("?", 1)
        if c != chemin or not q.startswith(nom + "="):
            continue
        val = q.split("=", 1)[1]
        if valides and val not in valides:
            mauvais_params.append((e["cle"], e["url"], sorted(valides)))
check("toutes les valeurs de paramètre existent", mauvais_params, [])

# ── 4. Les icônes existent dans le jeu SVG ──────────────────────────────────
html = (RACINE / "app/web/html.py").read_text(encoding="utf-8", errors="ignore")
dispo = set(re.findall(r"^\s*'([a-z-]+)':\s*'<", html, re.M))
inconnues = sorted({e.get("icone") for _v, e in entrees(sup) if e.get("icone") not in dispo})
check("toutes les icônes d'entrée existent", inconnues, [])
tetes = sorted({v.get("icone") for v in sup["rail"].values() if v.get("icone") not in dispo})
check("toutes les icônes de volet existent", tetes, [])

# ── 5. Un volet sans au moins deux destinations n'a pas lieu d'être ─────────
maigres = [cle for cle, v in sup["tuiles"].items()
           if sum(len(g["entrees"]) for g in v["groupes"]) < 2]
check("chaque volet de tuile propose au moins deux destinations", maigres, [])

print()
if ECHECS:
    print(f"ECHEC : {len(ECHECS)} verification(s)")
    sys.exit(1)
print("Toutes les verifications passent.")
