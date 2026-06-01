"""
Pont API — Access → MySifa
Authentification : header X-Api-Key
Scope requis : of:read (lecture) / of:write (écriture)

Endpoints :
  GET  /api/bridge/health      → ping sans auth
  GET  /api/bridge/of          → liste les OF importés (of:read)
  POST /api/bridge/of          → pousse un OF depuis Access (of:write)
  GET  /api/bridge/fiches      → liste les fiches techniques importées (of:read)
"""
import hashlib
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.database import get_db

router = APIRouter(prefix="/api/bridge", tags=["bridge"])


# ── Auth ──────────────────────────────────────────────────────────────

def _require_scope(raw_key: Optional[str], required_scope: str) -> None:
    if not raw_key:
        raise HTTPException(status_code=401, detail="Clé API manquante (header X-Api-Key).")
    h = hashlib.sha256(raw_key.encode()).hexdigest()
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, scopes, is_active FROM api_keys WHERE key_hash=? LIMIT 1", (h,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Clé API invalide.")
        if not row["is_active"]:
            raise HTTPException(status_code=403, detail="Clé API révoquée.")
        scopes = [s.strip() for s in (row["scopes"] or "").split(",")]
        if required_scope not in scopes:
            raise HTTPException(
                status_code=403,
                detail=f"Scope '{required_scope}' non autorisé pour cette clé."
            )
        try:
            conn.execute(
                "UPDATE api_keys SET last_used_at=? WHERE id=?",
                (datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), row["id"])
            )
            conn.commit()
        except Exception:
            pass


# ── Modèle ────────────────────────────────────────────────────────────

class OFPushIn(BaseModel):
    # Champs Access → of_imports
    numero_of: str                          # t_of.numero_of  → of_imports.of_numero
    date_creation: Optional[str] = None     # t_of.date_creation
    format: Optional[str] = None            # t_of.format
    qte_etiquettes: Optional[float] = None  # t_of.theorique_quantite
    qte_bobines: Optional[float] = None     # t_of.theorique_quantite_bobine
    # Champs optionnels supplémentaires (extensible)
    reference: Optional[str] = None
    machine: Optional[str] = None
    laize: Optional[float] = None
    matiere: Optional[str] = None
    delai_client: Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/health")
def bridge_health():
    return {"status": "ok", "service": "mysifa-bridge"}


@router.get("/of")
def list_of_imports(x_api_key: Optional[str] = Header(default=None)):
    """Liste les OFs importés, du plus récent au plus ancien."""
    _require_scope(x_api_key, "of:read")
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, of_numero, date_creation, format,
                      qte_etiquettes, qte_bobines, statut, date_import
               FROM of_imports
               ORDER BY date_import DESC
               LIMIT 500"""
        ).fetchall()
    return {"of": [dict(r) for r in rows]}


@router.get("/fiches")
def list_fiches_bridge(x_api_key: Optional[str] = Header(default=None)):
    """Liste les références de fiches techniques déjà importées."""
    _require_scope(x_api_key, "of:read")
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, reference, designation, client, source, date_import
               FROM fiches_techniques
               ORDER BY date_import DESC
               LIMIT 500"""
        ).fetchall()
    return {"fiches": [dict(r) for r in rows]}


@router.post("/of")
def push_of(
    body: OFPushIn,
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Pousse un OF depuis Access vers of_imports.

    Idempotent : si of_numero existe déjà dans of_imports, retourne
    {"inserted": false, "reason": "already_exists"} sans modifier les données.
    """
    _require_scope(x_api_key, "of:write")

    numero = body.numero_of.strip()
    if not numero:
        raise HTTPException(status_code=400, detail="numero_of est obligatoire.")

    with get_db() as conn:
        # Vérification doublon — ne jamais écraser un OF existant
        existing = conn.execute(
            "SELECT id FROM of_imports WHERE TRIM(of_numero)=? LIMIT 1",
            (numero,)
        ).fetchone()
        if existing:
            return {
                "inserted": False,
                "reason": "already_exists",
                "id": existing["id"],
                "of_numero": numero,
            }

        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        cur = conn.execute(
            """INSERT INTO of_imports
               (of_numero, date_creation, format, qte_etiquettes, qte_bobines,
                reference, machine, laize, matiere, delai_client,
                date_import, imported_by, statut)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                numero,
                body.date_creation,
                body.format,
                body.qte_etiquettes,
                body.qte_bobines,
                body.reference,
                body.machine,
                body.laize,
                body.matiere,
                body.delai_client,
                now,
                "access_bridge",
                "en_attente",
            )
        )
        conn.commit()
        return {
            "inserted": True,
            "id": cur.lastrowid,
            "of_numero": numero,
        }


class FicheTechniqueIn(BaseModel):
    reference:       str
    designation:     Optional[str] = None
    client:          Optional[str] = None
    format:          Optional[str] = None
    laize:           Optional[float] = None
    matiere:         Optional[str] = None
    adhesif:         Optional[str] = None
    nb_couleurs:     Optional[int] = None
    conditionnement: Optional[str] = None
    notes:           Optional[str] = None


@router.post("/fiche-technique")
def push_fiche_technique(
    body: FicheTechniqueIn,
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Crée ou met à jour une fiche technique (upsert par référence).
    Si la référence existe déjà : mise à jour des champs fournis.
    Scope requis : of:write
    """
    _require_scope(x_api_key, "of:write")
    ref = body.reference.strip()
    if not ref:
        raise HTTPException(status_code=400, detail="Le champ 'reference' est obligatoire.")

    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM fiches_techniques WHERE LOWER(TRIM(reference))=LOWER(TRIM(?)) LIMIT 1",
            (ref,)
        ).fetchone()
        if existing:
            fields = {k: v for k, v in body.model_dump().items() if k != "reference" and v is not None}
            if fields:
                conn.execute(
                    f"UPDATE fiches_techniques SET {', '.join(f'{k}=?' for k in fields)} WHERE id=?",
                    list(fields.values()) + [existing["id"]],
                )
                conn.commit()
            return {"action": "updated", "id": existing["id"], "reference": ref}
        else:
            cur = conn.execute(
                """INSERT INTO fiches_techniques
                   (reference, designation, client, format, laize, matiere,
                    adhesif, nb_couleurs, conditionnement, notes, source, date_import, imported_by)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (ref, body.designation, body.client, body.format, body.laize,
                 body.matiere, body.adhesif, body.nb_couleurs, body.conditionnement,
                 body.notes, "access_bridge", now, "access_bridge")
            )
            conn.commit()
            return {"action": "created", "id": cur.lastrowid, "reference": ref}
