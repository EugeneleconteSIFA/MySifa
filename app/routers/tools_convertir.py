"""MyTools › Convertir — API des conversions faites sur le serveur.

  GET  /api/tools/convertir/outils   outils système présents (l'écran grise le reste)
  POST /api/tools/convertir          fichiers (multipart `fichiers`), `cible`, `options` (JSON)
                                     → le fichier converti, ou un ZIP s'il y en a plusieurs

Le travail est dans app/services/conversion.py. Ouvert à tout utilisateur
connecté, comme les autres outils transverses de MyTools ; quota par heure et
nombre de conversions simultanées dans config.py (CONVERTIR_*).
"""
from __future__ import annotations

import json
import logging
from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response

from app.services import conversion
from app.services.auth_service import get_current_user
from config import CONVERTIR_MAX_MO

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tools/convertir", tags=["tools"])


@router.get("/outils")
def outils(request: Request):
    get_current_user(request)
    d = conversion.outils_disponibles()
    d["max_mo"] = CONVERTIR_MAX_MO
    d["cibles"] = {k: list(v) for k, v in conversion.CIBLES.items()}
    return d


@router.post("")
async def convertir(request: Request, cible: str = Form(...), options: str = Form("{}"),
                    fichiers: list[UploadFile] = File(...)):
    user = get_current_user(request)
    try:
        opts = json.loads(options or "{}")
        if not isinstance(opts, dict):
            opts = {}
    except ValueError:
        opts = {}
    plafond = CONVERTIR_MAX_MO * 1024 * 1024
    lus, total = [], 0
    for f in (fichiers or [])[:50]:
        if not f or not f.filename:
            continue
        contenu = await f.read()
        total += len(contenu)
        if total > plafond:
            raise HTTPException(status_code=413, detail=f"Fichiers trop lourds : {CONVERTIR_MAX_MO} Mo au plus.")
        lus.append((f.filename, contenu))
    qui = str(user.get("id") or user.get("email") or "?")
    try:
        conversion.reserver(qui)
    except conversion.ConversionRefusee as e:
        raise HTTPException(status_code=e.code, detail=str(e))
    try:
        nom, octets, mime = await run_in_threadpool(conversion.convertir, lus, (cible or "").strip(), opts)
    except conversion.ConversionRefusee as e:
        raise HTTPException(status_code=e.code, detail=str(e))
    except Exception as e:  # outil en échec : message générique, détail dans les journaux
        logger.warning("conversion %s en échec : %s", cible, e)
        raise HTTPException(status_code=500,
                            detail="La conversion a échoué : le fichier est peut-être abîmé ou protégé.")
    finally:
        conversion.liberer()
    return Response(content=octets, media_type=mime, headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(nom)}",
        "Cache-Control": "no-store",
    })
