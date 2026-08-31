"""
Fin de production sans aucun code matiere scanne : on demande pourquoi.

Un dossier cloture sans bobine scannee ne dit rien de la matiere qui l'a
produit. Ce n'est pas toujours une faute — un poste de repiquage ne consomme
pas de frontal, une bobine entamee la veille a pu etre scannee sur le dossier
precedent — mais dans la base, l'oubli et la raison legitime ont exactement la
meme allure. C'est precisement la difference qu'un audit FSC de chaine de
controle vient chercher.

Ce que ces cas verrouillent :

  - la colonne existe et la migration est rejouable ;
  - la question ne se pose QUE sur un compteur a zero. Une requete ratee laisse
    le compteur a -1 : bloquer un operateur sur la foi d'un appel reseau rate
    serait pire que le trou qu'on cherche a boucher ;
  - la reponse part avec la saisie et se relit dans le rapport de tracabilite —
    une reponse ecrite nulle part ne servirait a rien ;
  - la traca accepte un code inconnu, a condition de nommer le fournisseur.

Lancer : python3 tests/test_fin_prod_matiere.py
"""
import importlib.util
import re
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


def _charger(chemin, nom):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


print("\n1. La colonne, et une migration rejouable")
mig = _charger("app/core/migrations/2026_08_28_matiere_absente_motif.py",
               "mig_motif")
conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.execute("CREATE TABLE production_data (id INTEGER PRIMARY KEY, "
             "no_dossier TEXT, operation_code TEXT, operateur TEXT, "
             "date_operation TEXT)")
conn.commit()
mig.appliquer(conn)
cols = {r["name"] for r in conn.execute("PRAGMA table_info(production_data)")}
check("la colonne est la", "matiere_absente_motif" in cols, True)
mig.appliquer(conn)
check("rejouable sans casse", True, True)
# Vide par defaut : une valeur par defaut ferait croire a une reponse.
conn.execute("INSERT INTO production_data (no_dossier, operation_code) "
             "VALUES ('D1','89')")
conn.commit()
check("vide par defaut",
      conn.execute("SELECT matiere_absente_motif FROM production_data"
                   ).fetchone()[0], None)


print("\n2. La question ne se pose que sur un compteur a zero")
js = open("app/web/fabrication_page.py", encoding="utf-8").read()
check("le compteur vient du dossier, pas de la machine",
      "'/api/fabrication/matieres?no_dossier='" in js, True)
check("il est charge a l'ouverture de la modale",
      "loadNbMatieresDossier();" in js, True)
# -1 = « on ne sait pas ». Le bloc ne s'affiche que sur un zero franc.
check("un echec reseau ne bloque personne",
      "S.finNbMatieres = -1" in js, True)
check("le bloc ne sort que sur zero",
      "const aucuneMatiere = (S.finNbMatieres === 0);" in js, True)
check("le champ est obligatoire",
      "Aucun code matiere scanne sur ce dossier — indiquez pourquoi." in js, True)
# Deux reponses courantes d'un clic : sans elles, la question se ferait
# repondre « RAS » et on aurait perdu la seule chose qu'elle apporte.
check("les deux reponses courantes sont proposees",
      "Bobine deja scannee sur un dossier precedent" in js
      and "Poste sans matiere" in js, True)
check("la reponse part avec la saisie",
      "body.matiere_absente_motif = motifTxt;" in js, True)


print("\n3. La reponse s'ecrit, et se relit")
api = open("app/routers/fabrication.py", encoding="utf-8").read()
check("elle n'est ecrite que sur une fin de production",
      'if cl["code"] == "89" and motif_absence:' in api, True)
check("une base pas encore migree ne fait pas echouer la saisie",
      bool(re.search(r"matiere_absente_motif=\?.{0,600}?except Exception:", api,
                     re.DOTALL)), True)
check("le rapport de tracabilite la restitue",
      '"motifs_absence_matiere": motifs_absence,' in api, True)
check("et la synthese la resume",
      '"motif_absence_matiere":' in api, True)


