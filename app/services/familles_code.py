"""Familles de codes-barres bobine : la forme d'un code désigne son fournisseur.

Pourquoi des familles déclarées, en plus des signatures apprises
----------------------------------------------------------------
`origine_bobine` apprend la forme des codes à partir de ce que l'atelier a
déclaré. Relevé du 17/09/2026 : la famille `R1101-…` comptait 30 Likexin,
1 Sato et 1 Shine ; les codes Kanzan (11 chiffres, préfixe 60) avaient été
déclarés deux fois Burgo. Une mémoire nourrie par des déclarations
contradictoires n'ose plus rien proposer. Une famille, elle, est une règle
posée une fois en Paramètres et vérifiée avec l'atelier : elle passe devant
l'historique et tranche.

Elle reste DÉCLARATIVE : seule une réception démontre l'origine d'une bobine,
une famille n'apporte jamais de preuve FSC (`demontre` reste faux).

Syntaxe des masques
-------------------
    #   un chiffre
    ?   un caractère quelconque
    *   n'importe quelle suite (y compris vide)
    tout autre caractère : lui-même, sans tenir compte de la casse

Le masque le plus précis gagne (nombre de caractères littéraux et de `#`).

Laize
-----
`laize_segment` : pour une famille dont un bloc du code (séparés par `-`)
porte la laize en mm, le rang de ce bloc (1 = premier). Le bloc n'est lu que
si le code a au moins `laize_blocs_min` blocs — `R1101-SGD26020324-16` n'a
pas de laize, `R1001-26031387-510-13` en a une.

Normalisation
-------------
Artefacts de scan relevés en production, corrigés seulement quand le code
corrigé tombe dans une famille (jamais à l'aveugle) :
- un chiffre parasite devant le code (`7R1101-…`) ;
- des points à la place des tirets (`R1101.SGD…`) ;
- un code lu deux fois d'affilée (`125460462103125460462103`).
Un code trop court ou manifestement de test est signalé, pas refusé.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

_PARIS = ZoneInfo("Europe/Paris")
LONGUEUR_MIN = 8
CODES_TEST = {"TEST", "123123", "123456", "123456789", "123654789"}


def _maintenant() -> str:
    return datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")


def _table_existe(conn) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='bobine_familles_code'"
    ).fetchone())


def masque_regex(masque: str) -> re.Pattern:
    out = []
    for ch in str(masque or ""):
        if ch == "#":
            out.append(r"\d")
        elif ch == "?":
            out.append(".")
        elif ch == "*":
            out.append(".*")
        else:
            out.append(re.escape(ch))
    return re.compile("^" + "".join(out) + "$", re.IGNORECASE)


def precision(masque: str) -> int:
    return sum(1 for ch in str(masque or "") if ch not in "?*")


def valider_masque(masque: str) -> str:
    m = str(masque or "").strip()
    if not m:
        raise ValueError("Masque requis.")
    if len(m) > 40:
        raise ValueError("Masque trop long — 40 caractères au plus.")
    if precision(m) < 3:
        raise ValueError("Masque trop large — au moins 3 caractères ou chiffres fixés.")
    return m


# ── Référentiel ──────────────────────────────────────────────────────────────

def familles(conn, actives_seulement: bool = False) -> List[Dict[str, Any]]:
    if not _table_existe(conn):
        return []
    sql = """SELECT fc.*, f.nom AS fournisseur, f.licence AS licence
               FROM bobine_familles_code fc
          LEFT JOIN fournisseurs_fsc f ON f.id = fc.fournisseur_id"""
    if actives_seulement:
        sql += " WHERE fc.actif = 1"
    sql += " ORDER BY lower(COALESCE(f.nom,'')), fc.masque"
    return [dict(r) for r in conn.execute(sql).fetchall()]


def enregistrer(conn, body: Dict[str, Any], par: str,
                famille_id: Optional[int] = None) -> Dict[str, Any]:
    try:
        fid = int(body.get("fournisseur_id"))
    except (TypeError, ValueError):
        raise ValueError("Fournisseur requis.")
    if not conn.execute("SELECT 1 FROM fournisseurs_fsc WHERE id=?", (fid,)).fetchone():
        raise ValueError("Fournisseur introuvable.")
    masque = valider_masque(body.get("masque"))
    seg = body.get("laize_segment")
    try:
        seg = int(seg) if seg not in (None, "", 0, "0") else None
    except (TypeError, ValueError):
        raise ValueError("Rang du bloc laize invalide.")
    if seg is not None and not 1 <= seg <= 10:
        raise ValueError("Rang du bloc laize entre 1 et 10.")
    try:
        blocs_min = int(body.get("laize_blocs_min") or 0) or None
    except (TypeError, ValueError):
        blocs_min = None
    note = (str(body.get("note") or "").strip()[:200]) or None
    actif = 1 if body.get("actif", 1) else 0
    quand = _maintenant()
    doublon = conn.execute(
        "SELECT id FROM bobine_familles_code WHERE upper(masque)=upper(?)", (masque,)
    ).fetchone()
    if doublon and (famille_id is None or int(doublon["id"]) != int(famille_id)):
        raise ValueError("Ce masque existe déjà.")
    if famille_id:
        cur = conn.execute(
            """UPDATE bobine_familles_code
                  SET fournisseur_id=?, masque=?, laize_segment=?, laize_blocs_min=?,
                      note=?, actif=?, updated_at=?, updated_by=?
                WHERE id=?""",
            (fid, masque, seg, blocs_min, note, actif, quand, par, int(famille_id)),
        )
        if not cur.rowcount:
            raise LookupError("Famille introuvable.")
        rid = int(famille_id)
    else:
        rid = conn.execute(
            """INSERT INTO bobine_familles_code
                   (fournisseur_id, masque, laize_segment, laize_blocs_min, note, actif,
                    created_at, updated_at, updated_by)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (fid, masque, seg, blocs_min, note, actif, quand, quand, par),
        ).lastrowid
    return next(f for f in familles(conn) if f["id"] == rid)


