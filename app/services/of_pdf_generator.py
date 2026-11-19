"""
Génération PDF — Ordre de fabrication, posé sur le modèle vierge.

Sert deux cas qui n'en font qu'un : prévisualiser un OF importé sans PDF
(Access), et imprimer un OF saisi dans MySifa. Dans les deux cas il n'existe
aucun document d'origine, et l'atelier attend le même papier qu'avant.

Modèle : `data/of_template.pdf` — l'OF réel de l'atelier dont toutes les
valeurs ont été retirées (le cadre, les libellés et les aplats de couleur
restent). C'est pour cela que les coordonnées ci-dessous ne sont pas des
réglages esthétiques : ce sont les positions relevées sur le document
d'origine, case par case. Les déplacer décale le texte hors de sa case.

Le modèle est en A4 (595,28 × 841,92). La version précédente supposait du
US Letter — 46 points de décalage vertical cumulé en bas de page.

Convention des coordonnées : `y` est mesuré depuis le HAUT de la page, comme
le donne l'extraction du PDF d'origine, et vaut le BAS de la case (`y1`).
`_ligne()` convertit en repère reportlab.

Dépendances : reportlab, pypdf.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from io import BytesIO
from typing import Any, Optional

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from config import BASE_DIR

_TEMPLATE_PATH = os.path.join(BASE_DIR, "data", "of_template.pdf")

# A4 — le format du modèle.
_PAGE_W = 595.28
_PAGE_H = 841.92

_REGULIER = "Helvetica"
_GRAS = "Helvetica-Bold"


# ── Formatage ────────────────────────────────────────────────────────────────

def _fmt(v: Any) -> str:
    """None → '', 400.0 → '400', le reste tel quel."""
    if v is None or v == "":
        return ""
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v)


def _fmt_date(v: Any) -> str:
    """« 2026-11-18 » → « 18/11/2026 ». Un OF saisi dans MySifa porte ses
    dates en ISO (champ date du navigateur) ; Access les envoie déjà au
    format français, qui passe tel quel."""
    brut = _fmt(v)
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", brut)
    return "%s/%s/%s" % (m.group(3), m.group(2), m.group(1)) if m else brut


def _fmt_qte(v: Any) -> str:
    """3775000 → '3 775 000'. L'atelier lit des quantités à six chiffres."""
    if v is None or v == "":
        return ""
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        return str(v)
    s = str(abs(n))
    groupes = []
    while len(s) > 3:
        groupes.append(s[-3:])
        s = s[:-3]
    groupes.append(s)
    return ("-" if n < 0 else "") + " ".join(reversed(groupes))


def _fmt_fr(v: Any) -> str:
    """Décimale à la française : 63.6 → « 63,6 », 470 → « 470 ».

    L'atelier lit des virgules. Un « 10.8 » au milieu d'un document où tout le
    reste est en virgule se lit comme une coquille, et sur une quantité au
    mille cela suffit à faire douter du chiffre.
    """
    return _fmt(v).replace(".", ",")


def _fmt_1(v: Any) -> str:
    """Une décimale, à la française, comme l'OF Access : qté au mille
    10,794 → « 10,8 », adhésif 63,617 kg → « 63,6 » (OF 9931861 et 9931953,
    comparés le 17/11/2026). Un entier reste entier (470 → « 470 »)."""
    if v is None or v == "":
        return ""
    try:
        n = round(float(v), 1)
    except (TypeError, ValueError):
        return str(v)
    return (str(int(n)) if n == int(n) else ("%.1f" % n)).replace(".", ",")


def _fmt_dec(v: Any) -> str:
    """165.0 → '165,00' pour les quantités de bobines, à la française."""
    if v is None or v == "":
        return ""
    try:
        return ("%.2f" % float(v)).replace(".", ",")
    except (TypeError, ValueError):
        return str(v)


# ── Champs du modèle ─────────────────────────────────────────────────────────
#
# (clé, x, y_bas, taille, gras, alignement, formateur)
# `x` est le bord GAUCHE, sauf en alignement "droite" où c'est le bord droit.

