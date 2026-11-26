"""
Du nouvel OF au planning (22/11/2026, demande d'Eugène : « ajouter / modifier
un dossier de prod au planning à partir d'une création d'OF »).

La fenêtre OF porte une étape « 4 · Planning ». Elle cherche d'abord si un
dossier correspond déjà à l'OF, puis propose le bon geste :

- un dossier correspond (déjà relié à l'OF, même numéro d'OF, ou mêmes lignes
  de commande) : le relier, et reporter les valeurs de l'OF qui diffèrent,
  case par case ;
- aucun dossier : en créer un, « à placer » par défaut. La machine, la place
  exacte et la durée restent des arbitrages du planning : un dossier posé en
  silence au mauvais endroit coûte plus cher que deux clics (même règle que
  `of_dossier_prefill`, dont la création reprend les valeurs).

L'OF est enregistré AVANT : une erreur ici ne bloque jamais sa création.

Ce que l'OF peut modifier sur un dossier : numéro d'OF, référence produit,
délai, laize, format. Jamais la machine ni la place. Un délai imposé
(`date_livraison_imposee`) ne bouge pas. Un dossier en cours ou terminé est
relié, jamais modifié : ce qui a été produit est produit.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request

from database import get_db
from config import REFERENCE_A_VENIR_MOTIF
from services.auth_service import get_current_user, is_admin
from app.services.audit_service import log_action
from app.services import rvgi_rattachement as ratt
from app.services.fiche_choix import cle_machine
from app.routers.of_import import (
    _date_iso, _format_lh, _promote_of_link, _require_of_access, of_dossier_prefill,
)

router = APIRouter(tags=["of-planning"])

# (champ du dossier, libellé). L'ordre est celui de l'écran.
CHAMPS = (
    ("numero_of", "N° d'OF"),
    ("ref_produit", "Référence produit"),
    ("date_livraison", "Délai"),
    ("laize", "Laize"),
    ("format", "Format"),
)
PLACES = ("a_placer", "fin")
DUREE_DEFAUT_H = 8.0   # celle de l'ajout manuel au planning (`add_entry`)


_A_VENIR_RE = re.compile(REFERENCE_A_VENIR_MOTIF)


def reference_a_venir(reference: Any) -> bool:
    """Dossier réservé au planning sans son numéro (« ???? », « XXXXXXX »)."""
    return bool(_A_VENIR_RE.fullmatch(str(reference or "")))


def _cle_produit(reference: Any) -> str:
    return str(reference or "").split(" - ")[0].strip()


def _nombre(v: Any) -> Optional[float]:
    try:
        return float(str(v).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


def _txt_nombre(v: Optional[float]) -> str:
    if v is None:
        return ""
    return str(int(v)) if float(v).is_integer() else str(v).replace(".", ",")


def valeurs_de_l_of(of: Dict[str, Any]) -> Dict[str, Any]:
    """Ce que l'OF dirait au dossier, dans les unités du planning."""
    l, h = _format_lh(of.get("format"))
    return {
        "numero_of": (str(of.get("of_numero") or "").strip() or None),
        "reference": (str(of.get("of_numero") or "").strip() or None),
        "ref_produit": _cle_produit(of.get("reference")) or None,
        "date_livraison": _date_iso(of.get("delai_client")),
        "laize": _nombre(of.get("laize")),
        "format": (l, h) if l and h else None,
    }


def _format_dossier(d: Dict[str, Any]):
    l, h = _nombre(d.get("format_l")), _nombre(d.get("format_h"))
    return (l, h) if l and h else None


def _jour(iso: Any) -> str:
    s = str(iso or "")[:10]
    return "%s/%s/%s" % (s[8:10], s[5:7], s[0:4]) if len(s) == 10 and s[4] == "-" else s


def _affiche(champ: str, v: Any) -> str:
    if v in (None, ""):
        return "vide"
    if champ == "date_livraison":
        return _jour(v)
    if champ == "laize":
        return _txt_nombre(v)
    if champ == "format":
        return "%s x %s" % (_txt_nombre(v[0]), _txt_nombre(v[1]))
    return str(v)


def _egal(champ: str, a: Any, b: Any) -> bool:
    if champ in ("numero_of", "ref_produit", "reference"):
        return str(a or "").strip().lower() == str(b or "").strip().lower()
    if champ == "date_livraison":
        return str(a or "")[:10] == str(b or "")[:10]
    if champ == "laize":
        return (a is None and b is None) or (a is not None and b is not None and abs(a - b) < 0.01)
    if champ == "format":
        if not a or not b:
            return not a and not b
        return abs(a[0] - b[0]) < 0.01 and abs(a[1] - b[1]) < 0.01
    return a == b


def ecarts(dossier: Dict[str, Any], vals: Dict[str, Any], conn=None) -> List[Dict[str, Any]]:
    """Les valeurs de l'OF qui diffèrent du dossier. Une valeur que l'OF ne
    porte pas n'efface jamais celle du dossier.

    La référence du dossier n'est proposée que pour une réservation
    (« ???? ») : un vrai numéro de dossier ne se renomme pas depuis l'OF."""
    actuel = {
        "reference": dossier.get("reference"),
        "numero_of": dossier.get("numero_of"),
        "ref_produit": dossier.get("ref_produit"),
        "date_livraison": dossier.get("date_livraison"),
        "laize": _nombre(dossier.get("laize")),
        "format": _format_dossier(dossier),
    }
    modifiable = (dossier.get("statut") or "attente") == "attente"
    out = []
    champs = list(CHAMPS)
    if reference_a_venir(dossier.get("reference")):
        champs.insert(0, ("reference", "Référence dossier"))
    for champ, libelle in champs:
        neuf = vals.get(champ)
        if neuf in (None, "") or _egal(champ, actuel[champ], neuf):
            continue
        motif = None
        if not modifiable:
            motif = "Dossier %s : il n'est plus modifié depuis l'OF." % (
                "en cours" if dossier.get("statut") == "en_cours" else "terminé")
        elif champ == "date_livraison" and int(dossier.get("date_livraison_imposee") or 0):
            motif = "Délai imposé au planning."
        elif champ == "reference" and conn is not None:
            autre = conn.execute(
                "SELECT reference FROM planning_entries WHERE id<>? AND statut IN ('attente','en_cours') "
                "AND LOWER(TRIM(COALESCE(reference,'')))=LOWER(?) LIMIT 1",
                (dossier.get("id") or 0, neuf)).fetchone()
            if autre:
                motif = "Un autre dossier à produire porte déjà la référence %s." % autre["reference"]
        out.append({"champ": champ, "libelle": libelle,
                    "avant": _affiche(champ, actuel[champ]), "apres": _affiche(champ, neuf),
                    "modifiable": motif is None, "motif": motif})
    return out


