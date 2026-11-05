"""
Points de production : reunions, notes, actions.

Service pur — il prend une connexion sqlite et rien d'autre, donc il se teste
sur une base en memoire sans charger `database` ni FastAPI.

Ce qu'une reunion garde : sa plage de dates, son titre, ses notes, ses actions,
ses participants. Ce qu'elle NE garde PAS : les chiffres de production. Ils se
recalculent a la lecture depuis `app/services/rapport_dossier.py`, sur la plage
enregistree. Un compte-rendu rouvert plus tard montre donc l'atelier tel qu'il
apparait ce jour-la — les notes et les decisions, elles, sont figees.

Une seule reunion peut etre ouverte a la fois par personne : rouvrir la page
reprend celle qui traine plutot que d'en empiler une seconde. Une reunion
qu'on oublie de clore n'est pas une erreur, c'est une reunion qu'on reprend.
L'espace Reunions (`/reunions`) cree, lui, chaque reunion explicitement
(`reprendre=False`).

Espace commun (novembre 2026) : une reunion a un type (`reunion_types`,
referentiel de Parametres) et une visibilite. `peut_voir()` est le seul juge de
qui voit quoi ; toutes les lectures de l'API passent par lui, liste, detail et
suivi des actions compris. Jamais un filtre dans le JS seulement.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

STATUT_OUVERTE = "ouverte"
STATUT_CLOSE = "close"

# Statuts d'une action, dans l'ordre du suivi. `termine` est le seul final :
# la colonne `fait` le suit, pour ce qui lit encore la case.
ACTION_STATUTS = (
    {"code": "a_faire", "libelle": "À faire"},
    {"code": "en_cours", "libelle": "En cours"},
    {"code": "en_attente", "libelle": "En attente"},
    {"code": "termine", "libelle": "Terminé"},
)
ACTION_STATUTS_CODES = {s["code"] for s in ACTION_STATUTS}
ACTION_TERMINE = "termine"


def action_statuts() -> List[Dict[str, str]]:
    return [dict(s) for s in ACTION_STATUTS]

VISIBILITES = ("participants", "roles", "tous")
VISIBILITE_LIBELLES = {
    "participants": "Participants",
    "roles": "Rôles choisis",
    "tous": "Tout le monde",
}

_JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")


def _txt(v: Any) -> str:
    return ("" if v is None else str(v)).strip()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _table_existe(conn, nom: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (nom,)
    ).fetchone() is not None


def titre_par_defaut(quand: Optional[date] = None) -> str:
    """La date du jour, et rien d'autre — « 31/08/2026 ».

    Le titre sert a retrouver une reunion dans une liste : y repeter « Point de
    production » sur chaque ligne n'apprend rien, la page le dit deja. Il reste
    modifiable, pour les points qui meritent un nom.
    """
    return (quand or date.today()).strftime("%d/%m/%Y")


def _jour(valeur: Any, defaut: str = "") -> str:
    s = _txt(valeur)[:10]
    return s if len(s) == 10 else defaut


def _roles(v: Any) -> List[str]:
    """« a, b » ou ["a", "b"] -> ["a", "b"], sans doublon ni vide."""
    if isinstance(v, (list, tuple, set)):
        brut = [str(x) for x in v]
    else:
        brut = _txt(v).split(",")
    vus: List[str] = []
    for r in brut:
        r = r.strip().lower()
        if r and r not in vus:
            vus.append(r)
    return vus


# ─── Types de reunion (referentiel de Parametres) ────────────────────────────

def _type(row) -> Dict[str, Any]:
    d = dict(row)
    for k in ("actif", "chiffres_prod", "structuration_ia"):
        d[k] = bool(d.get(k))
    d["roles_defaut"] = _roles(d.get("roles_defaut"))
    return d


def types(conn, actifs_seulement: bool = False) -> List[Dict[str, Any]]:
    if not _table_existe(conn, "reunion_types"):
        return []
    sql = "SELECT * FROM reunion_types"
    if actifs_seulement:
        sql += " WHERE actif=1"
    rows = conn.execute(sql + " ORDER BY ordre, libelle").fetchall()
    return [_type(r) for r in rows]


def type_reunion(conn, type_id: Any) -> Optional[Dict[str, Any]]:
    if type_id in (None, "") or not _table_existe(conn, "reunion_types"):
        return None
    try:
        tid = int(type_id)
    except (TypeError, ValueError):
        return None
    row = conn.execute("SELECT * FROM reunion_types WHERE id=?", (tid,)).fetchone()
    return _type(row) if row else None


def type_chiffres_prod(conn) -> Optional[Dict[str, Any]]:
    """Le type que prennent les reunions lancees depuis la production : le
    premier, dans l'ordre du referentiel, qui regarde les chiffres."""
    for t in types(conn):
        if t["chiffres_prod"]:
            return t
    return None


