"""Génération PDF — fiche produit coûts matières (reportlab)."""

from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from typing import Any, Optional
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER  # footer_style
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import BASE_DIR

_ROLE_LABELS = {
    "frontal": "Frontal",
    "adhesif": "Adhésif",
    "silicone": "Silicone",
    "glassine": "Glassine",
}

_PARIS = ZoneInfo("Europe/Paris")


def _fmt4(v: Any) -> str:
    try:
        return f"{float(v):.4f}"
    except (TypeError, ValueError):
        return "—"


def _logo_path() -> Optional[str]:
    for rel in (
        "static/mys_icon_512.png",
        "static/mys_icon_192.png",
        "static/mys_icon_180.png",
    ):
        p = os.path.join(BASE_DIR, rel)
        if os.path.isfile(p):
            return p
    return None


def build_product_pdf(
    *,
    code: str,
    name: str,
    components: list[dict[str, Any]],
    total_eur_per_m2: Decimal,
    margin_eur_m2: Decimal,
    sell_price_eur_m2: Decimal,
) -> bytes:
    """Retourne les octets du PDF."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=20 * mm,
        title=f"Fiche produit {code}",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PrTitle",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=4,
        textColor=colors.HexColor("#0f172a"),
    )
    sub_style = ParagraphStyle(
        "PrSub",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#475569"),
    )
    footer_style = ParagraphStyle(
        "PrFooter",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#64748b"),
        alignment=TA_CENTER,
    )

    now = datetime.now(_PARIS).strftime("%d/%m/%Y %H:%M")
    story: list[Any] = []

    logo = _logo_path()
    if logo:
        try:
            img = Image(logo, width=22 * mm, height=22 * mm)
            img.hAlign = "LEFT"
            story.append(img)
            story.append(Spacer(1, 6))
        except Exception:
            pass

    story.append(Paragraph("MySifa — Coûts matières", sub_style))
    story.append(Paragraph(f"Fiche produit · {code}", title_style))
    story.append(Paragraph(name, styles["Heading2"]))
    story.append(Paragraph(f"Généré le {now} (heure Paris)", sub_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Composition", styles["Heading3"]))
    comp_rows = [["Composant", "Matière", "€/m²", "%"]]
    for c in components:
        role = _ROLE_LABELS.get(c.get("role") or "", (c.get("role") or "").capitalize())
        comp_rows.append(
            [
                role,
                str(c.get("name") or "—"),
                _fmt4(c.get("price_eur_per_m2")),
                f"{float(c.get('share_pct', 0)):.2f}",
            ]
        )
    if len(comp_rows) == 1:
        comp_rows.append(["—", "Aucun composant", "—", "—"])

    comp_table = Table(comp_rows, colWidths=[28 * mm, 72 * mm, 28 * mm, 18 * mm])
    comp_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (2, 1), (3, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(comp_table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Coûts", styles["Heading3"]))
    cost_rows = [
        ["Libellé", "€/m²"],
        ["Coût matières (total)", _fmt4(total_eur_per_m2)],
        ["Marge", _fmt4(margin_eur_m2)],
        ["Prix de vente", _fmt4(sell_price_eur_m2)],
    ]
    cost_table = Table(cost_rows, colWidths=[100 * mm, 40 * mm])
    cost_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ecfeff")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(cost_table)
    story.append(Spacer(1, 24))
    story.append(
        Paragraph(
            "Document interne — Prix HT, indicatifs, sujets à variation",
            footer_style,
        )
    )

    doc.build(story)
    return buf.getvalue()
