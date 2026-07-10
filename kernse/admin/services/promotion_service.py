"""
Kernse — service de promotion des instances clients.

Deux opérations :

    promote_client(client_id, git_ref, notes, actor, pin_after=True)
        Promeut un client vers un git ref (SHA court ou tag). Pose une épingle
        par défaut (règle : promotion individuelle = pin automatique).

    promote_all(git_ref, notes, actor)
        Promeut tous les clients actifs NON-ÉPINGLÉS vers le git ref. Les
        clients épinglés (individuellement promus) sont explicitement ignorés
        et listés dans le retour.

Implémentation :
    - Chaque promotion appelle `kernse/provisioning/promote_client.sh` via
      sudo (script owned root, whitelist sudoers).
    - Le shell backup la DB client, git checkout, restart le service systemd,
      hit /healthz, rollback auto si KO.
    - Le résultat (ok, healthcheck, rollback) est parsé depuis stdout du
      shell (une ligne JSON en dernier).
    - L'audit_log est écrit dans la MÊME transaction SQLite que la mise à
      jour de `clients` — jamais d'audit best-effort.

Sécurité :
    - Le git_ref est validé (whitelist regex) avant tout appel shell — pas
      d'injection.
    - Le slug est validé au niveau du modèle Pydantic (ClientCreate).
    - Le service ne s'auto-appelle jamais — seul le router admin invoque
      ces fonctions après auth superadmin plateforme.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

from kernse.shared.db.database import (
    get_client,
    list_promotable_clients,
    log_audit,
    platform_db,
)
from kernse.shared.db.schema import utcnow_iso
from kernse.shared.models.client import (
    MassPromotionResult,
    PromotionResult,
)


# Whitelist stricte des refs git acceptés : SHA hex (4-40) ou tag semver-like.
_GIT_REF_RE = re.compile(r"^[a-fA-F0-9]{4,40}$|^v?\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?$")


_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROMOTE_SCRIPT = _REPO_ROOT / "kernse" / "provisioning" / "promote_client.sh"


class PromotionError(RuntimeError):
    """Erreur métier de promotion (mauvais ref, client suspendu, script KO)."""


def _validate_git_ref(git_ref: str) -> str:
    ref = (git_ref or "").strip()
    if not _GIT_REF_RE.match(ref):
        raise PromotionError(
            f"Ref git invalide : {ref!r}. Attendu : SHA hex (4-40) ou tag semver."
        )
    return ref


def _run_promote_shell(slug: str, git_ref: str, notes: str | None) -> dict:
    """Appelle promote_client.sh en sudo. Retourne le JSON de sortie."""
    script = str(DEFAULT_PROMOTE_SCRIPT)
    args = ["sudo", "-n", script, slug, git_ref]
    if notes:
        args.append(notes[:200])  # tronque les notes trop longues

    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    out = proc.stdout or ""
    err = proc.stderr or ""

    # Le script écrit son résumé JSON en DERNIÈRE LIGNE non vide.
    last_json = ""
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            last_json = line
            break

    if not last_json:
        raise PromotionError(
            f"promote_client.sh n'a pas retourné de JSON. rc={proc.returncode}. "
            f"stderr={err[:400]!r}"
        )

    try:
        summary = json.loads(last_json)
    except json.JSONDecodeError as exc:
        raise PromotionError(f"JSON invalide de promote_client.sh : {exc}") from exc

    summary.setdefault("rc", proc.returncode)
    summary.setdefault("stderr_tail", err[-400:])
    return summary


# ─── Promotion individuelle ─────────────────────────────────────────────
def promote_client(
    *,
    client_id: str,
    git_ref: str,
    actor_email: str,
    actor_ip: str | None = None,
    notes: str | None = None,
    pin_after: bool = True,
) -> PromotionResult:
    """Promeut UN client vers un git ref. Pose une épingle par défaut."""
    ref = _validate_git_ref(git_ref)
    started = time.monotonic()

    with platform_db() as conn:
        row = get_client(conn, client_id)
        if row is None:
            raise PromotionError(f"Client inconnu : {client_id}")
        if row["suspended"]:
            raise PromotionError(f"Client {row['slug']} suspendu — promotion refusée.")
        if row["terminated_at"]:
            raise PromotionError(f"Client {row['slug']} résilié — promotion refusée.")

        from_ref = row.get("deployed_ref") or ""
        slug = row["slug"]

        # Appelle le shell hors transaction longue — on rouvre après pour audit.
    try:
        summary = _run_promote_shell(slug, ref, notes)
    except PromotionError as exc:
        duration = time.monotonic() - started
        # Trace l'échec sans modifier `clients` (ref inchangé).
        with platform_db() as conn:
            log_audit(
                conn,
                actor_email=actor_email,
                actor_ip=actor_ip,
                action="promote_client_failed",
                entity_type="client",
                entity_id=client_id,
                before={"deployed_ref": from_ref},
                after={"deployed_ref": from_ref, "attempted_ref": ref},
                note=str(exc),
            )
        return PromotionResult(
            ok=False,
            client_id=client_id,
            slug=slug,
            from_ref=from_ref,
            to_ref=ref,
            healthcheck_ok=False,
            rolled_back=False,
            duration_seconds=duration,
            error=str(exc),
        )

    healthcheck_ok = bool(summary.get("healthcheck_ok"))
    rolled_back = bool(summary.get("rolled_back"))
    ok = bool(summary.get("ok")) and healthcheck_ok and not rolled_back
    final_ref = summary.get("final_ref", from_ref if rolled_back else ref)
    duration = time.monotonic() - started

    with platform_db() as conn:
        # Recharger pour l'audit before/after cohérent.
        current = get_client(conn, client_id) or row
        before_snapshot = {
            "deployed_ref": current.get("deployed_ref"),
            "deployed_at":  current.get("deployed_at"),
            "pinned":       bool(current.get("pinned")),
            "pinned_at":    current.get("pinned_at"),
            "pinned_reason": current.get("pinned_reason"),
        }

        if not ok:
            # Rollback : on garde deployed_ref au ref d'origine.
            log_audit(
                conn,
                actor_email=actor_email,
                actor_ip=actor_ip,
                action="promote_client_rollback" if rolled_back else "promote_client_failed",
                entity_type="client",
                entity_id=client_id,
                before=before_snapshot,
                after={**before_snapshot, "attempted_ref": ref, "shell_summary": summary},
                note=notes,
            )
        else:
            new_pinned = 1 if pin_after else int(bool(current.get("pinned")))
            new_pinned_at = utcnow_iso() if pin_after else current.get("pinned_at")
            new_pinned_reason = (notes or "promotion individuelle") if pin_after else current.get("pinned_reason")

            conn.execute(
                """
                UPDATE clients
                SET deployed_ref = ?,
                    deployed_at  = ?,
                    pinned       = ?,
                    pinned_at    = ?,
                    pinned_reason = ?
                WHERE id = ?
                """,
                (
                    final_ref,
                    utcnow_iso(),
                    new_pinned,
                    new_pinned_at,
                    new_pinned_reason,
                    client_id,
                ),
            )
            after_snapshot = {
                "deployed_ref": final_ref,
                "deployed_at":  utcnow_iso(),
                "pinned":       bool(new_pinned),
                "pinned_at":    new_pinned_at,
                "pinned_reason": new_pinned_reason,
            }
            log_audit(
                conn,
                actor_email=actor_email,
                actor_ip=actor_ip,
                action="promote_client",
                entity_type="client",
                entity_id=client_id,
                before=before_snapshot,
                after=after_snapshot,
                note=notes,
            )

    return PromotionResult(
        ok=ok,
        client_id=client_id,
        slug=slug,
        from_ref=from_ref,
        to_ref=ref,
        healthcheck_ok=healthcheck_ok,
        rolled_back=rolled_back,
        duration_seconds=duration,
        error=None if ok else summary.get("error"),
    )


# ─── Promotion de masse ─────────────────────────────────────────────────
def promote_all(
    *,
    git_ref: str,
    actor_email: str,
    actor_ip: str | None = None,
    notes: str | None = None,
) -> MassPromotionResult:
    """Promeut tous les clients éligibles vers le git ref.

    Éligible = actif (non suspendu, non résilié) ET non-épinglé.

    Les épinglés sont conservés dans leur état — c'est la règle métier
    définitive (validée par Eugène) : un client individuellement promu est
    protégé des promotions de masse.
    """
    ref = _validate_git_ref(git_ref)
    started = time.monotonic()

    with platform_db() as conn:
        eligible_rows = list_promotable_clients(conn)
        # On liste aussi les épinglés/suspendus pour le retour.
        all_active = conn.execute(
            "SELECT slug, pinned, suspended, terminated_at FROM clients "
            "WHERE terminated_at IS NULL"
        ).fetchall()
        pinned_slugs = [r["slug"] for r in all_active if r["pinned"]]
        suspended_slugs = [r["slug"] for r in all_active if r["suspended"]]

    promoted: list[PromotionResult] = []
    failures: list[PromotionResult] = []

    for row in eligible_rows:
        try:
            result = promote_client(
                client_id=row["id"],
                git_ref=ref,
                actor_email=actor_email,
                actor_ip=actor_ip,
                notes=notes or "promotion de masse",
                pin_after=False,  # <-- mass promote NE PIN JAMAIS
            )
        except PromotionError as exc:
            result = PromotionResult(
                ok=False,
                client_id=row["id"],
                slug=row["slug"],
                from_ref=row.get("deployed_ref"),
                to_ref=ref,
                healthcheck_ok=False,
                rolled_back=False,
                duration_seconds=0.0,
                error=str(exc),
            )
        (promoted if result.ok else failures).append(result)

    duration = time.monotonic() - started

    with platform_db() as conn:
        log_audit(
            conn,
            actor_email=actor_email,
            actor_ip=actor_ip,
            action="promote_all",
            entity_type="platform",
            entity_id=None,
            before=None,
            after={
                "git_ref": ref,
                "total_eligible": len(eligible_rows),
                "promoted_count": len(promoted),
                "failure_count": len(failures),
                "skipped_pinned": pinned_slugs,
                "skipped_suspended": suspended_slugs,
            },
            note=notes,
        )

    return MassPromotionResult(
        ok=len(failures) == 0,
        to_ref=ref,
        total_eligible=len(eligible_rows),
        promoted=promoted,
        skipped_pinned=pinned_slugs,
        skipped_suspended=suspended_slugs,
        failures=failures,
        duration_seconds=duration,
    )


# ─── Épingle / détache ──────────────────────────────────────────────────
def unpin_client(
    *,
    client_id: str,
    actor_email: str,
    actor_ip: str | None = None,
    reason: str | None = None,
) -> dict:
    """Détache l'épingle d'un client. Le client redevient éligible aux
    promotions de masse dès le prochain appel."""
    with platform_db() as conn:
        row = get_client(conn, client_id)
        if row is None:
            raise PromotionError(f"Client inconnu : {client_id}")
        if not row["pinned"]:
            return {"ok": True, "already": True, "slug": row["slug"]}

        before = {
            "pinned": True,
            "pinned_at": row.get("pinned_at"),
            "pinned_reason": row.get("pinned_reason"),
        }
        conn.execute(
            "UPDATE clients SET pinned=0, pinned_at=NULL, pinned_reason=NULL WHERE id=?",
            (client_id,),
        )
        log_audit(
            conn,
            actor_email=actor_email,
            actor_ip=actor_ip,
            action="unpin_client",
            entity_type="client",
            entity_id=client_id,
            before=before,
            after={"pinned": False},
            note=reason,
        )
    return {"ok": True, "already": False, "slug": row["slug"]}
