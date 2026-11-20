"""
ADV : le carnet et sa chaîne de valeur (app/services/adv_commandes.py).

Ce que ce test protège :

1. **Le même carnet que l'ERP.** Ni frais de port (ligne sans référence), ni
   ligne soldée, ni ligne orpheline de son entête.
2. **Le stock est celui de MyStock, et il est partagé.** Deux lignes du même
   article ne revendiquent pas les mêmes étiquettes : la plus urgente est
   servie d'abord, les lots partent en FIFO — sauf une prépa déjà engagée,
   dont les étiquettes sont mises de côté.
3. **Un dossier se rattache par son numéro ET son article** (ou sa ligne
   « - L<n> ») ; un rattachement explicite fait foi.
4. **La fin de prod réelle** (saisie 89) l'emporte sur la fin planifiée.
5. **Un forçage ADV** remplace la valeur affichée sans effacer le calcul.
6. **L'onglet Prépa** range chaque ligne dans le bon groupe.

Bases temporaires : aucune base réelle n'est lue.
"""
import os
import sqlite3
import sys
import tempfile
from datetime import date, timedelta

sys.path.insert(0, ".")
# Aucune base réelle : même si un import tirait la base applicative, il
# tomberait sur un fichier temporaire.
_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmp, "jamais.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "jamais_erp.db")
from app.services import erp_mirror as miroir    # noqa: E402
from app.services import adv_commandes as adv    # noqa: E402

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


AUJ = adv.aujourdhui_paris()


def jour(n, heure="00:00:00"):
    return (AUJ + timedelta(days=n)).isoformat() + " " + heure


dossier = tempfile.mkdtemp()

# ── Miroir RVGI ──────────────────────────────────────────────────────────────
m = sqlite3.connect(os.path.join(dossier, "miroir.db"))
m.executescript("""
CREATE TABLE cde_entete(id INTEGER PRIMARY KEY, numero INTEGER, rs TEXT, vref TEXT, amjc TEXT);
CREATE TABLE cde_ligne(id INTEGER PRIMARY KEY, numero INTEGER, ligne INTEGER, lpos INTEGER,
    qte REAL, qtep REAL, amje TEXT, amjl TEXT, orig INTEGER, code1 TEXT, code2 TEXT,
    des1 TEXT, vref TEXT);
CREATE TABLE vte_ligne(id INTEGER PRIMARY KEY, code1 TEXT, code2 TEXT);
CREATE TABLE liv_entete(id INTEGER PRIMARY KEY, numero INTEGER);
CREATE TABLE liv_ligne(id INTEGER PRIMARY KEY, numero INTEGER, numcde INTEGER, lignecde INTEGER, qte REAL);
""")
m.executemany("INSERT INTO cde_entete(numero, rs, vref, amjc) VALUES (?,?,?,?)", [
    (9930001, "CLIENT A", "PO-1", jour(-20)),
    (9930002, "CLIENT B", None, jour(-10)),
    (9930003, "CLIENT C", None, jour(-5)),
])
m.executemany("""INSERT INTO cde_ligne(numero, ligne, lpos, qte, qtep, amje, amjl, orig, code1, code2, des1)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?)""", [
    (9930001, 1, 0, 1000, 1000, jour(-2), jour(0), 1, "100", "0001", "Etiquette A"),
    (9930001, 2, 0, 1, 1, jour(-2), jour(0), 1, "", "0", "Frais de port"),
    (9930002, 1, 0, 500, 9999, jour(3), jour(4), 1, "100", "0001", "Etiquette A bis"),
    (9930002, 2, 0, 300, 300, jour(5), jour(6), 1, "300", "0003", "Etiquette D"),
    (9930003, 1, 0, 50, 50, jour(4), jour(5), 2, "200", "0002", "Etiquette stock"),
    (9930003, 2, 2, 10, 10, jour(4), jour(5), 1, "200", "0002", "Soldée"),
    (9939999, 1, 0, 10, 10, jour(1), jour(2), 1, "100", "0001", "Orpheline"),
])
m.execute("INSERT INTO vte_ligne(code1, code2) VALUES ('200', '0002')")
m.execute("INSERT INTO liv_entete(numero) VALUES (500)")
# Un BL de 100 sur B, et un BL orphelin (entête à la corbeille) qui ne compte pas.
m.executemany("INSERT INTO liv_ligne(numero, numcde, lignecde, qte) VALUES (?,?,?,?)",
              [(500, 9930002, 1, 100), (501, 9930002, 1, 50), (500, 9930002, 2, 7)])
m.commit()
m.close()

