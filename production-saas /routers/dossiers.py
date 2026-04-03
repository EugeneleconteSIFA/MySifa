"""SIFA — Dossiers v0.6"""
import sqlite3
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from database import get_db
from services.auth_service import require_admin

router = APIRouter()

@router.post("/api/dossiers")
async def create_dossier(request: Request):
    require_admin(request)
    body = await request.json()
    now = datetime.now().isoformat()
    with get_db() as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO dossiers (reference,client,description,devis_montant,statut,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
                (body.get("reference",f"DOS-{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                 body.get("client",""),body.get("description",""),
                 body.get("devis_montant",0),body.get("statut","devis"),now,now))
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Référence déjà existante")
    return {"success":True,"id":cursor.lastrowid}

@router.get("/api/dossiers")
def list_dossiers(request: Request, statut: Optional[str]=None):
    require_admin(request)
    with get_db() as conn:
        if statut:
            rows = conn.execute("SELECT * FROM dossiers WHERE statut=? ORDER BY updated_at DESC",(statut,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM dossiers ORDER BY updated_at DESC").fetchall()
    return [dict(r) for r in rows]

@router.put("/api/dossiers/{dossier_id}")
async def update_dossier(dossier_id: int, request: Request):
    require_admin(request)
    body = await request.json()
    with get_db() as conn:
        ex = conn.execute("SELECT * FROM dossiers WHERE id=?", (dossier_id,)).fetchone()
        if not ex: raise HTTPException(status_code=404, detail="Dossier non trouvé")
        conn.execute("UPDATE dossiers SET client=?,description=?,devis_montant=?,statut=?,updated_at=? WHERE id=?",
                     (body.get("client",ex["client"]),body.get("description",ex["description"]),
                      body.get("devis_montant",ex["devis_montant"]),body.get("statut",ex["statut"]),
                      datetime.now().isoformat(),dossier_id))
        conn.commit()
    return {"success":True}
