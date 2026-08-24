"""MySifa — MyCalendrier — agrégation d'événements."""

from __future__ import annotations

import calendar
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from app.routers.planning import (
    _auto_complete_en_cours,
    _compute_timeline_slots,
    _enforce_single_en_cours,
    _fmt_ts,
    _hours_for_date_factory,
    _load_planning_calendar_maps_range,
    _parse_planned_dt as _parse_planned_dt_planning,
)
from app.services.cal_recurrence import (
    MAX_JOURS as RECURRENCE_MAX_JOURS,
    RECURRENCES,
    occurrences_serie,
)
from app.services.ics_service import (
    IcsError,
    events_from_ics,
    fetch_ics,
    normalize_feed_url,
)
from config import (
    ROLE_DIRECTION,
    ROLE_SUPERADMIN,
    ROLES_ADMINISTRATION_ALL,
    national_holidays_between,
    public_base_url,
)
from database import get_db
from services.auth_service import CALENDRIER_PAGE_ROLES, require_calendrier

router = APIRouter(tags=["calendrier"])

CALENDRIER_ADMIN_CALENDARS = frozenset(
    {"conges", "anniversaires", "feries", "paie", "expeditions"}
)
CALENDRIER_BASIC_CALENDARS = frozenset({"conges", "feries"})
CALENDRIER_PERSO_CAL = "perso"
# Les creneaux des collegues, jadis melanges au calendrier personnel, ont leur
# propre calendrier : « Mon calendrier » ne porte plus que mes creneaux et les
# reunions ou je suis invite.
CALENDRIER_COLLEGUES_CAL = "collegues"

# Reponse d'un invite a une reunion.
STATUTS_PARTICIPANT = frozenset({"en_attente", "accepte", "refuse", "peut_etre"})
# Fenetre de la pop-up de rappel avant une reunion.
RAPPEL_AVANT_MINUTES = 10

# Recurrences : une serie est materialisee — une ligne par occurrence, reliees
# par serie_id, chacune avec ses invites et ses reponses. Le depliage vit dans
# app/services/cal_recurrence.py, testable sans FastAPI.

# Calendriers externes (abonnements ICS) : identifiants dynamiques sub_<id>.
SUB_CAL_RE = re.compile(r"^sub_(\d+)$")
CAL_SUB_TTL_MINUTES = 30
# Rafraichissement opportuniste pendant une requete d'affichage : timeout court.
CAL_SUB_TIMEOUT_S = 6
CAL_SUB_TIMEOUT_MANUEL_S = 15
CAL_SUB_MAX = 12
CAL_SUB_COLOR_DEFAULT = "#7dd3fc"

# Flux ICS sortant (abonnement Outlook / Google / Apple).
FEED_PAST_DAYS = 120
FEED_FUTURE_DAYS = 400
FEED_DEFAULT_CALENDARS = CALENDRIER_PERSO_CAL

# Libelle affiche aux autres utilisateurs pour un creneau perso masque.
PERSO_BUSY_LABEL = "Occupé"

# Codes machines (table machines) — les id numériques ne sont pas fixes en base.
PRODUCTION_MACHINE_CODES: dict[str, str] = {
    "production_1": "C1",
    "production_2": "C2",
    "production_3": "DSI",
    "production_4": "REP",
}

VALID_CALENDARS = frozenset(
    set(PRODUCTION_MACHINE_CODES.keys())
    | {
        "conges",
        "anniversaires",
        "feries",
        "paie",
        "expeditions",
        "perso",
        "collegues",
    }
)

DEFAULT_CALENDARS = ",".join(
    [
        "production_1",
        "production_2",
        "production_3",
        "production_4",
        "conges",
        "anniversaires",
        "feries",
        "paie",
        "expeditions",
        "perso",
        "collegues",
    ]
)


def _allowed_calendars_for_role(role: str) -> frozenset[str]:
    if role in {ROLE_SUPERADMIN, ROLE_DIRECTION}:
        base: frozenset[str] = VALID_CALENDARS
    elif role in ROLES_ADMINISTRATION_ALL:
        base = CALENDRIER_ADMIN_CALENDARS
    else:
        base = CALENDRIER_BASIC_CALENDARS
    return base | frozenset({CALENDRIER_PERSO_CAL, CALENDRIER_COLLEGUES_CAL})


def _filter_calendars_for_role(role: str, requested: set[str]) -> set[str]:
    allowed = _allowed_calendars_for_role(role)
    return {c for c in requested if c in allowed or SUB_CAL_RE.match(c)}


def _sub_ids_from_cals(cals: set[str]) -> list[int]:
    out: list[int] = []
    for c in cals:
        m = SUB_CAL_RE.match(c)
        if m:
            try:
                out.append(int(m.group(1)))
            except ValueError:
                continue
    return sorted(set(out))


class PersoEventCreate(BaseModel):
    titre: str = Field(..., min_length=1, max_length=500)
    date_debut: str
    date_fin: str
    all_day: bool = False
    note: Optional[str] = Field(None, max_length=4000)
    prive: bool = False
    participants: Optional[list[int]] = None
    invites_externes: Optional[list[str]] = None
    lieu: Optional[str] = Field(None, max_length=300)
    visio: Optional[str] = Field(None, max_length=500)
    rappel_minutes: Optional[int] = None
    au_nom_de: Optional[int] = None
    recurrence: Optional[str] = Field(None, max_length=20)
    recurrence_fin: Optional[str] = Field(None, max_length=10)


class PersoEventUpdate(BaseModel):
    """Mise a jour partielle — seuls les champs fournis sont ecrits."""

    titre: Optional[str] = Field(None, min_length=1, max_length=500)
    date_debut: Optional[str] = None
    date_fin: Optional[str] = None
    all_day: Optional[bool] = None
    note: Optional[str] = Field(None, max_length=4000)
    prive: Optional[bool] = None
    participants: Optional[list[int]] = None
    invites_externes: Optional[list[str]] = None
    lieu: Optional[str] = Field(None, max_length=300)
    visio: Optional[str] = Field(None, max_length=500)
    rappel_minutes: Optional[int] = None
    serie: bool = False


class ParticipantReponse(BaseModel):
    """Reponse d'un invite : accepte / refuse / peut_etre."""

    statut: str = Field(..., max_length=20)


class PropositionCreate(BaseModel):
    """Un invite propose un autre horaire plutot que de refuser sec."""

    date_debut: str
    date_fin: str
    message: Optional[str] = Field(None, max_length=500)


class DelegationCreate(BaseModel):
    delegue_id: int


class SubscriptionCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=200)
    url: str = Field(..., min_length=5, max_length=2000)
    couleur: Optional[str] = Field(None, max_length=9)


class SubscriptionUpdate(BaseModel):
    nom: Optional[str] = Field(None, min_length=1, max_length=200)
    url: Optional[str] = Field(None, min_length=5, max_length=2000)
    couleur: Optional[str] = Field(None, max_length=9)
    actif: Optional[bool] = None


class FeedUpdate(BaseModel):
    calendriers: Optional[str] = Field(None, max_length=500)
    actif: Optional[bool] = None


def _parse_event_dt(s: str, field: str) -> datetime:
    raw = str(s or "").strip().replace(" ", "T")
    if len(raw) == 10:
        raw = f"{raw}T00:00"
    try:
        return datetime.fromisoformat(raw[:16])
    except ValueError:
        raise HTTPException(
            400,
            detail=f"{field} : format YYYY-MM-DDTHH:MM attendu.",
        )


def _user_id_from_session(user: dict) -> int:
    uid = user.get("id")
    if uid is None:
        raise HTTPException(401, detail="Session invalide.")
    try:
        return int(uid)
    except (TypeError, ValueError):
        raise HTTPException(401, detail="Session invalide.")


RAPPELS_PROPOSES = (0, 5, 10, 15, 30, 60, 120, 1440)


def _valider_rappel(valeur: Optional[int]) -> Optional[int]:
    """None = rappel par defaut du calendrier ; 0 = aucun rappel."""
    if valeur is None:
        return None
    try:
        n = int(valeur)
    except (TypeError, ValueError):
        return None
    if n not in RAPPELS_PROPOSES:
        # On ramene a la valeur proposee la plus proche plutot que de refuser :
        # le champ vient d'un menu, une valeur exotique est un bug d'appelant.
        n = min(RAPPELS_PROPOSES, key=lambda x: abs(x - n))
    return n


def _identite_utilisateur(conn, uid: int) -> tuple[str, str]:
    r = conn.execute("SELECT nom, email FROM users WHERE id = ?", (uid,)).fetchone()
    if not r:
        return ("Utilisateur", "")
    return ((r["nom"] or "").strip() or "Utilisateur", (r["email"] or "").strip())


def _nom_utilisateur(conn, uid: int) -> str:
    return _identite_utilisateur(conn, uid)[0]


def _users_invitables(conn) -> list[dict]:
    """Utilisateurs que l'on peut inviter : ceux qui peuvent ouvrir MyCalendrier.

    Inviter quelqu'un qui n'a pas acces a la page lui enverrait une reunion
    qu'il ne pourrait ni voir ni refuser — on ne les propose donc pas.
    """
    roles = sorted(CALENDRIER_PAGE_ROLES)
    marks = ",".join("?" for _ in roles)
    rows = conn.execute(
        f"""
        SELECT id, nom, role
        FROM users
        WHERE COALESCE(actif, 1) = 1
          AND role IN ({marks})
        ORDER BY nom COLLATE NOCASE ASC
        """,
        tuple(roles),
    ).fetchall()
    return [
        {"id": int(r["id"]), "nom": (r["nom"] or "").strip(), "role": r["role"] or ""}
        for r in rows
    ]


def _participants_par_event(conn, event_ids: list[int]) -> dict[int, list[dict]]:
    """{event_id: [{user_id, nom, statut, repondu_le}, ...]} pour les ids donnes."""
    if not event_ids:
        return {}
    out: dict[int, list[dict]] = {}
    marks = ",".join("?" for _ in event_ids)
    rows = conn.execute(
        f"""
        SELECT p.event_id, p.user_id, p.statut, p.repondu_le, u.nom, u.email
        FROM cal_event_participants p
        LEFT JOIN users u ON u.id = p.user_id
        WHERE p.event_id IN ({marks})
        ORDER BY u.nom COLLATE NOCASE ASC, p.user_id ASC
        """,
        tuple(event_ids),
    ).fetchall()
    for r in rows:
        out.setdefault(int(r["event_id"]), []).append(
            {
                "user_id": int(r["user_id"]),
                "nom": (r["nom"] or "").strip() or "Utilisateur",
                "email": (r["email"] or "").strip(),
                "statut": (r["statut"] or "en_attente").strip(),
                "repondu_le": r["repondu_le"],
            }
        )
    return out


def _ecrire_participants(conn, event_id: int, organisateur_id: int, ids: list[int]) -> None:
    """Aligne la liste des invites sur `ids`, en gardant les reponses deja donnees."""
    voulus = {int(i) for i in ids if int(i) != organisateur_id}
    if voulus:
        connus = {
            int(r["id"])
            for r in conn.execute(
                f"""SELECT id FROM users
                     WHERE COALESCE(actif, 1) = 1
                       AND id IN ({",".join("?" for _ in voulus)})""",
                tuple(sorted(voulus)),
            ).fetchall()
        }
        voulus &= connus
    actuels = {
        int(r["user_id"])
        for r in conn.execute(
            "SELECT user_id FROM cal_event_participants WHERE event_id = ?",
            (event_id,),
        ).fetchall()
    }
    for uid in sorted(voulus - actuels):
        conn.execute(
            """INSERT OR IGNORE INTO cal_event_participants (event_id, user_id, statut)
               VALUES (?, ?, 'en_attente')""",
            (event_id, uid),
        )
    retires = actuels - voulus
    if retires:
        conn.execute(
            f"""DELETE FROM cal_event_participants
                 WHERE event_id = ?
                   AND user_id IN ({",".join("?" for _ in retires)})""",
            (event_id, *sorted(retires)),
        )


def _valider_recurrence(
    regle: Optional[str], fin_str: Optional[str], debut: datetime
) -> tuple[Optional[str], Optional[date]]:
    regle = (regle or "").strip()
    if not regle or regle == "aucune":
        return None, None
    if regle not in RECURRENCES:
        raise HTTPException(400, detail="Récurrence inconnue.")
    if not fin_str:
        raise HTTPException(400, detail="Une répétition demande une date de fin.")
    fin = _parse_ymd(fin_str)
    if fin < debut.date():
        raise HTTPException(400, detail="La fin de répétition précède le premier créneau.")
    if (fin - debut.date()).days > RECURRENCE_MAX_JOURS:
        raise HTTPException(
            400, detail="Une répétition ne peut pas dépasser deux ans."
        )
    return regle, fin


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def _emails_valides(valeurs: Optional[list[str]]) -> list[str]:
    out: list[str] = []
    for v in valeurs or []:
        mail = str(v or "").strip().lower()
        if mail and EMAIL_RE.match(mail) and mail not in out:
            out.append(mail)
    return out[:30]


