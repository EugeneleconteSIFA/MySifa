"""
TVA des anciennes notes de frais : 20 % par défaut.

Avant les catégories (migration `ndf_categories`), une note de frais n'avait
qu'un montant TTC, sans TVA. La reprise `ndf_tva_lignes` leur a donné une ligne
« Sans TVA » : la comptabilité voyait 0 € de TVA récupérable sur tout
l'historique. Décision du 25/10/2026 : ces notes passent à 20 %, le taux le
plus courant, sans relire les justificatifs un par un. Un taux faux se corrige
ensuite note par note.

Sont reprises les notes en montant (pas les indemnités kilométriques), sans
catégorie du référentiel (donc saisies avant lui), sans aucune TVA et non
supprimées. Une note saisie volontairement « Sans TVA » depuis a une catégorie
et n'est pas touchée. Rejouable : une note reprise a une TVA, elle n'est plus
retenue.
"""

NOM = "ndf_anciennes_notes_tva_20"
DEPEND = ["ndf_tva_lignes"]

_TAUX = 20.0


def appliquer(conn):
    rows = conn.execute(
        """SELECT id, montant_ttc FROM notes_de_frais n
           WHERE deleted_at IS NULL
             AND distance_km IS NULL
             AND categorie_id IS NULL
             AND montant_ttc > 0
             AND COALESCE(montant_tva, 0) = 0
             AND NOT EXISTS (SELECT 1 FROM notes_de_frais_tva t
                             WHERE t.note_id = n.id AND (t.taux_tva > 0 OR t.montant_tva > 0))"""
    ).fetchall()
    for note_id, ttc in rows:
        ttc = round(float(ttc), 2)
        tva = round(ttc * _TAUX / (100 + _TAUX), 2)
        ht = round(ttc - tva, 2)
        conn.execute(
            "UPDATE notes_de_frais SET taux_tva=?, montant_tva=?, montant_ht=? WHERE id=?",
            (_TAUX, tva, ht, note_id),
        )
        conn.execute("DELETE FROM notes_de_frais_tva WHERE note_id=?", (note_id,))
        conn.execute(
            """INSERT INTO notes_de_frais_tva
               (note_id, ordre, taux_tva, montant_ttc, montant_tva, montant_ht)
               VALUES (?,?,?,?,?,?)""",
            (note_id, 0, _TAUX, ttc, tva, ht),
        )
    conn.commit()
    if rows:
        print(f"[MySifa] migration {NOM} : {len(rows)} note(s) passée(s) à 20 % de TVA.")
