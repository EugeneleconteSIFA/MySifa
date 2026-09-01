"""
Compte-rendu de dossier : ce que le calcul doit dire, et ce qu'il ne doit pas dire.

Les cas verrouilles ici sont ceux ou une erreur passerait inapercue en
production parce qu'elle produirait un chiffre plausible :

- deux conducteurs sur le meme dossier ne se chainent pas l'un a l'autre ;
- un compteur machine releve une seule fois n'est pas un metrage ;
- une saisie restee ouverte d'un jour a l'autre est comptee mais signalee ;
- le repere d'une reference exclut le dossier qu'on est en train de juger ;
- un dossier sans donnee ne rend pas une carte vide, il rend `existe: False`.

Le service ne touche a aucun module de l'application : il prend une connexion
sqlite et rien d'autre. Le test s'execute donc sur une base en memoire, sans
charger `database` ni FastAPI.

Lancer : python3 tests/test_rapport_dossier.py
"""

import importlib.util
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def _charger(nom: str, chemin: Path):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


svc = _charger("rapport_dossier", RACINE / "app" / "services" / "rapport_dossier.py")

FAIL = []
T0 = datetime(2026, 6, 8, 8, 0, 0)          # lundi 8 juin 2026, 08:00
SEMAINE_DEBUT = "2026-06-08T00:00:00"
SEMAINE_FIN = "2026-06-14T23:59:59"


def verifier(cas: str, obtenu, attendu):
    if obtenu != attendu:
        FAIL.append(f"{cas} : obtenu {obtenu!r}, attendu {attendu!r}")
        print(f"  ECHEC  {cas} — obtenu {obtenu!r}, attendu {attendu!r}")
    else:
        print(f"  ok     {cas}")


def verifier_proche(cas: str, obtenu, attendu, tolerance=0.51):
    if obtenu is None or abs(float(obtenu) - float(attendu)) > tolerance:
        FAIL.append(f"{cas} : obtenu {obtenu!r}, attendu ~{attendu!r}")
        print(f"  ECHEC  {cas} — obtenu {obtenu!r}, attendu ~{attendu!r}")
    else:
        print(f"  ok     {cas}")


def base():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE production_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operateur TEXT, date_operation TEXT, operation TEXT,
            operation_code TEXT, operation_category TEXT,
            machine TEXT, no_dossier TEXT, client TEXT, designation TEXT,
            quantite_a_traiter REAL DEFAULT 0, quantite_traitee REAL DEFAULT 0,
            commentaire TEXT, est_annule INTEGER DEFAULT 0,
            annule_motif TEXT, annule_par TEXT, annule_le TEXT,
            metrage_prevu REAL, metrage_reel REAL,
            metrage_total_debut REAL, metrage_total_fin REAL
        );
        CREATE TABLE dossier_info_prod (
            no_dossier TEXT PRIMARY KEY NOT NULL, ref_produit_norm TEXT,
            texte TEXT NOT NULL, auteur TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT, updated_par TEXT
        );
        CREATE TABLE arret_seuils_franchis (
            id INTEGER PRIMARY KEY AUTOINCREMENT, saisie_id INTEGER NOT NULL,
            no_dossier TEXT, machine TEXT, operation_code TEXT NOT NULL,
            operation TEXT, operateur TEXT, regle TEXT NOT NULL,
            compteur INTEGER NOT NULL DEFAULT 0,
            duree_saisie_min REAL, duree_cumul_min REAL,
            commentaire_present INTEGER NOT NULL DEFAULT 0,
            explication_exigee INTEGER NOT NULL DEFAULT 0,
            explication_texte TEXT, explication_le TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE produit_series (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ref_produit_norm TEXT NOT NULL,
            no_dossier TEXT NOT NULL, machine TEXT, date_fin TEXT,
            temps_calage_min REAL, temps_prod_min REAL, temps_arret_min REAL,
            metrage_m REAL, vitesse_m_min REAL, commentaires TEXT,
            nb_nc INTEGER DEFAULT 0, cloture_le TEXT NOT NULL
        );
        CREATE TABLE retour_prod_ecrits (
            cle TEXT PRIMARY KEY NOT NULL, no_dossier TEXT,
            valide INTEGER NOT NULL DEFAULT 0, valide_par TEXT, valide_le TEXT,
            masque INTEGER NOT NULL DEFAULT 0, masque_par TEXT, masque_le TEXT
        );
        CREATE TABLE retour_prod_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, no_dossier TEXT NOT NULL,
            cle_ecrit TEXT, texte TEXT NOT NULL, auteur TEXT NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT, updated_par TEXT
        );
        CREATE TABLE nc_dossiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT, numero TEXT NOT NULL UNIQUE,
            titre TEXT NOT NULL, gravite TEXT, statut TEXT, date_nc TEXT,
            type_nc TEXT, service_concerne TEXT, no_dossier TEXT
        );
        """
    )
    return conn


def saisie(conn, minutes_apres, code, categorie, operateur="Marc",
           no_dossier="D-100", machine="Cohesio 1", operation=None,
           metrage_reel=None, metrage_prevu=None, commentaire=None,
           est_annule=0, annule_motif=None, ctr_debut=None, ctr_fin=None):
    conn.execute(
        """INSERT INTO production_data
           (operateur, date_operation, operation, operation_code, operation_category,
            machine, no_dossier, client, designation, commentaire, est_annule,
            annule_motif, metrage_prevu, metrage_reel,
            metrage_total_debut, metrage_total_fin)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (operateur, (T0 + timedelta(minutes=minutes_apres)).strftime("%Y-%m-%dT%H:%M:%S"),
         operation or code, code, categorie, machine, no_dossier,
         "Client Test", "Etiquette 100x50", commentaire, est_annule,
         annule_motif, metrage_prevu, metrage_reel, ctr_debut, ctr_fin),
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]


# ─── 1. Repartition du temps ─────────────────────────────────────────────────

def test_temps_par_categorie():
    print("\n1. Repartition du temps par categorie")
    conn = base()
    #  08:00 calage (02) -> 08:30   = 30 min calage
    #  08:30 production  -> 09:15   = 45 min production
    #  09:15 arret (53)  -> 09:35   = 20 min arret
    #  09:35 production  -> 10:05   = 30 min production
    #  10:05 fin (89)                 derniere : aucune duree
    saisie(conn, 0, "02", "calage")
    saisie(conn, 30, "03", "production")
    saisie(conn, 75, "53", "arret", operation="Casse bande")
    saisie(conn, 95, "03", "production")
    saisie(conn, 125, "89", "personnel", metrage_reel=12000)

    t = svc.temps_par_categorie(svc._saisies(conn, "D-100"))
    verifier("calage", svc._minutes_de(t, "calage"), 30.0)
    verifier("production", svc._minutes_de(t, "production"), 75.0)
    verifier("arret", svc._minutes_de(t, "arret"), 20.0)
    verifier("total", t["total_minutes"], 125.0)
    verifier("aucune saisie ouverte", len(t["saisies_ouvertes"]), 0)


def test_deux_conducteurs_ne_se_chainent_pas():
    print("\n2. Deux conducteurs ne se chainent pas l'un a l'autre")
    conn = base()
    # Marc travaille de 08:00 a 09:00. Sophie ouvre une saisie a 08:10.
    # Si le chainage ignorait l'operateur, la production de Marc s'arreterait
    # a 08:10 et un ecart negatif apparaitrait sur Sophie.
    saisie(conn, 0, "03", "production", operateur="Marc")
    saisie(conn, 60, "89", "personnel", operateur="Marc", metrage_reel=5000)
    saisie(conn, 10, "03", "production", operateur="Sophie")
    saisie(conn, 70, "89", "personnel", operateur="Sophie", metrage_reel=9000)

    t = svc.temps_par_categorie(svc._saisies(conn, "D-100"))
    # Marc : 60 min. Sophie : 60 min. Total 120, et non 50 + 60.
    verifier("production cumulee des deux conducteurs", svc._minutes_de(t, "production"), 120.0)


