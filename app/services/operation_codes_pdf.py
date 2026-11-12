"""Affiche des codes opération à poser aux postes de conduite.

Une page A4, deux colonnes, codes groupés par section. Tout est lu dans la
table `operation_codes` : un code ajouté dans Paramètres apparaît au prochain
téléchargement, rien n'est figé dans ce fichier sinon la mise en page.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Dict, List, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from config import APP_NAME, CODE_DEBUT_DOS, CODE_FIN_DOS

# Sections de l'affiche, chacune dans la couleur que la saisie de prod
# donne à ses lignes (vert production, violet personnel, jaune calage) et,
# pour le reste, celle des états machine (arrêt rouge, nettoyage mauve).
# Teintes assombries : du jaune clair ne se lit pas imprimé sur du blanc.
# Une catégorie absente de cette table tombe dans « Autres ».
SECTIONS: List[Tuple[str, Tuple[str, ...], str]] = [
    ("Personnel et dossier", ("personnel",), "#7c3aed"),  # hex-ok
    ("Production", ("production",), "#059669"),  # hex-ok
    ("Calage et changements", ("calage",), "#b45309"),  # hex-ok
    ("Matière", ("appro",), "#0891b2"),  # hex-ok
    ("Pauses et divers", ("pause", "annulation"), "#64748b"),  # hex-ok
    ("Arrêts", ("arret",), "#dc2626"),  # hex-ok
    ("Nettoyage et maintenance", ("nettoyage", "technique"), "#9333ea"),  # hex-ok
    ("Autres", ("autre",), "#64748b"),  # hex-ok
]

# Thème clair de MySifa : une affiche imprimée ne se tire pas sur fond sombre.
TEXT = colors.HexColor("#0f172a")  # hex-ok
MUTED = colors.HexColor("#64748b")  # hex-ok
BORDER = colors.HexColor("#e2e8f0")  # hex-ok
BG = colors.HexColor("#f1f5f9")  # hex-ok


def _teinte(couleur, part: float):
    """La couleur mêlée de blanc : fond de pastille, filet."""
    return colors.Color(1 - (1 - couleur.red) * part,
                        1 - (1 - couleur.green) * part,
                        1 - (1 - couleur.blue) * part)


MARGE_X = 12 * mm
MARGE_HAUT = 12 * mm
MARGE_BAS = 11 * mm
GOUTTIERE = 7 * mm
H_TITRE_SECTION = 7.5 * mm
ESPACE_SECTION = 3.5 * mm


def _sections(codes: List[Dict]) -> List[Tuple[str, List[Dict], object]]:
    connues = {c for _, cats, _ in SECTIONS for c in cats}
    out = []
    for titre, cats, coul in SECTIONS:
        items = [
            c for c in codes
            if (c.get("category") in cats)
            or (titre == "Autres" and c.get("category") not in connues)
        ]
        if items:
            items.sort(key=lambda c: (len(str(c["code"])), str(c["code"])))
            out.append((titre, items, colors.HexColor(coul)))
    return out


def _repartir(sections, h_ligne) -> Tuple[list, list]:
    """Coupe la liste de sections en deux colonnes de hauteurs voisines,
    sans jamais couper une section."""
    hauteurs = [H_TITRE_SECTION + len(it) * h_ligne + ESPACE_SECTION for _, it, _ in sections]
    total = sum(hauteurs)
    meilleur, ecart = len(sections), total
    cumul = 0.0
    for i, h in enumerate(hauteurs):
        cumul += h
        e = abs(total - 2 * cumul)
        if e < ecart:
            meilleur, ecart = i + 1, e
    return sections[:meilleur], sections[meilleur:]


def _hauteur(col, h_ligne) -> float:
    return sum(H_TITRE_SECTION + len(it) * h_ligne + ESPACE_SECTION for _, it, _ in col)


def _ajuster(texte: str, police: str, taille: float, largeur: float) -> str:
    from reportlab.pdfbase.pdfmetrics import stringWidth
    if stringWidth(texte, police, taille) <= largeur:
        return texte
    while texte and stringWidth(texte + "…", police, taille) > largeur:
        texte = texte[:-1]
    return texte.rstrip() + "…"


def generer_pdf_codes_operation(codes: List[Dict]) -> bytes:
    larg, haut = A4
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle("Codes opération")
    c.setAuthor(APP_NAME)

    # ── En-tête ──────────────────────────────────────────────────────
    y = haut - MARGE_HAUT
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(MARGE_X, y - 7, (APP_NAME + " · Production").upper())
    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(MARGE_X, y - 27, "Codes opération")

    y_regle = y - 35
    c.setStrokeColor(TEXT)
    c.setLineWidth(1.5)
    c.line(MARGE_X, y_regle, larg - MARGE_X, y_regle)

    # ── Colonnes ─────────────────────────────────────────────────────
    sections = _sections(codes)
    h_dispo = y_regle - 5 * mm - (MARGE_BAS + 9 * mm)
    # La ligne la plus haute qui tient sur la page, plafonnée pour rester lisible.
    h_ligne = 7.6 * mm
    while h_ligne > 4.6 * mm:
        g, d = _repartir(sections, h_ligne)
        if max(_hauteur(g, h_ligne), _hauteur(d, h_ligne)) <= h_dispo:
            break
        h_ligne -= 0.2 * mm
    gauche, droite = _repartir(sections, h_ligne)
    taille = min(11.5, h_ligne / mm * 1.55)
    larg_col = (larg - 2 * MARGE_X - GOUTTIERE) / 2

    def colonne(x0, cols):
        yy = y_regle - 5 * mm
        for titre, items, coul in cols:
            fond = _teinte(coul, 0.13)
            filet = _teinte(coul, 0.35)
            c.setFillColor(coul)
            c.setFont("Helvetica-Bold", 8.5)
            t = titre.upper()
            c.drawString(x0, yy - 9, t)
            tw = c.stringWidth(t, "Helvetica-Bold", 8.5)
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 7.5)
            c.drawString(x0 + tw + 5, yy - 9, str(len(items)))
            c.setStrokeColor(filet)
            c.setLineWidth(1.2)
            c.line(x0, yy - 13, x0 + larg_col, yy - 13)
            yy -= H_TITRE_SECTION
            for i, it in enumerate(items):
                code = str(it["code"])
                cle = code in (CODE_DEBUT_DOS, CODE_FIN_DOS)
                milieu = yy - h_ligne / 2
                # Pastille du code, dans la couleur de sa section ; pleine pour
                # le début et la fin de dossier.
                pw, ph = 10.5 * mm, min(h_ligne - 1.6 * mm, 6 * mm)
                c.setLineWidth(0.8)
                c.setFillColor(coul if cle else fond)
                c.setStrokeColor(coul if cle else filet)
                c.roundRect(x0, milieu - ph / 2, pw, ph, 1.8 * mm, stroke=1, fill=1)
                c.setFillColor(colors.white if cle else coul)
                c.setFont("Courier-Bold", taille + 1)
                c.drawCentredString(x0 + pw / 2, milieu - (taille + 1) * 0.33, code)
                # Libellé
                police = "Helvetica-Bold" if cle else "Helvetica"
                c.setFillColor(TEXT)
                c.setFont(police, taille)
                lib = _ajuster(str(it.get("label") or ""), police, taille,
                               larg_col - pw - 3 * mm)
                c.drawString(x0 + pw + 3 * mm, milieu - taille * 0.34, lib)
                # Séparateur
                if i < len(items) - 1:
                    c.setStrokeColor(BG)
                    c.setLineWidth(0.8)
                    c.line(x0, yy - h_ligne, x0 + larg_col, yy - h_ligne)
                yy -= h_ligne
            yy -= ESPACE_SECTION

    colonne(MARGE_X, gauche)
    colonne(MARGE_X + larg_col + GOUTTIERE, droite)

    # ── Pied ─────────────────────────────────────────────────────────
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.8)
    c.line(MARGE_X, MARGE_BAS + 5 * mm, larg - MARGE_X, MARGE_BAS + 5 * mm)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.5)
    c.drawString(MARGE_X, MARGE_BAS, "Référentiel %s · %d codes" % (APP_NAME, len(codes)))
    c.drawRightString(larg - MARGE_X, MARGE_BAS,
                      "Édition du " + datetime.now().strftime("%d/%m/%Y"))

    c.showPage()
    c.save()
    return buf.getvalue()
