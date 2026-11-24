"""
Produits devisés à partir des matières MyStock.

Un produit MyStock est une composition de DÉCLINAISONS : une laize précise d'un
frontal, un grammage précis d'un adhésif. Chaque déclinaison sait déjà se
transformer en coût au m² (voir `mystock_prix`), il ne reste qu'à les additionner
et à appliquer la marge.

Le calcul lui-même n'est pas réécrit : on habille les déclinaisons en
`PricingMaterial` et on passe par `compute_product_cost`, le même moteur que la
base « Coûts matières ». Une seule formule de prix de revient dans l'application.

**Le poids au m² appartient au PRODUIT** (31 août 2026). Un adhésif ne coûte pas
plus cher au kilo parce qu'on en pose 22 g/m² plutôt que 17 : le prix est au
kilo, et c'est la quantité posée qui change — une décision de produit, pas une
caractéristique de la matière. Le composant porte donc `grammage_gsm` et
`perte_pct`, et c'est de là que sort le `weight_per_m2` passé au moteur.

Conséquence directe : un composant au kilo sans grammage coûte 0 €/m². On ne
lève pas — une composition incomplète ne doit pas faire tomber toute la liste des
produits — mais l'interface le signale, faute de quoi un prix de revient
silencieusement amputé passerait pour un prix bas.
"""

from __future__ import annotations

import re
import sqlite3
from collections import Counter
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from app.services.mystock_prix import parametrage, poids_retenu
from app.services.pricing import PricingError, PricingProduct, compute_product_cost
from app.services.pricing.repository import declinaison_to_pricing_material

# Les quatre emplacements usuels d'une étiquette, plus les matières libres.
ROLES_UNIQUES = ("FRONTAL", "ADHESIF", "SILICONE", "GLASSINE")
ROLE_AUTRE = "AUTRE"
ROLES = ROLES_UNIQUES + (ROLE_AUTRE,)

