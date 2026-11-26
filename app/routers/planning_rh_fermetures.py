"""MySifa — Planning RH : fermetures collectives.

Routes /api/rh/fermetures*

Une fermeture collective (fermeture annuelle, pont) pose un congé à chaque
employé actif sur la même période, avec un motif par défaut (CP en général).
Les congés créés sont des lignes ordinaires de rh_conges, reliées par
`fermeture_id` : le motif et le nombre de jours se modifient employé par
employé (sans solde pour quelqu'un qui n'a plus de CP), les soldes les
décomptent selon leur motif.

Règles :
  * un employé déjà absent sur la période (autre congé qui chevauche) n'en
    reçoit pas un second — il est signalé ;
  * un employé retiré de la fermeture (il travaille pendant la fermeture) est
    gardé dans rh_fermetures_exclus : réappliquer ne le rajoute pas ;
  * modifier la fermeture reporte les dates sur tous ses congés, le motif et
    le nombre de jours seulement sur ceux qui suivaient encore la valeur
    d'origine (un ajustement individuel n'est jamais écrasé).

Écriture réservée aux éditeurs RH (comptabilité, direction, superadmin) :
une fermeture touche tous les services.
"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from app.routers.planning_rh import (
    _assert_motif_actif,
    _planning_rh_nom_excluded,
    _require_hr_edit,
    _require_hr_view,
    jours_affectes_pendant,
    jours_ouvres,
)
from app.services.audit_service import log_action
from config import national_holidays_between
from database import get_db

router = APIRouter(prefix="/api/rh", tags=["planning_rh_fermetures"])


# ── Calcul ───────────────────────────────────────────────────────
def _ouvres_et_feries(d_deb: date, d_fin: date) -> tuple[float, list[dict]]:
    feries = national_holidays_between(d_deb.isoformat(), d_fin.isoformat())
    return jours_ouvres(d_deb, d_fin), [{"date": d, "libelle": l} for d, l in sorted(feries)]


def _dates(body: dict) -> tuple[date, date]:
    try:
        d_deb = date.fromisoformat(str(body.get("date_debut") or "")[:10])
        d_fin = date.fromisoformat(str(body.get("date_fin") or "")[:10])
    except ValueError:
        raise HTTPException(400, "Dates invalides — format AAAA-MM-JJ attendu.")
    if d_fin < d_deb:
        raise HTTPException(400, "La date de fin doit être postérieure ou égale à la date de début.")
    if (d_fin - d_deb).days > 62:
        raise HTTPException(400, "Période trop longue — une fermeture dure au plus deux mois.")
    return d_deb, d_fin


def _nb(val, defaut: float) -> float:
    if val in (None, ""):
        return defaut
    try:
        nb = float(val)
    except (TypeError, ValueError):
        raise HTTPException(400, "Nombre de jours invalide.")
    if nb <= 0 or nb > 62:
        raise HTTPException(400, "Nombre de jours invalide — valeur entre 0.5 et 62.")
    return nb


# ── Lecture ──────────────────────────────────────────────────────
def _fermeture(conn, fid: int) -> dict:
    row = conn.execute("SELECT * FROM rh_fermetures WHERE id = ?", (fid,)).fetchone()
    if not row:
        raise HTTPException(404, "Fermeture introuvable.")
    return dict(row)


def _employes_actifs(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT id, nom, role FROM users WHERE actif = 1 ORDER BY nom COLLATE NOCASE"
    ).fetchall()
    return [dict(r) for r in rows if not _planning_rh_nom_excluded(r["nom"])]


def _absence_qui_chevauche(conn, user_id: int, f: dict) -> Optional[dict]:
    row = conn.execute(
        """SELECT c.id, c.type_conge, c.date_debut, c.date_fin, m.libelle
             FROM rh_conges c LEFT JOIN rh_motifs_absence m ON m.code = c.type_conge
            WHERE c.user_id = ? AND c.statut != 'refuse'
              AND (c.fermeture_id IS NULL OR c.fermeture_id != ?)
              AND c.date_debut <= ? AND c.date_fin >= ?
            ORDER BY c.date_debut LIMIT 1""",
        (user_id, f["id"], f["date_fin"], f["date_debut"]),
    ).fetchone()
    return dict(row) if row else None


def _detail(conn, f: dict) -> dict:
    """La fermeture et la situation de chaque employé actif."""
    conges = {
        r["user_id"]: dict(r) for r in conn.execute(
            "SELECT id, user_id, type_conge, nb_jours, statut FROM rh_conges WHERE fermeture_id = ?",
            (f["id"],),
        ).fetchall()
    }
    exclus = {r["user_id"] for r in conn.execute(
        "SELECT user_id FROM rh_fermetures_exclus WHERE fermeture_id = ?", (f["id"],)
    ).fetchall()}
    d_deb, d_fin = date.fromisoformat(f["date_debut"]), date.fromisoformat(f["date_fin"])
    employes = []
    vus = set()
    for e in _employes_actifs(conn):
        uid = e["id"]
        vus.add(uid)
        ligne = {"user_id": uid, "nom": e["nom"], "role": e["role"],
                 "conge_id": None, "type_conge": None, "nb_jours": None}
        c = conges.get(uid)
        if c:
            ligne.update(etat="couvert", conge_id=c["id"], type_conge=c["type_conge"], nb_jours=c["nb_jours"])
            conflits = jours_affectes_pendant(conn, uid, d_deb, d_fin)
            if conflits:
                ligne["planning"] = conflits
        elif uid in exclus:
            ligne["etat"] = "exclu"
        else:
            autre = _absence_qui_chevauche(conn, uid, f)
            if autre:
                ligne["etat"] = "deja_absent"
                ligne["absence"] = {"type_conge": autre["type_conge"], "libelle": autre["libelle"],
                                    "date_debut": autre["date_debut"], "date_fin": autre["date_fin"]}
            else:
                ligne["etat"] = "a_ajouter"
        employes.append(ligne)
    # Congé d'une personne désactivée depuis : encore compté, montré à part.
    for uid, c in conges.items():
        if uid in vus:
            continue
        u = conn.execute("SELECT nom, role FROM users WHERE id = ?", (uid,)).fetchone()
        employes.append({"user_id": uid, "nom": u["nom"] if u else f"#{uid}", "role": u["role"] if u else None,
                         "etat": "couvert", "inactif": True, "conge_id": c["id"],
                         "type_conge": c["type_conge"], "nb_jours": c["nb_jours"]})
    compte = {}
    for e in employes:
        compte[e["etat"]] = compte.get(e["etat"], 0) + 1
    return {**f, "employes": employes, "compte": compte}


@router.get("/fermetures/apercu")
def apercu_fermeture(request: Request, du: str, au: str):
    """Avant création : jours ouvrés proposés et situation de chaque employé."""
    _require_hr_view(request)
    d_deb, d_fin = _dates({"date_debut": du, "date_fin": au})
    nb, feries = _ouvres_et_feries(d_deb, d_fin)
    with get_db() as conn:
        det = _detail(conn, {"id": 0, "date_debut": d_deb.isoformat(), "date_fin": d_fin.isoformat()})
    return {"nb_jours": nb, "feries": feries, "employes": det["employes"], "compte": det["compte"]}


@router.get("/fermetures")
def liste_fermetures(request: Request, annee: Optional[int] = None):
    _require_hr_view(request)
    with get_db() as conn:
        q = """SELECT f.*, m.libelle AS type_libelle,
                      (SELECT COUNT(*) FROM rh_conges c WHERE c.fermeture_id = f.id) AS nb_conges
                 FROM rh_fermetures f LEFT JOIN rh_motifs_absence m ON m.code = f.type_conge"""
        params: list = []
        if annee:
            q += " WHERE substr(f.date_debut,1,4) = ? OR substr(f.date_fin,1,4) = ?"
            params = [str(annee), str(annee)]
        q += " ORDER BY f.date_debut DESC"
        rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    return {"fermetures": rows}


@router.get("/fermetures/{fid}")
def detail_fermeture(fid: int, request: Request):
    _require_hr_view(request)
    with get_db() as conn:
        return _detail(conn, _fermeture(conn, fid))


# ── Écriture ─────────────────────────────────────────────────────
def _poser(conn, f: dict, user_id: int, par: str, type_conge: Optional[str] = None,
           nb_jours: Optional[float] = None) -> int:
    cur = conn.execute(
        """INSERT INTO rh_conges
               (user_id, date_debut, date_fin, nb_jours, type_conge, note, statut,
                created_by, created_at, fermeture_id)
           VALUES (?, ?, ?, ?, ?, ?, 'valide', ?, ?, ?)""",
        (user_id, f["date_debut"], f["date_fin"], nb_jours if nb_jours is not None else f["nb_jours"],
         type_conge or f["type_conge"], f["libelle"], par, datetime.now().isoformat(timespec="seconds"), f["id"]),
    )
    return cur.lastrowid


def _appliquer(conn, f: dict, par: str) -> dict:
    """Pose le congé aux employés qui n'en ont pas encore (ni exclus, ni déjà absents)."""
    det = _detail(conn, f)
    ajoutes = []
    for e in det["employes"]:
        if e["etat"] == "a_ajouter":
            _poser(conn, f, e["user_id"], par)
            ajoutes.append(e["nom"])
    deja = [e["nom"] for e in det["employes"] if e["etat"] == "deja_absent"]
    return {"ajoutes": len(ajoutes), "deja_absents": deja}


