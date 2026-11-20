"""
Fiche rentabilité d'un dossier : collecte du réel, de bout en bout.

Le jeu de données reprend les VRAIES lignes du dossier 9932862 (Danone,
148 × 105 thermique, 600 000 ex, Cohésio 1, novembre 2026) : saisies MyProd,
mouvements MyStock avec leurs retours, prix MyStock, facture RVGI 26110036.
Seul le chiffrage du devis est inventé (le classeur n'est pas dans le dépôt) ;
il est cohérent avec le prix au mille facturé, 11,26 €.

Ce que le test garde :
- la valorisation MyStock d'un dossier (bobines × laize × mètres × €/m²,
  adhésif au kilo, mandrins et cartons à la palette, retours déduits) ;
- le prix de vente lu sur la facture RVGI, par numéro de commande et article ;
- le dossier « complet » quand il est produit, déstocké et facturé, et
  seulement si rien ne fait douter du résultat : sinon « à vérifier » ;
- la fenêtre « 7 derniers jours ouvrés » lue dans le calendrier du planning ;
- le croisement compteur / MyStock qui SIGNALE l'écart réel de ce dossier
  (29 395 m au compteur, 23 885 m déstockés après relecture) ;
- un créneau sans devis, ou sans montants lus, rend un état explicite.

Lancer : python3 tests/test_rentabilite_reel.py
"""

import contextlib
import io
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))
os.chdir(RACINE)

tmp = tempfile.mkdtemp(prefix="mysifa_rent_reel_")
db = os.path.join(tmp, "test.db")
erp = os.path.join(tmp, "erp.db")
os.environ["DB_PATH"] = db
os.environ["ERP_MIRROR_DB"] = erp
import config; config.DB_PATH = db; config.ERP_MIRROR_DB = erp   # noqa: E402,E702
import database                                          # noqa: E402,F401
import app.core.database as dbmod                        # noqa: E402
dbmod.DB_PATH = db
with contextlib.redirect_stdout(io.StringIO()):
    dbmod.init_db()

from database import get_db                              # noqa: E402
from app.services import devis_chiffrage, erp_mirror     # noqa: E402
erp_mirror.ERP_MIRROR_DB = erp
from app.services.rentabilite_reel import (              # noqa: E402
    consommations_mystock, fiche_rentabilite,
)

FAIL = []


def check(nom, cond, detail=""):
    if cond:
        print(f"  ok  {nom}")
    else:
        print(f"  KO  {nom} {detail}")
        FAIL.append(nom)


def proche(a, b, tol=0.01):
    return a is not None and b is not None and abs(a - b) <= tol * max(1.0, abs(b))


# ── Miroir RVGI : la facture du dossier ─────────────────────────────
e = sqlite3.connect(erp)
e.executescript("""
CREATE TABLE vte_entete (numero INTEGER, corbeille INTEGER, amjf TEXT);
CREATE TABLE vte_ligne (numero INTEGER, corbeille INTEGER, livno INTEGER, ligne INTEGER,
                        code1 TEXT, code2 TEXT, des1 TEXT, qte REAL, pun REAL, htn REAL, cuv TEXT);
INSERT INTO vte_entete VALUES (26110036, 0, '2026-11-10 09:00');
INSERT INTO vte_ligne VALUES (26110036, 0, 9932862, 1, '185', '0009',
                              'Etiquette 148 x 105.125 mm.', 600000, 11.26, 6756.0, '11');
-- Une facture à la corbeille ne compte pas.
INSERT INTO vte_entete VALUES (26119999, 1, '2026-11-11 09:00');
INSERT INTO vte_ligne VALUES (26119999, 0, 9932862, 1, '185', '0009', 'x', 1000, 1, 999.0, '11');
""")
e.commit()
e.close()

