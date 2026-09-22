"""Référentiel des outils montables (plaques, contre-parties, magnétiques,
clichés…) et lecture de ce qui est monté sur une machine.

Deux tables, posées par la migration `changement_outil_referentiel` :

- `outil_types` : les natures d'outil. Une nature existe dès qu'un code
  opération la porte (`operation_codes.outil_type`) — c'est ce lien, et lui
  seul, qui décide qu'un code déclenche la saisie d'un changement d'outil.
- `outils`      : un numéro par ligne et par nature. Un outil ne se supprime
  jamais : les saisies passées pointent dessus. Il se désactive.

`a_valider` marque un numéro créé au poste par un conducteur qui ne trouvait
pas le sien dans la liste. Bloquer la saisie aurait garanti qu'on saisisse un
numéro faux ou rien du tout ; on encaisse, et Paramètres montre la file.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

TABLE = "outils"
TABLE_TYPES = "outil_types"

_NUMERO_MAX = 40
_LABEL_MAX = 80


def _maintenant() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def normalize_numero(numero: Any) -> str:
    """Un numéro d'outil est un identifiant d'atelier : espaces de bord et
    espaces multiples n'y portent aucun sens et créeraient deux lignes pour
    la même plaque. La casse, elle, est conservée (« SH CO2 »)."""
    txt = re.sub(r"\s+", " ", str(numero or "").strip())
    if not txt:
        raise ValueError("Numéro d'outil requis.")
    if len(txt) > _NUMERO_MAX:
        raise ValueError(f"Numéro d'outil trop long ({_NUMERO_MAX} caractères maximum).")
    return txt


def normalize_label(label: Any) -> Optional[str]:
    txt = re.sub(r"\s+", " ", str(label or "").strip())
    return txt[:_LABEL_MAX] or None


# ── Natures d'outil ──────────────────────────────────────────────────────

def list_types(conn, *, inclure_inactifs: bool = False) -> List[Dict[str, Any]]:
    where = "" if inclure_inactifs else "WHERE actif = 1"
    rows = conn.execute(
        f"""SELECT cle, label, label_pluriel, ordre, actif
            FROM {TABLE_TYPES} {where} ORDER BY ordre, label"""
    ).fetchall()
    return [
        {
            "cle": r["cle"],
            "label": r["label"],
            "label_pluriel": r["label_pluriel"] or r["label"],
            "ordre": r["ordre"],
            "actif": bool(r["actif"]),
        }
        for r in rows
    ]


def type_existe(conn, type_cle: str) -> bool:
    if not type_cle:
        return False
    row = conn.execute(
        f"SELECT 1 FROM {TABLE_TYPES} WHERE cle = ? AND actif = 1 LIMIT 1", (type_cle,)
    ).fetchone()
    return bool(row)


def label_type(conn, type_cle: str) -> str:
    row = conn.execute(
        f"SELECT label FROM {TABLE_TYPES} WHERE cle = ? LIMIT 1", (type_cle,)
    ).fetchone()
    return (row["label"] if row else None) or str(type_cle or "outil")


# ── Référentiel ──────────────────────────────────────────────────────────

def _row_to_outil(r) -> Dict[str, Any]:
    return {
        "id": r["id"],
        "type_cle": r["type_cle"],
        "numero": r["numero"],
        "label": r["label"],
        "actif": bool(r["actif"]),
        "a_valider": bool(r["a_valider"]),
        "cree_par": r["cree_par"],
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
    }


def list_outils(
    conn,
    *,
    type_cle: Optional[str] = None,
    q: Optional[str] = None,
    inclure_inactifs: bool = False,
    limite: int = 500,
) -> List[Dict[str, Any]]:
    where = []
    params: List[Any] = []
    if type_cle:
        where.append("type_cle = ?")
        params.append(type_cle)
    if not inclure_inactifs:
        where.append("actif = 1")
    terme = re.sub(r"\s+", " ", str(q or "").strip())
    if terme:
        where.append("(numero LIKE ? OR COALESCE(label,'') LIKE ?)")
        params.extend([f"%{terme}%", f"%{terme}%"])
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    params.append(max(1, min(int(limite or 500), 2000)))
    rows = conn.execute(
        f"""SELECT id, type_cle, numero, label, actif, a_valider, cree_par,
                   created_at, updated_at
            FROM {TABLE} {clause}
            ORDER BY a_valider DESC,
                     CASE WHEN numero GLOB '[0-9]*' THEN 0 ELSE 1 END,
                     CAST(numero AS INTEGER), numero
            LIMIT ?""",
        params,
    ).fetchall()
    return [_row_to_outil(r) for r in rows]


def get_outil(conn, outil_id: Any) -> Optional[Dict[str, Any]]:
    try:
        oid = int(outil_id)
    except (TypeError, ValueError):
        return None
    r = conn.execute(
        f"""SELECT id, type_cle, numero, label, actif, a_valider, cree_par,
                   created_at, updated_at
            FROM {TABLE} WHERE id = ?""",
        (oid,),
    ).fetchone()
    return _row_to_outil(r) if r else None


def trouver_par_numero(conn, type_cle: str, numero: str) -> Optional[Dict[str, Any]]:
    r = conn.execute(
        f"""SELECT id, type_cle, numero, label, actif, a_valider, cree_par,
                   created_at, updated_at
            FROM {TABLE} WHERE type_cle = ? AND numero = ?""",
        (type_cle, normalize_numero(numero)),
    ).fetchone()
    return _row_to_outil(r) if r else None


def creer_outil(
    conn,
    *,
    type_cle: str,
    numero: str,
    label: Any = None,
    cree_par: str = "",
    a_valider: bool = False,
) -> Dict[str, Any]:
    """Crée l'outil, ou rend celui qui existe déjà (en le réactivant s'il
    était désactivé). Un conducteur qui ressaisit un numéro retiré de la
    liste le remet en service plutôt que de tomber sur un conflit."""
    if not type_existe(conn, type_cle):
        raise ValueError("Nature d'outil inconnue.")
    num = normalize_numero(numero)
    lbl = normalize_label(label)
    existant = trouver_par_numero(conn, type_cle, num)
    if existant:
        if not existant["actif"]:
            conn.execute(
                f"UPDATE {TABLE} SET actif = 1, updated_at = ? WHERE id = ?",
                (_maintenant(), existant["id"]),
            )
            conn.commit()
            existant["actif"] = True
        return existant
    cur = conn.execute(
        f"""INSERT INTO {TABLE}
            (type_cle, numero, label, actif, a_valider, cree_par, created_at)
            VALUES (?,?,?,1,?,?,?)""",
        (type_cle, num, lbl, 1 if a_valider else 0, cree_par or None, _maintenant()),
    )
    conn.commit()
    return get_outil(conn, cur.lastrowid)


def maj_outil(
    conn,
    outil_id: Any,
    *,
    numero: Any = None,
    label: Any = None,
    actif: Any = None,
    a_valider: Any = None,
) -> Dict[str, Any]:
    outil = get_outil(conn, outil_id)
    if not outil:
        raise ValueError("Outil introuvable.")
    sets: List[str] = []
    params: List[Any] = []
    if numero is not None:
        num = normalize_numero(numero)
        if num != outil["numero"]:
            autre = trouver_par_numero(conn, outil["type_cle"], num)
            if autre and autre["id"] != outil["id"]:
                raise ValueError(f"Le numéro {num} existe déjà pour cette nature d'outil.")
            sets.append("numero = ?")
            params.append(num)
    if label is not None:
        sets.append("label = ?")
        params.append(normalize_label(label))
    if actif is not None:
        sets.append("actif = ?")
        params.append(1 if actif else 0)
    if a_valider is not None:
        sets.append("a_valider = ?")
        params.append(1 if a_valider else 0)
    if not sets:
        return outil
    sets.append("updated_at = ?")
    params.append(_maintenant())
    params.append(outil["id"])
    conn.execute(f"UPDATE {TABLE} SET {', '.join(sets)} WHERE id = ?", params)
    conn.commit()
    return get_outil(conn, outil["id"])


def compter_a_valider(conn, type_cle: Optional[str] = None) -> int:
    if type_cle:
        row = conn.execute(
            f"SELECT COUNT(*) FROM {TABLE} WHERE a_valider = 1 AND actif = 1 AND type_cle = ?",
            (type_cle,),
        ).fetchone()
    else:
        row = conn.execute(
            f"SELECT COUNT(*) FROM {TABLE} WHERE a_valider = 1 AND actif = 1"
        ).fetchone()
    return int(row[0] or 0)


# ── Ce qui est monté sur une machine ─────────────────────────────────────

def codes_par_type(conn) -> Dict[str, str]:
    """{code opération -> nature d'outil}. Lu du référentiel, jamais écrit en
    dur : ajouter un code de changement se fait dans Paramètres."""
    try:
        rows = conn.execute(
            """SELECT code, outil_type FROM operation_codes
               WHERE COALESCE(outil_type, '') <> ''"""
        ).fetchall()
    except sqlite3.Error:
        return {}
    return {str(r["code"]).strip(): str(r["outil_type"]).strip() for r in rows}


def dernier_outil_monte(
    conn, *, machine_nom: str, machine_code: str = "", type_cle: str = ""
) -> Optional[Dict[str, Any]]:
    """Dernier outil posé sur cette machine pour cette nature, d'après les
    saisies. C'est la seule source qui suit la machine et non le dossier :
    un outil reste en place d'un dossier au suivant."""
    codes = [c for c, t in codes_par_type(conn).items() if t == type_cle]
    if not codes:
        return None
    placeholders = ",".join("?" for _ in codes)
    mn = (machine_nom or "").strip()
    mc = (machine_code or "").strip()
    row = conn.execute(
        f"""SELECT outil_apres_id AS oid
            FROM production_data
            WHERE operation_code IN ({placeholders})
              AND outil_apres_id IS NOT NULL
              AND COALESCE(est_annule, 0) = 0
              AND (trim(machine) = trim(?) OR (trim(?) <> '' AND trim(machine) = trim(?)))
            ORDER BY date_operation DESC, id DESC
            LIMIT 1""",
        (*codes, mn, mc, mc),
    ).fetchone()
    if not row or row["oid"] is None:
        return None
    return get_outil(conn, row["oid"])
