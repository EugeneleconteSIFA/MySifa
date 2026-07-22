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

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.core.database import get_db
from app.services.auth_service import get_current_user
from config import (
    UPLOAD_DIR,
    NC_ACK_SERVICES,
    NC_ACK_SERVICE_KEYS,
    NC_ACK_RESET_FIELDS,
    nc_service_for_role,
)

ROLES_QUALITE = {"superadmin", "direction", "administration", "administration_ventes", "administration_technique"}
ROLES_QUALITE_VIEW = ROLES_QUALITE | {"commercial"}
NC_STATUTS = ("ouverte", "en_analyse", "action_corrective", "en_verification", "cloturee")
NC_TYPES = ("interne", "client", "fournisseur", "logistique")
NC_GRAVITES = ("mineure", "majeure", "critique")

QUALITE_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "qualite")
os.makedirs(QUALITE_UPLOAD_DIR, exist_ok=True)

router = APIRouter()


def _require_qualite_access(request: Request) -> dict:
    """Écriture : direction / administration / superadmin uniquement."""
    user = get_current_user(request)
    if user["role"] not in ROLES_QUALITE:
        raise HTTPException(status_code=403, detail="Accès réservé à l'administration et la direction")
    return user


def _require_qualite_view(request: Request) -> dict:
    """Lecture : + commercial (read-only)."""
    user = get_current_user(request)
    if user["role"] not in ROLES_QUALITE_VIEW:
        raise HTTPException(status_code=403, detail="Accès réservé à l'administration, la direction et le commercial")
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


def _enrich_acks(conn, nc_dicts):
    """Ajoute à chaque NC :
      - `service_acks` : dict {service_key: {user_id, user_nom, ack_at}} pour chaque service
        ayant pris connaissance de la NC.
      - `services_ack_order` : liste ordonnée des services (5 services standards) ; utilisée
        par le frontend pour afficher les pastilles dans le bon ordre.
    L'ordre + libellés + couleurs viennent de config.NC_ACK_SERVICES (source de vérité).
    """
    if not nc_dicts:
        return nc_dicts
    ids = [n["id"] for n in nc_dicts]
    ph = ",".join("?" * len(ids))
    rows = conn.execute(
        f"""SELECT a.nc_id, a.service, a.user_id, a.ack_at, u.nom AS user_nom
             FROM nc_service_acknowledgments a
             LEFT JOIN users u ON u.id = a.user_id
             WHERE a.nc_id IN ({ph})""",
        ids,
    ).fetchall()
    per_nc = {}
    for r in rows:
        per_nc.setdefault(r["nc_id"], {})[r["service"]] = {
            "user_id": r["user_id"],
            "user_nom": r["user_nom"],
            "ack_at": r["ack_at"],
        }
    for n in nc_dicts:
        n["service_acks"] = per_nc.get(n["id"], {})
    return nc_dicts


def _reset_acks_if_needed(conn, nc_id, changed_fields):
    """Reset les ack de tous les services si un champ « sensible » a été modifié.
    Les champs déclencheurs sont définis dans config.NC_ACK_RESET_FIELDS.
    """
    if not any(f in NC_ACK_RESET_FIELDS for f in changed_fields):
        return 0
    cur = conn.execute("DELETE FROM nc_service_acknowledgments WHERE nc_id=?", (nc_id,))
    return cur.rowcount


# ─── Liste NC ────────────────────────────────────────────────────────

@router.get("/api/qualite/nc")
def list_nc(request: Request, statut: Optional[str] = None, type_nc: Optional[str] = None):
    user = _require_qualite_view(request)
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
        ncs = _enrich_acks(conn, ncs)
    return ncs


# ─── Détail NC ───────────────────────────────────────────────────────

@router.get("/api/qualite/nc/{nc_id}")
def get_nc(nc_id: int, request: Request):
    user = _require_qualite_view(request)
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
        nc = _enrich_acks(conn, [nc])[0]
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
        # Reset des ack si un champ « sensible » a été modifié
        # (titre, description, analyse causes, actions, gravité, quantité concernée).
        _reset_acks_if_needed(conn, nc_id, set(new.keys()))
        conn.commit()
    return get_nc(nc_id, request)


# ─── Prise de connaissance NC par service ─────────────────────────────

@router.get("/api/qualite/services")
def list_ack_services(request: Request):
    """Retourne la liste des services d'ack + le service du user courant (si applicable).
    Utilisé par le frontend pour construire la légende, les pastilles et savoir si le
    user peut cliquer sur « Marquer comme lu ».
    """
    user = _require_qualite_view(request)
    my_service = nc_service_for_role(user.get("role"), user.get("nc_service_override"))
    return {
        "services": NC_ACK_SERVICES,
        "my_service": my_service,
    }


@router.post("/api/qualite/nc/{nc_id}/ack")
def ack_nc(nc_id: int, request: Request):
    """Le user courant marque la NC comme prise en connaissance pour SON service.
    Un seul user par service suffit : la ligne est upsert-ée (INSERT OR REPLACE).
    Le service du user est déterminé côté serveur (rôle + éventuel override).
    """
    user = _require_qualite_view(request)
    service = nc_service_for_role(user.get("role"), user.get("nc_service_override"))
    if not service:
        raise HTTPException(
            status_code=403,
            detail="Votre rôle n'est pas associé à un service de prise en connaissance NC",
        )
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM nc_dossiers WHERE id=?", (nc_id,)).fetchone():
            raise HTTPException(status_code=404, detail="NC introuvable")
        conn.execute(
            """INSERT INTO nc_service_acknowledgments (nc_id, service, user_id, ack_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(nc_id, service) DO UPDATE
                 SET user_id = excluded.user_id, ack_at = excluded.ack_at""",
            (nc_id, service, user["id"], _now()),
        )
        conn.commit()
    return get_nc(nc_id, request)


@router.delete("/api/qualite/nc/{nc_id}/ack")
def unack_nc(nc_id: int, request: Request):
    """Le user courant retire la prise en connaissance de SON service (annule l'ack).
    Utile si un user a cliqué par erreur. N'affecte pas les acks des autres services.
    """
    user = _require_qualite_view(request)
    service = nc_service_for_role(user.get("role"), user.get("nc_service_override"))
    if not service:
        raise HTTPException(
            status_code=403,
            detail="Votre rôle n'est pas associé à un service de prise en connaissance NC",
        )
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM nc_dossiers WHERE id=?", (nc_id,)).fetchone():
            raise HTTPException(status_code=404, detail="NC introuvable")
        conn.execute(
            "DELETE FROM nc_service_acknowledgments WHERE nc_id=? AND service=?",
            (nc_id, service),
        )
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
    _require_qualite_view(request)
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
    _require_qualite_view(request)
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
    user = _require_qualite_view(request)
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
    user = _require_qualite_view(request)
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
    user = _require_qualite_view(request)
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
    _require_qualite_view(request)
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


# ─── Import xlsx (fiche SIFA) ────────────────────────────────────────

def _parse_sifa_nc_xlsx(file_bytes: bytes) -> dict:
    """Parse une fiche xlsx SIFA NC (modèle V1-07/2024) et retourne les champs détectés."""
    import openpyxl
    from io import BytesIO
    wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
    ws = wb.worksheets[0]

    def _cell(coord):
        v = ws[coord].value
        if v is None:
            return None
        if hasattr(v, "isoformat"):  # datetime
            return v.strftime("%Y-%m-%d")
        return str(v).strip()

    def _strip_prefix(val, prefixes):
        if not val:
            return val
        v = val.strip().replace("\xa0", " ")
        for p in prefixes:
            if v.lower().startswith(p.lower()):
                v = v[len(p):].strip(" :\t\n\r-—–\xa0").strip()
        return v

    # En-tête : "N° 668608  -  AR 9930854"
    header = _cell("B3") or ""
    numero_historique = None
    numero_ar = None
    if header:
        m_n = re.search(r"N[°o]\s*([A-Za-z0-9\-_/]+)", header)
        if m_n:
            numero_historique = m_n.group(1)
        m_ar = re.search(r"AR\s*([A-Za-z0-9\-_/]+)", header, re.IGNORECASE)
        if m_ar:
            numero_ar = m_ar.group(1)

    # Date NC : B8 ou D15
    date_nc = _cell("B8") or _cell("D15")
    service_concerne = _cell("D8")

    # Émetteur : "EMETTEUR DE LA FICHE : ADV - RL" en A9
    emetteur_raw = _cell("A9") or ""
    emetteur = _strip_prefix(emetteur_raw, ["EMETTEUR DE LA FICHE", "Emetteur de la fiche", "ÉMETTEUR DE LA FICHE"])

    description = _cell("A11")
    client_fournisseur = _cell("B15")
    ref_client = _cell("B16")
    no_dossier = _cell("D16")
    descriptif_produit = _cell("B17")
    quantite_concernee = _cell("B18")

    # Services impliqués (B20 : "ADV - MECANIQUE - QUALITE")
    services_line = _cell("B20") or ""
    services = []
    if services_line:
        for tok in re.split(r"[-–—,;/]+", services_line):
            t = tok.strip()
            if t and len(t) < 30:
                tl = t.lower()
                mapping = {"adv": "ADV", "mecanique": "Mécanique", "mécanique": "Mécanique",
                           "qualite": "Qualité", "qualité": "Qualité", "production": "Production",
                           "logistique": "Logistique"}
                services.append(mapping.get(tl, t))

    analyse_causes = _cell("A21")
    action_corrective = _cell("A25")
    pilote_raw = _cell("A29") or ""
    pilote_name = _strip_prefix(pilote_raw, ["Pilote", "PILOTE"])
    action_preventive = _cell("A31")
    raw_cloture = _cell("A37") or _cell("B37")
    date_cloture = raw_cloture if (raw_cloture and re.match(r"^\d{4}-\d{2}-\d{2}", str(raw_cloture))) else None

    if description:
        titre = description.split(".")[0].strip()[:120]
    else:
        titre = "NC importée"

    type_nc = "client" if client_fournisseur else "interne"

    return {
        "titre": titre,
        "numero_ar": numero_ar,
        "numero_historique": numero_historique,
        "type_nc": type_nc,
        "gravite": "majeure",
        "date_nc": date_nc,
        "service_concerne": service_concerne,
        "client_fournisseur": client_fournisseur,
        "ref_client": ref_client,
        "no_dossier": no_dossier,
        "descriptif_produit": descriptif_produit,
        "quantite_concernee": quantite_concernee,
        "description": description,
        "services_impliques": services,
        "analyse_causes": analyse_causes,
        "action_corrective": action_corrective,
        "action_preventive": action_preventive,
        "emetteur_text": emetteur,
        "pilote_text": pilote_name,
        "date_cloture": date_cloture,
    }


