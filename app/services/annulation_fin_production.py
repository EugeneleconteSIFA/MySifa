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

    # Dossier repris après cette fin de production (fin « à reprendre » suivie
    # d'un nouveau démarrage) : il n'a pas été annulé, il a continué. Cas réel
    # du 10/09/2026 : M.718/3 cartons - 3e cadence converti par erreur alors
    # que la machine tournait dessus — le planning l'a sorti de « en cours ».
    ph_p = ",".join("?" * len(CODES_HORS_CYCLE))
    repris = conn.execute(
        f"""SELECT date_operation FROM production_data
             WHERE trim(no_dossier) = ? AND trim(machine) IN ({ph_m})
               AND operation_code NOT IN ({ph_p})
               AND (date_operation > ? OR (date_operation = ? AND id > ?))
             ORDER BY date_operation LIMIT 1""",
        (ref, *noms, *CODES_HORS_CYCLE, date_fin, date_fin, row_id),
    ).fetchone()
    if repris:
        out["raison"] = (
            "Le dossier a repris après cette fin de production (saisie du "
            f"{str(repris['date_operation'])[:16].replace('T', ' ')}) : "
            "il n'a pas été annulé."
        )
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
    # Lien explicite posé à la saisie : il désigne le créneau sans ambiguïté.
    lie = row.get("planning_entry_id")
    if lie:
        e_lie = next((e for e in entrees if int(e["id"]) == int(lie)), None)
        if e_lie is None:
            r_lie = conn.execute(
                """SELECT id, reference, numero_of, statut, statut_reel, position, annule_count
                     FROM planning_entries WHERE id = ?""", (lie,)).fetchone()
            e_lie = dict(r_lie) if r_lie else None
        if e_lie is not None:
            entrees = [e_lie] + [e for e in entrees if int(e["id"]) != int(e_lie["id"])]
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


_COLONNES_PLANNING_RETABLIES = (
    "position", "statut", "statut_force", "statut_reel",
    "planned_start", "planned_end", "planned_end_manual",
    "annule_count", "annule_motif", "annule_par", "annule_le",
)

