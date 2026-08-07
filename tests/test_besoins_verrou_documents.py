"""
Le verrou documentaire du déstockage, sur la vraie SQL.

Deux choses se vérifient ici et nulle part ailleurs :

1. Les requêtes `_SQL_PE` et `_SQL_FT` de Besoins matières tournent réellement
   sur le schéma migré. Elles nomment des colonnes ajoutées par migration
   (`valide`, `invalide_motif`) : une faute de frappe ne se voit pas à la
   lecture, elle sort en 500 sur les trois écrans d'un coup.

2. `_etat_documents` bloque bien, et raconte pourquoi. Un dossier dont la
   validation est TOMBÉE ne se lit pas comme un dossier jamais relu : dans le
   premier cas un chiffre a bougé sous une relecture acquise, et c'est
   l'information qui décide quoi rouvrir en premier.

Le code testé est extrait du router par découpage de source : le module entier
tirerait fastapi et toute la base du projet pour trois fonctions pures.
"""
import re
import sqlite3
import sys
from typing import Optional

sys.path.insert(0, ".")

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


# ── Extraction du code à tester ───────────────────────────────────────
src = open("app/routers/besoins_matieres.py", encoding="utf-8").read()
bloc_sql = src[src.index('_SQL_PE = """'):src.index("def _load_mapping(")]
bloc_etat = src[src.index("def _etat_documents("):src.index("def _destockage_lignes(")]
ns = {"re": re, "Optional": Optional}
exec(compile(bloc_sql + "\n" + bloc_etat, "besoins_bloc", "exec"), ns)
SQL_PE, SQL_PE_UN = ns["_SQL_PE"], ns["_SQL_PE_UN"]
load_dossiers, etat_documents = ns["_load_dossiers"], ns["_etat_documents"]

# ── Base minimale, puis migration réelle ──────────────────────────────
import importlib.util                                              # noqa: E402
spec = importlib.util.spec_from_file_location(
    "mig_dsv", "app/core/migrations/2026_08_07_documents_source_verite.py")
mig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mig)

conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.executescript("""
    CREATE TABLE machines(id INTEGER PRIMARY KEY, nom TEXT,
        sans_matiere_premiere INTEGER DEFAULT 0);
    CREATE TABLE planning_entries(
        id INTEGER PRIMARY KEY, machine_id INTEGER, reference TEXT, client TEXT,
        description TEXT, ref_produit TEXT, ref_produit_norm TEXT, numero_of TEXT,
        statut TEXT, planned_start TEXT, planned_end TEXT, date_livraison TEXT,
        duree_heures REAL, position INTEGER, of_import_id INTEGER,
        destockage TEXT DEFAULT 'todo');
    CREATE TABLE of_imports(
        id INTEGER PRIMARY KEY, of_numero TEXT, reference TEXT, machine TEXT,
        laize REAL, format TEXT, matiere TEXT, glassine TEXT, conditionnement TEXT,
        qte_etiquettes INTEGER, qte_bobines REAL, metrage REAL,
        nb_mandrins INTEGER, nb_cartons INTEGER, nb_tubes INTEGER,
        mandrins_dia TEXT, mandrin_longueur REAL, cartons_type TEXT,
        adhesif_label TEXT, ref_adhesif TEXT, qte_adhesif_g REAL, qte_adhesif_kg REAL,
        qte_au_mille REAL, date_creation TEXT, delai_client TEXT,
        pdf_filename TEXT, date_import TEXT, imported_by TEXT, statut TEXT,
        valide INTEGER NOT NULL DEFAULT 0, valide_par TEXT, valide_at TEXT);
    CREATE TABLE fiches_techniques(
        id INTEGER PRIMARY KEY, reference TEXT, ref_produit_norm TEXT, machine TEXT,
        support TEXT, matiere TEXT, glassine TEXT, adhesif TEXT, qte_au_mille REAL,
        eti_laize REAL, eti_longueur REAL, mod_laize REAL, mod_longueur REAL,
        mod_nb_front INTEGER, outil1_nb_front INTEGER,
        laize REAL, laize_optimale REAL, mandrin_dia TEXT,
        nb_etiq_bobin INTEGER, nb_bobines_carton INTEGER, cartons TEXT,
        conditionnement TEXT, palette_type TEXT, palette_nb_cartons_sol INTEGER,
        palette_nb_cartons_hauteur INTEGER, source TEXT, date_import TEXT,
        valide INTEGER NOT NULL DEFAULT 0, valide_par TEXT, valide_at TEXT);
    CREATE TABLE mp_mouvements(
        id INTEGER PRIMARY KEY, matiere_id INTEGER, type_mouvement TEXT,
        quantite REAL, planning_entry_id INTEGER, no_dossier TEXT,
        annule_mouvement_id INTEGER);
""")
conn.commit()

