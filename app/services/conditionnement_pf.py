"""
Conditionnement produit fini — palette et unités de vente par palette.
=====================================================================

Ce que la fiche technique sait déjà, l'opérateur n'a pas à le retaper. À
l'entrée Z1, MySifa demandait le type de palette et le nombre de palettes
alors que les deux se déduisent de la fiche du produit :

- **type de palette** : `fiches_techniques.palette_type` (texte libre venu
  d'Access), rapproché d'une référence concrète de `matieres_premieres` via
  `mp_fiche_mapping` (kind='palette'), la même table que la vue Besoins
  matières. Repli « Europe » : la première palette `is_europe=1`.
- **nombre de palettes** : quantité saisie ÷ nombre d'unités de vente qui
  tiennent sur une palette, arrondi au supérieur (une palette entamée reste
  une palette).

Unités de vente par palette (cascade du conditionnement) :

    cartons/palette    = palette_nb_cartons_sol × palette_nb_cartons_hauteur
    bobines/palette    = nb_bobines_carton × cartons/palette
    étiquettes/palette = nb_etiq_bobin × bobines/palette
    mille/palette      = étiquettes/palette ÷ 1000

Cas particulier repris de `app/routers/planning.py` : quand le « carton » est
en réalité un conteneur de taille palette (libellé carton ou palette_type),
1 carton = 1 palette.

Le calcul est toujours rendu avec sa trace (`manque`) : une valeur pré-remplie
qu'on ne peut pas expliquer est pire qu'un champ vide — l'opérateur la valide
sans la lire.
"""
from __future__ import annotations

import math
import re
import unicodedata
from typing import Optional

from app.services.fiche_ref_parser import normalize_ref_produit

# Champs de fiche utiles au conditionnement (mêmes noms que la table).
_FT_COLS = (
    "id", "reference", "ref_produit_norm", "machine",
    "conditionnement", "cartons",
    "nb_etiq_bobin", "nb_bobines_carton",
    "palette_type", "palette_nb_cartons_sol", "palette_nb_cartons_hauteur",
)


def _f(value) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def _sans_accents(value: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", value)
        if unicodedata.category(c) != "Mn"
    )


def est_carton_taille_palette(label) -> bool:
    """Le « carton » est-il en réalité un conteneur de taille palette ?

    Détection par mots-clés (conteneur, container, box…) ou par dimensions
    proches de 1200×800 mm (tolérance ±150). Dans ce cas 1 carton = 1 palette.
    """
    if not label:
        return False
    s = str(label).lower()
    for kw in ("conteneur", "container", " box", "box ", "palette box"):
        if kw in s:
            return True
    if s.strip().startswith("box"):
        return True
    m = re.search(r"(\d{3,4})\s*[x×]\s*(\d{3,4})", s)
    if m:
        try:
            a, b = int(m.group(1)), int(m.group(2))
            lo, hi = min(a, b), max(a, b)
            if 1050 <= hi <= 1350 and 650 <= lo <= 950:
                return True
        except ValueError:
            pass
    return False


def normaliser_palette_type(value) -> Optional[str]:
    """Libellé lisible du type de palette (Europe / Perdue / valeur d'origine)."""
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    s = _sans_accents(raw.lower())
    if "antibac" in s or "anti-bac" in s or "anti bac" in s:
        return "Perdue"
    if "perdu" in s or "jetab" in s:
        return "Perdue"
    if "europe" in s or s == "eur" or s.startswith("eur "):
        return "Europe"
    return raw[:1].upper() + raw[1:].lower() if len(raw) > 1 else raw.upper()


def famille_unite(unite) -> Optional[str]:
    """Famille d'unité de vente : etiquette | mille | bobine | carton | palette.

    `produits.unite` est du texte libre (« étiquettes », « Bobine », « ML »…) :
    on ne peut pas s'appuyer sur une énumération, seulement sur des mots-clés.
    Renvoie None quand l'unité n'appartient à aucune famille connue — le
    nombre de palettes n'est alors pas calculable, et on le dit.
    """
    if not unite:
        return None
    s = _sans_accents(str(unite).strip().lower())
    if not s:
        return None
    # « m » n'est pas un raccourci de mille ici : c'est le metre lineaire, qui
    # ne se palettise pas. Seul le mot ecrit en toutes lettres compte.
    if "mille" in s:
        return "mille"
    if "bobine" in s or "rouleau" in s or s.startswith("bob"):
        return "bobine"
    if "carton" in s or "colis" in s or "box" in s:
        return "carton"
    if "palette" in s or s == "pal":
        return "palette"
    if "etiq" in s or "piece" in s or s in ("pce", "pcs", "u", "unite", "unites"):
        return "etiquette"
    return None


