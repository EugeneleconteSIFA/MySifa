"""Génère les PNG favicons/touch-icons pour MyStock, MyExpé, Planning RH."""
import cairosvg
from pathlib import Path

OUT = Path("/sessions/quirky-lucid-thompson/mnt/outputs")

MODULES = {
    "stock": {
        "label": "MyStock",
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect width="512" height="512" rx="112" fill="#0a0e17"/>
  <g transform="translate(144,48) scale(9.333)" stroke="#22d3ee" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
    <line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/>
    <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
    <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
    <line x1="12" y1="22.08" x2="12" y2="12"/>
  </g>
  <text x="256" y="472" text-anchor="middle" font-family="Segoe UI, system-ui, sans-serif" font-size="144" font-weight="800" fill="#22d3ee">MyS</text>
</svg>"""
    },
    "expe": {
        "label": "MyExpé",
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect width="512" height="512" rx="112" fill="#0a0e17"/>
  <g transform="translate(144,48) scale(9.333)" stroke="#22d3ee" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
    <path d="M3 7h11v10H3z"/>
    <path d="M14 10h4l3 3v4h-7z"/>
    <circle cx="7.5" cy="17" r="2"/>
    <circle cx="17.5" cy="17" r="2"/>
  </g>
  <text x="256" y="472" text-anchor="middle" font-family="Segoe UI, system-ui, sans-serif" font-size="144" font-weight="800" fill="#22d3ee">MyS</text>
</svg>"""
    },
    "planning_rh": {
        "label": "Planning RH",
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect width="512" height="512" rx="112" fill="#0a0e17"/>
  <g transform="translate(144,48) scale(9.333)" stroke="#22d3ee" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </g>
  <text x="256" y="472" text-anchor="middle" font-family="Segoe UI, system-ui, sans-serif" font-size="144" font-weight="800" fill="#22d3ee">MyS</text>
</svg>"""
    },
}

for key, mod in MODULES.items():
    svg_bytes = mod["svg"].encode("utf-8")
    # 180x180 pour apple-touch-icon
    cairosvg.svg2png(bytestring=svg_bytes, write_to=str(OUT / f"{key}_favicon-180.png"), output_width=180, output_height=180)
    # 32x32 pour favicon navigateur
    cairosvg.svg2png(bytestring=svg_bytes, write_to=str(OUT / f"{key}_favicon-32.png"), output_width=32, output_height=32)
    print(f"✓ {key}: 180px + 32px")

print("Done.")
