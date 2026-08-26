# -*- coding: utf-8 -*-
"""Le bloc « Réception RVGI » dans le formulaire de réception matière."""
import json, os, re, sys, urllib.parse
from playwright.sync_api import sync_playwright

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(RACINE + "/app/web/stock_page.py", encoding="utf-8").read()
html = src[src.index('STOCK_HTML = r"""') + len('STOCK_HTML = r"""'):]
html = html[:html.rindex('"""')]
html = html.replace("__APP_ORG_NAME__", "SIFA").replace("__STOCK_UNITE_VENTE_DEFAUT__", "u")
# Les vrais modules dont la page dépend : les stuber à vide fait planter le
# rendu (`_SM.utils`), et on ne testerait plus rien.
def _lire(nom):
    try:
        return open(RACINE + "/static/" + nom, encoding="utf-8").read()
    except OSError:
        return ""
MODULES = {n: _lire(n) for n in ("mysifa_rvgi_reception.js", "mysifa_stock_modals.js",
                                 "mysifa_fournisseur_picker.js")}

RECEPTIONS = [
    {"cde": 5721, "bl": "AE0049887", "date_reception": "2026-08-05",
     "date_commande": "2026-07-02", "numfou": 42, "fournisseur": "ITASA",
     "fournisseur_id": 9, "fournisseur_mysifa": "ITASA", "certificat_fsc": "FSC-C001",
     "nb_lignes": 2, "nb_frais": 0, "qte_totale": 8, "natures": ["matiere"],
     "ecran": "matiere",
     "lignes": [
       {"article": "552/0005", "designation": "Glassine Siliconé Jaune - SUPER FA",
        "qte": 5, "qte_commandee": 5, "laize_mm": 333, "grammage": 58,
        "matiere_id": 17, "matiere_nom": "Glassine jaune 58 g", "categorie": "glassine",
        "produit_id": None, "nature": "matiere", "matiere_rvgi": "Glassine Siliconé Jaune"},
       {"article": "552/0009", "designation": "Glassine Siliconé Blanc",
        "qte": 3, "qte_commandee": 3, "laize_mm": 440, "grammage": 60,
        "matiere_id": None, "matiere_nom": None, "categorie": None,
        "produit_id": None, "nature": "matiere_rvgi", "matiere_rvgi": "Glassine blanc"},
     ]},
    # Une réception de matière dont le fournisseur n'est pas relié, et qui
    # porte une ligne de frais : les deux cas qu'il faut voir à l'écran.
    {"cde": 5952, "bl": "BL10742", "date_reception": "2026-08-05",
     "numfou": 1177, "fournisseur": "Cartonnages Auguste PAULET", "fournisseur_id": None,
     "nb_lignes": 2, "nb_frais": 1, "qte_totale": 300000, "natures": ["frais", "matiere"],
     "ecran": "matiere",
     "lignes": [
       {"article": "1164/0014", "designation": "Bague Ø 19.5 mm", "qte": 300000,
        "matiere_id": None, "matiere_rvgi": "Bague carton", "laize_mm": None,
        "produit_id": None, "nature": "matiere_rvgi"},
       {"article": "FR/FRAIS_DE_CLICHE", "designation": "Frais de cliché", "qte": 2,
        "matiere_id": None, "produit_id": None, "nature": "frais"},
     ]},
    # Celle-ci est une réception de PRODUITS FINIS : l'écran matière ne doit
    # pas la proposer, sinon on rattacherait une bobine à des étiquettes.
    {"cde": 5963, "bl": "292225", "date_reception": "2026-08-24",
     "numfou": 1092, "fournisseur": "QRT Graphique", "fournisseur_id": None,
     "nb_lignes": 1, "nb_frais": 0, "qte_totale": 200000, "natures": ["produit"],
     "ecran": "produit",
     "lignes": [
       {"article": "1004/0207", "designation": "Etiquette diamètre 50 mm", "qte": 200000,
        "matiere_id": None, "produit_id": 5, "produit_nom": "Etiq 50", "nature": "produit"},
     ]},
]

