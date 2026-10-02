"""
Comparaison des stocks matières MySifa / RVGI (`stock_compare._comparer_matiere`).

Ce que le test verrouille :
- la clé est l'appariement des réceptions (erp_article_matiere), pas une
  chaîne de référence identique des deux côtés ;
- RVGI tient le stock PAR LAIZE : chaque laize garde le `qte2` de son dernier
  mouvement, et la comparaison se fait matière par matière, laize par laize ;
- la quantité RVGI passe dans l'unité du magasin (ml → bobines) ;
- les doublons de variante (type >= 100) ne comptent pas ;
- article apparié sans stock MySifa, stock MySifa sans article, article non
  apparié : chacun son statut.

Lancer : python3 tests/test_stock_compare_matieres.py
"""

import os
import sqlite3
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))
os.chdir(RACINE)

from app.services import stock_compare as sc  # noqa: E402

FAIL = []


def check(label, got, expected):
    ok = got == expected
    print(("ok   " if ok else "KO   ") + label.ljust(64) + f"{got!r}"
          + ("" if ok else f"   attendu {expected!r}"))
    if not ok:
        FAIL.append(label)


ms = sqlite3.connect(":memory:")
ms.row_factory = sqlite3.Row
ms.executescript("""
    CREATE TABLE matieres_premieres (id INTEGER PRIMARY KEY, categorie TEXT, sous_section TEXT,
        reference TEXT, designation TEXT, actif INTEGER DEFAULT 1,
        metres_lineaires_par_bobine REAL, unites_par_palette REAL);
    CREATE TABLE erp_article_matiere (code1 TEXT, code2 TEXT, type_code INTEGER, matiere_id INTEGER);
    CREATE TABLE mp_laizes (id INTEGER PRIMARY KEY, valeur_mm REAL);
    CREATE TABLE mp_stock (matiere_id INTEGER, quantite REAL, updated_at TEXT);
    CREATE TABLE mp_stock_laize (matiere_id INTEGER, laize_id INTEGER, quantite REAL, updated_at TEXT);
    INSERT INTO matieres_premieres VALUES
        (1, 'adhesif', NULL, '2028Y', 'Adhésif permanent', 1, NULL, NULL),
        (2, 'frontal', 'Thermiques', 'ECO70', 'Thermique Eco 70 g/m²', 1, 12000, NULL);
    INSERT INTO erp_article_matiere VALUES ('1055', '0005', 9, 1), ('1183', '0004', 7, 2);
    INSERT INTO mp_laizes VALUES (10, 510), (11, 570), (12, 440);
    INSERT INTO mp_stock VALUES (1, 18000, '2026-10-01'), (2, 17, '2026-10-01');
    INSERT INTO mp_stock_laize VALUES (2, 10, 10, '2026-10-01'), (2, 11, 3, '2026-10-01'),
                                      (2, 12, 4, '2026-10-01');
""")

erp = sqlite3.connect(":memory:")
erp.row_factory = sqlite3.Row
erp.executescript("""
    CREATE TABLE stm_hist (id INTEGER, amjh TEXT, mvt INTEGER, type INTEGER, code1 TEXT, code2 TEXT,
        code3 TEXT, qte1 REAL, qte2 REAL, des1 TEXT);
    CREATE TABLE mat_mat (code1 TEXT, code2 TEXT, type INTEGER, corbeille INTEGER, libc1 TEXT, libt2 TEXT);
    INSERT INTO mat_mat VALUES ('1183', '0004', 5, 0, 'Thermal ECO', 'Roll 12.000 ml'),
                               ('1055', '0005', 7, 0, 'Hotmelt', 'Cart. de 25kg'),
                               ('1152', '0001', 2, 0, 'Glassine 62 g', 'R18.000 ml');
    INSERT INTO stm_hist VALUES
        (1, '2026-09-20 08:00:00', 3, 5,    '1183', '0004', '510', 144000, 144000, 'Réception'),
        (2, '2026-09-25 09:00:00', 2, 5,    '1183', '0004', '510', 24000,  120000, '9932500'),
        (3, '2026-09-28 10:00:00', 2, 5,    '1183', '0004', '570', 12000,  24000,  '9932561'),
        (4, '2026-09-29 10:00:00', 3, 1105, '1183', '0004', '510', 0,      999999, 'doublon de variante'),
        (5, '2026-09-26 10:00:00', 2, 7,    '1055', '0005', NULL,  200,    18000,  'Sortie'),
        (6, '2026-09-27 10:00:00', 3, 2,    '1152', '0001', '570', 46600,  46600,  'Réception'),
        (7, '1899-12-30 00:00:00', 0, 5,    '1183', '0004', NULL,  0,      99999999999.99, NULL);
""")

