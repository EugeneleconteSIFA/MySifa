"""MySifa — validité d'un certificat FSC fournisseur.

Le contrôle qui compte n'est pas « ce certificat est-il valide ? » mais
« était-il valide À LA DATE DU BON DE LIVRAISON ? ».

La nuance n'est pas théorique. Un partenaire dont le certificat expire entre la
commande et la livraison casse le claim de cette livraison précise. Un contrôle
fait « aujourd'hui » ne le verra jamais : il déclarera invalides toutes les
réceptions de ce fournisseur, anciennes comme récentes, ou aucune si le
certificat a été renouvelé entre-temps. Dans les deux cas le verdict est faux.

D'où deux principes tenus par ce module :

1. La date de référence est celle du document, pas celle du jour.
2. Le verdict est FIGÉ au moment de la réception (`pf_receptions.certificat_*`).
   Un renouvellement ultérieur ne doit pas réécrire l'histoire d'une livraison
   passée, et une expiration ultérieure ne doit pas la condamner.

Absence de date d'expiration = « inconnu », jamais « valide ». Un contrôle qui
ne sait pas doit le dire ; le déguiser en succès est la seule issue vraiment
inacceptable pour une chaîne de contrôle.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

# Verdicts possibles. `inconnu` est un état à part entière, pas un repli
# silencieux vers `valide`.
VALIDE = "valide"
EXPIRE = "expire"
INCONNU = "inconnu"
NON_CERTIFIE = "non_certifie"

LIBELLES = {
    VALIDE: "Certificat valide à la date du BL",
    EXPIRE: "Certificat EXPIRÉ à la date du BL",
    INCONNU: "Date d'expiration inconnue — à vérifier",
    NON_CERTIFIE: "Fournisseur non certifié FSC",
}


def _parse_date(valeur) -> Optional[date]:
    """Accepte 'AAAA-MM-JJ' ou un ISO datetime. Renvoie None si illisible."""
    if valeur is None:
        return None
    if isinstance(valeur, datetime):
        return valeur.date()
    if isinstance(valeur, date):
        return valeur
    s = str(valeur).strip()
    if not s:
        return None
    # Un horodatage complet est toléré : on ne garde que la partie date.
    s = s.replace("T", " ").split(" ")[0]
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def evaluer_certificat(
    fournisseur: dict,
    date_document,
) -> dict:
    """Verdict de validité d'un certificat à la date d'un document.

    `fournisseur` : ligne de fournisseurs_fsc (has_fsc, licence, certificat,
                    fsc_date_expiration).
    `date_document` : date du BL / de la facture. C'est ELLE qui fait foi.

    Renvoie {statut, libelle, expiration, jours_restants, bloquant}.
    `bloquant` distingue ce qui interdit un claim (certificat expiré, fournisseur
    non certifié) de ce qui appelle une vérification humaine (date inconnue).
    """
    f = fournisseur or {}
    has_fsc = int(f.get("has_fsc") if f.get("has_fsc") is not None else 1)

    if not has_fsc:
        return {
            "statut": NON_CERTIFIE,
            "libelle": LIBELLES[NON_CERTIFIE],
            "expiration": None,
            "jours_restants": None,
            "bloquant": True,
        }

    expiration = _parse_date(f.get("fsc_date_expiration"))
    reference = _parse_date(date_document) or date.today()

    if expiration is None:
        return {
            "statut": INCONNU,
            "libelle": LIBELLES[INCONNU],
            "expiration": None,
            "jours_restants": None,
            # Non bloquant : on n'empêche pas une réception faute d'une donnée
            # administrative absente. Mais l'écart est enregistré et remonte,
            # ce qui est le seul moyen qu'il finisse par être comblé.
            "bloquant": False,
        }

    jours = (expiration - reference).days
    if jours < 0:
        return {
            "statut": EXPIRE,
            "libelle": LIBELLES[EXPIRE],
            "expiration": expiration.isoformat(),
            "jours_restants": jours,
            "bloquant": True,
        }

    return {
        "statut": VALIDE,
        "libelle": LIBELLES[VALIDE],
        "expiration": expiration.isoformat(),
        "jours_restants": jours,
        "bloquant": False,
    }


def certificats_a_renouveler(conn, jours: int = 60) -> list[dict]:
    """Certificats expirés ou expirant dans les `jours` prochains.

    Sert l'alerte préventive : un certificat qui expire dans trois semaines est
    une livraison qui va casser un claim, pas encore un incident. Le voir avant
    coûte un mail au fournisseur ; le voir après coûte une non-conformité.
    """
    aujourdhui = date.today()
    lignes = conn.execute(
        """SELECT id, nom, licence, certificat, fsc_date_expiration
             FROM fournisseurs_fsc
            WHERE COALESCE(has_fsc,1) = 1
              AND COALESCE(actif,1) = 1
              AND TRIM(COALESCE(fsc_date_expiration,'')) <> ''
            ORDER BY fsc_date_expiration ASC"""
    ).fetchall()
    out = []
    for r in lignes:
        exp = _parse_date(r["fsc_date_expiration"])
        if exp is None:
            continue
        restants = (exp - aujourdhui).days
        if restants <= jours:
            out.append(
                {
                    "id": r["id"],
                    "nom": r["nom"],
                    "licence": r["licence"],
                    "certificat": r["certificat"],
                    "expiration": exp.isoformat(),
                    "jours_restants": restants,
                    "expire": restants < 0,
                }
            )
    return out


def fournisseurs_sans_date(conn) -> list[dict]:
    """Fournisseurs certifiés dont la date d'expiration manque.

    Ce sont les angles morts du contrôle : pour eux, aucune réception ne pourra
    jamais être déclarée conforme autrement que par « inconnu ».
    """
    lignes = conn.execute(
        """SELECT id, nom, licence, certificat
             FROM fournisseurs_fsc
            WHERE COALESCE(has_fsc,1) = 1
              AND COALESCE(actif,1) = 1
              AND TRIM(COALESCE(fsc_date_expiration,'')) = ''
            ORDER BY nom COLLATE NOCASE ASC"""
    ).fetchall()
    return [dict(r) for r in lignes]