erreurs = []

def route(r):
    u = urllib.parse.urlparse(r.request.url)
    p, qs = u.path, urllib.parse.parse_qs(u.query)
    if p == "/stock":
        return r.fulfill(status=200, content_type="text/html; charset=utf-8", body=html)
    base = p.rsplit("/", 1)[-1].split("?")[0]
    if base in MODULES and MODULES[base]:
        return r.fulfill(status=200, content_type="application/javascript", body=MODULES[base])
    if p.startswith("/static/"):
        return r.fulfill(status=200,
            content_type="text/css" if p.endswith(".css") else "application/javascript", body="")
    if p == "/api/auth/me":
        return r.fulfill(json={"nom": "Eugène", "role": "superadmin", "email": "e@sifa.fr"})
    if p == "/api/rvgi/receptions":
        q = (qs.get("q") or [""])[0].lower()
        out = [x for x in RECEPTIONS
               if not q or q in str(x["bl"]).lower() or q in x["fournisseur"].lower()
               or q in str(x["cde"])]
        return r.fulfill(json={"receptions": out,
                               "miroir": {"present": True, "releve_le": "2026-08-26T05:00:00"}})
    if p.startswith("/api/"):
        return r.fulfill(json=[] if p.rstrip("/").endswith(("s", "laizes")) else {})
    return r.fulfill(status=404, json={"detail": "non stubé " + p})

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=os.environ.get(
        "PW_CHROMIUM", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"))
    pg = b.new_page(viewport={"width": 1400, "height": 1000})
    pg.on("pageerror", lambda e: erreurs.append("pageerror: %s" % e))
    pg.on("console", lambda mm: erreurs.append("console %s: %s" % (mm.type, mm.text))
          if mm.type == "error" else None)
    pg.route("**/*", route)
    pg.goto("https://mysifa.test/stock", wait_until="networkidle")

    def ok(c, q):
        print(("  OK   " if c else "  ECHEC") + " " + q)
        if not c: erreurs.append("assertion: " + q)

    print("— le module")
    ok(pg.evaluate("()=>!!window.MysRvgiReception"), "MysRvgiReception est chargé")

    print("— l'onglet Réception")
    pg.evaluate("()=>{S.tab='reception';S.recepSubTab='nouvelle';renderContent();}")
    pg.wait_for_timeout(1500)
    print("      tab =", pg.evaluate("()=>S.tab"),
          "| .rr-bloc =", pg.locator(".rr-bloc").count(),
          "| recep-card =", pg.locator(".recep-card").count(),
          "| erreurs =", erreurs[:3])
    pg.wait_for_selector(".rr-bloc .rr-q", timeout=15000)
    ok(pg.locator(".rr-bloc").count() >= 1, "le bloc RVGI est au-dessus du formulaire")
    y_rvgi = pg.locator(".rr-bloc").first.bounding_box()["y"]
    pk = pg.locator(".recep-picker-card")
    ok(pk.count() == 0 or pk.first.bounding_box()["y"] > y_rvgi,
       "et bien AVANT le choix de la matière")

    print("— chercher une réception")
    pg.locator(".rr-bloc .rr-q").click()
    pg.wait_for_selector(".rr-res .rr-r", timeout=10000)
    ok(pg.locator(".rr-res .rr-r").count() == 2,
       "les 2 réceptions de matière remontent, pas celle de produits finis")
    tout = pg.locator(".rr-res").inner_text()
    ok("292225" not in tout, "la réception de produits finis est écartée de l'écran matière")
    t = pg.locator(".rr-res .rr-r").first.inner_text().replace("\n", " ")
    ok("AE0049887" in t and "ITASA" in t, "n° de BL et fournisseur sur la ligne : " + t)
    ok("matière" in t, "et la nature de la réception est dite")
    t2 = pg.locator(".rr-res .rr-r").nth(1).inner_text().replace("\n", " ")
    ok("fournisseur non relié" in t2, "un fournisseur non relié est signalé : " + t2)

    print("— reprendre une réception")
    pg.locator(".rr-res .rr-r").first.click()
    pg.wait_for_timeout(600)
    ok(pg.locator(".rr-pris").count() == 1, "la réception reprise est affichée")
    ok(pg.locator(".rr-lignes .rr-l").count() == 2, "avec ses deux lignes")
    l1 = pg.locator(".rr-lignes .rr-l").first.inner_text().replace("\n", " ")
    ok("552/0005" in l1 and "333" in l1, "article et laize : " + l1)
    l2 = pg.locator(".rr-lignes .rr-l").nth(1).inner_text().replace("\n", " ")
    ok("inconnu de MySifa" in l2, "une matière que MySifa ignore est signalée : " + l2)

    print("— ce qui a été prérempli")
    ok(pg.evaluate("()=>S.recepFournisseurId") == 9, "le fournisseur est repris")
    ok("AE0049887" in (pg.evaluate("()=>S.recepNote") or ""),
       "le BL part dans la note : " + str(pg.evaluate("()=>S.recepNote")))
    ok(pg.evaluate("()=>S.recepRvgi && S.recepRvgi.cde") == 5721, "le lien RVGI est en mémoire")

    print("— choisir une ligne remplit la matière")
    pg.evaluate("()=>document.querySelectorAll('.rr-lignes .rr-l')[0].click()")
    pg.wait_for_timeout(500)
    ok(pg.evaluate("()=>S.recepMatiereId") == 17, "la matière de la ligne est sélectionnée")
    ok(pg.evaluate("()=>S.recepMatiereRef") == "552/0005", "avec sa référence")
    ok(str(pg.evaluate("()=>S.recepLaizeCustomMm")) == "333", "et sa laize")

    print("— une ligne de frais ne se choisit pas")
    pg.evaluate("()=>{S.recepRvgi=null;renderContent();}")
    pg.wait_for_timeout(400)
    pg.locator(".rr-bloc .rr-q").fill("BL10742")
    # Le champ cherche déjà au focus (liste complète), puis re-cherche 280 ms
    # après la frappe. On attend que la liste se soit resserrée.
    pg.wait_for_function(
        "()=>document.querySelectorAll('.rr-res .rr-r').length===1", timeout=10000)
    n_res = pg.locator(".rr-res .rr-r").count()
    pg.locator(".rr-res .rr-r").first.click()
    pg.wait_for_timeout(900)
    print("      diag: %d resultats, %d blocs rr, cde = %s, lignes = %d"
          % (n_res, pg.locator(".rr-bloc").count(),
             pg.evaluate("()=>S.recepRvgi&&S.recepRvgi.cde"),
             pg.locator(".rr-lignes .rr-l").count()))
    ok(pg.locator(".rr-lignes .rr-l.frais").count() == 1, "la ligne de frais est grisée")

    print("— le contrôle de quantité")
    pg.evaluate("()=>{S.recepRvgiChamp && S.recepRvgiChamp.controle(12);}")
    pg.wait_for_timeout(300)
    c = pg.locator(".rr-ctl").inner_text().replace("\n", " ") if pg.locator(".rr-ctl").count() else ""
    ok("12" in c and "300" in c.replace(" ", "").replace("\xa0", ""),
       "les deux chiffres sont montrés côte à côte : " + c)
    ok("pas un nombre de bobines" in c, "et on dit que ce ne sont pas les mêmes unités")

    pg.screenshot(path="/tmp/reception.png")
    b.close()

if erreurs:
    print("\n%d PROBLÈME(S) :" % len(erreurs))
    for e in erreurs[:12]:
        print("   " + str(e)[:200])
    sys.exit(1)
print("\nTout passe.")
