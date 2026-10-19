"""MyQualité — questionnaire EUDR en PDF, à remplir à la main.

Pour le fournisseur qui préfère répondre sur papier ou joindre le document à
son propre circuit de validation. Mêmes questions, mêmes choix et mêmes textes
que le formulaire en ligne (`app/web/eudr_portail_page.py`, `config.EUDR_CHOIX`),
dans la langue demandée. La réponse revient par email et se saisit dans
MyQualité (« Saisie manuelle »).
"""

from __future__ import annotations

import io
import re
from xml.sax.saxutils import escape

from config import APP_ORG_NAME, EUDR_CHOIX, eudr_langue

# Phrases propres au PDF (le reste vient des textes du formulaire en ligne).
_PDF = {
    "en": {"supplier": "Supplier", "return": "Please return this completed questionnaire to:",
           "date_sign": "Date and signature", "origin_note": "Only if your company is established outside the EU.",
           "page": "Page"},
    "fr": {"supplier": "Fournisseur", "return": "Merci de retourner ce questionnaire complété à :",
           "date_sign": "Date et signature", "origin_note": "Uniquement si votre société est établie hors de l'UE.",
           "page": "Page"},
    "es": {"supplier": "Proveedor", "return": "Les rogamos devuelvan este cuestionario cumplimentado a:",
           "date_sign": "Fecha y firma", "origin_note": "Solo si su empresa está establecida fuera de la UE.",
           "page": "Página"},
}


def _textes(lang: str) -> dict:
    from app.web.eudr_portail_page import _I18N
    return {k: v.replace("__ORG__", APP_ORG_NAME) for k, v in _I18N[lang].items()}


