"""MySifa — Portail transporteur MyExpé (routes publiques via token).

Objectif:
- Le transporteur ouvre un lien (token) → on marque l'ouverture
- Il consulte ses demandes de devis (RFQ) envoyées à son email
- Il répond en ligne (prix + délai + commentaire optionnel)
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import HTMLResponse

from database import get_db
from app.web.expe_portail_page import get_portail_404_html, get_portail_html
from app.services.email_service import email_expe_reponse_recue, send_email

EXPE_DEVIS_CC = "expeditions@sifa.pro"

router_html = APIRouter(tags=["expe_portail"])
router_api = APIRouter(prefix="/api/portail/expe", tags=["expe_portail_api"])

_PARIS = ZoneInfo("Europe/Paris")
_RATE_WINDOW_SEC = 3600
_RATE_MAX_INVALID = 10
_invalid_attempts: dict[str, list[float]] = {}


def _now_paris_iso() -> str:
    return datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")


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


def _row_dict(row) -> dict:
    return dict(row) if row else {}


def _lookup_token(conn, token: str, ip: str) -> Optional[dict]:
    _check_rate_limit(ip)
    row = conn.execute(
        "SELECT * FROM expe_portal_transporteurs WHERE token=? AND actif=1",
        (token,),
    ).fetchone()
    if not row:
        _record_invalid_attempt(ip)
        return None
    return _row_dict(row)


def _get_account_or_404(conn, token: str, *, ip: str) -> dict:
    acc = _lookup_token(conn, token, ip)
    if not acc:
        raise HTTPException(status_code=404, detail="Lien invalide ou expiré")
    return acc


def _mark_opened(conn, *, acc: dict, ip: str) -> None:
    now = _now_paris_iso()
    # Best-effort: marquer l'ouverture dans le compte + sur les lignes de réponse
    conn.execute(
        """
        UPDATE expe_portal_transporteurs
        SET last_opened_at=?, last_opened_ip=?
        WHERE id=?
        """,
        (now, ip, int(acc["id"])),
    )
    conn.execute(
        """
        UPDATE expe_devis_reponses
        SET opened_at=?, opened_ip=?
        WHERE opened_at IS NULL
          AND destinataire_email=?
          AND statut IN ('envoyee','ouvert','echec')
        """,
        (now, ip, (acc.get("email") or "").strip().lower()),
    )


@router_html.get("/portail/expe/{token}", response_class=HTMLResponse)
def portail_expe_page(request: Request, token: str):
    ip = _client_ip(request)
    try:
        with get_db() as conn:
            acc = _lookup_token(conn, token, ip)
            if not acc:
                return HTMLResponse(content=get_portail_404_html(), status_code=404)
            _mark_opened(conn, acc=acc, ip=ip)
            conn.commit()
        return HTMLResponse(get_portail_html(token))
    except HTTPException as exc:
        if exc.status_code == 429:
            return HTMLResponse(content=get_portail_404_html(), status_code=429)
        raise


@router_api.get("/{token}")
def portail_expe_data(request: Request, token: str):
    ip = _client_ip(request)
    with get_db() as conn:
        acc = _get_account_or_404(conn, token, ip=ip)
        _mark_opened(conn, acc=acc, ip=ip)
        conn.commit()

        email = (acc.get("email") or "").strip().lower()
        # Liste des demandes liées à cet email (expe_devis_reponses.destinataire_email)
        rows = conn.execute(
            """
            SELECT
              d.id AS demande_id,
              d.created_at,
              d.code_postal_destination,
              d.poids_total_kg,
              d.nb_palette,
              d.type_envoi,
              d.contraintes,
              d.statut AS demande_statut,
              r.id AS reponse_id,
              r.nom_transporteur,
              r.prix,
              r.delai_jours,
              r.commentaire,
              r.statut AS reponse_statut,
              r.sent_at,
              r.opened_at,
              r.recu_at
            FROM expe_devis_reponses r
            JOIN expe_demandes_devis d ON d.id = r.demande_id
            WHERE LOWER(TRIM(COALESCE(r.destinataire_email,''))) = LOWER(TRIM(COALESCE(?,'')))
            ORDER BY d.created_at DESC, r.id DESC
            LIMIT 200
            """,
            (email,),
        ).fetchall()
        demandes = [dict(x) for x in rows]
        return {"email": email, "demandes": demandes}


@router_api.post("/{token}/demandes/{demande_id}/repondre")
def portail_expe_repondre(
    request: Request, token: str, demande_id: int, body: dict = Body(...)
):
    ip = _client_ip(request)
    now = _now_paris_iso()
    with get_db() as conn:
        acc = _get_account_or_404(conn, token, ip=ip)
        email = (acc.get("email") or "").strip().lower()

        try:
            prix = float(body.get("prix"))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Prix invalide.")
        if prix <= 0:
            raise HTTPException(status_code=400, detail="Prix invalide.")

        try:
            delai = int(body.get("delai_jours"))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Délai invalide.")
        if delai < 0 or delai > 365:
            raise HTTPException(status_code=400, detail="Délai invalide.")

        commentaire = (body.get("commentaire") or "").strip() or None
        if commentaire and len(commentaire) > 2000:
            raise HTTPException(status_code=400, detail="Commentaire trop long.")

        rep = conn.execute(
            """
            SELECT id, statut FROM expe_devis_reponses
            WHERE demande_id=?
              AND LOWER(TRIM(COALESCE(destinataire_email,''))) = LOWER(TRIM(COALESCE(?,'')))
            ORDER BY id DESC
            LIMIT 1
            """,
            (int(demande_id), email),
        ).fetchone()
        if not rep:
            raise HTTPException(status_code=404, detail="Demande introuvable.")

        conn.execute(
            """
            UPDATE expe_devis_reponses
            SET prix=?, delai_jours=?, commentaire=?, statut='recue', recu_at=?
            WHERE id=?
            """,
            (prix, delai, commentaire, now, int(rep["id"])),
        )
        conn.execute(
            """
            UPDATE expe_portal_transporteurs
            SET last_opened_at=?, last_opened_ip=?
            WHERE token=?
            """,
            (now, ip, token),
        )
        conn.commit()

        # Notification interne (best-effort) : auteur + copie expéditions.
        try:
            demande_row = conn.execute(
                "SELECT * FROM expe_demandes_devis WHERE id=?",
                (int(demande_id),),
            ).fetchone()
            if demande_row:
                demande = dict(demande_row)
                to_email = (demande.get("created_by_email") or "").strip() or None
                if to_email:
                    subject, html_body = email_expe_reponse_recue(
                        demande=demande,
                        nom_transporteur=(acc.get("email") or "Transporteur"),
                        prix=prix,
                        delai_jours=delai,
                        commentaire=commentaire,
                    )
                    send_email(
                        to=to_email,
                        subject=subject,
                        html_body=html_body,
                        reply_to=to_email,
                        cc=EXPE_DEVIS_CC,
                    )
        except Exception:
            # Ne jamais bloquer la réponse transporteur pour un problème de notification
            pass

    return {"success": True}