def _fiche_pour_ref(conn, ref_produit, machine_nom=None) -> Optional[dict]:
    """Fiche technique du produit, tie-breaker machine comme planning.py.

    Fiche de la machine du dossier > fiche sans machine > autre, puis id
    croissant. Sans ce départage, une référence déclinée par machine renvoie
    une fiche au hasard — et donc un conditionnement au hasard.
    """
    norm = normalize_ref_produit(ref_produit)
    ref_txt = (ref_produit or "").strip()
    if not norm and not ref_txt:
        return None
    cols = ", ".join(_FT_COLS)
    rows = []
    try:
        if norm:
            rows = conn.execute(
                f"SELECT {cols} FROM fiches_techniques WHERE ref_produit_norm = ?",
                (norm,),
            ).fetchall()
        if not rows and ref_txt:
            rows = conn.execute(
                f"SELECT {cols} FROM fiches_techniques "
                f"WHERE LOWER(TRIM(reference)) = LOWER(TRIM(?))",
                (ref_txt,),
            ).fetchall()
    except Exception:
        return None
    if not rows:
        return None
    mach = (machine_nom or "").strip().lower()

    def _rang(r):
        fm = (r["machine"] or "").strip().lower() if "machine" in r.keys() else ""
        if fm and fm == mach:
            rang = 0
        elif not fm:
            rang = 1
        else:
            rang = 2
        return (rang, r["id"])

    return dict(min(rows, key=_rang))


def _palette_matiere(conn, palette_type) -> Optional[dict]:
    """Référence palette de MyStock correspondant au `palette_type` de la fiche.

    1. `mp_fiche_mapping` (kind='palette') : la correspondance éditée à la main,
       qui fait autorité.
    2. Repli Europe : quand la fiche dit « Europe » et qu'aucun mapping n'existe,
       la première palette `is_europe=1`. Aucun repli pour les autres libellés :
       proposer une palette au hasard ferait sortir du stock la mauvaise
       référence sans que personne ne s'en aperçoive.
    """
    src = (palette_type or "").strip()
    if not src:
        return None
    row = None
    try:
        row = conn.execute(
            """SELECT mp.id, mp.reference, mp.designation, mp.is_europe
               FROM mp_fiche_mapping m
               JOIN matieres_premieres mp ON mp.id = m.matiere_id
               WHERE m.kind = 'palette'
                 AND LOWER(TRIM(m.source_value)) = LOWER(TRIM(?))
               LIMIT 1""",
            (src,),
        ).fetchone()
    except Exception:
        row = None
    origine = "mp_fiche_mapping"
    if not row and normaliser_palette_type(src) == "Europe":
        try:
            row = conn.execute(
                """SELECT id, reference, designation, is_europe
                   FROM matieres_premieres
                   WHERE LOWER(TRIM(categorie)) = 'palette'
                     AND COALESCE(is_europe, 0) = 1
                     AND COALESCE(actif, 1) = 1
                   ORDER BY reference LIMIT 1""",
            ).fetchone()
            origine = "is_europe"
        except Exception:
            row = None
    if not row:
        return None
    return {
        "matiere_id": int(row["id"]),
        "reference": row["reference"],
        "designation": row["designation"],
        "is_europe": bool(row["is_europe"]) if "is_europe" in row.keys() else False,
        "origine": origine,
    }


