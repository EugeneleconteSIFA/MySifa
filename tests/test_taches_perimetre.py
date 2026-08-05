"""
Périmètre de service du gestionnaire de tâches — `python3 tests/test_taches_perimetre.py`.

Ce qui est vérifié, c'est le cloisonnement : à chaque niveau d'accès, qu'est-ce
qui remonte et surtout qu'est-ce qui ne remonte pas. Le test attaque la clause
SQL produite par `_scope_sql` sur une vraie base SQLite, parce que c'est elle
qui est réellement exécutée en production — un test sur la fonction Python
seule laisserait passer une erreur de jointure ou d'ordre de paramètres.

`services.auth_service` est remplacé par un double : le router n'a besoin que
de connaître le niveau et le rôle effectif, et brancher la vraie chaîne
d'authentification ferait de ce test un test d'intégration.
"""

import os
import sqlite3
import sys
import types

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

# ─── Double de services.auth_service ──────────────────────────────────────
# Posé AVANT l'import du router : c'est ce module-là qu'il importera.
_faux = types.ModuleType("services.auth_service")
_faux.effective_role = lambda u: (u or {}).get("role") or ""
_faux.get_current_user = lambda request: {}
_faux.user_access_level = lambda u, app, module="_app": (u or {}).get("niveau", "none")
_faux.user_can = lambda u, app, module="_app", min_level="read": True
_paquet = types.ModuleType("services")
_paquet.auth_service = _faux
sys.modules.setdefault("services", _paquet)
sys.modules["services.auth_service"] = _faux

_db = types.ModuleType("database")
_db.get_db = lambda: None
sys.modules["database"] = _db

from app.routers import taches as R  # noqa: E402


# ─── Jeu d'essai ──────────────────────────────────────────────────────────
# 1 Eugène (superadmin) · 2 Fatou et 3 Karim (fabrication) · 4 Luc (logistique)
TACHES = [
    # (id, titre,              service,        createur)
    (1, "Refonte du portail", "superadmin",   1),
    (2, "Changer les lames",  "fabrication",  2),
    (3, "Ranger la zone Z1",  "fabrication",  3),
    (4, "Palettes Europe",    "logistique",   4),
    (5, "Demande de Luc",     "logistique",   4),
]
ASSIGNES = [(2, 2), (3, 2), (5, 2)]   # Fatou est assignée aux tâches 2, 3 et 5


def base():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE taches (id INTEGER PRIMARY KEY, titre TEXT, service TEXT,"
        "                     createur_user_id INTEGER, deleted_at TEXT);"
        "CREATE TABLE taches_assignes (tache_id INTEGER, user_id INTEGER);"
    )
    conn.executemany("INSERT INTO taches VALUES (?,?,?,?,NULL)", TACHES)
    conn.executemany("INSERT INTO taches_assignes VALUES (?,?)", ASSIGNES)
    conn.commit()
    return conn


def visibles(conn, user):
    scope, params = R._scope_sql(user)
    return sorted(
        r["id"] for r in conn.execute(
            f"SELECT t.id FROM taches t WHERE t.deleted_at IS NULL AND {scope}", params
        )
    )


def verifier(cas, obtenu, attendu):
    if obtenu != attendu:
        raise AssertionError(f"{cas} : {obtenu} au lieu de {attendu}")
    print(f"  ok  {cas} -> {obtenu}")


def main():
    conn = base()
    fatou_read = {"id": 2, "role": "fabrication", "niveau": "read"}
    fatou_write = {"id": 2, "role": "fabrication", "niveau": "write"}
    luc_write = {"id": 4, "role": "logistique", "niveau": "write"}
    eugene = {"id": 1, "role": "superadmin", "niveau": "admin"}

    print("Perimetre visible par niveau")
    # read : ce qui m'est assigné (2, 3, 5) et ce que j'ai créé (2).
    verifier("read  fabrication", visibles(conn, fatou_read), [2, 3, 5])
    # write : mon service (2, 3) plus ce qui m'est assigné ailleurs (5).
    verifier("write fabrication", visibles(conn, fatou_write), [2, 3, 5])
    # Luc ne voit pas l'atelier, et voit ses deux tâches de logistique.
    verifier("write logistique", visibles(conn, luc_write), [4, 5])
    verifier("admin direction", visibles(conn, eugene), [1, 2, 3, 4, 5])

    print("Etancheite")
    for cas, u, interdits in (
        ("read  fabrication", fatou_read, [1, 4]),
        ("write fabrication", fatou_write, [1, 4]),
        ("write logistique", luc_write, [1, 2, 3]),
    ):
        vus = visibles(conn, u)
        fuites = [i for i in interdits if i in vus]
        if fuites:
            raise AssertionError(f"{cas} : fuite sur {fuites}")
        print(f"  ok  {cas} ne voit pas {interdits}")

    # La tâche historique de dev (service superadmin) ne doit atteindre
    # personne d'autre : c'est ce qui rend la migration sans effet visible.
    print("Historique de dev")
    for u in (fatou_read, fatou_write, luc_write):
        if 1 in visibles(conn, u):
            raise AssertionError("la tache 1 (service superadmin) a fuite")
    print("  ok  service superadmin invisible aux autres services")

    print("Rattachement de service")
    if R._valid_service(fatou_write, None) != "fabrication":
        raise AssertionError("sans valeur, le service doit etre celui de l'auteur")
    print("  ok  valeur par defaut = service de l'auteur")
    for valeur, motif in (("logistique", "autre service"), ("inconnu", "code inconnu")):
        try:
            R._valid_service(fatou_write, valeur)
        except Exception:
            print(f"  ok  refus ({motif})")
        else:
            raise AssertionError(f"{valeur} aurait du etre refuse ({motif})")
    if R._valid_service(eugene, "logistique") != "logistique":
        raise AssertionError("un admin doit pouvoir viser un autre service")
    print("  ok  admin peut rattacher a un autre service")

    print("\nTous les controles passent.")


if __name__ == "__main__":
    main()
