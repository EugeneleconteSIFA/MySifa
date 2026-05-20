"""MySifa — Données pour l'agent IA (lecture + exécution d'actions confirmées)."""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from typing import Any

from app.services.ai_context import ANOMALY_ROLES, get_user_scope


def fetch_context_for_role(conn, user: dict) -> str:
    """Snapshot des données pertinentes selon le rôle — injecté dans le system prompt."""
    role = user.get("role", "")
    scope = get_user_scope(role)
    parts: list[str] = []

    if "production" in scope or "planning" in scope:
        parts.append(_production_today(conn))
        parts.append(_planning_status(conn))

    if "stock" in scope:
        parts.append(_stock_snapshot(conn))

    if "expe" in scope:
        parts.append(_expe_upcoming(conn))

    if "rh" in scope:
        parts.append(_rh_absences(conn))

    if role in ANOMALY_ROLES:
        anomalies = fetch_anomalies(conn)
        if anomalies:
            parts.append(anomalies)

    return "\n\n".join(p for p in parts if p)


def fetch_anomalies(conn) -> str:
    """Détection d'anomalies — string vide si aucune."""
    sections: list[str] = []

    cutoff_48h = (datetime.now() - timedelta(hours=48)).isoformat()
    stale = conn.execute(
        """
        SELECT pe.id,
               COALESCE(NULLIF(TRIM(pe.numero_of), ''), pe.reference) AS dossier,
               pe.client, m.nom AS machine, pe.updated_at
        FROM planning_entries pe
        JOIN machines m ON m.id = pe.machine_id
        WHERE pe.statut = 'en_cours'
          AND datetime(COALESCE(pe.updated_at, pe.created_at)) < datetime(?)
          AND NOT EXISTS (
              SELECT 1 FROM production_data pd
              WHERE datetime(pd.date_operation) >= datetime(?)
                AND (
                  TRIM(pd.no_dossier) = TRIM(pe.reference)
                  OR (TRIM(COALESCE(pe.numero_of, '')) != ''
                      AND TRIM(pd.no_dossier) = TRIM(pe.numero_of))
                )
          )
        ORDER BY pe.updated_at ASC
        LIMIT 15
        """,
        (cutoff_48h, cutoff_48h),
    ).fetchall()
    if stale:
        lines = ["Anomalies — dossiers en cours sans saisie depuis 48h :"]
        for r in stale:
            lines.append(
                f"  - #{r['id']} {r['dossier']} · {r['client']} ({r['machine']})"
            )
        sections.append("\n".join(lines))

    today = date.today()
    if today.weekday() < 5:
        idle = conn.execute(
            """
            SELECT m.nom AS machine
            FROM machines m
            WHERE COALESCE(m.actif, 1) = 1
              AND NOT EXISTS (
                  SELECT 1 FROM production_data pd
                  WHERE date(pd.date_operation) = date('now', 'localtime')
                    AND (
                      TRIM(pd.machine) = TRIM(m.nom)
                      OR (TRIM(COALESCE(m.code, '')) != ''
                          AND TRIM(pd.machine) = TRIM(m.code))
                    )
              )
            ORDER BY m.nom
            """
        ).fetchall()
        if idle:
            names = ", ".join(r["machine"] for r in idle)
            sections.append(
                f"Anomalies — machines sans saisie aujourd'hui ({today.isoformat()}) : {names}"
            )

    since_30 = (date.today() - timedelta(days=30)).isoformat()
    rupture = conn.execute(
        """
        SELECT p.reference, p.designation
        FROM produits p
        WHERE EXISTS (
            SELECT 1 FROM mouvements_stock m
            WHERE m.produit_id = p.id
              AND date(m.created_at) >= date(?)
        )
        GROUP BY p.id
        HAVING COALESCE((
            SELECT SUM(s.quantite) FROM stock_emplacements s WHERE s.produit_id = p.id
        ), 0) = 0
        ORDER BY p.reference
        LIMIT 15
        """,
        (since_30,),
    ).fetchall()
    if rupture:
        lines = ["Anomalies — rupture de stock (mouvement < 30j, quantité 0) :"]
        for r in rupture:
            lines.append(f"  - {r['reference']} — {r['designation']}")
        sections.append("\n".join(lines))

    overdue = conn.execute(
        """
        SELECT client, transporteur, date_enlevement
        FROM expe_departs
        WHERE statut = 'en_attente'
          AND date(date_enlevement) < date('now', 'localtime')
        ORDER BY date_enlevement ASC
        LIMIT 10
        """
    ).fetchall()
    if overdue:
        lines = ["Anomalies — expéditions en attente, date dépassée :"]
        for r in overdue:
            dt = str(r["date_enlevement"] or "")[:10]
            lines.append(f"  - {dt} · {r['client']} · {r['transporteur']}")
        sections.append("\n".join(lines))

    if not sections:
        return ""
    return "\n\n".join(sections)


