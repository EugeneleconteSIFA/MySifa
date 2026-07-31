"""BAT etiquette — plan technique A4 genere depuis une fiche produit MyAO.
 
Un seul calcul de geometrie (en millimetres, origine en haut a gauche, y vers le
bas) produit une liste de primitives de dessin. Deux rendus consomment cette
liste :
 
- ``render_bat_svg()``  → SVG pour l'apercu dans la fiche produit
- ``render_bat_pdf()``  → PDF A4 reportlab pour le telechargement client
 
Les deux rendus sont donc garantis identiques au pixel de conversion pres : il
n'y a jamais deux mises en page a maintenir.
 
Point d'entree cote router ::
 
    from app.services.bat_etiquette import build_bat_spec, render_bat_svg, render_bat_pdf
 
    spec = build_bat_spec(produit, fiche, matieres_map=mp, fiche_technique=ft)
    svg  = render_bat_svg(spec, lang="fr")
    pdf  = render_bat_pdf(spec, lang="en")
 
Aucune donnee client n'est ecrite en dur : le nom de marque et le logo sont lus
depuis ``config`` (regle Kernse — voir CLAUDE.md).
"""
 
from __future__ import annotations
 
import base64
import io
import math
import os
import re
import unicodedata
from typing import Any, Dict, List, Optional, Sequence, Tuple
 
# ---------------------------------------------------------------------------
# Charte du plan technique
# ---------------------------------------------------------------------------
 
COLOR_CUT = "#E2001A"        # trait de decoupe
COLOR_GLASSINE = "#7BA7D7"   # support siliconne
COLOR_DIM = "#2F6FB5"        # cotes support
COLOR_INK = "#111820"        # trait et texte neutres
COLOR_MUTED = "#8A94A1"      # mention d'echelle
COLOR_WHITE = "#FFFFFF"

# Bandeau "croquis automatique". Ambre plutot que rouge : le rouge est deja
# la couleur de la decoupe, un bandeau rouge se lirait comme une cote.
COLOR_WARN_BG = "#FFF4D6"
COLOR_WARN_BORDER = "#D98A00"
COLOR_WARN_INK = "#7A4A00"

PAGE_W_MM = 210.0
PAGE_H_MM = 297.0

# Bandeau d'avertissement (haut de page). La zone 0..21 mm est libre : le
# contenu le plus haut du plan est la cote de laize a y0-11, avec y0 >= DRAW_TOP.
WARN_X, WARN_Y, WARN_W, WARN_H = 14.0, 4.0, 182.0, 16.0

# Zone de dessin du plan
DRAW_TOP = 34.0
DRAW_MAX_H = 132.0
DRAW_MAX_W = 104.0
DRAW_CX = 88.0
 
# Profondeur visible des etiquettes voisines (mm reels, mis a l'echelle)
NEIGHBOUR_BAND_MM = 17.0
 
# Cartouche
BOX_X, BOX_Y, BOX_W, BOX_H = 32.0, 230.0, 146.0, 59.0

# Encart "detail des impressions". Occupe la bande libre a droite du logo,
# sous la fleche de sens de sortie : le plan ne descend jamais plus bas que
# y = 166 et la fleche s'arrete a y = 204, colonne x = 71..105. Un encart
# ancre a droite (x >= 108) et en bas (y = 228, juste au-dessus du cartouche)
# ne peut donc croiser aucune cote, quelle que soit l'echelle retenue.
PRINT_PANEL_X = 108.0
PRINT_PANEL_W = 88.0
PRINT_PANEL_BOTTOM = 228.0
PRINT_PANEL_TOP_MIN = 177.0
COLOR_PANEL_BG = "#EDF3FA"
 
# Echelles normalisees, de la plus grande a la plus petite
STANDARD_SCALES: Tuple[Tuple[float, str], ...] = (
    (1.0, "1:1"),
    (1 / 1.5, "1:1,5"),
    (1 / 2, "1:2"),
    (1 / 2.5, "1:2,5"),
    (1 / 3, "1:3"),
    (1 / 4, "1:4"),
    (1 / 5, "1:5"),
    (1 / 7.5, "1:7,5"),
    (1 / 10, "1:10"),
)
 
# ---------------------------------------------------------------------------
# Sens de sortie — 12 positions
# ---------------------------------------------------------------------------
# 1-4  : bobine, face imprimee vers l'exterieur, 4 orientations de lecture
# 5-8  : bobine, face imprimee vers l'interieur, 4 orientations de lecture
# 9-12 : paravent (fanfold), 4 orientations de lecture
#
# ``code`` est la valeur persistee en base (int 1..12). ``legacy`` permet de
# convertir l'ancien champ texte interieur/exterieur.
 
EXIT_DIRECTIONS: Tuple[Dict[str, Any], ...] = tuple(
    {
        "code": i + 1,
        "family": "roll_out" if i < 4 else ("roll_in" if i < 8 else "fanfold"),
        "rotation": (i % 4) * 90,
        "label_fr": (
            "Bobine, sortie extérieure" if i < 4
            else "Bobine, sortie intérieure" if i < 8
            else "Paravent"
        ) + f" — position {i + 1}",
        "label_en": (
            "Roll, wound out" if i < 4
            else "Roll, wound in" if i < 8
            else "Fanfold"
        ) + f" — position {i + 1}",
    }
    for i in range(12)
)
 
EXIT_DEFAULT_CODE = 1  # sortie exterieure, lecture droite — defaut SIFA
 
_LEGACY_EXIT = {"exterieur": 1, "extérieur": 1, "interieur": 5, "intérieur": 5}
 
 
def normalize_exit_direction(value: Any) -> int:
    """Accepte un int 1..12, une chaine '1'..'12', ou l'ancien interieur/exterieur."""
    if value is None or value == "":
        return EXIT_DEFAULT_CODE
    if isinstance(value, bool):
        return EXIT_DEFAULT_CODE
    if isinstance(value, (int, float)):
        code = int(value)
        return code if 1 <= code <= 12 else EXIT_DEFAULT_CODE
    text = str(value).strip().lower()
    if text.isdigit():
        code = int(text)
        return code if 1 <= code <= 12 else EXIT_DEFAULT_CODE
    return _LEGACY_EXIT.get(text, EXIT_DEFAULT_CODE)
 
 
def exit_direction_is_inner(code: int) -> bool:
    """Compat descendante : le champ historique interieur/exterieur reste calculable."""
    return 5 <= normalize_exit_direction(code) <= 8
 
 
def exit_direction_legacy(code: int) -> str:
    return "interieur" if exit_direction_is_inner(code) else "exterieur"
 
 
def exit_direction_choices(lang: str = "fr") -> List[Dict[str, Any]]:
    key = "label_fr" if lang == "fr" else "label_en"
    return [{"code": d["code"], "label": d[key]} for d in EXIT_DIRECTIONS]
 
 
# ---------------------------------------------------------------------------
# i18n
# ---------------------------------------------------------------------------
 
TEXTS: Dict[str, Dict[str, Any]] = {
    "fr": {
        "customer": "Client",
        "our_ref": "Notre référence :",
        "your_ref": "Votre référence :",
        "produced": "BAT établi le {date}",
        "without_printing": "Sans impression",
        "with_printing": "Avec impression",
        "format": "Format",
        "radius": "Rayon",
        "adhesive": "Adhésif",
        "roll_of": "Bobine de {n} étiquettes",
        "core": "Mandrin",
        "outer_dia": "Ø extérieur",
        "perf_full": "Perforation inter-étiquette {a}/{b} mm",
        "perf_full_plain": "Perforation inter-étiquette",
        "perf_l1": "Perforation",
        "perf_l2": "Inter-étiquette {a}/{b} mm",
        "perf_l2_plain": "Inter-étiquette",
        "vperf": "Perforation verticale",
        "exit_dir": "Sens de sortie",
        "cust_exit_1": "Sens de sortie",
        "cust_exit_2": "Client",
        "cutting": "Découpe",
        "glassine": "Glassine",
        "signature": "Signature",
        "disc_1": "Vous êtes seul responsable",
        "disc_2": "des erreurs non signalées.",
        "pitch": "Pas",
        "gap": "Avance",
        "scale": "Échelle {ratio}",
        "title": "Bon à tirer",
        # Bandeau "croquis automatique" — volontairement bilingue quelle que
        # soit la langue du BAT : le document part chez des fournisseurs
        # etrangers et l'avertissement ne doit jamais etre illisible.
        "warn_title": "CROQUIS AUTOMATIQUE — AUTOMATIC SKETCH",
        "warn_fr": "Plan généré automatiquement depuis la fiche produit. Il peut contenir des erreurs : vérifiez toutes les cotes avant production.",
        "warn_en": "Automatically generated from the product data sheet. It may contain errors: check every dimension before production.",
        # Cote de rayon d'angle + encart detail des impressions
        "sharp_corner": "Angles vifs",
        "printing_title": "Impressions",
        "front": "Recto",
        "back": "Verso",
        "colour": "couleur",
        "solid": "Aplat",
        "area": "Zone",
        "face_none": "sans impression",
        "print_no_detail": "Detail des couleurs non renseigne",
        "print_more": "+{n} autre(s) couleur(s)",
        "print_summary": "Impression {r} recto / {v} verso",
    },
    "en": {
        "customer": "Customer",
        "our_ref": "Our reference :",
        "your_ref": "Your reference :",
        "produced": "This proof was produced on {date}",
        "without_printing": "Without printing",
        "with_printing": "With printing",
        "format": "Format",
        "radius": "Radius",
        "adhesive": "Adhesive",
        "roll_of": "Roll of {n} labels",
        "core": "Core",
        "outer_dia": "Outer Ø",
        "perf_full": "Inter-label perforation {a}/{b} mm",
        "perf_full_plain": "Inter-label perforation",
        "perf_l1": "Inter-label",
        "perf_l2": "Perforation {a}/{b} mm",
        "perf_l2_plain": "Perforation",
        "vperf": "Vertical perforation",
        "exit_dir": "Exit direction",
        "cust_exit_1": "Customer exit",
        "cust_exit_2": "Direction",
        "cutting": "Cutting",
        "glassine": "Glassine",
        "signature": "Signature",
        "disc_1": "You are solely responsible for",
        "disc_2": "any errors that are not reported.",
        "pitch": "Pitch",
        "gap": "Gap",
        "scale": "Scale {ratio}",
        "title": "Proof",
        "warn_title": "AUTOMATIC SKETCH — CROQUIS AUTOMATIQUE",
        "warn_fr": "Automatically generated from the product data sheet. It may contain errors: check every dimension before production.",
        "warn_en": "Plan généré automatiquement depuis la fiche produit. Il peut contenir des erreurs : vérifiez toutes les cotes avant production.",
        "sharp_corner": "Square corners",
        "printing_title": "Printing",
        "front": "Front",
        "back": "Back",
        "colour": "colour",
        "solid": "Solid ink",
        "area": "Area",
        "face_none": "no printing",
        "print_no_detail": "No colour breakdown provided",
        "print_more": "+{n} more colour(s)",
        "print_summary": "Printing {r} front / {v} back",
    },
}
 
 
def _t(lang: str) -> Dict[str, Any]:
    return TEXTS.get(lang, TEXTS["fr"])