# ── Base MySifa ──────────────────────────────────────────────────────────────
b = sqlite3.connect(os.path.join(dossier, "mysifa.db"))
b.executescript("""
CREATE TABLE machines(id INTEGER PRIMARY KEY, nom TEXT);
CREATE TABLE produits(id INTEGER PRIMARY KEY, reference TEXT, designation TEXT, unite TEXT);
CREATE TABLE lots_stock(id INTEGER PRIMARY KEY, produit_id INTEGER, emplacement TEXT,
    quantite_restante REAL, date_entree TEXT);
CREATE TABLE bat_entries(id INTEGER PRIMARY KEY, numero_article TEXT, statut TEXT,
    description TEXT, updated_at TEXT);
CREATE TABLE planning_entries(id INTEGER PRIMARY KEY, reference TEXT, numero_of TEXT,
    ref_produit TEXT, statut TEXT, statut_reel TEXT, planned_start TEXT, planned_end TEXT,
    machine_id INTEGER, client TEXT, of_import_id INTEGER);
CREATE TABLE production_data(id INTEGER PRIMARY KEY, planning_entry_id INTEGER,
    operation_code TEXT, date_operation TEXT, est_annule INTEGER);
CREATE TABLE rvgi_rattachements(id INTEGER PRIMARY KEY, piece TEXT, objet TEXT,
    objet_id INTEGER, numero TEXT, ligne INTEGER);
CREATE TABLE expe_departs(id INTEGER PRIMARY KEY, date_enlevement TEXT, date_livraison TEXT,
    transporteur TEXT, statut TEXT, arc TEXT, ref_sifa TEXT, no_bl TEXT,
    planning_entry_id INTEGER, parti_le TEXT);
CREATE TABLE expe_depart_dossiers(id INTEGER PRIMARY KEY, depart_id INTEGER, planning_entry_id INTEGER);
""")
import importlib.util  # noqa: E402  (la vraie migration crée les tables ADV)
spec = importlib.util.spec_from_file_location(
    "mig_adv", "app/core/migrations/2026_11_20_adv_suivi_commandes.py")
mig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mig)
mig.appliquer(b)
mig.appliquer(b)                      # rejouable
b.executescript(f"""
INSERT INTO machines(id, nom) VALUES (1, 'Machine 1');
INSERT INTO produits(id, reference, designation, unite) VALUES
    (1, '100/0001', 'Etiquette A', 'étiquette'),
    (2, '100/0001 - BOX', 'Etiquette A en box', 'carton'),
    (3, '300/0003', 'Etiquette D', 'étiquette');
INSERT INTO lots_stock(id, produit_id, emplacement, quantite_restante, date_entree) VALUES
    (1, 1, 'E2', 600, '{jour(-1)}'),
    (2, 1, 'E1', 600, '{jour(-30)}'),
    (3, 2, 'BOX', 99, '{jour(-40)}'),
    (4, 3, 'D1', 0, '{jour(-40)}');
INSERT INTO bat_entries(id, numero_article, statut, updated_at) VALUES
    (1, '100/1', 'valide', '{jour(-50)}'),
    (2, '300/0003', 'en_attente', '{jour(-1)}');
INSERT INTO planning_entries(id, reference, numero_of, ref_produit, statut, statut_reel,
    planned_start, planned_end, machine_id) VALUES
    (10, '9930001 - L1', '9930001 - L1', '100/0001', 'termine', NULL, '{jour(-4)}', '{jour(-3, "10:00:00")}', 1),
    (11, '9930002 - L2', '9930002 - L2', '', 'attente', NULL, '{jour(4)}', '{jour(4, "18:00:00")}', 1),
    (12, '9930002 - L7', '9930002 - L7', '', 'attente', NULL, '{jour(2)}', '{jour(2)}', 1),
    (13, 'Autre', 'Autre', '100/0001', 'en_cours', 'reellement_en_saisie', '{jour(0)}', '{jour(1)}', 1);
INSERT INTO production_data(planning_entry_id, operation_code, date_operation, est_annule) VALUES
    (10, '89', '{jour(-3)[:10]}T14:30:00', 0),
    (10, '89', '{jour(-1)[:10]}T09:00:00', 1);
INSERT INTO rvgi_rattachements(piece, objet, objet_id, numero, ligne) VALUES
    ('commande', 'dossier', 13, '9930002', 1);
INSERT INTO expe_departs(id, date_enlevement, transporteur, statut, arc) VALUES
    (100, '{jour(1)[:10]}', 'TRANSP', 'valide', 'Cde 9930001'),
    (101, '{jour(6)[:10]}', 'TRANSP', 'en_attente', NULL);
INSERT INTO expe_depart_dossiers(depart_id, planning_entry_id) VALUES (101, 11);
INSERT INTO adv_forcages(numero, ligne, etape, valeur, note, maj_le, maj_par) VALUES
    ('9930003', 1, 'bat', 'non', 'Nouveau visuel', '{jour(0)}', 'ADV');
""")
b.commit()
b.close()

miroir.ERP_MIRROR_DB = os.path.join(dossier, "miroir.db")
miroir.DB_PATH = os.path.join(dossier, "mysifa.db")

# ── 1. Le carnet ─────────────────────────────────────────────────────────────
d = adv.construire()
par = {l["cle"]: l for l in d["lignes"]}
print("\nCarnet")
check("frais de port, soldée et orpheline écartés", sorted(par),
      ["9930001-1", "9930002-1", "9930002-2", "9930003-1"])
