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
    cur = conn.execute(
        """INSERT INTO mp_matiere_declinaison (matiere_id, laize_id, grammage_id)
           VALUES (?,?,?)""",
        (matiere_id, laize_id, grammage_id),
    )
    decl_id = int(cur.lastrowid)
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


def _mirror_principal(
    conn: sqlite3.Connection,
    declinaison_id: int,
    *,
    user_id: Optional[int],
    user_name: Optional[str],
    note: str,
) -> dict:
    """Recopie le prix principal dans les champs lus par la valorisation MyStock."""
    d = fetch_declinaison(conn, declinaison_id)
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
    prix = _f(row["prix"])

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
    existing = conn.execute(
        """SELECT id, principal FROM mp_matiere_prix
            WHERE declinaison_id=? AND COALESCE(fournisseur_id,0)=COALESCE(?,0)""",
        (declinaison_id, fournisseur_id),
    ).fetchone()
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
