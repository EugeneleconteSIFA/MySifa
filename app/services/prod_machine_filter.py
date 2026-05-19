"""Filtre production par machine — 4 machines canoniques + alias en base."""
from typing import List, Optional

CANONICAL_MACHINES = ("Cohésio 1", "Cohésio 2", "DSI", "Repiquage")


def norm_machine_canonical(raw: str) -> Optional[str]:
    """Mappe une valeur machine brute vers un nom canonique (ou None)."""
    if not raw:
        return None
    s = str(raw).strip()
    if s in CANONICAL_MACHINES:
        return s
    n = s.lower().replace("é", "e").replace("è", "e").replace("ê", "e").strip()
    if "cohesio 1" in n or "cohesion 1" in n or "cohesio !" in n:
        return "Cohésio 1"
    if "cohesio 2" in n or "cohesion 2" in n:
        return "Cohésio 2"
    if n == "dsi" or n.startswith("dsi ") or n.endswith(" dsi") or " dsi " in n:
        return "DSI"
    if "repiquage" in n or n == "rep" or n.startswith("rep "):
        return "Repiquage"
    if n in ("c1",):
        return "Cohésio 1"
    if n in ("c2",):
        return "Cohésio 2"
    return None


def list_filter_machines(conn) -> List[str]:
    """Liste des machines proposées dans le filtre MyProd (table machines, sinon défaut)."""
    rows = conn.execute(
        "SELECT nom FROM machines WHERE actif=1 ORDER BY id"
    ).fetchall()
    from_db = [r["nom"] for r in rows if r["nom"]]
    if from_db:
        ordered = [n for n in CANONICAL_MACHINES if n in from_db]
        return ordered or from_db[:4]
    return list(CANONICAL_MACHINES)


def resolve_machine_values(conn, selected: List[str]) -> List[str]:
    """Étend les noms canoniques vers toutes les valeurs distinctes présentes en base."""
    wanted = {s for s in selected if s in CANONICAL_MACHINES}
    if not wanted:
        return []
    rows = conn.execute(
        """SELECT DISTINCT machine FROM production_data
           WHERE machine IS NOT NULL AND TRIM(machine) != ''"""
    ).fetchall()
    out = set(wanted)
    for r in rows:
        raw = (r["machine"] or "").strip()
        if not raw:
            continue
        canon = norm_machine_canonical(raw)
        if canon in wanted:
            out.add(raw)
    return sorted(out)


def append_machine_filter(where: List[str], params: List, conn, selected: List[str]) -> None:
    """Ajoute une clause WHERE machine IN (...) avec alias résolus."""
    values = resolve_machine_values(conn, selected)
    if not values:
        where.append("1=0")
        return
    where.append(f"machine IN ({','.join('?' * len(values))})")
    params.extend(values)
