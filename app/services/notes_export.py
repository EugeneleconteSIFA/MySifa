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

# Teintes d'impression des styles de texte (papier blanc). hex-ok : couleurs
# d'export, hors thème de l'application — miroir clair de mysifa_notes_editeur.css.
COULEURS = {"rouge": "#dc2626", "orange": "#c2410c", "vert": "#15803d", "bleu": "#1d4ed8",  # hex-ok
            "violet": "#7e22ce", "rose": "#be185d", "gris": "#6b7280"}  # hex-ok
SURLIGNAGES = {"jaune": "#fde68a", "vert": "#bbf7d0", "bleu": "#bfdbfe", "rose": "#fbcfe8",  # hex-ok
               "orange": "#fed7aa", "gris": "#e5e7eb"}  # hex-ok
TAILLES = {"petit": 0.82, "grand": 1.3, "tres-grand": 1.7}
POLICES_CSS = {"serif": "Georgia,'Times New Roman',serif", "mono": "ui-monospace,Menlo,Consolas,monospace",
               "manuscrite": "'Segoe Print','Bradley Hand','Comic Sans MS',cursive"}

# Polices de la mise en forme libre (clé de notes.POLICES) → nom pour Word,
# police standard du PDF (None = police du document), italique de repli pour
# les écritures manuscrites que le PDF n'embarque pas.
POLICES_EXPORT = {
    "serif": ("Georgia", "Times-Roman", False), "mono": ("Consolas", "Courier", False),
    "manuscrite": ("Segoe Print", None, True),
    "arial": ("Arial", None, False), "verdana": ("Verdana", None, False), "tahoma": ("Tahoma", None, False),
    "trebuchet": ("Trebuchet MS", None, False), "georgia": ("Georgia", "Times-Roman", False),
    "times": ("Times New Roman", "Times-Roman", False), "garamond": ("Garamond", "Times-Roman", False),
    "palatino": ("Palatino Linotype", "Times-Roman", False), "courier": ("Courier New", "Courier", False),
    "consolas": ("Consolas", "Courier", False), "comic": ("Comic Sans MS", None, False),
    "brush": ("Brush Script MT", None, True), "impact": ("Impact", None, False),
}


def _jetons_style(style: str) -> list[str]:
    """Style en ligne d'un span (déjà validé par notes.style_admis) → jetons
    « c:#hex », « f:#hex », « t:12pt », « p:<clé de police> »."""
    from app.services.notes import POLICES, style_admis
    piles = {pile: cle for cle, pile in POLICES}
    out = []
    for decl in style_admis(style).split(";"):
        if ":" not in decl:
            continue
        prop, val = decl.split(":", 1)
        if prop == "color":
            out.append("c:" + val)
        elif prop == "background-color":
            out.append("f:" + val)
        elif prop == "font-size":
            out.append("t:" + val)
        elif prop == "font-family" and val in piles:
            out.append("p:" + piles[val])
    return out


# ── Texte riche → segments ────────────────────────────────────────────

class _Segments(HTMLParser):
    """'a <b>b</b><br>c' → [('a ', {}), ('b', {'b'}), ('\n', {}), ('c', {})] (+ lien)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.styles: list[str] = []
        self.lien: str | None = None
        self.spans: list[list[str]] = []
        self.out: list[tuple[str, frozenset, str | None]] = []

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.out.append(("\n", frozenset(), None))
        elif tag in ("b", "i", "u", "s", "code"):
            self.styles.append(tag)
        elif tag == "a":
            self.lien = dict(attrs).get("href")
        elif tag == "span":
            a = dict(attrs)
            m = re.match(r"^nt-([cftp])-([a-z-]+)$", a.get("class") or "")
            jetons = ([f"{m.group(1)}:{m.group(2)}"] if m else []) + _jetons_style(a.get("style") or "")
            self.spans.append(jetons)
            self.styles.extend(jetons)

    def handle_endtag(self, tag):
        if tag == "span":
            for jeton in reversed(self.spans.pop() if self.spans else []):
                if jeton in self.styles:
                    self.styles.reverse()
                    self.styles.remove(jeton)
                    self.styles.reverse()
            return
        if tag in self.styles:
            self.styles.reverse()
            self.styles.remove(tag)
            self.styles.reverse()
        elif tag == "a":
            self.lien = None

    def handle_data(self, data):
        if data:
            # Un style imbriqué remplace celui de même famille (le plus intérieur gagne).
            familles: dict[str, str] = {}
            for st in self.styles:
                familles[st.split(":")[0] if ":" in st else st] = st
            self.out.append((data, frozenset(familles.values()), self.lien))


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


def style_de(st, taille_base: float = 11) -> dict:
    """Jetons de style d'un segment → valeurs prêtes à exporter :
    couleur et fond en #rrggbb, taille en points, police (clé de POLICES_EXPORT)."""
    out = {}
    for j in st:
        if ":" not in j:
            continue
        fam, val = j.split(":", 1)
        if fam == "c":
            if val in COULEURS:
                out["couleur"] = COULEURS[val]
            elif re.match(r"^#[0-9a-f]{6}$", val):
                out["couleur"] = val
        elif fam == "f":
            if val in SURLIGNAGES:
                out["fond"] = SURLIGNAGES[val]
            elif re.match(r"^#[0-9a-f]{6}$", val):
                out["fond"] = val
        elif fam == "t":
            if val in TAILLES:
                out["taille"] = round(taille_base * TAILLES[val], 1)
            else:
                m = re.match(r"^(\d{1,2})pt$", val)
                if m:
                    out["taille"] = float(m.group(1))
        elif fam == "p" and val in POLICES_EXPORT:
            out["police"] = val
    return out


