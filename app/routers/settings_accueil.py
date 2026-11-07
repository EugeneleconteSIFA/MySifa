"""
Accueil des Paramètres : onglets ouverts récemment et bandeau « À traiter ».

Un signal du bandeau remplit quatre conditions : c'est un compte en base qui
retombe à zéro quand le travail est fait, il se règle depuis l'onglet des
Paramètres vers lequel il mène, il suit les droits de cet onglet, et il n'est
pas renvoyé quand il vaut zéro. Chaque source est isolée : une source qui
plante n'empêche pas les autres de s'afficher.
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from config import (
    ENV_NAME,
    FSC_ALERTE_JOURS,
    SETTINGS_RECENTS_DEFAUT,
    SETTINGS_RECENTS_DEFAUT_AUTRES,
    SETTINGS_RECENTS_NOMBRE,
)
from database import get_db
from services.auth_service import (
    can_access_settings,
    effective_role,
    get_current_user,
    settings_sections_visibility,
)
from app.services.settings_catalogue import onglets_visibles

router = APIRouter()

_PARIS = ZoneInfo("Europe/Paris")
_GARDER = 20  # lignes conservées par utilisateur


def _utilisateur(request: Request):
    user = get_current_user(request)
    if not can_access_settings(user):
        raise HTTPException(403, "Accès réservé aux Paramètres.")
    return user, settings_sections_visibility(user)


# ── Ouverts récemment ──────────────────────────────────────────────────────

class _Ouverture(BaseModel):
    onglet: str


@router.get("/api/settings/recents")
def recents(request: Request):
    user, vis = _utilisateur(request)
    ouverts = onglets_visibles(vis)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT onglet, ouvert_le FROM settings_recents WHERE user_id=? ORDER BY ouvert_le DESC",
            (user["id"],),
        ).fetchall()
    items = []
    for r in rows:
        if r["onglet"] in ouverts and len(items) < SETTINGS_RECENTS_NOMBRE:
            items.append({"onglet": r["onglet"], "ouvert_le": r["ouvert_le"]})
    deja = {i["onglet"] for i in items}
    defaut = SETTINGS_RECENTS_DEFAUT.get(effective_role(user), SETTINGS_RECENTS_DEFAUT_AUTRES)
    for tab in list(defaut) + list(ouverts):
        if len(items) >= SETTINGS_RECENTS_NOMBRE:
            break
        if tab in ouverts and tab not in deja:
            items.append({"onglet": tab, "ouvert_le": None})
            deja.add(tab)
    return {"items": items}


@router.post("/api/settings/recents")
def noter_ouverture(request: Request, body: _Ouverture):
    user, vis = _utilisateur(request)
    if body.onglet not in onglets_visibles(vis):
        raise HTTPException(400, "Onglet inconnu.")
    maintenant = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        conn.execute(
            "INSERT INTO settings_recents (user_id, onglet, ouvert_le) VALUES (?,?,?) "
            "ON CONFLICT(user_id, onglet) DO UPDATE SET ouvert_le=excluded.ouvert_le",
            (user["id"], body.onglet, maintenant),
        )
        conn.execute(
            "DELETE FROM settings_recents WHERE user_id=? AND onglet NOT IN ("
            " SELECT onglet FROM settings_recents WHERE user_id=? ORDER BY ouvert_le DESC LIMIT ?)",
            (user["id"], user["id"], _GARDER),
        )
        conn.commit()
    return {"ok": True}


# ── À traiter ──────────────────────────────────────────────────────────────

def _pluriel(n, un, plusieurs):
    return "%d %s" % (n, un if n == 1 else plusieurs)


def _fsc(conn):
    """Même calcul que MyQualité › FSC : expiration lue au dernier contrôle,
    sinon sur le document, sinon sur la fiche fournisseur."""
    from app.routers.qualite_fsc import _synthese
    lignes = _synthese(conn)["fournisseurs"]
    expires = sum(1 for l in lignes if l.get("statut") == "expire")
    a_renouveler = sum(1 for l in lignes if l.get("statut") == "a_renouveler")
    out = []
    if expires:
        out.append({"cle": "fsc_expire", "onglet": "fournisseurs", "niveau": "bloquant", "nombre": expires,
                    "libelle": _pluriel(expires, "certificat FSC expiré", "certificats FSC expirés")})
    if a_renouveler:
        out.append({"cle": "fsc_a_renouveler", "onglet": "fournisseurs", "niveau": "a_traiter", "nombre": a_renouveler,
                    "libelle": _pluriel(a_renouveler, "certificat FSC à renouveler", "certificats FSC à renouveler")
                               + " sous %d j" % FSC_ALERTE_JOURS})
    return out


def _coherence(conn):
    n = conn.execute("SELECT COUNT(*) FROM coherence_ecarts WHERE statut='ouvert'").fetchone()[0]
    if not n:
        return []
    return [{"cle": "coherence", "onglet": "coherence", "niveau": "a_traiter", "nombre": n,
             "libelle": _pluriel(n, "écart de cohérence", "écarts de cohérence")}]


def _appairage(conn):
    from app.services.pricing_bridge import list_orphaned_mp
    n = len(list_orphaned_mp(conn))
    if not n:
        return []
    return [{"cle": "appairage", "onglet": "bridge", "niveau": "a_traiter", "nombre": n,
             "libelle": _pluriel(n, "matière à appairer", "matières à appairer")}]


def _maintenance(conn):
    cols = {c[1] for c in conn.execute("PRAGMA table_info(maintenance_codes)").fetchall()}
    if "libre" not in cols:
        return []
    n = conn.execute("SELECT COUNT(*) FROM maintenance_codes WHERE libre=1").fetchone()[0]
    if not n:
        return []
    return [{"cle": "maintenance_libres", "onglet": "maintenance", "niveau": "a_traiter", "nombre": n,
             "libelle": _pluriel(n, "code de maintenance libre", "codes de maintenance libres")}]


def _promotion():
    """Changements de staging absents de v2, sur les références connues du
    dernier fetch (celui de l'onglet Promouvoir) : pas de fetch ici, l'accueil
    doit répondre tout de suite."""
    if ENV_NAME != "v1":
        return []
    from app.routers.settings import V2_REPO_PATH, _GIT_BIN
    res = subprocess.run(
        [_GIT_BIN, "-C", V2_REPO_PATH, "rev-list", "--count", "HEAD..origin/staging"],
        capture_output=True, text=True, timeout=3,
    )
    n = int((res.stdout or "0").strip() or 0) if res.returncode == 0 else 0
    if not n:
        return []
    return [{"cle": "promotion", "onglet": "promote", "niveau": "info", "nombre": n,
             "libelle": _pluriel(n, "changement prêt à promouvoir", "changements prêts à promouvoir")}]


_ORDRE = {"bloquant": 0, "a_traiter": 1, "info": 2}


@router.get("/api/settings/a-traiter")
def a_traiter(request: Request):
    _user, vis = _utilisateur(request)
    ouverts = onglets_visibles(vis)
    signaux = []
    with get_db() as conn:
        for onglet, source in (("fournisseurs", _fsc), ("coherence", _coherence),
                               ("bridge", _appairage), ("maintenance", _maintenance)):
            if onglet not in ouverts:
                continue
            try:
                signaux.extend(source(conn))
            except Exception:
                pass
    if "promote" in ouverts:
        try:
            signaux.extend(_promotion())
        except Exception:
            pass
    signaux.sort(key=lambda s: _ORDRE.get(s["niveau"], 9))
    return {"signaux": signaux}
