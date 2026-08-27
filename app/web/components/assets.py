# -*- coding: utf-8 -*-
"""
Reference d'un asset statique, versionnee automatiquement.

Le cache des assets est regle a deux endroits, et il faut connaitre les deux :

1. `main.py` sert le JS et le CSS en `no-cache` : le navigateur revalide, et
   StaticFiles repond 304 tant que le fichier n'a pas change. C'est le filet de
   securite — il rend impossible le scenario "JS perime pendant 24 h", quel que
   soit ce qui est ecrit dans les balises.

2. `asset()` ci-dessous ajoute `?v=APP_VERSION` a l'URL. C'est l'optimisation :
   une URL qui change a chaque version permet au navigateur de garder le fichier
   sans meme revalider. A utiliser pour tout nouveau code.

Les deux se completent : (1) garantit la fraicheur meme si on oublie (2), et (2)
evite l'aller-retour conditionnel quand on y pense.

    from app.web.components import asset

    f'<script src="{asset("/static/mysifa_dock.js")}"></script>'
    # -> /static/mysifa_dock.js?v=3.0.1

Ne JAMAIS revenir aux compteurs manuels (`?v=4`, `?v=11`) : sur 485 balises, 110
en portaient un, et rien ne signalait les 375 autres.
"""

from config import APP_VERSION


def asset(chemin: str) -> str:
    """Ajoute la version de l'application a l'URL d'un asset statique.

    Une URL qui porte deja un querystring est laissee telle quelle : c'est soit
    un compteur manuel historique, soit un parametre voulu.
    """
    if not chemin.startswith("/static/"):
        return chemin
    if "?" in chemin:
        return chemin
    return "%s?v=%s" % (chemin, APP_VERSION)