def test_saisie_annulee_exclue():
    print("\n3. Une saisie annulee ne compte pas dans le temps")
    conn = base()
    saisie(conn, 0, "03", "production")
    saisie(conn, 60, "50", "arret", est_annule=1, annule_motif="Erreur de code")
    saisie(conn, 90, "89", "personnel", metrage_reel=3000)

    t = svc.temps_par_categorie(svc._saisies(conn, "D-100"))
    verifier("aucun temps d'arret", svc._minutes_de(t, "arret"), 0.0)
    # La production court jusqu'a la saisie suivante NON annulee : 90 min.
    verifier("production non coupee par la ligne annulee", svc._minutes_de(t, "production"), 90.0)


def test_saisie_restee_ouverte():
    print("\n4. Saisie restee ouverte d'un jour a l'autre")
    conn = base()
    saisie(conn, 0, "03", "production")
    saisie(conn, 600, "89", "personnel", metrage_reel=8000)   # 10 h plus tard

    t = svc.temps_par_categorie(svc._saisies(conn, "D-100"))
    verifier("le temps reste compte (aligne sur le rapport hebdo)",
             svc._minutes_de(t, "production"), 600.0)
    verifier("mais il est signale", len(t["saisies_ouvertes"]), 1)
    cat_prod = [c for c in t["categories"] if c["categorie"] == "production"][0]
    verifier("et isole dans minutes_douteuses", cat_prod["minutes_douteuses"], 600.0)


# ─── 5. Metrage ──────────────────────────────────────────────────────────────

def test_metrage():
    print("\n5. Metrage : ecart de compteur, jamais le compteur brut")

    def m(saisies):
        return svc.metrage_dossier(saisies, "89", "01", "90")

    # Cas nominal : 01 pose le compteur de debut, 89 celui de fin.
    conn = base()
    saisie(conn, 0, "01", "personnel", ctr_debut=91_994_681)
    saisie(conn, 200, "89", "personnel", ctr_fin=92_006_681)
    r = m(svc._saisies(conn, "D-100"))
    verifier("ecart de compteur", r["reel"], 12000.0)
    verifier("fiable", r["fiable"], True)

    # Sans compteur de debut : PAS de metrage. Prendre 0 pour origine sortirait
    # le compteur machine entier (91 994 681 m), l'erreur d'ordre de grandeur
    # qui a deja fausse les besoins matieres.
    conn = base()
    saisie(conn, 0, "01", "personnel")
    saisie(conn, 200, "89", "personnel", ctr_fin=92_006_681)
    r = m(svc._saisies(conn, "D-100"))
    verifier("sans compteur de debut : aucun metrage", r["reel"], 0.0)
    verifier("et signale non fiable", r["fiable"], False)
    verifier("la cloture orpheline est comptee", r["fins_sans_debut"], 1)

    # Repli sur l'ancien couple de colonnes pour les lignes anterieures.
    conn = base()
    saisie(conn, 0, "01", "personnel", metrage_prevu=1000)
    saisie(conn, 200, "89", "personnel", metrage_reel=4500)
    verifier("repli metrage_prevu / metrage_reel", m(svc._saisies(conn, "D-100"))["reel"], 3500.0)

    # Les nouvelles colonnes priment sur le repli.
    conn = base()
    saisie(conn, 0, "01", "personnel", ctr_debut=1000, metrage_prevu=99999)
    saisie(conn, 200, "89", "personnel", ctr_fin=4000, metrage_reel=99999)
    verifier("les colonnes compteur priment", m(svc._saisies(conn, "D-100"))["reel"], 3000.0)

    # Deux cycles : les ecarts s'additionnent.
    conn = base()
    saisie(conn, 0, "01", "personnel", ctr_debut=1000)
    saisie(conn, 100, "89", "personnel", ctr_fin=3000)
    saisie(conn, 200, "01", "personnel", ctr_debut=3000)
    saisie(conn, 300, "89", "personnel", ctr_fin=8000)
    r = m(svc._saisies(conn, "D-100"))
    verifier("deux cycles additionnes", r["reel"], 7000.0)
    verifier("deux cycles comptes", r["cycles"], 2)

    # Le compteur de debut appartient au DOSSIER : l'equipe qui cloture n'a pas
    # forcement pose le code de debut.
    conn = base()
    saisie(conn, 0, "01", "personnel", operateur="Marc", ctr_debut=1000)
    saisie(conn, 300, "89", "personnel", operateur="Sophie", ctr_fin=6000)
    verifier("debut pose par un autre conducteur",
             m(svc._saisies(conn, "D-100"))["reel"], 5000.0)

    # L'annulation borne un cycle comme la fin, avec son propre compteur.
    conn = base()
    saisie(conn, 0, "01", "personnel", ctr_debut=1000)
    saisie(conn, 200, "90", "annulation", ctr_debut=1000, ctr_fin=2500)
    verifier("annulation bornee comme une fin",
             m(svc._saisies(conn, "D-100"))["reel"], 1500.0)

    verifier("aucune saisie", m([])["reel"], 0.0)


def test_mediane():
    print("\n6. Mediane")
    verifier("impair", svc.mediane([10, 30, 20]), 20.0)
    verifier("pair", svc.mediane([10, 20, 30, 40]), 25.0)
    verifier("vide", svc.mediane([]), None)


# ─── 7. Reperes de la reference ──────────────────────────────────────────────

def test_reperes_reference():
    print("\n7. Le repere d'une reference exclut le dossier juge")
    conn = base()
    for i, (dossier, vitesse) in enumerate(
            [("D-001", 10.0), ("D-002", 12.0), ("D-003", 14.0), ("D-100", 2.0)]):
        conn.execute(
            """INSERT INTO produit_series
               (ref_produit_norm, no_dossier, machine, date_fin, temps_calage_min,
                temps_prod_min, temps_arret_min, metrage_m, vitesse_m_min, cloture_le)
               VALUES ('REF-A',?,'Cohesio 1',?,?,?,?,?,?,?)""",
            (dossier, f"2026-05-{10 + i:02d}T12:00:00", 20.0 + i, 100.0, 15.0,
             1000.0, vitesse, "2026-05-20T12:00:00"),
        )
    conn.commit()

    r = svc.reperes_reference(conn, "REF-A", "D-100")
    verifier("3 series retenues", r["series"], 3)
    # m/min, sans conversion : 10, 12, 14 -> mediane 12. Le 2.0 (D-100) est exclu.
    verifier("mediane des cadences passees", r["cadence_mediane_m_min"], 12.0)
    verifier("reference inconnue", svc.reperes_reference(conn, None)["series"], 0)


# ─── 8. Compte-rendu complet ─────────────────────────────────────────────────

def dossier_complet(conn):
    # Compteur de debut sur le code 01 : sans lui, la regle canonique refuse
    # d'inventer un metrage (et c'est le bug observe en production).
    saisie(conn, -5, "01", "personnel", operation="Demarrer un dossier", ctr_debut=91_994_681)
    saisie(conn, 0, "02", "calage")
    saisie(conn, 30, "03", "production")
    saisie(conn, 90, "53", "arret", operation="Casse bande",
           commentaire="Bobine mal enroulee, changee")
    saisie(conn, 120, "03", "production")
    saisie(conn, 180, "89", "personnel", ctr_fin=92_014_681)
    conn.execute(
        """INSERT INTO arret_seuils_franchis
           (saisie_id, no_dossier, machine, operation_code, operation, operateur,
            regle, compteur, duree_saisie_min, explication_exigee,
            explication_texte, created_at)
           VALUES (3,'D-100','Cohesio 1','53','Casse bande','Marc','repetition',4,30,1,
                   'Bobine du lot 4412, defaut de refente','2026-06-08T09:30:00')""")
    conn.commit()


