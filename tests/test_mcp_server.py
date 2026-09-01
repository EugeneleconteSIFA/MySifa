"""
Serveur MCP : ce qui sort de la base, et surtout ce qui n'en sort pas.

Le MCP ouvre la base de production a un agent externe. Trois choses doivent
rester vraies, sinon la fuite est silencieuse — personne ne voit passer une
lecture reussie :

- les tables hors perimetre (messagerie, RH/paie, calendrier personnel,
  secrets) sont invisibles au schema ET refusees en requete ;
- les colonnes sensibles ne sont ni lues ni utilisables dans un WHERE — un
  filtre sur un mot de passe est un oracle, pas une lecture ;
- rien ne peut ecrire : le validateur refuse les verbes d'ecriture, et la
  connexion elle-meme est ouverte en `mode=ro`.

Plus les bornes qui evitent qu'une requete emporte le serveur : LIMIT force,
une seule instruction.

Le test monte sa propre base temporaire — il ne touche a aucune base du depot.
La partie protocole (initialize / tools/list) n'est jouee que si FastAPI est
installe.

Lancer : python3 tests/test_mcp_server.py
"""

import importlib.util
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
FAIL: list[str] = []


def verifier(libelle, obtenu, attendu):
    if obtenu == attendu:
        print(f"  ok   {libelle}")
    else:
        print(f"  KO   {libelle} : obtenu {obtenu!r}, attendu {attendu!r}")
        FAIL.append(libelle)


def refuse(libelle, fn):
    """Verifie qu'un appel est refuse par une ErreurMCP (et pas par un plantage)."""
    try:
        fn()
    except md.ErreurMCP:
        print(f"  ok   {libelle}")
        return
    except Exception as e:
        print(f"  KO   {libelle} : refus attendu, exception {type(e).__name__} obtenue")
        FAIL.append(libelle)
        return
    print(f"  KO   {libelle} : l'appel est PASSE alors qu'il devait etre refuse")
    FAIL.append(libelle)


# ─── Base temporaire ────────────────────────────────────────────────

tmp = tempfile.mkdtemp(prefix="mcp_test_")
chemin = os.path.join(tmp, "test.db")
conn = sqlite3.connect(chemin)
conn.executescript(
    """
    CREATE TABLE dossiers (id INTEGER PRIMARY KEY, reference TEXT, machine TEXT);
    CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT, password_hash TEXT);
    CREATE TABLE messages (id INTEGER PRIMARY KEY, corps TEXT);
    CREATE TABLE chat_messages (id INTEGER PRIMARY KEY, corps TEXT);
    CREATE TABLE cal_events_perso (id INTEGER PRIMARY KEY, titre TEXT);
    CREATE TABLE sessions (id INTEGER PRIMARY KEY, token TEXT);
    """
)
for i in range(10):
    conn.execute("INSERT INTO dossiers (reference, machine) VALUES (?,?)", (f"REF-{i}", "Cohesio 1"))
conn.execute("INSERT INTO users (email, password_hash) VALUES (?,?)", ("a@b.c", "TRES_SECRET"))
conn.execute("INSERT INTO messages (corps) VALUES ('confidentiel')")
conn.commit()
conn.close()


def _charger(nom, chemin_py):
    spec = importlib.util.spec_from_file_location(nom, chemin_py)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nom] = mod
    spec.loader.exec_module(mod)
    return mod


md = _charger("mcp_data", RACINE / "app" / "services" / "mcp_data.py")
md.BASES = {
    "mysifa": {"chemin": chemin, "description": "base de test"},
    "rvgi": {"chemin": chemin, "description": "base de test"},
}


# ─── 1. Le schema ne montre pas ce qui est hors perimetre ───────────

print("\n1. Perimetre du schema")
tables = {t["table"] for t in md.schema("mysifa")["tables"]}
verifier("les tables metier sont visibles", {"dossiers", "users"} <= tables, True)
verifier(
    "messagerie, calendrier perso et sessions sont invisibles",
    sorted(tables & {"messages", "chat_messages", "cal_events_perso", "sessions"}),
    [],
)
cols = [t["colonnes"] for t in md.schema("mysifa", "users")["tables"]][0]
verifier("la colonne secrete est annoncee masquee", "password_hash (masquée)" in cols, True)


# ─── 2. Rien ne sort des tables hors perimetre ──────────────────────

print("\n2. Tables hors perimetre")
for table in ("messages", "chat_messages", "cal_events_perso", "sessions"):
    refuse(f"SELECT sur {table} refuse", lambda t=table: md.executer_select("mysifa", f"SELECT * FROM {t}"))
refuse("apercu d'une table interdite refuse", lambda: md.apercu_table("mysifa", "messages"))
refuse("jointure vers une table interdite refusee", lambda: md.executer_select(
    "mysifa", "SELECT d.id FROM dossiers d JOIN messages m ON m.id = d.id"))


# ─── 3. Colonnes sensibles : ni lues, ni filtrables ─────────────────

