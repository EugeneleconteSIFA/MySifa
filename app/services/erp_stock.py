"""Le stock de RVGI, lu dans le miroir.

Pourquoi ce module existe
-------------------------
RVGI ne stocke pas la quantité en stock dans la fiche article. `fic_art.stk`
et `mat_mat.stk` ne prennent que les valeurs 1 et 2 sur la totalité des
articles : c'est un indicateur de suivi, pas une quantité. Les lire comme un
stock ferait lire « 2 » là où il y a deux millions d'étiquettes.

La quantité vit dans l'historique des mouvements : chaque ligne de `stk_hist`
(produits finis) et de `stm_hist` (matières) porte `qte1`, la quantité
mouvementée, et **`qte2`, le stock résultant**. Renseigné sur la totalité des
25 592 mouvements du miroir. Le stock d'un article, c'est donc le `qte2` de
son dernier mouvement — pas une somme, qui se tromperait au premier inventaire.

    890/0079  03/08 10:32  OF RELIQUAT 9932056   +7 014 300  ->  1 014 300
    890/0079  03/08 10:33  MISE A 0              -1 014 300  ->          0
    890/0079  03/08 10:33  RESTE A REPIQUER      +6 500 000  ->  6 500 000
    890/0079  07/08 11:25  Livraison du 07/08    -1 500 000  ->  5 000 000

Le stock négatif n'est pas une anomalie de lecture : RVGI l'autorise, et
7 866 mouvements y passent — une livraison saisie avant l'entrée d'OF. On le
rend tel quel.
"""

from typing import Any, Dict

from app.services import erp_mirror as miroir

# Deux périmètres, deux couples de tables. Le reste du code est commun : c'est
# la même mécanique, RVGI l'applique deux fois.
PERIMETRES = {
    "pf": {
        "label": "Produits finis",
        "mouvements": "stk_hist",
        "fiches": "fic_art",
    },
    "matiere": {
        "label": "Matières",
        "mouvements": "stm_hist",
        "fiches": "mat_mat",
    },
}


def _reference(code1: Any, code2: Any) -> str:
    """« 890 » + « 79 » → « 890/0079 ».

    Même règle que `_erp_reference()` de la réconciliation, qui la tient de
    l'export Excel : `code2` est complété à quatre chiffres. Les deux doivent
    produire la même clé, sinon un instantané pris depuis le miroir ne serait
    pas comparable à un instantané pris depuis un fichier.
    """
    c1 = str(code1 or "").strip()
    if not c1:
        return ""
    c2 = str(code2 or "").strip()
    if c2.isdigit() and len(c2) < 4:
        c2 = c2.zfill(4)
    return "%s/%s" % (c1, c2) if c2 else c1


def index_stock(perimetre: str = "pf") -> Dict[str, Dict[str, Any]]:
    """{référence: {stock_erp, designation, mvt_libelle, mvt_date, mvt_qte}}.

    Renvoie EXACTEMENT la forme que la réconciliation attend d'un export
    Excel : c'est ce qui permet de changer la source sans toucher au reste —
    l'écran, le classement des écarts et l'historique ne bougent pas.
    """
    p = PERIMETRES.get(perimetre)
    if not p:
        raise ValueError("Périmètre inconnu : %r" % (perimetre,))

    out: Dict[str, Dict[str, Any]] = {}
    with miroir.get_erp_db() as conn:
        presentes = miroir.tables_presentes(conn)
        if p["mouvements"] not in presentes:
            raise FileNotFoundError(
                "La table « %s » n'est pas dans le miroir : lancer la synchro RVGI."
                % p["mouvements"]
            )

        # Le dernier mouvement de chaque article. On départage deux mouvements
        # de même horodatage par l'id : RVGI écrit parfois trois lignes dans la
        # même seconde (mise à zéro puis ré-entrée), et prendre la mauvaise
        # inverserait le stock.
        sql = """
            SELECT h.code1, h.code2, h.qte2, h.qte1, h.amjh, h.des1, h.mvt
              FROM "%s" h
              JOIN (SELECT code1, code2, MAX(amjh || '#' || id) AS mx
                      FROM "%s" GROUP BY code1, code2) d
                ON d.code1 IS h.code1 AND d.code2 IS h.code2
               AND d.mx = h.amjh || '#' || h.id
        """ % (p["mouvements"], p["mouvements"])
        for r in conn.execute(sql):
            ref = _reference(r["code1"], r["code2"])
            if not ref:
                continue
            out[ref] = {
                "stock_erp": float(r["qte2"] or 0),
                "designation": None,
                "mvt_libelle": (r["des1"] or None),
                "mvt_date": (r["amjh"] or None),
                "mvt_qte": (float(r["qte1"]) if r["qte1"] is not None else None),
            }

        # La désignation vient de la fiche, pas du mouvement : le libellé d'un
        # mouvement dit « Livraison du 24/08/2026 », ce qui n'identifie rien.
        if p["fiches"] in presentes:
            for r in conn.execute(
                'SELECT code1, code2, libc1 FROM "%s" WHERE corbeille = 0' % p["fiches"]
            ):
                ref = _reference(r["code1"], r["code2"])
                if ref in out and not out[ref]["designation"]:
                    out[ref]["designation"] = (r["libc1"] or None)

    return out


def resume(perimetre: str = "pf") -> Dict[str, Any]:
    """De quoi annoncer ce que la comparaison va porter, avant de la lancer."""
    idx = index_stock(perimetre)
    non_nuls = [v["stock_erp"] for v in idx.values() if v["stock_erp"]]
    negatifs = [q for q in non_nuls if q < 0]
    dates = [v["mvt_date"] for v in idx.values() if v["mvt_date"]]
    return {
        "perimetre": perimetre,
        "label": PERIMETRES[perimetre]["label"],
        "references": len(idx),
        "avec_stock": len(non_nuls),
        "negatifs": len(negatifs),
        "dernier_mouvement": max(dates) if dates else None,
    }
