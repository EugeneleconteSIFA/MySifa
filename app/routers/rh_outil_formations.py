"""MySifa — Outil RH (MyCompta) : catégories et justificatifs des formations.

- Catégories : référentiel modifiable (rh_outil_formation_categories) ;
  supprimer une catégorie laisse ses formations « sans catégorie ».
- Justificatifs : chaque formation définit les justificatifs attendus
  (attestation, certificat…, rh_outil_formation_justificatifs). Un employé qui
  a la formation a une case par justificatif (rh_outil_membre_justificatifs),
  affichée sous la formation, avec pièces jointes (rh_outil_pieces.cible =
  'justificatif', routes dans rh_outil_pieces.py).
Accès : celui de l'Outil RH (accès à MyCompta).
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from database import get_db
from services.audit_service import log_action
from app.routers.rh_outil import (
    LibelleIn, _categorie, _libelle, _now, _require, _retirer_justificatifs, _supprimer_fichiers,
)

router = APIRouter(prefix="/api/rh-outil", tags=["rh_outil"])


class CategorieRef(BaseModel):
    categorie_id: Optional[int] = None


class FaitIn(BaseModel):
    fait: bool


# ─── Catégories ───────────────────────────────────────────────────────────

@router.get("/formations/categories")
def list_categories(request: Request):
    _require(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT c.id, c.libelle, c.ordre,
                      (SELECT COUNT(*) FROM rh_outil_formations f WHERE f.categorie_id = c.id) AS nb
                 FROM rh_outil_formation_categories c
                ORDER BY c.ordre, c.libelle COLLATE NOCASE"""
        ).fetchall()
    return {"categories": [{"id": r["id"], "libelle": r["libelle"], "nb_formations": r["nb"]} for r in rows]}


@router.post("/formations/categories")
def add_categorie(payload: LibelleIn, request: Request):
    user = _require(request)
    libelle = _libelle(payload.libelle)
    with get_db() as conn:
        if conn.execute("SELECT 1 FROM rh_outil_formation_categories WHERE libelle=? COLLATE NOCASE",
                        (libelle,)).fetchone():
            raise HTTPException(409, "Cette catégorie existe déjà.")
        ordre = conn.execute("SELECT COALESCE(MAX(ordre),0)+10 FROM rh_outil_formation_categories").fetchone()[0]
        cur = conn.execute(
            "INSERT INTO rh_outil_formation_categories (libelle, ordre, cree_le) VALUES (?,?,?)",
            (libelle, ordre, _now()))
        conn.commit()
    log_action(user=user, action="CREATE", module="rh_outil",
               objet=f"Outil RH · catégories de formations · ajout de « {libelle} »", request=request)
    return {"success": True, "id": cur.lastrowid}


@router.put("/formations/categories/{categorie_id}")
def rename_categorie(categorie_id: int, payload: LibelleIn, request: Request):
    user = _require(request)
    libelle = _libelle(payload.libelle)
    with get_db() as conn:
        row = _categorie(conn, categorie_id)
        if row["libelle"] == libelle:
            return {"success": True}
        if conn.execute("SELECT 1 FROM rh_outil_formation_categories WHERE libelle=? COLLATE NOCASE AND id!=?",
                        (libelle, categorie_id)).fetchone():
            raise HTTPException(409, "Cette catégorie existe déjà.")
        conn.execute("UPDATE rh_outil_formation_categories SET libelle=? WHERE id=?", (libelle, categorie_id))
        conn.commit()
    log_action(user=user, action="UPDATE", module="rh_outil",
               objet=f"Outil RH · catégories de formations · « {row['libelle']} » → « {libelle} »",
               request=request)
    return {"success": True}


@router.delete("/formations/categories/{categorie_id}")
def delete_categorie(categorie_id: int, request: Request):
    """Supprime la catégorie ; ses formations restent, sans catégorie."""
    user = _require(request)
    with get_db() as conn:
        row = _categorie(conn, categorie_id)
        n = conn.execute("UPDATE rh_outil_formations SET categorie_id=NULL WHERE categorie_id=?",
                         (categorie_id,)).rowcount
        conn.execute("DELETE FROM rh_outil_formation_categories WHERE id=?", (categorie_id,))
        conn.commit()
    log_action(user=user, action="DELETE", module="rh_outil",
               objet=f"Outil RH · catégories de formations · suppression de « {row['libelle']} » "
                     f"({n} formation(s) sans catégorie)", request=request)
    return {"success": True}


@router.put("/formations/catalogue/{element_id}/categorie")
def set_categorie(element_id: int, payload: CategorieRef, request: Request):
    user = _require(request)
    with get_db() as conn:
        f = conn.execute("SELECT libelle, categorie_id FROM rh_outil_formations WHERE id=?",
                         (element_id,)).fetchone()
        if not f:
            raise HTTPException(404, "Formation introuvable.")
        cat = _categorie(conn, payload.categorie_id)
        if f["categorie_id"] == payload.categorie_id:
            return {"success": True}
        conn.execute("UPDATE rh_outil_formations SET categorie_id=? WHERE id=?",
                     (payload.categorie_id, element_id))
        conn.commit()
    log_action(user=user, action="UPDATE", module="rh_outil",
               objet=f"Outil RH · catalogue des formations · « {f['libelle']} » → catégorie "
                     f"« {cat['libelle'] if cat else 'Sans catégorie'} »", request=request)
    return {"success": True}


# ─── Justificatifs attendus d'une formation ───────────────────────────────

