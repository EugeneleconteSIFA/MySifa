"""
Generation PDF -- Ordre de Fabrication depuis template vierge.

Utilise pour previsualiser les OFs importes via l'API (sans PDF uploade).
Template : data/of_template.pdf (sifa_pdf_cdi_of.pdf)
Dependances : reportlab (deja dans requirements.txt), pypdf
"""

from __future__ import annotations

import os
from io import BytesIO
from typing import Any, Optional

from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter

from config import BASE_DIR

# Chemin du template vierge (a deployer sur le VPS)
_TEMPLATE_PATH = os.path.join(BASE_DIR, "data", "of_template.pdf")

# Dimensions US Letter (page du template)
_PAGE_W = 612.0
_PAGE_H = 792.0


def _fmt(v: Any) -> str:
    """Formate une valeur pour l'affichage (None -> '', float entier -> sans decimale)."""
    if v is None or v == "":
        return ""
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v)


def _fmt_qte(v: Any) -> str:
    """Formate une quantite avec separateur milliers (espace ASCII simple)."""
    if v is None:
        return ""
    try:
        n = int(float(v))
        s = str(n)
        groups = []
        while len(s) > 3:
            groups.append(s[-3:])
            s = s[:-3]
        groups.append(s)
        return " ".join(reversed(groups))
    except (TypeError, ValueError):
        return str(v)


def generate_of_pdf(of_data: dict, template_path: Optional[str] = None) -> bytes:
    """
    Genere un PDF rempli a partir du template vierge.

    Args:
        of_data : dict avec les colonnes de of_imports
        template_path : chemin vers le template (defaut : data/of_template.pdf)

    Returns:
        Contenu PDF en bytes.

    Raises:
        FileNotFoundError : si le template est absent.
    """
    tpl = template_path or _TEMPLATE_PATH
    if not os.path.isfile(tpl):
        raise FileNotFoundError(
            "Template OF introuvable : {}. "
            "Deposez sifa_pdf_cdi_of.pdf dans data/of_template.pdf sur le VPS.".format(tpl)
        )

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(_PAGE_W, _PAGE_H))

    def _write(x, y0_mu, y1_mu, text, fontsize=10.8, bold=False):
        """Ecrit du texte sur le canvas. Coords y en convention PyMuPDF (origine haut de page)."""
        if not text:
            return
        baseline = _PAGE_H - y1_mu + 2.0
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold" if bold else "Helvetica", fontsize)
        c.drawString(x, baseline, text)

    d = of_data

    # En-tete
    _write(55,  20.7, 33.9, _fmt(d.get("of_numero")),    fontsize=11, bold=True)
    _write(55,  40.9, 54.0, _fmt(d.get("reference")))
    _write(235, 40.9, 54.0, _fmt(d.get("date_creation")))
    _write(358, 40.9, 54.0, _fmt(d.get("delai_client")))
    _write(55,  61.0, 74.2, _fmt(d.get("machine")))
    _write(292, 63.8, 76.9, _fmt(d.get("format")))

    # Matiere
    _write(92,  81.4, 100.1, _fmt(d.get("matiere")))
    _write(292, 118.4, 131.5, _fmt(d.get("laize")))

    # Quantites (decalees +10px droite pour alignement visuel)
    _write(429, 118.6, 131.8, _fmt_qte(d.get("qte_etiquettes")))
    _write(429, 139.2, 152.3, _fmt_qte(d.get("qte_bobines")))
    _write(429, 173.7, 186.9, _fmt(d.get("metrage")))

    # Conditionnement
    _write(93,  220.6, 233.8, _fmt(d.get("conditionnement")))
    _write(429, 237.9, 251.1, _fmt(d.get("nb_cartons")))
    _write(429, 255.2, 268.3, _fmt(d.get("nb_mandrins")))
    _write(419, 272.5, 285.6, _fmt(d.get("nb_tubes")))
    _write(76,  289.5, 302.7, _fmt(d.get("mandrins_dia", "")))

    # Outils
    _write(158, 419.1, 432.3, _fmt(d.get("outil_1_numero")), fontsize=8.4)

    c.save()
    buf.seek(0)

    # Fusion template + overlay
    template_pdf = PdfReader(tpl)
    overlay_pdf  = PdfReader(buf)
    writer = PdfWriter()
    page = template_pdf.pages[0]
    page.merge_page(overlay_pdf.pages[0])
    writer.add_page(page)

    out = BytesIO()
    writer.write(out)
    return out.getvalue()