def candidats(conn, of_id: Optional[int], numero: Optional[str],
              commandes: List[Dict[str, Any]], depart: Optional[int] = None) -> List[Dict[str, Any]]:
    """Les dossiers qui correspondent à cet OF, le plus sûr d'abord.

    1. déjà relié à l'OF (quel que soit son état) ;
    2. le dossier d'où l'OF est parti (« Partir d'un dossier du planning »),
       seul moyen de retrouver une réservation « ???? » qui n'a ni numéro ni
       commande ; puis même numéro d'OF ou même référence de dossier ;
    3. mêmes lignes de commande RVGI.
    Seuls les dossiers en attente ou en cours sont cherchés aux rangs 2 et 3 :
    un dossier terminé sur la même commande est une production passée, pas
    le dossier de ce nouvel OF.
    """
    raisons: Dict[int, str] = {}
    if of_id:
        for r in conn.execute(
            "SELECT planning_entry_id AS id FROM planning_of_links WHERE of_import_id=? "
            "UNION SELECT id FROM planning_entries WHERE of_import_id=?", (of_id, of_id)):
            raisons.setdefault(int(r["id"]), "Relié à cet OF")
    if depart:
        for r in conn.execute(
                "SELECT id FROM planning_entries WHERE id=? AND statut IN ('attente','en_cours')", (depart,)):
            raisons.setdefault(int(r["id"]), "Dossier de départ")
    num = str(numero or "").strip()
    if num:
        for r in conn.execute(
            "SELECT id FROM planning_entries WHERE statut IN ('attente','en_cours') AND "
            "(LOWER(TRIM(COALESCE(numero_of,'')))=LOWER(?) OR LOWER(TRIM(COALESCE(reference,'')))=LOWER(?))",
            (num, num)):
            raisons.setdefault(int(r["id"]), "Même numéro d'OF")
    for l in commandes or []:
        n = str(l.get("numero") or "").strip()
        if not n:
            continue
        lg = l.get("ligne")
        lg = None if lg in (None, "", 0) else int(lg)
        for r in conn.execute(
            "SELECT pe.id FROM rvgi_rattachements r JOIN planning_entries pe ON pe.id = r.objet_id "
            "WHERE r.objet='dossier' AND r.piece='commande' AND r.numero=? "
            "AND (? IS NULL OR r.ligne IS NULL OR r.ligne=?) "
            "AND pe.statut IN ('attente','en_cours')", (n, lg, lg)):
            raisons.setdefault(int(r["id"]), "Même commande %s%s" % (n, "/L%d" % lg if lg else ""))
    if not raisons:
        return []
    ph = ",".join("?" * len(raisons))
    rows = conn.execute(
        "SELECT pe.*, m.nom AS machine_nom, o.of_numero AS of_relie "
        "FROM planning_entries pe LEFT JOIN machines m ON m.id = pe.machine_id "
        "LEFT JOIN of_imports o ON o.id = pe.of_import_id "
        "WHERE pe.id IN (%s)" % ph, list(raisons)).fetchall()
    ordre = {"Relié à cet OF": 0, "Dossier de départ": 1, "Même numéro d'OF": 1}
    out = []
    for r in rows:
        d = dict(r)
        rang = None
        if d.get("statut") == "attente" and not int(d.get("a_placer") or 0):
            rang = conn.execute(
                "SELECT COUNT(*) FROM planning_entries WHERE machine_id=? AND statut='attente' "
                "AND COALESCE(a_placer,0)=0 AND position <= ?",
                (d["machine_id"], d["position"])).fetchone()[0]
        d["_raison"] = raisons[int(d["id"])]
        d["_rang"] = rang
        out.append(d)
    out.sort(key=lambda d: (ordre.get(d["_raison"], 2),
                            {"attente": 0, "en_cours": 1}.get(d.get("statut"), 2), -int(d["id"])))
    return out


def _heure(iso: Any) -> str:
    s = str(iso or "")
    return ("%s à %s" % (_jour(s), s[11:16])) if len(s) >= 16 else _jour(s)


def _apercu(d: Dict[str, Any]) -> Dict[str, Any]:
    """Ce qu'on regarde d'un dossier avant d'y relier un OF (retour du
    22/11/2026 : « c'est assez compliqué de se projeter sinon »)."""
    fmt = _format_dossier(d)
    duree = _nombre(d.get("duree_heures"))
    return {
        "client": (d.get("client") or "").strip() or None,
        "produit": (d.get("ref_produit") or "").strip() or None,
        "description": (d.get("description") or "").strip() or None,
        "debut": _heure(d.get("planned_start")) or None,
        "fin": _heure(d.get("planned_end")) or None,
        "duree": ("%s h" % _txt_nombre(duree)) if duree else None,
        "laize": _txt_nombre(_nombre(d.get("laize"))) or None,
        "format": _affiche("format", fmt) if fmt else None,
        "commandes": (d.get("dos_rvgi") or "").strip() or None,
        "commentaire": ((d.get("commentaire") or "").strip()[:240]) or None,
        "cree": "%s%s" % (_jour(d.get("created_at")), (" par " + d["created_by"]) if d.get("created_by") else ""),
    }


