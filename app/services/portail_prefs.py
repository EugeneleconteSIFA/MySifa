"""Preferences de tuiles du portail : ordre et favoris, par utilisateur.

Le front envoie une liste d'ids de tuiles ; on la valide avant de l'ecrire, et
on la revalide en la relisant. La validation porte sur la FORME de l'id, jamais
sur une liste fermee d'applications.

C'est le coeur de la correction : la liste fermee qui vivait dans `auth.py`
datait de la creation du portail. Chaque application ajoutee ensuite (MyAO,
MyBAT, MyQualite, Coffre, Coffre RH, Maintenance) voyait son id rejete a
l'ecriture ET a la lecture. Symptome vu par l'utilisateur : on epingle MyBAT,
l'etoile s'allume, et le premier rechargement complet la fait disparaitre —
le serveur n'avait rien enregistre. Une tuile nouvelle ne doit pas exiger une
retouche de ce fichier.

Rien a filtrer cote securite au-dela de la forme : ces ids ne servent qu'a
ordonner et epingler des tuiles que le front rend deja selon le role. Un id qui
ne correspond a aucune tuile visible est ignore a l'affichage.

Module volontairement sans dependance (stdlib seule) : il se teste sans base
et sans FastAPI.
"""

import json
import re
from typing import List, Optional

TILE_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")

# Un utilisateur n'a pas cinquante applications : la borne protege la colonne
# d'une liste envoyee en boucle, elle ne dimensionne pas le produit.
MAX_TILES = 40

# Renommages d'ids de tuile : la preference deja enregistree doit survivre.
TILE_ALIAS = {"devis": "pricing"}


def ids_valides(raw) -> List[str]:
    """Ids de tuile propres : forme valide, alias resolus, sans doublon."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
    if not isinstance(raw, list):
        return []
    out: List[str] = []
    seen: set = set()
    for x in raw:
        if not isinstance(x, str):
            continue
        tid = x.strip()
        tid = TILE_ALIAS.get(tid, tid)
        if not TILE_ID_RE.match(tid) or tid in seen:
            continue
        out.append(tid)
        seen.add(tid)
        if len(out) >= MAX_TILES:
            break
    return out


def depuis_db(val) -> List[str]:
    """Ce que la colonne contient -> liste d'ids exploitable par le front."""
    if not val:
        return []
    return ids_valides(val)


def pour_db(raw) -> Optional[str]:
    """Ce que le front envoie -> JSON compact a stocker, ou None si rien."""
    if raw is None:
        return None
    out = ids_valides(raw)
    if not out:
        return None
    return json.dumps(out, separators=(",", ":"))