check("compteur carnet", (d["compteurs"]["carnet"]["lignes"], d["compteurs"]["carnet"]["commandes"]), (4, 3))
check("retard", d["compteurs"]["retard"]["lignes"], 1)
check("tri par expédition", [l["cle"] for l in d["lignes"]],
      ["9930001-1", "9930002-1", "9930003-1", "9930002-2"])

A, B, C, D = par["9930001-1"], par["9930002-1"], par["9930003-1"], par["9930002-2"]

print("\nStock MyStock partagé, FIFO")
check("A servie d'abord, lots FIFO", [(e["emplacement"], e["quantite"]) for e in A["stock"]["emplacements"]],
      [("E1", 600.0), ("E2", 400.0)])
check("A : stock oui", A["etapes"]["stock"]["valeur"], "oui")
check("B : reste = qte − BL vivants, pas qtep", (B["reste"], B["besoin_rvgi"]), (400.0, 9999.0))
check("B : 200 en stock sur 400", (B["stock"]["alloue"], B["etapes"]["stock"]["valeur"]), (200.0, "en_cours"))
check("le lot en carton ne sert pas une ligne en étiquettes", A["stock"]["total"], 1200.0)
check("C : rien en stock", C["etapes"]["stock"]["valeur"], "non")

print("\nBAT")
check("BAT validé (référence « 100/1 » normalisée)", A["etapes"]["bat"]["valeur"], "oui")
check("BAT en attente", D["etapes"]["bat"]["valeur"], "en_cours")
check("forçage ADV affiché", (C["etapes"]["bat"]["valeur"], C["etapes"]["bat"]["force"]), ("non", True))
check("calcul conservé sous le forçage", C["etapes"]["bat"]["calcul"], "sans_objet")

print("\nProd et fin de prod")
check("A : dossier par numéro + article", [x["id"] for x in A["dossiers"]], [10])
check("A : prod terminée", A["etapes"]["prod"]["valeur"], "oui")
check("A : fin réelle (saisie 89 non annulée)", (A["fin_prod"][:10], A["fin_prod_reelle"]), (jour(-3)[:10], True))
check("B : le rattachement explicite fait foi", [x["id"] for x in B["dossiers"]], [13])
check("B : en production", B["etapes"]["prod"]["valeur"], "en_cours")
check("D : dossier par « - L2 », pas « - L7 »", [x["id"] for x in D["dossiers"]], [11])
check("D : fin planifiée", (D["fin_prod"][:10], D["fin_prod_reelle"]), (jour(4)[:10], False))
check("C : ligne sur stock, pas de prod", C["etapes"]["prod"]["valeur"], "sans_objet")

print("\nDépart")
check("A : départ par l'ARC", (A["etapes"]["depart"]["valeur"], [x["id"] for x in A["departs"]]), ("oui", [100]))
check("D : départ du dossier, à valider", (D["etapes"]["depart"]["valeur"], [x["id"] for x in D["departs"]]), ("en_cours", [101]))
check("C : aucun départ", C["etapes"]["depart"]["valeur"], "non")
check("étape bloquante de A : la prépa", A["bloquante"], "prepa")

# ── 2. Une prépa engagée garde ses étiquettes ────────────────────────────────
b = sqlite3.connect(miroir.DB_PATH)
b.execute("INSERT INTO adv_prepas(numero, ligne, statut, maj_le, maj_par) VALUES ('9930002', 1, 'en_cours', ?, 'LOG')",
          (jour(0),))
b.commit()
b.close()
d = adv.construire()
par = {l["cle"]: l for l in d["lignes"]}
print("\nPrépa engagée")
check("B engagée : servie en premier", (par["9930002-1"]["stock"]["alloue"], par["9930001-1"]["stock"]["alloue"]),
      (400.0, 800.0))
check("B : prépa en cours", par["9930002-1"]["etapes"]["prepa"]["valeur"], "en_cours")

# ── 3. L'onglet Prépa ────────────────────────────────────────────────────────
p = adv.prepa(horizon=4)
groupes = {l["cle"]: l["groupe"] for l in p["lignes"]}
print("\nOnglet Prépa")
check("groupes", groupes, {"9930001-1": "partiel", "9930002-1": "en_cours", "9930003-1": "attente"})
check("horizon : la ligne à J+5 hors champ", "9930002-2" in groupes, False)
check("compte par groupe", {g["cle"]: g["lignes"] for g in p["groupes"]},
      {"preparable": 0, "en_cours": 1, "partiel": 1, "attente": 1, "pretes": 0})

# ── 4. Miroir absent ─────────────────────────────────────────────────────────
miroir.ERP_MIRROR_DB = os.path.join(dossier, "absent.db")
d = adv.construire()
print("\nMiroir absent")
check("présent = False, aucune ligne", (d["present"], d["lignes"]), (False, []))

print()
if ko:
    print(f"test_adv_commandes : {ko} échec(s)")
    sys.exit(1)
print("test_adv_commandes : OK")
