"""
Le palier de quantité d'un devis, et le recalage des temps devisés dessus.

Pourquoi ce module existe. Un devis SIFA chiffre couramment plusieurs
quantités — « 500 000 ex à 12,40 €/mille ; 1 000 000 ex à 9,80 €/mille ». Le
classeur, lui, ne calcule les temps et les métrages que pour UNE de ces
quantités, pas forcément celle du dossier lancé. Sur la reprise de septembre
2026, 119 devis sur 624 portaient cette réserve, et dans 46 % des cas les deux
quantités étaient dans un rapport de un à deux : comparer la production réelle
aux temps de l'autre palier affichait un écart de 100 % sur un dossier
parfaitement conforme.

Ce que le recalage fait, et ce qu'il ne fait pas :

- le métrage de production vaut la quantité multipliée par le pas développé et
  divisée par le nombre de fronts : il est STRICTEMENT proportionnel à la
  quantité, et se proratise donc sans approximation ;
- le temps de production n'est que ce métrage divisé par la vitesse, qui ne
  dépend pas de la série : il suit la même règle ;
- le calage ne se proratise PAS. Monter un outil et caler les couleurs coûte
  le même temps pour 100 000 ou pour 1 000 000 d'étiquettes. C'est même toute
  la raison d'être des paliers : le calage s'amortit sur la série ;
- la gâche reste attachée au calage, donc inchangée elle aussi.

Le prix au mille, lui, ne se proratise jamais : c'est un prix négocié par
palier. On rend celui du palier le plus proche, et on dit lequel.
"""

from __future__ import annotations

import re

# En deçà, recaler ne change rien de lisible et l'écran n'a rien à proposer :
# une réserve qui se déclenche pour 2 % de mieux finit par être ignorée.
ECART_MINI_PROPOSITION = 0.10

_RANG_RE = re.compile(r"palier\s+(\d+)", re.I)


def paliers_du_devis(conn, devis_id: int) -> list[dict]:
    """Les quantités proposées par le devis, avec leur prix au mille.

    Elles sont stockées une par une dans `devis_indicateurs`, sous la forme
    « Quantité proposée (palier 2) ». On les rassemble par rang plutôt que de
    se fier à l'ordre d'insertion : un devis relu remplace ses indicateurs, et
    rien ne garantit que les ids restent croissants.
    """
    # Parentheses obligatoires autour du OR : sans elles, « devis_id=? AND a
    # OR b » se lit « (devis_id=? AND a) OR b » et ramene les indicateurs de
    # TOUS les devis des que le second motif correspond.
    lignes = conn.execute(
        "SELECT libelle, valeur_nombre FROM devis_indicateurs "
        "WHERE devis_id=? AND (libelle LIKE 'Quantité proposée (palier%' "
        "                   OR libelle LIKE 'Prix au mille (palier%')",
        (devis_id,),
    ).fetchall()

    par_rang: dict[int, dict] = {}
    for r in lignes:
        libelle = str(r["libelle"] or "")
        m = _RANG_RE.search(libelle)
        if not m:
            continue
        rang = int(m.group(1))
        entree = par_rang.setdefault(rang, {"rang": rang, "quantite": 0.0,
                                            "prix_mille": None})
        valeur = r["valeur_nombre"]
        if valeur is None:
            continue
        if libelle.startswith("Quantité"):
            entree["quantite"] = float(valeur)
        else:
            entree["prix_mille"] = float(valeur)

    return [p for _, p in sorted(par_rang.items()) if p["quantite"] > 0]


def palier_le_plus_proche(paliers: list[dict], quantite: float):
    """Le palier dont la quantité est la plus proche, en écart RELATIF.

    En écart absolu, 700 000 serait aussi loin de 500 000 que de 900 000 ;
    en relatif, il est plus proche de 900 000 — ce qui correspond à la façon
    dont un prix au mille évolue.
    """
    q = float(quantite or 0)
    if not paliers or q <= 0:
        return None
    return min(paliers, key=lambda p: abs(q - p["quantite"]) / max(p["quantite"], 1))


def recaler(devis_row, quantite_cible: float) -> dict:
    """Les valeurs devisées ramenées à `quantite_cible`.

    Rend un dict compatible avec une ligne de `devis` : les consommateurs
    (comparaison, écran) le lisent comme ils liraient la ligne d'origine.
    Quand le recalage est impossible — quantité devisée inconnue ou nulle —
    on rend les valeurs telles quelles plutôt qu'un zéro : une comparaison
    approximative reste lisible, une comparaison à zéro ne l'est pas.
    """
    base = dict(devis_row)
    qte_devis = float(base.get("qte_etiquettes") or 0)
    cible = float(quantite_cible or 0)
    if qte_devis <= 0 or cible <= 0:
        base["recale"] = False
        base["ratio_recalage"] = 1.0
        return base

    ratio = cible / qte_devis
    base["qte_etiquettes"] = cible
    for champ in ("temps_production_mn", "metrage_production_ml"):
        valeur = base.get(champ)
        if valeur is not None:
            base[champ] = round(float(valeur) * ratio, 2)
    base["recale"] = abs(ratio - 1.0) > 1e-9
    base["ratio_recalage"] = ratio
    base["qte_devisee_origine"] = qte_devis
    return base


def proposition(devis_row, paliers: list[dict], quantite_of: float):
    """Faut-il proposer un recalage, et sur quoi ?

    `None` quand il n'y a rien à dire : pas de quantité d'OF, ou les temps du
    classeur portent déjà sur la bonne série. Le seuil évite de proposer un
    recalage de quelques pour cent, que personne ne confirmerait.
    """
    qte_of = float(quantite_of or 0)
    qte_devis = float(dict(devis_row).get("qte_etiquettes") or 0)
    if qte_of <= 0 or qte_devis <= 0:
        return None

    ecart = abs(qte_of - qte_devis) / qte_devis
    if ecart < ECART_MINI_PROPOSITION:
        return None

    proche = palier_le_plus_proche(paliers, qte_of)
    return {
        "qte_of": qte_of,
        "qte_devisee": qte_devis,
        "ecart_pct": round((qte_of - qte_devis) / qte_devis * 100, 1),
        "palier_rang": (proche or {}).get("rang"),
        "palier_quantite": (proche or {}).get("quantite"),
        "prix_mille": (proche or {}).get("prix_mille"),
        # Un palier qui tombe pile veut dire que le classeur a chiffré cette
        # série : le prix au mille s'applique tel quel. Sinon on proratise les
        # temps sur la quantité exacte, et le prix reste indicatif.
        "palier_exact": bool(proche and abs(qte_of - proche["quantite"])
                             / max(proche["quantite"], 1) < 0.005),
        "paliers": paliers,
    }