# Sigles conserves tels quels par _sentence_case. Liste explicite et non
# heuristique : une regle du type "tout mot court en capitales" garderait
# aussi les mots outils ("BOBINE DE 1000" -> "Bobine DE 1000").
_KEEP_UPPER = {
    "PP", "PE", "PET", "PVC", "PS", "OPP", "BOPP", "PAP",
    "FSC", "PEFC", "ISO", "UV", "QR", "EAN", "GS1", "SIFA", "BAT",
    "CMJN", "CMYK", "RVB", "RGB", "Ø",
}


def _sentence_case(text: str) -> str:
    """Premiere lettre en capitale, le reste en minuscules.

    Deux exceptions, sinon on falsifierait la fiche : tout jeton contenant un
    chiffre (485C, 80g, 20/2, 76x51) garde sa casse, et les sigles listes
    dans _KEEP_UPPER restent en capitales.
    """
    s = str(text or "")
    if not s.strip():
        return text
    parts = []
    for tok in re.split(r"(\s+)", s):
        if not tok.strip():
            parts.append(tok)
        elif any(c.isdigit() for c in tok) or tok.strip(".,;:()").upper() in _KEEP_UPPER:
            parts.append(tok)
        else:
            parts.append(tok.lower())
    out = "".join(parts)
    for i, ch in enumerate(out):
        if ch.isalpha():
            return out[:i] + ch.upper() + out[i + 1:]
    return out
 
 
# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------
 
def _f(value: Any, default: float = 0.0) -> float:
    """Conversion tolerante — duree_heures et cotes sont des REAL en base."""
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
 
 
def fmt_mm(value: float) -> str:
    """1.60 → '1,6' ; 101.60 → '101,6' — virgule decimale, zeros inutiles retires."""
    rounded = round(float(value) + 0.0, 2)
    if abs(rounded - round(rounded)) < 1e-9:
        text = str(int(round(rounded)))
    else:
        text = f"{rounded:.2f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")
 
 
