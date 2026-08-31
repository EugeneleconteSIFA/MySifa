"""
MyExpé — note de départ 5/10 pour tous les transporteurs.

Le premier jet ne donnait aucune note tant qu'aucun avis n'avait été émis :
le référentiel affichait « aucun avis » sur toute la colonne, et le
comparateur n'avait rien à montrer. La note de départ (`NOTE_DEPART`, 5/10,
soit C) est désormais une composante du calcul, avec le poids d'un avis.

Cette migration ne change aucun schéma : elle recalcule le cache
(`note_valeur`, `note_lettre`) de tous les transporteurs, sans quoi les lignes
créées avant elle resteraient à NULL jusqu'au premier avis.
"""

NOM = "expe_note_depart"
DEPEND = ["expe_notes_transporteurs"]


def appliquer(conn):
    from app.services import expe_notes

    nb = expe_notes.recalculer_toutes(conn)
    conn.commit()
    print(f"[MySifa] migration {NOM} : note recalculee pour {nb} transporteur(s).")
