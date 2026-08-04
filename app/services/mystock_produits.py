"""
Produits devisés à partir des matières MyStock.

Un produit MyStock est une composition de DÉCLINAISONS : une laize précise d'un
frontal, un grammage précis d'un adhésif. Chaque déclinaison sait déjà se
transformer en coût au m² (voir `mystock_prix`), il ne reste qu'à les additionner
et à appliquer la marge.

Le calcul lui-même n'est pas réécrit : on habille les déclinaisons en
`PricingMaterial` et on passe par `compute_product_cost`, le même moteur que la
base « Coûts matières ». Une seule formule de prix de revient dans l'application.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from app.services.mystock_prix import parametrage
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


def _normaliser_composants(composants: Any) -> tuple[list[dict], Optional[str]]:
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
            return [], "la même déclinaison est présente deux fois"
        vus_decl.add(decl_id)
        propre.append({"declinaison_id": decl_id, "role": role, "ordre": i})
    return propre, None


def _composants_existent(conn: sqlite3.Connection, composants: list[dict]) -> Optional[str]:
    for c in composants:
        if not conn.execute(
            "SELECT 1 FROM mp_matiere_declinaison WHERE id=?", (c["declinaison_id"],)
        ).fetchone():
            return f"déclinaison introuvable (id={c['declinaison_id']})"
    return None


def _lire_composants(conn: sqlite3.Connection, produit_id: int) -> list[dict]:
    rows = conn.execute(
        """SELECT c.declinaison_id, c.role, c.ordre,
                  mp.reference, mp.designation, mp.categorie,
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
                "libelle": libelle,
            }
        )
    return out


def _ecrire_composants(conn: sqlite3.Connection, produit_id: int, composants: list[dict]) -> None:
    conn.execute("DELETE FROM mp_produit_composant WHERE produit_id=?", (produit_id,))
    for c in composants:
        conn.execute(
            """INSERT INTO mp_produit_composant (produit_id, declinaison_id, role, ordre)
               VALUES (?,?,?,?)""",
            (produit_id, c["declinaison_id"], c["role"], c["ordre"]),
        )


def cout_produit(conn: sqlite3.Connection, produit: dict, reglages) -> Any:
    """
    Prix de revient d'un produit MyStock.

    Les déclinaisons prennent la place des matières : leur identifiant sert d'id
    dans la carte passée au moteur. Les rôles usuels occupent les emplacements
    nommés, le reste part en composants libres.
    """
    carte = {}
    slots: dict[str, Optional[int]] = {
        "frontal_id": None, "adhesif_id": None, "silicone_id": None, "glassine_id": None
    }
    extras: list[int] = []
    for c in produit.get("composants", []):
        param = parametrage(conn, c["declinaison_id"])
        if not param:
            raise PricingError(f"Déclinaison introuvable (id={c['declinaison_id']}).")
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
    if not code:
        return {"ok": False, "reason": "code obligatoire"}
    if not designation:
        return {"ok": False, "reason": "désignation obligatoire"}
    if conn.execute(
        "SELECT 1 FROM mp_produit WHERE code=? COLLATE NOCASE", (code,)
    ).fetchone():
        return {"ok": False, "reason": f"le code « {code} » existe déjà"}
    propres, err = _normaliser_composants(composants)
    if err:
        return {"ok": False, "reason": err}
    err = _composants_existent(conn, propres)
    if err:
        return {"ok": False, "reason": err}
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
        composants, err = _normaliser_composants(patch["composants"])
        if err:
            return {"ok": False, "reason": err}
        err = _composants_existent(conn, composants)
        if err:
            return {"ok": False, "reason": err}

    if not sets and composants is None:
        return {"ok": False, "reason": "aucune modification"}

    if sets:
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
