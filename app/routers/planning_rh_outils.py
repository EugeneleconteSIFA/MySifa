"""MySifa — Planning RH : outils du responsable.

Routes /api/rh/*
  * absences-seuils : nombre maximal d'absents simultanés par service ;
  * planning/generer : remplir les semaines suivantes depuis une semaine source,
    en suivant la rotation des équipes réglée par machine (mode_alternance) ;
  * publications : semaine provisoire / publiée, notification des personnes
    dont le planning a changé depuis la dernière publication ;
  * equite : nuits, samedis, matins, après-midi travaillés par personne et par an ;
  * notes-equipe : notes du responsable à l'attention d'une équipe (tous, un
    service, une machine) sur une plage de semaines.

La logique lit les attributs (mode_alternance de rh_machine_config, rôle de
l'utilisateur), jamais un nom ou un code de machine.
"""
import hashlib
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from app.routers.planning_rh import (
    JOURS_BIT_SAMEDI,
    JOURS_MASK_ALL,
    _filter_planning_rh_user_rows,
    _planning_rh_nom_excluded,
    _require_atelier_edit,
    _require_atelier_view,
    _require_conge_edit,
    _week_bounds,
)
from app.services.audit_service import log_action
from app.services.auth_service import get_current_user
from config import ROLE_LABELS
from database import get_db

router = APIRouter(prefix="/api/rh", tags=["planning_rh_outils"])

_ROLES_OPERATEURS = ("fabrication", "logistique", "expedition")
_CRENEAUX = {"matin": "Matin", "aprem": "Après-midi", "nuit": "Nuit", "journee": "Journée"}


def _ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


def _semaine_plus(semaine: str, n: int) -> str:
    lundi, _ = _week_bounds(semaine)
    y, w, _ = (lundi + timedelta(weeks=n)).isocalendar()
    return f"{y}-W{w:02d}"


def _push(user_id, titre: str, corps: str, url: str) -> int:
    try:
        from app.routers.push import send_push_safe
        return send_push_safe(user_id, title=titre, body=corps, url=url, tag="rh-planning")
    except Exception:
        return 0


# ── Seuils d'absences simultanées ────────────────────────────────
@router.get("/absences-seuils")
def get_seuils(request: Request):
    _require_conge_edit(request)
    with get_db() as conn:
        rows = {r["service"]: r["max_absents"] for r in conn.execute(
            "SELECT service, max_absents FROM rh_absences_seuils").fetchall()}
    services = list(ROLE_LABELS)
    return {"seuils": [
        {"service": s, "libelle": ROLE_LABELS.get(s, s), "max_absents": rows.get(s)}
        for s in services if s != "superadmin"
    ]}


@router.put("/absences-seuils")
async def set_seuils(request: Request):
    editor = _require_conge_edit(request)
    body = await request.json()
    seuils = body.get("seuils") or []
    if not isinstance(seuils, list):
        raise HTTPException(400, "Liste de seuils attendue.")
    maintenant = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        for s in seuils:
            service = str((s or {}).get("service") or "")
            if service not in ROLE_LABELS:
                raise HTTPException(400, f"Service inconnu : {service}")
            v = s.get("max_absents")
            if v in (None, ""):
                conn.execute("DELETE FROM rh_absences_seuils WHERE service = ?", (service,))
                continue
            try:
                n = int(v)
            except (TypeError, ValueError):
                raise HTTPException(400, "Seuil invalide — nombre entier attendu.")
            if n < 1 or n > 99:
                raise HTTPException(400, "Seuil invalide — entre 1 et 99.")
            conn.execute(
                """INSERT INTO rh_absences_seuils (service, max_absents, modifie_le, modifie_par)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(service) DO UPDATE SET max_absents = excluded.max_absents,
                       modifie_le = excluded.modifie_le, modifie_par = excluded.modifie_par""",
                (service, n, maintenant, editor.get("email")),
            )
        conn.commit()
    log_action(user=editor, action="UPDATE", module="rh",
               objet="Seuils d'absences simultanées", detail=seuils, ip=_ip(request))
    return get_seuils(request)