res = sc._comparer_matiere(ms, erp)
par = {l["reference"]: l for l in res["lignes"]}

check("510 : dernier mouvement de la laize, 120 000 ml = 10 bobines", par["ECO70 · 510 mm"]["stock_rvgi"], 10.0)
check("510 : d'accord avec MySifa", par["ECO70 · 510 mm"]["statut"], "ok")
check("570 : laize lue à part (24 000 ml = 2 bobines)", par["ECO70 · 570 mm"]["stock_rvgi"], 2.0)
check("570 : écart signalé (+1 bobine)", (par["ECO70 · 570 mm"]["statut"], par["ECO70 · 570 mm"]["ecart"]), ("ecart", 1.0))
check("440 : stock MySifa sans laize RVGI", par["ECO70 · 440 mm"]["statut"], "mysifa_seul")
check("le doublon de variante (type 1105) est ignoré", "999999" in str(res), False)
check("la ligne d'initialisation de fiche (mvt 0, 1899) n'est pas un stock",
      [l["reference"] for l in res["lignes"] if l["reference"] == "ECO70"], [])
check("adhésif : clé par appariement, au kilo, sans laize", (par["2028Y"]["stock_rvgi"], par["2028Y"]["statut"]), (18000.0, "ok"))
check("article non apparié porteur de stock", par["1152/0001 · 570 mm"]["statut"], "rvgi_seul")
check("l'article RVGI est nommé sur la ligne", "1183/0004" in par["ECO70 · 510 mm"]["designation"], True)
check("taux de correspondance = lignes RVGI qui trouvent leur matière",
      res["compte"]["taux_correspondance"], round(100 * 3 / 4, 1))

# ── Stock par fournisseur (app/services/stock_fournisseurs.py) ──────────────
from app.services.stock_fournisseurs import stock_par_fournisseur  # noqa: E402

ms.executescript("""
    CREATE TABLE fournisseurs_fsc (id INTEGER PRIMARY KEY, nom TEXT, rvgi_numero INTEGER, actif INTEGER DEFAULT 1);
    CREATE TABLE mp_variantes (id INTEGER PRIMARY KEY, matiere_id INTEGER, fournisseur_id INTEGER,
        libelle_technique TEXT, rvgi_code1 TEXT, rvgi_code2 TEXT, rvgi_type_code INTEGER,
        ml_bobine REAL, actif INTEGER DEFAULT 1);
    INSERT INTO fournisseurs_fsc VALUES (7, 'Likexin', 1183, 1), (8, 'Bostik', NULL, 1);
    INSERT INTO mp_variantes VALUES (70, 1, 8, 'Hotmelt 2028Y', '1055', '0005', 9, NULL, 1);
""")
sf = stock_par_fournisseur(ms, conn_erp=erp)
par_cle = {(l["matiere_id"], l["fournisseur"], l["laize_mm"]): l for l in sf["lignes"]}
check("fournisseur par numéro RVGI (code1), laize 510 en mètres",
      par_cle[(2, "Likexin", 510.0)]["metres"], 120000.0)
check("même fournisseur, laize 570 à part", par_cle[(2, "Likexin", 570.0)]["metres"], 24000.0)
check("fournisseur par la variante, adhésif au kilo",
      (par_cle[(1, "Bostik", None)]["quantite"], par_cle[(1, "Bostik", None)]["metres"]), (18000.0, None))
check("fournisseur : pas de « laize vide » à cent milliards de mètres",
      any((l["metres"] or 0) > 1e9 for l in sf["lignes"]), False)
check("article non apparié ignoré", any(l["article"] == "1152/0001" for l in sf["lignes"]), False)
check("une seule matière demandée", {l["matiere_id"] for l in stock_par_fournisseur(ms, 2, conn_erp=erp)["lignes"]}, {2})

print()
if FAIL:
    print("ÉCHEC : %d contrôle(s) en erreur" % len(FAIL))
    sys.exit(1)
print("Comparaison des stocks matières : tout est vert.")
