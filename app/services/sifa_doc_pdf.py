# -*- coding: utf-8 -*-
"""
SIFA — Génération PDF des documents officiels (Déclarations UE de Conformité, etc.)

Ce service produit les PDFs de la section « Certifications SIFA » de MyQualité.
Un seul template pour le moment : Déclaration UE de Conformité.

Architecture par sections :
  - SECTIONS_META : liste ordonnée des sections avec leur id, titre, texte par
    défaut, et flags `removable` (peut-on la retirer) / `editable` (peut-on
    éditer son texte body).
  - _build_sec_*(ctx) : builder par section, retourne List[Flowable].
  - build_declaration_ue_pdf() orchestre : pour chaque section, applique les
    overrides éventuels (include=False → skip, custom_body="…" → remplace le
    paragraphe body) et empile les flowables.

Overrides = dict {"sec_5": {"include": False}, "sec_2": {"custom_body": "…"}}

Utilisé par app/routers/qualite.py — routes /api/qualite/sifa-docs/*.
"""

from io import BytesIO
from datetime import datetime
import os as _os

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak, KeepTogether,
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

# ─── Mois en français ─────────────────────────────────────────────────────
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
    try:
        d = datetime.fromisoformat(iso_str)
        return f"{d.day:02d}", f"{d.month:02d}", str(d.year)
    except Exception:
        return "____", "____", str(datetime.now().year)


def _esc(s: str) -> str:
    if s is None:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ─── Styles Paragraph ─────────────────────────────────────────────────────
def _make_styles():
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=ss["Title"], fontName="Helvetica-Bold",
            fontSize=20, alignment=TA_CENTER, textColor=NAVY,
            spaceBefore=4, spaceAfter=2),
        "subtitle": ParagraphStyle(
            "subtitle", parent=ss["Normal"], fontName="Helvetica-Oblique",
            fontSize=12, alignment=TA_CENTER, textColor=GREY, spaceAfter=14),
        "h2": ParagraphStyle(
            "h2", parent=ss["Heading2"], fontName="Helvetica-Bold",
            fontSize=13, textColor=NAVY, spaceBefore=12, spaceAfter=6),
        "h3": ParagraphStyle(
            "h3", parent=ss["Heading3"], fontName="Helvetica-Bold",
            fontSize=10.5, textColor=NAVY, spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle(
            "body", parent=ss["Normal"], fontName="Helvetica",
            fontSize=9.5, textColor=NAVY, leading=13,
            spaceAfter=4, alignment=TA_JUSTIFY),
        "body_it": ParagraphStyle(
            "body_it", parent=ss["Normal"], fontName="Helvetica-Oblique",
            fontSize=9.5, textColor=NAVY, leading=13,
            spaceAfter=4, alignment=TA_JUSTIFY),
        "bullet": ParagraphStyle(
            "bullet", parent=ss["Normal"], fontName="Helvetica",
            fontSize=9.5, textColor=NAVY, leading=13,
            leftIndent=14, bulletIndent=4, spaceAfter=2),
        "note_frame": ParagraphStyle(
            "note_frame", parent=ss["Normal"], fontName="Helvetica",
            fontSize=9, textColor=NAVY, leading=12,
            spaceAfter=0, alignment=TA_LEFT),
        "signature_lbl": ParagraphStyle(
            "signature_lbl", parent=ss["Normal"], fontName="Helvetica",
            fontSize=9.5, textColor=NAVY, leading=15, spaceAfter=2),
        "signature_hd": ParagraphStyle(
            "signature_hd", parent=ss["Normal"], fontName="Helvetica-Bold",
            fontSize=10.5, textColor=NAVY, leading=14, spaceAfter=6),
    }


# ─── Header / Footer ──────────────────────────────────────────────────────
_LOGO_PATH_CACHE = None
_CACHET_PATH_CACHE = None


def _locate_logo():
    global _LOGO_PATH_CACHE
    if _LOGO_PATH_CACHE is not None:
        return _LOGO_PATH_CACHE or None
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
    _LOGO_PATH_CACHE = ""
    return None


