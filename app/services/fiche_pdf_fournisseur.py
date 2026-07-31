"""
Générateur PDF — Fiche produit FOURNISSEUR (bilingue FR / EN)

Version à destination des fournisseurs SIFA lors des appels d'offres.
Reprend la charte graphique du PDF client (fiche_pdf_client) mais avec
les données brutes de la fiche produit MyAO (ao_produits) — pas de
classification par dictionnaire, on affiche ce qui est saisi dans la
fiche produit.

En-tête : logo SIFA + coordonnées.
Corps : sections de la fiche produit avec libellés bilingues FR/EN.
Pied de page : mentions de confidentialité + date d'édition.

Mise en page — une seule page A4
--------------------------------
Le document est construit en deux temps : on décrit d'abord tous les blocs
(``_build_blocks``), on mesure la hauteur qu'ils prendraient à l'échelle 1,
puis on en déduit un facteur de compression ``k`` appliqué aux hauteurs de
ligne, aux bandeaux de titre et aux interlignes. Une fiche complète tient
donc sur une seule page, sans jamais rogner une information : c'est la
densité qui s'ajuste, pas le contenu. Les polices suivent ``k`` de façon
amortie pour rester lisibles, et un plancher (``_K_MIN``) autorise en
dernier recours un débord sur une 2e page plutôt qu'un texte illisible.
"""
from __future__ import annotations

import os
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
_ACCENT_BG  = colors.HexColor("#e6f6fa")

W, H = A4

_PARIS = ZoneInfo("Europe/Paris")

# Marge basse : le bandeau de pied de page commence à 22 mm.
_CONTENT_BOTTOM = 24 * mm

# Compression minimale acceptable avant de préférer une 2e page.
_K_MIN = 0.62


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


def _int(val: Any) -> int:
    try:
        return int(float(str(val).replace(",", ".")))
    except (TypeError, ValueError):
        return 0


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


_ENROULEMENT_FR = {
    "interieur": "Intérieur",
    "intérieur": "Intérieur",
    "exterieur": "Extérieur",
    "extérieur": "Extérieur",
    "int": "Intérieur",
    "ext": "Extérieur",
}


def _tr_enroulement(v: Any) -> tuple[str, str]:
    if not v:
        return ("—", "—")
    s = str(v).strip()
    fr = _ENROULEMENT_FR.get(s.lower(), s.capitalize())
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
        max_w = 52 * mm
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
    y_top = H - 11 * mm
    logo_h = 15 * mm
    _draw_logo(c, ml, y_top, logo_h)

    x_right = W - mr
    c.setFillColor(_DARK)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawRightString(x_right, y_top - 4, SIFA_NAME)
    c.setFont("Helvetica", 7.5)
    c.setFillColor(_MUTED)
    c.drawRightString(x_right, y_top - 13, SIFA_ADDRESS)
    c.drawRightString(x_right, y_top - 22, f"Tél. : {SIFA_PHONE}")
    c.drawRightString(x_right, y_top - 31, SIFA_EMAIL)

    y_line = y_top - max(logo_h, 31) - 3 * mm
    c.setFillColor(_YELLOW)
    c.rect(ml, y_line, W - ml - mr, 1.2 * mm, fill=1, stroke=0)
    c.setFillColor(_BLACK)
    return y_line - 2 * mm


def _draw_title(c: canvas.Canvas, y: float) -> float:
    c.setFillColor(_BLACK)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W / 2, y - 11, "FICHE PRODUIT — APPEL D'OFFRES")
    c.setFillColor(_MUTED)
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(W / 2, y - 22, "Product data sheet — Request for quotation")
    c.setFillColor(_BLACK)
    return y - 29


def _draw_ref_block(c: canvas.Canvas, ml: float, mr: float, y: float,
                    produit: dict) -> float:
    inner_w = W - ml - mr
    block_h = 12 * mm
    y_bottom = y - block_h

    c.setStrokeColor(_BLACK)
    c.setLineWidth(0.6)
    c.setFillColor(_LIGHT_GRAY)
    c.rect(ml, y_bottom, inner_w, block_h, fill=1, stroke=1)
    c.setFillColor(_BLACK)

    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(_MUTED)
    c.drawString(ml + 4 * mm, y - 4.4 * mm, "Référence produit  /  Product reference")
    c.setFillColor(_BLACK)
    c.setFont("Helvetica-Bold", 13)
    ref = _clean_reference(produit.get("ref"))
    c.drawString(ml + 4 * mm, y - 9.6 * mm, ref)

    # Nom du client final volontairement omis dans le PDF destiné au
    # fournisseur (confidentialité — le fournisseur consulté n'a pas à
    # connaître le client final SIFA).

    return y_bottom - 3 * mm


