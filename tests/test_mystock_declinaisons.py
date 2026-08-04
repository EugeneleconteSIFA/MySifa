"""
Pont Coûts matières <-> MyStock : déclinaisons, prix par fournisseur, appairage.

Couvre le modèle mis en place le 3 août 2026 :
  - périmètre du module (les supports logistiques en sont exclus) ;
  - déclinaison par laize (frontal/glassine/complexe) ou grammage (adhésif) ;
  - appairage au niveau de la DÉCLINAISON, pas de la matière ;
  - prix par fournisseur, principal, miroir vers la valorisation MyStock ;
  - le prix MyStock pilote la fiche Coûts matières et le coût produit.

Lancer : python3 tests/test_mystock_declinaisons.py
(le script pilote un démarrage complet de la base, il ne passe pas par unittest)
"""

import contextlib
import io
import os
import sqlite3
import sys
import tempfile
import types
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))
os.chdir(RACINE)

# pydantic n'est pas toujours installé sur le poste de dev : doublure minimale,
# suffisante pour importer app.models.material_cost dont on n'utilise que des
# constantes. Sans elle, ce test ne pourrait tourner que sur le VPS.
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

ECHECS: list[str] = []


def check(label, got, expected):
    ok = got == expected
    print(("ok   " if ok else "KO   ") + label.ljust(58) + f"{got}"
          + ("" if ok else f"   attendu {expected}"))
    if not ok:
        ECHECS.append(label)


db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["DB_PATH"] = db
import config  # noqa: E402

config.DB_PATH = db
import app.core.database as dbmod  # noqa: E402

dbmod.DB_PATH = db
with contextlib.redirect_stdout(io.StringIO()):
    dbmod.init_db()

