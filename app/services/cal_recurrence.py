"""MySifa — MyCalendrier : dépliage d'une répétition en créneaux réels.

Isolé du routeur pour rester testable sans FastAPI ni session : c'est la seule
partie de la récurrence où une erreur passe inaperçue (un mensuel qui saute le
31, un « jours ouvrés » qui tombe un samedi).
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

# Règles proposées à l'utilisateur, dans l'ordre d'apparition du menu.
RECURRENCES: dict[str, str] = {
    "quotidien": "tous les jours",
    "ouvres": "tous les jours ouvrés",
    "hebdo": "toutes les semaines",
    "bihebdo": "toutes les deux semaines",
    "mensuel": "tous les mois",
}
MAX_OCCURRENCES = 260
MAX_JOURS = 760


def ajouter_mois(d: datetime, n: int) -> datetime:
    """Même quantième le mois suivant, ramené au dernier jour quand il manque.

    Un créneau du 31 janvier répété tous les mois tombe le 28 (ou 29) février,
    puis le 31 mars : on ne dérive pas d'un mois sur l'autre.
    """
    mois = d.month - 1 + n
    annee = d.year + mois // 12
    mois = mois % 12 + 1
    jour = min(d.day, calendar.monthrange(annee, mois)[1])
    return d.replace(year=annee, month=mois, day=jour)


def occurrences_serie(
    debut: datetime, fin: datetime, regle: str, jusqu_au: date
) -> list[tuple[datetime, datetime]]:
    """Les créneaux d'une série, première occurrence comprise.

    Chaque occurrence dure autant que la première : elles existent ensuite
    chacune pour elle-même et peuvent être déplacées ou annulées séparément.
    """
    duree = fin - debut
    out: list[tuple[datetime, datetime]] = []
    courant = debut
    rang = 0
    while courant.date() <= jusqu_au and len(out) < MAX_OCCURRENCES:
        out.append((courant, courant + duree))
        rang += 1
        if regle == "quotidien":
            courant = courant + timedelta(days=1)
        elif regle == "ouvres":
            courant = courant + timedelta(days=1)
            while courant.weekday() >= 5:
                courant = courant + timedelta(days=1)
        elif regle == "hebdo":
            courant = courant + timedelta(days=7)
        elif regle == "bihebdo":
            courant = courant + timedelta(days=14)
        elif regle == "mensuel":
            # Toujours calculé depuis le premier créneau : en enchaînant d'une
            # occurrence à l'autre, un 31 janvier ramené au 28 février resterait
            # ensuite bloqué au 28 de chaque mois.
            courant = ajouter_mois(debut, rang)
        else:
            break
    return out
