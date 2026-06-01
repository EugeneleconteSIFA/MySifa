"""
Pont API — Access → MySifa
Authentification par clé API (header X-Api-Key), pas de session cookie.

Endpoints exposés :
  GET  /api/bridge/health           → ping sans auth
  GET  /api/bridge/machines         → liste des machines (planning:read)
  GET  /api/bridge/of               → liste des OFs en attente (planning:read)
  GET  /api/bridge/of/{numero_of}   → vérifie si un OF existe (planning:read)
  POST /api/bridge/of               → crée ou met à jour un OF (planning:write)
"""
import hashlib
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.database import get_db

router = APIRouter(prefix="/api/bridge", tags=["bridge"])


# ── Auth helper ───────────────────────────────────────────────────────

def _require_scope(raw_key: Optional[str], required_scope: str) -> None:
    """Vérifie la clé API et le scope requis. Lève 401/403 si invalide."""
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


# ── Modèle ───────────────────────────────────────────────────────────

class OFIn(BaseModel):
    # Identification de l'OF
    reference: str                        # référence dossier (obligatoire)
    numero_of: Optional[str] = None       # n° OF Access — clé de liaison avec planning manuel

    # Affectation machine — au moins un des deux requis
    machine_nom: Optional[str] = None     # ex: "Cohésio 1" — résolu vers machine_id
    machine_id: Optional[int] = None      # ou directement l'id machine

    # Données du dossier
    client: Optional[str] = None
    description: Optional[str] = None
    duree_heures: Optional[float] = 8.0
    format_l: Optional[float] = None
    format_h: Optional[float] = None
    laize: Optional[float] = None
    ref_produit: Optional[str] = None
    dos_rvgi: Optional[str] = None
    date_livraison: Optional[str] = None   # format: "YYYY-MM-DD"
    commentaire: Optional[str] = None
    exigences_production: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("/health")
def bridge_health():
    """Ping sans authentification."""
    return {"status": "ok", "service": "mysifa-bridge"}


@router.get("/machines")
def list_machines(x_api_key: Optional[str] = Header(default=None)):
    """Liste des machines disponibles (pour récupérer les IDs côté Access)."""
    _require_scope(x_api_key, "planning:read")
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, nom, code FROM machines WHERE actif=1 ORDER BY nom"
        ).fetchall()
    return {"machines": [dict(r) for r in rows]}


