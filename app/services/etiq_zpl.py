"""
MyTools › Étiquettes — chaîne d'impression : du modèle vectoriel au flux
imprimante (ZPL, EPL, TSPL, PDF), aperçu raster interne, envoi réseau.

Le modèle est celui des étiquettes spécifiques (app/services/etiq_specifiques.py),
positions en mm depuis le coin haut gauche :

    modele = {"largeur_mm", "hauteur_mm", "dpi"?,
              "layout": {"elements": [...], "variables": [...]}}
    (les clés "elements" / "variables" sont aussi acceptées à la racine)

Éléments lus (champs absents = défaut ; un type inconnu est ignoré) :
    texte       valeur, taille (hauteur de cellule, mm), gras, largeur (mm, bloc
                multiligne), lignes, align (gauche|centre|droite), rotation
                (0|90|180|270), inverse, police ("" ou "0" = police interne de
                l'imprimante ; tout autre nom = rendue en image), ajuster
                (réduit la taille pour tenir dans la largeur sur une ligne)
    code_barre  symbologie (code128, gs1_128, ean13, ean8, upca, code39, itf14,
                qrcode, datamatrix, gs1_datamatrix, pdf417), valeur, hauteur
                (mm), module (mm), lisible, rotation, correction (QR : L|M|Q|H),
                securite (PDF417 : 0-8), colonnes (PDF417)
    cadre       largeur, hauteur, epaisseur, arrondi (0-8), plein
    ellipse     largeur, hauteur, epaisseur, plein
    ligne       orientation (h|v), longueur, epaisseur
    image       src (data:image/png;base64,…), largeur, hauteur (mm), seuil
                (0-255), tramage (seuil|diffusion), inverse

Profil d'imprimante (ligne de la table `imprimantes`) :
    langage (zpl|epl|tspl|pdf), dpi (203|300|600), largeur_mm, hauteur_mm
    (étiquette chargée, défaut du modèle), decalage_x_mm, decalage_y_mm,
    vitesse (pouces/s), contraste (ZPL 0-30, EPL/TSPL 0-15), ecart_mm (EPL/TSPL)

Module PUR : aucune base, aucun réseau, aucune horloge hors des variables
« date ». L'envoi à l'imprimante vit dans etiq_envoi.py. Testé par
tests/test_etiq_zpl.py.

L'aperçu (`apercu_png`) est dessiné ici, avec Pillow et les encodeurs de
reportlab : aucune donnée ne part vers un service extérieur (Labelary ou autre).
La police interne Zebra y est approchée par une Vera Bold condensée ; les codes
1D et le QR sont exacts ; la DataMatrix y est un symbole 44×44 approché ; le
PDF417 y est un cadre hachuré (l'imprimante dessine le vrai).
"""

from __future__ import annotations

import base64
import io
import os
import re
from datetime import datetime, timedelta
from typing import Any, Iterable, Optional

LANGAGES = ("zpl", "epl", "tspl", "pdf")
DPI_ADMIS = (203, 300, 600)
EXTENSIONS = {"zpl": "zpl", "epl": "epl", "tspl": "prn", "pdf": "pdf"}
MIMES = {"zpl": "application/x-zpl", "epl": "application/x-epl", "tspl": "application/octet-stream",
         "pdf": "application/pdf"}
SYMBOLOGIES = ("code128", "gs1_128", "ean13", "ean8", "upca", "code39", "itf14",
               "qrcode", "datamatrix", "gs1_datamatrix", "pdf417")
SYMBOLOGIES_2D = ("qrcode", "datamatrix", "gs1_datamatrix", "pdf417")
FORMAT_MAX_MM = 400
ENREGISTREMENTS_MAX = 5000
COPIES_MAX = 999
_ROT_ZPL = {0: "N", 90: "R", 180: "I", 270: "B"}
_ROT_EPL = {0: 0, 90: 1, 180: 2, 270: 3}
_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
# AI GS1 de longueur fixe (deux premiers chiffres) : pas de FNC1 après eux.
_AI_FIXES = {"00", "01", "02", "03", "04", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20",
             "31", "32", "33", "34", "35", "36", "41"}
_AI_RE = re.compile(r"\((\d{2,4})\)([^(]*)")
_GS1_NET = re.compile(r"[\s^~]")


class ImpressionImpossible(ValueError):
    """Message factuel, affiché tel quel à l'opérateur."""


# ─── Lecture tolérante ──────────────────────────────────────────────────

def _f(v, defaut: float, mini: float = -1e9, maxi: float = 1e9) -> float:
    try:
        x = float(str(v).replace(",", ".")) if v is not None and v != "" else defaut
    except (TypeError, ValueError):
        return defaut
    if x != x:
        return defaut
    return max(mini, min(maxi, x))


def _i(v, defaut: int, mini: int = -10**9, maxi: int = 10**9) -> int:
    return int(round(_f(v, defaut, mini, maxi)))


def dots(mm: float, dpi: int) -> int:
    """mm → points imprimante, arrondi au plus proche."""
    return int(round(float(mm) * int(dpi) / 25.4))


def normaliser_profil(p: Optional[dict], modele: Optional[dict] = None) -> dict:
    p = dict(p or {})
    modele = modele or {}
    langage = str(p.get("langage") or "zpl").lower()
    if langage not in LANGAGES:
        langage = "zpl"
    dpi = _i(p.get("dpi") or modele.get("dpi"), 203)
    if dpi not in DPI_ADMIS:
        dpi = min(DPI_ADMIS, key=lambda d: abs(d - dpi))
    vit = p.get("vitesse")
    con = p.get("contraste")
    return {
        "langage": langage,
        "dpi": dpi,
        "largeur_mm": _f(modele.get("largeur_mm") or p.get("largeur_mm"), 100, 5, FORMAT_MAX_MM),
        "hauteur_mm": _f(modele.get("hauteur_mm") or p.get("hauteur_mm"), 50, 5, FORMAT_MAX_MM),
        "decalage_x_mm": _f(p.get("decalage_x_mm"), 0, -50, 50),
        "decalage_y_mm": _f(p.get("decalage_y_mm"), 0, -50, 50),
        "vitesse": None if vit in (None, "") else _i(vit, 4, 1, 14),
        "contraste": None if con in (None, "") else _i(con, 15, 0, 30),
        "ecart_mm": _f(p.get("ecart_mm"), 2, 0, 20),
        "rfid": bool(p.get("rfid")) and langage == "zpl",
        "gs1_longueur_prefixe": _i(p.get("gs1_longueur_prefixe"), 7, 6, 12),
    }


def layout_de(modele: dict) -> dict:
    lay = modele.get("layout") if isinstance(modele.get("layout"), dict) else modele
    return {"elements": [e for e in (lay.get("elements") or []) if isinstance(e, dict)],
            "variables": [v for v in (lay.get("variables") or []) if isinstance(v, dict)]}


# ─── Valeurs ────────────────────────────────────────────────────────────

def substituer(texte: Any, valeurs: dict) -> str:
    return _PLACEHOLDER_RE.sub(lambda m: str(valeurs.get(m.group(1).lower(), valeurs.get(m.group(1), ""))),
                               "" if texte is None else str(texte))


