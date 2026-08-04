"""
Le lanceur de migrations en fichiers : application, idempotence, reprise.

Lancer : python3 tests/test_migrations_fichiers.py
(le script pilote un démarrage complet de la base, il ne passe pas par unittest)
"""

import os, sys, tempfile, io, contextlib, sqlite3
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))
os.chdir(RACINE)

FAIL = []
def check(label, got, expected):
    ok = got == expected
    print(("ok   " if ok else "KO   ") + label.ljust(58) + f"{got}" + ("" if ok else f"   attendu {expected}"))
    if not ok: FAIL.append(label)

db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["DB_PATH"] = db
import config; config.DB_PATH = db
import app.core.database as dbmod; dbmod.DB_PATH = db
with contextlib.redirect_stdout(io.StringIO()):
    dbmod.init_db()

# Le dossier grossit à chaque chantier : on compte les fichiers plutôt que de
# figer un nombre, sinon ce test tombe dès qu'un collègue ajoute une migration.
FICHIERS = sorted(m for m in os.listdir("app/core/migrations")
                  if m.endswith(".py") and not m.startswith("__"))

print("--- premier demarrage ---")
with dbmod.get_db() as conn:
    faites = {r[0] for r in conn.execute("SELECT nom FROM schema_migrations_fichiers")}
    for nom in ("mc_fournisseurs_annuaire_entreprise", "mp_matiere_prix_par_fournisseur",
                "mp_declinaisons_appairage", "imprimantes_type_connexion_windows_local"):
        check(f"{nom[:44]} appliquee", nom in faites, True)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    check("table mp_matiere_declinaison creee", "mp_matiere_declinaison" in tables, True)
    check("table mp_grammages creee", "mp_grammages" in tables, True)
    check("table de suivi creee", "schema_migrations_fichiers" in tables, True)
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(imprimantes)").fetchall()}
    check("colonne type_connexion enfin ajoutee", "type_connexion" in cols, True)
    check("colonne nom_queue_windows ajoutee", "nom_queue_windows" in cols, True)
    check("toutes les migrations du dossier sont enregistrees",
          conn.execute("SELECT COUNT(*) FROM schema_migrations_fichiers").fetchone()[0],
          len(FICHIERS))

print("\n--- second demarrage : rien ne doit se rejouer ---")
buf2 = io.StringIO()
with dbmod.get_db() as conn:
    with contextlib.redirect_stdout(buf2):
        dbmod._migrate(conn)
check("aucune migration rejouee", "appliquée" in buf2.getvalue(), False)

print("\n--- base ou une migration est deja passee par l'ancien mecanisme ---")
db2 = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
conn2 = sqlite3.connect(db2)
conn2.row_factory = sqlite3.Row
conn2.execute("""CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY,
                 name TEXT NOT NULL, applied_at TEXT NOT NULL)""")