@router.post("/api/qualite/import-xlsx")
async def import_nc_xlsx(request: Request, file: UploadFile = File(...)):
    user = _require_qualite_access(request)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Aucun fichier")
    name_lower = file.filename.lower()
    if not (name_lower.endswith(".xlsx") or name_lower.endswith(".xlsm")):
        raise HTTPException(status_code=400, detail="Format requis : .xlsx ou .xlsm")
    raw = await file.read()
    try:
        parsed = _parse_sifa_nc_xlsx(raw)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Impossible de parser le fichier : {e}")

    now = _now()
    services_csv = ",".join(parsed.get("services_impliques") or []) or None

    pilote_id = None
    pilote_text = parsed.get("pilote_text") or ""
    if pilote_text:
        with get_db() as conn:
            row = conn.execute(
                "SELECT id FROM users WHERE actif=1 AND LOWER(nom) LIKE ? LIMIT 1",
                (f"%{pilote_text.lower()}%",),
            ).fetchone()
            if row:
                pilote_id = row["id"]

    with get_db() as conn:
        numero = _generate_numero(conn, parsed.get("numero_ar"))
        cur = conn.execute(
            """INSERT INTO nc_dossiers
               (numero, numero_ar, numero_historique, type_nc, gravite, statut, titre,
                date_nc, service_concerne, emetteur_id, client_fournisseur, ref_client,
                no_dossier, descriptif_produit, quantite_concernee, description,
                services_impliques, analyse_causes, action_corrective, action_preventive,
                pilote_id, date_cloture,
                created_at, created_by, updated_at, updated_by)
               VALUES (?,?,?,?,?, 'ouverte', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                numero, parsed.get("numero_ar"), parsed.get("numero_historique"),
                parsed.get("type_nc"), parsed.get("gravite"), parsed.get("titre"),
                parsed.get("date_nc"), parsed.get("service_concerne"), user["id"],
                parsed.get("client_fournisseur"), parsed.get("ref_client"), parsed.get("no_dossier"),
                parsed.get("descriptif_produit"), parsed.get("quantite_concernee"), parsed.get("description"),
                services_csv, parsed.get("analyse_causes"), parsed.get("action_corrective"),
                parsed.get("action_preventive"), pilote_id, parsed.get("date_cloture"),
                now, user["id"], now, user["id"],
            ),
        )
        nc_id = cur.lastrowid

        original = _sanitize_filename(file.filename)
        ts = datetime.now().strftime("%Y%m%d%H%M%S%f")[:18]
        ext = "." + name_lower.rsplit(".", 1)[1]
        filename = f"nc_{nc_id}_{ts}{ext}"
        dest = os.path.join(QUALITE_UPLOAD_DIR, filename)
        with open(dest, "wb") as f:
            f.write(raw)
        size = os.path.getsize(dest)
        conn.execute(
            """INSERT INTO nc_fichiers (nc_id, filename, original_name, mime_type, size_bytes, uploaded_at, uploaded_by)
               VALUES (?,?,?,?,?,?,?)""",
            (nc_id, filename, original, file.content_type or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
             size, now, user["id"]),
        )
        conn.commit()

    return get_nc(nc_id, request)


# ─── Export PDF ──────────────────────────────────────────────────────

@router.get("/api/qualite/nc/{nc_id}/pdf")
def export_nc_pdf(nc_id: int, request: Request):
    _require_qualite_view(request)
    from fastapi.responses import Response
    from app.services.nc_pdf import render_nc_pdf
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
    _require_qualite_view(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, nom, role FROM users WHERE actif=1 ORDER BY nom"
        ).fetchall()
    return [dict(r) for r in rows]


# ════════════════════════════════════════════════════════════════════
# MODULE AUDITS CLIENT
# ════════════════════════════════════════════════════════════════════

AUDIT_STATUTS = ("ouvert", "cloture")
AUDIT_UPLOAD_DIR = QUALITE_UPLOAD_DIR  # même dossier physique, préfixe "audit_" dans le nom


def _generate_audit_numero(conn) -> str:
    """Génère un numéro audit type AUD-YYYY-NNN."""
    year = datetime.now().year
    rows = conn.execute(
        "SELECT numero FROM audit_dossiers WHERE numero LIKE ? ORDER BY id DESC",
        (f"AUD-{year}-%",),
    ).fetchall()
    used = set()
    for r in rows:
        m = re.match(rf"AUD-{year}-(\d+)$", r["numero"] or "")
        if m:
            used.add(int(m.group(1)))
    n = 1
    while n in used:
        n += 1
    return f"AUD-{year}-{n:03d}"


def _audit_row_to_dict(row) -> dict:
    return dict(row)


def _enrich_audit(conn, audits: List[dict]) -> List[dict]:
    if not audits:
        return audits
    ids = [a["id"] for a in audits]
    ph = ",".join("?" * len(ids))

    files = conn.execute(
        f"SELECT audit_id, COUNT(*) AS n FROM audit_fichiers WHERE audit_id IN ({ph}) GROUP BY audit_id", ids
    ).fetchall()
    fcount = {r["audit_id"]: r["n"] for r in files}

    msgs = conn.execute(
        f"""SELECT audit_id, COUNT(*) AS n, MAX(created_at) AS last_at, MAX(id) AS last_id
            FROM audit_messages WHERE audit_id IN ({ph}) GROUP BY audit_id""", ids
    ).fetchall()
    mmap = {r["audit_id"]: r for r in msgs}

    auditeurs = conn.execute(
        f"""SELECT a.audit_id, a.user_id, u.nom AS user_nom, u.role AS user_role
            FROM audit_auditeurs a
            LEFT JOIN users u ON u.id=a.user_id
            WHERE a.audit_id IN ({ph})
            ORDER BY u.nom""", ids
    ).fetchall()
    amap: dict = {}
    for r in auditeurs:
        amap.setdefault(r["audit_id"], []).append({
            "user_id": r["user_id"], "nom": r["user_nom"], "role": r["user_role"]
        })

    for a in audits:
        a["files_count"] = fcount.get(a["id"], 0)
        m = mmap.get(a["id"])
        a["messages_count"] = m["n"] if m else 0
        a["last_message_at"] = m["last_at"] if m else None
        a["last_message_id"] = m["last_id"] if m else None
        a["auditeurs"] = amap.get(a["id"], [])
    return audits


def _enrich_audit_unread(conn, user_id: int, audits: List[dict]) -> List[dict]:
    if not audits:
        return audits
    ids = [a["id"] for a in audits]
    ph = ",".join("?" * len(ids))
    reads = conn.execute(
        f"SELECT audit_id, last_read_message_id FROM audit_message_reads WHERE user_id=? AND audit_id IN ({ph})",
        [user_id] + ids,
    ).fetchall()
    rmap = {r["audit_id"]: (r["last_read_message_id"] or 0) for r in reads}
    for a in audits:
        last_seen = rmap.get(a["id"], 0)
        last_msg = a.get("last_message_id") or 0
        if last_msg > last_seen:
            cnt = conn.execute(
                "SELECT COUNT(*) FROM audit_messages WHERE audit_id=? AND id > ?",
                (a["id"], last_seen),
            ).fetchone()[0]
            a["unread_count"] = cnt
        else:
            a["unread_count"] = 0
    return audits


def _notify_auditeur(audit_id: int, audit_numero: str, audit_client: str, user_id: int) -> None:
    """Envoie une notification push à un auditeur nouvellement affecté.
    Ne lève jamais — silencieux si push non configuré."""
    try:
        from app.routers.push import send_push_safe
        send_push_safe(
            user_id,
            title=f"Audit client — {audit_numero}",
            body=f"Vous avez été affecté(e) à un audit chez {audit_client}.",
            url=f"/qualite?audit={audit_id}",
            tag=f"audit-{audit_id}",
        )
    except Exception:
        pass


# ─── Liste audits ────────────────────────────────────────────────────

@router.get("/api/qualite/audits")
def list_audits(request: Request, statut: Optional[str] = None, q: Optional[str] = None):
    user = _require_qualite_view(request)
    with get_db() as conn:
        sql = """SELECT a.*,
                        uc.nom AS created_by_nom,
                        cl.raison_sociale AS client_raison_sociale
                 FROM audit_dossiers a
                 LEFT JOIN users uc ON a.created_by = uc.id
                 LEFT JOIN clients cl ON a.client_id = cl.id
                 WHERE 1=1"""
        params: list = []
        if statut and statut in AUDIT_STATUTS:
            sql += " AND a.statut=?"
            params.append(statut)
        if q:
            sql += " AND (a.client_nom LIKE ? OR a.description LIKE ? OR a.numero LIKE ?)"
            like = f"%{q.strip()}%"
            params.extend([like, like, like])
        sql += " ORDER BY a.date_audit DESC, a.id DESC"
        rows = conn.execute(sql, params).fetchall()
        audits = [_audit_row_to_dict(r) for r in rows]
        audits = _enrich_audit(conn, audits)
        audits = _enrich_audit_unread(conn, user["id"], audits)
    return audits


# ─── Détail audit ────────────────────────────────────────────────────

@router.get("/api/qualite/audits/{audit_id}")
def get_audit(audit_id: int, request: Request):
    user = _require_qualite_view(request)
    with get_db() as conn:
        row = conn.execute(
            """SELECT a.*,
                      uc.nom AS created_by_nom,
                      uu.nom AS updated_by_nom,
                      cl.raison_sociale AS client_raison_sociale
               FROM audit_dossiers a
               LEFT JOIN users uc ON a.created_by = uc.id
               LEFT JOIN users uu ON a.updated_by = uu.id
               LEFT JOIN clients cl ON a.client_id = cl.id
               WHERE a.id=?""",
            (audit_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Audit introuvable")
        a = _audit_row_to_dict(row)
        a = _enrich_audit(conn, [a])[0]
        a = _enrich_audit_unread(conn, user["id"], [a])[0]
    return a


# ─── Création audit ──────────────────────────────────────────────────

class AuditCreate(BaseModel):
    client_nom: str
    client_id: Optional[int] = None
    date_audit: str
    description: str
    auditeur_ids: List[int]


@router.post("/api/qualite/audits")
def create_audit(body: AuditCreate, request: Request):
    user = _require_qualite_access(request)
    client_nom = (body.client_nom or "").strip()
    description = (body.description or "").strip()
    date_audit = (body.date_audit or "").strip()
    if not client_nom:
        raise HTTPException(status_code=400, detail="Nom du client obligatoire")
    if not date_audit:
        raise HTTPException(status_code=400, detail="Date obligatoire")
    if not description:
        raise HTTPException(status_code=400, detail="Description obligatoire")
    if not body.auditeur_ids:
        raise HTTPException(status_code=400, detail="Au moins un auditeur obligatoire")

    now = _now()
    notif_ids: List[int] = []
    with get_db() as conn:
        # Vérifier que les auditeurs ont bien un rôle Qualité
        ph = ",".join("?" * len(body.auditeur_ids))
        valid = conn.execute(
            f"SELECT id FROM users WHERE id IN ({ph}) AND actif=1 AND role IN ('superadmin','direction','administration','administration_ventes','administration_technique')",
            body.auditeur_ids,
        ).fetchall()
        valid_ids = [v["id"] for v in valid]
        if not valid_ids:
            raise HTTPException(status_code=400, detail="Aucun auditeur valide")

        # Vérifier client_id si fourni
        client_id = body.client_id
        if client_id:
            if not conn.execute("SELECT 1 FROM clients WHERE id=?", (client_id,)).fetchone():
                client_id = None

        numero = _generate_audit_numero(conn)
        cur = conn.execute(
            """INSERT INTO audit_dossiers
               (numero, client_id, client_nom, date_audit, description, statut,
                created_at, created_by, updated_at, updated_by)
               VALUES (?,?,?,?,?, 'ouvert', ?,?,?,?)""",
            (numero, client_id, client_nom, date_audit, description,
             now, user["id"], now, user["id"]),
        )
        audit_id = cur.lastrowid

        for uid in valid_ids:
            conn.execute(
                """INSERT INTO audit_auditeurs (audit_id, user_id, assigned_at, assigned_by, notified)
                   VALUES (?,?,?,?,0)""",
                (audit_id, uid, now, user["id"]),
            )
            if uid != user["id"]:
                notif_ids.append(uid)
        conn.commit()

    # Notifications push hors transaction (silencieux)
    for uid in notif_ids:
        _notify_auditeur(audit_id, numero, client_nom, uid)
    # Marquer notifié
    if notif_ids:
        with get_db() as conn:
            ph2 = ",".join("?" * len(notif_ids))
            conn.execute(
                f"UPDATE audit_auditeurs SET notified=1 WHERE audit_id=? AND user_id IN ({ph2})",
                [audit_id] + notif_ids,
            )
            conn.commit()

    return get_audit(audit_id, request)


# ─── Mise à jour audit ───────────────────────────────────────────────

class AuditUpdate(BaseModel):
    client_nom: Optional[str] = None
    client_id: Optional[int] = None
    date_audit: Optional[str] = None
    description: Optional[str] = None


@router.put("/api/qualite/audits/{audit_id}")
def update_audit(audit_id: int, body: AuditUpdate, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM audit_dossiers WHERE id=?", (audit_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Audit introuvable")
        data = body.dict(exclude_unset=True)
        fields = []
        params: list = []
        for col in ("client_nom", "client_id", "date_audit", "description"):
            if col in data:
                val = data[col]
                if col in ("client_nom", "date_audit", "description") and isinstance(val, str):
                    val = val.strip()
                    if not val:
                        raise HTTPException(status_code=400, detail=f"{col} ne peut pas être vide")
                if col == "client_id" and val:
                    if not conn.execute("SELECT 1 FROM clients WHERE id=?", (val,)).fetchone():
                        val = None
                fields.append(f"{col}=?")
                params.append(val)
        if fields:
            now = _now()
            fields.extend(["updated_at=?", "updated_by=?"])
            params.extend([now, user["id"]])
            params.append(audit_id)
            conn.execute(f"UPDATE audit_dossiers SET {', '.join(fields)} WHERE id=?", params)
            conn.commit()
    return get_audit(audit_id, request)


# ─── Clôture / réouverture ───────────────────────────────────────────

@router.post("/api/qualite/audits/{audit_id}/cloturer")
def cloturer_audit(audit_id: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        row = conn.execute("SELECT statut FROM audit_dossiers WHERE id=?", (audit_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Audit introuvable")
        if row["statut"] == "cloture":
            return get_audit(audit_id, request)
        now = _now()
        conn.execute(
            "UPDATE audit_dossiers SET statut='cloture', date_cloture=?, updated_at=?, updated_by=? WHERE id=?",
            (_today(), now, user["id"], audit_id),
        )
        conn.commit()
    return get_audit(audit_id, request)


@router.post("/api/qualite/audits/{audit_id}/rouvrir")
def rouvrir_audit(audit_id: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        row = conn.execute("SELECT statut FROM audit_dossiers WHERE id=?", (audit_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Audit introuvable")
        if row["statut"] == "ouvert":
            return get_audit(audit_id, request)
        now = _now()
        conn.execute(
            "UPDATE audit_dossiers SET statut='ouvert', date_cloture=NULL, updated_at=?, updated_by=? WHERE id=?",
            (now, user["id"], audit_id),
        )
        conn.commit()
    return get_audit(audit_id, request)


# ─── Suppression audit ───────────────────────────────────────────────

@router.delete("/api/qualite/audits/{audit_id}")
def delete_audit(audit_id: int, request: Request):
    _require_qualite_access(request)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM audit_dossiers WHERE id=?", (audit_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Audit introuvable")
        files = conn.execute("SELECT filename FROM audit_fichiers WHERE audit_id=?", (audit_id,)).fetchall()
        for f in files:
            path = os.path.join(AUDIT_UPLOAD_DIR, f["filename"])
            if os.path.exists(path):
                try: os.remove(path)
                except Exception: pass
        # Suppressions explicites (PRAGMA foreign_keys=OFF par défaut sur MySifa)
        conn.execute("DELETE FROM audit_message_reads WHERE audit_id=?", (audit_id,))
        conn.execute("DELETE FROM audit_messages WHERE audit_id=?", (audit_id,))
        conn.execute("DELETE FROM audit_fichiers WHERE audit_id=?", (audit_id,))
        conn.execute("DELETE FROM audit_folders WHERE audit_id=?", (audit_id,))
        conn.execute("DELETE FROM audit_auditeurs WHERE audit_id=?", (audit_id,))
        conn.execute("DELETE FROM audit_dossiers WHERE id=?", (audit_id,))
        conn.commit()
    return {"ok": True}


# ─── Auditeurs ───────────────────────────────────────────────────────

class AuditeurAdd(BaseModel):
    user_id: int


@router.post("/api/qualite/audits/{audit_id}/auditeurs")
def add_auditeur(audit_id: int, body: AuditeurAdd, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        a_row = conn.execute(
            "SELECT id, numero, client_nom FROM audit_dossiers WHERE id=?", (audit_id,)
        ).fetchone()
        if not a_row:
            raise HTTPException(status_code=404, detail="Audit introuvable")
        u_row = conn.execute(
            "SELECT id FROM users WHERE id=? AND actif=1 AND role IN ('superadmin','direction','administration','administration_ventes','administration_technique')",
            (body.user_id,),
        ).fetchone()
        if not u_row:
            raise HTTPException(status_code=400, detail="Utilisateur invalide pour ce rôle")
        if conn.execute(
            "SELECT 1 FROM audit_auditeurs WHERE audit_id=? AND user_id=?",
            (audit_id, body.user_id),
        ).fetchone():
            return get_audit(audit_id, request)
        now = _now()
        conn.execute(
            """INSERT INTO audit_auditeurs (audit_id, user_id, assigned_at, assigned_by, notified)
               VALUES (?,?,?,?,0)""",
            (audit_id, body.user_id, now, user["id"]),
        )
        conn.execute("UPDATE audit_dossiers SET updated_at=?, updated_by=? WHERE id=?",
                     (now, user["id"], audit_id))
        conn.commit()
    # Notif push
    if body.user_id != user["id"]:
        _notify_auditeur(audit_id, a_row["numero"], a_row["client_nom"], body.user_id)
        with get_db() as conn:
            conn.execute(
                "UPDATE audit_auditeurs SET notified=1 WHERE audit_id=? AND user_id=?",
                (audit_id, body.user_id),
            )
            conn.commit()
    return get_audit(audit_id, request)


@router.delete("/api/qualite/audits/{audit_id}/auditeurs/{user_id}")
def remove_auditeur(audit_id: int, user_id: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM audit_dossiers WHERE id=?", (audit_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Audit introuvable")
        conn.execute(
            "DELETE FROM audit_auditeurs WHERE audit_id=? AND user_id=?",
            (audit_id, user_id),
        )
        conn.execute("UPDATE audit_dossiers SET updated_at=?, updated_by=? WHERE id=?",
                     (_now(), user["id"], audit_id))
        conn.commit()
    return get_audit(audit_id, request)


# ─── Sous-dossiers (arborescence) ────────────────────────────────────

@router.get("/api/qualite/audits/{audit_id}/folders")
def list_folders(audit_id: int, request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM audit_dossiers WHERE id=?", (audit_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Audit introuvable")
        rows = conn.execute(
            """SELECT f.*, u.nom AS created_by_nom
               FROM audit_folders f
               LEFT JOIN users u ON f.created_by=u.id
               WHERE f.audit_id=?
               ORDER BY f.parent_id IS NOT NULL, f.parent_id, LOWER(f.nom)""",
            (audit_id,),
        ).fetchall()
    return [dict(r) for r in rows]


class FolderCreate(BaseModel):
    nom: str
    parent_id: Optional[int] = None


@router.post("/api/qualite/audits/{audit_id}/folders")
def create_folder(audit_id: int, body: FolderCreate, request: Request):
    user = _require_qualite_access(request)
    nom = (body.nom or "").strip()
    if not nom:
        raise HTTPException(status_code=400, detail="Nom du sous-dossier obligatoire")
    if len(nom) > 120:
        nom = nom[:120]
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM audit_dossiers WHERE id=?", (audit_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Audit introuvable")
        if body.parent_id is not None:
            if not conn.execute(
                "SELECT 1 FROM audit_folders WHERE id=? AND audit_id=?",
                (body.parent_id, audit_id),
            ).fetchone():
                raise HTTPException(status_code=400, detail="Dossier parent invalide")
        now = _now()
        cur = conn.execute(
            """INSERT INTO audit_folders (audit_id, parent_id, nom, created_at, created_by)
               VALUES (?,?,?,?,?)""",
            (audit_id, body.parent_id, nom, now, user["id"]),
        )
        conn.execute("UPDATE audit_dossiers SET updated_at=?, updated_by=? WHERE id=?",
                     (now, user["id"], audit_id))
        folder_id = cur.lastrowid
        conn.commit()
        row = conn.execute(
            """SELECT f.*, u.nom AS created_by_nom
               FROM audit_folders f LEFT JOIN users u ON f.created_by=u.id
               WHERE f.id=?""", (folder_id,)
        ).fetchone()
    return dict(row)


class FolderUpdate(BaseModel):
    nom: Optional[str] = None
    parent_id: Optional[int] = None
    parent_id_set: bool = False  # True pour permettre parent_id=None explicite


@router.put("/api/qualite/audits/{audit_id}/folders/{folder_id}")
def update_folder(audit_id: int, folder_id: int, body: FolderUpdate, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        f_row = conn.execute(
            "SELECT * FROM audit_folders WHERE id=? AND audit_id=?",
            (folder_id, audit_id),
        ).fetchone()
        if not f_row:
            raise HTTPException(status_code=404, detail="Sous-dossier introuvable")
        data = body.dict(exclude_unset=True)
        fields = []
        params: list = []
        if "nom" in data and data["nom"] is not None:
            nom = (data["nom"] or "").strip()
            if not nom:
                raise HTTPException(status_code=400, detail="Nom obligatoire")
            fields.append("nom=?"); params.append(nom[:120])
        if data.get("parent_id_set"):
            new_parent = data.get("parent_id")
            if new_parent is not None:
                # Pas de boucle : new_parent ne doit pas être un descendant
                if new_parent == folder_id:
                    raise HTTPException(status_code=400, detail="Impossible de déplacer dans lui-même")
                if not conn.execute(
                    "SELECT 1 FROM audit_folders WHERE id=? AND audit_id=?",
                    (new_parent, audit_id),
                ).fetchone():
                    raise HTTPException(status_code=400, detail="Dossier parent invalide")
                # vérif cycles
                cur_pid = new_parent
                visited = set()
                while cur_pid is not None and cur_pid not in visited:
                    visited.add(cur_pid)
                    if cur_pid == folder_id:
                        raise HTTPException(status_code=400, detail="Déplacement créerait une boucle")
                    parent_row = conn.execute(
                        "SELECT parent_id FROM audit_folders WHERE id=?", (cur_pid,)
                    ).fetchone()
                    cur_pid = parent_row["parent_id"] if parent_row else None
            fields.append("parent_id=?"); params.append(new_parent)
        if fields:
            params.append(folder_id)
            conn.execute(f"UPDATE audit_folders SET {', '.join(fields)} WHERE id=?", params)
            conn.execute("UPDATE audit_dossiers SET updated_at=?, updated_by=? WHERE id=?",
                         (_now(), user["id"], audit_id))
            conn.commit()
        row = conn.execute(
            """SELECT f.*, u.nom AS created_by_nom
               FROM audit_folders f LEFT JOIN users u ON f.created_by=u.id
               WHERE f.id=?""", (folder_id,)
        ).fetchone()
    return dict(row)


@router.delete("/api/qualite/audits/{audit_id}/folders/{folder_id}")
def delete_folder(audit_id: int, folder_id: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        if not conn.execute(
            "SELECT 1 FROM audit_folders WHERE id=? AND audit_id=?",
            (folder_id, audit_id),
        ).fetchone():
            raise HTTPException(status_code=404, detail="Sous-dossier introuvable")
        # Récupérer tous les descendants pour supprimer les fichiers du disque
        all_ids = [folder_id]
        cur_layer = [folder_id]
        while cur_layer:
            ph = ",".join("?" * len(cur_layer))
            children = conn.execute(
                f"SELECT id FROM audit_folders WHERE parent_id IN ({ph})", cur_layer
            ).fetchall()
            cur_layer = [c["id"] for c in children]
            all_ids.extend(cur_layer)
        ph = ",".join("?" * len(all_ids))
        files = conn.execute(
            f"SELECT filename FROM audit_fichiers WHERE folder_id IN ({ph})", all_ids
        ).fetchall()
        for f in files:
            path = os.path.join(AUDIT_UPLOAD_DIR, f["filename"])
            if os.path.exists(path):
                try: os.remove(path)
                except Exception: pass
        # Suppressions explicites (PRAGMA foreign_keys=OFF par défaut sur MySifa)
        conn.execute(f"DELETE FROM audit_fichiers WHERE folder_id IN ({ph})", all_ids)
        conn.execute(f"DELETE FROM audit_folders WHERE id IN ({ph})", all_ids)
        conn.execute("UPDATE audit_dossiers SET updated_at=?, updated_by=? WHERE id=?",
                     (_now(), user["id"], audit_id))
        conn.commit()
    return {"ok": True}


# ─── Fichiers ────────────────────────────────────────────────────────

@router.get("/api/qualite/audits/{audit_id}/fichiers")
def list_audit_fichiers(audit_id: int, request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM audit_dossiers WHERE id=?", (audit_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Audit introuvable")
        rows = conn.execute(
            """SELECT f.*, u.nom AS uploaded_by_nom
               FROM audit_fichiers f
               LEFT JOIN users u ON f.uploaded_by=u.id
               WHERE f.audit_id=? ORDER BY f.uploaded_at DESC""",
            (audit_id,),
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/api/qualite/audits/{audit_id}/fichiers")
async def upload_audit_fichier(
    audit_id: int,
    request: Request,
    file: UploadFile = File(...),
    folder_id: Optional[int] = None,
):
    user = _require_qualite_access(request)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Aucun fichier")
    original = _sanitize_filename(file.filename)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM audit_dossiers WHERE id=?", (audit_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Audit introuvable")
        if folder_id is not None:
            if not conn.execute(
                "SELECT 1 FROM audit_folders WHERE id=? AND audit_id=?",
                (folder_id, audit_id),
            ).fetchone():
                raise HTTPException(status_code=400, detail="Sous-dossier invalide")
        ts = datetime.now().strftime("%Y%m%d%H%M%S%f")[:18]
        ext = ""
        if "." in original:
            ext = "." + original.rsplit(".", 1)[1].lower()
        filename = f"audit_{audit_id}_{ts}{ext}"
        dest = os.path.join(AUDIT_UPLOAD_DIR, filename)
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
        size = os.path.getsize(dest)
        conn.execute(
            """INSERT INTO audit_fichiers
               (audit_id, folder_id, filename, original_name, mime_type, size_bytes, uploaded_at, uploaded_by)
               VALUES (?,?,?,?,?,?,?,?)""",
            (audit_id, folder_id, filename, original, file.content_type or None, size, _now(), user["id"]),
        )
        conn.execute("UPDATE audit_dossiers SET updated_at=?, updated_by=? WHERE id=?",
                     (_now(), user["id"], audit_id))
        conn.commit()
    return list_audit_fichiers(audit_id, request)


@router.get("/api/qualite/audits/{audit_id}/fichiers/{file_id}")
def download_audit_fichier(audit_id: int, file_id: int, request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM audit_fichiers WHERE id=? AND audit_id=?", (file_id, audit_id)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Fichier introuvable")
    d = dict(row)
    path = os.path.join(AUDIT_UPLOAD_DIR, d["filename"])
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Fichier absent du serveur")
    media = d.get("mime_type") or "application/octet-stream"
    return FileResponse(path, media_type=media, filename=d["original_name"],
                        headers={"Content-Disposition": f'inline; filename="{d["original_name"]}"'})


@router.delete("/api/qualite/audits/{audit_id}/fichiers/{file_id}")
def delete_audit_fichier(audit_id: int, file_id: int, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM audit_fichiers WHERE id=? AND audit_id=?", (file_id, audit_id)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Fichier introuvable")
        path = os.path.join(AUDIT_UPLOAD_DIR, row["filename"])
        if os.path.exists(path):
            try: os.remove(path)
            except Exception: pass
        conn.execute("DELETE FROM audit_fichiers WHERE id=?", (file_id,))
        conn.execute("UPDATE audit_dossiers SET updated_at=?, updated_by=? WHERE id=?",
                     (_now(), user["id"], audit_id))
        conn.commit()
    return {"ok": True}


class AuditFichierMove(BaseModel):
    folder_id: Optional[int] = None


@router.put("/api/qualite/audits/{audit_id}/fichiers/{file_id}")
def move_audit_fichier(audit_id: int, file_id: int, body: AuditFichierMove, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        if not conn.execute(
            "SELECT 1 FROM audit_fichiers WHERE id=? AND audit_id=?",
            (file_id, audit_id),
        ).fetchone():
            raise HTTPException(status_code=404, detail="Fichier introuvable")
        if body.folder_id is not None:
            if not conn.execute(
                "SELECT 1 FROM audit_folders WHERE id=? AND audit_id=?",
                (body.folder_id, audit_id),
            ).fetchone():
                raise HTTPException(status_code=400, detail="Sous-dossier invalide")
        conn.execute(
            "UPDATE audit_fichiers SET folder_id=? WHERE id=?",
            (body.folder_id, file_id),
        )
        conn.execute("UPDATE audit_dossiers SET updated_at=?, updated_by=? WHERE id=?",
                     (_now(), user["id"], audit_id))
        conn.commit()
    return {"ok": True}


# ─── Discussion ──────────────────────────────────────────────────────

@router.get("/api/qualite/audits/{audit_id}/messages")
def list_audit_messages(audit_id: int, request: Request):
    user = _require_qualite_view(request)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM audit_dossiers WHERE id=?", (audit_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Audit introuvable")
        rows = conn.execute(
            """SELECT m.*, u.nom AS author_nom, u.role AS author_role,
                      f.original_name AS attachment_name, f.mime_type AS attachment_mime
               FROM audit_messages m
               LEFT JOIN users u ON m.author_id=u.id
               LEFT JOIN audit_fichiers f ON m.attachment_id=f.id
               WHERE m.audit_id=? ORDER BY m.created_at ASC, m.id ASC""",
            (audit_id,),
        ).fetchall()
        msgs = [dict(r) for r in rows]
        if msgs:
            last_id = max(m["id"] for m in msgs)
            conn.execute(
                """INSERT INTO audit_message_reads (user_id, audit_id, last_read_message_id, last_read_at)
                   VALUES (?,?,?,?)
                   ON CONFLICT(user_id, audit_id) DO UPDATE SET
                     last_read_message_id=excluded.last_read_message_id,
                     last_read_at=excluded.last_read_at""",
                (user["id"], audit_id, last_id, _now()),
            )
            conn.commit()
    return msgs


class AuditMessageCreate(BaseModel):
    body: str
    attachment_id: Optional[int] = None


@router.post("/api/qualite/audits/{audit_id}/messages")
def post_audit_message(audit_id: int, body: AuditMessageCreate, request: Request):
    user = _require_qualite_access(request)
    text = (body.body or "").strip()
    if not text and not body.attachment_id:
        raise HTTPException(status_code=400, detail="Message vide")
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM audit_dossiers WHERE id=?", (audit_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Audit introuvable")
        if body.attachment_id:
            if not conn.execute(
                "SELECT 1 FROM audit_fichiers WHERE id=? AND audit_id=?", (body.attachment_id, audit_id)
            ).fetchone():
                raise HTTPException(status_code=400, detail="Pièce jointe invalide")
        now = _now()
        cur = conn.execute(
            "INSERT INTO audit_messages (audit_id, author_id, body, attachment_id, created_at) VALUES (?,?,?,?,?)",
            (audit_id, user["id"], text, body.attachment_id, now),
        )
        msg_id = cur.lastrowid
        conn.execute("UPDATE audit_dossiers SET updated_at=?, updated_by=? WHERE id=?",
                     (now, user["id"], audit_id))
        conn.execute(
            """INSERT INTO audit_message_reads (user_id, audit_id, last_read_message_id, last_read_at)
               VALUES (?,?,?,?)
               ON CONFLICT(user_id, audit_id) DO UPDATE SET
                 last_read_message_id=excluded.last_read_message_id,
                 last_read_at=excluded.last_read_at""",
            (user["id"], audit_id, msg_id, now),
        )
        conn.commit()
        row = conn.execute(
            """SELECT m.*, u.nom AS author_nom, u.role AS author_role,
                      f.original_name AS attachment_name, f.mime_type AS attachment_mime
               FROM audit_messages m
               LEFT JOIN users u ON m.author_id=u.id
               LEFT JOIN audit_fichiers f ON m.attachment_id=f.id
               WHERE m.id=?""",
            (msg_id,),
        ).fetchone()
    return dict(row)


# ─── Picker clients (recherche pour création audit) ──────────────────

@router.get("/api/qualite/clients-search")
def search_clients_qualite(request: Request, q: str = ""):
    _require_qualite_view(request)
    q = (q or "").strip()
    with get_db() as conn:
        if q:
            rows = conn.execute(
                """SELECT id, raison_sociale, code, ville
                   FROM clients
                   WHERE raison_sociale LIKE ? OR code LIKE ? OR ville LIKE ?
                   ORDER BY raison_sociale COLLATE NOCASE ASC LIMIT 30""",
                (f"%{q}%", f"%{q}%", f"%{q}%"),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, raison_sociale, code, ville
                   FROM clients
                   ORDER BY raison_sociale COLLATE NOCASE ASC LIMIT 30"""
            ).fetchall()
    return [dict(r) for r in rows]


