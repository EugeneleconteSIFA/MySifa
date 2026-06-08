"""MySifa — Module Qualité : Non-conformités
Route prefix : /api/qualite
Accès : superadmin, direction, administration
"""
from __future__ import annotations

import os
import re
import shutil
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.core.database import get_db
from app.services.auth_service import get_current_user
from config import UPLOAD_DIR

ROLES_QUALITE = {"superadmin", "direction", "administration"}
NC_STATUTS = ("ouverte", "en_analyse", "action_corrective", "en_verification", "cloturee")
NC_TYPES = ("interne", "client", "fournisseur", "logistique")
NC_GRAVITES = ("mineure", "majeure", "critique")

QUALITE_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "qualite")
os.makedirs(QUALITE_UPLOAD_DIR, exist_ok=True)

router = APIRouter()


def _require_qualite_access(request: Request) -> dict:
    user = get_current_user(request)
    if user["role"] not in ROLES_QUALITE:
        raise HTTPException(status_code=403, detail="Accès réservé à l'administration et la direction")
    return user


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _sanitize_filename(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._\- ]+", "_", name or "fichier")
    return name[:120] or "fichier"


def _generate_numero(conn, numero_ar: Optional[str]) -> str:
    """Génère un numéro NC. Si AR fourni → 'NC AR<value>', sinon 'NC-YYYY-NNN'."""
    ar = (numero_ar or "").strip()
    if ar:
        candidate = f"NC AR{ar}" if not ar.upper().startswith("NC") else ar
    else:
        year = datetime.now().year
        row = conn.execute(
            "SELECT numero FROM nc_dossiers WHERE numero LIKE ? ORDER BY id DESC",
            (f"NC-{year}-%",),
        ).fetchall()
        used = set()
        for r in row:
            m = re.match(rf"NC-{year}-(\d+)$", r["numero"] or "")
            if m:
                used.add(int(m.group(1)))
        n = 1
        while n in used:
            n += 1
        candidate = f"NC-{year}-{n:03d}"
    # Garantir l'unicité (collision rare sur AR partagé)
    base = candidate
    suffix = 1
    while conn.execute("SELECT 1 FROM nc_dossiers WHERE numero=?", (candidate,)).fetchone():
        suffix += 1
        candidate = f"{base}-{suffix}"
    return candidate


def _row_to_dict(row) -> dict:
    d = dict(row)
    # Parse services_impliques (CSV stocké)
    si = d.get("services_impliques")
    d["services_impliques"] = [s.strip() for s in si.split(",")] if si else []
    return d


def _enrich_nc(conn, nc_dicts: List[dict]) -> List[dict]:
    if not nc_dicts:
        return nc_dicts
    ids = [n["id"] for n in nc_dicts]
    ph = ",".join("?" * len(ids))
    # Compte fichiers
    files = conn.execute(
        f"SELECT nc_id, COUNT(*) AS n FROM nc_fichiers WHERE nc_id IN ({ph}) GROUP BY nc_id", ids
    ).fetchall()
    fcount = {r["nc_id"]: r["n"] for r in files}
    # Compte messages + dernier message
    msgs = conn.execute(
        f"""SELECT nc_id, COUNT(*) AS n, MAX(created_at) AS last_at, MAX(id) AS last_id
            FROM nc_messages WHERE nc_id IN ({ph}) GROUP BY nc_id""", ids
    ).fetchall()
    mmap = {r["nc_id"]: r for r in msgs}
    for n in nc_dicts:
        n["files_count"] = fcount.get(n["id"], 0)
        m = mmap.get(n["id"])
        n["messages_count"] = m["n"] if m else 0
        n["last_message_at"] = m["last_at"] if m else None
        n["last_message_id"] = m["last_id"] if m else None
    return nc_dicts