print("\n4. Traca : un code inconnu s'ajoute, avec son fournisseur")
# Le parcours existait deja ; il ne doit pas disparaitre au detour d'un
# refactor. Sans fournisseur, le serveur refuse en 409 — c'est ce refus qui
# garantit qu'aucune bobine n'entre en tracabilite sans origine.
check("le serveur exige le fournisseur d'un code non recu",
      'detail="Fournisseur requis — liaison manuelle."' in api, True)
check("l'ecran propose la saisie manuelle",
      "function tracaShowFicheManuelle(" in js, True)
check("il annonce que le code sera quand meme enregistre",
      "Il sera quand même enregistré" in js, True)
check("et le fournisseur est marque obligatoire",
      "Fournisseur (obligatoire)" in js, True)

print("\n5. La reponse remonte dans MyProd > Tracabilite")
# Ecrire la reponse ne sert a rien si les ecrans de tracabilite continuent
# d'afficher un dossier vide. Elle doit sortir partout ou l'absence de
# bobine se lit : liste, detail, rapport FSC, traceur.
import ast as _ast

traca_src = open("app/routers/traca.py", encoding="utf-8").read()

# La fonction s'execute pour de vrai, extraite de sa source : le test ne
# peut pas valider une copie du SQL qui aurait diverge de l'originale.
_fn = next(n for n in _ast.parse(traca_src).body
           if isinstance(n, _ast.FunctionDef) and n.name == "motifs_absence_matiere")
_ns = {"_MAX_NOEUDS": 50}
exec(compile(_ast.Module(body=[_fn], type_ignores=[]), "traca", "exec"), _ns)
motifs_absence_matiere = _ns["motifs_absence_matiere"]

c = sqlite3.connect(":memory:")
c.row_factory = sqlite3.Row
c.execute("CREATE TABLE production_data (id INTEGER PRIMARY KEY, no_dossier TEXT,"
          " operation_code TEXT, operateur TEXT, machine TEXT,"
          " date_operation TEXT, matiere_absente_motif TEXT)")
c.execute("INSERT INTO production_data (no_dossier, operation_code, operateur,"
          " date_operation, matiere_absente_motif) VALUES"
          " ('D1','89','LUC','2026-08-30T10:00','Poste sans matiere')")
# Une saisie de debut, et une fin sans reponse : ni l'une ni l'autre ne doit
# remonter — sinon la vue afficherait une explication qui n'existe pas.
c.execute("INSERT INTO production_data (no_dossier, operation_code, operateur,"
          " date_operation) VALUES ('D1','01','LUC','2026-08-30T08:00')")
c.execute("INSERT INTO production_data (no_dossier, operation_code, operateur,"
          " date_operation, matiere_absente_motif) VALUES"
          " ('D2','89','LUC','2026-08-30T11:00','   ')")
c.commit()
check("la reponse du dossier remonte",
      [r["motif"] for r in motifs_absence_matiere(c, "D1")],
      ["Poste sans matiere"])
check("une reponse blanche ne compte pas",
      motifs_absence_matiere(c, "D2"), [])
check("un dossier sans fin de production ne remonte rien",
      motifs_absence_matiere(c, "D3"), [])

# Base pas encore migree : la vue doit rester lisible, pas planter.
c2 = sqlite3.connect(":memory:")
c2.row_factory = sqlite3.Row
c2.execute("CREATE TABLE production_data (id INTEGER PRIMARY KEY, no_dossier TEXT)")
c2.commit()
check("une base sans la colonne ne casse pas la tracabilite",
      motifs_absence_matiere(c2, "D1"), [])

check("le traceur expose la reponse dans la chaine",
      '"motifs_absence": motifs_absence,' in traca_src, True)
check("et la compte parmi ce que la chaine ne demontre pas",
      "Réponse de l'opérateur" in traca_src, True)

check("l'API Tracabilite la sert avec le detail du dossier",
      '"motifs_absence_matiere": motifs_absence,' in api
      and "motifs_absence_matiere(conn, no_dossier)" in api, True)
