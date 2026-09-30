"""MySifa — Outil RH (MyCompta) : pièces jointes.

Deux cibles, une seule table (rh_outil_pieces.cible) :
- 'document'     : document administratif d'un employé (rh_outil_membre_documents) ;
- 'justificatif' : justificatif de formation d'un employé (rh_outil_membre_justificatifs).
Fichiers rangés hors de /static sous data/uploads/rh_outil/, nom sur disque
généré ; type vérifié sur le contenu (PDF, JPG, PNG, WEBP, HEIC) ; service en
téléchargement par défaut, aperçu isolé (CSP sandbox, nosniff).
Accès : celui de l'Outil RH (accès à MyCompta).
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from config import RH_OUTIL_MAX_FILE_MB
from database import get_db
from services.audit_service import log_action
from app.routers import rh_outil as _rh
from app.routers.rh_outil import (
    LISTES, PIECE_MAX_OCTETS, PIECE_NOM_MAX, _attribution, _now, _piece_json, _require,
    _supprimer_fichiers, _type_fichier,
)

router = APIRouter(prefix="/api/rh-outil", tags=["rh_outil"])

# cible → (préfixe du dossier sur disque, requête qui décrit la cible)
_CIBLES = {
    "document": ("", """SELECT a.id, e.libelle, u.nom AS employe
                          FROM rh_outil_membre_documents a
                          JOIN rh_outil_documents e ON e.id = a.document_id
                          JOIN rh_outil_membres m ON m.id = a.membre_id
                          JOIN users u ON u.id = m.user_id
                         WHERE a.id=?"""),
    "justificatif": ("j", """SELECT mj.id, f.libelle || ' · ' || j.libelle AS libelle, u.nom AS employe
                               FROM rh_outil_membre_justificatifs mj
                               JOIN rh_outil_formation_justificatifs j ON j.id = mj.justificatif_id
                               JOIN rh_outil_formations f ON f.id = j.formation_id
                               JOIN rh_outil_membre_formations a ON a.id = mj.attribution_id
                               JOIN rh_outil_membres m ON m.id = a.membre_id
                               JOIN users u ON u.id = m.user_id
                              WHERE mj.id=?"""),
}


def _cible(conn, cible: str, cible_id: int):
    row = conn.execute(_CIBLES[cible][1], (cible_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Document introuvable pour cet employé." if cible == "document"
                            else "Justificatif introuvable pour cet employé.")
    return row


def _lister(cible: str, cible_id: int, request: Request) -> dict:
    _require(request)
    with get_db() as conn:
        _cible(conn, cible, cible_id)
        rows = conn.execute(
            """SELECT id, attribution_id, nom, mime, taille, ajoute_le, ajoute_par
                 FROM rh_outil_pieces WHERE cible=? AND attribution_id=? ORDER BY ajoute_le, id""",
            (cible, cible_id),
        ).fetchall()
    return {"pieces": [_piece_json(r) for r in rows]}


async def _deposer(cible: str, cible_id: int, request: Request, fichier: UploadFile) -> dict:
    user = _require(request)
    # Lecture bornée : on ne charge jamais plus que la taille autorisée + 1 octet.
    contenu = await fichier.read(PIECE_MAX_OCTETS + 1)
    if not contenu:
        raise HTTPException(400, "Fichier vide.")
    if len(contenu) > PIECE_MAX_OCTETS:
        raise HTTPException(400, f"Fichier trop lourd — {RH_OUTIL_MAX_FILE_MB} Mo maximum.")
    detecte = _type_fichier(contenu[:16])
    if not detecte:
        raise HTTPException(400, "Format refusé — PDF, JPG, PNG, WEBP ou HEIC uniquement.")
    mime, ext = detecte
    nom = " ".join(Path(fichier.filename or "").name.split())[:PIECE_NOM_MAX] or f"piece.{ext}"
    racine = _rh.PIECES_ROOT
    with get_db() as conn:
        row = _cible(conn, cible, cible_id)
        dossier = f"{_CIBLES[cible][0]}{cible_id}"
        (racine / dossier).mkdir(parents=True, exist_ok=True)
        # Nom sur disque généré : rien du nom fourni par le navigateur n'y entre.
        relatif = f"{dossier}/{uuid.uuid4().hex}.{ext}"
        (racine / relatif).write_bytes(contenu)
        try:
            cur = conn.execute(
                """INSERT INTO rh_outil_pieces
                       (attribution_id, cible, nom, fichier, mime, taille, ajoute_le, ajoute_par)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (cible_id, cible, nom, relatif, mime, len(contenu), _now(), user.get("nom")),
            )
            conn.commit()
        except Exception:
            _supprimer_fichiers([relatif])
            raise
    log_action(user=user, action="UPLOAD", module="rh_outil",
               objet=f"Outil RH · {row['employe']} · « {row['libelle']} » : pièce jointe ajoutée",
               request=request)
    return {"success": True, "id": cur.lastrowid}


