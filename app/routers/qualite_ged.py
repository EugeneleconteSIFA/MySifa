"""MySifa - Module Qualite : Explorateur de documents (GED)
Route prefix : /api/qualite/ged

Acces : lecture ET ecriture pour tous les roles ayant acces a MyQualite
        (superadmin, direction, administration, administration_ventes,
         administration_technique, commercial).
        Purge definitive de la corbeille : admins qualite uniquement
        (seule action irreversible du module).

Modele :
- qualite_ged_folders       : arborescence recursive via parent_id (NULL = racine)
- qualite_ged_files         : le document "logique" (emplacement, tags, rattachement)
- qualite_ged_file_versions : les fichiers physiques successifs du meme document
- qualite_ged_fts           : index plein texte FTS5 (rowid = qualite_ged_files.id)

Pourquoi separer fichier logique et versions : les tags, la description et le
rattachement appartiennent au document, pas a un fichier physique. Reuploader
une v2 ne doit pas faire perdre les metadonnees ni casser les liens.

Corbeille : suppression douce via deleted_at + trash_id. Le trash_id est un uuid
commun a tout ce qui a ete supprime dans le meme geste (un dossier et tout son
contenu), ce qui rend la restauration exacte et atomique.

Stockage disque : UPLOAD_DIR/qualite/ged/<AAAA>/<MM>/<uuid>.<ext>
Nom opaque sur le disque, nom d'affichage en base : pas de collision, pas de
caractere exotique, pas de path traversal possible.
"""
from __future__ import annotations

import hashlib
import io
import os
import re
import unicodedata
import uuid
import zipfile
from datetime import datetime
from typing import Optional, List

from fastapi import (
    APIRouter, HTTPException, Request, UploadFile, File, Form, BackgroundTasks,
)
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from app.core.database import get_db
from app.services.auth_service import get_current_user
from app.services.ged_extract import extract_text
from config import UPLOAD_DIR, GED_MAX_FILE_MB, GED_BLOCKED_EXTENSIONS

router = APIRouter()

GED_DIR = os.path.join(UPLOAD_DIR, "qualite", "ged")
os.makedirs(GED_DIR, exist_ok=True)

ROLES_GED = {
    "superadmin", "direction", "administration",
    "administration_ventes", "administration_technique", "commercial",
}
ROLES_GED_ADMIN = ROLES_GED - {"commercial"}

LINK_TYPES = ("client", "fournisseur", "norme")

MAX_BYTES = int(GED_MAX_FILE_MB) * 1024 * 1024
ZIP_MAX_BYTES = 300 * 1024 * 1024   # garde-fou export ZIP (construit en memoire)
INLINE_SYNC_BYTES = 3 * 1024 * 1024  # au-dela, l'indexation passe en tache de fond


# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _require_ged(request: Request) -> dict:
    """Lecture et ecriture : tout utilisateur ayant acces a MyQualite."""
    user = get_current_user(request)
    if user["role"] not in ROLES_GED:
        raise HTTPException(status_code=403, detail="Acces reserve au module Qualite")
    return user


def _require_ged_admin(request: Request) -> dict:
    """Purge definitive uniquement."""
    user = get_current_user(request)
    if user["role"] not in ROLES_GED_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Purge definitive reservee a l'administration et la direction",
        )
    return user


def _strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c))


def _clean_name(name: str, fallback: str = "Sans nom") -> str:
    """Nettoie un nom saisi : pas de separateur de chemin, pas de caractere de
    controle, pas de nom vide. Le nom n'atteint jamais le disque (stockage en
    uuid), mais on le durcit quand meme pour l'affichage et les exports ZIP."""
    s = str(name or "").replace("\\", "-").replace("/", "-")
    s = re.sub(r"[\x00-\x1f\x7f]", "", s)
    s = re.sub(r"\s+", " ", s).strip(" .")
    return s[:180] or fallback


def _ext_of(filename: str) -> str:
    ext = os.path.splitext(filename or "")[1].lower().lstrip(".")
    return re.sub(r"[^a-z0-9]", "", ext)[:12]


def _norm_tags(raw) -> str:
    """Tags stockes normalises : minuscules, sans accents, separes par des
    virgules. C'est ce qui permet de chercher 'declaration' et de trouver
    'Declaration' comme 'declaration'."""
    if raw is None:
        return ""
    if isinstance(raw, (list, tuple)):
        items = list(raw)
    else:
        items = re.split(r"[,;\n]", str(raw))
    out = []
    for it in items:
        t = _strip_accents(it).lower().strip()
        t = re.sub(r"\s+", " ", t)
        if t and t not in out:
            out.append(t[:40])
    return ",".join(out[:25])


def _check_ext_allowed(filename: str) -> str:
    """Tout est accepte sauf les executables et scripts. On teste l'extension
    finale : 'facture.pdf.exe' est bien vu comme un .exe."""
    ext = _ext_of(filename)
    if ext in GED_BLOCKED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non autorise (.{ext}) : executables et scripts refuses",
        )
    return ext


def _storage_path(ext: str) -> str:
    now = datetime.now()
    sub = os.path.join(GED_DIR, now.strftime("%Y"), now.strftime("%m"))
    os.makedirs(sub, exist_ok=True)
    name = uuid.uuid4().hex + (f".{ext}" if ext else "")
    return os.path.join(sub, name)


def _row(r) -> dict:
    return dict(r) if r is not None else None


# ─── Arborescence ────────────────────────────────────────────────────

def _folder_map(conn) -> dict:
    rows = conn.execute(
        "SELECT id, parent_id, nom FROM qualite_ged_folders WHERE deleted_at IS NULL"
    ).fetchall()
    return {r["id"]: {"id": r["id"], "parent_id": r["parent_id"], "nom": r["nom"]} for r in rows}


def _breadcrumb_from(fmap: dict, folder_id: Optional[int]) -> List[dict]:
    """Chemin depuis la racine, a partir d'une carte deja chargee.
    Le garde-fou de profondeur protege d'un cycle qui aurait echappe au controle
    de _would_cycle (corruption manuelle en base)."""
    if not folder_id:
        return []
    out, cur, guard = [], folder_id, 0
    while cur and guard < 64:
        node = fmap.get(cur)
        if not node:
            break
        out.append({"id": node["id"], "nom": node["nom"]})
        cur = node["parent_id"]
        guard += 1
    return list(reversed(out))


