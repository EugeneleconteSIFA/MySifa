# -*- coding: utf-8 -*-
"""Statuts de maintenance : le calcul serveur reste celui de la page.

Le widget d'accueil maintenance.statuts lit GET /api/maintenance/statuts,
calculé par app/services/maintenance_statuts.py. La page Maintenance garde son
propre calcul en JavaScript (app/web/maintenance_page.py). Ce test protège
leur accord :

1. **Règles de base rejouées dans les deux langages.** Les fonctions JS de la
   page (_parseFrequenceDays, _maintComputeStatus, _lastInterventionFor,
   _lastInterventionForCode) sont extraites du fichier et exécutées par node
   (ou JavaScriptCore sur Mac) sur les mêmes entrées que leur traduction
   Python. Une règle modifiée d'un seul côté fait échouer la CI.
2. **Composition** (catégories, pièces d'usure, exclusions) vérifiée sur un jeu
   de données dont on connaît le résultat.

Lancer : python3 tests/test_maintenance_statuts.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
os.chdir(RACINE)
sys.path.insert(0, str(RACINE))

# Le module ne lit que FUSEAU_HORAIRE dans config : on évite d'importer toute
# l'application (FastAPI absent sur certains postes).
if "config" not in sys.modules:
    try:
        import config  # noqa: F401
    except Exception:
        sys.modules["config"] = types.SimpleNamespace(FUSEAU_HORAIRE="Europe/Paris")

_spec = importlib.util.spec_from_file_location("maintenance_statuts", RACINE / "app/services/maintenance_statuts.py")
ms = importlib.util.module_from_spec(_spec)
sys.modules["maintenance_statuts"] = ms
_spec.loader.exec_module(ms)

echecs: list[str] = []


def verifier(cond, msg):
    if not cond:
        echecs.append(msg)


# ── Jeux d'essai des règles de base ──────────────────────────────────────
FREQUENCES = [
    "Quotidien", "journalier", "Hebdomadaire", "Hebdo (7j)", "Bi-hebdomadaire",
    "bihebdo", "2 semaines", "14j", "Mensuel", "monthly", "Bimensuel", "2 mois",
    "Trimestriel", "3 mois", "Semestriel", "6 mois", "Annuel", "1 an",
    "Biannuel", "Biennal", "2 ans", "10 jours", "45 j", "3 sem", "4 mois",
    "5 ans", "", "   ", "à la demande", "Tous les 30j", "ÉTÉ", "90 J",
]
STATUTS = [(None, 5), (0, 5), (-3, 2), (7, None), (7, 8), (7, 7), (10, 8),
           (10, 7), (30, 0), (1, 1), (1, 2), (365, 292), (365, 291)]
HISTORIQUE = [
    {"type": "Graissage", "machine": "Cohésio 1", "date_saisie": "2026-09-01", "code": "G1"},
    {"type": "graissage ", "machine": "Cohésio 1 · Cohésio 2", "date_saisie": "2026-09-20T10:00:00", "code": "G1"},
    {"type": "Graissage", "machine": "Cohésio 2", "date_saisie": "2026-08-01", "code": "G1"},
    {"type": "Nettoyage", "machine": "cohésio 1, DSI", "date_saisie": "2026-09-15", "code": "N1"},
    {"type": "Couteaux bande", "machine": "Cohésio 1", "date_saisie": "2026-09-10", "code": "CB"},
    {"type": "Couteaux bande", "machine": "Cohésio 1", "date_saisie": "", "code": "CB"},
    {"type": "Vidange", "machine": "DSI", "date_saisie": "2026-07-01", "code": None},
]
HISTO_SANS_CODE = [dict(h, code=None) for h in HISTORIQUE]
LIBELLES = [("Graissage", "Cohésio 1"), ("Graissage", "Cohésio 2"), ("GRAISSAGE", "cohésio 2"),
            ("Nettoyage", "Cohésio 1"), ("Nettoyage", "DSI"), ("Vidange", "DSI"),
            ("Inconnu", "Cohésio 1"), ("", "Cohésio 1"), ("Graissage", "")]
CODES = [("G1", "Graissage", "Cohésio 1"), ("CB", "Couteaux bande", "Cohésio 1"),
         ("CB", "Couteaux bande", "Cohésio 2"), ("ZZ", "Vidange", "DSI"), ("", "Graissage", "Cohésio 1")]


# ── 1. Python ────────────────────────────────────────────────────────────
def resultats_python():
    return {
        "freq": [ms.parse_frequence_jours(f) for f in FREQUENCES],
        "statut": [ms.statut(f, d) for f, d in STATUTS],
        "libelle": [ms.derniere_par_libelle(l, m, HISTORIQUE) for l, m in LIBELLES],
        "code": [ms.derniere_par_code(c, l, m, HISTORIQUE) for c, l, m in CODES],
        "code_repli": [ms.derniere_par_code(c, l, m, HISTO_SANS_CODE) for c, l, m in CODES],
    }


# ── 2. JavaScript de la page ─────────────────────────────────────────────
FONCTIONS_JS = ("_normalizeFreqStr", "_parseFrequenceDays", "_maintComputeStatus",
                "_lastInterventionFor", "_lastInterventionForCode")


def extraire_fonction(source: str, nom: str) -> str:
    """Corps complet d'une fonction JS, par appariement des accolades."""
    m = re.search(r"\bfunction " + re.escape(nom) + r"\s*\(", source)
    if not m:
        raise LookupError(nom)
    i = source.index("{", m.end())
    profondeur = 0
    for j in range(i, len(source)):
        c = source[j]
        if c == "{":
            profondeur += 1
        elif c == "}":
            profondeur -= 1
            if profondeur == 0:
                return source[m.start():j + 1]
    raise LookupError(nom)


