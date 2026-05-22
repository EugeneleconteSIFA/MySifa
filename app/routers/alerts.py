"""MySifa — Compteurs d'alertes (favicon badge)."""

from fastapi import APIRouter, Request

from config import ROLE_ADMINISTRATION, ROLE_DIRECTION
from database import get_db
from services.auth_service import get_current_user

router = APIRouter(tags=["alerts"])


def _norm_email(s: str) -> str:
    return str(s or "").strip().lower()


def _table_has_column(conn, table: str, column: str) -> bool:
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    return column in cols


def _count_stock_alerts(conn) -> int:
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    if "matieres_premieres" not in tables:
        return 0
    if not _table_has_column(conn, "matieres_premieres", "seuil_alerte"):
        return 0
    row = conn.execute(
        """
        SELECT COUNT(*) AS n
        FROM matieres_premieres mp
        LEFT JOIN mp_stock s ON s.matiere_id = mp.id
        WHERE mp.actif = 1 AND mp.seuil_alerte > 0
          AND COALESCE(s.quantite, 0) <= mp.seuil_alerte
        """
    ).fetchone()
    return int(row["n"] if row else 0)


@router.get("/api/alerts/count")
def alerts_count(request: Request):
    user = get_current_user(request)
    email = _norm_email(user.get("email"))
    role = str(user.get("role") or "").strip()

    referer = (request.headers.get("referer") or "").lower()
    on_messages_page = "/messages" in referer

    messages = 0
    validations = 0
    stock = 0

    with get_db() as conn:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }

        if "messages" in tables and email:
            row = conn.execute(
                """SELECT COUNT(*) AS n
                   FROM messages
                   WHERE to_email=? AND deleted=0
                     AND (read_at IS NULL OR TRIM(read_at)='')""",
                (email,),
            ).fetchone()
            messages = int(row["n"] if row else 0)

        if role in (ROLE_DIRECTION, ROLE_ADMINISTRATION) and "planning_entries" in tables:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM planning_entries WHERE statut='attente'"
            ).fetchone()
            validations = int(row["n"] if row else 0)

        stock = _count_stock_alerts(conn)

    total = validations + stock
    if not on_messages_page:
        total += messages

    return {
        "total": total,
        "detail": {
            "messages": messages,
            "validations": validations,
            "stock": stock,
        },
    }
