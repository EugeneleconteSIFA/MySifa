"""MySifa — Outil RH (MyCompta) : contrat d'un employé suivi.

Le contrat (type, date de début, date de fin) est stocké dans la fiche Paie
(paie_employes), seule source du statut : la Paie et l'Outil RH lisent et
écrivent la même ligne. Ce module ne touche QUE ces trois colonnes ; le
salaire, le taux horaire, les primes et le matricule restent à la Paie.
Accès : celui de l'Outil RH (accès à MyCompta).
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from config import CONTRATS_DUREE_INDETERMINEE, CONTRATS_TYPES
from database import get_db
from services.audit_service import log_action
from app.routers.rh_outil import _attribuer_par_cible, _date, _jour_fr, _membre, _require

router = APIRouter(prefix="/api/rh-outil", tags=["rh_outil"])


class ContratIn(BaseModel):
    contrat_type: str
    debut: Optional[str] = None
    fin: Optional[str] = None


@router.put("/membres/{membre_id}/contrat")
def set_contrat(membre_id: int, payload: ContratIn, request: Request):
    """Crée ou met à jour le contrat dans la fiche Paie de l'employé."""
    user = _require(request)
    if payload.contrat_type not in CONTRATS_TYPES:
        raise HTTPException(400, "Type de contrat invalide.")
    debut = _date(payload.debut)
    fin = None if payload.contrat_type in CONTRATS_DUREE_INDETERMINEE else _date(payload.fin)
    if debut and fin and fin < debut:
        raise HTTPException(400, "La fin de contrat précède son début.")
    with get_db() as conn:
        m = _membre(conn, membre_id)
        user_id = conn.execute("SELECT user_id FROM rh_outil_membres WHERE id=?",
                               (membre_id,)).fetchone()["user_id"]
        now = datetime.now().isoformat()
        avant = conn.execute("SELECT contrat_type FROM paie_employes WHERE user_id=?", (user_id,)).fetchone()
        if avant:
            conn.execute(
                """UPDATE paie_employes SET contrat_type=?, date_debut=?, date_fin=?,
                          updated_at=?, updated_by=? WHERE user_id=?""",
                (payload.contrat_type, debut, fin, now, user.get("email"), user_id),
            )
        else:
            conn.execute(
                """INSERT INTO paie_employes (user_id, contrat_type, date_debut, date_fin, updated_at, updated_by)
                   VALUES (?,?,?,?,?,?)""",
                (user_id, payload.contrat_type, debut, fin, now, user.get("email")),
            )
        # Nouveau type de contrat : les documents administratifs exigés pour ce
        # contrat arrivent dans sa liste. Rien n'est retiré.
        n = 0
        if not avant or avant["contrat_type"] != payload.contrat_type:
            n = _attribuer_par_cible(conn, membre_id=membre_id, liste="documents")
        conn.commit()
    periode = (f" du {_jour_fr(debut)}" if debut else "") + (f" au {_jour_fr(fin)}" if fin else "")
    log_action(user=user, action="UPDATE", module="rh_outil",
               objet=f"Outil RH · {m['nom']} · contrat : {payload.contrat_type}{periode}"
                     + (f" · {n} document(s) attribué(s)" if n else ""),
               request=request)
    return {"success": True, "attribues": n}
