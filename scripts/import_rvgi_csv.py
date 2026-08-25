"""
Construit le miroir SQLite de l'ERP RVGI à partir des CSV d'export.
====================================================================

    python scripts/import_rvgi_csv.py
    python scripts/import_rvgi_csv.py --source data/rvgi_export --db data/erp_mirror.db
    python scripts/import_rvgi_csv.py --tables cde_entete,cde_ligne

Le miroir est **jetable** : chaque table importée est recréée de zéro. Il ne
contient rien qui ne soit reconstructible en relançant l'export — c'est la
raison pour laquelle il vit dans son propre fichier et pas dans
`production.db` : hors backups de prod, hors migrations, purgeable d'un `rm`.

Sens d'écriture unique : RVGI est la source, MySifa lit. Ce script écrit dans
le miroir, jamais dans l'ERP, jamais dans la base de prod.

Ce qu'il fait
-------------
  - une table SQLite par CSV, colonnes = en-tête du CSV (vue physique de RVGI,
    tableaux WinDev déjà dépilés) ;
  - types déduits d'un échantillon : INTEGER / REAL / TEXT. Un code à zéro
    initial (`0112`) reste TEXT — le lire en entier casserait la clé article ;
  - les dates restent en texte ISO `AAAA-MM-JJ hh:mm:ss`, donc triables et
    comparables telles quelles ;
  - index sur les colonnes qui servent réellement à filtrer et à joindre ;
  - table `erp_meta` : ce qui a été importé, quand, et de quel relevé.

Les valeurs sentinelles de RVGI (`30/11/1999` pour une date vide,
`99999999999.99` pour « pas de maximum », `0` pour un prix non renseigné) sont
conservées **telles quelles**. On neutralise à la lecture, dans
`app/services/erp_mirror.py` — pas en base, sinon le miroir ment sur sa source.

Aucune dépendance : stdlib seule, aucun import de `app.*`, donc aucun risque
de déclencher les migrations de la base de prod.
"""

import argparse
import csv
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SOURCE_DEFAUT = os.path.join(RACINE, "data", "rvgi_export")
DB_DEFAUT = os.path.join(RACINE, "data", "erp_mirror.db")

# Colonnes indexées quand elles existent : clés d'article, numéros de pièce,
# reports d'un domaine à l'autre, dates de tri. Rien d'autre — un index par
# colonne coûterait plus cher que les requêtes qu'il accélère.
COLS_INDEXEES = {
    "numero", "code1", "code2", "code3", "numclt", "numfou", "numfouclt",
    "numcde", "ligne", "lignecde", "refbl", "lot", "nofac", "livbl", "livno",
    "dos", "ndec1", "numart", "fam", "sfam", "gamme", "operateur", "depot",
    "amjc", "amjl", "amje", "amjf", "amjh", "amj", "amjd", "amjv", "dtem",
}

# `code1`/`code2`/`code3` sont TOUJOURS du texte, dans toutes les tables.
# Sinon le typage varie d'une table à l'autre — `code1` vaut 890 dans
# `cde_ligne` (INTEGER) et « FR » dans `fic_art` (TEXT) — et une jointure
# entre les deux ne remonte plus rien, sans erreur. La clé article de RVGI
# ne se compare qu'en texte.
COLS_TEXTE_FORCE = {"code1", "code2", "code3"}

# Un entier qui commence par 0 est un code, pas un nombre.
RE_ENTIER = re.compile(r"^-?\d+$")
RE_REEL = re.compile(r"^-?\d+[.,]\d+$")

TAILLE_LOT = 5000
ECHANTILLON_TYPE = 3000


def _typer(valeurs):
    """INTEGER / REAL / TEXT à partir d'un échantillon de valeurs."""
    vus = 0
    entier = True
    reel = True
    for v in valeurs:
        v = (v or "").strip()
        if v == "":
            continue
        vus += 1
        if entier and not RE_ENTIER.match(v):
            entier = False
        if reel and not (RE_ENTIER.match(v) or RE_REEL.match(v)):
            reel = False
        # Zéro initial : c'est un code (code2 = « 0112 »), jamais un nombre.
        if len(v) > 1 and v[0] == "0" and v[1] not in ".,":
            return "TEXT"
        if not entier and not reel:
            return "TEXT"
    if vus == 0:
        return "TEXT"
    if entier:
        return "INTEGER"
    if reel:
        return "REAL"
    return "TEXT"