def _invites_ext_par_event(conn, event_ids: list[int]) -> dict[int, list[dict]]:
    if not event_ids:
        return {}
    marks = ",".join("?" for _ in event_ids)
    out: dict[int, list[dict]] = {}
    for r in conn.execute(
        f"""SELECT event_id, email, nom, statut, repondu_le
              FROM cal_event_invites_ext
             WHERE event_id IN ({marks})
             ORDER BY email ASC""",
        tuple(event_ids),
    ).fetchall():
        out.setdefault(int(r["event_id"]), []).append(
            {
                "email": r["email"],
                "nom": (r["nom"] or "").strip() or r["email"],
                "statut": (r["statut"] or "en_attente").strip(),
                "repondu_le": r["repondu_le"],
                "externe": True,
            }
        )
    return out


def _propositions_par_event(conn, event_ids: list[int]) -> dict[int, list[dict]]:
    """Contre-propositions d'horaire encore ouvertes, par evenement."""
    if not event_ids:
        return {}
    marks = ",".join("?" for _ in event_ids)
    out: dict[int, list[dict]] = {}
    for r in conn.execute(
        f"""SELECT p.event_id, p.id, p.user_id, p.date_debut, p.date_fin,
                   p.message, p.statut, u.nom
              FROM cal_event_propositions p
              LEFT JOIN users u ON u.id = p.user_id
             WHERE p.event_id IN ({marks}) AND p.statut = 'proposee'
             ORDER BY p.date_debut ASC""",
        tuple(event_ids),
    ).fetchall():
        out.setdefault(int(r["event_id"]), []).append(
            {
                "id": int(r["id"]),
                "user_id": int(r["user_id"]),
                "nom": (r["nom"] or "").strip() or "Utilisateur",
                "debut": r["date_debut"],
                "fin": r["date_fin"],
                "message": (r["message"] or "").strip(),
            }
        )
    return out


def _ecrire_invites_ext(conn, event_id: int, emails: list[str]) -> list[dict]:
    """Aligne les invites externes, en gardant jeton et reponse de ceux qui restent."""
    voulus = set(emails)
    actuels = {
        r["email"]: r["jeton"]
        for r in conn.execute(
            "SELECT email, jeton FROM cal_event_invites_ext WHERE event_id = ?",
            (event_id,),
        ).fetchall()
    }
    nouveaux: list[dict] = []
    for mail in sorted(voulus - set(actuels)):
        jeton = secrets.token_urlsafe(24)
        conn.execute(
            """INSERT OR IGNORE INTO cal_event_invites_ext (event_id, email, jeton)
               VALUES (?, ?, ?)""",
            (event_id, mail, jeton),
        )
        nouveaux.append({"email": mail, "jeton": jeton})
    retires = set(actuels) - voulus
    if retires:
        conn.execute(
            f"""DELETE FROM cal_event_invites_ext
                 WHERE event_id = ? AND email IN ({",".join("?" for _ in retires)})""",
            (event_id, *sorted(retires)),
        )
    return nouveaux


# ---------------------------------------------------------------------------
# Delegations : poser un creneau au nom de quelqu'un d'autre
# ---------------------------------------------------------------------------


def _calendriers_delegues(conn, uid: int) -> list[dict]:
    """Les calendriers que l'on peut alimenter en plus du sien."""
    rows = conn.execute(
        """SELECT d.proprietaire_id, u.nom
             FROM cal_delegations d
             JOIN users u ON u.id = d.proprietaire_id
            WHERE d.delegue_id = ? AND COALESCE(u.actif, 1) = 1
            ORDER BY u.nom COLLATE NOCASE ASC""",
        (uid,),
    ).fetchall()
    return [
        {"id": int(r["proprietaire_id"]), "nom": (r["nom"] or "").strip()}
        for r in rows
    ]


def _resoudre_proprietaire(conn, uid: int, au_nom_de: Optional[int]) -> int:
    """L'id du calendrier vise, apres verification de la delegation."""
    if au_nom_de is None or int(au_nom_de) == uid:
        return uid
    cible = int(au_nom_de)
    ok = conn.execute(
        "SELECT 1 FROM cal_delegations WHERE proprietaire_id = ? AND delegue_id = ?",
        (cible, uid),
    ).fetchone()
    if not ok:
        raise HTTPException(
            403, detail="Vous n'avez pas de délégation sur ce calendrier."
        )
    return cible


def _notifier_invitation(user_ids: list[int], titre: str, debut: str) -> None:
    """Push best-effort : une invitation ne doit jamais faire echouer la creation."""
    if not user_ids:
        return
    try:
        from app.routers.push import send_push_to_user

        quand = str(debut or "").replace("T", " ")[:16]
        for uid in user_ids:
            try:
                send_push_to_user(
                    uid,
                    "Invitation à une réunion",
                    f"{titre} — {quand}",
                    url="/calendrier",
                    tag="cal-invitation",
                )
            except Exception:
                continue
    except Exception:
        return


JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def _quand_lisible(debut: str, fin: str, all_day: bool) -> str:
    d = _parse_planned_dt(debut)
    f = _parse_planned_dt(fin)
    if not d:
        return str(debut or "")
    jour = f"{JOURS_FR[d.weekday()]} {d.day} {MOIS_FR[d.month - 1]} {d.year}"
    if all_day:
        return f"{jour} — journée entière"
    fin_txt = f.strftime("%H:%M") if f else ""
    return f"{jour} de {d.strftime('%H:%M')}" + (f" à {fin_txt}" if fin_txt else "")


MOIS_COURT_FR = [
    "janv.", "févr.", "mars", "avril", "mai", "juin",
    "juil.", "août", "sept.", "oct.", "nov.", "déc.",
]


def _duree_lisible(debut: str, fin: str) -> str:
    d = _parse_planned_dt(debut)
    f = _parse_planned_dt(fin)
    if not d or not f or f <= d:
        return ""
    minutes = int((f - d).total_seconds() // 60)
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h} h {m:02d}"
    if h:
        return f"{h} h"
    return f"{m} min"


def _creneau_pour_email(debut: str, fin: str, all_day: bool) -> dict:
    """Les morceaux de date affichés dans le pavé de l'e-mail."""
    d = _parse_planned_dt(debut)
    f = _parse_planned_dt(fin)
    if not d:
        return {
            "jour_num": "?",
            "mois_court": "",
            "jour_semaine": str(debut or ""),
            "heures": "",
            "duree": "",
        }
    return {
        "jour_num": f"{d.day:02d}",
        "mois_court": MOIS_COURT_FR[d.month - 1],
        "jour_semaine": f"{JOURS_FR[d.weekday()]} {d.day} {MOIS_FR[d.month - 1]} {d.year}",
        "heures": "Journée entière"
        if all_day
        else (d.strftime("%H:%M") + (f" → {f.strftime('%H:%M')}" if f else "")),
        "duree": "" if all_day else _duree_lisible(debut, fin),
    }


def _envoyer_invitation_email(
    *,
    destinataires: list[dict],
    ev_ics: dict,
    titre: str,
    debut: str,
    fin: str,
    all_day: bool,
    organisateur: str,
    lieu: str,
    visio: str,
    note: str,
    participants: str = "",
    annulation: bool = False,
) -> None:
    """E-mail d'invitation avec le .ics en pièce jointe.

    Best-effort de bout en bout : une réunion se crée même si le serveur mail
    est muet. Un invité externe reçoit ses trois boutons de réponse (son jeton),
    un invité interne le lien du calendrier.
    """
    if not destinataires:
        return
    try:
        from app.services.email_service import email_invitation_reunion, send_email
    except Exception:
        return
    creneau = _creneau_pour_email(debut, fin, all_day)
    ics = build_ics_calendar(
        [ev_ics],
        nom="MySifa",
        methode="CANCEL" if annulation else "REQUEST",
    ).encode("utf-8")
    base = public_base_url()
    for dest in destinataires:
        mail = str(dest.get("email") or "").strip()
        if not mail:
            continue
        jeton = str(dest.get("jeton") or "").strip()
        sujet, corps = email_invitation_reunion(
            titre=titre,
            lieu=lieu,
            visio=visio,
            organisateur=organisateur,
            participants=participants,
            note=note,
            lien_app=f"{base}/calendrier",
            lien_reponse=f"{base}/calendrier/invitation/{jeton}" if jeton else "",
            annulation=annulation,
            **creneau,
        )
        try:
            send_email(
                mail,
                sujet,
                corps,
                attachments=[
                    {
                        "filename": "invitation.ics",
                        "content": ics,
                        "mime": "text/calendar",
                    }
                ],
            )
        except Exception:
            continue


def _prevenir_annulation(conn, event_ids: list[int]) -> None:
    """Un seul e-mail par personne, avec toutes les occurrences annulees dedans.

    Le .ics porte METHOD:CANCEL et un VEVENT par creneau : le client calendrier
    du destinataire retire exactement ce qui a ete annule, meme sur une serie.
    """
    if not event_ids:
        return
    marks = ",".join("?" for _ in event_ids)
    rows = conn.execute(
        f"""SELECT e.id, e.titre, e.date_debut, e.date_fin, e.all_day, e.note,
                   e.lieu, e.visio, e.user_id, u.nom AS org_nom, u.email AS org_mail
              FROM cal_events_perso e
              LEFT JOIN users u ON u.id = e.user_id
             WHERE e.id IN ({marks})
             ORDER BY e.date_debut ASC""",
        tuple(event_ids),
    ).fetchall()
    if not rows:
        return
    internes = _participants_par_event(conn, event_ids)
    externes = _invites_ext_par_event(conn, event_ids)
    destinataires: dict[str, dict] = {}
    for eid in event_ids:
        for p in internes.get(eid, []):
            if p.get("email"):
                destinataires.setdefault(p["email"], {"email": p["email"]})
        for p in externes.get(eid, []):
            destinataires.setdefault(p["email"], {"email": p["email"]})
    if not destinataires:
        return
    premier = rows[0]
    org_nom = (premier["org_nom"] or "").strip() or "MySifa"
    evs = [
        _ev_pour_ics(
            event_id=int(r["id"]),
            titre=(r["titre"] or "").strip() or "Sans titre",
            debut=str(r["date_debut"] or ""),
            fin=str(r["date_fin"] or ""),
            all_day=bool(int(r["all_day"] or 0)),
            meta={
                "reunion": True,
                "annule": True,
                "organisateur_nom": org_nom,
                "organisateur_email": (r["org_mail"] or "").strip(),
                "participants": internes.get(int(r["id"]), []),
                "invites_externes": externes.get(int(r["id"]), []),
                "lieu": r["lieu"] or "",
                "visio": r["visio"] or "",
            },
        )
        for r in rows
    ]
    titre = (premier["titre"] or "").strip() or "Sans titre"
    suffixe = f" ({len(evs)} créneaux)" if len(evs) > 1 else ""
    try:
        from app.services.email_service import email_invitation_reunion, send_email
    except Exception:
        return
    creneau = _creneau_pour_email(
        str(premier["date_debut"] or ""),
        str(premier["date_fin"] or ""),
        bool(int(premier["all_day"] or 0)),
    )
    noms = ", ".join(
        p["nom"] for p in internes.get(int(premier["id"]), []) if p.get("nom")
    )
    sujet, corps = email_invitation_reunion(
        titre=titre + suffixe,
        lieu=premier["lieu"] or "",
        visio=premier["visio"] or "",
        organisateur=org_nom,
        participants=noms,
        note="",
        annulation=True,
        **creneau,
    )
    ics = build_ics_calendar(evs, nom="MySifa", methode="CANCEL").encode("utf-8")
    for dest in destinataires.values():
        try:
            send_email(
                dest["email"],
                sujet,
                corps,
                attachments=[
                    {
                        "filename": "annulation.ics",
                        "content": ics,
                        "mime": "text/calendar",
                    }
                ],
            )
        except Exception:
            continue


def _ev_pour_ics(
    *,
    event_id: int,
    titre: str,
    debut: str,
    fin: str,
    all_day: bool,
    meta: dict,
) -> dict:
    return {
        "id": f"perso-{event_id}",
        "calendrier": CALENDRIER_PERSO_CAL,
        "titre": titre,
        "debut": debut,
        "fin": fin,
        "all_day": all_day,
        "meta": meta,
    }


def _parse_ymd(s: str) -> date:
    try:
        return datetime.strptime(s.strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, detail="date_debut / date_fin : format YYYY-MM-DD attendu.")


def _parse_planned_dt(val: Any) -> Optional[datetime]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    s = s.replace("Z", "").split("+")[0].strip()
    if len(s) == 10:
        s = f"{s}T00:00:00"
    elif "T" not in s and len(s) >= 16:
        s = s.replace(" ", "T", 1)
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        try:
            return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


def _fmt_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M")


