"""Database Viewer API — superadmin + direction, encadré par diagnostic_sql.

Endpoints :
  GET  /api/db/stats                        → stats globales (taille, nb tables, nb lignes)
  GET  /api/db/tables                       → tables lisibles, avec nb colonnes + nb lignes
  GET  /api/db/table/{name}/schema          → colonnes (name, type, notnull, pk, default, masquee)
  GET  /api/db/table/{name}/rows            → lignes paginées, avec recherche plein-texte
  POST /api/db/ai-query                     → question en français → SELECT + résultats

Ce module ne lit plus la base directement. Toute lecture passe par
`app/services/diagnostic_sql.executer()`, donc par l'autoriseur SQLite :
liste blanche de tables, colonnes masquées rendues NULL, plafond de lignes,
compteur d'opérations. Le viewer montre 162 tables sur 224, et les colonnes
sensibles d'une table par ailleurs lisible reviennent NULL.

Avant ce rebranchement, `rows` servait n'importe quelle table et n'importe
quelle colonne — `users` avec son hash, `api_keys`, `sessions`, `paie_*`,
`audit_logs`, `chat_messages` — et `ai-query` faisait exécuter à Claude du SQL
validé par une expression régulière. La régulière est un filtre de texte : elle
ne sait pas ce que la requête va lire. L'autoriseur, si.
"""

import os
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request

from app.services import diagnostic_sql
from app.services.auth_service import get_current_user
from app.services.db_ai_query import run_natural_language_query
from config import DB_PATH, ROLE_SUPERADMIN, ROLE_DIRECTION

router = APIRouter(tags=["db-viewer"])

# ── Accès ────────────────────────────────────────────────────────────────────

_ROLES_DB = {ROLE_SUPERADMIN, ROLE_DIRECTION}


def _require_db_access(request: Request) -> dict:
    user = get_current_user(request)
    if user.get("role") not in _ROLES_DB:
        raise HTTPException(status_code=403, detail="Accès réservé à la direction et au super administrateur.")
    return user


def _table_lisible(name: str) -> str:
    """Refuse tout de suite une table hors liste blanche.

    L'autoriseur la refuserait de toute façon à la lecture ; le faire ici
    permet de rendre un 404 explicite plutôt qu'un refus SQL, et évite de
    dire à l'appelant si la table existe ailleurs dans le schéma.
    """
    if name not in diagnostic_sql.TABLES_LISIBLES:
        raise HTTPException(status_code=404, detail=f"Table '{name}' introuvable ou non lisible.")
    return name


def _lire(sql: str, parametres: tuple = (), lignes_max: int = diagnostic_sql.LIGNES_MAX) -> dict:
    """Lecture encadrée, avec le refus traduit en réponse HTTP."""
    try:
        return diagnostic_sql.executer(DB_PATH, sql, parametres, lignes_max=lignes_max)
    except (diagnostic_sql.DiagnosticRefus, diagnostic_sql.DiagnosticTropLong) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _compter_lignes(tables: list[str]) -> dict[str, int]:
    """Nombre de lignes par table, en quelques requêtes plutôt qu'une par table.

    162 tables font 162 ouvertures de connexion si on compte une par une. Un
    UNION ALL par paquets de 40 en fait quatre, chacune passant par le même
    encadrement que le reste.
    """
    compte: dict[str, int] = {}
    for depart in range(0, len(tables), 40):
        paquet = tables[depart:depart + 40]
        sql = " UNION ALL ".join(
            f'SELECT \'{t}\' AS t, COUNT(*) AS n FROM "{t}"' for t in paquet
        )
        try:
            r = diagnostic_sql.executer(DB_PATH, sql, lignes_max=len(paquet))
        except (diagnostic_sql.DiagnosticRefus, diagnostic_sql.DiagnosticTropLong):
            # Une table du paquet manque à la base (liste blanche en avance sur
            # le schéma d'une instance) : on retombe sur un comptage unitaire
            # plutôt que de perdre les 39 autres.
            for t in paquet:
                try:
                    u = diagnostic_sql.executer(DB_PATH, f'SELECT COUNT(*) FROM "{t}"')
                    compte[t] = u["lignes"][0][0]
                except Exception:
                    compte[t] = 0
            continue
        for nom, n in r["lignes"]:
            compte[nom] = n
    return compte