_CHAMPS = [
    # En-tête
    ("of_numero",              54.7,  33.5, 11,   True,  "g", _fmt),
    ("reference",              54.7,  43.9, 10,   True,  "g", _fmt),
    ("date_creation",         231.0,  30.0, 10,   True,  "g", _fmt_date),
    ("delai_client",          337.7,  29.8, 10,   True,  "g", _fmt_date),
    ("format",                289.0,  44.1, 10,   True,  "g", _fmt),
    # Matière et substitution
    ("matiere",                86.0,  60.9, 10,   True,  "g", _fmt),
    ("ref_matiere",            26.0,  89.8, 10,   True,  "g", _fmt),
    ("ref_matiere_fournisseur", 176.9, 89.8, 10,  True,  "g", _fmt),
    ("laize",                 281.4,  69.0, 12,   True,  "g", _fmt_fr),
    ("glassine",               71.3, 106.4, 10,   True,  "g", _fmt),
    # Adhésif — les deux valeurs sur aplat orange sont volontairement grandes
    # sur le document d'origine : c'est ce que l'opérateur lit de loin.
    ("ref_adhesif",            86.4, 129.0, 15,   True,  "g", _fmt),
    ("qte_adhesif_g",         162.7, 136.9, 22,   True,  "g", _fmt),
    ("qte_adhesif_kg",        307.3, 125.8, 10,   True,  "d", _fmt_1),
    ("adhesif_label",          58.4, 151.4, 10,   True,  "g", _fmt),
    ("qte_au_mille",          102.8, 168.6, 10,   True,  "g", _fmt_1),
    ("nb_levees",             301.3, 168.6, 10,   True,  "g", _fmt),
    # Quantités théoriques — colonne de droite, alignées sur le bord des cases
    ("qte_etiquettes",        477.1, 100.6, 10,   True,  "d", _fmt_qte),
    ("qte_bobines",           479.8, 117.1, 10,   True,  "d", _fmt_dec),
    ("metrage",               477.3, 156.9, 10,   True,  "d", _fmt_qte),
    # Machine et conditionnement
    ("machine",               431.6, 211.2, 10,   True,  "g", _fmt),
    ("bobinettes_completes",  485.9, 231.0, 10,   True,  "g", _fmt),
    ("conditionnement",       119.9, 245.1, 10,   True,  "g", _fmt),
    ("tolerance",             119.9, 263.1, 10,   True,  "g", _fmt),
    ("cartons_type",          120.0, 281.1, 10,   True,  "g", _fmt),
    ("cales_sachets",         119.9, 294.5, 10,   True,  "g", _fmt),
    # Commence juste après « Mandrins dia. » plutôt que dans la colonne des
    # valeurs : une désignation MyStock (« Tube carton Ø 40 mm, Lg. 1500 mm,
    # ép. 4 mm ») n'y tiendrait pas avant « Long. ».
    ("mandrins_dia",           84.0, 309.7, 10,   True,  "g", _fmt),
    ("mandrin_longueur",      253.4, 309.7, 10,   True,  "g", _fmt_fr),
    ("nb_cartons",            429.5, 247.9, 10,   True,  "g", _fmt),
    ("nb_mandrins",           429.0, 277.0, 10,   True,  "g", _fmt),
    ("nb_tubes",              429.0, 291.7, 10,   True,  "g", _fmt),
    # Une seule case pour le type de palette. Le modèle papier porte deux
    # cadres, « Europe » et « perdues » — mais le type est un CHOIX parmi des
    # références (« Pallet Europe », « Pallet Perdue », « Anti-bactérienne »),
    # pas deux compteurs. La désignation s'écrit donc à cheval sur les deux,
    # en 8 pt pour y tenir, et le nombre se pose à gauche des cadres.
    ("nb_palettes",           427.0, 324.5, 10,   True,  "d", _fmt),
    ("palette_type",          432.0, 324.5,  8,   True,  "g", _fmt),
    # Outil 1
    ("outil_1_forme",          58.0, 443.4, 10,   True,  "g", _fmt),
    ("outil_1_numero",        160.2, 442.3,  9,   True,  "g", _fmt),
    ("outil_1_angle",         218.3, 443.4, 10,   True,  "g", _fmt),
    ("outil_1_mag",           250.2, 443.4, 10,   True,  "g", _fmt),
    ("outil_1_cp",            298.9, 443.4, 10,   True,  "g", _fmt),
    ("outil_1_hauteur",       336.0, 443.4, 10,   True,  "g", _fmt_fr),
    ("outil_1_fournisseur",   521.4, 444.0, 10,   True,  "g", _fmt),
    # Outil 2
    ("outil_2_forme",          57.8, 480.2, 10,   True,  "g", _fmt),
    ("outil_2_numero",        160.1, 479.0,  9,   True,  "g", _fmt),
    ("outil_2_angle",         218.2, 480.0, 10,   True,  "g", _fmt),
    ("outil_2_mag",           250.1, 479.8, 10,   True,  "g", _fmt),
    ("outil_2_cp",            298.8, 480.1, 10,   True,  "g", _fmt),
    ("outil_2_hauteur",       335.9, 480.1, 10,   True,  "g", _fmt_fr),
    ("outil_2_fournisseur",   521.4, 480.7, 10,   True,  "g", _fmt),
    # Réglages plieuse
    ("plieuse_pignon",        179.4, 639.4, 10,   True,  "g", _fmt),
    ("nb_pouces",             505.4, 639.4, 10,   True,  "g", _fmt),
]

