"""
Générateur PDF — Fiche de non-conformité.

Reprend le contenu de la fiche Excel historique (identification, observation,
cause, actions, validations) dans une mise en page lisible d'un coup d'oeil :
bandeau d'état en tête, photos intégrées, frise des étapes de suivi.

Nom, adresse et logo de l'organisation viennent de config.py (APP_ORG_NAME,
APP_ORG_ADRESSE, BAT_LOGO_PATH) : rien de propre à une entreprise ici.
"""
from __future__ import annotations

import os
from datetime import datetime
from io import BytesIO
from typing import Any, List, Optional
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from app.services.notes_export import _glyphes, _police

W, H = A4
MARGE = 15 * mm
LARGEUR = W - 2 * MARGE

# Palette du document imprimé (indépendante du thème écran).
ENCRE = colors.HexColor("#0f172a")
GRIS = colors.HexColor("#64748b")
FILET = colors.HexColor("#e2e8f0")
FOND = colors.HexColor("#f8fafc")
ACCENT = colors.HexColor("#0e7490")
ACCENT_FOND = colors.HexColor("#ecfeff")
OK = colors.HexColor("#047857")
OK_FOND = colors.HexColor("#ecfdf5")
ALERTE = colors.HexColor("#c2410c")
ALERTE_FOND = colors.HexColor("#fff7ed")
NEUTRE_FOND = colors.HexColor("#f1f5f9")

_TYPE = {"interne": "Interne", "client": "Client", "fournisseur": "Fournisseur", "logistique": "Logistique"}
_GRAVITE = {"mineure": "Mineure", "majeure": "Majeure", "critique": "Critique"}
_IMAGES = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")


def _date(s: Optional[str]) -> str:
    if not s:
        return ""
    s = str(s)
    if len(s) >= 10 and s[4] == "-":
        return f"{s[8:10]}/{s[5:7]}/{s[0:4]}"
    return s


def _t(val: Any) -> str:
    """Texte prêt pour un Paragraph : échappé, glyphes connus de la police."""
    if val is None:
        return ""
    return escape(_glyphes(str(val))).replace("\n", "<br/>")


class _Styles:
    def __init__(self):
        police, _ = _police()
        gras = police + "-Gras" if police != "Helvetica" else "Helvetica-Bold"
        self.police, self.gras = police, gras
        base = dict(fontName=police, textColor=ENCRE, alignment=TA_LEFT)
        self.corps = ParagraphStyle("corps", fontSize=9.5, leading=13, **base)
        self.petit = ParagraphStyle("petit", fontSize=8, leading=10.5, **{**base, "textColor": GRIS})
        self.label = ParagraphStyle("label", fontSize=7, leading=9, **{**base, "fontName": gras, "textColor": GRIS})
        self.valeur = ParagraphStyle("valeur", fontSize=10, leading=13, **{**base, "fontName": gras})
        self.titre_section = ParagraphStyle("ts", fontSize=10.5, leading=14, **{**base, "fontName": gras, "textColor": ACCENT})
        self.vide = ParagraphStyle("vide", fontSize=9, leading=12, **{**base, "textColor": GRIS})
        self.num = ParagraphStyle("num", fontSize=17, leading=21, **{**base, "fontName": gras, "alignment": TA_RIGHT})
        self.doc_titre = ParagraphStyle("dt", fontSize=8, leading=10, **{**base, "fontName": gras, "textColor": ACCENT, "alignment": TA_RIGHT})
        self.droite = ParagraphStyle("dr", fontSize=8.5, leading=11, **{**base, "textColor": GRIS, "alignment": TA_RIGHT})
        self.org = ParagraphStyle("org", fontSize=11, leading=14, **{**base, "fontName": gras})
        self.date = ParagraphStyle("date", fontSize=9, leading=13, **{**base, "fontName": gras})
        self.pastille = ParagraphStyle("pa", fontSize=8.5, leading=11, **{**base, "fontName": gras})


def _organisation():
    import config
    nom = str(getattr(config, "APP_ORG_NAME", "") or "")
    adresse = [l.strip() for l in str(getattr(config, "APP_ORG_ADRESSE", "") or "").split("\n") if l.strip()]
    logo = None
    for attr in ("APP_LOGO_PATH", "BAT_LOGO_PATH"):
        chemin = getattr(config, attr, None)
        if chemin and os.path.isfile(chemin):
            logo = chemin
            break
    return nom, adresse, logo


def _image(path: str, max_l: float, max_h: float) -> Optional[Image]:
    try:
        from PIL import Image as PILImage
        with PILImage.open(path) as im:
            l, h = im.size
            if im.mode not in ("RGB", "L") or path.lower().endswith((".webp", ".gif", ".bmp")):
                buf = BytesIO()
                im.convert("RGB").save(buf, "JPEG", quality=85)
                buf.seek(0)
                src = buf
            else:
                src = path
        ratio = min(max_l / l, max_h / h)
        return Image(src, width=l * ratio, height=h * ratio)
    except Exception:
        return None


