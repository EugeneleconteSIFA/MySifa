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
from app.web.ao_portail_page import (
    get_mes_demandes_html,
    get_portail_404_html,
    get_portail_html,
)
from config import BASE_URL, UPLOAD_DIR
from database import get_db

logger = logging.getLogger(__name__)

router_html = APIRouter(tags=["ao_portail"])
router_api = APIRouter(prefix="/api/portail", tags=["ao_portail_api"])

_PORTAIL_HTML_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}

_PARIS = ZoneInfo("Europe/Paris")
_RATE_WINDOW_SEC = 3600
_RATE_MAX_INVALID = 10
_invalid_attempts: dict[str, list[float]] = {}


def _now_paris_iso() -> str:
    return datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")


def _parse_lang(request: Request) -> str:
    lang = (request.query_params.get("lang") or "fr").strip().lower()
    return lang if lang in ("fr", "en") else "fr"


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


def _ensure_auto_attached_fiches(conn, ao_id: int, ao_reference: str | None) -> None:
    """Rattrapage idempotent : génère les fiches PDF fournisseur manquantes.

    Appelé au premier accès au portail sur un AO envoyé. Skip complet si
    toutes les fiches sont déjà présentes.
    """
    import re
    # Références produit distinctes de l'AO
    refs = [
        (r["ref_produit"] or "").strip()
        for r in conn.execute(
            "SELECT DISTINCT ref_produit FROM ao_lignes WHERE ao_id=?",
            (ao_id,),
        ).fetchall()
    ]
    refs = [r for r in refs if r]
    if not refs:
        return
    # PJ déjà présentes
    existing = {
        r["filename"]
        for r in conn.execute(
            "SELECT filename FROM ao_pieces_jointes WHERE ao_id=?", (ao_id,)
        ).fetchall()
    }
    # Rien à faire si toutes les fiches sont là
    missing = []
    for ref in refs:
        ref_clean = re.sub(r"[^\w\-]+", "_", ref.split(" - ")[0])
        fname = f"fiche_fournisseur_{ref_clean}.pdf"
        if fname not in existing:
            missing.append(ref)
    if not missing:
        return
    # Import tardif pour éviter la dépendance circulaire
    from app.routers.ao import (
        _auto_attach_fournisseur_pdfs,
        _produits_by_ref_map,
    )
    produits_map = _produits_by_ref_map(conn)
    lignes_raw = [
        {"ref_produit": ref, "designation": "", "quantite": None, "unite": None}
        for ref in missing
    ]
    now = _now_paris_iso()
    _auto_attach_fournisseur_pdfs(conn, ao_id, ao_reference, lignes_raw, produits_map, now)
    conn.commit()


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


def _email_fourni(fourni: dict) -> str:
    return (fourni.get("email_contact") or "").strip().lower()


def _produit_ids_by_ref(conn, refs: list[str | None]) -> dict[str, int]:
    """Réf. produit (lower) → id ao_produits pour les liens fiche technique."""
    out: dict[str, int] = {}
    for raw in refs:
        ref = (raw or "").strip()
        if not ref:
            continue
        key = ref.lower()
        if key in out:
            continue
        row = conn.execute(
            "SELECT id FROM ao_produits WHERE LOWER(ref)=LOWER(?) LIMIT 1",
            (ref,),
        ).fetchone()
        if row:
            out[key] = int(row["id"])
    return out