def _event(
    *,
    eid: str,
    cal: str,
    titre: str,
    debut: str,
    fin: str,
    all_day: bool,
    meta: Optional[dict] = None,
) -> dict:
    return {
        "id": eid,
        "calendrier": cal,
        "titre": titre,
        "debut": debut,
        "fin": fin,
        "all_day": all_day,
        "meta": meta or {},
    }


def _ranges_overlap(d0: date, d1: date, start: date, end: date) -> bool:
    return start <= d1 and end >= d0


def _resolve_production_machines(
    conn, cals: set[str]
) -> dict[str, int]:
    """cal_key → machine_id réel (via code C1, C2, DSI, REP)."""
    wanted = {
        cal_key: code
        for cal_key, code in PRODUCTION_MACHINE_CODES.items()
        if cal_key in cals
    }
    if not wanted:
        return {}
    codes = list(wanted.values())
    placeholders = ",".join("?" * len(codes))
    rows = conn.execute(
        f"SELECT id, code FROM machines WHERE code IN ({placeholders})",
        codes,
    ).fetchall()
    code_to_id = {str(r["code"]): int(r["id"]) for r in rows}
    out: dict[str, int] = {}
    for cal_key, code in wanted.items():
        mid = code_to_id.get(code)
        if mid is not None:
            out[cal_key] = mid
    return out


def _slot_in_range(start_iso: str, end_iso: str, d0: date, d1: date) -> bool:
    ps = _parse_planned_dt_planning(start_iso)
    pe = _parse_planned_dt_planning(end_iso) or ps
    if not ps:
        return False
    return ps.date() <= d1 and pe.date() >= d0


