"""Paramètres & matrice d'accès — super administrateur uniquement."""

import hashlib
import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from config import (
    ASSIGNABLE_ROLES,
    BASE_DIR,
    ROLE_SUPERADMIN,
    ROLE_FABRICATION,
    ROLE_ADMINISTRATION,
    ROLE_DIRECTION,
    ROLE_LOGISTIQUE,
    ROLE_COMPTABILITE,
    ROLE_EXPEDITION,
    ROLE_COMMERCIAL,
    ROLES_ADMIN,
    SUPERADMIN_EMAIL,
    default_app_access_for_role,
)
from app.services.audit_service import log_action
from services.auth_service import get_current_user, require_superadmin, merged_app_access, parse_access_overrides_raw

router = APIRouter(tags=["settings"])


def _audit_created_at_display_paris(created_at: Optional[str]) -> str:
    """Affichage journal audit en heure Europe/Paris.

    Les `created_at` naïfs issus de SQLite (`strftime(...,'now','localtime')` sur un
    serveur en UTC) correspondent à une horloge UTC — on les convertit en Paris.
    """
    if not created_at:
        return "—"
    s = str(created_at).strip().replace(" ", "T")[:19]
    if len(s) < 16:
        return str(created_at).replace("T", " ")[:16]
    try:
        dt_utc = datetime.fromisoformat(s).replace(tzinfo=ZoneInfo("UTC"))
        return dt_utc.astimezone(ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return s.replace("T", " ")


def _require_traca_photo_editor(request: Request) -> dict:
    """Super admin, direction ou administration : photo / guide traça fournisseur."""
    user = get_current_user(request)
    if user.get("role") not in ROLES_ADMIN:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs.")
    return user


def _traca_file_from_url(url: str) -> Optional[Path]:
    if not url or not isinstance(url, str):
        return None
    rel = url.strip().lstrip("/")
    if rel.startswith("..") or rel.startswith("/"):
        return None
    if not rel.startswith("uploads/traca/"):
        return None
    p = (Path(BASE_DIR) / rel).resolve()
    try:
        p.relative_to((Path(BASE_DIR) / "uploads" / "traca").resolve())
    except ValueError:
        return None
    return p


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
            "id": "pricing",
            "label": "Pricing",
            "hint": "Coûts matières et fiches produits (/pricing)",
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


@router.get("/api/settings/audit")
def get_audit_logs(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    module: str = "",
    action: str = "",
    search: str = "",
):
    require_superadmin(request)
    from database import get_db

    with get_db() as conn:
        conditions = ["1=1"]
        params: list = []
        if module:
            conditions.append("module = ?")
            params.append(module)
        if action:
            conditions.append("action = ?")
            params.append(action.upper())
        if search:
            conditions.append("(objet LIKE ? OR user_nom LIKE ? OR detail LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        where = " AND ".join(conditions)
        total = conn.execute(
            f"SELECT COUNT(*) FROM audit_logs WHERE {where}", params
        ).fetchone()[0]
        rows = conn.execute(
            f"""SELECT id, user_nom, user_role, action, module, objet, detail, ip, created_at
                FROM audit_logs WHERE {where}
                ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            params + [limit, offset],
        ).fetchall()
    logs = []
    for r in rows:
        d = dict(r)
        d["created_at_display"] = _audit_created_at_display_paris(d.get("created_at"))
        logs.append(d)
    return {
        "total": total,
        "logs": logs,
    }


# ─── Registre FSC ─────────────────────────────────────────────────

_FSC_CLAIM_LABELS = {
    "fsc_100": "FSC 100%",
    "fsc_mix_credit": "FSC Mix Credit",
    "fsc_mix": "FSC Mix",
    "fsc_recycled": "FSC Recycled",
    "non_fsc": "Non FSC",
}


@router.get("/api/fsc/stats")
def get_fsc_stats(request: Request):
    require_superadmin(request)
    from database import get_db

    with get_db() as conn:
        recep_fsc = conn.execute(
            """SELECT COUNT(*) FROM stock_receptions
               WHERE fsc_type_claim != 'non_fsc' AND fsc_type_claim IS NOT NULL
               AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')"""
        ).fetchone()[0]
        dossiers_fsc = conn.execute(
            """SELECT COUNT(*) FROM planning_entries
               WHERE fsc_requis = 1 AND statut != 'termine'"""
        ).fetchone()[0]
        alertes = conn.execute(
            "SELECT COUNT(*) FROM fab_matieres_utilisees WHERE fsc_warning = 1"
        ).fetchone()[0]
        total_termines = conn.execute(
            "SELECT COUNT(*) FROM planning_entries WHERE fsc_requis = 1 AND statut = 'termine'"
        ).fetchone()[0]
    return {
        "recep_fsc_ce_mois": recep_fsc,
        "dossiers_fsc_actifs": dossiers_fsc,
        "alertes_ecart_total": alertes,
        "dossiers_termines_fsc": total_termines,
    }


@router.get("/api/fsc/registre")
def get_fsc_registre(
    request: Request,
    du: str = "",
    au: str = "",
    format: str = "json",
):
    require_superadmin(request)
    import csv
    import datetime as dt
    import io

    from database import get_db
    from fastapi.responses import StreamingResponse

    now = dt.datetime.now()
    date_au = au or now.strftime("%Y-%m-%d")
    date_du = du or (now - dt.timedelta(days=365)).strftime("%Y-%m-%d")

    with get_db() as conn:
        receptions = conn.execute(
            """SELECT r.id, r.created_at, r.created_by_name, r.fournisseur,
                      r.certificat_fsc, r.fsc_type_claim, r.nb_bobines,
                      ff.licence AS fournisseur_licence
               FROM stock_receptions r
               LEFT JOIN fournisseurs_fsc ff ON ff.nom = r.fournisseur
               WHERE r.fsc_type_claim != 'non_fsc' AND r.fsc_type_claim IS NOT NULL
               AND date(r.created_at) BETWEEN ? AND ?
               ORDER BY r.created_at DESC""",
            (date_du, date_au),
        ).fetchall()

        dossiers = conn.execute(
            """SELECT pe.reference, pe.client, pe.fsc_type_requis, pe.statut,
                      pe.date_livraison, pe.machine_id,
                      COUNT(fmu.id) AS nb_bobines_scannees,
                      SUM(CASE WHEN fmu.fsc_warning = 1 THEN 1 ELSE 0 END) AS nb_alertes
               FROM planning_entries pe
               LEFT JOIN fab_matieres_utilisees fmu ON fmu.no_dossier = pe.reference
               WHERE pe.fsc_requis = 1
               AND (pe.date_livraison BETWEEN ? AND ? OR pe.date_livraison IS NULL OR pe.date_livraison = '')
               GROUP BY pe.id
               ORDER BY pe.date_livraison DESC NULLS LAST""",
            (date_du, date_au),
        ).fetchall()

    recep_list = [dict(r) for r in receptions]
    dossier_list = [dict(d) for d in dossiers]

    if format == "csv":
        output = io.StringIO()
        output.write(f"# Registre FSC SIFA — {date_du} au {date_au}\n")
        output.write(f"# Généré le {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        output.write("## RECEPTIONS FSC\n")
        w = csv.writer(output)
        w.writerow(
            [
                "Date",
                "Fournisseur",
                "Licence FSC",
                "Certificat",
                "Type claim",
                "Nb bobines",
                "Réceptionné par",
            ]
        )
        for r in recep_list:
            claim = r.get("fsc_type_claim", "")
            w.writerow(
                [
                    (r.get("created_at") or "")[:10],
                    r.get("fournisseur") or "",
                    r.get("fournisseur_licence") or "",
                    r.get("certificat_fsc") or "",
                    _FSC_CLAIM_LABELS.get(claim, claim),
                    r.get("nb_bobines") or "",
                    r.get("created_by_name") or "",
                ]
            )
        output.write("\n## DOSSIERS FSC\n")
        w.writerow(
            [
                "Référence",
                "Client",
                "Type FSC requis",
                "Statut",
                "Date livraison",
                "Nb bobines scannées",
                "Alertes écart",
            ]
        )
        for d in dossier_list:
            claim = d.get("fsc_type_requis", "")
            w.writerow(
                [
                    d.get("reference") or "",
                    d.get("client") or "",
                    _FSC_CLAIM_LABELS.get(claim, claim),
                    d.get("statut") or "",
                    d.get("date_livraison") or "",
                    d.get("nb_bobines_scannees") or 0,
                    d.get("nb_alertes") or 0,
                ]
            )
        filename = f"registre_fsc_{date_du}_{date_au}.csv"
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return {
        "periode": {"du": date_du, "au": date_au},
        "genere_a": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "receptions": recep_list,
        "dossiers": dossier_list,
    }


# ─── Fournisseurs FSC ──────────────────────────────────────────────

@router.get("/api/fournisseurs")
def list_fournisseurs(request: Request):
    require_superadmin(request)
    from database import get_db
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, nom, licence, certificat, traca_photo_url, traca_explication, traca_exemple_code
               FROM fournisseurs_fsc ORDER BY nom COLLATE NOCASE ASC"""
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/api/fournisseurs")
async def create_fournisseur(request: Request):
    user = require_superadmin(request)
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
            log_action(
                user=user,
                action="CREATE",
                module="settings",
                objet=f"Fournisseur FSC {nom}",
                ip=request.client.host if request.client else None,
            )
            return {"success": True, "id": cur.lastrowid}
        except Exception:
            raise HTTPException(status_code=409, detail="Ce fournisseur existe déjà")


@router.put("/api/fournisseurs/{fournisseur_id}")
async def update_fournisseur(fournisseur_id: int, request: Request):
    user = require_superadmin(request)
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
        traca_explication = (body.get("traca_explication") or "").strip() or None
        traca_exemple_code = (body.get("traca_exemple_code") or "").strip() or None
        try:
            conn.execute(
                """UPDATE fournisseurs_fsc SET nom=?, licence=?, certificat=?,
                       traca_explication=?, traca_exemple_code=?
                   WHERE id=?""",
                (nom, licence, certificat, traca_explication, traca_exemple_code, fournisseur_id),
            )
            conn.commit()
            log_action(
                user=user,
                action="UPDATE",
                module="settings",
                objet=f"Fournisseur FSC {nom}",
                ip=request.client.host if request.client else None,
            )
            return {"success": True}
        except Exception:
            raise HTTPException(status_code=409, detail="Ce nom de fournisseur existe déjà")


@router.post("/api/fournisseurs/{fournisseur_id}/traca-photo")
async def upload_traca_photo(fournisseur_id: int, request: Request, photo: UploadFile = File(...)):
    """Upload d'une photo d'étiquette fournisseur pour le guide code-barre."""
    user = _require_traca_photo_editor(request)
    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if (photo.content_type or "") not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Format image non accepté (jpg, png, webp, gif).",
        )
    ext_map = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}
    ext = ext_map.get(photo.content_type or "", "jpg")
    dest_dir = Path(BASE_DIR) / "uploads" / "traca"
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"traca_{fournisseur_id}_{uuid.uuid4().hex[:8]}.{ext}"
    dest = dest_dir / filename
    content = await photo.read()
    if len(content) > 6 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 6 Mo).")
    with open(dest, "wb") as f:
        f.write(content)
    url = f"/uploads/traca/{filename}"
    from database import get_db

    four_nom = ""
    with get_db() as conn:
        ex = conn.execute(
            "SELECT id, nom, traca_photo_url FROM fournisseurs_fsc WHERE id=?",
            (fournisseur_id,),
        ).fetchone()
        if not ex:
            try:
                dest.unlink(missing_ok=True)
            except OSError:
                pass
            raise HTTPException(status_code=404, detail="Fournisseur introuvable")
        four_nom = ex["nom"] or ""
        old_url = ex["traca_photo_url"]
        if old_url:
            old_p = _traca_file_from_url(str(old_url))
            if old_p and old_p.is_file():
                try:
                    old_p.unlink()
                except OSError:
                    pass
        conn.execute(
            "UPDATE fournisseurs_fsc SET traca_photo_url=? WHERE id=?",
            (url, fournisseur_id),
        )
        conn.commit()
    log_action(
        user=user,
        action="UPDATE",
        module="settings",
        objet=f"Fournisseur FSC {four_nom}",
        detail={"traca_photo": True},
        ip=request.client.host if request.client else None,
    )
    return {"url": url}


@router.delete("/api/fournisseurs/{fournisseur_id}/traca-photo")
def delete_traca_photo(fournisseur_id: int, request: Request):
    user = _require_traca_photo_editor(request)
    from database import get_db

    four_nom = ""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, nom, traca_photo_url FROM fournisseurs_fsc WHERE id=?",
            (fournisseur_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Fournisseur introuvable")
        four_nom = row["nom"] or ""
        old_url = row["traca_photo_url"]
        if old_url:
            old_p = _traca_file_from_url(str(old_url))
            if old_p and old_p.is_file():
                try:
                    old_p.unlink()
                except OSError:
                    pass
        conn.execute(
            "UPDATE fournisseurs_fsc SET traca_photo_url=NULL WHERE id=?",
            (fournisseur_id,),
        )
        conn.commit()
    log_action(
        user=user,
        action="UPDATE",
        module="settings",
        objet=f"Fournisseur FSC {four_nom}",
        detail={"traca_photo": False},
        ip=request.client.host if request.client else None,
    )
    return {"ok": True}


@router.delete("/api/fournisseurs/{fournisseur_id}")
async def delete_fournisseur(fournisseur_id: int, request: Request):
    user = require_superadmin(request)
    from database import get_db
    four_nom = ""
    with get_db() as conn:
        ex = conn.execute("SELECT * FROM fournisseurs_fsc WHERE id=?", (fournisseur_id,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
        four_nom = ex["nom"] or ""
        conn.execute("DELETE FROM fournisseurs_fsc WHERE id=?", (fournisseur_id,))
        conn.commit()
    log_action(
        user=user,
        action="DELETE",
        module="settings",
        objet=f"Fournisseur FSC {four_nom}",
        ip=request.client.host if request.client else None,
    )
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
                   WHERE a.active=1 AND (a.scope=? OR a.scope='global')
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
    log_action(
        user=user,
        action="CREATE",
        module="settings",
        objet=f"Annonce · {titre}",
        detail={"scope": scope},
        ip=request.client.host if request.client else None,
    )
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
    user = require_superadmin(request)
    from database import get_db
    titre_ann = ""
    with get_db() as conn:
        ann = conn.execute(
            "SELECT * FROM update_announcements WHERE id=?", (announcement_id,)
        ).fetchone()
        if not ann:
            raise HTTPException(status_code=404, detail="Annonce non trouvée")
        titre_ann = ann["titre"] or ""
        # Vérifier si l'annonce a déjà été lue
        ack_count = conn.execute(
            "SELECT COUNT(*) FROM update_acknowledgements WHERE announcement_id=?",
            (announcement_id,)
        ).fetchone()[0]
        if ack_count > 0:
            raise HTTPException(status_code=400, detail="Impossible de supprimer une annonce déjà lue")
        conn.execute("DELETE FROM update_announcements WHERE id=?", (announcement_id,))
        conn.commit()
    log_action(
        user=user,
        action="DELETE",
        module="settings",
        objet=f"Annonce · {titre_ann}",
        ip=request.client.host if request.client else None,
    )
    return {"success": True}


# ── Référentiel codes opération (table operation_codes) ─────────────────────


@router.get("/api/settings/operation-codes")
def list_operation_codes(request: Request):
    require_superadmin(request)
    from database import get_db
    from app.services.operations_config import categories_for_ui, list_operation_codes as _list

    with get_db() as conn:
        items = _list(conn)
    return {"items": items, "categories": categories_for_ui()}


@router.post("/api/settings/operation-codes")
async def create_operation_code(request: Request):
    require_superadmin(request)
    from database import get_db
    from app.services.operations_config import TABLE, validate_operation_payload
    from config import refresh_operations_cache

    body = await request.json()
    try:
        payload = validate_operation_payload(body, for_create=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    now = datetime.now().isoformat()
    with get_db() as conn:
        ex = conn.execute(f"SELECT 1 FROM {TABLE} WHERE code=?", (payload["code"],)).fetchone()
        if ex:
            raise HTTPException(status_code=409, detail=f"Le code {payload['code']} existe déjà.")
        conn.execute(
            f"""INSERT INTO {TABLE} (code, severity, label, category, required, updated_at)
                VALUES (?,?,?,?,?,?)""",
            (
                payload["code"],
                payload["severity"],
                payload["label"],
                payload["category"],
                1 if payload["required"] else 0,
                now,
            ),
        )
        conn.commit()
    refresh_operations_cache()
    return {"success": True, "code": payload["code"]}


@router.put("/api/settings/operation-codes/{code}")
async def update_operation_code(code: str, request: Request):
    require_superadmin(request)
    from database import get_db
    from app.services.operations_config import TABLE, normalize_code, validate_operation_payload
    from config import refresh_operations_cache

    try:
        code_key = normalize_code(code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    body = await request.json()
    body = dict(body) if isinstance(body, dict) else {}
    body["code"] = code_key
    try:
        payload = validate_operation_payload(body, for_create=False)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    now = datetime.now().isoformat()
    with get_db() as conn:
        ex = conn.execute(f"SELECT 1 FROM {TABLE} WHERE code=?", (code_key,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Code introuvable.")
        conn.execute(
            f"""UPDATE {TABLE}
                SET severity=?, label=?, category=?, required=?, updated_at=?
                WHERE code=?""",
            (
                payload["severity"],
                payload["label"],
                payload["category"],
                1 if payload["required"] else 0,
                now,
                code_key,
            ),
        )
        conn.commit()
    refresh_operations_cache()
    return {"success": True}


@router.delete("/api/settings/operation-codes/{code}")
def delete_operation_code(code: str, request: Request):
    require_superadmin(request)
    from database import get_db
    from app.services.operations_config import TABLE, normalize_code
    from config import refresh_operations_cache

    try:
        code_key = normalize_code(code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    with get_db() as conn:
        ex = conn.execute(f"SELECT 1 FROM {TABLE} WHERE code=?", (code_key,)).fetchone()
        if not ex:
            raise HTTPException(status_code=404, detail="Code introuvable.")
        conn.execute(f"DELETE FROM {TABLE} WHERE code=?", (code_key,))
        conn.commit()
    refresh_operations_cache()
    return {"success": True}


@router.post("/api/settings/operation-codes/import-json")
def import_operation_codes_json(request: Request):
    """Réimporte depuis operations.json (upsert tous les codes du fichier)."""
    require_superadmin(request)
    from database import get_db
    from app.services.operations_config import upsert_operation_codes_from_json
    from config import refresh_operations_cache

    with get_db() as conn:
        n = upsert_operation_codes_from_json(conn)
        conn.commit()
    refresh_operations_cache()
    return {"success": True, "upserted": n}


# ── Machines (horaires planning + métrage total compteur) ───────────────────


@router.put("/api/settings/machines/{machine_id}/dernier-metrage")
async def set_machine_dernier_metrage(machine_id: int, request: Request):
    """Correction manuelle du compteur machine (dernier_metrage) — super admin."""
    user = require_superadmin(request)
    body = await request.json()
    if not isinstance(body, dict) or "dernier_metrage" not in body:
        raise HTTPException(status_code=400, detail="dernier_metrage requis")

    raw = body.get("dernier_metrage")
    if raw is None or raw == "":
        new_val = None
    else:
        try:
            new_val = float(raw)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Métrage invalide")
        if new_val < 0:
            raise HTTPException(status_code=400, detail="Le métrage doit être positif ou nul")

    from database import get_db

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, nom, dernier_metrage FROM machines WHERE id=? AND actif=1",
            (machine_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Machine introuvable")
        old_val = row["dernier_metrage"]
        conn.execute(
            "UPDATE machines SET dernier_metrage=? WHERE id=?",
            (new_val, machine_id),
        )
        conn.commit()
        machine_nom = row["nom"] or ""

    log_action(
        user=user,
        action="UPDATE",
        module="settings",
        objet=f"Métrage total machine {machine_nom}",
        detail={"machine_id": machine_id, "ancien": old_val, "nouveau": new_val},
        ip=request.client.host if request.client else None,
    )
    return {"success": True, "dernier_metrage": new_val}


@router.put("/api/settings/machines/{machine_id}/nom")
async def rename_machine(machine_id: int, request: Request):
    """Renommage du nom affiché d'une machine — super admin uniquement."""
    user = require_superadmin(request)
    body = await request.json()
    if not isinstance(body, dict) or "nom" not in body:
        raise HTTPException(status_code=400, detail="Champ nom requis")

    new_nom = str(body["nom"]).strip()
    if not new_nom:
        raise HTTPException(status_code=400, detail="Le nom ne peut pas être vide")
    if len(new_nom) > 80:
        raise HTTPException(status_code=400, detail="Nom trop long (80 caractères max)")

    from database import get_db

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, nom FROM machines WHERE id=? AND actif=1",
            (machine_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Machine introuvable")

        conflict = conn.execute(
            "SELECT id FROM machines WHERE lower(nom)=lower(?) AND id!=? AND actif=1",
            (new_nom, machine_id),
        ).fetchone()
        if conflict:
            raise HTTPException(status_code=409, detail="Ce nom est déjà utilisé par une autre machine")

        old_nom = row["nom"] or ""
        conn.execute("UPDATE machines SET nom=? WHERE id=?", (new_nom, machine_id))
        conn.commit()

    log_action(
        user=user,
        action="UPDATE",
        module="settings",
        objet=f"Renommage machine #{machine_id}",
        detail={"machine_id": machine_id, "ancien": old_nom, "nouveau": new_nom},
        ip=request.client.host if request.client else None,
    )
    return {"success": True, "id": machine_id, "nom": new_nom}


# ══════════════════════════════════════════════════════════════════
# Gestion des clés API (superadmin uniquement)
# ══════════════════════════════════════════════════════════════════

def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class ApiKeyCreateIn(BaseModel):
    name: str
    scopes: str = "of:read,of:write"


@router.get("/api/settings/api-keys")
def list_api_keys(request: Request):
    require_superadmin(request)
    from database import get_db
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, name, key_prefix, scopes, is_active,
                      created_by, created_at, last_used_at, revoked_at
               FROM api_keys ORDER BY created_at DESC"""
        ).fetchall()
    return {"keys": [dict(r) for r in rows]}


@router.post("/api/settings/api-keys")
def create_api_key(body: ApiKeyCreateIn, request: Request):
    require_superadmin(request)
    user = get_current_user(request)
    from database import get_db

    raw = "msk_" + secrets.token_hex(32)   # 68 chars, préfixe "msk_"
    h = _hash_key(raw)
    prefix = raw[:12]  # affiché dans la liste pour identification visuelle

    with get_db() as conn:
        conn.execute(
            """INSERT INTO api_keys (name, key_prefix, key_hash, scopes, is_active, created_by)
               VALUES (?,?,?,?,1,?)""",
            (body.name.strip(), prefix, h, body.scopes.strip(), user.get("email", ""))
        )
        conn.commit()

    # La clé brute n'est retournée QU'UNE SEULE FOIS ici — elle n'est jamais stockée en clair
    return {"key": raw, "prefix": prefix, "name": body.name}


@router.patch("/api/settings/api-keys/{key_id}/revoke")
def revoke_api_key(key_id: int, request: Request):
    require_superadmin(request)
    from database import get_db
    from datetime import datetime
    with get_db() as conn:
        row = conn.execute("SELECT id FROM api_keys WHERE id=?", (key_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Clé introuvable.")
        conn.execute(
            "UPDATE api_keys SET is_active=0, revoked_at=? WHERE id=?",
            (datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), key_id)
        )
        conn.commit()
    return {"revoked": True, "id": key_id}


@router.delete("/api/settings/api-keys/{key_id}")
def delete_api_key(key_id: int, request: Request):
    require_superadmin(request)
    from database import get_db
    with get_db() as conn:
        conn.execute("DELETE FROM api_keys WHERE id=?", (key_id,))
        conn.commit()
    return {"deleted": True, "id": key_id}


# ──────────────────────────────────────────────────
# Emplacements (référentiel magasin)
# ──────────────────────────────────────────────────

class EmplacementCreate(BaseModel):
    code: str


@router.get("/api/settings/emplacements")
def get_emplacements(request: Request):
    require_superadmin(request)
    from database import get_db
    with get_db() as conn:
        # Créer la table si elle n'existe pas encore
        conn.execute(
            """CREATE TABLE IF NOT EXISTS emplacements_plan (
                code TEXT PRIMARY KEY NOT NULL,
                imported_at TEXT NOT NULL
            )"""
        )
        rows = conn.execute(
            "SELECT code, imported_at FROM emplacements_plan ORDER BY code"
        ).fetchall()
    return [{"code": r["code"], "imported_at": r["imported_at"]} for r in rows]


@router.post("/api/settings/emplacements")
def create_emplacement(payload: EmplacementCreate, request: Request):
    require_superadmin(request)
    code = payload.code.strip().upper()
    if not code:
        raise HTTPException(400, "Code emplacement vide.")
    if len(code) > 20:
        raise HTTPException(400, "Code trop long (20 caractères max).")
    from database import get_db
    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS emplacements_plan (
                code TEXT PRIMARY KEY NOT NULL,
                imported_at TEXT NOT NULL
            )"""
        )
        existing = conn.execute(
            "SELECT 1 FROM emplacements_plan WHERE code=?", (code,)
        ).fetchone()
        if existing:
            raise HTTPException(409, f"L'emplacement {code} existe déjà.")
        conn.execute(
            "INSERT INTO emplacements_plan (code, imported_at) VALUES (?, ?)",
            (code, now),
        )
        conn.commit()
    return {"code": code, "imported_at": now}


@router.delete("/api/settings/emplacements/{code}")
def delete_emplacement(code: str, request: Request):
    require_superadmin(request)
    from database import get_db
    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM emplacements_plan WHERE code=?", (code.upper(),)
        )
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(404, f"Emplacement {code} introuvable.")
    return {"deleted": True, "code": code.upper()}


@router.post("/api/settings/emplacements/reload-csv")
def reload_emplacements_csv(request: Request):
    require_superadmin(request)
    from app.core.database import sync_emplacements_plan_from_csv
    try:
        n = sync_emplacements_plan_from_csv()
    except Exception as exc:
        raise HTTPException(500, f"Erreur lors du rechargement CSV : {exc}")
    if n == 0:
        raise HTTPException(422, "Fichier CSV introuvable ou vide — aucun emplacement importé.")
    return {"imported": n}


@router.post("/api/settings/emplacements/import-csv")
async def import_emplacements_csv(request: Request, file: UploadFile = File(...)):
    require_superadmin(request)
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, "Le fichier doit être au format CSV (.csv).")
    contents = await file.read()
    if not contents.strip():
        raise HTTPException(422, "Le fichier CSV est vide.")
    csv_path = Path(BASE_DIR) / "data" / "emplacements_plan.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_bytes(contents)
    from app.core.database import sync_emplacements_plan_from_csv
    try:
        n = sync_emplacements_plan_from_csv()
    except Exception as exc:
        raise HTTPException(500, f"Erreur lors du rechargement : {exc}")
    if n == 0:
        raise HTTPException(422, "CSV importé mais aucun emplacement reconnu — vérifiez le format.")
    return {"imported": n}


# ─── Promotion v1 → v2 ─────────────────────────────────────────────────────────
# Endpoint pilote depuis l'instance v1. Lit l'état du dépôt v2 sur disque,
# liste les commits en avance, et exécute scripts/promote_v2.sh quand demandé.

import asyncio
import shutil as _shutil
import subprocess as _subprocess
from fastapi.responses import StreamingResponse
from config import ENV_NAME, APP_VERSION

V2_REPO_PATH = "/home/sifa/production-saas"
V1_REPO_PATH = "/home/sifa/production-saas-v1"

# systemd lance le service avec un PATH minimal qui ne contient pas /usr/bin.
# On résout git une fois au boot avec un PATH explicite, fallback /usr/bin/git.
_GIT_BIN = _shutil.which("git", path="/usr/local/bin:/usr/bin:/bin") or "/usr/bin/git"
# Le script est exécuté depuis v1 (la version la plus récente est toujours là)
# mais opère sur le dépôt v2.
PROMOTE_SCRIPT = f"{V1_REPO_PATH}/scripts/promote_v2.sh"


def _parse_version_from_text(text: str) -> Optional[str]:
    for line in text.splitlines():
        if line.strip().startswith("APP_VERSION"):
            parts = line.split('"')
            if len(parts) >= 2:
                return parts[1]
    return None


def _read_v2_app_version() -> Optional[str]:
    """Lit APP_VERSION depuis le config.py du dépôt v2 sur disque (sans import)."""
    try:
        with open(f"{V2_REPO_PATH}/config.py", "r", encoding="utf-8") as f:
            return _parse_version_from_text(f.read())
    except Exception:
        return None


def _read_origin_app_version() -> Optional[str]:
    """Lit APP_VERSION dans config.py côté origin/main (via git show, sans pull)."""
    try:
        out = _subprocess.check_output(
            [_GIT_BIN, "-C", V2_REPO_PATH, "show", "origin/main:config.py"],
            text=True, timeout=10,
        )
        return _parse_version_from_text(out)
    except Exception:
        return None


@router.get("/api/promote/status")
def promote_status(request: Request):
    require_superadmin(request)

    # 1. Fetch silencieux pour avoir l'état à jour d'origin/main
    try:
        _subprocess.run(
            [_GIT_BIN, "-C", V2_REPO_PATH, "fetch", "--quiet"],
            check=False, capture_output=True, timeout=15,
        )
    except Exception:
        pass  # On continue même si le fetch échoue, on travaille avec ce qu'on a

    try:
        v2_head = _subprocess.check_output(
            [_GIT_BIN, "-C", V2_REPO_PATH, "rev-parse", "HEAD"],
            text=True, timeout=5,
        ).strip()
        origin_main = _subprocess.check_output(
            [_GIT_BIN, "-C", V2_REPO_PATH, "rev-parse", "origin/main"],
            text=True, timeout=5,
        ).strip()
    except Exception as exc:
        raise HTTPException(500, f"Lecture git impossible : {exc}")

    v2_version = _read_v2_app_version()
    next_version = _read_origin_app_version() or v2_version

    commits_ahead = []
    if v2_head != origin_main:
        try:
            log_out = _subprocess.check_output(
                [_GIT_BIN, "-C", V2_REPO_PATH, "log",
                 f"{v2_head}..{origin_main}",
                 "--pretty=format:%h|%an|%ad|%s",
                 "--date=format:%Y-%m-%d %H:%M"],
                text=True, timeout=10,
            )
            for line in log_out.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("|", 3)
                if len(parts) == 4:
                    commits_ahead.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "subject": parts[3],
                    })
        except Exception:
            pass

    can_promote = (ENV_NAME == "v1") and len(commits_ahead) > 0
    reason: Optional[str] = None
    if ENV_NAME != "v1":
        reason = "La promotion doit être lancée depuis https://v1.mysifa.com."
    elif not commits_ahead:
        reason = "Rien à promouvoir — v2 est déjà à jour."

    return {
        "env": ENV_NAME,
        "v1_version": APP_VERSION,
        "v2_version": v2_version,
        "next_version": next_version,
        "v2_head": v2_head[:7],
        "origin_head": origin_main[:7],
        "commits_ahead": commits_ahead,
        "can_promote": can_promote,
        "reason": reason,
    }


@router.post("/api/promote")
async def promote_run(request: Request):
    require_superadmin(request)
    if ENV_NAME != "v1":
        raise HTTPException(400, "Promotion uniquement disponible depuis v1.")

    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    notes = (body.get("notes") or "").strip()

    async def stream():
        # Lance le script avec sudo (les droits sudo sans mot de passe sont
        # configurés côté système pour l'utilisateur sifa sur ce script précis).
        try:
            proc = await asyncio.create_subprocess_exec(
                "sudo", "-n", PROMOTE_SCRIPT, notes,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except Exception as exc:
            yield f"ERREUR : impossible de lancer le script — {exc}\n".encode()
            return

        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            yield line

        rc = await proc.wait()
        if rc == 0:
            yield b"\n[script termine OK]\n"
        else:
            yield f"\n[script termine en erreur — code {rc}]\n".encode()

    return StreamingResponse(stream(), media_type="text/plain; charset=utf-8")
