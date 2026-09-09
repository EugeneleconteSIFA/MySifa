"""
La bobine comme objet de stock — ce qui doit rester vrai.

Chaque bloc protege une decision prise le 09/09/2026, pas une propriete
theorique du code :

1. **Un scan tardif rattache, il n'ajoute jamais.** Sinon une bobine entree par
   packing list puis scannee au magasin compte deux fois, et le stock double
   sans que rien ne le signale.
2. **Un metrage inconnu vaut NULL, jamais zero.** Une somme qui traite
   l'inconnu comme du vide sort un stock reel sous-estime et muet.
3. **Le metrage de la packing list prime sur le standard matiere** — releve
   PZH260486 : 49 bobines d'une meme reference, de 17 700 a 18 200 m.
4. **Une bobine consommee ne s'efface pas** avec la reception qu'on annule :
   elle a servi en production, sa ligne est la seule trace de ce qui est parti.
5. **Le controle de coherence ne corrige rien** — il constate l'ecart entre le
   compteur `mp_stock_laize` et le nombre de bobines.
"""
import sqlite3
import sys

sys.path.insert(0, ".")
from app.services import stock_bobines as sb                 # noqa: E402

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


def base_de_test():
    """Le strict minimum du schema MyStock que le module touche."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE matieres_premieres (
            id INTEGER PRIMARY KEY, categorie TEXT, reference TEXT,
            designation TEXT, actif INTEGER DEFAULT 1,
            metres_lineaires_par_bobine REAL,
            suivi_bobine INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE mp_laizes (id INTEGER PRIMARY KEY, valeur_mm REAL, label TEXT);
        CREATE TABLE mp_stock_laize (matiere_id INTEGER, laize_id INTEGER,
            quantite REAL NOT NULL DEFAULT 0, PRIMARY KEY (matiere_id, laize_id));
        CREATE TABLE stock_receptions (id INTEGER PRIMARY KEY, lot_numero TEXT,
            fournisseur TEXT, fsc_type_claim TEXT, certificat_fsc TEXT);
        CREATE TABLE stock_bobines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code_barre TEXT NOT NULL UNIQUE,
            matiere_id INTEGER, laize_id INTEGER, reception_id INTEGER,
            lot_fournisseur TEXT, metrage_initial REAL, metrage_restant REAL,
            metrage_origine TEXT, etat TEXT NOT NULL DEFAULT 'stock',
            planning_entry_id INTEGER, no_dossier TEXT, source TEXT, note TEXT,
            created_at TEXT NOT NULL, created_by_name TEXT,
            consomme_at TEXT, updated_at TEXT);

        INSERT INTO matieres_premieres (id, categorie, reference, designation,
                                        metres_lineaires_par_bobine)
             VALUES (1, 'glassine', '552/0005', 'Glassine blanche 55 g', 18000),
                    (2, 'frontal',  '1026/0020', 'Thermique Eco', NULL);
        INSERT INTO mp_laizes (id, valeur_mm, label) VALUES (1, 440, '440'), (2, 470, '470');
        INSERT INTO stock_receptions (id, lot_numero, fournisseur, fsc_type_claim)
             VALUES (1, 'LOT-20260909-08-KANZAN-NF', 'Kanzan', 'non_fsc');
    """)
    conn.commit()
    return conn


# ── 1. Normalisation du code-barres ─────────────────────────────────────────
print("\nNormalisation du code-barres")
for brut, attendu in [("  y2606000506 ", "Y2606000506"),
                      ("R1101-sgd26030518-21", "R1101-SGD26030518-21"),
                      ("\n60226140597\n", "60226140597"),
                      (None, "")]:
    check(f"« {str(brut)!r} »", sb.normaliser_code(brut), attendu)


# ── 2. Le metrage : liste, standard, inconnu ────────────────────────────────
print("\nMetrage — d'ou vient le chiffre")
db = base_de_test()

r = sb.creer(db, code_barre="Y2606000506", matiere_id=1, laize_id=1,
             reception_id=1, metrage=17980, metrage_origine=sb.ORIGINE_LISTE,
             source=sb.SOURCE_LISTE, auteur="Test")
b = sb.lire(db, "Y2606000506")
vrai("bobine creee", r["cree"] and not r["rattachee"])
check("metrage de la liste retenu", b["metrage_initial"], 17980.0)
check("origine tracee", b["metrage_origine"], sb.ORIGINE_LISTE)

