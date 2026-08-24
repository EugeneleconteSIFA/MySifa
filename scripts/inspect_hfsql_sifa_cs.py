"""
Inventaire de la base HFSQL `sifa_cs` (ERP) — reconnaissance avant synchro.
===========================================================================

Ce script ne modifie rien. Il se connecte en lecture à la base HFSQL
Client/Serveur de l'ERP, liste les tables, leurs colonnes, le nombre de lignes
et quelques valeurs d'exemple, puis écrit un rapport Markdown. C'est ce rapport
qui permet de décider QUOI synchroniser vers MySifa, et par quelle clé.

Pourquoi ADO/OLE DB et pas pyodbc
---------------------------------
Excel se connecte déjà à cette base avec le provider OLE DB `PCSoft.HFSQL`.
Ce provider est donc DÉJÀ installé sur le poste et déjà accepté par le serveur :
on réutilise exactement la même chaîne de connexion, sans rien installer côté
base ni demander quoi que ce soit à l'éditeur de l'ERP.

Le driver ODBC HFSQL est l'autre voie, mais il fait planter `pyodbc`
(incompatibilité au niveau C — il faut alors `pypyodbc`) et suppose de créer un
DSN système à la bonne architecture. ADO passe par le même provider qu'Excel :
si Excel voit les données, ce script les voit.

Prérequis
---------
    pip install pywin32

    L'architecture de Python doit correspondre à celle du provider installé.
    Excel 64 bits → Python 64 bits. Si `Provider cannot be found` apparaît alors
    qu'Excel fonctionne, c'est presque toujours ça.

Configuration — jamais de mot de passe en clair dans le fichier
---------------------------------------------------------------
    setx HFSQL_CONN  "provider=PCSoft.HFSQL;initial catalog=sifa_cs;data source=192.168.100.199:4949;extended properties=\"Language=ISO-8859-1\""
    setx HFSQL_UID   "utilisateur_lecture"
    setx HFSQL_PWD   "..."
    (puis rouvrir le terminal)

    La chaîne complète se relit dans Excel : Données → Requêtes et connexions →
    Propriétés → Définition → Chaîne de connexion. Recopier la valeur telle
    quelle, y compris `extended properties`.

Usage
-----
    python inspect_hfsql_sifa_cs.py                      # inventaire complet
    python inspect_hfsql_sifa_cs.py --tables vte_com cdi_entete
    python inspect_hfsql_sifa_cs.py --motif "cdi_|vte_"  # regex sur le nom
    python inspect_hfsql_sifa_cs.py --sans-comptage      # rapide, pas de COUNT(*)
    python inspect_hfsql_sifa_cs.py --echantillon 0      # aucune donnée réelle

Le rapport sort dans `rapport_sifa_cs.md` à côté du script.

Prudence : `--echantillon` recopie de vraies lignes de l'ERP dans le rapport.
Trois lignes par table par défaut, tronquées à 60 caractères. Mettre 0 si le
rapport doit pouvoir circuler.
"""

import argparse
import os
import re
import sys
from datetime import datetime

try:
    import win32com.client
except ImportError:
    sys.exit(
        "pywin32 est requis : pip install pywin32\n"
        "(et un Python de la même architecture que le provider PCSoft.HFSQL)"
    )

# ── Configuration ────────────────────────────────────────────────────
CONN_DEFAUT = (
    "provider=PCSoft.HFSQL;"
    "initial catalog=sifa_cs;"
    "data source=192.168.100.199:4949;"
    'extended properties="Language=ISO-8859-1"'
)
CONN_STR = os.environ.get("HFSQL_CONN", CONN_DEFAUT)
UID = os.environ.get("HFSQL_UID", "")
PWD = os.environ.get("HFSQL_PWD", "")

TIMEOUT_S = 30
RAPPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rapport_sifa_cs.md")