# ─── Liste auditeurs candidats ───────────────────────────────────────

@router.get("/api/qualite/auditeurs")
def list_auditeurs(request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, nom, role FROM users
               WHERE actif=1 AND role IN ('superadmin','direction','administration','administration_ventes','administration_technique')
               ORDER BY nom"""
        ).fetchall()
    return [dict(r) for r in rows]


# ─── Compteur global Qualité (NC + audits) pour badge sidebar/portail ─

@router.get("/api/qualite/badges")
def qualite_badges(request: Request):
    """Compteur agrégé pour badges sidebar Qualité + tuile portail.

    Retourne :
        nc_unread : messages non lus sur NC ouvertes
        audits_unread : messages non lus sur audits ouverts
        audits_assigned_open : nb d'audits ouverts où l'utilisateur est affecté
        total : somme à afficher dans le badge
    """
    user = _require_qualite_view(request)
    uid = user["id"]
    with get_db() as conn:
        # NC unread
        nc_rows = conn.execute(
            """SELECT nc.id,
                      (SELECT MAX(id) FROM nc_messages WHERE nc_id=nc.id) AS last_id,
                      r.last_read_message_id AS last_read
               FROM nc_dossiers nc
               LEFT JOIN nc_message_reads r ON r.nc_id=nc.id AND r.user_id=?
               WHERE nc.statut != 'cloturee'""",
            (uid,),
        ).fetchall()
        nc_unread = 0
        for r in nc_rows:
            last = r["last_id"] or 0
            seen = r["last_read"] or 0
            if last > seen:
                cnt = conn.execute(
                    "SELECT COUNT(*) FROM nc_messages WHERE nc_id=? AND id>?",
                    (r["id"], seen),
                ).fetchone()[0]
                nc_unread += cnt

        # Audits unread
        a_rows = conn.execute(
            """SELECT a.id,
                      (SELECT MAX(id) FROM audit_messages WHERE audit_id=a.id) AS last_id,
                      r.last_read_message_id AS last_read
               FROM audit_dossiers a
               LEFT JOIN audit_message_reads r ON r.audit_id=a.id AND r.user_id=?
               WHERE a.statut='ouvert'""",
            (uid,),
        ).fetchall()
        audits_unread = 0
        for r in a_rows:
            last = r["last_id"] or 0
            seen = r["last_read"] or 0
            if last > seen:
                cnt = conn.execute(
                    "SELECT COUNT(*) FROM audit_messages WHERE audit_id=? AND id>?",
                    (r["id"], seen),
                ).fetchone()[0]
                audits_unread += cnt

        # Audits où je suis affecté et ouverts
        audits_assigned_open = conn.execute(
            """SELECT COUNT(*) FROM audit_auditeurs aa
               JOIN audit_dossiers a ON a.id=aa.audit_id
               WHERE aa.user_id=? AND a.statut='ouvert'""",
            (uid,),
        ).fetchone()[0]

    total = nc_unread + audits_unread
    return {
        "nc_unread": nc_unread,
        "audits_unread": audits_unread,
        "audits_assigned_open": audits_assigned_open,
        "total": total,
    }


# ═══════════════════════════════════════════════════════════════════════════
# MODULE REFERENTIEL RSE / NORMES & CERTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════
# Endpoints /api/qualite/ref/* : catalogue des normes/certifs (REACH, ISO 14001,
# Ecovadis, etc.) pour repondre aux audits clients environnement / social.
# Lecture : tous les collaborateurs connectes.
# Ecriture (creation/modification/proposition) : tous les collaborateurs.
# Validation / suppression : ROLES_QUALITE (superadmin, direction, administration).

REF_CATEGORIES = ("environnement", "social", "tracabilite", "securite")
REF_STATUTS_SIFA = ("conforme", "partiel", "en_cours", "non_applicable", "a_evaluer")
REF_STATUTS_VALIDATION = ("brouillon", "en_revue", "valide")


def _ref_slugify(text: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", (text or "").strip().lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:80] or "fiche"


def _ref_uniq_slug(conn, base: str, exclude_id: Optional[int] = None) -> str:
    slug = base or "fiche"
    i = 2
    while True:
        row = conn.execute(
            "SELECT id FROM qualite_ref_fiches WHERE slug=?", (slug,),
        ).fetchone()
        if not row or (exclude_id and row["id"] == exclude_id):
            return slug
        slug = f"{base}-{i}"
        i += 1


def _ref_fiche_row_to_dict(row) -> dict:
    d = dict(row)
    return d


def _ref_enrich_light(conn, fiches: List[dict]) -> List[dict]:
    """Ajoute compteurs (nb fichiers, nb questions, nb audits lies) pour la liste."""
    if not fiches:
        return fiches
    ids = [f["id"] for f in fiches]
    ph = ",".join("?" * len(ids))
    files = conn.execute(
        f"SELECT fiche_id, COUNT(*) AS n FROM qualite_ref_fichiers WHERE fiche_id IN ({ph}) GROUP BY fiche_id",
        ids,
    ).fetchall()
    fmap = {r["fiche_id"]: r["n"] for r in files}
    quests = conn.execute(
        f"SELECT fiche_id, COUNT(*) AS n FROM qualite_ref_questions WHERE fiche_id IN ({ph}) GROUP BY fiche_id",
        ids,
    ).fetchall()
    qmap = {r["fiche_id"]: r["n"] for r in quests}
    liens = conn.execute(
        f"SELECT fiche_id, COUNT(*) AS n FROM qualite_ref_audit_liens WHERE fiche_id IN ({ph}) GROUP BY fiche_id",
        ids,
    ).fetchall()
    lmap = {r["fiche_id"]: r["n"] for r in liens}
    for f in fiches:
        f["files_count"] = fmap.get(f["id"], 0)
        f["questions_count"] = qmap.get(f["id"], 0)
        f["audits_count"] = lmap.get(f["id"], 0)
    return fiches


# ─── Meta (categories, statuts) ───────────────────────────────────────────
@router.get("/api/qualite/ref/meta")
def ref_meta(request: Request):
    get_current_user(request)
    return {
        "categories": [
            {"key": "environnement", "label": "Environnement"},
            {"key": "social", "label": "Social & ethique"},
            {"key": "tracabilite", "label": "Tracabilite & qualite"},
            {"key": "securite", "label": "Securite & sante"},
        ],
        "statuts_sifa": [
            {"key": "conforme", "label": "Conforme", "color": "ok"},
            {"key": "partiel", "label": "Partiel", "color": "warn"},
            {"key": "en_cours", "label": "En cours", "color": "accent"},
            {"key": "non_applicable", "label": "Non applicable", "color": "muted"},
            {"key": "a_evaluer", "label": "A evaluer", "color": "muted"},
        ],
        "statuts_validation": [
            {"key": "brouillon", "label": "Brouillon", "color": "muted"},
            {"key": "en_revue", "label": "En revue", "color": "warn"},
            {"key": "valide", "label": "Valide", "color": "ok"},
        ],
    }


# ─── Liste des fiches (avec filtres et recherche) ─────────────────────────
@router.get("/api/qualite/ref/fiches")
def ref_list_fiches(
    request: Request,
    q: Optional[str] = None,
    categorie: Optional[str] = None,
    statut_validation: Optional[str] = None,
    statut_sifa: Optional[str] = None,
    valide_only: int = 0,
):
    get_current_user(request)
    where = ["1=1"]
    params: List = []
    if categorie and categorie in REF_CATEGORIES:
        where.append("categorie=?")
        params.append(categorie)
    if statut_validation and statut_validation in REF_STATUTS_VALIDATION:
        where.append("statut_validation=?")
        params.append(statut_validation)
    if statut_sifa and statut_sifa in REF_STATUTS_SIFA:
        where.append("statut_sifa=?")
        params.append(statut_sifa)
    if valide_only:
        where.append("statut_validation='valide'")
    if q and q.strip():
        # Recherche sur nom, acronyme, definition, position_sifa, tags,
        # + questions type (via sous-requete EXISTS)
        term = f"%{q.strip()}%"
        where.append(
            "(nom LIKE ? OR acronyme LIKE ? OR definition LIKE ? OR position_sifa LIKE ? OR tags LIKE ? "
            "OR EXISTS (SELECT 1 FROM qualite_ref_questions qq WHERE qq.fiche_id=qualite_ref_fiches.id AND qq.texte LIKE ?))"
        )
        params.extend([term, term, term, term, term, term])
    sql = "SELECT * FROM qualite_ref_fiches WHERE " + " AND ".join(where) + " ORDER BY categorie, nom"
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
        fiches = [_ref_fiche_row_to_dict(r) for r in rows]
        fiches = _ref_enrich_light(conn, fiches)
    return fiches


# ─── Detail d une fiche ───────────────────────────────────────────────────
@router.get("/api/qualite/ref/fiches/{fiche_id}")
def ref_get_fiche(fiche_id: int, request: Request):
    get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM qualite_ref_fiches WHERE id=?", (fiche_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Fiche introuvable")
        f = _ref_fiche_row_to_dict(row)

        # Fichiers
        f["fichiers"] = [
            dict(r) for r in conn.execute(
                "SELECT id, original_name, mime_type, size_bytes, uploaded_at, uploaded_by "
                "FROM qualite_ref_fichiers WHERE fiche_id=? ORDER BY uploaded_at DESC",
                (fiche_id,),
            ).fetchall()
        ]
        # Questions type
        f["questions"] = [
            dict(r) for r in conn.execute(
                "SELECT id, texte, reponse, created_at, created_by FROM qualite_ref_questions "
                "WHERE fiche_id=? ORDER BY id",
                (fiche_id,),
            ).fetchall()
        ]
        # Audits lies
        f["audits"] = [
            dict(r) for r in conn.execute(
                """SELECT a.id, a.numero, a.client_nom, a.date_audit, a.statut,
                          l.note, l.created_at AS linked_at
                   FROM qualite_ref_audit_liens l
                   JOIN audit_dossiers a ON a.id = l.audit_id
                   WHERE l.fiche_id=?
                   ORDER BY a.date_audit DESC""",
                (fiche_id,),
            ).fetchall()
        ]
        # Nom du createur / validateur (pour affichage)
        for uid_field in ("created_by", "updated_by", "validated_by"):
            uid = f.get(uid_field)
            if uid:
                u = conn.execute("SELECT nom FROM users WHERE id=?", (uid,)).fetchone()
                f[uid_field + "_nom"] = (u and u["nom"]) or None
    return f


# ─── Creation ─────────────────────────────────────────────────────────────
class RefFicheCreate(BaseModel):
    nom: str
    acronyme: Optional[str] = None
    categorie: str
    definition: str
    position_sifa: Optional[str] = ""
    details: Optional[str] = ""
    statut_sifa: Optional[str] = "a_evaluer"
    source_url: Optional[str] = None
    tags: Optional[str] = ""


@router.post("/api/qualite/ref/fiches")
def ref_create_fiche(body: RefFicheCreate, request: Request):
    user = get_current_user(request)
    nom = (body.nom or "").strip()
    definition = (body.definition or "").strip()
    if not nom:
        raise HTTPException(status_code=400, detail="Nom obligatoire")
    if not definition:
        raise HTTPException(status_code=400, detail="Definition obligatoire")
    if body.categorie not in REF_CATEGORIES:
        raise HTTPException(status_code=400, detail="Categorie invalide")
    statut_sifa = body.statut_sifa or "a_evaluer"
    if statut_sifa not in REF_STATUTS_SIFA:
        statut_sifa = "a_evaluer"
    now = _now()
    with get_db() as conn:
        slug = _ref_uniq_slug(conn, _ref_slugify(nom))
        cur = conn.execute(
            """INSERT INTO qualite_ref_fiches
                   (slug, nom, acronyme, categorie, definition, position_sifa, details,
                    statut_sifa, statut_validation, source_url, tags,
                    created_at, created_by, updated_at, updated_by)
               VALUES (?, ?, ?, ?, ?, ?, ?,
                       ?, 'brouillon', ?, ?,
                       ?, ?, ?, ?)""",
            (slug, nom, (body.acronyme or None), body.categorie, definition,
             (body.position_sifa or ""), (body.details or ""),
             statut_sifa, (body.source_url or None), (body.tags or ""),
             now, user["id"], now, user["id"]),
        )
        fid = cur.lastrowid
        conn.commit()
    return {"id": fid, "slug": slug, "statut_validation": "brouillon"}


# ─── Modification ─────────────────────────────────────────────────────────
class RefFicheUpdate(BaseModel):
    nom: Optional[str] = None
    acronyme: Optional[str] = None
    categorie: Optional[str] = None
    definition: Optional[str] = None
    position_sifa: Optional[str] = None
    details: Optional[str] = None
    statut_sifa: Optional[str] = None
    source_url: Optional[str] = None
    tags: Optional[str] = None


@router.put("/api/qualite/ref/fiches/{fiche_id}")
def ref_update_fiche(fiche_id: int, body: RefFicheUpdate, request: Request):
    user = get_current_user(request)
    fields = []
    params: List = []
    if body.nom is not None:
        nom = body.nom.strip()
        if not nom:
            raise HTTPException(status_code=400, detail="Nom vide")
        fields.append("nom=?"); params.append(nom)
    if body.acronyme is not None:
        fields.append("acronyme=?"); params.append(body.acronyme.strip() or None)
    if body.categorie is not None:
        if body.categorie not in REF_CATEGORIES:
            raise HTTPException(status_code=400, detail="Categorie invalide")
        fields.append("categorie=?"); params.append(body.categorie)
    if body.definition is not None:
        definition = body.definition.strip()
        if not definition:
            raise HTTPException(status_code=400, detail="Definition vide")
        fields.append("definition=?"); params.append(definition)
    if body.position_sifa is not None:
        fields.append("position_sifa=?"); params.append(body.position_sifa or "")
    if body.details is not None:
        fields.append("details=?"); params.append(body.details or "")
    if body.statut_sifa is not None:
        s = body.statut_sifa
        if s not in REF_STATUTS_SIFA:
            raise HTTPException(status_code=400, detail="Statut SIFA invalide")
        fields.append("statut_sifa=?"); params.append(s)
    if body.source_url is not None:
        fields.append("source_url=?"); params.append((body.source_url or "").strip() or None)
    if body.tags is not None:
        fields.append("tags=?"); params.append(body.tags or "")

    if not fields:
        raise HTTPException(status_code=400, detail="Aucun champ a modifier")

    now = _now()
    with get_db() as conn:
        row = conn.execute("SELECT id, statut_validation FROM qualite_ref_fiches WHERE id=?", (fiche_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Fiche introuvable")

        # Si la fiche etait validee, elle repasse en revue (regle metier)
        if row["statut_validation"] == "valide":
            fields.append("statut_validation='en_revue'")
            fields.append("validated_by=NULL")
            fields.append("validated_at=NULL")

        fields.append("updated_at=?"); params.append(now)
        fields.append("updated_by=?"); params.append(user["id"])
        params.append(fiche_id)
        conn.execute(f"UPDATE qualite_ref_fiches SET {', '.join(fields)} WHERE id=?", params)
        conn.commit()
    return {"ok": True}


# ─── Workflow validation ──────────────────────────────────────────────────
@router.post("/api/qualite/ref/fiches/{fiche_id}/submit")
def ref_submit_fiche(fiche_id: int, request: Request):
    """Passe une fiche brouillon en 'en_revue'. Tous les users peuvent soumettre."""
    user = get_current_user(request)
    now = _now()
    with get_db() as conn:
        row = conn.execute("SELECT statut_validation FROM qualite_ref_fiches WHERE id=?", (fiche_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Fiche introuvable")
        if row["statut_validation"] == "valide":
            raise HTTPException(status_code=400, detail="Fiche deja validee")
        conn.execute(
            "UPDATE qualite_ref_fiches SET statut_validation='en_revue', updated_at=?, updated_by=? WHERE id=?",
            (now, user["id"], fiche_id),
        )
        conn.commit()
    return {"ok": True, "statut_validation": "en_revue"}


@router.post("/api/qualite/ref/fiches/{fiche_id}/validate")
def ref_validate_fiche(fiche_id: int, request: Request):
    """Valide une fiche (reserve aux roles Qualite)."""
    user = _require_qualite_access(request)
    now = _now()
    with get_db() as conn:
        row = conn.execute("SELECT id FROM qualite_ref_fiches WHERE id=?", (fiche_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Fiche introuvable")
        conn.execute(
            """UPDATE qualite_ref_fiches
               SET statut_validation='valide', validated_at=?, validated_by=?,
                   updated_at=?, updated_by=?
               WHERE id=?""",
            (now, user["id"], now, user["id"], fiche_id),
        )
        conn.commit()
    return {"ok": True, "statut_validation": "valide"}


@router.post("/api/qualite/ref/fiches/{fiche_id}/reject")
def ref_reject_fiche(fiche_id: int, request: Request):
    """Rejette une fiche en revue (reserve aux roles Qualite)."""
    user = _require_qualite_access(request)
    now = _now()
    with get_db() as conn:
        row = conn.execute("SELECT id FROM qualite_ref_fiches WHERE id=?", (fiche_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Fiche introuvable")
        conn.execute(
            "UPDATE qualite_ref_fiches SET statut_validation='brouillon', updated_at=?, updated_by=? WHERE id=?",
            (now, user["id"], fiche_id),
        )
        conn.commit()
    return {"ok": True, "statut_validation": "brouillon"}


@router.delete("/api/qualite/ref/fiches/{fiche_id}")
def ref_delete_fiche(fiche_id: int, request: Request):
    """Supprime une fiche (reserve aux roles Qualite). Cascade sur fichiers/questions/liens."""
    _require_qualite_access(request)
    with get_db() as conn:
        # Purge fichiers physiques d abord
        files = conn.execute(
            "SELECT filename FROM qualite_ref_fichiers WHERE fiche_id=?", (fiche_id,),
        ).fetchall()
        for f in files:
            path = os.path.join(QUALITE_UPLOAD_DIR, f["filename"])
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
        conn.execute("DELETE FROM qualite_ref_fiches WHERE id=?", (fiche_id,))
        conn.commit()
    return {"ok": True}


# ─── Questions type (avec reponse) ────────────────────────────────────────
class RefQuestionCreate(BaseModel):
    texte: str
    reponse: Optional[str] = ""


class RefQuestionUpdate(BaseModel):
    texte: Optional[str] = None
    reponse: Optional[str] = None


@router.post("/api/qualite/ref/fiches/{fiche_id}/questions")
def ref_add_question(fiche_id: int, body: RefQuestionCreate, request: Request):
    user = get_current_user(request)
    texte = (body.texte or "").strip()
    if not texte or len(texte) > 400:
        raise HTTPException(status_code=400, detail="Question invalide (1 a 400 caracteres)")
    reponse = (body.reponse or "").strip()
    if len(reponse) > 4000:
        raise HTTPException(status_code=400, detail="Reponse trop longue (max 4000 caracteres)")
    now = _now()
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM qualite_ref_fiches WHERE id=?", (fiche_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Fiche introuvable")
        cur = conn.execute(
            "INSERT INTO qualite_ref_questions (fiche_id, texte, reponse, created_at, created_by) VALUES (?, ?, ?, ?, ?)",
            (fiche_id, texte, reponse, now, user["id"]),
        )
        conn.commit()
    return {"id": cur.lastrowid, "texte": texte, "reponse": reponse}


@router.put("/api/qualite/ref/fiches/{fiche_id}/questions/{qid}")
def ref_update_question(fiche_id: int, qid: int, body: RefQuestionUpdate, request: Request):
    get_current_user(request)
    fields = []
    params: List = []
    if body.texte is not None:
        t = body.texte.strip()
        if not t or len(t) > 400:
            raise HTTPException(status_code=400, detail="Question invalide (1 a 400 caracteres)")
        fields.append("texte=?"); params.append(t)
    if body.reponse is not None:
        r = body.reponse.strip()
        if len(r) > 4000:
            raise HTTPException(status_code=400, detail="Reponse trop longue (max 4000 caracteres)")
        fields.append("reponse=?"); params.append(r)
    if not fields:
        raise HTTPException(status_code=400, detail="Aucun champ a modifier")
    params.extend([qid, fiche_id])
    with get_db() as conn:
        conn.execute(
            f"UPDATE qualite_ref_questions SET {', '.join(fields)} WHERE id=? AND fiche_id=?",
            params,
        )
        conn.commit()
    return {"ok": True}


@router.delete("/api/qualite/ref/fiches/{fiche_id}/questions/{qid}")
def ref_delete_question(fiche_id: int, qid: int, request: Request):
    get_current_user(request)
    with get_db() as conn:
        conn.execute("DELETE FROM qualite_ref_questions WHERE id=? AND fiche_id=?", (qid, fiche_id))
        conn.commit()
    return {"ok": True}


# ─── Suggestions d autocompletion (questions + noms) ──────────────────────
@router.get("/api/qualite/ref/suggestions")
def ref_suggestions(request: Request, q: Optional[str] = None, limit: int = 8):
    get_current_user(request)
    term = (q or "").strip()
    if not term or len(term) < 2:
        return []
    like = f"%{term}%"
    limit = max(1, min(int(limit or 8), 30))
    with get_db() as conn:
        questions = conn.execute(
            """SELECT DISTINCT qq.texte, f.id AS fiche_id, f.nom AS fiche_nom, f.acronyme
               FROM qualite_ref_questions qq
               JOIN qualite_ref_fiches f ON f.id = qq.fiche_id
               WHERE qq.texte LIKE ?
               ORDER BY LENGTH(qq.texte) LIMIT ?""",
            (like, limit),
        ).fetchall()
        # Complete avec quelques noms de fiches matchants
        noms = conn.execute(
            """SELECT id AS fiche_id, nom AS fiche_nom, acronyme
               FROM qualite_ref_fiches
               WHERE nom LIKE ? OR acronyme LIKE ?
               ORDER BY nom LIMIT ?""",
            (like, like, limit),
        ).fetchall()
    return {
        "questions": [dict(r) for r in questions],
        "fiches": [dict(r) for r in noms],
    }


# ─── Liens vers audits ────────────────────────────────────────────────────
class RefAuditLink(BaseModel):
    audit_id: int
    note: Optional[str] = None


@router.post("/api/qualite/ref/fiches/{fiche_id}/audits")
def ref_link_audit(fiche_id: int, body: RefAuditLink, request: Request):
    user = get_current_user(request)
    now = _now()
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM qualite_ref_fiches WHERE id=?", (fiche_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Fiche introuvable")
        if not conn.execute("SELECT 1 FROM audit_dossiers WHERE id=?", (body.audit_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Audit introuvable")
        conn.execute(
            """INSERT OR REPLACE INTO qualite_ref_audit_liens
                   (fiche_id, audit_id, note, created_at, created_by)
               VALUES (?, ?, ?, ?, ?)""",
            (fiche_id, body.audit_id, (body.note or None), now, user["id"]),
        )
        conn.commit()
    return {"ok": True}


@router.delete("/api/qualite/ref/fiches/{fiche_id}/audits/{aid}")
def ref_unlink_audit(fiche_id: int, aid: int, request: Request):
    get_current_user(request)
    with get_db() as conn:
        conn.execute(
            "DELETE FROM qualite_ref_audit_liens WHERE fiche_id=? AND audit_id=?",
            (fiche_id, aid),
        )
        conn.commit()
    return {"ok": True}


@router.get("/api/qualite/ref/audits-picker")
def ref_audits_picker(request: Request, q: Optional[str] = None):
    """Liste courte d audits pour le picker de lien (dernier annee, plus recherche)."""
    get_current_user(request)
    where = ["1=1"]
    params: List = []
    if q and q.strip():
        term = f"%{q.strip()}%"
        where.append("(numero LIKE ? OR client_nom LIKE ? OR description LIKE ?)")
        params.extend([term, term, term])
    sql = ("SELECT id, numero, client_nom, date_audit, statut FROM audit_dossiers "
           "WHERE " + " AND ".join(where) + " ORDER BY date_audit DESC LIMIT 40")
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


# ─── Fichiers (upload / download / delete) ────────────────────────────────
@router.post("/api/qualite/ref/fiches/{fiche_id}/fichiers")
async def ref_upload_fichier(fiche_id: int, request: Request, file: UploadFile = File(...)):
    user = get_current_user(request)
    now = _now()
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM qualite_ref_fiches WHERE id=?", (fiche_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Fiche introuvable")

        safe = _sanitize_filename(file.filename or "fichier")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ref_{fiche_id}_{ts}_{safe}"
        dest = os.path.join(QUALITE_UPLOAD_DIR, filename)
        content = await file.read()
        with open(dest, "wb") as out:
            out.write(content)
        size = len(content)
        cur = conn.execute(
            """INSERT INTO qualite_ref_fichiers
                   (fiche_id, filename, original_name, mime_type, size_bytes, uploaded_at, uploaded_by)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (fiche_id, filename, file.filename or safe, file.content_type or None, size, now, user["id"]),
        )
        conn.commit()
    return {"id": cur.lastrowid, "original_name": file.filename, "size_bytes": size}


