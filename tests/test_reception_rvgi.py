"""
Réception RVGI → stock MyStock : les trois traductions qui peuvent fausser le stock.

Chaque bloc protège un piège relevé sur les données réelles le 04/09/2026. Aucun
n'est théorique — tous ont d'abord produit un résultat faux.

1. **L'article est un triplet.** `mat_mat` porte une ligne par type pour un même
   couple : `1183/0001` est une glassine en type 4 et un vélin en type 5.
2. **La quantité est en mètres linéaires**, alors que `cua` annonce des mètres
   carrés. Diviser par la laize donnerait un métrage faux d'un facteur deux.
3. **Le rapprochement ne doit pas confondre les natures.** « PP blanc mat
   adhésif permanent » sortait « PET blanc adhésif permanent » à 0,67 et se
   serait fait valider d'un clic.

Plus un contrôle qui n'était pas prévu : quand MyStock et l'ERP annoncent deux
longueurs de bobine différentes, la ligne le dit. Cas réel : `552/0005`.
"""
import sqlite3
import sys

sys.path.insert(0, ".")
from app.services import reception_rvgi as rr                # noqa: E402

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


def vrai(libelle, condition, detail=""):
    global ko
    if not condition:
        ko += 1
    print(f"  {'OK ' if condition else 'KO '} {libelle}")
    if not condition and detail:
        print(f"       {detail}")


# ── 1. Le métrage de bobine, lu dans le libellé de l'ERP ────────────────────
print("\nMétrage de bobine dans `mat_mat.libt2`")
for texte, attendu in [
    ("Ø 76 mm, Bobine 16.000 ml, CSO", 16000.0),
    ("Roll 18 000 ml, External winding, Ø Core 152 mm", 18000.0),
    ("For Hotmelt - R18.000 ml, Ø152 mm Barcode", 18000.0),
    ("Core Ø76 mm, Outside, Roll lenght 2.000 meters", 2000.0),
    ("Ø 76 mm, Bobine 10.000 ml, CSO - Release à 10", 10000.0),
    ("55 g/m², Mandrin 76 mm, Enroulement Extérieur", None),
    (None, None),
]:
    check(f"« {str(texte)[:38]} »", rr.metrage_bobine_erp(texte), attendu)


# ── 2. Les natures de support ne se confondent jamais ───────────────────────
print("\nNatures de support — un PP n'est pas un PET")
check("PP contre PET", rr.score("PP blanc mat adhésif permanent",
                                "PET blanc adhésif permanent"), 0.0)
check("PE contre couché", rr.score("PE 93µ adhésif permanent acrylique",
                                   "Couché adhésif permanent acrylique"), 0.0)
check("vélin contre thermique", rr.score("Velin adhésif permanent",
                                         "Thermique Eco adhésif permanent"), 0.0)
vrai("PP contre PP reste évalué",
     rr.score("PP transparent adhésif permanent acrylique",
              "PP transparent permanent acrylique") > 0.9)
vrai("une nature d'un seul côté ne disqualifie pas",
     rr.score("Adhésif congélation à - 35°C", "2030 Adhésif congélation JAOUR") > 0)


# ── 3. Le grammage se lit quelle que soit son écriture ──────────────────────
print("\nGrammages — « 60g », « 60gsm », « 95µ » disent le même nombre")
vrai("60g rejoint 60gsm",
     rr.score("Siliconnée Jaune 60g", "60gsm glassine jaune siliconné")
     > rr.score("Siliconnée Jaune 60g", "60gsm ITASA"))
vrai("le bon vélin se détache des autres vélins",
     rr.score("Velin teinté jaune fluo 70g", "70gsm Vellum fluo jaune")
     >= 2 * rr.score("Velin teinté jaune fluo 70g", "62gsm Vellum"),
     f"{rr.score('Velin teinté jaune fluo 70g', '70gsm Vellum fluo jaune')} "
     f"contre {rr.score('Velin teinté jaune fluo 70g', '62gsm Vellum')}")


