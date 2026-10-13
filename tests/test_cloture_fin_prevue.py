"""
Cloture a la fin prevue des postes sans saisie de production (DSI).

Ce qui se verifie ici :

1. La migration `postes_cloture_fin_prevue` ajoute la colonne, coche le poste
   dont le code est DSI, et se rejoue sans rien casser.
2. `cloturer_fins_prevues` ne clot que ce qu'il doit : poste coche, dossier
   pas encore termine, fin prevue passee ET posterieure a la mise en service
   (aucun rattrapage, arbitrage du 13/10/2026), aucune saisie de production.

Le code est extrait du router par decoupage de source, comme
`test_besoins_verrou_documents.py` : le module entier tirerait fastapi.
"""
import importlib.util
import sqlite3
import sys
from datetime import datetime, timedelta

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


src = open("app/routers/besoins_matieres.py", encoding="utf-8").read()
bloc = src[src.index("def cloturer_fins_prevues("):src.index("def balayer_destockage_auto(")]
ns = {"datetime": datetime}
exec(compile(bloc, "cloture_bloc", "exec"), ns)
cloturer = ns["cloturer_fins_prevues"]

spec = importlib.util.spec_from_file_location(
    "mig_cfp", "app/core/migrations/2026_10_13_machine_cloture_fin_prevue.py")
mig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mig)

conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.executescript("""
    CREATE TABLE machines(id INTEGER PRIMARY KEY, nom TEXT, code TEXT);
    CREATE TABLE planning_entries(id INTEGER PRIMARY KEY, machine_id INTEGER,
        reference TEXT, statut TEXT, statut_reel TEXT, statut_force INTEGER,
        planned_end TEXT, updated_at TEXT);
    CREATE TABLE production_data(id INTEGER PRIMARY KEY, no_dossier TEXT,
        est_annule INTEGER);
    INSERT INTO machines VALUES (1, 'Cohésio 1', 'C1'), (4, 'DSI', 'DSI');
""")

print("Migration")
mig.appliquer(conn)
mig.appliquer(conn)
coches = [r["code"] for r in conn.execute(
    "SELECT code FROM machines WHERE cloture_fin_prevue=1")]
check("seul le DSI est coché, migration rejouable", coches, ["DSI"])

print("Sélection des dossiers")
fmt = "%Y-%m-%dT%H:%M:%S"
maintenant = datetime.now()
hier = (maintenant - timedelta(days=1)).strftime(fmt)
demain = (maintenant + timedelta(days=1)).strftime(fmt)
avant_service = (maintenant - timedelta(days=30)).strftime(fmt)
depuis = (maintenant - timedelta(days=7)).strftime("%Y-%m-%d")
conn.executemany(
    "INSERT INTO planning_entries(id, machine_id, reference, statut, planned_end) "
    "VALUES (?,?,?,?,?)",
    [
        (1, 4, "D-echu", "attente", hier),           # à clore
        (2, 4, "D-encours", "en_cours", hier),       # à clore
        (3, 4, "D-futur", "attente", demain),        # fin pas encore passée
        (4, 4, "D-ancien", "attente", avant_service),  # avant mise en service
        (5, 4, "D-saisi", "attente", hier),          # porte une saisie
        (6, 4, "D-fini", "termine", hier),           # déjà terminé
        (7, 1, "C-echu", "attente", hier),           # poste non coché
        (8, 4, "D-sansfin", "attente", None),        # pas de fin prévue
    ])
conn.execute("INSERT INTO production_data(no_dossier, est_annule) VALUES ('D-saisi', 0)")

clos = cloturer(conn, depuis)
check("dossiers clos", sorted(clos), [1, 2])
r = conn.execute("SELECT statut, statut_reel, statut_force FROM planning_entries WHERE id=1").fetchone()
check("statut posé comme une clôture forcée",
      (r["statut"], r["statut_reel"], r["statut_force"]),
      ("termine", "reellement_termine", 1))
check("second passage : rien de plus", cloturer(conn, depuis), [])

conn.execute("UPDATE production_data SET est_annule=1")
check("saisie annulée : le dossier redevient clôturable", cloturer(conn, depuis), [5])

print()
print("Tout est vert." if not ko else f"{ko} échec(s).")
sys.exit(1 if ko else 0)