@router.get("/api/qualite/ref/fichiers/{fid}/download")
def ref_download_fichier(fid: int, request: Request):
    get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT filename, original_name, mime_type FROM qualite_ref_fichiers WHERE id=?", (fid,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Fichier introuvable")
    path = os.path.join(QUALITE_UPLOAD_DIR, row["filename"])
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Fichier absent du disque")
    return FileResponse(path, media_type=row["mime_type"] or "application/octet-stream",
                        filename=row["original_name"])


@router.delete("/api/qualite/ref/fichiers/{fid}")
def ref_delete_fichier(fid: int, request: Request):
    get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT filename FROM qualite_ref_fichiers WHERE id=?", (fid,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Fichier introuvable")
        path = os.path.join(QUALITE_UPLOAD_DIR, row["filename"])
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        conn.execute("DELETE FROM qualite_ref_fichiers WHERE id=?", (fid,))
        conn.commit()
    return {"ok": True}


# ============================================================================
# RESSOURCES FOURNISSEURS — un dossier par fournisseur avec certificats
# ============================================================================

RESSOURCES_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "qualite")
os.makedirs(RESSOURCES_UPLOAD_DIR, exist_ok=True)


def _compute_cert_status(date_expiration: Optional[str]) -> str:
    """'valide' | 'expire_bientot' (<60j) | 'expire' | 'sans_date' (pas de date d'expiration)."""
    if not date_expiration:
        return "sans_date"
    try:
        dexp = datetime.strptime(date_expiration[:10], "%Y-%m-%d").date()
    except Exception:
        return "sans_date"
    today = datetime.now().date()
    if dexp < today:
        return "expire"
    delta = (dexp - today).days
    if delta <= 60:
        return "expire_bientot"
    return "valide"


