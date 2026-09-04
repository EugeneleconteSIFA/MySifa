"""
Pilotage des expeditions : ce que le tableau de bord doit dire, et quand.

Le besoin, formule par SIFA le 04/09/2026 : on attend que la production soit
terminee pour reserver un transport, donc l'affretement se fait dans l'urgence.
Le tableau doit repondre en amont a trois questions par envoi — transport
commande, parti, bon de livraison fait — et surtout dire ce qu'il faut
commander AUJOURD'HUI.

Ces cas verrouillent les decisions prises :

- une ligne = un ENVOI (client + destination + date), pas un dossier : c'est
  ce qu'on commande a un transporteur, et c'est ce qui permet d'additionner
  les palettes du camion ;
- la date qui pilote est celle de RVGI (`cde_ligne.amje`, date d'expedition
  demandee), avec repli sur le planning puis sur la fin de production ;
- le nombre de palettes est ESTIME depuis la fiche technique, jamais invente :
  une fiche incomplete donne « partiel » et la raison, pas un chiffre faux ;
- au-dela du seuil de palettes, l'envoi est un affretement et son preavis de
  reservation est plus long ;
- l'horizon masque ce qui est LOIN, jamais ce qui est en retard ;
- le miroir RVGI absent ne fait pas tomber l'ecran.

Lancer : python3 tests/test_expe_pilotage.py
"""

import sqlite3
import sys
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from app.services import expe_pilotage as pil  # noqa: E402

MIG = RACINE / "app" / "core" / "migrations" / "2026_09_04_expe_pilotage.py"

FAIL = []


def verifier(cas, obtenu, attendu):
    if obtenu != attendu:
        FAIL.append(f"{cas} : obtenu {obtenu!r}, attendu {attendu!r}")
        print(f"  ECHEC  {cas} — obtenu {obtenu!r}, attendu {attendu!r}")
    else:
        print(f"  ok     {cas}")


SCHEMA = """
CREATE TABLE machines (id INTEGER PRIMARY KEY, nom TEXT, code TEXT);
CREATE TABLE of_imports (id INTEGER PRIMARY KEY, qte_bobines REAL, qte_etiquettes REAL);
CREATE TABLE fiches_techniques (
    id INTEGER PRIMARY KEY, reference TEXT, ref_produit_norm TEXT, machine TEXT,
    nb_bobines_carton INTEGER, palette_nb_cartons_sol INTEGER,
    palette_nb_cartons_hauteur INTEGER, palette_type TEXT, cartons TEXT);
CREATE TABLE planning_entries (
    id INTEGER PRIMARY KEY, machine_id INTEGER, position INTEGER, reference TEXT,
    client TEXT, description TEXT, ref_produit TEXT, ref_produit_norm TEXT,
    numero_of TEXT, statut TEXT, statut_reel TEXT, date_livraison TEXT,
    date_livraison_imposee INTEGER, planned_end TEXT, departement_livraison TEXT,
    prise_rdv INTEGER, fsc_requis INTEGER, fsc_type_requis TEXT,
    annule_count INTEGER, of_import_id INTEGER, updated_at TEXT);
CREATE TABLE expe_departs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, date_enlevement TEXT NOT NULL,
    transporteur TEXT, transporteur_id INTEGER, client TEXT,
    code_postal_destination TEXT, arc TEXT, no_cde_transport TEXT, no_bl TEXT,
    nb_palette REAL, poids_total_kg REAL, statut TEXT NOT NULL,
    created_at TEXT, created_by_email TEXT, validated_at TEXT,
    planning_entry_id INTEGER);
CREATE TABLE expe_depart_dossiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT, depart_id INTEGER NOT NULL,
    planning_entry_id INTEGER NOT NULL, no_dossier TEXT, created_at TEXT,
    created_by TEXT, UNIQUE(depart_id, planning_entry_id));
"""


def _appliquer_migration(conn):
    import importlib.util
    spec = importlib.util.spec_from_file_location("mig_pil", MIG)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.appliquer(conn)


def base():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _appliquer_migration(conn)
    conn.execute("INSERT INTO machines (id, nom, code) VALUES (1, 'Cohesio 1', 'C1')")
    # Fiche complete : 12 bobines/carton, 6 x 6 cartons par palette.
    conn.execute(
        """INSERT INTO fiches_techniques
             (id, reference, ref_produit_norm, machine, nb_bobines_carton,
              palette_nb_cartons_sol, palette_nb_cartons_hauteur, palette_type, cartons)
           VALUES (1, '100/0001', '100/0001', 'Cohesio 1', 12, 6, 6, 'Europe',
                   'Carton 385 x 385 x 208 mm')"""
    )
    conn.commit()
    return conn