def script_js() -> str:
    page = Path("app/web/maintenance_page.py").read_text(encoding="utf-8")
    corps = "\n".join(extraire_fonction(page, n) for n in FONCTIONS_JS)
    # Côté page, l'historique porte le code dans `_code` (fetchHistoryFromDb).
    entree = json.dumps({
        "FREQUENCES": FREQUENCES, "STATUTS": STATUTS, "LIBELLES": LIBELLES, "CODES": CODES,
        "HISTORIQUE": [dict(h, _code=h["code"]) for h in HISTORIQUE],
        "HISTO_SANS_CODE": [dict(h, _code=None) for h in HISTO_SANS_CODE],
    }, ensure_ascii=False)
    return corps + """
var E = """ + entree + """;
var N = function (v) { return v === undefined ? null : v; };
JSON.stringify({
  freq: E.FREQUENCES.map(function (f) { return N(_parseFrequenceDays(f)); }),
  statut: E.STATUTS.map(function (x) { return _maintComputeStatus(x[0], x[1]); }),
  libelle: E.LIBELLES.map(function (x) { return N(_lastInterventionFor(x[0], x[1], E.HISTORIQUE)); }),
  code: E.CODES.map(function (x) { return N(_lastInterventionForCode(x[0], x[1], x[2], E.HISTORIQUE)); }),
  code_repli: E.CODES.map(function (x) { return N(_lastInterventionForCode(x[0], x[1], x[2], E.HISTO_SANS_CODE)); })
});
"""


def resultats_js():
    script = script_js()
    if shutil.which("node"):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write("console.log((function(){ return " + "eval(" + json.dumps(script) + "); })());")
            chemin = f.name
        try:
            sortie = subprocess.run(["node", chemin], capture_output=True, text=True, timeout=30)
        finally:
            os.unlink(chemin)
        if sortie.returncode != 0:
            raise RuntimeError(sortie.stderr.strip())
        return json.loads(sortie.stdout)
    if shutil.which("osascript"):
        # Mac sans node : JavaScriptCore, le moteur de Safari.
        sortie = subprocess.run(["osascript", "-l", "JavaScript", "-e", script],
                                capture_output=True, text=True, timeout=30)
        if sortie.returncode != 0:
            raise RuntimeError(sortie.stderr.strip())
        return json.loads(sortie.stdout)
    return None


py = resultats_python()
try:
    js = resultats_js()
except (LookupError, RuntimeError, ValueError) as e:
    js = None
    verifier(False, f"exécution du JavaScript de la page impossible : {e}")
if js is None and not echecs:
    print("test_maintenance_statuts : ni node ni osascript — comparaison JS sautée")
elif js is not None:
    for cle in py:
        for i, (a, b) in enumerate(zip(py[cle], js[cle])):
            verifier(a == b, f"{cle}[{i}] : Python {a!r} ≠ page {b!r}")
        verifier(len(py[cle]) == len(js[cle]), f"{cle} : longueurs différentes")

# Quelques valeurs attendues, pour que les deux ne puissent pas se tromper ensemble.
verifier(ms.parse_frequence_jours("Hebdomadaire") == 7, "hebdomadaire = 7 j")
verifier(ms.parse_frequence_jours("Trimestriel") == 90, "trimestriel = 90 j")
verifier(ms.parse_frequence_jours("4 mois") == 120, "4 mois = 120 j")
verifier(ms.parse_frequence_jours("à la demande") is None, "texte libre = pas d'intervalle")
verifier(ms.statut(10, 8) == "soon" and ms.statut(10, 11) == "overdue" and ms.statut(10, 7) == "ok",
         "seuils 80 % et 100 %")
