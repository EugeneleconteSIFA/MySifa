# -*- coding: utf-8 -*-
"""
Le tarif quitte la déclinaison pour rejoindre le fournisseur.

Ce test porte sur la migration `mc_tarif_fournisseur` : ce qu'elle crée, ce
qu'elle reprend, et surtout ce qu'elle refuse de deviner. Une migration de
reprise se juge sur un critère simple — aucun coût ne doit bouger le jour du
déploiement — et sur un second, moins évident : elle doit dire tout haut les
cas qu'elle a tranchés à notre place.

Lancer : python3 tests/test_tarif_fournisseur.py
"""

import importlib.util
import io
import sqlite3
import sys
from contextlib import redirect_stdout
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
MIGRATION = RACINE / "app/core/migrations/2026_08_06_tarif_fournisseur.py"

ECHECS = []


def check(libelle, valeur, attendu):
    ok = valeur == attendu
    if not ok:
        ECHECS.append(libelle)
    print(("ok   " if ok else "KO   ") + libelle.ljust(56) + repr(valeur)
          + ("" if ok else "   attendu " + repr(attendu)))


def charger():
    spec = importlib.util.spec_from_file_location("mig_tarif", MIGRATION)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def base_jouet():
    """
    Un adhésif importé (1408) vendu par Meltavis en USD sur trois grammages,
    dont deux en forfait et un en conteneur — la divergence à trancher. Bostik
    propose un prix sur l'un d'eux sans en être le principal. Un frontal (PE80B)
    acheté à Bostik en EUR au m². Un fournisseur sans aucun prix.
    """
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(
        """
        CREATE TABLE fournisseurs_fsc (id INTEGER PRIMARY KEY, nom TEXT, actif INTEGER DEFAULT 1);
        CREATE TABLE matieres_premieres (id INTEGER PRIMARY KEY, reference TEXT,
          categorie TEXT DEFAULT 'adhesif', designation TEXT, actif INTEGER DEFAULT 1);
        -- Référentiels vides mais présents : `fetch_declinaison_complete` les
        -- joint pour composer le libellé d'une déclinaison.
        CREATE TABLE mp_laizes (id INTEGER PRIMARY KEY, valeur_mm REAL, label TEXT, ordre INTEGER);
        CREATE TABLE mp_grammages (id INTEGER PRIMARY KEY, valeur_gsm REAL, label TEXT);
        CREATE TABLE mp_matiere_declinaison (
          id INTEGER PRIMARY KEY, matiere_id INTEGER,
          laize_id INTEGER, grammage_id INTEGER, mc_material_id INTEGER,
          weight_per_m2 REAL DEFAULT 0, grammage_gsm REAL DEFAULT 0,
          perte_pct REAL DEFAULT 0, applique_marge INTEGER DEFAULT 1,
          parametre INTEGER DEFAULT 0, updated_at TEXT, updated_by_name TEXT,
          price_currency TEXT DEFAULT 'EUR',
          price_basis TEXT DEFAULT 'PER_KG', taxe_pct REAL DEFAULT 0,
          is_imported INTEGER DEFAULT 0, transport_mode TEXT DEFAULT 'AMOUNT',
          transport_unit_price REAL DEFAULT 0, transport_pct REAL DEFAULT 0,
          transport_cout REAL DEFAULT 0, transport_quantite REAL DEFAULT 0);
        CREATE TABLE mp_matiere_prix (
          id INTEGER PRIMARY KEY, declinaison_id INTEGER, fournisseur_id INTEGER,
          prix REAL, principal INTEGER DEFAULT 0);

        INSERT INTO fournisseurs_fsc (id,nom) VALUES (1,'Meltavis'),(2,'Bostik'),(3,'Sans prix');
        INSERT INTO matieres_premieres (id,reference,designation,categorie) VALUES
          (10,'1408','Adhésif enlevable fort','adhesif'),
          (11,'PE80B','Frontal PE blanc 80 µ','frontal');

        INSERT INTO mp_matiere_declinaison
          (id,matiere_id,price_currency,transport_mode,transport_cout,transport_quantite,taxe_pct,is_imported)
          VALUES (90,10,'USD','FORFAIT',150,260,6,1),
                 (91,10,'USD','FORFAIT',150,260,6,1),
                 (92,10,'USD','CONTENEUR',4800,18000,6,1);
        INSERT INTO mp_matiere_declinaison
          (id,matiere_id,price_currency,price_basis,transport_mode,transport_unit_price)
          VALUES (93,11,'EUR','PER_M2','AMOUNT',0.01);

        INSERT INTO mp_matiere_prix (declinaison_id,fournisseur_id,prix,principal) VALUES
          (90,1,4.2,1), (90,2,3.7,0), (91,1,4.2,1), (92,1,4.2,1),
          (93,2,0.24,1), (93,NULL,0,0);
        """
    )
    return c


