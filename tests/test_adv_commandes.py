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
    (101, '{jour(6)[:10]}', 'TRANSP', 'en_attente', NULL),
    (102, '{jour(-20)[:10]}', 'TRANSP', 'valide', 'Envoi précédent 9930003');
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
check("B : jauge du stock à 50 %, unité accordée", (B["etapes"]["stock"]["jauge"], B["etapes"]["stock"]["detail"]),
      (0.5, "Stock partiel : 200 étiquettes sur 400 (50 %)"))
check("le lot en carton ne sert pas une ligne en étiquettes", A["stock"]["total"], 1200.0)
check("C : rien en stock", C["etapes"]["stock"]["valeur"], "non")
check("à fabriquer = reste à livrer − stock attribué", (A["a_fabriquer"], B["a_fabriquer"], C["a_fabriquer"]),
      (0.0, 200.0, 50.0))

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
check("C : un départ passé ne « prévoit » rien", (C["etapes"]["depart"]["valeur"], [x["id"] for x in C["departs"]]),
      ("non", [102]))
check("C : le détail cite le dernier départ", C["etapes"]["depart"]["detail"].startswith("Aucun départ à venir"), True)
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

# ── 3 bis. Ordre fixé à la main par l'ADV ────────────────────────────────────
spec_o = importlib.util.spec_from_file_location(
    "mig_ordre", "app/core/migrations/2026_11_24_adv_prepa_priorites.py")
mig_o = importlib.util.module_from_spec(spec_o)
spec_o.loader.exec_module(mig_o)
b = sqlite3.connect(miroir.DB_PATH)
mig_o.appliquer(b)
mig_o.appliquer(b)                    # rejouable
# B n'est plus engagée, mais l'ADV la place en tête ; D (J+5, hors horizon)
# est placée juste après.
b.execute("DELETE FROM adv_prepas WHERE numero='9930002' AND ligne=1")
b.executemany("INSERT INTO adv_prepa_priorites(numero, ligne, rang, maj_le, maj_par) VALUES (?,?,?,?,?)",
              [("9930002", 1, 1, jour(0), "ADV"), ("9930002", 2, 2, jour(0), "ADV")])
b.commit()
b.close()
d = adv.construire()
par = {l["cle"]: l for l in d["lignes"]}
print("\nOrdre fixé à la main")
check("le rang voyage avec la ligne", (par["9930002-1"]["priorite_manuelle"], par["9930001-1"]["priorite_manuelle"]), (1, None))
check("le stock va d'abord à la ligne placée en tête",
      (par["9930002-1"]["stock"]["alloue"], par["9930001-1"]["stock"]["alloue"]), (400.0, 800.0))
p = adv.prepa(horizon=4)
ordre = [l["cle"] for l in p["lignes"]]
check("une ligne placée à la main reste visible hors horizon", "9930002-2" in ordre, True)
check("les lignes placées passent avant l'ordre par date", ordre[:2], ["9930002-1", "9930002-2"])
check("l'ordre manuel est signalé", p["ordre_manuel"], True)

# ── 3 ter. Repiquage ─────────────────────────────────────────────────────────
from app.services import machines_type as mtype  # noqa: E402


def _migrer(fichier):
    sp = importlib.util.spec_from_file_location("mig_" + fichier, "app/core/migrations/" + fichier)
    mod = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mod)
    bb = sqlite3.connect(miroir.DB_PATH)
    mod.appliquer(bb)
    mod.appliquer(bb)                 # rejouable
    bb.close()


b = sqlite3.connect(miroir.DB_PATH)
print("\nType de machine")
check("avant migration : ancienne règle de nom", mtype.sql_nom_repiquage(b, "machine").startswith("(lower(trim("), True)
b.execute("INSERT INTO machines(id, nom) VALUES (2, 'Repiquage')")
b.commit()
b.close()
for f in ("2026_11_24_machines_type.py", "2026_11_24_planning_repiquage.py", "2026_11_24_adv_repiquage.py"):
    _migrer(f)
b = sqlite3.connect(miroir.DB_PATH)
b.row_factory = sqlite3.Row
check("la migration type les postes de repiquage", [r["type"] for r in b.execute("SELECT type FROM machines ORDER BY id")],
      ["impression", "repiquage"])
