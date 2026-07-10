"""
Kernse — modèles Pydantic pour la console plateforme.

Ces modèles servent de contrats API (in/out) et de représentation typée en
mémoire. Ne jamais renvoyer un `dict` de la DB en direct — passer par un
modèle pour filtrer les champs sensibles avant sérialisation.
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, field_validator


PLAN_KEYS = {"atelier", "usine", "custom"}


class Client(BaseModel):
    """Représentation complète d'un client actif."""

    id: str
    slug: str
    company_name: str
    subdomain: str
    port: int
    plan: str
    deployed_ref: str = ""
    deployed_at: str | None = None
    pinned: bool = False
    pinned_at: str | None = None
    pinned_reason: str | None = None
    suspended: bool = False
    suspended_at: str | None = None
    suspended_reason: str | None = None
    terminated_at: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    contact_email: str
    contact_name: str | None = None
    created_at: str
    created_by: str

    @classmethod
    def from_row(cls, row: dict) -> "Client":
        """Reconstruit un Client depuis une ligne de la table `clients`."""
        options_raw = row.get("options_json") or "{}"
        try:
            options = json.loads(options_raw)
        except (TypeError, ValueError):
            options = {}
        return cls(
            id=row["id"],
            slug=row["slug"],
            company_name=row["company_name"],
            subdomain=row["subdomain"],
            port=row["port"],
            plan=row["plan"],
            deployed_ref=row.get("deployed_ref") or "",
            deployed_at=row.get("deployed_at"),
            pinned=bool(row.get("pinned")),
            pinned_at=row.get("pinned_at"),
            pinned_reason=row.get("pinned_reason"),
            suspended=bool(row.get("suspended")),
            suspended_at=row.get("suspended_at"),
            suspended_reason=row.get("suspended_reason"),
            terminated_at=row.get("terminated_at"),
            options=options,
            contact_email=row["contact_email"],
            contact_name=row.get("contact_name"),
            created_at=row["created_at"],
            created_by=row["created_by"],
        )


class ClientCreate(BaseModel):
    """Payload pour créer un client depuis la console plateforme."""

    slug: str = Field(min_length=2, max_length=40, pattern=r"^[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?$")
    company_name: str = Field(min_length=1, max_length=120)
    subdomain: str = Field(min_length=3, max_length=64)
    plan: str = "atelier"
    contact_email: str
    contact_name: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)

    @field_validator("plan")
    @classmethod
    def _plan_ok(cls, v: str) -> str:
        if v not in PLAN_KEYS:
            raise ValueError(f"plan invalide: {v!r} (attendu {sorted(PLAN_KEYS)})")
        return v


class PromoteRequest(BaseModel):
    """Payload d'une promotion (client individuel ou mass promote)."""

    git_ref: str = Field(min_length=4, max_length=40, description="SHA git ou tag")
    notes: str | None = None
    # Pour un promote client individuel : pin_after=True par défaut (règle acceptée
    # par Eugène). Peut être surchargé si besoin ponctuel de synchro sans pin.
    pin_after: bool = True


class UnpinRequest(BaseModel):
    """Détache l'épingle d'un client pour qu'il redevienne éligible aux
    promotions de masse."""

    reason: str | None = None


class PromoteAllRequest(BaseModel):
    """Mass promote : déploie sur tous les clients actifs non-épinglés."""

    git_ref: str = Field(min_length=4, max_length=40)
    notes: str | None = None


class PromotionResult(BaseModel):
    """Retour d'une promotion (individuelle ou de masse)."""

    ok: bool
    client_id: str | None = None
    slug: str | None = None
    from_ref: str | None = None
    to_ref: str
    healthcheck_ok: bool
    rolled_back: bool = False
    duration_seconds: float
    error: str | None = None


class MassPromotionResult(BaseModel):
    ok: bool
    to_ref: str
    total_eligible: int
    promoted: list[PromotionResult] = Field(default_factory=list)
    skipped_pinned: list[str] = Field(default_factory=list)  # slugs
    skipped_suspended: list[str] = Field(default_factory=list)
    failures: list[PromotionResult] = Field(default_factory=list)
    duration_seconds: float
