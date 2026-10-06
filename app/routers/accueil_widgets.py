"""MySifa — Widgets d'accueil (colonne « Mes widgets » du portail).

Endpoints utilisateur :
  GET    /api/accueil/blocs                 blocs capturables pour cet utilisateur
  GET    /api/accueil/widgets               mes widgets, URL résolue
  POST   /api/accueil/widgets               créer un widget (depuis la capture)
  PATCH  /api/accueil/widgets/{id}          renommer, valeurs, affichage, hauteur
  DELETE /api/accueil/widgets/{id}          supprimer
  PUT    /api/accueil/widgets-ordre         réordonner (liste complète des ids)
  GET    /api/accueil/prefs                 colonne repliée ou non
  PUT    /api/accueil/prefs

Endpoints superadmin (écran « Blocs capturables » de Paramètres) :
  GET    /api/accueil/blocs/admin           tous les blocs, usage, interrupteur
  PATCH  /api/accueil/blocs/admin/{nom}     activer / désactiver la capture

Le serveur ne calcule aucune donnée de bloc : le widget charge la page réelle,
qui applique ses propres droits. Le filtre d'accès ci-dessous sert seulement à
ne pas proposer à la capture un bloc dont la page serait refusée.
"""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.database import get_db
from app.services import blocs_registre as reg
from app.services.auth_service import (
    get_current_user,
    require_superadmin,
    user_has_app_access,
)

router = APIRouter(tags=["accueil-widgets"])

_COLS = ("id, bloc, objet, url_capture, nom, valeurs, affichage, hauteur, ordre,"
         " created_at, updated_at")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _bloc_accessible(user: dict, bloc: reg.Bloc) -> bool:
    return bloc.acces is None or user_has_app_access(user, bloc.acces)


def _desactives(conn) -> set[str]:
    rows = conn.execute("SELECT bloc FROM blocs_reglages WHERE capturable=0").fetchall()
    return {r["bloc"] for r in rows}


def _bloc_public(nom: str, b: reg.Bloc) -> dict:
    return {
        "nom": nom,
        "appli": b.appli,
        "libelle": b.libelle,
        "type": b.type,
        "objet": b.objet,
        "valeurs": [{"cle": c, "libelle": l} for c, l in b.valeurs],
        "url": b.url,
    }


def _widget_public(row, user: dict, desactives: set[str]) -> dict:
    w = dict(row)
    try:
        w["valeurs"] = json.loads(w.get("valeurs") or "[]")
    except (TypeError, ValueError):
        w["valeurs"] = []
    r = reg.resoudre(w["bloc"])
    if not r:
        # Bloc supprimé de MySifa : le front retire le widget et prévient.
        w["etat"] = "disparu"
        w["url"] = None
        return w
    nom, bloc = r
    w["bloc"] = nom
    w["url"] = reg.url_widget(nom, w["url_capture"])
    w["bloc_info"] = _bloc_public(nom, bloc)
    if nom in desactives:
        w["etat"] = "desactive"
    elif not _bloc_accessible(user, bloc):
        w["etat"] = "inaccessible"
    else:
        w["etat"] = "ok"
    return w


def _dump(modele: BaseModel) -> dict:
    # Pydantic v2 en production, v1 possible sur un poste de dev.
    return modele.model_dump() if hasattr(modele, "model_dump") else modele.dict()