def test_compte_rendu():
    print("\n8. Compte-rendu assemble")
    conn = base()
    dossier_complet(conn)
    conn.execute(
        """INSERT INTO dossier_info_prod (no_dossier, ref_produit_norm, texte, auteur, created_at)
           VALUES ('D-100','REF-A','Prevoir un passage a vitesse reduite sur cette reference',
                   'Marc','2026-06-08T11:05:00')""")
    conn.execute(
        """INSERT INTO nc_dossiers (numero, titre, gravite, statut, date_nc, no_dossier)
           VALUES ('NC-26-014','Decoupe hors tolerance','mineure','ouverte','2026-06-08','D-100')""")
    conn.commit()

    cr = svc.compte_rendu(conn, "D-100")
    verifier("dossier trouve", cr["existe"], True)
    verifier("machine", cr["identite"]["machine"], "Cohesio 1")
    verifier("cloture", cr["identite"]["cloture"], True)
    verifier("conducteurs", cr["identite"]["conducteurs"], ["Marc"])
    verifier("metrage", cr["metrage"]["reel"], 20000.0)
    # production 60 + 60 = 120 min -> 20000 m / 120 min = 166,7 m/min
    verifier("vitesse de production (hors arrets)", cr["vitesse_m_min"], 166.7)
    # cadence : denominateur production + arret = 120 + 30 = 150 min
    # -> 133,3 m/min. C'est la SEULE valeur comparable a produit_series.vitesse_m_min,
    # calcule par dossier_stats.py sur ce meme denominateur et dans la meme unite.
    verifier("cadence (arrets compris)", cr["cadence_m_min"], 133.3)
    verifier("un seuil franchi", len(cr["seuils"]), 1)
    verifier("seuil explique", cr["seuils"][0]["sans_explication"], False)
    verifier("info prod presente", bool(cr["ecrits"]["info_prod"]), True)
    verifier("info prod substantielle", cr["ecrits"]["info_prod"]["substantiel"], True)
    verifier("un commentaire de saisie", len(cr["ecrits"]["commentaires"]), 1)
    verifier("une NC", len(cr["non_conformites"]), 1)
    verifier("aucun point de vigilance", cr["vigilance"], [])


def test_cadence_comparable_au_repere():
    print("\n8 bis. La cadence se compare a un repere calcule pareil")
    conn = base()
    dossier_complet(conn)
    # Repere historique : 100 m/min, calcule par dossier_stats sur
    # (production + arret). Le dossier courant fait 133,3 m/min de cadence.
    for i, d in enumerate(("D-201", "D-202", "D-203")):
        conn.execute(
            """INSERT INTO produit_series (ref_produit_norm, no_dossier, machine,
               date_fin, vitesse_m_min, cloture_le)
               VALUES ('REF-A',?,'Cohesio 1',?,100.0,'2026-05-20T12:00:00')""",
            (d, f"2026-05-1{i}T12:00:00"))
    conn.execute(
        """INSERT INTO dossier_info_prod (no_dossier, ref_produit_norm, texte, auteur, created_at)
           VALUES ('D-100','REF-A','Tension a baisser','Marc','2026-06-08T11:05:00')""")
    conn.commit()

    cr = svc.compte_rendu(conn, "D-100")
    verifier("repere retrouve", cr["reference"]["cadence_mediane_m_min"], 100.0)
    # 133,3 vs 100 = +33,3 %. Sur la vitesse hors arrets (166,7) l'ecart aurait
    # ete de +66 % : c'est exactement l'erreur que ce cas empeche.
    verifier_proche("ecart calcule sur la cadence", cr["ecarts"]["cadence_pct"], 33.3, 0.2)
    verifier("aucun ecart de vitesse expose",
             "vitesse_pct" in cr["ecarts"], False)
    # L'unite est celle de la machine : jamais de m/h dans la sortie.
    verifier("aucune cle en m/h",
             [k for k in list(cr) + list(cr["ecarts"]) + list(cr["reference"])
              if k.endswith("_m_h")], [])


def test_vigilance():
    print("\n9. Points de vigilance")
    conn = base()
    dossier_complet(conn)
    # Pas d'info prod, et le seuil devient non explique.
    conn.execute("UPDATE arret_seuils_franchis SET explication_texte = NULL")
    conn.commit()

    cr = svc.compte_rendu(conn, "D-100")
    cles = {v["cle"] for v in cr["vigilance"]}
    verifier("info prod absente signalee", "info_prod_absente" in cles, True)
    verifier("seuil sans explication signale", "seuils_sans_explication" in cles, True)
    verifier("aucun point nominatif",
             all("Marc" not in v["texte"] for v in cr["vigilance"]), True)


def test_ras_non_substantiel():
    print("\n10. « R.A.S. » est une reponse, pas une information")
    conn = base()
    dossier_complet(conn)
    for texte in ("R.A.S.", "RAS", "ras", "neant", "Néant", "R A S", "ok", ""):
        conn.execute("DELETE FROM dossier_info_prod")
        conn.execute(
            """INSERT INTO dossier_info_prod (no_dossier, texte, auteur, created_at)
               VALUES ('D-100',?,'Marc','2026-06-08T11:05:00')""", (texte,))
        conn.commit()
        info = svc.info_prod(conn, "D-100")
        verifier(f"« {texte} » non substantiel", info["substantiel"], False)


# ─── 11. Retour atelier ──────────────────────────────────────────────────────

def test_retour_atelier():
    print("\n11. Retour atelier")
    conn = base()
    dossier_complet(conn)
    conn.execute(
        """INSERT INTO dossier_info_prod (no_dossier, ref_produit_norm, texte, auteur, created_at)
           VALUES ('D-100','REF-A','Vitesse reduite conseillee','Marc','2026-06-08T11:05:00')""")
    conn.commit()

    r = svc.retour_atelier(conn, "Cohesio 1", SEMAINE_DEBUT, SEMAINE_FIN)
    verifier("un dossier", r["dossiers"], 1)
    verifier("conducteurs listes sans chiffre", r["conducteurs"], ["Marc"])
    verifier("metrage", r["production"]["metrage"], 20000.0)
    verifier("temps de production", r["production"]["minutes_production"], 120.0)
    verifier("temps d'arret", r["production"]["minutes_arret"], 30.0)
    verifier("vitesse machine en m/min", r["production"]["vitesse_m_min"], 166.7)
    verifier("une reference produite", len(r["references"]), 1)
    verifier("code d'arret le plus couteux", r["arrets_couteux"][0]["code"], "53")

    origines = sorted({e["origine"] for e in r["ecrits"]})
    verifier("les trois sources d'ecrit remontent",
             origines, ["arret", "commentaire", "info_prod"])

    # Aucun chiffre rattache a une personne dans la sortie.
    verifier("aucune metrique par conducteur",
             all(isinstance(c, str) for c in r["conducteurs"]), True)


