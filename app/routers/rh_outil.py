"""MySifa — Outil RH (onglet de MyCompta).

Liste partagée des employés suivis dans l'onglet « Outil RH ». On y ajoute un
employé choisi parmi tous les comptes (actifs ou non), on peut le retirer.
Chaque employé suivi porte une checklist :
- des cases fixes, une colonne de rh_outil_membres chacune (CHECKLIST) ;
- ses formations, piochées dans un catalogue commun géré depuis l'onglet
  (rh_outil_formations / rh_outil_membre_formations).
Accès : quiconque a accès à MyCompta (rôle ou exception réglée dans Paramètres).
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from database import get_db
from services.auth_service import get_current_user, user_has_app_access
from services.audit_service import log_action

router = APIRouter(prefix="/api/rh-outil", tags=["rh_outil"])

LIBELLE_MAX = 120


class MembreIn(BaseModel):
    user_id: int


class MembrePatch(BaseModel):
    reglement_signe: Optional[bool] = None


class FormationIn(BaseModel):
    libelle: str


class AttributionIn(BaseModel):
    formation_id: int


class AttributionPatch(BaseModel):
    fait: bool


# Points fixes de la checklist : champ de MembrePatch → libellé du journal.
# Chaque point est une colonne de rh_outil_membres (migration fichier).
CHECKLIST = {"reglement_signe": "Règlement signé"}


def _require(request: Request) -> dict:
    u = get_current_user(request)
    if not user_has_app_access(u, "compta"):
        raise HTTPException(status_code=403, detail="Accès réservé à MyCompta")
    return u


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _libelle(brut: str) -> str:
    libelle = " ".join((brut or "").split())
    if not libelle:
        raise HTTPException(400, "Intitulé vide.")
    if len(libelle) > LIBELLE_MAX:
        raise HTTPException(400, f"Intitulé trop long — {LIBELLE_MAX} caractères maximum.")
    return libelle


def _membre(conn, membre_id: int):
    row = conn.execute(
        """SELECT m.id, u.nom FROM rh_outil_membres m
             JOIN users u ON u.id = m.user_id WHERE m.id=?""",
        (membre_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Employé introuvable dans la liste.")
    return row


def _doublon(conn, libelle: str, sauf_id: Optional[int] = None) -> bool:
    row = conn.execute(
        "SELECT id FROM rh_outil_formations WHERE libelle = ? COLLATE NOCASE AND id != ?",
        (libelle, sauf_id or 0),
    ).fetchone()
    return row is not None


# ─── Employés ─────────────────────────────────────────────────────────────

@router.get("/employes")
def list_employes(request: Request):
    """Tous les comptes, actifs ou non, pour le sélecteur d'ajout."""
    _require(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT u.id, u.nom, u.email, u.role, u.actif,
                      (m.id IS NOT NULL) AS deja_ajoute
                 FROM users u
                 LEFT JOIN rh_outil_membres m ON m.user_id = u.id
                WHERE LOWER(COALESCE(u.nom,'')) != 'administrateur'
                ORDER BY u.nom COLLATE NOCASE"""
        ).fetchall()
    return {"employes": [
        {"user_id": r["id"], "nom": r["nom"], "email": r["email"], "role": r["role"],
         "actif": bool(r["actif"]), "deja_ajoute": bool(r["deja_ajoute"])}
        for r in rows
    ]}


@router.get("/membres")
def list_membres(request: Request):
    _require(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT m.id, m.user_id, m.ajoute_le, m.ajoute_par, m.reglement_signe,
                      u.nom, u.email, u.role, u.actif
                 FROM rh_outil_membres m
                 JOIN users u ON u.id = m.user_id
                ORDER BY u.nom COLLATE NOCASE"""
        ).fetchall()
        attributions = conn.execute(
            """SELECT a.id, a.membre_id, a.formation_id, a.fait, f.libelle
                 FROM rh_outil_membre_formations a
                 JOIN rh_outil_formations f ON f.id = a.formation_id
                ORDER BY f.libelle COLLATE NOCASE"""
        ).fetchall()
    par_membre: dict = {}
    for a in attributions:
        par_membre.setdefault(a["membre_id"], []).append(
            {"id": a["id"], "formation_id": a["formation_id"],
             "libelle": a["libelle"], "fait": bool(a["fait"])}
        )
    return {"membres": [
        {"id": r["id"], "user_id": r["user_id"], "nom": r["nom"], "email": r["email"],
         "role": r["role"], "actif": bool(r["actif"]),
         "ajoute_le": r["ajoute_le"], "ajoute_par": r["ajoute_par"],
         "reglement_signe": bool(r["reglement_signe"]),
         "formations": par_membre.get(r["id"], [])}
        for r in rows
    ]}


