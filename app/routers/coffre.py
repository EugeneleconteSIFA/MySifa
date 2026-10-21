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
import mimetypes
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from config import BASE_DIR, NDF_TAUX_TVA, ROLE_COMPTABILITE, ROLE_SUPERADMIN
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
def download_document(doc_id: int, request: Request, inline: bool = False):
    """Télécharge ou prévisualise (?inline=1) un document RH.

    Propriétaire ou compta/superadmin uniquement. En mode inline, sert le
    fichier avec Content-Disposition: inline pour affichage dans iframe/img.
    """
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
            conn, doc_id, user, "preview" if inline else "download",
            request.client.host if request.client else None,
        )
        conn.commit()
    path = Path(d["fichier_path"])
    if not path.is_file():
        raise HTTPException(410, "Fichier absent du serveur")
    fname = d["fichier_nom"] or path.name
    mime, _ = mimetypes.guess_type(fname)
    if not mime:
        mime = "application/pdf"
    if inline:
        # Content-Disposition: inline → aperçu dans le navigateur (iframe/img)
        return FileResponse(
            str(path),
            media_type=mime,
            headers={"Content-Disposition": f'inline; filename="{fname}"'},
        )
    return FileResponse(str(path), filename=fname, media_type=mime)


# ── Notes de frais — vue salarié (dépôt + workflow) ──────────────────────

def ndf_categories(conn, toutes: bool = False) -> list:
    """Catégories de notes de frais, actives seulement sauf `toutes`."""
    where = "" if toutes else "WHERE actif=1"
    rows = conn.execute(
        f"""SELECT id,code,libelle,saisie,taux_tva,taux_km,ordre,actif
            FROM ndf_categories {where} ORDER BY ordre, libelle"""
    ).fetchall()
    return [dict(r) for r in rows]


def ndf_montants(saisie: str, montant_ttc: Optional[float], taux_tva: float,
                 montant_tva: Optional[float], distance_km: Optional[float],
                 taux_km: Optional[float]) -> dict:
    """TTC, TVA et HT d'une note. Même calcul que `ndfCalcul()` de la page.

    Kilométrique : TTC = distance × taux, sans TVA. Sinon la TVA se déduit du
    TTC et du taux, sauf si l'utilisateur l'a corrigée (ticket à deux taux).
    """
    if saisie == "km":
        if not distance_km or distance_km <= 0:
            raise HTTPException(400, "Distance invalide — nombre de km supérieur à 0.")
        if not taux_km or taux_km <= 0:
            raise HTTPException(400, "Taux kilométrique non défini — à régler par la comptabilité dans Notes de frais › Réglages.")
        ttc = round(distance_km * taux_km, 2)
        return {"montant_ttc": ttc, "montant_tva": 0.0, "montant_ht": ttc, "taux_tva": 0.0}
    if montant_ttc is None or montant_ttc <= 0:
        raise HTTPException(400, "Montant TTC invalide — valeur supérieure à 0.")
    ttc = round(montant_ttc, 2)
    if montant_tva is None:
        montant_tva = round(ttc - ttc / (1 + taux_tva / 100), 2)
    if montant_tva < 0 or montant_tva >= ttc:
        raise HTTPException(400, "TVA invalide — doit rester inférieure au montant TTC.")
    return {
        "montant_ttc": ttc,
        "montant_tva": round(montant_tva, 2),
        "montant_ht": round(ttc - montant_tva, 2),
        "taux_tva": taux_tva,
    }


def _nombre_ou_none(v: str, quoi: str) -> Optional[float]:
    v = (v or "").strip().replace(",", ".")
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        raise HTTPException(400, f"{quoi} invalide — nombre attendu.")


@router.get("/api/coffre/ndf-categories")
def list_ndf_categories(request: Request):
    get_current_user(request)
    with get_db() as conn:
        cats = ndf_categories(conn)
    return {"categories": cats, "taux_tva": list(NDF_TAUX_TVA)}


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
            f"""SELECT id,date_frais,categorie,categorie_id,montant_ttc,montant_tva,
                       montant_ht,taux_tva,distance_km,taux_km,ville,description,
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
    categorie_id: int = Form(...),
    montant_ttc: str = Form(""),
    taux_tva: str = Form(""),
    montant_tva: str = Form(""),
    distance_km: str = Form(""),
    ville: str = Form(""),
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
    with get_db() as conn:
        cat = conn.execute(
            "SELECT id,libelle,saisie,taux_tva,taux_km FROM ndf_categories WHERE id=? AND actif=1",
            (categorie_id,),
        ).fetchone()
    if not cat:
        raise HTTPException(400, "Catégorie inconnue — choisir dans la liste.")
    taux = _nombre_ou_none(taux_tva, "Taux de TVA")
    if taux is None:
        taux = float(cat["taux_tva"])
    if taux not in NDF_TAUX_TVA:
        raise HTTPException(400, "Taux de TVA invalide.")
    m = ndf_montants(
        cat["saisie"],
        _nombre_ou_none(montant_ttc, "Montant TTC"),
        taux,
        _nombre_ou_none(montant_tva, "TVA"),
        _nombre_ou_none(distance_km, "Distance"),
        cat["taux_km"],
    )
    est_km = cat["saisie"] == "km"

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
               (employe_user_id,date_frais,categorie,categorie_id,montant_ttc,montant_tva,
                montant_ht,taux_tva,distance_km,taux_km,ville,description,
                justificatif_path,justificatif_nom,statut,created_at,soumise_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                uid, date_frais[:10], cat["libelle"], cat["id"],
                m["montant_ttc"], m["montant_tva"], m["montant_ht"], m["taux_tva"],
                _nombre_ou_none(distance_km, "Distance") if est_km else None,
                cat["taux_km"] if est_km else None,
                (ville or "").strip()[:80] or None,
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
def download_ndf_justificatif(ndf_id: int, request: Request, inline: bool = False):
    """Télécharge ou prévisualise (?inline=1) le justificatif d'une note de frais.

    Propriétaire ou compta/superadmin uniquement.
    """
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
    fname = row["justificatif_nom"] or path.name
    mime, _ = mimetypes.guess_type(fname)
    if not mime:
        mime = "application/octet-stream"
    if inline:
        return FileResponse(
            str(path),
            media_type=mime,
            headers={"Content-Disposition": f'inline; filename="{fname}"'},
        )
    return FileResponse(str(path), filename=fname, media_type=mime)
