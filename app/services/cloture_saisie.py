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


# ── Recaler un créneau sur les saisies déjà faites ───────────────────────────
# Une saisie ne met le planning à jour qu'au moment où elle est faite, et
# seulement si elle trouve son créneau sur SA machine. Quand le créneau la
# rejoint après coup — dossier fictif rattaché, dossier changé de machine —
# personne ne relisait les saisies : 9932585 (16/10/2026) a été produit et
# clôturé sur Cohésio 2 pendant que son créneau était encore sur Cohésio 1,
# puis déplacé sur Cohésio 2, où il est resté « en attente ».

_CODES_HORS_CYCLE = ("86", "87")


def resynchroniser_creneau(conn, entry_id: int) -> Optional[str]:
    """Rattache au créneau ses saisies orphelines et recale son statut.

    Renvoie « termine » (fin « Dossier terminé » trouvée), « en_saisie »
    (dossier démarré, pas fini) ou None (rien à faire). Ne commite pas.

    Prudence sur les saisies non rattachées : elles ne sont prises que si ce
    créneau est le seul de la référence sur la machine — sinon elles peuvent
    appartenir à un passage précédent (reliquat), et clôturer le nouveau
    créneau avec l'ancienne fin serait faux.
    """
    pe = conn.execute(
        """SELECT pe.id, pe.reference, pe.numero_of, pe.statut, pe.statut_reel,
                  m.nom AS machine_nom, m.code AS machine_code
             FROM planning_entries pe JOIN machines m ON m.id = pe.machine_id
            WHERE pe.id = ?""",
        (entry_id,),
    ).fetchone()
    if not pe or pe["statut"] == "termine":
        return None
    refs = [r for r in {(pe["reference"] or "").strip(), (pe["numero_of"] or "").strip()} if r]
    macs = [m for m in {(pe["machine_nom"] or "").strip(), (pe["machine_code"] or "").strip()} if m]
    if not refs or not macs:
        return None

    cols = {r[1] for r in conn.execute("PRAGMA table_info(production_data)").fetchall()}
    if "planning_entry_id" not in cols:
        return None
    from app.services.lien_saisie_planning import candidats
    seul = len(candidats(conn, refs[0], macs[0])) <= 1
    ph_r, ph_m, ph_c = ",".join("?" * len(refs)), ",".join("?" * len(macs)), ",".join("?" * len(_CODES_HORS_CYCLE))
    orphelines = "OR planning_entry_id IS NULL" if seul else ""
    saisies = [dict(r) for r in conn.execute(
        f"""SELECT id, date_operation, operation_code, fin_dossier, planning_entry_id
              FROM production_data
             WHERE trim(no_dossier) IN ({ph_r}) AND trim(machine) IN ({ph_m})
               AND operation_code NOT IN ({ph_c})
               AND COALESCE(est_annule, 0) = 0
               AND (planning_entry_id = ? {orphelines})
             ORDER BY date_operation, id""",
        (*refs, *macs, *_CODES_HORS_CYCLE, entry_id),
    ).fetchall()]
    if not saisies:
        return None

    a_lier = [s["id"] for s in saisies if not s["planning_entry_id"]]
    if a_lier:
        conn.execute(
            f"UPDATE production_data SET planning_entry_id = ? WHERE id IN ({','.join('?' * len(a_lier))})",
            (entry_id, *a_lier),
        )

    now_iso = datetime.now().isoformat()
    derniere = saisies[-1]
    code = str(derniere["operation_code"] or "").strip()
    if code == "90":
        return None  # annulation : elle a son propre circuit
    if code == "89" and derniere["fin_dossier"] is not None and int(derniere["fin_dossier"]) == 1:
        debut = next((s["date_operation"] for s in saisies if str(s["operation_code"]).strip() == "01"),
                     saisies[0]["date_operation"])
        conn.execute(
            """UPDATE planning_entries
                  SET statut = 'termine', statut_force = 1, statut_reel = 'reellement_termine',
                      planned_start = ?, planned_end = ?, updated_at = ?
                WHERE id = ?""",
            (debut, derniere["date_operation"], now_iso, entry_id),
        )
        return "termine"
    if (pe["statut_reel"] or "reellement_en_attente") == "reellement_en_attente":
        conn.execute(
            "UPDATE planning_entries SET statut_reel = 'reellement_en_saisie', updated_at = ? WHERE id = ?",
            (now_iso, entry_id),
        )
        return "en_saisie"
    return None


def ranger_dans_historique(conn, machine_id: int, entry_id: int) -> None:
    """Range un dossier qui vient de passer Terminé parmi l'historique de la
    machine, à sa date de fin, au lieu de le laisser au milieu de la file.
    Ne commite pas."""
    rows = [dict(r) for r in conn.execute(
        """SELECT id, statut, planned_end FROM planning_entries
            WHERE machine_id = ? ORDER BY position ASC, id ASC""",
        (machine_id,),
    ).fetchall()]
    moi = next((r for r in rows if int(r["id"]) == int(entry_id)), None)
    if not moi:
        return
    rows = [r for r in rows if r is not moi]
    fin = moi["planned_end"] or ""
    rang = len(rows)
    for i, r in enumerate(rows):
        # Historique en tête : terminés puis en cours, avant la file d'attente.
        if r["statut"] != "termine" or (r["planned_end"] or "") > fin:
            rang = i
            break
    ordre = rows[:rang] + [moi] + rows[rang:]
    now_iso = datetime.now().isoformat()
    for pos, r in enumerate(ordre, start=1):
        conn.execute(
            "UPDATE planning_entries SET position = ?, updated_at = ? WHERE id = ? AND machine_id = ?",
            (pos, now_iso, r["id"], machine_id),
        )