# ── Génération par rotation ──────────────────────────────────────
def _bits_conge(conn, user_id: int, semaine: str) -> int:
    """Jours (Lun=bit0 … Sam=bit5) couverts par un congé non refusé."""
    lundi, dimanche = _week_bounds(semaine)
    bits = 0
    for c in conn.execute(
        """SELECT date_debut, date_fin FROM rh_conges
            WHERE user_id = ? AND statut != 'refuse' AND date_debut <= ? AND date_fin >= ?""",
        (user_id, dimanche.isoformat(), lundi.isoformat()),
    ).fetchall():
        for i in range(6):
            j = (lundi + timedelta(days=i)).isoformat()
            if c["date_debut"] <= j <= c["date_fin"]:
                bits |= 1 << i
    return bits


@router.post("/planning/generer")
async def generer_planning(request: Request):
    """Recopie la semaine source sur les N suivantes.

    Machines en mode « alterne » : matin et après-midi s'inversent une semaine
    sur deux. Une personne déjà affectée sur la semaine cible est laissée telle
    quelle ; ses jours de congé sont retirés, et une semaine entière de congé
    l'écarte. `appliquer` à faux = aperçu sans rien écrire.
    """
    editor = _require_atelier_edit(request)
    body = await request.json()
    source = str(body.get("source") or "")
    _week_bounds(source)
    try:
        n = int(body.get("semaines") or 1)
    except (TypeError, ValueError):
        raise HTTPException(400, "Nombre de semaines invalide.")
    if n < 1 or n > 8:
        raise HTTPException(400, "Nombre de semaines invalide — entre 1 et 8.")
    appliquer = bool(body.get("appliquer"))

    with get_db() as conn:
        rows = conn.execute(
            """SELECT p.*, u.nom AS user_nom, u.actif, m.nom AS machine_nom
                 FROM rh_planning_postes p JOIN users u ON u.id = p.user_id
                 LEFT JOIN machines m ON m.id = p.machine_id
                WHERE p.semaine = ? ORDER BY u.nom COLLATE NOCASE""",
            (source,),
        ).fetchall()
        if not rows:
            raise HTTPException(400, f"Semaine source {source} vide — rien à recopier.")
        modes = {r["machine_id"]: r["mode_alternance"] for r in conn.execute(
            "SELECT machine_id, mode_alternance FROM rh_machine_config").fetchall()}

        creees, ignorees = [], []
        maintenant = datetime.now().isoformat(timespec="seconds")
        for i in range(1, n + 1):
            cible = _semaine_plus(source, i)
            occupes = {r["user_id"] for r in conn.execute(
                "SELECT DISTINCT user_id FROM rh_planning_postes WHERE semaine = ?", (cible,)).fetchall()}
            for r in rows:
                nom = r["user_nom"]
                if not r["actif"] or _planning_rh_nom_excluded(nom):
                    continue
                if r["user_id"] in occupes:
                    ignorees.append({"semaine": cible, "nom": nom, "raison": "déjà affecté(e)"})
                    continue
                creneau = r["creneau"]
                if modes.get(r["machine_id"]) == "alterne" and i % 2 == 1 and creneau in ("matin", "aprem"):
                    creneau = "aprem" if creneau == "matin" else "matin"
                prevus = int(r["jours"] or 31) & JOURS_MASK_ALL
                jours = prevus & ~_bits_conge(conn, r["user_id"], cible)
                # Tous les jours de semaine prévus tombent en congé : la personne
                # est absente cette semaine, son samedi éventuel ne se garde pas.
                if not jours & JOURS_MASK_ALL or (prevus & 31 and not jours & 31):
                    ignorees.append({"semaine": cible, "nom": nom, "raison": "en congé"})
                    continue
                creees.append({
                    "semaine": cible, "nom": nom, "machine": r["machine_nom"], "poste": r["poste"],
                    "creneau": _CRENEAUX.get(creneau, creneau),
                    "partiel": jours != (int(r["jours"] or 31) & JOURS_MASK_ALL),
                })
                if appliquer:
                    conn.execute(
                        """INSERT INTO rh_planning_postes
                               (user_id, semaine, machine_id, poste, creneau, jours, created_by, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (r["user_id"], cible, r["machine_id"], r["poste"], creneau, jours,
                         editor.get("email"), maintenant),
                    )
        if appliquer:
            conn.commit()
    if appliquer:
        log_action(user=editor, action="CREATE", module="rh",
                   objet=f"Planning généré depuis {source} sur {n} semaine(s) · {len(creees)} affectation(s)",
                   ip=_ip(request))
    return {"source": source, "semaines": n, "applique": appliquer, "creees": creees, "ignorees": ignorees}


# ── Publication ──────────────────────────────────────────────────
def _empreintes(conn, semaine: str) -> dict:
    """{user_id: (empreinte, résumé lisible)} des affectations de la semaine."""
    par_user: dict = {}
    for r in conn.execute(
        """SELECT p.user_id, u.nom, p.machine_id, m.nom AS machine_nom, p.poste, p.creneau, p.jours
             FROM rh_planning_postes p JOIN users u ON u.id = p.user_id
             LEFT JOIN machines m ON m.id = p.machine_id
            WHERE p.semaine = ?""",
        (semaine,),
    ).fetchall():
        if _planning_rh_nom_excluded(r["nom"]):
            continue
        par_user.setdefault(r["user_id"], {"nom": r["nom"], "cles": [], "resume": []})
        par_user[r["user_id"]]["cles"].append(f"{r['machine_id']}|{r['poste']}|{r['creneau']}|{r['jours']}")
        par_user[r["user_id"]]["resume"].append(
            " · ".join(x for x in (r["machine_nom"], _CRENEAUX.get(r["creneau"], r["creneau"])) if x))
    return {
        uid: (hashlib.sha1(";".join(sorted(v["cles"])).encode()).hexdigest()[:16], v["nom"], ", ".join(v["resume"]))
        for uid, v in par_user.items()
    }


def _etat_semaine(conn, semaine: str, detail: bool) -> dict:
    pub = conn.execute("SELECT * FROM rh_planning_publications WHERE semaine = ?", (semaine,)).fetchone()
    out = {"semaine": semaine, "publie_le": pub["publie_le"] if pub else None,
           "publie_par": pub["publie_par"] if pub else None, "version": pub["version"] if pub else 0}
    if detail:
        actuel = _empreintes(conn, semaine)
        publie = {r["user_id"]: r["empreinte"] for r in conn.execute(
            "SELECT user_id, empreinte FROM rh_planning_publie WHERE semaine = ?", (semaine,)).fetchall()}
        noms = {uid: v[1] for uid, v in actuel.items()}
        for r in conn.execute(
            """SELECT p.user_id, u.nom FROM rh_planning_publie p JOIN users u ON u.id = p.user_id
                WHERE p.semaine = ?""", (semaine,)).fetchall():
            noms.setdefault(r["user_id"], r["nom"])
        changes = [uid for uid in set(actuel) | set(publie)
                   if (actuel.get(uid) or (None,))[0] != publie.get(uid)]
        out["personnes"] = len(actuel)
        out["modifies"] = sorted(noms[u] for u in changes) if pub else []
    return out


@router.get("/publications")
def get_publications(request: Request, from_week: str, to_week: str = ""):
    user = _require_atelier_view(request)
    detail = user.get("role") not in _ROLES_OPERATEURS
    fin = to_week or from_week
    _week_bounds(from_week)
    _week_bounds(fin)
    semaines, s = [], from_week
    while s <= fin and len(semaines) < 12:
        semaines.append(s)
        s = _semaine_plus(s, 1)
    with get_db() as conn:
        return {"semaines": [_etat_semaine(conn, s, detail) for s in semaines]}


@router.post("/publications/{semaine}")
def publier_semaine(semaine: str, request: Request):
    """Publie la semaine et prévient chaque personne dont le planning a changé."""
    editor = _require_atelier_edit(request)
    _week_bounds(semaine)
    num = semaine.split("-W")[1]
    url = f"/planning-rh?semaine={semaine}"
    with get_db() as conn:
        pub = conn.execute("SELECT version FROM rh_planning_publications WHERE semaine = ?", (semaine,)).fetchone()
        actuel = _empreintes(conn, semaine)
        avant = {r["user_id"]: (r["empreinte"], r["nom"]) for r in conn.execute(
            """SELECT p.user_id, p.empreinte, u.nom FROM rh_planning_publie p
                 JOIN users u ON u.id = p.user_id WHERE p.semaine = ?""", (semaine,)).fetchall()}
        a_prevenir = []
        for uid, (emp, nom, resume) in actuel.items():
            if not pub or (avant.get(uid) or (None,))[0] != emp:
                a_prevenir.append((uid, nom, f"Semaine {num} : {resume}."))
        for uid, (_, nom) in avant.items():
            if uid not in actuel:
                a_prevenir.append((uid, nom, f"Vous n'êtes plus affecté(e) en semaine {num}."))
        maintenant = datetime.now().isoformat(timespec="seconds")
        version = (pub["version"] + 1) if pub else 1
        conn.execute(
            """INSERT INTO rh_planning_publications (semaine, publie_le, publie_par, version)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(semaine) DO UPDATE SET publie_le = excluded.publie_le,
                   publie_par = excluded.publie_par, version = excluded.version""",
            (semaine, maintenant, editor.get("nom") or editor.get("email"), version),
        )
        conn.execute("DELETE FROM rh_planning_publie WHERE semaine = ?", (semaine,))
        conn.executemany(
            "INSERT INTO rh_planning_publie (semaine, user_id, empreinte) VALUES (?, ?, ?)",
            [(semaine, uid, v[0]) for uid, v in actuel.items()],
        )
        conn.commit()
    titre = f"Planning semaine {num} " + ("modifié" if pub else "publié")
    envois = sum(_push(uid, titre, corps, url) for uid, _, corps in a_prevenir)
    log_action(user=editor, action="UPDATE", module="rh",
               objet=f"Planning {semaine} publié (version {version}) · {len(a_prevenir)} personne(s) prévenue(s)",
               ip=_ip(request))
    return {"semaine": semaine, "version": version, "prevenus": sorted(n for _, n, _ in a_prevenir),
            "envois_push": envois}


# ── Équité ───────────────────────────────────────────────────────
@router.get("/equite")
def get_equite(request: Request, annee: Optional[int] = None):
    """Jours travaillés par créneau et samedis, par personne, sur l'année.

    Un jour = un bit du masque `jours` d'une affectation. Opérateurs : leur
    seule ligne (comme /planning).
    """
    user = _require_atelier_view(request)
    an = int(annee or datetime.now().year)
    courante = "%d-W%02d" % date.today().isocalendar()[:2]
    q = """SELECT p.user_id, u.nom, p.semaine, p.creneau, p.jours
             FROM rh_planning_postes p JOIN users u ON u.id = p.user_id
            WHERE p.semaine LIKE ? AND u.actif = 1"""
    params: list = [f"{an}-W%"]
    if user.get("role") in _ROLES_OPERATEURS:
        q += " AND p.user_id = ?"
        params.append(user["id"])
    with get_db() as conn:
        rows = _filter_planning_rh_user_rows(conn.execute(q, params).fetchall(), "nom")
    par: dict = {}
    for r in rows:
        p = par.setdefault(r["user_id"], {
            "user_id": r["user_id"], "nom": r["nom"], "semaines": set(),
            "matin": 0, "aprem": 0, "nuit": 0, "journee": 0, "samedis": 0, "a_venir": 0,
        })
        jours = int(r["jours"] or 31) & JOURS_MASK_ALL
        n = bin(jours).count("1")
        p["semaines"].add(r["semaine"])
        cle = r["creneau"] if r["creneau"] in ("matin", "aprem", "nuit") else "journee"
        p[cle] += n
        if jours & JOURS_BIT_SAMEDI:
            p["samedis"] += 1
        if r["semaine"] > courante:
            p["a_venir"] += n
    out = []
    for p in par.values():
        p["semaines"] = len(p["semaines"])
        p["total"] = p["matin"] + p["aprem"] + p["nuit"] + p["journee"]
        out.append(p)
    out.sort(key=lambda x: x["nom"].lower())
    return {"annee": an, "personnes": out}


# ── Notes d'équipe ───────────────────────────────────────────────
_CIBLES = ("tous", "service", "machine")
_IMPORTANCES = ("info", "important")


def _note_dict(conn, r) -> dict:
    d = dict(r)
    if d["cible_type"] == "service":
        d["cible_libelle"] = ROLE_LABELS.get(d["cible_valeur"], d["cible_valeur"])
    elif d["cible_type"] == "machine":
        m = conn.execute("SELECT nom FROM machines WHERE id = ?", (d["cible_valeur"],)).fetchone()
        d["cible_libelle"] = m["nom"] if m else "Machine supprimée"
    else:
        d["cible_libelle"] = "Tout le monde"
    return d


def _destinataires(conn, cible_type: str, cible_valeur, sem_deb: str, sem_fin: str) -> list[int]:
    """Personnes concernées : service = rôle ; machine = affectées sur la plage."""
    if cible_type == "service":
        rows = conn.execute("SELECT id, nom FROM users WHERE actif = 1 AND role = ?", (cible_valeur,)).fetchall()
    elif cible_type == "machine":
        rows = conn.execute(
            """SELECT DISTINCT u.id, u.nom FROM rh_planning_postes p JOIN users u ON u.id = p.user_id
                WHERE u.actif = 1 AND p.machine_id = ? AND p.semaine BETWEEN ? AND ?""",
            (cible_valeur, sem_deb, sem_fin)).fetchall()
    else:
        rows = conn.execute(
            """SELECT DISTINCT u.id, u.nom FROM rh_planning_postes p JOIN users u ON u.id = p.user_id
                WHERE u.actif = 1 AND p.semaine BETWEEN ? AND ?""", (sem_deb, sem_fin)).fetchall()
    return [r["id"] for r in rows if not _planning_rh_nom_excluded(r["nom"])]


@router.get("/notes-equipe")
def get_notes_equipe(request: Request, from_week: str, to_week: str = ""):
    """Notes qui touchent la plage. Un opérateur ne reçoit que celles qui le visent."""
    user = get_current_user(request)
    fin = to_week or from_week
    _week_bounds(from_week)
    _week_bounds(fin)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM rh_notes_equipe WHERE semaine_debut <= ? AND semaine_fin >= ?
                ORDER BY CASE importance WHEN 'important' THEN 0 ELSE 1 END, semaine_debut, id DESC""",
            (fin, from_week)).fetchall()
        notes = [_note_dict(conn, r) for r in rows]
        if user.get("role") in _ROLES_OPERATEURS or not _peut_gerer_notes(user):
            mes_machines = {str(r["machine_id"]) for r in conn.execute(
                "SELECT DISTINCT machine_id FROM rh_planning_postes WHERE user_id = ? AND semaine BETWEEN ? AND ?",
                (user["id"], from_week, fin)).fetchall()}
            notes = [n for n in notes if n["cible_type"] == "tous"
                     or (n["cible_type"] == "service" and n["cible_valeur"] == user.get("role"))
                     or (n["cible_type"] == "machine" and str(n["cible_valeur"]) in mes_machines)]
    return {"notes": notes}


