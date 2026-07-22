"""
Générateur PDF — Fiche technique CLIENT SIFA (bilingue FR / EN)

Version simplifiée à destination des clients, contenant uniquement les infos
essentielles (format, frontal, adhésif, grammage adhésif, nombre d'impressions,
conditionnement) avec libellés bilingues (FR à gauche, EN à droite).

En-tête : logo SIFA + coordonnées siège (adresse, téléphone, email).
Pied de page : mentions de confidentialité + date d'édition + n° version.
"""
from __future__ import annotations

import os
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
SIFA_EMAIL   = "contact@sifa.pro"

# Version du modèle de fiche client (à incrémenter si on change la mise en page)
FICHE_CLIENT_VERSION = "V1 — 07/2026"

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


def _v(val: Any) -> str:
    """None/'' → '—', sinon str(val)."""
    if val is None:
        return "—"
    s = str(val).strip()
    return s if s else "—"


def _fmt_adhesif(fiche: dict) -> str:
    """Adhésif : préfère 'adhesif' puis 'adhesif_label' puis 'ref_adhesif'."""
    for k in ("adhesif", "adhesif_label", "ref_adhesif"):
        v = fiche.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return "—"


def _fmt_grammage(fiche: dict) -> str:
    """Grammage adhésif : qte_au_mille (g/m² ou ml selon contexte)."""
    v = fiche.get("qte_au_mille")
    if v is None or str(v).strip() == "":
        return "—"
    s = str(v).strip()
    # Ajoute unité si numérique nu
    try:
        float(s.replace(",", "."))
        return f"{s} g/m²"
    except ValueError:
        return s


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
        txt += f"  ({', '.join(extras)})"
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
    # Chemins possibles : static/ à la racine du projet
    candidates = [
        os.path.join(os.getcwd(), "static", "sifa_logo.png"),
        os.path.join(os.path.dirname(__file__), "..", "..", "static", "sifa_logo.png"),
        "/home/sifa/production-saas/static/sifa_logo.png",
        "/home/sifa/production-saas-v1/static/sifa_logo.png",
    ]
    logo_path = next((p for p in candidates if os.path.isfile(p)), None)
    if not logo_path:
        # Fallback texte
        c.setFillColor(_BLACK)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(x, y_top - 16, "SIFA")
        return 45 * mm
    try:
        from reportlab.lib.utils import ImageReader
        img = ImageReader(logo_path)
        iw, ih = img.getSize()
        # Fit dans max_h de hauteur
        target_h = max_h
        target_w = iw * target_h / ih
        # Cap la largeur pour ne pas manger toute la page
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
    logo_w = _draw_logo(c, ml, y_top, logo_h)

    # Coordonnées à droite
    x_right = W - mr
    c.setFillColor(_DARK)
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(x_right, y_top - 4, SIFA_NAME)
    c.setFont("Helvetica", 8)
    c.setFillColor(_MUTED)
    c.drawRightString(x_right, y_top - 14, SIFA_ADDRESS)
    c.drawRightString(x_right, y_top - 24, f"Tél. : {SIFA_PHONE}")
    c.drawRightString(x_right, y_top - 34, SIFA_EMAIL)

    # Ligne jaune séparatrice
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
    """Bloc référence produit (encadré, mise en avant)."""
    inner_w = W - ml - mr
    block_h = 14 * mm
    y_bottom = y - block_h

    # Cadre
    c.setStrokeColor(_BLACK)
    c.setLineWidth(0.6)
    c.setFillColor(_LIGHT_GRAY)
    c.rect(ml, y_bottom, inner_w, block_h, fill=1, stroke=1)
    c.setFillColor(_BLACK)

    # Contenu
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(_MUTED)
    c.drawString(ml + 4 * mm, y - 5 * mm, "Référence produit  /  Product reference")
    c.setFillColor(_BLACK)
    c.setFont("Helvetica-Bold", 14)
    ref = _v(fiche.get("reference"))
    c.drawString(ml + 4 * mm, y - 11 * mm, ref)

    # Client (si dispo) à droite
    client = fiche.get("client")
    if client and str(client).strip():
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(_MUTED)
        c.drawRightString(W - mr - 4 * mm, y - 5 * mm, "Client  /  Customer")
        c.setFillColor(_BLACK)
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(W - mr - 4 * mm, y - 11 * mm, str(client).strip())

    return y_bottom - 6 * mm


