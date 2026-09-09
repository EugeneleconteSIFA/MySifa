"""Import quotidien des devis commerciaux — une passe par jour.

Ne regarde que les fichiers modifies dans les N derniers jours (30 par
defaut) et que les sous-dossiers de l'annee en cours : sur un dossier qui
porte plusieurs annees de devis, relire l'integralite chaque nuit couterait
des minutes de reseau pour rien.

La fenetre est volontairement large. Un devis pose en retard, ou un classeur
retouche par le commercial, reste attrape — et un classeur retouche DOIT
repartir, puisque son contenu a change : le serveur le verra comme un nouveau
document et l'ancienne version restera en base a cote. C'est voulu : deux
versions d'un devis ne sont pas un doublon, ce sont deux devis.

    python devis_import_quotidien.py --cle msk_xxxx

Planificateur de taches Windows, tous les jours a 20h30 :

    Programme : C:\\Python3\\python.exe
    Arguments : "C:\\MySifa\\scripts\\devis_import_quotidien.py" --cle msk_xxxx
    Demarrer dans : C:\\MySifa\\scripts

Prevoir « Executer meme si l'utilisateur n'est pas connecte » avec un compte
qui voit le lecteur U: — un lecteur mappe a une session n'existe pas pour une
tache planifiee. En cas de doute, utiliser le chemin UNC complet plutot que U:.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from devis_import_commun import arguments_communs, importer, log, verifier_cle  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Import quotidien des devis commerciaux.")
    arguments_communs(ap)
    ap.add_argument("--jours", type=int, default=30,
                    help="Fenetre de modification examinee (defaut : 30 jours)")
    ap.add_argument("--age-min", type=int, default=120,
                    help="Ignorer les fichiers modifies il y a moins de N secondes "
                         "(un classeur encore en cours de copie partirait tronque)")
    ap.add_argument("--annee-min", type=int, default=0,
                    help="Ignorer les sous-dossiers d'annee anterieurs "
                         "(defaut : l'annee en cours ; 0 la calcule, -1 prend tout)")
    args = ap.parse_args()

    if not args.simulation:
        verifier_cle(args.cle)

    # Annee en cours par defaut, et recalculee a chaque execution : une valeur
    # figee dans le planificateur cesserait de ramasser les devis au 1er janvier
    # sans que rien ne le signale.
    if args.annee_min == 0:
        annee_min = datetime.now().year
    elif args.annee_min < 0:
        annee_min = 0
    else:
        annee_min = args.annee_min

    depuis = time.time() - max(1, args.jours) * 86400
    log("Passe quotidienne — %d dernier(s) jour(s), annee >= %s, dans %s"
        % (args.jours, annee_min or "toutes", args.dossier))

    bilan = importer(
        args.dossier, args.url, args.cle, args.index,
        age_min=args.age_min, modifie_depuis=depuis, annee_min=annee_min,
        simulation=args.simulation,
    )
    # Code de sortie non nul en cas d'echec : le planificateur Windows le
    # remonte, ce qui evite une tache qui « reussit » tous les soirs sans rien
    # envoyer parce que le partage n'est plus monte.
    return 1 if bilan["echecs"] else 0


if __name__ == "__main__":
    sys.exit(main())
