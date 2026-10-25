"""
Questionnaires d'alerte qui changent : chaque réponse reste sous sa question.

Cas tirés de « Inspection des produits finis » (7 questions jusqu'au
09/10/2026, 4 ensuite), puis évolutions à venir du questionnaire : question
ajoutée, retirée, déplacée, changée de type, éditeur en cache sans
identifiants.

Lancer : python3 tests/test_alertes_questionnaire.py
"""

import json
import sqlite3
import sys
import importlib.util
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

from app.services.alertes_questionnaire import (  # noqa: E402
    attribuer_ids, compatible, lire_saisie, photo, pour_affichage,
)

FAIL = []


def check(label, got, expected):
    ok = got == expected
    print(("ok   " if ok else "KO   ") + label.ljust(64) + ("" if ok else f"{got!r}   attendu {expected!r}"))
    if not ok:
        FAIL.append(label)


ACTUEL = [
    {"type": "choice", "label": "Centrage étiquette", "responses": ["Conforme", "Décentré"],
     "allow_other": True, "nc_responses": ["Décentré"]},
    {"type": "value", "label": "Grammage de colle", "unit": "g"},
    {"type": "value", "label": "Release"},
    {"type": "value", "label": "Pesée de 2 étiquettes / sur tous les fronts", "unit": "g",
     "points_libres": True},
]
ANCIENNE = {"0": ["Nette"], "1": ["Conforme"], "2": ["Conforme"], "3": ["Conforme"],
            "4": ["Conforme"], "5": 19.5, "6": 8}
RECENTE = {"0": ["Conforme"], "1": 50.3, "2": 10, "3": [1.021, 1.021, 1.045, 1.005]}

# ── Validations d'avant les identifiants ─────────────────────────────────
check("récente compatible avec le questionnaire actuel", compatible(ACTUEL, RECENTE), True)
check("ancienne (7 réponses) incompatible", compatible(ACTUEL, ANCIENNE), False)
check("« Nette » n'est pas une réponse de Centrage", compatible(ACTUEL, {"0": ["Nette"]}), False)
check("« Autre » + précision acceptés", compatible(ACTUEL, {"0": ["Autre"], "0_other": "plis"}), True)
check("liste de nombres refusée sans mesures multiples",
      compatible(ACTUEL, {"1": [19.4, 19.6]}), False)

# ── Migration sur une base en mémoire ────────────────────────────────────
conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE maintenance_alerts (id INTEGER PRIMARY KEY, nom TEXT, params TEXT)")
conn.execute("""CREATE TABLE maintenance_alert_acks (id INTEGER PRIMARY KEY, alert_id INTEGER,
                ack_at TEXT, responses TEXT, comment TEXT)""")
conn.execute("INSERT INTO maintenance_alerts VALUES (1, 'Inspection', ?)",
             (json.dumps({"checklist": {"enabled": True, "items": ACTUEL}}),))
for i, r in enumerate([ANCIENNE, RECENTE, {}], start=1):
    conn.execute("INSERT INTO maintenance_alert_acks (id, alert_id, ack_at, responses) VALUES (?, 1, '', ?)",
                 (i, json.dumps(r)))
spec = importlib.util.spec_from_file_location(
    "m", RACINE / "app/core/migrations/2026_10_25_alertes_questionnaire_photo.py")
mig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mig)
mig.appliquer(conn)
items = json.loads(conn.execute("SELECT params FROM maintenance_alerts").fetchone()[0])["checklist"]["items"]
ids = [it["id"] for it in items]
check("chaque question a un identifiant", all(ids) and len(set(ids)) == 4, True)
mig.appliquer(conn)
items2 = json.loads(conn.execute("SELECT params FROM maintenance_alerts").fetchone()[0])["checklist"]["items"]
check("migration rejouée : identifiants inchangés", [it["id"] for it in items2], ids)
photos = {r[0]: r[1] for r in conn.execute("SELECT id, questionnaire FROM maintenance_alert_acks")}
check("toutes les validations ont leur photo", all(photos.values()), True)

ancienne = lire_saisie(ANCIENNE, photos[1], items)
check("ancienne : aucune réponse sous les questions actuelles",
      {k for k in ancienne["responses"] if k[0].isdigit()}, set())
