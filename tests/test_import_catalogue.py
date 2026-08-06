# -*- coding: utf-8 -*-
"""
Import du catalogue « Table Matières » dans les produits MyStock.

On rejoue le script sur une base fabriquée qui ressemble à la production :
des frontaux à plusieurs laizes, quatre familles d'adhésif dont les grammages
ne couvrent pas tout le catalogue, une glassine. On vérifie que les 42 produits
sortent complets, que la déclinaison retenue pour un frontal est bien la moins
chère, que les grammages manquants sont créés, et que rejouer ne duplique rien.

Lancer : python3 tests/test_import_catalogue.py
"""

import contextlib
import importlib
import io
import os
import sys
import tempfile
import types
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))
os.chdir(RACINE)

# pydantic n'est pas toujours installé sur le poste de dev.
if "pydantic" not in sys.modules:
    try:
        import pydantic  # noqa: F401
    except ModuleNotFoundError:
        _pd = types.ModuleType("pydantic")

        class _BM:
            model_config = None

            def __init__(self, **kw):
                self.__dict__.update(kw)

            def __init_subclass__(cls, **kw):
                pass

        _pd.BaseModel = _BM
        _pd.ConfigDict = lambda **kw: kw
        _pd.Field = lambda *a, **kw: (a[0] if a else None)
        _pd.field_validator = lambda *a, **kw: (lambda fn: fn)
        sys.modules["pydantic"] = _pd

ECHECS = []


def check(libelle, valeur, attendu):
    ok = valeur == attendu
    if not ok:
        ECHECS.append(libelle)
    print(("ok   " if ok else "KO   ") + libelle.ljust(56) + repr(valeur)
          + ("" if ok else "   attendu " + repr(attendu)))


db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["DB_PATH"] = db
import config  # noqa: E402

config.DB_PATH = db
import app.core.database as dbmod  # noqa: E402

dbmod.DB_PATH = db
with contextlib.redirect_stdout(io.StringIO()):
    dbmod.init_db()

IMP = importlib.import_module("scripts.import_catalogue_produits")

# ─── Une base qui ressemble à la production ─────────────────────────────────
FRONTAUX_MYSTOCK = [
    ("THPRO70", "Thermique Pro 70g"),
    ("THECO70", "Thermique Eco 70g"),
    ("THECOBI74", "Thermique Eco Bicolore 74g"),
    ("THPRO108", "Thermique Pro 108g"),
    ("CBRIL80", "Couché Brillant 80g"),
    ("SYNTH95", "Synthetique 95 um 71g"),
    ("VEL62", "Velin 62g"),
    ("VEL68", "Velin 68g"),
    ("VELFLUO90", "Velin Jaune Fluo 90g"),
]
ADHESIFS_MYSTOCK = [
    ("ADH-ENL", "Adhesif enlevable", [17, 19, 22]),
    ("ADH-PERM", "Adhesif permanent", [17, 19, 22, 25, 30]),
    ("ADH-CONG", "Adhesif congelation", [22, 28]),
    ("ADH-PNEU", "Adhesif permanent pneu", [55]),
]

