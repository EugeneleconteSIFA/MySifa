"""Jeu de démonstration de l'ERP : peu de lignes, mais une vraie chaîne.

Sociétés et articles fictifs. Tout ce qui est créé ici porte
`origine='demo'` et c'est la seule chose que `reinitialiser` efface : une
donnée saisie à la main (origine 'erp') ou reprise de RVGI n'est jamais
touchée. Les pièces passent par le moteur (`pieces.py`), comme une saisie :
numéros, stock, échéances et états sont ceux qu'aurait produits l'ADV.
"""
from __future__ import annotations

from datetime import date, timedelta

from app.services.gc import fichiers, pieces

CLIENTS = [
    # code, raison sociale, ville, cp, condition, remise_bp, tva
    ("C0001", "Domaine des Trois Collines", "Beaune", "21200", "30FM", 0, None),
    ("C0002", "Brasserie de la Vallée", "Lille", "59000", "45FM", 200, None),
    ("C0003", "Laboratoires Alvéa", "Lyon", "69007", "60J", 0, None),
    ("C0004", "Fromagerie Morvan", "Avallon", "89200", "30J", 0, None),
    ("C0005", "Weingut Halden", "Freiburg", "79098", "30J", 0, "UE"),
]
FOURNISSEURS = [
    ("F0001", "Papeteries Adhésives du Centre", "Clermont-Ferrand", "63000", "45FM"),
    ("F0002", "Films Techniques Rhône", "Vienne", "38200", "30FM"),
    ("F0003", "Encres Morel", "Orléans", "45000", "30FM"),
]
ARTICLES = [
    # code, libellé, nature, famille, unité, base, PV, PA, tva, stock
    ("PF0001", "Étiquette vin 90x120 vergé blanc", "pf", "ETQ", "ETQ", 1000, 4200, None, "N", 1),
    ("PF0002", "Étiquette bière 70x90 PP blanc", "pf", "ETQ", "ETQ", 1000, 2800, None, "N", 1),
    ("PF0003", "Étiquette pharma 35x20 couché", "pf", "ETQ", "ETQ", 1000, 1500, None, "N", 1),
    ("PF0004", "Étiquette fromage Ø80 couché brillant", "pf", "ETQ", "ETQ", 1000, 3100, None, "N", 1),
    ("MP0001", "Vergé blanc adhésif permanent 330 mm", "mp", "PAP", "ML", 1, None, 62, "N", 1),
    ("MP0002", "PP blanc 60µ adhésif 330 mm", "mp", "FIL", "ML", 1, None, 48, "N", 1),
    ("MP0003", "Couché brillant adhésif 250 mm", "mp", "PAP", "ML", 1, None, 21, "N", 1),
    ("MP0004", "Encre noire UV", "mp", "ENC", "KG", 1, None, 2850, "N", 1),
    ("PR0001", "Frais de calage", "service", "PREST", "FORF", 1, 8500, None, "N", 0),
    ("PR0002", "Création de cliché", "service", "PREST", "U", 1, 6500, None, "N", 0),
]

TABLES = ("gc_mouvements", "gc_echeances", "gc_pieces_lignes", "gc_pieces", "gc_tarifs",
          "gc_articles", "gc_tiers_contacts", "gc_tiers_adresses", "gc_tiers")


def effacer(conn) -> None:
    t = "SELECT id FROM gc_tiers WHERE origine='demo'"
    conn.execute(f"DELETE FROM gc_reglements_affectations WHERE reglement_id IN (SELECT id FROM gc_reglements WHERE tiers_id IN ({t}))")
    conn.execute(f"DELETE FROM gc_reglements WHERE tiers_id IN ({t})")
    ids = "SELECT id FROM gc_pieces WHERE origine='demo'"
    conn.execute(f"DELETE FROM gc_mouvements WHERE piece_id IN ({ids}) OR article_id IN (SELECT id FROM gc_articles WHERE origine='demo')")
    conn.execute(f"DELETE FROM gc_echeances WHERE piece_id IN ({ids})")
    conn.execute(f"DELETE FROM gc_pieces_lignes WHERE piece_id IN ({ids})")
    conn.execute("DELETE FROM gc_pieces WHERE origine='demo'")
    conn.execute("DELETE FROM gc_tarifs WHERE article_id IN (SELECT id FROM gc_articles WHERE origine='demo')")
    conn.execute("DELETE FROM gc_articles WHERE origine='demo'")
    conn.execute(f"DELETE FROM gc_tiers_contacts WHERE tiers_id IN ({t})")
    conn.execute(f"DELETE FROM gc_tiers_adresses WHERE tiers_id IN ({t})")
    conn.execute("DELETE FROM gc_tiers WHERE origine='demo'")