def test_machine_sans_donnee():
    print("\n12. A vide, rien ne doit ressembler a une carte pleine")
    conn = base()
    cr = svc.compte_rendu(conn, "D-INEXISTANT")
    verifier("dossier inconnu", cr["existe"], False)

    r = svc.retour_atelier(conn, "Cohesio 1", SEMAINE_DEBUT, SEMAINE_FIN)
    verifier("aucun dossier", r["dossiers"], 0)
    verifier("aucun conducteur", r["conducteurs"], [])
    verifier("aucune reference", r["references"], [])
    verifier("aucun arret", r["arrets_couteux"], [])
    verifier("aucun ecrit", r["ecrits"], [])
    verifier("vitesse indeterminee, pas zero", r["production"]["vitesse_m_min"], None)
    verifier("aucune machine sur la periode",
             svc.machines_periode(conn, SEMAINE_DEBUT, SEMAINE_FIN), [])
    verifier("liste de comptes-rendus vide",
             svc.comptes_rendus_periode(conn, SEMAINE_DEBUT, SEMAINE_FIN), [])


def test_recherche_tous_dossiers():
    print("\n12 bis. La recherche atteint n'importe quel dossier")
    conn = base()
    # Un dossier cloture il y a trois mois, hors de toute periode courante.
    saisie(conn, -130000, "03", "production", no_dossier="D-300", operateur="Marc")
    saisie(conn, -129940, "89", "personnel", no_dossier="D-300", operateur="Marc",
           metrage_reel=5000)
    # Un dossier encore EN COURS : aucune saisie de fin.
    saisie(conn, 0, "02", "calage", no_dossier="D-400", operateur="Sophie")
    saisie(conn, 40, "03", "production", no_dossier="D-400", operateur="Sophie")
    conn.commit()

    verifier("terme trop court ignore", svc.rechercher_dossiers(conn, "D"), [])

    r = {d["no_dossier"]: d for d in svc.rechercher_dossiers(conn, "D-")}
    verifier("le dossier ancien est trouve", "D-300" in r, True)
    verifier("le dossier en cours aussi", "D-400" in r, True)
    verifier("etat de cloture correct (ancien)", r["D-300"]["cloture"], True)
    verifier("etat de cloture correct (en cours)", r["D-400"]["cloture"], False)

    # Recherche par client, pas seulement par numero.
    verifier("recherche par client",
             len(svc.rechercher_dossiers(conn, "Client Test")) >= 2, True)

    # Et le compte-rendu s'ouvre sur les deux, cloture ou non.
    verifier("compte-rendu d'un dossier ancien",
             svc.compte_rendu(conn, "D-300")["existe"], True)
    cr = svc.compte_rendu(conn, "D-400")
    verifier("compte-rendu d'un dossier en cours", cr["existe"], True)
    verifier("et il se sait non cloture", cr["identite"]["cloture"], False)
    verifier("un dossier en cours n'exige pas d'info prod",
             [v["cle"] for v in cr["vigilance"]], [])


def test_suivi_des_remontees():
    print("\n12 ter. Suivi des remontees : valider, commenter, corriger")
    conn = base()
    dossier_complet(conn)
    conn.execute(
        """INSERT INTO dossier_info_prod (no_dossier, texte, auteur, created_at)
           VALUES ('D-100','Tension a baisser','Marc','2026-06-08T11:05:00')""")
    conn.commit()

    # La cle doit etre stable et distinguer les sources.
    verifier("cle d'un commentaire de saisie", svc.cle_ecrit("commentaire", 4), "saisie:4")
    verifier("cle d'une info prod", svc.cle_ecrit("info_prod", "D-100"), "infoprod:D-100")
    verifier("cle d'un seuil", svc.cle_ecrit("arret", 4), "seuil:4")
    verifier("cle d'une note", svc.cle_ecrit("note", 7), "note:7")

    cr = svc.compte_rendu(conn, "D-100")
    verifier("rien n'est valide au depart",
             any(e.get("valide") for e in cr["ecrits"]["commentaires"]), False)
    verifier("l'info prod porte sa cle", cr["ecrits"]["info_prod"]["cle"], "infoprod:D-100")
    verifier("un commentaire de saisie est modifiable",
             cr["ecrits"]["commentaires"][0]["modifiable"], True)
    verifier("un seuil porte sa cle", cr["seuils"][0]["cle"].startswith("seuil:"), True)

    # Validation, puis retour en arriere.
    cle = cr["ecrits"]["info_prod"]["cle"]
    svc.valider_ecrit(conn, cle, "D-100", True, "Eugene")
    cr = svc.compte_rendu(conn, "D-100")
    verifier("info prod validee", cr["ecrits"]["info_prod"]["valide"], True)
    verifier("et l'auteur est trace", cr["ecrits"]["info_prod"]["valide_par"], "Eugene")
    verifier("valider n'efface pas la remontee",
             cr["ecrits"]["info_prod"]["texte"], "Tension a baisser")

    svc.valider_ecrit(conn, cle, "D-100", False, "Eugene")
    cr = svc.compte_rendu(conn, "D-100")
    verifier("devalidation possible", cr["ecrits"]["info_prod"]["valide"], False)
    verifier("et l'auteur est efface", cr["ecrits"]["info_prod"]["valide_par"], "")

    # Note ajoutee, puis corrigee, puis supprimee par un texte vide.
    note = svc.ajouter_note(conn, "D-100", "Vu avec le chef d'atelier", "Eugene", cle)
    verifier("note creee", note["texte"], "Vu avec le chef d'atelier")
    verifier("note rattachee a la remontee", note["cle_ecrit"], cle)
    cr = svc.compte_rendu(conn, "D-100")
    # Une reponse se range SOUS la remontee qu'elle commente, en citation :
    # ajoutee a la file, elle la noyait.
    verifier("la reponse ne grossit pas la liste", len(cr["ecrits"]["notes"]), 0)
    verifier("elle est rangee sous sa remontee",
             len(cr["ecrits"]["info_prod"]["reponses"]), 1)
    verifier("avec son texte",
             cr["ecrits"]["info_prod"]["reponses"][0]["texte"], "Vu avec le chef d'atelier")
    verifier("et sa cle", cr["ecrits"]["info_prod"]["reponses"][0]["cle"],
             "note:" + str(note["id"]))

    # Une note libre, elle, reste une remontee a part entiere.
    libre = svc.ajouter_note(conn, "D-100", "Penser a commander des lames", "Eugene")
    cr = svc.compte_rendu(conn, "D-100")
    verifier("une note sans parent reste dans la liste", len(cr["ecrits"]["notes"]), 1)
    svc.modifier_note(conn, libre["id"], "", "Eugene")

    svc.modifier_note(conn, note["id"], "Vu avec le chef d'atelier le 12", "Eugene")
    verifier("note corrigee",
             svc.notes_dossier(conn, "D-100")[0]["texte"], "Vu avec le chef d'atelier le 12")
    verifier("dernier correcteur trace",
             svc.notes_dossier(conn, "D-100")[0]["updated_par"], "Eugene")
    verifier("note vide = note supprimee",
             svc.modifier_note(conn, note["id"], "   ", "Eugene"), None)
    verifier("et elle a disparu", svc.notes_dossier(conn, "D-100"), [])

    # Correction du texte d'une saisie.
    sid = cr["ecrits"]["commentaires"][0]["saisie_id"]
    verifier("commentaire de saisie corrige",
             svc.modifier_commentaire_saisie(conn, sid, "Bobine lot 4412 — reprise"), True)
    cr = svc.compte_rendu(conn, "D-100")
    verifier("le nouveau texte remonte",
             cr["ecrits"]["commentaires"][0]["texte"], "Bobine lot 4412 — reprise")

    # Masquer : hors sujet, ni traite ni efface.
    cle_com = svc.compte_rendu(conn, "D-100")["ecrits"]["commentaires"][0]["cle"]
    svc.masquer_ecrit(conn, cle_com, "D-100", True, "Eugene")
    cr = svc.compte_rendu(conn, "D-100")
    verifier("la remontee est marquee masquee",
             cr["ecrits"]["commentaires"][0]["masque"], True)
    verifier("masquer n'est pas valider",
             cr["ecrits"]["commentaires"][0]["valide"], False)
    r = svc.retour_atelier(conn, "Cohesio 1", SEMAINE_DEBUT, SEMAINE_FIN)
    verifier("elle quitte la liste principale de la feuille",
             any(e["cle"] == cle_com for e in r["ecrits"]), False)
    verifier("mais reste consultable a part",
             any(e["cle"] == cle_com for e in r["ecrits_masques"]), True)
    svc.masquer_ecrit(conn, cle_com, "D-100", False, "Eugene")
    r = svc.retour_atelier(conn, "Cohesio 1", SEMAINE_DEBUT, SEMAINE_FIN)
    verifier("le demasquage la ramene",
             any(e["cle"] == cle_com for e in r["ecrits"]), True)

    # La feuille atelier porte les memes etats.
    svc.valider_ecrit(conn, cle, "D-100", True, "Eugene")
    r = svc.retour_atelier(conn, "Cohesio 1", SEMAINE_DEBUT, SEMAINE_FIN)
    valides = [e for e in r["ecrits"] if e.get("valide")]
    verifier("la feuille montre l'etat de validation", len(valides), 1)
    verifier("chaque ecrit de la feuille porte sa cle",
             all(e.get("cle") for e in r["ecrits"]), True)