# ── Base MySifa ──────────────────────────────────────────────────────
SAISIES = [  # id, date, code, libellé, catégorie, qté traitée, compteur début, compteur fin, fin
    (6471, "2026-11-09T09:57:02", "01", "01 - Démarrer un dossier", "personnel", 0, 7461749, None, None),
    (6472, "2026-11-09T10:28:45", "02", "02 - Calage", "calage", 0, None, None, None),
    (6473, "2026-11-09T10:28:56", "67", "67 - Vidange four colle", "nettoyage", 0, None, None, None),
    (6474, "2026-11-09T11:14:21", "03", "03 - Production", "production", 0, None, None, None),
    (6475, "2026-11-09T11:53:43", "62", "62 - Remplissage colle Errépi", "arret", 0, None, None, None),
    (6476, "2026-11-09T12:05:28", "88", "88 - Reprise production", "production", 0, None, None, None),
    (6477, "2026-11-09T12:52:23", "89", "89 - Fin de production", "personnel", 240000, None, 7473396, 0),
    (6480, "2026-11-09T12:55:07", "01", "01 - Démarrer un dossier", "personnel", 0, 7473396, None, None),
    (6481, "2026-11-09T12:56:27", "95", "95 - Problème fondoir", "arret", 0, None, None, None),
    (6488, "2026-11-09T13:39:03", "88", "88 - Reprise production", "production", 0, None, None, None),
    (6491, "2026-11-09T16:54:00", "89", "89 - Fin de production", "personnel", 360000, None, 7491144, 1),
]
MATIERES = [  # id, catégorie, référence, ml/bobine, €/m², unités/palette, prix unitaire
    (31, "frontal", "70gsm TOP Thermal", 12000, 0.140286, None, 0),
    (53, "glassine", "60gsm glassine jaune", 18100, 0.114286, None, 0),
    (24, "adhesif", "2028Y", None, None, 1200, 2.554362),
    (4, "mandrin", "Ø 76 mm", None, None, 338, 1.1495),
    (20, "carton", "385 x 385 x 311 mm", None, None, 260, 0.99),
    (39, "palette", "Europe", None, None, None, 8.5),
]
MOUVEMENTS = [  # matière, laize, type, quantité
    (31, 3, "sortie", 2.449583), (53, 3, "sortie", 1.624033), (24, None, "sortie", 276.313),
    (4, None, "sortie", 0.066203), (20, None, "sortie", 0.384615), (39, None, "sortie", 4.0),
    (31, 3, "entree", 0.459166), (53, 3, "entree", 0.30442), (4, None, "entree", 0.016236),
    (20, None, "entree", 0.096153), (39, None, "entree", 1.0),
]