def enregistrer_type(conn, type_id: Optional[int], donnees: Dict[str, Any]) -> Dict[str, Any]:
    """Cree (type_id None) ou modifie un type. Leve ValueError, message affichable."""
    libelle = _txt(donnees.get("libelle"))
    if type_id is None and not libelle:
        raise ValueError("Libellé obligatoire.")
    actuel = type_reunion(conn, type_id) if type_id is not None else None
    if type_id is not None and not actuel:
        raise ValueError("Type introuvable.")
    vis = _txt(donnees.get("visibilite_defaut")) or (actuel or {}).get("visibilite_defaut") or "participants"
    if vis not in VISIBILITES:
        raise ValueError("Visibilité inconnue.")
    roles = _roles(donnees["roles_defaut"]) if "roles_defaut" in donnees else (actuel or {}).get("roles_defaut", [])
    if vis == "roles" and not roles:
        raise ValueError("Choisir au moins un rôle pour une visibilité par rôles.")

    def _b(cle: str, defaut: bool) -> int:
        if cle in donnees:
            return 1 if donnees.get(cle) in (True, 1, "1", "true", "on") else 0
        return 1 if (actuel or {}).get(cle, defaut) else 0

    valeurs = {
        "libelle": libelle or actuel["libelle"],
        "ordre": int(donnees.get("ordre") if donnees.get("ordre") not in (None, "") else (actuel or {}).get("ordre", 0) or 0),
        "actif": _b("actif", True),
        "chiffres_prod": _b("chiffres_prod", False),
        "visibilite_defaut": vis,
        "roles_defaut": ",".join(roles),
        "structuration_ia": _b("structuration_ia", True),
    }
    doublon = conn.execute(
        "SELECT id FROM reunion_types WHERE LOWER(libelle)=LOWER(?) AND id<>?",
        (valeurs["libelle"], int(type_id or 0)),
    ).fetchone()
    if doublon:
        raise ValueError(f"Un type « {valeurs['libelle']} » existe déjà.")
    if type_id is None:
        cur = conn.execute(
            """INSERT INTO reunion_types (libelle, ordre, actif, chiffres_prod, visibilite_defaut,
                   roles_defaut, structuration_ia, created_at)
               VALUES (:libelle, :ordre, :actif, :chiffres_prod, :visibilite_defaut,
                   :roles_defaut, :structuration_ia, :maintenant)""",
            dict(valeurs, maintenant=_now()),
        )
        type_id = cur.lastrowid
    else:
        conn.execute(
            """UPDATE reunion_types SET libelle=:libelle, ordre=:ordre, actif=:actif,
                   chiffres_prod=:chiffres_prod, visibilite_defaut=:visibilite_defaut,
                   roles_defaut=:roles_defaut, structuration_ia=:structuration_ia,
                   updated_at=:maintenant WHERE id=:id""",
            dict(valeurs, maintenant=_now(), id=int(type_id)),
        )
    conn.commit()
    return type_reunion(conn, type_id)


def supprimer_type(conn, type_id: int) -> str:
    """Supprime un type inutilise, desactive un type qui porte des reunions.

    Rend « supprime » ou « desactive ». Une reunion ne perd jamais son type :
    le retirer la rendrait invisible a ceux qui la voyaient par lui.
    """
    if not type_reunion(conn, type_id):
        raise ValueError("Type introuvable.")
    utilise = conn.execute(
        "SELECT COUNT(*) FROM reunions WHERE type_id=?", (int(type_id),)
    ).fetchone()[0] if _table_existe(conn, "reunions") else 0
    if utilise:
        conn.execute("UPDATE reunion_types SET actif=0, updated_at=? WHERE id=?", (_now(), int(type_id)))
        conn.commit()
        return "desactive"
    conn.execute("DELETE FROM reunion_types WHERE id=?", (int(type_id),))
    conn.commit()
    return "supprime"


# ─── Visibilite ──────────────────────────────────────────────────────────────

