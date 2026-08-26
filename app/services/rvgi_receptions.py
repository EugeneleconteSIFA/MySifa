"""Les réceptions de RVGI, pour préremplir celles de MyStock.

Ce que RVGI appelle une réception
---------------------------------
`lif_ligne` : une ligne par article reçu, rattachée à la ligne de commande
fournisseur par (`numero`, `ligne`). Elle ne porte ni le fournisseur ni
l'article — les deux viennent de la commande :

    lif_ligne     numero (n° de commande fournisseur), ligne, qte, amjl, ref
    cdf_ligne     code1/code2 (l'article), des1, qte commandée, pun
    cdf_entete    numfou, rs (le fournisseur), amjc

Mesuré sur les 4 242 lignes de réception depuis 2025 :

    ligne de commande retrouvée   100 %
    article (code1/code2)         100 %
    fournisseur                   100 %
    date de livraison             100 %
    quantité                      100 %
    `ref` (= n° de BL fournisseur, « BL137434 »)   100 %
    fiche matière dans `mat_mat`   62 %
    laize (`mat_mat.m1_lai`)       32 %
    `lot`                           0 %   — RVGI ne s'en sert pas

Les 38 % sans fiche matière ne sont pas un trou : ce sont des achats de
produits FINIS. GRAND OUEST ETIQUETTES livre des étiquettes 14 × 14 mm, pas
du support adhésif. Une réception RVGI peut donc alimenter l'un ou l'autre
des deux écrans de MyStock, et c'est l'article qui le dit.

Ce qu'on peut préremplir, et ce qu'on ne peut pas
------------------------------------------------
Le fournisseur, le n° de BL, la matière, la laize et la date : oui.

Les bobines : non, et ce n'est pas un manque. La réception de MyStock se
saisit au code-barres, une bobine à la fois — c'est ce qui donne la traçabilité
FSC. RVGI ne connaît qu'une quantité globale. On la rend donc comme un
CONTRÔLE (« RVGI attend 250 000, vous avez scanné 12 bobines ») plutôt que
comme un préremplissage qui ferait perdre le comptage réel.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any, Dict, List, Optional

from app.services import erp_mirror as miroir

# Au-delà, la liste ne se lit plus et la recherche coûte cher pour rien.
LIMITE = 30

# `FR` n'est pas une famille d'articles : c'est ce que RVGI facture en plus de
# la marchandise — frais de cliché, frais d'outils, frais de port. 291 des
# 3 017 lignes de réception depuis 2025. Ces lignes n'entrent dans aucun stock,
# et les compter comme de la marchandise ferait proposer une réception de
# « 4 frais de cliché ».
CODE1_FRAIS = "FR"

# `lpos = 2` marque une ligne soldée dans RVGI. On garde tout le reste : une
# réception partielle est justement celle qu'on va compléter.
_SQL = """
    SELECT l.id            AS id,
           l.numero        AS cde,
           l.ligne         AS ligne,
           l.qte           AS qte,
           l.amjl          AS date_reception,
           l.ref           AS bl,
           l.depot         AS depot,
           l.lpos          AS position,
           c.code1         AS code1,
           c.code2         AS code2,
           c.des1          AS designation,
           c.qte           AS qte_commandee,
           c.pun           AS prix_unitaire,
           e.numfou        AS numfou,
           e.rs            AS fournisseur,
           e.amjc          AS date_commande
      FROM lif_ligne l
      LEFT JOIN cdf_ligne  c ON c.numero = l.numero AND c.ligne = l.ligne AND c.corbeille = 0
      LEFT JOIN cdf_entete e ON e.numero = l.numero AND e.corbeille = 0
     WHERE l.corbeille = 0
