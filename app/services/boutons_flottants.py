"""Boutons flottants (en bas à droite) : lesquels s'affichent dans quelle appli.

Depuis le 11/10/2026, les boutons communs — messagerie, post-it, assistant IA,
calculette, capture de tableau de bord, tâche rapide — sont injectés par
`main.py` dans toutes les pages connectées de MySifa, au lieu d'être inclus
page par page (plusieurs modules n'en avaient aucun). Le superadmin peut en
couper certains appli par appli : Paramètres › Audit › Widgets et tableaux de
bord, section « Boutons flottants par application ». Le réglage vaut pour tout
le monde.

Deux sortes de boutons :

- **communs** : réglables dans chaque appli ;
- **propres à une appli** (Métrage bobine dans MyStock, Carte de France dans
  MyExpé) : ils dépendent du code de leur page, on peut les couper chez elle
  mais pas les étendre ailleurs. Pour en faire un bouton commun, il faut
  d'abord sortir son code dans un fichier partagé.

Ce module décrit le logiciel, pas l'entreprise : les applis et les boutons
sont ceux de MySifa. Seuls les réglages (table `boutons_flottants_reglages`)
sont des données. Par défaut tout est activé, sauf la bulle de messagerie sur
la page Messagerie elle-même (doublon).

Masquer un bouton = une règle CSS `display:none` sur ses éléments, posée dans
le <head> de la page : le placement du dock (mysifa_dock.js) ignore déjà les
éléments masqués, et aucune page n'a à connaître ce réglage. Les deux boutons
sans icône propre (raccourcis Alt+C et Option+T) lisent en plus
`window.MySifaBoutons.actif(cle)`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Appli:
    code: str
    libelle: str
    chemins: tuple            # préfixes d'adresse (« /stock » couvre /stock/…)


@dataclass(frozen=True)
class Bouton:
    cle: str
    libelle: str
    detail: str
    selecteur: str | None     # éléments à masquer quand le bouton est coupé
    appli: str | None = None  # bouton propre à une appli, sinon commun


# Ordre d'affichage de la grille. Un préfixe plus précis passe avant un plus
# court (« /planning-rh » avant « /planning », « /rh/coffre » avant tout).
APPLIS: tuple[Appli, ...] = (
    Appli("portail", "Accueil", ("/",)),
    Appli("prod", "MyProd", ("/prod",)),
    Appli("fabrication", "Saisie prod", ("/fabrication",)),
    Appli("planning_rh", "Planning RH", ("/planning-rh",)),
    Appli("planning", "Planning machine", ("/planning",)),
    Appli("stock", "MyStock", ("/stock",)),
    Appli("expe", "MyExpé", ("/expe",)),
    Appli("qualite", "MyQualité", ("/qualite",)),
    Appli("maintenance", "Maintenance", ("/maintenance",)),
    Appli("bat", "MyBAT", ("/bat",)),
    Appli("ao", "MyAO", ("/ao",)),
    Appli("pricing", "Coûts matières", ("/pricing",)),
    Appli("compta", "MyCompta", ("/compta",)),
    Appli("paie", "Paie", ("/paie",)),
    Appli("rh_coffre", "Coffre RH", ("/rh/coffre",)),
    Appli("coffre", "Coffres", ("/coffre",)),
    Appli("erp", "ERP RVGI", ("/erp",)),
    Appli("reunions", "Points de production", ("/reunions",)),
    Appli("taches", "Tâches", ("/taches",)),
    Appli("messages", "Messagerie", ("/messages",)),
    Appli("calendrier", "Calendrier", ("/calendrier",)),
    Appli("learning", "Formation", ("/learning",)),
    Appli("profil", "Mon profil", ("/profil",)),
    Appli("settings", "Paramètres", ("/settings",)),
)

# Pages servies sous un préfixe d'appli mais publiques ou sans session.
_HORS_APPLI = ("/calendrier/invitation",)

BOUTONS: tuple[Bouton, ...] = (
    Bouton("messagerie", "Messagerie", "Bulle de discussion",
           "#cw-bubble,#cw-bar,#cw-panel"),
    Bouton("postit", "Post-it", "Bouton et post-its posés sur la page",
           "#postit-dock-root,#postitLayer"),
    Bouton("ia", "Assistant IA", "Réservé aux rôles qui y ont droit",
           "#ai-chat-root"),
    Bouton("calculette", "Calculette", "", "#_calc_fab,#_calc_panel"),
    Bouton("capture", "Capture tableau de bord", "Bouton et raccourci Alt+C",
           "#mysifa-cap-fab"),
    Bouton("tache", "Tâche rapide", "Raccourci Option+T, sans icône", None),
    Bouton("carte_france", "Carte de France (délais)", "", "#expe-carte-fab,#expe-carte-panel",
           appli="expe"),
    Bouton("metrage", "Métrage bobine", "", "#mtr-fab,#mtr-panel", appli="stock"),
)

PAR_CLE = {b.cle: b for b in BOUTONS}
CODES_APPLIS = {a.code for a in APPLIS}

# Coupés tant que personne n'a rien réglé.
DEFAUTS_OFF = {("messages", "messagerie")}


def appli_de_chemin(chemin: str) -> str | None:
    """Code de l'appli d'une adresse, ou None (page publique, API, inconnue)."""
    p = (chemin or "").split("?", 1)[0] or "/"
    if p.startswith("/api/") or p.startswith("/static/"):
        return None
    if any(p == h or p.startswith(h + "/") for h in _HORS_APPLI):
        return None
    if p == "/":
        return "portail"
    for a in APPLIS:
        for c in a.chemins:
            if c != "/" and (p == c or p.startswith(c + "/")):
                return a.code
    return None


def applicable(bouton: Bouton, appli: str) -> bool:
    """Un bouton propre n'existe que dans son appli."""
    return bouton.appli is None or bouton.appli == appli


