"""MySifa — Outil RH (onglet de MyCompta).

Liste partagée des employés suivis dans l'onglet « Outil RH ». On y ajoute un
employé choisi parmi tous les comptes (actifs ou non), on peut le retirer.
Chaque employé suivi porte une checklist :
- des cases fixes, une colonne de rh_outil_membres chacune (CHECKLIST) ;
- des listes qui varient d'un employé à l'autre (LISTES : formations,
  documents), piochées chacune dans un catalogue commun géré depuis l'onglet.
Accès : quiconque a accès à MyCompta (rôle ou exception réglée dans Paramètres).
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from database import get_db
from services.auth_service import get_current_user, user_has_app_access
from services.audit_service import log_action

router = APIRouter(prefix="/api/rh-outil", tags=["rh_outil"])

LIBELLE_MAX = 120


class MembreIn(BaseModel):
    user_id: int


class MembrePatch(BaseModel):
    reglement_signe: Optional[bool] = None


class LibelleIn(BaseModel):
    libelle: str


class AttributionIn(BaseModel):
    element_id: int


class AttributionPatch(BaseModel):
    fait: bool


# Listes par employé. Chaque liste = un catalogue + une table de liaison
# employé ↔ élément avec une case « fait ». Les noms de tables et de colonnes
# viennent d'ici, jamais de la requête : les f-strings SQL sont sûres.
LISTES = {
    "formations": {
        "catalogue": "rh_outil_formations",
        "liaison": "rh_outil_membre_formations",
        "fk": "formation_id",
        "nom": "formation",
        "catalogue_nom": "catalogue des formations",
        "doublon": "Cette formation existe déjà au catalogue.",
        "introuvable": "Formation introuvable.",
        "deja": "Cet employé a déjà cette formation.",
        "fait": ("faite", "à faire"),
    },
    "documents": {
        "catalogue": "rh_outil_documents",
        "liaison": "rh_outil_membre_documents",
        "fk": "document_id",
        "nom": "document",
        "catalogue_nom": "catalogue des documents",
        "doublon": "Ce document existe déjà au catalogue.",
        "introuvable": "Document introuvable.",
        "deja": "Cet employé a déjà ce document.",
        "fait": ("vérifié", "à vérifier"),
    },
}


def _liste(liste: str) -> dict:
    cfg = LISTES.get(liste)
    if not cfg:
        raise HTTPException(404, "Liste inconnue.")
    return cfg


# Points fixes de la checklist : champ de MembrePatch → libellé du journal.
# Chaque point est une colonne de rh_outil_membres (migration fichier).
CHECKLIST = {"reglement_signe": "Règlement signé"}


def _require(request: Request) -> dict:
    u = get_current_user(request)
    if not user_has_app_access(u, "compta"):
        raise HTTPException(status_code=403, detail="Accès réservé à MyCompta")
    return u


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _libelle(brut: str) -> str:
    libelle = " ".join((brut or "").split())
    if not libelle:
        raise HTTPException(400, "Intitulé vide.")
    if len(libelle) > LIBELLE_MAX:
        raise HTTPException(400, f"Intitulé trop long — {LIBELLE_MAX} caractères maximum.")
    return libelle


def _membre(conn, membre_id: int):
    row = conn.execute(
        """SELECT m.id, u.nom FROM rh_outil_membres m
             JOIN users u ON u.id = m.user_id WHERE m.id=?""",
        (membre_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Employé introuvable dans la liste.")
    return row


def _doublon(conn, cfg: dict, libelle: str, sauf_id: Optional[int] = None) -> bool:
    row = conn.execute(
        f"SELECT id FROM {cfg['catalogue']} WHERE libelle = ? COLLATE NOCASE AND id != ?",
        (libelle, sauf_id or 0),
    ).fetchone()
    return row is not None


# ─── Employés ─────────────────────────────────────────────────────────────

@router.get("/employes")
def list_employes(request: Request):
    """Tous les comptes, actifs ou non, pour le sélecteur d'ajout."""
    _require(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT u.id, u.nom, u.email, u.role, u.actif,
                      (m.id IS NOT NULL) AS deja_ajoute
                 FROM users u
                 LEFT JOIN rh_outil_membres m ON m.user_id = u.id
                WHERE LOWER(COALESCE(u.nom,'')) != 'administrateur'
                ORDER BY u.nom COLLATE NOCASE"""
        ).fetchall()
    return {"employes": [
        {"user_id": r["id"], "nom": r["nom"], "email": r["email"], "role": r["role"],
         "actif": bool(r["actif"]), "deja_ajoute": bool(r["deja_ajoute"])}
        for r in rows
    ]}


@router.get("/membres")
def list_membres(request: Request):
    _require(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT m.id, m.user_id, m.ajoute_le, m.ajoute_par, m.reglement_signe,
                      u.nom, u.email, u.role, u.actif
                 FROM rh_outil_membres m
                 JOIN users u ON u.id = m.user_id
                ORDER BY u.nom COLLATE NOCASE"""
        ).fetchall()
        # {liste: {membre_id: [éléments]}}
        par_liste: dict = {}
        for liste, cfg in LISTES.items():
            par_membre = par_liste.setdefault(liste, {})
            for a in conn.execute(
                f"""SELECT a.id, a.membre_id, a.{cfg['fk']} AS element_id, a.fait, e.libelle
                      FROM {cfg['liaison']} a
                      JOIN {cfg['catalogue']} e ON e.id = a.{cfg['fk']}
                     ORDER BY e.libelle COLLATE NOCASE"""
            ).fetchall():
                par_membre.setdefault(a["membre_id"], []).append(
                    {"id": a["id"], "element_id": a["element_id"],
                     "libelle": a["libelle"], "fait": bool(a["fait"])}
                )
    membres = []
    for r in rows:
        m = {"id": r["id"], "user_id": r["user_id"], "nom": r["nom"], "email": r["email"],
             "role": r["role"], "actif": bool(r["actif"]),
             "ajoute_le": r["ajoute_le"], "ajoute_par": r["ajoute_par"],
             "reglement_signe": bool(r["reglement_signe"])}
        for liste in LISTES:
            m[liste] = par_liste[liste].get(r["id"], [])
        membres.append(m)
    return {"membres": membres}


