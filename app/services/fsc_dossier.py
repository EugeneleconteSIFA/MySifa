"""
MySifa — dossier FSC fournisseurs : quel document retenir, et le PDF fusionné.

Quel document pour quel fournisseur
-----------------------------------
Un fournisseur peut avoir plusieurs certificats FSC déposés (ancien et
renouvelé, certificat et « statement » annexe), et un certificat de groupe peut
avoir été déposé sur une autre branche que la sienne — cas réel : le certificat
de Frimpeks Turkey (FSC-C129558) rangé sous Frimpeks Italy. La règle :

1. Candidats : les documents FSC du fournisseur, plus tout document FSC qui
   porte sa licence (dans son nom, son titre, ou lue dans son contenu), où
   qu'il ait été rangé.
2. Un document dont le NOM porte une autre licence est écarté, même rangé chez
   ce fournisseur : sinon Frimpeks Italy présenterait le certificat de
   Frimpeks Turkey déposé sous sa fiche.
3. Une pièce annexe (auto-déclaration RBUE, mémo EUDR, « statement »…) n'est
   jamais retenue comme certificat, même taguée FSC.
4. Le document qui porte la licence passe devant celui qui se dit certificat
   FSC, qui passe devant un simple tag ; à égalité, le non expiré d'abord, puis
   la date d'expiration la plus tardive.

Le PDF fusionné
---------------
Une page de garde (la liste des fournisseurs certifiés, exigée telle quelle par
l'audit CoC), puis chaque certificat retenu, avec un signet par fournisseur.
Une photo de certificat devient une page A4. Un fichier absent du disque ou
illisible ne bloque pas le dossier : il est signalé sur la page de garde.
"""
from __future__ import annotations

import io
import os
import re
from datetime import date, datetime
from typing import Optional


def _norm_licence(s: Optional[str]) -> str:
    """« FSC-C004451 », « FSC_C004451 », « fscc004451 » → « C004451 »."""
    m = re.search(r"C\s*[-_]?\s*(\d{6})", (s or "").upper())
    return f"C{m.group(1)}" if m else ""


def document_porte_licence(doc: dict, licence: Optional[str]) -> bool:
    cible = _norm_licence(licence)
    if not cible:
        return False
    for champ in ("fsc_licence_lue", "original_name", "titre"):
        valeur = (doc.get(champ) or "").upper().replace(" ", "")
        if cible in re.sub(r"[-_]", "", valeur):
            return True
    return False


def _licences_du_nom(doc: dict) -> set[str]:
    """Licences écrites dans le nom ou le titre du fichier (pas dans le contenu :
    un certificat de groupe liste toutes les licences de ses membres)."""
    txt = f"{doc.get('original_name') or ''} {doc.get('titre') or ''}".upper()
    return {f"C{m}" for m in re.findall(r"C\s*[-_]?\s*(\d{6})", txt)}


# Pièces qui accompagnent un certificat sans en être un. Elles sont souvent
# taguées FSC dans Ressources fournisseurs (auto-déclarations RBUE, mémo EUDR,
# « Statement on FSC Directive »…) et portent parfois une date d'expiration
# plus lointaine que le certificat : sans cette règle, elles passeraient devant.
_RE_ANNEXE = re.compile(
    r"statement|d[ée]claration|attestation|letter|lettre|directive|policy|politique|"
    r"memo|m[ée]mo|eudr|rbue|timber|origin|reach|rohs|\bfds\b|\bsds\b",
    re.I,
)


def rang_document(doc: dict, licence: Optional[str]) -> int:
    """3 = porte la licence · 2 = se dit certificat FSC · 1 = tagué FSC sans plus
    · 0 = pièce annexe, ou lu sans qu'aucune licence n'y figure. Un document de
    rang 0 n'est jamais présenté comme le certificat du fournisseur."""
    if document_porte_licence(doc, licence):
        return 3
    libelle = f"{doc.get('titre') or ''} {doc.get('original_name') or ''}"
    if _RE_ANNEXE.search(libelle):
        return 0
    rang = 2 if re.search(r"FSC|CERTIF", libelle, re.I) else 1
    # Lu pour de bon (motifs ou IA) sans qu'aucune licence n'y figure : le
    # document perd un rang. Il reste présentable s'il se dit certificat FSC
    # (la licence peut être écrite d'une façon que la lecture n'a pas reconnue),
    # il ne l'est plus s'il n'était que tagué. Une lecture qui n'a pas pu se
    # faire ne condamne rien.
    if doc.get("fsc_lecture_methode") in ("motifs", "ia") and not doc.get("fsc_licence_lue"):
        rang -= 1
    return rang


