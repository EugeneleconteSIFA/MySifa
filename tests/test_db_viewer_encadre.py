# -*- coding: utf-8 -*-
"""
Le Database Viewer (/db) ne sort que ce que l'encadrement autorise.

Pourquoi ce test existe. `/db` a longtemps servi n'importe quelle table et
n'importe quelle colonne à la direction et au super-admin : `users` avec son
hash, `api_keys`, `sessions`, `paie_*`, `audit_logs`, `chat_messages`. Et son
`ai-query` faisait exécuter à Claude du SQL validé par une expression
régulière — un filtre de texte, qui ne sait pas ce qu'une requête va lire.
Le viewer a été rebranché sur `app/services/diagnostic_sql.py`, donc sur
l'autoriseur SQLite.

Ce test attaque les fonctions du router contre la VRAIE liste blanche, pas
contre une configuration de test. C'est volontaire : il doit échouer le jour
où quelqu'un ajoute `users` à `TABLES_LISIBLES` sans y avoir réfléchi.

`app.services.auth_service` est remplacé par un double — l'authentification se
teste ailleurs, et brancher la vraie chaîne ferait de ce test un test
d'intégration. Le garde, lui, est bien vérifié : chaque endpoint doit refuser
un rôle qui n'y a pas droit.

Lancer : python3 tests/test_db_viewer_encadre.py
"""

import os
import sqlite3
import sys
import tempfile
import types
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

_TMP = tempfile.mkdtemp()
CHEMIN = os.path.join(_TMP, "viewer.db")
# Posé avant le premier import de config : c'est cette base que le router lira.
os.environ["DB_PATH"] = CHEMIN

# ─── Double de app.services.auth_service ──────────────────────────────────
_UTILISATEUR = {"role": "superadmin", "email": "sa@test.local"}
_faux_auth = types.ModuleType("app.services.auth_service")
_faux_auth.get_current_user = lambda request: dict(_UTILISATEUR)
sys.modules["app.services.auth_service"] = _faux_auth

from app.routers import db_viewer as V              # noqa: E402
from app.services import diagnostic_sql as D        # noqa: E402
from app.services import db_ai_query as IA          # noqa: E402
from fastapi import HTTPException                   # noqa: E402

_ECHECS = []
_RIEN = object()


def ok(libelle, valeur, attendu=_RIEN):
    bon = bool(valeur) if attendu is _RIEN else (valeur == attendu)
    if not bon:
        _ECHECS.append(libelle)
    print(("ok   " if bon else "ECHEC") + " " + libelle.ljust(56) + " " + repr(valeur)[:64])


def refuse(libelle, appel, code_attendu=None):
    """Vérifie que l'appel est bloqué, et par quel code."""
    try:
        appel()
    except HTTPException as e:
        bon = code_attendu is None or e.status_code == code_attendu
        if not bon:
            _ECHECS.append(libelle)
        print(("ok   " if bon else "ECHEC") + " " + libelle.ljust(56) + " " + str(e.status_code))
        return
    except (D.DiagnosticRefus, D.DiagnosticTropLong) as e:
        print("ok   " + libelle.ljust(56) + " " + str(e)[:60])
        return
    _ECHECS.append(libelle)
    print("ECHEC " + libelle.ljust(56) + " PASSE ALORS QUE CA DEVAIT ETRE BLOQUE")


# Tables réelles : les noms comptent, la liste blanche est celle de production.
TABLES_FERMEES = ["users", "api_keys", "sessions", "paie_employes",
                  "audit_logs", "chat_messages"]


