"""
Lecture d'une packing list — les pieges releves sur des fichiers reels.

Chaque bloc protege une erreur qui a produit, ou aurait produit, une entree de
stock fausse :

1. **L'entete n'est pas la premiere ligne.** Sur PZH260486 elle est en ligne 2,
   la ligne 1 etant vide. Supposer la ligne 1 fait entrer « roll batch number »
   comme une bobine et perd la premiere vraie.
2. **« roll batch number » est un code de bobine, pas un lot.** Le prendre pour
   un lot ferait entrer 48 bobines sous un seul code — donc UNE bobine.
3. **L'unite vit dans le titre de la colonne.** `length(KM)` lu comme des
   metres donne un stock mille fois trop petit.
4. **Les numeros de ligne rendus sont ceux du FICHIER.** Un refus qui annonce
   « ligne 12 » alors que l'utilisateur en voit 14 l'envoie chercher au mauvais
   endroit.
5. **Un doublon dans le fichier se refuse et se dit** — il ne se laisse pas
   entrer deux fois.
"""
import sqlite3
import sys

sys.path.insert(0, ".")
from app.services import packing_list as pl                  # noqa: E402

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


# Extrait fidele de PZH260486 : ligne vide en tete, entete en ligne 2,
# cinq laizes, metrages de 17 700 a 18 200.
PZH = [
    [None, None, None],
    ["roll batch number", "width(MM)", "length(M)"],
    ["Y2606000506", 440, 17980],
    ["Y2606000527", 440, 18100],
    ["Y2606000909", 470, 18100],
    ["Y2606000910", 530, 18100],
    ["Y2606001371", 570, 17750],
    [None, None, None],
]


# ── 1. Lecture des nombres ──────────────────────────────────────────────────
print("\nNombres — trois fournisseurs, trois ecritures du meme metrage")
for brut, attendu in [("17980", 17980.0), ("17 980", 17980.0), ("17.980", 17980.0),
                      ("17,980", 17980.0), ("2 000,5", 2000.5), ("440", 440.0),
                      ("", None), ("N/A", None), (None, None)]:
    check(f"« {brut} »", pl._nombre(brut), attendu)


# ── 2. L'entete se cherche, il ne se suppose pas ────────────────────────────
print("\nDetection de l'entete")
a = pl.analyser(PZH)
check("entetes", a["entetes"], ["roll batch number", "width(MM)", "length(M)"])
check("ligne de l'entete dans le fichier", a["entete_ligne"], 2)
check("lignes de donnees", a["nb_lignes"], 5)

sans_entete = [["Y2606000506", 440, 17980], ["Y2606000527", 440, 18100]]
b = pl.analyser(sans_entete)
check("fichier sans entete : aucune ligne sacrifiee", b["nb_lignes"], 2)
vrai("colonnes nommees par defaut", b["entetes"][0].startswith("Colonne"))


# ── 3. « roll batch number » designe la bobine ─────────────────────────────
print("\nProposition de correspondance")
p = a["proposition"]
check("code", p["code"], "roll batch number")
check("le lot reste vide, pas confondu avec le code", p["lot"], None)
check("laize", p["laize"], "width(MM)")
check("metrage", p["metrage"], "length(M)")
check("unite de laize lue dans le titre", p["unite_laize"], "mm")
check("unite de metrage lue dans le titre", p["unite_metrage"], "m")
check("origine de la proposition", p["confiance"]["code"], "entete")

# Un fichier qui porte les deux : la colonne « roll » est le code, la colonne
# « lot number » est le lot. Aucune des deux ne prend la place de l'autre.
deux = [["roll number", "lot number", "width", "length"],
        ["R1", "LOT-A", "440", "2000"],
        ["R2", "LOT-A", "440", "2000"]]
p2 = pl.analyser(deux)["proposition"]
check("code et lot distingues — code", p2["code"], "roll number")
check("code et lot distingues — lot", p2["lot"], "lot number")


# ── 4. Sans entete parlant, la FORME des valeurs tranche ───────────────────
print("\nRepli sur la forme des valeurs")
muet = [["a", "b", "c"],
        ["ZZ001", "440", "18000"],
        ["ZZ002", "440", "18100"],
        ["ZZ003", "470", "17900"],
        ["ZZ004", "470", "18050"]]
p3 = pl.analyser(muet)["proposition"]
check("laize reconnue a ses valeurs", p3["laize"], "b")
check("metrage reconnu a ses valeurs", p3["metrage"], "c")
check("code reconnu a ses valeurs distinctes", p3["code"], "a")
check("origine du verdict", p3["confiance"]["laize"], "valeurs")


