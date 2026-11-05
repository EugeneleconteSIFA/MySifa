"""Outil confirmé au démarrage du dossier : quelle plaque tourne vraiment.

La fiche technique dit quelle plaque le dossier DEVAIT utiliser. Au démarrage,
le conducteur confirme d'un appui ou change ; ce qu'il choisit est gardé dans
`outils_demarrage` avec l'écart à la fiche. C'est ce qui rend calculable le
métrage d'une plaque sans que personne ne le recopie à la main.

Quelles natures se confirment au démarrage : `outil_types.au_demarrage`,
attribut du référentiel — jamais une liste écrite ici. Quelle colonne de la
fiche porte l'outil d'une nature : seule la nature dont la source est la table
des outils de découpe (`source_table = 'out_dec'`) se lit sur la fiche, comme
dans la recherche (`outils._chercher_fiches`). Les autres natures se
confirment sans proposition de la fiche : l'outil en place sur la machine est
proposé à la place.

Rien ici ne bloque une saisie : le démarrage d'un dossier est enregistré même
si l'outil ne l'est pas. Le refuser ferait saisir un numéro faux pour passer.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import FORMES_OUTIL_DECOUPE
from app.services import outils as ref

TABLE = "outils_demarrage"
_RANG_MAX = 3


def _sans_accent(txt: Any) -> str:
    out = str(txt or "").strip().lower()
    for a, b in (("é", "e"), ("è", "e"), ("ê", "e"), ("à", "a"), ("ç", "c")):
        out = out.replace(a, b)
    return out


def est_forme_decoupe(forme: Any) -> bool:
    f = _sans_accent(forme)
    return bool(f) and any(f.startswith(_sans_accent(p)) for p in FORMES_OUTIL_DECOUPE)


def table_existe(conn) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)
    ).fetchone())


def types_au_demarrage(conn) -> List[Dict[str, Any]]:
    return [t for t in ref.list_types(conn) if t.get("au_demarrage")]


# ── Ce que la fiche prévoit ──────────────────────────────────────────────

def _entree_planning(conn, no_dossier: str, machine_id: Optional[int]):
    """Le créneau du dossier : il porte la clé produit et la laize qui
    départagent les fiches d'un même produit."""
    params: List[Any] = [no_dossier, no_dossier]
    tri_machine = ""
    if machine_id:
        tri_machine = "CASE WHEN machine_id = ? THEN 0 ELSE 1 END, "
        params.append(machine_id)
    return conn.execute(
        f"""SELECT id, reference, ref_produit, laize
            FROM planning_entries
            WHERE trim(reference) = trim(?) OR trim(COALESCE(numero_of,'')) = trim(?)
            ORDER BY {tri_machine}CASE WHEN statut = 'termine' THEN 1 ELSE 0 END, id DESC
            LIMIT 1""",
        params,
    ).fetchone()


