"""
Rattachement OF <-> dossier : triggers et migration de rattrapage.

Lancer : python3 tests/test_autolink_of_dossier.py
"""

import os, sys, tempfile, io, contextlib, importlib.util
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

spec = importlib.util.spec_from_file_location(
    "mig_autolink", "app/core/migrations/2026_09_22_autolink_of_dossier.py")
MIG = importlib.util.module_from_spec(spec); spec.loader.exec_module(MIG)


def of(conn, numero, pdf=""):
    cur = conn.execute(
        "INSERT INTO of_imports (of_numero, reference, pdf_filename) VALUES (?,?,?)",
        (numero, "965/0001", pdf))
    return int(cur.lastrowid)


def dossier(conn, reference, numero_of=None, **extra):
    cols = {"machine_id": 1, "position": 1, "reference": reference,
            "numero_of": numero_of, "statut": "attente"}
    cols.update(extra)
    noms = list(cols)
    cur = conn.execute(
        f"INSERT INTO planning_entries ({', '.join(noms)}) "
        f"VALUES ({', '.join('?' * len(noms))})", [cols[n] for n in noms])
    return int(cur.lastrowid)


def colonne(conn, eid):
    return conn.execute(
        "SELECT of_import_id FROM planning_entries WHERE id=?", (eid,)).fetchone()[0]


def liens(conn, eid):
    return [r[0] for r in conn.execute(
        "SELECT of_import_id FROM planning_of_links WHERE planning_entry_id=? "
        "ORDER BY position, id", (eid,))]


print("--- triggers : le dossier cree apres son OF ---")
with dbmod.get_db() as conn:
    conn.execute("INSERT OR IGNORE INTO machines (id, nom) VALUES (1,'Cohesio 1')")

    of1 = of(conn, "9932467-68-69-70-71")
    d1 = dossier(conn, "9932467-68-69-70-71", "9932467-68-69-70-71")
    check("colonne renseignee a la creation", colonne(conn, d1), of1)
    check("lien cree a la creation", liens(conn, d1), [of1])

    # Copie de dossier (second creneau) : la colonne est recopiee, le lien doit suivre.
    d2 = dossier(conn, "copie", "9932467-68-69-70-71", of_import_id=of1)
    check("copie de dossier : lien recree depuis la colonne", liens(conn, d2), [of1])
    check("copie de dossier : colonne inchangee", colonne(conn, d2), of1)

    # Numero d'OF pose apres coup.
    d3 = dossier(conn, "sans numero", None)
    check("pas de numero d'OF : rien", (colonne(conn, d3), liens(conn, d3)), (None, []))
    conn.execute("UPDATE planning_entries SET numero_of=? WHERE id=?",
                 ("9932467-68-69-70-71", d3))
    check("numero pose apres coup : rattache", colonne(conn, d3), of1)

    # Arbitrage humain : on ne le defait pas.
    d4 = dossier(conn, "detache", "9932467-68-69-70-71", of_link_user_managed=1)
    check("detachement humain respecte", (colonne(conn, d4), liens(conn, d4)), (None, []))

    # Numero inconnu : pas de rattachement au petit bonheur.
    d5 = dossier(conn, "inconnu", "0000000")
    check("numero sans OF : rien", colonne(conn, d5), None)

    # PDF prioritaire sur l'anciennete, entre deux OF de meme numero.
    of_sans = of(conn, "9932500")
    of_avec = of(conn, "9932500", pdf="of_9932500.pdf")
    of_recent = of(conn, "9932500")
    d6 = dossier(conn, "9932500", "9932500")
    check("l'OF avec PDF l'emporte", colonne(conn, d6), of_avec)
    check("les OF sans PDF ne sont pas rattaches",
          of_sans not in liens(conn, d6) and of_recent not in liens(conn, d6), True)

    # Suppression : les liens ne survivent pas au dossier.
    conn.execute("DELETE FROM planning_entries WHERE id=?", (d2,))
    check("liens purges a la suppression du dossier", liens(conn, d2), [])
    conn.commit()

print("\n--- migration : rattrapage de l'existant ---")
with dbmod.get_db() as conn:
    # On remet la base dans l'etat d'avant : triggers de rattachement absents.
    for t in ("trg_pe_autolink_of_ins", "trg_pe_autolink_of_upd",
              "trg_pe_of_lien_depuis_colonne", "trg_pe_purge_of_links_del"):
        conn.execute(f"DROP TRIGGER IF EXISTS {t}")

    of7 = of(conn, "9932600")
    d7 = dossier(conn, "9932600", "9932600")
    check("sans trigger : dossier non rattache", colonne(conn, d7), None)

    # Deux OF de meme numero : la migration laisse arbitrer.
    of(conn, "9932700"); of(conn, "9932700")
    d8 = dossier(conn, "9932700", "9932700")

    # Lien orphelin (dossier supprime) et lien vers un OF disparu.
    conn.execute("INSERT INTO planning_of_links "
                 "(planning_entry_id, of_import_id, position) VALUES (999999, ?, 0)", (of7,))
    of_mort = of(conn, "9932800")
    d9 = dossier(conn, "9932800", "9932800", of_import_id=of_mort)
    conn.execute("DELETE FROM of_imports WHERE id=?", (of_mort,))
    conn.commit()

    with contextlib.redirect_stdout(io.StringIO()) as bilan:
        MIG.appliquer(conn)
    print("   " + bilan.getvalue().strip())

    check("dossier rattrape", colonne(conn, d7), of7)
    check("dossier rattrape : lien cree", liens(conn, d7), [of7])
    check("dossier ambigu laisse a arbitrer", colonne(conn, d8), None)
    check("colonne pointant un OF supprime remise a NULL", colonne(conn, d9), None)
    check("liens orphelins purges", conn.execute(
        "SELECT COUNT(*) FROM planning_of_links "
        "WHERE planning_entry_id NOT IN (SELECT id FROM planning_entries)").fetchone()[0], 0)
    check("liens vers un OF supprime purges", conn.execute(
        "SELECT COUNT(*) FROM planning_of_links "
        "WHERE of_import_id NOT IN (SELECT id FROM of_imports)").fetchone()[0], 0)

    # Rejouabilite.
    with contextlib.redirect_stdout(io.StringIO()):
        MIG.appliquer(conn)
    check("second passage sans effet de bord", liens(conn, d7), [of7])
    check("colonne et premier lien d'accord partout", conn.execute(
        """SELECT COUNT(*) FROM planning_entries pe
           WHERE COALESCE(pe.of_import_id, -1) <> COALESCE(
             (SELECT of_import_id FROM planning_of_links
               WHERE planning_entry_id = pe.id ORDER BY position, id LIMIT 1), -1)"""
    ).fetchone()[0], 0)
    conn.commit()

os.unlink(db)
print()
if FAIL:
    print(f"{len(FAIL)} echec(s) : " + ", ".join(FAIL))
    sys.exit(1)
print("Tout est vert.")
