"""MyTools › Éditeur PDF — fonctions IA.

  POST /api/tools/pdf/ia/resumer    multipart `pdf`
  POST /api/tools/pdf/ia/question   multipart `pdf`, `question`
  POST /api/tools/pdf/ia/extraire   multipart `pdf`, `nature` (facture|bl|fiche|libre), `consigne`
  POST /api/tools/pdf/ia/champs     multipart `pdf`
  POST /api/tools/pdf/ia/modifier   `consigne`, `blocs` (JSON : [{id, page, texte, x, y}]) — sans le PDF
  POST /api/tools/pdf/ia/creer      `consigne`, `format`, `ton`, `langue`, `entete`, [`precedent`, `affiner`]
  GET  /api/tools/pdf/ia/entete     identité de l'organisation pour l'en-tête (nom, adresse, logo)

Le travail est dans app/services/pdf_ia.py. Ouvert à tout utilisateur
connecté (outil transverse de MyTools), avec un quota par heure
(PDF_IA_PAR_HEURE) et une taille d'envoi bornée (PDF_IA_MAX_MO). Chaque appel
est enregistré dans ia_usage au nom de l'utilisateur (fonction « pdf »).
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.services import ia_usage, pdf_ia
from app.services.auth_service import get_current_user
from config import PDF_IA_MAX_MO, PDF_IA_PAR_HEURE

router = APIRouter(prefix="/api/tools/pdf/ia", tags=["tools"])

_verrou = threading.Lock()
_appels: dict[str, deque] = defaultdict(deque)


def _quota(user: dict) -> None:
    cle = str(user.get("id") or user.get("email") or "?")
    maintenant = time.time()
    with _verrou:
        file = _appels[cle]
        while file and maintenant - file[0] > 3600:
            file.popleft()
        if len(file) >= PDF_IA_PAR_HEURE:
            raise HTTPException(status_code=429, detail=f"Quota atteint : {PDF_IA_PAR_HEURE} demandes IA par heure.")
        file.append(maintenant)


async def _lire(pdf: UploadFile) -> bytes:
    contenu = await pdf.read()
    if len(contenu) > PDF_IA_MAX_MO * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"PDF trop lourd pour l'IA : {PDF_IA_MAX_MO} Mo au plus — le compresser d'abord.")
    if not contenu.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Fichier illisible — ce n'est pas un PDF valide.")
    return contenu


async def _executer(request: Request, pdf: UploadFile, fn, *args):
    user = get_current_user(request)
    _quota(user)
    contenu = await _lire(pdf)

    def travail():
        with ia_usage.suivi(user, "pdf", "MyTools"):
            return fn(contenu, *args)
    try:
        return await run_in_threadpool(travail)
    except pdf_ia.PdfIaErreur as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/resumer")
async def resumer(request: Request, pdf: UploadFile = File(...)):
    return await _executer(request, pdf, pdf_ia.resumer)


@router.post("/question")
async def question(request: Request, pdf: UploadFile = File(...), question: str = Form(...)):
    if len(question) > 2000:
        raise HTTPException(status_code=400, detail="Question trop longue — 2 000 caractères au plus.")
    return await _executer(request, pdf, pdf_ia.question, question)


@router.post("/extraire")
async def extraire(request: Request, pdf: UploadFile = File(...), nature: str = Form("facture"), consigne: str = Form("")):
    if nature not in pdf_ia.NATURES:
        raise HTTPException(status_code=400, detail="Type de document inconnu.")
    return await _executer(request, pdf, pdf_ia.extraire, nature, consigne[:2000])


@router.post("/champs")
async def champs(request: Request, pdf: UploadFile = File(...)):
    return await _executer(request, pdf, pdf_ia.champs)


# ─── Lot 4 ─────────────────────────────────────────────────────────

@router.post("/selection")
async def selection(request: Request, texte: str = Form(...), mode: str = Form("expliquer")):
    user = get_current_user(request)
    _quota(user)
    if len(texte) > 20000:
        raise HTTPException(status_code=400, detail="Sélection trop longue — 20 000 caractères au plus.")

    def travail():
        with ia_usage.suivi(user, "pdf", "MyTools"):
            return pdf_ia.selection(texte, mode)
    try:
        return await run_in_threadpool(travail)
    except pdf_ia.PdfIaErreur as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/contrats")
async def contrats(request: Request, pdf: UploadFile = File(...), pdf2: UploadFile = File(...)):
    second = await _lire(pdf2)
    return await _executer(request, pdf, pdf_ia.contrats, second)


@router.post("/bat")
async def bat(request: Request, pdf: UploadFile = File(...), fiche_id: int = Form(...)):
    # Même droit que l'écran des fiches techniques.
    from app.routers.of_import import _require_of_access
    _require_of_access(request)
    from database import get_db
    with get_db() as conn:
        r = conn.execute("SELECT * FROM fiches_techniques WHERE id = ?", (fiche_id,)).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Fiche technique introuvable.")
    return await _executer(request, pdf, pdf_ia.bat, dict(r))


@router.post("/remplir")
async def remplir(request: Request, pdf: UploadFile = File(...), champs: str = Form("[]"), donnees: str = Form("")):
    import json
    try:
        liste = json.loads(champs or "[]")
    except ValueError:
        raise HTTPException(status_code=400, detail="Liste des champs illisible.")
    return await _executer(request, pdf, pdf_ia.remplir, liste if isinstance(liste, list) else [], donnees)


# ─── Modification assistée ─────────────────────────────────────────

@router.post("/modifier")
async def modifier(request: Request, consigne: str = Form(...), blocs: str = Form("[]")):
    """Propositions de modification sur les blocs de texte envoyés (rien n'est appliqué ici)."""
    import json
    user = get_current_user(request)
    if len(consigne) > 2000:
        raise HTTPException(status_code=400, detail="Consigne trop longue — 2 000 caractères au plus.")
    if len(blocs) > 400000:
        raise HTTPException(status_code=413, detail="Document trop long pour un seul passage — choisir la page courante ou une sélection.")
    try:
        liste = json.loads(blocs or "[]")
    except ValueError:
        raise HTTPException(status_code=400, detail="Liste des blocs illisible.")
    _quota(user)

    def travail():
        with ia_usage.suivi(user, "pdf", "MyTools"):
            return pdf_ia.modifier(consigne, liste)
    try:
        return await run_in_threadpool(travail)
    except pdf_ia.PdfIaErreur as e:
        raise HTTPException(status_code=502, detail=str(e))


# ─── Créer un document ─────────────────────────────────────────────

def _identite() -> dict:
    """Nom, adresse et logo de l'organisation, lus dans la configuration."""
    import os
    import config
    nom = str(getattr(config, "APP_ORG_NAME", "") or "")
    adresse = str(getattr(config, "APP_ORG_ADRESSE", "") or "")
    logo = ""
    for attr in ("APP_LOGO_PATH", "BAT_LOGO_PATH"):
        chemin = getattr(config, attr, None)
        if chemin and os.path.isfile(chemin):
            statique = os.path.join(config.BASE_DIR, "static")
            if os.path.abspath(chemin).startswith(os.path.abspath(statique) + os.sep):
                logo = "/static/" + os.path.relpath(chemin, statique).replace(os.sep, "/")
                break
    return {"nom": nom, "adresse": [l.strip() for l in adresse.replace("\\n", "\n").split("\n") if l.strip()], "logo": logo}


@router.get("/entete")
async def entete(request: Request):
    get_current_user(request)
    return _identite()


@router.post("/creer")
async def creer(request: Request, consigne: str = Form(""), format: str = Form("a4"), ton: str = Form("neutre"),
                langue: str = Form("fr"), entete: str = Form("0"), precedent: str = Form(""), affiner: str = Form("")):
    """Structure d'un document (titre + blocs) à composer dans le navigateur."""
    import json
    user = get_current_user(request)
    if len(consigne) > 4000 or len(affiner) > 4000:
        raise HTTPException(status_code=400, detail="Consigne trop longue — 4 000 caractères au plus.")
    if len(precedent) > 200000:
        raise HTTPException(status_code=413, detail="Document précédent trop long pour être affiné.")
    prec = None
    if precedent:
        try:
            prec = json.loads(precedent)
        except ValueError:
            raise HTTPException(status_code=400, detail="Document précédent illisible.")
    org = _identite()["nom"] if entete in ("1", "true", "oui") else ""
    _quota(user)

    def travail():
        with ia_usage.suivi(user, "pdf", "MyTools"):
            return pdf_ia.creer(consigne, format, ton, langue, org, prec, affiner)
    try:
        return await run_in_threadpool(travail)
    except pdf_ia.PdfIaErreur as e:
        raise HTTPException(status_code=502, detail=str(e))
