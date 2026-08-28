"""Lecture SQL de diagnostic — super administrateur réel uniquement.

Endpoint :
  POST /api/diagnostic/query   → un SELECT encadré par app/services/diagnostic_sql.py

L'encadrement n'est pas ici : il est dans le service, appliqué par l'autoriseur
de SQLite. Ce module ne fait que trois choses que le service ne peut pas faire —
vérifier qui appelle, borner ce qui est rendu, et laisser une trace.

Le garde est `require_superadmin`, pas `require_settings`. `require_settings`
est l'union des sections Paramètres : il ouvrirait le SELECT libre à la
direction, à la comptabilité et aux trois rôles administration, qui y accèdent
pour les Contacts ou le registre FSC.

`require_superadmin` lit le rôle **en base** (`is_real_superadmin`), pas le rôle
effectif : un super-admin qui joue un rôle simulé garde donc le panneau. C'est
volontaire et aligné sur /settings, qui reste ouvert au vrai super-admin pendant
une impersonation pour lui laisser un chemin de sortie. Ce n'est pas une
élévation : c'est la même personne, avec le même rôle en base.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from config import DB_PATH
from app.services import diagnostic_sql
from app.services.audit_service import log_action
from app.services.auth_service import require_superadmin

router = APIRouter(tags=["diagnostic"])

# Au-delà, ce n'est plus une requête de diagnostic tapée à la main.
SQL_MAX_CARACTERES = 4000


class RequeteDiagnostic(BaseModel):
    sql: str
    lignes_max: Optional[int] = None


def _journaliser(user: dict, ip: Optional[str], sql: str, detail: dict) -> None:
    """Trace la requête, jamais son résultat.

    Le SQL montre ce qui a été demandé ; les lignes rendues, elles, peuvent
    contenir n'importe quelle donnée de la base et n'ont rien à faire dans
    `audit_logs`. On journalise donc l'intention et le volume, pas le contenu.
    """
    log_action(
        user=user,
        action="SEARCH",
        module="settings",
        objet="Diagnostic SQL",
        detail={"sql": sql[:SQL_MAX_CARACTERES], **detail},
        ip=ip,
    )


@router.post("/api/diagnostic/query")
def diagnostic_query(request: Request, body: RequeteDiagnostic):
    """Exécute une lecture encadrée sur la base de l'instance.

    La base lue est `DB_PATH` — celle de l'instance qui répond, définie dans
    `.env`. Une instance ne débogue que ses propres données.
    """
    user = require_superadmin(request)
    ip = request.client.host if request.client else None

    sql = (body.sql or "").strip()
    if not sql:
        raise HTTPException(status_code=400, detail="Requête vide.")
    if len(sql) > SQL_MAX_CARACTERES:
        raise HTTPException(
            status_code=400,
            detail=f"Requête trop longue — {SQL_MAX_CARACTERES} caractères au maximum.",
        )

    lignes_max = diagnostic_sql.LIGNES_MAX
    if body.lignes_max is not None:
        try:
            demande = int(body.lignes_max)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="lignes_max doit être un entier.") from None
        # Bornée des deux côtés : le client peut demander moins, jamais plus.
        lignes_max = max(1, min(demande, diagnostic_sql.LIGNES_MAX))

    try:
        resultat = diagnostic_sql.executer(DB_PATH, sql, lignes_max=lignes_max)
    except (diagnostic_sql.DiagnosticRefus, diagnostic_sql.DiagnosticTropLong) as exc:
        # Un refus se journalise comme une réussite : c'est même la ligne la
        # plus intéressante du journal.
        _journaliser(user, ip, sql, {"refus": str(exc)})
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _journaliser(user, ip, sql, {
        "nb_lignes": resultat["nb_lignes"],
        "tronque": resultat["tronque"],
        "duree_ms": resultat["duree_ms"],
    })
    return {"success": True, **resultat}


@router.get("/api/diagnostic/tables")
def diagnostic_tables(request: Request):
    """Les tables lisibles, pour que le panneau puisse les afficher.

    Rend la liste blanche telle qu'elle est déclarée, pas le schéma de la base :
    une table absente de la liste n'a pas à être nommée ici.
    """
    require_superadmin(request)
    return {
        "tables": sorted(diagnostic_sql.TABLES_LISIBLES),
        "lignes_max": diagnostic_sql.LIGNES_MAX,
    }
