#!/usr/bin/env python3
"""Génère les PNG icônes MyProd Widget (usine + couleurs MySifa)."""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
STATIC_DIRS = [ROOT.parent / "static", ROOT.parent / "app" / "static"]

ACCENT = (34, 211, 238)       # #22d3ee
BG = (10, 14, 23)             # #0a0e17
BLACK = (0, 0, 0)

# Paths from assets/tray-factory-template.svg (viewBox 0 0 64 64)
FACTORY_PATHS = [
    "M10 54V28l12-10v-6h6v6l4 3V12h6v14l16 13v15H10Z",
    "M16 48h32V41H16v7Z",
    "M16 35h32v-6.3L32 20.6 16 28.7V35Z",
    "M22 46h4v6h-4v-6Z",
    "M30 46h4v6h-4v-6Z",
    "M38 46h4v6h-4v-6Z",
]


def _tokenize_path(d: str) -> list[str]:
    return re.findall(
        r"[MmLlHhVvZz]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?",
        d.replace(",", " "),
    )


def _path_to_points(d: str) -> list[tuple[float, float]]:
    tokens = _tokenize_path(d)
    pts: list[tuple[float, float]] = []
    i = 0
    x = y = 0.0
    start = (0.0, 0.0)

    def read() -> float:
        nonlocal i
        v = float(tokens[i])
        i += 1
        return v

    while i < len(tokens):
        cmd = tokens[i]
        i += 1
        rel = cmd.islower()
        c = cmd.upper()

        if c == "M":
            x, y = read(), read()
            start = (x, y)
            pts.append((x, y))
            while i < len(tokens) and tokens[i] not in "MmLlHhVvZz":
                x, y = read(), read()
                pts.append((x, y))
        elif c == "L":
            while i < len(tokens) and tokens[i] not in "MmLlHhVvZz":
                nx, ny = read(), read()
                if rel:
                    nx += x
                    ny += y
                x, y = nx, ny
                pts.append((x, y))
        elif c == "H":
            while i < len(tokens) and tokens[i] not in "MmLlHhVvZz":
                nx = read()
                if rel:
                    nx += x
                x = nx
                pts.append((x, y))
        elif c == "V":
            while i < len(tokens) and tokens[i] not in "MmLlHhVvZz":
                ny = read()
                if rel:
                    ny += y
                y = ny
                pts.append((x, y))
        elif c == "Z":
            pts.append(start)
            x, y = start
    return pts


def _draw_factory(
    draw: ImageDraw.ImageDraw,
    size: int,
    color: tuple[int, int, int],
    *,
    pad: float = 0.12,
) -> None:
    margin = size * pad
    scale = (size - 2 * margin) / 64.0
    ox = margin
    oy = margin

    def tx(p: tuple[float, float]) -> tuple[float, float]:
        return (ox + p[0] * scale, oy + p[1] * scale)

    for d in FACTORY_PATHS:
        poly = [tx(p) for p in _path_to_points(d)]
        if len(poly) >= 3:
            draw.polygon(poly, fill=color)


def _rounded_app_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r = int(size * 0.18)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=r, fill=BG + (255,))
    _draw_factory(draw, size, ACCENT, pad=0.16)
    return img


def _tray_template(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    _draw_factory(draw, size, BLACK, pad=0.1)
    return img


def _tray_colored(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    _draw_factory(draw, size, ACCENT, pad=0.1)
    return img


def _write_png(path: Path, img: Image.Image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)


def _write_ico(path: Path, sizes: list[int]) -> None:
    images = [_rounded_app_icon(s) for s in sizes]
    path.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(
        path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    for d in STATIC_DIRS:
        d.mkdir(parents=True, exist_ok=True)

    _write_png(ASSETS / "icon.png", _rounded_app_icon(512))
    _write_png(ASSETS / "trayTemplate.png", _tray_template(18))
    _write_png(ASSETS / "trayTemplate@2x.png", _tray_template(36))
    _write_png(ASSETS / "trayWin16.png", _tray_colored(16))
    _write_png(ASSETS / "trayWin32.png", _tray_colored(32))

    for name, size in (("favicon-16.png", 16), ("favicon-32.png", 32)):
        img = _rounded_app_icon(size)
        _write_png(ASSETS / name, img)
        for d in STATIC_DIRS:
            _write_png(d / f"widget-{name}", img)

    for d in STATIC_DIRS:
        _write_ico(d / "widget-favicon.ico", [16, 32, 48])

    print("Icons generated in", ASSETS)
    print("Widget favicons copied to", ", ".join(str(d) for d in STATIC_DIRS))


if __name__ == "__main__":
    main()
