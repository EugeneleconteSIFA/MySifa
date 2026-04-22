"""SIFA — MyStock v2.0
FIFO lots, inventaire, recherche instantanée, mobile-first.
Accès : direction, administration, logistique.
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Request, HTTPException

from database import get_db
from services.auth_service import get_current_user, user_has_app_access

router = APIRouter()

INVENTAIRE_ALERTE_JOURS = 180  # 6 mois

# Colonnes mouvements (évite m.* + collision avec join users)
_MVT_FIELDS = (
    "m.id, m.produit_id, m.emplacement, m.type_mouvement, m.quantite, "
    "m.quantite_avant, m.quantite_apres, m.note, m.created_at, m.created_by, m.created_by_name"
)

_STOCK_USER_JOIN = (
    "LEFT JOIN users u ON LOWER(TRIM(COALESCE(u.email,''))) = "
    "LOWER(TRIM(COALESCE(m.created_by,'')))"
)

# Références type XXXX-XXXX / XXXX/XXXX : même résultat si l’utilisateur omet ou change -, /, espaces.
_NORM_REF_SQL = (
    "REPLACE(REPLACE(REPLACE(UPPER(TRIM(p.reference)), '-', ''), '/', ''), ' ', '')"
)
_NORM_DES_SQL = (
    "REPLACE(REPLACE(REPLACE(UPPER(IFNULL(p.designation,'')), '-', ''), '/', ''), ' ', '')"
)


def _produit_search_where_args(q: str) -> tuple[str, list]:
    """Clause WHERE + paramètres : concordance sur la chaîne tapée et sur la forme sans séparateurs."""
    q = (q or "").strip()
    pattern = f"%{q}%"
    if not q:
        return "(p.reference LIKE ? OR IFNULL(p.designation,'') LIKE ?)", [pattern, pattern]
    core = "".join(c for c in q.upper() if c not in "-/ ")
    if core:
        norm_pat = f"%{core}%"
        where = (
            f"({_NORM_REF_SQL} LIKE ? OR p.reference LIKE ? OR "
            f"{_NORM_DES_SQL} LIKE ? OR IFNULL(p.designation,'') LIKE ?)"
        )
        return where, [norm_pat, pattern, norm_pat, pattern]
    return "(p.reference LIKE ? OR IFNULL(p.designation,'') LIKE ?)", [pattern, pattern]


def require_stock(request: Request) -> dict:
    user = get_current_user(request)
    if not user_has_app_access(user, "stock"):
        raise HTTPException(403, "Accès réservé à la Direction, Administration et Logistique")
    return user


def require_stock_write(request: Request) -> dict:
    user = require_stock(request)
    if user.get("role") == "commercial":
        raise HTTPException(403, "Accès en lecture seule pour le rôle commercial")
    return user


# ── Helpers FIFO ──────────────────────────────────────────────────
def get_stock_produit_total(conn, produit_id: int) -> dict:
    """Quantité totale + date FIFO (lot le plus ancien avec restant > 0)."""
    rows = conn.execute(
        """SELECT quantite_restante, date_entree, emplacement
           FROM lots_stock
           WHERE produit_id=? AND quantite_restante > 0
           ORDER BY date_entree ASC""",
        (produit_id,),
    ).fetchall()
    total = sum(r["quantite_restante"] for r in rows)
    date_fifo = rows[0]["date_entree"] if rows else None
    return {"total": total, "date_fifo": date_fifo, "nb_lots": len(rows)}


def apply_fifo_sortie(
    conn,
    produit_id: int,
    emplacement: str,
    quantite: float,
    user_email: str,
    user_name: Optional[str] = None,
    note: str = "",
) -> dict:
    """
    Consomme les lots FIFO pour un emplacement donné.
    Retourne quantite_avant, quantite_apres.
    """
    lots = conn.execute(
        """SELECT id, quantite_restante, date_entree
           FROM lots_stock
           WHERE produit_id=? AND emplacement=? AND quantite_restante > 0
           ORDER BY date_entree ASC""",
        (produit_id, emplacement),
    ).fetchall()

    total_dispo = sum(l["quantite_restante"] for l in lots)
    if quantite > total_dispo:
        raise HTTPException(400, f"Stock insuffisant sur {emplacement} : {total_dispo} disponibles")

    quantite_avant = total_dispo
    restant = quantite
    now = datetime.now().isoformat()

    for lot in lots:
        if restant <= 0:
            break
        consomme = min(lot["quantite_restante"], restant)
        nouvelle_qte = lot["quantite_restante"] - consomme
        conn.execute(
            "UPDATE lots_stock SET quantite_restante=? WHERE id=?",
            (nouvelle_qte, lot["id"]),
        )
        restant -= consomme

    quantite_apres = total_dispo - quantite

    # Mettre à jour stock_emplacements (vue agrégée)
    conn.execute(
        """UPDATE stock_emplacements
           SET quantite=?, updated_at=?, updated_by=?, commentaire=?
           WHERE produit_id=? AND emplacement=?""",
        (quantite_apres, now, user_email, note or None, produit_id, emplacement),
    )

    # Historique
    conn.execute(
        """INSERT INTO mouvements_stock
           (produit_id,emplacement,type_mouvement,quantite,quantite_avant,quantite_apres,note,created_at,created_by,created_by_name)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (produit_id, emplacement, "sortie", quantite, quantite_avant, quantite_apres, note, now, user_email, user_name),
    )
    return {"quantite_avant": quantite_avant, "quantite_apres": quantite_apres}


