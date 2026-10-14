"""
MyPrint — étiquettes spécifiques : rendu PDF, pour les imprimantes qui ne
parlent pas ZPL (laser et jet d'encre de bureau).

Même mise en page JSON que le ZPL (`etiq_specifiques.py`), dessinée avec
reportlab. Les étiquettes sont posées à taille réelle sur des pages A4, en
planche : autant par page qu'il en tient, dans l'ordre de la série. Une
étiquette plus grande que l'A4 a sa propre page à son format.

L'aperçu exact (Labelary) reste celui du ZPL : sur PDF, la police est une
Helvetica, proche mais pas identique à la police 0 des Zebra.
"""

from __future__ import annotations

import io
import re

from reportlab.graphics.barcode import eanbc, qr
from reportlab.graphics.barcode.code128 import Code128
from reportlab.graphics.barcode.ecc200datamatrix import ECC200DataMatrix
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.services.etiq_specifiques import substituer

MARGE_A4 = 5 * mm
ECART = 2 * mm

# AI GS1 à longueur fixe : pas de séparateur FNC1 après eux.
_AI_FIXES = {"00", "01", "02", "03", "04", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "31", "32",
             "33", "34", "35", "36", "41"}
_AI_RE = re.compile(r"\((\d{2,4})\)([^(]*)")


def gs1_vers_code128(valeur: str) -> str:
    """« (00)3301…(10)LOT » → FNC1 + 00 3301… + 10 LOT, FNC1 après chaque AI
    de longueur variable suivi d'un autre AI."""
    groupes = _AI_RE.findall(re.sub(r"\s+", "", valeur or ""))
    if not groupes:
        return "\xf1" + re.sub(r"\D", "", valeur or "")
    out = "\xf1"
    for i, (ai, data) in enumerate(groupes):
        out += ai + data
        if i < len(groupes) - 1 and ai[:2] not in _AI_FIXES:
            out += "\xf1"
    return out


def _police(gras: bool) -> str:
    return "Helvetica-Bold" if gras else "Helvetica"


def _texte(c, e, valeurs, h_mm):
    t = substituer(e.get("valeur", ""), valeurs)
    taille_pt = e["taille"] * mm * 1.15   # hauteur de cellule ZPL ≈ corps de police
    c.setFont(_police(e.get("gras")), taille_pt)
    largeur = (e.get("largeur") or 0) * mm
    lignes = [t]
    if largeur:
        mots, lignes, cur = t.split(), [], ""
        for m in mots:
            essai = (cur + " " + m).strip()
            if cur and c.stringWidth(essai, _police(e.get("gras")), taille_pt) > largeur:
                lignes.append(cur)
                cur = m
            else:
                cur = essai
        if cur:
            lignes.append(cur)
        lignes = lignes[: max(1, e.get("lignes", 1))]
    x0, y0 = e["x"] * mm, (h_mm - e["y"]) * mm
    c.saveState()
    c.translate(x0, y0)
    if e.get("rotation"):
        c.rotate(-e["rotation"])
    for i, ligne in enumerate(lignes):
        y = -taille_pt * 0.82 - i * taille_pt * 1.05
        if largeur and e.get("align") == "centre":
            c.drawCentredString(largeur / 2, y, ligne)
        elif largeur and e.get("align") == "droite":
            c.drawRightString(largeur, y, ligne)
        else:
            c.drawString(0, y, ligne)
    c.restoreState()


def _code(c, e, valeurs, h_mm):
    sym = e["symbologie"]
    brut = substituer(e.get("valeur", ""), valeurs)
    module = e["module"] * mm
    hauteur = e["hauteur"] * mm
    x0, y_haut = e["x"] * mm, (h_mm - e["y"]) * mm
    c.saveState()
    c.translate(x0, y_haut)
    if e.get("rotation"):
        c.rotate(-e["rotation"])
    try:
        if sym in ("code128", "gs1_128"):
            data = gs1_vers_code128(brut) if sym == "gs1_128" else brut
            b = Code128(data, barWidth=module, barHeight=hauteur, quiet=False, humanReadable=False)
            b.drawOn(c, 0, -hauteur)
            if e.get("lisible", True):
                lisible = re.sub(r"\s+", "", brut) if sym == "gs1_128" else brut
                c.setFont("Helvetica", 2.6 * mm)
                c.drawCentredString(b.width / 2, -hauteur - 3 * mm, lisible)
        elif sym == "ean13":
            chiffres = re.sub(r"\D", "", brut)[:12].ljust(12, "0")
            w = eanbc.Ean13BarcodeWidget(chiffres, barWidth=module, barHeight=hauteur,
                                         humanReadable=bool(e.get("lisible", True)), quiet=False)
            x1, y1, x2, y2 = w.getBounds()
            d = Drawing(x2 - x1, y2 - y1)
            w.x, w.y = -x1, -y1
            d.add(w)
            d.drawOn(c, 0, -(y2 - y1))
        elif sym == "datamatrix":
            # Encodage explicite avant le dessin ; largeur = col_modules × barWidth.
            dm = ECC200DataMatrix(value=brut, barWidth=module)
            dm.validate()
            dm.encode()
            dm.x = dm.y = 0   # attendus par draw(), jamais posés par le constructeur
            dm.drawOn(c, 0, -dm.height)
        elif sym == "qrcode":
            w = qr.QrCodeWidget(brut, barLevel="M", barBorder=0)
            w.qr.make()
            cote = w.qr.getModuleCount() * module
            w = qr.QrCodeWidget(brut, barLevel="M", barBorder=0, barWidth=cote, barHeight=cote)
            d = Drawing(cote, cote)
            d.add(w)
            d.drawOn(c, 0, -cote)
    except Exception as err:
        c.setFont("Helvetica", 2.5 * mm)
        c.drawString(0, -3 * mm, f"Code invalide : {str(err)[:60]}")
    c.restoreState()


