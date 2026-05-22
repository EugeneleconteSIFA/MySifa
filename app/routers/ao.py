"""MySifa — MyAO (appels d'offre) — API interne.

Routes : /api/ao/*
Rôles : superadmin, direction, administration
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.services.audit_service import log_action
from app.services.email_service import email_invitation_ao, send_email
from app.services.path_safety import path_is_under_directory
from app.services.auth_service import get_current_user
from config import (
    BASE_URL,
    ROLE_ADMINISTRATION,
    ROLE_DIRECTION,
    ROLE_SUPERADMIN,
    UPLOAD_DIR,
)
from database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ao", tags=["ao"])

_PARIS = ZoneInfo("Europe/Paris")
_AO_ROLES = frozenset({
    ROLE_SUPERADMIN,
    ROLE_DIRECTION,
    ROLE_ADMINISTRATION,
})


def _now_paris_iso() -> str:
    return datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")


def _row_dict(row) -> dict:
    return dict(row) if row else {}


def _require_ao(request: Request) -> dict:
    user = get_current_user(request)
    if user.get("role") not in _AO_ROLES:
        raise HTTPException(status_code=403, detail="Accès réservé au module Appels d'offre")
    return user


def _get_ao_or_404(conn, ao_id: int) -> dict:
    row = conn.execute("SELECT * FROM ao_demandes WHERE id=?", (ao_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Appel d'offre introuvable")
    return _row_dict(row)


def _require_brouillon(ao: dict) -> None:
    if ao.get("statut") != "brouillon":
        raise HTTPException(
            status_code=400,
            detail="Modification impossible — l'appel d'offre n'est plus en brouillon.",
        )


def _gen_reference(conn) -> str:
    year = datetime.now(_PARIS).year
    prefix = f"AO-{year}-"
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM ao_demandes WHERE reference LIKE ?",
        (f"{prefix}%",),
    ).fetchone()
    seq = int(row["n"]) + 1
    for _ in range(100):
        ref = f"{prefix}{seq:03d}"
        if not conn.execute(
            "SELECT 1 FROM ao_demandes WHERE reference=? LIMIT 1", (ref,)
        ).fetchone():
            return ref
        seq += 1
    raise HTTPException(status_code=500, detail="Impossible de générer une référence unique")


def _ao_upload_dir(ao_id: int) -> str:
    path = os.path.join(UPLOAD_DIR, "ao", str(ao_id))
    os.makedirs(path, exist_ok=True)
    return path


def _nb_reponses(conn, ao_id: int) -> int:
    row = conn.execute(
        """SELECT COUNT(*) AS n FROM ao_fournisseurs
           WHERE ao_id=? AND statut='repondu'""",
        (ao_id,),
    ).fetchone()
    return int(row["n"]) if row else 0


def _get_fourni_in_ao(conn, ao_id: int, fourni_id: int) -> dict:
    row = conn.execute(
        "SELECT * FROM ao_fournisseurs WHERE id=? AND ao_id=?",
        (fourni_id, ao_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Fournisseur introuvable")
    return _row_dict(row)


def _pj_file_path(ao_id: int, stored_name: str) -> str:
    return os.path.join(_ao_upload_dir(ao_id), stored_name)


# ─── Liste et création ───────────────────────────────────────────

@router.get("")
def list_ao(request: Request):
    _require_ao(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT d.id, d.reference, d.titre, d.statut, d.date_creation, d.date_limite,
                      (SELECT COUNT(*) FROM ao_fournisseurs f WHERE f.ao_id = d.id) AS nb_fournisseurs,
                      (SELECT COUNT(*) FROM ao_fournisseurs f WHERE f.ao_id = d.id AND f.statut = 'repondu') AS nb_reponses
               FROM ao_demandes d
               ORDER BY d.date_creation DESC"""
        ).fetchall()
    return [_row_dict(r) for r in rows]


@router.post("")
async def create_ao(request: Request):
    user = _require_ao(request)
    body = await request.json()
    titre = (body.get("titre") or "").strip()
    if not titre:
        raise HTTPException(status_code=400, detail="Titre obligatoire.")
    description = (body.get("description") or "").strip() or None
    date_limite = (body.get("date_limite") or "").strip() or None
    responsable_email = (body.get("responsable_email") or "").strip() or None
    now = _now_paris_iso()

    with get_db() as conn:
        reference = _gen_reference(conn)
        cur = conn.execute(
            """INSERT INTO ao_demandes
               (reference, titre, description, date_creation, date_limite, statut, created_by, responsable_email)
               VALUES (?,?,?,?,?,'brouillon',?,?)""",
            (
                reference,
                titre,
                description,
                now,
                date_limite,
                user.get("id"),
                responsable_email,
            ),
        )
        ao_id = cur.lastrowid
        conn.commit()
        ao = _get_ao_or_404(conn, ao_id)

    log_action(
        user=user,
        action="CREATE",
        module="ao",
        objet=f"AO {reference}",
        ip=request.client.host if request.client else None,
    )
    return ao


