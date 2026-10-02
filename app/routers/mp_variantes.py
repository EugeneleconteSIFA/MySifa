"""MyStock — variantes fournisseur d'une matière.

Toute la logique vit dans `app/services/mp_variantes.py` ; ce router tient
l'accès et le journal. Lecture : accès MyStock. Écriture : administrateurs
matières, comme la fiche matière elle-même.
"""
from fastapi import APIRouter, HTTPException, Request

from app.core.database import get_db
from app.routers.stock import require_stock, require_stock_matieres_admin
from app.services import mp_variantes as mv
from app.services.audit_service import log_action

router = APIRouter(tags=["stock-variantes"])


def _auteur(user: dict) -> str:
    return (user.get("nom") or user.get("email") or "").strip()


def _erreur(e: Exception):
    if isinstance(e, LookupError):
        raise HTTPException(404, str(e).strip("'\"")) from None
    raise HTTPException(400, str(e)) from None


@router.get("/api/stock/matieres/{matiere_id}/variantes")
def lister_variantes(matiere_id: int, request: Request, inactives: int = 0):
    require_stock(request)
    with get_db() as conn:
        try:
            out = mv.lister(conn, matiere_id, avec_inactives=bool(inactives))
        except (LookupError, ValueError) as e:
            _erreur(e)
        out["types_rvgi"] = mv.types_rvgi(conn)
        out["fournisseurs"] = [
            {"id": r["id"], "nom": r["nom"]}
            for r in conn.execute("SELECT id, nom FROM fournisseurs_fsc ORDER BY nom COLLATE NOCASE").fetchall()
        ]
    return out


@router.post("/api/stock/matieres/{matiere_id}/variantes")
async def creer_variante(matiere_id: int, request: Request):
    user = require_stock_matieres_admin(request)
    body = await request.json() or {}
    with get_db() as conn:
        try:
            vid = mv.creer(conn, matiere_id, body, _auteur(user))
        except (LookupError, ValueError) as e:
            _erreur(e)
        conn.commit()
        out = mv.lister(conn, matiere_id)
    log_action(user=user, request=request, module="stock", action="CREATE",
               objet=f"matiere:{matiere_id}:variante:{vid}",
               detail=str(body.get("libelle_technique") or "")[:200])
    return out


@router.put("/api/stock/variantes/{variante_id}")
async def modifier_variante(variante_id: int, request: Request):
    user = require_stock_matieres_admin(request)
    body = await request.json() or {}
    with get_db() as conn:
        try:
            r = mv.modifier(conn, variante_id, body, _auteur(user))
        except (LookupError, ValueError) as e:
            _erreur(e)
        conn.commit()
        out = mv.lister(conn, r["matiere_id"])
    log_action(user=user, request=request, module="stock", action="UPDATE",
               objet=f"matiere:{r['matiere_id']}:variante:{variante_id}",
               detail=", ".join(sorted(body))[:200])
    return out


@router.post("/api/stock/variantes/{variante_id}/principal")
def principal_variante(variante_id: int, request: Request):
    user = require_stock_matieres_admin(request)
    with get_db() as conn:
        try:
            res = mv.definir_principal(conn, variante_id, user_id=user.get("id"), user_name=_auteur(user))
        except (LookupError, ValueError) as e:
            _erreur(e)
        conn.commit()
        mid = conn.execute("SELECT matiere_id FROM mp_variantes WHERE id=?", (variante_id,)).fetchone()[0]
        out = mv.lister(conn, mid)
    out["principal"] = res
    log_action(user=user, request=request, module="stock", action="UPDATE",
               objet=f"matiere:{mid}:variante:{variante_id}",
               detail="Fournisseur principal · prix suivis : %d · sans prix : %d"
                      % (len(res["declinaisons_suivies"]), len(res["declinaisons_sans_prix"])))
    return out


@router.post("/api/stock/variantes/{variante_id}/desactiver")
def desactiver_variante(variante_id: int, request: Request):
    user = require_stock_matieres_admin(request)
    with get_db() as conn:
        try:
            r = mv.desactiver(conn, variante_id, _auteur(user))
        except (LookupError, ValueError) as e:
            _erreur(e)
        conn.commit()
        out = mv.lister(conn, r["matiere_id"])
    log_action(user=user, request=request, module="stock", action="UPDATE",
               objet=f"matiere:{r['matiere_id']}:variante:{variante_id}", detail="Variante désactivée")
    return out


@router.post("/api/stock/variantes/{variante_id}/reactiver")
def reactiver_variante(variante_id: int, request: Request):
    user = require_stock_matieres_admin(request)
    with get_db() as conn:
        try:
            r = mv.reactiver(conn, variante_id, _auteur(user))
        except (LookupError, ValueError) as e:
            _erreur(e)
        conn.commit()
        out = mv.lister(conn, r["matiere_id"], avec_inactives=True)
    log_action(user=user, request=request, module="stock", action="UPDATE",
               objet=f"matiere:{r['matiere_id']}:variante:{variante_id}", detail="Variante réactivée")
    return out
