"""
Étiquettes spécifiques — GS1 : identifiants d'application (AI), contrôle des
données, étiquette logistique palette.

Miroir de la partie GS1 de `static/mysifa_etiq_moteur.js` (mêmes règles, mêmes
messages). Les données d'un GS1-128 ou d'un GS1 DataMatrix s'écrivent avec les
AI entre parenthèses : « (00)330123450000000017(02)03012345000017(37)24 ».

Le préfixe entreprise GS1 vient de config.py (ETIQ_GS1_PREFIXE, .env) : rien
de propre à SIFA n'est écrit ici.
"""

from __future__ import annotations

import re
from datetime import date

from app.services.etiq_specifiques import cle_gs1

# AI pris en charge : (libellé de la zone en clair, longueur fixe ou None,
# longueur max, contenu : n = chiffres, an = alphanumérique, contrôle de clé)
AI = {
    "00": ("SSCC", 18, 18, "n", True),
    "01": ("GTIN", 14, 14, "n", True),
    "02": ("CONTENT", 14, 14, "n", True),
    "10": ("BATCH/LOT", None, 20, "an", False),
    "11": ("PROD DATE", 6, 6, "date", False),
    "15": ("BEST BEFORE", 6, 6, "date", False),
    "17": ("USE BY", 6, 6, "date", False),
    "21": ("SERIAL", None, 20, "an", False),
    "37": ("COUNT", None, 8, "n", False),
    "400": ("ORDER NUMBER", None, 30, "an", False),
    "420": ("SHIP TO POST", None, 20, "an", False),
}
# 310x poids net (kg) et 330x poids brut (kg), x = nombre de décimales.
for _x in range(6):
    AI[f"310{_x}"] = ("NET WEIGHT (kg)", 6, 6, "n", False)
    AI[f"330{_x}"] = ("GROSS WEIGHT (kg)", 6, 6, "n", False)

# Spécifications GS1 de l'étiquette logistique (GS1 General Specifications,
# section 5.4 et 6.6) : dimension X du GS1-128 entre 0,495 et 1,016 mm,
# hauteur des barres d'au moins 31,75 mm, zones de silence de 10 X.
LOGISTIQUE_X_MIN_MM = 0.495
LOGISTIQUE_X_MAX_MM = 1.016
LOGISTIQUE_HAUTEUR_MIN_MM = 31.75

_AI_RE = re.compile(r"\((\d{2,4})\)([^(]*)")


def decouper(valeur: str) -> list[tuple[str, str]]:
    """« (00)123…(10)LOT » → [("00", "123…"), ("10", "LOT")]."""
    return [(a, d) for a, d in _AI_RE.findall(re.sub(r"\s+", "", valeur or ""))]


def _date_ok(s: str) -> bool:
    if not re.fullmatch(r"\d{6}", s):
        return False
    a, m, j = 2000 + int(s[:2]), int(s[2:4]), int(s[4:])
    if not 1 <= m <= 12:
        return False
    if j == 0:   # « 00 » = fin de mois, admis par GS1
        return True
    try:
        date(a, m, j)
        return True
    except ValueError:
        return False


def controler(valeur: str) -> list[str]:
    """Erreurs bloquantes d'une chaîne GS1 (vide = conforme)."""
    groupes = decouper(valeur)
    if not groupes:
        return ["Aucun identifiant d'application — écrire les AI entre parenthèses, ex. (00)…"]
    out = []
    for ai, data in groupes:
        if ai not in AI:
            out.append(f"AI ({ai}) non pris en charge.")
            continue
        lib, fixe, maxi, typ, cle = AI[ai]
        if not data:
            out.append(f"AI ({ai}) {lib} : donnée vide.")
            continue
        if typ in ("n", "date") and not data.isdigit():
            out.append(f"AI ({ai}) {lib} : chiffres uniquement.")
            continue
        if fixe and len(data) != fixe:
            out.append(f"AI ({ai}) {lib} : {fixe} chiffres attendus, {len(data)} reçus.")
            continue
        if len(data) > maxi:
            out.append(f"AI ({ai}) {lib} : {maxi} caractères au plus.")
            continue
        if typ == "date" and not _date_ok(data):
            out.append(f"AI ({ai}) {lib} : date AAMMJJ invalide ({data}).")
        if cle and cle_gs1(data[:-1]) != data[-1]:
            out.append(f"AI ({ai}) {lib} : clé de contrôle fausse (attendu {cle_gs1(data[:-1])}).")
    if groupes and groupes[0][0] != "00" and any(a == "00" for a, _ in groupes):
        out.append("Le SSCC (00) se place en tête de son code-barres.")
    return out


def texte_clair(valeur: str) -> str:
    """Zone en clair sous le code : un groupe « (AI)donnée » par AI, séparés
    d'une espace."""
    return " ".join(f"({a}){d}" for a, d in decouper(valeur))


def poids_310x(kg, decimales: int = 2) -> str:
    """Poids en kg → 6 chiffres de l'AI 310x (x = décimales)."""
    v = round(float(str(kg).replace(",", ".")) * (10 ** decimales))
    if v < 0 or v > 999999:
        raise ValueError("Poids hors plage de l'AI 310x.")
    return f"{int(v):06d}"