def _section(titre: str, contenu: list, st: _Styles):
    """Bloc titré : filet coloré à gauche, fond très clair."""
    inner = Table([[Paragraph(_t(titre).upper(), st.titre_section)]] + [[c] for c in contenu],
                  colWidths=[LARGEUR - 6 * mm])
    inner.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
    ]))
    t = Table([[inner]], colWidths=[LARGEUR])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), FOND),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 3 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
    ]))
    return t


def _texte_ou_vide(val: Optional[str], st: _Styles, vide: str = "Non renseigné."):
    v = (val or "").strip()
    return Paragraph(_t(v), st.corps) if v else Paragraph(_t(vide), st.vide)


def _pastilles(items, st: _Styles):
    """items = [(texte, couleur_texte, couleur_fond)]."""
    cells = [Paragraph(_t(txt), ParagraphStyle("p", parent=st.pastille, textColor=c)) for txt, c, _ in items]
    largeur = LARGEUR / len(items)
    t = Table([cells], colWidths=[largeur - 2 * mm] * len(items), spaceBefore=0)
    style = [("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
             ("LEFTPADDING", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    for i, (_, c, fond) in enumerate(items):
        style += [("BACKGROUND", (i, 0), (i, 0), fond), ("LINEBEFORE", (i, 0), (i, 0), 2.5, c)]
    t.setStyle(TableStyle(style))
    return t


def render_nc_pdf(nc: dict, fichiers: Optional[List[dict]] = None) -> bytes:
    st = _Styles()
    fichiers = fichiers or []
    buf = BytesIO()
    numero = nc.get("numero") or ""
    org_nom, org_adresse, logo = _organisation()
    edite = datetime.now().strftime("%d/%m/%Y %H:%M")

    def pied(c, doc):
        c.saveState()
        c.setStrokeColor(FILET)
        c.setLineWidth(0.5)
        c.line(MARGE, 12 * mm, W - MARGE, 12 * mm)
        c.setFont(st.police, 7.5)
        c.setFillColor(GRIS)
        c.drawString(MARGE, 8 * mm, _glyphes(f"Non-conformité {numero} · éditée le {edite}"))
        c.drawRightString(W - MARGE, 8 * mm, f"Page {doc.page}")
        c.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=MARGE, rightMargin=MARGE,
                            topMargin=MARGE, bottomMargin=18 * mm,
                            title=f"Non-conformité {numero}", author=org_nom)
    story: list = []

    # ── En-tête : organisation à gauche, numéro à droite ──────────────
    gauche = []
    if logo:
        img = _image(logo, 38 * mm, 14 * mm)
        if img:
            img.hAlign = "LEFT"
            gauche.append(img)
    if org_nom:
        gauche.append(Paragraph(_t(org_nom), st.org))
    for l in org_adresse:
        gauche.append(Paragraph(_t(l), st.petit))
    droite = [Paragraph("FICHE DE NON-CONFORMITÉ", st.doc_titre),
              Paragraph(_t(numero), st.num),
              Paragraph(_t("Date de la NC : " + (_date(nc.get("date_nc")) or "—")), st.droite)]
    if nc.get("numero_ar"):
        droite.append(Paragraph(_t("Commande AR " + str(nc["numero_ar"])), st.droite))
    entete = Table([[gauche, droite]], colWidths=[LARGEUR * 0.55, LARGEUR * 0.45])
    entete.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                ("LINEBELOW", (0, 0), (-1, 0), 1, ACCENT), ("BOTTOMPADDING", (0, 0), (-1, 0), 4 * mm)]))
    story += [entete, Spacer(1, 4 * mm)]

    # ── Bandeau d'état ────────────────────────────────────────────────
    cloturee = nc.get("statut") == "cloturee"
    etat = (f"Clôturée le {_date(nc.get('date_cloture'))}", GRIS, NEUTRE_FOND) if cloturee \
        else ("En cours", ACCENT, ACCENT_FOND)
    ar = (f"Accusé de réception client envoyé{(' le ' + _date(nc.get('ar_client_envoye_at'))) if nc.get('ar_client_envoye_at') else ''}", OK, OK_FOND) \
        if nc.get("ar_client_envoye") else ("Accusé de réception client non envoyé", ALERTE, ALERTE_FOND)
    jours = nc.get("jours_sans_action")
    der = _date(nc.get("derniere_action_at")) or "—"
    if not cloturee and nc.get("a_relancer"):
        action = (f"Dernière action le {der} · {jours} j sans avancée", ALERTE, ALERTE_FOND)
    else:
        action = (f"Dernière action le {der}", ENCRE, NEUTRE_FOND)
    story += [_pastilles([etat, ar, action], st), Spacer(1, 5 * mm)]

    # ── Identification ────────────────────────────────────────────────
    def champ(lbl, val):
        return [Paragraph(_t(lbl).upper(), st.label), Paragraph(_t(val or "—"), st.valeur)]

    produit = " · ".join(p for p in (nc.get("ref_client"), nc.get("descriptif_produit")) if p)
    lignes = [
        (champ("Client", nc.get("client_fournisseur")), champ("Produit", produit)),
        (champ("Référence dossier", nc.get("no_dossier")), champ("Quantité concernée", nc.get("quantite_concernee"))),
        (champ("Type · gravité", f"{_TYPE.get(nc.get('type_nc'), nc.get('type_nc') or '')} · {_GRAVITE.get(nc.get('gravite'), nc.get('gravite') or '')}"),
         champ("Ouverte par", nc.get("emetteur_nom") or nc.get("created_by_nom"))),
    ]
    data = [[a, b] for a, b in lignes]
    ident = Table(data, colWidths=[LARGEUR / 2, LARGEUR / 2])
    ident.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
    ]))
    story += [ident, Spacer(1, 1 * mm)]

    # ── Observation ──────────────────────────────────────────────────
    story += [_section("Observation", [_texte_ou_vide(nc.get("description"), st)], st), Spacer(1, 4 * mm)]

    # ── Photos et documents ──────────────────────────────────────────
    images = [f for f in fichiers if (f.get("original_name") or "").lower().endswith(_IMAGES)
              or (f.get("mime_type") or "").startswith("image/")]
    autres = [f for f in fichiers if f not in images]
    if images:
        larg = (LARGEUR - 14 * mm) / 2
        cells = []
        for f in images:
            img = _image(f.get("path") or "", larg, 55 * mm)
            if img is None:
                autres.append(f)
                continue
            cells.append([img, Paragraph(_t(f.get("original_name")), st.petit)])
        if cells:
            rangs = [cells[i:i + 2] + ([""] if len(cells[i:i + 2]) == 1 else []) for i in range(0, len(cells), 2)]
            grille = Table(rangs, colWidths=[larg + 2 * mm, larg + 2 * mm])
            grille.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm)]))
            story += [_section(f"Photos ({len(cells)})", [grille], st), Spacer(1, 4 * mm)]
    if autres:
        lst = [Paragraph(_t(f"· {f.get('original_name')}  —  ajouté le {_date(f.get('uploaded_at'))}"), st.corps) for f in autres]
        story += [_section("Documents joints", lst, st), Spacer(1, 4 * mm)]

    # ── Cause et actions ─────────────────────────────────────────────
    story += [KeepTogether(_section("Cause de la non-conformité", [_texte_ou_vide(nc.get("analyse_causes"), st)], st)),
              Spacer(1, 4 * mm)]
    actions = [Paragraph("CORRIGER", st.label), _texte_ou_vide(nc.get("action_corrective"), st)]
    if (nc.get("action_preventive") or "").strip():
        actions += [Spacer(1, 2 * mm), Paragraph("ÉVITER QUE ÇA SE REPRODUISE", st.label),
                    _texte_ou_vide(nc.get("action_preventive"), st)]
    story += [KeepTogether(_section("Actions correctives", actions, st)), Spacer(1, 4 * mm)]

    # ── Suivi (ordre chronologique) ──────────────────────────────────
    suivis = sorted(nc.get("suivis") or [], key=lambda s: (s.get("date_action") or "", s.get("id") or 0))
    if suivis:
        rangs = []
        for s in suivis:
            rangs.append([Paragraph(_t(_date(s.get("date_action"))), st.date),
                          Paragraph(_t(s.get("texte")), st.corps),
                          Paragraph(_t(s.get("auteur_nom") or ""), st.petit)])
        frise = Table(rangs, colWidths=[22 * mm, LARGEUR - 6 * mm - 22 * mm - 34 * mm, 34 * mm])
        frise.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, FILET),
        ]))
        contenu = [frise]
    else:
        contenu = [Paragraph("Aucune étape enregistrée.", st.vide)]
    story += [_section(f"Suivi · {len(suivis)} étape{'s' if len(suivis) > 1 else ''}", contenu, st), Spacer(1, 5 * mm)]

    # ── Validations ──────────────────────────────────────────────────
    def visa(titre, nom, at):
        lignes_v = [Paragraph(_t(titre).upper(), st.label)]
        if nom:
            lignes_v += [Paragraph(_t(nom), st.valeur), Paragraph(_t("Signé le " + _date(at)), st.petit)]
        else:
            lignes_v += [Spacer(1, 12 * mm), Paragraph("Nom, date et signature", st.petit)]
        return lignes_v

    visas = Table([[visa("Direction qualité", nc.get("validation_qualite_nom"), nc.get("validation_qualite_at")),
                    visa("Direction industrielle", nc.get("validation_industrielle_nom"), nc.get("validation_industrielle_at"))]],
                  colWidths=[LARGEUR / 2 - 2 * mm, LARGEUR / 2 - 2 * mm])
    visas.setStyle(TableStyle([("BOX", (0, 0), (0, 0), 0.6, FILET), ("BOX", (1, 0), (1, 0), 0.6, FILET),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("TOPPADDING", (0, 0), (-1, -1), 3 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
                               ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm)]))
    story.append(KeepTogether(visas))

    doc.build(story, onFirstPage=pied, onLaterPages=pied)
    return buf.getvalue()
