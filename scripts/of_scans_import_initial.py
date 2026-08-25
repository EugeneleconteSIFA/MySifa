"""Reprise complete des OF termines scannes — a lancer UNE fois.

Balaie tout U:\\Requia\\Scan\\OF SCANNES, sous-dossiers d'annee compris
(2023, 2024, 2025, 2026, « 2022 retrouves derriere radiateur »…), et envoie
chaque PDF a MySifa. Rien n'est deplace ni renomme dans le dossier source.

La reprise peut durer : plusieurs milliers de fichiers de ~300 Ko. Elle est
**interruptible et relancable** — l'index local est sauvegarde tous les 25
fichiers, et le serveur refuse de toute facon les contenus deja connus.

    python of_scans_import_initial.py --cle msk_xxxx
    python of_scans_import_initial.py --cle msk_xxxx --simulation
    python of_scans_import_initial.py --cle msk_xxxx --max 500

Commencer par `--simulation` : elle affiche ce qui partirait, sans rien
envoyer. C'est le moment de verifier que le compte de fichiers ressemble a ce
qu'on attend avant d'ouvrir le robinet.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from of_scans_commun import arguments_communs, importer, log, verifier_cle  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Reprise complete des OF scannes.")
    arguments_communs(ap)
    ap.add_argument("--max", type=int, default=0,
                    help="S'arreter apres N fichiers (reprise par tranches)")
    ap.add_argument("--pause", type=float, default=0.0,
                    help="Secondes entre deux envois (menage le reseau)")
    ap.add_argument("--annee-min", type=int, default=2026,
                    help="Ignorer les sous-dossiers d'annee anterieurs "
                         "(0 pour tout reprendre)")
    args = ap.parse_args()

    if not args.simulation:
        verifier_cle(args.cle)

    log("Reprise complete — dossier %s" % args.dossier)
    if args.simulation:
        log("Mode simulation : aucun envoi.")

    bilan = importer(
        args.dossier, args.url, args.cle, args.index,
        age_min=0, modifie_depuis=0.0, annee_min=args.annee_min,
        simulation=args.simulation, pause=args.pause, max_fichiers=args.max,
    )
    return 1 if bilan["echecs"] else 0


if __name__ == "__main__":
    sys.exit(main())
