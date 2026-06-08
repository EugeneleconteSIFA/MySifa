"""
Générateur PDF — Fiche de Non-conformité SIFA
Calqué sur le modèle "Fiche NON CONFORMITE" version V1-07/2024.
"""
from __future__ import annotations

from io import BytesIO
from typing import Any, Optional, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_LEFT

_BLACK = colors.black
_WHITE = colors.white
_GRAY_BG = colors.HexColor("#F2F2F2")
_BORDER = colors.HexColor("#333333")
_ACCENT = colors.HexColor("#1F4E79")

W, H = A4


_TYPE_LABELS = {
    "interne": "Interne",
    "client": "Client",
    "fournisseur": "Fournisseur",
    "logistique": "Logistique",
}
_GRAVITE_LABELS = {
    "mineure": "Mineure",
    "majeure": "Majeure",
    "critique": "Critique",
}
_STATUT_LABELS = {
    "ouverte": "Ouverte",
    "en_analyse": "En analyse",
    "action_corrective": "Action corrective",
    "en_verification": "En vérification",
    "cloturee": "Clôturée",
}


def _v(val: Any) -> str:
    if val is None or val == "":
        return ""
    return str(val)


def _fmt_date(s: Optional[str]) -> str:
    if not s:
        return ""
    s = str(s)
    if len(s) >= 10 and s[4] == "-":
        return f"{s[8:10]}/{s[5:7]}/{s[0:4]}"
    return s


def _cell(c: canvas.Canvas, x: float, y: float, w: float, h: float,
          bg: Optional[colors.Color] = None, border: bool = True) -> None:
    if bg:
        c.setFillColor(bg)
        c.rect(x, y, w, h, fill=1, stroke=0)
    if border:
        c.setStrokeColor(_BORDER)
        c.setLineWidth(0.4)
        c.rect(x, y, w, h, fill=0, stroke=1)
    c.setFillColor(_BLACK)


def _label(c: canvas.Canvas, x: float, y: float, text: str, size: float = 7.5, bold: bool = True) -> None:
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    c.setFillColor(_BLACK)
    c.drawString(x, y, text)


def _value(c: canvas.Canvas, x: float, y: float, text: str, size: float = 9, bold: bool = False) -> None:
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    c.setFillColor(_BLACK)
    c.drawString(x, y, _v(text))


def _multiline(c: canvas.Canvas, x: float, y: float, w: float, h: float,
               text: str, font_size: float = 9, leading: float = 11) -> None:
    style = ParagraphStyle(
        "nc_block", fontName="Helvetica", fontSize=font_size, leading=leading,
        textColor=_BLACK, alignment=TA_LEFT,
    )
    p = Paragraph((text or "").replace("\n", "<br/>"), style)
    pw, ph = p.wrap(w - 4 * mm, h)
    p.drawOn(c, x + 2 * mm, y + h - ph - 2 * mm)