def _expe_upcoming_days(conn, days: int) -> str:
    today = date.today().isoformat()
    end = (date.today() + timedelta(days=days)).isoformat()
    rows = conn.execute(
        """
        SELECT client, transporteur, date_enlevement, statut
        FROM expe_departs
        WHERE statut IN ('en_attente', 'valide')
          AND date(date_enlevement) BETWEEN ? AND ?
        ORDER BY date_enlevement ASC
        LIMIT 8
        """,
        (today, end),
    ).fetchall()
    if not rows:
        return f"Expéditions : aucun départ sur {days}j."
    lines = [f"Expéditions ({days}j) :"]
    for r in rows:
        dt = str(r["date_enlevement"] or "")[:10]
        lines.append(f"  - {dt} · {r['client']} · {r['transporteur']} [{r['statut']}]")
    return "\n".join(lines)


def _rh_absences_today(conn) -> str:
    today = date.today().isoformat()
    rows = conn.execute(
        """
        SELECT u.nom, c.type_conge, c.statut
        FROM rh_conges c
        JOIN users u ON u.id = c.user_id
        WHERE c.statut IN ('pose', 'valide')
          AND date(c.date_debut) <= ?
          AND date(c.date_fin) >= ?
        ORDER BY u.nom
        """,
        (today, today),
    ).fetchall()
    if not rows:
        return f"RH aujourd'hui ({today}) : aucune absence."
    lines = [f"RH aujourd'hui ({today}) :"]
    for r in rows:
        lines.append(f"  - {r['nom']} · {r['type_conge']} [{r['statut']}]")
    return "\n".join(lines)


def build_daily_brief(conn) -> dict[str, str]:
    """Résumé JSON de la journée (brief quotidien)."""
    today = date.today().isoformat()
    return {
        "date": today,
        "production": _production_today(conn),
        "anomalies": fetch_anomalies(conn) or "Aucune anomalie détectée.",
        "expe": _expe_upcoming_days(conn, 2),
        "rh": _rh_absences_today(conn),
    }


def _production_today(conn) -> str:
    today = date.today().isoformat()
    rows = conn.execute(
        """
        SELECT COALESCE(NULLIF(TRIM(machine), ''), '(sans machine)') AS machine,
               COUNT(*) AS nb_saisies
        FROM production_data
        WHERE date(date_operation) = ?
        GROUP BY TRIM(COALESCE(machine, ''))
        ORDER BY machine
        """,
        (today,),
    ).fetchall()
    if not rows:
        return f"Production aujourd'hui ({today}) : aucune saisie."
    lines = [f"Production aujourd'hui ({today}) :"]
    for r in rows:
        lines.append(f"  - {r['machine']} : {r['nb_saisies']} saisies")
    return "\n".join(lines)


def _planning_status(conn) -> str:
    rows = conn.execute(
        """
        SELECT m.nom AS machine,
               SUM(CASE WHEN pe.statut = 'en_cours' THEN 1 ELSE 0 END) AS en_cours,
               SUM(CASE WHEN pe.statut = 'attente' THEN 1 ELSE 0 END) AS en_attente,
               SUM(CASE WHEN pe.statut = 'termine' THEN 1 ELSE 0 END) AS termines
        FROM planning_entries pe
        JOIN machines m ON m.id = pe.machine_id
        GROUP BY m.id
        ORDER BY m.nom
        """
    ).fetchall()
    if not rows:
        return "Planning : aucune entrée."
    lines = ["Planning machines :"]
    for r in rows:
        lines.append(
            f"  - {r['machine']} : {r['en_cours']} en cours, "
            f"{r['en_attente']} en attente, {r['termines']} terminés"
        )
    return "\n".join(lines)


def _stock_snapshot(conn) -> str:
    rows = conn.execute(
        """
        SELECT p.reference, p.designation, p.unite,
               SUM(s.quantite) AS total
        FROM stock_emplacements s
        JOIN produits p ON p.id = s.produit_id
        WHERE s.quantite > 0
        GROUP BY p.id
        ORDER BY total ASC
        LIMIT 5
        """
    ).fetchall()
    if not rows:
        return "Stock : aucun article en stock."
    lines = ["Stock (5 articles les plus bas) :"]
    for r in rows:
        lines.append(f"  - {r['reference']} — {r['designation']} : {r['total']} {r['unite']}")
    return "\n".join(lines)


