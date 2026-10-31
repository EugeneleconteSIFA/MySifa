"""MySifa — Outil RH (MyRH) : intitulés de poste.

Catalogue saisi à la main (MyRH › Catalogues › Postes) : un poste appartient à
un service (un rôle MySifa, cf. config.taches_services). Un employé suivi en
occupe zéro, un ou plusieurs ; une formation peut être exigée pour un poste
(PUT /{liste}/catalogue/{id}/exige, champ `postes`, dans rh_outil.py).

Comme pour les services : occuper un poste attribue les formations exigées
pour lui, et rien n'est jamais retiré automatiquement.
Accès : celui de l'Outil RH (accès à MyRH).
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from config import role_label
from database import get_db
from services.audit_service import log_action
from app.routers.rh_outil import (
    _attribuer_par_poste, _formations_du_membre, _justificatifs_lies, _libelle, _membre,
    _now, _postes_liste, _postes_valides, _require, _services,
)

router = APIRouter(prefix="/api/rh-outil", tags=["rh_outil"])


class PosteIn(BaseModel):
    libelle: str
    service: str


class PostePatch(BaseModel):
    libelle: Optional[str] = None
    service: Optional[str] = None


class PostesMembreIn(BaseModel):
    postes: list[int] = []


def _service_valide(code: str) -> str:
    code = (code or "").strip()
    if code not in {s["code"] for s in _services()}:
        raise HTTPException(400, "Service inconnu.")
    return code


def _poste(conn, poste_id: int):
    row = conn.execute("SELECT id, libelle, service FROM rh_outil_poste_catalogue WHERE id=?",
                       (poste_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Poste introuvable.")
    return row


def _doublon_poste(conn, service: str, libelle: str, sauf_id: int = 0) -> bool:
    return conn.execute(
        """SELECT 1 FROM rh_outil_poste_catalogue
            WHERE service = ? AND libelle = ? COLLATE NOCASE AND id != ?""",
        (service, libelle, sauf_id),
    ).fetchone() is not None


@router.get("/postes")
def list_postes(request: Request):
    _require(request)
    with get_db() as conn:
        return {"postes": _postes_liste(conn)}


@router.post("/postes")
def add_poste(payload: PosteIn, request: Request):
    user = _require(request)
    libelle = _libelle(payload.libelle)
    service = _service_valide(payload.service)
    with get_db() as conn:
        if _doublon_poste(conn, service, libelle):
            raise HTTPException(409, "Ce poste existe déjà dans ce service.")
        cur = conn.execute(
            "INSERT INTO rh_outil_poste_catalogue (libelle, service, cree_le, cree_par) VALUES (?,?,?,?)",
            (libelle, service, _now(), user.get("nom")),
        )
        conn.commit()
    log_action(user=user, action="CREATE", module="rh_outil",
               objet=f"Outil RH · postes · ajout de « {libelle} » ({role_label(service)})", request=request)
    return {"success": True, "id": cur.lastrowid}


@router.put("/postes/{poste_id}")
def update_poste(poste_id: int, payload: PostePatch, request: Request):
    """Renomme le poste ou le range dans un autre service. Les employés qui
    l'occupent le gardent, et gardent leurs formations."""
    user = _require(request)
    with get_db() as conn:
        row = _poste(conn, poste_id)
        libelle = _libelle(payload.libelle) if payload.libelle is not None else row["libelle"]
        service = _service_valide(payload.service) if payload.service is not None else row["service"]
        if libelle == row["libelle"] and service == row["service"]:
            return {"success": True}
        if _doublon_poste(conn, service, libelle, poste_id):
            raise HTTPException(409, "Ce poste existe déjà dans ce service.")
        conn.execute("UPDATE rh_outil_poste_catalogue SET libelle=?, service=? WHERE id=?",
                     (libelle, service, poste_id))
        conn.commit()
    changes = []
    if libelle != row["libelle"]:
        changes.append(f"renommé « {libelle} »")
    if service != row["service"]:
        changes.append(f"service : {role_label(service)}")
    log_action(user=user, action="UPDATE", module="rh_outil",
               objet=f"Outil RH · postes · « {row['libelle']} » " + ", ".join(changes), request=request)
    return {"success": True}


@router.delete("/postes/{poste_id}")
def delete_poste(poste_id: int, request: Request):
    """Supprime le poste du catalogue, des employés qui l'occupent et des
    exigences de formation. Les formations déjà attribuées restent."""
    user = _require(request)
    with get_db() as conn:
        row = _poste(conn, poste_id)
        n = conn.execute("DELETE FROM rh_outil_membre_poste WHERE poste_id=?", (poste_id,)).rowcount
        conn.execute("DELETE FROM rh_outil_formation_poste WHERE poste_id=?", (poste_id,))
        conn.execute("DELETE FROM rh_outil_poste_catalogue WHERE id=?", (poste_id,))
        conn.commit()
    log_action(user=user, action="DELETE", module="rh_outil",
               objet=f"Outil RH · postes · suppression de « {row['libelle']} » ({n} employé(s))",
               request=request)
    return {"success": True}


@router.put("/membres/{membre_id}/postes")
def set_postes_membre(membre_id: int, payload: PostesMembreIn, request: Request):
    """Postes occupés par l'employé (remplace la liste). Un poste ajouté lui
    attribue les formations exigées pour ce poste ; un poste retiré ne lui
    retire aucune formation."""
    user = _require(request)
    with get_db() as conn:
        m = _membre(conn, membre_id)
        voulus = set(_postes_valides(conn, payload.postes))
        avant = {r["poste_id"] for r in conn.execute(
            "SELECT poste_id FROM rh_outil_membre_poste WHERE membre_id=?", (membre_id,)).fetchall()}
        for pid in avant - voulus:
            conn.execute("DELETE FROM rh_outil_membre_poste WHERE membre_id=? AND poste_id=?", (membre_id, pid))
        n = 0
        for pid in voulus - avant:
            conn.execute("INSERT OR IGNORE INTO rh_outil_membre_poste (membre_id, poste_id, ajoute_le) VALUES (?,?,?)",
                         (membre_id, pid, _now()))
            n += _attribuer_par_poste(conn, membre_id=membre_id, poste_id=pid)
        if n:
            _justificatifs_lies(conn, _formations_du_membre(conn, membre_id))
        noms = {r["id"]: r["libelle"] for r in conn.execute(
            "SELECT id, libelle FROM rh_outil_poste_catalogue").fetchall()}
        conn.commit()
    if voulus != avant:
        log_action(user=user, action="UPDATE", module="rh_outil",
                   objet=f"Outil RH · {m['nom']} · postes : "
                         + (", ".join(sorted(noms.get(p, str(p)) for p in voulus)) or "aucun")
                         + (f" · {n} formation(s) attribuée(s)" if n else ""),
                   request=request)
    return {"success": True, "attribues": n}
