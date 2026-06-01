"""MySifa — Router MyBAT (Bons À Tirer)
Route prefix : /api/bat
Accès : superadmin, direction, administration
"""
from __future__ import annotations

import os
import shutil
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.core.database import get_db
from app.services.auth_service import get_current_user
from config import UPLOAD_DIR

ROLES_BAT = {"superadmin", "direction", "administration"}
BAT_STATUTS = {"a_faire", "en_attente", "valide"}
BAT_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "bat")
os.makedirs(BAT_UPLOAD_DIR, exist_ok=True)

router = APIRouter()


def _require_bat_access(request: Request) -> dict:
    user = get_current_user(request)
    if user["role"] not in ROLES_BAT:
        raise HTTPException(status_code=403, detail="Accès réservé à l'administration et la direction")
    return user


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _row_to_dict(row) -> dict:
    d = dict(row)
    # Construire la référence BAT affichée
    d["reference"] = f"{d['numero_client']}/{d['numero_article']}"
    d["has_pdf"] = bool(d.get("pdf_path"))
    return d


# ─── Lecture ──────────────────────────────────────────────────────────────────

@router.get("/api/bat")
def list_bat(request: Request, statut: Optional[str] = None):
    _require_bat_access(request)
    with get_db() as conn:
        if statut and statut in BAT_STATUTS:
            rows = conn.execute(
                """SELECT b.*, u1.nom AS created_by_nom, u2.nom AS updated_by_nom
                   FROM bat_entries b
                   LEFT JOIN users u1 ON b.created_by = u1.id
                   LEFT JOIN users u2 ON b.updated_by = u2.id
                   WHERE b.statut = ?
                   ORDER BY b.updated_at DESC""",
                (statut,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT b.*, u1.nom AS created_by_nom, u2.nom AS updated_by_nom
                   FROM bat_entries b
                   LEFT JOIN users u1 ON b.created_by = u1.id
                   LEFT JOIN users u2 ON b.updated_by = u2.id
                   ORDER BY b.updated_at DESC"""
            ).fetchall()
    return [_row_to_dict(r) for r in rows]


@router.get("/api/bat/{bat_id}")
def get_bat(bat_id: int, request: Request):
    _require_bat_access(request)
    with get_db() as conn:
        row = conn.execute(
            """SELECT b.*, u1.nom AS created_by_nom, u2.nom AS updated_by_nom
               FROM bat_entries b
               LEFT JOIN users u1 ON b.created_by = u1.id
               LEFT JOIN users u2 ON b.updated_by = u2.id
               WHERE b.id = ?""",
            (bat_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="BAT introuvable")
    return _row_to_dict(row)


# ─── Création ─────────────────────────────────────────────────────────────────

class BatCreate(BaseModel):
    numero_client: str
    numero_article: str
    notes: Optional[str] = None


@router.post("/api/bat")
def create_bat(body: BatCreate, request: Request):
    user = _require_bat_access(request)
    numero_client = body.numero_client.strip()
    numero_article = body.numero_article.strip()
    if not numero_client or not numero_article:
        raise HTTPException(status_code=400, detail="Numéro client et numéro article obligatoires")
    now = _now()
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM bat_entries WHERE numero_client=? AND numero_article=?",
            (numero_client, numero_article),
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Un BAT existe déjà pour {numero_client}/{numero_article}",
            )
        cur = conn.execute(
            """INSERT INTO bat_entries (numero_client, numero_article, statut, notes, created_at, updated_at, created_by, updated_by)
               VALUES (?, ?, 'a_faire', ?, ?, ?, ?, ?)""",
            (numero_client, numero_article, body.notes, now, now, user["id"], user["id"]),
        )
        conn.commit()
        row = conn.execute(
            "SELECT b.*, u1.nom AS created_by_nom, u2.nom AS updated_by_nom "
            "FROM bat_entries b "
            "LEFT JOIN users u1 ON b.created_by=u1.id "
            "LEFT JOIN users u2 ON b.updated_by=u2.id "
            "WHERE b.id=?",
            (cur.lastrowid,),
        ).fetchone()
    return _row_to_dict(row)


# ─── Mise à jour statut / notes ───────────────────────────────────────────────

class BatUpdate(BaseModel):
    statut: Optional[str] = None
    notes: Optional[str] = None


@router.put("/api/bat/{bat_id}")
def update_bat(bat_id: int, body: BatUpdate, request: Request):
    user = _require_bat_access(request)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM bat_entries WHERE id=?", (bat_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="BAT introuvable")

        current = dict(row)
        new_statut = body.statut if body.statut is not None else current["statut"]
        if new_statut not in BAT_STATUTS:
            raise HTTPException(status_code=400, detail="Statut invalide")

        # Empêcher passage à "en_attente" sans PDF
        if new_statut == "en_attente" and not current.get("pdf_path"):
            raise HTTPException(
                status_code=400,
                detail="Un PDF doit être importé avant de passer en statut 'en attente'",
            )

        new_notes = body.notes if body.notes is not None else current["notes"]
        now = _now()
        conn.execute(
            "UPDATE bat_entries SET statut=?, notes=?, updated_at=?, updated_by=? WHERE id=?",
            (new_statut, new_notes, now, user["id"], bat_id),
        )
        conn.commit()
        updated = conn.execute(
            "SELECT b.*, u1.nom AS created_by_nom, u2.nom AS updated_by_nom "
            "FROM bat_entries b "
            "LEFT JOIN users u1 ON b.created_by=u1.id "
            "LEFT JOIN users u2 ON b.updated_by=u2.id "
            "WHERE b.id=?",
            (bat_id,),
        ).fetchone()
    return _row_to_dict(updated)


# ─── Upload PDF ───────────────────────────────────────────────────────────────

@router.post("/api/bat/{bat_id}/upload")
async def upload_bat_pdf(bat_id: int, request: Request, file: UploadFile = File(...)):
    user = _require_bat_access(request)
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés")

    with get_db() as conn:
        row = conn.execute("SELECT * FROM bat_entries WHERE id=?", (bat_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="BAT introuvable")
        current = dict(row)

        # Supprimer l'ancien PDF si existant
        if current.get("pdf_path"):
            old_path = os.path.join(BAT_UPLOAD_DIR, current["pdf_path"])
            if os.path.exists(old_path):
                os.remove(old_path)

        # Nom de fichier unique : bat_{id}_{timestamp}.pdf
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"bat_{bat_id}_{ts}.pdf"
        dest = os.path.join(BAT_UPLOAD_DIR, filename)
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Passer automatiquement à "en_attente" si encore "à faire"
        new_statut = "en_attente" if current["statut"] == "a_faire" else current["statut"]
        now = _now()
        conn.execute(
            "UPDATE bat_entries SET pdf_path=?, statut=?, updated_at=?, updated_by=? WHERE id=?",
            (filename, new_statut, now, user["id"], bat_id),
        )
        conn.commit()
        updated = conn.execute(
            "SELECT b.*, u1.nom AS created_by_nom, u2.nom AS updated_by_nom "
            "FROM bat_entries b "
            "LEFT JOIN users u1 ON b.created_by=u1.id "
            "LEFT JOIN users u2 ON b.updated_by=u2.id "
            "WHERE b.id=?",
            (bat_id,),
        ).fetchone()
    return _row_to_dict(updated)


# ─── Téléchargement PDF ───────────────────────────────────────────────────────

@router.get("/api/bat/{bat_id}/pdf")
def download_bat_pdf(bat_id: int, request: Request):
    _require_bat_access(request)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM bat_entries WHERE id=?", (bat_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="BAT introuvable")
        current = dict(row)

    if not current.get("pdf_path"):
        raise HTTPException(status_code=404, detail="Aucun PDF associé à ce BAT")

    path = os.path.join(BAT_UPLOAD_DIR, current["pdf_path"])
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Fichier PDF introuvable sur le serveur")

    ref = f"{current['numero_client']}_{current['numero_article']}"
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"BAT_{ref}.pdf",
        headers={"Content-Disposition": f'inline; filename="BAT_{ref}.pdf"'},
    )


# ─── Suppression ─────────────────────────────────────────────────────────────

@router.delete("/api/bat/{bat_id}")
def delete_bat(bat_id: int, request: Request):
    _require_bat_access(request)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM bat_entries WHERE id=?", (bat_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="BAT introuvable")
        current = dict(row)

        # Supprimer le PDF associé si existant
        if current.get("pdf_path"):
            path = os.path.join(BAT_UPLOAD_DIR, current["pdf_path"])
            if os.path.exists(path):
                os.remove(path)

        conn.execute("DELETE FROM bat_entries WHERE id=?", (bat_id,))
        conn.commit()
    return {"ok": True}