def _locate_cachet():
    """Localise le PNG du cachet SIFA (fichier `static/sifa_cachet.png`).
    Retourne le chemin absolu si trouvé, None sinon. Le cachet est apposé
    dans la section 8 (Signature) de la Déclaration UE de Conformité."""
    global _CACHET_PATH_CACHE
    if _CACHET_PATH_CACHE is not None:
        return _CACHET_PATH_CACHE or None
    here = _os.path.dirname(_os.path.abspath(__file__))
    candidates = [
        _os.path.abspath(_os.path.join(here, "..", "..", "static", "sifa_cachet.png")),
        _os.path.abspath(_os.path.join(here, "..", "static", "sifa_cachet.png")),
        _os.path.abspath(_os.path.join(here, "..", "..", "app", "static", "sifa_cachet.png")),
    ]
    for path in candidates:
        if _os.path.exists(path):
            _CACHET_PATH_CACHE = path
            return path
    _CACHET_PATH_CACHE = ""
    return None


def _draw_logo(canvas_, x, y_top):
    """Place le logo dans le coin supérieur gauche. y_top = bord haut du logo."""
    logo_path = _locate_logo()
    canvas_.saveState()
    if logo_path:
        try:
            from reportlab.lib.utils import ImageReader
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            target_w = 30 * mm
            target_h = target_w * (ih / iw) if iw else 14 * mm
            # Bottom-left origin en PDF : le point (x, y_bottom) est le coin bas-gauche
            y_bottom = y_top - target_h
            canvas_.drawImage(logo_path, x, y_bottom,
                              width=target_w, height=target_h,
                              preserveAspectRatio=True, mask="auto")
            canvas_.restoreState()
            return
        except Exception:
            pass
    # Fallback texte
    canvas_.setFillColor(YELLOW)
    canvas_.rect(x, y_top - 9 * mm, 26 * mm, 9 * mm, fill=1, stroke=0)
    canvas_.setFillColor(BLACK)
    canvas_.setFont("Helvetica-Bold", 14)
    canvas_.drawString(x + 5 * mm, y_top - 6.5 * mm, "SIFA")
    canvas_.restoreState()


def _page_decor(canvas_, doc, ref: str, header_date: str, total_pages_hint: int = 3):
    canvas_.saveState()
    page_w, page_h = A4
    _draw_logo(canvas_, 15 * mm, page_h - 8 * mm)
    canvas_.setFillColor(GREY)
    canvas_.setFont("Helvetica-Oblique", 8.5)
    canvas_.drawRightString(page_w - 15 * mm, page_h - 14 * mm,
                            "SIFA — Déclaration UE de Conformité")
    canvas_.drawRightString(page_w - 15 * mm, page_h - 19 * mm,
                            f"{header_date} Réf. {ref}")
    canvas_.setStrokeColor(BORDER)
    canvas_.setLineWidth(0.4)
    canvas_.line(15 * mm, page_h - 25 * mm, page_w - 15 * mm, page_h - 25 * mm)
    canvas_.line(15 * mm, 26 * mm, page_w - 15 * mm, 26 * mm)
    canvas_.setFillColor(GREY)
    canvas_.setFont("Helvetica", 8.5)
    canvas_.drawCentredString(page_w / 2, 20 * mm,
                              "SIFA · 45 rue Rollin · 59100 Roubaix · France")
    canvas_.setFont("Helvetica", 8)
    canvas_.drawCentredString(page_w / 2, 15.5 * mm,
                              "+33 (0)3 20 69 01 01 · commandes@sifa.pro")
    canvas_.drawCentredString(page_w / 2, 11 * mm, f"Page {doc.page}")
    canvas_.restoreState()


# ═══════════════════════════════════════════════════════════════════════════
# TEXTES PAR DÉFAUT PAR SECTION
# ═══════════════════════════════════════════════════════════════════════════
# Chaque section a un texte principal (body) surchargeable via `custom_body`
# dans les overrides. Les éléments graphiques (tableaux, encadrés) restent
# fixes — on ne surcharge que le paragraphe descriptif principal.

SEC_2_BODY = (
    "SIFA fabrique les étiquettes adhésives, avec ou sans enduction, "
    "à partir de matières déjà complexées ou à partir de glassines, adhésifs "
    "et frontaux assemblés en interne."
)

SEC_4_INTRO = (
    "SIFA atteste, sur la base des attestations fournisseurs conservées au "
    "dossier technique, que les matières entrant dans les étiquettes livrées "
    "à ce client respectent les exigences suivantes."
)

SEC_4_1_BODY = (
    "Règlement (CE) n° 1907/2006. Aucune substance figurant sur la liste "
    "candidate SVHC de l'ECHA n'est présente à une concentration supérieure "
    "à 0,1 % (w/w), qu'elle soit ajoutée intentionnellement ou présente en "
    "tant qu'impureté. Les fournisseurs s'engagent à notifier SIFA en cas "
    "d'évolution."
)

