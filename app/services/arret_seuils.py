"""
Seuils d'arret — evaluation cote serveur.

Trois compteurs tournent sur un couple (dossier, machine, code) :
repetition, duree d'un seul arret, duree cumulee du code sur la production.
Le premier des trois qui tombe fait un franchissement, la ligne part au
rapport de prod, et les trois compteurs repartent a zero.

Un point de mecanique qui decide de l'implementation : la duree d'un arret
n'est connue qu'a la saisie suivante — c'est l'ecart entre les deux lignes.
Les regles de duree ne peuvent donc pas se declencher au moment ou l'arret
est code, mais au moment ou l'operateur reprend. C'est aussi le bon moment
pour lui poser la question : il est revenu devant sa machine.

D'ou deux points d'evaluation, appeles l'un derriere l'autre a chaque saisie :

- `evaluer_saisie()`     — regles permanentes et repetition, sur la ligne
                           qu'on vient d'inserer ;
- `cloturer_precedent()` — regles de duree, sur l'arret que cette saisie
                           vient de refermer.

Aucun des deux ne bloque jamais une saisie : ils renvoient une demande
d'explication que le front affiche, et la saisie est deja enregistree.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

# Ecart maximal retenu entre deux saisies d'un meme operateur, en minutes.
# Meme convention que le calcul de duree de app/routers/historique.py : au-dela,
# on considere qu'il ne s'agit plus d'un arret mais d'une fin de journee.
ECART_MAX_MIN = 480

_DEFAUT_PARAMS = {
    "duree_unitaire_min": 60.0,
    "duree_cumul_min": 90.0,
    "categories_surveillees": "arret,appro,technique",
}

REGLES_LABELS = {
    "permanent": "Explication systematique",
    "repetition": "Repetition dans la production",
    "duree_unitaire": "Arret long",
    "duree_cumul": "Duree cumulee sur la production",
}


# ─── Parametres et regles ────────────────────────────────────────────────────

def _table_existe(conn, nom: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (nom,)
    ).fetchone()
    return row is not None


def charger_params(conn) -> Dict[str, Any]:
    vals = dict(_DEFAUT_PARAMS)
    if _table_existe(conn, "arret_seuils_params"):
        for r in conn.execute("SELECT cle, valeur FROM arret_seuils_params").fetchall():
            vals[r["cle"]] = r["valeur"]
    out: Dict[str, Any] = {}
    for cle in ("duree_unitaire_min", "duree_cumul_min"):
        try:
            out[cle] = float(vals.get(cle) or 0)
        except (TypeError, ValueError):
            out[cle] = float(_DEFAUT_PARAMS[cle])
    cats = str(vals.get("categories_surveillees") or "")
    out["categories_surveillees"] = {
        c.strip().lower() for c in cats.split(",") if c.strip()
    }
    return out


def charger_regles(conn) -> List[Dict[str, Any]]:
    if not _table_existe(conn, "arret_seuils"):
        return []
    rows = conn.execute(
        "SELECT * FROM arret_seuils WHERE actif = 1"
    ).fetchall()
    return [dict(r) for r in rows]


def regle_pour(regles: List[Dict[str, Any]], code: str, categorie: str,
               machine: Optional[str]) -> Optional[Dict[str, Any]]:
    """La regle la plus specifique gagne : code, puis categorie, puis defaut.

    A specificite egale, une regle attachee a une machine bat la regle qui
    vaut pour toutes — un meme code n'a pas le meme sens sur deux machines.
    """
    code = (code or "").strip()
    categorie = (categorie or "").strip().lower()
    mach = (machine or "").strip().lower()

    def _candidates(cible_type: str, cible: str) -> List[Dict[str, Any]]:
        out = [
            r for r in regles
            if r.get("cible_type") == cible_type
            and (r.get("cible") or "").strip().lower() == cible.lower()
        ]
        out.sort(key=lambda r: 0 if (r.get("machine") or "").strip().lower() == mach and mach else 1)
        return [
            r for r in out
            if not (r.get("machine") or "").strip()
            or (r.get("machine") or "").strip().lower() == mach
        ]

    for cible_type, cible in (("code", code), ("categorie", categorie), ("defaut", "")):
        found = _candidates(cible_type, cible)
        if found:
            return found[0]
    return None


# ─── Utilitaires ─────────────────────────────────────────────────────────────

def _parse_dt(val: Any) -> Optional[datetime]:
    if not val:
        return None
    s = str(val).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _ecart_min(debut: Optional[datetime], fin: Optional[datetime]) -> Optional[float]:
    if not debut or not fin:
        return None
    delta = (fin - debut).total_seconds() / 60.0
    if delta < 0 or delta > ECART_MAX_MIN:
        return None
    return round(delta, 1)


def _dernier_franchissement_id(conn, no_dossier: str, machine: str, code: str) -> int:
    row = conn.execute(
        """SELECT MAX(saisie_id) AS m FROM arret_seuils_franchis
           WHERE COALESCE(no_dossier,'') = ? AND COALESCE(machine,'') = ?
             AND operation_code = ?""",
        (no_dossier or "", machine or "", code or ""),
    ).fetchone()
    return int(row["m"] or 0) if row else 0


def _serie_courante(conn, saisie: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Les arrets du meme code sur la meme production depuis la derniere remise a zero."""
    depuis = _dernier_franchissement_id(
        conn, saisie.get("no_dossier") or "", saisie.get("machine") or "",
        saisie.get("operation_code") or "",
    )
    rows = conn.execute(
        """SELECT id, date_operation, operateur, commentaire
           FROM production_data
           WHERE COALESCE(no_dossier,'') = ? AND COALESCE(machine,'') = ?
             AND operation_code = ? AND id > ? AND id <= ?
             AND COALESCE(est_annule,0) = 0
           ORDER BY id ASC""",
        (saisie.get("no_dossier") or "", saisie.get("machine") or "",
         saisie.get("operation_code") or "", depuis, int(saisie["id"])),
    ).fetchall()
    return [dict(r) for r in rows]


