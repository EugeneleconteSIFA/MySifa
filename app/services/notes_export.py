"""MySifa — Mes notes : export d'une note en PDF, en Word et en page imprimable.

Le contenu est la suite de blocs de la note (app/services/notes.py) ; le texte
riche est le sous-ensemble assaini (gras, italique, souligné, barré, code,
lien, retour à la ligne). Les images viennent de `note_images` (fichiers sous
UPLOAD_DIR). Le PDF sert aussi à l'impression sur une imprimante du réseau
(POST /api/print/pdf, entity_type « note »).
"""
from __future__ import annotations

import html as html_mod
import io
import os
import re
from html.parser import HTMLParser

from config import UPLOAD_DIR

# ── Texte riche → segments ────────────────────────────────────────────

class _Segments(HTMLParser):
    """'a <b>b</b><br>c' → [('a ', {}), ('b', {'b'}), ('\n', {}), ('c', {})] (+ lien)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.styles: list[str] = []
        self.lien: str | None = None
        self.out: list[tuple[str, frozenset, str | None]] = []

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.out.append(("\n", frozenset(), None))
        elif tag in ("b", "i", "u", "s", "code"):
            self.styles.append(tag)
        elif tag == "a":
            self.lien = dict(attrs).get("href")

    def handle_endtag(self, tag):
        if tag in self.styles:
            self.styles.reverse()
            self.styles.remove(tag)
            self.styles.reverse()
        elif tag == "a":
            self.lien = None

    def handle_data(self, data):
        if data:
            self.out.append((data, frozenset(self.styles), self.lien))


def segments(bloc_ou_html) -> list[tuple[str, frozenset, str | None]]:
    if isinstance(bloc_ou_html, dict):
        b = bloc_ou_html
        h = b.get("html") or html_mod.escape(b.get("texte") or "").replace("\n", "<br>")
    else:
        h = bloc_ou_html or ""
    p = _Segments()
    p.feed(h)
    p.close()
    return p.out


def chemin_image(conn, image_id) -> tuple[str, str] | None:
    row = conn.execute("SELECT chemin, mime FROM note_images WHERE id=?", (int(image_id or 0),)).fetchone()
    if not row:
        return None
    p = os.path.join(UPLOAD_DIR, row["chemin"])
    return (p, row["mime"]) if os.path.isfile(p) else None


def blocs_visibles(blocs: list[dict]) -> list[dict]:
    """Tous les blocs, dans l'ordre : un export montre aussi le contenu replié."""
    return [b for b in blocs if isinstance(b, dict)]


# ── Page imprimable (HTML) ────────────────────────────────────────────

def html_note(titre: str, blocs: list[dict], auteur: str = "", date: str = "") -> str:
    """Corps HTML d'une note pour l'impression navigateur. Les HTML de blocs sont
    déjà assainis par le serveur ; les textes bruts sont échappés ici."""
    esc = html_mod.escape
    out = []
    num = 0
    for b in blocs_visibles(blocs):
        t = b.get("type")
        r = int(b.get("retrait") or 0)
        style = f' style="margin-left:{r * 1.4}em"' if r else ""
        contenu = b.get("html") or esc(b.get("texte") or "").replace("\n", "<br>")
        num = num + 1 if t == "num" else 0
        if t in ("h1", "h2", "h3"):
            out.append(f"<{t}{style}>{contenu}</{t}>")
        elif t == "todo":
            out.append(f'<p class="todo{" coche" if b.get("coche") else ""}"{style}><span class="case">{"☑" if b.get("coche") else "☐"}</span> {contenu}</p>')
        elif t == "puce":
            out.append(f'<p class="liste"{style}>•&nbsp; {contenu}</p>')
        elif t == "num":
            out.append(f'<p class="liste"{style}>{num}.&nbsp; {contenu}</p>')
        elif t == "citation":
            out.append(f"<blockquote{style}>{contenu}</blockquote>")
        elif t == "encadre":
            out.append(f'<div class="encadre"{style}>{contenu}</div>')
        elif t == "code":
            out.append(f"<pre{style}>{esc(b.get('texte') or '')}</pre>")
        elif t == "sep":
            out.append("<hr>")
        elif t == "bascule":
            out.append(f'<p class="bascule"{style}>▾ {contenu}</p>')
        elif t == "page":
            out.append(f'<p class="page"{style}>▤ {esc(b.get("texte") or "Sous-page")}</p>')
        elif t == "image":
            largeur = int(b.get("largeur") or 100)
            leg = esc(b.get("legende") or "")
            out.append(f'<figure{style}><img src="/api/postits/images/{int(b.get("ref") or 0)}" style="width:{largeur}%" alt="{leg}">'
                       + (f"<figcaption>{leg}</figcaption>" if leg else "") + "</figure>")
        elif t == "tableau":
            lignes = b.get("lignes") or []
            corps = []
            for i, l in enumerate(lignes):
                tag = "th" if i == 0 and b.get("entete") else "td"
                corps.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in l) + "</tr>")
            out.append(f'<table{style}>{"".join(corps)}</table>')
        else:
            out.append(f"<p{style}>{contenu}</p>")
    entete = f'<div class="meta">{esc(auteur)}{" · " if auteur and date else ""}{esc(date)}</div>' if (auteur or date) else ""
    return f"<h1 class=\"titre\">{esc(titre or 'Sans titre')}</h1>{entete}" + "\n".join(out)


