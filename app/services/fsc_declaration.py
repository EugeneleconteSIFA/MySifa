"""
MySifa — déclaration de contrôle des certificats fournisseurs (pièce d'audit CoC).

Ce que ce document est
----------------------
La pièce que l'auditeur FSC demande au titre de la section 2 de
FSC-STD-40-004 V3-1 : la preuve que l'organisation a vérifié, sur la base
publique FSC, les certificats des fournisseurs dont elle achète de la matière
sous allégation. Il ne s'agit PAS d'une attestation de conformité des
fournisseurs : c'est une déclaration datée et signée de ce que
l'organisation a contrôlé, avec ce que la base affichait ce jour-là.

Conséquence sur le contenu : les écarts font partie de la preuve. Un contrôle
qui ne relève jamais rien ressemble à un contrôle qui n'a pas eu lieu, et le
document liste donc explicitement les certificats non contrôlés, périmés,
suspendus, ou dont la portée ne couvre pas ce que l'organisation achète.

D'où viennent les données
-------------------------
Du DERNIER contrôle enregistré pour chaque fournisseur actif
(`qualite_fsc_controles`), tel que le routeur le prépare déjà dans
`_synthese()` — mêmes lignes que l'écran et que le dossier PDF fusionné, donc
aucun troisième chiffre possible pour un même fournisseur.

Rien n'est déduit ni complété : un champ absent en base s'affiche « — ». Le
titulaire du certificat lu sur la base n'est pas persisté aujourd'hui, il ne
figure donc pas dans le tableau ; ce qui a été relevé à la main lors du
contrôle est dans la colonne Constat, via la note du contrôle.
"""
from __future__ import annotations

import io
import re
from datetime import date, datetime
from typing import Optional


# ─── petits formatteurs ───────────────────────────────────────────────

def _fr(d: Optional[str]) -> str:
    if not d:
        return "—"
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(d))
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else str(d)


def _jour(d: Optional[str]) -> Optional[str]:
    return (str(d)[:10] or None) if d else None


def constats(ligne: dict) -> list[str]:
    """Ce qui doit être dit sur cette ligne, sans rien inventer.

    Ordre : l'absence de contrôle d'abord (elle prime sur tout le reste),
    puis les alertes déjà calculées par le routeur, puis la note saisie par
    la personne qui a fait le contrôle.
    """
    ctrl = ligne.get("dernier_controle") or {}
    out: list[str] = []
    if not ctrl:
        out.append("Jamais contrôlé sur la base FSC")
    elif ctrl.get("a_refaire"):
        out.append("Contrôle à refaire (antériorité dépassée)")
    for a in ligne.get("alertes") or []:
        if a not in out:
            out.append(a)
    note = (ctrl.get("note") or "").strip()
    if note:
        out.append(note)
    if not ctrl.get("justificatif") and ctrl:
        out.append("Justificatif horodaté absent")
    return out


def resume(lignes: list[dict]) -> dict:
    """Les chiffres de l'en-tête. Un fournisseur est « en écart » dès qu'il a
    au moins un constat — c'est la même règle que la section Écarts."""
    dates = sorted({_jour((l.get("dernier_controle") or {}).get("date_controle"))
                    for l in lignes if l.get("dernier_controle")} - {None})
    return {
        "total": len(lignes),
        "controles": sum(1 for l in lignes if l.get("dernier_controle")),
        "non_controles": sum(1 for l in lignes if not l.get("dernier_controle")),
        "a_refaire": sum(1 for l in lignes
                         if (l.get("dernier_controle") or {}).get("a_refaire")),
        "valides": sum(1 for l in lignes
                       if (l.get("dernier_controle") or {}).get("statut_base") == "valide"),
        "en_ecart": sum(1 for l in lignes if constats(l)),
        "premier_controle": dates[0] if dates else None,
        "dernier_controle": dates[-1] if dates else None,
    }


# ─── le PDF ───────────────────────────────────────────────────────────

