"""Composition automatique de la référence d'un produit MyAO.

La référence part chez des fournisseurs étrangers : elle est donc rédigée en
anglais, et suit toujours le même gabarit ::

    <laize> x <longueur> mm <frontal> <adhésif>, <n> Color(s), M<mandrin> mm
    105 x 148 mm Th Top-Coated Perm, 1 Color, M40 mm

Chaque segment optionnel disparaît quand la donnée manque — un produit sans
impression n'affiche pas « 0 Colors », il n'affiche rien.

Abréviation des matières : deux niveaux, dans cet ordre.

1. ``matieres_premieres.abbreviation`` — la forme courte saisie dans MyStock.
   C'est la seule source fiable : « Th Top-Coated » ne se déduit pas d'une
   désignation par une règle générale.
2. À défaut, ``abbreviate_designation()`` réduit la désignation française via un
   glossaire explicite. C'est un repli utile mais approximatif, volontairement
   conservateur : un mot inconnu est gardé tel quel plutôt que tronqué.

Le module ne touche pas la base et n'importe rien de l'application : il est
testable seul, et sert de source unique de vérité pour le serveur comme pour le
formulaire (qui consomme les abréviations calculées via ``/api/ao/matieres``).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, Optional

__all__ = [
    "abbreviate_designation",
    "matiere_abbrev",
    "build_ref_produit",
    "format_dimension",
    "unique_ref",
]


# ---------------------------------------------------------------------------
# Glossaire d'abréviation (repli quand la colonne abbreviation est vide)
# ---------------------------------------------------------------------------
# Ordre significatif : les expressions les plus longues d'abord, pour que
# « top coated » soit consommé avant « coated ». Clés normalisées (minuscules,
# sans accents).

_GLOSSARY: tuple[tuple[str, str], ...] = (
    # Familles de frontaux
    ("thermique top coated", "Th Top-Coated"),
    ("thermique topcoated", "Th Top-Coated"),
    ("thermique protege", "Th Protected"),
    ("thermique eco", "Th Eco"),
    ("thermique", "Th"),
    ("top coated", "Top-Coated"),
    ("topcoated", "Top-Coated"),
    ("jet d encre", "Inkjet"),
    ("jet d'encre", "Inkjet"),
    ("sans silicone", "Linerless"),
    ("couche", "Coated"),
    ("velin", "Vellum"),
    ("polypropylene", "PP"),
    ("polyethylene", "PE"),
    ("polyester", "PET"),
    ("papier", "Paper"),
    ("carton", "Board"),
    ("glassine", "Glassine"),
    # Familles d'adhésifs
    ("repositionnable", "Remov"),
    ("enlevable", "Remov"),
    ("amovible", "Remov"),
    ("permanent", "Perm"),
    ("renforce", "Reinf"),
    ("acrylique", "Acrylic"),
    ("hot melt", "HM"),
    ("hotmelt", "HM"),
    ("caoutchouc", "Rubber"),
    ("dispersion", "Disp"),
    # Qualificatifs
    ("congelation", "Deep-Freeze"),
    ("surgele", "Deep-Freeze"),
    ("alimentaire", "Food"),
    ("securite", "Security"),
    ("pneumatique", "Tyre"),
    ("transparent", "Clear"),
    ("brillant", "Gloss"),
    ("argente", "Silver"),
    ("argent", "Silver"),
    ("dore", "Gold"),
    ("blanc", "White"),
    ("noir", "Black"),
    ("jaune", "Yellow"),
    ("rouge", "Red"),
    ("bleu", "Blue"),
    ("vert", "Green"),
    ("mat", "Matt"),
    ("or", "Gold"),
)

# Sigles et codes gardés intacts par la mise en casse.
_KEEP_AS_IS = {
    "PP", "PE", "PET", "PVC", "HM", "FSC", "PEFC", "BOPP", "TC", "UV",
    "RFID", "EAN", "OTR", "MDO", "PCR",
}

# Préfixe de code article fournisseur : « 1393299 - papier jet d'encre mat 70g ».
# Le code n'apporte rien dans une référence produit.
_CODE_PREFIX_RE = re.compile(r"^\s*[\w./-]*\d{3,}[\w./-]*\s*[-–—]\s*")

# Grammages et épaisseurs : « 80 g », « 80g/m2 », « 23 µm » → conservés compacts.
_GRAMMAGE_RE = re.compile(r"^(\d+(?:[.,]\d+)?)\s*(g|gsm|g/m2|gr|um|µm|mic)$", re.I)


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def _normalize(text: str) -> str:
    out = re.sub(r"\s+", " ", _strip_accents(str(text or "")).lower()).strip()
    # « 80 g » et « 23 µm » sont une seule information : on recolle l'unité au
    # nombre avant de découper en mots, sinon « g » ressort comme un mot isolé.
    return re.sub(r"(\d)\s+(g/m2|gsm|gr|g|µm|um|mic)\b", r"\1\2", out)


def _titlecase_token(token: str) -> str:
    """Met un mot en casse de référence, en préservant sigles et grammages."""
    upper = token.upper()
    if upper in _KEEP_AS_IS:
        return upper
    m = _GRAMMAGE_RE.match(token)
    if m:
        unit = m.group(2).lower()
        unit = "µm" if unit in {"um", "µm", "mic"} else ("g" if unit in {"g", "gr"} else unit)
        return f"{m.group(1).replace(',', '.')}{unit}"
    if token.isupper() and len(token) <= 4:
        return upper
    return token[:1].upper() + token[1:]


def abbreviate_designation(designation: str) -> str:
    """Réduit une désignation de matière française en forme courte anglaise.

    Repli heuristique, utilisé seulement quand ``abbreviation`` n'est pas saisie.
    Les mots reconnus sont traduits et raccourcis ; les autres sont conservés,
    parce qu'une troncature arbitraire produirait une référence illisible.

    >>> abbreviate_designation("Thermique Top Coated 80 g")
    'Th Top-Coated 80g'
    >>> abbreviate_designation("Adhésif permanent acrylique")
    'Perm Acrylic'
    """
    raw = str(designation or "").strip()
    if not raw:
        return ""
    raw = _CODE_PREFIX_RE.sub("", raw)

    normalized = _normalize(raw)
    if not normalized:
        return ""

    pieces: list[str] = []
    remaining = normalized
    # On consomme le texte de gauche à droite : à chaque position, la plus longue
    # entrée du glossaire qui matche gagne. Les fragments non reconnus sont
    # accumulés puis remis en casse mot par mot.
    buffer: list[str] = []
    while remaining:
        matched = None
        for key, value in _GLOSSARY:
            if remaining.startswith(key) and (
                len(remaining) == len(key) or not remaining[len(key)].isalnum()
            ):
                matched = (key, value)
                break
        if matched:
            if buffer:
                pieces.extend(_titlecase_token(w) for w in "".join(buffer).split())
                buffer = []
            pieces.append(matched[1])
            remaining = remaining[len(matched[0]):].lstrip()
        else:
            buffer.append(remaining[0])
            remaining = remaining[1:]
    if buffer:
        pieces.extend(_titlecase_token(w) for w in "".join(buffer).split())

    # Dédoublonne en conservant l'ordre : « adhesif permanent permanent » arrive.
    seen: set[str] = set()
    out: list[str] = []
    for p in pieces:
        if not p:
            continue
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    # « Adhésif » / « Adhesive » n'apporte rien : la position dans la référence
    # dit déjà qu'il s'agit de l'adhésif.
    out = [p for p in out if p.lower() not in {"adhesif", "adhesive", "support", "frontal"}]
    return " ".join(out)


def matiere_abbrev(row: Optional[Dict[str, Any]]) -> str:
    """Forme courte d'une matière : colonne ``abbreviation``, sinon repli déduit."""
    if not row:
        return ""
    explicit = str(row.get("abbreviation") or "").strip()
    if explicit:
        return explicit
    return abbreviate_designation(row.get("designation") or row.get("reference") or "")


