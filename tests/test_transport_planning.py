"""
Contrainte transport : ce qui declenche, ce qui ne declenche pas, ce qui bloque.

La regle n'a d'interet que si elle reste muette sur la routine. Ces cas
verrouillent les six decisions prises avec SIFA le 02/09/2026 :

- 6 palettes declenche, 5 ne declenche pas — le seuil est inclusif ;
- un seul depart au-dessus du seuil suffit, meme si un autre est plus petit ;
- MyExpe donne les palettes, la fiche technique sert de repli, et sans ni
  l'une ni l'autre on ne devine pas ;
- un depart deja passe ne contraint plus rien ;
- la marge majore la duree sans jamais toucher `duree_heures` ;
- un dossier deja en retard n'est pas bloque tant qu'on ne l'aggrave pas.

Le service ne connait ni FastAPI ni l'application : il prend une connexion
sqlite. Le test tourne donc en memoire, sans dependance.

Lancer : python3 tests/test_transport_planning.py
"""

import importlib.util
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def _charger(nom: str, chemin: Path):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tp = _charger("transport_planning", RACINE / "app" / "services" / "transport_planning.py")
mig = _charger(
    "mig_transport",
    RACINE / "app" / "core" / "migrations" / "2026_09_02_transport_planning.py",
)

FAIL = []
AUJ = date(2026, 9, 2)


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
    mig.appliquer(conn)
    return conn


def depart(conn, entry_id, jour, palettes, transporteur="CEVA", statut="en_attente"):
    cur = conn.execute(
        """INSERT INTO expe_departs
             (date_enlevement, transporteur, nb_palette, statut, planning_entry_id)
           VALUES (?,?,?,?,?)""",
        (jour, transporteur, palettes, statut, entry_id),
    )
    did = cur.lastrowid
    conn.execute(
        """INSERT INTO expe_depart_dossiers (depart_id, planning_entry_id, created_at)
           VALUES (?,?,?)""",
        (did, entry_id, "2026-09-01T08:00:00"),
    )
    conn.commit()
    return did


DOSSIER = {"id": 1, "statut": "attente", "reference": "9932259", "duree_heures": 10.0}


def contraintes(conn, entries=None, palettes=None):
    return tp.contraintes_pour(
        conn, entries or [DOSSIER], palettes or {}, aujourdhui=AUJ
    )


# ── 1. Le seuil de palettes ────────────────────────────────────────────────
print("\n1. Seuil de palettes — 6 declenche, 5 non")

conn = base()
depart(conn, 1, "2026-09-04", 6.0)
verifier("6 palettes : dossier contraint", 1 in contraintes(conn), True)

conn = base()
depart(conn, 1, "2026-09-04", 5.0)
verifier("5 palettes : rien", contraintes(conn), {})

conn = base()
depart(conn, 1, "2026-09-04", 20.0)
verifier("20 palettes : dossier contraint", 1 in contraintes(conn), True)

# ── 2. Plusieurs departs sur un meme dossier ───────────────────────────────
print("\n2. Plusieurs departs — un seul au-dessus du seuil suffit")

conn = base()
depart(conn, 1, "2026-09-10", 11.0, "MEHEZ")
depart(conn, 1, "2026-09-04", 3.0, "CEVA")
c = contraintes(conn)
verifier("un gros et un petit : contraint", 1 in c, True)
verifier("le petit depart est ignore", c[1]["palettes"], 11.0)
verifier("la limite vient du gros depart", c[1]["date_enlevement"], "2026-09-10")

conn = base()
depart(conn, 1, "2026-09-10", 8.0, "MEHEZ")
depart(conn, 1, "2026-09-04", 7.0, "CEVA")
c = contraintes(conn)
verifier("deux gros : le plus proche impose la limite", c[1]["date_enlevement"], "2026-09-04")
verifier("les deux restent listes pour l'infobulle", len(c[1]["departs"]), 2)

