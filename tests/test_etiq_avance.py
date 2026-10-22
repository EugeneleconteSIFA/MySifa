"""
Étiquettes spécifiques — fonctions avancées (formules, dates, GS1, sources,
versions, verrous, pictogrammes, rendu conditionnel).

Lancer : python3 tests/test_etiq_avance.py

Les cas de tests/etiq_formules_cas.json sont rejoués à l'identique par
tests/test_etiq_moteur.js : aperçu (JS) et impression (Python) doivent rendre
la même valeur.
"""

import importlib.util
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

from app.services import etiq_formules as ef        # noqa: E402
from app.services import etiq_gs1 as g1              # noqa: E402
from app.services import etiq_specifiques as es      # noqa: E402

ECHECS = []


def check(label, obtenu, attendu=True):
    ok = obtenu == attendu
    print(("ok   " if ok else "KO   ") + label[:70].ljust(72) + ("" if ok else f"{obtenu!r}   attendu {attendu!r}"))
    if not ok:
        ECHECS.append(label)


CAS = json.loads((RACINE / "tests/etiq_formules_cas.json").read_text(encoding="utf-8"))

# ── 1. Formules (cas partagés avec le JS) ──────────────────────────────────
for expr, vals, attendu in CAS["formules"]:
    check(f"formule {expr!r}", ef.evaluer(expr, vals)["valeur"], attendu)
for expr, message in CAS["erreurs"]:
    check(f"erreur {expr!r}", ef.evaluer(expr, {})["erreur"], message)
for expr, vals, attendu in CAS["conditions"]:
    check(f"condition {expr!r} {vals}", ef.condition_vraie(expr, vals), attendu)
check("formule trop longue refusée", bool(ef.evaluer("1+" * 600 + "1", {})["erreur"]), True)
check("imbrication bornée", bool(ef.evaluer("(" * 200 + "1" + ")" * 200, {})["erreur"]), True)

# ── 2. Dates calculées ─────────────────────────────────────────────────────
for var, vals, maintenant, attendu in CAS["dates"]:
    check(f"date {var} {vals}", ef.calculer_date(var, vals, datetime.fromisoformat(maintenant)), attendu)

# ── 3. GS1 ─────────────────────────────────────────────────────────────────
for valeur, nb in CAS["gs1"]:
    check(f"GS1 {valeur}", len(g1.controler(valeur)), nb)
check("poids 310x", g1.poids_310x("12,5", 2), "001250")

# ── 4. Valeurs d'une étiquette : sources, dates, formules ──────────────────
layout = es.normaliser_layout({
    "elements": [
        {"id": "t1", "type": "texte", "x": 2, "y": 2, "valeur": "{{ref}} {{libelle}}", "taille": 3},
        {"id": "t2", "type": "texte", "x": 2, "y": 8, "valeur": "Lot {{lot}}", "taille": 3, "masquer_si_vide": True},
        {"id": "t3", "type": "texte", "x": 2, "y": 14, "valeur": "GROS", "taille": 3, "condition": "NUM(qte) > 100"},
        {"id": "p1", "type": "picto", "x": 60, "y": 2, "picto": "fsc", "largeur": 14, "hauteur": 18, "legende": "{{fsc_licence}}"},
        {"id": "p2", "type": "picto", "x": 60, "y": 2, "picto": "inexistant"},
        {"id": "c1", "type": "code_barre", "x": 2, "y": 20, "symbologie": "pdf417", "valeur": "{{ref}}"},
    ],
    "variables": [
        {"nom": "ref", "libelle": "Réf", "type": "source", "champ": "dossier.reference"},
        {"nom": "client", "libelle": "Client", "type": "source", "champ": "client.raison_sociale", "valeur": "x"},
        {"nom": "lot", "libelle": "Lot", "type": "saisie", "obligatoire": False},
        {"nom": "qte", "libelle": "Qté", "type": "saisie", "valeur": "50"},
        {"nom": "libelle", "libelle": "Libellé", "type": "formule", "expression": "MAJUSCULE(client) & ' / ' & dluo"},
        {"nom": "dluo", "libelle": "DLUO", "type": "date", "base": "impression", "decalage_mois": 12, "format": "%m/%Y"},
        {"nom": "mauvais", "libelle": "x", "type": "source", "champ": "drop table"},
    ],
})
check("picto inconnu écarté", [e["id"] for e in layout["elements"]], ["t1", "t2", "t3", "p1", "c1"])
check("calques par défaut", [c["id"] for c in layout["calques"]], ["fond", "donnees"])
check("champ source invalide vidé", layout["variables"][-1]["champ"], "")
vals = es.valeurs_etiquette(layout, {}, 0, {"ref": "24-1187", "client": "Dupont"}, datetime(2026, 10, 22, 9, 0))
check("formule lit une date déclarée après elle", vals["libelle"], "DUPONT / 10/2027")
check("masquer si vide", [e["id"] for e in es.elements_visibles(layout, vals)], ["t1", "p1", "c1"])
vals2 = dict(vals, lot="L1", qte="250")
check("condition vraie → affiché", [e["id"] for e in es.elements_visibles(layout, vals2)], ["t1", "t2", "t3", "p1", "c1"])
zpl = es.rendre_zpl(layout, 100, 50, 203, vals)
check("ZPL : objet masqué absent", "Lot" in zpl, False)
check("ZPL : picto en image", "^GFA," in zpl, True)
check("ZPL : PDF417", "^B7N" in zpl, True)
check("avertissement champ source vide", any("choisir la donnée" in a for a in es.controles(layout)), True)

