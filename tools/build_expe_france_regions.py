"""Fabrique `app/web/expe_france_regions.svg` à partir de la carte des départements.

Les contours de région sont l'UNION géométrique des départements du SVG
`expe_france_departments.svg` : aucune deuxième source de vérité, aucun trait
interne, et les deux cartes restent superposables au pixel près.

À relancer uniquement si la carte des départements change — la carte des régions
est un artefact versionné, pas un calcul fait au démarrage de l'application.

    pip install shapely
    python3 tools/build_expe_france_regions.py

Deux pièges du format, tous deux déjà tombés :

* un `m` qui n'est pas le premier du chemin est RELATIF au point courant. Le
  traiter comme absolu envoie les îles à l'origine du repère et creuse un trou
  là où elles auraient dû être ;
* les frontières partagées ne coïncident pas exactement d'un département à
  l'autre. L'union est donc faite sur des tracés dilatés de `EPS`, puis rétractée
  d'autant : sans ça, chaque frontière interne laisse un fil blanc.
"""

from __future__ import annotations

import re
from pathlib import Path

from shapely.geometry import Polygon
from shapely.ops import unary_union

RACINE = Path(__file__).resolve().parents[1]
SRC = RACINE / "app" / "web" / "expe_france_departments.svg"
DEST = RACINE / "app" / "web" / "expe_france_regions.svg"

# Dilatation/rétraction pour souder les frontières partagées, en unités de vue.
EPS = 0.35
# Simplification des tracés : en dessous, le fichier double de taille sans que
# l'œil y gagne quoi que ce soit à l'échelle où la carte est affichée.
SIMPLIFICATION = 0.12
# En dessous de cette aire, un polygone est un résidu de la soudure, pas une île.
AIRE_MINI = 0.8


def _regions() -> dict[str, tuple[str, tuple[str, ...]]]:
    import sys

    sys.path.insert(0, str(RACINE))
    from app.services.expe_regions import REGIONS  # noqa: E402

    return {c: v for c, v in REGIONS.items() if not v[1][0].startswith("97")}


def lire_departements() -> dict[str, str]:
    raw = SRC.read_text(encoding="utf-8")
    blocs = re.findall(r"<path\b(.*?)/>", raw, re.S)
    sortie = {}
    for b in blocs:
        pid = re.search(r'id="([^"]+)"', b).group(1)
        d = re.search(r'\sd="([^"]+)"', b, re.S).group(1)
        sortie[pid] = d
    return sortie


def sous_chemins(d: str) -> list[list[tuple[float, float]]]:
    polys: list[list[tuple[float, float]]] = []
    x = y = 0.0
    depart = (0.0, 0.0)
    for idx, chunk in enumerate(d.split("m")[1:]):
        chunk = chunk.replace("z", "").replace("Z", "").strip()
        pts: list[tuple[float, float]] = []
        for i, tok in enumerate(t for t in re.split(r"\s+", chunk) if t):
            dx, dy = (float(v) for v in tok.split(","))
            if i == 0:
                x, y = (dx, dy) if idx == 0 else (x + dx, y + dy)
                depart = (x, y)
            else:
                x, y = x + dx, y + dy
            pts.append((x, y))
        # 'z' referme le sous-chemin : le point courant revient à son départ.
        x, y = depart
        if len(pts) >= 3:
            polys.append(pts)
    return polys


def geometrie(d: str):
    morceaux = []
    for pts in sous_chemins(d):
        p = Polygon(pts)
        if not p.is_valid:
            p = p.buffer(0)
        if not p.is_empty:
            morceaux.append(p)
    return unary_union(morceaux)


def en_chemin(geom) -> str:
    polys = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
    morceaux = []
    for p in polys:
        if p.area < AIRE_MINI:
            continue
        for anneau in [p.exterior] + list(p.interiors):
            coords = list(anneau.coords)[:-1]
            if len(coords) < 3:
                continue
            morceaux.append(
                "M " + " ".join(f"{round(x, 2):g},{round(y, 2):g}" for x, y in coords) + " Z"
            )
    return " ".join(morceaux)


def main() -> None:
    regions = _regions()
    depts = lire_departements()
    manquants = sorted(
        set(depts) - {d for _, ds in regions.values() for d in ds}
    )
    if manquants:
        raise SystemExit(f"départements sans région : {manquants}")

    geoms = {code: geometrie(d) for code, d in depts.items()}
    lignes = [
        "<svg",
        '\txmlns="http://www.w3.org/2000/svg"',
        '\tviewBox="0 0 613 585"',
        '\taria-label="Map of France regions"',
        ">",
    ]
    for code, (nom, liste) in regions.items():
        fusion = unary_union([geoms[d].buffer(EPS) for d in liste]).buffer(-EPS)
        fusion = fusion.simplify(SIMPLIFICATION, preserve_topology=True)
        lignes += [
            "\t<path",
            f'\t\tid="{code}"',
            f'\t\tdata-region="{code}"',
            f'\t\taria-label="{nom}"',
            f'\t\td="{en_chemin(fusion)}"',
            "\t/>",
        ]
    lignes.append("</svg>")
    DEST.write_text("\n".join(lignes) + "\n", encoding="utf-8", newline="\n")
    print(f"{DEST.relative_to(RACINE)} — {len(regions)} régions, {DEST.stat().st_size} octets")


if __name__ == "__main__":
    main()