def valeurs_enregistrement(layout: dict, enregistrement: Optional[dict],
                           maintenant: Optional[datetime] = None) -> dict:
    """Valeurs des variables pour une étiquette : l'enregistrement fait foi,
    puis la valeur fixe ou par défaut de la variable, puis la date du jour.
    Compteurs et SSCC non fournis restent vides : c'est au serveur de les
    réserver (etiq_specifiques.plan_serie) avant l'appel."""
    rec = {str(k).lower(): ("" if v is None else str(v)) for k, v in (enregistrement or {}).items()}
    out = {}
    maintenant = maintenant or datetime.now()
    for v in layout.get("variables", []):
        nom = str(v.get("nom") or "").lower()
        if not nom:
            continue
        if nom in rec:
            out[nom] = rec[nom]
        elif v.get("type") == "date":
            d = maintenant + timedelta(days=_i(v.get("decalage_jours"), 0, -3650, 3650))
            fmt = str(v.get("format") or "%d/%m/%Y")
            out[nom] = d.strftime(fmt if "%" in fmt else "%d/%m/%Y")
        else:
            out[nom] = str(v.get("valeur") or "")
    for k, val in rec.items():
        out.setdefault(k, val)
    return out


def cle_gs1(chiffres: str) -> str:
    total = 0
    for i, c in enumerate(reversed(chiffres)):
        total += int(c) * (3 if i % 2 == 0 else 1)
    return str((10 - total % 10) % 10)


def gs1_groupes(valeur: str) -> list:
    """« (01)0345…(10)LOT » → [("01", "0345…"), ("10", "LOT")]."""
    return _AI_RE.findall(re.sub(r"\s+", "", valeur or ""))


def _gs1_avec_separateur(valeur: str, sep: str) -> str:
    groupes = gs1_groupes(valeur)
    if not groupes:
        return re.sub(r"\s+", "", valeur or "")
    out = ""
    for i, (ai, data) in enumerate(groupes):
        out += ai + data
        if i < len(groupes) - 1 and ai[:2] not in _AI_FIXES:
            out += sep
    return out


def _chiffres(v: str) -> str:
    return re.sub(r"\D", "", v or "")


def donnee_codee(symbologie: str, valeur: str) -> str:
    """Ce qu'un lecteur rend en scannant le code (sans préfixe AIM ni GS) :
    sert à la vérification après impression."""
    v = (valeur or "").strip()
    if symbologie in ("gs1_128", "gs1_datamatrix"):
        return _gs1_avec_separateur(v, "")
    if symbologie == "ean13":
        c = _chiffres(v)[:12].rjust(12, "0")
        return c + cle_gs1(c)
    if symbologie == "ean8":
        c = _chiffres(v)[:7].rjust(7, "0")
        return c + cle_gs1(c)
    if symbologie == "upca":
        c = _chiffres(v)[:11].rjust(11, "0")
        return c + cle_gs1(c)
    if symbologie == "itf14":
        c = _chiffres(v)[:13].rjust(13, "0")
        return c + cle_gs1(c)
    if symbologie == "code39":
        return v.upper()
    return v


def codes_attendus(modele: dict, enregistrements: Iterable[dict], valeurs: Optional[list] = None,
                   visible=None) -> list:
    """Données codées de chaque code-barres, étiquette par étiquette :
    [{"index", "element", "symbologie", "donnee"}]."""
    layout = layout_de(modele)
    if valeurs is None:
        valeurs = [valeurs_enregistrement(layout, rec) for rec in enregistrements]
    out = []
    for i, vals in enumerate(valeurs):
        codes = [e for e in _elements(modele, vals, visible) if e.get("type") == "code_barre"]
        for e in codes:
            sym = e.get("symbologie") if e.get("symbologie") in SYMBOLOGIES else "code128"
            d = donnee_codee(sym, substituer(e.get("valeur"), vals))
            if d:
                out.append({"index": i, "element": e.get("nom") or e.get("id") or sym, "symbologie": sym, "donnee": d})
    return out


def resume_donnees(enregistrements: list, maxi: int = 240, ignorer: Iterable = ()) -> str:
    """Résumé lisible pour le journal : premières valeurs, puis « +N ».
    Les clés techniques (« _… ») et celles de `ignorer` n'y figurent pas."""
    if not enregistrements:
        return ""
    ign = set(ignorer)
    enregistrements = [{k: v for k, v in (r or {}).items() if not str(k).startswith("_") and k not in ign}
                       for r in enregistrements]
    premier = enregistrements[0] or {}
    morceaux = [f"{k}={v}" for k, v in list(premier.items())[:6] if str(v).strip()]
    txt = ", ".join(morceaux)
    if len(enregistrements) > 1:
        dernier = enregistrements[-1] or {}
        diff = [f"{k}={v}" for k, v in dernier.items() if premier.get(k) != v][:3]
        txt += f" … {', '.join(diff)}" if diff else ""
        txt += f" ({len(enregistrements)} étiquettes)"
    return txt[:maxi]


# ─── Codes-barres : modules (aperçu et repli image) ─────────────────────

_EAN_L = ["0001101", "0011001", "0010011", "0111101", "0100011", "0110001", "0101111", "0111011",
          "0110111", "0001011"]
_EAN_R = ["".join("1" if c == "0" else "0" for c in x) for x in _EAN_L]
_EAN_G = [x[::-1] for x in _EAN_R]
_EAN_PARITE = ["LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG", "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL",
               "LGGLGL"]


def _modules_ean(code: str) -> str:
    """Modules (« 1 » barre, « 0 » espace) d'un EAN-13 / EAN-8 complet."""
    if len(code) == 8:
        g = "".join(_EAN_L[int(c)] for c in code[:4])
        d = "".join(_EAN_R[int(c)] for c in code[4:])
        return "101" + g + "01010" + d + "101"
    par = _EAN_PARITE[int(code[0])]
    g = "".join((_EAN_L if par[i] == "L" else _EAN_G)[int(c)] for i, c in enumerate(code[1:7]))
    d = "".join(_EAN_R[int(c)] for c in code[7:13])
    return "101" + g + "01010" + d + "101"


def _decompose_vers_modules(dec: str, ratio: int) -> str:
    out = []
    for c in dec:
        if c in "ABCD":
            out.append("1" * (ord(c) - 64))
        elif c in "abcd":
            out.append("0" * (ord(c) - 96))
        elif c == "b":
            out.append("1")
        elif c == "B":
            out.append("1" * ratio)
        elif c in "si":
            out.append("0")
        elif c == "S":
            out.append("0" * ratio)
    return "".join(out)


def modules_1d(symbologie: str, valeur: str, ratio: int = 3) -> str:
    """Suite de modules d'un code 1D. Lève ImpressionImpossible si la donnée
    ne peut pas être codée."""
    from reportlab.graphics.barcode.code128 import Code128
    from reportlab.graphics.barcode.code39 import Standard39
    from reportlab.graphics.barcode.common import I2of5
    d = donnee_codee(symbologie, valeur)
    if not d:
        raise ImpressionImpossible("Code-barres vide.")
    if symbologie in ("ean13", "upca"):
        return _modules_ean(d if symbologie == "ean13" else "0" + d)
    if symbologie == "ean8":
        return _modules_ean(d)
    if symbologie in ("code128", "gs1_128"):
        val = ("\xf1" + _gs1_avec_separateur(valeur, "\xf1")) if symbologie == "gs1_128" else d
        b = Code128(val)
        b.validate()
        b.encode()
        b.decompose()
        # Barres et espaces alternent : la casse ne distingue pas les deux ici.
        out, barre = [], True
        for c in b.decomposed:
            w = ord(c.upper()) - 64
            out.append(("1" if barre else "0") * w)
            barre = not barre
        return "".join(out)
    if symbologie == "code39":
        b = Standard39(d, checksum=0)
        b.validate()
        if not b.valid:
            raise ImpressionImpossible(f"Code 39 : caractère non codable dans « {d} ».")
        b.encode()
        b.decompose()
        return _decompose_vers_modules(b.decomposed, ratio)
    if symbologie == "itf14":
        b = I2of5(d, checksum=0, bearers=0, quiet=0)
        b.validate()
        b.encode()
        b.decompose()
        return _decompose_vers_modules(b.decomposed, ratio)
    raise ImpressionImpossible(f"Symbologie 1D inconnue : {symbologie}.")