print("\n0. La migration s'applique sur un schéma déjà en place")
mig.appliquer(conn)
cols_of = {r["name"] for r in conn.execute("PRAGMA table_info(of_imports)")}
cols_ft = {r["name"] for r in conn.execute("PRAGMA table_info(fiches_techniques)")}
cols_mv = {r["name"] for r in conn.execute("PRAGMA table_info(mp_mouvements)")}
check("colonnes ajoutées sur of_imports",
      {"champs_manuels", "invalide_at", "invalide_motif"} <= cols_of, True)
check("colonnes ajoutées sur fiches_techniques",
      {"champs_manuels", "invalide_at", "invalide_motif", "imported_by"} <= cols_ft, True)
check("mouvement rattachable à ses documents",
      {"of_import_id", "fiche_id"} <= cols_mv, True)
mig.appliquer(conn)  # rejouable
check("rejouable sans casse", True, True)

# ── Jeu de données ────────────────────────────────────────────────────
conn.executescript("""
    INSERT INTO machines(id, nom) VALUES (1, 'Cohésio 1');
    INSERT INTO of_imports(id, of_numero, qte_etiquettes, metrage, laize, valide, valide_par)
      VALUES (10, '9932056', 18000, 7124.04, 470, 1, 'Nathalie'),
             (11, '9932057', 12000, 5000.0, 470, 0, NULL),
             (12, '9932058', 9000, 3000.0, 470, 0, NULL);
    UPDATE of_imports SET invalide_motif =
      'Validation retirée : quantité d''étiquettes modifiée par Access.'
      WHERE id = 12;
    -- outil1_nb_front est le vrai nombre de fronts : mod_nb_front vaut 1 sur
    -- 878 fiches sur 909 en production. Le métrage se calcule sur le premier.
    INSERT INTO fiches_techniques(id, reference, ref_produit_norm, valide, valide_par,
                                  mod_nb_front, outil1_nb_front, mod_laize,
                                  mod_longueur, laize_optimale)
      VALUES (20, '1068/0001', '1068/0001', 1, 'Nathalie', 1, 8, 57.5, 152.4, 470),
             (21, '1068/0002', '1068/0002', 0, NULL,       1, 8, 57.5, 152.4, 470);
    INSERT INTO planning_entries(id, machine_id, reference, ref_produit,
        ref_produit_norm, numero_of, statut, of_import_id, position)
      VALUES (1, 1, 'D-1', '1068/0001', '1068/0001', '9932056', 'en_cours', 10, 0),
             (2, 1, 'D-2', '1068/0002', '1068/0002', '9932057', 'attente', 11, 1),
             (3, 1, 'D-3', '1068/0001', '1068/0001', '9932058', 'attente', 12, 2),
             (4, 1, 'D-4', '9999/0000', '9999/0000', '9932059', 'attente', NULL, 3);
""")
conn.commit()

print("\n1. Les requêtes de Besoins matières tournent sur le schéma migré")
dossiers = load_dossiers(conn)
check("les 4 dossiers du planning remontent", len(dossiers), 4)
par_id = {d["id"]: d for d in dossiers}
check("l'OF validé est vu comme validé", par_id[1]["of_valide"], 1)
check("la fiche est rapprochée", par_id[1]["ft_id"], 20)
check("le motif d'invalidation remonte jusqu'au dossier",
      "quantité d'étiquettes" in (par_id[3]["of_invalide_motif"] or ""), True)
check("le nombre de fronts de l'outil est remonté, pas celui du module",
      (par_id[1]["ft_outil1_nb_front"], par_id[1]["ft_mod_nb_front"]), (8, 1))
un = load_dossiers(conn, SQL_PE_UN, (1,))
check("la variante mono-dossier tourne aussi", (len(un), un[0]["id"]), (1, 1))

print("\n2. Le verrou ne laisse passer que les deux documents validés")
e1 = etat_documents(par_id[1])
check("dossier complet : déstockage ouvert", (e1["complet"], e1["blocage"]), (True, None))

e2 = etat_documents(par_id[2])
check("fiche non validée : bloqué", e2["complet"], False)
check("le blocage nomme les deux manques",
      ("OF non validé" in e2["blocage"] and "fiche technique non validée" in e2["blocage"]),
      True)

e4 = etat_documents(par_id[4])
check("aucun OF rattaché : bloqué", e4["complet"], False)
check("et le blocage le dit", "aucun OF rattaché" in e4["blocage"], True)

print("\n3. Une validation tombée ne se raconte pas comme une absence de relecture")
e3 = etat_documents(par_id[3])
check("bloqué", e3["complet"], False)
check("le motif est repris dans le blocage",
      "modifiée par Access" in e3["blocage"], True)
check("et remonté à part pour l'interface", len(e3["motifs_invalidation"]), 1)
check("un dossier jamais relu n'invente pas de motif", e2["motifs_invalidation"], [])

print()
if ko:
    print(f"ÉCHEC — {ko} vérification(s) en erreur.")
    sys.exit(1)
print("Tous les cas passent.")