# ---------------------------------------------------------------------------
# Composition de la référence
# ---------------------------------------------------------------------------

def format_dimension(value: Any) -> str:
    """Cote en millimètres, sans zéro inutile. Séparateur décimal : le point.

    Le point plutôt que la virgule parce que la virgule sépare déjà les segments
    de la référence : « 101,6 x 152,4 mm Th, 1 Color » serait ambigu à la lecture
    comme au parsing.

    >>> format_dimension(105.0), format_dimension(101.6)
    ('105', '101.6')
    """
    try:
        num = float(str(value).replace(",", ".")) if value not in (None, "") else 0.0
    except (TypeError, ValueError):
        return ""
    if num <= 0:
        return ""
    if abs(num - round(num)) < 1e-9:
        return str(int(round(num)))
    return f"{num:.2f}".rstrip("0").rstrip(".")


def _int_or_zero(value: Any) -> int:
    try:
        return int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return 0


def _colors_segment(fiche: Dict[str, Any]) -> str:
    """« 1 Color », « 4 Colors », « 4+1 Colors ». Vide si le produit est nu."""
    if not fiche.get("impressions"):
        return ""
    imp = fiche.get("impressions_detail") or {}
    recto = _int_or_zero(imp.get("recto"))
    verso = _int_or_zero(imp.get("verso"))
    if recto <= 0 and verso <= 0:
        return ""
    total = recto + verso
    count = f"{recto}+{verso}" if verso > 0 else str(recto)
    return f"{count} {'Color' if total == 1 else 'Colors'}"