# ── 4. La conversion vers l'unité du magasin ────────────────────────────────
print("\nConversion — mètres linéaires, kilos, palettes")
glassine = {"categorie": "glassine", "metres_lineaires_par_bobine": 16000}
c = rr.convertir(4, 64008.51, glassine, "Ø 76 mm, Bobine 16.000 ml, CSO")
check("64 009 m ÷ 16 000 = 4 bobines", round(c["quantite"]), 4)
check("unité de gestion", c["unite"], "bobine")
vrai("aucune alerte quand les deux sources s'accordent", c["alerte"] is None)

# Le cas réel : MyStock se trompe, l'ERP a raison. C'est l'ERP qui est retenu.
faux = {"categorie": "glassine", "metres_lineaires_par_bobine": 18100}
c = rr.convertir(4, 64008.51, faux, "Ø 76 mm, Bobine 16.000 ml, CSO")
vrai("divergence MyStock / ERP signalée", bool(c["alerte"]), str(c))
check("le conditionnement de l ERP fait foi", round(c["quantite"]), 4)
vrai("l'alerte cite les deux valeurs",
     "18 100" in (c["alerte"] or "") and "16 000" in (c["alerte"] or ""),
     c["alerte"])
vrai("et dit laquelle est retenue", "ERP" in (c["alerte"] or ""), c["alerte"])

# L'ERP fait foi, y compris quand MyStock ne sait pas — cinq références à 0.
vide = {"categorie": "glassine", "metres_lineaires_par_bobine": 0}
c = rr.convertir(4, 20000, vide, "Bobine 10.000 ml")
check("conditionnement lu sur l ERP", round(c["quantite"]), 2)
vrai("la provenance du métrage est dite", "ERP" in (c["detail"] or ""), c["detail"])

# Repli sur MyStock quand l ERP n annonce rien de lisible.
c = rr.convertir(4, 24000, {"categorie": "glassine", "metres_lineaires_par_bobine": 12000},
                 "58 g/m², Mandrin 76 mm")
check("repli sur MyStock", round(c["quantite"]), 2)
vrai("et la provenance le dit", "MyStock" in (c["detail"] or ""), c["detail"])

c = rr.convertir(4, 20000, {"categorie": "glassine"}, None)
check("aucune source : rien n'est inventé", c["quantite"], None)
vrai("et la ligne dit ce qui manque", bool(c["manque"]))

check("adhésif : le kilo ne se convertit pas",
      rr.convertir(9, 1300, {"categorie": "adhesif"}, None)["quantite"], 1300)
check("carton : 520 unités ÷ 260 par palette",
      rr.convertir(19, 520, {"categorie": "carton", "unites_par_palette": 260}, None)["quantite"], 2.0)
check("palette : la quantité EST déjà l'unité",
      rr.convertir(20, 30, {"categorie": "palette"}, None)["quantite"], 30.0)
check("carton sans conditionnement : non convertible",
      rr.convertir(19, 520, {"categorie": "carton"}, None)["quantite"], None)


# ── 5. Le périmètre et les deux régimes ─────────────────────────────────────
print("\nPérimètre et régimes d'entrée")
bobines = {3, 4, 5, 6, 7, 8}
for t, (cat, sous, regime) in sorted(rr.PERIMETRE.items()):
    attendu = "attente" if t in bobines else "direct"
    check(f"type {t} ({cat}) → {attendu}", regime, attendu)
vrai("les types hors périmètre sont absents",
     not ({1, 2, 10, 11, 16, 17, 18, 21} & set(rr.PERIMETRE)))
vrai("chaque catégorie du périmètre a une unité de gestion",
     all(cat in rr.UNITE_GESTION for cat, _s, _r in rr.PERIMETRE.values()))


# ── 6. Rien ne bouge sans date de mise en service ───────────────────────────
print("\nMise en service")
base = sqlite3.connect(":memory:")
base.row_factory = sqlite3.Row
base.execute("CREATE TABLE stock_config (cle TEXT PRIMARY KEY, valeur TEXT, updated_at TEXT)")
base.execute("INSERT INTO stock_config (cle, valeur) VALUES (?, '')", (rr.CLE_DEPUIS,))
check("vide au départ", rr.date_de_mise_en_service(base), None)
res = rr.lignes_a_integrer(base, None)
check("aucune ligne prise tant que la date est vide", res["total"], 0)
vrai("et l'écran le dit", bool(res["message"]), str(res))
base.execute("UPDATE stock_config SET valeur='2026-09-04' WHERE cle=?", (rr.CLE_DEPUIS,))
check("date posée", rr.date_de_mise_en_service(base), "2026-09-04")
base.close()


