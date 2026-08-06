"""MySifa — MyAO (appels d'offres) — API interne.

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
from typing import Any, Sequence
from zoneinfo import ZoneInfo

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response

from app.services.audit_service import log_action
from app.services.email_service import (
    email_invitation_ao,
    email_message_fournisseur,
    email_offre_retenue,
    send_email,
)
from app.services import ao_evenements as ao_ev
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
from app.services.ao_ref_produit import (
    build_ref_produit,
    matiere_abbrev,
    unique_ref,
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
            detail="Modification impossible — l'appel d'offres n'est plus en brouillon.",
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


def _translate_or_original(text, target_lang, conn):
    """Traduit text vers target_lang via translate_service + cache.
    Retourne l'original en cas d'erreur ou si target = fr."""
    if not text or not (text or "").strip():
        return text
    tgt = (target_lang or "").strip().upper()
    if not tgt or tgt in ("FR", "FR-FR"):
        return text
    try:
        from app.services.translate_service import translate as _svc_translate
        res = _svc_translate(conn, text=text, target_lang=tgt, source_lang="FR", formality="default")
        return res.get("translated") or text
    except Exception:
        return text


@router.get("")
def list_ao(request: Request, filter: str = ""):
    """List AOs. Par defaut : actifs uniquement (deleted_at IS NULL).
    filter=corbeille : uniquement les supprimes."""
    _require_ao(request)
    show_deleted = (filter or "").strip().lower() == "corbeille"
    where_deleted = "d.deleted_at IS NOT NULL" if show_deleted else "d.deleted_at IS NULL"
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT d.id, d.reference, d.titre, d.statut, d.date_creation, d.date_limite,
                       d.deleted_at,
                       (SELECT COUNT(*) FROM ao_fournisseurs f WHERE f.ao_id = d.id) AS nb_fournisseurs,
                       (SELECT COUNT(*) FROM ao_fournisseurs f WHERE f.ao_id = d.id AND f.statut = 'repondu') AS nb_reponses,
                       (SELECT GROUP_CONCAT(DISTINCT l.ref_produit)
                          FROM ao_lignes l
                          WHERE l.ao_id = d.id
                            AND l.ref_produit IS NOT NULL AND l.ref_produit != '') AS refs_produits,
                       -- Le client d'un AO se déduit de ses produits. On joint sur
                       -- produit_id, avec repli sur la référence normalisée pour
                       -- les lignes que le backfill n'a pas rattachées. L'ancien
                       -- « p.ref = l.ref_produit » était sensible à la casse et
                       -- aux espaces : la moindre divergence vidait la colonne.
                       (SELECT GROUP_CONCAT(DISTINCT COALESCE(cg.raison_sociale, lc.nom))
                          FROM ao_lignes l
                          JOIN ao_produits p
                            ON p.id = l.produit_id
                            OR (l.produit_id IS NULL
                                AND LOWER(TRIM(p.ref)) = LOWER(TRIM(COALESCE(l.ref_produit,''))))
                          LEFT JOIN clients            cg ON cg.id = p.client_id
                          LEFT JOIN ao_carnet_clients  lc ON lc.id = p.client_id
                          WHERE l.ao_id = d.id) AS clients,
                       COALESCE(d.prix_transport_pct, 0) AS prix_transport_pct
                FROM ao_demandes d
                WHERE {where_deleted}
                ORDER BY d.date_creation DESC"""
        ).fetchall()
        # Enrichit chaque AO avec le résumé de ses lignes (ref + qté) pour affichage
        # dans la colonne « Titre » de la liste (auto-généré).
        out: list[dict] = []
        for r in rows:
            d = _row_dict(r)
            # La référence affichée est celle du produit rattaché quand il existe :
            # le résumé suit ainsi les renommages, et une ligne sans produit se
            # repère à son drapeau orphelin.
            lignes = conn.execute(
                """SELECT l.ref_produit, l.quantite, p.ref AS produit_ref
                     FROM ao_lignes l
                     LEFT JOIN ao_produits p ON p.id = l.produit_id
                    WHERE l.ao_id=? ORDER BY l.position, l.id""",
                (int(d["id"]),),
            ).fetchall()
            d["lignes_summary"] = [
                {"ref": (l["produit_ref"] or l["ref_produit"] or "").strip() or "—",
                 "qte": (float(l["quantite"]) if l["quantite"] is not None else None),
                 "orpheline": not (l["produit_ref"] or "").strip()}
                for l in lignes
            ]
            out.append(d)
    return out


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
        cols = {r[1] for r in conn.execute("PRAGMA table_info(fournisseurs_fsc)").fetchall()}
        # Colonnes disponibles + valeurs supplémentaires (ville, langue_default)
        insert_cols = ["nom", "licence", "certificat"]
        insert_vals: list = [nom, licence, certificat]
        for extra in ("ville", "langue_default"):
            if extra in cols and body.get(extra) is not None:
                v = body.get(extra)
                if isinstance(v, str):
                    v = v.strip() or None
                insert_cols.append(extra)
                insert_vals.append(v)
        placeholders = ",".join("?" * len(insert_cols))
        try:
            cur = conn.execute(
                f"INSERT INTO fournisseurs_fsc ({', '.join(insert_cols)}) VALUES ({placeholders})",
                tuple(insert_vals),
            )
            conn.commit()
            new_id = cur.lastrowid
        except Exception:
            raise HTTPException(409, "Ce fournisseur existe déjà.")
        row = conn.execute(
            "SELECT * FROM fournisseurs_fsc WHERE id=?",
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


# ─── CRUD Fournisseurs (onglet Fournisseurs MyAO) ─────────────────
# Ces endpoints permettent d'éditer directement les fournisseurs et
# leurs contacts depuis MyAO, sans devoir passer par Paramètres.
# La table fournisseurs_fsc est partagée avec Qualité / Fabrication,
# donc la suppression est un soft-delete via actif=0 (protégeant les
# références historiques dans les autres modules).

@router.put("/picker/fournisseurs/{four_id}")
async def update_fournisseur(request: Request, four_id: int):
    _require_ao(request)
    body = await request.json()
    nom = (body.get("nom") or "").strip()
    if not nom:
        raise HTTPException(status_code=400, detail="Nom du fournisseur obligatoire.")
    with get_db() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(fournisseurs_fsc)").fetchall()}
        # Champs autorisés à l'édition
        allowed = ("nom", "licence", "certificat", "ville", "langue_default")
        sets = []
        vals: list = []
        for k in allowed:
            if k in cols and k in body:
                v = body.get(k)
                if isinstance(v, str):
                    v = v.strip() or None
                sets.append(f"{k}=?")
                vals.append(v)
        if not sets:
            raise HTTPException(status_code=400, detail="Rien à modifier.")
        vals.append(four_id)
        try:
            cur = conn.execute(
                f"UPDATE fournisseurs_fsc SET {', '.join(sets)} WHERE id=?", vals
            )
        except Exception:
            raise HTTPException(status_code=409, detail="Nom déjà utilisé.")
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Fournisseur introuvable.")
        conn.commit()
        row = conn.execute(
            "SELECT * FROM fournisseurs_fsc WHERE id=?", (four_id,)
        ).fetchone()
    return _row_dict(row)


@router.delete("/picker/fournisseurs/{four_id}")
def delete_fournisseur(request: Request, four_id: int):
    """Soft-delete (actif=0) — la table est partagée avec d'autres modules
    et supprimer physiquement casserait l'historique."""
    _require_ao(request)
    with get_db() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(fournisseurs_fsc)").fetchall()}
        if "actif" in cols:
            cur = conn.execute(
                "UPDATE fournisseurs_fsc SET actif=0 WHERE id=?", (four_id,)
            )
        else:
            cur = conn.execute("DELETE FROM fournisseurs_fsc WHERE id=?", (four_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Fournisseur introuvable.")
        conn.commit()
    return {"ok": True, "fournisseur_id": four_id}


@router.post("/picker/fournisseurs/{four_id}/contacts")
async def create_fournisseur_contact(request: Request, four_id: int):
    _require_ao(request)
    body = await request.json()
    nom = (body.get("nom") or "").strip()
    if not nom:
        raise HTTPException(status_code=400, detail="Nom du contact obligatoire.")
    import json as _json
    fonction = (body.get("fonction") or "").strip() or None
    langue = (body.get("langue") or "fr").strip().lower()
    if langue not in ("fr", "en", "it", "es", "de"):
        langue = "fr"
    emails = body.get("emails") or []
    if isinstance(emails, str):
        emails = [e.strip() for e in emails.split(",") if e.strip()]
    tels = body.get("tels") or []
    if isinstance(tels, str):
        tels = [t.strip() for t in tels.split(",") if t.strip()]
    is_principal = 1 if body.get("is_principal") else 0
    with get_db() as conn:
        exists = conn.execute(
            "SELECT id FROM fournisseurs_fsc WHERE id=?", (four_id,)
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Fournisseur introuvable.")
        # Si is_principal, remettre les autres à 0
        if is_principal:
            conn.execute(
                "UPDATE fournisseur_contacts SET is_principal=0 WHERE fournisseur_id=?",
                (four_id,),
            )
        now_iso = _now_paris_iso()
        cur = conn.execute(
            """INSERT INTO fournisseur_contacts
               (fournisseur_id, nom, fonction, emails, tels, langue, is_principal, actif, created_at)
               VALUES (?,?,?,?,?,?,?,1,?)""",
            (four_id, nom, fonction, _json.dumps(emails), _json.dumps(tels), langue, is_principal, now_iso),
        )
        conn.commit()
        new_id = cur.lastrowid
        row = conn.execute(
            "SELECT * FROM fournisseur_contacts WHERE id=?", (new_id,)
        ).fetchone()
    d = _row_dict(row)
    for k in ("emails", "tels"):
        try:
            d[k] = _json.loads(d.get(k) or "[]")
        except (_json.JSONDecodeError, TypeError):
            d[k] = []
    d["is_principal"] = bool(d.get("is_principal"))
    return d


@router.put("/picker/fournisseurs/{four_id}/contacts/{contact_id}")
async def update_fournisseur_contact(request: Request, four_id: int, contact_id: int):
    _require_ao(request)
    body = await request.json()
    nom = (body.get("nom") or "").strip()
    if not nom:
        raise HTTPException(status_code=400, detail="Nom du contact obligatoire.")
    import json as _json
    fonction = (body.get("fonction") or "").strip() or None
    langue = (body.get("langue") or "fr").strip().lower()
    if langue not in ("fr", "en", "it", "es", "de"):
        langue = "fr"
    emails = body.get("emails") or []
    if isinstance(emails, str):
        emails = [e.strip() for e in emails.split(",") if e.strip()]
    tels = body.get("tels") or []
    if isinstance(tels, str):
        tels = [t.strip() for t in tels.split(",") if t.strip()]
    is_principal = 1 if body.get("is_principal") else 0
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM fournisseur_contacts WHERE id=? AND fournisseur_id=?",
            (contact_id, four_id),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Contact introuvable.")
        if is_principal:
            conn.execute(
                "UPDATE fournisseur_contacts SET is_principal=0 WHERE fournisseur_id=? AND id!=?",
                (four_id, contact_id),
            )
        conn.execute(
            """UPDATE fournisseur_contacts
               SET nom=?, fonction=?, emails=?, tels=?, langue=?, is_principal=?, updated_at=?
               WHERE id=?""",
            (nom, fonction, _json.dumps(emails), _json.dumps(tels), langue, is_principal, _now_paris_iso(), contact_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM fournisseur_contacts WHERE id=?", (contact_id,)
        ).fetchone()
    d = _row_dict(row)
    for k in ("emails", "tels"):
        try:
            d[k] = _json.loads(d.get(k) or "[]")
        except (_json.JSONDecodeError, TypeError):
            d[k] = []
    d["is_principal"] = bool(d.get("is_principal"))
    return d


@router.delete("/picker/fournisseurs/{four_id}/contacts/{contact_id}")
def delete_fournisseur_contact(request: Request, four_id: int, contact_id: int):
    """Soft-delete (actif=0)."""
    _require_ao(request)
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE fournisseur_contacts SET actif=0 WHERE id=? AND fournisseur_id=?",
            (contact_id, four_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Contact introuvable.")
        conn.commit()
    return {"ok": True, "contact_id": contact_id}


# ─── Matières premières (lecture pour fiches produit) ─────────────

_MP_AO_CATEGORIES = frozenset({
    "frontal", "adhesif", "glassine", "carton", "palette", "mandrin",
})


def _load_matieres_map(conn, ids: set[int] | None = None) -> dict[int, dict]:
    if ids:
        placeholders = ",".join("?" * len(ids))
        rows = conn.execute(
            f"""SELECT id, categorie, reference, designation, couleur,
                       sous_categorie, sous_categorie_en, abbreviation
                FROM matieres_premieres WHERE id IN ({placeholders}) AND actif=1""",
            tuple(ids),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT id, categorie, reference, designation, couleur,
                       sous_categorie, sous_categorie_en, abbreviation
               FROM matieres_premieres WHERE actif=1
               ORDER BY categorie, reference"""
        ).fetchall()
    return {int(r["id"]): _row_dict(r) for r in rows}


def _with_abbrev(row: dict) -> dict:
    """Ajoute ``abbrev`` : la forme courte effective de la matière.

    Le formulaire produit compose la référence côté client ; il consomme cette
    valeur déjà résolue plutôt que de dupliquer le glossaire d'abréviation en JS.
    ``abbreviation`` reste exposé tel quel pour l'édition dans MyStock.
    """
    row["abbrev"] = matiere_abbrev(row)
    return row


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
                """SELECT id, categorie, reference, designation, couleur,
                       sous_categorie, sous_categorie_en, abbreviation
                   FROM matieres_premieres
                   WHERE actif=1 AND categorie=?
                   ORDER BY reference COLLATE NOCASE""",
                (cat,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, categorie, reference, designation, couleur,
                       sous_categorie, sous_categorie_en, abbreviation
                   FROM matieres_premieres
                   WHERE actif=1 AND categorie IN (
                     'frontal','adhesif','glassine','carton','palette','mandrin'
                   )
                   ORDER BY categorie, reference COLLATE NOCASE"""
            ).fetchall()
    return [_with_abbrev(_row_dict(r)) for r in rows]


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


def _ref_key(value: Any) -> str:
    """Clé de comparaison d'une référence produit : sans espaces de bord, repliée.

    ``str.casefold()`` et non ``LOWER()`` SQL : LOWER() et COLLATE NOCASE de
    SQLite ne replient que l'ASCII, donc « COUCHÉ » ne s'y compare pas à
    « couché ». Les références d'ici sont pleines d'accents ; comparer en SQL
    laissait passer des doublons et ratait des rattachements.
    """
    return str(value or "").strip().casefold()


def _produit_id_key(produit_id: Any) -> str | None:
    """Clé canonique d'un produit dans produits_map. None si l'id est inutilisable."""
    try:
        return f"#{int(produit_id)}"
    except (TypeError, ValueError):
        return None


def _produits_by_ref_map(conn) -> dict[str, dict]:
    """Catalogue produits indexé pour la résolution des lignes d'AO.

    Le dict porte deux familles de clés vers les MÊMES objets produit :

      - ``"#<id>"``      clé canonique, insensible aux renommages de référence ;
      - ``"<ref>"``      en minuscules et sans espaces de bord — repli historique
                         pour les lignes dont ``produit_id`` est encore NULL.

    Passer par ``_resolve_produit_for_ligne()`` plutôt que d'indexer à la main :
    l'ordre de priorité entre les deux familles de clés est ce qui empêche une
    ligne de s'orpheliner quand la référence du produit change.
    """
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
        produit = _serialize_produit_row(d, conn)
        id_key = _produit_id_key(d.get("id"))
        if id_key:
            out[id_key] = produit
        ref_key = _ref_key(d.get("ref"))
        if ref_key and ref_key not in out:
            out[ref_key] = produit
    return out


def _resolve_produit_for_ligne(ln: dict, produits_map: dict[str, dict]) -> dict | None:
    """Produit d'une ligne d'AO : ``produit_id`` d'abord, ``ref_produit`` en repli.

    Le repli par référence couvre deux cas légitimes : les lignes antérieures à
    la colonne ``produit_id`` que le backfill n'a pas pu rattacher, et les dicts
    de ligne synthétiques ``{"ref_produit": ...}`` construits par les appels de
    rattrapage. Il ne doit jamais devenir le chemin principal.
    """
    id_key = _produit_id_key(ln.get("produit_id"))
    if id_key:
        produit = produits_map.get(id_key)
        if produit:
            return produit
    ref_key = _ref_key(ln.get("ref_produit"))
    return produits_map.get(ref_key) if ref_key else None


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
    key = _ref_key(ref)
    if not key:
        return False
    # Comparaison en Python sur l'ensemble des références : le catalogue produit
    # se compte en centaines de lignes, le coût est négligeable devant le risque
    # de créer deux produits que tout le monde lira comme le même.
    rows = conn.execute("SELECT id, ref FROM ao_produits").fetchall()
    for row in rows:
        if exclude_id is not None and int(row["id"]) == int(exclude_id):
            continue
        if _ref_key(row["ref"]) == key:
            return True
    return False


def _fiche_matieres_map(conn, fiche: dict) -> dict[int, dict]:
    """Lignes matieres_premieres référencées par la fiche (frontal, adhésif…)."""
    mat = (fiche or {}).get("matiere") or {}
    ids: set[int] = set()
    for key in ("frontal_id", "adhesif_id", "glassine_id"):
        try:
            if mat.get(key) not in (None, ""):
                ids.add(int(mat[key]))
        except (TypeError, ValueError):
            pass
    return _load_matieres_map(conn, ids) if ids else {}


def _compose_ref_produit(conn, fiche: dict) -> str:
    """Référence composée depuis la fiche, avec les abréviations de la base."""
    return build_ref_produit(fiche, _fiche_matieres_map(conn, fiche))


def _existing_refs(conn, exclude_id: int | None = None) -> list[str]:
    if exclude_id is not None:
        rows = conn.execute(
            "SELECT ref FROM ao_produits WHERE id<>?", (exclude_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT ref FROM ao_produits").fetchall()
    return [str(r["ref"] or "") for r in rows]


@router.post("/produits/ref-auto")
async def compose_ref_produit(request: Request):
    """Compose la référence produit depuis une fiche, sans rien enregistrer.

    Le formulaire l'appelle pour proposer la référence pendant la saisie. Le
    calcul vit côté serveur — même code que l'enregistrement — pour que la
    référence proposée à l'écran soit exactement celle qui sera stockée.

    Body : ``{fiche: {...}, produit_id?: int}``
    Réponse : ``{ref, ref_unique, disponible}`` — ``ref`` est la composition
    brute, ``ref_unique`` la même éventuellement suffixée « (2) » si elle est
    déjà prise par un autre produit.
    """
    _require_ao(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    fiche = body.get("fiche")
    fiche = normalize_fiche(
        parse_fiche(json.dumps(fiche, ensure_ascii=False))
        if isinstance(fiche, dict) else default_fiche()
    )
    exclude_id = body.get("produit_id")
    try:
        exclude_id = int(exclude_id) if exclude_id not in (None, "") else None
    except (TypeError, ValueError):
        exclude_id = None

    with get_db() as conn:
        ref = _compose_ref_produit(conn, fiche)
        if not ref:
            return {"ref": "", "ref_unique": "", "disponible": True}
        return {
            "ref": ref,
            "ref_unique": unique_ref(ref, _existing_refs(conn, exclude_id)),
            "disponible": not _produit_ref_taken(conn, ref, exclude_id=exclude_id),
        }


def _produit_from_body(body: dict, conn) -> tuple[str, str, str, str | None, int | None, str]:
    ref = (body.get("ref") or "").strip()
    if isinstance(body.get("fiche"), dict):
        fiche = parse_fiche(json.dumps(body["fiche"], ensure_ascii=False))
    elif isinstance(body.get("fiche_json"), str):
        fiche = parse_fiche(body["fiche_json"])
    else:
        fiche = default_fiche()
    fiche = normalize_fiche(fiche)
    if not ref:
        # Référence laissée vide : on la compose depuis la fiche plutôt que de
        # refuser. C'est le même calcul que celui affiché dans le formulaire, donc
        # un client qui n'aurait pas envoyé le champ obtient la même référence.
        ref = _compose_ref_produit(conn, fiche)
    if not ref:
        raise HTTPException(
            status_code=400,
            detail=(
                "Référence produit obligatoire — elle se compose automatiquement "
                "à partir de la laize et de la longueur, renseignez-les ou "
                "saisissez la référence à la main."
            ),
        )
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


@router.get("/fiches-techniques/by-ref")
def get_fiche_technique(request: Request, ref: str = ""):
    """Retourne la fiche technique complete (query param `ref` : supporte les slashes)."""
    _require_ao(request)
    reference = (ref or "").strip()
    if not reference:
        raise HTTPException(status_code=400, detail="Reference vide.")
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM fiches_techniques WHERE LOWER(TRIM(reference))=LOWER(TRIM(?)) LIMIT 1",
            (reference,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Fiche technique introuvable pour '{reference}'.")
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


@router.get("/produits/{produit_id}/aos")
def produit_aos(request: Request, produit_id: int):
    """Liste des appels d'offres (hors corbeille) contenant ce produit — pour
    la section « historique » de la fiche produit. Match sur ref_produit."""
    _require_ao(request)
    with get_db() as conn:
        prow = conn.execute("SELECT ref FROM ao_produits WHERE id=?", (produit_id,)).fetchone()
        if not prow:
            raise HTTPException(status_code=404, detail="Produit introuvable")
        ref = (prow["ref"] or "").strip()
        if not ref:
            return {"aos": []}
        rows = conn.execute(
            """SELECT DISTINCT d.id, d.reference, d.titre, d.statut, d.date_limite
               FROM ao_lignes l
               JOIN ao_demandes d ON d.id = l.ao_id
               WHERE LOWER(TRIM(l.ref_produit)) = LOWER(TRIM(?))
                 AND d.deleted_at IS NULL
               ORDER BY d.id DESC""",
            (ref,),
        ).fetchall()
    return {"aos": [dict(r) for r in rows]}


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


@router.get("/produits/{produit_id}/pdf-fournisseur")
def export_produit_fiche_pdf_fournisseur(
    request: Request,
    produit_id: int,
    ao_id: int | None = None,
):
    """
    Génère le PDF fournisseur (bilingue FR/EN) d'une fiche produit MyAO.

    Reprend la charte graphique du PDF client mais avec les données
    brutes de la fiche produit (pas de mapping/classification).

    Query param optionnel : ao_id — si fourni, la référence de l'AO
    apparaît en pied de page du PDF.
    """
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
        ao_reference: str | None = None
        if ao_id:
            ao_row = conn.execute(
                "SELECT reference FROM ao_demandes WHERE id=?", (ao_id,)
            ).fetchone()
            if ao_row:
                ao_reference = ao_row["reference"]

    try:
        from app.services.fiche_pdf_fournisseur import generate_fiche_fournisseur_pdf
        pdf_bytes = generate_fiche_fournisseur_pdf(
            produit, matieres_map=mp_map, ao_reference=ao_reference,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur génération PDF : {exc}") from exc

    ref_clean = re.sub(r"[^\w\-]+", "_", str(produit.get("ref") or produit_id).split(" - ")[0])
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="fiche_fournisseur_{ref_clean}.pdf"'},
    )


@router.get("/produits/{produit_id}/bat")
def export_produit_bat(
    request: Request,
    produit_id: int,
    fmt: str = "svg",
    lang: str = "fr",
    ref_client: str = "",
):
    """BAT étiquette (plan technique A4) d'une fiche produit MyAO.

    fmt=svg → aperçu intégrable dans la page ; fmt=pdf → document client.
    lang=fr|en → langue du cartouche.
    """
    from app.services.bat_etiquette import (
        build_bat_spec, render_bat_svg, render_bat_pdf, bat_filename,
        translate_spec_fields,
    )

    user = _require_ao(request)
    fmt = "pdf" if str(fmt).lower() == "pdf" else "svg"
    lang = "en" if str(lang).lower() == "en" else "fr"

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

        # Libellés matières — dégradation propre si le schéma diffère.
        matieres_map = {}
        try:
            for mp in conn.execute("SELECT * FROM matieres_premieres").fetchall():
                d = _row_dict(mp)
                matieres_map[d.get("id")] = d
        except Exception:
            matieres_map = {}

        # Enrichissement fiche technique quand la Ref SIFA est renseignée.
        ft = None
        ref_sifa = str(fiche.get("ref_sifa") or produit.get("ref_sifa") or "").strip()
        if ref_sifa:
            try:
                ft_row = conn.execute(
                    "SELECT * FROM fiches_techniques WHERE LOWER(TRIM(reference))=LOWER(TRIM(?)) LIMIT 1",
                    (ref_sifa,),
                ).fetchone()
                if ft_row:
                    ft = _row_dict(ft_row)
            except Exception:
                ft = None

    spec = build_bat_spec(
        produit, fiche,
        matieres_map=matieres_map,
        fiche_technique=ft,
        client_nom=produit.get("client_nom") or "",
        ref_interne=produit.get("ref") or "",
        ref_client=ref_client,
        date_bat="/".join(reversed(_now_paris_iso()[:10].split("-"))),
        lang=lang,
    )

    # Champs libres (support, adhesif, couleurs) : saisis en francais en base,
    # traduits a la volee pour le BAT anglais. Connexion dediee et courte : le
    # cache DeepL ecrit, on ne veut pas tenir la connexion du rendu pendant un
    # appel reseau.
    if lang == "en":
        with get_db() as conn:
            translate_spec_fields(spec, conn, lang="en", user_id=user.get("id"))

    if fmt == "pdf":
        return Response(
            content=render_bat_pdf(spec, lang),
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{bat_filename(spec)}"'},
        )
    return Response(content=render_bat_svg(spec, lang), media_type="image/svg+xml")


@router.get("/produits/{produit_id}/etiquette-carton")
def export_produit_etiquette_carton(
    request: Request,
    produit_id: int,
    fmt: str = "svg",
    ref_sifa: str = "",
):
    """Etiquette d'identification carton (100 x 50 mm) d'une fiche produit MyAO.

    fmt=svg → apercu inline dans la fiche produit ; fmt=pdf → page a la taille
    exacte de l'etiquette, prete pour l'imprimante d'etiquettes.

    ref_sifa surcharge la Ref SIFA enregistree : la fiche produit la transmet
    telle qu'elle est saisie, pour que l'apercu la refletent sans attendre un
    enregistrement. Le reste du contenu vient de la fiche produit (et de la
    fiche technique correspondante).
    """
    from app.services.etiquette_carton import (
        build_etiquette_spec, render_etiquette_svg, render_etiquette_pdf,
        etiquette_filename,
    )

    _require_ao(request)
    fmt = "pdf" if str(fmt).lower() == "pdf" else "svg"

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

        # Ref SIFA saisie dans le formulaire : elle prime sur celle enregistree,
        # y compris pour la recherche de fiche technique ci-dessous.
        ref_sifa = str(ref_sifa or "").strip()
        if ref_sifa:
            fiche = dict(fiche)
            fiche["ref_sifa"] = ref_sifa
        else:
            ref_sifa = str(fiche.get("ref_sifa") or produit.get("ref_sifa") or "").strip()

        # Libelles matieres — degradation propre si le schema differe.
        matieres_map = {}
        try:
            for mp in conn.execute("SELECT * FROM matieres_premieres").fetchall():
                d = _row_dict(mp)
                matieres_map[d.get("id")] = d
        except Exception:
            matieres_map = {}

        # Enrichissement fiche technique quand la Ref SIFA est renseignee.
        ft = None
        if ref_sifa:
            try:
                ft_row = conn.execute(
                    "SELECT * FROM fiches_techniques WHERE LOWER(TRIM(reference))=LOWER(TRIM(?)) LIMIT 1",
                    (ref_sifa,),
                ).fetchone()
                if ft_row:
                    ft = _row_dict(ft_row)
            except Exception:
                ft = None

    spec = build_etiquette_spec(
        produit, fiche,
        matieres_map=matieres_map,
        fiche_technique=ft,
        date_edition="/".join(reversed(_now_paris_iso()[:10].split("-"))),
    )

    if fmt == "pdf":
        return Response(
            content=render_etiquette_pdf(spec),
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{etiquette_filename(spec)}"'},
        )
    return Response(content=render_etiquette_svg(spec), media_type="image/svg+xml")


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
        produit_id = int(cur.lastrowid)

        # Réparation : des lignes d'AO peuvent déjà porter cette référence sans
        # produit rattaché (produit supprimé, AO dupliqué, import). Créer le
        # produit manquant les répare, et déclenche la génération de la fiche et
        # du BAT qui n'avaient jamais pu être produits.
        rattachees = conn.execute(
            """UPDATE ao_lignes SET produit_id=?
                WHERE produit_id IS NULL
                  AND LOWER(TRIM(COALESCE(ref_produit,''))) = LOWER(TRIM(?))""",
            (produit_id, ref),
        ).rowcount
        conn.commit()
        if rattachees:
            logger.info(
                "Produit %s créé : %s ligne(s) d'AO orpheline(s) rattachée(s).",
                ref, rattachees,
            )
            try:
                _regen_fiches_for_produit(conn, produit_id)
                conn.commit()
            except Exception:
                logger.exception("Regen PJ auto sur create produit %s échoué", produit_id)

        row = conn.execute("SELECT * FROM ao_produits WHERE id=?", (produit_id,)).fetchone()
        return _serialize_produit_row(_row_dict(row), conn)


@router.put("/produits/{produit_id}")
async def update_produit(request: Request, produit_id: int):
    _require_ao(request)
    body = await request.json()
    with get_db() as conn:
        ref, designation, unite, notes, client_id, fiche_json = _produit_from_body(body, conn)
        if _produit_ref_taken(conn, ref, exclude_id=produit_id):
            raise HTTPException(status_code=400, detail="Référence déjà utilisée.")
        ancienne = conn.execute(
            "SELECT ref FROM ao_produits WHERE id=?", (produit_id,)
        ).fetchone()
        ancienne_ref = str((ancienne["ref"] if ancienne else "") or "").strip()
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

        # Renommage : on resynchronise le libellé des lignes d'AO. Sans ça, les
        # lignes gardent l'ancienne référence — c'est ce qui rendait le produit
        # « introuvable » côté AO et privait le fournisseur de la fiche et du BAT.
        # Les AO clôturés sont laissés en l'état : ils doivent rester le reflet
        # de ce qui a réellement été envoyé.
        if ancienne_ref and ancienne_ref.lower() != ref.lower():
            conn.execute(
                """UPDATE ao_lignes SET ref_produit=?
                    WHERE ao_id IN (SELECT id FROM ao_demandes
                                     WHERE statut IN ('brouillon','envoyee')
                                       AND deleted_at IS NULL)
                      AND (produit_id = ?
                           OR (produit_id IS NULL
                               AND LOWER(TRIM(COALESCE(ref_produit,'')))
                                   = LOWER(TRIM(?))))""",
                (ref, produit_id, ancienne_ref),
            )
            # Rattache au passage les lignes restées sur du texte seul.
            conn.execute(
                """UPDATE ao_lignes SET produit_id=?
                    WHERE produit_id IS NULL
                      AND LOWER(TRIM(COALESCE(ref_produit,''))) = LOWER(TRIM(?))""",
                (produit_id, ref),
            )
            conn.commit()

        row = conn.execute("SELECT * FROM ao_produits WHERE id=?", (produit_id,)).fetchone()
        # Regénère les PJ auto (fiche + BAT) attachées aux AO ouverts qui
        # utilisent ce produit (brouillon ou envoyé, pas clôturé) — idempotent.
        try:
            _regen_fiches_for_produit(conn, produit_id, refs_obsoletes=(ancienne_ref,))
            conn.commit()
        except Exception:
            logger.exception("Regen PJ auto sur update produit %s échoué", produit_id)
        return _serialize_produit_row(_row_dict(row), conn)


def _regen_fiches_for_produit(
    conn, produit_id: int, refs_obsoletes: Sequence[str] = (),
) -> None:
    """Regénère les PJ auto (fiche fournisseur + BAT) de ce produit dans tous les
    AO ouverts qui l'utilisent. Ne touche pas aux AO clôturés.

    ``refs_obsoletes`` liste les anciennes références du produit : leurs PJ
    portent l'ancien nom de fichier et doivent être supprimées, sinon un
    renommage laisse en place un document périmé à côté du nouveau.
    """
    try:
        produit_id = int(produit_id)
    except (TypeError, ValueError):
        return
    row = conn.execute(
        "SELECT ref FROM ao_produits WHERE id=?", (produit_id,)
    ).fetchone()
    if not row:
        return
    ref_actuelle = str(row["ref"] or "").strip()

    # Les lignes rattachées par id ET celles encore rattachées par texte seul :
    # une base dont le backfill n'a rien trouvé doit quand même être régénérée.
    aos = conn.execute(
        """SELECT DISTINCT d.id, d.reference
           FROM ao_demandes d
           JOIN ao_lignes l ON l.ao_id = d.id
           WHERE (l.produit_id = ?
                  OR LOWER(TRIM(COALESCE(l.ref_produit,''))) = LOWER(TRIM(?)))
             AND d.statut IN ('brouillon', 'envoyee')
             AND d.deleted_at IS NULL""",
        (produit_id, ref_actuelle),
    ).fetchall()
    if not aos:
        return
    produits_map = _produits_by_ref_map(conn)
    now_iso = _now_paris_iso()
    slugs = {_auto_doc_ref_slug(r) for r in (ref_actuelle, *refs_obsoletes) if r}
    stale_names = [
        f"{prefix}{slug}.pdf"
        for slug in sorted(slugs)
        for prefix in AUTO_DOC_PREFIXES
    ]
    for ao in aos:
        # Supprime les PJ auto existantes pour cette ref (noms idempotents), afin
        # que _auto_attach_fournisseur_pdfs les régénère juste après.
        for fname in stale_names:
            pjs_to_del = conn.execute(
                "SELECT id, stored_name FROM ao_pieces_jointes"
                " WHERE ao_id=? AND filename=?",
                (int(ao["id"]), fname),
            ).fetchall()
            for pj in pjs_to_del:
                try:
                    path = os.path.join(_ao_upload_dir(int(ao["id"])), pj["stored_name"])
                    if os.path.exists(path):
                        os.remove(path)
                except OSError:
                    pass
            if pjs_to_del:
                conn.execute(
                    "DELETE FROM ao_pieces_jointes WHERE ao_id=? AND filename=?",
                    (int(ao["id"]), fname),
                )
        _auto_attach_fournisseur_pdfs(
            conn, int(ao["id"]), ao["reference"],
            [{"produit_id": produit_id, "ref_produit": ref_actuelle}],
            produits_map, now_iso,
        )


@router.delete("/produits/{produit_id}")
def delete_produit(request: Request, produit_id: int):
    _require_ao(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT ref FROM ao_produits WHERE id=?", (produit_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Produit introuvable")
        ref = str(row["ref"] or "").strip()

        # Un produit utilisé par un AO ouvert ne peut pas disparaître : sa
        # suppression orphelinerait les lignes, ferait tomber le client et les
        # étiq./bobine, et priverait le fournisseur de la fiche et du BAT — sans
        # aucune erreur visible. On refuse en nommant les AO concernés.
        utilisateurs = conn.execute(
            """SELECT DISTINCT d.reference
                 FROM ao_demandes d
                 JOIN ao_lignes l ON l.ao_id = d.id
                WHERE (l.produit_id = ?
                       OR (l.produit_id IS NULL
                           AND LOWER(TRIM(COALESCE(l.ref_produit,''))) = LOWER(TRIM(?))))
                  AND d.statut IN ('brouillon','envoyee')
                  AND d.deleted_at IS NULL
                ORDER BY d.reference""",
            (produit_id, ref),
        ).fetchall()
        if utilisateurs:
            refs = ", ".join(str(r["reference"]) for r in utilisateurs[:5])
            reste = len(utilisateurs) - 5
            if reste > 0:
                refs += f" et {reste} autre(s)"
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Produit utilisé par {len(utilisateurs)} appel(s) d'offres "
                    f"en cours ({refs}). Retirez-le de ces AO avant de le supprimer."
                ),
            )

        # AO clôturés : on garde la trace textuelle de ce qui a été envoyé, mais
        # on coupe le lien pour ne pas laisser un produit_id pendant.
        conn.execute(
            "UPDATE ao_lignes SET produit_id=NULL WHERE produit_id=?", (produit_id,)
        )
        conn.execute("DELETE FROM ao_produits WHERE id=?", (produit_id,))
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
    series_by_ligne: dict[int, list[dict]] | None = None,
) -> dict:
    """Ajoute client, étiq./bobine, séries depuis le catalogue et la DB."""
    produit = _resolve_produit_for_ligne(ln, produits_map)
    ctx = ligne_context_from_produit(
        ln.get("ref_produit") or "",
        ln.get("quantite"),
        produit,
        matieres_map,
    )
    ln["client_nom"] = ctx.get("client_nom")
    ln["etiquettes_par_bobine"] = ctx.get("etiquettes_par_bobine")
    # Ligne orpheline : une référence est saisie mais ne correspond à aucun
    # produit du catalogue. Le front affiche un badge, et l'envoi de l'AO est
    # bloqué — sans ce signal, le fournisseur reçoit un AO sans fiche ni BAT.
    ln["produit_id"] = (produit or {}).get("id") or ln.get("produit_id")
    ln["produit_introuvable"] = bool(
        (ln.get("ref_produit") or "").strip()
    ) and produit is None
    if produit:
        # La ligne affiche toujours la référence actuelle du produit, même si
        # ref_produit n'a pas encore été resynchronisé.
        ln["ref_produit"] = produit.get("ref") or ln.get("ref_produit")
    # Séries — la somme des quantités séries doit égaler la quantité ligne (contrôle applicatif)
    series = (series_by_ligne or {}).get(int(ln.get("id") or 0), [])
    ln["series"] = series
    try:
        ln["series_qty_sum"] = sum(float(s.get("quantite") or 0) for s in series)
    except Exception:
        ln["series_qty_sum"] = 0.0
    return ln


def _load_series_by_ligne(conn, ligne_ids: list[int]) -> dict[int, list[dict]]:
    if not ligne_ids:
        return {}
    qmarks = ",".join("?" * len(ligne_ids))
    rows = conn.execute(
        f"""SELECT * FROM ao_lignes_series
            WHERE ligne_id IN ({qmarks})
            ORDER BY ligne_id, position, id""",
        tuple(ligne_ids),
    ).fetchall()
    out: dict[int, list[dict]] = {}
    for r in rows:
        d = _row_dict(r)
        out.setdefault(int(d["ligne_id"]), []).append(d)
    return out


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
        engagement = ao_ev.resume_par_fournisseur(conn, ao_id)
        produits_map = _produits_by_ref_map(conn)
        mat_ids = _matiere_ids_from_produits(produits_map)
        matieres_map = _load_matieres_map(conn, mat_ids or None)
        ligne_ids = [int(r["id"]) for r in lignes_rows]
        series_by_ligne = _load_series_by_ligne(conn, ligne_ids)
        lignes = [
            _enrich_ligne_display(_row_dict(r), produits_map, matieres_map, series_by_ligne)
            for r in lignes_rows
        ]
    fournis_out = []
    for r in fournisseurs:
        d = _row_dict(r)
        # Le token de pixel ne sort jamais de l'API : c'est un identifiant de
        # suivi, il n'a rien à faire dans le JSON d'une page d'administration.
        d.pop("token_pixel", None)
        d["engagement"] = engagement.get(int(d["id"]), {})
        fournis_out.append(d)

    return {
        "ao": ao,
        "lignes": lignes,
        "fournisseurs": fournis_out,
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
        # Un titre envoyé explicitement et différent de celui dérivé des lignes
        # est un choix de l'utilisateur : on le protège de _regen_titre_ao.
        # `titre_manuel: false` dans le body permet de repasser en automatique.
        titre_manuel = int(ao.get("titre_manuel") or 0)
        if "titre_manuel" in body:
            titre_manuel = 1 if body.get("titre_manuel") else 0
        elif (body.get("titre") or "").strip() and titre != (ao.get("titre") or "").strip():
            titre_manuel = 1
        conn.execute(
            """UPDATE ao_demandes
               SET titre=?, titre_manuel=?, description=?, date_limite=?, responsable_email=?
               WHERE id=?""",
            (
                titre,
                titre_manuel,
                (body.get("description") or "").strip() or None,
                (body.get("date_limite") or "").strip() or None,
                (body.get("responsable_email") or "").strip() or None,
                ao_id,
            ),
        )
        if not titre_manuel:
            _regen_titre_ao(conn, ao_id)
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
                detail="Cloture impossible : l'appel d'offres doit etre au statut envoyee.",
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
        px_retenu = None
        if fourni_retenu is not None:
            px_retenu = ao_ev.url_pixel(
                ao_ev.token_pixel(conn, int(fourni_retenu["id"])), "attr"
            )
        conn.commit()
        updated = _get_ao_or_404(conn, ao_id)

    if fourni_retenu:
        try:
            subject, html_body = email_offre_retenue(
                dict(updated),
                dict(fourni_retenu),
                message_perso=message_perso,
                pixel_url=px_retenu,
            )
            ok = send_email(fourni_retenu["email_contact"], subject, html_body)
            if ok:
                with get_db() as conn2:
                    ao_ev.log_evenement(
                        conn2,
                        ao_fournisseur_id=int(fourni_retenu["id"]),
                        ao_id=ao_id,
                        canal=ao_ev.CANAL_EMAIL,
                        type_evenement=ao_ev.EV_EMAIL_ATTRIBUTION,
                        date=now,
                        meta={"suivi": bool(px_retenu)},
                    )
                    conn2.commit()
        except Exception as e:
            logger.warning("Envoi email offre retenue echoue pour AO %s: %s", ao_id, e)

    return updated


@router.delete("/{ao_id}")
def delete_ao(request: Request, ao_id: int):
    """Soft-delete : deplace l'AO dans la corbeille (deleted_at = now).
    Pour supprimer definitivement : voir DELETE /{ao_id}/definitif."""
    _require_ao(request)
    now = _now_paris_iso()
    with get_db() as conn:
        row = conn.execute("SELECT id, deleted_at FROM ao_demandes WHERE id=?", (ao_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="AO introuvable.")
        conn.execute("UPDATE ao_demandes SET deleted_at=? WHERE id=?", (now, ao_id))
        conn.commit()
    return {"ok": True, "ao_id": ao_id, "deleted_at": now}


@router.post("/{ao_id}/restaurer")
def restaurer_ao(request: Request, ao_id: int):
    """Restaure un AO de la corbeille."""
    _require_ao(request)
    with get_db() as conn:
        row = conn.execute("SELECT id FROM ao_demandes WHERE id=? AND deleted_at IS NOT NULL", (ao_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="AO non trouve dans la corbeille.")
        conn.execute("UPDATE ao_demandes SET deleted_at=NULL WHERE id=?", (ao_id,))
        conn.commit()
    return {"ok": True, "ao_id": ao_id}


@router.delete("/{ao_id}/definitif")
def delete_ao_definitif(request: Request, ao_id: int):
    """Suppression definitive (uniquement si deja dans la corbeille)."""
    user = _require_ao(request)
    with get_db() as conn:
        row = conn.execute("SELECT id FROM ao_demandes WHERE id=? AND deleted_at IS NOT NULL", (ao_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="AO doit d'abord etre dans la corbeille.")
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
    """Duplique un appel d'offres. Le nouveau AO est en statut 'brouillon'.

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
               (reference, titre, titre_manuel, description, date_creation, date_limite,
                statut, created_by, responsable_email, prix_transport_pct)
               VALUES (?,?,?,?,?,?,'brouillon',?,?,?)""",
            (
                new_ref,
                new_titre,
                # Un titre explicitement demandé est protégé de la régénération.
                # Sinon le « (copie) » n'est qu'un provisoire : le titre définitif
                # est recalculé depuis les lignes juste après leur copie.
                1 if titre_override else 0,
                src.get("description"),
                now,
                src.get("date_limite"),
                user.get("id"),
                src.get("responsable_email"),
                # Le % de transport est un paramètre de chiffrage de l'AO, pas une
                # donnée de réponse : le remettre à 0 obligeait à le ressaisir à
                # chaque duplication, avec un risque d'oubli silencieux.
                float(src.get("prix_transport_pct") or 0),
            ),
        )
        new_id = cur.lastrowid

        # Copie des lignes. produit_id est repris tel quel : la copie reste
        # rattachée au même produit du catalogue même si sa référence a changé
        # depuis. On resynchronise au passage le libellé sur la référence
        # actuelle du produit, pour ne pas naître avec une ref périmée.
        src_lignes = conn.execute(
            """SELECT l.*, p.ref AS produit_ref
                 FROM ao_lignes l
                 LEFT JOIN ao_produits p ON p.id = l.produit_id
                WHERE l.ao_id=? ORDER BY l.position, l.id""",
            (ao_id,),
        ).fetchall()
        # Séries : perdues jusqu'ici, alors qu'elles portent le découpage
        # quantitatif qu'on veut justement rejouer d'un AO sur l'autre.
        series_src = _load_series_by_ligne(
            conn, [int(ln["id"]) for ln in src_lignes]
        )
        for ln in src_lignes:
            new_ligne = conn.execute(
                """INSERT INTO ao_lignes
                   (ao_id, produit_id, ref_produit, designation, quantite, unite,
                    notes, position, condi_unite, condi_qte)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    new_id,
                    ln["produit_id"],
                    ln["produit_ref"] or ln["ref_produit"],
                    ln["designation"],
                    ln["quantite"],
                    ln["unite"],
                    ln["notes"],
                    ln["position"],
                    ln["condi_unite"] if "condi_unite" in ln.keys() else None,
                    ln["condi_qte"] if "condi_qte" in ln.keys() else None,
                ),
            )
            for serie in series_src.get(int(ln["id"]), []):
                conn.execute(
                    """INSERT INTO ao_lignes_series
                       (ligne_id, position, libelle, quantite, notes, created_at)
                       VALUES (?,?,?,?,?,?)""",
                    (
                        int(new_ligne.lastrowid),
                        serie.get("position") or 0,
                        serie.get("libelle") or "",
                        serie.get("quantite") or 0,
                        serie.get("notes"),
                        now,
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
                keys = f.keys()
                conn.execute(
                    """INSERT INTO ao_fournisseurs
                       (ao_id, nom_fournisseur, email_contact, token, statut, langue,
                        fournisseur_id, fournisseur_contact_id)
                       VALUES (?,?,?,?,'invite',?,?,?)""",
                    (
                        new_id,
                        f["nom_fournisseur"],
                        f["email_contact"],
                        str(uuid.uuid4()),
                        src_langue,
                        # Liens vers le référentiel Paramètres > Fournisseurs :
                        # sans eux, la copie n'était plus qu'un nom et un email
                        # détachés de la fiche fournisseur.
                        f["fournisseur_id"] if "fournisseur_id" in keys else None,
                        f["fournisseur_contact_id"] if "fournisseur_contact_id" in keys else None,
                    ),
                )

        # Titre définitif de la copie : dérivé de ses lignes, comme n'importe quel
        # AO. Sans cet appel, la copie gardait « … (copie) » jusqu'à la première
        # modification de ligne, qui l'écrasait ensuite sans prévenir.
        if not titre_override:
            _regen_titre_ao(conn, new_id)
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

def _regen_titre_ao(conn, ao_id: int) -> None:
    """Régénère le titre de l'AO à partir de ses lignes (refs concaténées).

    Appelé après chaque INSERT/UPDATE/DELETE sur ao_lignes. Respecte les titres
    saisis à la main (ao_demandes.titre_manuel = 1) : sans ce garde-fou, un titre
    voulu — dont le « (copie) » d'une duplication — était écrasé dès la première
    modification de ligne.
    """
    manuel = conn.execute(
        "SELECT COALESCE(titre_manuel, 0) AS m FROM ao_demandes WHERE id=?",
        (ao_id,),
    ).fetchone()
    if manuel and int(manuel["m"] or 0):
        return
    # La référence affichée suit le produit rattaché quand il existe, pour que le
    # titre reste juste après un renommage.
    refs = [
        str(r["ref"] or "").strip()
        for r in conn.execute(
            """SELECT COALESCE(p.ref, l.ref_produit) AS ref
                 FROM ao_lignes l
                 LEFT JOIN ao_produits p ON p.id = l.produit_id
                WHERE l.ao_id=? ORDER BY l.position, l.id""",
            (ao_id,),
        ).fetchall()
    ]
    refs = [r for r in refs if r]
    titre = " · ".join(refs) if refs else "Nouvel appel d'offres"
    conn.execute("UPDATE ao_demandes SET titre=? WHERE id=?", (titre, ao_id))


def _resolve_ligne_produit_ref(
    conn, produit_id_raw: Any, ref_produit: str,
) -> tuple[int | None, str]:
    """Détermine le couple (produit_id, ref_produit) à stocker sur une ligne d'AO.

    Le front peut envoyer un ``produit_id`` (choix dans le catalogue) et/ou une
    ``ref_produit`` (saisie libre, ou payload historique). On privilégie l'id ;
    à défaut on tente de retrouver le produit par sa référence. La référence
    stockée est celle du produit résolu, pour que le libellé de la ligne ne
    puisse pas naître déjà désynchronisé.
    """
    produit_id: int | None = None
    try:
        if produit_id_raw is not None and str(produit_id_raw).strip() != "":
            produit_id = int(produit_id_raw)
    except (TypeError, ValueError):
        produit_id = None

    row = None
    if produit_id is not None:
        row = conn.execute(
            "SELECT id, ref FROM ao_produits WHERE id=?", (produit_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=400, detail="Produit introuvable.")
    elif ref_produit:
        # Comparaison en Python (_ref_key) et non en SQL : LOWER() de SQLite ne
        # replie pas les accents, et « 15 x 10 mm Couché » ne se serait pas
        # rattaché à « 15 x 10 mm couché ».
        key = _ref_key(ref_produit)
        for cand in conn.execute("SELECT id, ref FROM ao_produits ORDER BY id").fetchall():
            if _ref_key(cand["ref"]) == key:
                row = cand
                break

    if row is not None:
        return int(row["id"]), (row["ref"] or ref_produit)
    # Référence hors catalogue : accepté (saisie libre historique), mais la ligne
    # sera signalée « produit introuvable ».
    return None, ref_produit


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
        produit_id, ref_produit = _resolve_ligne_produit_ref(
            conn, body.get("produit_id"), ref_produit,
        )
        row = conn.execute(
            "SELECT COALESCE(MAX(position), -1) AS m FROM ao_lignes WHERE ao_id=?",
            (ao_id,),
        ).fetchone()
        position = int(row["m"]) + 1
        cur = conn.execute(
            """INSERT INTO ao_lignes
               (ao_id, produit_id, ref_produit, designation, quantite, unite, notes, position)
               VALUES (?,?,?,?,?,?,?,?)""",
            (ao_id, produit_id, ref_produit, designation, quantite, unite, notes, position),
        )
        _regen_titre_ao(conn, ao_id)
        conn.commit()
        ligne = conn.execute(
            "SELECT * FROM ao_lignes WHERE id=?", (cur.lastrowid,)
        ).fetchone()
        # Auto-attach : génère la fiche technique fournisseur et le BAT
        # étiquette de ce produit dès l'ajout de la ligne (pas seulement à
        # l'envoi), pour qu'on puisse les relire avant de partir.
        try:
            now_iso = _now_paris_iso()
            produits_map = _produits_by_ref_map(conn)
            _auto_attach_fournisseur_pdfs(
                conn, ao_id, ao.get("reference"),
                [{"produit_id": produit_id, "ref_produit": ref_produit}],
                produits_map, now_iso,
            )
            conn.commit()
        except Exception:
            logger.exception("Auto-attach fiche PDF à l'ajout ligne échoué (AO %s)", ao_id)
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
        produit_id, ref_produit = _resolve_ligne_produit_ref(
            conn, body.get("produit_id"), ref_produit,
        )
        conn.execute(
            """UPDATE ao_lignes
               SET produit_id=?, ref_produit=?, designation=?, quantite=?, unite=?, notes=?
               WHERE id=? AND ao_id=?""",
            (produit_id, ref_produit, designation, quantite, unite, notes,
             ligne_id, ao_id),
        )
        _regen_titre_ao(conn, ao_id)
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
        _regen_titre_ao(conn, ao_id)
        conn.commit()
    return {"ok": True}


# ─── Séries ────────────────────────────────────────────────────────
# Une ligne d'AO peut être déclinée en plusieurs séries (même produit,
# légère variation — souvent d'impression). La somme des quantités des
# séries doit égaler la quantité de la ligne mère (contrôle applicatif :
# on renvoie series_qty_sum et le front peut avertir).

def _get_ligne_or_404(conn, ao_id: int, ligne_id: int) -> dict:
    row = conn.execute(
        "SELECT * FROM ao_lignes WHERE id=? AND ao_id=?",
        (ligne_id, ao_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Ligne introuvable")
    return _row_dict(row)


CONDI_UNITES = frozenset({"mille", "bobine", "carton", "etiquette", "palette"})


@router.patch("/{ao_id}/lignes/{ligne_id}/condi")
async def update_ligne_condi(request: Request, ao_id: int, ligne_id: int):
    """Met à jour le conditionnement de vente (unité + quantité) sur une ligne."""
    _require_ao(request)
    body = await request.json()
    unite = body.get("condi_unite")
    qte = body.get("condi_qte")
    if unite is not None:
        unite = (unite or "").strip().lower() or None
        if unite and unite not in CONDI_UNITES:
            raise HTTPException(status_code=400, detail="Unité condi invalide.")
    if qte is not None and qte != "":
        try:
            qte = float(qte)
            if qte <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Quantité condi invalide.")
    else:
        qte = None
    with get_db() as conn:
        _get_ao_or_404(conn, ao_id)
        _get_ligne_or_404(conn, ao_id, ligne_id)
        conn.execute(
            "UPDATE ao_lignes SET condi_unite=?, condi_qte=? WHERE id=? AND ao_id=?",
            (unite, qte, ligne_id, ao_id),
        )
        conn.commit()
    return {"ok": True, "ligne_id": ligne_id, "condi_unite": unite, "condi_qte": qte}


def _load_series_for_ligne(conn, ligne_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM ao_lignes_series WHERE ligne_id=? ORDER BY position, id",
        (ligne_id,),
    ).fetchall()
    return [_row_dict(r) for r in rows]


@router.post("/{ao_id}/lignes/{ligne_id}/series")
async def create_serie(request: Request, ao_id: int, ligne_id: int):
    _require_ao(request)
    body = await request.json()
    libelle = (body.get("libelle") or "").strip()
    if not libelle:
        raise HTTPException(status_code=400, detail="Libellé obligatoire.")
    try:
        quantite = float(body.get("quantite") or 0)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Quantité invalide.")
    if quantite < 0:
        raise HTTPException(status_code=400, detail="Quantité invalide.")
    notes = (body.get("notes") or "").strip() or None
    now = _now_paris_iso()
    with get_db() as conn:
        ao = _get_ao_or_404(conn, ao_id)
        _get_ligne_or_404(conn, ao_id, ligne_id)
        # AO envoyée : bloqué (les fournisseurs ont déjà répondu peut-être)
        if ao.get("statut") not in ("brouillon", "envoyee"):
            raise HTTPException(status_code=400, detail="AO clôturé — impossible d'ajouter une série.")
        pos_row = conn.execute(
            "SELECT COALESCE(MAX(position), -1) AS m FROM ao_lignes_series WHERE ligne_id=?",
            (ligne_id,),
        ).fetchone()
        position = int(pos_row["m"]) + 1
        cur = conn.execute(
            """INSERT INTO ao_lignes_series
               (ligne_id, position, libelle, quantite, notes, created_at)
               VALUES (?,?,?,?,?,?)""",
            (ligne_id, position, libelle, quantite, notes, now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM ao_lignes_series WHERE id=?", (cur.lastrowid,)
        ).fetchone()
    return _row_dict(row)


@router.put("/{ao_id}/lignes/{ligne_id}/series/{serie_id}")
async def update_serie(request: Request, ao_id: int, ligne_id: int, serie_id: int):
    _require_ao(request)
    body = await request.json()
    libelle = (body.get("libelle") or "").strip()
    if not libelle:
        raise HTTPException(status_code=400, detail="Libellé obligatoire.")
    try:
        quantite = float(body.get("quantite") or 0)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Quantité invalide.")
    if quantite < 0:
        raise HTTPException(status_code=400, detail="Quantité invalide.")
    notes = (body.get("notes") or "").strip() or None
    with get_db() as conn:
        ao = _get_ao_or_404(conn, ao_id)
        _get_ligne_or_404(conn, ao_id, ligne_id)
        if ao.get("statut") == "cloturee":
            raise HTTPException(status_code=400, detail="AO clôturé — édition impossible.")
        cur = conn.execute(
            """UPDATE ao_lignes_series
               SET libelle=?, quantite=?, notes=?
               WHERE id=? AND ligne_id=?""",
            (libelle, quantite, notes, serie_id, ligne_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Série introuvable")
        conn.commit()
        row = conn.execute(
            "SELECT * FROM ao_lignes_series WHERE id=?", (serie_id,)
        ).fetchone()
    return _row_dict(row)


@router.delete("/{ao_id}/lignes/{ligne_id}/series/{serie_id}")
def delete_serie(request: Request, ao_id: int, ligne_id: int, serie_id: int):
    _require_ao(request)
    with get_db() as conn:
        ao = _get_ao_or_404(conn, ao_id)
        _get_ligne_or_404(conn, ao_id, ligne_id)
        if ao.get("statut") == "cloturee":
            raise HTTPException(status_code=400, detail="AO clôturé — suppression impossible.")
        # Les réponses fournisseur liées à cette série sont détachées (serie_id → NULL)
        conn.execute(
            "UPDATE ao_reponses SET serie_id=NULL WHERE serie_id=?",
            (serie_id,),
        )
        cur = conn.execute(
            "DELETE FROM ao_lignes_series WHERE id=? AND ligne_id=?",
            (serie_id, ligne_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Série introuvable")
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
    d = _row_dict(row)
    d.pop("token_pixel", None)
    return d


@router.get("/{ao_id}/fournisseurs/{fourni_id}/evenements")
def evenements_fournisseur(request: Request, ao_id: int, fourni_id: int):
    """Timeline d'engagement d'un fournisseur : email, portail, et plus tard WhatsApp."""
    _require_ao(request)
    with get_db() as conn:
        _get_ao_or_404(conn, ao_id)
        fourni = _get_fourni_in_ao(conn, ao_id, fourni_id)
        evts = ao_ev.timeline(conn, fourni_id)
    return {
        "fournisseur": {
            "id": fourni_id,
            "nom": fourni.get("nom_fournisseur"),
            "email": fourni.get("email_contact"),
            "date_envoi": fourni.get("date_envoi"),
        },
        "evenements": evts,
    }


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

# Noms logiques des PJ auto-générées. Le préfixe sert de clé d'idempotence et
# de clé de suppression lors d'une régénération : il ne doit jamais changer sans
# migration des lignes ao_pieces_jointes existantes.
AUTO_DOC_FICHE_PREFIX = "fiche_fournisseur_"
AUTO_DOC_BAT_PREFIX = "bat_"

# Valeurs de ao_pieces_jointes.uploaded_by identifiant une PJ auto-générée.
AUTO_DOC_KIND_FICHE = "auto-fiche-produit"
AUTO_DOC_KIND_BAT = "auto-bat-produit"

AUTO_DOC_PREFIXES = (AUTO_DOC_FICHE_PREFIX, AUTO_DOC_BAT_PREFIX)


def _auto_doc_ref_slug(ref: str) -> str:
    """Fragment de nom de fichier dérivé d'une réf produit. Doit rester stable."""
    return re.sub(r"[^\w\-]+", "_", (ref or "").split(" - ")[0])


def _build_fiche_fournisseur_bytes(conn, prod_full, mp_map, ao_reference):
    from app.services.fiche_pdf_fournisseur import generate_fiche_fournisseur_pdf

    return generate_fiche_fournisseur_pdf(
        prod_full, matieres_map=mp_map, ao_reference=ao_reference,
    )


def _build_bat_bytes(conn, prod_full, mp_map, ao_reference):
    """BAT étiquette du produit, en français, avec bandeau « croquis automatique ».

    Le bandeau est bilingue (cf. bat_etiquette.TEXTS), donc un fournisseur
    anglophone lit l'avertissement même si le cartouche est en français : on
    évite ainsi un appel de traduction DeepL à chaque ajout de ligne d'AO.
    """
    from app.services.bat_etiquette import build_bat_spec, render_bat_pdf

    fiche = prod_full.get("fiche") or {}

    # Fiche technique SIFA, quand la Ref SIFA est renseignée : elle est
    # prioritaire sur la fiche produit pour la géométrie (même règle que
    # l'endpoint /produits/{id}/bat).
    ft = None
    ref_sifa = str(fiche.get("ref_sifa") or prod_full.get("ref_sifa") or "").strip()
    if ref_sifa:
        try:
            ft_row = conn.execute(
                "SELECT * FROM fiches_techniques"
                " WHERE LOWER(TRIM(reference))=LOWER(TRIM(?)) LIMIT 1",
                (ref_sifa,),
            ).fetchone()
            if ft_row:
                ft = _row_dict(ft_row)
        except Exception:
            ft = None

    spec = build_bat_spec(
        prod_full, fiche,
        matieres_map=mp_map,
        fiche_technique=ft,
        client_nom=prod_full.get("client_nom") or "",
        ref_interne=prod_full.get("ref") or "",
        date_bat="/".join(reversed(_now_paris_iso()[:10].split("-"))),
        lang="fr",
    )
    # Sans laize ni longueur il n'y a pas de plan à dessiner : mieux vaut aucune
    # PJ qu'un croquis d'une étiquette de 0,1 mm que le fournisseur croirait réel.
    if not (_f_or_zero(spec.get("laize")) > 0 and _f_or_zero(spec.get("longueur")) > 0):
        return None
    return render_bat_pdf(spec, "fr")


def _f_or_zero(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _fournisseur_doc_generators() -> list[tuple[str, str, Any]]:
    """(kind, préfixe de nom de fichier, fabricant) pour chaque PJ auto-générée."""
    out: list[tuple[str, str, Any]] = []
    try:
        import app.services.fiche_pdf_fournisseur  # noqa: F401

        out.append((AUTO_DOC_KIND_FICHE, AUTO_DOC_FICHE_PREFIX,
                    _build_fiche_fournisseur_bytes))
    except ImportError:
        logger.warning("fiche_pdf_fournisseur indisponible, fiche auto ignorée.")
    try:
        import app.services.bat_etiquette  # noqa: F401

        out.append((AUTO_DOC_KIND_BAT, AUTO_DOC_BAT_PREFIX, _build_bat_bytes))
    except ImportError:
        logger.warning("bat_etiquette indisponible, BAT auto ignoré.")
    return out


def _auto_attach_fournisseur_pdfs(
    conn,
    ao_id: int,
    ao_reference: str | None,
    lignes_raw: list[dict],
    produits_map: dict[str, dict],
    now_iso: str,
) -> None:
    """
    Génère, pour chaque produit référencé dans l'AO, les documents fournisseur
    et les insère dans `ao_pieces_jointes` :

      - `fiche_fournisseur_<ref>.pdf` — fiche technique bilingue
      - `bat_<ref>.pdf`              — BAT étiquette (plan technique A4)

    Appelé à l'ajout d'une ligne, à l'envoi de l'AO et au premier accès portail
    (rattrapage) — les PDFs apparaissent dans l'onglet Documents du portail.

    Idempotent : un document dont le nom logique est déjà présent n'est pas
    recréé, ce qui permet de relancer l'envoi sans dupliquer les pièces jointes.
    L'échec d'un document n'empêche pas les autres : chaque génération est
    isolée, l'AO part même si un BAT n'a pas pu être dessiné.
    """
    generators = _fournisseur_doc_generators()
    if not generators:
        return

    # Produits uniques réellement rattachés aux lignes de l'AO. On résout par
    # produit_id d'abord : une ligne dont la ref a été renommée doit continuer
    # de produire sa fiche et son BAT.
    produits: dict[int, dict] = {}
    for ln in lignes_raw:
        produit = _resolve_produit_for_ligne(ln, produits_map)
        if produit and produit.get("id"):
            produits[int(produit["id"])] = produit
    if not produits:
        return

    # Pièces jointes déjà présentes (pour l'idempotence)
    existing = {
        r["filename"]
        for r in conn.execute(
            "SELECT filename FROM ao_pieces_jointes WHERE ao_id=?", (ao_id,)
        ).fetchall()
    }

    dest_dir = _ao_upload_dir(ao_id)

    for produit in sorted(produits.values(), key=lambda p: str(p.get("ref") or "")):
        ref = str(produit.get("ref") or "").strip()
        if not ref:
            continue

        ref_clean = _auto_doc_ref_slug(ref)
        wanted = [
            (kind, fname, build)
            for kind, suffix, build in generators
            for fname in (f"{suffix}{ref_clean}.pdf",)
            if fname not in existing
        ]
        if not wanted:
            continue

        # Recharge le produit avec client_nom (comme dans /export)
        row = conn.execute(
            """SELECT p.*,
                      COALESCE(cg.raison_sociale, lc.nom) AS client_nom
               FROM ao_produits p
               LEFT JOIN clients            cg ON cg.id = p.client_id
               LEFT JOIN ao_carnet_clients  lc ON lc.id = p.client_id
               WHERE p.id=?""",
            (int(produit["id"]),),
        ).fetchone()
        if not row:
            continue
        prod_full = _serialize_produit_row(_row_dict(row), conn)

        # Matières map pour ce produit uniquement
        fiche = prod_full.get("fiche") or {}
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

        for kind, filename, build in wanted:
            try:
                pdf_bytes = build(conn, prod_full, mp_map, ao_reference)
            except Exception:
                logger.exception(
                    "Échec génération %s pour produit %s (AO %s)",
                    kind, ref, ao_reference,
                )
                continue
            if not pdf_bytes:
                continue

            stored_name = str(uuid.uuid4()) + ".pdf"
            dest_path = os.path.join(dest_dir, stored_name)
            try:
                with open(dest_path, "wb") as f:
                    f.write(pdf_bytes)
            except OSError:
                logger.exception("Écriture %s impossible : %s", kind, dest_path)
                continue

            conn.execute(
                """INSERT INTO ao_pieces_jointes
                   (ao_id, filename, stored_name, taille_octets, uploaded_by, date)
                   VALUES (?,?,?,?,?,?)""",
                (ao_id, filename, stored_name, len(pdf_bytes), kind, now_iso),
            )


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
                detail="Envoi impossible — l'appel d'offres est clôturé.",
            )
        lignes_raw = [
            _row_dict(r)
            for r in conn.execute(
                "SELECT produit_id, ref_produit, designation, quantite, unite"
                " FROM ao_lignes WHERE ao_id=? ORDER BY position, id",
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

        # Garde-fou : une ligne sans produit rattaché part chez le fournisseur
        # sans fiche technique ni BAT, et sans étiq./bobine dans le tableau de
        # réponse. Mieux vaut refuser l'envoi que laisser partir une demande
        # incomplète que le fournisseur ne pourra pas chiffrer.
        orphelines = [
            str(ln.get("ref_produit") or "?")
            for ln in lignes if ln.get("produit_introuvable")
        ]
        if orphelines:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Envoi impossible — "
                    f"{len(orphelines)} ligne(s) ne correspondent à aucun produit "
                    f"du catalogue : {', '.join(orphelines[:5])}"
                    + (" …" if len(orphelines) > 5 else "")
                    + ". Créez le produit manquant ou corrigez la ligne : sans lui,"
                    " le fournisseur ne reçoit ni fiche technique ni BAT."
                ),
            )

        fournisseurs = conn.execute(
            """SELECT * FROM ao_fournisseurs
               WHERE ao_id=? AND statut='invite' AND date_envoi IS NULL""",
            (ao_id,),
        ).fetchall()

        # ── Auto-attach : génère la fiche technique fournisseur et le BAT
        # étiquette de chaque produit de l'AO, et les insère dans
        # ao_pieces_jointes (visibles côté portail dans l'onglet Documents).
        # Idempotent : ne recrée pas les PDFs déjà attachés lors d'un envoi
        # précédent (détecté par nom de fichier, cf. AUTO_DOC_PREFIXES).
        _auto_attach_fournisseur_pdfs(conn, ao_id, ao.get("reference"),
                                      lignes_raw, produits_map, now)

        for row in fournisseurs:
            fourni = _row_dict(row)
            lien = f"{BASE_URL.rstrip('/')}/portail/ao/{fourni['token']}"
            # Pixel de suivi d'ouverture : token dédié, créé à la volée pour les
            # fournisseurs antérieurs à la colonne. Si sa génération échoue,
            # l'email part quand même — sans suivi, mais il part.
            px = ao_ev.url_pixel(ao_ev.token_pixel(conn, int(fourni["id"])), "inv")
            subject, html_body = email_invitation_ao(ao, fourni, lien, lignes, pixel_url=px)
            ok = send_email(fourni["email_contact"], subject, html_body)
            if ok:
                conn.execute(
                    "UPDATE ao_fournisseurs SET date_envoi=? WHERE id=?",
                    (now, fourni["id"]),
                )
                envoyes += 1
                ao_ev.log_evenement(
                    conn,
                    ao_fournisseur_id=int(fourni["id"]),
                    ao_id=ao_id,
                    canal=ao_ev.CANAL_EMAIL,
                    type_evenement=ao_ev.EV_EMAIL_ENVOYE,
                    date=now,
                    meta={"destinataire": fourni.get("email_contact"),
                          "suivi": bool(px)},
                )
            else:
                erreurs += 1
                ao_ev.log_evenement(
                    conn,
                    ao_fournisseur_id=int(fourni["id"]),
                    ao_id=ao_id,
                    canal=ao_ev.CANAL_EMAIL,
                    type_evenement=ao_ev.EV_EMAIL_ECHEC,
                    date=now,
                    fiable=False,
                    motif="envoi refusé par le fournisseur d'email",
                    meta={"destinataire": fourni.get("email_contact")},
                )
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
        # Ce mail est, en pratique, la relance d'un fournisseur silencieux :
        # savoir s'il a été ouvert vaut autant que pour l'invitation.
        px_msg = ao_ev.url_pixel(ao_ev.token_pixel(conn, int(fourni_id)), "msg")
        conn.commit()
        inserted = conn.execute(
            "SELECT * FROM ao_messages WHERE rowid=last_insert_rowid()"
        ).fetchone()

    reference = ao.get("reference") or ""
    lien = f"{BASE_URL.rstrip('/')}/portail/ao/{fourni['token']}"
    subject, html_body = email_message_fournisseur(
        reference,
        message,
        lien,
        langue=fourni.get("langue") or "fr",
        pixel_url=px_msg,
    )
    if send_email(fourni["email_contact"], subject, html_body):
        with get_db() as conn2:
            ao_ev.log_evenement(
                conn2,
                ao_fournisseur_id=int(fourni_id),
                ao_id=ao_id,
                canal=ao_ev.CANAL_EMAIL,
                type_evenement=ao_ev.EV_EMAIL_MESSAGE,
                date=now,
                meta={"suivi": bool(px_msg), "auteur": auteur},
            )
            conn2.commit()

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
        _ao_pct_row = conn.execute(
            "SELECT COALESCE(prix_transport_pct, 0) AS pct FROM ao_demandes WHERE id=?",
            (ao_id,),
        ).fetchone()
        transport_pct = float(_ao_pct_row[0]) if _ao_pct_row else 0.0

        ligne_ids_all = [int(r["id"]) for r in lignes_rows]
        series_by_ligne = _load_series_by_ligne(conn, ligne_ids_all)
        lignes_out: list[dict[str, Any]] = []
        rows_flat: list[dict[str, Any]] = []
        for ln_row in lignes_rows:
            ln = _row_dict(ln_row)
            produit = _resolve_produit_for_ligne(ln, produits_map)
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
                              r.unite_quotation_original,
                              CASE WHEN COALESCE(r.unite_quotation_original, r.unite_quotation) != r.unite_quotation THEN 1 ELSE 0 END AS unite_manuel,
                              r.coef, r.marge, r.devise_prix_devis,
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
                        enrich_reponse_pricing(raw, ctx, eur_usd_rate=eur_usd, transport_pct=transport_pct)
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
            series_list = series_by_ligne.get(int(ln["id"]), [])
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
                "series": series_list,
            }
            lignes_out.append(ligne_out)
            for f in fournisseurs:
                fid = int(f["id"])
                raw = rep_by_fourni.get(fid)
                if raw:
                    rep = enrich_reponse_pricing(raw, ctx, eur_usd_rate=eur_usd, transport_pct=transport_pct)
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
                            "marge": 1.0,
                            "devise_prix_devis": "EUR",
                        },
                        ctx,
                        eur_usd_rate=eur_usd,
                        transport_pct=transport_pct,
                    )
                # Détail par série — prix calculé + prix vente pour chaque série
                # (utile pour l'affichage sous-ligne dans le comparateur)
                series_breakdown: list[dict[str, Any]] = []
                for s in series_list:
                    s_ctx = dict(ctx)
                    s_ctx["quantite_etiquettes"] = float(s.get("quantite") or 0)
                    s_rep = enrich_reponse_pricing(
                        dict(raw) if raw else {
                            "reponse_id": None,
                            "quotation": None,
                            "devise": rep.get("devise"),
                            "unite_quotation": rep.get("unite_quotation"),
                            "coef": rep.get("coef", 1.0),
                            "devise_prix_devis": rep.get("devise_prix_devis"),
                        },
                        s_ctx,
                        eur_usd_rate=eur_usd,
                        transport_pct=transport_pct,
                    )
                    series_breakdown.append({
                        "id": s.get("id"),
                        "libelle": s.get("libelle"),
                        "quantite": s.get("quantite"),
                        "notes": s.get("notes"),
                        "prix_calcule": s_rep.get("prix_calcule"),
                        "transport_amount": s_rep.get("transport_amount"),
                        "prix_vente": s_rep.get("prix_vente"),
                    })
                rows_flat.append({
                    "ligne_id": ln["id"],
                    "reponse_id": rep.get("reponse_id"),
                    "fourni_id": rep.get("fourni_id"),
                    "nom_fournisseur": rep.get("nom_fournisseur"),
                    **ctx,
                    **{k: rep.get(k) for k in (
                        "quotation", "devise", "unite_quotation", "unite_quotation_original", "unite_manuel",
                        "prix_calcule", "transport_amount", "prix_au_mille", "prix_achat_mille", "coef",
                        "marge", "devise_prix_devis", "prix_vente",
                        # Nouveau pipeline conditionnement (v217)
                        "prix_achat_mille_dd", "unite_vente_type", "unite_vente_qte",
                        "etiq_par_condi", "prix_achat_conditionne", "prix_vente_final",
                        # Marge brute vs dernier prix de vente (fiche produit)
                        "dernier_prix_vente", "has_produit", "marge_brute_pct",
                        "delai_jours", "commentaire",
                    )},
                    "series_breakdown": series_breakdown,
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
    marge = body.get("marge")
    devise_prix_devis = body.get("devise_prix_devis")
    unite_quotation = body.get("unite_quotation")
    if unite_quotation is not None:
        unite_quotation = (unite_quotation or "").strip().lower()
        if unite_quotation not in UNITES_QUOTATION:
            raise HTTPException(status_code=400, detail="Unite invalide.")
    if coef is not None:
        try:
            coef = float(coef)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Coefficient invalide.")
        if coef <= 0:
            raise HTTPException(status_code=400, detail="Coefficient invalide.")
    if marge is not None:
        try:
            marge = float(marge)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Marge invalide.")
        if marge <= 0:
            raise HTTPException(status_code=400, detail="Marge invalide.")
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
        if marge is not None:
            conn.execute(
                "UPDATE ao_reponses SET marge=? WHERE id=?",
                (marge, reponse_id),
            )
        if devise_prix_devis is not None:
            conn.execute(
                "UPDATE ao_reponses SET devise_prix_devis=? WHERE id=?",
                (devise_prix_devis, reponse_id),
            )
        if unite_quotation is not None:
            # Recup original pour calculer unite_manuel
            row_orig = conn.execute(
                "SELECT COALESCE(unite_quotation_original, unite_quotation) AS orig FROM ao_reponses WHERE id=?",
                (reponse_id,),
            ).fetchone()
            orig_unite = (row_orig[0] if row_orig else None) or unite_quotation
            manuel_flag = 0 if unite_quotation == orig_unite else 1
            conn.execute(
                "UPDATE ao_reponses SET unite_quotation=?, unite_manuel=? WHERE id=?",
                (unite_quotation, manuel_flag, reponse_id),
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
        _ao_pct_row2 = conn.execute(
            "SELECT COALESCE(prix_transport_pct, 0) AS pct FROM ao_demandes WHERE id=?",
            (ao_id,),
        ).fetchone()
        transport_pct2 = float(_ao_pct_row2[0]) if _ao_pct_row2 else 0.0
        produit = _resolve_produit_for_ligne(_row_dict(row), produits_map)
        ctx = ligne_context_from_produit(
            row["ref_produit"], row["quantite"], produit, matieres_map
        )
        return enrich_reponse_pricing(rep_out, ctx, eur_usd_rate=eur_usd, transport_pct=transport_pct2)


@router.post("/{ao_id}/lignes/{ligne_id}/reponses-manuelles")
async def create_reponse_manuelle(request: Request, ao_id: int, ligne_id: int):
    """Crée une réponse fournisseur saisie manuellement en interne.

    Utilisé quand un fournisseur donne son prix par email/téléphone plutôt
    que via le portail. La ligne côté comparateur affiche l'offre comme
    n'importe quelle autre réponse. Le fournisseur est marqué "repondu".

    Body : {ao_fournisseur_id, quotation, devise, unite_quotation,
             delai_jours?, commentaire?, coef?, devise_prix_devis?}
    """
    user = _require_ao(request)
    body = await request.json()
    try:
        ao_fournisseur_id = int(body.get("ao_fournisseur_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Fournisseur invalide.")
    quotation = body.get("quotation")
    if quotation is None or str(quotation).strip() == "":
        raise HTTPException(status_code=400, detail="Quotation obligatoire.")
    try:
        quotation = float(quotation)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Quotation invalide.")
    devise = (body.get("devise") or "EUR").strip().upper()
    if devise not in DEVISES:
        devise = "EUR"
    unite = (body.get("unite_quotation") or "mille").strip().lower()
    if unite not in UNITES_QUOTATION:
        raise HTTPException(status_code=400, detail="Unité invalide.")
    delai = body.get("delai_jours")
    if delai is not None and str(delai).strip() != "":
        try:
            delai = int(delai)
        except (TypeError, ValueError):
            delai = None
    else:
        delai = None
    commentaire = (body.get("commentaire") or "").strip() or None
    coef = body.get("coef")
    if coef is not None:
        try:
            coef = float(coef)
        except (TypeError, ValueError):
            coef = 1.0
        if coef <= 0:
            coef = 1.0
    else:
        coef = 1.0
    devise_prix_devis = (body.get("devise_prix_devis") or "EUR").strip().upper()
    if devise_prix_devis not in DEVISES:
        devise_prix_devis = "EUR"
    now = _now_paris_iso()
    with get_db() as conn:
        _get_ao_or_404(conn, ao_id)
        # Vérifier que la ligne appartient à l'AO
        ln = conn.execute(
            "SELECT * FROM ao_lignes WHERE id=? AND ao_id=?",
            (ligne_id, ao_id),
        ).fetchone()
        if not ln:
            raise HTTPException(status_code=404, detail="Ligne introuvable.")
        # Vérifier que le fournisseur appartient à l'AO
        fourni = conn.execute(
            "SELECT * FROM ao_fournisseurs WHERE id=? AND ao_id=?",
            (ao_fournisseur_id, ao_id),
        ).fetchone()
        if not fourni:
            raise HTTPException(status_code=404, detail="Fournisseur introuvable.")
        # Existe déjà une réponse pour ce couple (fournisseur, ligne, sans série) ?
        existing = conn.execute(
            """SELECT id FROM ao_reponses
               WHERE ao_fournisseur_id=? AND ligne_id=? AND serie_id IS NULL""",
            (ao_fournisseur_id, ligne_id),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Une réponse existe déjà pour ce fournisseur — modifiez-la à la place.")
        conn.execute(
            """INSERT INTO ao_reponses
               (ao_fournisseur_id, ligne_id, quotation, prix_unitaire,
                devise, unite_quotation, unite_quotation_original, unite_manuel,
                coef, devise_prix_devis, delai_jours, commentaire)
               VALUES (?,?,?,?,?,?,?,1,?,?,?,?)""",
            (
                ao_fournisseur_id, ligne_id, quotation, quotation,
                devise, unite, unite,
                coef, devise_prix_devis, delai, commentaire,
            ),
        )
        # Marquer le fournisseur "repondu" (comportement analogue au portail)
        conn.execute(
            """UPDATE ao_fournisseurs
               SET statut='repondu', date_reponse=COALESCE(date_reponse, ?)
               WHERE id=?""",
            (now, ao_fournisseur_id),
        )
        conn.commit()
    log_action(
        user=user, action="CREATE", module="ao",
        objet=f"Réponse manuelle · AO {ao_id} · fournisseur {ao_fournisseur_id}",
        ip=request.client.host if request.client else None,
    )
    return {"ok": True, "ao_id": ao_id, "ligne_id": ligne_id,
            "ao_fournisseur_id": ao_fournisseur_id}


@router.get("/{ao_id}/non-lus")
def non_lus(request: Request, ao_id: int):
    """Retourne pour chaque fournisseur de l'AO le nombre de messages non lus
    et le nombre total de messages. Format : {fourni_id: {"unread": n, "total": m}}
    Rétrocompatible : pour l'ancien front qui lit `S.nonLus[id]` comme un int,
    on renvoie ce format enrichi avec les deux vues au niveau top-level.
    """
    _require_ao(request)
    with get_db() as conn:
        _get_ao_or_404(conn, ao_id)
        unread_rows = conn.execute(
            """SELECT ao_fournisseur_id, COUNT(*) AS n
               FROM ao_messages
               WHERE ao_fournisseur_id IN (
                 SELECT id FROM ao_fournisseurs WHERE ao_id=?
               ) AND expediteur='fournisseur' AND lu=0
               GROUP BY ao_fournisseur_id""",
            (ao_id,),
        ).fetchall()
        total_rows = conn.execute(
            """SELECT ao_fournisseur_id, COUNT(*) AS n
               FROM ao_messages
               WHERE ao_fournisseur_id IN (
                 SELECT id FROM ao_fournisseurs WHERE ao_id=?
               )
               GROUP BY ao_fournisseur_id""",
            (ao_id,),
        ).fetchall()
    unread = {str(r["ao_fournisseur_id"]): int(r["n"]) for r in unread_rows}
    totals = {str(r["ao_fournisseur_id"]): int(r["n"]) for r in total_rows}
    return {
        # Rétrocompatibilité : premier niveau = compte non lus par fournisseur
        **unread,
        # Nouvelles clés dédiées
        "_unread": unread,
        "_totals": totals,
    }