def lecteur(user: Dict[str, Any], role: str = "", superadmin: bool = False) -> Dict[str, Any]:
    """Ce que `peut_voir` sait de la personne qui lit : id, nom, role."""
    return {
        "id": user.get("id"),
        "nom": _txt(user.get("nom") or user.get("email")),
        "role": _txt(role or user.get("role")).lower(),
        "superadmin": bool(superadmin),
    }


def peut_voir(r: Dict[str, Any], qui: Optional[Dict[str, Any]]) -> bool:
    """Le seul juge de la visibilite d'une reunion.

    `r` porte `visibilite`, `roles_visibles`, `ouverte_par(_id)` et
    `participants` (noms ou dicts). Le createur et les participants voient
    toujours ; ensuite `tous` ou le role. `qui=None` = appel interne.
    """
    if qui is None or qui.get("superadmin"):
        return True
    nom = _txt(qui.get("nom")).lower()
    if qui.get("id") is not None and r.get("ouverte_par_id") not in (None, "") \
            and str(r.get("ouverte_par_id")) == str(qui.get("id")):
        return True
    if nom and _txt(r.get("ouverte_par")).lower() == nom:
        return True
    for p in r.get("participants") or []:
        if isinstance(p, dict):
            if qui.get("id") is not None and p.get("user_id") not in (None, "") \
                    and str(p.get("user_id")) == str(qui.get("id")):
                return True
            p = p.get("nom")
        if nom and _txt(p).lower() == nom:
            return True
    vis = _txt(r.get("visibilite")) or "tous"
    if vis == "tous":
        return True
    if vis == "roles":
        return _txt(qui.get("role")).lower() in _roles(r.get("roles_visibles"))
    return False


def _avec_type(conn, d: Dict[str, Any]) -> Dict[str, Any]:
    t = type_reunion(conn, d.get("type_id"))
    d["type"] = {"id": t["id"], "libelle": t["libelle"], "chiffres_prod": t["chiffres_prod"],
                 "structuration_ia": t["structuration_ia"]} if t else None
    d["roles_visibles"] = _roles(d.get("roles_visibles"))
    if not d.get("visibilite"):
        d["visibilite"] = "tous"
    return d


# ─── Lecture ─────────────────────────────────────────────────────────────────

def participants(conn, reunion_id: int) -> List[Dict[str, Any]]:
    if not _table_existe(conn, "reunion_participants"):
        return []
    rows = conn.execute(
        "SELECT nom, user_id FROM reunion_participants WHERE reunion_id=? ORDER BY nom",
        (int(reunion_id),),
    ).fetchall()
    return [dict(r) for r in rows]


def machines(conn, reunion_id: int) -> List[str]:
    """Les machines regardees par cette reunion. Vide = tout l'atelier.

    L'absence de ligne est le seul sens que « toutes les machines » ait jamais
    eu : on ne stocke pas la liste complete, qui changerait a chaque machine
    ajoutee dans les Parametres.
    """
    if not _table_existe(conn, "reunion_machines"):
        return []
    rows = conn.execute(
        "SELECT machine FROM reunion_machines WHERE reunion_id=? ORDER BY machine",
        (int(reunion_id),),
    ).fetchall()
    return [r["machine"] for r in rows]


def _poser_machines(conn, reunion_id: int, noms: Optional[List[str]]) -> None:
    if noms is None or not _table_existe(conn, "reunion_machines"):
        return
    conn.execute("DELETE FROM reunion_machines WHERE reunion_id=?", (int(reunion_id),))
    for nom in noms:
        if _txt(nom):
            conn.execute(
                "INSERT OR IGNORE INTO reunion_machines (reunion_id, machine) VALUES (?,?)",
                (int(reunion_id), _txt(nom)),
            )


def _action(row) -> Dict[str, Any]:
    d = dict(row)
    d["fait"] = bool(d.get("fait"))
    # Base pas encore migree : le statut se deduit de la case.
    if d.get("statut") not in ACTION_STATUTS_CODES:
        d["statut"] = ACTION_TERMINE if d["fait"] else "a_faire"
    return d


def actions(conn, reunion_id: int) -> List[Dict[str, Any]]:
    if not _table_existe(conn, "reunion_actions"):
        return []
    rows = conn.execute(
        """SELECT * FROM reunion_actions WHERE reunion_id=?
            ORDER BY fait, echeance IS NULL, echeance, id""",
        (int(reunion_id),),
    ).fetchall()
    return [_action(r) for r in rows]