def _expe_upcoming(conn) -> str:
    today = date.today().isoformat()
    in_7 = (date.today() + timedelta(days=7)).isoformat()
    rows = conn.execute(
        """
        SELECT client, transporteur, date_enlevement, statut
        FROM expe_departs
        WHERE statut IN ('en_attente', 'valide')
          AND date(date_enlevement) BETWEEN ? AND ?
        ORDER BY date_enlevement ASC
        LIMIT 5
        """,
        (today, in_7),
    ).fetchall()
    if not rows:
        return "Expéditions : aucun départ dans les 7 prochains jours."
    lines = ["Expéditions à venir (7j) :"]
    for r in rows:
        dt = str(r["date_enlevement"] or "")[:10]
        lines.append(f"  - {dt} · {r['client']} · {r['transporteur']} [{r['statut']}]")
    return "\n".join(lines)


def _rh_absences(conn) -> str:
    today = date.today().isoformat()
    in_14 = (date.today() + timedelta(days=14)).isoformat()
    rows = conn.execute(
        """
        SELECT u.nom, c.type_conge, c.date_debut, c.date_fin, c.statut
        FROM rh_conges c
        JOIN users u ON u.id = c.user_id
        WHERE c.statut IN ('pose', 'valide')
          AND date(c.date_fin) >= ?
          AND date(c.date_debut) <= ?
        ORDER BY c.date_debut ASC
        LIMIT 8
        """,
        (today, in_14),
    ).fetchall()
    if not rows:
        return "RH : aucune absence dans les 14 prochains jours."
    lines = ["Absences / congés (14j) :"]
    for r in rows:
        lines.append(
            f"  - {r['nom']} · {r['type_conge']} du {str(r['date_debut'])[:10]} "
            f"au {str(r['date_fin'])[:10]} [{r['statut']}]"
        )
    return "\n".join(lines)


# ─── Outils appelés par l'agent (lecture seule) ───────────────────────────────


def tool_production_detail(conn, inp: dict) -> str:
    jours = max(1, min(int(inp.get("jours") or 7), 90))
    machine_nom = (inp.get("machine_nom") or "").strip()
    since = (date.today() - timedelta(days=jours - 1)).isoformat()

    if machine_nom:
        rows = conn.execute(
            """
            SELECT date(date_operation) AS jour,
                   COUNT(*) AS nb_saisies,
                   COUNT(DISTINCT NULLIF(TRIM(no_dossier), '')) AS dossiers
            FROM production_data
            WHERE date(date_operation) >= ?
              AND (
                TRIM(machine) = TRIM(?)
                OR TRIM(machine) LIKE '%' || TRIM(?) || '%'
              )
            GROUP BY date(date_operation)
            ORDER BY jour DESC
            """,
            (since, machine_nom, machine_nom),
        ).fetchall()
        if not rows:
            return f"Production — {machine_nom} : aucune saisie sur {jours} j."
        lines = [f"Production — {machine_nom} ({jours} derniers jours) :"]
        for r in rows:
            lines.append(
                f"  - {r['jour']} : {r['nb_saisies']} saisies, {r['dossiers']} dossier(s)"
            )
        return "\n".join(lines)

    rows = conn.execute(
        """
        SELECT COALESCE(NULLIF(TRIM(machine), ''), '(sans machine)') AS machine,
               COUNT(*) AS nb_saisies
        FROM production_data
        WHERE date(date_operation) >= ?
        GROUP BY TRIM(COALESCE(machine, ''))
        ORDER BY nb_saisies DESC, machine
        LIMIT 20
        """,
        (since,),
    ).fetchall()
    if not rows:
        return f"Production ({jours}j) : aucune saisie."
    lines = [f"Production par machine ({jours} derniers jours) :"]
    for r in rows:
        lines.append(f"  - {r['machine']} : {r['nb_saisies']} saisies")
    return "\n".join(lines)