def _marquer(conn, piece_id: int) -> None:
    conn.execute("UPDATE gc_pieces SET origine='demo' WHERE id=?", (piece_id,))


def reinitialiser(conn, user: dict | None = None) -> dict:
    """Efface la démonstration et la recrée. Refuse s'il existe des données
    non fictives : la numérotation serait remise à zéro par-dessus."""
    autres = conn.execute("SELECT COUNT(*) n FROM gc_pieces WHERE origine!='demo'").fetchone()["n"]
    if autres:
        raise pieces.ErreurPiece(f"{autres} pièce(s) réelle(s) en base : la démonstration ne se réinitialise plus.")
    effacer(conn)
    conn.execute("UPDATE gc_sequences SET prochain=1, annee=0")
    fichiers.enregistrer_societe(conn, {
        "raison_sociale": "Société de démonstration", "forme_juridique": "SAS", "capital_cents": 10_000_000,
        "siret": "000 000 000 00000", "rcs": "RCS Démo", "tva_intra": "FR00000000000",
        "adresse1": "1 rue de l'Exemple", "code_postal": "00000", "ville": "Démoville",
        "penalites_retard": "Pénalités de retard : 3 fois le taux d'intérêt légal. "
                            "Indemnité forfaitaire pour frais de recouvrement : 40 €.",
    } if not fichiers.lire_societe(conn).get("raison_sociale") else {})

    tiers = {}
    for code, nom, ville, cp, cond, rem, tva in CLIENTS:
        tiers[code] = fichiers.enregistrer_tiers(conn, None, {
            "code": code, "est_client": 1, "raison_sociale": nom, "condition_paiement": cond,
            "mode_paiement": "VIR", "remise_bp": rem, "tva_code": tva,
            "email": "adv@" + nom.split()[-1].lower() + ".example", "encours_max_cents": 5_000_000,
        }, adresses=[
            {"type": "facturation", "libelle": "Siège", "adresse1": "12 avenue Centrale", "code_postal": cp,
             "ville": ville, "pays": "DE" if tva == "UE" else "FR", "par_defaut": 1},
            {"type": "livraison", "libelle": "Site de conditionnement", "adresse1": "ZA des Prés", "code_postal": cp,
             "ville": ville, "pays": "DE" if tva == "UE" else "FR", "par_defaut": 1},
        ], contacts=[{"nom": "Service achats", "fonction": "Acheteur", "email": "achats@exemple.example"}],
            origine="demo")
    for code, nom, ville, cp, cond in FOURNISSEURS:
        tiers[code] = fichiers.enregistrer_tiers(conn, None, {
            "code": code, "est_fournisseur": 1, "raison_sociale": nom, "condition_paiement": cond,
            "mode_paiement": "VIR",
        }, adresses=[{"type": "facturation", "libelle": "Siège", "adresse1": "3 rue de l'Industrie",
                      "code_postal": cp, "ville": ville, "par_defaut": 1}], origine="demo")

    arts = {}
    fourn = {"PAP": "F0001", "FIL": "F0002", "ENC": "F0003"}
    for code, lib, nat, fam, un, base, pv, pa, tva, st in ARTICLES:
        arts[code] = fichiers.enregistrer_article(conn, None, {
            "code": code, "libelle": lib, "nature": nat, "famille": fam, "unite": un, "base_prix": base,
            "prix_vente_cents": pv, "prix_achat_cents": pa, "tva_code": tva, "gere_stock": st,
            "fournisseur_id": tiers.get(fourn.get(fam, "")),
        }, origine="demo")
    # Tarifs négociés : un client au palier, un fournisseur
    fichiers.enregistrer_article(conn, arts["PF0001"], {}, tarifs=[
        {"tiers_id": tiers["C0001"], "sens": "vente", "qte_min_milli": 0, "prix_cents": 4000},
        {"tiers_id": tiers["C0001"], "sens": "vente", "qte_min_milli": 50_000_000, "prix_cents": 3650},
    ])
    fichiers.enregistrer_article(conn, arts["MP0001"], {}, tarifs=[
        {"tiers_id": tiers["F0001"], "sens": "achat", "qte_min_milli": 0, "prix_cents": 62},
        {"tiers_id": tiers["F0001"], "sens": "achat", "qte_min_milli": 10_000_000, "prix_cents": 55},
    ])

    j = date.today()

    def jour(n):
        return (j + timedelta(days=n)).isoformat()

    def ligne(code, qte, tiers_code, sens="vente"):
        p = pieces.prix(conn, arts[code], tiers[tiers_code], qte, sens)
        return {"article_id": arts[code], "quantite_milli": qte, "prix_cents": p["prix_cents"],
                "base_prix": p["base_prix"]}

    def nouvelle(type_p, tiers_code, lignes, date_p, **entete):
        pid = pieces.creer(conn, type_p, tiers[tiers_code], user)
        _marquer(conn, pid)
        pieces.enregistrer(conn, pid, {"date_piece": date_p, **entete}, lignes)
        return pid

    def suite(sources, cible, date_p, modif=None):
        pid = pieces.transformer(conn, sources, cible, user)
        _marquer(conn, pid)
        lignes = pieces.charger(conn, pid)["lignes"]
        if modif:
            lignes = modif(lignes)
        pieces.enregistrer(conn, pid, {"date_piece": date_p}, lignes)
        return pid

    # Stock initial : inventaire d'ouverture
    for code, q in (("PF0001", 40_000_000), ("PF0002", 15_000_000), ("PF0004", 8_000_000),
                    ("MP0001", 6_000_000), ("MP0002", 4_500_000), ("MP0003", 3_000_000), ("MP0004", 25_000)):
        fichiers.mouvement_manuel(conn, {"type": "inventaire", "article_id": arts[code], "depot": "PRINC",
                                         "quantite_milli": q, "date_mvt": jour(-40),
                                         "commentaire": "Inventaire d'ouverture"}, user)

    # Ventes
    d1 = nouvelle("devis", "C0001", [ligne("PF0001", 60_000_000, "C0001"), ligne("PR0001", 1000, "C0001")],
                  jour(-30), date_validite=jour(0))
    pieces.valider(conn, d1, user)
    c1 = suite([d1], "commande", jour(-25))
    conn.execute("UPDATE gc_pieces SET ref_tiers='BC-2026-118', date_livraison=? WHERE id=?", (jour(-10), c1))
    pieces.valider(conn, c1, user)
    b1 = suite([c1], "bl", jour(-12),
               modif=lambda ls: [dict(l, quantite_milli=35_000_000) if l["article_code"] == "PF0001" else l for l in ls])
    pieces.valider(conn, b1, user)
    f1 = suite([b1], "facture", jour(-11))
    pieces.valider(conn, f1, user)

    from app.services.gc import compta
    ech = conn.execute("SELECT id, montant_cents FROM gc_echeances WHERE piece_id=?", (f1,)).fetchone()
    compta.enregistrer_reglement(conn, {
        "tiers_id": tiers["C0001"], "sens": "encaissement", "date_reglement": jour(-3), "mode_paiement": "VIR",
        "montant_cents": 100000, "reference": "VIR DOMAINE 3 COLLINES",
        "affectations": [{"echeance_id": ech["id"], "montant_cents": 100000}]}, user)

    c2 = nouvelle("commande", "C0002", [ligne("PF0002", 12_000_000, "C0002"), ligne("PR0002", 2000, "C0002")],
                  jour(-8), ref_tiers="Cde 4471", date_livraison=jour(5))
    pieces.valider(conn, c2, user)
    b2 = suite([c2], "bl", jour(-2))
    pieces.valider(conn, b2, user)

    c3 = nouvelle("commande", "C0005", [ligne("PF0001", 20_000_000, "C0005")], jour(-3),
                  ref_tiers="PO 88123", date_livraison=jour(12))
    pieces.valider(conn, c3, user)

    nouvelle("devis", "C0003", [ligne("PF0003", 100_000_000, "C0003"), ligne("PR0002", 3000, "C0003")],
             jour(-1), date_validite=jour(29))
    d5 = nouvelle("devis", "C0004", [ligne("PF0004", 25_000_000, "C0004")], jour(-6), date_validite=jour(24))
    pieces.valider(conn, d5, user)

    # Achats
    cf1 = nouvelle("cde_fournisseur", "F0001", [ligne("MP0001", 12_000_000, "F0001", "achat")], jour(-20),
                   date_livraison=jour(-6))
    pieces.valider(conn, cf1, user)
    r1 = suite([cf1], "reception", jour(-6),
               modif=lambda ls: [dict(l, quantite_milli=8_000_000) for l in ls])
    pieces.valider(conn, r1, user)
    cf2 = nouvelle("cde_fournisseur", "F0003", [ligne("MP0004", 40_000, "F0003", "achat")], jour(-4),
                   date_livraison=jour(3))
    pieces.valider(conn, cf2, user)

    return {t: conn.execute(f"SELECT COUNT(*) n FROM {t} WHERE " + (
        "origine='demo'" if t in ("gc_pieces", "gc_articles", "gc_tiers") else "1=1")).fetchone()["n"]
        for t in ("gc_tiers", "gc_articles", "gc_pieces", "gc_mouvements")}
