"""
Combien d'étiquettes côte à côte — et pourquoi la réponse était fausse.

Le nombre de fronts est le nombre d'étiquettes en travers de la bobine. Il
n'est pas libre : la laize du module multipliée par le nombre de fronts doit
tenir dans la laize de la bobine, et la remplir à peu près.

    nb_fronts ≈ laize_bobine ÷ laize_module

Cette identité ne demande aucune source extérieure. Elle se vérifie sur la
fiche seule, et rend une classe entière d'erreurs de saisie détectable sans
que personne ait à ouvrir un document.

Ce qui a été constaté le 7 août 2026
────────────────────────────────────
Sur la base de production, **878 fiches sur 909 portent `mod_nb_front = 1`**,
alors que la géométrie en annonce 4, 9, 17 sur les mêmes fiches. `mod_nb_front`
n'est pas une valeur : c'est un champ que personne ne remplit.

Le vrai nombre de fronts vit dans **`outil1_nb_front`** — le nombre de poses de
l'outil de découpe. Importé par le pont Access, il n'était utilisé nulle part.
Confrontation faite : **868 fiches sur 909 le confirment par la géométrie**
(fiche 1 : 9 poses déclarées, 9,6 attendues ; fiche 4 : 17 pour 17,6 ; fiche 15 :
15 pour 15,6).

La conséquence était directe. Quand l'OF ne porte pas de métrage — 585 OF sur
745 — le besoin se calcule par la fiche :

    métrage = qte_étiquettes ÷ nb_fronts × mod_longueur ÷ 1000

Le nombre de fronts est au DÉNOMINATEUR. Le prendre à 1 quand il vaut 18
multiplie le besoin en frontal par 18. Un dossier est ainsi ressorti à
55 823 km de frontal, dix fois le total d'un mois entier.

Ce module fait deux choses distinctes, qu'il ne faut pas confondre :

1. `nb_fronts()` — résout la valeur à utiliser, en disant d'où elle vient.
   L'outil d'abord, le module ensuite, la géométrie en dernier recours.
2. `controler()` — vérifie que la valeur retenue boucle, et nomme l'écart.
   Il ne corrige rien : une fiche fausse se répare dans Access, à la source.
   Compenser en silence à chaque lecture reviendrait à cacher le problème
   pendant que les commandes continuent de partir de travers.
"""
import math
from typing import Optional

# Marge d'acceptation autour de la valeur géométrique. Une bobine n'est jamais
# remplie au millimètre : coupe, échenillage latéral et marges de conduite en
# mangent quelques pour cent. 20 %, ou un front d'écart, absorbent cela sans
# laisser passer un facteur 2.
_TOLERANCE_REL = 0.20


def _f(v) -> Optional[float]:
    try:
        x = float(str(v).replace(",", "."))
        return x if x > 0 else None
    except (TypeError, ValueError):
        return None


def laize_utile(ft: dict, laize_of: Optional[float] = None) -> Optional[float]:
    """Laize de la bobine réellement engagée.

    Celle de l'OF prime : c'est la bobine qu'on montera sur la machine pour CE
    dossier. La fiche ne donne qu'un cas nominal. `eti_laize` est délibérément
    exclue — c'est la largeur de l'étiquette, pas de la bobine, et les
    confondre donne un nombre de fronts de 1.
    """
    return (_f(laize_of)
            or _f(ft.get("laize_optimale"))
            or _f(ft.get("laize")))


def nb_fronts_geometrique(ft: dict, laize_of: Optional[float] = None) -> Optional[int]:
    """Combien de modules tiennent en travers de la bobine, ou None."""
    mod_laize = _f(ft.get("mod_laize"))
    laize = laize_utile(ft, laize_of)
    if not mod_laize or not laize:
        return None
    return max(0, math.floor(laize / mod_laize + 1e-9))