def est_actif(reglages: dict, appli: str, cle: str) -> bool:
    """`reglages` : {(appli, bouton): bool} lu en base ; le défaut sinon."""
    if (appli, cle) in reglages:
        return bool(reglages[(appli, cle)])
    return (appli, cle) not in DEFAUTS_OFF


def coupes(reglages: dict, appli: str) -> list[str]:
    """Boutons coupés dans cette appli (seulement ceux qui y existent)."""
    return [b.cle for b in BOUTONS
            if applicable(b, appli) and not est_actif(reglages, appli, b.cle)]


def tete_de_page(reglages: dict, appli: str) -> str:
    """Ce que main.py pose dans le <head> : le réglage et le CSS de masquage.

    Posé dans le <head> pour que les scripts de la page le trouvent avant de
    s'exécuter. Les données viennent du code ou de clés validées : rien
    d'utilisateur n'est interpolé.
    """
    off = coupes(reglages, appli)
    conf = json.dumps({"appli": appli, "off": off}, ensure_ascii=True)
    h = ("<script>window.__MYSIFA_BOUTONS__=%s;window.MySifaBoutons={actif:function(k){"
         "return (window.__MYSIFA_BOUTONS__.off||[]).indexOf(k)<0;}};</script>" % conf)
    sels = [PAR_CLE[k].selecteur for k in off if PAR_CLE[k].selecteur]
    if sels:
        h += '<style id="mysifa-boutons-off">%s{display:none!important}</style>' % ",".join(sels)
    return h


def grille(reglages: dict) -> dict:
    """La grille de Paramètres : applis en colonnes, boutons en lignes."""
    return {
        "applis": [{"code": a.code, "libelle": a.libelle} for a in APPLIS],
        "boutons": [{
            "cle": b.cle, "libelle": b.libelle, "detail": b.detail,
            "propre": b.appli,
            "propre_libelle": next((a.libelle for a in APPLIS if a.code == b.appli), None),
            "etats": {a.code: (est_actif(reglages, a.code, b.cle) if applicable(b, a.code) else None)
                      for a in APPLIS},
        } for b in BOUTONS],
    }


def valider(appli: str, cle: str) -> None:
    """Lève ValueError (message affichable) sur un couple invalide."""
    if appli not in CODES_APPLIS:
        raise ValueError("Application inconnue.")
    b = PAR_CLE.get(cle)
    if not b:
        raise ValueError("Bouton inconnu.")
    if not applicable(b, appli):
        raise ValueError("Ce bouton est propre à une autre application.")


# ── Lecture en base, avec un petit cache ────────────────────────────────────
# Chaque page HTML connectée lit ce réglage : on le garde 30 secondes, et une
# écriture depuis Paramètres le vide aussitôt (même processus).

_CACHE = {"t": 0.0, "val": None}
_TTL = 30.0


def lire_reglages(conn) -> dict:
    try:
        rows = conn.execute(
            "SELECT appli, bouton, actif FROM boutons_flottants_reglages").fetchall()
    except Exception:
        return {}
    return {(r[0], r[1]): bool(r[2]) for r in rows}


def reglages_en_cache(get_db) -> dict:
    import time
    now = time.monotonic()
    if _CACHE["val"] is not None and now - _CACHE["t"] < _TTL:
        return _CACHE["val"]
    try:
        with get_db() as conn:
            val = lire_reglages(conn)
    except Exception:
        val = {}
    _CACHE.update(t=now, val=val)
    return val


def vider_cache() -> None:
    _CACHE.update(t=0.0, val=None)