def _draw_info_row(c: canvas.Canvas, ml: float, mr: float, y: float,
                   label_fr: str, label_en: str, value: str,
                   striped: bool = False) -> float:
    """
    Ligne d'info : [label FR | label EN | valeur].
    Retourne le nouveau y (bas de la ligne).
    """
    inner_w = W - ml - mr
    row_h   = 12 * mm

    col_fr = inner_w * 0.28
    col_en = inner_w * 0.28
    col_v  = inner_w - col_fr - col_en

    y_bottom = y - row_h

    # Fond zébré
    if striped:
        c.setFillColor(_LIGHT_GRAY)
        c.rect(ml, y_bottom, inner_w, row_h, fill=1, stroke=0)

    # Séparateurs colonnes
    c.setStrokeColor(_BORDER)
    c.setLineWidth(0.3)
    c.line(ml + col_fr, y_bottom, ml + col_fr, y)
    c.line(ml + col_fr + col_en, y_bottom, ml + col_fr + col_en, y)

    # Bord inférieur
    c.setStrokeColor(_BORDER)
    c.setLineWidth(0.4)
    c.line(ml, y_bottom, ml + inner_w, y_bottom)

    # Textes
    text_y = y - row_h / 2 - 3
    c.setFillColor(_DARK)

    # Label FR
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(ml + 3 * mm, text_y, label_fr)

    # Label EN (italique gris)
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(_MUTED)
    c.drawString(ml + col_fr + 3 * mm, text_y, label_en)

    # Valeur (bold noir)
    c.setFillColor(_BLACK)
    c.setFont("Helvetica-Bold", 10.5)
    # Wrap si trop long
    max_val_w = col_v - 6 * mm
    text_w = c.stringWidth(value, "Helvetica-Bold", 10.5)
    if text_w > max_val_w:
        # Réduit la taille progressivement
        for size in (10, 9.5, 9, 8.5, 8):
            c.setFont("Helvetica-Bold", size)
            if c.stringWidth(value, "Helvetica-Bold", size) <= max_val_w:
                break
    c.drawString(ml + col_fr + col_en + 3 * mm, text_y, value)

    return y_bottom


def _draw_footer(c: canvas.Canvas, ml: float, mr: float, fiche: dict) -> None:
    """Pied de page : mentions + date d'édition + version."""
    inner_w = W - ml - mr

    # Ligne jaune
    y = 22 * mm
    c.setFillColor(_YELLOW)
    c.rect(ml, y, inner_w, 0.8 * mm, fill=1, stroke=0)
    c.setFillColor(_BLACK)

    # Mentions confidentialité (bilingues, petit gris)
    y -= 3 * mm
    style_fr = ParagraphStyle(
        "mentions_fr", fontName="Helvetica-Oblique", fontSize=6.5, leading=8,
        textColor=_MUTED, alignment=TA_CENTER,
    )
    style_en = ParagraphStyle(
        "mentions_en", fontName="Helvetica-Oblique", fontSize=6.5, leading=8,
        textColor=_MUTED, alignment=TA_CENTER,
    )
    txt_fr = ("Document non contractuel — Les spécifications techniques peuvent évoluer sans préavis. "
              "Diffusion réservée au destinataire. © SIFA — tous droits réservés.")
    txt_en = ("Non-contractual document — Technical specifications may change without notice. "
              "For addressee use only. © SIFA — all rights reserved.")
    p_fr = Paragraph(txt_fr, style_fr)
    p_en = Paragraph(txt_en, style_en)
    w1, h1 = p_fr.wrap(inner_w, 20)
    p_fr.drawOn(c, ml, y - h1)
    y -= h1 + 1
    w2, h2 = p_en.wrap(inner_w, 20)
    p_en.drawOn(c, ml, y - h2)
    y -= h2 + 2 * mm

    # Ligne date + version
    now_paris = datetime.now(_PARIS)
    date_str = now_paris.strftime("%d/%m/%Y %H:%M")
    ref = _v(fiche.get("reference"))
    c.setFont("Helvetica", 7)
    c.setFillColor(_MUTED)
    c.drawString(ml, 8 * mm,
                 f"Édité le / Issued on : {date_str} (Europe/Paris)")
    c.drawCentredString(W / 2, 8 * mm,
                        f"Réf. {ref}")
    c.drawRightString(W - mr, 8 * mm,
                      f"Modèle {FICHE_CLIENT_VERSION}")
    c.setFillColor(_BLACK)


