"""MyStock — écarts de mouvements matières entre MySifa et RVGI.

Toute la logique vit dans `app/services/ecarts_mouvements_rvgi.py` ; ce router
tient l'accès, la fenêtre de temps et la fraîcheur du miroir.
"""
from fastapi import APIRouter, HTTPException, Request

from app.core.database import get_db
from app.routers.stock import require_stock_matieres_admin

router = APIRouter(tags=["stock-ecarts-rvgi"])


def _fraicheur_miroir(miroir) -> str:
    """Date du dernier import du miroir, ou chaîne vide."""
    try:
        m = miroir.meta() or {}
    except Exception:
        return ""
    # `releve_le` est l'heure de l'extraction RVGI ; `importe_le` celle de la
    # reconstruction du miroir, toujours postérieure.
    return str(m.get("releve_le") or m.get("importe_le") or "")


@router.get("/api/stock/ecarts-rvgi")
def ecarts_rvgi(request: Request, heures: float = 48, debut: str = "", fin: str = ""):
    """Entrées et sorties de matières des deux côtés, sur une fenêtre de temps.

    Par défaut les 48 dernières heures ; `debut`/`fin` (AAAA-MM-JJ ou
    AAAA-MM-JJTHH:MM) pour une période choisie, 31 jours au plus.
    """
    require_stock_matieres_admin(request)
    from app.services import erp_mirror as miroir
    from app.services import ecarts_mouvements_rvgi as em

    if not miroir.miroir_present():
        raise HTTPException(503, "Le miroir de l'ERP n'a pas encore été construit.")
    try:
        d, f = em.fenetre(heures=heures, debut=debut or None, fin=fin or None)
    except ValueError as e:
        raise HTTPException(400, str(e)) from None

    try:
        with get_db() as conn, miroir.get_erp_db() as erp:
            res = em.comparer(conn, erp, d, f)
    except FileNotFoundError as e:
        raise HTTPException(503, str(e)) from None

    maj = _fraicheur_miroir(miroir)
    res["miroir_importe_le"] = maj or None
    # Un mouvement saisi dans RVGI après le dernier import n'est pas dans le
    # miroir : l'écran doit le dire, sinon il le compterait comme manquant.
    res["miroir_en_retard"] = bool(maj) and maj.replace("T", " ")[:19] < f
    return res