# ── Métriques de mise en page ───────────────────────────────────────
def _metrics(k: float) -> dict:
    """Hauteurs et corps de police pour un facteur de compression donné.

    Les polices suivent ``k`` de façon amortie (fk) : une page dense reste
    lisible parce que le texte ne rétrécit que de moitié par rapport à la
    géométrie.
    """
    fk = 0.55 + 0.45 * k
    return {
        "k": k,
        "title_h":   6.2 * mm * k,
        "row_h":     6.8 * mm * k,
        "color_h":   7.8 * mm * k,
        "gap":       4.2 * mm * k,
        "f_title":    9.0 * fk,
        "f_title_en": 7.4 * fk,
        "f_lbl":      8.2 * fk,
        "f_lbl_en":   6.8 * fk,
        "f_val":      8.5 * fk,
        "f_val_en":   6.8 * fk,
    }


def _fit_size(c: canvas.Canvas, txt: str, base: float, font: str, max_w: float,
              floor_ratio: float = 0.72) -> float:
    """Réduit le corps jusqu'à ce que le texte tienne, sans descendre trop bas."""
    if not txt:
        return base
    size = base
    floor = base * floor_ratio
    while size > floor and c.stringWidth(txt, font, size) > max_w:
        size -= 0.25
    return max(size, floor)


def _ellipsize(c: canvas.Canvas, txt: str, font: str, size: float, max_w: float) -> str:
    if c.stringWidth(txt, font, size) <= max_w:
        return txt
    out = txt
    while out and c.stringWidth(out + "…", font, size) > max_w:
        out = out[:-1]
    return (out + "…") if out else ""


# ── Primitives de section ───────────────────────────────────────────
def _section_title(c: canvas.Canvas, x: float, y: float,
                   fr: str, en: str, width: float, m: dict) -> float:
    """Bandeau de section : accent + titre FR + sous-titre EN italique."""
    h_band = m["title_h"]
    y_bottom = y - h_band

    c.setFillColor(_LIGHT_GRAY)
    c.rect(x, y_bottom, width, h_band, fill=1, stroke=0)
    c.setFillColor(_ACCENT)
    c.rect(x, y_bottom, 2.6 * mm, h_band, fill=1, stroke=0)

    tx = x + 4.6 * mm
    max_w = width - 6 * mm
    s_fr = _fit_size(c, fr, m["f_title"], "Helvetica-Bold", max_w * 0.7)
    c.setFillColor(_DARK)
    c.setFont("Helvetica-Bold", s_fr)
    c.drawString(tx, y_bottom + h_band / 2 - s_fr * 0.34, fr)

    used = c.stringWidth(fr, "Helvetica-Bold", s_fr) + 2 * mm
    if en and en != fr:
        s_en = _fit_size(c, "/ " + en, m["f_title_en"], "Helvetica-Oblique",
                         max(max_w - used, 10))
        c.setFillColor(_MUTED)
        c.setFont("Helvetica-Oblique", s_en)
        c.drawString(tx + used,
                     y_bottom + h_band / 2 - s_en * 0.34,
                     _ellipsize(c, "/ " + en, "Helvetica-Oblique", s_en,
                                max(max_w - used, 10)))

    c.setFillColor(_BLACK)
    return y_bottom


