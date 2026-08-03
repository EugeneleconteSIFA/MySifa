"""Etiquette d'identification carton (100 x 50 mm) d'une fiche produit MyAO.

Reproduit le modele physique colle sur les cartons SIFA :

    +----------------------------------------------------+---+
    | SI  |  1382/0006                                    |   |
    |-----+----------------------------------------------| d |
    | Ref. client   |                                     | a |
    | Matiere       | PP blanc brillant 56u               | t |
    | Adhesif       | Enlevable                           | e |
    | Ref./Format   | 1382/0006  /  140 x 60 mm           |   |
    | Condt.        | Bobine de 12 000 etiquettes         | M |
    | Quantite      | Carton de 1 bobine                  | i |
    +----------------------------------------------------+---+

Meme architecture que `bat_etiquette` : on construit un spec normalise, puis
une liste d'operations de dessin en millimetres, rendue soit en SVG (apercu
inline dans la fiche produit) soit en PDF (page a la taille exacte de
l'etiquette, prete pour l'imprimante d'etiquettes). Les deux sorties
partagent donc rigoureusement la meme geometrie.

Regle de fond : rien n'est invente. Un champ absent de la fiche produit
reste vide sur l'etiquette, exactement comme la ligne "Ref. client" du
modele physique.
"""

from __future__ import annotations

import io
import re
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Geometrie (millimetres) — page = etiquette, aucune marge d'impression
# ---------------------------------------------------------------------------

PAGE_W_MM = 100.0
PAGE_H_MM = 50.0

# Le modele physique n'a NI cadre exterieur NI encadrement de la date : les
# seuls traits sont un filet vertical separant intitules et valeurs, des
# filets horizontaux qui ne courent que sous la colonne des intitules, et un
# unique filet sous le gros numero. Toute ligne supplementaire s'en ecarte.
X_LABEL = 1.8         # bord gauche des intitules et des filets horizontaux
X_RULE = 23.5         # filet vertical intitules / valeurs
X_VALUE = 25.0        # bord gauche des valeurs
X_HDR_RULE_R = 89.0   # extremite droite du filet sous le bandeau
X_VALUE_MAX = 80.0    # au-dela on entre dans la zone des textes pivotes
X_DATE = 83.0         # colonne pivotee : date
X_MADE_IN = 88.0      # colonne pivotee : Made in France

Y_HDR_RULE = 14.0     # filet unique sous le bandeau, droit sur toute la largeur
Y_REF_CLIENT = 21.3   # bas de la ligne "Ref. client", plus haute que les autres
ROW_H = 5.3           # hauteur des 5 lignes suivantes
Y_BASE_SI = 8.3       # ligne de base du "SI"
Y_BASE_REF = 11.5     # ligne de base du gros numero
# Textes pivotes : lecture de bas en haut, donc ancres sur leur extremite basse.
Y_BOT_DATE = 37.0
Y_BOT_MADE_IN = 38.5

# Lignes sous "Ref. client", dans l'ordre d'affichage.
ROWS = ("matiere", "adhesif", "ref_format", "condt", "quantite")

COLOR_INK = "#000000"
COLOR_RULE = "#000000"

RULE_W = 0.3          # epaisseur des filets

FS_HEADER = 6.2       # taille du gros numero (mm)
FS_SI = 3.0
FS_LABEL = 2.4
FS_VALUE = 2.9
FS_STRIP = 2.0
FS_MIN = 1.7          # plancher avant troncature

# Largeur moyenne d'un glyphe Helvetica, en fraction de la taille de fonte.
# Sert uniquement a decider d'une reduction de corps : la mesure exacte est
# faite par reportlab cote PDF, mais le SVG doit rendre le meme texte.
_CHAR_W = 0.52