def _justificatif(conn, justificatif_id: int):
    row = conn.execute(
        """SELECT j.id, j.formation_id, j.libelle, f.libelle AS formation
             FROM rh_outil_formation_justificatifs j
             JOIN rh_outil_formations f ON f.id = j.formation_id WHERE j.id=?""",
        (justificatif_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Justificatif introuvable.")
    return row


@router.post("/formations/catalogue/{formation_id}/justificatifs")
def add_justificatif(formation_id: int, payload: LibelleIn, request: Request):
    """Ajoute un justificatif attendu ; chaque employé qui a déjà la formation
    reçoit la case tout de suite."""
    user = _require(request)
    libelle = _libelle(payload.libelle)
    with get_db() as conn:
        f = conn.execute("SELECT libelle FROM rh_outil_formations WHERE id=?", (formation_id,)).fetchone()
        if not f:
            raise HTTPException(404, "Formation introuvable.")
        if conn.execute(
            """SELECT 1 FROM rh_outil_formation_justificatifs
                WHERE formation_id=? AND libelle=? COLLATE NOCASE""", (formation_id, libelle)).fetchone():
            raise HTTPException(409, "Ce justificatif existe déjà pour cette formation.")
        cur = conn.execute(
            "INSERT INTO rh_outil_formation_justificatifs (formation_id, libelle, cree_le) VALUES (?,?,?)",
            (formation_id, libelle, _now()))
        n = conn.execute(
            """INSERT OR IGNORE INTO rh_outil_membre_justificatifs (attribution_id, justificatif_id, fait, ajoute_le)
               SELECT a.id, ?, 0, ? FROM rh_outil_membre_formations a WHERE a.formation_id = ?""",
            (cur.lastrowid, _now(), formation_id)).rowcount
        conn.commit()
    suite = f" · attendu chez {n} employé(s)" if n else ""
    log_action(user=user, action="CREATE", module="rh_outil",
               objet=f"Outil RH · formation « {f['libelle']} » · justificatif « {libelle} » ajouté{suite}",
               request=request)
    return {"success": True, "id": cur.lastrowid, "attribues": n}


@router.put("/formations/justificatifs/{justificatif_id}")
def rename_justificatif(justificatif_id: int, payload: LibelleIn, request: Request):
    user = _require(request)
    libelle = _libelle(payload.libelle)
    with get_db() as conn:
        j = _justificatif(conn, justificatif_id)
        if j["libelle"] == libelle:
            return {"success": True}
        if conn.execute(
            """SELECT 1 FROM rh_outil_formation_justificatifs
                WHERE formation_id=? AND libelle=? COLLATE NOCASE AND id!=?""",
            (j["formation_id"], libelle, justificatif_id)).fetchone():
            raise HTTPException(409, "Ce justificatif existe déjà pour cette formation.")
        conn.execute("UPDATE rh_outil_formation_justificatifs SET libelle=? WHERE id=?", (libelle, justificatif_id))
        conn.commit()
    log_action(user=user, action="UPDATE", module="rh_outil",
               objet=f"Outil RH · formation « {j['formation']} » · justificatif « {j['libelle']} » → « {libelle} »",
               request=request)
    return {"success": True}


@router.delete("/formations/justificatifs/{justificatif_id}")
def delete_justificatif(justificatif_id: int, request: Request):
    """Supprime le justificatif de la formation et de tous les employés, avec
    leurs pièces jointes."""
    user = _require(request)
    with get_db() as conn:
        j = _justificatif(conn, justificatif_id)
        rows = conn.execute(
            """SELECT p.id, p.fichier FROM rh_outil_pieces p
                 JOIN rh_outil_membre_justificatifs mj ON mj.id = p.attribution_id
                WHERE p.cible = 'justificatif' AND mj.justificatif_id = ?""", (justificatif_id,)).fetchall()
        for r in rows:
            conn.execute("DELETE FROM rh_outil_pieces WHERE id=?", (r["id"],))
        n = conn.execute("DELETE FROM rh_outil_membre_justificatifs WHERE justificatif_id=?",
                         (justificatif_id,)).rowcount
        conn.execute("DELETE FROM rh_outil_formation_justificatifs WHERE id=?", (justificatif_id,))
        conn.commit()
    _supprimer_fichiers([r["fichier"] for r in rows])
    log_action(user=user, action="DELETE", module="rh_outil",
               objet=f"Outil RH · formation « {j['formation']} » · justificatif « {j['libelle']} » supprimé "
                     f"({n} employé(s))", request=request)
    return {"success": True}


@router.patch("/justificatifs/{membre_justificatif_id}")
def cocher_justificatif(membre_justificatif_id: int, payload: FaitIn, request: Request):
    user = _require(request)
    with get_db() as conn:
        row = conn.execute(
            """SELECT mj.id, j.libelle, f.libelle AS formation, u.nom
                 FROM rh_outil_membre_justificatifs mj
                 JOIN rh_outil_formation_justificatifs j ON j.id = mj.justificatif_id
                 JOIN rh_outil_formations f ON f.id = j.formation_id
                 JOIN rh_outil_membre_formations a ON a.id = mj.attribution_id
                 JOIN rh_outil_membres m ON m.id = a.membre_id
                 JOIN users u ON u.id = m.user_id
                WHERE mj.id=?""", (membre_justificatif_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Justificatif introuvable pour cet employé.")
        conn.execute("UPDATE rh_outil_membre_justificatifs SET fait=? WHERE id=?",
                     (1 if payload.fait else 0, membre_justificatif_id))
        conn.commit()
    log_action(user=user, action="UPDATE", module="rh_outil",
               objet=f"Outil RH · {row['nom']} · formation « {row['formation']} » · « {row['libelle']} » : "
                     f"{'reçu' if payload.fait else 'à fournir'}", request=request)
    return {"success": True}
