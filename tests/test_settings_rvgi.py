# -*- coding: utf-8 -*-
"""Les onglets Clients et Fournisseurs des Paramètres, API entièrement stubée."""
import json, re, sys, urllib.parse
from playwright.sync_api import sync_playwright

import os
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(RACINE + "/app/web/settings_page.py", encoding="utf-8").read()
html = re.search(r'SETTINGS_HTML = r"""(.*)"""\s*$', src, re.S).group(1)
html = (html.replace("__V_LABEL__", "v3.0.0")
            .replace("__SETTINGS_VISIBILITY_JSON__",
                     json.dumps({k: True for k in
                                 ("contacts", "referentiels", "utilisateurs", "systeme",
                                  "production", "qualite", "expeditions", "achats")}))
            .replace("/*__TRACA_GUIDE__*/", ""))
MODULE = open(RACINE + "/static/mysifa_rvgi_tiers.js", encoding="utf-8").read()

CLIENTS = [
    {"id": 1, "numero": 129, "code": "CEDAM", "raison_sociale": "CEDAM",
     "cp": "67210", "ville": "OBERNAI", "pays": "FRANCE", "telephone": "03 88 95 00 00",
     "email": "contact@cedam.fr", "contact_nom": "M. Weber", "etat": "Normal",
     "groupe": "CEDAM", "encours_autorise": 25000,
     "rvgi_numero": 129, "rvgi_code": "CEDAM", "rvgi_etat": "lie", "rvgi_bloq": 1,
     "rvgi_maj_le": "2026-08-26T09:30:00"},
    {"id": 2, "numero": 1361, "code": "SONELOG LE PONTET", "raison_sociale": "SONELOG LE PONTET",
     "cp": "84130", "ville": "LE PONTET", "pays": "FRANCE", "telephone": "",
     "email": "", "etat": "Bloqué",
     "rvgi_numero": 1361, "rvgi_code": "SONELOG LE PONTET", "rvgi_etat": "lie", "rvgi_bloq": 2},
    {"id": 3, "numero": None, "code": "", "raison_sociale": "CLIENT SAISI À LA MAIN",
     "ville": "LOOS", "pays": "FRANCE", "email": "local@sifa.fr", "etat": "Normal",
     "rvgi_etat": "manuel"},
    {"id": 4, "numero": 257, "code": "ETICSERVICESC", "raison_sociale": "SIGNUM",
     "cp": "59139", "ville": "WATTIGNIES", "pays": "FRANCE", "etat": "Normal",
     "rvgi_numero": 257, "rvgi_etat": "a_confirmer"},
]
FOURNISSEURS = [
    {"id": 1, "nom": "CPI", "has_fsc": 1, "licence": "FSC-C012345", "actif": 1,
     "ville": "ROUBAIX", "pays": "FR", "categories": ["papier"], "nb_contacts": 2,
     "rvgi_numero": 257, "rvgi_code": "CPI", "rvgi_etat": "lie", "rvgi_bloq": 1,
     "rvgi_rs": "CPI", "rvgi_maj_le": "2026-08-26T09:30:00"},
    {"id": 2, "nom": "Beule S.A.", "has_fsc": 0, "actif": 1, "nb_contacts": 0,
     "rvgi_numero": 129, "rvgi_etat": "a_confirmer", "rvgi_rs": "BEULE"},
    {"id": 3, "nom": "FOURNISSEUR MAISON", "has_fsc": 0, "actif": 1, "nb_contacts": 0,
     "rvgi_etat": "manuel"},
]
ETAT = {
    "client": {"perimetre": "client", "label": "Clients", "disponible": True,
               "rvgi_total": 1264, "rvgi_actifs": 551, "mysifa_total": 4, "lies": 2,
               "a_confirmer": 1, "manuels": 1, "rvgi_seuls": 3,
               "champs_pilotes": ["adresse1", "code", "email", "pays", "raison_sociale",
                                  "siret", "telephone", "ville"],
               "miroir": "2026-08-26T05:00:00", "derniere_synchro": None},
    "fournisseur": {"perimetre": "fournisseur", "label": "Fournisseurs", "disponible": True,
                    "rvgi_total": 1217, "rvgi_actifs": 199, "mysifa_total": 3, "lies": 1,
                    "a_confirmer": 1, "manuels": 1, "rvgi_seuls": 2,
                    "champs_pilotes": ["adresse", "email", "siret", "telephone", "ville"],
                    "miroir": "2026-08-26T05:00:00", "derniere_synchro": None},
}

