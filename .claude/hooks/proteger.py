# -*- coding: utf-8 -*-
"""
PreToolUse sur Edit|Write — refuse d'ecrire dans un fichier qui ne doit jamais
etre modifie par un agent, et prend un instantane du fichier pour que
apres_edition.py puisse mesurer ce que l'edition a change.

Regles appliquees ici (elles etaient consultatives dans le CLAUDE.md) :
  - jamais d'ecriture dans .env (sauf .env.example)
  - jamais d'ecriture dans une base SQLite
  - jamais d'ecriture dans data/ (donnees runtime)
  - jamais d'ecriture dans docs/archive/ (archives figees)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _commun import entree, chemin_edite, lire_texte, compter, memoriser, bloquer, RACINE

INTERDITS = [
    (lambda p: os.path.basename(p) == ".env" or (os.path.basename(p).startswith(".env.") and not p.endswith(".env.example")),
     "Ce fichier contient des secrets et n'est jamais edite par un agent.\n"
     "Si une variable manque, ajoute-la a .env.example (placeholder) et demande\n"
     "a Eugene de la renseigner sur le VPS."),
    (lambda p: p.endswith((".db", ".db-wal", ".db-shm", ".db-journal")),
     "Ecriture dans une base SQLite refusee. Toute modification de schema passe\n"
     "par une migration fichier dans app/core/migrations/ — skill /migration."),
    (lambda p: "/data/" in p.replace("\\", "/") and not p.replace("\\", "/").endswith(".csv"),
     "data/ contient les donnees lues au runtime, pas du code. Rien n'y est ecrit\n"
     "par un agent."),
    (lambda p: "/docs/archive/" in p.replace("\\", "/"),
     "docs/archive/ est une archive figee : on y depose, on n'y edite pas."),
]

payload = entree()
chemin = chemin_edite(payload)
if not chemin:
    sys.exit(0)

absolu = os.path.abspath(chemin)
relatif = absolu[len(os.path.abspath(RACINE)):].replace("\\", "/") or absolu

for predicat, motif in INTERDITS:
    if predicat(absolu.replace("\\", "/")):
        bloquer("Ecriture refusee sur %s\n\n%s" % (relatif.lstrip("/"), motif))

# Instantane avant edition, pour mesurer ce que l'edition ajoute.
metriques = compter(lire_texte(absolu))
if metriques is not None:
    memoriser(absolu, metriques)

sys.exit(0)