# ── 5. Pictogrammes : trame et ZPL ─────────────────────────────────────────
from app.services import etiq_pictos as ep  # noqa: E402
for nom in ep.PICTOS:
    g = ep.zpl_gfa(nom, 61, 61)
    total = int(g.split(",")[1])
    check(f"picto {nom} : ^GFA cohérent", total == 8 * 61 and len(g.split(",")[4]) == 2 * total, True)
img = ep.trame("haut", 48, 48)
check("picto dessiné (pixels noirs)", img.getextrema()[0] == 0, True)

# ── 6. Base : migration, versions, compteurs (reprise), verrous ───────────
conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
for f in ("2026_10_14_etiquettes_specifiques.py", "2026_10_22_etiq_bibliotheque_versions.py"):
    spec = importlib.util.spec_from_file_location("m", RACINE / "app/core/migrations" / f)
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)
    mig.appliquer(conn)
    mig.appliquer(conn)   # rejouable
cols = {r[1] for r in conn.execute("PRAGMA table_info(etiq_modeles)")}
check("colonnes usage, client, version", {"usage", "client", "version"} <= cols, True)
conn.execute("INSERT INTO etiq_dossiers (nom,created_at) VALUES ('D','2026-10-22T00:00:00')")
conn.execute("INSERT INTO etiq_modeles (dossier_id,nom,layout_json,created_at,updated_at) VALUES (1,'M','{}','x','x')")
row = conn.execute("SELECT * FROM etiq_modeles WHERE id=1").fetchone()
from app.services import etiq_bibliotheque as eb  # noqa: E402
check("version suivante", eb.enregistrer_version(conn, row, "a@b"), 2)
check("version rangée", len(eb.lister_versions(conn, 1)), 1)

lay_c = es.normaliser_layout({"variables": [
    {"nom": "n", "libelle": "N", "type": "compteur", "debut": 5, "longueur": 3, "prefixe": "P"},
    {"nom": "r", "libelle": "R", "type": "compteur", "debut": 1, "reprise": False}]})
p = es.plan_serie(conn, 1, lay_c, 2)
es.reserver_serie(conn, p, 2, "a@b")
p = es.plan_serie(conn, 1, lay_c, 1)
check("compteur repris au dernier numéro mémorisé", p["n"]["premier"], 7)
check("compteur sans reprise repart du départ", p["r"]["premier"], 1)

fige = es.normaliser_layout({"elements": [
    {"id": "logo", "type": "cadre", "x": 1, "y": 1, "calque": "fond"},
    {"id": "m", "type": "texte", "x": 1, "y": 9, "valeur": "Mention", "verrou": True},
    {"id": "v", "type": "texte", "x": 1, "y": 20, "valeur": "{{lot}}"}]})
bouge = json.loads(json.dumps(fige))
bouge["elements"][2]["x"] = 5
check("objet libre modifiable", eb.violations_verrous(fige, es.normaliser_layout(bouge)), [])
bouge["elements"][0]["x"] = 5
check("calque figé protégé", len(eb.violations_verrous(fige, es.normaliser_layout(bouge))), 1)
sans = json.loads(json.dumps(fige))
sans["elements"] = sans["elements"][:1] + sans["elements"][2:]
check("objet verrouillé non retirable", len(eb.violations_verrous(fige, es.normaliser_layout(sans))), 1)
dever = json.loads(json.dumps(fige))
dever["calques"][0]["verrou"] = False
check("calque non déverrouillable", len(eb.violations_verrous(fige, es.normaliser_layout(dever))) >= 1, True)

# ── 7. Sources : référentiel et lecture sur une base vide ─────────────────
from app.services import etiq_sources as src  # noqa: E402
ref = src.referentiel()
check("sources", sorted(ref), sorted(["dossier", "of", "produit", "client", "matiere", "lot", "article", "article_erp"]))
check("champ connu", src.champ_connu("client.ville"), True)
check("champ inconnu", src.champ_connu("client.mot_de_passe"), False)
check("source sans table : vide, sans erreur", src.rechercher(conn, "dossier", "x"), [])