def choisir_document(fournisseur: dict, docs: list[dict], aujourdhui: Optional[date] = None) -> Optional[dict]:
    """Le certificat FSC à présenter pour ce fournisseur, ou None.

    `docs` : tous les documents FSC déposés, tous fournisseurs confondus
    (clé `fournisseur_id`) — un certificat rangé sous une autre branche du
    groupe n'est retrouvé que par sa licence.
    """
    aujourdhui = aujourdhui or date.today()
    iso = aujourdhui.isoformat()
    licence = fournisseur.get("licence")
    fid = fournisseur.get("id")
    cible = _norm_licence(licence)

    def autre_licence(d: dict) -> bool:
        noms = _licences_du_nom(d)
        return bool(noms) and bool(cible) and cible not in noms

    def score(d: dict):
        exp = (d.get("date_expiration") or d.get("fsc_expiration_lue") or "")[:10]
        non_expire = bool(exp) and exp >= iso
        return (rang_document(d, licence), d.get("fournisseur_id") == fid, non_expire,
                exp, d.get("uploaded_at") or "", d.get("id") or 0)

    candidats = [
        d for d in docs
        if (d.get("fournisseur_id") == fid or document_porte_licence(d, licence))
        and not autre_licence(d)
        and rang_document(d, licence) >= 1
    ]
    if not candidats:
        return None
    return max(candidats, key=score)


def statut_expiration(date_iso: Optional[str], alerte_jours: int, aujourdhui: Optional[date] = None) -> dict:
    """{statut: valide|a_renouveler|expire|sans_date, jours}"""
    aujourdhui = aujourdhui or date.today()
    if not date_iso:
        return {"statut": "sans_date", "jours": None}
    try:
        d = datetime.strptime(str(date_iso)[:10], "%Y-%m-%d").date()
    except ValueError:
        return {"statut": "sans_date", "jours": None}
    jours = (d - aujourdhui).days
    if jours < 0:
        return {"statut": "expire", "jours": jours}
    if jours <= alerte_jours:
        return {"statut": "a_renouveler", "jours": jours}
    return {"statut": "valide", "jours": jours}


# ══════════════════════════════════════════════════════════════════
# PDF fusionné
# ══════════════════════════════════════════════════════════════════

def _fr(d: Optional[str]) -> str:
    if not d:
        return "—"
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(d))
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else str(d)


def _page_image(chemin: str) -> bytes:
    """Une photo ou un scan image → une page A4 PDF, image centrée."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    largeur, hauteur = A4
    img = ImageReader(chemin)
    iw, ih = img.getSize()
    marge = 28
    ratio = min((largeur - 2 * marge) / iw, (hauteur - 2 * marge) / ih)
    w, h = iw * ratio, ih * ratio
    c.drawImage(img, (largeur - w) / 2, (hauteur - h) / 2, w, h, preserveAspectRatio=True)
    c.showPage()
    c.save()
    return buf.getvalue()


def _page_de_garde(lignes: list[dict], titre: str, sous_titre: str, pages_debut: dict) -> bytes:
    """Liste des fournisseurs certifiés, avec la page où commence chaque certificat."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
        title=titre,
    )
    st_titre = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=16, leading=20, spaceAfter=2)
    st_sous = ParagraphStyle("s", fontName="Helvetica", fontSize=9, leading=12,
                             textColor=colors.HexColor("#475569"))  # hex-ok (PDF reportlab)
    st_cell = ParagraphStyle("c", fontName="Helvetica", fontSize=8, leading=10)
    st_head = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white)

    def P(txt, style=st_cell):
        from xml.sax.saxutils import escape
        return Paragraph(escape(str(txt or "—")), style)

    entetes = ["Fournisseur", "Licence", "Certificat", "Expiration", "Catégories FSC",
               "Contrôle base FSC", "Page"]
    data = [[P(h, st_head) for h in entetes]]
    for l in lignes:
        ctrl = l.get("dernier_controle") or {}
        ctrl_txt = (f"{_fr(ctrl.get('date_controle'))} · {ctrl.get('statut_label') or ''}"
                    if ctrl else "Non contrôlé")
        page = pages_debut.get(l["id"])
        data.append([
            P(l.get("nom")),
            P(l.get("licence")),
            P(l.get("certificat")),
            P(_fr(l.get("expiration"))),
            P(", ".join(l.get("claims_labels") or []) or "Non renseignées"),
            P(ctrl_txt),
            P(str(page) if page else (l.get("note_dossier") or "Aucun document")),
        ])

    table = Table(data, repeatRows=1,
                  colWidths=[52 * mm, 26 * mm, 36 * mm, 22 * mm, 60 * mm, 44 * mm, 29 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),  # hex-ok (PDF reportlab)
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),  # hex-ok (PDF reportlab)
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),  # hex-ok (PDF reportlab)
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    doc.build([Paragraph(titre, st_titre), Paragraph(sous_titre, st_sous), Spacer(1, 6 * mm), table])
    return buf.getvalue()