check("ancienne : marquée ancien formulaire", ancienne["ancien"], True)
check("ancienne : ses 7 réponses gardées à part", len(ancienne["hors_formulaire"]), 7)
check("ancienne : 19.5 conservé", ancienne["hors_formulaire"][5]["valeur"], "19.5")

recente = lire_saisie(RECENTE, photos[2], items)
check("récente : lue telle quelle", recente["responses"], RECENTE)
check("récente : pas ancien formulaire", recente["ancien"], False)
check("validation vide : pas ancien formulaire", lire_saisie({}, photos[3], items)["ancien"], False)

# ── Évolutions futures du questionnaire ──────────────────────────────────
photo_v2 = photo(items)  # validation faite avec les 4 questions actuelles

# L'admin déplace « Release » en tête et ajoute une question à la fin.
v3 = [dict(items[2]), dict(items[0]), dict(items[1]), dict(items[3]),
      {"type": "choice", "label": "Aspect mandrin", "responses": ["OK", "Abîmé"]}]
attribuer_ids(v3, items)
check("questions déplacées : identifiants gardés", [it["id"] for it in v3[:4]],
      [ids[2], ids[0], ids[1], ids[3]])
check("question ajoutée : identifiant neuf", v3[4]["id"] not in ids, True)
lu = lire_saisie(RECENTE, photo_v2, v3)
check("déplacement : Release suit sa question", lu["responses"].get("0"), 10)
check("déplacement : Centrage suit sa question", lu["responses"].get("1"), ["Conforme"])
check("déplacement : pesée suit sa question", lu["responses"].get("3"), [1.021, 1.021, 1.045, 1.005])
check("question ajoutée : vide pour l'ancienne validation", "4" in lu["responses"], False)
check("ajout/déplacement : pas ancien formulaire", lu["ancien"], False)

# L'admin retire « Release ».
v4 = [dict(it) for it in v3 if it["id"] != ids[2]]
attribuer_ids(v4, v3)
lu = lire_saisie(RECENTE, photo_v2, v4)
check("question retirée : réponse sortie à part", lu["hors_formulaire"],
      [{"libelle": "Release", "valeur": "10"}])
check("question retirée : la saisie reste affichée", lu["ancien"], False)
check("question retirée : le reste reste en place", lu["responses"].get("0"), ["Conforme"])
q_aff, r_aff = pour_affichage(RECENTE, photo_v2, v4)
check("affichage détail : question retirée ajoutée en fin", q_aff[-1]["label"], "Release (ancien formulaire)")
check("affichage détail : sa réponse en face", r_aff.get(str(len(q_aff) - 1)), 10)

# Grammage passe de « valeur » à « choix » : c'est une autre question.
v5 = [dict(it) for it in v4]
v5[1] = dict(v5[1], type="choice", responses=["OK", "KO"])
v5[1].pop("unit", None)
attribuer_ids(v5, v4)
check("changement de type : nouvel identifiant", v5[1]["id"] != ids[1], True)
lu = lire_saisie(RECENTE, photo_v2, v5)
check("une seule question survivante : pas ancien formulaire",
      lire_saisie({"0": ["Conforme"], "2": 10}, photo_v2, v4)["ancien"], False)
check("plus aucune réponse en place : ancien formulaire",
      lire_saisie({"2": 10}, photo_v2, v4)["ancien"], True)
check("changement de type : ancienne valeur à part",
      {"libelle": "Grammage de colle", "valeur": "50.3 g"} in lu["hors_formulaire"], True)

# Éditeur resté en cache (sans identifiants) : on retrouve par libellé.
sans_ids = [{k: v for k, v in it.items() if k != "id"} for it in v4]
attribuer_ids(sans_ids, v4)
check("éditeur sans identifiants : repris par libellé", [it["id"] for it in sans_ids],
      [it["id"] for it in v4])

# Doublon d'identifiant envoyé (copie de carte) : le second en reçoit un neuf.
doublon = [dict(v4[0]), dict(v4[0], label="Copie")]
attribuer_ids(doublon, v4)
check("identifiant en double : le second est renouvelé", doublon[0]["id"] != doublon[1]["id"], True)

print()
print("ÉCHEC : " + ", ".join(FAIL) if FAIL else "Tous les contrôles passent.")
sys.exit(1 if FAIL else 0)