def appliquer(mod, conn):
    """Applique la migration en capturant son message de démarrage."""
    sortie = io.StringIO()
    with redirect_stdout(sortie):
        mod.appliquer(conn)
    return sortie.getvalue()


def main():
    mod = charger()

    print("--- ce que la migration met en place ---")
    c = base_jouet()
    message = appliquer(mod, c)
    tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    check("la table des tarifs existe", "mc_tarif_fournisseur" in tables, True)
    cols_f = {r[1] for r in c.execute("PRAGMA table_info(fournisseurs_fsc)")}
    check("la devise est montée au fournisseur", "price_currency" in cols_f, True)
    cols_t = {r[1] for r in c.execute("PRAGMA table_info(mc_tarif_fournisseur)")}
    for champ in mod._CHAMPS_TARIF:
        check("le tarif porte " + champ, champ in cols_t, True)
    check("la devise n'est PAS dans le tarif", "price_currency" in cols_t, False)

    print("\n--- la reprise : un tarif par couple fournisseur × matière ---")
    tarifs = {
        (r["fournisseur_id"], r["matiere_id"]): dict(r)
        for r in c.execute("SELECT * FROM mc_tarif_fournisseur")
    }
    check("trois couples repris", len(tarifs), 3)
    check("Meltavis × 1408 existe", (1, 10) in tarifs, True)
    check("Bostik × PE80B existe", (2, 11) in tarifs, True)
    check("le fournisseur sans prix n'a pas de tarif",
          any(f == 3 for f, _ in tarifs), False)
    check("les réglages sont ceux de la déclinaison",
          (tarifs[(1, 10)]["transport_mode"], tarifs[(1, 10)]["transport_cout"]),
          ("FORFAIT", 150.0))
    check("la base de prix suit la matière",
          tarifs[(2, 11)]["price_basis"], "PER_M2")

    print("\n--- la devise ne se contamine pas ---")
    # Bostik vend sur une déclinaison réglée en USD pour Meltavis. Compter
    # toutes ses lignes le ferait basculer en USD sans aucune raison : seules
    # les lignes où il est principal comptent.
    devises = {r["nom"]: r["price_currency"]
               for r in c.execute("SELECT nom, price_currency FROM fournisseurs_fsc")}
    check("Meltavis passe en USD", devises["Meltavis"], "USD")
    check("Bostik reste en EUR", devises["Bostik"], "EUR")
    check("un fournisseur sans prix garde le défaut", devises["Sans prix"], "EUR")

    print("\n--- ce qui a été tranché est annoncé ---")
    # Meltavis × 1408 était en forfait sur deux grammages et en conteneur sur un
    # troisième : le tarif est unique, il a fallu choisir.
    check("la divergence est signalée", "ATTENTION" in message, True)
    check("et comptée", "1 couple(s)" in message, True)
    check("le tarif retenu est celui du principal",
          tarifs[(1, 10)]["transport_mode"], "FORFAIT")

    print("\n--- rejouable, comme toute migration ---")
    appliquer(mod, c)
    check("aucun doublon au second passage",
          c.execute("SELECT COUNT(*) FROM mc_tarif_fournisseur").fetchone()[0], 3)
    check("la devise ne rebascule pas",
          c.execute("SELECT price_currency FROM fournisseurs_fsc WHERE id=2").fetchone()[0],
          "EUR")

    print("\n--- base fraîche : rien à reprendre, pas de plantage ---")
    # L'ordre des migrations ne garantit pas que les déclinaisons existent déjà.
    vierge = sqlite3.connect(":memory:")
    vierge.row_factory = sqlite3.Row
    vierge.executescript("CREATE TABLE fournisseurs_fsc (id INTEGER PRIMARY KEY, nom TEXT);")
    try:
        msg = appliquer(mod, vierge)
        check("la migration passe quand même", "rien à reprendre" in msg, True)
    except Exception as e:  # noqa: BLE001
        check("la migration passe quand même", f"exception : {e}", True)

    print("\n--- devise indécidable : on ne tire pas à pile ou face ---")
    # Un fournisseur principal sur deux déclinaisons, une en EUR une en USD :
    # rien ne permet de trancher, et se tromper changerait un prix de 12 %.
    c2 = base_jouet()
    c2.execute("UPDATE mp_matiere_prix SET principal=1 WHERE declinaison_id=90 AND fournisseur_id=2")
    c2.execute("UPDATE mp_matiere_prix SET principal=0 WHERE declinaison_id=90 AND fournisseur_id=1")
    msg2 = appliquer(mod, c2)
    check("Bostik reste au défaut",
          c2.execute("SELECT price_currency FROM fournisseurs_fsc WHERE id=2").fetchone()[0],
          "EUR")
    check("et l'indécision est dite", "sans devise majoritaire" in msg2, True)

    print("\n--- le calcul lit le tarif de la ligne, pas celui de la déclinaison ---")
    calcul(mod)

    print("\n--- écrire un tarif ---")
    ecriture(mod)

    print("\n" + ("TOUT EST VERT" if not ECHECS else "ECHECS : " + ", ".join(ECHECS)))
    return 0 if not ECHECS else 1