check("le type décide, plus le nom", (mtype.est_repiquage_nom(b, "Repiquage"), mtype.est_repiquage_nom(b, "Machine 1")), (True, False))
b.execute("UPDATE machines SET nom='Atelier surimpression' WHERE id=2")
check("un poste renommé reste un poste de repiquage", mtype.est_repiquage_nom(b, "Atelier surimpression"), True)
check("fragment SQL sur les noms typés", mtype.sql_nom_repiquage(b, "machine"), "lower(trim(COALESCE(machine,''))) IN ('atelier surimpression')")
# D (9930002-2) : son dossier 11 est imprimé, coché « pour repiquage » ; un
# dossier de repiquage, sous une autre référence, le désigne comme origine.
b.execute("UPDATE planning_entries SET pour_repiquage=1, statut='termine' WHERE id=11")
b.execute("""INSERT INTO planning_entries(id, reference, numero_of, ref_produit, statut, machine_id, repiquage_source_id, planned_end)
             VALUES (20, 'REP-ATELIER', 'REP-ATELIER', '', 'en_cours', 2, 11, ?)""", (jour(6),))
b.commit()
b.close()
d = adv.construire()
D = {l["cle"]: l for l in d["lignes"]}["9930002-2"]
print("\nRepiquage dans Prod")
check("le repiquage relié rejoint la ligne", sorted(x["id"] for x in D["dossiers"]), [11, 20])
check("repiquage requis, en cours (planning)", (D["repiquage"]["requis"], D["repiquage"]["statut"], D["repiquage"]["manuel"]),
      (True, "en_cours", False))
check("Prod : impression faite, repiquage en cours", (D["etapes"]["prod"]["valeur"], D["etapes"]["prod"]["detail"]),
      ("en_cours", "Impression terminée · repiquage en cours"))
check("la fin de prod tient compte du repiquage", D["fin_prod"][:10], jour(6)[:10])
b = sqlite3.connect(miroir.DB_PATH)
b.execute("INSERT INTO adv_repiquages(numero, ligne, statut, maj_le, maj_par) VALUES ('9930002', 2, 'termine', ?, 'ADV')", (jour(0),))
b.commit()
b.close()
D = {l["cle"]: l for l in adv.construire()["lignes"]}["9930002-2"]
check("statut fixé par l'ADV : Prod faite", (D["etapes"]["prod"]["valeur"], D["repiquage"]["manuel"], D["repiquage"]["calcul"]),
      ("oui", True, "en_cours"))

# ── 4. Miroir absent ─────────────────────────────────────────────────────────
miroir.ERP_MIRROR_DB = os.path.join(dossier, "absent.db")
d = adv.construire()
print("\nMiroir absent")
check("présent = False, aucune ligne", (d["present"], d["lignes"]), (False, []))

# ── 5. Règles de mise en forme ───────────────────────────────────────────────
from app.services import adv_mise_en_forme as mef  # noqa: E402
print("\nMise en forme : validation")
ok_regles = mef.valider([
    {"colonne": "a_fabriquer", "operateur": "gt", "cible": "valeur", "valeur": "0", "ton": "warn"},
    {"colonne": "fin_prod", "operateur": "gt", "cible": "colonne", "valeur": "expedition", "ton": "danger"},
    {"colonne": "expedition", "operateur": "lt", "cible": "aujourdhui", "valeur": "", "ton": "danger"},
    {"colonne": "etape_bat", "operateur": "eq", "cible": "valeur", "valeur": "non", "ton": "danger"},
    {"colonne": "client", "operateur": "vide", "cible": "colonne", "valeur": "x", "ton": "neutre"},
])
check("règles valides acceptées et normalisées",
      [(r["cible"], r["valeur"]) for r in ok_regles],
      [("valeur", "0"), ("colonne", "expedition"), ("aujourdhui", "0"), ("valeur", "non"), ("valeur", "")])


def refusee(regle):
    try:
        mef.valider([regle])
    except mef.RegleInvalide:
        return True
    return False


