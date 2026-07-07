"""MySifa — Coffre RH côté salarié.

Endpoints pour un utilisateur connecté (tous rôles) : consultation de ses
propres bulletins de paie et gestion de ses notes de frais (dépôt, soumission,
suppression brouillon). L'accès aux fichiers est strictement limité au
propriétaire ou aux rôles compta/superadmin (partagés avec /rh/coffre).

Coffre interne SIFA — pas de valeur légale opposable, le bulletin officiel
reste celui remis en main propre / par email par la comptabilité.
"""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from config import BASE_DIR, ROLE_COMPTABILITE, ROLE_SUPERADMIN
from database import get_db
from services.auth_service import get_current_user


router = APIRouter(tags=["coffre"])

COFFRE_ROOT = Path(BASE_DIR) / "data" / "uploads" / "coffre_rh"
COFFRE_ROOT.mkdir(parents=True, exist_ok=True)

NDF_ROOT = Path(BASE_DIR) / "data" / "uploads" / "ndf_justificatifs"
NDF_ROOT.mkdir(parents=True, exist_ok=True)

ALLOWED_DOC_TYPES = {"bulletin_paie", "contrat", "attestation", "autre"}
ALLOWED_NDF_STATUTS = {"brouillon", "soumise", "validee", "payee", "refusee"}

MAX_JUSTIFICATIF_MB = 10
MAX_JUSTIFICATIF_BYTES = MAX_JUSTIFICATIF_MB * 1024 * 1024


def _is_compta_or_super(user: dict) -> bool:
    return user.get("role") in {ROLE_COMPTABILITE, ROLE_SUPERADMIN}


def _log_doc_access(conn, doc_id: int, user: dict, action: str, ip: Optional[str]) -> None:
    conn.execute(
        """INSERT INTO documents_rh_access_log
           (document_id,user_id,user_nom,action,ip,created_at)
           VALUES (?,?,?,?,?,?)""",
        (
            doc_id,
            user.get("id"),
            (user.get("nom") or user.get("email") or "")[:120],
            action,
            (ip or "")[:64],
            datetime.now().isoformat(timespec="seconds"),
        ),
    )


def _sanitize_filename(name: str) -> str:
    base = os.path.basename(name or "")
    base = re.sub(r"[^A-Za-z0-9._\-]", "_", base)
    return base[:120] or "fichier"


# ── Documents RH (bulletins, contrats, attestations) — vue salarié ──────

@router.get("/api/coffre/documents")
def list_my_documents(request: Request, annee: Optional[int] = None, type: Optional[str] = None):
    """Liste des documents visibles par le salarié connecté."""
    user = get_current_user(request)
    uid = user.get("id")
    where = ["employe_user_id=?", "deleted_at IS NULL", "visible_salarie=1"]
    params: list = [uid]
    if annee:
        where.append("annee=?")
        params.append(int(annee))
    if type and type in ALLOWED_DOC_TYPES:
        where.append("type=?")
        params.append(type)
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT id,type,annee,mois,libelle,fichier_nom,taille_bytes,
                       uploaded_at,distribue_at,consulte_at
                FROM documents_rh
                WHERE {' AND '.join(where)}
                ORDER BY annee DESC, mois DESC, uploaded_at DESC""",
            params,
        ).fetchall()
        # Regroupement par année pour l'affichage
        annees = conn.execute(
            """SELECT DISTINCT annee FROM documents_rh
               WHERE employe_user_id=? AND deleted_at IS NULL AND visible_salarie=1
               AND annee IS NOT NULL
               ORDER BY annee DESC""",
            (uid,),
        ).fetchall()
    return {
        "documents": [dict(r) for r in rows],
        "annees_disponibles": [r["annee"] for r in annees],
    }


@router.get("/api/coffre/documents/{doc_id}/download")
def download_document(doc_id: int, request: Request):
    """Télécharge un document RH — propriétaire ou compta/superadmin uniquement."""
    user = get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            """SELECT id,employe_user_id,fichier_path,fichier_nom,deleted_at
               FROM documents_rh WHERE id=?""",
            (doc_id,),
        ).fetchone()
        if not row or row["deleted_at"]:
            raise HTTPException(404, "Document introuvable")
        d = dict(row)
        if d["employe_user_id"] != user.get("id") and not _is_compta_or_super(user):
            raise HTTPException(403, "Accès refusé")
        # Marquage première consultation
        conn.execute(
            "UPDATE documents_rh SET consulte_at=COALESCE(consulte_at,?) WHERE id=?",
            (datetime.now().isoformat(timespec="seconds"), doc_id),
        )
        _log_doc_access(
            conn, doc_id, user, "download",
            request.client.host if request.client else None,
        )
        conn.commit()
    path = Path(d["fichier_path"])
    if not path.is_file():
        raise HTTPException(410, "Fichier absent du serveur")
    return FileResponse(
        str(path),
        filename=d["fichier_nom"] or path.name,
        media_type="application/pdf",
    )


# ── Notes de frais — vue salarié (dépôt + workflow) ──────────────────────

@router.get("/api/coffre/notes-frais")
def list_my_ndf(request: Request, annee: Optional[int] = None):
    user = get_current_user(request)
    uid = user.get("id")
    where = ["employe_user_id=?", "deleted_at IS NULL"]
    params: list = [uid]
    if annee:
        where.append("strftime('%Y', date_frais)=?")
        params.append(str(annee))
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT id,date_frais,categorie,montant_ttc,montant_tva,description,
                       justificatif_nom,statut,created_at,soumise_at,validee_at,
                       validee_by_nom,payee_at,motif_refus
                FROM notes_de_frais
                WHERE {' AND '.join(where)}
                ORDER BY date_frais DESC, id DESC""",
            params,
        ).fetchall()
    return {"notes": [dict(r) for r in rows]}


