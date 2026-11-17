"""
MyExpe — activer une grille tarifaire remplace l'ancienne sur ses zones.

L'import CSV ajoute des lignes en brouillon ; « Valider » les activait sans
toucher aux lignes deja actives. La recherche de tarif ignore les dates de
validite : apres l'import de la grille CEVA 2027, chaque departement avait
deux lignes actives par tranche et le comparateur prenait l'une ou l'autre.

Ce que ce test verrouille :

- une ligne active de meme type / base / zone, sur une tranche qui chevauche,
  est supprimee a l'activation ;
- une zone absente de la nouvelle grille (international) garde ses tarifs ;
- une autre base de calcul (palette vs poids) n'est pas touchee ;
- une activation partielle (ids) ne remplace que ce que couvrent ces ids ;
- les lignes remplacees ne repassent pas en brouillon (un « Tout activer »
  ulterieur les ressusciterait) ;
- un autre transporteur n'est jamais touche.

Lancer : python3 tests/test_expe_tarifs_remplacement.py
"""

import _base_temporaire  # noqa: F401  — base jetable, avant tout le reste
import sqlite3

import database  # noqa: E402,F401  — toujours avant tout app.*
from app.routers.expe_departs import _activer_tarifs_brouillon  # noqa: E402

ECHECS = []


def check(label, obtenu, attendu=True):
    ok = obtenu == attendu
    print(("ok   " if ok else "KO   ") + label.ljust(62)
          + ("" if ok else f"{obtenu!r}   attendu {attendu!r}"))
    if not ok:
        ECHECS.append(label)


def base():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute(
        """CREATE TABLE expe_tarifs (
               id INTEGER PRIMARY KEY, transporteur_id INTEGER, type_envoi TEXT,
               base_calcul TEXT, zone_type TEXT, zone_valeur TEXT,
               tranche_min REAL, tranche_max REAL, prix REAL, unite TEXT,
               actif INTEGER)"""
    )
    return c


def ajout(c, trp, base_c, zone, tmin, tmax, prix, actif):
    return c.execute(
        """INSERT INTO expe_tarifs (transporteur_id, type_envoi, base_calcul,
               zone_type, zone_valeur, tranche_min, tranche_max, prix, unite, actif)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (trp, "messagerie", base_c, "departement", zone, tmin, tmax, prix,
         "forfait", actif),
    ).lastrowid


def actifs(c, trp=2):
    return sorted(
        (r["base_calcul"], r["zone_valeur"], r["tranche_min"], r["prix"])
        for r in c.execute(
            "SELECT * FROM expe_tarifs WHERE transporteur_id=? AND actif=1", (trp,)
        )
    )


# ─── Tout activer : la grille France remplace l'ancienne ─────────────
c = base()
ajout(c, 2, "poids", "01", 1, 10, 19.07, 1)
ajout(c, 2, "poids", "01", 11, 20, 20.25, 1)
ajout(c, 2, "poids", "Italie 00", 1, 10, 30.0, 1)
ajout(c, 2, "palette", "01", 1, 1, 94.0, 1)
ajout(c, 3, "poids", "01", 1, 10, 50.0, 1)
ajout(c, 2, "poids", "01", 1, 10, 20.21, 0)
ajout(c, 2, "poids", "01", 11, 20, 21.47, 0)

res = _activer_tarifs_brouillon(c, 2)
check("deux lignes activees", res["activees"], 2)
check("deux anciennes remplacees", res["remplacees"], 2)
check("lignes actives restantes", res["actives"], 4)
check("nouveaux prix France, international et palette intacts", actifs(c), [
    ("palette", "01", 1.0, 94.0),
    ("poids", "01", 1.0, 20.21),
    ("poids", "01", 11.0, 21.47),
    ("poids", "Italie 00", 1.0, 30.0),
])
check("aucun brouillon ressuscitable",
      c.execute("SELECT COUNT(*) FROM expe_tarifs WHERE actif=0").fetchone()[0], 0)
check("autre transporteur intact", actifs(c, 3), [("poids", "01", 1.0, 50.0)])

# ─── Activation partielle : seule la tranche choisie remplace ────────
c = base()
ajout(c, 2, "poids", "59", 1, 10, 19.41, 1)
ajout(c, 2, "poids", "59", 11, 20, 18.85, 1)
choisi = ajout(c, 2, "poids", "59", 1, 10, 20.57, 0)
ajout(c, 2, "poids", "59", 11, 20, 19.98, 0)

res = _activer_tarifs_brouillon(c, 2, [choisi])
check("partiel : une activee, une remplacee",
      (res["activees"], res["remplacees"]), (1, 1))
check("partiel : l'autre tranche garde l'ancien prix", actifs(c), [
    ("poids", "59", 1.0, 20.57),
    ("poids", "59", 11.0, 18.85),
])
check("partiel : le brouillon non choisi reste brouillon",
      c.execute("SELECT COUNT(*) FROM expe_tarifs WHERE actif=0").fetchone()[0], 1)

# ─── Tranche ouverte et decoupage different ──────────────────────────
c = base()
ajout(c, 2, "poids", "75", 101, 200, 32.0, 1)
ajout(c, 2, "poids", "75", 201, None, 29.0, 1)
ajout(c, 2, "poids", "75", 1, 10, 20.0, 1)
ajout(c, 2, "poids", "75", 151, 300, 31.0, 0)
res = _activer_tarifs_brouillon(c, 2)
check("chevauchement et tranche ouverte remplaces", res["remplacees"], 2)
check("tranche sans chevauchement gardee", actifs(c), [
    ("poids", "75", 1.0, 20.0),
    ("poids", "75", 151.0, 31.0),
])

print()
if ECHECS:
    print(f"{len(ECHECS)} echec(s)")
    raise SystemExit(1)
print("tout passe")