# ── 7. L'intégration : deux régimes, et une seule fois ──────────────────────
#
# `appliquer_mouvement_mp` vit dans le routeur, qui importe FastAPI : on passe
# un double, ce qui vérifie au passage que le service ne l'appelle QUE pour le
# régime direct. Une bobine qui produirait un mouvement ici serait le bug que
# tout ce découpage cherche à éviter — le stock avancerait sans que personne
# n'ait scanné, et la chaîne FSC resterait muette.
print("\nIntégration")

base = sqlite3.connect(":memory:")
base.row_factory = sqlite3.Row
base.executescript("""
    CREATE TABLE matieres_premieres (id INTEGER PRIMARY KEY, categorie TEXT,
        sous_section TEXT, reference TEXT, designation TEXT, actif INTEGER DEFAULT 1,
        metres_lineaires_par_bobine REAL, unites_par_palette REAL);
    CREATE TABLE mp_laizes (id INTEGER PRIMARY KEY, valeur_mm REAL, label TEXT,
        ordre INTEGER, actif INTEGER, created_at TEXT);
    CREATE TABLE stock_receptions (id INTEGER PRIMARY KEY, created_at TEXT,
        created_by TEXT, created_by_name TEXT, note TEXT, nb_bobines INTEGER,
        fournisseur TEXT, fsc_type_claim TEXT, lot_numero TEXT, rvgi_cde TEXT,
        rvgi_bl TEXT, rvgi_qte_attendue REAL, rvgi_lif_id INTEGER,
        rvgi_matiere_id INTEGER, rvgi_laize_id INTEGER);
    CREATE TABLE erp_article_matiere (code1 TEXT, code2 TEXT, type_code INTEGER,
        matiere_id INTEGER, origine TEXT, notes TEXT, created_at TEXT,
        created_by_name TEXT, PRIMARY KEY (code1, code2, type_code));
    CREATE TABLE erp_reception_integree (lif_id INTEGER PRIMARY KEY, numero INTEGER,
        ligne INTEGER, amjl TEXT, qte_rvgi REAL, matiere_id INTEGER, laize_id INTEGER,
        quantite REAL, unite TEXT, regime TEXT, mouvement_id INTEGER,
        reception_id INTEGER, integre_at TEXT, integre_par TEXT);
    INSERT INTO matieres_premieres (id, categorie, reference, designation,
        metres_lineaires_par_bobine, unites_par_palette)
      VALUES (53, 'glassine', '60gsm', 'glassine jaune', 16000, NULL),
             (18, 'carton', '385 x 385 x 208 mm', '', NULL, 260);
""")

mouvements = []


def faux_mouvement(conn, user, matiere_id, type_mvt, quantite, **kw):
    mouvements.append((matiere_id, type_mvt, quantite, kw.get("laize_id")))
    return {"mouvement_id": 900 + len(mouvements)}


LIGNE_CARTON = {"lif_id": 1, "numero": 5905, "ligne": 3, "amjl": "2026-09-01",
                "qte_rvgi": 520, "matiere_id": 18, "quantite": 2.0, "unite": "palette",
                "type_code": 19, "regime": "direct", "integrable": True, "manque": [],
                "laize_mm": None, "fournisseur": "RAJA", "ref_br": "BL1"}
LIGNE_BOBINE = {"lif_id": 2, "numero": 5905, "ligne": 4, "amjl": "2026-09-01",
                "qte_rvgi": 64008.51, "matiere_id": 53, "quantite": 4.0, "unite": "bobine",
                "type_code": 4, "regime": "attente", "integrable": True, "manque": [],
                "laize_mm": 470.0, "fournisseur": "ITASA", "ref_br": "BL2"}