@router.post("/membres")
def add_membre(payload: MembreIn, request: Request):
    user = _require(request)
    with get_db() as conn:
        emp = conn.execute("SELECT id, nom FROM users WHERE id=?", (payload.user_id,)).fetchone()
        if not emp:
            raise HTTPException(404, "Employé introuvable.")
        cur = conn.execute(
            "INSERT OR IGNORE INTO rh_outil_membres (user_id, ajoute_le, ajoute_par) VALUES (?,?,?)",
            (emp["id"], _now(), user.get("nom")),
        )
        conn.commit()
        if not cur.rowcount:
            raise HTTPException(409, "Employé déjà dans la liste.")
    log_action(user=user, action="CREATE", module="rh_outil",
               objet=f"Outil RH · ajout de {emp['nom']}", request=request)
    return {"success": True}


@router.patch("/membres/{membre_id}")
def update_membre(membre_id: int, payload: MembrePatch, request: Request):
    user = _require(request)
    data = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if k in CHECKLIST}
    if not data:
        return {"success": True}
    with get_db() as conn:
        row = _membre(conn, membre_id)
        # Les clés viennent de CHECKLIST, jamais de la requête : pas d'injection.
        sets = ", ".join(f"{k}=?" for k in data)
        conn.execute(f"UPDATE rh_outil_membres SET {sets} WHERE id=?",
                     [1 if v else 0 for v in data.values()] + [membre_id])
        conn.commit()
    for k, v in data.items():
        log_action(user=user, action="UPDATE", module="rh_outil",
                   objet=f"Outil RH · {row['nom']} · {CHECKLIST[k]} : {'oui' if v else 'non'}",
                   request=request)
    return {"success": True}


@router.delete("/membres/{membre_id}")
def delete_membre(membre_id: int, request: Request):
    user = _require(request)
    with get_db() as conn:
        row = _membre(conn, membre_id)
        conn.execute("DELETE FROM rh_outil_membre_formations WHERE membre_id=?", (membre_id,))
        conn.execute("DELETE FROM rh_outil_membres WHERE id=?", (membre_id,))
        conn.commit()
    log_action(user=user, action="DELETE", module="rh_outil",
               objet=f"Outil RH · retrait de {row['nom']}", request=request)
    return {"success": True}


# ─── Catalogue des formations ─────────────────────────────────────────────

