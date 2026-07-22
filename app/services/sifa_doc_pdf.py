# -*- coding: utf-8 -*-
"""
SIFA — Génération PDF des documents officiels (Déclarations UE de Conformité, etc.)

Ce service produit les PDFs de la section « Certifications SIFA » de MyQualité.
Un seul template pour le moment : Déclaration UE de Conformité.

La mise en page reproduit fidèlement le template de référence (SIFA-DoC-2026-001) :
en-tête avec logo SIFA + référence à droite, sections numérotées 1..8, tableau seuils
métaux lourds, encadré jaune Certification FSC en cours, footer centré avec pagination.

Utilisé par app/routers/qualite.py — routes /api/qualite/sifa-docs/*.
"""

from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable, PageBreak,
)

# ─── Palette SIFA ─────────────────────────────────────────────────────────
NAVY = colors.HexColor("#0f172a")
GREY = colors.HexColor("#64748b")
MUTED = colors.HexColor("#94a3b8")
BORDER = colors.HexColor("#cbd5e1")
LIGHT_BG = colors.HexColor("#f8fafc")
YELLOW = colors.HexColor("#fbbf24")
YELLOW_BG = colors.HexColor("#fef9e7")
BLACK = colors.black

# ─── Mois en français (utilisé dans l'en-tête) ────────────────────────────
_MONTHS_FR = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]


def _fr_month_year(iso_str: str) -> str:
    try:
        d = datetime.fromisoformat(iso_str)
        return f"{_MONTHS_FR[d.month - 1]} {d.year}"
    except Exception:
        now = datetime.now()
        return f"{_MONTHS_FR[now.month - 1]} {now.year}"


def _fr_date_parts(iso_str: str):
    """Retourne (jour, mois, année) formatés — pour 'Roubaix, le J / M / AAAA'."""
    try:
        d = datetime.fromisoformat(iso_str)
        return f"{d.day:02d}", f"{d.month:02d}", str(d.year)
    except Exception:
        return "____", "____", str(datetime.now().year)


def _year(iso_str: str) -> int:
    try:
        return datetime.fromisoformat(iso_str).year
    except Exception:
        return datetime.now().year


# ─── Styles Paragraph ──────────────────────────────────────────────────────
def _make_styles():
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=ss["Title"], fontName="Helvetica-Bold",
            fontSize=20, alignment=TA_CENTER, textColor=NAVY,
            spaceBefore=4, spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=ss["Normal"], fontName="Helvetica-Oblique",
            fontSize=12, alignment=TA_CENTER, textColor=GREY,
            spaceAfter=14,
        ),
        "h2": ParagraphStyle(
            "h2", parent=ss["Heading2"], fontName="Helvetica-Bold",
            fontSize=13, textColor=NAVY, spaceBefore=12, spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "h3", parent=ss["Heading3"], fontName="Helvetica-Bold",
            fontSize=10.5, textColor=NAVY, spaceBefore=8, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body", parent=ss["Normal"], fontName="Helvetica",
            fontSize=9.5, textColor=NAVY, leading=13,
            spaceAfter=4, alignment=TA_JUSTIFY,
        ),
        "body_it": ParagraphStyle(
            "body_it", parent=ss["Normal"], fontName="Helvetica-Oblique",
            fontSize=9.5, textColor=NAVY, leading=13,
            spaceAfter=4, alignment=TA_JUSTIFY,
        ),
        "body_bold": ParagraphStyle(
            "body_bold", parent=ss["Normal"], fontName="Helvetica-Bold",
            fontSize=9.5, textColor=NAVY, leading=13,
            spaceAfter=4, alignment=TA_LEFT,
        ),
        "bullet": ParagraphStyle(
            "bullet", parent=ss["Normal"], fontName="Helvetica",
            fontSize=9.5, textColor=NAVY, leading=13,
            leftIndent=14, bulletIndent=4, spaceAfter=2,
        ),
        "note_frame": ParagraphStyle(
            "note_frame", parent=ss["Normal"], fontName="Helvetica",
            fontSize=9, textColor=NAVY, leading=12,
            spaceAfter=0, alignment=TA_LEFT,
        ),
        "signature_lbl": ParagraphStyle(
            "signature_lbl", parent=ss["Normal"], fontName="Helvetica",
            fontSize=9.5, textColor=NAVY, leading=15, spaceAfter=2,
        ),
        "signature_hd": ParagraphStyle(
            "signature_hd", parent=ss["Normal"], fontName="Helvetica-Bold",
            fontSize=10.5, textColor=NAVY, leading=14, spaceAfter=6,
        ),
    }


