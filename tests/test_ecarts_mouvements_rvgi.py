"""
Écarts de mouvements MySifa ↔ RVGI — ce qui doit rester vrai.

1. **Le type de `stm_hist` est celui de `mat_mat`**, soit le type d'achat moins
   2 : sans la correction, aucun mouvement ne rejoindrait son appariement.
2. **Les doublons de variante (type > 100) ne comptent pas** : RVGI écrit
   chaque réception deux fois, les compter doublerait les entrées.
3. **Un retour sur un dossier recule la sortie**, il ne gonfle pas les entrées.
4. **Le dossier se lit dans le libellé RVGI**, y compris « 9932376+377 ».
5. **Une réception saisie après la mise en service entre dans la file même si
   sa date de livraison est antérieure** — le filtre porte sur la saisie.
"""
import sqlite3
import sys

sys.path.insert(0, ".")
from app.services import ecarts_mouvements_rvgi as em   # noqa: E402
from app.services import reception_rvgi as rr           # noqa: E402

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


ms = sqlite3.connect(":memory:")
ms.row_factory = sqlite3.Row
ms.executescript("""
    CREATE TABLE matieres_premieres (id INTEGER PRIMARY KEY, categorie TEXT,
        sous_section TEXT, reference TEXT, designation TEXT, actif INTEGER DEFAULT 1,
        metres_lineaires_par_bobine REAL, unites_par_palette REAL);
    CREATE TABLE erp_article_matiere (code1 TEXT, code2 TEXT, type_code INTEGER,
        matiere_id INTEGER, origine TEXT, created_at TEXT, created_by_name TEXT,
        PRIMARY KEY (code1, code2, type_code));
    CREATE TABLE mp_mouvements (id INTEGER PRIMARY KEY, created_at TEXT,
        matiere_id INTEGER, laize_id INTEGER, type_mouvement TEXT, quantite REAL,
        planning_entry_id INTEGER, no_dossier TEXT, note TEXT, created_by_name TEXT);
    INSERT INTO matieres_premieres (id, categorie, sous_section, reference, designation,
        metres_lineaires_par_bobine, unites_par_palette) VALUES
        (1, 'adhesif', NULL, '2028Y', 'Adhésif permanent 2028Y', NULL, NULL),
        (2, 'frontal', 'Thermiques', 'ECO70', 'Thermique eco 70', 12000, NULL);
    INSERT INTO erp_article_matiere VALUES
        ('1055', '0005', 9, 1, 'manuel', '', ''),
        ('1183', '0004', 7, 2, 'manuel', '', '');
    -- MySifa : réception adhésif juste, sortie thermique dossier 9932366 de 1 bobine
    -- puis retour de 0,25 ; sortie manuelle hors dossier ignorée côté dossier.
    INSERT INTO mp_mouvements VALUES
        (1, '2026-09-08T10:40:00', 1, NULL, 'entree', 18000, NULL, NULL, 'Réception RVGI', 'Synchro'),
        (2, '2026-09-08T15:20:00', 2, 5, 'sortie', 1.0, 44, '9932366', 'Déstockage automatique 9932366', 'Auto'),
        (3, '2026-09-08T16:00:00', 2, 5, 'entree', 0.25, 44, '9932366', 'Ajustement déstockage 9932366', 'Anne'),
        (4, '2026-09-09T09:00:00', 1, NULL, 'ajustement', 7000, NULL, NULL, 'Inventaire', 'Anne');
""")

erp = sqlite3.connect(":memory:")
erp.row_factory = sqlite3.Row
erp.executescript("""
    CREATE TABLE stm_hist (id INTEGER, dtem TEXT, amjh TEXT, mvt INTEGER, type INTEGER,
        code1 TEXT, code2 TEXT, code3 TEXT, numcde INTEGER, ligne INTEGER,
        qte1 REAL, qte2 REAL, des1 TEXT, refbl TEXT);
    CREATE TABLE mat_mat (code1 TEXT, code2 TEXT, type INTEGER, corbeille INTEGER,
        libc1 TEXT, libt2 TEXT);
    INSERT INTO mat_mat VALUES
        ('1055', '0005', 7, 0, 'Adhésif Permanent, Hotmelt', 'JT-2028Y, Cart. de 25kg'),
        ('1183', '0004', 5, 0, 'Thermal ECO', 'Roll 12.000 ml'),
        ('1152', '0001', 2, 0, 'Glassine', 'R18.000 ml');
    INSERT INTO stm_hist VALUES
        (1, '', '2026-09-08 10:26:39', 3, 7,    '1055', '0005', NULL, 5893, 2, 18000, 0, 'Réception du 08/09/2026', 'JH'),
        (2, '', '2026-09-08 10:26:39', 3, 1107, '1055', '0005', NULL, 5893, 2, 18000, 0, 'Réception du 08/09/2026', 'JH'),
        (3, '', '2026-09-08 15:14:40', 2, 5,    '1183', '0004', '440', 0, 0, 12000, 0, '9932366 ligne 1', NULL),
        (4, '', '2026-09-08 15:26:20', 2, 5,    '1183', '0004', '570', 0, 0, 24000, 0, '9932376+377', NULL),
        (5, '', '2026-09-08 15:28:17', 2, 2,    '1152', '0001', '570', 0, 0, 46600, 0, '9932376+377', NULL),
        (6, '', '2026-09-09 17:26:53', 1, 1,    '629',  '0008', '333', 6059, 1, 0, 0, 'Création automatique Laize', NULL),
        (7, '', '2026-09-01 08:00:00', 2, 5,    '1183', '0004', '440', 0, 0, 99999, 0, 'hors fenêtre', NULL);
""")

