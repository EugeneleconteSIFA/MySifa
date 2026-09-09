"""
Rapprochement automatique d'un devis et d'une entrée de planning.

POURQUOI CE MODULE EXISTE. Le planning porte plusieurs centaines de dossiers,
les devis arrivent par centaines du partage réseau, et relier les deux à la
main dossier par dossier ne se fera jamais. Sans rapprochement, la comparaison
devis/réel reste une promesse : elle marche sur les cinq dossiers qu'on aura
liés un jour de motivation.

CE QU'IL NE FAUT PAS FAIRE. Proposer beaucoup. Une proposition fausse qu'on
confirme d'un clic par réflexe empoisonne la comparaison sans laisser de trace :
l'écart affiché sera faux, et personne ne saura pourquoi. Le moteur est donc
construit pour se TAIRE en cas de doute :

- le format est éliminatoire. Sans format des deux côtés, aucune proposition —
  le nom du client seul rapproche « SCACENTRE-LECLERC » de seize dossiers ;
- il faut un score minimum ET un écart net avec le deuxième candidat. Deux
  dossiers également plausibles, c'est zéro proposition, pas un tirage au sort ;
- un devis n'est proposé qu'à UNE entrée, la meilleure. Un dossier fractionné en
  deux créneaux se rattache à la main : mieux vaut une liaison manquante qu'un
  devis recopié sur tout le planning ;
- chaque proposition porte son motif en clair. On doit pouvoir juger sans
  rouvrir le classeur, sinon l'orange devient un ordre au lieu d'une aide.

Les liaisons déjà posées ne sont jamais touchées, quelle que soit leur origine.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime

# ── Barème ────────────────────────────────────────────────────────
# Sur 100. Le format pèse le plus : c'est la seule grandeur physique que les
# deux côtés mesurent de la même façon.
POIDS_FORMAT = 40
POIDS_LAIZE = 15
POIDS_CLIENT = 25
POIDS_DATE = 10
POIDS_MOTS = 10

# En dessous, on ne propose pas. Au-dessus, il faut encore devancer le second
# candidat de MARGE_MINIMALE : un ex aequo n'est pas une réponse.
SCORE_MINIMAL = 55
MARGE_MINIMALE = 12

# Un devis est chiffré peu avant la production qu'il chiffre. Plein points
# jusqu'à un mois d'écart, puis décroissance jusqu'à un an. Au-delà, le critère
# ne dit plus rien — il n'élimine pas pour autant : un marché annuel se produit
# longtemps après son devis.
JOURS_PLEIN = 30
JOURS_NEUTRE = 365

_SUFFIXES_JURIDIQUES = {
    "sa", "sas", "sasu", "sarl", "eurl", "sci", "snc", "gie", "scop",
    "ste", "societe", "cie", "co", "ltd", "gmbh", "bv", "nv", "spa", "srl",
}

# Mots trop répandus dans les noms de fichiers pour distinguer quoi que ce soit.
_MOTS_VIDES = {
    "mm", "cm", "ex", "coul", "coul.", "couleurs", "couleur", "devis", "de",
    "la", "le", "les", "du", "des", "et", "en", "sur", "pour", "avec", "xlsx",
    "xls", "pdf", "bob", "bobine", "bobines", "etiquette", "etiquettes",
    "permanent", "blanc", "blanche", "serie", "series", "copie", "v1", "v2",
}


def _sans_accents(txt: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", txt)
        if unicodedata.category(c) != "Mn"
    )


def normaliser_client(valeur) -> str:
    """« EP CONSULT  » et « Ep-Consult SAS » donnent la même chaîne.

    Les noms viennent de deux saisies indépendantes — le planning d'un côté,
    la case client du devis de l'autre. Comparer les chaînes brutes ne
    rapprocherait quasiment rien.
    """
    txt = _sans_accents(str(valeur or "")).lower()
    txt = re.sub(r"[^a-z0-9]+", " ", txt)
    mots = [m for m in txt.split() if m and m not in _SUFFIXES_JURIDIQUES]
    return " ".join(mots)


def _mots_significatifs(valeur) -> set:
    txt = _sans_accents(str(valeur or "")).lower()
    txt = re.sub(r"[^a-z0-9]+", " ", txt)
    return {m for m in txt.split() if len(m) >= 3 and m not in _MOTS_VIDES}


def _nombre(valeur):
    try:
        n = float(valeur)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _proches(a: float, b: float, tolerance_rel: float = 0.015,
             tolerance_abs: float = 0.5) -> bool:
    """Deux cotes se valent si elles diffèrent de moins de 1,5 % ou de 0,5 mm.

    La tolérance absolue est indispensable sur les petits formats : 1,5 % de
    20 mm fait 0,3 mm, en dessous de l'arrondi que fait déjà un commercial en
    saisissant « 20 » pour 19,8.
    """
    return abs(a - b) <= max(tolerance_abs, tolerance_rel * max(a, b))


def _score_format(devis, entree) -> tuple[float, str]:
    """Compare deux couples de cotes SANS tenir compte de l'ordre.

    Un devis « 148 × 210 » et un planning « 210 × 148 » décrivent la même
    étiquette : c'est le sens de passage dans la machine qui change, pas le
    produit. Comparer largeur à largeur raterait un rapprochement sur deux.
    """
    d = sorted(x for x in (_nombre(devis.get("format_h")),
                           _nombre(devis.get("format_v"))) if x)
    e = sorted(x for x in (_nombre(entree.get("format_l")),
                           _nombre(entree.get("format_h"))) if x)
    if len(d) != 2 or len(e) != 2:
        return 0.0, ""
    if _proches(d[0], e[0]) and _proches(d[1], e[1]):
        return POIDS_FORMAT, "format %g×%g" % (e[0], e[1])
    return 0.0, ""


def _score_laize(devis, entree) -> tuple[float, str]:
    ld, le = _nombre(devis.get("laize")), _nombre(entree.get("laize"))
    if ld is None or le is None:
        return 0.0, ""
    if _proches(ld, le, 0.02, 2.0):
        return POIDS_LAIZE, "laize %g" % le
    # Une laize qui diffère franchement contredit le format : on retire, on ne
    # se contente pas de ne rien ajouter.
    return -POIDS_LAIZE, ""


def _score_client(devis, entree) -> tuple[float, str]:
    """Le client du devis est souvent vide — le modèle maison arrive prérempli
    « Mon client » et la lecture le neutralise. Son absence ne prouve donc
    rien et ne doit pas pénaliser ; sa présence, elle, pèse lourd."""
    cd, ce = normaliser_client(devis.get("client")), normaliser_client(entree.get("client"))
    if not cd or not ce:
        return 0.0, ""
    if cd == ce:
        return POIDS_CLIENT, "client %s" % (entree.get("client") or "").strip()
    court, long_ = (cd, ce) if len(cd) <= len(ce) else (ce, cd)
    if len(court) >= 4 and court in long_:
        return POIDS_CLIENT * 0.8, "client %s" % (entree.get("client") or "").strip()
    return 0.0, ""


def _jour(valeur) -> datetime | None:
    txt = str(valeur or "").strip()[:10]
    try:
        return datetime.strptime(txt, "%Y-%m-%d")
    except ValueError:
        return None


def _score_date(devis, entree) -> tuple[float, str]:
    """Un devis précède sa production. L'inverse n'est pas impossible — une date
    mal lue, un devis refait après coup — donc ce critère nuance, il n'élimine
    jamais."""
    dd = _jour(devis.get("date_devis"))
    dp = _jour(entree.get("planned_start"))
    if dd is None or dp is None:
        return 0.0, ""
    ecart = (dp - dd).days
    if ecart < 0:
        return -POIDS_DATE * 0.5, ""
    if ecart <= JOURS_PLEIN:
        return POIDS_DATE, "produit %d j après le devis" % ecart
    if ecart >= JOURS_NEUTRE:
        return 0.0, ""
    reste = (JOURS_NEUTRE - ecart) / (JOURS_NEUTRE - JOURS_PLEIN)
    return POIDS_DATE * reste, ""


def _score_mots(devis, entree) -> tuple[float, str]:
    """Les noms de fichiers portent le produit (« tabac », « RONDS », « velin »).
    Ce n'est jamais une preuve, c'est un appoint qui départage deux formats
    identiques."""
    mots_devis = _mots_significatifs(devis.get("filename"))
    mots_entree = (_mots_significatifs(entree.get("client"))
                   | _mots_significatifs(entree.get("description"))
                   | _mots_significatifs(entree.get("ref_produit")))
    if not mots_devis or not mots_entree:
        return 0.0, ""
    communs = mots_devis & mots_entree
    if not communs:
        return 0.0, ""
    part = min(1.0, len(communs) / 2.0)
    return POIDS_MOTS * part, "mots communs : " + ", ".join(sorted(communs)[:3])


def evaluer(devis: dict, entree: dict) -> dict:
    """Score d'un couple (devis, entrée de planning) et motif lisible.

    `retenu` est faux dès que le format ne concorde pas : tout le reste réuni
    ne suffit pas à affirmer qu'il s'agit du même produit.
    """
    s_format, m_format = _score_format(devis, entree)
    if s_format <= 0:
        return {"score": 0.0, "motif": "", "format_ok": False}

    total = s_format
    motifs = [m_format]
    for fn in (_score_laize, _score_client, _score_date, _score_mots):
        pts, motif = fn(devis, entree)
        total += pts
        if motif:
            motifs.append(motif)
    return {
        "score": round(max(0.0, min(100.0, total)), 1),
        "motif": " · ".join(m for m in motifs if m),
        "format_ok": True,
    }


def classer_pour_entree(devis_rows, entree: dict, limite: int = 8) -> list[dict]:
    """Les devis plausibles pour UN dossier, du plus au moins probable.

    Ce que le rapprochement automatique ne peut pas faire, l'écran le peut. Un
    même produit est fabriqué des dizaines de fois pour le même client : format,
    laize et nom coïncident sur treize dossiers, et aucun calcul ne dira lequel
    des treize porte ce devis-là. Le moteur se tait — c'est voulu — mais se
    taire ne doit pas laisser l'utilisateur devant une liste de mille devis à
    faire défiler. Ici on ne tranche pas : on remonte les candidats en tête,
    avec leur motif, et c'est un humain qui choisit.
    """
    classes = []
    for dv in devis_rows:
        note = evaluer(dv, entree)
        if note["score"] <= 0:
            continue
        classes.append({
            "devis_id": int(dv.get("id")),
            "score": note["score"],
            "motif": note["motif"],
        })
    classes.sort(key=lambda c: (-c["score"], c["devis_id"]))
    return classes[:limite]


def proposer(devis_rows, entrees_rows, deja_liees) -> list[dict]:
    """Les propositions à écrire, pour l'ensemble du planning.

    `deja_liees` : les identifiants d'entrées qui ont déjà une liaison. On n'y
    touche pas — une proposition qui écrase une décision humaine serait une
    régression silencieuse.

    Un devis ne sort qu'une fois : on classe tous les couples plausibles par
    score décroissant et on sert au plus offrant, devis et entrée étant
    consommés ensemble.
    """
    exclues = {int(x) for x in (deja_liees or [])}
    candidats = []
    for dv in devis_rows:
        for en in entrees_rows:
            eid = int(en.get("id") or 0)
            if not eid or eid in exclues:
                continue
            note = evaluer(dv, en)
            if note["score"] >= SCORE_MINIMAL:
                candidats.append({
                    "devis_id": int(dv.get("id")),
                    "planning_entry_id": eid,
                    "score": note["score"],
                    "motif": note["motif"],
                })

    # LA MARGE SE VÉRIFIE DES DEUX CÔTÉS, et c'est tout l'enjeu.
    #
    # Ne regarder que « ce dossier a-t-il un second devis plausible ? » laisse
    # passer l'ambiguïté inverse, qui est de loin la plus fréquente ici : un
    # devis qui explique aussi bien VINGT dossiers. Le même produit refabriqué
    # pour le même client donne des entrées de planning rigoureusement
    # identiques — même format, même laize, même nom. Mesuré sur les 335
    # entrées réelles, cette seule omission produisait 13 % de rattachements
    # faux, tous entre deux séries du même client : exactement les erreurs
    # qu'on ne repère pas à la relecture.
    par_entree: dict[int, list[float]] = {}
    par_devis: dict[int, list[float]] = {}
    for c in candidats:
        par_entree.setdefault(c["planning_entry_id"], []).append(c["score"])
        par_devis.setdefault(c["devis_id"], []).append(c["score"])
    for scores in list(par_entree.values()) + list(par_devis.values()):
        scores.sort(reverse=True)

    def _detache(scores: list[float], score: float) -> bool:
        second = scores[1] if len(scores) > 1 else 0.0
        return (score - second) >= MARGE_MINIMALE

    candidats.sort(key=lambda c: (-c["score"], c["planning_entry_id"]))

    retenus, devis_pris, entrees_prises = [], set(), set()
    for c in candidats:
        eid, did = c["planning_entry_id"], c["devis_id"]
        if eid in entrees_prises or did in devis_pris:
            continue
        if not _detache(par_entree.get(eid, []), c["score"]):
            # Deux devis expliquent aussi bien ce dossier.
            continue
        if not _detache(par_devis.get(did, []), c["score"]):
            # Ce devis explique aussi bien plusieurs dossiers.
            continue
        retenus.append(c)
        entrees_prises.add(eid)
        devis_pris.add(did)
    return retenus