# ─── Header / Footer ───────────────────────────────────────────────────────
import os as _os

# Cache du chemin du logo (résolu une fois)
_LOGO_PATH_CACHE = None


def _locate_logo():
    """Trouve le PNG du logo SIFA — cherche à plusieurs endroits usuels du repo."""
    global _LOGO_PATH_CACHE
    if _LOGO_PATH_CACHE is not None:
        return _LOGO_PATH_CACHE or None
    # Chemin relatif : app/services/sifa_doc_pdf.py → repo root / static / sifa_logo.png
    here = _os.path.dirname(_os.path.abspath(__file__))
    candidates = [
        _os.path.abspath(_os.path.join(here, "..", "..", "static", "sifa_logo.png")),
        _os.path.abspath(_os.path.join(here, "..", "static", "sifa_logo.png")),
        _os.path.abspath(_os.path.join(here, "..", "..", "app", "static", "sifa_logo.png")),
    ]
    for path in candidates:
        if _os.path.exists(path):
            _LOGO_PATH_CACHE = path
            return path
    _LOGO_PATH_CACHE = ""  # Pas trouvé, ne pas re-chercher
    return None


def _draw_logo(canvas_, x, y):
    """Logo SIFA : PNG réel (brosse + rectangle jaune SIFA). Fallback texte si absent."""
    logo_path = _locate_logo()
    canvas_.saveState()
    if logo_path:
        try:
            # Le logo est ~2:1, on veut ~28mm large, 14mm haut
            from reportlab.lib.utils import ImageReader
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            target_w = 30 * mm
            target_h = target_w * (ih / iw) if iw else 14 * mm
            canvas_.drawImage(logo_path, x, y - (target_h - 9 * mm),
                              width=target_w, height=target_h,
                              preserveAspectRatio=True, mask="auto")
            canvas_.restoreState()
            return
        except Exception:
            pass
    # Fallback : ancien rendu vectoriel
    canvas_.setFillColor(YELLOW)
    canvas_.rect(x, y, 26 * mm, 9 * mm, fill=1, stroke=0)
    canvas_.setFillColor(BLACK)
    canvas_.setFont("Helvetica-Bold", 14)
    canvas_.drawString(x + 5 * mm, y + 2.5 * mm, "SIFA")
    canvas_.restoreState()


def _page_decor(canvas_, doc, ref: str, header_date: str):
    canvas_.saveState()
    page_w, page_h = A4
    # Logo en haut à gauche
    _draw_logo(canvas_, 15 * mm, page_h - 22 * mm)
    # En-tête droit
    canvas_.setFillColor(GREY)
    canvas_.setFont("Helvetica-Oblique", 8.5)
    canvas_.drawRightString(page_w - 15 * mm, page_h - 14 * mm,
                            "SIFA — Déclaration UE de Conformité")
    canvas_.drawRightString(page_w - 15 * mm, page_h - 19 * mm,
                            f"{header_date} Réf. {ref}")
    # Traits horizontaux fins
    canvas_.setStrokeColor(BORDER)
    canvas_.setLineWidth(0.4)
    canvas_.line(15 * mm, page_h - 25 * mm, page_w - 15 * mm, page_h - 25 * mm)
    canvas_.line(15 * mm, 25 * mm, page_w - 15 * mm, 25 * mm)
    # Footer centré
    canvas_.setFillColor(GREY)
    canvas_.setFont("Helvetica", 8.5)
    canvas_.drawCentredString(page_w / 2, 20 * mm,
                              "SIFA · 45 rue Rollin · 59100 Roubaix · France")
    canvas_.setFont("Helvetica", 8)
    canvas_.drawCentredString(page_w / 2, 15 * mm, f"Page {doc.page} / 3")
    canvas_.restoreState()