for _ddl in (
    "CREATE TABLE matieres_premieres (id INTEGER PRIMARY KEY, categorie TEXT, prix_eur_m2 REAL, prix_par_laize INTEGER, mc_material_id INTEGER)",
    "CREATE TABLE mp_valorisation (matiere_id INTEGER, prix_unitaire REAL)",
    "CREATE TABLE mp_matiere_laizes (matiere_id INTEGER, laize_id INTEGER, prix_eur_m2 REAL)",
    "CREATE TABLE matiere_laize_fournisseurs (matiere_id INTEGER, laize_id INTEGER, fournisseur_id INTEGER)",
    "CREATE TABLE mp_laizes (id INTEGER PRIMARY KEY, valeur_mm REAL, label TEXT, ordre INTEGER, actif INTEGER)",
    "CREATE TABLE mc_material (id INTEGER PRIMARY KEY, name TEXT, appellation_code TEXT,"
    " supplier_id INTEGER, category_id INTEGER, is_active INTEGER, weight_per_m2 REAL,"
    " weight_gsm INTEGER, price_currency TEXT, price_basis TEXT, tax_incidence REAL,"
    " is_imported INTEGER)",
    "CREATE TABLE mc_supplier (id INTEGER PRIMARY KEY, name TEXT)",
    "CREATE TABLE fournisseurs_fsc (id INTEGER PRIMARY KEY, nom TEXT)",
    "CREATE TABLE imprimantes (id INTEGER PRIMARY KEY)",
    # La base pretend avoir deja joue mp_declinaisons_appairage : ses tables
    # doivent donc exister, sinon la simulation est incoherente.
    "CREATE TABLE mp_matiere_declinaison (id INTEGER PRIMARY KEY, matiere_id INTEGER,"
    " laize_id INTEGER, grammage_id INTEGER, mc_material_id INTEGER)",
    "CREATE TABLE mp_grammages (id INTEGER PRIMARY KEY, valeur_gsm REAL)",
): conn2.execute(_ddl)
conn2.execute("INSERT INTO schema_migrations VALUES (228,'mp_declinaisons_appairage','2026-01-01')")
conn2.commit()
from app.core.migrations import appliquer_migrations
faites = appliquer_migrations(conn2)
check("migration deja passee sous son ancien numero -> ignoree",
      "mp_declinaisons_appairage" in faites, False)
check("les autres restent a appliquer", len(faites), len(FICHIERS) - 1)
conn2.close(); os.unlink(db2)

print("\n--- garde-fous du lanceur ---")
import app.core.migrations as M
mods = FICHIERS
noms = []
for f in mods:
    ns = {}
    exec(compile(open("app/core/migrations/" + f, encoding="utf-8").read(), f, "exec"), ns)
    noms.append(ns["NOM"])
check("tous les fichiers portent un NOM", len(noms), len(mods))
check("aucun nom en double", len(set(noms)), len(noms))
check("ordre d'execution = ordre des noms de fichiers", mods, sorted(mods))
# DEPEND : les declinaisons attendent la table des prix
db3 = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
c3 = sqlite3.connect(db3); c3.row_factory = sqlite3.Row
c3.execute("CREATE TABLE matieres_premieres (id INTEGER PRIMARY KEY, categorie TEXT, prix_eur_m2 REAL, prix_par_laize INTEGER, mc_material_id INTEGER)")
c3.execute("CREATE TABLE mp_valorisation (matiere_id INTEGER, prix_unitaire REAL)")
c3.execute("CREATE TABLE mp_matiere_laizes (matiere_id INTEGER, laize_id INTEGER, prix_eur_m2 REAL)")
c3.execute("CREATE TABLE matiere_laize_fournisseurs (matiere_id INTEGER, laize_id INTEGER, fournisseur_id INTEGER)")
c3.execute("CREATE TABLE mp_laizes (id INTEGER PRIMARY KEY, valeur_mm REAL, label TEXT, ordre INTEGER, actif INTEGER)")
c3.execute("CREATE TABLE mc_material (id INTEGER PRIMARY KEY, name TEXT, appellation_code TEXT, supplier_id INTEGER, category_id INTEGER, is_active INTEGER)")
c3.execute("CREATE TABLE mc_supplier (id INTEGER PRIMARY KEY, name TEXT)")
c3.execute("CREATE TABLE fournisseurs_fsc (id INTEGER PRIMARY KEY, nom TEXT)")
c3.execute("CREATE TABLE imprimantes (id INTEGER PRIMARY KEY)")
c3.commit()
ordre = appliquer_migrations(c3)
check("prix_par_fournisseur passe avant declinaisons",
      ordre.index("mp_matiere_prix_par_fournisseur") < ordre.index("mp_declinaisons_appairage"), True)
c3.close(); os.unlink(db3)

os.unlink(db)
print()
print("ECHECS : " + ", ".join(FAIL) if FAIL else "TOUT EST VERT")
sys.exit(1 if FAIL else 0)