# Largeur disponible avant le libellé suivant du modèle, relevée sur
# data/of_template.pdf. Sans elle, un libellé long venu de MyStock (« Tube
# carton Ø 40 mm, Lg. 1500 mm, ép. 4 mm ») écrivait par-dessus « Long. » et sa
# valeur, une glassine par-dessus « Subst. ». Le texte se resserre jusqu'à
# 6 pt, puis se coupe avec « … » : l'OF reste lisible, la valeur complète
# reste dans MySifa.
_LARGEURS = {
    "of_numero":        124.0,   # « Date créa. » à x = 182
    "reference":        190.0,   # « Format » à x = 250
    "format":           185.0,   # cadre « Contrôlé » à x = 477
    "matiere":          158.0,   # « Laize » à x = 250
    "ref_matiere":      148.0,
    "glassine":         112.0,   # « Subst. » à x = 185
    "adhesif_label":    280.0,   # bord du bloc de gauche, x ≈ 340
    "conditionnement":  220.0,
    "tolerance":        220.0,
    "cartons_type":     220.0,
    "cales_sachets":    220.0,
    "mandrins_dia":     138.0,   # « Long. » à x = 224,8
    "palette_type":     104.0,   # bord droit du second cadre, x ≈ 538
}

# Zones de texte libre : (clé, x, y_bas de la première ligne, largeur, taille,
# interligne, nombre de lignes maximum).
_ZONES = [
    # Tout l'aplat jaune (x = 100 → 573) : une particularité longue (560
    # caractères pour 1341/0006) était coupée à 4 lignes.
    ("particularites", 100.3, 344.1, 468.0, 10, 12.4, 4),
    ("observations",    32.0, 692.0, 350.0,  9, 11.0, 9),
]

# Bloc « Texte pour étiquettes bobinettes », en bas à droite.
_BOBINETTES_X = 397.8
_BOBINETTES_Y = [778.6, 790.5, 802.3, 814.2]


# Largeur des petites cases à l'écran : celle du cadre du modèle. Sans elle, une
# case corrigée se colore par-dessus le libellé voisin.
_LARGEURS_ECRAN = {
    "date_creation": 54.0, "delai_client": 62.0, "laize": 54.0, "ref_adhesif": 50.0,
    "qte_adhesif_g": 44.0, "qte_adhesif_kg": 40.0, "qte_au_mille": 36.0, "nb_levees": 34.0,
    "qte_etiquettes": 48.0, "qte_bobines": 48.0, "metrage": 50.0, "machine": 120.0,
    "bobinettes_completes": 70.0, "mandrin_longueur": 60.0, "nb_cartons": 50.0,
    "nb_mandrins": 50.0, "nb_tubes": 50.0, "nb_palettes": 14.0,
}


_CADRES_PATH = os.path.join(BASE_DIR, "data", "of_modele_cadres.json")