def _duree_de(conn, saisie: Dict[str, Any]) -> Optional[float]:
    """Duree d'une saisie : ecart avec la saisie suivante du meme operateur."""
    dt = _parse_dt(saisie.get("date_operation"))
    if not dt:
        return None
    row = conn.execute(
        """SELECT date_operation FROM production_data
           WHERE operateur = ? AND id > ? AND COALESCE(est_annule,0) = 0
           ORDER BY id ASC LIMIT 1""",
        (saisie.get("operateur") or "", int(saisie["id"])),
    ).fetchone()
    if not row:
        return None
    return _ecart_min(dt, _parse_dt(row["date_operation"]))


def _saisie(conn, saisie_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT * FROM production_data WHERE id = ?", (int(saisie_id),)
    ).fetchone()
    return dict(row) if row else None


def _surveillee(saisie: Dict[str, Any], params: Dict[str, Any]) -> bool:
    cat = (saisie.get("operation_category") or "").strip().lower()
    return bool(cat) and cat in params["categories_surveillees"]


# ─── Enregistrement d'un franchissement ──────────────────────────────────────

def _enregistrer(conn, saisie: Dict[str, Any], regle: str, compteur: int,
                 duree_saisie: Optional[float], duree_cumul: Optional[float]) -> Dict[str, Any]:
    commentaire = (saisie.get("commentaire") or "").strip()
    exigee = 0 if commentaire else 1
    now = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        """INSERT INTO arret_seuils_franchis
           (saisie_id, no_dossier, machine, operation_code, operation, operateur,
            regle, compteur, duree_saisie_min, duree_cumul_min,
            commentaire_present, explication_exigee, explication_texte,
            explication_le, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            int(saisie["id"]), saisie.get("no_dossier"), saisie.get("machine"),
            saisie.get("operation_code") or "", saisie.get("operation"),
            saisie.get("operateur"), regle, int(compteur or 0),
            duree_saisie, duree_cumul,
            1 if commentaire else 0, exigee,
            commentaire or None, now if commentaire else None, now,
        ),
    )
    return {
        "franchissement_id": cur.lastrowid,
        "saisie_id": int(saisie["id"]),
        "operation": saisie.get("operation"),
        "operation_code": saisie.get("operation_code"),
        "no_dossier": saisie.get("no_dossier"),
        "machine": saisie.get("machine"),
        "regle": regle,
        "compteur": int(compteur or 0),
        "duree_saisie_min": duree_saisie,
        "duree_cumul_min": duree_cumul,
        "explication_exigee": bool(exigee),
        "message": _message(regle, compteur, duree_saisie, duree_cumul, saisie),
    }


def _fmt_duree(minutes: Optional[float]) -> str:
    if not minutes:
        return ""
    m = int(round(minutes))
    return f"{m // 60} h {m % 60:02d}" if m >= 60 else f"{m} min"


def _message(regle: str, compteur: int, duree_saisie: Optional[float],
             duree_cumul: Optional[float], saisie: Dict[str, Any]) -> str:
    op = (saisie.get("operation") or saisie.get("operation_code") or "cet arret").strip()
    if regle == "permanent":
        return f"{op} — une explication est attendue a chaque fois."
    if regle == "repetition":
        return f"{op} — {compteur}e fois sur cette production."
    if regle == "duree_unitaire":
        return f"{op} — l'arret a dure {_fmt_duree(duree_saisie)}."
    if regle == "duree_cumul":
        return f"{op} — {_fmt_duree(duree_cumul)} cumulees sur cette production."
    return op


# ─── Points d'evaluation ─────────────────────────────────────────────────────

def evaluer_saisie(conn, saisie_id: int) -> Optional[Dict[str, Any]]:
    """Regles permanentes et repetition, sur la saisie qu'on vient d'inserer."""
    if not _table_existe(conn, "arret_seuils"):
        return None
    saisie = _saisie(conn, saisie_id)
    if not saisie:
        return None
    params = charger_params(conn)
    if not _surveillee(saisie, params):
        return None

    regle = regle_pour(
        charger_regles(conn),
        saisie.get("operation_code") or "",
        saisie.get("operation_category") or "",
        saisie.get("machine"),
    )
    if not regle:
        return None

    if regle.get("mode") == "permanent":
        return _enregistrer(conn, saisie, "permanent", 1, None, None)

    serie = _serie_courante(conn, saisie)
    seuil = int(regle.get("repetitions") or 0)
    if seuil > 0 and len(serie) >= seuil:
        return _enregistrer(conn, saisie, "repetition", len(serie), None, None)
    return None


def cloturer_precedent(conn, saisie_id: int) -> Optional[Dict[str, Any]]:
    """Regles de duree, sur l'arret que cette saisie vient de refermer."""
    if not _table_existe(conn, "arret_seuils"):
        return None
    saisie = _saisie(conn, saisie_id)
    if not saisie:
        return None
    row = conn.execute(
        """SELECT * FROM production_data
           WHERE operateur = ? AND id < ? AND COALESCE(est_annule,0) = 0
           ORDER BY id DESC LIMIT 1""",
        (saisie.get("operateur") or "", int(saisie_id)),
    ).fetchone()
    if not row:
        return None
    prec = dict(row)

    params = charger_params(conn)
    if not _surveillee(prec, params):
        return None
    # Deja compte : un arret ne franchit qu'un seuil a la fois.
    deja = conn.execute(
        "SELECT 1 FROM arret_seuils_franchis WHERE saisie_id = ? LIMIT 1",
        (int(prec["id"]),),
    ).fetchone()
    if deja:
        return None

    duree = _ecart_min(_parse_dt(prec.get("date_operation")),
                       _parse_dt(saisie.get("date_operation")))
    if duree is None:
        return None

    serie = _serie_courante(conn, prec)
    cumul = 0.0
    for s in serie:
        cumul += (_duree_de(conn, s) or 0.0)
    cumul = round(cumul, 1)

    if cumul >= params["duree_cumul_min"]:
        return _enregistrer(conn, prec, "duree_cumul", len(serie), duree, cumul)
    if duree >= params["duree_unitaire_min"]:
        return _enregistrer(conn, prec, "duree_unitaire", len(serie), duree, cumul)
    return None