def matrice_2d(symbologie: str, valeur: str, correction: str = "M") -> list:
    """Matrice (liste de lignes de booléens) d'un QR code ou d'une DataMatrix."""
    if symbologie == "qrcode":
        from reportlab.graphics.barcode import qrencoder
        niv = {"L": qrencoder.QRErrorCorrectLevel.L, "M": qrencoder.QRErrorCorrectLevel.M,
               "Q": qrencoder.QRErrorCorrectLevel.Q, "H": qrencoder.QRErrorCorrectLevel.H}
        q = qrencoder.QRCode(None, niv.get((correction or "M").upper(), niv["M"]))
        q.addData(valeur or "")
        q.make()
        return [[bool(c) for c in row] for row in q.modules]
    if symbologie in ("datamatrix", "gs1_datamatrix"):
        from reportlab.graphics.barcode.ecc200datamatrix import ECC200DataMatrix
        data = donnee_codee(symbologie, valeur)
        try:
            dm = ECC200DataMatrix(data)
            dm.validate()
            if not dm.valid:
                raise ValueError
            m = dm.encode()
        except Exception:
            raise ImpressionImpossible("DataMatrix : donnée trop longue ou non codable pour le rendu image.")
        return [[bool(c) for c in row] for row in reversed(m)]
    raise ImpressionImpossible(f"Symbologie 2D sans rendu image : {symbologie}.")


_DM_TAILLES = ((10, 3), (12, 5), (14, 8), (16, 12), (18, 18), (20, 22), (22, 30), (24, 36), (26, 44),
               (32, 62), (36, 86), (40, 114), (44, 144), (48, 174), (52, 204), (64, 280), (72, 368),
               (80, 456), (88, 576), (96, 696), (104, 816))


def taille_datamatrix(donnee: str) -> int:
    """Côté (modules) de la plus petite DataMatrix carrée ECC200 qui contient
    la donnée, deux chiffres comptant pour un mot de code."""
    chiffres = len(re.findall(r"\d\d", donnee or ""))
    mots = len(donnee or "") - chiffres + 1
    for cote, capacite in _DM_TAILLES:
        if capacite >= mots:
            return cote
    return _DM_TAILLES[-1][0]


# ─── Raster (aperçu, polices non internes, repli image) ─────────────────

def _polices_dir() -> list:
    import reportlab
    dirs = [d for d in (os.getenv("ETIQ_POLICES_DIR") or "").split(os.pathsep) if d]
    return dirs + [os.path.join(os.path.dirname(reportlab.__file__), "fonts")]


def _fichier_police(police: str, gras: bool) -> str:
    nom = re.sub(r"[^A-Za-z0-9_-]", "", police or "")
    if nom and nom not in ("0", "interne"):
        for d in _polices_dir():
            for cand in (f"{nom}{'-Bold' if gras else ''}.ttf", f"{nom}{'Bd' if gras else ''}.ttf", f"{nom}.ttf"):
                p = os.path.join(d, cand)
                if os.path.isfile(p):
                    return p
    base = _polices_dir()[-1]
    return os.path.join(base, "VeraBd.ttf" if gras else "Vera.ttf")


def police_interne(police: Any) -> bool:
    return str(police or "").strip().lower() in ("", "0", "interne", "a0")


def texte_element(e: dict, valeurs: dict) -> str:
    """Texte d'un objet, dans la langue de l'étiquette (`_langue` de
    l'enregistrement, variantes `traductions` de l'objet), substitué."""
    langue = str(valeurs.get("_langue") or "")
    brut = (e.get("traductions") or {}).get(langue) if langue else None
    return substituer(brut or e.get("valeur"), valeurs)


def texte_en_image(e: dict) -> bool:
    """Texte que l'imprimante ne sait pas tracer elle-même : police non
    interne, miroir, texte en arc (rendu droit : limite connue)."""
    return not police_interne(e.get("police")) or bool(e.get("miroir")) or bool(e.get("arc"))


_CACHE_POLICES: dict = {}


def _police_pil(police: str, gras: bool, px: int):
    from PIL import ImageFont
    cle = (police, gras, px)
    if cle not in _CACHE_POLICES:
        try:
            _CACHE_POLICES[cle] = ImageFont.truetype(_fichier_police(police, gras), max(4, px))
        except OSError:
            _CACHE_POLICES[cle] = ImageFont.load_default()
    return _CACHE_POLICES[cle]


def _decouper(texte: str, police, largeur: int, lignes_max: int) -> list:
    from PIL import ImageDraw, Image
    mesure = ImageDraw.Draw(Image.new("L", (1, 1)))
    out = []
    for para in str(texte).split("\n"):
        mots, cour = para.split(" "), ""
        for m in mots:
            essai = (cour + " " + m) if cour else m
            if largeur <= 0 or mesure.textlength(essai, font=police) <= largeur or not cour:
                cour = essai
            else:
                out.append(cour)
                cour = m
        out.append(cour)
    return out[:max(1, lignes_max)]


def _hauteur_texte(e: dict, dpi: int, texte: str) -> tuple:
    """(hauteur, largeur) de cellule en points pour un texte, taille ajustée."""
    h = max(8, dots(_f(e.get("taille"), 3.5, 0.5, 100), dpi))
    w = int(h * (1.0 if e.get("gras") else 0.85))
    larg = dots(_f(e.get("largeur"), 0, 0, FORMAT_MAX_MM), dpi)
    if e.get("ajuster") and larg and _i(e.get("lignes"), 1, 1, 20) == 1 and texte:
        estime = len(texte) * w * 0.55
        if estime > larg:
            k = larg / estime
            h, w = max(8, int(h * k)), max(6, int(w * k))
    return h, w


def _image_texte(e: dict, texte: str, dpi: int):
    """Le texte d'un élément, dessiné à plat (non tourné), en niveaux de gris."""
    from PIL import Image, ImageDraw
    h, w = _hauteur_texte(e, dpi, texte)
    interne = police_interne(e.get("police"))
    px = int(h * 0.92)
    police = _police_pil("" if interne else str(e.get("police")), bool(e.get("gras")) or interne, px)
    larg = dots(_f(e.get("largeur"), 0, 0, FORMAT_MAX_MM), dpi)
    # Police interne : la « 0 » Zebra est une grotesque grasse condensée.
    cond = (w / h) * 0.78 if interne else 1.0
    lignes = _decouper(texte, police, int(larg / cond) if larg else 0, _i(e.get("lignes"), 1, 1, 20))
    mesure = ImageDraw.Draw(Image.new("L", (1, 1)))
    large = max([int(mesure.textlength(l, font=police)) for l in lignes] + [1])
    boite = int(larg / cond) if larg else large
    img = Image.new("L", (max(1, boite), max(1, h * len(lignes))), 255)
    dr = ImageDraw.Draw(img)
    align = e.get("align") or "gauche"
    for i, l in enumerate(lignes):
        lw = mesure.textlength(l, font=police)
        x = 0 if align == "gauche" or not larg else ((boite - lw) / 2 if align == "centre" else boite - lw)
        dr.text((x, i * h + int(h * 0.04)), l, font=police, fill=0)
    if cond != 1.0:
        img = img.resize((max(1, int(img.width * cond)), img.height))
    if e.get("miroir"):
        from PIL import ImageOps
        img = ImageOps.mirror(img)
    return img


