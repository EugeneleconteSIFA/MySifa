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

from fastapi import APIRouter, Body, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response

from config import EXPE_DEVIS_FROM
from database import get_db
from app.web.expe_portail_page import get_portail_404_html, get_portail_html
from app.services.email_service import email_expe_reponse_recue, send_email
from app.services import expe_evenements as expe_ev
from app.services.auth_service import get_optional_user

logger = logging.getLogger(__name__)

# Notification interne quand un transporteur dépose une offre : la boîte du
# service reste en copie du créateur, pour qu'une offre ne dorme pas dans une
# boîte personnelle pendant une absence.
EXPE_DEVIS_CC = EXPE_DEVIS_FROM


def _visiteur_interne(request: Request) -> bool:
    """Vrai si la visite du portail vient d'un utilisateur MySifa connecté.

    Le portail est servi par le même domaine que l'application : un
    navigateur qui y arrive depuis nos bureaux porte encore son cookie de
    session. C'est un signal certain, contrairement au pixel — et il évite le
    dégât le plus visible : le créateur qui clique sur le lien du mail dont
    il est en copie faisait basculer la ligne en « Ouverte », c'est-à-dire
    affirmait que le transporteur avait consulté sa demande.

    Un transporteur, lui, n'a jamais de session MySifa : il ne peut pas être
    pris pour un interne par erreur.
    """
    try:
        return get_optional_user(request) is not None
    except Exception:
        return False

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
    # `opened_at` garde la PREMIÈRE consultation (COALESCE), mais le statut,
    # lui, doit repasser à `ouvert` à chaque fois. Avant, la garde
    # `WHERE opened_at IS NULL` portait sur les deux : après un renvoi qui
    # remet le statut à `envoyee`, une nouvelle visite ne le relevait plus
    # jamais — la colonne mentait et le bouton « Relancer » restait proposé à
    # un transporteur revenu trois fois sur la page.
    conn.execute(
        """
        UPDATE expe_devis_reponses
        SET opened_at=COALESCE(opened_at, ?), opened_ip=COALESCE(opened_ip, ?),
            statut=CASE WHEN statut IN ('envoyee','echec') THEN 'ouvert' ELSE statut END
        WHERE LOWER(TRIM(COALESCE(destinataire_email,''))) = LOWER(TRIM(COALESCE(?,'')))
          AND statut IN ('envoyee','ouvert','echec')
        """,
        (now, ip, email),
    )
    tid = acc.get("transporteur_id")
    if tid:
        conn.execute(
            """
            UPDATE expe_devis_reponses
            SET opened_at=COALESCE(opened_at, ?), opened_ip=COALESCE(opened_ip, ?),
                destinataire_email=COALESCE(NULLIF(TRIM(destinataire_email),''), ?),
                statut=CASE WHEN statut IN ('envoyee','echec') THEN 'ouvert' ELSE statut END
            WHERE COALESCE(TRIM(destinataire_email),'') = ''
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


def _require_demande_ouverte_portail(conn, demande_id: int) -> dict:
    """403 propre si la demande n'est plus ouverte, 404 si elle n'existe plus."""
    row = conn.execute(
        "SELECT id, statut, deleted_at FROM expe_demandes_devis WHERE id=?",
        (int(demande_id),),
    ).fetchone()
    if not row or row["deleted_at"]:
        raise HTTPException(status_code=404, detail="Demande introuvable.")
    if (row["statut"] or "") != "ouverte":
        raise HTTPException(
            status_code=403,
            detail="Cette consultation est close : votre offre ne peut plus être enregistrée.",
        )
    return dict(row)


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
    interne = _visiteur_interne(request)
    try:
        with get_db() as conn:
            acc = _lookup_token(conn, token, ip)
            if not acc:
                return HTMLResponse(content=get_portail_404_html(), status_code=404)
            if not interne:
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
    interne = _visiteur_interne(request)
    with get_db() as conn:
        acc = _get_account_or_404(conn, token, ip=ip)
        if not interne:
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
              d.date_limite,
              d.reference,
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
            WHERE d.deleted_at IS NULL
              AND (
                LOWER(TRIM(COALESCE(r.destinataire_email,''))) = LOWER(TRIM(COALESCE(?,'')))
                OR (
                  COALESCE(TRIM(r.destinataire_email),'') = ''
                  AND r.transporteur_id IS NOT NULL
                  AND r.transporteur_id = ?
                )
              )
            ORDER BY d.created_at DESC, r.id DESC
            LIMIT 200
            """,
            (email, int(tid) if tid else -1),
        ).fetchall()
        demandes = _dedupe_portail_demandes([dict(x) for x in rows])
        # Documents joints à chaque demande. Ils n'étaient accessibles qu'en
        # interne (route protégée par get_current_user) : le transporteur ne
        # pouvait pas consulter le plan de chargement qu'on lui avait préparé,
        # et devait le redemander par mail.
        for dem in demandes:
            dem["pieces_jointes"] = [
                {"id": int(p["id"]), "filename": p["filename"], "taille_octets": p["taille_octets"]}
                for p in conn.execute(
                    """SELECT id, filename, taille_octets FROM expe_devis_pieces_jointes
                       WHERE demande_id=? AND origine='sifa' ORDER BY id""",
                    (int(dem["demande_id"]),),
                ).fetchall()
            ]
            dem["mes_fichiers"] = [
                {"id": int(p["id"]), "filename": p["filename"], "taille_octets": p["taille_octets"]}
                for p in conn.execute(
                    """SELECT id, filename, taille_octets FROM expe_devis_pieces_jointes
                       WHERE demande_id=? AND origine='transporteur' AND reponse_id=?
                       ORDER BY id""",
                    (int(dem["demande_id"]), int(dem["reponse_id"] or 0)),
                ).fetchall()
            ]
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

        # Garde côté portail : une demande clôturée n'attend plus de prix, et
        # accepter une offre après attribution ne pourrait que semer la
        # confusion chez le transporteur qui la déposerait.
        _require_demande_ouverte_portail(conn, int(demande_id))

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
                _notifier_reponse_devis(
                    conn,
                    demande=demande,
                    nom_transporteur=(rep.get("nom_transporteur") or "").strip() or "Un transporteur",
                    prix=prix,
                )
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


