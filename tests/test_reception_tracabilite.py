# -*- coding: utf-8 -*-
"""L'import depuis une liste ne touche pas au compteur — et sa suppression non plus.

Ce test protège l'arbitrage du 09/09/2026. Il ne vérifie pas « le code appelle
la bonne fonction » mais la propriété qui compte pour le magasin : après un
import de traçabilité, le compteur de stock est à l'octet ce qu'il était avant,
et le supprimer ne le fait pas descendre.

Le deuxième cas est le plus important des deux : c'est celui qui, s'il cassait,
créerait du stock négatif silencieux. Une entrée oubliée se voit à l'inventaire ;
une sortie fantôme se voit six mois plus tard.
"""

from __future__ import annotations

import os
import sqlite3
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

ECHECS: list[str] = []


def verifie(condition, libelle: str) -> None:
    if condition:
        print("  ok   %s" % libelle)
    else:
        print("  ECHEC %s" % libelle)
        ECHECS.append(libelle)


def egal(obtenu, attendu, libelle: str) -> None:
    verifie(obtenu == attendu, "%s (obtenu %r, attendu %r)" % (libelle, obtenu, attendu))


# ── Une base minimale : uniquement ce que le chemin testé touche ──────────
SCHEMA = """
CREATE TABLE stock_receptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT, created_by TEXT, created_by_name TEXT, note TEXT,
    nb_bobines INTEGER DEFAULT 0, fournisseur TEXT, fournisseur_id INTEGER,
    fsc_type_claim TEXT, certificat_fsc TEXT, lot_numero TEXT,
    certificat_valide TEXT, certificat_expiration TEXT, certificat_note TEXT,
    rvgi_qte_attendue REAL);
CREATE TABLE stock_reception_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reception_id INTEGER, code_barre TEXT, scanned_at TEXT,
    matiere_id INTEGER, laize_id INTEGER, doublon_note TEXT);
CREATE TABLE mp_stock_laize (
    matiere_id INTEGER, laize_id INTEGER, quantite REAL DEFAULT 0,
    updated_at TEXT, updated_by_name TEXT,
    PRIMARY KEY (matiere_id, laize_id));
CREATE TABLE mp_stock (
    matiere_id INTEGER PRIMARY KEY, quantite REAL DEFAULT 0,
    updated_at TEXT, updated_by_name TEXT);
CREATE TABLE mp_mouvements (
    id INTEGER PRIMARY KEY AUTOINCREMENT, matiere_id INTEGER, laize_id INTEGER,
    type_mouvement TEXT, quantite REAL,
    quantite_avant REAL, quantite_apres REAL,
    ref_bl TEXT, note TEXT, emplacement_source TEXT, emplacement_dest TEXT,
    prix_eur_m2 REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT, created_by_name TEXT);
"""


def base() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


# ── 1. La migration ajoute la colonne sans réécrire l'histoire ────────────
print("\n1. Migration reception_items_impacte_stock")
print("-" * 46)

import importlib.util as _iu

_chemin_mig = os.path.join(RACINE, "app", "core", "migrations",
                           "2026_09_09_reception_tracabilite.py")
_spec = _iu.spec_from_file_location("mig_traca", _chemin_mig)
_mig = _iu.module_from_spec(_spec)
_spec.loader.exec_module(_mig)

conn = base()
conn.execute(
    "INSERT INTO stock_reception_items (reception_id, code_barre, matiere_id, "
    "laize_id, doublon_note) VALUES (1,'ANCIENNE-1',7,3,'Packing list x.xlsx')")
conn.execute(
    "INSERT INTO stock_reception_items (reception_id, code_barre, matiere_id, "
    "laize_id) VALUES (1,'ANCIENNE-2',7,3)")
conn.commit()

_mig.appliquer(conn)
cols = {r[1] for r in conn.execute('PRAGMA table_info("stock_reception_items")')}
verifie("impacte_stock" in cols, "la colonne existe")
vals = [r[0] for r in conn.execute(
    "SELECT impacte_stock FROM stock_reception_items ORDER BY id")]
egal(vals, [1, 1], "les lignes existantes restent a 1 (elles ont bien compte)")