def _public(d: Dict[str, Any], vals: Dict[str, Any], of_id: Optional[int], conn=None) -> Dict[str, Any]:
    relie_ailleurs = bool(d.get("of_import_id")) and of_id and int(d["of_import_id"]) != int(of_id)
    return {
        "apercu": _apercu(d),
        "id": d["id"], "reference": d.get("reference"), "machine_id": d.get("machine_id"),
        "reservation": reference_a_venir(d.get("reference")), "client": d.get("client"),
        "machine": d.get("machine_nom"), "statut": d.get("statut"),
        "a_placer": bool(int(d.get("a_placer") or 0)), "rang": d.get("_rang"),
        "date_livraison": _jour(d.get("date_livraison")) or None,
        "raison": d["_raison"],
        "of_relie": d.get("of_relie") if (relie_ailleurs or (not of_id and d.get("of_import_id"))) else None,
        "deja_relie": bool(of_id) and d["_raison"] == "Relié à cet OF",
        # Ce que l'OF peut reprendre du dossier quand il ne le porte pas
        # (retour du 26/11/2026 : le délai du dossier n'arrivait pas à l'OF).
        "delai_iso": str(d.get("date_livraison") or "")[:10] or None,
        "ecarts": ecarts(d, vals, conn),
    }


def _machines(conn) -> List[Dict[str, Any]]:
    return [{"id": r["id"], "nom": r["nom"]} for r in conn.execute(
        "SELECT id, nom FROM machines WHERE COALESCE(actif,1)=1 ORDER BY id")]


def _machine_proposee(machines: List[Dict[str, Any]], *noms: Any) -> Optional[int]:
    for nom in noms:
        cle = cle_machine(nom)
        if not cle:
            continue
        for m in machines:
            if cle_machine(m["nom"]) == cle:
                return m["id"]
        # « COHESIO » seul ne désigne aucune machine.
    return None


@router.post("/api/of/planning/candidats")
async def of_planning_candidats(request: Request):
    """Les dossiers qui correspondent à un OF, enregistré ou en cours de saisie,
    avec les écarts que l'OF y reporterait."""
    user = _require_of_access(request)
    body = await request.json()
    of_id = body.get("of_id")
    of_id = int(of_id) if str(of_id or "").isdigit() else None
    commandes = [l for l in (body.get("commandes") or []) if isinstance(l, dict)][:50]
    vals = valeurs_de_l_of(body)
    with get_db() as conn:
        if of_id and not commandes:
            # OF enregistré : ses lignes de commande sont en base.
            commandes = [l for l in ratt.lister(conn, "of", of_id) if l["piece"] == "commande"]
        machines = _machines(conn)
        depart = body.get("dossier_depart")
        depart = int(depart) if str(depart or "").isdigit() else None
        dossiers = candidats(conn, of_id, vals["numero_of"], commandes, depart)
        # Un numéro tapé déjà porté par un autre OF sera refusé à la création :
        # le dire avant le clic, avec de quoi ouvrir l'OF existant.
        meme_numero = None
        if vals["numero_of"]:
            r = conn.execute(
                "SELECT id, of_numero, date_import, imported_by FROM of_imports "
                "WHERE LOWER(TRIM(of_numero)) = LOWER(?) AND id != ? ORDER BY id DESC LIMIT 1",
                (vals["numero_of"], of_id or 0)).fetchone()
            if r:
                meme_numero = {"id": r["id"], "numero": r["of_numero"], "le": _jour(r["date_import"]),
                               "par": r["imported_by"] if r["imported_by"] not in (None, "access_bridge") else
                               ("le pont Access" if r["imported_by"] == "access_bridge" else None)}
        publics = [_public(d, vals, of_id, conn) for d in dossiers[:5]]
    return {
        "of_meme_numero": meme_numero,
        "dossiers": publics,
        "machines": machines,
        "machine_proposee": _machine_proposee(machines, body.get("machine"), body.get("machine_fiche")),
        "peut_planifier": is_admin(user),
    }


@router.post("/api/of/{of_id}/planning")
async def of_planning_appliquer(of_id: int, request: Request):
    """Relie l'OF à un dossier et y reporte les valeurs choisies, ou crée son
    dossier. Appelé après l'enregistrement de l'OF."""
    _require_of_access(request)
    user = get_current_user(request)
    if not is_admin(user):
        raise HTTPException(403, "Le planning est réservé à la direction et à l'administration.")
    body = await request.json()
    action = body.get("action")
    qui = user.get("nom") or user.get("email") or "Admin"
    maintenant = datetime.now().isoformat()
    with get_db() as conn:
        of = conn.execute("SELECT * FROM of_imports WHERE id=?", (of_id,)).fetchone()
        if not of:
            raise HTTPException(404, "OF introuvable.")
        of = dict(of)
        if action == "relier":
            return _relier(conn, request, user, qui, maintenant, of,
                           int(body.get("entry_id") or 0), body.get("champs") or [])
        if action == "creer":
            place = body.get("place") if body.get("place") in PLACES else "a_placer"
            return _creer(conn, request, user, qui, maintenant, of,
                                body.get("machine_id"), place)
    raise HTTPException(400, "Action inconnue : relier ou creer.")


