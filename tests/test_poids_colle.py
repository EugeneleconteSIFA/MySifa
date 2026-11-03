"""
Poids de colle (saisie prod) et historique des pesées par front.

- migration `epaisseurs_grammages_matiere` sur une table d'avant le grammage ;
- PUT du référentiel par périmètre : enregistrer les épaisseurs ne touche pas
  aux grammages, et inversement ;
- rapprochement texte de fiche ↔ référentiel (cas réels des fiches au
  02/11/2026) ;
- historique des pesées : une colonne par front, validations vides écartées.

Lancer : python3 tests/test_poids_colle.py
"""
import asyncio
import importlib.util
import json
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import database  # noqa: E402,F401  — d'abord, toujours (CLAUDE.md)
from app.routers import stock  # noqa: E402
from app.services import alertes_pesees, poids_colle  # noqa: E402

FAIL = []


def check(label, got, expected):
    ok = got == expected
    print(("ok   " if ok else "KO   ") + label.ljust(66) + ("" if ok else f"{got!r}   attendu {expected!r}"))
    if not ok:
        FAIL.append(label)


def base():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    return c


# ── Migration ────────────────────────────────────────────────────────────
conn = base()
conn.execute("""CREATE TABLE mp_metrage_epaisseurs (id INTEGER PRIMARY KEY AUTOINCREMENT,
                libelle TEXT NOT NULL UNIQUE, microns REAL NOT NULL, ordre INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT)""")
for lib, um, o in [("Matière enduite (frontal + colle + glassine)", 145, 10), ("Vélin", 66, 20),
                   ("Couché", 75, 30), ("Thermique Eco", 78, 40), ("Glassine", 52, 60), ("Perso", 99, 70)]:
    conn.execute("INSERT INTO mp_metrage_epaisseurs (libelle, microns, ordre) VALUES (?,?,?)", (lib, um, o))
spec = importlib.util.spec_from_file_location("m", RACINE / "app/core/migrations/2026_11_02_epaisseurs_grammages.py")
mig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mig)
mig.appliquer(conn)
mig.appliquer(conn)
L = stock._metrage_epaisseurs(conn)
par = {l["libelle"]: l for l in L}
check("épaisseurs conservées", (par["Vélin"]["microns"], par["Perso"]["microns"]), (66.0, 99.0))
check("grammage posé sur Vélin", par["Vélin"]["grammage_gsm"], 70.0)
check("familles reprises", (par["Glassine"]["famille"], par["Thermique Eco"]["famille"]), ("glassine", "frontal"))
check("ligne inconnue sans famille", par["Perso"]["famille"], None)
check("anilox seedés", sorted(l["libelle"] for l in L if l["famille"] == "anilox"), ["400L", "500L", "800L"])
check("migration rejouée : pas de doublon", len(L), 6 + 14)
check("microns devenu facultatif", par["Polyart"]["microns"], None)


# ── PUT par périmètre ────────────────────────────────────────────────────
class Req:
    def __init__(self, corps):
        self.corps = corps
        self.client = None

    async def json(self):
        return self.corps


@contextmanager
def _db():
    yield conn


stock.get_db = _db
stock.require_stock_matieres_admin = lambda r: {"role": "superadmin", "nom": "test"}
stock.log_action = lambda **k: None

ep = [l for l in L if l["microns"] is not None and l["libelle"] != "Perso"]
out = asyncio.run(stock.save_metrage_epaisseurs(Req({"perimetre": "epaisseur", "items": [
    {"id": l["id"], "libelle": l["libelle"], "microns": l["microns"]} for l in ep]})))
par = {l["libelle"]: l for l in out}
check("épaisseur retirée : ligne sans grammage supprimée", "Perso" in par, False)
check("grammages intacts après PUT épaisseurs", par["Polyart"]["grammage_gsm"], 80.0)

