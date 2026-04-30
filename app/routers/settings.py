"""Paramètres & matrice d'accès — super administrateur uniquement."""

from datetime import datetime
from fastapi import APIRouter, Request, HTTPException

from config import (
    ASSIGNABLE_ROLES,
    ROLE_SUPERADMIN,
    ROLE_FABRICATION,
    ROLE_ADMINISTRATION,
    ROLE_DIRECTION,
    ROLE_LOGISTIQUE,
    ROLE_COMPTABILITE,
    ROLE_EXPEDITION,
    ROLE_COMMERCIAL,
    SUPERADMIN_EMAIL,
    default_app_access_for_role,
)
from services.auth_service import require_superadmin, merged_app_access, parse_access_overrides_raw

router = APIRouter(tags=["settings"])


@router.get("/api/settings/access-matrix")
def access_matrix(request: Request):
    require_superadmin(request)
    from database import get_db

    apps = [
        {
            "id": "prod",
            "label": "MyProd",
            "hint": "Suivi de production (hors planning autonome)",
        },
        {
            "id": "planning",
            "label": "Planning machine",
            "hint": "Planning atelier (même périmètre que MyProd pour les rôles)",
        },
        {
            "id": "planning_rh",
            "label": "Planning RH",
            "hint": "Planning personnel (affectation opérateurs)",
        },
        {
            "id": "stock",
            "label": "MyStock",
            "hint": "Stocks & emplacements",
        },
        {
            "id": "compta",
            "label": "MyCompta",
            "hint": "Interface comptabilité",
        },
        {
            "id": "expe",
            "label": "MyExpé",
            "hint": "Expédition",
        },
        {
            "id": "settings",
            "label": "Paramètres",
            "hint": "Comptes, rôles & matrice — super admin uniquement",
        },
    ]

    role_labels = {
        ROLE_DIRECTION: "Direction",
        ROLE_ADMINISTRATION: "Administration",
        ROLE_FABRICATION: "Fabrication",
        ROLE_LOGISTIQUE: "Logistique",
        ROLE_COMPTABILITE: "Comptabilité",
        ROLE_EXPEDITION: "Expédition",
        ROLE_COMMERCIAL: "Commercial",
        ROLE_SUPERADMIN: "Super admin",
    }

    with get_db() as conn:
        rows = conn.execute(
            """SELECT u.id,u.email,u.nom,u.role,u.actif,u.last_login,u.access_overrides
               FROM users u
               ORDER BY u.actif DESC, u.role DESC, u.nom ASC"""
        ).fetchall()

    defaults = []
    for r in (*ASSIGNABLE_ROLES, ROLE_SUPERADMIN):
        defaults.append(
            {
                "role": r,
                "label": role_labels.get(r, r),
                "access": default_app_access_for_role(r),
            }
        )

    matrix = []
    for row in rows:
        d = dict(row)
        role = d["role"]
        om = d.get("access_overrides")
        matrix.append(
            {
                "id": d["id"],
                "email": d["email"],
                "nom": d["nom"],
                "role": role,
                "role_label": role_labels.get(role, role),
                "actif": d["actif"],
                "last_login": d.get("last_login"),
                "access_default": default_app_access_for_role(role),
                "access_overrides": parse_access_overrides_raw(om),
                "access": merged_app_access(role, om),
            }
        )

    return {
        "apps": apps,
        "assignable_roles": sorted(ASSIGNABLE_ROLES | {ROLE_SUPERADMIN}),
        "role_labels": role_labels,
        "superadmin_email": SUPERADMIN_EMAIL,
        "matrix": matrix,
        "role_defaults": defaults,
    }


# ─── Fournisseurs FSC ──────────────────────────────────────────────

@router.get("/api/fournisseurs")
def list_fournisseurs(request: Request):
    require_superadmin(request)
    from database import get_db
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, nom, licence, certificat FROM fournisseurs_fsc ORDER BY nom COLLATE NOCASE ASC"
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/api/fournisseurs")
async def create_fournisseur(request: Request):
    require_superadmin(request)
    from database import get_db
    body = await request.json()
    nom = (body.get("nom") or "").strip()
    licence = (body.get("licence") or "").strip() or None
    certificat = (body.get("certificat") or "").strip() or None
    if not nom:
        raise HTTPException(status_code=400, detail="Nom du fournisseur requis")
    with get_db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO fournisseurs_fsc (nom, licence, certificat) VALUES (?,?,?)",
                (nom, licence, certificat),
            )
            conn.commit()
            return {"success": True, "id": cur.lastrowid}
        except Exception:
            raise HTTPException(status_code=409, detail="Ce fournisseur existe déjà")


