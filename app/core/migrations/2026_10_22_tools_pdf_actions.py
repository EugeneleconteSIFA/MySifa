"""
MyTools › Éditeur PDF — actions enregistrées (suites d'étapes réutilisables).

Une action = un nom et une liste d'étapes JSON (filigrane, compression,
numérotation, OCR, renommage…) que l'utilisateur rejoue sur un lot de PDF.
Gardée en base et non dans le navigateur : c'est un outil de travail que l'on
retrouve sur tous ses postes (atelier, bureau), pas une préférence d'affichage.

tools_pdf_actions : une ligne par action et par utilisateur (nom unique par
                    utilisateur).
"""

NOM = "tools_pdf_actions"


def appliquer(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tools_pdf_actions (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   INTEGER NOT NULL,
            nom       TEXT NOT NULL,
            etapes    TEXT NOT NULL DEFAULT '[]',
            cree_le   TEXT NOT NULL,
            maj_le    TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tools_pdf_actions_nom ON tools_pdf_actions(user_id, nom)")
