"""MyTools › Éditeur PDF — ce qui demande le serveur (hors IA).

  GET    /api/tools/pdf/reglages          seuils du preflight BAT (config.py)
  GET    /api/tools/pdf/actions           actions enregistrées de l'utilisateur
  PUT    /api/tools/pdf/actions           {nom, etapes} : crée ou remplace
  DELETE /api/tools/pdf/actions/{aid}     retire une action
  POST   /api/tools/pdf/pdfa              multipart `pdf` → PDF/A-2b (ghostscript)

Le reste de l'éditeur travaille dans le navigateur. La conversion PDF/A passe
par ghostscript, comme la compression de Convertir (quota et parallélisme
partagés : app/services/conversion.py).
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.services import conversion
from app.services.auth_service import get_current_user
from config import (
    CONVERTIR_MAX_MO,
    PDF_ACTIONS_MAX,
    PDF_ACTIONS_MAX_OCTETS,
    PREFLIGHT_DPI_MIN,
    PREFLIGHT_FOND_PERDU_MM,
    PREFLIGHT_TRAIT_MIN_PT,
)
from database import get_db

router = APIRouter(prefix="/api/tools/pdf", tags=["tools"])
_PARIS = ZoneInfo("Europe/Paris")
ETAPES = ("filigrane", "numerotation", "compression", "ocr", "renommage", "nettoyage")


@router.get("/reglages")
def reglages(request: Request):
    get_current_user(request)
    return {"preflight": {"dpi_min": PREFLIGHT_DPI_MIN, "trait_min_pt": PREFLIGHT_TRAIT_MIN_PT,
                          "fond_perdu_mm": PREFLIGHT_FOND_PERDU_MM}}


class ActionIn(BaseModel):
    nom: str = Field(..., min_length=1, max_length=80)
    etapes: list = Field(default_factory=list)


def _ligne(r) -> dict:
    try:
        etapes = json.loads(r["etapes"] or "[]")
    except ValueError:
        etapes = []
    return {"id": r["id"], "nom": r["nom"], "etapes": etapes, "maj_le": r["maj_le"]}


@router.get("/actions")
def lister_actions(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM tools_pdf_actions WHERE user_id = ? ORDER BY nom COLLATE NOCASE",
                            (user["id"],)).fetchall()
    return {"actions": [_ligne(r) for r in rows]}


@router.put("/actions")
def enregistrer_action(payload: ActionIn, request: Request):
    user = get_current_user(request)
    nom = payload.nom.strip()
    if not nom:
        raise HTTPException(status_code=400, detail="Nom obligatoire.")
    etapes = [e for e in payload.etapes if isinstance(e, dict) and e.get("type") in ETAPES]
    if not etapes:
        raise HTTPException(status_code=400, detail="Ajouter au moins une étape.")
    brut = json.dumps(etapes, ensure_ascii=False)
    if len(brut.encode()) > PDF_ACTIONS_MAX_OCTETS:
        raise HTTPException(status_code=400, detail="Action trop volumineuse.")
    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        deja = conn.execute("SELECT id FROM tools_pdf_actions WHERE user_id = ? AND nom = ?", (user["id"], nom)).fetchone()
        if deja:
            conn.execute("UPDATE tools_pdf_actions SET etapes = ?, maj_le = ? WHERE id = ?", (brut, now, deja["id"]))
            aid = deja["id"]
        else:
            n = conn.execute("SELECT COUNT(*) FROM tools_pdf_actions WHERE user_id = ?", (user["id"],)).fetchone()[0]
            if n >= PDF_ACTIONS_MAX:
                raise HTTPException(status_code=400, detail=f"{PDF_ACTIONS_MAX} actions au plus — en retirer une.")
            aid = conn.execute("INSERT INTO tools_pdf_actions (user_id, nom, etapes, cree_le, maj_le) VALUES (?,?,?,?,?)",
                               (user["id"], nom, brut, now, now)).lastrowid
        conn.commit()
        r = conn.execute("SELECT * FROM tools_pdf_actions WHERE id = ?", (aid,)).fetchone()
    return _ligne(r)


@router.delete("/actions/{aid}")
def retirer_action(aid: int, request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        cur = conn.execute("DELETE FROM tools_pdf_actions WHERE id = ? AND user_id = ?", (aid, user["id"]))
        conn.commit()
    if not cur.rowcount:
        raise HTTPException(status_code=404, detail="Action introuvable.")
    return {"ok": True}


def _pdfa(contenu: bytes) -> bytes:
    with tempfile.TemporaryDirectory(prefix="mysifa_pdfa_") as tmp:
        src, dst = os.path.join(tmp, "entree.pdf"), os.path.join(tmp, "sortie.pdf")
        with open(src, "wb") as f:
            f.write(contenu)
        conversion._lancer(["gs", "-dPDFA=2", "-dBATCH", "-dNOPAUSE", "-dNOOUTERSAVE", "-dQUIET",
                            "-sColorConversionStrategy=RGB", "-dPDFACompatibilityPolicy=1",
                            "-sDEVICE=pdfwrite", f"-sOutputFile={dst}", src], tmp, 5 * 60)
        with open(dst, "rb") as f:
            return f.read()


@router.post("/pdfa")
async def pdfa(request: Request, pdf: UploadFile = File(...)):
    user = get_current_user(request)
    contenu = await pdf.read()
    if len(contenu) > CONVERTIR_MAX_MO * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Fichier trop lourd : {CONVERTIR_MAX_MO} Mo au plus.")
    if not contenu.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Fichier illisible — ce n'est pas un PDF valide.")
    qui = str(user.get("id") or user.get("email") or "?")
    try:
        conversion.reserver(qui)
    except conversion.ConversionRefusee as e:
        raise HTTPException(status_code=e.code, detail=str(e))
    try:
        sortie = await run_in_threadpool(_pdfa, contenu)
    except conversion.ConversionRefusee as e:
        raise HTTPException(status_code=e.code, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Conversion PDF/A en échec sur ce document.")
    finally:
        conversion.liberer()
    return Response(content=sortie, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="document-pdfa.pdf"'})
