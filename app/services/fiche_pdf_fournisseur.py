"""
Générateur PDF — Fiche produit FOURNISSEUR (bilingue FR / EN)

Version à destination des fournisseurs SIFA lors des appels d'offre.
Reprend la charte graphique du PDF client (fiche_pdf_client) mais avec
les données brutes de la fiche produit MyAO (ao_produits) — pas de
classification par dictionnaire, on affiche ce qui est saisi dans la
fiche produit.

En-tête : logo SIFA + coordonnées.
Corps : sections de la fiche produit avec libellés bilingues FR/EN.
Pied de page : mentions de confidentialité + date d'édition.
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from io import BytesIO
from typing import Any
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
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

# ── Couleurs (charte alignée sur fiche_pdf_client) ──────────────────
_YELLOW     = colors.HexColor("#FFD100")
_BLACK      = colors.black
_WHITE      = colors.white
_DARK       = colors.HexColor("#1a1a1a")
_MUTED      = colors.HexColor("#666666")
_LIGHT_GRAY = colors.HexColor("#f5f5f5")
_BORDER     = colors.HexColor("#d1d1d1")
_ACCENT     = colors.HexColor("#0891b2")   # même accent que MyAO

W, H = A4

_PARIS = ZoneInfo("Europe/Paris")


def _v(val: Any) -> str:
    if val is None:
        return "—"
    s = str(val).strip()
    return s if s else "—"


def _num(val: Any, suffix: str = "") -> str:
    """Formatte un nombre : entier si round, sinon décimales propres. + suffixe optionnel."""
    if val is None or val == "":
        return "—"
    try:
        f = float(str(val).replace(",", "."))
        if f == int(f):
            base = f"{int(f)}"
        else:
            base = f"{f:g}"
        return f"{base}{suffix}"
    except (ValueError, TypeError):
        return str(val)


def _clean_reference(ref: Any) -> str:
    """Tronque la référence produit après le premier ' - '."""
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


# ── Traductions FR → EN pour les valeurs libres ─────────────────────
_TYPE_PRODUIT_EN = {
    "rouleau":  "roll",
    "paravent": "fan-folded",
}
_ENROULEMENT_EN = {
    "interieur":  "inside",
    "intérieur":  "inside",
    "exterieur":  "outside",
    "extérieur":  "outside",
    "int":        "inside",
    "ext":        "outside",
}
_BOOL_FR_EN = {
    True:  ("Oui", "Yes"),
    False: ("Non", "No"),
}


def _tr_type_produit(v: Any) -> tuple[str, str]:
    if not v:
        return ("—", "—")
    s = str(v).strip()
    fr = s.capitalize()
    en = _TYPE_PRODUIT_EN.get(s.lower(), s).capitalize()
    return (fr, en)


def _tr_enroulement(v: Any) -> tuple[str, str]:
    if not v:
        return ("—", "—")
    s = str(v).strip()
    fr = s.capitalize()
    en = _ENROULEMENT_EN.get(s.lower(), s).capitalize()
    return (fr, en)


def _tr_bool(v: Any) -> tuple[str, str]:
    b = bool(v)
    return _BOOL_FR_EN[b]


# ── Header / footer (identiques au PDF client) ──────────────────────
def _draw_logo(c: canvas.Canvas, x: float, y_top: float, max_h: float) -> float:
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


def _draw_title(c: canvas.Canvas, y: float) -> float:
    c.setFillColor(_BLACK)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(W / 2, y - 12, "FICHE PRODUIT — APPEL D'OFFRE")
    c.setFillColor(_MUTED)
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(W / 2, y - 26, "Product data sheet — Request for quotation")
    c.setFillColor(_BLACK)
    return y - 34


def _draw_ref_block(c: canvas.Canvas, ml: float, mr: float, y: float,
                    produit: dict) -> float:
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
    ref = _clean_reference(produit.get("ref"))
    c.drawString(ml + 4 * mm, y - 11 * mm, ref)

    client = produit.get("client_nom")
    if client and str(client).strip():
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(_MUTED)
        c.drawRightString(W - mr - 4 * mm, y - 5 * mm, "Client final  /  End customer")
        c.setFillColor(_BLACK)
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(W - mr - 4 * mm, y - 11 * mm, str(client).strip())

    return y_bottom - 4 * mm


_SECTION_TITLE_H = 6.5 * mm
_SECTION_ROW_H = 6.8 * mm
_SECTION_GAP = 5 * mm  # espace vertical entre deux sections empilées


def _section_title(c: canvas.Canvas, x: float, y: float,
                   fr: str, en: str, width: float) -> float:
    """Bandeau de section : accent + titre FR + sous-titre EN italique."""
    h_band = _SECTION_TITLE_H
    y_bottom = y - h_band

    # Bandeau clair de fond
    c.setFillColor(_LIGHT_GRAY)
    c.rect(x, y_bottom, width, h_band, fill=1, stroke=0)
    # Accent gauche (encart plus visible)
    c.setFillColor(_ACCENT)
    c.rect(x, y_bottom, 3 * mm, h_band, fill=1, stroke=0)

    c.setFillColor(_DARK)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 5 * mm, y_bottom + h_band / 2 - 1, fr)

    c.setFillColor(_MUTED)
    c.setFont("Helvetica-Oblique", 7.5)
    c.drawString(x + 5 * mm + c.stringWidth(fr, "Helvetica-Bold", 9) + 2 * mm,
                 y_bottom + h_band / 2 - 1, "/ " + en)

    c.setFillColor(_BLACK)
    return y_bottom


def _draw_row(c: canvas.Canvas, x: float, y: float,
              label_fr: str, label_en: str, value_fr: str, value_en: str,
              striped: bool = False, width: float | None = None) -> float:
    """Ligne compacte — FR uniquement pour label, EN sous FR si valeur diffère."""
    inner_w = width if width is not None else (W - x - 15 * mm)
    row_h = _SECTION_ROW_H
    col_lbl = inner_w * 0.42
    col_val = inner_w - col_lbl

    y_bottom = y - row_h

    if striped:
        c.setFillColor(_LIGHT_GRAY)
        c.rect(x, y_bottom, inner_w, row_h, fill=1, stroke=0)

    c.setStrokeColor(_BORDER)
    c.setLineWidth(0.25)
    c.line(x + col_lbl, y_bottom, x + col_lbl, y)
    c.setLineWidth(0.3)
    c.line(x, y_bottom, x + inner_w, y_bottom)

    y_txt = y - 4.4 * mm

    # Label FR uniquement (EN est signalé dans le titre de section)
    c.setFillColor(_DARK)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(x + 2.5 * mm, y_txt, label_fr)

    # Value FR (bold). Ajout EN en muted si différent.
    x_val = x + col_lbl + 2.5 * mm
    max_val_w = col_val - 5 * mm

    def _fit(txt: str, base: float, bold: bool) -> float:
        font = "Helvetica-Bold" if bold else "Helvetica-Oblique"
        for s in (base, base - 0.5, base - 1, base - 1.5, base - 2):
            if c.stringWidth(txt, font, s) <= max_val_w:
                return s
        return base - 2

    show_en = bool(value_en) and value_en != value_fr
    if show_en:
        y_fr = y - 3.2 * mm
        y_en = y - 5.6 * mm
        size_fr = _fit(value_fr, 8.5, bold=True)
        c.setFillColor(_BLACK)
        c.setFont("Helvetica-Bold", size_fr)
        c.drawString(x_val, y_fr, value_fr)
        size_en = _fit(value_en, 7, bold=False)
        c.setFillColor(_MUTED)
        c.setFont("Helvetica-Oblique", size_en)
        c.drawString(x_val, y_en, value_en)
    else:
        size_fr = _fit(value_fr, 9, bold=True)
        c.setFillColor(_BLACK)
        c.setFont("Helvetica-Bold", size_fr)
        c.drawString(x_val, y_txt, value_fr)

    c.setFillColor(_BLACK)
    return y_bottom


def _section_box(c: canvas.Canvas, x: float, y: float, width: float, height: float) -> None:
    """Bordure autour d'une section (titre + rows) — trace après remplissage."""
    c.setStrokeColor(_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y - height, width, height, fill=0, stroke=1)