def test_dernier_jour_saisi():
    print("\n12 quater. « Hier » = derniere journee reellement travaillee")
    conn = base()
    verifier("base vide : aucun jour", svc.dernier_jour_saisi(conn, "2026-06-14"), None)

    # T0 est un lundi (8 juin 2026). On pose du vendredi et du samedi precedents.
    saisie(conn, -3 * 24 * 60, "03", "production")        # vendredi 05/06
    saisie(conn, -2 * 24 * 60, "03", "production")        # samedi 06/06
    conn.commit()

    # Un lundi matin, la veille est un dimanche vide : on doit remonter au samedi.
    verifier("le dimanche vide renvoie au samedi",
             svc.dernier_jour_saisi(conn, "2026-06-07"), "2026-06-06")
    # Si la veille a bien tourne, c'est elle qu'on garde.
    verifier("une veille travaillee reste la veille",
             svc.dernier_jour_saisi(conn, "2026-06-06"), "2026-06-06")

    # La journee en cours n'est jamais remontee : la borne l'exclut.
    saisie(conn, 0, "03", "production")                   # lundi 08/06
    conn.commit()
    verifier("la journee en cours est exclue par la borne",
             svc.dernier_jour_saisi(conn, "2026-06-07"), "2026-06-06")

    # Une journee qui n'a que des saisies annulees n'a pas ete travaillee.
    conn2 = base()
    saisie(conn2, -2 * 24 * 60, "03", "production")        # samedi : reel
    saisie(conn2, -1 * 24 * 60, "03", "production", est_annule=1)  # dimanche : annule
    conn2.commit()
    verifier("un jour entierement annule ne compte pas",
             svc.dernier_jour_saisi(conn2, "2026-06-07"), "2026-06-06")


def _s(conn, quand, code, cat, dos, machine="Cohesio 1", operateur="Marc", operation=None):
    conn.execute(
        """INSERT INTO production_data
           (operateur, date_operation, operation, operation_code, operation_category,
            machine, no_dossier, client, designation, est_annule)
           VALUES (?,?,?,?,?,?,?,'NESTLE','Etiquette',0)""",
        (operateur, quand, operation or code, code, cat, machine, dos))


def test_frise():
    print("\n12 quinquies. Frise : axe replie, phases, debordements")
    conn = base()
    # Jeudi 27 : un dossier de 06:00 a 14:00, avec calage, prod, arret, prod.
    for q, c, cat in [("2026-08-27T06:00:00", "02", "calage"),
                      ("2026-08-27T07:00:00", "03", "production"),
                      ("2026-08-27T10:00:00", "53", "arret"),
                      ("2026-08-27T10:30:00", "03", "production"),
                      ("2026-08-27T14:00:00", "89", "personnel")]:
        _s(conn, q, c, cat, "D-1")
    # Vendredi 28 : rien. Samedi 29 : une demi-journee sur une autre machine.
    _s(conn, "2026-08-29T06:00:00", "03", "production", "D-2", "Cohesio 2", "Sophie")
    _s(conn, "2026-08-29T10:00:00", "89", "personnel", "D-2", "Cohesio 2", "Sophie")
    conn.commit()

    f = svc.frise(conn, "2026-08-27T00:00:00", "2026-08-29T23:59:59")
    verifier("deux journees a l'axe (le vendredi vide est replie)", len(f["axe"]), 2)
    verifier("jeudi : 8 h de saisie", f["axe"][0]["heures"], 8.0)
    verifier("samedi : 4 h", f["axe"][1]["heures"], 4.0)
    # Largeurs proportionnelles : 8 h contre 4 h -> deux tiers / un tiers.
    verifier_proche("largeur du jeudi", f["axe"][0]["largeur"], 66.67, 0.1)
    verifier_proche("largeur du samedi", f["axe"][1]["largeur"], 33.33, 0.1)
    verifier("l'axe fait 100 %",
             round(sum(a["largeur"] for a in f["axe"]), 2), 100.0)
    verifier("le samedi porte la coupure", f["axe"][1]["coupure_avant"], True)
    verifier("le jeudi n'en porte pas", f["axe"][0]["coupure_avant"], False)

    verifier("une ligne par machine", [l["machine"] for l in f["lignes"]],
             ["Cohesio 1", "Cohesio 2"])
    d1 = f["lignes"][0]["slots"][0]
    verifier("le dossier commence au debut de l'axe", d1["x"], 0.0)
    verifier_proche("et occupe tout le jeudi", d1["largeur"], 66.67, 0.1)
    verifier("aucun debordement", (d1["deborde_avant"], d1["deborde_apres"]), (False, False))
    verifier("quatre phases", len(d1["segments"]), 4)
    verifier("les phases dans l'ordre",
             [g["categorie"] for g in d1["segments"]],
             ["calage", "production", "arret", "production"])
    verifier("les phases remplissent le slot",
             round(sum(g["largeur"] for g in d1["segments"])), 100)
    verifier("aucun chevauchement",
             all(d1["segments"][i]["x"] + d1["segments"][i]["largeur"] <= d1["segments"][i+1]["x"] + 0.01
                 for i in range(len(d1["segments"]) - 1)), True)


def test_frise_debordements():
    print("\n12 sexies. Frise : ce qui deborde de la periode")
    conn = base()
    # Dossier commence la veille de la periode et non termine a la fin.
    _s(conn, "2026-08-26T14:00:00", "03", "production", "D-9")
    _s(conn, "2026-08-27T08:00:00", "53", "arret", "D-9")
    _s(conn, "2026-08-27T09:00:00", "03", "production", "D-9")
    _s(conn, "2026-08-28T10:00:00", "89", "personnel", "D-9")
    conn.commit()

    f = svc.frise(conn, "2026-08-27T00:00:00", "2026-08-27T23:59:59")
    sl = f["lignes"][0]["slots"][0]
    verifier("commence avant la periode", sl["deborde_avant"], True)
    verifier("et n'est pas fini a la fin", sl["deborde_apres"], True)
    verifier("le slot est cale au debut de l'axe", sl["x"], 0.0)
    verifier("le slot va jusqu'au bout", round(sl["x"] + sl["largeur"]), 100)
    verifier("les dates reelles sont conservees", sl["debut"][:10], "2026-08-26")

    # Une saisie restee ouverte ne doit pas deplier la nuit.
    conn2 = base()
    _s(conn2, "2026-08-27T06:00:00", "03", "production", "D-8")
    _s(conn2, "2026-08-27T14:00:00", "03", "production", "D-8")   # ouverte jusqu'au lendemain
    _s(conn2, "2026-08-28T09:00:00", "89", "personnel", "D-8")
    conn2.commit()
    f2 = svc.frise(conn2, "2026-08-27T00:00:00", "2026-08-28T23:59:59")
    verifier("la nuit reste repliee malgre la saisie ouverte",
             f2["axe"][0]["heures"], 8.0)

    verifier("periode sans saisie : frise vide",
             svc.frise(conn2, "2026-09-10T00:00:00", "2026-09-10T23:59:59")["vide"], True)