def _breadcrumb(conn, folder_id: Optional[int]) -> List[dict]:
    return _breadcrumb_from(_folder_map(conn), folder_id)


def _path_from(fmap: dict, folder_id: Optional[int]) -> str:
    bc = _breadcrumb_from(fmap, folder_id)
    return "/" + "/".join(b["nom"] for b in bc) if bc else "/"


def _folder_path_str(conn, folder_id: Optional[int]) -> str:
    return _path_from(_folder_map(conn), folder_id)


def _descendants(conn, folder_id: int) -> List[int]:
    """Ids de tous les sous-dossiers (recursif), folder_id exclu."""
    rows = conn.execute(
        "SELECT id, parent_id FROM qualite_ged_folders WHERE deleted_at IS NULL"
    ).fetchall()
    children = {}
    for r in rows:
        children.setdefault(r["parent_id"], []).append(r["id"])
    out, stack = [], list(children.get(folder_id, []))
    while stack:
        cur = stack.pop()
        out.append(cur)
        stack.extend(children.get(cur, []))
    return out


def _would_cycle(conn, folder_id: int, new_parent_id: Optional[int]) -> bool:
    """Interdit de deplacer un dossier dans lui-meme ou dans sa descendance."""
    if not new_parent_id:
        return False
    if new_parent_id == folder_id:
        return True
    return new_parent_id in _descendants(conn, folder_id)


def _uniq_folder_name(conn, parent_id: Optional[int], nom: str,
                      exclude_id: Optional[int] = None) -> str:
    """Unicite (parent, nom) geree en applicatif avec suffixe ' (2)'.
    Plus souple qu'un index unique : on ne bloque jamais l'utilisateur."""
    base, n, cand = nom, 1, nom
    while True:
        sql = ("SELECT id FROM qualite_ged_folders WHERE deleted_at IS NULL "
               "AND nom = ? COLLATE NOCASE AND ")
        params = [cand]
        sql += "parent_id IS NULL " if parent_id is None else "parent_id = ? "
        if parent_id is not None:
            params.append(parent_id)
        if exclude_id:
            sql += "AND id <> ? "
            params.append(exclude_id)
        if not conn.execute(sql + "LIMIT 1", params).fetchone():
            return cand
        n += 1
        cand = f"{base} ({n})"


def _uniq_file_name(conn, folder_id: Optional[int], nom: str,
                    exclude_id: Optional[int] = None) -> str:
    stem, dot, ext = nom.rpartition(".")
    if not dot:
        stem, ext = nom, ""
    base, n, cand = stem, 1, nom
    while True:
        sql = ("SELECT id FROM qualite_ged_files WHERE deleted_at IS NULL "
               "AND nom = ? COLLATE NOCASE AND ")
        params = [cand]
        sql += "folder_id IS NULL " if folder_id is None else "folder_id = ? "
        if folder_id is not None:
            params.append(folder_id)
        if exclude_id:
            sql += "AND id <> ? "
            params.append(exclude_id)
        if not conn.execute(sql + "LIMIT 1", params).fetchone():
            return cand
        n += 1
        cand = f"{base} ({n}).{ext}" if ext else f"{base} ({n})"


# ─── Index plein texte ───────────────────────────────────────────────

_FTS_OK: Optional[bool] = None


def _fts_available(conn) -> bool:
    """FTS5 est compile par defaut dans SQLite sur Debian/Ubuntu, mais on ne
    parie pas dessus : si la table virtuelle n'existe pas, la recherche bascule
    silencieusement sur un LIKE sur contenu_txt. Meme API, meme resultats a peu
    pres, juste moins rapide et sans surlignage."""
    global _FTS_OK
    if _FTS_OK is None:
        try:
            conn.execute("SELECT 1 FROM qualite_ged_fts LIMIT 1").fetchone()
            _FTS_OK = True
        except Exception:
            _FTS_OK = False
    return _FTS_OK


def _fts_delete(conn, file_id: int) -> None:
    if not _fts_available(conn):
        return
    try:
        conn.execute("DELETE FROM qualite_ged_fts WHERE rowid=?", (file_id,))
    except Exception:
        pass


def _fts_sync(conn, file_id: int, nom: str, description: str,
              tags: str, contenu: str) -> None:
    if not _fts_available(conn):
        return
    try:
        conn.execute("DELETE FROM qualite_ged_fts WHERE rowid=?", (file_id,))
        conn.execute(
            "INSERT INTO qualite_ged_fts (rowid, nom, description, tags, contenu) "
            "VALUES (?,?,?,?,?)",
            (file_id, nom or "", description or "", tags or "", contenu or ""),
        )
    except Exception:
        pass


def _fts_query(q: str) -> str:
    """Transforme la saisie libre en requete FTS5 sure.
    'declaration ue' -> '"declaration"* AND "ue"*'
    Les guillemets neutralisent la syntaxe FTS (un utilisateur qui tape 'NC-2026*'
    ne doit pas declencher une erreur de syntaxe), l'etoile finale donne le
    prefixe pour que 'declar' trouve 'declaration'."""
    toks = [t for t in re.split(r"[^\w]+", _strip_accents(q).lower()) if len(t) >= 2]
    if not toks:
        return ""
    return " AND ".join(f'"{t}"*' for t in toks[:10])


def _index_file(file_id: int, path: str, ext: str) -> None:
    """Extraction + indexation. Appelee en direct pour les petits fichiers,
    en tache de fond au-dela de INLINE_SYNC_BYTES."""
    txt, status = extract_text(path, ext)
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT nom, description, tags FROM qualite_ged_files WHERE id=?",
                (file_id,),
            ).fetchone()
            if not row:
                return
            conn.execute(
                "UPDATE qualite_ged_files SET contenu_txt=?, index_status=? WHERE id=?",
                (txt, status, file_id),
            )
            _fts_sync(conn, file_id, row["nom"], row["description"], row["tags"], txt)
            conn.commit()
    except Exception:
        pass


# ─── Serialisation ───────────────────────────────────────────────────

def _file_dict(conn, r) -> dict:
    d = dict(r)
    d.pop("contenu_txt", None)
    return d