@router.post("/membres")
def add_membre(payload: MembreIn, request: Request):
    user = _require(request)
    with get_db() as conn:
        emp = conn.execute("SELECT id, nom FROM users WHERE id=?", (payload.user_id,)).fetchone()
        if not emp:
            raise HTTPException(404, "Employé introuvable.")
        cur = conn.execute(
            "INSERT OR IGNORE INTO rh_outil_membres (user_id, ajoute_le, ajoute_par) VALUES (?,?,?)",
            (emp["id"], _now(), user.get("nom")),
        )
        conn.commit()
        if not cur.rowcount:
            raise HTTPException(409, "Employé déjà dans la liste.")
    log_action(user=user, action="CREATE", module="rh_outil",
               objet=f"Outil RH · ajout de {emp['nom']}", request=request)
    return {"success": True}


@router.patch("/membres/{membre_id}")
def update_membre(membre_id: int, payload: MembrePatch, request: Request):
    user = _require(request)
    data = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if k in CHECKLIST}
    if not data:
        return {"success": True}
    with get_db() as conn:
        row = _membre(conn, membre_id)
        # Les clés viennent de CHECKLIST, jamais de la requête : pas d'injection.
        sets = ", ".join(f"{k}=?" for k in data)
        conn.execute(f"UPDATE rh_outil_membres SET {sets} WHERE id=?",
                     [1 if v else 0 for v in data.values()] + [membre_id])
        conn.commit()
    for k, v in data.items():
        log_action(user=user, action="UPDATE", module="rh_outil",
                   objet=f"Outil RH · {row['nom']} · {CHECKLIST[k]} : {'oui' if v else 'non'}",
                   request=request)
    return {"success": True}


@router.delete("/membres/{membre_id}")
def delete_membre(membre_id: int, request: Request):
    user = _require(request)
    with get_db() as conn:
        row = _membre(conn, membre_id)
        for cfg in LISTES.values():
            conn.execute(f"DELETE FROM {cfg['liaison']} WHERE membre_id=?", (membre_id,))
        conn.execute("DELETE FROM rh_outil_membres WHERE id=?", (membre_id,))
        conn.commit()
    log_action(user=user, action="DELETE", module="rh_outil",
               objet=f"Outil RH · retrait de {row['nom']}", request=request)
    return {"success": True}


# ─── Catalogues (formations, documents) ───────────────────────────────────