# ── PDF (reportlab) ───────────────────────────────────────────────────

_POLICE = None


def _police():
    """DejaVu Sans si présente (flèches, cases à cocher), sinon Vera de reportlab."""
    global _POLICE
    if _POLICE:
        return _POLICE
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import reportlab

    candidats = [
        ("/usr/share/fonts/truetype/dejavu", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf", "DejaVuSans-BoldOblique.ttf"),
        (os.path.join(os.path.dirname(reportlab.__file__), "fonts"), "Vera.ttf", "VeraBd.ttf", "VeraIt.ttf", "VeraBI.ttf"),
    ]
    for dossier, n, g, i, gi in candidats:
        chemins = [os.path.join(dossier, f) for f in (n, g, i, gi)]
        if all(os.path.isfile(c) for c in chemins):
            noms = ("NoteTexte", "NoteTexte-Gras", "NoteTexte-Ital", "NoteTexte-GrasItal")
            for nom, c in zip(noms, chemins):
                pdfmetrics.registerFont(TTFont(nom, c))
            from reportlab.lib.fonts import addMapping
            addMapping("NoteTexte", 0, 0, "NoteTexte")
            addMapping("NoteTexte", 1, 0, "NoteTexte-Gras")
            addMapping("NoteTexte", 0, 1, "NoteTexte-Ital")
            addMapping("NoteTexte", 1, 1, "NoteTexte-GrasItal")
            _POLICE = ("NoteTexte", TTFont("_test", chemins[0]))
            return _POLICE
    _POLICE = ("Helvetica", None)
    return _POLICE


_REPLI = {"→": "->", "←": "<-", "↔": "<->", "⇒": "=>", "☐": "[ ]", "☑": "[x]", "▾": "v", "▤": "", "≠": "!=",
          "≥": ">=", "≤": "<=", "•": "-", "◦": "-"}


def _glyphes(texte: str) -> str:
    """Remplace les signes que la police ne sait pas dessiner."""
    _, face = _police()
    if face is None:
        return "".join(_REPLI.get(c, c) for c in texte)
    cmap = face.face.charToGlyph
    return "".join(c if (ord(c) in cmap or c in "\n\t ") else _REPLI.get(c, "?") for c in texte)


def _para_xml(segs) -> str:
    """Segments → balisage Paragraph de reportlab."""
    morceaux = []
    for txt, st, lien in segs:
        t = html_mod.escape(_glyphes(txt)).replace("\n", "<br/>")
        if "code" in st:
            t = f'<font face="Courier">{t}</font>'
        if "b" in st:
            t = f"<b>{t}</b>"
        if "i" in st:
            t = f"<i>{t}</i>"
        if "u" in st:
            t = f"<u>{t}</u>"
        if "s" in st:
            t = f"<strike>{t}</strike>"
        if lien and re.match(r"^(https?://|mailto:)", lien):
            t = f'<a href="{html_mod.escape(lien)}" color="#0e7490">{t}</a>'  # hex-ok : lien dans le PDF
        morceaux.append(t)
    return "".join(morceaux)


def pdf_note(conn, titre: str, blocs: list[dict], auteur: str = "", date: str = "") -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (HRFlowable, Image, Paragraph, Preformatted, SimpleDocTemplate,
                                    Spacer, Table, TableStyle)

    police, _ = _police()
    encre = colors.HexColor("#1f2937")  # hex-ok : encre du PDF
    discret = colors.HexColor("#6b7280")  # hex-ok : texte secondaire du PDF
    filet = colors.HexColor("#d1d5db")  # hex-ok : filets du PDF
    fond = colors.HexColor("#f3f4f6")  # hex-ok : fonds du PDF

    def st(nom, taille, gras=False, avant=2, apres=3, couleur=encre, retrait=0):
        return ParagraphStyle(nom, fontName=police, fontSize=taille, leading=taille * 1.35,
                              spaceBefore=avant, spaceAfter=apres, textColor=couleur,
                              leftIndent=retrait, alignment=TA_LEFT)

    flux = [Paragraph(f"<b>{html_mod.escape(_glyphes(titre or 'Sans titre'))}</b>", st("t", 20, avant=0, apres=4))]
    if auteur or date:
        flux.append(Paragraph(html_mod.escape(" · ".join(x for x in (auteur, date) if x)), st("m", 9, couleur=discret, apres=10)))
    num = 0
    largeur_utile = A4[0] - 36 * mm
    for b in blocs_visibles(blocs):
        t = b.get("type")
        retrait = int(b.get("retrait") or 0) * 7 * mm
        num = num + 1 if t == "num" else 0
        segs = segments(b)
        if t in ("h1", "h2", "h3"):
            taille = {"h1": 16, "h2": 13.5, "h3": 11.5}[t]
            flux.append(Paragraph(f"<b>{_para_xml(segs)}</b>", st(t, taille, avant=8, apres=3, retrait=retrait)))
        elif t in ("todo", "puce", "num", "bascule"):
            prefixe = {"todo": ("☑ " if b.get("coche") else "☐ "), "puce": "• ", "num": f"{num}. ", "bascule": "▾ "}[t]
            corps = _para_xml(segs)
            if t == "todo" and b.get("coche"):
                corps = f'<font color="#9ca3af"><strike>{corps}</strike></font>'  # hex-ok : case cochée
            flux.append(Paragraph(html_mod.escape(_glyphes(prefixe)) + corps, st("l", 10.5, retrait=retrait + 3 * mm)))
        elif t == "citation":
            flux.append(Paragraph(f"<i>{_para_xml(segs)}</i>", st("c", 10.5, couleur=discret, retrait=retrait + 6 * mm)))
        elif t == "encadre":
            tb = Table([[Paragraph(_para_xml(segs), st("e", 10.5))]], colWidths=[largeur_utile - retrait])
            tb.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), fond), ("BOX", (0, 0), (-1, -1), 0.6, filet),
                                    ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                                    ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
            flux += [Spacer(1, 3), tb, Spacer(1, 3)]
        elif t == "code":
            flux.append(Preformatted(_glyphes(b.get("texte") or ""), ParagraphStyle("pre", fontName="Courier", fontSize=9,
                                                                                    leading=11.5, leftIndent=retrait + 4 * mm,
                                                                                    backColor=fond, spaceBefore=3, spaceAfter=3)))
        elif t == "sep":
            flux.append(HRFlowable(width="100%", thickness=0.6, color=filet, spaceBefore=6, spaceAfter=6))
        elif t == "page":
            flux.append(Paragraph(html_mod.escape(_glyphes("Sous-page : " + (b.get("texte") or ""))), st("pg", 10.5, couleur=discret, retrait=retrait)))
        elif t == "image":
            fichier = chemin_image(conn, b.get("ref"))
            if fichier:
                try:
                    from reportlab.lib.utils import ImageReader
                    lir = ImageReader(fichier[0])
                    iw, ih = lir.getSize()
                    w = (largeur_utile - retrait) * max(20, min(100, int(b.get("largeur") or 100))) / 100
                    h = w * ih / iw if iw else w
                    if h > 200 * mm:
                        w, h = w * 200 * mm / h, 200 * mm
                    im = Image(fichier[0], width=w, height=h)
                    im.hAlign = "LEFT"
                    flux += [Spacer(1, 4), im]
                    if b.get("legende"):
                        flux.append(Paragraph(html_mod.escape(_glyphes(b["legende"])), st("lg", 8.5, couleur=discret)))
                except Exception:
                    flux.append(Paragraph("[image illisible]", st("ie", 9, couleur=discret)))
        elif t == "tableau":
            lignes = b.get("lignes") or []
            if lignes:
                nb = max(len(l) for l in lignes)
                donnees = [[Paragraph(_para_xml(segments(c)) or "", st("cel", 9.5, avant=0, apres=0)) for c in (l + [""] * nb)[:nb]]
                           for l in lignes]
                tb = Table(donnees, colWidths=[(largeur_utile - retrait) / nb] * nb, repeatRows=1 if b.get("entete") else 0)
                style = [("GRID", (0, 0), (-1, -1), 0.5, filet), ("VALIGN", (0, 0), (-1, -1), "TOP")]
                if b.get("entete"):
                    style.append(("BACKGROUND", (0, 0), (-1, 0), fond))
                tb.setStyle(TableStyle(style))
                flux += [Spacer(1, 4), tb, Spacer(1, 4)]
        else:
            flux.append(Paragraph(_para_xml(segs) or "&nbsp;", st("p", 10.5, retrait=retrait)))

    tampon = io.BytesIO()

    def pied(canvas, doc):
        canvas.saveState()
        canvas.setFont(police, 8)
        canvas.setFillColor(discret)
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"{_glyphes(titre or '')} — page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(tampon, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=16 * mm, title=titre or "Note", author=auteur or "")
    doc.build(flux, onFirstPage=pied, onLaterPages=pied)
    return tampon.getvalue()


