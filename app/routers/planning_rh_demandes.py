"""MySifa — Planning RH : demandes des employés et motifs d'absence.

Routes /api/rh/motifs* et /api/rh/demandes*

Tout employé connecté dépose ses propres demandes (absence avec un motif,
aménagement d'horaire, autre) et peut les annuler tant qu'elles attendent.
Le responsable du planning RH les valide ou les refuse :
  * éditeurs RH (comptabilité, direction, superadmin) : toutes les demandes ;
  * éditeurs atelier (exceptions planning_rh) : celles du personnel atelier.
Une absence validée crée le congé correspondant dans rh_conges, avec le code
du motif comme type_conge — c'est lui que le planning et les soldes lisent.

Les motifs d'absence sont un référentiel en base (rh_motifs_absence) : la
logique lit leur `decompte` (solde imputé) et `demandable`, jamais leur code.
"""
import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from app.routers.planning_rh import (
    _filter_planning_rh_user_rows,
    _planning_rh_nom_excluded,
    _require_conge_edit,
)
from app.services.audit_service import log_action
from app.services.auth_service import get_current_user
from config import (
    ROLE_SUPERADMIN,
    ROLES_PLANNING_RH_HR_EDIT,
    rh_demande_natures,
    rh_demande_statuts,
    rh_motif_decomptes,
)
from database import get_db

router = APIRouter(prefix="/api/rh", tags=["planning_rh_demandes"])

_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_ATELIER_SQL = "(u.role IN ('fabrication','logistique') OR u.email = 'mlesaffre@sifa.pro')"

_SELECT_DEMANDE = """
    SELECT d.id, d.user_id, u.nom AS user_nom, u.role AS user_role,
           d.nature, d.motif_code, m.libelle AS motif_libelle,
           d.date_debut, d.date_fin, d.nb_jours, d.heure_debut, d.heure_fin,
           d.commentaire, d.statut, d.decision_par, d.decision_le,
           d.decision_note, d.conge_id, d.cree_le
      FROM rh_demandes d
      JOIN users u ON u.id = d.user_id
      LEFT JOIN rh_motifs_absence m ON m.code = d.motif_code
"""


def _ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


def _perimetre_validation(user: dict) -> str:
    """'rh' = toutes les demandes ; 'atelier' = personnel atelier seulement."""
    return "rh" if user.get("role") in ROLES_PLANNING_RH_HR_EDIT else "atelier"


def _jours_ouvres(d_deb: date, d_fin: date) -> float:
    n, cur = 0, d_deb
    while cur <= d_fin:
        if cur.weekday() < 5:
            n += 1
        cur += timedelta(days=1)
    return float(n)


def _lire_dates(body: dict) -> tuple[date, date]:
    try:
        d_deb = date.fromisoformat(str(body.get("date_debut") or ""))
        d_fin = date.fromisoformat(str(body.get("date_fin") or body.get("date_debut") or ""))
    except ValueError:
        raise HTTPException(400, "Dates invalides — format AAAA-MM-JJ attendu.")
    if d_fin < d_deb:
        raise HTTPException(400, "La date de fin doit être postérieure ou égale à la date de début.")
    if (d_fin - d_deb).days > 366:
        raise HTTPException(400, "Période trop longue — un an au plus.")
    return d_deb, d_fin


def _motif(conn, code: str, *, demandable: bool = False):
    row = conn.execute(
        "SELECT * FROM rh_motifs_absence WHERE code = ? AND actif = 1", (code,)
    ).fetchone()
    if not row:
        raise HTTPException(400, "Motif d'absence inconnu ou désactivé.")
    if demandable and not row["demandable"]:
        raise HTTPException(400, f"Le motif « {row['libelle']} » ne se demande pas : voir le responsable.")
    return row