with get_db() as conn:
    conn.execute("INSERT OR IGNORE INTO machines (id, nom, code, actif) VALUES (1, 'Cohésio 1', 'C1', 1)")
    conn.execute(
        """INSERT INTO planning_entries (id, machine_id, position, reference, client, format_l, format_h,
               statut, numero_of, ref_produit, laize, destockage)
           VALUES (707, 1, 1, '9932862', 'DANONE', 148, 105.125, 'termine', '9932862', '185/0009', 470, 'done')""")
    for (i, d, code, lib, cat, qte, deb, fin, fin_dos) in SAISIES:
        # Deux équipes, comme dans la réalité : `dossier_stats` range les
        # quantités par conducteur et par jour.
        operateur = "Tony Cathelineau" if i < 6480 else "907 - DENIS Alan"
        data = {"operateur": operateur, "date_operation": d, "operation": lib,
                "no_dossier": "9932862", "machine": "Cohésio 1"}
        conn.execute(
            """INSERT INTO production_data (id, operateur, date_operation, operation, operation_code,
                   operation_severity, operation_category, machine, no_dossier, quantite_traitee,
                   metrage_total_debut, metrage_total_fin, metrage_reel, metrage_prevu, fin_dossier,
                   est_annule, planning_entry_id, data)
               VALUES (?,?,?,?,?,'info',?,'Cohésio 1','9932862',?,?,?,?,?,?,0,707,?)""",
            (i, operateur, d, lib, code, cat, qte, deb, fin, fin, deb, fin_dos, json.dumps(data)))
    conn.execute("INSERT OR IGNORE INTO mp_laizes (id, valeur_mm, label, ordre, actif, created_at) "
                 "VALUES (3, 470, '470 mm', 3, 1, '2026-01-01')")
    for (mid, cat, ref, ml, prix_m2, upp, pu) in MATIERES:
        conn.execute(
            """INSERT INTO matieres_premieres (id, categorie, reference, designation,
                   metres_lineaires_par_bobine, prix_eur_m2, unites_par_palette, actif)
               VALUES (?,?,?,?,?,?,?,1)""", (mid, cat, ref, ref, ml, prix_m2, upp))
        conn.execute(
            """INSERT INTO mp_valorisation (matiere_id, prix_unitaire, updated_at, prix_en_usd,
                   taxe_importation, cout_transport_inclus) VALUES (?,?, '2026-11-01', 0, 0, 0)""",
            (mid, pu))
    for (mid, lid, typ, q) in MOUVEMENTS:
        conn.execute(
            """INSERT INTO mp_mouvements (matiere_id, laize_id, type_mouvement, quantite,
                   no_dossier, planning_entry_id, created_at) VALUES (?,?,?,?,'9932862',707,'2026-11-09')""",
            (mid, lid, typ, q))
    # Un mouvement d'un autre dossier ne doit pas entrer dans le compte.
    conn.execute("INSERT INTO mp_mouvements (matiere_id, laize_id, type_mouvement, quantite, no_dossier, "
                 "created_at) VALUES (31, 3, 'sortie', 5, '9932999', '2026-11-09')")
    conn.execute(
        """INSERT INTO devis (id, filename, client, laize, qte_etiquettes, temps_calage_mn,
               temps_calage_impression_mn, temps_production_mn, metrage_production_ml,
               vitesse_theorique, imported_at)
           VALUES (10, '148 x 105 test.xlsx', 'Danone', 470, 600000, 150, 0, 317.5, 22225, 70, '2026-11-06')""")
    conn.execute("INSERT INTO rent_links (planning_entry_id, devis_id, updated_at) VALUES (707, 10, '2026-11-10')")
    # Chiffrage de test, cohérent avec 11,26 € le mille.
    valeurs = {c: None for c in devis_chiffrage.CHAMPS_CHIFFRAGE}
    valeurs.update(prix_m2_corrige=0.30, cout_matiere=23861 * 0.47 * 0.30, cout_encre=0, cout_cliche=0,
                   cout_outil=25.0, cout_emballage=120.0, cout_transport=180.0, cout_production=2805.0,
                   prix_revient=6364.0, remise=0, surmarge=392.0, surmarge_taux=0.0616,
                   prix_vente=6756.0, taux_horaire=360.0, temps_total_mn=467.5, metrage_total_ml=23861.0)
    valeurs["marge_brute"] = 6756.0 - (valeurs["cout_matiere"] + 25 + 120 + 180)
    devis_chiffrage.enregistrer(conn, 10, {"valeurs": valeurs, "sources": {}, "erreurs": []})
    # Un créneau sans devis.
    conn.execute("INSERT INTO planning_entries (id, machine_id, position, reference, statut) "
                 "VALUES (708, 1, 2, '9932999', 'termine')")
    conn.commit()

print("1. Valorisation MyStock du dossier")
with get_db() as conn:
    conso = {c["matiere_id"]: c for c in consommations_mystock(conn, 707, ["9932862"])}