def _draw_row(c: canvas.Canvas, x: float, y: float, width: float, m: dict,
              label_fr: str, label_en: str, value_fr: str, value_en: str,
              striped: bool = False) -> float:
    """Ligne bilingue compacte — label FR bold + EN italique dessous, valeur idem."""
    row_h = m["row_h"]
    col_lbl = width * 0.42
    col_val = width - col_lbl
    y_bottom = y - row_h

    if striped:
        c.setFillColor(_LIGHT_GRAY)
        c.rect(x, y_bottom, width, row_h, fill=1, stroke=0)

    c.setStrokeColor(_BORDER)
    c.setLineWidth(0.25)
    c.line(x + col_lbl, y_bottom, x + col_lbl, y)
    c.setLineWidth(0.3)
    c.line(x, y_bottom, x + width, y_bottom)

    has_lbl_en = bool(label_en) and label_en != label_fr
    has_val_en = bool(value_en) and value_en != value_fr
    two_lines = has_lbl_en or has_val_en

    y_l1 = y - row_h * (0.46 if two_lines else 0.62)
    y_l2 = y - row_h * 0.84
    y_mid = y - row_h * 0.62

    pad = 2.2 * mm
    max_lbl_w = col_lbl - 2 * pad
    max_val_w = col_val - 2 * pad

    # Label
    s = _fit_size(c, label_fr, m["f_lbl"], "Helvetica-Bold", max_lbl_w)
    c.setFillColor(_DARK)
    c.setFont("Helvetica-Bold", s)
    c.drawString(x + pad, y_l1 if has_lbl_en else (y_l1 if two_lines else y_mid), label_fr)
    if has_lbl_en:
        s2 = _fit_size(c, label_en, m["f_lbl_en"], "Helvetica-Oblique", max_lbl_w)
        c.setFillColor(_MUTED)
        c.setFont("Helvetica-Oblique", s2)
        c.drawString(x + pad, y_l2,
                     _ellipsize(c, label_en, "Helvetica-Oblique", s2, max_lbl_w))

    # Valeur
    xv = x + col_lbl + pad
    sv = _fit_size(c, value_fr, m["f_val"], "Helvetica-Bold", max_val_w)
    c.setFillColor(_BLACK)
    c.setFont("Helvetica-Bold", sv)
    c.drawString(xv, y_l1 if two_lines else y_mid,
                 _ellipsize(c, value_fr, "Helvetica-Bold", sv, max_val_w))
    if has_val_en:
        sv2 = _fit_size(c, value_en, m["f_val_en"], "Helvetica-Oblique", max_val_w)
        c.setFillColor(_MUTED)
        c.setFont("Helvetica-Oblique", sv2)
        c.drawString(xv, y_l2,
                     _ellipsize(c, value_en, "Helvetica-Oblique", sv2, max_val_w))

    c.setFillColor(_BLACK)
    return y_bottom


def _draw_color_row(c: canvas.Canvas, x: float, y: float, width: float, m: dict,
                    num: int, couleur: str, area: str, striped: bool = False) -> float:
    """Ligne « couleur d'impression » : pastille numérotée + encre + zone.

    La zone d'impression est écrite sur toute la largeur du bloc (et non dans
    une colonne de droite) : une mention du type « Spot 2 x 18,9 mm toutes les
    10 étiquettes » doit rester lisible d'un coup d'œil par le fournisseur.
    """
    row_h = m["color_h"]
    y_bottom = y - row_h

    if striped:
        c.setFillColor(_LIGHT_GRAY)
        c.rect(x, y_bottom, width, row_h, fill=1, stroke=0)
    c.setStrokeColor(_BORDER)
    c.setLineWidth(0.3)
    c.line(x, y_bottom, x + width, y_bottom)

    pad = 2.2 * mm
    y_name = y - row_h * 0.42
    y_zone = y - row_h * 0.80

    chip_h = min(row_h * 0.30, 3.6 * mm)
    chip_w = max(chip_h * 1.35, 4.0 * mm)
    chip_y = y_name - chip_h * 0.24
    c.setFillColor(_ACCENT)
    c.roundRect(x + pad, chip_y, chip_w, chip_h, 0.9 * mm, fill=1, stroke=0)
    c.setFillColor(_WHITE)
    fs = min(m["f_val_en"], chip_h * 0.62)
    c.setFont("Helvetica-Bold", fs)
    c.drawCentredString(x + pad + chip_w / 2, chip_y + chip_h * 0.5 - fs * 0.35, str(num))

    tx = x + pad + chip_w + 1.8 * mm
    max_w = width - (tx - x) - pad
    lbl = couleur or "Couleur non précisée / Colour not specified"
    s = _fit_size(c, lbl, m["f_val"], "Helvetica-Bold", max_w)
    c.setFillColor(_BLACK)
    c.setFont("Helvetica-Bold", s)
    c.drawString(tx, y_name, _ellipsize(c, lbl, "Helvetica-Bold", s, max_w))

    zone = f"Zone / Printing area : {area}" if area else "Zone / Printing area : —"
    sz = _fit_size(c, zone, m["f_val_en"], "Helvetica-Oblique", max_w)
    c.setFillColor(_MUTED)
    c.setFont("Helvetica-Oblique", sz)
    c.drawString(tx, y_zone, _ellipsize(c, zone, "Helvetica-Oblique", sz, max_w))

    c.setFillColor(_BLACK)
    return y_bottom