_FILE_SELECT = """
    SELECT f.id, f.folder_id, f.nom, f.ext, f.mime_type, f.description, f.tags,
           f.link_type, f.link_id, f.index_status,
           f.created_at, f.updated_at,
           u.nom AS created_by_nom, u2.nom AS updated_by_nom,
           (SELECT COUNT(*) FROM qualite_ged_file_versions v WHERE v.file_id=f.id)
               AS version_count,
           (SELECT v.version FROM qualite_ged_file_versions v
             WHERE v.file_id=f.id AND v.is_current=1 LIMIT 1) AS version,
           (SELECT v.size_bytes FROM qualite_ged_file_versions v
             WHERE v.file_id=f.id AND v.is_current=1 LIMIT 1) AS size_bytes,
           (SELECT v.uploaded_at FROM qualite_ged_file_versions v
             WHERE v.file_id=f.id AND v.is_current=1 LIMIT 1) AS version_date
      FROM qualite_ged_files f
      LEFT JOIN users u  ON u.id  = f.created_by
      LEFT JOIN users u2 ON u2.id = f.updated_by
"""


def _current_version(conn, file_id: int):
    return conn.execute(
        "SELECT * FROM qualite_ged_file_versions "
        "WHERE file_id=? AND is_current=1 ORDER BY version DESC LIMIT 1",
        (file_id,),
    ).fetchone()


# ══════════════════════════════════════════════════════════════════════
# Arborescence & navigation
# ══════════════════════════════════════════════════════════════════════

@router.get("/api/qualite/ged/tree")
def ged_tree(request: Request):
    """Arbre des dossiers seuls, a plat : le front reconstruit la hierarchie.
    Volontairement leger, c'est appele a chaque navigation."""
    _require_ged(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT f.id, f.parent_id, f.nom, f.link_type, f.link_id,
                      (SELECT COUNT(*) FROM qualite_ged_files x
                        WHERE x.folder_id = f.id AND x.deleted_at IS NULL) AS nb_files,
                      (SELECT COUNT(*) FROM qualite_ged_folders y
                        WHERE y.parent_id = f.id AND y.deleted_at IS NULL) AS nb_folders
                 FROM qualite_ged_folders f
                WHERE f.deleted_at IS NULL
                ORDER BY f.nom COLLATE NOCASE ASC"""
        ).fetchall()
        root_files = conn.execute(
            "SELECT COUNT(*) AS n FROM qualite_ged_files "
            "WHERE folder_id IS NULL AND deleted_at IS NULL"
        ).fetchone()["n"]
        trash_n = conn.execute(
            "SELECT (SELECT COUNT(*) FROM qualite_ged_files WHERE deleted_at IS NOT NULL) + "
            "       (SELECT COUNT(*) FROM qualite_ged_folders WHERE deleted_at IS NOT NULL) AS n"
        ).fetchone()["n"]
    return {"folders": [dict(r) for r in rows],
            "root_files": root_files,
            "trash_count": trash_n}


@router.get("/api/qualite/ged/folders/{folder_id}")
def ged_folder_content(folder_id: int, request: Request):
    """Contenu d'un dossier + fil d'Ariane. folder_id = 0 -> racine."""
    _require_ged(request)
    fid = folder_id or None
    with get_db() as conn:
        folder = None
        if fid:
            row = conn.execute(
                """SELECT f.*, u.nom AS created_by_nom
                     FROM qualite_ged_folders f
                     LEFT JOIN users u ON u.id = f.created_by
                    WHERE f.id=? AND f.deleted_at IS NULL""",
                (fid,),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Dossier introuvable")
            folder = dict(row)

        sub_sql = """SELECT f.id, f.parent_id, f.nom, f.description, f.link_type, f.link_id,
                            f.created_at,
                            (SELECT COUNT(*) FROM qualite_ged_files x
                              WHERE x.folder_id = f.id AND x.deleted_at IS NULL) AS nb_files,
                            (SELECT COUNT(*) FROM qualite_ged_folders y
                              WHERE y.parent_id = f.id AND y.deleted_at IS NULL) AS nb_folders
                       FROM qualite_ged_folders f
                      WHERE f.deleted_at IS NULL AND """
        sub_sql += "f.parent_id IS NULL " if fid is None else "f.parent_id = ? "
        sub_sql += "ORDER BY f.nom COLLATE NOCASE ASC"
        subs = conn.execute(sub_sql, () if fid is None else (fid,)).fetchall()

        f_sql = _FILE_SELECT + " WHERE f.deleted_at IS NULL AND "
        f_sql += "f.folder_id IS NULL " if fid is None else "f.folder_id = ? "
        f_sql += "ORDER BY f.nom COLLATE NOCASE ASC"
        files = conn.execute(f_sql, () if fid is None else (fid,)).fetchall()

        bc = _breadcrumb(conn, fid)

    return {
        "folder": folder,
        "breadcrumb": bc,
        "folders": [dict(r) for r in subs],
        "files": [dict(r) for r in files],
    }


# ══════════════════════════════════════════════════════════════════════
# Dossiers - CRUD
# ══════════════════════════════════════════════════════════════════════

class FolderCreate(BaseModel):
    parent_id: Optional[int] = None
    nom: str
    description: Optional[str] = None
    link_type: Optional[str] = None
    link_id: Optional[int] = None


class FolderUpdate(BaseModel):
    nom: Optional[str] = None
    parent_id: Optional[int] = None
    move: bool = False            # explicite : sans ce flag, parent_id est ignore
    description: Optional[str] = None
    link_type: Optional[str] = None
    link_id: Optional[int] = None


def _check_link(link_type: Optional[str], link_id: Optional[int]):
    if link_type and link_type not in LINK_TYPES:
        raise HTTPException(status_code=400, detail="Type de rattachement inconnu")
    if link_type and not link_id:
        raise HTTPException(status_code=400, detail="Rattachement incomplet")
    return (link_type or None), (link_id if link_type else None)


@router.post("/api/qualite/ged/folders")
def ged_create_folder(body: FolderCreate, request: Request):
    user = _require_ged(request)
    nom = _clean_name(body.nom, "Nouveau dossier")
    link_type, link_id = _check_link(body.link_type, body.link_id)
    with get_db() as conn:
        if body.parent_id:
            p = conn.execute(
                "SELECT id FROM qualite_ged_folders WHERE id=? AND deleted_at IS NULL",
                (body.parent_id,),
            ).fetchone()
            if not p:
                raise HTTPException(status_code=404, detail="Dossier parent introuvable")
        nom = _uniq_folder_name(conn, body.parent_id, nom)
        now = _now()
        cur = conn.execute(
            """INSERT INTO qualite_ged_folders
               (parent_id, nom, description, link_type, link_id,
                created_at, created_by, updated_at, updated_by)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (body.parent_id, nom, (body.description or "").strip() or None,
             link_type, link_id, now, user["id"], now, user["id"]),
        )
        conn.commit()
        new_id = cur.lastrowid
    return {"id": new_id, "nom": nom}