verifier(ms.derniere_par_libelle("Graissage", "Cohésio 2", HISTORIQUE) == "2026-09-20T10:00:00",
         "une saisie sur plusieurs machines compte pour chacune")


# ── 3. Composition ───────────────────────────────────────────────────────
AUJ = date(2026, 10, 6)
CODES_CATALOGUE = [
    # Entretien périodique : hebdo, fait il y a 3 j → ok
    {"code": "E1", "label": "Graissage", "categorie": "entretien", "periodique": True, "intervalle": "Hebdomadaire"},
    # Entretien (code legacy « suivi ») : mensuel, fait il y a 27 j → soon
    {"code": "E2", "label": "Nettoyage", "categorie": "suivi", "periodique": True, "intervalle": "Mensuel"},
    # Contrôle périodique : quotidien, jamais fait → never
    {"code": "C1", "label": "Contrôle buses", "categorie": "controles", "periodique": True, "intervalle": "Quotidien"},
    # Contrôle non périodique : ignoré
    {"code": "C2", "label": "Contrôle ponctuel", "categorie": "controles", "periodique": False, "intervalle": ""},
    # Entretien périodique à intervalle illisible → unknown
    {"code": "E3", "label": "Révision", "categorie": "entretien", "periodique": True, "intervalle": "selon usage"},
    # Remplacement périodique : trimestriel, fait il y a 100 j → overdue
    {"code": "R1", "label": "Courroie", "categorie": "remplacements", "periodique": True, "intervalle": "Trimestriel"},
    # Pièce d'usure 7, position bande : 30 j, fait il y a 10 j → ok
    {"code": "CB", "label": "Couteaux bande", "categorie": "remplacements", "periodique": True,
     "intervalle": "30 jours", "usure_piece_id": 7, "usure_position": "bande"},
    # Pièce d'usure 7, position rive : 30 j, jamais faite → never
    {"code": "CR", "label": "Couteaux rive", "categorie": "remplacements", "periodique": True,
     "intervalle": "30 jours", "usure_piece_id": 7, "usure_position": "rive"},
]
PIECES = [
    {"id": 7, "positions": ["bande", "rive"]},
    # Pièce sans aucun code rattaché : position unique, statut unknown
    {"id": 8, "positions": []},
]
HISTO = [
    {"type": "Graissage", "machine": "Cohésio 1", "date_saisie": "2026-10-03T08:00:00", "code": "E1"},
    {"type": "Nettoyage", "machine": "Cohésio 1 · Cohésio 2", "date_saisie": "2026-09-09", "code": "E2"},
    {"type": "Courroie", "machine": "Cohésio 1", "date_saisie": "2026-06-28", "code": "R1"},
    {"type": "Couteaux bande", "machine": "Cohésio 1", "date_saisie": "2026-09-26", "code": "CB"},
    {"type": "Graissage", "machine": "Cohésio 2", "date_saisie": "2026-08-01", "code": "E1"},
]
OPS = ms._operations(CODES_CATALOGUE)


def c(machine, cat):
    return ms.compter(OPS, PIECES, HISTO, machine, cat, AUJ)


verifier(c("Cohésio 1", "entretien") == {"overdue": 0, "soon": 1, "ok": 1, "never": 1, "unknown": 1},
         f"Cohésio 1 / entretien : {c('Cohésio 1', 'entretien')}")
verifier(c("Cohésio 1", "remplacements") == {"overdue": 1, "soon": 0, "ok": 1, "never": 1, "unknown": 1},
         f"Cohésio 1 / remplacements (pièces d'usure comptées par position) : {c('Cohésio 1', 'remplacements')}")
verifier(c("Cohésio 1", "all") == {"overdue": 1, "soon": 1, "ok": 2, "never": 2, "unknown": 2},
         f"Cohésio 1 / tout : {c('Cohésio 1', 'all')}")
verifier(c("Cohésio 2", "entretien") == {"overdue": 1, "soon": 1, "ok": 0, "never": 1, "unknown": 1},
         f"Cohésio 2 / entretien : {c('Cohésio 2', 'entretien')}")
verifier(ms.valeurs_bloc(c("Cohésio 1", "all")) == {"en-retard": 1, "bientot": 1, "jamais": 4, "a-jour": 2},
         "valeurs du bloc : « jamais » réunit jamais saisi et intervalle illisible")

if echecs:
    print("ÉCHEC test_maintenance_statuts :")
    for e in echecs:
        print("  -", e)
    sys.exit(1)
print("test_maintenance_statuts : OK" + ("" if js is None else " (calcul identique à celui de la page)"))