check("frontal : 1,99 bobine nette (retour déduit)", proche(conso[31]["quantite"], 1.990417, 1e-5), conso[31])
check("frontal : 11 226 m² et 1 575 €", proche(conso[31]["surface_m2"], 11226.0, 0.001) and proche(conso[31]["valeur"], 1574.8, 0.001), conso[31])
check("glassine : même surface que le frontal", proche(conso[53]["surface_m2"], conso[31]["surface_m2"], 0.001))
check("adhésif au kilo : 705,8 €", proche(conso[24]["valeur"], 705.8, 0.001), conso[24])
check("mandrins à la palette : 19,4 €", proche(conso[4]["valeur"], 19.41, 0.002), conso[4])
check("cartons à la palette : 74,2 €", proche(conso[20]["valeur"], 74.25, 0.002), conso[20])
check("palettes à l'unité : 3 × 8,5 €", proche(conso[39]["valeur"], 25.5, 1e-6), conso[39])
check("autre dossier exclu", conso[31]["quantite"] < 2.5)

print("2. Fiche du dossier 9932862")
with get_db() as conn:
    f = fiche_rentabilite(conn, 707)
check("compteur et MyStock qui divergent : à vérifier, pas complet",
      f["etat"] == "a_verifier" and not f["manque"] and not f["hors_norme"]
      and any("Compteur et MyStock" in r for r in f["raisons"]), (f["etat"], f.get("raisons")))
from app.services import rentabilite_parametres          # noqa: E402
with get_db() as conn:
    # Tolérance élargie : le même dossier, sans doute, redevient complet.
    rentabilite_parametres.ecrire(conn, "ecart_croisement_pct", 25, "test")
    conn.commit()
    f = fiche_rentabilite(conn, 707)
check("dossier complet : produit, déstocké, facturé, sans doute", f["etat"] == "complet" and not f["manque"]
      and not f["raisons"], (f["etat"], f.get("manque"), f.get("raisons")))
check("racine de commande", f["racine"] == "9932862")
pv = next(p for p in f["parametres"] if p["parametre"] == "Prix de vente")
check("PV = facture RVGI 6 756 € (corbeille exclue)", pv["reel"] == 6756 and pv["source"].startswith("facture RVGI"), pv)
laize = next(p for p in f["parametres"] if p["parametre"] == "Laize")
check("laize réelle 470 mm lue sur les bobines", laize["reel"] == 470 and not laize["modifie"], laize)
met = next(p for p in f["parametres"] if p["parametre"] == "Métrage")
check("métrage compteur 29 395 m", met["reel"] == 29395, met)
check("écart compteur / MyStock dans la fourchette retenue", f["parametres"] and any(
      p["parametre"] == "Surface consommée" and "compteur et MyStock" in p["source"] for p in f["parametres"]), f["parametres"])
emb = next(p for p in f["parametres"] if p["parametre"] == "Emballage")
check("emballage mesuré dans MyStock : 119 €", emb["reel"] == 119 and emb["source"] == "sorties MyStock", emb)
tr = next(p for p in f["parametres"] if p["parametre"] == "Transport")
check("transport sans prix retenu : repris du devis", "non mesuré" in tr["source"], tr)
r = f["reel"]
check("MB en fourchette, bas ≤ probable ≤ haut",
      r["marge_brute"]["bas"] <= r["marge_brute"]["probable"] <= r["marge_brute"]["haut"], r["marge_brute"])
check("coût horaire calculé", r["cout_horaire"] and r["cout_horaire"]["probable"] > 0, r)
check("verdict rendu", f["verdict"]["global"] in ("reussi", "limite", "sous_seuil"), f["verdict"])
cm = f["cascade_marge"]
somme = sum(x["valeur"] for x in cm if x["nature"] != "total")
check("cascade marge : retombe sur la MB réelle", proche(cm[0]["valeur"] + somme, cm[-1]["valeur"], 0.001)
      and proche(cm[-1]["valeur"], r["marge_brute"]["probable"], 0.001), cm)
