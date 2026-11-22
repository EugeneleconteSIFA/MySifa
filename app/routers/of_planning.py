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

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request

from database import get_db
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
    if champ in ("numero_of", "ref_produit"):
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


def ecarts(dossier: Dict[str, Any], vals: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Les valeurs de l'OF qui diffèrent du dossier. Une valeur que l'OF ne
    porte pas n'efface jamais celle du dossier."""
    actuel = {
        "numero_of": dossier.get("numero_of"),
        "ref_produit": dossier.get("ref_produit"),
        "date_livraison": dossier.get("date_livraison"),
        "laize": _nombre(dossier.get("laize")),
        "format": _format_dossier(dossier),
    }
    modifiable = (dossier.get("statut") or "attente") == "attente"
    out = []
    for champ, libelle in CHAMPS:
        neuf = vals.get(champ)
        if neuf in (None, "") or _egal(champ, actuel[champ], neuf):
            continue
        motif = None
        if not modifiable:
            motif = "Dossier %s : il n'est plus modifié depuis l'OF." % (
                "en cours" if dossier.get("statut") == "en_cours" else "terminé")
        elif champ == "date_livraison" and int(dossier.get("date_livraison_imposee") or 0):
            motif = "Délai imposé au planning."
        out.append({"champ": champ, "libelle": libelle,
                    "avant": _affiche(champ, actuel[champ]), "apres": _affiche(champ, neuf),
                    "modifiable": motif is None, "motif": motif})
    return out


def candidats(conn, of_id: Optional[int], numero: Optional[str],
              commandes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Les dossiers qui correspondent à cet OF, le plus sûr d'abord.

    1. déjà relié à l'OF (quel que soit son état) ;
    2. même numéro d'OF ou même référence de dossier ;
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
    ordre = {"Relié à cet OF": 0, "Même numéro d'OF": 1}
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


def _public(d: Dict[str, Any], vals: Dict[str, Any], of_id: Optional[int]) -> Dict[str, Any]:
    relie_ailleurs = bool(d.get("of_import_id")) and of_id and int(d["of_import_id"]) != int(of_id)
    return {
        "apercu": _apercu(d),
        "id": d["id"], "reference": d.get("reference"), "machine_id": d.get("machine_id"),
        "machine": d.get("machine_nom"), "statut": d.get("statut"),
        "a_placer": bool(int(d.get("a_placer") or 0)), "rang": d.get("_rang"),
        "date_livraison": _jour(d.get("date_livraison")) or None,
        "raison": d["_raison"],
        "of_relie": d.get("of_relie") if (relie_ailleurs or (not of_id and d.get("of_import_id"))) else None,
        "deja_relie": bool(of_id) and d["_raison"] == "Relié à cet OF",
        "ecarts": ecarts(d, vals),
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
        dossiers = candidats(conn, of_id, vals["numero_of"], commandes)
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
    return {
        "of_meme_numero": meme_numero,
        "dossiers": [_public(d, vals, of_id) for d in dossiers[:5]],
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
    _promote_of_link(conn, entry_id, of["id"], qui)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(planning_entries)")}
    sets: Dict[str, Any] = {}
    if "of_link_user_managed" in cols:
        sets["of_link_user_managed"] = 1
    vals = valeurs_de_l_of(of)
    voulus = {c for c in champs if isinstance(c, str)}
    ecrits = []
    for e in ecarts(d, vals):
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
    log_action(user=user, action="UPDATE", module="planning",
               objet="Dossier %s · OF %s" % (d.get("reference") or entry_id, of.get("of_numero") or of["id"]),
               detail={"relie_of": of["id"], "champs": {e["champ"]: [e["avant"], e["apres"]] for e in ecrits}},
               request=request)
    n = len(ecrits)
    return {"ok": True, "entry_id": entry_id, "machine_id": d["machine_id"],
            "message": "OF relié au dossier %s%s." % (
                d.get("reference") or entry_id,
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
    log_action(user=user, action="CREATE", module="planning",
               objet="Dossier %s · %s" % (reference, mac["nom"]),
               detail={"depuis_of": of["id"], "a_placer": place == "a_placer"}, request=request)
    return {"ok": True, "entry_id": entry_id, "machine_id": mac["id"],
            "message": "Dossier %s ajouté au planning %s%s." % (
                reference, mac["nom"], " (à placer)" if place == "a_placer" else ", en fin de file")}


def _invalider_plans(conn, machine_id) -> None:
    try:
        from app.routers.planning import _invalidate_attente_plans
        _invalidate_attente_plans(conn, machine_id)
    except Exception:
        pass