def _peut_gerer_notes(user: dict) -> bool:
    try:
        from app.routers.planning_rh import ROLES_PLANNING_RH_ATELIER_EDIT, _has_planning_rh_override
        email = (user.get("email") or "").strip().lower()
        return (user.get("role") in ROLES_PLANNING_RH_ATELIER_EDIT or _has_planning_rh_override(user)
                or email == "mlesaffre@sifa.pro")
    except Exception:
        return False


def _lire_note(conn, body: dict) -> dict:
    texte = str(body.get("texte") or "").strip()
    if not texte or len(texte) > 500:
        raise HTTPException(400, "Texte obligatoire — 500 caractères au plus.")
    deb = str(body.get("semaine_debut") or "")
    fin = str(body.get("semaine_fin") or deb)
    _week_bounds(deb)
    _week_bounds(fin)
    if fin < deb:
        raise HTTPException(400, "La semaine de fin doit suivre la semaine de début.")
    cible_type = str(body.get("cible_type") or "tous")
    if cible_type not in _CIBLES:
        raise HTTPException(400, "Destinataires invalides.")
    valeur = body.get("cible_valeur")
    if cible_type == "service":
        if str(valeur) not in ROLE_LABELS:
            raise HTTPException(400, "Service inconnu.")
        valeur = str(valeur)
    elif cible_type == "machine":
        try:
            valeur = int(valeur)
        except (TypeError, ValueError):
            raise HTTPException(400, "Machine invalide.")
        if not conn.execute("SELECT 1 FROM machines WHERE id = ?", (valeur,)).fetchone():
            raise HTTPException(400, "Machine introuvable.")
    else:
        valeur = None
    importance = str(body.get("importance") or "info")
    if importance not in _IMPORTANCES:
        importance = "info"
    return {"semaine_debut": deb, "semaine_fin": fin, "cible_type": cible_type,
            "cible_valeur": valeur, "texte": texte, "importance": importance}