with dbmod.get_db() as conn:
    for mm in (330, 500, 1000):
        conn.execute(
            "INSERT OR IGNORE INTO mp_laizes (valeur_mm, label, ordre, actif) VALUES (?,?,?,1)",
            (mm, f"{mm} mm", mm),
        )
    laizes = [r["id"] for r in conn.execute("SELECT id FROM mp_laizes ORDER BY valeur_mm")]

    mid = 100
    for ref, des in FRONTAUX_MYSTOCK:
        mid += 1
        conn.execute(
            """INSERT INTO matieres_premieres (id,categorie,reference,designation,actif,prix_par_laize)
               VALUES (?,'frontal',?,?,1,1)""",
            (mid, ref, des),
        )
        # Trois laizes, prix décroissant : la moins chère est la dernière.
        for i, lid in enumerate(laizes):
            conn.execute(
                """INSERT INTO mp_matiere_declinaison (matiere_id, laize_id, price_basis)
                   VALUES (?,?,'PER_M2')""",
                (mid, lid),
            )
            d = conn.execute("SELECT last_insert_rowid() AS i").fetchone()["i"]
            conn.execute(
                """INSERT INTO mp_matiere_prix
                   (matiere_id, laize_id, declinaison_id, prix, principal, updated_at)
                   VALUES (?,?,?,?,1,'2026-08-04T00:00:00')""",
                (mid, lid, d, 3.0 - i),
            )
    for ref, des, grammages in ADHESIFS_MYSTOCK:
        mid += 1
        conn.execute(
            """INSERT INTO matieres_premieres (id,categorie,reference,designation,actif)
               VALUES (?,'adhesif',?,?,1)""",
            (mid, ref, des),
        )
        for g in grammages:
            conn.execute(
                "INSERT OR IGNORE INTO mp_grammages (valeur_gsm, label, ordre, actif) VALUES (?,?,?,1)",
                (g, f"{g} g/m²", g),
            )
            gid = conn.execute(
                "SELECT id FROM mp_grammages WHERE valeur_gsm=?", (g,)
            ).fetchone()["id"]
            conn.execute(
                """INSERT INTO mp_matiere_declinaison (matiere_id, grammage_id, price_basis)
                   VALUES (?,?,'PER_KG')""",
                (mid, gid),
            )
            d = conn.execute("SELECT last_insert_rowid() AS i").fetchone()["i"]
            conn.execute(
                """INSERT INTO mp_matiere_prix
                   (matiere_id, grammage_id, declinaison_id, prix, principal, updated_at)
                   VALUES (?,?,?,3.2,1,'2026-08-04T00:00:00')""",
                (mid, gid, d),
            )
    mid += 1
    conn.execute(
        """INSERT INTO matieres_premieres (id,categorie,reference,designation,actif,prix_par_laize)
           VALUES (?,'glassine','GLJ60','Glassine jaune 60g',1,1)""",
        (mid,),
    )
    conn.execute(
        """INSERT INTO mp_matiere_declinaison (matiere_id, laize_id, price_basis)
           VALUES (?,?,'PER_M2')""",
        (mid, laizes[0]),
    )
    d = conn.execute("SELECT last_insert_rowid() AS i").fetchone()["i"]
    conn.execute(
        """INSERT INTO mp_matiere_prix
           (matiere_id, laize_id, declinaison_id, prix, principal, updated_at)
           VALUES (?,?,?,0.9,1,'2026-08-04T00:00:00')""",
        (mid, laizes[0], d),
    )
    conn.commit()

    print("--- rapprochement automatique sur une base jouet ---")
    noms = sorted({c[2] for c in IMP.CATALOGUE})
    auto = {nom: ref for ref, des in FRONTAUX_MYSTOCK
            for nom in noms
            if IMP._score(nom, des) >= 0.75 or IMP._score(nom, ref) >= 0.75}
    check("les 9 frontaux du catalogue sont rapprochés", len(auto), len(noms))
    check("le synthétique tombe juste malgré l'orthographe",
          auto.get("Synthé. 95µm 71g"), "SYNTH95")
    check("Velin 62g ne se confond pas avec Velin 68g", auto.get("Velin 62g"), "VEL62")
    check("ni avec le Velin fluo", auto.get("Velin Jaune Fluo 90g"), "VELFLUO90")

    print("\n--- lexique : références réelles du stock SIFA ---")
    # Les références MyStock sont en anglais technique, le catalogue en français
    # commercial. Sans lexique, 3 frontaux sur 9 seulement se rapprochaient.
    REELLES = [
        "62gsm Vellum", "68gsm Vellum", "70g Eco Thermal", "70gsm TOP Thermal",
        "70gsm Vellum fluo jaune", "80gsm Coated Paper", "95gsm TOP Thermal",
        "couché 70gsm satiné", "couché 90gsm fluo jaune",
        "Eco Thermal 70gsm Torraspapel", "PP blanc mat 120µm", "PP blanc mat 200µm",
        "PP blanc mat 95µm", "Thermique Bicolore", "TOP Thermal 105gsm",
    ]

    def meilleur(cible):
        return max(REELLES, key=lambda r: IMP._score(cible, r))

    for cible, veut in [
        ("Velin 62g", "62gsm Vellum"),
        ("Velin 68g", "68gsm Vellum"),
        ("Couché Brillant 80g", "80gsm Coated Paper"),
        ("Thermique Pro 70g", "70gsm TOP Thermal"),
        ("Thermique Eco 70g", "70g Eco Thermal"),
        ("Synthé. 95µm 71g", "PP blanc mat 95µm"),
    ]:
        check(f"{cible} -> stock", meilleur(cible), veut)
    # Un vélin de 62 ne doit jamais partir sur le 68 : sur un nombre, seule
    # l'égalité compte.
    check("62 et 68 ne se confondent pas",
          meilleur("Velin 62g") != meilleur("Velin 68g"), True)

    print("\n--- correspondances figées pour ce catalogue ---")
    check("les 9 frontaux sont renseignés", len(IMP.FRONTAUX), 9)
    check("les 4 familles d'adhésif aussi", len(IMP.ADHESIFS), 4)
    check("une glassine est choisie", bool(IMP.GLASSINE), True)
    check("chaque frontal du catalogue a sa ligne",
          sorted(IMP.FRONTAUX) == sorted({c[2] for c in IMP.CATALOGUE}), True)
    check("chaque famille d'adhésif aussi",
          sorted(IMP.ADHESIFS) == sorted({c[3] for c in IMP.CATALOGUE}), True)

    # Le test tourne ensuite sur ses propres correspondances.
    IMP.FRONTAUX = {nom: ref for ref, des in FRONTAUX_MYSTOCK
                    for nom in [n for n in {c[2] for c in IMP.CATALOGUE}
                                if IMP._score(n, des) >= 0.75 or IMP._score(n, ref) >= 0.75]}
    IMP.ADHESIFS = {"Enlevable": "ADH-ENL", "Permanent": "ADH-PERM",
                    "Congélation": "ADH-CONG", "Permanent Pneu": "ADH-PNEU"}
    IMP.GLASSINE = "GLJ60"

    print("\n--- simulation ---")
    with contextlib.redirect_stdout(io.StringIO()) as sortie:
        code = IMP.executer(conn, appliquer=False)
    txt = sortie.getvalue()
    check("la simulation aboutit", code, 0)
    check("42 produits annoncés", "42 créé(s)" in txt, True)
    check("rien n'est enregistré",
          conn.execute("SELECT COUNT(*) FROM mp_produit").fetchone()[0], 0)

    print("\n--- import ---")
    with contextlib.redirect_stdout(io.StringIO()) as sortie:
        code = IMP.executer(conn, appliquer=True)
    txt = sortie.getvalue()
    check("l'import aboutit", code, 0)
    check("42 produits en base",
          conn.execute("SELECT COUNT(*) FROM mp_produit").fetchone()[0], 42)
    check("trois composants par produit",
          conn.execute("""SELECT MIN(n), MAX(n) FROM (
                            SELECT COUNT(*) AS n FROM mp_produit_composant
                             GROUP BY produit_id)""").fetchone()[:], (3, 3))
    check("aucun produit sans frontal",
          conn.execute("""SELECT COUNT(*) FROM mp_produit p WHERE NOT EXISTS (
                            SELECT 1 FROM mp_produit_composant c
                             WHERE c.produit_id=p.id AND c.role='FRONTAL')""").fetchone()[0], 0)

    # Les grammages absents (25 et 30 en congélation, 40 en permanent) sont créés.
    check("grammages de colle ajoutés", "déclinaison(s) ajoutée(s)" in txt, True)
    check("congélation 30 g/m² existe désormais",
          conn.execute("""SELECT COUNT(*) FROM mp_matiere_declinaison d
                            JOIN mp_grammages g ON g.id=d.grammage_id
                            JOIN matieres_premieres m ON m.id=d.matiere_id
                           WHERE m.reference='ADH-CONG' AND g.valeur_gsm=30""").fetchone()[0], 1)
    check("permanent 40 g/m² aussi",
          conn.execute("""SELECT COUNT(*) FROM mp_matiere_declinaison d
                            JOIN mp_grammages g ON g.id=d.grammage_id
                            JOIN matieres_premieres m ON m.id=d.matiere_id
                           WHERE m.reference='ADH-PERM' AND g.valeur_gsm=40""").fetchone()[0], 1)

    print("\n--- la laize retenue est la moins chère ---")
    prix_frontal = conn.execute(
        """SELECT DISTINCT p.prix FROM mp_produit_composant c
             JOIN mp_matiere_prix p ON p.declinaison_id = c.declinaison_id AND p.principal=1
            WHERE c.role='FRONTAL'"""
    ).fetchall()
    check("un seul niveau de prix, le plus bas", [r["prix"] for r in prix_frontal], [1.0])

    print("\n--- le coût de revient se calcule ---")
    from app.services import mystock_produits as PROD  # noqa: E402
    from app.services.pricing.repository import load_pricing_settings  # noqa: E402

    reglages = load_pricing_settings(conn)
    p1 = conn.execute("SELECT id FROM mp_produit WHERE code='886-0001'").fetchone()["id"]
    cout = PROD.cout_produit(conn, PROD.get_produit(conn, p1), reglages)
    check("trois composants dans le calcul", len(cout.components), 3)
    check("un coût strictement positif", float(cout.total_eur_per_m2) > 0, True)

    print("\n--- rejouer ne duplique rien ---")
    with contextlib.redirect_stdout(io.StringIO()) as sortie:
        IMP.executer(conn, appliquer=True)
    check("toujours 42 produits",
          conn.execute("SELECT COUNT(*) FROM mp_produit").fetchone()[0], 42)
    check("42 mises à jour, aucune création", "0 créé(s), 42 mis à jour" in sortie.getvalue(), True)
    check("pas de composant en double",
          conn.execute("""SELECT COUNT(*) FROM (
                            SELECT produit_id FROM mp_produit_composant
                             GROUP BY produit_id HAVING COUNT(*)<>3)""").fetchone()[0], 0)

    print("\n--- base qui n'est pas celle de l'application ---")
    # Lancé à la main, le script peut viser un fichier vide : il doit le dire,
    # pas partir en traceback sur « no such table ».
    import sqlite3 as _sq

    vide = _sq.connect(":memory:")
    vide.row_factory = _sq.Row
    check("les tables attendues sont listées",
          IMP.tables_manquantes(vide), list(IMP.TABLES_REQUISES))
    vide.close()
    check("aucune table ne manque sur la vraie base", IMP.tables_manquantes(conn), [])
    check("l'aide cite l'option --db", "--db" in IMP._AIDE_BASE, True)

    print("\n--- correspondance manquante ---")
    IMP.ADHESIFS = dict(IMP.ADHESIFS, **{"Congélation": "NEXISTEPAS"})
    with contextlib.redirect_stdout(io.StringIO()) as sortie:
        code = IMP.executer(conn, appliquer=False)
    check("le script refuse de tourner", code, 1)
    check("et dit précisément ce qui manque", "Congélation" in sortie.getvalue(), True)

os.unlink(db)
print("\n" + ("TOUT EST VERT" if not ECHECS else "ECHECS : " + ", ".join(ECHECS)))
sys.exit(1 if ECHECS else 0)
