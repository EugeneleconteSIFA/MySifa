"""
Étiquettes spécifiques (MyPrint) : SSCC, séries, rendu ZPL.

Lancer : python3 tests/test_etiq_specifiques.py

Ce que le test verrouille :
1. La clé de contrôle GS1 et le SSCC de 18 chiffres (exemple officiel GS1).
2. Un SSCC ne ressort jamais : le compteur avance d'une impression à l'autre,
   et un départ manuel en arrière est refusé.
3. Le ZPL reste du ZPL valide quand une saisie contient ^ ou ~.
4. Une mise en page venue de l'IA est bornée avant d'être enregistrée.
"""

import sqlite3
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

from app.services import etiq_specifiques as es   # noqa: E402

ECHECS = []


def check(label, obtenu, attendu=True):
    ok = obtenu == attendu
    print(("ok   " if ok else "KO   ") + label.ljust(62)
          + ("" if ok else f"{obtenu!r}   attendu {attendu!r}"))
    if not ok:
        ECHECS.append(label)


def base_simple():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    import importlib.util
    chemin = RACINE / "app/core/migrations/2026_10_14_etiquettes_specifiques.py"
    spec = importlib.util.spec_from_file_location("mig_etiq", chemin)
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)
    mig.appliquer(conn)
    mig.appliquer(conn)  # rejouable
    return conn


# ── 1. GS1 ──────────────────────────────────────────────────────────────────
# Exemple des spécifications générales GS1 : (00) 1 0614141 234567890 8
check("clé GS1 de l'exemple officiel", es.cle_gs1("10614141234567890"), "8")
check("SSCC 18 chiffres", es.sscc("1", "0614141", 234567890), "106141412345678908")
check("SSCC préfixe 9 chiffres", len(es.sscc("0", "306123456", 1)), 18)
try:
    es.sscc("0", "0614141", 10 ** 9)
    check("série épuisée refusée", False)
except es.EtiquetteInvalide:
    check("série épuisée refusée", True)

# ── 2. Séries ──────────────────────────────────────────────────────────────
layout = es.normaliser_layout({
    "elements": [
        {"type": "texte", "x": 5, "y": 5, "valeur": "Lot {{lot}} n°{{num}}", "taille": 4},
        {"type": "code_barre", "x": 5, "y": 20, "symbologie": "gs1_128", "valeur": "(00){{sscc}}"},
    ],
    "variables": [
        {"nom": "lot", "libelle": "Lot", "type": "saisie"},
        {"nom": "num", "libelle": "N°", "type": "compteur", "debut": 1, "longueur": 4, "prefixe": "C"},
        {"nom": "sscc", "libelle": "SSCC", "type": "sscc", "extension": "3", "prefixe_gs1": "3012345"},
    ],
})
conn = base_simple()
p = es.plan_serie(conn, 7, layout, 3)
check("compteur démarre à debut", p["num"]["premier"], 1)
check("SSCC démarre à 1", p["sscc"]["premier"], 1)
zpl, vals = es.rendre_serie(layout, 100, 150, 203, p, 3, {"lot": "L42"})
check("3 étiquettes dans le ZPL", zpl.count("^XA"), 3)
check("compteur formaté", [v["num"] for v in vals], ["C0001", "C0002", "C0003"])
check("SSCC distincts", len({v["sscc"] for v in vals}), 3)
es.reserver_serie(conn, p, 3, "test@x")
conn.commit()
p2 = es.plan_serie(conn, 7, layout, 2)
check("le compteur reprend après la série", p2["num"]["premier"], 4)
check("le SSCC reprend après la série", p2["sscc"]["premier"], 4)
# Une autre étiquette sur le même préfixe partage le compteur SSCC
p3 = es.plan_serie(conn, 99, layout, 1)
check("SSCC partagé entre étiquettes", p3["sscc"]["premier"], 4)
check("compteur propre à l'étiquette", p3["num"]["premier"], 1)
try:
    es.plan_serie(conn, 7, layout, 1, {"sscc": 2})
    check("départ SSCC en arrière refusé", False)
except es.EtiquetteInvalide:
    check("départ SSCC en arrière refusé", True)
check("départ SSCC en avant accepté", es.plan_serie(conn, 7, layout, 1, {"sscc": 50})["sscc"]["premier"], 50)
try:
    es.controler_saisies(layout, {})
    check("saisie obligatoire manquante refusée", False)
except es.EtiquetteInvalide:
    check("saisie obligatoire manquante refusée", True)

# ── 3. ZPL ─────────────────────────────────────────────────────────────────
z = es.rendre_zpl(layout, 100, 150, 203, {"lot": "A^B~C_D", "num": "1", "sscc": "1"})
check("^ échappé", "A_5EB_7EC_5FD" in z)
check("GS1-128 en mode D", "^BCN," in z and ",N,N,D^FH_" in z)
check("largeur en points (100 mm à 203 dpi)", "^PW799" in z)
check("UTF-8 déclaré", "^CI28" in z)

# ── 4. Normalisation ──────────────────────────────────────────────────────
n = es.normaliser_layout({"elements": [
    {"type": "inconnu", "x": 1, "y": 1},
    {"type": "texte", "x": -40, "y": 9999, "taille": "abc", "rotation": 45},
    {"id": "a", "type": "cadre", "x": 1, "y": 1},
    {"id": "a", "type": "ligne", "x": 1, "y": 1},
]})
check("type inconnu écarté", len(n["elements"]), 3)
check("x borné à 0", n["elements"][0]["x"], 0)
check("y borné", n["elements"][0]["y"], es.FORMAT_MAX_MM)
check("rotation invalide → 0", n["elements"][0]["rotation"], 0)
check("ids rendus uniques", len({e["id"] for e in n["elements"]}), 3)
try:
    es.normaliser_layout({"variables": [{"nom": "Mauvais Nom", "type": "fixe"}]})
    check("nom de variable invalide refusé", False)
except es.EtiquetteInvalide:
    check("nom de variable invalide refusé", True)
check("variable non déclarée signalée",
      any("inconnue" in a or "aucune variable" in a for a in es.controles(
          es.normaliser_layout({"elements": [{"type": "texte", "x": 1, "y": 1, "valeur": "{{x}}"}]}))))

print()
if ECHECS:
    print(f"{len(ECHECS)} échec(s)")
    sys.exit(1)
print("Tout est vert.")
