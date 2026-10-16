"""
Matières tenues à l'unité : bagues et cartons achetés au lot (16/10/2026).

1. La migration bascule les bagues et les cartons dont le fournisseur principal
   vend au lot, et convertit le stock (palettes -> unités) sans toucher aux
   autres. Rejouée, elle ne convertit pas deux fois.
2. La réception RVGI entre la quantité RVGI telle quelle, sans exiger de
   conditionnement.
3. Le retour à la palette divise le stock par le conditionnement saisi.
4. La liste d'appariement nomme le fournisseur PRINCIPAL, pas le premier venu.
"""
import importlib
import sqlite3
import sys

sys.path.insert(0, ".")
from app.services import reception_rvgi as rr                # noqa: E402
from app.services.stock_a_l_unite import repasser_a_la_palette  # noqa: E402

mig = importlib.import_module("app.core.migrations.2026_10_16_mp_stock_a_l_unite")

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


def base():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript("""
        CREATE TABLE matieres_premieres (id INTEGER PRIMARY KEY, categorie TEXT, sous_section TEXT,
            reference TEXT, designation TEXT, seuil_alerte REAL, actif INTEGER DEFAULT 1,
            metres_lineaires_par_bobine REAL, unites_par_palette REAL);
        CREATE TABLE mp_stock (matiere_id INTEGER PRIMARY KEY, quantite REAL);
        CREATE TABLE mp_mouvements (id INTEGER PRIMARY KEY, matiere_id INTEGER, quantite REAL,
            quantite_avant REAL, quantite_apres REAL);
        CREATE TABLE inventaires_matieres (id INTEGER PRIMARY KEY, matiere_id INTEGER,
            quantite_avant REAL, quantite_comptee REAL, ecart REAL);
        CREATE TABLE fournisseurs_fsc (id INTEGER PRIMARY KEY, nom TEXT);
        CREATE TABLE mp_variantes (id INTEGER PRIMARY KEY, matiere_id INTEGER, fournisseur_id INTEGER,
            libelle_technique TEXT, principal INTEGER, actif INTEGER DEFAULT 1);
        CREATE TABLE mp_laizes (id INTEGER PRIMARY KEY, valeur_mm REAL, actif INTEGER DEFAULT 1);
        CREATE TABLE mp_matiere_laizes (matiere_id INTEGER, laize_id INTEGER);
        INSERT INTO fournisseurs_fsc VALUES (1, 'RAJA'), (2, 'LGP PACKAGING'),
            (3, 'ALLPACK TUPACK'), (4, 'JOYE KARTONNAGE NV');
        INSERT INTO matieres_premieres VALUES
            (1, 'mandrin', 'Bague', 'B1', 'Bague Ø 76 mm, Lg 91,5 mm', 2, 1, NULL, 125),
            (2, 'mandrin', NULL, 'B2', 'Bague Ø 19 mm', 0, 1, NULL, NULL),
            (3, 'carton', NULL, 'C1', '300 x 300 x 250 mm', 0, 1, NULL, 25),
            (4, 'carton', NULL, 'C2', 'Carton 385 x 385 x 120 mm', 1, 1, NULL, 260),
            (5, 'mandrin', NULL, 'T76', 'Tube carton Ø 76 mm', 0, 1, NULL, 338);
        INSERT INTO mp_stock VALUES (1, 12), (2, 0), (3, 1), (4, 3), (5, 2);
        INSERT INTO mp_mouvements VALUES (1, 1, 12, 0, 12), (2, 4, 3, 0, 3);
        INSERT INTO inventaires_matieres VALUES (1, 1, 10, 12, 2);
        INSERT INTO mp_variantes VALUES
            (1, 3, 1, '300 x 300 x 250 mm', 1, 1),
            (2, 4, 2, 'Carton 385 x 385 x 120 mm — LGP PACKAGING', 1, 1),
            (3, 4, 1, 'Carton 385', 0, 1),
            (4, 5, 3, 'Tube Ø 76 mm, Palette 260 t — ALLPACK TUPACK', 0, 1),
            (5, 5, 4, 'Tube carton Ø 76 mm', 1, 1);
    """)
    return c


def stock(c, mid):
    return c.execute("SELECT quantite FROM mp_stock WHERE matiere_id=?", (mid,)).fetchone()[0]


def flag(c, mid):
    return c.execute("SELECT stock_a_l_unite, unites_par_palette FROM matieres_premieres WHERE id=?",
                     (mid,)).fetchone()


print("1. Migration")
c = base()
mig.appliquer(c)
mig.appliquer(c)
check("bague : 12 palettes de 125 -> 1 500 bagues", stock(c, 1), 1500)
check("bague : seuil converti", c.execute("SELECT seuil_alerte FROM matieres_premieres WHERE id=1").fetchone()[0], 250)
check("bague : historique converti",
      tuple(c.execute("SELECT quantite, quantite_apres FROM mp_mouvements WHERE id=1").fetchone()), (1500, 1500))
check("bague : inventaire converti",
      c.execute("SELECT quantite_comptee FROM inventaires_matieres WHERE id=1").fetchone()[0], 1500)
check("bague : drapeau et conditionnement 1", tuple(flag(c, 1)), (1, 1))
check("bague sans conditionnement : basculée, stock nul inchangé", (tuple(flag(c, 2)), stock(c, 2)), ((1, 1), 0))
check("carton RAJA : 1 lot de 25 -> 25 cartons", stock(c, 3), 25)
check("carton LGP (RAJA secondaire) : intact", (tuple(flag(c, 4)), stock(c, 4)), ((0, 260), 3))
check("tube : intact", tuple(flag(c, 5)), (0, 338))

print("2. Réception RVGI")
ms = {m["id"]: m for m in rr._matieres(c)}
r = rr.convertir(15, 4000, ms[2])
check("4 000 bagues sans conditionnement -> 4 000 tubes", (r["quantite"], r["unite"], r["manque"]), (4000, "tube", []))
r = rr.convertir(19, 175, ms[3])
check("175 cartons au lot -> 175 cartons", (r["quantite"], r["unite"]), (175, "carton"))
r = rr.convertir(19, 520, ms[4])
check("carton à la palette : toujours converti", r["quantite"], 2)

print("3. Retour à la palette")
repasser_a_la_palette(c, 1, 125)
check("1 500 bagues -> 12 palettes", (stock(c, 1), tuple(flag(c, 1))), (12, (0, 125)))

print("4. Fournisseur principal")
d = rr.details_matieres(c)
check("tube : variante principale seule", d[5]["libelles_techniques"], ["Tube carton Ø 76 mm"])
check("tube : fournisseur principal", d[5]["fournisseur_principal"], "JOYE KARTONNAGE NV")

print(f"\n{'KO' if ko else 'OK'} — {ko} échec(s)")
sys.exit(1 if ko else 0)
