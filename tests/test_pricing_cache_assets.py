# -*- coding: utf-8 -*-
"""
Empreinte de cache des fichiers statiques du module Coûts matières.

Sans `?v=`, un correctif d'affichage peut être en production sans que personne
ne le voie : le navigateur ressert son fichier en cache. C'est arrivé le
4 août 2026 sur la mise en page du grammage — le correctif était déployé, la
capture d'écran montrait toujours l'ancienne version.

Lancer : python3 tests/test_pricing_cache_assets.py
"""

import ast
import hashlib
import io
import os
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

PAGE = RACINE / "app/web/pricing_page.py"
ECHECS = []


def check(libelle, valeur, attendu):
    ok = valeur == attendu
    if not ok:
        ECHECS.append(libelle)
    print(("ok   " if ok else "KO   ") + libelle.ljust(56) + repr(valeur)
          + ("" if ok else "   attendu " + repr(attendu)))


def empreinte_isolee(assets):
    """
    La fonction du routeur, exécutée seule : le test ne démarre pas
    l'application pour vérifier une empreinte de fichier.
    """
    src = io.open(PAGE, encoding="utf-8").read()
    corps = [
        ast.get_source_segment(src, n)
        for n in ast.parse(src).body
        if isinstance(n, ast.FunctionDef) and n.name == "_empreinte_assets"
    ]
    assert len(corps) == 1, "_empreinte_assets introuvable dans pricing_page.py"
    ns = {
        "hashlib": hashlib,
        "Path": Path,
        "APP_VERSION": "0.0.0",
        "__file__": str(PAGE),
        "_ASSETS_PRICING": assets,
        "_EMPREINTE_CACHE": {},
    }
    exec(corps[0], ns)
    return ns["_empreinte_assets"]


def main():
    page = io.open(PAGE, encoding="utf-8").read()

    print("--- le gabarit demande bien une version ---")
    check("le CSS porte une empreinte",
          'href="/static/pricing_app.css?v=__ASSETS__"' in page, True)
    check("le JS porte une empreinte",
          'src="/static/pricing_app.js?v=__ASSETS__"' in page, True)
    check("le marqueur est bien remplacé",
          '.replace("__ASSETS__", _empreinte_assets())' in page, True)
    check("aucun marqueur oublié", page.count("__ASSETS__"), 3)

    print("\n--- l'empreinte suit les fichiers ---")
    empreinte = empreinte_isolee(("static/pricing_app.css", "static/pricing_app.js"))
    avant = empreinte()
    check("une empreinte courte est produite", 0 < len(avant) <= 12, True)
    check("stable tant que rien ne bouge", empreinte(), avant)

    # On touche le CSS : sans changement d'empreinte, le cache ne lâchera pas.
    css = RACINE / "static/pricing_app.css"
    mtime = css.stat().st_mtime_ns
    try:
        os.utime(css, ns=(mtime + 1_000_000_000, mtime + 1_000_000_000))
        apres = empreinte()
        check("elle change quand le CSS change", apres != avant, True)
        check("et reste stable dans le nouvel état", empreinte(), apres)
    finally:
        # On ne compare pas à l'empreinte de départ : certains montages
        # arrondissent la date à la seconde, la restitution n'est pas exacte.
        os.utime(css, ns=(mtime, mtime))

    print("\n--- fichier illisible ---")
    check("la page ne tombe pas, elle renonce au cache",
          empreinte_isolee(("static/nexiste_pas.css",))(), "0.0.0")

    print("\n" + ("TOUT EST VERT" if not ECHECS else "ECHECS : " + ", ".join(ECHECS)))
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    raise SystemExit(main())