# ── 5. Extraction : unites, plages, numeros de ligne ───────────────────────
print("\nExtraction")
r = pl.extraire(PZH, a["proposition"])
check("bobines retenues", r["nb"], 5)
check("aucun refus", r["refusees"], [])
check("metrage total", r["metrage_total"], 90030.0)
check("premiere ligne = ligne 3 du FICHIER", r["lignes"][0]["ligne"], 3)
check("derniere ligne = ligne 7 du FICHIER", r["lignes"][-1]["ligne"], 7)
check("code normalise en majuscules", r["lignes"][0]["code_barre"], "Y2606000506")
check("laize en mm", r["lignes"][0]["laize_mm"], 440.0)
check("repartition par laize",
      [(l["laize_mm"], l["nb"]) for l in r["par_laize"]],
      [(440.0, 2), (470.0, 1), (530.0, 1), (570.0, 1)])

km = [["roll", "width(CM)", "length(KM)"], ["A1", "44", "18"]]
rk = pl.extraire(km, pl.analyser(km)["proposition"])
check("laize en cm convertie", rk["lignes"][0]["laize_mm"], 440.0)
check("metrage en km converti", rk["lignes"][0]["metrage_m"], 18000.0)


# ── 6. Ce qui est refuse est DIT, avec sa ligne ───────────────────────────
print("\nLignes refusees")
sale = [["roll", "width(MM)", "length(M)"],
        ["A1", "440", "18000"],
        ["", "440", "18000"],
        ["A1", "470", "17000"],
        ["A2", "3", "18000"],
        ["A3", "530", ""]]
rs = pl.extraire(sale, pl.analyser(sale)["proposition"])
check("retenues", [l["code_barre"] for l in rs["lignes"]], ["A1", "A3"])
check("trois refus", len(rs["refusees"]), 3)
check("code vide, ligne 3", (rs["refusees"][0]["ligne"], rs["refusees"][0]["motif"]),
      (3, "code-barres vide"))
check("doublon, ligne 4", rs["refusees"][1]["ligne"], 4)
vrai("le doublon nomme la ligne d'origine",
     "ligne 2" in rs["refusees"][1]["motif"], rs["refusees"][1]["motif"])
vrai("laize aberrante refusee", "hors plage" in rs["refusees"][2]["motif"])
check("metrage vide accepte, mais compte", rs["sans_metrage"], 1)
check("la bobine sans metrage n'a pas zero", rs["lignes"][1]["metrage_m"], None)

try:
    pl.extraire(PZH, {"laize": "width(MM)"})
    vrai("colonne de code obligatoire", False, "accepte sans code")
except ValueError:
    vrai("colonne de code obligatoire", True)


# ── 7. Le profil par fournisseur ──────────────────────────────────────────
print("\nProfil memorise")
db = sqlite3.connect(":memory:")
db.row_factory = sqlite3.Row
db.executescript("""
    CREATE TABLE stock_packing_profils (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fournisseur_id INTEGER, fournisseur_nom TEXT,
        colonne_code TEXT, colonne_laize TEXT, colonne_metrage TEXT,
        colonne_lot TEXT, unite_laize TEXT, unite_metrage TEXT,
        exemple_fichier TEXT, created_at TEXT, updated_at TEXT, updated_by_name TEXT);
""")
check("aucun profil au depart", pl.profil(db, 7), None)

pl.enregistrer_profil(db, fournisseur_id=7, fournisseur_nom="Kanzan",
                      mapping=a["proposition"], fichier="PZH260486.xlsx", auteur="Test")
db.commit()
pr = pl.profil(db, 7)
check("profil relu", (pr["code"], pr["laize"], pr["unite_metrage"]),
      ("roll batch number", "width(MM)", "m"))

pl.enregistrer_profil(db, fournisseur_id=7, fournisseur_nom="Kanzan",
                      mapping={"code": "reel id", "laize": "larg", "metrage": "long",
                               "lot": None, "unite_laize": "mm", "unite_metrage": "m"},
                      fichier="v2.xlsx", auteur="Test")
db.commit()
check("un seul profil par fournisseur",
      db.execute("SELECT COUNT(*) FROM stock_packing_profils").fetchone()[0], 1)
check("profil mis a jour", pl.profil(db, 7)["code"], "reel id")

# Sans id, le nom sert de repli — et ne se confond pas avec le profil a id.
pl.enregistrer_profil(db, fournisseur_id=None, fournisseur_nom="Frimpeks",
                      mapping=a["proposition"], auteur="Test")
db.commit()
check("repli sur le nom", pl.profil(db, None, "frimpeks")["code"], "roll batch number")
check("un fournisseur inconnu n'herite de rien", pl.profil(db, None, "Likexin"), None)
db.close()

print("\n%s" % ("Tout est vert." if not ko else f"{ko} controle(s) en echec."))
sys.exit(1 if ko else 0)
