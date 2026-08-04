"""
Migrations en fichiers, identifiées par leur NOM.

Pourquoi
--------
Les migrations historiques vivent toutes dans `app/core/database.py` et sont
identifiées par un numéro croissant. Ce fonctionnement pose deux problèmes dès
que deux chantiers avancent en parallèle :

1. Collision de numéros. Deux sessions choisissent le même numéro chacune de son
   côté ; après fusion, la seconde ne s'exécutera JAMAIS, son garde-fou voyant le
   numéro de l'autre déjà enregistré. Le doublon historique en v195 en est un
   exemple : le bloc « imprimantes_type_connexion_windows_local » est resté muet
   sur toutes les bases où le backfill des libres était passé avant lui.
2. Fichier partagé. `database.py` fait des milliers de lignes ; deux sessions qui
   y écrivent s'écrasent mutuellement, et git n'a aucun moyen de trancher.

Ici, une migration = un fichier, identifié par un nom. Deux chantiers ne touchent
jamais le même fichier et ne choisissent jamais le même nom.

Écrire une migration
--------------------
Créer `app/core/migrations/AAAA_MM_JJ_sujet.py` :

    NOM = "sujet_explicite"           # identifiant unique et définitif
    DEPEND = ["autre_migration"]      # facultatif : à passer avant celle-ci

    def appliquer(conn):
        conn.execute("ALTER TABLE ... ")

Le préfixe de date ne sert qu'à ordonner l'exécution par défaut : ce n'est pas une
clé, deux migrations datées du même jour ne se gênent pas. Le NOM, lui, est la clé
— il ne doit jamais changer une fois la migration partie en production.

Quand une migration en attend une autre (elle touche une table que l'autre crée),
il faut le DIRE via `DEPEND` plutôt que compter sur l'ordre alphabétique : deux
chantiers parallèles ne contrôlent pas le nom de fichier de l'autre.

Une migration doit rester REJOUABLE : elle peut être exécutée sur une base où
elle est déjà passée sans rien casser (`CREATE TABLE IF NOT EXISTS`, test de
présence de colonne avant `ALTER TABLE`).
"""

from __future__ import annotations

import importlib
import pkgutil
import sqlite3
from datetime import datetime
from typing import Any


def _table_suivi(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations_fichiers (
               nom         TEXT PRIMARY KEY NOT NULL,
               applique_le TEXT NOT NULL
           )"""
    )


def _deja_appliquees(conn: sqlite3.Connection) -> set[str]:
    """
    Noms déjà passés. On regarde aussi la table historique : une migration
    déplacée depuis `database.py` y est enregistrée sous le même nom, il ne faut
    surtout pas la rejouer.
    """
    noms = {
        r[0] for r in conn.execute("SELECT nom FROM schema_migrations_fichiers").fetchall()
    }
    try:
        noms |= {
            r[0]
            for r in conn.execute("SELECT name FROM schema_migrations").fetchall()
            if r[0]
        }
    except sqlite3.OperationalError:
        pass  # base très ancienne, sans table de suivi historique
    return noms


def appliquer_migrations(conn: sqlite3.Connection) -> list[str]:
    """Applique les migrations non encore passées, dans l'ordre des noms de fichiers."""
    _table_suivi(conn)
    faites = _deja_appliquees(conn)
    vus: dict[str, str] = {}
    appliquees: list[str] = []

    modules = sorted(
        (m.name for m in pkgutil.iter_modules(__path__) if not m.name.startswith("_"))
    )
    charges: list[tuple[str, str, list[str], Any]] = []
    for nom_module in modules:
        module = importlib.import_module(f"{__name__}.{nom_module}")
        nom = getattr(module, "NOM", None)
        if not nom:
            raise RuntimeError(f"Migration {nom_module} : NOM manquant.")
        if nom in vus:
            raise RuntimeError(
                f"Migration {nom_module} : le nom « {nom} » est déjà pris par "
                f"{vus[nom]}. Choisissez-en un autre."
            )
        vus[nom] = nom_module
        appliquer = getattr(module, "appliquer", None)
        if not callable(appliquer):
            raise RuntimeError(f"Migration {nom_module} : fonction appliquer(conn) manquante.")
        charges.append((nom, nom_module, list(getattr(module, "DEPEND", []) or []), appliquer))

    inconnues = {d for _, _, deps, _ in charges for d in deps} - set(vus)
    if inconnues:
        raise RuntimeError(f"DEPEND vers des migrations inexistantes : {sorted(inconnues)}.")

    # Ordre : les noms de fichiers d'abord, mais une migration attend celles
    # qu'elle déclare dans DEPEND.
    restantes = [c for c in charges if c[0] not in faites]
    satisfaites = set(faites)
    while restantes:
        prete = next(
            (c for c in restantes if all(d in satisfaites for d in c[2])), None
        )
        if prete is None:
            raise RuntimeError(
                "Dépendances circulaires ou impossibles entre migrations : "
                + ", ".join(c[0] for c in restantes)
            )
        nom, nom_module, _, appliquer = prete
        restantes.remove(prete)
        appliquer(conn)
        conn.execute(
            "INSERT OR REPLACE INTO schema_migrations_fichiers (nom, applique_le) VALUES (?,?)",
            (nom, datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
        )
        conn.commit()
        satisfaites.add(nom)
        appliquees.append(nom)
    return appliquees