@router.put("/api/fournisseurs/{fournisseur_id}")
async def update_fournisseur(fournisseur_id: int, request: Request):
    require_superadmin(request)
    from database import get_db
    body = await request.json()
    with get_db() as conn:
        ex = conn.execute("SELECT * FROM fournisseurs_fsc WHERE id=?", (fournisseur_id,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
        nom = (body.get("nom") or ex["nom"]).strip()
        licence = body.get("licence") if "licence" in body else ex["licence"]
        certificat = body.get("certificat") if "certificat" in body else ex["certificat"]
        if isinstance(licence, str): licence = licence.strip() or None
        if isinstance(certificat, str): certificat = certificat.strip() or None
        if not nom:
            raise HTTPException(status_code=400, detail="Nom du fournisseur requis")
        try:
            conn.execute(
                "UPDATE fournisseurs_fsc SET nom=?, licence=?, certificat=? WHERE id=?",
                (nom, licence, certificat, fournisseur_id),
            )
            conn.commit()
            return {"success": True}
        except Exception:
            raise HTTPException(status_code=409, detail="Ce nom de fournisseur existe déjà")


@router.delete("/api/fournisseurs/{fournisseur_id}")
async def delete_fournisseur(fournisseur_id: int, request: Request):
    require_superadmin(request)
    from database import get_db
    with get_db() as conn:
        ex = conn.execute("SELECT * FROM fournisseurs_fsc WHERE id=?", (fournisseur_id,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
        conn.execute("DELETE FROM fournisseurs_fsc WHERE id=?", (fournisseur_id,))
        conn.commit()
        return {"success": True}


@router.get("/api/fournisseurs/{fournisseur_id}/receptions")
def fournisseur_receptions(fournisseur_id: int, request: Request):
    """Historique des réceptions pour un fournisseur donné."""
    require_superadmin(request)
    from database import get_db
    with get_db() as conn:
        four = conn.execute("SELECT nom FROM fournisseurs_fsc WHERE id=?", (fournisseur_id,)).fetchone()
        if not four:
            raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
        rows = conn.execute(
            """SELECT r.id, r.created_at, r.created_by_name, r.nb_bobines, r.certificat_fsc, r.note,
                      GROUP_CONCAT(i.code_barre, '||') as codes
               FROM stock_receptions r
               LEFT JOIN stock_reception_items i ON i.reception_id = r.id
               WHERE r.fournisseur = ?
               GROUP BY r.id
               ORDER BY r.created_at DESC LIMIT 50""",
            (four["nom"],),
        ).fetchall()
    result = []
    for d in rows:
        raw = d.pop("codes", None)
        d = dict(d)
        d["items"] = raw.split("||") if raw else []
        result.append(d)
    return {"fournisseur": four["nom"], "receptions": result}


# ─── Annonces de mise à jour ──────────────────────────────────────────────────

@router.get("/api/updates/pending")
def pending_updates(request: Request, scope: str = None):
    """Annonces non acquittées pour l'utilisateur courant (toutes pages)."""
    from database import get_db
    from services.auth_service import get_current_user
    user = get_current_user(request)
    uid = user.get("id")
    with get_db() as conn:
        if scope:
            rows = conn.execute(
                """SELECT a.* FROM update_announcements a
                   WHERE a.active=1 AND a.scope=?
                     AND NOT EXISTS (
                         SELECT 1 FROM update_acknowledgements ack
                         WHERE ack.announcement_id=a.id AND ack.user_id=?
                     )
                   ORDER BY a.created_at DESC""",
                (scope, uid),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT a.* FROM update_announcements a
                   WHERE a.active=1
                     AND NOT EXISTS (
                         SELECT 1 FROM update_acknowledgements ack
                         WHERE ack.announcement_id=a.id AND ack.user_id=?
                     )
                   ORDER BY a.created_at DESC""",
                (uid,),
            ).fetchall()
    return [dict(r) for r in rows]


@router.post("/api/updates/{announcement_id}/acknowledge")
async def acknowledge_update(announcement_id: int, request: Request):
    """Marque une annonce comme lue par l'utilisateur courant."""
    from database import get_db
    from services.auth_service import get_current_user
    user = get_current_user(request)
    uid = user.get("id")
    nom = user.get("nom") or user.get("email") or ""
    with get_db() as conn:
        ann = conn.execute(
            "SELECT id FROM update_announcements WHERE id=?", (announcement_id,)
        ).fetchone()
        if not ann:
            raise HTTPException(status_code=404, detail="Annonce non trouvée")
        conn.execute(
            """INSERT OR IGNORE INTO update_acknowledgements
               (announcement_id, user_id, user_nom, acknowledged_at) VALUES (?,?,?,?)""",
            (announcement_id, uid, nom, datetime.now().isoformat()),
        )
        conn.commit()
    return {"success": True}


@router.get("/api/updates")
def list_updates(request: Request):
    """Liste toutes les annonces avec compteur d'acquittements (super admin)."""
    require_superadmin(request)
    from database import get_db
    with get_db() as conn:
        rows = conn.execute(
            """SELECT a.*, COUNT(ack.id) AS nb_ack
               FROM update_announcements a
               LEFT JOIN update_acknowledgements ack ON ack.announcement_id=a.id
               GROUP BY a.id
               ORDER BY a.created_at DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/api/updates/{announcement_id}/acknowledgements")
def list_acknowledgements(announcement_id: int, request: Request):
    """Détail des acquittements pour une annonce (super admin)."""
    require_superadmin(request)
    from database import get_db
    with get_db() as conn:
        ann = conn.execute(
            "SELECT * FROM update_announcements WHERE id=?", (announcement_id,)
        ).fetchone()
        if not ann:
            raise HTTPException(status_code=404, detail="Annonce non trouvée")
        acks = conn.execute(
            """SELECT ack.user_nom, ack.acknowledged_at, u.email
               FROM update_acknowledgements ack
               LEFT JOIN users u ON u.id=ack.user_id
               WHERE ack.announcement_id=?
               ORDER BY ack.acknowledged_at DESC""",
            (announcement_id,),
        ).fetchall()
    return {"announcement": dict(ann), "acknowledgements": [dict(a) for a in acks]}


@router.post("/api/updates")
async def create_update(request: Request):
    """Créer une nouvelle annonce (super admin)."""
    user = require_superadmin(request)
    from database import get_db
    body = await request.json()
    scope   = (body.get("scope")   or "").strip()
    titre   = (body.get("titre")   or "").strip()
    message = (body.get("message") or "").strip()
    active  = int(bool(body.get("active", True)))
    if not scope or not titre or not message:
        raise HTTPException(status_code=400, detail="scope, titre et message sont requis")
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO update_announcements (scope,titre,message,created_at,created_by,active)
               VALUES (?,?,?,?,?,?)""",
            (scope, titre, message, datetime.now().isoformat(),
             user.get("nom") or user.get("email"), active),
        )
        conn.commit()
    return {"success": True, "id": cur.lastrowid}


@router.patch("/api/updates/{announcement_id}")
async def patch_update(announcement_id: int, request: Request):
    """Modifier une annonce — ex: activer/désactiver (super admin)."""
    require_superadmin(request)
    from database import get_db
    body = await request.json()
    with get_db() as conn:
        ann = conn.execute(
            "SELECT id FROM update_announcements WHERE id=?", (announcement_id,)
        ).fetchone()
        if not ann:
            raise HTTPException(status_code=404, detail="Annonce non trouvée")
        if "active" in body:
            conn.execute(
                "UPDATE update_announcements SET active=? WHERE id=?",
                (int(bool(body["active"])), announcement_id),
            )
        if "titre" in body:
            conn.execute(
                "UPDATE update_announcements SET titre=? WHERE id=?",
                ((body["titre"] or "").strip(), announcement_id),
            )
        if "message" in body:
            conn.execute(
                "UPDATE update_announcements SET message=? WHERE id=?",
                ((body["message"] or "").strip(), announcement_id),
            )
        conn.commit()
    return {"success": True}

@router.delete("/api/updates/{announcement_id}")
def delete_update(announcement_id: int, request: Request):
    """Supprimer une annonce (uniquement si elle n'a pas encore été lue)."""
    require_superadmin(request)
    from database import get_db
    with get_db() as conn:
        ann = conn.execute(
            "SELECT * FROM update_announcements WHERE id=?", (announcement_id,)
        ).fetchone()
        if not ann:
            raise HTTPException(status_code=404, detail="Annonce non trouvée")
        # Vérifier si l'annonce a déjà été lue
        ack_count = conn.execute(
            "SELECT COUNT(*) FROM update_acknowledgements WHERE announcement_id=?",
            (announcement_id,)
        ).fetchone()[0]
        if ack_count > 0:
            raise HTTPException(status_code=400, detail="Impossible de supprimer une annonce déjà lue")
        conn.execute("DELETE FROM update_announcements WHERE id=?", (announcement_id,))
        conn.commit()
    return {"success": True}