def _draw_note_row(c: canvas.Canvas, x: float, y: float, width: float, m: dict,
                   fr: str, en: str, striped: bool = False) -> float:
    """Ligne pleine largeur sans colonne de label (message d'état)."""
    row_h = m["row_h"]
    y_bottom = y - row_h
    if striped:
        c.setFillColor(_LIGHT_GRAY)
        c.rect(x, y_bottom, width, row_h, fill=1, stroke=0)
    c.setStrokeColor(_BORDER)
    c.setLineWidth(0.3)
    c.line(x, y_bottom, x + width, y_bottom)

    pad = 2.2 * mm
    maxw = width - 2 * pad
    s = _fit_size(c, fr, m["f_lbl"], "Helvetica-Bold", maxw)
    c.setFillColor(_DARK)
    c.setFont("Helvetica-Bold", s)
    c.drawString(x + pad, y - row_h * 0.46, _ellipsize(c, fr, "Helvetica-Bold", s, maxw))
    if en and en != fr:
        s2 = _fit_size(c, en, m["f_lbl_en"], "Helvetica-Oblique", maxw)
        c.setFillColor(_MUTED)
        c.setFont("Helvetica-Oblique", s2)
        c.drawString(x + pad, y - row_h * 0.84,
                     _ellipsize(c, en, "Helvetica-Oblique", s2, maxw))
    c.setFillColor(_BLACK)
    return y_bottom


def _section_box(c: canvas.Canvas, x: float, y_top: float, width: float, height: float) -> None:
    c.setStrokeColor(_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y_top - height, width, height, fill=0, stroke=1)


# ── Modèle de blocs (mesure puis rendu) ─────────────────────────────
def _kv(label_fr: str, label_en: str, value_fr: Any, value_en: Any = None) -> tuple:
    return ("kv", label_fr, label_en, str(value_fr), str(value_en if value_en is not None else value_fr))


def _color(num: int, couleur: str, area: str) -> tuple:
    return ("color", num, couleur, area)


def _note(fr: str, en: str) -> tuple:
    return ("note", fr, en)


def _keep(rows: list[tuple]) -> list[tuple]:
    """Retire les lignes kv dont la valeur FR ET EN sont vides ou '—'."""
    def empty(v):
        return v is None or str(v).strip() in ("", "—")
    out = []
    for r in rows:
        if r[0] == "kv" and empty(r[3]) and empty(r[4]):
            continue
        out.append(r)
    return out


def _rows_h(rows: list[tuple], m: dict) -> float:
    total = 0.0
    for r in rows:
        total += m["color_h"] if r[0] == "color" else m["row_h"]
    return total


def _draw_rows(c: canvas.Canvas, x: float, y: float, width: float, m: dict,
               rows: list[tuple]) -> float:
    for i, r in enumerate(rows):
        striped = (i % 2 == 0)
        if r[0] == "color":
            y = _draw_color_row(c, x, y, width, m, r[1], r[2], r[3], striped)
        elif r[0] == "note":
            y = _draw_note_row(c, x, y, width, m, r[1], r[2], striped)
        else:
            y = _draw_row(c, x, y, width, m, r[1], r[2], r[3], r[4], striped)
    return y


