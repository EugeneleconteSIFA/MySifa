"""Fiches techniques matières et produits (BOM) — données et PDF.

Une fiche matière décrit un composant (frontal, adhésif, dorsal…). Une fiche
produit assemble les fiches de ses composants dans l'ordre de la composition
et n'ajoute que ce qui lui est propre (applications, impression, durée de vie,
performances mesurées sur le complexe). Aucun prix n'y figure : c'est un
document qui part chez le client.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from io import BytesIO
from typing import Any, Optional
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

from config import APP_ORG_NAME

_PARIS = ZoneInfo("Europe/Paris")

# Champs saisissables. (clé, libellé, unité, multiligne)
CHAMPS_MATIERE: list[tuple[str, str, str, bool]] = [
    ("nom_commercial", "Nom commercial", "", False),
    ("description", "Description", "", True),
    ("epaisseur_um", "Épaisseur", "µm", False),
    ("grammage_gsm", "Poids de base", "g/m²", False),
    ("couleur", "Couleur", "", False),
    ("type_adhesif", "Type d'adhésif", "", False),
    ("temp_application", "Température d'application", "", False),
    ("temp_tenue", "Température de tenue", "", False),
    ("pouvoir_adhesif", "Pouvoir adhésif (pelage)", "", False),
    ("tack", "Tack en boucle", "", False),
    ("notes", "Informations complémentaires", "", True),
]

CHAMPS_PRODUIT: list[tuple[str, str, str, bool]] = [
    ("nom_commercial", "Nom commercial", "", False),
    ("sous_titre", "Sous-titre", "", False),
    ("description", "Description générale", "", True),
    ("epaisseur_totale_um", "Épaisseur totale du produit", "µm", False),
    ("pouvoir_adhesif", "Pouvoir adhésif (pelage)", "", False),
    ("tack", "Tack en boucle", "", False),
    ("temp_application", "Température d'application", "", False),
    ("temp_tenue", "Température de tenue", "", False),
    ("applications", "Applications et utilités", "", True),
    ("impression", "Impression et conversion", "", True),
    ("duree_vie", "Durée de vie", "", True),
    ("notes", "Information supplémentaire", "", True),
]

# Libellé de section par rôle de composant. « Dorsal » est le terme client
# pour la glassine (le support siliconé).
_ROLE_SECTION = {
    "FRONTAL": "Frontal",
    "ADHESIF": "Adhésif",
    "GLASSINE": "Dorsal",
    "AUTRE": "Autre composant",
}

# Caractéristiques reprises dans le tableau d'une section de composant.
_CARACS_COMPOSANT = [
    ("epaisseur_um", "Épaisseur", "µ (microns)"),
    ("grammage_gsm", "Poids de base", "g/m²"),
    ("couleur", "Couleur", ""),
    ("type_adhesif", "Type", ""),
    ("temp_application", "Température d'application", ""),
    ("temp_tenue", "Température de tenue", ""),
]


def champs_def(objet: str) -> list[dict]:
    src = CHAMPS_PRODUIT if objet == "produit" else CHAMPS_MATIERE
    return [{"cle": k, "label": l, "unite": u, "multi": m} for k, l, u, m in src]


def _cles(objet: str) -> set[str]:
    return {c[0] for c in (CHAMPS_PRODUIT if objet == "produit" else CHAMPS_MATIERE)}


def lire(conn: sqlite3.Connection, objet: str, objet_id: int) -> dict:
    row = conn.execute(
        "SELECT data, updated_at, updated_by_name FROM mp_fiche_technique WHERE objet=? AND objet_id=?",
        (objet, objet_id),
    ).fetchone()
    if not row:
        return {"data": {}, "updated_at": None, "updated_by_name": None}
    try:
        data = json.loads(row["data"] or "{}")
    except ValueError:
        data = {}
    return {"data": data, "updated_at": row["updated_at"], "updated_by_name": row["updated_by_name"]}


def ecrire(conn: sqlite3.Connection, objet: str, objet_id: int, data: dict, par: str) -> dict:
    cles = _cles(objet)
    propre = {}
    for k, v in (data or {}).items():
        if k not in cles or v is None:
            continue
        s = str(v).strip()
        if s:
            propre[k] = s[:4000]
    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    conn.execute(
        """INSERT INTO mp_fiche_technique (objet, objet_id, data, updated_at, updated_by_name)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(objet, objet_id) DO UPDATE SET
             data=excluded.data, updated_at=excluded.updated_at,
             updated_by_name=excluded.updated_by_name""",
        (objet, objet_id, json.dumps(propre, ensure_ascii=False), now, par),
    )
    conn.commit()
    return lire(conn, objet, objet_id)


def matiere(conn: sqlite3.Connection, matiere_id: int) -> Optional[dict]:
    row = conn.execute(
        "SELECT id, reference, designation, categorie, sous_section, couleur, weight_gsm "
        "FROM matieres_premieres WHERE id=?",
        (matiere_id,),
    ).fetchone()
    if not row:
        return None
    m = dict(row)
    fiche = lire(conn, "matiere", matiere_id)
    m["fiche"] = fiche
    return m


def _defauts_matiere(m: dict) -> dict:
    """Ce que la base sait déjà, pour qu'une fiche jamais saisie ne soit pas vide."""
    d: dict[str, str] = {}
    if m.get("couleur"):
        d["couleur"] = str(m["couleur"])
    if m.get("weight_gsm"):
        try:
            d["grammage_gsm"] = f"{float(m['weight_gsm']):g}"
        except (TypeError, ValueError):
            pass
    return d