# Rejouable : c'est la règle du dépôt, une migration se rejoue sans casser.
_mig.appliquer(conn)
egal([r[0] for r in conn.execute(
    "SELECT impacte_stock FROM stock_reception_items ORDER BY id")], [1, 1],
    "rejouer la migration ne change rien")


# ── 2. La défalque ignore les lignes de traçabilité ───────────────────────
print("\n2. _defalquer_bobines")
print("-" * 46)

# On charge la fonction seule : importer le routeur entier tirerait FastAPI,
# les sessions et la moitié de l'application pour tester vingt lignes.
src = open(os.path.join(RACINE, "app", "routers", "stock.py"),
           encoding="utf-8").read()
debut = src.index("def _defalquer_bobines(")
fin = src.index("\n@router.delete", debut)
ns: dict = {}
exec(compile(src[debut:fin], "stock_defalque", "exec"), ns)
defalquer = ns["_defalquer_bobines"]

conn = base()
conn.execute("INSERT INTO mp_stock_laize (matiere_id, laize_id, quantite) "
             "VALUES (7, 3, 100)")
conn.commit()
user = {"email": "test@sifa", "nom": "Test"}

# a) deux bobines scannées : le stock descend de 2
recap = defalquer(conn, [
    {"matiere_id": 7, "laize_id": 3, "impacte_stock": 1},
    {"matiere_id": 7, "laize_id": 3, "impacte_stock": 1},
], "LOT-A", user, "Test scan")
q = conn.execute("SELECT quantite FROM mp_stock_laize WHERE matiere_id=7 "
                 "AND laize_id=3").fetchone()["quantite"]
egal(q, 98.0, "deux bobines scannees : le compteur descend de 2")
egal(recap["nb_bobines_stock"], 2, "le recap compte 2 bobines")

# b) trois bobines de traçabilité : le stock ne bouge PAS
recap = defalquer(conn, [
    {"matiere_id": 7, "laize_id": 3, "impacte_stock": 0},
    {"matiere_id": 7, "laize_id": 3, "impacte_stock": 0},
    {"matiere_id": 7, "laize_id": 3, "impacte_stock": 0},
], "LOT-B", user, "Test tracabilite")
q = conn.execute("SELECT quantite FROM mp_stock_laize WHERE matiere_id=7 "
                 "AND laize_id=3").fetchone()["quantite"]
egal(q, 98.0, "trois bobines de tracabilite : le compteur ne bouge pas")
egal(recap["nb_bobines_stock"], 0, "aucune bobine n'a impacte le stock")
egal(recap["bobines_tracabilite"], 3, "le recap nomme les 3 bobines ignorees")

# c) un lot mixte : seules les scannées descendent
recap = defalquer(conn, [
    {"matiere_id": 7, "laize_id": 3, "impacte_stock": 1},
    {"matiere_id": 7, "laize_id": 3, "impacte_stock": 0},
], "LOT-C", user, "Test mixte")
q = conn.execute("SELECT quantite FROM mp_stock_laize WHERE matiere_id=7 "
                 "AND laize_id=3").fetchone()["quantite"]
egal(q, 97.0, "lot mixte : seule la bobine scannee descend")
egal(recap["bobines_tracabilite"], 1, "l'autre est comptee comme tracabilite")

# d) absence de la clé (lignes d'avant la migration) : comportement d'avant
recap = defalquer(conn, [{"matiere_id": 7, "laize_id": 3}], "LOT-D", user, "Test")
q = conn.execute("SELECT quantite FROM mp_stock_laize WHERE matiere_id=7 "
                 "AND laize_id=3").fetchone()["quantite"]
egal(q, 96.0, "sans la cle, on defalque comme avant (defaut 1)")

# e) le plancher à zéro tient toujours
conn.execute("UPDATE mp_stock_laize SET quantite=1 WHERE matiere_id=7 AND laize_id=3")
recap = defalquer(conn, [
    {"matiere_id": 7, "laize_id": 3, "impacte_stock": 1},
    {"matiere_id": 7, "laize_id": 3, "impacte_stock": 1},
    {"matiere_id": 7, "laize_id": 3, "impacte_stock": 1},
], "LOT-E", user, "Test plancher")
q = conn.execute("SELECT quantite FROM mp_stock_laize WHERE matiere_id=7 "
                 "AND laize_id=3").fetchone()["quantite"]