def conditionnement_produit(conn, ref_produit, machine_nom=None,
                            unite_vente=None) -> dict:
    """Palette par défaut + unités de vente par palette pour une référence.

    Renvoie toujours une structure complète : `palette` et `unites_par_palette`
    valent None quand la fiche ne permet pas de conclure, et `manque` dit
    lesquelles des données ont fait défaut.
    """
    out = {
        "ref_produit": (ref_produit or "").strip() or None,
        "ref_produit_norm": normalize_ref_produit(ref_produit),
        "fiche_id": None,
        "fiche_reference": None,
        "palette": None,
        "palette_type": None,
        "palette_label": None,
        "etiquettes_par_bobine": None,
        "bobines_par_carton": None,
        "cartons_par_palette": None,
        "carton_taille_palette": False,
        "par_palette": {},
        "unite_vente": (unite_vente or "").strip() or None,
        "unite_vente_famille": famille_unite(unite_vente),
        "unites_par_palette": None,
        "phrase": None,
        "manque": [],
    }

    ft = _fiche_pour_ref(conn, ref_produit, machine_nom)
    if not ft:
        out["manque"].append("Aucune fiche technique pour cette référence")
        return out

    out["fiche_id"] = ft.get("id")
    out["fiche_reference"] = ft.get("reference")
    out["palette_type"] = (ft.get("palette_type") or "").strip() or None
    out["palette_label"] = normaliser_palette_type(ft.get("palette_type"))

    if out["palette_type"]:
        pal = _palette_matiere(conn, out["palette_type"])
        if pal:
            out["palette"] = pal
        else:
            out["manque"].append(
                "Type de palette « %s » non rapproché d'une référence MyStock"
                % out["palette_type"]
            )
    else:
        out["manque"].append("Type de palette absent de la fiche technique")

    etiq_bob = _f(ft.get("nb_etiq_bobin"))
    bob_cart = _f(ft.get("nb_bobines_carton"))
    sol = _f(ft.get("palette_nb_cartons_sol"))
    haut = _f(ft.get("palette_nb_cartons_hauteur"))
    is_box = (est_carton_taille_palette(ft.get("cartons"))
              or est_carton_taille_palette(ft.get("palette_type")))
    out["carton_taille_palette"] = is_box
    out["etiquettes_par_bobine"] = etiq_bob
    out["bobines_par_carton"] = bob_cart

    if is_box:
        cartons_pal = 1.0
    elif sol and haut:
        cartons_pal = sol * haut
    else:
        cartons_pal = None
        out["manque"].append("Cartons au sol / en hauteur absents de la fiche")
    out["cartons_par_palette"] = cartons_pal

    par_palette = {"palette": 1.0}
    if cartons_pal:
        par_palette["carton"] = cartons_pal
        if bob_cart:
            par_palette["bobine"] = bob_cart * cartons_pal
            if etiq_bob:
                par_palette["etiquette"] = etiq_bob * bob_cart * cartons_pal
                par_palette["mille"] = etiq_bob * bob_cart * cartons_pal / 1000.0
            else:
                out["manque"].append("Étiquettes par bobine absentes de la fiche")
        else:
            out["manque"].append("Bobines par carton absentes de la fiche")
    out["par_palette"] = par_palette

    fam = out["unite_vente_famille"]
    if fam:
        out["unites_par_palette"] = par_palette.get(fam)
        if out["unites_par_palette"] is None:
            out["manque"].append(
                "Conditionnement incomplet pour l'unité de vente « %s »"
                % (out["unite_vente"] or fam)
            )
    elif out["unite_vente"]:
        out["manque"].append(
            "Unité de vente « %s » non reconnue" % out["unite_vente"]
        )

    out["phrase"] = phrase_conditionnement(out)
    return out


def phrase_conditionnement(c: dict) -> Optional[str]:
    """« Palettes de 30 cartons de 6 bobines de 1 000 étiquettes »."""
    parts = []
    cartons_pal = c.get("cartons_par_palette")
    if c.get("carton_taille_palette"):
        parts.append("Conteneurs")
    elif cartons_pal:
        n = int(cartons_pal)
        parts.append("Palettes de %d %s" % (n, "cartons" if n > 1 else "carton"))
    else:
        return None
    bob = c.get("bobines_par_carton")
    if bob:
        n = int(bob)
        parts.append("de %d %s" % (n, "bobines" if n > 1 else "bobine"))
    etiq = c.get("etiquettes_par_bobine")
    if etiq:
        n = int(etiq)
        s = f"{n:,}".replace(",", " ")
        parts.append("de %s %s" % (s, "étiquettes" if n > 1 else "étiquette"))
    return " ".join(parts)


def nb_palettes(quantite, unites_par_palette) -> Optional[int]:
    """Nombre de palettes pour une quantité — arrondi au supérieur.

    Une palette entamée occupe une place au sol : l'arrondi inférieur ferait
    sortir du stock une palette de moins qu'il n'en faut réellement.
    """
    q = _f(quantite)
    u = _f(unites_par_palette)
    if not q or not u:
        return None
    return max(1, int(math.ceil(q / u)))