sb.creer(db, code_barre="Y2606000527", matiere_id=1, laize_id=1, reception_id=1,
         source=sb.SOURCE_SCAN, auteur="Test")
b2 = sb.lire(db, "Y2606000527")
check("repli sur le standard matiere", b2["metrage_initial"], 18000.0)
check("origine = standard", b2["metrage_origine"], sb.ORIGINE_STANDARD)

sb.creer(db, code_barre="60226140597", matiere_id=2, laize_id=1,
         source=sb.SOURCE_SCAN, auteur="Test")
b3 = sb.lire(db, "60226140597")
check("sans standard, le metrage reste inconnu", b3["metrage_initial"], None)
check("et pas zero", b3["metrage_restant"], None)
check("aucune origine inventee", b3["metrage_origine"], None)

check("suivi_bobine s'allume tout seul", db.execute(
    "SELECT suivi_bobine FROM matieres_premieres WHERE id=1").fetchone()[0], 1)


# ── 3. Un scan tardif rattache, il n'ajoute pas ─────────────────────────────
print("\nRattachement — la regle du 04/09")
avant = db.execute("SELECT COUNT(*) FROM stock_bobines").fetchone()[0]
r = sb.creer(db, code_barre="  y2606000506  ", matiere_id=1, laize_id=1,
             reception_id=1, source=sb.SOURCE_SCAN, auteur="Magasin")
apres = db.execute("SELECT COUNT(*) FROM stock_bobines").fetchone()[0]
check("aucune ligne creee", apres, avant)
vrai("rattachement signale", r["rattachee"] and not r["cree"])
vrai("l'appelant est prevenu de ne rien compter",
     "aucune entree de stock" in (r["note"] or ""))

# La liste arrive APRES le scan : le metrage sur mesure remplace le standard.
r = sb.creer(db, code_barre="Y2606000527", matiere_id=1, laize_id=1,
             metrage=18100, metrage_origine=sb.ORIGINE_LISTE, source=sb.SOURCE_LISTE)
b2 = sb.lire(db, "Y2606000527")
check("la packing list remplace le standard", b2["metrage_initial"], 18100.0)
check("restant recale sur une bobine intacte", b2["metrage_restant"], 18100.0)
check("origine mise a jour", b2["metrage_origine"], sb.ORIGINE_LISTE)

# ...mais jamais sur une bobine deja entamee.
sb.consommer(db, b2["id"], metres=5000, no_dossier="9932128")
sb.creer(db, code_barre="Y2606000527", matiere_id=1, metrage=18200,
         metrage_origine=sb.ORIGINE_LISTE, source=sb.SOURCE_LISTE)
b2 = sb.lire(db, "Y2606000527")
check("le restant d'une bobine entamee n'est pas remonte",
      b2["metrage_restant"], 13100.0)


# ── 4. Consommation ─────────────────────────────────────────────────────────
print("\nConsommation et reliquat")
b1 = sb.lire(db, "Y2606000506")
res = sb.consommer(db, b1["id"], metres=12000, no_dossier="9932128")
check("restant decremente", res["metrage_restant"], 5980.0)
check("toujours en stock", res["etat"], sb.ETAT_STOCK)
check("dossier porte", sb.lire(db, "Y2606000506")["no_dossier"], "9932128")

res = sb.consommer(db, b1["id"], metres=9000, no_dossier="9932128")
check("plancher a zero", res["metrage_restant"], 0.0)
check("depassement signale, pas efface", res["depassement"], 3020.0)
check("sortie du stock", res["etat"], sb.ETAT_CONSOMMEE)
vrai("sortie constatee une seule fois", res["sortie_du_stock"])

# Bobine finie sans mesure du reliquat : le geste normal en fin de dossier.
b3 = sb.lire(db, "60226140597")
res = sb.consommer(db, b3["id"], terminee=True, no_dossier="9932200")
check("terminee sans metrage", res["etat"], sb.ETAT_CONSOMMEE)

res = sb.remettre_en_stock(db, b1["id"])
check("retour en stock", res["etat"], sb.ETAT_STOCK)
check("sans metrage invente", res["metrage_restant"], 0.0)
sb.consommer(db, b1["id"], terminee=True)