egal(q, 0.0, "le plancher a zero tient")
verifie(bool(recap["ecarts"]), "l'ecart est inscrit plutot que tu")


# ── 3. L'import de liste n'écrit plus de mouvement ────────────────────────
print("\n3. packing_list_importer — lecture du code")
print("-" * 46)

debut = src.index('@router.post("/api/stock/packing-list/importer")')
fin = src.index("def _pl_origine_metrage", debut)
corps = src[debut:fin]

verifie("appliquer_mouvement_mp" not in corps,
        "aucun appel a appliquer_mouvement_mp dans l'import")
verifie("impacte_stock" in corps and "VALUES (?, ?, ?, ?, ?, ?, 0)" in corps,
        "les lignes inserees portent impacte_stock = 0")
verifie('"stock_modifie": False' in corps,
        "la reponse dit explicitement que le stock n'a pas bouge")
verifie("repartition" in corps,
        "la repartition par laize est rendue pour l'ecran")


# ── 4. Le stock réel additionne les deux moitiés ──────────────────────────
print("\n4. Stock reel : releve + standard")
print("-" * 46)

bloc = src[src.index("b = bobines_par_mat.get(int(r[\"id\"]))"):]
bloc = bloc[:bloc.index("out.append(d)")]
verifie('"mixte"' in bloc, "une source « mixte » existe")
verifie("bobines_hors_suivi" in bloc, "la part non suivie est nommee")


def stock_reel(compteur, suivies, metrage_suivi, standard, sans=0):
    """Reproduit la regle du routeur, pour la verifier sur des cas nommes."""
    reste = max(0, int(round(compteur)) - suivies)
    if reste and standard > 0:
        return round(metrage_suivi + reste * standard, 1), "mixte"
    return round(metrage_suivi, 1), "bobines"


# Le cas réel du 09/09 : 442 au compteur, 96 suivies, 18 100 m de standard.
val, srcn = stock_reel(442, 96, 1735140.0, 18100.0)
egal(srcn, "mixte", "442 bobines dont 96 suivies : source mixte")
egal(val, 7997740.0, "le total additionne les deux moities")
# Controle d'ordre de grandeur : le tableau par laize de l'ecran totalise
# 8 000 200 m pour cette reference. On tombe a 0,03 % — c'est le signe que
# la moitie completee au standard est bien calee sur le compteur.
verifie(abs(val - 8000200.0) / 8000200.0 < 0.01,
        "le total colle au tableau par laize a moins de 1 %")
verifie(val > 1735140.0,
        "et il est superieur a la seule somme des bobines suivies")

# Tout suivi : on retombe sur le relevé pur.
val, srcn = stock_reel(96, 96, 1735140.0, 18100.0)
egal(srcn, "bobines", "fleet entierement suivie : source bobines")
egal(val, 1735140.0, "le total est le releve exact")

# Plus de bobines suivies que le compteur : on ne complete pas, l'ecart
# appartient a la carte « Ecarts au compteur ».
val, srcn = stock_reel(50, 96, 1735140.0, 18100.0)
egal(srcn, "bobines", "suivi > compteur : pas de completion")

# Sans metrage standard, on ne complete pas au hasard.
val, srcn = stock_reel(442, 96, 1735140.0, 0.0)
egal(srcn, "bobines", "sans standard connu : pas de completion inventee")


# ── 5. L'etiquette porte le lot fournisseur ───────────────────────────────
print("\n5. Etiquette de tracabilite")
print("-" * 46)

page = open(os.path.join(RACINE, "app", "web", "stock_page.py"),
            encoding="utf-8").read()
verifie("lot_fournisseur: (lot.lot_fournisseur || '')" in page,
        "le payload d'impression porte lot_fournisseur")
verifie(page.count("lot_fournisseur: b.lot_fournisseur || ''") == 1,
        "la serie par bobine passe le lot de SA bobine")
verifie("lot_fournisseur: bobine.lot_fournisseur || ''" in page,
        "la reimpression unitaire aussi")
verifie('"lot_fournisseur": b["lot_fournisseur"]' in src,
        "l'historique des receptions rend le lot fournisseur")


print("\n" + "=" * 46)
if ECHECS:
    print("%d echec(s) :" % len(ECHECS))
    for e in ECHECS:
        print("  - %s" % e)
    sys.exit(1)
print("Tout est vert.")