# ─── Détail ──────────────────────────────────────────────────────

@router.get("/{ao_id}")
def get_ao(request: Request, ao_id: int):
    _require_ao(request)
    with get_db() as conn:
        ao = _get_ao_or_404(conn, ao_id)
        lignes = conn.execute(
            "SELECT * FROM ao_lignes WHERE ao_id=? ORDER BY position, id",
            (ao_id,),
        ).fetchall()
        fournisseurs = conn.execute(
            "SELECT * FROM ao_fournisseurs WHERE ao_id=? ORDER BY nom_fournisseur",
            (ao_id,),
        ).fetchall()
        nb_reponses = _nb_reponses(conn, ao_id)
    return {
        "ao": ao,
        "lignes": [_row_dict(r) for r in lignes],
        "fournisseurs": [_row_dict(r) for r in fournisseurs],
        "nb_reponses": nb_reponses,
    }


@router.put("/{ao_id}")
async def update_ao(request: Request, ao_id: int):
    _require_ao(request)
    body = await request.json()
    with get_db() as conn:
        ao = _get_ao_or_404(conn, ao_id)
        _require_brouillon(ao)
        titre = (body.get("titre") or ao.get("titre") or "").strip()
        if not titre:
            raise HTTPException(status_code=400, detail="Titre obligatoire.")
        conn.execute(
            """UPDATE ao_demandes
               SET titre=?, description=?, date_limite=?, responsable_email=?
               WHERE id=?""",
            (
                titre,
                (body.get("description") or "").strip() or None,
                (body.get("date_limite") or "").strip() or None,
                (body.get("responsable_email") or "").strip() or None,
                ao_id,
            ),
        )
        conn.commit()
        updated = _get_ao_or_404(conn, ao_id)
    return updated


@router.patch("/{ao_id}/cloturer")
def cloturer_ao(request: Request, ao_id: int):
    _require_ao(request)
    with get_db() as conn:
        ao = _get_ao_or_404(conn, ao_id)
        if ao.get("statut") != "envoyee":
            raise HTTPException(
                status_code=400,
                detail="Clôture impossible — l'appel d'offre doit être au statut « envoyée ».",
            )
        conn.execute(
            "UPDATE ao_demandes SET statut='cloturee' WHERE id=?",
            (ao_id,),
        )
        conn.commit()
        updated = _get_ao_or_404(conn, ao_id)
    return updated


# ─── Lignes ──────────────────────────────────────────────────────