with dbmod.get_db() as conn:
    # ── jeu de données ──────────────────────────────────────────────────────
    # On rejoue les migrations en fichiers après avoir posé les données, pour
    # vérifier la reprise de l'existant.
    conn.execute("DELETE FROM schema_migrations_fichiers")
    for nom in ("Rheno", "Jaour", "Meltavis"):
        conn.execute("INSERT OR IGNORE INTO fournisseurs_fsc (nom, actif) VALUES (?,1)", (nom,))
    f = {r["nom"]: r["id"] for r in conn.execute("SELECT id, nom FROM fournisseurs_fsc")}
    for mm in (330, 500):
        conn.execute(
            "INSERT OR IGNORE INTO mp_laizes (valeur_mm, label, ordre, actif) VALUES (?,?,?,1)",
            (mm, f"{mm} mm", mm),
        )
    laize = {int(r["valeur_mm"]): r["id"] for r in conn.execute("SELECT id, valeur_mm FROM mp_laizes")}
    cat_a = conn.execute("SELECT id FROM mc_material_category WHERE code='ADHESIF'").fetchone()["id"]
    cat_f = conn.execute("SELECT id FROM mc_material_category WHERE code='FRONTAL'").fetchone()["id"]

    # Fiches Coûts matières : trois grammages du même adhésif + un frontal.
    for mid, nom, prix in ((1, "2028/22", 2.70), (2, "2028/25", 2.70), (3, "2028/30", 3.11)):
        conn.execute(
            """INSERT INTO mc_material (id,name,appellation_code,category_id,weight_per_m2,
               price_currency,unit_price,price_basis,tax_incidence,is_active)
               VALUES (?,?,'2028',?,0.028,'EUR',?,'PER_KG',1,1)""",
            (mid, nom, cat_a, prix),
        )
    conn.execute(
        """INSERT INTO mc_material (id,name,appellation_code,category_id,weight_per_m2,
           price_currency,unit_price,price_basis,tax_incidence,is_active)
           VALUES (9,'Frontal 70','F70',?,0.07,'EUR',9.99,'PER_M2',1,1)""",
        (cat_f,),
    )
    # Une fiche jamais appairée : elle doit garder son prix propre.
    conn.execute(
        """INSERT INTO mc_material (id,name,appellation_code,category_id,weight_per_m2,
           price_currency,unit_price,price_basis,tax_incidence,is_active)
           VALUES (10,'Import Chine','R163',?,0,'EUR',4.0183,'PER_M2',0.95,1)""",
        (cat_f,),
    )
    # Ancien annuaire Coûts matières, à rapprocher de celui de l'entreprise.
    for nom in ("Rheno", "JAOUR S.A.", "Chine"):
        conn.execute("INSERT INTO mc_supplier (name) VALUES (?)", (nom,))

    # MyStock : un adhésif, un frontal laizé, un carton (support logistique).
    conn.execute(
        """INSERT INTO matieres_premieres (id,categorie,reference,designation,actif)
           VALUES (1,'adhesif','2028','Adhesif permanent 2028',1)"""
    )
    conn.execute("INSERT INTO mp_valorisation (matiere_id,prix_unitaire) VALUES (1,2.70)")
    conn.execute(
        """INSERT INTO matieres_premieres (id,categorie,reference,designation,actif,
           prix_eur_m2,prix_par_laize,mc_material_id)
           VALUES (2,'frontal','F70','Frontal 70g',1,0,1,9)"""
    )
    for lid, prix in ((laize[330], 1.25), (laize[500], 1.45)):
        conn.execute(
            "INSERT INTO mp_matiere_laizes (matiere_id,laize_id,prix_eur_m2) VALUES (2,?,?)",
            (lid, prix),
        )
    conn.execute(
        """INSERT INTO matieres_premieres (id,categorie,reference,designation,actif)
           VALUES (3,'carton','CART','Carton 40x30',1)"""
    )
    conn.execute("INSERT INTO mp_valorisation (matiere_id,prix_unitaire) VALUES (3,0.85)")
    conn.execute(
        """INSERT INTO mc_product (id,code,name,frontal_id,adhesif_id,is_active)
           VALUES (1,'P1','Produit test',9,1,1)"""
    )
    conn.commit()
    with contextlib.redirect_stdout(io.StringIO()):
        dbmod._migrate(conn)

    from app.services import mystock_prix as MP  # noqa: E402
    from app.services.pricing import (  # noqa: E402
        PricingProduct,
        compute_material_price_per_m2,
        compute_product_cost,
    )
    from app.services.pricing.repository import (  # noqa: E402
        fetch_material,
        fetch_materials_map,
        load_pricing_settings,
        mystock_price_for_row,
        row_to_pricing_material,
    )

    reglages = load_pricing_settings(conn)
    mats = {m["reference"]: m for m in MP.list_materials(conn)}

    print("--- rapprochement de l'annuaire fournisseurs ---")
    rap = {r["name"]: r["fournisseur_fsc_id"]
           for r in conn.execute("SELECT name, fournisseur_fsc_id FROM mc_supplier")}
    check("Rheno rapproché", rap["Rheno"] == f["Rheno"], True)
    check("JAOUR S.A. rapproché malgré le suffixe", rap["JAOUR S.A."] == f["Jaour"], True)
    check("Chine sans correspondance", rap["Chine"], None)

    print("\n--- périmètre du module ---")
    check("support logistique exclu", "CART" in mats, False)
    check("adhésif présent", "2028" in mats, True)
    check("frontal présent", "F70" in mats, True)

    print("\n--- type de déclinaison ---")
    check("adhésif décliné au grammage", mats["2028"]["type_declinaison"], "GRAMMAGE")
    check("frontal décliné à la laize", mats["F70"]["type_declinaison"], "LAIZE")
    check("unité adhésif", mats["2028"]["unite"], "€/kg")
    check("unité frontal", mats["F70"]["unite"], "€/m²")
    check("les 2 laizes sont reprises", mats["F70"]["nb_declinaisons"], 2)
    check("appairage matière ambigu, non repris", mats["F70"]["nb_appairees"], 0)

    print("\n--- déclaration des grammages ---")
    vide = next(d for d in mats["2028"]["declinaisons"] if d["grammage_id"] is None)
    check("nommage de la déclinaison reprise",
          MP.set_declinaison_valeur(conn, declinaison_id=vide["id"], valeur_gsm=22)["ok"], True)
    for gsm in (25, 30):
        assert MP.add_declinaison(conn, matiere_id=1, valeur_gsm=gsm)["ok"]
    conn.commit()
    check("refus d'un grammage déjà décliné",
          MP.add_declinaison(conn, matiere_id=1, valeur_gsm=22)["ok"], False)
    check("refus d'une laize sur un adhésif",
          MP.add_declinaison(conn, matiere_id=1, laize_id=laize[330])["ok"], False)
    mats = {m["reference"]: m for m in MP.list_materials(conn)}
    check("3 grammages", sorted(d["libelle"] for d in mats["2028"]["declinaisons"]),
          ["22 g/m²", "25 g/m²", "30 g/m²"])

    print("\n--- appairage par déclinaison ---")
    d22 = next(d for d in mats["2028"]["declinaisons"] if d["libelle"] == "22 g/m²")
    d30 = next(d for d in mats["2028"]["declinaisons"] if d["libelle"] == "30 g/m²")
    check("22 g/m² -> fiche 2028/22",
          MP.set_appairage(conn, declinaison_id=d22["id"], mc_material_id=1)["ok"], True)
    check("30 g/m² -> fiche 2028/30",
          MP.set_appairage(conn, declinaison_id=d30["id"], mc_material_id=3)["ok"], True)
    conn.commit()
    MP.set_appairage(conn, declinaison_id=d30["id"], mc_material_id=1)
    check("une fiche n'est pilotée que par une déclinaison",
          conn.execute("SELECT COUNT(*) FROM mp_matiere_declinaison WHERE mc_material_id=1")
          .fetchone()[0], 1)
    MP.set_appairage(conn, declinaison_id=d30["id"], mc_material_id=3)
    MP.set_appairage(conn, declinaison_id=d22["id"], mc_material_id=1)
    conn.commit()

    print("\n--- tarifs différents selon le grammage ---")
    MP.set_prix(conn, declinaison_id=d22["id"], fournisseur_id=f["Jaour"], prix=2.70,
                user_name="Test")
    MP.set_prix(conn, declinaison_id=d30["id"], fournisseur_id=f["Jaour"], prix=3.11,
                user_name="Test")
    conn.commit()
    ms22 = mystock_price_for_row(conn, fetch_material(conn, 1))
    ms30 = mystock_price_for_row(conn, fetch_material(conn, 3))
    check("un vrai prix reprend la main sur la ligne vide", ms22 is not None, True)
    check("fiche 2028/22 pilotée à 2,70", float(ms22["unit_price"]), 2.7)
    check("fiche 2028/30 pilotée à 3,11", float(ms30["unit_price"]), 3.11)
    check("le détail du grammage remonte", ms22["detail"], "grammage 22 g/m²")
    check("base au kilo pour un adhésif", ms22["price_basis"], "PER_KG")
    check("le prix local de la fiche est ignoré",
          float(compute_material_price_per_m2(
              row_to_pricing_material(fetch_material(conn, 1), mystock=ms22),
              reglages).price_eur_per_m2), round(2.70 * 0.028, 4))

    print("\n--- fiche non appairée ---")
    row10 = fetch_material(conn, 10)
    check("aucun pilotage", mystock_price_for_row(conn, row10), None)
    check("garde son prix propre",
          float(compute_material_price_per_m2(row_to_pricing_material(row10), reglages)
                .price_eur_per_m2), round(4.0183 * 0.95, 4))

    print("\n--- laize : renommage du fournisseur, miroir, historisation ---")
    mats = {m["reference"]: m for m in MP.list_materials(conn)}
    dl = next(d for d in mats["F70"]["declinaisons"] if "330" in d["libelle"])
    check("renommage du fournisseur de la ligne principale",
          MP.set_fournisseur(conn, declinaison_id=dl["id"], fournisseur_id=None,
                             nouveau_fournisseur_id=f["Rheno"])["ok"], True)
    conn.commit()
    check("la ligne reste principale",
          conn.execute("""SELECT COUNT(*) FROM mp_matiere_prix
                          WHERE declinaison_id=? AND principal=1 AND fournisseur_id=?""",
                       (dl["id"], f["Rheno"])).fetchone()[0], 1)
    check("fournisseur reporté pour les écrans MyStock",
          conn.execute("""SELECT COUNT(*) FROM matiere_laize_fournisseurs
                          WHERE matiere_id=2 AND laize_id=?""", (laize[330],)).fetchone()[0], 1)
    MP.set_prix(conn, declinaison_id=dl["id"], fournisseur_id=f["Rheno"], prix=1.31,
                user_name="Test")
    conn.commit()
    check("miroir dans mp_matiere_laizes",
          conn.execute("SELECT prix_eur_m2 FROM mp_matiere_laizes WHERE matiere_id=2 AND laize_id=?",
                       (laize[330],)).fetchone()[0], 1.31)
    check("changement historisé",
          conn.execute("SELECT COUNT(*) FROM mp_valorisation_historique WHERE matiere_id=2")
          .fetchone()[0], 1)
    check("l'autre laize n'a pas bougé",
          conn.execute("SELECT prix_eur_m2 FROM mp_matiere_laizes WHERE matiere_id=2 AND laize_id=?",
                       (laize[500],)).fetchone()[0], 1.45)

    print("\n--- un fournisseur non principal ne pousse rien ---")
    MP.set_prix(conn, declinaison_id=dl["id"], fournisseur_id=f["Meltavis"], prix=1.19,
                user_name="Test")
    conn.commit()
    check("le miroir MyStock ne bouge pas",
          conn.execute("SELECT prix_eur_m2 FROM mp_matiere_laizes WHERE matiere_id=2 AND laize_id=?",
                       (laize[330],)).fetchone()[0], 1.31)
    MP.set_principal(conn, declinaison_id=dl["id"], fournisseur_id=f["Meltavis"], user_name="Test")
    conn.commit()
    check("bascule du principal : son tarif est poussé",
          conn.execute("SELECT prix_eur_m2 FROM mp_matiere_laizes WHERE matiere_id=2 AND laize_id=?",
                       (laize[330],)).fetchone()[0], 1.19)
    check("un seul principal par déclinaison",
          conn.execute("SELECT COUNT(*) FROM mp_matiere_prix WHERE declinaison_id=? AND principal=1",
                       (dl["id"],)).fetchone()[0], 1)

    print("\n--- coût produit : les prix MyStock font foi ---")
    MP.set_appairage(conn, declinaison_id=dl["id"], mc_material_id=9)
    conn.commit()
    produit = PricingProduct(id=1, code="P1", name="Produit test", frontal_id=9, adhesif_id=1)
    cout = compute_product_cost(produit, fetch_materials_map(conn, {9, 1}, require_active=True),
                                reglages)
    check("coût = frontal MyStock + adhésif MyStock",
          float(cout.total_eur_per_m2), round(1.19 + 2.70 * 0.028, 4))
    MP.set_prix(conn, declinaison_id=dl["id"], fournisseur_id=f["Meltavis"], prix=1.55,
                user_name="Test")
    conn.commit()
    cout = compute_product_cost(produit, fetch_materials_map(conn, {9, 1}, require_active=True),
                                reglages)
    check("une modification MyStock se voit sans recopie",
          float(cout.total_eur_per_m2), round(1.55 + 2.70 * 0.028, 4))

    print("\n--- garde-fous ---")
    check("prix négatif refusé",
          MP.set_prix(conn, declinaison_id=d22["id"], fournisseur_id=None, prix=-1)["ok"], False)
    check("retrait du principal refusé quand d'autres lignes existent",
          MP.delete_ligne(conn, declinaison_id=dl["id"], fournisseur_id=f["Meltavis"])["ok"], False)

    print("\n--- création, duplication, suppression ---")
    r = MP.add_declinaison(conn, matiere_id=1)
    conn.commit()
    check("déclinaison créée sans valeur", r["ok"], True)
    check("une ligne de prix est amorcée",
          conn.execute("SELECT COUNT(*) FROM mp_matiere_prix WHERE declinaison_id=?",
                       (r["declinaison_id"],)).fetchone()[0], 1)
    check("refus d'une seconde déclinaison vide",
          MP.add_declinaison(conn, matiere_id=1)["ok"], False)
    check("saisie du grammage dans la ligne",
          MP.set_declinaison_valeur(conn, declinaison_id=r["declinaison_id"], valeur_gsm=40)["ok"],
          True)
    conn.commit()
    check("refus d'une valeur déjà déclinée",
          MP.set_declinaison_valeur(conn, declinaison_id=r["declinaison_id"], valeur_gsm=22)["ok"],
          False)
    MP.set_fournisseur(conn, declinaison_id=r["declinaison_id"], fournisseur_id=None,
                       nouveau_fournisseur_id=f["Jaour"])
    conn.commit()
    check("duplication de la ligne",
          MP.dupliquer_ligne(conn, declinaison_id=r["declinaison_id"],
                             fournisseur_id=f["Jaour"])["ok"], True)
    conn.commit()
    check("refus d'une seconde ligne sans fournisseur",
          MP.dupliquer_ligne(conn, declinaison_id=r["declinaison_id"],
                             fournisseur_id=f["Jaour"])["ok"], False)
    MP.delete_ligne(conn, declinaison_id=r["declinaison_id"], fournisseur_id=None)
    res = MP.delete_ligne(conn, declinaison_id=r["declinaison_id"], fournisseur_id=f["Jaour"])
    conn.commit()
    check("suppression de la dernière ligne acceptée", res["ok"], True)
    check("la déclinaison part avec", res.get("declinaison_supprimee"), True)

    print("\n--- migrations rejouables ---")
    avant = conn.execute("SELECT COUNT(*) FROM mp_matiere_declinaison").fetchone()[0]
    with contextlib.redirect_stdout(io.StringIO()):
        dbmod._migrate(conn)
    check("aucun doublon créé",
          conn.execute("SELECT COUNT(*) FROM mp_matiere_declinaison").fetchone()[0], avant)

os.unlink(db)
print()
print("ECHECS : " + ", ".join(ECHECS) if ECHECS else "TOUT EST VERT")
sys.exit(1 if ECHECS else 0)