def _cadre(c, e, h_mm):
    t = e["epaisseur"] * mm
    x, y = e["x"] * mm, (h_mm - e["y"] - e["hauteur"]) * mm
    w, h = e["largeur"] * mm, e["hauteur"] * mm
    r = (e.get("arrondi") or 0) / 8 * min(w, h) / 2
    if e.get("plein"):
        c.roundRect(x, y, w, h, r, stroke=0, fill=1)
    else:
        c.setLineWidth(t)
        c.roundRect(x + t / 2, y + t / 2, max(0.1, w - t), max(0.1, h - t), r, stroke=1, fill=0)


def _ligne(c, e, h_mm):
    t, l = e["epaisseur"] * mm, e["longueur"] * mm
    x, y_haut = e["x"] * mm, (h_mm - e["y"]) * mm
    if e["orientation"] == "v":
        c.rect(x, y_haut - l, t, l, stroke=0, fill=1)
    else:
        c.rect(x, y_haut - t, l, t, stroke=0, fill=1)


def dessiner_etiquette(c, layout: dict, largeur_mm: float, hauteur_mm: float, valeurs: dict) -> None:
    """Dessine une étiquette avec son coin bas-gauche à l'origine courante."""
    c.saveState()
    p = c.beginPath()
    p.rect(0, 0, largeur_mm * mm, hauteur_mm * mm)
    c.clipPath(p, stroke=0, fill=0)
    c.setFillColorRGB(0, 0, 0)
    c.setStrokeColorRGB(0, 0, 0)
    for e in layout.get("elements", []):
        typ = e.get("type")
        if typ == "texte":
            if e.get("inverse"):
                c.setFillColorRGB(1, 1, 1)
            _texte(c, e, valeurs, hauteur_mm)
            c.setFillColorRGB(0, 0, 0)
        elif typ == "code_barre":
            _code(c, e, valeurs, hauteur_mm)
        elif typ == "cadre":
            _cadre(c, e, hauteur_mm)
        elif typ == "ligne":
            _ligne(c, e, hauteur_mm)
    c.restoreState()


def rendre_pdf(layout: dict, largeur_mm: float, hauteur_mm: float, valeurs_serie: list[dict],
               exemplaires: int = 1) -> bytes:
    """PDF de toute la série : planche A4, étiquettes à taille réelle."""
    etiquettes = [v for v in valeurs_serie for _ in range(max(1, int(exemplaires)))]
    buf = io.BytesIO()
    lw, lh = largeur_mm * mm, hauteur_mm * mm
    pw, ph = A4
    if lw > pw - 2 * MARGE_A4 or lh > ph - 2 * MARGE_A4:
        # Plus grande que l'A4 : une page au format de l'étiquette.
        c = canvas.Canvas(buf, pagesize=(lw, lh))
        for vals in etiquettes:
            dessiner_etiquette(c, layout, largeur_mm, hauteur_mm, vals)
            c.showPage()
        c.save()
        return buf.getvalue()
    cols = max(1, int((pw - 2 * MARGE_A4 + ECART) // (lw + ECART)))
    rangs = max(1, int((ph - 2 * MARGE_A4 + ECART) // (lh + ECART)))
    par_page = cols * rangs
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle("Étiquettes MySifa")
    for i, vals in enumerate(etiquettes):
        if i and i % par_page == 0:
            c.showPage()
        k = i % par_page
        col, rang = k % cols, k // cols
        x = MARGE_A4 + col * (lw + ECART)
        y = ph - MARGE_A4 - (rang + 1) * lh - rang * ECART
        c.saveState()
        c.translate(x, y)
        # Repère de découpe discret autour de chaque étiquette
        c.setStrokeColorRGB(0.75, 0.75, 0.75)
        c.setLineWidth(0.3)
        c.rect(0, 0, lw, lh, stroke=1, fill=0)
        dessiner_etiquette(c, layout, largeur_mm, hauteur_mm, vals)
        c.restoreState()
    c.save()
    return buf.getvalue()
