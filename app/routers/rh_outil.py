"""MySifa — Outil RH (onglet de MyCompta).

Liste partagée des employés suivis dans l'onglet « Outil RH ». On y ajoute un
employé choisi parmi tous les comptes (actifs ou non), on peut le retirer.
Accès : quiconque a accès à MyCompta (rôle ou exception réglée dans Paramètres).
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from database import get_db
from services.auth_service import get_current_user, user_has_app_access
from services.audit_service import log_action

router = APIRouter(prefix="/api/rh-outil", tags=["rh_outil"])


class MembreIn(BaseModel):
    user_id: int


def _require(request: Request) -> dict:
    u = get_current_user(request)
    if not user_has_app_access(u, "compta"):
        raise HTTPException(status_code=403, detail="Accès réservé à MyCompta")
    return u


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
            """SELECT m.id, m.user_id, m.ajoute_le, m.ajoute_par,
                      u.nom, u.email, u.role, u.actif
                 FROM rh_outil_membres m
                 JOIN users u ON u.id = m.user_id
                ORDER BY u.nom COLLATE NOCASE"""
        ).fetchall()
    return {"membres": [
        {"id": r["id"], "user_id": r["user_id"], "nom": r["nom"], "email": r["email"],
         "role": r["role"], "actif": bool(r["actif"]),
         "ajoute_le": r["ajoute_le"], "ajoute_par": r["ajoute_par"]}
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
            (emp["id"], datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), user.get("nom")),
        )
        conn.commit()
        if not cur.rowcount:
            raise HTTPException(409, "Employé déjà dans la liste.")
    log_action(user=user, action="CREATE", module="rh_outil",
               objet=f"Outil RH · ajout de {emp['nom']}", request=request)
    return {"success": True}


@router.delete("/membres/{membre_id}")
def delete_membre(membre_id: int, request: Request):
    user = _require(request)
    with get_db() as conn:
        row = conn.execute(
            """SELECT m.id, u.nom FROM rh_outil_membres m
                 JOIN users u ON u.id = m.user_id WHERE m.id=?""",
            (membre_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Employé introuvable dans la liste.")
        conn.execute("DELETE FROM rh_outil_membres WHERE id=?", (membre_id,))
        conn.commit()
    log_action(user=user, action="DELETE", module="rh_outil",
               objet=f"Outil RH · retrait de {row['nom']}", request=request)
    return {"success": True}
