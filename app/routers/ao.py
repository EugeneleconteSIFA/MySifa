"""MySifa — MyAO (appels d'offre) — API interne.

Routes : /api/ao/*
Rôles : superadmin, direction
"""
from __future__ import annotations

import json
import logging
import sqlite3
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from app.services.audit_service import log_action
from app.services.email_service import email_invitation_ao, send_email
from app.services.path_safety import path_is_under_directory
from app.services.auth_service import get_current_user
from config import (
    BASE_URL,
    ROLE_DIRECTION,
    ROLE_SUPERADMIN,
    UPLOAD_DIR,
)
from app.services.ao_pricing import (
    DEVISES,
    UNITES_QUOTATION,
    enrich_reponse_pricing,
    get_eur_usd_rate,
    ligne_context_from_produit,
)
from app.services.ao_produit_fiche import (
    build_designation,
    default_fiche,
    normalize_fiche,
    parse_fiche,
    produit_row_to_api,
    render_fiche_html,
)
from database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ao", tags=["ao"])

_PARIS = ZoneInfo("Europe/Paris")
_AO_ROLES = frozenset({
    ROLE_SUPERADMIN,
    ROLE_DIRECTION,
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


# ─── Carnet fournisseurs (routes statiques avant /{ao_id}) ───────


def _parse_carnet_fournisseur_body(body: dict) -> tuple[str, str, str | None, str | None, str | None]:
    nom = (body.get("nom") or "").strip()
    if not nom:
        raise HTTPException(status_code=400, detail="Nom obligatoire.")
    email = (body.get("email") or "").strip().lower()
    societe = (body.get("societe") or "").strip() or None
    adresse = (body.get("adresse") or "").strip() or None
    notes = (body.get("notes") or "").strip() or None
    return nom, email, societe, adresse, notes


@router.get("/carnet-fournisseurs")
def list_carnet(request: Request):
    _require_ao(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM ao_carnet_fournisseurs ORDER BY COALESCE(societe, nom) COLLATE NOCASE, nom COLLATE NOCASE"
        ).fetchall()
    return [_row_dict(r) for r in rows]


@router.post("/carnet-fournisseurs")
async def create_carnet(request: Request):
    _require_ao(request)
    body = await request.json()
    nom, email, societe, adresse, notes = _parse_carnet_fournisseur_body(body)
    now = _now_paris_iso()
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO ao_carnet_fournisseurs
               (nom, email, societe, adresse, notes, created_at) VALUES (?,?,?,?,?,?)""",
            (nom, email, societe, adresse, notes, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM ao_carnet_fournisseurs WHERE id=?", (cur.lastrowid,)).fetchone()
    return _row_dict(row)


@router.put("/carnet-fournisseurs/{entry_id}")
async def update_carnet(request: Request, entry_id: int):
    _require_ao(request)
    body = await request.json()
    nom, email, societe, adresse, notes = _parse_carnet_fournisseur_body(body)
    with get_db() as conn:
        cur = conn.execute(
            """UPDATE ao_carnet_fournisseurs
               SET nom=?, email=?, societe=?, adresse=?, notes=? WHERE id=?""",
            (nom, email, societe, adresse, notes, entry_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Entrée introuvable")
        conn.commit()
        row = conn.execute("SELECT * FROM ao_carnet_fournisseurs WHERE id=?", (entry_id,)).fetchone()
    return _row_dict(row)


@router.delete("/carnet-fournisseurs/{entry_id}")
def delete_carnet(request: Request, entry_id: int):
    _require_ao(request)
    with get_db() as conn:
        cur = conn.execute("DELETE FROM ao_carnet_fournisseurs WHERE id=?", (entry_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Entrée introuvable")
        conn.commit()
    return {"ok": True}


# ─── Carnet clients (routes statiques avant /{ao_id}) ─────────────

@router.get("/carnet-clients")
def list_carnet_clients(request: Request):
    _require_ao(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM ao_carnet_clients ORDER BY nom COLLATE NOCASE"
        ).fetchall()
    return [_row_dict(r) for r in rows]


@router.post("/carnet-clients")
async def create_carnet_client(request: Request):
    _require_ao(request)
    body = await request.json()
    nom = (body.get("nom") or "").strip()
    if not nom:
        raise HTTPException(status_code=400, detail="Nom obligatoire.")
    email = (body.get("email") or "").strip().lower()
    pays = (body.get("pays") or "").strip() or None
    notes = (body.get("notes") or "").strip() or None
    now = _now_paris_iso()
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO ao_carnet_clients (nom, email, pays, notes, created_at) VALUES (?,?,?,?,?)",
            (nom, email, pays, notes, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM ao_carnet_clients WHERE id=?", (cur.lastrowid,)).fetchone()
    return _row_dict(row)


@router.put("/carnet-clients/{entry_id}")
async def update_carnet_client(request: Request, entry_id: int):
    _require_ao(request)
    body = await request.json()
    nom = (body.get("nom") or "").strip()
    if not nom:
        raise HTTPException(status_code=400, detail="Nom obligatoire.")
    email = (body.get("email") or "").strip().lower()
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE ao_carnet_clients SET nom=?, email=?, pays=?, notes=? WHERE id=?",
            (nom, email, (body.get("pays") or "").strip() or None,
             (body.get("notes") or "").strip() or None, entry_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Entrée introuvable")
        conn.commit()
        row = conn.execute("SELECT * FROM ao_carnet_clients WHERE id=?", (entry_id,)).fetchone()
    return _row_dict(row)


@router.delete("/carnet-clients/{entry_id}")
def delete_carnet_client(request: Request, entry_id: int):
    _require_ao(request)
    with get_db() as conn:
        cur = conn.execute("DELETE FROM ao_carnet_clients WHERE id=?", (entry_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Entrée introuvable")
        conn.commit()
    return {"ok": True}


# ─── Picker clients (depuis Paramètres > Clients) ────────────────

@router.get("/picker/clients")
def picker_clients(request: Request, search: str = "", limit: int = 50):
    """Recherche dans le référentiel clients (Paramètres > Clients).

    Renvoie max `limit` résultats. Si search est vide → renvoie les premiers.
    """
    _require_ao(request)
    with get_db() as conn:
        if search:
            like = f"%{search.strip()}%"
            rows = conn.execute(
                """SELECT id, code, raison_sociale, ville, pays, email, telephone
                   FROM clients
                   WHERE raison_sociale LIKE ? OR code LIKE ? OR ville LIKE ?
                      OR email LIKE ? OR CAST(numero AS TEXT) LIKE ?
                   ORDER BY raison_sociale COLLATE NOCASE
                   LIMIT ?""",
                (like, like, like, like, like, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, code, raison_sociale, ville, pays, email, telephone
                   FROM clients
                   ORDER BY raison_sociale COLLATE NOCASE
                   LIMIT ?""",
                (limit,),
            ).fetchall()
    return [_row_dict(r) for r in rows]


@router.post("/picker/clients")
async def picker_create_client(request: Request):
    """Création rapide d'un client depuis MyAO — alimente la même table que Paramètres."""
    user = _require_ao(request)
    body = await request.json()
    raison = (body.get("raison_sociale") or "").strip()
    if not raison:
        raise HTTPException(status_code=400, detail="Raison sociale obligatoire.")
    code = (body.get("code") or "").strip() or None
    now = _now_paris_iso()
    fields = {
        "numero": body.get("numero"),
        "code": code,
        "raison_sociale": raison,
        "adresse1": (body.get("adresse1") or "").strip() or None,
        "adresse2": (body.get("adresse2") or "").strip() or None,
        "cp": (body.get("cp") or "").strip() or None,
        "ville": (body.get("ville") or "").strip() or None,
        "pays": (body.get("pays") or "").strip() or None,
        "code_pays": (body.get("code_pays") or "").strip() or None,
        "siret": (body.get("siret") or "").strip() or None,
        "tva": (body.get("tva") or "").strip() or None,
        "telephone": (body.get("telephone") or "").strip() or None,
        "email": (body.get("email") or "").strip() or None,
        "contact_nom": (body.get("contact_nom") or "").strip() or None,
        "contact_fonction": (body.get("contact_fonction") or "").strip() or None,
        "contact_email": (body.get("contact_email") or "").strip() or None,
        "contact_tel": (body.get("contact_tel") or "").strip() or None,
        "representant": (body.get("representant") or "").strip() or None,
        "notes": (body.get("notes") or "").strip() or None,
        "etat": (body.get("etat") or "Normal").strip() or "Normal",
    }
    with get_db() as conn:
        if code:
            ex = conn.execute(
                "SELECT id FROM clients WHERE code=? COLLATE NOCASE", (code,)
            ).fetchone()
            if ex:
                raise HTTPException(409, f"Le code client « {code} » existe déjà.")
        cur = conn.execute(
            """INSERT INTO clients (
                numero, code, raison_sociale, adresse1, adresse2, cp, ville, pays, code_pays,
                siret, tva, telephone, email, contact_nom, contact_fonction, contact_email,
                contact_tel, representant, notes, etat, created_at, updated_at
              ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                fields["numero"], fields["code"], fields["raison_sociale"],
                fields["adresse1"], fields["adresse2"], fields["cp"], fields["ville"],
                fields["pays"], fields["code_pays"], fields["siret"], fields["tva"],
                fields["telephone"], fields["email"], fields["contact_nom"],
                fields["contact_fonction"], fields["contact_email"], fields["contact_tel"],
                fields["representant"], fields["notes"], fields["etat"], now, now,
            ),
        )
        conn.commit()
        new_id = cur.lastrowid
        row = conn.execute(
            "SELECT id, code, raison_sociale, ville, pays, email, telephone FROM clients WHERE id=?",
            (new_id,),
        ).fetchone()
    log_action(
        user=user, action="CREATE", module="ao",
        objet=f"Client (depuis MyAO) · {raison}",
        ip=request.client.host if request.client else None,
    )
    return _row_dict(row)


# ─── Picker fournisseurs (depuis Paramètres > Fournisseurs) ──────

@router.get("/picker/fournisseurs")
def picker_fournisseurs(request: Request, search: str = ""):
    """Liste des fournisseurs (table fournisseurs_fsc, identique Paramètres > Fournisseurs)."""
    _require_ao(request)
    with get_db() as conn:
        if search:
            like = f"%{search.strip()}%"
            rows = conn.execute(
                """SELECT id, nom, licence, certificat
                   FROM fournisseurs_fsc
                   WHERE nom LIKE ? OR licence LIKE ? OR certificat LIKE ?
                   ORDER BY nom COLLATE NOCASE""",
                (like, like, like),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, nom, licence, certificat
                   FROM fournisseurs_fsc
                   ORDER BY nom COLLATE NOCASE"""
            ).fetchall()
    return [_row_dict(r) for r in rows]


@router.post("/picker/fournisseurs")
async def picker_create_fournisseur(request: Request):
    """Création rapide d'un fournisseur depuis MyAO."""
    user = _require_ao(request)
    body = await request.json()
    nom = (body.get("nom") or "").strip()
    if not nom:
        raise HTTPException(status_code=400, detail="Nom du fournisseur obligatoire.")
    licence = (body.get("licence") or "").strip() or None
    certificat = (body.get("certificat") or "").strip() or None
    with get_db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO fournisseurs_fsc (nom, licence, certificat) VALUES (?,?,?)",
                (nom, licence, certificat),
            )
            conn.commit()
            new_id = cur.lastrowid
        except Exception:
            raise HTTPException(409, "Ce fournisseur existe déjà.")
        row = conn.execute(
            "SELECT id, nom, licence, certificat FROM fournisseurs_fsc WHERE id=?",
            (new_id,),
        ).fetchone()
    log_action(
        user=user, action="CREATE", module="ao",
        objet=f"Fournisseur (depuis MyAO) · {nom}",
        ip=request.client.host if request.client else None,
    )
    return _row_dict(row)


