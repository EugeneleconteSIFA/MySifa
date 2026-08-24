"""
Memoire produit : rattachement dossier -> reference, materialisation figee,
savoirs et scans.

Lancer : python3 tests/test_produit_memoire.py
(comme test_migrations_fichiers.py, le script pilote un demarrage complet de
la base — il ne passe pas par unittest)
"""

import contextlib
import io
import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))
os.chdir(RACINE)

FAIL = []


def check(label, got, expected):
    ok = got == expected
    print(("ok   " if ok else "KO   ") + label.ljust(58) + f"{got}"
          + ("" if ok else f"   attendu {expected}"))
    if not ok:
        FAIL.append(label)


db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["DB_PATH"] = db
import config; config.DB_PATH = db
import app.core.database as dbmod; dbmod.DB_PATH = db
with contextlib.redirect_stdout(io.StringIO()):
    dbmod.init_db()

from app.services import produit_memoire as pm

print("--- tables creees par la migration ---")
with dbmod.get_db() as conn:
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
for t in ("produit_series", "produit_documents", "produit_savoirs", "produit_savoirs_utile"):
    check(f"table {t}", t in tables, True)

# ── Jeu d'essai : deux productions de la meme reference, sur deux dossiers ───
REF = "1013/0068"

with dbmod.get_db() as conn:
    # La migration seede deja des machines : on en pose une a nous, avec un id
    # hors de portee du seed, pour ne dependre d'aucun contenu par defaut.
    conn.execute("INSERT OR REPLACE INTO machines (id, nom, code) VALUES (991, 'Cohesio 2', 'CO2')")
    for i, (dos, of_num) in enumerate(((("D-1001"), "9932056"), (("D-1002"), "9932100")), start=1):
        conn.execute(
            "INSERT INTO of_imports (id, of_numero, reference, machine, matiere, ref_adhesif, "
            "outil_1_forme, outil_1_numero, date_import) VALUES (?,?,?,?,?,?,?,?,?)",
            (i, of_num, REF, "Cohesio 2", "PPBLANC", "2028Y", "Rectangle", "F-77", "2026-01-01"),
        )
        conn.execute(
            "INSERT INTO planning_entries (machine_id, position, reference, client, description, "
            "duree_heures, statut, ref_produit, numero_of, of_import_id) "
            "VALUES (991, ?, ?, 'CLIENT TEST', 'Etiquette logistique', 8, 'termine', ?, ?, ?)",
            (i, dos, REF + " - COHESIO 2", of_num, i),
        )
    conn.commit()

    # Le trigger de la migration v101 alimente ref_produit_norm tout seul.
    norm = conn.execute(
        "SELECT ref_produit_norm FROM planning_entries WHERE reference='D-1001'"
    ).fetchone()[0]
check("ref_produit_norm alimente par le trigger", norm, REF)

print("--- resolution dossier -> reference produit ---")
with dbmod.get_db() as conn:
    ctx = pm.contexte_dossier(conn, "D-1001")
check("ref produit resolue", ctx["ref_produit_norm"], REF)
check("machine resolue", ctx["machine"], "Cohesio 2")
check("OF rattache", ctx["of_import_id"], 1)

with dbmod.get_db() as conn:
    inconnu = pm.contexte_dossier(conn, "DOSSIER-INEXISTANT")
check("dossier inconnu non rattache", inconnu["ref_produit_norm"], None)

print("--- saisies de production ---")


def saisie(conn, dos, code, label, quand, **extra):
    cols = ["operateur", "date_operation", "operation", "operation_code",
            "operation_category", "machine", "no_dossier", "data"]
    vals = ["DUPONT", quand, f"{code} - {label}", code,
            "arret" if code in ("50", "54") else ("calage" if code == "02" else "production"),
            "Cohesio 2", dos, "{}"]
    for k, v in extra.items():
        cols.append(k)
        vals.append(v)
    conn.execute(
        f"INSERT INTO production_data ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
        vals,
    )


with dbmod.get_db() as conn:
    saisie(conn, "D-1001", "01", "Debut de production", "2026-03-12T08:00:00", metrage_prevu=1000)
    saisie(conn, "D-1001", "02", "Calage", "2026-03-12T08:10:00")
    saisie(conn, "D-1001", "03", "Production", "2026-03-12T09:00:00",
           commentaire="Contre-partie a regler 2/10e plus bas.")
    saisie(conn, "D-1001", "54", "Probleme Impressions", "2026-03-12T10:00:00")
    saisie(conn, "D-1001", "03", "Production", "2026-03-12T10:30:00")
    saisie(conn, "D-1001", "89", "Fin de production", "2026-03-12T12:00:00",
           metrage_reel=13400, quantite_traitee=42000)

    saisie(conn, "D-1002", "01", "Debut de production", "2026-05-04T08:00:00", metrage_prevu=13400)
    saisie(conn, "D-1002", "02", "Calage", "2026-05-04T08:20:00")
    saisie(conn, "D-1002", "03", "Production", "2026-05-04T09:00:00")
    saisie(conn, "D-1002", "54", "Probleme Impressions", "2026-05-04T10:15:00")
    saisie(conn, "D-1002", "89", "Fin de production", "2026-05-04T11:30:00",
           metrage_reel=22000, quantite_traitee=25000)
    conn.commit()