@router.put("/api/qualite/ged/folders/{fid}")
def ged_update_folder(fid: int, body: FolderUpdate, request: Request):
    user = _require_ged(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM qualite_ged_folders WHERE id=? AND deleted_at IS NULL", (fid,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Dossier introuvable")

        parent_id = row["parent_id"]
        if body.move:
            new_parent = body.parent_id or None
            if new_parent:
                p = conn.execute(
                    "SELECT id FROM qualite_ged_folders WHERE id=? AND deleted_at IS NULL",
                    (new_parent,),
                ).fetchone()
                if not p:
                    raise HTTPException(status_code=404, detail="Dossier cible introuvable")
            if _would_cycle(conn, fid, new_parent):
                raise HTTPException(
                    status_code=400,
                    detail="Impossible : on ne peut pas deplacer un dossier dans lui-meme",
                )
            parent_id = new_parent

        nom = _clean_name(body.nom, row["nom"]) if body.nom is not None else row["nom"]
        nom = _uniq_folder_name(conn, parent_id, nom, exclude_id=fid)

        description = row["description"]
        if body.description is not None:
            description = (body.description or "").strip() or None

        link_type, link_id = row["link_type"], row["link_id"]
        if body.link_type is not None or body.link_id is not None:
            link_type, link_id = _check_link(body.link_type, body.link_id)

        conn.execute(
            """UPDATE qualite_ged_folders
                  SET parent_id=?, nom=?, description=?, link_type=?, link_id=?,
                      updated_at=?, updated_by=?
                WHERE id=?""",
            (parent_id, nom, description, link_type, link_id, _now(), user["id"], fid),
        )
        conn.commit()
    return {"ok": True, "nom": nom, "parent_id": parent_id}


@router.delete("/api/qualite/ged/folders/{fid}")
def ged_delete_folder(fid: int, request: Request):
    """Corbeille recursive : le dossier, ses sous-dossiers et tous leurs fichiers
    partagent le meme trash_id, ce qui permet une restauration exacte."""
    user = _require_ged(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, nom FROM qualite_ged_folders WHERE id=? AND deleted_at IS NULL", (fid,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Dossier introuvable")
        ids = [fid] + _descendants(conn, fid)
        qm = ",".join("?" * len(ids))
        trash_id = uuid.uuid4().hex
        now = _now()
        conn.execute(
            f"UPDATE qualite_ged_files SET deleted_at=?, deleted_by=?, trash_id=? "
            f"WHERE folder_id IN ({qm}) AND deleted_at IS NULL",
            [now, user["id"], trash_id] + ids,
        )
        conn.execute(
            f"UPDATE qualite_ged_folders SET deleted_at=?, deleted_by=?, trash_id=? "
            f"WHERE id IN ({qm}) AND deleted_at IS NULL",
            [now, user["id"], trash_id] + ids,
        )
        # On retire de l'index : un document en corbeille ne doit plus remonter
        # dans les recherches. La reindexation se fait a la restauration.
        for r in conn.execute(
            f"SELECT id FROM qualite_ged_files WHERE folder_id IN ({qm}) "
            f"AND trash_id=?", ids + [trash_id]
        ).fetchall():
            _fts_delete(conn, r["id"])
        conn.commit()
    return {"ok": True, "trash_id": trash_id}


# ══════════════════════════════════════════════════════════════════════
# Fichiers - upload, metadonnees, versions
# ══════════════════════════════════════════════════════════════════════

