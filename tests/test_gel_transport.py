"""
Gel H-48 : quand un dossier se fige, et ce qui declenche la confirmation.

La regle a ete decidee avec SIFA le 04/09/2026, apres constat que la
contrainte transport du 02/09 laissait passer l'essentiel du probleme : tant
qu'un camion restait theoriquement tenable, un dossier pouvait glisser autant
de fois qu'on voulait, sans que personne ait a signer le glissement.

Ces cas verrouillent les decisions prises :

- la fenetre se calcule sur l'heure limite du camion, pas sur minuit ;
- le gel IGNORE le seuil de palettes — c'est son seul ecart avec la contrainte
  transport, et il est volontaire ;
- il ne se declenche que sur du retard AJOUTE : avancer un dossier gele, ou
  atteindre la meme fin a la minute pres, ne demande rien ;
- un dossier qu'on vient d'inserer n'a pas de fin d'avant, donc pas d'alerte ;
- un dossier termine ne se gele pas, il est deja produit ;
- l'interrupteur `gel_actif` rend la regle totalement muette.

Lancer : python3 tests/test_gel_transport.py
"""

import importlib.util
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def _charger(nom: str, chemin: Path):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tp = _charger("transport_planning", RACINE / "app" / "services" / "transport_planning.py")
mig_tr = _charger(
    "mig_transport",
    RACINE / "app" / "core" / "migrations" / "2026_09_02_transport_planning.py",
)
mig_gel = _charger(
    "mig_gel",
    RACINE / "app" / "core" / "migrations" / "2026_09_04_gel_transport.py",
)

FAIL = []


def verifier(cas: str, obtenu, attendu):
    if obtenu != attendu:
        FAIL.append(f"{cas} : obtenu {obtenu!r}, attendu {attendu!r}")
        print(f"  ECHEC  {cas} — obtenu {obtenu!r}, attendu {attendu!r}")
    else:
        print(f"  ok     {cas}")


