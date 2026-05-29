"""MyStock — Monitoring : réconciliation stocks PF ERP vs MySifa."""
import io
import sqlite3
from datetime import date, datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from python_calamine import CalamineWorkbook

from app.routers.stock import _resolve_created_by_name
from database import get_db
from services.auth_service import get_current_user

router = APIRouter()

_MONITORING_ROLES = frozenset({"superadmin", "direction", "administration"})
_PARIS = ZoneInfo("Europe/Paris")

_ERP_COL_CODE1 = "Code 1"
_ERP_COL_CODE2 = "Code 2"
_ERP_COL_STOCK = "Stock réel"
_ERP_COL_DESIGNATION = "Désignation produit "
_ERP_COL_MVT_LIB = "Libellé dernier Mvt"
_ERP_COL_MVT_DATE = "Date dernier Mvt"
_ERP_COL_MVT_QTE = "Quantité dernier Mvt"

_REQUIRED_ERP_COLS = (
    _ERP_COL_CODE1,
    _ERP_COL_CODE2,
    _ERP_COL_STOCK,
    _ERP_COL_DESIGNATION,
    _ERP_COL_MVT_LIB,
    _ERP_COL_MVT_DATE,
    _ERP_COL_MVT_QTE,
)


def require_monitoring(request: Request) -> dict:
    user = get_current_user(request)
    if user.get("role") not in _MONITORING_ROLES:
        raise HTTPException(
            403, "Accès réservé à la Direction et à l'Administration"
        )
    return user


def _now_paris_iso() -> str:
    return datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")


def _to_float(val: Any) -> float:
    if val is None or val == "":
        return 0.0
    if isinstance(val, bool):
        return float(val)
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _to_iso_datetime(val: Any) -> Optional[str]:
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(val, date):
        return datetime(val.year, val.month, val.day).strftime("%Y-%m-%dT%H:%M:%S")
    s = str(val).strip()
    if not s:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
    return s


