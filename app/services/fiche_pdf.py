"""
Générateur PDF — Fiche technique SIFA
Reproduit fidèlement le modèle sifa_pdf_gpr_ff.pdf avec les données remplies.
"""
from __future__ import annotations

from io import BytesIO
from typing import Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT


# ── Couleurs (reprises du modèle) ────────────────────────────────────
_YELLOW   = colors.HexColor("#FFFF00")
_LAVENDER = colors.HexColor("#E8CFEC")
_WHITE    = colors.white
_BLACK    = colors.black
_LIGHT_GRAY = colors.HexColor("#F5F5F5")

W, H = A4  # 595.28 x 841.89 pt


def _v(val: Any, suffix: str = "") -> str:
    """Formate une valeur : None → '', sinon str + suffix."""
    if val is None or val == "":
        return ""
    return f"{val}{suffix}"


def _draw_cell(
    c: canvas.Canvas,
    x: float, y: float, w: float, h: float,
    label: str = "", value: str = "",
    bg: Optional[colors.Color] = None,
    bold_label: bool = False,
    bold_value: bool = False,
    font_size: float = 7,
    border: bool = True,
    label_color: colors.Color = _BLACK,
    align_value: str = "left",
) -> None:
    """Dessine une cellule avec label et valeur."""
    if bg:
        c.setFillColor(bg)
        c.rect(x, y, w, h, fill=1, stroke=0)
        c.setFillColor(_BLACK)
    if border:
        c.setStrokeColor(_BLACK)
        c.setLineWidth(0.3)
        c.rect(x, y, w, h, fill=0, stroke=1)

    pad = 1.5 * mm
    text_y = y + h / 2 - font_size * 0.35

    if label:
        c.setFont("Helvetica-Bold" if bold_label else "Helvetica", font_size - 0.5)
        c.setFillColor(label_color)
        c.drawString(x + pad, text_y, label)
        c.setFillColor(_BLACK)

    if value:
        c.setFont("Helvetica-Bold" if bold_value else "Helvetica", font_size)
        val_x = x + pad + (c.stringWidth(label, "Helvetica-Bold" if bold_label else "Helvetica", font_size - 0.5) + 1 * mm if label else 0)
        if align_value == "right":
            val_x = x + w - pad - c.stringWidth(value, "Helvetica-Bold" if bold_value else "Helvetica", font_size)
        c.drawString(val_x, text_y, value)


def _hline(c: canvas.Canvas, x: float, y: float, w: float) -> None:
    c.setStrokeColor(_BLACK)
    c.setLineWidth(0.5)
    c.line(x, y, x + w, y)


def _section_header(c: canvas.Canvas, x: float, y: float, w: float, h: float, text: str) -> None:
    c.setFillColor(_BLACK)
    c.rect(x, y, w, h, fill=1, stroke=0)
    c.setFillColor(_WHITE)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x + 2 * mm, y + h / 2 - 3, text)
    c.setFillColor(_BLACK)


