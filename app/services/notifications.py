"""MySifa — Notifications par service (pastilles rouges sur les applis du portail).

Principe
--------
Une notification n'est pas un événement stocké : c'est un **détecteur** qui
compte, à la lecture, ce qui attend quelqu'un (réceptions à intégrer, départs
à valider…). Tant que le compte est positif, la notification existe ; elle
disparaît d'elle-même quand le travail est fait. Aucun risque de pastille
« fantôme » restée allumée sur une tâche déjà traitée.

Partage des responsabilités
---------------------------
- Le CODE (ce module) définit ce qui se détecte : une fonction de comptage,
  une app, un lien. Ajouter un type de notification = ajouter un détecteur.
- La BASE (`notif_regles`) définit qui est prévenu : actif ou non, rôles
  destinataires, push ou non. Se règle dans Paramètres › Notifications, sans
  toucher au code.

Chaque détecteur renvoie `(nombre, signature)`. La signature change quand un
nouvel élément apparaît (typiquement le plus grand identifiant) : c'est elle
qui rallume la pastille « nouveau » pour un utilisateur qui avait déjà vu la
notification.

Les comptages sont communs à tous les utilisateurs : ils sont mis en cache
`CACHE_TTL` secondes pour que le polling de toutes les pages ouvertes ne
refasse pas la même requête.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Optional
from zoneinfo import ZoneInfo

from config import ROLE_LABELS, ROLE_SUPERADMIN

log = logging.getLogger("mysifa.notifications")

CACHE_TTL = 60  # secondes
_PARIS = ZoneInfo("Europe/Paris")
DESTOCKAGE_JOURS = 15  # fenêtre de la notification « Dossiers à déstocker »


@dataclass(frozen=True)
class Detecteur:
    code: str                 # clé stable, jamais renommée (référencée en base)
    app: str                  # clé d'application (contrôle d'accès user_has_app_access)
    app_label: str            # libellé (infobulle de la tuile, push)
    titre: str                # ex. « Réceptions à intégrer »
    description: str          # affichée dans Paramètres
    lien: str                 # où cliquer pour traiter
    compter: Callable         # conn -> (int, str | None)
    roles_suggeres: tuple = field(default_factory=tuple)

    def libelle(self, n: int) -> str:
        return f"{self.titre} : {n}" if n else self.titre


# ─── Détecteurs ────────────────────────────────────────────────────────────

def _tables(conn) -> set:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _compter_receptions_rvgi(conn):
    """Réceptions saisies dans RVGI et pas encore entrées dans MyStock."""
    from app.services import erp_mirror
    from app.services import reception_rvgi as rr

    depuis = rr.date_de_mise_en_service(conn)
    if not depuis or not erp_mirror.miroir_present():
        return 0, None
    types = ",".join(str(t) for t in sorted(rr.PERIMETRE))
    with erp_mirror.get_erp_db() as erp:
        ids = [int(r["lif_id"]) for r in erp.execute(rr._SQL_LIGNES % types, (depuis,)).fetchall()]
    faites = rr._deja_integrees(conn)
    restantes = [i for i in ids if i not in faites]
    return len(restantes), (str(max(restantes)) if restantes else None)


def _compter_seuil_alerte(conn):
    """Matières actives dont le stock est passé sous le seuil d'alerte."""
    if "matieres_premieres" not in _tables(conn):
        return 0, None
    cols = {r[1] for r in conn.execute("PRAGMA table_info(matieres_premieres)")}
    if "seuil_alerte" not in cols:
        return 0, None
    ids = [int(r[0]) for r in conn.execute(
        """SELECT mp.id
           FROM matieres_premieres mp
           LEFT JOIN mp_stock s ON s.matiere_id = mp.id
           WHERE mp.actif = 1 AND mp.seuil_alerte > 0
             AND COALESCE(s.quantite, 0) <= mp.seuil_alerte
           ORDER BY mp.id"""
    ).fetchall()]
    if not ids:
        return 0, None
    # Empreinte de la liste : une matière qui passe sous le seuil rallume la
    # pastille, même si son id est plus petit que les autres.
    emp = hashlib.sha1(",".join(map(str, ids)).encode()).hexdigest()[:16]
    return len(ids), emp


def _compter_a_destocker(conn):
    """Dossiers terminés sur les `DESTOCKAGE_JOURS` derniers jours et pas encore
    sortis du stock. Même règle que MyStock › Déstockage › à traiter (fin
    planifiée, sinon dernière mise à jour), réserves exclues : un dossier
    sorti avec réserve est déjà déstocké, il attend une relecture."""
    if "planning_entries" not in _tables(conn):
        return 0, None
    cols = {r[1] for r in conn.execute("PRAGMA table_info(planning_entries)")}
    if "destockage" not in cols:
        return 0, None
    depuis = (datetime.now(_PARIS) - timedelta(days=DESTOCKAGE_JOURS)).date().isoformat()
    ids = [int(r[0]) for r in conn.execute(
        """SELECT id FROM planning_entries
           WHERE statut = 'termine'
             AND COALESCE(destockage, 'todo') = 'todo'
             AND COALESCE(planned_end, updated_at, '') >= ?
           ORDER BY id""",
        (depuis,),
    ).fetchall()]
    if not ids:
        return 0, None
    # Empreinte plutôt que max(id) : un dossier ancien qui se termine
    # aujourd'hui doit rallumer la pastille.
    emp = hashlib.sha1(",".join(map(str, ids)).encode()).hexdigest()[:16]
    return len(ids), emp