"""


def _txt(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _article(code1: Any, code2: Any) -> Optional[str]:
    a, b = _txt(code1), _txt(code2)
    if not a and not b:
        return None
    return ("%s/%s" % (a, b)) if b else a


def _fiches_matiere(conn, couples) -> Dict[str, Dict[str, Any]]:
    """La fiche `mat_mat` de chaque article reçu : désignation, laize, grammage.

    `m1_lai` … `m1_lai_30` : RVGI stocke jusqu'à trente laizes par matière.
    On rend la première renseignée — c'est la laize principale, et proposer
    les trente dans un formulaire de réception n'aiderait personne.
    """
    cles = [(a, b) for a, b in {(str(x or "").strip(), str(y or "").strip())
                                for x, y in couples} if a]
    if not cles or "mat_mat" not in miroir.tables_presentes(conn):
        return {}
    lais = ["m1_lai"] + ["m1_lai_%d" % i for i in range(2, 31)]
    dispo = {r[1] for r in conn.execute('PRAGMA table_info("mat_mat")')}
    lais = [c for c in lais if c in dispo]
    out: Dict[str, Dict[str, Any]] = {}
    for debut in range(0, len(cles), 400):
        lot = cles[debut:debut + 400]
        sql = ('SELECT code1, code2, libc1, pds, ref, numfou, %s FROM mat_mat '
               'WHERE corbeille = 0 AND (%s)'
               % (", ".join(lais) or "code1",
                  " OR ".join(["(code1 = ? AND code2 = ?)"] * len(lot))))
        for r in conn.execute(sql, [v for paire in lot for v in paire]):
            laize = next((r[c] for c in lais if r[c]), None)
            out[_article(r["code1"], r["code2"])] = {
                "matiere_rvgi": _txt(r["libc1"]),
                "laize_mm": float(laize) if laize else None,
                "grammage": (float(r["pds"]) if r["pds"] else None),
                "ref_fournisseur": _txt(r["ref"]),
            }
    return out


def _resoudre_mysifa(conn_mysifa: sqlite3.Connection,
                     lignes: List[Dict[str, Any]]) -> None:
    """Retrouve, pour chaque ligne, la matière ou le produit fini de MySifa.

    La clé est la référence article — « 890/0079 » des deux côtés. Quand elle
    ne répond pas, on le DIT sur la ligne au lieu de la préremplir à moitié :
    une réception rattachée à la mauvaise matière fausserait le stock et la
    traçabilité FSC, ce qui est bien pire que de la saisir à la main.
    """
    refs = [l["article"] for l in lignes if l.get("article")]
    if not refs:
        return
    tables = {r[0] for r in conn_mysifa.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}

    mat: Dict[str, Dict[str, Any]] = {}
    if "matieres_premieres" in tables:
        for debut in range(0, len(refs), 400):
            lot = refs[debut:debut + 400]
            for r in conn_mysifa.execute(
                    "SELECT id, reference, designation, categorie FROM matieres_premieres "
                    "WHERE COALESCE(actif,1)=1 AND reference IN (%s)"
                    % ",".join("?" * len(lot)), lot):
                mat.setdefault(str(r["reference"]).strip(), dict(r))

    pf: Dict[str, Dict[str, Any]] = {}
    if "produits" in tables:
        for debut in range(0, len(refs), 400):
            lot = refs[debut:debut + 400]
            for r in conn_mysifa.execute(
                    "SELECT id, reference, designation FROM produits "
                    "WHERE reference IN (%s)" % ",".join("?" * len(lot)), lot):
                pf.setdefault(str(r["reference"]).strip(), dict(r))

    for l in lignes:
        a = l.get("article")
        m, p = mat.get(a or ""), pf.get(a or "")
        l["matiere_id"] = m["id"] if m else None
        l["matiere_nom"] = m["designation"] if m else None
        l["categorie"] = m["categorie"] if m else None
        l["produit_id"] = p["id"] if p else None
        l["produit_nom"] = p["designation"] if p else None
        # Ce que la ligne est, de l'avis de MySifa. « inconnu » n'est pas une
        # erreur : un consommable ou des frais d'outils n'ont rien à y faire.
        if str(l.get("article") or "").split("/")[0] == CODE1_FRAIS:
            l["nature"] = "frais"
        else:
            l["nature"] = ("matiere" if m else "produit" if p
                           else ("matiere_rvgi" if l.get("matiere_rvgi") else "inconnu"))


def _fournisseur_mysifa(conn_mysifa: sqlite3.Connection,
                        numeros: List[int]) -> Dict[int, Dict[str, Any]]:
    """Le fournisseur MySifa derrière le `numfou` de RVGI.

    Possible depuis que les fiches fournisseurs portent `rvgi_numero`. Sans ce
    lien, le formulaire demanderait de resaisir un fournisseur que l'ERP
    connaît déjà.
    """
    if not numeros:
        return {}
    cols = {r[1] for r in conn_mysifa.execute('PRAGMA table_info("fournisseurs_fsc")')}
    if "rvgi_numero" not in cols:
        return {}
    lot = list({int(n) for n in numeros if n})[:400]
    if not lot:
        return {}
    return {int(r["rvgi_numero"]): {"id": r["id"], "nom": r["nom"],
                                    "certificat": r["certificat"] if "certificat" in r.keys() else None}
            for r in conn_mysifa.execute(
                "SELECT id, nom, certificat, rvgi_numero FROM fournisseurs_fsc "
                "WHERE rvgi_numero IN (%s)" % ",".join("?" * len(lot)), lot)}


def chercher(conn_mysifa: sqlite3.Connection, q: str = "",
             limite: int = LIMITE, depuis: str = "") -> List[Dict[str, Any]]:
    """Les réceptions RVGI candidates, groupées par bon de livraison.

    Une réception se cherche par son n° de BL (« BL137434 »), par le n° de
    commande fournisseur, par le nom du fournisseur ou par une désignation
    d'article — c'est ce qu'un magasinier a sous les yeux quand le camion
    arrive.

    Le regroupement se fait sur (commande, BL) et non sur la seule commande :
    une commande peut être livrée en trois fois, et ce sont trois réceptions
    distinctes à saisir.
    """
    q = str(q or "").strip()
    conditions, params = [], []
    if depuis:
        conditions.append("l.amjl >= ?")
        params.append(depuis)
    if q:
        motif = "%" + q.replace("%", "") + "%"
        champs = ["l.ref", "l.numero", "e.rs", "c.des1", "c.code1", "c.code2"]
        conditions.append("(" + " OR ".join(
            "CAST(%s AS TEXT) LIKE ?" % c for c in champs) + ")")
        params += [motif] * len(champs)

    sql = _SQL + ("".join(" AND " + c for c in conditions))
    sql += " ORDER BY l.amjl DESC, l.numero DESC, l.ligne LIMIT ?"
    params.append(int(limite) * 25)

    with miroir.get_erp_db() as conn:
        if "lif_ligne" not in miroir.tables_presentes(conn):
            return []
        brutes = [dict(r) for r in conn.execute(sql, params)]
        fiches = _fiches_matiere(conn, [(b["code1"], b["code2"]) for b in brutes])

    lignes = []
    for b in brutes:
        art = _article(b.pop("code1", None), b.pop("code2", None))
        d = dict(b)
        d["article"] = art
        d.update(fiches.get(art or "", {}))
        d["qte"] = miroir.nettoyer(d.get("qte"), "qte")
        d["qte_commandee"] = miroir.nettoyer(d.get("qte_commandee"), "qte")
        d["prix_unitaire"] = miroir.nettoyer(d.get("prix_unitaire"), "prix")
        d["date_reception"] = miroir.nettoyer(d.get("date_reception"), "date")
        d["date_commande"] = miroir.nettoyer(d.get("date_commande"), "date")
        d["soldee"] = d.pop("position", None) == 2
        lignes.append(d)

    _resoudre_mysifa(conn_mysifa, lignes)
    fournisseurs = _fournisseur_mysifa(conn_mysifa, [l.get("numfou") for l in lignes])

    groupes: Dict[Any, Dict[str, Any]] = {}
    for l in lignes:
        cle = (str(l.get("cde") or ""), _txt(l.get("bl")) or "")
        g = groupes.get(cle)
        if g is None:
            f = fournisseurs.get(int(l.get("numfou") or 0)) or {}
            g = groupes[cle] = {
                "cde": l.get("cde"),
                "bl": _txt(l.get("bl")),
                "date_reception": l.get("date_reception"),
                "date_commande": l.get("date_commande"),
                "numfou": l.get("numfou"),
                "fournisseur": l.get("fournisseur"),
                # Ce que MySifa sait du fournisseur — c'est ce qui permet de
                # remplir le champ plutôt que d'afficher un nom à retaper.
                "fournisseur_id": f.get("id"),
                "fournisseur_mysifa": f.get("nom"),
                "certificat_fsc": f.get("certificat"),
                "lignes": [],
            }
        g["lignes"].append(l)

    out = list(groupes.values())
    for g in out:
        g["nb_lignes"] = len(g["lignes"])
        natures = {x["nature"] for x in g["lignes"]}
        g["natures"] = sorted(natures)
        g["nb_frais"] = sum(1 for x in g["lignes"] if x["nature"] == "frais")
        # Les frais ne décident de rien : une réception d'une bobine et de
        # deux frais de cliché reste une réception de matière. Une ligne que
        # MySifa ne reconnaît pas reste de la marchandise — pas un frais.
        mat = bool(natures & {"matiere", "matiere_rvgi"})
        pro = "produit" in natures
        g["ecran"] = ("mixte" if mat and pro
                      else "matiere" if mat
                      else "produit" if pro
                      else "frais" if natures <= {"frais"}
                      else "inconnu")
        g["qte_totale"] = sum(float(x["qte"] or 0) for x in g["lignes"]
                              if x["nature"] != "frais")
    out.sort(key=lambda g: (str(g["date_reception"] or ""), str(g["cde"] or "")), reverse=True)
    return out[:limite]


def une(conn_mysifa: sqlite3.Connection, cde: str, bl: str = "") -> Optional[Dict[str, Any]]:
    """Une réception précise, pour la reprendre dans le formulaire."""
    for g in chercher(conn_mysifa, str(cde), limite=LIMITE):
        if str(g.get("cde")) == str(cde) and (not bl or (g.get("bl") or "") == bl):
            return g
    return None