gr = [l for l in out if l["grammage_gsm"] is not None and l["libelle"] != "Vélin"]
items = [{"id": l["id"], "libelle": l["libelle"], "famille": l["famille"], "grammage_gsm": l["grammage_gsm"]} for l in gr]
items.append({"libelle": "Thermique Eco", "famille": "frontal", "grammage_gsm": "73,5"})
out = asyncio.run(stock.save_metrage_epaisseurs(Req({"perimetre": "grammage", "items": items})))
par = {l["libelle"]: l for l in out}
check("grammage retiré : Vélin garde son épaisseur", (par["Vélin"]["microns"], par["Vélin"]["grammage_gsm"]), (66.0, None))
check("libellé existant enrichi, pas dupliqué",
      (par["Thermique Eco"]["microns"], par["Thermique Eco"]["grammage_gsm"]), (78.0, 73.5))
try:
    asyncio.run(stock.save_metrage_epaisseurs(Req({"perimetre": "grammage", "items": [
        {"libelle": "X", "famille": "inconnue", "grammage_gsm": 70}]})))
    check("famille inconnue refusée", False, True)
except Exception as e:
    check("famille inconnue refusée", getattr(e, "status_code", None), 400)


# ── Rapprochement fiche ↔ référentiel ────────────────────────────────────
L = stock._metrage_epaisseurs(conn)
lib = {l["id"]: l["libelle"] for l in L}


def corr(t):
    c = poids_colle.correspondance(t, L, "frontal")
    return (c["choix"] and lib[c["choix"]["id"]], sorted(lib[x["id"]] for x in c["candidats"]))


check("COUCHé → Couché", corr("COUCHé")[0], "Couché")
check("THERMIQUE ECO → la ligne générique, grammage connu", corr("THERMIQUE ECO")[0], "Thermique Eco")
check("THERMIQUE PRO → protégé Kanzan / Jujo, sans choisir", corr("THERMIQUE PRO"),
      (None, ["Thermique protégé Jujo", "Thermique protégé Kanzan"]))
check("PP 60ZH247 JINDAL → deux Jindal proposés", corr("PP 60ZH247 JINDAL")[1],
      ["PP blanc Jindal 60ZH647", "PP blanc Jindal 65LT500"])
check("Foliset 80 ≠ Foliset 100", corr("FOLISET 80")[0], "Foliset 80")
check("VELIN ETIWELL : Vélin a perdu son grammage, rien", corr("VELIN ETIWELL"), (None, []))
check("anilox « 400 lignes »", lib[poids_colle.correspondance_anilox("400 lignes", L)["id"]], "400L")
check("anilox inconnu", poids_colle.correspondance_anilox("900L", L), None)


# ── Historique des pesées ────────────────────────────────────────────────
c2 = base()
c2.execute("CREATE TABLE maintenance_alerts (id INTEGER PRIMARY KEY, nom TEXT, params TEXT)")
c2.execute("""CREATE TABLE maintenance_alert_acks (id INTEGER PRIMARY KEY, alert_id INTEGER, user_nom TEXT,
              machine TEXT, no_dossier TEXT, ack_at TEXT, responses TEXT, comment TEXT,
              dismissed INTEGER DEFAULT 0, questionnaire TEXT)""")
q_items = [
    {"type": "choice", "label": "Centrage", "responses": ["Conforme", "Décentré"], "id": "q1"},
    {"type": "value", "label": "Grammage de colle", "unit": "g", "id": "q2"},
    {"type": "value", "label": "Pesée", "unit": "g", "points_libres": True, "libelle_point": "Front", "id": "q3"},
]
c2.execute("INSERT INTO maintenance_alerts VALUES (1, 'Inspection', ?)",
           (json.dumps({"checklist": {"enabled": True, "items": q_items}}),))
c2.execute("INSERT INTO maintenance_alerts VALUES (2, 'Nettoyage', ?)",
           (json.dumps({"checklist": {"enabled": True, "items": [q_items[0]]}}),))