def _cert_row_to_dict(row) -> dict:
    d = dict(row)
    d["statut"] = _compute_cert_status(d.get("date_expiration"))
    return d


# ─── Liste fournisseurs (avec compteurs certifs) ─────────────────────

@router.get("/api/qualite/ressources/fournisseurs")
def ressources_list_fournisseurs(request: Request):
    """Retourne 2 listes agregees pour la vue Ressources :
       - groupes : un item par groupe existant, avec stats agregees sur toutes les branches
       - fournisseurs : fournisseurs sans groupe (traites individuellement)
    Chaque item porte : id (pour fournisseurs) ou groupe (pour groupes),
    label, sub-label, stats {total, valide, soon, exp, nod}.
    """
    _require_qualite_view(request)
    with get_db() as conn:
        # Charger fournisseurs + certifs en 2 requetes puis agreger
        fours = [dict(r) for r in conn.execute(
            """SELECT id, nom, licence, certificat, groupe, branche, pays_origine
               FROM fournisseurs_fsc
               ORDER BY groupe COLLATE NOCASE ASC, nom COLLATE NOCASE ASC"""
        ).fetchall()]
        # Charger toutes les dates d'expiration + groupe_ref
        cert_rows = conn.execute(
            """SELECT fournisseur_id, date_expiration, groupe_ref
               FROM qualite_fournisseur_certificats"""
        ).fetchall()
        certs_by_four = {}
        for cr in cert_rows:
            certs_by_four.setdefault(cr["fournisseur_id"], []).append({
                "date_expiration": cr["date_expiration"],
                "groupe_ref": cr["groupe_ref"],
            })

    def _stats(cert_list):
        s = {"total": 0, "valide": 0, "soon": 0, "exp": 0, "nod": 0}
        for c in cert_list:
            s["total"] += 1
            st = _compute_cert_status(c["date_expiration"])
            if st == "valide": s["valide"] += 1
            elif st == "expire_bientot": s["soon"] += 1
            elif st == "expire": s["exp"] += 1
            elif st == "sans_date": s["nod"] += 1
        return s

    # Separer groupes vs fournisseurs isolés
    groupes_map = {}
    fournisseurs_indep = []
    for f in fours:
        f_certs = certs_by_four.get(f["id"], [])
        f_stats = _stats(f_certs)
        g = (f.get("groupe") or "").strip()
        if g:
            if g not in groupes_map:
                groupes_map[g] = {
                    "groupe": g,
                    "branches": [],
                    "stats": {"total": 0, "valide": 0, "soon": 0, "exp": 0, "nod": 0},
                }
            groupes_map[g]["branches"].append({
                "id": f["id"], "nom": f["nom"], "branche": f.get("branche"),
                "licence": f.get("licence"), "certificat": f.get("certificat"),
                "pays_origine": f.get("pays_origine"),
                "cert_stats": f_stats,
            })
            for k in ("total", "valide", "soon", "exp", "nod"):
                groupes_map[g]["stats"][k] += f_stats[k]
        else:
            fournisseurs_indep.append({
                "id": f["id"], "nom": f["nom"],
                "licence": f.get("licence"), "certificat": f.get("certificat"),
                "pays_origine": f.get("pays_origine"),
                "cert_stats": f_stats,
            })

    groupes = sorted(groupes_map.values(), key=lambda x: x["groupe"].lower())
    flat = []
    for f in fours:
        key = (f.get("groupe") or f["nom"] or "").lower()
        flat.append((key, f["id"]))
    flat.sort(key=lambda x: x[0])
    order = [fid for _, fid in flat]
    return {"groupes": groupes, "fournisseurs": fournisseurs_indep, "order": order}




class FournisseurPatchBody(BaseModel):
    nom: Optional[str] = None
    licence: Optional[str] = None
    certificat: Optional[str] = None
    has_fsc: Optional[bool] = None
    groupe: Optional[str] = None
    branche: Optional[str] = None
    pays_origine: Optional[str] = None


@router.patch("/api/qualite/ressources/fournisseurs/{four_id}")
def ressources_patch_fournisseur(four_id: int, body: FournisseurPatchBody, request: Request):
    _require_qualite_access(request)
    d = body.model_dump(exclude_unset=True)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM fournisseurs_fsc WHERE id=?", (four_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Fournisseur introuvable")
        sets, vals = [], []
        if "nom" in d:
            v = (d["nom"] or "").strip()
            if not v:
                raise HTTPException(status_code=400, detail="Nom obligatoire")
            sets.append("nom=?"); vals.append(v)
        if "licence" in d:
            v = (d["licence"] or "").strip() or None
            sets.append("licence=?"); vals.append(v)
        if "certificat" in d:
            v = (d["certificat"] or "").strip() or None
            sets.append("certificat=?"); vals.append(v)
        if "has_fsc" in d:
            sets.append("has_fsc=?"); vals.append(1 if bool(d["has_fsc"]) else 0)
        if "groupe" in d:
            v = (d["groupe"] or "").strip() or None
            sets.append("groupe=?"); vals.append(v)
        if "branche" in d:
            v = (d["branche"] or "").strip() or None
            sets.append("branche=?"); vals.append(v)
        if "pays_origine" in d:
            v = (d["pays_origine"] or "").strip() or None
            sets.append("pays_origine=?"); vals.append(v)
        if sets:
            vals.append(four_id)
            try:
                conn.execute(f"UPDATE fournisseurs_fsc SET {', '.join(sets)} WHERE id=?", vals)
                conn.commit()
            except Exception as e:
                raise HTTPException(status_code=409, detail=f"Erreur : {e}")
    return ressources_get_fournisseur(four_id, request)


# ─── Detail d'un groupe (toutes les branches + certifs agreges) ──────
@router.get("/api/qualite/ressources/groupes/{groupe_nom:path}")
def ressources_get_groupe(groupe_nom: str, request: Request):
    _require_qualite_view(request)
    g = (groupe_nom or "").strip()
    if not g:
        raise HTTPException(status_code=400, detail="Nom de groupe requis")
    with get_db() as conn:
        branches = [dict(r) for r in conn.execute(
            """SELECT id, nom, licence, certificat, branche, groupe
               FROM fournisseurs_fsc
               WHERE LOWER(TRIM(groupe)) = LOWER(?)
               ORDER BY branche COLLATE NOCASE ASC, nom COLLATE NOCASE ASC""",
            (g,),
        ).fetchall()]
        if not branches:
            raise HTTPException(status_code=404, detail="Groupe introuvable")
        b_ids = [b["id"] for b in branches]
        qmarks = ",".join(["?"] * len(b_ids))
        certs = conn.execute(
            f"""SELECT c.*, u.nom AS uploaded_by_nom, f.nom AS fournisseur_nom, f.branche AS fournisseur_branche
                FROM qualite_fournisseur_certificats c
                LEFT JOIN users u ON u.id = c.uploaded_by
                LEFT JOIN fournisseurs_fsc f ON f.id = c.fournisseur_id
                WHERE c.fournisseur_id IN ({qmarks})
                ORDER BY COALESCE(c.date_expiration, c.uploaded_at) DESC, c.id DESC""",
            b_ids,
        ).fetchall()
        certs = [_cert_row_to_dict(r) for r in certs]
        # Charger fiches liees
        if certs:
            ids = [c["id"] for c in certs]
            qm = ",".join(["?"] * len(ids))
            links = conn.execute(
                f"""SELECT l.certificat_id, l.fiche_id, f.nom AS fiche_nom, f.acronyme AS fiche_acronyme, f.slug AS fiche_slug, f.categorie AS fiche_categorie
                    FROM qualite_fournisseur_certificat_fiches l
                    JOIN qualite_ref_fiches f ON f.id = l.fiche_id
                    WHERE l.certificat_id IN ({qm})""",
                ids,
            ).fetchall()
            by_cert = {}
            for lk in links:
                by_cert.setdefault(lk["certificat_id"], []).append({
                    "fiche_id": lk["fiche_id"], "nom": lk["fiche_nom"],
                    "acronyme": lk["fiche_acronyme"], "slug": lk["fiche_slug"],
                    "categorie": lk["fiche_categorie"],
                })
            for c in certs:
                c["fiches"] = by_cert.get(c["id"], [])
        # Ajouter fournisseur_nom + fournisseur_branche depuis la query
        for c in certs:
            fb = next((b for b in branches if b["id"] == c["fournisseur_id"]), None)
            if fb:
                c["fournisseur_nom"] = fb["nom"]
                c["fournisseur_branche"] = fb.get("branche")
    return {
        "groupe": g,
        "branches": branches,
        "certificats": certs,
    }