# ── Word (python-docx) ────────────────────────────────────────────────

def docx_note(conn, titre: str, blocs: list[dict], auteur: str = "", date: str = "") -> bytes:
    from docx import Document
    from docx.enum.text import WD_COLOR_INDEX
    from docx.shared import Cm, Pt, RGBColor

    doc = Document()
    doc.core_properties.title = titre or "Note"
    if auteur:
        doc.core_properties.author = auteur
    doc.add_heading(titre or "Sans titre", level=0)
    if auteur or date:
        p = doc.add_paragraph(" · ".join(x for x in (auteur, date) if x))
        p.runs[0].font.size = Pt(9)
        p.runs[0].font.color.rgb = RGBColor(0x6B, 0x72, 0x80)

    def remplir(par, segs):
        for txt, st, lien in segs:
            morceaux = txt.split("\n")
            for k, m in enumerate(morceaux):
                if k:
                    par.add_run().add_break()
                if not m:
                    continue
                run = par.add_run(m)
                run.bold = "b" in st or None
                run.italic = "i" in st or None
                run.underline = "u" in st or bool(lien) or None
                run.font.strike = "s" in st or None
                if "code" in st:
                    run.font.name = "Consolas"
                    run.font.highlight_color = WD_COLOR_INDEX.GRAY_25
                if lien:
                    run.font.color.rgb = RGBColor(0x0E, 0x74, 0x90)

    num = 0
    for b in blocs_visibles(blocs):
        t = b.get("type")
        retrait = Cm(0.7 * int(b.get("retrait") or 0))
        num = num + 1 if t == "num" else 0
        segs = segments(b)
        if t in ("h1", "h2", "h3"):
            par = doc.add_heading("", level={"h1": 1, "h2": 2, "h3": 3}[t])
            remplir(par, segs)
        elif t == "puce":
            par = doc.add_paragraph(style="List Bullet")
            remplir(par, segs)
        elif t == "num":
            par = doc.add_paragraph()
            par.add_run(f"{num}. ")
            remplir(par, segs)
        elif t == "todo":
            par = doc.add_paragraph()
            par.add_run("☑ " if b.get("coche") else "☐ ")
            remplir(par, segs)
        elif t == "bascule":
            par = doc.add_paragraph()
            par.add_run("▾ ").bold = True
            remplir(par, [(x, st | {"b"}, l) for x, st, l in segs])
        elif t == "citation":
            par = doc.add_paragraph(style="Quote") if "Quote" in [s.name for s in doc.styles] else doc.add_paragraph()
            remplir(par, segs)
        elif t == "encadre":
            tb = doc.add_table(rows=1, cols=1)
            tb.style = "Table Grid"
            remplir(tb.cell(0, 0).paragraphs[0], segs)
            par = None
        elif t == "code":
            par = doc.add_paragraph()
            run = par.add_run(b.get("texte") or "")
            run.font.name = "Consolas"
            run.font.size = Pt(9)
        elif t == "sep":
            par = doc.add_paragraph("―" * 30)
        elif t == "page":
            par = doc.add_paragraph("Sous-page : " + (b.get("texte") or ""))
        elif t == "image":
            par = None
            fichier = chemin_image(conn, b.get("ref"))
            if fichier and fichier[1] != "image/webp":
                try:
                    doc.add_picture(fichier[0], width=Cm(16 * max(20, min(100, int(b.get("largeur") or 100))) / 100))
                    if b.get("legende"):
                        doc.add_paragraph(b["legende"]).runs[0].italic = True
                except Exception:
                    doc.add_paragraph("[image illisible]")
            else:
                doc.add_paragraph("[image non exportable en Word (WebP)]" if fichier else "[image absente]")
        elif t == "tableau":
            par = None
            lignes = b.get("lignes") or []
            if lignes:
                nb = max(len(l) for l in lignes)
                tb = doc.add_table(rows=len(lignes), cols=nb)
                tb.style = "Table Grid"
                for r, l in enumerate(lignes):
                    for c, cel in enumerate((l + [""] * nb)[:nb]):
                        sg = segments(cel)
                        if r == 0 and b.get("entete"):
                            sg = [(x, st | {"b"}, li) for x, st, li in sg]
                        remplir(tb.cell(r, c).paragraphs[0], sg)
        else:
            par = doc.add_paragraph()
            remplir(par, segs)
        if par is not None and retrait:
            par.paragraph_format.left_indent = retrait
    tampon = io.BytesIO()
    doc.save(tampon)
    return tampon.getvalue()


def nom_fichier(titre: str, ext: str) -> str:
    base = re.sub(r"[^\w\- ]+", "", (titre or "note"), flags=re.UNICODE).strip().replace(" ", "_")[:60] or "note"
    return f"{base}.{ext}"
