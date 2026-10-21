# -*- coding: utf-8 -*-
"""MyStock › Monitoring : production → stock et expédition, rapprochés par source."""
import os, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database  # noqa: F401  — d'abord, toujours (CLAUDE.md)
from app.services.monitoring_flux_pf import flux_production, flux_expedition

erreurs = []
def ok(cond, quoi):
    print(("  OK   " if cond else "  ECHEC") + " " + quoi)
    if not cond: erreurs.append(quoi)

conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.executescript("""
CREATE TABLE machines(id INTEGER PRIMARY KEY, nom TEXT);
CREATE TABLE of_imports(id INTEGER PRIMARY KEY, qte_etiquettes REAL);
CREATE TABLE planning_entries(id INTEGER PRIMARY KEY, reference TEXT, numero_of TEXT,
  ref_produit TEXT, ref_produit_norm TEXT, client TEXT, statut TEXT, date_livraison TEXT,
  machine_id INT, of_import_id INT, planned_end TEXT, planned_end_manual TEXT, planned_start TEXT);
CREATE TABLE production_data(id INTEGER PRIMARY KEY, no_dossier TEXT, date_operation TEXT,
  operation_code TEXT, machine TEXT, quantite_traitee REAL, fin_dossier INT, est_annule INT,
  operateur TEXT);
CREATE TABLE produits(id INTEGER PRIMARY KEY, reference TEXT, designation TEXT, unite TEXT);
CREATE TABLE mouvements_stock(id INTEGER PRIMARY KEY, produit_id INT, emplacement TEXT,
  type_mouvement TEXT, quantite REAL, note TEXT, created_at TEXT, created_by_name TEXT,
  no_dossier TEXT);
CREATE TABLE lots_stock(id INTEGER PRIMARY KEY, produit_id INT, emplacement TEXT,
  quantite_restante REAL, no_dossier TEXT);
CREATE TABLE stock_emplacements(produit_id INT, emplacement TEXT, quantite REAL);
CREATE TABLE expe_departs(id INTEGER PRIMARY KEY, date_enlevement TEXT, statut TEXT,
  client TEXT, no_bl TEXT, transporteur TEXT, date_livraison TEXT, no_dossier TEXT,
  planning_entry_id INT);

INSERT INTO machines VALUES (1,'Machine A');
INSERT INTO of_imports VALUES (1, 2000000);
INSERT INTO produits VALUES (1,'890/0007','Etiq 1','étiquette'),(2,'601/0161','Etiq 2','étiquette'),
                            (3,'470/0020','Etiq 3','étiquette'),(4,'24/0012','Etiq 4','étiquette'),
                            (5,'931/0005','Etiq 5','étiquette'),
                            (6,'1120/0003','Etiq 6','étiquette'),
                            (7,'890/0115','Etiq 7','étiquette'),
                            (8,'1013/0068','Etiq 8','carton');
INSERT INTO planning_entries VALUES
  (10,'9932689','9932689','890/0007 - X','890/0007','CLIENT A','termine','2026-10-14',1,1,'2026-10-15T10:00:00',NULL,NULL),
  (11,'9932700','9932700','470/0020 - X','470/0020','CLIENT B','termine','2026-10-30',1,NULL,NULL,NULL,NULL),
  (12,'9932585','9932585','24/0012 - X','24/0012','CLIENT C','termine','2026-10-14',1,NULL,NULL,NULL,NULL),
  (13,'9932800','9932800','601/0161 - X','601/0161','CLIENT D','attente','2026-10-16',1,NULL,'2026-10-21T08:00:00',NULL,NULL),
  (14,'9932648 + Stock','9932648 + Stock','1120/0003 - X','1120/0003','CLIENT E','termine','2026-10-07',1,NULL,'2026-10-09T10:22:45',NULL,NULL),
  (15,'9932573','9932573','890/0115 - X','890/0115','XEROX','termine','2026-10-10',1,NULL,'2026-10-14T17:00:00',NULL,NULL);
-- 9932689 : deux fins de prod, la dernière porte le cumul ; entré en deux fois.
INSERT INTO production_data VALUES
  (1,'9932689','2026-10-14T12:00:00','89','Machine A',1000000,0,0,NULL),
  (2,'9932689','2026-10-15T10:00:00','89','Machine A',2000000,1,0,NULL),
  (3,'9932700','2026-10-15T10:00:00','89','Machine A',500000,1,0,NULL),
  (4,'9932700','2026-10-15T11:00:00','89','Machine A',900000,1,1,NULL),
  (5,'9932800','2026-10-15T06:00:00','01','Machine A',0,NULL,0,NULL),
  (6,'9932648 + Stock','2026-10-09T10:22:45','89','Machine A',363000,1,0,NULL),
  (7,'9932573','2026-10-14T17:00:00','89','Machine A',1500000,1,0,NULL);
INSERT INTO mouvements_stock VALUES
  (1,1,'Z1','entree',1000000,'Production dossier 9932689','2026-10-15T07:00:00','A','9932689'),
  (2,1,'Z1','entree',1000000,'Production dossier 9932689','2026-10-15T11:00:00','A','9932689'),
  (3,1,'Z1','sortie',1000000,'Déplacement vers A111','2026-10-16T08:00:00','A','9932689'),
  (4,1,'A111','entree',1000000,'Déplacement depuis Z1','2026-10-16T08:00:00','A','9932689'),
  (5,2,'C211','entree',92400,'','2026-10-15T09:00:00','B',NULL),
  -- 470/0020 : saisi, jamais entré.
  -- expédition : 24/0012 sorti 300 000 pour 304 000 au BL (écart 1,3 %).
  (6,4,'A131','sortie',300000,'Expédition | BL OK','2026-10-19T10:00:00','C',NULL),
  (7,4,'A131','sortie',5,'Annulation de l''entree #2','2026-10-19T10:00:00','C',NULL),
  (11,8,'Z1','sortie',968,'Sortie lot FIFO','2026-10-21T09:00:00','E',NULL),
  (12,8,'Z1','entree',842400,'Production dossier 9932543','2026-10-14T16:51:00','E','9932543'),
  (13,8,'Z1','sortie',842352,'jai note en etiquette et cest en carton','2026-10-14T17:38:00','E',NULL),
  (8,5,'B302','entree',363000,'','2026-10-19T13:00:00','D',NULL),
  (9,6,'B302','entree',363000,'','2026-10-19T13:16:00','D',NULL),
  (10,7,'B200','entree',1500000,'','2026-10-23T08:00:00','D',NULL);
INSERT INTO lots_stock VALUES (1,1,'A111',1000000,'9932689'),(2,1,'Z1',1000000,'9932689');
INSERT INTO stock_emplacements VALUES (4,'A131',10000);
INSERT INTO expe_departs VALUES (1,'2026-10-19','valide','CLIENT C','9939121','T',NULL,NULL,12),
                                (2,'2026-10-17','en_attente','CLIENT D',NULL,'T',NULL,NULL,13);
""")

