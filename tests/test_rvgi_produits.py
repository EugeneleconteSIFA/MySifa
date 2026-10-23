"""
Articles RVGI → produits MyStock : ce qui doit entrer, ce qui ne doit pas bouger.

Cas réel à l'origine : 601/0168 (Roquette) est commandé dans RVGI et n'existe
pas dans MyStock, dont la base produits n'a été chargée qu'une fois, en avril.
"""
import sqlite3
import sys

sys.path.insert(0, ".")
import database                                              # noqa: E402,F401
from app.services import rvgi_produits as rp                 # noqa: E402
import importlib.util                                        # noqa: E402

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


def base_mysifa():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE produits (
        id INTEGER PRIMARY KEY AUTOINCREMENT, reference TEXT NOT NULL UNIQUE,
        designation TEXT NOT NULL, description TEXT, unite TEXT,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        type TEXT NOT NULL DEFAULT 'fabrique', origine TEXT NOT NULL DEFAULT 'interne')""")
    spec = importlib.util.spec_from_file_location(
        "m", "app/core/migrations/2026_10_23_produits_rvgi.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.appliquer(c)
    m.appliquer(c)  # rejouable
    for ref, des, typ in [
        ("601/0001", "Saisie MyStock à garder", "fabrique"),
        ("112/12", "Saisi sans zéros", "fabrique"),
        ("FR110X450_S2021", "Négoce existant", "negoce"),
        ("945/0001", "Connu comme négoce", "negoce"),
    ]:
        c.execute("INSERT INTO produits (reference, designation, unite, type, created_at, updated_at) "
                  "VALUES (?,?,?,?,'2026-04-14','2026-04-14')", (ref, des, "étiquette", typ))
    return c


def base_rvgi():
    e = sqlite3.connect(":memory:")
    e.row_factory = sqlite3.Row
    e.executescript("""
        CREATE TABLE fic_art (code1 TEXT, code2 TEXT, libc1 TEXT, libc2 TEXT,
                              libc3 TEXT, libc4 TEXT, corbeille INTEGER);
        CREATE TABLE cde_entete (numero INTEGER, corbeille INTEGER);
        CREATE TABLE cde_ligne (numero INTEGER, code1 TEXT, code2 TEXT, corbeille INTEGER);
    """)
    arts = [
        ("601", "0001", "Libellé ERP", None, None, 0),
        ("601", "0168", "Etiquette 100 x 150 mm,", "Couché Perm.   Renforcé,",
         "Bobine de 1.000 étiquettes", 0),
        ("601", "0200", "Jamais commandé", None, None, 0),
        ("601", "0201", "Commande à la corbeille", None, None, 0),
        ("112", "12", "Brut", None, None, 0),
        ("TT", "FR110X450_S2021", "Négoce ERP", None, None, 0),
        ("TT", "FR200X300_NEUF", "Nouveau négoce", None, None, 0),
        ("945", "0001", "Fabriqué selon l'ERP", None, None, 0),
        ("FR", "FRAIS_DE_PORT", "Frais de port", None, None, 0),
    ]
    e.executemany("INSERT INTO fic_art VALUES (?,?,?,?,?,NULL,?)", arts)
    e.executemany("INSERT INTO cde_entete VALUES (?,?)", [(1, 0), (2, 1)])
    lignes = [(1, c1, c2, 0) for c1, c2, *_ in arts if c2 not in ("0200", "0201")]
    lignes.append((2, "601", "0201", 0))  # entête supprimée : ne compte pas
    e.executemany("INSERT INTO cde_ligne VALUES (?,?,?,?)", lignes)
    return e


print("\nSynchronisation")
c, e = base_mysifa(), base_rvgi()
res = rp.synchroniser(c, e)
refs = {r["reference"]: dict(r) for r in c.execute("SELECT * FROM produits")}

check("601/0168 créé", "601/0168" in refs, True)
check("désignation au format d'avril, blancs repliés",
      refs["601/0168"]["designation"],
      "Etiquette 100 x 150 mm, | Couché Perm. Renforcé, | Bobine de 1.000 étiquettes")
check("601/0168 marqué comme venant de RVGI", bool(refs["601/0168"]["rvgi_cree_le"]), True)
check("nouveau négoce créé sans TT/", refs.get("FR200X300_NEUF", {}).get("type"), "negoce")
check("article jamais commandé ignoré", "601/0200" in refs, False)
check("commande à la corbeille ignorée", "601/0201" in refs, False)
check("frais ignorés", any(r.startswith("FR/") or r == "FRAIS_DE_PORT" for r in refs), False)
check("existant non réécrit", refs["601/0001"]["designation"], "Saisie MyStock à garder")
check("existant lié", refs["601/0001"]["rvgi_article"], "601/0001")
check("existant non marqué créé", refs["601/0001"]["rvgi_cree_le"], None)
check("« 112/12 » reconnu, pas de doublon 112/0012", "112/0012" in refs, False)
check("négoce existant lié", refs["FR110X450_S2021"]["rvgi_article"], "TT/FR110X450_S2021")
check("type divergent : pas converti", refs["945/0001"]["type"], "negoce")
check("bilan", (res["crees"], res["lies"], res["nb_conflits"]), (2, 3, 1))

print("\nSeconde synchro")
res2 = rp.synchroniser(c, e)
check("rien de neuf", (res2["crees"], res2["lies"], res2["deja_lies"]), (0, 0, 5))

print(f"\n{'Tout est OK' if not ko else f'{ko} échec(s)'}")
sys.exit(1 if ko else 0)