def fiche_du_dossier(conn, no_dossier: str, machine_nom: str = "",
                     machine_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    from app.services.fiche_choix import choisir_fiche

    if not (no_dossier or "").strip():
        return None
    try:
        pe = _entree_planning(conn, no_dossier, machine_id)
        ref_produit = (pe["ref_produit"] if pe else None) or no_dossier
        laize = pe["laize"] if pe else None
        return choisir_fiche(conn, ref_produit, machine=machine_nom or None, laize=laize)
    except sqlite3.Error:
        return None


def outils_prevus(fiche: Optional[Dict[str, Any]], type_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Les outils de découpe que la fiche prévoit, dans l'ordre de la fiche."""
    if not fiche or (type_info.get("source_table") or "") != "out_dec":
        return []
    prevus = []
    for i in range(1, _RANG_MAX + 1):
        numero = str(fiche.get(f"outil{i}_numero_sifa") or "").strip()
        if not numero or numero == "0":
            continue
        if not est_forme_decoupe(fiche.get(f"outil{i}_forme")):
            continue
        prevus.append({"rang": len(prevus) + 1, "numero": numero,
                       "forme": (fiche.get(f"outil{i}_forme") or "").strip() or None})
    return prevus


def contexte(conn, *, no_dossier: str, machine: Dict[str, Any]) -> Dict[str, Any]:
    """Ce que l'écran « Démarrer un dossier » propose, nature par nature."""
    natures = types_au_demarrage(conn)
    if not natures or not table_existe(conn):
        return {"natures": [], "fiche": None}
    fiche = fiche_du_dossier(conn, no_dossier, machine.get("nom") or "", machine.get("id"))
    sortie = []
    for t in natures:
        en_place = ref.dernier_outil_monte(
            conn, machine_nom=machine.get("nom") or "",
            machine_code=machine.get("code") or "", type_cle=t["cle"],
        )
        lignes = []
        for p in outils_prevus(fiche, t):
            local = ref.trouver_par_numero(conn, t["cle"], p["numero"])
            lignes.append({
                "rang": p["rang"],
                "prevu": {
                    "id": local["id"] if local else None,
                    "numero": local["numero"] if local else p["numero"],
                    "label": (local["label"] if local else None) or p["forme"],
                    "origine": ref.ORIGINE_REFERENTIEL if local else ref.ORIGINE_FICHE,
                },
            })
        if not lignes:
            # Rien sur la fiche : une ligne quand même, l'outil en place proposé.
            lignes.append({"rang": 1, "prevu": None})
        sortie.append({
            "type_cle": t["cle"],
            "label": t["label"],
            "en_place": en_place,
            "lignes": lignes,
        })
    return {
        "natures": sortie,
        "fiche": {"id": fiche["id"], "reference": fiche.get("reference")} if fiche else None,
    }


# ── Enregistrement ───────────────────────────────────────────────────────

def _entier(v) -> Optional[int]:
    try:
        return int(v) if v not in (None, "", "null") else None
    except (TypeError, ValueError):
        return None


def enregistrer(conn, *, saisie_id: int, choix: Any, machine: str, no_dossier: Optional[str],
                date_operation: str, cree_par: str,
                machine_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Écrit les outils confirmés au démarrage. `choix` vient du poste :
    [{type, rang, outil_id} | {type, rang, numero, label, origine}].

    L'outil prévu est relu ici sur la fiche, pas pris dans la requête : c'est
    l'écart à la fiche qu'on mesure, il ne se déclare pas. Rend les lignes
    écrites ; une entrée invalide est ignorée, jamais bloquante."""
    if not isinstance(choix, list) or not choix or not table_existe(conn):
        return []
    natures = {t["cle"]: t for t in types_au_demarrage(conn)}
    fiche = fiche_du_dossier(conn, no_dossier or "", machine, machine_id) if no_dossier else None
    maintenant = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    ecrites: List[Dict[str, Any]] = []
    vus = set()
    for c in choix[:10]:
        if not isinstance(c, dict):
            continue
        type_cle = str(c.get("type") or c.get("type_cle") or "").strip()
        rang = _entier(c.get("rang")) or 1
        if type_cle not in natures or not (1 <= rang <= _RANG_MAX) or (type_cle, rang) in vus:
            continue
        outil = None
        oid = _entier(c.get("outil_id"))
        try:
            if oid is not None:
                outil = ref.get_outil(conn, oid)
                if outil and outil["type_cle"] != type_cle:
                    outil = None
            elif c.get("numero"):
                outil = ref.resoudre(
                    conn, type_cle=type_cle, numero=c.get("numero"), label=c.get("label"),
                    origine=str(c.get("origine") or "").strip(), cree_par=cree_par,
                )
        except ValueError:
            outil = None
        if not outil:
            continue
        prevu = next((p for p in outils_prevus(fiche, natures[type_cle]) if p["rang"] == rang), None)
        prevu_local = ref.trouver_par_numero(conn, type_cle, prevu["numero"]) if prevu else None
        conforme = None
        if prevu:
            conforme = 1 if outil["numero"].lower() == prevu["numero"].lower() else 0
        conn.execute(
            f"""INSERT OR REPLACE INTO {TABLE}
                (saisie_id, type_cle, rang, outil_id, outil_prevu_id, numero_prevu,
                 conforme, machine, no_dossier, date_operation, cree_par, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (saisie_id, type_cle, rang, outil["id"],
             prevu_local["id"] if prevu_local else None,
             prevu["numero"] if prevu else None,
             conforme, machine, no_dossier, date_operation, cree_par, maintenant),
        )
        vus.add((type_cle, rang))
        ecrites.append({"type_cle": type_cle, "label": natures[type_cle]["label"],
                        "rang": rang, "numero": outil["numero"],
                        "numero_prevu": prevu["numero"] if prevu else None,
                        "conforme": conforme})
    return ecrites


def trace(conn, ecrites: List[Dict[str, Any]]) -> str:
    """La phrase lisible ajoutée au commentaire de la saisie : c'est la colonne
    que lisent le retour de prod, les points de production et les exports."""
    morceaux = []
    for e in ecrites:
        txt = f"{e['label']} {e['numero']}"
        if e["conforme"] == 0:
            txt += f" (fiche : {e['numero_prevu']})"
        morceaux.append(txt)
    return " · ".join(morceaux)
