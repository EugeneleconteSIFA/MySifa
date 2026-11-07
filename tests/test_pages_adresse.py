# -*- coding: utf-8 -*-
"""
Garde-fou : toute page de MySifa porte son état dans l'adresse.

Règle du 15/10/2026 (.claude/rules/url-etat.md) : onglet, filtres, tri,
fenêtre ouverte vont dans l'URL, par le helper commun static/mysifa_url.js.
La règle n'était qu'un texte : rien n'empêchait une nouvelle appli de s'en
passer. Les Paramètres sont restés sans adresse jusqu'au 07/11/2026, et
« Retour » y renvoyait au menu de MySifa au lieu de la Vue d'ensemble.

Ce test bloque :

1. une page HTML de app/web/ (un document <!DOCTYPE html>) qui n'inclut pas
   static/mysifa_url.js et n'est ni dans EXCEPTIONS (avec sa raison), ni dans
   A_BRANCHER (dette connue, datée) ;
2. une page qui inclut le helper sans jamais s'en servir : ni elle, ni aucun
   des static/*.js qu'elle charge n'appelle MySifaUrl.ecrire ;
3. une entrée de A_BRANCHER dont la page est désormais branchée (la retirer),
   et toute entrée qui ne correspond plus à aucun fichier.

Lancer : python3 tests/test_pages_adresse.py
"""

import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
WEB = RACINE / "app" / "web"
STATIC = RACINE / "static"

# Pages qui n'ont pas d'état de navigation à porter. Une raison par ligne :
# « c'est plus simple » n'en est pas une.
EXCEPTIONS = {
    "access_denied.py": "message d'accès refusé, un seul écran",
    "calendrier_invitation_page.py": "réponse d'un invité externe, un seul écran, sans script",
    "mcp_oauth_page.py": "écran de consentement OAuth, une seule décision",
    "ao_portail_page.py": "portail fournisseur externe : l'adresse porte déjà le jeton d'accès",
    "eudr_portail_page.py": "portail fournisseur externe : l'adresse porte déjà le jeton d'accès",
    "expe_portail_page.py": "portail transporteur externe : l'adresse porte déjà le jeton d'accès",
    "portail_espace_page.py": "Espace SIFA externe : l'adresse porte déjà le jeton d'accès",
    "widget_page.py": "widget de bureau embarqué, sans historique de navigation",
    "widget_install_page.py": "page de téléchargement, un seul écran",
    "fsc_label_js.py": "sortie d'impression (étiquette FSC), pas une page",
    "mcp_page.py": "page d'information du serveur MCP, un seul écran",
}

# Dette connue : pages d'appli qui ont des onglets ou des fenêtres et pas
# encore d'adresse. On n'en ajoute pas : une page neuve se branche tout de
# suite. On en retire dès qu'une page est faite (le test le réclame).
A_BRANCHER = {
    "learning_page.py": "MyLearning (07/11/2026) : formation, module et vidéo ouverts",
    "paie_page.py": "Paie (07/11/2026) : période et salarié ouverts",
    "website_page.py": "aperçu du site vitrine (07/11/2026) : le chemin porte la page, à vérifier",
}

FAIL = []


def check(nom, ok, detail=""):
    print(("ok   " if ok else "KO   ") + nom + (("  —  " + detail) if detail and not ok else ""))
    if not ok:
        FAIL.append(nom)


def est_page(src):
    return "<!DOCTYPE html>" in src or "<!doctype html>" in src


def scripts_charges(src):
    return {m for m in re.findall(r"/static/([A-Za-z0-9_./-]+\.js)", src)}


def utilise_helper(src):
    """La page, ou un des scripts statiques qu'elle charge, écrit l'adresse."""
    if "MySifaUrl.ecrire" in src:
        return True
    for nom in scripts_charges(src):
        if nom == "mysifa_url.js":
            continue
        f = STATIC / nom
        if f.exists() and "MySifaUrl.ecrire" in f.read_text(encoding="utf-8", errors="ignore"):
            return True
    return False


pages = {}
for f in sorted(WEB.glob("*.py")):
    src = f.read_text(encoding="utf-8", errors="ignore")
    if est_page(src):
        pages[f.name] = src

check("des pages ont été trouvées", len(pages) >= 20, "%d page(s)" % len(pages))

sans_helper, helper_inutilise, branchees_encore_listees = [], [], []
for nom, src in pages.items():
    a_le_helper = "mysifa_url.js" in src
    if nom in EXCEPTIONS:
        continue
    if nom in A_BRANCHER:
        if a_le_helper:
            branchees_encore_listees.append(nom)
        continue
    if not a_le_helper:
        sans_helper.append(nom)
    elif not utilise_helper(src):
        helper_inutilise.append(nom)

check("toute page d'appli inclut static/mysifa_url.js", not sans_helper,
      ", ".join(sans_helper) + " : brancher l'adresse (.claude/rules/url-etat.md), "
      "ou déclarer la page dans EXCEPTIONS avec sa raison")
check("toute page qui inclut le helper écrit son adresse", not helper_inutilise,
      ", ".join(helper_inutilise) + " : aucun MySifaUrl.ecrire dans la page ni dans ses static/*.js")
check("A_BRANCHER ne liste que des pages encore à faire", not branchees_encore_listees,
      ", ".join(branchees_encore_listees) + " : branchée, la retirer de A_BRANCHER")

orphelines = [n for n in list(EXCEPTIONS) + list(A_BRANCHER) if not (WEB / n).exists()]
check("chaque exception désigne un fichier existant", not orphelines, ", ".join(orphelines))

# Les applis servies par le gabarit commun (MyExpé, MyCompta, MyRH, portail)
# passent par html.py : il charge le helper et le fichier d'adresse de chacune.
gabarit = pages.get("html.py", "")
for appli in ("expe_url.js", "compta_url.js", "myrh_url.js", "portail_url.js"):
    check("le gabarit commun charge " + appli, appli in gabarit)

print()
print("ECHECS : " + ", ".join(FAIL) if FAIL else "TOUT EST VERT")
sys.exit(1 if FAIL else 0)