def _draw_full_section(c: canvas.Canvas, ml: float, mr: float, y: float,
                       fr: str, en: str, rows: list[tuple],
                       ao_reference: str | None = None) -> float:
    """Rend une section pleine largeur avec bordure autour."""
    rows = _filter_meaningful(rows)
    if not rows:
        return y
    inner_w = W - ml - mr
    need = _SECTION_TITLE_H + len(rows) * _SECTION_ROW_H + _SECTION_GAP
    y = _need_page(c, y, need, ml, mr, ao_reference)
    y_start = y
    y = _section_title(c, ml, y, fr, en, width=inner_w)
    for i, (lfr, len_, vf, ve) in enumerate(rows):
        y = _draw_row(c, ml, y, lfr, len_, vf, ve, striped=(i % 2 == 0), width=inner_w)
    # Bordure autour de la section
    total_h = y_start - y
    _section_box(c, ml, y_start, inner_w, total_h)
    return y - _SECTION_GAP


def _filter_meaningful(rows: list[tuple]) -> list[tuple]:
    """Retire les lignes dont la valeur FR ET EN sont vides ou '—'."""
    def is_empty(v):
        return v is None or str(v).strip() in ("", "—")
    return [r for r in rows if not (is_empty(r[2]) and is_empty(r[3]))]


