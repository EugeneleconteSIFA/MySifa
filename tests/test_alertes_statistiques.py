"""
Analyse des alertes (onglet Analyse de l'historique des saisies).

1. La non-conformité calculée par le serveur est celle de la page :
   `_ackHasNonConformite` de maintenance_page.py est extraite et rejouée
   (node, ou JavaScriptCore sur Mac) sur les mêmes réponses que
   `est_non_conforme`.
2. Statistiques sur une base en mémoire : fermetures auto et esquives hors
   des chiffres, anciens formulaires écartés, filtres (conformité, question,
   machine), valeurs, mesures multiples, produit de l'export, période précédente.

Lancer : python3 tests/test_alertes_statistiques.py
"""

import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import os
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

from app.services.alertes_questionnaire import attribuer_ids, photo  # noqa: E402
from app.services.alertes_statistiques import (  # noqa: E402
    bornes_periode, est_non_conforme, passe_filtres_points, statistiques,
)

FAIL = []


def check(label, got, expected):
    ok = got == expected
    print(("ok   " if ok else "KO   ") + label.ljust(64) + ("" if ok else f"{got!r}   attendu {expected!r}"))
    if not ok:
        FAIL.append(label)


ITEMS = attribuer_ids([
    {"type": "choice", "label": "Centrage", "responses": ["Conforme", "Décentré"],
     "allow_other": True, "nc_responses": ["Décentré"], "other_is_nc": False},
    {"type": "value", "label": "Grammage", "unit": "g", "min": 18, "max": 22, "target_value": 20,
     "out_of_range_is_nc": True},
    {"type": "value", "label": "Release"},
    {"type": "value", "label": "Pesée", "unit": "g", "points_libres": True, "libelle_point": "Front"},
], [])

# ── 1. Non-conformité : serveur = page ───────────────────────────────────
CAS_NC = [
    {"0": ["Conforme"], "1": 20},
    {"0": ["Décentré"], "1": 20},
    {"0": ["Autre"], "0_other": "plis", "1": 20},
    {"0": ["Conforme"], "1": 23.5},
    {"0": ["Conforme"], "1": "17.9"},
    {"0": ["Conforme"], "1": [19, 22.1]},
    {"0": ["Conforme"], "2": 999, "3": [1.0, 9.0]},
    {},
]
ITEMS_AUTRE_NC = [dict(ITEMS[0], other_is_nc=True)]


def nc_js(cas, items):
    page = (RACINE / "app/web/maintenance_page.py").read_text(encoding="utf-8")
    debut = page.index("function _ackHasNonConformite")
    i, prof = page.index("{", debut), 0
    for j in range(i, len(page)):
        prof += {"{": 1, "}": -1}.get(page[j], 0)
        if prof == 0:
            break
    fonction = page[debut:j + 1]
    script = ("var CTRL_STATE = {alerts_meta: {'1': {checklist_items: " + json.dumps(items) + "}}};\n"
              + fonction + "\nJSON.stringify(" + json.dumps(cas)
              + ".map(function (r) { return _ackHasNonConformite({_source: 'alert', _alert_id: 1, _responses: r}); }));")
    if shutil.which("node"):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write("console.log(eval(" + json.dumps(script) + "));")
            chemin = f.name
        try:
            out = subprocess.run(["node", chemin], capture_output=True, text=True, timeout=30)
        finally:
            os.unlink(chemin)
    elif shutil.which("osascript"):
        out = subprocess.run(["osascript", "-l", "JavaScript", "-e", script], capture_output=True, text=True, timeout=30)
    else:
        return None
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip())
    return json.loads(out.stdout)


py = [est_non_conforme(ITEMS, r) for r in CAS_NC]
check("NC : jeu d'essai attendu", py, [False, True, False, True, True, True, False, False])
js = nc_js(CAS_NC, ITEMS)
if js is None:
    print("     (ni node ni osascript : comparaison avec la page sautée)")
else:
    check("NC : serveur identique à la page", py, js)
    py2 = [est_non_conforme(ITEMS_AUTRE_NC, r) for r in CAS_NC[:3]]
    check("NC « Autre » non conforme : serveur identique à la page", py2, nc_js(CAS_NC[:3], ITEMS_AUTRE_NC))

check("filtre question : choix", passe_filtres_points(ITEMS, {"0": ["Décentré"]}, {"0": {"value": "Décentré"}}), True)
check("filtre question : choix exclu", passe_filtres_points(ITEMS, {"0": ["Conforme"]}, {"0": {"value": "Décentré"}}), False)
check("filtre question : min", passe_filtres_points(ITEMS, {"1": 19}, {"1": {"min": "19.5"}}), False)
check("filtre question : valeur absente exclue", passe_filtres_points(ITEMS, {}, {"1": {"max": "30"}}), False)
check("période last7", bornes_periode("last7", date(2026, 10, 25)), (date(2026, 10, 19), date(2026, 10, 25)))
check("période prevMonth", bornes_periode("prevMonth", date(2026, 10, 25)), (date(2026, 9, 1), date(2026, 9, 30)))

# ── 2. Statistiques ──────────────────────────────────────────────────────
conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.execute("CREATE TABLE maintenance_alerts (id INTEGER PRIMARY KEY, nom TEXT, params TEXT)")
conn.execute("""CREATE TABLE maintenance_alert_acks (id INTEGER PRIMARY KEY, alert_id INTEGER, user_nom TEXT,
                machine TEXT, no_dossier TEXT, ack_at TEXT, responses TEXT, comment TEXT,
                dismissed INTEGER DEFAULT 0, questionnaire TEXT)""")