# ── 3. D'ou viennent les palettes ──────────────────────────────────────────
print("\n3. Palettes — MyExpe d'abord, la fiche technique en repli")

conn = base()
depart(conn, 1, "2026-09-04", None)
verifier("nb_palette vide et pas de repli : rien", contraintes(conn), {})

conn = base()
depart(conn, 1, "2026-09-04", None)
c = contraintes(conn, palettes={1: 9})
verifier("nb_palette vide, repli fiche : contraint", 1 in c, True)
verifier("le repli est signale comme tel", c[1]["source_palettes"], "dossier")

conn = base()
depart(conn, 1, "2026-09-04", 7.0)
c = contraintes(conn, palettes={1: 2})
verifier("MyExpe l'emporte sur le repli", c[1]["palettes"], 7.0)
verifier("source MyExpe", c[1]["source_palettes"], "expe")

conn = base()
depart(conn, 1, "2026-09-04", None)
verifier("repli en dessous du seuil : rien", contraintes(conn, palettes={1: 4}), {})

# ── 4. Ce qui ne contraint pas ─────────────────────────────────────────────
print("\n4. Departs passes, dossiers termines, regle desactivee")

conn = base()
depart(conn, 1, "2026-09-01", 12.0)
verifier("enlevement d'hier : rien", contraintes(conn), {})

conn = base()
depart(conn, 1, "2026-09-02", 12.0)
verifier("enlevement du jour : contraint", 1 in contraintes(conn), True)

conn = base()
depart(conn, 1, "2026-09-04", 12.0)
fini = [{**DOSSIER, "statut": "termine"}]
verifier("dossier termine : rien a contraindre", contraintes(conn, entries=fini), {})

conn = base()
depart(conn, 1, "2026-09-04", 12.0)
tp.enregistrer_params(conn, {"actif": False})
verifier("regle desactivee : rien", contraintes(conn), {})
tp.enregistrer_params(conn, {"actif": True})
verifier("reactivee : contraint de nouveau", 1 in contraintes(conn), True)

# ── 5. Les parametres ──────────────────────────────────────────────────────
print("\n5. Parametres — valeurs par defaut, bornes, seuil deplacable")

conn = base()
p = tp.charger_params(conn)
verifier("defaut heure limite", p["heure_limite"], 11.0)
verifier("defaut seuil", p["seuil_palettes"], 6.0)
verifier("defaut marge", p["marge_pct"], 20.0)

tp.enregistrer_params(conn, {"seuil_palettes": 10})
depart(conn, 1, "2026-09-04", 8.0)
verifier("seuil monte a 10 : 8 palettes ne declenchent plus", contraintes(conn), {})

erreur = None
try:
    tp.enregistrer_params(conn, {"marge_pct": 500})
except ValueError as e:
    erreur = str(e)
verifier("marge de 500 % refusee", erreur is not None, True)
verifier("la marge n'a pas bouge", tp.charger_params(conn)["marge_pct"], 20.0)

conn = base()
tp.enregistrer_params(conn, {"heure_limite": 8.5})
depart(conn, 1, "2026-09-04", 9.0)
verifier("heure limite reglee a 8h30",
         contraintes(conn)[1]["limite"], datetime(2026, 9, 4, 8, 30))

# ── 6. La marge de duree ───────────────────────────────────────────────────
print("\n6. Marge — elle majore la duree, elle n'ecrit rien")

conn = base()
depart(conn, 1, "2026-09-04", 9.0)
c = contraintes(conn)[1]
verifier("20 % sur 10 h", tp.duree_effective(10.0, c), 12.0)
verifier("marge isolee", tp.marge_heures(10.0, c), 2.0)
verifier("sans contrainte, duree inchangee", tp.duree_effective(10.0, None), 10.0)
verifier("le dossier n'a pas ete modifie", DOSSIER["duree_heures"], 10.0)

