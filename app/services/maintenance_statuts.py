"""Statuts de maintenance périodique, calculés côté serveur.

Compteurs de l'accueil Maintenance (« En retard », « Dû bientôt », « À jour »,
« Jamais saisi ») pour une machine et une catégorie. Ils servent au widget
d'accueil `maintenance.statuts`, qui n'a plus à charger la page.

Ce module est la traduction exacte du calcul de la page
(app/web/maintenance_page.py) :

  _parseFrequenceDays, _normalizeFreqStr  → parse_frequence_jours
  _maintComputeStatus                     → statut
  _lastInterventionFor                    → derniere_par_libelle
  _lastInterventionForCode                → derniere_par_code
  loadOpsTypes (filtre + normalisation)   → _operations
  renderMaintCards / _wearPartsCounts     → compter

Les fonctions de base sont rejouées contre le JavaScript de la page par
tests/test_maintenance_statuts.py : modifier une règle d'un côté sans l'autre
fait échouer la CI.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from zoneinfo import ZoneInfo

from config import FUSEAU_HORAIRE

CATEGORIES = ("entretien", "remplacements", "all")
# Catégorie affichée par défaut sur la page (getMaintCatFilter).
CATEGORIE_DEFAUT = "entretien"
STATUTS = ("overdue", "soon", "ok", "never", "unknown")


# ── Règles de base ────────────────────────────────────────────────────────

def _normaliser(s) -> str:
    # Comme la page : minuscules, puis accents retirés (plage U+0300–U+036F).
    s = unicodedata.normalize("NFD", str(s or "").lower())
    return re.sub("[\u0300-\u036f]", "", s).strip()


def parse_frequence_jours(freq) -> int | None:
    """Intervalle en jours depuis un texte libre (« Hebdomadaire », « 3 mois »)."""
    s = _normaliser(freq)
    if not s:
        return None
    if re.search(r"quotid|journal|daily", s):
        return 1
    if re.search(r"(bi[\s-]?hebdo|14\s*j|2\s*sem)", s):
        return 14
    if re.search(r"hebdo|weekly|7\s*j", s):
        return 7
    if re.search(r"(bi[\s-]?mensuel|2\s*mois)", s):
        return 60
    if re.search(r"(trimestr|quarter|3\s*mois|90\s*j)", s):
        return 90
    if re.search(r"(semestr|6\s*mois|180\s*j)", s):
        return 180
    if re.search(r"(bi[\s-]?annuel|biennal|2\s*ans?|730\s*j)", s):
        return 730
    if re.search(r"(annuel|annual|yearly|365\s*j|1\s*an)", s):
        return 365
    if re.search(r"mensuel|monthly|30\s*j", s):
        return 30
    m = re.search(r"(\d+)\s*j(?:our)?", s)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*sem", s)
    if m:
        return int(m.group(1)) * 7
    m = re.search(r"(\d+)\s*mois", s)
    if m:
        return int(m.group(1)) * 30
    m = re.search(r"(\d+)\s*an", s)
    if m:
        return int(m.group(1)) * 365
    return None


def statut(freq_jours: int | None, jours_depuis: int | None) -> str:
    """overdue au-delà de l'intervalle, soon à partir de 80 %, sinon ok."""
    if freq_jours is None or freq_jours <= 0:
        return "unknown"
    if jours_depuis is None:
        return "never"
    ratio = jours_depuis / freq_jours
    if ratio > 1:
        return "overdue"
    if ratio >= 0.8:
        return "soon"
    return "ok"


def _machine_correspond(champ, machine: str) -> bool:
    # Une saisie peut viser plusieurs machines (« Cohésio 1 · Cohésio 2 »).
    s = str(champ or "").lower().strip()
    m = machine.lower().strip()
    return (s == m
            or m in [x.strip() for x in s.split("·")]
            or m in [x.strip() for x in s.split(",")])


def derniere_par_libelle(libelle, machine, historique) -> str | None:
    if not libelle or not machine or not isinstance(historique, list):
        return None
    lib = str(libelle).lower().strip()
    derniere = None
    for it in historique:
        if not it:
            continue
        if str(it.get("type") or "").lower().strip() == lib and _machine_correspond(it.get("machine"), machine):
            d = it.get("date_saisie")
            if d and (derniere is None or d > derniere):
                derniere = d
    return derniere


def derniere_par_code(code, libelle, machine, historique) -> str | None:
    """Par code (pièces d'usure) ; repli sur le libellé seulement si aucune
    ligne de l'historique ne porte de code."""
    if not code or not machine or not isinstance(historique, list):
        return None
    code = str(code)
    derniere, code_vu = None, False
    for it in historique:
        if not it or it.get("code") in (None, ""):
            continue
        code_vu = True
        if str(it.get("code")) != code or not _machine_correspond(it.get("machine"), machine):
            continue
        d = it.get("date_saisie")
        if d and (derniere is None or d > derniere):
            derniere = d
    if derniere is None and not code_vu:
        return derniere_par_libelle(libelle, machine, historique)
    return derniere


def jours_depuis(iso, aujourdhui: date) -> int | None:
    """Jours calendaires entre la date d'une saisie et aujourd'hui."""
    if not iso:
        return None
    try:
        return (aujourdhui - date.fromisoformat(str(iso)[:10])).days
    except ValueError:
        return None


