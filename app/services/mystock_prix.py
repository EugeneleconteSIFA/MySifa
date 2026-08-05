"""
Pont Coûts matières <-> MyStock : déclinaisons et prix d'achat par fournisseur.

Le prix d'une matière MyStock n'existe qu'à un seul endroit. Ce module en est la
porte d'entrée unique, quel que soit l'écran qui écrit.

Déclinaisons
------------
Une matière MyStock se décline selon sa catégorie :

- frontal / glassine / complexe → par LAIZE ;
- adhésif                        → par GRAMMAGE (g/m²), parce qu'un même adhésif
  en 22, 25 ou 30 g/m² n'a pas le même tarif ;
- autre                          → pas de déclinaison, une seule ligne.

Les supports logistiques (mandrin, palette, carton) ne sont pas exposés : Coûts
matières sert à deviser des produits finis, pas de l'emballage.

C'est la DÉCLINAISON qui correspond à une matière de la base Coûts matières :
l'adhésif MyStock « 2028 » y existe en « 2028/22 », « 2028/25 », « 2028/30 ».
L'appairage vit donc sur `mp_matiere_declinaison.mc_material_id`.

Prix
----
`mp_matiere_prix` porte une ligne par (déclinaison, fournisseur). `principal = 1`
désigne le prix qui fait foi. Ce prix est recopié dans les champs que la
valorisation MyStock lit déjà (`matieres_premieres.prix_eur_m2`,
`mp_matiere_laizes.prix_eur_m2`, `mp_valorisation.prix_unitaire`) : aucun calcul
de valorisation existant n'a à être modifié.

Attention au prix moyen pondéré
-------------------------------
Sur une entrée de stock avec prix, MyStock recalcule un PMP et écrit dans ces
mêmes champs. Le prix d'un fournisseur est donc un TARIF, pas le PMP. On ne
pousse un tarif dans le miroir que sur action explicite : modification du prix
principal, ou désignation d'un nouveau principal.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Optional

# Doit rester aligné avec _MP_CATEGORIES_LAIZEES dans app/routers/stock.py.
CATEGORIES_LAIZEES = frozenset({"frontal", "glassine", "complexe"})
CATEGORIES_GRAMMAGE = frozenset({"adhesif"})
# Catégories visibles dans Coûts matières : tout sauf les supports logistiques.
CATEGORIES_VISIBLES = frozenset({"frontal", "glassine", "complexe", "adhesif", "autre"})


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _cat(categorie: Optional[str]) -> str:
    return (categorie or "").strip().lower()


def is_laizee(categorie: Optional[str]) -> bool:
    return _cat(categorie) in CATEGORIES_LAIZEES


def type_declinaison(categorie: Optional[str]) -> Optional[str]:
    """'LAIZE', 'GRAMMAGE' ou None si la matière ne se décline pas."""
    c = _cat(categorie)
    if c in CATEGORIES_LAIZEES:
        return "LAIZE"
    if c in CATEGORIES_GRAMMAGE:
        return "GRAMMAGE"
    return None


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def fetch_matiere(conn: sqlite3.Connection, matiere_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        """SELECT mp.id, mp.categorie, mp.reference, mp.designation, mp.actif,
                  COALESCE(mp.prix_eur_m2, 0)     AS prix_eur_m2,
                  COALESCE(mp.prix_par_laize, 0)  AS prix_par_laize,
                  COALESCE(v.prix_unitaire, 0)    AS prix_unitaire
             FROM matieres_premieres mp
             LEFT JOIN mp_valorisation v ON v.matiere_id = mp.id
            WHERE mp.id = ?""",
        (matiere_id,),
    ).fetchone()


def fetch_declinaison(conn: sqlite3.Connection, declinaison_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        """SELECT d.*, mp.categorie, mp.reference, mp.designation
             FROM mp_matiere_declinaison d
             JOIN matieres_premieres mp ON mp.id = d.matiere_id
            WHERE d.id = ?""",
        (declinaison_id,),
    ).fetchone()


# ─────────────────────────────────────────────────────────────────────────────
# Lecture
# ─────────────────────────────────────────────────────────────────────────────


def list_materials(
    conn: sqlite3.Connection,
    *,
    q: Optional[str] = None,
    categorie: Optional[str] = None,
    actives_only: bool = True,
) -> list[dict]:
    """Une entrée par matière visible, avec ses déclinaisons et leurs prix."""
    args: list[Any] = list(sorted(CATEGORIES_VISIBLES))
    placeholders = ",".join("?" for _ in CATEGORIES_VISIBLES)
    sql = f"""
        SELECT mp.id, mp.categorie, mp.reference, mp.designation, mp.actif,
               COALESCE(mp.prix_eur_m2, 0)    AS prix_eur_m2,
               COALESCE(mp.prix_par_laize, 0) AS prix_par_laize,
               COALESCE(v.prix_unitaire, 0)   AS prix_unitaire
          FROM matieres_premieres mp
          LEFT JOIN mp_valorisation v ON v.matiere_id = mp.id
         WHERE LOWER(mp.categorie) IN ({placeholders})
    """
    if actives_only:
        sql += " AND mp.actif = 1"
    if categorie:
        sql += " AND LOWER(mp.categorie) = ?"
        args.append(categorie.strip().lower())
    if q and q.strip():
        sql += " AND (mp.reference LIKE ? OR mp.designation LIKE ?)"
        pat = f"%{q.strip()}%"
        args.extend([pat, pat])
    sql += " ORDER BY mp.categorie ASC, mp.reference COLLATE NOCASE ASC"
    rows = conn.execute(sql, args).fetchall()

    decl_rows = conn.execute(
        """SELECT d.id, d.matiere_id, d.laize_id, d.grammage_id, d.mc_material_id,
                  d.weight_per_m2, d.grammage_gsm, d.perte_pct,
                  d.price_currency, d.price_basis,
                  d.taxe_pct, d.is_imported, d.applique_marge, d.transport_mode,
                  d.transport_unit_price, d.transport_pct, d.parametre,
                  l.valeur_mm, l.label AS laize_label, l.ordre AS laize_ordre,
                  g.valeur_gsm, g.label AS grammage_label,
                  mc.name AS mc_name, mc.appellation_code AS mc_appellation
             FROM mp_matiere_declinaison d
             LEFT JOIN mp_laizes   l  ON l.id = d.laize_id
             LEFT JOIN mp_grammages g ON g.id = d.grammage_id
             LEFT JOIN mc_material mc ON mc.id = d.mc_material_id
            ORDER BY l.ordre ASC, l.valeur_mm ASC, g.valeur_gsm ASC"""
    ).fetchall()

    prix_rows = conn.execute(
        """SELECT p.id, p.declinaison_id, p.fournisseur_id, p.prix, p.principal,
                  p.updated_at, p.updated_by_name,
                  f.nom AS fournisseur_nom, COALESCE(f.has_fsc, 0) AS fournisseur_fsc
             FROM mp_matiere_prix p
             LEFT JOIN fournisseurs_fsc f ON f.id = p.fournisseur_id
            WHERE p.declinaison_id IS NOT NULL
            ORDER BY p.principal DESC, f.nom COLLATE NOCASE ASC"""
    ).fetchall()
    prix_by_decl: dict[int, list[dict]] = {}
    for r in prix_rows:
        prix_by_decl.setdefault(int(r["declinaison_id"]), []).append(
            {
                "id": int(r["id"]),
                "fournisseur_id": int(r["fournisseur_id"])
                if r["fournisseur_id"] is not None
                else None,
                "fournisseur_nom": r["fournisseur_nom"],
                "fournisseur_fsc": bool(r["fournisseur_fsc"]),
                "prix": _f(r["prix"]),
                "principal": bool(r["principal"]),
                "updated_at": r["updated_at"],
                "updated_by_name": r["updated_by_name"],
            }
        )

    decl_by_mat: dict[int, list[dict]] = {}
    for r in decl_rows:
        lignes = prix_by_decl.get(int(r["id"]), [])
        principal = next((x for x in lignes if x["principal"]), None)
        if r["laize_id"] is not None:
            libelle = r["laize_label"] or (
                f"{int(r['valeur_mm'])} mm" if r["valeur_mm"] is not None else "Laize"
            )
        elif r["grammage_id"] is not None:
            libelle = r["grammage_label"] or (
                f"{_f(r['valeur_gsm']):g} g/m²" if r["valeur_gsm"] is not None else "Grammage"
            )
        else:
            libelle = "Toutes déclinaisons"
        decl_by_mat.setdefault(int(r["matiere_id"]), []).append(
            {
                "id": int(r["id"]),
                "laize_id": int(r["laize_id"]) if r["laize_id"] is not None else None,
                "grammage_id": int(r["grammage_id"]) if r["grammage_id"] is not None else None,
                "libelle": libelle,
                "mc_material_id": int(r["mc_material_id"])
                if r["mc_material_id"] is not None
                else None,
                "mc_name": r["mc_name"],
                "mc_appellation": r["mc_appellation"],
                "prix_principal": principal["prix"] if principal else None,
                "lignes": lignes,
                # Réglages de calcul portés par la déclinaison : ils suffisent à
                # en tirer un coût au m², sans fiche Coûts matières.
                "unit_price": principal["prix"] if principal else 0.0,
                "parametre": bool(_col(r, "parametre")),
                "weight_per_m2": _f(_col(r, "weight_per_m2")),
                "grammage_gsm": _f(_col(r, "grammage_gsm")),
                "perte_pct": _f(_col(r, "perte_pct")),
                "price_currency": _col(r, "price_currency") or "EUR",
                "price_basis": _col(r, "price_basis") or "PER_KG",
                "taxe_pct": _f(_col(r, "taxe_pct")),
                "is_imported": bool(_col(r, "is_imported")),
                "applique_marge": _col(r, "applique_marge") is None or bool(_col(r, "applique_marge")),
                "transport_mode": _col(r, "transport_mode") or "AMOUNT",
                "transport_unit_price": _f(_col(r, "transport_unit_price")),
                "transport_pct": _f(_col(r, "transport_pct")),
            }
        )

    out: list[dict] = []
    for r in rows:
        mid = int(r["id"])
        cat = _cat(r["categorie"])
        decls = decl_by_mat.get(mid, [])
        prix = [d["prix_principal"] for d in decls if d["prix_principal"] is not None]
        fournisseurs = {
            l["fournisseur_id"]
            for d in decls
            for l in d["lignes"]
            if l["fournisseur_id"] is not None
        }
        out.append(
            {
                "id": mid,
                "categorie": r["categorie"],
                "reference": r["reference"],
                "designation": r["designation"],
                "actif": bool(r["actif"]),
                "type_declinaison": type_declinaison(cat),
                "unite": "€/m²" if cat in CATEGORIES_LAIZEES else "€/kg"
                if cat in CATEGORIES_GRAMMAGE
                else "€/unité",
                "prix_min": min(prix) if prix else None,
                "prix_max": max(prix) if prix else None,
                "nb_declinaisons": len(decls),
                "nb_appairees": sum(1 for d in decls if d["mc_material_id"]),
                "nb_parametrees": sum(1 for d in decls if d["parametre"]),
                "nb_fournisseurs": len(fournisseurs),
                "declinaisons": decls,
            }
        )
    return out


def list_grammages(conn: sqlite3.Connection) -> list[dict]:
    return [
        {
            "id": int(r["id"]),
            "valeur_gsm": _f(r["valeur_gsm"]),
            "label": r["label"] or f"{_f(r['valeur_gsm']):g} g/m²",
        }
        for r in conn.execute(
            "SELECT id, valeur_gsm, label FROM mp_grammages WHERE actif=1 ORDER BY valeur_gsm"
        ).fetchall()
    ]


def list_laizes(conn: sqlite3.Connection) -> list[dict]:
    return [
        {
            "id": int(r["id"]),
            "valeur_mm": _f(r["valeur_mm"]),
            "label": r["label"] or f"{int(_f(r['valeur_mm']))} mm",
        }
        for r in conn.execute(
            "SELECT id, valeur_mm, label FROM mp_laizes WHERE actif=1 ORDER BY ordre, valeur_mm"
        ).fetchall()
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Déclinaisons
# ─────────────────────────────────────────────────────────────────────────────


def ensure_grammage(conn: sqlite3.Connection, valeur_gsm: float) -> int:
    """Référentiel des grammages : réutilise la valeur si elle existe déjà."""
    v = round(_f(valeur_gsm), 4)
    row = conn.execute("SELECT id FROM mp_grammages WHERE valeur_gsm=?", (v,)).fetchone()
    if row:
        return int(row["id"])
    cur = conn.execute(
        "INSERT INTO mp_grammages (valeur_gsm, label, ordre) VALUES (?,?,?)",
        (v, f"{v:g} g/m²", int(v)),
    )
    return int(cur.lastrowid)


def add_declinaison(
    conn: sqlite3.Connection,
    *,
    matiere_id: int,
    laize_id: Optional[int] = None,
    valeur_gsm: Optional[float] = None,
) -> dict:
    mat = fetch_matiere(conn, matiere_id)
    if not mat:
        return {"ok": False, "reason": "matière introuvable"}
    td = type_declinaison(mat["categorie"])
    grammage_id = None
    if td == "GRAMMAGE":
        if laize_id:
            return {"ok": False, "reason": "cette matière se décline au grammage, pas à la laize"}
        # Valeur facultative : la déclinaison peut naître vide, le grammage se
        # saisit ensuite directement dans la ligne du tableau.
        if valeur_gsm is not None and _f(valeur_gsm) > 0:
            grammage_id = ensure_grammage(conn, valeur_gsm)
            conn.execute(
                """INSERT OR IGNORE INTO mp_matiere_grammages (matiere_id, grammage_id)
                   VALUES (?,?)""",
                (matiere_id, grammage_id),
            )
        laize_id = None
    elif td == "LAIZE":
        if valeur_gsm is not None:
            return {"ok": False, "reason": "cette matière se décline à la laize, pas au grammage"}
        if laize_id and not conn.execute(
            "SELECT 1 FROM mp_laizes WHERE id=?", (laize_id,)
        ).fetchone():
            return {"ok": False, "reason": "laize inconnue"}
    else:
        return {"ok": False, "reason": "cette matière ne se décline pas"}

    exist = conn.execute(
        """SELECT id FROM mp_matiere_declinaison
            WHERE matiere_id=? AND COALESCE(laize_id,0)=COALESCE(?,0)
              AND COALESCE(grammage_id,0)=COALESCE(?,0)""",
        (matiere_id, laize_id, grammage_id),
    ).fetchone()
    if exist:
        return {
            "ok": False,
            "reason": "une déclinaison sans valeur existe déjà — renseignez-la d'abord"
            if grammage_id is None and laize_id is None
            else "cette déclinaison existe déjà",
        }
    # Réglages de départ déduits de la catégorie : une matière laizée se tarife
    # au m², un adhésif au kilo. Sans ça, une nouvelle déclinaison naîtrait en
    # €/kg avec un poids nul et afficherait un coût de 0 sans raison visible.
    cur = conn.execute(
        """INSERT INTO mp_matiere_declinaison
           (matiere_id, laize_id, grammage_id, price_basis)
           VALUES (?,?,?,?)""",
        (matiere_id, laize_id, grammage_id, "PER_M2" if td == "LAIZE" else "PER_KG"),
    )
    decl_id = int(cur.lastrowid)
    if grammage_id is not None:
        _poids_depuis_grammage(conn, decl_id, grammage_id)
    # Une déclinaison sans ligne de prix serait invisible dans le tableau : on
    # amorce une ligne vide, prête à recevoir fournisseur et prix.
    conn.execute(
        """INSERT INTO mp_matiere_prix
           (matiere_id, laize_id, grammage_id, declinaison_id, fournisseur_id,
            prix, principal, updated_at)
           VALUES (?,?,?,?,NULL,0,1,?)""",
        (matiere_id, laize_id, grammage_id, decl_id, _now()),
    )
    return {"ok": True, "declinaison_id": decl_id}


def _poids_depuis_grammage(conn: sqlite3.Connection, declinaison_id: int, grammage_id: int) -> None:
    """
    Le grammage d'une déclinaison EST son grammage de calcul.

    « 1225 en 22 g/m² » ne peut pas peser autre chose que 22 g/m² : c'est une
    seule et même information. La ligne du tableau et la fiche de paramétrage
    écrivent donc dans le même endroit — sinon la fiche annonce 25 pendant que
    la liste affiche 22, et personne ne sait laquelle fait foi.

    La perte, elle, reste propre au paramétrage : c'est ce qu'on consomme en
    plus, pas ce qu'on achète.
    """
    row = conn.execute(
        "SELECT valeur_gsm FROM mp_grammages WHERE id=?", (grammage_id,)
    ).fetchone()
    if not row or _f(row["valeur_gsm"]) <= 0:
        return
    gsm = _f(row["valeur_gsm"])
    d = conn.execute(
        "SELECT COALESCE(perte_pct,0) AS perte FROM mp_matiere_declinaison WHERE id=?",
        (declinaison_id,),
    ).fetchone()
    perte = _f(d["perte"]) if d else 0.0
    conn.execute(
        """UPDATE mp_matiere_declinaison
              SET weight_gsm=?, grammage_gsm=?, weight_per_m2=?
            WHERE id=?""",
        (int(gsm), gsm, poids_retenu(gsm, perte), declinaison_id),
    )


def set_declinaison_valeur(
    conn: sqlite3.Connection,
    *,
    declinaison_id: int,
    laize_id: Optional[int] = None,
    valeur_gsm: Optional[float] = None,
) -> dict:
    """
    Change la valeur d'une déclinaison (son grammage ou sa laize) sur place.

    Modifier plutôt que recréer : la déclinaison garde son appairage, ses prix et
    l'historique de ses fournisseurs.
    """
    d = fetch_declinaison(conn, declinaison_id)
    if not d:
        return {"ok": False, "reason": "déclinaison introuvable"}
    matiere_id = int(d["matiere_id"])
    td = type_declinaison(d["categorie"])
    if td == "GRAMMAGE":
        if valeur_gsm is None or _f(valeur_gsm) <= 0:
            return {"ok": False, "reason": "grammage invalide"}
        cible_grammage = ensure_grammage(conn, valeur_gsm)
        cible_laize = None
        conn.execute(
            "INSERT OR IGNORE INTO mp_matiere_grammages (matiere_id, grammage_id) VALUES (?,?)",
            (matiere_id, cible_grammage),
        )
    elif td == "LAIZE":
        if not laize_id:
            return {"ok": False, "reason": "laize requise"}
        if not conn.execute("SELECT 1 FROM mp_laizes WHERE id=?", (laize_id,)).fetchone():
            return {"ok": False, "reason": "laize inconnue"}
        cible_laize, cible_grammage = laize_id, None
    else:
        return {"ok": False, "reason": "cette matière ne se décline pas"}

    conflit = conn.execute(
        """SELECT 1 FROM mp_matiere_declinaison
            WHERE matiere_id=? AND id<>? AND COALESCE(laize_id,0)=COALESCE(?,0)
              AND COALESCE(grammage_id,0)=COALESCE(?,0)""",
        (matiere_id, declinaison_id, cible_laize, cible_grammage),
    ).fetchone()
    if conflit:
        return {"ok": False, "reason": "cette valeur est déjà déclinée sur cette matière"}

    conn.execute(
        "UPDATE mp_matiere_declinaison SET laize_id=?, grammage_id=? WHERE id=?",
        (cible_laize, cible_grammage, declinaison_id),
    )
    if cible_grammage is not None:
        _poids_depuis_grammage(conn, declinaison_id, cible_grammage)
    conn.execute(
        "UPDATE mp_matiere_prix SET laize_id=?, grammage_id=? WHERE declinaison_id=?",
        (cible_laize, cible_grammage, declinaison_id),
    )
    _sync_laize_fournisseurs(conn, declinaison_id)
    return {"ok": True}


def dupliquer_ligne(
    conn: sqlite3.Connection, *, declinaison_id: int, fournisseur_id: Optional[int]
) -> dict:
    """Copie une ligne de prix sur la même déclinaison, sans fournisseur."""
    src_row = conn.execute(
        """SELECT prix FROM mp_matiere_prix
            WHERE declinaison_id=? AND COALESCE(fournisseur_id,0)=COALESCE(?,0)""",
        (declinaison_id, fournisseur_id),
    ).fetchone()
    if not src_row:
        return {"ok": False, "reason": "ligne de prix introuvable"}
    if conn.execute(
        "SELECT 1 FROM mp_matiere_prix WHERE declinaison_id=? AND fournisseur_id IS NULL",
        (declinaison_id,),
    ).fetchone():
        return {"ok": False, "reason": "une ligne sans fournisseur existe déjà ici"}
    d = fetch_declinaison(conn, declinaison_id)
    conn.execute(
        """INSERT INTO mp_matiere_prix
           (matiere_id, laize_id, grammage_id, declinaison_id, fournisseur_id,
            prix, principal, updated_at)
           VALUES (?,?,?,?,NULL,?,0,?)""",
        (int(d["matiere_id"]), d["laize_id"], d["grammage_id"], declinaison_id,
         _f(src_row["prix"]), _now()),
    )
    return {"ok": True}


def delete_declinaison(conn: sqlite3.Connection, declinaison_id: int) -> dict:
    d = fetch_declinaison(conn, declinaison_id)
    if not d:
        return {"ok": False, "reason": "déclinaison introuvable"}
    conn.execute("DELETE FROM mp_matiere_prix WHERE declinaison_id=?", (declinaison_id,))
    conn.execute("DELETE FROM mp_matiere_declinaison WHERE id=?", (declinaison_id,))
    return {"ok": True}


def set_appairage(
    conn: sqlite3.Connection, *, declinaison_id: int, mc_material_id: Optional[int]
) -> dict:
    """Appaire (ou détache si mc_material_id est None) une déclinaison."""
    d = fetch_declinaison(conn, declinaison_id)
    if not d:
        return {"ok": False, "reason": "déclinaison introuvable"}
    if mc_material_id is not None:
        if not conn.execute(
            "SELECT 1 FROM mc_material WHERE id=?", (mc_material_id,)
        ).fetchone():
            return {"ok": False, "reason": "matière Coûts matières introuvable"}
        # Une matière Coûts matières ne peut être pilotée que par une déclinaison.
        conn.execute(
            "UPDATE mp_matiere_declinaison SET mc_material_id=NULL WHERE mc_material_id=? AND id<>?",
            (mc_material_id, declinaison_id),
        )
    conn.execute(
        "UPDATE mp_matiere_declinaison SET mc_material_id=? WHERE id=?",
        (mc_material_id, declinaison_id),
    )
    return {"ok": True}


# ─────────────────────────────────────────────────────────────────────────────
# Prix
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# Paramétrage de prix d'une déclinaison
# ─────────────────────────────────────────────────────────────────────────────
# Comment un prix d'achat devient un coût au m² : poids, devise, base de prix,
# incidence des taxes, transport d'import. Ces réglages vivent sur la
# déclinaison — une matière MyStock se devise sans passer par la base historique
# « Coûts matières ».

CHAMPS_PARAM = (
    "grammage_gsm",
    "perte_pct",
    "price_currency",
    "price_basis",
    "taxe_pct",
    "is_imported",
    "applique_marge",
    "transport_mode",
    "transport_unit_price",
    "transport_pct",
)

# Perte matière par défaut sur une nouvelle déclinaison, en %.
PERTE_DEFAUT = 9.0


def poids_retenu(grammage_gsm: Any, perte_pct: Any) -> float:
    """
    Poids au m² (kg) réellement consommé : le grammage majoré de la perte.

    On produit rarement au gramme près — la chute et le déchet de calage font
    qu'un frontal de 70 g/m² en consomme davantage. C'est ce poids-là qui doit
    entrer dans le prix de revient, pas le grammage théorique.
    """
    g = _f(grammage_gsm)
    p = _f(perte_pct)
    return round(g * (1 + p / 100.0) / 1000.0, 6)

_DEVISES = ("EUR", "USD")
_BASES = ("PER_KG", "PER_M2")
_MODES_TRANSPORT = ("AMOUNT", "PCT")


def libelle_declinaison(row: Any) -> str:
    """« 330 mm », « 22 g/m² », ou « Toutes déclinaisons » si la valeur manque."""
    laize_id = _col(row, "laize_id")
    gram_id = _col(row, "grammage_id")
    if laize_id is not None:
        return _col(row, "laize_label") or (
            f"{int(_f(_col(row, 'valeur_mm')))} mm" if _col(row, "valeur_mm") is not None else "Laize"
        )
    if gram_id is not None:
        return _col(row, "grammage_label") or (
            f"{_f(_col(row, 'valeur_gsm')):g} g/m²" if _col(row, "valeur_gsm") is not None else "Grammage"
        )
    return "Toutes déclinaisons"


def _col(row: Any, nom: str, defaut: Any = None) -> Any:
    """Lecture tolérante : la même fonction sert sur un sqlite3.Row et un dict."""
    if isinstance(row, dict):
        return row.get(nom, defaut)
    try:
        return row[nom]
    except (IndexError, KeyError):
        return defaut


def fetch_declinaison_complete(conn: sqlite3.Connection, declinaison_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        """SELECT d.*, mp.categorie, mp.reference, mp.designation,
                  mp.actif AS matiere_active,
                  l.valeur_mm, l.label AS laize_label,
                  g.valeur_gsm, g.label AS grammage_label
             FROM mp_matiere_declinaison d
             JOIN matieres_premieres mp ON mp.id = d.matiere_id
             LEFT JOIN mp_laizes    l ON l.id = d.laize_id
             LEFT JOIN mp_grammages g ON g.id = d.grammage_id
            WHERE d.id = ?""",
        (declinaison_id,),
    ).fetchone()


def parametrage(conn: sqlite3.Connection, declinaison_id: int) -> Optional[dict]:
    """Fiche complète d'une déclinaison : identité, prix d'achat, réglages."""
    d = fetch_declinaison_complete(conn, declinaison_id)
    if not d:
        return None
    lignes = [
        {
            "fournisseur_id": int(r["fournisseur_id"]) if r["fournisseur_id"] is not None else None,
            "fournisseur_nom": r["fournisseur_nom"],
            "prix": _f(r["prix"]),
            "principal": bool(r["principal"]),
            "updated_at": r["updated_at"],
            "updated_by_name": r["updated_by_name"],
        }
        for r in conn.execute(
            """SELECT p.fournisseur_id, p.prix, p.principal, p.updated_at, p.updated_by_name,
                      f.nom AS fournisseur_nom
                 FROM mp_matiere_prix p
                 LEFT JOIN fournisseurs_fsc f ON f.id = p.fournisseur_id
                WHERE p.declinaison_id = ?
                ORDER BY p.principal DESC, f.nom COLLATE NOCASE ASC""",
            (declinaison_id,),
        ).fetchall()
    ]
    principal = next((x for x in lignes if x["principal"]), None)
    cat = _cat(d["categorie"])
    return {
        "declinaison_id": int(d["id"]),
        "matiere_id": int(d["matiere_id"]),
        "reference": d["reference"],
        "designation": d["designation"],
        "categorie": d["categorie"],
        "matiere_active": bool(d["matiere_active"]),
        "type_declinaison": type_declinaison(cat),
        "libelle": libelle_declinaison(d),
        "unit_price": principal["prix"] if principal else 0.0,
        # Ce que la valorisation MyStock affiche pour cette matière.
        "sous_total_achat": sous_total_achat(
            principal["prix"] if principal else 0, **_reglages_declinaison(d)
        ),
        "fournisseur_nom": principal["fournisseur_nom"] if principal else None,
        "prix_updated_at": principal["updated_at"] if principal else None,
        "lignes_prix": lignes,
        "parametre": bool(_col(d, "parametre")),
        "updated_at": _col(d, "updated_at"),
        "updated_by_name": _col(d, "updated_by_name"),
        "weight_per_m2": _f(_col(d, "weight_per_m2")),
        "grammage_gsm": _f(_col(d, "grammage_gsm")),
        "perte_pct": _f(_col(d, "perte_pct")),
        "price_currency": _col(d, "price_currency") or "EUR",
        "price_basis": _col(d, "price_basis") or "PER_KG",
        "taxe_pct": _f(_col(d, "taxe_pct")),
        "is_imported": bool(_col(d, "is_imported")),
        "applique_marge": _col(d, "applique_marge") is None or bool(_col(d, "applique_marge")),
        "transport_mode": _col(d, "transport_mode") or "AMOUNT",
        "transport_unit_price": _f(_col(d, "transport_unit_price")),
        "transport_pct": _f(_col(d, "transport_pct")),
    }


def set_parametrage(
    conn: sqlite3.Connection,
    *,
    declinaison_id: int,
    patch: dict,
    user_name: Optional[str] = None,
) -> dict:
    """
    Enregistre les réglages de calcul d'une déclinaison.

    Seuls les champs présents dans `patch` bougent : la page peut n'envoyer que
    ce que l'utilisateur a touché. Les valeurs hors domaine sont refusées plutôt
    que corrigées en silence — un « PER_M3 » accepté puis ignoré donnerait un
    coût faux sans le dire.
    """
    actuelle = fetch_declinaison_complete(conn, declinaison_id)
    if not actuelle:
        return {"ok": False, "reason": "déclinaison introuvable"}

    # Sur un adhésif, le grammage saisi ici EST la valeur de la déclinaison :
    # le changer déplace la déclinaison, exactement comme dans le tableau. Sans
    # ça, la fiche et la ligne afficheraient deux grammages différents.
    if "grammage_gsm" in patch and type_declinaison(actuelle["categorie"]) == "GRAMMAGE":
        cible = _f(patch["grammage_gsm"])
        if cible != _f(_col(actuelle, "grammage_gsm")) or actuelle["grammage_id"] is None:
            if cible <= 0:
                return {"ok": False, "reason": "grammage invalide"}
            res = set_declinaison_valeur(
                conn, declinaison_id=declinaison_id, valeur_gsm=cible
            )
            if not res.get("ok"):
                return res

    sets: list[str] = []
    args: list[Any] = []

    def poser(champ, valeur):
        sets.append(f"{champ}=?")
        args.append(valeur)

    if "price_currency" in patch:
        v = str(patch["price_currency"] or "").upper()
        if v not in _DEVISES:
            return {"ok": False, "reason": f"devise inconnue : {v or '(vide)'}"}
        poser("price_currency", v)
    if "price_basis" in patch:
        v = str(patch["price_basis"] or "").upper()
        if v not in _BASES:
            return {"ok": False, "reason": f"base de prix inconnue : {v or '(vide)'}"}
        poser("price_basis", v)
    if "transport_mode" in patch:
        v = str(patch["transport_mode"] or "").upper()
        if v not in _MODES_TRANSPORT:
            return {"ok": False, "reason": f"mode de transport inconnu : {v or '(vide)'}"}
        poser("transport_mode", v)

    for champ, mini, maxi in (
        ("grammage_gsm", 0, 99999),
        ("perte_pct", 0, 100),
        ("taxe_pct", -100, 1000),
        ("transport_unit_price", 0, 1_000_000),
        ("transport_pct", 0, 1000),
    ):
        if champ in patch:
            v = _f(patch[champ], None)
            if v is None or v < mini or v > maxi:
                return {"ok": False, "reason": f"{champ} hors limites"}
            poser(champ, v)

    if "is_imported" in patch:
        poser("is_imported", 1 if patch["is_imported"] else 0)
    if "applique_marge" in patch:
        poser("applique_marge", 1 if patch["applique_marge"] else 0)

    if not sets:
        return {"ok": False, "reason": "aucun réglage à modifier"}

    # Le poids n'est pas saisi : il découle du grammage et de la perte. Le
    # recalculer ici garantit qu'aucun écran ne peut enregistrer un poids
    # incohérent avec ce qui est affiché.
    actuel = fetch_declinaison_complete(conn, declinaison_id)
    g = patch.get("grammage_gsm", _col(actuel, "grammage_gsm"))
    p = patch.get("perte_pct", _col(actuel, "perte_pct"))
    poser("weight_per_m2", poids_retenu(g, p))
    poser("weight_gsm", int(_f(g)) if _f(g) > 0 else None)

    poser("parametre", 1)
    poser("updated_at", _now())
    poser("updated_by_name", user_name)
    args.append(declinaison_id)
    st_avant = sous_total_declinaison(conn, declinaison_id)
    conn.execute(
        f"UPDATE mp_matiere_declinaison SET {', '.join(sets)} WHERE id=?", args
    )
    # Transport et taxes déplacent le sous-total sans toucher au prix d'achat :
    # la valorisation MyStock doit suivre, et l'historique doit le dire.
    st_apres = sous_total_declinaison(conn, declinaison_id)
    if abs(st_avant - st_apres) > 1e-9:
        prix_row = conn.execute(
            "SELECT prix FROM mp_matiere_prix WHERE declinaison_id=? AND principal=1 LIMIT 1",
            (declinaison_id,),
        ).fetchone()
        prix = _f(prix_row["prix"]) if prix_row else None
        journaliser_prix(
            conn, declinaison_id=declinaison_id,
            prix_avant=prix, prix_apres=prix,
            sous_total_avant=st_avant, sous_total_apres=st_apres,
            origine="Coûts matières — paramétrage",
            note="transport / taxes modifiés", user_name=user_name,
        )
        _mirror_principal(
            conn, declinaison_id, user_id=None, user_name=user_name,
            note="Paramétrage modifié depuis Coûts matières",
        )
    return {"ok": True, "parametrage": parametrage(conn, declinaison_id)}


# ─────────────────────────────────────────────────────────────────────────────
# Sous-total d'achat — la valeur commune aux deux applications
# ─────────────────────────────────────────────────────────────────────────────
# Coûts matières saisit un PRIX D'ACHAT fournisseur, auquel s'ajoutent le
# transport d'import et les taxes. La valorisation MyStock, elle, raisonne sur ce
# que la matière coûte rendue : c'est le SOUS-TOTAL D'ACHAT.
#
# C'est donc lui qui circule entre les deux écrans, pas le prix nu. Les deux sens
# passent par les deux fonctions ci-dessous, qui sont l'inverse l'une de l'autre.


def sous_total_achat(
    prix: Any,
    *,
    is_imported: Any = False,
    transport_mode: Optional[str] = "AMOUNT",
    transport_unit_price: Any = 0,
    transport_pct: Any = 0,
    taxe_pct: Any = 0,
) -> float:
    """Prix d'achat + transport + taxes, dans la devise et la base d'achat."""
    p = _f(prix)
    if not is_imported:
        return round(p, 6)
    if (transport_mode or "AMOUNT").upper() == "PCT":
        transport = p * _f(transport_pct) / 100.0
    else:
        transport = _f(transport_unit_price)
    return round((p + transport) * (1 + _f(taxe_pct) / 100.0), 6)


def prix_depuis_sous_total(
    sous_total: Any,
    *,
    is_imported: Any = False,
    transport_mode: Optional[str] = "AMOUNT",
    transport_unit_price: Any = 0,
    transport_pct: Any = 0,
    taxe_pct: Any = 0,
) -> Optional[float]:
    """
    Chemin inverse : de la valeur affichée en valorisation au prix fournisseur.

    Renvoie None quand la décomposition n'a pas de solution acceptable — un
    sous-total inférieur au seul transport, par exemple. Mieux vaut refuser que
    d'inscrire un prix d'achat négatif que personne ne comprendrait.
    """
    st = _f(sous_total)
    if not is_imported:
        return round(st, 6) if st >= 0 else None
    facteur_taxe = 1 + _f(taxe_pct) / 100.0
    if facteur_taxe <= 0:
        return None
    hors_taxe = st / facteur_taxe
    if (transport_mode or "AMOUNT").upper() == "PCT":
        facteur_transport = 1 + _f(transport_pct) / 100.0
        if facteur_transport <= 0:
            return None
        p = hors_taxe / facteur_transport
    else:
        p = hors_taxe - _f(transport_unit_price)
    return round(p, 6) if p >= 0 else None


def _reglages_declinaison(row: Any) -> dict:
    """Les réglages qui font passer du prix d'achat au sous-total."""
    return {
        "is_imported": bool(_col(row, "is_imported")),
        "transport_mode": _col(row, "transport_mode") or "AMOUNT",
        "transport_unit_price": _f(_col(row, "transport_unit_price")),
        "transport_pct": _f(_col(row, "transport_pct")),
        "taxe_pct": _f(_col(row, "taxe_pct")),
    }