def dossier(conn, eid, ref, client, refprod="100/0001", statut="attente",
            date_livraison="", planned_end="2026-09-08T12:00:00", dept="",
            bobines=None):
    of_id = None
    if bobines is not None:
        of_id = 1000 + eid
        conn.execute("INSERT INTO of_imports (id, qte_bobines) VALUES (?,?)",
                     (of_id, bobines))
    conn.execute(
        """INSERT INTO planning_entries
             (id, machine_id, position, reference, client, ref_produit,
              ref_produit_norm, numero_of, statut, statut_reel, date_livraison,
              date_livraison_imposee, planned_end, departement_livraison,
              prise_rdv, fsc_requis, annule_count, of_import_id, updated_at)
           VALUES (?,1,?,?,?,?,?,?,?,?,?,0,?,?,0,0,0,?, '2026-09-04T08:00:00')""",
        (eid, eid, ref, client, refprod, refprod, ref, statut,
         "reellement_termine" if statut == "termine" else "reellement_en_attente",
         date_livraison, planned_end, dept, of_id),
    )
    conn.commit()


def sans_rvgi(_numeros):
    return {}


def avec_rvgi(table):
    def _f(numeros):
        return {n: table[n] for n in numeros if n in table}
    return _f


def fiche_rvgi(amje, cp="59200", ville="TOURCOING", bls=None):
    return {"amje": amje, "amjl": None, "lrs": "DESTINATAIRE", "lcp": cp,
            "lville": ville, "lpays": "FRANCE", "client": "CLIENT RVGI",
            "lignes_ouvertes": 1, "bls": bls or []}


JOUR = date(2026, 9, 4)


def tableau(conn, aujourdhui=JOUR):
    return pil.construire_tableau(conn, aujourdhui=aujourdhui)


# ── 1. Une ligne = un envoi ─────────────────────────────────────────────────
print("\n1. Regroupement — deux dossiers du meme camion font une seule ligne")

conn = base()
pil.infos_rvgi = avec_rvgi({"9932001": fiche_rvgi("2026-09-10")})
dossier(conn, 1, "9932001", "EUROFINS", bobines=760)
dossier(conn, 2, "9932001", "EUROFINS", bobines=760)
t = tableau(conn)
verifier("un seul envoi", len(t["envois"]), 1)
verifier("deux dossiers dedans", len(t["envois"][0]["dossiers"]), 2)
# 760 bobines / 12 = 64 cartons ; 64 / 36 = 2 palettes. Deux fois.
verifier("les palettes s'additionnent", t["envois"][0]["nb_palette"], 4)
verifier("chiffre annonce comme estime", t["envois"][0]["nb_palette_source"], "estime")

print("\n   Deux destinations differentes ne se regroupent pas")
conn = base()
pil.infos_rvgi = avec_rvgi({"9932001": fiche_rvgi("2026-09-10", cp="59200"),
                            "9932002": fiche_rvgi("2026-09-10", cp="75001")})
dossier(conn, 1, "9932001", "EUROFINS", bobines=760)
dossier(conn, 2, "9932002", "EUROFINS", bobines=760)
verifier("deux envois", len(tableau(conn)["envois"]), 2)


# ── 2. La date qui pilote ───────────────────────────────────────────────────
print("\n2. Date d'expedition visee — RVGI, puis planning, puis fin de prod")

conn = base()
pil.infos_rvgi = avec_rvgi({"9932001": fiche_rvgi("2026-09-10")})
dossier(conn, 1, "9932001", "EUROFINS", date_livraison="2026-09-30", bobines=760)
e = tableau(conn)["envois"][0]
verifier("RVGI prime sur le planning", e["date_cible"], "2026-09-10")
verifier("et la source est nommee", e["date_cible_source"], "rvgi")

conn = base()
pil.infos_rvgi = sans_rvgi
dossier(conn, 1, "9932001", "EUROFINS", date_livraison="2026-09-12", bobines=760)
e = tableau(conn)["envois"][0]
verifier("sans RVGI, le planning prend le relais", e["date_cible"], "2026-09-12")
verifier("source planning", e["date_cible_source"], "planning")