def construire_pdf(langue: str | None, *, fournisseur: str = "", retour: str = "") -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Flowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    class Case(Flowable):
        """Case à cocher : un carré de 3,4 mm aligné sur la première ligne."""
        def wrap(self, *args):
            return 3.4 * mm, 3.4 * mm

        def draw(self):
            self.canv.setStrokeColor(gris)
            self.canv.setLineWidth(0.8)
            self.canv.rect(0, 0, 3.4 * mm, 3.4 * mm)

    lang = eudr_langue(langue)
    t = _textes(lang)
    p = _PDF[lang]
    accent = colors.HexColor("#0891b2")  # hex-ok : PDF reportlab
    gris = colors.HexColor("#64748b")    # hex-ok : PDF reportlab
    trait = colors.HexColor("#cbd5e1")   # hex-ok : PDF reportlab

    st = {
        "brand": ParagraphStyle("brand", fontName="Helvetica-Bold", fontSize=8, textColor=accent, leading=10),
        "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=18, leading=22, spaceAfter=2),
        "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=9, textColor=gris, leading=12),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9, leading=12.5, spaceAfter=5),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=10, textColor=accent, leading=13,
                             spaceBefore=10, spaceAfter=6, keepWithNext=1),
        "q": ParagraphStyle("q", fontName="Helvetica-Bold", fontSize=9, leading=12, spaceAfter=3),
        "hint": ParagraphStyle("hint", fontName="Helvetica-Oblique", fontSize=8, textColor=gris, leading=10,
                               spaceAfter=3),
        "opt": ParagraphStyle("opt", fontName="Helvetica", fontSize=9, leading=11.5),
    }

    def para(texte: str, style: str) -> Paragraph:
        # Les textes d'intro portent <b> : on le garde, on échappe le reste.
        brut = escape(texte).replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
        return Paragraph(brut, st[style])

    def libelle(cle: str, oblig: bool = False) -> Paragraph:
        return para(t[cle] + (" *" if oblig else ""), "q")

    def ligne(hauteur: float = 7 * mm) -> Table:
        tb = Table([[""]], colWidths=[170 * mm], rowHeights=[hauteur], hAlign="LEFT")
        tb.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.6, trait)]))
        return tb

    def zone(hauteur: float = 18 * mm) -> Table:
        tb = Table([[""]], colWidths=[170 * mm], rowHeights=[hauteur], hAlign="LEFT")
        tb.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, trait)]))
        return tb

    def champ(cle: str, oblig: bool = False, hint: str | None = None, grand: bool = False) -> KeepTogether:
        items = [libelle(cle, oblig)]
        if hint:
            items.append(para(t[hint], "hint"))
        items += [zone() if grand else ligne(), Spacer(1, 4 * mm)]
        return KeepTogether(items)

    def choix(cle: str, nom: str, oblig: bool = False, hint: str | None = None) -> KeepTogether:
        items = [libelle(cle, oblig)]
        if hint:
            items.append(para(t[hint], "hint"))
        lignes = [[Case(), para(v[lang], "opt")] for v in EUDR_CHOIX[nom].values()]
        tb = Table(lignes, colWidths=[6 * mm, 164 * mm])
        style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2),
                 ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("LEFTPADDING", (0, 0), (0, -1), 0)]
        tb.setStyle(TableStyle(style + [("LEFTPADDING", (1, 0), (1, -1), 4), ("TOPPADDING", (0, 0), (0, -1), 3)]))
        tb.hAlign = "LEFT"
        return KeepTogether(items + [tb, Spacer(1, 4 * mm)])

    def petit_champ(cle: str, oblig: bool = False) -> list:
        tb = Table([[""]], colWidths=[80 * mm], rowHeights=[7 * mm], hAlign="LEFT")
        tb.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.6, trait)]))
        return [libelle(cle, oblig), tb, Spacer(1, 3 * mm)]

    def bloc_deux(c1: str, c2: str, o1: bool = False, o2: bool = False) -> Table:
        tb = Table([[petit_champ(c1, o1), petit_champ(c2, o2)]], colWidths=[85 * mm, 85 * mm], hAlign="LEFT")
        tb.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        return tb

    h: list = [
        para(t["brand"], "brand"), Spacer(1, 2 * mm),
        para(t["title"], "h1"),
        para(f"{p['supplier']} : {fournisseur}" if fournisseur else p["supplier"] + " : ______________________", "sub"),
        Spacer(1, 4 * mm),
        para(t["intro_purpose"], "body"), para(t["intro_eudr"], "body"), para(t["intro_how"].split(". ")[0] + ".", "body"),
        para(t["s_you"], "h2"),
        champ("q_company", True),
        bloc_deux("q_name", "q_position", o1=True),
        bloc_deux("q_email", "q_phone", o1=True),
        para(f"{t['part'].replace('{n}', '1')} · {t['p1']}", "h2"),
        choix("q_etab", "etablissement"),
        choix("q_scope", "perimetre", hint="h_scope"),
        champ("q_cn", hint="h_cn"),
        choix("q_role", "role", oblig=True),
        champ("q_date"),
        para(f"{t['part'].replace('{n}', '2')} · {t['p2']}", "h2"),
        choix("q_trans", "transmission"),
        champ("q_detail", grand=True),
        choix("q_perdel", "ref_par_livraison"),
        champ("q_amont", hint="h_amont", grand=True),
        para(t["s_origin"], "h2"),
        para(p["origin_note"] + " " + t["h_origin"], "hint"),
        choix("q_geo", "geolocalisation"),
        champ("q_species"),
        champ("q_countries"),
        para(f"{t['part'].replace('{n}', '3')} · {t['p3']}", "h2"),
        bloc_deux("q_cname", "q_cemail"),
        champ("q_comment", grand=True),
        Spacer(1, 4 * mm),
        KeepTogether([para(p["date_sign"], "q"), zone(16 * mm)]),
    ]
    if retour:
        h += [Spacer(1, 5 * mm), para(f"{p['return']} <b>{escape(retour)}</b>", "body")]

    buf = io.BytesIO()

    def pied(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(gris)
        canvas.drawString(20 * mm, 10 * mm, re.sub(r"\s+", " ", f"{t['title']} — {t['brand']}"))
        canvas.drawRightString(190 * mm, 10 * mm, f"{p['page']} {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=16 * mm, bottomMargin=18 * mm,
                            title=f"{t['title']} — {APP_ORG_NAME}", author=APP_ORG_NAME)
    doc.build(h, onFirstPage=pied, onLaterPages=pied)
    return buf.getvalue()
