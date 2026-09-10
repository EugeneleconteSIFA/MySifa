"""
Repère « déstocké dans RVGI » du planning — disjoint du déstockage MyStock.

Décision d'Eugène du 10/09/2026 : la collègue qui déstocke dans l'ERP garde
son point gris sur le planning, et ce point ne touche plus au stock MySifa.

1. **La reprise déplace le marquage manuel** : « déstocké » sans mouvement
   devient un repère RVGI et l'état MyStock revient à « à destocker ».
2. **Un dossier réellement sorti du stock garde son état MyStock.**
3. **La reprise ne se rejoue pas** : un second passage n'efface rien.
4. **Le bouton du planning n'écrit que le repère** — ni `destockage`, ni
   `updated_at`, ni la modale MyStock.
"""
import importlib.util
import sqlite3
import sys

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


spec = importlib.util.spec_from_file_location(
    "mig", "app/core/migrations/2026_09_10_destockage_rvgi_planning.py")
mig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mig)

conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.executescript("""
    CREATE TABLE planning_entries (id INTEGER PRIMARY KEY, destockage TEXT DEFAULT 'todo',
        destockage_at TEXT, destockage_reserve TEXT, destockage_par TEXT,
        destockage_relu_par TEXT, destockage_relu_at TEXT, updated_at TEXT);
    CREATE TABLE mp_mouvements (id INTEGER PRIMARY KEY, planning_entry_id INTEGER);
    INSERT INTO planning_entries VALUES (1, 'done', NULL, NULL, NULL, NULL, NULL, '2026-05-01');
    INSERT INTO planning_entries VALUES (2, 'reserve', '2026-09-10T10:00', 'carton', 'Anne', NULL, NULL, '2026-09-10');
    INSERT INTO planning_entries VALUES (3, 'todo', NULL, NULL, NULL, NULL, NULL, '2026-09-10');
    INSERT INTO mp_mouvements VALUES (1, 2);
""")
mig.appliquer(conn)
r = {x["id"]: dict(x) for x in conn.execute("SELECT * FROM planning_entries")}

print("1. Reprise du marquage manuel")
check("dossier marqué sans mouvement : repère RVGI posé", r[1]["destockage_rvgi"], "done")
check("et état MyStock remis à « à destocker »", r[1]["destockage"], "todo")
check("updated_at intact", r[1]["updated_at"], "2026-05-01")

print("2. Un dossier sorti du stock garde son état")
check("état MyStock conservé", (r[2]["destockage"], r[2]["destockage_reserve"]), ("reserve", "carton"))
check("pas de repère RVGI inventé", r[2]["destockage_rvgi"], "todo")
check("dossier à faire : rien ne change", (r[3]["destockage"], r[3]["destockage_rvgi"]), ("todo", "todo"))

print("3. Pas de reprise au second passage")
conn.execute("UPDATE planning_entries SET destockage='done' WHERE id=3")
mig.appliquer(conn)
check("un déstockage MyStock postérieur n'est pas repris",
      conn.execute("SELECT destockage, destockage_rvgi FROM planning_entries WHERE id=3").fetchone()[:],
      ("done", "todo"))

print("4. Le bouton du planning")
src = open("app/routers/planning.py", encoding="utf-8").read()
route = src[src.index("def toggle_destockage("):]
route = route[:route.index("\n@router")]
check("écrit destockage_rvgi", "SET destockage_rvgi=?" in route, True)
check("n'écrit pas l'état MyStock", "destockage=?" in route.replace("destockage_rvgi=?", ""), False)
check("ne touche pas updated_at", "updated_at" in route.split('"""')[2], False)
page = open("app/web/planning_page.py", encoding="utf-8").read()
check("le point gris lit le repère RVGI", 'const destock=s.destockage_rvgi==="done";' in page, True)
check("le planning n'ouvre plus la modale MyStock", "MySifaDestockage" in page or "mysifa_destockage.js" in page, False)

print()
if ko:
    print(f"ÉCHEC — {ko} vérification(s) en erreur.")
    sys.exit(1)
print("Tous les cas passent.")