def _production_events_for_machine(
    conn,
    machine_id: int,
    cal_key: str,
    d0: date,
    d1: date,
) -> list[dict]:
    """Créneaux alignés sur GET /machines/{id}/timeline (horaires ouvrés, recalcul attente)."""
    machine = conn.execute("SELECT * FROM machines WHERE id=?", (machine_id,)).fetchone()
    if not machine:
        return []
    m = dict(machine)

    today = date.today()
    weeks_back = max(12, (today - d0).days // 7 + 2)
    weeks_forward = max(12, (d1 - today).days // 7 + 2)
    configs, off_days, day_worked_map, day_horaires_map = _load_planning_calendar_maps_range(
        conn, machine_id, weeks_back=weeks_back, weeks_forward=weeks_forward
    )

    _auto_complete_en_cours(conn, machine_id)
    _enforce_single_en_cours(conn, machine_id)

    rows = conn.execute(
        """
        SELECT * FROM planning_entries
        WHERE machine_id = ?
        ORDER BY position ASC
        """,
        (machine_id,),
    ).fetchall()
    entries_list = [dict(r) for r in rows]
    main_entries: list[dict] = []
    aplacer_entries: list[dict] = []
    for e in entries_list:
        st = (e.get("statut") or "attente").strip()
        ap = int(e.get("a_placer") or 0)
        if st == "attente" and ap == 1:
            aplacer_entries.append(e)
        else:
            main_entries.append(e)
    entries_list = main_entries + aplacer_entries

    slots = _compute_timeline_slots(
        conn,
        machine_id,
        m,
        configs,
        off_days,
        day_worked_map,
        day_horaires_map,
        entries_list,
    )

    out: list[dict] = []
    for slot in slots:
        ps_iso = slot.get("start") or ""
        pe_iso = slot.get("end") or ""
        if not _slot_in_range(ps_iso, pe_iso, d0, d1):
            continue
        ref = (slot.get("reference") or slot.get("numero_of") or "").strip()
        cli = (slot.get("client") or "").strip()
        entry_id = slot.get("entry_id")
        titre = f"{ref} · {cli}" if cli else ref or f"Dossier #{entry_id}"
        out.append(
            _event(
                eid=f"prod-{cal_key}-{entry_id}",
                cal=cal_key,
                titre=titre,
                debut=_fmt_ts(_parse_planned_dt_planning(ps_iso) or datetime.now()),
                fin=_fmt_ts(
                    _parse_planned_dt_planning(pe_iso)
                    or _parse_planned_dt_planning(ps_iso)
                    or datetime.now()
                ),
                all_day=False,
                meta={
                    "statut": slot.get("statut"),
                    "machine_id": machine_id,
                    "machine_code": m.get("code"),
                    "reference": ref,
                },
            )
        )
    return out


def _compute_day_windows(
    conn,
    prod_machine_ids: list[int],
    d0: date,
    d1: date,
) -> dict[str, dict[str, float]]:
    """Plage horaire d'affichage par jour (union des machines production), alignée planning."""
    if not prod_machine_ids:
        return {}

    unique_ids = list(dict.fromkeys(prod_machine_ids))
    today = date.today()
    weeks_back = max(12, (today - d0).days // 7 + 2)
    weeks_forward = max(12, (d1 - today).days // 7 + 2)

    getters: list[Any] = []
    for mid in unique_ids:
        row = conn.execute("SELECT * FROM machines WHERE id=?", (mid,)).fetchone()
        if not row:
            continue
        m = dict(row)
        configs, off_days, day_worked_map, day_horaires_map = _load_planning_calendar_maps_range(
            conn, mid, weeks_back=weeks_back, weeks_forward=weeks_forward
        )
        getters.append(
            _hours_for_date_factory(m, configs, off_days, day_worked_map, day_horaires_map)
        )

    if not getters:
        return {}

    default_start, default_end = 5.0, 21.0
    windows: dict[str, dict[str, float]] = {}
    cur = d0
    while cur <= d1:
        dkey = cur.isoformat()
        dt = datetime(cur.year, cur.month, cur.day)
        starts: list[float] = []
        ends: list[float] = []
        for get_h in getters:
            win = get_h(dt)
            if win:
                starts.append(float(win[0]))
                ends.append(float(win[1]))
        if starts:
            windows[dkey] = {"h_start": min(starts), "h_end": max(ends)}
        else:
            windows[dkey] = {
                "h_start": default_start,
                "h_end": default_end,
                "off": 1.0,
            }
        cur += timedelta(days=1)
    return windows


def _calendar_request_context(
    request: Request,
    date_debut: str,
    date_fin: str,
    calendriers: str,
) -> tuple[dict, date, date, set[str]]:
    user = require_calendrier(request)
    d0 = _parse_ymd(date_debut)
    d1 = _parse_ymd(date_fin)
    if d1 < d0:
        raise HTTPException(400, detail="date_fin doit être >= date_debut.")
    role = str(user.get("role") or "")
    requested = {c.strip() for c in calendriers.split(",") if c.strip()}
    cals = _filter_calendars_for_role(role, requested)
    unknown = {
        c for c in cals if c not in VALID_CALENDARS and not SUB_CAL_RE.match(c)
    }
    if unknown:
        raise HTTPException(400, detail=f"Calendriers inconnus : {', '.join(sorted(unknown))}")
    return user, d0, d1, cals


def _fetch_calendar_events(
    user: dict,
    d0: date,
    d1: date,
    cals: set[str],
    *,
    perso_own_only: bool = False,
) -> tuple[list[dict], dict[str, dict[str, float]]]:
    """perso_own_only : flux ICS personnel — on exclut les créneaux des collègues."""
    out: list[dict] = []
    prod_machine_ids: list[int] = []
    day_windows: dict[str, dict[str, float]] = {}

    with get_db() as conn:
        prod_machines = _resolve_production_machines(conn, cals)
        prod_machine_ids = list(prod_machines.values())
        for cal_key, machine_id in prod_machines.items():
            out.extend(
                _production_events_for_machine(conn, machine_id, cal_key, d0, d1)
            )
        conn.commit()

        if "conges" in cals:
            rows = conn.execute(
                """
                SELECT c.id, c.date_debut, c.date_fin, c.type_conge, c.statut, u.nom
                FROM rh_conges c
                JOIN users u ON u.id = c.user_id
                WHERE c.statut IN ('pose', 'valide')
                  AND date(c.date_debut) <= ?
                  AND date(c.date_fin) >= ?
                """,
                (d1.isoformat(), d0.isoformat()),
            ).fetchall()
            for r in rows:
                nom = (r["nom"] or "").strip() or "Utilisateur"
                tc = (r["type_conge"] or "CP").strip()
                try:
                    db = datetime.strptime(str(r["date_debut"])[:10], "%Y-%m-%d").date()
                    de = datetime.strptime(str(r["date_fin"])[:10], "%Y-%m-%d").date()
                except ValueError:
                    continue
                out.append(
                    _event(
                        eid=f"conge-{r['id']}",
                        cal="conges",
                        titre=f"{nom} · {tc}",
                        debut=f"{db.isoformat()}T00:00",
                        fin=f"{de.isoformat()}T23:59",
                        all_day=True,
                        meta={"statut": r["statut"], "type_conge": tc},
                    )
                )

        if "anniversaires" in cals:
            rows = conn.execute(
                """
                SELECT id, nom, date_naissance
                FROM users
                WHERE actif = 1 AND date_naissance IS NOT NULL AND trim(date_naissance) != ''
                """
            ).fetchall()
            for r in rows:
                raw = str(r["date_naissance"] or "").strip()[:10]
                try:
                    born = datetime.strptime(raw, "%Y-%m-%d").date()
                except ValueError:
                    continue
                nom = (r["nom"] or "").strip() or "Utilisateur"
                for year in range(d0.year, d1.year + 1):
                    try:
                        bday = date(year, born.month, born.day)
                    except ValueError:
                        if born.month == 2 and born.day == 29:
                            bday = date(year, 2, 28)
                        else:
                            continue
                    if d0 <= bday <= d1:
                        out.append(
                            _event(
                                eid=f"anniv-{r['id']}-{year}",
                                cal="anniversaires",
                                titre=nom,
                                debut=f"{bday.isoformat()}T00:00",
                                fin=f"{bday.isoformat()}T23:59",
                                all_day=True,
                                meta={"user_id": r["id"], "annee": year},
                            )
                        )

        if "feries" in cals:
            for ds, label in national_holidays_between(d0.isoformat(), d1.isoformat()):
                try:
                    hd = datetime.strptime(ds, "%Y-%m-%d").date()
                except ValueError:
                    continue
                out.append(
                    _event(
                        eid=f"ferie-{ds}-{label}",
                        cal="feries",
                        titre=label,
                        debut=f"{hd.isoformat()}T00:00",
                        fin=f"{hd.isoformat()}T23:59",
                        all_day=True,
                        meta={},
                    )
                )

        if "expeditions" in cals:
            rows = conn.execute(
                """
                SELECT id, date_enlevement, date_livraison, client, transporteur,
                       ref_sifa, code_postal_destination, statut, nb_palette, poids_total_kg
                FROM expe_departs
                WHERE statut IN ('en_attente', 'valide')
                  AND date(date_enlevement) <= ?
                  AND date(COALESCE(NULLIF(trim(date_livraison), ''), date_enlevement)) >= ?
                ORDER BY date_enlevement ASC, id ASC
                """,
                (d1.isoformat(), d0.isoformat()),
            ).fetchall()
            for r in rows:
                try:
                    d_enl = datetime.strptime(
                        str(r["date_enlevement"] or "")[:10], "%Y-%m-%d"
                    ).date()
                except ValueError:
                    continue
                d_liv = d_enl
                raw_liv = str(r["date_livraison"] or "").strip()[:10]
                if raw_liv:
                    try:
                        d_liv = datetime.strptime(raw_liv, "%Y-%m-%d").date()
                    except ValueError:
                        d_liv = d_enl
                if d_liv < d_enl:
                    d_liv = d_enl
                if not _ranges_overlap(d0, d1, d_enl, d_liv):
                    continue
                client = (r["client"] or "").strip()
                transp = (r["transporteur"] or "").strip()
                ref = (r["ref_sifa"] or "").strip()
                cp = (r["code_postal_destination"] or "").strip()
                parts = [p for p in (client, transp) if p]
                if not parts and ref:
                    parts = [ref]
                titre = " · ".join(parts) if parts else f"Départ #{r['id']}"
                if cp and cp not in titre:
                    titre = f"{titre} ({cp})"
                out.append(
                    _event(
                        eid=f"expe-{r['id']}",
                        cal="expeditions",
                        titre=titre,
                        debut=f"{d_enl.isoformat()}T00:00",
                        fin=f"{d_liv.isoformat()}T23:59",
                        all_day=True,
                        meta={
                            "statut": r["statut"],
                            "ref_sifa": ref,
                            "date_enlevement": d_enl.isoformat(),
                            "date_livraison": d_liv.isoformat(),
                        },
                    )
                )

        if "paie" in cals:
            rows = conn.execute(
                """
                SELECT DISTINCT annee, mois
                FROM paie_variables
                ORDER BY annee, mois
                """
            ).fetchall()
            seen: set[tuple[int, int]] = set()
            for r in rows:
                annee = int(r["annee"])
                mois = int(r["mois"])
                if mois < 1 or mois > 12:
                    continue
                key = (annee, mois)
                if key in seen:
                    continue
                last_day = calendar.monthrange(annee, mois)[1]
                start = date(annee, mois, 1)
                end = date(annee, mois, last_day)
                if not _ranges_overlap(d0, d1, start, end):
                    continue
                seen.add(key)
                out.append(
                    _event(
                        eid=f"paie-{annee}-{mois}",
                        cal="paie",
                        titre=f"Paie · {mois}/{annee}",
                        debut=f"{end.isoformat()}T00:00",
                        fin=f"{end.isoformat()}T23:59",
                        all_day=True,
                        meta={"annee": annee, "mois": mois},
                    )
                )

        if prod_machine_ids:
            day_windows = _compute_day_windows(conn, prod_machine_ids, d0, d1)

        besoin_perso = CALENDRIER_PERSO_CAL in cals
        besoin_collegues = CALENDRIER_COLLEGUES_CAL in cals
        if besoin_perso or besoin_collegues:
            uid = _user_id_from_session(user)
            rows = conn.execute(
                """
                SELECT e.id, e.user_id, e.titre, e.date_debut, e.date_fin,
                       e.all_day, e.note, e.prive,
                       COALESCE(e.annule, 0) AS annule,
                       e.serie_id, e.recurrence, e.lieu, e.visio,
                       e.rappel_minutes, e.cree_par,
                       u.nom AS user_nom, u.email AS user_email,
                       p.statut AS mon_statut,
                       (SELECT COUNT(*) FROM cal_event_participants x
                         WHERE x.event_id = e.id) AS nb_invites
                FROM cal_events_perso e
                LEFT JOIN users u ON u.id = e.user_id
                LEFT JOIN cal_event_participants p
                       ON p.event_id = e.id AND p.user_id = ?
                WHERE date(substr(e.date_debut, 1, 10)) <= ?
                  AND date(substr(e.date_fin, 1, 10)) >= ?
                  AND (e.user_id = ? OR p.user_id IS NOT NULL
                       OR COALESCE(u.actif, 1) = 1)
                ORDER BY e.date_debut ASC, e.id ASC
                """,
                (uid, d1.isoformat(), d0.isoformat(), uid),
            ).fetchall()

            # Les invites d'une reunion ne sont detailles que pour les concernes.
            ids_a_moi = [
                int(r["id"])
                for r in rows
                if int(r["user_id"] or 0) == uid or r["mon_statut"] is not None
            ]
            invites_par_event = _participants_par_event(conn, ids_a_moi)
            ext_par_event = _invites_ext_par_event(conn, ids_a_moi)
            propositions_par_event = _propositions_par_event(conn, ids_a_moi)

            for r in rows:
                debut = str(r["date_debut"] or "").strip()
                fin = str(r["date_fin"] or "").strip() or debut
                all_day = bool(int(r["all_day"] or 0))
                note = (r["note"] or "").strip() or None
                prive = bool(int(r["prive"] or 0))
                annule = bool(int(r["annule"] or 0))
                owner_id = int(r["user_id"] or 0)
                owner_nom = (r["user_nom"] or "").strip() or "Utilisateur"
                own = owner_id == uid
                mon_statut_brut = r["mon_statut"]
                invite = mon_statut_brut is not None
                a_moi = own or invite
                reunion = bool(int(r["nb_invites"] or 0)) or bool(
                    ext_par_event.get(int(r["id"]))
                )
                titre_brut = (r["titre"] or "").strip() or "Sans titre"

                cal = CALENDRIER_PERSO_CAL if a_moi else CALENDRIER_COLLEGUES_CAL
                if cal not in cals:
                    continue
                if perso_own_only and not a_moi:
                    continue
                # Une reunion annulee reste chez l'organisateur et ses invites,
                # barree — mais elle libere le creneau aux yeux des autres.
                if annule and not a_moi:
                    continue

                if a_moi:
                    titre = titre_brut
                elif prive:
                    titre = f"{owner_nom} · {PERSO_BUSY_LABEL}"
                    note = None
                else:
                    titre = f"{owner_nom} · {titre_brut}"

                meta: dict[str, Any] = {
                    "own": own,
                    "prive": prive,
                    "user_id": owner_id,
                    "user_nom": owner_nom,
                }
                if note:
                    meta["note"] = note
                if own:
                    meta["titre_brut"] = titre_brut
                if annule:
                    meta["annule"] = True
                if r["serie_id"]:
                    meta["serie_id"] = r["serie_id"]
                    meta["recurrence"] = r["recurrence"] or ""
                    meta["recurrence_libelle"] = RECURRENCES.get(
                        r["recurrence"] or "", ""
                    )
                if a_moi:
                    if r["lieu"]:
                        meta["lieu"] = r["lieu"]
                    if r["visio"]:
                        meta["visio"] = r["visio"]
                    if r["rappel_minutes"] is not None:
                        meta["rappel_minutes"] = int(r["rappel_minutes"])
                    if own and r["cree_par"]:
                        meta["cree_par_nom"] = _nom_utilisateur(
                            conn, int(r["cree_par"])
                        )
                if a_moi and (reunion or invite):
                    meta["reunion"] = True
                    meta["organisateur_id"] = owner_id
                    meta["organisateur_nom"] = owner_nom
                    meta["organisateur_email"] = (r["user_email"] or "").strip()
                    meta["mon_statut"] = (
                        "organisateur"
                        if own
                        else str(mon_statut_brut or "en_attente").strip()
                    )
                    meta["participants"] = invites_par_event.get(int(r["id"]), [])
                    meta["invites_externes"] = ext_par_event.get(int(r["id"]), [])
                    props = propositions_par_event.get(int(r["id"]), [])
                    if props:
                        meta["propositions"] = props
                out.append(
                    _event(
                        eid=f"perso-{r['id']}",
                        cal=cal,
                        titre=titre,
                        debut=debut,
                        fin=fin,
                        all_day=all_day,
                        meta=meta,
                    )
                )

        sub_ids = _sub_ids_from_cals(cals)
        if sub_ids:
            out.extend(
                _subscription_events(
                    conn, _user_id_from_session(user), sub_ids, d0, d1
                )
            )

    out.sort(key=lambda e: (e["debut"], e["calendrier"], e["id"]))
    return out, day_windows


def _ics_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def _fold_ics_line(line: str, limit: int = 75) -> str:
    if len(line) <= limit:
        return line
    parts = [line[:limit]]
    rest = line[limit:]
    while rest:
        parts.append(" " + rest[: limit - 1])
        rest = rest[limit - 1 :]
    return "\r\n".join(parts)


def _parse_ev_dt_for_ics(raw: str) -> Optional[datetime]:
    s = str(raw or "").strip().replace(" ", "T").split("+")[0]
    if not s:
        return None
    if len(s) == 10:
        s = f"{s}T00:00:00"
    elif "T" in s and len(s) == 16:
        s = f"{s}:00"
    try:
        return datetime.fromisoformat(s[:19])
    except ValueError:
        return None


def _ics_description(ev: dict) -> str:
    """Description lisible dans le client calendrier (pas de JSON brut)."""
    meta = ev.get("meta") or {}
    lines: list[str] = []
    for key, prefix in (
        ("note", ""),
        ("visio", "Visio : "),
        ("statut", "Statut : "),
        ("reference", "Référence : "),
        ("type_conge", "Type : "),
        ("source", "Source : "),
    ):
        val = str(meta.get(key) or "").strip()
        if val:
            lines.append(f"{prefix}{val}")
    lines.append(f"MySifa · {ev.get('calendrier') or 'calendrier'}")
    return "\n".join(lines)


ICS_PARTSTAT = {
    "en_attente": "NEEDS-ACTION",
    "accepte": "ACCEPTED",
    "refuse": "DECLINED",
    "peut_etre": "TENTATIVE",
}


def _ics_personnes(ev: dict) -> list[str]:
    """ORGANIZER / ATTENDEE — la reunion arrive complete dans Outlook."""
    meta = ev.get("meta") or {}
    if not meta.get("reunion"):
        return []
    out: list[str] = []
    org_nom = _ics_escape(str(meta.get("organisateur_nom") or "").strip())
    org_mail = str(meta.get("organisateur_email") or "").strip()
    if org_mail:
        cn = f';CN="{org_nom}"' if org_nom else ""
        out.append(f"ORGANIZER{cn}:mailto:{org_mail}")
    for part in list(meta.get("participants") or []) + list(
        meta.get("invites_externes") or []
    ):
        mail = str(part.get("email") or "").strip()
        if not mail:
            continue
        nom = _ics_escape(str(part.get("nom") or "").strip())
        cn = f';CN="{nom}"' if nom else ""
        partstat = ICS_PARTSTAT.get(str(part.get("statut") or ""), "NEEDS-ACTION")
        out.append(
            f"ATTENDEE{cn};ROLE=REQ-PARTICIPANT;PARTSTAT={partstat}"
            f";RSVP=TRUE:mailto:{mail}"
        )
    return out


def _event_to_vevent_lines(ev: dict) -> list[str]:
    eid = str(ev.get("id") or "event")
    titre = _ics_escape(str(ev.get("titre") or "Sans titre"))
    uid = _ics_escape(f"{eid}@mysifa")
    desc = _ics_escape(_ics_description(ev))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{stamp}",
        f"SUMMARY:{titre}",
    ]
    if desc:
        lines.append(f"DESCRIPTION:{desc}")
    lines.extend(_ics_personnes(ev))
    meta_ev = ev.get("meta") or {}
    lieu = str(meta_ev.get("lieu") or "").strip()
    if lieu:
        lines.append(f"LOCATION:{_ics_escape(lieu)}")
    visio = str(meta_ev.get("visio") or "").strip()
    if visio:
        lines.append(f"URL:{_ics_escape(visio)}")
    if meta_ev.get("annule"):
        lines.append("STATUS:CANCELLED")
    debut = _parse_ev_dt_for_ics(ev.get("debut") or "")
    fin = _parse_ev_dt_for_ics(ev.get("fin") or "") or debut
    if not debut:
        lines.append("END:VEVENT")
        return lines
    if ev.get("all_day"):
        start_d = debut.date()
        end_d = (fin or debut).date()
        if end_d < start_d:
            end_d = start_d
        end_exclusive = end_d + timedelta(days=1)
        lines.append(f"DTSTART;VALUE=DATE:{start_d.strftime('%Y%m%d')}")
        lines.append(f"DTEND;VALUE=DATE:{end_exclusive.strftime('%Y%m%d')}")
    else:
        if not fin or fin < debut:
            fin = debut
        lines.append(
            f"DTSTART;TZID={ICS_TZID}:{debut.strftime('%Y%m%dT%H%M%S')}"
        )
        lines.append(f"DTEND;TZID={ICS_TZID}:{fin.strftime('%Y%m%dT%H%M%S')}")
        rappel = meta_ev.get("rappel_minutes")
        if rappel is None:
            rappel = RAPPEL_AVANT_MINUTES
        try:
            rappel = int(rappel)
        except (TypeError, ValueError):
            rappel = RAPPEL_AVANT_MINUTES
        if rappel > 0:
            lines.extend(
                [
                    "BEGIN:VALARM",
                    "ACTION:DISPLAY",
                    f"DESCRIPTION:{titre}",
                    f"TRIGGER:-PT{rappel}M",
                    "END:VALARM",
                ]
            )
    lines.append("END:VEVENT")
    return lines


# Les creneaux sont stockes en heure de Paris sans fuseau. Publies tels quels,
# ils etaient lus comme des heures « flottantes » : un destinataire a Londres
# voyait la reunion a 9 h chez lui. On declare donc le fuseau, avec ses regles
# de changement d'heure, et on y rattache chaque DTSTART / DTEND.
ICS_TZID = "Europe/Paris"
ICS_VTIMEZONE = [
    "BEGIN:VTIMEZONE",
    f"TZID:{ICS_TZID}",
    "X-LIC-LOCATION:Europe/Paris",
    "BEGIN:DAYLIGHT",
    "TZOFFSETFROM:+0100",
    "TZOFFSETTO:+0200",
    "TZNAME:CEST",
    "DTSTART:19700329T020000",
    "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU",
    "END:DAYLIGHT",
    "BEGIN:STANDARD",
    "TZOFFSETFROM:+0200",
    "TZOFFSETTO:+0100",
    "TZNAME:CET",
    "DTSTART:19701025T030000",
    "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU",
    "END:STANDARD",
    "END:VTIMEZONE",
]


def build_ics_calendar(
    events: list[dict],
    *,
    nom: Optional[str] = None,
    ttl_minutes: int = 60,
    methode: str = "PUBLISH",
) -> str:
    ttl = max(15, int(ttl_minutes or 60))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//MySifa//MyCalendrier//FR",
        "CALSCALE:GREGORIAN",
        f"METHOD:{methode}",
        f"X-WR-CALNAME:{_ics_escape(nom or 'MySifa')}",
        "X-WR-TIMEZONE:Europe/Paris",
        f"REFRESH-INTERVAL;VALUE=DURATION:PT{ttl}M",
        f"X-PUBLISHED-TTL:PT{ttl}M",
        *ICS_VTIMEZONE,
    ]
    for ev in events:
        for line in _event_to_vevent_lines(ev):
            lines.append(_fold_ics_line(line))
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


@router.get("/api/calendrier/events")
def list_events(
    request: Request,
    date_debut: str = Query(..., description="YYYY-MM-DD"),
    date_fin: str = Query(..., description="YYYY-MM-DD"),
    calendriers: str = Query(
        DEFAULT_CALENDARS,
        description="Liste séparée par des virgules",
    ),
):
    user, d0, d1, cals = _calendar_request_context(
        request, date_debut, date_fin, calendriers
    )
    if not cals:
        return {"events": [], "day_windows": {}}
    events, day_windows = _fetch_calendar_events(user, d0, d1, cals)
    return {"events": events, "day_windows": day_windows}


@router.get("/api/calendrier/export.ics")
def export_ics(
    request: Request,
    date_debut: str = Query(..., description="YYYY-MM-DD"),
    date_fin: str = Query(..., description="YYYY-MM-DD"),
    calendriers: str = Query(
        DEFAULT_CALENDARS,
        description="Liste séparée par des virgules",
    ),
):
    user, d0, d1, cals = _calendar_request_context(
        request, date_debut, date_fin, calendriers
    )
    events: list[dict] = []
    if cals:
        events, _ = _fetch_calendar_events(user, d0, d1, cals)
    body = build_ics_calendar(events, nom="MySifa")
    return Response(
        content=body.encode("utf-8"),
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="mysifa-calendrier.ics"',
        },
    )


@router.post("/api/calendrier/events/perso")
def create_perso_event(request: Request, body: PersoEventCreate):
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    titre = body.titre.strip()
    if not titre:
        raise HTTPException(400, detail="titre est requis.")
    dt_debut = _parse_event_dt(body.date_debut, "date_debut")
    dt_fin = _parse_event_dt(body.date_fin, "date_fin")
    if dt_fin < dt_debut:
        raise HTTPException(400, detail="date_fin doit être >= date_debut.")
    note = (body.note or "").strip() or None
    all_day = 1 if body.all_day else 0
    prive = 1 if body.prive else 0
    lieu = (body.lieu or "").strip() or None
    visio = (body.visio or "").strip() or None
    rappel = _valider_rappel(body.rappel_minutes)
    emails_ext = _emails_valides(body.invites_externes)
    debut_s = _fmt_dt(dt_debut)
    fin_s = _fmt_dt(dt_fin)
    regle, regle_fin = _valider_recurrence(
        body.recurrence, body.recurrence_fin, dt_debut
    )
    creneaux = (
        occurrences_serie(dt_debut, dt_fin, regle, regle_fin)
        if regle
        else [(dt_debut, dt_fin)]
    )
    serie_id = secrets.token_hex(8) if regle else None
    with get_db() as conn:
        proprietaire = _resoudre_proprietaire(conn, uid, body.au_nom_de)
        ids: list[int] = []
        for c_debut, c_fin in creneaux:
            cur = conn.execute(
                """
                INSERT INTO cal_events_perso
                    (user_id, titre, date_debut, date_fin, all_day, note, prive,
                     serie_id, recurrence, lieu, visio, rappel_minutes, cree_par)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proprietaire,
                    titre,
                    _fmt_dt(c_debut),
                    _fmt_dt(c_fin),
                    all_day,
                    note,
                    prive,
                    serie_id,
                    regle,
                    lieu,
                    visio,
                    rappel,
                    uid if proprietaire != uid else None,
                ),
            )
            ids.append(int(cur.lastrowid))
        new_id = ids[0]
        nouveaux_ext: list[dict] = []
        if body.participants or emails_ext:
            # Chaque occurrence porte ses propres invites : une reponse vaut
            # pour une date, pas pour la serie entiere.
            for eid in ids:
                if body.participants:
                    _ecrire_participants(conn, eid, proprietaire, body.participants)
                if emails_ext:
                    crees = _ecrire_invites_ext(conn, eid, emails_ext)
                    if eid == new_id:
                        nouveaux_ext = crees
        organisateur_nom, organisateur_email = _identite_utilisateur(
            conn, proprietaire
        )
        conn.commit()
        invites = _participants_par_event(conn, [new_id]).get(new_id, [])
        invites_ext = _invites_ext_par_event(conn, [new_id]).get(new_id, [])
    meta: dict[str, Any] = {
        "own": proprietaire == uid,
        "prive": bool(prive),
        "user_id": proprietaire,
    }
    if note:
        meta["note"] = note
    if lieu:
        meta["lieu"] = lieu
    if visio:
        meta["visio"] = visio
    if rappel is not None:
        meta["rappel_minutes"] = rappel
    if proprietaire != uid:
        meta["cree_par_moi"] = True
    if invites or invites_ext:
        meta["reunion"] = True
        meta["organisateur_id"] = proprietaire
        meta["organisateur_nom"] = organisateur_nom
        meta["organisateur_email"] = organisateur_email
        meta["mon_statut"] = "organisateur"
        meta["participants"] = invites
        meta["invites_externes"] = invites_ext
        _notifier_invitation([p["user_id"] for p in invites], titre, debut_s)
        _envoyer_invitation_email(
            destinataires=[
                {"email": p.get("email")} for p in invites if p.get("email")
            ]
            + nouveaux_ext,
            ev_ics=_ev_pour_ics(
                event_id=new_id,
                titre=titre,
                debut=debut_s,
                fin=fin_s,
                all_day=bool(all_day),
                meta=meta,
            ),
            titre=titre,
            debut=debut_s,
            fin=fin_s,
            all_day=bool(all_day),
            organisateur=organisateur_nom,
            lieu=lieu or "",
            visio=visio or "",
            note=note or "",
            participants=", ".join(
                p.get("nom") or p.get("email") or ""
                for p in (invites + invites_ext)
            ),
        )
    if serie_id:
        meta["serie_id"] = serie_id
        meta["recurrence"] = regle
        meta["occurrences"] = len(creneaux)
    return {
        "id": f"perso-{new_id}",
        "calendrier": CALENDRIER_PERSO_CAL,
        "titre": titre,
        "debut": debut_s,
        "fin": fin_s,
        "all_day": bool(all_day),
        "meta": meta,
    }


@router.delete("/api/calendrier/events/perso/{event_id}")
def delete_perso_event(
    request: Request,
    event_id: int,
    serie: bool = Query(False, description="Toute la série à partir de ce créneau"),
):
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    with get_db() as conn:
        row = conn.execute(
            """SELECT id, COALESCE(annule, 0) AS annule, serie_id, date_debut
                 FROM cal_events_perso WHERE id = ? AND user_id = ?""",
            (event_id, uid),
        ).fetchone()
        if not row:
            raise HTTPException(404, detail="Événement introuvable.")

        # Serie : on n'agit que sur ce creneau et les suivants — le passe reste
        # au calendrier, c'est de l'historique.
        cibles = [event_id]
        if serie and row["serie_id"]:
            cibles = [
                int(r["id"])
                for r in conn.execute(
                    """SELECT id FROM cal_events_perso
                        WHERE serie_id = ? AND user_id = ? AND date_debut >= ?""",
                    (row["serie_id"], uid, row["date_debut"]),
                ).fetchall()
            ]
        if len(cibles) > 1:
            marks = ",".join("?" for _ in cibles)
            nb_invites = int(
                conn.execute(
                    f"SELECT COUNT(*) FROM cal_event_participants "
                    f"WHERE event_id IN ({marks})",
                    tuple(cibles),
                ).fetchone()[0]
            ) + int(
                conn.execute(
                    f"SELECT COUNT(*) FROM cal_event_invites_ext "
                    f"WHERE event_id IN ({marks})",
                    tuple(cibles),
                ).fetchone()[0]
            )
            deja_annule = int(
                conn.execute(
                    f"SELECT COUNT(*) FROM cal_events_perso "
                    f"WHERE id IN ({marks}) AND COALESCE(annule, 0) = 0",
                    tuple(cibles),
                ).fetchone()[0]
            ) == 0
            if nb_invites and not deja_annule:
                _prevenir_annulation(conn, cibles)
                conn.execute(
                    f"""UPDATE cal_events_perso
                           SET annule = 1,
                               updated_at = strftime('%Y-%m-%dT%H:%M:%S','now','localtime')
                         WHERE id IN ({marks})""",
                    tuple(cibles),
                )
                conn.commit()
                return {"ok": True, "annule": True, "occurrences": len(cibles)}
            if not deja_annule:
                _prevenir_annulation(conn, cibles)
            conn.execute(
                f"DELETE FROM cal_event_participants WHERE event_id IN ({marks})",
                tuple(cibles),
            )
            conn.execute(
                f"DELETE FROM cal_event_invites_ext WHERE event_id IN ({marks})",
                tuple(cibles),
            )
            conn.execute(
                f"DELETE FROM cal_events_perso WHERE id IN ({marks})", tuple(cibles)
            )
            conn.commit()
            return {"ok": True, "annule": False, "occurrences": len(cibles)}

        nb_invites = int(
            conn.execute(
                "SELECT COUNT(*) FROM cal_event_participants WHERE event_id = ?",
                (event_id,),
            ).fetchone()[0]
        ) + int(
            conn.execute(
                "SELECT COUNT(*) FROM cal_event_invites_ext WHERE event_id = ?",
                (event_id,),
            ).fetchone()[0]
        )
        # Une reunion suivie par d'autres ne disparait pas sans un mot : on
        # l'annule d'abord, les invites la voient barree. Une seconde
        # suppression la retire pour de bon.
        if nb_invites and not int(row["annule"] or 0):
            _prevenir_annulation(conn, [event_id])
            conn.execute(
                """UPDATE cal_events_perso
                      SET annule = 1,
                          updated_at = strftime('%Y-%m-%dT%H:%M:%S','now','localtime')
                    WHERE id = ?""",
                (event_id,),
            )
            conn.commit()
            return {"ok": True, "annule": True}
        if not int(row["annule"] or 0):
            _prevenir_annulation(conn, [event_id])
        conn.execute(
            "DELETE FROM cal_event_participants WHERE event_id = ?", (event_id,)
        )
        conn.execute(
            "DELETE FROM cal_event_invites_ext WHERE event_id = ?", (event_id,)
        )
        conn.execute("DELETE FROM cal_events_perso WHERE id = ?", (event_id,))
        conn.commit()
    return {"ok": True, "annule": False, "occurrences": 1}


# ---------------------------------------------------------------------------
# Édition d'un créneau personnel
# ---------------------------------------------------------------------------


@router.put("/api/calendrier/events/perso/{event_id}")
def update_perso_event(request: Request, event_id: int, body: PersoEventUpdate):
    """Mise à jour partielle d'un créneau personnel (propriétaire uniquement)."""
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT id, titre, date_debut, date_fin, all_day, note, prive, serie_id,
                   lieu, visio, rappel_minutes
            FROM cal_events_perso
            WHERE id = ? AND user_id = ?
            """,
            (event_id, uid),
        ).fetchone()
        if not row:
            raise HTTPException(404, detail="Événement introuvable.")

        titre = (row["titre"] or "").strip()
        if body.titre is not None:
            titre = body.titre.strip()
            if not titre:
                raise HTTPException(400, detail="titre est requis.")

        all_day = bool(int(row["all_day"] or 0))
        if body.all_day is not None:
            all_day = bool(body.all_day)

        dt_debut = _parse_event_dt(
            body.date_debut if body.date_debut is not None else row["date_debut"],
            "date_debut",
        )
        dt_fin = _parse_event_dt(
            body.date_fin if body.date_fin is not None else row["date_fin"],
            "date_fin",
        )
        if dt_fin < dt_debut:
            raise HTTPException(400, detail="date_fin doit être >= date_debut.")

        note = row["note"]
        if body.note is not None:
            note = body.note.strip() or None

        prive = bool(int(row["prive"] or 0))
        if body.prive is not None:
            prive = bool(body.prive)

        lieu = row["lieu"]
        if body.lieu is not None:
            lieu = body.lieu.strip() or None
        visio = row["visio"]
        if body.visio is not None:
            visio = body.visio.strip() or None
        rappel = row["rappel_minutes"]
        if body.rappel_minutes is not None:
            rappel = _valider_rappel(body.rappel_minutes)

        debut_s = _fmt_dt(dt_debut)
        fin_s = _fmt_dt(dt_fin)
        avant = {
            int(r["user_id"])
            for r in conn.execute(
                "SELECT user_id FROM cal_event_participants WHERE event_id = ?",
                (event_id,),
            ).fetchall()
        }
        conn.execute(
            """
            UPDATE cal_events_perso
               SET titre = ?, date_debut = ?, date_fin = ?, all_day = ?,
                   note = ?, prive = ?, lieu = ?, visio = ?, rappel_minutes = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%S','now','localtime')
             WHERE id = ? AND user_id = ?
            """,
            (
                titre,
                debut_s,
                fin_s,
                1 if all_day else 0,
                note,
                1 if prive else 0,
                lieu,
                visio,
                rappel,
                event_id,
                uid,
            ),
        )
        if body.participants is not None:
            _ecrire_participants(conn, event_id, uid, body.participants)
        nouveaux_ext: list[dict] = []
        if body.invites_externes is not None:
            nouveaux_ext = _ecrire_invites_ext(
                conn, event_id, _emails_valides(body.invites_externes)
            )
        # Deplacer une reunion remet tout le monde en attente : une reponse
        # donnee sur l'ancien creneau ne vaut pas pour le nouveau.
        creneau_change = (
            body.date_debut is not None or body.date_fin is not None
        ) and (debut_s != str(row["date_debut"] or "") or fin_s != str(row["date_fin"] or ""))
        if creneau_change:
            conn.execute(
                """UPDATE cal_event_participants
                      SET statut = 'en_attente', repondu_le = NULL
                    WHERE event_id = ?""",
                (event_id,),
            )
        # « Toute la série » : les occurrences suivantes gardent leur date mais
        # prennent l'horaire, la durée et le contenu de celle qu'on vient de
        # modifier. Le passé n'est pas réécrit.
        occurrences = 1
        if body.serie and row["serie_id"]:
            duree = dt_fin - dt_debut
            suivantes = conn.execute(
                """SELECT id, date_debut FROM cal_events_perso
                    WHERE serie_id = ? AND user_id = ? AND id <> ?
                      AND date_debut >= ?""",
                (row["serie_id"], uid, event_id, str(row["date_debut"] or "")),
            ).fetchall()
            for suiv in suivantes:
                base = _parse_planned_dt(suiv["date_debut"])
                if not base:
                    continue
                n_debut = base.replace(
                    hour=dt_debut.hour, minute=dt_debut.minute, second=0, microsecond=0
                )
                n_fin = n_debut + duree
                conn.execute(
                    """UPDATE cal_events_perso
                          SET titre = ?, date_debut = ?, date_fin = ?, all_day = ?,
                              note = ?, prive = ?, lieu = ?, visio = ?,
                              rappel_minutes = ?,
                              updated_at = strftime('%Y-%m-%dT%H:%M:%S','now','localtime')
                        WHERE id = ?""",
                    (
                        titre,
                        _fmt_dt(n_debut),
                        _fmt_dt(n_fin),
                        1 if all_day else 0,
                        note,
                        1 if prive else 0,
                        lieu,
                        visio,
                        rappel,
                        int(suiv["id"]),
                    ),
                )
                if body.participants is not None:
                    _ecrire_participants(conn, int(suiv["id"]), uid, body.participants)
                if body.invites_externes is not None:
                    _ecrire_invites_ext(
                        conn, int(suiv["id"]), _emails_valides(body.invites_externes)
                    )
                if creneau_change:
                    conn.execute(
                        """UPDATE cal_event_participants
                              SET statut = 'en_attente', repondu_le = NULL
                            WHERE event_id = ?""",
                        (int(suiv["id"]),),
                    )
                occurrences += 1
        organisateur_nom, organisateur_email = _identite_utilisateur(conn, uid)
        conn.commit()
        invites = _participants_par_event(conn, [event_id]).get(event_id, [])
        invites_ext = _invites_ext_par_event(conn, [event_id]).get(event_id, [])

    meta: dict[str, Any] = {"own": True, "prive": prive, "user_id": uid}
    if lieu:
        meta["lieu"] = lieu
    if visio:
        meta["visio"] = visio
    if rappel is not None:
        meta["rappel_minutes"] = rappel
    if row["serie_id"]:
        meta["serie_id"] = row["serie_id"]
        meta["occurrences"] = occurrences
    if note:
        meta["note"] = note
    if invites or invites_ext:
        meta["reunion"] = True
        meta["organisateur_id"] = uid
        meta["organisateur_nom"] = organisateur_nom
        meta["organisateur_email"] = organisateur_email
        meta["mon_statut"] = "organisateur"
        meta["participants"] = invites
        meta["invites_externes"] = invites_ext
        nouveaux = [p["user_id"] for p in invites if p["user_id"] not in avant]
        _notifier_invitation(nouveaux, titre, debut_s)
        # Un creneau deplace vaut une nouvelle invitation pour tout le monde :
        # sans cela, le .ics reste sur l'ancien horaire dans leur Outlook.
        cibles_mail = (
            [{"email": p.get("email")} for p in invites if p.get("email")]
            if creneau_change
            else [
                {"email": p.get("email")}
                for p in invites
                if p.get("email") and p["user_id"] in nouveaux
            ]
        ) + nouveaux_ext
        _envoyer_invitation_email(
            destinataires=cibles_mail,
            ev_ics=_ev_pour_ics(
                event_id=event_id,
                titre=titre,
                debut=debut_s,
                fin=fin_s,
                all_day=all_day,
                meta=meta,
            ),
            titre=titre,
            debut=debut_s,
            fin=fin_s,
            all_day=all_day,
            organisateur=organisateur_nom,
            lieu=lieu or "",
            visio=visio or "",
            note=note or "",
            participants=", ".join(
                p.get("nom") or p.get("email") or ""
                for p in (invites + invites_ext)
            ),
        )
    return {
        "id": f"perso-{event_id}",
        "calendrier": CALENDRIER_PERSO_CAL,
        "titre": titre,
        "debut": debut_s,
        "fin": fin_s,
        "all_day": all_day,
        "meta": meta,
    }


# ---------------------------------------------------------------------------
# Reunions : invites et reponses
# ---------------------------------------------------------------------------


@router.get("/api/calendrier/invitables")
def list_invitables(request: Request):
    """Personnes que l'on peut convier a une reunion."""
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    with get_db() as conn:
        gens = _users_invitables(conn)
    return {"utilisateurs": [g for g in gens if g["id"] != uid]}


@router.get("/api/calendrier/disponibilites")
def list_disponibilites(
    request: Request,
    date_debut: str = Query(..., description="YYYY-MM-DDTHH:MM"),
    date_fin: str = Query(..., description="YYYY-MM-DDTHH:MM"),
    utilisateurs: str = Query("", description="Ids separes par des virgules"),
):
    """Qui est deja pris sur ce creneau — affiche au moment d'inviter."""
    require_calendrier(request)
    dt_debut = _parse_event_dt(date_debut, "date_debut")
    dt_fin = _parse_event_dt(date_fin, "date_fin")
    if dt_fin < dt_debut:
        raise HTTPException(400, detail="date_fin doit être >= date_debut.")
    ids: list[int] = []
    for part in str(utilisateurs or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            continue
    ids = sorted(set(ids))[:100]
    if not ids:
        return {"occupes": []}
    debut_s = _fmt_dt(dt_debut)
    fin_s = _fmt_dt(dt_fin)
    marks = ",".join("?" for _ in ids)
    with get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT DISTINCT q.user_id
            FROM (
                SELECT e.user_id AS user_id, e.date_debut, e.date_fin, e.annule
                  FROM cal_events_perso e
                UNION ALL
                SELECT p.user_id AS user_id, e.date_debut, e.date_fin, e.annule
                  FROM cal_event_participants p
                  JOIN cal_events_perso e ON e.id = p.event_id
                 WHERE p.statut <> 'refuse'
            ) q
            WHERE q.user_id IN ({marks})
              AND COALESCE(q.annule, 0) = 0
              AND q.date_debut < ?
              AND q.date_fin > ?
            """,
            (*ids, fin_s, debut_s),
        ).fetchall()
    return {"occupes": [int(r["user_id"]) for r in rows]}


@router.post("/api/calendrier/events/perso/{event_id}/reponse")
def repondre_invitation(request: Request, event_id: int, body: ParticipantReponse):
    """Un invite accepte, refuse ou repond « peut-etre »."""
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    statut = (body.statut or "").strip()
    if statut not in STATUTS_PARTICIPANT:
        raise HTTPException(
            400,
            detail="statut attendu : en_attente, accepte, refuse ou peut_etre.",
        )
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM cal_event_participants WHERE event_id = ? AND user_id = ?",
            (event_id, uid),
        ).fetchone()
        if not row:
            raise HTTPException(404, detail="Vous n'êtes pas invité à cette réunion.")
        conn.execute(
            """UPDATE cal_event_participants
                  SET statut = ?,
                      repondu_le = strftime('%Y-%m-%dT%H:%M:%S','now','localtime')
                WHERE event_id = ? AND user_id = ?""",
            (statut, event_id, uid),
        )
        conn.commit()
        invites = _participants_par_event(conn, [event_id]).get(event_id, [])
    return {"ok": True, "statut": statut, "participants": invites}


# ---------------------------------------------------------------------------
# Contre-propositions d'horaire
# ---------------------------------------------------------------------------


@router.post("/api/calendrier/events/perso/{event_id}/proposition")
def proposer_horaire(request: Request, event_id: int, body: PropositionCreate):
    """Un invite propose un autre creneau au lieu de refuser sans explication."""
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    dt_debut = _parse_event_dt(body.date_debut, "date_debut")
    dt_fin = _parse_event_dt(body.date_fin, "date_fin")
    if dt_fin <= dt_debut:
        raise HTTPException(400, detail="date_fin doit être après date_debut.")
    with get_db() as conn:
        invite = conn.execute(
            "SELECT 1 FROM cal_event_participants WHERE event_id = ? AND user_id = ?",
            (event_id, uid),
        ).fetchone()
        if not invite:
            raise HTTPException(404, detail="Vous n'êtes pas invité à cette réunion.")
        # Une seule proposition ouverte par personne : la nouvelle remplace
        # l'ancienne, sinon l'organisateur arbitre entre trois avis du meme.
        conn.execute(
            """DELETE FROM cal_event_propositions
                WHERE event_id = ? AND user_id = ? AND statut = 'proposee'""",
            (event_id, uid),
        )
        conn.execute(
            """INSERT INTO cal_event_propositions
                   (event_id, user_id, date_debut, date_fin, message)
               VALUES (?, ?, ?, ?, ?)""",
            (
                event_id,
                uid,
                _fmt_dt(dt_debut),
                _fmt_dt(dt_fin),
                (body.message or "").strip() or None,
            ),
        )
        conn.execute(
            """UPDATE cal_event_participants
                  SET statut = 'peut_etre',
                      repondu_le = strftime('%Y-%m-%dT%H:%M:%S','now','localtime')
                WHERE event_id = ? AND user_id = ? AND statut = 'en_attente'""",
            (event_id, uid),
        )
        organisateur = conn.execute(
            "SELECT user_id, titre FROM cal_events_perso WHERE id = ?", (event_id,)
        ).fetchone()
        conn.commit()
        props = _propositions_par_event(conn, [event_id]).get(event_id, [])
    if organisateur:
        _notifier_invitation(
            [int(organisateur["user_id"])],
            f"Nouvel horaire proposé — {organisateur['titre']}",
            _fmt_dt(dt_debut),
        )
    return {"ok": True, "propositions": props}


@router.post("/api/calendrier/events/perso/{event_id}/proposition/{prop_id}")
def arbitrer_proposition(
    request: Request,
    event_id: int,
    prop_id: int,
    accepter: bool = Query(True, description="Accepter (défaut) ou écarter"),
):
    """L'organisateur retient la contre-proposition, ou l'écarte."""
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    with get_db() as conn:
        ev = conn.execute(
            "SELECT id FROM cal_events_perso WHERE id = ? AND user_id = ?",
            (event_id, uid),
        ).fetchone()
        if not ev:
            raise HTTPException(404, detail="Réunion introuvable.")
        prop = conn.execute(
            """SELECT id, date_debut, date_fin FROM cal_event_propositions
                WHERE id = ? AND event_id = ? AND statut = 'proposee'""",
            (prop_id, event_id),
        ).fetchone()
        if not prop:
            raise HTTPException(404, detail="Proposition introuvable.")
        if not accepter:
            conn.execute(
                "UPDATE cal_event_propositions SET statut = 'ecartee' WHERE id = ?",
                (prop_id,),
            )
            conn.commit()
            return {"ok": True, "deplacee": False}
        conn.execute(
            """UPDATE cal_events_perso
                  SET date_debut = ?, date_fin = ?,
                      updated_at = strftime('%Y-%m-%dT%H:%M:%S','now','localtime')
                WHERE id = ?""",
            (prop["date_debut"], prop["date_fin"], event_id),
        )
        conn.execute(
            "UPDATE cal_event_propositions SET statut = 'retenue' WHERE id = ?",
            (prop_id,),
        )
        # Nouvel horaire : chacun redonne son accord.
        conn.execute(
            """UPDATE cal_event_participants
                  SET statut = 'en_attente', repondu_le = NULL
                WHERE event_id = ?""",
            (event_id,),
        )
        conn.execute(
            """UPDATE cal_event_invites_ext
                  SET statut = 'en_attente', repondu_le = NULL
                WHERE event_id = ?""",
            (event_id,),
        )
        conn.commit()
    return {"ok": True, "deplacee": True, "debut": prop["date_debut"]}


# ---------------------------------------------------------------------------
# Recherche
# ---------------------------------------------------------------------------


@router.get("/api/calendrier/recherche")
def rechercher_evenements(
    request: Request,
    q: str = Query(..., min_length=2, max_length=120),
    limite: int = Query(25, ge=1, le=60),
):
    """Cherche dans les créneaux visibles par l'utilisateur, à venir d'abord."""
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    motif = f"%{q.strip().lower()}%"
    aujourd_hui = date.today().isoformat()
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT e.id, e.titre, e.date_debut, e.date_fin, e.all_day, e.lieu,
                   e.user_id, COALESCE(e.annule, 0) AS annule, e.prive,
                   u.nom AS user_nom,
                   p.user_id AS invite
              FROM cal_events_perso e
              LEFT JOIN users u ON u.id = e.user_id
              LEFT JOIN cal_event_participants p
                     ON p.event_id = e.id AND p.user_id = ?
             WHERE (lower(e.titre) LIKE ? OR lower(COALESCE(e.note,'')) LIKE ?
                    OR lower(COALESCE(e.lieu,'')) LIKE ?)
               AND (e.user_id = ? OR p.user_id IS NOT NULL
                    OR COALESCE(e.prive, 0) = 0)
             ORDER BY (date(substr(e.date_debut,1,10)) < date(?)) ASC,
                      e.date_debut ASC
             LIMIT ?
            """,
            (uid, motif, motif, motif, uid, aujourd_hui, limite),
        ).fetchall()
    resultats = []
    for r in rows:
        a_moi = int(r["user_id"] or 0) == uid or r["invite"] is not None
        titre = (r["titre"] or "").strip() or "Sans titre"
        if not a_moi:
            titre = f"{(r['user_nom'] or '').strip()} · {titre}"
        resultats.append(
            {
                "id": f"perso-{r['id']}",
                "titre": titre,
                "debut": str(r["date_debut"] or "")[:16],
                "fin": str(r["date_fin"] or "")[:16],
                "all_day": bool(int(r["all_day"] or 0)),
                "lieu": (r["lieu"] or "").strip(),
                "annule": bool(int(r["annule"] or 0)),
                "a_moi": a_moi,
            }
        )
    return {"resultats": resultats}


# ---------------------------------------------------------------------------
# Delegations
# ---------------------------------------------------------------------------


@router.get("/api/calendrier/delegations")
def list_delegations(request: Request):
    """Qui peut écrire chez moi, et chez qui je peux écrire."""
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    with get_db() as conn:
        mes_delegues = [
            {"id": int(r["delegue_id"]), "nom": (r["nom"] or "").strip()}
            for r in conn.execute(
                """SELECT d.delegue_id, u.nom
                     FROM cal_delegations d
                     JOIN users u ON u.id = d.delegue_id
                    WHERE d.proprietaire_id = ?
                    ORDER BY u.nom COLLATE NOCASE ASC""",
                (uid,),
            ).fetchall()
        ]
        pour_moi = _calendriers_delegues(conn, uid)
    return {"mes_delegues": mes_delegues, "calendriers_delegues": pour_moi}


@router.post("/api/calendrier/delegations")
def create_delegation(request: Request, body: DelegationCreate):
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    cible = int(body.delegue_id)
    if cible == uid:
        raise HTTPException(400, detail="Vous avez déjà accès à votre calendrier.")
    with get_db() as conn:
        connus = {u["id"] for u in _users_invitables(conn)}
        if cible not in connus:
            raise HTTPException(400, detail="Cette personne n'a pas accès à MyCalendrier.")
        conn.execute(
            """INSERT OR IGNORE INTO cal_delegations (proprietaire_id, delegue_id)
               VALUES (?, ?)""",
            (uid, cible),
        )
        conn.commit()
        nom = _nom_utilisateur(conn, cible)
    return {"ok": True, "delegue": {"id": cible, "nom": nom}}


@router.delete("/api/calendrier/delegations/{delegue_id}")
def delete_delegation(request: Request, delegue_id: int):
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    with get_db() as conn:
        conn.execute(
            "DELETE FROM cal_delegations WHERE proprietaire_id = ? AND delegue_id = ?",
            (uid, delegue_id),
        )
        conn.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Invites externes : page publique de reponse
# ---------------------------------------------------------------------------


def _invitation_contexte(conn, jeton: str) -> dict:
    row = conn.execute(
        """SELECT i.email, i.statut, i.jeton, e.titre, e.date_debut, e.date_fin,
                  e.all_day, e.note, e.lieu, e.visio, COALESCE(e.annule,0) AS annule,
                  u.nom AS organisateur
             FROM cal_event_invites_ext i
             JOIN cal_events_perso e ON e.id = i.event_id
             LEFT JOIN users u ON u.id = e.user_id
            WHERE i.jeton = ?""",
        (jeton,),
    ).fetchone()
    if not row:
        raise HTTPException(404, detail="Invitation introuvable ou expirée.")
    return {
        "titre": (row["titre"] or "").strip() or "Réunion",
        "quand": _quand_lisible(
            str(row["date_debut"] or ""),
            str(row["date_fin"] or ""),
            bool(int(row["all_day"] or 0)),
        ),
        "organisateur": (row["organisateur"] or "").strip(),
        "lieu": (row["lieu"] or "").strip(),
        "visio": (row["visio"] or "").strip(),
        "note": (row["note"] or "").strip(),
        "statut": (row["statut"] or "en_attente").strip(),
        "jeton": row["jeton"],
        "annule": bool(int(row["annule"] or 0)),
    }


@router.get("/calendrier/invitation/{jeton}", response_class=HTMLResponse)
def page_invitation_externe(
    jeton: str,
    reponse: str = Query("", description="Réponse en un clic depuis l'e-mail"),
):
    """Page publique — l'invité externe n'a pas de compte MySifa.

    `?reponse=accepte` enregistre la réponse à l'ouverture : c'est ce que font
    les trois boutons de l'e-mail d'invitation, pour qu'un clic suffise.
    """
    from app.web.calendrier_invitation_page import page_invitation

    tok = str(jeton or "").strip()
    statut = str(reponse or "").strip()
    with get_db() as conn:
        ctx = _invitation_contexte(conn, tok)
        if statut in STATUTS_PARTICIPANT and not ctx["annule"]:
            conn.execute(
                """UPDATE cal_event_invites_ext
                      SET statut = ?,
                          repondu_le = strftime('%Y-%m-%dT%H:%M:%S','now','localtime')
                    WHERE jeton = ?""",
                (statut, tok),
            )
            conn.commit()
            ctx["statut"] = statut
    return HTMLResponse(page_invitation(ctx))


@router.post("/calendrier/invitation/{jeton}/reponse", response_class=HTMLResponse)
async def repondre_invitation_externe(jeton: str, request: Request):
    from app.web.calendrier_invitation_page import page_invitation

    form = await request.form()
    statut = str(form.get("statut") or "").strip()
    if statut not in STATUTS_PARTICIPANT:
        raise HTTPException(400, detail="Réponse invalide.")
    tok = str(jeton or "").strip()
    with get_db() as conn:
        ctx = _invitation_contexte(conn, tok)
        if not ctx["annule"]:
            conn.execute(
                """UPDATE cal_event_invites_ext
                      SET statut = ?,
                          repondu_le = strftime('%Y-%m-%dT%H:%M:%S','now','localtime')
                    WHERE jeton = ?""",
                (statut, tok),
            )
            conn.commit()
            ctx["statut"] = statut
    return HTMLResponse(page_invitation(ctx))


# ---------------------------------------------------------------------------
# Pop-up de rappel et pastille d'invitations (interrogees depuis tout MySifa)
# ---------------------------------------------------------------------------


@router.get("/api/calendrier/notifications")
def calendrier_notifications(request: Request):
    """Reunions dont le rappel est du, + invitations sans reponse.

    Interroge par toutes les pages du portail : un role sans acces a
    MyCalendrier recoit un contenu vide plutot qu'un 403, une pastille ne
    devant jamais faire echouer le chargement d'une page.
    """
    from services.auth_service import can_access_calendrier, get_current_user

    try:
        user = get_current_user(request)
    except HTTPException:
        return {"rappels": [], "invitations": 0}
    if not can_access_calendrier(user):
        return {"rappels": [], "invitations": 0}
    uid = _user_id_from_session(user)
    maintenant = _fmt_dt(datetime.now())
    with get_db() as conn:
        # Le delai de rappel appartient a l'evenement (NULL = defaut du
        # calendrier, 0 = aucun rappel) : la fenetre se calcule ligne par ligne.
        rows = conn.execute(
            """
            SELECT e.id, e.titre, e.date_debut, e.date_fin, e.user_id, e.lieu,
                   e.visio, COALESCE(e.rappel_minutes, ?) AS rappel,
                   u.nom AS organisateur_nom,
                   p.statut AS mon_statut,
                   (SELECT COUNT(*) FROM cal_event_participants x
                     WHERE x.event_id = e.id) AS nb_invites
              FROM cal_events_perso e
              LEFT JOIN users u ON u.id = e.user_id
              LEFT JOIN cal_event_participants p
                     ON p.event_id = e.id AND p.user_id = ?
             WHERE COALESCE(e.all_day, 0) = 0
               AND COALESCE(e.annule, 0) = 0
               AND COALESCE(e.rappel_minutes, ?) > 0
               AND e.date_debut >= ?
               AND datetime(e.date_debut) <=
                   datetime(?, '+' || COALESCE(e.rappel_minutes, ?) || ' minutes')
               AND (e.user_id = ? OR (p.user_id IS NOT NULL AND p.statut <> 'refuse'))
             ORDER BY e.date_debut ASC
             LIMIT 20
            """,
            (
                RAPPEL_AVANT_MINUTES,
                uid,
                RAPPEL_AVANT_MINUTES,
                maintenant,
                maintenant,
                RAPPEL_AVANT_MINUTES,
                uid,
            ),
        ).fetchall()
        rappels = [
            {
                "id": f"perso-{r['id']}",
                "titre": (r["titre"] or "").strip() or "Sans titre",
                "debut": str(r["date_debut"] or "")[:16],
                "fin": str(r["date_fin"] or "")[:16],
                "lieu": (r["lieu"] or "").strip(),
                "visio": (r["visio"] or "").strip(),
                "reunion": bool(int(r["nb_invites"] or 0)),
                "organisateur_nom": (r["organisateur_nom"] or "").strip(),
                "organisateur": int(r["user_id"] or 0) == uid,
                "mon_statut": (r["mon_statut"] or "") if r["mon_statut"] else "",
            }
            for r in rows
        ]
        nb = int(
            conn.execute(
                """SELECT COUNT(*)
                     FROM cal_event_participants p
                     JOIN cal_events_perso e ON e.id = p.event_id
                    WHERE p.user_id = ?
                      AND p.statut = 'en_attente'
                      AND COALESCE(e.annule, 0) = 0
                      AND date(substr(e.date_fin, 1, 10)) >= date('now','localtime')""",
                (uid,),
            ).fetchone()[0]
        )
    return {"rappels": rappels, "invitations": nb}


# ---------------------------------------------------------------------------
# Abonnements ICS entrants
# ---------------------------------------------------------------------------


def _valid_hex_color(value: Any) -> Optional[str]:
    s = str(value or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", s):
        return s.lower()
    return None


def _sub_public(row) -> dict:
    return {
        "id": int(row["id"]),
        "cal_id": f"sub_{int(row['id'])}",
        "nom": (row["nom"] or "").strip(),
        "url": (row["url"] or "").strip(),
        "couleur": (row["couleur"] or CAL_SUB_COLOR_DEFAULT),
        "actif": bool(int(row["actif"] or 0)),
        "last_sync_at": row["last_sync_at"],
        "last_status": row["last_status"],
        "last_error": row["last_error"],
        "nb_events": int(row["nb_events"] or 0),
    }


def _sub_is_stale(row) -> bool:
    if not (row["cache_ics"] or "").strip():
        return True
    raw = str(row["last_sync_at"] or "").strip()
    if not raw:
        return True
    try:
        last = datetime.fromisoformat(raw[:19])
    except ValueError:
        return True
    return (datetime.now() - last) > timedelta(minutes=CAL_SUB_TTL_MINUTES)


def _sync_subscription(
    conn, row, *, force: bool = False, timeout: int = CAL_SUB_TIMEOUT_S
) -> Optional[str]:
    """Rafraîchit le cache ICS d'un abonnement. Retourne le contenu utilisable."""
    cached = (row["cache_ics"] or "") if "cache_ics" in row.keys() else ""
    if not force and not _sub_is_stale(row):
        return cached
    now_s = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    try:
        text = fetch_ics(row["url"], timeout=timeout)
    except IcsError as e:
        conn.execute(
            """
            UPDATE cal_subscriptions
               SET last_sync_at = ?, last_status = 'erreur', last_error = ?
             WHERE id = ?
            """,
            (now_s, str(e)[:400], int(row["id"])),
        )
        conn.commit()
        return cached or None
    nb = text.upper().count("BEGIN:VEVENT")
    conn.execute(
        """
        UPDATE cal_subscriptions
           SET cache_ics = ?, last_sync_at = ?, last_status = 'ok',
               last_error = NULL, nb_events = ?
         WHERE id = ?
        """,
        (text, now_s, nb, int(row["id"])),
    )
    conn.commit()
    return text


def _subscription_events(
    conn, uid: int, sub_ids: list[int], d0: date, d1: date
) -> list[dict]:
    if not sub_ids:
        return []
    placeholders = ",".join("?" * len(sub_ids))
    rows = conn.execute(
        f"""
        SELECT * FROM cal_subscriptions
        WHERE user_id = ? AND actif = 1 AND id IN ({placeholders})
        ORDER BY id ASC
        """,
        [uid, *sub_ids],
    ).fetchall()
    out: list[dict] = []
    for row in rows:
        sub_id = int(row["id"])
        cal_key = f"sub_{sub_id}"
        try:
            text = _sync_subscription(conn, row)
        except Exception:
            text = row["cache_ics"]
        if not text:
            continue
        try:
            parsed = events_from_ics(text, d0, d1)
        except Exception:
            continue
        for idx, ev in enumerate(parsed):
            debut = ev["start"].strftime("%Y-%m-%dT%H:%M")
            fin = ev["end"].strftime("%Y-%m-%dT%H:%M")
            meta = {"source": (row["nom"] or "").strip(), "externe": True}
            if ev.get("location"):
                meta["lieu"] = ev["location"][:300]
            if ev.get("description"):
                meta["note"] = ev["description"][:1000]
            out.append(
                _event(
                    eid=f"sub-{sub_id}-{ev.get('occurrence_key') or idx}-{idx}",
                    cal=cal_key,
                    titre=ev.get("summary") or "Sans titre",
                    debut=debut,
                    fin=fin,
                    all_day=bool(ev.get("all_day")),
                    meta=meta,
                )
            )
    return out


@router.get("/api/calendrier/subscriptions")
def list_subscriptions(request: Request):
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM cal_subscriptions WHERE user_id = ? ORDER BY id ASC",
            (uid,),
        ).fetchall()
    return {"subscriptions": [_sub_public(r) for r in rows]}


@router.post("/api/calendrier/subscriptions")
def create_subscription(request: Request, body: SubscriptionCreate):
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    nom = body.nom.strip()
    if not nom:
        raise HTTPException(400, detail="nom est requis.")
    try:
        url = normalize_feed_url(body.url)
    except IcsError as e:
        raise HTTPException(400, detail=str(e))
    couleur = _valid_hex_color(body.couleur) or CAL_SUB_COLOR_DEFAULT
    with get_db() as conn:
        nb = conn.execute(
            "SELECT COUNT(*) AS n FROM cal_subscriptions WHERE user_id = ?", (uid,)
        ).fetchone()["n"]
        if int(nb or 0) >= CAL_SUB_MAX:
            raise HTTPException(
                400, detail=f"Limite atteinte — {CAL_SUB_MAX} abonnements maximum."
            )
        cur = conn.execute(
            """
            INSERT INTO cal_subscriptions (user_id, nom, url, couleur, actif)
            VALUES (?, ?, ?, ?, 1)
            """,
            (uid, nom, url, couleur),
        )
        conn.commit()
        new_id = int(cur.lastrowid)
        row = conn.execute(
            "SELECT * FROM cal_subscriptions WHERE id = ?", (new_id,)
        ).fetchone()
        _sync_subscription(conn, row, force=True, timeout=CAL_SUB_TIMEOUT_MANUEL_S)
        row = conn.execute(
            "SELECT * FROM cal_subscriptions WHERE id = ?", (new_id,)
        ).fetchone()
    payload = _sub_public(row)
    if payload["last_status"] == "erreur":
        payload["warning"] = payload["last_error"] or "Flux injoignable."
    return payload


@router.put("/api/calendrier/subscriptions/{sub_id}")
def update_subscription(request: Request, sub_id: int, body: SubscriptionUpdate):
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM cal_subscriptions WHERE id = ? AND user_id = ?",
            (sub_id, uid),
        ).fetchone()
        if not row:
            raise HTTPException(404, detail="Abonnement introuvable.")
        nom = (row["nom"] or "").strip()
        if body.nom is not None:
            nom = body.nom.strip()
            if not nom:
                raise HTTPException(400, detail="nom est requis.")
        url = row["url"]
        url_changed = False
        if body.url is not None:
            try:
                new_url = normalize_feed_url(body.url)
            except IcsError as e:
                raise HTTPException(400, detail=str(e))
            url_changed = new_url != url
            url = new_url
        couleur = row["couleur"] or CAL_SUB_COLOR_DEFAULT
        if body.couleur is not None:
            couleur = _valid_hex_color(body.couleur) or couleur
        actif = bool(int(row["actif"] or 0))
        if body.actif is not None:
            actif = bool(body.actif)
        conn.execute(
            """
            UPDATE cal_subscriptions
               SET nom = ?, url = ?, couleur = ?, actif = ?
             WHERE id = ? AND user_id = ?
            """,
            (nom, url, couleur, 1 if actif else 0, sub_id, uid),
        )
        if url_changed:
            conn.execute(
                """
                UPDATE cal_subscriptions
                   SET cache_ics = NULL, last_sync_at = NULL, last_status = NULL,
                       last_error = NULL, nb_events = 0
                 WHERE id = ?
                """,
                (sub_id,),
            )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM cal_subscriptions WHERE id = ?", (sub_id,)
        ).fetchone()
        if url_changed and actif:
            _sync_subscription(conn, row, force=True, timeout=CAL_SUB_TIMEOUT_MANUEL_S)
            row = conn.execute(
                "SELECT * FROM cal_subscriptions WHERE id = ?", (sub_id,)
            ).fetchone()
    return _sub_public(row)