def generate_fiche_pdf(fiche: dict) -> bytes:
    """
    Génère le PDF d'une fiche technique à partir d'un dict de données.
    Retourne les bytes du PDF.
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    # Marges
    ml = 10 * mm   # left
    mr = 10 * mm   # right
    mt = 10 * mm   # top (from top of page)
    pw = W - ml - mr  # page width usable

    y = H - mt  # current y (top-down)
    row_h = 5.5 * mm
    sh = 5 * mm  # section header height

    def _f(key: str, suffix: str = "") -> str:
        return _v(fiche.get(key), suffix)

    # ── Titre ────────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(W / 2, y - 6 * mm, "FICHE TECHNIQUE")
    y -= 10 * mm

    # ── REF / Dernière modif ─────────────────────────────────────────
    ref_w = pw * 0.45
    mod_w = pw - ref_w
    _draw_cell(c, ml, y - row_h, ref_w, row_h,
               label="REF : ", value=_f("reference"), bold_label=True, bold_value=True, font_size=8)
    _draw_cell(c, ml + ref_w, y - row_h, mod_w, row_h,
               label="Dernière modification le : ", value=_f("date_modif"), font_size=7.5)
    y -= row_h

    # ── FORMAT ──────────────────────────────────────────────────────
    _draw_cell(c, ml, y - row_h, pw, row_h,
               label="FORMAT : ", value=_f("format"), bold_label=True, font_size=8)
    y -= row_h + 1 * mm

    # ── En-têtes colonnes ETIQUETTE / MODULE / ECHENILLAGE ──────────
    col1 = pw * 0.28
    col2 = pw * 0.28
    col3 = pw - col1 - col2

    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(_BLACK)
    # Underline headers
    for label, cx, cw in [("ETIQUETTE", ml, col1), ("MODULE", ml + col1, col2), ("ECHENILLAGE", ml + col1 + col2, col3)]:
        c.drawCentredString(cx + cw / 2, y - 4 * mm, label)
        c.setLineWidth(0.5)
        c.line(cx + 2 * mm, y - 5 * mm, cx + cw - 2 * mm, y - 5 * mm)
    y -= 6 * mm

    # Lignes Etiquette / Module / Echenillage
    eti_rows = [
        ("Laize",        _f("eti_laize"),       "Laize",       _f("mod_laize"),    "Latéral ext.",  _f("lateral_ext")),
        ("Longueur",     _f("eti_longueur"),     "Longueur",    _f("mod_longueur"), "Horizontal",    _f("horizontal")),
        ("Rayons",       _f("eti_rayons"),       "Nb de front", _f("mod_nb_front"), "Latéral int.",  _f("lateral_int")),
        ("Perforations", _f("eti_perforations"), "",            "",                  "",              ""),
    ]

    nb_front_highlight = _YELLOW
    lat_int_highlight = _YELLOW

    for i, (l1, v1, l2, v2, l3, v3) in enumerate(eti_rows):
        bg2 = nb_front_highlight if l2 == "Nb de front" else None
        bg3 = lat_int_highlight if l3 in ("Latéral int.",) else None
        _draw_cell(c, ml, y - row_h, col1, row_h, label=l1 + " : ", value=v1, font_size=7)
        _draw_cell(c, ml + col1, y - row_h, col2, row_h, label=l2 + (" : " if l2 else ""), value=v2, bg=bg2, bold_label=bool(bg2), font_size=7)
        _draw_cell(c, ml + col1 + col2, y - row_h, col3, row_h, label=l3 + (" : " if l3 else ""), value=v3, bg=bg3, bold_label=bool(bg3), font_size=7)
        y -= row_h

    y -= 1 * mm

    # ── OUTILS ──────────────────────────────────────────────────────
    # Colonnes : étiquette RECTO/VERSO | Outil | N°SIFA | Laize/Epaisseur | suite
    lbl_w = 8 * mm
    o_w1  = pw * 0.16
    o_w2  = pw * 0.16
    o_w3  = pw * 0.14
    o_w4  = pw * 0.12
    o_w5  = pw * 0.12
    o_rest = pw - lbl_w - o_w1 - o_w2 - o_w3 - o_w4 - o_w5

    def _outil_row(label_side: str, outil_label: str, forme: str, num_sifa: str,
                   laize_ep_label: str, laize_ep_val: str,
                   epaisseur_label: str, epaisseur_val: str, epaisseur_unit: str):
        nonlocal y
        # Colonne gauche : RECTO/VERSO
        if label_side:
            c.setFont("Helvetica-Bold", 6.5)
            c.saveState()
            c.translate(ml + lbl_w / 2, y - row_h * 1.5)
            c.rotate(90)
            c.drawCentredString(0, 0, label_side)
            c.restoreState()

        _draw_cell(c, ml + lbl_w, y - row_h, o_w1, row_h, label=outil_label + " : ", value=forme, bold_label=True, font_size=7)
        _draw_cell(c, ml + lbl_w + o_w1, y - row_h, o_w2, row_h, label="N° SIFA : ", value=num_sifa, font_size=7)
        _draw_cell(c, ml + lbl_w + o_w1 + o_w2, y - row_h, o_w3, row_h, label=laize_ep_label + " : ", value=laize_ep_val, font_size=7)
        _draw_cell(c, ml + lbl_w + o_w1 + o_w2 + o_w3, y - row_h, o_w4 + o_w5 + o_rest, row_h,
                   label=epaisseur_label + " : ", value=epaisseur_val + (" µm" if epaisseur_val and epaisseur_unit else ""), font_size=7)
        y -= row_h

    def _outil_dents_row(nb_dents: str, nb_front: str, nb_avance: str):
        nonlocal y
        w3 = (pw - lbl_w) / 3
        _draw_cell(c, ml + lbl_w, y - row_h, w3, row_h, label="Nb dents : ", value=nb_dents, font_size=7)
        _draw_cell(c, ml + lbl_w + w3, y - row_h, w3, row_h, label="Nb de front : ", value=nb_front, font_size=7)
        _draw_cell(c, ml + lbl_w + w3 * 2, y - row_h, w3, row_h, label="Nb avance : ", value=nb_avance, font_size=7)
        y -= row_h

    # Outil 1
    _outil_row("RECTO", "OUTIL 1", _f("outil1_forme"), _f("outil1_numero_sifa"),
               "Laize", _f("outil1_laize"), "Epaisseur", _f("outil1_epaisseur"), "µm")
    # Machine row
    w_mach = (pw - lbl_w) / 2
    _draw_cell(c, ml + lbl_w, y - row_h, w_mach, row_h, label="Machine : ", value=_f("machine"), font_size=7)
    _draw_cell(c, ml + lbl_w + w_mach, y - row_h, w_mach, row_h, font_size=7)
    y -= row_h
    _outil_dents_row(_f("outil1_nb_dents"), _f("outil1_nb_front"), _f("outil1_nb_avance"))

    # Outil 2
    _outil_row("VERSO", "OUTIL 2", _f("outil2_forme"), _f("outil2_numero_sifa"),
               "", "", "Epaisseur", _f("outil2_epaisseur"), "µm")
    _outil_dents_row(_f("outil2_nb_dents"), _f("outil2_nb_front"), _f("outil2_nb_avance"))

    # Outil 3
    _outil_row("", "OUTIL 3", _f("outil3_forme"), _f("outil3_numero_sifa"),
               "", "", "Epaisseur", _f("outil3_epaisseur"), "µm")
    _outil_dents_row(_f("outil3_nb_dents"), _f("outil3_nb_front"), _f("outil3_nb_avance"))

    y -= 1 * mm

    # ── MATIÈRE ──────────────────────────────────────────────────────
    half = pw / 2

    _draw_cell(c, ml, y - row_h, half, row_h, label="Support : ",
               value=_f("support") or _f("matiere"), bg=_LAVENDER, font_size=7)
    _draw_cell(c, ml + half, y - row_h, half, row_h, label="Glassine : ",
               value=_f("glassine"), bg=_LAVENDER, font_size=7)
    y -= row_h

    _draw_cell(c, ml, y - row_h, half, row_h, label="Laize optimale : ", value=_f("laize_optimale"), font_size=7)
    _draw_cell(c, ml + half, y - row_h, half, row_h, label="Laize optionnelle : ", value=_f("laize_optionnelle"), font_size=7)
    y -= row_h

    ep_w = pw * 0.4
    adh_w = pw - ep_w
    _draw_cell(c, ml, y - row_h, ep_w, row_h, label="Epaisseur : ", value=_f("epaisseur", " µm"), font_size=7)
    _draw_cell(c, ml + ep_w, y - row_h, adh_w, row_h, label="Adhésif : ", value=_f("adhesif"), bg=_LAVENDER, font_size=7)
    y -= row_h

    _draw_cell(c, ml, y - row_h, ep_w, row_h, font_size=7)
    _draw_cell(c, ml + ep_w, y - row_h, adh_w, row_h, label="Grammage : ", value=_f("qte_au_mille", " ml"), bg=_LAVENDER, font_size=7)
    y -= row_h + 1 * mm

    # ── IMPRESSION ────────────────────────────────────────────────────
    _section_header(c, ml, y - sh, pw, sh, "IMPRESSION")
    y -= sh

    nc_w = pw * 0.33
    r_w  = pw * 0.33
    v_w  = pw - nc_w - r_w
    _draw_cell(c, ml, y - row_h, nc_w, row_h, label="Nb couleurs : ", value=_f("nb_couleurs"), font_size=7)
    _draw_cell(c, ml + nc_w, y - row_h, r_w, row_h, label="Recto : ", value=_f("recto"), font_size=7)
    _draw_cell(c, ml + nc_w + r_w, y - row_h, v_w, row_h, label="Verso : ", value=_f("verso"), font_size=7)
    y -= row_h

    # En-têtes tableau impression
    col_p = pw * 0.08
    col_coul = pw * 0.15
    col_ani  = pw * 0.12
    col_comp = pw - col_p - col_coul - col_ani
    thead_h  = 4 * mm

    for lbl, cx, cw in [("Pantone", ml, col_p), ("Couleur", ml + col_p, col_coul),
                         ("Anilox", ml + col_p + col_coul, col_ani),
                         ("Composition", ml + col_p + col_coul + col_ani, col_comp)]:
        c.setFillColor(_LIGHT_GRAY)
        c.rect(cx, y - thead_h, cw, thead_h, fill=1, stroke=1)
        c.setFillColor(_BLACK)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(cx + cw / 2, y - thead_h + 1.2 * mm, lbl)
    y -= thead_h

    tete_row_h = 7 * mm
    for i, (pref, cref, aref, compref) in enumerate([
        ("tete1_pantone", "tete1_couleur", "tete1_anilox", "tete1_composition"),
        ("tete2_pantone", "tete2_couleur", "tete2_anilox", "tete2_composition"),
        ("tete3_pantone", "tete3_couleur", "tete3_anilox", "tete3_composition"),
    ], start=1):
        _draw_cell(c, ml, y - tete_row_h, col_p, tete_row_h, value=_f(pref), font_size=7)
        _draw_cell(c, ml + col_p, y - tete_row_h, col_coul, tete_row_h, value=_f(cref), font_size=7)
        _draw_cell(c, ml + col_p + col_coul, y - tete_row_h, col_ani, tete_row_h, value=_f(aref), font_size=7)
        _draw_cell(c, ml + col_p + col_coul + col_ani, y - tete_row_h, col_comp, tete_row_h, value=_f(compref), font_size=7)
        # Label Tête N sur le côté gauche
        c.setFont("Helvetica", 6)
        c.drawString(ml - 7 * mm, y - tete_row_h / 2 - 2, f"Tête {i}")
        y -= tete_row_h

    _draw_cell(c, ml, y - row_h, pw, row_h, label="Remarque : ", value=_f("remarque"), font_size=7)
    y -= row_h + 1 * mm

    # ── CONDITIONNEMENT ───────────────────────────────────────────────
    _section_header(c, ml, y - sh, pw, sh, "CONDITIONNEMENT")
    y -= sh

    mw = pw * 0.5
    _draw_cell(c, ml, y - row_h, mw, row_h, label="Mandrin dia. : ", value=_f("mandrin_dia"), bg=_YELLOW, bold_label=True, font_size=7)
    _draw_cell(c, ml + mw, y - row_h, pw - mw, row_h, label="Mandrin longueur : ", value=_f("mandrin_longueur"), font_size=7)
    y -= row_h

    _draw_cell(c, ml, y - row_h, mw, row_h, label="Enroulement : ", value=_f("enroulement"), bg=_YELLOW, bold_label=True, font_size=7)
    _draw_cell(c, ml + mw, y - row_h, pw - mw, row_h, label="Nb etiq / bobin : ", value=_f("nb_etiq_bobin"), bg=_YELLOW, bold_label=True, font_size=7)
    y -= row_h

    _draw_cell(c, ml, y - row_h, mw, row_h, label="Dia. Ext. : ", value=_f("dia_ext"), font_size=7)
    _draw_cell(c, ml + mw, y - row_h, pw - mw, row_h, label="Poids : ", value=_f("poids"), font_size=7)
    y -= row_h

    _draw_cell(c, ml, y - row_h, pw, row_h, label="Condi. : ", value=_f("conditionnement"), font_size=7)
    y -= row_h

    _draw_cell(c, ml, y - row_h, pw, row_h, label="Cales et sachets : ", value=_f("cales_sachets"), font_size=7)
    y -= row_h

    _draw_cell(c, ml, y - row_h, pw, row_h, label="Cartons : ", value=_f("cartons"), font_size=7)
    y -= row_h

    sol_w = pw * 0.3
    et_w  = pw * 0.3
    bob_w = pw - sol_w - et_w
    _draw_cell(c, ml, y - row_h, sol_w, row_h, label="Nb au sol : ", value=_f("nb_au_sol"), font_size=7)
    _draw_cell(c, ml + sol_w, y - row_h, et_w, row_h, label="Nb étage : ", value=_f("nb_etage"), font_size=7)
    _draw_cell(c, ml + sol_w + et_w, y - row_h, bob_w, row_h, label="Nb bobines / carton : ",
               value=_f("nb_bobines_carton"), bg=_YELLOW, bold_label=True, font_size=7)
    y -= row_h + 1 * mm

    # ── PALETTISATION ─────────────────────────────────────────────────
    _section_header(c, ml, y - sh, pw, sh, "PALETTISATION")
    y -= sh

    _draw_cell(c, ml, y - row_h, pw, row_h, label="Type de palette : ", value=_f("palette_type"), font_size=7)
    y -= row_h

    p1 = pw * 0.33
    p2 = pw * 0.33
    p3 = pw - p1 - p2
    _draw_cell(c, ml, y - row_h, p1, row_h, label="Nb cartons sol : ", value=_f("palette_nb_cartons_sol"), font_size=7)
    _draw_cell(c, ml + p1, y - row_h, p2, row_h, label="Nb cartons en hauteur : ", value=_f("palette_nb_cartons_hauteur"), font_size=7)
    _draw_cell(c, ml + p1 + p2, y - row_h, p3, row_h, label="Hauteur Max : ", value=_f("palette_hauteur_max"), font_size=7)
    y -= row_h + 1 * mm

    # ── PARTICULARITÉ ─────────────────────────────────────────────────
    _section_header(c, ml, y - sh, pw, sh, "Particularité")
    y -= sh

    part_h = 18 * mm
    c.setStrokeColor(_BLACK)
    c.setLineWidth(0.3)
    c.rect(ml, y - part_h, pw, part_h, fill=0, stroke=1)

    part_text = _f("particularite") or _f("notes")
    if part_text:
        style = ParagraphStyle("pt", fontName="Helvetica", fontSize=7, leading=9)
        p = Paragraph(part_text.replace("\n", "<br/>"), style)
        pw_inner = pw - 4 * mm
        p.wrapOn(c, pw_inner, part_h - 2 * mm)
        p.drawOn(c, ml + 2 * mm, y - part_h + 2 * mm)

    c.save()
    return buf.getvalue()
