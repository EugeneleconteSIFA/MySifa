"""MySifa — Portail fournisseur AO (routes publiques, token UUID)."""
from __future__ import annotations

import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from app.services.ao_pricing import DEVISES, UNITES_QUOTATION
from app.services.ao_produit_fiche import parse_fiche
from app.services.email_service import email_accuse_reception, send_email
from app.services.path_safety import path_is_under_directory
from app.web.ao_portail_page import get_portail_404_html, get_portail_html
from config import BASE_URL, UPLOAD_DIR
from database import get_db

logger = logging.getLogger(__name__)

router_html = APIRouter(tags=["ao_portail"])
router_api = APIRouter(prefix="/api/portail", tags=["ao_portail_api"])

_PARIS = ZoneInfo("Europe/Paris")
_RATE_WINDOW_SEC = 3600
_RATE_MAX_INVALID = 10
_invalid_attempts: dict[str, list[float]] = {}


def _now_paris_iso() -> str:
    return datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")


def _row_dict(row) -> dict:
    return dict(row) if row else {}


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    cutoff = now - _RATE_WINDOW_SEC
    attempts = [t for t in _invalid_attempts.get(ip, []) if t > cutoff]
    _invalid_attempts[ip] = attempts
    if len(attempts) > _RATE_MAX_INVALID:
        raise HTTPException(status_code=429, detail="Trop de tentatives.")


def _record_invalid_attempt(ip: str) -> None:
    now = time.time()
    cutoff = now - _RATE_WINDOW_SEC
    attempts = [t for t in _invalid_attempts.get(ip, []) if t > cutoff]
    attempts.append(now)
    _invalid_attempts[ip] = attempts


def _lookup_token(
    conn, token: str, ip: str
) -> tuple[dict, dict] | None:
    _check_rate_limit(ip)
    fourni_row = conn.execute(
        "SELECT * FROM ao_fournisseurs WHERE token=?",
        (token,),
    ).fetchone()
    if not fourni_row:
        _record_invalid_attempt(ip)
        return None
    fourni = _row_dict(fourni_row)
    ao_row = conn.execute(
        "SELECT * FROM ao_demandes WHERE id=?",
        (fourni["ao_id"],),
    ).fetchone()
    if not ao_row:
        _record_invalid_attempt(ip)
        return None
    return _row_dict(ao_row), fourni


def _get_fourni_or_404(
    token: str, conn, *, ip: str | None = None
) -> tuple[dict, dict]:
    """Retourne (ao, fournisseur) ou lève HTTPException 404."""
    result = _lookup_token(conn, token, ip or "unknown")
    if not result:
        raise HTTPException(status_code=404, detail="Lien invalide ou expiré")
    return result


def _require_not_cloture(ao: dict) -> None:
    if ao.get("statut") == "cloturee":
        raise HTTPException(
            status_code=403,
            detail="Cet appel d'offre est clôturé.",
        )


def _fourni_upload_dir(ao_id: int, fourni_id: int) -> str:
    path = os.path.join(UPLOAD_DIR, "ao", str(ao_id), "fournisseurs", str(fourni_id))
    os.makedirs(path, exist_ok=True)
    return path


def _ao_pj_path(ao_id: int, stored_name: str, fourni_id: int | None = None) -> str:
    if fourni_id is not None:
        return os.path.join(_fourni_upload_dir(ao_id, fourni_id), stored_name)
    return os.path.join(UPLOAD_DIR, "ao", str(ao_id), stored_name)


def _mp_label(conn, mid: Any) -> str | None:
    if mid is None:
        return None
    try:
        mid = int(mid)
    except (TypeError, ValueError):
        return None
    m = conn.execute(
        "SELECT reference, designation FROM matieres_premieres WHERE id=? AND actif=1",
        (mid,),
    ).fetchone()
    if not m:
        return None
    ref = (m["reference"] or "").strip()
    des = (m["designation"] or "").strip()
    return f"{ref} — {des}".strip(" —") or None


def _produit_ctx_for_ligne(conn, ref_produit: str) -> dict:
    row = conn.execute(
        """SELECT p.fiche_json, c.nom AS client_nom
           FROM ao_produits p
           LEFT JOIN ao_carnet_clients c ON c.id = p.client_id
           WHERE LOWER(p.ref) = LOWER(?)
           LIMIT 1""",
        ((ref_produit or "").strip(),),
    ).fetchone()
    if not row:
        return {}
    fiche = parse_fiche(row["fiche_json"])
    mat = fiche.get("matiere") or {}
    bob = fiche.get("bobines") or {}
    nb = bob.get("nb_etiquettes")
    try:
        nb = float(nb) if nb is not None else None
    except (TypeError, ValueError):
        nb = None
    return {
        "client_nom": row["client_nom"],
        "frontal": _mp_label(conn, mat.get("frontal_id")),
        "adhesif": _mp_label(conn, mat.get("adhesif_id")),
        "etiquettes_par_bobine": nb,
    }


