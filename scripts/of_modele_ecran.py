"""
Prépare l'OF à l'écran à partir du modèle vierge `data/of_template.pdf`.

Produit deux fichiers que l'application lit telle quelle :

- `data/of_modele.png` : le modèle en image, fond de la feuille corrigée à
  l'écran (fenêtre OF de MyProd, au-delà de 900 px) ;
- `data/of_modele_cadres.json` : les cadres du modèle, relevés sur ses traits
  noirs et sur ses cases blanches et colorées. Chaque saisie de l'écran s'y
  cale (`of_pdf_generator.cases_du_modele`), et un cadre vide qu'aucun champ
  n'occupe devient une case libre, imprimée telle quelle.

À relancer seulement quand le modèle PDF change :

    .venv-ci/bin/python scripts/of_modele_ecran.py

Dépendances : pdfplumber et pypdfium2 (celui de pdfplumber).
"""
import json
import os
import sys

import pdfplumber
import pypdfium2

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELE = os.path.join(RACINE, "data", "of_template.pdf")
IMAGE = os.path.join(RACINE, "data", "of_modele.png")
CADRES = os.path.join(RACINE, "data", "of_modele_cadres.json")


def _couleur(r):
    c = r.get("non_stroking_color")
    return tuple(c) if isinstance(c, (list, tuple)) else (c,)


def _trait(r):
    """Un trait du cadre : noir, ou le gris des pointillés."""
    c = [float(x or 0) for x in _couleur(r)]
    return all(abs(x) < 0.05 for x in c) or all(abs(x - 0.63) < 0.05 for x in c)


def relever(page):
    hor = [(r["x0"], r["x1"], (r["top"] + r["bottom"]) / 2) for r in page.rects
           if _trait(r) and r["height"] <= 2.6 and r["width"] > 3]
    ver = [(r["top"], r["bottom"], (r["x0"] + r["x1"]) / 2) for r in page.rects
           if _trait(r) and r["width"] <= 2.6 and r["height"] > 3]
    mots = page.extract_words()

    def cellule(x, y):
        t = [h[2] for h in hor if h[0] - 1 <= x <= h[1] + 1 and h[2] < y]
        b = [h[2] for h in hor if h[0] - 1 <= x <= h[1] + 1 and h[2] > y]
        g = [v[2] for v in ver if v[0] - 1 <= y <= v[1] + 1 and v[2] < x]
        d = [v[2] for v in ver if v[0] - 1 <= y <= v[1] + 1 and v[2] > x]
        if not (t and b and g and d):
            return None
        return (max(g), max(t), min(d), min(b))

    def vide(c):
        return not any(m["x0"] < c[2] - 1 and m["x1"] > c[0] + 1 and
                       m["top"] < c[3] - 1 and m["bottom"] > c[1] + 1 for m in mots)

    def ferme(c):
        """Les quatre côtés sont tracés sur presque toute leur longueur : un
        vide entre deux cadres voisins n'est pas un cadre."""
        def couvert(segments, a, b):
            total = sum(max(0.0, min(s1, b) - max(s0, a)) for s0, s1 in segments)
            return total >= 0.8 * (b - a)
        haut = [(h[0], h[1]) for h in hor if abs(h[2] - c[1]) < 1.2]
        bas = [(h[0], h[1]) for h in hor if abs(h[2] - c[3]) < 1.2]
        gauche = [(v[0], v[1]) for v in ver if abs(v[2] - c[0]) < 1.2]
        droite = [(v[0], v[1]) for v in ver if abs(v[2] - c[2]) < 1.2]
        return (couvert(haut, c[0], c[2]) and couvert(bas, c[0], c[2]) and
                couvert(gauche, c[1], c[3]) and couvert(droite, c[1], c[3]))

    cadres = set()
    y = 20.0
    while y < 830:
        x = 18.0
        while x < 580:
            c = cellule(x, y)
            if c and 12 <= c[2] - c[0] <= 360 and 9 <= c[3] - c[1] <= 45:
                cadres.add(tuple(round(v, 1) for v in c))
            x += 3
        y += 3
    sortie = [{"x0": c[0], "y0": c[1], "x1": c[2], "y1": c[3], "type": "cadre", "vide": vide(c),
               "ferme": ferme(c)}
              for c in sorted(cadres, key=lambda c: (c[1], c[0]))]
    # Cases blanches posées sur un aplat (plieuse, Serame), cases colorées
    # (adhésif en orange, consommation en vert) : elles n'ont pas de trait.
    for r in page.rects:
        c = [round(float(x or 0), 2) for x in _couleur(r)]
        if _trait(r) or not (7 <= r["width"] <= 360 and 7 <= r["height"] <= 45):
            continue
        blanc = c == [1.0, 1.0, 1.0]
        box = (round(r["x0"], 1), round(r["top"], 1), round(r["x1"], 1), round(r["bottom"], 1))
        sortie.append({"x0": box[0], "y0": box[1], "x1": box[2], "y1": box[3],
                       "type": "blanc" if blanc else "aplat", "vide": vide(box), "ferme": blanc})
    return sortie


def main():
    pdf = pdfplumber.open(MODELE)
    cadres = relever(pdf.pages[0])
    with open(CADRES, "w", encoding="utf-8") as f:
        json.dump({"modele": "of_template.pdf", "cadres": cadres}, f, ensure_ascii=False, indent=0)
    image = pypdfium2.PdfDocument(MODELE)[0].render(scale=2.4).to_pil().convert("RGB")
    image.quantize(colors=64, dither=0).save(IMAGE, optimize=True)
    print("%d cadres relevés, image %dx%d." % (len(cadres), image.width, image.height))


if __name__ == "__main__":
    sys.exit(main())