def _compter_departs_a_valider(conn):
    """Départs dont l'enlèvement est aujourd'hui ou passé, encore en attente."""
    if "expe_departs" not in _tables(conn):
        return 0, None
    today = datetime.now(_PARIS).date().isoformat()
    r = conn.execute(
        """SELECT COUNT(*) AS n, MAX(id) AS m FROM expe_departs
           WHERE statut = 'en_attente' AND substr(date_enlevement, 1, 10) <= ?""",
        (today,),
    ).fetchone()
    n = int(r["n"] or 0)
    return n, (f"{today}:{r['m']}" if n else None)


DETECTEURS: dict[str, Detecteur] = {d.code: d for d in (
    Detecteur(
        code="stock.receptions_rvgi",
        app="stock", app_label="MyStock",
        titre="Réceptions à intégrer",
        description="Réceptions matières saisies dans l'ERP et pas encore entrées dans le stock.",
        lien="/stock?tab=reception&sous=rvgi",
        compter=_compter_receptions_rvgi,
        roles_suggeres=("administration_technique",),
    ),
    Detecteur(
        code="stock.seuil_alerte",
        app="stock", app_label="MyStock",
        titre="Matières sous le seuil d'alerte",
        description="Matières actives dont la quantité en stock est inférieure ou égale au seuil d'alerte.",
        lien="/stock?tab=matieres",
        compter=_compter_seuil_alerte,
        roles_suggeres=("administration_technique",),
    ),
    Detecteur(
        code="stock.a_destocker",
        app="stock", app_label="MyStock",
        titre="Dossiers à déstocker",
        description=f"Dossiers terminés depuis moins de {DESTOCKAGE_JOURS} jours et pas encore sortis du stock.",
        lien="/stock?tab=destockage",
        compter=_compter_a_destocker,
        roles_suggeres=("administration_technique",),
    ),
    Detecteur(
        code="expe.departs_a_valider",
        app="expe", app_label="MyExpé",
        titre="Départs à valider",
        description="Départs dont la date d'enlèvement est aujourd'hui ou passée, toujours en attente de validation.",
        lien="/expe#suivi_departs",
        compter=_compter_departs_a_valider,
        roles_suggeres=("expedition",),
    ),
)}


# ─── Cache des comptages ───────────────────────────────────────────────────

_cache: dict[str, tuple[float, int, Optional[str]]] = {}
_cache_lock = threading.Lock()


def compter(conn, code: str, *, frais: bool = False) -> tuple[int, Optional[str]]:
    det = DETECTEURS[code]
    now = time.monotonic()
    if not frais:
        with _cache_lock:
            hit = _cache.get(code)
        if hit and now - hit[0] < CACHE_TTL:
            return hit[1], hit[2]
    try:
        n, sig = det.compter(conn)
    except Exception as exc:  # un détecteur cassé ne doit pas casser les pastilles
        log.warning("détecteur %s en échec : %s", code, exc)
        n, sig = 0, None
    with _cache_lock:
        _cache[code] = (now, int(n or 0), sig)
    return int(n or 0), sig


def invalider_cache(code: Optional[str] = None) -> None:
    with _cache_lock:
        if code:
            _cache.pop(code, None)
        else:
            _cache.clear()


# ─── Règles (base) ─────────────────────────────────────────────────────────

def _roles(raw) -> list[str]:
    try:
        v = json.loads(raw or "[]")
        return [str(x) for x in v if isinstance(x, str)]
    except Exception:
        return []


def regles(conn) -> dict[str, dict]:
    """Règles en base, complétées pour les détecteurs sans ligne (inactifs)."""
    out = {}
    try:
        for r in conn.execute("SELECT code, actif, roles, push, updated_at, updated_by FROM notif_regles"):
            out[r["code"]] = {
                "actif": bool(r["actif"]), "roles": _roles(r["roles"]),
                "push": bool(r["push"]), "updated_at": r["updated_at"],
                "updated_by": r["updated_by"],
            }
    except Exception:
        pass
    for code in DETECTEURS:
        out.setdefault(code, {"actif": False, "roles": [], "push": False,
                              "updated_at": None, "updated_by": None})
    return out


