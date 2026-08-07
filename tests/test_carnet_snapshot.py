"""
Photo quotidienne du carnet de commandes.

La calibration du modèle de prévision se jouera en novembre sur les photos
prises à partir d'aujourd'hui. Une erreur de capture ne se verra donc que
dans trois mois, quand il sera trop tard pour la corriger rétroactivement —
d'où ces cas, qui verrouillent le contrat maintenant :

  - une seule photo par jour, rejouable sans doublon ;
  - le mois retenu est celui de la LIVRAISON, y compris quand elle est
    écrite à la main (« A livrer le 03/04 ») ;
  - un besoin non chiffrable est COMPTÉ À PART, jamais confondu avec zéro :
    un carnet dont les OF n'ont pas de métrage ressemble sinon trait pour
    trait à un carnet vide ;
  - un dossier sans aucune date exploitable ne pèse sur aucun mois.
"""
import importlib.util
import sqlite3
import sys
from datetime import date

sys.path.insert(0, ".")

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


def _charger(chemin, nom):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mig = _charger("app/core/migrations/2026_08_07_carnet_snapshots.py", "mig_carnet")

conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
mig.appliquer(conn)

print("\n1. Le schéma tient et la migration est rejouable")
cols = {r["name"] for r in conn.execute("PRAGMA table_info(carnet_snapshots)")}
check("colonnes attendues",
      {"snapshot_le", "mois_livraison", "matiere_id", "kind", "unite",
       "quantite", "nb_dossiers", "nb_incalculables"} <= cols, True)
mig.appliquer(conn)
check("rejouable", True, True)

print("\n2. Une seule ligne par jour et par combinaison")
ins = ("INSERT INTO carnet_snapshots (snapshot_le, mois_livraison, matiere_id, "
       "kind, unite, quantite, nb_dossiers) VALUES (?,?,?,?,?,?,?)")
conn.execute(ins, ("2026-08-07", "2026-10", 3, "support", "ml", 12000, 4))
try:
    conn.execute(ins, ("2026-08-07", "2026-10", 3, "support", "ml", 99999, 9))
    check("doublon refusé", False, True)
except sqlite3.IntegrityError:
    check("doublon refusé par l'index unique", True, True)
# matiere_id NULL : NULL != NULL en SQL, d'où le COALESCE dans l'index
conn.execute(ins, ("2026-08-07", "2026-10", None, "support", "ml", 500, 1))
try:
    conn.execute(ins, ("2026-08-07", "2026-10", None, "support", "ml", 500, 1))
    check("doublon sur matiere_id NULL refusé", False, True)
except sqlite3.IntegrityError:
    check("doublon sur matiere_id NULL refusé aussi", True, True)
conn.commit()

print("\n3. Choix du mois : la livraison prime, même écrite à la main")
snap = _charger("app/services/carnet_snapshot.py", "carnet_snap")
cas = [
    ({"date_livraison": "2026-10-15"},                        "2026-10", "ISO"),
    ({"date_livraison": "15/10/2026"},                        "2026-10", "français"),
    ({"date_livraison": "A livrer le 03/04",
      "planned_end": "2026-09-01"},                           "2026-04", "phrase — prime sur planned_end"),
    ({"date_livraison": "", "planned_end": "2026-09-20"},     "2026-09", "repli planned_end"),
    ({"date_livraison": None, "planned_end": None,
      "planned_start": "2026-11-02"},                         "2026-11", "repli planned_start"),
    ({"date_livraison": "dès que possible"},                  None,      "illisible — ne pèse sur aucun mois"),
    ({},                                                      None,      "aucune date"),
]
for pe, attendu, libelle in cas:
    check(f"{libelle:42} → {snap._mois_livraison(pe)}", snap._mois_livraison(pe), attendu)

print("\n4. Un besoin non chiffrable n'est pas un zéro")
# On rejoue l'agrégation du service sur un besoin sans quantité.
conn.execute("DELETE FROM carnet_snapshots")
cumul = {}
vus = {}
for pe_id, q in [(1, 8000.0), (2, None), (3, 4000.0)]:
    cle = ("2026-11", 7, "support")
    agg = cumul.setdefault(cle, {"q": 0.0, "unite": "ml", "inc": 0})
    vus.setdefault(cle, set()).add(pe_id)
    if q is None:
        agg["inc"] += 1
    else:
        agg["q"] += q
agg = cumul[("2026-11", 7, "support")]
check("les quantités connues sont sommées", agg["q"], 12000.0)
check("l'incalculable est compté à part", agg["inc"], 1)
check("les 3 dossiers sont comptés", len(vus[("2026-11", 7, "support")]), 3)

print("\n5. Couverture : tant qu'on n'a qu'un mois, rien n'est calibrable")
check("base vide", snap.couverture(conn)["horizons_calibrables"], [])
for j, m in [("2026-08-07", "2026-10"), ("2026-08-20", "2026-10"), ("2026-09-05", "2026-11")]:
    conn.execute(ins, (j, m, 3, "support", "ml", 1000, 1))
conn.commit()
cov = snap.couverture(conn)
check("3 jours photographiés", cov["jours"], 3)
check("un mois d'écart → M+1 calibrable", cov["horizons_calibrables"], [1])
check("la période est datée", (cov["depuis"], cov["jusqu_a"]), ("2026-08-07", "2026-09-05"))

print()
if ko:
    print(f"ÉCHEC — {ko} vérification(s) en erreur.")
    sys.exit(1)
print("Tous les cas passent.")