def _image_code(e: dict, valeurs: dict, dpi: int, apercu: bool):
    from PIL import Image, ImageDraw
    sym = e.get("symbologie") if e.get("symbologie") in SYMBOLOGIES else "code128"
    val = substituer(e.get("valeur"), valeurs)
    mod = max(1, dots(_f(e.get("module"), 0.375 if sym not in SYMBOLOGIES_2D else 0.5, 0.05, 5), dpi))
    h = max(4, dots(_f(e.get("hauteur"), 15, 1, 200), dpi))
    if sym == "pdf417":
        if not apercu:
            raise ImpressionImpossible("PDF417 : pas de rendu image, il faut une imprimante ZPL ou TSPL.")
        img = Image.new("L", (mod * 17 * 6, max(h, mod * 3 * 8)), 255)
        dr = ImageDraw.Draw(img)
        dr.rectangle([0, 0, img.width - 1, img.height - 1], outline=0, width=max(1, mod))
        for x in range(0, img.width, mod * 3):
            dr.line([x, 0, x, img.height], fill=0, width=1)
        return img
    if sym in SYMBOLOGIES_2D:
        if sym == "gs1_datamatrix" and not apercu:
            raise ImpressionImpossible("DataMatrix GS1 : pas de rendu image fiable, il faut une imprimante ZPL ou TSPL.")
        m = matrice_2d(sym, val, e.get("correction") or "M")
        n = len(m)
        img = Image.new("L", (n * mod, n * mod), 255)
        dr = ImageDraw.Draw(img)
        for r, row in enumerate(m):
            for c, v in enumerate(row):
                if v:
                    dr.rectangle([c * mod, r * mod, (c + 1) * mod - 1, (r + 1) * mod - 1], fill=0)
        if sym != "qrcode" and apercu:
            # L'encodeur image ne sait faire que le 44×44 : l'aperçu est ramené
            # à la taille que l'imprimante choisira pour cette donnée.
            cote = taille_datamatrix(donnee_codee(sym, val)) * mod
            img = img.resize((cote, cote), Image.NEAREST)
        return img
    mods = modules_1d(sym, val)
    lisible = e.get("lisible", True)
    th = max(8, int(h * 0.22)) if lisible else 0
    img = Image.new("L", (len(mods) * mod, h + th), 255)
    dr = ImageDraw.Draw(img)
    x = 0
    for c in mods:
        if c == "1":
            dr.rectangle([x, 0, x + mod - 1, h - 1], fill=0)
        x += mod
    if lisible:
        lib = val.strip() if sym in ("gs1_128",) else donnee_codee(sym, val)
        police = _police_pil("", False, th)
        lw = dr.textlength(lib, font=police)
        dr.text(((img.width - lw) / 2, h), lib, font=police, fill=0)
    return img


def _decoder_image(src: str):
    from PIL import Image
    s = str(src or "")
    if s.startswith("data:"):
        s = s.split(",", 1)[-1]
    try:
        brut = base64.b64decode(s, validate=False)
        img = Image.open(io.BytesIO(brut))
        img.load()
    except Exception:
        raise ImpressionImpossible("Image illisible (PNG ou JPEG en base64 attendu).")
    if img.mode in ("RGBA", "LA", "P"):
        fond = Image.new("RGBA", img.size, (255, 255, 255, 255))
        fond.alpha_composite(img.convert("RGBA"))
        img = fond
    return img.convert("L")


def binariser(img, seuil: int = 128, tramage: str = "seuil", inverse: bool = False):
    """Image en niveaux de gris → image 1 bit (0 = noir). Tramage
    Floyd-Steinberg (« diffusion ») pour les photos, seuil pour les logos."""
    from PIL import ImageOps
    if inverse:
        img = ImageOps.invert(img)
    if tramage == "diffusion":
        return img.convert("1")
    s = max(1, min(254, int(seuil)))
    return img.point(lambda p: 255 if p > s else 0).convert("1", dither=0)


def _image_element(e: dict, dpi: int):
    img = _decoder_image(e.get("src") or e.get("image"))
    w = dots(_f(e.get("largeur"), 20, 0.5, FORMAT_MAX_MM), dpi)
    h = dots(_f(e.get("hauteur"), 0, 0, FORMAT_MAX_MM), dpi) or max(1, int(w * img.height / max(1, img.width)))
    img = img.resize((max(1, w), max(1, h)))
    return binariser(img, _i(e.get("seuil"), 128, 1, 254), e.get("tramage") or "seuil",
                     bool(e.get("inverse"))).convert("L")


def _tourner(img, rotation: int):
    r = _i(rotation, 0) % 360
    return img.rotate(-r, expand=True, fillcolor=255) if r else img


def image_element(e: dict, valeurs: dict, dpi: int, apercu: bool = True):
    """Rendu image d'un élément (déjà tourné). None pour un élément vide."""
    from PIL import Image, ImageDraw
    typ = e.get("type")
    if typ == "texte":
        t = texte_element(e, valeurs)
        return _tourner(_image_texte(e, t, dpi), e.get("rotation")) if t else None
    if typ == "code_barre":
        return _tourner(_image_code(e, valeurs, dpi, apercu), e.get("rotation"))
    if typ == "image":
        return _tourner(_image_element(e, dpi), e.get("rotation"))
    if typ in ("cadre", "ellipse"):
        w = max(1, dots(_f(e.get("largeur"), 20, 0.1, FORMAT_MAX_MM), dpi))
        h = max(1, dots(_f(e.get("hauteur"), 10, 0.1, FORMAT_MAX_MM), dpi))
        t = max(1, dots(_f(e.get("epaisseur"), 0.5, 0.05, 50), dpi))
        img = Image.new("L", (w, h), 255)
        dr = ImageDraw.Draw(img)
        plein = bool(e.get("plein"))
        if typ == "ellipse":
            dr.ellipse([0, 0, w - 1, h - 1], fill=0 if plein else None, outline=0, width=t)
        else:
            r = int(_i(e.get("arrondi"), 0, 0, 8) / 8 * min(w, h) / 2)
            dr.rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=0 if plein else None, outline=0, width=t)
        return img
    if typ == "ligne":
        l = max(1, dots(_f(e.get("longueur"), 20, 0.1, FORMAT_MAX_MM), dpi))
        t = max(1, dots(_f(e.get("epaisseur"), 0.5, 0.05, 50), dpi))
        return Image.new("L", (l, t) if e.get("orientation") != "v" else (t, l), 0)
    if typ == "picto":
        return _tourner(_image_picto(e, valeurs, dpi), e.get("rotation"))
    return None


def _image_picto(e: dict, valeurs: dict, dpi: int):
    """Pictogramme réglementaire (etiq_pictos.trame) et sa légende dessous."""
    from PIL import Image, ImageDraw
    try:
        from app.services.etiq_pictos import trame
    except Exception:
        return None
    w = max(4, dots(_f(e.get("largeur"), 15, 1, FORMAT_MAX_MM), dpi))
    h = max(4, dots(_f(e.get("hauteur"), 15, 1, FORMAT_MAX_MM), dpi))
    pic = trame(str(e.get("picto") or ""), w, h)
    if pic is None:
        return None
    legende = substituer(e.get("legende"), valeurs).strip()
    if not legende:
        return pic.convert("L")
    th = max(8, dots(_f(e.get("taille_legende"), 2.2, 0.5, 20), dpi))
    police = _police_pil("", False, th)
    img = Image.new("L", (w, h + th + 2), 255)
    img.paste(pic.convert("L"), (0, 0))
    dr = ImageDraw.Draw(img)
    lw = dr.textlength(legende, font=police)
    dr.text((max(0, (w - lw) / 2), h + 1), legende, font=police, fill=0)
    return img