def _demande(conn, demande_id: int) -> dict:
    row = conn.execute(_SELECT_DEMANDE + " WHERE d.id = ?", (demande_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Demande introuvable.")
    return dict(row)


def _conflits_planning(conn, user_id: int, d_deb: date, d_fin: date) -> list[str]:
    """Semaines où l'employé est déjà affecté à un poste pendant la période."""
    semaines = set()
    for a in conn.execute(
        "SELECT semaine FROM rh_planning_postes WHERE user_id = ?", (user_id,)
    ).fetchall():
        try:
            ay, aw = str(a["semaine"]).split("-W")
            lundi = date.fromisocalendar(int(ay), int(aw), 1)
        except (ValueError, AttributeError):
            continue
        if d_deb <= lundi + timedelta(days=6) and d_fin >= lundi:
            semaines.add(a["semaine"])
    return sorted(semaines)


# ── Référentiels ─────────────────────────────────────────────────
@router.get("/demandes/referentiels")
def get_referentiels(request: Request):
    get_current_user(request)
    return {
        "natures": rh_demande_natures(),
        "statuts": rh_demande_statuts(),
        "decomptes": rh_motif_decomptes(),
    }


# ── Motifs d'absence ─────────────────────────────────────────────
@router.get("/motifs")
def list_motifs(request: Request, tous: int = 0):
    """Motifs actifs (tous les connectés) ; `tous=1` ajoute les désactivés."""
    get_current_user(request)
    q = "SELECT id, code, libelle, decompte, demandable, actif, ordre FROM rh_motifs_absence"
    if not tous:
        q += " WHERE actif = 1"
    q += " ORDER BY ordre, libelle COLLATE NOCASE"
    with get_db() as conn:
        rows = conn.execute(q).fetchall()
    return {"motifs": [dict(r) for r in rows]}


def _code_depuis_libelle(libelle: str) -> str:
    s = unicodedata.normalize("NFKD", libelle).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")[:40] or "motif"


def _champs_motif(body: dict, *, creation: bool) -> dict:
    out = {}
    if "libelle" in body or creation:
        lib = str(body.get("libelle") or "").strip()
        if not lib or len(lib) > 60:
            raise HTTPException(400, "Libellé obligatoire — 60 caractères au plus.")
        out["libelle"] = lib
    if "decompte" in body or creation:
        dec = str(body.get("decompte") or "aucun")
        if dec not in rh_motif_decomptes():
            raise HTTPException(400, "Décompte invalide.")
        out["decompte"] = dec
    for k in ("demandable", "actif"):
        if k in body:
            out[k] = 1 if body.get(k) else 0
    if "ordre" in body:
        try:
            out["ordre"] = int(body.get("ordre") or 0)
        except (TypeError, ValueError):
            raise HTTPException(400, "Ordre invalide.")
    return out


@router.post("/motifs")
async def create_motif(request: Request):
    editor = _require_conge_edit(request)
    body = await request.json()
    champs = _champs_motif(body, creation=True)
    with get_db() as conn:
        base = _code_depuis_libelle(champs["libelle"])
        code, i = base, 2
        while conn.execute("SELECT 1 FROM rh_motifs_absence WHERE code = ?", (code,)).fetchone():
            code, i = f"{base}_{i}", i + 1
        if "ordre" not in champs:
            champs["ordre"] = int(conn.execute(
                "SELECT COALESCE(MAX(ordre), 0) + 1 FROM rh_motifs_absence"
            ).fetchone()[0])
        champs.setdefault("demandable", 1)
        cols = ["code"] + list(champs) + ["modifie_le", "modifie_par"]
        vals = [code] + list(champs.values()) + [datetime.now().isoformat(), editor.get("email")]
        cur = conn.execute(
            f"INSERT INTO rh_motifs_absence ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
            vals,
        )
        conn.commit()
        row = conn.execute("SELECT * FROM rh_motifs_absence WHERE id = ?", (cur.lastrowid,)).fetchone()
    log_action(user=editor, action="CREATE", module="rh",
               objet=f"Motif d'absence « {champs['libelle']} »", ip=_ip(request))
    return dict(row)


@router.put("/motifs/{motif_id}")
async def update_motif(motif_id: int, request: Request):
    editor = _require_conge_edit(request)
    body = await request.json()
    champs = _champs_motif(body, creation=False)
    if not champs:
        raise HTTPException(400, "Aucun champ modifiable fourni.")
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM rh_motifs_absence WHERE id = ?", (motif_id,)).fetchone():
            raise HTTPException(404, "Motif introuvable.")
        champs["modifie_le"] = datetime.now().isoformat()
        champs["modifie_par"] = editor.get("email")
        conn.execute(
            f"UPDATE rh_motifs_absence SET {', '.join(k + ' = ?' for k in champs)} WHERE id = ?",
            list(champs.values()) + [motif_id],
        )
        conn.commit()
        row = conn.execute("SELECT * FROM rh_motifs_absence WHERE id = ?", (motif_id,)).fetchone()
    log_action(user=editor, action="UPDATE", module="rh",
               objet=f"Motif d'absence #{motif_id} modifié", detail=champs, ip=_ip(request))
    return dict(row)


# ── Demandes : côté employé ──────────────────────────────────────
@router.get("/demandes/mes")
def mes_demandes(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        rows = conn.execute(
            _SELECT_DEMANDE + " WHERE d.user_id = ? ORDER BY d.date_debut DESC, d.id DESC LIMIT 200",
            (user["id"],),
        ).fetchall()
    return {"demandes": [dict(r) for r in rows]}


@router.post("/demandes")
async def create_demande(request: Request):
    """Un employé dépose une demande pour lui-même."""
    user = get_current_user(request)
    body = await request.json()
    nature = str(body.get("nature") or "")
    if nature not in rh_demande_natures():
        raise HTTPException(400, "Type de demande invalide.")
    d_deb, d_fin = _lire_dates(body)
    commentaire = str(body.get("commentaire") or "").strip()[:1000] or None
    motif_code = nb = h_deb = h_fin = None

    with get_db() as conn:
        u = conn.execute("SELECT nom FROM users WHERE id = ? AND actif = 1", (user["id"],)).fetchone()
        if not u or _planning_rh_nom_excluded(u["nom"]):
            raise HTTPException(403, "Ce compte ne peut pas déposer de demande RH.")

        if nature == "absence":
            motif_code = _motif(conn, str(body.get("motif_code") or ""), demandable=True)["code"]
            ouvres = _jours_ouvres(d_deb, d_fin)
            raw = body.get("nb_jours")
            try:
                nb = float(raw) if raw not in (None, "") else ouvres
            except (TypeError, ValueError):
                raise HTTPException(400, "Nombre de jours invalide.")
            if nb <= 0 or nb > max(ouvres, 0.5) or (nb * 2) % 1:
                raise HTTPException(
                    400, f"Nombre de jours invalide — entre 0,5 et {ouvres:g}, par demi-journée.")
        elif nature == "horaire":
            h_deb = str(body.get("heure_debut") or "")
            h_fin = str(body.get("heure_fin") or "")
            if not _HHMM.match(h_deb) or not _HHMM.match(h_fin):
                raise HTTPException(400, "Horaires souhaités invalides — format HH:MM.")
            if h_fin == h_deb:
                raise HTTPException(400, "L'heure de fin doit différer de l'heure de début.")
            if not commentaire:
                raise HTTPException(400, "Précisez le motif de l'aménagement.")
        elif not commentaire:
            raise HTTPException(400, "Décrivez votre demande.")

        chevauche = conn.execute(
            """SELECT 1 FROM rh_demandes
                WHERE user_id = ? AND nature = ? AND statut IN ('en_attente', 'validee')
                  AND date_debut <= ? AND date_fin >= ?""",
            (user["id"], nature, d_fin.isoformat(), d_deb.isoformat()),
        ).fetchone()
        if chevauche:
            raise HTTPException(409, "Une demande du même type couvre déjà ces dates.")

        cur = conn.execute(
            """INSERT INTO rh_demandes
                   (user_id, nature, motif_code, date_debut, date_fin, nb_jours,
                    heure_debut, heure_fin, commentaire, statut, cree_le, cree_par)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'en_attente', ?, ?)""",
            (user["id"], nature, motif_code, d_deb.isoformat(), d_fin.isoformat(), nb,
             h_deb, h_fin, commentaire, datetime.now().isoformat(timespec="seconds"),
             user.get("email")),
        )
        conn.commit()
        out = _demande(conn, cur.lastrowid)
    _invalider_notif()
    log_action(user=user, action="CREATE", module="rh",
               objet=f"Demande {rh_demande_natures()[nature]} · {d_deb} → {d_fin}", ip=_ip(request))
    return out


@router.post("/demandes/{demande_id}/annuler")
def annuler_demande(demande_id: int, request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        d = _demande(conn, demande_id)
        if d["user_id"] != user["id"]:
            raise HTTPException(403, "Seul le demandeur peut annuler sa demande.")
        if d["statut"] != "en_attente":
            raise HTTPException(409, "Demande déjà traitée — voir le responsable pour la modifier.")
        conn.execute("UPDATE rh_demandes SET statut = 'annulee' WHERE id = ?", (demande_id,))
        conn.commit()
        out = _demande(conn, demande_id)
    _invalider_notif()
    log_action(user=user, action="UPDATE", module="rh",
               objet=f"Demande RH #{demande_id} annulée", ip=_ip(request))
    return out


# ── Demandes : côté responsable ──────────────────────────────────
@router.get("/demandes")
def list_demandes(request: Request, statut: str = "", annee: Optional[int] = None):
    editor = _require_conge_edit(request)
    conds, params = [], []
    if statut:
        if statut not in rh_demande_statuts():
            raise HTTPException(400, "Statut invalide.")
        conds.append("d.statut = ?")
        params.append(statut)
    if annee:
        conds.append("(substr(d.date_debut, 1, 4) = ? OR substr(d.date_fin, 1, 4) = ?)")
        params += [str(annee), str(annee)]
    if _perimetre_validation(editor) == "atelier":
        conds.append(_ATELIER_SQL)
    q = _SELECT_DEMANDE + (" WHERE " + " AND ".join(conds) if conds else "")
    q += " ORDER BY CASE d.statut WHEN 'en_attente' THEN 0 ELSE 1 END, d.date_debut DESC, d.id DESC"
    with get_db() as conn:
        rows = conn.execute(q, params).fetchall()
    return {"demandes": _filter_planning_rh_user_rows(rows, "user_nom")}


@router.post("/demandes/{demande_id}/decision")
async def decider_demande(demande_id: int, request: Request):
    """Valider ou refuser. `force` passe outre un conflit avec le planning postes."""
    editor = _require_conge_edit(request)
    body = await request.json()
    decision = str(body.get("decision") or "")
    if decision not in ("valider", "refuser"):
        raise HTTPException(400, "Décision invalide.")
    note = str(body.get("note") or "").strip()[:500] or None
    if decision == "refuser" and not note:
        raise HTTPException(400, "Motif du refus obligatoire — il est affiché au demandeur.")

    with get_db() as conn:
        d = _demande(conn, demande_id)
        if d["statut"] != "en_attente":
            raise HTTPException(409, "Demande déjà traitée.")
        if _perimetre_validation(editor) == "atelier" and d["user_role"] not in ("fabrication", "logistique"):
            raise HTTPException(403, "Cette demande relève de la vue RH.")
        reel = editor.get("real_role") or editor.get("role")
        if d["user_id"] == editor.get("id") and reel != ROLE_SUPERADMIN:
            raise HTTPException(403, "Une demande ne se valide pas par son auteur.")

        maintenant = datetime.now().isoformat(timespec="seconds")
        conge_id = None
        if decision == "valider" and d["nature"] == "absence":
            d_deb, d_fin = date.fromisoformat(d["date_debut"]), date.fromisoformat(d["date_fin"])
            semaines = _conflits_planning(conn, d["user_id"], d_deb, d_fin)
            if semaines and not body.get("force"):
                raise HTTPException(409, {
                    "message": (f"{d['user_nom']} est affecté(e) au planning les semaines "
                                f"{', '.join(semaines)}. Valider quand même ? Les affectations "
                                f"seront à ajuster dans le planning."),
                    "conflict_type": "planning",
                    "semaines": semaines,
                })
            note_conge = d["commentaire"] or None
            cur = conn.execute(
                """INSERT INTO rh_conges
                       (user_id, date_debut, date_fin, nb_jours, type_conge, note,
                        statut, created_by, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'valide', ?, ?)""",
                (d["user_id"], d["date_debut"], d["date_fin"], d["nb_jours"] or 0,
                 d["motif_code"], note_conge, editor.get("email"), maintenant),
            )
            conge_id = cur.lastrowid

        conn.execute(
            """UPDATE rh_demandes
                  SET statut = ?, decision_par = ?, decision_le = ?, decision_note = ?, conge_id = ?
                WHERE id = ?""",
            ("validee" if decision == "valider" else "refusee",
             editor.get("nom") or editor.get("email"), maintenant, note, conge_id, demande_id),
        )
        conn.commit()
        out = _demande(conn, demande_id)
    _invalider_notif()
    log_action(user=editor, action="UPDATE", module="rh",
               objet=f"Demande RH #{demande_id} {'validée' if decision == 'valider' else 'refusée'} · {d['user_nom']}",
               detail={"note": note} if note else None, ip=_ip(request))
    return out


def _invalider_notif():
    try:
        from app.services import notifications
        notifications.invalider_cache("rh.demandes_a_valider")
    except Exception:
        pass
