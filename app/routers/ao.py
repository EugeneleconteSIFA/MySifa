"""MySifa — MyAO (appels d'offre) — API interne.

Routes : /api/ao/*
Rôles : superadmin, direction
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
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
                      (SELECT COUNT(*) FROM ao_fournisseurs f WHERE f.ao_id = d.id AND f.statut = 'repondu') AS nb_reponses,
                      (SELECT GROUP_CONCAT(DISTINCT l.ref_produit)
                         FROM ao_lignes l
                         WHERE l.ao_id = d.id
                           AND l.ref_produit IS NOT NULL AND l.ref_produit != '') AS refs_produits,
                      (SELECT GROUP_CONCAT(DISTINCT COALESCE(cg.raison_sociale, lc.nom))
                         FROM ao_lignes l
                         JOIN ao_produits p ON p.ref = l.ref_produit
                         LEFT JOIN clients            cg ON cg.id = p.client_id
                         LEFT JOIN ao_carnet_clients  lc ON lc.id = p.client_id
                         WHERE l.ao_id = d.id) AS clients,
                      COALESCE(d.prix_transport_pct, 0) AS prix_transport_pct
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


def _normalize_langue(value: object) -> str:
    """Normalise la langue : 'fr' ou 'en', défaut 'fr'."""
    v = (str(value or "").strip().lower())
    return "en" if v == "en" else "fr"


def _parse_carnet_fournisseur_body(body: dict) -> tuple[str, str, str | None, str | None, str | None, str]:
    nom = (body.get("nom") or "").strip()
    if not nom:
        raise HTTPException(status_code=400, detail="Nom obligatoire.")
    email = (body.get("email") or "").strip().lower()
    societe = (body.get("societe") or "").strip() or None
    adresse = (body.get("adresse") or "").strip() or None
    notes = (body.get("notes") or "").strip() or None
    langue = _normalize_langue(body.get("langue"))
    return nom, email, societe, adresse, notes, langue


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
    nom, email, societe, adresse, notes, langue = _parse_carnet_fournisseur_body(body)
    now = _now_paris_iso()
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO ao_carnet_fournisseurs
               (nom, email, societe, adresse, notes, langue, created_at) VALUES (?,?,?,?,?,?,?)""",
            (nom, email, societe, adresse, notes, langue, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM ao_carnet_fournisseurs WHERE id=?", (cur.lastrowid,)).fetchone()
    return _row_dict(row)


@router.put("/carnet-fournisseurs/{entry_id}")
async def update_carnet(request: Request, entry_id: int):
    _require_ao(request)
    body = await request.json()
    nom, email, societe, adresse, notes, langue = _parse_carnet_fournisseur_body(body)
    with get_db() as conn:
        cur = conn.execute(
            """UPDATE ao_carnet_fournisseurs
               SET nom=?, email=?, societe=?, adresse=?, notes=?, langue=? WHERE id=?""",
            (nom, email, societe, adresse, notes, langue, entry_id),
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




@router.get("/picker/fournisseurs-with-contacts")
def picker_fournisseurs_with_contacts(request: Request, search: str = ""):
    """Fournisseurs actifs + leurs contacts, pour le modal AO."""
    _require_ao(request)
    import json as _json
    with get_db() as conn:
        four_cols = {r[1] for r in conn.execute("PRAGMA table_info(fournisseurs_fsc)").fetchall()}
        actif_clause = "AND (actif IS NULL OR actif=1)" if "actif" in four_cols else ""
        select_extras = ""
        for extra in ("ville", "langue_default", "tags"):
            if extra in four_cols:
                select_extras += f", {extra}"
        if search:
            like = f"%{search.strip()}%"
            search_cols = ["nom"]
            if "ville" in four_cols: search_cols.append("ville")
            if "tags" in four_cols: search_cols.append("tags")
            where = " OR ".join(f"{c} LIKE ?" for c in search_cols)
            frows = conn.execute(
                f"SELECT id, nom, licence, has_fsc{select_extras} FROM fournisseurs_fsc "
                f"WHERE ({where}) {actif_clause} ORDER BY nom COLLATE NOCASE",
                tuple([like] * len(search_cols)),
            ).fetchall()
        else:
            frows = conn.execute(
                f"SELECT id, nom, licence, has_fsc{select_extras} FROM fournisseurs_fsc "
                f"WHERE 1=1 {actif_clause} ORDER BY nom COLLATE NOCASE"
            ).fetchall()

        has_contacts_table = bool(conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='fournisseur_contacts'"
        ).fetchone())
        contacts_by_four = {}
        if has_contacts_table:
            crows = conn.execute(
                """SELECT id, fournisseur_id, nom, fonction, emails, tels, langue, is_principal
                   FROM fournisseur_contacts WHERE actif=1
                   ORDER BY is_principal DESC, nom COLLATE NOCASE"""
            ).fetchall()
            for c in crows:
                d = dict(c)
                for k in ("emails", "tels"):
                    raw = d.get(k)
                    if raw:
                        try:
                            parsed = _json.loads(raw)
                            d[k] = parsed if isinstance(parsed, list) else []
                        except (_json.JSONDecodeError, TypeError):
                            d[k] = []
                    else:
                        d[k] = []
                d["is_principal"] = bool(d.get("is_principal"))
                contacts_by_four.setdefault(d["fournisseur_id"], []).append(d)

    out = []
    for f in frows:
        fd = dict(f)
        raw = fd.get("tags")
        if raw:
            try:
                fd["tags"] = _json.loads(raw) if isinstance(raw, str) else []
                if not isinstance(fd["tags"], list):
                    fd["tags"] = []
            except (_json.JSONDecodeError, TypeError):
                fd["tags"] = []
        else:
            fd["tags"] = []
        fd["contacts"] = contacts_by_four.get(fd["id"], [])
        out.append(fd)
    return out


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



# =========================================================================
# --- AO params + fiches techniques + config EUR/USD -----------------------
# =========================================================================

@router.patch("/{ao_id}/params")
async def update_ao_params(request: Request, ao_id: int):
    """Met a jour les parametres de calcul de l'AO (pour l'instant : prix_transport_pct)."""
    _require_ao(request)
    body = await request.json()
    pct = body.get("prix_transport_pct")
    try:
        pct = float(pct) if pct is not None else 0.0
    except (TypeError, ValueError):
        pct = 0.0
    pct = max(0.0, min(100.0, pct))
    with get_db() as conn:
        row = conn.execute("SELECT id FROM ao_demandes WHERE id=?", (ao_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="AO introuvable.")
        conn.execute(
            "UPDATE ao_demandes SET prix_transport_pct=? WHERE id=?",
            (pct, ao_id),
        )
        conn.commit()
    return {"ok": True, "ao_id": ao_id, "prix_transport_pct": pct}


@router.get("/fiches-techniques")
def search_fiches_techniques(request: Request, q: str = "", limit: int = 20):
    """Recherche autocomplete sur fiches_techniques (reference, designation, client)."""
    _require_ao(request)
    q_norm = (q or "").strip()
    try:
        limit = max(1, min(50, int(limit)))
    except (TypeError, ValueError):
        limit = 20
    with get_db() as conn:
        if not q_norm:
            rows = conn.execute(
                """SELECT id, reference, designation, client, format, matiere
                   FROM fiches_techniques
                   ORDER BY date_import DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
        else:
            like = f"%{q_norm}%"
            rows = conn.execute(
                """SELECT id, reference, designation, client, format, matiere
                   FROM fiches_techniques
                   WHERE reference LIKE ? COLLATE NOCASE
                      OR IFNULL(designation,'') LIKE ? COLLATE NOCASE
                      OR IFNULL(client,'')      LIKE ? COLLATE NOCASE
                   ORDER BY
                     CASE WHEN reference LIKE ? COLLATE NOCASE THEN 0 ELSE 1 END,
                     reference COLLATE NOCASE
                   LIMIT ?""",
                (like, like, like, f"{q_norm}%", limit),
            ).fetchall()
    return [dict(r) for r in rows]


@router.get("/fiches-techniques/by-ref/{reference}")
def get_fiche_technique(request: Request, reference: str):
    """Retourne la fiche technique complete (tous les champs disponibles)."""
    _require_ao(request)
    ref = (reference or "").strip()
    if not ref:
        raise HTTPException(status_code=400, detail="Reference vide.")
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM fiches_techniques WHERE LOWER(TRIM(reference))=LOWER(TRIM(?)) LIMIT 1",
            (ref,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Fiche technique introuvable pour '{ref}'.")
        return dict(row)


@router.get("/config/eur-usd")
def get_eur_usd(request: Request):
    """Retourne le taux EUR/USD actif. Source de verite : mc_setting.eur_usd_rate.
    Fallback : matiere_config.taux_change_usd."""
    _require_ao(request)
    with get_db() as conn:
        rate = 0.0
        try:
            row = conn.execute(
                "SELECT value_decimal FROM mc_setting WHERE key='eur_usd_rate' LIMIT 1"
            ).fetchone()
            if row and row[0] is not None:
                rate = float(row[0])
        except Exception:
            rate = 0.0
        if rate <= 0:
            try:
                row = conn.execute(
                    "SELECT valeur FROM matiere_config WHERE cle='taux_change_usd' LIMIT 1"
                ).fetchone()
                if row:
                    rate = float(row[0])
            except Exception:
                pass
    return {"eur_usd_rate": rate}


@router.post("/config/eur-usd")
async def set_eur_usd(request: Request):
    """Ecrit le taux EUR/USD dans les deux tables (source unifiee).
    Corps : { "eur_usd_rate": <float> }"""
    user = _require_ao(request)
    body = await request.json()
    try:
        rate = float(body.get("eur_usd_rate") or 0)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="eur_usd_rate invalide.")
    if rate <= 0:
        raise HTTPException(status_code=400, detail="eur_usd_rate doit etre > 0.")
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        # 1. mc_setting (source canonique)
        try:
            existing = conn.execute(
                "SELECT 1 FROM mc_setting WHERE key='eur_usd_rate' LIMIT 1"
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE mc_setting SET value_decimal=?, updated_at=?, updated_by=?, source=? WHERE key='eur_usd_rate'",
                    (rate, now, user.get("id"), "ao_panel"),
                )
            else:
                conn.execute(
                    "INSERT INTO mc_setting (key, value_decimal, updated_at, updated_by, source) VALUES ('eur_usd_rate', ?, ?, ?, ?)",
                    (rate, now, user.get("id"), "ao_panel"),
                )
        except Exception as e:
            # Table peut-etre absente (migration MyCouts pas passee). On log en douceur.
            print(f"[eur-usd] mc_setting write failed: {e}")
        # 2. matiere_config (compat Cout matiere)
        try:
            conn.execute(
                """INSERT INTO matiere_config (cle, valeur, updated_at) VALUES (?,?,?)
                   ON CONFLICT(cle) DO UPDATE SET valeur=excluded.valeur, updated_at=excluded.updated_at""",
                ("taux_change_usd", str(rate), now),
            )
        except Exception as e:
            print(f"[eur-usd] matiere_config write failed: {e}")
        conn.commit()
    return {"ok": True, "eur_usd_rate": rate}



def _serialize_produit_row(row: dict, conn) -> dict:
    client_nom = row.get("client_nom") or _client_nom(conn, row.get("client_id"))
    return produit_row_to_api(row, client_nom)


# ─── Catalogue produits (routes statiques avant /{ao_id}) ─────────

@router.get("/produits")
def list_produits(request: Request):
    _require_ao(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT p.*,
                      COALESCE(cg.raison_sociale, lc.nom) AS client_nom
               FROM ao_produits p
               LEFT JOIN clients            cg ON cg.id = p.client_id
               LEFT JOIN ao_carnet_clients  lc ON lc.id = p.client_id
               ORDER BY p.ref COLLATE NOCASE"""
        ).fetchall()
        return [_serialize_produit_row(_row_dict(r), conn) for r in rows]


@router.get("/produits/{produit_id}")
def get_produit(request: Request, produit_id: int):
    _require_ao(request)
    with get_db() as conn:
        row = conn.execute(
            """SELECT p.*,
                      COALESCE(cg.raison_sociale, lc.nom) AS client_nom
               FROM ao_produits p
               LEFT JOIN clients            cg ON cg.id = p.client_id
               LEFT JOIN ao_carnet_clients  lc ON lc.id = p.client_id
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
            """SELECT p.*,
                      COALESCE(cg.raison_sociale, lc.nom) AS client_nom
               FROM ao_produits p
               LEFT JOIN clients            cg ON cg.id = p.client_id
               LEFT JOIN ao_carnet_clients  lc ON lc.id = p.client_id
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


_DUP_REF_RE = re.compile(r"^(?P<base>.+?)\((?P<n>\d+)\)\s*$")


def _next_copy_ref(conn, source_ref: str) -> str:
    """Calcule la prochaine référence de copie pour un produit.

    Règle :
      - "ABC"        → "ABC(1)" (ou "ABC(2)" si "ABC(1)" existe déjà)
      - "ABC(1)"     → "ABC(2)" (jamais "ABC(1)(1)")
      - "ABC(7)"     → "ABC(8)" si "ABC(8)" libre, sinon la 1re libre
    """
    source_ref = (source_ref or "").strip()
    if not source_ref:
        raise HTTPException(status_code=400, detail="Référence source vide.")
    m = _DUP_REF_RE.match(source_ref)
    base = m.group("base").rstrip() if m else source_ref
    # Cherche toutes les réfs existantes en "base(N)" pour déterminer N max
    rows = conn.execute(
        "SELECT ref FROM ao_produits WHERE LOWER(ref) LIKE LOWER(?)",
        (f"{base}(%)%",),
    ).fetchall()
    taken: set[int] = set()
    for r in rows:
        mm = _DUP_REF_RE.match(r["ref"] or "")
        if mm and mm.group("base").rstrip().lower() == base.lower():
            try:
                taken.add(int(mm.group("n")))
            except (TypeError, ValueError):
                pass
    # Première valeur libre ≥ 1
    n = 1
    while n in taken:
        n += 1
    return f"{base}({n})"


@router.post("/produits/{produit_id}/dupliquer")
def dupliquer_produit(request: Request, produit_id: int):
    """Duplique une fiche produit. Nouvelle référence calculée selon la règle
    `ref(N)` (incrémente N si déjà existant, sans imbrication)."""
    user = _require_ao(request)
    now = _now_paris_iso()
    with get_db() as conn:
        src = conn.execute(
            "SELECT * FROM ao_produits WHERE id=?", (produit_id,)
        ).fetchone()
        if not src:
            raise HTTPException(status_code=404, detail="Produit introuvable")
        src_d = _row_dict(src)
        new_ref = _next_copy_ref(conn, src_d.get("ref") or "")
        try:
            cur = conn.execute(
                """INSERT INTO ao_produits
                   (ref, designation, unite, notes, client_id, fiche_json, created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    new_ref,
                    src_d.get("designation"),
                    src_d.get("unite"),
                    src_d.get("notes"),
                    src_d.get("client_id"),
                    src_d.get("fiche_json"),
                    now,
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            raise HTTPException(status_code=409, detail="Référence déjà utilisée.") from None
        row = conn.execute(
            "SELECT * FROM ao_produits WHERE id=?", (cur.lastrowid,)
        ).fetchone()
        result = _serialize_produit_row(_row_dict(row), conn)
    log_action(
        user=user, action="DUPLICATE", module="ao",
        objet=f"Produit {src_d.get('ref')} → {new_ref}",
        ip=request.client.host if request.client else None,
    )
    return result


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
async def cloturer_ao(request: Request, ao_id: int):
    """Cloture l'AO et notifie optionnellement le fournisseur retenu.

    Body JSON optionnel :
      - fournisseur_retenu_id (int) : id du fournisseur invite retenu
      - message_perso (str) : message personnalise ajoute a l'email au retenu
    """
    _require_ao(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    fournisseur_retenu_id = body.get("fournisseur_retenu_id")
    if fournisseur_retenu_id is not None:
        try:
            fournisseur_retenu_id = int(fournisseur_retenu_id)
        except (TypeError, ValueError):
            fournisseur_retenu_id = None
    message_perso = (body.get("message_perso") or "").strip() or None
    now = _now_paris_iso()

    with get_db() as conn:
        ao = _get_ao_or_404(conn, ao_id)
        if ao.get("statut") != "envoyee":
            raise HTTPException(
                status_code=400,
                detail="Cloture impossible : l'appel d'offre doit etre au statut envoyee.",
            )
        fourni_retenu = None
        if fournisseur_retenu_id:
            fourni_retenu = conn.execute(
                "SELECT * FROM ao_fournisseurs WHERE id=? AND ao_id=?",
                (fournisseur_retenu_id, ao_id),
            ).fetchone()
            if not fourni_retenu:
                raise HTTPException(status_code=400, detail="Fournisseur retenu invalide.")

        aod_cols = {r[1] for r in conn.execute("PRAGMA table_info(ao_demandes)").fetchall()}
        if "fournisseur_retenu_id" in aod_cols and "date_cloture" in aod_cols:
            conn.execute(
                "UPDATE ao_demandes SET statut='cloturee', fournisseur_retenu_id=?, date_cloture=? WHERE id=?",
                (fournisseur_retenu_id, now, ao_id),
            )
        else:
            conn.execute(
                "UPDATE ao_demandes SET statut='cloturee' WHERE id=?",
                (ao_id,),
            )
        conn.commit()
        updated = _get_ao_or_404(conn, ao_id)

    if fourni_retenu:
        try:
            subject, html_body = email_offre_retenue(
                dict(updated), dict(fourni_retenu), message_perso=message_perso
            )
            send_email(fourni_retenu["email_contact"], subject, html_body)
        except Exception as e:
            logger.warning("Envoi email offre retenue echoue pour AO %s: %s", ao_id, e)

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




@router.get("/{ao_id}/export.pdf")
def export_ao_pdf(request: Request, ao_id: int):
    """Genere un PDF recapitulant l'AO : infos, lignes, fournisseurs invites + reponses."""
    from fastapi.responses import Response
    _require_ao(request)
    with get_db() as conn:
        ao = _get_ao_or_404(conn, ao_id)
        lignes = [dict(r) for r in conn.execute(
            "SELECT * FROM ao_lignes WHERE ao_id=? ORDER BY position, id",
            (ao_id,),
        ).fetchall()]
        fournis = [dict(r) for r in conn.execute(
            "SELECT * FROM ao_fournisseurs WHERE ao_id=? ORDER BY nom_fournisseur COLLATE NOCASE",
            (ao_id,),
        ).fetchall()]
        # Reponses regroupees par fournisseur
        rep_rows = conn.execute(
            """SELECT r.ao_fournisseur_id, r.ligne_id, r.quotation, r.devise,
                      r.unite_quotation, r.delai_jours, r.commentaire
               FROM ao_reponses r
               JOIN ao_fournisseurs f ON f.id = r.ao_fournisseur_id
               WHERE f.ao_id=?""",
            (ao_id,),
        ).fetchall()
        reponses_by_fourni: dict[int, dict[int, dict]] = {}
        for r in rep_rows:
            reponses_by_fourni.setdefault(r["ao_fournisseur_id"], {})[r["ligne_id"]] = dict(r)

    # Genere le PDF avec reportlab (deja dans les deps)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab non disponible sur le serveur.")

    from io import BytesIO
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, leading=10)
    normal = styles["Normal"]

    story = []
    story.append(Paragraph(f"Appel d'offres — {ao.get('reference') or ''}", h1))
    story.append(Paragraph(ao.get("titre") or "", h2))
    story.append(Spacer(1, 0.3*cm))

    info_data = [
        ["Reference", ao.get("reference") or "—"],
        ["Statut", (ao.get("statut") or "").capitalize()],
        ["Date creation", (ao.get("date_creation") or "")[:10]],
        ["Date limite", ao.get("date_limite") or "—"],
        ["Responsable", ao.get("responsable_email") or "—"],
    ]
    info_tbl = Table(info_data, colWidths=[4*cm, 12*cm])
    info_tbl.setStyle(TableStyle([
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 0.4*cm))

    if ao.get("description"):
        story.append(Paragraph("<b>Description</b>", normal))
        story.append(Paragraph(str(ao.get("description")), small))
        story.append(Spacer(1, 0.3*cm))

    # Lignes produits
    story.append(Paragraph("<b>Lignes produits</b>", h2))
    if lignes:
        lignes_data = [["Ref produit", "Designation", "Quantite", "Unite", "Notes"]]
        for ln in lignes:
            lignes_data.append([
                ln.get("ref_produit") or "",
                (ln.get("designation") or "")[:60],
                str(ln.get("quantite") or ""),
                ln.get("unite") or "",
                (ln.get("notes") or "")[:40],
            ])
        tbl = Table(lignes_data, colWidths=[3*cm, 6*cm, 2*cm, 2*cm, 4*cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#eef2f7")),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))
        story.append(tbl)
    else:
        story.append(Paragraph("<i>Aucune ligne produit.</i>", small))
    story.append(Spacer(1, 0.5*cm))

    # Fournisseurs invites + reponses
    story.append(Paragraph("<b>Fournisseurs invites</b>", h2))
    if fournis:
        four_data = [["Nom", "Email", "Statut", "Envoi", "Reponse"]]
        for f in fournis:
            four_data.append([
                (f.get("nom_fournisseur") or "")[:30],
                (f.get("email_contact") or "")[:35],
                (f.get("statut") or ""),
                (f.get("date_envoi") or "")[:10],
                (f.get("date_reponse") or "")[:10],
            ])
        tbl = Table(four_data, colWidths=[4*cm, 6*cm, 2.5*cm, 2*cm, 2.5*cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#eef2f7")),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.5*cm))

        # Reponses detaillees par fournisseur
        for f in fournis:
            reps = reponses_by_fourni.get(f["id"])
            if not reps:
                continue
            story.append(PageBreak())
            story.append(Paragraph(f"Reponse — {f.get('nom_fournisseur') or ''}", h2))
            rep_data = [["Ref produit", "Prix", "Devise", "Unite", "Delai (j)", "Commentaire"]]
            for ln in lignes:
                r = reps.get(ln["id"])
                if not r:
                    continue
                rep_data.append([
                    ln.get("ref_produit") or "",
                    (f"{r.get('quotation'):.4f}" if r.get('quotation') is not None else "—"),
                    r.get("devise") or "EUR",
                    r.get("unite_quotation") or "mille",
                    str(r.get("delai_jours") or "—"),
                    (r.get("commentaire") or "")[:40],
                ])
            tbl = Table(rep_data, colWidths=[3*cm, 2.5*cm, 1.5*cm, 2*cm, 2*cm, 6*cm])
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#eef2f7")),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE", (0,0), (-1,-1), 8),
                ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
            ]))
            story.append(tbl)
    else:
        story.append(Paragraph("<i>Aucun fournisseur invite.</i>", small))

    doc.build(story)
    pdf_bytes = buf.getvalue()
    buf.close()

    filename = f"AO_{ao.get('reference') or ao_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
    # fournisseur_ids : liste optionnelle d'IDs a recopier. Si absente,
    # copie tous les fournisseurs (comportement existant). Si liste vide,
    # ne copie aucun fournisseur meme si with_fournisseurs=True.
    fournisseur_ids_raw = body.get("fournisseur_ids")
    fournisseur_ids: list[int] | None = None
    if isinstance(fournisseur_ids_raw, list):
        fournisseur_ids = []
        for v in fournisseur_ids_raw:
            try:
                fournisseur_ids.append(int(v))
            except (TypeError, ValueError):
                pass
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
        # Si fournisseur_ids est fourni : ne copier que ceux-là. Sinon : tous (si with_fournisseurs).
        if with_fournisseurs and (fournisseur_ids is None or fournisseur_ids):
            if fournisseur_ids is not None:
                qmarks = ",".join("?" * len(fournisseur_ids))
                src_fournis = conn.execute(
                    f"SELECT * FROM ao_fournisseurs WHERE ao_id=? AND id IN ({qmarks})",
                    tuple([ao_id] + fournisseur_ids),
                ).fetchall()
            else:
                src_fournis = conn.execute(
                    "SELECT * FROM ao_fournisseurs WHERE ao_id=?",
                    (ao_id,),
                ).fetchall()
            for f in src_fournis:
                src_langue = _normalize_langue(f["langue"] if "langue" in f.keys() else "fr")
                conn.execute(
                    """INSERT INTO ao_fournisseurs
                       (ao_id, nom_fournisseur, email_contact, token, statut, langue)
                       VALUES (?,?,?,?,'invite',?)""",
                    (
                        new_id,
                        f["nom_fournisseur"],
                        f["email_contact"],
                        str(uuid.uuid4()),
                        src_langue,
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
    langue = _normalize_langue(body.get("langue"))
    fournisseur_id = body.get("fournisseur_id")
    contact_id = body.get("fournisseur_contact_id")
    try:
        fournisseur_id = int(fournisseur_id) if fournisseur_id is not None else None
    except (TypeError, ValueError):
        fournisseur_id = None
    try:
        contact_id = int(contact_id) if contact_id is not None else None
    except (TypeError, ValueError):
        contact_id = None
    token = str(uuid.uuid4())
    with get_db() as conn:
        _get_ao_or_404(conn, ao_id)
        af_cols = {r[1] for r in conn.execute("PRAGMA table_info(ao_fournisseurs)").fetchall()}
        if "fournisseur_id" in af_cols and "fournisseur_contact_id" in af_cols:
            cur = conn.execute(
                """INSERT INTO ao_fournisseurs
                   (ao_id, nom_fournisseur, email_contact, token, statut, langue,
                    fournisseur_id, fournisseur_contact_id)
                   VALUES (?,?,?,?,'invite',?,?,?)""",
                (ao_id, nom, email, token, langue, fournisseur_id, contact_id),
            )
        else:
            cur = conn.execute(
                """INSERT INTO ao_fournisseurs
                   (ao_id, nom_fournisseur, email_contact, token, statut, langue)
                   VALUES (?,?,?,?,'invite',?)""",
                (ao_id, nom, email, token, langue),
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




@router.put("/{ao_id}/fournisseurs/{fourni_id}")
async def update_fournisseur_ao(request: Request, ao_id: int, fourni_id: int):
    """Override local (nom, email, langue) d'un fournisseur invite — ne touche pas Parametres."""
    _require_ao(request)
    body = await request.json()
    with get_db() as conn:
        fourni = _get_fourni_in_ao(conn, ao_id, fourni_id)
        if fourni.get("statut") == "repondu":
            raise HTTPException(status_code=400, detail="Modification impossible — le fournisseur a deja repondu.")
        nom = (body.get("nom_fournisseur") or fourni["nom_fournisseur"] or "").strip()
        email = (body.get("email_contact") or fourni["email_contact"] or "").strip().lower()
        if not nom or not email:
            raise HTTPException(status_code=400, detail="Nom et email obligatoires.")
        if "langue" in body:
            langue = _normalize_langue(body.get("langue"))
        else:
            langue = fourni.get("langue") or "fr"
        conn.execute(
            """UPDATE ao_fournisseurs SET nom_fournisseur=?, email_contact=?, langue=?
               WHERE id=? AND ao_id=?""",
            (nom, email, langue, fourni_id, ao_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM ao_fournisseurs WHERE id=?", (fourni_id,)).fetchone()
    return _row_dict(row)


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
        lignes_raw = [
            _row_dict(r)
            for r in conn.execute(
                "SELECT ref_produit, designation, quantite, unite FROM ao_lignes WHERE ao_id=? ORDER BY position, id",
                (ao_id,),
            ).fetchall()
        ]
        # Enrichit chaque ligne avec etiquettes_par_bobine et client_nom (fiche produit)
        produits_map = _produits_by_ref_map(conn)
        mat_ids = _matiere_ids_from_produits(produits_map)
        matieres_map = _load_matieres_map(conn, mat_ids or None)
        lignes = [
            _enrich_ligne_display(ln, produits_map, matieres_map)
            for ln in lignes_raw
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
