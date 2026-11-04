"""Prix d'achat RVGI des produits finis sous-traités.

Un produit fini fabriqué chez SIFA tire son prix de valorisation des commandes
clients (import de la feuille « Valorisation »). Un produit SOUS-TRAITÉ n'a pas
de prix de revient dans les commandes : ce qu'il coûte est sur la commande
d'achat au sous-traitant (`cdf_ligne` du miroir RVGI). Exemple : 1004/0128,
acheté au rouleau et en dollars à un fournisseur chinois.

Ce module rend, par référence produit (« code1/code2 »), le prix de la
dernière commande d'achat ramené à l'unité de la valorisation :

- au mille pour un produit compté en étiquettes ;
- à l'unité sinon, seulement si l'achat est lui-même à l'unité.

Conversions :
- l'unité d'achat se lit dans `fic_ua` (`nombre` = quantité contenue : 1000
  pour « Mille », 100 pour « Cent ») ;
- un achat au rouleau ou à la bobine se convertit avec le nombre d'étiquettes
  par rouleau, que RVGI ne porte qu'en texte libre (« Box: 15 rolls of 2000
  labels ») sur la fiche d'achat ou la ligne de commande ;
- les dollars passent en euros au taux de Coûts matières (`eur_usd_rate`).

Ce qui ne se convertit pas sans deviner (unité inconnue, rouleau sans nombre
d'étiquettes, devise sans taux) est laissé de côté : un prix faux est pire
qu'un « sans prix », qui se voit.

Lecture seule sur le miroir. Résultat gardé en mémoire tant que le miroir ne
change pas (empreinte du fichier, comme `encres_rvgi`).
"""

import logging
import os
import re
from typing import Optional

from app.services import erp_mirror as miroir

logger = logging.getLogger(__name__)

# Devises RVGI : « E » = euro, « DOL » = dollar US.
_DEVISES_EURO = {"E", "EUR", "EURO", ""}
_DEVISES_USD = {"DOL", "USD", "$"}

# Unités d'achat comptées au rouleau / à la bobine : il faut le nombre
# d'étiquettes par rouleau pour revenir à l'étiquette.
_UA_ROULEAU = re.compile(r"roll|rouleau|bobine", re.IGNORECASE)
# Unités d'achat « à l'unité ».
_UA_UNITE = re.compile(r"^unit", re.IGNORECASE)
# Nombre d'étiquettes PAR ROULEAU, seulement accolé au rouleau : une
# désignation dit aussi « spot toutes les 10 étiq. », qu'il ne faut pas lire.
#   « rolls of 2000 labels », « rouleaux de 2 000 étiquettes »
#   « 2000 labels/roll », « 2 000 étiq. par rouleau »
_N = r"(\d[\d\s.,]*\d|\d)"
_ETIQ = r"(?:labels?|[ée]tiquettes?|[ée]tiq\.?)"
_ROUL = r"(?:rolls?|rouleaux?|bobines?)"
_ETIQ_PAR_ROULEAU = (
    re.compile(_ROUL + r"\s*(?:of|de|:)?\s*" + _N + r"\s*" + _ETIQ, re.IGNORECASE),
    re.compile(_N + r"\s*" + _ETIQ + r"\s*(?:/|par|per|by)\s*" + _ROUL, re.IGNORECASE),
)

_CACHE = {"empreinte": None, "achats": None}


def _empreinte():
    chemin = miroir.ERP_MIRROR_DB
    try:
        return tuple(
            (os.stat(f).st_mtime_ns, os.stat(f).st_size)
            for f in (chemin, chemin + "-wal") if os.path.exists(f)
        )
    except OSError:
        return None


def _nombre(txt) -> Optional[float]:
    """« 2 000 » / « 2.000 » / « 2,000 » → 2000. Les séparateurs de milliers
    sont retirés : un nombre d'étiquettes par rouleau n'a pas de décimales."""
    chiffres = re.sub(r"[\s.,]", "", str(txt or ""))
    try:
        v = float(chiffres)
    except ValueError:
        return None
    return v if v > 0 else None


def etiquettes_par_rouleau(*textes) -> Optional[float]:
    for t in textes:
        if not t:
            continue
        for motif in _ETIQ_PAR_ROULEAU:
            m = motif.search(str(t))
            if m:
                n = _nombre(m.group(1))
                if n:
                    return n
    return None


