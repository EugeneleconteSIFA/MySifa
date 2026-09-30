"""
Outil RH (MyCompta) : documents administratifs par contrat, justificatifs de
formation, fin de la case « Règlement signé ».

1. Documents administratifs exigés par CONTRAT (et non plus par service) :
   table `rh_outil_document_contrats` ; `rh_outil_document_services` est
   supprimée (rien n'est retiré aux employés, seules les règles partent).
2. Justificatifs de formation : chaque formation définit ses justificatifs
   attendus (`rh_outil_formation_justificatifs`) ; un employé qui a la
   formation a une case par justificatif (`rh_outil_membre_justificatifs`),
   affichée sous la formation. Les pièces jointes servent les deux :
   `rh_outil_pieces.cible` = 'document' ou 'justificatif'.
   Reprise : chaque lien formation → document (`rh_outil_formation_documents`,
   qui n'a existé que sur v1) devient un justificatif de même intitulé ; la
   case est reprise « faite » si l'employé avait vérifié ce document.
3. « Règlement signé » devient le document administratif « Règlement
   intérieur signé », exigé pour tous ; les « Oui » deviennent des cases
   cochées. La colonne `reglement_signe` n'est plus lue (DROP au lot suivant).
"""

from datetime import datetime

NOM = "rh_outil_documents_administratifs"
DEPEND = ["rh_outil_categories_documents_lies", "rh_outil_pieces", "rh_outil_reglement_signe",
          "rh_outil_exigences_services", "rh_outil_obligatoire", "rh_outil_membres"]

REGLEMENT = "Règlement intérieur signé"


def _tables(conn):
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def appliquer(conn):
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # 1. Exigences des documents par contrat
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_outil_document_contrats (
               document_id  INTEGER NOT NULL REFERENCES rh_outil_documents(id) ON DELETE CASCADE,
               contrat      TEXT NOT NULL,
               PRIMARY KEY (document_id, contrat)
           )"""
    )
    conn.execute("DROP TABLE IF EXISTS rh_outil_document_services")

    # 2. Justificatifs de formation
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_outil_formation_justificatifs (
               id            INTEGER PRIMARY KEY AUTOINCREMENT,
               formation_id  INTEGER NOT NULL REFERENCES rh_outil_formations(id) ON DELETE CASCADE,
               libelle       TEXT NOT NULL,
               cree_le       TEXT NOT NULL
           )"""
    )
    conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS ux_rh_outil_formation_justificatifs
                        ON rh_outil_formation_justificatifs(formation_id, libelle COLLATE NOCASE)""")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rh_outil_membre_justificatifs (
               id              INTEGER PRIMARY KEY AUTOINCREMENT,
               attribution_id  INTEGER NOT NULL REFERENCES rh_outil_membre_formations(id) ON DELETE CASCADE,
               justificatif_id INTEGER NOT NULL REFERENCES rh_outil_formation_justificatifs(id) ON DELETE CASCADE,
               fait            INTEGER NOT NULL DEFAULT 0,
               ajoute_le       TEXT NOT NULL,
               UNIQUE(attribution_id, justificatif_id)
           )"""
    )
    cols = {r[1] for r in conn.execute("PRAGMA table_info(rh_outil_pieces)").fetchall()}
    if "cible" not in cols:
        conn.execute("ALTER TABLE rh_outil_pieces ADD COLUMN cible TEXT NOT NULL DEFAULT 'document'")

    repris = 0
    if "rh_outil_formation_documents" in _tables(conn):
        for lien in conn.execute(
            """SELECT fd.formation_id, d.id AS document_id, d.libelle
                 FROM rh_outil_formation_documents fd JOIN rh_outil_documents d ON d.id = fd.document_id"""
        ).fetchall():
            conn.execute(
                """INSERT OR IGNORE INTO rh_outil_formation_justificatifs (formation_id, libelle, cree_le)
                   VALUES (?,?,?)""",
                (lien[0], lien[2], now),
            )
            jid = conn.execute(
                """SELECT id FROM rh_outil_formation_justificatifs
                    WHERE formation_id=? AND libelle=? COLLATE NOCASE""",
                (lien[0], lien[2]),
            ).fetchone()[0]
            repris += conn.execute(
                """INSERT OR IGNORE INTO rh_outil_membre_justificatifs (attribution_id, justificatif_id, fait, ajoute_le)
                   SELECT a.id, ?, COALESCE((SELECT md.fait FROM rh_outil_membre_documents md
                                              WHERE md.membre_id = a.membre_id AND md.document_id = ?), 0), ?
                     FROM rh_outil_membre_formations a WHERE a.formation_id = ?""",
                (jid, lien[1], now, lien[0]),
            ).rowcount
        conn.execute("DROP TABLE rh_outil_formation_documents")

    # 3. « Règlement signé » → document administratif exigé pour tous
    conn.execute(
        """INSERT OR IGNORE INTO rh_outil_documents (libelle, cree_le, cree_par, obligatoire)
           VALUES (?,?,NULL,1)""",
        (REGLEMENT, now),
    )
    doc = conn.execute("SELECT id FROM rh_outil_documents WHERE libelle=? COLLATE NOCASE",
                       (REGLEMENT,)).fetchone()[0]
    conn.execute("UPDATE rh_outil_documents SET obligatoire=1 WHERE id=?", (doc,))
    conn.execute("DELETE FROM rh_outil_document_contrats WHERE document_id=?", (doc,))
    coches = conn.execute(
        """INSERT OR IGNORE INTO rh_outil_membre_documents (membre_id, document_id, fait, ajoute_le)
           SELECT m.id, ?, CASE WHEN m.reglement_signe = 1 THEN 1 ELSE 0 END, ?
             FROM rh_outil_membres m""",
        (doc, now),
    ).rowcount
    conn.execute(
        """UPDATE rh_outil_membre_documents SET fait = 1
            WHERE document_id = ? AND membre_id IN (SELECT id FROM rh_outil_membres WHERE reglement_signe = 1)""",
        (doc,),
    )
    conn.commit()
    print(f"[MySifa] migration {NOM} : {repris} justificatif(s) repris, "
          f"« {REGLEMENT} » attribué à {coches} employé(s).")
