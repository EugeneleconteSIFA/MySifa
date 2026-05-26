import json
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "data" / "uploads" / "excel-data-export.json"
d = json.loads(p.read_text(encoding="utf-8"))
for m in d["materials"][:5]:
    print(m)
print("--- imported sample ---")
for m in d["materials"]:
    if m.get("is_imported"):
        print(m["name"], m.get("transport_per_m2"), m.get("transport_usd_total"), m.get("container_cost_usd"))
        break
# check extra fields on any material
all_keys = set()
for m in d["materials"]:
    all_keys.update(m.keys())
print("all material keys", sorted(all_keys))