SEC_4_2_BODY = (
    "Aucune substance de la liste OEHHA n'est intentionnellement ajoutée aux "
    "matières. Les traces éventuelles restent inférieures aux seuils NSRL "
    "et MADL applicables."
)

SEC_4_3_BODY = (
    "Directive 94/62/CE (art. 11) et Model Toxics in Packaging Legislation "
    "(CONEG). Plomb (Pb), cadmium (Cd), mercure (Hg) et chrome hexavalent "
    "(Cr VI) ne sont pas intentionnellement ajoutés aux matières. Les seuils "
    "individuels attestés par les fournisseurs sont :"
)

SEC_4_4_BODY = (
    "Les frontaux papier sont issus de fournisseurs sous chaîne de contrôle "
    "FSC valide."
)

SEC_4_4_NOTE = (
    "<b>Note — Certification FSC SIFA en cours.</b> SIFA sera auditée le "
    "8 octobre 2026 en vue de l'obtention de sa propre chaîne de contrôle "
    "FSC. Le numéro de licence SIFA sera intégré à cette DoC dès délivrance."
)

SEC_4_5_BODY = (
    "Les fournisseurs de SIFA certifient l'absence d'ajout intentionnel de "
    "substances PFAS (per- et polyfluoroalkyles, incluant PFOA, PFOS et GenX) "
    "dans les matières livrées. <i>Les fournisseurs ne réalisent pas d'analyse "
    "de routine sur ces substances.</i>"
)

SEC_4_6_BODY = (
    "Aucun ajout intentionnel de bisphénol A, bisphénol S ou bisphénol F "
    "dans les matières."
)

SEC_4_7_BODY = (
    "Selon les fournisseurs, SIFA reçoit des certificats d'analyse (CoA) "
    "délivrés par des laboratoires indépendants sur les adhésifs concernés. "
    "Ces certificats attestent de la conformité de ces adhésifs au règlement "
    "(CE) n°1935/2004 et au règlement (UE) n°10/2011, applicables aux "
    "matériaux destinés à entrer en contact avec les denrées alimentaires. "
    "Les CoA disponibles sont conservés au dossier technique SIFA et "
    "communicables sur demande."
)

SEC_4_8_BODY = (
    "La présente Déclaration est établie conformément à l'Annexe VIII du "
    "règlement (UE) 2025/40 (PPWR), applicable à compter du 12 août 2026."
)

SEC_4_9_BODY = (
    "À la date d'émission, aucune évaluation formelle de recyclabilité "
    "(Recyclass, COTREP, CEREC) n'a été réalisée sur les étiquettes couvertes "
    "par la présente Déclaration. Les matières utilisées sont issues de "
    "fournisseurs qui appliquent les recommandations d'éco-conception "
    "publiées par la filière (Guide technique UNFEA / Citeo — Éco-conception "
    "des étiquettes adhésives, édition 2026). <i>Une évaluation formelle est "
    "engagée par SIFA. Les résultats seront intégrés à la présente Déclaration "
    "dès disponibilité.</i>"
)

SEC_5_BODY = (
    "À la date d'émission, au moins un des fournisseurs de SIFA ne livre pas "
    "ses matières sous forme recyclée. SIFA ne peut donc pas garantir un taux "
    "de contenu recyclé pour l'ensemble de sa gamme au sens de l'article 7 "
    "du PPWR."
)

SEC_6_BODY = (
    "La présente Déclaration s'appuie sur l'ensemble des documents du dossier "
    "technique SIFA : attestations fournisseurs, certificats de conformité, "
    "certificats FSC, certificats d'analyse de laboratoire et fiches techniques "
    "produit. L'ensemble de ces pièces est conservé au dossier technique et "
    "communicable au client ou à toute autorité compétente sous 10 jours "
    "ouvrés sur demande écrite."
)

SEC_7_BODY = (
    "Déclaration établie sous la seule responsabilité de SIFA en tant que "
    "fabricant. Toute évolution des matières, du statut d'un fournisseur ou "
    "de la liste candidate SVHC entraîne réémission. SIFA n'est pas "
    "responsable des usages non conformes aux fiches techniques produit ni "
    "des transformations ultérieures effectuées par le client."
)

SEC_8_BODY = (
    "Fait à Roubaix, la présente Déclaration engage la responsabilité "
    "de SIFA."
)