r = rr.integrer(base, LIGNE_CARTON, {"nom": "Test"}, faux_mouvement)
check("carton : régime direct", r["regime"], "direct")
vrai("carton : un mouvement d'entrée est écrit", len(mouvements) == 1, str(mouvements))
check("carton : la bonne quantité", mouvements[0][:3], (18, "entree", 2.0))
vrai("carton : aucune réception en attente",
     base.execute("SELECT COUNT(*) FROM stock_receptions").fetchone()[0] == 0)

r = rr.integrer(base, LIGNE_BOBINE, {"nom": "Test"}, faux_mouvement)
check("bobine : régime attente", r["regime"], "attente")
vrai("bobine : AUCUN mouvement de stock", len(mouvements) == 1,
     f"{len(mouvements)} mouvement(s) — le stock a bougé sans scan")
rec = base.execute("SELECT * FROM stock_receptions").fetchone()
vrai("bobine : une réception est créée", rec is not None)
check("bobine : zéro bobine tant que rien n'est scanné", rec["nb_bobines"], 0)
check("bobine : la quantité attendue est portée", rec["rvgi_qte_attendue"], 4.0)
check("bobine : la ligne RVGI est tracée", rec["rvgi_lif_id"], 2)
laize = base.execute("SELECT * FROM mp_laizes").fetchone()
vrai("bobine : la laize inconnue est créée à la volée",
     laize is not None and abs(laize["valeur_mm"] - 470.0) < 0.5)
check("bobine : la réception pointe cette laize", rec["rvgi_laize_id"], laize["id"])

# Rejouer la même ligne — c'est ce qui arrive à chaque synchro.
for ligne, nom in ((LIGNE_CARTON, "carton"), (LIGNE_BOBINE, "bobine")):
    try:
        rr.integrer(base, ligne, {"nom": "Test"}, faux_mouvement)
        vrai(f"{nom} : seconde intégration refusée", False, "elle est passée")
    except ValueError:
        vrai(f"{nom} : seconde intégration refusée", True)
vrai("le stock n'a pas doublé", len(mouvements) == 1)
check("deux lignes tracées, pas quatre",
      base.execute("SELECT COUNT(*) FROM erp_reception_integree").fetchone()[0], 2)

# Une ligne non intégrable ne passe jamais, même forcée.
try:
    rr.integrer(base, dict(LIGNE_CARTON, lif_id=9, integrable=False,
                           manque=["Article non apparié"]),
                {"nom": "Test"}, faux_mouvement)
    vrai("ligne non intégrable refusée", False, "elle est passée")
except ValueError as e:
    vrai("ligne non intégrable refusée", "apparié" in str(e), str(e))

# Une laize déjà connue n'est pas recréée.
n_avant = base.execute("SELECT COUNT(*) FROM mp_laizes").fetchone()[0]
rr._laize_id(base, 470.0)
check("laize existante réutilisée",
      base.execute("SELECT COUNT(*) FROM mp_laizes").fetchone()[0], n_avant)


# ── 8. L'appariement ────────────────────────────────────────────────────────
print("\nAppariement")
rr.apparier(base, "552", "0005", 4, 53, auteur="Test")
check("apparié", base.execute(
    "SELECT matiere_id FROM erp_article_matiere WHERE code1='552'").fetchone()["matiere_id"], 53)
rr.apparier(base, "552", "0005", 4, None)
check("délié", base.execute(
    "SELECT COUNT(*) FROM erp_article_matiere").fetchone()[0], 0)
for c1, c2, t, mid, quoi in [("", "0005", 4, 53, "code1 vide"),
                             ("552", "0005", "x", 53, "type non entier"),
                             ("552", "0005", 4, 999, "matière inconnue")]:
    try:
        rr.apparier(base, c1, c2, t, mid)
        vrai(f"{quoi} refusé", False, "accepté")
    except ValueError:
        vrai(f"{quoi} refusé", True)
base.close()


print("\n%s" % ("Tout est vert." if not ko else f"{ko} contrôle(s) en échec."))
sys.exit(1 if ko else 0)