@router.get("/of")
def list_of(
    statut: Optional[str] = None,
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Liste les dossiers planning.
    Paramètre optionnel : ?statut=attente|en_cours|termine
    """
    _require_scope(x_api_key, "planning:read")
    with get_db() as conn:
        q = """SELECT pe.id, pe.reference, pe.numero_of, pe.client, pe.statut,
                      pe.machine_id, m.nom AS machine_nom, pe.duree_heures,
                      pe.date_livraison, pe.created_at
               FROM planning_entries pe
               JOIN machines m ON m.id = pe.machine_id"""
        params = []
        if statut:
            q += " WHERE pe.statut=?"
            params.append(statut)
        q += " ORDER BY pe.created_at DESC LIMIT 500"
        rows = conn.execute(q, params).fetchall()
    return {"of": [dict(r) for r in rows]}


@router.get("/of/{numero_of}")
def get_of(
    numero_of: str,
    x_api_key: Optional[str] = Header(default=None),
):
    """Vérifie si un OF existe déjà dans le planning (par numero_of ou reference)."""
    _require_scope(x_api_key, "planning:read")
    with get_db() as conn:
        row = conn.execute(
            """SELECT pe.id, pe.reference, pe.numero_of, pe.client, pe.statut,
                      pe.machine_id, m.nom AS machine_nom, pe.duree_heures
               FROM planning_entries pe
               JOIN machines m ON m.id = pe.machine_id
               WHERE LOWER(TRIM(pe.numero_of)) = LOWER(TRIM(?))
                  OR LOWER(TRIM(pe.reference)) = LOWER(TRIM(?))
               LIMIT 1""",
            (numero_of, numero_of)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="OF introuvable.")
    return dict(row)


@router.post("/of", status_code=201)
def push_of(
    body: OFIn,
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Crée ou met à jour un OF dans planning_entries.

    Logique :
    1. Si numero_of fourni et correspond à un planning_entries.numero_of existant
       → met à jour le dossier existant (liaison OF Access ↔ dossier planning manuel)
    2. Si reference correspond à un planning_entries.reference existant
       → met à jour le dossier existant
    3. Sinon → crée un nouveau dossier en position 9999 (fin de liste)

    machine_nom est résolu vers machine_id (insensible à la casse).
    Si ni machine_nom ni machine_id : erreur 400.
    """
    _require_scope(x_api_key, "planning:write")

    ref = body.reference.strip()
    if not ref:
        raise HTTPException(status_code=400, detail="Le champ 'reference' est obligatoire.")

    duree = body.duree_heures if body.duree_heures and body.duree_heures > 0 else 8.0

    with get_db() as conn:
        # ── Résolution machine ──────────────────────────────────────────
        machine_id = body.machine_id
        if not machine_id and body.machine_nom:
            m = conn.execute(
                "SELECT id FROM machines WHERE LOWER(TRIM(nom))=LOWER(TRIM(?)) AND actif=1 LIMIT 1",
                (body.machine_nom.strip(),)
            ).fetchone()
            if not m:
                raise HTTPException(
                    status_code=400,
                    detail=f"Machine '{body.machine_nom}' introuvable. Utilisez GET /api/bridge/machines pour la liste."
                )
            machine_id = m["id"]
        if not machine_id:
            raise HTTPException(
                status_code=400,
                detail="Précisez 'machine_nom' (ex: 'Cohésio 1') ou 'machine_id'."
            )

        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        # Champs à mettre à jour si l'OF existe déjà
        update_fields = {
            "reference":             ref,
            "client":                body.client,
            "description":           body.description,
            "duree_heures":          duree,
            "format_l":              body.format_l,
            "format_h":              body.format_h,
            "laize":                 body.laize,
            "ref_produit":           body.ref_produit,
            "dos_rvgi":              body.dos_rvgi,
            "date_livraison":        body.date_livraison,
            "commentaire":           body.commentaire,
            "exigences_production":  body.exigences_production,
            "updated_at":            now,
            "updated_by":            "access_bridge",
        }
        if body.numero_of:
            update_fields["numero_of"] = body.numero_of.strip()

        # ── Chercher si l'OF existe déjà ───────────────────────────────
        existing = None
        if body.numero_of:
            existing = conn.execute(
                "SELECT id, machine_id FROM planning_entries WHERE LOWER(TRIM(numero_of))=LOWER(TRIM(?)) LIMIT 1",
                (body.numero_of.strip(),)
            ).fetchone()
        if not existing:
            existing = conn.execute(
                "SELECT id, machine_id FROM planning_entries WHERE LOWER(TRIM(reference))=LOWER(TRIM(?)) LIMIT 1",
                (ref,)
            ).fetchone()

        if existing:
            # ── Mise à jour ────────────────────────────────────────────
            set_clause = ", ".join(f"{k}=?" for k in update_fields)
            conn.execute(
                f"UPDATE planning_entries SET {set_clause} WHERE id=?",
                list(update_fields.values()) + [existing["id"]]
            )
            conn.commit()
            return {
                "action": "updated",
                "id": existing["id"],
                "machine_id": existing["machine_id"],
                "reference": ref,
            }
        else:
            # ── Création ───────────────────────────────────────────────
            # Position : fin de la liste pour cette machine
            row_pos = conn.execute(
                "SELECT COALESCE(MAX(position),0)+1 AS pos FROM planning_entries WHERE machine_id=?",
                (machine_id,)
            ).fetchone()
            position = row_pos["pos"] if row_pos else 9999

            insert_data = {
                "machine_id":           machine_id,
                "position":             position,
                "reference":            ref,
                "client":               body.client or "",
                "description":          body.description or "",
                "duree_heures":         duree,
                "statut":               "attente",
                "format_l":             body.format_l,
                "format_h":             body.format_h,
                "laize":                body.laize,
                "ref_produit":          body.ref_produit,
                "dos_rvgi":             body.dos_rvgi,
                "numero_of":            body.numero_of.strip() if body.numero_of else None,
                "date_livraison":       body.date_livraison,
                "commentaire":          body.commentaire,
                "exigences_production": body.exigences_production,
                "notes":                "",
                "created_at":           now,
                "updated_at":           now,
                "created_by":           "access_bridge",
                "updated_by":           "access_bridge",
            }
            cols   = list(insert_data.keys())
            vals   = list(insert_data.values())
            cur    = conn.execute(
                f"INSERT INTO planning_entries ({', '.join(cols)}) VALUES ({', '.join('?'*len(cols))})",
                vals
            )
            new_id = cur.lastrowid
            # Backfill group_id (requis par la logique planning)
            conn.execute(
                "UPDATE planning_entries SET group_id=CAST(id AS TEXT) WHERE id=? AND (group_id IS NULL OR TRIM(group_id)='')",
                (new_id,)
            )
            conn.commit()
            return {
                "action": "created",
                "id": new_id,
                "machine_id": machine_id,
                "reference": ref,
                "position": position,
            }