# ─── Corps du document ────────────────────────────────────────────────────
def _build_flowables(*, client_nom, fournisseurs, ref, date_emission_iso,
                     validite_mois, styles):
    """Construit la liste de flowables reproduisant fidèlement le template."""
    S = styles
    story = []

    # ── Titre principal
    story.append(Paragraph("DÉCLARATION UE DE CONFORMITÉ", S["title"]))
    story.append(Paragraph("EU Declaration of Conformity (DoC)", S["subtitle"]))

    # ── Tableau identification (Ref + Date d'émission)
    jour, mois, annee = _fr_date_parts(date_emission_iso)
    id_data = [
        [Paragraph("<b>Numéro d'identification unique</b>", S["body"]),
         Paragraph(f"{ref}", S["body"])],
        [Paragraph("<b>Date d'émission</b>", S["body"]),
         Paragraph(f"Roubaix, le {jour} / {mois} / {annee}", S["body"])],
    ]
    id_tbl = Table(id_data, colWidths=[65 * mm, 115 * mm])
    id_tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(id_tbl)
    story.append(Spacer(1, 12))

    # ── Section 1 : Fabricant
    story.append(Paragraph("1. Fabricant", S["h2"]))
    story.append(HRFlowable(width="100%", thickness=0.6, color=BORDER, spaceAfter=6))
    fab_data = [
        [Paragraph("<b>Raison sociale</b>", S["body"]), Paragraph("SIFA", S["body"])],
        [Paragraph("<b>Adresse</b>", S["body"]),
         Paragraph("45 rue Rollin, 59100 Roubaix, France", S["body"])],
        [Paragraph("<b>Activité</b>", S["body"]),
         Paragraph("Fabricant d'étiquettes adhésives", S["body"])],
    ]
    fab_tbl = Table(fab_data, colWidths=[45 * mm, 135 * mm])
    fab_tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(fab_tbl)

    # ── Section 2 : Nature de l'activité SIFA
    story.append(Paragraph("2. Nature de l'activité SIFA", S["h2"]))
    story.append(HRFlowable(width="100%", thickness=0.6, color=BORDER, spaceAfter=6))
    story.append(Paragraph(
        "SIFA fabrique les étiquettes adhésives avec ou sans enduction", S["body"]))
    story.append(Paragraph(
        "<i>Les étiquettes couvertes par la présente Déclaration ne sont pas destinées "
        "au contact alimentaire.</i>", S["body_it"]))

    # ── Section 3 : Fournisseurs
    story.append(Paragraph("3. Fournisseurs — origine géographique", S["h2"]))
    story.append(HRFlowable(width="100%", thickness=0.6, color=BORDER, spaceAfter=6))
    if client_nom:
        story.append(Paragraph(
            f"Pour les étiquettes livrées à <b>{_esc(client_nom)}</b>, les matières "
            f"entrant dans les étiquettes proviennent des fournisseurs suivants :",
            S["body"]))
    else:
        story.append(Paragraph(
            "Les matières entrant dans les étiquettes proviennent des fournisseurs suivants :",
            S["body"]))
    for f in fournisseurs:
        nom = _esc(f.get("nom") or "").strip()
        pays = _esc(f.get("pays_origine") or "").strip() or "origine à préciser"
        story.append(Paragraph(
            f"• <b>{nom}</b> — matières fabriquées en {pays}.", S["bullet"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Toutes les matières à l'origine de la fabrication des étiquettes couvertes par la "
        "présente Déclaration sont fabriquées au sein de l'Union européenne ou du Royaume-Uni.",
        S["body"]))

    # ── Section 4 : Conformités attestées
    story.append(Paragraph("4. Conformités attestées", S["h2"]))
    story.append(HRFlowable(width="100%", thickness=0.6, color=BORDER, spaceAfter=6))
    story.append(Paragraph(
        "SIFA atteste, sur la base des attestations fournisseurs conservées au dossier "
        "technique, que les matières entrant dans les étiquettes livrées à ce client "
        "respectent les exigences suivantes.", S["body"]))

    story.append(Paragraph(
        "4.1 REACH — Substances extrêmement préoccupantes (SVHC)", S["h3"]))
    story.append(Paragraph("Règlement (CE) n° 1907/2006.", S["body"]))
    story.append(Paragraph(
        "Aucune substance figurant sur la liste candidate SVHC de l'ECHA n'est présente à "
        "une concentration supérieure à 0,1 % (w/w), qu'elle soit ajoutée intentionnellement "
        "ou présente en tant qu'impureté.", S["body"]))
    story.append(Paragraph(
        "Les fournisseurs s'engagent à notifier SIFA en cas d'évolution.", S["body"]))

    story.append(Paragraph("4.2 California Proposition 65", S["h3"]))
    story.append(Paragraph(
        "Aucune substance de la liste OEHHA n'est intentionnellement ajoutée aux matières.",
        S["body"]))
    story.append(Paragraph(
        "Les traces éventuelles restent inférieures aux seuils NSRL et MADL applicables.",
        S["body"]))

    # ── Page 2
    story.append(PageBreak())

    # ── Section 4.3 : Métaux lourds
    story.append(Paragraph(
        "4.3 Métaux lourds — traces techniquement inévitables", S["h3"]))
    story.append(Paragraph(
        "Directive 94/62/CE (art. 11) et Model Toxics in Packaging Legislation (CONEG).",
        S["body"]))
    story.append(Paragraph(
        "Plomb (Pb), cadmium (Cd), mercure (Hg) et chrome hexavalent (Cr VI) ne sont pas "
        "intentionnellement ajoutés aux matières. Les seuils individuels attestés par les "
        "fournisseurs sont :", S["body"]))
    metaux_data = [
        [Paragraph("<b>Élément</b>", S["body"]),
         Paragraph("<b>Seuil individuel</b>", S["body"]),
         Paragraph("<b>Seuil cumulé (94/62/CE)</b>", S["body"])],
        [Paragraph("Plomb (Pb)", S["body"]),
         Paragraph("&lt; 50 ppm", S["body"]),
         Paragraph("Somme Pb+Cd+Hg+Cr VI &lt; 100 ppm", S["body"])],
        [Paragraph("Cadmium (Cd)", S["body"]),
         Paragraph("&lt; 25 ppm", S["body"]),
         Paragraph("", S["body"])],
        [Paragraph("Mercure (Hg)", S["body"]),
         Paragraph("&lt; 12 ppm", S["body"]),
         Paragraph("", S["body"])],
        [Paragraph("Chrome hexavalent (Cr VI)", S["body"]),
         Paragraph("&lt; 50 ppm", S["body"]),
         Paragraph("", S["body"])],
    ]
    m_tbl = Table(metaux_data, colWidths=[55 * mm, 40 * mm, 85 * mm])
    m_tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BG),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (1, 1), (1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("SPAN", (2, 1), (2, 4)),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(m_tbl)

    # ── Section 4.4 : Certification FSC
    story.append(Paragraph("4.4 Certification FSC", S["h3"]))
    story.append(Paragraph(
        "Les frontaux papier sont issus de fournisseurs sous chaîne de contrôle FSC valide.",
        S["body"]))
    story.append(Paragraph(
        "Références couvertes : licence FSC-C104291 / certificat CU-COC-815304 (Rheno), "
        "valide jusqu'au 18 décembre 2026 ; FSC Mix Credit SCS-COC-004933 (VPF).",
        S["body"]))
    # Encadré jaune
    note_txt = ("<b>Note — Certification FSC SIFA en cours.</b> SIFA sera auditée le 8 octobre 2026 "
                "en vue de l'obtention de sa propre chaîne de contrôle FSC. Le numéro de licence SIFA "
                "sera intégré à cette DoC dès délivrance.")
    note_para = Paragraph(note_txt, S["note_frame"])
    note_tbl = Table([[note_para]], colWidths=[180 * mm])
    note_tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, YELLOW),
        ("BACKGROUND", (0, 0), (-1, -1), YELLOW_BG),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(Spacer(1, 4))
    story.append(note_tbl)
    story.append(Spacer(1, 4))

    # ── Section 4.5 : PFAS
    story.append(Paragraph("4.5 Absence de PFAS", S["h3"]))
    story.append(Paragraph(
        "Les fournisseurs de SIFA certifient l'absence d'ajout intentionnel de substances "
        "PFAS (per- et polyfluoroalkyles, incluant PFOA, PFOS et GenX) dans les matières livrées.",
        S["body"]))
    story.append(Paragraph(
        "<i>Les fournisseurs ne réalisent pas d'analyse de routine sur ces substances.</i>",
        S["body_it"]))

    # ── Section 4.6 : Bisphénols
    story.append(Paragraph("4.6 Absence de bisphénols (BPA, BPS, BPF)", S["h3"]))
    story.append(Paragraph(
        "Aucun ajout intentionnel de bisphénol A, bisphénol S ou bisphénol F dans les matières.",
        S["body"]))

    # ── Section 4.7 : CoA laboratoire
    story.append(Paragraph("4.7 Certificats d'analyse laboratoire (CoA)", S["h3"]))
    story.append(Paragraph(
        "SIFA détient au dossier technique les certificats d'analyse de conformité délivrés par "
        "le laboratoire indépendant ISEGA (Aschaffenburg, Allemagne) sur les adhésifs livrés par "
        "ses fournisseurs.", S["body"]))
    story.append(Paragraph(
        "Ces certificats attestent de la conformité des adhésifs au règlement (CE) n°1935/2004 "
        "et au règlement (UE) n°10/2011. Bien que les étiquettes couvertes ici ne soient pas "
        "destinées au contact alimentaire, ces analyses constituent une garantie supplémentaire "
        "sur l'innocuité des matières.", S["body"]))

    # ── Section 4.8 : PPWR
    story.append(Paragraph("4.8 Cadre général — PPWR", S["h3"]))
    story.append(Paragraph(
        "La présente Déclaration est établie conformément à l'Annexe VIII du règlement (UE) "
        "2025/40 (PPWR), applicable à compter du 12 août 2026.", S["body"]))

    # ── Section 4.9 : Recyclabilité
    story.append(Paragraph("4.9 Recyclabilité", S["h3"]))
    story.append(Paragraph(
        "À la date d'émission, aucune évaluation formelle de recyclabilité (Recyclass, COTREP, "
        "CEREC) n'a été réalisée sur les étiquettes couvertes par la présente Déclaration.",
        S["body"]))
    story.append(Paragraph(
        "Les matières utilisées sont issues de fournisseurs qui appliquent les recommandations "
        "d'éco-conception publiées par la filière (Guide technique UNFEA / Citeo — "
        "Éco-conception des étiquettes adhésives, édition 2026).", S["body"]))
    story.append(Paragraph(
        "<i>Une évaluation formelle est engagée par SIFA. Les résultats seront intégrés à la "
        "présente Déclaration dès disponibilité.</i>", S["body_it"]))

    # ── Page 3
    story.append(PageBreak())

    # ── Section 5 : Contenu recyclé
    story.append(Paragraph("5. Contenu recyclé", S["h2"]))
    story.append(HRFlowable(width="100%", thickness=0.6, color=BORDER, spaceAfter=6))
    story.append(Paragraph(
        "À la date d'émission, au moins un des deux fournisseurs de SIFA ne livre pas ses "
        "matières sous forme recyclée.", S["body"]))
    story.append(Paragraph(
        "SIFA ne peut donc pas garantir un taux de contenu recyclé pour l'ensemble de sa gamme "
        "au sens de l'article 7 du PPWR.", S["body"]))
    story.append(Paragraph(
        "Le taux réel de contenu recyclé, lorsqu'il s'applique, est indiqué dans la fiche "
        "technique produit associée à chaque référence d'étiquette.", S["body"]))

    # ── Section 6 : Base documentaire
    story.append(Paragraph("6. Base documentaire", S["h2"]))
    story.append(HRFlowable(width="100%", thickness=0.6, color=BORDER, spaceAfter=6))
    story.append(Paragraph(
        "La présente Déclaration s'appuie sur l'ensemble des documents du dossier technique "
        "SIFA : attestations fournisseurs, certificats de conformité, certificats FSC, "
        "certificats d'analyse de laboratoire et fiches techniques produit.", S["body"]))
    story.append(Paragraph(
        "L'ensemble de ces pièces est conservé au dossier technique et communicable au client "
        "ou à toute autorité compétente sous 10 jours ouvrés sur demande écrite.", S["body"]))

    # ── Section 7 : Responsabilité et validité
    story.append(Paragraph("7. Responsabilité et validité", S["h2"]))
    story.append(HRFlowable(width="100%", thickness=0.6, color=BORDER, spaceAfter=6))
    story.append(Paragraph(
        "Déclaration établie sous la seule responsabilité de SIFA en tant que fabricant.",
        S["body"]))
    story.append(Paragraph(
        f"<b>Validité : {int(validite_mois)} mois à compter de la date d'émission.</b>",
        S["body"]))
    story.append(Paragraph(
        "Toute évolution des matières, du statut d'un fournisseur ou de la liste candidate SVHC "
        "entraîne réémission.", S["body"]))
    story.append(Paragraph(
        "SIFA n'est pas responsable des usages non conformes aux fiches techniques produit ni "
        "des transformations ultérieures effectuées par le client.", S["body"]))

    # ── Section 8 : Signature et cachet
    story.append(Paragraph("8. Signature et cachet", S["h2"]))
    story.append(HRFlowable(width="100%", thickness=0.6, color=BORDER, spaceAfter=6))
    story.append(Paragraph(
        "Fait à Roubaix, la présente Déclaration engage la responsabilité de SIFA.",
        S["body"]))
    story.append(Spacer(1, 10))

    sig_left = [
        Paragraph("<b>Représentant SIFA</b>", S["signature_hd"]),
        Paragraph("Nom : ______________________________", S["signature_lbl"]),
        Paragraph("Fonction : __________________________", S["signature_lbl"]),
        Paragraph(f"Date : ____ / ____ / {annee}", S["signature_lbl"]),
        Paragraph("Signature :", S["signature_lbl"]),
        Spacer(1, 40),
        Paragraph("______________________________________", S["signature_lbl"]),
    ]
    cachet_frame = Table(
        [[Paragraph("<i>[Emplacement réservé au cachet]</i>",
                    ParagraphStyle("cachet", parent=S["body_it"],
                                   alignment=TA_CENTER, textColor=MUTED))]],
        colWidths=[75 * mm], rowHeights=[55 * mm]
    )
    cachet_frame.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("DASHED", (0, 0), (-1, -1), 2),
    ]))
    sig_right = [
        Paragraph("<b>Cachet SIFA</b>", S["signature_hd"]),
        Spacer(1, 6),
        cachet_frame,
    ]

    sig_tbl = Table([[sig_left, sig_right]], colWidths=[95 * mm, 85 * mm])
    sig_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(sig_tbl)

    story.append(Spacer(1, 30))
    story.append(HRFlowable(width="40%", thickness=0.4, color=BORDER,
                            hAlign="CENTER", spaceAfter=6))
    story.append(Paragraph(
        f"<i>Document établi conformément à l'Annexe VIII du règlement (UE) 2025/40 (PPWR).</i>",
        ParagraphStyle("foot1", parent=S["body_it"], alignment=TA_CENTER,
                       textColor=MUTED, fontSize=9)))
    story.append(Paragraph(
        f"<i>Référence unique : {_esc(ref)} — Version 1.0</i>",
        ParagraphStyle("foot2", parent=S["body_it"], alignment=TA_CENTER,
                       textColor=MUTED, fontSize=9)))

    return story