def enregistrer_regle(conn, code: str, *, actif: bool, roles: list[str], push: bool, auteur: str) -> dict:
    if code not in DETECTEURS:
        raise KeyError(code)
    connus = set(ROLE_LABELS)
    roles = sorted({r for r in roles if r in connus})
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """INSERT INTO notif_regles (code, actif, roles, push, updated_at, updated_by)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(code) DO UPDATE SET actif=excluded.actif, roles=excluded.roles,
               push=excluded.push, updated_at=excluded.updated_at, updated_by=excluded.updated_by""",
        (code, 1 if actif else 0, json.dumps(roles), 1 if push else 0, now, auteur),
    )
    return {"actif": bool(actif), "roles": roles, "push": bool(push),
            "updated_at": now, "updated_by": auteur}


def codes_pour(user: dict, regles_: dict, *, a_acces: Callable[[dict, str], bool], role: str) -> list[str]:
    """Détecteurs qui concernent cet utilisateur : règle active, rôle listé,
    accès à l'application. Le super admin ne reçoit que ce qui lui est
    explicitement destiné (il se sert de l'impersonation pour vérifier)."""
    codes = []
    for code, det in DETECTEURS.items():
        rg = regles_.get(code) or {}
        if not rg.get("actif") or role not in (rg.get("roles") or []):
            continue
        if role != ROLE_SUPERADMIN and not a_acces(user, det.app):
            continue
        codes.append(code)
    return codes


def vues(conn, user_id: int) -> dict[str, Optional[str]]:
    try:
        return {r["code"]: r["signature"] for r in conn.execute(
            "SELECT code, signature FROM notif_vues WHERE user_id=?", (int(user_id),))}
    except Exception:
        return {}


def marquer_vu(conn, user_id: int, signatures: dict[str, Optional[str]]) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    conn.executemany(
        """INSERT INTO notif_vues (user_id, code, signature, vu_at) VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id, code) DO UPDATE SET signature=excluded.signature, vu_at=excluded.vu_at""",
        [(int(user_id), c, s, now) for c, s in signatures.items() if c in DETECTEURS],
    )


def pour_utilisateur(conn, user: dict, *, a_acces, role: str) -> dict:
    rg = regles(conn)
    deja_vues = vues(conn, user["id"])
    items = []
    codes = codes_pour(user, rg, a_acces=a_acces, role=role)
    for code in codes:
        n, sig = compter(conn, code)
        if n <= 0:
            continue
        det = DETECTEURS[code]
        items.append({
            "code": code, "app": det.app, "app_label": det.app_label,
            "titre": det.titre, "libelle": det.libelle(n), "n": n,
            "lien": det.lien, "signature": sig,
            "nouveau": deja_vues.get(code) != sig,
        })
    return {
        "concerne": bool(codes),
        "items": items,
        "nouveaux": sum(1 for i in items if i["nouveau"]),
        "total": sum(i["n"] for i in items),
    }


# ─── Push (boucle de fond, prod uniquement) ────────────────────────────────

def tour_de_push(get_db, send_push, a_acces) -> int:
    """Un passage : pour chaque règle active avec push, si la signature a
    changé et que le compte est positif, prévient chaque destinataire.
    Retourne le nombre de pushs envoyés."""
    envoyes = 0
    with get_db() as conn:
        rg = regles(conn)
        cibles = {c: r for c, r in rg.items() if r["actif"] and r["push"] and r["roles"]}
        if not cibles:
            return 0
        try:
            etat = {r["code"]: r["signature"] for r in conn.execute("SELECT code, signature FROM notif_push_etat")}
        except Exception:
            return 0
        a_faire, a_noter = [], []
        for code, r in cibles.items():
            n, sig = compter(conn, code, frais=True)
            if n <= 0 or not sig or etat.get(code) == sig:
                continue
            # Premier passage pour ce détecteur (boot, push tout juste activé) :
            # on note l'existant sans le pousser — le push annonce du nouveau,
            # pas un stock de travail déjà visible sur le portail.
            (a_faire if code in etat else a_noter).append((code, r, n, sig))
        if not a_faire and not a_noter:
            return 0
        users = [dict(u) for u in conn.execute(
            "SELECT id, email, nom, role, access_overrides FROM users WHERE actif=1")]
        now = datetime.now().isoformat(timespec="seconds")
        for code, _r, _n, sig in a_faire + a_noter:
            conn.execute(
                """INSERT INTO notif_push_etat (code, signature, updated_at) VALUES (?, ?, ?)
                   ON CONFLICT(code) DO UPDATE SET signature=excluded.signature, updated_at=excluded.updated_at""",
                (code, sig, now))
        conn.commit()
    for code, r, n, _sig in a_faire:
        det = DETECTEURS[code]
        for u in users:
            if u["role"] not in r["roles"]:
                continue
            if u["role"] != ROLE_SUPERADMIN:
                try:
                    if not a_acces(u, det.app):
                        continue
                except Exception:
                    continue
            envoyes += send_push(u["id"], title=det.app_label, body=det.libelle(n),
                                 url=det.lien, tag=f"notif-{code}") or 0
    return envoyes