# ─── Détail d'un fournisseur (avec certificats + fiches liées) ───────

@router.get("/api/qualite/ressources/fournisseurs/{four_id}")
def ressources_get_fournisseur(four_id: int, request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        four = conn.execute(
            "SELECT id, nom, licence, certificat, groupe, branche, pays_origine FROM fournisseurs_fsc WHERE id=?",
            (four_id,),
        ).fetchone()
        if not four:
            raise HTTPException(status_code=404, detail="Fournisseur introuvable")
        certs = conn.execute(
            """SELECT c.*, u.nom AS uploaded_by_nom
               FROM qualite_fournisseur_certificats c
               LEFT JOIN users u ON u.id = c.uploaded_by
               WHERE c.fournisseur_id=?
               ORDER BY COALESCE(c.date_expiration, c.uploaded_at) DESC, c.id DESC""",
            (four_id,),
        ).fetchall()
        certs = [_cert_row_to_dict(r) for r in certs]
        if certs:
            ids = [c["id"] for c in certs]
            qmarks = ",".join(["?"] * len(ids))
            links = conn.execute(
                f"""SELECT l.certificat_id, l.fiche_id, f.nom AS fiche_nom, f.acronyme AS fiche_acronyme, f.slug AS fiche_slug, f.categorie AS fiche_categorie
                    FROM qualite_fournisseur_certificat_fiches l
                    JOIN qualite_ref_fiches f ON f.id = l.fiche_id
                    WHERE l.certificat_id IN ({qmarks})""",
                ids,
            ).fetchall()
            by_cert = {}
            for lk in links:
                by_cert.setdefault(lk["certificat_id"], []).append({
                    "fiche_id": lk["fiche_id"],
                    "nom": lk["fiche_nom"],
                    "acronyme": lk["fiche_acronyme"],
                    "slug": lk["fiche_slug"],
                    "categorie": lk["fiche_categorie"],
                })
            for c in certs:
                c["fiches"] = by_cert.get(c["id"], [])
        else:
            for c in certs:
                c["fiches"] = []
    return {"fournisseur": dict(four), "certificats": certs}


# ─── Upload d'un certificat ──────────────────────────────────────────

@router.post("/api/qualite/ressources/fournisseurs/{four_id}/certificats")
async def ressources_upload_certificat(
    four_id: int,
    request: Request,
    file: UploadFile = File(...),
    titre: str = Form(""),
    date_emission: str = Form(""),
    date_expiration: str = Form(""),
    commentaire: str = Form(""),
    fiche_ids: str = Form(""),
    niveau: str = Form("branche"),
):
    user = _require_qualite_access(request)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Aucun fichier")
    original = _sanitize_filename(file.filename)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM fournisseurs_fsc WHERE id=?", (four_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Fournisseur introuvable")
        ts = datetime.now().strftime("%Y%m%d%H%M%S%f")[:18]
        ext = ""
        if "." in original:
            ext = "." + original.rsplit(".", 1)[1].lower()
        filename = f"res_{four_id}_{ts}{ext}"
        dest = os.path.join(RESSOURCES_UPLOAD_DIR, filename)
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
        size = os.path.getsize(dest)
        # Determiner groupe_ref selon niveau demande
        groupe_ref = None
        if (niveau or "").strip().lower() == "groupe":
            fr = conn.execute(
                "SELECT groupe FROM fournisseurs_fsc WHERE id=?", (four_id,)
            ).fetchone()
            g = (fr["groupe"] or "").strip() if fr and "groupe" in fr.keys() and fr["groupe"] else ""
            groupe_ref = g or None
        conn.execute(
            """INSERT INTO qualite_fournisseur_certificats
               (fournisseur_id, filename, original_name, mime_type, size_bytes,
                titre, date_emission, date_expiration, commentaire, uploaded_at, uploaded_by, groupe_ref)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                four_id, filename, original, file.content_type or None, size,
                (titre or "").strip(),
                (date_emission or "").strip() or None,
                (date_expiration or "").strip() or None,
                (commentaire or "").strip(),
                _now(), user["id"], groupe_ref,
            ),
        )
        cert_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        # Fiches liées : CSV "1,3,7"
        wanted = []
        for tok in (fiche_ids or "").split(","):
            tok = tok.strip()
            if tok.isdigit():
                wanted.append(int(tok))
        if wanted:
            existing = conn.execute(
                f"SELECT id FROM qualite_ref_fiches WHERE id IN ({','.join(['?']*len(wanted))})",
                wanted,
            ).fetchall()
            ok_ids = {r["id"] for r in existing}
            for fid in wanted:
                if fid in ok_ids:
                    conn.execute(
                        "INSERT OR IGNORE INTO qualite_fournisseur_certificat_fiches (certificat_id, fiche_id) VALUES (?,?)",
                        (cert_id, fid),
                    )
        conn.commit()
    return ressources_get_fournisseur(four_id, request)


# ─── Mise à jour métadonnées / fiches liées d'un certificat ──────────

class CertPatchBody(BaseModel):
    titre: Optional[str] = None
    date_emission: Optional[str] = None
    date_expiration: Optional[str] = None
    commentaire: Optional[str] = None
    fiche_ids: Optional[List[int]] = None
    niveau: Optional[str] = None  # 'branche' | 'groupe' — met a jour groupe_ref


@router.patch("/api/qualite/ressources/certificats/{cert_id}")
def ressources_patch_certificat(cert_id: int, body: CertPatchBody, request: Request):
    _require_qualite_access(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM qualite_fournisseur_certificats WHERE id=?", (cert_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Certificat introuvable")
        sets = []
        vals = []
        d = body.model_dump(exclude_unset=True)
        if "titre" in d:
            sets.append("titre=?"); vals.append((d["titre"] or "").strip())
        if "date_emission" in d:
            v = (d["date_emission"] or "").strip() or None
            sets.append("date_emission=?"); vals.append(v)
        if "date_expiration" in d:
            v = (d["date_expiration"] or "").strip() or None
            sets.append("date_expiration=?"); vals.append(v)
            # Reset des annonces si nouvelle date : un nouveau cycle d'alertes s'ouvre
            conn.execute("DELETE FROM qualite_cert_expiration_annonces WHERE certificat_id=?", (cert_id,))
        if "commentaire" in d:
            sets.append("commentaire=?"); vals.append((d["commentaire"] or "").strip())
        if "niveau" in d:
            niv = (d["niveau"] or "").strip().lower()
            if niv == "groupe":
                fr = conn.execute(
                    """SELECT f.groupe FROM fournisseurs_fsc f
                       WHERE f.id=?""", (row["fournisseur_id"],),
                ).fetchone()
                g = (fr["groupe"] or "").strip() if fr and "groupe" in fr.keys() and fr["groupe"] else ""
                sets.append("groupe_ref=?"); vals.append(g or None)
            else:
                sets.append("groupe_ref=?"); vals.append(None)
        if sets:
            vals.append(cert_id)
            conn.execute(f"UPDATE qualite_fournisseur_certificats SET {', '.join(sets)} WHERE id=?", vals)
        if "fiche_ids" in d and d["fiche_ids"] is not None:
            conn.execute("DELETE FROM qualite_fournisseur_certificat_fiches WHERE certificat_id=?", (cert_id,))
            wanted = [int(x) for x in d["fiche_ids"] if isinstance(x, int) or (isinstance(x, str) and x.isdigit())]
            if wanted:
                existing = conn.execute(
                    f"SELECT id FROM qualite_ref_fiches WHERE id IN ({','.join(['?']*len(wanted))})",
                    wanted,
                ).fetchall()
                ok_ids = {r["id"] for r in existing}
                for fid in wanted:
                    if fid in ok_ids:
                        conn.execute(
                            "INSERT OR IGNORE INTO qualite_fournisseur_certificat_fiches (certificat_id, fiche_id) VALUES (?,?)",
                            (cert_id, fid),
                        )
        conn.commit()
        four_id = row["fournisseur_id"]
    return ressources_get_fournisseur(four_id, request)


# ─── Suppression / téléchargement d'un certificat ────────────────────

@router.delete("/api/qualite/ressources/certificats/{cert_id}")
def ressources_delete_certificat(cert_id: int, request: Request):
    _require_qualite_access(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM qualite_fournisseur_certificats WHERE id=?", (cert_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Certificat introuvable")
        path = os.path.join(RESSOURCES_UPLOAD_DIR, row["filename"])
        if os.path.exists(path):
            try: os.remove(path)
            except Exception: pass
        conn.execute("DELETE FROM qualite_fournisseur_certificats WHERE id=?", (cert_id,))
        conn.commit()
    return {"ok": True}


@router.get("/api/qualite/ressources/certificats/{cert_id}/download")
def ressources_download_certificat(cert_id: int, request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM qualite_fournisseur_certificats WHERE id=?", (cert_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Certificat introuvable")
    d = dict(row)
    path = os.path.join(RESSOURCES_UPLOAD_DIR, d["filename"])
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Fichier absent du serveur")
    media = d.get("mime_type") or "application/octet-stream"
    return FileResponse(path, media_type=media, filename=d["original_name"],
                        headers={"Content-Disposition": f'inline; filename="{d["original_name"]}"'})


# ─── Alertes expiration (liste + scan pour annonces auto) ────────────

@router.get("/api/qualite/ressources/expiration-alerts")
def ressources_expiration_alerts(request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT c.id, c.fournisseur_id, c.titre, c.original_name, c.date_expiration,
                      f.nom AS fournisseur_nom
               FROM qualite_fournisseur_certificats c
               JOIN fournisseurs_fsc f ON f.id = c.fournisseur_id
               WHERE c.date_expiration IS NOT NULL AND c.date_expiration != ''
               ORDER BY c.date_expiration ASC"""
        ).fetchall()
    today = datetime.now().date()
    expired = []
    j30 = []
    j60 = []
    for r in rows:
        try:
            dexp = datetime.strptime(r["date_expiration"][:10], "%Y-%m-%d").date()
        except Exception:
            continue
        delta = (dexp - today).days
        item = {
            "id": r["id"],
            "fournisseur_id": r["fournisseur_id"],
            "fournisseur_nom": r["fournisseur_nom"],
            "titre": r["titre"] or r["original_name"],
            "date_expiration": r["date_expiration"],
            "jours": delta,
        }
        if delta < 0:
            expired.append(item)
        elif delta <= 30:
            j30.append(item)
        elif delta <= 60:
            j60.append(item)
    return {"expired": expired, "j30": j30, "j60": j60}


def _emit_expiration_annonce(conn, scope: str, titre: str, message: str) -> None:
    """Insère une annonce dans update_announcements (best-effort, jamais bloquant).
    Dédup soft : si une annonce identique existe déjà et est active, on rafraîchit
    juste son message plutôt que d'empiler."""
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(update_announcements)").fetchall()}
    except Exception:
        return
    if not cols:
        return
    try:
        exist = conn.execute(
            "SELECT 1 FROM update_announcements WHERE scope=? AND titre=? AND active=1 LIMIT 1",
            (scope, titre),
        ).fetchone()
        if exist:
            conn.execute(
                "UPDATE update_announcements SET message=?, created_at=? WHERE scope=? AND titre=? AND active=1",
                (message, _now(), scope, titre),
            )
            return
        conn.execute(
            "INSERT INTO update_announcements (scope,titre,message,created_at,created_by,active) VALUES (?,?,?,?,?,1)",
            (scope, titre, message, _now(), "système"),
        )
    except Exception:
        pass


@router.post("/api/qualite/ressources/scan-expirations")
def ressources_scan_expirations(request: Request):
    """Scan des certificats : émet une annonce interne pour chaque bucket
    (expired / j30 / j60) fraîchement atteint et non encore annoncé.
    Idempotent : peut être appelé au boot et à chaque ouverture de MyQualité."""
    _require_qualite_view(request)
    alerts = ressources_expiration_alerts(request)
    with get_db() as conn:
        already = {
            (r["certificat_id"], r["bucket"])
            for r in conn.execute("SELECT certificat_id, bucket FROM qualite_cert_expiration_annonces").fetchall()
        }
        emitted = {"expired": 0, "j30": 0, "j60": 0}
        for bucket, items in (("expired", alerts["expired"]), ("j30", alerts["j30"]), ("j60", alerts["j60"])):
            new_items = [it for it in items if (it["id"], bucket) not in already]
            if not new_items:
                continue
            lines = "".join(
                f"<li style='margin-bottom:4px'>{it['fournisseur_nom']} — {it['titre']} "
                f"({'expiré depuis ' + str(-it['jours']) + 'j' if it['jours']<0 else 'dans ' + str(it['jours']) + 'j'})</li>"
                for it in new_items
            )
            label = {"expired": "Certificats expirés", "j30": "Certificats — expiration < 30 jours", "j60": "Certificats — expiration < 60 jours"}[bucket]
            msg = (
                f"<div style='font-size:13px;line-height:1.7;color:var(--text2)'>"
                f"<div style='font-size:14px;font-weight:700;color:var(--text);margin-bottom:8px'>{label}</div>"
                f"<ul style='margin:0;padding-left:18px'>{lines}</ul></div>"
            )
            _emit_expiration_annonce(conn, "qualite", label, msg)
            for it in new_items:
                conn.execute(
                    "INSERT OR IGNORE INTO qualite_cert_expiration_annonces (certificat_id, bucket, annonce_at) VALUES (?,?,?)",
                    (it["id"], bucket, _now()),
                )
                emitted[bucket] += 1
        conn.commit()
    return {"ok": True, "emitted": emitted, "counts": {"expired": len(alerts["expired"]), "j30": len(alerts["j30"]), "j60": len(alerts["j60"])}}


# ============================================================================
# AUDIT — extension matrice fournisseurs × certifications demandées client
# ============================================================================


def _matrice_status_from_cert_stats(cert_stats: dict) -> str:
    """Réduit les statuts individuels des certifs liées en un statut global :
    - 'ok' : au moins un certif valide
    - 'expire_bientot' : que des certifs qui expirent bientôt (aucun valide)
    - 'expire' : que des certifs expirés
    - 'sans_date' : que des certifs sans date d'expiration
    - 'manquant' : aucun certif
    """
    if cert_stats.get("valide", 0) > 0:
        return "ok"
    if cert_stats.get("expire_bientot", 0) > 0:
        return "expire_bientot"
    if cert_stats.get("expire", 0) > 0:
        return "expire"
    if cert_stats.get("sans_date", 0) > 0:
        return "sans_date"
    return "manquant"