# ── 5. Etat du stock : la somme dit ce qu'elle ignore ───────────────────────
print("\nEtat du stock")
sb.creer(db, code_barre="Y2606000718", matiere_id=1, laize_id=1, metrage=18100,
         metrage_origine=sb.ORIGINE_LISTE, source=sb.SOURCE_LISTE)
sb.creer(db, code_barre="INCONNUE-1", matiere_id=1, laize_id=1,
         source=sb.SOURCE_SAISIE)
db.execute("UPDATE stock_bobines SET metrage_initial=NULL, metrage_restant=NULL, "
           "metrage_origine=NULL WHERE code_barre='INCONNUE-1'")

e = sb.etat_stock(db, 1, laize_id=1)
check("bobines en stock", e["nb_bobines"], 3)          # 527 entamee, 718, INCONNUE-1
check("metrage somme", e["metrage"], 31200.0)          # 13100 + 18100 + inconnu
check("bobines sans metrage comptees a part", e["sans_metrage"], 1)
vrai("la somme se declare incomplete", e["metrage_complet"] is False)


# ── 6. Annuler une reception n'efface pas ce qui a servi ────────────────────
print("\nAnnulation d'une reception")
db.execute("UPDATE stock_bobines SET reception_id=1")
n = sb.supprimer_de_la_reception(db, 1)
check("bobines en stock retirees", n, 3)
restantes = db.execute("SELECT code_barre, reception_id, etat FROM stock_bobines "
                       "ORDER BY code_barre").fetchall()
check("les consommees restent", [r["code_barre"] for r in restantes],
      ["60226140597", "Y2606000506"])
check("reception detachee", {r["reception_id"] for r in restantes}, {None})


# ── 7. Coherence : constater, jamais corriger ──────────────────────────────
print("\nControle de coherence")
db2 = base_de_test()
for i, code in enumerate(("A1", "A2", "A3"), start=1):
    sb.creer(db2, code_barre=code, matiere_id=1, laize_id=1, source=sb.SOURCE_SCAN)
db2.execute("INSERT INTO mp_stock_laize (matiere_id, laize_id, quantite) VALUES (1,1,3)")
c = sb.coherence(db2)
check("aucun ecart quand les deux concordent", c["ecarts"], [])

db2.execute("UPDATE mp_stock_laize SET quantite=5 WHERE matiere_id=1 AND laize_id=1")
c = sb.coherence(db2)
check("un ecart", len(c["ecarts"]), 1)
check("compteur", c["ecarts"][0]["compteur"], 5.0)
check("bobines", c["ecarts"][0]["bobines"], 3)
check("ecart chiffre", c["ecarts"][0]["ecart"], 2.0)
check("rien n'a ete corrige", db2.execute(
    "SELECT quantite FROM mp_stock_laize WHERE matiere_id=1").fetchone()[0], 5.0)

# Une matiere jamais scannee n'est pas en ecart : elle n'est pas suivie.
db2.execute("INSERT INTO mp_stock_laize (matiere_id, laize_id, quantite) VALUES (2,2,7)")
c = sb.coherence(db2)
check("matiere non suivie ignoree", len(c["ecarts"]), 1)

sb.creer(db2, code_barre="ORPHELINE", source=sb.SOURCE_SCAN)
check("bobine sans matiere signalee", sb.coherence(db2)["bobines_sans_matiere"], 1)


# ── 8. Liste et filtres ────────────────────────────────────────────────────
print("\nListe")
res = sb.lister(db2, matiere_id=1, etat=sb.ETAT_STOCK)
check("total sur le filtre entier", res["total"], 3)
check("toutes sans metrage (standard 18000 present)", res["sans_metrage"], 0)
res = sb.lister(db2, q="a2")
check("recherche insensible a la casse", res["total"], 1)
res = sb.lister(db2, limit=2, matiere_id=1)
check("pagination ne fausse pas le total", (len(res["items"]), res["total"]), (2, 3))
try:
    sb.lister(db2, etat="parti_en_fumee")
    vrai("etat inconnu refuse", False, "accepte")
except ValueError:
    vrai("etat inconnu refuse", True)

db.close()
db2.close()

print("\n%s" % ("Tout est vert." if not ko else f"{ko} controle(s) en echec."))
sys.exit(1 if ko else 0)