def test_statut_saisieprod():
    print("\n12 octies. Les phases parlent la langue de Saisieprod")
    # Cinq etats, pas plus : la frise reprend les couleurs de Saisieprod, donc
    # elle doit en reprendre exactement le vocabulaire.
    verifier("production", svc.statut_saisie("production"), "production")
    verifier("calage", svc.statut_saisie("calage"), "calage")
    verifier("arret", svc.statut_saisie("arret"), "arret")
    verifier("appro compte comme un arret", svc.statut_saisie("appro"), "arret")
    verifier("technique aussi", svc.statut_saisie("technique"), "arret")
    verifier("nettoyage", svc.statut_saisie("nettoyage"), "nettoyage")
    verifier("pause", svc.statut_saisie("pause"), "autre")
    verifier("personnel", svc.statut_saisie("personnel"), "autre")
    verifier("inconnu", svc.statut_saisie("zzz"), "autre")
    verifier("cinq etats seulement",
             sorted(set(svc.STATUT_SAISIE.values())),
             ["arret", "autre", "calage", "nettoyage", "production"])

    conn = base()
    dossier_complet(conn)
    conn.commit()
    segs = svc.compte_rendu(conn, "D-100")["frise"]["lignes"][0]["slots"][0]["segments"]
    verifier("chaque phase porte son statut", all(g.get("statut") for g in segs), True)


def test_frise_dossier():
    print("\n12 septies. Frise d'un seul dossier")
    conn = base()
    dossier_complet(conn)
    conn.commit()
    cr = svc.compte_rendu(conn, "D-100")
    verifier("le compte-rendu porte sa frise", cr["frise"]["vide"], False)
    verifier("une seule ligne", len(cr["frise"]["lignes"]), 1)
    verifier("un seul slot", len(cr["frise"]["lignes"][0]["slots"]), 1)
    verifier("qui occupe toute la largeur",
             round(cr["frise"]["lignes"][0]["slots"][0]["largeur"]), 100)
    verifier("dossier inconnu : frise vide",
             svc.frise_dossier(conn, "D-INEXISTANT")["vide"], True)


def test_minutes_txt():
    print("\n13. Format des durees")
    verifier("moins d'une heure", svc._minutes_txt(45), "45 min")
    verifier("heure pleine", svc._minutes_txt(120), "2 h")
    verifier("heure et minutes", svc._minutes_txt(95), "1 h 35")
    verifier("inconnu", svc._minutes_txt(None), "—")


# ─── 14. Une periode ne compte que ce qui s'y est passe ──────────────────────

