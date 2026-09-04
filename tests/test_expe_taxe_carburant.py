"""
MyExpe — la taxe carburant entre dans le prix compare.

Elle est saisie sur la fiche transporteur (`taxe_carburant_pct`, de 12 a 26 %
selon le transporteur) et n'entrait dans aucun calcul : le comparateur
affichait un prix hors gasoil, jusqu'a un quart sous le prix facture, et
CLASSAIT les transporteurs sur ce prix-la. Deux transporteurs a 100 € de
transport mais 12 % et 26 % de gasoil sortaient a egalite.

Ce que ce test verrouille :

- la taxe s'applique au transport, pas aux frais annexes ;
- elle s'applique APRES la mini perception (c'est le transport facture qui
  porte le gasoil, pas le prix theorique) ;
- une grille qui porte deja sa propre ligne gasoil (parseur CEVA) fait foi :
  la taxe de fiche est ignoree, jamais comptee deux fois ;
- une taxe a zero ne cree aucune ligne — l'ecran de detail reste celui d'avant
  pour les transporteurs sans gasoil negocie ;
- le detail de calcul montre la ligne, avec son pourcentage et son montant :
  un prix qui monte sans explication vaut un prix faux.

Lancer : python3 tests/test_expe_taxe_carburant.py
"""

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

_TMP = tempfile.mkdtemp(prefix="mysifa_txc_")
os.environ["DB_PATH"] = os.path.join(_TMP, "test.db")

import database  # noqa: E402,F401  — toujours avant tout app.* (cf. CLAUDE.md)
from app.routers.expe_departs import (  # noqa: E402
    _appliquer_frais,
    _calculer_prix_base,
)

ECHECS = []


def check(label, obtenu, attendu=True):
    ok = obtenu == attendu
    print(("ok   " if ok else "KO   ") + label.ljust(62)
          + ("" if ok else f"{obtenu!r}   attendu {attendu!r}"))
    if not ok:
        ECHECS.append(label)


def conn_frais(lignes):
    """Base en memoire avec les seuls frais annexes utiles au calcul."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute(
        """CREATE TABLE expe_tarifs_frais (
               id INTEGER PRIMARY KEY, transporteur_id INTEGER, libelle TEXT,
               mode TEXT, valeur REAL, mini REAL, applique_defaut INTEGER)"""
    )
    for lg in lignes:
        c.execute(
            "INSERT INTO expe_tarifs_frais "
            "(transporteur_id,libelle,mode,valeur,mini,applique_defaut) "
            "VALUES (1,?,?,?,?,?)",
            (lg["libelle"], lg["mode"], lg["valeur"], lg.get("mini"),
             lg.get("applique_defaut", 1)),
        )
    return c


def ligne_tarif(**kw):
    """Une ligne de grille, sous la forme que `_calculer_prix_base` attend."""
    base = {"unite": "forfait", "prix": 100.0, "mini_perception": None,
            "base_calcul": "palette"}
    base.update(kw)
    return base


# ── 1. La taxe s'applique au transport ─────────────────────────────────────
c = conn_frais([])
frais, total = _appliquer_frais(c, 1, 100.0, 2, 18.16)
check("une ligne de taxe carburant est ajoutee", len(frais), 1)
check("son montant est le pourcentage du transport", round(total, 2), 18.16)
check("elle est libellee", frais[0]["libelle"], "Taxe carburant")
check("le detail porte le pourcentage", "18.16 %" in frais[0]["detail"])
check("le detail porte le montant", "18.16 €" in frais[0]["detail"])

# ── 2. Zero taxe = ecran inchange ──────────────────────────────────────────
frais, total = _appliquer_frais(conn_frais([]), 1, 100.0, 2, 0)
check("une taxe a zero ne cree aucune ligne", frais, [])
check("et n'ajoute rien au total", total, 0.0)
frais, total = _appliquer_frais(conn_frais([]), 1, 100.0, 2, None)
check("une taxe absente ne cree aucune ligne", frais, [])

# ── 3. Elle porte sur le transport, pas sur les frais annexes ──────────────
c = conn_frais([{"libelle": "Taxe surete", "mode": "forfait_expedition",
                 "valeur": 50.0}])
frais, total = _appliquer_frais(c, 1, 100.0, 2, 20.0)
check("la taxe ignore les frais annexes", round(total, 2), 70.0)
taxe_l = [f for f in frais if f["libelle"] == "Taxe carburant"][0]
check("elle vaut 20 % des 100 € de transport", taxe_l["montant"], 20.0)

# ── 4. Pas de double comptage avec une ligne gasoil de grille ──────────────
for libelle in ("Gasoil", "Surcharge carburant", "Fuel surcharge"):
    c = conn_frais([{"libelle": libelle, "mode": "pct_transport", "valeur": 12.0}])
    frais, total = _appliquer_frais(c, 1, 100.0, 2, 18.16)
    check(f"« {libelle} » de la grille fait foi", round(total, 2), 12.0)
    check(f"aucune ligne ajoutee en plus de « {libelle} »", len(frais), 1)

# Une ligne gasoil NON appliquee par defaut n'entre pas dans le total : la taxe
# de fiche reprend alors son role.
c = conn_frais([{"libelle": "Gasoil", "mode": "pct_transport", "valeur": 12.0,
                 "applique_defaut": 0}])
frais, total = _appliquer_frais(c, 1, 100.0, 2, 18.16)
check("une ligne gasoil desactivee laisse la taxe de fiche s'appliquer",
      round(total, 2), 18.16)

# ── 5. La taxe suit la mini perception ─────────────────────────────────────
prix_base, _detail = _calculer_prix_base(
    ligne_tarif(unite="au_100kg", prix=10.0, mini_perception=80.0,
                base_calcul="poids"),
    poids=100.0, nb_pal=0,
)
check("la mini perception releve le transport", prix_base, 80.0)
frais, total = _appliquer_frais(conn_frais([]), 1, prix_base, 0, 25.0)
check("la taxe porte sur le transport facture, pas sur le prix theorique",
      round(total, 2), 20.0)

# ── 6. Ce que ca change au classement ──────────────────────────────────────
# Deux transporteurs a 100 € de transport : celui qui a 12 % de gasoil doit
# passer devant celui qui en a 26. C'est exactement ce que le comparateur ne
# savait pas faire.
a = 100.0 + _appliquer_frais(conn_frais([]), 1, 100.0, 1, 12.0)[1]
b = 100.0 + _appliquer_frais(conn_frais([]), 1, 100.0, 1, 25.6)[1]
check("a transport egal, le gasoil departage", a < b)
check("et l'ecart est celui des deux taxes", round(b - a, 2), 13.6)

print()
if ECHECS:
    print(f"ECHEC : {len(ECHECS)} verification(s)")
    sys.exit(1)
print("Toutes les verifications passent.")
