"""Import quotidien des OF termines scannes — une passe par jour.

Ne regarde que les fichiers modifies dans les N derniers jours (30 par
defaut) : sur un dossier qui contient plusieurs annees d'archives, relire
l'integralite chaque nuit couterait des minutes de reseau pour rien.

La fenetre est volontairement large. Un scan pose en retard, ou un fichier
retouche, reste attrape. Et si un fichier passait quand meme au travers, il
sera repris a la prochaine reprise complete — sans doublon, le serveur
deduplique sur le contenu.

    python of_scans_import_quotidien.py --cle msk_xxxx

Planificateur de taches Windows, tous les jours a 20h00 :

    Programme : C:\\Python3\\python.exe
    Arguments : "C:\\MySifa\\scripts\\of_scans_import_quotidien.py" --cle msk_xxxx
    Demarrer dans : C:\\MySifa\\scripts

Prevoir « Executer meme si l'utilisateur n'est pas connecte » avec un compte
qui voit le lecteur U: — un lecteur mappe a une session n'existe pas pour une
tache planifiee. En cas de doute, utiliser le chemin UNC complet
(\\\\IDEFIX\\users\\Requia\\Scan\\OF SCANNES) plutot que U:.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from of_scans_commun import arguments_communs, importer, log, verifier_cle  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Import quotidien des OF scannes.")
    arguments_communs(ap)
    ap.add_argument("--jours", type=int, default=30,
                    help="Fenetre de modification examinee (defaut : 30 jours)")
    ap.add_argument("--age-min", type=int, default=120,
                    help="Ignorer les fichiers modifies il y a moins de N secondes "
                         "(un PDF encore en cours d'ecriture partirait tronque)")
    ap.add_argument("--annee-min", type=int, default=2026,
                    help="Ignorer les sous-dossiers d'annee anterieurs "
                         "(0 pour tout reprendre)")
    args = ap.parse_args()

    if not args.simulation:
        verifier_cle(args.cle)

    depuis = time.time() - max(1, args.jours) * 86400
    log("Passe quotidienne — %d dernier(s) jour(s) dans %s" % (args.jours, args.dossier))

    bilan = importer(
        args.dossier, args.url, args.cle, args.index,
        age_min=args.age_min, modifie_depuis=depuis, annee_min=args.annee_min,
        simulation=args.simulation,
    )
    # Code de sortie non nul en cas d'echec : le planificateur Windows le
    # remonte, ce qui evite une tache qui « reussit » tous les soirs sans rien
    # envoyer parce que le partage n'est plus monte.
    return 1 if bilan["echecs"] else 0


if __name__ == "__main__":
    sys.exit(main())