def _relier(conn, request, user, qui, maintenant, of, entry_id, champs):
    d = conn.execute("SELECT * FROM planning_entries WHERE id=?", (entry_id,)).fetchone()
    if not d:
        raise HTTPException(404, "Dossier introuvable.")
    d = dict(d)
    verifier_reutilisable(conn, [of["id"]], entry_id)
    _promote_of_link(conn, entry_id, of["id"], qui)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(planning_entries)")}
    sets: Dict[str, Any] = {}
    if "of_link_user_managed" in cols:
        sets["of_link_user_managed"] = 1
    vals = valeurs_de_l_of(of)
    voulus = {c for c in champs if isinstance(c, str)}
    ecrits = []
    for e in ecarts(d, vals, conn):
        if e["champ"] not in voulus or not e["modifiable"]:
            continue
        if e["champ"] == "format":
            sets["format_l"], sets["format_h"] = vals["format"]
        else:
            sets[e["champ"]] = vals[e["champ"]]
        ecrits.append(e)
    if ecrits:
        sets["updated_at"] = maintenant
        if "updated_by" in cols:
            sets["updated_by"] = qui
    if sets:
        conn.execute("UPDATE planning_entries SET %s WHERE id=?" % ", ".join("%s=?" % c for c in sets),
                     list(sets.values()) + [entry_id])
    # Les lignes de commande de l'OF passent au dossier s'il n'en a aucune :
    # jamais en remplacement de celles qu'on y a déjà rattachées.
    lignes = [l for l in ratt.lister(conn, "of", of["id"]) if l["piece"] == "commande"]
    if lignes and not ratt.lister(conn, "dossier", entry_id, piece="commande"):
        try:
            ratt.enregistrer(conn, "dossier", entry_id, "commande",
                             [dict(l, confirme=(l.get("etat") == "confirme")) for l in lignes], qui)
        except ValueError:
            pass
    if any(e["champ"] == "date_livraison" for e in ecrits):
        _invalider_plans(conn, d["machine_id"])
    conn.commit()
    ecrits_ch = {e["champ"] for e in ecrits}
    # Ce que l'OF aurait changé et qui ne l'a pas été : case décochée,
    # délai imposé, dossier en cours. `d` est le dossier d'AVANT l'écriture.
    gardes = [{"libelle": e["libelle"], "valeur": e["avant"], "propose": e["apres"],
               "motif": e["motif"] or "non reporté"}
              for e in ecarts(d, vals, conn) if e["champ"] not in ecrits_ch]
    bilan = _bilan_dossier(conn, entry_id)
    numero_of = of.get("of_numero") or "#%s" % of["id"]
    # Lisible dans « Historique des modifications » de la machine : la ligne
    # porte machine_id, le geste et les valeurs avant → après.
    nom = bilan.get("reference") or d.get("reference") or entry_id
    log_action(user=user, action="UPDATE", module="planning",
               objet="Dossier %s · %s" % (nom, bilan.get("machine") or ""),
               detail={"machine_id": d["machine_id"], "geste": "Relié à l'OF %s" % numero_of,
                       "avant": {e["libelle"]: e["avant"] for e in ecrits},
                       "apres": {e["libelle"]: e["apres"] for e in ecrits}},
               request=request)
    n = len(ecrits)
    return {"ok": True, "action": "relier", "entry_id": entry_id, "machine_id": d["machine_id"],
            "dossier": bilan, "ecrits": [{"libelle": e["libelle"], "avant": e["avant"], "apres": e["apres"]} for e in ecrits],
            "gardes": gardes,
            "message": "OF relié au dossier %s%s." % (
                nom,
                (", %d valeur%s mise%s à jour" % (n, "s" if n > 1 else "", "s" if n > 1 else "")) if n else "")}


def _creer(conn, request, user, qui, maintenant, of, machine_id, place):
    p = of_dossier_prefill(of["id"], request)
    mid = machine_id or p.get("machine_id")
    mac = conn.execute("SELECT id, nom FROM machines WHERE id=?", (mid,)).fetchone() if mid else None
    if not mac:
        raise HTTPException(400, "Choisissez la machine du dossier.")
    dos = p["dossier"]
    cols = {r[1] for r in conn.execute("PRAGMA table_info(planning_entries)")}
    position = int(conn.execute(
        "SELECT COALESCE(MAX(position),0) FROM planning_entries WHERE machine_id=?",
        (mac["id"],)).fetchone()[0]) + 1
    reference = (dos.get("reference") or of.get("of_numero") or "").strip()
    if not reference:
        raise HTTPException(400, "L'OF n'a pas de numéro : impossible de nommer le dossier.")
    row = {
        "machine_id": mac["id"], "position": position, "reference": reference,
        "client": dos.get("client") or "", "description": dos.get("description") or "",
        "format_l": dos.get("format_l"), "format_h": dos.get("format_h"),
        "duree_heures": DUREE_DEFAUT_H, "statut": "attente", "notes": "",
        "created_at": maintenant, "updated_at": maintenant,
        "numero_of": dos.get("numero_of") or reference, "ref_produit": dos.get("ref_produit"),
        "laize": dos.get("laize"), "date_livraison": dos.get("date_livraison"),
        "commentaire": dos.get("commentaire") or "",
        "a_placer": 1 if place == "a_placer" else 0, "valide": 0,
        "etiquettes_par_carton": dos.get("etiquettes_par_carton"),
        "created_by": qui, "updated_by": qui,
    }
    row = {c: v for c, v in row.items() if c in cols}
    conn.execute("INSERT INTO planning_entries (%s) VALUES (%s)" % (
        ", ".join(row), ", ".join("?" * len(row))), list(row.values()))
    entry_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    from app.routers.planning import _backfill_group_id
    try:
        _backfill_group_id(conn, entry_id, cols)
    except Exception:
        pass
    _promote_of_link(conn, entry_id, of["id"], qui)
    if p.get("commandes"):
        try:
            ratt.enregistrer(conn, "dossier", entry_id, "commande", p["commandes"], qui)
        except ValueError:
            pass
    _invalider_plans(conn, mac["id"])
    conn.commit()
    bilan = _bilan_dossier(conn, entry_id)
    log_action(user=user, action="CREATE", module="planning",
               objet="Dossier %s · %s" % (reference, mac["nom"]),
               detail={"machine_id": mac["id"],
                       "geste": "Ajouté depuis l'OF %s" % (of.get("of_numero") or "#%s" % of["id"]),
                       "Place": "À placer" if place == "a_placer" else "En fin de file"},
               request=request)
    return {"ok": True, "action": "creer", "entry_id": entry_id, "machine_id": mac["id"],
            "dossier": bilan, "ecrits": [], "gardes": [],
            "message": "Dossier %s ajouté au planning %s%s." % (
                reference, mac["nom"], " (à placer)" if place == "a_placer" else ", en fin de file")}


