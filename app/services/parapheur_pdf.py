"""MyTools › Parapheur — lecture du PDF d'origine et scellement du document final.

Trois étapes, toutes côté serveur (pypdf + reportlab, déjà au requirements) :

1. `apposer()` : chaque zone reçoit son contenu (image de la signature ou du
   paraphe, date de signature, nom) sur une surcouche fusionnée à la page.
   Les zones sont rangées en fractions de la page AFFICHÉE (rotation
   appliquée, origine en haut à gauche) ; `vers_pdf()` les ramène dans
   l'espace utilisateur PDF, comme `versPdf()` de l'éditeur PDF.
2. `certificat()` : page(s) ajoutée(s) en fin de document — demande,
   signataires, dates, IP, méthode, historique, empreintes SHA-256 du document
   d'origine et du document signé (pages signées, hors certificat : une page ne
   peut pas contenir l'empreinte du fichier qui la contient ; l'empreinte du
   fichier final complet est gardée en base et affichée dans le suivi).
3. `appliquer_niveau()` : POINT D'EXTENSION eIDAS. Le niveau « simple » rend
   le PDF tel quel (signature électronique simple). Une signature avancée ou
   qualifiée (PAdES, certificat de signataire, horodatage qualifié, prestataire
   de confiance qualifié) s'ajoute en déclarant une fonction dans `NIVEAUX` qui
   reçoit le PDF final et son contexte et rend le PDF signé
   cryptographiquement ; `PARAPHEUR_NIVEAU` (config.py) la choisit. Rien
   d'autre n'est à modifier : l'empreinte finale est calculée après.

Aucune couleur d'interface ici : ce sont les couleurs d'un document imprimé.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Callable
from xml.sax.saxutils import escape

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ENCRE = colors.Color(0.08, 0.09, 0.14)
GRIS = colors.Color(0.42, 0.45, 0.5)
FILET = colors.Color(0.82, 0.84, 0.87)
FOND = colors.Color(0.95, 0.96, 0.97)

TYPES_ZONE = ("signature", "paraphe", "date", "nom")


# ── Lecture ─────────────────────────────────────────────────────────────

def lire(octets: bytes) -> PdfReader:
    if not octets or not octets[:1024].lstrip().startswith(b"%PDF"):
        raise ValueError("Fichier non reconnu comme PDF.")
    try:
        r = PdfReader(io.BytesIO(octets))
    except Exception:
        raise ValueError("PDF illisible.")
    if r.is_encrypted:
        try:
            if not r.decrypt(""):
                raise ValueError
        except Exception:
            raise ValueError("PDF protégé par mot de passe — le déverrouiller avant de l'envoyer.")
    return r


def pages(octets: bytes) -> list[dict]:
    """Dimensions de chaque page TELLE QU'AFFICHÉE (points), avec la boîte et
    la rotation qui servent à revenir à l'espace PDF."""
    r = lire(octets)
    out = []
    for p in r.pages:
        mb = p.mediabox
        x0, y0, x1, y1 = float(mb.left), float(mb.bottom), float(mb.right), float(mb.top)
        rot = int(p.rotation or 0) % 360
        w, h = x1 - x0, y1 - y0
        if rot in (90, 270):
            w, h = h, w
        out.append({"w": round(w, 2), "h": round(h, 2), "rot": rot, "box": [x0, y0, x1, y1]})
    if not out:
        raise ValueError("PDF sans page.")
    return out


def vers_pdf(box: list[float], rot: int, u: float, v: float) -> tuple[float, float]:
    """Point de la page affichée (u, v en points, origine haut-gauche) vers
    l'espace utilisateur PDF. Même table que versPdf() de l'éditeur PDF."""
    x0, y0, x1, y1 = box
    if rot == 90:
        return x0 + v, y0 + u
    if rot == 180:
        return x1 - u, y0 + v
    if rot == 270:
        return x1 - v, y1 - u
    return x0 + u, y1 - v


def date_fr(iso: str | None, heure: bool = False) -> str:
    if not iso:
        return ""
    try:
        d = datetime.fromisoformat(str(iso)[:19])
    except ValueError:
        return str(iso)
    return d.strftime("%d/%m/%Y à %H:%M:%S" if heure else "%d/%m/%Y")


# ── Apposition des signatures ───────────────────────────────────────────

def _poser_image(c, png: bytes, w: float, h: float) -> None:
    img = ImageReader(io.BytesIO(png))
    iw, ih = img.getSize()
    if not iw or not ih:
        return
    k = min(w / iw, h / ih)
    dw, dh = iw * k, ih * k
    c.drawImage(img, (w - dw) / 2, (h - dh) / 2, dw, dh, mask="auto")


def _poser_texte(c, texte: str, w: float, h: float) -> None:
    taille = max(5.0, min(h * 0.6, 12.0))
    while taille > 5 and c.stringWidth(texte, "Helvetica", taille) > w - 2:
        taille -= 0.5
    c.setFillColor(ENCRE)
    c.setFont("Helvetica", taille)
    c.drawString(1, (h - taille) / 2 + taille * 0.22, texte)


