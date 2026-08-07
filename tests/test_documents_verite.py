"""
Arbitrage des sources et péremption de la validation.

Ce que ces cas verrouillent, dans l'ordre de gravité :

1. Une validation ne survit pas au changement du chiffre qu'elle couvre. C'est
   le défaut qui rendait le verrou de déstockage décoratif : l'OF validé lundi
   sur 18 000 étiquettes déstockait 22 000 le mardi, toujours affiché « validé ».
2. Une valeur saisie à la main n'est pas écrasée par Access, et le désaccord
   est journalisé au lieu d'être ignoré.
3. Une valeur qu'aucun humain n'a touchée l'est, elle — y compris sur un
   document par ailleurs relu. « Le plus récent fait foi » et « le manuel est
   plus sûr » ne se contredisent qu'au niveau du document ; au niveau du champ
   les deux tiennent.

Sans dépendance : le service ne tire ni fastapi ni la base du projet.
"""
import json
import sqlite3
import sys

sys.path.insert(0, ".")

from app.services.documents_verite import (          # noqa: E402
    appliquer_maj, constater_remplacement, marquer_champs_manuels,
    historique_document, valeur_differente,
)

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}")
        print(f"       obtenu  : {obtenu!r}")


def base():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE of_imports(
            id INTEGER PRIMARY KEY, of_numero TEXT, reference TEXT, machine TEXT,
            date_creation TEXT, delai_client TEXT,
            qte_etiquettes INTEGER, metrage REAL, laize REAL, nb_cartons INTEGER,
            pdf_filename TEXT, date_import TEXT, imported_by TEXT, statut TEXT,
            valide INTEGER NOT NULL DEFAULT 0, valide_par TEXT, valide_at TEXT,
            champs_manuels TEXT, invalide_at TEXT, invalide_motif TEXT);
        CREATE TABLE fiches_techniques(
            id INTEGER PRIMARY KEY, reference TEXT, designation TEXT,
            support TEXT, glassine TEXT, nb_etiq_bobin INTEGER, notes TEXT,
            source TEXT, date_import TEXT, imported_by TEXT,
            valide INTEGER NOT NULL DEFAULT 0, valide_par TEXT, valide_at TEXT,
            champs_manuels TEXT, invalide_at TEXT, invalide_motif TEXT);
        CREATE TABLE documents_valeurs_historique(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_nom TEXT NOT NULL, doc_id INTEGER NOT NULL, champ TEXT NOT NULL,
            avant TEXT, apres TEXT, origine TEXT NOT NULL, auteur TEXT,
            at TEXT NOT NULL, etait_valide INTEGER NOT NULL DEFAULT 0,
            refuse INTEGER NOT NULL DEFAULT 0);
    """)
    return conn


def of_valide(conn, **surcharges):
    """Un OF poussé par Access, relu et validé par l'administration."""
    champs = {"of_numero": "9932056", "reference": "1068/0001",
              "qte_etiquettes": 18000, "metrage": 7124.0398, "laize": 470,
              "date_creation": "2026-08-01", "imported_by": "access_bridge",
              "valide": 1, "valide_par": "Nathalie", "valide_at": "2026-08-05T09:00:00"}
    champs.update(surcharges)
    cols = ", ".join(champs)
    conn.execute(
        f"INSERT INTO of_imports ({cols}) VALUES ({', '.join('?' * len(champs))})",
        list(champs.values()))
    conn.commit()
    return conn.execute("SELECT id FROM of_imports ORDER BY id DESC LIMIT 1").fetchone()["id"]


def lire(conn, table, doc_id):
    return conn.execute(f"SELECT * FROM {table} WHERE id=?", (doc_id,)).fetchone()


print("\n1. Access corrige une quantité sous une validation acquise")
conn = base()
oid = of_valide(conn)
r = appliquer_maj(conn, "of_imports", oid, {"qte_etiquettes": 22000},
                  origine="access_bridge")
conn.commit()
row = lire(conn, "of_imports", oid)
check("la valeur est bien écrite", row["qte_etiquettes"], 22000)
check("la validation tombe", row["valide"], 0)
check("le validateur est effacé", row["valide_par"], None)
check("le motif nomme le champ", "quantité d'étiquettes" in (row["invalide_motif"] or ""), True)
check("le motif nomme la source", "Access" in (row["invalide_motif"] or ""), True)
check("l'appelant est prévenu", r["invalide"], True)
h = historique_document(conn, "of_imports", oid)
check("le changement est journalisé", len(h), 1)
check("avec l'avant et l'après", (h[0]["avant"], h[0]["apres"]), ("18000", "22000"))
check("et le fait qu'il portait sur un document validé", h[0]["etait_valide"], 1)