def donnees_matiere(m: dict) -> dict:
    return {**_defauts_matiere(m), **(m.get("fiche") or {}).get("data", {})}


def produit(conn: sqlite3.Connection, produit_id: int) -> Optional[dict]:
    row = conn.execute("SELECT id, code, designation FROM mp_produit WHERE id=?", (produit_id,)).fetchone()
    if not row:
        return None
    p = dict(row)
    comps = conn.execute(
        """SELECT c.role, c.ordre, c.grammage_gsm, d.matiere_id
             FROM mp_produit_composant c
             JOIN mp_matiere_declinaison d ON d.id = c.declinaison_id
            WHERE c.produit_id=? ORDER BY c.ordre, c.id""",
        (produit_id,),
    ).fetchall()
    composants = []
    for c in comps:
        m = matiere(conn, int(c["matiere_id"]))
        if not m:
            continue
        data = donnees_matiere(m)
        # Le grammage d'adhésif est porté par la composition, pas par la matière.
        if c["grammage_gsm"] and not (m["fiche"]["data"] or {}).get("grammage_gsm"):
            data["grammage_gsm"] = f"{float(c['grammage_gsm']):g}"
        composants.append({"role": c["role"], "matiere": m, "data": data})
    p["composants"] = composants
    p["fiche"] = lire(conn, "produit", produit_id)
    return p


def donnees_produit(p: dict) -> dict:
    """Fiche produit complétée par celles des composants quand elle se tait."""
    d = dict(p["fiche"]["data"])
    adh = next((c["data"] for c in p["composants"] if c["role"] == "ADHESIF"), {})
    for k in ("pouvoir_adhesif", "tack", "temp_application", "temp_tenue"):
        if not d.get(k) and adh.get(k):
            d[k] = adh[k]
    if not d.get("epaisseur_totale_um"):
        total, complet = 0.0, bool(p["composants"])
        for c in p["composants"]:
            try:
                total += float(str(c["data"].get("epaisseur_um", "")).replace(",", "."))
            except ValueError:
                complet = False
        if complet and total > 0:
            d["epaisseur_totale_um"] = f"{total:g}"
    return d


# ─── PDF ──────────────────────────────────────────────────────────

_ENCRE = colors.HexColor("#0f172a")
_DOUX = colors.HexColor("#475569")
_TRAIT = colors.HexColor("#cbd5e1")
_FOND = colors.HexColor("#f1f5f9")


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "org": ParagraphStyle("ftOrg", parent=base["Normal"], fontSize=9, textColor=_DOUX),
        "titre": ParagraphStyle("ftTitre", parent=base["Heading1"], fontSize=18, textColor=_ENCRE, spaceAfter=2),
        "sous": ParagraphStyle("ftSous", parent=base["Normal"], fontSize=11, textColor=_DOUX, spaceAfter=6),
        "h": ParagraphStyle("ftH", parent=base["Heading3"], fontSize=11, textColor=_ENCRE,
                            spaceBefore=8, spaceAfter=4),
        "nom": ParagraphStyle("ftNom", parent=base["Normal"], fontSize=10, fontName="Helvetica-Bold",
                              textColor=_ENCRE, spaceAfter=2),
        "txt": ParagraphStyle("ftTxt", parent=base["Normal"], fontSize=9, leading=12, textColor=_ENCRE),
        "pied": ParagraphStyle("ftPied", parent=base["Normal"], fontSize=7.5, textColor=_DOUX),
    }


def _p(txt: str, st) -> Paragraph:
    return Paragraph(escape(str(txt)).replace("\n", "<br/>"), st)


def _valeur(v: str, unite: str) -> str:
    return f"{v} {unite}".strip() if unite and v and not any(ch.isalpha() for ch in v) else v


