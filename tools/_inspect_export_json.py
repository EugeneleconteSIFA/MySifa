import json
from collections import Counter
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "data" / "uploads" / "excel-data-export.json"
raw = p.read_text(encoding="utf-8")
if '""' in raw[:30]:
    raw = raw.replace('""', '"')
d = json.loads(raw)
print("keys", list(d.keys()))
print("settings", d.get("settings"))
print("suppliers", len(d.get("suppliers", [])))
print("materials", len(d.get("materials", [])))
print("products", len(d.get("products", [])))
print("material keys", list(d["materials"][0].keys()))
print("product keys", list(d["products"][0].keys()))
print("product sample", d["products"][0])
cats = Counter(m.get("category") or m.get("category_code") for m in d["materials"])
print("categories", dict(cats))