def ecriture(mod):
    """
    `set_tarif` : validation, création, et surtout propagation.

    Changer un transport ne touche aucun prix d'achat, mais déplace le sous-total
    de chaque déclinaison où ce fournisseur fait foi. Si ça ne redescend pas dans
    la valorisation MyStock, l'écart se constate sans jamais s'expliquer — le
    défaut qu'on passe cette refonte à corriger.
    """
    if str(RACINE) not in sys.path:
        sys.path.insert(0, str(RACINE))
    from app.services import mystock_prix as mpx

    c = base_jouet()
    # `journaliser_prix` et `_mirror_principal` écrivent dans des tables qui
    # n'existent pas dans la base jouet : on les neutralise pour tester ce qui
    # nous intéresse ici, la propagation elle-même.
    touche = []
    mpx.journaliser_prix = lambda conn, **kw: touche.append(kw)
    mpx._mirror_principal = lambda conn, decl_id, **kw: {"ok": True}
    appliquer(mod, c)

    print("  · ce qui est refusé")
    for patch, motif in (
        ({"price_basis": "PER_TONNE"}, "base inconnue"),
        ({"transport_mode": "AVION"}, "méthode inconnue"),
        ({"taxe_pct": 5000}, "taxe hors limites"),
        ({"transport_cout": -1}, "coût négatif"),
        ({}, "patch vide"),
    ):
        r = mpx.set_tarif(c, fournisseur_id=1, matiere_id=10, patch=patch)
        check("refus : " + motif, r.get("ok"), False)
    check("fournisseur inconnu",
          mpx.set_tarif(c, fournisseur_id=999, matiere_id=10,
                        patch={"taxe_pct": 1}).get("ok"), False)
    check("matière inconnue",
          mpx.set_tarif(c, fournisseur_id=1, matiere_id=999,
                        patch={"taxe_pct": 1}).get("ok"), False)

    print("  · ce qui est écrit, et ce que ça déplace")
    avant = mpx.sous_total_declinaison(c, 90)
    r = mpx.set_tarif(
        c, fournisseur_id=1, matiere_id=10,
        patch={"transport_mode": "CONTENEUR", "transport_cout": 4800,
               "transport_quantite": 18000, "taxe_pct": 6, "is_imported": True},
        user_name="Eugene",
    )
    check("le tarif est accepté", r.get("ok"), True)
    check("le mode est enregistré", r["tarif"]["transport_mode"], "CONTENEUR")
    check("l'auteur est tracé", r["tarif"]["updated_by_name"], "Eugene")
    # Meltavis est principal sur les trois grammages de 1408 : les trois bougent.
    check("les déclinaisons pilotées suivent", r["declinaisons_touchees"], 3)
    check("le sous-total a bien changé", mpx.sous_total_declinaison(c, 90) != avant, True)
    check("l'historique dit d'où ça vient",
          {k["origine"] for k in touche}, {"Coûts matières — tarif fournisseur"})

    print("  · un tarif neuf prend les défauts de sa catégorie")
    # PE80B est un frontal : laizé, donc tarifé au m² et non au kilo.
    r2 = mpx.set_tarif(c, fournisseur_id=1, matiere_id=11, patch={"taxe_pct": 0})
    check("création acceptée", r2.get("ok"), True)
    check("base déduite de la catégorie", r2["tarif"]["price_basis"], "PER_M2")
    check("et rien d'autre n'est facturé", r2["tarif"]["transport_mode"], "AMOUNT")

    print("  · un fournisseur secondaire ne pousse rien")
    touche.clear()
    r3 = mpx.set_tarif(c, fournisseur_id=2, matiere_id=10, patch={"taxe_pct": 12})
    check("le tarif est bien écrit", r3.get("ok"), True)
    # Bostik n'est principal nulle part sur 1408 : son coût change à l'écran,
    # mais rien ne part dans la valorisation.
    check("aucune déclinaison touchée", r3["declinaisons_touchees"], 0)
    check("et aucun historique", touche, [])

    print("  · la devise")
    check("devise inconnue refusée",
          mpx.set_devise_fournisseur(c, fournisseur_id=2, devise="CHF").get("ok"), False)
    check("devise acceptée",
          mpx.set_devise_fournisseur(c, fournisseur_id=2, devise="usd").get("price_currency"),
          "USD")
    check("fournisseur inconnu refusé",
          mpx.set_devise_fournisseur(c, fournisseur_id=999, devise="EUR").get("ok"), False)

    print("  · les deux vues, fournisseur et matière")
    par_f = mpx.tarifs_du_fournisseur(c, 1)
    # 1408 (où il a des prix) et PE80B (où on vient de lui poser un tarif sans
    # prix). Un tarif enregistré d'avance doit rester visible, sinon il n'est
    # jamais corrigé.
    check("Meltavis : deux matières listées", len(par_f), 2)
    check("dont celle sans prix", sorted(x["reference"] for x in par_f), ["1408", "PE80B"])
    check("le compteur de déclinaisons suit",
          {x["reference"]: x["nb_declinaisons"] for x in par_f}, {"1408": 3, "PE80B": 0})
    check("chacune dit si elle a un tarif", all("a_tarif" in x for x in par_f), True)
    par_m = mpx.fournisseurs_de_la_matiere(c, 10)
    check("1408 a deux fournisseurs", len(par_m), 2)
    check("le principal est en tête", par_m[0]["nom"], "Meltavis")
    check("avec sa devise", par_m[0]["price_currency"], "USD")

    print("  · base non migrée : on refuse proprement")
    vieille = base_jouet()
    check("écriture refusée sans table",
          mpx.set_tarif(vieille, fournisseur_id=1, matiere_id=10,
                        patch={"taxe_pct": 1}).get("ok"), False)
    check("et les vues restent vides", mpx.tarifs_du_fournisseur(vieille, 1), [])


