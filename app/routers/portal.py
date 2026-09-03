"""Portail d'accueil — agregats de la page d'accueil.

Deux endpoints en LECTURE SEULE, appeles au chargement du portail :

    GET /api/portal/a-traiter  -> les compteurs « ce qui m'attend »
    GET /api/portal/atelier    -> ce qui tourne sur chaque machine, maintenant

Regle de ce module : **jamais d'erreur**. Le portail est la premiere page que
voit l'utilisateur ; un 403 sur un compteur ne doit pas la casser. Chaque bloc
est isole dans son propre try, et un utilisateur sans acces recoit 0, pas une
exception. C'est le meme parti pris que GET /api/taches/badge.

Aucun chiffre n'est recalcule ici. Les compteurs delegent aux endpoints qui
font deja foi (qualite_badges, rh_coffre_badges, taches_badge) et l'avancement
d'un dossier reprend exactement le calcul en heures ouvrees de
planning.live_refresh_en_cours — sans quoi le portail et le planning
donneraient deux chiffres pour le meme dossier, ce que la regle produit
interdit.

Les imports des autres routeurs sont faits DANS les fonctions : au chargement
du module, main.py n'a pas encore fini d'importer planning/qualite/taches.
"""

import math
from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Request

from database import get_db
from services.auth_service import get_current_user, user_has_app_access

router = APIRouter(tags=["portal"])


def _a_traiter_vide() -> dict:
    return {
        "expe": {"en_attente": 0, "aujourdhui": 0, "en_retard": 0},
        "qualite": {"nc_unread": 0, "audits_unread": 0, "audits_assigned_open": 0, "total": 0},
        "rh_coffre": {"ndf_soumises": 0},
        "taches": {"count": 0, "en_retard": 0},
    }


@router.get("/api/portal/a-traiter")
def portal_a_traiter(request: Request):
    """Compteurs agreges du bloc « A traiter » du portail.

    Chaque bloc est filtre par les acces de l'utilisateur et retombe a 0 en cas
    d'echec : le portail affiche moins de lignes, il n'affiche jamais d'erreur.
    """
    out = _a_traiter_vide()
    try:
        user = get_current_user(request)
    except HTTPException:
        return out

    # ── MyExpe : departs enregistres mais pas encore valides ──────────────
    # statut est le critere (validated_at n'en est que la consequence), et
    # date_enlevement peut porter une heure sur les lignes historiques.
    try:
        if user_has_app_access(user, "expe"):
            today = date.today().isoformat()
            with get_db() as conn:
                row = conn.execute(
                    """SELECT COUNT(*) AS en_attente,
                              SUM(CASE WHEN substr(date_enlevement,1,10) = ? THEN 1 ELSE 0 END) AS aujourdhui,
                              SUM(CASE WHEN substr(date_enlevement,1,10) < ? THEN 1 ELSE 0 END) AS en_retard
                         FROM expe_departs
                        WHERE statut = 'en_attente'""",
                    (today, today),
                ).fetchone()
            if row:
                out["expe"] = {
                    "en_attente": int(row["en_attente"] or 0),
                    "aujourdhui": int(row["aujourdhui"] or 0),
                    "en_retard": int(row["en_retard"] or 0),
                }
    except Exception:
        pass

    # ── MyQualite : NC et audits non lus ──────────────────────────────────
    try:
        from app.routers.qualite import qualite_badges

        d = qualite_badges(request) or {}
        out["qualite"] = {
            "nc_unread": int(d.get("nc_unread") or 0),
            "audits_unread": int(d.get("audits_unread") or 0),
            "audits_assigned_open": int(d.get("audits_assigned_open") or 0),
            "total": int(d.get("total") or 0),
        }
    except Exception:
        pass

    # ── Coffre RH : notes de frais soumises ───────────────────────────────
    try:
        from app.routers.rh_coffre import rh_coffre_badges

        d = rh_coffre_badges(request) or {}
        out["rh_coffre"] = {"ndf_soumises": int(d.get("ndf_soumises") or 0)}
    except Exception:
        pass

    # ── Taches assignees ──────────────────────────────────────────────────
    try:
        from app.routers.taches import taches_badge

        d = taches_badge(request) or {}
        out["taches"] = {
            "count": int(d.get("count") or 0),
            "en_retard": int(d.get("en_retard") or 0),
        }
    except Exception:
        pass

    return out