# ═══════════════════════════════════════════════════════════════════════════
# BUILDERS PAR SECTION — chacun retourne List[Flowable]
# ═══════════════════════════════════════════════════════════════════════════
def _h2(title, S):
    return [Paragraph(title, S["h2"]),
            HRFlowable(width="100%", thickness=0.6, color=BORDER, spaceAfter=6)]


def _sec_1(ctx, body, num=1):
    S = ctx["styles"]
    out = _h2(f"{num}. Fabricant", S)
    fab_data = [
        [Paragraph("<b>Raison sociale</b>", S["body"]),
         Paragraph("SIFA", S["body"])],
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
    out.append(fab_tbl)
    return out


def _sec_2(ctx, body, num=2):
    S = ctx["styles"]
    out = _h2(f"{num}. Nature de l'activité SIFA", S)
    out.append(Paragraph(body or SEC_2_BODY, S["body"]))
    return out


def _sec_3(ctx, body, num=3):
    S = ctx["styles"]
    out = _h2(f"{num}. Fournisseurs — origine géographique", S)
    client_nom = ctx["client_nom"]
    fournisseurs = ctx["fournisseurs"]
    if client_nom:
        out.append(Paragraph(
            f"Pour les étiquettes livrées à <b>{_esc(client_nom)}</b>, les "
            f"matières entrant dans les étiquettes proviennent des "
            f"fournisseurs suivants :", S["body"]))
    else:
        out.append(Paragraph(
            "Les matières entrant dans les étiquettes proviennent des "
            "fournisseurs suivants :", S["body"]))
    for f in fournisseurs:
        nom = _esc((f.get("nom") or "").strip())
        pays = _esc((f.get("pays_origine") or "").strip()) or "origine à préciser"
        out.append(Paragraph(
            f"• <b>{nom}</b> — matières fabriquées en {pays}.", S["bullet"]))
    out.append(Spacer(1, 4))
    out.append(Paragraph(
        "Toutes les matières à l'origine de la fabrication des étiquettes "
        "couvertes par la présente Déclaration sont fabriquées au sein de "
        "l'Union européenne ou du Royaume-Uni.", S["body"]))
    return out


def _sec_4_intro(ctx, body, num=4):
    S = ctx["styles"]
    out = _h2(f"{num}. Conformités attestées", S)
    out.append(Paragraph(body or SEC_4_INTRO, S["body"]))
    return out


def _sec_4_1(ctx, body, parent_num=4, sub_num=1):
    S = ctx["styles"]
    return [Paragraph(f"{parent_num}.{sub_num} REACH — Substances extrêmement préoccupantes (SVHC)",
                      S["h3"]),
            Paragraph(body or SEC_4_1_BODY, S["body"])]


def _sec_4_2(ctx, body, parent_num=4, sub_num=2):
    S = ctx["styles"]
    return [Paragraph(f"{parent_num}.{sub_num} California Proposition 65", S["h3"]),
            Paragraph(body or SEC_4_2_BODY, S["body"])]


def _sec_4_3(ctx, body, parent_num=4, sub_num=3):
    S = ctx["styles"]
    inner = [Paragraph(f"{parent_num}.{sub_num} Métaux lourds — traces techniquement inévitables",
                       S["h3"]),
             Paragraph(body or SEC_4_3_BODY, S["body"])]
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
    inner.append(m_tbl)
    # KeepTogether garantit que titre + paragraphe + tableau tiennent sur une page
    return [KeepTogether(inner)]


def _sec_4_4(ctx, body, parent_num=4, sub_num=4):
    S = ctx["styles"]
    # Note : l'encadré jaune FSC en cours est rendu séparément par le builder
    # _sec_4_4_note (section pseudo « sec_4_4_note »). Cela permet à l'admin
    # de retirer/éditer la note indépendamment du corps de la sous-section 4.4.
    return [Paragraph(f"{parent_num}.{sub_num} Certification FSC", S["h3"]),
            Paragraph(body or SEC_4_4_BODY, S["body"])]


def _sec_4_4_note(ctx, body):
    """Encadré jaune « FSC en cours » — rendu inline sous 4.4 sans numéro
    propre. Editable + removable via SECTIONS_META (flag is_note=True)."""
    S = ctx["styles"]
    note_para = Paragraph(body or SEC_4_4_NOTE, S["note_frame"])
    note_tbl = Table([[note_para]], colWidths=[180 * mm])
    note_tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, YELLOW),
        ("BACKGROUND", (0, 0), (-1, -1), YELLOW_BG),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return [Spacer(1, 4), note_tbl, Spacer(1, 4)]


