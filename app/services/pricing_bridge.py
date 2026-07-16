"""
Pont MyStock <-> /pricing (Coûts matières).

Ce module contient la logique de synchronisation bidirectionnelle du prix
matière entre les deux mondes de MySifa, une fois qu'une matière
`matieres_premieres` (MyStock) et une matière `mc_material` (/pricing) sont
appairées via `matieres_premieres.mc_material_id` (migration 187).

Périmètre couvert par la sync automatique (Round 2)
---------------------------------------------------

- Matières **laizées** (frontal, glassine, complexe) appairées avec un
  `mc_material` dont `price_basis = 'PER_M2'` et `price_currency = 'EUR'`.
  Ces deux mondes parlent alors la même unité (EUR/m2) et le prix se
  propage sans conversion.
- Toute autre configuration (prix en USD, base PER_KG, matière non laizée,
  matière non appairée) est **volontairement ignorée** en Round 2 : la
  synchronisation retourne `{synced: False, reason: '...'}` et laisse
  l'endpoint principal s'exécuter normalement. La sync des cas USD/PER_KG
  sera ajoutée en Round 3 quand la conversion via `weight_per_m2` et
  `eur_usd_rate` sera testée dans les deux sens.

Contrat des fonctions publiques
-------------------------------

Toutes les fonctions publiques :

- prennent une `sqlite3.Connection` déjà ouverte (l'appelant gère la
  transaction et le `commit`).
- ne lèvent jamais d'exception métier - elles retournent un dict de
  diagnostic. Les erreurs SQL non prévues remontent (bug à corriger).
- sont idempotentes : rejouer une sync sur des données identiques ne crée
  pas de doublon historique (comparaison prix_avant/prix_apres).
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Any, Optional


# Catégories MyStock qui parlent en EUR/m2 (frontal / glassine / complexe).
# Doit rester aligné avec `_MP_CATEGORIES_LAIZEES` dans app/routers/stock.py.
_LAIZEE_CATEGORIES = frozenset({"frontal", "glassine", "complexe"})


def _is_laizee(categorie: Optional[str]) -> bool:
    return (categorie or "").strip().lower() in _LAIZEE_CATEGORIES


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


# ─────────────────────────────────────────────────────────────────────────────
# Appairage manuel
# ─────────────────────────────────────────────────────────────────────────────


def link_matiere(conn: sqlite3.Connection, mp_id: int, mc_id: int) -> dict[str, Any]:
    """
    Lie une matière `matieres_premieres` à un `mc_material`.

    Copie également les caractéristiques pricing (weight_per_m2, weight_gsm,
    price_basis, is_imported, container_kg, container_cost_usd,
    tax_incidence) depuis mc_material vers matieres_premieres, sans jamais
    écraser une valeur déjà saisie côté MyStock (COALESCE).

    Retourne {ok, mp_id, mc_id, copied: list[str]}.
    """
    mp = conn.execute(
        "SELECT id, mc_material_id FROM matieres_premieres WHERE id=?", (mp_id,)
    ).fetchone()
    if not mp:
        return {"ok": False, "reason": f"matieres_premieres id={mp_id} introuvable"}
    mc = conn.execute(
        "SELECT id, weight_per_m2, weight_gsm, price_basis, is_imported, "
        "container_kg, container_cost_usd, tax_incidence "
        "FROM mc_material WHERE id=?",
        (mc_id,),
    ).fetchone()
    if not mc:
        return {"ok": False, "reason": f"mc_material id={mc_id} introuvable"}

    conn.execute(
        "UPDATE matieres_premieres SET mc_material_id=? WHERE id=?", (mc_id, mp_id)
    )

    copy_map = [
        ("weight_per_m2",      mc["weight_per_m2"]),
        ("weight_gsm",         mc["weight_gsm"]),
        ("price_basis",        mc["price_basis"]),
        ("is_imported",        mc["is_imported"]),
        ("container_kg",       mc["container_kg"]),
        ("container_cost_usd", mc["container_cost_usd"]),
        ("tax_incidence",      mc["tax_incidence"]),
    ]
    copied: list[str] = []
    for col, val in copy_map:
        if val is None:
            continue
        # COALESCE : garde la valeur MyStock si déjà présente.
        cur = conn.execute(
            f"UPDATE matieres_premieres SET {col} = COALESCE({col}, ?) WHERE id=?",
            (val, mp_id),
        )
        if cur.rowcount > 0:
            copied.append(col)
    return {"ok": True, "mp_id": mp_id, "mc_id": mc_id, "copied": copied}


def unlink_matiere(conn: sqlite3.Connection, mp_id: int) -> dict[str, Any]:
    """
    Casse le lien matieres_premieres <-> mc_material. Ne touche à aucune
    autre colonne (les caractéristiques précédemment copiées restent).
    """
    cur = conn.execute(
        "UPDATE matieres_premieres SET mc_material_id=NULL WHERE id=?", (mp_id,)
    )
    return {"ok": cur.rowcount > 0, "mp_id": mp_id}


# ─────────────────────────────────────────────────────────────────────────────
# Synchronisation MyStock -> /pricing
# ─────────────────────────────────────────────────────────────────────────────


def sync_mp_to_mc(
    conn: sqlite3.Connection,
    mp_id: int,
    *,
    actor_id: Optional[int] = None,
    actor_name: Optional[str] = None,
    source_note: str = "MyStock",
) -> dict[str, Any]:
    """
    Après une modification côté MyStock (mp_valorisation ou
    matieres_premieres.prix_eur_m2), pousse le prix vers mc_material.

    Ne fait rien si :
    - la matière n'est pas appairée (mc_material_id NULL) ;
    - la matière n'est pas laizée (adhesif, mandrin, palette, carton...) ;
    - le mc_material appairé n'est pas en (PER_M2, EUR).

    Retourne {synced, reason, ...}.
    """
    mp = conn.execute(
        "SELECT id, categorie, prix_eur_m2, mc_material_id "
        "FROM matieres_premieres WHERE id=?",
        (mp_id,),
    ).fetchone()
    if not mp:
        return {"synced": False, "reason": f"mp id={mp_id} introuvable"}
    if mp["mc_material_id"] is None:
        return {"synced": False, "reason": "non appairée"}
    if not _is_laizee(mp["categorie"]):
        return {"synced": False, "reason": "matière non laizée — sync EUR/m² non applicable"}
    if mp["prix_eur_m2"] is None:
        return {"synced": False, "reason": "prix_eur_m2 vide côté MyStock"}

    mc = conn.execute(
        "SELECT id, unit_price, price_basis, price_currency, tax_incidence "
        "FROM mc_material WHERE id=?",
        (mp["mc_material_id"],),
    ).fetchone()
    if not mc:
        return {"synced": False, "reason": "mc_material appairé introuvable"}
    if (mc["price_basis"] or "PER_KG") != "PER_M2":
        return {
            "synced": False,
            "reason": f"mc price_basis={mc['price_basis']} incompatible (attendu PER_M2)",
        }
    if (mc["price_currency"] or "EUR") != "EUR":
        return {
            "synced": False,
            "reason": f"mc price_currency={mc['price_currency']} incompatible (attendu EUR)",
        }

    new_price = float(mp["prix_eur_m2"])
    old_price = float(mc["unit_price"] or 0)
    if abs(new_price - old_price) < 1e-6:
        return {"synced": False, "reason": "prix identique — pas de mise à jour"}

    conn.execute(
        "UPDATE mc_material SET unit_price=?, "
        "updated_at=strftime('%Y-%m-%dT%H:%M:%S','now','localtime') WHERE id=?",
        (new_price, mc["id"]),
    )
    conn.execute(
        "INSERT INTO mc_material_price_history "
        "(material_id, unit_price, price_currency, tax_incidence, "
        " effective_date, source, created_by) "
        "VALUES (?,?,?,?,?,?,?)",
        (
            mc["id"],
            new_price,
            mc["price_currency"] or "EUR",
            float(mc["tax_incidence"] or 1.0),
            date.today().isoformat(),
            f"Sync depuis {source_note} par {actor_name or 'système'}",
            actor_id,
        ),
    )
    return {
        "synced": True,
        "direction": "mp→mc",
        "mp_id": mp_id,
        "mc_id": mc["id"],
        "old_price": old_price,
        "new_price": new_price,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Synchronisation /pricing -> MyStock
# ─────────────────────────────────────────────────────────────────────────────


def sync_mc_to_mp(
    conn: sqlite3.Connection,
    mc_id: int,
    *,
    actor_id: Optional[int] = None,
    actor_name: Optional[str] = None,
    source_note: str = "Coûts matières",
) -> dict[str, Any]:
    """
    Après une modification côté /pricing (mc_material.unit_price), pousse le
    nouveau prix vers matieres_premieres.prix_eur_m2 pour chaque matière
    MyStock appairée (théoriquement 1, mais on gère N par prudence).

    Ne fait rien si :
    - aucun matieres_premieres.mc_material_id ne pointe sur ce mc_id ;
    - la matière MyStock appairée n'est pas laizée ;
    - le mc_material n'est pas en (PER_M2, EUR).

    Retourne {synced, count_updated, results: list[dict]}.
    """
    mc = conn.execute(
        "SELECT id, unit_price, price_basis, price_currency "
        "FROM mc_material WHERE id=?",
        (mc_id,),
    ).fetchone()
    if not mc:
        return {"synced": False, "reason": f"mc id={mc_id} introuvable"}
    if (mc["price_basis"] or "PER_KG") != "PER_M2":
        return {"synced": False, "reason": f"price_basis={mc['price_basis']} incompatible"}
    if (mc["price_currency"] or "EUR") != "EUR":
        return {"synced": False, "reason": f"price_currency={mc['price_currency']} incompatible"}

    new_price = float(mc["unit_price"] or 0)
    now = _now()
    linked = conn.execute(
        "SELECT id, categorie, prix_eur_m2 FROM matieres_premieres "
        "WHERE mc_material_id=?",
        (mc_id,),
    ).fetchall()

    results: list[dict[str, Any]] = []
    for mp in linked:
        if not _is_laizee(mp["categorie"]):
            results.append(
                {"mp_id": mp["id"], "synced": False, "reason": "non laizée"}
            )
            continue
        old_price = float(mp["prix_eur_m2"] or 0)
        if abs(new_price - old_price) < 1e-6:
            results.append(
                {"mp_id": mp["id"], "synced": False, "reason": "prix identique"}
            )
            continue
        conn.execute(
            "UPDATE matieres_premieres SET prix_eur_m2=?, updated_at=? WHERE id=?",
            (new_price, now, mp["id"]),
        )
        note = (
            f"Sync depuis {source_note} par {actor_name or 'système'} · "
            f"prix €/m² : {old_price if old_price else '—'} → {new_price}"
        )
        conn.execute(
            "INSERT INTO mp_valorisation_historique "
            "(matiere_id, prix_avant, prix_apres, note, created_at, created_by, created_by_name) "
            "VALUES (?,?,?,?,?,?,?)",
            (mp["id"], old_price if old_price else None, new_price, note, now, actor_id, actor_name),
        )
        results.append(
            {
                "mp_id": mp["id"],
                "synced": True,
                "old_price": old_price,
                "new_price": new_price,
            }
        )
    count = sum(1 for r in results if r.get("synced"))
    return {"synced": count > 0, "count_updated": count, "results": results}


# ─────────────────────────────────────────────────────────────────────────────
# Écran d'appairage : listes orphelines et propositions
# ─────────────────────────────────────────────────────────────────────────────


def list_orphaned_mp(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """
    Matières MyStock sans appairage mc_material_id, uniquement celles dont
    la catégorie a un rôle pricing (frontal / glassine / complexe / adhesif
    / silicone via pricing_role). Trie par catégorie puis référence.
    """
    rows = conn.execute(
        "SELECT id, categorie, reference, designation, pricing_role, "
        "       sous_section, couleur "
        "FROM matieres_premieres "
        "WHERE mc_material_id IS NULL "
        "  AND actif = 1 "
        "  AND pricing_role IS NOT NULL "
        "ORDER BY categorie, reference"
    ).fetchall()
    return [dict(r) for r in rows]


def list_orphaned_mc(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """
    Matières mc_material actives non référencées par aucun matieres_premieres.
    """
    rows = conn.execute(
        "SELECT m.id, m.name, m.appellation_code, c.code AS category_code, "
        "       m.unit_price, m.price_basis, m.price_currency "
        "FROM mc_material m "
        "JOIN mc_material_category c ON c.id = m.category_id "
        "WHERE m.is_active = 1 "
        "  AND NOT EXISTS ("
        "    SELECT 1 FROM matieres_premieres mp WHERE mp.mc_material_id = m.id"
        "  ) "
        "ORDER BY c.code, m.name"
    ).fetchall()
    return [dict(r) for r in rows]


def suggest_matches(conn: sqlite3.Connection, mp_id: int, limit: int = 5) -> list[dict[str, Any]]:
    """
    Pour une matière MyStock non appairée, retourne jusqu'à `limit`
    propositions de mc_material triées par pertinence (match nom exact,
    puis inclusion partielle, puis même catégorie).
    """
    mp = conn.execute(
        "SELECT id, categorie, reference, designation, pricing_role "
        "FROM matieres_premieres WHERE id=?",
        (mp_id,),
    ).fetchone()
    if not mp:
        return []
    ref = (mp["reference"] or "").strip().lower()
    des = (mp["designation"] or "").strip().lower()
    role = (mp["pricing_role"] or "").strip().lower()
    # Mapping pricing_role -> mc_material_category.code
    role_to_code = {
        "frontal":  "FRONTAL",
        "adhesif":  "ADHESIF",
        "silicone": "SILICONE",
        "glassine": "GLASSINE",
        "autre":    "AUTRE",
    }
    cat_code = role_to_code.get(role)
    rows = conn.execute(
        "SELECT m.id, m.name, m.appellation_code, c.code AS category_code, "
        "       m.unit_price, m.price_basis, m.price_currency "
        "FROM mc_material m "
        "JOIN mc_material_category c ON c.id = m.category_id "
        "WHERE m.is_active = 1"
    ).fetchall()

    scored: list[tuple[int, dict[str, Any]]] = []
    for r in rows:
        name = (r["name"] or "").strip().lower()
        app = (r["appellation_code"] or "").strip().lower()
        score = 0
        if ref and app and ref == app:
            score += 100
        if des and name and des == name:
            score += 80
        if ref and app and (ref in app or app in ref):
            score += 20
        if des and name and (des in name or name in des):
            score += 15
        if cat_code and r["category_code"] == cat_code:
            score += 5
        if score > 0:
            scored.append((score, dict(r)))
    scored.sort(key=lambda t: -t[0])
    return [d for _, d in scored[:limit]]
