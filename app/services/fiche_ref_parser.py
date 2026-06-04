"""
Parser de libellés de fiches techniques.

Les références de fiches techniques sont historiquement saisies sous la forme:

    "1013/0068"                       (cas simple, pas de variante)
    "1013/0068 - COHESIO 1"           (variante machine)
    "1013/0249 - L510"                (variante laize)
    "1027/0005 - COHESIO 2 - L570"    (variante machine + laize)
    "1153/0005 - Box de 510 000"      (variante conditionnement)
    "1153/0005 - Box de 510 000 - L570"  (variante conditionnement + laize)
    "1004/0128-COHESIO1"              (séparateur collé)

Ce module extrait une clé normalisée `ref_produit_norm` (XXX/NNNN, le n°
produit avec 4 chiffres après le slash) et catégorise les variantes en
trois dimensions structurées : machine, laize_mm, conditionnement.

Cette normalisation permet la jointure fiche ↔ dossier produit
(`planning_entries.ref_produit`), sans dépendre du libellé textuel.
"""

from __future__ import annotations

import re
from typing import Optional, TypedDict


# ─── Référentiels ────────────────────────────────────────────────────

# Libellés machine canoniques (alignés avec config.MACHINES côté UI).
MACHINE_CANON = {
    "cohesio1":  "Cohésio 1",
    "cohesio 1": "Cohésio 1",
    "co1":       "Cohésio 1",
    "cohesio2":  "Cohésio 2",
    "cohesio 2": "Cohésio 2",
    "co2":       "Cohésio 2",
    "dsi":       "DSI",
    "repiquage": "Repiquage",
}

# Patterns machines reconnus dans un libellé libre.
_MACHINE_RE = re.compile(
    r"\b(?:COH[EÉ]SIO\s*0*(1|2)|CO\s*0*(1|2)|DSI|REPIQUAGE)\b",
    re.IGNORECASE,
)

# Laize : "L510", "L 510", "Laize 320 mm", "Laize 470", "laize 333mm"…
_LAIZE_RE = re.compile(
    r"\b(?:L\s*(\d{3})\b|LAIZE\s+(\d{3})\s*(?:MM)?\b)",
    re.IGNORECASE,
)

# Conditionnement libre (fragment normalisé, casse uniforme).
_COND_PATTERNS = (
    (re.compile(r"\bBOX\s+DE\s+([\d  ]+)\b", re.IGNORECASE),
        lambda m: f"Box de {re.sub(r'[  ]+', ' ', m.group(1)).strip()}"),
    (re.compile(r"\bCARTON\s+DE\s+(\d+)\s+BOBINES?\b", re.IGNORECASE),
        lambda m: f"Carton de {m.group(1)} bobines"),
    (re.compile(r"\bPALETTE\s+BOX\b", re.IGNORECASE),
        lambda m: "Palette box"),
)

# Préfixe XXX/NNNN au début de la chaîne, tolère espace ou tiret comme séparateur.
_REF_PREFIX_RE = re.compile(r"^\s*(\d{1,5})\s*/\s*(\d{1,5})")


# ─── API publique ────────────────────────────────────────────────────


class FicheRefParsed(TypedDict, total=False):
    ref_produit_norm: Optional[str]
    machine: Optional[str]
    laize_mm: Optional[int]
    conditionnement_norm: Optional[str]


def normalize_ref_produit(value: str | None) -> Optional[str]:
    """
    Extrait la clé produit normalisée d'une chaîne quelconque.

    Retourne "XXX/NNNN" (avec NNNN sur 4 chiffres min, sans zéros en trop
    devant la partie famille) ou None si aucune référence valide n'est
    trouvée. Tolère "1315-0004" et "690-0041" (tiret au lieu du slash).
    """
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    # tolère le tiret comme séparateur famille/numéro
    m = re.match(r"^\s*(\d{1,5})\s*[/\-]\s*(\d{1,5})", s)
    if not m:
        return None
    famille = str(int(m.group(1)))  # supprime zéros initiaux superflus
    numero = m.group(2)
    # pad à 4 chiffres si c'est un nombre court (convention SIFA),
    # sinon garde la longueur d'origine (déjà 4+).
    if len(numero) < 4:
        numero = numero.zfill(4)
    return f"{famille}/{numero}"


def parse_fiche_reference(reference: str | None) -> FicheRefParsed:
    """
    Parse une référence fiche technique brute et extrait les 4 dimensions:
      - ref_produit_norm : "1013/0068"
      - machine          : "Cohésio 1" | "Cohésio 2" | "DSI" | "Repiquage" | None
      - laize_mm         : 320 | 333 | 440 | 470 | 510 | 570 | … | None
      - conditionnement_norm : texte normalisé ou None

    Ne lève jamais : retourne `{}` si la chaîne est inexploitable.
    """
    out: FicheRefParsed = {
        "ref_produit_norm": None,
        "machine": None,
        "laize_mm": None,
        "conditionnement_norm": None,
    }
    if not reference:
        return out
    s = str(reference).strip()
    if not s:
        return out

    out["ref_produit_norm"] = normalize_ref_produit(s)

    # tout ce qui suit le premier séparateur " - " (ou collé) est variante
    m = _REF_PREFIX_RE.match(s)
    suffix = s[m.end():] if m else s
    # nettoie un éventuel "-" ou " - " collé après le numéro
    suffix = re.sub(r"^\s*[-–—]\s*", "", suffix).strip()

    if suffix:
        out["machine"] = _extract_machine(suffix)
        out["laize_mm"] = _extract_laize(suffix)
        out["conditionnement_norm"] = _extract_conditionnement(suffix)

    return out


# ─── Helpers internes ────────────────────────────────────────────────


def _extract_machine(text: str) -> Optional[str]:
    m = _MACHINE_RE.search(text)
    if not m:
        return None
    raw = m.group(0).lower().replace(" ", "")
    # normalise "cohesio01" → "cohesio1"
    raw = re.sub(r"0+(\d)", r"\1", raw)
    return MACHINE_CANON.get(raw) or MACHINE_CANON.get(raw.replace("é", "e"))


def _extract_laize(text: str) -> Optional[int]:
    m = _LAIZE_RE.search(text)
    if not m:
        return None
    val = m.group(1) or m.group(2)
    try:
        n = int(val)
    except (TypeError, ValueError):
        return None
    # garde-fou : laize plausible (entre 100 et 999 mm)
    if 100 <= n <= 999:
        return n
    return None


def _extract_conditionnement(text: str) -> Optional[str]:
    for pat, fmt in _COND_PATTERNS:
        m = pat.search(text)
        if m:
            try:
                return fmt(m)
            except Exception:
                return None
    return None


# ─── Self-test simple ────────────────────────────────────────────────

if __name__ == "__main__":
    samples = [
        "1013/0068 - COHESIO 1",
        "1013/0068 - COHESIO2",
        "1013/0249 - L510",
        "1027/0005 - COHESIO 2 - L570",
        "1153/0005 - Box de 510 000",
        "1153/0005 - Box de 510 000 - L570",
        "1004/0128-COHESIO1",
        "1153/0004 - Carton de 4 bobines",
        "1004/0078 - Laize 333 mm",
        "83/0005 PALETTE BOX",
        "1183/0027 - CO1",
        "1315-0004",
        "1050/0001",
    ]
    for s in samples:
        print(f"{s!r:55} → {parse_fiche_reference(s)}")
