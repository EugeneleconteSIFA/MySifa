"""
Lire une date de livraison écrite à la main.

`planning_entries.date_livraison` est un champ TEXTE, et le reste : c'est
l'atelier qui l'écrit, pas un formulaire. On y trouve donc, en vrai :

    2026-04-07              saisi par l'application
    07/04/2026              saisi à la main, format français
    A livrer le 03/04       une phrase, sans année

Jusqu'ici seul le premier format était compris. Les deux autres tombaient dans
`_parse_iso() → None`, et `_ratio_dans_fenetre` concluait « aucune info
temporelle → dossier ouvert, tout compte » : ces dossiers étaient comptés à
100 % dans TOUTES les fenêtres d'échéance, y compris « à 7 jours ». Le besoin
à court terme était donc surévalué, silencieusement, par 11 % des dossiers.

La règle, quand la date reste illisible, ne change pas : on compte le dossier
en entier. Se tromper en commandant trop coûte du stock ; se tromper en
commandant trop peu arrête une machine. Mais ce repli doit servir aux vraies
illisibles, pas à un format qu'on savait lire.

Convention de date : française. `03/04` est le 3 avril, jamais le 4 mars.
"""
import re
from datetime import date
from typing import Optional

# ISO, éventuellement suivi d'une heure : 2026-04-07, 2026-04-07T09:00:00
_ISO = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})")

# Jour/mois[/année] n'importe où dans la chaîne. Le préfixe « A livrer le »
# n'est pas listé comme mot-clé : demain ce sera « livraison prévue » ou
# « pour le ». On cherche la date, on ignore la phrase autour.
_FR = re.compile(r"(?<!\d)(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?(?!\d)")


def _valide(a: int, m: int, j: int) -> Optional[date]:
    try:
        return date(a, m, j)
    except ValueError:
        return None


def parse_date_livraison(brut, reference: Optional[date] = None) -> Optional[date]:
    """Date de livraison lue depuis un texte libre, ou None si illisible.

    `reference` sert à deviner l'année quand elle est absente — par défaut
    aujourd'hui. On retient l'année qui place la date au plus près de la
    référence, ce qui donne le bon résultat des deux côtés du 31 décembre :
    un « 03/01 » écrit fin décembre désigne janvier prochain, pas janvier
    dernier.
    """
    s = str(brut or "").strip()
    if not s:
        return None

    m = _ISO.match(s)
    if m:
        return _valide(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    m = _FR.search(s)
    if not m:
        return None
    jour, mois = int(m.group(1)), int(m.group(2))
    an_txt = m.group(3)

    if an_txt:
        an = int(an_txt)
        if an < 100:  # « 26 » → 2026. Un dossier de production n'est pas daté de 1926.
            an += 2000
        return _valide(an, mois, jour)

    ref = reference or date.today()
    candidats = [d for d in (_valide(ref.year - 1, mois, jour),
                             _valide(ref.year, mois, jour),
                             _valide(ref.year + 1, mois, jour)) if d]
    if not candidats:
        return None  # 30/02 et autres impossibilités
    return min(candidats, key=lambda d: abs((d - ref).days))


def est_lisible(brut) -> bool:
    """Vrai si la date sera comprise par le calcul des besoins."""
    return parse_date_livraison(brut) is not None