def _notifier_reponse_devis(conn, *, demande: dict, nom_transporteur: str, prix: float) -> None:
    """Notification push au demandeur quand une offre arrive. Ne lève jamais.

    L'email d'accusé existait déjà, mais un email arrive dans une boîte qu'on
    ne regarde pas toujours ; la notification est ce qui fait qu'on revient sur
    la page au bon moment. Le compteur « 3/5 reçues » y est mis parce que
    « une offre est arrivée » ne dit pas s'il reste à attendre.
    """
    try:
        email = (demande.get("created_by_email") or "").strip().lower()
        if not email:
            return
        u = conn.execute(
            "SELECT id FROM users WHERE LOWER(TRIM(email))=? OR LOWER(TRIM(identifiant))=? LIMIT 1",
            (email, email),
        ).fetchone()
        if not u:
            return
        c = conn.execute(
            """SELECT SUM(CASE WHEN statut IN ('recue','retenue') THEN 1 ELSE 0 END) AS recues,
                      SUM(CASE WHEN statut IN ('envoyee','ouvert','recue','retenue','refusee')
                          THEN 1 ELSE 0 END) AS envoyes
               FROM expe_devis_reponses WHERE demande_id=?""",
            (int(demande["id"]),),
        ).fetchone()
        recues, envoyes = int(c["recues"] or 0), int(c["envoyes"] or 0)
        ref = demande.get("reference") or f"#{demande['id']}"
        from app.routers.push import send_push_safe

        send_push_safe(
            int(u["id"]),
            title=f"Devis transport {ref} — offre reçue",
            body=(
                f"{nom_transporteur} : {prix:.2f} € HT. "
                f"{recues}/{envoyes} réponse(s)."
                + (" Toutes les offres sont là." if envoyes and recues >= envoyes else "")
            ),
            url="/expe#devis",
            tag=f"expe-devis-{demande['id']}",
        )
    except Exception:
        pass