check("colonne inconnue refusée", refusee({"colonne": "x; DROP", "operateur": "gt", "valeur": "0", "ton": "warn"}), True)
check("opérateur d'un autre type refusé", refusee({"colonne": "qte", "operateur": "contient", "valeur": "1", "ton": "warn"}), True)
check("nombre attendu", refusee({"colonne": "qte", "operateur": "gt", "valeur": "abc", "ton": "warn"}), True)
check("colonne de comparaison d'un autre type refusée",
      refusee({"colonne": "qte", "operateur": "gt", "cible": "colonne", "valeur": "expedition", "ton": "warn"}), True)
check("« aujourd'hui » réservé aux dates",
      refusee({"colonne": "qte", "operateur": "gt", "cible": "aujourdhui", "valeur": "1", "ton": "warn"}), True)
check("couleur hors thème refusée", refusee({"colonne": "qte", "operateur": "gt", "valeur": "1", "ton": "#ff0000"}), True)
try:
    mef.valider([dict(ok_regles[0]) for _ in range(mef.ADV_MEF_MAX_REGLES + 1)])
    trop = False
except mef.RegleInvalide:
    trop = True
check("plafond de règles", trop, True)

# ── 6. Stock « probable » : production finie, pas rentrée dans MyStock ───────
# La logistique ne met pas toujours en stock ce qui part directement. Prod
# faite + étiquettes de fin de production qui couvrent la ligne = préparable.
miroir.ERP_MIRROR_DB = os.path.join(dossier, "miroir.db")   # rebranché après le §4
m = sqlite3.connect(miroir.ERP_MIRROR_DB)
m.execute("INSERT INTO cde_entete(numero, rs, amjc) VALUES (9930004, 'CLIENT E', ?)", (jour(-3),))
m.executemany("""INSERT INTO cde_ligne(numero, ligne, lpos, qte, qtep, amje, amjl, orig, code1, code2, des1)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?)""", [
    (9930004, 1, 0, 1000, 1000, jour(2), jour(3), 1, "400", "0004", "Etiquette E"),
    (9930004, 2, 0, 10, 10, jour(2), jour(3), 1, "500", "0005", "Etiquette F en cartons"),
    (9930004, 3, 0, 500, 500, jour(3), jour(4), 1, "400", "0004", "Etiquette E, suite"),
])
m.commit()
m.close()
b = sqlite3.connect(miroir.DB_PATH)
for col in ("no_dossier TEXT", "quantite_traitee REAL", "operateur TEXT",
            "metrage_total_debut REAL", "metrage_total_fin REAL"):
    b.execute("ALTER TABLE production_data ADD COLUMN " + col)
b.execute("ALTER TABLE planning_entries ADD COLUMN etiquettes_par_carton INTEGER")
b.execute("INSERT INTO produits(id, reference, designation, unite) VALUES (5, '500/0005', 'Etiquette F', 'carton')")
b.executemany("""INSERT INTO planning_entries(id, reference, numero_of, ref_produit, statut,
                 planned_start, planned_end, machine_id) VALUES (?,?,?,?,?,?,?,1)""", [
    (40, "9930004 - L1", "9930004 - L1", "400/0004", "termine", jour(-2), jour(-2, "12:00:00")),
    (41, "9930004 - L2", "9930004 - L2", "500/0005", "termine", jour(-2), jour(-2, "12:00:00")),
])
for pe, dos in ((40, "9930004 - L1"), (41, "9930004 - L2")):
    b.executemany("""INSERT INTO production_data(planning_entry_id, no_dossier, operation_code, date_operation,
                     est_annule, operateur, quantite_traitee, metrage_total_debut, metrage_total_fin)
                     VALUES (?,?,?,?,0,'OP',?,?,?)""", [
        (pe, dos, "01", jour(-2)[:10] + "T08:00:00", None, 0, None),
        (pe, dos, "89", jour(-2)[:10] + "T12:00:00", 1200, None, 500),
    ])
b.commit()
b.close()
d = adv.construire()
par = {l["cle"]: l for l in d["lignes"]}
E1, F, E3 = par["9930004-1"], par["9930004-2"], par["9930004-3"]
print("\nStock probable")
check("E1 : prod faite, 1 200 produites pour 1 000 : stock probable",
      (E1["etapes"]["prod"]["valeur"], E1["etapes"]["stock"]["valeur"]), ("oui", "probable"))
