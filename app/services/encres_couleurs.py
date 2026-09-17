"""Couleurs d'encre — désignation saisie à l'atelier → teinte écran.

Le référentiel vit dans la table ``encres_couleurs`` (Paramètres › Fabrication
› Impression). Ce module ne contient que la logique de rapprochement, sans
aucune valeur métier : il prend une connexion sqlite et rien d'autre, ce qui
permet de le tester sur une base en mémoire.

Les désignations réelles sont très irrégulières — relevé des fiches
techniques du 17/09/2026 : « P.485 C », « P 485C », « 485 C », « P485 »,
« P.286 C BLEU », « JAUNE P 135U », « P.BLACKU », « RED 032 ». Le
rapprochement réduit donc chaque désignation à une clé canonique :

- une référence numérique → « 485 C » (suffixe C couché / U non couché) ;
- sinon un nom → « BLACK C », « BLEU CLAIR ».

Sans suffixe, on essaie C puis U. Une référence connue seulement dans l'autre
finition est acceptée en dernier recours : la teinte n'est qu'indicative et un
486 U affiché comme un 486 C vaut mieux qu'une zone violette.

La teinte est une approximation écran, jamais une référence d'impression.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from typing import Dict, Iterable, List, Optional

_HEX = re.compile(r"^#[0-9A-F]{6}$")
# Une reference Pantone : 3 ou 4 chiffres, suffixe C/U facultatif. Un nombre
# suivi de « % » est un taux (« APLAT 100% »), pas une encre.
_NUM = re.compile(r"(?<![0-9])(\d{3,4})(?!\s*%)\s*[-.]?\s*([CU])?(?![0-9A-Z])")
# Abreviations relevees dans les fiches : « P PROC. BLUE C », « P. RUB.RED C ».
_ABREV = {"PROC": "PROCESS", "RUB": "RUBINE", "RHOD": "RHODAMINE",
          "REFL": "REFLEX", "GREY": "GRAY"}
_PREFIXE = re.compile(r"^(?:PANTONE|PMS|P)(?:\s+|[.\-]\s*|(?=\d))")


def _norm(texte: str) -> str:
    """Majuscules, sans accents, espaces et ponctuation réduits."""
    s = unicodedata.normalize("NFKD", str(texte or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).upper()
    s = re.sub(r"[().,/]", " ", s)
    # « APLAT ROSE » : l'aplat est une facon d'imprimer, pas une couleur.
    s = re.sub(r"\bPANTONE\b|\bPMS\b|\bAPLAT\b", " ", s)
    s = re.sub(r"\b(%s)\b" % "|".join(_ABREV), lambda m: _ABREV[m.group(1)], s)
    return re.sub(r"\s+", " ", s).strip()


def normaliser_hex(valeur: str) -> Optional[str]:
    """'#fd0' → '#FFDD00' ; valeur invalide → None."""
    s = str(valeur or "").strip().upper()
    if not s.startswith("#"):
        s = "#" + s
    if re.fullmatch(r"#[0-9A-F]{3}", s):
        s = "#" + "".join(c * 2 for c in s[1:])
    return s if _HEX.match(s) else None


def _num(n: str) -> str:
    # Les zeros de tete sont garde tels quels : 032, 012, 0631 sont des
    # references distinctes chez Pantone (0631 = Violet 0631, pas 631).
    return n


def cle(code: str) -> str:
    """Clé canonique d'un code saisi dans le référentiel."""
    s = _norm(code)
    m = _NUM.search(s)
    if m:
        return f"{_num(m.group(1))} {m.group(2) or 'C'}"
    s = _PREFIXE.sub("", s).strip()
    m = re.fullmatch(r"(.+?)\s+([CU])", s)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return s


def candidats(designation: str, noms: Iterable[str] = ()) -> List[str]:
    """Clés à essayer, de la plus exacte à la plus approximative.

    ``noms`` : les noms (sans suffixe) présents dans le référentiel, pour
    reconnaître un suffixe collé (« BLACKU »).
    """
    s = _norm(designation)
    if not s:
        return []
    out: List[str] = []

    def add(k: str) -> None:
        if k and k not in out:
            out.append(k)

    m = _NUM.search(s)
    if m:
        n, suf = _num(m.group(1)), m.group(2)
        if suf:
            add(f"{n} {suf}")
            add(f"{n} {'U' if suf == 'C' else 'C'}")
        else:
            add(f"{n} C")
            add(f"{n} U")
        return out

    add(s)
    nom = _PREFIXE.sub("", s).strip()
    m = re.fullmatch(r"(.+?)\s+([CU])", nom)
    if m:
        base, suf = m.group(1), m.group(2)
    elif len(nom) > 1 and nom[-1] in "CU" and nom[:-1] in set(noms):
        base, suf = nom[:-1], nom[-1]
    else:
        base, suf = nom, None
    if suf:
        add(f"{base} {suf}")
        add(f"{base} {'U' if suf == 'C' else 'C'}")
    else:
        add(base)
        add(f"{base} C")
        add(f"{base} U")
    # Dernier recours : le premier mot (« ROSE FUSHIA » → « ROSE »,
    # « NOIR VERSO » → « NOIR »).
    mots = base.split()
    if len(mots) > 1:
        add(mots[0])
        add(f"{mots[0]} C")
    return out


def charger(conn: sqlite3.Connection) -> Dict[str, str]:
    """Référentiel actif {clé: hex}. Table absente → dictionnaire vide."""
    try:
        rows = conn.execute(
            "SELECT cle, hex FROM encres_couleurs WHERE actif=1"
        ).fetchall()
    except sqlite3.Error:
        return {}
    return {r[0]: r[1] for r in rows if r[0] and r[1]}


def resoudre(designation: str, encres: Dict[str, str]) -> Optional[str]:
    """Teinte d'une désignation, ou None si le référentiel ne la connaît pas."""
    if not encres or not designation:
        return None
    direct = normaliser_hex(designation) if str(designation).strip().startswith("#") else None
    if direct:
        return direct
    noms = {k[:-2] for k in encres if k[-2:] in (" C", " U")}
    for k in candidats(designation, noms):
        if k in encres:
            return encres[k]
    return None
