"""API de comparaison des stocks — RVGI face à MySifa.

Lecture seule des deux côtés : on lit le miroir de RVGI, on lit le stock de
MySifa, on écrit uniquement l'instantané de comparaison. Aucune des deux
sources n'est corrigée par l'autre — c'est l'écart qui est l'indicateur.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from database import get_db
from app.services import erp_stock, stock_compare
from services.auth_service import require_admin

router = APIRouter(prefix="/api/stock-compare", tags=["stock-compare"])


def _perimetre(p: str) -> str:
    if p not in stock_compare.PERIMETRES:
        raise HTTPException(status_code=400, detail="Périmètre inconnu.")
    return p


@router.get("/etat")
def sc_etat(request: Request, perimetre: str = Query("pf", max_length=10)):
    """Ce que la comparaison porterait, et le dernier instantané pris."""
    require_admin(request)
    p = _perimetre(perimetre)
    try:
        cote_rvgi = erp_stock.resume(p)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    with get_db() as conn:
        hist = stock_compare.instantanes(conn, p, limite=1)
    return {"rvgi": cote_rvgi, "dernier": hist[0] if hist else None}


@router.post("/comparer")
def sc_comparer(request: Request, perimetre: str = Query("pf", max_length=10)):
    """Prend un instantané maintenant."""
    user = require_admin(request)
    p = _perimetre(perimetre)
    nom = (user.get("nom") or user.get("email") or "") if isinstance(user, dict) else ""
    try:
        with get_db() as conn:
            res = stock_compare.enregistrer(conn, p, nom, origine="manuel")
            conn.commit()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return res


@router.get("/instantanes")
def sc_instantanes(request: Request, perimetre: str = Query("pf", max_length=10),
                   limite: int = Query(40, ge=1, le=200)):
    require_admin(request)
    p = _perimetre(perimetre)
    with get_db() as conn:
        return {"instantanes": stock_compare.instantanes(conn, p, limite)}


@router.get("/instantanes/{instantane_id}")
def sc_lignes(instantane_id: int, request: Request,
              statut: str = Query("", max_length=16),
              q: str = Query("", max_length=80),
              limite: int = Query(500, ge=1, le=2000)):
    require_admin(request)
    if statut and statut not in ("ok", "ecart", "rvgi_seul", "mysifa_seul"):
        raise HTTPException(status_code=400, detail="Statut inconnu.")
    with get_db() as conn:
        entete = conn.execute(
            "SELECT * FROM stock_compare_instantanes WHERE id=?", (instantane_id,)
        ).fetchone()
        if entete is None:
            raise HTTPException(status_code=404, detail="Instantané introuvable.")
        res = stock_compare.lignes(conn, instantane_id, statut, q, limite)
    return {"instantane": dict(entete), **res}


@router.get("/suivi")
def sc_suivi(request: Request, reference: str = Query(..., max_length=60),
             perimetre: str = Query("pf", max_length=10)):
    """L'histoire d'une référence : un écart corrigé, ou un écart qui dure."""
    require_admin(request)
    p = _perimetre(perimetre)
    with get_db() as conn:
        return {"reference": reference, "suivi": stock_compare.suivi(conn, reference, p)}