conn.execute("CREATE TABLE planning_entries (reference TEXT, numero_of TEXT, ref_produit TEXT, ref_produit_norm TEXT)")
conn.execute("CREATE TABLE fiches_techniques (id INTEGER PRIMARY KEY, ref_produit_norm TEXT, adhesif TEXT)")
conn.execute("INSERT INTO planning_entries VALUES ('D1', '', 'ETQ-A', 'ETQA')")
conn.execute("INSERT INTO fiches_techniques (ref_produit_norm, adhesif) VALUES ('ETQA', 'Acrylique')")
conn.execute("INSERT INTO maintenance_alerts VALUES (1, 'Inspection', ?)",
             (json.dumps({"checklist": {"enabled": True, "items": ITEMS}}),))
PHOTO = photo(ITEMS)
ANCIENNE = json.dumps([{"id": "ancien-0", "type": "choice", "label": "Question 1", "inconnue": True}])
SAISIES = [
    # (date, machine, opérateur, dossier, réponses, commentaire, esquive, photo)
    ("2026-10-20T08:00:00", "C1", "Henri", "D1", {"0": ["Conforme"], "1": 19.5, "2": 7, "3": [1.70, 1.80]}, "", 0, PHOTO),
    ("2026-10-21T08:00:00", "C1", "Henri", "", {"0": ["Décentré"], "1": 20.5, "2": 8}, "", 0, PHOTO),
    ("2026-10-22T08:00:00", "C2", "Bastien", "D1", {"0": ["Autre"], "0_other": "Plis", "1": 23.0, "3": [1.75, 1.77]}, "", 0, PHOTO),
    ("2026-10-23T08:00:00", "C2", "Bastien", "", {"0": ["Autre"], "0_other": "plis "}, "", 0, PHOTO),
    ("2026-10-23T09:00:00", "C2", "", "", {}, "Fermée auto : 89 - Fin de production", 0, PHOTO),
    ("2026-10-23T10:00:00", "C2", "Bastien", "", {}, "Fermée auto (esquive) : Pas de bobine", 1, PHOTO),
    ("2026-10-24T08:00:00", "C1", "Henri", "", {"0": ["Nette"]}, "", 0, ANCIENNE),
    ("2026-10-12T08:00:00", "C1", "Henri", "", {"0": ["Décentré"], "1": 20}, "", 0, PHOTO),  # période précédente
]
for d, m, o, dos, r, com, esq, ph in SAISIES:
    conn.execute("""INSERT INTO maintenance_alert_acks (alert_id, user_nom, machine, no_dossier, ack_at, responses,
                    comment, dismissed, questionnaire) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)""",
                 (o, m, dos, d, json.dumps(r), com, esq, ph))

res = statistiques(conn, [1], du=date(2026, 10, 18), au=date(2026, 10, 24))
a = res["alertes"][0]
s = a["synthese"]
check("validations remplies retenues", s["validations"], 4)
check("fermeture auto hors des chiffres", s["fermetures_auto"], 1)
check("esquive hors des chiffres", s["esquives"], 1)
check("ancien formulaire écarté", s["anciens_exclus"], 1)
check("remplissage = remplies / occurrences", s["remplissage"], round(100 * 4 / 6, 1))
check("non-conformités (Décentré, grammage 23)", s["nc"], 2)
check("taux NC", s["taux_nc"], 50.0)
check("période précédente : même durée, juste avant",
      (s["precedent"]["du"], s["precedent"]["au"], s["precedent"]["validations"]), ("2026-10-11", "2026-10-17", 1))

q0, q1, q3 = a["questions"][0], a["questions"][1], a["questions"][3]
rep = {r["reponse"]: (r["n"], r["nc"]) for r in q0["repartition"]}
check("choix : répartition", rep, {"Conforme": (1, False), "Décentré": (1, True), "Autre": (2, False)})
check("choix : précisions « Autre » regroupées", [(o["texte"], o["n"]) for o in q0["autres"]], [("Plis", 2)])
check("valeur : moyenne", q1["resume"]["moyenne"], round((19.5 + 20.5 + 23.0) / 3, 4))
check("valeur : hors tolérance", (q1["hors_tolerance"], q1["pct_hors_tolerance"]), (1, round(100 / 3, 1)))
check("valeur : cible", q1["cible"], 20.0)
check("mesures multiples : toutes les mesures comptées", q3["resume"]["n"], 4)
check("mesures multiples : écart moyen entre fronts", round(q3["multiples"]["ecart"]["moyenne"], 3), round((0.10 + 0.02) / 2, 3))
check("mesures multiples : moyenne du front 1", round(q3["multiples"]["par_position"][0]["moyenne"], 3), 1.725)
check("export : produit et adhésif du dossier (planning, fiche)",
      sorted({(l["produit"], l["adhesif"]) for l in a["_lignes"]}), [("", ""), ("ETQ-A", "Acrylique")])

nc = statistiques(conn, [1], du=date(2026, 10, 18), au=date(2026, 10, 24), conformite="nc")["alertes"][0]["synthese"]
check("filtre conformité NC", nc["validations"], 2)
pt = statistiques(conn, [1], du=date(2026, 10, 18), au=date(2026, 10, 24), points={"1": {"min": "20"}})["alertes"][0]
check("filtre par question (grammage ≥ 20)", pt["synthese"]["validations"], 2)
m2 = statistiques(conn, [1], du=date(2026, 10, 18), au=date(2026, 10, 24), machine="C2")["alertes"][0]["synthese"]
check("filtre machine : remplissage sur la machine", (m2["validations"], m2["remplissage"]), (2, 50.0))

print()
print("ÉCHEC : " + ", ".join(FAIL) if FAIL else "Tous les contrôles passent.")
sys.exit(1 if FAIL else 0)