check("et la liste distingue l'absence expliquee de l'absence muette",
      "AS motif_absence_matiere" in api, True)

core = open("static/mysifa_prod_core.js", encoding="utf-8").read()
check("le detail du dossier l'affiche",
      "function motifAbsenceMatiereBloc(" in core
      and "motifBloc," in core, True)
check("le rapport FSC l'affiche",
      "motifAbsenceMatiereBloc(data && data.motifs_absence_matiere)" in core, True)
check("le traceur en fait une etape de la chaine",
      "(ch.motifs_absence || []).forEach" in core, True)
check("la liste des dossiers le signale",
      "'Aucune — expliqué'" in core, True)
check("le rapport de l'atelier l'affiche aussi",
      "motifsAbsenceBloc," in js, True)
# Declaratif : la vue ne doit jamais le presenter comme une donnee tracee.
check("et il est annonce comme declaratif",
      "non vérifiable par la chaîne" in core
      and "non vérifiable par la chaîne" in js, True)


print("\n6. Le fournisseur d'une bobine se choisit dans une liste courte")
# Une bobine, c'est un frontal, une glassine ou un complexe. Proposer en plus
# les fournisseurs de colle, de mandrins et de palettes, c'est demander a
# l'operateur de trancher une question de nomenclature au poste, en pleine
# production. Le filtre est donc DUR, et l'elargissement explicite.
check("le filtre porte sur les categories bobine",
      "const CATS_BOBINE = ['frontal', 'glassine', 'complexe'];" in js, True)
check("et c'est un vrai filtre, pas un simple ordre d'affichage",
      "filter: (f) => ficheElargi" in js, True)
# L'adhesif seul (une colle) n'est pas une bobine : il ne doit plus figurer
# dans les categories mises en avant, ici ni sur les ecrans voisins.
check("l'adhesif seul ne figure plus dans les listes de bobines",
      "'frontal', 'adhesif', 'glassine', 'complexe'" in js, False)
for _f in ("app/web/html.py", "static/mysifa_prod_core.js"):
    check(f"idem sur {_f}",
          "'frontal', 'adhesif', 'glassine', 'complexe'"
          in open(_f, encoding="utf-8").read(), False)

# Deux paliers, pas un : l'annuaire complet d'abord, le hors-annuaire ensuite.
# Un operateur qui ne trouve pas son fournisseur ne doit jamais se retrouver
# bloque, mais il ne doit pas non plus sortir de l'annuaire par inadvertance.
check("palier 1 : le bouton rend l'annuaire complet",
      "ficheElargi = true;" in js and "Annuaire complet" in js, True)
check("palier 2 : puis le champ libre",
      "Vraiment pas dans la liste ?" in js and "ficheLibre = true;" in js, True)
check("le champ libre annonce ce qu'il coute",
      "aucun certificat FSC ne sera rattaché" in js, True)
check("et l'ecran affiche « hors annuaire » a la place de la licence",
      "'hors annuaire'" in js, True)
check("l'envoi porte le nom libre quand il n'y a pas d'id",
      "{fournisseur_libre: libre}" in js, True)

# Cote serveur : la voie libre existe, elle ne fabrique pas de faux certificat,
# et le refus 409 reste en place quand rien n'est fourni.
check("le serveur accepte un nom hors annuaire",
      'body.get("fournisseur_libre")' in api, True)
check("un nom deja connu de l'annuaire rejoint sa fiche",
      "_resolve_fournisseur_fsc_id(conn, None, libre)" in api, True)
check("un nom libre n'invente jamais de certificat",
      "fournisseur_manual=?, certificat_fsc_manual=NULL" in api, True)
check("et sans fournisseur du tout, le refus tient toujours",
      'detail="Fournisseur requis — liaison manuelle."' in api, True)


print()
if ko:
    print(f"ECHEC — {ko} verification(s) en erreur.")
    sys.exit(1)
print("Tous les cas passent.")