ce = f["cascade_cout_horaire"]
somme = sum(x["valeur"] for x in ce if x["nature"] != "total")
check("cascade €/h : retombe sur le coût horaire réel", proche(ce[0]["valeur"] + somme, ce[-1]["valeur"], 0.002), ce)
check("pas de re-devisé quand la laize n'a pas changé", f["redevise"] is None)
qte = next(p for p in f["parametres"] if p["parametre"] == "Quantité")
check("quantité produite 600 000 (deux équipes)", qte["reel"] == 600000, qte)
print("     MB", r["marge_brute"], "MB %", r["mb_pct"], "€/h", r["cout_horaire"], "verdict", f["verdict"]["global"])

print("3. États explicites")
with get_db() as conn:
    check("créneau sans devis", fiche_rentabilite(conn, 708)["etat"] == "sans_devis")
    conn.execute("DELETE FROM devis_chiffrage WHERE devis_id=10")
    conn.commit()
    check("devis sans montants lus", fiche_rentabilite(conn, 707)["etat"] == "sans_chiffrage")
    try:
        fiche_rentabilite(conn, 99999)
        check("créneau inconnu : LookupError", False)
    except LookupError:
        check("créneau inconnu : LookupError", True)

print("4. Non facturé : provisoire, PV estimé")
with get_db() as conn:
    devis_chiffrage.enregistrer(conn, 10, {"valeurs": valeurs, "sources": {}, "erreurs": []})
    conn.commit()
e = sqlite3.connect(erp)
e.execute("DELETE FROM vte_ligne")
e.commit()
e.close()
with get_db() as conn:
    f = fiche_rentabilite(conn, 707)
check("provisoire, il manque la facture", f["etat"] == "provisoire" and f["manque"] == ["facture"], f.get("manque"))
pv = next(p for p in f["parametres"] if p["parametre"] == "Prix de vente")
check("PV estimé depuis le devis", pv["source"].startswith("estimé") and pv["reel"] == 6756, pv)

print("5. Tableau de bord")
from datetime import date                                # noqa: E402
from app.services.rentabilite_reel import bornes_periode, tableau_de_bord  # noqa: E402
check("période 30 jours", bornes_periode("last30", date(2026, 11, 20)) == ("2026-10-22", "2026-11-20"))
check("période année", bornes_periode("thisYear", date(2026, 11, 20)) == ("2026-01-01", "2026-11-20"))
check("période tout", bornes_periode("all") == (None, None))
from app.services.rentabilite_reel import debut_jours_ouvres  # noqa: E402
with get_db() as conn:
    # Vendredi 20/11/2026 : 7 jours ouvrés = du jeudi 12 au vendredi 20.
    check("7 jours ouvrés : week-end sauté", debut_jours_ouvres(conn, 7, date(2026, 11, 20)) == date(2026, 11, 12))
    conn.execute("INSERT INTO planning_holidays (machine_id, date, is_off) SELECT id, '2026-11-16', 1 FROM machines")
    conn.commit()
    # 16/11 off pour toutes les machines, 11/11 férié au calendrier : on remonte au 10.
    check("7 jours ouvrés : jours off de toutes les machines sautés",
          debut_jours_ouvres(conn, 7, date(2026, 11, 20)) == date(2026, 11, 10))
    check("période 7 jours ouvrés par défaut", bornes_periode("ouvres7", date(2026, 11, 20), conn) == ("2026-11-10", "2026-11-20"))
    conn.execute("DELETE FROM planning_holidays WHERE date='2026-11-16'")
    conn.commit()
with get_db() as conn:
    t = tableau_de_bord(conn, "all")
check("dossier non facturé : en attente, hors compteurs",
      t["comptes"]["attente"] == 1 and t["comptes"]["complets"] == 0 and len(t["dossiers"]) == 1, t["comptes"])
