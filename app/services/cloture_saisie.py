"""
Corriger après coup le choix fait à la « Fin de production » (89).

À la fin de production, l'opérateur choisit « Dossier terminé » ou « À
reprendre plus tard » (`production_data.fin_dossier`). Une erreur de bouton
laissait un dossier fini en attente au planning, ou fermait un dossier qui
devait repasser — sans moyen de le corriger depuis MyProd › Saisies.

`changer(conn, row_id, cloture, auteur)` réécrit le choix et en rejoue les
conséquences, comme la saisie l'aurait fait :
- planning : le créneau passe Terminé (clôture) ou revient En attente
  (reprise), sauf si la machine a redémarré le dossier depuis — il est alors
  en cours, et cette fin n'y change rien ;
- mémoire produit : la série est figée à la clôture, retirée à la reprise si
  aucune autre fin du dossier ne le clôture.

Le déstockage de clôture n'est pas rejoué : il se pilote depuis Besoins
matières, où son état reste visible.
"""
from datetime import datetime
from typing import Optional


def _planning_entry(conn, row: dict) -> Optional[dict]:
    pe_id = row.get("planning_entry_id")
    if not pe_id:
        try:
            from app.services.lien_saisie_planning import resoudre
            pe_id = resoudre(conn, row)
        except Exception:
            pe_id = None
    if not pe_id:
        return None
    pe = conn.execute(
        "SELECT id, machine_id, statut, statut_reel FROM planning_entries WHERE id = ?",
        (int(pe_id),),
    ).fetchone()
    return dict(pe) if pe else None


def changer(conn, row_id: int, cloture: bool, auteur: str) -> dict:
    """Passe la fin de production `row_id` en clôture (True) ou en reprise (False)."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(production_data)").fetchall()}
    if "fin_dossier" not in cols:
        raise ValueError("Base non migrée : colonne fin_dossier absente.")
    sel = "planning_entry_id" if "planning_entry_id" in cols else "NULL AS planning_entry_id"
    r = conn.execute(
        f"""SELECT id, operation_code, no_dossier, machine, date_operation,
                   fin_dossier, COALESCE(est_annule, 0) AS est_annule, {sel}
              FROM production_data WHERE id = ?""",
        (row_id,),
    ).fetchone()
    if not r:
        raise ValueError("Saisie introuvable.")
    row = dict(r)
    if str(row["operation_code"] or "").strip() != "89":
        raise ValueError("Seule une fin de production porte ce choix.")
    if int(row["est_annule"] or 0):
        raise ValueError("Saisie annulée avec le dossier — modification impossible.")
    ref = (row["no_dossier"] or "").strip()
    if not ref:
        raise ValueError("Fin de production sans dossier.")

    nouveau = 1 if cloture else 0
    avant = row["fin_dossier"]
    conn.execute("UPDATE production_data SET fin_dossier = ? WHERE id = ?", (nouveau, row_id))
    if avant is not None and int(avant) == nouveau:
        conn.commit()
        return {"no_dossier": ref, "fin_dossier": nouveau, "planning": "inchange", "serie": None}

    now_iso = datetime.now().isoformat()
    machine = (row["machine"] or "").strip()
    date_op = row["date_operation"]

    # 1. Planning — seulement si la machine n'a pas repris le dossier depuis.
    planning = "inchange"
    pe = _planning_entry(conn, row)
    if pe:
        from app.services.annulation_fin_production import _dossier_en_production_apres
        repris = _dossier_en_production_apres(conn, ref, machine, date_op, row_id)
        if repris:
            planning = "repris"
        elif nouveau == 1 and pe["statut"] != "termine":
            conn.execute(
                """UPDATE planning_entries
                      SET statut = 'termine', statut_force = 1,
                          statut_reel = 'reellement_termine',
                          planned_end = ?, updated_at = ?
                    WHERE id = ?""",
                (date_op, now_iso, pe["id"]),
            )
            planning = "termine"
        elif nouveau == 0 and pe["statut"] == "termine":
            # Démarré, pas fini : il revient dans la file de la machine.
            conn.execute(
                """UPDATE planning_entries
                      SET statut = 'attente', statut_force = 0,
                          statut_reel = 'reellement_en_saisie', updated_at = ?
                    WHERE id = ?""",
                (now_iso, pe["id"]),
            )
            planning = "attente"
    conn.commit()

    if pe and planning in ("termine", "attente") and pe.get("machine_id") is not None:
        try:
            from app.routers.planning import _invalidate_attente_plans
            _invalidate_attente_plans(conn, pe["machine_id"])
            conn.commit()
        except Exception:
            pass

    # 2. Mémoire produit — la série n'existe que pour un dossier clôturé.
    serie = None
    try:
        if nouveau == 1:
            from app.services.produit_memoire import materialiser_serie
            materialiser_serie(conn, ref, cloture_par=auteur)
            serie = "materialisee"
        else:
            autre = conn.execute(
                """SELECT 1 FROM production_data
                    WHERE trim(no_dossier) = ? AND operation_code = '89'
                      AND fin_dossier = 1 AND id <> ? AND COALESCE(est_annule, 0) = 0
                    LIMIT 1""",
                (ref, row_id),
            ).fetchone()
            if not autre:
                conn.execute("DELETE FROM produit_series WHERE no_dossier = ?", (ref,))
                serie = "supprimee"
        conn.commit()
    except Exception:
        pass

    return {"no_dossier": ref, "fin_dossier": nouveau, "planning": planning, "serie": serie}
