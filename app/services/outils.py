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

La recherche, elle, ne s'arrête pas au référentiel local. Les listes d'outils
existent déjà dans RVGI depuis toujours — les recopier serait les condamner à
diverger. `rechercher()` interroge donc TROIS sources d'un coup :

1. `outils`             — ce qui a déjà été monté, ou saisi à la main ;
2. le miroir RVGI       — la table et les types sont lus sur la nature
                          (`outil_types.source_table` / `source_types`), pas
                          écrits ici : ajouter une nature est une ligne de
                          référentiel, pas une release ;
3. `fiches_techniques`  — les numéros SIFA déjà vus en production, pour les
                          natures dont la source est la table des outils de
                          découpe.

Un résultat RVGI n'a pas d'identifiant local tant que personne ne l'a choisi.
`resoudre()` le matérialise au moment de la sélection : les saisies pointent
toujours un `outils.id` stable, même si RVGI renomme sa ligne plus tard.
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

def _colonnes(conn, table: str) -> set:
    try:
        return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}
    except sqlite3.Error:
        return set()


def _row_to_type(r) -> Dict[str, Any]:
    def champ(nom):
        try:
            return r[nom]
        except (IndexError, KeyError):
            return None

    return {
        "cle": r["cle"],
        "label": r["label"],
        "label_pluriel": r["label_pluriel"] or r["label"],
        "ordre": r["ordre"],
        "actif": bool(r["actif"]),
        # Source RVGI : posée par la migration `changement_outil_sources_rvgi`.
        # Absente sur une base plus ancienne — la recherche se rabat alors sur
        # le seul référentiel local.
        "source_table": (champ("source_table") or "").strip() or None,
        "source_types": (champ("source_types") or "").strip() or None,
    }


def list_types(conn, *, inclure_inactifs: bool = False) -> List[Dict[str, Any]]:
    where = "" if inclure_inactifs else "WHERE actif = 1"
    cols = _colonnes(conn, TABLE_TYPES)
    src = ", source_table, source_types" if "source_table" in cols else ""
    rows = conn.execute(
        f"""SELECT cle, label, label_pluriel, ordre, actif{src}
            FROM {TABLE_TYPES} {where} ORDER BY ordre, label"""
    ).fetchall()
    return [_row_to_type(r) for r in rows]


def get_type(conn, type_cle: str) -> Optional[Dict[str, Any]]:
    cols = _colonnes(conn, TABLE_TYPES)
    src = ", source_table, source_types" if "source_table" in cols else ""
    r = conn.execute(
        f"""SELECT cle, label, label_pluriel, ordre, actif{src}
            FROM {TABLE_TYPES} WHERE cle = ?""",
        (type_cle,),
    ).fetchone()
    return _row_to_type(r) if r else None


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


# ── Recherche multi-sources ──────────────────────────────────────────────
# Comment lire une table du miroir RVGI comme une liste d'outils. Ce n'est pas
# de la configuration SIFA — c'est la connaissance du schéma RVGI, au même
# titre que `app/services/rvgi_article_fiche.py`. QUELLE table sert à quelle
# nature, en revanche, vit en base (`outil_types.source_table`).
_LECTEURS_RVGI = {
    # Outils de découpe : le numéro d'outil EST le numéro de plaque.
    "out_dec": {
        "select": "CAST(numero AS TEXT) AS numero, code, nbl, nba",
        "recherche": ["CAST(numero AS TEXT)", "COALESCE(code,'')"],
        "tri": "numero DESC",
        "label": lambda r: " · ".join(
            p for p in (
                (r["code"] or "").strip() or None,
                f"{r['nbl']}×{r['nba']} poses" if r["nbl"] and r["nba"] else None,
            ) if p
        ) or None,
    },
    # Cylindres : magnétiques et contre-parties. Un magnétique n'a pas de code,
    # il se nomme par son nombre de dents — c'est ce que dit l'atelier.
    "out_cyl": {
        "select": (
            "COALESCE(NULLIF(TRIM(code),''), CAST(nbd AS TEXT)) AS numero, "
            "code, nbd, qte"
        ),
        "recherche": ["COALESCE(code,'')", "CAST(nbd AS TEXT)"],
        "tri": "nbd ASC",
        "label": lambda r: " · ".join(
            p for p in (
                f"{r['nbd']} dents" if r["nbd"] else None,
                f"{r['qte']} en parc" if r["qte"] and r["qte"] > 1 else None,
            ) if p
        ) or None,
    },
    # Matières : la famille des clichés. La référence est le couple code1/code2.
    "mat_mat": {
        "select": (
            "TRIM(COALESCE(code1,'')) || '/' || TRIM(COALESCE(code2,'')) AS numero, "
            "libc1, ref"
        ),
        "recherche": [
            "COALESCE(code1,'')", "COALESCE(code2,'')",
            "TRIM(COALESCE(code1,'')) || '/' || TRIM(COALESCE(code2,''))",
            "COALESCE(libc1,'')", "COALESCE(ref,'')",
        ],
        "tri": "id DESC",
        "label": lambda r: (r["libc1"] or "").strip() or None,
    },
}

ORIGINE_REFERENTIEL = "referentiel"
ORIGINE_RVGI = "rvgi"
ORIGINE_FICHE = "fiche"


def _types_autorises(source_types: Optional[str]) -> List[str]:
    return [t.strip() for t in str(source_types or "").split(",") if t.strip()]