def _tableau(lignes: list[tuple[str, str]], st) -> Table:
    t = Table([[_p(a, st["txt"]), _p(b, st["txt"])] for a, b in lignes], colWidths=[62 * mm, 110 * mm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, _TRAIT),
        ("BACKGROUND", (0, 0), (0, -1), _FOND),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _section_composant(titre: str, nom: str, data: dict, st) -> list:
    bloc: list[Any] = [_p(titre, st["h"])]
    nom = data.get("nom_commercial") or nom
    if nom:
        bloc.append(_p(nom, st["nom"]))
    if data.get("description"):
        bloc.append(_p(data["description"], st["txt"]))
        bloc.append(Spacer(1, 4))
    lignes = [(lab, _valeur(data[k], u)) for k, lab, u in _CARACS_COMPOSANT if data.get(k)]
    if lignes:
        bloc.append(_tableau(lignes, st))
    if data.get("notes"):
        bloc.append(Spacer(1, 3))
        bloc.append(_p(data["notes"], st["txt"]))
    return [KeepTogether(bloc)]


def _document(titre: str, sous_titre: str, corps: list, reference: str) -> bytes:
    st = _styles()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=18 * mm, title=f"Fiche technique {titre}",
        author=APP_ORG_NAME,
    )
    date = datetime.now(_PARIS).strftime("%d/%m/%Y")

    def pied(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(_DOUX)
        canvas.drawString(18 * mm, 10 * mm, f"{APP_ORG_NAME} · Fiche technique {reference} · édition du {date}")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    story: list[Any] = [
        _p(f"{APP_ORG_NAME} · Fiche technique", st["org"]),
        _p(titre, st["titre"]),
    ]
    if sous_titre:
        story.append(_p(sous_titre, st["sous"]))
    story.append(Spacer(1, 4))
    story.extend(corps)
    story.append(Spacer(1, 12))
    story.append(_p(
        "Les valeurs indiquées sont des valeurs typiques, fournies à titre indicatif. "
        "Il appartient à l'utilisateur de vérifier l'adéquation du produit à son application.",
        st["pied"],
    ))
    doc.build(story, onFirstPage=pied, onLaterPages=pied)
    return buf.getvalue()


def pdf_matiere(m: dict) -> bytes:
    st = _styles()
    data = donnees_matiere(m)
    role = (m.get("categorie") or "").strip().lower()
    titre_section = {"frontal": "Frontal", "adhesif": "Adhésif", "adhésif": "Adhésif",
                     "glassine": "Dorsal"}.get(role, m.get("categorie") or "Caractéristiques")
    corps = _section_composant(titre_section, m.get("designation") or "", data, st)
    perf = [(lab, data[k]) for k, lab in (("pouvoir_adhesif", "Pouvoir adhésif (pelage)"), ("tack", "Tack en boucle"))
            if data.get(k)]
    if perf:
        corps += [_p("Performance technique", st["h"]), _tableau(perf, st)]
    titre = data.get("nom_commercial") or m.get("designation") or m.get("reference") or ""
    return _document(titre, m.get("reference") or "", corps, m.get("reference") or "")


def pdf_produit(p: dict) -> bytes:
    st = _styles()
    d = donnees_produit(p)
    corps: list[Any] = []
    if d.get("description"):
        corps += [_p(d["description"], st["txt"]), Spacer(1, 4)]
    for c in p["composants"]:
        corps += _section_composant(
            _ROLE_SECTION.get(c["role"], "Composant"),
            c["matiere"].get("designation") or c["matiere"].get("reference") or "",
            c["data"], st,
        )
    if not p["composants"]:
        corps.append(_p("Aucun composant renseigné.", st["txt"]))

    perf = [
        (lab, _valeur(d[k], u))
        for k, lab, u in (
            ("epaisseur_totale_um", "Épaisseur totale du produit", "µ (microns)"),
            ("pouvoir_adhesif", "Pouvoir adhésif (pelage)", ""),
            ("tack", "Tack en boucle", ""),
            ("temp_application", "Température d'application", ""),
            ("temp_tenue", "Température de tenue", ""),
        )
        if d.get(k)
    ]
    if perf:
        corps.append(KeepTogether([_p("Performance technique", st["h"]), _tableau(perf, st)]))
    for k, lab in (("applications", "Applications et utilités"), ("impression", "Impression et conversion"),
                   ("duree_vie", "Durée de vie"), ("notes", "Information supplémentaire")):
        if d.get(k):
            corps.append(KeepTogether([_p(lab, st["h"]), _p(d[k], st["txt"])]))

    titre = d.get("nom_commercial") or p.get("designation") or p.get("code") or ""
    sous = d.get("sous_titre") or (p.get("code") or "")
    return _document(titre, sous, corps, p.get("code") or "")