def _block_height(b: dict, m: dict) -> float:
    if b["t"] == "full":
        return m["title_h"] + _rows_h(b["rows"], m) + m["gap"]
    if b["t"] == "two":
        return m["title_h"] + max(_rows_h(b["left"][1], m),
                                  _rows_h(b["right"][1], m)) + m["gap"]
    if b["t"] == "text":
        return m["title_h"] + b["h1"] * m["k"] + 4 * mm * m["k"] + m["gap"]
    return 0.0


def _draw_block(c: canvas.Canvas, ml: float, mr: float, y: float, b: dict,
                m: dict) -> float:
    inner_w = W - ml - mr
    if b["t"] == "full":
        y_start = y
        y = _section_title(c, ml, y, b["title"][0], b["title"][1], inner_w, m)
        y = _draw_rows(c, ml, y, inner_w, m, b["rows"])
        _section_box(c, ml, y_start, inner_w, y_start - y)
        return y - m["gap"]

    if b["t"] == "two":
        gap_x = 5 * mm
        col_w = (inner_w - gap_x) / 2
        x_l, x_r = ml, ml + col_w + gap_x
        body_h = max(_rows_h(b["left"][1], m), _rows_h(b["right"][1], m))
        y_start = y
        for x, (title, rows) in ((x_l, b["left"]), (x_r, b["right"])):
            if not rows:
                continue
            yy = _section_title(c, x, y_start, title[0], title[1], col_w, m)
            _draw_rows(c, x, yy, col_w, m, rows)
            _section_box(c, x, y_start, col_w, m["title_h"] + body_h)
        return y_start - m["title_h"] - body_h - m["gap"]

    if b["t"] == "text":
        y_start = y
        y = _section_title(c, ml, y, b["title"][0], b["title"][1], inner_w, m)
        box_h = b["h1"] * m["k"] + 4 * mm * m["k"]
        y_box = y - box_h
        style = ParagraphStyle("part", fontName="Helvetica",
                               fontSize=max(6.6, 9 * m["k"]),
                               leading=max(8.0, 11 * m["k"]),
                               textColor=_BLACK, alignment=TA_LEFT)
        p = Paragraph(str(b["text"]).replace("\n", "<br/>"), style)
        _, ph = p.wrap(inner_w - 5 * mm, box_h)
        p.drawOn(c, ml + 2.5 * mm, y_box + max(box_h - ph - 1.5 * mm, 1.5 * mm))
        _section_box(c, ml, y_start, inner_w, y_start - y_box)
        return y_box - m["gap"]

    return y


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
              "dans le cadre de l'appel d'offres SIFA. Toute diffusion à un tiers est interdite. "
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


def _mp_label(mp: dict | None) -> str:
    """Formatte une matière première depuis matieres_map."""
    if not mp:
        return "—"
    ref = str(mp.get("reference") or "").strip()
    des = str(mp.get("designation") or "").strip()
    if ref and des:
        return f"{ref} — {des}"
    return ref or des or "—"


def _plural(n: int, fr: str, en: str) -> tuple[str, str]:
    s = "s" if n > 1 else ""
    return (f"{n} {fr}{s}", f"{n} {en}{s}")


def _face_rows(details: list[dict], nb: int, face: str) -> list[tuple]:
    """Lignes d'un bloc recto ou verso : une pastille par couleur."""
    rows: list[tuple] = []
    details = [d for d in (details or []) if isinstance(d, dict)]
    for i, d in enumerate(details, 1):
        rows.append(_color(i, str(d.get("couleur") or "").strip(),
                           str(d.get("printing_area") or "").strip()))
    if not rows:
        if nb > 0:
            fr, en = _plural(nb, "couleur annoncée", "colour declared")
            rows.append(_note(fr + " — détail non renseigné",
                              en + " — no breakdown provided"))
        else:
            rows.append(_note(
                "Aucune impression au " + face,
                "No printing on the " + ("front" if face == "recto" else "back")))
    return rows


