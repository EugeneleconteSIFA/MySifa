"""MySifa — Portail transporteur MyExpé (routes publiques via token).

Objectif:
- Le transporteur ouvre un lien (token) → on marque l'ouverture
- Il consulte ses demandes de devis (RFQ) envoyées à son email
- Il répond en ligne (prix + délai + commentaire optionnel)
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from database import get_db
from app.web.expe_portail_page import get_portail_404_html, get_portail_html
from app.services.email_service import email_expe_reponse_recue, send_email
from app.services import expe_evenements as expe_ev

logger = logging.getLogger(__name__)

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


def _account_email(acc: dict) -> str:
    return (acc.get("email") or "").strip().lower()


_REPONSE_STATUT_RANK = {
    "recue": 0,
    "retenue": 1,
    "ouvert": 2,
    "envoyee": 3,
    "refusee": 4,
    "echec": 5,
}


def _portail_reponse_rank(row: dict) -> tuple:
    """Plus le tuple est petit, plus la ligne est prioritaire à afficher."""
    st = (row.get("reponse_statut") or row.get("statut") or "").strip()
    rid = int(row.get("reponse_id") or row.get("id") or 0)
    has_answer = 0 if row.get("prix") is not None else 1
    return (has_answer, _REPONSE_STATUT_RANK.get(st, 9), -rid)


def _dedupe_portail_demandes(rows: list[dict]) -> list[dict]:
    """Une seule carte par demande de devis (doublons d'envoi RFQ)."""
    best: dict[int, dict] = {}
    for row in rows:
        did = int(row["demande_id"])
        cur = best.get(did)
        if cur is None or _portail_reponse_rank(row) < _portail_reponse_rank(cur):
            best[did] = row
    out = list(best.values())
    out.sort(key=lambda r: (r.get("created_at") or ""), reverse=True)
    return out


def _mark_opened(conn, *, acc: dict, ip: str, user_agent: str | None = None) -> None:
    now = _now_paris_iso()
    email = _account_email(acc)
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
        SET opened_at=?, opened_ip=?,
            statut=CASE WHEN statut='envoyee' THEN 'ouvert' ELSE statut END
        WHERE opened_at IS NULL
          AND LOWER(TRIM(COALESCE(destinataire_email,''))) = LOWER(TRIM(COALESCE(?,'')))
          AND statut IN ('envoyee','ouvert','echec')
        """,
        (now, ip, email),
    )
    tid = acc.get("transporteur_id")
    if tid:
        conn.execute(
            """
            UPDATE expe_devis_reponses
            SET opened_at=?, opened_ip=?,
                destinataire_email=COALESCE(NULLIF(TRIM(destinataire_email),''), ?),
                statut=CASE WHEN statut='envoyee' THEN 'ouvert' ELSE statut END
            WHERE opened_at IS NULL
              AND COALESCE(TRIM(destinataire_email),'') = ''
              AND transporteur_id=?
              AND statut IN ('envoyee','ouvert','echec')
            """,
            (now, ip, email, int(tid)),
        )
    # `opened_at` ci-dessus est un one-shot : il ne retient que la PREMIÈRE
    # visite, et se tait sur les suivantes. Le journal, lui, en garde une par
    # passage — c'est ce qui distingue « il a jeté un œil une fois » de « il
    # revient tous les jours sans répondre ». Signal fort, contrairement au
    # pixel : personne ne charge ce portail par précaution. Dédup 90 s pour ne
    # pas compter deux fois un rafraîchissement ou un retour arrière.
    expe_ev.log_par_email(
        conn,
        email=email,
        canal=expe_ev.CANAL_PORTAIL,
        type_evenement=expe_ev.EV_PORTAIL_OUVERT,
        date=now,
        user_agent=user_agent,
        dedup_secondes=90,
    )


def _find_reponse_row(
    conn,
    *,
    demande_id: int,
    acc: dict,
    reponse_id: int | None = None,
) -> dict | None:
    """Retrouve la ligne expe_devis_reponses liée au compte portail."""
    email = _account_email(acc)
    tid = acc.get("transporteur_id")
    if reponse_id:
        row = conn.execute(
            """
            SELECT id, statut, destinataire_email, transporteur_id, nom_transporteur
            FROM expe_devis_reponses
            WHERE id=? AND demande_id=?
            """,
            (int(reponse_id), int(demande_id)),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        dest = (d.get("destinataire_email") or "").strip().lower()
        if dest and dest != email:
            return None
        if not dest and tid and d.get("transporteur_id") not in (None, int(tid)):
            return None
        return d
    row = conn.execute(
        """
        SELECT id, statut, destinataire_email, transporteur_id, nom_transporteur
        FROM expe_devis_reponses
        WHERE demande_id=?
          AND (
            LOWER(TRIM(COALESCE(destinataire_email,''))) = LOWER(TRIM(COALESCE(?,'')))
            OR (
              COALESCE(TRIM(destinataire_email),'') = ''
              AND transporteur_id IS NOT NULL
              AND transporteur_id = ?
            )
          )
        ORDER BY
          CASE WHEN prix IS NOT NULL THEN 0 ELSE 1 END,
          CASE statut
            WHEN 'recue' THEN 0 WHEN 'retenue' THEN 1 WHEN 'ouvert' THEN 2
            WHEN 'envoyee' THEN 3 WHEN 'refusee' THEN 4 WHEN 'echec' THEN 5
            ELSE 6
          END,
          id DESC
        LIMIT 1
        """,
        (int(demande_id), email, int(tid) if tid else -1),
    ).fetchone()
    return dict(row) if row else None


@router_html.get("/portail/expe/{token}", response_class=HTMLResponse)
def portail_expe_page(request: Request, token: str):
    ip = _client_ip(request)
    try:
        with get_db() as conn:
            acc = _lookup_token(conn, token, ip)
            if not acc:
                return HTMLResponse(content=get_portail_404_html(), status_code=404)
            _mark_opened(
                conn, acc=acc, ip=ip, user_agent=request.headers.get("user-agent")
            )
            conn.commit()
        lang = (request.query_params.get("lang") or "fr").strip().lower()
        if lang not in ("fr", "en"):
            lang = "fr"
        return HTMLResponse(get_portail_html(token, lang=lang))
    except HTTPException as exc:
        if exc.status_code == 429:
            return HTMLResponse(content=get_portail_404_html(), status_code=429)
        raise


@router_api.get("/{token}")
def portail_expe_data(request: Request, token: str):
    ip = _client_ip(request)
    with get_db() as conn:
        acc = _get_account_or_404(conn, token, ip=ip)
        _mark_opened(
            conn, acc=acc, ip=ip, user_agent=request.headers.get("user-agent")
        )
        conn.commit()

        email = _account_email(acc)
        tid = acc.get("transporteur_id")
        # Liste des demandes liées à cet email (ou transporteur_id si anciennes lignes)
        rows = conn.execute(
            """
            SELECT
              d.id AS demande_id,
              d.created_at,
              d.code_postal_destination,
              d.poids_total_kg,
              d.nb_palette,
              d.type_envoi,
              d.type_palette,
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
               OR (
                 COALESCE(TRIM(r.destinataire_email),'') = ''
                 AND r.transporteur_id IS NOT NULL
                 AND r.transporteur_id = ?
               )
            ORDER BY d.created_at DESC, r.id DESC
            LIMIT 200
            """,
            (email, int(tid) if tid else -1),
        ).fetchall()
        demandes = _dedupe_portail_demandes([dict(x) for x in rows])
        return {"email": email, "demandes": demandes}


@router_api.post("/{token}/demandes/{demande_id}/repondre")
def portail_expe_repondre(
    request: Request, token: str, demande_id: int, body: dict = Body(...)
):
    ip = _client_ip(request)
    now = _now_paris_iso()
    with get_db() as conn:
        acc = _get_account_or_404(conn, token, ip=ip)
        email = _account_email(acc)
        reponse_id_body = body.get("reponse_id")
        try:
            reponse_id_int = int(reponse_id_body) if reponse_id_body is not None else None
        except (TypeError, ValueError):
            reponse_id_int = None

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

        rep = _find_reponse_row(
            conn,
            demande_id=int(demande_id),
            acc=acc,
            reponse_id=reponse_id_int,
        )
        if not rep:
            raise HTTPException(status_code=404, detail="Demande introuvable.")

        conn.execute(
            """
            UPDATE expe_devis_reponses
            SET prix=?, delai_jours=?, commentaire=?, statut='recue', recu_at=?,
                destinataire_email=COALESCE(NULLIF(TRIM(destinataire_email),''), ?)
            WHERE id=?
            """,
            (prix, delai, commentaire, now, email, int(rep["id"])),
        )
        conn.execute(
            """
            UPDATE expe_portal_transporteurs
            SET last_opened_at=?, last_opened_ip=?
            WHERE token=?
            """,
            (now, ip, token),
        )
        # Sans dédup : une offre corrigée est une information, pas un doublon.
        # La timeline doit montrer qu'un transporteur a repris son prix.
        expe_ev.log_evenement(
            conn,
            reponse_id=int(rep["id"]),
            demande_id=int(demande_id),
            canal=expe_ev.CANAL_PORTAIL,
            type_evenement=expe_ev.EV_REPONSE_DEPOSEE,
            date=now,
            meta={"prix": prix, "delai_jours": delai},
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
                        nom_transporteur=(rep.get("nom_transporteur") or "").strip() or "Transporteur",
                        email_transporteur=email or None,
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


# ─── Pixel de suivi d'ouverture d'email ───────────────────────────

# GIF transparent 1x1, en dur : aucune lecture disque, aucune dépendance.
_PIXEL_GIF = bytes([
    0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00, 0x01, 0x00, 0x80, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x21, 0xF9, 0x04, 0x01, 0x00,
    0x00, 0x00, 0x00, 0x2C, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00,
    0x00, 0x02, 0x02, 0x44, 0x01, 0x00, 0x3B,
])

_PIXEL_HEADERS = {
    # Sans ces en-têtes, le proxy d'images de Gmail sert sa copie en cache et
    # les ouvertures suivantes n'atteignent jamais le serveur.
    "Cache-Control": "no-store, no-cache, must-revalidate, private, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
    "Content-Disposition": "inline",
}


@router_html.get("/portail/expe/px/{token}.gif", include_in_schema=False)
def pixel_ouverture_email_expe(request: Request, token: str):
    """Trace l'ouverture d'un email de demande de tarif. Renvoie TOUJOURS le GIF.

    Trois règles, reprises telles quelles de MyAO :

    - **Jamais d'erreur.** Token inconnu, base indisponible, ligne supprimée :
      on renvoie le pixel quand même. Un 404 sur une image d'email dessine un
      cadre cassé chez le transporteur et, pire, signale à qui sonde l'URL
      quels tokens existent.
    - **Aucun effet de bord métier.** Le pixel ne fait pas passer la réponse en
      statut `ouvert` et ne remplit pas `opened_at` : ces deux-là veulent dire
      « le portail a été consulté », ce qui est certain. Une ouverture d'email
      n'est qu'un indice — voir `classer_ouverture()`.
    - **Le token ne donne accès à rien.** Il n'identifie que la ligne à
      journaliser ; il est distinct du token portail.
    """
    try:
        with get_db() as conn:
            row = conn.execute(
                """SELECT id, demande_id, sent_at FROM expe_devis_reponses
                   WHERE token_pixel=?""",
                (str(token or "").strip(),),
            ).fetchone()
            if row is not None:
                ua = request.headers.get("user-agent")
                maintenant = expe_ev.now_paris_iso()
                # `?e=` dit QUEL email a été ouvert (demande, attribution).
                # Absent ou inconnu : on journalise quand même sans préciser —
                # mieux vaut un signal imprécis que perdu.
                ctx = str(request.query_params.get("e") or "").strip().lower()
                reference = expe_ev.date_email_reference(
                    conn, int(row["id"]), ctx, row["sent_at"]
                )
                fiable, motif = expe_ev.classer_ouverture(reference, ua, maintenant)
                expe_ev.log_evenement(
                    conn,
                    reponse_id=int(row["id"]),
                    demande_id=(
                        int(row["demande_id"]) if row["demande_id"] is not None else None
                    ),
                    canal=expe_ev.CANAL_EMAIL,
                    type_evenement=expe_ev.EV_EMAIL_OUVERT,
                    date=maintenant,
                    fiable=fiable,
                    motif=motif,
                    user_agent=ua,
                    meta={"email": ctx} if ctx in expe_ev.CONTEXTES else None,
                    dedup_secondes=expe_ev.DEDUP_SECONDES,
                )
                conn.commit()
    except Exception as exc:
        logger.warning("pixel_ouverture_email_expe: %s", exc)

    return Response(content=_PIXEL_GIF, media_type="image/gif", headers=_PIXEL_HEADERS)

