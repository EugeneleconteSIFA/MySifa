"""
SIFA — MyStock v1.0
Gestion des stocks par référence et par emplacement.
Accès : direction, administration, logistique.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from database import get_db
from services.auth_service import get_current_user
from config import ROLES_STOCK

router = APIRouter()

EMPLACEMENTS = [
    "A121", "A122", "A123",
    "B121", "B122", "B123",
    "C121", "C122", "C123",
]


def require_stock(request: Request) -> dict:
    user = get_current_user(request)
    if user["role"] not in ROLES_STOCK:
        raise HTTPException(status_code=403,
                            detail="Accès réservé à la Direction, Administration et Logistique")
    return user


# ── Emplacements disponibles ──────────────────────────────────────
@router.get("/api/stock/emplacements")
def get_emplacements(request: Request):
    require_stock(request)
    return {"emplacements": EMPLACEMENTS}


# ── Produits ──────────────────────────────────────────────────────
@router.get("/api/stock/produits")
def list_produits(request: Request, q: Optional[str] = None):
    require_stock(request)
    with get_db() as conn:
        if q:
            rows = conn.execute(
                """SELECT p.*,
                          COALESCE(SUM(s.quantite), 0) as stock_total
                   FROM produits p
                   LEFT JOIN stock_emplacements s ON s.produit_id = p.id
                   WHERE p.reference LIKE ? OR p.designation LIKE ?
                   GROUP BY p.id ORDER BY p.reference""",
                (f"%{q}%", f"%{q}%")
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT p.*,
                          COALESCE(SUM(s.quantite), 0) as stock_total
                   FROM produits p
                   LEFT JOIN stock_emplacements s ON s.produit_id = p.id
                   GROUP BY p.id ORDER BY p.reference"""
            ).fetchall()
    return [dict(r) for r in rows]


@router.post("/api/stock/produits")
async def create_produit(request: Request):
    require_stock(request)
    body = await request.json()
    ref  = (body.get("reference") or "").strip().upper()
    des  = (body.get("designation") or "").strip()
    if not ref or not des:
        raise HTTPException(status_code=400, detail="Référence et désignation obligatoires")
    now = datetime.now().isoformat()
    with get_db() as conn:
        try:
            cursor = conn.execute(
                """INSERT INTO produits (reference, designation, description, unite, created_at, updated_at)
                   VALUES (?,?,?,?,?,?)""",
                (ref, des, body.get("description",""), body.get("unite","unité"), now, now)
            )
            conn.commit()
        except Exception:
            raise HTTPException(status_code=409, detail="Référence déjà existante")
    return {"success": True, "id": cursor.lastrowid}


