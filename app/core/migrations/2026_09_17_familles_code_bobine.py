"""Familles de codes-barres bobine, et remise d'aplomb des scans existants.

Relevé du 17/09/2026, vérifié avec l'atelier (voir
`app/services/familles_code.py`) :

    R1?01-… / G1?01-…      Likexin — 3e bloc = laize en mm (codes à 4 blocs),
                           G = glassine (règle de préfixe déjà en place)
    11 chiffres en 60…     Kanzan
    12 chiffres            Burgo / Mosaico (« customer barcode »)
    641578 + 7 chiffres    UPM (GTIN)
    003641578 + 11 chiffres UPM (SSCC)
    003868 + 14 chiffres   Frimpeks Turkey (SSCC, préfixe GS1 turc)
    653 + 16 chiffres      Frimpeks UK (forme de l'exemple de sa fiche traça)

Le seed ne pose une famille que si la fiche fournisseur existe sous ce nom :
une autre instance démarre avec une table vide et la remplit en Paramètres.

Reprise des scans
-----------------
Sur les scans SANS réception (les seuls dont l'origine est déclarative) :
- le code est normalisé quand un artefact de scan le sort de sa famille
  (`7R1101-…`, `R1101.SGD…`, code lu deux fois) ; le code lu est gardé dans
  `code_barre_brut` ;
- le fournisseur est réattribué selon la famille quand il diffère ; l'ancien
  est gardé dans `fournisseur_corrige_de`. Le certificat suit la fiche.
Les montages en cours (`bobines_montees`) reçoivent le code normalisé.
Les signatures apprises sont ensuite reconstruites depuis l'historique corrigé.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

NOM = "familles_code_bobine"
DEPEND = ["bobines_heritees", "postes_deroulement"]

SEED = [
    # (fournisseur, masque, laize_segment, laize_blocs_min, note)
    ("Likexin", "R1?01-*", 3, 4, "Frontal. 3e bloc = laize en mm (codes à 4 blocs)."),
    ("Likexin", "G1?01-*", 3, 4, "Glassine. 3e bloc = laize en mm (codes à 4 blocs)."),
    ("Kanzan", "60#########", None, None, "11 chiffres commençant par 60."),
    ("Burgo / Mosaico", "############", None, None, "Customer barcode, 12 chiffres."),
    ("UPM", "641578#######", None, None, "GTIN, préfixe GS1 UPM."),
    ("UPM", "003641578###########", None, None, "SSCC, préfixe GS1 UPM."),
    ("Frimpeks Turkey", "003868##############", None, None, "SSCC, préfixe GS1 turc."),
    ("Frimpeks UK", "653################", None, None, "19 chiffres, forme de l'exemple de la fiche."),
]


def _cols(conn, table):
    return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}


def appliquer(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bobine_familles_code (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            fournisseur_id  INTEGER NOT NULL REFERENCES fournisseurs_fsc(id) ON DELETE CASCADE,
            masque          TEXT    NOT NULL,
            laize_segment   INTEGER,
            laize_blocs_min INTEGER,
            note            TEXT,
            actif           INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT    NOT NULL,
            updated_at      TEXT,
            updated_by      TEXT
        )
    """)
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_bobine_familles_masque "
        "ON bobine_familles_code(upper(masque))"
    )
    fmu = _cols(conn, "fab_matieres_utilisees")
    if fmu:
        for col in ("code_barre_brut", "fournisseur_corrige_de"):
            if col not in fmu:
                conn.execute("ALTER TABLE fab_matieres_utilisees ADD COLUMN %s TEXT" % col)

    quand = datetime.now().isoformat(timespec="seconds")
    for nom, masque, seg, blocs, note in SEED:
        f = conn.execute(
            "SELECT id FROM fournisseurs_fsc WHERE trim(nom)=? ORDER BY id LIMIT 1", (nom,)
        ).fetchone()
        if not f:
            continue
        conn.execute(
            """INSERT OR IGNORE INTO bobine_familles_code
                   (fournisseur_id, masque, laize_segment, laize_blocs_min, note, actif,
                    created_at, updated_at, updated_by)
               VALUES (?,?,?,?,?,1,?,?,'migration')""",
            (int(f[0]), masque, seg, blocs, note, quand, quand),
        )
    conn.commit()

    if not fmu:
        return
    from app.services import familles_code as fc

    liste = fc.familles(conn, actives_seulement=True)
    if not liste:
        return
    fiches = {
        r[0]: (r[1] or "") for r in conn.execute("SELECT nom, certificat FROM fournisseurs_fsc")
    }
    n_code = n_four = 0
    for r in conn.execute(
        """SELECT id, code_barre, fournisseur_manual, certificat_fsc_manual
             FROM fab_matieres_utilisees
            WHERE reception_id IS NULL"""
    ).fetchall():
        rid, code, four = r[0], (r[1] or "").strip(), (r[2] or "").strip()
        neuf, notes = fc.normaliser(code, liste)
        if neuf != code:
            conn.execute(
                "UPDATE fab_matieres_utilisees SET code_barre=?, code_barre_brut=? WHERE id=?",
                (neuf, code, rid),
            )
            conn.execute(
                "UPDATE bobines_montees SET code_barre=? WHERE trim(code_barre)=?",
                (neuf, code),
            )
            n_code += 1
        f = fc._correspond(neuf, liste)
        if f and f.get("fournisseur") and f["fournisseur"] != four:
            conn.execute(
                """UPDATE fab_matieres_utilisees
                      SET fournisseur_manual=?, certificat_fsc_manual=?,
                          liaison_mode='manual', fournisseur_corrige_de=?
                    WHERE id=?""",
                (f["fournisseur"], fiches.get(f["fournisseur"], ""), four or "(aucun)", rid),
            )
            n_four += 1
    conn.commit()

    try:
        from app.services.origine_bobine import reconstruire
        bilan = reconstruire(conn)
        conn.commit()
    except Exception as e:  # la mémoire est un bénéfice, pas une condition
        conn.rollback()
        bilan = {"erreur": str(e)}
    print(f"[MySifa] migration {NOM} : {len(liste)} famille(s), {n_code} code(s) "
          f"normalisé(s), {n_four} fournisseur(s) réattribué(s), signatures {bilan}.")