def base():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE expe_departs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_enlevement TEXT, transporteur TEXT, transporteur_id INTEGER,
            nb_palette REAL, statut TEXT, client TEXT, no_cde_transport TEXT,
            planning_entry_id INTEGER);
        CREATE TABLE expe_depart_dossiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            depart_id INTEGER NOT NULL, planning_entry_id INTEGER NOT NULL,
            no_dossier TEXT, created_at TEXT, created_by TEXT);
        """
    )
    mig_tr.appliquer(conn)
    mig_gel.appliquer(conn)
    return conn


def depart(conn, entry_id, jour, palettes, transporteur="CEVA"):
    cur = conn.execute(
        """INSERT INTO expe_departs
             (date_enlevement, transporteur, nb_palette, statut, planning_entry_id)
           VALUES (?,?,?,?,?)""",
        (jour, transporteur, palettes, "en_attente", entry_id),
    )
    did = cur.lastrowid
    conn.execute(
        """INSERT INTO expe_depart_dossiers (depart_id, planning_entry_id, created_at)
           VALUES (?,?,?)""",
        (did, entry_id, "2026-09-01T08:00:00"),
    )
    conn.commit()
    return did


DOSSIER = {"id": 1, "statut": "attente", "reference": "9932259",
           "numero_of": "9932259", "duree_heures": 10.0}


def geles(conn, quand, entries=None):
    return tp.dossiers_geles(conn, entries or [DOSSIER], maintenant=quand)


# ── 1. Les parametres ───────────────────────────────────────────────────────
print("\n1. Parametres — le gel est actif a 48 h par defaut")

conn = base()
p = tp.charger_params(conn)
verifier("gel actif au seed", p["gel_actif"], True)
verifier("fenetre de 48 h au seed", p["gel_heures"], 48.0)
verifier("l'heure limite reste celle du transport", p["heure_limite"], 11.0)

p = tp.enregistrer_params(conn, {"gel_heures": 24})
verifier("fenetre modifiable", p["gel_heures"], 24.0)
verifier("le reste ne bouge pas", p["seuil_palettes"], 6.0)

try:
    tp.enregistrer_params(conn, {"gel_heures": 900})
    verifier("fenetre hors bornes refusee", "acceptee", "ValueError")
except ValueError:
    verifier("fenetre hors bornes refusee", "ValueError", "ValueError")

# ── 2. La fenetre ───────────────────────────────────────────────────────────
print("\n2. Fenetre — 48 h avant l'heure limite, pas avant minuit")

conn = base()
depart(conn, 1, "2026-09-04", 9.0)   # limite : 04/09 11h → gel des le 02/09 11h

verifier("02/09 10h : pas encore gele", geles(conn, datetime(2026, 9, 2, 10, 0)), {})
g = geles(conn, datetime(2026, 9, 2, 11, 0))
verifier("02/09 11h pile : gele", 1 in g, True)
verifier("le debut de gel est expose", g[1]["gel_debut_iso"], "2026-09-02T11:00:00")
verifier("la limite est celle du camion", g[1]["limite_iso"], "2026-09-04T11:00:00")
verifier("03/09 08h : gele", 1 in geles(conn, datetime(2026, 9, 3, 8, 0)), True)
verifier("04/09 14h, camion parti le matin : toujours gele",
         1 in geles(conn, datetime(2026, 9, 4, 14, 0)), True)

# ── 3. Le seuil de palettes ne s'applique pas ───────────────────────────────
print("\n3. Palettes — le gel ne connait pas le seuil de la contrainte transport")

conn = base()
depart(conn, 1, "2026-09-04", 2.0)
quand = datetime(2026, 9, 3, 8, 0)
verifier("2 palettes : hors contrainte transport",
         tp.contraintes_pour(conn, [DOSSIER], {}, aujourdhui=quand.date()), {})
verifier("2 palettes : gele quand meme", 1 in geles(conn, quand), True)

conn = base()
depart(conn, 1, "2026-09-04", None)
verifier("palettes inconnues : gele quand meme", 1 in geles(conn, quand), True)

conn = base()
verifier("aucun depart : pas de gel", geles(conn, quand), {})

conn = base()
depart(conn, 1, "2026-09-30", 9.0)
verifier("camion lointain : pas de gel", geles(conn, quand), {})

# ── 4. Ce qui ne se gele pas ────────────────────────────────────────────────
print("\n4. Etats — un dossier termine est deja produit")

conn = base()
depart(conn, 1, "2026-09-04", 9.0)
termine = [{**DOSSIER, "statut": "termine"}]
verifier("dossier termine : pas de gel", geles(conn, quand, termine), {})

conn = base()
depart(conn, 1, "2026-09-04", 9.0)
tp.enregistrer_params(conn, {"gel_actif": False})
verifier("interrupteur a 0 : plus aucun gel", geles(conn, quand), {})

# ── 5. Ce qui declenche la confirmation ─────────────────────────────────────
print("\n5. Alertes — seul le retard ajoute compte")

conn = base()
depart(conn, 1, "2026-09-04", 9.0)
gels = geles(conn, quand)
FIN = datetime(2026, 9, 4, 6, 0)   # 5 h de battement avant le camion de 11 h


def alertes(avant, apres, entries=None):
    return tp.alertes_gel(entries or [DOSSIER], gels, {1: avant}, {1: apres})


verifier("fin repoussee de 3 h : une alerte", len(alertes(FIN, FIN + timedelta(hours=3))), 1)
verifier("fin avancee : rien", alertes(FIN, FIN - timedelta(hours=3)), [])
verifier("fin identique : rien", alertes(FIN, FIN), [])
verifier("30 secondes de derive de calcul : rien",
         alertes(FIN, FIN + timedelta(seconds=30)), [])
verifier("dossier sans fin d'avant (insere) : rien",
         tp.alertes_gel([DOSSIER], gels, {}, {1: FIN}), [])

a = alertes(FIN, FIN + timedelta(hours=3))[0]
verifier("l'alerte nomme le dossier", a["reference"], "9932259")
verifier("l'ecart est en heures", a["ecart_h"], 3.0)
verifier("3 h de plus tient encore le camion", a["depasse_limite"], False)
verifier("le message nomme le dossier", a["message"].startswith("9932259 —"), True)

a = alertes(FIN, datetime(2026, 9, 4, 15, 0))[0]
verifier("passe 11h, le camion est rate", a["depasse_limite"], True)
verifier("et le message le dit", "apres l'heure limite" in a["message"], True)

# ── 6. Le resume affiche en tete de fenetre ─────────────────────────────────
print("\n6. Resume — singulier, pluriel, et la fenetre en clair")

un = alertes(FIN, FIN + timedelta(hours=3))
verifier("un dossier", tp.resume_gel(un), "Ce geste repousse un dossier dont le camion part dans moins de 48 h.")
verifier("deux dossiers", tp.resume_gel(un + un),
         "Ce geste repousse 2 dossiers dont le camion part dans moins de 48 h.")
verifier("aucun dossier", tp.resume_gel([]), "")

print()
if FAIL:
    print(f"ECHEC : {len(FAIL)} cas")
    for f in FAIL:
        print("  -", f)
    sys.exit(1)
print("Gel H-48 : tous les cas passent.")
