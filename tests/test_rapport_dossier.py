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
            metrage_prevu REAL, metrage_reel REAL
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
           est_annule=0, annule_motif=None):
    conn.execute(
        """INSERT INTO production_data
           (operateur, date_operation, operation, operation_code, operation_category,
            machine, no_dossier, client, designation, commentaire, est_annule,
            annule_motif, metrage_prevu, metrage_reel)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (operateur, (T0 + timedelta(minutes=minutes_apres)).strftime("%Y-%m-%dT%H:%M:%S"),
         operation or code, code, categorie, machine, no_dossier,
         "Client Test", "Etiquette 100x50", commentaire, est_annule,
         annule_motif, metrage_prevu, metrage_reel),
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
    print("\n5. Metrage : le compteur machine n'est pas un metrage")
    conn = base()
    saisies_deux = [
        {"operation_code": "89", "metrage_reel": 91_994_681},
        {"operation_code": "89", "metrage_reel": 92_006_681},
    ]
    m = svc.metrage_dossier(saisies_deux, "89")
    verifier("deux releves : ecart de compteur", m["reel"], 12000.0)
    verifier("fiable", m["fiable"], True)

    m1 = svc.metrage_dossier([{"operation_code": "89", "metrage_reel": 12000}], "89")
    verifier("un seul releve plausible : retenu", m1["reel"], 12000.0)

    m2 = svc.metrage_dossier([{"operation_code": "89", "metrage_reel": 91_994_681}], "89")
    verifier("un seul releve au-dela du seuil : ecarte", m2["reel"], 0.0)
    verifier("et signale non fiable", m2["fiable"], False)

    verifier("aucun releve", svc.metrage_dossier([], "89")["reel"], 0.0)


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
    saisie(conn, 0, "02", "calage")
    saisie(conn, 30, "03", "production")
    saisie(conn, 90, "53", "arret", operation="Casse bande",
           commentaire="Bobine mal enroulee, changee")
    saisie(conn, 120, "03", "production")
    saisie(conn, 180, "89", "personnel", metrage_reel=20000, metrage_prevu=25000)
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
    verifier("ecart au prevu", round(cr["metrage"]["ecart_pct"], 1), -20.0)
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


def test_minutes_txt():
    print("\n13. Format des durees")
    verifier("moins d'une heure", svc._minutes_txt(45), "45 min")
    verifier("heure pleine", svc._minutes_txt(120), "2 h")
    verifier("heure et minutes", svc._minutes_txt(95), "1 h 35")
    verifier("inconnu", svc._minutes_txt(None), "—")


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
    test_minutes_txt()

    print("\n" + "=" * 60)
    if FAIL:
        print(f"{len(FAIL)} echec(s) :")
        for f in FAIL:
            print("  -", f)
        sys.exit(1)
    print("Tous les cas passent.")