def enregistrer_explication(conn, saisie_id: int, texte: str) -> int:
    """Rattache un commentaire aux franchissements en attente de cette saisie."""
    if not _table_existe(conn, "arret_seuils_franchis"):
        return 0
    texte = (texte or "").strip()
    if not texte:
        return 0
    now = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        """UPDATE arret_seuils_franchis
           SET explication_texte = ?, explication_le = ?, explication_exigee = 0
           WHERE saisie_id = ?""",
        (texte, now, int(saisie_id)),
    )
    return cur.rowcount or 0


def franchissements(conn, debut: str, fin: str) -> List[Dict[str, Any]]:
    """Les seuils franchis sur une periode — matiere du rapport de prod."""
    if not _table_existe(conn, "arret_seuils_franchis"):
        return []
    rows = conn.execute(
        """SELECT f.*, COALESCE(u.nom, f.operateur) AS operateur_nom
           FROM arret_seuils_franchis f
           LEFT JOIN users u
             ON trim(lower(u.operateur_lie)) = trim(lower(f.operateur))
             OR trim(lower(u.nom)) = trim(lower(f.operateur))
           WHERE f.created_at >= ? AND f.created_at <= ?
           ORDER BY f.created_at ASC, f.id ASC""",
        (debut, fin),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["regle_label"] = REGLES_LABELS.get(d.get("regle") or "", d.get("regle"))
        d["duree_cumul_txt"] = _fmt_duree(d.get("duree_cumul_min"))
        d["duree_saisie_txt"] = _fmt_duree(d.get("duree_saisie_min"))
        out.append(d)
    return out