def generate_fiche_client_pdf(fiche: dict) -> bytes:
    """
    Génère le PDF client (bilingue FR/EN) d'une fiche technique.
    Retourne les bytes du PDF.
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Fiche technique client — {_v(fiche.get('reference'))}")
    c.setAuthor("SIFA")

    ml = 15 * mm
    mr = 15 * mm

    # 1) Bandeau (logo + coordonnées)
    y = _draw_header(c, ml, mr)

    # 2) Titre bilingue
    y = _draw_bilingual_title(c, y)

    # 3) Bloc référence
    y = _draw_ref_block(c, ml, mr, y - 4 * mm, fiche)

    # 4) Tableau bilingue des 6 infos essentielles
    # Cadre extérieur
    rows = [
        ("Format de l'étiquette", "Label format",
         _v(fiche.get("format"))),
        ("Frontal", "Facestock",
         _v(fiche.get("support") or fiche.get("matiere"))),
        ("Adhésif", "Adhesive",
         _fmt_adhesif(fiche)),
        ("Grammage adhésif", "Adhesive coat weight",
         _fmt_grammage(fiche)),
        ("Nombre d'impressions", "Number of print colours",
         _fmt_nb_impressions(fiche)),
        ("Conditionnement", "Packaging",
         _fmt_conditionnement(fiche)),
    ]

    inner_w = W - ml - mr
    table_top = y

    # En-tête de tableau (petits libellés colonnes)
    hdr_h = 6 * mm
    y_hdr_bottom = y - hdr_h
    c.setFillColor(_BLACK)
    c.rect(ml, y_hdr_bottom, inner_w, hdr_h, fill=1, stroke=0)
    c.setFillColor(_WHITE)
    c.setFont("Helvetica-Bold", 8)
    col_fr = inner_w * 0.28
    col_en = inner_w * 0.28
    col_v  = inner_w - col_fr - col_en
    c.drawString(ml + 3 * mm,                    y_hdr_bottom + 2, "CARACTÉRISTIQUE")
    c.drawString(ml + col_fr + 3 * mm,           y_hdr_bottom + 2, "SPECIFICATION")
    c.drawString(ml + col_fr + col_en + 3 * mm,  y_hdr_bottom + 2, "VALEUR / VALUE")
    c.setFillColor(_BLACK)
    y = y_hdr_bottom

    for i, (fr, en, val) in enumerate(rows):
        y = _draw_info_row(c, ml, mr, y, fr, en, val, striped=(i % 2 == 0))

    # Cadre global du tableau
    c.setStrokeColor(_BLACK)
    c.setLineWidth(0.6)
    c.rect(ml, y, inner_w, table_top - y, fill=0, stroke=1)

    # 5) Bloc note bilingue en dessous (optionnel, si particularité)
    particularite = fiche.get("particularite") or fiche.get("notes")
    if particularite and str(particularite).strip():
        y -= 8 * mm
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(_DARK)
        c.drawString(ml, y, "Particularités  /  Special requirements")
        c.setFillColor(_BLACK)
        y -= 3 * mm
        box_h = 20 * mm
        c.setStrokeColor(_BORDER)
        c.setLineWidth(0.4)
        c.rect(ml, y - box_h, inner_w, box_h, fill=0, stroke=1)
        style = ParagraphStyle("part", fontName="Helvetica", fontSize=8.5,
                               leading=11, textColor=_BLACK, alignment=TA_LEFT)
        p = Paragraph(str(particularite).replace("\n", "<br/>"), style)
        p.wrapOn(c, inner_w - 4 * mm, box_h - 2 * mm)
        p.drawOn(c, ml + 2 * mm, y - box_h + 2 * mm)

    # 6) Pied de page
    _draw_footer(c, ml, mr, fiche)

    c.showPage()
    c.save()
    return buf.getvalue()
