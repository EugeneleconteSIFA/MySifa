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

import os
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
    ("date_creation",         231.0,  30.0, 10,   True,  "g", _fmt),
    ("delai_client",          337.7,  29.8, 10,   True,  "g", _fmt),
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
    ("qte_adhesif_kg",        307.3, 125.8, 10,   True,  "d", _fmt_fr),
    ("adhesif_label",          58.4, 151.4, 10,   True,  "g", _fmt),
    ("qte_au_mille",          102.8, 168.6, 10,   True,  "g", _fmt_fr),
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
    ("mandrins_dia",          119.9, 309.7, 10,   True,  "g", _fmt),
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

# Zones de texte libre : (clé, x, y_bas de la première ligne, largeur, taille,
# interligne, nombre de lignes maximum).
_ZONES = [
    ("particularites", 100.3, 344.1, 420.0, 10, 12.4, 4),
    ("observations",    32.0, 692.0, 350.0,  9, 11.0, 9),
]

# Bloc « Texte pour étiquettes bobinettes », en bas à droite.
_BOBINETTES_X = 397.8
_BOBINETTES_Y = [778.6, 790.5, 802.3, 814.2]


def _lignes_bobinettes(d: dict) -> list:
    """Les quatre lignes de l'étiquette de bobinette.

    Elles se déduisent de l'OF — c'est un rappel, pas une saisie de plus. Un
    `texte_bobinettes` explicite prend le pas : l'ADV doit pouvoir écrire autre
    chose sans que le code lui redemande de le justifier.
    """
    brut = (d.get("texte_bobinettes") or "").strip()
    if brut:
        return brut.splitlines()[:4]

    date = _fmt(d.get("delai_client")) or _fmt(d.get("date_creation"))
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

    def _poser(x, y_bas, texte, taille=10, gras=True, align="g"):
        if texte in (None, ""):
            return
        police = _GRAS if gras else _REGULIER
        # y1 est le bas de la case dans le repère du PDF d'origine ; la ligne
        # de base remonte de la descendante de la police.
        base = _PAGE_H - y_bas + 0.21 * taille
        c.setFont(police, taille)
        if align == "d":
            c.drawRightString(x, base, texte)
        else:
            c.drawString(x, base, texte)

    for cle, x, y, taille, gras, align, fmt in _CHAMPS:
        _poser(x, y, fmt(d.get(cle)), taille, gras, align)

    for cle, x, y, largeur, taille, interligne, maxi in _ZONES:
        valeur = d.get(cle)
        if not valeur:
            continue
        for i, ligne in enumerate(_couper(valeur, largeur, _GRAS, taille)[:maxi]):
            _poser(x, y + i * interligne, ligne, taille, True, "g")

    for y, ligne in zip(_BOBINETTES_Y, _lignes_bobinettes(d)):
        _poser(_BOBINETTES_X, y, ligne, 10, True, "g")

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
