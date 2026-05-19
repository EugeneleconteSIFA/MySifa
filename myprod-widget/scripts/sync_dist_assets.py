#!/usr/bin/env python3
"""Copie les PNG assets/ vers les builds dist/ (app.asar.unpacked/assets).

Utile après `generate_icons.py` sans rebuild complet, ou en complément de electron-builder.
Les installateurs Setup.exe / DMG embarquent le contenu au moment du build — pour la prod,
relancer `npm run build:win` / `build:mac` après sync.
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
DIST = ROOT / "dist"

PNG_NAMES = (
    "icon.png",
    "favicon-16.png",
    "favicon-32.png",
    "trayTemplate.png",
    "trayTemplate@2x.png",
    "trayWin16.png",
    "trayWin32.png",
)


def _targets() -> list[Path]:
    out: list[Path] = []
    win = DIST / "win-unpacked" / "resources" / "app.asar.unpacked" / "assets"
    if (DIST / "win-unpacked").is_dir():
        out.append(win)
    for app in DIST.rglob("MyProd Widget.app"):
        out.append(app / "Contents" / "Resources" / "app.asar.unpacked" / "assets")
    return out


def main() -> None:
    if not ASSETS.is_dir():
        raise SystemExit(f"Missing assets dir: {ASSETS}")

    sources = [ASSETS / name for name in PNG_NAMES if (ASSETS / name).is_file()]
    if not sources:
        raise SystemExit("No PNG files in assets/ — run: python3 scripts/generate_icons.py")

    targets = _targets()
    if not targets:
        print("No dist/ build found — run electron-builder first, or ignore if only refreshing assets/")
        return

    for dest_dir in targets:
        dest_dir.mkdir(parents=True, exist_ok=True)
        for src in sources:
            shutil.copy2(src, dest_dir / src.name)
        # Ancien SVG usine (builds avant waveform) — ne doit plus rester seul dans unpacked
        old_svg = dest_dir / "tray-factory-template.svg"
        if old_svg.is_file():
            old_svg.unlink()
        print(f"Synced {len(sources)} PNG → {dest_dir.relative_to(ROOT)}")

    print("Done. Rebuild Setup.exe / DMG for download links to serve new icons.")


if __name__ == "__main__":
    main()
