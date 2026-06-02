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
    desc = d.get("description") or d.get("numero_client") or ""
    d["description"] = desc
    d["reference"] = f"{desc}/{d['numero_article']}" if desc else d["numero_article"]
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
    description: str
    numero_article: str
    delai_client: Optional[str] = None
    notes: Optional[str] = None


@router.post("/api/bat")
def create_bat(body: BatCreate, request: Request):
    user = _require_bat_access(request)
    description = body.description.strip()
    numero_article = body.numero_article.strip()
    if not description or not numero_article:
        raise HTTPException(status_code=400, detail="Description et numéro article obligatoires")
    now = _now()
    with get_db() as conn:
        # Récupérer les colonnes disponibles
        cols = {row[1] for row in conn.execute("PRAGMA table_info(bat_entries)").fetchall()}
        desc_col = "description" if "description" in cols else "numero_client"

        existing = conn.execute(
            f"SELECT id FROM bat_entries WHERE {desc_col}=? AND numero_article=?",
            (description, numero_article),
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Un BAT existe déjà pour {description}/{numero_article}",
            )

        if "delai_client" in cols:
            cur = conn.execute(
                f"""INSERT INTO bat_entries ({desc_col}, numero_article, statut, delai_client, notes, created_at, updated_at, created_by, updated_by)
                   VALUES (?, ?, 'a_faire', ?, ?, ?, ?, ?, ?)""",
                (description, numero_article, body.delai_client, body.notes, now, now, user["id"], user["id"]),
            )
        else:
            cur = conn.execute(
                f"""INSERT INTO bat_entries ({desc_col}, numero_article, statut, notes, created_at, updated_at, created_by, updated_by)
                   VALUES (?, ?, 'a_faire', ?, ?, ?, ?, ?)""",
                (description, numero_article, body.notes, now, now, user["id"], user["id"]),
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


# ─── Mise à jour ──────────────────────────────────────────────────────────────

class BatUpdate(BaseModel):
    statut: Optional[str] = None
    notes: Optional[str] = None
    description: Optional[str] = None
    numero_article: Optional[str] = None
    delai_client: Optional[str] = None


@router.put("/api/bat/{bat_id}")
def update_bat(bat_id: int, body: BatUpdate, request: Request):
    user = _require_bat_access(request)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM bat_entries WHERE id=?", (bat_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="BAT introuvable")

        current = dict(row)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(bat_entries)").fetchall()}
        desc_col = "description" if "description" in cols else "numero_client"

        new_statut = body.statut if body.statut is not None else current["statut"]
        if new_statut not in BAT_STATUTS:
            raise HTTPException(status_code=400, detail="Statut invalide")

        # Empêcher passage à "en_attente" sans PDF
        if new_statut == "en_attente" and not current.get("pdf_path"):
            raise HTTPException(
                status_code=400,
                detail="Un PDF doit être importé avant de passer en statut 'en attente'",
            )

        new_notes = body.notes if body.notes is not None else current.get("notes")
        new_desc = body.description.strip() if body.description is not None else current.get(desc_col, current.get("description", ""))
        new_article = body.numero_article.strip() if body.numero_article is not None else current["numero_article"]
        new_delai = body.delai_client if body.delai_client is not None else current.get("delai_client")

        if not new_desc or not new_article:
            raise HTTPException(status_code=400, detail="Description et numéro article obligatoires")

        now = _now()
        if "delai_client" in cols:
            conn.execute(
                f"UPDATE bat_entries SET statut=?, notes=?, {desc_col}=?, numero_article=?, delai_client=?, updated_at=?, updated_by=? WHERE id=?",
                (new_statut, new_notes, new_desc, new_article, new_delai, now, user["id"], bat_id),
            )
        else:
            conn.execute(
                f"UPDATE bat_entries SET statut=?, notes=?, {desc_col}=?, numero_article=?, updated_at=?, updated_by=? WHERE id=?",
                (new_statut, new_notes, new_desc, new_article, now, user["id"], bat_id),
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

    desc = current.get("description") or current.get("numero_client") or "BAT"
    ref = f"{desc}_{current['numero_article']}"
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
