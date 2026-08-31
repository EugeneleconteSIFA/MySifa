"""MySifa — /reunions : redirection vers l'onglet Reunions de MyProd.

Les points de production ont ete une page a part entiere le temps de les
construire. Ils sont desormais un sous-onglet de MyProd > Production, au meme
titre que Vue d'ensemble, Saisies ou Retour de prod : meme barre laterale,
meme titre de page, meme rangee de sous-onglets. Le rendu vit dans
`static/mysifa_reunions.js`, monte par `renderReunionsTab()`.

Cette route ne disparait pas pour autant : des liens et des favoris pointent
sur /reunions. Elle mene maintenant au sous-onglet, dont l'ancre est lue au
demarrage par `_readProdHash()`.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()


@router.get("/reunions")
def reunions_page():
    # Le controle d'acces n'est pas perdu : /prod verifie l'acces a MyProd, et
    # les API de reunion filtrent sur ROLES_PROD.
    return RedirectResponse(url="/prod#reunions", status_code=302)