print("— production → stock")
r = flux_production(conn, "2026-10-14", "2026-10-20")
L = {l["cle"]: l for l in r["lignes"]}
d = L.get("d:9932689") or {}
ok(d.get("statut") == "ok", "9932689 : entrée 2 M entre le plus grand relevé (2 M) et la somme (3 M) → OK")
ok(d.get("qte_entree") == 2000000, "les déplacements ne comptent pas comme entrée")
ok(d.get("nb_deplacements") == 1 and d.get("derniere_destination") == "A111", "déplacement vers A111 suivi")
ok(d.get("stock_restant") == 2000000, "stock restant du dossier = lots")
ok(len((d.get("detail") or {}).get("fins", [])) == 2 and len(d["detail"]["deplacements"]) == 1,
   "détail : fins de production et déplacements du dossier")
ok(d.get("debut_prod") == "2026-10-14T12:00:00" and d.get("derniere_saisie") == "2026-10-15T10:00:00", "dates de production du dossier")
ok(d.get("qte_of") == 2000000 and d.get("machine") == "Machine A", "OF et machine du planning")
ok(d.get("fin_prevue") == "2026-10-15T10:00:00", "fin prévue du planning transmise")
n = L.get("d:9932700") or {}
ok(n.get("statut") == "non_entre", "9932700 clôturé sans entrée → Non entré")
ok(n.get("qte_produite") == 500000, "une saisie annulée n'est pas comptée")
h = L.get("d:9932800") or {}
ok(h.get("qte_entree") == 92400 and "reference" in h.get("rattachement", []),
   "entrée sans dossier rapprochée du seul dossier de même référence")
ok(h.get("statut") == "sans_saisie", "entrée sans saisie de production signalée")
t = L.get("d:9932648 + Stock") or {}
ok(t.get("statut") == "ok" and "reference" in t.get("rattachement", []),
   "entrée tardive (prod le 09, stock le 19) rattachée au dossier produit avant la période")
x5 = L.get("d:9932573") or {}
ok(x5.get("statut") == "ok" and x5.get("qte_entree") == 1500000,
   "saisi dans la période, entré APRÈS la période sans n° de dossier → entrée retrouvée")
