"""
Étiquettes spécifiques — pictogrammes réglementaires.

Une seule définition, en primitives simples sur une grille de 24 × 24 :
  - l'éditeur les dessine en SVG inline (servies par /bootstrap) ;
  - le ZPL les pose en image monochrome (^GFA), tramée ici avec Pillow ;
  - le PDF les trace avec reportlab.

Primitives (coordonnées de la grille 24) :
  {"t": "ligne", "p": [[x, y], ...], "e": épaisseur}     polyligne
  {"t": "poly",  "p": [[x, y], ...]}                     polygone plein
  {"t": "cercle", "c": [x, y], "r": r, "e": épaisseur}   cercle (e = 0 → plein)
  {"t": "texte", "x", "y", "s": corps, "v": "FSC"}       texte centré sur x, ligne de base y

Pictogrammes de manutention : dessins d'après l'ISO 780 (haut, fragile, au
sec). Le logo FSC n'est pas reproduit : c'est une marque, son usage passe par
l'outil de marquage FSC. L'objet « FSC » pose un repère d'emplacement (arbre
générique + sigle) et le numéro de licence lu dans config.py (FSC_LICENCE_SIFA,
le même que MyQualité) — à remplacer par l'illustration officielle validée.
"""

from __future__ import annotations

import math


def _fleche(x1, y1, x2, y2, e=1.6, tete=3.2):
    """Ligne terminée par une pointe pleine."""
    ang = math.atan2(y2 - y1, x2 - x1)
    bx, by = x2 - tete * math.cos(ang), y2 - tete * math.sin(ang)
    px, py = -math.sin(ang) * tete * 0.6, math.cos(ang) * tete * 0.6
    return [
        {"t": "ligne", "p": [[x1, y1], [bx, by]], "e": e},
        {"t": "poly", "p": [[round(x2, 2), round(y2, 2)], [round(bx + px, 2), round(by + py, 2)],
                            [round(bx - px, 2), round(by - py, 2)]]},
    ]


def _arc(cx, cy, r, de, a, n=18):
    return [[round(cx + r * math.cos(math.radians(de + (a - de) * i / n)), 2),
             round(cy + r * math.sin(math.radians(de + (a - de) * i / n)), 2)] for i in range(n + 1)]


def _recyclage():
    out = []
    for x1, y1, x2, y2 in ((13.4, 5.2, 19.6, 15.8), (17.8, 19.2, 6.4, 19.2), (4.4, 16.2, 10.4, 5.6)):
        out += _fleche(x1, y1, x2, y2)
    return out


def _fsc():
    return [
        {"t": "poly", "p": [[12, 1.5], [17.5, 8], [14.5, 8], [19, 13], [5, 13], [9.5, 8], [6.5, 8]]},
        {"t": "ligne", "p": [[12, 13], [12, 16]], "e": 2},
        {"t": "texte", "x": 12, "y": 22.5, "s": 6, "v": "FSC"},
    ]


def _deroulage():
    return [
        {"t": "cercle", "c": [8, 10], "r": 6.5, "e": 1.5},
        {"t": "cercle", "c": [8, 10], "r": 2, "e": 1.2},
        {"t": "ligne", "p": [[8, 16.5], [16, 16.5]], "e": 1.5},
        {"t": "ligne", "p": [[10.5, 18.5], [13.5, 18.5]], "e": 1},
    ] + _fleche(15, 16.5, 23, 16.5, e=1.5, tete=3)


def _fragile():
    return [
        {"t": "poly", "p": [[6.5, 2.5], [17.5, 2.5], [17, 7.5], [15, 10.5], [12, 11.5], [9, 10.5], [7, 7.5]]},
        {"t": "ligne", "p": [[12, 11.5], [12, 19.5]], "e": 1.6},
        {"t": "ligne", "p": [[7.5, 20.5], [16.5, 20.5]], "e": 1.8},
    ]


def _haut():
    return (_fleche(8, 18.5, 8, 3) + _fleche(16, 18.5, 16, 3)
            + [{"t": "ligne", "p": [[3.5, 21.2], [20.5, 21.2]], "e": 1.8}])