# ── Recherche instantanée ─────────────────────────────────────────
@router.get("/api/stock/search")
def search(request: Request, q: str = "", limit: int = 12):
    """Recherche unifiée : produits + emplacements. 'text contains'."""
    require_stock(request)
    q = q.strip()
    if not q:
        return {"produits": [], "emplacements": []}

    pattern = f"%{q}%"
    prod_where, prod_params = _produit_search_where_args(q)
    with get_db() as conn:
        produits = conn.execute(
            f"""SELECT p.id, p.reference, p.designation, p.unite,
                      COALESCE(SUM(l.quantite_restante),0) as stock_total,
                      MIN(CASE WHEN l.quantite_restante>0 THEN l.date_entree END) as date_fifo
               FROM produits p
               LEFT JOIN lots_stock l ON l.produit_id=p.id
               WHERE {prod_where}
               GROUP BY p.id
               ORDER BY p.reference
               LIMIT ?""",
            (*prod_params, limit),
        ).fetchall()

        # Emplacements : stock réel + référentiel plan (grille A/B/… + numéro)
        empls = conn.execute(
            """SELECT DISTINCT s.emplacement,
                      COUNT(DISTINCT s.produit_id) as nb_refs,
                      COALESCE(SUM(s.quantite),0) as total_unites,
                      s.derniere_inventaire
               FROM stock_emplacements s
               WHERE s.emplacement LIKE ? AND s.quantite > 0
               GROUP BY s.emplacement
               ORDER BY s.emplacement
               LIMIT ?""",
            (pattern, limit),
        ).fetchall()

        plan_empl = conn.execute(
            """SELECT code as emplacement,
                      0 as nb_refs,
                      0 as total_unites,
                      NULL as derniere_inventaire
               FROM emplacements_plan
               WHERE code LIKE ?
               ORDER BY code
               LIMIT ?""",
            (pattern, limit * 2),
        ).fetchall()

    by_code = {r["emplacement"]: dict(r) for r in empls}
    for r in plan_empl:
        d = dict(r)
        code = d["emplacement"]
        if code not in by_code:
            by_code[code] = d
    merged_empl = sorted(by_code.values(), key=lambda x: x["emplacement"])[:limit]

    return {
        "produits": [dict(r) for r in produits],
        "emplacements": merged_empl,
    }


