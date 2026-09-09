"""Reprise complete des devis commerciaux — a lancer une fois.

Parcourt tout le dossier, sans fenetre de date. A reserver au premier
demarrage : ensuite, `devis_import_quotidien.py` suffit.

    python devis_import_initial.py --cle msk_xxxx --simulation
    python devis_import_initial.py --cle msk_xxxx

Commencer TOUJOURS par --simulation : la sortie liste ce qui partirait, sans
rien envoyer. C'est le seul moyen de voir si le dossier contient ce qu'on
croit avant d'en pousser plusieurs centaines.

`--max` limite un passage et permet de reprendre : l'index local retient ce
qui est deja parti, et le serveur deduplique de toute facon sur le contenu.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from devis_import_commun import arguments_communs, importer, log, verifier_cle  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Reprise complete des devis.")
    arguments_communs(ap)
    ap.add_argument("--annee-min", type=int, default=0,
                    help="Ignorer les sous-dossiers d'annee anterieurs (0 = tout prendre)")
    ap.add_argument("--max", type=int, default=0,
                    help="S'arreter apres N fichiers (0 = pas de limite)")
    ap.add_argument("--pause", type=float, default=0.0,
                    help="Pause entre deux envois, en secondes")
    args = ap.parse_args()

    if not args.simulation:
        verifier_cle(args.cle)

    log("Reprise complete dans %s" % args.dossier)
    bilan = importer(
        args.dossier, args.url, args.cle, args.index,
        age_min=120, annee_min=args.annee_min, simulation=args.simulation,
        pause=args.pause, max_fichiers=args.max,
    )
    return 1 if bilan["echecs"] else 0


if __name__ == "__main__":
    sys.exit(main())