@router.post("/notes-equipe")
async def create_note_equipe(request: Request):
    editor = _require_atelier_edit(request)
    body = await request.json()
    with get_db() as conn:
        n = _lire_note(conn, body)
        cur = conn.execute(
            """INSERT INTO rh_notes_equipe (semaine_debut, semaine_fin, cible_type, cible_valeur, texte,
                   importance, cree_le, cree_par, cree_par_nom) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (n["semaine_debut"], n["semaine_fin"], n["cible_type"], n["cible_valeur"], n["texte"],
             n["importance"], datetime.now().isoformat(timespec="seconds"), editor.get("email"),
             editor.get("nom")))
        conn.commit()
        out = _note_dict(conn, conn.execute("SELECT * FROM rh_notes_equipe WHERE id = ?",
                                            (cur.lastrowid,)).fetchone())
        dest = _destinataires(conn, n["cible_type"], n["cible_valeur"], n["semaine_debut"], n["semaine_fin"]) \
            if body.get("prevenir") else []
    num = n["semaine_debut"].split("-W")[1]
    for uid in dest:
        _push(uid, f"Note planning · semaine {num}", n["texte"][:180],
              f"/planning-rh?semaine={n['semaine_debut']}")
    out["prevenus"] = len(dest)
    log_action(user=editor, action="CREATE", module="rh",
               objet=f"Note d'équipe · {out['cible_libelle']} · {n['semaine_debut']}", ip=_ip(request))
    return out


@router.put("/notes-equipe/{note_id}")
async def update_note_equipe(note_id: int, request: Request):
    editor = _require_atelier_edit(request)
    body = await request.json()
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM rh_notes_equipe WHERE id = ?", (note_id,)).fetchone():
            raise HTTPException(404, "Note introuvable.")
        n = _lire_note(conn, body)
        conn.execute(
            """UPDATE rh_notes_equipe SET semaine_debut = ?, semaine_fin = ?, cible_type = ?,
                   cible_valeur = ?, texte = ?, importance = ? WHERE id = ?""",
            (n["semaine_debut"], n["semaine_fin"], n["cible_type"], n["cible_valeur"], n["texte"],
             n["importance"], note_id))
        conn.commit()
        out = _note_dict(conn, conn.execute("SELECT * FROM rh_notes_equipe WHERE id = ?", (note_id,)).fetchone())
    log_action(user=editor, action="UPDATE", module="rh", objet=f"Note d'équipe #{note_id} modifiée",
               ip=_ip(request))
    return out


@router.delete("/notes-equipe/{note_id}")
def delete_note_equipe(note_id: int, request: Request):
    editor = _require_atelier_edit(request)
    with get_db() as conn:
        conn.execute("DELETE FROM rh_notes_equipe WHERE id = ?", (note_id,))
        conn.commit()
    log_action(user=editor, action="DELETE", module="rh", objet=f"Note d'équipe #{note_id} supprimée",
               ip=_ip(request))
    return {"ok": True}
