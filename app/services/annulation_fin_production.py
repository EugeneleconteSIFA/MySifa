"""
Convertir après coup une « Fin de production » (89) en annulation de dossier.

Pourquoi. L'annulation n'existe qu'au poste opérateur, et seulement tant que le
dossier est en cours (`POST /api/fabrication/annuler-dossier`). Quand
l'opérateur clôt un dossier par une fin de production alors qu'il a en réalité
été annulé, plus rien ne permettait de rattraper la saisie : le dossier restait
« terminé » au planning, sa série figée dans la mémoire produit, et il fallait
le dupliquer à la main — doublon que les garde-fous du planning empêchaient
ensuite de placer. Cas réel : Reliquat 9932324 (Cohésio 2, SOLUROAD), 09/09/2026.

Ce que fait la conversion — exactement ce qu'aurait fait l'annulation opérateur
au moment de la fin de production :
- les saisies du cycle (dernier 01 du dossier sur la machine jusqu'au 89, hors
  pointage 86/87 et traces 90) reçoivent `annule_le/par/motif`. `est_annule`
  n'est pas posé : le temps passé compte (voir la migration
  `annulation_conserve_les_temps`) ;
- le 89 devient, EN PLACE, la trace « 90 - Annulation dossier » : même date,
  même compteur de fin, compteur de début du cycle. La chaîne des compteurs
  machine reste intacte et le métrage consommé reste mesurable. La quantité et
  le commentaire d'origine sont conservés dans `data.converti_depuis` ;
- au planning, le créneau du passage annulé reste en place, terminé et marqué
  « Annulé » : c'est l'historique de ce qui s'est réellement passé sur la
  machine. Pour relancer le dossier, un SECOND créneau est créé en attente
  (copie du dossier), juste après les dossiers déjà engagés. Retour d'usage
  du 10/09/2026 : remettre le même créneau en attente effaçait le passage
  annulé du planning et laissait le badge « Annulé » sur le dossier relancé.
  S'il existe déjà un doublon en attente — dossier recréé à la main — on peut
  ne pas créer de second créneau ;
- la série de la mémoire produit est rematérialisée.

Le compteur machine (`machines.dernier_metrage`) n'est pas touché : le relevé
du 89 est déjà celui qu'aurait porté l'annulation.
"""
import json
from datetime import datetime
from typing import Optional

from config import classify_operation

CODE_ANNULATION = "90"
CODES_HORS_CYCLE = ("86", "87", "90")
CODES_PRODUCTION_REELLE = ("03", "88")