def _esc(s: str) -> str:
    """Échappe HTML entities pour reportlab Paragraph."""
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build_declaration_ue_pdf(*, client_nom: str, fournisseurs: list,
                             ref: str, date_emission_iso: str,
                             validite_mois: int = 12) -> bytes:
    """
    Génère un PDF de Déclaration UE de Conformité.

    Args:
        client_nom: Nom du client destinataire (ex. "Hermès")
        fournisseurs: Liste de dicts {"nom": str, "pays_origine": str, "certificat": str|None}
        ref: Référence unique du document (ex. "SIFA-DoC-HERMES-001")
        date_emission_iso: Date d'émission au format ISO (YYYY-MM-DD)
        validite_mois: Durée de validité en mois (12 par défaut)

    Returns:
        bytes: contenu binaire du PDF
    """
    buf = BytesIO()
    styles = _make_styles()
    header_date = _fr_month_year(date_emission_iso)

    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=30 * mm, bottomMargin=28 * mm,
        title=f"SIFA - Déclaration UE - {client_nom}",
        author="SIFA",
        subject="Déclaration UE de Conformité",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  doc.width, doc.height, id="body_frame",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    def _on_page(canvas_, doc_):
        _page_decor(canvas_, doc_, ref=ref, header_date=header_date)

    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_on_page)])
    story = _build_flowables(
        client_nom=client_nom,
        fournisseurs=fournisseurs or [],
        ref=ref,
        date_emission_iso=date_emission_iso,
        validite_mois=validite_mois,
        styles=styles,
    )
    doc.build(story)
    return buf.getvalue()


# ─── Registry des templates disponibles ───────────────────────────────────
TEMPLATE_BUILDERS = {
    "declaration_ue": build_declaration_ue_pdf,
}


def build_template_pdf(template_code: str, **kwargs) -> bytes:
    """Point d'entrée générique : dispatch sur le bon builder selon le code template."""
    builder = TEMPLATE_BUILDERS.get(template_code)
    if not builder:
        raise ValueError(f"Template inconnu: {template_code}")
    return builder(**kwargs)
