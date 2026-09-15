"""
Un départ rattache les lignes de commande qu'il emporte — sans jamais dire
qu'elles sont produites.

MyExpé permet, depuis le 15/09/2026, de cocher plusieurs lignes de commande
RVGI sur une programmation de départ, comme le planning le fait déjà pour un
dossier de fabrication. Les deux liaisons vivent dans la même table et ne
répondent pas à la même question :

  dossier → commande   « cette ligne est produite »
  départ  → commande   « cette ligne est partie »

Ce que ce test verrouille :

1. **Les deux natures de pièce d'un départ ne se marchent pas dessus.**
   Enregistrer ses lignes de commande ne touche pas à ses bons de livraison.
2. **`rvgi_etat` ne parle que des BL.** C'est la pièce native d'un départ :
   un ARC renseigné ne doit pas faire passer « rattaché » un départ sans BL.
3. **Chaque couple écrit sa propre vitrine** — `no_bl` pour les BL, `arc`
   pour les commandes.
4. **Une expédition ne fait pas reliquat.** Le dossier suivant posé sur la
   même ligne de commande garde une référence normale.
5. **Production et expédition se lisent séparément** sur une même ligne.
6. **Un couple non prévu est refusé** : un dossier ne rattache pas un BL.
"""
import importlib.util
import sqlite3
import sys

sys.path.insert(0, ".")
ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


spec = importlib.util.spec_from_file_location(
    "mig_ratt", "app/core/migrations/2026_08_25_rvgi_rattachements.py")
mig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mig)

from app.services import rvgi_rattachement as ratt  # noqa: E402

conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.executescript(
    """
    CREATE TABLE planning_entries (
        id INTEGER PRIMARY KEY, reference TEXT, numero_of TEXT,
        dos_rvgi TEXT, created_at TEXT);
    CREATE TABLE expe_departs (
        id INTEGER PRIMARY KEY, no_bl TEXT, arc TEXT, created_at TEXT);
    CREATE TABLE of_imports (
        id INTEGER PRIMARY KEY, of_numero TEXT, cmd_rvgi TEXT, date_import TEXT);
    INSERT INTO planning_entries (id, reference, created_at)
         VALUES (1, '9932128', '2026-09-01'), (2, NULL, '2026-09-02');
    INSERT INTO expe_departs (id, created_at) VALUES (10, '2026-09-10');
    """
)
mig.appliquer(conn)
# La migration reprend l'existant : on repart d'une table vide pour ne tester
# que les écritures de ce chantier.
conn.execute("DELETE FROM rvgi_rattachements")
conn.execute("UPDATE expe_departs SET no_bl=NULL, arc=NULL, rvgi_etat=NULL")
conn.execute("UPDATE planning_entries SET dos_rvgi=NULL, rvgi_etat=NULL")

L = lambda num, lg=None, **kw: dict(numero=num, ligne=lg, confirme=True, **kw)  # noqa: E731

print("\n1. Les deux natures de pièce d'un départ cohabitent")
ratt.enregistrer(conn, "depart", 10, "livraison", [L("9938763")], "test")
ratt.enregistrer(conn, "depart", 10, "commande",
                 [L("9932128", 1), L("9932131", 2)], "test")
check("les BL survivent à l'enregistrement des commandes",
      [r["numero"] for r in ratt.lister(conn, "depart", 10, piece="livraison")],
      ["9938763"])
check("les deux lignes de commande sont posées",
      [r["numero"] for r in ratt.lister(conn, "depart", 10, piece="commande")],
      ["9932128", "9932131"])
ratt.enregistrer(conn, "depart", 10, "livraison",
                 [L("9938763"), L("9938764")], "test")
check("réenregistrer les BL ne touche pas aux commandes",
      len(ratt.lister(conn, "depart", 10, piece="commande")), 2)

print("\n2. `rvgi_etat` ne parle que de la pièce native")
d = conn.execute("SELECT * FROM expe_departs WHERE id=10").fetchone()
check("l'état du départ reste celui de ses BL", d["rvgi_etat"], "lie")
conn.execute("DELETE FROM rvgi_rattachements WHERE objet='depart' AND piece='livraison'")
res = ratt.enregistrer(conn, "depart", 10, "commande", [L("9932128", 1)], "test")
d = conn.execute("SELECT * FROM expe_departs WHERE id=10").fetchone()
check("un ARC seul ne fait pas passer le départ « rattaché »",
      d["rvgi_etat"], "lie")   # inchangé : l'écriture des commandes n'y touche pas
check("l'état rendu à l'écran est bien celui des commandes", res["etat"], "lie")
check("et il est signalé comme non natif", res["native"], False)

print("\n3. Chaque couple a sa vitrine")
ratt.enregistrer(conn, "depart", 10, "livraison", [L("9938763")], "test")
ratt.enregistrer(conn, "depart", 10, "commande",
                 [L("9932128", 1), L("9932131", 2)], "test")
d = conn.execute("SELECT * FROM expe_departs WHERE id=10").fetchone()
check("les BL s'écrivent dans no_bl", d["no_bl"], "9938763")
check("les commandes s'écrivent dans arc", d["arc"], "9932128+131")

print("\n4. Une expédition ne fait pas reliquat")
lignes = [dict(numero="9932128", ligne=1, qte=1000)]
check("un départ seul sur la ligne ne fait pas reliquat",
      ratt.deja_couvertes(conn, lignes, "commande"), False)
ratt.enregistrer(conn, "dossier", 1, "commande", [L("9932128", 1)], "test")
check("un dossier sur la ligne, lui, fait reliquat",
      ratt.deja_couvertes(conn, lignes, "commande", sauf=("dossier", 2)), True)
check("sauf pour le dossier qui l'a posé",
      ratt.deja_couvertes(conn, lignes, "commande", sauf=("dossier", 1)), False)

print("\n5. Production et expédition se lisent séparément")
prod = ratt.etat_des_lignes(conn, "commande", lignes, objets=ratt.OBJETS_PRODUCTION)
exp = ratt.etat_des_lignes(conn, "commande", lignes, objets=ratt.OBJETS_EXPEDITION)
cle = ("9932128", 1)
check("la production voit le dossier, et lui seul",
      [o["objet"] for o in prod[cle]["objets"]], ["dossier"])
check("l'expédition voit le départ, et lui seul",
      [o["objet"] for o in exp[cle]["objets"]], ["depart"])
ligne_libre = [dict(numero="9932131", ligne=2, qte=500)]
check("une ligne partie sans dossier reste non rattachée côté production",
      ratt.etat_des_lignes(conn, "commande", ligne_libre,
                           objets=ratt.OBJETS_PRODUCTION)[("9932131", 2)]["etat"],
      "non_rattache")

print("\n6. Un couple non prévu est refusé")
try:
    ratt.enregistrer(conn, "dossier", 1, "livraison", [L("9938763")], "test")
    check("un dossier ne rattache pas un BL", "accepté", "refusé")
except ValueError:
    check("un dossier ne rattache pas un BL", "refusé", "refusé")
check("les pièces d'un départ, la native d'abord",
      ratt.pieces_de("depart"), ("livraison", "commande"))
check("celles d'un dossier", ratt.pieces_de("dossier"), ("commande",))

print()
if ko:
    print(f"{ko} verification(s) en echec")
    sys.exit(1)
print("Tout est vert")