print("\n3. Colonnes sensibles")
refuse("lecture directe d'un secret refusee",
       lambda: md.executer_select("mysifa", "SELECT password_hash FROM users"))
refuse("filtre sur un secret refuse",
       lambda: md.executer_select("mysifa", "SELECT id FROM users WHERE password_hash = 'x'"))
r = md.executer_select("mysifa", "SELECT * FROM users")
verifier("SELECT * masque la valeur du secret", r["lignes"][0]["password_hash"], "«masqué»")
verifier("la colonne masquee est signalee", r["colonnes_masquees"], ["password_hash"])
verifier("l'email reste lisible", r["lignes"][0]["email"], "a@b.c")


# ─── 4. Aucune ecriture possible ────────────────────────────────────

print("\n4. Lecture seule")
for sql in (
    "DELETE FROM dossiers",
    "UPDATE dossiers SET reference = 'x'",
    "INSERT INTO dossiers (reference) VALUES ('x')",
    "DROP TABLE dossiers",
    "PRAGMA table_info(dossiers)",
    "ATTACH DATABASE '/tmp/autre.db' AS a",
):
    refuse(f"refus de « {sql.split()[0]} »", lambda s=sql: md.executer_select("mysifa", s))
refuse("ecriture cachee derriere un SELECT refusee", lambda: md.executer_select(
    "mysifa", "SELECT 1; DELETE FROM dossiers"))

# Ceinture et bretelles : meme en contournant le validateur, la connexion est
# ouverte en lecture seule et c'est SQLite qui refuse.
with md._connexion("mysifa") as c:
    try:
        c.execute("DELETE FROM dossiers")
        print("  KO   la connexion accepte une ecriture")
        FAIL.append("connexion en mode=ro")
    except sqlite3.OperationalError:
        print("  ok   la connexion elle-meme refuse l'ecriture (mode=ro)")


# ─── 5. Bornes d'execution ──────────────────────────────────────────

print("\n5. Bornes")
r = md.executer_select("mysifa", "SELECT * FROM dossiers", 3)
verifier("la limite est appliquee", r["nb_lignes"], 3)
verifier("la troncature est signalee", r["tronque"], True)
r = md.executer_select("mysifa", "SELECT * FROM dossiers", 50)
verifier("sous la limite, rien n'est tronque", (r["nb_lignes"], r["tronque"]), (10, False))
r = md.executer_select("mysifa", "SELECT * FROM dossiers", 99999)
verifier("la limite est plafonnee", r["limite"], md.LIMITE_MAX)
refuse("base inconnue refusee", lambda: md.executer_select("inexistante", "SELECT 1"))
refuse("requete vide refusee", lambda: md.executer_select("mysifa", "   "))


# ─── 6. Protocole MCP (si FastAPI est installe) ─────────────────────

print("\n6. Protocole")
try:
    import fastapi  # noqa: F401
    from app.routers import mcp_server as srv
except Exception as e:
    print(f"  --   saute : {type(e).__name__} a l'import ({e})")
else:
    def rpc(methode, params=None):
        msg = {"jsonrpc": "2.0", "id": 1, "method": methode}
        if params is not None:
            msg["params"] = params
        return srv._traiter(msg)

    r = rpc("initialize", {"protocolVersion": "2025-06-18"})["result"]
    verifier("la version demandee est reprise telle quelle", r["protocolVersion"], "2025-06-18")
    verifier("une version inconnue retombe sur celle par defaut",
             rpc("initialize", {"protocolVersion": "1999-01-01"})["result"]["protocolVersion"],
             srv.VERSION_DEFAUT)
    verifier("les regles de lecture RVGI voyagent avec le serveur",
             "corbeille = 0" in r["instructions"] and "htn" in r["instructions"], True)
    noms = [t["name"] for t in rpc("tools/list")["result"]["tools"]]
    # Quatre outils d'acces brut a la base, quatre outils metier qui appellent
    # le code des ecrans au lieu de recalculer.
    verifier("le catalogue d'outils est complet", sorted(noms), [
        "mysifa_anomalies", "mysifa_apercu_table", "mysifa_bases", "mysifa_dossier",
        "mysifa_metric", "mysifa_resolve", "mysifa_schema", "mysifa_sql",
    ])
    metier = {"mysifa_metric", "mysifa_dossier", "mysifa_resolve", "mysifa_anomalies"}
    verifier("les outils metier sont tous exposes", sorted(metier - set(noms)), [])
    verifier("chaque outil declare un schema d'entree",
             all("inputSchema" in t for t in rpc("tools/list")["result"]["tools"]), True)
    verifier("une notification ne repond pas",
             srv._traiter({"jsonrpc": "2.0", "method": "notifications/initialized"}), None)
    verifier("une methode inconnue renvoie -32601",
             rpc("resources/list")["error"]["code"], -32601)


# ─── Verdict ────────────────────────────────────────────────────────

print("\n" + "=" * 62)
if FAIL:
    print(f"{len(FAIL)} echec(s) :")
    for f in FAIL:
        print(f"  - {f}")
    sys.exit(1)
print("Tous les cas passent.")