def tool_planning_detail(conn, inp: dict) -> str:
    limit = max(1, min(int(inp.get("limit") or 10), 30))
    machine_nom = (inp.get("machine_nom") or "").strip()
    client = (inp.get("client") or "").strip()
    statut = (inp.get("statut") or "").strip()

    where = ["1=1"]
    params: list = []
    if machine_nom:
        where.append("(TRIM(m.nom) = TRIM(?) OR TRIM(m.nom) LIKE '%' || TRIM(?) || '%')")
        params.extend([machine_nom, machine_nom])
    if client:
        where.append("pe.client LIKE ? COLLATE NOCASE")
        params.append(f"%{client}%")
    if statut:
        where.append("pe.statut = ?")
        params.append(statut)

    rows = conn.execute(
        f"""
        SELECT m.nom AS machine, pe.position, pe.statut,
               COALESCE(NULLIF(TRIM(pe.numero_of), ''), pe.reference) AS dossier,
               pe.client, pe.duree_heures, pe.planned_start, pe.planned_end
        FROM planning_entries pe
        JOIN machines m ON m.id = pe.machine_id
        WHERE {' AND '.join(where)}
        ORDER BY m.nom, pe.position
        LIMIT ?
        """,
        (*params, limit),
    ).fetchall()
    if not rows:
        filt = []
        if machine_nom:
            filt.append(f"machine={machine_nom}")
        if statut:
            filt.append(f"statut={statut}")
        suffix = f" ({', '.join(filt)})" if filt else ""
        return f"Planning : aucun dossier{suffix}."
    lines = [f"Planning ({len(rows)} dossier(s)) :"]
    for r in rows:
        dates = ""
        if r["planned_start"] or r["planned_end"]:
            dates = (
                f" · {_fmt_planning_dt(r['planned_start'])}"
                f" → {_fmt_planning_dt(r['planned_end'])}"
            )
        lines.append(
            f"  - {r['machine']} #{r['position']} · {r['dossier']} · {r['client']} "
            f"[{r['statut']}, {r['duree_heures']}h]{dates}"
        )
    return "\n".join(lines)


def _fmt_planning_dt(iso: str | None) -> str:
    if not iso:
        return "—"
    s = str(iso).strip()
    if len(s) >= 16:
        return s[:16].replace("T", " ")
    return s[:10]


def _split_planning_entries(entries_list: list[dict]) -> list[dict]:
    """Même ordre que la timeline UI : dossiers planifiés puis « à placer »."""
    main_entries: list[dict] = []
    aplacer_entries: list[dict] = []
    for e in entries_list:
        st = (e.get("statut") or "attente").strip()
        ap = int(e.get("a_placer") or 0)
        if st == "attente" and ap == 1:
            aplacer_entries.append(e)
        else:
            main_entries.append(e)
    return main_entries + aplacer_entries