def _enrich_unread(conn, user_id: int, nc_dicts: List[dict]) -> List[dict]:
    """Calcule unread_count pour l'utilisateur courant."""
    if not nc_dicts:
        return nc_dicts
    ids = [n["id"] for n in nc_dicts]
    ph = ",".join("?" * len(ids))
    reads = conn.execute(
        f"SELECT nc_id, last_read_message_id FROM nc_message_reads WHERE user_id=? AND nc_id IN ({ph})",
        [user_id] + ids,
    ).fetchall()
    rmap = {r["nc_id"]: (r["last_read_message_id"] or 0) for r in reads}
    for n in nc_dicts:
        last_seen = rmap.get(n["id"], 0)
        last_msg = n.get("last_message_id") or 0
        if last_msg > last_seen:
            cnt = conn.execute(
                "SELECT COUNT(*) FROM nc_messages WHERE nc_id=? AND id > ?",
                (n["id"], last_seen),
            ).fetchone()[0]
            n["unread_count"] = cnt
        else:
            n["unread_count"] = 0
    return nc_dicts


# ─── Liste NC ────────────────────────────────────────────────────────

@router.get("/api/qualite/nc")
def list_nc(request: Request, statut: Optional[str] = None, type_nc: Optional[str] = None):
    user = _require_qualite_access(request)
    with get_db() as conn:
        sql = """SELECT nc.*,
                        ue.nom AS emetteur_nom,
                        up.nom AS pilote_nom,
                        uc.nom AS created_by_nom
                 FROM nc_dossiers nc
                 LEFT JOIN users ue ON nc.emetteur_id = ue.id
                 LEFT JOIN users up ON nc.pilote_id = up.id
                 LEFT JOIN users uc ON nc.created_by = uc.id
                 WHERE 1=1"""
        params: list = []
        if statut and statut in NC_STATUTS:
            sql += " AND nc.statut=?"
            params.append(statut)
        if type_nc and type_nc in NC_TYPES:
            sql += " AND nc.type_nc=?"
            params.append(type_nc)
        sql += " ORDER BY nc.updated_at DESC"
        rows = conn.execute(sql, params).fetchall()
        ncs = [_row_to_dict(r) for r in rows]
        ncs = _enrich_nc(conn, ncs)
        ncs = _enrich_unread(conn, user["id"], ncs)
    return ncs


# ─── Détail NC ───────────────────────────────────────────────────────