@router.post("/api/calendrier/subscriptions/{sub_id}/refresh")
def refresh_subscription(request: Request, sub_id: int):
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM cal_subscriptions WHERE id = ? AND user_id = ?",
            (sub_id, uid),
        ).fetchone()
        if not row:
            raise HTTPException(404, detail="Abonnement introuvable.")
        _sync_subscription(conn, row, force=True, timeout=CAL_SUB_TIMEOUT_MANUEL_S)
        row = conn.execute(
            "SELECT * FROM cal_subscriptions WHERE id = ?", (sub_id,)
        ).fetchone()
    payload = _sub_public(row)
    if payload["last_status"] == "erreur":
        raise HTTPException(400, detail=payload["last_error"] or "Flux injoignable.")
    return payload


@router.delete("/api/calendrier/subscriptions/{sub_id}")
def delete_subscription(request: Request, sub_id: int):
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM cal_subscriptions WHERE id = ? AND user_id = ?",
            (sub_id, uid),
        ).fetchone()
        if not row:
            raise HTTPException(404, detail="Abonnement introuvable.")
        conn.execute("DELETE FROM cal_subscriptions WHERE id = ?", (sub_id,))
        conn.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Flux ICS sortant (abonnement depuis Outlook / Google / Apple)
# ---------------------------------------------------------------------------


