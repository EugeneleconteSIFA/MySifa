"""Relier les clients et les fournisseurs de MySifa à ceux de RVGI.

Le principe
-----------
RVGI est la source. Un client, un fournisseur existent d'abord dans l'ERP ;
MySifa peut en ajouter à la main, mais dès qu'une fiche est LIÉE à RVGI, les
champs que l'ERP connaît lui appartiennent : la synchro les réécrit, et
l'interface les passe en lecture seule. Ce que RVGI ignore — FSC, catégories,
tags, notes, tarifs, contacts MySifa — n'est jamais touché.

Trois colonnes suffisent à porter ça, et une quatrième à l'expliquer :

    rvgi_numero   le `numero` de `fic_clt` / `fic_fou`. C'est LE lien.
    rvgi_etat     manuel | lie | a_confirmer
    rvgi_motif    comment le lien a été posé : siret, nom, code, import, manuel
    rvgi_maj_le   quand la synchro a réécrit la fiche pour la dernière fois

Ce que la synchro n'écrasera JAMAIS, et pourquoi
------------------------------------------------
`fournisseurs_fsc.nom` est unique, et une douzaine de modules joignent dessus
en texte plutôt que sur l'id — `fabrication.py` (`ON ff.nom = r.fournisseur`),
`stock.py` (`WHERE UPPER(TRIM(nom)) = UPPER(?)`), `qualite_ged.py`. Réécrire
ce nom depuis RVGI romprait ces jointures en silence, et pourrait violer la
contrainte d'unicité au passage. La raison sociale de RVGI est donc rangée à
part, dans `rvgi_rs`, affichée à côté du nom MySifa. L'adopter reste un geste
humain, avec le contrôle d'unicité que ça suppose.

Même raisonnement pour `fournisseurs_fsc.groupe` (l'écran de groupe s'appuie
dessus) et pour `actif` (qui pilote la visibilité dans MyAO et Qualité) : la
valeur RVGI est gardée dans `rvgi_groupe` et `rvgi_bloq`, montrée, jamais
imposée.

Côté clients rien de tel : `raison_sociale` n'est ni unique ni jointe en
texte, les liens passent par `clients.id`. Elle est donc réécrite normalement.

Une note sur `bloq`
-------------------
Dans RVGI, `bloq` ne veut pas dire ce que son nom laisse croire. Sur les
1 264 clients du miroir : `bloq = 1` (537 fiches) porte 282 clients ayant
commandé en 2026 et la dernière modification date de juillet 2026 ;
`bloq = 2` (713 fiches) n'a AUCUNE commande en 2026 et n'a plus bougé depuis
2023. C'est donc 1 = actif, 2 = bloqué. Vérifié de la même façon côté
fournisseurs (96 fiches `bloq = 1` avec une commande d'achat depuis 2025,
zéro pour `bloq = 2`). Reste `bloq = 3`, 14 clients dont 4 commandent encore :
un état intermédiaire dont on ne connaît pas le nom, qu'on garde tel quel
plutôt que de lui en inventer un.
"""

from __future__ import annotations

import sqlite3

NOM = "rvgi_tiers"


def _colonnes(conn: sqlite3.Connection, table: str) -> set:
    try:
        return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}
    except sqlite3.Error:
        return set()


def _ajouter(conn: sqlite3.Connection, table: str, colonnes: dict) -> int:
    presentes = _colonnes(conn, table)
    if not presentes:
        return 0
    n = 0
    for nom, decl in colonnes.items():
        if nom in presentes:
            continue
        conn.execute('ALTER TABLE "%s" ADD COLUMN %s %s' % (table, nom, decl))
        n += 1
    return n


# Communes aux deux référentiels : le lien lui-même.
_LIEN = {
    "rvgi_numero": "INTEGER",
    "rvgi_code": "TEXT",
    # manuel      : fiche créée dans MySifa, sans équivalent ERP connu
    # lie         : rattachée à une fiche RVGI, champs pilotés par l'ERP
    # a_confirmer : un candidat a été trouvé, personne ne l'a encore validé
    "rvgi_etat": "TEXT NOT NULL DEFAULT 'manuel'",
    "rvgi_motif": "TEXT",
    "rvgi_score": "REAL",
    "rvgi_bloq": "INTEGER",
    "rvgi_lie_le": "TEXT",
    "rvgi_maj_le": "TEXT",
}

