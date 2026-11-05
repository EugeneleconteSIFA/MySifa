"""
MyTools › Étiquettes — vérification d'une impression par scan.

Une lecture (caméra, douchette, vérificateur ISO branché en émulation clavier
ou en série) est ramenée à une forme comparable (préfixe AIM, séparateurs GS,
parenthèses GS1 retirés) puis comparée aux codes attendus de l'impression.
Un vérificateur ISO/IEC 15415-15416 ajoute sa note (A à F) : elle est
séparée de la donnée et consignée. Module pur.
"""

from __future__ import annotations

import re
from typing import Any, Optional


_AIM_RE = re.compile(r"^\][A-Za-z][0-9A-Za-z]")


def normaliser_lecture(s: str) -> str:
    """Lecture scanner → forme comparable : préfixe AIM (]C1, ]d2, ]Q3…),
    séparateurs GS, FNC1 et parenthèses retirés, espaces de bord coupés."""
    s = str(s or "").strip()
    s = _AIM_RE.sub("", s)
    s = s.replace("\x1d", "").replace("\xf1", "").replace("\u241d", "")
    if s.startswith("("):
        from app.services.etiq_zpl import _gs1_avec_separateur
        s = _gs1_avec_separateur(s, "")
    return s.strip()


def verifier_lecture(lu: str, attendus: list) -> dict:
    """Compare une lecture aux codes attendus d'une impression."""
    n = normaliser_lecture(lu)
    for a in attendus or []:
        if normaliser_lecture(a.get("donnee")) == n and n:
            return {"statut": "ok", "index": a.get("index"), "element": a.get("element"), "lu": n}
    proche = None
    if attendus:
        proche = min(attendus, key=lambda a: _distance(n, normaliser_lecture(a.get("donnee"))))
    return {"statut": "ecart", "lu": n, "attendu": proche.get("donnee") if proche else None,
            "element": proche.get("element") if proche else None}


def _distance(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a[:200], 1):
        cur = [i]
        for j, cb in enumerate(b[:200], 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


_NOTE_RE = re.compile(r"(?:grade|note|iso\s*1541[56]|ansi)\s*[:=]?\s*([A-F]|[0-4](?:[.,]\d+)?)(?![\w.,])", re.I)


def note_iso(v: Any) -> Optional[str]:
    """Note de vérification ISO/IEC 15415-15416 en lettre (A, B, C, D, F),
    depuis une lettre ou une note chiffrée 0-4 (A ≥ 3,5 ; B ≥ 2,5 ; C ≥ 1,5 ;
    D ≥ 0,5 ; F en dessous)."""
    t = str(v or "").strip().upper().replace(",", ".")
    if not t:
        return None
    if t in ("A", "B", "C", "D", "F"):
        return t
    if t == "E":
        return "F"
    try:
        n = float(t)
    except ValueError:
        return None
    if not 0 <= n <= 4:
        return None
    return "A" if n >= 3.5 else "B" if n >= 2.5 else "C" if n >= 1.5 else "D" if n >= 0.5 else "F"


def lecture_verificateur(lu: str) -> tuple:
    """Sépare la donnée lue et la note ISO dans la sortie d'un vérificateur
    branché en émulation clavier ou en série : « Grade: B », « ISO15416 3.2 »,
    ou la note en dernier champ après une tabulation. (donnée, note|None)."""
    s = str(lu or "")
    m = _NOTE_RE.search(s)
    if m:
        note = note_iso(m.group(1))
        reste = (s[:m.start()] + " " + s[m.end():]).strip(" \t;|,")
        return reste.strip(), note
    if "\t" in s:
        champs = [c for c in s.split("\t")]
        dernier = champs[-1].strip()
        if note_iso(dernier) and len(dernier) <= 4:
            return "\t".join(champs[:-1]).strip(), note_iso(dernier)
    return s.strip(), None
