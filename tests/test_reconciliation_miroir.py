# -*- coding: utf-8 -*-
"""Le monitoring alimenté par le miroir : même snapshot qu'un import Excel."""
import ast, sqlite3, sys, types

import os
SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "app", "routers", "reconciliation.py")

# On charge les fonctions pures du routeur sans monter l'application : le
# fichier importe fastapi, calamine et le reste de MySifa, dont on n'a besoin
# pour rien ici.
arbre = ast.parse(open(SRC, encoding="utf-8").read())
garde = {"_cell_str", "_load_mysifa_index", "_build_reconciliation_lines",
         "_snapshot_counts", "_ecrire_snapshot", "_now_paris_iso", "_source_miroir"}
mod = ast.Module(body=[n for n in arbre.body
                       if isinstance(n, ast.FunctionDef) and n.name in garde], type_ignores=[])
ns = {"_PARIS": __import__("zoneinfo").ZoneInfo("Europe/Paris"),
      "datetime": __import__("datetime").datetime,
      "_resolve_created_by_name": lambda conn, user: user.get("nom") or "",
      "Any": object, "Optional": object, "sqlite3": sqlite3}
exec(compile(mod, SRC, "exec"), ns)

erreurs = []
def ok(cond, quoi):
    print(("  OK   " if cond else "  ECHEC") + " " + quoi)
    if not cond: erreurs.append(quoi)

# ── Une base MySifa minimale, et un index « miroir » de la forme rendue par
#    erp_stock.index_stock() ────────────────────────────────────────────────
conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.executescript("""
CREATE TABLE produits(id INTEGER PRIMARY KEY, reference TEXT, designation TEXT, unite TEXT);
CREATE TABLE lots_stock(id INTEGER PRIMARY KEY, produit_id INT, quantite_restante REAL, date_entree TEXT);
CREATE TABLE reconciliation_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT, created_by_name TEXT, source_filename TEXT, nb_refs_erp INT,
  nb_refs_mysifa INT, nb_matched INT, nb_ecarts INT, nb_sans_corresp INT, nb_negatifs INT);
CREATE TABLE reconciliation_lines(id INTEGER PRIMARY KEY AUTOINCREMENT, snapshot_id INT,
  reference TEXT, designation TEXT, unite TEXT, stock_erp REAL, stock_mysifa REAL,
  ecart REAL, statut TEXT, erp_dernier_mvt_libelle TEXT, erp_dernier_mvt_date TEXT,
  erp_dernier_mvt_qte REAL, mysifa_date_fifo TEXT);
INSERT INTO produits VALUES (1,'890/0079','Etiquette 75 x 52','u'),
                            (2,'890/0112','Etiquette 100 x 210','u'),
                            (3,'999/0001','Connu de MySifa seul','u');
INSERT INTO lots_stock VALUES (1,1,6500000,'2026-08-03'),(2,2,120000,'2026-08-01'),
                              (3,3,4200,'2026-07-30');
""")

MIROIR = {
  "890/0079": {"stock_erp": 6500000.0, "designation": "Etiquette 75 x 52",
               "mvt_libelle": "RESTE A REPIQUER", "mvt_date": "2026-08-03", "mvt_qte": 6500000.0},
  "890/0112": {"stock_erp": 128000.0, "designation": "Etiquette 100 x 210",
               "mvt_libelle": "Livraison du 07/08", "mvt_date": "2026-08-07", "mvt_qte": -1500000.0},
  "965/0001": {"stock_erp": -5824000.0, "designation": "Stock négatif RVGI",
               "mvt_libelle": "Livraison", "mvt_date": "2026-08-24", "mvt_qte": -5824000.0},
  "965/0009": {"stock_erp": 0.0, "designation": "Dormant", "mvt_libelle": None,
               "mvt_date": None, "mvt_qte": None},
}

print("— la comparaison")
ms = ns["_load_mysifa_index"](conn)
lignes = ns["_build_reconciliation_lines"](MIROIR, ms)
par_ref = {l["reference"]: l for l in lignes}
ok(par_ref["890/0079"]["statut"] == "ok", "un stock identique est « ok »")
ok(par_ref["890/0112"]["statut"] == "ecart" and par_ref["890/0112"]["ecart"] == -8000,
   "un écart est chiffré dans le sens MySifa − RVGI : %s" % par_ref["890/0112"]["ecart"])
ok(par_ref["999/0001"]["statut"] == "sans_corresp_erp", "une réf. inconnue de RVGI est signalée")
ok(par_ref["965/0001"]["statut"] == "sans_corresp_mysifa", "et l'inverse aussi")
ok("965/0009" not in par_ref, "une réf. à stock nul des deux côtés n'encombre pas la liste")
ok(par_ref["890/0112"]["erp_dernier_mvt_libelle"] == "Livraison du 07/08",
   "le dernier mouvement RVGI est repris tel quel")

print("— le compte")
c = ns["_snapshot_counts"](lignes, MIROIR, ms)
ok(c["nb_refs_erp"] == 4 and c["nb_refs_mysifa"] == 3, "les deux volumétries sont gardées")
ok(c["nb_matched"] == 2, "2 références communes")
ok(c["nb_ecarts"] == 1, "1 écart")
ok(c["nb_negatifs"] == 1, "le stock négatif de RVGI est compté")

print("— l'enregistrement")
res = ns["_ecrire_snapshot"](conn, MIROIR, "Miroir RVGI — relevé du 2026-08-25 09:02",
                            {"nom": "Eugène"})
conn.commit()
snap = conn.execute("SELECT * FROM reconciliation_snapshots WHERE id=?", (res["snapshot_id"],)).fetchone()
ok(snap["source_filename"].startswith("Miroir RVGI"), "la source dit d'où vient le snapshot : "
   + snap["source_filename"])
ok(snap["nb_ecarts"] == 1, "les compteurs sont écrits sur le snapshot")
n = conn.execute("SELECT COUNT(*) FROM reconciliation_lines WHERE snapshot_id=?",
                 (res["snapshot_id"],)).fetchone()[0]
ok(n == len(lignes), "toutes les lignes sont écrites (%d)" % n)

print("— la source porte la date de RELEVÉ, pas celle du clic")
s1 = ns["_source_miroir"]({"releve_le": "2026-08-25T09:02:53"})
s2 = ns["_source_miroir"]({"releve_le": "2026-08-25T09:02:53"})
ok(s1 == s2 == "Miroir RVGI — relevé du 2026-08-25 09:02",
   "deux comparaisons du même relevé portent la même source : " + s1)
ok(ns["_source_miroir"]({}) == "Miroir RVGI", "et un relevé inconnu ne fabrique pas de date")

print("\nTout passe." if not erreurs else "\n%d ECHEC(S)" % len(erreurs))
sys.exit(1 if erreurs else 0)