def _feed_row(conn, uid: int):
    return conn.execute(
        "SELECT * FROM cal_feed_tokens WHERE user_id = ?", (uid,)
    ).fetchone()


def _ensure_feed_token(conn, uid: int):
    row = _feed_row(conn, uid)
    if row:
        return row
    conn.execute(
        """
        INSERT INTO cal_feed_tokens (user_id, token, calendriers, actif)
        VALUES (?, ?, ?, 1)
        """,
        (uid, secrets.token_urlsafe(32), FEED_DEFAULT_CALENDARS),
    )
    conn.commit()
    return _feed_row(conn, uid)


def _feed_base_url(request: Optional[Request]) -> str:
    """Hôte réellement appelé — évite de publier une URL de prod depuis v1."""
    host = ""
    if request is not None:
        host = str(request.headers.get("host") or request.url.hostname or "").strip()
    if not host:
        return public_base_url()
    low = host.lower()
    if low.startswith("localhost") or low.startswith("127.0.0.1"):
        return f"http://{host}"
    return f"https://{host}"


def _feed_payload(row, request: Optional[Request] = None) -> dict:
    url = f"{_feed_base_url(request)}/api/calendrier/feed/{row['token']}.ics"
    return {
        "token": row["token"],
        "url": url,
        "webcal_url": re.sub(r"^https?://", "webcal://", url),
        "calendriers": (row["calendriers"] or FEED_DEFAULT_CALENDARS),
        "actif": bool(int(row["actif"] or 0)),
        "last_access_at": row["last_access_at"],
        "hits": int(row["hits"] or 0),
        "fenetre": {"passe_jours": FEED_PAST_DAYS, "futur_jours": FEED_FUTURE_DAYS},
    }


