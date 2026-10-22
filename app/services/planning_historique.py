"""MySifa — Historique des modifications du Planning de production.

Lit `audit_logs` (module `planning`) et le rend lisible pour la fenêtre
« Historique des modifications » de la page Planning : qui, quand, sur quelle
machine, quoi, et la valeur avant → après quand le journal la connaît.

Le journal mélange trois formes de ligne, et ce module les ramène à une seule :

1. `_journal_horaires` (planning.py) : `{"avant": …, "apres": …}` ;
2. les `log_action` métier : un dict libre (`reference`, `duree_heures`,
   `geste`…) ou une phrase ;
3. le middleware : `{"methode", "chemin", "donnees"}` avec un objet technique
   (« Set day horaires · machine_id=3 »), qu'on renomme d'après la route.

La machine d'une ligne se déduit de son chemin (`/machines/3/`), de ses
identifiants (`machine_id`, `machine_source`, `machine_cible`) ou du nom de
machine écrit dans l'objet. Les lignes métier anciennes qui ne portent rien de
tout ça restent visibles sous « Toutes les machines ».
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from app.core.audit_taxonomy import action_color, action_label

LIMITE_MAX = 200

# Le rafraîchissement automatique de la timeline (POST /live-refresh) n'est pas
# un geste humain : ~1 400 lignes par jour avant d'être exclu du journal.
_BRUIT = "Live refresh%"

_RE_MACHINE = re.compile(r"/machines/(\d+)/")
_RE_SUFFIXE_ID = re.compile(r"\s·\smachine_id=\d+.*$")

# Lignes du middleware : dernier segment de la route → libellé. `{date}`,
# `{semaine}`, `{day}` sont pris dans les données envoyées.
_TITRES_ROUTE = {
    "day-horaires": "Horaires du {date}",
    "day-work": "Jour travaillé du {date}",
    "holidays": "Jour off du {date}",
    "horaires-parity": "Horaires semaines paires / impaires",
    "horaires-bulk": "Horaires machine (semaine type)",
    "horaires": "Horaires machine du {day}",
    "config": "Réglage de la semaine {semaine}",
    "week-comment": "Commentaire de la semaine {semaine}",
    "day-comment": "Commentaire du {date}",
    "journee-entiere": "Journée entière par défaut",
    "reset-default-days": "Réinitialisation des jours",
    "pack-termines": "Recalage des terminés",
    "pack-attente": "Recalage des en attente",
    "pack-termines-before-en-cours": "Terminés replacés avant le dossier en cours",
    "import-orphan": "Import d'un dossier terminé",
    "reorder": "Réorganisation du planning",
    "split": "Scission d'un dossier",
    "deplacer": "Déplacement d'un dossier",
    "changer-machine": "Changement de machine",
    "statut": "Statut d'un dossier",
    "destockage": "Repère déstockage",
    "etiquettes-par-carton": "Étiquettes par carton",
}

_LIBELLES = {
    "heure_debut": "Début",
    "heure_fin": "Fin",
    "journee_entiere": "Journée entière",
    "is_worked": "Travaillé",
    "is_off": "Non travaillé",
    "off": "Non travaillé",
    "label": "Libellé",
    "libelle": "Libellé",
    "samedi_travaille": "Samedi travaillé",
    "notes": "Notes",
    "comment": "Commentaire",
    "duree_heures": "Durée (h)",
    "duree": "Durée (h)",
    "duree_1": "Durée partie 1 (h)",
    "duree_2": "Durée partie 2 (h)",
    "reference": "Référence",
    "statut": "Statut",
    "override": "Forcé",
    "geste": "Geste",
    "rang": "Rang",
    "en_tete": "En tête",
    "apres_id": "Après le dossier n°",
    "machine_source": "Machine d'origine",
    "machine_cible": "Machine cible",
    "entry_ids": "Dossiers",
    "sans_matiere_premiere": "Sans matière première",
    "hors_production": "Hors production",
    "cloture_fin_prevue": "Clôture à la fin prévue",
    "notif_admin": "Admin prévenu",
    "affiche_avant": "Affiché avant",
    "jours_feries_ou_off": "Jours off enregistrés",
    "jours_forces": "Jours forcés",
    "horaires_lundi": "Lundi",
    "horaires_mardi": "Mardi",
    "horaires_mercredi": "Mercredi",
    "horaires_jeudi": "Jeudi",
    "horaires_vendredi": "Vendredi",
    "horaires_samedi": "Samedi",
    # Champs d'un dossier (planning_entries)
    "client": "Client",
    "description": "Description",
    "format_l": "Format largeur (mm)",
    "format_h": "Format hauteur (mm)",
    "numero_of": "N° OF",
    "ref_produit": "Réf. produit",
    "laize": "Laize (mm)",
    "date_livraison": "Livraison",
    "date_livraison_imposee": "Date de livraison imposée",
    "commentaire": "Commentaire",
    "statut_force": "Statut forcé",
    "dos_rvgi": "Dossier RVGI",
    "a_placer": "À placer",
    "destockage": "Déstockage",
    "destockage_rvgi": "Déstockage RVGI",
    "exigences_production": "Exigences de production",
    "fsc_requis": "FSC requis",
    "fsc_type_requis": "Type FSC",
    "departement_livraison": "Département de livraison",
    "prise_rdv": "Prise de RDV",
    "valide": "Validé",
    "etiquettes_par_carton": "Étiquettes par carton",
    "planned_end_manual": "Fin fixée à la main",
    "pair": "Paire",
    "impair": "Impaire",
    "week": "lun–jeu",
    "fri": "ven",
}
_DRAPEAUX = {
    "journee_entiere", "is_worked", "is_off", "off", "samedi_travaille", "override",
    "en_tete", "sans_matiere_premiere", "hors_production", "cloture_fin_prevue",
    "notif_admin", "a_placer", "date_livraison_imposee", "statut_force", "fsc_requis", "prise_rdv",
    "valide", "planned_end_manual",
}
_GESTES = {"en_tete": "Placé en tête", "apres": "Placé après un dossier",
           "changer_machine": "Changé de machine"}
# Clés techniques qui n'apprennent rien au lecteur.
_MASQUEES = {"machine_id", "inchange", "confirme_gel", "motif_gel"}
_STATUTS = {"attente": "En attente", "en_cours": "En cours", "termine": "Terminé"}


# ── Mise en forme ───────────────────────────────────────────────────────────

def _quand(created_at: Optional[str]) -> tuple[str, str]:
    """(jour ISO, 'JJ/MM/AAAA HH:MM') en heure de Paris. `created_at` est en UTC."""
    s = str(created_at or "").strip().replace(" ", "T")[:19]
    try:
        dt = datetime.fromisoformat(s).replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Europe/Paris"))
    except ValueError:
        return s[:10], s.replace("T", " ")[:16]
    return dt.strftime("%Y-%m-%d"), dt.strftime("%d/%m/%Y %H:%M")


def _hm(h: Any) -> str:
    try:
        tot = int(round(float(h) * 60))
    except (TypeError, ValueError):
        return str(h)
    return f"{tot // 60:02d}:{tot % 60:02d}"


def _date_fr(v: Any) -> str:
    try:
        d = datetime.strptime(str(v), "%Y-%m-%d")
    except ValueError:
        return str(v)
    return ("lun", "mar", "mer", "jeu", "ven", "sam", "dim")[d.weekday()] + d.strftime(" %d/%m/%Y")


def _valeur(cle: str, v: Any, machines: Dict[int, str]) -> str:
    if v is None or v == "":
        return "—"
    if cle in _DRAPEAUX:
        return "Oui" if v in (1, True, "1", "true") else "Non"
    if cle in ("heure_debut", "heure_fin"):
        return _hm(v)
    if cle.startswith("horaires_") and isinstance(v, str) and "," in v:
        # Format des colonnes machines.horaires_* : « 5,21 » ou « 05:25,20:35 ».
        a, b = (x.strip() for x in v.split(",", 1))
        return "–".join(x if ":" in x else _hm(x) for x in (a, b))
    if cle in ("machine_source", "machine_cible"):
        try:
            return machines.get(int(v), f"Machine {v}")
        except (TypeError, ValueError):
            return str(v)
    if cle == "geste":
        return _GESTES.get(str(v), str(v))
    if cle == "statut":
        return _STATUTS.get(str(v), str(v))
    if cle in ("date", "date_livraison"):
        return _date_fr(str(v)[:10]) if re.match(r"^\d{4}-\d{2}-\d{2}", str(v)) else str(v)
    if isinstance(v, bool):
        return "Oui" if v else "Non"
    if isinstance(v, list):
        return f"{len(v)} dossier(s)" if cle == "entry_ids" else ", ".join(str(x) for x in v[:8])
    if isinstance(v, dict):
        if set(v) >= {"s", "e"}:
            return f"{_hm(v['s'])}–{_hm(v['e'])}"
        return " · ".join(f"{_LIBELLES.get(k, k)} {_valeur(k, x, machines)}" for k, x in v.items())
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def _aplatir(d: Any, prefixe: str = "") -> Dict[str, Any]:
    """{'pair': {'week': '05:00–13:00'}} → {'Paire lun–jeu': ('week', '05:00–13:00')}."""
    out: Dict[str, Any] = {}
    if not isinstance(d, dict) or (set(d) >= {"s", "e"} and len(d) == 2):
        out[prefixe or "Valeur"] = ("", d)
        return out
    for k, v in d.items():
        lib = _LIBELLES.get(k, k)
        nom = f"{prefixe} {lib}".strip()
        if isinstance(v, dict) and not (set(v) >= {"s", "e"}):
            out.update(_aplatir(v, nom))
        else:
            out[nom] = (k, v)
    return out


def _lignes_avant_apres(detail: dict, machines: Dict[int, str]) -> List[dict]:
    avant, apres = detail.get("avant"), detail.get("apres")
    lignes: List[dict] = []
    if isinstance(avant, dict) or isinstance(apres, dict):
        a = _aplatir(avant or {})
        b = _aplatir(apres or {})
        for nom in list(dict.fromkeys([*a.keys(), *b.keys()])):
            ka, va = a.get(nom, (None, None))
            kb, vb = b.get(nom, (None, None))
            cle = ka or kb or ""
            ta, tb = _valeur(cle, va, machines), _valeur(cle, vb, machines)
            if ta != tb or detail.get("inchange"):
                lignes.append({"champ": nom, "avant": ta, "apres": tb})
    else:
        lignes.append({
            "champ": "Valeur",
            "avant": "aucun réglage enregistré" if avant is None else _valeur("", avant, machines),
            "apres": "réglage retiré" if apres is None else _valeur("", apres, machines),
        })
    for k, v in detail.items():
        if k in ("avant", "apres") or k in _MASQUEES:
            continue
        lignes.append({"champ": _LIBELLES.get(k, k), "valeur": _valeur(k, v, machines)})
    return lignes


def _lignes_dict(d: dict, machines: Dict[int, str], deja: set) -> List[dict]:
    if set(d) >= {"old", "new"}:
        return [{"champ": "Valeur", "avant": _valeur("", d.get("old"), machines),
                 "apres": _valeur("", d.get("new"), machines)}]
    lignes = []
    for k, v in d.items():
        if k in deja or k in _MASQUEES:
            continue
        if k in ("pair", "impair") and isinstance(v, dict):
            for slot, h in v.items():
                lignes.append({"champ": f"{_LIBELLES[k]} {_LIBELLES.get(slot, slot)}",
                               "valeur": _valeur(slot, h, machines)})
            continue
        lignes.append({"champ": _LIBELLES.get(k, k), "valeur": _valeur(k, v, machines)})
    return lignes


def _titre_route(chemin: str, donnees: dict) -> Optional[tuple[str, set]]:
    segs = [s for s in chemin.strip("/").split("/") if s]
    for seg in reversed(segs):
        if seg in _TITRES_ROUTE:
            modele = _TITRES_ROUTE[seg]
            utilises = set(re.findall(r"\{(\w+)\}", modele))
            vals = {k: (_date_fr(donnees.get(k)) if k == "date" else donnees.get(k, "?"))
                    for k in utilises}
            return modele.format(**vals), utilises
    return None


def _machine_de(detail: Any, objet: str, machines: Dict[int, str]) -> Optional[int]:
    if isinstance(detail, dict):
        m = _RE_MACHINE.search(str(detail.get("chemin") or ""))
        if m:
            return int(m.group(1))
        for k in ("machine_id", "machine_source"):
            try:
                if detail.get(k) is not None:
                    return int(detail[k])
            except (TypeError, ValueError):
                pass
    # Nom le plus long d'abord : « Cohésio 10 » ne doit pas tomber sur « Cohésio 1 ».
    for mid, nom in sorted(machines.items(), key=lambda x: -len(x[1])):
        if nom and nom in (objet or ""):
            return mid
    return None


def mettre_en_forme(row: dict, machines: Dict[int, str]) -> dict:
    objet = str(row.get("objet") or "")
    brut = row.get("detail")
    try:
        detail = json.loads(brut) if brut else None
    except (TypeError, ValueError):
        detail = brut
    titre = _RE_SUFFIXE_ID.sub("", objet)
    lignes: List[dict] = []
    mid = _machine_de(detail, objet, machines)

    if isinstance(detail, dict) and ("avant" in detail or "apres" in detail):
        lignes = _lignes_avant_apres(detail, machines)
    elif isinstance(detail, dict) and "chemin" in detail:
        donnees = detail.get("donnees") if isinstance(detail.get("donnees"), dict) else {}
        t = _titre_route(str(detail["chemin"]), donnees)
        deja: set = set()
        if t:
            titre, deja = t
        lignes = _lignes_dict(donnees, machines, deja)
    elif isinstance(detail, dict):
        lignes = _lignes_dict(detail, machines, set())
    elif detail:
        lignes = [{"champ": "", "valeur": str(detail)}]

    # La machine a sa pastille et l'absence de changement sa mention : le titre
    # n'a pas à les répéter.
    titre = titre.replace(" (inchangé)", "")
    nom_m = machines.get(mid) if mid is not None else None
    if nom_m and titre.startswith(nom_m + " · "):
        titre = titre[len(nom_m) + 3:]
    elif nom_m and titre.endswith(" · " + nom_m):
        titre = titre[: -(len(nom_m) + 3)]
    elif nom_m and titre.endswith(" " + nom_m):           # « Réorganisation planning Cohésio 1 »
        titre = titre[: -(len(nom_m) + 1)]
    jour, quand = _quand(row.get("created_at"))
    action = str(row.get("action") or "")
    return {
        "id": row.get("id"),
        "jour": jour,
        "quand": quand,
        "utilisateur": row.get("user_nom") or "—",
        "action": action,
        "action_label": action_label(action),
        "action_couleur": action_color(action),
        "machine_id": mid,
        "machine": machines.get(mid) if mid is not None else None,
        "titre": titre,
        "inchange": bool(isinstance(detail, dict) and (
            detail.get("inchange")
            or ("avant" in detail and "apres" in detail and detail["avant"] == detail["apres"])
        )),
        "lignes": lignes,
    }


# ── Lecture ─────────────────────────────────────────────────────────────────

def _filtres(machines: Dict[int, str], machine_id: Optional[int], utilisateur: str,
             action: str, jours: Optional[int], q: str) -> tuple[str, list]:
    cond = ["module = 'planning'", "objet NOT LIKE ?"]
    params: list = [_BRUIT]
    if machine_id is not None:
        ou = [
            "detail LIKE ?",
            "(CASE WHEN json_valid(detail) THEN "
            " COALESCE(json_extract(detail,'$.machine_id'), -1) = ? "
            " OR COALESCE(json_extract(detail,'$.machine_source'), -1) = ? "
            " OR COALESCE(json_extract(detail,'$.machine_cible'), -1) = ? "
            " ELSE 0 END)",
        ]
        params += [f"%/machines/{machine_id}/%", machine_id, machine_id, machine_id]
        nom = machines.get(machine_id)
        if nom:
            # « Cohésio 1 » est contenu dans « Cohésio 10 » : on écarte les noms
            # plus longs qui commencent par celui-ci.
            plus_longs = [v for k, v in machines.items() if k != machine_id and v.startswith(nom)]
            ou.append("(objet LIKE ?" + " AND objet NOT LIKE ?" * len(plus_longs) + ")")
            params += [f"%{nom}%"] + [f"%{v}%" for v in plus_longs]
        cond.append("(" + " OR ".join(ou) + ")")
    if utilisateur:
        cond.append("user_nom = ?")
        params.append(utilisateur)
    if action:
        cond.append("action = ?")
        params.append(action.upper())
    if jours:
        depuis = datetime.utcnow() - timedelta(days=int(jours))
        cond.append("created_at >= ?")
        params.append(depuis.strftime("%Y-%m-%dT%H:%M:%S"))
    if q:
        cond.append("(objet LIKE ? OR user_nom LIKE ? OR detail LIKE ?)")
        params += [f"%{q}%"] * 3
    return " AND ".join(cond), params


def lister(conn, *, machine_id: Optional[int] = None, utilisateur: str = "",
           action: str = "", jours: Optional[int] = 30, q: str = "",
           offset: int = 0, limite: int = 100) -> dict:
    machines = {int(r["id"]): str(r["nom"] or "") for r in
                conn.execute("SELECT id, nom FROM machines ORDER BY id").fetchall()}
    limite = max(1, min(int(limite or 100), LIMITE_MAX))
    where, params = _filtres(machines, machine_id, utilisateur.strip(), action.strip(),
                             jours, q.strip())
    total = conn.execute(f"SELECT COUNT(*) FROM audit_logs WHERE {where}", params).fetchone()[0]
    rows = conn.execute(
        f"""SELECT id, user_nom, action, objet, detail, created_at FROM audit_logs
             WHERE {where} ORDER BY id DESC LIMIT ? OFFSET ?""",
        params + [limite, max(0, int(offset or 0))],
    ).fetchall()

    # Listes des filtres : ce qui existe pour la machine et la période choisies,
    # sans le filtre lui-même (sinon la liste se réduirait à la valeur cochée).
    w_fac, p_fac = _filtres(machines, machine_id, "", "", jours, "")
    utilisateurs = [r[0] for r in conn.execute(
        f"""SELECT user_nom FROM audit_logs WHERE {w_fac} AND user_nom IS NOT NULL
             GROUP BY user_nom ORDER BY COUNT(*) DESC""", p_fac).fetchall()]
    actions = [r[0] for r in conn.execute(
        f"SELECT action FROM audit_logs WHERE {w_fac} GROUP BY action", p_fac).fetchall()]

    return {
        "total": total,
        "lignes": [mettre_en_forme(dict(r), machines) for r in rows],
        "machines": [{"id": k, "nom": v} for k, v in machines.items()],
        "utilisateurs": utilisateurs,
        "actions": sorted(({"valeur": a, "libelle": action_label(a)} for a in actions),
                          key=lambda d: d["libelle"].lower()),
    }
