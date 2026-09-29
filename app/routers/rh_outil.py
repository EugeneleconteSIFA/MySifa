"""MySifa — Outil RH (onglet de MyCompta).

Liste partagée des employés suivis dans l'onglet « Outil RH ». On y ajoute un
employé choisi parmi tous les comptes (actifs ou non), on peut le retirer.
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


class MembreIn(BaseModel):
    user_id: int


class MembrePatch(BaseModel):
    reglement_signe: Optional[bool] = None


# Points de la checklist : champ de MembrePatch → libellé du journal.
# Chaque point est une colonne de rh_outil_membres (migration fichier).
CHECKLIST = {"reglement_signe": "Règlement signé"}


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
            """SELECT m.id, m.user_id, m.ajoute_le, m.ajoute_par, m.reglement_signe,
                      u.nom, u.email, u.role, u.actif
                 FROM rh_outil_membres m
                 JOIN users u ON u.id = m.user_id
                ORDER BY u.nom COLLATE NOCASE"""
        ).fetchall()
    return {"membres": [
        {"id": r["id"], "user_id": r["user_id"], "nom": r["nom"], "email": r["email"],
         "role": r["role"], "actif": bool(r["actif"]),
         "ajoute_le": r["ajoute_le"], "ajoute_par": r["ajoute_par"],
         "reglement_signe": bool(r["reglement_signe"])}
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


@router.patch("/membres/{membre_id}")
def update_membre(membre_id: int, payload: MembrePatch, request: Request):
    user = _require(request)
    data = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if k in CHECKLIST}
    if not data:
        return {"success": True}
    with get_db() as conn:
        row = conn.execute(
            """SELECT m.id, u.nom FROM rh_outil_membres m
                 JOIN users u ON u.id = m.user_id WHERE m.id=?""",
            (membre_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Employé introuvable dans la liste.")
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
