"""Carte SVG départements France (inline) — Victor Cazanave / svg-maps, CC-BY-4.0."""
from pathlib import Path

_SVG_PATH = Path(__file__).resolve().parent / "expe_france_departments.svg"

_DOM_PATHS = """
<g id="expe-dom-tom" transform="translate(455, 548)">
  <text x="0" y="-6" font-size="9" fill="var(--muted)" font-family="system-ui,sans-serif">DOM-TOM</text>
  <rect id="971" data-dept="971" x="0" y="4" width="34" height="20" rx="3" fill="var(--card)" stroke="var(--border)" stroke-width="1.2"/>
  <text x="17" y="17" text-anchor="middle" font-size="7" fill="var(--text2)" pointer-events="none">971</text>
  <rect id="972" data-dept="972" x="38" y="4" width="34" height="20" rx="3" fill="var(--card)" stroke="var(--border)" stroke-width="1.2"/>
  <text x="55" y="17" text-anchor="middle" font-size="7" fill="var(--text2)" pointer-events="none">972</text>
  <rect id="973" data-dept="973" x="76" y="4" width="34" height="20" rx="3" fill="var(--card)" stroke="var(--border)" stroke-width="1.2"/>
  <text x="93" y="17" text-anchor="middle" font-size="7" fill="var(--text2)" pointer-events="none">973</text>
  <rect id="974" data-dept="974" x="0" y="28" width="34" height="20" rx="3" fill="var(--card)" stroke="var(--border)" stroke-width="1.2"/>
  <text x="17" y="41" text-anchor="middle" font-size="7" fill="var(--text2)" pointer-events="none">974</text>
  <rect id="976" data-dept="976" x="38" y="28" width="34" height="20" rx="3" fill="var(--card)" stroke="var(--border)" stroke-width="1.2"/>
  <text x="55" y="41" text-anchor="middle" font-size="7" fill="var(--text2)" pointer-events="none">976</text>
</g>
"""


def _load_svg_inner() -> str:
    raw = _SVG_PATH.read_text(encoding="utf-8")
    start = raw.find(">", raw.find("<svg")) + 1
    end = raw.rfind("</svg>")
    inner = raw[start:end].strip() if end > start else raw
    return inner


def build_expe_france_svg_markup() -> str:
    inner = _load_svg_inner()
    return (
        '<svg class="expe-carte-svg" xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 613 600" aria-label="Carte des départements français" role="img">'
        + inner
        + _DOM_PATHS
        + "</svg>"
    )


EXPE_FRANCE_SVG_MARKUP = build_expe_france_svg_markup()