# Les tables `_backup_sauvegarde des donnees de . (JJ-MM-AAAA HH.MM)_xxx` sont
# des copies datées laissées par l'ERP. Elles polluent l'inventaire et ne sont
# jamais une source de synchro.
RE_BACKUP = re.compile(r"^_backup", re.IGNORECASE)

# adSchemaTables / adSchemaColumns
ADO_SCHEMA_TABLES = 20

ADO_TYPES = {
    0: "vide", 2: "entier2", 3: "entier4", 4: "réel4", 5: "réel8",
    6: "monétaire", 7: "date", 11: "booléen", 14: "décimal", 16: "entier1",
    17: "octet", 18: "entier2ns", 19: "entier4ns", 20: "entier8",
    21: "entier8ns", 72: "guid", 128: "binaire", 129: "texte",
    130: "texte_unicode", 131: "numérique", 133: "date", 134: "heure",
    135: "horodatage", 200: "varchar", 201: "texte_long", 202: "varwchar",
    203: "texte_long_unicode", 204: "varbinaire", 205: "binaire_long",
}


def _type_lisible(code, taille):
    nom = ADO_TYPES.get(code, f"type_{code}")
    if taille and code in (129, 130, 200, 202) and taille < 1_000_000:
        return f"{nom}({taille})"
    return nom


def _ouvrir():
    conn = win32com.client.Dispatch("ADODB.Connection")
    conn.CommandTimeout = TIMEOUT_S
    conn.ConnectionTimeout = TIMEOUT_S
    chaine = CONN_STR
    if UID and "user id" not in chaine.lower():
        chaine += f";User ID={UID};Password={PWD}"
    conn.Open(chaine)
    return conn


def _lister_tables(conn):
    """Renvoie [(nom, type)] via le schéma ADO — la même liste qu'Excel."""
    rs = conn.OpenSchema(ADO_SCHEMA_TABLES)
    tables = []
    while not rs.EOF:
        nom = str(rs.Fields.Item("TABLE_NAME").Value or "")
        typ = str(rs.Fields.Item("TABLE_TYPE").Value or "")
        if nom:
            tables.append((nom, typ))
        rs.MoveNext()
    rs.Close()
    return sorted(tables, key=lambda t: t[0].lower())


def _citer(nom):
    """HFSQL accepte le nom nu ; on ne quote que si nécessaire."""
    return nom if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", nom) else f'"{nom}"'


def _compter(conn, table):
    try:
        rs = conn.Execute(f"SELECT COUNT(*) AS n FROM {_citer(table)}")[0]
        n = rs.Fields.Item(0).Value
        rs.Close()
        return int(n)
    except Exception as e:
        return f"erreur ({str(e).splitlines()[0][:80]})"


def _colonnes_et_echantillon(conn, table, n_lignes):
    """Une seule requête : les métadonnées viennent du recordset lui-même."""
    cmd = win32com.client.Dispatch("ADODB.Command")
    cmd.ActiveConnection = conn
    cmd.CommandTimeout = TIMEOUT_S
    cmd.CommandText = f"SELECT * FROM {_citer(table)}"
    rs = win32com.client.Dispatch("ADODB.Recordset")
    rs.MaxRecords = max(n_lignes, 1)
    rs.Open(cmd)

    colonnes = []
    for i in range(rs.Fields.Count):
        f = rs.Fields.Item(i)
        colonnes.append((str(f.Name), _type_lisible(f.Type, f.DefinedSize)))

    lignes = []
    while not rs.EOF and len(lignes) < n_lignes:
        vals = []
        for i in range(rs.Fields.Count):
            try:
                v = rs.Fields.Item(i).Value
            except Exception:
                v = "<illisible>"
            s = "" if v is None else str(v)
            s = s.replace("\n", " ").replace("|", "/")
            vals.append(s[:60])
        lignes.append(vals)
        rs.MoveNext()
    rs.Close()
    return colonnes, lignes