@router.get("/api/qualite/nc/{nc_id}")
def get_nc(nc_id: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        row = conn.execute(
            """SELECT nc.*,
                      ue.nom AS emetteur_nom,
                      up.nom AS pilote_nom,
                      uc.nom AS created_by_nom,
                      uvq.nom AS validation_qualite_nom,
                      uvi.nom AS validation_industrielle_nom
               FROM nc_dossiers nc
               LEFT JOIN users ue ON nc.emetteur_id = ue.id
               LEFT JOIN users up ON nc.pilote_id = up.id
               LEFT JOIN users uc ON nc.created_by = uc.id
               LEFT JOIN users uvq ON nc.validation_qualite_id = uvq.id
               LEFT JOIN users uvi ON nc.validation_industrielle_id = uvi.id
               WHERE nc.id=?""",
            (nc_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="NC introuvable")
        nc = _row_to_dict(row)
        nc = _enrich_nc(conn, [nc])[0]
        nc = _enrich_unread(conn, user["id"], [nc])[0]
    return nc


# ─── Création NC ─────────────────────────────────────────────────────

class NCCreate(BaseModel):
    titre: str
    type_nc: str = "interne"
    gravite: str = "mineure"
    date_nc: Optional[str] = None
    service_concerne: Optional[str] = None
    numero_ar: Optional[str] = None
    numero_historique: Optional[str] = None
    client_fournisseur: Optional[str] = None
    ref_client: Optional[str] = None
    no_dossier: Optional[str] = None
    descriptif_produit: Optional[str] = None
    quantite_concernee: Optional[str] = None
    description: Optional[str] = None
    services_impliques: Optional[List[str]] = None
    analyse_causes: Optional[str] = None
    action_corrective: Optional[str] = None
    action_preventive: Optional[str] = None
    pilote_id: Optional[int] = None
    delai_cible: Optional[str] = None
    cout_estime: Optional[float] = None
    emetteur_id: Optional[int] = None


@router.post("/api/qualite/nc")
def create_nc(body: NCCreate, request: Request):
    user = _require_qualite_access(request)
    titre = (body.titre or "").strip()
    if not titre:
        raise HTTPException(status_code=400, detail="Titre obligatoire")
    if body.type_nc not in NC_TYPES:
        raise HTTPException(status_code=400, detail="Type NC invalide")
    if body.gravite not in NC_GRAVITES:
        raise HTTPException(status_code=400, detail="Gravité invalide")

    now = _now()
    services_csv = ",".join([s.strip() for s in (body.services_impliques or []) if s.strip()]) or None
    emetteur = body.emetteur_id or user["id"]

    with get_db() as conn:
        numero = _generate_numero(conn, body.numero_ar)
        cur = conn.execute(
            """INSERT INTO nc_dossiers
               (numero, numero_ar, numero_historique, type_nc, gravite, statut, titre,
                date_nc, service_concerne, emetteur_id, client_fournisseur, ref_client,
                no_dossier, descriptif_produit, quantite_concernee, description,
                services_impliques, analyse_causes, action_corrective, action_preventive,
                pilote_id, delai_cible, cout_estime,
                created_at, created_by, updated_at, updated_by)
               VALUES (?,?,?,?,?, 'ouverte', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                numero, (body.numero_ar or None), (body.numero_historique or None),
                body.type_nc, body.gravite, titre,
                body.date_nc or _today(), body.service_concerne, emetteur,
                body.client_fournisseur, body.ref_client, body.no_dossier,
                body.descriptif_produit, body.quantite_concernee, body.description,
                services_csv, body.analyse_causes, body.action_corrective, body.action_preventive,
                body.pilote_id, body.delai_cible, body.cout_estime,
                now, user["id"], now, user["id"],
            ),
        )
        conn.commit()
        nc_id = cur.lastrowid
    return get_nc(nc_id, request)


# ─── Mise à jour NC ──────────────────────────────────────────────────

class NCUpdate(BaseModel):
    titre: Optional[str] = None
    type_nc: Optional[str] = None
    gravite: Optional[str] = None
    statut: Optional[str] = None
    date_nc: Optional[str] = None
    service_concerne: Optional[str] = None
    numero_ar: Optional[str] = None
    numero_historique: Optional[str] = None
    client_fournisseur: Optional[str] = None
    ref_client: Optional[str] = None
    no_dossier: Optional[str] = None
    descriptif_produit: Optional[str] = None
    quantite_concernee: Optional[str] = None
    description: Optional[str] = None
    services_impliques: Optional[List[str]] = None
    analyse_causes: Optional[str] = None
    action_corrective: Optional[str] = None
    action_preventive: Optional[str] = None
    pilote_id: Optional[int] = None
    delai_cible: Optional[str] = None
    cout_estime: Optional[float] = None
    emetteur_id: Optional[int] = None


@router.put("/api/qualite/nc/{nc_id}")
def update_nc(nc_id: int, body: NCUpdate, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM nc_dossiers WHERE id=?", (nc_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="NC introuvable")
        current = dict(row)

        new = {}
        data = body.dict(exclude_unset=True)
        for k, v in data.items():
            if k == "services_impliques":
                new["services_impliques"] = (
                    ",".join([s.strip() for s in (v or []) if s and s.strip()]) or None
                )
            else:
                new[k] = v

        if "statut" in new and new["statut"] not in NC_STATUTS:
            raise HTTPException(status_code=400, detail="Statut invalide")
        if "type_nc" in new and new["type_nc"] not in NC_TYPES:
            raise HTTPException(status_code=400, detail="Type NC invalide")
        if "gravite" in new and new["gravite"] not in NC_GRAVITES:
            raise HTTPException(status_code=400, detail="Gravité invalide")

        # Date de clôture automatique
        date_cloture = current.get("date_cloture")
        if "statut" in new:
            if new["statut"] == "cloturee" and not date_cloture:
                date_cloture = _today()
            elif new["statut"] != "cloturee" and current["statut"] == "cloturee":
                date_cloture = None

        now = _now()
        fields = []
        params: list = []
        for col in (
            "titre", "type_nc", "gravite", "statut", "date_nc", "service_concerne",
            "numero_ar", "numero_historique", "client_fournisseur", "ref_client", "no_dossier",
            "descriptif_produit", "quantite_concernee", "description", "services_impliques",
            "analyse_causes", "action_corrective", "action_preventive", "pilote_id",
            "delai_cible", "cout_estime", "emetteur_id",
        ):
            if col in new:
                fields.append(f"{col}=?")
                params.append(new[col])
        fields.append("date_cloture=?"); params.append(date_cloture)
        fields.append("updated_at=?"); params.append(now)
        fields.append("updated_by=?"); params.append(user["id"])
        params.append(nc_id)
        conn.execute(f"UPDATE nc_dossiers SET {', '.join(fields)} WHERE id=?", params)
        conn.commit()
    return get_nc(nc_id, request)


# ─── Validations Direction Qualité / Industrielle ────────────────────

class NCValidate(BaseModel):
    kind: str  # "qualite" ou "industrielle"
    revoke: bool = False


@router.post("/api/qualite/nc/{nc_id}/valider")
def valider_nc(nc_id: int, body: NCValidate, request: Request):
    user = _require_qualite_access(request)
    if body.kind not in ("qualite", "industrielle"):
        raise HTTPException(status_code=400, detail="Type de validation invalide")
    col_id = "validation_qualite_id" if body.kind == "qualite" else "validation_industrielle_id"
    col_at = "validation_qualite_at" if body.kind == "qualite" else "validation_industrielle_at"
    with get_db() as conn:
        row = conn.execute("SELECT id FROM nc_dossiers WHERE id=?", (nc_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="NC introuvable")
        if body.revoke:
            conn.execute(
                f"UPDATE nc_dossiers SET {col_id}=NULL, {col_at}=NULL, updated_at=?, updated_by=? WHERE id=?",
                (_now(), user["id"], nc_id),
            )
        else:
            conn.execute(
                f"UPDATE nc_dossiers SET {col_id}=?, {col_at}=?, updated_at=?, updated_by=? WHERE id=?",
                (user["id"], _now(), _now(), user["id"], nc_id),
            )
        conn.commit()
    return get_nc(nc_id, request)


# ─── Suppression NC ──────────────────────────────────────────────────

@router.delete("/api/qualite/nc/{nc_id}")
def delete_nc(nc_id: int, request: Request):
    _require_qualite_access(request)
    with get_db() as conn:
        row = conn.execute("SELECT id FROM nc_dossiers WHERE id=?", (nc_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="NC introuvable")
        # Supprimer fichiers du disque
        files = conn.execute("SELECT filename FROM nc_fichiers WHERE nc_id=?", (nc_id,)).fetchall()
        for f in files:
            path = os.path.join(QUALITE_UPLOAD_DIR, f["filename"])
            if os.path.exists(path):
                try: os.remove(path)
                except Exception: pass
        conn.execute("DELETE FROM nc_dossiers WHERE id=?", (nc_id,))
        conn.commit()
    return {"ok": True}


# ─── Fichiers ────────────────────────────────────────────────────────

@router.get("/api/qualite/nc/{nc_id}/fichiers")
def list_fichiers(nc_id: int, request: Request):
    _require_qualite_access(request)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM nc_dossiers WHERE id=?", (nc_id,)).fetchone():
            raise HTTPException(status_code=404, detail="NC introuvable")
        rows = conn.execute(
            """SELECT f.*, u.nom AS uploaded_by_nom
               FROM nc_fichiers f
               LEFT JOIN users u ON f.uploaded_by=u.id
               WHERE f.nc_id=? ORDER BY f.uploaded_at DESC""",
            (nc_id,),
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/api/qualite/nc/{nc_id}/fichiers")
async def upload_fichier(nc_id: int, request: Request, file: UploadFile = File(...)):
    user = _require_qualite_access(request)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Aucun fichier")
    original = _sanitize_filename(file.filename)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM nc_dossiers WHERE id=?", (nc_id,)).fetchone():
            raise HTTPException(status_code=404, detail="NC introuvable")
        ts = datetime.now().strftime("%Y%m%d%H%M%S%f")[:18]
        ext = ""
        if "." in original:
            ext = "." + original.rsplit(".", 1)[1].lower()
        filename = f"nc_{nc_id}_{ts}{ext}"
        dest = os.path.join(QUALITE_UPLOAD_DIR, filename)
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
        size = os.path.getsize(dest)
        conn.execute(
            """INSERT INTO nc_fichiers (nc_id, filename, original_name, mime_type, size_bytes, uploaded_at, uploaded_by)
               VALUES (?,?,?,?,?,?,?)""",
            (nc_id, filename, original, file.content_type or None, size, _now(), user["id"]),
        )
        # Bump updated_at
        conn.execute("UPDATE nc_dossiers SET updated_at=?, updated_by=? WHERE id=?", (_now(), user["id"], nc_id))
        conn.commit()
    return list_fichiers(nc_id, request)


@router.get("/api/qualite/nc/{nc_id}/fichiers/{file_id}")
def download_fichier(nc_id: int, file_id: int, request: Request):
    _require_qualite_access(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM nc_fichiers WHERE id=? AND nc_id=?", (file_id, nc_id)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Fichier introuvable")
    d = dict(row)
    path = os.path.join(QUALITE_UPLOAD_DIR, d["filename"])
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Fichier absent du serveur")
    media = d.get("mime_type") or "application/octet-stream"
    return FileResponse(path, media_type=media, filename=d["original_name"],
                        headers={"Content-Disposition": f'inline; filename="{d["original_name"]}"'})


@router.delete("/api/qualite/nc/{nc_id}/fichiers/{file_id}")
def delete_fichier(nc_id: int, file_id: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM nc_fichiers WHERE id=? AND nc_id=?", (file_id, nc_id)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Fichier introuvable")
        path = os.path.join(QUALITE_UPLOAD_DIR, row["filename"])
        if os.path.exists(path):
            try: os.remove(path)
            except Exception: pass
        conn.execute("DELETE FROM nc_fichiers WHERE id=?", (file_id,))
        conn.execute("UPDATE nc_dossiers SET updated_at=?, updated_by=? WHERE id=?", (_now(), user["id"], nc_id))
        conn.commit()
    return {"ok": True}


# ─── Discussion ──────────────────────────────────────────────────────

@router.get("/api/qualite/nc/{nc_id}/messages")
def list_messages(nc_id: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM nc_dossiers WHERE id=?", (nc_id,)).fetchone():
            raise HTTPException(status_code=404, detail="NC introuvable")
        rows = conn.execute(
            """SELECT m.*, u.nom AS author_nom, u.role AS author_role,
                      f.original_name AS attachment_name, f.mime_type AS attachment_mime
               FROM nc_messages m
               LEFT JOIN users u ON m.author_id=u.id
               LEFT JOIN nc_fichiers f ON m.attachment_id=f.id
               WHERE m.nc_id=? ORDER BY m.created_at ASC, m.id ASC""",
            (nc_id,),
        ).fetchall()
        msgs = [dict(r) for r in rows]
        # Marquer comme lus
        if msgs:
            last_id = max(m["id"] for m in msgs)
            conn.execute(
                """INSERT INTO nc_message_reads (user_id, nc_id, last_read_message_id, last_read_at)
                   VALUES (?,?,?,?)
                   ON CONFLICT(user_id, nc_id) DO UPDATE SET
                     last_read_message_id=excluded.last_read_message_id,
                     last_read_at=excluded.last_read_at""",
                (user["id"], nc_id, last_id, _now()),
            )
            conn.commit()
    return msgs


class NCMessageCreate(BaseModel):
    body: str
    attachment_id: Optional[int] = None


@router.post("/api/qualite/nc/{nc_id}/messages")
def post_message(nc_id: int, body: NCMessageCreate, request: Request):
    user = _require_qualite_access(request)
    text = (body.body or "").strip()
    if not text and not body.attachment_id:
        raise HTTPException(status_code=400, detail="Message vide")
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM nc_dossiers WHERE id=?", (nc_id,)).fetchone():
            raise HTTPException(status_code=404, detail="NC introuvable")
        if body.attachment_id:
            if not conn.execute(
                "SELECT 1 FROM nc_fichiers WHERE id=? AND nc_id=?", (body.attachment_id, nc_id)
            ).fetchone():
                raise HTTPException(status_code=400, detail="Pièce jointe invalide")
        now = _now()
        cur = conn.execute(
            "INSERT INTO nc_messages (nc_id, author_id, body, attachment_id, created_at) VALUES (?,?,?,?,?)",
            (nc_id, user["id"], text, body.attachment_id, now),
        )
        msg_id = cur.lastrowid
        conn.execute("UPDATE nc_dossiers SET updated_at=?, updated_by=? WHERE id=?", (now, user["id"], nc_id))
        # L'auteur lit son propre message
        conn.execute(
            """INSERT INTO nc_message_reads (user_id, nc_id, last_read_message_id, last_read_at)
               VALUES (?,?,?,?)
               ON CONFLICT(user_id, nc_id) DO UPDATE SET
                 last_read_message_id=excluded.last_read_message_id,
                 last_read_at=excluded.last_read_at""",
            (user["id"], nc_id, msg_id, now),
        )
        conn.commit()
        row = conn.execute(
            """SELECT m.*, u.nom AS author_nom, u.role AS author_role,
                      f.original_name AS attachment_name, f.mime_type AS attachment_mime
               FROM nc_messages m
               LEFT JOIN users u ON m.author_id=u.id
               LEFT JOIN nc_fichiers f ON m.attachment_id=f.id
               WHERE m.id=?""",
            (msg_id,),
        ).fetchone()
    return dict(row)


# ─── Canaux : NC ouvertes avec activité récente ──────────────────────

@router.get("/api/qualite/canaux")
def list_canaux(request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT nc.id, nc.numero, nc.titre, nc.statut, nc.type_nc, nc.gravite,
                      nc.updated_at,
                      (SELECT COUNT(*) FROM nc_messages WHERE nc_id=nc.id) AS messages_count,
                      (SELECT MAX(id) FROM nc_messages WHERE nc_id=nc.id) AS last_message_id,
                      (SELECT MAX(created_at) FROM nc_messages WHERE nc_id=nc.id) AS last_message_at
               FROM nc_dossiers nc
               WHERE nc.statut != 'cloturee'
               ORDER BY (SELECT MAX(created_at) FROM nc_messages WHERE nc_id=nc.id) DESC NULLS LAST,
                        nc.updated_at DESC"""
        ).fetchall()
        ncs = [dict(r) for r in rows]
        ncs = _enrich_unread(conn, user["id"], ncs)
    return ncs


@router.get("/api/qualite/unread-total")
def unread_total(request: Request):
    """Total des messages non lus pour la sidebar/portail."""
    user = _require_qualite_access(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT nc.id,
                      (SELECT MAX(id) FROM nc_messages WHERE nc_id=nc.id) AS last_id,
                      r.last_read_message_id AS last_read
               FROM nc_dossiers nc
               LEFT JOIN nc_message_reads r ON r.nc_id=nc.id AND r.user_id=?
               WHERE nc.statut != 'cloturee'""",
            (user["id"],),
        ).fetchall()
        total = 0
        for r in rows:
            last = r["last_id"] or 0
            seen = r["last_read"] or 0
            if last > seen:
                cnt = conn.execute(
                    "SELECT COUNT(*) FROM nc_messages WHERE nc_id=? AND id>?",
                    (r["id"], seen),
                ).fetchone()[0]
                total += cnt
    return {"unread": total}


# ─── Picker dossier production ───────────────────────────────────────

@router.get("/api/qualite/dossiers-search")
def search_dossiers(request: Request, q: str = ""):
    _require_qualite_access(request)
    q = (q or "").strip()
    with get_db() as conn:
        if q:
            rows = conn.execute(
                """SELECT DISTINCT no_dossier, client, designation
                   FROM production_data
                   WHERE no_dossier LIKE ? OR client LIKE ? OR designation LIKE ?
                   ORDER BY no_dossier DESC LIMIT 30""",
                (f"%{q}%", f"%{q}%", f"%{q}%"),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT DISTINCT no_dossier, client, designation
                   FROM production_data
                   WHERE no_dossier IS NOT NULL AND no_dossier != ''
                   ORDER BY no_dossier DESC LIMIT 30"""
            ).fetchall()
    return [dict(r) for r in rows]


# ─── Export PDF ──────────────────────────────────────────────────────

@router.get("/api/qualite/nc/{nc_id}/pdf")
def export_nc_pdf(nc_id: int, request: Request):
    _require_qualite_access(request)
    from fastapi.responses import Response
    from fastapi.responses import Response
    nc = get_nc(nc_id, request)
    pdf_bytes = render_nc_pdf(nc)
    fname = (nc.get("numero") or f"NC_{nc_id}").replace(" ", "_") + ".pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{fname}"'},
    )


# ─── Liste utilisateurs (pour pilote / émetteur picker) ──────────────

@router.get("/api/qualite/users")
def list_users(request: Request):
    _require_qualite_access(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, nom, role FROM users WHERE actif=1 ORDER BY nom"
        ).fetchall()
    return [dict(r) for r in rows]
