"""
Kernse-admin — endpoint de provisioning d'une instance client.

Une fois le client créé en DB (POST /api/v1/clients), on peut déclencher
la création physique de l'instance : dossier, venv, DB, systemd, nginx,
certbot, service start, healthcheck.

L'opération est longue (30-90s) et n'est PAS idempotente : impossible
de provisionner deux fois un même slug (le script sort en erreur).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from kernse.shared.auth.dependency import SuperadminContext, require_superadmin
from kernse.shared.db.database import get_client, log_audit, platform_db
from kernse.shared.db.schema import utcnow_iso


router = APIRouter(prefix="/api/v1/provision", tags=["provision"])


_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROVISION_SCRIPT = _REPO_ROOT / "kernse" / "provisioning" / "provision_client.sh"


class ProvisionRequest(BaseModel):
    """Options passées au script provision_client.sh."""

    starter_kit: str | None = Field(
        default=None,
        min_length=2,
        max_length=32,
        pattern=r"^[a-z_]+$",
        description="Jeu de démarrage métier (imprimerie, usinage, plasturgie, ...)",
    )
    notes: str | None = None


class ProvisionResult(BaseModel):
    ok: bool
    client_id: str
    slug: str
    subdomain: str | None = None
    port: int | None = None
    service: str | None = None
    deployed_ref: str | None = None
    starter_kit: str | None = None
    error: str | None = None


def _run_provision_shell(*, slug: str, subdomain: str, port: int, starter_kit: str | None) -> dict:
    script = str(DEFAULT_PROVISION_SCRIPT)
    args = ["sudo", "-n", script, slug, subdomain, str(port)]
    if starter_kit:
        args.append(starter_kit)

    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=600,  # provisioning peut prendre du temps (venv + pip)
        check=False,
    )
    out = proc.stdout or ""
    err = proc.stderr or ""

    last_json = ""
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            last_json = line
            break

    if not last_json:
        return {"ok": False, "error": f"provision_client.sh sans JSON. stderr={err[:400]!r}", "rc": proc.returncode}
    try:
        summary = json.loads(last_json)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"JSON invalide : {exc}", "raw": last_json[:400]}
    summary.setdefault("rc", proc.returncode)
    return summary


@router.post("/client/{client_id}", response_model=ProvisionResult)
def provision(
    client_id: str,
    payload: ProvisionRequest,
    request: Request,
    ctx: SuperadminContext = Depends(require_superadmin),
) -> ProvisionResult:
    """Provisionne physiquement l'instance client (script shell + certbot)."""
    with platform_db() as conn:
        row = get_client(conn, client_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Client inconnu.")
        if row["deployed_ref"]:
            raise HTTPException(
                status_code=409,
                detail=f"Instance déjà provisionnée (ref déployé : {row['deployed_ref']}).",
            )
        slug = row["slug"]
        subdomain = row["subdomain"]
        port = int(row["port"])

    summary = _run_provision_shell(
        slug=slug,
        subdomain=subdomain,
        port=port,
        starter_kit=payload.starter_kit,
    )

    with platform_db() as conn:
        if summary.get("ok"):
            conn.execute(
                """
                UPDATE clients
                SET deployed_ref = ?, deployed_at = ?, options_json = json_patch(options_json, ?)
                WHERE id = ?
                """,
                (
                    summary.get("deployed_ref") or "provisioned",
                    utcnow_iso(),
                    json.dumps({"starter_kit": payload.starter_kit, "provisioned_at": utcnow_iso()}),
                    client_id,
                ),
            )
            log_audit(
                conn,
                actor_email=ctx.email,
                actor_ip=request.client.host if request.client else None,
                action="provision_client",
                entity_type="client",
                entity_id=client_id,
                after={
                    "slug": slug,
                    "subdomain": subdomain,
                    "port": port,
                    "starter_kit": payload.starter_kit,
                    "deployed_ref": summary.get("deployed_ref"),
                },
                note=payload.notes,
            )
        else:
            log_audit(
                conn,
                actor_email=ctx.email,
                actor_ip=request.client.host if request.client else None,
                action="provision_client_failed",
                entity_type="client",
                entity_id=client_id,
                after={"slug": slug, "shell_summary": summary},
                note=payload.notes,
            )

    return ProvisionResult(
        ok=bool(summary.get("ok")),
        client_id=client_id,
        slug=slug,
        subdomain=summary.get("subdomain"),
        port=summary.get("port"),
        service=summary.get("service"),
        deployed_ref=summary.get("deployed_ref"),
        starter_kit=summary.get("starter_kit"),
        error=None if summary.get("ok") else summary.get("error"),
    )
