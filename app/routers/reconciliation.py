"""MyStock — Monitoring : réconciliation stocks PF ERP vs MySifa."""
import io
import re
import sqlite3
import unicodedata
from datetime import date, datetime, timedelta
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

# Alias normalisés (minuscules, espaces unifiés) — correspondance exacte ou préfixe
_ERP_COL_ALIASES: dict[str, tuple[str, ...]] = {
    "code1": ("code 1", "code1", "code article", "référence", "ref", "article"),
    "code2": ("code 2", "code2", "désignation", "libellé", "libelle"),
    "stock": ("stock réel", "stock reel", "stock réel pf", "stock pf", "quantité", "qte", "stock"),
    "designation": (
        "désignation produit",
        "designation produit",
        "désignation",
        "designation",
    ),
    "mvt_lib": (
        "libellé dernier mvt",
        "libelle dernier mvt",
        "libellé du dernier mvt",
        "libelle du dernier mvt",
    ),
    "mvt_date": (
        "date dernier mvt",
        "date du dernier mvt",
        "date mvt",
    ),
    "mvt_qte": (
        "quantité dernier mvt",
        "quantite dernier mvt",
        "quantité du dernier mvt",
        "qte dernier mvt",
    ),
}

_ERP_REQUIRED_KEYS = ("code1", "code2", "stock")
_ERP_OPTIONAL_KEYS = ("designation", "mvt_lib", "mvt_date", "mvt_qte")
_ERP_REQUIRED_LABELS = {
    "code1": "Code 1",
    "code2": "Code 2",
    "stock": "Stock réel",
    "designation": "Désignation produit",
    "mvt_lib": "Libellé dernier Mvt",
    "mvt_date": "Date dernier Mvt",
    "mvt_qte": "Quantité dernier Mvt",
}


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
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        # Sériel Excel (jours depuis 1899-12-30)
        try:
            base = datetime(1899, 12, 30)
            dt = base + timedelta(days=float(val))
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        except (OverflowError, ValueError):
            pass
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


def _norm_header(val: Any) -> str:
    s = _cell_str(val)
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s)
    return s.lower()


def _erp_code_part(val: Any) -> str:
    if val is None or val == "":
        return ""
    if isinstance(val, bool):
        return ""
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        if val == int(val):
            return str(int(val))
        return str(val).strip().replace(",", ".")
    s = _cell_str(val)
    if not s:
        return ""
    try:
        f = float(s.replace(",", "."))
        if f == int(f):
            return str(int(f))
    except ValueError:
        pass
    return s


def _erp_code2_part(val: Any) -> str:
    c2 = _erp_code_part(val)
    if c2.isdigit() and len(c2) < 4:
        return c2.zfill(4)
    return c2


def _erp_reference(code1: Any, code2: Any) -> Optional[str]:
    c1 = _erp_code_part(code1)
    if not c1:
        return None
    c2 = _erp_code2_part(code2)
    return f"{c1}/{c2}" if c2 else c1


def _header_matches(norm: str, aliases: tuple[str, ...]) -> bool:
    if not norm:
        return False
    for alias in aliases:
        if norm == alias:
            return True
        if norm.startswith(alias + " ") or norm.startswith(alias + "("):
            return True
        # Correspondance partielle uniquement pour alias longs et spécifiques
        if len(alias) >= 14 and alias in norm:
            return True
    return False


def _row_looks_like_erp_header(row: list) -> bool:
    norms = [_norm_header(c) for c in row if _norm_header(c)]
    has_code1 = any(_header_matches(n, _ERP_COL_ALIASES["code1"]) for n in norms)
    has_stock = any(_header_matches(n, _ERP_COL_ALIASES["stock"]) for n in norms)
    return has_code1 and has_stock


def _find_header_row_index(rows: list) -> int:
    for i, row in enumerate(rows[:30]):
        if row and _row_looks_like_erp_header(row):
            return i
    return 0


def _resolve_erp_columns(headers: list) -> dict[str, int]:
    norms = [_norm_header(h) for h in headers]
    col_idx: dict[str, int] = {}
    for key, aliases in _ERP_COL_ALIASES.items():
        for i, h in enumerate(norms):
            if _header_matches(h, aliases):
                col_idx[key] = i
                break
    return col_idx