@router.get("/api/qualite/audits/{audit_id}/matrice")
def audit_get_matrice(audit_id: int, request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM audit_dossiers WHERE id=?", (audit_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Audit introuvable")
        four_rows = conn.execute(
            """SELECT f.id, f.nom, f.licence, f.certificat, f.groupe, f.branche
               FROM audit_fournisseurs af
               JOIN fournisseurs_fsc f ON f.id = af.fournisseur_id
               WHERE af.audit_id=?
               ORDER BY f.nom COLLATE NOCASE ASC""",
            (audit_id,),
        ).fetchall()
        fiche_rows = conn.execute(
            """SELECT r.id, r.slug, r.nom, r.acronyme, r.categorie
               FROM audit_certifications_demandees ac
               JOIN qualite_ref_fiches r ON r.id = ac.fiche_id
               WHERE ac.audit_id=?
               ORDER BY r.nom COLLATE NOCASE ASC""",
            (audit_id,),
        ).fetchall()
        four_ids = [r["id"] for r in four_rows]
        fiche_ids = [r["id"] for r in fiche_rows]
        # Charger tous les liens certif × fiche pour les fournisseurs concernés
        cert_link_stats = {}   # {(four_id, fiche_id): {"valide":n,"expire_bientot":n,"expire":n,"sans_date":n}}
        cert_examples = {}     # {(four_id, fiche_id): [cert_id,...]}
        # Mapping groupe -> [fournisseurs_ids de four_rows appartenant a ce groupe]
        groupe_of_four = {r["id"]: (r["groupe"] or "").strip() for r in four_rows}
        fours_by_groupe = {}
        for fid, g in groupe_of_four.items():
            if g:
                fours_by_groupe.setdefault(g.lower(), []).append(fid)

        def _add_cert_link(fid, fiche_id, cert_id, date_exp, seen_ids):
            if cert_id in seen_ids.get((fid, fiche_id), set()):
                return  # anti-doublon
            key = (fid, fiche_id)
            st = _compute_cert_status(date_exp)
            d = cert_link_stats.setdefault(key, {"valide": 0, "expire_bientot": 0, "expire": 0, "sans_date": 0})
            d[st] = d.get(st, 0) + 1
            cert_examples.setdefault(key, []).append(cert_id)
            seen_ids.setdefault(key, set()).add(cert_id)

        seen_by_key = {}  # {(fid, fiche_id): set(cert_id)} pour dedup groupe/direct
        if four_ids and fiche_ids:
            # Query 1 : certs directs (attaches directement au fournisseur, sans groupe_ref)
            q_direct = f"""
                SELECT c.id AS cert_id, c.fournisseur_id, c.date_expiration, l.fiche_id
                FROM qualite_fournisseur_certificats c
                JOIN qualite_fournisseur_certificat_fiches l ON l.certificat_id = c.id
                WHERE c.fournisseur_id IN ({','.join(['?']*len(four_ids))})
                  AND l.fiche_id IN ({','.join(['?']*len(fiche_ids))})
                  AND (c.groupe_ref IS NULL OR TRIM(c.groupe_ref) = '')
            """
            for r in conn.execute(q_direct, four_ids + fiche_ids).fetchall():
                _add_cert_link(r["fournisseur_id"], r["fiche_id"], r["cert_id"], r["date_expiration"], seen_by_key)

            # Query 2 : certs niveau groupe → s'appliquent a TOUTES les branches du groupe presentes dans l'audit
            if fours_by_groupe:
                groupes_lower = list(fours_by_groupe.keys())
                q_groupe = f"""
                    SELECT c.id AS cert_id, c.groupe_ref, c.date_expiration, l.fiche_id
                    FROM qualite_fournisseur_certificats c
                    JOIN qualite_fournisseur_certificat_fiches l ON l.certificat_id = c.id
                    WHERE c.groupe_ref IS NOT NULL AND TRIM(c.groupe_ref) <> ''
                      AND LOWER(TRIM(c.groupe_ref)) IN ({','.join(['?']*len(groupes_lower))})
                      AND l.fiche_id IN ({','.join(['?']*len(fiche_ids))})
                """
                for r in conn.execute(q_groupe, groupes_lower + fiche_ids).fetchall():
                    gref_low = (r["groupe_ref"] or "").strip().lower()
                    for fid in fours_by_groupe.get(gref_low, []):
                        _add_cert_link(fid, r["fiche_id"], r["cert_id"], r["date_expiration"], seen_by_key)
        # Charger les overrides manuels
        over_rows = conn.execute(
            "SELECT * FROM audit_matrice_overrides WHERE audit_id=?",
            (audit_id,),
        ).fetchall()
        overrides = {(r["fournisseur_id"], r["fiche_id"]): dict(r) for r in over_rows}
        # Construire la matrice
        cells = []
        for f in four_rows:
            for r in fiche_rows:
                key = (f["id"], r["id"])
                stats = cert_link_stats.get(key, {"valide": 0, "expire_bientot": 0, "expire": 0, "sans_date": 0})
                auto = _matrice_status_from_cert_stats(stats)
                over = overrides.get(key)
                cell = {
                    "fournisseur_id": f["id"],
                    "fiche_id": r["id"],
                    "auto_statut": auto,
                    "cert_stats": stats,
                    "cert_ids": cert_examples.get(key, []),
                    "override_statut": (over["statut"] if over else None),
                    "override_note": (over["note"] if over else ""),
                    "statut": (over["statut"] if over else auto),
                }
                cells.append(cell)
        # Résumé rapide (nb OK / total)
        total = len(cells)
        ok = sum(1 for c in cells if c["statut"] == "ok")
    return {
        "fournisseurs": [dict(r) for r in four_rows],
        "certifications": [dict(r) for r in fiche_rows],
        "cells": cells,
        "resume": {"total": total, "ok": ok},
    }


class MatriceIdsBody(BaseModel):
    ids: List[int]


@router.put("/api/qualite/audits/{audit_id}/matrice/fournisseurs")
def audit_set_matrice_fournisseurs(audit_id: int, body: MatriceIdsBody, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM audit_dossiers WHERE id=?", (audit_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Audit introuvable")
        wanted = [int(x) for x in (body.ids or []) if isinstance(x, int)]
        # Ne garder que ceux qui existent réellement
        if wanted:
            exists = conn.execute(
                f"SELECT id FROM fournisseurs_fsc WHERE id IN ({','.join(['?']*len(wanted))})",
                wanted,
            ).fetchall()
            wanted = [r["id"] for r in exists]
        conn.execute("DELETE FROM audit_fournisseurs WHERE audit_id=?", (audit_id,))
        for fid in wanted:
            conn.execute(
                "INSERT OR IGNORE INTO audit_fournisseurs (audit_id, fournisseur_id, added_at, added_by) VALUES (?,?,?,?)",
                (audit_id, fid, _now(), user["id"]),
            )
        # Purger les overrides devenus orphelins
        conn.execute(
            "DELETE FROM audit_matrice_overrides WHERE audit_id=? AND fournisseur_id NOT IN (SELECT fournisseur_id FROM audit_fournisseurs WHERE audit_id=?)",
            (audit_id, audit_id),
        )
        conn.execute("UPDATE audit_dossiers SET updated_at=?, updated_by=? WHERE id=?", (_now(), user["id"], audit_id))
        conn.commit()
    return audit_get_matrice(audit_id, request)


@router.put("/api/qualite/audits/{audit_id}/matrice/certifications")
def audit_set_matrice_certifications(audit_id: int, body: MatriceIdsBody, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM audit_dossiers WHERE id=?", (audit_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Audit introuvable")
        wanted = [int(x) for x in (body.ids or []) if isinstance(x, int)]
        if wanted:
            exists = conn.execute(
                f"SELECT id FROM qualite_ref_fiches WHERE id IN ({','.join(['?']*len(wanted))})",
                wanted,
            ).fetchall()
            wanted = [r["id"] for r in exists]
        conn.execute("DELETE FROM audit_certifications_demandees WHERE audit_id=?", (audit_id,))
        for fid in wanted:
            conn.execute(
                "INSERT OR IGNORE INTO audit_certifications_demandees (audit_id, fiche_id, added_at, added_by) VALUES (?,?,?,?)",
                (audit_id, fid, _now(), user["id"]),
            )
        conn.execute(
            "DELETE FROM audit_matrice_overrides WHERE audit_id=? AND fiche_id NOT IN (SELECT fiche_id FROM audit_certifications_demandees WHERE audit_id=?)",
            (audit_id, audit_id),
        )
        conn.execute("UPDATE audit_dossiers SET updated_at=?, updated_by=? WHERE id=?", (_now(), user["id"], audit_id))
        conn.commit()
    return audit_get_matrice(audit_id, request)


class MatriceCellBody(BaseModel):
    fournisseur_id: int
    fiche_id: int
    statut: Optional[str] = None   # null → efface l'override
    note: Optional[str] = ""


MATRICE_OVERRIDE_STATUTS = ("ok", "expire_bientot", "expire", "manquant", "sans_date", "na", "demande_envoyee")


@router.put("/api/qualite/audits/{audit_id}/matrice/cell")
def audit_set_matrice_cell(audit_id: int, body: MatriceCellBody, request: Request):
    user = _require_qualite_access(request)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM audit_dossiers WHERE id=?", (audit_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Audit introuvable")
        # Vérif que la case fait bien partie de la sélection
        if not conn.execute(
            "SELECT 1 FROM audit_fournisseurs WHERE audit_id=? AND fournisseur_id=?",
            (audit_id, body.fournisseur_id),
        ).fetchone():
            raise HTTPException(status_code=400, detail="Fournisseur non sélectionné dans cet audit")
        if not conn.execute(
            "SELECT 1 FROM audit_certifications_demandees WHERE audit_id=? AND fiche_id=?",
            (audit_id, body.fiche_id),
        ).fetchone():
            raise HTTPException(status_code=400, detail="Certification non sélectionnée dans cet audit")
        if body.statut is None or body.statut == "":
            conn.execute(
                "DELETE FROM audit_matrice_overrides WHERE audit_id=? AND fournisseur_id=? AND fiche_id=?",
                (audit_id, body.fournisseur_id, body.fiche_id),
            )
        else:
            if body.statut not in MATRICE_OVERRIDE_STATUTS:
                raise HTTPException(status_code=400, detail="Statut invalide")
            conn.execute(
                """INSERT INTO audit_matrice_overrides
                   (audit_id, fournisseur_id, fiche_id, statut, note, updated_at, updated_by)
                   VALUES (?,?,?,?,?,?,?)
                   ON CONFLICT(audit_id, fournisseur_id, fiche_id) DO UPDATE SET
                     statut=excluded.statut, note=excluded.note,
                     updated_at=excluded.updated_at, updated_by=excluded.updated_by""",
                (audit_id, body.fournisseur_id, body.fiche_id,
                 body.statut, (body.note or "").strip(), _now(), user["id"]),
            )
        conn.execute("UPDATE audit_dossiers SET updated_at=?, updated_by=? WHERE id=?", (_now(), user["id"], audit_id))
        conn.commit()
    return audit_get_matrice(audit_id, request)


# ─── Pickers : fournisseurs / fiches disponibles pour la matrice ─────

@router.get("/api/qualite/audits/{audit_id}/matrice/pickers")
def audit_matrice_pickers(audit_id: int, request: Request):
    """Renvoie la liste complète des fournisseurs + fiches, plus la sélection courante."""
    _require_qualite_view(request)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM audit_dossiers WHERE id=?", (audit_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Audit introuvable")
        fours = conn.execute(
            "SELECT id, nom, licence FROM fournisseurs_fsc ORDER BY nom COLLATE NOCASE ASC"
        ).fetchall()
        fiches = conn.execute(
            """SELECT id, slug, nom, acronyme, categorie FROM qualite_ref_fiches
               WHERE statut_validation='valide' OR statut_validation IS NULL
               ORDER BY nom COLLATE NOCASE ASC"""
        ).fetchall()
        # Si la contrainte "valide only" ne donne rien, tomber sur tout
        if not fiches:
            fiches = conn.execute(
                "SELECT id, slug, nom, acronyme, categorie FROM qualite_ref_fiches ORDER BY nom COLLATE NOCASE ASC"
            ).fetchall()
        sel_four = [r["fournisseur_id"] for r in conn.execute(
            "SELECT fournisseur_id FROM audit_fournisseurs WHERE audit_id=?", (audit_id,)
        ).fetchall()]
        sel_fiche = [r["fiche_id"] for r in conn.execute(
            "SELECT fiche_id FROM audit_certifications_demandees WHERE audit_id=?", (audit_id,)
        ).fetchall()]
    return {
        "fournisseurs": [dict(r) for r in fours],
        "fiches": [dict(r) for r in fiches],
        "selection": {"fournisseurs": sel_four, "fiches": sel_fiche},
    }



# ══════════════════════════════════════════════════════════════════════
# SIFA — Certifications & Documents officiels (Déclarations UE, etc.)
# ══════════════════════════════════════════════════════════════════════
#
# Structure :
# - qualite_sifa_doc_templates : catalogue des templates disponibles
#   (aujourd'hui : declaration_ue). Un template = code + titre + validité.
# - qualite_sifa_doc_versions : une ligne par version générée pour un client.
#   Rattachée à un audit_dossiers si le client a un audit ouvert, sinon nom libre.
# - PDF stocké sur disque dans QUALITE_UPLOAD_DIR/sifa-docs/, chemin dans pdf_path.
# - Génération via app.services.sifa_doc_pdf.build_template_pdf(code, ...).
# - Numéro auto par client : ref_prefix + slug(client) + séquence 001, 002, ...
#
# Rôles :
# - Lecture (list templates, list versions, télécharger un PDF) : ROLES_QUALITE_VIEW
#   → superadmin, direction, administration, commercial (les commerciaux envoient au client)
# - Génération d'une version : ROLES_QUALITE_VIEW aussi (commercial autorisé — c'est leur job)
# - Suppression / modification pays_origine fournisseur : _require_qualite_access (admin qualité)

SIFA_DOCS_DIR = os.path.join(QUALITE_UPLOAD_DIR, "sifa-docs")
os.makedirs(SIFA_DOCS_DIR, exist_ok=True)


def _slug(txt: str) -> str:
    """Slug simple pour intégrer dans une référence de document.
    « Hermès Paris » → « HERMES-PARIS »."""
    if not txt:
        return "CLIENT"
    import unicodedata
    s = unicodedata.normalize("NFKD", str(txt))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").upper()
    return s[:40] or "CLIENT"


def _next_ref_for_client(conn, template, client_slug: str) -> str:
    """Calcule la prochaine référence pour ce client : SIFA-DoC-HERMES-001, 002, …"""
    prefix = (template["ref_prefix"] or "SIFA-DoC").rstrip("-")
    base = f"{prefix}-{client_slug}-"
    rows = conn.execute(
        "SELECT ref_document FROM qualite_sifa_doc_versions "
        "WHERE template_id=? AND client_slug=? AND deleted_at IS NULL",
        (template["id"], client_slug),
    ).fetchall()
    max_n = 0
    for r in rows:
        ref = (r["ref_document"] or "").upper()
        if ref.startswith(base.upper()):
            tail = ref[len(base):]
            try:
                n = int(re.match(r"^(\d+)", tail).group(1))
                if n > max_n:
                    max_n = n
            except Exception:
                pass
    return f"{base}{max_n + 1:03d}"


def _fetch_template(conn, code_or_id):
    """Récupère un template par code ou id."""
    if isinstance(code_or_id, int) or (isinstance(code_or_id, str) and code_or_id.isdigit()):
        row = conn.execute(
            "SELECT * FROM qualite_sifa_doc_templates WHERE id=?",
            (int(code_or_id),),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM qualite_sifa_doc_templates WHERE code=?",
            (code_or_id,),
        ).fetchone()
    return row