def _bilan_dossier(conn, entry_id: int) -> Dict[str, Any]:
    """Le dossier tel qu'il est APRÈS le geste, pour le récapitulatif."""
    r = conn.execute(
        "SELECT pe.*, m.nom AS machine_nom FROM planning_entries pe "
        "LEFT JOIN machines m ON m.id = pe.machine_id WHERE pe.id=?", (entry_id,)).fetchone()
    if not r:
        return {}
    d = dict(r)
    rang = None
    if d.get("statut") == "attente" and not int(d.get("a_placer") or 0):
        rang = conn.execute(
            "SELECT COUNT(*) FROM planning_entries WHERE machine_id=? AND statut='attente' "
            "AND COALESCE(a_placer,0)=0 AND position <= ?", (d["machine_id"], d["position"])).fetchone()[0]
    return {"id": d["id"], "reference": d.get("reference"), "machine_id": d.get("machine_id"),
            "machine": d.get("machine_nom"), "statut": d.get("statut"),
            "a_placer": bool(int(d.get("a_placer") or 0)), "rang": rang,
            "date_livraison": _jour(d.get("date_livraison")) or None,
            "debut": _heure(d.get("planned_start")) or None}


def _invalider_plans(conn, machine_id) -> None:
    try:
        from app.routers.planning import _invalidate_attente_plans
        _invalidate_attente_plans(conn, machine_id)
    except Exception:
        pass


# ── Depuis le dossier : créer son OF, ou relier un OF existant ────────────
#
# Le panneau OF d'un dossier sans OF (planning) proposait « Importer un PDF »
# et une recherche brute dans tous les OF (retour du 22/11/2026 : « ni
# esthétique, ni pratique »). Il propose désormais de CRÉER l'OF dans MySifa,
# prérempli depuis le dossier, et met en tête les OF qui lui correspondent.

def _ofs_suggeres(conn, d: Dict[str, Any], limite: int = 8) -> List[Dict[str, Any]]:
    """Les OF qui ressemblent à ce dossier : même numéro, mêmes lignes de
    commande, même produit. Les plus récents d'abord, jamais plus de `limite`."""
    raisons: Dict[int, str] = {}
    num = str(d.get("numero_of") or d.get("reference") or "").strip()
    if num and not reference_a_venir(num):
        for r in conn.execute("SELECT id FROM of_imports WHERE LOWER(TRIM(COALESCE(of_numero,'')))=LOWER(?)", (num,)):
            raisons.setdefault(int(r["id"]), "Même numéro")
    for l in ratt.lister(conn, "dossier", int(d["id"]), piece="commande"):
        for r in conn.execute(
                "SELECT objet_id AS id FROM rvgi_rattachements WHERE objet='of' AND piece='commande' "
                "AND numero=? AND (? IS NULL OR ligne IS NULL OR ligne=?)",
                (l["numero"], l.get("ligne"), l.get("ligne"))):
            raisons.setdefault(int(r["id"]), "Même commande")
    cle = _cle_produit(d.get("ref_produit"))
    if cle:
        for r in conn.execute(
                "SELECT id FROM of_imports WHERE LOWER(TRIM(COALESCE(reference,''))) = LOWER(?) "
                "OR LOWER(COALESCE(reference,'')) LIKE LOWER(?) ORDER BY date_import DESC, id DESC LIMIT 20",
                (cle, cle + " - %")):
            raisons.setdefault(int(r["id"]), "Même produit")
    if not raisons:
        return []
    ph = ",".join("?" * len(raisons))
    rows = conn.execute(
        "SELECT o.id, o.of_numero, o.reference, o.machine, o.delai_client, o.qte_etiquettes, "
        "o.date_import, o.imported_by, "
        "(SELECT GROUP_CONCAT(pe.reference, ', ') FROM planning_of_links l "
        "  JOIN planning_entries pe ON pe.id = l.planning_entry_id WHERE l.of_import_id = o.id) AS dossiers "
        "FROM of_imports o WHERE o.id IN (%s)" % ph, list(raisons)).fetchall()
    ordre = {"Même numéro": 0, "Même commande": 1, "Même produit": 2}
    etats = etat_des_of(conn, [int(r["id"]) for r in rows], d)
    out = []
    for r in rows:
        o = dict(r, raison=raisons[int(r["id"])], _etat=etats.get(int(r["id"])))
        e = o["_etat"] or {}
        # « Même produit » ne dit rien d'une production : seul un OF libre et
        # récent (préparé, pas encore planifié) mérite d'être proposé.
        if o["raison"] == "Même produit" and not (
                e.get("etat") == "libre" and e.get("age_jours") is not None and e["age_jours"] <= JOURS_RECENT):
            continue
        out.append(o)
    # Le plus sûr d'abord ; à rang égal, le plus récent.
    out.sort(key=lambda o: (ordre[o["raison"]], -_horodatage(o.get("date_import"))))
    return out[:limite]


def _horodatage(iso: Any) -> float:
    try:
        return datetime.fromisoformat(str(iso)[:19]).timestamp()
    except (TypeError, ValueError):
        return 0.0


# Un numéro de dossier SIFA EST souvent celui de la commande RVGI :
# « 9932911 », « 9932891 ligne 1 », « 9932723 - L1 ». Les dossiers du planning
# ne gardent presque jamais leur commande (4 sur 65 à produire au 26/11/2026).
_COMMANDE_RE = re.compile(r"\b(99\d{5})\b")
_LIGNE_RE = re.compile(r"(?:\bL|\bligne\s*)(\d{1,2})\b", re.IGNORECASE)


def commande_du_dossier(d: Dict[str, Any]):
    """(lignes, numéro) de la commande RVGI que le numéro du dossier désigne,
    ([], None) sinon. Une ligne citée (« L1 », « ligne 2 ») est prise seule ;
    sinon les lignes de l'article du dossier ; sinon la seule ligne s'il n'y
    en a qu'une. Jamais un choix au hasard entre plusieurs articles. Les
    dossiers « Stock … » et « Marché … » n'ont pas de commande."""
    texte = "%s %s" % (d.get("numero_of") or "", d.get("reference") or "")
    m = _COMMANDE_RE.search(texte)
    if not m:
        return [], None
    numero = m.group(1)
    try:
        groupes = ratt.chercher_commandes(numero)
    except Exception:
        return [], None
    g = next((g for g in groupes if str(g.get("numero")) == numero), None)
    if not g or not g.get("lignes"):
        return [], None
    lignes = g["lignes"]
    ml = _LIGNE_RE.search(texte)
    if ml:
        lignes = [l for l in lignes if str(l.get("ligne")) == ml.group(1)]
    else:
        cle = _cle_produit(d.get("ref_produit"))
        memes = [l for l in lignes if cle and str(l.get("article") or "").strip().lower() == cle.lower()]
        lignes = memes or (lignes if len(lignes) == 1 else [])
    if not lignes:
        return [], None
    return ([{"numero": numero, "ligne": l.get("ligne"), "qte": l.get("qte"),
              "vu_qte": l.get("qte"), "vu_article": l.get("article"), "vu_client": l.get("client"),
              "confirme": True} for l in lignes], numero)


