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

print()
if ko:
    print(f"ECHEC — {ko} verification(s) en erreur.")
    sys.exit(1)
print("Tous les cas passent.")