e = sqlite3.connect(erp)
e.execute("INSERT INTO vte_ligne VALUES (26110036, 0, 9932862, 1, '185', '0009', 'x', 600000, 11.26, 6756.0, '11')")
e.commit()
e.close()
with get_db() as conn:
    conn.execute("UPDATE planning_entries SET planned_end='2026-11-09T16:54:00' WHERE id=707")
    conn.commit()
    t_cache = tableau_de_bord(conn, "all")
    t = tableau_de_bord(conn, "all", force=True)
    t_machine = tableau_de_bord(conn, "all", "Autre machine")
    t_hors = tableau_de_bord(conn, "last30")  # la date du dossier dépend du jour du test
check("cache : sans « Recalculer », la fiche gardée sert encore", t_cache["comptes"]["attente"] == 1, t_cache["comptes"])
check("dossier facturé : complet et compté", t["comptes"]["complets"] == 1
      and sum(t["comptes"][k] for k in ("reussi", "limite", "sous_seuil")) == 1, t["comptes"])
check("créneau sans devis absent de la liste", all(d["planning_entry_id"] != 708 for d in t["dossiers"]))
check("dossier daté et pondérable", t["dossiers"][0]["date"] == "2026-11-09"
      and t["dossiers"][0]["heures"] > 0 and t["dossiers"][0]["marge_brute"] is not None, t["dossiers"][0])
check("filtre machine", t_machine["dossiers"] == [] and t["machines"] == ["Cohésio 1"])
check("causes en points de marge", t["causes_marge"] and all("valeur" in c for c in t["causes_marge"]), t["causes_marge"])
check("écart MB calculé", t["ecart_mb_pts"] is not None and t["cout_horaire_median"] is not None)
with get_db() as conn:
    conn.execute("UPDATE machines SET rent_suivi_devis=0 WHERE id=1")
    conn.commit()
    check("machine retirée du suivi : exclue", tableau_de_bord(conn, "all", force=True)["dossiers"] == [])

print("6. Commandes groupées, devis partagé, résultat hors norme")
from app.services.rentabilite_reel import devis_ramene, racines_commande  # noqa: E402
check("commandes abrégées", racines_commande({"numero_of": "9932574-75-77-78", "reference": ""}, [])
      == ["9932574", "9932575", "9932577", "9932578"])
check("commandes à la barre", racines_commande({"numero_of": "9932729/730/731", "reference": ""}, [])
      == ["9932729", "9932730", "9932731"])
check("date et référence article ignorées", racines_commande({"numero_of": "01/10/2026 - Cdes Ref 961/0008", "reference": ""}, []) == [])
vr = devis_ramene({"prix_vente": 20000.0, "cout_matiere": 10000.0, "metrage_total_ml": 100000.0,
                   "temps_total_mn": 1000.0, "marge_brute": 9000.0}, 0.2, 100)
check("devis ramené au cinquième", vr["prix_vente"] == 4000 and vr["metrage_total_ml"] == 20000, vr)
check("calage non divisé", abs(vr["temps_total_mn"] - (100 + 900 * 0.2)) < 1e-9, vr)
e = sqlite3.connect(erp)
e.execute("UPDATE vte_ligne SET htn = 600")    # facture d'une autre commande : 600 € au lieu de 6 756 €
e.commit()
e.close()
with get_db() as conn:
    conn.execute("UPDATE machines SET rent_suivi_devis=1 WHERE id=1")
    conn.commit()
    f = fiche_rentabilite(conn, 707)
    t = tableau_de_bord(conn, "all", force=True)
check("résultat hors norme : à vérifier", f["etat"] == "a_verifier" and f["hors_norme"], (f["etat"], f.get("hors_norme")))
check("hors norme : hors des compteurs", t["comptes"]["complets"] == 0 and t["comptes"]["a_verifier"] == 1, t["comptes"])

import shutil                                            # noqa: E402
shutil.rmtree(tmp, ignore_errors=True)
print()
if FAIL:
    print(f"{len(FAIL)} échec(s) : {FAIL}")
    sys.exit(1)
print("Tous les tests passent.")