def _draw_two_col_sections(
    c: canvas.Canvas, ml: float, mr: float, y: float,
    left_title: tuple[str, str], left_rows: list[tuple],
    right_title: tuple[str, str], right_rows: list[tuple],
    ao_reference: str | None = None,
) -> float:
    """Rend deux sections côte à côte, chacune sur ~50% de la largeur, avec bordure."""
    left_rows = _filter_meaningful(left_rows)
    right_rows = _filter_meaningful(right_rows)
    if not left_rows and not right_rows:
        return y
    gap = 6 * mm
    inner_w = W - ml - mr
    col_w = (inner_w - gap) / 2
    x_left = ml
    x_right = ml + col_w + gap
    need = _SECTION_TITLE_H + max(len(left_rows), len(right_rows)) * _SECTION_ROW_H + _SECTION_GAP
    y = _need_page(c, y, need, ml, mr, ao_reference)

    y_start = y
    y_left = y_start
    y_right = y_start
    if left_rows:
        y_left = _section_title(c, x_left, y_start, left_title[0], left_title[1], width=col_w)
        for i, row in enumerate(left_rows):
            fr, en, vf, ve = row
            y_left = _draw_row(c, x_left, y_left, fr, en, vf, ve, striped=(i % 2 == 0), width=col_w)
        _section_box(c, x_left, y_start, col_w, y_start - y_left)
    if right_rows:
        y_right = _section_title(c, x_right, y_start, right_title[0], right_title[1], width=col_w)
        for i, row in enumerate(right_rows):
            fr, en, vf, ve = row
            y_right = _draw_row(c, x_right, y_right, fr, en, vf, ve, striped=(i % 2 == 0), width=col_w)
        _section_box(c, x_right, y_start, col_w, y_start - y_right)
    return min(y_left, y_right) - _SECTION_GAP


def _draw_footer(c: canvas.Canvas, ml: float, mr: float,
                 ao_reference: str | None = None) -> None:
    inner_w = W - ml - mr
    y = 22 * mm
    c.setFillColor(_YELLOW)
    c.rect(ml, y, inner_w, 0.8 * mm, fill=1, stroke=0)
    c.setFillColor(_BLACK)

    y -= 3 * mm
    style = ParagraphStyle(
        "mentions", fontName="Helvetica-Oblique", fontSize=6.5, leading=8,
        textColor=_MUTED, alignment=TA_CENTER,
    )
    txt_fr = ("Document confidentiel destiné exclusivement au fournisseur consulté "
              "dans le cadre de l'appel d'offre SIFA. Toute diffusion à un tiers est interdite. "
              "© SIFA — tous droits réservés.")
    txt_en = ("Confidential document — for the exclusive use of the consulted supplier "
              "in the context of the SIFA request for quotation. Any disclosure to a third "
              "party is prohibited. © SIFA — all rights reserved.")
    p_fr = Paragraph(txt_fr, style)
    p_en = Paragraph(txt_en, style)
    _, h1 = p_fr.wrap(inner_w, 20)
    p_fr.drawOn(c, ml, y - h1)
    y -= h1 + 1
    _, h2 = p_en.wrap(inner_w, 20)
    p_en.drawOn(c, ml, y - h2)

    now_paris = datetime.now(_PARIS)
    date_str = now_paris.strftime("%d/%m/%Y %H:%M")
    c.setFont("Helvetica", 7)
    c.setFillColor(_MUTED)
    c.drawString(ml, 8 * mm,
                 f"Édité le / Issued on : {date_str} (Europe/Paris)")
    if ao_reference:
        c.drawRightString(W - mr, 8 * mm,
                          f"Appel d'offre / RFQ : {ao_reference}")
    c.setFillColor(_BLACK)