def main():
    ap = argparse.ArgumentParser(description="Inventaire lecture seule de la base HFSQL sifa_cs.")
    ap.add_argument("--tables", nargs="*", help="Noms de tables précis à inspecter.")
    ap.add_argument("--motif", help="Regex de filtrage sur le nom des tables.")
    ap.add_argument("--echantillon", type=int, default=3, help="Lignes d'exemple par table (0 = aucune).")
    ap.add_argument("--sans-comptage", action="store_true", help="Ne pas faire de COUNT(*) (plus rapide).")
    ap.add_argument("--avec-backups", action="store_true", help="Inclure les tables _backup_ de l'ERP.")
    args = ap.parse_args()

    print(f"Connexion : {CONN_STR.split('extended')[0]}...")
    try:
        conn = _ouvrir()
    except Exception as e:
        sys.exit(
            f"Connexion impossible : {e}\n\n"
            "Pistes : architecture Python vs provider (Excel 64 bits -> Python 64 bits), "
            "chaîne HFSQL_CONN incomplète, identifiants HFSQL_UID/HFSQL_PWD absents, "
            "ou poste hors du réseau SIFA (192.168.100.x)."
        )

    toutes = _lister_tables(conn)
    print(f"{len(toutes)} objets remontés par le schéma.")

    tables = toutes
    if not args.avec_backups:
        tables = [t for t in tables if not RE_BACKUP.match(t[0])]
    if args.motif:
        rx = re.compile(args.motif, re.IGNORECASE)
        tables = [t for t in tables if rx.search(t[0])]
    if args.tables:
        voulues = {t.lower() for t in args.tables}
        tables = [t for t in tables if t[0].lower() in voulues]

    print(f"{len(tables)} table(s) à inspecter.\n")

    lignes_md = [
        "# Inventaire de la base HFSQL `sifa_cs`",
        "",
        f"Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')} — lecture seule.",
        f"Source : `{CONN_STR.split('extended')[0].strip()}`",
        f"Objets vus par le schéma : {len(toutes)} — inspectés ici : {len(tables)}"
        + ("" if args.avec_backups else f" (tables `_backup_` exclues : {len(toutes) - len([t for t in toutes if not RE_BACKUP.match(t[0])])})"),
        "",
        "## Sommaire",
        "",
        "| Table | Type | Lignes | Colonnes |",
        "|---|---|---:|---:|",
    ]
    detail = []

    for idx, (nom, typ) in enumerate(tables, 1):
        print(f"[{idx}/{len(tables)}] {nom}", flush=True)
        n = "-" if args.sans_comptage else _compter(conn, nom)
        try:
            cols, ech = _colonnes_et_echantillon(conn, nom, args.echantillon)
        except Exception as e:
            cols, ech = [], []
            detail.append(f"### `{nom}`\n\nLecture impossible : {str(e).splitlines()[0][:200]}\n")
            lignes_md.append(f"| `{nom}` | {typ} | {n} | erreur |")
            continue

        lignes_md.append(f"| [`{nom}`](#{nom.lower().replace('_', '-')}) | {typ} | {n} | {len(cols)} |")

        bloc = [f"### `{nom}`", "", f"Type : {typ} — lignes : {n} — colonnes : {len(cols)}", "",
                "| # | Colonne | Type |", "|---:|---|---|"]
        for i, (cn, ct) in enumerate(cols, 1):
            bloc.append(f"| {i} | `{cn}` | {ct} |")
        if ech:
            bloc += ["", "Extrait :", "", "| " + " | ".join(c[0] for c in cols) + " |",
                     "|" + "---|" * len(cols)]
            for r in ech:
                bloc.append("| " + " | ".join(r) + " |")
        bloc.append("")
        detail.append("\n".join(bloc))

    conn.Close()

    contenu = "\n".join(lignes_md) + "\n\n## Détail des tables\n\n" + "\n".join(detail)
    with open(RAPPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write(contenu)

    print(f"\nRapport écrit : {RAPPORT}")
    print("Relis-le avant de le partager : il contient des extraits de données réelles.")


if __name__ == "__main__":
    main()