# Propres aux fournisseurs : ce que RVGI dit, et que MySifa ne se laisse pas
# imposer parce que d'autres modules en dépendent.
_FOU_EN_MIROIR = {
    "rvgi_rs": "TEXT",
    "rvgi_groupe": "TEXT",
}


def appliquer(conn: sqlite3.Connection) -> None:
    n = 0
    n += _ajouter(conn, "clients", _LIEN)
    n += _ajouter(conn, "fournisseurs_fsc", dict(_LIEN, **_FOU_EN_MIROIR))

    # Le contact RVGI d'un fournisseur (`fic_foui`) peut être repris dans les
    # contacts MySifa : on garde de quoi savoir lequel, pour ne pas le reprendre
    # deux fois à la synchro suivante.
    n += _ajouter(conn, "fournisseur_contacts", {"rvgi_numint": "INTEGER"})

    for table, idx, col in (
        ("clients", "idx_clients_rvgi", "rvgi_numero"),
        ("clients", "idx_clients_rvgi_etat", "rvgi_etat"),
        ("fournisseurs_fsc", "idx_fournisseurs_rvgi", "rvgi_numero"),
        ("fournisseurs_fsc", "idx_fournisseurs_rvgi_etat", "rvgi_etat"),
    ):
        if _colonnes(conn, table):
            conn.execute(
                "CREATE INDEX IF NOT EXISTS %s ON %s(%s)" % (idx, table, col)
            )

    # Le journal des synchros. Un rapprochement qui a lié 340 fiches et en a
    # laissé 12 à confirmer, c'est une information qui se relit — surtout le
    # jour où quelqu'un se demande d'où vient un nom qui a changé tout seul.
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rvgi_tiers_synchros (
               id            INTEGER PRIMARY KEY AUTOINCREMENT,
               perimetre     TEXT NOT NULL CHECK (perimetre IN ('client','fournisseur')),
               lance_le      TEXT NOT NULL,
               lance_par     TEXT,
               origine       TEXT NOT NULL DEFAULT 'manuel',
               miroir_releve_le TEXT,

               rvgi_total    INTEGER NOT NULL DEFAULT 0,
               rvgi_actifs   INTEGER NOT NULL DEFAULT 0,
               lies          INTEGER NOT NULL DEFAULT 0,
               nouveaux      INTEGER NOT NULL DEFAULT 0,
               mis_a_jour    INTEGER NOT NULL DEFAULT 0,
               a_confirmer   INTEGER NOT NULL DEFAULT 0,
               champs_ecrits INTEGER NOT NULL DEFAULT 0
           )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_rvgi_tiers_synchros ON "
        "rvgi_tiers_synchros(perimetre, lance_le)"
    )

    # Une fiche déjà rapprochée à la main garde son lien : on ne repart pas de
    # zéro à chaque migration. Rien à reprendre ici, la colonne vient d'être
    # créée — mais les clients importés de l'export ERP portent déjà `numero`,
    # qui EST le `fic_clt.numero`. On pose le lien tout de suite : c'est la
    # même clé, et le refaire deviner au rapprochement serait absurde.
    if "rvgi_numero" in _colonnes(conn, "clients"):
        cur = conn.execute(
            """UPDATE clients
                  SET rvgi_numero = numero,
                      rvgi_etat   = 'a_confirmer',
                      rvgi_motif  = 'numero_erp'
                WHERE rvgi_numero IS NULL
                  AND numero IS NOT NULL AND numero > 0"""
        )
        if cur.rowcount:
            print("[MySifa] migration rvgi_tiers : %d clients portaient déjà un "
                  "numéro ERP — lien proposé, à confirmer par la synchro."
                  % cur.rowcount)

    print(
        "[MySifa] migration rvgi_tiers : clients et fournisseurs reliables à "
        "RVGI (%d colonnes ajoutées)." % n
    )