def supprimer(conn, famille_id: int) -> bool:
    return bool(conn.execute(
        "DELETE FROM bobine_familles_code WHERE id=?", (int(famille_id),)
    ).rowcount)


# ── Reconnaissance ───────────────────────────────────────────────────────────

def _correspond(code: str, liste: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    meilleure, score = None, -1
    for f in liste:
        if masque_regex(f["masque"]).match(code):
            p = precision(f["masque"])
            if p > score:
                meilleure, score = f, p
    return meilleure


def laize_mm(code: str, famille: Optional[Dict[str, Any]]) -> Optional[int]:
    if not famille or not famille.get("laize_segment"):
        return None
    blocs = [b for b in re.split(r"[-._/ ]+", code or "") if b]
    rang = int(famille["laize_segment"])
    if len(blocs) < max(rang, int(famille.get("laize_blocs_min") or 0)):
        return None
    bloc = blocs[rang - 1]
    return int(bloc) if bloc.isdigit() and 50 <= int(bloc) <= 3000 else None


def normaliser(code: str, liste: Optional[List[Dict[str, Any]]] = None,
               conn=None) -> Tuple[str, List[str]]:
    """Le code corrigé et ce qui a été corrigé ou signalé."""
    brut = (code or "").strip()
    notes: List[str] = []
    if not brut:
        return brut, notes
    if liste is None:
        liste = familles(conn, actives_seulement=True) if conn is not None else []

    if brut.upper() in CODES_TEST or len(brut) < LONGUEUR_MIN:
        notes.append("Code suspect : trop court ou code de test.")
        return brut, notes
    if not liste or _correspond(brut, liste):
        return brut, notes

    candidats = []
    moitie = len(brut) // 2
    if len(brut) % 2 == 0 and brut[:moitie] == brut[moitie:]:
        candidats.append((brut[:moitie], "Code lu deux fois : une seule lecture gardée."))
    if "." in brut:
        candidats.append((brut.replace(".", "-"), "Points remplacés par des tirets."))
    if len(brut) > LONGUEUR_MIN and brut[0].isdigit() and not brut[1:2].isdigit():
        candidats.append((brut[1:], "Chiffre parasite retiré en tête du code."))
    for neuf, note in candidats:
        if _correspond(neuf, liste):
            notes.append(note)
            return neuf, notes
    return brut, notes


def reconnaitre(conn, code: str) -> Optional[Dict[str, Any]]:
    """La famille d'un code (déjà normalisé), avec fournisseur et laize."""
    liste = familles(conn, actives_seulement=True)
    f = _correspond((code or "").strip(), liste)
    if not f or not f.get("fournisseur"):
        return None
    return {
        "famille_id": f["id"], "masque": f["masque"],
        "fournisseur_id": f["fournisseur_id"], "fournisseur": f["fournisseur"],
        "licence": f.get("licence") or "",
        "laize_mm": laize_mm(code, f),
    }
