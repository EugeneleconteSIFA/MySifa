"""Database Viewer API — superadmin + direction uniquement.

Endpoints :
  GET /api/db/stats                        → stats globales (taille, nb tables, nb lignes total)
  GET /api/db/tables                       → liste des tables avec nb colonnes + nb lignes
  GET /api/db/table/{name}/schema          → colonnes (name, type, notnull, pk, default)
  GET /api/db/table/{name}/rows            → lignes paginées, avec recherche plein-texte
"""

import os
import sqlite3
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.services.auth_service import get_current_user
from config import DB_PATH, ROLE_SUPERADMIN, ROLE_DIRECTION

router = APIRouter(tags=["db-viewer"])

# ── Accès ────────────────────────────────────────────────────────────────────

_ROLES_DB = {ROLE_SUPERADMIN, ROLE_DIRECTION}

def _require_db_access(request: Request) -> dict:
    user = get_current_user(request)
    if user.get("role") not in _ROLES_DB:
        raise HTTPException(status_code=403, detail="Accès réservé à la direction et au super administrateur.")
    return user


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def _safe_table_name(name: str) -> str:
    """Valide que le nom de table ne contient que des caractères sûrs."""
    import re
    if not re.match(r'^[A-Za-z0-9_]+$', name):
        raise HTTPException(status_code=400, detail="Nom de table invalide.")
    return name


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/api/db/stats")
def db_stats(request: Request):
    _require_db_access(request)
    conn = _get_conn()
    try:
        # Taille du fichier
        try:
            size_bytes = os.path.getsize(DB_PATH)
        except OSError:
            size_bytes = 0

        # Liste des tables (user tables seulement)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        table_names = [t["name"] for t in tables]

        # Compte total de lignes (somme de toutes les tables)
        total_rows = 0
        for tname in table_names:
            try:
                cnt = conn.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
                total_rows += cnt
            except Exception:
                pass

        # SQLite version + page size
        sqlite_version = conn.execute("SELECT sqlite_version()").fetchone()[0]
        page_size = conn.execute("PRAGMA page_size").fetchone()[0]
        page_count = conn.execute("PRAGMA page_count").fetchone()[0]

        return {
            "db_path": DB_PATH,
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024 * 1024), 3),
            "table_count": len(table_names),
            "total_rows": total_rows,
            "sqlite_version": sqlite_version,
            "page_size": page_size,
            "page_count": page_count,
        }
    finally:
        conn.close()


@router.get("/api/db/tables")
def db_tables(request: Request):
    _require_db_access(request)
    conn = _get_conn()
    try:
        tables_raw = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()

        result = []
        for t in tables_raw:
            name = t["name"]
            # Nombre de colonnes
            cols = conn.execute(f'PRAGMA table_info("{name}")').fetchall()
            # Nombre de lignes
            try:
                row_count = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            except Exception:
                row_count = 0
            result.append({
                "name": name,
                "col_count": len(cols),
                "row_count": row_count,
            })
        return result
    finally:
        conn.close()


@router.get("/api/db/table/{name}/schema")
def db_table_schema(name: str, request: Request):
    _require_db_access(request)
    name = _safe_table_name(name)
    conn = _get_conn()
    try:
        cols = conn.execute(f'PRAGMA table_info("{name}")').fetchall()
        if not cols:
            raise HTTPException(status_code=404, detail=f"Table '{name}' introuvable.")
        return [
            {
                "cid": c["cid"],
                "name": c["name"],
                "type": c["type"] or "TEXT",
                "notnull": bool(c["notnull"]),
                "pk": bool(c["pk"]),
                "dflt_value": c["dflt_value"],
            }
            for c in cols
        ]
    finally:
        conn.close()


@router.get("/api/db/table/{name}/rows")
def db_table_rows(
    name: str,
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    order_col: Optional[str] = Query(None),
    order_dir: str = Query("ASC"),
):
    _require_db_access(request)
    name = _safe_table_name(name)

    if order_dir.upper() not in ("ASC", "DESC"):
        order_dir = "ASC"

    conn = _get_conn()
    try:
        cols = conn.execute(f'PRAGMA table_info("{name}")').fetchall()
        if not cols:
            raise HTTPException(status_code=404, detail=f"Table '{name}' introuvable.")
        col_names = [c["name"] for c in cols]

        # Construction de la clause WHERE (recherche texte sur toutes les colonnes)
        where_clause = ""
        params: list = []
        if search and search.strip():
            term = f"%{search.strip()}%"
            conditions = [f'CAST("{c}" AS TEXT) LIKE ?' for c in col_names]
            where_clause = "WHERE " + " OR ".join(conditions)
            params = [term] * len(col_names)

        # Comptage total (pour pagination)
        count_sql = f'SELECT COUNT(*) FROM "{name}" {where_clause}'
        total = conn.execute(count_sql, params).fetchone()[0]

        # Ordre
        order_clause = ""
        if order_col and order_col in col_names:
            order_clause = f'ORDER BY "{order_col}" {order_dir.upper()}'

        # Données paginées
        offset = (page - 1) * limit
        data_sql = f'SELECT * FROM "{name}" {where_clause} {order_clause} LIMIT ? OFFSET ?'
        rows = conn.execute(data_sql, params + [limit, offset]).fetchall()

        def _safe(v):
            """Convertit les bytes (BLOB) en représentation lisible pour JSON."""
            if isinstance(v, bytes):
                try:
                    return v.decode("utf-8", errors="replace")
                except Exception:
                    return f"<BLOB {len(v)} bytes>"
            return v

        return {
            "columns": col_names,
            "rows": [[_safe(cell) for cell in r] for r in rows],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": max(1, (total + limit - 1) // limit),
        }
    finally:
        conn.close()