def _store_upload(up: UploadFile) -> tuple[str, str, int, str]:
    """Ecrit le fichier sur disque. Renvoie (path, ext, size, sha256)."""
    ext = _check_ext_allowed(up.filename or "")
    raw = up.file.read()
    size = len(raw)
    if size == 0:
        raise HTTPException(status_code=400, detail="Fichier vide")
    if size > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Fichier trop volumineux ({size // 1048576} Mo) - limite {GED_MAX_FILE_MB} Mo",
        )
    path = _storage_path(ext)
    with open(path, "wb") as fh:
        fh.write(raw)
    return path, ext, size, hashlib.sha256(raw).hexdigest()


@router.post("/api/qualite/ged/folders/{folder_id}/files")
async def ged_upload_files(folder_id: int, request: Request,
                           background: BackgroundTasks,
                           files: List[UploadFile] = File(...)):
    """Upload multiple dans un dossier. folder_id = 0 -> racine."""
    user = _require_ged(request)
    fid = folder_id or None
    created, errors = [], []
    with get_db() as conn:
        if fid:
            p = conn.execute(
                "SELECT id FROM qualite_ged_folders WHERE id=? AND deleted_at IS NULL", (fid,)
            ).fetchone()
            if not p:
                raise HTTPException(status_code=404, detail="Dossier introuvable")

        for up in files:
            try:
                path, ext, size, sha = _store_upload(up)
            except HTTPException as e:
                errors.append({"nom": up.filename, "detail": str(e.detail)})
                continue

            nom = _uniq_file_name(conn, fid, _clean_name(up.filename, "document"))
            now = _now()
            cur = conn.execute(
                """INSERT INTO qualite_ged_files
                   (folder_id, nom, ext, mime_type, description, tags,
                    link_type, link_id, contenu_txt, index_status,
                    created_at, created_by, updated_at, updated_by)
                   VALUES (?,?,?,?,NULL,'',NULL,NULL,'','pending',?,?,?,?)""",
                (fid, nom, ext, up.content_type, now, user["id"], now, user["id"]),
            )
            file_id = cur.lastrowid
            conn.execute(
                """INSERT INTO qualite_ged_file_versions
                   (file_id, version, storage_path, size_bytes, sha256,
                    original_name, is_current, commentaire, uploaded_at, uploaded_by)
                   VALUES (?,1,?,?,?,?,1,NULL,?,?)""",
                (file_id, path, size, sha, up.filename or nom, now, user["id"]),
            )
            _fts_sync(conn, file_id, nom, "", "", "")
            created.append({"id": file_id, "nom": nom, "size_bytes": size})
            # Indexation : synchrone si petit (l'utilisateur voit le resultat
            # tout de suite), en tache de fond sinon (l'upload ne doit pas
            # attendre l'extraction d'un PDF de 200 pages).
            if size <= INLINE_SYNC_BYTES:
                conn.commit()
                _index_file(file_id, path, ext)
            else:
                background.add_task(_index_file, file_id, path, ext)
        conn.commit()
    return {"created": created, "errors": errors}


class FileUpdate(BaseModel):
    nom: Optional[str] = None
    folder_id: Optional[int] = None
    move: bool = False
    description: Optional[str] = None
    tags: Optional[str] = None
    link_type: Optional[str] = None
    link_id: Optional[int] = None


@router.put("/api/qualite/ged/files/{file_id}")
def ged_update_file(file_id: int, body: FileUpdate, request: Request):
    user = _require_ged(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM qualite_ged_files WHERE id=? AND deleted_at IS NULL", (file_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Document introuvable")

        folder_id = row["folder_id"]
        if body.move:
            folder_id = body.folder_id or None
            if folder_id:
                p = conn.execute(
                    "SELECT id FROM qualite_ged_folders WHERE id=? AND deleted_at IS NULL",
                    (folder_id,),
                ).fetchone()
                if not p:
                    raise HTTPException(status_code=404, detail="Dossier cible introuvable")

        nom = _clean_name(body.nom, row["nom"]) if body.nom is not None else row["nom"]
        nom = _uniq_file_name(conn, folder_id, nom, exclude_id=file_id)

        description = row["description"]
        if body.description is not None:
            description = (body.description or "").strip() or None

        tags = row["tags"]
        if body.tags is not None:
            tags = _norm_tags(body.tags)

        link_type, link_id = row["link_type"], row["link_id"]
        if body.link_type is not None or body.link_id is not None:
            link_type, link_id = _check_link(body.link_type, body.link_id)

        conn.execute(
            """UPDATE qualite_ged_files
                  SET folder_id=?, nom=?, description=?, tags=?,
                      link_type=?, link_id=?, updated_at=?, updated_by=?
                WHERE id=?""",
            (folder_id, nom, description, tags, link_type, link_id,
             _now(), user["id"], file_id),
        )
        _fts_sync(conn, file_id, nom, description or "", tags or "", row["contenu_txt"] or "")
        conn.commit()
    return {"ok": True, "nom": nom, "folder_id": folder_id, "tags": tags}


@router.post("/api/qualite/ged/files/{file_id}/version")
async def ged_new_version(file_id: int, request: Request,
                          background: BackgroundTasks,
                          file: UploadFile = File(...),
                          commentaire: str = Form("")):
    """Nouvelle version d'un document existant. L'ancienne reste consultable."""
    user = _require_ged(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM qualite_ged_files WHERE id=? AND deleted_at IS NULL", (file_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Document introuvable")
        path, ext, size, sha = _store_upload(file)
        nmax = conn.execute(
            "SELECT COALESCE(MAX(version),0) AS n FROM qualite_ged_file_versions WHERE file_id=?",
            (file_id,),
        ).fetchone()["n"]
        now = _now()
        conn.execute(
            "UPDATE qualite_ged_file_versions SET is_current=0 WHERE file_id=?", (file_id,)
        )
        conn.execute(
            """INSERT INTO qualite_ged_file_versions
               (file_id, version, storage_path, size_bytes, sha256,
                original_name, is_current, commentaire, uploaded_at, uploaded_by)
               VALUES (?,?,?,?,?,?,1,?,?,?)""",
            (file_id, nmax + 1, path, size, sha, file.filename or row["nom"],
             (commentaire or "").strip() or None, now, user["id"]),
        )
        conn.execute(
            "UPDATE qualite_ged_files SET ext=?, mime_type=?, index_status='pending', "
            "updated_at=?, updated_by=? WHERE id=?",
            (ext, file.content_type, now, user["id"], file_id),
        )
        conn.commit()
    if size <= INLINE_SYNC_BYTES:
        _index_file(file_id, path, ext)
    else:
        background.add_task(_index_file, file_id, path, ext)
    return {"ok": True, "version": nmax + 1}


@router.get("/api/qualite/ged/files/{file_id}")
def ged_get_file(file_id: int, request: Request):
    """Detail complet pour le panneau lateral : metadonnees + chemin + versions."""
    _require_ged(request)
    with get_db() as conn:
        row = conn.execute(
            _FILE_SELECT + " WHERE f.id=? AND f.deleted_at IS NULL", (file_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Document introuvable")
        d = dict(row)
        d["path"] = _folder_path_str(conn, d["folder_id"])
        d["breadcrumb"] = _breadcrumb(conn, d["folder_id"])
        vers = conn.execute(
            """SELECT v.id, v.version, v.size_bytes, v.original_name, v.is_current,
                      v.commentaire, v.uploaded_at, u.nom AS uploaded_by_nom
                 FROM qualite_ged_file_versions v
                 LEFT JOIN users u ON u.id = v.uploaded_by
                WHERE v.file_id=? ORDER BY v.version DESC""",
            (file_id,),
        ).fetchall()
        d["versions"] = [dict(r) for r in vers]
    return d


@router.get("/api/qualite/ged/files/{file_id}/versions")
def ged_list_versions(file_id: int, request: Request):
    _require_ged(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT v.id, v.version, v.size_bytes, v.original_name, v.is_current,
                      v.commentaire, v.uploaded_at, u.nom AS uploaded_by_nom
                 FROM qualite_ged_file_versions v
                 LEFT JOIN users u ON u.id = v.uploaded_by
                WHERE v.file_id=? ORDER BY v.version DESC""",
            (file_id,),
        ).fetchall()
    return {"versions": [dict(r) for r in rows]}


@router.post("/api/qualite/ged/files/{file_id}/versions/{version}/restore")
def ged_restore_version(file_id: int, version: int, request: Request):
    """Repasser une ancienne version en version courante, sans rien effacer."""
    user = _require_ged(request)
    with get_db() as conn:
        v = conn.execute(
            "SELECT * FROM qualite_ged_file_versions WHERE file_id=? AND version=?",
            (file_id, version),
        ).fetchone()
        if not v:
            raise HTTPException(status_code=404, detail="Version introuvable")
        conn.execute("UPDATE qualite_ged_file_versions SET is_current=0 WHERE file_id=?",
                     (file_id,))
        conn.execute("UPDATE qualite_ged_file_versions SET is_current=1 WHERE id=?", (v["id"],))
        conn.execute("UPDATE qualite_ged_files SET updated_at=?, updated_by=? WHERE id=?",
                     (_now(), user["id"], file_id))
        conn.commit()
        path, ext = v["storage_path"], _ext_of(v["storage_path"])
    _index_file(file_id, path, ext)
    return {"ok": True}


@router.delete("/api/qualite/ged/files/{file_id}")
def ged_delete_file(file_id: int, request: Request):
    user = _require_ged(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM qualite_ged_files WHERE id=? AND deleted_at IS NULL", (file_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Document introuvable")
        conn.execute(
            "UPDATE qualite_ged_files SET deleted_at=?, deleted_by=?, trash_id=? WHERE id=?",
            (_now(), user["id"], uuid.uuid4().hex, file_id),
        )
        _fts_delete(conn, file_id)
        conn.commit()
    return {"ok": True}


# ─── Telechargement / apercu ─────────────────────────────────────────

def _serve_version(conn, file_id: int, version: Optional[int], inline: bool):
    frow = conn.execute(
        "SELECT nom, ext, mime_type FROM qualite_ged_files WHERE id=?", (file_id,)
    ).fetchone()
    if not frow:
        raise HTTPException(status_code=404, detail="Document introuvable")
    if version:
        v = conn.execute(
            "SELECT * FROM qualite_ged_file_versions WHERE file_id=? AND version=?",
            (file_id, version),
        ).fetchone()
    else:
        v = _current_version(conn, file_id)
    if not v:
        raise HTTPException(status_code=404, detail="Version introuvable")
    if not v["storage_path"] or not os.path.exists(v["storage_path"]):
        raise HTTPException(status_code=410, detail="Fichier absent du disque")
    return frow, v


@router.get("/api/qualite/ged/files/{file_id}/download")
def ged_download(file_id: int, request: Request, version: int = 0):
    _require_ged(request)
    with get_db() as conn:
        frow, v = _serve_version(conn, file_id, version or None, inline=False)
    return FileResponse(
        v["storage_path"],
        media_type=frow["mime_type"] or "application/octet-stream",
        filename=frow["nom"],
    )


@router.get("/api/qualite/ged/files/{file_id}/preview")
def ged_preview(file_id: int, request: Request, version: int = 0):
    """Apercu inline (PDF, images). Le navigateur affiche au lieu de telecharger."""
    _require_ged(request)
    with get_db() as conn:
        frow, v = _serve_version(conn, file_id, version or None, inline=True)
        try:
            with open(v["storage_path"], "rb") as fh:
                data = fh.read()
        except Exception:
            raise HTTPException(status_code=500, detail="Erreur lecture fichier")
    safe = re.sub(r'[^A-Za-z0-9._ -]+', "_", frow["nom"] or "document")
    return Response(
        content=data,
        media_type=frow["mime_type"] or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{safe}"'},
    )


# ─── Export ZIP d'un dossier ─────────────────────────────────────────

@router.get("/api/qualite/ged/folders/{folder_id}/zip")
def ged_folder_zip(folder_id: int, request: Request):
    """Zippe le dossier et toute son arborescence (version courante des
    documents). Pratique pour envoyer un pack complet a un client ou un auditeur."""
    _require_ged(request)
    fid = folder_id or None
    with get_db() as conn:
        root_name = "GED-Qualite"
        if fid:
            row = conn.execute(
                "SELECT nom FROM qualite_ged_folders WHERE id=? AND deleted_at IS NULL", (fid,)
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Dossier introuvable")
            root_name = row["nom"]

        ids = ([fid] + _descendants(conn, fid)) if fid else None
        # Chemin relatif de chaque dossier, calcule une seule fois a partir
        # d'une carte chargee une seule fois.
        fmap = _folder_map(conn)
        rel = {}
        if fid:
            base_depth = len(_breadcrumb_from(fmap, fid)) - 1
            for i in ids:
                bc = _breadcrumb_from(fmap, i)
                rel[i] = "/".join(b["nom"] for b in bc[base_depth:])
        else:
            for i in fmap:
                bc = _breadcrumb_from(fmap, i)
                rel[i] = "/".join(b["nom"] for b in bc)

        if ids:
            qm = ",".join("?" * len(ids))
            rows = conn.execute(
                f"SELECT id, nom, folder_id FROM qualite_ged_files "
                f"WHERE deleted_at IS NULL AND folder_id IN ({qm})", ids
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, nom, folder_id FROM qualite_ged_files WHERE deleted_at IS NULL"
            ).fetchall()

        total = 0
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for r in rows:
                v = _current_version(conn, r["id"])
                if not v or not v["storage_path"] or not os.path.exists(v["storage_path"]):
                    continue
                total += v["size_bytes"] or 0
                if total > ZIP_MAX_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="Dossier trop volumineux pour un export ZIP "
                               "(limite 300 Mo) - zipper un sous-dossier",
                    )
                sub = rel.get(r["folder_id"], "")
                arc = f"{sub}/{r['nom']}" if sub else r["nom"]
                zf.write(v["storage_path"], arcname=arc)
        data = buf.getvalue()

    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", _strip_accents(root_name)) or "dossier"
    return Response(
        content=data, media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={safe}.zip"},
    )


# ══════════════════════════════════════════════════════════════════════
# Recherche
# ══════════════════════════════════════════════════════════════════════

@router.get("/api/qualite/ged/search")
def ged_search(request: Request, q: str = "", tags: str = "", ext: str = "",
               link_type: str = "", link_id: int = 0, limit: int = 80):
    """Recherche sur le nom, les tags, la description ET le contenu texte des
    documents. Chaque resultat porte son chemin complet et un extrait surligne."""
    _require_ged(request)
    q = (q or "").strip()
    limit = max(1, min(int(limit or 80), 300))
    tag_list = [t for t in _norm_tags(tags).split(",") if t]

    with get_db() as conn:
        results = []
        use_fts = _fts_available(conn) and bool(_fts_query(q))

        if use_fts:
            sql = f"""
                SELECT f.id, f.folder_id, f.nom, f.ext, f.tags, f.description,
                       f.link_type, f.link_id, f.index_status, f.updated_at,
                       snippet(qualite_ged_fts, 3, '<mark>', '</mark>', ' ... ', 14) AS extrait,
                       bm25(qualite_ged_fts, 8.0, 4.0, 6.0, 1.0) AS score
                  FROM qualite_ged_fts
                  JOIN qualite_ged_files f ON f.id = qualite_ged_fts.rowid
                 WHERE qualite_ged_fts MATCH ? AND f.deleted_at IS NULL
            """
            params = [_fts_query(q)]
            if ext:
                sql += " AND f.ext = ?"
                params.append(ext.lower().lstrip("."))
            if link_type:
                sql += " AND f.link_type = ?"
                params.append(link_type)
                if link_id:
                    sql += " AND f.link_id = ?"
                    params.append(link_id)
            sql += " ORDER BY score LIMIT ?"
            params.append(limit)
            try:
                rows = conn.execute(sql, params).fetchall()
            except Exception:
                rows = []          # requete FTS invalide -> on bascule sur le LIKE
                use_fts = False
            if use_fts:
                results = [dict(r) for r in rows]

        if not use_fts:
            # Repli : LIKE sur nom + tags + description + contenu extrait.
            like = f"%{_strip_accents(q).lower()}%"
            sql = """
                SELECT f.id, f.folder_id, f.nom, f.ext, f.tags, f.description,
                       f.link_type, f.link_id, f.index_status, f.updated_at,
                       '' AS extrait, 0 AS score
                  FROM qualite_ged_files f
                 WHERE f.deleted_at IS NULL
            """
            params = []
            if q:
                sql += (" AND (LOWER(f.nom) LIKE ? OR LOWER(f.tags) LIKE ? "
                        "OR LOWER(COALESCE(f.description,'')) LIKE ? "
                        "OR LOWER(COALESCE(f.contenu_txt,'')) LIKE ?)")
                params += [like, like, like, like]
            if ext:
                sql += " AND f.ext = ?"
                params.append(ext.lower().lstrip("."))
            if link_type:
                sql += " AND f.link_type = ?"
                params.append(link_type)
                if link_id:
                    sql += " AND f.link_id = ?"
                    params.append(link_id)
            sql += " ORDER BY f.updated_at DESC LIMIT ?"
            params.append(limit)
            results = [dict(r) for r in conn.execute(sql, params).fetchall()]

        # Filtre tags applique apres coup : ils sont peu nombreux et deja normalises
        if tag_list:
            results = [r for r in results
                       if all(t in (r.get("tags") or "").split(",") for t in tag_list)]

        # Chemin lisible pour chaque resultat : sans ca, un nom de fichier seul
        # ne dit pas ou le document se trouve. La carte des dossiers est chargee
        # UNE fois pour tous les resultats (sinon on relit toute l'arborescence
        # a chaque ligne : 80 resultats = 80 scans pour rien).
        fmap = _folder_map(conn)
        for r in results:
            r["path"] = _path_from(fmap, r["folder_id"])

    return {"results": results, "count": len(results), "fts": bool(use_fts)}


@router.get("/api/qualite/ged/tags")
def ged_tags(request: Request):
    """Tous les tags utilises, avec leur frequence - pour l'autocompletion."""
    _require_ged(request)
    counts = {}
    with get_db() as conn:
        for r in conn.execute(
            "SELECT tags FROM qualite_ged_files WHERE deleted_at IS NULL AND tags <> ''"
        ).fetchall():
            for t in (r["tags"] or "").split(","):
                if t:
                    counts[t] = counts.get(t, 0) + 1
    out = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return {"tags": [{"tag": k, "n": v} for k, v in out[:200]]}


# ══════════════════════════════════════════════════════════════════════
# Corbeille
# ══════════════════════════════════════════════════════════════════════

@router.get("/api/qualite/ged/trash")
def ged_trash(request: Request):
    """Corbeille groupee par geste de suppression."""
    _require_ged(request)
    with get_db() as conn:
        folders = conn.execute(
            """SELECT f.id, f.nom, f.trash_id, f.deleted_at, u.nom AS deleted_by_nom
                 FROM qualite_ged_folders f
                 LEFT JOIN users u ON u.id = f.deleted_by
                WHERE f.deleted_at IS NOT NULL""",
        ).fetchall()
        files = conn.execute(
            """SELECT f.id, f.nom, f.ext, f.trash_id, f.deleted_at, u.nom AS deleted_by_nom
                 FROM qualite_ged_files f
                 LEFT JOIN users u ON u.id = f.deleted_by
                WHERE f.deleted_at IS NOT NULL""",
        ).fetchall()

    groups = {}
    for r in folders:
        g = groups.setdefault(r["trash_id"], {
            "trash_id": r["trash_id"], "deleted_at": r["deleted_at"],
            "deleted_by_nom": r["deleted_by_nom"], "folders": [], "files": [],
        })
        g["folders"].append({"id": r["id"], "nom": r["nom"]})
    for r in files:
        g = groups.setdefault(r["trash_id"], {
            "trash_id": r["trash_id"], "deleted_at": r["deleted_at"],
            "deleted_by_nom": r["deleted_by_nom"], "folders": [], "files": [],
        })
        g["files"].append({"id": r["id"], "nom": r["nom"], "ext": r["ext"]})

    out = []
    for g in groups.values():
        label = (g["folders"][0]["nom"] if g["folders"]
                 else (g["files"][0]["nom"] if g["files"] else "?"))
        n = len(g["folders"]) + len(g["files"])
        out.append({**g, "label": label, "count": n,
                    "kind": "folder" if g["folders"] else "file"})
    out.sort(key=lambda x: x["deleted_at"] or "", reverse=True)
    return {"groups": out}


@router.post("/api/qualite/ged/trash/{trash_id}/restore")
def ged_trash_restore(trash_id: str, request: Request):
    """Restaure tout ce qui a ete supprime dans le meme geste. Si le dossier
    parent a disparu entre-temps, l'element remonte a la racine plutot que de
    rester invisible."""
    _require_ged(request)
    with get_db() as conn:
        folders = conn.execute(
            "SELECT id, parent_id FROM qualite_ged_folders WHERE trash_id=?", (trash_id,)
        ).fetchall()
        files = conn.execute(
            "SELECT id, folder_id, nom, description, tags, contenu_txt "
            "FROM qualite_ged_files WHERE trash_id=?", (trash_id,)
        ).fetchall()
        if not folders and not files:
            raise HTTPException(status_code=404, detail="Element de corbeille introuvable")

        restored_folder_ids = {f["id"] for f in folders}
        for f in folders:
            parent = f["parent_id"]
            if parent and parent not in restored_folder_ids:
                alive = conn.execute(
                    "SELECT id FROM qualite_ged_folders WHERE id=? AND deleted_at IS NULL",
                    (parent,),
                ).fetchone()
                if not alive:
                    parent = None
            conn.execute(
                "UPDATE qualite_ged_folders SET deleted_at=NULL, deleted_by=NULL, "
                "trash_id=NULL, parent_id=? WHERE id=?", (parent, f["id"]),
            )
        for f in files:
            folder_id = f["folder_id"]
            if folder_id and folder_id not in restored_folder_ids:
                alive = conn.execute(
                    "SELECT id FROM qualite_ged_folders WHERE id=? AND deleted_at IS NULL",
                    (folder_id,),
                ).fetchone()
                if not alive:
                    folder_id = None
            conn.execute(
                "UPDATE qualite_ged_files SET deleted_at=NULL, deleted_by=NULL, "
                "trash_id=NULL, folder_id=? WHERE id=?", (folder_id, f["id"]),
            )
            _fts_sync(conn, f["id"], f["nom"], f["description"] or "",
                      f["tags"] or "", f["contenu_txt"] or "")
        conn.commit()
    return {"ok": True, "folders": len(folders), "files": len(files)}


@router.delete("/api/qualite/ged/trash/{trash_id}")
def ged_trash_purge(trash_id: str, request: Request):
    """Purge definitive : supprime les lignes ET les fichiers du disque.
    Seule action irreversible du module, donc reservee aux admins qualite."""
    _require_ged_admin(request)
    with get_db() as conn:
        files = conn.execute(
            "SELECT id FROM qualite_ged_files WHERE trash_id=?", (trash_id,)
        ).fetchall()
        folders = conn.execute(
            "SELECT id FROM qualite_ged_folders WHERE trash_id=?", (trash_id,)
        ).fetchall()
        if not files and not folders:
            raise HTTPException(status_code=404, detail="Element de corbeille introuvable")
        for f in files:
            for v in conn.execute(
                "SELECT storage_path FROM qualite_ged_file_versions WHERE file_id=?", (f["id"],)
            ).fetchall():
                try:
                    if v["storage_path"] and os.path.exists(v["storage_path"]):
                        os.remove(v["storage_path"])
                except Exception:
                    pass
            conn.execute("DELETE FROM qualite_ged_file_versions WHERE file_id=?", (f["id"],))
            _fts_delete(conn, f["id"])
            conn.execute("DELETE FROM qualite_ged_files WHERE id=?", (f["id"],))
        for f in folders:
            conn.execute("DELETE FROM qualite_ged_folders WHERE id=?", (f["id"],))
        conn.commit()
    return {"ok": True, "files": len(files), "folders": len(folders)}


# ══════════════════════════════════════════════════════════════════════
# Divers
# ══════════════════════════════════════════════════════════════════════

@router.get("/api/qualite/ged/link-options")
def ged_link_options(request: Request, type: str = "", q: str = ""):
    """Options de rattachement d'un dossier ou d'un document."""
    _require_ged(request)
    q = (q or "").strip()
    like = f"%{q}%"
    out = []
    with get_db() as conn:
        if type == "client":
            rows = conn.execute(
                "SELECT id, raison_sociale AS label FROM clients "
                + ("WHERE raison_sociale LIKE ? OR code LIKE ? " if q else "")
                + "ORDER BY raison_sociale COLLATE NOCASE ASC LIMIT 50",
                ((like, like) if q else ()),
            ).fetchall()
        elif type == "fournisseur":
            rows = conn.execute(
                "SELECT id, nom AS label FROM fournisseurs_fsc "
                + ("WHERE nom LIKE ? " if q else "")
                + "ORDER BY nom COLLATE NOCASE ASC LIMIT 50",
                ((like,) if q else ()),
            ).fetchall()
        elif type == "norme":
            rows = conn.execute(
                "SELECT id, COALESCE(NULLIF(acronyme,''), nom) AS label FROM qualite_ref_fiches "
                + ("WHERE nom LIKE ? OR acronyme LIKE ? " if q else "")
                + "ORDER BY nom COLLATE NOCASE ASC LIMIT 50",
                ((like, like) if q else ()),
            ).fetchall()
        else:
            rows = []
        out = [{"id": r["id"], "label": r["label"]} for r in rows]
    return {"options": out}


@router.get("/api/qualite/ged/link-label")
def ged_link_label(request: Request, type: str = "", id: int = 0):
    """Libelle d'un rattachement existant (affichage du panneau detail)."""
    _require_ged(request)
    if not type or not id:
        return {"label": None}
    tbl = {"client": ("clients", "raison_sociale"),
           "fournisseur": ("fournisseurs_fsc", "nom"),
           "norme": ("qualite_ref_fiches", "nom")}.get(type)
    if not tbl:
        return {"label": None}
    with get_db() as conn:
        r = conn.execute(f"SELECT {tbl[1]} AS label FROM {tbl[0]} WHERE id=?", (id,)).fetchone()
    return {"label": r["label"] if r else None}


@router.get("/api/qualite/ged/stats")
def ged_stats(request: Request):
    _require_ged(request)
    with get_db() as conn:
        nb_files = conn.execute(
            "SELECT COUNT(*) AS n FROM qualite_ged_files WHERE deleted_at IS NULL"
        ).fetchone()["n"]
        nb_folders = conn.execute(
            "SELECT COUNT(*) AS n FROM qualite_ged_folders WHERE deleted_at IS NULL"
        ).fetchone()["n"]
        octets = conn.execute(
            """SELECT COALESCE(SUM(v.size_bytes),0) AS n
                 FROM qualite_ged_file_versions v
                 JOIN qualite_ged_files f ON f.id = v.file_id
                WHERE f.deleted_at IS NULL"""
        ).fetchone()["n"]
        non_indexes = conn.execute(
            "SELECT COUNT(*) AS n FROM qualite_ged_files "
            "WHERE deleted_at IS NULL AND index_status <> 'ok'"
        ).fetchone()["n"]
        trash = conn.execute(
            "SELECT (SELECT COUNT(*) FROM qualite_ged_files WHERE deleted_at IS NOT NULL) + "
            "       (SELECT COUNT(*) FROM qualite_ged_folders WHERE deleted_at IS NOT NULL) AS n"
        ).fetchone()["n"]
        fts = _fts_available(conn)
    return {"files": nb_files, "folders": nb_folders, "bytes": octets,
            "non_indexes": non_indexes, "trash": trash, "fts": fts,
            "max_mo": GED_MAX_FILE_MB}
