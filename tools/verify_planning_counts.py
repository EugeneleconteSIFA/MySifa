import os
import sys
from pathlib import Path

_TOOL_PARENT = Path(__file__).resolve().parents[1]
_CODE_ROOT = Path(os.environ.get("MYSIFA_CODE_ROOT", str(_TOOL_PARENT))).resolve()
sys.path.insert(0, str(_CODE_ROOT))

from database import get_db


def main():
    with get_db() as conn:
        for name in ("Cohésio 1", "Cohésio 2"):
            mid = conn.execute("SELECT id FROM machines WHERE nom=?", (name,)).fetchone()
            if not mid:
                print(name, "machine introuvable")
                continue
            mid = int(mid[0])
            n = conn.execute(
                "SELECT COUNT(1) FROM planning_entries WHERE machine_id=?", (mid,)
            ).fetchone()[0]
            last = conn.execute(
                "SELECT position, numero_of, client FROM planning_entries WHERE machine_id=? ORDER BY position DESC LIMIT 1",
                (mid,),
            ).fetchone()
            print(name, "entries=", n, "last=", dict(last) if last else None)


if __name__ == "__main__":
    main()

