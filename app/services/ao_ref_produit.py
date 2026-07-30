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
# Le repli ne RÉSUME pas la désignation, il en EXTRAIT la famille de matière.
# Tout ce qui n'est pas une famille reconnue est jeté : grammage, épaisseur, code
# fournisseur, nom commercial entre parenthèses, qualificatif commercial
# (« fort », « spécial »). Une référence produit sert à identifier un produit
# chez un fournisseur, pas à recopier la fiche matière.
#
# Historique : la première version conservait les mots inconnus « pour ne rien
# perdre ». Résultat réel en production :
#   « 104 x 102 mm 62gsm Vellum Remov Fort 1408 (meltavis), 1 Color, M40 mm »
# là où on attendait :
#   « 104 x 102 mm Vellum Removable, 1 Color, M40 mm »
# Le bruit ne venait pas d'un mot mal traduit mais du principe de tout garder.
#
# Ordre significatif : les expressions les plus longues d'abord, pour que
# « top coated » soit consommé avant « coated ». Clés normalisées (minuscules,
# sans accents). Valeurs en mots entiers et non tronqués : « Removable », pas
# « Remov » — c'est un fournisseur étranger qui lit.

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
    ("vellum", "Vellum"),
    ("polypropylene", "PP"),
    ("polyethylene", "PE"),
    ("polyester", "PET"),
    # Sigles déjà en forme courte dans la désignation. Le contrôle de frontière
    # sur caractère alphanumérique évite les faux positifs : « permanent » ne
    # matche pas « pe », « pet » n'est pas coupé en « pe ».
    ("bopp", "BOPP"),
    ("pvc", "PVC"),
    ("pet", "PET"),
    ("pp", "PP"),
    ("pe", "PE"),
    ("papier", "Paper"),
    ("carton", "Board"),
    ("glassine", "Glassine"),
    # Familles d'adhésifs — le type d'adhésion, pas sa chimie ni sa force
    ("ultra removable", "Ultra Removable"),
    ("ultra enlevable", "Ultra Removable"),
    ("repositionnable", "Removable"),
    ("enlevable", "Removable"),
    ("amovible", "Removable"),
    ("removable", "Removable"),
    ("permanent", "Permanent"),
    # Spécifications fonctionnelles : elles changent le produit, on les garde
    ("congelation", "Deep-Freeze"),
    ("surgele", "Deep-Freeze"),
    ("alimentaire", "Food"),
    ("securite", "Security"),
    ("pneumatique", "Tyre"),
)

# Reconnus mais VOLONTAIREMENT jetés : chimie de l'adhésif, couleur, finition,
# intensité. Ce sont des précisions de fiche matière, pas d'identification
# produit — et c'est ce qui alourdissait la référence. Ils figurent ici, et non
# dans une simple absence du glossaire, pour deux raisons : documenter le choix,
# et empêcher le repli « premiers mots parlants » de les récupérer.
_DROPPED: frozenset[str] = frozenset({
    "acrylique", "hotmelt", "hot melt", "caoutchouc", "dispersion", "renforce",
    "fort", "forte", "extra", "special", "standard", "classique", "premium",
    "blanc", "blanche", "noir", "noire", "jaune", "rouge", "bleu", "vert",
    "argente", "argent", "dore", "or", "transparent", "brillant", "mat", "mate",
    "adhesif", "adhesive", "support", "frontal", "matiere", "etiquette",
    "silicone", "siliconne", "face", "dos", "recto", "verso", "qualite",
})

# Nombre maximum de familles conservées. Trois suffisent à identifier
# (« Th Top-Coated », « Removable », « Deep-Freeze ») ; au-delà on recopie la
# fiche matière.
_MAX_TERMS = 3

# Sigles gardés intacts par la mise en casse.
_KEEP_AS_IS = {
    "PP", "PE", "PET", "PVC", "HM", "FSC", "PEFC", "BOPP", "TC", "UV",
    "RFID", "EAN", "OTR", "MDO", "PCR",
}

# Préfixe de code article fournisseur : « 1393299 - papier jet d'encre mat 70g ».
_CODE_PREFIX_RE = re.compile(r"^\s*[\w./-]*\d{3,}[\w./-]*\s*[-–—]\s*")

# Segments entre parenthèses ou crochets : nom commercial du fabricant
# (« (meltavis) »), jamais utile dans une référence produit.
_PARENS_RE = re.compile(r"[(\[{][^)\]}]*[)\]}]")