# ─── Matières premières (lecture pour fiches produit) ─────────────

_MP_AO_CATEGORIES = frozenset({
    "frontal", "adhesif", "glassine", "carton", "palette", "mandrin",
})


def _load_matieres_map(conn, ids: set[int] | None = None) -> dict[int, dict]:
    if ids:
        placeholders = ",".join("?" * len(ids))
        rows = conn.execute(
            f"""SELECT id, categorie, reference, designation, couleur
                FROM matieres_premieres WHERE id IN ({placeholders}) AND actif=1""",
            tuple(ids),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT id, categorie, reference, designation, couleur
               FROM matieres_premieres WHERE actif=1
               ORDER BY categorie, reference"""
        ).fetchall()
    return {int(r["id"]): _row_dict(r) for r in rows}


@router.get("/matieres")
def list_matieres_ao(
    request: Request,
    categorie: str | None = Query(None),
):
    _require_ao(request)
    cat = (categorie or "").strip().lower()
    with get_db() as conn:
        if cat:
            if cat not in _MP_AO_CATEGORIES:
                raise HTTPException(status_code=400, detail="Catégorie invalide.")
            rows = conn.execute(
                """SELECT id, categorie, reference, designation, couleur
                   FROM matieres_premieres
                   WHERE actif=1 AND categorie=?
                   ORDER BY reference COLLATE NOCASE""",
                (cat,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, categorie, reference, designation, couleur
                   FROM matieres_premieres
                   WHERE actif=1 AND categorie IN (
                     'frontal','adhesif','glassine','carton','palette','mandrin'
                   )
                   ORDER BY categorie, reference COLLATE NOCASE"""
            ).fetchall()
    return [_row_dict(r) for r in rows]