@router.put("/api/stock/produits/{produit_id}")
async def update_produit(produit_id: int, request: Request):
    require_stock(request)
    body = await request.json()
    now  = datetime.now().isoformat()
    with get_db() as conn:
        ex = conn.execute("SELECT * FROM produits WHERE id=?", (produit_id,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Produit non trouvé")
        conn.execute(
            "UPDATE produits SET designation=?,description=?,unite=?,updated_at=? WHERE id=?",
            (body.get("designation", ex["designation"]),
             body.get("description", ex["description"]),
             body.get("unite", ex["unite"]),
             now, produit_id)
        )
        conn.commit()
    return {"success": True}


@router.delete("/api/stock/produits/{produit_id}")
def delete_produit(produit_id: int, request: Request):
    require_stock(request)
    with get_db() as conn:
        conn.execute("DELETE FROM stock_emplacements WHERE produit_id=?", (produit_id,))
        conn.execute("DELETE FROM mouvements_stock WHERE produit_id=?", (produit_id,))
        conn.execute("DELETE FROM produits WHERE id=?", (produit_id,))
        conn.commit()
    return {"success": True}


# ── Stock par produit ─────────────────────────────────────────────
@router.get("/api/stock/produits/{produit_id}/emplacements")
def get_stock_produit(produit_id: int, request: Request):
    """Tous les emplacements où ce produit est stocké + quantités."""
    require_stock(request)
    with get_db() as conn:
        produit = conn.execute("SELECT * FROM produits WHERE id=?", (produit_id,)).fetchone()
        if not produit:
            raise HTTPException(status_code=404, detail="Produit non trouvé")
        rows = conn.execute(
            """SELECT emplacement, quantite, updated_at, updated_by
               FROM stock_emplacements WHERE produit_id=? AND quantite > 0
               ORDER BY emplacement""",
            (produit_id,)
        ).fetchall()
        total = conn.execute(
            "SELECT COALESCE(SUM(quantite),0) as t FROM stock_emplacements WHERE produit_id=?",
            (produit_id,)
        ).fetchone()["t"]
    return {
        "produit": dict(produit),
        "emplacements": [dict(r) for r in rows],
        "stock_total": total,
    }


# ── Stock par emplacement ─────────────────────────────────────────
@router.get("/api/stock/emplacements/{emplacement}")
def get_stock_emplacement(emplacement: str, request: Request):
    """Tous les produits dans un emplacement + quantités."""
    require_stock(request)
    emplacement = emplacement.upper()
    if emplacement not in EMPLACEMENTS:
        raise HTTPException(status_code=404, detail=f"Emplacement {emplacement} inconnu")
    with get_db() as conn:
        rows = conn.execute(
            """SELECT p.id, p.reference, p.designation, p.unite,
                      s.quantite, s.updated_at, s.updated_by
               FROM stock_emplacements s
               JOIN produits p ON p.id = s.produit_id
               WHERE s.emplacement=? AND s.quantite > 0
               ORDER BY p.reference""",
            (emplacement,)
        ).fetchall()
    return {"emplacement": emplacement, "produits": [dict(r) for r in rows]}


# ── Mouvement de stock ────────────────────────────────────────────
@router.post("/api/stock/mouvement")
async def mouvement_stock(request: Request):
    """
    Entrée, sortie ou transfert de stock.
    type_mouvement : 'entree' | 'sortie' | 'transfert' | 'inventaire'
    """
    user = require_stock(request)
    body = await request.json()

    produit_id     = body.get("produit_id")
    emplacement    = (body.get("emplacement") or "").upper()
    type_mvt       = body.get("type_mouvement", "entree")
    quantite       = float(body.get("quantite", 0))
    note           = body.get("note", "")

    if not produit_id or not emplacement:
        raise HTTPException(status_code=400, detail="produit_id et emplacement obligatoires")
    if emplacement not in EMPLACEMENTS:
        raise HTTPException(status_code=400, detail=f"Emplacement {emplacement} inconnu")
    if quantite <= 0:
        raise HTTPException(status_code=400, detail="La quantité doit être positive")

    now = datetime.now().isoformat()

    with get_db() as conn:
        # Stock actuel
        ex = conn.execute(
            "SELECT quantite FROM stock_emplacements WHERE produit_id=? AND emplacement=?",
            (produit_id, emplacement)
        ).fetchone()
        qte_avant = ex["quantite"] if ex else 0.0

        # Calcul nouvelle quantité
        if type_mvt == "entree":
            qte_apres = qte_avant + quantite
        elif type_mvt == "sortie":
            qte_apres = max(0, qte_avant - quantite)
        elif type_mvt == "inventaire":
            qte_apres = quantite  # écrasement
        else:
            qte_apres = qte_avant + quantite

        # Upsert stock_emplacements
        if ex:
            conn.execute(
                "UPDATE stock_emplacements SET quantite=?,updated_at=?,updated_by=? WHERE produit_id=? AND emplacement=?",
                (qte_apres, now, user["email"], produit_id, emplacement)
            )
        else:
            conn.execute(
                "INSERT INTO stock_emplacements (produit_id,emplacement,quantite,updated_at,updated_by) VALUES (?,?,?,?,?)",
                (produit_id, emplacement, qte_apres, now, user["email"])
            )

        # Historique
        conn.execute(
            """INSERT INTO mouvements_stock
               (produit_id,emplacement,type_mouvement,quantite,quantite_avant,quantite_apres,note,created_at,created_by)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (produit_id, emplacement, type_mvt, quantite,
             qte_avant, qte_apres, note, now, user["email"])
        )
        conn.commit()

    return {
        "success": True,
        "quantite_avant": qte_avant,
        "quantite_apres": qte_apres,
    }


# ── Vue globale du stock ──────────────────────────────────────────
@router.get("/api/stock/vue-globale")
def vue_globale(request: Request):
    """Tous les emplacements avec leurs produits — vue tableau de bord."""
    require_stock(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT s.emplacement, p.reference, p.designation, p.unite,
                      s.quantite, s.updated_at
               FROM stock_emplacements s
               JOIN produits p ON p.id = s.produit_id
               WHERE s.quantite > 0
               ORDER BY s.emplacement, p.reference"""
        ).fetchall()
        stats = conn.execute(
            """SELECT COUNT(DISTINCT produit_id) as nb_refs,
                      COUNT(DISTINCT emplacement) as nb_empl,
                      COALESCE(SUM(quantite),0) as total_unites
               FROM stock_emplacements WHERE quantite > 0"""
        ).fetchone()
        mouvements = conn.execute(
            """SELECT m.*, p.reference, p.designation
               FROM mouvements_stock m
               JOIN produits p ON p.id = m.produit_id
               ORDER BY m.created_at DESC LIMIT 10"""
        ).fetchall()
    return {
        "grille": [dict(r) for r in rows],
        "stats":  dict(stats),
        "derniers_mouvements": [dict(r) for r in mouvements],
    }


# ── Historique mouvements d'un produit ───────────────────────────
@router.get("/api/stock/produits/{produit_id}/historique")
def historique_produit(produit_id: int, request: Request):
    require_stock(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM mouvements_stock WHERE produit_id=?
               ORDER BY created_at DESC LIMIT 50""",
            (produit_id,)
        ).fetchall()
    return [dict(r) for r in rows]