def _colonnes(conn, table: str) -> set:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _flottant(v) -> Optional[float]:
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def contexte(conn, row_id: int) -> dict:
    """Tout ce qu'il faut pour afficher l'aperçu et exécuter la conversion.

    Aucune écriture. `convertible` est faux avec une `raison` lisible dès
    qu'une condition manque.
    """
    out = {
        "convertible": False, "raison": "", "saisie_id": row_id,
        "no_dossier": None, "machine": None, "machine_id": None,
        "date_fin": None, "debut": None, "ids_cycle": [],
        "nb_saisies": 0, "nb_production": 0,
        "metrage_debut": None, "metrage_fin": None, "quantite_traitee": None,
        "planning": None, "doublons": [],
    }
    row = conn.execute("SELECT * FROM production_data WHERE id=?", (row_id,)).fetchone()
    if not row:
        out["raison"] = "Saisie introuvable."
        return out
    row = dict(row)
    if str(row.get("operation_code") or "").strip() != "89":
        out["raison"] = "Seule une « Fin de production » (89) peut être convertie en annulation."
        return out
    if int(row.get("est_annule") or 0):
        out["raison"] = "Saisie déjà neutralisée par une annulation."
        return out
    ref = (row.get("no_dossier") or "").strip()
    if not ref:
        out["raison"] = "Fin de production sans dossier — rien à annuler."
        return out
    machine_nom = (row.get("machine") or "").strip()
    date_fin = str(row.get("date_operation") or "").strip()
    out.update({
        "no_dossier": ref, "machine": machine_nom, "date_fin": date_fin,
        "metrage_fin": _flottant(row.get("metrage_total_fin")) if row.get("metrage_total_fin") is not None
        else _flottant(row.get("metrage_reel")),
        "quantite_traitee": _flottant(row.get("quantite_traitee")),
        "client": row.get("client"), "designation": row.get("designation"),
        "commentaire": row.get("commentaire"),
    })

    mac = conn.execute(
        """SELECT id, nom, code FROM machines
            WHERE trim(nom) = trim(?) OR (trim(COALESCE(code,'')) <> '' AND trim(code) = trim(?))
            ORDER BY id LIMIT 1""",
        (machine_nom, machine_nom),
    ).fetchone()
    if not mac:
        out["raison"] = f"Machine « {machine_nom or '—'} » introuvable."
        return out
    out["machine_id"] = int(mac["id"])
    noms = {machine_nom, (mac["nom"] or "").strip(), (mac["code"] or "").strip()} - {""}
    ph_m = ",".join("?" * len(noms))

    debut = conn.execute(
        f"""SELECT id, date_operation, COALESCE(metrage_total_debut, metrage_prevu) AS ctr
              FROM production_data
             WHERE trim(no_dossier) = ? AND operation_code = '01'
               AND COALESCE(est_annule, 0) = 0
               AND trim(machine) IN ({ph_m})
               AND (date_operation < ? OR (date_operation = ? AND id < ?))
             ORDER BY date_operation DESC, id DESC LIMIT 1""",
        (ref, *noms, date_fin, date_fin, row_id),
    ).fetchone()
    if not debut:
        out["raison"] = "Début de production introuvable pour ce cycle."
        return out
    out["debut"] = debut["date_operation"]
    out["metrage_debut"] = _flottant(debut["ctr"])

    deja = conn.execute(
        f"""SELECT 1 FROM production_data
             WHERE trim(no_dossier) = ? AND operation_code = '90'
               AND trim(machine) IN ({ph_m})
               AND date_operation >= ? AND date_operation <= ?
             LIMIT 1""",
        (ref, *noms, debut["date_operation"], date_fin),
    ).fetchone()
    if deja:
        out["raison"] = "Ce cycle porte déjà une annulation."
        return out

    ph_c = ",".join("?" * len(CODES_HORS_CYCLE))
    cycle = conn.execute(
        f"""SELECT id, operation_code FROM production_data
             WHERE trim(no_dossier) = ?
               AND COALESCE(est_annule, 0) = 0
               AND trim(machine) IN ({ph_m})
               AND operation_code NOT IN ({ph_c})
               AND date_operation >= ? AND date_operation <= ?
               AND id <> ?
             ORDER BY date_operation, id""",
        (ref, *noms, *CODES_HORS_CYCLE, debut["date_operation"], date_fin, row_id),
    ).fetchall()
    out["ids_cycle"] = [int(r["id"]) for r in cycle]
    out["nb_saisies"] = len(out["ids_cycle"]) + 1
    out["nb_production"] = sum(
        1 for r in cycle if str(r["operation_code"] or "").strip() in CODES_PRODUCTION_REELLE
    )

    # Entrée planning fermée par ce 89 : la terminée la plus récente de ce
    # dossier sur la machine. Les autres entrées non terminées du même dossier
    # sont des doublons (typiquement une duplication faite à la main).
    entrees = [dict(r) for r in conn.execute(
        """SELECT id, reference, numero_of, statut, statut_reel, position, annule_count
             FROM planning_entries
            WHERE machine_id = ?
              AND (trim(reference) = ? OR trim(COALESCE(numero_of,'')) = ?)
            ORDER BY CASE statut WHEN 'termine' THEN 0 ELSE 1 END, position DESC, id DESC""",
        (out["machine_id"], ref, ref),
    ).fetchall()]
    if entrees:
        out["planning"] = entrees[0]
        out["doublons"] = [e for e in entrees[1:] if e["statut"] != "termine"]
        # Un dossier recréé à la main ne porte pas forcément la même référence
        # (« 9932324 » pour « Reliquat 9932324 ») : même référence produit et
        # même client, en attente sur la machine, c'est un doublon probable.
        src = conn.execute(
            "SELECT ref_produit, client FROM planning_entries WHERE id = ?",
            (entrees[0]["id"],),
        ).fetchone()
        rp = (src["ref_produit"] or "").strip() if src else ""
        if rp:
            deja = {e["id"] for e in entrees}
            for r in conn.execute(
                """SELECT id, reference, numero_of, statut, statut_reel, position, annule_count
                     FROM planning_entries
                    WHERE machine_id = ? AND statut <> 'termine'
                      AND trim(COALESCE(ref_produit,'')) = ?
                      AND lower(trim(COALESCE(client,''))) = lower(trim(?))
                    ORDER BY position""",
                (out["machine_id"], rp, (src["client"] or "")),
            ).fetchall():
                if r["id"] not in deja:
                    out["doublons"].append(dict(r))

    out["convertible"] = True
    return out