def _client_nom(conn, client_id: int | None) -> str | None:
    """Renvoie la raison sociale d'un client depuis le référentiel Paramètres > Clients.

    Fallback sur l'ancienne table ao_carnet_clients si l'id n'existe pas dans la
    nouvelle table — pour ne pas casser les fiches produit déjà liées.
    """
    if not client_id:
        return None
    row = conn.execute(
        "SELECT raison_sociale FROM clients WHERE id=?", (client_id,)
    ).fetchone()
    if row:
        return row["raison_sociale"]
    legacy = conn.execute(
        "SELECT nom FROM ao_carnet_clients WHERE id=?", (client_id,)
    ).fetchone()
    return legacy["nom"] if legacy else None


def _produits_by_ref_map(conn) -> dict[str, dict]:
    # On joint d'abord sur la nouvelle table clients (Paramètres > Clients),
    # puis on prend la valeur legacy ao_carnet_clients si la première ligne est NULL.
    rows = conn.execute(
        """SELECT p.*,
                  COALESCE(c.raison_sociale, lc.nom) AS client_nom
           FROM ao_produits p
           LEFT JOIN clients c            ON c.id  = p.client_id
           LEFT JOIN ao_carnet_clients lc ON lc.id = p.client_id"""
    ).fetchall()
    out: dict[str, dict] = {}
    for row in rows:
        d = _row_dict(row)
        ref_key = (d.get("ref") or "").strip().lower()
        if ref_key and ref_key not in out:
            out[ref_key] = _serialize_produit_row(d, conn)
    return out