print("\n2. Access ne peut pas écraser une valeur saisie à la main")
conn = base()
oid = of_valide(conn, champs_manuels=json.dumps(["qte_etiquettes"]))
r = appliquer_maj(conn, "of_imports", oid, {"qte_etiquettes": 22000},
                  origine="access_bridge")
conn.commit()
row = lire(conn, "of_imports", oid)
check("la saisie manuelle est conservée", row["qte_etiquettes"], 18000)
check("la validation tient", row["valide"], 1)
check("le conflit est remonté", len(r["conflits"]), 1)
check("avec les deux valeurs", (r["conflits"][0]["actuel"], r["conflits"][0]["propose"]),
      (18000, 22000))
h = historique_document(conn, "of_imports", oid)
check("le refus est journalisé, pas silencieux", (len(h), h[0]["refuse"]), (1, 1))

print("\n3. Un OF relu garde ses champs, mais ses trous restent ouverts")
# Le comportement d'avant gelait l'OF ENTIER dès qu'un PDF existait : une
# quantité corrigée dans Access n'arrivait jamais, et un métrage absent le
# restait. La protection porte désormais sur les colonnes effectivement lues.
conn = base()
oid = of_valide(conn, pdf_filename="9932056_20260801.pdf", imported_by="Nathalie",
                metrage=None, champs_manuels=json.dumps(["qte_etiquettes", "laize"]))
r = appliquer_maj(conn, "of_imports", oid,
                  {"qte_etiquettes": 22000, "metrage": 7124.0398},
                  origine="access_bridge")
conn.commit()
row = lire(conn, "of_imports", oid)
check("le champ protégé par le PDF ne bouge pas", row["qte_etiquettes"], 18000)
check("le champ vide est complété", round(row["metrage"], 4), 7124.0398)
check("compté comme un trou comblé", r["remplis"], ["metrage"])
check("et la validation tombe quand même", row["valide"], 0)

print("\n4. Ce qui ne change pas le calcul ne périme pas la validation")
conn = base()
oid = of_valide(conn)
appliquer_maj(conn, "of_imports", oid, {"delai_client": "2026-09-15"},
              origine="access_bridge")
conn.commit()
row = lire(conn, "of_imports", oid)
check("le délai client est écrit", row["delai_client"], "2026-09-15")
check("la validation tient", row["valide"], 1)

print("\n5. Une valeur identique n'est ni réécrite ni journalisée")
conn = base()
oid = of_valide(conn)
r = appliquer_maj(conn, "of_imports", oid,
                  {"qte_etiquettes": 18000, "metrage": 7124.03980000001},
                  origine="access_bridge")
conn.commit()
check("rien n'est écrit", r["ecrits"], [])
check("la validation tient", lire(conn, "of_imports", oid)["valide"], 1)
check("le journal reste vide", len(historique_document(conn, "of_imports", oid)), 0)
check("tolérance numérique", valeur_differente(7124.0, 7124.0000000001), False)
check("écart réel détecté", valeur_differente(7124.0, 7124.04), True)

print("\n6. enrich_if_exists ne comble que les trous")
conn = base()
oid = of_valide(conn, nb_cartons=None)
r = appliquer_maj(conn, "of_imports", oid,
                  {"qte_etiquettes": 22000, "nb_cartons": 12},
                  origine="access_bridge", seulement_vides=True)
conn.commit()
row = lire(conn, "of_imports", oid)
check("la valeur existante est intacte", row["qte_etiquettes"], 18000)
check("le trou est comblé", row["nb_cartons"], 12)
check("seul le trou est écrit", r["ecrits"], ["nb_cartons"])

print("\n7. Une correction humaine périme aussi, et se protège")
conn = base()
oid = of_valide(conn)
r = appliquer_maj(conn, "of_imports", oid, {"qte_etiquettes": 19500},
                  origine="manuel", auteur="Nathalie",
                  proteger_manuels=False, marquer_manuels=True,
                  autoriser_effacement=True)