MADE_IN = "Made in France"
SITE_CODE = "SI"


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def _s(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _f(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _i(value: Any, default: int = 0) -> int:
    try:
        return int(round(_f(value, default)))
    except (TypeError, ValueError):
        return default


def _fmt_dim(value: float) -> str:
    """140.0 -> '140' ; 101.6 -> '101.6' (le modele physique ecrit en point)."""
    rounded = round(float(value), 2)
    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


def _fmt_milliers(n: int) -> str:
    """12000 -> '12 000' — espace simple, compatible Helvetica/WinAnsi."""
    return f"{n:,}".replace(",", " ")


def _plural(n: int, singulier: str, pluriel: Optional[str] = None) -> str:
    return singulier if abs(n) <= 1 else (pluriel or singulier + "s")


def _text_w(text: str, size: float) -> float:
    return len(text) * size * _CHAR_W


def _fit(text: str, max_w: float, size: float) -> tuple:
    """Reduit le corps puis tronque. Retourne (texte, taille)."""
    text = _s(text)
    if not text:
        return "", size
    cur = size
    while cur > FS_MIN and _text_w(text, cur) > max_w:
        cur -= 0.1
    if _text_w(text, cur) <= max_w:
        return text, round(cur, 2)
    max_chars = max(1, int(max_w / (cur * _CHAR_W)) - 1)
    return text[:max_chars].rstrip() + "…", round(cur, 2)


# ---------------------------------------------------------------------------
# Construction du spec depuis une fiche produit MyAO
# ---------------------------------------------------------------------------

def build_etiquette_spec(
    produit: Optional[Dict[str, Any]] = None,
    fiche: Optional[Dict[str, Any]] = None,
    matieres_map: Optional[Dict[Any, Dict[str, Any]]] = None,
    fiche_technique: Optional[Dict[str, Any]] = None,
    *,
    date_edition: str = "",
    site_code: str = SITE_CODE,
) -> Dict[str, Any]:
    """Normalise une fiche produit MyAO en spec d'etiquette carton.

    La fiche technique (Ref SIFA renseignee), quand elle existe, a priorite
    sur la fiche produit pour les champs qu'elle porte de facon structuree —
    meme regle que le BAT, pour que les deux documents ne se contredisent
    jamais.
    """
    produit = produit or {}
    fiche = fiche or {}
    ft = fiche_technique or {}
    mp = matieres_map or {}

    etiquette = fiche.get("etiquette") or {}
    bobines = fiche.get("bobines") or {}
    matiere = fiche.get("matiere") or {}
    cond = fiche.get("conditionnement") or {}
    carton = cond.get("carton") or {}

    def mp_label(mid: Any) -> str:
        """Libelle de sous-categorie en priorite.

        Le carton physique porte la nature de la matiere ("Enlevable",
        "PP blanc brillant 56u"), pas la designation commerciale du rouleau
        ("Adhesif enlevable leger (BOSTIK)"). On retombe sur la designation
        quand la sous-categorie n'est pas renseignee, plutot que de laisser
        la ligne vide.
        """
        row = mp.get(mid) or mp.get(str(mid)) or {}
        for key in ("sous_categorie", "designation", "libelle", "nom"):
            value = _s(row.get(key))
            if value:
                return value
        return ""

    # --- reference affichee -------------------------------------------------
    # Uniquement la reference SIFA (XXX/NNNN) : c'est elle qui figure sur le
    # carton physique. Pas de repli sur la reference MyAO composee — celle-ci
    # decrit le produit ("85 x 55 mm Thermal Eco Permanent, M25 mm") et n'a
    # rien a faire en identifiant de carton. Fiche sans Ref SIFA -> case vide.
    reference = _s(fiche.get("ref_sifa") or produit.get("ref_sifa"))

    # --- format -------------------------------------------------------------
    laize = _f(ft.get("eti_laize")) or _f(etiquette.get("laize"))
    longueur = _f(ft.get("eti_longueur")) or _f(etiquette.get("longueur"))
    format_txt = ""
    if laize > 0 and longueur > 0:
        format_txt = f"{_fmt_dim(laize)} x {_fmt_dim(longueur)} mm"

    ref_format = "  /  ".join(p for p in (reference, format_txt) if p)

    # --- matiere / adhesif --------------------------------------------------
    # La sous-categorie du frontal prime sur le champ "support" de la fiche
    # technique, qui est une saisie libre : ce dernier ne sert que de repli.
    matiere_txt = mp_label(matiere.get("frontal_id")) or _s(ft.get("support"))
    adhesif_txt = mp_label(matiere.get("adhesif_id"))

    # --- conditionnement ----------------------------------------------------
    nb_etiq = _i(ft.get("nb_etiq_bobin")) or _i(bobines.get("nb_etiquettes"))
    condt_txt = ""
    if nb_etiq > 0:
        condt_txt = f"Bobine de {_fmt_milliers(nb_etiq)} étiquettes"

    nb_bob = _i(carton.get("bobines_carton"))
    quantite_txt = ""
    if nb_bob > 0:
        quantite_txt = f"Carton de {nb_bob} {_plural(nb_bob, 'bobine')}"

    return {
        "site_code": _s(site_code) or SITE_CODE,
        "reference": reference,
        "ref_client": _s(fiche.get("ref_client") or produit.get("ref_client")),
        "matiere": matiere_txt,
        "adhesif": adhesif_txt,
        "ref_format": ref_format,
        "condt": condt_txt,
        "quantite": quantite_txt,
        "date": _s(date_edition),
        "made_in": MADE_IN,
        # conserve pour le nom de fichier / diagnostic
        "laize": laize,
        "longueur": longueur,
        "designation": _s(produit.get("designation")),
        "client": _s(produit.get("client_nom")),
    }


# ---------------------------------------------------------------------------
# Operations de dessin
# ---------------------------------------------------------------------------

_ROW_LABELS = {
    "ref_client": "Ref. client",
    "matiere": "Matière",
    "adhesif": "Adhésif",
    "ref_format": "Réf./Format",
    "condt": "Condt.",
    "quantite": "Quantité",
}


def build_etiquette_ops(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Liste d'ops en mm, origine en haut a gauche, partagee SVG / PDF."""
    ops: List[Dict[str, Any]] = []

    def rule(xa, ya, xb, yb):
        ops.append({"op": "line", "x1": xa, "y1": ya, "x2": xb, "y2": yb,
                    "stroke": COLOR_RULE, "sw": RULE_W})

    def text(x, y, s, size, *, bold=False, anchor="start", rot=None):
        op = {"op": "text", "x": x, "y": y, "s": s, "size": size, "anchor": anchor}
        if bold:
            op["bold"] = True
        if rot:
            op["rot"] = rot
        ops.append(op)

    # Fond blanc : le PDF peut etre imprime sur support colore.
    ops.append({"op": "rect", "x": 0, "y": 0, "w": PAGE_W_MM, "h": PAGE_H_MM,
                "fill": "#FFFFFF"})

    y_bottom = Y_REF_CLIENT + len(ROWS) * ROW_H

    # Bandeau : "SI" a gauche, gros numero a droite. Aucun filet vertical ici,
    # les deux blocs sont simplement espaces.
    text((X_LABEL + X_RULE) / 2, Y_BASE_SI, spec.get("site_code") or SITE_CODE,
         FS_SI, bold=True, anchor="middle")

    ref_txt, ref_size = _fit(spec.get("reference") or "",
                             X_HDR_RULE_R - X_VALUE, FS_HEADER)
    if ref_txt:
        text(X_VALUE, Y_BASE_REF, ref_txt, ref_size, bold=True)

    # Filet unique sous le bandeau : une seule droite sur toute la largeur,
    # pas de decrochement entre la colonne "SI" et celle du numero.
    rule(X_LABEL, Y_HDR_RULE, X_HDR_RULE_R, Y_HDR_RULE)

    # Filet vertical : du bas du bandeau jusqu'a la derniere ligne.
    rule(X_RULE, Y_HDR_RULE, X_RULE, y_bottom)

    # "Ref. client" : ligne plus haute que les autres, intitule cale en haut.
    text(X_LABEL + 0.6, Y_HDR_RULE + 3.0, _ROW_LABELS["ref_client"], FS_LABEL)
    ref_cli = _s(spec.get("ref_client"))
    if ref_cli:
        txt, size = _fit(ref_cli, X_VALUE_MAX - X_VALUE, FS_VALUE)
        text(X_VALUE, Y_HDR_RULE + 3.0, txt, size)
    rule(X_LABEL, Y_REF_CLIENT, X_RULE, Y_REF_CLIENT)

    # Lignes suivantes : filet horizontal sous la colonne des intitules
    # uniquement, et aucun filet sous la derniere.
    for idx, key in enumerate(ROWS):
        top = Y_REF_CLIENT + idx * ROW_H
        base = top + ROW_H / 2 + FS_VALUE * 0.34

        text(X_LABEL + 0.6, top + ROW_H / 2 + FS_LABEL * 0.34,
             _ROW_LABELS[key], FS_LABEL)

        value = _s(spec.get(key))
        if value:
            txt, size = _fit(value, X_VALUE_MAX - X_VALUE, FS_VALUE)
            text(X_VALUE, base, txt, size)

        if idx < len(ROWS) - 1:
            rule(X_LABEL, top + ROW_H, X_RULE, top + ROW_H)

    # Date et "Made in France" : deux textes pivotes cote a cote sur le bord
    # droit, lecture de bas en haut (rotation antihoraire), sans filet autour.
    date_txt = _s(spec.get("date"))
    if date_txt:
        text(X_DATE, Y_BOT_DATE, date_txt, FS_STRIP, rot=270)
    made = _s(spec.get("made_in"))
    if made:
        text(X_MADE_IN, Y_BOT_MADE_IN, made, FS_STRIP, rot=270)

    return ops


# ---------------------------------------------------------------------------
# Rendu SVG
# ---------------------------------------------------------------------------

_SVG_FONT = "Helvetica, Arial, sans-serif"


def _esc(text: Any) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _svg_paint(op: Dict[str, Any]) -> str:
    fill = op.get("fill")
    stroke = op.get("stroke")
    out = f' fill="{fill}"' if fill else ' fill="none"'
    if stroke:
        out += f' stroke="{stroke}" stroke-width="{op.get("sw", RULE_W):.3f}"'
    return out


def render_etiquette_svg(spec: Dict[str, Any],
                         ops: Optional[List[Dict[str, Any]]] = None) -> str:
    """SVG autonome, unites mm, injectable tel quel dans la fiche produit."""
    ops = ops if ops is not None else build_etiquette_ops(spec)
    parts: List[str] = []

    for op in ops:
        kind = op["op"]
        if kind == "rect":
            parts.append(
                f'<rect x="{op["x"]:.3f}" y="{op["y"]:.3f}" width="{op["w"]:.3f}"'
                f' height="{op["h"]:.3f}"{_svg_paint(op)}/>'
            )
        elif kind == "line":
            parts.append(
                f'<line x1="{op["x1"]:.3f}" y1="{op["y1"]:.3f}" x2="{op["x2"]:.3f}"'
                f' y2="{op["y2"]:.3f}" stroke="{op.get("stroke", COLOR_RULE)}"'
                f' stroke-width="{op.get("sw", RULE_W):.3f}"/>'
            )
        elif kind == "text":
            transform = ""
            if op.get("rot"):
                transform = f' transform="rotate({op["rot"]} {op["x"]:.3f} {op["y"]:.3f})"'
            weight = ' font-weight="bold"' if op.get("bold") else ""
            parts.append(
                f'<text x="{op["x"]:.3f}" y="{op["y"]:.3f}" font-family="{_SVG_FONT}"'
                f' font-size="{op["size"]:.3f}" fill="{op.get("fill", COLOR_INK)}"'
                f' text-anchor="{op["anchor"]}"{weight}{transform}>{_esc(op["s"])}</text>'
            )

    body = "".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg"'
        f' viewBox="0 0 {PAGE_W_MM:.0f} {PAGE_H_MM:.0f}" width="100%"'
        f' preserveAspectRatio="xMidYMid meet" role="img">{body}</svg>'
    )


# ---------------------------------------------------------------------------
# Rendu PDF — page a la taille exacte de l'etiquette
# ---------------------------------------------------------------------------

# Caracteres que les polices Type1 de base de reportlab n'impriment pas : le
# glyphe est simplement absent du PDF, sans erreur. Le micro n'est pas un cas
# d'ecole ici — toutes les matieres sont libellees "PP blanc brillant 56µ".
# Les substituts choisis sont visuellement equivalents.
_PDF_SUBST = {
    "µ": "μ",  # MICRO SIGN -> GREEK SMALL LETTER MU
    "²": "2",       # exposant 2
    "³": "3",       # exposant 3
}


def _pdf_text(text: Any) -> str:
    s = str(text)
    for bad, good in _PDF_SUBST.items():
        if bad in s:
            s = s.replace(bad, good)
    return s


def render_etiquette_pdf(spec: Dict[str, Any],
                         ops: Optional[List[Dict[str, Any]]] = None) -> bytes:
    """PDF vectoriel 100 x 50 mm, meme geometrie que le SVG."""
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfgen import canvas as rl_canvas

    ops = ops if ops is not None else build_etiquette_ops(spec)
    buffer = io.BytesIO()
    c = rl_canvas.Canvas(buffer, pagesize=(PAGE_W_MM * mm, PAGE_H_MM * mm))
    c.setTitle(f"Etiquette {spec.get('reference') or ''}".strip())

    def X(v: float) -> float:
        return v * mm

    def Y(v: float) -> float:
        return (PAGE_H_MM - v) * mm

    for op in ops:
        kind = op["op"]

        if kind == "rect":
            c.saveState()
            fill = op.get("fill")
            stroke = op.get("stroke")
            if fill:
                c.setFillColor(HexColor(fill))
            if stroke:
                c.setStrokeColor(HexColor(stroke))
                c.setLineWidth(op.get("sw", RULE_W) * mm)
            c.rect(X(op["x"]), Y(op["y"] + op["h"]), op["w"] * mm, op["h"] * mm,
                   stroke=1 if stroke else 0, fill=1 if fill else 0)
            c.restoreState()

        elif kind == "line":
            c.saveState()
            c.setStrokeColor(HexColor(op.get("stroke", COLOR_RULE)))
            c.setLineWidth(op.get("sw", RULE_W) * mm)
            c.line(X(op["x1"]), Y(op["y1"]), X(op["x2"]), Y(op["y2"]))
            c.restoreState()

        elif kind == "text":
            c.saveState()
            name = "Helvetica-Bold" if op.get("bold") else "Helvetica"
            size_pt = op["size"] * mm
            text = _pdf_text(op["s"])
            c.setFont(name, size_pt)
            c.setFillColor(HexColor(op.get("fill", COLOR_INK)))
            width = pdfmetrics.stringWidth(text, name, size_pt)
            dx = {"start": 0.0, "middle": -width / 2, "end": -width}[op["anchor"]]
            c.translate(X(op["x"]), Y(op["y"]))
            if op.get("rot"):
                c.rotate(-op["rot"])  # SVG horaire -> reportlab antihoraire
            c.drawString(dx, 0, text)
            c.restoreState()

    c.showPage()
    c.save()
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Nom de fichier
# ---------------------------------------------------------------------------

def etiquette_filename(spec: Dict[str, Any]) -> str:
    base = _s(spec.get("reference")) or "produit"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-") or "produit"
    return f"Etiquette_{safe}.pdf"
