# -*- coding: utf-8 -*-
"""MyStock n'appelle que le toast qui existe dans la page.

Le 11/09/2026, « Entrer en stock » et « Intégrer la ligne prête » (Réception ›
Depuis l'ERP) écrivaient bien l'entrée, mais l'écran ne bougeait pas : le code
appelait `toast()`, qui n'existe pas dans stock_page.py. La ReferenceError
tombait APRÈS la réponse du serveur, donc avant le rechargement de la file.

Le toast de la page est `showToast(message, type)`. Ce test refuse tout appel
nu à `toast(` dans le JavaScript de la page.
"""
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(RACINE, "app", "web", "stock_page.py"), encoding="utf-8").read()

ko = 0
# Appel nu : `toast(` qui n'est ni `showToast(`, ni une méthode (`.toast(`),
# ni une clé d'objet (`toast:`).
# Les lignes de commentaire (`//`, `#`, `*`) peuvent citer le nom sans l'appeler.
nus = []
for m in re.finditer(r"(?<![\w.$`])toast\s*\(", src):
    debut = src.rfind("\n", 0, m.start()) + 1
    fin = src.find("\n", m.start())
    ligne = src[debut:fin]
    if ligne.lstrip().startswith(("//", "#", "*", "/*")):
        continue
    nus.append((src.count("\n", 0, m.start()) + 1, ligne.strip()[:80]))
if nus:
    ko += 1
    print("KO  appels à toast() inexistant :")
    for ligne, extrait in nus:
        print("      ligne %d : %s" % (ligne, extrait))
else:
    print("  OK  aucun appel à toast() nu")

if "function showToast(" in src:
    print("  OK  showToast est défini")
else:
    ko += 1
    print("KO  showToast introuvable")

if ko:
    sys.exit(1)
print("\nTous les cas passent.")