@router.get("/api/calendrier/feed")
def get_feed(request: Request):
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    with get_db() as conn:
        row = _ensure_feed_token(conn, uid)
    return _feed_payload(row, request)


@router.put("/api/calendrier/feed")
def update_feed(request: Request, body: FeedUpdate):
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    role = str(user.get("role") or "")
    with get_db() as conn:
        row = _ensure_feed_token(conn, uid)
        cals_s = row["calendriers"] or FEED_DEFAULT_CALENDARS
        if body.calendriers is not None:
            requested = {c.strip() for c in body.calendriers.split(",") if c.strip()}
            kept = _filter_calendars_for_role(role, requested)
            kept = {c for c in kept if c in VALID_CALENDARS or SUB_CAL_RE.match(c)}
            if not kept:
                raise HTTPException(400, detail="Au moins un calendrier est requis.")
            cals_s = ",".join(sorted(kept))
        actif = bool(int(row["actif"] or 0))
        if body.actif is not None:
            actif = bool(body.actif)
        conn.execute(
            "UPDATE cal_feed_tokens SET calendriers = ?, actif = ? WHERE user_id = ?",
            (cals_s, 1 if actif else 0, uid),
        )
        conn.commit()
        row = _feed_row(conn, uid)
    return _feed_payload(row, request)