res = em.comparer(ms, erp, "2026-09-08 00:00:00", "2026-09-10 00:00:00")
par = {x["reference"]: x for x in res["matieres"]}

print("1. Entrées")
check("adhésif : réception RVGI rejointe malgré le décalage de type", par["2028Y"]["entrees_rvgi"], 18000.0)
check("adhésif : le doublon de variante n'est pas compté deux fois", par["2028Y"]["statut_entrees"], "ok")
check("l'inventaire MySifa est compté à part", res["resume"]["ajustements_mysifa"], 1)

print("2. Sorties")
check("thermique : 36 000 ml RVGI = 3 bobines", par["ECO70"]["sorties_rvgi"], 3.0)
check("thermique : sortie MySifa nette du retour (1 − 0,25)", par["ECO70"]["sorties_mysifa"], 0.75)
check("thermique : écart signalé", par["ECO70"]["statut_sorties"], "ecart")
check("le mouvement hors fenêtre est ignoré", len(par["ECO70"]["mouvements_rvgi"]), 2)

print("3. Dossiers")
dos = {d["dossier"]: d for d in res["dossiers"]}
check("9932376+377 ouvre deux dossiers", sorted(k for k in dos if k.startswith("99323")),
      ["9932366", "9932376", "9932377"])
check("9932366 : 1 bobine RVGI contre 0,75 MySifa", dos["9932366"]["matieres"][0]["statut"], "ecart")
check("9932376 : absent de MySifa", dos["9932376"]["statut"], "absent_mysifa")

print("4. Non appariés")
na = {x["article"]: x for x in res["non_apparies"]}
check("la glassine 1152/0001 est à apparier", "1152/0001" in na, True)
check("avec son type d'achat, pas celui de stm_hist", na["1152/0001"]["type_code"], 4)
check("la création de laize (mvt 1) n'est pas un mouvement comparé",
      res["resume"]["mouvements_rvgi_ignores"], 1)

print("5. Fenêtre")
d, f = em.fenetre(debut="2026-09-08", fin="2026-09-09")
check("« jusqu'au 09/09 » inclut le 09/09", (d, f), ("2026-09-08 00:00:00", "2026-09-10 00:00:00"))

print("6. File des réceptions : filtre sur la saisie")
sql = rr._SQL_LIGNES
check("le filtre ne porte plus sur la date de livraison", "l.amjl, 1, 10) >= ?" in sql, False)
check("il porte sur l'ordre de saisie", "MAX(x.id)" in sql and "x.dtem" in sql, True)

print("7. Une seule entrée de stock par bobine")
src_stock = open("app/routers/stock.py", encoding="utf-8").read()
corps = src_stock[src_stock.index("def _scan_alimente_stock("):]
corps = corps[:corps.index("@router.post")]
ns = {"sqlite3": sqlite3, "_now_paris": lambda: __import__("datetime").datetime(2026, 9, 10, 12)}
exec(corps, ns)
base = sqlite3.connect(":memory:")
base.row_factory = sqlite3.Row
base.execute("CREATE TABLE stock_config (cle TEXT PRIMARY KEY, valeur TEXT)")
check("sans mise en service, le scan alimente le stock", ns["_scan_alimente_stock"](base), True)
base.execute("INSERT INTO stock_config VALUES ('reception_rvgi_depuis', '2026-09-09')")
check("intégration RVGI en service : le scan ne fait que tracer", ns["_scan_alimente_stock"](base), False)
base.execute("UPDATE stock_config SET valeur='2026-09-20'")
check("mise en service future : rien ne change encore", ns["_scan_alimente_stock"](base), True)
src_pont = open("app/routers/api_bridge.py", encoding="utf-8").read()
check("la synchro du miroir intègre les réceptions avant de comparer les stocks",
      src_pont.index("_integrer_les_receptions(lignes_journal)")
      < src_pont.index("_comparer_les_stocks(lignes_journal)"), True)

print()
if ko:
    print(f"ÉCHEC — {ko} vérification(s) en erreur.")
    sys.exit(1)
print("Tous les cas passent.")