def _get_widget_or_404(conn, widget_id: int, user_id: int):
    row = conn.execute(
        f"SELECT {_COLS} FROM accueil_widgets WHERE id=? AND user_id=?",
        (widget_id, user_id),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Indicateur introuvable.")
    return row


# ─── Modèles ─────────────────────────────────────────────────────────────────

class WidgetCreate(BaseModel):
    bloc: str
    url_capture: str
    objet: Optional[str] = None
    nom: str
    valeurs: list = []
    affichage: str = "valeurs"
    hauteur: str = "m"


class WidgetUpdate(BaseModel):
    nom: Optional[str] = None
    valeurs: Optional[list] = None
    affichage: Optional[str] = None
    hauteur: Optional[str] = None


class Ordre(BaseModel):
    ids: list[int]


class Prefs(BaseModel):
    colonne_repliee: bool


class Reglage(BaseModel):
    capturable: bool


# ─── Utilisateur ─────────────────────────────────────────────────────────────

@router.get("/api/accueil/blocs")
def blocs_capturables(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        desactives = _desactives(conn)
    return {
        "valeurs_max": reg.VALEURS_MAX,
        "blocs": [
            _bloc_public(nom, b)
            for nom, b in reg.BLOCS.items()
            if nom not in desactives and _bloc_accessible(user, b)
        ],
    }


@router.get("/api/accueil/widgets")
def mes_widgets(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        desactives = _desactives(conn)
        rows = conn.execute(
            f"SELECT {_COLS} FROM accueil_widgets WHERE user_id=? ORDER BY ordre, id",
            (user["id"],),
        ).fetchall()
    return {"widgets": [_widget_public(r, user, desactives) for r in rows]}


@router.post("/api/accueil/widgets")
def creer_widget(body: WidgetCreate, request: Request):
    user = get_current_user(request)
    try:
        w = reg.valider_widget(_dump(body), creation=True)
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    bloc = reg.BLOCS[w["bloc"]]
    if not _bloc_accessible(user, bloc):
        raise HTTPException(403, "Accès refusé à l'application de ce bloc.")
    now = _now()
    with get_db() as conn:
        if w["bloc"] in _desactives(conn):
            raise HTTPException(400, "Ce bloc n'est plus capturable.")
        ordre = conn.execute(
            "SELECT COALESCE(MAX(ordre), -1) + 1 FROM accueil_widgets WHERE user_id=?",
            (user["id"],),
        ).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO accueil_widgets (user_id, bloc, objet, url_capture, nom, valeurs,"
            " affichage, hauteur, ordre, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (user["id"], w["bloc"], w["objet"], w["url_capture"], w["nom"],
             json.dumps(w["valeurs"], ensure_ascii=False), w["affichage"], w["hauteur"],
             ordre, now, now),
        )
        conn.commit()
        row = _get_widget_or_404(conn, cur.lastrowid, user["id"])
        return _widget_public(row, user, _desactives(conn))


@router.patch("/api/accueil/widgets/{widget_id}")
def modifier_widget(widget_id: int, body: WidgetUpdate, request: Request):
    user = get_current_user(request)
    data = {k: v for k, v in _dump(body).items() if v is not None}
    if not data:
        return {"ok": True}
    with get_db() as conn:
        actuel = _get_widget_or_404(conn, widget_id, user["id"])
        # Les clés de valeurs se contrôlent contre le bloc du widget.
        data["bloc"] = actuel["bloc"]
        try:
            w = reg.valider_widget(data, creation=False)
        except ValueError as e:
            raise HTTPException(400, str(e)) from None
        if "valeurs" in w and not w["valeurs"]:
            raise HTTPException(400, "Cochez au moins une valeur.")
        if "valeurs" in w:
            w["valeurs"] = json.dumps(w["valeurs"], ensure_ascii=False)
        sets, params = [], []
        for col in ("bloc", "nom", "valeurs", "affichage", "hauteur"):
            if col in w:
                sets.append(f"{col}=?")
                params.append(w[col])
        sets.append("updated_at=?")
        params.extend([_now(), widget_id, user["id"]])
        conn.execute(
            f"UPDATE accueil_widgets SET {', '.join(sets)} WHERE id=? AND user_id=?",
            params,
        )
        conn.commit()
        row = _get_widget_or_404(conn, widget_id, user["id"])
        return _widget_public(row, user, _desactives(conn))


@router.delete("/api/accueil/widgets/{widget_id}")
def supprimer_widget(widget_id: int, request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        _get_widget_or_404(conn, widget_id, user["id"])
        conn.execute(
            "DELETE FROM accueil_widgets WHERE id=? AND user_id=?",
            (widget_id, user["id"]),
        )
        conn.commit()
    return {"ok": True}


@router.put("/api/accueil/widgets-ordre")
def reordonner(body: Ordre, request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        mes_ids = {
            r["id"] for r in conn.execute(
                "SELECT id FROM accueil_widgets WHERE user_id=?", (user["id"],)
            ).fetchall()
        }
        if set(body.ids) != mes_ids or len(body.ids) != len(mes_ids):
            raise HTTPException(400, "Ordre incomplet — rechargez la page.")
        for i, wid in enumerate(body.ids):
            conn.execute(
                "UPDATE accueil_widgets SET ordre=? WHERE id=? AND user_id=?",
                (i, wid, user["id"]),
            )
        conn.commit()
    return {"ok": True}


@router.get("/api/accueil/prefs")
def lire_prefs(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT colonne_repliee FROM accueil_prefs WHERE user_id=?", (user["id"],)
        ).fetchone()
    return {"colonne_repliee": bool(row and row["colonne_repliee"])}


@router.put("/api/accueil/prefs")
def ecrire_prefs(body: Prefs, request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO accueil_prefs (user_id, colonne_repliee, updated_at) VALUES (?,?,?)"
            " ON CONFLICT(user_id) DO UPDATE SET colonne_repliee=excluded.colonne_repliee,"
            " updated_at=excluded.updated_at",
            (user["id"], 1 if body.colonne_repliee else 0, _now()),
        )
        conn.commit()
    return {"ok": True}


# ─── Superadmin ──────────────────────────────────────────────────────────────

@router.get("/api/accueil/blocs/admin")
def blocs_admin(request: Request):
    require_superadmin(request)
    with get_db() as conn:
        reglages = {
            r["bloc"]: r for r in conn.execute(
                "SELECT bloc, capturable, updated_at, updated_by FROM blocs_reglages"
            ).fetchall()
        }
        usages = {
            r["bloc"]: r["n"] for r in conn.execute(
                "SELECT bloc, COUNT(*) AS n FROM accueil_widgets GROUP BY bloc"
            ).fetchall()
        }
    out = []
    for nom, b in reg.BLOCS.items():
        rg = reglages.get(nom)
        n = usages.get(nom, 0) + sum(usages.get(a, 0) for a in b.alias)
        out.append({
            **_bloc_public(nom, b),
            "capturable": bool(rg["capturable"]) if rg else True,
            "nouveau": rg is None,
            "nb_widgets": n,
            "updated_at": rg["updated_at"] if rg else None,
            "updated_by": rg["updated_by"] if rg else None,
        })
    return {"blocs": out}


@router.patch("/api/accueil/blocs/admin/{nom}")
def regler_bloc(nom: str, body: Reglage, request: Request):
    user = require_superadmin(request)
    if nom not in reg.BLOCS:
        raise HTTPException(404, "Bloc inconnu.")
    with get_db() as conn:
        conn.execute(
            "INSERT INTO blocs_reglages (bloc, capturable, updated_at, updated_by) VALUES (?,?,?,?)"
            " ON CONFLICT(bloc) DO UPDATE SET capturable=excluded.capturable,"
            " updated_at=excluded.updated_at, updated_by=excluded.updated_by",
            (nom, 1 if body.capturable else 0, _now(), user.get("email") or str(user["id"])),
        )
        conn.commit()
    return {"ok": True}