def depot_de_test():
    con = sqlite3.connect(CHEMIN)
    con.executescript("""
        CREATE TABLE machines (id INTEGER PRIMARY KEY, nom TEXT, actif INTEGER);
        CREATE TABLE production_data (id INTEGER PRIMARY KEY, no_dossier TEXT, operateur TEXT, metrage_reel REAL);
        CREATE TABLE arret_seuils_franchis (id INTEGER PRIMARY KEY, saisie_id INTEGER, no_dossier TEXT,
            machine TEXT, operateur TEXT, regle TEXT, duree_saisie_min REAL, explication_texte TEXT);
        CREATE TABLE perf_releves (id INTEGER PRIMARY KEY, email TEXT, poste TEXT, score INTEGER);
        CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT, password_hash TEXT, role TEXT);
        CREATE TABLE api_keys (id INTEGER PRIMARY KEY, nom TEXT, secret TEXT);
        CREATE TABLE sessions (id INTEGER PRIMARY KEY, token TEXT, user_id INTEGER);
        CREATE TABLE paie_employes (id INTEGER PRIMARY KEY, salarie TEXT, brut REAL);
        CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, action TEXT, objet TEXT);
        CREATE TABLE chat_messages (id INTEGER PRIMARY KEY, auteur TEXT, texte TEXT);
    """)
    con.execute("INSERT INTO machines VALUES (1,'Cohésio 1',1)")
    con.execute("INSERT INTO machines VALUES (2,'Repiquage',1)")
    con.execute("INSERT INTO production_data VALUES (1,'REF-4521','DUPONT Jean',1200.0)")
    con.execute("INSERT INTO arret_seuils_franchis VALUES "
                "(1,12,'REF-4521','Cohésio 1','DUPONT Jean','3x calage',45.0,'bourrage papier')")
    con.execute("INSERT INTO perf_releves VALUES (1,'eleconte@sifa.pro','PC-ATELIER-2',88)")
    con.execute("INSERT INTO users VALUES (1,'eleconte@sifa.pro','$2b$12$secret','superadmin')")
    con.execute("INSERT INTO api_keys VALUES (1,'Pont Access','sk-secret')")
    con.execute("INSERT INTO sessions VALUES (1,'tok-secret',1)")
    con.execute("INSERT INTO paie_employes VALUES (1,'X',3200.0)")
    con.execute("INSERT INTO audit_logs VALUES (1,'LOGIN','sa@test.local')")
    con.execute("INSERT INTO chat_messages VALUES (1,'Fatou','message privé')")
    con.commit()
    con.close()


