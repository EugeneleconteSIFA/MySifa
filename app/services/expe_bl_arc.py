"""MyExpé — le BL d'un départ est-il relié à sa commande (ARC) dans RVGI ?

Le suivi des départs affiche un badge à côté du n° de BL, à trois états :

- **lié** : le BL a été rattaché depuis le sélecteur RVGI (`rvgi_etat` du
  départ vaut `lie` ou `partiel`) — quelqu'un a choisi la pièce dans le miroir ;
- **lié auto** : rien n'a été rattaché, mais le BL et l'ARC saisis à la main
  se recoupent dans le miroir — chaque BL porte au moins une ligne dont la
  commande (`liv_ligne.numcde`) est l'une des commandes de l'ARC ;
- **non lié** : tout le reste, avec la raison (pas de BL, BL inconnu de RVGI,
  BL d'une autre commande…). La raison est ce qui permet d'agir.

Lecture seule des deux côtés : rien n'est écrit, ni dans le miroir ni dans
`rvgi_rattachements`. Un « lié auto » reste une observation, pas un
rattachement — le confirmer reste un geste humain.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

LIE = "lie"
LIE_AUTO = "lie_auto"
NON_LIE = "non_lie"

# Un numéro de pièce RVGI fait 7 chiffres aujourd'hui ; 5 au moins écarte les
# nombres parasites d'un champ libre (« 9932344 (marché 751) »).
_LONGUEUR_MIN = 5


def numeros(texte: Any) -> List[str]:
    """Numéros de pièce lus dans un champ texte.

    Comprend la vitrine compacte écrite par le rattachement
    (« 9932610+611+612 » = 9932610, 9932611, 9932612) : un morceau court
    collé par « + » remplace la fin du numéro précédent. Ailleurs, seuls les
    nombres d'au moins cinq chiffres comptent.
    """
    out: List[str] = []
    for bloc in re.split(r"[\s,;/]+", str(texte or "")):
        precedent = None
        for morceau in bloc.split("+"):
            n = re.sub(r"\D", "", morceau)
            if not n:
                precedent = None
                continue
            if len(n) >= _LONGUEUR_MIN:
                precedent = n
            elif precedent and len(n) < len(precedent) and morceau.strip().isdigit():
                n = precedent[: len(precedent) - len(n)] + n
            else:
                continue
            if n not in out:
                out.append(n)
    return out


def _commandes_des_bl(bls: Iterable[str]) -> Optional[Dict[str, set]]:
    """{BL: {commandes}} d'après le miroir, ou None s'il est indisponible.

    `numero` est un entier indexé : on compare en entier, jamais par CAST en
    texte, qui fait perdre l'index (cf. préremplissage par l'ARC)."""
    from app.services import erp_mirror as miroir

    uniques = sorted({int(b) for b in bls})
    trouves: Dict[str, set] = {}
    if not uniques:
        return trouves
    try:
        with miroir.get_erp_db() as c:
            if "liv_ligne" not in miroir.tables_presentes(c):
                return None
            for debut in range(0, len(uniques), 400):
                lot = uniques[debut:debut + 400]
                for r in c.execute(
                    "SELECT numero, numcde FROM liv_ligne WHERE corbeille=0 AND numero IN (%s)"
                    % ",".join("?" * len(lot)),
                    lot,
                ):
                    cde = re.sub(r"\D", "", str(r["numcde"] if r["numcde"] is not None else "").split(".")[0])
                    trouves.setdefault(str(int(r["numero"])), set())
                    if cde:
                        trouves[str(int(r["numero"]))].add(cde)
    except FileNotFoundError:
        return None
    return trouves


def evaluer(depart: dict, miroir_bl: Optional[Dict[str, set]]) -> Dict[str, str]:
    """État et raison pour un départ, `miroir_bl` venant de `_commandes_des_bl`."""
    if (depart.get("rvgi_etat") or "") in ("lie", "partiel"):
        return {"etat": LIE, "detail": "BL rattaché depuis RVGI"}
    bls = numeros(depart.get("no_bl"))
    arcs = numeros(depart.get("arc"))
    if not bls:
        return {"etat": NON_LIE, "detail": "Pas de n° de BL"}
    if not arcs:
        return {"etat": NON_LIE, "detail": "Pas d'ARC"}
    if miroir_bl is None:
        return {"etat": NON_LIE, "detail": "Miroir RVGI indisponible"}
    inconnus = [b for b in bls if b not in miroir_bl]
    if inconnus:
        return {
            "etat": NON_LIE,
            "detail": "BL %s inconnu de RVGI (miroir en retard ?)" % ", ".join(inconnus),
        }
    autres = {b: miroir_bl[b] for b in bls if not (miroir_bl[b] & set(arcs))}
    if autres:
        b, cdes = next(iter(autres.items()))
        return {
            "etat": NON_LIE,
            "detail": "BL %s livre la commande %s dans RVGI, pas l'ARC saisi"
            % (b, ", ".join(sorted(cdes)) or "—"),
        }
    return {"etat": LIE_AUTO, "detail": "BL et ARC concordants dans RVGI"}


def annoter(departs: List[dict]) -> List[dict]:
    """Pose `bl_arc` ({etat, detail}) sur chaque départ, en une lecture du miroir."""
    a_lire: List[str] = []
    for d in departs:
        if (d.get("rvgi_etat") or "") in ("lie", "partiel"):
            continue
        if numeros(d.get("arc")):
            a_lire += numeros(d.get("no_bl"))
    miroir_bl = _commandes_des_bl(a_lire) if a_lire else {}
    for d in departs:
        d["bl_arc"] = evaluer(d, miroir_bl)
    return departs