def _avancement_pct(conn, machine_id: int, mac: dict, no_dossier: str, duree_heures: float):
    """Pourcentage d'avancement du run en cours, en heures OUVREES machine.

    Reprend trait pour trait le calcul de planning.live_refresh_en_cours :
    debut du run depuis les saisies operateur, ecoule mesure sur le calendrier
    de la machine (nuits, dimanches et jours chomes exclus), arrondi au quart
    d'heure superieur. Retourne None des qu'un element manque — mieux vaut pas
    de pourcentage qu'un pourcentage faux.
    """
    if not no_dossier or not duree_heures or duree_heures <= 0:
        return None
    try:
        from app.routers.planning import (
            _TZ_PARIS,
            _hours_for_date_factory,
            _load_planning_calendar_maps,
            _prod_run_start_for_machine,
            _work_hours_between,
        )

        dt_start = _prod_run_start_for_machine(conn, machine_id, mac, no_dossier)
        if not dt_start:
            return None
        now = datetime.now(_TZ_PARIS).replace(tzinfo=None)
        cfgs, off, dw, dh = _load_planning_calendar_maps(conn, machine_id)
        get_hours_for_date = _hours_for_date_factory(mac, cfgs, off, dw, dh)
        elapsed = _work_hours_between(get_hours_for_date, dt_start, now)
        elapsed = math.ceil(elapsed * 4 - 1e-9) / 4
        if elapsed <= 0:
            return None
        return max(0, min(100, int(round(100.0 * elapsed / float(duree_heures)))))
    except Exception:
        return None


@router.get("/api/portal/atelier")
def portal_atelier(request: Request):
    """Etat instantane des machines, pour le bloc « Atelier maintenant ».

    etat vaut :
        prod     — une saisie operateur est ouverte sur la machine (C1 / C2)
        planifie — un dossier est en_cours au planning mais aucune saisie ouverte
        libre    — rien en cours

    La distinction compte : « planifie » sans « prod » signale une machine
    arretee sur un dossier cense tourner, ce qui est precisement ce qu'on veut
    voir depuis son telephone.
    """
    try:
        user = get_current_user(request)
    except HTTPException:
        return {"machines": []}
    if not (user_has_app_access(user, "planning") or user_has_app_access(user, "prod")):
        return {"machines": []}

    machines = []
    try:
        from app.routers.planning import (
            ROLE_FABRICATION,
            fabrication_planning_machine_ids,
            get_active_dossier,
        )

        with get_db() as conn:
            rows = conn.execute(
                """SELECT m.id, m.nom, m.code,
                          pe.id AS entry_id,
                          COALESCE(NULLIF(TRIM(pe.numero_of), ''), pe.reference) AS no_dossier,
                          pe.client, pe.ref_produit, pe.duree_heures
                     FROM machines m
                     LEFT JOIN planning_entries pe
                            ON pe.machine_id = m.id AND pe.statut = 'en_cours'
                    WHERE m.actif = 1
                    ORDER BY m.nom"""
            ).fetchall()

            autorisees = None
            if user.get("role") == ROLE_FABRICATION:
                autorisees = fabrication_planning_machine_ids(conn, user)

            for r in rows:
                mid = int(r["id"])
                if autorisees is not None and mid not in autorisees:
                    continue
                mac_row = conn.execute("SELECT * FROM machines WHERE id=?", (mid,)).fetchone()
                mac = dict(mac_row) if mac_row else {}

                # Saisie operateur ouverte ? (renvoie None hors C1/C2 : ces
                # machines n'ont pas de saisie, l'absence n'y veut rien dire)
                live = None
                try:
                    live = (get_active_dossier(mid, request) or {}).get("dossier")
                except Exception:
                    live = None

                planifie = (r["no_dossier"] or "").strip()
                duree = float(r["duree_heures"] or 0)

                if live:
                    etat = "prod"
                    no_dossier = (live.get("no_dossier") or "").strip()
                    client = (live.get("client") or "").strip() or (r["client"] or "")
                    designation = (live.get("designation") or "").strip()
                elif planifie:
                    etat = "planifie"
                    no_dossier = planifie
                    client = r["client"] or ""
                    designation = r["ref_produit"] or ""
                else:
                    etat = "libre"
                    no_dossier = ""
                    client = ""
                    designation = ""

                pct = None
                if etat == "prod" and no_dossier and no_dossier == planifie:
                    pct = _avancement_pct(conn, mid, mac, no_dossier, duree)

                machines.append({
                    "id": mid,
                    "nom": r["nom"],
                    "code": r["code"],
                    "etat": etat,
                    "no_dossier": no_dossier,
                    "client": client,
                    "designation": designation,
                    "duree_heures": duree or None,
                    "avancement_pct": pct,
                })
    except Exception:
        return {"machines": []}

    return {"machines": machines}