# Grammages, épaisseurs et codes numériques : « 62gsm », « 23µm », « 1408 ».
_GRAMMAGE_RE = re.compile(r"^\d+(?:[.,]\d+)?\s*(?:g|gsm|g/m2|gr|um|µm|mic)$", re.I)
_CODE_TOKEN_RE = re.compile(r"^[\w./-]*\d[\w./-]*$")


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def _normalize(text: str) -> str:
    out = _strip_accents(str(text or "")).lower()
    out = _PARENS_RE.sub(" ", out)
    out = re.sub(r"\s+", " ", out).strip()
    # « 62 gsm » et « 23 µm » sont une seule information : on recolle l'unité au
    # nombre avant de découper en mots, sinon « gsm » ressort comme un mot isolé.
    return re.sub(r"(\d)\s+(g/m2|gsm|gr|g|µm|um|mic)\b", r"\1\2", out)


def _titlecase_token(token: str) -> str:
    """Met un mot en casse de référence, en préservant les sigles."""
    upper = token.upper()
    if upper in _KEEP_AS_IS:
        return upper
    if token.isupper() and len(token) <= 4:
        return upper
    return token[:1].upper() + token[1:]


def _is_noise(token: str) -> bool:
    """Un mot qui n'identifie pas la matière : code, grammage, qualificatif."""
    if len(token) < 3:
        return True
    if token in _DROPPED:
        return True
    if _GRAMMAGE_RE.match(token) or _CODE_TOKEN_RE.match(token):
        return True
    return False


def abbreviate_designation(designation: str) -> str:
    """Extrait la famille de matière d'une désignation française, en anglais.

    Repli utilisé seulement quand ``matieres_premieres.abbreviation`` est vide.
    Ne garde que les familles du glossaire ; grammage, code fournisseur, nom
    commercial et qualificatif sont écartés. Si aucune famille n'est reconnue, on
    retombe sur les deux premiers mots parlants — mieux qu'un champ vide, et ça
    signale à l'œil qu'une abréviation reste à saisir.

    >>> abbreviate_designation("62gsm Vellum")
    'Vellum'
    >>> abbreviate_designation("Velin adhésif permanent")
    'Vellum Permanent'
    >>> abbreviate_designation("Removable fort 1408 (Meltavis)")
    'Removable'
    >>> abbreviate_designation("Thermique Top Coated 80 g")
    'Th Top-Coated'
    >>> abbreviate_designation("Adhésif permanent acrylique")
    'Permanent'
    """
    raw = str(designation or "").strip()
    if not raw:
        return ""
    raw = _CODE_PREFIX_RE.sub("", raw)

    normalized = _normalize(raw)
    if not normalized:
        return ""

    # Consommation de gauche à droite : à chaque position, la plus longue entrée
    # du glossaire qui matche gagne. Ce qui n'est pas reconnu est mis de côté
    # comme repli éventuel, jamais concaténé au résultat.
    familles: list[str] = []
    restes: list[str] = []
    buffer: list[str] = []
    remaining = normalized
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
                restes.extend("".join(buffer).split())
                buffer = []
            familles.append(matched[1])
            remaining = remaining[len(matched[0]):].lstrip()
        else:
            buffer.append(remaining[0])
            remaining = remaining[1:]
    if buffer:
        restes.extend("".join(buffer).split())

    if familles:
        out = familles
    else:
        # Aucune famille reconnue : les deux premiers mots parlants.
        out = [_titlecase_token(w) for w in restes if not _is_noise(w)][:2]
        if not out and restes:
            # Désignation entièrement composée de codes (« XZ-9000 ») : on garde
            # le premier terme. Une référence produit sans sa matière serait plus
            # trompeuse qu'une référence portant un code brut.
            out = [_titlecase_token(restes[0])]

    # Dédoublonne en conservant l'ordre : « adhesif permanent permanent » arrive.
    seen: set[str] = set()
    deduped: list[str] = []
    for p in out:
        if not p:
            continue
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(p)
    return " ".join(deduped[:_MAX_TERMS])


def matiere_abbrev(row: Optional[Dict[str, Any]]) -> str:
    """Forme courte d'une matière, par ordre de priorité décroissante.

    1. ``abbreviation`` — exception assumée, saisie pour forcer un libellé sur
       cette matière précise et rien d'autre.
    2. ``sous_categorie_en`` — la source normale. La référence produit part chez
       des fournisseurs étrangers : c'est la version anglaise qui doit y figurer
       (« Vellum », « Removable »), pas la française.
    3. ``sous_categorie`` — le libellé français, si l'anglais n'a pas été saisi.
       Mieux que rien, et visible à l'œil comme une traduction à compléter.
    4. ``abbreviate_designation()`` — dernier repli, déduit de la désignation.
       Approximatif par nature ; il ne sert qu'aux matières pas encore classées.

    Ne pas confondre ``sous_categorie`` avec ``sous_section`` : la seconde pilote
    les pastilles de navigation de MyStock et n'entre pas dans les références.
    """
    if not row:
        return ""
    for champ in ("abbreviation", "sous_categorie_en", "sous_categorie"):
        valeur = str(row.get(champ) or "").strip()
        if valeur:
            return valeur
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