def _humidite():
    canope = _arc(12, 10.5, 8.5, 180, 360, 20)
    return [
        {"t": "poly", "p": canope},
        {"t": "ligne", "p": [[12, 10.5], [12, 19.5]], "e": 1.4},
        {"t": "ligne", "p": _arc(13.8, 19.5, 1.8, 180, 0, 8), "e": 1.4},
        {"t": "ligne", "p": [[5, 0.6], [4.4, 2.4]], "e": 1.1},
        {"t": "ligne", "p": [[12, 0.2], [11.4, 1.6]], "e": 1.1},
        {"t": "ligne", "p": [[19, 0.6], [18.4, 2.4]], "e": 1.1},
    ]


# clé → (libellé, primitives, légende proposée sous le dessin)
PICTOS = {
    "recyclage": ("Recyclable", _recyclage(), ""),
    "fsc": ("FSC (emplacement + licence)", _fsc(), "{{fsc_licence}}"),
    "deroulage": ("Sens de déroulage", _deroulage(), ""),
    "fragile": ("Fragile", _fragile(), ""),
    "haut": ("Haut / bas", _haut(), ""),
    "humidite": ("Protéger de l'humidité", _humidite(), ""),
}


def referentiel() -> dict:
    return {k: {"libelle": l, "primitives": p, "legende": g} for k, (l, p, g) in PICTOS.items()}


# ─── Trame monochrome pour le ZPL ──────────────────────────────────────

def trame(nom: str, largeur: int, hauteur: int):
    """Image Pillow mode « 1 » du pictogramme (noir = 0), ou None."""
    if nom not in PICTOS or largeur < 4 or hauteur < 4:
        return None
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("L", (largeur, hauteur), 255)
    dr = ImageDraw.Draw(img)
    k = min(largeur, hauteur) / 24.0
    ox, oy = (largeur - 24 * k) / 2, (hauteur - 24 * k) / 2

    def pt(p):
        return (ox + p[0] * k, oy + p[1] * k)

    for prim in PICTOS[nom][1]:
        t = prim["t"]
        if t == "ligne":
            dr.line([pt(p) for p in prim["p"]], fill=0, width=max(1, int(round(prim.get("e", 1) * k))), joint="curve")
        elif t == "poly":
            dr.polygon([pt(p) for p in prim["p"]], fill=0)
        elif t == "cercle":
            cx, cy = pt(prim["c"])
            r = prim["r"] * k
            box = [cx - r, cy - r, cx + r, cy + r]
            if prim.get("e"):
                dr.ellipse(box, outline=0, width=max(1, int(round(prim["e"] * k))))
            else:
                dr.ellipse(box, fill=0)
        elif t == "texte":
            corps = max(6, int(prim["s"] * k))
            try:
                police = ImageFont.load_default(size=corps)
            except TypeError:  # Pillow < 10.1 : police bitmap fixe
                police = ImageFont.load_default()
            x, y = pt([prim["x"], prim["y"]])
            dr.text((x, y), prim["v"], fill=0, font=police, anchor="ms")
    return img.convert("1", dither=Image.Dither.NONE) if hasattr(Image, "Dither") else img.convert("1")


def zpl_gfa(nom: str, largeur: int, hauteur: int) -> str:
    """« ^GFA,… » du pictogramme à la taille en points, ou "" s'il est inconnu."""
    img = trame(nom, largeur, hauteur)
    return gfa_depuis_image(img) if img is not None else ""


def gfa_depuis_image(img) -> str:
    """Image Pillow (mode 1 ou L : noir = 0) → « ^GFA,… »."""
    if img.mode != "1":
        img = img.convert("L").point(lambda p: 255 if p >= 128 else 0).convert("1")
    largeur = img.size[0]
    octets_ligne = (largeur + 7) // 8
    brut = img.tobytes()   # mode 1 : 1 = blanc, rangées complétées à l'octet
    noir = bytes(b ^ 0xFF for b in brut)
    # Les bits de remplissage en fin de rangée doivent rester blancs (0).
    reste = largeur % 8
    if reste:
        masque = (0xFF << (8 - reste)) & 0xFF
        noir = bytes(b & masque if (i + 1) % octets_ligne == 0 else b for i, b in enumerate(noir))
    total = len(noir)
    return f"^GFA,{total},{total},{octets_ligne},{noir.hex().upper()}"


# ─── Tracé PDF (reportlab) ─────────────────────────────────────────────