check("E1 : sortie de prod et plus rien à fabriquer", (E1["stock"]["sortie_prod"], E1["a_fabriquer"]), (1000.0, 0.0))
check("E1 : le stock ne bloque plus, ni le BAT (prod faite)", E1["bloquante"], "prepa")
check("E1 : sans BAT dans MyBAT, la prod faite vaut BAT bon",
      (E1["etapes"]["bat"]["valeur"], "production lancée" in E1["etapes"]["bat"]["detail"]), ("oui", True))
check("E3 : le même dossier ne sert pas deux fois (200 restantes pour 500)",
      (E3["etapes"]["stock"]["valeur"], E3["a_fabriquer"]), ("non", 500.0))
check("F : cartons sans « étiquettes par carton », on ne devine pas", F["etapes"]["stock"]["valeur"], "non")
p = adv.prepa(horizon=10)
check("E1 se prépare", {l["cle"]: l["groupe"] for l in p["lignes"]}.get("9930004-1"), "preparable")
b = sqlite3.connect(miroir.DB_PATH)
b.execute("UPDATE planning_entries SET etiquettes_par_carton = 100 WHERE id = 41")
b.commit()
b.close()
F = {l["cle"]: l for l in adv.construire()["lignes"]}["9930004-2"]
check("F : 1 200 étiquettes à 100 par carton couvrent 10 cartons", F["etapes"]["stock"]["valeur"], "probable")
# Marge : 95 % du reste suffisent (la gâche d'un tirage ne bloque pas).
def _produit_e(q):
    b = sqlite3.connect(miroir.DB_PATH)
    b.execute("UPDATE production_data SET quantite_traitee=? WHERE planning_entry_id=40 AND operation_code='89'", (q,))
    b.commit()
    b.close()
    return {l["cle"]: l for l in adv.construire()["lignes"]}["9930004-1"]
E1 = _produit_e(960)
check("960 pour 1 000 (96 %) : probable, 960 en sortie de prod",
      (E1["etapes"]["stock"]["valeur"], E1["stock"]["sortie_prod"]), ("probable", 960.0))
check("le détail dit la couverture", "96 % du reste" in E1["etapes"]["stock"]["detail"], True)
E1 = _produit_e(900)
check("900 pour 1 000 (90 %) : pas assez", E1["etapes"]["stock"]["valeur"], "non")
_produit_e(1200)
b = sqlite3.connect(miroir.DB_PATH)
b.execute("""INSERT INTO adv_forcages(numero, ligne, etape, valeur, maj_le, maj_par)
             VALUES ('9930004', 1, 'stock', 'non', ?, 'ADV')""", (jour(0),))
b.commit()
b.close()
E1 = {l["cle"]: l for l in adv.construire()["lignes"]}["9930004-1"]
check("un forçage de l'ADV prime sur « probable »", (E1["etapes"]["stock"]["valeur"], E1["etapes"]["stock"]["force"]),
      ("non", True))

# ── 7. Préparations urgentes et bulles du portail ───────────────────────────
print("\nUrgences")
spec_u = importlib.util.spec_from_file_location("mig_urg", "app/core/migrations/2026_11_24_adv_urgences.py")
mig_u = importlib.util.module_from_spec(spec_u)
spec_u.loader.exec_module(mig_u)
b = sqlite3.connect(miroir.DB_PATH)
mig_u.appliquer(b)
mig_u.appliquer(b)                    # rejouable
b.execute("INSERT INTO adv_urgences(numero, ligne, maj_le, maj_par) VALUES ('9930003', 1, ?, 'ADV')", (jour(0),))
b.commit()
b.close()
p = adv.prepa(horizon=4)
par_p = {l["cle"]: l for l in p["lignes"]}
check("marquée par l'ADV : urgente, avec son auteur", par_p["9930003-1"]["urgence"], "Marquée urgente par ADV")
check("une ligne marquée (expédition à J+4) reste visible sur un horizon d'un jour",
      "9930003-1" in {l["cle"] for l in adv.prepa(horizon=1)["lignes"]}, True)
