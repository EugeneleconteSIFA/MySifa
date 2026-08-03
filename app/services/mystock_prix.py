"""
Pont Coûts matières <-> MyStock : prix d'achat par fournisseur.

Le prix d'une matière MyStock n'existe qu'à un seul endroit. Ce module en est
la porte d'entrée unique, quel que soit l'écran qui écrit (MyStock ou Coûts
matières).

Modèle
------
`mp_matiere_prix` porte une ligne par (matière, laize, fournisseur) :

- `laize_id` NULL  → matière non laizée, ou matière laizée à prix unique.
- `fournisseur_id` NULL → prix connu sans fournisseur désigné.
- `principal = 1`  → le prix qui fait foi pour cette matière/laize.

Miroir
------
Le prix principal est recopié dans les champs que la valorisation MyStock lit
déjà (`matieres_premieres.prix_eur_m2`, `mp_matiere_laizes.prix_eur_m2`,
`mp_valorisation.prix_unitaire`). Aucun calcul de valorisation existant n'a donc
à être modifié : ces champs restent la source de vérité pour eux.

Attention au prix moyen pondéré
-------------------------------
Sur une entrée de stock avec prix, MyStock recalcule un PMP et écrit dans ces
mêmes champs. Le prix d'un fournisseur est donc un TARIF (dernier prix d'achat
connu), pas le PMP. On ne pousse un tarif dans le miroir que sur action
explicite : modification du prix principal, ou désignation d'un nouveau
principal. Une réception de stock reste libre de faire évoluer le PMP ensuite.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Optional

# Doit rester aligné avec _MP_CATEGORIES_LAIZEES dans app/routers/stock.py.
_LAIZEES = frozenset({"frontal", "glassine", "complexe"})


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def is_laizee(categorie: Optional[str]) -> bool:
    return (categorie or "").strip().lower() in _LAIZEES


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
                  mp.mc_material_id,
                  COALESCE(v.prix_unitaire, 0)    AS prix_unitaire
             FROM matieres_premieres mp
             LEFT JOIN mp_valorisation v ON v.matiere_id = mp.id
            WHERE mp.id = ?""",
        (matiere_id,),
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
    """
    Une entrée par matière MyStock, avec le détail de ses lignes de prix.

    Chaque matière porte :
      - `prix_principal` : le prix qui fait foi (None si la matière est laizée
        avec un prix par laize — dans ce cas le prix vit sur chaque ligne) ;
      - `lignes` : les prix, une par (laize, fournisseur).
    """
    args: list[Any] = []
    sql = """
        SELECT mp.id, mp.categorie, mp.reference, mp.designation, mp.actif,
               COALESCE(mp.prix_eur_m2, 0)    AS prix_eur_m2,
               COALESCE(mp.prix_par_laize, 0) AS prix_par_laize,
               mp.mc_material_id,
               COALESCE(v.prix_unitaire, 0)   AS prix_unitaire,
               mc.name                        AS mc_name
          FROM matieres_premieres mp
          LEFT JOIN mp_valorisation v ON v.matiere_id = mp.id
          LEFT JOIN mc_material mc    ON mc.id = mp.mc_material_id
         WHERE 1=1
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

    prix_rows = conn.execute(
        """SELECT p.id, p.matiere_id, p.laize_id, p.fournisseur_id, p.prix, p.principal,
                  p.updated_at, p.updated_by_name,
                  l.valeur_mm, l.label AS laize_label, l.ordre AS laize_ordre,
                  f.nom AS fournisseur_nom, COALESCE(f.has_fsc, 0) AS fournisseur_fsc
             FROM mp_matiere_prix p
             LEFT JOIN mp_laizes l       ON l.id = p.laize_id
             LEFT JOIN fournisseurs_fsc f ON f.id = p.fournisseur_id
            ORDER BY l.ordre ASC, l.valeur_mm ASC, p.principal DESC,
                     f.nom COLLATE NOCASE ASC"""
    ).fetchall()
    by_mat: dict[int, list[dict]] = {}
    for r in prix_rows:
        by_mat.setdefault(int(r["matiere_id"]), []).append(
            {
                "id": int(r["id"]),
                "laize_id": int(r["laize_id"]) if r["laize_id"] is not None else None,
                "laize_label": r["laize_label"]
                or (f"{int(r['valeur_mm'])} mm" if r["valeur_mm"] is not None else None),
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

    out: list[dict] = []
    for r in rows:
        mid = int(r["id"])
        laizee = is_laizee(r["categorie"])
        par_laize = bool(int(r["prix_par_laize"] or 0)) and laizee
        lignes = by_mat.get(mid, [])
        principaux = [x for x in lignes if x["principal"]]
        if par_laize:
            prix_principal = None
            prix_min = min((x["prix"] for x in principaux), default=None)
            prix_max = max((x["prix"] for x in principaux), default=None)
        else:
            prix_principal = principaux[0]["prix"] if principaux else (
                _f(r["prix_eur_m2"]) if laizee else _f(r["prix_unitaire"])
            )
            prix_min = prix_max = prix_principal
        out.append(
            {
                "id": mid,
                "categorie": r["categorie"],
                "reference": r["reference"],
                "designation": r["designation"],
                "actif": bool(r["actif"]),
                "laizee": laizee,
                "prix_par_laize": par_laize,
                "unite": "€/m²" if laizee else "€/unité",
                "prix_principal": prix_principal,
                "prix_min": prix_min,
                "prix_max": prix_max,
                "nb_lignes": len(lignes),
                "nb_fournisseurs": len({x["fournisseur_id"] for x in lignes if x["fournisseur_id"]}),
                "mc_material_id": int(r["mc_material_id"])
                if r["mc_material_id"] is not None
                else None,
                "mc_name": r["mc_name"],
                "lignes": lignes,
            }
        )
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Écriture
# ─────────────────────────────────────────────────────────────────────────────


def _mirror_principal(
    conn: sqlite3.Connection,
    matiere_id: int,
    laize_id: Optional[int],
    *,
    user_id: Optional[int],
    user_name: Optional[str],
    note: str,
) -> dict:
    """
    Recopie le prix principal dans les champs lus par la valorisation MyStock et
    historise le changement. Retourne un diagnostic.
    """
    mat = fetch_matiere(conn, matiere_id)
    if not mat:
        return {"ok": False, "reason": "matière introuvable"}

    row = conn.execute(
        """SELECT prix FROM mp_matiere_prix
            WHERE matiere_id=? AND COALESCE(laize_id,0)=COALESCE(?,0) AND principal=1
            LIMIT 1""",
        (matiere_id, laize_id),
    ).fetchone()
    if not row:
        return {"ok": False, "reason": "aucun prix principal"}
    prix = _f(row["prix"])

    laizee = is_laizee(mat["categorie"])
    par_laize = bool(int(mat["prix_par_laize"] or 0)) and laizee
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
    matiere_id: int,
    laize_id: Optional[int],
    fournisseur_id: Optional[int],
    prix: float,
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
    origine: str = "Coûts matières",
) -> dict:
    """
    Fixe le prix d'un fournisseur. Si cette ligne est la principale, le prix est
    aussitôt répercuté dans MyStock et historisé.
    """
    if prix < 0:
        return {"ok": False, "reason": "prix négatif interdit"}
    if prix > 1_000_000:
        return {"ok": False, "reason": "prix hors limites"}
    mat = fetch_matiere(conn, matiere_id)
    if not mat:
        return {"ok": False, "reason": "matière introuvable"}

    now = _now()
    existing = conn.execute(
        """SELECT id, principal FROM mp_matiere_prix
            WHERE matiere_id=? AND COALESCE(laize_id,0)=COALESCE(?,0)
              AND COALESCE(fournisseur_id,0)=COALESCE(?,0)""",
        (matiere_id, laize_id, fournisseur_id),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE mp_matiere_prix SET prix=?, updated_at=?, updated_by_name=? WHERE id=?",
            (float(prix), now, user_name, existing["id"]),
        )
        principal = bool(existing["principal"])
    else:
        # Première ligne de prix pour cette matière/laize → elle devient principale.
        others = conn.execute(
            """SELECT COUNT(*) AS n FROM mp_matiere_prix
                WHERE matiere_id=? AND COALESCE(laize_id,0)=COALESCE(?,0)""",
            (matiere_id, laize_id),
        ).fetchone()
        principal = int(others["n"] or 0) == 0
        conn.execute(
            """INSERT INTO mp_matiere_prix
               (matiere_id, laize_id, fournisseur_id, prix, principal, updated_at, updated_by_name)
               VALUES (?,?,?,?,?,?,?)""",
            (matiere_id, laize_id, fournisseur_id, float(prix), 1 if principal else 0,
             now, user_name),
        )
    result = {"ok": True, "principal": principal}
    if principal:
        result["miroir"] = _mirror_principal(
            conn, matiere_id, laize_id,
            user_id=user_id, user_name=user_name,
            note=f"Prix modifié depuis {origine}",
        )
    return result


def set_principal(
    conn: sqlite3.Connection,
    *,
    matiere_id: int,
    laize_id: Optional[int],
    fournisseur_id: Optional[int],
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
    origine: str = "Coûts matières",
) -> dict:
    """Désigne le fournisseur dont le prix fait foi, et pousse son tarif dans MyStock."""
    row = conn.execute(
        """SELECT id FROM mp_matiere_prix
            WHERE matiere_id=? AND COALESCE(laize_id,0)=COALESCE(?,0)
              AND COALESCE(fournisseur_id,0)=COALESCE(?,0)""",
        (matiere_id, laize_id, fournisseur_id),
    ).fetchone()
    if not row:
        return {"ok": False, "reason": "ligne de prix introuvable"}
    conn.execute(
        """UPDATE mp_matiere_prix SET principal=0
            WHERE matiere_id=? AND COALESCE(laize_id,0)=COALESCE(?,0)""",
        (matiere_id, laize_id),
    )
    conn.execute("UPDATE mp_matiere_prix SET principal=1 WHERE id=?", (row["id"],))
    miroir = _mirror_principal(
        conn, matiere_id, laize_id,
        user_id=user_id, user_name=user_name,
        note=f"Fournisseur principal changé depuis {origine}",
    )
    _sync_laize_fournisseurs(conn, matiere_id, laize_id)
    return {"ok": True, "miroir": miroir}


def delete_ligne(
    conn: sqlite3.Connection,
    *,
    matiere_id: int,
    laize_id: Optional[int],
    fournisseur_id: Optional[int],
) -> dict:
    """Retire un fournisseur de la matière. Le principal ne peut pas être retiré."""
    row = conn.execute(
        """SELECT id, principal FROM mp_matiere_prix
            WHERE matiere_id=? AND COALESCE(laize_id,0)=COALESCE(?,0)
              AND COALESCE(fournisseur_id,0)=COALESCE(?,0)""",
        (matiere_id, laize_id, fournisseur_id),
    ).fetchone()
    if not row:
        return {"ok": False, "reason": "ligne de prix introuvable"}
    if int(row["principal"] or 0):
        return {
            "ok": False,
            "reason": "fournisseur principal — désignez-en un autre avant de le retirer",
        }
    conn.execute("DELETE FROM mp_matiere_prix WHERE id=?", (row["id"],))
    _sync_laize_fournisseurs(conn, matiere_id, laize_id)
    return {"ok": True}


def _sync_laize_fournisseurs(
    conn: sqlite3.Connection, matiere_id: int, laize_id: Optional[int]
) -> None:
    """
    Tient à jour la table historique matiere_laize_fournisseurs, encore lue par
    les écrans MyStock (réception, guide traça). Sans laize, rien à faire :
    cette table exige une laize.
    """
    if laize_id is None:
        return
    conn.execute(
        "DELETE FROM matiere_laize_fournisseurs WHERE matiere_id=? AND laize_id=?",
        (matiere_id, laize_id),
    )
    for r in conn.execute(
        """SELECT DISTINCT fournisseur_id FROM mp_matiere_prix
            WHERE matiere_id=? AND laize_id=? AND fournisseur_id IS NOT NULL""",
        (matiere_id, laize_id),
    ).fetchall():
        conn.execute(
            """INSERT OR IGNORE INTO matiere_laize_fournisseurs
               (matiere_id, laize_id, fournisseur_id) VALUES (?,?,?)""",
            (matiere_id, laize_id, int(r["fournisseur_id"])),
        )