hd = L.get("r:931/0005") or {}
ok(not hd and r.get("ajustements_ignores") == 1,
   "entrée sans aucun dossier (ajustement) : pas de ligne, comptée à part")

ok(not (L.get("d:9932543") or {}).get("qte_entree"),
   "entrée annulée le jour même par une sortie de même quantité : pas comptée en production")

print("— expédition")
erp = sqlite3.connect(":memory:")
erp.row_factory = sqlite3.Row
erp.executescript("""
CREATE TABLE liv_entete(numero INT, amje TEXT, lrs TEXT, corbeille INT);
CREATE TABLE liv_ligne(numero INT, numcde INT, lignecde INT, qte REAL, corbeille INT);
CREATE TABLE cde_ligne(numero INT, ligne INT, code1 TEXT, code2 TEXT, corbeille INT);
CREATE TABLE cdf_ligne(numero INT, ligne INT, code1 TEXT, code2 TEXT, type INT, corbeille INT);
INSERT INTO cdf_ligne VALUES (1,1,'1004','0219',1,0),(2,1,'24','0012',3,0);
INSERT INTO liv_entete VALUES (9939053,'2026-10-17 00:00:00','LC2',0);
INSERT INTO liv_ligne VALUES (9939053,9932999,1,350000,0);
INSERT INTO cde_ligne VALUES (9932999,1,'1004','0219',0);
INSERT INTO liv_entete VALUES (9939054,'2026-10-15 00:00:00','PROSOL',0);
INSERT INTO liv_ligne VALUES (9939054,9932543,1,968,0);
INSERT INTO cde_ligne VALUES (9932543,1,'1013','0068',0);
INSERT INTO liv_entete VALUES (9939121,'2026-10-19 00:00:00','CLIENT C',0);
INSERT INTO liv_ligne VALUES (9939121,9932585,1,304000,0),(9939121,9932585,2,1,0);
INSERT INTO cde_ligne VALUES (9932585,1,'24','0012',0),(9932585,2,'FR','FRAIS_DE_PORT',0);
""")
e = flux_expedition(conn, erp, "2026-10-14", "2026-10-20")
E = {l["reference"]: l for l in e["lignes"]}
x = E.get("24/0012") or {}
ok(x.get("statut") == "ok" and x.get("qte_bl") == 304000 and x.get("qte_sortie") == 300000,
   "24/0012 : BL 304 000, sortie 300 000 → OK à 2 % (annulation exclue)")
ok([dd["no_dossier"] for dd in x.get("dossiers", [])] == ["9932585"], "dossier retrouvé par la commande du BL")
ok([dp["id"] for dp in x.get("departs", [])] == [1], "départ retrouvé par son numéro de BL")
ok("FR/FRAIS_DE_PORT" not in E and "FR" not in E, "les frais de port ne sont pas un article")
ok("1004/0219" not in E and e.get("sous_traitance_ignorees") == 1,
   "sous-traitance (achetée en article, cdf_ligne.type = 1) écartée, comptée à part")
ok("24/0012" in E, "une matière de même code (type 3) n'écarte pas l'article")
y = E.get("601/0161") or {}
ok(y.get("statut") == "depart_prevu", "dossier à livrer avec départ en attente → Départ prévu")
w = E.get("1013/0068") or {}
ok(w.get("statut") == "ok" and w.get("qte_sortie") == 968,
   "BL du 15, sortie du 21 (hors période) : rapprochée du BL à 7 jours près")
ok([b["bl"] for b in (w.get("detail") or {}).get("bls", [])] == ["9939054"]
   and (w["detail"]["sorties"][0] or {}).get("bl_jour") == "2026-10-15",
   "détail : lignes de BL et sorties avec le BL rapproché")
ok(w.get("date_expedition") == "2026-10-15" and w.get("date_expedition_source") == "bl", "date d'expédition = date du BL")
ok(w.get("nb_sorties") == 1, "la sortie qui corrige une entrée du jour n'est pas une expédition")
ok("890/0007" not in E, "la date de livraison du planning ne fait pas entrer de ligne")
sans = flux_expedition(conn, None, "2026-10-14", "2026-10-20")
ok(sans["miroir"] is False and {l["reference"]: l for l in sans["lignes"]}["24/0012"]["statut"] == "sortie",
   "miroir absent : le côté MySifa reste affiché")

print()
print("ECHEC" if erreurs else "Tout est vert.")
sys.exit(1 if erreurs else 0)
