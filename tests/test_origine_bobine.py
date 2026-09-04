"""
Detection automatique du fournisseur d'une bobine au scan.

Avant ce chantier, la saisie de production demandait le fournisseur a chaque
bobine non receptionnee. Mesure faite sur la base : 90 scans matiere, ZERO
rattache a une reception, 57 fournisseurs tapes a la main -- et des
contradictions (`R1001-26050458-440-*` declare Frimpeks UK sur une bobine et
Likexin sur l'autre, meme lot).

Ce que ces cas verrouillent :

  - la cascade rend TOUJOURS son niveau de confiance, et seule la reception
    vaut « demontre ». Une signature apprise ne fabrique pas de preuve FSC ;
  - une forme de code vue sous deux fournisseurs cesse de designer quelqu'un.
    C'est la garantie qui empeche une erreur de saisie de se propager en regle ;
  - la normalisation GS1 rapproche l'EAN-13 et le SSCC d'un meme fabricant.
    Sans elle, `6415788160497` et `00364157811504575495` (tous deux UPM) n'ont
    rien en commun ;
  - la longueur du code fait partie de la signature « maison » : Kanzan emet
    des codes de 11 chiffres, Burgo de 12, et les confondre reintroduirait
    exactement l'ambiguite qu'on cherche a lever ;
  - l'apprentissage est rejouable : reconstruire deux fois ne double pas les
    compteurs.

Lancer : python3 tests/test_origine_bobine.py
"""
import json
import sqlite3
import sys

sys.path.insert(0, ".")

from app.services import origine_bobine as ob  # noqa: E402

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
    c.executescript(
        """
        CREATE TABLE stock_receptions(id INTEGER PRIMARY KEY, fournisseur TEXT,
            certificat_fsc TEXT, fsc_type_claim TEXT);
        CREATE TABLE stock_reception_items(id INTEGER PRIMARY KEY, reception_id INT,
            code_barre TEXT, scanned_at TEXT);
        CREATE TABLE fab_matieres_utilisees(id INTEGER PRIMARY KEY, code_barre TEXT,
            fournisseur_manual TEXT, certificat_fsc_manual TEXT, reception_id INT,
            liaison_mode TEXT, no_dossier TEXT,
            origine_detection TEXT, origine_confiance TEXT);
        CREATE TABLE fournisseurs_fsc(id INTEGER PRIMARY KEY, nom TEXT, licence TEXT);
        CREATE TABLE bobine_signatures(id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT, valeur TEXT, specificite INT,
            observations TEXT DEFAULT '{}', total INT DEFAULT 0,
            premier_vu TEXT, dernier_vu TEXT, UNIQUE(type, valeur));
        INSERT INTO fournisseurs_fsc(id,nom,licence) VALUES
            (1,'Kanzan','FSC-C000001'),(2,'Burgo / Mosaico','FSC-C000002'),
            (3,'Likexin','FSC-C000003'),(4,'UPM','FSC-C000004');
        ALTER TABLE fournisseurs_fsc ADD COLUMN certificat TEXT;
        UPDATE fournisseurs_fsc SET certificat = licence;
        """
    )
    return c


def scan(c, code, nom, dossier=None):
    c.execute(
        "INSERT INTO fab_matieres_utilisees(code_barre,fournisseur_manual,no_dossier)"
        " VALUES(?,?,?)", (code, nom, dossier))
    ob.apprendre(c, code, nom)


print("\n1. La reception prime, et elle seule demontre")
c = base()
c.execute("INSERT INTO stock_receptions(id,fournisseur,certificat_fsc,fsc_type_claim)"
          " VALUES(1,'Kanzan','FSC-C000001','fsc_mix')")
c.execute("INSERT INTO stock_reception_items(reception_id,code_barre,scanned_at)"
          " VALUES(1,'60226140597','2026-06-29')")
# Une saisie contradictoire ne doit pas prendre le pas sur le scan d'arrivee.
scan(c, "60226140597", "Likexin")
r = ob.resoudre(c, "60226140597")
check("source", r["source"], "reception")
check("confiance", r["confiance"], "certain")
check("fournisseur", r["fournisseur"], "Kanzan")
check("origine demontree", r["demontre"], True)
check("certificat rendu", r["certificat_fsc"], "FSC-C000001")

print("\n2. Une signature apprise ne demontre jamais rien")
c = base()
for n in ("60226140585", "60226140586", "60226140587", "60226140588"):
    scan(c, n, "Kanzan")
r = ob.resoudre(c, "60226140591")
check("source", r["source"], "signature")
check("confiance", r["confiance"], "probable")
check("fournisseur", r["fournisseur"], "Kanzan")
check("pas de preuve", r["demontre"], False)
check("licence de l'annuaire", r["licence"], "FSC-C000001")
check("explication non vide", bool(r["explication"]), True)

print("\n3. Deux fournisseurs sous la meme forme : plus personne n'est designe")
c = base()
# Cas reel : `R1101-SGD…` a ete declare Likexin, Sato et Shine.
for i in (5, 6, 7):
    scan(c, "R1101-SGD26020324-%d" % i, "Likexin")
for i in (14, 15, 16):
    scan(c, "R1101-SGD26020324-%d" % i, "Burgo / Mosaico")