@router.post("/fermetures")
async def creer_fermeture(request: Request):
    editor = _require_hr_edit(request)
    body = await request.json()
    libelle = str(body.get("libelle") or "").strip()
    if not libelle:
        raise HTTPException(400, "Nom de la fermeture obligatoire.")
    d_deb, d_fin = _dates(body)
    nb_defaut = jours_ouvres(d_deb, d_fin)
    nb = _nb(body.get("nb_jours"), nb_defaut)
    type_conge = str(body.get("type_conge") or "CP")
    exclus = [int(u) for u in (body.get("exclus") or []) if str(u).isdigit()]
    par = editor.get("email")
    with get_db() as conn:
        _assert_motif_actif(conn, type_conge)
        cur = conn.execute(
            """INSERT INTO rh_fermetures (libelle, date_debut, date_fin, nb_jours, type_conge, note, cree_par)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (libelle, d_deb.isoformat(), d_fin.isoformat(), nb, type_conge,
             (str(body.get("note") or "").strip() or None), par),
        )
        fid = cur.lastrowid
        for uid in exclus:
            conn.execute(
                "INSERT OR IGNORE INTO rh_fermetures_exclus (fermeture_id, user_id, cree_par) VALUES (?, ?, ?)",
                (fid, uid, par),
            )
        f = _fermeture(conn, fid)
        bilan = _appliquer(conn, f, par)
        conn.commit()
        det = _detail(conn, f)
    log_action(user=editor, action="CREATE", module="rh",
               objet=f"Fermeture « {libelle} » · {d_deb.isoformat()} → {d_fin.isoformat()} · {bilan['ajoutes']} congé(s)",
               ip=request.client.host if request.client else None)
    return {**det, "bilan": bilan}


@router.put("/fermetures/{fid}")
async def modifier_fermeture(fid: int, request: Request):
    editor = _require_hr_edit(request)
    body = await request.json()
    par = editor.get("email")
    with get_db() as conn:
        avant = _fermeture(conn, fid)
        libelle = str(body.get("libelle", avant["libelle"]) or "").strip()
        if not libelle:
            raise HTTPException(400, "Nom de la fermeture obligatoire.")
        d_deb, d_fin = _dates({"date_debut": body.get("date_debut", avant["date_debut"]),
                               "date_fin": body.get("date_fin", avant["date_fin"])})
        nb = _nb(body.get("nb_jours"), float(avant["nb_jours"]))
        type_conge = str(body.get("type_conge") or avant["type_conge"])
        if type_conge != avant["type_conge"]:
            _assert_motif_actif(conn, type_conge)
        note = body.get("note", avant["note"])
        conn.execute(
            """UPDATE rh_fermetures SET libelle=?, date_debut=?, date_fin=?, nb_jours=?, type_conge=?,
                      note=?, modifie_le=datetime('now'), modifie_par=? WHERE id=?""",
            (libelle, d_deb.isoformat(), d_fin.isoformat(), nb, type_conge,
             (str(note or "").strip() or None), par, fid),
        )
        # Dates et libellé : tous les congés de la fermeture.
        conn.execute(
            "UPDATE rh_conges SET date_debut=?, date_fin=?, note=? WHERE fermeture_id=?",
            (d_deb.isoformat(), d_fin.isoformat(), libelle, fid),
        )
        # Motif et jours : seulement ceux qui n'ont pas été ajustés à la main.
        n_type = conn.execute(
            "UPDATE rh_conges SET type_conge=? WHERE fermeture_id=? AND type_conge=?",
            (type_conge, fid, avant["type_conge"]),
        ).rowcount if type_conge != avant["type_conge"] else 0
        if nb != float(avant["nb_jours"]):
            conn.execute(
                "UPDATE rh_conges SET nb_jours=? WHERE fermeture_id=? AND nb_jours=?",
                (nb, fid, float(avant["nb_jours"])),
            )
        f = _fermeture(conn, fid)
        conn.commit()
        det = _detail(conn, f)
    log_action(user=editor, action="UPDATE", module="rh", objet=f"Fermeture « {libelle} » modifiée",
               detail={"avant": {k: avant[k] for k in ("libelle", "date_debut", "date_fin", "nb_jours", "type_conge")},
                       "apres": {k: f[k] for k in ("libelle", "date_debut", "date_fin", "nb_jours", "type_conge")},
                       "motif_reporte": n_type},
               ip=request.client.host if request.client else None)
    return det


@router.post("/fermetures/{fid}/appliquer")
def appliquer_fermeture(fid: int, request: Request):
    """Pose le congé aux employés arrivés depuis (ou libérés d'une autre absence)."""
    editor = _require_hr_edit(request)
    with get_db() as conn:
        f = _fermeture(conn, fid)
        bilan = _appliquer(conn, f, editor.get("email"))
        conn.commit()
        det = _detail(conn, f)
    if bilan["ajoutes"]:
        log_action(user=editor, action="UPDATE", module="rh",
                   objet=f"Fermeture « {f['libelle']} » · {bilan['ajoutes']} congé(s) ajouté(s)",
                   ip=request.client.host if request.client else None)
    return {**det, "bilan": bilan}


@router.put("/fermetures/{fid}/employes/{user_id}")
async def ajuster_employe(fid: int, user_id: int, request: Request):
    """Motif ou jours d'un employé, ou inclusion / retrait de la fermeture.

    Corps : {type_conge?, nb_jours?} pour un employé couvert ;
            {inclus: false} le retire (son congé est supprimé, il reste exclu) ;
            {inclus: true} le réintègre (congé posé avec les valeurs de la fermeture).
    """
    editor = _require_hr_edit(request)
    body = await request.json()
    par = editor.get("email")
    with get_db() as conn:
        f = _fermeture(conn, fid)
        u = conn.execute("SELECT nom FROM users WHERE id = ?", (user_id,)).fetchone()
        if not u:
            raise HTTPException(404, "Employé introuvable.")
        conge = conn.execute(
            "SELECT id, type_conge, nb_jours FROM rh_conges WHERE fermeture_id = ? AND user_id = ?",
            (fid, user_id),
        ).fetchone()
        if body.get("inclus") is False:
            if conge:
                conn.execute("DELETE FROM rh_conges WHERE id = ?", (conge["id"],))
            conn.execute(
                "INSERT OR IGNORE INTO rh_fermetures_exclus (fermeture_id, user_id, cree_par) VALUES (?, ?, ?)",
                (fid, user_id, par),
            )
            quoi = "retiré(e)"
        elif body.get("inclus") is True:
            conn.execute("DELETE FROM rh_fermetures_exclus WHERE fermeture_id = ? AND user_id = ?", (fid, user_id))
            if not conge:
                if _absence_qui_chevauche(conn, user_id, f):
                    raise HTTPException(409, f"{u['nom']} a déjà une absence sur cette période — modifiez-la d'abord.")
                _poser(conn, f, user_id, par)
            quoi = "réintégré(e)"
        else:
            if not conge:
                raise HTTPException(409, f"{u['nom']} n'a pas de congé sur cette fermeture.")
            champs = {}
            if body.get("type_conge"):
                _assert_motif_actif(conn, body["type_conge"])
                champs["type_conge"] = str(body["type_conge"])
            if body.get("nb_jours") not in (None, ""):
                champs["nb_jours"] = _nb(body["nb_jours"], float(conge["nb_jours"]))
            if not champs:
                raise HTTPException(400, "Rien à modifier.")
            conn.execute(
                f"UPDATE rh_conges SET {', '.join(k + ' = ?' for k in champs)} WHERE id = ?",
                [*champs.values(), conge["id"]],
            )
            quoi = "modifié(e) : " + ", ".join(f"{k}={v}" for k, v in champs.items())
        conn.commit()
        det = _detail(conn, f)
    log_action(user=editor, action="UPDATE", module="rh",
               objet=f"Fermeture « {f['libelle']} » · {u['nom']} {quoi}",
               ip=request.client.host if request.client else None)
    return det


@router.delete("/fermetures/{fid}")
def supprimer_fermeture(fid: int, request: Request):
    editor = _require_hr_edit(request)
    with get_db() as conn:
        f = _fermeture(conn, fid)
        n = conn.execute("DELETE FROM rh_conges WHERE fermeture_id = ?", (fid,)).rowcount
        conn.execute("DELETE FROM rh_fermetures_exclus WHERE fermeture_id = ?", (fid,))
        conn.execute("DELETE FROM rh_fermetures WHERE id = ?", (fid,))
        conn.commit()
    log_action(user=editor, action="DELETE", module="rh",
               objet=f"Fermeture « {f['libelle']} » supprimée · {n} congé(s) retiré(s)",
               ip=request.client.host if request.client else None)
    return {"ok": True, "conges_supprimes": n}