def dessiner_pdf(c, nom: str, x: float, y_haut: float, largeur: float, hauteur: float) -> None:
    """Trace le pictogramme dans la boîte (points PDF, y_haut = bord haut)."""
    if nom not in PICTOS:
        return
    k = min(largeur, hauteur) / 24.0
    ox = x + (largeur - 24 * k) / 2
    oy = y_haut - (hauteur - 24 * k) / 2

    def pt(p):
        return ox + p[0] * k, oy - p[1] * k

    c.saveState()
    c.setLineCap(1)
    c.setLineJoin(1)
    for prim in PICTOS[nom][1]:
        t = prim["t"]
        if t == "ligne":
            c.setLineWidth(prim.get("e", 1) * k)
            p = c.beginPath()
            p.moveTo(*pt(prim["p"][0]))
            for q in prim["p"][1:]:
                p.lineTo(*pt(q))
            c.drawPath(p, stroke=1, fill=0)
        elif t == "poly":
            p = c.beginPath()
            p.moveTo(*pt(prim["p"][0]))
            for q in prim["p"][1:]:
                p.lineTo(*pt(q))
            p.close()
            c.drawPath(p, stroke=0, fill=1)
        elif t == "cercle":
            cx, cy = pt(prim["c"])
            if prim.get("e"):
                c.setLineWidth(prim["e"] * k)
                c.circle(cx, cy, prim["r"] * k, stroke=1, fill=0)
            else:
                c.circle(cx, cy, prim["r"] * k, stroke=0, fill=1)
        elif t == "texte":
            c.setFont("Helvetica-Bold", prim["s"] * k * 1.2)
            c.drawCentredString(*pt([prim["x"], prim["y"]]), prim["v"])
    c.restoreState()


def gfa_image_src(src: str, largeur: int, hauteur: int, seuil: int = 128, inverse: bool = False) -> str:
    """Logo (data URL) tramé au seuil, à la taille en points."""
    import base64
    import io
    from PIL import Image
    try:
        brut = base64.b64decode(src.split(",", 1)[1])
        img = Image.open(io.BytesIO(brut))
        img.load()
    except Exception:
        return ""
    fond = Image.new("RGBA", img.size, (255, 255, 255, 255))
    img = Image.alpha_composite(fond, img.convert("RGBA")).convert("L").resize((largeur, hauteur))
    img = img.point(lambda p: (255 if p < seuil else 0) if inverse else (0 if p < seuil else 255))
    return gfa_depuis_image(img)


def _police(px: int):
    from PIL import ImageFont
    for nom in ("DejaVuSansCondensed-Bold.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(nom, px)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=px)
    except TypeError:
        return ImageFont.load_default()


def image_texte(e: dict, texte: str, dpi: int):
    """Texte en arc ou en miroir, dessiné en image (l'imprimante ne sait ni
    courber ni retourner un champ texte)."""
    from PIL import Image, ImageDraw, ImageOps
    k = dpi / 25.4
    px = max(8, int(e.get("taille", 3.5) * k))
    police = _police(px)
    arc = e.get("arc")
    if arc:
        r = arc["rayon_mm"] * k
        cote = int(2 * (r + px)) + 4
        img = Image.new("L", (cote, cote), 255)
        cx = cy = cote / 2
        lettres = list(texte)
        if not lettres:
            return img
        larg = [police.getlength(c) for c in lettres]
        total = sum(larg)
        angle_total = total / max(1.0, r)        # radians
        bas = arc.get("sens") == "bas"
        a = (-math.pi / 2 - angle_total / 2) if not bas else (math.pi / 2 + angle_total / 2)
        for c, w in zip(lettres, larg):
            da = w / max(1.0, r)
            mid = a + (da / 2 if not bas else -da / 2)
            tuile = Image.new("L", (int(w) + 4, px + 4), 255)
            ImageDraw.Draw(tuile).text((2, 2), c, font=police, fill=0)
            deg = math.degrees(mid) + (90 if not bas else -90)
            tuile = tuile.rotate(-deg, expand=True, fillcolor=255)
            x = cx + r * math.cos(mid) - tuile.size[0] / 2
            y = cy + r * math.sin(mid) - tuile.size[1] / 2
            img.paste(tuile, (int(x), int(y)), ImageOps.invert(tuile))
            a += da if not bas else -da
    else:
        w = int(police.getlength(texte)) + 4
        img = Image.new("L", (max(4, w), px + 6), 255)
        ImageDraw.Draw(img).text((2, 2), texte, font=police, fill=0)
    if e.get("miroir"):
        img = ImageOps.mirror(img)
    if e.get("inverse"):
        img = ImageOps.invert(img)
    return img


def gfa_texte(e: dict, texte: str, dpi: int) -> str:
    if not texte:
        return ""
    return gfa_depuis_image(image_texte(e, texte, dpi))
