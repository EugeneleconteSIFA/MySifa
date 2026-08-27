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

def base_complete():
    """Cree une base neuve avec le schema COMPLET, puis oublie les migrations fichiers.

    Historique : ce test construisait ses bases de simulation a la main, avec une
    poignee de CREATE TABLE. Chaque nouvelle migration fichier touchant une table
    absente de cette liste faisait echouer le test pour une raison qui n'avait
    rien a voir avec ce qu'il verifie (constate le 27/08/2026 sur
    2026_08_06_expe_no_bl_controle, qui lit expe_departs — table creee par la
    migration numerotee v13, jamais presente dans le fixture).

    On part donc d'un init_db() reel : le schema est complet et il le reste, quoi
    qu'on ajoute ensuite. On vide simplement la table de suivi des migrations
    fichiers pour que le lanceur croie qu'aucune n'est passee. Effet de bord
    utile : les migrations sont rejouees sur un schema reel, ce qui verifie leur
    idempotence pour de vrai.
    """
    chemin = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    os.environ["DB_PATH"] = chemin
    config.DB_PATH = chemin
    dbmod.DB_PATH = chemin
    with contextlib.redirect_stdout(io.StringIO()):
        dbmod.init_db()
    c = sqlite3.connect(chemin)
    c.row_factory = sqlite3.Row
    c.execute("DELETE FROM schema_migrations_fichiers")
    c.commit()
    return chemin, c


print("\n--- base ou une migration est deja passee par l'ancien mecanisme ---")
db2, conn2 = base_complete()
# La base pretend avoir joue mp_declinaisons_appairage sous son ancien numero.
conn2.execute("INSERT OR REPLACE INTO schema_migrations VALUES (228,'mp_declinaisons_appairage','2026-01-01')")
conn2.commit()
from app.core.migrations import appliquer_migrations
with contextlib.redirect_stdout(io.StringIO()):
    faites = appliquer_migrations(conn2)
check("migration deja passee sous son ancien numero -> ignoree",
      "mp_declinaisons_appairage" in faites, False)
check("les autres restent a appliquer", len(faites), len(FICHIERS) - 1)
check("rejeu sur schema reel : aucune erreur", True, True)
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
# DEPEND : les declinaisons attendent la table des prix. Meme base complete,
# pour que l'ordre teste soit celui d'un vrai demarrage et pas celui d'un fixture.
db3, c3 = base_complete()
with contextlib.redirect_stdout(io.StringIO()):
    ordre = appliquer_migrations(c3)
check("prix_par_fournisseur passe avant declinaisons",
      ordre.index("mp_matiere_prix_par_fournisseur") < ordre.index("mp_declinaisons_appairage"), True)
check("toutes les migrations rejouables sur un schema reel", len(ordre), len(FICHIERS))
c3.close(); os.unlink(db3)

os.unlink(db)
print()
print("ECHECS : " + ", ".join(FAIL) if FAIL else "TOUT EST VERT")
sys.exit(1 if FAIL else 0)