def _chercher_rvgi(type_info: Dict[str, Any], terme: str, limite: int) -> List[Dict[str, Any]]:
    """Interroge le miroir RVGI. Ne lève jamais : miroir absent, table absente
    ou base illisible rendent une liste vide — le conducteur garde le
    référentiel local et la possibilité de créer son numéro."""
    table = (type_info.get("source_table") or "").strip()
    lecteur = _LECTEURS_RVGI.get(table)
    if not lecteur:
        return []
    try:
        from app.services import erp_mirror as miroir
    except Exception:
        return []
    if not miroir.miroir_present():
        return []
    where = ["corbeille = 0"]
    params: List[Any] = []
    types = _types_autorises(type_info.get("source_types"))
    if types:
        where.append("type IN (" + ",".join("?" for _ in types) + ")")
        params.extend(types)
    if terme:
        ors = " OR ".join(f"{c} LIKE ?" for c in lecteur["recherche"])
        where.append("(" + ors + ")")
        params.extend([f"%{terme}%"] * len(lecteur["recherche"]))
    sql = (
        f"SELECT {lecteur['select']} FROM {table} "
        f"WHERE {' AND '.join(where)} ORDER BY {lecteur['tri']} LIMIT ?"
    )
    params.append(limite)
    try:
        with miroir.get_erp_db() as conn_erp:
            if table not in miroir.tables_presentes(conn_erp):
                return []
            rows = conn_erp.execute(sql, params).fetchall()
    except Exception:
        return []
    sortie = []
    for r in rows:
        numero = str(r["numero"] or "").strip()
        if not numero or numero == "/":
            continue
        sortie.append({
            "id": None,
            "numero": numero,
            "label": lecteur["label"](r),
            "origine": ORIGINE_RVGI,
        })
    return sortie


def _chercher_fiches(conn, type_info: Dict[str, Any], terme: str, limite: int) -> List[Dict[str, Any]]:
    """Numéros SIFA déjà vus sur une fiche technique. N'a de sens que pour la
    nature dont la source est la table des outils de découpe : c'est le même
    numéro des deux côtés."""
    if (type_info.get("source_table") or "") != "out_dec":
        return []
    cols = _colonnes(conn, "fiches_techniques")
    paires = [
        (f"outil{i}_forme", f"outil{i}_numero_sifa")
        for i in (1, 2, 3)
        if f"outil{i}_numero_sifa" in cols
    ]
    if not paires:
        return []
    morceaux = []
    params: List[Any] = []
    for col_forme, col_num in paires:
        cond = f"COALESCE(TRIM({col_num}),'') <> ''"
        if terme:
            cond += f" AND {col_num} LIKE ?"
            params.append(f"%{terme}%")
        forme = col_forme if col_forme in cols else "NULL"
        morceaux.append(
            f"SELECT TRIM({col_num}) AS numero, {forme} AS forme "
            f"FROM fiches_techniques WHERE {cond}"
        )
    params.append(limite)
    try:
        rows = conn.execute(
            "SELECT numero, MIN(forme) AS forme FROM (" + " UNION ALL ".join(morceaux) + ") "
            "GROUP BY numero ORDER BY LENGTH(numero), numero LIMIT ?",
            params,
        ).fetchall()
    except sqlite3.Error:
        return []
    return [
        {
            "id": None,
            "numero": str(r["numero"]).strip(),
            "label": (r["forme"] or "").strip() or None,
            "origine": ORIGINE_FICHE,
        }
        for r in rows
        if str(r["numero"] or "").strip()
    ]


def rechercher(
    conn, *, type_cle: str, q: str = "", limite: int = 25
) -> Dict[str, Any]:
    """Les trois sources, fusionnées par numéro. Le référentiel local gagne —
    c'est lui qui porte l'identifiant que les saisies référencent."""
    type_info = get_type(conn, type_cle)
    if not type_info:
        raise ValueError("Nature d'outil inconnue.")
    terme = re.sub(r"\s+", " ", str(q or "").strip())
    plafond = max(5, min(int(limite or 25), 100))

    resultats: List[Dict[str, Any]] = []
    vus = set()

    def ajouter(entrees):
        for e in entrees:
            cle = e["numero"].lower()
            if cle in vus:
                continue
            vus.add(cle)
            resultats.append(e)

    locaux = list_outils(conn, type_cle=type_cle, q=terme, limite=plafond)
    ajouter({
        "id": o["id"], "numero": o["numero"], "label": o["label"],
        "origine": ORIGINE_REFERENTIEL, "a_valider": o["a_valider"],
    } for o in locaux)
    ajouter(_chercher_rvgi(type_info, terme, plafond))
    ajouter(_chercher_fiches(conn, type_info, terme, plafond))

    # « Créer cet outil » n'a de sens que si le terme saisi n'est pas déjà là.
    creation = None
    if terme and terme.lower() not in vus:
        try:
            creation = normalize_numero(terme)
        except ValueError:
            creation = None

    return {
        "type": type_info,
        "q": terme,
        "creation": creation,
        "resultats": resultats[:plafond],
    }


def resoudre(
    conn, *, type_cle: str, numero: str, label: Any = None,
    origine: str = "", cree_par: str = "",
) -> Dict[str, Any]:
    """Rend l'outil local correspondant à un résultat de recherche, en le
    créant au besoin. Un numéro venu de RVGI ou d'une fiche technique n'est
    pas « à valider » : il existe déjà quelque part, il n'a pas été inventé au
    poste. Tout autre numéro, si."""
    existant = trouver_par_numero(conn, type_cle, numero)
    if existant:
        if not existant["actif"]:
            return maj_outil(conn, existant["id"], actif=True)
        return existant
    return creer_outil(
        conn,
        type_cle=type_cle,
        numero=numero,
        label=label,
        cree_par=cree_par,
        a_valider=origine not in (ORIGINE_RVGI, ORIGINE_FICHE),
    )
