import csv
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DB_PATH
from database import get_db


@dataclass
class PlanningRow:
    client: str = ""
    numero_of: str = ""
    ref_produit: str = ""
    format_raw: str = ""
    laize_raw: str = ""
    date_livraison: str = ""
    duree_heures: Optional[float] = None
    commentaire: str = ""


def _norm(s: str) -> str:
    return (s or "").strip()


def _parse_duration(val: str) -> Optional[float]:
    s = _norm(val)
    if not s:
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _extract_laize_mm(val: str) -> Tuple[Optional[float], str]:
    raw = _norm(val)
    if not raw:
        return None, ""
    m = re.search(r"(\d{2,4})", raw)
    if not m:
        return None, raw
    try:
        return float(int(m.group(1))), raw
    except ValueError:
        return None, raw


def _parse_format_mm(val: str) -> Tuple[Optional[float], Optional[float], str]:
    raw = _norm(val)
    if not raw:
        return None, None, ""
    s = raw.lower().replace("mm", "").replace(" ", "")
    s = s.replace("×", "*").replace("x", "*")
    s = s.replace(",", ".")
    m = re.search(r"(?P<a>\d+(?:\.\d+)?)\*(?P<b>\d+(?:\.\d+)?)", s)
    if not m:
        return None, None, raw
    try:
        a = float(m.group("a"))
        b = float(m.group("b"))
        return a, b, raw
    except ValueError:
        return None, None, raw


def _read_grid_csv(path: Path) -> List[List[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [list(row) for row in csv.reader(f)]


def _find_block(rows: List[List[str]], title: str) -> Tuple[int, int]:
    """Return (start_idx, end_idx_exclusive) for a block beginning with `title` row."""
    start = None
    for i, r in enumerate(rows):
        if len(r) and _norm(r[0]).lower() == title.lower():
            start = i
            break
    if start is None:
        raise ValueError(f"Bloc introuvable: {title}")
    end = len(rows)
    for j in range(start + 1, len(rows)):
        v = _norm(rows[j][0])
        if v and v.lower().startswith("cohésio") and v.lower() != title.lower():
            end = j
            break
    return start, end


def _transpose_block(rows: List[List[str]], start: int, end: int) -> List[PlanningRow]:
    """
    Block format:
      [title]
      client, ...
      numero of, ...
      ref produit, ...
      format, ...
      laize, ...
      date livraison, ...
      dureée, ...
      commentaire, ...
    Each column (from col 1..) is one dossier.
    """
    data: Dict[str, List[str]] = {}
    for r in rows[start + 1 : end]:
        if not r:
            continue
        key = _norm(r[0]).lower()
        if not key:
            continue
        data[key] = [(_norm(x) if x is not None else "") for x in r[1:]]

    def col(i: int, key: str) -> str:
        arr = data.get(key, [])
        return arr[i] if i < len(arr) else ""

    ncols = max((len(v) for v in data.values()), default=0)
    out: List[PlanningRow] = []
    for i in range(ncols):
        pr = PlanningRow(
            client=col(i, "client"),
            numero_of=col(i, "numero of"),
            ref_produit=col(i, "ref produit"),
            format_raw=col(i, "format"),
            laize_raw=col(i, "laize"),
            date_livraison=col(i, "date livraison"),
            duree_heures=_parse_duration(col(i, "dureée")) or _parse_duration(col(i, "duree")) or _parse_duration(col(i, "durée")),
            commentaire=col(i, "commentaire"),
        )
        if any([pr.client, pr.numero_of, pr.ref_produit, pr.format_raw, pr.laize_raw, pr.date_livraison, pr.commentaire, pr.duree_heures]):
            out.append(pr)
    return out


def _get_machine_id(conn, machine_name: str) -> int:
    row = conn.execute("SELECT id FROM machines WHERE nom=?", (machine_name,)).fetchone()
    if not row:
        raise ValueError(f"Machine non trouvée en base: {machine_name}")
    return int(row["id"])


def _append_entries(conn, machine_id: int, items: List[PlanningRow], machine_label: str) -> int:
    if not items:
        return 0
    max_pos = conn.execute(
        "SELECT COALESCE(MAX(position),0) AS p FROM planning_entries WHERE machine_id=?",
        (machine_id,),
    ).fetchone()["p"]
    pos = int(max_pos)
    now = datetime.now().isoformat()
    added = 0

    for it in items:
        numero_of = _norm(it.numero_of)
        if not numero_of:
            continue
        fl, fh, fmt_raw = _parse_format_mm(it.format_raw)
        laize_mm, laize_raw = _extract_laize_mm(it.laize_raw)

        commentaire = _norm(it.commentaire)
        extras = []
        if fmt_raw and (fl is None or fh is None):
            extras.append(f"format: {fmt_raw}")
        if laize_raw and laize_mm is None:
            extras.append(f"laize: {laize_raw}")
        if it.date_livraison and not re.search(r"\d{4}-\d{2}-\d{2}", it.date_livraison):
            extras.append(f"livraison: {it.date_livraison}")
        if extras:
            commentaire = (commentaire + " | " if commentaire else "") + " / ".join(extras)

        duree = float(it.duree_heures) if it.duree_heures is not None else 8.0
        # API impose 2..30h — on clamp ici pour éviter l'échec
        duree = max(2.0, min(30.0, duree))

        pos += 1
        conn.execute(
            """
            INSERT INTO planning_entries
                (machine_id, position, reference, client, description, format_l, format_h,
                 duree_heures, statut, notes, created_at, updated_at,
                 numero_of, ref_produit, laize, date_livraison, commentaire)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'attente', '', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                machine_id,
                pos,
                numero_of,
                it.client,
                "",
                fl,
                fh,
                duree,
                now,
                now,
                numero_of,
                it.ref_produit,
                laize_mm,
                _norm(it.date_livraison),
                commentaire,
            ),
        )
        added += 1

    # Invalidation des plans "attente" pour recalcul timeline
    conn.execute(
        "UPDATE planning_entries SET planned_start=NULL, planned_end=NULL WHERE machine_id=? AND statut='attente'",
        (machine_id,),
    )
    print(f"{machine_label}: +{added} dossiers")
    return added


def main(argv: List[str]) -> int:
    if len(argv) >= 2:
        csv_path = Path(argv[1])
    else:
        csv_path = Path.home() / "Downloads" / "Untitled spreadsheet - Sheet2.csv"

    if not csv_path.exists():
        print(f"CSV introuvable: {csv_path}")
        return 2

    print(f"Base SQLite utilisée: {DB_PATH}")

    rows = _read_grid_csv(csv_path)
    c1s, c1e = _find_block(rows, "Cohésio 1")
    c2s, c2e = _find_block(rows, "Cohésio 2")
    items_c1 = _transpose_block(rows, c1s, c1e)
    items_c2 = _transpose_block(rows, c2s, c2e)

    with get_db() as conn:
        mid1 = _get_machine_id(conn, "Cohésio 1")
        mid2 = _get_machine_id(conn, "Cohésio 2")
        a1 = _append_entries(conn, mid1, items_c1, "Cohésio 1")
        a2 = _append_entries(conn, mid2, items_c2, "Cohésio 2")
        conn.commit()

    print(f"OK — total ajoutés: {a1 + a2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