J = AUJ
check("calcul : préparable, expédition demain → urgente",
      bool(adv.urgence({"expedition": (J + timedelta(days=1)).isoformat()}, "preparable", J)), True)
check("calcul : préparable, expédition dans 3 jours → non",
      adv.urgence({"expedition": (J + timedelta(days=3)).isoformat()}, "preparable", J), None)
check("calcul : en retard mais en attente de prod → non (rien à préparer)",
      adv.urgence({"expedition": (J - timedelta(days=2)).isoformat()}, "attente", J), None)
check("une prépa prête n'est plus urgente",
      adv.urgence({"urgente_manuelle": True, "expedition": None}, "pretes", J), None)
bd = adv.badges()
d = adv.construire()
check("bulle logistique = urgences de la Prépa", bd["urgentes"],
      sum(1 for l in d["lignes"] if adv.urgence(l, adv.groupe_prepa(l), J)))
check("bulle administration = tuiles retard + 7 jours du carnet",
      (bd["retard"], bd["semaine"]), (d["compteurs"]["retard"]["lignes"], d["compteurs"]["semaine"]["lignes"]))

# ── 8. Historique des préparations déjà faites ──────────────────────────────
print("\nHistorique")
b = sqlite3.connect(miroir.DB_PATH)
b.execute("DELETE FROM adv_prepas")
b.executemany("INSERT INTO adv_prepas(numero, ligne, statut, maj_le, maj_par) VALUES (?, ?, ?, ?, 'LOG')", [
    ("9930003", 1, "prete", jour(0, "10:00:00")),      # dans le carnet, pas partie
    ("9930001", 1, "prete", jour(-1, "08:00:00")),     # son départ est parti
    ("9930003", 2, "prete", jour(-2, "09:00:00")),     # sortie du carnet (soldée)
    ("9930002", 2, "prete", jour(-40, "09:00:00")),    # hors des 30 jours
    ("9930002", 1, "en_cours", jour(0, "11:00:00")),   # pas encore faite
])
b.execute("UPDATE expe_departs SET parti_le = ? WHERE id = 100", (jour(-1, "16:00:00"),))
b.commit()
b.close()
hst = adv.historique_prepa(30)
check("les prêtes des 30 jours, la plus récente en tête", [l["cle"] for l in hst["lignes"]],
      ["9930003-1", "9930001-1", "9930003-2"])
par_h = {l["cle"]: l for l in hst["lignes"]}
check("encore au carnet : en attente de départ", par_h["9930003-1"]["situation"], "attente_depart")
check("départ parti : la ligne a quitté la Prépa, l'historique la garde",
      (par_h["9930001-1"]["situation"], par_h["9930001-1"]["situation_label"][:9]), ("parti", "Parti le "))
check("sortie du carnet : client et article relus dans le miroir",
      tuple(par_h["9930003-2"][k] for k in ("situation", "client", "article", "qte")),
      ("sortie", "CLIENT C", "200/0002", 10.0))
check("auteur et date de la prépa", (par_h["9930003-1"]["prete_par"], par_h["9930003-1"]["prete_le"][:10]),
      ("LOG", jour(0)[:10]))
check("sur 90 jours, la plus ancienne revient", len(adv.historique_prepa(90)["lignes"]), 4)
check("partie : absente de l'onglet Prépa", "9930001-1" in {l["cle"] for l in adv.prepa(horizon=30)["lignes"]}, False)

# ── 9. Planning de prépa : le jour où préparer ──────────────────────────────
print("\nJour de prépa")
from datetime import date as _d  # noqa: E402
check("jour ouvré avant un lundi = vendredi", adv.jour_ouvre_avant(_d(2026, 11, 30)).isoformat(), "2026-11-27")
check("jour ouvré avant un mercredi = mardi", adv.jour_ouvre_avant(_d(2026, 11, 25)).isoformat(), "2026-11-24")
LUNDI = _d(2026, 11, 23)
check("expédition jeudi → préparée mercredi",
      adv.jour_prepa({"expedition": "2026-11-26"}, LUNDI), ("2026-11-25", "expedition"))