def construire_dossier_pdf(lignes: list[dict], dossier_uploads: str, titre: str, sous_titre: str) -> bytes:
    """PDF unique : page de garde + certificats retenus, un signet par fournisseur.

    `lignes` : [{id, nom, licence, certificat, expiration, claims_labels,
                 dernier_controle, document: {filename, original_name, mime_type} | None}]
    """
    from pypdf import PdfReader, PdfWriter

    # 1. Charger chaque document, sans rien écrire encore : la page de garde
    #    doit connaître le nombre de pages de chacun pour afficher ses renvois.
    blocs: list[tuple[dict, Optional[PdfReader]]] = []
    for l in lignes:
        d = l.get("document")
        lecteur = None
        if d:
            chemin = os.path.join(dossier_uploads, d.get("filename") or "")
            nom = (d.get("original_name") or d.get("filename") or "").lower()
            mime = (d.get("mime_type") or "").lower()
            try:
                if not os.path.isfile(chemin):
                    l["note_dossier"] = "Fichier absent du serveur"
                elif nom.endswith(".pdf") or "pdf" in mime:
                    lecteur = PdfReader(chemin)
                    if lecteur.is_encrypted:
                        try:
                            lecteur.decrypt("")
                        except Exception:
                            lecteur = None
                            l["note_dossier"] = "PDF protégé"
                elif re.search(r"\.(png|jpe?g|webp|gif)$", nom) or mime.startswith("image/"):
                    lecteur = PdfReader(io.BytesIO(_page_image(chemin)))
                else:
                    l["note_dossier"] = "Format non fusionnable"
            except Exception:
                lecteur = None
                l["note_dossier"] = "Fichier illisible"
        blocs.append((l, lecteur))

    # 2. Page de garde en deux passes : la première mesure sa propre longueur.
    def debuts(nb_garde: int) -> dict:
        out, courant = {}, nb_garde + 1
        for l, lecteur in blocs:
            if lecteur is not None:
                out[l["id"]] = courant
                courant += len(lecteur.pages)
        return out

    garde = _page_de_garde(lignes, titre, sous_titre, debuts(1))
    nb_garde = len(PdfReader(io.BytesIO(garde)).pages)
    if nb_garde != 1:
        garde = _page_de_garde(lignes, titre, sous_titre, debuts(nb_garde))

    # 3. Assemblage.
    writer = PdfWriter()
    for page in PdfReader(io.BytesIO(garde)).pages:
        writer.add_page(page)
    writer.add_outline_item("Liste des fournisseurs certifiés", 0)
    for l, lecteur in blocs:
        if lecteur is None:
            continue
        debut = len(writer.pages)
        for page in lecteur.pages:
            writer.add_page(page)
        libelle = l.get("nom") or "Fournisseur"
        if l.get("licence"):
            libelle += f" · {l['licence']}"
        writer.add_outline_item(libelle, debut)
    writer.add_metadata({"/Title": titre})
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
