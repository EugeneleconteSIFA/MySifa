"""Génération PDF pour la valorisation du stock (MyStock > Valorisation).

3 vues :
  - lignes    : tableau ligne par ligne (MP puis PF)
  - sommaire  : totaux MP + PF + par catégorie
  - insights  : sommaire + charts (répartition catégories + top-10 refs)

Utilise reportlab (déjà installé) pour le layout et matplotlib pour les charts
(intégrés en PNG via BytesIO).
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Palette (aligné sur charte MySifa) ────────────────────────────────────────
_ACCENT = colors.HexColor("#0891b2")
_ACCENT_BG = colors.HexColor("#e0f7fa")
_MUTED = colors.HexColor("#64748b")
_TEXT = colors.HexColor("#0f172a")
_BORDER = colors.HexColor("#e2e8f0")
_GREEN = colors.HexColor("#16a34a")
_ORANGE = colors.HexColor("#c2410c")

_STYLES = getSampleStyleSheet()

_TITLE = ParagraphStyle(
    "MysifaTitle",
    parent=_STYLES["Title"],
    fontName="Helvetica-Bold",
    fontSize=18,
    textColor=_TEXT,
    spaceAfter=4,
    alignment=0,
)
_SUBTITLE = ParagraphStyle(
    "MysifaSubtitle",
    parent=_STYLES["Normal"],
    fontName="Helvetica",
    fontSize=10,
    textColor=_MUTED,
    spaceAfter=6,
)
_H2 = ParagraphStyle(
    "MysifaH2",
    parent=_STYLES["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=13,
    textColor=_TEXT,
    spaceBefore=10,
    spaceAfter=6,
)
_BODY = ParagraphStyle(
    "MysifaBody",
    parent=_STYLES["BodyText"],
    fontName="Helvetica",
    fontSize=9,
    textColor=_TEXT,
    leading=12,
)
_BADGE = ParagraphStyle(
    "MysifaBadge",
    parent=_STYLES["Normal"],
    fontName="Helvetica-Bold",
    fontSize=9,
    textColor=_ORANGE,
    leading=12,
)


def _fmt_eur(n: float | int | None) -> str:
    v = float(n or 0)
    txt = f"{v:,.2f}".replace(",", " ").replace(".", ",")
    if txt.endswith(",00"):
        txt = txt[:-3]
    return f"{txt} €"


def _fmt_qte(n: float | int | None) -> str:
    v = float(n or 0)
    if abs(v - round(v)) < 0.005:
        return f"{int(round(v)):,}".replace(",", " ")
    return f"{v:,.2f}".replace(",", " ").replace(".", ",")


def _fmt_date_fr(iso: str | None) -> str:
    if not iso:
        return datetime.now().strftime("%d/%m/%Y")
    parts = iso.split("-")
    if len(parts) == 3:
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return iso


def _header_flowables(
    subtitle: str,
    snapshot_date: str | None,
    generated_by: str | None,
) -> list:
    out: list = []
    out.append(Paragraph("MySifa &nbsp;·&nbsp; Valorisation du stock", _TITLE))
    out.append(Paragraph(subtitle, _SUBTITLE))
    now = datetime.now().strftime("%d/%m/%Y à %H:%M")
    meta_parts = [f"Généré le {now}"]
    if generated_by:
        meta_parts.append(f"par {generated_by}")
    out.append(Paragraph(" · ".join(meta_parts), _SUBTITLE))
    if snapshot_date:
        badge_txt = (
            f"Valorisation figée au {_fmt_date_fr(snapshot_date)} — quantités et prix reconstitués. "
            f"Paramètres globaux actuels (taux USD, taxe, containers, charges de prod)."
        )
        out.append(Spacer(1, 4))
        out.append(Paragraph(badge_txt, _BADGE))
    out.append(Spacer(1, 8))
    line = Table([[""]], colWidths=[190 * mm], rowHeights=[1.5])
    line.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), _ACCENT)]))
    out.append(line)
    out.append(Spacer(1, 10))
    return out


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(_MUTED)
    txt = f"MySifa · page {doc.page}"
    canvas.drawRightString(200 * mm, 10 * mm, txt)
    canvas.restoreState()


def _std_table_style() -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _ACCENT_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), _ACCENT),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, 0), 1, _ACCENT),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, _BORDER),
    ])


# ─── Vue « lignes » ───────────────────────────────────────────────────────────

def _build_pdf_lignes(items_mp, items_pf, summary_mp, summary_pf, snapshot_date, generated_by):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=10 * mm, rightMargin=10 * mm,
        topMargin=12 * mm, bottomMargin=15 * mm,
        title="MySifa — Valorisation détaillée",
        author="MySifa",
    )
    story: list = []
    story.extend(_header_flowables("Détail ligne par ligne (matières premières + produits finis)", snapshot_date, generated_by))

    story.append(Paragraph(
        f"Matières premières — {_fmt_eur(summary_mp.get('total_mp'))}", _H2))
    mp_header = ["Catégorie", "Référence", "Désignation", "Qté", "Prix unit.", "Valorisation"]
    mp_rows: list[list[Any]] = [mp_header]
    for it in items_mp:
        cat_lbl = str(it.get("categorie_label") or it.get("categorie") or "")
        ref = str(it.get("reference") or "")
        des = str(it.get("designation") or "")
        if len(des) > 55:
            des = des[:52] + "…"
        qte = _fmt_qte(it.get("quantite"))
        unite = it.get("unite") or ""
        prix = _fmt_eur(it.get("prix_unitaire"))
        valo = _fmt_eur(it.get("valorisation"))
        mp_rows.append([
            Paragraph(cat_lbl, _BODY),
            Paragraph(ref, _BODY),
            Paragraph(des, _BODY),
            Paragraph(f"{qte} {unite}".strip(), _BODY),
            Paragraph(prix, _BODY),
            Paragraph(valo, _BODY),
        ])
    mp_table = Table(
        mp_rows,
        colWidths=[30 * mm, 32 * mm, 55 * mm, 22 * mm, 25 * mm, 26 * mm],
        repeatRows=1,
    )
    mp_table.setStyle(_std_table_style())
    story.append(mp_table)

    story.append(PageBreak())
    story.extend(_header_flowables("Détail ligne par ligne (produits finis)", snapshot_date, generated_by))
    story.append(Paragraph(
        f"Produits finis — {_fmt_eur(summary_pf.get('total_pf'))}", _H2))
    pf_header = ["Type", "Référence", "Désignation", "Qté", "Prix HT", "Valorisation"]
    pf_rows: list[list[Any]] = [pf_header]
    for it in items_pf:
        type_lbl = str(it.get("type_label") or ("Négoce" if it.get("type") == "negoce" else "Fabriqué"))
        ref = str(it.get("reference") or "")
        des = str(it.get("designation") or "")
        if len(des) > 55:
            des = des[:52] + "…"
        qte = _fmt_qte(it.get("quantite"))
        unite = it.get("unite") or ""
        prix = _fmt_eur(it.get("prix_unitaire_ht"))
        valo = _fmt_eur(it.get("valorisation"))
        pf_rows.append([
            Paragraph(type_lbl, _BODY),
            Paragraph(ref, _BODY),
            Paragraph(des, _BODY),
            Paragraph(f"{qte} {unite}".strip(), _BODY),
            Paragraph(prix, _BODY),
            Paragraph(valo, _BODY),
        ])
    pf_table = Table(
        pf_rows,
        colWidths=[22 * mm, 32 * mm, 63 * mm, 22 * mm, 25 * mm, 26 * mm],
        repeatRows=1,
    )
    pf_table.setStyle(_std_table_style())
    story.append(pf_table)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


# ─── KPI card ─────────────────────────────────────────────────────────────────

def _kpi_card_flowable(title: str, base: float, reel: float | None, reel_label: str) -> Table:
    body = [
        [Paragraph(f"<b>{title.upper()}</b>", ParagraphStyle(
            "kpi_title", parent=_BODY, fontSize=8, textColor=_MUTED, spaceAfter=4))],
    ]
    if reel is not None:
        body.append([Paragraph(f"<font size='16' color='#16a34a'><b>{_fmt_eur(reel)}</b></font>", _BODY)])
        body.append([Paragraph(f"<font color='#64748b'>{_fmt_eur(base)}</font> <font size='7' color='#64748b'>BASE</font>", _BODY)])
    else:
        body.append([Paragraph(f"<font size='16'><b>{_fmt_eur(base)}</b></font>", _BODY)])
    t = Table(body, colWidths=[58 * mm])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.75, _BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


# ─── Vue « sommaire » ─────────────────────────────────────────────────────────

def _build_pdf_sommaire(items_mp, items_pf, summary_mp, summary_pf, snapshot_date, generated_by):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=12 * mm, bottomMargin=15 * mm,
        title="MySifa — Valorisation sommaire",
        author="MySifa",
    )
    story: list = []
    story.extend(_header_flowables("Sommaire par catégorie", snapshot_date, generated_by))

    total_mp = float(summary_mp.get("total_mp") or 0)
    total_pf = float(summary_pf.get("total_pf") or 0)
    total_mp_reel = float(summary_mp.get("total_mp_reel") or total_mp)
    pf_avec_charges = float(summary_pf.get("total_pf_avec_charges") or total_pf)
    charge_pct = float(summary_pf.get("charge_production_pct") or 0)
    storage_pct = float(summary_pf.get("storage_fees_pct") or 0)
    has_pf_charges = charge_pct > 0 or storage_pct > 0
    total_global = total_mp + total_pf
    total_global_reel = total_mp_reel + (pf_avec_charges if has_pf_charges else total_pf)

    kpi_rows = [
        [
            _kpi_card_flowable("Stock total", total_global, total_global_reel if abs(total_global_reel - total_global) > 0.5 else None, "avec charges"),
            _kpi_card_flowable("Matières premières", total_mp, total_mp_reel if abs(total_mp_reel - total_mp) > 0.5 else None, "réel"),
            _kpi_card_flowable("Produits finis", total_pf, pf_avec_charges if has_pf_charges else None, "avec charges"),
        ]
    ]
    kpi = Table(kpi_rows, colWidths=[60 * mm, 60 * mm, 60 * mm])
    kpi.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(kpi)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Matières premières · répartition par catégorie", _H2))
    cats = summary_mp.get("categories") or []
    header = ["Catégorie", "Réf.", "Réf. valorisées", "Total"]
    rows: list[list[Any]] = [header]
    for c in cats:
        rows.append([
            Paragraph(str(c.get("categorie_label") or c.get("categorie") or ""), _BODY),
            Paragraph(str(c.get("nb_refs") or 0), _BODY),
            Paragraph(str(c.get("nb_refs_valorisees") or 0), _BODY),
            Paragraph(_fmt_eur(c.get("total")), _BODY),
        ])
    tbl = Table(rows, colWidths=[70 * mm, 30 * mm, 40 * mm, 40 * mm], repeatRows=1)
    tbl.setStyle(_std_table_style())
    story.append(tbl)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Produits finis · répartition", _H2))
    total_fab = float(summary_pf.get("total_fabrique") or 0)
    total_neg = float(summary_pf.get("total_negoce") or 0)
    nb_fab = int(summary_pf.get("nb_refs_fabrique") or 0)
    nb_neg = int(summary_pf.get("nb_refs_negoce") or 0)
    rows_pf = [
        ["Type", "Réf.", "Total"],
        [Paragraph("Fabriqués", _BODY), Paragraph(str(nb_fab), _BODY), Paragraph(_fmt_eur(total_fab), _BODY)],
        [Paragraph("Négoce", _BODY), Paragraph(str(nb_neg), _BODY), Paragraph(_fmt_eur(total_neg), _BODY)],
    ]
    tbl_pf = Table(rows_pf, colWidths=[70 * mm, 30 * mm, 40 * mm])
    tbl_pf.setStyle(_std_table_style())
    story.append(tbl_pf)

    story.append(Spacer(1, 14))
    story.append(Paragraph("Paramètres globaux actuellement appliqués", _H2))
    param_rows = [["Paramètre", "Valeur"]]
    tx = summary_mp.get("taux_eur_usd") or 0
    if tx:
        param_rows.append([Paragraph("Taux EUR/USD", _BODY), Paragraph(f"1 USD = {float(tx):.4f} €", _BODY)])
    tax = summary_mp.get("import_tax_pct") or 0
    if tax:
        param_rows.append([Paragraph("Taxe d'importation (adhésifs)", _BODY), Paragraph(f"{float(tax):.2f} %", _BODY)])
    if charge_pct:
        param_rows.append([Paragraph("Charge de production (PF)", _BODY), Paragraph(f"{charge_pct:.2f} %", _BODY)])
    if storage_pct:
        param_rows.append([Paragraph("Frais de stockage (PF)", _BODY), Paragraph(f"{storage_pct:.2f} %", _BODY)])
    if len(param_rows) > 1:
        pt = Table(param_rows, colWidths=[100 * mm, 60 * mm])
        pt.setStyle(_std_table_style())
        story.append(pt)
    else:
        story.append(Paragraph("Aucun paramètre multiplicateur actif.", _SUBTITLE))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


# ─── Vue « sommaire + insights » ─────────────────────────────────────────────

def _build_pdf_insights(items_mp, items_pf, summary_mp, summary_pf, snapshot_date, generated_by):
    pie_png = _render_pie_categories(summary_mp)
    top_png = _render_top10_refs(items_mp, items_pf)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=12 * mm, bottomMargin=15 * mm,
        title="MySifa — Valorisation & insights",
        author="MySifa",
    )
    story: list = []
    story.extend(_header_flowables("Sommaire + insights & répartitions", snapshot_date, generated_by))

    total_mp = float(summary_mp.get("total_mp") or 0)
    total_pf = float(summary_pf.get("total_pf") or 0)
    total_mp_reel = float(summary_mp.get("total_mp_reel") or total_mp)
    pf_avec_charges = float(summary_pf.get("total_pf_avec_charges") or total_pf)
    charge_pct = float(summary_pf.get("charge_production_pct") or 0)
    storage_pct = float(summary_pf.get("storage_fees_pct") or 0)
    has_pf_charges = charge_pct > 0 or storage_pct > 0
    total_global = total_mp + total_pf
    total_global_reel = total_mp_reel + (pf_avec_charges if has_pf_charges else total_pf)

    kpi_rows = [
        [
            _kpi_card_flowable("Stock total", total_global, total_global_reel if abs(total_global_reel - total_global) > 0.5 else None, "avec charges"),
            _kpi_card_flowable("Matières premières", total_mp, total_mp_reel if abs(total_mp_reel - total_mp) > 0.5 else None, "réel"),
            _kpi_card_flowable("Produits finis", total_pf, pf_avec_charges if has_pf_charges else None, "avec charges"),
        ]
    ]
    kpi = Table(kpi_rows, colWidths=[58 * mm, 58 * mm, 58 * mm])
    kpi.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(kpi)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Répartition MP par catégorie (€)", _H2))
    if pie_png:
        story.append(Image(io.BytesIO(pie_png), width=170 * mm, height=90 * mm))
    else:
        story.append(Paragraph("Pas de données pour le graphique.", _SUBTITLE))
    story.append(Spacer(1, 10))

    story.append(PageBreak())
    story.extend(_header_flowables("Top 10 — références par valorisation (MP + PF)", snapshot_date, generated_by))
    story.append(Paragraph("Top 10 des références par valorisation", _H2))
    if top_png:
        story.append(Image(io.BytesIO(top_png), width=180 * mm, height=110 * mm))
    else:
        story.append(Paragraph("Pas de données pour le graphique.", _SUBTITLE))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def _render_pie_categories(summary_mp):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None
    cats = summary_mp.get("categories") or []
    data = [(str(c.get("categorie_label") or ""), float(c.get("total") or 0)) for c in cats if float(c.get("total") or 0) > 0]
    if not data:
        return None
    labels = [d[0] for d in data]
    values = [d[1] for d in data]
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=120)
    palette = ["#0891b2", "#22d3ee", "#0284c7", "#4f46e5", "#7c3aed", "#c026d3", "#e11d48", "#f97316", "#eab308", "#16a34a"]
    colors_ = [palette[i % len(palette)] for i in range(len(values))]
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, autopct="%1.1f%%",
        startangle=90, colors=colors_,
        textprops={"fontsize": 9},
    )
    for at in autotexts:
        at.set_color("white")
        at.set_fontweight("bold")
    ax.set_aspect("equal")
    plt.tight_layout()
    out = io.BytesIO()
    fig.savefig(out, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out.getvalue()


def _render_top10_refs(items_mp, items_pf):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None
    combined = []
    for it in items_mp:
        v = float(it.get("valorisation") or 0)
        if v > 0:
            combined.append((f"MP · {it.get('reference') or ''}", v, "#0891b2"))
    for it in items_pf:
        v = float(it.get("valorisation") or 0)
        if v > 0:
            combined.append((f"PF · {it.get('reference') or ''}", v, "#16a34a"))
    if not combined:
        return None
    combined.sort(key=lambda x: x[1], reverse=True)
    top = combined[:10][::-1]
    labels = [t[0] for t in top]
    values = [t[1] for t in top]
    colors_ = [t[2] for t in top]
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=120)
    ax.barh(labels, values, color=colors_)
    ax.set_xlabel("Valorisation (€)", fontsize=9)
    ax.tick_params(axis="y", labelsize=8)
    ax.tick_params(axis="x", labelsize=8)
    for i, v in enumerate(values):
        ax.text(v, i, f"  {v:,.0f} €".replace(",", " "), va="center", fontsize=8, color="#0f172a")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    out = io.BytesIO()
    fig.savefig(out, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out.getvalue()


# ─── Dispatcher ───────────────────────────────────────────────────────────────

def build_valorisation_pdf(
    type_vue: str,
    items_mp,
    items_pf,
    summary_mp,
    summary_pf,
    snapshot_date=None,
    generated_by=None,
):
    if type_vue == "lignes":
        return _build_pdf_lignes(items_mp, items_pf, summary_mp, summary_pf, snapshot_date, generated_by)
    if type_vue == "sommaire":
        return _build_pdf_sommaire(items_mp, items_pf, summary_mp, summary_pf, snapshot_date, generated_by)
    if type_vue == "insights":
        return _build_pdf_insights(items_mp, items_pf, summary_mp, summary_pf, snapshot_date, generated_by)
    raise ValueError(f"Type de vue PDF inconnu : {type_vue!r}")