def _cell_str(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _erp_reference(code1: Any, code2: Any) -> Optional[str]:
    c1 = _cell_str(code1)
    if not c1:
        return None
    c2 = _cell_str(code2)
    return f"{c1}/{c2}" if c2 else c1


def _parse_erp_workbook(contents: bytes) -> dict[str, dict]:
    try:
        wb = CalamineWorkbook.from_filelike(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(
            400,
            "Fichier illisible — vérifiez qu'il s'agit bien de l'export Table Stocks (.xlsx).",
        ) from e

    if not wb.sheet_names:
        raise HTTPException(400, "Fichier vide — aucune feuille trouvée.")

    sheet = wb.get_sheet_by_name(wb.sheet_names[0])
    rows = sheet.to_python()
    if not rows:
        raise HTTPException(400, "Fichier vide — aucune ligne de données.")

    headers = [_cell_str(h) for h in rows[0]]
    col_idx: dict[str, int] = {}
    for i, h in enumerate(headers):
        if h and h not in col_idx:
            col_idx[h] = i

    missing = [c for c in _REQUIRED_ERP_COLS if c not in col_idx]
    if missing:
        raise HTTPException(
            400,
            f"Colonnes manquantes dans l'export ERP : {', '.join(missing)}.",
        )

    erp_index: dict[str, dict] = {}
    for row in rows[1:]:
        if not row:
            continue
        ref = _erp_reference(
            row[col_idx[_ERP_COL_CODE1]] if col_idx[_ERP_COL_CODE1] < len(row) else None,
            row[col_idx[_ERP_COL_CODE2]] if col_idx[_ERP_COL_CODE2] < len(row) else None,
        )
        if not ref:
            continue

        def _col(name: str) -> Any:
            i = col_idx[name]
            return row[i] if i < len(row) else None

        erp_index[ref] = {
            "stock_erp": _to_float(_col(_ERP_COL_STOCK)),
            "designation": _cell_str(_col(_ERP_COL_DESIGNATION)) or None,
            "mvt_libelle": _cell_str(_col(_ERP_COL_MVT_LIB)) or None,
            "mvt_date": _to_iso_datetime(_col(_ERP_COL_MVT_DATE)),
            "mvt_qte": _to_float(_col(_ERP_COL_MVT_QTE)),
        }

    return erp_index


def _load_mysifa_index(conn: sqlite3.Connection) -> dict[str, dict]:
    rows = conn.execute(
        """
        SELECT p.reference, p.designation, p.unite,
               COALESCE(SUM(CASE WHEN l.quantite_restante > 0 THEN l.quantite_restante END), 0)
                   AS stock_mysifa,
               MIN(CASE WHEN l.quantite_restante > 0 THEN l.date_entree END) AS date_fifo
        FROM produits p
        LEFT JOIN lots_stock l ON l.produit_id = p.id
        GROUP BY p.id
        """
    ).fetchall()

    index: dict[str, dict] = {}
    for r in rows:
        ref = _cell_str(r["reference"])
        if not ref:
            continue
        index[ref] = {
            "designation": r["designation"],
            "unite": r["unite"],
            "stock_mysifa": float(r["stock_mysifa"] or 0),
            "date_fifo": r["date_fifo"],
        }
    return index


def _build_reconciliation_lines(
    erp_index: dict[str, dict], mysifa_index: dict[str, dict]
) -> list[dict]:
    lines: list[dict] = []

    for ref, ms in mysifa_index.items():
        stock_mysifa = ms["stock_mysifa"]
        erp = erp_index.get(ref)
        if erp is None:
            lines.append(
                {
                    "reference": ref,
                    "designation": ms.get("designation"),
                    "unite": ms.get("unite"),
                    "stock_erp": None,
                    "stock_mysifa": stock_mysifa,
                    "ecart": None,
                    "statut": "sans_corresp_erp",
                    "erp_dernier_mvt_libelle": None,
                    "erp_dernier_mvt_date": None,
                    "erp_dernier_mvt_qte": None,
                    "mysifa_date_fifo": ms.get("date_fifo"),
                }
            )
            continue

        stock_erp = erp["stock_erp"]
        ecart = stock_mysifa - stock_erp
        statut = "ok" if ecart == 0 else "ecart"
        designation = erp.get("designation") or ms.get("designation")
        lines.append(
            {
                "reference": ref,
                "designation": designation,
                "unite": ms.get("unite"),
                "stock_erp": stock_erp,
                "stock_mysifa": stock_mysifa,
                "ecart": ecart,
                "statut": statut,
                "erp_dernier_mvt_libelle": erp.get("mvt_libelle"),
                "erp_dernier_mvt_date": erp.get("mvt_date"),
                "erp_dernier_mvt_qte": erp.get("mvt_qte"),
                "mysifa_date_fifo": ms.get("date_fifo"),
            }
        )

    for ref, erp in erp_index.items():
        if ref in mysifa_index:
            continue
        stock_erp = erp["stock_erp"]
        if abs(stock_erp) < 1e-9:
            continue
        lines.append(
            {
                "reference": ref,
                "designation": erp.get("designation"),
                "unite": None,
                "stock_erp": stock_erp,
                "stock_mysifa": None,
                "ecart": None,
                "statut": "sans_corresp_mysifa",
                "erp_dernier_mvt_libelle": erp.get("mvt_libelle"),
                "erp_dernier_mvt_date": erp.get("mvt_date"),
                "erp_dernier_mvt_qte": erp.get("mvt_qte"),
                "mysifa_date_fifo": None,
            }
        )

    return lines


def _snapshot_counts(lines: list[dict], erp_index: dict, mysifa_index: dict) -> dict:
    matched = sum(
        1
        for ln in lines
        if ln["statut"] in ("ok", "ecart")
    )
    return {
        "nb_refs_erp": len(erp_index),
        "nb_refs_mysifa": len(mysifa_index),
        "nb_matched": matched,
        "nb_ecarts": sum(1 for ln in lines if ln["statut"] == "ecart"),
        "nb_sans_corresp": sum(1 for ln in lines if ln["statut"] == "sans_corresp_erp"),
        "nb_negatifs": sum(
            1
            for ln in lines
            if (ln.get("stock_erp") is not None and ln["stock_erp"] < 0)
            or (ln.get("stock_mysifa") is not None and ln["stock_mysifa"] < 0)
        ),
    }


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


@router.post("/api/reconciliation/import")
async def import_reconciliation(
    request: Request, file: UploadFile = File(...)
):
    user = require_monitoring(request)
    filename = file.filename or "import.xlsx"
    if not filename.lower().endswith((".xlsx", ".xlsm", ".xls")):
        raise HTTPException(
            400,
            "Format non supporté — importez l'export Table Stocks au format .xlsx.",
        )

    try:
        contents = await file.read()
        erp_index = _parse_erp_workbook(contents)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            400,
            "Fichier illisible — vérifiez qu'il s'agit bien de l'export Table Stocks (.xlsx).",
        ) from e

    created_at = _now_paris_iso()

    with get_db() as conn:
        mysifa_index = _load_mysifa_index(conn)
        lines = _build_reconciliation_lines(erp_index, mysifa_index)
        counts = _snapshot_counts(lines, erp_index, mysifa_index)
        created_by_name = _resolve_created_by_name(conn, user)

        cur = conn.execute(
            """
            INSERT INTO reconciliation_snapshots (
                created_at, created_by_name, source_filename,
                nb_refs_erp, nb_refs_mysifa, nb_matched, nb_ecarts,
                nb_sans_corresp, nb_negatifs
            ) VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                created_at,
                created_by_name,
                filename,
                counts["nb_refs_erp"],
                counts["nb_refs_mysifa"],
                counts["nb_matched"],
                counts["nb_ecarts"],
                counts["nb_sans_corresp"],
                counts["nb_negatifs"],
            ),
        )
        snapshot_id = cur.lastrowid

        conn.executemany(
            """
            INSERT INTO reconciliation_lines (
                snapshot_id, reference, designation, unite,
                stock_erp, stock_mysifa, ecart, statut,
                erp_dernier_mvt_libelle, erp_dernier_mvt_date, erp_dernier_mvt_qte,
                mysifa_date_fifo
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            [
                (
                    snapshot_id,
                    ln["reference"],
                    ln.get("designation"),
                    ln.get("unite"),
                    ln.get("stock_erp"),
                    ln.get("stock_mysifa"),
                    ln.get("ecart"),
                    ln["statut"],
                    ln.get("erp_dernier_mvt_libelle"),
                    ln.get("erp_dernier_mvt_date"),
                    ln.get("erp_dernier_mvt_qte"),
                    ln.get("mysifa_date_fifo"),
                )
                for ln in lines
            ],
        )
        conn.commit()

    return {
        "snapshot_id": snapshot_id,
        "nb_refs_erp": counts["nb_refs_erp"],
        "nb_matched": counts["nb_matched"],
        "nb_ecarts": counts["nb_ecarts"],
        "nb_sans_corresp": counts["nb_sans_corresp"],
        "nb_negatifs": counts["nb_negatifs"],
    }


@router.get("/api/reconciliation/snapshots")
def list_snapshots(request: Request):
    require_monitoring(request)
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, created_by_name, source_filename,
                   nb_refs_erp, nb_refs_mysifa, nb_matched, nb_ecarts,
                   nb_sans_corresp, nb_negatifs
            FROM reconciliation_snapshots
            ORDER BY created_at DESC
            LIMIT 52
            """
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


@router.get("/api/reconciliation/snapshots/{snapshot_id}")
def get_snapshot(
    request: Request,
    snapshot_id: int,
    statut: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
):
    require_monitoring(request)
    valid_statuts = {"ok", "ecart", "sans_corresp_erp", "sans_corresp_mysifa"}
    if statut is not None and statut not in valid_statuts:
        raise HTTPException(400, f"Statut invalide — valeurs : {', '.join(sorted(valid_statuts))}.")

    with get_db() as conn:
        snap = conn.execute(
            """
            SELECT id, created_at, created_by_name, source_filename,
                   nb_refs_erp, nb_refs_mysifa, nb_matched, nb_ecarts,
                   nb_sans_corresp, nb_negatifs
            FROM reconciliation_snapshots
            WHERE id = ?
            """,
            (snapshot_id,),
        ).fetchone()
        if not snap:
            raise HTTPException(404, "Snapshot introuvable.")

        sql = """
            SELECT id, snapshot_id, reference, designation, unite,
                   stock_erp, stock_mysifa, ecart, statut,
                   erp_dernier_mvt_libelle, erp_dernier_mvt_date, erp_dernier_mvt_qte,
                   mysifa_date_fifo
            FROM reconciliation_lines
            WHERE snapshot_id = ?
        """
        params: list[Any] = [snapshot_id]
        if statut:
            sql += " AND statut = ?"
            params.append(statut)
        if q and (q := q.strip()):
            sql += " AND (reference LIKE ? OR IFNULL(designation,'') LIKE ?)"
            pattern = f"%{q}%"
            params.extend([pattern, pattern])
        sql += " ORDER BY ABS(COALESCE(ecart, 0)) DESC, statut, reference"

        line_rows = conn.execute(sql, params).fetchall()

    return {
        "snapshot": _row_to_dict(snap),
        "lines": [_row_to_dict(r) for r in line_rows],
    }


@router.delete("/api/reconciliation/snapshots/{snapshot_id}")
def delete_snapshot(request: Request, snapshot_id: int):
    require_monitoring(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM reconciliation_snapshots WHERE id = ?",
            (snapshot_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Snapshot introuvable.")
        conn.execute(
            "DELETE FROM reconciliation_snapshots WHERE id = ?",
            (snapshot_id,),
        )
        conn.commit()
    return {"ok": True, "snapshot_id": snapshot_id}