# ── 8. Contrôles de saisie opérateur (miroir du formulaire JS) ────────────
v_lot = es.normaliser_layout({"variables": [{"nom": "lot", "libelle": "Lot", "type": "saisie",
    "controle": {"type": "motif", "motif": "[A-Z0-9-]{3,12}"}}]})["variables"][0]
check("motif respecté", es.controle_saisie(v_lot, "LOT-1"), "")
check("motif refusé", bool(es.controle_saisie(v_lot, "lot 1")), True)
v_qte = es.normaliser_layout({"variables": [{"nom": "q", "libelle": "Qté", "type": "saisie",
    "controle": {"type": "entier", "min": 1, "max": 500}}]})["variables"][0]
check("plage : 0 refusé", es.controle_saisie(v_qte, "0"), "Qté : 1 au moins.")
check("plage : 12,5 refusé (entier)", es.controle_saisie(v_qte, "12,5"), "Qté : nombre entier attendu.")
v_ch = es.normaliser_layout({"variables": [{"nom": "c", "libelle": "Pays", "type": "saisie", "choix": ["FR", "DE"]}]})["variables"][0]
check("liste de choix", es.controle_saisie(v_ch, "IT"), "Pays : valeur hors de la liste.")

# ── 9. Multilingue, rouleau multi-poses, ellipse, arc ─────────────────────
lay_m = es.normaliser_layout({"langues": ["fr", "en"], "planche": {"type": "rouleau", "poses": 3, "espace_h_mm": 2},
    "elements": [{"id": "t", "type": "texte", "x": 1, "y": 1, "valeur": "Lot {{lot}}", "traductions": {"en": "Batch {{lot}}"}},
                 {"id": "a", "type": "texte", "x": 1, "y": 9, "valeur": "ARC", "arc": {"rayon_mm": 10}},
                 {"id": "o", "type": "ellipse", "x": 20, "y": 1, "largeur": 8, "hauteur": 5}],
    "variables": [{"nom": "lot", "libelle": "Lot", "type": "saisie"}]})
vals_m = [es.valeurs_etiquette(lay_m, {}, i, {"lot": f"L{i}", "_langue": "en" if i == 1 else "fr"}) for i in range(4)]
z = es.rendre_lot(lay_m, 30, 20, 203, vals_m)
check("3 poses de front : 2 rangées", z.count("^XA"), 2)
check("pose décalée par ^LH", "^LH256,0" in z, True)
check("variante anglaise", "Batch L1" in z and "Lot L0" in z, True)
check("texte en arc tramé", z.count("^GFA") >= 4, True)
check("ellipse ^GE", "^GE" in z, True)

# ── 10. Validation : la production imprime la version approuvée ───────────
from app.services import etiq_validation as ev  # noqa: E402
spec = importlib.util.spec_from_file_location("mv", RACINE / "app/core/migrations/2026_10_22_etiq_validation_modeles.py")
mv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mv)
mv.appliquer(conn)
mv.appliquer(conn)
check("reprise : modèle en service approuvé", conn.execute("SELECT statut_validation, version_approuvee FROM etiq_modeles WHERE id=1").fetchone()[:], ("approuve", 1))
conn.execute("UPDATE etiq_modeles SET layout_json=?, version=3, version_approuvee=2, statut_validation='brouillon' WHERE id=1",
             (json.dumps({"elements": [{"type": "texte", "x": 1, "y": 1, "valeur": "BROUILLON"}]}),))
conn.execute("INSERT INTO etiq_modeles_versions (modele_id,version,nom,largeur_mm,hauteur_mm,dpi,layout_json,created_at)"
             " VALUES (1,2,'M',100,150,203,?,'x')", (json.dumps({"elements": [{"type": "texte", "x": 1, "y": 1, "valeur": "APPROUVÉE"}]}),))
prod = ev.modele_production(conn, 1)
check("production = version approuvée, pas le brouillon", (prod["version"], prod["layout"]["elements"][0]["valeur"]), (2, "APPROUVÉE"))
conn.execute("INSERT INTO etiq_modeles (dossier_id,nom,layout_json,created_at,updated_at) VALUES (1,'Neuve','{}','x','x')")
try:
    ev.modele_production(conn, 2)
    check("jamais approuvée : impression refusée", False)
except es.EtiquetteInvalide:
    check("jamais approuvée : impression refusée", True)

print()
if ECHECS:
    print(f"{len(ECHECS)} échec(s)")
    sys.exit(1)
print("Tout est bon.")