def sous_total_declinaison(conn: sqlite3.Connection, declinaison_id: int,
                           prix: Optional[Any] = None) -> float:
    """Sous-total d'une déclinaison, à partir de son prix principal par défaut."""
    d = fetch_declinaison_complete(conn, declinaison_id)
    if not d:
        return 0.0
    if prix is None:
        row = conn.execute(
            "SELECT prix FROM mp_matiere_prix WHERE declinaison_id=? AND principal=1 LIMIT 1",
            (declinaison_id,),
        ).fetchone()
        prix = row["prix"] if row else 0
    return sous_total_achat(prix, **_reglages_declinaison(d))


def journaliser_prix(
    conn: sqlite3.Connection,
    *,
    declinaison_id: int,
    fournisseur_id: Optional[int] = None,
    prix_avant: Optional[float] = None,
    prix_apres: Optional[float] = None,
    sous_total_avant: Optional[float] = None,
    sous_total_apres: Optional[float] = None,
    origine: str,
    note: Optional[str] = None,
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
) -> None:
    """
    Trace un mouvement de prix, avec l'écran d'où il vient.

    Rien n'est écrit si ni le prix ni le sous-total n'ont bougé : l'historique
    doit se lire, pas se dérouler.
    """
    bouge = (
        prix_avant is None
        or abs(_f(prix_avant) - _f(prix_apres)) > 1e-9
        or abs(_f(sous_total_avant) - _f(sous_total_apres)) > 1e-9
    )
    if not bouge:
        return
    d = fetch_declinaison_complete(conn, declinaison_id)
    conn.execute(
        """INSERT INTO mp_prix_historique
           (declinaison_id, matiere_id, fournisseur_id, prix_avant, prix_apres,
            sous_total_avant, sous_total_apres, origine, note,
            created_at, created_by, created_by_name)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            declinaison_id,
            int(d["matiere_id"]) if d else None,
            fournisseur_id,
            prix_avant, prix_apres, sous_total_avant, sous_total_apres,
            origine, note, _now(), user_id, user_name,
        ),
    )


def historique_prix(conn: sqlite3.Connection, declinaison_id: int, limite: int = 50) -> list[dict]:
    rows = conn.execute(
        """SELECT h.*, f.nom AS fournisseur_nom
             FROM mp_prix_historique h
             LEFT JOIN fournisseurs_fsc f ON f.id = h.fournisseur_id
            WHERE h.declinaison_id = ?
            ORDER BY h.created_at DESC, h.id DESC
            LIMIT ?""",
        (declinaison_id, int(limite)),
    ).fetchall()
    return [
        {
            "date": r["created_at"],
            "origine": r["origine"],
            "auteur": r["created_by_name"],
            "fournisseur_nom": r["fournisseur_nom"],
            "prix_avant": _f(r["prix_avant"]) if r["prix_avant"] is not None else None,
            "prix_apres": _f(r["prix_apres"]) if r["prix_apres"] is not None else None,
            "sous_total_avant": _f(r["sous_total_avant"]) if r["sous_total_avant"] is not None else None,
            "sous_total_apres": _f(r["sous_total_apres"]) if r["sous_total_apres"] is not None else None,
            "note": r["note"],
        }
        for r in rows
    ]


def _mirror_principal(
    conn: sqlite3.Connection,
    declinaison_id: int,
    *,
    user_id: Optional[int],
    user_name: Optional[str],
    note: str,
) -> dict:
    """
    Pousse le SOUS-TOTAL D'ACHAT dans les champs lus par la valorisation MyStock.

    Pas le prix nu : la valorisation raisonne sur ce que la matière coûte rendue,
    transport d'import et taxes compris. C'est cette valeur-là qui doit
    apparaître des deux côtés, sinon les deux écrans affichent deux chiffres
    différents pour la même matière.
    """
    d = fetch_declinaison_complete(conn, declinaison_id)
    if not d:
        return {"ok": False, "reason": "déclinaison introuvable"}
    matiere_id = int(d["matiere_id"])
    mat = fetch_matiere(conn, matiere_id)
    row = conn.execute(
        "SELECT prix FROM mp_matiere_prix WHERE declinaison_id=? AND principal=1 LIMIT 1",
        (declinaison_id,),
    ).fetchone()
    if not row:
        return {"ok": False, "reason": "aucun prix principal"}
    prix = sous_total_achat(row["prix"], **_reglages_declinaison(d))

    laizee = is_laizee(mat["categorie"])
    par_laize = bool(int(mat["prix_par_laize"] or 0)) and laizee
    laize_id = d["laize_id"]
    now = _now()

    if laizee and par_laize and laize_id is not None:
        prev = conn.execute(
            "SELECT prix_eur_m2 FROM mp_matiere_laizes WHERE matiere_id=? AND laize_id=?",
            (matiere_id, laize_id),
        ).fetchone()
        avant = _f(prev["prix_eur_m2"]) if prev else None
        conn.execute(
            "UPDATE mp_matiere_laizes SET prix_eur_m2=? WHERE matiere_id=? AND laize_id=?",
            (prix, matiere_id, laize_id),
        )
        cible = "prix laize"
    elif laizee:
        avant = _f(mat["prix_eur_m2"])
        conn.execute(
            "UPDATE matieres_premieres SET prix_eur_m2=?, "
            "updated_at=strftime('%Y-%m-%dT%H:%M:%S','now','localtime') WHERE id=?",
            (prix, matiere_id),
        )
        cible = "prix matière"
    else:
        prev = conn.execute(
            "SELECT prix_unitaire FROM mp_valorisation WHERE matiere_id=?", (matiere_id,)
        ).fetchone()
        avant = _f(prev["prix_unitaire"]) if prev else None
        if prev:
            conn.execute(
                """UPDATE mp_valorisation SET prix_unitaire=?, updated_at=?, updated_by_name=?
                    WHERE matiere_id=?""",
                (prix, now, user_name, matiere_id),
            )
        else:
            conn.execute(
                """INSERT INTO mp_valorisation
                   (matiere_id, prix_unitaire, updated_at, updated_by_name)
                   VALUES (?,?,?,?)""",
                (matiere_id, prix, now, user_name),
            )
        cible = "prix unitaire"

    changed = avant is None or abs(_f(avant) - prix) > 1e-9
    if changed:
        conn.execute(
            """INSERT INTO mp_valorisation_historique
               (matiere_id, prix_avant, prix_apres, note, created_at, created_by, created_by_name)
               VALUES (?,?,?,?,?,?,?)""",
            (matiere_id, avant, prix, note, now, user_id, user_name),
        )
    return {"ok": True, "cible": cible, "prix_avant": avant, "prix_apres": prix, "changed": changed}


def _prix_mystock_de_reference(
    conn: sqlite3.Connection, mat: sqlite3.Row, laize_id: Optional[int]
) -> float:
    """
    Le prix qui fait foi côté MyStock pour une déclinaison donnée.

    Miroir exact de la cible choisie par `_mirror_principal` : on relit le champ
    dans lequel ce dernier écrirait, pour que les deux sens parlent du même
    endroit.
    """
    laizee = is_laizee(mat["categorie"])
    par_laize = bool(int(mat["prix_par_laize"] or 0)) and laizee
    if laizee and par_laize and laize_id is not None:
        row = conn.execute(
            "SELECT prix_eur_m2 FROM mp_matiere_laizes WHERE matiere_id=? AND laize_id=?",
            (int(mat["id"]), int(laize_id)),
        ).fetchone()
        return _f(row["prix_eur_m2"]) if row else 0.0
    if laizee:
        return _f(mat["prix_eur_m2"])
    return _f(mat["prix_unitaire"])


def resync_depuis_mystock(
    conn: sqlite3.Connection,
    matiere_id: int,
    *,
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
    origine: str = "MyStock",
) -> dict:
    """
    MyStock -> Coûts matières : le sens retour de `_mirror_principal`.

    Coûts matières lit le prix d'une matière appairée dans la ligne principale de
    `mp_matiere_prix`. Un prix corrigé côté MyStock — saisie sur la valorisation,
    prix par laize de la fiche matière, PMP recalculé à l'entrée en stock — doit
    donc redescendre dans cette ligne, sans quoi Coûts matières continue
    d'afficher l'ancienne valeur.

    Le prix n'est pas passé en paramètre : la fonction relit elle-même le champ
    qui fait foi pour chaque déclinaison. L'appelant n'a qu'à signaler que la
    matière a bougé, il ne peut pas se tromper de champ.

    Un prix à 0 ne remplace rien : côté MyStock il veut dire « pas encore
    renseigné », pas « gratuit ». Écraser un tarif connu avec un zéro ferait
    disparaître le prix de revient d'un produit.
    """
    mat = fetch_matiere(conn, matiere_id)
    if not mat:
        return {"ok": False, "reason": "matière introuvable"}

    declinaisons = conn.execute(
        "SELECT id, laize_id FROM mp_matiere_declinaison WHERE matiere_id=?",
        (matiere_id,),
    ).fetchall()
    if not declinaisons:
        return {"ok": True, "declinaisons": 0, "mises_a_jour": 0}

    now = _now()
    note = f"Prix repris depuis {origine}"
    mises_a_jour = 0

    for d in declinaisons:
        # Côté MyStock, la valeur affichée est un SOUS-TOTAL : on remonte au prix
        # d'achat en retirant transport et taxes, sinon on écrirait un tarif
        # fournisseur gonflé de ses propres frais.
        sous_total = _prix_mystock_de_reference(conn, mat, d["laize_id"])
        if sous_total <= 0 or sous_total > 1_000_000:
            continue
        decl_id = int(d["id"])
        complete = fetch_declinaison_complete(conn, decl_id)
        prix = prix_depuis_sous_total(sous_total, **_reglages_declinaison(complete))
        if prix is None:
            # Le sous-total ne couvre même pas le transport : on ne devine pas.
            continue

        ligne = conn.execute(
            "SELECT id, prix FROM mp_matiere_prix WHERE declinaison_id=? AND principal=1 LIMIT 1",
            (decl_id,),
        ).fetchone()
        if ligne is None:
            # Pas de principal désigné : on promeut la première ligne existante
            # plutôt que d'en créer une seconde sans fournisseur.
            ligne = conn.execute(
                "SELECT id, prix FROM mp_matiere_prix WHERE declinaison_id=? ORDER BY id LIMIT 1",
                (decl_id,),
            ).fetchone()
            if ligne is not None:
                conn.execute(
                    "UPDATE mp_matiere_prix SET principal=1 WHERE id=?", (int(ligne["id"]),)
                )

        if ligne is None:
            conn.execute(
                """INSERT INTO mp_matiere_prix
                   (matiere_id, laize_id, grammage_id, declinaison_id, fournisseur_id,
                    prix, principal, note, updated_at, updated_by_name)
                   VALUES (?,?,?,?,NULL,?,1,?,?,?)""",
                (matiere_id, d["laize_id"], None, decl_id, prix, note, now, user_name),
            )
            mises_a_jour += 1
            continue

        if abs(_f(ligne["prix"]) - prix) <= 1e-9:
            continue  # déjà à la bonne valeur : ni écriture ni bruit dans l'historique
        avant = _f(ligne["prix"])
        conn.execute(
            """UPDATE mp_matiere_prix
                  SET prix=?, note=?, updated_at=?, updated_by_name=?
                WHERE id=?""",
            (prix, note, now, user_name, int(ligne["id"])),
        )
        journaliser_prix(
            conn, declinaison_id=decl_id,
            prix_avant=avant, prix_apres=prix,
            sous_total_avant=sous_total_achat(avant, **_reglages_declinaison(complete)),
            sous_total_apres=sous_total,
            origine=origine, user_id=user_id, user_name=user_name,
        )
        mises_a_jour += 1

    return {
        "ok": True,
        "declinaisons": len(declinaisons),
        "mises_a_jour": mises_a_jour,
    }


def set_prix(
    conn: sqlite3.Connection,
    *,
    declinaison_id: int,
    fournisseur_id: Optional[int],
    prix: float,
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
    origine: str = "Coûts matières",
) -> dict:
    if prix < 0:
        return {"ok": False, "reason": "prix négatif interdit"}
    if prix > 1_000_000:
        return {"ok": False, "reason": "prix hors limites"}
    d = fetch_declinaison(conn, declinaison_id)
    if not d:
        return {"ok": False, "reason": "déclinaison introuvable"}

    now = _now()
    complete = fetch_declinaison_complete(conn, declinaison_id)
    reglages = _reglages_declinaison(complete)
    existing = conn.execute(
        """SELECT id, principal, prix FROM mp_matiere_prix
            WHERE declinaison_id=? AND COALESCE(fournisseur_id,0)=COALESCE(?,0)""",
        (declinaison_id, fournisseur_id),
    ).fetchone()
    avant = _f(existing["prix"]) if existing else None
    if existing:
        conn.execute(
            "UPDATE mp_matiere_prix SET prix=?, updated_at=?, updated_by_name=? WHERE id=?",
            (float(prix), now, user_name, existing["id"]),
        )
        principal = bool(existing["principal"])
    else:
        others = conn.execute(
            "SELECT COUNT(*) AS n FROM mp_matiere_prix WHERE declinaison_id=?",
            (declinaison_id,),
        ).fetchone()
        principal = int(others["n"] or 0) == 0
        conn.execute(
            """INSERT INTO mp_matiere_prix
               (matiere_id, laize_id, grammage_id, declinaison_id, fournisseur_id,
                prix, principal, updated_at, updated_by_name)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                int(d["matiere_id"]), d["laize_id"], d["grammage_id"], declinaison_id,
                fournisseur_id, float(prix), 1 if principal else 0, now, user_name,
            ),
        )
    # Un prix à zéro n'est pas un prix de référence : si le principal actuel est
    # vide et que cette ligne porte enfin un montant, elle prend la main. Sans
    # ça, la ligne amorcée à la création d'une déclinaison resterait principale
    # à 0 € et la matière n'aurait aucun prix en vigueur.
    if not principal and prix > 0:
        actuel = conn.execute(
            "SELECT prix FROM mp_matiere_prix WHERE declinaison_id=? AND principal=1 LIMIT 1",
            (declinaison_id,),
        ).fetchone()
        if not actuel or _f(actuel["prix"]) <= 0:
            conn.execute(
                "UPDATE mp_matiere_prix SET principal=0 WHERE declinaison_id=?",
                (declinaison_id,),
            )
            conn.execute(
                """UPDATE mp_matiere_prix SET principal=1
                    WHERE declinaison_id=? AND COALESCE(fournisseur_id,0)=COALESCE(?,0)""",
                (declinaison_id, fournisseur_id),
            )
            principal = True

    journaliser_prix(
        conn, declinaison_id=declinaison_id, fournisseur_id=fournisseur_id,
        prix_avant=avant, prix_apres=float(prix),
        sous_total_avant=sous_total_achat(avant, **reglages) if avant is not None else None,
        sous_total_apres=sous_total_achat(prix, **reglages),
        origine=origine, user_id=user_id, user_name=user_name,
    )
    result = {"ok": True, "principal": principal}
    if principal:
        result["miroir"] = _mirror_principal(
            conn, declinaison_id, user_id=user_id, user_name=user_name,
            note=f"Prix modifié depuis {origine}",
        )
    _sync_laize_fournisseurs(conn, declinaison_id)
    return result


