"""
Portée produit FSC — lecture, normalisation et couverture.

Le référentiel lui-même (`FSC_PORTEES_PRODUIT`) vit dans `config.py`, à côté de
`FSC_CLAIMS_PORTEE` et `FSC_ALLEGATIONS` : c'est un référentiel figé de la norme
FSC-STD-40-004a, et la règle du projet veut qu'on l'importe depuis `config`.
Ce module ne porte que les fonctions qui s'en servent.

Deux vocabulaires à ne jamais confondre, et toute la section FSC en dépend :

- la **portée produit** dit CE QUE le certificat couvre — P7.8 Adhesive labels,
  P2.4 Specialty paper. C'est la colonne « Product type » de la fiche de
  certificat sur la base FSC ;
- l'**allégation de sortie** dit SOUS QUELLE MENTION le fournisseur livre —
  FSC Mix, FSC Recycled, FSC Controlled Wood.

Un certificat FSC Mix parfaitement valide peut ne pas couvrir les étiquettes
adhésives. Le certificat est bon, il ne couvre simplement pas ce qu'on achète —
et c'est exactement ce que l'auditeur vient vérifier.
"""
from __future__ import annotations

from config import FSC_PORTEES_PRODUIT


def normaliser_portee(code: str) -> str:
    """« p7.8 », « P 7.8 », « P7.8. » → « P7.8 ».

    Chaîne vide si ce n'est pas un code de portée bien formé : on ne stocke pas
    ce qu'on ne sait pas lire, et un code approximatif dans une pièce d'audit
    vaut moins que pas de code du tout.
    """
    c = (code or "").strip().upper().replace(" ", "").replace("\u00a0", "").rstrip(".")
    if not c.startswith("P") or len(c) < 2:
        return ""
    corps = c[1:]
    if corps.startswith(".") or ".." in corps:
        return ""
    segments = corps.split(".")
    if not segments or not all(s.isdigit() for s in segments):
        return ""
    return "P" + corps


def libelle_portee(code: str, langue: str = "fr") -> str:
    """Libellé de la norme, ou le code seul s'il n'y figure pas.

    Un certificat peut porter un code d'une version du standard que ce
    référentiel ne connaît pas encore : mieux vaut l'afficher brut que le
    refuser et perdre l'information.
    """
    norme = normaliser_portee(code)
    entree = FSC_PORTEES_PRODUIT.get(norme)
    if not entree:
        return norme or (code or "")
    return entree.get(langue) or entree.get("fr") or norme


def catalogue_portees(langue: str = "fr") -> list[dict]:
    """Le référentiel mis à plat pour l'écran : code, libellé, profondeur.

    La profondeur sert au rendu en arbre — elle se déduit du code, il n'y a pas
    de hiérarchie à maintenir à côté.
    """
    return [
        {
            "code": code,
            "label": (entree.get(langue) or entree.get("fr") or code),
            "label_en": entree.get("en") or "",
            "niveau": code.count("."),
            "parent": code.rsplit(".", 1)[0] if "." in code else None,
        }
        for code, entree in FSC_PORTEES_PRODUIT.items()
    ]


def couvre(portee_certificat: str, besoin: str) -> bool:
    """Le certificat couvre-t-il ce besoin ?

    La hiérarchie des codes est la règle : un certificat qui porte « P2 » couvre
    P2.4.13, parce que le papier adhésif est du papier. L'inverse est faux —
    « P7.6 Enveloppes » ne couvre pas « P7.8 Étiquettes adhésives ».

    La comparaison se fait segment par segment, jamais sur la chaîne : un
    `startswith` ferait couvrir « P10 » par « P1 », deux catégories sans aucun
    rapport (pâte et autres produits manufacturés).
    """
    cert = normaliser_portee(portee_certificat)
    bes = normaliser_portee(besoin)
    if not cert or not bes:
        return False
    a = cert[1:].split(".")
    b = bes[1:].split(".")
    return len(a) <= len(b) and a == b[: len(a)]


def couverture(portees_certificat, besoins) -> dict:
    """Confronte la portée d'un certificat aux catégories achetées au fournisseur.

    Trois états, et l'écran doit pouvoir les distinguer — les confondre
    donnerait une alerte rouge à un fournisseur dont on n'a simplement pas
    encore saisi la portée :

    - `alerte` : les deux côtés sont connus et aucun besoin n'est couvert ;
    - `portee_inconnue` : le certificat n'a pas encore été contrôlé ;
    - `besoins_inconnus` : on n'a pas dit ce qu'on achète à ce fournisseur.

    Une couverture partielle (certains besoins couverts, d'autres non) ne lève
    pas l'alerte mais remonte dans `manquants` : c'est une question à poser au
    fournisseur, pas un refus de matière.
    """
    certs = []
    for x in portees_certificat or []:
        c = normaliser_portee(x)
        if c and c not in certs:
            certs.append(c)
    bes = []
    for x in besoins or []:
        b = normaliser_portee(x)
        if b and b not in bes:
            bes.append(b)

    couverts = [b for b in bes if any(couvre(c, b) for c in certs)]
    manquants = [b for b in bes if b not in couverts]
    return {
        "besoins": bes,
        "couverts": couverts,
        "manquants": manquants,
        "portee_inconnue": not certs,
        "besoins_inconnus": not bes,
        "partielle": bool(couverts) and bool(manquants),
        "alerte": bool(certs) and bool(bes) and not couverts,
    }


def nettoyer_liste(codes) -> list[str]:
    """Liste de codes normalisée, dédoublonnée, ordonnée comme la norme.

    L'ordre du référentiel plutôt que l'ordre de saisie : deux contrôles du même
    certificat donnent alors la même chaîne, et le diff d'un contrôle à l'autre
    ne montre que ce qui a vraiment changé.
    """
    vus = []
    for c in codes or []:
        n = normaliser_portee(c)
        if n and n not in vus:
            vus.append(n)
    connus = [c for c in FSC_PORTEES_PRODUIT if c in vus]
    inconnus = sorted(c for c in vus if c not in FSC_PORTEES_PRODUIT)
    return connus + inconnus