def toutes_actions(conn, qui: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Le suivi : toutes les actions, toutes reunions confondues.

    Chaque action porte la reunion qui l'a decidee — titre et date — pour
    qu'on puisse y revenir depuis le tableau de suivi. Une action d'une reunion
    que `qui` ne voit pas n'y figure pas : l'action d'une reunion de direction
    ne doit pas apparaitre sur le tableau de l'atelier.
    """
    if not _table_existe(conn, "reunion_actions") or not _table_existe(conn, "reunions"):
        return []
    # LEFT JOIN : une action creee depuis le suivi n'a pas de reunion.
    rows = conn.execute(
        """SELECT a.*, r.titre AS reunion_titre, r.date_debut AS reunion_date
             FROM reunion_actions a
             LEFT JOIN reunions r ON r.id = a.reunion_id
            ORDER BY a.echeance IS NULL, a.echeance, a.id"""
    ).fetchall()
    if qui is None or qui.get("superadmin"):
        return [_action(r) for r in rows]
    visibles: Dict[int, bool] = {}
    out = []
    for row in rows:
        rid = row["reunion_id"]
        if rid is not None and rid not in visibles:
            visibles[rid] = reunion_visible(conn, rid, qui)
        if rid is None or visibles[rid]:
            out.append(_action(row))
    return out


def reunion_visible(conn, reunion_id: int, qui: Optional[Dict[str, Any]]) -> bool:
    row = conn.execute("SELECT * FROM reunions WHERE id=?", (int(reunion_id),)).fetchone()
    if not row:
        return False
    d = dict(row)
    d["participants"] = participants(conn, reunion_id)
    return peut_voir(d, qui)


def reunion(conn, reunion_id: int) -> Optional[Dict[str, Any]]:
    if not _table_existe(conn, "reunions"):
        return None
    row = conn.execute("SELECT * FROM reunions WHERE id=?", (int(reunion_id),)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["ouverte"] = d.get("statut") == STATUT_OUVERTE
    d["actions"] = actions(conn, reunion_id)
    d["participants"] = participants(conn, reunion_id)
    d["machines"] = machines(conn, reunion_id)
    d["actions_restantes"] = sum(1 for a in d["actions"] if not a["fait"])
    return _avec_type(conn, d)


def liste(conn, limite: int = 100, qui: Optional[Dict[str, Any]] = None,
          type_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Les reunions, la plus recente en tete.

    L'ordre suit la plage analysee et non la date de creation : c'est la
    journee dont on a parle qui situe une reunion, pas l'heure ou quelqu'un a
    clique.

    `qui` filtre sur la visibilite (None = tout, appel interne) ; `type_id`
    sur le type. La limite porte sur ce qui reste APRES le filtre.
    """
    if not _table_existe(conn, "reunions"):
        return []
    limite = max(1, min(int(limite), 500))
    cols = {r[1] for r in conn.execute("PRAGMA table_info(reunions)").fetchall()}
    extra = ", ".join(c for c in ("type_id", "visibilite", "roles_visibles", "ouverte_par_id")
                      if c in cols)
    filtre, params = "", []
    if type_id is not None and "type_id" in cols:
        filtre, params = "WHERE type_id=?", [int(type_id)]
    rows = conn.execute(
        f"""SELECT id, titre, date_debut, date_fin, machine, statut,
                  ouverte_le, ouverte_par, close_le, close_par,
                  LENGTH(TRIM(notes)) AS taille_notes
                  {', ' + extra if extra else ''}
             FROM reunions {filtre}
            ORDER BY date_debut DESC, id DESC""",
        params,
    ).fetchall()
    out = []
    for r in rows:
        if len(out) >= limite:
            break
        d = dict(r)
        parts = participants(conn, d["id"])
        if qui is not None and not peut_voir(dict(d, participants=parts), qui):
            continue
        d["ouverte"] = d.get("statut") == STATUT_OUVERTE
        d["a_des_notes"] = bool(d.pop("taille_notes", 0))
        actes = actions(conn, d["id"])
        d["nb_actions"] = len(actes)
        d["actions_restantes"] = sum(1 for a in actes if not a["fait"])
        # La liste porte les actions elles-memes, pas seulement leur nombre :
        # l'historique sert a retrouver ce qui a ete decide, et un compteur ne
        # le dit pas. Le detail reste leger — quelques lignes de texte.
        d["actions"] = actes
        d["participants"] = [p["nom"] for p in parts]
        d["machines"] = machines(conn, d["id"])
        out.append(_avec_type(conn, d))
    return out


def precedente(conn, reunion_id: int) -> Optional[Dict[str, Any]]:
    """Le point de production qui precede celui-ci, avec ses notes.

    « La veille » n'est pas J-1 dans un atelier : le lundi, le point precedent
    est celui du vendredi, et une semaine sans point ne doit pas renvoyer une
    boite vide. On prend donc le plus recent qui passe AVANT, sur le meme ordre
    que la liste — la plage analysee d'abord, l'id pour departager deux points
    tenus sur la meme journee.
    """
    if not _table_existe(conn, "reunions"):
        return None
    ici = conn.execute(
        "SELECT id, date_debut FROM reunions WHERE id=?", (int(reunion_id),)
    ).fetchone()
    if not ici:
        return None
    row = conn.execute(
        """SELECT id, titre, date_debut, date_fin, notes, statut, ouverte_le, ouverte_par
             FROM reunions
            WHERE (COALESCE(date_debut,'') < ?)
               OR (COALESCE(date_debut,'') = ? AND id < ?)
            ORDER BY date_debut DESC, id DESC LIMIT 1""",
        (_txt(ici["date_debut"]), _txt(ici["date_debut"]), int(reunion_id)),
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["notes"] = _txt(d.get("notes"))
    d["ouverte"] = d.get("statut") == STATUT_OUVERTE
    return d


def ouverte_de(conn, auteur: str) -> Optional[Dict[str, Any]]:
    """La reunion encore ouverte de cette personne, s'il y en a une."""
    if not _table_existe(conn, "reunions"):
        return None
    row = conn.execute(
        """SELECT id FROM reunions
            WHERE statut=? AND TRIM(LOWER(ouverte_par))=TRIM(LOWER(?))
            ORDER BY id DESC LIMIT 1""",
        (STATUT_OUVERTE, _txt(auteur)),
    ).fetchone()
    return reunion(conn, row["id"]) if row else None


# ─── Ecriture ────────────────────────────────────────────────────────────────

def lancer(conn, auteur: str, date_debut: str, date_fin: str = "",
           titre: str = "", machine: str = "",
           noms_participants: Optional[List[str]] = None,
           noms_machines: Optional[List[str]] = None,
           type_id: Optional[int] = None, visibilite: Optional[str] = None,
           roles_visibles: Optional[List[str]] = None,
           auteur_id: Optional[int] = None, reprendre: bool = True,
           notes: str = "", decisions: str = "",
           statut: str = STATUT_OUVERTE) -> Optional[Dict[str, Any]]:
    """Ouvre une reunion sur une plage de dates.

    Si l'auteur en a deja une ouverte, on la lui rend plutot que d'en creer une
    seconde : deux reunions ouvertes en meme temps par la meme personne n'ont
    pas de sens, et la seconde ferait perdre les notes de la premiere. Avec
    `reprendre=False` (espace Reunions, brief d'une ecoute), la reunion est
    toujours creee.

    Sans type, la reunion prend le type « chiffres de prod » du referentiel ;
    sans visibilite, celle de son type.
    """
    if not _table_existe(conn, "reunions"):
        return None
    if reprendre:
        deja = ouverte_de(conn, auteur)
        if deja:
            return deja
    t = type_reunion(conn, type_id) if type_id not in (None, "") else type_chiffres_prod(conn)
    vis = _txt(visibilite) if _txt(visibilite) in VISIBILITES else (t["visibilite_defaut"] if t else "tous")
    roles = _roles(roles_visibles) if roles_visibles is not None else (t["roles_defaut"] if t else [])

    debut = _jour(date_debut, (date.today() - timedelta(days=1)).isoformat())
    fin = _jour(date_fin, debut) or debut
    if fin < debut:
        debut, fin = fin, debut

    cur = conn.execute(
        """INSERT INTO reunions
           (titre, date_debut, date_fin, machine, notes, statut, ouverte_le, ouverte_par)
           VALUES (?,?,?,?,?,?,?,?)""",
        (_txt(titre) or titre_par_defaut(), debut, fin, _txt(machine) or None,
         str(notes or ""), statut if statut in (STATUT_OUVERTE, STATUT_CLOSE) else STATUT_OUVERTE,
         _now(), _txt(auteur)),
    )
    rid = cur.lastrowid
    cols = {r[1] for r in conn.execute("PRAGMA table_info(reunions)").fetchall()}
    if "type_id" in cols:
        conn.execute(
            """UPDATE reunions SET type_id=?, visibilite=?, roles_visibles=?, decisions=?,
                   ouverte_par_id=? WHERE id=?""",
            (t["id"] if t else None, vis, ",".join(roles), str(decisions or ""),
             auteur_id, rid),
        )
    if statut == STATUT_CLOSE:
        conn.execute("UPDATE reunions SET close_le=?, close_par=? WHERE id=?",
                     (_now(), _txt(auteur), rid))
    # `machine` reste renseignee pour les lecteurs anciens ; le perimetre vit
    # desormais dans reunion_machines, qui en accepte plusieurs.
    _poser_machines(conn, rid, noms_machines
                    if noms_machines is not None
                    else ([_txt(machine)] if _txt(machine) else []))
    for nom in (noms_participants or []):
        if _txt(nom):
            conn.execute(
                "INSERT OR IGNORE INTO reunion_participants (reunion_id, nom) VALUES (?,?)",
                (rid, _txt(nom)),
            )
    conn.commit()
    return reunion(conn, rid)


def enregistrer(conn, reunion_id: int, auteur: str, titre: Optional[str] = None,
                notes: Optional[str] = None, date_debut: Optional[str] = None,
                date_fin: Optional[str] = None, machine: Optional[str] = None,
                noms_machines: Optional[List[str]] = None,
                noms_participants: Optional[List[str]] = None,
                decisions: Optional[str] = None, type_id: Optional[int] = None,
                visibilite: Optional[str] = None,
                roles_visibles: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """Met a jour ce qui est fourni, et rien d'autre.

    Une reunion close reste modifiable : on corrige un compte-rendu, on ajoute
    ce qu'on avait oublie. La clore ne le verrouille pas, elle dit seulement
    que le point est passe.
    """
    actuelle = reunion(conn, reunion_id)
    if not actuelle:
        return None
    champs, valeurs = [], []
    if titre is not None and _txt(titre):
        champs.append("titre=?"); valeurs.append(_txt(titre))
    if notes is not None:
        champs.append("notes=?"); valeurs.append(str(notes))
    if date_debut is not None and _jour(date_debut):
        champs.append("date_debut=?"); valeurs.append(_jour(date_debut))
    if date_fin is not None and _jour(date_fin):
        champs.append("date_fin=?"); valeurs.append(_jour(date_fin))
    if machine is not None:
        champs.append("machine=?"); valeurs.append(_txt(machine) or None)
    if decisions is not None:
        champs.append("decisions=?"); valeurs.append(str(decisions))
    if type_id is not None and type_reunion(conn, type_id):
        champs.append("type_id=?"); valeurs.append(int(type_id))
    if visibilite is not None and _txt(visibilite) in VISIBILITES:
        champs.append("visibilite=?"); valeurs.append(_txt(visibilite))
    if roles_visibles is not None:
        champs.append("roles_visibles=?"); valeurs.append(",".join(_roles(roles_visibles)))
    if noms_machines is None and machine is not None:
        # Un appelant ancien qui ne connait qu'une machine reste coherent.
        noms_machines = [_txt(machine)] if _txt(machine) else []
    if champs:
        champs += ["updated_at=?", "updated_par=?"]
        valeurs += [_now(), _txt(auteur), int(reunion_id)]
        conn.execute(f"UPDATE reunions SET {', '.join(champs)} WHERE id=?", valeurs)

    _poser_machines(conn, reunion_id, noms_machines)

    if noms_participants is not None:
        conn.execute("DELETE FROM reunion_participants WHERE reunion_id=?", (int(reunion_id),))
        for nom in noms_participants:
            if _txt(nom):
                conn.execute(
                    "INSERT OR IGNORE INTO reunion_participants (reunion_id, nom) VALUES (?,?)",
                    (int(reunion_id), _txt(nom)),
                )
    conn.commit()
    maj = reunion(conn, reunion_id)
    # Les bornes ont pu etre inversees par la saisie : on remet dans l'ordre.
    if maj and maj["date_fin"] < maj["date_debut"]:
        conn.execute("UPDATE reunions SET date_debut=?, date_fin=? WHERE id=?",
                     (maj["date_fin"], maj["date_debut"], int(reunion_id)))
        conn.commit()
        maj = reunion(conn, reunion_id)
    return maj


def clore(conn, reunion_id: int, auteur: str, rouvrir: bool = False) -> Optional[Dict[str, Any]]:
    """Clot le point, ou le rouvre. Rien n'est verrouille dans les deux cas."""
    if not reunion(conn, reunion_id):
        return None
    if rouvrir:
        conn.execute(
            "UPDATE reunions SET statut=?, close_le=NULL, close_par=NULL WHERE id=?",
            (STATUT_OUVERTE, int(reunion_id)),
        )
    else:
        conn.execute(
            "UPDATE reunions SET statut=?, close_le=?, close_par=? WHERE id=?",
            (STATUT_CLOSE, _now(), _txt(auteur), int(reunion_id)),
        )
    conn.commit()
    return reunion(conn, reunion_id)


def supprimer(conn, reunion_id: int) -> bool:
    if not reunion(conn, reunion_id):
        return False
    conn.execute("DELETE FROM reunion_actions WHERE reunion_id=?", (int(reunion_id),))
    conn.execute("DELETE FROM reunion_participants WHERE reunion_id=?", (int(reunion_id),))
    if _table_existe(conn, "reunion_machines"):
        conn.execute("DELETE FROM reunion_machines WHERE reunion_id=?", (int(reunion_id),))
    conn.execute("DELETE FROM reunions WHERE id=?", (int(reunion_id),))
    conn.commit()
    return True


# ─── Actions ─────────────────────────────────────────────────────────────────

def ajouter_action(conn, reunion_id: Optional[int], texte: str, responsable: str = "",
                   echeance: str = "") -> Optional[Dict[str, Any]]:
    """Une action, c'est un quoi, un qui et un pour quand. Le quoi suffit.

    Sans `reunion_id`, l'action est creee directement depuis le suivi.
    """
    texte = _txt(texte)
    if not texte or (reunion_id is not None and not reunion(conn, reunion_id)):
        return None
    cur = conn.execute(
        """INSERT INTO reunion_actions (reunion_id, texte, responsable, echeance, created_at)
           VALUES (?,?,?,?,?)""",
        (None if reunion_id is None else int(reunion_id), texte, _txt(responsable) or None, _jour(echeance) or None, _now()),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM reunion_actions WHERE id=?", (cur.lastrowid,)).fetchone()
    return _action(row)


def modifier_action(conn, action_id: int, auteur: str, texte: Optional[str] = None,
                    responsable: Optional[str] = None, echeance: Optional[str] = None,
                    fait: Optional[bool] = None,
                    statut: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Corrige une action, change son statut, ou la coche. Un texte vide la supprime.

    Le statut et la case vont ensemble : cocher vaut `termine`, decocher
    `a_faire` ; passer en `termine` coche, en sortir decoche.
    """
    row = conn.execute("SELECT * FROM reunion_actions WHERE id=?", (int(action_id),)).fetchone()
    if not row:
        return None
    if texte is not None and not _txt(texte):
        conn.execute("DELETE FROM reunion_actions WHERE id=?", (int(action_id),))
        conn.commit()
        return None
    champs, valeurs = [], []
    if texte is not None:
        champs.append("texte=?"); valeurs.append(_txt(texte))
    if responsable is not None:
        champs.append("responsable=?"); valeurs.append(_txt(responsable) or None)
    if echeance is not None:
        champs.append("echeance=?"); valeurs.append(_jour(echeance) or None)
    if statut is not None and _txt(statut) not in ACTION_STATUTS_CODES:
        statut = None
    if statut is not None:
        statut = _txt(statut)
        fait = statut == ACTION_TERMINE
    elif fait is not None:
        statut = ACTION_TERMINE if fait else "a_faire"
    if statut is not None and "statut" in row.keys():
        champs.append("statut=?"); valeurs.append(statut)
    if fait is not None:
        champs += ["fait=?", "fait_le=?", "fait_par=?"]
        valeurs += [1 if fait else 0, _now() if fait else None,
                    _txt(auteur) if fait else None]
    if not champs:
        return _action(row)
    valeurs.append(int(action_id))
    conn.execute(f"UPDATE reunion_actions SET {', '.join(champs)} WHERE id=?", valeurs)
    conn.commit()
    maj = conn.execute("SELECT * FROM reunion_actions WHERE id=?", (int(action_id),)).fetchone()
    return _action(maj)