# ── Vue tableau de bord (grille) ──────────────────────────────────
@router.get("/api/stock/vue-globale")
def vue_globale(request: Request):
    """Données du tableau de bord MyStock : une ligne par (emplacement × produit) avec lots actifs."""
    require_stock(request)
    with get_db() as conn:
        grille_rows = conn.execute(
            """SELECT l.emplacement, p.id AS id, p.reference, p.designation, p.unite,
                      SUM(l.quantite_restante) AS quantite
               FROM lots_stock l
               JOIN produits p ON p.id = l.produit_id
               WHERE l.quantite_restante > 0
               GROUP BY l.emplacement, p.id, p.reference, p.designation, p.unite
               ORDER BY l.emplacement, p.reference"""
        ).fetchall()
        stats_row = conn.execute(
            """SELECT
               COUNT(DISTINCT p.id) AS nb_refs,
               COUNT(DISTINCT CASE WHEN s.quantite > 0 THEN s.emplacement END) AS nb_empl,
               COALESCE(SUM(s.quantite), 0) AS total_unites
               FROM produits p
               LEFT JOIN stock_emplacements s ON s.produit_id = p.id"""
        ).fetchone()
        mvts = conn.execute(
            f"""SELECT {_MVT_FIELDS}, p.reference, p.designation, p.unite,
                      COALESCE(NULLIF(TRIM(m.created_by_name),''), u.nom) AS created_by_nom
               FROM mouvements_stock m
               JOIN produits p ON p.id = m.produit_id
               {_STOCK_USER_JOIN}
               ORDER BY m.created_at DESC LIMIT 15"""
        ).fetchall()
    return {
        "grille": [dict(r) for r in grille_rows],
        "stats": dict(stats_row) if stats_row else {},
        "derniers_mouvements": [dict(r) for r in mvts],
    }