def _elements(modele: dict, valeurs: dict, visible=None) -> list:
    els = layout_de(modele)["elements"]
    if visible is None:
        return els
    out = []
    for e in els:
        try:
            ok = visible(e, valeurs)
        except Exception:
            ok = True
        if ok:
            out.append(e)
    return out


def rasteriser(modele: dict, valeurs: dict, dpi: int, profil: Optional[dict] = None, visible=None):
    """L'étiquette entière en image niveaux de gris (blanc = fond).
    `visible(e, valeurs)` : filtre facultatif (conditions d'affichage)."""
    from PIL import Image, ImageChops
    prof = normaliser_profil(profil, modele) if profil else normaliser_profil({"dpi": dpi}, modele)
    W, H = dots(prof["largeur_mm"], dpi), dots(prof["hauteur_mm"], dpi)
    page = Image.new("L", (max(1, W), max(1, H)), 255)
    for e in _elements(modele, valeurs, visible):
        img = image_element(e, valeurs, dpi, apercu=True)
        if img is None:
            continue
        x, y = dots(_f(e.get("x"), 0), dpi), dots(_f(e.get("y"), 0), dpi)
        if e.get("type") == "texte" and e.get("inverse"):
            zone = page.crop((x, y, x + img.width, y + img.height))
            masque = ImageChops.invert(img)
            page.paste(ImageChops.invert(zone), (x, y), masque)
        else:
            page.paste(img, (x, y), ImageChops.invert(img))
    return page


def apercu_png(modele: dict, valeurs: dict, profil: Optional[dict] = None, echelle_max: int = 1400,
               visible=None) -> bytes:
    prof = normaliser_profil(profil, modele)
    img = rasteriser(modele, valeurs, prof["dpi"], prof, visible)
    if max(img.size) > echelle_max:
        k = echelle_max / max(img.size)
        img = img.resize((max(1, int(img.width * k)), max(1, int(img.height * k))))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ─── Graphiques : ^GF (ZPL), GW (EPL), BITMAP (TSPL) ────────────────────

def octets_bitmap(img, noir_vaut_un: bool = True) -> tuple:
    """Image 'L' ou '1' → (octets par ligne, lignes, bytes). Noir = pixel < 128.
    `noir_vaut_un` : ZPL (^GF) code le noir à 1, EPL (GW) et TSPL (BITMAP) à 0.
    Les bits de bourrage en fin de ligne sont toujours blancs."""
    g = img.convert("L").point(lambda p: 255 if p >= 128 else 0).convert("1", dither=0)
    w, h = g.size
    bpr = (w + 7) // 8
    brut = g.tobytes()            # Pillow : 1 = blanc, bourrage à 0
    reste = w % 8
    masque = (0xFF << (8 - reste)) & 0xFF if reste else 0xFF
    out = bytearray(brut)
    if noir_vaut_un:
        out = bytearray(b ^ 0xFF for b in out)
        if reste:
            for y in range(h):
                out[y * bpr + bpr - 1] &= masque
    elif reste:
        for y in range(h):
            out[y * bpr + bpr - 1] |= (~masque) & 0xFF
    return bpr, h, bytes(out)