@lru_cache(maxsize=1)
def _releve() -> dict:
    """Cadres et libellés du modèle, relevés par scripts/of_modele_ecran.py."""
    try:
        with open(_CADRES_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _cadres() -> tuple:
    return tuple(_releve().get("cadres") or ())


def _borner_par_libelles(gauche: float, droite: float, haut: float, bas: float,
                         ancre: float) -> tuple:
    """Une case ne recouvre aucun libellé imprimé de sa ligne : elle s'arrête
    au mot qui la précède et à celui qui la suit (« Qté totale … kg »)."""
    for m in _releve().get("mots") or ():
        if m["y1"] <= haut + 2 or m["y0"] >= bas - 2:
            continue
        if (m["x0"] + m["x1"]) / 2 < ancre:
            gauche = max(gauche, m["x1"] + 2)
        else:
            droite = min(droite, m["x0"] - 2)
    return gauche, droite


def _recouvre(a, b) -> float:
    """Part de la surface de `a` couverte par `b` ; boîtes (x0, y0, x1, y1)."""
    l = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    h = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    aire = max((a[2] - a[0]) * (a[3] - a[1]), 0.01)
    return l * h / aire


def _case_ecran(c) -> dict:
    """Une case de `_CHAMPS`, calée sur le cadre du modèle qui la contient."""
    cle, x, y, taille, _gras, align, _f = c
    ax, ay = (x - 3 if align == "d" else x + 3), y - taille * 0.4
    dedans = [k for k in _cadres()
              if k["x0"] - 0.5 <= ax <= k["x1"] + 0.5 and k["y0"] - 0.5 <= ay <= k["y1"] + 0.5
              and k["x1"] - k["x0"] <= 360 and k["y1"] - k["y0"] <= 45]
    h = taille * 1.55
    if dedans:
        # Un cadre tracé d'abord, puis une case blanche, puis un aplat : une case
        # blanche peut n'occuper qu'une partie du cadre (N° d'outil).
        rang = {"cadre": 0, "blanc": 1, "aplat": 2}
        k = min(dedans, key=lambda k: (not k.get("ferme"), rang.get(k["type"], 3),
                                       (k["x1"] - k["x0"]) * (k["y1"] - k["y0"])))
        # Libellé dans le cadre (« Conditionnement ») : la case part de la valeur.
        # Un cadre vide se prend en entier, même si l'impression y décale le texte.
        gauche = k["x0"] + 1.5 if (align == "d" or k.get("vide") or k["x0"] >= x - 8) else x - 1
        droite = k["x1"] - 1.5
        if k["y1"] - k["y0"] <= taille * 2.4:
            haut, h = k["y0"] + 1.5, k["y1"] - k["y0"] - 3
        else:
            haut = y - h + 2
        taille_ecran = min(taille, h / 1.25)
        gauche, droite = _borner_par_libelles(gauche, droite, haut, haut + h,
                                              x - 2 if align == "d" else x + 2)
        return {"cle": cle, "x": round(gauche, 1), "y": round(haut, 1), "l": round(droite - gauche, 1),
                "h": round(h, 1), "taille": round(taille_ecran, 1), "align": align, "cadre": True}

    def gauche_de(o):
        return o[1] - _LARGEURS_ECRAN.get(o[0], 72.0) if o[5] == "d" else o[1]

    if align == "d":
        l = _LARGEURS_ECRAN.get(cle, 72.0)
    else:
        suivantes = [gauche_de(o) for o in _CHAMPS
                     if o[0] != cle and abs(o[2] - y) < 9 and gauche_de(o) > x]
        borne = min(suivantes) - 3 if suivantes else 572.0
        l = min(borne - x, _LARGEURS_ECRAN.get(cle, _LARGEURS.get(cle, 150.0)))
    gauche, droite = _borner_par_libelles(gauche_de(c), gauche_de(c) + l, y - h + 2, y + 2,
                                          x - 2 if align == "d" else x + 2)
    return {"cle": cle, "x": round(gauche, 1), "y": round(y - h + 2, 1),
            "l": round(max(droite - gauche, 8.0), 1), "h": round(h, 1), "taille": taille,
            "align": align, "cadre": False}


@lru_cache(maxsize=1)
def cases_du_modele() -> dict:
    """Où poser les cases modifiables à l'écran : les positions de l'impression.

    L'écran et le PDF lisent les mêmes `_CHAMPS` : une case déplacée ici bouge
    aux deux endroits. Chaque case se cale sur le cadre du modèle qui la
    contient. Un cadre vide qu'aucun champ n'occupe devient une case LIBRE :
    l'ADV peut y écrire, et le texte s'imprime à cet endroit.
    """
    cases = [_case_ecran(c) for c in _CHAMPS]
    zones = [{"cle": cle, "x": x, "y": round(y - taille * 1.2, 1), "l": largeur,
              "h": round(interligne * maxi + 3, 1), "taille": taille}
             for cle, x, y, largeur, taille, interligne, maxi in _ZONES]
    occupe = [(c["x"], c["y"], c["x"] + c["l"], c["y"] + c["h"]) for c in cases + zones]
    occupe.append((_BOBINETTES_X - 4, _BOBINETTES_Y[0] - 14, 572.0, _BOBINETTES_Y[-1] + 4))
    libres = []
    # Du plus petit au plus grand : un grand cadre qui en englobe trois petits
    # (ligne Sheeter) ne doit pas les masquer.
    for k in sorted(_cadres(), key=lambda k: (k["x1"] - k["x0"]) * (k["y1"] - k["y0"])):
        if not k.get("vide") or not k.get("ferme") or k.get("type") == "aplat":
            continue
        box = (k["x0"] + 1.5, k["y0"] + 1.5, k["x1"] - 1.5, k["y1"] - 1.5)
        # Les cases à cocher (« Terminé », « Galets de pression ») en font partie.
        if box[2] - box[0] < 4 or box[3] - box[1] < 4:
            continue
        if any(_recouvre(box, o) > 0.25 for o in occupe):
            continue
        if sum(_recouvre(box, (l["x"], l["y"], l["x"] + l["l"], l["y"] + l["h"])) for l in libres) > 0.4:
            continue
        h = box[3] - box[1]
        libres.append({"cle": "c%d_%d" % (round(k["x0"]), round(k["y0"])), "x": round(box[0], 1),
                       "y": round(box[1], 1), "l": round(box[2] - box[0], 1), "h": round(h, 1),
                       "taille": round(max(6.0, min(10.0, h / 1.3)), 1)})
    libres.sort(key=lambda l: (l["y"], l["x"]))
    return {"page": {"l": _PAGE_W, "h": _PAGE_H}, "cases": cases, "zones": zones, "libres": libres,
            "bobinettes": {"x": _BOBINETTES_X, "y": _BOBINETTES_Y, "taille": 10}}


def lire_cases_libres(brut: Any) -> dict:
    """{clé: texte} des cases libres, clés du modèle seulement, 60 caractères."""
    if isinstance(brut, str):
        try:
            brut = json.loads(brut)
        except ValueError:
            return {}
    if not isinstance(brut, dict):
        return {}
    connues = {l["cle"] for l in cases_du_modele()["libres"]}
    return {str(k): str(v).strip()[:60] for k, v in brut.items()
            if str(k) in connues and v is not None and str(v).strip()}


def lignes_bobinettes(d: dict) -> list:
    """Les lignes de bobinettes de l'OF, telles qu'elles seront imprimées."""
    return _lignes_bobinettes(dict(d or {}))


def _lignes_bobinettes(d: dict) -> list:
    """Les quatre lignes de l'étiquette de bobinette.

    Elles se déduisent de l'OF — c'est un rappel, pas une saisie de plus. Un
    `texte_bobinettes` explicite prend le pas : l'ADV doit pouvoir écrire autre
    chose sans que le code lui redemande de le justifier.
    """
    brut = (d.get("texte_bobinettes") or "").strip()
    if brut:
        return brut.splitlines()[:4]

    # La date de l'OF (sa création), pas le délai client : c'est elle que
    # porte l'OF Access 9931953 (« 28/05/2026 », délai le 18/06).
    date = _fmt_date(d.get("date_creation")) or _fmt_date(d.get("delai_client"))
    adhesif = (d.get("adhesif_label") or "").replace("Adhésif", "").strip()
    # « Permanent 2028Y - 1 » → « Permanent » : l'étiquette ne porte que la
    # nature de la colle et celle du support.
    adhesif = adhesif.split()[0] if adhesif else ""
    matiere = (d.get("matiere") or "").strip().title()
    ref = (d.get("reference") or "").split(" - ")[0].strip()
    return [
        ("Date : " + date) if date else "",
        ("OF : " + _fmt(d.get("of_numero"))) if d.get("of_numero") else "",
        " / ".join(x for x in (adhesif, matiere) if x),
        (ref.replace("-", "/") + "FS") if ref else "",
    ]


def _couper(texte: str, largeur: float, police: str, taille: float) -> list:
    """Découpe un texte en lignes qui tiennent dans `largeur`."""
    lignes = []
    for para in str(texte).splitlines():
        mots, courante = para.split(), ""
        for mot in mots:
            essai = (courante + " " + mot).strip()
            if courante and stringWidth(essai, police, taille) > largeur:
                lignes.append(courante)
                courante = mot
            else:
                courante = essai
        lignes.append(courante)
    return lignes


def _ajuster(texte: str, police: str, taille: float, largeur: float):
    """(texte, taille) qui tiennent dans `largeur` : on resserre jusqu'à
    6 pt, puis on coupe en finissant par « … »."""
    t = float(taille)
    while stringWidth(texte, police, t) > largeur and t > 6.0:
        t -= 0.5
    if stringWidth(texte, police, t) <= largeur:
        return texte, t
    while texte and stringWidth(texte + "…", police, t) > largeur:
        texte = texte[:-1]
    return texte.rstrip() + "…", t


def _terminer_le_flux(page) -> None:
    """Garantit que le flux du modèle se termine par un séparateur.

    `merge_page` colle la surcouche à la suite du flux existant. Le modèle
    d'OF finit par « … W* n Q » sans retour à la ligne : collé au « Q » que
    pypdf ouvre, cela donne l'opérateur « QQ », que ne connaît aucun lecteur —
    et la page s'affiche alors SANS aucune des valeurs, sans erreur visible
    côté serveur. Un octet suffit à l'éviter.
    """
    contenu = page.get_contents()
    if contenu is None:
        return
    donnees = contenu.get_data()
    if donnees.endswith((b"\n", b"\r", b" ", b"\t")):
        return
    flux = DecodedStreamObject()
    flux.set_data(donnees + b"\n")
    page.replace_contents(flux)


def generate_of_pdf(of_data: dict, template_path: Optional[str] = None) -> bytes:
    """Remplit le modèle vierge avec les colonnes de `of_imports`.

    Une colonne absente du dict laisse simplement sa case vide : c'est ce qui
    permet d'imprimer un OF en cours de saisie sans casser la mise en page.
    """
    tpl = template_path or _TEMPLATE_PATH
    if not os.path.isfile(tpl):
        raise FileNotFoundError(
            "Modèle d'OF introuvable : %s. Déposez data/of_template.pdf "
            "sur le serveur." % tpl
        )

    d = dict(of_data or {})
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(_PAGE_W, _PAGE_H))
    c.setFillColorRGB(0, 0, 0)

    def _poser(x, y_bas, texte, taille=10, gras=True, align="g", largeur=None):
        if texte in (None, ""):
            return
        police = _GRAS if gras else _REGULIER
        if largeur:
            texte, taille = _ajuster(texte, police, taille, largeur)
        # y1 est le bas de la case dans le repère du PDF d'origine ; la ligne
        # de base remonte de la descendante de la police.
        base = _PAGE_H - y_bas + 0.21 * taille
        c.setFont(police, taille)
        if align == "d":
            c.drawRightString(x, base, texte)
        else:
            c.drawString(x, base, texte)

    for cle, x, y, taille, gras, align, fmt in _CHAMPS:
        _poser(x, y, fmt(d.get(cle)), taille, gras, align, _LARGEURS.get(cle))

    for cle, x, y, largeur, taille, interligne, maxi in _ZONES:
        valeur = d.get(cle)
        if not valeur:
            continue
        # Le texte se resserre jusqu'à 6 pt pour tenir dans la hauteur de la
        # zone ; au-delà seulement, il est coupé, et la coupure se voit (« … »).
        bas = y + (maxi - 1) * interligne
        t_z, lignes = float(taille), []
        while True:
            il = interligne * t_z / taille
            places = 1 + int((bas - y) // il)
            lignes = _couper(valeur, largeur, _GRAS, t_z)
            if len(lignes) <= places or t_z <= 6.0:
                break
            t_z -= 0.5
        if len(lignes) > places:
            lignes = lignes[:places]
            lignes[-1] = lignes[-1].rstrip() + " …"
        for i, ligne in enumerate(lignes):
            _poser(x, y + i * il, ligne, t_z, True, "g")

    for y, ligne in zip(_BOBINETTES_Y, _lignes_bobinettes(d)):
        _poser(_BOBINETTES_X, y, ligne, 10, True, "g")

    # Cases libres : un cadre du modèle qu'aucun champ n'occupe, rempli à la main.
    libres = lire_cases_libres(d.get("cases_libres"))
    if libres:
        for l in cases_du_modele()["libres"]:
            texte = libres.get(l["cle"])
            if texte:
                _poser(l["x"] + 1, l["y"] + l["h"] - 1, texte, l["taille"], True, "g", l["l"] - 2)

    c.save()
    buf.seek(0)

    modele = PdfReader(tpl)
    surcouche = PdfReader(buf)

    # La page est d'abord attachée au writer, PUIS normalisée et fusionnée :
    # pypdf refuse de réécrire le flux d'une page qui n'appartient encore à
    # aucun document, et le fait savoir par un DeprecationWarning qui annonce
    # une suppression pure et simple.
    sortie = PdfWriter()
    sortie.add_page(modele.pages[0])
    page = sortie.pages[0]
    _terminer_le_flux(page)
    page.merge_page(surcouche.pages[0])

    out = BytesIO()
    sortie.write(out)
    return out.getvalue()