def calcul(mod):
    """
    Le point de bascule : deux fournisseurs sur la MÊME déclinaison, avec des
    tarifs différents, doivent produire deux sous-totaux différents.

    Avant, transport et taxes venaient de la déclinaison : les deux sortaient le
    même sous-total à un rapport de prix près, et ajouter un second fournisseur
    pour comparer ne servait à rien.
    """
    if str(RACINE) not in sys.path:
        sys.path.insert(0, str(RACINE))
    from app.services import mystock_prix as mpx

    c = base_jouet()
    appliquer(mod, c)
    # Meltavis importe par conteneur ; Bostik livre en local, sans transport ni
    # taxe. Deux tarifs, une seule déclinaison (le 17 g/m², id 90).
    c.execute(
        """UPDATE mc_tarif_fournisseur
              SET transport_mode='CONTENEUR', transport_cout=4800,
                  transport_quantite=18000, taxe_pct=6, is_imported=1
            WHERE fournisseur_id=1 AND matiere_id=10"""
    )
    c.execute(
        """UPDATE mc_tarif_fournisseur
              SET transport_mode='AMOUNT', transport_unit_price=0,
                  transport_cout=0, transport_quantite=0, taxe_pct=0, is_imported=0
            WHERE fournisseur_id=2 AND matiere_id=10"""
    )

    decl = c.execute("SELECT * FROM mp_matiere_declinaison WHERE id=90").fetchone()

    t_meltavis = mpx.fetch_tarif(c, 1, 10)
    t_bostik = mpx.fetch_tarif(c, 2, 10)
    check("le tarif de Meltavis est trouvé", t_meltavis["transport_mode"], "CONTENEUR")
    check("celui de Bostik aussi", t_bostik["transport_mode"], "AMOUNT")

    st_meltavis = mpx.sous_total_achat(4.2, **mpx.reglages_ligne(decl, t_meltavis))
    st_bostik = mpx.sous_total_achat(3.7, **mpx.reglages_ligne(decl, t_bostik))
    # 4,20 + 4800/18000 = 4,4667, puis +6 % de taxe = 4,7347
    check("Meltavis : conteneur puis taxe", round(st_meltavis, 4), 4.7347)
    check("Bostik : ni transport ni taxe", round(st_bostik, 4), 3.7)
    check("les deux sous-totaux diffèrent vraiment",
          abs(st_meltavis - st_bostik) > 0.5, True)

    print("\n  · le principal fait foi pour la déclinaison")
    check("le sous-total de la déclinaison est celui du principal",
          round(mpx.sous_total_declinaison(c, 90), 4), 4.7347)
    # On bascule le principal sur Bostik : le sous-total doit suivre le tarif de
    # Bostik, pas seulement son prix. C'est le comportement voulu.
    c.execute("UPDATE mp_matiere_prix SET principal=0 WHERE declinaison_id=90")
    c.execute("UPDATE mp_matiere_prix SET principal=1 WHERE declinaison_id=90 AND fournisseur_id=2")
    check("changer de principal change aussi le tarif appliqué",
          round(mpx.sous_total_declinaison(c, 90), 4), 3.7)

    print("\n  · le repli quand il n'y a pas de tarif")
    # Une ligne sans fournisseur ne peut pas avoir de tarif : elle retombe sur
    # les colonnes de la déclinaison, qui valent encore forfait 150/260 + 6 %.
    check("sans fournisseur, on lit la déclinaison",
          mpx.reglages_ligne(decl, None)["transport_mode"], "FORFAIT")
    check("et le tarif absent se voit", mpx.fetch_tarif(c, 3, 10), None)

    print("\n  · devise et base de prix")
    devises = mpx.devises_fournisseurs(c)
    check("Meltavis facture en USD", mpx.devise_ligne(c, decl, 1, devises), "USD")
    check("Bostik en EUR", mpx.devise_ligne(c, decl, 2, devises), "EUR")
    check("sans fournisseur, la déclinaison décide",
          mpx.devise_ligne(c, decl, None, devises), "USD")
    check("la base vient du tarif", mpx.base_prix_ligne(decl, t_meltavis), "PER_KG")

    print("\n  · base non migrée : rien ne tombe")
    # v1 tourne avec les migrations désactivées : la table n'existe pas, tout
    # doit continuer sur les anciennes colonnes.
    vieille = base_jouet()
    check("pas de table de tarifs", mpx.tarifs_disponibles(vieille), False)
    check("aucun tarif chargé", mpx.charger_tarifs(vieille), {})
    d90 = vieille.execute("SELECT * FROM mp_matiere_declinaison WHERE id=90").fetchone()
    check("le calcul retombe sur la déclinaison",
          mpx.reglages_ligne(d90, mpx.fetch_tarif(vieille, 1, 10))["transport_mode"],
          "FORFAIT")


if __name__ == "__main__":
    raise SystemExit(main())