@router.get("/formations")
def list_formations(request: Request):
    _require(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT f.id, f.libelle,
                      (SELECT COUNT(*) FROM rh_outil_membre_formations a
                        WHERE a.formation_id = f.id) AS nb_employes
                 FROM rh_outil_formations f
                ORDER BY f.libelle COLLATE NOCASE"""
        ).fetchall()
    return {"formations": [
        {"id": r["id"], "libelle": r["libelle"], "nb_employes": r["nb_employes"]}
        for r in rows
    ]}


@router.post("/formations")
def add_formation(payload: FormationIn, request: Request):
    user = _require(request)
    libelle = _libelle(payload.libelle)
    with get_db() as conn:
        if _doublon(conn, libelle):
            raise HTTPException(409, "Cette formation existe déjà au catalogue.")
        cur = conn.execute(
            "INSERT INTO rh_outil_formations (libelle, cree_le, cree_par) VALUES (?,?,?)",
            (libelle, _now(), user.get("nom")),
        )
        conn.commit()
    log_action(user=user, action="CREATE", module="rh_outil",
               objet=f"Outil RH · formation « {libelle} » ajoutée au catalogue", request=request)
    return {"success": True, "id": cur.lastrowid}


@router.put("/formations/{formation_id}")
def rename_formation(formation_id: int, payload: FormationIn, request: Request):
    user = _require(request)
    libelle = _libelle(payload.libelle)
    with get_db() as conn:
        row = conn.execute("SELECT libelle FROM rh_outil_formations WHERE id=?",
                           (formation_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Formation introuvable.")
        if row["libelle"] == libelle:
            return {"success": True}
        if _doublon(conn, libelle, formation_id):
            raise HTTPException(409, "Cette formation existe déjà au catalogue.")
        conn.execute("UPDATE rh_outil_formations SET libelle=? WHERE id=?", (libelle, formation_id))
        conn.commit()
    log_action(user=user, action="UPDATE", module="rh_outil",
               objet=f"Outil RH · formation « {row['libelle']} » renommée « {libelle} »",
               request=request)
    return {"success": True}


@router.delete("/formations/{formation_id}")
def delete_formation(formation_id: int, request: Request):
    """Supprime la formation du catalogue ET de tous les employés qui l'ont."""
    user = _require(request)
    with get_db() as conn:
        row = conn.execute("SELECT libelle FROM rh_outil_formations WHERE id=?",
                           (formation_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Formation introuvable.")
        n = conn.execute("DELETE FROM rh_outil_membre_formations WHERE formation_id=?",
                         (formation_id,)).rowcount
        conn.execute("DELETE FROM rh_outil_formations WHERE id=?", (formation_id,))
        conn.commit()
    log_action(user=user, action="DELETE", module="rh_outil",
               objet=f"Outil RH · formation « {row['libelle']} » supprimée ({n} employé(s))",
               request=request)
    return {"success": True}


# ─── Formations d'un employé ──────────────────────────────────────────────

@router.post("/membres/{membre_id}/formations")
def add_attribution(membre_id: int, payload: AttributionIn, request: Request):
    user = _require(request)
    with get_db() as conn:
        m = _membre(conn, membre_id)
        f = conn.execute("SELECT libelle FROM rh_outil_formations WHERE id=?",
                         (payload.formation_id,)).fetchone()
        if not f:
            raise HTTPException(404, "Formation introuvable.")
        cur = conn.execute(
            """INSERT OR IGNORE INTO rh_outil_membre_formations
                   (membre_id, formation_id, fait, ajoute_le) VALUES (?,?,0,?)""",
            (membre_id, payload.formation_id, _now()),
        )
        conn.commit()
        if not cur.rowcount:
            raise HTTPException(409, "Cet employé a déjà cette formation.")
    log_action(user=user, action="ASSIGN", module="rh_outil",
               objet=f"Outil RH · {m['nom']} · formation « {f['libelle']} » attribuée",
               request=request)
    return {"success": True}


def _attribution(conn, attribution_id: int):
    row = conn.execute(
        """SELECT a.id, f.libelle, u.nom
             FROM rh_outil_membre_formations a
             JOIN rh_outil_formations f ON f.id = a.formation_id
             JOIN rh_outil_membres m ON m.id = a.membre_id
             JOIN users u ON u.id = m.user_id
            WHERE a.id=?""",
        (attribution_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Formation introuvable pour cet employé.")
    return row


@router.patch("/membre-formations/{attribution_id}")
def update_attribution(attribution_id: int, payload: AttributionPatch, request: Request):
    user = _require(request)
    with get_db() as conn:
        row = _attribution(conn, attribution_id)
        conn.execute("UPDATE rh_outil_membre_formations SET fait=? WHERE id=?",
                     (1 if payload.fait else 0, attribution_id))
        conn.commit()
    log_action(user=user, action="UPDATE", module="rh_outil",
               objet=f"Outil RH · {row['nom']} · formation « {row['libelle']} » : "
                     f"{'faite' if payload.fait else 'à faire'}",
               request=request)
    return {"success": True}


@router.delete("/membre-formations/{attribution_id}")
def delete_attribution(attribution_id: int, request: Request):
    user = _require(request)
    with get_db() as conn:
        row = _attribution(conn, attribution_id)
        conn.execute("DELETE FROM rh_outil_membre_formations WHERE id=?", (attribution_id,))
        conn.commit()
    log_action(user=user, action="DELETE", module="rh_outil",
               objet=f"Outil RH · {row['nom']} · formation « {row['libelle']} » retirée",
               request=request)
    return {"success": True}