conn.commit()
row = lire(conn, "of_imports", oid)
check("la correction passe", row["qte_etiquettes"], 19500)
check("corriger n'est pas relire : la validation tombe", row["valide"], 0)
check("le motif nomme l'auteur", "Nathalie" in (row["invalide_motif"] or ""), True)
check("le champ devient protégé", json.loads(row["champs_manuels"]), ["qte_etiquettes"])
# …et Access ne peut plus le reprendre.
r2 = appliquer_maj(conn, "of_imports", oid, {"qte_etiquettes": 22000},
                   origine="access_bridge")
conn.commit()
check("Access bute dessus au sync suivant",
      lire(conn, "of_imports", oid)["qte_etiquettes"], 19500)
check("et le signale", len(r2["conflits"]), 1)

print("\n8. Une fiche technique corrigée à la main survit au sync Access")
# C'est le cas qui perdait le plus : l'upsert réécrivait TOUS les champs
# fournis, correction atelier de la veille comprise, sans trace.
conn = base()
conn.execute("""INSERT INTO fiches_techniques
    (id, reference, support, glassine, nb_etiq_bobin, valide, valide_par, imported_by)
    VALUES (1, '1068/0001', 'PP blanc 60', 'Glassine 62', 1000, 1, 'Nathalie', 'access_bridge')""")
conn.commit()
appliquer_maj(conn, "fiches_techniques", 1, {"nb_etiq_bobin": 1250},
              origine="manuel", auteur="Atelier", proteger_manuels=False,
              marquer_manuels=True, autoriser_effacement=True)
conn.commit()
r = appliquer_maj(conn, "fiches_techniques", 1,
                  {"nb_etiq_bobin": 1000, "support": "PP blanc 80"},
                  origine="access_bridge")
conn.commit()
row = lire(conn, "fiches_techniques", 1)
check("la correction atelier tient", row["nb_etiq_bobin"], 1250)
check("le reste est bien mis à jour", row["support"], "PP blanc 80")
check("le conflit est visible", [c["champ"] for c in r["conflits"]], ["nb_etiq_bobin"])

print("\n9. Import d'un PDF : remplacement en bloc, conséquences identiques")
conn = base()
oid = of_valide(conn)
avant = dict(lire(conn, "of_imports", oid))
conn.execute("UPDATE of_imports SET qte_etiquettes=?, metrage=?, pdf_filename=? WHERE id=?",
             (21000, 8300.0, "9932056_20260807.pdf", oid))
r = constater_remplacement(conn, "of_imports", oid, avant,
                           origine="import_pdf", auteur="Nathalie")
conn.commit()
row = lire(conn, "of_imports", oid)
check("la validation tombe", row["valide"], 0)
check("le motif nomme l'import PDF", "import d'un PDF" in (row["invalide_motif"] or ""), True)
check("les deux chiffres sont journalisés",
      sorted(c for c in r["changes"] if c in ("qte_etiquettes", "metrage")),
      ["metrage", "qte_etiquettes"])
manuels = json.loads(row["champs_manuels"])
check("ce que le PDF a rempli devient protégé",
      all(c in manuels for c in ("qte_etiquettes", "metrage", "laize")), True)

print("\n10. Robustesse")
conn = base()
oid = of_valide(conn, champs_manuels="{ceci n'est pas du json")
r = appliquer_maj(conn, "of_imports", oid, {"qte_etiquettes": 22000},
                  origine="access_bridge")
conn.commit()
check("un champs_manuels illisible ne bloque pas l'import", r["ecrits"], ["qte_etiquettes"])
r = appliquer_maj(conn, "of_imports", oid,
                  {"valide": 1, "id": 99, "colonne_inconnue": "x"},
                  origine="access_bridge")
conn.commit()
check("on ne valide pas un document en le mettant à jour",
      lire(conn, "of_imports", oid)["valide"], 0)
check("les colonnes de service sont ignorées", r["ecrits"], [])
marquer_champs_manuels(conn, "of_imports", oid, ["laize"])
conn.commit()
check("marquage additif", "laize" in json.loads(lire(conn, "of_imports", oid)["champs_manuels"]), True)

print()
if ko:
    print(f"ÉCHEC — {ko} vérification(s) en erreur.")
    sys.exit(1)
print("Tous les cas passent.")