def styles_cellule(b: dict, r: int, c: int) -> dict:
    try:
        jetons = str((b.get("styles") or [])[r][c] or "").split()
    except (IndexError, TypeError):
        jetons = []
    out = {}
    for j in jetons:
        fam, _, val = j.partition("-")
        if fam == "fond" and val in SURLIGNAGES:
            out["fond"] = val
        elif fam == "al":
            out["aligne"] = val
    return out


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

def _romain(n: int) -> str:
    out = ""
    for v, l in ((1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"),
                 (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")):
        while n >= v:
            out += l
            n -= v
    return out


def _lettres(n: int) -> str:
    out = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        out = chr(97 + r) + out
    return out


def marque_num(n: int, retrait: int) -> str:
    """Numéro d'une liste selon son niveau : 1. puis a. puis i. (miroir de l'éditeur)."""
    niveau = (retrait or 0) % 3
    return (str(n) if niveau == 0 else _lettres(n) if niveau == 1 else _romain(n)) + "."


def marques_num(blocs: list[dict]) -> list:
    """Numéro affiché de chaque bloc « num » (None pour les autres). Une liste
    continue sous ses sous-éléments plus en retrait, comme dans l'éditeur."""
    out = []
    for i, b in enumerate(blocs):
        if b.get("type") != "num":
            out.append(None)
            continue
        r = int(b.get("retrait") or 0)
        n = 1
        for j in range(i - 1, -1, -1):
            rj = int(blocs[j].get("retrait") or 0)
            if rj > r:
                continue
            if rj < r or blocs[j].get("type") != "num":
                break
            n += 1
        out.append(marque_num(n, r))
    return out


def html_note(titre: str, blocs: list[dict], auteur: str = "", date: str = "") -> str:
    """Corps HTML d'une note pour l'impression navigateur. Les HTML de blocs sont
    déjà assainis par le serveur ; les textes bruts sont échappés ici."""
    esc = html_mod.escape
    out = []
    vis = blocs_visibles(blocs)
    marques = marques_num(vis)
    for k, b in enumerate(vis):
        t = b.get("type")
        num = marques[k]
        r = int(b.get("retrait") or 0)
        regles = []
        if r:
            regles.append(f"margin-left:{r * 1.4}em")
        if b.get("aligne") in ("centre", "droite", "justifie"):
            regles.append("text-align:" + {"centre": "center", "droite": "right", "justifie": "justify"}[b["aligne"]])
        style = f' style="{";".join(regles)}"' if regles else ""
        contenu = b.get("html") or esc(b.get("texte") or "").replace("\n", "<br>")
        if t in ("h1", "h2", "h3"):
            out.append(f"<{t}{style}>{contenu}</{t}>")
        elif t == "todo":
            out.append(f'<p class="todo{" coche" if b.get("coche") else ""}"{style}><span class="case">{"☑" if b.get("coche") else "☐"}</span> {contenu}</p>')
        elif t == "puce":
            out.append(f'<p class="liste"{style}>•&nbsp; {contenu}</p>')
        elif t == "num":
            out.append(f'<p class="liste"{style}>{num}&nbsp; {contenu}</p>')
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
                cellules = []
                for j, cel in enumerate(l):
                    sc = styles_cellule(b, i, j)
                    css = []
                    if sc.get("fond"):
                        css.append("background:" + SURLIGNAGES[sc["fond"]])
                    if sc.get("aligne") in ("centre", "droite", "justifie"):
                        css.append("text-align:" + {"centre": "center", "droite": "right", "justifie": "justify"}[sc["aligne"]])
                    attr = f' style="{";".join(css)}"' if css else ""
                    cellules.append(f"<{tag}{attr}>{cel}</{tag}>")
                corps.append("<tr>" + "".join(cellules) + "</tr>")
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


def _para_xml(segs, taille_base: float = 10.5) -> str:
    """Segments → balisage Paragraph de reportlab."""
    morceaux = []
    for txt, st, lien in segs:
        t = html_mod.escape(_glyphes(txt)).replace("\n", "<br/>")
        if "code" in st:
            t = f'<font face="Courier">{t}</font>'
        sty = style_de(st, taille_base)
        attrs = []
        if sty.get("couleur"):
            attrs.append(f'color="{sty["couleur"]}"')
        if sty.get("fond"):
            attrs.append(f'backColor="{sty["fond"]}"')
        if sty.get("taille"):
            attrs.append(f'size="{sty["taille"]}"')
        _nom, face, penche = POLICES_EXPORT.get(sty.get("police"), (None, None, False))
        if face:
            attrs.append(f'face="{face}"')
        if attrs:
            t = f'<font {" ".join(attrs)}>{t}</font>'
        if penche:
            t = f"<i>{t}</i>"
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

    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
    alignements = {"centre": TA_CENTER, "droite": TA_RIGHT, "justifie": TA_JUSTIFY}

    def st(nom, taille, gras=False, avant=2, apres=3, couleur=encre, retrait=0, aligne=None):
        return ParagraphStyle(nom, fontName=police, fontSize=taille, leading=taille * 1.35,
                              spaceBefore=avant, spaceAfter=apres, textColor=couleur,
                              leftIndent=retrait, alignment=alignements.get(aligne, TA_LEFT))

    flux = [Paragraph(f"<b>{html_mod.escape(_glyphes(titre or 'Sans titre'))}</b>", st("t", 20, avant=0, apres=4))]
    if auteur or date:
        flux.append(Paragraph(html_mod.escape(" · ".join(x for x in (auteur, date) if x)), st("m", 9, couleur=discret, apres=10)))
    largeur_utile = A4[0] - 36 * mm
    vis = blocs_visibles(blocs)
    marques = marques_num(vis)
    for k, b in enumerate(vis):
        t = b.get("type")
        retrait = int(b.get("retrait") or 0) * 7 * mm
        num = marques[k]
        segs = segments(b)
        if t in ("h1", "h2", "h3"):
            taille = {"h1": 16, "h2": 13.5, "h3": 11.5}[t]
            flux.append(Paragraph(f"<b>{_para_xml(segs, taille)}</b>", st(t, taille, avant=8, apres=3, retrait=retrait, aligne=b.get("aligne"))))
        elif t in ("todo", "puce", "num", "bascule"):
            prefixe = {"todo": ("☑ " if b.get("coche") else "☐ "), "puce": "• ", "num": f"{num} ", "bascule": "▾ "}[t]
            corps = _para_xml(segs)
            if t == "todo" and b.get("coche"):
                corps = f'<font color="#9ca3af"><strike>{corps}</strike></font>'  # hex-ok : case cochée
            flux.append(Paragraph(html_mod.escape(_glyphes(prefixe)) + corps, st("l", 10.5, retrait=retrait + 3 * mm, aligne=b.get("aligne"))))
        elif t == "citation":
            flux.append(Paragraph(f"<i>{_para_xml(segs)}</i>", st("c", 10.5, couleur=discret, retrait=retrait + 6 * mm, aligne=b.get("aligne"))))
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
                donnees = [[Paragraph(_para_xml(segments(c), 9.5) or "",
                                      st("cel", 9.5, avant=0, apres=0, aligne=styles_cellule(b, r, k).get("aligne")))
                             for k, c in enumerate((l + [""] * nb)[:nb])]
                           for r, l in enumerate(lignes)]
                tb = Table(donnees, colWidths=[(largeur_utile - retrait) / nb] * nb, repeatRows=1 if b.get("entete") else 0)
                style = [("GRID", (0, 0), (-1, -1), 0.5, filet), ("VALIGN", (0, 0), (-1, -1), "TOP")]
                if b.get("entete"):
                    style.append(("BACKGROUND", (0, 0), (-1, 0), fond))
                for r in range(len(lignes)):
                    for k in range(nb):
                        f = styles_cellule(b, r, k).get("fond")
                        if f:
                            style.append(("BACKGROUND", (k, r), (k, r), colors.HexColor(SURLIGNAGES[f])))
                tb.setStyle(TableStyle(style))
                flux += [Spacer(1, 4), tb, Spacer(1, 4)]
        else:
            flux.append(Paragraph(_para_xml(segs) or "&nbsp;", st("p", 10.5, retrait=retrait, aligne=b.get("aligne"))))

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

    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    surligne = {"jaune": WD_COLOR_INDEX.YELLOW, "vert": WD_COLOR_INDEX.BRIGHT_GREEN, "bleu": WD_COLOR_INDEX.TURQUOISE,
                "rose": WD_COLOR_INDEX.PINK, "orange": WD_COLOR_INDEX.YELLOW, "gris": WD_COLOR_INDEX.GRAY_25}
    index_surligne = {v: surligne[k] for k, v in SURLIGNAGES.items()}

    def fond_run(run, hexa):
        """Surlignage : couleur exacte en trame (Word n'a que 16 surligneurs)."""
        if hexa in index_surligne:
            run.font.highlight_color = index_surligne[hexa]
            return
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hexa.lstrip("#"))
        run._r.get_or_add_rPr().append(shd)
    aligne_docx = {"centre": WD_ALIGN_PARAGRAPH.CENTER, "droite": WD_ALIGN_PARAGRAPH.RIGHT,
                   "justifie": WD_ALIGN_PARAGRAPH.JUSTIFY}

    def rgb(h):
        h = h.lstrip("#")
        return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    def remplir(par, segs):
        for txt, st, lien in segs:
            sty = style_de(st)
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
                if sty.get("couleur"):
                    run.font.color.rgb = rgb(sty["couleur"])
                if sty.get("fond"):
                    fond_run(run, sty["fond"])
                if sty.get("taille"):
                    run.font.size = Pt(sty["taille"])
                if sty.get("police"):
                    run.font.name = POLICES_EXPORT[sty["police"]][0]

    vis = blocs_visibles(blocs)
    marques = marques_num(vis)
    for k, b in enumerate(vis):
        t = b.get("type")
        retrait = Cm(0.7 * int(b.get("retrait") or 0))
        num = marques[k]
        segs = segments(b)
        if t in ("h1", "h2", "h3"):
            par = doc.add_heading("", level={"h1": 1, "h2": 2, "h3": 3}[t])
            remplir(par, segs)
        elif t == "puce":
            par = doc.add_paragraph(style="List Bullet")
            remplir(par, segs)
        elif t == "num":
            par = doc.add_paragraph()
            par.add_run(f"{num} ")
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
                        cellule = tb.cell(r, c)
                        remplir(cellule.paragraphs[0], sg)
                        sc = styles_cellule(b, r, c)
                        if sc.get("aligne") in aligne_docx:
                            cellule.paragraphs[0].alignment = aligne_docx[sc["aligne"]]
                        if sc.get("fond"):
                            ombre = OxmlElement("w:shd")
                            ombre.set(qn("w:val"), "clear")
                            ombre.set(qn("w:fill"), SURLIGNAGES[sc["fond"]].lstrip("#"))
                            cellule._tc.get_or_add_tcPr().append(ombre)
        else:
            par = doc.add_paragraph()
            remplir(par, segs)
        if par is not None and retrait:
            par.paragraph_format.left_indent = retrait
        if par is not None and b.get("aligne") in aligne_docx:
            par.alignment = aligne_docx[b["aligne"]]
    tampon = io.BytesIO()
    doc.save(tampon)
    return tampon.getvalue()


def nom_fichier(titre: str, ext: str) -> str:
    base = re.sub(r"[^\w\- ]+", "", (titre or "note"), flags=re.UNICODE).strip().replace(" ", "_")[:60] or "note"
    return f"{base}.{ext}"