def _convertir(valeur, type_sql):
    # HFSQL rend des textes à longueur fixe, complétés d'espaces : on les
    # retire, sinon « 890 » et « 890   » sont deux clés différentes.
    valeur = (valeur or "").strip()
    if valeur == "":
        return None
    if type_sql == "INTEGER":
        try:
            return int(valeur)
        except ValueError:
            return valeur
    if type_sql == "REAL":
        try:
            return float(valeur.replace(",", "."))
        except ValueError:
            return valeur
    return valeur


def _lire_entete_et_types(chemin):
    """Renvoie (colonnes, types) en lisant l'en-tête + un échantillon."""
    with open(chemin, "r", encoding="utf-8-sig", newline="") as f:
        lecteur = csv.reader(f, delimiter=";")
        try:
            entete = next(lecteur)
        except StopIteration:
            return [], []
        colonnes = [c.strip() for c in entete]
        echantillon = [[] for _ in colonnes]
        for i, ligne in enumerate(lecteur):
            if i >= ECHANTILLON_TYPE:
                break
            for j, v in enumerate(ligne[: len(colonnes)]):
                echantillon[j].append(v)
    types = [
        "TEXT" if c.lower() in COLS_TEXTE_FORCE else _typer(vals)
        for c, vals in zip(colonnes, echantillon)
    ]
    return colonnes, types


def _nom_sur(nom):
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", nom or ""):
        raise ValueError("Nom de table ou de colonne invalide : %r" % nom)
    return nom


def importer_table(conn, table, chemin, verbeux=True):
    table = _nom_sur(table)
    colonnes, types = _lire_entete_et_types(chemin)
    if not colonnes:
        if verbeux:
            print("  %-16s fichier vide, ignoré." % table)
        return 0

    for c in colonnes:
        _nom_sur(c)

    ddl = ", ".join('"%s" %s' % (c, t) for c, t in zip(colonnes, types))
    conn.execute('DROP TABLE IF EXISTS "%s"' % table)
    conn.execute('CREATE TABLE "%s" (%s)' % (table, ddl))

    place = ",".join("?" * len(colonnes))
    sql = 'INSERT INTO "%s" VALUES (%s)' % (table, place)

    nb = 0
    lot = []
    with open(chemin, "r", encoding="utf-8-sig", newline="") as f:
        lecteur = csv.reader(f, delimiter=";")
        next(lecteur, None)
        for ligne in lecteur:
            if len(ligne) < len(colonnes):
                ligne = ligne + [""] * (len(colonnes) - len(ligne))
            elif len(ligne) > len(colonnes):
                ligne = ligne[: len(colonnes)]
            lot.append(tuple(_convertir(v, t) for v, t in zip(ligne, types)))
            if len(lot) >= TAILLE_LOT:
                conn.executemany(sql, lot)
                nb += len(lot)
                lot = []
        if lot:
            conn.executemany(sql, lot)
            nb += len(lot)

    posees = 0
    for c in colonnes:
        if c.lower() in COLS_INDEXEES:
            conn.execute(
                'CREATE INDEX IF NOT EXISTS "ix_%s_%s" ON "%s" ("%s")' % (table, c, table, c)
            )
            posees += 1

    conn.commit()
    if verbeux:
        print("  %-16s %9d lignes  %3d colonnes  %d index" % (table, nb, len(colonnes), posees))
    return nb


