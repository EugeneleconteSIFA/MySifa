"""Nouvel ERP — PDF d'une pièce (pièce jointe des e-mails, téléchargement).

Même contenu que l'aperçu HTML : les deux rendus lisent `impression.donnees()`,
ils ne peuvent pas diverger. Rendu reportlab (déjà dans requirements.txt), sans
dépendance système : rien à installer sur le VPS.
"""
from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

GRIS = colors.Color(0.41, 0.41, 0.41)
GRIS_CLAIR = colors.Color(0.86, 0.86, 0.86)


def _st(taille=8.5, align=TA_LEFT, gras=False, couleur=colors.black, interligne=None):
    return ParagraphStyle("s", fontName="Helvetica-Bold" if gras else "Helvetica", fontSize=taille,
                          leading=interligne or taille * 1.25, alignment=align, textColor=couleur)


def _p(txt, **k):
    return Paragraph(txt or "", _st(**k))


def generer(D: dict) -> bytes:
    """`D` : le dictionnaire de app/web/erp2/impression.donnees()."""
    tampon = io.BytesIO()
    larg = 186 * mm
    doc = SimpleDocTemplate(tampon, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                            bottomMargin=14 * mm, title=f"{D['titre']} {D['numero']}")
    cadre = [("BOX", (0, 0), (-1, -1), 0.6, GRIS)]
    grille = [("GRID", (0, 0), (-1, -1), 0.6, GRIS)]
    flux = []

    # En-tête : société à gauche, titre et adresses à droite
    S = D["societe"]
    gauche = [_p(S["nom"], taille=14, gras=True, interligne=17)] + [_p(x, taille=8) for x in S["lignes"]] \
        + [Spacer(1, 2 * mm)] + [_p(x, taille=8) for x in S["ident"]]
    droite = [_p(D["titre_complet"], taille=15, gras=True, interligne=19), Spacer(1, 2 * mm)]
    for a in D["adresses"]:
        contenu = [_p(f"<u>{a['titre']}</u>", taille=8.5, align=TA_CENTER)] + [_p(x, taille=9.5) for x in a["lignes"]]
        t = Table([[contenu]], colWidths=[100 * mm], rowHeights=[24 * mm])
        style = cadre + [("VALIGN", (0, 0), (-1, -1), "TOP")]
        if a["barree"]:
            style += [("LINEBELOW", (0, 0), (-1, -1), 0.6, GRIS)]
        t.setStyle(TableStyle(style))
        if a["barree"]:
            t = _barree(t)
        droite += [t, Spacer(1, 2 * mm)]
    haut = Table([[gauche, droite]], colWidths=[84 * mm, 102 * mm])
    haut.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    flux += [haut, Spacer(1, 3 * mm)]

    # Cartouche et règlement
    C = D["cartouche"]
    cart_rows = [[_p(e, align=TA_CENTER) for e in C["entetes"]], [_p(v, taille=10.5, align=TA_CENTER) for v in C["valeurs"]]]
    cart_style = grille[:]
    if C["suivi"]:
        cart_rows.append([_p("<br/>".join(C["suivi"]), taille=8.5), "", ""])
        cart_style.append(("SPAN", (0, 2), (2, 2)))
    cart = Table(cart_rows, colWidths=[30 * mm, 26 * mm, 22 * mm])
    cart.setStyle(TableStyle(cart_style))
    colg = [cart] + ([Spacer(1, 2 * mm)] + [_p(x, taille=9) for x in D["origine"]] if D["origine"] else [])
    cold = []
    R = D["reglement"]
    if R:
        ent = [_p("Mode de règlement", align=TA_CENTER)] + ([_p("Échéance", align=TA_CENTER)] if R["echeance"] else [])
        val = [_p(f"{R['mode']}<br/>{R['conditions']}", taille=9)] + ([_p(R["echeance"], taille=10.5, align=TA_CENTER)] if R["echeance"] else [])
        t = Table([ent, val], colWidths=[64 * mm, 36 * mm] if R["echeance"] else [100 * mm])
        t.setStyle(TableStyle(grille))
        cold.append(t)
    if D["contact"] is not None:
        t = Table([[[_p("<u>Contact</u>", align=TA_CENTER), _p(D["contact"], taille=9.5)]]], colWidths=[100 * mm], rowHeights=[16 * mm])
        t.setStyle(TableStyle(cadre + [("VALIGN", (0, 0), (-1, -1), "TOP")]))
        cold.append(t)
    milieu = Table([[colg, cold]], colWidths=[84 * mm, 102 * mm])
    milieu.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    flux += [milieu, Spacer(1, 3 * mm)]

    # Lignes
    cols = D["colonnes"]
    alignes = {"d": TA_RIGHT, "g": TA_LEFT, "c": TA_CENTER}
    reste = larg - 96 * mm
    largeurs = [96 * mm] + [reste / len(cols)] * len(cols)
    rows = [[_p("Désignation", align=TA_CENTER)] + [_p(c[0], align=TA_CENTER, taille=8) for c in cols]]
    for l in D["lignes"]:
        if l["texte"]:
            rows.append([_p(l["des"][0], taille=8.5)] + [""] * len(cols))
            continue
        tete = Table([[_p(l["code"], taille=8), _p("<br/>".join(l["droite"]), taille=8, gras=True, align=TA_RIGHT)]],
                     colWidths=[30 * mm, 64 * mm])
        tete.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                  ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                                  ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        des = [tete] + [_p(x, taille=8) for x in l["des"]]
        rows.append([des] + [_p(v, taille=9, align=alignes[c[1]]) for c, v in zip(cols, l["cells"])])
    lig = Table(rows, colWidths=largeurs, repeatRows=1)
    lig.setStyle(TableStyle(cadre + [("GRID", (0, 0), (-1, 0), 0.6, GRIS),
                                     ("LINEAFTER", (0, 0), (-2, -1), 0.6, GRIS),
                                     ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                     ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
                                     ("TOPPADDING", (0, 1), (-1, -1), 5)]))
    flux.append(lig)

    T = D["totaux"]
    if T and T["genre"] == "montants":
        if T["remises"]:
            flux.append(_p(T["remises"], taille=8.5, align=TA_RIGHT))
        rows = [[_p(e, align=TA_CENTER) for e in T["entetes"]]] + [[_p(v, taille=10, align=TA_RIGHT) for v in r] for r in T["rangees"]]
        t = Table(rows, colWidths=[larg / 5] * 5)
        t.setStyle(TableStyle(grille))
        flux += [Spacer(1, 1), t]
        if T["tva_debits"]:
            flux.append(_p("TVA sur les débits", taille=7.5))
        bas = []
        if T["acompte"]:
            bas.append([_p("Acompte :", taille=10), _p(T["acompte"], taille=10, align=TA_RIGHT)])
        bas.append([_p(T["net_libelle"] + " :", taille=12), _p(f"<b>{T['net']}</b>", taille=12, align=TA_RIGHT)])
        t = Table(bas, colWidths=[38 * mm, 40 * mm], hAlign="RIGHT")
        t.setStyle(TableStyle(grille))
        flux += [Spacer(1, 2 * mm), t]
    elif T:
        t = Table([[_p(e, align=TA_CENTER, taille=8) for e in T["entetes"]],
                   [_p(v, align=TA_CENTER, taille=10) for v in T["valeurs"]]], colWidths=[larg / len(T["entetes"])] * len(T["entetes"]))
        t.setStyle(TableStyle(grille))
        flux.append(t)

    flux.append(Spacer(1, 4 * mm))
    if D["affacturage"]:
        flux.append(_p(f"<b>{D['affacturage']}</b>", taille=7.5, couleur=colors.firebrick))
    for m in D["mentions"]:
        flux.append(_p(m, taille=7, couleur=GRIS))
    flux.append(Spacer(1, 4 * mm))
    for x in D["pied"]:
        flux.append(_p(x, taille=7, align=TA_CENTER, couleur=GRIS))

    def filigrane(canvas, _doc):
        if D["brouillon"]:
            canvas.saveState()
            canvas.setFont("Helvetica-Bold", 70)
            canvas.setFillColor(GRIS_CLAIR)
            canvas.translate(A4[0] / 2, A4[1] / 2)
            canvas.rotate(24)
            canvas.drawCentredString(0, 0, "BROUILLON")
            canvas.restoreState()

    doc.build(flux, onFirstPage=filigrane, onLaterPages=filigrane)
    return tampon.getvalue()


class _barree(Table):
    """Cadre d'adresse barré en croix (adresse de facturation d'un BL)."""

    def __init__(self, t):
        super().__init__(t._cellvalues, colWidths=t._colWidths, rowHeights=t._rowHeights)
        self.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, GRIS), ("VALIGN", (0, 0), (-1, -1), "TOP")]))

    def draw(self):
        super().draw()
        c = self.canv
        c.saveState()
        c.setStrokeColor(GRIS)
        c.setLineWidth(0.6)
        c.line(0, 0, self._width, self._height)
        c.line(0, self._height, self._width, 0)
        c.restoreState()