@router.post("/{ao_id}/lignes")
async def add_ligne(request: Request, ao_id: int):
    _require_ao(request)
    body = await request.json()
    ref_produit = (body.get("ref_produit") or "").strip()
    designation = (body.get("designation") or "").strip()
    if not ref_produit or not designation:
        raise HTTPException(status_code=400, detail="Référence produit et désignation obligatoires.")
    try:
        quantite = float(body.get("quantite"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Quantité invalide.")
    if quantite <= 0:
        raise HTTPException(status_code=400, detail="Quantité invalide.")
    unite = (body.get("unite") or "unité").strip() or "unité"
    notes = (body.get("notes") or "").strip() or None

    with get_db() as conn:
        ao = _get_ao_or_404(conn, ao_id)
        _require_brouillon(ao)
        row = conn.execute(
            "SELECT COALESCE(MAX(position), -1) AS m FROM ao_lignes WHERE ao_id=?",
            (ao_id,),
        ).fetchone()
        position = int(row["m"]) + 1
        cur = conn.execute(
            """INSERT INTO ao_lignes
               (ao_id, ref_produit, designation, quantite, unite, notes, position)
               VALUES (?,?,?,?,?,?,?)""",
            (ao_id, ref_produit, designation, quantite, unite, notes, position),
        )
        conn.commit()
        ligne = conn.execute(
            "SELECT * FROM ao_lignes WHERE id=?", (cur.lastrowid,)
        ).fetchone()
    return _row_dict(ligne)


@router.put("/{ao_id}/lignes/{ligne_id}")
async def update_ligne(request: Request, ao_id: int, ligne_id: int):
    _require_ao(request)
    body = await request.json()
    ref_produit = (body.get("ref_produit") or "").strip()
    designation = (body.get("designation") or "").strip()
    if not ref_produit or not designation:
        raise HTTPException(status_code=400, detail="Référence produit et désignation obligatoires.")
    try:
        quantite = float(body.get("quantite"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Quantité invalide.")
    if quantite <= 0:
        raise HTTPException(status_code=400, detail="Quantité invalide.")
    unite = (body.get("unite") or "unité").strip() or "unité"
    notes = (body.get("notes") or "").strip() or None

    with get_db() as conn:
        ao = _get_ao_or_404(conn, ao_id)
        _require_brouillon(ao)
        existing = conn.execute(
            "SELECT id FROM ao_lignes WHERE id=? AND ao_id=?",
            (ligne_id, ao_id),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Ligne introuvable")
        conn.execute(
            """UPDATE ao_lignes
               SET ref_produit=?, designation=?, quantite=?, unite=?, notes=?
               WHERE id=? AND ao_id=?""",
            (ref_produit, designation, quantite, unite, notes, ligne_id, ao_id),
        )
        conn.commit()
        ligne = conn.execute(
            "SELECT * FROM ao_lignes WHERE id=?", (ligne_id,)
        ).fetchone()
    return _row_dict(ligne)


@router.delete("/{ao_id}/lignes/{ligne_id}")
def delete_ligne(request: Request, ao_id: int, ligne_id: int):
    _require_ao(request)
    with get_db() as conn:
        ao = _get_ao_or_404(conn, ao_id)
        _require_brouillon(ao)
        cur = conn.execute(
            "DELETE FROM ao_lignes WHERE id=? AND ao_id=?",
            (ligne_id, ao_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Ligne introuvable")
        conn.commit()
    return {"ok": True}


# ─── Fournisseurs ──────────────────────────────────────────────────

@router.post("/{ao_id}/fournisseurs")
async def add_fournisseur(request: Request, ao_id: int):
    _require_ao(request)
    body = await request.json()
    nom = (body.get("nom_fournisseur") or "").strip()
    email = (body.get("email_contact") or "").strip().lower()
    if not nom or not email:
        raise HTTPException(status_code=400, detail="Nom et email du fournisseur obligatoires.")

    token = str(uuid.uuid4())
    with get_db() as conn:
        _get_ao_or_404(conn, ao_id)
        cur = conn.execute(
            """INSERT INTO ao_fournisseurs
               (ao_id, nom_fournisseur, email_contact, token, statut)
               VALUES (?,?,?,?,'invite')""",
            (ao_id, nom, email, token),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM ao_fournisseurs WHERE id=?", (cur.lastrowid,)
        ).fetchone()
    return _row_dict(row)


@router.delete("/{ao_id}/fournisseurs/{fourni_id}")
def delete_fournisseur(request: Request, ao_id: int, fourni_id: int):
    _require_ao(request)
    with get_db() as conn:
        fourni = _get_fourni_in_ao(conn, ao_id, fourni_id)
        if fourni.get("statut") == "repondu":
            raise HTTPException(
                status_code=400,
                detail="Suppression impossible — ce fournisseur a déjà soumis une réponse.",
            )
        conn.execute(
            "DELETE FROM ao_fournisseurs WHERE id=? AND ao_id=?",
            (fourni_id, ao_id),
        )
        conn.commit()
    return {"ok": True}


# ─── Envoi ───────────────────────────────────────────────────────

@router.post("/{ao_id}/envoyer")
def envoyer_ao(request: Request, ao_id: int):
    _require_ao(request)
    now = _now_paris_iso()
    envoyes = 0
    erreurs = 0

    with get_db() as conn:
        ao = _get_ao_or_404(conn, ao_id)
        if ao.get("statut") == "cloturee":
            raise HTTPException(
                status_code=400,
                detail="Envoi impossible — l'appel d'offre est clôturé.",
            )
        lignes = [
            _row_dict(r)
            for r in conn.execute(
                "SELECT ref_produit, designation, quantite, unite FROM ao_lignes WHERE ao_id=? ORDER BY position, id",
                (ao_id,),
            ).fetchall()
        ]
        fournisseurs = conn.execute(
            """SELECT * FROM ao_fournisseurs
               WHERE ao_id=? AND statut='invite' AND date_envoi IS NULL""",
            (ao_id,),
        ).fetchall()

        for row in fournisseurs:
            fourni = _row_dict(row)
            lien = f"{BASE_URL.rstrip('/')}/portail/ao/{fourni['token']}"
            subject, html_body = email_invitation_ao(ao, fourni, lien, lignes)
            ok = send_email(fourni["email_contact"], subject, html_body)
            if ok:
                conn.execute(
                    "UPDATE ao_fournisseurs SET date_envoi=? WHERE id=?",
                    (now, fourni["id"]),
                )
                envoyes += 1
            else:
                erreurs += 1
                logger.warning(
                    "Échec envoi invitation AO %s → %s",
                    ao.get("reference"),
                    fourni.get("email_contact"),
                )

        conn.execute(
            "UPDATE ao_demandes SET statut='envoyee' WHERE id=?",
            (ao_id,),
        )
        conn.commit()

    return {"envoyes": envoyes, "erreurs": erreurs}


# ─── Pièces jointes ───────────────────────────────────────────────

@router.post("/{ao_id}/pieces-jointes")
async def upload_piece_jointe(
    request: Request,
    ao_id: int,
    file: UploadFile = File(...),
):
    _require_ao(request)
    raw_name = file.filename or "fichier"
    ext = Path(raw_name).suffix.lower()
    stored_name = str(uuid.uuid4()) + ext
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide.")

    with get_db() as conn:
        _get_ao_or_404(conn, ao_id)
        dest_dir = _ao_upload_dir(ao_id)
        dest_path = os.path.join(dest_dir, stored_name)
        try:
            with open(dest_path, "wb") as out:
                out.write(content)
        except OSError:
            raise HTTPException(status_code=500, detail="Enregistrement du fichier impossible.")
        now = _now_paris_iso()
        cur = conn.execute(
            """INSERT INTO ao_pieces_jointes
               (ao_id, filename, stored_name, taille_octets, uploaded_by, date)
               VALUES (?,?,?,?,?,?)""",
            (ao_id, os.path.basename(raw_name), stored_name, len(content), "interne", now),
        )
        conn.commit()
        pj = conn.execute(
            "SELECT * FROM ao_pieces_jointes WHERE id=?", (cur.lastrowid,)
        ).fetchone()
    return _row_dict(pj)


@router.get("/{ao_id}/pieces-jointes")
def list_pieces_jointes(request: Request, ao_id: int):
    _require_ao(request)
    with get_db() as conn:
        _get_ao_or_404(conn, ao_id)
        rows = conn.execute(
            """SELECT * FROM ao_pieces_jointes
               WHERE ao_id=? AND ao_fournisseur_id IS NULL
               ORDER BY date DESC""",
            (ao_id,),
        ).fetchall()
    return [_row_dict(r) for r in rows]


@router.delete("/{ao_id}/pieces-jointes/{pj_id}")
def delete_piece_jointe(request: Request, ao_id: int, pj_id: int):
    _require_ao(request)
    with get_db() as conn:
        _get_ao_or_404(conn, ao_id)
        pj = conn.execute(
            """SELECT * FROM ao_pieces_jointes
               WHERE id=? AND ao_id=? AND ao_fournisseur_id IS NULL""",
            (pj_id, ao_id),
        ).fetchone()
        if not pj:
            raise HTTPException(status_code=404, detail="Pièce jointe introuvable")
        pj = _row_dict(pj)
        conn.execute("DELETE FROM ao_pieces_jointes WHERE id=?", (pj_id,))
        conn.commit()

    path = _pj_file_path(ao_id, pj["stored_name"])
    allowed_root = _ao_upload_dir(ao_id)
    if path_is_under_directory(path, allowed_root) and os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            logger.warning("Suppression fichier PJ impossible: %s", path)
    return {"ok": True}


@router.get("/{ao_id}/pieces-jointes/{pj_id}/download")
def download_piece_jointe(request: Request, ao_id: int, pj_id: int):
    _require_ao(request)
    with get_db() as conn:
        _get_ao_or_404(conn, ao_id)
        pj = conn.execute(
            """SELECT * FROM ao_pieces_jointes
               WHERE id=? AND ao_id=? AND ao_fournisseur_id IS NULL""",
            (pj_id, ao_id),
        ).fetchone()
        if not pj:
            raise HTTPException(status_code=404, detail="Pièce jointe introuvable")
        pj = _row_dict(pj)

    path = _pj_file_path(ao_id, pj["stored_name"])
    allowed_root = _ao_upload_dir(ao_id)
    if not path_is_under_directory(path, allowed_root) or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Fichier introuvable sur le disque")
    return FileResponse(path=path, filename=pj.get("filename") or pj["stored_name"])


# ─── Messagerie ───────────────────────────────────────────────────

@router.get("/{ao_id}/fournisseurs/{fourni_id}/messages")
def list_messages(request: Request, ao_id: int, fourni_id: int):
    _require_ao(request)
    with get_db() as conn:
        _get_ao_or_404(conn, ao_id)
        _get_fourni_in_ao(conn, ao_id, fourni_id)
        rows = conn.execute(
            """SELECT * FROM ao_messages
               WHERE ao_fournisseur_id=?
               ORDER BY date ASC""",
            (fourni_id,),
        ).fetchall()
        conn.execute(
            """UPDATE ao_messages SET lu=1
               WHERE ao_fournisseur_id=? AND expediteur='fournisseur' AND lu=0""",
            (fourni_id,),
        )
        conn.commit()
    return [_row_dict(r) for r in rows]


@router.post("/{ao_id}/fournisseurs/{fourni_id}/messages")
async def post_message(request: Request, ao_id: int, fourni_id: int):
    user = _require_ao(request)
    body = await request.json()
    message = (body.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message vide.")

    now = _now_paris_iso()
    auteur = (user.get("nom") or user.get("email") or "Interne").strip()

    with get_db() as conn:
        ao = _get_ao_or_404(conn, ao_id)
        fourni = _get_fourni_in_ao(conn, ao_id, fourni_id)
        conn.execute(
            """INSERT INTO ao_messages
               (ao_fournisseur_id, expediteur, auteur_nom, message, date, lu)
               VALUES (?,'interne',?,?,?,0)""",
            (fourni_id, auteur, message, now),
        )
        conn.commit()
        inserted = conn.execute(
            "SELECT * FROM ao_messages WHERE rowid=last_insert_rowid()"
        ).fetchone()

    reference = ao.get("reference") or ""
    lien = f"{BASE_URL.rstrip('/')}/portail/ao/{fourni['token']}"
    subject = f"[MySifa] Nouveau message — {reference}"
    corps_texte = (
        f"Vous avez reçu un message concernant l'appel d'offre {reference}.\n\n"
        f"{message}\n\n"
        f"Accéder à la demande : {lien}"
    )
    html_body = (
        "<div style=\"font-family:'Segoe UI',system-ui,sans-serif;font-size:14px;"
        "color:#0f172a;line-height:1.6;white-space:pre-wrap\">"
        f"{corps_texte.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}"
        "</div>"
    )
    send_email(fourni["email_contact"], subject, html_body)

    return _row_dict(inserted) if inserted else {"ok": True}


# ─── Comparaison ──────────────────────────────────────────────────

@router.get("/{ao_id}/comparaison")
def comparaison_ao(request: Request, ao_id: int):
    _require_ao(request)
    with get_db() as conn:
        _get_ao_or_404(conn, ao_id)
        lignes_rows = conn.execute(
            "SELECT * FROM ao_lignes WHERE ao_id=? ORDER BY position, id",
            (ao_id,),
        ).fetchall()
        fournisseurs = [
            _row_dict(r)
            for r in conn.execute(
                """SELECT id, nom_fournisseur, statut FROM ao_fournisseurs
                   WHERE ao_id=? ORDER BY nom_fournisseur""",
                (ao_id,),
            ).fetchall()
        ]

        lignes_out: list[dict[str, Any]] = []
        for ln_row in lignes_rows:
            ln = _row_dict(ln_row)
            reponses = [
                _row_dict(r)
                for r in conn.execute(
                    """SELECT f.id AS fourni_id, f.nom_fournisseur,
                              r.prix_unitaire, r.delai_jours, r.commentaire
                       FROM ao_reponses r
                       JOIN ao_fournisseurs f ON f.id = r.ao_fournisseur_id
                       WHERE r.ligne_id=?
                       ORDER BY f.nom_fournisseur""",
                    (ln["id"],),
                ).fetchall()
            ]
            prices = [
                float(r["prix_unitaire"])
                for r in reponses
                if r.get("prix_unitaire") is not None
            ]
            if prices:
                prix_min = min(prices)
                prix_max = max(prices)
                prix_moyen = sum(prices) / len(prices)
            else:
                prix_min = prix_max = prix_moyen = None
            lignes_out.append({
                "id": ln["id"],
                "ref_produit": ln["ref_produit"],
                "designation": ln["designation"],
                "quantite": ln["quantite"],
                "unite": ln.get("unite"),
                "reponses": reponses,
                "prix_min": prix_min,
                "prix_max": prix_max,
                "prix_moyen": prix_moyen,
            })

    return {"lignes": lignes_out, "fournisseurs": fournisseurs}
