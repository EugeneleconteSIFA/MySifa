"""MyTraduction — endpoints API pour DeepL."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from database import get_db
from services.auth_service import get_current_user
from app.services.translate_service import (
    SUPPORTED_LANGS,
    get_usage,
    translate,
)

router = APIRouter(prefix="/api/translate", tags=["mytraduction"])


class TranslateIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=100_000)
    target_lang: str = Field(..., min_length=2, max_length=5)
    source_lang: Optional[str] = Field(None, min_length=2, max_length=5)
    formality: str = Field("default", max_length=20)


@router.get("/langs")
def api_translate_langs(request: Request):
    """Liste des langues supportées par MyTraduction (code + label FR)."""
    get_current_user(request)  # accès pour tous les utilisateurs connectés
    return {
        "langs": [{"code": code, "label": label} for code, label in SUPPORTED_LANGS],
    }


@router.post("")
def api_translate(payload: TranslateIn, request: Request):
    """Traduit un texte via DeepL avec cache. Toast d'erreur côté UI si 4xx/5xx."""
    user = get_current_user(request)
    with get_db() as conn:
        result = translate(
            conn,
            text=payload.text,
            target_lang=payload.target_lang,
            source_lang=payload.source_lang,
            formality=payload.formality,
            user_id=user.get("id"),
        )
    return result


@router.get("/usage")
def api_translate_usage(request: Request):
    """Retourne l'usage du mois + quota DeepL restant (si disponible)."""
    user = get_current_user(request)
    with get_db() as conn:
        return get_usage(conn, user_id=user.get("id"))