def _colonnes(name: str) -> list[str]:
    """Noms des colonnes, obtenus à travers l'encadrement lui-même.

    `SELECT * ... LIMIT 0` fait passer la table par l'autoriseur et rend la
    description du curseur. Pas de PRAGMA, donc pas d'exception à la règle.
    """
    r = _lire(f'SELECT * FROM "{name}" LIMIT 0', (), lignes_max=1)
    return r["colonnes"]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/api/db/stats")
def db_stats(request: Request):
    _require_db_access(request)
    try:
        size_bytes = os.path.getsize(DB_PATH)
    except OSError:
        size_bytes = 0

    tables = sorted(diagnostic_sql.TABLES_LISIBLES)
    total_rows = sum(_compter_lignes(tables).values())

    return {
        "db_path": DB_PATH,
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / (1024 * 1024), 3),
        "table_count": len(tables),
        "total_rows": total_rows,
        **diagnostic_sql.geometrie_fichier(DB_PATH),
    }


@router.get("/api/db/tables")
def db_tables(request: Request):
    _require_db_access(request)
    tables = sorted(diagnostic_sql.TABLES_LISIBLES)
    lignes = _compter_lignes(tables)
    resultat = []
    for name in tables:
        try:
            cols = diagnostic_sql.colonnes_de_la_table(DB_PATH, name)
        except diagnostic_sql.DiagnosticRefus:
            continue
        resultat.append({
            "name": name,
            "col_count": len(cols),
            "row_count": lignes.get(name, 0),
            "masked_count": sum(1 for c in cols if c["masquee"]),
        })
    return resultat


@router.get("/api/db/table/{name}/schema")
def db_table_schema(name: str, request: Request):
    _require_db_access(request)
    name = _table_lisible(name)
    cols = diagnostic_sql.colonnes_de_la_table(DB_PATH, name)
    if not cols:
        raise HTTPException(status_code=404, detail=f"Table '{name}' introuvable.")
    return cols


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
    name = _table_lisible(name)
    col_names = _colonnes(name)
    if not col_names:
        raise HTTPException(status_code=404, detail=f"Table '{name}' introuvable.")

    if order_dir.upper() not in ("ASC", "DESC"):
        order_dir = "ASC"

    # Recherche plein-texte sur toutes les colonnes. Une colonne masquée revient
    # NULL, donc elle ne peut pas matcher — c'est le comportement voulu : on ne
    # retrouve pas une ligne par un fragment de ce qui est masqué.
    where_clause = ""
    params: list = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        where_clause = "WHERE " + " OR ".join(
            f'CAST("{c}" AS TEXT) LIKE ?' for c in col_names
        )
        params = [term] * len(col_names)

    total = _lire(f'SELECT COUNT(*) FROM "{name}" {where_clause}', tuple(params))["lignes"][0][0]

    order_clause = ""
    if order_col and order_col in col_names:
        order_clause = f'ORDER BY "{order_col}" {order_dir.upper()}'

    offset = (page - 1) * limit
    r = _lire(
        f'SELECT * FROM "{name}" {where_clause} {order_clause} LIMIT ? OFFSET ?',
        tuple(params + [limit, offset]),
        lignes_max=limit,
    )

    def _safe(v):
        """Les BLOB en représentation lisible pour JSON."""
        if isinstance(v, bytes):
            try:
                return v.decode("utf-8", errors="replace")
            except Exception:
                return f"<BLOB {len(v)} bytes>"
        return v

    return {
        "columns": r["colonnes"],
        "rows": [[_safe(cell) for cell in ligne] for ligne in r["lignes"]],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, (total + limit - 1) // limit),
    }


@router.post("/api/db/ai-query")
def db_ai_query(request: Request, body: dict = Body(...)):
    """Question en français → SELECT SQLite (Claude), exécuté sous encadrement.

    Le schéma envoyé au modèle ne décrit que les tables lisibles et tait les
    colonnes masquées : il ne peut donc pas proposer de lire ce qui est fermé.
    Et s'il le faisait quand même, l'autoriseur refuserait à la lecture.
    """
    _require_db_access(request)
    question = body.get("question") or body.get("q") or ""
    try:
        return run_natural_language_query(str(question))
    except HTTPException:
        raise
    except (diagnostic_sql.DiagnosticRefus, diagnostic_sql.DiagnosticTropLong) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'exécution : {e}") from e