def _sec_4_5(ctx, body, parent_num=4, sub_num=5):
    S = ctx["styles"]
    return [Paragraph(f"{parent_num}.{sub_num} Absence de PFAS", S["h3"]),
            Paragraph(body or SEC_4_5_BODY, S["body"])]


def _sec_4_6(ctx, body, parent_num=4, sub_num=6):
    S = ctx["styles"]
    return [Paragraph(f"{parent_num}.{sub_num} Absence de bisphénols (BPA, BPS, BPF)", S["h3"]),
            Paragraph(body or SEC_4_6_BODY, S["body"])]


def _sec_4_7(ctx, body, parent_num=4, sub_num=7):
    S = ctx["styles"]
    return [Paragraph(f"{parent_num}.{sub_num} Certificats d'analyse laboratoire (CoA)", S["h3"]),
            Paragraph(body or SEC_4_7_BODY, S["body"])]


def _sec_4_8(ctx, body, parent_num=4, sub_num=8):
    S = ctx["styles"]
    return [Paragraph(f"{parent_num}.{sub_num} Cadre général — PPWR", S["h3"]),
            Paragraph(body or SEC_4_8_BODY, S["body"])]


def _sec_4_9(ctx, body, parent_num=4, sub_num=9):
    S = ctx["styles"]
    return [Paragraph(f"{parent_num}.{sub_num} Recyclabilité", S["h3"]),
            Paragraph(body or SEC_4_9_BODY, S["body"])]


def _sec_5(ctx, body, num=5):
    S = ctx["styles"]
    out = _h2(f"{num}. Contenu recyclé", S)
    out.append(Paragraph(body or SEC_5_BODY, S["body"]))
    return out


def _sec_6(ctx, body, num=6):
    S = ctx["styles"]
    out = _h2(f"{num}. Base documentaire", S)
    out.append(Paragraph(body or SEC_6_BODY, S["body"]))
    return out


def _sec_7(ctx, body, num=7):
    S = ctx["styles"]
    out = _h2(f"{num}. Responsabilité et validité", S)
    validite_mois = ctx["validite_mois"]
    out.append(Paragraph(
        f"<b>Validité : {int(validite_mois)} mois à compter de la date "
        f"d'émission.</b>", S["body"]))
    out.append(Paragraph(body or SEC_7_BODY, S["body"]))
    return out


def _sec_8(ctx, body, num=8):
    S = ctx["styles"]
    out = _h2(f"{num}. Signature et cachet", S)
    out.append(Paragraph(body or SEC_8_BODY, S["body"]))
    out.append(Spacer(1, 10))
    annee = ctx["annee"]
    representant = (ctx.get("representant") or "").strip()
    nom_line = (
        f"Nom : <b>{_esc(representant)}</b>"
        if representant
        else "Nom : ______________________________"
    )
    sig_left = [
        Paragraph("<b>Représentant SIFA</b>", S["signature_hd"]),
        Paragraph(nom_line, S["signature_lbl"]),
        Paragraph("Fonction : __________________________", S["signature_lbl"]),
        Paragraph(f"Date : ____ / ____ / {annee}", S["signature_lbl"]),
        Paragraph("Signature :", S["signature_lbl"]),
        Spacer(1, 40),
        Paragraph("______________________________________", S["signature_lbl"]),
    ]
    # Cachet : si le PNG statique est présent, on l'affiche ; sinon on garde
    # le cadre pointillé « Emplacement réservé au cachet » qui laisse la place
    # à un tampon manuel après impression.
    cachet_path = _locate_cachet()
    cachet_flow = None
    if cachet_path:
        try:
            from reportlab.platypus import Image as _RLImage
            from reportlab.lib.utils import ImageReader as _RLReader
            _img = _RLReader(cachet_path)
            _iw, _ih = _img.getSize()
            target_w = 55 * mm
            target_h = target_w * (_ih / _iw) if _iw else 55 * mm
            # On borne la hauteur pour ne pas déborder du bloc signature
            if target_h > 55 * mm:
                target_h = 55 * mm
                target_w = target_h * (_iw / _ih) if _ih else target_w
            cachet_flow = _RLImage(cachet_path, width=target_w, height=target_h)
            cachet_flow.hAlign = "CENTER"
        except Exception:
            cachet_flow = None
    if cachet_flow is None:
        cachet_style = ParagraphStyle("cachet", parent=S["body_it"],
                                      alignment=TA_CENTER, textColor=MUTED)
        cachet_frame = Table(
            [[Paragraph("<i>[Emplacement réservé au cachet]</i>", cachet_style)]],
            colWidths=[75 * mm], rowHeights=[55 * mm])
        cachet_frame.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.8, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("DASHED", (0, 0), (-1, -1), 2),
        ]))
        cachet_flow = cachet_frame
    sig_right = [
        Paragraph("<b>Cachet SIFA</b>", S["signature_hd"]),
        Spacer(1, 6),
        cachet_flow,
    ]
    sig_tbl = Table([[sig_left, sig_right]], colWidths=[95 * mm, 85 * mm])
    sig_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    out.append(sig_tbl)
    out.append(Spacer(1, 30))
    out.append(HRFlowable(width="40%", thickness=0.4, color=BORDER,
                          hAlign="CENTER", spaceAfter=6))
    out.append(Paragraph(
        "<i>Document établi conformément à l'Annexe VIII du règlement "
        "(UE) 2025/40 (PPWR).</i>",
        ParagraphStyle("foot1", parent=S["body_it"], alignment=TA_CENTER,
                       textColor=MUTED, fontSize=9)))
    out.append(Paragraph(
        f"<i>Référence unique : {_esc(ctx['ref'])} — Version 1.0</i>",
        ParagraphStyle("foot2", parent=S["body_it"], alignment=TA_CENTER,
                       textColor=MUTED, fontSize=9)))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# REGISTRY DES SECTIONS
