"""
Créneaux restés « en attente » alors que leur dossier a été produit et clôturé.

Le planning ne suivait une saisie qu'au moment où elle était faite, et
seulement sur le créneau de SA machine. Un dossier saisi en fictif puis
rattaché, ou déplacé sur la machine où il avait tourné après coup, gardait
son statut d'avant : 9932585 (ALCYON, Cohésio 2, clôturé le 16/10/2026)
apparaissait encore à venir le 19/10. Rattachement et changement de machine
recalent désormais le créneau (app/services/cloture_saisie) ; cette reprise
applique le même recalage aux créneaux non terminés dont la dernière saisie
sur leur machine est une fin « Dossier terminé ». Rejouable.
"""

NOM = "creneaux_clotures_resynchro"
DEPEND = ["saisie_fin_dossier", "saisie_lien_planning"]


def appliquer(conn):
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if not {"planning_entries", "production_data", "machines"} <= tables:
        return
    cols = {r[1] for r in conn.execute("PRAGMA table_info(production_data)").fetchall()}
    if not {"fin_dossier", "planning_entry_id"} <= cols:
        return

    from app.services.cloture_saisie import resynchroniser_creneau, ranger_dans_historique
    candidats = conn.execute(
        """SELECT pe.id, pe.machine_id FROM planning_entries pe
             JOIN machines m ON m.id = pe.machine_id
            WHERE pe.statut <> 'termine'
              AND EXISTS (SELECT 1 FROM production_data pd
                           WHERE trim(pd.no_dossier) IN (trim(pe.reference), trim(COALESCE(pe.numero_of, '')))
                             AND trim(pd.machine) = trim(m.nom)
                             AND pd.operation_code = '89' AND pd.fin_dossier = 1
                             AND COALESCE(pd.est_annule, 0) = 0)"""
    ).fetchall()
    recales = []
    for c in candidats:
        if resynchroniser_creneau(conn, int(c["id"])) == "termine":
            ranger_dans_historique(conn, int(c["machine_id"]), int(c["id"]))
            recales.append(int(c["id"]))
            conn.commit()
        else:
            conn.rollback()  # seule la clôture est reprise ici
    conn.commit()
    print(f"[MySifa] migration {NOM} : {len(recales)} créneau(x) passé(s) Terminé {recales}.")