def apposer(original: bytes, zones: list[dict], signataires: dict[int, dict]) -> bytes:
    """PDF d'origine + contenu de chaque zone. `signataires` : id → ligne
    (signature_png, paraphe_png, signe_le, nom_saisi, nom)."""
    r = lire(original)
    w = PdfWriter(clone_from=r)
    par_page: dict[int, list[dict]] = {}
    for z in zones:
        par_page.setdefault(int(z["page"]), []).append(z)
    for num, zs in par_page.items():
        if num < 1 or num > len(w.pages):
            continue
        page = w.pages[num - 1]
        mb = page.mediabox
        box = [float(mb.left), float(mb.bottom), float(mb.right), float(mb.top)]
        rot = int(page.rotation or 0) % 360
        lw, lh = box[2] - box[0], box[3] - box[1]
        if rot in (90, 270):
            lw, lh = lh, lw
        tampon = io.BytesIO()
        c = rl_canvas.Canvas(tampon, pagesize=(max(box[2], 1), max(box[3], 1)))
        for z in zs:
            s = signataires.get(int(z["signataire_id"]))
            if not s or not s.get("signe_le"):
                continue
            u, v = float(z["x"]) * lw, float(z["y"]) * lh
            zw, zh = float(z["w"]) * lw, float(z["h"]) * lh
            ax, ay = vers_pdf(box, rot, u, v + zh)
            c.saveState()
            c.translate(ax, ay)
            if rot:
                c.rotate(rot)
            t = z["type"]
            if t == "signature" and s.get("signature_png"):
                _poser_image(c, s["signature_png"], zw, zh)
            elif t == "paraphe" and (s.get("paraphe_png") or s.get("signature_png")):
                _poser_image(c, s.get("paraphe_png") or s["signature_png"], zw, zh)
            elif t == "date":
                _poser_texte(c, date_fr(s["signe_le"]), zw, zh)
            elif t == "nom":
                _poser_texte(c, (s.get("nom_saisi") or s.get("nom") or "")[:80], zw, zh)
            c.restoreState()
        c.showPage()
        c.save()
        surcouche = PdfReader(io.BytesIO(tampon.getvalue())).pages[0]
        page.merge_page(surcouche)
    sortie = io.BytesIO()
    w.write(sortie)
    return sortie.getvalue()


# ── Certificat ──────────────────────────────────────────────────────────

_STATUT_SIG = {"signe": "Signé", "refuse": "Refusé", "attente": "En attente", "a_signer": "À signer",
               "ouvert": "Consulté", "expire": "Expiré", "annule": "Annulé"}
_METHODE = {"dessin": "Signature tracée", "texte": "Signature saisie", "reutilise": "Signature réutilisée"}


def _p(texte: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(texte or "")).replace("\n", "<br/>"), style)


