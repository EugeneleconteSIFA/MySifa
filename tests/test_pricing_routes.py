# -*- coding: utf-8 -*-
"""
Toute route cliente du module Coûts matières doit exister côté serveur.

Le routage se fait dans le navigateur (`parseRoute` dans pricing_app.js) : tant
qu'on navigue dans l'application, le serveur n'est jamais sollicité. Un
rechargement forcé, un favori ou un lien collé dans la barre d'adresse, eux,
tapent bien sur FastAPI — et une URL sans route déclarée renvoie un
`{"detail":"Not Found"}` sur fond noir, sans le moindre indice.

C'est arrivé le 6 août 2026 sur `/pricing/mystock/90` : la fiche s'ouvrait très
bien au clic, et disparaissait au premier F5.

Lancer : python3 tests/test_pricing_routes.py
"""

import io
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
PAGE = RACINE / "app/web/pricing_page.py"
APP = RACINE / "static/pricing_app.js"

ECHECS = []


def check(libelle, valeur, attendu):
    ok = valeur == attendu
    if not ok:
        ECHECS.append(libelle)
    print(("ok   " if ok else "KO   ") + libelle.ljust(52) + repr(valeur)
          + ("" if ok else "   attendu " + repr(attendu)))


def routes_declarees(src):
    """Les chemins des décorateurs @router.get, dans l'ordre du fichier."""
    return re.findall(r'@router\.get\(\s*"([^"]+)"', src)


def compile_motif(chemin):
    """`/pricing/materials/{id}` → expression qui accepte un segment."""
    motif = re.sub(r"\{[^}]+\}", "[^/]+", re.escape(chemin).replace(r"\{", "{").replace(r"\}", "}"))
    return re.compile("^" + motif + "$")


def premiere_route(routes, url):
    """
    FastAPI retient la PREMIÈRE route qui correspond : on reproduit ce
    comportement, sinon un test passerait alors que `{id}` avale « produit ».
    """
    for chemin in routes:
        if compile_motif(chemin).match(url):
            return chemin
    return None


def main():
    page = io.open(PAGE, encoding="utf-8").read()
    app = io.open(APP, encoding="utf-8").read()
    routes = routes_declarees(page)

    # Les URL que `parseRoute` sait produire, telles qu'un utilisateur peut les
    # recharger. Le libellé reprend le nom de vue côté client.
    attendues = [
        ("materials (racine)", "/pricing"),
        ("materials", "/pricing/materials"),
        ("material-new", "/pricing/materials/new"),
        ("material-edit", "/pricing/materials/7"),
        ("products", "/pricing/products"),
        ("product-new", "/pricing/products/new"),
        ("product-edit", "/pricing/products/7"),
        ("mystock (liste)", "/pricing/mystock"),
        ("mystock-edit", "/pricing/mystock/90"),
        ("msproduct-new", "/pricing/mystock/produit/new"),
        ("msproduct-edit", "/pricing/mystock/produit/12"),
        ("fournisseurs (liste)", "/pricing/fournisseurs"),
        ("fournisseur-edit", "/pricing/fournisseurs/3"),
        ("settings", "/pricing/settings"),
    ]

    print("--- chaque URL rechargeable a sa route serveur ---")
    for nom, url in attendues:
        check("F5 sur " + nom, premiere_route(routes, url) is not None, True)

    print("\n--- l'ordre de déclaration ne piège personne ---")
    # `/pricing/mystock/produit/...` doit être capté par la route produit, pas
    # par `/pricing/mystock/{declinaison_id}`.
    check("produit/new n'est pas avalé par {declinaison_id}",
          premiere_route(routes, "/pricing/mystock/produit/new"),
          "/pricing/mystock/produit/new")
    check("produit/12 n'est pas avalé par {declinaison_id}",
          premiere_route(routes, "/pricing/mystock/produit/12"),
          "/pricing/mystock/produit/{produit_id}")
    check("materials/new n'est pas avalé par {material_id}",
          premiere_route(routes, "/pricing/materials/new"),
          "/pricing/materials/new")

    print("\n--- un identifiant qui n'en est pas un ne tombe pas en 404 ---")
    for nom in ("pricing_material_edit", "pricing_product_edit",
                "pricing_mystock_produit_edit", "pricing_mystock_declinaison",
                "pricing_fournisseur_tarif"):
        corps = page[page.index("def " + nom + "("):]
        corps = corps[:corps.index("\n\n\n")] if "\n\n\n" in corps else corps
        check(nom + " renvoie vers la liste",
              "RedirectResponse" in corps and r'r"\d+"' in corps, True)

    print("\n--- le client ne fabrique pas d'URL inconnue du serveur ---")
    # Filet complémentaire : tout `navigate("/pricing…")` du JS doit trouver une
    # route. Un chemin qui finit par « / » est un préfixe concaténé à un
    # identifiant (`navigate("/pricing/materials/" + id)`) : on remet un segment
    # pour retrouver l'URL réellement demandée.
    for litteral in sorted(set(re.findall(r'navigate\("(/pricing[^"]*)"', app))):
        url = litteral + "1" if litteral.endswith("/") else litteral
        check("navigate " + litteral, premiere_route(routes, url) is not None, True)

    print("\n" + ("TOUT EST VERT" if not ECHECS else "ECHECS : " + ", ".join(ECHECS)))
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    raise SystemExit(main())
