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
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

STATUT_OUVERTE = "ouverte"
STATUT_CLOSE = "close"

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


def actions(conn, reunion_id: int) -> List[Dict[str, Any]]:
    if not _table_existe(conn, "reunion_actions"):
        return []
    rows = conn.execute(
        """SELECT id, texte, responsable, echeance, fait, fait_le, fait_par, created_at
             FROM reunion_actions WHERE reunion_id=?
            ORDER BY fait, echeance IS NULL, echeance, id""",
        (int(reunion_id),),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["fait"] = bool(d["fait"])
        out.append(d)
    return out


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
    return d


def liste(conn, limite: int = 100) -> List[Dict[str, Any]]:
    """Les reunions, la plus recente en tete.

    L'ordre suit la plage analysee et non la date de creation : c'est la
    journee dont on a parle qui situe une reunion, pas l'heure ou quelqu'un a
    clique.
    """
    if not _table_existe(conn, "reunions"):
        return []
    rows = conn.execute(
        """SELECT id, titre, date_debut, date_fin, machine, statut,
                  ouverte_le, ouverte_par, close_le, close_par,
                  LENGTH(TRIM(notes)) AS taille_notes
             FROM reunions
            ORDER BY date_debut DESC, id DESC
            LIMIT ?""",
        (max(1, min(int(limite), 500)),),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["ouverte"] = d.get("statut") == STATUT_OUVERTE
        d["a_des_notes"] = bool(d.pop("taille_notes", 0))
        actes = actions(conn, d["id"])
        d["nb_actions"] = len(actes)
        d["actions_restantes"] = sum(1 for a in actes if not a["fait"])
        d["participants"] = [p["nom"] for p in participants(conn, d["id"])]
        d["machines"] = machines(conn, d["id"])
        out.append(d)
    return out


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
           noms_machines: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """Ouvre une reunion sur une plage de dates.

    Si l'auteur en a deja une ouverte, on la lui rend plutot que d'en creer une
    seconde : deux reunions ouvertes en meme temps par la meme personne n'ont
    pas de sens, et la seconde ferait perdre les notes de la premiere.
    """
    if not _table_existe(conn, "reunions"):
        return None
    deja = ouverte_de(conn, auteur)
    if deja:
        return deja

    debut = _jour(date_debut, (date.today() - timedelta(days=1)).isoformat())
    fin = _jour(date_fin, debut) or debut
    if fin < debut:
        debut, fin = fin, debut

    cur = conn.execute(
        """INSERT INTO reunions
           (titre, date_debut, date_fin, machine, notes, statut, ouverte_le, ouverte_par)
           VALUES (?,?,?,?,'',?,?,?)""",
        (_txt(titre) or titre_par_defaut(), debut, fin, _txt(machine) or None,
         STATUT_OUVERTE, _now(), _txt(auteur)),
    )
    rid = cur.lastrowid
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
                noms_participants: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
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

def ajouter_action(conn, reunion_id: int, texte: str, responsable: str = "",
                   echeance: str = "") -> Optional[Dict[str, Any]]:
    """Une action, c'est un quoi, un qui et un pour quand. Le quoi suffit."""
    texte = _txt(texte)
    if not texte or not reunion(conn, reunion_id):
        return None
    cur = conn.execute(
        """INSERT INTO reunion_actions (reunion_id, texte, responsable, echeance, created_at)
           VALUES (?,?,?,?,?)""",
        (int(reunion_id), texte, _txt(responsable) or None, _jour(echeance) or None, _now()),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM reunion_actions WHERE id=?", (cur.lastrowid,)).fetchone()
    d = dict(row)
    d["fait"] = bool(d["fait"])
    return d


def modifier_action(conn, action_id: int, auteur: str, texte: Optional[str] = None,
                    responsable: Optional[str] = None, echeance: Optional[str] = None,
                    fait: Optional[bool] = None) -> Optional[Dict[str, Any]]:
    """Corrige une action, ou la coche. Un texte vide la supprime."""
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
    if fait is not None:
        champs += ["fait=?", "fait_le=?", "fait_par=?"]
        valeurs += [1 if fait else 0, _now() if fait else None,
                    _txt(auteur) if fait else None]
    if not champs:
        d = dict(row); d["fait"] = bool(d["fait"]); return d
    valeurs.append(int(action_id))
    conn.execute(f"UPDATE reunion_actions SET {', '.join(champs)} WHERE id=?", valeurs)
    conn.commit()
    maj = conn.execute("SELECT * FROM reunion_actions WHERE id=?", (int(action_id),)).fetchone()
    d = dict(maj); d["fait"] = bool(d["fait"])
    return d