_ROLE_VERS_CHAMP = {
    "FRONTAL": "frontal_id",
    "ADHESIF": "adhesif_id",
    "SILICONE": "silicone_id",
    "GLASSINE": "glassine_id",
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _f(v: Any, defaut: Optional[float] = None) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return defaut


# ─── Libellé commercial, désignation et code proposés ────────────────────────
#
# Un commercial ne cherche pas « P1203 » ou « 2028Y » : il cherche un adhésif
# permanent. Ce nom existe déjà en base, c'est la sous-catégorie de la matière
# dans MyStock (« Permanent », « Thermique Pro », « Enlevable »). Il sert de
# libellé dans la liste des produits et de brique à la désignation proposée.
# Une matière pas encore classée retombe sur sa désignation.

# Un grammage (« 70 g/m² », « 58-60 g/m² », « 70gsm ») ou une épaisseur
# (« 95 µm ») lu dans la désignation d'une matière.
_RE_GRAMMAGE = re.compile(
    r"(\d+(?:[.,]\d+)?(?:\s*-\s*\d+(?:[.,]\d+)?)?)\s*(g/m²|g/m2|gsm|g\b|µm|μm|micro)",
    re.IGNORECASE,
)


def libelle_commercial(sous_categorie: Any, designation: Any, reference: Any = None) -> str:
    """Le nom qu'un commercial reconnaît : la sous-catégorie, sinon la désignation."""
    for v in (sous_categorie, designation, reference):
        t = str(v or "").strip()
        if t:
            return t
    return ""


def grammage_matiere(designation: Any, reference: Any = None) -> Optional[str]:
    """« 70g », « 58-60g », « 95µm » : ce que la matière dit de son poids.

    Lu dans la désignation, puis la référence. Ni le frontal ni la glassine,
    achetés au m², ne portent de grammage saisi : sans ce repli, « Thermique
    Pro » en 70 et en 105 g/m² seraient indiscernables dans la liste.
    """
    for v in (designation, reference):
        m = _RE_GRAMMAGE.search(str(v or ""))
        if m:
            nombre = re.sub(r"\s+", "", m.group(1)).replace(",", ".")
            unite = m.group(2).lower()
            return nombre + ("µm" if unite in ("µm", "μm", "micro") else "g")
    return None


def _fmt_g(v: Any) -> Optional[str]:
    g = _f(v)
    if not g or g <= 0:
        return None
    return f"{g:g}g"


def _brique(c: dict) -> str:
    """Un composant dans la désignation : son libellé, puis son grammage.

    Le grammage saisi sur le produit l'emporte (c'est lui qui distingue un
    Permanent 19g d'un Permanent 22g) ; à défaut, celui de la matière. Quand le
    libellé est déjà la désignation complète, elle porte son grammage : on ne
    le répète pas.
    """
    lib = c.get("libelle_commercial") or c.get("reference") or ""
    g = _fmt_g(c.get("grammage_gsm"))
    if not g and c.get("sous_categorie"):
        g = c.get("grammage_matiere")
    if g:
        nombre = re.escape(g.rstrip("gµm"))
        if not re.search(rf"(?<![\d.]){nombre}(?![\d.])", lib):
            return f"{lib} {g}"
    return lib


def designation_auto(composants: list[dict]) -> str:
    """« Thermique Pro 70g · Permanent 22g, Glassine 58-60g ».

    Même ordre que les désignations saisies à la main jusqu'ici : frontal et
    adhésif liés par « · », puis la glassine et les autres matières.
    """
    par_role = {c.get("role"): c for c in composants if c.get("role") != ROLE_AUTRE}
    tete = [_brique(par_role[r]) for r in ("FRONTAL", "ADHESIF") if r in par_role]
    suite = [_brique(par_role[r]) for r in ("SILICONE", "GLASSINE") if r in par_role]
    suite += [_brique(c) for c in composants if c.get("role") == ROLE_AUTRE]
    morceaux = [" · ".join(x for x in tete if x)] if tete else []
    morceaux += [x for x in suite if x]
    return ", ".join(x for x in morceaux if x)


def infos_declinaisons(conn: sqlite3.Connection, composants: list[dict]) -> list[dict]:
    """Les composants d'une saisie, complétés de ce que la désignation demande."""
    ids = sorted({int(c["declinaison_id"]) for c in composants})
    if not ids:
        return []
    rows = conn.execute(
        f"""SELECT d.id, mp.reference, mp.designation, mp.sous_categorie, mp.sous_section
              FROM mp_matiere_declinaison d
              JOIN matieres_premieres mp ON mp.id = d.matiere_id
             WHERE d.id IN ({",".join("?" * len(ids))})""",
        ids,
    ).fetchall()
    par_id = {int(r["id"]): r for r in rows}
    out = []
    for c in composants:
        r = par_id.get(int(c["declinaison_id"]))
        if not r:
            continue
        out.append({
            **c,
            "reference": r["reference"],
            "sous_categorie": r["sous_categorie"],
            "sous_section": r["sous_section"],
            "libelle_commercial": libelle_commercial(r["sous_categorie"], r["designation"], r["reference"]),
            "grammage_matiere": grammage_matiere(r["designation"], r["reference"]),
        })
    return out


_RE_CODE = re.compile(r"^(.*?)(\d+)$")


def code_propose(
    conn: sqlite3.Connection,
    composants: list[dict],
    exclure_produit_id: Optional[int] = None,
) -> str:
    """Le prochain code libre dans la famille du frontal.

    Rien n'est figé dans le code : préfixe et largeur sont ceux des codes déjà
    en base (« 886-0001 »), et chaque famille de support (la sous-section du
    frontal : Thermiques, Couché…) occupe un bloc de centaines qu'on lit dans
    les produits existants. Un nouveau produit prend le premier numéro libre
    après le plus haut de son bloc ; une famille sans produit, ou un bloc
    plein, part après le plus haut code de la base. Vide quand aucun code
    existant n'a de forme reconnaissable — la saisie reste alors à la main.
    """
    rows = conn.execute(
        """SELECT p.id, p.code, mp.sous_section
             FROM mp_produit p
             LEFT JOIN mp_produit_composant c ON c.produit_id = p.id AND c.role = 'FRONTAL'
             LEFT JOIN mp_matiere_declinaison d ON d.id = c.declinaison_id
             LEFT JOIN matieres_premieres mp ON mp.id = d.matiere_id"""
    ).fetchall()
    lus = []
    for r in rows:
        m = _RE_CODE.match(str(r["code"] or "").strip())
        if m:
            lus.append((m.group(1), len(m.group(2)), int(m.group(2)), r["sous_section"], r["id"]))
    if not lus:
        return ""
    prefixe, largeur = Counter((x[0], x[1]) for x in lus).most_common(1)[0][0]
    utilises = {x[2] for x in lus if x[0] == prefixe and x[1] == largeur}
    candidats = [x for x in lus if x[0] == prefixe and x[1] == largeur and x[4] != exclure_produit_id]
    plafond = 10 ** largeur

    famille = None
    for c in infos_declinaisons(conn, [c for c in composants if c.get("role") == "FRONTAL"]):
        famille = c.get("sous_section")
    nums = [x[2] for x in candidats if famille and x[3] == famille]
    n = None
    if nums:
        bloc = Counter(v // 100 for v in nums).most_common(1)[0][0]
        n = max(v for v in nums if v // 100 == bloc) + 1
        while n in utilises and n // 100 == bloc:
            n += 1
        if n // 100 != bloc:
            n = None
    if n is None:
        n = max(utilises) + 1
        while n in utilises:
            n += 1
    if n >= plafond:
        return ""
    return prefixe + str(n).zfill(largeur)


def normaliser_composants(composants: Any) -> tuple[list[dict], Optional[str]]:
    """
    Valide la composition envoyée par l'interface.

    Renvoie (liste propre, erreur). Un rôle unique deux fois ou une déclinaison
    répétée sont refusés : dans les deux cas le coût serait faux sans que rien ne
    le signale à l'écran.
    """
    if composants is None:
        return [], None
    if not isinstance(composants, list):
        return [], "composition invalide"
    propre: list[dict] = []
    vus_role: set[str] = set()
    vus_decl: set[int] = set()
    for i, c in enumerate(composants):
        if not isinstance(c, dict):
            return [], "composant invalide"
        try:
            decl_id = int(c.get("declinaison_id"))
        except (TypeError, ValueError):
            return [], "déclinaison invalide"
        role = str(c.get("role") or ROLE_AUTRE).upper()
        if role not in ROLES:
            return [], f"rôle inconnu : {role}"
        if role in ROLES_UNIQUES:
            if role in vus_role:
                return [], f"deux matières pour le rôle {role.lower()}"
            vus_role.add(role)
        if decl_id in vus_decl:
            return [], "la même matière est présente deux fois"
        vus_decl.add(decl_id)

        # Grammage et perte : ce que le produit CONSOMME. Facultatifs — une
        # matière achetée au m² n'en a pas besoin — mais bornés quand ils sont
        # là : un grammage négatif ou une perte de 400 % sont des fautes de
        # frappe, et elles donneraient un prix de revient crédible mais faux.
        gram = _f(c.get("grammage_gsm"))
        perte = _f(c.get("perte_pct"))
        if gram is not None and not (0 <= gram <= 99999):
            return [], "grammage hors limites"
        if perte is not None and not (0 <= perte <= 100):
            return [], "perte hors limites (0 à 100 %)"

        propre.append(
            {
                "declinaison_id": decl_id,
                "role": role,
                "ordre": i,
                "grammage_gsm": gram,
                "perte_pct": perte,
            }
        )
    return propre, None


def composants_existent(conn: sqlite3.Connection, composants: list[dict]) -> Optional[str]:
    for c in composants:
        if not conn.execute(
            "SELECT 1 FROM mp_matiere_declinaison WHERE id=?", (c["declinaison_id"],)
        ).fetchone():
            return f"déclinaison introuvable (id={c['declinaison_id']})"
    return None


def _lire_composants(conn: sqlite3.Connection, produit_id: int) -> list[dict]:
    rows = conn.execute(
        """SELECT c.declinaison_id, c.role, c.ordre,
                  c.grammage_gsm, c.perte_pct, d.price_basis,
                  mp.reference, mp.designation, mp.categorie, mp.sous_section,
                  mp.sous_categorie,
                  l.valeur_mm, l.label AS laize_label,
                  g.valeur_gsm, g.label AS grammage_label
             FROM mp_produit_composant c
             JOIN mp_matiere_declinaison d ON d.id = c.declinaison_id
             JOIN matieres_premieres mp    ON mp.id = d.matiere_id
             LEFT JOIN mp_laizes    l ON l.id = d.laize_id
             LEFT JOIN mp_grammages g ON g.id = d.grammage_id
            WHERE c.produit_id = ?
            ORDER BY c.ordre, c.id""",
        (produit_id,),
    ).fetchall()
    out = []
    for r in rows:
        if r["valeur_mm"] is not None:
            libelle = r["laize_label"] or f"{int(_f(r['valeur_mm'], 0))} mm"
        elif r["valeur_gsm"] is not None:
            libelle = r["grammage_label"] or f"{_f(r['valeur_gsm'], 0):g} g/m²"
        else:
            libelle = "Toutes déclinaisons"
        out.append(
            {
                "declinaison_id": int(r["declinaison_id"]),
                "role": r["role"],
                "ordre": int(r["ordre"]),
                "reference": r["reference"],
                "designation": r["designation"],
                "categorie": r["categorie"],
                # Le support d'un frontal (thermique, couché, synthétique,
                # vélin) : la liste des produits le montre en badge, c'est ce
                # qui distingue deux étiquettes à l'œil.
                "sous_section": r["sous_section"],
                # Le nom commercial (« Permanent » plutôt que « 2028Y ») et le
                # grammage que la matière annonce : la liste des produits les
                # affiche, la désignation proposée les assemble.
                "sous_categorie": r["sous_categorie"],
                "libelle_commercial": libelle_commercial(
                    r["sous_categorie"], r["designation"], r["reference"]),
                "grammage_matiere": grammage_matiere(r["designation"], r["reference"]),
                "libelle": libelle,
                # Ce que le produit consomme, et le poids qui en découle. Le
                # poids est calculé ici plutôt qu'à l'écran : deux endroits qui
                # appliquent la perte finissent par ne plus le faire pareil.
                "grammage_gsm": _f(r["grammage_gsm"]),
                "perte_pct": _f(r["perte_pct"]),
                "weight_per_m2": poids_retenu(r["grammage_gsm"], r["perte_pct"]),
                # Une matière au m² n'a pas de grammage à saisir : l'interface a
                # besoin de le savoir pour ne pas réclamer un chiffre inutile.
                "price_basis": r["price_basis"] or "PER_KG",
            }
        )
    return out


def _ecrire_composants(conn: sqlite3.Connection, produit_id: int, composants: list[dict]) -> None:
    conn.execute("DELETE FROM mp_produit_composant WHERE produit_id=?", (produit_id,))
    for c in composants:
        conn.execute(
            """INSERT INTO mp_produit_composant
                   (produit_id, declinaison_id, role, ordre, grammage_gsm, perte_pct)
               VALUES (?,?,?,?,?,?)""",
            (
                produit_id, c["declinaison_id"], c["role"], c["ordre"],
                c.get("grammage_gsm"), c.get("perte_pct"),
            ),
        )


def parametrage_cache(conn: sqlite3.Connection, declinaison_id: int, cache: Optional[dict]) -> Optional[dict]:
    """`parametrage` d'une déclinaison, mémorisé dans `cache` s'il est fourni."""
    if cache is None:
        return parametrage(conn, declinaison_id)
    if declinaison_id not in cache:
        cache[declinaison_id] = parametrage(conn, declinaison_id)
    return cache[declinaison_id]


def cout_produit(conn: sqlite3.Connection, produit: dict, reglages, cache: Optional[dict] = None) -> Any:
    """
    Prix de revient d'un produit MyStock.

    Les déclinaisons prennent la place des matières : leur identifiant sert d'id
    dans la carte passée au moteur. Les rôles usuels occupent les emplacements
    nommés, le reste part en composants libres.

    `cache` (déclinaison → paramétrage) se partage entre les produits d'une même
    liste : une déclinaison sert à des dizaines de produits, et chaque
    `parametrage` coûte une dizaine de requêtes.
    """
    carte = {}
    slots: dict[str, Optional[int]] = {
        "frontal_id": None, "adhesif_id": None, "silicone_id": None, "glassine_id": None
    }
    extras: list[int] = []
    for c in produit.get("composants", []):
        param = parametrage_cache(conn, c["declinaison_id"], cache)
        if not param:
            raise PricingError(f"Matière introuvable (id={c['declinaison_id']}).")
        # Le poids vient du COMPOSANT, pas de la matière : c'est le produit qui
        # décide de la quantité posée. `param` porte encore l'ancien poids —
        # colonne conservée pour permettre le retour en arrière — et il ne doit
        # surtout pas resservir, sinon la bascule n'aurait rien changé.
        param = {
            **param,
            "weight_per_m2": poids_retenu(c.get("grammage_gsm"), c.get("perte_pct")),
        }
        carte[c["declinaison_id"]] = declinaison_to_pricing_material(param)
        champ = _ROLE_VERS_CHAMP.get(c["role"])
        if champ:
            slots[champ] = c["declinaison_id"]
        else:
            extras.append(c["declinaison_id"])
    pp = PricingProduct(
        id=int(produit["id"]),
        code=produit["code"],
        name=produit["designation"],
        extra_material_ids=tuple(extras),
        # Le moteur travaille en Decimal : un float ici casserait l'arrondi.
        custom_margin_pct=(
            Decimal(str(produit["custom_margin_pct"]))
            if produit.get("custom_margin_pct") is not None
            else None
        ),
        **slots,
    )
    return compute_product_cost(pp, carte, reglages)


def _produit_dict(row: sqlite3.Row, composants: list[dict]) -> dict:
    return {
        "id": int(row["id"]),
        "code": row["code"],
        "designation": row["designation"],
        "custom_margin_pct": _f(row["custom_margin_pct"]),
        "actif": bool(row["actif"]),
        "note": row["note"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "updated_by_name": row["updated_by_name"],
        "composants": composants,
    }


def get_produit(conn: sqlite3.Connection, produit_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM mp_produit WHERE id=?", (produit_id,)).fetchone()
    if not row:
        return None
    return _produit_dict(row, _lire_composants(conn, produit_id))


def list_produits(
    conn: sqlite3.Connection,
    *,
    q: Optional[str] = None,
    actifs_only: bool = True,
) -> list[dict]:
    sql = "SELECT * FROM mp_produit WHERE 1=1"
    args: list[Any] = []
    if actifs_only:
        sql += " AND actif=1"
    if q and q.strip():
        sql += " AND (code LIKE ? OR designation LIKE ?)"
        pat = f"%{q.strip()}%"
        args.extend([pat, pat])
    sql += " ORDER BY code COLLATE NOCASE ASC"
    return [
        _produit_dict(r, _lire_composants(conn, int(r["id"])))
        for r in conn.execute(sql, args).fetchall()
    ]


def creer_produit(
    conn: sqlite3.Connection,
    *,
    code: str,
    designation: str,
    composants: Any = None,
    custom_margin_pct: Any = None,
    note: Optional[str] = None,
    user_name: Optional[str] = None,
) -> dict:
    code = (code or "").strip()
    designation = (designation or "").strip()
    propres, err = normaliser_composants(composants)
    if err:
        return {"ok": False, "reason": err}
    err = composants_existent(conn, propres)
    if err:
        return {"ok": False, "reason": err}
    # Laissés vides, code et désignation se déduisent de la composition.
    if not code:
        code = code_propose(conn, propres)
    if not designation:
        designation = designation_auto(infos_declinaisons(conn, propres))
    if not code:
        return {"ok": False, "reason": "code obligatoire"}
    if not designation:
        return {"ok": False, "reason": "désignation obligatoire"}
    if conn.execute(
        "SELECT 1 FROM mp_produit WHERE code=? COLLATE NOCASE", (code,)
    ).fetchone():
        return {"ok": False, "reason": f"le code « {code} » existe déjà"}
    marge = _f(custom_margin_pct)
    if marge is not None and (marge < 0 or marge > 1000):
        return {"ok": False, "reason": "marge hors limites"}
    now = _now()
    cur = conn.execute(
        """INSERT INTO mp_produit
           (code, designation, custom_margin_pct, note, created_at, updated_at, updated_by_name)
           VALUES (?,?,?,?,?,?,?)""",
        (code, designation, marge, note, now, now, user_name),
    )
    produit_id = int(cur.lastrowid)
    _ecrire_composants(conn, produit_id, propres)
    return {"ok": True, "produit": get_produit(conn, produit_id)}


def modifier_produit(
    conn: sqlite3.Connection,
    produit_id: int,
    *,
    patch: dict,
    user_name: Optional[str] = None,
) -> dict:
    row = conn.execute("SELECT * FROM mp_produit WHERE id=?", (produit_id,)).fetchone()
    if not row:
        return {"ok": False, "reason": "produit introuvable"}

    sets: list[str] = []
    args: list[Any] = []

    if "code" in patch:
        code = str(patch["code"] or "").strip()
        if not code:
            return {"ok": False, "reason": "code obligatoire"}
        if conn.execute(
            "SELECT 1 FROM mp_produit WHERE code=? COLLATE NOCASE AND id<>?",
            (code, produit_id),
        ).fetchone():
            return {"ok": False, "reason": f"le code « {code} » existe déjà"}
        sets.append("code=?")
        args.append(code)
    if "designation" in patch:
        des = str(patch["designation"] or "").strip()
        if not des:
            return {"ok": False, "reason": "désignation obligatoire"}
        sets.append("designation=?")
        args.append(des)
    if "custom_margin_pct" in patch:
        raw = patch["custom_margin_pct"]
        marge = None if raw in (None, "", "null") else _f(raw)
        if marge is not None and (marge < 0 or marge > 1000):
            return {"ok": False, "reason": "marge hors limites"}
        sets.append("custom_margin_pct=?")
        args.append(marge)
    if "note" in patch:
        sets.append("note=?")
        args.append((str(patch["note"]).strip() or None) if patch["note"] else None)
    if "actif" in patch:
        sets.append("actif=?")
        args.append(1 if patch["actif"] else 0)

    composants = None
    if "composants" in patch:
        composants, err = normaliser_composants(patch["composants"])
        if err:
            return {"ok": False, "reason": err}
        err = composants_existent(conn, composants)
        if err:
            return {"ok": False, "reason": err}

    if not sets and composants is None:
        return {"ok": False, "reason": "aucune modification"}

    # Une composition modifiée est une modification du produit : elle date et
    # signe la fiche comme le reste.
    sets.extend(["updated_at=?", "updated_by_name=?"])
    args.extend([_now(), user_name])
    args.append(produit_id)
    conn.execute(f"UPDATE mp_produit SET {', '.join(sets)} WHERE id=?", args)
    if composants is not None:
        _ecrire_composants(conn, produit_id, composants)
    return {"ok": True, "produit": get_produit(conn, produit_id)}


def supprimer_produit(conn: sqlite3.Connection, produit_id: int) -> dict:
    """Désactivation : un produit devisé peut avoir servi, on ne l'efface pas."""
    if not conn.execute("SELECT 1 FROM mp_produit WHERE id=?", (produit_id,)).fetchone():
        return {"ok": False, "reason": "produit introuvable"}
    conn.execute(
        "UPDATE mp_produit SET actif=0, updated_at=? WHERE id=?", (_now(), produit_id)
    )
    return {"ok": True}
