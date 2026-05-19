#!/usr/bin/env python3
"""Génère les PNG icônes MyProd Widget (waveform activité + couleurs MySifa)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
STATIC_DIRS = [ROOT.parent / "static", ROOT.parent / "app" / "static"]

ACCENT = (34, 211, 238)   # #22d3ee
BG     = (10, 14, 23)     # #0a0e17
BLACK  = (0, 0, 0)


def _draw_waveform(
    draw: ImageDraw.ImageDraw,
    size: int,
    color: tuple[int, int, int],
    *,
    pad: float = 0.10,
) -> None:
    """
    Waveform (activité / signal vital) — polyline en dents de scie.
    Correspond exactement au SVG <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    normalisé sur un viewBox 24x24, mis à l'échelle dans size×size.
    """
    m = size * pad
    w = size - 2 * m

    # Points normalisés sur viewBox 24×24
    raw = [
        (0,  12),
        (6,  12),
        (9,   3),
        (15, 21),
        (18, 12),
        (24, 12),
    ]

    def tx(px: float, py: float) -> tuple[float, float]:
        return (m + px / 24 * w, m + py / 24 * w)

    pts = [tx(px, py) for px, py in raw]
    lw = max(1, round(size * 0.09))   # épaisseur relative à la taille
    draw.line(pts, fill=color + (255,), width=lw, joint="curve")


def _rounded_app_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r = int(size * 0.18)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=r, fill=BG + (255,))
    _draw_waveform(draw, size, ACCENT, pad=0.18)
    return img


def _tray_template(size: int) -> Image.Image:
    """macOS : template image noire sur fond transparent."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    _draw_waveform(draw, size, BLACK, pad=0.08)
    return img


def _tray_colored(size: int) -> Image.Image:
    """Windows : waveform accent sur fond transparent."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    _draw_waveform(draw, size, ACCENT, pad=0.08)
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

    _write_png(ASSETS / "icon.png",            _rounded_app_icon(512))
    _write_png(ASSETS / "trayTemplate.png",    _tray_template(18))
    _write_png(ASSETS / "trayTemplate@2x.png", _tray_template(36))
    _write_png(ASSETS / "trayWin16.png",        _tray_colored(16))
    _write_png(ASSETS / "trayWin32.png",        _tray_colored(32))

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