def _score_column_map(col_idx: dict[str, int]) -> int:
    score = 0
    for k in _ERP_REQUIRED_KEYS:
        if k in col_idx:
            score += 100
    for k in _ERP_OPTIONAL_KEYS:
        if k in col_idx:
            score += 1
    return score


def _open_erp_workbook(contents: bytes) -> CalamineWorkbook:
    try:
        return CalamineWorkbook.from_filelike(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(
            400,
            "Fichier illisible — vérifiez qu'il s'agit bien de l'export Table Stocks (.xlsx).",
        ) from e


def _sheet_names_priority(wb: CalamineWorkbook) -> list[str]:
    names = list(wb.sheet_names or [])
    if not names:
        return []
    if "A" in names:
        return ["A"] + [n for n in names if n != "A"]
    return names


def _parse_erp_sheet_rows(rows: list) -> tuple[dict[str, dict], int, dict[str, int], list]:
    if not rows:
        raise HTTPException(400, "Fichier vide — aucune ligne de données.")

    header_i = _find_header_row_index(rows)
    headers = rows[header_i]
    col_idx = _resolve_erp_columns(headers)

    missing = [k for k in _ERP_REQUIRED_KEYS if k not in col_idx]
    if missing:
        found = [_cell_str(h) for h in headers if _cell_str(h)][:20]
        missing_labels = ", ".join(_ERP_REQUIRED_LABELS[k] for k in missing)
        found_hint = (
            " Colonnes détectées : " + " | ".join(found) + "."
            if found
            else ""
        )
        raise HTTPException(
            400,
            f"Colonnes manquantes : {missing_labels}.{found_hint}",
        )

    erp_index: dict[str, dict] = {}

    def _col(row: list, key: str) -> Any:
        if key not in col_idx:
            return None
        i = col_idx[key]
        return row[i] if i < len(row) else None

    for row in rows[header_i + 1 :]:
        if not row:
            continue
        ref = _erp_reference(_col(row, "code1"), _col(row, "code2"))
        if not ref:
            continue
        erp_index[ref] = {
            "stock_erp": _to_float(_col(row, "stock")),
            "designation": _cell_str(_col(row, "designation")) or None,
            "mvt_libelle": _cell_str(_col(row, "mvt_lib")) or None,
            "mvt_date": _to_iso_datetime(_col(row, "mvt_date")),
            "mvt_qte": _to_float(_col(row, "mvt_qte")),
        }

    if not erp_index:
        raise HTTPException(
            400,
            "Aucune référence lisible — vérifiez que le fichier contient des lignes avec Code 1 renseigné.",
        )

    return erp_index, header_i, col_idx, headers


def _parse_erp_workbook(contents: bytes) -> dict[str, dict]:
    wb = _open_erp_workbook(contents)
    if not wb.sheet_names:
        raise HTTPException(400, "Fichier vide — aucune feuille trouvée.")

    best: Optional[tuple[dict[str, dict], int]] = None
    best_score = -1
    last_exc: Optional[HTTPException] = None

    for sheet_name in _sheet_names_priority(wb):
        rows = wb.get_sheet_by_name(sheet_name).to_python()
        if not rows:
            continue
        try:
            erp_index, header_i, col_idx, _headers = _parse_erp_sheet_rows(rows)
            score = _score_column_map(col_idx) + len(erp_index)
            if score > best_score:
                best_score = score
                best = (erp_index, header_i)
        except HTTPException as exc:
            last_exc = exc
            continue

    if best:
        return best[0]

    if last_exc:
        raise last_exc

    raise HTTPException(
        400,
        "Fichier illisible — aucune feuille Table Stocks reconnue (Code 1, Code 2, Stock réel).",
    )


def _diagnose_erp_workbook(contents: bytes) -> dict:
    """Analyse le fichier sans importer (diagnostic 400)."""
    try:
        wb = _open_erp_workbook(contents)
    except HTTPException as exc:
        return {"ok": False, "error": str(exc.detail)}

    sheets_out = []
    for sheet_name in _sheet_names_priority(wb):
        rows = wb.get_sheet_by_name(sheet_name).to_python()
        if not rows:
            sheets_out.append({"name": sheet_name, "empty": True})
            continue
        header_i = _find_header_row_index(rows)
        headers = [_cell_str(h) for h in rows[header_i] if _cell_str(h)]
        col_idx = _resolve_erp_columns(rows[header_i])
        missing = [k for k in _ERP_REQUIRED_KEYS if k not in col_idx]
        sheets_out.append({
            "name": sheet_name,
            "header_row": header_i,
            "headers": headers[:30],
            "columns_found": list(col_idx.keys()),
            "missing": [_ERP_REQUIRED_LABELS[k] for k in missing],
            "score": _score_column_map(col_idx),
        })

    scored = [s for s in sheets_out if not s.get("empty")]
    best = max(scored, key=lambda s: s.get("score", 0)) if scored else None
    if best and not best.get("missing"):
        return {
            "ok": True,
            "sheet": best["name"],
            "header_row": best["header_row"],
            "headers": best["headers"],
            "columns_found": best["columns_found"],
            "sheets": sheets_out,
        }

    err_parts = []
    if best:
        sheet_name = best.get("name", "inconnue")
        missing_cols = ", ".join(best.get("missing") or [])
        err_parts.append(f"Feuille analysée : {sheet_name}")
        if missing_cols:
            err_parts.append(f"Colonnes manquantes : {missing_cols}")
        if best.get("headers"):
            found_cols = " | ".join(best["headers"][:15])
            err_parts.append(f"Colonnes trouvées : {found_cols}")
        err_parts.append("Vérifiez que le fichier est bien l'export Table Stocks ERP (.xlsx).")
    else:
        err_parts.append("Aucune feuille avec données reconnue.")

    return {
        "ok": False,
        "error": ". ".join(err_parts),
        "sheets": sheets_out,
    }


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


@router.post("/api/reconciliation/import/preview")
async def preview_reconciliation_import(
    request: Request, file: UploadFile = File(...)
):
    """Diagnostic : en-têtes détectés sans enregistrer de snapshot."""
    require_monitoring(request)
    contents = await file.read()
    if not contents:
        raise HTTPException(400, "Fichier vide — sélectionnez un export Table Stocks (.xlsx).")
    return _diagnose_erp_workbook(contents)


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

    contents = await file.read()
    if not contents:
        raise HTTPException(400, "Fichier vide — sélectionnez un export Table Stocks (.xlsx).")

    try:
        erp_index = _parse_erp_workbook(contents)
    except HTTPException as exc:
        if exc.status_code == 400:
            diag = _diagnose_erp_workbook(contents)
            if not diag.get("ok") and diag.get("error"):
                raise HTTPException(400, str(diag["error"])) from exc
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

        # Enrichir avec les données pf_mouvements si des lignes existent
        pf_mvt_index: dict[str, dict] = {}
        if line_rows:
            # Extraire les références uniques
            refs = list({r["reference"] for r in line_rows})
            # Calculer la date seuil (7 jours glissants)
            seuil_date = (datetime.now(_PARIS) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
            # Requête groupée pour éviter N+1
            placeholders = ",".join("?" * len(refs))
            mvt_rows = conn.execute(
                f"""
                SELECT reference,
                       COUNT(CASE WHEN date_mouvement >= ? THEN 1 END) AS mvt_semaine_count,
                       MAX(date_mouvement) AS dernier_mvt_date
                FROM pf_mouvements
                WHERE reference IN ({placeholders})
                GROUP BY reference
                """,
                [seuil_date] + refs,
            ).fetchall()
            # Construire l'index
            for mr in mvt_rows:
                pf_mvt_index[mr["reference"]] = {
                    "count": mr["mvt_semaine_count"] or 0,
                    "dernier": mr["dernier_mvt_date"],
                }

    return {
        "snapshot": _row_to_dict(snap),
        "lines": [
            {
                **_row_to_dict(r),
                "mysifa_mvt_semaine_count": pf_mvt_index.get(r["reference"], {}).get("count", 0),
                "mysifa_dernier_mvt_date": pf_mvt_index.get(r["reference"], {}).get("dernier", None),
            }
            for r in line_rows
        ],
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