def tool_planning_client_schedule(conn, inp: dict) -> str:
    """Créneaux estimés (début/fin) pour les dossiers d'un client — lecture seule."""
    from app.routers.planning import (
        _compute_timeline_slots,
        _load_planning_calendar_maps,
    )

    client_q = (inp.get("client") or "").strip()
    if not client_q:
        return "Indiquez un nom de client (ex. SNV)."
    machine_nom = (inp.get("machine_nom") or "").strip()
    cq = client_q.lower()

    params: list[Any] = [f"%{client_q}%"]
    machine_sql = ""
    if machine_nom:
        machine_sql = (
            " AND (TRIM(m.nom) = TRIM(?) OR TRIM(m.nom) LIKE '%' || TRIM(?) || '%')"
        )
        params.extend([machine_nom, machine_nom])

    machines = conn.execute(
        f"""
        SELECT DISTINCT m.id, m.nom
        FROM planning_entries pe
        JOIN machines m ON m.id = pe.machine_id
        WHERE pe.client LIKE ? COLLATE NOCASE
          AND pe.statut IN ('attente', 'en_cours')
          {machine_sql}
        ORDER BY m.nom
        """,
        params,
    ).fetchall()

    if not machines:
        termines = conn.execute(
            f"""
            SELECT m.nom, pe.position,
                   COALESCE(NULLIF(TRIM(pe.numero_of), ''), pe.reference) AS dossier,
                   pe.statut, pe.planned_end
            FROM planning_entries pe
            JOIN machines m ON m.id = pe.machine_id
            WHERE pe.client LIKE ? COLLATE NOCASE
              AND pe.statut = 'termine'
              {machine_sql}
            ORDER BY pe.planned_end DESC
            LIMIT 5
            """,
            params,
        ).fetchall()
        if termines:
            lines = [
                f"Aucun dossier en attente/en cours pour « {client_q} ».",
                "Derniers dossiers terminés :",
            ]
            for r in termines:
                lines.append(
                    f"  - {r['nom']} #{r['position']} · {r['dossier']} "
                    f"(fin {_fmt_planning_dt(r['planned_end'])})"
                )
            return "\n".join(lines)
        return f"Aucun dossier planning trouvé pour le client « {client_q} »."

    lines = [
        f"Planning client « {client_q} » — dates estimées (heures ouvrées machine, Paris) :"
    ]

    for mrow in machines:
        mid = int(mrow["id"])
        mnom = mrow["nom"]
        machine = conn.execute("SELECT * FROM machines WHERE id=?", (mid,)).fetchone()
        if not machine:
            continue

        configs, off_days, day_worked_map, day_horaires_map = _load_planning_calendar_maps(
            conn, mid
        )
        rows = conn.execute(
            "SELECT * FROM planning_entries WHERE machine_id=? ORDER BY position ASC",
            (mid,),
        ).fetchall()
        entries_list = _split_planning_entries([dict(r) for r in rows])
        by_id = {int(e["id"]): e for e in entries_list}

        slots = _compute_timeline_slots(
            conn,
            mid,
            dict(machine),
            configs,
            off_days,
            day_worked_map,
            day_horaires_map,
            entries_list,
            persist=False,
        )

        client_slots: list[tuple[dict, dict]] = []
        for slot in slots:
            eid = int(slot.get("entry_id") or 0)
            ent = by_id.get(eid, {})
            if cq not in str(ent.get("client") or "").lower():
                continue
            client_slots.append((slot, ent))

        if not client_slots:
            continue

        lines.append(f"\n{mnom} :")

        first_pos = min(int(ent.get("position") or 0) for _, ent in client_slots)
        ahead_h = 0.0
        ahead_n = 0
        for ent in entries_list:
            pos = int(ent.get("position") or 0)
            if pos >= first_pos:
                break
            st = (ent.get("statut") or "").strip()
            if st in ("attente", "en_cours"):
                ahead_h += float(ent.get("duree_heures") or 0)
                ahead_n += 1

        if ahead_n:
            lines.append(
                f"  File d'attente : {ahead_n} dossier(s) avant le premier dossier "
                f"{client_q} (~{ahead_h:.1f}h ouvrées machine au total)."
            )

        for slot, ent in client_slots:
            dossier = (
                (ent.get("numero_of") or "").strip()
                or (ent.get("reference") or "").strip()
                or "?"
            )
            st = slot.get("statut") or ent.get("statut") or "?"
            pos = int(ent.get("position") or 0)
            start = _fmt_planning_dt(slot.get("start"))
            end = _fmt_planning_dt(slot.get("end"))
            duree = float(ent.get("duree_heures") or 0)
            liv = ent.get("date_livraison")
            liv_s = f" · livraison {str(liv)[:10]}" if liv else ""
            if st == "en_cours":
                lines.append(
                    f"  - #{pos} · {dossier} · {st} · en cours depuis {start} "
                    f"(fin estimée {end}, {duree}h){liv_s}"
                )
            elif st == "attente" and start != "—":
                lines.append(
                    f"  - #{pos} · {dossier} · {st} · passage estimé du {start} au {end} "
                    f"({duree}h){liv_s}"
                )
            else:
                lines.append(
                    f"  - #{pos} · {dossier} · {st} · {duree}h{liv_s}"
                )

    if len(lines) == 1:
        return f"Aucun créneau calculable pour « {client_q} »."
    lines.append(
        "\nNote : estimation basée sur la file actuelle et le calendrier machine "
        "(jours ouvrés, horaires). Sous réserve des aléas de production."
    )
    return "\n".join(lines)