def _list_demandes_fournisseur(
    conn, email: str, *, current_token: str | None = None
) -> list[dict[str, Any]]:
    """Toutes les invitations AO pour cet email (hors brouillons non envoyés)."""
    rows = conn.execute(
        """SELECT
               f.token,
               f.nom_fournisseur,
               f.statut AS fournisseur_statut,
               f.date_envoi,
               f.date_ouverture,
               f.date_reponse,
               d.id AS ao_id,
               d.reference,
               d.titre,
               d.description,
               d.date_limite,
               d.date_creation,
               d.statut AS ao_statut
           FROM ao_fournisseurs f
           JOIN ao_demandes d ON d.id = f.ao_id
           WHERE LOWER(TRIM(COALESCE(f.email_contact, ''))) = LOWER(TRIM(COALESCE(?, '')))
             AND (
               d.statut IN ('envoyee', 'cloturee')
               OR f.date_envoi IS NOT NULL
             )
           ORDER BY COALESCE(f.date_envoi, d.date_creation) DESC, f.id DESC
           LIMIT 200""",
        (email,),
    ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        item = _row_dict(r)
        item["is_current"] = bool(
            current_token and item.get("token") == current_token
        )
        out.append(item)
    return out


def _portail_payload(conn, ao: dict, fourni: dict) -> dict[str, Any]:
    ao_id = int(ao["id"])
    fourni_id = int(fourni["id"])
    lignes_raw = conn.execute(
        """SELECT id, ref_produit, designation, quantite, unite, notes, position
           FROM ao_lignes WHERE ao_id=? ORDER BY position, id""",
        (ao_id,),
    ).fetchall()
    lignes = []
    ligne_ids: list[int] = []
    for r in lignes_raw:
        ln = _row_dict(r)
        ctx = _produit_ctx_for_ligne(conn, ln.get("ref_produit") or "")
        ln.update(ctx)
        ligne_ids.append(int(ln["id"]))
        lignes.append(ln)
    # Séries par ligne (portail fournisseur : lecture seule)
    series_by_ligne: dict[int, list[dict]] = {}
    if ligne_ids:
        qmarks = ",".join("?" * len(ligne_ids))
        for r in conn.execute(
            f"""SELECT id, ligne_id, position, libelle, quantite, notes
                FROM ao_lignes_series
                WHERE ligne_id IN ({qmarks})
                ORDER BY ligne_id, position, id""",
            tuple(ligne_ids),
        ).fetchall():
            d = _row_dict(r)
            series_by_ligne.setdefault(int(d["ligne_id"]), []).append(d)
    for ln in lignes:
        ln["series"] = series_by_ligne.get(int(ln["id"]), [])
    reponses = [
        _row_dict(r)
        for r in conn.execute(
            """SELECT ligne_id, serie_id, quotation, prix_unitaire, devise, unite_quotation,
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
                    headers=_PORTAIL_HTML_HEADERS,
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
        lang = _parse_lang(request)
        return HTMLResponse(
            get_portail_html(token, ao, fourni, lang=lang),
            headers=_PORTAIL_HTML_HEADERS,
        )
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
                headers=_PORTAIL_HTML_HEADERS,
            )
        raise


@router_html.get("/portail/ao/{token}/mes-demandes", response_class=HTMLResponse)
def portail_mes_demandes_page(request: Request, token: str):
    ip = _client_ip(request)
    try:
        with get_db() as conn:
            found = _lookup_token(conn, token, ip)
            if not found:
                return HTMLResponse(
                    content=get_portail_404_html(),
                    status_code=404,
                    headers=_PORTAIL_HTML_HEADERS,
                )
            _ao, fourni = found
            email = _email_fourni(fourni)
        lang = _parse_lang(request)
        return HTMLResponse(
            get_mes_demandes_html(
                token,
                email=email,
                nom_fournisseur=fourni.get("nom_fournisseur"),
                lang=lang,
            ),
            headers=_PORTAIL_HTML_HEADERS,
        )
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
                headers=_PORTAIL_HTML_HEADERS,
            )
        raise


# ─── API JSON ─────────────────────────────────────────────────────

@router_api.get("/ao/{token}/demandes")
def list_portail_demandes(request: Request, token: str):
    """Liste toutes les demandes de prix accessibles pour l'email du fournisseur."""
    ip = _client_ip(request)
    with get_db() as conn:
        _ao, fourni = _get_fourni_or_404(token, conn, ip=ip)
        email = _email_fourni(fourni)
        if not email:
            raise HTTPException(status_code=400, detail="Email fournisseur manquant.")
        demandes = _list_demandes_fournisseur(conn, email, current_token=token)
        return {
            "email": email,
            "nom_fournisseur": fourni.get("nom_fournisseur"),
            "demandes": demandes,
        }



def _translate_offre_texts(data: dict, target_lang: str, conn) -> dict:
    """Traduit les champs texte de l'offre selon target_lang (FR/EN/DE/...)."""
    if not data or not target_lang:
        return data
    tgt = (target_lang or "").strip().upper()
    if not tgt or tgt in ("FR", "FR-FR"):
        return data
    try:
        from app.services.translate_service import translate as _svc_translate
    except Exception:
        return data

    def _t(text):
        if not text or not str(text).strip():
            return text
        try:
            res = _svc_translate(conn, text=str(text), target_lang=tgt, source_lang="FR", formality="default")
            return res.get("translated") or text
        except Exception:
            return text

    ao = data.get("ao") if isinstance(data, dict) else None
    if isinstance(ao, dict):
        if ao.get("description"):
            ao["description"] = _t(ao["description"])
        if ao.get("titre"):
            ao["titre"] = _t(ao["titre"])
    lignes = data.get("lignes") if isinstance(data, dict) else []
    if isinstance(lignes, list):
        for ln in lignes:
            if not isinstance(ln, dict):
                continue
            if ln.get("notes"):
                ln["notes"] = _t(ln["notes"])
            if ln.get("designation"):
                ln["designation"] = _t(ln["designation"])
    return data


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
        # Rattrapage : si l'AO est envoyée et qu'il manque des fiches PDF
        # (AO envoyé avant l'auto-attach, ou produit ajouté au catalogue plus
        # tard), on les génère maintenant — idempotent.
        try:
            if ao.get("statut") == "envoyee":
                _ensure_auto_attached_fiches(conn, int(ao["id"]), ao.get("reference"))
        except Exception:
            logger.exception("Rattrapage fiches PDF portail échoué (AO %s)", ao.get("id"))
        payload = _portail_payload(conn, ao, fourni)
        # Traduction auto selon langue fournisseur
        try:
            _lang = (fourni.get("langue") if isinstance(fourni, dict) else None) or ""
        except Exception:
            _lang = ""
        payload = _translate_offre_texts(payload, _lang, conn)
        return payload


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
                    devise, unite_quotation, unite_quotation_original, unite_manuel,
                    delai_jours, commentaire)
                   VALUES (?,?,?,?,?,?,?,0,?,?)""",
                (
                    fourni_id,
                    ligne_id,
                    quotation,
                    quotation,
                    devise,
                    unite_q,
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
                """SELECT ligne_id, quotation, prix_unitaire, devise, unite_quotation,
                          delai_jours, commentaire
                   FROM ao_reponses WHERE ao_fournisseur_id=?""",
                (fourni_id,),
            ).fetchall()
        ]
        produits_by_ref = _produit_ids_by_ref(
            conn, [ln.get("ref_produit") for ln in lignes_db]
        )
        fourni = _row_dict(
            conn.execute(
                "SELECT * FROM ao_fournisseurs WHERE id=?", (fourni_id,)
            ).fetchone()
        )

    responsable = (ao.get("responsable_email") or "").strip()
    if responsable:
        subject, html_body = email_accuse_reception(
            ao,
            fourni,
            lignes_db,
            reponses_db,
            produits_by_ref=produits_by_ref,
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
        # Mark interne messages as read once fournisseur consulted them
        conn.execute(
            """UPDATE ao_messages SET lu=1
               WHERE ao_fournisseur_id=? AND expediteur='interne' AND lu=0""",
            (fourni["id"],),
        )
        conn.commit()
    return [_row_dict(r) for r in rows]


@router_api.get("/ao/{token}/counts")
def get_portail_counts(request: Request, token: str):
    """Retourne le nombre de messages interne non lus + documents non vus."""
    ip = _client_ip(request)
    with get_db() as conn:
        ao, fourni = _get_fourni_or_404(token, conn, ip=ip)
        msg = conn.execute(
            """SELECT COUNT(*) FROM ao_messages
               WHERE ao_fournisseur_id=? AND expediteur='interne' AND lu=0""",
            (fourni["id"],),
        ).fetchone()[0]
        try:
            docs = conn.execute(
                """SELECT COUNT(*) FROM ao_pieces_jointes
                   WHERE ao_id=? AND (ao_fournisseur_id IS NULL OR ao_fournisseur_id=?)
                     AND COALESCE(vu_par_fournisseur, 0)=0""",
                (ao["id"], fourni["id"]),
            ).fetchone()[0]
        except Exception:
            docs = 0
    return {"messages_non_lus": int(msg or 0), "documents_nouveaux": int(docs or 0)}


@router_api.post("/ao/{token}/documents/mark-viewed")
def portail_mark_docs_viewed(request: Request, token: str):
    """Marque tous les documents comme vus par le fournisseur."""
    ip = _client_ip(request)
    with get_db() as conn:
        ao, fourni = _get_fourni_or_404(token, conn, ip=ip)
        try:
            conn.execute(
                """UPDATE ao_pieces_jointes SET vu_par_fournisseur=1
                   WHERE ao_id=? AND (ao_fournisseur_id IS NULL OR ao_fournisseur_id=?)
                     AND COALESCE(vu_par_fournisseur, 0)=0""",
                (ao["id"], fourni["id"]),
            )
            conn.commit()
        except Exception:
            pass
    return {"ok": True}


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