# ═══════════════════════════════════════════════════════════════════════════
# id            : identifiant unique — utilisé dans les overrides et l'UI
# title         : titre affiché dans l'UI de personnalisation
# removable     : peut être exclu du PDF via override include=False
# editable      : peut recevoir un custom_body qui remplace le paragraphe principal
# default_body  : texte par défaut affiché dans l'UI de personnalisation
# builder       : fonction (ctx, body) -> List[Flowable]
SECTIONS_META = [
    {"id": "sec_1", "is_main": True, "title": "1. Fabricant", "removable": False,
     "editable": False, "default_body": "", "builder": _sec_1},
    {"id": "sec_2", "is_main": True, "title": "2. Nature de l'activité SIFA",
     "removable": True, "editable": True, "default_body": SEC_2_BODY,
     "builder": _sec_2},
    {"id": "sec_3", "is_main": True, "title": "3. Fournisseurs — origine géographique",
     "removable": False, "editable": False, "default_body": "",
     "builder": _sec_3},
    {"id": "sec_4_intro", "is_main": True, "title": "4. Conformités attestées (intro)",
     "removable": False, "editable": True, "default_body": SEC_4_INTRO,
     "builder": _sec_4_intro},
    {"id": "sec_4_1", "sub_group": "4", "parent": "sec_4_intro", "title": "4.1 REACH — SVHC",
     "removable": True, "editable": True, "default_body": SEC_4_1_BODY,
     "builder": _sec_4_1},
    {"id": "sec_4_2", "sub_group": "4", "parent": "sec_4_intro", "title": "4.2 California Proposition 65",
     "removable": True, "editable": True, "default_body": SEC_4_2_BODY,
     "builder": _sec_4_2},
    {"id": "sec_4_3", "sub_group": "4", "parent": "sec_4_intro", "title": "4.3 Métaux lourds",
     "removable": True, "editable": True, "default_body": SEC_4_3_BODY,
     "builder": _sec_4_3},
    {"id": "sec_4_4", "sub_group": "4", "parent": "sec_4_intro", "title": "4.4 Certification FSC",
     "removable": True, "editable": True, "default_body": SEC_4_4_BODY,
     "builder": _sec_4_4},
    {"id": "sec_4_4_note", "sub_group": "4", "parent": "sec_4_intro", "is_note": True,
     "title": "4.4 (encadré) — Note FSC en cours",
     "removable": True, "editable": True, "default_body": SEC_4_4_NOTE,
     "builder": _sec_4_4_note},
    {"id": "sec_4_5", "sub_group": "4", "parent": "sec_4_intro", "title": "4.5 Absence de PFAS",
     "removable": True, "editable": True, "default_body": SEC_4_5_BODY,
     "builder": _sec_4_5},
    {"id": "sec_4_6", "sub_group": "4", "parent": "sec_4_intro", "title": "4.6 Absence de bisphénols",
     "removable": True, "editable": True, "default_body": SEC_4_6_BODY,
     "builder": _sec_4_6},
    {"id": "sec_4_7", "sub_group": "4", "parent": "sec_4_intro", "title": "4.7 Certificats d'analyse laboratoire (CoA)",
     "removable": True, "editable": True, "default_body": SEC_4_7_BODY,
     "builder": _sec_4_7},
    {"id": "sec_4_8", "sub_group": "4", "parent": "sec_4_intro", "title": "4.8 Cadre général — PPWR",
     "removable": True, "editable": True, "default_body": SEC_4_8_BODY,
     "builder": _sec_4_8},
    {"id": "sec_4_9", "sub_group": "4", "parent": "sec_4_intro", "title": "4.9 Recyclabilité",
     "removable": True, "editable": True, "default_body": SEC_4_9_BODY,
     "builder": _sec_4_9},
    {"id": "sec_5", "is_main": True, "title": "5. Contenu recyclé",
     "removable": True, "editable": True, "default_body": SEC_5_BODY,
     "builder": _sec_5},
    {"id": "sec_6", "is_main": True, "title": "6. Base documentaire",
     "removable": True, "editable": True, "default_body": SEC_6_BODY,
     "builder": _sec_6},
    {"id": "sec_7", "is_main": True, "title": "7. Responsabilité et validité",
     "removable": False, "editable": True, "default_body": SEC_7_BODY,
     "builder": _sec_7},
    {"id": "sec_8", "is_main": True, "title": "8. Signature et cachet",
     "removable": False, "editable": True, "default_body": SEC_8_BODY,
     "builder": _sec_8},
]