def _resolve_logo_path(explicit: Optional[str] = None) -> Optional[str]:
    """Cherche le logo dans les emplacements connus du repo, sans rien coder en dur."""
    candidates: List[str] = []
    if explicit:
        candidates.append(explicit)
    try:  # config.py racine = source de verite
        import config as _cfg  # type: ignore
        for attr in ("BAT_LOGO_PATH", "APP_LOGO_PATH", "LOGO_PATH"):
            value = getattr(_cfg, attr, None)
            if value:
                candidates.append(str(value))
    except Exception:  # pragma: no cover - config absente en test isole
        pass
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", ".."))
    candidates += [
        os.path.join(root, "static", "img", "logo_sifa.png"),
        os.path.join(root, "static", "logo_sifa.png"),
        os.path.join(root, "app", "web", "assets", "logo_sifa.png"),
        os.path.join(here, "assets", "logo_sifa.png"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None
 
 
def _brand_name() -> str:
    try:
        import config as _cfg  # type: ignore
        for attr in ("APP_TITLE", "APP_NAME", "BRAND_NAME"):
            value = getattr(_cfg, attr, None)
            if value:
                return str(value)
    except Exception:
        pass
    return "SIFA"
 
 
# ---------------------------------------------------------------------------
# Construction du spec depuis une fiche produit MyAO
# ---------------------------------------------------------------------------
 
def build_bat_spec(
    produit: Optional[Dict[str, Any]] = None,
    fiche: Optional[Dict[str, Any]] = None,
    matieres_map: Optional[Dict[Any, Dict[str, Any]]] = None,
    fiche_technique: Optional[Dict[str, Any]] = None,
    *,
    client_nom: str = "",
    ref_interne: str = "",
    ref_client: str = "",
    date_bat: str = "",
    lang: str = "fr",
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Normalise fiche produit MyAO (+ fiche technique optionnelle) en spec de dessin.
 
    La fiche technique, quand elle est fournie (Ref SIFA renseignee), a priorite
    sur la fiche produit pour les champs qu'elle porte de facon structuree
    (pantones par tete, nb d'etiquettes par bobine, mandrin, enroulement).
    """
    produit = produit or {}
    fiche = fiche or {}
    ft = fiche_technique or {}
    mp = matieres_map or {}
 
    etiquette = fiche.get("etiquette") or {}
    echen = fiche.get("echenillage") or {}
    bobines = fiche.get("bobines") or {}
    imp = fiche.get("impressions_detail") or {}
 
    def mp_label(mid: Any) -> str:
        row = mp.get(mid) or mp.get(str(mid)) or {}
        return str(row.get("designation") or row.get("libelle") or row.get("nom") or "").strip()
 
    laize = _f(ft.get("eti_laize")) or _f(etiquette.get("laize"))
    longueur = _f(ft.get("eti_longueur")) or _f(etiquette.get("longueur"))
    rayon = _f(ft.get("eti_rayons")) or _f(etiquette.get("rayon"))
 
    perfo_text = str(ft.get("eti_perforations") or etiquette.get("perforation") or "").strip()
    perf_cut, perf_bridge = _parse_perforation(perfo_text)
 
    nb_etiq = _i(ft.get("nb_etiq_bobin")) or _i(bobines.get("nb_etiquettes"))
    mandrin = _f(ft.get("mandrin_dia")) or _f(bobines.get("diametre_mandrin"))
    dia_ext = _f(ft.get("dia_ext")) or _f(bobines.get("diametre_bobine"))
    exit_code = normalize_exit_direction(
        bobines.get("sens_sortie", bobines.get("enroulement", ft.get("enroulement")))
    )
 
    support = str(ft.get("support") or mp_label(((fiche.get("matiere") or {}).get("frontal_id"))) or "").strip()
    adhesif = mp_label(((fiche.get("matiere") or {}).get("adhesif_id")))
 
    couleurs = _collect_colors(imp, ft)
    imprime = bool(fiche.get("impressions")) or bool(couleurs)
 
    spec: Dict[str, Any] = {
        "client": client_nom or str(produit.get("client_nom") or ""),
        "ref_interne": ref_interne or str(produit.get("ref") or ""),
        "ref_client": ref_client,
        "date_bat": date_bat,
        "designation": str(produit.get("designation") or ""),
        # geometrie
        "laize": laize,
        "longueur": longueur,
        "rayon": rayon,
        "echen_gauche": _f(ft.get("lateral_int"), _f(echen.get("gauche"))),
        "echen_droite": _f(ft.get("lateral_ext"), _f(echen.get("droite"))),
        "avance": _f(ft.get("horizontal"), _f(echen.get("avance"))),
        # perforations
        # Une perforation peut etre saisie en texte libre ("inter-etiquette",
        # "perfo standard") sans aucune cote. Elle existe quand meme : le BAT
        # doit la montrer, sans inventer de valeurs numeriques.
        "perfo_active": bool(perfo_text),
        "perfo_cotee": perf_cut > 0,
        "perfo_coupe": perf_cut,
        "perfo_pont": perf_bridge,
        "perfo_texte": perfo_text,
        "perfo_verticale": False,
        "perfo_verticale_x": 0.0,
        # bobine / matiere
        "support": support,
        "adhesif": adhesif,
        "nb_etiquettes": nb_etiq,
        "mandrin": mandrin,
        "diametre_bobine": dia_ext,
        "exit_code": exit_code,
        # impression
        "imprime": imprime,
        "couleurs": couleurs,
        # Volumetrie annoncee sur la fiche produit : elle peut differer du
        # nombre de couleurs detaillees (fiche remplie a moitie). On garde les
        # deux pour que le BAT puisse le signaler au lieu de le masquer.
        "aplat": bool(imp.get("aplat")),
        "aplat_pourcent": _f(imp.get("aplat_pourcent")),
        "nb_recto": _i(imp.get("recto")),
        "nb_verso": _i(imp.get("verso")),
        # affichage
        "show_echen": True,
        "show_pitch": True,
        "show_gap": True,
        "show_core": False,
        "scale_mode": "standard",  # "standard" | "fit"
        "auto_warning": True,
        "lang": lang,
    }
    if overrides:
        spec.update({k: v for k, v in overrides.items() if v is not None})
    spec["exit_code"] = normalize_exit_direction(spec.get("exit_code"))
    return spec
 
 
def _parse_perforation(text: str) -> Tuple[float, float]:
    """'2/1 mm', '2 / 1', 'perfo 2/1' → (2.0, 1.0). Rien d'exploitable → (0, 0)."""
    if not text:
        return 0.0, 0.0
    digits = "0123456789.,"
    parts: List[str] = []
    current = ""
    for char in text:
        if char in digits:
            current += char
        else:
            if current:
                parts.append(current)
                current = ""
            if char == "/" and parts:
                parts.append("/")
    if current:
        parts.append(current)
    numbers = [_f(p) for p in parts if p != "/"]
    if len(numbers) >= 2:
        return numbers[0], numbers[1]
    if len(numbers) == 1:
        return numbers[0], 0.0
    return 0.0, 0.0
 
 
_PANTONE_FALLBACK = "#9AA3AD"
 
_BASIC_INKS = {
    "noir": "#111820", "black": "#111820",
    "blanc": "#FFFFFF", "white": "#FFFFFF",
    "cyan": "#009EE0", "magenta": "#E5007E",
    "jaune": "#FFDD00", "yellow": "#FFDD00",
    "rouge": "#DA291C", "red": "#DA291C",
    "bleu": "#10069F", "blue": "#10069F",
    "vert": "#00954E", "green": "#00954E",
    "orange": "#F07300", "gris": "#8A94A1", "grey": "#8A94A1",
}
 
 
def _collect_colors(imp: Dict[str, Any], ft: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Couleurs de la fiche technique (pantones par tete) sinon fiche produit."""
    colors: List[Dict[str, Any]] = []
    for n in (1, 2, 3):
        pantone = str(ft.get(f"tete{n}_pantone") or "").strip()
        nom = str(ft.get(f"tete{n}_couleur") or "").strip()
        if pantone or nom:
            colors.append({
                "label": " ".join(x for x in (pantone, nom) if x).strip(),
                "hex": _guess_hex(nom or pantone),
                "face": "recto",
                "area": str(ft.get(f"tete{n}_zone") or "").strip(),
            })
    if colors:
        return colors
    for face in ("recto", "verso"):
        for row in (imp.get(f"{face}_details") or []):
            label = str((row or {}).get("couleur") or "").strip()
            if not label:
                continue
            colors.append({
                "label": label,
                "hex": _guess_hex(label),
                "face": face,
                "area": str((row or {}).get("printing_area") or "").strip(),
            })
    return colors
 
 
def _guess_hex(label: str) -> str:
    text = (label or "").strip().lower()
    if text.startswith("#") and len(text) in (4, 7):
        return text.upper()
    for key, value in _BASIC_INKS.items():
        if key in text:
            return value
    return _PANTONE_FALLBACK
 
 
# ---------------------------------------------------------------------------
# Primitives de dessin
# ---------------------------------------------------------------------------
 
def _rect(x, y, w, h, *, rx=0.0, fill=None, stroke=None, sw=0.25, dash=None,
          fill_opacity=None):
    return {"op": "rect", "x": x, "y": y, "w": w, "h": h, "rx": rx,
            "fill": fill, "stroke": stroke, "sw": sw, "dash": dash,
            "fill_opacity": fill_opacity}
 
 
def _line(x1, y1, x2, y2, *, stroke=COLOR_INK, sw=0.22, dash=None):
    return {"op": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "stroke": stroke, "sw": sw, "dash": dash}
 
 
def _poly(points: Sequence[Tuple[float, float]], *, fill=None, stroke=None, sw=0.25, close=True):
    return {"op": "poly", "pts": list(points), "fill": fill, "stroke": stroke,
            "sw": sw, "close": close}
 
 
def _text(x, y, s, *, size=2.6, fill=COLOR_INK, anchor="start", bold=False,
          italic=False, rot=0.0):
    return {"op": "text", "x": x, "y": y, "s": s, "size": size, "fill": fill,
            "anchor": anchor, "bold": bold, "italic": italic, "rot": rot}
 
 
def _circle(cx, cy, r, *, fill=None, stroke=COLOR_INK, sw=0.25):
    return {"op": "circle", "cx": cx, "cy": cy, "r": r, "fill": fill,
            "stroke": stroke, "sw": sw}
 
 
def _image(x, y, w, h, path):
    return {"op": "image", "x": x, "y": y, "w": w, "h": h, "path": path}
 
 
def _clip(x, y, w, h):
    return {"op": "clip_push", "x": x, "y": y, "w": w, "h": h}
 
 
_CLIP_POP = {"op": "clip_pop"}
 
 
# --- cotes ------------------------------------------------------------------
 
def _arrow_h(ops: List[Dict[str, Any]], x1, x2, y, color):
    a = 1.4
    ops.append(_line(x1, y, x2, y, stroke=color, sw=0.22))
    ops.append(_poly([(x1, y), (x1 + a, y - a * 0.45), (x1 + a, y + a * 0.45)], fill=color))
    ops.append(_poly([(x2, y), (x2 - a, y - a * 0.45), (x2 - a, y + a * 0.45)], fill=color))
 
 
def _arrow_v(ops: List[Dict[str, Any]], y1, y2, x, color):
    a = 1.4
    ops.append(_line(x, y1, x, y2, stroke=color, sw=0.22))
    ops.append(_poly([(x, y1), (x - a * 0.45, y1 + a), (x + a * 0.45, y1 + a)], fill=color))
    ops.append(_poly([(x, y2), (x - a * 0.45, y2 - a), (x + a * 0.45, y2 - a)], fill=color))
 
 
def _leader(ops: List[Dict[str, Any]], x1, y1, x2, y2, color, *, sw=0.2, head=1.7):
    """Trait de rappel termine par une pointe de fleche en (x2, y2)."""
    ops.append(_line(x1, y1, x2, y2, stroke=color, sw=sw))
    dx, dy = x2 - x1, y2 - y1
    norm = math.hypot(dx, dy) or 1.0
    ux, uy = dx / norm, dy / norm
    nx, ny = -uy, ux
    ops.append(_poly([
        (x2, y2),
        (x2 - ux * head + nx * head * 0.42, y2 - uy * head + ny * head * 0.42),
        (x2 - ux * head - nx * head * 0.42, y2 - uy * head - ny * head * 0.42),
    ], fill=color))


def _text_w(text: str, size: float, bold: bool = False) -> float:
    """Largeur approchee d'un texte Helvetica, en mm (pas de canvas ici)."""
    return len(str(text)) * size * (0.55 if bold else 0.50)


def _clip_text(text: str, size: float, max_w: float, bold: bool = False) -> str:
    out = str(text)
    if _text_w(out, size, bold) <= max_w:
        return out
    while out and _text_w(out + "...", size, bold) > max_w:
        out = out[:-1]
    return (out + "...") if out else ""


def _dim_h(ops, x1, x2, y, label, color, *, ext_y=None, size=2.5):
    if ext_y is not None:
        ops.append(_line(x1, ext_y, x1, y + 1.2, stroke=color, sw=0.15))
        ops.append(_line(x2, ext_y, x2, y + 1.2, stroke=color, sw=0.15))
    _arrow_h(ops, x1, x2, y, color)
    ops.append(_text((x1 + x2) / 2, y - 1.4, label, size=size, fill=color,
                     anchor="middle", bold=True))
 
 
def _dim_v(ops, y1, y2, x, label, color, *, ext_x=None, size=2.5):
    if ext_x is not None:
        ops.append(_line(ext_x, y1, x - 1.2, y1, stroke=color, sw=0.15))
        ops.append(_line(ext_x, y2, x - 1.2, y2, stroke=color, sw=0.15))
    _arrow_v(ops, y1, y2, x, color)
    ops.append(_text(x - 1.4, (y1 + y2) / 2, label, size=size, fill=color,
                     anchor="middle", bold=True, rot=-90))
 
 
# --- pictogrammes sens de sortie -------------------------------------------
 
def _picto(ops: List[Dict[str, Any]], cx: float, cy: float, index: int, selected: bool):
    size = 8.5
    ops.append(_rect(cx - size / 2, cy - size / 2, size, size,
                     fill="#E4F6E9" if selected else COLOR_WHITE,
                     stroke=COLOR_INK, sw=0.15))
    if selected:
        ops.append(_rect(cx - size / 2 + 0.4, cy - size / 2 + 0.4, 1.5, 1.5, fill="#1FA65A"))
 
    spec = EXIT_DIRECTIONS[index]
    rot = math.radians(spec["rotation"])
 
    def rp(px: float, py: float) -> Tuple[float, float]:
        """Rotation autour du centre de la cellule."""
        dx, dy = px - cx, py - cy
        return (cx + dx * math.cos(rot) - dy * math.sin(rot),
                cy + dx * math.sin(rot) + dy * math.cos(rot))
 
    if spec["family"] in ("roll_out", "roll_in"):
        r = 2.0
        roll_cy = cy + 0.6
        pc = rp(cx, roll_cy)
        ops.append(_circle(pc[0], pc[1], r, stroke=COLOR_INK, sw=0.28))
        ops.append(_circle(pc[0], pc[1], r * 0.42, stroke=COLOR_INK, sw=0.2))
        wound_out = spec["family"] == "roll_out"
        ty = roll_cy - r if wound_out else roll_cy + r
        p1, p2 = rp(cx, ty), rp(cx + 3.3, ty)
        ops.append(_line(p1[0], p1[1], p2[0], p2[1], stroke=COLOR_INK, sw=0.28))
        pa = rp(cx + 2.2, ty + (-0.5 if wound_out else 1.9))
        ops.append(_text(pa[0], pa[1], "A", size=2.0, anchor="middle", bold=True,
                         rot=spec["rotation"]))
    else:
        zig = [(cx - 2.6, cy - 2.0), (cx - 0.9, cy - 0.4), (cx - 2.6, cy + 1.2),
               (cx - 0.9, cy + 2.8)]
        pts = [rp(px, py) for px, py in zig]
        for i in range(len(pts) - 1):
            ops.append(_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                             stroke=COLOR_INK, sw=0.28))
        w1, w2 = rp(cx - 0.9, cy - 0.4), rp(cx + 3.0, cy - 0.4)
        ops.append(_line(w1[0], w1[1], w2[0], w2[1], stroke=COLOR_INK, sw=0.28))
        pa = rp(cx + 1.6, cy - 1.0)
        ops.append(_text(pa[0], pa[1], "A", size=2.0, anchor="middle", bold=True,
                         rot=spec["rotation"]))
 
 
# ---------------------------------------------------------------------------
# Geometrie du plan
# ---------------------------------------------------------------------------
 
def compute_geometry(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Calcule echelle et coordonnees. Isole pour etre testable sans rendu."""
    laize = max(_f(spec.get("laize")), 0.1)
    longueur = max(_f(spec.get("longueur")), 0.1)
    eg = max(_f(spec.get("echen_gauche")), 0.0)
    ed = max(_f(spec.get("echen_droite")), 0.0)
    avance = max(_f(spec.get("avance")), 0.0)
 
    glassine_w = laize + eg + ed
    pitch = longueur + avance
    band = NEIGHBOUR_BAND_MM
    total_h = 2 * band + 2 * avance + longueur
 
    fit = min(DRAW_MAX_W / glassine_w, DRAW_MAX_H / total_h)
    if spec.get("scale_mode") == "fit":
        scale = fit
        ratio = f"1:{fmt_mm(1 / fit)}" if fit < 1 else "1:1"
    else:
        scale, ratio = next(
            ((s, lbl) for s, lbl in STANDARD_SCALES if s <= fit),
            STANDARD_SCALES[-1],
        )
 
    gw_s = glassine_w * scale
    th_s = total_h * scale
    x0 = DRAW_CX - gw_s / 2
    y0 = DRAW_TOP + (DRAW_MAX_H - th_s) / 2
 
    return {
        "laize": laize, "longueur": longueur, "eg": eg, "ed": ed,
        "avance": avance, "glassine_w": glassine_w, "pitch": pitch,
        "band": band, "total_h": total_h, "scale": scale, "ratio": ratio,
        "gw_s": gw_s, "th_s": th_s, "x0": x0, "y0": y0,
        "label_x": x0 + eg * scale,
        "label_w": laize * scale,
        "label_h": longueur * scale,
        "radius_s": max(_f(spec.get("rayon")) * scale, 0.0),
        "y_main": y0 + (band + avance) * scale,
        "y_prev_bottom": y0 + band * scale,
        "y_next_top": y0 + (band + avance + longueur + avance) * scale,
        "gap_top_mid": y0 + (band + avance / 2) * scale,
        "gap_bottom_mid": y0 + (band + avance + longueur + avance / 2) * scale,
    }
 
 
def build_bat_ops(spec: Dict[str, Any], lang: Optional[str] = None,
                  logo_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Produit la liste de primitives du BAT complet."""
    lang = lang or spec.get("lang") or "fr"
    t = _t(lang)
    g = compute_geometry(spec)
    ops: List[Dict[str, Any]] = [_rect(0, 0, PAGE_W_MM, PAGE_H_MM, fill=COLOR_WHITE)]

    # Avertissement "croquis automatique" : actif par defaut. Le BAT est
    # toujours derive de la fiche produit, donc toujours a verifier ; seul un
    # appelant qui sait ce qu'il fait peut le desactiver (spec["auto_warning"]).
    if spec.get("auto_warning", True):
        _build_auto_warning(ops, t)

    x0, y0, gw_s, th_s = g["x0"], g["y0"], g["gw_s"], g["th_s"]
    lx, lw, lh, rs = g["label_x"], g["label_w"], g["label_h"], g["radius_s"]
    scale = g["scale"]
    avance = g["avance"]
 
    # --- support siliconne -------------------------------------------------
    ops.append(_rect(x0, y0, gw_s, th_s, fill=COLOR_GLASSINE))
 
    # --- etiquettes (voisines rognees par la zone de dessin) ---------------
    ops.append(_clip(x0 - 0.2, y0, gw_s + 0.4, th_s))
    label_kwargs = dict(rx=rs, fill=COLOR_WHITE, stroke=COLOR_CUT, sw=0.3,
                        dash=(1.6, 1.1))
    ops.append(_rect(lx, g["y_prev_bottom"] - lh, lw, lh, **label_kwargs))
    ops.append(_rect(lx, g["y_main"], lw, lh, **label_kwargs))
    ops.append(_rect(lx, g["y_next_top"], lw, lh, **label_kwargs))
 
    # perforations
    perf_on = bool(spec.get("perfo_active")) and avance > 0
    dash = None
    if perf_on:
        if spec.get("perfo_cotee"):
            cut = max(_f(spec.get("perfo_coupe")) * scale, 0.4)
            bridge = max(_f(spec.get("perfo_pont")) * scale, 0.25)
        else:
            # Perforation sans cotes : tirete generique et lisible, plutot
            # qu'un trait plein qu'on confondrait avec la decoupe.
            cut, bridge = 2.0, 0.8
        dash = (cut, bridge)
        for y in (g["gap_top_mid"], g["gap_bottom_mid"]):
            ops.append(_line(x0, y, x0 + gw_s, y, stroke=COLOR_CUT, sw=0.45, dash=dash))
    if spec.get("perfo_verticale"):
        xv = lx + _f(spec.get("perfo_verticale_x")) * scale
        ops.append(_line(xv, y0, xv, y0 + th_s, stroke=COLOR_CUT, sw=0.4,
                         dash=dash or (1.4, 0.7)))
    ops.append(_CLIP_POP)
 
    # --- cotes -------------------------------------------------------------
    _dim_h(ops, x0, x0 + gw_s, y0 - 11, f"{fmt_mm(g['glassine_w'])} mm",
           COLOR_DIM, ext_y=y0 - 1)
    _dim_h(ops, lx, lx + lw, y0 - 5.5, f"{fmt_mm(g['laize'])} mm",
           COLOR_CUT, ext_y=y0 - 1)
    _dim_v(ops, g["y_main"], g["y_main"] + lh, x0 - 8,
           f"{fmt_mm(g['longueur'])} mm", COLOR_CUT, ext_x=lx)
 
    if spec.get("show_pitch", True) and avance > 0:
        _dim_v(ops, g["y_main"], g["y_main"] + g["pitch"] * scale, x0 - 18,
               f"{t['pitch']} {fmt_mm(g['pitch'])} mm", COLOR_INK, ext_x=x0 - 7)
 
    if spec.get("show_gap", True) and avance > 0:
        xr = x0 + gw_s + 17
        ops.append(_line(x0 + gw_s, g["y_main"] + lh, xr + 1.2, g["y_main"] + lh,
                         stroke=COLOR_INK, sw=0.15))
        ops.append(_line(x0 + gw_s, g["y_next_top"], xr + 1.2, g["y_next_top"],
                         stroke=COLOR_INK, sw=0.15))
        _arrow_v(ops, g["y_main"] + lh, g["y_next_top"], xr, COLOR_INK)
        ops.append(_text(xr + 2.2, (g["y_main"] + lh + g["y_next_top"]) / 2,
                         f"{t['gap']} {fmt_mm(avance)} mm", size=2.4,
                         anchor="middle", bold=True, rot=-90))
 
    if spec.get("show_echen", True) and (g["eg"] > 0 or g["ed"] > 0):
        yb = y0 + th_s + 8
        for xv in (x0, lx, lx + lw, x0 + gw_s):
            ops.append(_line(xv, y0 + th_s, xv, yb + 1.2, stroke=COLOR_DIM, sw=0.15))
        _arrow_h(ops, x0, lx, yb, COLOR_DIM)
        _arrow_h(ops, lx + lw, x0 + gw_s, yb, COLOR_DIM)
        ops.append(_text(x0 - 1.5, yb + 0.9, fmt_mm(g["eg"]), size=2.3,
                         fill=COLOR_DIM, anchor="end", bold=True))
        ops.append(_text(x0 + gw_s + 1.5, yb + 0.9, fmt_mm(g["ed"]), size=2.3,
                         fill=COLOR_DIM, anchor="start", bold=True))
 
    # --- annotation perforation -------------------------------------------
    if perf_on:
        ax = x0 + gw_s + 5
        ops.append(_line(x0 + gw_s, g["gap_top_mid"], ax - 1, y0 + 4,
                         stroke=COLOR_CUT, sw=0.2))
        l2 = (t["perf_l2"].format(a=fmt_mm(_f(spec.get("perfo_coupe"))),
                                  b=fmt_mm(_f(spec.get("perfo_pont"))))
              if spec.get("perfo_cotee") else t["perf_l2_plain"])
        ops.append(_text(ax, y0 + 3.5, t["perf_l1"], size=2.9, fill=COLOR_CUT, bold=True))
        ops.append(_text(ax, y0 + 7, l2, size=2.9, fill=COLOR_CUT, bold=True))
    if spec.get("perfo_verticale"):
        # sous le plan, hors de la colonne de cote d'avance
        ops.append(_text(x0 + gw_s + 5, y0 + th_s + 3.5, t["vperf"], size=2.5,
                         fill=COLOR_CUT, bold=True))
 
    # --- rayon / angle des etiquettes --------------------------------------
    _build_radius_callout(ops, spec, g, t)

    ops.append(_text(x0 - 19, y0 - 11, t["scale"].format(ratio=g["ratio"]),
                     size=2.5, fill=COLOR_MUTED, bold=True))
 
    # --- fleche sens de sortie --------------------------------------------
    a_top = y0 + th_s + 12
    cx = DRAW_CX
    ops.append(_poly([
        (cx - 8, a_top), (cx + 8, a_top), (cx + 8, a_top + 11),
        (cx + 17, a_top + 11), (cx, a_top + 26), (cx - 17, a_top + 11),
        (cx - 8, a_top + 11),
    ], fill=COLOR_GLASSINE, stroke=COLOR_DIM, sw=0.25))
    ops.append(_text(cx, a_top + 5, t["cust_exit_1"], size=2.7, anchor="middle",
                     bold=True, fill="#0D2540"))
    ops.append(_text(cx, a_top + 8.6, t["cust_exit_2"], size=2.7, anchor="middle",
                     bold=True, fill="#0D2540"))
 
    # --- logo --------------------------------------------------------------
    resolved_logo = _resolve_logo_path(logo_path)
    if resolved_logo:
        logo_w, logo_h = 34.0, 34.0 * 335 / 640
        ops.append(_image(52, 212 - logo_h / 2, logo_w, logo_h, resolved_logo))
    else:
        ops.append(_text(52, 214, _brand_name(), size=8, bold=True))
 
    _build_print_panel(ops, spec, t)
    _build_cartouche(ops, spec, g, t, perf_on)
    return ops


def _build_radius_callout(ops: List[Dict[str, Any]], spec: Dict[str, Any],
                          g: Dict[str, Any], t: Dict[str, Any]) -> None:
    """Fleche vers l'angle superieur gauche de l'etiquette de reference.

    Le rayon figure deja dans le cartouche, mais un chiffre isole ne dit pas
    de quel angle il s'agit : la fleche montre l'arrondi lui-meme. Rayon nul,
    on annote quand meme, pour que "angles vifs" soit un choix lu comme tel et
    non comme un oubli de saisie.
    """
    rayon = _f(spec.get("rayon"))
    rs = g["radius_s"]
    lx, y_top, x0, y0 = g["label_x"], g["y_main"], g["x0"], g["y0"]

    if rayon > 0 and rs > 0.3:
        cx_arc, cy_arc = lx + rs, y_top + rs
        px = cx_arc - rs * 0.7071
        py = cy_arc - rs * 0.7071
        label = f"{t['radius']} {fmt_mm(rayon)} mm"
    else:
        px, py = lx, y_top
        label = t["sharp_corner"]

    # On reste sous la cote de laize : au-dessus, on marcherait sur l'echelle.
    tx = x0 - 3.0
    ty = max(y_top - 5.0, y0 - 2.0)
    _leader(ops, tx + 0.6, ty + 0.9, px, py, COLOR_DIM, sw=0.2, head=1.5)
    ops.append(_text(tx, ty, label, size=2.5, fill=COLOR_DIM, anchor="end", bold=True))


def _nb_colors(n: int, t: Dict[str, Any]) -> str:
    return f"{n} {t['colour']}" + ("s" if n > 1 else "")


def _print_panel_lines(spec: Dict[str, Any], t: Dict[str, Any]) -> List[Tuple[str, str, Any]]:
    """Contenu de l'encart impressions : (type, texte, couleur hex)."""
    couleurs = spec.get("couleurs") or []
    recto = [c for c in couleurs if (c or {}).get("face") != "verso"]
    verso = [c for c in couleurs if (c or {}).get("face") == "verso"]
    nb_r = _i(spec.get("nb_recto")) or len(recto)
    nb_v = _i(spec.get("nb_verso")) or len(verso)

    lines: List[Tuple[str, str, Any]] = []
    if spec.get("aplat"):
        pct = _f(spec.get("aplat_pourcent"))
        lines.append(("head", f"{t['solid']} {fmt_mm(pct)} %" if pct > 0 else t["solid"], None))

    for key, items, nb in (("front", recto, nb_r), ("back", verso, nb_v)):
        if nb <= 0 and not items:
            lines.append(("head", f"{t[key]} - {t['face_none']}", None))
            continue
        lines.append(("head", f"{t[key]} - {_nb_colors(nb, t)}", None))
        if items:
            for i, col in enumerate(items, 1):
                txt = f"{i}. {(col.get('label') or '').strip() or '-'}"
                area = str(col.get("area") or "").strip()
                if area:
                    txt += f" - {t['area']} : {area}"
                lines.append(("color", txt, col.get("hex")))
        else:
            lines.append(("note", t["print_no_detail"], None))
    return lines


def _build_print_panel(ops: List[Dict[str, Any]], spec: Dict[str, Any],
                       t: Dict[str, Any]) -> None:
    """Encart detaille des impressions (une ligne par passage couleur).

    Le cartouche ne portait que trois libelles de couleur tronques, sans la
    face ni la zone imprimee : un fournisseur ne pouvait pas chiffrer un
    verso spot sans rouvrir la fiche produit. L'encart donne face par face
    le nombre de passages, la pastille d'encre, le libelle et la zone.
    """
    if not spec.get("imprime"):
        return
    lines = _print_panel_lines(spec, t)
    if not lines:
        return

    title_h, pad = 5.0, 3.0
    avail = PRINT_PANEL_BOTTOM - PRINT_PANEL_TOP_MIN - title_h - 2 * pad
    step = 3.5
    if len(lines) * step > avail:
        step = max(avail / len(lines), 2.6)
    if len(lines) * step > avail:
        keep = max(int(avail // step), 1)
        hidden = len(lines) - keep + 1
        lines = lines[:keep - 1] + [("note", t["print_more"].format(n=hidden), None)]

    h = title_h + len(lines) * step + pad
    top = PRINT_PANEL_BOTTOM - h
    x, w = PRINT_PANEL_X, PRINT_PANEL_W

    ops.append(_rect(x, top, w, h, rx=1.6, fill=COLOR_WHITE, stroke=COLOR_DIM, sw=0.35))
    ops.append(_rect(x, top, w, title_h, rx=1.6, fill=COLOR_PANEL_BG))
    ops.append(_text(x + 3, top + 3.4, str(t["printing_title"]).upper(), size=3.0,
                     bold=True, fill=COLOR_DIM))

    y = top + title_h + 3.2
    for kind, txt, hex_col in lines:
        if kind == "head":
            ops.append(_text(x + 3, y, _clip_text(txt, 2.6, w - 6, bold=True),
                             size=2.6, bold=True, fill=COLOR_INK))
        elif kind == "color":
            sw_s = min(step * 0.58, 2.4)
            ops.append(_rect(x + 4.5, y - sw_s + 0.35, sw_s, sw_s, rx=0.35,
                             fill=hex_col or _PANTONE_FALLBACK, stroke=COLOR_MUTED, sw=0.12))
            tx = x + 4.5 + sw_s + 1.4
            ops.append(_text(tx, y, _clip_text(txt, 2.4, x + w - 2.5 - tx), size=2.4))
        else:
            ops.append(_text(x + 5, y, _clip_text(txt, 2.3, w - 8), size=2.3,
                             italic=True, fill=COLOR_MUTED))
        y += step
 
 
def _build_auto_warning(ops: List[Dict[str, Any]], t: Dict[str, Any]) -> None:
    """Bandeau haut de page : ce plan est un croquis genere automatiquement.

    Dessine en premier dans la zone 4..20 mm, laissee libre par compute_geometry
    (le contenu le plus haut du plan est a y0-11, avec y0 >= DRAW_TOP = 34).
    Le pictogramme est un triangle vectoriel et non un caractere Unicode : les
    polices Helvetica de base de ReportLab n'ont pas de glyphe pour "⚠".
    """
    x, y, w, h = WARN_X, WARN_Y, WARN_W, WARN_H
    ops.append(_rect(x, y, w, h, rx=1.6, fill=COLOR_WARN_BG,
                     stroke=COLOR_WARN_BORDER, sw=0.5))

    # Pictogramme triangle + point d'exclamation
    tcx, ttop, tsize = x + 8.5, y + 3.6, 8.8
    ops.append(_poly([
        (tcx, ttop),
        (tcx + tsize / 2, ttop + tsize * 0.87),
        (tcx - tsize / 2, ttop + tsize * 0.87),
    ], fill=COLOR_WARN_BORDER, stroke=COLOR_WARN_INK, sw=0.3))
    ops.append(_text(tcx, ttop + tsize * 0.72, "!", size=5.6, fill=COLOR_WHITE,
                     anchor="middle", bold=True))

    tx = x + 16.0
    ops.append(_text(tx, y + 5.6, t["warn_title"], size=3.7,
                     fill=COLOR_WARN_INK, bold=True))
    ops.append(_text(tx, y + 10.0, t["warn_fr"], size=2.55, fill=COLOR_WARN_INK))
    ops.append(_text(tx, y + 13.6, t["warn_en"], size=2.55, fill=COLOR_WARN_INK,
                     italic=True))


def _build_cartouche(ops, spec, g, t, perf_on):
    bx, by, bw, bh = BOX_X, BOX_Y, BOX_W, BOX_H
    ops.append(_rect(bx, by, bw, bh, rx=3, stroke=COLOR_INK, sw=0.45))
 
    ops.append(_text(bx + 5, by + 8, f"{t['customer']} : {spec.get('client') or ''}",
                     size=3.6, bold=True))
    ops.append(_text(bx + 73, by + 8,
                     t["with_printing"] if spec.get("imprime") else t["without_printing"],
                     size=3.1, bold=True))
    ops.append(_text(bx + 5, by + 13.5, f"{t['our_ref']} {spec.get('ref_interne') or ''}", size=1.9))
    ops.append(_text(bx + 5, by + 17.5, f"{t['your_ref']} {spec.get('ref_client') or ''}", size=1.9))
    if spec.get("date_bat"):
        ops.append(_text(bx + bw - 4, by + 17.5, t["produced"].format(date=spec["date_bat"]),
                         size=1.9, anchor="end"))
    ops.append(_line(bx, by + 20, bx + bw, by + 20, sw=0.35))
    ops.append(_line(bx + 78, by + 20, bx + 78, by + bh, sw=0.35))
    ops.append(_line(bx + 116, by + 20, bx + 116, by + bh, sw=0.35))
 
    # colonne gauche
    rows: List[Tuple[str, str]] = [
        (f"{t['format']} {fmt_mm(g['laize'])}x{fmt_mm(g['longueur'])} mm", COLOR_INK),
    ]
    if _f(spec.get("rayon")) > 0:
        rows.append((f"{t['radius']} {fmt_mm(_f(spec['rayon']))} mm", COLOR_INK))
    if spec.get("support"):
        rows.append((str(spec["support"]), COLOR_INK))
    if spec.get("adhesif"):
        rows.append((f"{t['adhesive']} {spec['adhesif']}", COLOR_INK))
    if _i(spec.get("nb_etiquettes")) > 0:
        rows.append((t["roll_of"].format(n=_i(spec["nb_etiquettes"])), COLOR_INK))
    if perf_on:
        rows.append((t["perf_full"].format(a=fmt_mm(_f(spec.get("perfo_coupe"))),
                                           b=fmt_mm(_f(spec.get("perfo_pont"))))
                     if spec.get("perfo_cotee") else t["perf_full_plain"], COLOR_CUT))
    if spec.get("perfo_verticale"):
        rows.append((t["vperf"], COLOR_CUT))
    # Le detail des couleurs vit desormais dans l'encart Impressions : ici on
    # ne garde que la volumetrie, qui sert au calcul du prix.
    if spec.get("imprime"):
        couleurs = spec.get("couleurs") or []
        nb_r = _i(spec.get("nb_recto")) or len([c for c in couleurs if (c or {}).get("face") != "verso"])
        nb_v = _i(spec.get("nb_verso")) or len([c for c in couleurs if (c or {}).get("face") == "verso"])
        rows.append((t["print_summary"].format(r=nb_r, v=nb_v), COLOR_INK))
        if spec.get("aplat"):
            pct = _f(spec.get("aplat_pourcent"))
            rows.append((f"{t['solid']} {fmt_mm(pct)} %" if pct > 0 else t["solid"], COLOR_INK))
    if spec.get("show_core") and _f(spec.get("mandrin")) > 0:
        rows.append((f"{t['core']} {fmt_mm(_f(spec['mandrin']))} mm", COLOR_INK))
    if spec.get("show_core") and _f(spec.get("diametre_bobine")) > 0:
        rows.append((f"{t['outer_dia']} {fmt_mm(_f(spec['diametre_bobine']))} mm", COLOR_INK))
 
    # Le cartouche a une hauteur fixe : on adapte l'interligne, puis on tronque
    # plutot que de laisser deborder hors du cadre.
    top = by + 27
    avail = (by + bh - 2.5) - top
    max_rows = 9
    visible = rows[:max_rows]
    step = 4.3 if len(visible) <= 1 else min(4.3, avail / (len(visible) - 1))
    size = 2.9 if step >= 3.6 else 2.5
    for idx, (label, color) in enumerate(visible):
        ops.append(_text(bx + 5, top + idx * step, _sentence_case(label),
                         size=size, bold=True, fill=color))
 
    # colonne milieu : grille sens de sortie
    ops.append(_text(bx + 97, by + 25, t["exit_dir"], size=2.7, anchor="middle", bold=True))
    selected = normalize_exit_direction(spec.get("exit_code")) - 1
    for i in range(12):
        col, row = i % 4, i // 4
        _picto(ops, bx + 84.5 + col * 8.5, by + 31.5 + row * 8.5, i, i == selected)
 
    # colonne droite : legende, signature, mention
    # Decoupe : meme tirete rouge que le contour des etiquettes sur le plan,
    # pour que la legende decrive ce qu'on voit et pas un aplat.
    ops.append(_line(bx + 120, by + 23.5, bx + 127, by + 23.5,
                     stroke=COLOR_CUT, sw=0.5, dash=(1.6, 1.1)))
    ops.append(_text(bx + 129, by + 24.7, t["cutting"], size=2.4))
    ops.append(_rect(bx + 120, by + 27, 7, 3, fill=COLOR_GLASSINE))
    ops.append(_text(bx + 129, by + 29.7, t["glassine"], size=2.4))
    ops.append(_line(bx + 116, by + 33, bx + bw, by + 33, sw=0.35))
    ops.append(_text(bx + 131, by + 40, t["signature"], size=3.2, anchor="middle", bold=True))
    ops.append(_text(bx + 131, by + 53, t["disc_1"], size=1.75, anchor="middle", italic=True))
    ops.append(_text(bx + 131, by + 55.8, t["disc_2"], size=1.75, anchor="middle", italic=True))
 
 
# ---------------------------------------------------------------------------
# Traduction des champs libres du cartouche (MyTraduction / DeepL)
# ---------------------------------------------------------------------------

# Les libelles metier (FORMAT, ADHESIF, SENS DE SORTIE...) sont traduits par
# TEXTS. Restent les champs variables issus de la base, saisis en francais :
# le support, l'adhesif et les libelles couleur. On les passe par DeepL via
# MyTraduction, qui met en cache dans translations_cache : seul le premier
# BAT d'une matiere donnee consomme du quota.
_TRANSLATABLE_KEYS = ("support", "adhesif")

# Filet de securite hors ligne. DeepL n'est pas configure sur toutes les
# instances : sans lui, un BAT anglais partirait chez le client avec le
# support et l'adhesif en francais. Le vocabulaire etiquette est borne, donc
# un glossaire le couvre. Les expressions completes passent avant les mots
# isoles : le francais postpose l'adjectif ("papier couche brillant"),
# l'anglais l'antepose ("gloss coated paper") — seule une entree de phrase
# remet les mots dans le bon ordre.
_GLOSSARY_PHRASES: Dict[str, str] = {
    # supports
    "papier couche brillant": "gloss coated paper",
    "papier couche mat": "matt coated paper",
    "papier couche": "coated paper",
    "papier thermique protege": "protected thermal paper",
    "papier thermique direct": "direct thermal paper",
    "papier thermique": "thermal paper",
    "transfert thermique": "thermal transfer",
    "papier velin": "vellum paper",
    "papier kraft": "kraft paper",
    "papier recycle": "recycled paper",
    "papier blanc": "white paper",
    "papier mat": "matt paper",
    "polypropylene blanc": "white polypropylene",
    "polypropylene transparent": "clear polypropylene",
    "polypropylene metallise": "metallised polypropylene",
    "polyethylene blanc": "white polyethylene",
    "film transparent": "clear film",
    "film blanc": "white film",
    "qualite alimentaire": "food grade",
    "contact alimentaire": "food contact",
    # adhesifs
    "acrylique permanent": "permanent acrylic",
    "acrylique enlevable": "removable acrylic",
    "acrylique repositionnable": "repositionable acrylic",
    "adhesif permanent": "permanent adhesive",
    "adhesif enlevable": "removable adhesive",
    "adhesif renforce": "high-tack adhesive",
    "forte adherence": "high tack",
    "basse temperature": "low temperature",
    "sans solvant": "solvent-free",
    "base eau": "water-based",
    "hydrosoluble": "water-soluble",
    "grand froid": "deep-freeze",
    # couleurs composees
    "bleu marine": "navy blue",
    "bleu clair": "light blue",
    "bleu fonce": "dark blue",
    "vert clair": "light green",
    "vert fonce": "dark green",
    "gris clair": "light grey",
    "gris fonce": "dark grey",
    "vernis mat": "matt varnish",
    "vernis brillant": "gloss varnish",
}

_GLOSSARY_WORDS: Dict[str, str] = {
    # matieres
    "papier": "paper", "carton": "board", "film": "film", "kraft": "kraft",
    "velin": "vellum", "couche": "coated", "thermique": "thermal",
    "polypropylene": "polypropylene", "polyester": "polyester",
    "polyethylene": "polyethylene", "pp": "PP", "pe": "PE", "pet": "PET",
    "glassine": "glassine", "siliconne": "silicone-coated",
    "silicone": "silicone-coated", "pellicule": "laminated",
    "vernis": "varnish", "recycle": "recycled", "metallise": "metallised",
    "autocollant": "self-adhesive", "support": "face stock",
    # adhesifs
    "adhesif": "adhesive", "acrylique": "acrylic", "caoutchouc": "rubber",
    "hotmelt": "hotmelt", "permanent": "permanent", "enlevable": "removable",
    "repositionnable": "repositionable", "renforce": "high-tack",
    "congelation": "deep-freeze", "surgelation": "deep-freeze",
    # etats / adjectifs
    "brillant": "gloss", "mat": "matt", "satine": "satin",
    "transparent": "clear", "opaque": "opaque", "protege": "protected",
    "lisse": "smooth", "rugueux": "rough", "souple": "flexible",
    "rigide": "rigid", "resistant": "resistant", "epais": "thick",
    "fin": "thin", "clair": "light", "fonce": "dark", "neutre": "neutral",
    "special": "special", "renforcee": "reinforced", "imprime": "printed",
    "alimentaire": "food-grade", "humide": "damp", "froid": "cold",
    # couleurs
    "noir": "black", "noire": "black", "blanc": "white", "blanche": "white",
    "rouge": "red", "bleu": "blue", "bleue": "blue", "vert": "green",
    "verte": "green", "jaune": "yellow", "orange": "orange",
    "violet": "purple", "rose": "pink", "gris": "grey", "grise": "grey",
    "marron": "brown", "brun": "brown", "beige": "beige", "cyan": "cyan",
    "magenta": "magenta", "argent": "silver", "argente": "silver",
    "or": "gold", "dore": "gold", "doree": "gold",
}

_WORD_RE = re.compile(r"[A-Za-z\u00C0-\u024F]+")


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def _match_case(src_word: str, out: str) -> str:
    """Rend la casse du mot source : SUPPORT -> ADHESIVE, Support -> Adhesive."""
    if src_word.isupper() and len(src_word) > 1:
        return out.upper()
    if src_word[:1].isupper():
        return out[:1].upper() + out[1:]
    return out


def glossary_translate(text: str) -> str:
    """Traduit FR->EN mot a mot via le glossaire. Inconnu = laisse tel quel.

    Volontairement conservateur : une reference fournisseur (RAFLATAC RP37),
    un grammage (80g) ou un pantone (485C) ne contiennent aucun terme du
    glossaire et ressortent intacts.
    """
    s = str(text or "")
    if not s.strip():
        return text

    tokens = _WORD_RE.split(s)          # separateurs (espaces, chiffres, /)
    words = _WORD_RE.findall(s)         # mots
    norm = [_strip_accents(w).lower() for w in words]

    out: List[Optional[str]] = [None] * len(words)
    i = 0
    hit = False
    while i < len(words):
        matched = False
        for span in (4, 3, 2):          # phrases d'abord, de la plus longue
            if i + span > len(words):
                continue
            key = " ".join(norm[i:i + span])
            if key in _GLOSSARY_PHRASES:
                out[i] = _match_case(words[i], _GLOSSARY_PHRASES[key])
                for k in range(i + 1, i + span):
                    out[k] = ""
                i += span
                matched = hit = True
                break
        if matched:
            continue
        rep = _GLOSSARY_WORDS.get(norm[i])
        if rep:
            out[i] = _match_case(words[i], rep)
            hit = True
        else:
            out[i] = words[i]
        i += 1

    if not hit:                         # rien de reconnu : on ne touche a rien
        return text

    parts = [tokens[0]]
    for idx, w in enumerate(out):
        parts.append(w or "")
        parts.append(tokens[idx + 1])
    return re.sub(r"\s{2,}", " ", "".join(parts)).strip()


def translate_spec_fields(spec: Dict[str, Any], conn=None, lang: str = "en",
                          user_id: Optional[int] = None) -> Dict[str, Any]:
    """Traduit sur place les champs libres du cartouche. Retourne spec.

    DeepL d'abord quand une connexion est fournie (meilleure qualite, cache
    SQLite), glossaire ensuite. Aucune des deux voies ne peut faire echouer
    le BAT : cle absente, quota atteint ou reseau coupe retombent sur le
    glossaire, et un terme hors glossaire reste en francais. Un BAT en
    franglais reste livrable ; un BAT qui repond 502 ne l'est pas.
    """
    if (lang or "fr").lower() != "en":
        return spec

    _deepl = None
    if conn is not None:
        try:
            from app.services.translate_service import translate as _deepl
        except Exception:
            _deepl = None

    def _one(txt: Any) -> Any:
        s = str(txt or "").strip()
        if not s:
            return txt
        if _deepl is not None:
            try:
                res = _deepl(conn, text=s, target_lang="EN", source_lang="FR",
                             user_id=user_id)
                if res.get("translated"):
                    return res["translated"]
            except Exception:
                pass
        return glossary_translate(s)

    for key in _TRANSLATABLE_KEYS:
        if spec.get(key):
            spec[key] = _one(spec[key])
    for color in (spec.get("couleurs") or []):
        if color.get("label"):
            color["label"] = _one(color["label"])
        if color.get("area"):
            color["area"] = _one(color["area"])
    return spec


# ---------------------------------------------------------------------------
# Rendu SVG
# ---------------------------------------------------------------------------
 
_SVG_FONT = "Helvetica, Arial, sans-serif"
 
 
def _esc(value: Any) -> str:
    return (str(value).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))
 
 
def _svg_dash(dash) -> str:
    return f' stroke-dasharray="{dash[0]:.3f} {dash[1]:.3f}"' if dash else ""
 
 
def _svg_paint(op) -> str:
    out = ""
    fill = op.get("fill")
    out += f' fill="{fill}"' if fill else ' fill="none"'
    if op.get("fill_opacity") is not None:
        out += f' fill-opacity="{op["fill_opacity"]}"'
    stroke = op.get("stroke")
    if stroke:
        out += f' stroke="{stroke}" stroke-width="{op.get("sw", 0.25):.3f}"'
    return out
 
 
def render_bat_svg(spec: Dict[str, Any], lang: Optional[str] = None,
                   logo_path: Optional[str] = None,
                   ops: Optional[List[Dict[str, Any]]] = None) -> str:
    """SVG autonome, unites millimetre, pret a etre injecte dans la page."""
    ops = ops if ops is not None else build_bat_ops(spec, lang, logo_path)
    parts: List[str] = []
    clip_id = 0
    open_clips = 0
 
    for op in ops:
        kind = op["op"]
        if kind == "rect":
            rx = min(op.get("rx", 0.0), min(op["w"], op["h"]) / 2)
            parts.append(
                f'<rect x="{op["x"]:.3f}" y="{op["y"]:.3f}" width="{op["w"]:.3f}"'
                f' height="{op["h"]:.3f}" rx="{rx:.3f}" ry="{rx:.3f}"'
                f'{_svg_paint(op)}{_svg_dash(op.get("dash"))}/>'
            )
        elif kind == "line":
            parts.append(
                f'<line x1="{op["x1"]:.3f}" y1="{op["y1"]:.3f}" x2="{op["x2"]:.3f}"'
                f' y2="{op["y2"]:.3f}" stroke="{op.get("stroke", COLOR_INK)}"'
                f' stroke-width="{op.get("sw", 0.22):.3f}"{_svg_dash(op.get("dash"))}/>'
            )
        elif kind == "poly":
            pts = " ".join(f"{x:.3f},{y:.3f}" for x, y in op["pts"])
            tag = "polygon" if op.get("close", True) else "polyline"
            parts.append(f'<{tag} points="{pts}"{_svg_paint(op)}/>')
        elif kind == "circle":
            parts.append(
                f'<circle cx="{op["cx"]:.3f}" cy="{op["cy"]:.3f}" r="{op["r"]:.3f}"'
                f'{_svg_paint(op)}/>'
            )
        elif kind == "text":
            anchor = {"start": "start", "middle": "middle", "end": "end"}[op["anchor"]]
            transform = ""
            if op.get("rot"):
                transform = f' transform="rotate({op["rot"]} {op["x"]:.3f} {op["y"]:.3f})"'
            style = ""
            if op.get("bold"):
                style += ' font-weight="bold"'
            if op.get("italic"):
                style += ' font-style="italic"'
            parts.append(
                f'<text x="{op["x"]:.3f}" y="{op["y"]:.3f}" font-family="{_SVG_FONT}"'
                f' font-size="{op["size"]:.3f}" fill="{op.get("fill", COLOR_INK)}"'
                f' text-anchor="{anchor}"{style}{transform}>{_esc(op["s"])}</text>'
            )
        elif kind == "image":
            href = _data_uri(op["path"])
            if href:
                parts.append(
                    f'<image x="{op["x"]:.3f}" y="{op["y"]:.3f}" width="{op["w"]:.3f}"'
                    f' height="{op["h"]:.3f}" href="{href}" preserveAspectRatio="xMidYMid meet"/>'
                )
        elif kind == "clip_push":
            clip_id += 1
            parts.append(
                f'<clipPath id="batclip{clip_id}"><rect x="{op["x"]:.3f}"'
                f' y="{op["y"]:.3f}" width="{op["w"]:.3f}" height="{op["h"]:.3f}"/></clipPath>'
                f'<g clip-path="url(#batclip{clip_id})">'
            )
            open_clips += 1
        elif kind == "clip_pop":
            if open_clips:
                parts.append("</g>")
                open_clips -= 1
 
    parts.append("</g>" * open_clips)
    body = "".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"'
        f' viewBox="0 0 {PAGE_W_MM:.0f} {PAGE_H_MM:.0f}" width="100%"'
        f' preserveAspectRatio="xMidYMid meet" role="img">{body}</svg>'
    )
 
 
_DATA_URI_CACHE: Dict[str, str] = {}
 
 
def _data_uri(path: str) -> str:
    if path in _DATA_URI_CACHE:
        return _DATA_URI_CACHE[path]
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError:
        return ""
    ext = os.path.splitext(path)[1].lower()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".gif": "image/gif", ".svg": "image/svg+xml"}.get(ext, "image/png")
    uri = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
    _DATA_URI_CACHE[path] = uri
    return uri
 
 
# ---------------------------------------------------------------------------
# Rendu PDF (reportlab)
# ---------------------------------------------------------------------------
 
def render_bat_pdf(spec: Dict[str, Any], lang: Optional[str] = None,
                   logo_path: Optional[str] = None,
                   ops: Optional[List[Dict[str, Any]]] = None) -> bytes:
    """PDF A4 vectoriel, meme geometrie que le SVG."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfgen import canvas as rl_canvas
 
    ops = ops if ops is not None else build_bat_ops(spec, lang, logo_path)
    buffer = io.BytesIO()
    c = rl_canvas.Canvas(buffer, pagesize=A4)
    c.setTitle(f"BAT {spec.get('ref_interne') or ''} {spec.get('client') or ''}".strip())
 
    def X(v: float) -> float:
        return v * mm
 
    def Y(v: float) -> float:
        return (PAGE_H_MM - v) * mm
 
    def set_dash(dash):
        c.setDash([dash[0] * mm, dash[1] * mm]) if dash else c.setDash()
 
    def font_name(op) -> str:
        if op.get("bold"):
            return "Helvetica-Bold"
        if op.get("italic"):
            return "Helvetica-Oblique"
        return "Helvetica"
 
    clip_depth = 0
    for op in ops:
        kind = op["op"]
 
        if kind == "clip_push":
            c.saveState()
            path = c.beginPath()
            path.rect(X(op["x"]), Y(op["y"] + op["h"]), op["w"] * mm, op["h"] * mm)
            c.clipPath(path, stroke=0, fill=0)
            clip_depth += 1
            continue
        if kind == "clip_pop":
            if clip_depth:
                c.restoreState()
                clip_depth -= 1
            continue
 
        if kind == "rect":
            c.saveState()
            set_dash(op.get("dash"))
            fill = op.get("fill")
            stroke = op.get("stroke")
            if fill:
                c.setFillColor(_rl_color(fill, op.get("fill_opacity")))
            if stroke:
                c.setStrokeColor(_rl_color(stroke))
                c.setLineWidth(op.get("sw", 0.25) * mm)
            rx = min(op.get("rx", 0.0), min(op["w"], op["h"]) / 2)
            args = (X(op["x"]), Y(op["y"] + op["h"]), op["w"] * mm, op["h"] * mm)
            if rx > 0.01:
                c.roundRect(*args, rx * mm, stroke=1 if stroke else 0, fill=1 if fill else 0)
            else:
                c.rect(*args, stroke=1 if stroke else 0, fill=1 if fill else 0)
            c.restoreState()
 
        elif kind == "line":
            c.saveState()
            set_dash(op.get("dash"))
            c.setStrokeColor(_rl_color(op.get("stroke", COLOR_INK)))
            c.setLineWidth(op.get("sw", 0.22) * mm)
            c.line(X(op["x1"]), Y(op["y1"]), X(op["x2"]), Y(op["y2"]))
            c.restoreState()
 
        elif kind == "poly":
            c.saveState()
            path = c.beginPath()
            pts = op["pts"]
            path.moveTo(X(pts[0][0]), Y(pts[0][1]))
            for px, py in pts[1:]:
                path.lineTo(X(px), Y(py))
            if op.get("close", True):
                path.close()
            fill = op.get("fill")
            stroke = op.get("stroke")
            if fill:
                c.setFillColor(_rl_color(fill))
            if stroke:
                c.setStrokeColor(_rl_color(stroke))
                c.setLineWidth(op.get("sw", 0.25) * mm)
            c.drawPath(path, stroke=1 if stroke else 0, fill=1 if fill else 0)
            c.restoreState()
 
        elif kind == "circle":
            c.saveState()
            fill = op.get("fill")
            stroke = op.get("stroke")
            if fill:
                c.setFillColor(_rl_color(fill))
            if stroke:
                c.setStrokeColor(_rl_color(stroke))
                c.setLineWidth(op.get("sw", 0.25) * mm)
            c.circle(X(op["cx"]), Y(op["cy"]), op["r"] * mm,
                     stroke=1 if stroke else 0, fill=1 if fill else 0)
            c.restoreState()
 
        elif kind == "text":
            c.saveState()
            name = font_name(op)
            size_pt = op["size"] * mm
            c.setFont(name, size_pt)
            c.setFillColor(_rl_color(op.get("fill", COLOR_INK)))
            width = pdfmetrics.stringWidth(str(op["s"]), name, size_pt)
            dx = {"start": 0.0, "middle": -width / 2, "end": -width}[op["anchor"]]
            c.translate(X(op["x"]), Y(op["y"]))
            if op.get("rot"):
                c.rotate(-op["rot"])  # SVG horaire → reportlab antihoraire
            c.drawString(dx, 0, str(op["s"]))
            c.restoreState()
 
        elif kind == "image":
            try:
                c.drawImage(ImageReader(op["path"]), X(op["x"]), Y(op["y"] + op["h"]),
                            op["w"] * mm, op["h"] * mm, mask="auto",
                            preserveAspectRatio=True, anchor="c")
            except Exception:
                pass
 
    while clip_depth:
        c.restoreState()
        clip_depth -= 1
 
    c.showPage()
    c.save()
    return buffer.getvalue()
 
 
def _rl_color(value: str, opacity: Optional[float] = None):
    from reportlab.lib.colors import HexColor
    color = HexColor(value if value.startswith("#") else f"#{value}")
    if opacity is not None:
        color = color.clone(alpha=float(opacity))
    return color
 
 
# ---------------------------------------------------------------------------
# Nom de fichier
# ---------------------------------------------------------------------------
 
def bat_filename(spec: Dict[str, Any]) -> str:
    g = compute_geometry(spec)
    parts = ["BAT"]
    if spec.get("ref_interne"):
        parts.append(str(spec["ref_interne"]))
    parts.append(f"{fmt_mm(g['laize']).replace(',', '')}x{fmt_mm(g['longueur']).replace(',', '')}mm")
    if spec.get("client"):
        parts.append(str(spec["client"]))
    safe = "_".join(
        "".join(ch if (ch.isalnum() or ch in "-_") else "-" for ch in str(p)).strip("-")
        for p in parts if str(p).strip()
    )
    return f"{safe}.pdf"
 