def render_nc_pdf(nc: dict) -> bytes:
    """Construit le PDF d'une fiche NC et retourne les bytes."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    margin = 15 * mm
    inner_w = W - 2 * margin
    y = H - margin

    # ── Bandeau supérieur ─────────────────────────────────────────────
    _label(c, margin, y - 8, "SIFA", size=14, bold=True)
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#555555"))
    c.drawString(margin, y - 22, "45 rue Rollin — 59100 Roubaix")

    # Version (haut droite)
    c.setFont("Helvetica", 7.5)
    c.drawRightString(W - margin, y - 8, "Version : V1-07/2024")
    c.setFillColor(_BLACK)

    # Titre central
    y -= 38
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(W / 2, y, "Fiche de Non-conformité")

    y -= 18
    c.setFont("Helvetica-Bold", 11)
    numero = nc.get("numero") or ""
    ar = nc.get("numero_ar")
    if ar and ar not in numero:
        title = f"N° {numero}  —  AR {ar}"
    else:
        title = f"N° {numero}"
    c.drawCentredString(W / 2, y, title)

    # Statut + gravité en pastille
    y -= 16
    statut_lbl = _STATUT_LABELS.get(nc.get("statut") or "", nc.get("statut") or "")
    gravite_lbl = _GRAVITE_LABELS.get(nc.get("gravite") or "", nc.get("gravite") or "")
    type_lbl = _TYPE_LABELS.get(nc.get("type_nc") or "", nc.get("type_nc") or "")
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#666666"))
    c.drawCentredString(W / 2, y, f"Type : {type_lbl}   ·   Gravité : {gravite_lbl}   ·   Statut : {statut_lbl}")
    c.setFillColor(_BLACK)

    y -= 14
    # ── Ligne 1 : Date / Service ──────────────────────────────────────
    row_h = 14
    col_w = inner_w / 2
    _cell(c, margin, y - row_h, col_w, row_h, bg=_GRAY_BG)
    _label(c, margin + 3, y - 10, "DATE :")
    _value(c, margin + 30, y - 10, _fmt_date(nc.get("date_nc") or nc.get("created_at", "")[:10]))
    _cell(c, margin + col_w, y - row_h, col_w, row_h, bg=_GRAY_BG)
    _label(c, margin + col_w + 3, y - 10, "SERVICE CONCERNÉ :")
    _value(c, margin + col_w + 90, y - 10, nc.get("service_concerne") or "")

    y -= row_h
    # ── Ligne 2 : Émetteur ────────────────────────────────────────────
    _cell(c, margin, y - row_h, inner_w, row_h)
    _label(c, margin + 3, y - 10, "ÉMETTEUR DE LA FICHE :")
    _value(c, margin + 110, y - 10, nc.get("emetteur_nom") or nc.get("created_by_nom") or "")

    y -= row_h + 4
    # ── Description ───────────────────────────────────────────────────
    block_h = 36
    _cell(c, margin, y - block_h, inner_w, block_h)
    _label(c, margin + 3, y - 10, "Description de la non-conformité :")
    _multiline(c, margin + 2, y - block_h, inner_w - 4, block_h - 12, nc.get("description") or "", font_size=8.5, leading=10.5)

    y -= block_h + 4
    # ── Type NC (déjà rappelé en haut) + Client + Date ───────────────
    _cell(c, margin, y - row_h, inner_w, row_h, bg=_GRAY_BG)
    _label(c, margin + 3, y - 10, "Type de NC :")
    _value(c, margin + 70, y - 10, type_lbl)

    y -= row_h
    half = inner_w / 2
    _cell(c, margin, y - row_h, half, row_h)
    _label(c, margin + 3, y - 10, "Nom client / fournisseur :")
    _value(c, margin + 110, y - 10, nc.get("client_fournisseur") or "")
    _cell(c, margin + half, y - row_h, half, row_h)
    _label(c, margin + half + 3, y - 10, "Date de la NC :")
    _value(c, margin + half + 75, y - 10, _fmt_date(nc.get("date_nc")))

    y -= row_h
    _cell(c, margin, y - row_h, half, row_h)
    _label(c, margin + 3, y - 10, "Référence client :")
    _value(c, margin + 75, y - 10, nc.get("ref_client") or "")
    _cell(c, margin + half, y - row_h, half, row_h)
    _label(c, margin + half + 3, y - 10, "Référence SIFA :")
    _value(c, margin + half + 75, y - 10, nc.get("no_dossier") or "")

    y -= row_h
    _cell(c, margin, y - row_h, inner_w, row_h)
    _label(c, margin + 3, y - 10, "Descriptif produit :")
    _value(c, margin + 85, y - 10, nc.get("descriptif_produit") or "")

    y -= row_h
    _cell(c, margin, y - row_h, half, row_h)
    _label(c, margin + 3, y - 10, "Quantité concernée :")
    _value(c, margin + 90, y - 10, nc.get("quantite_concernee") or "")
    _cell(c, margin + half, y - row_h, half, row_h)
    _label(c, margin + half + 3, y - 10, "Coût estimé (€) :")
    _value(c, margin + half + 80, y - 10,
           f"{nc['cout_estime']:.2f}" if nc.get("cout_estime") is not None else "")

    y -= row_h + 4
    # ── Analyse des causes ────────────────────────────────────────────
    block_h = 50
    services = nc.get("services_impliques") or []
    if isinstance(services, str):
        services = [s.strip() for s in services.split(",") if s.strip()]
    services_line = "   -   ".join(services) if services else ""
    _cell(c, margin, y - block_h, inner_w, block_h)
    _label(c, margin + 3, y - 10, "Analyse des causes :")
    if services_line:
        c.setFont("Helvetica-Bold", 8)
        c.drawString(margin + 100, y - 10, services_line)
    _multiline(c, margin + 2, y - block_h, inner_w - 4, block_h - 12,
               nc.get("analyse_causes") or "", font_size=8.5, leading=10.5)

    y -= block_h + 4
    # ── Action corrective ─────────────────────────────────────────────
    block_h = 50
    _cell(c, margin, y - block_h, inner_w, block_h)
    _label(c, margin + 3, y - 10, "Action corrective :")
    _multiline(c, margin + 2, y - block_h, inner_w - 4, block_h - 12,
               nc.get("action_corrective") or "", font_size=8.5, leading=10.5)

    y -= block_h
    # ── Pilote ────────────────────────────────────────────────────────
    _cell(c, margin, y - row_h, inner_w, row_h, bg=_GRAY_BG)
    _label(c, margin + 3, y - 10, "Pilote :")
    _value(c, margin + 50, y - 10, nc.get("pilote_nom") or "")

    y -= row_h + 4
    # ── Action préventive ─────────────────────────────────────────────
    block_h = 50
    _cell(c, margin, y - block_h, inner_w, block_h)
    _label(c, margin + 3, y - 10, "Action préventive à mettre en place :")
    _multiline(c, margin + 2, y - block_h, inner_w - 4, block_h - 12,
               nc.get("action_preventive") or "", font_size=8.5, leading=10.5)

    y -= block_h + 6
    # ── Clôture + validations ─────────────────────────────────────────
    sig_h = 26
    third = inner_w / 3
    _cell(c, margin, y - sig_h, third, sig_h, bg=_GRAY_BG)
    _label(c, margin + 3, y - 9, "Date de clôture NC")
    _value(c, margin + 3, y - 20, _fmt_date(nc.get("date_cloture")))

    _cell(c, margin + third, y - sig_h, third, sig_h)
    _label(c, margin + third + 3, y - 9, "Validation Direction Qualité")
    vq = nc.get("validation_qualite_nom")
    if vq:
        c.setFont("Helvetica", 8)
        c.drawString(margin + third + 3, y - 19, vq)
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#666666"))
        c.drawString(margin + third + 3, y - 25, _fmt_date(nc.get("validation_qualite_at", "")[:10]))
        c.setFillColor(_BLACK)

    _cell(c, margin + 2 * third, y - sig_h, third, sig_h)
    _label(c, margin + 2 * third + 3, y - 9, "Validation Direction Industrielle")
    vi = nc.get("validation_industrielle_nom")
    if vi:
        c.setFont("Helvetica", 8)
        c.drawString(margin + 2 * third + 3, y - 19, vi)
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#666666"))
        c.drawString(margin + 2 * third + 3, y - 25, _fmt_date(nc.get("validation_industrielle_at", "")[:10]))
        c.setFillColor(_BLACK)

    # ── Footer ────────────────────────────────────────────────────────
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#666666"))
    c.drawCentredString(W / 2, 18 * mm, "Siège social : 45 rue Rollin — 59100 Roubaix — France")
    c.drawCentredString(W / 2, 12 * mm, "TVA FR 26 340 885 — SIRET 340 885 003 00061")
    c.drawCentredString(W / 2, 7 * mm, "SAS au capital de 204 440 €uros — R.C.S 340 885 003 LILLE METROPOLE")

    c.showPage()
    c.save()
    return buf.getvalue()