conn = base()
tp.enregistrer_params(conn, {"marge_pct": 0})
depart(conn, 1, "2026-09-04", 9.0)
verifier("marge a 0 %", tp.duree_effective(10.0, contraintes(conn)[1]), 10.0)

# ── 7. Tension affichee ────────────────────────────────────────────────────
print("\n7. Tension — vert, ambre, rouge")

conn = base()
depart(conn, 1, "2026-09-04", 9.0)
c = contraintes(conn)[1]
verifier("large avance : ok", tp.tension(c, datetime(2026, 9, 2, 10, 0)), "ok")
verifier("moins d'une journee : juste", tp.tension(c, datetime(2026, 9, 4, 6, 0)), "juste")
verifier("apres la limite : depasse", tp.tension(c, datetime(2026, 9, 4, 14, 0)), "depasse")
verifier("pile a l'heure : ok", tp.tension(c, datetime(2026, 9, 3, 11, 0)), "ok")
verifier("sans contrainte : ok", tp.tension(None, datetime(2026, 9, 9)), "ok")

# ── 8. Ce qui est refuse ───────────────────────────────────────────────────
print("\n8. Violations — on refuse ce qui aggrave, pas ce qui existe deja")

conn = base()
depart(conn, 1, "2026-09-04", 9.0)
cs = contraintes(conn)
lim = cs[1]["limite"]
tot = datetime(2026, 9, 3, 8, 0)
apres = lim + timedelta(hours=5)

verifier("dans les temps : rien",
         tp.violations([DOSSIER], cs, {1: tot}, {1: tot}), [])
verifier("le geste fait rater : refuse",
         len(tp.violations([DOSSIER], cs, {1: tot}, {1: apres})), 1)
verifier("deja en retard, geste neutre : laisse passer",
         tp.violations([DOSSIER], cs, {1: apres}, {1: apres}), [])
verifier("deja en retard, geste qui ameliore : laisse passer",
         tp.violations([DOSSIER], cs, {1: apres}, {1: lim + timedelta(hours=1)}), [])
verifier("deja en retard, geste qui aggrave : refuse",
         len(tp.violations([DOSSIER], cs, {1: apres}, {1: apres + timedelta(hours=3)})), 1)
verifier("aggravation d'une seconde : sous la tolerance, laisse passer",
         tp.violations([DOSSIER], cs, {1: apres}, {1: apres + timedelta(seconds=1)}), [])

v = tp.violations([DOSSIER], cs, {1: tot}, {1: apres})
msg = v[0]["message"]
verifier("le message nomme le dossier", "9932259" in msg, True)
verifier("le message donne la limite", "04/09/2026 à 11h" in msg, True)
verifier("le message donne la fin calculee", "Fin calculée" in msg, True)
verifier("le message nomme le transporteur", "CEVA" in msg, True)
verifier("aucun emoji dans le message", all(ord(ch) < 0x2190 for ch in msg), True)

# ── 9. Le rattachement fait foi dans la table de liaison ───────────────────
print("\n9. Rattachement — la table de liaison et le miroir donnent le meme resultat")

conn = base()
conn.execute(
    """INSERT INTO expe_departs
         (date_enlevement, transporteur, nb_palette, statut, planning_entry_id)
       VALUES ('2026-09-04','COQUELLE',9,'en_attente',1)"""
)
conn.commit()
verifier("miroir seul (sans ligne de liaison) : vu quand meme", 1 in contraintes(conn), True)

conn = base()
did = depart(conn, 1, "2026-09-04", 9.0)
conn.execute("UPDATE expe_departs SET planning_entry_id=NULL WHERE id=?", (did,))
conn.commit()
verifier("liaison seule (sans miroir) : vue aussi", 1 in contraintes(conn), True)
verifier("pas de doublon de depart", len(contraintes(conn)[1]["departs"]), 1)

print()
if FAIL:
    print(f"ECHEC : {len(FAIL)} cas")
    for f in FAIL:
        print("  -", f)
    sys.exit(1)
print("Contrainte transport : tous les cas passent.")