def _pj_accessible(conn, pj_id: int, email: str, transporteur_id) -> dict | None:
    """Une pièce jointe est lisible par ce compte portail si…

    …c'est un document SIFA d'une demande à laquelle il a été sollicité, ou
    un fichier qu'il a lui-même déposé. On ne se contente pas de l'id : une
    URL devinée ne doit pas ouvrir la cotation d'un concurrent.
    """
    row = conn.execute(
        """SELECT pj.*, r.destinataire_email, r.transporteur_id AS r_trp
           FROM expe_devis_pieces_jointes pj
           JOIN expe_demandes_devis d ON d.id = pj.demande_id AND d.deleted_at IS NULL
           LEFT JOIN expe_devis_reponses r ON r.id = pj.reponse_id
           WHERE pj.id=?""",
        (int(pj_id),),
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    if d["origine"] == "transporteur":
        dest = (d.get("destinataire_email") or "").strip().lower()
        if dest and dest == email:
            return d
        if not dest and transporteur_id and d.get("r_trp") == int(transporteur_id):
            return d
        return None
    sollicite = conn.execute(
        """SELECT 1 FROM expe_devis_reponses
           WHERE demande_id=?
             AND (LOWER(TRIM(COALESCE(destinataire_email,''))) = ?
                  OR (COALESCE(TRIM(destinataire_email),'')='' AND transporteur_id=?))
           LIMIT 1""",
        (int(d["demande_id"]), email, int(transporteur_id) if transporteur_id else -1),
    ).fetchone()
    return d if sollicite else None


@router_html.get("/portail/expe/{token}/pj/{pj_id}")
def portail_expe_download_pj(request: Request, token: str, pj_id: int):
    """Téléchargement d'un document, côté transporteur."""
    ip = _client_ip(request)
    with get_db() as conn:
        acc = _get_account_or_404(conn, token, ip=ip)
        pj = _pj_accessible(conn, pj_id, _account_email(acc), acc.get("transporteur_id"))
    if not pj:
        raise HTTPException(status_code=404, detail="Fichier introuvable.")
    from config import BASE_DIR
    from pathlib import Path

    path_abs = Path(BASE_DIR) / pj["path"]
    if not path_abs.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable.")
    return FileResponse(path=str(path_abs), filename=pj["filename"] or path_abs.name)


@router_api.post("/{token}/demandes/{demande_id}/piece-jointe")
async def portail_expe_upload(
    request: Request, token: str, demande_id: int, file: UploadFile = File(...)
):
    """Le transporteur joint un fichier à son offre.

    Sans cela, sa cotation PDF ou sa photo de contrainte d'accès partait par
    mail à côté du portail — et n'entrait jamais dans le comparatif. Le fichier
    est rattaché à SA ligne de réponse, pas à la demande : deux transporteurs
    ne doivent pas voir les documents l'un de l'autre.
    """
    ip = _client_ip(request)
    now = _now_paris_iso()
    # Le token est vérifié AVANT de lire le corps : sinon n'importe quel
    # appelant non authentifié fait spooler 20 Mo sur le disque du serveur
    # avant de recevoir son 404, et le rate-limit anti-énumération n'a jamais
    # l'occasion de s'appliquer.
    with get_db() as conn:
        acc = _get_account_or_404(conn, token, ip=ip)
        _require_demande_ouverte_portail(conn, int(demande_id))
        rep = _find_reponse_row(conn, demande_id=int(demande_id), acc=acc)
        if not rep:
            raise HTTPException(status_code=404, detail="Demande introuvable.")
        deja = conn.execute(
            """SELECT COUNT(*) AS n FROM expe_devis_pieces_jointes
               WHERE reponse_id=? AND origine='transporteur'""",
            (int(rep["id"]),),
        ).fetchone()
        if int(deja["n"] or 0) >= 5:
            raise HTTPException(status_code=400, detail="5 fichiers maximum par offre.")

        contents = await file.read()
        if len(contents) > 20 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 20 Mo).")
        if not contents:
            raise HTTPException(status_code=400, detail="Fichier vide.")

        from app.routers.expe_departs import (
            _DEVIS_UPLOAD_SUBDIR,
            _devis_safe_filename,
            _devis_upload_dir,
        )
        import uuid as _uuid

        orig = (file.filename or "fichier").strip()
        unique = f"{demande_id}_trp{rep['id']}_{_uuid.uuid4().hex[:8]}_{_devis_safe_filename(orig)}"
        with open(_devis_upload_dir() / unique, "wb") as out:
            out.write(contents)
        conn.execute(
            """INSERT INTO expe_devis_pieces_jointes
               (demande_id, reponse_id, origine, filename, path, taille_octets,
                created_at, created_by_email)
               VALUES (?,?,'transporteur',?,?,?,?,?)""",
            (
                int(demande_id),
                int(rep["id"]),
                orig,
                f"{_DEVIS_UPLOAD_SUBDIR}/{unique}",
                len(contents),
                now,
                _account_email(acc),
            ),
        )
        expe_ev.log_evenement(
            conn,
            reponse_id=int(rep["id"]),
            demande_id=int(demande_id),
            canal=expe_ev.CANAL_PORTAIL,
            type_evenement=expe_ev.EV_PJ_DEPOSEE,
            date=now,
            meta={"filename": orig, "octets": len(contents)},
        )
        conn.commit()
    return {"success": True, "filename": orig}


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

    Quatrième règle depuis août 2026 : **un hit venu de chez nous est
    enregistré, jamais compté.** Le créateur de la demande est en copie du
    mail, donc son client de messagerie charge le même pixel que le
    transporteur. L'IP source est journalisée et confrontée à
    `EXPE_IPS_INTERNES` ; ce qui échappe au filtre (Outlook Web, mobile, qui
    passent par les serveurs Microsoft) se corrige à la main depuis la
    timeline.
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
                ip = _client_ip(request)
                maintenant = expe_ev.now_paris_iso()
                # `?e=` dit QUEL email a été ouvert (demande, attribution).
                # Absent ou inconnu : on journalise quand même sans préciser —
                # mieux vaut un signal imprécis que perdu.
                ctx = str(request.query_params.get("e") or "").strip().lower()
                reference = expe_ev.date_email_reference(
                    conn, int(row["id"]), ctx, row["sent_at"]
                )
                fiable, motif = expe_ev.classer_ouverture(reference, ua, maintenant)
                # L'origine interne prime sur toute autre classification :
                # savoir que le hit vient de nous est plus utile que de savoir
                # qu'il ressemble à un préchargement.
                if expe_ev.est_ip_interne(ip):
                    fiable, motif = False, expe_ev.MOTIF_INTERNE
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
                    ip=ip,
                    meta={"email": ctx} if ctx in expe_ev.CONTEXTES else None,
                    dedup_secondes=expe_ev.DEDUP_SECONDES,
                )
                conn.commit()
    except Exception as exc:
        logger.warning("pixel_ouverture_email_expe: %s", exc)

    return Response(content=_PIXEL_GIF, media_type="image/gif", headers=_PIXEL_HEADERS)