photo = json.dumps(q_items)
acks = [
    ("Cohésio 2", "A", "2026-11-02T14:26:58", {"0": ["Conforme"], "1": 19.8, "2": [1.374, 1.391, 1.402]}, ""),
    ("Cohésio 2", "B", "2026-11-02T16:38:23", {"0": ["Conforme"], "1": 23.6, "2": [1.419, 1.444, 1.437, 1.453]}, ""),
    ("Cohésio 1", "A", "2026-11-02T16:21:20", {}, "Fermée auto"),
    ("Cohésio 1", "C", "2026-11-01T10:00:00", {"0": ["Conforme"], "1": 21, "2": [1.2, 1.3]}, ""),
]
for i, (m, dos, at, r, com) in enumerate(acks, start=1):
    c2.execute("INSERT INTO maintenance_alert_acks (id, alert_id, user_nom, machine, no_dossier, ack_at, responses,"
               " comment, dismissed, questionnaire) VALUES (?,1,'Op',?,?,?,?,?,0,?)",
               (i, m, dos, at, json.dumps(r), com, photo))
h = alertes_pesees.historique(c2)
check("seule l'alerte à mesures multiples", [a["nom"] for a in h["alertes"]], ["Inspection"])
a = h["alertes"][0]
check("fermeture automatique écartée, plus récente en haut", [l["no_dossier"] for l in a["lignes"]], ["B", "A", "C"])
check("colonnes : grammage et pesée", [q["label"] for q in a["questions"]], ["Grammage de colle", "Pesée"])
check("nombre de fronts = la plus longue série", a["nb_fronts"], 4)
pf = {x["position"]: x for x in a["questions"][1]["par_front"]}
check("moyenne du front 1", round(pf[1]["moyenne"], 4), round((1.374 + 1.419 + 1.2) / 3, 4))
check("front 4 : une seule pesée", pf[4]["n"], 1)
check("filtre machine",
      [l["no_dossier"] for l in alertes_pesees.historique(c2, machine="Cohésio 1")["alertes"][0]["lignes"]], ["C"])
check("filtre dossier", len(alertes_pesees.historique(c2, no_dossier="A")["alertes"][0]["lignes"]), 1)
check("machines proposées", h["machines"], ["Cohésio 1", "Cohésio 2"])
check("dossiers : le plus récemment pesé d'abord", [d["no_dossier"] for d in a["dossiers"]], ["B", "A", "C"])

# Valeurs à vérifier (cas du 30/10 : 4,266 g au milieu de pesées à 1,4 g).
qs3 = [{"index": 2, "multiple": True}, {"index": 1, "multiple": False}]


def L(dos, fronts, colle=None):
    return {"no_dossier": dos, "machine": "M", "valeurs": {"2": fronts, "1": [colle] if colle else []}}


lignes = [L("768", [1.415, 1.421, 1.419], 21.5), L("768", [4.266, 4.264], 22.6),
          L("768", [1.454, 1.458], 22.5), L("768", [1.432, 1.430, 1.441], 22.5),
          L("729", [0.736, 0.741, 0.98]), L("771", [24.9, 26.2, 25.7], 25.6)]
gs = {g["no_dossier"]: g for g in alertes_pesees.par_dossier(lignes, qs3)}
check("loin de la médiane du dossier", lignes[1]["aberrants"], {"2": [0, 1]})
check("pesée cohérente : rien", lignes[0]["aberrants"], {})
check("un front loin des autres fronts", lignes[4]["aberrants"], {"2": [2]})
check("dossier d'une seule pesée cohérente : rien", lignes[5]["aberrants"], {})
check("compte par dossier", (gs["768"]["nb_aberrants"], gs["771"]["nb_aberrants"]), (2, 0))
check("grammage de colle comparé aussi", "1" in lignes[1]["aberrants"], False)

print("\n" + ("TOUT EST VERT" if not FAIL else f"{len(FAIL)} ÉCHEC(S)"))
sys.exit(1 if FAIL else 0)