r = ob.resoudre(c, "R1101-SGD26020324-20")
check("aucun fournisseur impose", r["fournisseur"], None)
check("confiance", r["confiance"], "ambigu")
check("les deux candidats sont rendus", len(r["candidats"]), 2)
check("candidats nommes",
      sorted(x["nom"] for x in r["candidats"]),
      ["Burgo / Mosaico", "Likexin"])

print("\n4. GS1 : EAN-13 et SSCC d'un meme fabricant se rejoignent")
c = base()
# `00364157811504575495` = AI(00) + SSCC ; `6415788160497` = EAN-13.
# Bruts ils n'ont rien en commun ; enveloppe retiree, ils partagent `641578`.
for suffixe in ("5495", "5496", "5497"):
    scan(c, "003641578115045754" + suffixe[-2:], "UPM")
r = ob.resoudre(c, "6415788160497")
check("source", r["source"], "signature")
check("fournisseur", r["fournisseur"], "UPM")
check("via le prefixe entreprise", r.get("signature", "").startswith("641578"), True)

print("\n5. La longueur separe deux formats maison qui commencent pareil")
c = base()
for n in ("60226140585", "60226140586", "60226140587"):
    scan(c, n, "Kanzan")           # 11 chiffres
r = ob.resoudre(c, "602261405850")  # 12 chiffres, meme tete
check("pas de report d'un format sur l'autre", r["fournisseur"], None)

print("\n6. Le meme code deja identifie ne repose pas la question")
c = base()
scan(c, "826149120468", "Burgo / Mosaico")
r = ob.resoudre(c, "826149120468")
check("source", r["source"], "historique")
check("fournisseur", r["fournisseur"], "Burgo / Mosaico")
check("declaratif, pas demontre", r["demontre"], False)

print("\n7. A defaut, les autres bobines du dossier en cours")
c = base()
c.execute("INSERT INTO fab_matieres_utilisees(code_barre,fournisseur_manual,no_dossier)"
          " VALUES('AAA-111-1','Likexin','9932280')")
r = ob.resoudre(c, "ZZZ-999-9", "9932280")
check("source", r["source"], "dossier")
check("fournisseur", r["fournisseur"], "Likexin")
check("simple suggestion", r["confiance"], "suggere")

print("\n8. Code inconnu : on ne devine pas")
c = base()
r = ob.resoudre(c, "XYZ00000")
check("rien trouve", r["trouve"], False)
check("confiance", r["confiance"], "aucune")
check("aucun candidat", r["candidats"], [])
check("code vide accepte sans planter", ob.resoudre(c, "")["trouve"], False)

print("\n9. Reconstruction rejouable")
c = base()
c.execute("INSERT INTO stock_receptions(id,fournisseur) VALUES(1,'Kanzan')")
c.execute("INSERT INTO stock_reception_items(reception_id,code_barre,scanned_at)"
          " VALUES(1,'60226140597','2026-06-29')")
c.execute("INSERT INTO fab_matieres_utilisees(code_barre,fournisseur_manual)"
          " VALUES('60226140598','Kanzan')")
b1 = ob.reconstruire(c)
b2 = ob.reconstruire(c)
check("meme nombre de signatures", b1["signatures"], b2["signatures"])
tot = c.execute("SELECT total FROM bobine_signatures WHERE type='num'"
                " ORDER BY specificite DESC LIMIT 1").fetchone()["total"]
check("compteurs non doubles", tot, 2)

print("\n10. Une identification hors annuaire reste utilisable, sans licence")
c = base()
for i in range(3):
    scan(c, "9911%03d1234" % i, "Papeterie du Nord")
r = ob.resoudre(c, "99114001234")
check("fournisseur propose", r["fournisseur"], "Papeterie du Nord")
check("signale hors annuaire", r["hors_annuaire"], True)
check("aucune licence", r["licence"], "")

print("\n11. Le chemin reel d'enregistrement ecrit l'origine et apprend")
# On appelle la fonction du router, pas une reimplementation : c'est elle qui
# doit poser `origine_detection` et nourrir les signatures. Un test qui
# reverifierait le service seul laisserait passer un branchement oublie.
from app.routers.fabrication import _link_matiere_to_reception  # noqa: E402

c = base()
c.execute("INSERT INTO fab_matieres_utilisees(id,code_barre) VALUES(1,'60226140591')")
_link_matiere_to_reception(c, 1, "60226140591", 1,
                           origine="signature", confiance="probable")
row = c.execute("SELECT * FROM fab_matieres_utilisees WHERE id=1").fetchone()
check("fournisseur pose", row["fournisseur_manual"], "Kanzan")
check("liaison declarative", row["liaison_mode"], "manual")
check("origine tracee", row["origine_detection"], "signature")
check("confiance tracee", row["origine_confiance"], "probable")
check("la validation a nourri la memoire",
      c.execute("SELECT COUNT(*) c FROM bobine_signatures").fetchone()["c"] > 0, True)

# Meme code, meme fournisseur : la prochaine bobine se resout toute seule.
c.execute("INSERT INTO fab_matieres_utilisees(id,code_barre,fournisseur_manual)"
          " VALUES(2,'60226140591','Kanzan')")
check("le code est desormais connu",
      ob.resoudre(c, "60226140591")["fournisseur"], "Kanzan")

print()
if ko:
    print(f"{ko} verification(s) en echec.")
    sys.exit(1)
print("Tout est vert.")