def set_fournisseur(
    conn: sqlite3.Connection,
    *,
    declinaison_id: int,
    fournisseur_id: Optional[int],
    nouveau_fournisseur_id: Optional[int],
) -> dict:
    """
    Change le fournisseur d'une ligne de prix existante, sur place.

    On ne recrée pas la ligne : la remplacer ferait perdre son statut de
    principal, et une déclinaison se retrouverait sans prix de référence.
    """
    row = conn.execute(
        """SELECT id FROM mp_matiere_prix
            WHERE declinaison_id=? AND COALESCE(fournisseur_id,0)=COALESCE(?,0)""",
        (declinaison_id, fournisseur_id),
    ).fetchone()
    if not row:
        return {"ok": False, "reason": "ligne de prix introuvable"}
    if (fournisseur_id or 0) == (nouveau_fournisseur_id or 0):
        return {"ok": True, "inchange": True}
    deja = conn.execute(
        """SELECT 1 FROM mp_matiere_prix
            WHERE declinaison_id=? AND COALESCE(fournisseur_id,0)=COALESCE(?,0)""",
        (declinaison_id, nouveau_fournisseur_id),
    ).fetchone()
    if deja:
        return {"ok": False, "reason": "ce fournisseur a déjà un prix sur cette déclinaison"}
    conn.execute(
        "UPDATE mp_matiere_prix SET fournisseur_id=?, updated_at=? WHERE id=?",
        (nouveau_fournisseur_id, _now(), row["id"]),
    )
    _sync_laize_fournisseurs(conn, declinaison_id)
    return {"ok": True}


