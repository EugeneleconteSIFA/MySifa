"""
Tracabilite : le dossier ne se lit pas sans son prevu.

L'onglet Tracabilite listait la designation du dossier et, dans le detail, les
seules bobines scannees. Deux manques de la meme famille : l'ecran disait ce
qui avait ete CONSOMME sans jamais dire ce qu'il fallait consommer. Devant un
dossier a zero bobine, impossible de distinguer l'oubli du poste qui n'en
consomme pas — c'est pourtant la question que pose un audit.

La colonne « Metrage » et le bloc « Matieres necessaires » viennent donc du
meme calcul que Besoins matieres, par SES fonctions. Ce test verrouille le
fait qu'aucune des deux valeurs n'est recalculee ici : deux ecrans qui
chiffrent separement le meme dossier finissent par en donner deux chiffres, et
c'est le stock qui tranche, des semaines plus tard.

Lancer : python3 tests/test_traca_contexte_produit.py
"""
import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))
os.chdir(RACINE)

# Base jetable : le schema se cree au chargement du shim, jamais sur
# data/production.db.
os.environ["DB_PATH"] = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
import database  # noqa: F401,E402 — le shim doit etre charge avant tout app.*
from app.core.database import get_db  # noqa: E402
import app.routers.fabrication as fab  # noqa: E402

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


with get_db() as conn:
    conn.execute("INSERT OR IGNORE INTO machines (code, nom) VALUES ('T1','Machine test')")
    mid = conn.execute("SELECT id FROM machines WHERE nom='Machine test'").fetchone()[0]
    conn.execute(
        """INSERT INTO fiches_techniques
             (reference, ref_produit_norm, designation, machine, format,
              support, glassine, adhesif, mod_longueur, outil1_nb_front,
              mod_laize, laize)
           VALUES ('PROD-T','prod-t','Etiquette de test','Machine test','100x50',
                   'Frontal 80g','Glassine 62','Acrylique', 100, 4, 330, 330)""")
    conn.execute(
        """INSERT INTO of_imports (of_numero, reference, metrage, qte_etiquettes,
                                   laize, machine)
           VALUES ('OF-T','PROD-T', 12345.6, 40000, 330, 'Machine test')""")
    of_id = conn.execute("SELECT id FROM of_imports").fetchone()[0]
    conn.execute(
        """INSERT INTO planning_entries
             (machine_id, position, reference, client, description, ref_produit,
              statut, of_import_id, format_l, format_h, numero_of)
           VALUES (?, 1, 'D-AVEC-OF', 'Client A', 'Libelle dossier', 'PROD-T',
                   'en_cours', ?, 100, 50, 'OF-T')""", (mid, of_id))
    # Le meme produit, mais sans OF importe : rien a chiffrer, et l'ecran doit
    # le dire plutot que d'afficher un zero.
    conn.execute(
        """INSERT INTO planning_entries
             (machine_id, position, reference, client, description, ref_produit, statut)
           VALUES (?, 2, 'D-SANS-OF', 'Client B', 'Sans OF', 'PROD-T', 'termine')""",
        (mid,))
    conn.commit()

fab.get_current_user = lambda r: {"id": 1, "role": "superadmin", "nom": "Test"}
fab._check_fab_access = lambda u: None
fab.is_admin = lambda u: True


print("\n1. La liste porte le metrage du dossier")
dossiers = {d["reference"]: d for d in fab.get_traceability(request=None)["dossiers"]}
avec = dossiers["D-AVEC-OF"]
sans = dossiers["D-SANS-OF"]
check("le metrage vient de l'OF", avec.get("metrage"), 12345.6)
check("et sa provenance voyage avec lui", avec.get("metrage_source"), "of")
# Sans OF il n'y a ni metrage ni quantite : la fiche seule ne suffit pas.
check("aucun metrage invente sans OF", sans.get("metrage"), None)
check("et la provenance reste vide", sans.get("metrage_source"), None)
# Les champs de fiche ont servi au calcul ; ils ne partent pas au navigateur.
check("la fiche ne fuit pas dans la liste",
      [k for k in avec if k.startswith("ft_")], [])


print("\n2. Le detail dit ce que le dossier devait produire")
ctx = fab.get_traceability(request=None, no_dossier="D-AVEC-OF")["contexte_produit"]
check("meme metrage que la liste", ctx["metrage"], 12345.6)
check("le produit du dossier", ctx["produit_ref"], "PROD-T")
check("sa designation vient de la fiche", ctx["produit_designation"],
      "Etiquette de test")
check("le format du dossier, sans decimale parasite", ctx["format"], "100 × 50")
check("la laize retenue", ctx["laize"], 330.0)

kinds = {m["kind"]: m for m in ctx["matieres"]}
check("le frontal est un besoin", kinds["support"]["libelle"], "Frontal 80g")
check("chiffre sur le metrage du dossier", kinds["support"]["quantite"], 12345.6)
check("en metres lineaires", kinds["support"]["unite"], "ml")
check("la glassine aussi", kinds["glassine"]["libelle"], "Glassine 62")
# L'adhesif se pese : sans grammage sur la matiere, il n'est pas chiffrable —
# et se montre non chiffre plutot que de disparaitre de la liste.
check("l'adhesif figure meme non chiffrable", kinds["adhesif"]["calculable"], False)
check("et il dit ce qui lui manque", bool(kinds["adhesif"]["manque"]), True)

print("\n3. Sans fiche technique rapprochee, rien n'est invente")
with get_db() as conn:
    conn.execute(
        """INSERT INTO planning_entries
             (machine_id, position, reference, client, description, ref_produit, statut)
           VALUES ((SELECT id FROM machines WHERE nom='Machine test'), 3,
                   'D-SANS-FICHE', 'Client C', 'Inconnu', 'PROD-INCONNU', 'attente')""")
    conn.commit()
ctx2 = fab.get_traceability(request=None, no_dossier="D-SANS-FICHE")["contexte_produit"]
check("aucun besoin fabrique", ctx2["matieres"], [])
check("aucun metrage fabrique", ctx2["metrage"], None)


print("\n4. L'ecran de tracabilite montre bien ces deux choses")
js = Path("static/mysifa_prod_core.js").read_text(encoding="utf-8")
# La designation du dossier faisait doublon avec sa reference et poussait le
# reste de la ligne hors de l'ecran : elle cede sa place au metrage.
check("plus de colonne Designation dans la liste",
      "thSort('designation'" in js, False)
check("une colonne Metrage triable a la place",
      "thSort('metrage','Métrage','right')" in js, True)
check("la provenance du metrage se lit au survol",
      "dos.metrage_source==='of'" in js, True)
check("le detail affiche le metrage du dossier",
      "'Métrage dossier'" in js, True)
check("sans effacer le metrage reellement produit",
      "'Métrage produit'" in js, True)
check("le produit et le format y figurent",
      "'Produit'" in js and "ctx.format" in js, True)
check("et le bloc des matieres necessaires",
      "Matières nécessaires" in js, True)


print()
if ko:
    print(f"ECHEC — {ko} verification(s) en erreur.")
    sys.exit(1)
print("Tous les cas passent.")