def _build_blocks(c: canvas.Canvas, produit: dict, matieres_map: dict) -> list[dict]:
    """Décrit tous les blocs de la fiche, sans rien dessiner."""
    fiche = produit.get("fiche") or {}
    et   = fiche.get("etiquette") or {}
    ech  = fiche.get("echenillage") or {}
    mat  = fiche.get("matiere") or {}
    bob  = fiche.get("bobines") or {}
    imp  = fiche.get("impressions_detail") or {}
    cond = fiche.get("conditionnement") or {}
    cart = cond.get("carton") or {}
    pal  = cond.get("palette") or {}

    blocks: list[dict] = []

    # ── Infos générales ────────────────────────────────────────────
    type_fr, type_en = _tr_type_produit(fiche.get("type_produit"))
    imp_fr, imp_en = _tr_bool(fiche.get("impressions"))
    rows_1 = [
        _kv("Type de produit", "Product type", type_fr, type_en),
        _kv("Impressions", "Printing", imp_fr, imp_en),
    ]
    laize, longueur = et.get("laize"), et.get("longueur")
    if laize is not None and longueur is not None:
        try:
            fmt_eti = f"{int(float(laize))} × {int(float(longueur))} mm"
            rows_1.append(_kv("Format étiquette", "Label format", fmt_eti))
        except (TypeError, ValueError):
            pass
    if fiche.get("impressions"):
        if imp.get("aplat"):
            pct = imp.get("aplat_pourcent")
            rows_1.append(_kv("Aplat", "Solid ink coverage",
                              f"Oui — {_num(pct)} %", f"Yes — {_num(pct)}%"))
        else:
            rows_1.append(_kv("Aplat", "Solid ink coverage", "Non", "No"))
    blocks.append({"t": "full", "title": ("Infos générales", "General information"),
                   "rows": _keep(rows_1)})

    # ── Étiquette + Échenillage ────────────────────────────────────
    rows_2 = _keep([
        _kv("Laize", "Width", _num(et.get("laize"), " mm")),
        _kv("Longueur", "Length", _num(et.get("longueur"), " mm")),
        _kv("Rayon", "Corner radius", _num(et.get("rayon"), " mm")),
        _kv("Perforation", "Perforation", _v(et.get("perforation"))),
    ])
    rows_3 = _keep([
        _kv("Espace à droite", "Right gap", _num(ech.get("droite"), " mm")),
        _kv("Espace à gauche", "Left gap", _num(ech.get("gauche"), " mm")),
        _kv("En avance", "Down gap", _num(ech.get("avance"), " mm")),
    ])
    if rows_2 or rows_3:
        blocks.append({"t": "two",
                       "left": (("Étiquette", "Label"), rows_2),
                       "right": (("Échenillage", "Matrix stripping"), rows_3)})

    # ── Matière + Bobines ──────────────────────────────────────────
    def mp_of(key: str, src: dict) -> str:
        val = src.get(key)
        if val is None or val == "":
            return "—"
        try:
            return _mp_label(matieres_map.get(int(val)))
        except (TypeError, ValueError):
            return "—"

    rows_4 = _keep([
        _kv("Frontal", "Facestock", mp_of("frontal_id", mat)),
        _kv("Adhésif", "Adhesive", mp_of("adhesif_id", mat)),
        _kv("Grammage adhésif", "Adhesive coat weight",
            _num(mat.get("grammage_adhesif"), " g/m²"),
            _num(mat.get("grammage_adhesif"), " gsm")),
        _kv("Glassine", "Release liner", mp_of("glassine_id", mat)),
        _kv("Couleur glassine", "Liner colour", _v(mat.get("couleur_glassine"))),
    ])
    enr_fr, enr_en = _tr_enroulement(bob.get("enroulement"))
    rows_5 = _keep([
        _kv("Diamètre mandrin", "Core diameter", _num(bob.get("diametre_mandrin"), " mm")),
        _kv("Enroulement", "Winding direction", enr_fr, enr_en),
        _kv("Diamètre bobine", "Roll diameter", _num(bob.get("diametre_bobine"), " mm")),
        _kv("Étiquettes / bobine", "Labels / roll", _num(bob.get("nb_etiquettes"))),
    ])
    if rows_4 or rows_5:
        blocks.append({"t": "two",
                       "left": (("Matière", "Material"), rows_4),
                       "right": (("Bobines", "Rolls"), rows_5)})

    # ── Impressions : une case recto, une case verso ───────────────
    if fiche.get("impressions"):
        nb_recto = _int(imp.get("recto"))
        nb_verso = _int(imp.get("verso"))
        d_recto = imp.get("recto_details") or []
        d_verso = imp.get("verso_details") or []
        n_r = len([d for d in d_recto if isinstance(d, dict)]) or nb_recto
        n_v = len([d for d in d_verso if isinstance(d, dict)]) or nb_verso
        t_r_fr, t_r_en = _plural(n_r, "couleur", "colour")
        t_v_fr, t_v_en = _plural(n_v, "couleur", "colour")
        blocks.append({
            "t": "two",
            "left": ((f"Recto — {t_r_fr}", f"Front — {t_r_en}"),
                     _face_rows(d_recto, nb_recto, "recto")),
            "right": ((f"Verso — {t_v_fr}", f"Back — {t_v_en}"),
                      _face_rows(d_verso, nb_verso, "verso")),
        })

    # ── Cartons + Palettes ─────────────────────────────────────────
    rows_7 = _keep([
        _kv("Type de carton", "Box type", mp_of("matiere_id", cart)),
        _kv("Bobines au sol", "Rolls per layer", _num(cart.get("bobines_sol"))),
        _kv("Nombre d'étages", "Number of layers", _num(cart.get("nb_etages"))),
        _kv("Bobines / carton", "Rolls / box", _num(cart.get("bobines_carton"))),
    ])
    rows_8 = _keep([
        _kv("Type de palette", "Pallet type", mp_of("matiere_id", pal)),
        _kv("Cartons au sol", "Boxes per layer", _num(pal.get("cartons_sol"))),
        _kv("Étages de cartons", "Number of layers", _num(pal.get("nb_etages"))),
        _kv("Cartons / palette", "Boxes / pallet", _num(pal.get("cartons_palette"))),
    ])
    if rows_7 or rows_8:
        blocks.append({"t": "two",
                       "left": (("Cartons", "Boxes"), rows_7),
                       "right": (("Palettes", "Pallets"), rows_8)})

    # ── Particularités ─────────────────────────────────────────────
    part = fiche.get("particularites")
    if part and str(part).strip():
        style = ParagraphStyle("measure", fontName="Helvetica", fontSize=9,
                               leading=11, alignment=TA_LEFT)
        p = Paragraph(str(part).replace("\n", "<br/>"), style)
        _, h1 = p.wrap(W - 30 * mm - 5 * mm, 200 * mm)
        blocks.append({"t": "text",
                       "title": ("Particularités", "Special requirements"),
                       "text": str(part), "h1": max(h1, 10 * mm)})

    return blocks