def _portail_payload(conn, ao: dict, fourni: dict) -> dict[str, Any]:
    ao_id = int(ao["id"])
    fourni_id = int(fourni["id"])
    lignes_raw = conn.execute(
        """SELECT id, ref_produit, designation, quantite, unite, notes, position
           FROM ao_lignes WHERE ao_id=? ORDER BY position, id""",
        (ao_id,),
    ).fetchall()
    lignes = []
    for r in lignes_raw:
        ln = _row_dict(r)
        ctx = _produit_ctx_for_ligne(conn, ln.get("ref_produit") or "")
        ln.update(ctx)
        lignes.append(ln)
    reponses = [
        _row_dict(r)
        for r in conn.execute(
            """SELECT ligne_id, quotation, prix_unitaire, devise, unite_quotation,
                      delai_jours, commentaire
               FROM ao_reponses WHERE ao_fournisseur_id=?""",
            (fourni_id,),
        ).fetchall()
    ]
    pj_ao = [
        _row_dict(r)
        for r in conn.execute(
            """SELECT id, filename, taille_octets FROM ao_pieces_jointes
               WHERE ao_id=? AND ao_fournisseur_id IS NULL
               ORDER BY date DESC""",
            (ao_id,),
        ).fetchall()
    ]
    pj_fournisseur = [
        _row_dict(r)
        for r in conn.execute(
            """SELECT id, filename, taille_octets FROM ao_pieces_jointes
               WHERE ao_fournisseur_id=?
               ORDER BY date DESC""",
            (fourni_id,),
        ).fetchall()
    ]
    return {
        "ao": {
            "id": ao["id"],
            "reference": ao.get("reference"),
            "titre": ao.get("titre"),
            "description": ao.get("description"),
            "date_limite": ao.get("date_limite"),
            "statut": ao.get("statut"),
        },
        "fournisseur": {
            "id": fourni["id"],
            "nom_fournisseur": fourni.get("nom_fournisseur"),
            "statut": fourni.get("statut"),
            "commentaire_global": fourni.get("commentaire_global"),
        },
        "lignes": lignes,
        "reponses": reponses,
        "pj_ao": pj_ao,
        "pj_fournisseur": pj_fournisseur,
        "cloture": ao.get("statut") == "cloturee",
    }


# ─── HTML ─────────────────────────────────────────────────────────

@router_html.get("/portail/ao/{token}", response_class=HTMLResponse)
def portail_page(request: Request, token: str):
    ip = _client_ip(request)
    try:
        with get_db() as conn:
            found = _lookup_token(conn, token, ip)
            if not found:
                return HTMLResponse(
                    content=get_portail_404_html(),
                    status_code=404,
                )
            ao, fourni = found
            if not fourni.get("date_ouverture"):
                now = _now_paris_iso()
                conn.execute(
                    """UPDATE ao_fournisseurs
                       SET statut='ouvert', date_ouverture=?
                       WHERE id=? AND date_ouverture IS NULL""",
                    (now, fourni["id"]),
                )
                conn.commit()
                fourni["statut"] = "ouvert"
                fourni["date_ouverture"] = now
        return HTMLResponse(get_portail_html(token, ao, fourni))
    except HTTPException as exc:
        if exc.status_code == 429:
            return HTMLResponse(
                content=get_portail_404_html().replace(
                    "Lien invalide ou expiré",
                    "Trop de tentatives",
                ).replace(
                    "Ce lien de demande de prix n'est pas reconnu.",
                    "Réessayez plus tard.",
                ),
                status_code=429,
            )
        raise


# ─── API JSON ─────────────────────────────────────────────────────

@router_api.get("/ao/{token}")
def get_portail_data(request: Request, token: str):
    ip = _client_ip(request)
    with get_db() as conn:
        ao, fourni = _get_fourni_or_404(token, conn, ip=ip)
        if not fourni.get("date_ouverture"):
            now = _now_paris_iso()
            conn.execute(
                """UPDATE ao_fournisseurs
                   SET statut='ouvert', date_ouverture=?
                   WHERE id=? AND date_ouverture IS NULL""",
                (now, fourni["id"]),
            )
            conn.commit()
            fourni["statut"] = "ouvert"
            fourni["date_ouverture"] = now
        return _portail_payload(conn, ao, fourni)