def _atelier_trois_jours():
    """Un dossier qui tourne le 28, le 31 et le 01 — c'est le cas reel d'un
    reliquat qui revient. Le point du 31 ne doit connaitre que le 31."""
    conn = base()
    D = "D-REL"
    def ligne(jour, heure, minute, code, cat, ctr_deb=None, ctr_fin=None, op="Tony"):
        conn.execute(
            """INSERT INTO production_data
               (operateur, date_operation, operation, operation_code,
                operation_category, machine, no_dossier, client,
                metrage_total_debut, metrage_total_fin)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (op, "2026-08-%02dT%02d:%02d:00" % (jour, heure, minute),
             code + " - x", code, cat, "Cohesio 1", D, "KIABI", ctr_deb, ctr_fin))
    # 28/08 : une passe entiere, 3 h de production, cloturee.
    ligne(28, 13, 0, "01", "personnel", ctr_deb=1000)
    ligne(28, 13, 1, "03", "production")
    ligne(28, 16, 1, "89", "personnel", ctr_fin=4000)
    # 31/08 : une passe de 2 h, cloturee.
    ligne(31, 8, 0, "01", "personnel", ctr_deb=4000)
    ligne(31, 8, 1, "03", "production")
    ligne(31, 10, 1, "89", "personnel", ctr_fin=5200)
    conn.commit()
    return conn


def test_periode_borne_les_chiffres():
    print("\n14. Une periode ne compte que ce qui s'y est passe")
    conn = _atelier_trois_jours()
    DEB, FIN = "2026-08-31T00:00:00", "2026-08-31T23:59:59"

    at = svc.retour_atelier(conn, "Cohesio 1", DEB, FIN)
    p = at["production"]
    verifier_proche("production du 31 seule (2 h)", p["minutes_production"], 120)
    verifier_proche("metrage du 31 seul", p["metrage"], 1200)
    verifier("un seul dossier", at["dossiers"], 1)
    # 120 min pour 1200 m : la vitesse ne peut pas melanger les deux passes.
    verifier_proche("vitesse du 31", p["vitesse_m_min"], 10.0)

    # La fiche du dossier, elle, raconte sa vie entiere : c'est son role.
    entier = svc.compte_rendu(conn, "D-REL")
    verifier_proche("la fiche garde les deux passes",
                    svc._minutes_de(entier["temps"], "production"), 300)
    verifier_proche("et leur metrage cumule", entier["metrage"]["reel"], 4200)
    verifier("sans fenetre, pas de periode annoncee", entier["periode"], None)

    borne = svc.compte_rendu(conn, "D-REL", debut=DEB, fin=FIN)
    verifier("avec fenetre, la periode est annoncee",
             borne["periode"], {"debut": DEB, "fin": FIN})
    verifier_proche("temps borne", svc._minutes_de(borne["temps"], "production"), 120)
    verifier_proche("metrage borne", borne["metrage"]["reel"], 1200)

    # Le total affiche ne peut pas depasser la journee : c'est le controle qui
    # a fait tomber le defaut sur un vrai point de production.
    f = svc.frise(conn, DEB, FIN, "Cohesio 1")
    heures = sum(a["heures"] for a in f["axe"])
    total = p["minutes_production"] + p["minutes_calage"] + p["minutes_arret"]
    verifier("le total tient dans la journee", total <= heures * 60 + 1, True)


def test_fin_de_cycle_ne_dure_pas():
    print("\n15. Une saisie de fin de cycle ne dure pas")
    conn = base()
    # Fin de production a 10 h, le dossier repart quatre jours plus tard avec
    # le MEME operateur : sans la regle, l'ecart devient un bloc « personnel »
    # de plusieurs milliers de minutes, dessine en gris sur toute la frise.
    for (jour, h, m, code, cat) in [(8, 8, 0, "01", "personnel"),
                                    (8, 8, 1, "03", "production"),
                                    (8, 10, 0, "89", "personnel"),
                                    (12, 9, 0, "01", "personnel"),
                                    (12, 9, 1, "03", "production"),
                                    (12, 10, 0, "89", "personnel")]:
        conn.execute(
            """INSERT INTO production_data
               (operateur, date_operation, operation, operation_code,
                operation_category, machine, no_dossier)
               VALUES (?,?,?,?,?,?,?)""",
            ("Marc", "2026-06-%02dT%02d:%02d:00" % (jour, h, m),
             code + " - x", code, cat, "Cohesio 1", "D-FIN"))
    conn.commit()
    sa = svc._saisies(conn, "D-FIN")

    ivs = svc.intervalles(sa)
    codes = sorted({i["code"] for i in ivs})
    verifier("aucun intervalle ne part d'une fin de cycle", "89" in codes, False)
    verifier("les autres restent", codes, ["01", "03"])

    t = svc.temps_par_categorie(sa)
    verifier_proche("production des deux passes (119 + 59)",
                    svc._minutes_de(t, "production"), 178)
    verifier_proche("personnel reduit aux amorces", svc._minutes_de(t, "personnel"), 2)
    verifier("plus aucune saisie ouverte", len(t["saisies_ouvertes"]), 0)

    # Sur la frise, le gris disparait : il ne restait que par cet intervalle.
    fr = svc.frise(conn, "2026-06-08T00:00:00", "2026-06-08T23:59:59", "Cohesio 1")
    parts = {}
    for ligne in fr["lignes"]:
        for sl in ligne["slots"]:
            for g in sl["segments"]:
                parts[g["statut"]] = parts.get(g["statut"], 0) + g["largeur"]
    verifier("le ruban n'est plus gris", round(parts.get("autre", 0), 1) < 1.0, True)
    verifier_proche("il est en production", parts.get("production", 0), 100, 1.0)


def test_intervalles_bornes():
    print("\n16. Bornage d'un intervalle a cheval sur la periode")
    conn = base()
    for (h, code, cat) in [(22, "01", "personnel"), (22, "03", "production")]:
        conn.execute(
            """INSERT INTO production_data
               (operateur, date_operation, operation, operation_code,
                operation_category, machine, no_dossier)
               VALUES (?,?,?,?,?,?,?)""",
            ("Marc", "2026-06-08T%02d:%02d:00" % (h, 0 if code == "01" else 30),
             code + " - x", code, cat, "Cohesio 1", "D-CHEV"))
    conn.execute(
        """INSERT INTO production_data
           (operateur, date_operation, operation, operation_code,
            operation_category, machine, no_dossier)
           VALUES (?,?,?,?,?,?,?)""",
        ("Marc", "2026-06-09T02:00:00", "89 - x", "89", "personnel",
         "Cohesio 1", "D-CHEV"))
    conn.commit()
    sa = svc._saisies(conn, "D-CHEV")

    entier = [i for i in svc.intervalles(sa) if i["code"] == "03"][0]
    verifier_proche("sans fenetre, la duree reelle", entier["minutes"], 210)

    jour = svc.intervalles(sa, "2026-06-08T00:00:00", "2026-06-08T23:59:59")
    coupe = [i for i in jour if i["code"] == "03"][0]
    verifier_proche("borne a la fin de la journee", coupe["minutes"], 90)
    verifier_proche("la duree reelle reste lisible", coupe["minutes_brutes"], 210)
    verifier("l'intervalle se sait borne", coupe["bornee"], True)
    verifier("ses bornes reelles sont conservees",
             coupe["fin_brut"].strftime("%Y-%m-%dT%H:%M"), "2026-06-09T02:00")

    lendemain = svc.intervalles(sa, "2026-06-09T00:00:00", "2026-06-09T23:59:59")
    verifier_proche("le reste tombe le lendemain",
                    [i for i in lendemain if i["code"] == "03"][0]["minutes"], 120)
    verifier("aucun intervalle hors fenetre",
             all(i["debut"].day == 9 for i in lendemain), True)


# ─── 17. Le deroule des saisies d'une periode ────────────────────────────────

def test_saisies_periode():
    print("\n17. Le deroule des saisies d'une periode")
    conn = base()

    def pose(quand, code, cat, op="Marc", machine="Cohesio 1", dossier="D-100",
             annule=0, commentaire=None):
        conn.execute(
            """INSERT INTO production_data
               (operateur, date_operation, operation, operation_code,
                operation_category, machine, no_dossier, client, commentaire,
                est_annule)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (op, quand, code + " - x", code, cat, machine, dossier,
             "Client Test", commentaire, annule))

    conn.execute(
        """INSERT INTO produit_series
           (ref_produit_norm, no_dossier, machine, cloture_le)
           VALUES (?,?,?,?)""",
        ("REF-A", "D-100", "Cohesio 1", "2026-06-08T12:00:00"))

    pose("2026-06-07T22:00:00", "03", "production")          # la veille
    pose("2026-06-08T08:00:00", "01", "personnel")
    pose("2026-06-08T08:01:00", "03", "production", commentaire="bobine neuve")
    pose("2026-06-08T09:01:00", "53", "arret")
    pose("2026-06-08T09:11:00", "88", "production")
    pose("2026-06-08T10:00:00", "63", "pause", annule=1)      # annulee
    pose("2026-06-08T11:00:00", "03", "production", machine="Cohesio 2")
    pose("2026-06-09T07:00:00", "89", "personnel")            # le lendemain
    conn.commit()

    DEB, FIN = "2026-06-08T00:00:00", "2026-06-08T23:59:59"
    l = svc.saisies_periode(conn, "Cohesio 1", DEB, FIN)
    codes = [r["code"] for r in l]
    verifier("seules les saisies de la periode", codes, ["01", "03", "53", "88"])
    verifier("l'annulee est ecartee", "63" in codes, False)
    verifier("l'autre machine est ecartee",
             all(r["machine"] == "Cohesio 1" for r in l), True)

    par_code = {r["code"]: r for r in l}
    verifier("heure lisible", par_code["03"]["heure"], "08:01")
    verifier_proche("duree jusqu'a la suivante", par_code["03"]["minutes"], 60)
    verifier("duree en clair", par_code["53"]["minutes_txt"], "10 min")
    verifier("le commentaire suit", par_code["03"]["commentaire"], "bobine neuve")
    verifier("statut Saisieprod", par_code["53"]["statut"], "arret")
    verifier("le dossier suit", par_code["53"]["no_dossier"], "D-100")
    verifier("la reference produit est jointe",
             par_code["53"]["ref_produit_norm"], "REF-A")
    verifier("libelle de categorie", par_code["01"]["label"], "Entrees et sorties")

    # La derniere saisie de la journee tire sa duree de la suivante, qui est le
    # lendemain : sans la lire, elle n'aurait pas de duree. Mais elle est bornee
    # a la journee, pas comptee jusqu'au lendemain.
    derniere = par_code["88"]
    verifier_proche("bornee a la fin de la journee", derniere["minutes"], 60 * 14 + 49)
    verifier("et elle le sait", derniere["bornee"], True)

    # Toutes machines : la liste couvre l'atelier.
    verifier("sans machine, tout l'atelier",
             len(svc.saisies_periode(conn, "", DEB, FIN)), 5)

    # Le plafond garde les plus recentes.
    verifier("plafond respecte", len(svc.saisies_periode(conn, "", DEB, FIN, limite=2)), 2)
    verifier("et garde la fin",
             svc.saisies_periode(conn, "", DEB, FIN, limite=2)[-1]["heure"], "11:00")

    # La feuille d'atelier la porte.
    at = svc.retour_atelier(conn, "Cohesio 1", DEB, FIN)
    verifier("la feuille porte les saisies", len(at["saisies"]), 4)


