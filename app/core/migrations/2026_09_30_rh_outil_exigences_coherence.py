"""
Outil RH : « Obligatoire pour tous » et « exigé pour des services » deviennent
exclusifs (un seul réglage « Exigé pour » : personne, tous les employés, ou
certains services).

Reprise : un élément qui cumulait les deux garde « tous les employés » et perd
ses services, qui n'avaient plus d'effet visible et pouvaient continuer
d'attribuer l'élément après qu'on l'avait rendu facultatif.
"""

NOM = "rh_outil_exigences_coherence"
DEPEND = ["rh_outil_exigences_services", "rh_outil_obligatoire"]


def appliquer(conn):
    n = 0
    for exig, fk, catalogue in (
        ("rh_outil_formation_services", "formation_id", "rh_outil_formations"),
        ("rh_outil_document_services", "document_id", "rh_outil_documents"),
    ):
        n += conn.execute(
            f"""DELETE FROM {exig}
                 WHERE {fk} IN (SELECT id FROM {catalogue} WHERE obligatoire = 1)"""
        ).rowcount
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n} exigence(s) par service retirée(s).")
