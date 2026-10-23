"""La base produits de MyStock, enrichie par les articles de RVGI.

`produits` a été chargée une fois, le 14/04/2026, depuis un export de l'ERP.
Rien ne l'a tenue à jour depuis : une référence créée dans RVGI après cette
date — 601/0168 chez Roquette, et des centaines d'autres — est commandée,
produite et livrée sans exister dans MyStock. Ce module comble l'écart à
chaque import du miroir, comme `rvgi_tiers` le fait pour les clients et les
fournisseurs.

Ce que le module fait
---------------------
1. **Lire** les articles de `fic_art` qui ont déjà été commandés au moins une
   fois (`cde_ligne`, entête vivante). Une fiche jamais commandée est un devis
   mort ou un doublon « XXX » : elle n'a rien à faire dans le stock. Un
   produit déjà créé ne disparaît pas pour autant s'il n'est plus commandé.
2. **Lier** chaque produit MyStock existant à son article (`rvgi_article`).
3. **Créer** ceux qui manquent, avec le libellé de l'ERP.

Ce qu'il ne fait jamais
-----------------------
Il ne réécrit ni la désignation ni l'unité d'un produit qui existe déjà
(décision d'Eugène, 23/10/2026) : ce que MyStock a saisi prime. Il ne change
pas le type d'un produit — une référence connue comme fabriquée et annoncée
en négoce par l'ERP est comptée en conflit, pas convertie. Et il ne supprime
rien : un article sorti de RVGI garde son produit et son stock.

Deux natures d'article
----------------------
- `code1` numérique : article fabriqué, référence `code1/code2` (« 601/0168 »).
- `code1 = TT` : négoce. MyStock le range sous `code2` seul
  (« FR110X450_S2021 ») — c'est ainsi que les 27 produits de négoce existants
  ont été saisis.
Tout le reste (`FR/` frais, `FA/`, `DI/`…) n'est pas un produit.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

CODE1_NEGOCE = "TT"
UNITE_FABRIQUE = "étiquette"
UNITE_NEGOCE = "rouleau"

# Au-delà, le bilan devient illisible dans le journal de synchro.
MAX_CONFLITS_RAPPORTES = 30


def _maintenant() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _txt(v: Any) -> str:
    """« Frais de changement de           clichés » : RVGI aligne au blanc."""
    return re.sub(r"\s+", " ", str(v or "")).strip()


def designation(art: Dict[str, Any]) -> str:
    """Les trois premiers libellés de l'article, séparés comme à l'import d'avril.

    `libc4` (le carton) est laissé de côté : les 1 571 produits existants ont
    été chargés sans lui, et deux formats côte à côte dans la même liste
    feraient croire à deux sortes de produits.
    """
    return " | ".join(p for p in (_txt(art.get("libc1")), _txt(art.get("libc2")),
                                  _txt(art.get("libc3"))) if p)


def nature(code1: Any) -> Optional[str]:
    c1 = _txt(code1).upper()
    if not c1:
        return None
    if c1 == CODE1_NEGOCE:
        return "negoce"
    if c1.isdigit():
        return "fabrique"
    return None


def references(code1: Any, code2: Any) -> Tuple[Optional[str], List[str]]:
    """(référence à créer, formes sous lesquelles MyStock a pu la saisir).

    La forme canonique passe par `_erp_reference`, la même que le reste de
    l'application pour joindre une ligne ERP à un produit. La forme brute
    reste reconnue : « 112/12 » a été saisi tel quel, et le recréer en
    « 112/0012 » ferait un doublon.
    """
    from app.routers.reconciliation import _erp_reference

    nat = nature(code1)
    c2 = _txt(code2)
    if not nat or not c2:
        return None, []
    if nat == "negoce":
        ref = c2.upper()
        return ref, [ref]
    canon = (_erp_reference(_txt(code1), c2) or "").upper()
    brut = ("%s/%s" % (_txt(code1), c2)).upper()
    formes = [canon] + ([brut] if brut != canon else [])
    return canon or None, formes


def lire_articles(erp: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Articles fabriqués et de négoce déjà commandés au moins une fois."""
    lignes = erp.execute(
        """
        SELECT a.code1, a.code2, a.libc1, a.libc2, a.libc3
          FROM fic_art a
         WHERE a.corbeille = 0
           AND EXISTS (
                 SELECT 1 FROM cde_ligne l
                   JOIN cde_entete e ON e.numero = l.numero AND e.corbeille = 0
                  WHERE l.corbeille = 0
                    AND l.code1 = a.code1 AND l.code2 = a.code2)
        """
    ).fetchall()
    return [dict(r) for r in lignes if nature(r["code1"])]


def synchroniser(conn: sqlite3.Connection, erp: sqlite3.Connection) -> Dict[str, Any]:
    """Lier, puis créer. N'écrit que dans `produits`, ne valide pas (`commit`)."""
    maintenant = _maintenant()
    existants: Dict[str, Dict[str, Any]] = {}
    for r in conn.execute(
        "SELECT id, reference, type, rvgi_article FROM produits"
    ).fetchall():
        existants[_txt(r["reference"]).upper()] = dict(r)

    crees = lies = deja_lies = nb_conflits = 0
    conflits: List[Dict[str, str]] = []
    vus: List[Tuple[str, int]] = []

    for art in lire_articles(erp):
        ref, formes = references(art["code1"], art["code2"])
        if not ref:
            continue
        nat = nature(art["code1"])
        article = "%s/%s" % (_txt(art["code1"]).upper(), _txt(art["code2"]))

        trouve = next((existants[f] for f in formes if f in existants), None)
        if trouve:
            if (trouve.get("type") or "fabrique") != nat:
                nb_conflits += 1
                if len(conflits) < MAX_CONFLITS_RAPPORTES:
                    conflits.append({"reference": trouve["reference"],
                                     "mystock": trouve.get("type") or "fabrique",
                                     "rvgi": nat})
                continue
            if trouve.get("rvgi_article") == article:
                deja_lies += 1
                vus.append((maintenant, trouve["id"]))
                continue
            conn.execute(
                "UPDATE produits SET rvgi_article=?, rvgi_vu_le=? WHERE id=?",
                (article, maintenant, trouve["id"]))
            trouve["rvgi_article"] = article
            lies += 1
            continue

        des = designation(art) or ref
        unite = UNITE_NEGOCE if nat == "negoce" else UNITE_FABRIQUE
        try:
            cur = conn.execute(
                "INSERT INTO produits (reference, designation, description, unite, type, "
                "created_at, updated_at, rvgi_article, rvgi_cree_le, rvgi_vu_le) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (ref, des, "", unite, nat, maintenant, maintenant,
                 article, maintenant, maintenant))
        except sqlite3.IntegrityError:
            # Deux articles RVGI qui tombent sur la même référence MyStock :
            # le premier l'a prise, le second est déjà représenté.
            continue
        existants[ref] = {"id": cur.lastrowid, "reference": ref, "type": nat,
                          "rvgi_article": article}
        crees += 1

    if vus:
        conn.executemany("UPDATE produits SET rvgi_vu_le=? WHERE id=?", vus)

    return {
        "crees": crees,
        "lies": lies,
        "deja_lies": deja_lies,
        "nb_conflits": nb_conflits,
        "conflits": conflits,
    }
