"""
Kernse-admin — routes /promotion : promouvoir un client, une masse, épingles.

Endpoints :

    POST /api/v1/promotion/client/{client_id}   promouvoir un client
    POST /api/v1/promotion/all                  promouvoir tous les non-épinglés
    POST /api/v1/promotion/client/{client_id}/unpin  détacher l'épingle

Toutes les actions passent par le service `promotion_service.py` qui
respecte l'audit trail et la règle métier « pin_after=True par défaut sur
un promote individuel ».
"""
from __future__ import annotations

from kernse.shared.auth.dependency import SuperadminContext, require_superadmin

from fastapi import APIRouter, Depends, HTTPException, Request

from kernse.admin.services.promotion_service import (
    PromotionError,
    promote_all,
    promote_client,
    unpin_client,
)
from kernse.shared.models.client import (
    MassPromotionResult,
    PromoteAllRequest,
    PromoteRequest,
    PromotionResult,
    UnpinRequest,
)


router = APIRouter(prefix="/api/v1/promotion", tags=["promotion"])



def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/client/{client_id}", response_model=PromotionResult)
def promote_one(
    client_id: str,
    payload: PromoteRequest,
    request: Request,
    ctx: SuperadminContext = Depends(require_superadmin),
) -> PromotionResult:
    """Promeut un client vers un ref git. Pose une épingle par défaut
    (règle : promotion individuelle = pin automatique).

    Passer `pin_after=false` pour synchroniser un client sans le sortir de la
    flotte (cas d'usage : recaler manuellement un client dont la promotion
    précédente avait échoué, sans qu'il devienne « à part »)."""
    try:
        return promote_client(
            client_id=client_id,
            git_ref=payload.git_ref,
            actor_email=ctx.email,
            actor_ip=_client_ip(request),
            notes=payload.notes,
            pin_after=payload.pin_after,
        )
    except PromotionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/all", response_model=MassPromotionResult)
def promote_everyone(
    payload: PromoteAllRequest,
    request: Request,
    ctx: SuperadminContext = Depends(require_superadmin),
) -> MassPromotionResult:
    """Promeut TOUS les clients éligibles (actifs et non-épinglés).

    Les clients épinglés sont volontairement ignorés — c'est la garantie
    donnée à un client qu'on ne « touche pas » à son instance sans son
    accord une fois qu'il a été promu individuellement."""
    try:
        return promote_all(
            git_ref=payload.git_ref,
            actor_email=ctx.email,
            actor_ip=_client_ip(request),
            notes=payload.notes,
        )
    except PromotionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/client/{client_id}/unpin")
def unpin(
    client_id: str,
    payload: UnpinRequest,
    request: Request,
    ctx: SuperadminContext = Depends(require_superadmin),
) -> dict:
    """Détache l'épingle d'un client — il redevient éligible aux promotions
    de masse dès la prochaine passe."""
    try:
        return unpin_client(
            client_id=client_id,
            actor_email=ctx.email,
            actor_ip=_client_ip(request),
            reason=payload.reason,
        )
    except PromotionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