def main():
    ap = argparse.ArgumentParser(description="Construit le miroir SQLite de l'ERP RVGI.")
    ap.add_argument("--source", default=SOURCE_DEFAUT, help="dossier des CSV exportés")
    ap.add_argument("--db", default=DB_DEFAUT, help="fichier SQLite du miroir")
    ap.add_argument("--tables", default="", help="liste de tables, séparées par des virgules")
    args = ap.parse_args()

    if not os.path.isdir(args.source):
        print("Dossier introuvable : %s" % args.source)
        print("Lancer d'abord scripts\\export_rvgi_csv.ps1 depuis un poste du réseau SIFA.")
        return 1

    manifeste = {}
    chemin_manifeste = os.path.join(args.source, "_manifeste.json")
    if os.path.exists(chemin_manifeste):
        with open(chemin_manifeste, "r", encoding="utf-8-sig") as f:
            manifeste = json.load(f)
    else:
        print("Pas de _manifeste.json — import à l'aveugle sur les CSV présents.")

    voulues = [t.strip() for t in args.tables.split(",") if t.strip()]
    fichiers = sorted(
        f for f in os.listdir(args.source)
        if f.endswith(".csv") and not f.startswith("_")
    )
    if voulues:
        fichiers = [f for f in fichiers if f[:-4] in voulues]
    if not fichiers:
        print("Aucun CSV à importer dans %s" % args.source)
        return 1

    os.makedirs(os.path.dirname(args.db) or ".", exist_ok=True)

    # Construction dans un fichier temporaire, remplacement atomique à la fin.
    # Deux raisons : l'application ne voit jamais un miroir à moitié construit,
    # et un import qui échoue laisse en place le miroir précédent.
    #
    # Pas de WAL : un miroir ouvert en lecture seule (`mode=ro`) ne peut pas
    # créer les fichiers -wal/-shm dont WAL a besoin, et certains montages
    # réseau le refusent carrément (« disk I/O error »).
    db_tmp = args.db + ".tmp"
    for reste in (db_tmp, db_tmp + "-wal", db_tmp + "-shm"):
        if os.path.exists(reste):
            os.remove(reste)
    if voulues and os.path.exists(args.db):
        # Import partiel : on repart du miroir existant pour ne pas perdre
        # les tables qu'on ne réimporte pas.
        shutil.copy2(args.db, db_tmp)

    conn = sqlite3.connect(db_tmp)
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA synchronous=OFF")

    conn.execute(
        "CREATE TABLE IF NOT EXISTS erp_meta ("
        " nom TEXT PRIMARY KEY, lignes INTEGER, colonnes INTEGER,"
        " importe_le TEXT, releve_le TEXT, fichier TEXT)"
    )
    conn.commit()

    releve_le = str(manifeste.get("genere_le") or "")
    maintenant = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("Miroir  : %s" % args.db)
    print("Source  : %s%s" % (args.source, (" (relevé du %s)" % releve_le) if releve_le else ""))
    print("Tables  : %d" % len(fichiers))
    print("")

    total = 0
    for f in fichiers:
        table = f[:-4]
        chemin = os.path.join(args.source, f)
        try:
            nb = importer_table(conn, table, chemin)
        except Exception as e:
            print("  %-16s ÉCHEC : %s" % (table, e))
            continue
        total += nb
        cols = conn.execute("SELECT COUNT(*) FROM pragma_table_info(?)", (table,)).fetchone()[0]
        conn.execute(
            "INSERT INTO erp_meta (nom, lignes, colonnes, importe_le, releve_le, fichier)"
            " VALUES (?,?,?,?,?,?)"
            " ON CONFLICT(nom) DO UPDATE SET lignes=excluded.lignes, colonnes=excluded.colonnes,"
            " importe_le=excluded.importe_le, releve_le=excluded.releve_le, fichier=excluded.fichier",
            (table, nb, cols, maintenant, releve_le, f),
        )
        conn.commit()

    conn.execute("ANALYZE")
    conn.commit()
    conn.close()

    for reste in (args.db + "-wal", args.db + "-shm"):
        if os.path.exists(reste):
            os.remove(reste)
    os.replace(db_tmp, args.db)
    taille = os.path.getsize(args.db)

    print("")
    print("Terminé : %d lignes, miroir de %.1f Mo." % (total, taille / (1024.0 * 1024.0)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