# ── Rendu principal ─────────────────────────────────────────────────
def _pw_reset(c: canvas.Canvas, ml: float, mr: float) -> float:
    """Nouvelle page : redessine header + retourne y de départ (après titre)."""
    y = _draw_header(c, ml, mr)
    return y


def _need_page(c: canvas.Canvas, y: float, needed: float, ml: float, mr: float,
               ao_reference: str | None) -> float:
    """Passe à une nouvelle page si y - needed < 30mm (place pour footer)."""
    if y - needed < 30 * mm:
        _draw_footer(c, ml, mr, ao_reference)
        c.showPage()
        y = _pw_reset(c, ml, mr)
    return y


def _mp_label(mp: dict | None) -> str:
    """Formatte une matière première depuis matieres_map."""
    if not mp:
        return "—"
    ref = str(mp.get("reference") or "").strip()
    des = str(mp.get("designation") or "").strip()
    if ref and des:
        return f"{ref} — {des}"
    return ref or des or "—"


def generate_fiche_fournisseur_pdf(
    produit: dict,
    *,
    matieres_map: dict[int, dict] | None = None,
    ao_reference: str | None = None,
) -> bytes:
    """
    Génère le PDF fournisseur bilingue d'une fiche produit MyAO.

    - produit : dict retourné par `_serialize_produit_row()` (contient
      `ref`, `client_nom`, `fiche` avec toutes les sous-sections)
    - matieres_map : dict {matiere_id: {reference, designation, ...}}
      pour afficher les libellés des frontal/adhésif/glassine/carton/palette
    - ao_reference : référence de l'AO (affichée en pied de page si fourni)
    """
    matieres_map = matieres_map or {}
    fiche = produit.get("fiche") or {}
    et   = fiche.get("etiquette") or {}
    ech  = fiche.get("echenillage") or {}
    mat  = fiche.get("matiere") or {}
    bob  = fiche.get("bobines") or {}
    imp  = fiche.get("impressions_detail") or {}
    cond = fiche.get("conditionnement") or {}
    cart = cond.get("carton") or {}
    pal  = cond.get("palette") or {}

    def mp(k: str) -> str:
        mid = mat.get(k) if k in mat else (
            cart.get(k) if k in cart else pal.get(k)
        )
        if mid is None:
            return "—"
        try:
            return _mp_label(matieres_map.get(int(mid)))
        except (TypeError, ValueError):
            return "—"

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    ref_clean = _clean_reference(produit.get("ref"))
    c.setTitle(f"Fiche produit fournisseur — {ref_clean}")
    c.setAuthor("SIFA")

    ml = 15 * mm
    mr = 15 * mm

    y = _draw_header(c, ml, mr)
    y = _draw_title(c, y)
    y = _draw_ref_block(c, ml, mr, y - 4 * mm, produit)

    type_fr, type_en = _tr_type_produit(fiche.get("type_produit"))
    imp_fr, imp_en = _tr_bool(fiche.get("impressions"))

    # ── Section 1 : Infos générales (pleine largeur, courte) ──────
    rows_1 = [
        ("Type de produit",       "Product type",        type_fr, type_en),
        ("Impressions",           "Printing",            imp_fr, imp_en),
    ]
    fmt_eti = ""
    laize, longueur = et.get("laize"), et.get("longueur")
    if laize is not None and longueur is not None:
        try:
            fmt_eti = f"{int(float(laize))} × {int(float(longueur))} mm"
        except (TypeError, ValueError):
            pass
    if fmt_eti:
        rows_1.append(("Format étiquette", "Label format", fmt_eti, fmt_eti))
    y = _draw_full_section(c, ml, mr, y - 2 * mm, "Infos générales", "General information",
                           rows_1, ao_reference=ao_reference)

    # ── Sections 2 & 3 : Étiquette + Échenillage (côte à côte) ────
    rows_2 = [
        ("Laize",         "Width",        _num(et.get("laize"),    " mm"), _num(et.get("laize"),    " mm")),
        ("Longueur",      "Length",       _num(et.get("longueur"), " mm"), _num(et.get("longueur"), " mm")),
        ("Rayon",         "Corner radius",_num(et.get("rayon"),    " mm"), _num(et.get("rayon"),    " mm")),
        ("Perforation",   "Perforation",  _v(et.get("perforation")),        _v(et.get("perforation"))),
    ]
    rows_3 = [
        ("Espace à droite", "Right gap",   _num(ech.get("droite"), " mm"), _num(ech.get("droite"), " mm")),
        ("Espace à gauche", "Left gap",    _num(ech.get("gauche"), " mm"), _num(ech.get("gauche"), " mm")),
        ("En avance",       "Down gap",    _num(ech.get("avance"), " mm"), _num(ech.get("avance"), " mm")),
    ]
    y = _draw_two_col_sections(
        c, ml, mr, y - 2 * mm,
        ("Étiquette", "Label"), rows_2,
        ("Échenillage", "Matrix stripping"), rows_3,
        ao_reference=ao_reference,
    )

    # ── Sections 4 & 5 : Matière + Bobines (côte à côte) ──────────
    frontal_lbl  = _mp_label(matieres_map.get(int(mat["frontal_id"])) if mat.get("frontal_id") else None)
    adhesif_lbl  = _mp_label(matieres_map.get(int(mat["adhesif_id"])) if mat.get("adhesif_id") else None)
    glassine_lbl = _mp_label(matieres_map.get(int(mat["glassine_id"])) if mat.get("glassine_id") else None)
    rows_4 = [
        ("Frontal",           "Facestock",              frontal_lbl,  frontal_lbl),
        ("Adhésif",           "Adhesive",               adhesif_lbl,  adhesif_lbl),
        ("Grammage adhésif",  "Adhesive coat weight",   _num(mat.get("grammage_adhesif"), " g/m²"),
                                                        _num(mat.get("grammage_adhesif"), " gsm")),
        ("Glassine",          "Release liner",          glassine_lbl, glassine_lbl),
        ("Couleur glassine",  "Liner colour",           _v(mat.get("couleur_glassine")), _v(mat.get("couleur_glassine"))),
    ]
    enr_fr, enr_en = _tr_enroulement(bob.get("enroulement"))
    rows_5 = [
        ("Diamètre mandrin",   "Core diameter",     _num(bob.get("diametre_mandrin"), " mm"),
                                                    _num(bob.get("diametre_mandrin"), " mm")),
        ("Enroulement",        "Winding direction", enr_fr, enr_en),
        ("Diamètre bobine",    "Roll diameter",     _num(bob.get("diametre_bobine"), " mm"),
                                                    _num(bob.get("diametre_bobine"), " mm")),
        ("Étiquettes / bobine","Labels / roll",     _num(bob.get("nb_etiquettes")),
                                                    _num(bob.get("nb_etiquettes"))),
    ]
    y = _draw_two_col_sections(
        c, ml, mr, y - 1 * mm,
        ("Matière", "Material"), rows_4,
        ("Bobines", "Rolls"), rows_5,
        ao_reference=ao_reference,
    )

    # ── Section 6 : Impressions (si activées) ─────────────────────
    if fiche.get("impressions"):
        aplat_txt_fr = "Non"
        aplat_txt_en = "No"
        if imp.get("aplat"):
            pct = imp.get("aplat_pourcent")
            aplat_txt_fr = f"Oui ({_num(pct)} %)"
            aplat_txt_en = f"Yes ({_num(pct)} %)"
        rows_6 = [
            ("Aplat",  "Solid ink coverage", aplat_txt_fr, aplat_txt_en),
            ("Recto",  "Front (colours)",    _num(imp.get("recto")), _num(imp.get("recto"))),
            ("Verso",  "Back (colours)",     _num(imp.get("verso")), _num(imp.get("verso"))),
        ]
        details_recto = imp.get("recto_details") or []
        details_verso = imp.get("verso_details") or []
        for i, d in enumerate(details_recto, 1):
            val = f"{d.get('couleur','')} — {d.get('printing_area','')}".strip(" —")
            rows_6.append((f"Recto {i}", f"Front {i}", val or "—", val or "—"))
        for i, d in enumerate(details_verso, 1):
            val = f"{d.get('couleur','')} — {d.get('printing_area','')}".strip(" —")
            rows_6.append((f"Verso {i}", f"Back {i}", val or "—", val or "—"))
        y = _draw_full_section(c, ml, mr, y - 1 * mm, "Impressions", "Printing details",
                               rows_6, ao_reference=ao_reference)

    # ── Sections 7 & 8 : Cartons + Palettes (côte à côte) ─────────
    cart_lbl = _mp_label(matieres_map.get(int(cart["matiere_id"])) if cart.get("matiere_id") else None)
    rows_7 = [
        ("Type de carton",   "Box type",           cart_lbl, cart_lbl),
        ("Bobines au sol",   "Rolls per layer",    _num(cart.get("bobines_sol")), _num(cart.get("bobines_sol"))),
        ("Nombre d'étages",  "Number of layers",   _num(cart.get("nb_etages")),   _num(cart.get("nb_etages"))),
        ("Bobines / carton", "Rolls / box",        _num(cart.get("bobines_carton")), _num(cart.get("bobines_carton"))),
    ]
    pal_lbl = _mp_label(matieres_map.get(int(pal["matiere_id"])) if pal.get("matiere_id") else None)
    rows_8 = [
        ("Type de palette",   "Pallet type",         pal_lbl, pal_lbl),
        ("Cartons au sol",    "Boxes per layer",     _num(pal.get("cartons_sol")),     _num(pal.get("cartons_sol"))),
        ("Étages de cartons", "Number of layers",    _num(pal.get("nb_etages")),       _num(pal.get("nb_etages"))),
        ("Cartons / palette", "Boxes / pallet",      _num(pal.get("cartons_palette")), _num(pal.get("cartons_palette"))),
    ]
    y = _draw_two_col_sections(
        c, ml, mr, y - 1 * mm,
        ("Cartons", "Boxes"), rows_7,
        ("Palettes", "Pallets"), rows_8,
        ao_reference=ao_reference,
    )

    # ── Section 9 : Particularités (si renseignées) ───────────────
    part = fiche.get("particularites")
    if part and str(part).strip():
        inner_w = W - ml - mr
        box_h = 22 * mm
        need = _SECTION_TITLE_H + box_h + _SECTION_GAP
        y = _need_page(c, y, need, ml, mr, ao_reference)
        y_start = y
        y = _section_title(c, ml, y, "Particularités", "Special requirements", width=inner_w)
        y_box = y - box_h
        c.setStrokeColor(_BORDER)
        c.setLineWidth(0.4)
        c.rect(ml, y_box, inner_w, box_h, fill=0, stroke=1)
        style = ParagraphStyle("part", fontName="Helvetica", fontSize=9,
                               leading=11, textColor=_BLACK, alignment=TA_LEFT)
        p = Paragraph(str(part).replace("\n", "<br/>"), style)
        p.wrapOn(c, inner_w - 4 * mm, box_h - 2 * mm)
        p.drawOn(c, ml + 2 * mm, y_box + 2 * mm)
        _section_box(c, ml, y_start, inner_w, y_start - y_box)
        y = y_box - _SECTION_GAP

    _draw_footer(c, ml, mr, ao_reference)
    c.showPage()
    c.save()
    return buf.getvalue()