@router.get("/documents/attributions/{attribution_id}/pieces")
def list_pieces_document(attribution_id: int, request: Request):
    return _lister("document", attribution_id, request)


@router.post("/documents/attributions/{attribution_id}/pieces")
async def add_piece_document(attribution_id: int, request: Request, fichier: UploadFile = File(...)):
    return await _deposer("document", attribution_id, request, fichier)


@router.get("/justificatifs/{membre_justificatif_id}/pieces")
def list_pieces_justificatif(membre_justificatif_id: int, request: Request):
    return _lister("justificatif", membre_justificatif_id, request)


@router.post("/justificatifs/{membre_justificatif_id}/pieces")
async def add_piece_justificatif(membre_justificatif_id: int, request: Request,
                                 fichier: UploadFile = File(...)):
    return await _deposer("justificatif", membre_justificatif_id, request, fichier)


def _piece(conn, piece_id: int):
    p = conn.execute("SELECT id, attribution_id, cible, nom, fichier, mime FROM rh_outil_pieces WHERE id=?",
                     (piece_id,)).fetchone()
    if not p or p["cible"] not in _CIBLES:
        raise HTTPException(404, "Pièce jointe introuvable.")
    return p, _cible(conn, p["cible"], p["attribution_id"])


@router.get("/pieces/{piece_id}")
def get_piece(piece_id: int, request: Request, apercu: bool = False):
    """Téléchargement (par défaut) ou aperçu dans le navigateur (?apercu=1).

    Seuls des PDF et des images vérifiés au dépôt sont servis. L'aperçu est
    isolé (CSP sandbox) et nosniff : le navigateur n'exécute rien et ne
    réinterprète pas le type."""
    user = _require(request)
    with get_db() as conn:
        p, row = _piece(conn, piece_id)
    chemin = _rh.PIECES_ROOT / p["fichier"]
    if not chemin.is_file():
        raise HTTPException(410, "Fichier absent du serveur.")
    log_action(user=user, action="EXPORT", module="rh_outil",
               objet=f"Outil RH · {row['employe']} · « {row['libelle']} » : pièce jointe consultée",
               request=request)
    return FileResponse(
        str(chemin), media_type=p["mime"], filename=p["nom"],
        content_disposition_type="inline" if apercu else "attachment",
        headers={"X-Content-Type-Options": "nosniff",
                 "Content-Security-Policy": "sandbox",
                 "Cache-Control": "private, no-store"},
    )


@router.delete("/pieces/{piece_id}")
def delete_piece(piece_id: int, request: Request):
    user = _require(request)
    with get_db() as conn:
        p, row = _piece(conn, piece_id)
        conn.execute("DELETE FROM rh_outil_pieces WHERE id=?", (piece_id,))
        conn.commit()
    _supprimer_fichiers([p["fichier"]])
    log_action(user=user, action="DELETE", module="rh_outil",
               objet=f"Outil RH · {row['employe']} · « {row['libelle']} » : pièce jointe supprimée",
               request=request)
    return {"success": True}