@router.post("/api/coffre/notes-frais")
async def create_ndf(
    request: Request,
    date_frais: str = Form(...),
    categorie: str = Form(""),
    montant_ttc: float = Form(...),
    montant_tva: str = Form(""),
    description: str = Form(""),
    soumettre: str = Form("0"),
    justificatif: Optional[UploadFile] = File(None),
):
    """Créer une note de frais. Si soumettre=1, statut=soumise directement."""
    user = get_current_user(request)
    uid = user.get("id")

    # Validations
    try:
        datetime.fromisoformat(date_frais[:10])
    except ValueError:
        raise HTTPException(400, "Date invalide (format YYYY-MM-DD attendu)")
    if montant_ttc <= 0:
        raise HTTPException(400, "Montant TTC doit être positif")
    tva_val: Optional[float] = None
    if montant_tva.strip():
        try:
            tva_val = float(montant_tva.replace(",", "."))
        except ValueError:
            raise HTTPException(400, "TVA invalide")

    # Justificatif
    just_path: Optional[str] = None
    just_nom: Optional[str] = None
    if justificatif is not None and justificatif.filename:
        allowed_ct = {"image/jpeg", "image/png", "image/webp", "image/heic", "application/pdf"}
        ct = (justificatif.content_type or "").lower()
        if ct not in allowed_ct:
            raise HTTPException(400, "Format justificatif : PDF, JPG, PNG, WEBP, HEIC uniquement")
        content = await justificatif.read()
        if len(content) > MAX_JUSTIFICATIF_BYTES:
            raise HTTPException(400, f"Justificatif > {MAX_JUSTIFICATIF_MB} Mo")
        user_dir = NDF_ROOT / str(uid)
        user_dir.mkdir(parents=True, exist_ok=True)
        safe_name = _sanitize_filename(justificatif.filename)
        fname = f"{uuid.uuid4().hex[:12]}_{safe_name}"
        dest = user_dir / fname
        with open(dest, "wb") as f:
            f.write(content)
        just_path = str(dest)
        just_nom = justificatif.filename[:180]

    do_soumettre = str(soumettre).strip() in {"1", "true", "yes"}
    statut = "soumise" if do_soumettre else "brouillon"
    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO notes_de_frais
               (employe_user_id,date_frais,categorie,montant_ttc,montant_tva,description,
                justificatif_path,justificatif_nom,statut,created_at,soumise_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                uid, date_frais[:10], (categorie or "").strip()[:80],
                float(montant_ttc), tva_val,
                (description or "").strip()[:1000],
                just_path, just_nom, statut, now,
                now if do_soumettre else None,
            ),
        )
        conn.commit()
    return {"success": True, "id": cur.lastrowid, "statut": statut}


@router.post("/api/coffre/notes-frais/{ndf_id}/soumettre")
def submit_ndf(ndf_id: int, request: Request):
    """Soumet un brouillon à la compta. Une fois soumise, non modifiable côté salarié."""
    user = get_current_user(request)
    uid = user.get("id")
    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id,employe_user_id,statut FROM notes_de_frais WHERE id=? AND deleted_at IS NULL",
            (ndf_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Note introuvable")
        if row["employe_user_id"] != uid:
            raise HTTPException(403, "Accès refusé")
        if row["statut"] != "brouillon":
            raise HTTPException(400, "Seuls les brouillons peuvent être soumis")
        conn.execute(
            "UPDATE notes_de_frais SET statut='soumise', soumise_at=? WHERE id=?",
            (now, ndf_id),
        )
        conn.commit()
    return {"success": True}


@router.delete("/api/coffre/notes-frais/{ndf_id}")
def delete_ndf(ndf_id: int, request: Request):
    """Suppression logique — brouillons uniquement côté salarié."""
    user = get_current_user(request)
    uid = user.get("id")
    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id,employe_user_id,statut FROM notes_de_frais WHERE id=? AND deleted_at IS NULL",
            (ndf_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Note introuvable")
        if row["employe_user_id"] != uid and not _is_compta_or_super(user):
            raise HTTPException(403, "Accès refusé")
        if row["statut"] != "brouillon" and not _is_compta_or_super(user):
            raise HTTPException(400, "Seuls les brouillons peuvent être supprimés par le salarié")
        conn.execute(
            "UPDATE notes_de_frais SET deleted_at=? WHERE id=?",
            (now, ndf_id),
        )
        conn.commit()
    return {"success": True}


@router.get("/api/coffre/notes-frais/{ndf_id}/justificatif")
def download_ndf_justificatif(ndf_id: int, request: Request):
    """Télécharge le justificatif — propriétaire ou compta/superadmin."""
    user = get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            """SELECT id,employe_user_id,justificatif_path,justificatif_nom
               FROM notes_de_frais WHERE id=? AND deleted_at IS NULL""",
            (ndf_id,),
        ).fetchone()
        if not row or not row["justificatif_path"]:
            raise HTTPException(404, "Justificatif introuvable")
        if row["employe_user_id"] != user.get("id") and not _is_compta_or_super(user):
            raise HTTPException(403, "Accès refusé")
    path = Path(row["justificatif_path"])
    if not path.is_file():
        raise HTTPException(410, "Fichier absent du serveur")
    return FileResponse(str(path), filename=row["justificatif_nom"] or path.name)