_COLONNES_NON_COPIEES = {
    "id", "position", "statut", "statut_force", "statut_reel",
    "planned_start", "planned_end", "planned_end_manual",
    "created_at", "updated_at", "created_by", "updated_by",
    "group_id", "split_parent_id",
    "annule_count", "annule_motif", "annule_par", "annule_le",
    "destockage", "destockage_at", "destockage_reserve",
    "destockage_par", "destockage_relu_par", "destockage_relu_at",
    "destockage_rvgi", "destockage_rvgi_at", "destockage_rvgi_par",
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

    # Ce qu'il faut pour pouvoir tout rétablir (voir `retablir`).
    planning_avant = None
    if ctx["planning"]:
        pe_row = conn.execute(
            "SELECT * FROM planning_entries WHERE id = ?", (ctx["planning"]["id"],)
        ).fetchone()
        if pe_row:
            planning_avant = {k: pe_row[k] for k in pe_row.keys() if k in _COLONNES_PLANNING_RETABLIES}
            planning_avant["id"] = pe_row["id"]
    serie_existait = False
    try:
        serie_existait = conn.execute(
            "SELECT 1 FROM produit_series WHERE no_dossier = ?", (ref,)
        ).fetchone() is not None
    except Exception:
        pass

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
            "metrage_prevu": row.get("metrage_prevu"),
            "metrage_reel": row.get("metrage_reel"),
            "metrage_total_debut": row.get("metrage_total_debut"),
            "metrage_total_fin": row.get("metrage_total_fin"),
            "modifie_par": row.get("modifie_par"),
            "modifie_le": row.get("modifie_le"),
            "modifie_note": row.get("modifie_note"),
            "planning_avant": planning_avant,
            "serie_existait": serie_existait,
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
    if nouveau_id is not None:
        trace["converti_depuis"]["nouveau_creneau_id"] = nouveau_id
        conn.execute("UPDATE production_data SET data = ? WHERE id = ?",
                     (json.dumps(trace, default=str), row_id))
    conn.commit()

    # 4. Best effort : replanification et mémoire produit ne bloquent jamais.
    if pe:
        try:
            from app.routers.planning import _invalidate_attente_plans
            _invalidate_attente_plans(conn, ctx["machine_id"])
            conn.commit()
        except Exception:
            pass
    # Série : rafraîchie seulement si elle existait (dossier clôturé). Une fin
    # « à reprendre » n'a pas de série, la conversion ne doit pas en créer une.
    serie = False
    if serie_existait:
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



# ─────────────────────────────────────────────────────────────────────────────
# Annuler une annulation
# ─────────────────────────────────────────────────────────────────────────────
# Retour d'usage du 10/09/2026 : une fin de production convertie par erreur ne
# se rattrapait plus. La trace 90 garde tout ce qu'il faut :
# - annulation issue d'une conversion (`data.converti_depuis`) : la saisie 89
#   d'origine, l'état du planning et l'existence de la série sont rétablis à
#   l'identique ; le second créneau créé est supprimé s'il n'a pas servi ;
# - annulation faite au poste : il n'y a pas d'origine, la trace devient une
#   « Fin de production » et on demande si le dossier était terminé ou à
#   reprendre. Le planning se déduit des saisies.


def _data_trace(row: dict) -> dict:
    try:
        d = json.loads(row.get("data") or "{}")
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def contexte_retablir(conn, row_id: int) -> dict:
    out = {"retablissable": False, "raison": "", "saisie_id": row_id,
           "no_dossier": None, "machine": None, "date": None, "motif": None,
           "conversion": False, "fin_dossier": None, "quantite_traitee": None,
           "nb_saisies": 0, "planning": None, "nouveau_creneau": None}
    row = conn.execute("SELECT * FROM production_data WHERE id=?", (row_id,)).fetchone()
    if not row:
        out["raison"] = "Saisie introuvable."
        return out
    row = dict(row)
    code = str(row.get("operation_code") or "").strip()
    if code != CODE_ANNULATION:
        # Depuis une saisie du cycle, ou depuis une trace déjà remise à la main
        # en « Fin de production » : l'édition ne retire pas les marques
        # d'annulation (cas du 10/09/2026, lignes restées « cycle annulé »). On
        # retrouve la trace par sa date d'annulation, commune à tout le cycle.
        annule_le = (row.get("annule_le") or "").strip()
        if not annule_le:
            out["raison"] = "Cette saisie ne porte aucune annulation."
            return out
        trace = conn.execute(
            """SELECT * FROM production_data
                WHERE trim(no_dossier) = trim(?) AND trim(machine) = trim(?)
                  AND annule_le = ? AND operation_code IN ('90', '89')
                ORDER BY CASE operation_code WHEN '90' THEN 0 ELSE 1 END, date_operation DESC, id DESC
                LIMIT 1""",
            (row.get("no_dossier") or "", row.get("machine") or "", annule_le),
        ).fetchone()
        if trace:
            row = dict(trace)
    out["trace_id"] = int(row["id"])
    out["trace_deja_fin"] = str(row.get("operation_code") or "").strip() != CODE_ANNULATION
    ref = (row.get("no_dossier") or "").strip()
    if not ref:
        out["raison"] = "Annulation sans dossier."
        return out
    data = _data_trace(row)
    origine = data.get("converti_depuis") if isinstance(data.get("converti_depuis"), dict) else None
    ids = [int(i) for i in (data.get("saisies_annulees") or []) if str(i).isdigit() or isinstance(i, int)]
    # Toutes les saisies marquées par la même annulation, même absentes de la
    # liste de la trace : c'est la date d'annulation qui fait foi.
    if (row.get("annule_le") or "").strip():
        for r in conn.execute(
            """SELECT id FROM production_data
                WHERE trim(no_dossier) = trim(?) AND trim(machine) = trim(?)
                  AND annule_le = ? AND id <> ?""",
            (ref, row.get("machine") or "", row["annule_le"], row["id"]),
        ).fetchall():
            if int(r["id"]) not in ids:
                ids.append(int(r["id"]))
    if out["trace_deja_fin"] and not ids and not (row.get("annule_le") or "").strip():
        out["raison"] = "Cette saisie ne porte aucune annulation."
        return out
    out.update({
        "no_dossier": ref, "machine": (row.get("machine") or "").strip(),
        "date": row.get("date_operation"), "motif": row.get("annule_motif") or data.get("motif"),
        "conversion": origine is not None, "nb_saisies": len(ids) + 1,
        "fin_dossier": (origine or {}).get("fin_dossier") if origine is not None
        else (row.get("fin_dossier") if out["trace_deja_fin"] else None),
        "quantite_traitee": (origine or {}).get("quantite_traitee"),
        "ids_cycle": ids, "origine": origine, "row": row,
    })
    mac = conn.execute(
        """SELECT id FROM machines
            WHERE trim(nom) = trim(?) OR (trim(COALESCE(code,'')) <> '' AND trim(code) = trim(?))
            ORDER BY id LIMIT 1""",
        (out["machine"], out["machine"]),
    ).fetchone()
    out["machine_id"] = int(mac["id"]) if mac else None
    pa = (origine or {}).get("planning_avant") or None
    pe = None
    if pa and pa.get("id"):
        pe = conn.execute("SELECT id, reference, statut FROM planning_entries WHERE id = ?",
                          (pa["id"],)).fetchone()
    if pe is None and row.get("planning_entry_id"):
        pe = conn.execute("SELECT id, reference, statut FROM planning_entries WHERE id = ?",
                          (row["planning_entry_id"],)).fetchone()
    if pe is None and out["machine_id"] is not None:
        pe = conn.execute(
            """SELECT id, reference, statut FROM planning_entries
                WHERE machine_id = ? AND (trim(reference) = ? OR trim(COALESCE(numero_of,'')) = ?)
                ORDER BY CASE WHEN annule_le IS NOT NULL THEN 0 ELSE 1 END, position DESC LIMIT 1""",
            (out["machine_id"], ref, ref),
        ).fetchone()
    out["planning"] = dict(pe) if pe else None
    nid = (origine or {}).get("nouveau_creneau_id")
    if nid:
        nc = conn.execute("SELECT id, reference, statut FROM planning_entries WHERE id = ?", (nid,)).fetchone()
        out["nouveau_creneau"] = dict(nc) if nc else None
    out["retablissable"] = True
    return out


def _dossier_en_production_apres(conn, ref: str, machine: str, date_iso: str, row_id: int) -> Optional[str]:
    """Le dossier tourne-t-il encore sur la machine ?

    Oui si la DERNIÈRE saisie de la machine postérieure à la trace (hors
    pointage) porte sur ce dossier et n'est pas une fin (89) ni une
    annulation (90). Renvoie alors la date de la première saisie du dossier
    après la trace. Une fin « à reprendre » suivie d'un redémarrage (cas du
    M.718/3 cartons, 10/09/2026) reste donc bien « en cours ».
    """
    ph = ",".join("?" * len(CODES_HORS_CYCLE))
    der = conn.execute(
        f"""SELECT no_dossier, operation_code FROM production_data
             WHERE trim(machine) = trim(?) AND operation_code NOT IN ({ph})
               AND (date_operation > ? OR (date_operation = ? AND id > ?))
             ORDER BY date_operation DESC, id DESC LIMIT 1""",
        (machine, *CODES_HORS_CYCLE, date_iso, date_iso, row_id),
    ).fetchone()
    if not der or (der["no_dossier"] or "").strip() != ref:
        return None
    if str(der["operation_code"] or "").strip() in ("89", "90"):
        return None
    r = conn.execute(
        f"""SELECT MIN(date_operation) AS d FROM production_data
             WHERE trim(no_dossier) = ? AND trim(machine) = trim(?)
               AND operation_code NOT IN ({ph})
               AND (date_operation > ? OR (date_operation = ? AND id > ?))""",
        (ref, machine, *CODES_HORS_CYCLE, date_iso, date_iso, row_id),
    ).fetchone()
    return r["d"] if r and r["d"] else None


def retablir(conn, row_id: int, fin_dossier: Optional[bool], auteur: str, auteur_email: str) -> dict:
    """Annule l'annulation : la trace 90 redevient une fin de production."""
    ctx = contexte_retablir(conn, row_id)
    if not ctx["retablissable"]:
        raise ValueError(ctx["raison"] or "Rétablissement impossible.")
    row_id = ctx["trace_id"]
    now_iso = datetime.now().isoformat()
    row, origine, ref = ctx["row"], ctx["origine"], ctx["no_dossier"]
    data = _data_trace(row)
    cols_pd = _colonnes(conn, "production_data")

    if origine is not None:
        cloture = origine.get("fin_dossier")
        cloture = int(cloture) if cloture not in (None, "") else None
    elif fin_dossier is None and ctx["trace_deja_fin"] and ctx["row"].get("fin_dossier") is not None:
        cloture = int(ctx["row"]["fin_dossier"])
    else:
        if fin_dossier is None:
            raise ValueError("Préciser si le dossier était terminé ou à reprendre.")
        cloture = 1 if fin_dossier else 0

    # 1. Le cycle perd sa marque d'annulation (et `est_annule` des bases
    #    antérieures au 07/09/2026).
    motif = ctx["motif"]
    if ctx["ids_cycle"]:
        ph = ",".join("?" * len(ctx["ids_cycle"]))
        conn.execute(
            f"""UPDATE production_data
                   SET annule_le = NULL, annule_par = NULL, annule_motif = NULL, est_annule = 0
                 WHERE id IN ({ph})""",
            tuple(ctx["ids_cycle"]),
        )

    # 2. La trace redevient la fin de production.
    cl = classify_operation("89 - Fin de production")
    if origine is not None:
        libelle = origine.get("operation") or "89 - Fin de production"
        cl = classify_operation(libelle)
        m_fin = origine.get("metrage_total_fin", row.get("metrage_total_fin"))
        valeurs = (
            libelle, "89", cl["severity"], cl["category"],
            origine.get("quantite_traitee") or 0,
            origine.get("metrage_prevu"),
            origine.get("metrage_reel", m_fin),
            origine.get("metrage_total_debut"),
            m_fin,
            origine.get("commentaire"),
            json.dumps(origine.get("data") or {}, default=str),
            origine.get("modifie_par"), origine.get("modifie_le"), origine.get("modifie_note"),
        )
    elif ctx["trace_deja_fin"]:
        # Déjà remise à la main en fin de production : on garde ce qui a été
        # saisi, on retire seulement les marques d'annulation.
        valeurs = None
    else:
        m_fin = row.get("metrage_total_fin") if row.get("metrage_total_fin") is not None else row.get("metrage_reel")
        historique = dict(data)
        historique["annulation_retiree"] = {"le": now_iso, "par": auteur_email}
        commentaire = (row.get("commentaire") or "")
        if commentaire.startswith("Dossier annulé — "):
            commentaire = None
        valeurs = (
            "89 - Fin de production", "89", cl["severity"], cl["category"],
            0, None, m_fin, None, m_fin, commentaire,
            json.dumps(historique, default=str),
            auteur_email, now_iso, "Annulation de dossier retirée",
        )
    if valeurs is not None:
        conn.execute(
            """UPDATE production_data
                  SET operation = ?, operation_code = ?, operation_severity = ?, operation_category = ?,
                      quantite_traitee = ?, metrage_prevu = ?, metrage_reel = ?,
                      metrage_total_debut = ?, metrage_total_fin = ?,
                      commentaire = ?, data = ?,
                      modifie_par = ?, modifie_le = ?, modifie_note = ?,
                      est_annule = 0, annule_le = NULL, annule_par = NULL, annule_motif = NULL
                WHERE id = ?""",
            (*valeurs, row_id),
        )
    else:
        conn.execute(
            """UPDATE production_data
                  SET est_annule = 0, annule_le = NULL, annule_par = NULL, annule_motif = NULL,
                      modifie_par = ?, modifie_le = ?
                WHERE id = ?""",
            (auteur_email, now_iso, row_id),
        )
    if "fin_dossier" in cols_pd:
        conn.execute("UPDATE production_data SET fin_dossier = ? WHERE id = ?", (cloture, row_id))

    # 3. Planning.
    planning_action = None
    nc = ctx.get("nouveau_creneau")
    if nc and nc.get("statut") == "attente":
        # Second créneau créé par la conversion et jamais démarré : il n'a plus
        # lieu d'être.
        pos = conn.execute("SELECT machine_id, position FROM planning_entries WHERE id = ?",
                           (nc["id"],)).fetchone()
        conn.execute("DELETE FROM planning_entries WHERE id = ?", (nc["id"],))
        if pos:
            conn.execute(
                "UPDATE planning_entries SET position = position - 1 WHERE machine_id = ? AND position > ?",
                (pos["machine_id"], pos["position"]),
            )
    pe = ctx["planning"]
    pa = (origine or {}).get("planning_avant")
    if pe:
        pe_id = int(pe["id"])
        en_prod = _dossier_en_production_apres(conn, ref, ctx["machine"], ctx["date"], row_id)
        if en_prod:
            # La machine tourne encore dessus : le dossier est en cours, quel
            # que soit l'état noté avant l'erreur.
            debut = conn.execute(
                """SELECT MIN(date_operation) AS d FROM production_data
                    WHERE trim(no_dossier) = ? AND trim(machine) = trim(?) AND operation_code = '01'
                      AND COALESCE(est_annule, 0) = 0""",
                (ref, ctx["machine"]),
            ).fetchone()
            start = (debut["d"] if debut and debut["d"] else en_prod)
            end = None
            try:
                from app.routers.planning import _planned_end_iso_for_machine
                d = conn.execute("SELECT duree_heures FROM planning_entries WHERE id = ?", (pe_id,)).fetchone()
                end = _planned_end_iso_for_machine(conn, ctx["machine_id"], start, float(d["duree_heures"] or 0))
            except Exception:
                end = (pa or {}).get("planned_end")
            conn.execute(
                """UPDATE planning_entries SET statut = 'en_cours', statut_force = 1,
                          statut_reel = 'reellement_en_saisie', planned_start = ?,
                          planned_end = COALESCE(?, planned_end), updated_at = ?
                    WHERE id = ?""",
                (start, end, now_iso, pe_id),
            )
            # Un seul dossier en cours par machine.
            conn.execute(
                """UPDATE planning_entries SET statut = 'termine', statut_force = 1, updated_at = ?
                    WHERE machine_id = ? AND statut = 'en_cours' AND id <> ?""",
                (now_iso, ctx["machine_id"], pe_id),
            )
            planning_action = "en_cours"
        elif pa:
            sets = [c for c in _COLONNES_PLANNING_RETABLIES if c in pa and c != "position"]
            conn.execute(
                f"UPDATE planning_entries SET {', '.join(c + ' = ?' for c in sets)}, updated_at = ? WHERE id = ?",
                (*[pa[c] for c in sets], now_iso, pe_id),
            )
            planning_action = "retabli"
        else:
            if cloture == 1:
                conn.execute(
                    """UPDATE planning_entries SET statut = 'termine', statut_force = 1,
                              statut_reel = 'reellement_termine', planned_end = ?, updated_at = ?
                        WHERE id = ?""",
                    (ctx["date"], now_iso, pe_id),
                )
                planning_action = "termine"
            planning_action = planning_action or "inchange"
        # Retire la marque d'annulation posée par cette annulation (déjà
        # remise à son état d'avant quand l'instantané a été rétabli).
        if planning_action != "retabli":
            conn.execute(
                """UPDATE planning_entries
                      SET annule_count = MAX(COALESCE(annule_count, 0) - 1, 0),
                          annule_motif = CASE WHEN COALESCE(annule_count, 0) <= 1 THEN NULL ELSE annule_motif END,
                          annule_par   = CASE WHEN COALESCE(annule_count, 0) <= 1 THEN NULL ELSE annule_par END,
                          annule_le    = CASE WHEN COALESCE(annule_count, 0) <= 1 THEN NULL ELSE annule_le END
                    WHERE id = ?""",
                (pe_id,),
            )
    conn.commit()

    if ctx["machine_id"] is not None:
        try:
            from app.routers.planning import _invalidate_attente_plans
            _invalidate_attente_plans(conn, ctx["machine_id"])
            conn.commit()
        except Exception:
            pass

    # 4. Série : elle n'existe que pour un dossier clôturé.
    serie = None
    try:
        existait = (origine or {}).get("serie_existait")
        if cloture == 1:
            from app.services.produit_memoire import materialiser_serie
            materialiser_serie(conn, ref, cloture_par=auteur)
            serie = "rematerialisee"
        elif existait is not True:
            # Dossier non clôturé : la série a été créée par l'annulation
            # (ou par une conversion antérieure au 10/09 qui en créait une).
            conn.execute("DELETE FROM produit_series WHERE no_dossier = ?", (ref,))
            serie = "supprimee"
        conn.commit()
    except Exception:
        pass

    return {"no_dossier": ref, "machine": ctx["machine"], "planning": planning_action,
            "fin_dossier": cloture, "serie": serie,
            "saisies_retablies": len(ctx["ids_cycle"])}


def trace_du_creneau(conn, entry_id: int) -> Optional[int]:
    """Saisie d'annulation (90) qui a marqué ce créneau du planning.

    Par ordre de fiabilité : la trace rattachée au créneau et datée de la même
    annulation ; la trace rattachée la plus récente ; à défaut de lien (saisies
    antérieures au 10/09/2026), la trace de même référence sur la machine et de
    même date d'annulation, puis la plus récente.
    """
    pe = conn.execute(
        """SELECT pe.id, pe.reference, pe.numero_of, pe.annule_le, m.nom, m.code
             FROM planning_entries pe JOIN machines m ON m.id = pe.machine_id
            WHERE pe.id = ?""", (entry_id,)).fetchone()
    if not pe:
        return None
    lien = "planning_entry_id" in _colonnes(conn, "production_data")
    annule_le = (pe["annule_le"] or "").strip()
    refs = [x for x in {(pe["reference"] or "").strip(), (pe["numero_of"] or "").strip()} if x]
    macs = [x for x in {(pe["nom"] or "").strip(), (pe["code"] or "").strip()} if x]
    essais = []
    if lien:
        essais.append(("planning_entry_id = ? AND annule_le = ?", [entry_id, annule_le]))
        essais.append(("planning_entry_id = ?", [entry_id]))
    if refs and macs:
        cond = (f"trim(no_dossier) IN ({','.join('?' * len(refs))}) "
                f"AND trim(machine) IN ({','.join('?' * len(macs))})")
        if lien:
            cond += " AND planning_entry_id IS NULL"
        essais.append((cond + " AND annule_le = ?", refs + macs + [annule_le]))
        essais.append((cond, refs + macs))
    for cond, params in essais:
        r = conn.execute(
            f"""SELECT id FROM production_data
                 WHERE operation_code = '90' AND {cond}
                 ORDER BY date_operation DESC, id DESC LIMIT 1""",
            params,
        ).fetchone()
        if r:
            return int(r["id"])
    return None


def retirer_marque_planning(conn, entry_id: int) -> None:
    """Aucune saisie d'annulation retrouvée : on retire la marque du créneau seul."""
    conn.execute(
        """UPDATE planning_entries
              SET annule_count = MAX(COALESCE(annule_count, 0) - 1, 0),
                  annule_motif = CASE WHEN COALESCE(annule_count, 0) <= 1 THEN NULL ELSE annule_motif END,
                  annule_par   = CASE WHEN COALESCE(annule_count, 0) <= 1 THEN NULL ELSE annule_par END,
                  annule_le    = CASE WHEN COALESCE(annule_count, 0) <= 1 THEN NULL ELSE annule_le END,
                  updated_at   = ?
            WHERE id = ?""",
        (datetime.now().isoformat(), entry_id),
    )
    conn.commit()