def certificat(demande: dict, signataires: list[dict], evenements: list[dict], *,
               organisation: str, sha_original: str, sha_signe: str, niveau_libelle: str) -> bytes:
    tampon = io.BytesIO()
    doc = SimpleDocTemplate(tampon, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"Certificat de signature — {demande.get('titre') or ''}",
                            author=organisation)
    st_titre = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=ENCRE)
    st_sous = ParagraphStyle("s", fontName="Helvetica", fontSize=9, leading=12, textColor=GRIS)
    st_h = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=ENCRE,
                          spaceBefore=8, spaceAfter=4)
    st = ParagraphStyle("n", fontName="Helvetica", fontSize=8.5, leading=11, textColor=ENCRE)
    st_m = ParagraphStyle("m", fontName="Courier", fontSize=7.5, leading=10, textColor=ENCRE)
    st_g = ParagraphStyle("g", fontName="Helvetica", fontSize=8, leading=10.5, textColor=GRIS)

    elems = [
        _p("Certificat de signature", st_titre),
        _p(f"{organisation} · Parapheur · demande n° {demande['id']}", st_sous),
        Spacer(1, 8),
    ]
    infos = [
        ("Document", demande.get("nom_fichier") or ""),
        ("Objet", demande.get("titre") or ""),
        ("Émise par", " — ".join(x for x in (demande.get("cree_par_nom"), demande.get("cree_par_email")) if x)),
        ("Créée le", date_fr(demande.get("cree_le"), heure=True)),
        ("Terminée le", date_fr(demande.get("termine_le"), heure=True)),
        ("Ordre de signature", "Séquentiel" if demande.get("mode") == "sequentiel" else "Parallèle"),
        ("Pages du document", str(demande.get("nb_pages") or "")),
        ("Niveau", niveau_libelle),
    ]
    t = Table([[_p(a, st_g), _p(b, st)] for a, b in infos], colWidths=[42 * mm, None])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                           ("TOPPADDING", (0, 0), (-1, -1), 2)]))
    elems += [t, _p("Empreintes SHA-256", st_h)]
    t = Table([
        [_p("Document d'origine", st_g), _p(sha_original, st_m)],
        [_p("Document signé (pages signées, hors certificat)", st_g), _p(sha_signe, st_m)],
    ], colWidths=[62 * mm, None])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOX", (0, 0), (-1, -1), 0.5, FILET),
                           ("BACKGROUND", (0, 0), (-1, -1), FOND), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                           ("TOPPADDING", (0, 0), (-1, -1), 4)]))
    elems += [t, _p("Signataires", st_h)]
    lignes = [[_p(x, st_g) for x in ("N°", "Signataire", "Statut et date", "Adresse IP", "Méthode")]]
    for s in signataires:
        qui = s.get("nom") or s.get("email") or ""
        if s.get("organisation"):
            qui += f"\n{s['organisation']}"
        if s.get("email"):
            qui += f"\n{s['email']}"
        qui += "\n" + ("Utilisateur interne" if s.get("type") == "interne" else "Contact externe (Espace)")
        quand = _STATUT_SIG.get(s.get("statut"), s.get("statut") or "")
        if s.get("signe_le"):
            quand += "\n" + date_fr(s["signe_le"], heure=True)
        elif s.get("refuse_le"):
            quand += "\n" + date_fr(s["refuse_le"], heure=True)
            if s.get("motif_refus"):
                quand += "\nMotif : " + s["motif_refus"][:300]
        methode = _METHODE.get(s.get("mode_signature") or "", "")
        if s.get("nom_saisi"):
            methode += f"\nNom déclaré : {s['nom_saisi']}"
        if s.get("ouvert_le"):
            methode += "\nConsulté le " + date_fr(s["ouvert_le"], heure=True)
        lignes.append([_p(str(s.get("ordre") or ""), st), _p(qui, st), _p(quand, st),
                       _p(s.get("ip") or "", st_m), _p(methode, st)])
    t = Table(lignes, colWidths=[9 * mm, 58 * mm, 38 * mm, 28 * mm, None], repeatRows=1)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, FILET),
                           ("BACKGROUND", (0, 0), (-1, 0), FOND), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                           ("TOPPADDING", (0, 0), (-1, -1), 4)]))
    elems += [t, _p("Historique", st_h)]
    hist = [[_p(date_fr(e.get("le"), heure=True), st_g), _p(e.get("libelle") or e.get("type") or "", st),
             _p(" · ".join(x for x in (e.get("acteur"), e.get("detail")) if x), st),
             _p(e.get("ip") or "", st_m)] for e in evenements]
    if hist:
        t = Table(hist, colWidths=[34 * mm, 34 * mm, None, 28 * mm], repeatRows=0)
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.3, FILET),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("TOPPADDING", (0, 0), (-1, -1), 2)]))
        elems.append(t)
    elems += [Spacer(1, 10), _p(
        "Signature électronique simple : ce certificat atteste des actions enregistrées par le parapheur "
        f"de {organisation} (identité déclarée, adresse électronique ou compte utilisateur, adresse IP, "
        "horodatage du serveur). Il ne constitue pas une signature électronique avancée ou qualifiée au sens "
        "du règlement eIDAS. L'empreinte SHA-256 du fichier final complet est conservée par l'émetteur.", st_g)]
    doc.build(elems)
    return tampon.getvalue()


def assembler(signe: bytes, cert: bytes, *, organisation: str, demande_id: int, titre: str) -> bytes:
    w = PdfWriter(clone_from=PdfReader(io.BytesIO(signe)))
    for p in PdfReader(io.BytesIO(cert)).pages:
        w.add_page(p)
    try:
        w.add_metadata({"/Producer": f"{organisation} — Parapheur",
                        "/Subject": f"Demande de signature n° {demande_id} · {titre}"[:200]})
    except Exception:
        pass
    sortie = io.BytesIO()
    w.write(sortie)
    return sortie.getvalue()


# ── Niveau de signature (point d'extension eIDAS) ───────────────────────

def _niveau_simple(pdf: bytes, contexte: dict) -> bytes:
    return pdf


# nom → (libellé imprimé sur le certificat, fonction(pdf, contexte) -> pdf).
# Ajouter ici « avancee » / « qualifiee » (PAdES via un prestataire de
# confiance qualifié ou un certificat PKCS#12 et pyHanko) : la fonction reçoit
# le PDF final et {demande, signataires} et rend le PDF signé.
NIVEAUX: dict[str, tuple[str, Callable[[bytes, dict], bytes]]] = {
    "simple": ("Signature électronique simple (non qualifiée au sens eIDAS)", _niveau_simple),
}


def niveau(nom: str) -> tuple[str, Callable[[bytes, dict], bytes]]:
    if nom not in NIVEAUX:
        raise ValueError(f"Niveau de signature inconnu : {nom!r} (PARAPHEUR_NIVEAU).")
    return NIVEAUX[nom]
