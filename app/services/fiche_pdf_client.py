"""
Générateur PDF — Fiche technique CLIENT SIFA (bilingue FR / EN)

Version simplifiée à destination des clients, contenant uniquement les infos
essentielles (format, frontal, adhésif, grammage adhésif, nombre d'impressions,
conditionnement) avec libellés bilingues et valeurs traduites (FR au-dessus,
EN en italique dessous).

En-tête : logo SIFA + coordonnées siège (adresse, téléphone, email).
Pied de page : mentions de confidentialité + date d'édition.
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from io import BytesIO
from typing import Any, Optional
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


# ── Coordonnées SIFA (siège social) ─────────────────────────────────
SIFA_NAME    = "SIFA"
SIFA_ADDRESS = "45 rue Rollin — 59100 Roubaix — France"
SIFA_PHONE   = "+33 (0)3 20 69 01 01"
SIFA_EMAIL   = "commandes@sifa.pro"

# ── Couleurs ─────────────────────────────────────────────────────────
_YELLOW     = colors.HexColor("#FFD100")   # jaune SIFA
_BLACK      = colors.black
_WHITE      = colors.white
_DARK       = colors.HexColor("#1a1a1a")
_MUTED      = colors.HexColor("#666666")
_LIGHT_GRAY = colors.HexColor("#f5f5f5")
_BORDER     = colors.HexColor("#d1d1d1")

W, H = A4  # 595.28 x 841.89 pt

_PARIS = ZoneInfo("Europe/Paris")


# ── Traduction FR → EN pour les valeurs libres ──────────────────────
# Dictionnaire de tokens courants dans les fiches SIFA. Appliqué par
# substitution mot-entier (word boundary) sur la valeur FR pour produire
# une version EN raisonnablement lisible côté client anglophone.
_FR_TO_EN_WORDS = [
    # multi-mots d'abord (l'ordre compte : plus long → plus court)
    ("étiq./bobine",           "labels/roll"),
    ("étiq/bobine",            "labels/roll"),
    ("étiquettes / bobine",    "labels / roll"),
    ("étiquettes/bobine",      "labels/roll"),
    ("mandrin de",             "core of"),
    ("mandrin ø",              "core Ø"),
    ("mandrin diamètre",       "core diameter"),
    ("bobines / carton",       "rolls / box"),
    ("bobines/carton",         "rolls/box"),
    # mots simples
    ("étiquettes",             "labels"),
    ("étiquette",              "label"),
    ("bobines",                "rolls"),
    ("Bobines",                "Rolls"),
    ("bobine",                 "roll"),
    ("Bobine",                 "Roll"),
    ("cartons",                "boxes"),
    ("Cartons",                "Boxes"),
    ("carton",                 "box"),
    ("Carton",                 "Box"),
    ("palettes",               "pallets"),
    ("Palettes",               "Pallets"),
    ("palette",                "pallet"),
    ("Palette",                "Pallet"),
    ("mandrin",                "core"),
    ("Mandrin",                "Core"),
    ("recto",                  "front"),
    ("Recto",                  "Front"),
    ("verso",                  "back"),
    ("Verso",                  "Back"),
    ("blanc",                  "white"),
    ("Blanc",                  "White"),
    ("noir",                   "black"),
    ("Noir",                   "Black"),
    ("brillant",               "gloss"),
    ("Brillant",               "Gloss"),
    ("brillante",              "gloss"),
    ("mat",                    "matt"),
    ("Mat",                    "Matt"),
    ("transparent",            "clear"),
    ("Transparent",            "Clear"),
    ("permanent",              "permanent"),
    ("Permanent",              "Permanent"),
    ("amovible",               "removable"),
    ("Amovible",               "Removable"),
    ("repositionnable",        "repositionable"),
    ("couché",                 "coated"),
    ("non couché",             "uncoated"),
    ("thermique",              "thermal"),
    ("Thermique",              "Thermal"),
    ("laize",                  "width"),
    ("Laize",                  "Width"),
    ("longueur",               "length"),
    ("Longueur",               "Length"),
    ("épaisseur",              "thickness"),
    ("Épaisseur",              "Thickness"),
    ("avec",                   "with"),
    ("Avec",                   "With"),
    ("sans",                   "without"),
    ("Sans",                   "Without"),
    ("de la",                  "of the"),
    ("de l'",                  "of the "),
    ("des",                    "of"),
    ("du",                     "of the"),
    ("de",                     "of"),
    ("et",                     "and"),
    ("par",                    "per"),
    ("pour",                   "for"),
    ("couleurs",               "colours"),
    ("couleur",                "colour"),
    ("Couleurs",               "Colours"),
    ("Couleur",                "Colour"),
]


def _v(val: Any) -> str:
    """None/'' → '—', sinon str(val)."""
    if val is None:
        return "—"
    s = str(val).strip()
    return s if s else "—"


def _sentence_case(val: str) -> str:
    """
    Applique la casse « phrase » (première lettre en majuscule, reste en
    minuscules). '—' est renvoyé tel quel. Les caractères non-lettres et
    les accents sont préservés.
    """
    if val is None or val == "—":
        return "—"
    s = str(val).strip()
    if not s:
        return "—"
    return s[0].upper() + s[1:].lower()


# ── Dictionnaire des types d'adhésif ────────────────────────────────
# L'utilisateur veut masquer les codes techniques (ex. « Permanent 2028Y »
# → « Permanent »). On matche le libellé brut sur une liste de motifs
# regex et on retourne l'étiquette canonique (FR, EN).
_ADHESIF_TYPES = [
    # (regex insensible à la casse, label FR, label EN)
    (r"cong[eé]l|surgel|deep\s*freeze|freezer|frozen",  "Congélation",       "Freezer"),
    (r"r[eé]frig[eé]r|cold|chill",                       "Réfrigération",     "Chilled"),
    (r"pneu\b|tire\b|tyre\b",                            "Pneu",              "Tire"),
    (r"enlevable|amovible|removable|peelable",           "Enlevable",         "Removable"),
    (r"repositionnable|repositionable",                  "Repositionnable",   "Repositionable"),
    (r"haute\s*(?:temp|adh[eé]sion)|hot\s*melt|forte\s*adh[eé]sion|high[- ]?tack",
                                                          "Haute adhésion",    "High-tack"),
    (r"basse\s*temp|low[- ]?temp",                       "Basse température", "Low-temperature"),
    (r"agroalimentaire|food[- ]?grade|food\s*contact",   "Agroalimentaire",   "Food-grade"),
    (r"pharma",                                          "Pharmaceutique",    "Pharmaceutical"),
    (r"marine|salt\s*water|hydro",                       "Marine",            "Marine"),
    (r"transparent|clear",                               "Transparent",       "Clear"),
    # Permanent en dernier car c'est un mot très commun qu'on veut matcher
    # uniquement si aucun type plus spécifique n'a été détecté.
    (r"permanent",                                       "Permanent",         "Permanent"),
]


# ── Dictionnaire des types de glassine ──────────────────────────────
# Réponse « par défaut » attendue : « Jaune Siliconnée » (la très grande
# majorité des fiches SIFA). Les autres cas sont là pour ne pas rendre
# une valeur brute exotique côté client.
_GLASSINE_TYPES = [
    # (regex insensible à la casse, label FR, label EN)
    (r"jaun|yellow",                                     "Jaune Siliconnée",   "Yellow silicone glassine"),
    (r"blanc|white",                                     "Blanche Siliconnée", "White silicone glassine"),
    (r"kraft|brun|brown",                                "Kraft Siliconnée",   "Brown kraft silicone glassine"),
    (r"transparent|clear|pet\b|film",                    "Transparente (PET)", "Clear (PET film)"),
    (r"bopp|pp\s*film",                                  "BOPP",               "BOPP film"),
    (r"silicon|silicone",                                "Jaune Siliconnée",   "Yellow silicone glassine"),
]


def _classify_glassine(raw: str) -> tuple[str, str]:
    """
    Extrait le type canonique d'une glassine.

    Ex. 'Glassine jaune 60g' → ('Jaune Siliconnée',   'Yellow silicone glassine')
        'GLASSINE BLANCHE'   → ('Blanche Siliconnée', 'White siliconised')
        'Kraft 65g'          → ('Kraft Siliconnée',   'Brown kraft siliconised')

    Si rien ne matche mais que le champ est renseigné, on renvoie par
    défaut « Jaune Siliconnée » (c'est le liner le plus courant SIFA).
    Si le champ est vide, on renvoie '—' / '—'.
    """
    if not raw or raw == "—":
        return ("—", "—")
    s = str(raw).strip()
    for pattern, fr, en in _GLASSINE_TYPES:
        if re.search(pattern, s, flags=re.IGNORECASE):
            return (fr, en)
    # Défaut SIFA : jaune siliconnée (cas le plus fréquent)
    return ("Jaune Siliconnée", "Yellow silicone glassine")


def _classify_adhesif(raw: str) -> tuple[str, str]:
    """
    Extrait le type canonique d'un libellé adhésif brut.

    Ex. 'Permanent 2028Y'      → ('Permanent',   'Permanent')
        'Enlevable RP51'       → ('Enlevable',   'Removable')
        'Congélation D2050'    → ('Congélation', 'Freezer')
        'Pneu HD52'            → ('Pneu',        'Tire')

    Si aucun motif ne matche, on renvoie le premier mot du libellé
    (avec sentence case) comme approximation, en FR/EN identiques.
    """
    if not raw or raw == "—":
        return ("—", "—")
    s = str(raw).strip()
    for pattern, fr, en in _ADHESIF_TYPES:
        if re.search(pattern, s, flags=re.IGNORECASE):
            return (fr, en)
    # Fallback : premier mot du libellé
    first = re.split(r"\s+", s, maxsplit=1)[0]
    return (_sentence_case(first), _sentence_case(first))


def _clean_reference(ref: Any) -> str:
    """
    Tronque la référence produit après le premier ' - ' (ou variante).
    Ex. '748/0016 - COHESIO 1' → '748/0016'.
    """
    if ref is None:
        return "—"
    s = str(ref).strip()
    if not s:
        return "—"
    for sep in (" - ", " — ", " – "):
        if sep in s:
            s = s.split(sep, 1)[0].strip()
            break
    return s or "—"


def _translate_fr_to_en(value: str) -> str:
    """
    Traduit une valeur FR en EN par substitution de tokens connus.
    Renvoie la chaîne EN (peut rester identique si aucun mot FR n'est reconnu).
    """
    if not value or value == "—":
        return value
    s = str(value)
    for fr, en in _FR_TO_EN_WORDS:
        # \b ne fonctionne pas bien avec accents/slash — on utilise une regex
        # qui borne par non-lettre pour respecter les mots entiers.
        pattern = r"(?<![A-Za-zÀ-ÿ])" + re.escape(fr) + r"(?![A-Za-zÀ-ÿ])"
        s = re.sub(pattern, en, s)
    return s


def _get_adhesif_raw(fiche: dict) -> str:
    """Adhésif brut : préfère 'adhesif' puis 'adhesif_label' puis 'ref_adhesif'."""
    for k in ("adhesif", "adhesif_label", "ref_adhesif"):
        v = fiche.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return "—"


def _fmt_glassine(fiche: dict) -> str:
    """Glassine : renvoie le libellé du champ 'glassine' tel quel."""
    v = fiche.get("glassine")
    if v is not None and str(v).strip():
        return str(v).strip()
    return "—"


def _fmt_nb_impressions(fiche: dict) -> str:
    """Nombre d'impressions = nb_couleurs (recto/verso indiqué à part)."""
    nb = fiche.get("nb_couleurs")
    if nb is None or str(nb).strip() == "":
        return "—"
    txt = str(nb).strip()
    recto = fiche.get("recto")
    verso = fiche.get("verso")
    extras = []
    if recto and str(recto).strip():
        extras.append(f"recto {recto}")
    if verso and str(verso).strip():
        extras.append(f"verso {verso}")
    if extras:
        txt += f" ({', '.join(extras)})"
    return txt


def _fmt_conditionnement(fiche: dict) -> str:
    """Conditionnement : combine conditionnement + nb par bobine si dispo."""
    parts = []
    cond = fiche.get("conditionnement")
    if cond and str(cond).strip():
        parts.append(str(cond).strip())
    nb_et = fiche.get("nb_etiq_bobin")
    if nb_et and str(nb_et).strip():
        parts.append(f"{nb_et} étiq./bobine")
    return " — ".join(parts) if parts else "—"


def _draw_logo(c: canvas.Canvas, x: float, y_top: float, max_h: float) -> float:
    """Dessine le logo SIFA. Retourne la largeur consommée."""
    candidates = [
        os.path.join(os.getcwd(), "static", "sifa_logo.png"),
        os.path.join(os.path.dirname(__file__), "..", "..", "static", "sifa_logo.png"),
        "/home/sifa/production-saas/static/sifa_logo.png",
        "/home/sifa/production-saas-v1/static/sifa_logo.png",
    ]
    logo_path = next((p for p in candidates if os.path.isfile(p)), None)
    if not logo_path:
        c.setFillColor(_BLACK)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(x, y_top - 16, "SIFA")
        return 45 * mm
    try:
        from reportlab.lib.utils import ImageReader
        img = ImageReader(logo_path)
        iw, ih = img.getSize()
        target_h = max_h
        target_w = iw * target_h / ih
        max_w = 55 * mm
        if target_w > max_w:
            target_w = max_w
            target_h = ih * target_w / iw
        c.drawImage(logo_path, x, y_top - target_h, width=target_w, height=target_h,
                    mask="auto", preserveAspectRatio=True)
        return target_w
    except Exception:
        c.setFillColor(_BLACK)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(x, y_top - 16, "SIFA")
        return 45 * mm


def _draw_header(c: canvas.Canvas, ml: float, mr: float) -> float:
    """Bandeau supérieur : logo + coordonnées à droite. Retourne le Y en bas du bandeau."""
    y_top = H - 12 * mm
    logo_h = 18 * mm
    _draw_logo(c, ml, y_top, logo_h)

    x_right = W - mr
    c.setFillColor(_DARK)
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(x_right, y_top - 4, SIFA_NAME)
    c.setFont("Helvetica", 8)
    c.setFillColor(_MUTED)
    c.drawRightString(x_right, y_top - 14, SIFA_ADDRESS)
    c.drawRightString(x_right, y_top - 24, f"Tél. : {SIFA_PHONE}")
    c.drawRightString(x_right, y_top - 34, SIFA_EMAIL)

    y_line = y_top - max(logo_h, 34) - 4 * mm
    c.setFillColor(_YELLOW)
    c.rect(ml, y_line, W - ml - mr, 1.5 * mm, fill=1, stroke=0)
    c.setFillColor(_BLACK)
    return y_line - 2 * mm


def _draw_bilingual_title(c: canvas.Canvas, y: float) -> float:
    """Titre bilingue centré."""
    c.setFillColor(_BLACK)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(W / 2, y - 12, "FICHE TECHNIQUE CLIENT")
    c.setFillColor(_MUTED)
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(W / 2, y - 26, "Customer technical data sheet")
    c.setFillColor(_BLACK)
    return y - 34


def _draw_ref_block(c: canvas.Canvas, ml: float, mr: float, y: float, fiche: dict) -> float:
    """Bloc référence produit (encadré, mise en avant). Référence tronquée."""
    inner_w = W - ml - mr
    block_h = 14 * mm
    y_bottom = y - block_h

    c.setStrokeColor(_BLACK)
    c.setLineWidth(0.6)
    c.setFillColor(_LIGHT_GRAY)
    c.rect(ml, y_bottom, inner_w, block_h, fill=1, stroke=1)
    c.setFillColor(_BLACK)

    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(_MUTED)
    c.drawString(ml + 4 * mm, y - 5 * mm, "Référence produit  /  Product reference")
    c.setFillColor(_BLACK)
    c.setFont("Helvetica-Bold", 14)
    ref = _clean_reference(fiche.get("reference"))
    c.drawString(ml + 4 * mm, y - 11 * mm, ref)

    client = fiche.get("client")
    if client and str(client).strip():
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(_MUTED)
        c.drawRightString(W - mr - 4 * mm, y - 5 * mm, "Client  /  Customer")
        c.setFillColor(_BLACK)
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(W - mr - 4 * mm, y - 11 * mm, str(client).strip())

    return y_bottom - 6 * mm


def _draw_bilingual_row(
    c: canvas.Canvas, ml: float, mr: float, y: float,
    label_fr: str, label_en: str,
    value_fr: str, value_en: str,
    striped: bool = False,
) -> float:
    """
    Ligne bilingue :
      [ Label FR (titre)    |  Valeur FR (titre)    ]
      [ Label EN (sous-tit.)|  Valeur EN (sous-tit.)]

    Retourne le nouveau y (bas de la ligne).
    """
    inner_w = W - ml - mr
    row_h   = 14 * mm  # 2 lignes de texte + padding
    col_lbl = inner_w * 0.36
    col_val = inner_w - col_lbl

    y_bottom = y - row_h

    # Fond zébré
    if striped:
        c.setFillColor(_LIGHT_GRAY)
        c.rect(ml, y_bottom, inner_w, row_h, fill=1, stroke=0)

    # Séparateur vertical
    c.setStrokeColor(_BORDER)
    c.setLineWidth(0.3)
    c.line(ml + col_lbl, y_bottom, ml + col_lbl, y)

    # Bord inférieur
    c.setStrokeColor(_BORDER)
    c.setLineWidth(0.4)
    c.line(ml, y_bottom, ml + inner_w, y_bottom)

    # ── Colonne label ──
    y_line1 = y - 5.5 * mm       # ligne FR (titre)
    y_line2 = y - 10.5 * mm      # ligne EN (sous-titre)

    c.setFillColor(_DARK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(ml + 3 * mm, y_line1, label_fr)
    c.setFillColor(_MUTED)
    c.setFont("Helvetica-Oblique", 8.5)
    c.drawString(ml + 3 * mm, y_line2, label_en)

    # ── Colonne valeur ──
    x_val = ml + col_lbl + 3 * mm
    max_val_w = col_val - 6 * mm

    def _fit_font(txt: str, base_size: float, bold: bool = True) -> float:
        font = "Helvetica-Bold" if bold else "Helvetica-Oblique"
        for s in (base_size, base_size - 0.5, base_size - 1, base_size - 1.5, base_size - 2, base_size - 2.5, base_size - 3):
            if c.stringWidth(txt, font, s) <= max_val_w:
                return s
        return base_size - 3

    # Valeur FR (bold noir)
    size_fr = _fit_font(value_fr, 11.5, bold=True)
    c.setFillColor(_BLACK)
    c.setFont("Helvetica-Bold", size_fr)
    c.drawString(x_val, y_line1, value_fr)

    # Valeur EN (italique gris) — n'affiche que si différente de la FR
    if value_en and value_en != value_fr:
        size_en = _fit_font(value_en, 9, bold=False)
        c.setFillColor(_MUTED)
        c.setFont("Helvetica-Oblique", size_en)
        c.drawString(x_val, y_line2, value_en)

    return y_bottom


def _draw_footer(c: canvas.Canvas, ml: float, mr: float) -> None:
    """Pied de page : mentions bilingues + date d'édition (gauche)."""
    inner_w = W - ml - mr

    # Ligne jaune
    y = 22 * mm
    c.setFillColor(_YELLOW)
    c.rect(ml, y, inner_w, 0.8 * mm, fill=1, stroke=0)
    c.setFillColor(_BLACK)

    # Mentions confidentialité (bilingues, petit gris)
    y -= 3 * mm
    style = ParagraphStyle(
        "mentions", fontName="Helvetica-Oblique", fontSize=6.5, leading=8,
        textColor=_MUTED, alignment=TA_CENTER,
    )
    txt_fr = ("Document non contractuel — Les spécifications techniques peuvent évoluer sans préavis. "
              "Diffusion réservée au destinataire. © SIFA — tous droits réservés.")
    txt_en = ("Non-contractual document — Technical specifications may change without notice. "
              "For addressee use only. © SIFA — all rights reserved.")
    p_fr = Paragraph(txt_fr, style)
    p_en = Paragraph(txt_en, style)
    _, h1 = p_fr.wrap(inner_w, 20)
    p_fr.drawOn(c, ml, y - h1)
    y -= h1 + 1
    _, h2 = p_en.wrap(inner_w, 20)
    p_en.drawOn(c, ml, y - h2)

    # Date d'édition (gauche uniquement)
    now_paris = datetime.now(_PARIS)
    date_str = now_paris.strftime("%d/%m/%Y %H:%M")
    c.setFont("Helvetica", 7)
    c.setFillColor(_MUTED)
    c.drawString(ml, 8 * mm,
                 f"Édité le / Issued on : {date_str} (Europe/Paris)")
    c.setFillColor(_BLACK)


def generate_fiche_client_pdf(fiche: dict) -> bytes:
    """
    Génère le PDF client (bilingue FR/EN) d'une fiche technique.
    Retourne les bytes du PDF.
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Fiche technique client — {_clean_reference(fiche.get('reference'))}")
    c.setAuthor("SIFA")

    ml = 15 * mm
    mr = 15 * mm

    # 1) Bandeau (logo + coordonnées)
    y = _draw_header(c, ml, mr)

    # 2) Titre bilingue
    y = _draw_bilingual_title(c, y)

    # 3) Bloc référence (tronquée avant ' - ')
    y = _draw_ref_block(c, ml, mr, y - 4 * mm, fiche)

    # 4) Les 6 caractéristiques essentielles — label FR/EN + valeur FR/EN
    #    (valeur EN calculée par traduction lexicale, sauf adhésif qui a
    #    son propre classifieur bilingue).
    format_fr    = _sentence_case(_v(fiche.get("format")))
    frontal_fr   = _sentence_case(_v(fiche.get("support") or fiche.get("matiere")))
    adhesif_fr, adhesif_en   = _classify_adhesif(_get_adhesif_raw(fiche))
    glassine_fr, glassine_en = _classify_glassine(_fmt_glassine(fiche))
    nb_impr_fr   = _sentence_case(_fmt_nb_impressions(fiche))
    condi_fr     = _sentence_case(_fmt_conditionnement(fiche))

    rows = [
        ("Format de l'étiquette", "Label format",
         format_fr, _sentence_case(_translate_fr_to_en(format_fr))),
        ("Frontal", "Facestock",
         frontal_fr, _sentence_case(_translate_fr_to_en(frontal_fr))),
        ("Adhésif", "Adhesive",
         adhesif_fr, adhesif_en),
        ("Glassine", "Release liner",
         glassine_fr, glassine_en),
        ("Nombre d'impressions", "Number of print colours",
         nb_impr_fr, _sentence_case(_translate_fr_to_en(nb_impr_fr))),
        ("Conditionnement", "Packaging",
         condi_fr, _sentence_case(_translate_fr_to_en(condi_fr))),
    ]

    inner_w = W - ml - mr
    table_top = y

    for i, (fr_lbl, en_lbl, v_fr, v_en) in enumerate(rows):
        y = _draw_bilingual_row(c, ml, mr, y, fr_lbl, en_lbl, v_fr, v_en,
                                striped=(i % 2 == 0))

    # Cadre global du tableau
    c.setStrokeColor(_BLACK)
    c.setLineWidth(0.6)
    c.rect(ml, y, inner_w, table_top - y, fill=0, stroke=1)

    # 5) Pied de page
    _draw_footer(c, ml, mr)

    c.showPage()
    c.save()
    return buf.getvalue()
