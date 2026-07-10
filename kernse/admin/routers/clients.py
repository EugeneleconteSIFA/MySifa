"""
Kernse-admin — routes /clients : liste, fiche, création.

Note : la promotion est traitée dans routers/promotion.py (endpoints
séparés pour clarté et pour permettre un rate-limit dédié plus tard).
"""
from __future__ import annotations

import json
import uuid

from kernse.shared.auth.dependency import SuperadminContext, require_superadmin

from fastapi import APIRouter, Depends, HTTPException, Request

from kernse.shared.db.database import (
    get_client,
    list_active_clients,
    log_audit,
    platform_db,
)
from kernse.shared.db.schema import utcnow_iso
from kernse.shared.models.client import Client, ClientCreate


router = APIRouter(prefix="/api/v1/clients", tags=["clients"])



@router.get("")
def list_clients(_ctx: SuperadminContext = Depends(require_superadmin)) -> list[dict]:
    """Renvoie la liste des clients actifs (non-résiliés) triée par nom.

    Les épinglés sont mélangés au reste — le front affiche un badge distinct.
    """
    with platform_db() as conn:
        rows = list_active_clients(conn)
    return [Client.from_row(r).model_dump() for r in rows]


@router.get("/{client_id}")
def get_one(client_id: str, _ctx: SuperadminContext = Depends(require_superadmin)) -> dict:
    with platform_db() as conn:
        row = get_client(conn, client_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Client introuvable.")
    return Client.from_row(row).model_dump()


@router.post("", status_code=201)
def create_client(
    payload: ClientCreate,
    request: Request,
    ctx: SuperadminContext = Depends(require_superadmin),
) -> dict:
    """Crée un client (SEULEMENT l'enregistrement plateforme).

    NB : ne provisionne PAS l'instance FastAPI + DB + nginx + certbot — c'est
    le rôle de `kernse/provisioning/provision_client.sh` invoqué séparément
    depuis la fiche client. On sépare volontairement l'inscription plateforme
    de l'infrastructure : on peut ainsi préparer un contrat client avant
    d'exposer une URL publique.
    """
    now = utcnow_iso()
    client_id = str(uuid.uuid4())

    with platform_db() as conn:
        # Unicité slug + subdomain + port (le port est choisi automatiquement).
        clash = conn.execute(
            "SELECT slug FROM clients WHERE slug=? OR subdomain=? LIMIT 1",
            (payload.slug, payload.subdomain),
        ).fetchone()
        if clash:
            raise HTTPException(
                status_code=409,
                detail=f"slug ou subdomain déjà utilisé (existant : {clash['slug']}).",
            )

        # Attribue le prochain port libre >= 8200.
        max_port = conn.execute("SELECT COALESCE(MAX(port), 8199) AS m FROM clients").fetchone()
        next_port = int(max_port["m"]) + 1

        conn.execute(
            """
            INSERT INTO clients (
                id, slug, company_name, subdomain, port, plan,
                deployed_ref, pinned, suspended,
                options_json, contact_email, contact_name,
                created_at, created_by
            )
            VALUES (?, ?, ?, ?, ?, ?, '', 0, 0, ?, ?, ?, ?, ?)
            """,
            (
                client_id,
                payload.slug,
                payload.company_name,
                payload.subdomain,
                next_port,
                payload.plan,
                json.dumps(payload.options, ensure_ascii=False),
                payload.contact_email,
                payload.contact_name,
                now,
                ctx.email,
            ),
        )
        log_audit(
            conn,
            actor_email=ctx.email,
            actor_ip=request.client.host if request.client else None,
            action="create_client",
            entity_type="client",
            entity_id=client_id,
            before=None,
            after={
                "slug": payload.slug,
                "company_name": payload.company_name,
                "subdomain": payload.subdomain,
                "port": next_port,
                "plan": payload.plan,
            },
        )

    with platform_db() as conn:
        row = get_client(conn, client_id)
    return Client.from_row(row).model_dump()