conn = base()
pil.infos_rvgi = sans_rvgi
dossier(conn, 1, "9932001", "EUROFINS", date_livraison="",
        planned_end="2026-09-15T10:00:00", bobines=760)
e = tableau(conn)["envois"][0]
verifier("sans date, la fin de prod fait foi", e["date_cible"], "2026-09-15")
verifier("source fin de prod", e["date_cible_source"], "fin_prod")


# ── 3. Palettes : estimees, jamais inventees ────────────────────────────────
print("\n3. Palettes — l'estimation dit aussi ce qui lui manque")

conn = base()
pil.infos_rvgi = avec_rvgi({"9932001": fiche_rvgi("2026-09-10")})
dossier(conn, 1, "9932001", "EUROFINS", bobines=760)
dossier(conn, 2, "9932001", "EUROFINS", refprod="999/9999", bobines=100)
e = tableau(conn)["envois"][0]
verifier("l'envoi garde le chiffre connu", e["nb_palette"], 2)
verifier("mais se declare partiel", e["nb_palette_estime_partiel"], True)
verifier("et nomme ce qui manque", "Bobines par carton (fiche technique)" in e["manques"], True)

conn = base()
pil.infos_rvgi = avec_rvgi({"9932001": fiche_rvgi("2026-09-10")})
dossier(conn, 1, "9932001", "EUROFINS", refprod="999/9999")
e = tableau(conn)["envois"][0]
verifier("aucune donnee : pas de chiffre invente", e["nb_palette"], None)
verifier("et aucune source annoncee", e["nb_palette_source"], None)


# ── 4. Preavis : quand la ligne passe en « a commander » ────────────────────
print("\n4. Preavis — messagerie a J-2, affretement a J-5")

conn = base()
pil.infos_rvgi = avec_rvgi({"9932001": fiche_rvgi("2026-09-10")})
dossier(conn, 1, "9932001", "EUROFINS", bobines=760)   # 2 palettes -> messagerie
e = tableau(conn)["envois"][0]
verifier("messagerie sous le seuil", e["type_envoi"], "messagerie")
verifier("preavis de 2 jours", e["preavis_jours"], 2)
verifier("a commander le 08", e["a_commander_le"], "2026-09-08")
verifier("le 4, rien ne presse encore", e["alerte"], "a_venir")
verifier("le 8, il faut commander", tableau(conn, date(2026, 9, 8))["envois"][0]["alerte"],
         "a_commander")
verifier("le 9, c'est urgent", tableau(conn, date(2026, 9, 9))["envois"][0]["alerte"],
         "urgent")
verifier("le 11, c'est du retard", tableau(conn, date(2026, 9, 11))["envois"][0]["alerte"],
         "retard")

conn = base()
pil.infos_rvgi = avec_rvgi({"9932001": fiche_rvgi("2026-09-10")})
for i in range(1, 5):                                   # 4 x 2 = 8 palettes
    dossier(conn, i, "9932001", "EUROFINS", bobines=760)
e = tableau(conn)["envois"][0]
verifier("au-dela du seuil, c'est de l'affretement", e["type_envoi"], "affretement")
verifier("preavis de 5 jours", e["preavis_jours"], 5)
verifier("donc a commander des le 5", e["a_commander_le"], "2026-09-05")


# ── 5. Les trois jalons ─────────────────────────────────────────────────────
print("\n5. Jalons — transport, depart, bon de livraison")

conn = base()
pil.infos_rvgi = avec_rvgi({"9932001": fiche_rvgi("2026-09-10")})
dossier(conn, 1, "9932001", "EUROFINS", bobines=760)
e = tableau(conn)["envois"][0]
verifier("rien de commande au depart", e["jalons"]["transport"]["fait"], False)
verifier("pas de BL non plus", e["jalons"]["bl"]["fait"], False)

conn.execute(
    """INSERT INTO expe_departs
         (id, date_enlevement, transporteur, no_cde_transport, statut, created_at,
          transport_commande_le, planning_entry_id, cle_envoi)
       VALUES (7, '2026-09-10', 'COUPE', 'CDE-42', 'en_attente',
               '2026-09-04T09:00:00', '2026-09-04T09:00:00', 1, 'x')"""
)
conn.commit()
e = tableau(conn)["envois"][0]
verifier("transport commande", e["jalons"]["transport"]["fait"], True)
verifier("le transporteur est nomme", e["jalons"]["transport"]["transporteur"], "COUPE")
verifier("l'alerte retombe", e["alerte"], "commande")