def main():
    global _UTILISATEUR
    depot_de_test()

    print("--- la liste blanche elle-même ---")
    for t in TABLES_FERMEES:
        ok("%s reste hors liste blanche" % t, t in D.TABLES_LISIBLES, False)
    ok("le masquage de arret_seuils_franchis est déclaré",
       ("arret_seuils_franchis", "operateur") in D.COLONNES_MASQUEES
       and ("arret_seuils_franchis", "explication_texte") in D.COLONNES_MASQUEES, True)
    ok("le masquage de perf_releves.email est déclaré",
       ("perf_releves", "email") in D.COLONNES_MASQUEES, True)

    print("\n--- garde d'accès ---")
    _UTILISATEUR = {"role": "comptabilite"}
    refuse("stats refusé à la comptabilité", lambda: V.db_stats(None), 403)
    refuse("tables refusé à la comptabilité", lambda: V.db_tables(None), 403)
    refuse("schema refusé à la comptabilité", lambda: V.db_table_schema("machines", None), 403)
    refuse("rows refusé à la comptabilité",
           lambda: V.db_table_rows("machines", None, 1, 50, None, None, "ASC"), 403)
    _UTILISATEUR = {"role": "superadmin"}

    print("\n--- les tables fermées ne s'ouvrent pas ---")
    for t in TABLES_FERMEES:
        refuse("schema %s" % t, lambda t=t: V.db_table_schema(t, None), 404)
        refuse("rows %s" % t, lambda t=t: V.db_table_rows(t, None, 1, 50, None, None, "ASC"), 404)

    liste = V.db_tables(None)
    noms = {t["name"] for t in liste}
    ok("aucune table fermée dans la liste du viewer",
       sorted(noms & set(TABLES_FERMEES)), [])
    ok("le viewer ne liste que la liste blanche", noms <= D.TABLES_LISIBLES, True)
    ok("machines est bien listée", "machines" in noms, True)

    print("\n--- colonnes masquées ---")
    schema = V.db_table_schema("arret_seuils_franchis", None)
    masquees = sorted(c["name"] for c in schema if c["masquee"])
    ok("le schéma signale les colonnes masquées", masquees, ["explication_texte", "operateur"])

    r = V.db_table_rows("arret_seuils_franchis", None, 1, 50, None, None, "ASC")
    par_nom = dict(zip(r["columns"], r["rows"][0]))
    ok("la ligne remonte", par_nom["no_dossier"], "REF-4521")
    ok("le contexte de débogage est intact", par_nom["duree_saisie_min"], 45.0)
    ok("l'opérateur revient NULL", par_nom["operateur"], None)
    ok("la justification revient NULL", par_nom["explication_texte"], None)

    r = V.db_table_rows("perf_releves", None, 1, 50, None, None, "ASC")
    par_nom = dict(zip(r["columns"], r["rows"][0]))
    ok("perf_releves reste lisible", par_nom["poste"], "PC-ATELIER-2")
    ok("l'e-mail revient NULL", par_nom["email"], None)

    print("\n--- la recherche ne reconstitue pas ce qui est masqué ---")
    r = V.db_table_rows("arret_seuils_franchis", None, 1, 50, "DUPONT", None, "ASC")
    ok("chercher une valeur masquée ne trouve rien", r["total"], 0)
    r = V.db_table_rows("arret_seuils_franchis", None, 1, 50, "bourrage", None, "ASC")
    ok("chercher dans la justification ne trouve rien", r["total"], 0)
    r = V.db_table_rows("arret_seuils_franchis", None, 1, 50, "REF-4521", None, "ASC")
    ok("chercher une valeur visible trouve la ligne", r["total"], 1)
    r = V.db_table_rows("production_data", None, 1, 50, "DUPONT", None, "ASC")
    ok("l'opérateur de production_data, lui, reste cherchable", r["total"], 1)

    print("\n--- stats ---")
    s = V.db_stats(None)
    ok("le décompte de tables est celui de la liste blanche",
       s["table_count"], len(D.TABLES_LISIBLES))
    # 2 machines + 1 production_data + 1 arret_seuils_franchis + 1 perf_releves.
    # Les 6 lignes des tables fermées ne sont pas dans le total.
    ok("les lignes des tables fermées ne sont pas comptées", s["total_rows"], 5)

    print("\n--- ai-query : ce que le modèle voit, et ce qu'il peut exécuter ---")
    schema_ia = IA.build_schema_snapshot()
    for t in TABLES_FERMEES:
        ok("le schéma envoyé au modèle tait %s" % t, ("- %s:" % t) in schema_ia, False)
    ok("il tait aussi password_hash", "password_hash" in schema_ia, False)
    ok("il tait les colonnes masquées", "explication_texte" in schema_ia, False)
    ok("mais il décrit bien les tables lisibles", "- machines:" in schema_ia, True)

    refuse("un SQL généré vers users est refusé à l'exécution",
           lambda: IA.execute_select("SELECT email, password_hash FROM users"))
    refuse("un SQL généré vers la paie est refusé",
           lambda: IA.execute_select("SELECT * FROM paie_employes"))
    refuse("un SQL généré qui écrit est refusé",
           lambda: IA.execute_select("DELETE FROM machines"))
    res = IA.execute_select("SELECT nom FROM machines ORDER BY id")
    ok("un SQL généré légitime passe", res["rows"], [["Cohésio 1"], ["Repiquage"]])

    print("\n--- la base n'a pas bougé ---")
    con = sqlite3.connect(CHEMIN)
    ok("les machines sont toujours là",
       con.execute("SELECT COUNT(*) FROM machines").fetchone()[0], 2)
    ok("le hash est toujours en base, simplement inatteignable",
       con.execute("SELECT password_hash FROM users").fetchone()[0], "$2b$12$secret")
    con.close()

    print("\n" + ("TOUT EST VERT" if not _ECHECS else
                  "DES VERIFICATIONS ONT ECHOUE : " + ", ".join(_ECHECS)))
    return 0 if not _ECHECS else 1


if __name__ == "__main__":
    raise SystemExit(main())
