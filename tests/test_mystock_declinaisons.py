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
    # Sa taxe de -5 % ne compte plus : la matière n'est pas marquée importée, et
    # une taxe d'importation ne s'applique qu'à ce qui est importé.
    check("garde son prix propre",
          float(compute_material_price_per_m2(row_to_pricing_material(row10), reglages)
                .price_eur_per_m2), 4.0183)

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

    print("\n--- MyStock -> Coûts matières : le sens retour ---")
    # Un prix corrigé dans MyStock (valorisation, fiche matière, PMP) doit
    # redescendre dans la ligne principale que Coûts matières interroge.
    def _principal(decl_id):
        return conn.execute(
            "SELECT prix FROM mp_matiere_prix WHERE declinaison_id=? AND principal=1",
            (decl_id,),
        ).fetchone()[0]

    dl500 = next(d for d in mats["F70"]["declinaisons"] if "500" in d["libelle"])
    conn.execute("UPDATE mp_matiere_laizes SET prix_eur_m2=1.62 WHERE matiere_id=2 AND laize_id=?",
                 (laize[330],))
    conn.commit()
    r = MP.resync_depuis_mystock(conn, 2, user_name="MyStock")
    conn.commit()
    check("le tarif de la laize suit MyStock", _principal(dl["id"]), 1.62)
    check("la laize voisine n'est pas touchée", _principal(dl500["id"]), 1.45)
    check("une seule ligne modifiée", r["mises_a_jour"], 1)
    check("rien à refaire au second passage",
          MP.resync_depuis_mystock(conn, 2)["mises_a_jour"], 0)

    # Un zéro côté MyStock veut dire « pas renseigné », pas « gratuit » : il ne
    # doit jamais effacer un tarif connu.
    conn.execute("UPDATE mp_matiere_laizes SET prix_eur_m2=0 WHERE matiere_id=2 AND laize_id=?",
                 (laize[330],))
    conn.commit()
    MP.resync_depuis_mystock(conn, 2)
    conn.commit()
    check("un prix vide n'efface pas le tarif", _principal(dl["id"]), 1.62)
    conn.execute("UPDATE mp_matiere_laizes SET prix_eur_m2=1.62 WHERE matiere_id=2 AND laize_id=?",
                 (laize[330],))
    conn.commit()

    # Matière non laizée : MyStock ne tient qu'un prix, toutes ses déclinaisons
    # le suivent.
    conn.execute("UPDATE mp_valorisation SET prix_unitaire=2.95 WHERE matiere_id=1")
    conn.commit()
    MP.resync_depuis_mystock(conn, 1, user_name="MyStock")
    conn.commit()
    check("le grammage appairé suit", _principal(d22["id"]), 2.95)
    check("les autres grammages aussi", _principal(d30["id"]), 2.95)

    # Le sens retour lit MyStock, il n'y réécrit rien : pas d'aller-retour.
    check("MyStock n'est pas réécrit au passage",
          conn.execute("SELECT prix_unitaire FROM mp_valorisation WHERE matiere_id=1")
          .fetchone()[0], 2.95)
    check("ni le prix de la laize",
          conn.execute("SELECT prix_eur_m2 FROM mp_matiere_laizes WHERE matiere_id=2 AND laize_id=?",
                       (laize[330],)).fetchone()[0], 1.62)

    cout = compute_product_cost(produit, fetch_materials_map(conn, {9, 1}, require_active=True),
                                reglages)
    check("le coût produit repart sur les prix MyStock",
          float(cout.total_eur_per_m2), round(1.62 + 2.95 * 0.028, 4))

    # Les trois écrans MyStock qui écrivent un prix doivent appeler ce retour,
    # sinon la correction reste invisible côté Coûts matières.
    _stock = io.open(RACINE / "app/routers/stock.py", encoding="utf-8").read()
    check("les écrans MyStock déclenchent le retour",
          _stock.count("_mystock_prix.resync_depuis_mystock("), 3)

    print("\n--- paramétrage porté par la déclinaison ---")
    from app.services.pricing.repository import declinaison_to_pricing_material  # noqa: E402

    def cout(decl_id):
        return float(compute_material_price_per_m2(
            declinaison_to_pricing_material(MP.parametrage(conn, decl_id)), reglages
        ).price_eur_per_m2)

    p22 = MP.parametrage(conn, d22["id"])
    check("un adhésif part au kilo", p22["price_basis"], "PER_KG")
    check("poids déduit du grammage déclaré", p22["weight_per_m2"], 0.022)
    check("tant que personne n'a réglé la fiche", p22["parametre"], False)
    check("le prix du fournisseur principal remonte", p22["unit_price"], 2.95)
    check("libellé de la déclinaison", p22["libelle"], "22 g/m²")
    check("coût au m² sans passer par une fiche", cout(d22["id"]), round(2.95 * 0.022, 4))

    p500 = MP.parametrage(conn, dl500["id"])
    check("une laize non appairée part au m²", p500["price_basis"], "PER_M2")
    check("et reste à paramétrer", p500["parametre"], False)
    check("un prix au m² ignore le poids", cout(dl500["id"]), 1.45)

    # Un grammage EST un poids : le saisir suffit, on ne le redemande pas. Une
    # déclinaison neuve part avec la perte par défaut (9 %), les anciennes ont
    # été reprises à 0 pour ne pas renchérir les prix existants.
    r35 = MP.add_declinaison(conn, matiere_id=1, valeur_gsm=35)
    conn.commit()
    p35 = MP.parametrage(conn, r35["declinaison_id"])
    check("le grammage est repris tel quel", p35["grammage_gsm"], 35.0)
    check("perte par défaut sur une nouvelle déclinaison", p35["perte_pct"], MP.PERTE_DEFAUT)
    check("le poids retenu inclut la perte", p35["weight_per_m2"], round(35 * 1.09 / 1000, 6))
    check("les anciennes déclinaisons gardent une perte nulle", p22["perte_pct"], 0.0)

    print("\n--- édition des réglages ---")
    check("devise inconnue refusée",
          MP.set_parametrage(conn, declinaison_id=d22["id"],
                             patch={"price_currency": "GBP"})["ok"], False)
    check("perte au-delà de 100 % refusée",
          MP.set_parametrage(conn, declinaison_id=d22["id"],
                             patch={"perte_pct": 150})["ok"], False)
    check("base de prix inconnue refusée",
          MP.set_parametrage(conn, declinaison_id=d22["id"],
                             patch={"price_basis": "PER_M3"})["ok"], False)
    check("grammage négatif refusé",
          MP.set_parametrage(conn, declinaison_id=d22["id"],
                             patch={"grammage_gsm": -1})["ok"], False)
    check("déclinaison inexistante refusée",
          MP.set_parametrage(conn, declinaison_id=999999,
                             patch={"grammage_gsm": 1})["ok"], False)
    check("un patch vide ne fait rien",
          MP.set_parametrage(conn, declinaison_id=d22["id"], patch={})["ok"], False)

    # Import en USD avec transport au pourcentage : (prix + transport) × taux.
    MP.set_parametrage(conn, declinaison_id=d22["id"], patch={
        "price_currency": "USD", "is_imported": True, "taxe_pct": 6,
        "transport_mode": "PCT", "transport_pct": 10,
        "grammage_gsm": 30, "perte_pct": 0,
    }, user_name="Test")
    conn.commit()
    p22 = MP.parametrage(conn, d22["id"])
    check("devise enregistrée", p22["price_currency"], "USD")
    check("transport en pourcentage enregistré", p22["transport_pct"], 10.0)
    check("taxe en pourcentage enregistrée", p22["taxe_pct"], 6.0)
    check("le poids découle du grammage", p22["weight_per_m2"], 0.03)
    check("auteur tracé", p22["updated_by_name"], "Test")
    attendu = round(2.95 * 1.10 * 1.06 * 0.03 * float(reglages.eur_usd_rate), 4)
    check("coût = (prix + transport + taxes) × devise × poids", cout(d22["id"]), attendu)

    # Une taxe sur une matière qui n'est plus importée ne doit pas continuer à
    # gonfler le prix en douce : le champ n'est même plus visible.
    MP.set_parametrage(conn, declinaison_id=d22["id"], patch={"is_imported": False})
    conn.commit()
    check("taxe ignorée hors import",
          cout(d22["id"]), round(2.95 * 0.03 * float(reglages.eur_usd_rate), 4))

    # Les réglages sont propres à chaque déclinaison : 22 en USD ne déteint pas
    # sur 30, qui est la même matière MyStock.
    check("l'autre grammage garde ses réglages",
          MP.parametrage(conn, d30["id"])["price_currency"], "EUR")

    MP.set_parametrage(conn, declinaison_id=d22["id"], patch={
        "price_currency": "EUR", "is_imported": False, "taxe_pct": 0,
        "transport_mode": "AMOUNT", "transport_pct": 0,
        "grammage_gsm": 28, "perte_pct": 0,
    })
    conn.commit()

    print("\n--- reprise des fiches déjà appairées (migration) ---")
    # Sur la vraie base, des déclinaisons sont appairées depuis des semaines :
    # elles doivent hériter des réglages de leur fiche, pas repartir de zéro.
    import importlib  # noqa: E402

    mig = importlib.import_module("app.core.migrations.2026_08_04_declinaison_parametrage")
    old = sqlite3.connect(":memory:")
    old.row_factory = sqlite3.Row
    old.executescript("""
        CREATE TABLE matieres_premieres (id INTEGER PRIMARY KEY, categorie TEXT);
        CREATE TABLE mp_grammages (id INTEGER PRIMARY KEY, valeur_gsm REAL);
        CREATE TABLE mc_material (id INTEGER PRIMARY KEY, weight_per_m2 REAL, weight_gsm INTEGER,
            price_currency TEXT, price_basis TEXT, tax_incidence REAL, is_imported INTEGER,
            transport_mode TEXT, transport_unit_price REAL, transport_pct REAL);
        CREATE TABLE mp_laizes (id INTEGER PRIMARY KEY, valeur_mm REAL);
        CREATE TABLE mp_matiere_declinaison (id INTEGER PRIMARY KEY, matiere_id INTEGER,
            laize_id INTEGER, grammage_id INTEGER, mc_material_id INTEGER);
        INSERT INTO matieres_premieres VALUES (1,'adhesif'), (2,'frontal');
        INSERT INTO mp_grammages VALUES (1, 25);
        INSERT INTO mc_material VALUES (7, 0.031, 31, 'USD', 'PER_KG', 1.065, 1, 'PCT', 0, 12);
        INSERT INTO mp_laizes VALUES (5, 330);
        INSERT INTO mp_matiere_declinaison VALUES (1, 1, NULL, 1, 7);
        INSERT INTO mp_matiere_declinaison VALUES (2, 2, 5, NULL, NULL);
    """)
    mig.appliquer(old)
    reprise = old.execute("SELECT * FROM mp_matiere_declinaison WHERE id=1").fetchone()
    libre = old.execute("SELECT * FROM mp_matiere_declinaison WHERE id=2").fetchone()
    check("poids repris de la fiche", reprise["weight_per_m2"], 0.031)
    check("devise reprise", reprise["price_currency"], "USD")
    check("incidence taxes reprise", reprise["tax_incidence"], 1.065)
    mig_taxe = importlib.import_module("app.core.migrations.2026_08_04_taxe_marge_grammage")
    mig_taxe.appliquer(old)
    reprise = old.execute("SELECT * FROM mp_matiere_declinaison WHERE id=1").fetchone()
    check("multiplicateur converti en pourcentage", reprise["taxe_pct"], 6.5)
    check("marge appliquée par défaut", reprise["applique_marge"], 1)
    check("grammage repris depuis le poids", reprise["grammage_gsm"], 31.0)
    check("perte remise à zéro pour ne rien renchérir", reprise["perte_pct"], 0.0)
    check("import repris", reprise["is_imported"], 1)
    check("transport en pourcentage repris", reprise["transport_pct"], 12.0)
    check("la fiche appairée compte comme paramétrée", reprise["parametre"], 1)
    check("une laize sans fiche part au m²", libre["price_basis"], "PER_M2")
    check("et reste à paramétrer", libre["parametre"], 0)
    mig.appliquer(old)
    check("migration rejouable sans dégât",
          old.execute("SELECT weight_per_m2 FROM mp_matiere_declinaison WHERE id=1").fetchone()[0],
          0.031)
    old.close()

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

    print("\n--- produits devisés depuis MyStock ---")
    from app.services import mystock_produits as PROD  # noqa: E402

    compo = [
        {"declinaison_id": dl["id"], "role": "FRONTAL"},
        {"declinaison_id": d22["id"], "role": "ADHESIF"},
    ]
    r = PROD.creer_produit(conn, code="MS-1", designation="Étiquette test",
                           composants=compo, user_name="Test")
    conn.commit()
    check("produit créé", r["ok"], True)
    prod = r["produit"]
    check("les deux composants sont enregistrés", len(prod["composants"]), 2)
    check("le libellé de la déclinaison suit",
          sorted(c["libelle"] for c in prod["composants"]), ["22 g/m²", "330 mm"])

    c = PROD.cout_produit(conn, prod, reglages)
    attendu = round(1.62 + 2.95 * 0.028, 4)
    check("coût = somme des déclinaisons", float(c.total_eur_per_m2), attendu)
    check("un composant par rôle", sorted(x.role for x in c.components), ["adhesif", "frontal"])
    check("les parts font 100 %", float(sum(x.share_pct for x in c.components)), 100.0)
    check("marge par défaut appliquée",
          float(c.margin_pct), float(reglages.default_margin_pct))

    print("\n--- garde-fous du produit ---")
    check("code déjà pris refusé",
          PROD.creer_produit(conn, code="ms-1", designation="Doublon")["ok"], False)
    check("code vide refusé",
          PROD.creer_produit(conn, code="  ", designation="X")["ok"], False)
    check("désignation vide refusée",
          PROD.creer_produit(conn, code="MS-2", designation="")["ok"], False)
    check("deux matières pour le même rôle refusées",
          PROD.creer_produit(conn, code="MS-3", designation="X", composants=[
              {"declinaison_id": dl["id"], "role": "FRONTAL"},
              {"declinaison_id": dl500["id"], "role": "FRONTAL"},
          ])["ok"], False)
    check("la même déclinaison deux fois refusée",
          PROD.creer_produit(conn, code="MS-4", designation="X", composants=[
              {"declinaison_id": dl["id"], "role": "FRONTAL"},
              {"declinaison_id": dl["id"], "role": "AUTRE"},
          ])["ok"], False)
    check("déclinaison inexistante refusée",
          PROD.creer_produit(conn, code="MS-5", designation="X", composants=[
              {"declinaison_id": 999999, "role": "FRONTAL"},
          ])["ok"], False)
    check("rôle inconnu refusé",
          PROD.creer_produit(conn, code="MS-6", designation="X", composants=[
              {"declinaison_id": dl["id"], "role": "CARTON"},
          ])["ok"], False)
    check("marge hors limites refusée",
          PROD.creer_produit(conn, code="MS-7", designation="X",
                             custom_margin_pct=5000)["ok"], False)

    print("\n--- édition complète du produit ---")
    m = PROD.modifier_produit(conn, prod["id"], patch={
        "custom_margin_pct": 12,
        "composants": compo + [{"declinaison_id": dl500["id"], "role": "AUTRE"}],
    }, user_name="Test")
    conn.commit()
    check("modification acceptée", m["ok"], True)
    prod2 = m["produit"]
    check("une matière libre s'ajoute", len(prod2["composants"]), 3)
    c2 = PROD.cout_produit(conn, prod2, reglages)
    check("le coût suit la nouvelle composition",
          float(c2.total_eur_per_m2), round(attendu + 1.45, 4))
    check("la marge du produit prend le pas", float(c2.margin_pct), 12.0)
    check("prix de vente = revient + marge", float(c2.sell_price_eur_m2),
          round(float(c2.total_eur_per_m2) * 1.12, 4))

    # Se réattribuer son propre code doit passer : la garde d'unicité exclut le
    # produit qu'on est en train de modifier.
    check("un produit garde son propre code",
          PROD.modifier_produit(conn, prod["id"], patch={"code": "MS-1"})["ok"], True)
    r8 = PROD.creer_produit(conn, code="MS-8", designation="Autre")
    conn.commit()
    check("un autre produit ne peut pas prendre ce code",
          PROD.modifier_produit(conn, r8["produit"]["id"], patch={"code": "MS-1"})["ok"], False)
    check("patch vide refusé",
          PROD.modifier_produit(conn, prod["id"], patch={})["ok"], False)
    check("produit inconnu refusé",
          PROD.modifier_produit(conn, 999999, patch={"designation": "X"})["ok"], False)

    check("désactivation", PROD.supprimer_produit(conn, r8["produit"]["id"])["ok"], True)
    conn.commit()
    check("le produit désactivé sort de la liste",
          [p["code"] for p in PROD.list_produits(conn)], ["MS-1"])
    check("mais reste consultable",
          PROD.get_produit(conn, r8["produit"]["id"])["actif"], False)
    check("recherche par code", len(PROD.list_produits(conn, q="MS-1")), 1)
    check("recherche sans résultat", len(PROD.list_produits(conn, q="zzz")), 0)

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