# ── Rendu principal ─────────────────────────────────────────────────
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

    Le document tient sur une seule page A4 : la densité des blocs est
    calculée avant le rendu en fonction du volume d'informations saisi.
    """
    matieres_map = matieres_map or {}

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    ref_clean = _clean_reference(produit.get("ref"))
    c.setTitle(f"Fiche produit fournisseur — {ref_clean}")
    c.setAuthor("SIFA")

    ml = mr = 15 * mm

    y = _draw_header(c, ml, mr)
    y = _draw_title(c, y)
    y = _draw_ref_block(c, ml, mr, y - 3 * mm, produit)

    blocks = _build_blocks(c, produit, matieres_map)

    # Facteur de compression : hauteur disponible / hauteur naturelle.
    m1 = _metrics(1.0)
    # Le dernier bloc ne consomme pas son interligne de fin : on le retire de
    # la mesure, sinon une fiche qui tient tout juste bascule sur 2 pages.
    need = max(sum(_block_height(b, m1) for b in blocks) - m1["gap"], 0.0)
    avail = (y - _CONTENT_BOTTOM) * 0.995
    k = 1.0 if need <= avail or need <= 0 else max(avail / need, _K_MIN)
    m = _metrics(k)

    for b in blocks:
        h = _block_height(b, m) - m["gap"]
        if y - h < _CONTENT_BOTTOM - 1 and y < H - 60 * mm:
            # Filet de sécurité : fiche hors norme (texte de particularités
            # très long). On préfère une 2e page à un contenu tronqué.
            _draw_footer(c, ml, mr, ao_reference)
            c.showPage()
            y = _draw_header(c, ml, mr)
        y = _draw_block(c, ml, mr, y, b, m)

    _draw_footer(c, ml, mr, ao_reference)
    c.showPage()
    c.save()
    return buf.getvalue()