def _resolve_dossier_refs_for_traceability(conn, query: str) -> tuple[list[str], list[dict]]:
    """Références planning/OF et no_dossier matières correspondant à la recherche."""
    q = (query or "").strip()
    if not q:
        return [], []

    refs: set[str] = set()
    planning_hits: list[dict] = []
    seen_pe: set[str] = set()

    def _add_pe_row(r) -> None:
        ref = (r["reference"] or "").strip()
        of = (r["numero_of"] or "").strip()
        key = ref or of
        if not key or key in seen_pe:
            return
        seen_pe.add(key)
        if ref:
            refs.add(ref)
        if of:
            refs.add(of)
        planning_hits.append(
            {
                "reference": ref or of,
                "numero_of": of or None,
                "client": (r["client"] or "").strip() or None,
                "statut": (r["statut"] or "").strip() or None,
                "machine": (r["machine_nom"] or "").strip() or None,
            }
        )

    like = f"%{q}%"
    pe_rows = conn.execute(
        """
        SELECT pe.reference, pe.numero_of, pe.client, pe.statut, m.nom AS machine_nom
        FROM planning_entries pe
        LEFT JOIN machines m ON m.id = pe.machine_id
        WHERE TRIM(COALESCE(pe.reference, '')) = TRIM(?)
           OR TRIM(COALESCE(pe.numero_of, '')) = TRIM(?)
           OR pe.reference LIKE ? COLLATE NOCASE
           OR pe.numero_of LIKE ? COLLATE NOCASE
           OR TRIM(COALESCE(pe.reference, '')) LIKE '%' || TRIM(?) || '%' COLLATE NOCASE
           OR TRIM(COALESCE(pe.numero_of, '')) LIKE '%' || TRIM(?) || '%' COLLATE NOCASE
        ORDER BY pe.position ASC
        LIMIT 12
        """,
        (q, q, like, like, q, q),
    ).fetchall()
    for r in pe_rows:
        _add_pe_row(r)

    for chunk in re.findall(r"\d{4,}", q):
        if chunk == q:
            continue
        chunk_like = f"%{chunk}%"
        extra = conn.execute(
            """
            SELECT pe.reference, pe.numero_of, pe.client, pe.statut, m.nom AS machine_nom
            FROM planning_entries pe
            LEFT JOIN machines m ON m.id = pe.machine_id
            WHERE pe.reference LIKE ? COLLATE NOCASE
               OR pe.numero_of LIKE ? COLLATE NOCASE
            ORDER BY pe.position ASC
            LIMIT 8
            """,
            (chunk_like, chunk_like),
        ).fetchall()
        for r in extra:
            _add_pe_row(r)

    m_rows = conn.execute(
        """
        SELECT DISTINCT TRIM(no_dossier) AS nd
        FROM fab_matieres_utilisees
        WHERE no_dossier IS NOT NULL AND TRIM(no_dossier) != ''
          AND (
            TRIM(no_dossier) = TRIM(?)
            OR no_dossier LIKE ? COLLATE NOCASE
            OR TRIM(no_dossier) LIKE '%' || TRIM(?) || '%' COLLATE NOCASE
          )
        """,
        (q, like, q),
    ).fetchall()
    for r in m_rows:
        nd = (r["nd"] or "").strip()
        if nd:
            refs.add(nd)

    return sorted(refs), planning_hits


def tool_traceability_dossier_bobines(conn, inp: dict) -> str:
    """Bobines matière scannées pour un dossier (MyProd > Traçabilité)."""
    query = (
        inp.get("no_dossier")
        or inp.get("query")
        or inp.get("reference")
        or inp.get("dossier")
        or ""
    ).strip()
    if not query:
        return "Indiquez le numéro ou la référence du dossier (ex. 9931595, Reliquat 9931595)."

    refs, planning_hits = _resolve_dossier_refs_for_traceability(conn, query)
    if not refs:
        return (
            f"Traçabilité — aucun dossier fabrication trouvé pour « {query} ». "
            "Vérifiez la référence planning ou le numéro d'OF."
        )

    placeholders = ",".join("?" * len(refs))
    matieres = conn.execute(
        f"""
        SELECT code_barre, machine_nom, operateur, scanned_at, no_dossier
        FROM fab_matieres_utilisees
        WHERE TRIM(no_dossier) IN ({placeholders})
        ORDER BY scanned_at ASC
        """,
        refs,
    ).fetchall()

    lines = [f"Traçabilité bobines — recherche « {query} » :"]

    if planning_hits:
        pe = planning_hits[0]
        dossier_lbl = pe["reference"] or "—"
        extra = []
        if pe.get("client"):
            extra.append(pe["client"])
        if pe.get("machine"):
            extra.append(pe["machine"])
        if pe.get("statut"):
            extra.append(pe["statut"])
        suffix = f" ({', '.join(extra)})" if extra else ""
        lines.append(f"Dossier planning : {dossier_lbl}{suffix}")
        if len(planning_hits) > 1:
            others = ", ".join(
                (p["reference"] or "?") for p in planning_hits[1:4]
            )
            lines.append(f"Autres correspondances planning : {others}")

    if not matieres:
        lines.append(
            "Aucune bobine matière scannée enregistrée pour ce dossier "
            "(MyProd > Traçabilité)."
        )
        return "\n".join(lines)

    lines.append(f"{len(matieres)} bobine(s) scannée(s) :")
    for m in matieres:
        code = (m["code_barre"] or "").strip() or "—"
        mach = (m["machine_nom"] or "").strip() or "—"
        op = (m["operateur"] or "").strip() or "—"
        dt = str(m["scanned_at"] or "")[:16].replace("T", " ")
        nd = (m["no_dossier"] or "").strip()
        nd_s = f" · dossier {nd}" if nd and len(refs) > 1 else ""
        lines.append(f"  - {code} · {mach} · {op} · {dt or '—'}{nd_s}")

    return "\n".join(lines)