erreurs, appels = [], []

def route(r):
    u = urllib.parse.urlparse(r.request.url)
    p, qs = u.path, urllib.parse.parse_qs(u.query)
    appels.append(p)
    if p == "/settings":
        return r.fulfill(status=200, content_type="text/html; charset=utf-8", body=html)
    if p == "/static/mysifa_rvgi_tiers.js":
        return r.fulfill(status=200, content_type="application/javascript", body=MODULE)
    if p.startswith("/static/"):
        return r.fulfill(status=200,
                         content_type="text/css" if p.endswith(".css") else "application/javascript",
                         body="")
    if p == "/api/auth/me":
        return r.fulfill(json={"nom": "Eugène Leconte", "role": "superadmin", "email": "e@sifa.fr"})
    if p == "/api/clients":
        return r.fulfill(json={"total": len(CLIENTS), "limit": 2000, "offset": 0,
                               "items": CLIENTS, "etats": ["Normal", "Bloqué"]})
    if p.startswith("/api/clients/"):
        cid = int(p.rsplit("/", 1)[1])
        return r.fulfill(json=next((c for c in CLIENTS if c["id"] == cid), {}))
    if p == "/api/fournisseurs":
        return r.fulfill(json=FOURNISSEURS)
    if p == "/api/rvgi-tiers/etat":
        return r.fulfill(json=ETAT[(qs.get("perimetre") or ["client"])[0]])
    if p == "/api/rvgi-tiers/a-confirmer":
        per = (qs.get("perimetre") or ["client"])[0]
        return r.fulfill(json={"perimetre": per, "total": 1, "lignes": [
            {"id": 4, "motif": "nom", "score": 0.9,
             "mysifa": {"nom": "SIGNUM", "siret": None, "ville": "WATTIGNIES"},
             "rvgi": {"numero": 257, "code": "ETICSERVICESC", "rs": "SIGNUM",
                      "siret": None, "ville": "WATTIGNIES", "actif": True}}]})
    if p == "/api/rvgi-tiers/rvgi-seuls":
        return r.fulfill(json={"perimetre": "client", "lignes": [
            {"numero": 1, "code": "3SUISSES", "rs": "3 SUISSES", "ville": "CROIX CEDEX",
             "cp": "59170", "siret": None, "actif": False},
            {"numero": 891, "code": "INGREDIA", "rs": "INGREDIA SA", "ville": "ARRAS",
             "cp": "62033", "siret": "12345678900011", "actif": True}]})
    if p == "/api/rvgi-tiers/fiche":
        return r.fulfill(json={"perimetre": (qs.get("perimetre") or ["client"])[0],
            "numero": int((qs.get("numero") or [0])[0]),
            "champs_pilotes": ["raison_sociale", "adresse1", "ville", "siret", "email"],
            "fiche": {"code": "CEDAM", "rs": "CEDAM", "adr1": "12 rue de la Gare",
                      "adr2": None, "cp": "67210", "vil": "OBERNAI", "pays": "FRANCE",
                      "siret": "35346402700013", "ntva": "FR12353464027", "rcs": None,
                      "tel": "03 88 95 00 00", "fax": None, "mail": "contact@cedam.fr",
                      "_groupe": None, "_representant": "TASSART Philippe",
                      "nbjliv": 2, "bloq": 1}})
    if p == "/api/rvgi-tiers/contacts":
        return r.fulfill(json={"numero": 257, "contacts": [
            {"numint": 1, "nom": "DUPONT", "prenom": "Marie", "service": "Commercial",
             "tel": "03 20 00 00 00", "gsm": None, "fax": None,
             "mail": "m.dupont@cpi.fr", "principal": True}]})
    if p == "/api/rvgi-tiers/adresses":
        return r.fulfill(json={"numero": 129, "adresses": [
            {"numadr": 1, "rs": "CEDAM Logistique", "adr1": "ZI Nord", "adr2": None,
             "cp": "67210", "ville": "OBERNAI", "pays": "FRANCE",
             "contact": "Paul Weber", "contact_mail": "p.weber@cedam.fr", "contact_tel": None}]})
    if p == "/api/rvgi-tiers/synchroniser":
        return r.fulfill(json={"perimetre": "client", "lies": 552, "nouveaux": 419,
                               "mis_a_jour": 3, "a_confirmer": 0, "champs_ecrits": 14,
                               "rvgi_total": 1264, "rvgi_actifs": 551})
    if p == "/api/rvgi-tiers/lier":
        return r.fulfill(json={"ok": True})
    if p == "/api/rvgi-tiers/candidats":
        return r.fulfill(json={"candidats": [
            {"numero": 891, "code": "INGREDIA", "rs": "INGREDIA SA",
             "ville": "ARRAS", "siret": None, "actif": True}]})
    if p == "/api/rvgi-tiers/importer":
        return r.fulfill(json={"ok": True, "importes": 1})
    # Tout le reste des Paramètres : une réponse vide et valide.
    if p.startswith("/api/"):
        return r.fulfill(json=[] if p.rstrip("/").endswith(("s", "certifs")) else {})
    return r.fulfill(status=404, json={"detail": "non stubé " + p})

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=os.environ.get("PW_CHROMIUM", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"))
    pg = b.new_page(viewport={"width": 1500, "height": 980})
    pg.on("pageerror", lambda e: erreurs.append("pageerror: %s" % e))
    pg.on("console", lambda m: erreurs.append("console %s: %s" % (m.type, m.text))
          if m.type == "error" else None)
    pg.route("**/*", route)
    pg.goto("https://mysifa.test/settings", wait_until="networkidle")

    def ok(c, q):
        print(("  OK   " if c else "  ECHEC") + " " + q)
        if not c: erreurs.append("assertion: " + q)

    print("— le module est chargé")
    ok(pg.evaluate("()=>!!window.MysRvgiTiers"), "MysRvgiTiers est disponible")

    print("— onglet Clients")
    pg.evaluate("()=>{document.querySelector('[data-tab=\"clients\"]').click();}")
    pg.wait_for_selector("#cli-tbody .cli-row")
    ok(pg.locator("#cli-tbody .cli-row").count() == 4, "les 4 clients sont listés")
    ths = [t.strip() for t in pg.locator("#cli-table thead th").all_inner_texts()]
    ok(len([t for t in ths if t]) == 4, "quatre colonnes, plus la colonne d'action : " + " | ".join(ths))
    l1 = pg.locator("#cli-tbody .cli-row").first.inner_text().replace("\n", " ")
    ok("CEDAM" in l1 and "OBERNAI" in l1, "identité et localisation sur la même ligne : " + l1)
    ok(pg.locator("#cli-tbody .rt-chip.erp").count() >= 1, "les fiches pilotées portent la pastille RVGI")
    ok(pg.locator("#cli-tbody .rt-chip.loc").count() == 1, "la fiche saisie main porte « MySifa »")
    ok(pg.locator("#cli-tbody .rt-chip.att").count() == 1, "celle à confirmer est distinguée")
    ok(pg.locator("#cli-tbody .rt-chip.blo").count() == 1, "le client bloqué dans RVGI est signalé")

    pg.screenshot(path="/tmp/liste_clients.png")

    print("— le bandeau de synchro")
    pg.wait_for_selector("#cli-rvgi-barre .rt-a")
    t = pg.locator("#cli-rvgi-barre").inner_text().replace("\n", " ")
    ok("2 fiche" in t and "1264" not in t, "il dit ce qui est piloté, pas la volumétrie brute : " + t)
    ok("miroir relevé le 26/08/2026" in t, "et depuis quand le miroir date")
    ok(pg.locator('#cli-rvgi-barre [data-rt="sync"]').count() == 1, "le bouton de synchro est là")
    ok(pg.locator('#cli-rvgi-barre [data-rt="conf"]').count() == 1, "« à confirmer » aussi")

    print("— confirmer un rapprochement")
    pg.locator('#cli-rvgi-barre [data-rt="conf"]').click()
    pg.wait_for_selector(".rt-fond .rt-tab")
    d = pg.locator(".rt-fond").inner_text()
    ok("SIGNUM" in d and "ETICSERVICESC" in d, "les deux fiches sont montrées côte à côte")
    ok("le nom" in d, "le motif du rapprochement est dit")
    pg.locator('.rt-fond [data-rt="oui"]').first.click()
    pg.wait_for_timeout(400)
    ok(pg.locator(".rt-fond .rt-chip.erp").count() >= 1, "la ligne confirmée le montre")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)

    print("— la fiche d'un client piloté")
    pg.evaluate("()=>openCliModal(1)")
    pg.wait_for_timeout(500)
    ok(pg.locator("#cli-raison").get_attribute("readonly") is not None,
       "la raison sociale est en lecture seule")
    ok("RVGI" in (pg.locator("#cli-raison").get_attribute("title") or ""),
       "et on voit pourquoi : " + (pg.locator("#cli-raison").get_attribute("title") or ""))
    ok(pg.locator("#cli-notes").get_attribute("readonly") is None,
       "les notes restent modifiables")
    ok(pg.locator("#cli-delete-btn").is_hidden(), "supprimer est retiré sur une fiche pilotée")
    pg.locator('[data-clisub="cli-tab-rvgi"]').click()
    pg.wait_for_selector("#cli-rvgi-bloc .rt-grille")
    r = pg.locator("#cli-rvgi-bloc").inner_text()
    ok("35346402700013" in r, "la fiche RVGI est affichée en regard")
    ok("Adresses de livraison RVGI" in r, "avec ses adresses de livraison")
    ok("CEDAM Logistique" in r, "et leur destinataire")
    pg.screenshot(path="/tmp/clients.png")

    print("— une fiche saisie à la main")
    pg.evaluate("()=>{closeCliModal();openCliModal(3);}")
    pg.wait_for_timeout(500)
    ok(pg.locator("#cli-raison").get_attribute("readonly") is None,
       "ses champs restent saisissables")
    ok(pg.locator("#cli-delete-btn").is_visible(), "et elle peut être supprimée")
    pg.locator('[data-clisub="cli-tab-rvgi"]').click()
    pg.wait_for_selector('#cli-rvgi-bloc [data-rt="q"]')
    ok(pg.locator('#cli-rvgi-bloc [data-rt="q"]').count() == 1,
       "un champ propose de la relier à une fiche RVGI")
    pg.evaluate("()=>closeCliModal()")

    print("— onglet Fournisseurs")
    pg.evaluate("()=>{document.querySelector('[data-tab=\"fournisseurs\"]').click();}")
    pg.wait_for_selector("#four-table-wrap .f2-row")
    ok(pg.locator("#four-table-wrap .f2-row").count() == 3, "les 3 fournisseurs sont listés")
    ok(pg.locator("#four-table-wrap .rt-chip").count() >= 3, "chacun porte son origine")
    ok(pg.locator("#four-rvgi-barre .rt-a").count() == 1, "le bandeau est là aussi")
    ths = [t.strip().upper() for t in pg.locator(".four-table thead th").all_inner_texts()]
    ok(any("FOURNISSEUR" in t for t in ths) and any("FSC" in t for t in ths),
       "les colonnes d'origine sont intactes : " + " | ".join(ths))

    print("— la fiche d'un fournisseur")
    # CPI est la fiche pilotée par RVGI ; la liste est triée par nom, donc
    # on l'ouvre par son id plutôt que par sa position.
    pg.evaluate("()=>openFournisseurFiche(1)")
    pg.wait_for_selector("#f2-tabs .f2-tab")
    onglets = [t.strip() for t in pg.locator("#f2-tabs .f2-tab").all_inner_texts()]
    ok("RVGI" in [o.split("\n")[0] for o in onglets], "un onglet RVGI complète la fiche : " + ", ".join(onglets))
    ok(len(onglets) == 9, "et les 8 onglets d'origine sont là (%d au total)" % len(onglets))
    pg.locator('#f2-tabs [data-f2tab="rvgi"]').click()
    pg.wait_for_selector("#f2-rvgi-bloc .rt-grille")
    r = pg.locator("#f2-rvgi-bloc").inner_text()
    ok("Interlocuteurs dans RVGI" in r, "les interlocuteurs RVGI sont montrés")
    ok("Marie" in r, "avec leur nom")
    ok("Détacher" in r, "et on peut détacher la fiche")
    pg.screenshot(path="/tmp/fournisseurs.png")

    print("— on n'a rien cassé")
    pg.locator('#f2-tabs [data-f2tab="identite"]').click()
    pg.wait_for_timeout(300)
    ok(pg.locator("#f2-body").inner_text().strip() != "", "l'onglet Identité rend toujours quelque chose")
    pg.locator('#f2-tabs [data-f2tab="synthese"]').click()
    pg.wait_for_timeout(300)
    ok(pg.locator("#f2-body .f2-block").count() >= 1, "la Synthèse aussi")

    b.close()

if erreurs:
    print("\n%d PROBLÈME(S) :" % len(erreurs))
    for e in erreurs[:14]:
        print("   " + str(e)[:220])
    sys.exit(1)
print("\nTout passe.")