def nb_fronts(ft: dict, laize_of: Optional[float] = None) -> dict:
    """Nombre de fronts à utiliser dans le calcul, et sa provenance.

    Retourne { valeur, source, champ } — `source` ∈ 'outil' | 'module' |
    'geometrie' | None.

    L'ordre n'est pas arbitraire : `outil1_nb_front` est confirmé par la
    géométrie sur 868 fiches sur 909, `mod_nb_front` vaut 1 sur 878. Le
    second ne sert donc que là où le premier manque, et la géométrie ne prend
    la main que si les deux sont absents — auquel cas on préfère une valeur
    déduite d'une mesure à une valeur qu'on sait fausse.
    """
    outil = _f(ft.get("outil1_nb_front"))
    if outil:
        return {"valeur": outil, "source": "outil",
                "champ": "fiches_techniques.outil1_nb_front"}
    mod = _f(ft.get("mod_nb_front"))
    if mod and mod > 1:
        return {"valeur": mod, "source": "module",
                "champ": "fiches_techniques.mod_nb_front"}
    geo = nb_fronts_geometrique(ft, laize_of)
    if geo and geo >= 1:
        return {"valeur": float(geo), "source": "geometrie",
                "champ": "laize ÷ mod_laize"}
    # Reste `mod_nb_front = 1`, qui peut être vrai sur une étiquette très large.
    if mod:
        return {"valeur": mod, "source": "module",
                "champ": "fiches_techniques.mod_nb_front"}
    return {"valeur": None, "source": None, "champ": None}


def controler(ft: dict, laize_of: Optional[float] = None) -> dict:
    """Vérifie que la fiche boucle géométriquement.

    Retourne { verdict, retenu, source, nb_front_geometrique, laize_utile,
    mod_laize, facteur_erreur, message }.

    `verdict` ∈ 'coherent' | 'incoherent' | 'indeterminable'.

    `facteur_erreur` est le rapport entre le besoin qui serait calculé avec la
    valeur retenue et celui qu'implique la géométrie. C'est le seul chiffre qui
    dit si l'écart est vénielle ou s'il fausse une commande.
    """
    res = nb_fronts(ft, laize_of)
    retenu, source = res["valeur"], res["source"]
    mod_laize = _f(ft.get("mod_laize"))
    laize = laize_utile(ft, laize_of)
    geo = nb_fronts_geometrique(ft, laize_of)

    base = {
        "retenu": retenu,
        "source": source,
        "nb_front_declare_module": _f(ft.get("mod_nb_front")),
        "nb_front_outil": _f(ft.get("outil1_nb_front")),
        "nb_front_geometrique": geo,
        "laize_utile": laize,
        "mod_laize": mod_laize,
        "facteur_erreur": None,
    }

    if geo is None:
        return {**base, "verdict": "indeterminable",
                "message": "Laize du module ou de la bobine absente : la "
                           "cohérence géométrique ne peut pas être vérifiée."}
    if geo < 1:
        return {**base, "verdict": "incoherent",
                "message": f"Le module ({mod_laize:g} mm) est plus large que la "
                           f"bobine ({laize:g} mm) : la fiche ne peut pas être juste."}
    if not retenu:
        return {**base, "verdict": "incoherent",
                "message": f"Aucun nombre de fronts renseigné. La géométrie en "
                           f"implique {geo} ({laize:g} mm ÷ {mod_laize:g} mm)."}

    if abs(retenu - geo) <= max(1.0, geo * _TOLERANCE_REL):
        return {**base, "verdict": "coherent",
                "message": f"{retenu:g} front(s) retenu(s), {geo} attendu(s) par "
                           f"la géométrie — cohérent."}

    facteur = geo / retenu
    base["facteur_erreur"] = round(facteur, 2)
    sens = "surestimé" if facteur > 1 else "sous-estimé"
    return {**base, "verdict": "incoherent",
            "message": (f"{retenu:g} front(s) retenu(s) mais {geo} attendu(s) "
                        f"({laize:g} mm ÷ {mod_laize:g} mm). Le besoin en frontal "
                        f"calculé depuis cette fiche est {sens} d'un facteur "
                        f"{facteur:.1f} tant qu'elle n'est pas corrigée.")}


def alerte_courte(res: dict) -> Optional[str]:
    """Une ligne pour l'interface, ou None si la fiche est saine."""
    if res.get("verdict") != "incoherent":
        return None
    r, g = res.get("retenu"), res.get("nb_front_geometrique")
    f = res.get("facteur_erreur")
    if r and g:
        txt = f"Fiche à vérifier : {r:g} front(s), {g} attendu(s) par la laize"
        return txt + (f" — besoin ×{f:g}." if f and f > 1 else ".")
    return "Fiche à vérifier : nombre de fronts incohérent avec la laize."