@router.get("/{liste}/catalogue")
def list_catalogue(liste: str, request: Request):
    _require(request)
    cfg = _liste(liste)
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT e.id, e.libelle,
                       (SELECT COUNT(*) FROM {cfg['liaison']} a
                         WHERE a.{cfg['fk']} = e.id) AS nb_employes
                  FROM {cfg['catalogue']} e
                 ORDER BY e.libelle COLLATE NOCASE"""
        ).fetchall()
    return {"elements": [
        {"id": r["id"], "libelle": r["libelle"], "nb_employes": r["nb_employes"]}
        for r in rows
    ]}


@router.post("/{liste}/catalogue")
def add_catalogue(liste: str, payload: LibelleIn, request: Request):
    user = _require(request)
    cfg = _liste(liste)
    libelle = _libelle(payload.libelle)
    with get_db() as conn:
        if _doublon(conn, cfg, libelle):
            raise HTTPException(409, cfg["doublon"])
        cur = conn.execute(
            f"INSERT INTO {cfg['catalogue']} (libelle, cree_le, cree_par) VALUES (?,?,?)",
            (libelle, _now(), user.get("nom")),
        )
        conn.commit()
    log_action(user=user, action="CREATE", module="rh_outil",
               objet=f"Outil RH · {cfg['catalogue_nom']} · ajout de « {libelle} »", request=request)
    return {"success": True, "id": cur.lastrowid}


@router.put("/{liste}/catalogue/{element_id}")
def rename_catalogue(liste: str, element_id: int, payload: LibelleIn, request: Request):
    user = _require(request)
    cfg = _liste(liste)
    libelle = _libelle(payload.libelle)
    with get_db() as conn:
        row = conn.execute(f"SELECT libelle FROM {cfg['catalogue']} WHERE id=?",
                           (element_id,)).fetchone()
        if not row:
            raise HTTPException(404, cfg["introuvable"])
        if row["libelle"] == libelle:
            return {"success": True}
        if _doublon(conn, cfg, libelle, element_id):
            raise HTTPException(409, cfg["doublon"])
        conn.execute(f"UPDATE {cfg['catalogue']} SET libelle=? WHERE id=?", (libelle, element_id))
        conn.commit()
    log_action(user=user, action="UPDATE", module="rh_outil",
               objet=f"Outil RH · {cfg['catalogue_nom']} · « {row['libelle']} » → « {libelle} »",
               request=request)
    return {"success": True}


@router.delete("/{liste}/catalogue/{element_id}")
def delete_catalogue(liste: str, element_id: int, request: Request):
    """Supprime l'élément du catalogue ET de tous les employés qui l'ont."""
    user = _require(request)
    cfg = _liste(liste)
    with get_db() as conn:
        row = conn.execute(f"SELECT libelle FROM {cfg['catalogue']} WHERE id=?",
                           (element_id,)).fetchone()
        if not row:
            raise HTTPException(404, cfg["introuvable"])
        n = conn.execute(f"DELETE FROM {cfg['liaison']} WHERE {cfg['fk']}=?",
                         (element_id,)).rowcount
        conn.execute(f"DELETE FROM {cfg['catalogue']} WHERE id=?", (element_id,))
        conn.commit()
    log_action(user=user, action="DELETE", module="rh_outil",
               objet=f"Outil RH · {cfg['catalogue_nom']} · suppression de « {row['libelle']} » ({n} employé(s))",
               request=request)
    return {"success": True}


# ─── Listes d'un employé ──────────────────────────────────────────────────

@router.post("/membres/{membre_id}/{liste}")
def add_attribution(membre_id: int, liste: str, payload: AttributionIn, request: Request):
    user = _require(request)
    cfg = _liste(liste)
    with get_db() as conn:
        m = _membre(conn, membre_id)
        e = conn.execute(f"SELECT libelle FROM {cfg['catalogue']} WHERE id=?",
                         (payload.element_id,)).fetchone()
        if not e:
            raise HTTPException(404, cfg["introuvable"])
        cur = conn.execute(
            f"""INSERT OR IGNORE INTO {cfg['liaison']}
                    (membre_id, {cfg['fk']}, fait, ajoute_le) VALUES (?,?,0,?)""",
            (membre_id, payload.element_id, _now()),
        )
        conn.commit()
        if not cur.rowcount:
            raise HTTPException(409, cfg["deja"])
    log_action(user=user, action="ASSIGN", module="rh_outil",
               objet=f"Outil RH · {m['nom']} · {cfg['nom']} « {e['libelle']} » : attribution",
               request=request)
    return {"success": True}


def _attribution(conn, cfg: dict, attribution_id: int):
    row = conn.execute(
        f"""SELECT a.id, e.libelle, u.nom
              FROM {cfg['liaison']} a
              JOIN {cfg['catalogue']} e ON e.id = a.{cfg['fk']}
              JOIN rh_outil_membres m ON m.id = a.membre_id
              JOIN users u ON u.id = m.user_id
             WHERE a.id=?""",
        (attribution_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, cfg["introuvable"])
    return row


@router.patch("/{liste}/attributions/{attribution_id}")
def update_attribution(liste: str, attribution_id: int, payload: AttributionPatch,
                       request: Request):
    user = _require(request)
    cfg = _liste(liste)
    with get_db() as conn:
        row = _attribution(conn, cfg, attribution_id)
        conn.execute(f"UPDATE {cfg['liaison']} SET fait=? WHERE id=?",
                     (1 if payload.fait else 0, attribution_id))
        conn.commit()
    etat = cfg["fait"][0] if payload.fait else cfg["fait"][1]
    log_action(user=user, action="UPDATE", module="rh_outil",
               objet=f"Outil RH · {row['nom']} · {cfg['nom']} « {row['libelle']} » : {etat}",
               request=request)
    return {"success": True}


@router.delete("/{liste}/attributions/{attribution_id}")
def delete_attribution(liste: str, attribution_id: int, request: Request):
    user = _require(request)
    cfg = _liste(liste)
    with get_db() as conn:
        row = _attribution(conn, cfg, attribution_id)
        conn.execute(f"DELETE FROM {cfg['liaison']} WHERE id=?", (attribution_id,))
        conn.commit()
    log_action(user=user, action="DELETE", module="rh_outil",
               objet=f"Outil RH · {row['nom']} · {cfg['nom']} « {row['libelle']} » : retrait",
               request=request)
    return {"success": True}
