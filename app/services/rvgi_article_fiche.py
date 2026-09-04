"""Pré-remplir une fiche technique MySifa depuis un article de RVGI.

Pourquoi ce module existe
-------------------------
Une fiche technique se saisit en cinquante champs. RVGI en connaît déjà la
plus grande partie, éclatée dans cinq tables que personne ne joint à la main :

    fic_art   l'article vendu — libellé, référence client, format commandé
    gpr_ff    sa fiche de fabrication — machine, laize matière, outils, matière
    out_dec   l'outil de découpe — LA source de la géométrie de l'étiquette
    mat_mat   la matière — support, adhésif, protecteur, grammage
    gpr_ff1   l'impression — pantone, anilox, composition, tête par tête

`out_dec` est la table qui compte. Vérification faite sur la fiche papier de
623/0014, outil 2796 : format 104,5 × 148,4 (`ftl`/`fta`), rayons 6 (`ray`),
module 107,75 × 152,4 (`ftl+espl` / `fta+espa`), échenillage latéral int. 3,25
(`espl`), horizontal 4 (`espa`), latéral ext. 1,625 (`espl/2`), 192 dents
(`nbd`), 4 de front (`nbl`), 4 d'avance (`nba`), épaisseur 52 (`eps`). Tout
concorde, au centième.

Deux mises en garde qui expliquent la forme du résultat
-------------------------------------------------------
1. **On ne renvoie jamais une valeur sans dire d'où elle vient.** `provenance`
   nomme la table pour chaque champ, et l'écran l'affiche. Une fiche technique
   fausse ne se voit pas à l'écran : elle sort à l'inventaire, des semaines
   plus tard. Celui qui valide doit savoir ce qu'il valide.

2. **`gpr_ff` est un référentiel partiel.** 585 lignes pour 7 688 articles, et
   la plupart datées d'avant 2010. Sans elle, pas d'outil, donc pas de
   géométrie : le pré-remplissage se réduit alors au libellé et au format de
   `fic_art`. C'est un service rendu, jamais une promesse.

Le nombre de fronts mérite une note à lui seul. `out_dec.nbl` est la valeur
juste — c'est le nombre de poses de l'outil, celui que le métrage divise. Il
alimente `outil1_nb_front`, JAMAIS `mod_nb_front`, qui vaut 1 sur 878 fiches
sur 909 en production et n'est pas une donnée (voir la règle
of-fiches-techniques).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.services import erp_mirror as miroir


# ── Petits utilitaires ───────────────────────────────────────────────────────

def _nb(v) -> Optional[float]:
    if v in (None, ""):
        return None
    try:
        f = float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return f


def _pos(v) -> Optional[float]:
    """Une valeur nulle dans RVGI veut dire « non renseigné », pas « zéro ».

    `laiout = 0`, `nbcoul = 0`, `ray = 0` sont des cases vides du logiciel, et
    les recopier écrirait un zéro là où la fiche doit rester vide — ce qui se
    lit ensuite comme une valeur vérifiée.
    """
    f = _nb(v)
    return f if (f is not None and f > 0) else None


def _txt(v) -> Optional[str]:
    s = ("" if v is None else str(v)).strip()
    return s or None


def _mm(v: Optional[float]) -> str:
    if v is None:
        return ""
    return str(int(v)) if float(v) == int(v) else str(v)


# ── Ce que disent les libellés de l'article ──────────────────────────────────
#
# `fic_art` porte quatre libellés, et les trois derniers ne sont pas de la
# décoration : ils décrivent le produit fini tel qu'il part chez le client.
#
#     libc1  « Etiquette 105 x 148 mm. »
#     libc2  « Therm. Eco. Permanent, M. 76, Enr. Ext. »
#     libc3  « Bobine de 300 étiquettes, M. 25. »
#     libc4  « Carton de 16 bobines »
#
# `libc3` est mot pour mot le conditionnement imprimé sur l'OF, et `libc4`
# donne le nombre de bobines par carton que porte la fiche technique. On les
# lit donc — mais ce sont des PHRASES, pas des colonnes : une extraction se
# trompe silencieusement là où une colonne vide se voit. Les motifs ci-dessous
# sont donc ancrés au plus court, et tout ce qui en sort est marqué
# « libellé » dans la provenance, pour que l'écran le signale comme à relire.

_NOMBRE = r"([0-9][0-9\s.\u202f\u00a0]*)"


def _entier(brut: Optional[str]) -> Optional[int]:
    """« 1.500 », « 2 000 », « 1 500 » → 1500. Le point est un séparateur de
    milliers dans ces libellés, jamais une décimale."""
    if not brut:
        return None
    net = re.sub(r"[\s.\u202f\u00a0]", "", brut)
    try:
        return int(net)
    except ValueError:
        return None


def _indices_libelles(art: dict) -> Dict[str, Any]:
    """Ce qu'on sait lire dans les libellés 2, 3 et 4 d'un article."""
    l2 = _txt(art.get("libc2")) or ""
    l3 = _txt(art.get("libc3")) or ""
    l4 = _txt(art.get("libc4")) or ""
    out: Dict[str, Any] = {}

    if l3:
        # Le conditionnement, tel quel : c'est la phrase que l'OF imprime.
        out["conditionnement"] = l3.rstrip(".")

    m = re.search(r"[Bb]obine\s+de\s+" + _NOMBRE + r"\s*étiquettes?", l3)
    if m:
        out["nb_etiq_bobin"] = _entier(m.group(1))

    m = re.search(r"[Cc]arton\s+de\s+" + _NOMBRE + r"\s*bobines?", l4 or l3)
    if m:
        out["nb_bobines_carton"] = _entier(m.group(1))

    # « M. 76 », « M.40 », « M. 25. » — le diamètre du mandrin.
    m = re.search(r"\bM\.\s*(\d{2,3})\b", l3 + " " + l2)
    if m:
        out["mandrin_dia"] = m.group(1)

    # « Enr. Ext. », « Ext. P.A. », « Enr. Int. »
    if re.search(r"\bEnr\.?\s*Ext|(?<![A-Za-z])Ext\.", l2 + " " + l3):
        out["enroulement"] = "Extérieur"
    elif re.search(r"\bEnr\.?\s*Int|(?<![A-Za-z])Int\.", l2 + " " + l3):
        out["enroulement"] = "Intérieur"

    return out


# ── Lectures élémentaires ────────────────────────────────────────────────────

def _machines(c, presentes) -> Dict[Any, str]:
    if "mac_pro" not in presentes:
        return {}
    return {r["code"]: str(r["nom"]).strip()
            for r in c.execute(
                "SELECT code, nom FROM mac_pro WHERE corbeille = 0 AND type = 1")
            if r["nom"]}


def _outil(c, presentes, numero) -> Optional[dict]:
    """L'outil de découpe `numero` — la géométrie de l'étiquette.

    `numero` est un entier côté `gpr_ff` et côté `out_dec` : on compare en
    texte des deux côtés pour ne dépendre ni de l'un ni de l'autre.
    """
    if "out_dec" not in presentes or not numero:
        return None
    r = c.execute(
        "SELECT numero, machine, nbd, nbl, nba, nbt, ftl, fta, lt, at, "
        "       espl, espa, eche, ray, eps, hcou1 "
        "FROM out_dec WHERE corbeille = 0 AND CAST(numero AS TEXT) = ? LIMIT 1",
        (str(numero).strip(),),
    ).fetchone()
    return dict(r) if r else None


def _matiere(c, presentes, code1, code2) -> Optional[dict]:
    if "mat_mat" not in presentes or not code1:
        return None
    r = c.execute(
        "SELECT code1, code2, libc1, libc2, pds, m1_epais, m1_adh, m1_pro "
        "FROM mat_mat WHERE corbeille = 0 AND CAST(code1 AS TEXT) = ? "
        "  AND CAST(code2 AS TEXT) = ? LIMIT 1",
        (str(code1).strip(), str(code2 or "").strip()),
    ).fetchone()
    return dict(r) if r else None


def _impression(c, presentes, code1, code2) -> Optional[dict]:
    if "gpr_ff1" not in presentes:
        return None
    r = c.execute(
        "SELECT * FROM gpr_ff1 WHERE corbeille = 0 AND code1 = ? AND code2 = ? LIMIT 1",
        (code1, code2),
    ).fetchone()
    return dict(r) if r else None


def _suffixe(n: int) -> str:
    """gpr_ff1 numérote ses vingt têtes en colonnes : `pms`, `pms_2`, `pms_3`…"""
    return "" if n == 1 else "_%d" % n


# ── Lecture unique du miroir ─────────────────────────────────────────────────

def _lire_tout(a: str, b: str) -> Optional[dict]:
    """Tout ce que RVGI sait de l'article, en une ouverture du miroir.

    Deux consommateurs — la fiche technique et l'OF — regardent les mêmes
    tables. Les lire deux fois, c'est se donner deux occasions de diverger.
    """
    with miroir.get_erp_db() as c:
        presentes = miroir.tables_presentes(c)
        if "fic_art" not in presentes:
            return None
        art = c.execute(
            "SELECT code1, code2, libc1, libc2, libc3, libc4, cltc2, ftl, fth, pdsn "
            "FROM fic_art WHERE corbeille = 0 AND code1 = ? AND code2 = ? LIMIT 1",
            (a, b),
        ).fetchone()
        if not art:
            return None
        art = dict(art)

        ff = None
        if "gpr_ff" in presentes:
            r = c.execute(
                "SELECT nmac1, laiout, laimat, nbcoul, cliche, m1cod1, m1cod2, "
                "       ndec1, ndec2, ndec3, amj "
                "FROM gpr_ff WHERE corbeille = 0 AND code1 = ? AND code2 = ? "
                "ORDER BY COALESCE(amj,'') DESC LIMIT 1", (a, b),
            ).fetchone()
            ff = dict(r) if r else None

        outils: Dict[int, dict] = {}
        if ff:
            for rang, cle in ((1, "ndec1"), (2, "ndec2"), (3, "ndec3")):
                o = _outil(c, presentes, ff[cle])
                if o:
                    outils[rang] = o

        return {
            "art": art,
            "ff": ff,
            "outils": outils,
            "machines": _machines(c, presentes) if ff else {},
            "mat": _matiere(c, presentes, ff["m1cod1"], ff["m1cod2"]) if ff else None,
            "imp": _impression(c, presentes, a, b) if ff else None,
        }


def _article_public(art: dict) -> dict:
    largeur, hauteur = _pos(art["ftl"]), _pos(art["fth"])
    return {
        "code1": str(art["code1"]).strip(), "code2": str(art["code2"]).strip(),
        "reference": "%s/%s" % (str(art["code1"]).strip(), str(art["code2"]).strip()),
        "libelle": _txt(art["libc1"]),
        "libelle_matiere": _txt(art["libc2"]),
        "libelle_conditionnement": _txt(art["libc3"]),
        "libelle_carton": _txt(art["libc4"]),
        "ref_client": _txt(art["cltc2"]),
        "largeur": largeur, "hauteur": hauteur,
        "format": ("%s x %s mm" % (_mm(largeur), _mm(hauteur))
                   if largeur and hauteur else None),
    }


# ── Rattachement aux références de MyStock ───────────────────────────────────

def _resoudre_references(champs: Dict[str, Any], provenance: Dict[str, str],
                         liens: List[Tuple[str, str, str]]) -> None:
    """Pose les `*_ref_id` que `mp_fiche_mapping` permet déjà de trancher.

    RVGI rend des libellés (« Thermique Eco 70g »), MyStock veut des id. La
    table de correspondance existe et contient soixante entrées : s'en servir
    ici évite à l'ADV de rechoisir à la main ce que quelqu'un a déjà tranché.

    Ce qui ne se résout pas reste en texte, sans id — et l'écran l'affiche
    « non rattaché au stock ». C'est le bon comportement : un libellé qu'on ne
    sait pas rattacher est une information à traiter, pas à masquer.
    """
    a_resoudre = [(kind, champs[col]) for col_id, col, kind in liens
                  if champs.get(col)]
    if not a_resoudre:
        return
    from database import get_db
    with get_db() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(mp_fiche_mapping)")}
        if not cols:
            return
        for col_id, col, kind in liens:
            valeur = champs.get(col)
            if not valeur or champs.get(col_id):
                continue
            r = conn.execute(
                "SELECT matiere_id FROM mp_fiche_mapping "
                " WHERE kind = ? AND LOWER(TRIM(source_value)) = LOWER(TRIM(?)) LIMIT 1",
                (kind, str(valeur)),
            ).fetchone()
            if r:
                champs[col_id] = r["matiere_id"]
                provenance[col_id] = "mp_fiche_mapping"


_LIENS_FICHE = [
    ("support_ref_id",  "support",      "support"),
    ("glassine_ref_id", "glassine",     "glassine"),
    ("adhesif_ref_id",  "adhesif",      "adhesif"),
    ("mandrin_ref_id",  "mandrin_dia",  "mandrin"),
]

_LIENS_OF = [
    ("matiere_ref_id",  "matiere",       "support"),
    ("glassine_ref_id", "glassine",      "glassine"),
    ("adhesif_ref_id",  "adhesif_label", "adhesif"),
    ("mandrin_ref_id",  "mandrins_dia",  "mandrin"),
]


# ── Fiche technique ──────────────────────────────────────────────────────────

def prefill_fiche(code1: str, code2: str) -> Optional[Dict[str, Any]]:
    """Champs de `fiches_techniques` déductibles de l'article `code1/code2`.

    Retourne `None` si l'article est inconnu du miroir. Sinon :

        {"article": {...}, "champs": {colonne: valeur},
         "provenance": {colonne: table}, "sources": {...}, "manques": [...]}

    `champs` ne contient que ce qui a une valeur : une clé absente veut dire
    « RVGI ne sait pas », et l'écran doit laisser la case vide plutôt que d'y
    écrire un zéro.
    """
    a, b = str(code1 or "").strip(), str(code2 or "").strip()
    if not a or not b:
        return None
    lu = _lire_tout(a, b)
    if not lu:
        return None

    art, ff, outils, mat, imp = lu["art"], lu["ff"], lu["outils"], lu["mat"], lu["imp"]
    article = _article_public(art)
    champs: Dict[str, Any] = {}
    provenance: Dict[str, str] = {}
    manques: List[str] = []
    sources = {"gpr_ff": bool(ff), "out_dec": sorted(o["numero"] for o in outils.values()),
               "mat_mat": ("%s/%s" % (mat["code1"], mat["code2"])) if mat else None,
               "gpr_ff1": bool(imp),
               "gpr_ff_maj_le": _txt(ff["amj"]) if ff else None}

    def poser(colonne, valeur, table):
        if valeur in (None, ""):
            return
        champs[colonne] = valeur
        provenance[colonne] = table

    poser("reference", article["reference"], "fic_art")
    poser("designation", article["libelle"], "fic_art")
    poser("format", article["format"], "fic_art")
    poser("eti_laize", article["largeur"], "fic_art")
    poser("eti_longueur", article["hauteur"], "fic_art")

    # Le produit fini, lu dans les libellés 2 à 4.
    for cle, val in _indices_libelles(art).items():
        poser(cle, val, "libellé")

    if not ff:
        manques.append("Aucune fiche de fabrication dans RVGI pour cet article : "
                       "géométrie, outils et matière restent à saisir.")
        _resoudre_references(champs, provenance, _LIENS_FICHE)
        return {"article": article, "champs": champs, "provenance": provenance,
                "sources": sources, "manques": manques}

    poser("machine", lu["machines"].get(ff["nmac1"]), "gpr_ff")
    poser("laize_optimale", _pos(ff["laimat"]), "gpr_ff")
    poser("laize_optionnelle", _pos(ff["laiout"]), "gpr_ff")
    poser("nb_couleurs", int(_pos(ff["nbcoul"]) or 0) or None, "gpr_ff")
    if _txt(ff["cliche"]):
        poser("remarque", "Cliché " + _txt(ff["cliche"]), "gpr_ff")

    for rang, out in sorted(outils.items()):
        p = "outil%d_" % rang
        poser(p + "numero_sifa", str(out["numero"]), "out_dec")
        poser(p + "nb_dents", int(_pos(out["nbd"]) or 0) or None, "out_dec")
        # nbl = les poses en laize. C'est LE nombre de fronts, celui qui divise
        # le métrage — pas `mod_nb_front`, qui n'est pas rempli.
        poser(p + "nb_front", int(_pos(out["nbl"]) or 0) or None, "out_dec")
        poser(p + "nb_avance", int(_pos(out["nba"]) or 0) or None, "out_dec")
        poser(p + "epaisseur", _pos(out["eps"]), "out_dec")
        if rang != 1:
            continue
        # La colonne « Laize » de l'outil, sur la fiche papier, est celle de la
        # BOBINE (440 sur la fiche 623/0014), pas la laize développée de
        # l'outil (`out_dec.lt` = 443,75).
        poser("outil1_laize", _pos(ff["laimat"]), "gpr_ff")
        # La géométrie vient de l'outil, pas de l'article : `fic_art` porte le
        # format commandé, l'outil porte celui qui est réellement découpé.
        etl, eta = _pos(out["ftl"]), _pos(out["fta"])
        espl, espa = _nb(out["espl"]), _nb(out["espa"])
        poser("eti_laize", etl, "out_dec")
        poser("eti_longueur", eta, "out_dec")
        poser("eti_rayons", _pos(out["ray"]), "out_dec")
        if etl and eta:
            poser("format", "%s x %s mm" % (_mm(etl), _mm(eta)), "out_dec")
        if espl is not None:
            poser("lateral_int", espl, "out_dec")
            # Le latéral extérieur vaut la moitié de l'espacement : la découpe
            # partage l'inter-étiquette entre les deux bords.
            poser("lateral_ext", round(espl / 2.0, 4), "out_dec")
            if etl:
                poser("mod_laize", round(etl + espl, 4), "out_dec")
        if espa is not None:
            poser("horizontal", espa, "out_dec")
            if eta:
                poser("mod_longueur", round(eta + espa, 4), "out_dec")

    if not outils:
        manques.append("Outil de découpe absent de RVGI : la géométrie de "
                       "l'étiquette et du module reste à saisir.")

    # Métrage au mille : l'identité du métrage, mille étiquettes ÷ nombre de
    # fronts × longueur du module. Proposée parce qu'elle est vérifiable à
    # l'œil, marquée « calcul » pour ne pas passer pour une valeur relevée.
    mod_lg, fronts = champs.get("mod_longueur"), champs.get("outil1_nb_front")
    if mod_lg and fronts:
        poser("qte_au_mille", round(1000.0 / fronts * mod_lg / 1000.0, 4), "calcul")

    if mat:
        poser("support", _txt(mat["libc1"]), "mat_mat")
        poser("matiere", _txt(mat["libc1"]), "mat_mat")
        poser("adhesif", _txt(mat["m1_adh"]), "mat_mat")
        poser("glassine", _txt(mat["m1_pro"]), "mat_mat")
        poser("grammage", _pos(mat["pds"]), "mat_mat")
        poser("epaisseur", _pos(mat["m1_epais"]), "mat_mat")
    else:
        manques.append("Matière absente de RVGI : support, adhésif et glassine "
                       "restent à saisir.")

    if imp:
        for tete in (1, 2, 3):
            sfx = _suffixe(tete)
            pantone = _txt(imp.get("pms" + sfx))
            couleur = _txt(imp.get("coul" + sfx))
            anilox = _pos(imp.get("anilox" + sfx))
            compo = _txt(imp.get("descriptif" + sfx))
            if not any((pantone, couleur, anilox, compo)):
                continue
            p = "tete%d_" % tete
            poser(p + "pantone", pantone, "gpr_ff1")
            poser(p + "couleur", couleur, "gpr_ff1")
            poser(p + "anilox", _mm(anilox), "gpr_ff1")
            poser(p + "composition", compo, "gpr_ff1")
        rv = _nb(imp.get("recver"))
        if rv == 1:
            poser("recto", 1, "gpr_ff1")
        elif rv == 2:
            poser("verso", 1, "gpr_ff1")

    _resoudre_references(champs, provenance, _LIENS_FICHE)
    return {"article": article, "champs": champs, "provenance": provenance,
            "sources": sources, "manques": manques}


# ── Ordre de fabrication ─────────────────────────────────────────────────────

def _grammage_adhesif(libelle: Optional[str]) -> Optional[float]:
    """« Permanent 19g » → 19. La quantité d'adhésif au m², en grammes.

    C'est le chiffre encadré en orange sur l'OF, celui que l'opérateur lit de
    loin. Il n'a pas de colonne dans RVGI : il est dans le libellé de la
    matière, toujours sous la même forme.
    """
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*g\b", str(libelle or ""))
    return _nb(m.group(1)) if m else None


# Ce qu'un OF précédent peut redonner. On exclut tout ce qui appartient à la
# commande du jour — quantités, dates, numéro : le reste décrit le produit, et
# le produit ne change pas d'un OF à l'autre.
_REPRISE_OF = [
    "machine", "laize", "format", "matiere", "ref_matiere",
    "ref_matiere_fournisseur", "glassine", "ref_adhesif", "adhesif_label",
    "qte_adhesif_g", "qte_au_mille", "conditionnement", "tolerance",
    "cartons_type", "cales_sachets", "mandrins_dia", "mandrin_longueur",
    "bobinettes_completes", "palette_type",
    "outil_1_forme", "outil_1_numero", "outil_1_angle", "outil_1_mag",
    "outil_1_cp", "outil_1_hauteur", "outil_1_fournisseur",
    "outil_2_forme", "outil_2_numero", "outil_2_angle", "outil_2_mag",
    "outil_2_cp", "outil_2_hauteur", "outil_2_fournisseur",
    "plieuse_pignon", "nb_pouces", "particularites",
    "matiere_ref_id", "glassine_ref_id", "adhesif_ref_id",
    "carton_ref_id", "mandrin_ref_id", "palette_ref_id",
]


def _completer_depuis_mysifa(reference: str, champs: Dict[str, Any],
                             provenance: Dict[str, str]) -> Optional[str]:
    """Comble les vides avec le dernier OF de MySifa pour la même référence.

    `gpr_ff` ne couvre que 585 articles sur 7 688 : pour tous les autres, RVGI
    ne sait dire ni la machine, ni la laize, ni l'outil. Or MySifa les connaît
    — elle a déjà fabriqué ce produit, et l'OF précédent est là.

    Ce n'est pas une devinette : c'est ce que l'ADV fait à la main aujourd'hui,
    rouvrir le dernier OF de la référence et recopier. La provenance le dit
    (« OF 9931861 »), et rien n'écrase une valeur déjà posée — RVGI, quand il
    répond, garde la main.

    Retourne le numéro de l'OF repris, ou None.
    """
    ref = str(reference or "").strip()
    if not ref:
        return None
    from database import get_db
    with get_db() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(of_imports)")}
        if not cols:
            return None
        row = conn.execute(
            "SELECT * FROM of_imports "
            " WHERE LOWER(TRIM(reference)) = LOWER(TRIM(?)) "
            "    OR LOWER(TRIM(reference)) LIKE LOWER(TRIM(?)) || ' - %' "
            " ORDER BY COALESCE(date_creation, date_import) DESC LIMIT 1",
            (ref, ref),
        ).fetchone()
    if row is None:
        return None
    precedent = dict(row)
    source = "OF " + str(precedent.get("of_numero") or precedent.get("id"))
    for colonne in _REPRISE_OF:
        if colonne not in cols or champs.get(colonne) not in (None, ""):
            continue
        valeur = precedent.get(colonne)
        if valeur in (None, ""):
            continue
        champs[colonne] = valeur
        provenance[colonne] = source
    return source


def prefill_of(code1: str, code2: str) -> Optional[Dict[str, Any]]:
    """Champs de `of_imports` déductibles de l'article `code1/code2`.

    Appelé quand l'ADV rattache une commande à un OF : la ligne de commande
    porte un article, et l'article porte la moitié de l'OF. Ce qui reste à
    saisir, ce sont les quantités et les réglages du jour — pas la description
    du produit, qui ne change pas d'un OF à l'autre.
    """
    a, b = str(code1 or "").strip(), str(code2 or "").strip()
    if not a or not b:
        return None
    lu = _lire_tout(a, b)
    if not lu:
        return None

    art, ff, outils, mat = lu["art"], lu["ff"], lu["outils"], lu["mat"]
    article = _article_public(art)
    champs: Dict[str, Any] = {}
    provenance: Dict[str, str] = {}
    manques: List[str] = []
    sources = {"gpr_ff": bool(ff), "out_dec": sorted(o["numero"] for o in outils.values()),
               "mat_mat": ("%s/%s" % (mat["code1"], mat["code2"])) if mat else None,
               "gpr_ff_maj_le": _txt(ff["amj"]) if ff else None}

    def poser(colonne, valeur, table):
        if valeur in (None, ""):
            return
        champs[colonne] = valeur
        provenance[colonne] = table

    poser("reference", article["reference"], "fic_art")
    poser("format", article["format"], "fic_art")

    indices = _indices_libelles(art)
    poser("conditionnement", indices.get("conditionnement"), "libellé")
    if indices.get("mandrin_dia"):
        # Le libellé donne un diamètre (« M. 76 »), pas une référence de tube.
        # On l'écrit tel quel : le champ affichera « non rattaché au stock »
        # tant que personne n'aura choisi la référence, ce qui est exactement
        # l'information utile.
        poser("mandrins_dia", "M. " + indices["mandrin_dia"], "libellé")

    if not ff:
        repris = _completer_depuis_mysifa(article["reference"], champs, provenance)
        sources["of_precedent"] = repris
        if repris:
            manques.append("RVGI n'a pas de fiche de fabrication pour cet "
                           "article : le reste vient de l'%s. À relire." % repris)
        else:
            manques.append("Aucune fiche de fabrication dans RVGI et aucun OF "
                           "antérieur pour cette référence : machine, laize, "
                           "matière et outillage restent à saisir.")
        _resoudre_references(champs, provenance, _LIENS_OF)
        return {"article": article, "champs": champs, "provenance": provenance,
                "sources": sources, "manques": manques}

    poser("machine", lu["machines"].get(ff["nmac1"]), "gpr_ff")
    # La « Laize » de l'OF est celle de la bobine montée.
    poser("laize", _pos(ff["laimat"]), "gpr_ff")

    for rang, out in sorted(outils.items()):
        if rang > 2:
            break
        poser("outil_%d_numero" % rang, str(out["numero"]), "out_dec")
        poser("outil_%d_hauteur" % rang, _pos(out["hcou1"]), "out_dec")

    o1 = outils.get(1)
    if o1:
        etl, eta = _pos(o1["ftl"]), _pos(o1["fta"])
        espa = _nb(o1["espa"])
        if etl and eta:
            poser("format", "%s x %s mm" % (_mm(etl), _mm(eta)), "out_dec")
        fronts = int(_pos(o1["nbl"]) or 0)
        if eta is not None and espa is not None and fronts:
            # Même identité que sur la fiche : la quantité au mille est la
            # longueur d'un module divisée par le nombre de fronts.
            poser("qte_au_mille",
                  round(1000.0 / fronts * (eta + espa) / 1000.0, 4), "calcul")
    else:
        manques.append("Outil de découpe absent de RVGI : outillage et "
                       "quantité au mille restent à saisir.")

    if mat:
        poser("matiere", _txt(mat["libc1"]), "mat_mat")
        poser("glassine", _txt(mat["m1_pro"]), "mat_mat")
        poser("adhesif_label", _txt(mat["m1_adh"]), "mat_mat")
        poser("qte_adhesif_g", _grammage_adhesif(mat["m1_adh"]), "mat_mat")
    else:
        manques.append("Matière absente de RVGI : matière, glassine et adhésif "
                       "restent à saisir.")

    # RVGI a répondu, mais partiellement : l'OF précédent comble ce qui reste.
    sources["of_precedent"] = _completer_depuis_mysifa(
        article["reference"], champs, provenance)
    _resoudre_references(champs, provenance, _LIENS_OF)
    return {"article": article, "champs": champs, "provenance": provenance,
            "sources": sources, "manques": manques}