@router.post("/api/calendrier/feed/rotate")
def rotate_feed(request: Request):
    """Révoque l'URL d'abonnement en cours et en génère une nouvelle."""
    user = require_calendrier(request)
    uid = _user_id_from_session(user)
    with get_db() as conn:
        _ensure_feed_token(conn, uid)
        conn.execute(
            "UPDATE cal_feed_tokens SET token = ?, hits = 0, last_access_at = NULL "
            "WHERE user_id = ?",
            (secrets.token_urlsafe(32), uid),
        )
        conn.commit()
        row = _feed_row(conn, uid)
    return _feed_payload(row, request)


@router.get("/api/calendrier/feed/{token}.ics")
def feed_ics(token: str):
    """Flux ICS public protégé par jeton — consommé par un client calendrier."""
    tok = str(token or "").strip()
    if len(tok) < 20:
        raise HTTPException(404, detail="Flux introuvable.")
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT f.user_id, f.calendriers, f.actif, u.role, u.nom,
                   u.actif AS user_actif
            FROM cal_feed_tokens f
            JOIN users u ON u.id = f.user_id
            WHERE f.token = ?
            """,
            (tok,),
        ).fetchone()
        if not row or not int(row["actif"] or 0) or not int(row["user_actif"] or 0):
            raise HTTPException(404, detail="Flux introuvable.")
        conn.execute(
            "UPDATE cal_feed_tokens SET hits = hits + 1, "
            "last_access_at = strftime('%Y-%m-%dT%H:%M:%S','now','localtime') "
            "WHERE token = ?",
            (tok,),
        )
        conn.commit()
        feed_user = {"id": int(row["user_id"]), "role": str(row["role"] or "")}
        feed_nom = (row["nom"] or "").strip()
        requested = {
            c.strip()
            for c in str(row["calendriers"] or FEED_DEFAULT_CALENDARS).split(",")
            if c.strip()
        }

    cals = _filter_calendars_for_role(feed_user["role"], requested)
    today = date.today()
    d0 = today - timedelta(days=FEED_PAST_DAYS)
    d1 = today + timedelta(days=FEED_FUTURE_DAYS)
    events: list[dict] = []
    if cals:
        try:
            events, _ = _fetch_calendar_events(
                feed_user, d0, d1, cals, perso_own_only=True
            )
        except HTTPException:
            raise
        except Exception:
            events = []
    body = build_ics_calendar(
        events,
        nom=f"MySifa — {feed_nom}" if feed_nom else "MySifa",
        ttl_minutes=60,
    )
    return Response(
        content=body.encode("utf-8"),
        media_type="text/calendar; charset=utf-8",
        headers={"Cache-Control": "private, max-age=900"},
    )
