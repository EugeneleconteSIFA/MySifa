#!/usr/bin/env python3
"""Génère les PNG favicons pour MyStock, MyExpé, Planning RH.

Usage (depuis la racine du projet) :
    python scripts/generate_module_favicons.py

Dépendance : cairosvg  →  pip install cairosvg
Les fichiers SVG source doivent exister dans static/.
"""
from __future__ import annotations

from pathlib import Path

try:
    import cairosvg
except ImportError:
    raise SystemExit("cairosvg manquant — pip install cairosvg")

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"

MODULES = [
    ("stock_favicon",       180),
    ("stock_favicon",        32),
    ("expe_favicon",        180),
    ("expe_favicon",         32),
    ("planning_rh_favicon", 180),
    ("planning_rh_favicon",  32),
]

for stem, size in MODULES:
    svg_path = STATIC / f"{stem}.svg"
    if not svg_path.exists():
        print(f"  SKIP  {svg_path.name} introuvable")
        continue
    out = STATIC / f"{stem}-{size}.png"
    cairosvg.svg2png(
        url=str(svg_path),
        write_to=str(out),
        output_width=size,
        output_height=size,
    )
    print(f"  OK    {out.name}  ({size}x{size})")

print("Terminé.")