check("un enlèvement prévu prime sur l'expédition",
      adv.jour_prepa({"expedition": "2026-11-27", "departs": [{"date_enlevement": "2026-11-25", "parti_le": None}]}, LUNDI),
      ("2026-11-24", "enlevement"))
check("un enlèvement déjà parti ne compte pas",
      adv.jour_prepa({"expedition": "2026-11-27", "departs": [{"date_enlevement": "2026-11-25", "parti_le": "2026-11-25"}]}, LUNDI),
      ("2026-11-26", "expedition"))
check("en retard → aujourd'hui", adv.jour_prepa({"expedition": "2026-11-20"}, LUNDI), ("2026-11-23", "expedition"))
check("expédition demain → aujourd'hui", adv.jour_prepa({"expedition": "2026-11-24"}, LUNDI), ("2026-11-23", "expedition"))
check("jour fixé par l'ADV", adv.jour_prepa({"expedition": "2026-11-27", "jour_manuel": "2026-11-24"}, LUNDI),
      ("2026-11-24", "manuel"))
check("jour fixé dépassé → aujourd'hui", adv.jour_prepa({"expedition": "2026-11-27", "jour_manuel": "2026-11-20"}, LUNDI),
      ("2026-11-23", "manuel"))
check("sans date", adv.jour_prepa({"expedition": None}, LUNDI), (None, "sans_date"))
spec_j = importlib.util.spec_from_file_location("mig_jours", "app/core/migrations/2026_11_24_adv_prepa_jours.py")
mig_j = importlib.util.module_from_spec(spec_j)
spec_j.loader.exec_module(mig_j)
b = sqlite3.connect(miroir.DB_PATH)
mig_j.appliquer(b)
mig_j.appliquer(b)                    # rejouable
b.execute("DELETE FROM adv_prepas")
b.execute("INSERT INTO adv_prepa_jours(numero, ligne, jour, maj_le, maj_par) VALUES ('9930003', 1, ?, ?, 'ADV')",
          ((AUJ + timedelta(days=3)).isoformat(), jour(0)))
b.commit()
b.close()
par_p = {l["cle"]: l for l in adv.prepa(horizon=30)["lignes"]}
check("le jour fixé par l'ADV remonte dans la Prépa",
      (par_p["9930003-1"]["jour_prepa"], par_p["9930003-1"]["jour_source"]), ((AUJ + timedelta(days=3)).isoformat(), "manuel"))
check("chaque ligne de la Prépa a un jour (ou None sans date)",
      all("jour_prepa" in l for l in par_p.values()), True)

# ── 10. Adresse de livraison : ce qui part ensemble ─────────────────────────
print("\nAdresse de livraison")
check("sans adresse dans le miroir : clé vide",
      [l["destination"]["cle"] for l in adv.construire()["lignes"]][:1], [""])
m = sqlite3.connect(miroir.ERP_MIRROR_DB)
for c in adv.ADRESSE_LIVRAISON:
    m.execute("ALTER TABLE cde_ligne ADD COLUMN %s TEXT" % c)
m.execute("UPDATE cde_ligne SET lrs='CLIENT B', ladr1='1 rue des Lilas', lcp='69007', lville='LYON', lpays='FR' WHERE numero=9930002")
m.execute("UPDATE cde_ligne SET lrs='client  b', ladr1='1 RUE DES LILAS', lcp='69007', lville='Lyon', lpays='FR' WHERE numero=9930002 AND ligne=2")
m.commit()
m.close()
par_d = {l["cle"]: l for l in adv.construire()["lignes"]}
dest = par_d["9930002-1"]["destination"]
check("adresse de la ligne lue dans cde_ligne", (dest["rs"], dest["adr1"], dest["cp"], dest["ville"], dest["pays"]),
      ("CLIENT B", "1 rue des Lilas", "69007", "LYON", "FR"))
check("même adresse à la casse et aux espaces près : même clé",
      par_d["9930002-1"]["destination"]["cle"] == par_d["9930002-2"]["destination"]["cle"] != "", True)
check("autre commande sans adresse : clé différente",
      par_d["9930001-1"]["destination"]["cle"] != dest["cle"], True)

print()
if ko:
    print(f"test_adv_commandes : {ko} échec(s)")
    sys.exit(1)
print("test_adv_commandes : OK")