def tool_stock_search(conn, inp: dict) -> str:
    query = (inp.get("query") or "").strip()
    if not query:
        return "Indiquez une référence ou une désignation à chercher."
    like = f"%{query}%"
    rows = conn.execute(
        """
        SELECT p.reference, p.designation, p.unite,
               COALESCE(SUM(s.quantite), 0) AS total
        FROM produits p
        LEFT JOIN stock_emplacements s ON s.produit_id = p.id AND s.quantite > 0
        WHERE p.reference LIKE ? COLLATE NOCASE
           OR p.designation LIKE ? COLLATE NOCASE
        GROUP BY p.id
        ORDER BY p.reference
        LIMIT 10
        """,
        (like, like),
    ).fetchall()
    if not rows:
        return f"Stock : aucun article pour « {query} »."
    lines = [f"Stock — recherche « {query} » ({len(rows)} résultat(s)) :"]
    for r in rows:
        lines.append(f"  - {r['reference']} — {r['designation']} : {r['total']} {r['unite']}")
    return "\n".join(lines)


def tool_expe_detail(conn, inp: dict) -> str:
    jours = max(1, min(int(inp.get("jours") or 14), 60))
    today = date.today().isoformat()
    end = (date.today() + timedelta(days=jours)).isoformat()
    rows = conn.execute(
        """
        SELECT date_enlevement, client, transporteur, statut,
               nb_palette, poids_total_kg
        FROM expe_departs
        WHERE statut IN ('en_attente', 'valide')
          AND date(date_enlevement) BETWEEN ? AND ?
        ORDER BY date_enlevement ASC
        LIMIT 15
        """,
        (today, end),
    ).fetchall()
    if not rows:
        return f"Expéditions : aucun départ sur les {jours} prochains jours."
    lines = [f"Expéditions ({jours}j, {len(rows)} départ(s)) :"]
    for r in rows:
        dt = str(r["date_enlevement"] or "")[:10]
        pal = r["nb_palette"]
        poids = r["poids_total_kg"]
        extra = []
        if pal is not None:
            extra.append(f"{pal} pal.")
        if poids is not None:
            extra.append(f"{poids} kg")
        extra_s = f" · {' · '.join(extra)}" if extra else ""
        lines.append(
            f"  - {dt} · {r['client']} · {r['transporteur']} [{r['statut']}]{extra_s}"
        )
    return "\n".join(lines)


# ─── Actions avec confirmation ────────────────────────────────────────────────


def _confirm_tag(payload: dict) -> str:
    return f"[CONFIRM_ACTION:{json.dumps(payload, ensure_ascii=False)}]"


def tool_planning_close_dossier_prepare(conn, inp: dict) -> str:
    entry_id = int(inp.get("entry_id") or 0)
    if entry_id <= 0:
        return "Identifiant de dossier invalide."
    row = conn.execute(
        """
        SELECT id, reference, client, statut,
               COALESCE(NULLIF(TRIM(numero_of), ''), reference) AS dossier
        FROM planning_entries WHERE id = ?
        """,
        (entry_id,),
    ).fetchone()
    if not row:
        return f"Dossier planning #{entry_id} introuvable."
    if row["statut"] == "termine":
        return f"Le dossier #{row['dossier']} est déjà terminé."
    ref = row["dossier"] or row["reference"]
    client = row["client"] or "—"
    payload = {
        "action": "planning_close_dossier",
        "entry_id": entry_id,
        "reference": ref,
        "client": client,
    }
    return (
        f"Confirmes-tu la clôture du dossier #{ref} — {client} ?\n"
        f"{_confirm_tag(payload)}"
    )


def execute_planning_close_dossier(conn, user: dict, payload: dict) -> str:
    entry_id = int(payload.get("entry_id") or 0)
    row = conn.execute(
        "SELECT id, statut FROM planning_entries WHERE id = ?", (entry_id,)
    ).fetchone()
    if not row:
        return f"Dossier #{entry_id} introuvable."
    if row["statut"] == "termine":
        return f"Dossier #{payload.get('reference', entry_id)} déjà terminé."
    now = datetime.now().isoformat()
    conn.execute(
        """
        UPDATE planning_entries
        SET statut = 'termine',
            statut_reel = 'reellement_termine',
            statut_force = 1,
            updated_at = ?
        WHERE id = ?
        """,
        (now, entry_id),
    )
    conn.commit()
    ref = payload.get("reference") or entry_id
    return f"Dossier #{ref} clôturé."