def _matiere_ids_from_produits(produits: dict[str, dict]) -> set[int]:
    ids: set[int] = set()
    for p in produits.values():
        fiche = p.get("fiche") or parse_fiche(p.get("fiche_json"))
        mat = fiche.get("matiere") or {}
        for key in ("frontal_id", "adhesif_id", "glassine_id"):
            try:
                mid = mat.get(key)
                if mid is not None:
                    ids.add(int(mid))
            except (TypeError, ValueError):
                pass
    return ids


def _produit_ref_taken(conn, ref: str, exclude_id: int | None = None) -> bool:
    ref = (ref or "").strip()
    if not ref:
        return False
    if exclude_id is not None:
        row = conn.execute(
            "SELECT 1 FROM ao_produits WHERE LOWER(ref)=LOWER(?) AND id<>? LIMIT 1",
            (ref, exclude_id),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT 1 FROM ao_produits WHERE LOWER(ref)=LOWER(?) LIMIT 1",
            (ref,),
        ).fetchone()
    return row is not None


def _produit_from_body(body: dict, conn) -> tuple[str, str, str, str | None, int | None, str]:
    ref = (body.get("ref") or "").strip()
    if not ref:
        raise HTTPException(status_code=400, detail="Référence produit obligatoire.")
    if isinstance(body.get("fiche"), dict):
        fiche = parse_fiche(json.dumps(body["fiche"], ensure_ascii=False))
    elif isinstance(body.get("fiche_json"), str):
        fiche = parse_fiche(body["fiche_json"])
    else:
        fiche = default_fiche()
    fiche = normalize_fiche(fiche)
    client_id = body.get("client_id")
    try:
        client_id = int(client_id) if client_id not in (None, "") else None
    except (TypeError, ValueError):
        client_id = None
    client_nom = _client_nom(conn, client_id)
    type_produit = (fiche.get("type_produit") or "rouleau").strip()
    designation = (body.get("designation") or "").strip()
    if not designation:
        designation = build_designation(ref, client_nom, type_produit)
    unite = (body.get("unite") or "unité").strip() or "unité"
    notes = (body.get("notes") or "").strip() or None
    fiche_json = json.dumps(fiche, ensure_ascii=False)
    return ref, designation, unite, notes, client_id, fiche_json


def _serialize_produit_row(row: dict, conn) -> dict:
    client_nom = row.get("client_nom") or _client_nom(conn, row.get("client_id"))
    return produit_row_to_api(row, client_nom)


# ─── Catalogue produits (routes statiques avant /{ao_id}) ─────────