@router_api.post("/ao/{token}/repondre")
async def repondre_ao(request: Request, token: str):
    ip = _client_ip(request)
    body = await request.json()
    lignes_in = body.get("lignes") or []
    commentaire_global = (body.get("commentaire_global") or "").strip() or None
    now = _now_paris_iso()

    with get_db() as conn:
        ao, fourni = _get_fourni_or_404(token, conn, ip=ip)
        _require_not_cloture(ao)
        ao_id = int(ao["id"])
        fourni_id = int(fourni["id"])

        valid_ligne_ids = {
            int(r["id"])
            for r in conn.execute(
                "SELECT id FROM ao_lignes WHERE ao_id=?", (ao_id,)
            ).fetchall()
        }

        for item in lignes_in:
            try:
                ligne_id = int(item.get("ligne_id"))
            except (TypeError, ValueError):
                continue
            if ligne_id not in valid_ligne_ids:
                raise HTTPException(status_code=400, detail="Ligne invalide.")
            quotation = item.get("quotation")
            if quotation is None:
                quotation = item.get("prix_unitaire")
            if quotation is not None:
                try:
                    quotation = float(quotation)
                except (TypeError, ValueError):
                    quotation = None
            devise = (item.get("devise") or "EUR").strip().upper()
            if devise not in DEVISES:
                devise = "EUR"
            unite_q = (item.get("unite_quotation") or "mille").strip().lower()
            if unite_q not in UNITES_QUOTATION:
                unite_q = "mille"
            delai = item.get("delai_jours")
            if delai is not None:
                try:
                    delai = int(delai)
                except (TypeError, ValueError):
                    delai = None
            commentaire = (item.get("commentaire") or "").strip() or None
            conn.execute(
                """INSERT OR REPLACE INTO ao_reponses
                   (ao_fournisseur_id, ligne_id, quotation, prix_unitaire,
                    devise, unite_quotation, delai_jours, commentaire)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    fourni_id,
                    ligne_id,
                    quotation,
                    quotation,
                    devise,
                    unite_q,
                    delai,
                    commentaire,
                ),
            )

        conn.execute(
            """UPDATE ao_fournisseurs
               SET statut='repondu', date_reponse=?, commentaire_global=?
               WHERE id=?""",
            (now, commentaire_global, fourni_id),
        )
        conn.commit()

        lignes_db = [
            _row_dict(r)
            for r in conn.execute(
                "SELECT * FROM ao_lignes WHERE ao_id=? ORDER BY position, id",
                (ao_id,),
            ).fetchall()
        ]
        reponses_db = [
            _row_dict(r)
            for r in conn.execute(
                """SELECT ligne_id, prix_unitaire, delai_jours, commentaire
                   FROM ao_reponses WHERE ao_fournisseur_id=?""",
                (fourni_id,),
            ).fetchall()
        ]
        fourni = _row_dict(
            conn.execute(
                "SELECT * FROM ao_fournisseurs WHERE id=?", (fourni_id,)
            ).fetchone()
        )

    responsable = (ao.get("responsable_email") or "").strip()
    if responsable:
        subject, html_body = email_accuse_reception(
            ao, fourni, lignes_db, reponses_db
        )
        send_email(responsable, subject, html_body)

    return {"ok": True}


@router_api.get("/ao/{token}/messages")
def list_portail_messages(request: Request, token: str):
    ip = _client_ip(request)
    with get_db() as conn:
        ao, fourni = _get_fourni_or_404(token, conn, ip=ip)
        rows = conn.execute(
            """SELECT * FROM ao_messages
               WHERE ao_fournisseur_id=?
               ORDER BY date ASC""",
            (fourni["id"],),
        ).fetchall()
    return [_row_dict(r) for r in rows]


@router_api.post("/ao/{token}/messages")
async def post_portail_message(request: Request, token: str):
    ip = _client_ip(request)
    body = await request.json()
    message = (body.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message vide.")
    now = _now_paris_iso()

    with get_db() as conn:
        ao, fourni = _get_fourni_or_404(token, conn, ip=ip)
        _require_not_cloture(ao)
        cur = conn.execute(
            """INSERT INTO ao_messages
               (ao_fournisseur_id, expediteur, auteur_nom, message, date, lu)
               VALUES (?,'fournisseur',?,?,?,0)""",
            (
                fourni["id"],
                fourni.get("nom_fournisseur"),
                message,
                now,
            ),
        )
        conn.commit()
        inserted = conn.execute(
            "SELECT * FROM ao_messages WHERE id=?", (cur.lastrowid,)
        ).fetchone()

    responsable = (ao.get("responsable_email") or "").strip()
    if responsable:
        reference = ao.get("reference") or ""
        nom = fourni.get("nom_fournisseur") or ""
        lien = f"{BASE_URL.rstrip('/')}/portail/ao/{token}"
        subject = f"[MySifa] Message de {nom} — {reference}"
        corps = (
            f"{nom} vous a envoyé un message :\n\n{message}\n\nLien : {lien}"
        )
        html_body = (
            "<div style=\"font-family:'Segoe UI',system-ui,sans-serif;font-size:14px;"
            "line-height:1.6;white-space:pre-wrap\">"
            + corps.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            + "</div>"
        )
        send_email(responsable, subject, html_body)

    return {"ok": True, "message": _row_dict(inserted) if inserted else None}


@router_api.post("/ao/{token}/pieces-jointes")
async def upload_portail_pj(
    request: Request,
    token: str,
    file: UploadFile = File(...),
):
    ip = _client_ip(request)
    raw_name = file.filename or "fichier"
    ext = Path(raw_name).suffix.lower()
    stored_name = str(uuid.uuid4()) + ext
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide.")

    with get_db() as conn:
        ao, fourni = _get_fourni_or_404(token, conn, ip=ip)
        _require_not_cloture(ao)
        ao_id = int(ao["id"])
        fourni_id = int(fourni["id"])
        dest_dir = _fourni_upload_dir(ao_id, fourni_id)
        dest_path = os.path.join(dest_dir, stored_name)
        try:
            with open(dest_path, "wb") as out:
                out.write(content)
        except OSError:
            raise HTTPException(
                status_code=500,
                detail="Enregistrement du fichier impossible.",
            )
        now = _now_paris_iso()
        cur = conn.execute(
            """INSERT INTO ao_pieces_jointes
               (ao_id, ao_fournisseur_id, filename, stored_name, taille_octets, uploaded_by, date)
               VALUES (?,?,?,?,?,?,?)""",
            (
                ao_id,
                fourni_id,
                os.path.basename(raw_name),
                stored_name,
                len(content),
                fourni.get("nom_fournisseur"),
                now,
            ),
        )
        conn.commit()
        pj = conn.execute(
            "SELECT * FROM ao_pieces_jointes WHERE id=?", (cur.lastrowid,)
        ).fetchone()

    return {"ok": True, "pj": _row_dict(pj)}


@router_api.get("/ao/{token}/pieces-jointes/{pj_id}/download")
def download_fournisseur_pj(request: Request, token: str, pj_id: int):
    ip = _client_ip(request)
    with get_db() as conn:
        ao, fourni = _get_fourni_or_404(token, conn, ip=ip)
        ao_id = int(ao["id"])
        fourni_id = int(fourni["id"])
        pj = conn.execute(
            """SELECT * FROM ao_pieces_jointes
               WHERE id=? AND ao_id=? AND ao_fournisseur_id=?""",
            (pj_id, ao_id, fourni_id),
        ).fetchone()
        if not pj:
            raise HTTPException(status_code=404, detail="Pièce jointe introuvable")
        pj = _row_dict(pj)

    path = _ao_pj_path(ao_id, pj["stored_name"], fourni_id)
    root = _fourni_upload_dir(ao_id, fourni_id)
    if not path_is_under_directory(path, root) or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(path=path, filename=pj.get("filename") or pj["stored_name"])


@router_api.get("/ao/{token}/pj-ao/{pj_id}/download")
def download_ao_pj(request: Request, token: str, pj_id: int):
    ip = _client_ip(request)
    with get_db() as conn:
        ao, fourni = _get_fourni_or_404(token, conn, ip=ip)
        ao_id = int(ao["id"])
        pj = conn.execute(
            """SELECT * FROM ao_pieces_jointes
               WHERE id=? AND ao_id=? AND ao_fournisseur_id IS NULL""",
            (pj_id, ao_id),
        ).fetchone()
        if not pj:
            raise HTTPException(status_code=404, detail="Pièce jointe introuvable")
        pj = _row_dict(pj)

    path = _ao_pj_path(ao_id, pj["stored_name"])
    root = os.path.join(UPLOAD_DIR, "ao", str(ao_id))
    os.makedirs(root, exist_ok=True)
    if not path_is_under_directory(path, root) or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(path=path, filename=pj.get("filename") or pj["stored_name"])