@router.get("/api/of-planning/dossiers-sans-of")
def of_dossiers_sans_of(request: Request):
    """Les dossiers à produire qui n'ont pas d'OF : le point de départ
    « Partir d'un dossier du planning » de « Créer un OF » (26/11/2026)."""
    _require_of_access(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT pe.id, pe.reference, pe.numero_of, pe.ref_produit, pe.client, pe.statut,
                      pe.a_placer, pe.date_livraison, pe.planned_start, m.nom AS machine
                 FROM planning_entries pe LEFT JOIN machines m ON m.id = pe.machine_id
                WHERE pe.statut IN ('attente', 'en_cours') AND pe.of_import_id IS NULL
                  AND NOT EXISTS (SELECT 1 FROM planning_of_links l WHERE l.planning_entry_id = pe.id)
                ORDER BY COALESCE(pe.planned_start, pe.date_livraison, '9999') , pe.id""").fetchall()
    return {"items": [{
        "id": r["id"], "reference": r["reference"], "ref_produit": r["ref_produit"], "client": r["client"],
        "reservation": reference_a_venir(r["reference"]), "machine": r["machine"], "statut": r["statut"], "a_placer": bool(int(r["a_placer"] or 0)),
        "livraison": _jour(r["date_livraison"]) or None, "debut": _heure(r["planned_start"]) or None,
        "commande": (_COMMANDE_RE.search("%s %s" % (r["numero_of"] or "", r["reference"] or "")) or [None, None])[1],
    } for r in rows]}


@router.get("/api/of/planning/dossier/{entry_id}")
def of_depuis_dossier(entry_id: int, request: Request):
    """Ce qu'il faut pour ouvrir « Nouvel OF » sur ce dossier, et les OF
    qui lui correspondent déjà."""
    _require_of_access(request)
    from app.services.fiche_choix import choisir_fiche
    with get_db() as conn:
        r = conn.execute(
            "SELECT pe.*, m.nom AS machine_nom FROM planning_entries pe "
            "LEFT JOIN machines m ON m.id = pe.machine_id WHERE pe.id=?", (entry_id,)).fetchone()
        if not r:
            raise HTTPException(404, "Dossier introuvable.")
        d = dict(r)
        commandes = [{"numero": l["numero"], "ligne": l.get("ligne"), "qte": l.get("qte")}
                     for l in ratt.lister(conn, "dossier", entry_id, piece="commande")]
        retrouvee = None
        if not commandes:
            commandes, retrouvee = commande_du_dossier(d)
        fiche = None
        if d.get("ref_produit"):
            try:
                fiche = choisir_fiche(conn, d["ref_produit"], d.get("machine_nom"), d.get("laize"),
                                      colonnes="id, reference, machine")
            except Exception:
                fiche = None
        suggestions = _ofs_suggeres(conn, d)
    return {
        # Réservation « ???? » : le numéro est à venir, il ne préremplit rien.
        "dossier": {"id": d["id"], "reference": d.get("reference"),
                    "reservation": reference_a_venir(d.get("reference")),
                    "numero_of": None if reference_a_venir(d.get("numero_of") or d.get("reference"))
                    else ((d.get("numero_of") or d.get("reference") or "").strip() or None),
                    "ref_produit": d.get("ref_produit"), "machine": d.get("machine_nom"),
                    "date_livraison": str(d.get("date_livraison") or "")[:10] or None,
                    "client": d.get("client")},
        "commandes": commandes,
        "commande_retrouvee": retrouvee,
        "fiche": ({"id": fiche["id"], "reference": fiche.get("reference")} if fiche else None),
        "suggestions": [dict(_ligne_of(o, o.get("_etat"), o["raison"]), dossiers=o.get("dossiers"))
                        for o in suggestions],
    }


# ── Supprimer un OF relié à un dossier ────────────────────────────────────
#
# Constat du 22/11/2026 : supprimer un OF effaçait la ligne et rien d'autre.
# La base n'applique pas ON DELETE CASCADE (PRAGMA foreign_keys désactivé) :
# le dossier gardait un lien vers un OF disparu, perdait sa quantité au
# planning et son chiffrage dans Besoins matières, sans que personne n'ait été
# prévenu ni que le geste soit tracé.

def dossiers_des_of(conn, ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    """Les dossiers reliés à chaque OF, avec l'OF qui prendrait le relais."""
    if not ids:
        return {}
    ph = ",".join("?" * len(ids))
    rows = conn.execute(
        f"""SELECT DISTINCT x.of_id, pe.id, pe.reference, pe.statut, pe.a_placer, pe.machine_id,
                   m.nom AS machine
              FROM (SELECT of_import_id AS of_id, planning_entry_id AS pe_id FROM planning_of_links
                     WHERE of_import_id IN ({ph})
                    UNION SELECT of_import_id, id FROM planning_entries WHERE of_import_id IN ({ph})) x
              JOIN planning_entries pe ON pe.id = x.pe_id
              LEFT JOIN machines m ON m.id = pe.machine_id""", list(ids) * 2).fetchall()
    out: Dict[int, List[Dict[str, Any]]] = {}
    for r in rows:
        relais = conn.execute(
            f"""SELECT o.of_numero FROM planning_of_links l JOIN of_imports o ON o.id = l.of_import_id
                 WHERE l.planning_entry_id = ? AND l.of_import_id NOT IN ({ph})
                 ORDER BY l.position, l.id LIMIT 1""", [r["id"]] + list(ids)).fetchone()
        out.setdefault(int(r["of_id"]), []).append({
            "id": r["id"], "reference": r["reference"], "statut": r["statut"],
            "a_placer": bool(int(r["a_placer"] or 0)), "machine_id": r["machine_id"],
            "machine": r["machine"], "relais": relais["of_numero"] if relais else None})
    return out


def detacher_of(conn, ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    """Retire les liens des OF `ids` avant leur suppression. Le dossier prend
    son OF suivant s'il en a un, sinon il repasse sans OF (« Dossiers sans
    OF »). Les scans gardent leur numéro, perdent l'id. Ne committe pas."""
    if not ids:
        return {}
    touches = dossiers_des_of(conn, ids)
    ph = ",".join("?" * len(ids))
    # Le trigger trg_planning_of_links_after_delete recalcule of_import_id
    # sur le lien restant, ou NULL s'il n'y en a plus.
    conn.execute(f"DELETE FROM planning_of_links WHERE of_import_id IN ({ph})", ids)
    conn.execute(f"UPDATE planning_entries SET of_import_id = NULL WHERE of_import_id IN ({ph})", ids)
    for sql in (f"UPDATE produit_documents SET of_import_id = NULL WHERE of_import_id IN ({ph})",
                f"DELETE FROM rvgi_rattachements WHERE objet = 'of' AND objet_id IN ({ph})"):
        try:
            conn.execute(sql, ids)
        except Exception:
            pass   # base ancienne sans la table
    return touches


def journaliser_suppression(user, request, of_numeros: Dict[int, str],
                            touches: Dict[int, List[Dict[str, Any]]]) -> None:
    """Une ligne par OF (journal), une par dossier touché (historique de sa
    machine au planning)."""
    for of_id, numero in of_numeros.items():
        ds = touches.get(of_id) or []
        log_action(user=user, action="DELETE", module="of", objet="OF %s" % numero,
                   detail={"dossiers": [d["reference"] for d in ds]}, request=request)
        for d in ds:
            log_action(user=user, action="UPDATE", module="planning",
                       objet="Dossier %s · %s" % (d["reference"], d.get("machine") or ""),
                       detail={"machine_id": d["machine_id"], "geste": "OF %s supprimé" % numero,
                               "OF actif": d["relais"] or "aucun, dossier sans OF"},
                       request=request)


@router.post("/api/of/suppression/apercu")
async def of_suppression_apercu(request: Request):
    """Ce que la suppression de ces OF changerait au planning, pour la
    confirmation. Lecture seule."""
    _require_of_access(request)
    body = await request.json()
    ids = [int(i) for i in (body.get("ids") or []) if str(i).isdigit()][:500]
    with get_db() as conn:
        touches = dossiers_des_of(conn, ids)
        nums = {int(r["id"]): r["of_numero"] for r in conn.execute(
            "SELECT id, of_numero FROM of_imports WHERE id IN (%s)" % ",".join("?" * len(ids)), ids)} if ids else {}
    return {"ofs": [{"id": i, "of_numero": nums.get(i), "dossiers": touches.get(i, [])}
                    for i in ids if touches.get(i)]}


# ── Un OF déjà produit ne se réutilise pas ───────────────────────────────
#
# Retour du 22/11/2026 : le sélecteur proposait, au nom du « même produit »,
# des OF d'octobre 2025 et d'avril 2026 pour un dossier de septembre. Mais
# un OF sert légitimement plusieurs passes d'une même production : 9931710
# (4 dossiers, Cohésio 1 puis 2), 9932304 (DSI puis Repiquage). Ces passes
# portent la MÊME référence de dossier et naissent avant la fin de la
# précédente. Le cas fautif, lui : 1153/0005 - 01/04/26, produit fin juin,
# relié en novembre au dossier « Stock 1153/0005 ».
#
# Un OF est donc « déjà produit » pour un dossier quand il a un scan d'OF
# terminé, ou quand tous ses dossiers sont terminés depuis plus de
# `JOURS_PRODUIT` jours sous une autre référence.

JOURS_PRODUIT = 14       # fin de la dernière passe au-delà : l'OF est clos
JOURS_RECENT = 30        # « même produit » : un OF libre et récent seulement
JOURS_ANCIEN = 90        # libre mais plus vieux : sûrement produit hors MySifa


def _norm_ref(v: Any) -> str:
    return " ".join(str(v or "").lower().split())


def _jours_depuis(iso: Any) -> Optional[float]:
    s = str(iso or "")[:19]
    if not s:
        return None
    try:
        return (datetime.now() - datetime.fromisoformat(s)).total_seconds() / 86400
    except ValueError:
        return None


def etat_des_of(conn, ids: List[int], cible: Optional[Dict[str, Any]] = None) -> Dict[int, Dict[str, Any]]:
    """L'état de réutilisation de chaque OF vu depuis le dossier `cible`.

    `etat` : libre, deja (relié à ce dossier), passe (même référence que ce
    dossier), en_cours, recent, ancien, produit. `selectionnable` est faux
    seulement pour `produit` et `deja`. `note` dit pourquoi, en clair.
    """
    if not ids:
        return {}
    ph = ",".join("?" * len(ids))
    ofs = {int(r["id"]): dict(r) for r in conn.execute(
        f"SELECT id, of_numero, date_creation, date_import FROM of_imports WHERE id IN ({ph})", ids)}
    liens: Dict[int, List[Dict[str, Any]]] = {}
    for r in conn.execute(
            f"""SELECT x.of_id, pe.id, pe.reference, pe.statut, pe.planned_end, pe.updated_at,
                       (SELECT MAX(pd.date_operation) FROM production_data pd
                         WHERE pd.no_dossier = pe.reference AND pd.operation_code = '89'
                           AND COALESCE(pd.est_annule, 0) = 0) AS fin_reelle
                  FROM (SELECT of_import_id AS of_id, planning_entry_id AS pe_id FROM planning_of_links
                         WHERE of_import_id IN ({ph})
                        UNION SELECT of_import_id, id FROM planning_entries WHERE of_import_id IN ({ph})) x
                  JOIN planning_entries pe ON pe.id = x.pe_id""", list(ids) * 2):
        liens.setdefault(int(r["of_id"]), []).append(dict(r))
    scans = set()
    try:
        for r in conn.execute(
                f"""SELECT o.id FROM of_imports o WHERE o.id IN ({ph}) AND EXISTS (
                      SELECT 1 FROM produit_documents d WHERE d.of_import_id = o.id
                         OR (TRIM(COALESCE(o.of_numero,'')) <> ''
                             AND LOWER(TRIM(COALESCE(d.of_numero,''))) = LOWER(TRIM(o.of_numero))))""", ids):
            scans.add(int(r["id"]))
    except Exception:
        pass
    cible_id = int(cible["id"]) if cible and cible.get("id") else None
    cible_ref = _norm_ref((cible or {}).get("reference"))
    out: Dict[int, Dict[str, Any]] = {}
    for of_id in ids:
        of = ofs.get(of_id)
        if not of:
            continue
        ds = liens.get(of_id, [])
        autres = [d for d in ds if int(d["id"]) != cible_id]
        cree = _date_iso(of.get("date_creation")) or str(of.get("date_import") or "")[:10]
        age = _jours_depuis(cree)
        def dossier_txt(d):
            return "%s (%s)" % (d.get("reference") or "#%s" % d["id"],
                                {"attente": "en attente", "en_cours": "en cours", "termine": "terminé"}.get(d.get("statut"), d.get("statut") or ""))
        etat, note = "libre", None
        if cible_id and any(int(d["id"]) == cible_id for d in ds):
            etat, note = "deja", "déjà relié à ce dossier"
        elif of_id in scans:
            etat, note = "produit", "déjà produit (scan de l'OF terminé) : créez un nouvel OF"
        elif autres and cible_ref and any(_norm_ref(d.get("reference")) == cible_ref for d in autres):
            etat, note = "passe", "même dossier sur une autre passe : ce dossier sera une passe de plus"
        elif any(d.get("statut") in ("attente", "en_cours") for d in autres):
            d = next(d for d in autres if d.get("statut") in ("attente", "en_cours"))
            etat, note = "en_cours", "déjà sur le dossier %s : ce dossier sera une passe de plus" % dossier_txt(d)
        elif autres:
            fins = [d.get("fin_reelle") or d.get("planned_end") or d.get("updated_at") for d in autres]
            fin = max((f for f in fins if f), default=None)
            jours = _jours_depuis(fin)
            dernier = max(autres, key=lambda d: str(d.get("fin_reelle") or d.get("planned_end") or ""))
            if jours is not None and jours <= JOURS_PRODUIT:
                etat, note = "recent", "dernière passe (dossier %s) terminée le %s : ce dossier sera une passe de plus" % (
                    dernier.get("reference"), _jour(fin))
            else:
                etat, note = "produit", "déjà produit (dossier %s terminé%s) : créez un nouvel OF" % (
                    dernier.get("reference"), (" le " + _jour(fin)) if fin else "")
        elif age is not None and age > JOURS_ANCIEN:
            etat, note = "ancien", "OF du %s jamais planifié : probablement produit hors MySifa" % _jour(cree)
        out[of_id] = {"etat": etat, "selectionnable": etat not in ("produit", "deja"), "note": note,
                      "age_jours": age}
    return out


def verifier_reutilisable(conn, of_ids: List[int], entry_id: int) -> None:
    """Refuse de relier à `entry_id` un OF déjà produit (409). Les passes du
    même dossier et un OF encore en production restent permises."""
    r = conn.execute("SELECT id, reference FROM planning_entries WHERE id=?", (entry_id,)).fetchone()
    if not r:
        return
    etats = etat_des_of(conn, [int(i) for i in of_ids], dict(r))
    bloques = [(i, e) for i, e in etats.items() if e["etat"] == "produit"]
    if bloques:
        nums = {int(x["id"]): x["of_numero"] for x in conn.execute(
            "SELECT id, of_numero FROM of_imports WHERE id IN (%s)" % ",".join("?" * len(bloques)),
            [i for i, _ in bloques])}
        raise HTTPException(409, "OF %s %s." % (nums.get(bloques[0][0]) or bloques[0][0], bloques[0][1]["note"]))


@router.get("/api/of/planning/dossier/{entry_id}/recherche")
def of_recherche_pour_dossier(entry_id: int, request: Request):
    """La recherche d'OF du panneau d'un dossier, avec l'état de chacun vu
    depuis ce dossier (libre, déjà produit…)."""
    _require_of_access(request)
    q = (request.query_params.get("q") or "").strip()
    if not q:
        return {"items": []}
    like = "%" + q + "%"
    with get_db() as conn:
        d = conn.execute("SELECT id, reference FROM planning_entries WHERE id=?", (entry_id,)).fetchone()
        rows = [dict(r) for r in conn.execute(
            "SELECT id, of_numero, reference, machine, delai_client, qte_etiquettes, date_import, imported_by "
            "FROM of_imports WHERE LOWER(COALESCE(of_numero,'')) LIKE LOWER(?) "
            "OR LOWER(COALESCE(reference,'')) LIKE LOWER(?) OR LOWER(COALESCE(machine,'')) LIKE LOWER(?) "
            "ORDER BY date_import DESC, id DESC LIMIT 20", (like, like, like))]
        etats = etat_des_of(conn, [r["id"] for r in rows], dict(d) if d else None)
    return {"items": [_ligne_of(r, etats.get(r["id"]), None) for r in rows]}


def _ligne_of(o: Dict[str, Any], etat: Optional[Dict[str, Any]], raison: Optional[str]) -> Dict[str, Any]:
    return {"id": o["id"], "of_numero": o.get("of_numero"), "reference": o.get("reference"),
            "machine": o.get("machine"),
            "delai": _jour(_date_iso(o.get("delai_client"))) or o.get("delai_client"),
            "qte": o.get("qte_etiquettes"), "cree_le": _jour(o.get("date_import")),
            "par": ("le pont Access" if o.get("imported_by") == "access_bridge" else o.get("imported_by")),
            "raison": raison, "etat": (etat or {}).get("etat", "libre"),
            "selectionnable": (etat or {}).get("selectionnable", True), "note": (etat or {}).get("note")}