def get_sections_meta():
    """Expose la liste des sections (id, titre, flags, texte par défaut) au
    frontend — sans les builders (non sérialisables)."""
    return [
        {k: v for k, v in s.items() if k != "builder"}
        for s in SECTIONS_META
    ]


# ═══════════════════════════════════════════════════════════════════════════
# ORCHESTRATION
# ═══════════════════════════════════════════════════════════════════════════
def _title_block(ctx):
    S = ctx["styles"]
    out = [Paragraph("DÉCLARATION UE DE CONFORMITÉ", S["title"]),
           Paragraph("EU Declaration of Conformity (DoC)", S["subtitle"])]
    jour, mois, annee = _fr_date_parts(ctx["date_emission_iso"])
    id_data = [
        [Paragraph("<b>Numéro d'identification unique</b>", S["body"]),
         Paragraph(f"{_esc(ctx['ref'])}", S["body"])],
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
    out.append(id_tbl)
    out.append(Spacer(1, 12))
    return out


def _build_flowables(ctx, sections_overrides):
    story = _title_block(ctx)
    ov_all = sections_overrides or {}
    # Overrides « par défaut du template » édités par les admins qualité.
    # Priorité de résolution du body d'une section :
    #   1. version.sections_overrides[sec_id].custom_body  (par client)
    #   2. template.default_body_overrides[sec_id]         (par template)
    #   3. SEC_*_BODY hardcodé (via `body or SEC_X_BODY` dans les builders)
    tpl_ov_all = ctx.get("template_default_overrides") or {}

    def _skipped(sec):
        ov = ov_all.get(sec["id"], {})
        return sec["removable"] and ov.get("include") is False

    # Étape 1 : renumérotation dynamique des sections principales
    # (retirer "2. Nature" → la suivante devient "2" au lieu de "3")
    main_counter = 0
    main_num_by_id = {}
    for sec in SECTIONS_META:
        if not sec.get("is_main"):
            continue
        if _skipped(sec):
            continue
        main_counter += 1
        main_num_by_id[sec["id"]] = main_counter

    # Étape 2 : renumérotation des sous-sections (ex. 4.x)
    # Pour chaque sous-section, on retient le num du parent (renuméroté)
    # et un sub_num incrémenté au sein de ce parent.
    sub_counters = {}   # parent_id → compteur
    sub_info_by_id = {} # id → {"parent_num": int, "sub_num": int}
    for sec in SECTIONS_META:
        parent_id = sec.get("parent")
        if not parent_id:
            continue
        if _skipped(sec):
            continue
        # Notes inline (encadrés) : rendues sous leur parent sans numéro propre
        # (ex. sec_4_4_note s'affiche sous 4.4 sans devenir 4.5).
        if sec.get("is_note"):
            continue
        parent_num = main_num_by_id.get(parent_id)
        if parent_num is None:
            # Le parent a été retiré : on skip la sous-section aussi
            continue
        sub_counters[parent_id] = sub_counters.get(parent_id, 0) + 1
        sub_info_by_id[sec["id"]] = {
            "parent_num": parent_num,
            "sub_num": sub_counters[parent_id],
        }

    # Étape 3 : rendu
    for sec in SECTIONS_META:
        if _skipped(sec):
            continue
        # Si sous-section dont le parent a été retiré : skip
        parent_id = sec.get("parent")
        if parent_id and parent_id not in main_num_by_id:
            continue

        # Résolution du body : priorité version.custom_body → template default
        # override → SEC_*_BODY hardcodé (fallback dans le builder).
        body = None
        if sec["editable"]:
            v_custom = ov_all.get(sec["id"], {}).get("custom_body")
            if v_custom and str(v_custom).strip():
                body = str(v_custom).strip()
            else:
                t_default = tpl_ov_all.get(sec["id"])
                if t_default and str(t_default).strip():
                    body = str(t_default).strip()

        # Appeler le builder avec les bons kwargs de numérotation
        if sec.get("is_main"):
            story.extend(sec["builder"](ctx, body, num=main_num_by_id[sec["id"]]))
        elif sec["id"] in sub_info_by_id:
            info = sub_info_by_id[sec["id"]]
            story.extend(sec["builder"](ctx, body,
                                        parent_num=info["parent_num"],
                                        sub_num=info["sub_num"]))
        else:
            story.extend(sec["builder"](ctx, body))
    return story


def build_declaration_ue_pdf(*, client_nom: str, fournisseurs: list,
                             ref: str, date_emission_iso: str,
                             validite_mois: int = 12,
                             sections_overrides: dict = None,
                             template_default_overrides: dict = None,
                             representant: str = None) -> bytes:
    """
    Génère un PDF de Déclaration UE de Conformité.

    Args:
        client_nom: Nom du client destinataire
        fournisseurs: Liste [{"nom": str, "pays_origine": str, ...}]
        ref: Référence unique du document
        date_emission_iso: Date d'émission (YYYY-MM-DD)
        validite_mois: Durée de validité en mois (12 par défaut)
        sections_overrides: {section_id: {"include": bool, "custom_body": str}}
            - include=False → la section est retirée du PDF (si removable)
            - custom_body → remplace le paragraphe principal (si editable)
        template_default_overrides: {section_id: str} — textes par défaut
            édités par les admins qualité au niveau du template. Priorité
            inférieure aux overrides de version, supérieure aux SEC_*_BODY
            hardcodés.
        representant: Nom du représentant SIFA qui signe (section 8). Si
            fourni, remplace la ligne « Nom : ____ » par le nom en gras.

    Returns:
        bytes: contenu binaire du PDF
    """
    buf = BytesIO()
    styles = _make_styles()
    header_date = _fr_month_year(date_emission_iso)
    _, _, annee = _fr_date_parts(date_emission_iso)

    ctx = {
        "styles": styles,
        "client_nom": client_nom or "",
        "fournisseurs": fournisseurs or [],
        "ref": ref,
        "date_emission_iso": date_emission_iso,
        "validite_mois": validite_mois,
        "annee": annee,
        "template_default_overrides": template_default_overrides or {},
        "representant": representant or "",
    }

    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=30 * mm, bottomMargin=32 * mm,
        title=f"SIFA - Déclaration UE - {client_nom}",
        author="SIFA",
        subject="Déclaration UE de Conformité",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  doc.width, doc.height, id="body_frame",
                  leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0)

    def _on_page(canvas_, doc_):
        _page_decor(canvas_, doc_, ref=ref, header_date=header_date)

    doc.addPageTemplates([PageTemplate(id="main", frames=[frame],
                                       onPage=_on_page)])
    story = _build_flowables(ctx, sections_overrides or {})
    doc.build(story)
    return buf.getvalue()


# ─── Registry générique multi-templates ──────────────────────────────────
TEMPLATE_BUILDERS = {
    "declaration_ue": build_declaration_ue_pdf,
}

TEMPLATE_SECTIONS = {
    "declaration_ue": get_sections_meta,
}


def build_template_pdf(template_code: str, **kwargs) -> bytes:
    builder = TEMPLATE_BUILDERS.get(template_code)
    if not builder:
        raise ValueError(f"Template inconnu: {template_code}")
    return builder(**kwargs)


def get_template_sections(template_code: str):
    fn = TEMPLATE_SECTIONS.get(template_code)
    if not fn:
        return []
    return fn()