def _rep(n: int) -> str:
    s = ""
    while n >= 400:
        s += "z"
        n -= 400
    if n >= 20:
        s += chr(ord("g") + n // 20 - 1)
        n %= 20
    if n:
        s += chr(ord("G") + n - 1)
    return s


def compresser_ligne_zpl(hexa: str) -> str:
    """Compression ASCII ZPL d'une ligne hexadécimale (G…Y = 1-19, g…z = 20-400,
    « , » = zéros jusqu'au bout, « ! » = F jusqu'au bout)."""
    m = re.match(r"^(.*?)(0+)$", hexa)
    fin = ""
    if m and m.group(2):
        hexa, fin = m.group(1), ","
    else:
        m = re.match(r"^(.*?)(F+)$", hexa)
        if m and m.group(2) and len(m.group(2)) > 2:
            hexa, fin = m.group(1), "!"
    out, i = [], 0
    while i < len(hexa):
        j = i
        while j < len(hexa) and hexa[j] == hexa[i]:
            j += 1
        n = j - i
        out.append((_rep(n) + hexa[i]) if n > 1 else hexa[i])
        i = j
    return "".join(out) + fin


def zpl_graphique(img) -> str:
    """^GFA compressé (ligne identique à la précédente = « : »)."""
    bpr, h, data = octets_bitmap(img, True)
    total = bpr * h
    lignes, prec = [], None
    for y in range(h):
        hexa = data[y * bpr:(y + 1) * bpr].hex().upper()
        if hexa == prec:
            lignes.append(":")
        else:
            lignes.append(compresser_ligne_zpl(hexa))
        prec = hexa
    return f"^GFA,{total},{total},{bpr},{''.join(lignes)}"


# ─── ZPL ────────────────────────────────────────────────────────────────

def _fh(s: str) -> str:
    """Échappement ^FH\\ : \\ ^ ~ en hexadécimal, retours ligne en \\0A."""
    return (str(s).replace("\\", "\\5C").replace("^", "\\5E").replace("~", "\\7E")
            .replace("\r", "").replace("\n", "\\0A"))


def _xy(e: dict, prof: dict) -> tuple:
    d = prof["dpi"]
    return (max(0, dots(_f(e.get("x"), 0) + prof["decalage_x_mm"], d)),
            max(0, dots(_f(e.get("y"), 0) + prof["decalage_y_mm"], d)))


def _zpl_element(e: dict, vals: dict, prof: dict) -> str:
    d = prof["dpi"]
    x, y = _xy(e, prof)
    typ = e.get("type")
    rot = _ROT_ZPL.get(_i(e.get("rotation"), 0) % 360, "N")
    if typ == "texte":
        t = texte_element(e, vals)
        if not t:
            return ""
        if texte_en_image(e):
            img = _tourner(_image_texte(e, t, d), e.get("rotation"))
            return f"^FO{x},{y}{zpl_graphique(img)}^FS"
        h, w = _hauteur_texte(e, d, t)
        out = f"^FO{x},{y}^A0{rot},{h},{w}"
        larg = dots(_f(e.get("largeur"), 0, 0, FORMAT_MAX_MM), d)
        if larg:
            al = {"gauche": "L", "centre": "C", "droite": "R"}.get(e.get("align") or "gauche", "L")
            out += f"^FB{larg},{_i(e.get('lignes'), 1, 1, 20)},0,{al},0"
        if e.get("inverse"):
            out += "^FR"
        return out + f"^FH\\^FD{_fh(t)}^FS"
    if typ == "code_barre":
        sym = e.get("symbologie") if e.get("symbologie") in SYMBOLOGIES else "code128"
        val = substituer(e.get("valeur"), vals)
        if not val.strip():
            return ""
        h = max(10, dots(_f(e.get("hauteur"), 15, 1, 200), d))
        mod = max(1, dots(_f(e.get("module"), 0.375 if sym not in SYMBOLOGIES_2D else 0.5, 0.05, 5), d))
        hr = "Y" if e.get("lisible", True) else "N"
        fo = f"^FO{x},{y}"
        if sym == "code128":
            return f"{fo}^BY{mod},3,{h}^BC{rot},{h},{hr},N,N,A^FH\\^FD{_fh(val)}^FS"
        if sym == "gs1_128":
            # Mode D : parenthèses lues comme AI, FNC1 posés par l'imprimante.
            return f"{fo}^BY{mod},3,{h}^BC{rot},{h},{hr},N,N,D^FD{_GS1_NET.sub('', val)}^FS"
        if sym == "ean13":
            return f"{fo}^BY{mod},3,{h}^BE{rot},{h},{hr},N^FD{_chiffres(val)[:12]}^FS"
        if sym == "ean8":
            return f"{fo}^BY{mod},3,{h}^B8{rot},{h},{hr},N^FD{_chiffres(val)[:7]}^FS"
        if sym == "upca":
            return f"{fo}^BY{mod},3,{h}^BU{rot},{h},{hr},N,Y^FD{_chiffres(val)[:11]}^FS"
        if sym == "code39":
            return f"{fo}^BY{mod},3,{h}^B3{rot},N,{h},{hr},N^FH\\^FD{_fh(val.upper())}^FS"
        if sym == "itf14":
            return f"{fo}^BY{mod},3,{h}^B2{rot},{h},{hr},N,N^FD{donnee_codee('itf14', val)}^FS"
        if sym == "qrcode":
            ecc = (e.get("correction") or "M").upper()
            ecc = ecc if ecc in "LMQH" else "M"
            return f"{fo}^BQN,2,{min(10, mod)},{ecc}^FH\\^FD{ecc}A,{_fh(val)}^FS"
        if sym in ("datamatrix", "gs1_datamatrix"):
            # Caractère d'échappement « _ » : « _1 » = FNC1, « __ » = _ littéral.
            if sym == "gs1_datamatrix":
                data = "_1" + _gs1_avec_separateur(val.replace("_", ""), "_1")
            else:
                data = val.replace("_", "__")
            return f"{fo}^BX{rot},{mod},200,,,,_^FH\\^FD{_fh(data)}^FS"
        if sym == "pdf417":
            sec = _i(e.get("securite"), 2, 0, 8)
            col = _i(e.get("colonnes"), 0, 0, 30)
            return f"{fo}^BY{mod}^B7{rot},{mod * 3},{sec},{col or ''},,N^FH\\^FD{_fh(val)}^FS"
    if typ == "cadre":
        t = max(1, dots(_f(e.get("epaisseur"), 0.5, 0.05, 50), d))
        w = max(t, dots(_f(e.get("largeur"), 20, 0.1, FORMAT_MAX_MM), d))
        h = max(t, dots(_f(e.get("hauteur"), 10, 0.1, FORMAT_MAX_MM), d))
        if e.get("plein"):
            t = min(w, h)
        return f"^FO{x},{y}^GB{w},{h},{t},B,{_i(e.get('arrondi'), 0, 0, 8)}^FS"
    if typ == "ellipse":
        t = max(1, dots(_f(e.get("epaisseur"), 0.5, 0.05, 50), d))
        w = max(t, dots(_f(e.get("largeur"), 20, 0.1, FORMAT_MAX_MM), d))
        h = max(t, dots(_f(e.get("hauteur"), 10, 0.1, FORMAT_MAX_MM), d))
        if e.get("plein"):
            t = min(w, h) // 2 + 1
        return f"^FO{x},{y}^GE{w},{h},{t},B^FS"
    if typ == "ligne":
        t = max(1, dots(_f(e.get("epaisseur"), 0.5, 0.05, 50), d))
        l = max(1, dots(_f(e.get("longueur"), 20, 0.1, FORMAT_MAX_MM), d))
        return f"^FO{x},{y}^GB{l},{t},{t}^FS" if e.get("orientation") != "v" else f"^FO{x},{y}^GB{t},{l},{t}^FS"
    if typ in ("image", "picto"):
        img = image_element(e, vals, d, apercu=False)
        return f"^FO{x},{y}{zpl_graphique(img)}^FS" if img is not None else ""
    return ""


def epc_etiquette(modele: dict, vals: dict, prof: dict, visible=None) -> Optional[str]:
    """EPC à encoder (profil RFID) : élément « rfid » du modèle, sinon tiré du
    premier code GS1 portant un SSCC (00) ou un GTIN et une série (01)(21)."""
    if not prof.get("rfid"):
        return None
    from app.services import etiq_rfid
    els = _elements(modele, vals, visible)
    for e in els:
        if e.get("type") == "rfid":
            try:
                return etiq_rfid.epc_element(e, substituer(e.get("valeur"), vals), prof["gs1_longueur_prefixe"])
            except etiq_rfid.EpcInvalide as err:
                raise ImpressionImpossible(str(err))
    for e in els:
        if e.get("type") == "code_barre" and e.get("symbologie") in ("gs1_128", "gs1_datamatrix"):
            try:
                epc = etiq_rfid.epc_depuis_gs1(substituer(e.get("valeur"), vals), prof["gs1_longueur_prefixe"])
            except etiq_rfid.EpcInvalide:
                epc = None
            if epc:
                return epc
    return None


def _zpl_etiquette(modele: dict, vals: dict, prof: dict, copies: int, visible=None) -> str:
    d = prof["dpi"]
    tete = []
    if prof["contraste"] is not None:
        tete.append(f"~SD{min(30, prof['contraste']):02d}")
    tete += ["^XA", "^CI28", f"^PW{dots(prof['largeur_mm'], d)}", f"^LL{dots(prof['hauteur_mm'], d)}", "^LH0,0"]
    if prof["vitesse"] is not None:
        tete.append(f"^PR{max(1, min(14, prof['vitesse']))}")
    corps = [z for z in (_zpl_element(e, vals, prof) for e in _elements(modele, vals, visible)) if z]
    epc = epc_etiquette(modele, vals, prof, visible)
    if epc:
        from app.services.etiq_rfid import zpl_rfid
        corps.insert(0, zpl_rfid(epc))
    return "\n".join(tete + corps + [f"^PQ{copies}", "^XZ"]) + "\n"


# ─── EPL2 ───────────────────────────────────────────────────────────────

# Cellule (largeur, hauteur) des polices internes 1 à 5.
_EPL_POLICES = {203: [(8, 12), (10, 16), (12, 20), (14, 24), (32, 48)],
                300: [(12, 20), (16, 28), (20, 36), (24, 44), (48, 80)]}


def _epl_chaine(s: str) -> str:
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def _epl_police(h: int, dpi: int) -> tuple:
    table = _EPL_POLICES[300 if dpi >= 300 else 203]
    meilleur = None
    for n, (cw, ch) in enumerate(table, 1):
        for m in range(1, 10):
            ecart = abs(ch * m - h)
            if meilleur is None or ecart < meilleur[0]:
                meilleur = (ecart, n, m, cw)
    _, n, m, cw = meilleur
    return n, m, cw


def _epl_graphique(x: int, y: int, img) -> bytes:
    bpr, h, data = octets_bitmap(img, noir_vaut_un=False)
    return f"GW{x},{y},{bpr},{h},".encode("ascii") + data + b"\n"


def _epl_element(e: dict, vals: dict, prof: dict) -> bytes:
    d = prof["dpi"]
    x, y = _xy(e, prof)
    typ = e.get("type")
    rot = _ROT_EPL.get(_i(e.get("rotation"), 0) % 360, 0)
    if typ == "texte":
        t = texte_element(e, vals)
        if not t:
            return b""
        larg = dots(_f(e.get("largeur"), 0, 0, FORMAT_MAX_MM), d)
        multi = larg and _i(e.get("lignes"), 1, 1, 20) > 1
        if texte_en_image(e) or multi or "\n" in t:
            return _epl_graphique(x, y, _tourner(_image_texte(e, t, d), e.get("rotation")))
        h, _ = _hauteur_texte(e, d, t)
        n, m, cw = _epl_police(h, d)
        if larg and rot == 0 and (e.get("align") or "gauche") != "gauche":
            w = len(t) * cw * m
            x += max(0, (larg - w) // (2 if e.get("align") == "centre" else 1))
        inv = "R" if e.get("inverse") else "N"
        return f"A{x},{y},{rot},{n},{m},{m},{inv},{_epl_chaine(t)}\n".encode("cp1252", "replace")
    if typ == "code_barre":
        sym = e.get("symbologie") if e.get("symbologie") in SYMBOLOGIES else "code128"
        val = substituer(e.get("valeur"), vals)
        if not val.strip():
            return b""
        if sym in SYMBOLOGIES_2D:
            return _epl_graphique(x, y, _tourner(_image_code(e, vals, d, apercu=False), e.get("rotation")))
        h = max(10, dots(_f(e.get("hauteur"), 15, 1, 200), d))
        mod = max(1, dots(_f(e.get("module"), 0.375, 0.05, 5), d))
        hr = "B" if e.get("lisible", True) else "N"
        types = {"code128": "1", "gs1_128": "1E", "ean13": "E30", "ean8": "E80", "upca": "UA0", "code39": "3",
                 "itf14": "2"}
        if sym == "gs1_128":
            data = _gs1_avec_separateur(val, "")
        elif sym in ("ean13", "ean8", "upca"):
            data = donnee_codee(sym, val)[:-1]
        elif sym == "itf14":
            data = donnee_codee(sym, val)
        else:
            data = val.upper() if sym == "code39" else val
        return f"B{x},{y},{rot},{types[sym]},{mod},{mod * 3},{h},{hr},{_epl_chaine(data)}\n".encode("cp1252", "replace")
    if typ == "cadre":
        t = max(1, dots(_f(e.get("epaisseur"), 0.5, 0.05, 50), d))
        w = max(t, dots(_f(e.get("largeur"), 20, 0.1, FORMAT_MAX_MM), d))
        h = max(t, dots(_f(e.get("hauteur"), 10, 0.1, FORMAT_MAX_MM), d))
        if e.get("plein"):
            return f"LO{x},{y},{w},{h}\n".encode()
        if _i(e.get("arrondi"), 0, 0, 8):
            return _epl_graphique(x, y, image_element(e, vals, d, apercu=False))
        return f"X{x},{y},{t},{x + w},{y + h}\n".encode()
    if typ == "ligne":
        t = max(1, dots(_f(e.get("epaisseur"), 0.5, 0.05, 50), d))
        l = max(1, dots(_f(e.get("longueur"), 20, 0.1, FORMAT_MAX_MM), d))
        return (f"LO{x},{y},{l},{t}\n" if e.get("orientation") != "v" else f"LO{x},{y},{t},{l}\n").encode()
    if typ in ("image", "ellipse", "picto"):
        img = image_element(e, vals, d, apercu=False)
        return _epl_graphique(x, y, img) if img is not None else b""
    return b""


def _epl_etiquette(modele: dict, vals: dict, prof: dict, copies: int, visible=None) -> bytes:
    d = prof["dpi"]
    tete = ["", "N", "I8,A,001", f"q{dots(prof['largeur_mm'], d)}",
            f"Q{dots(prof['hauteur_mm'], d)},{dots(prof['ecart_mm'], d)}", "ZT"]
    if prof["vitesse"] is not None:
        tete.append(f"S{max(1, min(6, prof['vitesse']))}")
    if prof["contraste"] is not None:
        tete.append(f"D{min(15, prof['contraste'])}")
    out = ("\n".join(tete) + "\n").encode()
    for e in _elements(modele, vals, visible):
        out += _epl_element(e, vals, prof)
    return out + f"P1,{copies}\n".encode()


# ─── TSPL (TSC) ─────────────────────────────────────────────────────────

def _tspl_chaine(s: str) -> str:
    return '"' + str(s).replace('"', '\\["]').replace("\n", " ") + '"'


def _tspl_graphique(x: int, y: int, img) -> bytes:
    bpr, h, data = octets_bitmap(img, noir_vaut_un=False)
    return f"BITMAP {x},{y},{bpr},{h},0,".encode("ascii") + data + b"\n"


def _tspl_element(e: dict, vals: dict, prof: dict) -> bytes:
    d = prof["dpi"]
    x, y = _xy(e, prof)
    typ = e.get("type")
    rot = _i(e.get("rotation"), 0) % 360
    rot = rot if rot in (0, 90, 180, 270) else 0
    enc = lambda s: s.encode("utf-8")  # noqa: E731 — CODEPAGE UTF-8 en tête
    if typ == "texte":
        t = texte_element(e, vals)
        if not t:
            return b""
        if texte_en_image(e):
            return _tspl_graphique(x, y, _tourner(_image_texte(e, t, d), e.get("rotation")))
        h, w = _hauteur_texte(e, d, t)
        pt_h, pt_w = round(h * 72 / d, 1), round(w * 72 / d, 1)
        larg = dots(_f(e.get("largeur"), 0, 0, FORMAT_MAX_MM), d)
        al = {"gauche": 1, "centre": 2, "droite": 3}.get(e.get("align") or "gauche", 1)
        if larg:
            lignes = _i(e.get("lignes"), 1, 1, 20)
            out = f"BLOCK {x},{y},{larg},{h * lignes},\"0\",{rot},{pt_w},{pt_h},0,{al},{_tspl_chaine(t)}\n"
        else:
            out = f"TEXT {x},{y},\"0\",{rot},{pt_w},{pt_h},{_tspl_chaine(t)}\n"
        if e.get("inverse"):
            out += f"REVERSE {x},{y},{larg or int(len(t) * w * 0.55)},{h}\n"
        return enc(out)
    if typ == "code_barre":
        sym = e.get("symbologie") if e.get("symbologie") in SYMBOLOGIES else "code128"
        val = substituer(e.get("valeur"), vals)
        if not val.strip():
            return b""
        h = max(10, dots(_f(e.get("hauteur"), 15, 1, 200), d))
        mod = max(1, dots(_f(e.get("module"), 0.375 if sym not in SYMBOLOGIES_2D else 0.5, 0.05, 5), d))
        hr = 2 if e.get("lisible", True) else 0
        if sym == "qrcode":
            ecc = (e.get("correction") or "M").upper()
            return enc(f"QRCODE {x},{y},{ecc if ecc in 'LMQH' else 'M'},{min(10, mod)},A,{rot},{_tspl_chaine(val)}\n")
        if sym in ("datamatrix", "gs1_datamatrix"):
            cote = mod * 40
            if sym == "gs1_datamatrix":
                data = "~1" + _gs1_avec_separateur(val.replace("~", ""), "~1")
            else:
                data = val.replace("~", "~~")
            return enc(f"DMATRIX {x},{y},{cote},{cote},c126,x{mod},{_tspl_chaine(data)}\n")
        if sym == "pdf417":
            return enc(f"PDF417 {x},{y},{mod * 17 * 8},{max(h, mod * 3 * 10)},{rot},{_tspl_chaine(val)}\n")
        types = {"code128": "128", "gs1_128": "EAN128", "ean13": "EAN13", "ean8": "EAN8", "upca": "UPCA",
                 "code39": "39", "itf14": "ITF14"}
        if sym == "gs1_128":
            data = re.sub(r"\s", "", val)
        elif sym in ("ean13", "ean8", "upca", "itf14"):
            data = donnee_codee(sym, val)[:-1]
        else:
            data = val.upper() if sym == "code39" else val
        return enc(f"BARCODE {x},{y},\"{types[sym]}\",{h},{hr},{rot},{mod},{mod * 3},{_tspl_chaine(data)}\n")
    if typ == "cadre":
        t = max(1, dots(_f(e.get("epaisseur"), 0.5, 0.05, 50), d))
        w = max(t, dots(_f(e.get("largeur"), 20, 0.1, FORMAT_MAX_MM), d))
        h = max(t, dots(_f(e.get("hauteur"), 10, 0.1, FORMAT_MAX_MM), d))
        if e.get("plein"):
            return enc(f"BAR {x},{y},{w},{h}\n")
        r = int(_i(e.get("arrondi"), 0, 0, 8) / 8 * min(w, h) / 2)
        return enc(f"BOX {x},{y},{x + w},{y + h},{t}" + (f",{r}" if r else "") + "\n")
    if typ == "ellipse":
        t = max(1, dots(_f(e.get("epaisseur"), 0.5, 0.05, 50), d))
        w = dots(_f(e.get("largeur"), 20, 0.1, FORMAT_MAX_MM), d)
        h = dots(_f(e.get("hauteur"), 10, 0.1, FORMAT_MAX_MM), d)
        if e.get("plein"):
            return _tspl_graphique(x, y, image_element(e, vals, d, apercu=False))
        return enc(f"ELLIPSE {x},{y},{w},{h},{t}\n")
    if typ == "ligne":
        t = max(1, dots(_f(e.get("epaisseur"), 0.5, 0.05, 50), d))
        l = max(1, dots(_f(e.get("longueur"), 20, 0.1, FORMAT_MAX_MM), d))
        return enc(f"BAR {x},{y},{l},{t}\n" if e.get("orientation") != "v" else f"BAR {x},{y},{t},{l}\n")
    if typ in ("image", "picto"):
        img = image_element(e, vals, d, apercu=False)
        return _tspl_graphique(x, y, img) if img is not None else b""
    return b""


def _tspl_entete(prof: dict) -> bytes:
    lignes = [f"SIZE {prof['largeur_mm']:g} mm,{prof['hauteur_mm']:g} mm", f"GAP {prof['ecart_mm']:g} mm,0 mm",
              "DIRECTION 0", "REFERENCE 0,0", "CODEPAGE UTF-8"]
    if prof["vitesse"] is not None:
        lignes.append(f"SPEED {max(1, min(14, prof['vitesse']))}")
    if prof["contraste"] is not None:
        lignes.append(f"DENSITY {min(15, prof['contraste'])}")
    return ("\n".join(lignes) + "\n").encode()


def _tspl_etiquette(modele: dict, vals: dict, prof: dict, copies: int, visible=None) -> bytes:
    out = b"CLS\n"
    for e in _elements(modele, vals, visible):
        out += _tspl_element(e, vals, prof)
    return out + f"PRINT 1,{copies}\n".encode()


# ─── PDF (imprimante sans langage d'étiquette) ──────────────────────────

def images_vers_pdf(images: list, largeur_mm: float, hauteur_mm: float, copies: int = 1) -> bytes:
    """Une page au format de l'étiquette par image (et par exemplaire)."""
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(largeur_mm * mm, hauteur_mm * mm))
    for img in images:
        lecteur = ImageReader(img.convert("L"))
        for _ in range(copies):
            c.drawImage(lecteur, 0, 0, width=largeur_mm * mm, height=hauteur_mm * mm)
            c.showPage()
    c.save()
    return buf.getvalue()


# ─── Point d'entrée ─────────────────────────────────────────────────────

def generer(modele: dict, enregistrements: list, profil: Optional[dict], copies: int = 1,
            maintenant: Optional[datetime] = None, valeurs: Optional[list] = None, visible=None) -> bytes:
    """Flux complet pour l'imprimante : une étiquette par enregistrement,
    `copies` exemplaires identiques de chacune.

    `valeurs` : valeurs déjà calculées, une par étiquette (formules, dates,
    compteurs résolus par le serveur) ; sinon elles sont tirées des
    enregistrements. `visible(e, valeurs)` : conditions d'affichage."""
    prof = normaliser_profil(profil, modele)
    copies = max(1, min(COPIES_MAX, _i(copies, 1)))
    if valeurs is None:
        recs = list(enregistrements or [{}]) or [{}]
        layout = layout_de(modele)
        maintenant = maintenant or datetime.now()
        valeurs = [valeurs_enregistrement(layout, r, maintenant) for r in recs]
    if not valeurs:
        valeurs = [{}]
    if len(valeurs) > ENREGISTREMENTS_MAX:
        raise ImpressionImpossible(f"Trop d'étiquettes — {ENREGISTREMENTS_MAX} au plus par impression.")
    lang = prof["langage"]
    if lang == "zpl":
        return "".join(_zpl_etiquette(modele, v, prof, copies, visible) for v in valeurs).encode("utf-8")
    if lang == "epl":
        return b"".join(_epl_etiquette(modele, v, prof, copies, visible) for v in valeurs)
    if lang == "tspl":
        return _tspl_entete(prof) + b"".join(_tspl_etiquette(modele, v, prof, copies, visible) for v in valeurs)
    imgs = [rasteriser(modele, v, 300, dict(prof, dpi=300), visible) for v in valeurs]
    return images_vers_pdf(imgs, prof["largeur_mm"], prof["hauteur_mm"], copies)


def generer_depuis_images(images: list, profil: dict, copies: int = 1, seuil: int = 128,
                          tramage: str = "seuil") -> bytes:
    """Repli « rendu » : chaque image est une étiquette entière, envoyée en
    graphique (ou en PDF). Les images sont mises au format du profil."""
    prof = normaliser_profil(profil)
    copies = max(1, min(COPIES_MAX, _i(copies, 1)))
    d = prof["dpi"]
    W, H = dots(prof["largeur_mm"], d), dots(prof["hauteur_mm"], d)
    if prof["langage"] == "pdf":
        return images_vers_pdf(images, prof["largeur_mm"], prof["hauteur_mm"], copies)
    x0, y0 = max(0, dots(prof["decalage_x_mm"], d)), max(0, dots(prof["decalage_y_mm"], d))
    out = _tspl_entete(prof) if prof["langage"] == "tspl" else b""
    for img in images:
        b = binariser(img.convert("L").resize((W, H)), seuil, tramage).convert("L")
        if prof["langage"] == "zpl":
            tete = f"~SD{prof['contraste']:02d}\n" if prof["contraste"] is not None else ""
            out += (f"{tete}^XA\n^PW{W}\n^LL{H}\n^LH0,0\n^FO{x0},{y0}{zpl_graphique(b)}^FS\n^PQ{copies}\n^XZ\n"
                    ).encode("ascii")
        elif prof["langage"] == "epl":
            out += (f"\nN\nq{W}\nQ{H},{dots(prof['ecart_mm'], d)}\n").encode() + _epl_graphique(x0, y0, b) + \
                f"P1,{copies}\n".encode()
        else:
            out += b"CLS\n" + _tspl_graphique(x0, y0, b) + f"PRINT 1,{copies}\n".encode()
    return out


def pdf_vers_images(pdf: bytes, dpi: int, pages_max: int = 200) -> list:
    """Pages d'un PDF en images niveaux de gris, à la résolution de l'imprimante."""
    import pypdfium2
    try:
        doc = pypdfium2.PdfDocument(pdf)
    except Exception:
        raise ImpressionImpossible("PDF illisible.")
    if len(doc) > pages_max:
        raise ImpressionImpossible(f"PDF trop long — {pages_max} pages au plus.")
    out = []
    for i in range(len(doc)):
        page = doc[i]
        out.append(page.render(scale=dpi / 72).to_pil().convert("L"))
    return out


def decoder_image_rendu(src: str):
    return _decoder_image(src)


# Vérification par scan (lecture, note ISO) : app/services/etiq_verif.py,
# réexportée ici pour les appelants du module.
from app.services.etiq_verif import (  # noqa: E402,F401
    lecture_verificateur, normaliser_lecture, note_iso, verifier_lecture,
)
