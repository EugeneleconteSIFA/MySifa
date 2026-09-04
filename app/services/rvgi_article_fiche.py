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

from typing import Any, Dict, Optional, Tuple

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


# ── Le pré-remplissage ───────────────────────────────────────────────────────

def prefill_fiche(code1: str, code2: str) -> Optional[Dict[str, Any]]:
    """Champs de `fiches_techniques` déductibles de l'article `code1/code2`.

    Retourne `None` si l'article est inconnu du miroir. Sinon :

        {"article": {...}, "champs": {colonne: valeur}, "provenance": {colonne: table},
         "sources": {"gpr_ff": bool, "out_dec": [n°], "mat_mat": "886/0021", ...},
         "manques": [ce que RVGI ne sait pas dire]}

    `champs` ne contient que ce qui a une valeur : une clé absente veut dire
    « RVGI ne sait pas », et l'écran doit laisser la case vide plutôt que d'y
    écrire un zéro.
    """
    a, b = str(code1 or "").strip(), str(code2 or "").strip()
    if not a or not b:
        return None

    champs: Dict[str, Any] = {}
    provenance: Dict[str, str] = {}
    sources: Dict[str, Any] = {"gpr_ff": False, "out_dec": [], "mat_mat": None,
                               "gpr_ff1": False}
    manques = []

    def poser(colonne, valeur, table):
        if valeur in (None, ""):
            return
        champs[colonne] = valeur
        provenance[colonne] = table

    with miroir.get_erp_db() as c:
        presentes = miroir.tables_presentes(c)
        if "fic_art" not in presentes:
            return None

        art = c.execute(
            "SELECT code1, code2, libc1, cltc2, ftl, fth, pdsn "
            "FROM fic_art WHERE corbeille = 0 AND code1 = ? AND code2 = ? LIMIT 1",
            (a, b),
        ).fetchone()
        if not art:
            return None
        art = dict(art)

        largeur, hauteur = _pos(art["ftl"]), _pos(art["fth"])
        article = {
            "code1": a, "code2": b, "reference": "%s/%s" % (a, b),
            "libelle": _txt(art["libc1"]),
            "ref_client": _txt(art["cltc2"]),
            "largeur": largeur, "hauteur": hauteur,
            "format": ("%s x %s mm" % (_mm(largeur), _mm(hauteur))
                       if largeur and hauteur else None),
        }
        poser("reference", article["reference"], "fic_art")
        poser("designation", article["libelle"], "fic_art")
        poser("format", article["format"], "fic_art")
        poser("eti_laize", largeur, "fic_art")
        poser("eti_longueur", hauteur, "fic_art")

        # ── Fiche de fabrication ────────────────────────────────────────────
        ff = None
        if "gpr_ff" in presentes:
            r = c.execute(
                "SELECT nmac1, laiout, laimat, nbcoul, cliche, m1cod1, m1cod2, "
                "       ndec1, ndec2, ndec3, amj "
                "FROM gpr_ff WHERE corbeille = 0 AND code1 = ? AND code2 = ? "
                "ORDER BY COALESCE(amj,'') DESC LIMIT 1", (a, b),
            ).fetchone()
            ff = dict(r) if r else None
        if not ff:
            manques.append("Aucune fiche de fabrication dans RVGI pour cet "
                           "article : géométrie, outils et matière restent à saisir.")
            return {"article": article, "champs": champs, "provenance": provenance,
                    "sources": sources, "manques": manques}

        sources["gpr_ff"] = True
        sources["gpr_ff_maj_le"] = _txt(ff["amj"])
        machines = _machines(c, presentes)
        poser("machine", machines.get(ff["nmac1"]), "gpr_ff")
        poser("laize_optimale", _pos(ff["laimat"]), "gpr_ff")
        poser("laize_optionnelle", _pos(ff["laiout"]), "gpr_ff")
        poser("nb_couleurs", int(_pos(ff["nbcoul"]) or 0) or None, "gpr_ff")
        if _txt(ff["cliche"]):
            poser("remarque", "Cliché " + _txt(ff["cliche"]), "gpr_ff")

        # ── Outils de découpe ───────────────────────────────────────────────
        for rang, cle in ((1, "ndec1"), (2, "ndec2"), (3, "ndec3")):
            out = _outil(c, presentes, ff[cle])
            if not out:
                continue
            sources["out_dec"].append(out["numero"])
            p = "outil%d_" % rang
            poser(p + "numero_sifa", str(out["numero"]), "out_dec")
            poser(p + "nb_dents", int(_pos(out["nbd"]) or 0) or None, "out_dec")
            # nbl = les poses en laize. C'est LE nombre de fronts, celui qui
            # divise le métrage — pas `mod_nb_front`, qui n'est pas rempli.
            poser(p + "nb_front", int(_pos(out["nbl"]) or 0) or None, "out_dec")
            poser(p + "nb_avance", int(_pos(out["nba"]) or 0) or None, "out_dec")
            poser(p + "epaisseur", _pos(out["eps"]), "out_dec")
            if rang == 1:
                # La colonne « Laize » de l'outil, sur la fiche papier, est
                # celle de la BOBINE (440 sur la fiche 623/0014), pas la laize
                # développée de l'outil (`out_dec.lt` = 443,75). Les confondre
                # décale le calcul de frontal de quelques millimètres par pose.
                poser("outil1_laize", _pos(ff["laimat"]), "gpr_ff")
                # La géométrie de l'étiquette vient de l'outil, pas de
                # l'article : `fic_art` porte le format commandé, l'outil porte
                # celui qui est réellement découpé.
                etl, eta = _pos(out["ftl"]), _pos(out["fta"])
                espl, espa = _nb(out["espl"]), _nb(out["espa"])
                poser("eti_laize", etl, "out_dec")
                poser("eti_longueur", eta, "out_dec")
                poser("eti_rayons", _pos(out["ray"]), "out_dec")
                if etl and eta:
                    poser("format", "%s x %s mm" % (_mm(etl), _mm(eta)), "out_dec")
                if espl is not None:
                    poser("lateral_int", espl, "out_dec")
                    # Le latéral extérieur vaut la moitié de l'espacement : la
                    # découpe partage l'inter-étiquette entre les deux bords.
                    poser("lateral_ext", round(espl / 2.0, 4), "out_dec")
                    if etl:
                        poser("mod_laize", round(etl + espl, 4), "out_dec")
                if espa is not None:
                    poser("horizontal", espa, "out_dec")
                    if eta:
                        poser("mod_longueur", round(eta + espa, 4), "out_dec")

        if not sources["out_dec"]:
            manques.append("Outil de découpe absent de RVGI : la géométrie de "
                           "l'étiquette et du module reste à saisir.")

        # ── Métrage au mille, calculé ──────────────────────────────────────
        # Ce n'est pas une donnée de RVGI : c'est l'identité du métrage,
        # mille étiquettes ÷ nombre de fronts × longueur du module. On la
        # propose parce qu'elle est vérifiable à l'œil, et on la marque comme
        # calculée pour qu'elle ne passe pas pour une valeur relevée.
        mod_lg, fronts = champs.get("mod_longueur"), champs.get("outil1_nb_front")
        if mod_lg and fronts:
            poser("qte_au_mille", round(1000.0 / fronts * mod_lg / 1000.0, 4), "calcul")

        # ── Matière ─────────────────────────────────────────────────────────
        mat = _matiere(c, presentes, ff["m1cod1"], ff["m1cod2"])
        if mat:
            sources["mat_mat"] = "%s/%s" % (mat["code1"], mat["code2"])
            poser("support", _txt(mat["libc1"]), "mat_mat")
            poser("matiere", _txt(mat["libc1"]), "mat_mat")
            poser("adhesif", _txt(mat["m1_adh"]), "mat_mat")
            poser("glassine", _txt(mat["m1_pro"]), "mat_mat")
            poser("grammage", _pos(mat["pds"]), "mat_mat")
            poser("epaisseur", _pos(mat["m1_epais"]), "mat_mat")
        else:
            manques.append("Matière absente de RVGI : support, adhésif et "
                           "glassine restent à saisir.")

        # ── Impression ──────────────────────────────────────────────────────
        imp = _impression(c, presentes, a, b)
        if imp:
            sources["gpr_ff1"] = True
            for tete in (1, 2, 3):
                s = _suffixe(tete)
                pantone = _txt(imp.get("pms" + s))
                couleur = _txt(imp.get("coul" + s))
                anilox = _pos(imp.get("anilox" + s))
                compo = _txt(imp.get("descriptif" + s))
                if not any((pantone, couleur, anilox, compo)):
                    continue
                p = "tete%d_" % tete
                poser(p + "pantone", pantone, "gpr_ff1")
                poser(p + "couleur", couleur, "gpr_ff1")
                poser(p + "anilox", _mm(anilox), "gpr_ff1")
                poser(p + "composition", compo, "gpr_ff1")
            # recver : 1 = recto, 2 = verso dans RVGI.
            rv = _nb(imp.get("recver"))
            if rv == 1:
                poser("recto", 1, "gpr_ff1")
            elif rv == 2:
                poser("verso", 1, "gpr_ff1")

    return {"article": article, "champs": champs, "provenance": provenance,
            "sources": sources, "manques": manques}
