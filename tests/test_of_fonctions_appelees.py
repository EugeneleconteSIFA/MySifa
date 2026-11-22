"""Toute fonction `ofe…` appelée dans la fenêtre OF doit exister.

Constat du 22/11/2026 : le bouton « Signaler » de la fenêtre OF appelait
`ofeSignalerFicheManquante`, effacée par erreur trois jours plus tôt lors
d'une réécriture voisine. Le clic levait une erreur silencieuse dans la
console et rien ne partait au gestionnaire de tâches. `node --check` ne voit
pas ce genre de trou : une fonction absente n'est pas une erreur de syntaxe.

Lancement : `python3 tests/test_of_fonctions_appelees.py`
"""
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FICHIER = os.path.join(RACINE, "static", "mysifa_prod_core.js")


def main() -> int:
    src = open(FICHIER, encoding="utf-8").read()
    definies = set(re.findall(r"\bfunction\s+(ofe[A-Za-z0-9_]*)\s*\(", src))
    definies |= set(re.findall(r"\b(?:const|let|var)\s+(ofe[A-Za-z0-9_]*)\s*=", src))
    appelees = set(re.findall(r"(?<![\w.$'\"])(ofe[A-Za-z0-9_]*)\s*\(", src))
    manquantes = sorted(appelees - definies)
    if manquantes:
        print("KO  fonctions appelées mais absentes : " + ", ".join(manquantes))
        return 1
    print("OK  %d fonctions ofe… appelées, toutes définies." % len(appelees))
    return 0


if __name__ == "__main__":
    sys.exit(main())