@router.get("/produits")
def list_produits(request: Request):
    _require_ao(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT p.*, c.nom AS client_nom
               FROM ao_produits p
               LEFT JOIN ao_carnet_clients c ON c.id = p.client_id
               ORDER BY p.ref COLLATE NOCASE"""
        ).fetchall()
    return [_serialize_produit_row(_row_dict(r), conn) for r in rows]


@router.get("/produits/{produit_id}")
def get_produit(request: Request, produit_id: int):
    _require_ao(request)
    with get_db() as conn:
        row = conn.execute(
            """SELECT p.*, c.nom AS client_nom
               FROM ao_produits p
               LEFT JOIN ao_carnet_clients c ON c.id = p.client_id
               WHERE p.id=?""",
            (produit_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Produit introuvable")
    return _serialize_produit_row(_row_dict(row), conn)


@router.get("/produits/{produit_id}/export")
def export_produit_fiche(request: Request, produit_id: int):
    _require_ao(request)
    with get_db() as conn:
        row = conn.execute(
            """SELECT p.*, c.nom AS client_nom
               FROM ao_produits p
               LEFT JOIN ao_carnet_clients c ON c.id = p.client_id
               WHERE p.id=?""",
            (produit_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Produit introuvable")
        produit = _serialize_produit_row(_row_dict(row), conn)
        fiche = produit.get("fiche") or {}
        ids: set[int] = set()
        mat = fiche.get("matiere") or {}
        for key in ("frontal_id", "adhesif_id", "glassine_id"):
            if mat.get(key):
                ids.add(int(mat[key]))
        cond = fiche.get("conditionnement") or {}
        for block in (cond.get("carton") or {}, cond.get("palette") or {}):
            if block.get("matiere_id"):
                ids.add(int(block["matiere_id"]))
        mp_map = _load_matieres_map(conn, ids) if ids else {}
    html = render_fiche_html(produit, client_nom=produit.get("client_nom"), matieres_map=mp_map)
    return HTMLResponse(content=html)


@router.post("/produits")
async def create_produit(request: Request):
    _require_ao(request)
    body = await request.json()
    now = _now_paris_iso()
    with get_db() as conn:
        ref, designation, unite, notes, client_id, fiche_json = _produit_from_body(body, conn)
        if _produit_ref_taken(conn, ref):
            raise HTTPException(status_code=400, detail="Référence déjà utilisée.")
        try:
            cur = conn.execute(
                """INSERT INTO ao_produits
                   (ref, designation, unite, notes, client_id, fiche_json, created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (ref, designation, unite, notes, client_id, fiche_json, now),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            raise HTTPException(status_code=400, detail="Référence déjà utilisée.") from None
        row = conn.execute("SELECT * FROM ao_produits WHERE id=?", (cur.lastrowid,)).fetchone()
    return _serialize_produit_row(_row_dict(row), conn)


@router.put("/produits/{produit_id}")
async def update_produit(request: Request, produit_id: int):
    _require_ao(request)
    body = await request.json()
    with get_db() as conn:
        ref, designation, unite, notes, client_id, fiche_json = _produit_from_body(body, conn)
        if _produit_ref_taken(conn, ref, exclude_id=produit_id):
            raise HTTPException(status_code=400, detail="Référence déjà utilisée.")
        try:
            cur = conn.execute(
                """UPDATE ao_produits
                   SET ref=?, designation=?, unite=?, notes=?, client_id=?, fiche_json=?
                   WHERE id=?""",
                (ref, designation, unite, notes, client_id, fiche_json, produit_id),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Produit introuvable")
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            raise HTTPException(status_code=400, detail="Référence déjà utilisée.") from None
        row = conn.execute("SELECT * FROM ao_produits WHERE id=?", (produit_id,)).fetchone()
    return _serialize_produit_row(_row_dict(row), conn)


@router.delete("/produits/{produit_id}")
def delete_produit(request: Request, produit_id: int):
    _require_ao(request)
    with get_db() as conn:
        cur = conn.execute("DELETE FROM ao_produits WHERE id=?", (produit_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Produit introuvable")
        conn.commit()
    return {"ok": True}


# ─── Détail ──────────────────────────────────────────────────────

def _enrich_ligne_display(
    ln: dict,
    produits_map: dict[str, dict],
    matieres_map: dict[int, dict],
) -> dict:
    """Ajoute client et étiq./bobine depuis le catalogue produit (fiche)."""
    ref_key = (ln.get("ref_produit") or "").strip().lower()
    produit = produits_map.get(ref_key)
    ctx = ligne_context_from_produit(
        ln.get("ref_produit") or "",
        ln.get("quantite"),
        produit,
        matieres_map,
    )
    ln["client_nom"] = ctx.get("client_nom")
    ln["etiquettes_par_bobine"] = ctx.get("etiquettes_par_bobine")
    return ln


@router.get("/{ao_id}/voisins")
def get_ao_voisins(request: Request, ao_id: int):
    """Renvoie l'AO précédent et suivant dans l'ordre antichronologique
    (mêmes critères que GET /api/ao : ORDER BY date_creation DESC)."""
    _require_ao(request)
    with get_db() as conn:
        _get_ao_or_404(conn, ao_id)
        rows = conn.execute(
            """SELECT id, reference, titre FROM ao_demandes
               ORDER BY date_creation DESC, id DESC"""
        ).fetchall()
    triples = [(int(r["id"]), r["reference"], r["titre"]) for r in rows]
    pos = next((i for i, t in enumerate(triples) if t[0] == ao_id), None)
    if pos is None:
        raise HTTPException(404, "Appel d'offre introuvable")
    prev_ao = None
    next_ao = None
    if pos > 0:
        p = triples[pos - 1]
        prev_ao = {"id": p[0], "reference": p[1], "titre": p[2]}
    if pos < len(triples) - 1:
        n = triples[pos + 1]
        next_ao = {"id": n[0], "reference": n[1], "titre": n[2]}
    return {
        "position": pos + 1,
        "total": len(triples),
        "prev": prev_ao,
        "next": next_ao,
    }


@router.get("/{ao_id}")
def get_ao(request: Request, ao_id: int):
    _require_ao(request)
    with get_db() as conn:
        ao = _get_ao_or_404(conn, ao_id)
        lignes_rows = conn.execute(
            "SELECT * FROM ao_lignes WHERE ao_id=? ORDER BY position, id",
            (ao_id,),
        ).fetchall()
        fournisseurs = conn.execute(
            "SELECT * FROM ao_fournisseurs WHERE ao_id=? ORDER BY nom_fournisseur",
            (ao_id,),
        ).fetchall()
        nb_reponses = _nb_reponses(conn, ao_id)
        produits_map = _produits_by_ref_map(conn)
        mat_ids = _matiere_ids_from_produits(produits_map)
        matieres_map = _load_matieres_map(conn, mat_ids or None)
        lignes = [
            _enrich_ligne_display(_row_dict(r), produits_map, matieres_map)
            for r in lignes_rows
        ]
    return {
        "ao": ao,
        "lignes": lignes,
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


@router.delete("/{ao_id}")
def delete_ao(request: Request, ao_id: int):
    """Suppression complète d'un appel d'offre (lignes, fournisseurs, réponses,
    messages, pièces jointes et fichiers sur disque)."""
    user = _require_ao(request)
    with get_db() as conn:
        ao = _get_ao_or_404(conn, ao_id)
        # Récupère les noms de fichiers PJ pour suppression disque
        pjs = conn.execute(
            "SELECT stored_name FROM ao_pieces_jointes WHERE ao_id=?",
            (ao_id,),
        ).fetchall()
        # Suppressions explicites (les FK CASCADE ne sont pas garanties — PRAGMA foreign_keys=OFF par défaut)
        fournis = conn.execute(
            "SELECT id FROM ao_fournisseurs WHERE ao_id=?", (ao_id,)
        ).fetchall()
        fourni_ids = [int(r["id"]) for r in fournis]
        if fourni_ids:
            qmarks = ",".join("?" * len(fourni_ids))
            conn.execute(
                f"DELETE FROM ao_messages WHERE ao_fournisseur_id IN ({qmarks})",
                fourni_ids,
            )
            conn.execute(
                f"DELETE FROM ao_reponses WHERE ao_fournisseur_id IN ({qmarks})",
                fourni_ids,
            )
        conn.execute("DELETE FROM ao_pieces_jointes WHERE ao_id=?", (ao_id,))
        conn.execute("DELETE FROM ao_fournisseurs WHERE ao_id=?", (ao_id,))
        conn.execute("DELETE FROM ao_lignes WHERE ao_id=?", (ao_id,))
        conn.execute("DELETE FROM ao_demandes WHERE id=?", (ao_id,))
        conn.commit()

    # Suppression des fichiers sur disque
    upload_dir = os.path.join(UPLOAD_DIR, "ao", str(ao_id))
    allowed_root = os.path.join(UPLOAD_DIR, "ao")
    for pj in pjs:
        try:
            stored = pj["stored_name"]
            path = os.path.join(upload_dir, stored)
            if path_is_under_directory(path, allowed_root) and os.path.isfile(path):
                os.remove(path)
        except OSError:
            logger.warning("Suppression fichier PJ impossible lors du delete AO %s", ao_id)
    try:
        if os.path.isdir(upload_dir) and path_is_under_directory(upload_dir, allowed_root):
            # Ne supprime que si vide pour éviter les surprises
            if not os.listdir(upload_dir):
                os.rmdir(upload_dir)
    except OSError:
        logger.warning("Suppression dossier upload impossible: %s", upload_dir)

    log_action(
        user=user,
        action="DELETE",
        module="ao",
        objet=f"AO {ao.get('reference')}",
        ip=request.client.host if request.client else None,
    )
    return {"ok": True}


@router.post("/{ao_id}/dupliquer")
async def dupliquer_ao(request: Request, ao_id: int):
    """Duplique un appel d'offre. Le nouveau AO est en statut 'brouillon'.

    Body JSON optionnel :
      - with_fournisseurs (bool, défaut True) : recopie les fournisseurs (sans réponses)
      - with_pieces_jointes (bool, défaut False) : recopie les documents joints
      - titre (str optionnel) : titre du nouvel AO (sinon : « <titre> (copie) »)
    """
    user = _require_ao(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    with_fournisseurs = bool(body.get("with_fournisseurs", True))
    with_pieces_jointes = bool(body.get("with_pieces_jointes", False))
    titre_override = (body.get("titre") or "").strip() or None
    now = _now_paris_iso()

    with get_db() as conn:
        src = _get_ao_or_404(conn, ao_id)
        default_titre = (src.get("titre") or "Appel d'offre") + " (copie)"
        new_titre = titre_override or default_titre
        new_ref = _gen_reference(conn)
        cur = conn.execute(
            """INSERT INTO ao_demandes
               (reference, titre, description, date_creation, date_limite, statut, created_by, responsable_email)
               VALUES (?,?,?,?,?,'brouillon',?,?)""",
            (
                new_ref,
                new_titre,
                src.get("description"),
                now,
                src.get("date_limite"),
                user.get("id"),
                src.get("responsable_email"),
            ),
        )
        new_id = cur.lastrowid

        # Copie des lignes
        src_lignes = conn.execute(
            "SELECT * FROM ao_lignes WHERE ao_id=? ORDER BY position, id",
            (ao_id,),
        ).fetchall()
        for ln in src_lignes:
            conn.execute(
                """INSERT INTO ao_lignes
                   (ao_id, ref_produit, designation, quantite, unite, notes, position)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    new_id,
                    ln["ref_produit"],
                    ln["designation"],
                    ln["quantite"],
                    ln["unite"],
                    ln["notes"],
                    ln["position"],
                ),
            )

        # Copie des fournisseurs (sans dates d'envoi / ouverture / réponse, nouveau token, statut='invite')
        if with_fournisseurs:
            src_fournis = conn.execute(
                "SELECT * FROM ao_fournisseurs WHERE ao_id=?",
                (ao_id,),
            ).fetchall()
            for f in src_fournis:
                conn.execute(
                    """INSERT INTO ao_fournisseurs
                       (ao_id, nom_fournisseur, email_contact, token, statut)
                       VALUES (?,?,?,?,'invite')""",
                    (
                        new_id,
                        f["nom_fournisseur"],
                        f["email_contact"],
                        str(uuid.uuid4()),
                    ),
                )

        conn.commit()
        new_ao = _get_ao_or_404(conn, new_id)

    # Copie optionnelle des pièces jointes (fichiers sur disque)
    if with_pieces_jointes:
        with get_db() as conn:
            src_pjs = conn.execute(
                """SELECT * FROM ao_pieces_jointes
                   WHERE ao_id=? AND ao_fournisseur_id IS NULL""",
                (ao_id,),
            ).fetchall()
            for pj in src_pjs:
                src_path = _pj_file_path(ao_id, pj["stored_name"])
                if not os.path.isfile(src_path):
                    continue
                ext = Path(pj["stored_name"]).suffix.lower()
                new_stored = str(uuid.uuid4()) + ext
                dest_path = os.path.join(_ao_upload_dir(new_id), new_stored)
                try:
                    with open(src_path, "rb") as fin, open(dest_path, "wb") as fout:
                        fout.write(fin.read())
                except OSError:
                    logger.warning("Copie PJ impossible lors de la duplication AO %s", ao_id)
                    continue
                conn.execute(
                    """INSERT INTO ao_pieces_jointes
                       (ao_id, filename, stored_name, taille_octets, uploaded_by, date)
                       VALUES (?,?,?,?,?,?)""",
                    (
                        new_id,
                        pj["filename"],
                        new_stored,
                        pj["taille_octets"],
                        pj["uploaded_by"],
                        _now_paris_iso(),
                    ),
                )
            conn.commit()

    log_action(
        user=user,
        action="DUPLICATE",
        module="ao",
        objet=f"AO {src.get('reference')} → {new_ref}",
        ip=request.client.host if request.client else None,
    )
    return new_ao


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
        produits_map = _produits_by_ref_map(conn)
        mat_ids = _matiere_ids_from_produits(produits_map)
        matieres_map = _load_matieres_map(conn, mat_ids or None)
        eur_usd = get_eur_usd_rate(conn)

        lignes_out: list[dict[str, Any]] = []
        rows_flat: list[dict[str, Any]] = []
        for ln_row in lignes_rows:
            ln = _row_dict(ln_row)
            ref_key = (ln.get("ref_produit") or "").strip().lower()
            produit = produits_map.get(ref_key)
            ctx = ligne_context_from_produit(
                ln.get("ref_produit") or "",
                ln.get("quantite"),
                produit,
                matieres_map,
            )
            reponses_raw = [
                _row_dict(r)
                for r in conn.execute(
                    """SELECT r.id AS reponse_id, f.id AS fourni_id, f.nom_fournisseur,
                              r.quotation, r.prix_unitaire, r.devise, r.unite_quotation,
                              r.coef, r.devise_prix_devis,
                              r.delai_jours, r.commentaire
                       FROM ao_reponses r
                       JOIN ao_fournisseurs f ON f.id = r.ao_fournisseur_id
                       WHERE r.ligne_id=?
                       ORDER BY f.nom_fournisseur""",
                    (ln["id"],),
                ).fetchall()
            ]
            rep_by_fourni = {int(r["fourni_id"]): r for r in reponses_raw}
            reponses = []
            for f in fournisseurs:
                raw = rep_by_fourni.get(int(f["id"]))
                if raw:
                    reponses.append(
                        enrich_reponse_pricing(raw, ctx, eur_usd_rate=eur_usd)
                    )
            prices_mille = [
                float(r["prix_au_mille"])
                for r in reponses
                if r.get("prix_au_mille") is not None
            ]
            if prices_mille:
                prix_min = min(prices_mille)
                prix_max = max(prices_mille)
                prix_moyen = sum(prices_mille) / len(prices_mille)
            else:
                prix_min = prix_max = prix_moyen = None
            ligne_out = {
                "id": ln["id"],
                "ref_produit": ln["ref_produit"],
                "designation": ln["designation"],
                "quantite": ln["quantite"],
                "unite": ln.get("unite"),
                **ctx,
                "reponses": reponses,
                "prix_min": prix_min,
                "prix_max": prix_max,
                "prix_moyen": prix_moyen,
            }
            lignes_out.append(ligne_out)
            for f in fournisseurs:
                fid = int(f["id"])
                raw = rep_by_fourni.get(fid)
                if raw:
                    rep = enrich_reponse_pricing(raw, ctx, eur_usd_rate=eur_usd)
                else:
                    rep = enrich_reponse_pricing(
                        {
                            "reponse_id": None,
                            "fourni_id": fid,
                            "nom_fournisseur": f.get("nom_fournisseur"),
                            "quotation": None,
                            "devise": "EUR",
                            "unite_quotation": "mille",
                            "coef": 1.0,
                            "devise_prix_devis": "EUR",
                        },
                        ctx,
                        eur_usd_rate=eur_usd,
                    )
                rows_flat.append({
                    "ligne_id": ln["id"],
                    "reponse_id": rep.get("reponse_id"),
                    "fourni_id": rep.get("fourni_id"),
                    "nom_fournisseur": rep.get("nom_fournisseur"),
                    **ctx,
                    **{k: rep.get(k) for k in (
                        "quotation", "devise", "unite_quotation",
                        "prix_calcule", "prix_au_mille", "coef",
                        "devise_prix_devis", "prix_vente",
                        "delai_jours", "commentaire",
                    )},
                })

    return {
        "lignes": lignes_out,
        "fournisseurs": fournisseurs,
        "rows": rows_flat,
        "eur_usd_rate": eur_usd,
    }


@router.patch("/{ao_id}/reponses/{reponse_id}")
async def patch_reponse_pricing(request: Request, ao_id: int, reponse_id: int):
    """Met à jour coef et devise du devis (saisie interne)."""
    _require_ao(request)
    body = await request.json()
    coef = body.get("coef")
    devise_prix_devis = body.get("devise_prix_devis")
    if coef is not None:
        try:
            coef = float(coef)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Coefficient invalide.")
        if coef <= 0:
            raise HTTPException(status_code=400, detail="Coefficient invalide.")
    if devise_prix_devis is not None:
        devise_prix_devis = (devise_prix_devis or "").strip().upper()
        if devise_prix_devis not in DEVISES:
            raise HTTPException(status_code=400, detail="Devise invalide.")

    with get_db() as conn:
        _get_ao_or_404(conn, ao_id)
        row = conn.execute(
            """SELECT r.*, l.ao_id, l.ref_produit, l.quantite
               FROM ao_reponses r
               JOIN ao_lignes l ON l.id = r.ligne_id
               WHERE r.id=? AND l.ao_id=?""",
            (reponse_id, ao_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Réponse introuvable")
        rep = _row_dict(row)
        if coef is not None:
            conn.execute(
                "UPDATE ao_reponses SET coef=? WHERE id=?",
                (coef, reponse_id),
            )
        if devise_prix_devis is not None:
            conn.execute(
                "UPDATE ao_reponses SET devise_prix_devis=? WHERE id=?",
                (devise_prix_devis, reponse_id),
            )
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM ao_reponses WHERE id=?", (reponse_id,)
        ).fetchone()
        rep_out = _row_dict(updated)
        fourni = conn.execute(
            "SELECT id, nom_fournisseur FROM ao_fournisseurs WHERE id=?",
            (rep_out["ao_fournisseur_id"],),
        ).fetchone()
        if fourni:
            rep_out["fourni_id"] = fourni["id"]
            rep_out["nom_fournisseur"] = fourni["nom_fournisseur"]
        produits_map = _produits_by_ref_map(conn)
        mat_ids = _matiere_ids_from_produits(produits_map)
        matieres_map = _load_matieres_map(conn, mat_ids or None)
        eur_usd = get_eur_usd_rate(conn)
        produit = produits_map.get((row["ref_produit"] or "").strip().lower())
        ctx = ligne_context_from_produit(
            row["ref_produit"], row["quantite"], produit, matieres_map
        )
        return enrich_reponse_pricing(rep_out, ctx, eur_usd_rate=eur_usd)


@router.get("/{ao_id}/non-lus")
def non_lus(request: Request, ao_id: int):
    """Retourne le nombre de messages fournisseur non lus, par fournisseur."""
    _require_ao(request)
    with get_db() as conn:
        _get_ao_or_404(conn, ao_id)
        rows = conn.execute(
            """SELECT ao_fournisseur_id, COUNT(*) AS n
               FROM ao_messages
               WHERE ao_fournisseur_id IN (
                 SELECT id FROM ao_fournisseurs WHERE ao_id=?
               ) AND expediteur='fournisseur' AND lu=0
               GROUP BY ao_fournisseur_id""",
            (ao_id,),
        ).fetchall()
    return {str(r["ao_fournisseur_id"]): int(r["n"]) for r in rows}