def construire_declaration_pdf(
    lignes: list[dict],
    *,
    organisation: str,
    licence_sifa: str = "",
    responsables: str = "",
    edite_par: str = "",
    validite_jours: Optional[int] = None,
    aujourdhui: Optional[date] = None,
) -> bytes:
    """Déclaration de contrôle, une page A4 paysage (plus si le tableau déborde).

    `lignes` : les lignes de `_synthese()` — {id, nom, licence, certificat,
    expiration, alertes, dernier_controle{date_controle, statut_label,
    statut_base, a_refaire, note, justificatif}}.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate,
                                    Spacer, Table, TableStyle)
    from xml.sax.saxutils import escape

    aujourdhui = aujourdhui or date.today()
    r = resume(lignes)
    titre = "Déclaration de contrôle des certificats fournisseurs"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
        title=titre, author=organisation,
    )
    ENCRE = colors.HexColor("#0f172a")   # hex-ok (PDF reportlab)
    GRIS = colors.HexColor("#475569")    # hex-ok (PDF reportlab)
    TRAIT = colors.HexColor("#cbd5e1")   # hex-ok (PDF reportlab)
    ZEBRE = colors.HexColor("#f1f5f9")   # hex-ok (PDF reportlab)
    ROUGE = colors.HexColor("#b91c1c")   # hex-ok (PDF reportlab)

    st_titre = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=16, leading=20, spaceAfter=2)
    st_sous = ParagraphStyle("s", fontName="Helvetica", fontSize=9, leading=12, textColor=GRIS)
    st_corps = ParagraphStyle("p", fontName="Helvetica", fontSize=9, leading=12.5)
    st_h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11, leading=14, spaceAfter=3)
    st_cell = ParagraphStyle("c", fontName="Helvetica", fontSize=8, leading=10)
    st_cell_r = ParagraphStyle("cr", fontName="Helvetica", fontSize=8, leading=10, textColor=ROUGE)
    st_head = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=8, leading=10,
                             textColor=colors.white)
    st_pied = ParagraphStyle("f", fontName="Helvetica-Oblique", fontSize=7.5, leading=10,
                             textColor=GRIS)

    def P(txt, style=st_cell):
        return Paragraph(escape(str(txt if txt not in (None, "") else "—")), style)

    flow = [Paragraph(escape(titre), st_titre)]
    sous = " · ".join(x for x in [
        organisation,
        f"licence {licence_sifa}" if licence_sifa else "",
        "FSC-STD-40-004 V3-1, section 2",
        f"édité le {aujourdhui.strftime('%d/%m/%Y')}",
    ] if x)
    flow.append(Paragraph(escape(sous), st_sous))
    flow.append(Spacer(1, 5 * mm))

    # ─── la déclaration proprement dite ───
    periode = ""
    if r["premier_controle"] and r["dernier_controle"]:
        periode = (f" Les contrôles retenus ont été réalisés le {_fr(r['dernier_controle'])}."
                   if r["premier_controle"] == r["dernier_controle"]
                   else f" Les contrôles retenus s'échelonnent du {_fr(r['premier_controle'])}"
                        f" au {_fr(r['dernier_controle'])}.")
    decl = (
        f"{organisation} déclare avoir vérifié sur la base publique FSC "
        f"(search.fsc.org) les certificats des {r['total']} fournisseurs listés ci-dessous."
        f"{periode} Pour chaque fournisseur, le tableau indique la date à laquelle le contrôle "
        f"a été réalisé et le statut affiché par la base ce jour-là ; le relevé horodaté "
        f"correspondant est conservé dans MySifa."
    )
    flow.append(Paragraph(escape(decl), st_corps))
    flow.append(Spacer(1, 2 * mm))
    rappel = (
        "Un certificat valide ne suffit pas à couvrir une livraison : l'entité qui facture "
        f"{organisation} doit être le titulaire du certificat ou l'un de ses sites en cours de "
        "validité, et la portée du certificat doit couvrir le produit acheté. Les écarts relevés "
        "figurent en fin de document ; ils font partie du contrôle."
    )
    flow.append(Paragraph(escape(rappel), st_corps))
    flow.append(Spacer(1, 4 * mm))

    # ─── bandeau de chiffres ───
    cases = [
        ("Fournisseurs", str(r["total"])),
        ("Contrôlés", str(r["controles"])),
        ("Valides sur la base", str(r["valides"])),
        ("Contrôle à refaire", str(r["a_refaire"])),
        ("Jamais contrôlés", str(r["non_controles"])),
        ("Avec constat", str(r["en_ecart"])),
    ]
    st_kpi_l = ParagraphStyle("kl", fontName="Helvetica", fontSize=7.5, leading=9, textColor=GRIS)
    st_kpi_v = ParagraphStyle("kv", fontName="Helvetica-Bold", fontSize=13, leading=16)
    bandeau = Table(
        [[Paragraph(escape(l), st_kpi_l) for l, _ in cases],
         [Paragraph(escape(v), st_kpi_v) for _, v in cases]],
        colWidths=[44.8 * mm] * 6,
    )
    bandeau.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ZEBRE),
        ("BOX", (0, 0), (-1, -1), 0.4, TRAIT),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, TRAIT),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
    ]))
    flow.append(bandeau)
    flow.append(Spacer(1, 6 * mm))

    # ─── le tableau ───
    entetes = ["Fournisseur", "Licence", "Code de certificat", "Contrôlé le",
               "Statut sur la base", "Expiration", "Relevé", "Constat"]
    data = [[P(h, st_head) for h in entetes]]
    for l in lignes:
        ctrl = l.get("dernier_controle") or {}
        cs = constats(l)
        style_c = st_cell_r if cs else st_cell
        data.append([
            P(l.get("nom")),
            P(l.get("licence")),
            P(l.get("certificat")),
            P(_fr(ctrl.get("date_controle")) if ctrl else "—"),
            P(ctrl.get("statut_label") if ctrl else "Non contrôlé"),
            P(_fr(l.get("expiration"))),
            P("Oui" if ctrl.get("justificatif") else "Non"),
            P(" · ".join(cs) if cs else "Conforme", style_c),
        ])
    table = Table(data, repeatRows=1,
                  colWidths=[46 * mm, 24 * mm, 34 * mm, 22 * mm, 24 * mm,
                             22 * mm, 16 * mm, 81 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ENCRE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, TRAIT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRE]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    flow.append(table)
    flow.append(Spacer(1, 6 * mm))

    # ─── écarts ───
    bloc = [Paragraph("Écarts et points de vigilance", st_h2)]
    en_ecart = [(l, constats(l)) for l in lignes if constats(l)]
    if en_ecart:
        for l, cs in en_ecart:
            bloc.append(Paragraph(
                "•&nbsp;&nbsp;<b>%s</b> — %s" % (escape(str(l.get("nom") or "—")),
                                                 escape(" ; ".join(cs))), st_corps))
    else:
        bloc.append(Paragraph(
            escape("Aucun écart relevé au dernier contrôle de chaque fournisseur."), st_corps))
    if validite_jours:
        bloc.append(Spacer(1, 2 * mm))
        bloc.append(Paragraph(escape(
            "Un contrôle est réputé à refaire au-delà de %d jours. Le contrôle complet est "
            "relancé avant chaque audit et à chaque renouvellement ou signalement."
            % validite_jours), st_pied))
    flow.append(KeepTogether(bloc))
    flow.append(Spacer(1, 8 * mm))

    # ─── visa ───
    visa = Table(
        [[P("Établi par", st_head), P("Date", st_head), P("Visa", st_head)],
         [P(responsables or "—"), P(aujourdhui.strftime("%d/%m/%Y")), P(" ")]],
        colWidths=[110 * mm, 40 * mm, 119 * mm], rowHeights=[None, 16 * mm],
    )
    visa.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ENCRE),
        ("GRID", (0, 0), (-1, -1), 0.4, TRAIT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    flow.append(KeepTogether([visa]))

    pied = "Édité depuis MySifa › MyQualité › Certifications SIFA"
    if edite_par:
        pied += " par %s" % edite_par
    pied += " le %s. Source des données : dernier contrôle enregistré pour chaque fournisseur." % \
        aujourdhui.strftime("%d/%m/%Y")
    flow.append(Spacer(1, 3 * mm))
    flow.append(Paragraph(escape(pied), st_pied))

    doc.build(flow)
    return buf.getvalue()