def set_principal(
    conn: sqlite3.Connection,
    *,
    declinaison_id: int,
    fournisseur_id: Optional[int],
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
    origine: str = "Coûts matières",
) -> dict:
    row = conn.execute(
        """SELECT id FROM mp_matiere_prix
            WHERE declinaison_id=? AND COALESCE(fournisseur_id,0)=COALESCE(?,0)""",
        (declinaison_id, fournisseur_id),
    ).fetchone()
    if not row:
        return {"ok": False, "reason": "ligne de prix introuvable"}
    conn.execute(
        "UPDATE mp_matiere_prix SET principal=0 WHERE declinaison_id=?", (declinaison_id,)
    )
    conn.execute("UPDATE mp_matiere_prix SET principal=1 WHERE id=?", (row["id"],))
    miroir = _mirror_principal(
        conn, declinaison_id, user_id=user_id, user_name=user_name,
        note=f"Fournisseur principal changé depuis {origine}",
    )
    _sync_laize_fournisseurs(conn, declinaison_id)
    return {"ok": True, "miroir": miroir}


def delete_ligne(
    conn: sqlite3.Connection, *, declinaison_id: int, fournisseur_id: Optional[int]
) -> dict:
    row = conn.execute(
        """SELECT id, principal FROM mp_matiere_prix
            WHERE declinaison_id=? AND COALESCE(fournisseur_id,0)=COALESCE(?,0)""",
        (declinaison_id, fournisseur_id),
    ).fetchone()
    if not row:
        return {"ok": False, "reason": "ligne de prix introuvable"}
    reste = conn.execute(
        "SELECT COUNT(*) AS n FROM mp_matiere_prix WHERE declinaison_id=?", (declinaison_id,)
    ).fetchone()
    derniere = int(reste["n"] or 0) <= 1
    if int(row["principal"] or 0) and not derniere:
        return {
            "ok": False,
            "reason": "fournisseur principal — désignez-en un autre avant de le retirer",
        }
    conn.execute("DELETE FROM mp_matiere_prix WHERE id=?", (row["id"],))
    if derniere:
        # Plus aucun prix : la déclinaison n'a plus de raison d'exister.
        conn.execute("DELETE FROM mp_matiere_declinaison WHERE id=?", (declinaison_id,))
        return {"ok": True, "declinaison_supprimee": True}
    _sync_laize_fournisseurs(conn, declinaison_id)
    return {"ok": True}


def _sync_laize_fournisseurs(conn: sqlite3.Connection, declinaison_id: int) -> None:
    """
    Tient à jour matiere_laize_fournisseurs, encore lue par les écrans MyStock
    (réception, guide traça). Ne concerne que les déclinaisons par laize.
    """
    d = fetch_declinaison(conn, declinaison_id)
    if not d or d["laize_id"] is None:
        return
    matiere_id, laize_id = int(d["matiere_id"]), int(d["laize_id"])
    conn.execute(
        "DELETE FROM matiere_laize_fournisseurs WHERE matiere_id=? AND laize_id=?",
        (matiere_id, laize_id),
    )
    for r in conn.execute(
        """SELECT DISTINCT fournisseur_id FROM mp_matiere_prix
            WHERE declinaison_id=? AND fournisseur_id IS NOT NULL""",
        (declinaison_id,),
    ).fetchall():
        conn.execute(
            """INSERT OR IGNORE INTO matiere_laize_fournisseurs
               (matiere_id, laize_id, fournisseur_id) VALUES (?,?,?)""",
            (matiere_id, laize_id, int(r["fournisseur_id"])),
        )