def test_saisies_repiquage():
    print("\n18. Repiquage : memes masquages que l'onglet Saisies")
    conn = base()
    for code, cat in [("01", "personnel"), ("89", "personnel"), ("86", "personnel"),
                      ("87", "personnel"), ("03", "production"), ("53", "arret")]:
        conn.execute(
            """INSERT INTO production_data
               (operateur, date_operation, operation, operation_code,
                operation_category, machine, no_dossier)
               VALUES (?,?,?,?,?,?,?)""",
            ("Marc", "2026-06-08T08:%s:00" % code, code + " - x", code, cat,
             "Repiquage", "D-100"))
    conn.commit()
    l = svc.saisies_periode(conn, "Repiquage",
                            "2026-06-08T00:00:00", "2026-06-08T23:59:59")
    codes = sorted(r["code"] for r in l)
    verifier("debut, fin et pointages masques sur Repiquage", codes, ["03", "53"])


# ─── 19. Une, plusieurs ou toutes les machines ───────────────────────────────

def test_plusieurs_machines():
    print("\n19. Une, plusieurs ou toutes les machines")
    conn = base()

    def journee(machine, dossier, metrage):
        for quand, code, cat, cd, cf in [
                ("08:00:00", "01", "personnel", 1000, None),
                ("08:01:00", "03", "production", None, None),
                ("10:01:00", "89", "personnel", None, 1000 + metrage)]:
            conn.execute(
                """INSERT INTO production_data
                   (operateur, date_operation, operation, operation_code,
                    operation_category, machine, no_dossier, client,
                    metrage_total_debut, metrage_total_fin)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                ("Marc", "2026-06-08T" + quand, code + " - x", code, cat,
                 machine, dossier, "Client Test", cd, cf))

    journee("Cohesio 1", "D-C1", 1000)
    journee("Cohesio 2", "D-C2", 2000)
    journee("Repiquage", "D-RP", 4000)
    conn.commit()
    DEB, FIN = "2026-06-08T00:00:00", "2026-06-08T23:59:59"

    verifier("normalisation d'une chaine",
             svc.machines_demandees("Cohesio 1"), ["Cohesio 1"])
    verifier("normalisation d'une liste",
             svc.machines_demandees(["Cohesio 1", "Cohesio 2"]), ["Cohesio 1", "Cohesio 2"])
    verifier("les doublons et les vides tombent",
             svc.machines_demandees(["Cohesio 1", " cohesio 1 ", "", None]), ["Cohesio 1"])
    verifier("rien demande = tout l'atelier", svc.machines_demandees(None), [])

    un = svc.retour_atelier(conn, "Cohesio 1", DEB, FIN)
    verifier_proche("une machine : son metrage", un["production"]["metrage"], 1000)
    verifier("une machine : nommee", un["machine"], "Cohesio 1")
    verifier("une machine : pas 'toutes'", un["toutes_machines"], False)

    deux = svc.retour_atelier(conn, ["Cohesio 1", "Cohesio 2"], DEB, FIN)
    verifier_proche("deux machines : la somme", deux["production"]["metrage"], 3000)
    verifier("deux machines : deux dossiers", deux["dossiers"], 2)
    verifier("deux machines : les deux nommees", deux["machines"], ["Cohesio 1", "Cohesio 2"])
    verifier("deux machines : pas 'toutes'", deux["toutes_machines"], False)

    tout = svc.retour_atelier(conn, [], DEB, FIN)
    verifier_proche("toutes : la somme entiere", tout["production"]["metrage"], 7000)
    verifier("toutes : le drapeau", tout["toutes_machines"], True)

    verifier("la casse et les blancs n'empechent rien",
             svc.retour_atelier(conn, ["  cohesio 2  "], DEB, FIN)["dossiers"], 1)

    # La frise, les comptes-rendus et le deroule suivent le meme perimetre.
    fr = svc.frise(conn, DEB, FIN, ["Cohesio 1", "Repiquage"])
    verifier("frise : deux lignes machine", sorted(l["machine"] for l in fr["lignes"]),
             ["Cohesio 1", "Repiquage"])
    verifier("comptes-rendus : deux dossiers",
             len(svc.comptes_rendus_periode(conn, DEB, FIN, ["Cohesio 1", "Cohesio 2"])), 2)
    verifier("saisies : deux machines",
             sorted({r["machine"] for r in
                     svc.saisies_periode(conn, ["Cohesio 1", "Cohesio 2"], DEB, FIN)}),
             ["Cohesio 1", "Cohesio 2"])


# ─── 20. Postes hors production ──────────────────────────────────────────────

def test_postes_hors_production():
    print("\n20. Postes hors production")
    conn = base()
    verifier("sans table machines, aucun poste", svc.postes_hors_production(conn), [])

    conn.executescript(
        """
        CREATE TABLE machines (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT UNIQUE NOT NULL,
            code TEXT, actif INTEGER DEFAULT 1
        );
        """
    )
    conn.execute("INSERT INTO machines (nom, code) VALUES ('Cohesio 1','C1')")
    conn.execute("INSERT INTO machines (nom, code) VALUES ('Repiquage','REP')")
    conn.commit()
    verifier("sans la colonne, aucun poste", svc.postes_hors_production(conn), [])

    conn.execute("ALTER TABLE machines ADD COLUMN hors_production INTEGER NOT NULL DEFAULT 0")
    conn.commit()
    verifier("colonne vide, aucun poste", svc.postes_hors_production(conn), [])

    conn.execute("UPDATE machines SET hors_production=1 WHERE nom='Repiquage'")
    conn.commit()
    verifier("le poste coche remonte", svc.postes_hors_production(conn), ["Repiquage"])

    # Le service ne decide rien tout seul : demander explicitement le poste
    # continue de le rendre. C'est l'appelant qui resout « toutes ».
    for quand, code, cat, m in [("08:00:00", "01", "personnel", "Repiquage"),
                                ("08:01:00", "03", "production", "Repiquage"),
                                ("10:01:00", "89", "personnel", "Repiquage")]:
        conn.execute(
            """INSERT INTO production_data
               (operateur, date_operation, operation, operation_code,
                operation_category, machine, no_dossier)
               VALUES (?,?,?,?,?,?,?)""",
            ("Marc", "2026-06-08T" + quand, code + " - x", code, cat, m, "D-REP"))
    conn.commit()
    DEB, FIN = "2026-06-08T00:00:00", "2026-06-08T23:59:59"
    verifier("demande explicite : le poste repond",
             svc.retour_atelier(conn, ["Repiquage"], DEB, FIN)["dossiers"], 1)

    # Le selecteur, lui, doit pouvoir le nommer : une machine affichee sur la
    # frise et absente du filtre, c'est un filtre qui ment.
    verifier("le poste figure dans les machines de la periode",
             "Repiquage" in svc.machines_periode(conn, DEB, FIN), True)


if __name__ == "__main__":
    test_temps_par_categorie()
    test_deux_conducteurs_ne_se_chainent_pas()
    test_saisie_annulee_exclue()
    test_saisie_restee_ouverte()
    test_metrage()
    test_mediane()
    test_reperes_reference()
    test_compte_rendu()
    test_cadence_comparable_au_repere()
    test_vigilance()
    test_ras_non_substantiel()
    test_retour_atelier()
    test_machine_sans_donnee()
    test_recherche_tous_dossiers()
    test_suivi_des_remontees()
    test_dernier_jour_saisi()
    test_frise()
    test_frise_debordements()
    test_statut_saisieprod()
    test_frise_dossier()
    test_minutes_txt()
    test_periode_borne_les_chiffres()
    test_fin_de_cycle_ne_dure_pas()
    test_intervalles_bornes()
    test_saisies_periode()
    test_saisies_repiquage()
    test_plusieurs_machines()
    test_postes_hors_production()

    print("\n" + "=" * 60)
    if FAIL:
        print(f"{len(FAIL)} echec(s) :")
        for f in FAIL:
            print("  -", f)
        sys.exit(1)
    print("Tous les cas passent.")