# ── Produits CRUD ─────────────────────────────────────────────────
@router.get("/api/stock/produits")
def list_produits(request: Request, q: Optional[str] = None, limit: int = 50):
    require_stock(request)
    qs = (q or "").strip()
    if qs:
        prod_where, prod_params = _produit_search_where_args(qs)
    else:
        prod_where = "(p.reference LIKE ? OR IFNULL(p.designation,'') LIKE ?)"
        prod_params = ["%", "%"]
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT p.id, p.reference, p.designation, p.unite, p.description,
                      COALESCE(SUM(l.quantite_restante),0) as stock_total,
                      MIN(CASE WHEN l.quantite_restante>0 THEN l.date_entree END) as date_fifo,
                      COUNT(DISTINCT CASE WHEN l.quantite_restante>0 THEN l.emplacement END) as nb_emplacements
               FROM produits p
               LEFT JOIN lots_stock l ON l.produit_id=p.id
               WHERE {prod_where}
               GROUP BY p.id ORDER BY p.reference LIMIT ?""",
            (*prod_params, limit),
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/api/stock/produits/{produit_id}")
def get_produit(produit_id: int, request: Request):
    require_stock(request)
    with get_db() as conn:
        p = conn.execute("SELECT * FROM produits WHERE id=?", (produit_id,)).fetchone()
        if not p:
            raise HTTPException(404, "Produit non trouvé")

        # Stock par emplacement avec date FIFO par emplacement
        empls = conn.execute(
            """SELECT l.emplacement,
                      SUM(l.quantite_restante) as quantite,
                      MIN(CASE WHEN l.quantite_restante>0 THEN l.date_entree END) as date_fifo_empl,
                      MAX(s.derniere_inventaire) as derniere_inventaire,
                      MAX(s.updated_at) as updated_at,
                      MAX(s.updated_by) as updated_by,
                      MAX(s.commentaire) as commentaire
               FROM lots_stock l
               LEFT JOIN stock_emplacements s ON s.produit_id=l.produit_id AND s.emplacement=l.emplacement
               WHERE l.produit_id=? AND l.quantite_restante>0
               GROUP BY l.emplacement
               ORDER BY l.emplacement""",
            (produit_id,),
        ).fetchall()

        # FIFO global
        fifo = get_stock_produit_total(conn, produit_id)

        # Historique mouvements
        mvts = conn.execute(
            f"""SELECT {_MVT_FIELDS}, p.reference, p.designation, p.unite,
                      COALESCE(NULLIF(TRIM(m.created_by_name),''), u.nom) AS created_by_nom
               FROM mouvements_stock m
               JOIN produits p ON p.id=m.produit_id
               {_STOCK_USER_JOIN}
               WHERE m.produit_id=?
               ORDER BY m.created_at DESC LIMIT 80""",
            (produit_id,),
        ).fetchall()

        # Alerte inventaire
        now = datetime.now()
        empl_data = []
        for e in empls:
            d = dict(e)
            if e["derniere_inventaire"]:
                try:
                    inv = str(e["derniere_inventaire"]).replace("Z", "")[:19]
                    delta = (now - datetime.fromisoformat(inv)).days
                    d["jours_depuis_inventaire"] = delta
                    d["alerte_inventaire"] = delta > INVENTAIRE_ALERTE_JOURS
                except Exception:
                    d["jours_depuis_inventaire"] = None
                    d["alerte_inventaire"] = True
            else:
                d["jours_depuis_inventaire"] = None
                d["alerte_inventaire"] = True
            empl_data.append(d)

    # Durée de stock en jours
    jours_stock = None
    if fifo["date_fifo"]:
        try:
            jours_stock = (datetime.now() - datetime.fromisoformat(fifo["date_fifo"][:19])).days
        except Exception:
            pass

    return {
        "produit": dict(p),
        "stock_total": fifo["total"],
        "date_fifo": fifo["date_fifo"],
        "jours_stock": jours_stock,
        "nb_lots": fifo["nb_lots"],
        "emplacements": empl_data,
        "mouvements": [dict(r) for r in mvts],
    }


@router.get("/api/stock/produits/{produit_id}/emplacements")
def get_produit_emplacements_compat(produit_id: int, request: Request):
    """Alias historique : l’app chargeait cette URL par erreur."""
    return get_produit(produit_id, request)


@router.post("/api/stock/produits")
async def create_produit(request: Request):
    user = require_stock_write(request)
    body = await request.json()
    ref = (body.get("reference") or "").strip().upper()
    if not ref:
        raise HTTPException(400, "Référence obligatoire")
    commentaire = (body.get("commentaire") or "").strip()
    des = (body.get("designation") or "").strip()
    if not des:
        des = commentaire if commentaire else ref
    q = body.get("quantite")
    description = ""
    if q is not None and str(q).strip() != "":
        description = f"Quantité: {str(q).strip()}"
    # Par défaut, l'unité de vente est "étiquette" (singulier ; le pluriel est géré côté frontend).
    unite = (body.get("unite") or "étiquette").strip() or "étiquette"
    now = datetime.now().isoformat()
    with get_db() as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO produits (reference,designation,description,unite,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                (ref, des, description, unite, now, now),
            )
            conn.commit()
            return {"success": True, "id": cursor.lastrowid, "existing": False}
        except sqlite3.IntegrityError:
            conn.rollback()
            row = conn.execute("SELECT id FROM produits WHERE reference=?", (ref,)).fetchone()
            if row:
                return {"success": True, "id": row["id"], "existing": True}
            raise HTTPException(409, "Conflit en base pour cette référence")


@router.put("/api/stock/produits/{produit_id}")
async def update_produit(produit_id: int, request: Request):
    require_stock_write(request)
    body = await request.json()
    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE produits SET designation=?,description=?,unite=?,updated_at=? WHERE id=?",
            (body.get("designation"), body.get("description"), body.get("unite"), now, produit_id),
        )
        conn.commit()
    return {"success": True}


@router.delete("/api/stock/produits/{produit_id}")
def delete_produit(produit_id: int, request: Request):
    require_stock_write(request)
    with get_db() as conn:
        conn.execute("DELETE FROM lots_stock WHERE produit_id=?", (produit_id,))
        conn.execute("DELETE FROM stock_emplacements WHERE produit_id=?", (produit_id,))
        conn.execute("DELETE FROM mouvements_stock WHERE produit_id=?", (produit_id,))
        conn.execute("DELETE FROM produits WHERE id=?", (produit_id,))
        conn.commit()
    return {"success": True}


# ── Emplacements ──────────────────────────────────────────────────
@router.get("/api/stock/emplacements/{emplacement}")
def get_emplacement(emplacement: str, request: Request):
    require_stock(request)
    emplacement = emplacement.upper()
    now = datetime.now()
    with get_db() as conn:
        refs = conn.execute(
            """SELECT p.id, p.reference, p.designation, p.unite,
                      SUM(l.quantite_restante) as quantite,
                      MIN(CASE WHEN l.quantite_restante>0 THEN l.date_entree END) as date_fifo,
                      MAX(s.derniere_inventaire) as derniere_inventaire,
                      MAX(s.updated_at) as updated_at,
                      MAX(s.updated_by) as updated_by
               FROM lots_stock l
               JOIN produits p ON p.id=l.produit_id
               LEFT JOIN stock_emplacements s ON s.produit_id=l.produit_id AND s.emplacement=l.emplacement
               WHERE l.emplacement=? AND l.quantite_restante>0
               GROUP BY l.produit_id
               ORDER BY p.reference""",
            (emplacement,),
        ).fetchall()

        mvts = conn.execute(
            f"""SELECT {_MVT_FIELDS}, p.reference, p.designation, p.unite,
                      COALESCE(NULLIF(TRIM(m.created_by_name),''), u.nom) AS created_by_nom
               FROM mouvements_stock m
               JOIN produits p ON p.id=m.produit_id
               {_STOCK_USER_JOIN}
               WHERE m.emplacement=? ORDER BY m.created_at DESC LIMIT 80""",
            (emplacement,),
        ).fetchall()

    refs_data = []
    for r in refs:
        d = dict(r)
        try:
            delta = (now - datetime.fromisoformat(d["date_fifo"][:19])).days if d["date_fifo"] else None
            d["jours_stock"] = delta
        except Exception:
            d["jours_stock"] = None
        if d["derniere_inventaire"]:
            try:
                inv = str(d["derniere_inventaire"]).replace("Z", "")[:19]
                d["alerte_inventaire"] = (
                    now - datetime.fromisoformat(inv)
                ).days > INVENTAIRE_ALERTE_JOURS
            except Exception:
                d["alerte_inventaire"] = True
        else:
            d["alerte_inventaire"] = True
        refs_data.append(d)

    return {
        "emplacement": emplacement,
        "refs": refs_data,
        "total_unites": sum(r["quantite"] for r in refs),
        "nb_refs": len(refs),
        "mouvements": [dict(r) for r in mvts],
    }


# ── Mouvement de stock ────────────────────────────────────────────
@router.post("/api/stock/mouvement")
async def mouvement_stock(request: Request):
    user = require_stock_write(request)
    body = await request.json()

    produit_id = body.get("produit_id")
    emplacement = (body.get("emplacement") or "").strip().upper()
    type_mvt = body.get("type_mouvement", "entree")
    quantite = float(body.get("quantite", 0))
    note = (body.get("note") or "").strip()
    date_entree = (body.get("date_entree") or datetime.now().strftime("%Y-%m-%d"))

    if not produit_id or not emplacement:
        raise HTTPException(400, "produit_id et emplacement obligatoires")
    if not emplacement[0].isalpha() or not emplacement[1:].isdigit():
        raise HTTPException(400, f"Format emplacement invalide : {emplacement}")
    if quantite <= 0:
        raise HTTPException(400, "Quantité doit être positive")

    now = datetime.now().isoformat()
    # Toujours tracer un "Nom Prénom" fiable (champ #ed-nom → users.nom).
    # Certains contextes peuvent renvoyer un user.nom vide : on complète via la DB.
    created_by_name = (user.get("nom") or "").strip() or None

    with get_db() as conn:
        if not created_by_name:
            try:
                if user.get("id") is not None:
                    r = conn.execute("SELECT nom FROM users WHERE id=? LIMIT 1", (int(user["id"]),)).fetchone()
                else:
                    r = conn.execute(
                        "SELECT nom FROM users WHERE LOWER(TRIM(COALESCE(email,'')))=? LIMIT 1",
                        (str(user.get("email") or "").strip().lower(),),
                    ).fetchone()
                created_by_name = (str(r["nom"] or "").strip() if r else "") or None
            except Exception:
                created_by_name = None

        # Vérifier produit
        p = conn.execute("SELECT id FROM produits WHERE id=?", (produit_id,)).fetchone()
        if not p:
            raise HTTPException(404, "Produit non trouvé")

        ex = conn.execute(
            "SELECT quantite FROM stock_emplacements WHERE produit_id=? AND emplacement=?",
            (produit_id, emplacement),
        ).fetchone()
        qte_avant = ex["quantite"] if ex else 0.0

        if type_mvt == "entree":
            # Créer un nouveau lot FIFO
            conn.execute(
                """INSERT INTO lots_stock
                   (produit_id,emplacement,quantite_initiale,quantite_restante,date_entree,note,created_by,created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (produit_id, emplacement, quantite, quantite, date_entree, note, user["email"], now),
            )
            qte_apres = qte_avant + quantite

            # Upsert stock_emplacements
            if ex:
                conn.execute(
                    """UPDATE stock_emplacements
                       SET quantite=?,updated_at=?,updated_by=?,derniere_inventaire=?,commentaire=?
                       WHERE produit_id=? AND emplacement=?""",
                    (qte_apres, now, user["email"], now, note or None, produit_id, emplacement),
                )
            else:
                conn.execute(
                    """INSERT INTO stock_emplacements
                       (produit_id,emplacement,quantite,updated_at,updated_by,derniere_inventaire,commentaire)
                       VALUES (?,?,?,?,?,?,?)""",
                    (produit_id, emplacement, qte_apres, now, user["email"], now, note or None),
                )

            # Historique
            conn.execute(
                """INSERT INTO mouvements_stock
                   (produit_id,emplacement,type_mouvement,quantite,quantite_avant,quantite_apres,note,created_at,created_by,created_by_name)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (produit_id, emplacement, "entree", quantite, qte_avant, qte_apres, note, now, user["email"], created_by_name),
            )
            result = {"quantite_avant": qte_avant, "quantite_apres": qte_apres}

        elif type_mvt == "sortie":
            result = apply_fifo_sortie(conn, produit_id, emplacement, quantite, user["email"], created_by_name, note)
            qte_apres = result["quantite_apres"]

        elif type_mvt == "inventaire":
            # Annuler tous les lots existants sur cet emplacement
            conn.execute(
                "UPDATE lots_stock SET quantite_restante=0 WHERE produit_id=? AND emplacement=?",
                (produit_id, emplacement),
            )
            # Créer un nouveau lot unique avec la quantité inventoriée
            conn.execute(
                """INSERT INTO lots_stock
                   (produit_id,emplacement,quantite_initiale,quantite_restante,date_entree,note,created_by,created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (produit_id, emplacement, quantite, quantite, date_entree, f"Inventaire — {note}", user["email"], now),
            )
            # Mettre à jour stock_emplacements + date inventaire
            if ex:
                conn.execute(
                    """UPDATE stock_emplacements
                       SET quantite=?,updated_at=?,updated_by=?,derniere_inventaire=?,commentaire=?
                       WHERE produit_id=? AND emplacement=?""",
                    (quantite, now, user["email"], now, note or None, produit_id, emplacement),
                )
            else:
                conn.execute(
                    """INSERT INTO stock_emplacements
                       (produit_id,emplacement,quantite,updated_at,updated_by,derniere_inventaire,commentaire)
                       VALUES (?,?,?,?,?,?,?)""",
                    (produit_id, emplacement, quantite, now, user["email"], now, note or None),
                )
            conn.execute(
                """INSERT INTO mouvements_stock
                   (produit_id,emplacement,type_mouvement,quantite,quantite_avant,quantite_apres,note,created_at,created_by,created_by_name)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (produit_id, emplacement, "inventaire", quantite, qte_avant, quantite, note, now, user["email"], created_by_name),
            )
            result = {"quantite_avant": qte_avant, "quantite_apres": quantite}
            qte_apres = quantite

        conn.commit()

    return {"success": True, **result}


# ── Inventaire en chaîne ──────────────────────────────────────────
@router.get("/api/stock/inventaire/priorites")
def inventaire_priorites(request: Request):
    """Toutes les lignes en stock (quantite > 0), tri : jamais / le plus ancien inventaire d'abord."""
    require_stock(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT p.id AS produit_id, p.reference, p.designation, p.unite,
                      s.emplacement, s.quantite, s.derniere_inventaire,
                      CASE
                        WHEN s.derniere_inventaire IS NULL
                          OR TRIM(COALESCE(s.derniere_inventaire, '')) = ''
                          THEN 999999
                        ELSE CAST(
                          julianday('now') - julianday(SUBSTR(s.derniere_inventaire, 1, 10))
                          AS INTEGER
                        )
                      END AS jours_depuis_inv
               FROM stock_emplacements s
               JOIN produits p ON p.id = s.produit_id
               WHERE s.quantite > 0
               ORDER BY jours_depuis_inv DESC, s.quantite DESC, p.reference, s.emplacement"""
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/api/stock/inventaire/produits-a-inventorier")
def produits_a_inventorier(request: Request, jours: int = 180):
    """Produits avec emplacements non inventoriés depuis > jours."""
    require_stock(request)
    limite = (datetime.now() - timedelta(days=jours)).isoformat()
    with get_db() as conn:
        rows = conn.execute(
            """SELECT p.id, p.reference, p.designation, p.unite,
                      s.emplacement, s.quantite, s.derniere_inventaire,
                      COALESCE(CAST(julianday('now') - julianday(s.derniere_inventaire) AS INTEGER), 9999) as jours_depuis
               FROM stock_emplacements s
               JOIN produits p ON p.id=s.produit_id
               WHERE s.quantite > 0
                 AND (s.derniere_inventaire IS NULL OR s.derniere_inventaire < ?)
               ORDER BY jours_depuis DESC, p.reference""",
            (limite,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Stats dashboard ───────────────────────────────────────────────
@router.get("/api/stock/dashboard")
def dashboard(request: Request):
    require_stock(request)
    now = datetime.now()
    limite_alerte = (now - timedelta(days=INVENTAIRE_ALERTE_JOURS)).isoformat()
    with get_db() as conn:
        stats = conn.execute(
            """SELECT
               COUNT(DISTINCT p.id) as nb_refs,
               COUNT(DISTINCT CASE WHEN s.quantite>0 THEN s.emplacement END) as nb_empl_occupes,
               COALESCE(SUM(s.quantite),0) as total_unites,
               COUNT(DISTINCT CASE WHEN (s.derniere_inventaire IS NULL OR s.derniere_inventaire < ?) AND s.quantite>0 THEN s.produit_id END) as nb_a_inventorier
               FROM produits p
               LEFT JOIN stock_emplacements s ON s.produit_id=p.id""",
            (limite_alerte,),
        ).fetchone()

        derniers_mvts = conn.execute(
            f"""SELECT {_MVT_FIELDS}, p.reference, p.designation, p.unite,
                      COALESCE(NULLIF(TRIM(m.created_by_name),''), u.nom) AS created_by_nom
               FROM mouvements_stock m
               JOIN produits p ON p.id=m.produit_id
               {_STOCK_USER_JOIN}
               ORDER BY m.created_at DESC LIMIT 15""",
        ).fetchall()

        top_refs = conn.execute(
            """SELECT p.id, p.reference, p.designation, p.unite,
                      COALESCE(SUM(l.quantite_restante),0) as stock_total
               FROM produits p
               LEFT JOIN lots_stock l ON l.produit_id=p.id AND l.quantite_restante>0
               GROUP BY p.id ORDER BY stock_total DESC LIMIT 8""",
        ).fetchall()

    return {
        "stats": dict(stats),
        "derniers_mouvements": [dict(r) for r in derniers_mvts],
        "top_refs": [dict(r) for r in top_refs],
    }


# ─── Réception matière ─────────────────────────────────────────────────────────

@router.get("/api/stock/receptions")
def list_receptions(request: Request, limit: int = 50):
    """Historique des réceptions de bobines."""
    user = require_stock(request)
    with get_db() as conn:
        lots = conn.execute(
            """SELECT r.*, GROUP_CONCAT(i.code_barre, '||') as codes
               FROM stock_receptions r
               LEFT JOIN stock_reception_items i ON i.reception_id = r.id
               GROUP BY r.id
               ORDER BY r.created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    result = []
    for lot in lots:
        d = dict(lot)
        raw = d.pop("codes", None)
        d["items"] = raw.split("||") if raw else []
        result.append(d)
    return {"receptions": result}


@router.post("/api/stock/receptions")
async def create_reception(request: Request):
    """Enregistre une réception de bobines (lot de codes-barres)."""
    user = require_stock(request)
    body = await request.json()
    codes = [str(c).strip() for c in (body.get("codes") or []) if str(c).strip()]
    if not codes:
        raise HTTPException(status_code=400, detail="Aucun code-barres fourni")
    note = (body.get("note") or "").strip() or None
    fournisseur = (body.get("fournisseur") or "").strip() or None
    certificat_fsc = (body.get("certificat_fsc") or "").strip() or None
    now = datetime.now().isoformat()

    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO stock_receptions (created_at, created_by, created_by_name, note, nb_bobines, fournisseur, certificat_fsc)
               VALUES (?,?,?,?,?,?,?)""",
            (now, user.get("email"), user.get("nom"), note, len(codes), fournisseur, certificat_fsc),
        )
        reception_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO stock_reception_items (reception_id, code_barre, scanned_at) VALUES (?,?,?)",
            [(reception_id, code, now) for code in codes],
        )
        conn.commit()

    return {"success": True, "id": reception_id, "nb_bobines": len(codes)}