def _replacer_apres_tete(conn, machine_id: int, entry_id: int) -> None:
    """Place l'entrée juste après les dossiers engagés de tête de liste.

    Remise en attente, l'entrée garderait sa position d'origine : derrière elle,
    d'autres dossiers ont démarré depuis, et un dossier en attente coincé dans
    l'historique fausse la replanification. On la remet en tête des attentes —
    là où la laisse une annulation faite au poste.
    """
    from app.routers.planning import compute_statut

    rows = [dict(r) for r in conn.execute(
        """SELECT id, statut, statut_force, planned_start, planned_end
             FROM planning_entries WHERE machine_id = ?
            ORDER BY position ASC, id ASC""",
        (machine_id,),
    ).fetchall()]
    autres = [r for r in rows if int(r["id"]) != entry_id]
    tete = 0
    for r in autres:
        if compute_statut(r) not in ("en_cours", "termine"):
            break
        tete += 1
    ordre = [int(r["id"]) for r in autres]
    ordre.insert(tete, entry_id)
    for pos, eid in enumerate(ordre, start=1):
        conn.execute(
            "UPDATE planning_entries SET position = ? WHERE id = ? AND machine_id = ? AND position IS NOT ?",
            (pos, eid, machine_id, pos),
        )


_COLONNES_NON_COPIEES = {
    "id", "position", "statut", "statut_force", "statut_reel",
    "planned_start", "planned_end", "planned_end_manual",
    "created_at", "updated_at", "created_by", "updated_by",
    "group_id", "split_parent_id",
    "annule_count", "annule_motif", "annule_par", "annule_le",
    "destockage", "destockage_at", "destockage_reserve",
}


def _creer_second_creneau(conn, source_id: int, auteur: str, now_iso: str) -> int:
    """Copie le dossier au planning dans un nouveau créneau en attente.

    Tout ce qui décrit le dossier est repris (client, OF, formats, laize,
    livraison, FSC, exigences…). Ce qui décrit le passage annulé ne l'est pas :
    créneau, statuts, marque d'annulation, déstockage déjà fait.
    """
    cols = [c for c in _colonnes(conn, "planning_entries") if c not in _COLONNES_NON_COPIEES]
    row = dict(conn.execute("SELECT * FROM planning_entries WHERE id = ?", (source_id,)).fetchone())
    valeurs = {c: row.get(c) for c in cols}
    valeurs.update({"statut": "attente", "statut_force": 0, "position": 0,
                    "created_at": now_iso, "updated_at": now_iso})
    toutes = _colonnes(conn, "planning_entries")
    if "statut_reel" in toutes:
        valeurs["statut_reel"] = "reellement_en_attente"
    if "created_by" in toutes:
        valeurs["created_by"] = auteur
    noms = list(valeurs)
    cur = conn.execute(
        f"INSERT INTO planning_entries ({', '.join(noms)}) VALUES ({', '.join('?' * len(noms))})",
        [valeurs[n] for n in noms],
    )
    new_id = int(cur.lastrowid)
    if "group_id" in toutes:
        conn.execute("UPDATE planning_entries SET group_id = CAST(id AS TEXT) WHERE id = ?", (new_id,))
    return new_id


