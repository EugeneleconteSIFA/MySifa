"""Les bobines MONTÉES sur chaque machine — un état, pas un journal.

Pourquoi une table de plus
--------------------------
`fab_matieres_utilisees` est un journal : ce code a été scanné à cette machine,
sur ce dossier, à cette heure. Il ne dit pas ce qui est encore sur le poste de
déroulement une heure plus tard. Or c'est précisément ce que l'atelier ne
rescanne pas : la glassine gardée d'un dossier à l'autre, le frontal laissé en
place quand la laize ne change pas. Relevé du 10/09/2026 : aucun code-barres
n'a jamais été scanné sur deux dossiers.

`bobines_montees` tient l'état : une ligne par montage, ouverte au scan
(`demonte_at` NULL), fermée quand la bobine quitte le poste. La ligne n'est
jamais effacée à la fermeture — savoir quand une bobine est partie est ce qui
permettra, au lot suivant, de dire quels dossiers l'ont eue sous la main.

Le poste peut rester NULL : une bobine dont on n'a pas su dire la nature est
montée « en attente de poste » plutôt que refusée. Elle n'occupe aucune place
tant que personne n'a tranché.

Colonnes ajoutées
-----------------
`fab_matieres_utilisees.categorie_bobine / poste / poste_source / poste_confiance`
    — la nature arrêtée au scan et ce qui a permis de l'arrêter, pour qu'un
    audit distingue une nature démontrée (stock) d'une nature devinée.

`bobine_signatures.observations_categorie`
    — les comptes par catégorie de chaque forme de code, à côté des comptes
    par fournisseur. Même principe que `signature_bobine` : on compte, on ne
    tranche pas, et une forme vue sous deux natures devient ambiguë.

Reprise
-------
Aucune reprise de l'état : on ne sait pas ce qui est monté aujourd'hui, et
inventer un état serait pire que partir vide. En revanche, l'historique des
scans alimente la mémoire des catégories partout où la nature est CERTAINE
(bobine connue du stock, règle de préfixe, fournisseur à nature unique).
"""

from __future__ import annotations

import sqlite3

NOM = "bobines_montees"
DEPEND = ["postes_deroulement", "signature_bobine"]


def _colonnes(conn: sqlite3.Connection, table: str) -> set:
    try:
        return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}
    except sqlite3.Error:
        return set()


def appliquer(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bobines_montees (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id       INTEGER NOT NULL,
            poste            TEXT,                  -- NULL = en attente de poste
            categorie        TEXT,                  -- frontal | complexe | glassine
            code_barre       TEXT    NOT NULL,
            fab_matiere_id   INTEGER,               -- le scan qui l'a montée
            no_dossier       TEXT,                  -- dossier en cours au montage
            poste_source     TEXT,
            poste_confiance  TEXT,
            monte_at         TEXT    NOT NULL,
            monte_par        TEXT,
            demonte_at       TEXT,
            demonte_par      TEXT,
            motif_demontage  TEXT                   -- remplacee | retiree | deplacee | scan_annule
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_bob_montees_actives "
        "ON bobines_montees(machine_id, demonte_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_bob_montees_code "
        "ON bobines_montees(code_barre)"
    )

    fmu = _colonnes(conn, "fab_matieres_utilisees")
    if fmu:
        for col in ("categorie_bobine", "poste", "poste_source", "poste_confiance"):
            if col not in fmu:
                conn.execute("ALTER TABLE fab_matieres_utilisees ADD COLUMN %s TEXT" % col)

    sig = _colonnes(conn, "bobine_signatures")
    if sig and "observations_categorie" not in sig:
        conn.execute(
            "ALTER TABLE bobine_signatures ADD COLUMN observations_categorie "
            "TEXT NOT NULL DEFAULT '{}'"
        )
    conn.commit()

    try:
        from app.services.poste_bobine import reconstruire_categories
        bilan = reconstruire_categories(conn)
        conn.commit()
        print(f"[MySifa] migration {NOM} : {bilan['apprises']} identification(s) "
              f"de nature rejouée(s) sur {bilan['scans']} scan(s).")
    except Exception as e:  # la mémoire est un bénéfice, pas une condition
        conn.rollback()
        print(f"[MySifa] migration {NOM} : mémoire des natures non reconstruite ({e}).")