def _lire_achats() -> dict:
    """{« code1/code2 »: dernière ligne d'achat}, brut, depuis le miroir."""
    with miroir.get_erp_db() as c:
        presentes = miroir.tables_presentes(c)
        if not {"cdf_ligne", "cdf_entete"} <= set(presentes):
            return {}
        ua = {}
        if "fic_ua" in presentes:
            for r in c.execute("SELECT code, lib1, nombre FROM fic_ua WHERE corbeille = 0"):
                ua[str(r["code"] or "").strip()] = (str(r["lib1"] or "").strip(), float(r["nombre"] or 0))
        textes_fiche = {}
        if "fic_arta" in presentes:
            for r in c.execute(
                "SELECT code1, code2, libt1, libt2 FROM fic_arta WHERE corbeille = 0"
            ):
                k = "%s/%s" % (str(r["code1"]).strip(), str(r["code2"]).strip())
                textes_fiche.setdefault(k, []).extend([r["libt1"], r["libt2"]])
        rows = c.execute(
            """SELECT l.code1, l.code2, l.qte, l.pun, l.htn, l.cua, l.vua,
                      l.des1, l.des2, l.des3, l.des4,
                      e.numero, e.amjc, e.devise, e.rs
                 FROM cdf_ligne l
                 JOIN cdf_entete e ON e.numero = l.numero AND e.corbeille = 0
                WHERE l.corbeille = 0 AND l.htn > 0 AND l.pun > 0
                  AND COALESCE(l.code1, '') <> ''
                ORDER BY e.amjc DESC, l.id DESC"""
        ).fetchall()
    out = {}
    for r in rows:
        k = "%s/%s" % (str(r["code1"]).strip(), str(r["code2"] or "").strip())
        if k in out:
            continue  # trié par date décroissante : la première est la dernière commande
        cua = str(r["cua"] or "").strip()
        lib, nombre = ua.get(cua, ("", 0.0))
        out[k] = {
            "pun": float(r["pun"]),
            "cua": cua,
            "ua_libelle": lib or cua,
            "ua_nombre": nombre or float(r["vua"] or 0) or 1.0,
            "devise": str(r["devise"] or "").strip().upper(),
            "numero": r["numero"],
            "date": str(r["amjc"] or "")[:10],
            "fournisseur": (r["rs"] or "").strip(),
            "textes": [r["des1"], r["des2"], r["des3"], r["des4"]] + textes_fiche.get(k, []),
        }
    return out


def achats_bruts() -> dict:
    emp = _empreinte()
    if emp is not None and emp == _CACHE["empreinte"] and _CACHE["achats"] is not None:
        return _CACHE["achats"]
    try:
        achats = _lire_achats()
    except Exception:
        logger.exception("prix d'achat PF : lecture du miroir RVGI impossible")
        return {}
    _CACHE.update(empreinte=emp, achats=achats)
    return achats


def prix_achat(achat: dict, par_mille: bool, taux_usd: float) -> Optional[dict]:
    """Prix d'achat ramené à l'unité de valorisation, en euros, ou None.

    `par_mille` : le produit se valorise au mille d'étiquettes.
    `taux_usd` : 1 USD = taux_usd € (0 = non renseigné).
    """
    devise = achat["devise"]
    if devise in _DEVISES_EURO:
        change = 1.0
    elif devise in _DEVISES_USD and taux_usd > 0:
        change = taux_usd
    else:
        return None
    pun, lib, nombre = achat["pun"], achat["ua_libelle"], achat["ua_nombre"]
    detail = ""
    if par_mille:
        if _UA_ROULEAU.search(lib) or _UA_ROULEAU.search(achat["cua"]):
            n = etiquettes_par_rouleau(*achat["textes"])
            if not n:
                return None
            par_etiquette = pun / n
            detail = "%s étiq./rouleau" % format(int(n), ",").replace(",", " ")
        elif nombre > 1:
            par_etiquette = pun / nombre  # « Mille » (1000), « Cent » (100)…
        elif _UA_UNITE.search(lib) or achat["cua"] in ("U", "15"):
            par_etiquette = pun
        else:
            return None
        prix = par_etiquette * 1000.0 * change
    else:
        if not (_UA_UNITE.search(lib) or achat["cua"] in ("U", "15")):
            return None
        prix = pun * change
    if devise in _DEVISES_USD:
        detail = (detail + " · " if detail else "") + "USD × %s" % format(taux_usd, "g")
    return {
        "prix": round(prix, 6),
        "source": "Achat RVGI n°%s · %s" % (achat["numero"], _date_fr(achat["date"])),
        "fournisseur": achat["fournisseur"],
        "detail": detail,
    }


def _date_fr(iso: str) -> str:
    try:
        a, m, j = iso.split("-")
        return "%s/%s/%s" % (j, m, a)
    except ValueError:
        return iso