def build_ref_produit(
    fiche: Dict[str, Any],
    matieres_map: Optional[Dict[Any, Dict[str, Any]]] = None,
    *,
    abbrevs: Optional[Dict[str, str]] = None,
) -> str:
    """Compose la référence produit depuis la fiche.

    ``matieres_map`` indexe les lignes ``matieres_premieres`` par id (le format
    rendu par ``_load_matieres_map``). ``abbrevs`` permet de fournir directement
    les formes courtes ``{"frontal": ..., "adhesif": ...}`` — c'est ce que fait
    le formulaire, qui les reçoit déjà calculées par l'API.

    Retourne une chaîne vide si laize et longueur manquent : sans dimensions il
    n'y a pas de référence à composer, et mieux vaut un champ vide qu'une
    référence tronquée que l'utilisateur croirait complète.

    >>> build_ref_produit(
    ...     {"etiquette": {"laize": 105, "longueur": 148},
    ...      "impressions": True, "impressions_detail": {"recto": 1},
    ...      "bobines": {"diametre_mandrin": 40}},
    ...     abbrevs={"frontal": "Th Top-Coated", "adhesif": "Perm"})
    '105 x 148 mm Th Top-Coated Perm, 1 Color, M40 mm'
    """
    fiche = fiche or {}
    etiquette = fiche.get("etiquette") or {}
    bobines = fiche.get("bobines") or {}
    matiere = fiche.get("matiere") or {}
    mp = matieres_map or {}

    laize = format_dimension(etiquette.get("laize"))
    longueur = format_dimension(etiquette.get("longueur"))
    if not laize or not longueur:
        return ""

    def abbrev_for(kind: str, id_key: str) -> str:
        if abbrevs and abbrevs.get(kind):
            return str(abbrevs[kind]).strip()
        mid = matiere.get(id_key)
        if mid in (None, ""):
            return ""
        row = mp.get(mid) or mp.get(str(mid))
        try:
            row = row or mp.get(int(mid))
        except (TypeError, ValueError):
            pass
        return matiere_abbrev(row)

    # Segment 1 — dimensions et matières, séparés par des espaces.
    head_parts = [f"{laize} x {longueur} mm"]
    for kind, id_key in (("frontal", "frontal_id"), ("adhesif", "adhesif_id")):
        abbrev = abbrev_for(kind, id_key)
        if abbrev:
            head_parts.append(abbrev)

    # Segments suivants — séparés par des virgules, omis quand vides.
    segments = [" ".join(head_parts)]
    colors = _colors_segment(fiche)
    if colors:
        segments.append(colors)
    mandrin = format_dimension(bobines.get("diametre_mandrin"))
    if mandrin:
        segments.append(f"M{mandrin} mm")

    return ", ".join(segments)


def unique_ref(base: str, taken: Iterable[str]) -> str:
    """Rend ``base`` unique en ajoutant « (2) », « (3) »… si nécessaire.

    Comparaison insensible à la casse et aux espaces de bord, comme la contrainte
    d'unicité côté base. Deux produits qui ne diffèrent que par un champ absent
    de la référence (le client, l'échenillage) composent légitimement la même
    référence : on ne refuse pas, on numérote.
    """
    base = (base or "").strip()
    if not base:
        return ""
    used = {str(t or "").strip().lower() for t in taken}
    if base.lower() not in used:
        return base
    n = 2
    while f"{base} ({n})".lower() in used:
        n += 1
    return f"{base} ({n})"