# ── Lecture des référentiels ─────────────────────────────────────────────

def _categorie_normale(c) -> str:
    if c == "remplacements":
        return "remplacements"
    if c in ("entretien", "interventions", "suivi"):
        return "entretien"
    return "controles"


def _operations(codes: list[dict]) -> list[dict]:
    """Codes retenus par l'accueil Maintenance (loadOpsTypes)."""
    out = []
    for it in codes:
        cat = _categorie_normale(it.get("categorie"))
        retenu = (it.get("usure_piece_id") is not None
                  or cat in ("entretien", "remplacements")
                  or (cat == "controles" and bool(it.get("periodique"))))
        if not retenu:
            continue
        out.append({
            "code": it["code"],
            "libelle": it.get("label") or "",
            "categorie": cat,
            "periodique": bool(it.get("periodique")),
            "intervalle": str(it.get("intervalle") or ""),
            "usure_piece_id": it.get("usure_piece_id"),
            "usure_position": str(it.get("usure_position") or ""),
        })
    return out


def _pieces(conn) -> list[dict]:
    """Pièces d'usure actives et leurs positions (GET /api/maintenance/usure-pieces)."""
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='maintenance_usure_pieces'"
    ).fetchone():
        return []
    pieces = []
    for r in conn.execute(
        "SELECT id FROM maintenance_usure_pieces WHERE actif = 1 ORDER BY ordre ASC, label ASC"
    ).fetchall():
        positions = [p["pos"] for p in conn.execute(
            """SELECT DISTINCT COALESCE(usure_position,'') AS pos
               FROM maintenance_codes
               WHERE usure_piece_id=? AND COALESCE(usure_position,'') <> ''
               ORDER BY pos""",
            (int(r["id"]),),
        ).fetchall()]
        pieces.append({"id": int(r["id"]), "positions": positions})
    return pieces


def _code_de_piece(operations, piece, position) -> dict | None:
    """_findWearPartCode : pièce sans position → code à position vide."""
    voulue = "" if not piece["positions"] else str(position or "")
    for o in operations:
        if (o["usure_piece_id"] is not None and str(o["usure_piece_id"]) == str(piece["id"])
                and o["usure_position"] == voulue):
            return o
    return None


def _positions(piece) -> list[str]:
    return list(piece["positions"]) if piece["positions"] else ["single"]


# ── Calcul ───────────────────────────────────────────────────────────────

def compter(operations, pieces, historique, machine: str, categorie: str,
            aujourdhui: date) -> dict:
    """Compteurs par statut pour une machine, comme renderMaintCards."""
    avec_pieces = categorie in ("remplacements", "all")
    codes_pieces = set()
    if avec_pieces:
        for p in pieces:
            for pos in _positions(p):
                c = _code_de_piece(operations, p, pos)
                if c:
                    codes_pieces.add(str(c["code"]))

    compteurs = {s: 0 for s in STATUTS}
    for o in operations:
        if not o["periodique"] or str(o["code"]) in codes_pieces:
            continue
        entretien = o["categorie"] in ("controles", "entretien", "interventions", "suivi")
        remplacement = o["categorie"] == "remplacements"
        if categorie == "all":
            garde = entretien or remplacement
        elif categorie == "entretien":
            garde = entretien
        else:
            garde = remplacement
        if not garde:
            continue
        derniere = derniere_par_libelle(o["libelle"], machine, historique)
        compteurs[statut(parse_frequence_jours(o["intervalle"]), jours_depuis(derniere, aujourdhui))] += 1

    if avec_pieces:
        for p in pieces:
            for pos in _positions(p):
                c = _code_de_piece(operations, p, pos)
                if not c:
                    compteurs["unknown"] += 1
                    continue
                derniere = derniere_par_code(c["code"], c["libelle"], machine, historique)
                compteurs[statut(parse_frequence_jours(c["intervalle"]), jours_depuis(derniere, aujourdhui))] += 1
    return compteurs


def valeurs_bloc(compteurs: dict) -> dict:
    """Valeurs du bloc maintenance.statuts (mêmes clés que la page)."""
    return {
        "en-retard": compteurs["overdue"],
        "bientot": compteurs["soon"],
        "jamais": compteurs["never"] + compteurs["unknown"],
        "a-jour": compteurs["ok"],
    }


def aujourdhui() -> date:
    return datetime.now(ZoneInfo(FUSEAU_HORAIRE)).date()


def statuts_machine(conn, machine: str, categorie: str) -> dict:
    """Lit codes, pièces et historique en base et rend les compteurs."""
    # Imports différés : ces lectures vivent dans les routers qui les servent,
    # pour qu'il n'en existe qu'une version.
    from app.routers.maintenance_events import historique_termine
    from app.routers.settings import _maint_row_to_dict, lire_codes_maintenance

    operations = _operations([_maint_row_to_dict(r) for r in lire_codes_maintenance(conn)])
    historique = historique_termine(conn, ["o.statut = 'termine'"], [])
    compteurs = compter(operations, _pieces(conn), historique, machine, categorie, aujourdhui())
    return {"compteurs": compteurs, "valeurs": valeurs_bloc(compteurs)}