print("--- materialisation d'une serie ---")
with dbmod.get_db() as conn:
    s1 = pm.materialiser_serie(conn, "D-1001", cloture_par="DUPONT")
check("serie materialisee", bool(s1), True)
check("serie rattachee a la reference", s1["ref_produit_norm"], REF)
check("machine dans la serie", s1["machine"], "Cohesio 2")
check("calage compte", s1["temps_calage_min"] > 0, True)
check("outillage capture", "outil_1_numero" in (s1["outillage"] or ""), True)
check("commentaire capture", "Contre-partie" in (s1["commentaires"] or ""), True)

with dbmod.get_db() as conn:
    pm.materialiser_serie(conn, "D-1001", cloture_par="DUPONT")
    n = conn.execute("SELECT COUNT(*) FROM produit_series WHERE no_dossier='D-1001'").fetchone()[0]
check("materialisation rejouable sans doublon", n, 1)

with dbmod.get_db() as conn:
    rattrapage = pm.rattraper_series(conn)
check("rattrapage materialise le dossier restant", rattrapage["materialisees"], 1)
with dbmod.get_db() as conn:
    check("rattrapage idempotent", pm.rattraper_series(conn)["materialisees"], 0)

print("--- apercu vu depuis Saisieprod ---")
with dbmod.get_db() as conn:
    ap = pm.apercu_pour_dossier(conn, "D-1002")
check("historique disponible sur D-1002", ap["disponible"], True)
check("une seule serie anterieure", ap["nb_series"], 1)

with dbmod.get_db() as conn:
    ap_seul = pm.apercu_pour_dossier(conn, "DOSSIER-INEXISTANT")
check("pas de bouton sur un dossier non rattache", ap_seul["disponible"], False)

print("--- resume produit ---")
with dbmod.get_db() as conn:
    res = pm.resume_produit(conn, REF)
check("deux series sur la reference", res["nb_series"], 2)
check("machine listee", res["machines"], ["Cohesio 2"])
check("mediane de calage calculee", res["medianes"]["calage_min"] is not None, True)
codes = [a["code"] for a in res["arrets_recurrents"]]
check("arret 54 detecte comme recurrent", "54" in codes, True)
if "54" in codes:
    a54 = [a for a in res["arrets_recurrents"] if a["code"] == "54"][0]
    check("54 present sur les 2 series", a54["series"], 2)

print("--- savoirs ---")
with dbmod.get_db() as conn:
    conn.execute(
        "INSERT INTO produit_savoirs (ref_produit_norm, type, texte, auteur, created_at) "
        "VALUES (?,?,?,?,?)",
        (REF, "reglage", "Contre-partie 2/10e plus bas.", "DUPONT", pm.now_iso()),
    )
    conn.commit()
    savoirs = pm.savoirs_produit(conn, REF)
check("savoir visible", len(savoirs), 1)
check("libelle de type resolu", savoirs[0]["type_label"], "Reglage")

with dbmod.get_db() as conn:
    conn.execute("UPDATE produit_savoirs SET obsolete=1 WHERE id=1")
    conn.commit()
    check("savoir perime masque par defaut", len(pm.savoirs_produit(conn, REF)), 0)
    check("savoir perime toujours lisible", len(pm.savoirs_produit(conn, REF, True)), 1)

print("--- taux de rattachement ---")
with dbmod.get_db() as conn:
    taux = pm.taux_rattachement(conn)
check("deux dossiers termines", taux["dossiers_termines"], 2)
check("deux series", taux["series_materialisees"], 2)
check("taux a 100 %", taux["taux"], 1.0)
check("une reference multi-series", taux["references_multi_series"], 1)

print("--- diagnostic : reference qui a tourne mais pas encore reprise ---")
with dbmod.get_db() as conn:
    conn.execute("DELETE FROM produit_series")
    conn.commit()
    manquants = pm.dossiers_non_materialises(conn, REF)
check("les deux dossiers sont vus comme a reprendre", sorted(manquants), ["D-1001", "D-1002"])

print("--- rattrapage par lots (limit + offset) ---")
with dbmod.get_db() as conn:
    lot1 = pm.rattraper_series(conn, limit=1, offset=0)
    lot2 = pm.rattraper_series(conn, limit=1, offset=0)
check("premier lot", lot1["materialisees"], 1)
check("second lot", lot2["materialisees"], 1)
with dbmod.get_db() as conn:
    check("plus rien a reprendre", pm.dossiers_non_materialises(conn, REF), [])
    check("les deux series sont la", pm.taux_rattachement(conn)["series_materialisees"], 2)

print("--- normalisation de reference ---")
check("variante machine ignoree", pm._norm("1013/0068 - COHESIO 2 - L570"), "1013/0068")
check("tiret tolere", pm._norm("1315-0004"), "1315/0004")
check("chaine non conforme", pm._norm("sans reference"), None)

print()
if FAIL:
    print(f"{len(FAIL)} echec(s) : " + ", ".join(FAIL))
    sys.exit(1)
print("Tous les controles passent.")
