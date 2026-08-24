"""
Le fournisseur récupère ses coordonnées et ses conditions d'achat.

Le problème
-----------
`fournisseurs_fsc` savait dire qui certifie un fournisseur, jamais comment le
joindre. Un téléphone n'existait qu'au travers d'un `fournisseur_contacts` —
donc rattaché à une personne. Or l'accueil d'une société survit à la personne
qui y répond : le standard, le fax et l'adresse générique de commande sont des
attributs de l'entreprise, pas d'un contact. Résultat concret : 146 numéros et
60 adresses e-mail de l'export ERP n'avaient nulle part où atterrir.

Même constat sur les conditions d'achat. Mode de règlement, mode de livraison,
délai d'expédition et régime de TVA conditionnent chaque commande passée chez
ce fournisseur. Ils vivaient dans l'ERP comptable, invisibles depuis MySifa.

Ce que fait cette migration
---------------------------
Ajoute huit colonnes à `fournisseurs_fsc`, en trois blocs :

  coordonnées société  → telephone, email, fax
  conditions d'achat   → mode_reglement, mode_livraison, delai_expedition_jours
  fiscalité            → regime_tva, rcs

Rien n'est rempli ici : la reprise est le travail du script d'import
(`scripts/import_fournisseurs_excel.py`), qui sait rapprocher les lignes de
l'export ERP des fiches existantes. Une migration qui devinerait des numéros de
téléphone serait une migration qui invente des données.

Paramétrage (règle Kernse)
--------------------------
Les trois référentiels — modes de règlement, modes de livraison, régimes de TVA
— sont des petits référentiels structurants : ils vivent dans `config.py`
(`MODES_REGLEMENT`, `MODES_LIVRAISON`, `REGIMES_TVA`), surchargeables par
variable d'environnement JSON, jamais interpolés en dur dans un template. Aucun
nom propre SIFA n'y figure : « livré par un transporteur affrété » est un mode,
le nom du transporteur est une donnée.

Pourquoi `delai_expedition_jours` en INTEGER et pas en TEXT
-----------------------------------------------------------
C'est un nombre de jours qui servira à calculer une date de disponibilité
prévisionnelle. Stocké en texte, il faudrait le reparser à chaque lecture et
tolérer « 3 j », « 3 jours », « ~3 » — trois écritures pour une même valeur, et
un calcul qui échoue silencieusement sur deux d'entre elles.
"""

from __future__ import annotations

import sqlite3

NOM = "fournisseur_contact_conditions"
DEPEND: list[str] = []

# (nom, déclaration SQL) — l'ordre est celui de la fiche à l'écran.
_COLONNES = (
    # Coordonnées de la société, pas d'une personne.
    ("telephone",              "TEXT"),
    ("email",                  "TEXT"),
    ("fax",                    "TEXT"),
    # Conditions d'achat négociées.
    ("mode_reglement",         "TEXT"),
    ("mode_livraison",         "TEXT"),
    ("delai_expedition_jours", "INTEGER"),
    # Fiscalité et immatriculation.
    ("regime_tva",             "TEXT"),
    ("rcs",                    "TEXT"),
)


def _colonnes(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def appliquer(conn: sqlite3.Connection) -> None:
    presentes = _colonnes(conn, "fournisseurs_fsc")
    if not presentes:
        # Base fraîche où la table n'existe pas encore : le socle la créera,
        # et cette migration repassera. Rien à faire, surtout pas planter.
        print(f"[MySifa] migration {NOM} : fournisseurs_fsc absente, rien a faire.")
        return

    ajoutees = []
    for nom, decl in _COLONNES:
        if nom in presentes:
            continue
        conn.execute(f"ALTER TABLE fournisseurs_fsc ADD COLUMN {nom} {decl}")
        ajoutees.append(nom)

    # Index sur l'e-mail : il sert de clé de rapprochement secondaire dans la
    # detection de doublons, qui balaie tout l'annuaire a chaque ouverture.
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_fournisseurs_email "
        "ON fournisseurs_fsc(email) WHERE email IS NOT NULL AND email <> ''"
    )
    conn.commit()

    print(
        f"[MySifa] migration {NOM} : {len(ajoutees)} colonne(s) ajoutee(s)"
        + (f" ({', '.join(ajoutees)})." if ajoutees else " (deja a jour).")
    )