def _fournisseurs_for_pdf(conn, ids: list) -> list:
    """Charge nom + pays_origine + certificat pour la liste d'ids."""
    if not ids:
        return []
    qm = ",".join(["?"] * len(ids))
    rows = conn.execute(
        f"SELECT id, nom, pays_origine, licence, certificat "
        f"FROM fournisseurs_fsc WHERE id IN ({qm}) "
        f"ORDER BY nom COLLATE NOCASE ASC",
        ids,
    ).fetchall()
    # Respecter l'ordre demandé si possible
    by_id = {r["id"]: dict(r) for r in rows}
    ordered = [by_id[i] for i in ids if i in by_id]
    return ordered


# ─── Liste des templates disponibles ─────────────────────────────────
@router.get("/api/qualite/sifa-docs/templates")
def sifa_docs_list_templates(request: Request):
    """Renvoie tous les templates actifs + le nombre de versions générées."""
    _require_qualite_view(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT t.*, (
                   SELECT COUNT(*) FROM qualite_sifa_doc_versions v
                   WHERE v.template_id = t.id AND v.deleted_at IS NULL
               ) AS versions_count
               FROM qualite_sifa_doc_templates t
               WHERE t.actif = 1
               ORDER BY t.titre COLLATE NOCASE ASC"""
        ).fetchall()
    return {"templates": [dict(r) for r in rows]}


# ─── Détail d'un template ────────────────────────────────────────────
@router.get("/api/qualite/sifa-docs/templates/{code}")
def sifa_docs_get_template(code: str, request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        row = _fetch_template(conn, code)
        if not row:
            raise HTTPException(status_code=404, detail="Template introuvable")
        # Charger les versions rattachées
        versions = conn.execute(
            """SELECT v.*, u.nom AS created_by_nom, a.numero AS audit_numero
               FROM qualite_sifa_doc_versions v
               LEFT JOIN users u ON u.id = v.created_by
               LEFT JOIN audit_dossiers a ON a.id = v.audit_id
               WHERE v.template_id = ? AND v.deleted_at IS NULL
               ORDER BY v.created_at DESC""",
            (row["id"],),
        ).fetchall()
        # Décoder fournisseurs_ids_json pour chaque version + charger noms
        vs = []
        for v in versions:
            d = dict(v)
            try:
                import json
                d["fournisseurs_ids"] = json.loads(v["fournisseurs_ids_json"] or "[]")
            except Exception:
                d["fournisseurs_ids"] = []
            if d["fournisseurs_ids"]:
                fours = _fournisseurs_for_pdf(conn, d["fournisseurs_ids"])
                d["fournisseurs"] = [
                    {"id": f["id"], "nom": f["nom"], "pays_origine": f["pays_origine"]}
                    for f in fours
                ]
            else:
                d["fournisseurs"] = []
            vs.append(d)
    return {"template": dict(row), "versions": vs}


# ─── Pickers : audits + fournisseurs disponibles ─────────────────────
@router.get("/api/qualite/sifa-docs/pickers")
def sifa_docs_pickers(request: Request):
    """Renvoie ce qu'il faut au modal de génération :
       - audits ouverts + fournisseurs de chaque audit (pré-cochés)
       - liste complète des fournisseurs (avec pays_origine)"""
    _require_qualite_view(request)
    with get_db() as conn:
        audits = [dict(r) for r in conn.execute(
            """SELECT a.id, a.numero, a.client_nom, a.date_audit, a.statut, a.client_id
               FROM audit_dossiers a
               WHERE a.statut = 'ouvert'
               ORDER BY a.date_audit DESC, a.id DESC"""
        ).fetchall()]
        # Charger les fournisseurs de chaque audit
        af_rows = conn.execute(
            "SELECT audit_id, fournisseur_id FROM audit_fournisseurs"
        ).fetchall()
        by_audit = {}
        for r in af_rows:
            by_audit.setdefault(r["audit_id"], []).append(r["fournisseur_id"])
        for a in audits:
            a["fournisseur_ids"] = by_audit.get(a["id"], [])
        # Liste complète fournisseurs
        fours = [dict(r) for r in conn.execute(
            """SELECT id, nom, pays_origine, groupe, branche, licence, certificat
               FROM fournisseurs_fsc
               ORDER BY nom COLLATE NOCASE ASC"""
        ).fetchall()]
    return {"audits": audits, "fournisseurs": fours}


# ─── Récupérer la liste des sections d'un template (pour l'UI de personnalisation)
@router.get("/api/qualite/sifa-docs/templates/{code}/sections")
def sifa_docs_get_sections(code: str, request: Request):
    """Renvoie la liste des sections du template avec leurs textes par défaut.
    Utilisé par le modal génération pour permettre d'exclure ou éditer des sections."""
    _require_qualite_view(request)
    with get_db() as conn:
        template = _fetch_template(conn, code)
        if not template:
            raise HTTPException(status_code=404, detail="Template introuvable")
    try:
        from app.services.sifa_doc_pdf import get_template_sections
        return {"sections": get_template_sections(template["code"])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")


# ─── Créer une nouvelle version + générer le PDF ─────────────────────
class SifaDocVersionCreateBody(BaseModel):
    template_code: str
    audit_id: Optional[int] = None
    client_nom: str
    fournisseurs_ids: List[int]
    ref_document: Optional[str] = None
    date_emission: Optional[str] = None
    notes: Optional[str] = None
    sections_overrides: Optional[dict] = None  # {sec_id: {"include": bool, "custom_body": str}}


@router.post("/api/qualite/sifa-docs/versions")
def sifa_docs_create_version(body: SifaDocVersionCreateBody, request: Request):
    user = _require_qualite_view(request)
    client_nom = (body.client_nom or "").strip()
    if not client_nom:
        raise HTTPException(status_code=400, detail="Nom de client obligatoire")
    if not body.fournisseurs_ids:
        raise HTTPException(status_code=400, detail="Au moins un fournisseur obligatoire")

    with get_db() as conn:
        template = _fetch_template(conn, body.template_code)
        if not template:
            raise HTTPException(status_code=404, detail="Template introuvable")

        # Vérifier que tous les fournisseurs ont un pays_origine renseigné
        missing = conn.execute(
            f"SELECT id, nom FROM fournisseurs_fsc "
            f"WHERE id IN ({','.join(['?']*len(body.fournisseurs_ids))}) "
            f"AND (pays_origine IS NULL OR TRIM(pays_origine) = '')",
            body.fournisseurs_ids,
        ).fetchall()
        if missing:
            # Le front doit d'abord passer par /missing-countries
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "MISSING_COUNTRIES",
                    "message": "Origine géographique manquante pour certains fournisseurs",
                    "fournisseurs": [{"id": r["id"], "nom": r["nom"]} for r in missing],
                },
            )

        # Vérifier audit_id si fourni
        audit_id = body.audit_id
        if audit_id:
            arow = conn.execute(
                "SELECT id, client_nom FROM audit_dossiers WHERE id=?", (audit_id,)
            ).fetchone()
            if not arow:
                audit_id = None  # Audit supprimé entre-temps, on continue quand même

        # Générer la ref si absente
        client_slug = _slug(client_nom)
        ref = (body.ref_document or "").strip() or _next_ref_for_client(conn, template, client_slug)
        # Éviter doublon de ref
        dup = conn.execute(
            "SELECT id FROM qualite_sifa_doc_versions "
            "WHERE ref_document=? AND deleted_at IS NULL",
            (ref,),
        ).fetchone()
        if dup:
            raise HTTPException(status_code=409, detail=f"Référence {ref} déjà utilisée")

        date_emission = (body.date_emission or "").strip() or _today()
        validite_mois = int(template["validite_mois"] or 12)

        # Charger les fournisseurs et générer le PDF
        fours = _fournisseurs_for_pdf(conn, body.fournisseurs_ids)
        try:
            from app.services.sifa_doc_pdf import build_template_pdf
            pdf_bytes = build_template_pdf(
                template["code"],
                client_nom=client_nom,
                fournisseurs=fours,
                ref=ref,
                date_emission_iso=date_emission,
                validite_mois=validite_mois,
                sections_overrides=body.sections_overrides or None,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur génération PDF : {e}")

        # Enregistrer sur disque
        safe_ref = re.sub(r"[^A-Za-z0-9._-]+", "-", ref)
        rel_dir = os.path.join(SIFA_DOCS_DIR, template["code"])
        os.makedirs(rel_dir, exist_ok=True)
        pdf_path = os.path.join(rel_dir, f"{safe_ref}.pdf")
        try:
            with open(pdf_path, "wb") as fh:
                fh.write(pdf_bytes)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur écriture disque : {e}")

        import json as _json
        now = _now()
        sec_ov_json = _json.dumps(body.sections_overrides or {})
        cur = conn.execute(
            """INSERT INTO qualite_sifa_doc_versions
               (template_id, audit_id, client_nom, client_slug, fournisseurs_ids_json,
                ref_document, date_emission, validite_mois, pdf_path, notes,
                sections_overrides_json,
                created_by, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (template["id"], audit_id, client_nom, client_slug,
             _json.dumps(list(body.fournisseurs_ids)),
             ref, date_emission, validite_mois, pdf_path,
             (body.notes or "").strip() or None,
             sec_ov_json,
             user["id"], now, now),
        )
        conn.commit()
        vid = cur.lastrowid

    return {"id": vid, "ref_document": ref, "pdf_path": pdf_path}


# ─── Régénérer le PDF d'une version existante ────────────────────────
@router.post("/api/qualite/sifa-docs/versions/{vid}/regenerate")
def sifa_docs_regenerate_version(vid: int, request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        v = conn.execute(
            "SELECT * FROM qualite_sifa_doc_versions WHERE id=? AND deleted_at IS NULL",
            (vid,),
        ).fetchone()
        if not v:
            raise HTTPException(status_code=404, detail="Version introuvable")
        template = conn.execute(
            "SELECT * FROM qualite_sifa_doc_templates WHERE id=?", (v["template_id"],)
        ).fetchone()
        if not template:
            raise HTTPException(status_code=404, detail="Template introuvable")

        import json as _json
        try:
            f_ids = _json.loads(v["fournisseurs_ids_json"] or "[]")
        except Exception:
            f_ids = []
        try:
            sec_ov = _json.loads(v["sections_overrides_json"] or "{}")
        except Exception:
            sec_ov = {}
        fours = _fournisseurs_for_pdf(conn, f_ids)
        try:
            from app.services.sifa_doc_pdf import build_template_pdf
            pdf_bytes = build_template_pdf(
                template["code"],
                client_nom=v["client_nom"],
                fournisseurs=fours,
                ref=v["ref_document"],
                date_emission_iso=v["date_emission"],
                validite_mois=int(v["validite_mois"] or 12),
                sections_overrides=sec_ov or None,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur génération : {e}")

        try:
            with open(v["pdf_path"], "wb") as fh:
                fh.write(pdf_bytes)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur écriture : {e}")

        conn.execute(
            "UPDATE qualite_sifa_doc_versions SET updated_at=? WHERE id=?",
            (_now(), vid),
        )
        conn.commit()
    return {"ok": True}


# ─── Télécharger le PDF d'une version ────────────────────────────────
@router.get("/api/qualite/sifa-docs/versions/{vid}/pdf")
def sifa_docs_download_version(vid: int, request: Request):
    _require_qualite_view(request)
    with get_db() as conn:
        v = conn.execute(
            "SELECT ref_document, pdf_path FROM qualite_sifa_doc_versions "
            "WHERE id=? AND deleted_at IS NULL",
            (vid,),
        ).fetchone()
    if not v:
        raise HTTPException(status_code=404, detail="Version introuvable")
    if not v["pdf_path"] or not os.path.exists(v["pdf_path"]):
        raise HTTPException(status_code=410, detail="PDF absent — régénérer la version")
    return FileResponse(
        v["pdf_path"], media_type="application/pdf",
        filename=f"{v['ref_document']}.pdf",
    )


# ─── Aperçu : PDF vierge du template (avec placeholders) ─────────────
@router.get("/api/qualite/sifa-docs/templates/{code}/preview")
def sifa_docs_preview_template(code: str, request: Request):
    """Génère un PDF « vierge » avec placeholders pour prévisualisation dans l'UI."""
    _require_qualite_view(request)
    with get_db() as conn:
        template = _fetch_template(conn, code)
        if not template:
            raise HTTPException(status_code=404, detail="Template introuvable")
    try:
        from app.services.sifa_doc_pdf import build_template_pdf
        pdf_bytes = build_template_pdf(
            template["code"],
            client_nom="[NOM DU CLIENT]",
            fournisseurs=[
                {"id": 0, "nom": "[Fournisseur 1]", "pays_origine": "[Pays]", "certificat": None},
                {"id": 0, "nom": "[Fournisseur 2]", "pays_origine": "[Pays]", "certificat": None},
            ],
            ref=f"{template['ref_prefix']}-APERCU",
            date_emission_iso=_today(),
            validite_mois=int(template["validite_mois"] or 12),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur preview : {e}")
    from fastapi.responses import Response
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": "inline; filename=preview.pdf"})


# ─── Supprimer (soft delete) une version ─────────────────────────────
@router.delete("/api/qualite/sifa-docs/versions/{vid}")
def sifa_docs_delete_version(vid: int, request: Request):
    _require_qualite_access(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM qualite_sifa_doc_versions WHERE id=? AND deleted_at IS NULL",
            (vid,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Version introuvable")
        conn.execute(
            "UPDATE qualite_sifa_doc_versions SET deleted_at=? WHERE id=?",
            (_now(), vid),
        )
        conn.commit()
    return {"ok": True}


# ─── Renseigner en masse les pays d'origine manquants ─────────────────
class SifaDocCountriesBody(BaseModel):
    updates: List[dict]  # [{"id": 1, "pays_origine": "Allemagne"}, ...]


@router.put("/api/qualite/sifa-docs/fournisseurs-countries")
def sifa_docs_update_countries(body: SifaDocCountriesBody, request: Request):
    """Renseigne en une seule requête le pays_origine de plusieurs fournisseurs.
    Utilisé par le modal « Origine géographique » avant génération d'une version."""
    _require_qualite_view(request)
    if not body.updates:
        return {"updated": 0}
    updated = 0
    with get_db() as conn:
        for u in body.updates:
            fid = u.get("id")
            pays = (u.get("pays_origine") or "").strip()
            if not fid or not pays:
                continue
            conn.execute(
                "UPDATE fournisseurs_fsc SET pays_origine=? WHERE id=?",
                (pays, int(fid)),
            )
            updated += 1
        conn.commit()
    return {"updated": updated}


# ─── Créer une nouvelle version PLUS mettre à jour audit_fournisseurs ───
# (Pour le raccourci « Générer Déclaration UE » depuis un audit client, on veut
#  que les fournisseurs cochés dans le modal soient aussi ajoutés à l'audit s'ils
#  n'y sont pas déjà. Simple sync additive, sans retrait.)
class SifaDocSyncAuditBody(BaseModel):
    audit_id: int
    fournisseur_ids: List[int]


@router.post("/api/qualite/sifa-docs/sync-audit-fournisseurs")
def sifa_docs_sync_audit_fournisseurs(body: SifaDocSyncAuditBody, request: Request):
    """Ajoute des fournisseurs à un audit (sans en retirer)."""
    user = _require_qualite_access(request)
    with get_db() as conn:
        a = conn.execute(
            "SELECT id FROM audit_dossiers WHERE id=?", (body.audit_id,)
        ).fetchone()
        if not a:
            raise HTTPException(status_code=404, detail="Audit introuvable")
        now = _now()
        added = 0
        for fid in (body.fournisseur_ids or []):
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO audit_fournisseurs "
                    "(audit_id, fournisseur_id, added_at, added_by) VALUES (?, ?, ?, ?)",
                    (body.audit_id, int(fid), now, user["id"]),
                )
                added += 1
            except Exception:
                pass
        conn.commit()
    return {"added": added}