conn.execute("UPDATE expe_departs SET parti_le='2026-09-10' WHERE id=7")
conn.commit()
e = tableau(conn)["envois"][0]
verifier("parti", e["jalons"]["parti"]["fait"], True)
verifier("l'alerte le dit", e["alerte"], "parti")

print("\n   Le BL se lit dans RVGI, il ne se saisit pas ici")
conn = base()
pil.infos_rvgi = avec_rvgi({
    "9932001": fiche_rvgi("2026-09-10", bls=[{"numero": "9938800", "date": "2026-09-09",
                                              "pal": 3, "pds": 900.0, "col": 30}])})
dossier(conn, 1, "9932001", "EUROFINS", bobines=760)
e = tableau(conn)["envois"][0]
verifier("le BL remonte", e["jalons"]["bl"]["numeros"], ["9938800"])
verifier("et ses palettes priment sur l'estimation", e["nb_palette"], 3.0)
verifier("la source est nommee", e["nb_palette_source"], "bl")


# ── 6. Un depart valide sort du tableau ─────────────────────────────────────
print("\n6. Ce qui est parti et historise ne revient pas")

conn = base()
pil.infos_rvgi = avec_rvgi({"9932001": fiche_rvgi("2026-09-10")})
dossier(conn, 1, "9932001", "EUROFINS", bobines=760)
conn.execute(
    """INSERT INTO expe_departs (id, date_enlevement, statut, created_at, planning_entry_id)
       VALUES (9, '2026-09-02', 'valide', '2026-09-02T09:00:00', 1)"""
)
conn.commit()
verifier("plus rien a piloter", len(tableau(conn)["envois"]), 0)


# ── 7. Horizon : masquer le lointain, jamais le retard ──────────────────────
print("\n7. Horizon — il borne le lointain, pas le retard")

conn = base()
pil.infos_rvgi = avec_rvgi({"9932001": fiche_rvgi("2026-12-20"),
                            "9932002": fiche_rvgi("2026-08-01", cp="75001")})
dossier(conn, 1, "9932001", "EUROFINS", bobines=760)
dossier(conn, 2, "9932002", "AUTRE", bobines=760)
envois = tableau(conn)["envois"]
verifier("le lointain est masque", [e["client"] for e in envois], ["AUTRE"])
verifier("et c'est bien le retard qui reste", envois[0]["alerte"], "retard")


# ── 8. Fin de prod apres la date d'expedition ───────────────────────────────
print("\n8. Le tableau signale une production qui finit trop tard")

conn = base()
pil.infos_rvgi = avec_rvgi({"9932001": fiche_rvgi("2026-09-10")})
dossier(conn, 1, "9932001", "EUROFINS", planned_end="2026-09-14T10:00:00", bobines=760)
e = tableau(conn)["envois"][0]
verifier("le probleme est signale", e["prod_apres_expedition"], True)
verifier("la production n'est pas prete", e["prod_prete"], False)


# ── 9. Miroir RVGI absent ───────────────────────────────────────────────────
print("\n9. Sans miroir RVGI, l'ecran reste juste — il le dit, il ne tombe pas")

conn = base()
pil.infos_rvgi = sans_rvgi
dossier(conn, 1, "9932001", "EUROFINS", date_livraison="2026-09-12", bobines=760)
t = tableau(conn)
verifier("le tableau existe", len(t["envois"]), 1)
verifier("et signale le miroir absent", t["rvgi"]["present"], False)
verifier("les palettes restent estimees", t["envois"][0]["nb_palette"], 2)


# ── 10. Reglages ────────────────────────────────────────────────────────────
print("\n10. Reglages — defauts, bornes, et refus des valeurs absurdes")

conn = base()
p = pil.charger_params(conn)
verifier("horizon par defaut", p["horizon_jours"], 21.0)
pil.enregistrer_params(conn, {"preavis_messagerie_jours": 4})
verifier("le reglage est relu", pil.charger_params(conn)["preavis_messagerie_jours"], 4.0)
try:
    pil.enregistrer_params(conn, {"horizon_jours": 5000})
    verifier("une valeur hors bornes est refusee", "acceptee", "refusee")
except ValueError:
    verifier("une valeur hors bornes est refusee", "refusee", "refusee")

print()
if FAIL:
    print(f"ECHEC : {len(FAIL)} cas")
    for f in FAIL:
        print("  -", f)
    sys.exit(1)
print("Pilotage des expeditions : tous les cas passent.")