def convertir(conn, row_id: int, motif: str, remettre_planning: bool,
              auteur: str, auteur_email: str) -> dict:
    ctx = contexte(conn, row_id)
    if not ctx["convertible"]:
        raise ValueError(ctx["raison"] or "Conversion impossible.")

    now_iso = datetime.now().isoformat()
    ref = ctx["no_dossier"]
    row = dict(conn.execute("SELECT * FROM production_data WHERE id=?", (row_id,)).fetchone())

    # 1. Le cycle est marqué, sans rien retirer aux chiffres.
    if ctx["ids_cycle"]:
        ph = ",".join("?" * len(ctx["ids_cycle"]))
        conn.execute(
            f"""UPDATE production_data
                   SET annule_le = ?, annule_par = ?, annule_motif = ?
                 WHERE id IN ({ph})""",
            (now_iso, auteur, motif, *ctx["ids_cycle"]),
        )

    # 2. Le 89 devient la trace 90, en place.
    m_debut, m_fin = ctx["metrage_debut"], ctx["metrage_fin"]
    consomme = max(0.0, m_fin - m_debut) if (m_fin is not None and m_debut is not None) else None
    try:
        data_prec = json.loads(row.get("data") or "{}")
        if not isinstance(data_prec, dict):
            data_prec = {}
    except Exception:
        data_prec = {}
    trace = {
        "no_dossier": ref,
        "motif": motif,
        "saisies_annulees": ctx["ids_cycle"],
        "machine": ctx["machine"],
        "metrage_debut": m_debut,
        "metrage_fin": m_fin,
        "metrage_consomme": consomme,
        "nb_saisies_production": ctx["nb_production"],
        "converti_depuis": {
            "operation": row.get("operation"),
            "operation_code": "89",
            "quantite_traitee": row.get("quantite_traitee"),
            "commentaire": row.get("commentaire"),
            "fin_dossier": row.get("fin_dossier"),
            "data": data_prec,
            "converti_le": now_iso,
            "converti_par": auteur_email,
        },
    }
    libelle = f"{CODE_ANNULATION} - Annulation dossier"
    cl = classify_operation(libelle)
    commentaire_prec = (row.get("commentaire") or "").strip()
    commentaire = f"Dossier annulé — {motif}" + (f" · {commentaire_prec}" if commentaire_prec else "")
    conn.execute(
        """UPDATE production_data
              SET operation = ?, operation_code = ?, operation_severity = ?, operation_category = ?,
                  quantite_traitee = 0,
                  metrage_prevu = ?, metrage_reel = ?,
                  metrage_total_debut = ?, metrage_total_fin = ?,
                  commentaire = ?, data = ?,
                  modifie_par = ?, modifie_le = ?, modifie_note = ?,
                  est_annule = 0, annule_le = ?, annule_par = ?, annule_motif = ?
            WHERE id = ?""",
        (libelle, CODE_ANNULATION, cl["severity"], cl["category"],
         m_debut, m_fin, m_debut, m_fin,
         commentaire, json.dumps(trace, default=str),
         auteur_email, now_iso, "Fin de production convertie en annulation",
         now_iso, auteur, motif, row_id),
    )
    if "fin_dossier" in _colonnes(conn, "production_data"):
        conn.execute("UPDATE production_data SET fin_dossier = NULL WHERE id = ?", (row_id,))

    # 3. Planning.
    pe = ctx["planning"]
    planning_action = None
    nouveau_id = None
    if pe:
        pe_id = int(pe["id"])
        if pe["statut"] == "termine":
            # Le créneau du passage annulé reste : terminé, marqué annulé.
            conn.execute(
                """UPDATE planning_entries
                      SET statut_reel = 'reellement_termine',
                          annule_count = COALESCE(annule_count, 0) + 1,
                          annule_motif = ?, annule_par = ?, annule_le = ?,
                          updated_at = ?
                    WHERE id = ?""",
                (motif, auteur, now_iso, now_iso, pe_id),
            )
            if remettre_planning:
                nouveau_id = _creer_second_creneau(conn, pe_id, auteur, now_iso)
                _replacer_apres_tete(conn, ctx["machine_id"], nouveau_id)
                planning_action = "second_creneau"
            else:
                planning_action = "marque_annule"
        else:
            # Créneau jamais clos (fin « à reprendre ») : c'est encore le
            # dossier à produire, il repart en attente comme au poste.
            conn.execute(
                """UPDATE planning_entries
                      SET statut = 'attente', statut_force = 0,
                          statut_reel = 'reellement_en_attente',
                          planned_start = NULL, planned_end = NULL, planned_end_manual = 0,
                          annule_count = COALESCE(annule_count, 0) + 1,
                          annule_motif = ?, annule_par = ?, annule_le = ?,
                          updated_at = ?
                    WHERE id = ?""",
                (motif, auteur, now_iso, now_iso, pe_id),
            )
            _replacer_apres_tete(conn, ctx["machine_id"], pe_id)
            planning_action = "remis_en_attente"
    conn.commit()

    # 4. Best effort : replanification et mémoire produit ne bloquent jamais.
    if pe:
        try:
            from app.routers.planning import _invalidate_attente_plans
            _invalidate_attente_plans(conn, ctx["machine_id"])
            conn.commit()
        except Exception:
            pass
    serie = False
    try:
        from app.services.produit_memoire import materialiser_serie
        serie = bool(materialiser_serie(conn, ref, cloture_par=auteur))
        conn.commit()
    except Exception:
        pass

    return {
        "no_dossier": ref,
        "machine": ctx["machine"],
        "saisies_marquees": len(ctx["ids_cycle"]),
        "metrage_consomme": consomme,
        "planning_entry_id": int(pe["id"]) if pe else None,
        "planning": planning_action,
        "nouveau_creneau_id": nouveau_id,
        "serie_rematerialisee": serie,
    }