def tool_stock_adjust_prepare(conn, inp: dict) -> str:
    reference = (inp.get("reference") or "").strip()
    emplacement = (inp.get("emplacement") or "").strip()
    raison = (inp.get("raison") or "").strip()
    try:
        nouvelle_quantite = float(inp.get("nouvelle_quantite"))
    except (TypeError, ValueError):
        return "Quantité invalide."
    if not reference or not emplacement:
        return "Référence et emplacement requis."
    if nouvelle_quantite < 0:
        return "La quantité ne peut pas être négative."
    if not raison:
        return "Une raison est requise pour l'ajustement."

    p = conn.execute(
        "SELECT id, designation FROM produits WHERE reference = ? COLLATE NOCASE",
        (reference,),
    ).fetchone()
    if not p:
        return f"Article « {reference} » introuvable."

    ex = conn.execute(
        "SELECT quantite FROM stock_emplacements WHERE produit_id = ? AND emplacement = ?",
        (p["id"], emplacement),
    ).fetchone()
    qte_avant = float(ex["quantite"]) if ex else 0.0

    payload = {
        "action": "stock_adjust",
        "produit_id": p["id"],
        "reference": reference,
        "designation": p["designation"],
        "emplacement": emplacement,
        "nouvelle_quantite": nouvelle_quantite,
        "quantite_avant": qte_avant,
        "raison": raison,
    }
    return (
        f"Confirmes-tu l'ajustement de {reference} ({p['designation']}) "
        f"à l'emplacement {emplacement} : {qte_avant} → {nouvelle_quantite} ({raison}) ?\n"
        f"{_confirm_tag(payload)}"
    )


def execute_stock_adjust(conn, user: dict, payload: dict) -> str:
    produit_id = int(payload["produit_id"])
    emplacement = payload["emplacement"]
    quantite = float(payload["nouvelle_quantite"])
    raison = payload.get("raison") or "Ajustement agent IA"
    email = str(user.get("email") or "agent-ia")
    nom = str(user.get("nom") or "").strip() or None
    now = datetime.now().isoformat()

    ex = conn.execute(
        "SELECT quantite FROM stock_emplacements WHERE produit_id = ? AND emplacement = ?",
        (produit_id, emplacement),
    ).fetchone()
    qte_avant = float(ex["quantite"]) if ex else 0.0

    conn.execute(
        "UPDATE lots_stock SET quantite_restante = 0 WHERE produit_id = ? AND emplacement = ?",
        (produit_id, emplacement),
    )
    if quantite > 0:
        conn.execute(
            """
            INSERT INTO lots_stock
            (produit_id, emplacement, quantite_initiale, quantite_restante,
             date_entree, note, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                produit_id,
                emplacement,
                quantite,
                quantite,
                now,
                f"Ajustement IA — {raison}",
                email,
                now,
            ),
        )

    if ex:
        conn.execute(
            """
            UPDATE stock_emplacements
            SET quantite = ?, updated_at = ?, updated_by = ?,
                derniere_inventaire = ?, commentaire = ?
            WHERE produit_id = ? AND emplacement = ?
            """,
            (quantite, now, email, now, raison, produit_id, emplacement),
        )
    else:
        conn.execute(
            """
            INSERT INTO stock_emplacements
            (produit_id, emplacement, quantite, updated_at, updated_by,
             derniere_inventaire, commentaire)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (produit_id, emplacement, quantite, now, email, now, raison),
        )

    conn.execute(
        """
        INSERT INTO mouvements_stock
        (produit_id, emplacement, type_mouvement, quantite,
         quantite_avant, quantite_apres, note, created_at, created_by, created_by_name)
        VALUES (?, ?, 'inventaire', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            produit_id,
            emplacement,
            quantite,
            qte_avant,
            quantite,
            f"Ajustement IA — {raison}",
            now,
            email,
            nom,
        ),
    )
    conn.commit()
    ref = payload.get("reference", produit_id)
    return (
        f"Stock ajusté — {ref} / {emplacement} : "
        f"{qte_avant} → {quantite}."
    )


def execute_pending_action(conn, user: dict, payload: dict) -> str:
    action = payload.get("action")
    if action == "planning_close_dossier":
        return execute_planning_close_dossier(conn, user, payload)
    if action == "stock_adjust":
        return execute_stock_adjust(conn, user, payload)
    return "Action inconnue."
